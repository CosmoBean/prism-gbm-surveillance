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
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

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


def seg_path(scan_id: str, model: str = "brats21"):
    pid, tp = scan_id.split("_Timepoint_")
    return SEG / SUBDIR[model] / pid / f"Timepoint_{tp}.nii.gz"


def volumes_path(model: str = "brats21"):
    return SEG / f"volumes_{model}.csv"


def load_model(name: str, device="cuda"):
    from monai.networks.nets import SwinUNETR
    m = SwinUNETR(in_channels=4, out_channels=3, feature_size=48, use_checkpoint=False)
    path, key = MODELS[name]
    sd = torch.load(path, map_location="cpu", weights_only=False)
    sd = sd[key] if key else sd
    sd = sd.get("state_dict", sd)
    m.load_state_dict({k.replace("module.", ""): v for k, v in sd.items()}, strict=True)
    return m.to(device).eval()


def load_scan(scan_id: str):
    from monai.transforms import NormalizeIntensity
    pid, tp = scan_id.split("_Timepoint_")
    p = mu_scan_paths(pid, f"Timepoint_{tp}")
    img = np.stack([np.asarray(nib.load(str(p[c])).dataobj, dtype=np.float32) for c in CHANNELS])
    img = NormalizeIntensity(nonzero=True, channel_wise=True)(img)
    ref = nib.load(str(p["mask"]))
    mu = np.rint(np.asarray(ref.dataobj)).astype(np.uint8)
    return np.asarray(img, dtype=np.float32), mu, ref.affine, ref.header


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
    def __init__(self, ids):
        self.ids = list(ids)

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, i):
        try:
            return self.ids[i], *load_scan(self.ids[i])
        except FileNotFoundError:
            return self.ids[i], None, None, None, None


@torch.no_grad()
def run(ids, model_name: str, workers: int = 6, write: bool = True) -> pd.DataFrame:
    from monai.inferers import sliding_window_inference
    model = load_model(model_name)
    loader = torch.utils.data.DataLoader(_Scans(ids), batch_size=None, num_workers=workers, prefetch_factor=2,
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
        if write:
            f = seg_path(sid, model_name)
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
    a = ap.parse_args(argv)
    idx = load_index()
    ids = idx.loc[idx.complete.astype(bool), "scan_id"].tolist()[: a.limit]
    vp = volumes_path(a.model)
    if a.gpus > 1 and a.shard is None:
        t = time.time()
        gpus = os.environ.get("CUDA_VISIBLE_DEVICES", ",".join(map(str, range(a.gpus)))).split(",")[: a.gpus]
        base = [sys.executable, "-m", "prism.features.reseg", "--model", a.model, "--workers", str(a.workers)]
        base += ["--limit", str(a.limit)] if a.limit else []
        procs = [subprocess.Popen(base + ["--shard", str(k), str(len(gpus))], env={**os.environ, "CUDA_VISIBLE_DEVICES": g})
                 for k, g in enumerate(gpus)]
        if any(p.wait() for p in procs):
            raise SystemExit("a shard failed")
        parts = [vp.with_suffix(f".shard{k}.csv") for k in range(len(gpus))]
        df = pd.concat([pd.read_csv(p) for p in parts]).set_index("scan_id").reindex(ids).reset_index()
        if a.limit is None:
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
    df = run(ids, a.model, a.workers)
    vp.parent.mkdir(parents=True, exist_ok=True)
    if a.shard:
        df.to_csv(vp.with_suffix(f".shard{a.shard[0]}.csv"), index=False)
    else:
        print(df.round(3).to_string(index=False))
        if a.limit is None:
            df.to_csv(vp, index=False)


if __name__ == "__main__":
    main()
