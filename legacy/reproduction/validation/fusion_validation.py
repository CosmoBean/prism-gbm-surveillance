#!/usr/bin/env python3
"""Fusion MLP validation: original vs leakage-free protocols, plus modality ablations.

Re-uses the model, loss and hyperparameters from MLPFusion/fusion_mlp.py (FocalLoss(0.7, 2),
Adam lr 1e-3 wd 1e-4, batch 16, 500 epochs, checkpoint check every 10 epochs).
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "MLPFusion"))

PROTOCOLS = {
    "A_test_loss_checkpoint": "original: keep weights with lowest TEST loss (checked every 10 epochs)",
    "B_final_epoch": "no peeking: weights after 500 epochs",
    "C_val_checkpoint": "keep weights with lowest loss on a patient-grouped 20% validation split of train",
    "D_score_only": "B, with vision embeddings zeroed",
    "E_shuffled_embeddings": "B, with embeddings permuted across scans",
    "F_vision_only": "B, with the radiomics score zeroed",
}


def load(inputs_dir: Path, emb_dir: Path):
    import torch
    out = {}
    for split in ("train", "test"):
        df = pd.read_csv(inputs_dir / f"{split}_predictions.csv")
        emb = torch.stack([torch.load(emb_dir / f"{r.patient_id}_{r.timepoint}_embedding.pt").view(-1) for r in df.itertuples()])
        out[split] = (df, emb, torch.tensor(df.progression_risk_probability.values, dtype=torch.float32)[:, None],
                      torch.tensor(df.label.values, dtype=torch.float32)[:, None])
    return out


def run(job):
    protocol, seed, inputs_dir, emb_dir = job
    import torch
    from sklearn.metrics import roc_auc_score
    from fusion_mlp import FocalLoss, MultimodalLateFusionMLP

    torch.set_num_threads(1)
    data = load(Path(inputs_dir), Path(emb_dir))
    tr_df, tr_e, tr_s, tr_y = data["train"]
    te_df, te_e, te_s, te_y = data["test"]
    g = torch.Generator().manual_seed(seed)
    rng = np.random.default_rng(seed)
    if protocol == "D_score_only":
        tr_e, te_e = torch.zeros_like(tr_e), torch.zeros_like(te_e)
    if protocol == "E_shuffled_embeddings":
        tr_e, te_e = tr_e[torch.randperm(len(tr_e), generator=g)], te_e[torch.randperm(len(te_e), generator=g)]
    if protocol == "F_vision_only":
        tr_s, te_s = torch.zeros_like(tr_s), torch.zeros_like(te_s)

    fit_idx = np.arange(len(tr_df))
    val_idx = np.array([], dtype=int)
    if protocol == "C_val_checkpoint":
        pats = tr_df.patient_id.unique()
        val_p = set(rng.choice(pats, size=int(round(0.2 * len(pats))), replace=False))
        is_val = tr_df.patient_id.isin(val_p).to_numpy()
        fit_idx, val_idx = np.where(~is_val)[0], np.where(is_val)[0]

    torch.manual_seed(seed)
    model = MultimodalLateFusionMLP(vision_dim=tr_e.shape[1])
    crit = FocalLoss(alpha=0.7, gamma=2.0)
    opt = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
    loss_of = lambda e, s, y: float(np.mean([crit(model(e[i:i + 16], s[i:i + 16]), y[i:i + 16]).item() for i in range(0, len(y), 16)]))
    best, best_state = float("inf"), None
    for epoch in range(500):
        model.train()
        perm = fit_idx[torch.randperm(len(fit_idx), generator=g).numpy()]
        for i in range(0, len(perm), 16):
            b = perm[i:i + 16]
            opt.zero_grad()
            crit(model(tr_e[b], tr_s[b]), tr_y[b]).backward()
            opt.step()
        if (epoch + 1) % 10 == 0 and protocol in ("A_test_loss_checkpoint", "C_val_checkpoint"):
            model.eval()
            with torch.no_grad():
                ref = loss_of(te_e, te_s, te_y) if protocol == "A_test_loss_checkpoint" else loss_of(tr_e[val_idx], tr_s[val_idx], tr_y[val_idx])
            if ref < best:
                best, best_state = ref, {k: v.clone() for k, v in model.state_dict().items()}
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        p = torch.sigmoid(model(te_e, te_s)).squeeze(1).numpy()
    y = te_y.squeeze(1).numpy()
    pred = (p >= 0.48).astype(int)
    tp, fp, fn = int(((pred == 1) & (y == 1)).sum()), int(((pred == 1) & (y == 0)).sum()), int(((pred == 0) & (y == 1)).sum())
    return {"protocol": protocol, "seed": seed, "auc": roc_auc_score(y, p), "acc@0.48": float((pred == y).mean()),
            "f1@0.48": 2 * tp / max(1, 2 * tp + fp + fn), "predictions": p.round(5).tolist()}


def logistic_stacker(inputs_dir: Path, emb_dir: Path) -> float:
    """L2 logistic regression on [radiomics score, embeddings]; C tuned by patient-grouped CV on train only."""
    from sklearn.linear_model import LogisticRegressionCV
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    data = load(inputs_dir, emb_dir)
    X = {k: np.hstack([v[2].numpy(), v[1].numpy()]) for k, v in data.items()}
    tr_df = data["train"][0]
    folds = list(GroupKFold(5).split(X["train"], tr_df.label, tr_df.patient_id))
    m = make_pipeline(StandardScaler(), LogisticRegressionCV(Cs=10, cv=folds, scoring="roc_auc", max_iter=5000))
    m.fit(X["train"], tr_df.label)
    return roc_auc_score(data["test"][0].label, m.predict_proba(X["test"])[:, 1])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs-dir", default=str(REPO / "reproduction" / "fusion_inputs"))
    ap.add_argument("--embeddings-dir", default=str(REPO / "SWIN UNetR" / "embeddings_all"))
    ap.add_argument("--output", default=str(REPO / "reproduction" / "validation" / "fusion_validation.csv"))
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--workers", type=int, default=64)
    ap.add_argument("--protocols", default=",".join(PROTOCOLS), help="Comma-separated subset of protocols")
    a = ap.parse_args()
    protocols = [p for p in a.protocols.split(",") if p]
    jobs = [(p, s, a.inputs_dir, a.embeddings_dir) for p in protocols for s in range(a.seeds)]
    with ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(run, jobs))
    df = pd.DataFrame(rows)
    df.to_csv(a.output, index=False)
    from sklearn.metrics import roc_auc_score
    te = pd.read_csv(Path(a.inputs_dir) / "test_predictions.csv")
    print(f"upstream radiomics score alone: test AUC {roc_auc_score(te.label, te.progression_risk_probability):.4f}")
    print(f"logistic stacker, score + embeddings (C by patient-grouped CV): test AUC {logistic_stacker(Path(a.inputs_dir), Path(a.embeddings_dir)):.4f}\n")
    summ = df.groupby("protocol")[["auc", "acc@0.48", "f1@0.48"]].agg(["mean", "std", "median"]).round(4)
    print(summ.to_string())
    for p in protocols:
        print(f"  {p}: {PROTOCOLS[p]}")


if __name__ == "__main__":
    main()
