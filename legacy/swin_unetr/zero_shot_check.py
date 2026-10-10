#!/usr/bin/env python3
"""Sanity-check BraTS21-pretrained SwinUNETR on MU-Glioma-Post before fine-tuning.

Runs zero-shot segmentation and reports Dice of each BraTS output channel (TC, WT, ET)
against each MU mask label, to verify channel order / normalization and the label mapping.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
from monai.inferers import sliding_window_inference
from monai.networks.nets import SwinUNETR

# BraTS21 training order (brats21_folds.json): flair, t1ce, t1, t2
MU_CHANNELS = ["t2f", "t1c", "t1n", "t2w"]
WEIGHTS = Path(__file__).parent / "pretrained/fold1_f48_ep300_4gpu_dice0_9059/model.pt"


def load_case(tp_dir: Path) -> tuple[torch.Tensor, np.ndarray]:
    name = f"{tp_dir.parent.name}_{tp_dir.name}"
    vols = [nib.load(tp_dir / f"{name}_brain_{c}.nii.gz").get_fdata().astype(np.float32) for c in MU_CHANNELS]
    img = np.stack(vols)
    for c in range(4):  # NormalizeIntensityd(nonzero=True, channel_wise=True)
        nz = img[c] != 0
        img[c][nz] = (img[c][nz] - img[c][nz].mean()) / (img[c][nz].std() + 1e-8)
    mask = np.rint(nib.load(tp_dir / f"{name}_tumorMask.nii.gz").get_fdata()).astype(np.int16)
    return torch.from_numpy(img)[None], mask


def dice(a: np.ndarray, b: np.ndarray) -> float:
    s = a.sum() + b.sum()
    return float("nan") if s == 0 else 2.0 * (a & b).sum() / s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset-root", default="mu-glioma-post-raw/MU-Glioma-Post")
    ap.add_argument("--n", type=int, default=40)
    a = ap.parse_args()

    model = SwinUNETR(in_channels=4, out_channels=3, feature_size=48)
    model.load_state_dict(torch.load(WEIGHTS, map_location="cpu", weights_only=False)["state_dict"])
    model = model.cuda().eval()

    cases = sorted(p for p in Path(a.dataset_root).glob("PatientID_*/Timepoint_*") if (p / f"{p.parent.name}_{p.name}_tumorMask.nii.gz").exists())
    random.Random(0).shuffle(cases)
    rows = []
    for tp in cases[: a.n]:
        img, mask = load_case(tp)
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
            logits = sliding_window_inference(img.cuda(), (128, 128, 128), 4, model, overlap=0.5)
        pred = (torch.sigmoid(logits.float())[0] > 0.5).cpu().numpy()  # TC, WT, ET
        row = {}
        for ci, cname in enumerate(("TC", "WT", "ET")):
            for lab in (1, 2, 3, 4):
                row[f"{cname}~L{lab}"] = dice(pred[ci], mask == lab)
        row["WT~L123"] = dice(pred[1], np.isin(mask, (1, 2, 3)))
        row["voxels"] = {lab: int((mask == lab).sum()) for lab in (1, 2, 3, 4)}
        rows.append(row)
    import pandas as pd
    df = pd.DataFrame(rows)
    print(f"{len(df)} scans; mean voxel counts per label:", pd.DataFrame(list(df.voxels)).mean().round(0).to_dict())
    print(df.drop(columns="voxels").median().round(3).to_string())


if __name__ == "__main__":
    main()
