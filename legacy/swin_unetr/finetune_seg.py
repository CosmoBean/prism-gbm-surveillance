#!/usr/bin/env python3
"""Stage 1: fine-tune BraTS21-pretrained SwinUNETR for MU-Glioma-Post segmentation (DDP).

Outputs TC / WT / ET (BraTS heads, kept) + RC (new resection-cavity head). Patients held out
by the radiomics/fusion test split are excluded entirely; a patient-grouped validation split
of the remaining patients selects the best checkpoint.

    torchrun --nproc_per_node=4 "SWIN UNetR/finetune_seg.py" --output-dir "SWIN UNetR/runs/seg"
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

import numpy as np
import torch
import torch.distributed as dist
from monai.data import CacheDataset, DataLoader, list_data_collate, partition_dataset
from monai.inferers import sliding_window_inference
from monai.losses import DiceLoss
from monai.transforms import (
    Compose,
    MapTransform,
    RandCropByPosNegLabeld,
    RandFlipd,
    RandScaleIntensityd,
    RandShiftIntensityd,
)

import nibabel as nib

from swin_common import OUTPUT_CHANNELS, ROI, build_seg_model, list_cases, load_normalized, mask_to_channels, test_patients


class LoadCase(MapTransform):
    """Load + normalize the 4 channels, build target channels, crop to the brain bounding box."""

    def __init__(self):
        super().__init__(keys=["image", "label"])

    def __call__(self, data):
        img = load_normalized(data["image"])
        mask = np.rint(nib.load(data["label"]).get_fdata()).astype(np.int16)
        brain = np.argwhere((img != 0).any(axis=0))
        lo, hi = brain.min(0), brain.max(0) + 1
        sl = tuple(slice(a, b) for a, b in zip(lo, hi))
        img, mask = img[(slice(None), *sl)], mask[sl]
        # Some brains are narrower than the ROI along an axis; zero-pad so 128^3 crops always fit.
        pad = [(max(0, r - s) // 2, max(0, r - s) - max(0, r - s) // 2) for r, s in zip(ROI, mask.shape)]
        img, mask = np.pad(img, [(0, 0), *pad]), np.pad(mask, pad)
        return {
            "image": torch.from_numpy(np.ascontiguousarray(img)),
            "label": torch.from_numpy(mask_to_channels(mask)).to(torch.uint8),
            "fg": torch.from_numpy((mask > 0)[None].astype(np.uint8)),
            "id": f"{data['patient_id']}_{data['timepoint']}",
        }


def train_transforms(samples: int) -> Compose:
    return Compose([
        LoadCase(),
        RandCropByPosNegLabeld(keys=["image", "label"], label_key="fg", spatial_size=ROI, pos=2, neg=1,
                               num_samples=samples, image_key="image", image_threshold=0, allow_smaller=False),
        RandFlipd(keys=["image", "label"], prob=0.5, spatial_axis=0),
        RandFlipd(keys=["image", "label"], prob=0.5, spatial_axis=1),
        RandFlipd(keys=["image", "label"], prob=0.5, spatial_axis=2),
        RandScaleIntensityd(keys="image", factors=0.1, prob=1.0),
        RandShiftIntensityd(keys="image", offsets=0.1, prob=1.0),
    ])


def dice_sums(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Per-channel [2*intersection, pred+target] for one volume (channels first)."""
    p, t = pred.flatten(1).float(), target.flatten(1).float()
    return torch.stack([2 * (p * t).sum(1), p.sum(1) + t.sum(1)], dim=1)


@torch.no_grad()
def evaluate(model, loader, device) -> dict[str, float]:
    model.eval()
    per_case = []  # mean over cases of per-case Dice (nan-skip channels absent in both)
    for batch in loader:
        img = batch["image"].to(device)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = sliding_window_inference(img, ROI, 4, model, overlap=0.5)
        pred = (torch.sigmoid(logits.float()) > 0.5)[0]
        s = dice_sums(pred, batch["label"][0].to(device))
        per_case.append(torch.where(s[:, 1] > 0, s[:, 0] / s[:, 1].clamp(min=1), torch.full_like(s[:, 0], float("nan"))))
    stacked = torch.stack(per_case) if per_case else torch.zeros(0, len(OUTPUT_CHANNELS), device=device)
    sums = torch.stack([torch.nan_to_num(stacked, nan=0.0).sum(0), (~stacked.isnan()).float().sum(0)])
    dist.all_reduce(sums)
    dice = (sums[0] / sums[1].clamp(min=1)).tolist()
    model.train()
    out = {name: d for name, d in zip(OUTPUT_CHANNELS, dice)}
    out["mean"] = float(np.mean(dice))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--samples-per-volume", type=int, default=2)
    ap.add_argument("--val-fraction", type=float, default=0.15)
    ap.add_argument("--eval-every", type=int, default=5)
    ap.add_argument("--max-minutes", type=float, default=80.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cache-workers", type=int, default=12)
    ap.add_argument("--max-cases", type=int, default=None, help="Smoke testing: cap train/val scans")
    args = ap.parse_args()

    dist.init_process_group("nccl")
    rank, world = dist.get_rank(), dist.get_world_size()
    device = torch.device("cuda", int(os.environ["LOCAL_RANK"]))
    torch.cuda.set_device(device)
    torch.manual_seed(args.seed + rank)
    np.random.seed(args.seed + rank)
    log = (lambda *a: print(*a, flush=True)) if rank == 0 else (lambda *a: None)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    cases = list_cases()
    held_out = test_patients()
    cases = cases[~cases.patient_id.isin(held_out)]
    patients = np.array(sorted(cases.patient_id.unique()))
    rng = np.random.default_rng(args.seed)
    val_patients = set(rng.choice(patients, size=int(round(args.val_fraction * len(patients))), replace=False))
    train_cases = cases[~cases.patient_id.isin(val_patients)].to_dict("records")
    val_cases = cases[cases.patient_id.isin(val_patients)].to_dict("records")
    if args.max_cases:
        train_cases, val_cases = train_cases[: args.max_cases], val_cases[: max(4, args.max_cases // 4)]
    if rank == 0:
        (args.output_dir / "split.json").write_text(json.dumps({
            "excluded_test_patients": sorted(held_out), "val_patients": sorted(val_patients),
            "n_train_scans": len(train_cases), "n_val_scans": len(val_cases)}, indent=2))
    log(f"train scans {len(train_cases)} | val scans {len(val_cases)} | excluded test patients {len(held_out)}")

    my_train = partition_dataset(train_cases, num_partitions=world, shuffle=True, seed=args.seed, even_divisible=True)[rank]
    my_val = partition_dataset(val_cases, num_partitions=world, shuffle=False, even_divisible=False)[rank]
    train_ds = CacheDataset(my_train, train_transforms(args.samples_per_volume), cache_rate=1.0, num_workers=args.cache_workers, progress=False)
    val_ds = CacheDataset(my_val, Compose([LoadCase()]), cache_rate=1.0, num_workers=args.cache_workers, progress=False)
    train_loader = DataLoader(train_ds, batch_size=1, shuffle=True, num_workers=6, collate_fn=list_data_collate, persistent_workers=True)
    val_loader = DataLoader(val_ds, batch_size=1, num_workers=2)
    log("data cached")

    model = build_seg_model().to(device)
    model = torch.nn.parallel.DistributedDataParallel(model, device_ids=[device.index])
    dice_loss = DiceLoss(sigmoid=True, squared_pred=True, smooth_nr=0.0, smooth_dr=1e-6)
    bce = torch.nn.BCEWithLogitsLoss()
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)
    steps_per_epoch = len(train_loader)
    total = args.epochs * steps_per_epoch
    warmup = 2 * steps_per_epoch
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / warmup if s < warmup else 0.5 * (1 + math.cos(math.pi * (s - warmup) / max(1, total - warmup))))

    start_epoch, best, history = 0, -1.0, []
    last_path, best_path = args.output_dir / "last.pt", args.output_dir / "best.pt"
    if last_path.exists():
        ck = torch.load(last_path, map_location="cpu", weights_only=False)
        model.module.load_state_dict(ck["model"]); opt.load_state_dict(ck["opt"]); sched.load_state_dict(ck["sched"])
        start_epoch, best, history = ck["epoch"] + 1, ck["best"], ck["history"]
        log(f"resumed at epoch {start_epoch}, best {best:.4f}")
    else:
        zs = evaluate(model.module, val_loader, device)
        history.append({"epoch": 0, "val": zs, "note": "pretrained, before fine-tuning (RC head untrained)"})
        log(f"epoch 0 (pretrained) val dice {json.dumps({k: round(v, 4) for k, v in zs.items()})}")

    t0 = time.time()
    for epoch in range(start_epoch, args.epochs):
        model.train()
        running = 0.0
        for batch in train_loader:
            img, lab = batch["image"].to(device, non_blocking=True), batch["label"].to(device, non_blocking=True).float()
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logits = model(img)
            loss = dice_loss(logits.float(), lab) + bce(logits.float(), lab)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
            running += loss.item()
        loss_t = torch.tensor(running / steps_per_epoch, device=device)
        dist.all_reduce(loss_t)
        entry = {"epoch": epoch + 1, "train_loss": loss_t.item() / world, "lr": sched.get_last_lr()[0], "minutes": (time.time() - t0) / 60}
        out_of_time = (time.time() - t0) / 60 > args.max_minutes
        if (epoch + 1) % args.eval_every == 0 or epoch + 1 == args.epochs or out_of_time:
            entry["val"] = evaluate(model.module, val_loader, device)
            if rank == 0 and entry["val"]["mean"] > best:
                best = entry["val"]["mean"]
                torch.save({"model": model.module.state_dict(), "epoch": epoch + 1, "val": entry["val"]}, best_path)
        history.append(entry)
        if rank == 0:
            torch.save({"model": model.module.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(),
                        "epoch": epoch, "best": best, "history": history}, last_path)
            (args.output_dir / "history.json").write_text(json.dumps(history, indent=2))
        log(f"epoch {epoch + 1}/{args.epochs} loss {entry['train_loss']:.4f} {entry['minutes']:.1f} min"
            + (f" | val dice {json.dumps({k: round(v, 4) for k, v in entry['val'].items()})}" if "val" in entry else ""))
        if out_of_time:
            log(f"stopping: exceeded --max-minutes {args.max_minutes}")
            break
    dist.barrier()
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
