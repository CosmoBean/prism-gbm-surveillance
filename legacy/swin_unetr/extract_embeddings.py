#!/usr/bin/env python3
"""Local re-run of swinunetr-pipeline-kaggle.ipynb (cells 3, 6, 7, 9).

Same seed order, preprocessing, and random-init encoder as the notebook, but reads
the raw MU-Glioma-Post tree from disk instead of Google Drive. Writes one
{PatientID}_{Timepoint}_embedding.pt (shape (1, 48)) per complete scan.
"""

from __future__ import annotations

import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
import torch.nn as nn
from scipy.ndimage import zoom

TARGET_SIZE = (128, 128, 128)
# Notebook channel order (cell 5): t1c, t1n, t2f, t2w
MODALITIES = ["t1c", "t1n", "t2f", "t2w"]


# CELL 6
def preprocess_from_local_paths(image_paths, mask_path):
    vols = []
    for path in image_paths:
        vols.append(nib.load(path).get_fdata().astype(np.float32))
    image = np.stack(vols, axis=0)

    mask = nib.load(mask_path).get_fdata().astype(np.float32)

    for c in range(image.shape[0]):
        p1, p99 = np.percentile(image[c], 1), np.percentile(image[c], 99)
        image[c] = np.clip((image[c] - p1) / (p99 - p1 + 1e-8), 0, 1)

    nz = np.argwhere(mask > 0)
    if len(nz) > 0:
        margin = 10
        mins = np.maximum(nz.min(axis=0) - margin, 0)
        maxs = np.minimum(nz.max(axis=0) + margin + 1, np.array(mask.shape))
        image = image[:, mins[0]:maxs[0], mins[1]:maxs[1], mins[2]:maxs[2]]
        mask = mask[mins[0]:maxs[0], mins[1]:maxs[1], mins[2]:maxs[2]]

    scale = [TARGET_SIZE[i] / image.shape[i + 1] for i in range(3)]
    resized = np.stack([zoom(image[c], scale, order=1) for c in range(4)], axis=0)
    mask_resized = zoom(mask, scale, order=0)

    return (
        torch.tensor(resized, dtype=torch.float32),
        torch.tensor(mask_resized, dtype=torch.float32).unsqueeze(0),
    )


# CELL 7
class PatchEmbed3D(nn.Module):
    def __init__(self, patch_size=4, in_channels=4, embed_dim=48):
        super().__init__()
        self.proj = nn.Conv3d(in_channels, embed_dim, kernel_size=patch_size, stride=patch_size)
        self.norm = nn.LayerNorm(embed_dim)

    def forward(self, x):
        x = self.proj(x)
        x = x.flatten(2).transpose(1, 2)
        return self.norm(x)


class SwinEncoder3D(nn.Module):
    def __init__(self, in_channels=4, embed_dim=48, patch_size=4):
        super().__init__()
        self.patch_embed = PatchEmbed3D(patch_size, in_channels, embed_dim)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=3,
            dim_feedforward=embed_dim * 4,
            dropout=0.0,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=4)
        self.norm = nn.LayerNorm(embed_dim)

    def forward(self, x):
        x = self.patch_embed(x)
        x = self.transformer(x)
        x = self.norm(x)
        return x.mean(dim=1), x


# The shipped embeddings come from the third SwinEncoder3D built after seeding (cell 7 was
# run three times in the original session). Build index 2 reproduces MLPFusion's
# unified_fusion_results.csv to 4 decimals with the shipped best_fusion_model.pth.
MODEL_BUILD_INDEX = 2


def build_model(device: str, build_index: int = MODEL_BUILD_INDEX) -> SwinEncoder3D:
    torch.manual_seed(42)
    np.random.seed(42)
    for _ in range(build_index):
        SwinEncoder3D(in_channels=4, embed_dim=48, patch_size=4)
    return SwinEncoder3D(in_channels=4, embed_dim=48, patch_size=4).to(device).eval()


def find_scans(dataset_root: Path) -> tuple[list[dict], int]:
    scans, skipped = [], 0
    for patient_dir in sorted(p for p in dataset_root.iterdir() if p.is_dir()):
        for tp_dir in sorted(p for p in patient_dir.iterdir() if p.is_dir()):
            names = [f.name for f in tp_dir.glob("*.nii*")]
            images = [next((n for n in names if m in n), None) for m in MODALITIES]
            mask = next((n for n in names if "tumorMask" in n), None)
            if all(images) and mask:
                scans.append(
                    {
                        "patient": patient_dir.name,
                        "timepoint": tp_dir.name,
                        "images": [str(tp_dir / n) for n in images],
                        "mask": str(tp_dir / mask),
                    }
                )
            else:
                skipped += 1
    return scans, skipped


_MODEL: SwinEncoder3D | None = None
_DEVICE = "cpu"


def _init_worker(device: str, threads: int, build_index: int) -> None:
    global _MODEL, _DEVICE
    torch.set_num_threads(threads)
    _DEVICE = device
    _MODEL = build_model(device, build_index)


def _embed(scan: dict, output_dir: str) -> str:
    out_path = Path(output_dir) / f"{scan['patient']}_{scan['timepoint']}_embedding.pt"
    if out_path.exists():
        return f"skip {out_path.name}"
    img_tensor, _ = preprocess_from_local_paths(scan["images"], scan["mask"])
    with torch.no_grad():
        embedding, _ = _MODEL(img_tensor.unsqueeze(0).to(_DEVICE))
    torch.save(embedding.cpu(), out_path)
    return f"done {out_path.name}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=Path("mu-glioma-post-raw/MU-Glioma-Post"))
    parser.add_argument("--output-dir", type=Path, default=Path("SWIN UNetR/embeddings_all"))
    parser.add_argument("--device", default="cpu", help="cpu (matches the original Kaggle run) or cuda[:N]")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--threads-per-worker", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--model-build-index",
        type=int,
        default=MODEL_BUILD_INDEX,
        help="Which model built after seeding to use (0 = first build).",
    )
    args = parser.parse_args()

    scans, skipped = find_scans(args.dataset_root)
    print(f"Total scans ready: {len(scans)}  Skipped (missing files): {skipped}", flush=True)
    if args.limit:
        scans = scans[: args.limit]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with ProcessPoolExecutor(
        max_workers=args.workers,
        initializer=_init_worker,
        initargs=(args.device, args.threads_per_worker, args.model_build_index),
    ) as pool:
        futures = [pool.submit(_embed, s, str(args.output_dir)) for s in scans]
        for i, fut in enumerate(as_completed(futures), start=1):
            print(f"[{i}/{len(scans)}] {fut.result()}", flush=True)


if __name__ == "__main__":
    os.environ.setdefault("OMP_NUM_THREADS", "4")
    main()
