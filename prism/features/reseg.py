"""Re-segment every MU scan with ONE fixed BraTS model (consistency test for the shipped MU masks).

Model    MONAI BraTS 2021 SwinUNETR fold 1 (in 4 / out 3 / feature size 48), optionally BrainSegFounder BraTS-finetune
         (same architecture). Channel order FLAIR, T1c, T1, T2 (MONAI BraTS21 tutorial json order).
Input    MU FeTS-preprocessed 1 mm BraTS-space volumes as stored (no reorientation; the BraTS21 training pipeline used
         none either), NormalizeIntensity(nonzero=True, channel_wise=True) as in the tutorial.
Infer    sliding_window_inference roi 128^3, overlap 0.5, sw batch 4, bf16 autocast; sigmoid > 0.5 on (TC, WT, ET).
Labels   MU convention: 3 ET = ET; 1 NETC = TC & ~ET; 2 SNFH = WT & ~TC & ~ET (tutorial priority ET > TC > WT).
         The BraTS models have no resection-cavity class, so label 4 is never produced.

    python -m prism.features.reseg [--model brats21|bsf] [--gpus 4] [--limit N]
    -> $PRISM_OUTPUTS/features/seg_swin/<mu|mu_bsf>/<patient>/<timepoint>.nii.gz + volumes_<model>.csv
       (voxel counts per label, Dice ET/TC/WT vs the shipped MU mask)

External cohorts (segmentation stage S1, docs/results/SEGMENTER_STAGE_PLAN.md; brats21 only):
    python -m prism.features.reseg --cohort lumiere|ucsf [--gpus 4] [--limit N | --ids ID ...]
    -> $PRISM_OUTPUTS/features/seg_swin/<lumiere|ucsf>/<patient>/<timepoint>.nii.gz + volumes_brats21_<cohort>.csv
  LUMIERE  DeepBraTumIA atlas/skull_strip/{flair,ct1,t1,t2}_skull_strip.nii.gz, extracted from Imaging-v202211.zip
           into $PRISM_OUTPUTS/features/seg_swin/lumiere_input/ (prism.features.seg_measurements extract_lumiere).
           182x218x182 1 mm, LAS. Released mask atlas/segmentation/seg_mask.nii.gz uses the DeepBraTumIA numbering
           1 enhancing, 2 necrotic + non-enhancing (cavity included), 3 oedema (checked against the study's
           measured_volumes_in_mm3.json), mapped to MU 3 ET, 1 NETC, 2 SNFH. --orient lps reorients the four images
           to the MU / BraTS axis order (LPS) for inference and maps the labels back to the stored grid.
  UCSF     <id>/<id>_time{1,2}_{flair,t1ce,t1,t2}.nii.gz (240x240x155, 1 mm, LPS as MU); released <id>_time{t}_seg
           uses the MU / BraTS post-treatment numbering (prism.features.ucsf_imaging): 1 NETC, 2 SNFH, 3 ET, 4 RC.
  Same model, normalisation, sliding window and thresholds as MU. Dice compartments as MU: ET = 3, TC = 1|3,
  WT = 1|2|3 (the UCSF cavity, label 4, is outside WT).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import torch

from prism.config import DATA, LABEL_ET, LABEL_NETC, LABEL_SNFH, OUTPUTS, mu_scan_paths
from prism.data.mu import load_index

WEIGHTS = DATA / "weights"
MODELS = {"brats21": (WEIGHTS / "brats21_swinunetr_fold1_f48" / "model.pt", "state_dict"),
          "bsf": (WEIGHTS / "brainsegfounder_brats_ft.pt", None)}
CHANNELS = ("flair", "t1c", "t1", "t2")
SEG = OUTPUTS / "features" / "seg_swin"
SUBDIR = {"brats21": "mu", "bsf": "mu_bsf"}
COHORTS = ("mu", "lumiere", "ucsf")
LUMIERE_IN = SEG / "lumiere_input" / "Imaging"
UCSF_ROOT = Path(os.environ.get("PRISM_UCSF_ROOT", "/project/community/sbandred/ucsf"))
LUMIERE_TO_MU = np.array([0, LABEL_ET, LABEL_NETC, LABEL_SNFH], np.uint8)  # DeepBraTumIA 1 ET, 2 NC, 3 oedema
ORIENT = {"lumiere": os.environ.get("PRISM_RESEG_ORIENT", "as_stored"), "ucsf": "as_stored"}


def seg_path(scan_id: str, model: str = "brats21"):
    pid, tp = scan_id.split("_Timepoint_")
    return SEG / SUBDIR[model] / pid / f"Timepoint_{tp}.nii.gz"


def volumes_path(model: str = "brats21", cohort: str = "mu"):
    return SEG / (f"volumes_{model}.csv" if cohort == "mu" else f"volumes_{model}_{cohort}.csv")


def ext_seg_path(cohort: str, scan_id: str):
    """Segmenter label map of an external scan: LUMIERE Patient-001_week-044, UCSF 100001_time2."""
    pid, tp = scan_id.split("_", 1)
    return SEG / cohort / pid / f"{tp}.nii.gz"


def ext_paths(cohort: str, scan_id: str) -> dict:
    """Image paths (flair, t1c, t1, t2) and released mask of one external scan."""
    pid, tp = scan_id.split("_", 1)
    if cohort == "lumiere":
        d = LUMIERE_IN / pid / tp / "DeepBraTumIA-segmentation" / "atlas"
        p = {c: d / "skull_strip" / f"{f}_skull_strip.nii.gz" for c, f in
             (("flair", "flair"), ("t1c", "ct1"), ("t1", "t1"), ("t2", "t2"))}
        p["mask"] = d / "segmentation" / "seg_mask.nii.gz"
        return p
    d, stem = UCSF_ROOT / pid, f"{pid}_{tp}"
    p = {c: d / f"{stem}_{f}.nii.gz" for c, f in (("flair", "flair"), ("t1c", "t1ce"), ("t1", "t1"), ("t2", "t2"))}
    p["mask"] = d / f"{stem}_seg.nii.gz"
    return p


def ext_ids(cohort: str) -> list[str]:
    """Every external scan with all four images on disk."""
    if cohort == "lumiere":
        ids = sorted(f"{q.parent.name}_{q.name}" for q in LUMIERE_IN.glob("Patient-*/week-*"))
    else:
        ids = sorted(f"{q.name}_time{t}" for q in UCSF_ROOT.iterdir() if q.is_dir() and q.name.isdigit() for t in (1, 2))
    return [i for i in ids if all(v.exists() for k, v in ext_paths(cohort, i).items() if k != "mask")]


def load_model(name: str, device="cuda"):
    from monai.networks.nets import SwinUNETR
    m = SwinUNETR(in_channels=4, out_channels=3, feature_size=48, use_checkpoint=False)
    path, key = MODELS[name]
    sd = torch.load(path, map_location="cpu", weights_only=False)
    sd = sd[key] if key else sd
    sd = sd.get("state_dict", sd)
    m.load_state_dict({k.replace("module.", ""): v for k, v in sd.items()}, strict=True)
    return m.to(device).eval()


def load_scan(scan_id: str, cohort: str = "mu"):
    from monai.transforms import NormalizeIntensity
    if cohort == "mu":
        pid, tp = scan_id.split("_Timepoint_")
        p = mu_scan_paths(pid, f"Timepoint_{tp}")
    else:
        return load_ext(scan_id, cohort)
    img = np.stack([np.asarray(nib.load(str(p[c])).dataobj, dtype=np.float32) for c in CHANNELS])
    img = NormalizeIntensity(nonzero=True, channel_wise=True)(img)
    ref = nib.load(str(p["mask"]))
    mu = np.rint(np.asarray(ref.dataobj)).astype(np.uint8)
    return np.asarray(img, dtype=np.float32), mu, ref.affine, ref.header


def _ornt(aff):
    """(to LPS, back to stored) orientation transforms for an affine."""
    from nibabel.orientations import axcodes2ornt, io_orientation, ornt_transform
    src, dst = io_orientation(aff), axcodes2ornt(("L", "P", "S"))
    return ornt_transform(src, dst), ornt_transform(dst, src)


def load_ext(scan_id: str, cohort: str):
    """External scan as (image (4, ...) normalised, released mask in MU numbering, affine, header); with
    ORIENT[cohort] == 'lps' both arrays are in LPS axis order (run() maps the prediction back)."""
    from monai.transforms import NormalizeIntensity
    from nibabel.orientations import apply_orientation
    p = ext_paths(cohort, scan_id)
    ref = nib.load(str(p["t1c"]))
    img = np.stack([np.asarray(nib.load(str(p[c])).dataobj, dtype=np.float32) for c in CHANNELS])
    if p["mask"].exists():
        mask = np.rint(np.asarray(nib.load(str(p["mask"])).dataobj)).astype(np.uint8)
        if cohort == "lumiere":
            mask = LUMIERE_TO_MU[mask]
    else:  # no released mask: compare against an empty map
        mask = np.zeros(ref.shape[:3], np.uint8)
    if ORIENT[cohort] == "lps":
        fwd, _ = _ornt(ref.affine)
        img = np.stack([apply_orientation(x, fwd) for x in img])
        mask = apply_orientation(mask, fwd)
    img = NormalizeIntensity(nonzero=True, channel_wise=True)(img)
    return np.asarray(img, dtype=np.float32), np.ascontiguousarray(mask), ref.affine, ref.header


def to_labels(prob: np.ndarray) -> np.ndarray:
    tc, wt, et = prob > 0.5
    lab = np.zeros(tc.shape, np.uint8)
    lab[wt] = LABEL_SNFH
    lab[tc] = LABEL_NETC
    lab[et] = LABEL_ET
    return lab


def compartments(lab: np.ndarray) -> dict[str, np.ndarray]:
    et = lab == LABEL_ET
    tc = et | (lab == LABEL_NETC)
    return {"et": et, "tc": tc, "wt": tc | (lab == LABEL_SNFH)}


def dice(a: np.ndarray, b: np.ndarray) -> float:
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else np.nan


class _Scans(torch.utils.data.Dataset):
    def __init__(self, ids, cohort="mu"):
        self.ids = list(ids)
        self.cohort = cohort

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, i):
        try:
            return self.ids[i], *(load_scan(self.ids[i]) if self.cohort == "mu" else load_scan(self.ids[i], self.cohort))
        except FileNotFoundError:
            return self.ids[i], None, None, None, None


@torch.no_grad()
def run(ids, model_name: str, workers: int = 6, write: bool = True, cohort: str = "mu") -> pd.DataFrame:
    from monai.inferers import sliding_window_inference
    model = load_model(model_name)
    loader = torch.utils.data.DataLoader(_Scans(ids, cohort), batch_size=None, num_workers=workers, prefetch_factor=2,
                                         collate_fn=lambda x: x)
    rows, t = [], time.time()
    for i, (sid, img, mu, aff, hdr) in enumerate(loader):
        if img is None:
            rows.append({"scan_id": sid})
            continue
        x = torch.from_numpy(img)[None].cuda()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logit = sliding_window_inference(x, (128, 128, 128), 4, model, overlap=0.5)
        lab = to_labels(torch.sigmoid(logit.float())[0].cpu().numpy())
        if cohort != "mu" and ORIENT[cohort] == "lps":
            from nibabel.orientations import apply_orientation
            back = _ornt(aff)[1]
            lab, mu = (np.ascontiguousarray(apply_orientation(v, back)).astype(np.uint8) for v in (lab, mu))
        if write:
            f = seg_path(sid, model_name) if cohort == "mu" else ext_seg_path(cohort, sid)
            f.parent.mkdir(parents=True, exist_ok=True)
            out = nib.Nifti1Image(lab, aff, hdr)
            out.set_data_dtype(np.uint8)
            nib.save(out, str(f))
        new, old = compartments(lab), compartments(mu)
        rows.append({"scan_id": sid, **{f"label{k}_voxels": int((lab == k).sum()) for k in (1, 2, 3)},
                     **{f"mu_{c}_voxels": int(old[c].sum()) for c in old},
                     **{f"new_{c}_voxels": int(new[c].sum()) for c in new},
                     **{f"dice_{c}": dice(new[c], old[c]) for c in new}})
        if i % 25 == 0:
            r = rows[-1]
            print(f"  {i + 1}/{len(ids)} {sid} dice ET/TC/WT {r['dice_et']:.2f}/{r['dice_tc']:.2f}/{r['dice_wt']:.2f} "
                  f"{time.time() - t:.0f}s", flush=True)
    return pd.DataFrame(rows)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism.features.reseg", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="brats21", choices=list(MODELS))
    ap.add_argument("--gpus", type=int, default=1, help="shard over this many visible GPUs (one process each)")
    ap.add_argument("--shard", type=int, nargs=2, metavar=("K", "N"), help=argparse.SUPPRESS)
    ap.add_argument("--limit", type=int, help="first N scans only (smoke test; label maps written, csv not)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--cohort", default="mu", choices=COHORTS)
    ap.add_argument("--ids", nargs="+", help="these scan ids only (smoke test; label maps written, csv not)")
    a = ap.parse_args(argv)
    if a.cohort == "mu":
        idx = load_index()
        ids = idx.loc[idx.complete.astype(bool), "scan_id"].tolist()[: a.limit]
    else:
        assert a.model == "brats21", "external cohorts: brats21 only"
        ids = a.ids or ext_ids(a.cohort)[: a.limit]
    partial = a.limit is not None or a.ids is not None
    vp = volumes_path(a.model, a.cohort)
    if a.gpus > 1 and a.shard is None:
        t = time.time()
        gpus = os.environ.get("CUDA_VISIBLE_DEVICES", ",".join(map(str, range(a.gpus)))).split(",")[: a.gpus]
        base = [sys.executable, "-m", "prism.features.reseg", "--model", a.model, "--workers", str(a.workers)]
        base += ["--limit", str(a.limit)] if a.limit else []
        base += ["--cohort", a.cohort] if a.cohort != "mu" else []
        base += ["--ids", *a.ids] if a.ids else []
        procs = [subprocess.Popen(base + ["--shard", str(k), str(len(gpus))], env={**os.environ, "CUDA_VISIBLE_DEVICES": g})
                 for k, g in enumerate(gpus)]
        if any(p.wait() for p in procs):
            raise SystemExit("a shard failed")
        parts = [vp.with_suffix(f".shard{k}.csv") for k in range(len(gpus))]
        df = pd.concat([pd.read_csv(p) for p in parts]).set_index("scan_id").reindex(ids).reset_index()
        if not partial:
            df.to_csv(vp, index=False)
        for p in parts:
            p.unlink()
        print(f"{len(df)} scans, {time.time() - t:.0f}s; median Dice ET/TC/WT "
              f"{df.dice_et.median():.3f}/{df.dice_tc.median():.3f}/{df.dice_wt.median():.3f} -> {vp}")
        return
    torch.backends.cuda.matmul.allow_tf32 = True
    if a.shard:
        ids = ids[a.shard[0]::a.shard[1]]
    print(f"== {a.model}: {len(ids)} scans", flush=True)
    df = run(ids, a.model, a.workers) if a.cohort == "mu" else run(ids, a.model, a.workers, cohort=a.cohort)
    vp.parent.mkdir(parents=True, exist_ok=True)
    if a.shard:
        df.to_csv(vp.with_suffix(f".shard{a.shard[0]}.csv"), index=False)
    else:
        print(df.round(3).to_string(index=False))
        if not partial:
            df.to_csv(vp, index=False)


if __name__ == "__main__":
    main()
