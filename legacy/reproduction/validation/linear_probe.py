#!/usr/bin/env python3
"""Image-only signal of an embedding folder: L2 logistic probe (C tuned by inner patient-grouped CV).

Reports outer patient-grouped CV AUC on the training cohort and test AUC of a probe fit on all training rows.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegressionCV
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

REPO = Path(__file__).resolve().parents[2]


def probe(X: np.ndarray, y: np.ndarray, g: np.ndarray):
    folds = list(GroupKFold(5).split(X, y, g))
    return make_pipeline(StandardScaler(), LogisticRegressionCV(Cs=10, cv=folds, scoring="roc_auc", max_iter=5000)).fit(X, y)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("embedding_dirs", nargs="+")
    ap.add_argument("--inputs-dir", default=str(REPO / "reproduction" / "fusion_inputs"))
    a = ap.parse_args()
    tr, te = (pd.read_csv(Path(a.inputs_dir) / f"{s}_predictions.csv") for s in ("train", "test"))
    for d in a.embedding_dirs:
        E = lambda df: np.stack([torch.load(Path(d) / f"{r.patient_id}_{r.timepoint}_embedding.pt").view(-1).numpy() for r in df.itertuples()])
        Xtr, Xte, y, g = E(tr), E(te), tr.label.values, tr.patient_id.values
        oof = np.zeros(len(tr))
        for fit_idx, val_idx in GroupKFold(5).split(Xtr, y, g):
            oof[val_idx] = probe(Xtr[fit_idx], y[fit_idx], g[fit_idx]).predict_proba(Xtr[val_idx])[:, 1]
        test_auc = roc_auc_score(te.label, probe(Xtr, y, g).predict_proba(Xte)[:, 1])
        print(f"{Path(d).name:28s} dim {Xtr.shape[1]:4d} | train grouped-CV AUC {roc_auc_score(y, oof):.3f} | test AUC {test_auc:.3f}")


if __name__ == "__main__":
    main()
