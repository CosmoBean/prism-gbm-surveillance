"""Segment scans with a BraTS 2024 post-treatment glioma model (BraTS orchestrator container, run with enroot).

Model    BraTS24_1 (Ferreira et al., 1st place, adult glioma post-treatment): nnU-Net / MedNeXt ensemble, image
         brainles/brats24_adult_glioma_faking_it:latest, imported with `enroot import` and unpacked as `brats24_1`
         under $PRISM_ENROOT_DATA. Labels: 1 NETC, 2 SNFH, 3 ET, 4 RC (the MU / BraTS post-treatment numbering).
Input    the four sequences named BraTS-GLI-{i:05d}-100-{t1c,t1n,t2f,t2w}.nii.gz. MU and UCSF as stored (240 x 240 x
         155, 1 mm, LPS); LUMIERE DeepBraTumIA atlas images reoriented to LPS, as for the Swin UNETR stage (S1), and
         the label map mapped back to the stored grid.
Run      one container per GPU (NVIDIA_VISIBLE_DEVICES), each with its own input, output and scratch mounts, so the
         ensemble's working folders inside the image never collide.
Output   $PRISM_OUTPUTS/features/seg_brats24/<cohort>/<patient>/<timepoint>.nii.gz and volumes_brats24_<cohort>.csv
         (voxels per label, Dice ET / TC / WT / RC against the released mask; RC only where the mask has one).

    python -m prism.features.reseg_brats24 --cohort mu|lumiere|ucsf [--gpus 4] [--ids ID ...] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

from prism.config import LABEL_ET, LABEL_NETC, LABEL_SNFH, OUTPUTS, mu_scan_paths
from prism.features import reseg as R

ENROOT_DATA = os.environ.get("PRISM_ENROOT_DATA", "/project/community/sbandred/containers/data")
CONTAINER = "brats24_1"
OUT = OUTPUTS / "features" / "seg_brats24"
WORK = Path(os.environ.get("PRISM_BRATS24_WORK", "/project/community/sbandred/brats24_work"))
LABEL_RC = 4
SEQ = {"t1c": "t1c", "t1n": "t1", "t2f": "flair", "t2w": "t2"}     # BraTS suffix -> our channel name


def paths(cohort: str, sid: str) -> dict:
    if cohort == "mu":
        pid, tp = sid.split("_Timepoint_")
        return mu_scan_paths(pid, f"Timepoint_{tp}")
    return R.ext_paths(cohort, sid)


def out_path(cohort: str, sid: str) -> Path:
    if cohort == "mu":
        pid, tp = sid.split("_Timepoint_")
        return OUT / "mu" / pid / f"Timepoint_{tp}.nii.gz"
    pid, tp = sid.split("_", 1)
    return OUT / cohort / pid / f"{tp}.nii.gz"


def all_ids(cohort: str) -> list[str]:
    if cohort == "mu":
        from prism.data.mu import load_index
        idx = load_index()
        return idx.loc[idx.complete.astype(bool), "scan_id"].tolist()
    return R.ext_ids(cohort)


def _lps(cohort: str) -> bool:
    return cohort == "lumiere"


def stage(cohort: str, ids: list[str], d: Path) -> dict:
    """Write the BraTS-named inputs into d/in; return {case name: scan id}."""
    from nibabel.orientations import apply_orientation
    names = {}
    for i, sid in enumerate(ids):
        name = f"BraTS-GLI-{i:05d}-100"
        (d / "in" / name).mkdir(parents=True, exist_ok=True)
        p = paths(cohort, sid)
        for suf, ch in SEQ.items():
            src = nib.load(str(p[ch]))
            dst = d / "in" / name / f"{name}-{suf}.nii.gz"
            if _lps(cohort):
                fwd, _ = R._ornt(src.affine)
                arr = apply_orientation(np.asarray(src.dataobj, dtype=np.float32), fwd)
                aff = src.affine @ nib.orientations.inv_ornt_aff(fwd, src.shape[:3])
                nib.save(nib.Nifti1Image(arr, aff), str(dst))
            else:
                shutil.copyfile(p[ch], dst)
        names[name] = sid
    return names


def run_container(d: Path, gpu: int) -> float:
    for sub in ("out", "conv", "inf"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    # enroot does not pass the host environment into the container; --env NAME copies the named host variable in.
    env = dict(os.environ, ENROOT_DATA_PATH=ENROOT_DATA, CUDA_VISIBLE_DEVICES=str(gpu))
    cmd = ["enroot", "start", "--rw", "--env", "CUDA_VISIBLE_DEVICES",
           "--mount", f"{d / 'in'}:/mlcube_io0", "--mount", f"{d / 'out'}:/mlcube_io2",
           "--mount", f"{d / 'conv'}:/mlcube_project/converted_dataset",
           "--mount", f"{d / 'inf'}:/mlcube_project/inference",
           CONTAINER, "infer", "--data_path=/mlcube_io0", "--output_path=/mlcube_io2"]
    t = time.time()
    with open(d / "container.log", "w") as fh:
        subprocess.run(cmd, env=env, stdout=fh, stderr=subprocess.STDOUT, check=True)
    return time.time() - t


def released(cohort: str, sid: str) -> np.ndarray | None:
    m = paths(cohort, sid)["mask"]
    if not Path(m).exists():
        return None
    a = np.rint(np.asarray(nib.load(str(m)).dataobj)).astype(np.uint8)
    return R.LUMIERE_TO_MU[a] if cohort == "lumiere" else a


def collect(cohort: str, names: dict, d: Path) -> list[dict]:
    from nibabel.orientations import apply_orientation
    rows = []
    for name, sid in names.items():
        f = d / "out" / f"{name}.nii.gz"
        if not f.exists():
            rows.append({"scan_id": sid, "error": "no output"})
            continue
        lab = np.rint(np.asarray(nib.load(str(f)).dataobj)).astype(np.uint8)
        ref = nib.load(str(paths(cohort, sid)["t1c"]))
        if _lps(cohort):
            lab = apply_orientation(lab, R._ornt(ref.affine)[1])
        lab = np.ascontiguousarray(lab).astype(np.uint8)
        assert lab.shape == ref.shape[:3], (sid, lab.shape, ref.shape)
        o = out_path(cohort, sid)
        o.parent.mkdir(parents=True, exist_ok=True)
        img = nib.Nifti1Image(lab, ref.affine, ref.header)
        img.set_data_dtype(np.uint8)
        nib.save(img, str(o))
        row = {"scan_id": sid, **{f"label{k}_voxels": int((lab == k).sum()) for k in (1, 2, 3, 4)}}
        mu = released(cohort, sid)
        if mu is not None:
            new, old = R.compartments(lab), R.compartments(mu)
            row.update({f"dice_{c}": R.dice(new[c], old[c]) for c in new})
            row["dice_rc"] = R.dice(lab == LABEL_RC, mu == LABEL_RC) if (mu == LABEL_RC).any() else np.nan
        rows.append(row)
    return rows


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism.features.reseg_brats24", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cohort", required=True, choices=R.COHORTS)
    ap.add_argument("--gpus", type=int, default=4)
    ap.add_argument("--gpu0", type=int, default=0, help="first GPU index (to run cohorts side by side)")
    ap.add_argument("--ids", nargs="+")
    ap.add_argument("--ids-file", help="scan ids, one per line: the run's scope (writes the cohort's volumes csv)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--tag", default="full", help="work-folder name; checks use their own tag")
    ap.add_argument("--skip-done", action="store_true", help="leave out scans whose label map exists")
    a = ap.parse_args(argv)
    scoped = a.ids_file is not None
    ids = (Path(a.ids_file).read_text().split() if scoped else a.ids or all_ids(a.cohort)[: a.limit])
    if a.skip_done:
        ids = [i for i in ids if not out_path(a.cohort, i).exists()]
    shards = [ids[k::a.gpus] for k in range(a.gpus) if ids[k::a.gpus]]
    root = WORK / a.cohort / a.tag
    if root.exists():
        shutil.rmtree(root)

    def job(k):
        d = root / f"gpu{k}"
        names = stage(a.cohort, shards[k], d)
        secs = run_container(d, a.gpu0 + k)
        rows = collect(a.cohort, names, d)
        print(f"gpu{k}: {len(rows)} scans in {secs:.0f} s", flush=True)
        return rows, secs, len(rows)

    with ThreadPoolExecutor(len(shards)) as ex:
        res = list(ex.map(job, range(len(shards))))
    df = pd.DataFrame([r for rows, _, _ in res for r in rows])
    full = scoped or (a.ids is None and a.limit is None)
    f = OUT / (f"volumes_brats24_{a.cohort}.csv" if full else f"check_brats24_{a.cohort}_{a.tag}.csv")
    f.parent.mkdir(parents=True, exist_ok=True)
    if full and a.skip_done and f.exists():
        df = pd.concat([pd.read_csv(f), df]).drop_duplicates("scan_id", keep="last")
    df.to_csv(f, index=False)
    with open(root / "timing.json", "w") as fh:
        json.dump([{"gpu": k, "scans": n, "seconds": s} for k, (_, s, n) in enumerate(res)], fh)
    print(df.drop(columns=[c for c in df.columns if c.endswith("voxels")]).describe().round(3).to_string())


if __name__ == "__main__":
    main()
