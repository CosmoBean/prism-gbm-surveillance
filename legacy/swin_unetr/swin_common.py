"""Shared pieces for BraTS-pretrained SwinUNETR fine-tuning on MU-Glioma-Post."""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import torch
from monai.networks.nets import SwinUNETR

REPO = Path(__file__).resolve().parents[1]
SWIN_DIR = REPO / "SWIN UNetR"
DATASET_ROOT = REPO / "mu-glioma-post-raw" / "MU-Glioma-Post"
PRETRAINED = SWIN_DIR / "pretrained" / "fold1_f48_ep300_4gpu_dice0_9059" / "model.pt"
# Held-out patients of the radiomics model; fusion test rows come from these patients.
TEST_PATIENTS_FILE = REPO / "radiomics" / "results" / "calibrated_forward_hybrid" / "test_patients.txt"
FUSION_INPUTS = REPO / "reproduction" / "fusion_inputs"

# BraTS21 SwinUNETR input order (brats21_folds.json): flair, t1ce, t1, t2.
MU_CHANNELS = ("t2f", "t1c", "t1n", "t2w")
# MU-Glioma-Post mask labels, confirmed by zero-shot BraTS ET overlapping label 3 (zero_shot_check.py).
LABEL_NETC, LABEL_SNFH, LABEL_ET, LABEL_RC = 1, 2, 3, 4
OUTPUT_CHANNELS = ("TC", "WT", "ET", "RC")
ROI = (128, 128, 128)


def test_patients() -> set[str]:
    return set(TEST_PATIENTS_FILE.read_text().split())


def list_cases(dataset_root: Path = DATASET_ROOT) -> pd.DataFrame:
    rows = []
    for tp in sorted(dataset_root.glob("PatientID_*/Timepoint_*")):
        stem = f"{tp.parent.name}_{tp.name}"
        images = [tp / f"{stem}_brain_{c}.nii.gz" for c in MU_CHANNELS]
        mask = tp / f"{stem}_tumorMask.nii.gz"
        if all(p.exists() for p in images) and mask.exists():
            rows.append({
                "patient_id": tp.parent.name,
                "timepoint": tp.name,
                "image": [str(p) for p in images],
                "label": str(mask),
            })
    return pd.DataFrame(rows)


def mask_to_channels(mask: np.ndarray) -> np.ndarray:
    """MU labels -> overlapping BraTS-style channels plus resection cavity."""
    return np.stack([
        np.isin(mask, (LABEL_NETC, LABEL_ET)),               # TC
        np.isin(mask, (LABEL_NETC, LABEL_SNFH, LABEL_ET)),   # WT
        mask == LABEL_ET,                                     # ET
        mask == LABEL_RC,                                     # RC
    ]).astype(np.float32)


def load_normalized(image_paths: list[str]) -> np.ndarray:
    """Stack channels and z-score nonzero voxels per channel (BraTS21 NormalizeIntensityd)."""
    img = np.stack([nib.load(p).get_fdata(dtype=np.float32) for p in image_paths])
    for c in range(img.shape[0]):
        nz = img[c] != 0
        if nz.any():
            v = img[c][nz]
            img[c][nz] = (v - v.mean()) / (v.std() + 1e-8)
    return img


def lesion_centered_crop(img: np.ndarray, mask: np.ndarray, roi=ROI) -> np.ndarray:
    """Native-resolution ROI crop centered on the lesion (labels 1-4), zero-padded at borders."""
    coords = np.argwhere(mask > 0)
    center = (coords.min(0) + coords.max(0)) // 2 if len(coords) else np.array(mask.shape) // 2
    out = np.zeros((img.shape[0], *roi), dtype=img.dtype)
    src, dst = [], []
    for d in range(3):
        start = int(center[d]) - roi[d] // 2
        s0, s1 = max(start, 0), min(start + roi[d], mask.shape[d])
        src.append(slice(s0, s1))
        dst.append(slice(s0 - start, s1 - start))
    out[(slice(None), *dst)] = img[(slice(None), *src)]
    return out


def build_seg_model(out_channels: int = 4, pretrained: bool = True, use_checkpoint: bool = True) -> SwinUNETR:
    """SwinUNETR with BraTS21 weights; TC/WT/ET heads copied, RC head newly initialized."""
    model = SwinUNETR(in_channels=4, out_channels=out_channels, feature_size=48, use_checkpoint=use_checkpoint)
    if pretrained:
        state = torch.load(PRETRAINED, map_location="cpu", weights_only=False)["state_dict"]
        own = model.state_dict()
        for key, value in state.items():
            if key.startswith("out.") and own[key].shape != value.shape:
                own[key][: value.shape[0]] = value
            else:
                own[key] = value
        model.load_state_dict(own)
    return model


POOL_STAGES = (2, 3, 4)  # swinViT hidden states at 16^3 (192 ch), 8^3 (384 ch), 4^3 (768 ch) for a 128^3 input
POOLED_DIM = 2 * (192 + 384 + 768)


def lesion_pooled_features(hidden: list[torch.Tensor], lesion: torch.Tensor) -> torch.Tensor:
    """Per stage: mean over lesion voxels and mean over the whole crop, concatenated.

    Global average pooling of the deepest stage alone is nearly identical across scans
    (scan-to-scan correlation ~1.0), so lesion-restricted pooling at several scales is used.
    `lesion` is (B, 1, 128, 128, 128) in {0, 1}.
    """
    feats = []
    for s in POOL_STAGES:
        h = hidden[s]
        w = torch.nn.functional.adaptive_avg_pool3d(lesion.float(), h.shape[2:])  # lesion fraction per token
        lesion_mean = (h * w).sum((2, 3, 4)) / w.sum((2, 3, 4)).clamp(min=1e-6)
        feats += [lesion_mean, h.mean((2, 3, 4))]
    return torch.cat(feats, dim=1)


class SwinProgressionClassifier(torch.nn.Module):
    """SwinUNETR encoder + lesion-masked multi-scale pooling + BatchNorm + linear head.

    BatchNorm standardizes each pooled feature across scans; the raw pooled features share a
    large common component (scan-to-scan correlation ~0.99) that otherwise swamps the head.
    """

    def __init__(self, seg_model: SwinUNETR, dropout: float = 0.3):
        super().__init__()
        self.swinViT = seg_model.swinViT
        self.norm = torch.nn.BatchNorm1d(POOLED_DIM)
        self.head = torch.nn.Sequential(torch.nn.Dropout(dropout), torch.nn.Linear(POOLED_DIM, 1))

    def embed(self, x: torch.Tensor, lesion: torch.Tensor) -> torch.Tensor:
        hidden = self.swinViT(x, normalize=True)
        return self.norm(lesion_pooled_features([h.float() for h in hidden], lesion))

    def forward(self, x: torch.Tensor, lesion: torch.Tensor) -> torch.Tensor:
        return self.head(self.embed(x, lesion))
