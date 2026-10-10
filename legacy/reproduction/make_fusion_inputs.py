#!/usr/bin/env python3
"""Rebuild the radiomics inputs for MLPFusion from recomputed features.

Refits the shipped calibrated LogReg-48 (columns + hyperparameters from models/calibrated) on the
recomputed feature table, then writes, in the shipped column layout:
  reproduction/fusion_inputs/train_predictions.csv  out-of-fold predictions (= glioma_agent/data/train_predictions.csv)
  reproduction/fusion_inputs/test_predictions.csv   final-model predictions on held-out patients
and prints how closely they match the shipped files.
Requires radiomics/results/calibrated_forward_hybrid/ from reproduction/radiomics/run_train.py.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import types
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
RADIOMICS = REPO / "radiomics"
os.chdir(RADIOMICS)
sys.path.insert(0, str(RADIOMICS))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

from radiomics_pipeline.workflows import export_calibrated as ex  # noqa: E402
from radiomics_pipeline.workflows import train as surv  # noqa: E402

# The shipped bundle was pickled under the pre-refactor module path.
sys.modules["scripts"] = types.ModuleType("scripts")
sys.modules["scripts.run_postoperative_progression_surveillance"] = surv

b = pickle.load(open("models/calibrated/model_bundle.pkl", "rb"))
meta = json.load(open("models/calibrated/metadata.json"))
st = b["preprocessor_state"]
cols = meta["selected_columns"]
params = {"C": b["classifier"].C, "variance_threshold": st.variance_threshold, "corr_threshold": st.corr_threshold}

feats = pd.read_csv("results/calibrated_forward_hybrid/radiomics_features.csv")
test_p = set(open("results/calibrated_forward_hybrid/test_patients.txt").read().split())
tr = feats[~feats.patient_id.isin(test_p)].copy()
te = feats[feats.patient_id.isin(test_p)].copy()
oof, folds, state, model = surv.fit_oof_predictions(train_df=tr, model_name="logreg", params=params, columns=cols,
                                                   args=ex.make_args(output_dir=Path("/tmp/x"), seed=62, cv_folds=5))
cal = LogisticRegression(solver="lbfgs", max_iter=1000, random_state=62).fit(oof.reshape(-1, 1), tr.label)
te_raw = surv.predict_positive_probability(model, surv.transform_preprocessor(te[cols], state))
thr = surv.select_threshold(tr.label.to_numpy(), cal.predict_proba(oof.reshape(-1, 1))[:, 1])[0]

ship_tr = pd.read_csv(REPO / "glioma_agent/data/train_predictions.csv")
ship_te = pd.read_csv("models/calibrated/test_predictions.csv")


def fill(ship: pd.DataFrame, part: pd.DataFrame, raw: np.ndarray, pred_col: str) -> pd.DataFrame:
    df = ship[["patient_id", "timepoint"]].merge(part[["patient_id", "timepoint"]].assign(r=raw), on=["patient_id", "timepoint"])
    res = ship.copy()
    res["raw_probability"] = df.r.values
    res["calibrated_probability"] = cal.predict_proba(df.r.values.reshape(-1, 1))[:, 1]
    res["progression_risk_probability"] = res["calibrated_probability"]
    res["progression_risk_percent"] = 100 * res["calibrated_probability"]
    res[pred_col] = (res["calibrated_probability"] >= thr).astype(int)
    return res


out = REPO / "reproduction" / "fusion_inputs"
out.mkdir(parents=True, exist_ok=True)
tr_out = fill(ship_tr, tr, oof, "predicted_class_by_threshold")
te_out = fill(ship_te, te, te_raw, "predicted_class")
tr_out.to_csv(out / "train_predictions.csv", index=False)
te_out.to_csv(out / "test_predictions.csv", index=False)
print(f"fold AUCs {[round(f['auc'], 4) for f in folds]} (shipped {[round(f['auc'], 4) for f in meta['cv_fold_metrics']]})")
print(f"threshold {thr:.6f} (shipped {meta['threshold']:.6f})")
print(f"max |calibrated prob - shipped|: train (OOF) {np.abs(tr_out.calibrated_probability - ship_tr.calibrated_probability).max():.4f}, "
      f"test {np.abs(te_out.calibrated_probability - ship_te.calibrated_probability).max():.4f}")
print(f"wrote {out}/train_predictions.csv ({len(tr_out)}) and test_predictions.csv ({len(te_out)})")
