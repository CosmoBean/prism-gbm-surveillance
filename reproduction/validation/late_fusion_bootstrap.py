#!/usr/bin/env python3
"""Two-feature logistic late fusion [radiomics score, image probability] vs radiomics score alone.

The stacker is fit on training rows only (radiomics OOF score + image OOF probability); test AUC
difference is bootstrapped by resampling test PATIENTS.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image_probs_csv", nargs="+")
    ap.add_argument("--inputs-dir", default=str(REPO / "reproduction" / "fusion_inputs"))
    ap.add_argument("--n-boot", type=int, default=5000)
    a = ap.parse_args()
    tr, te = (pd.read_csv(Path(a.inputs_dir) / f"{s}_predictions.csv") for s in ("train", "test"))
    for path in a.image_probs_csv:
        img = pd.read_csv(path)[["patient_id", "timepoint", "image_prob"]]
        dtr, dte = tr.merge(img, on=["patient_id", "timepoint"]), te.merge(img, on=["patient_id", "timepoint"])
        X = lambda d: np.column_stack([d.progression_risk_probability, d.image_prob])
        m = LogisticRegression(max_iter=1000).fit(X(dtr), dtr.label)
        fused, score, y = m.predict_proba(X(dte))[:, 1], dte.progression_risk_probability.values, dte.label.values
        rng = np.random.default_rng(0)
        groups = {p: np.where(dte.patient_id.values == p)[0] for p in dte.patient_id.unique()}
        pats = np.array(list(groups))
        diffs = []
        for _ in range(a.n_boot):
            idx = np.concatenate([groups[p] for p in rng.choice(pats, len(pats))])
            if len(np.unique(y[idx])) == 2:
                diffs.append(roc_auc_score(y[idx], fused[idx]) - roc_auc_score(y[idx], score[idx]))
        diffs = np.array(diffs)
        print(f"{Path(path).name}: coef [score, image] = {m.coef_.ravel().round(3).tolist()}")
        print(f"  test AUC radiomics alone {roc_auc_score(y, score):.4f} | late fusion {roc_auc_score(y, fused):.4f} | "
              f"delta {roc_auc_score(y, fused) - roc_auc_score(y, score):+.4f}, patient-bootstrap 95% CI "
              f"[{np.percentile(diffs, 2.5):+.3f}, {np.percentile(diffs, 97.5):+.3f}], P(delta>0) {np.mean(diffs > 0):.2f}")


if __name__ == "__main__":
    main()
