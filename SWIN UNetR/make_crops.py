#!/usr/bin/env python3
"""Cache 144^3 lesion-centered, BraTS-normalized crops for every fusion-cohort scan (train + test)."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

from swin_common import DATASET_ROOT, FUSION_INPUTS, MU_CHANNELS, SWIN_DIR, lesion_centered_crop, load_normalized

CROP = (144, 144, 144)


def crop_one(job: tuple[str, str, str]) -> str:
    pid, tp, out_dir = job
    out = Path(out_dir) / f"{pid}_{tp}.npy"
    mask_out = Path(out_dir) / f"{pid}_{tp}_mask.npy"
    if out.exists() and mask_out.exists():
        return out.name
    d = DATASET_ROOT / pid / tp
    stem = f"{pid}_{tp}"
    img = load_normalized([str(d / f"{stem}_brain_{c}.nii.gz") for c in MU_CHANNELS])
    mask = np.rint(nib.load(d / f"{stem}_tumorMask.nii.gz").get_fdata()).astype(np.int16)
    np.save(out, lesion_centered_crop(img, mask, CROP).astype(np.float16))
    np.save(mask_out, lesion_centered_crop(mask[None], mask, CROP)[0].astype(np.uint8))
    return out.name


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", type=Path, default=SWIN_DIR / "runs" / "crops")
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    rows = pd.concat([pd.read_csv(FUSION_INPUTS / f"{s}_predictions.csv") for s in ("train", "test")])
    jobs = [(r.patient_id, r.timepoint, str(a.output_dir)) for r in rows.itertuples()]
    with ProcessPoolExecutor(a.workers) as ex:
        done = list(ex.map(crop_one, jobs))
    print(f"cached {len(done)} crops in {a.output_dir}")


if __name__ == "__main__":
    main()
