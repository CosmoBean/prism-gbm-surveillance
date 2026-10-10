#!/usr/bin/env python3
"""Write SwinUNETR features as {PatientID}_{Timepoint}_embedding.pt (shape (1, D)) for MLPFusion.

  --source pretrained   BraTS21 encoder, lesion-masked + global pooling at 3 Swin stages (no MU training)
  --source seg          stage-1 segmentation-fine-tuned encoder, same pooling
  --source stage2       stage-2 progression model: out-of-fold rows for train, full model for test
                        (writes 768-d embeddings and, under <out>_prob, the 1-d image probability)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from finetune_progression import center_view, load_crops, load_lesion_masks
from swin_common import FUSION_INPUTS, SWIN_DIR, build_seg_model, lesion_pooled_features


def save(df: pd.DataFrame, values: np.ndarray, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for r, v in zip(df.itertuples(), values):
        torch.save(torch.tensor(np.asarray(v, dtype=np.float32)).view(1, -1), out_dir / f"{r.patient_id}_{r.timepoint}_embedding.pt")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, choices=["pretrained", "seg", "stage2"])
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--seg-checkpoint", type=Path, default=SWIN_DIR / "runs" / "seg" / "best.pt")
    ap.add_argument("--stage2-dir", type=Path, default=SWIN_DIR / "runs" / "progression")
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--device", default="cuda:0")
    a = ap.parse_args()
    rows = pd.concat([pd.read_csv(FUSION_INPUTS / f"{s}_predictions.csv") for s in ("train", "test")], ignore_index=True)

    if a.source == "stage2":
        parts, probs = [], []
        for k in [*map(str, range(a.n_folds)), "full"]:
            pred = pd.read_csv(a.stage2_dir / f"pred_{k}.csv")
            pred["emb"] = list(np.load(a.stage2_dir / f"emb_{k}.npy"))
            parts.append(pred)
        allp = pd.concat(parts, ignore_index=True)
        assert allp.duplicated(["patient_id", "timepoint"]).sum() == 0
        allp = rows[["patient_id", "timepoint"]].merge(allp, on=["patient_id", "timepoint"], validate="one_to_one")
        save(allp, np.stack(allp.emb), a.output_dir)
        save(allp, allp.image_prob.values[:, None], Path(f"{a.output_dir}_prob"))
        allp[["patient_id", "timepoint", "label", "image_prob"]].to_csv(f"{a.output_dir}_image_probs.csv", index=False)
        print(f"wrote {len(allp)} stage-2 embeddings ({np.stack(allp.emb).shape[1]}-d) and image probabilities")
        return

    seg = build_seg_model(pretrained=True, use_checkpoint=False)
    if a.source == "seg":
        seg.load_state_dict(torch.load(a.seg_checkpoint, map_location="cpu", weights_only=False)["model"])
    vit = seg.swinViT.to(a.device).eval()
    x, m = load_crops(rows), load_lesion_masks(rows)
    embs = []
    with torch.no_grad():
        for i in range(0, len(x), 8):
            with torch.autocast(torch.device(a.device).type, dtype=torch.bfloat16):
                hidden = [h.float() for h in vit(center_view(x[i:i + 8]).to(a.device).float(), normalize=True)]
            embs.append(lesion_pooled_features(hidden, center_view(m[i:i + 8]).to(a.device)).cpu())
    feats = torch.cat(embs).numpy()
    save(rows, feats, a.output_dir)
    print(f"wrote {len(rows)} {a.source} lesion-pooled embeddings ({feats.shape[1]}-d) to {a.output_dir}")


if __name__ == "__main__":
    main()
