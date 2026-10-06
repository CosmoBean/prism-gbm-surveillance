#!/usr/bin/env python3
"""Stage 2: fine-tune the SwinUNETR encoder + linear head on the 120-day progression label.

One invocation trains one job:
  --fold k   train on the other CV folds' patients, predict fold k  (out-of-fold rows for fusion)
  --fold full  train on all training patients, predict the held-out test patients

Folds are patient-grouped and stratified. Epochs are fixed up front (no early stopping on the
predicted fold), so out-of-fold predictions never see their own labels.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from swin_common import FUSION_INPUTS, ROI, SWIN_DIR, SwinProgressionClassifier, build_seg_model

CROPS = SWIN_DIR / "runs" / "crops"


def assign_folds(train: pd.DataFrame, n_folds: int, seed: int) -> np.ndarray:
    folds = np.full(len(train), -1)
    sgkf = StratifiedGroupKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    for k, (_, idx) in enumerate(sgkf.split(train, train.label, train.patient_id)):
        folds[idx] = k
    return folds


def load_crops(df: pd.DataFrame) -> torch.Tensor:
    return torch.stack([torch.from_numpy(np.load(CROPS / f"{r.patient_id}_{r.timepoint}.npy")) for r in df.itertuples()])


def load_lesion_masks(df: pd.DataFrame) -> torch.Tensor:
    """(N, 1, 144, 144, 144) binary tumor masks (labels 1-3) aligned with load_crops."""
    return torch.stack([torch.from_numpy(np.isin(np.load(CROPS / f"{r.patient_id}_{r.timepoint}_mask.npy"), (1, 2, 3)))[None]
                        for r in df.itertuples()])


def random_view(x: torch.Tensor, m: torch.Tensor, gen: torch.Generator) -> tuple[torch.Tensor, torch.Tensor]:
    """Random 128^3 window of the 144^3 crop, random flips (image + mask), intensity scale/shift (BraTS21-style)."""
    xs, ms = [], []
    for v, w in zip(x, m):
        o = [int(torch.randint(0, v.shape[d + 1] - ROI[d] + 1, (1,), generator=gen)) for d in range(3)]
        win = (slice(None), slice(o[0], o[0] + ROI[0]), slice(o[1], o[1] + ROI[1]), slice(o[2], o[2] + ROI[2]))
        v, w = v[win], w[win]
        for d in (1, 2, 3):
            if torch.rand(1, generator=gen) < 0.5:
                v, w = v.flip(d), w.flip(d)
        nz = v != 0
        scale = 1 + (torch.rand(4, 1, 1, 1, generator=gen) * 0.2 - 0.1)
        shift = torch.rand(4, 1, 1, 1, generator=gen) * 0.2 - 0.1
        xs.append(torch.where(nz, v * scale + shift, v))
        ms.append(w)
    return torch.stack(xs), torch.stack(ms)


def center_view(x: torch.Tensor) -> torch.Tensor:
    o = [(x.shape[d + 2] - ROI[d]) // 2 for d in range(3)]
    return x[:, :, o[0]:o[0] + ROI[0], o[1]:o[1] + ROI[1], o[2]:o[2] + ROI[2]]


@torch.no_grad()
def predict(model, x: torch.Tensor, m: torch.Tensor, device, batch: int = 8) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    probs, embs = [], []
    for i in range(0, len(x), batch):
        xb, mb = center_view(x[i:i + batch]).to(device).float(), center_view(m[i:i + batch]).to(device)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            e = model.embed(xb, mb)
            logit = model.head(e)
        probs.append(torch.sigmoid(logit.float()).squeeze(1).cpu())
        embs.append(e.float().cpu())
    return torch.cat(probs).numpy(), torch.cat(embs).numpy()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fold", required=True, help="0..n_folds-1 or 'full'")
    ap.add_argument("--init", default="seg", choices=["seg", "pretrained"])
    ap.add_argument("--seg-checkpoint", type=Path, default=SWIN_DIR / "runs" / "seg" / "best.pt")
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--lr-encoder", type=float, default=1e-5)
    ap.add_argument("--lr-head", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--threads", type=int, default=8, help="CPU threads (augmentation runs on CPU)")
    a = ap.parse_args()

    torch.set_num_threads(a.threads)
    torch.manual_seed(a.seed)
    device = torch.device(a.device)
    train = pd.read_csv(FUSION_INPUTS / "train_predictions.csv")
    test = pd.read_csv(FUSION_INPUTS / "test_predictions.csv")
    train["fold"] = assign_folds(train, a.n_folds, a.seed)
    if a.fold == "full":
        fit_df, pred_df = train, test
    else:
        k = int(a.fold)
        fit_df, pred_df = train[train.fold != k], train[train.fold == k]
    assert not set(fit_df.patient_id) & set(pred_df.patient_id), "patient leakage between fit and predict sets"

    seg = build_seg_model(pretrained=True, use_checkpoint=True)
    if a.init == "seg":
        seg.load_state_dict(torch.load(a.seg_checkpoint, map_location="cpu", weights_only=False)["model"])
    model = SwinProgressionClassifier(seg).to(device)
    opt = torch.optim.AdamW([
        {"params": model.swinViT.parameters(), "lr": a.lr_encoder},
        {"params": list(model.norm.parameters()) + list(model.head.parameters()), "lr": a.lr_head},
    ], weight_decay=1e-2)
    steps = a.epochs * int(np.ceil(len(fit_df) / a.batch_size))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[a.lr_encoder, a.lr_head], total_steps=steps, pct_start=0.1)
    pos = fit_df.label.mean()
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor((1 - pos) / pos, device=device))

    x_fit, m_fit, y_fit = load_crops(fit_df), load_lesion_masks(fit_df), torch.tensor(fit_df.label.values, dtype=torch.float32)
    x_pred, m_pred = load_crops(pred_df), load_lesion_masks(pred_df)
    gen = torch.Generator().manual_seed(a.seed)
    history = []
    for epoch in range(a.epochs):
        model.train()
        order = torch.randperm(len(x_fit), generator=gen)
        order = order[: len(order) - len(order) % 2] if len(order) % a.batch_size == 1 else order  # BatchNorm needs >1 sample
        total = 0.0
        for i in range(0, len(order), a.batch_size):
            b = order[i:i + a.batch_size]
            xb, mb = random_view(x_fit[b].float(), m_fit[b], gen)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logit = model(xb.to(device), mb.to(device)).float().squeeze(1)
            loss = loss_fn(logit, y_fit[b].to(device))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
            total += loss.item() * len(b)
        history.append({"epoch": epoch + 1, "train_loss": total / len(x_fit)})

    probs, embs = predict(model, x_pred, m_pred, device)
    a.output_dir.mkdir(parents=True, exist_ok=True)
    out = pred_df[["patient_id", "timepoint", "label"]].copy()
    out["image_prob"] = probs
    out.to_csv(a.output_dir / f"pred_{a.fold}.csv", index=False)
    np.save(a.output_dir / f"emb_{a.fold}.npy", embs)
    summary = {"fold": a.fold, "init": a.init, "n_fit": len(fit_df), "n_pred": len(pred_df),
               "pred_auc": float(roc_auc_score(out.label, probs)) if out.label.nunique() == 2 else None,
               "history": history}
    (a.output_dir / f"summary_{a.fold}.json").write_text(json.dumps(summary, indent=2))
    torch.save(model.state_dict(), a.output_dir / f"model_{a.fold}.pt")
    print(json.dumps({k: v for k, v in summary.items() if k != "history"}), flush=True)


if __name__ == "__main__":
    main()
