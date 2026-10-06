"""Censoring-aware evaluation harness with patient-cluster bootstrap.

Primary: IPCW cumulative/dynamic AUC(H) and IPCW Brier(H) (scikit-survival; Uno/Blanche, Graf).
Secondary: AUC on verified scans, AUC against the naive label (what a naive analysis reports),
observed/expected ratio (Kaplan-Meier risk at H vs mean prediction), IPCW calibration slope.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sksurv.metrics import brier_score, cumulative_dynamic_auc
from sksurv.nonparametric import kaplan_meier_estimator
from sksurv.util import Surv

from prism.formulations import G_FLOOR, _observed_time, censoring_survival


def _surv(d: pd.DataFrame, horizon: int):
    return Surv.from_arrays(event=d["event"].to_numpy(bool), time=_observed_time(d, horizon))


def point_metrics(d: pd.DataFrame, p: np.ndarray, horizon: int) -> dict[str, float]:
    s = _surv(d, horizon)
    out = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out["auc_ipcw"] = float(cumulative_dynamic_auc(s, s, p, [horizon])[0][0])
        out["brier_ipcw"] = float(brier_score(s, s, (1 - p)[:, None], [horizon])[1][0])
    label = d[f"label_{horizon}"].to_numpy(float)
    known = ~np.isnan(label)
    out["auc_verified"] = float(roc_auc_score(label[known], p[known]))
    out["auc_naive"] = float(roc_auc_score(d[f"naive_label_{horizon}"], p))
    times, km = kaplan_meier_estimator(s["event"], s["time"])
    observed = 1.0 - float(km[times <= horizon][-1]) if (times <= horizon).any() else 0.0
    out["oe_ratio"] = observed / float(p.mean())
    G = censoring_survival(d, horizon)
    w = 1.0 / np.maximum(G(np.minimum(_observed_time(d, horizon), horizon)), G_FLOOR)
    logit = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))[known]
    slope = LogisticRegression(penalty=None, max_iter=1000).fit(logit[:, None], label[known], sample_weight=w[known])
    out["cal_slope"] = float(slope.coef_[0][0])
    return out


def cluster_bootstrap(d: pd.DataFrame, preds: dict[str, np.ndarray], horizon: int, reference: str,
                      metrics=("auc_ipcw", "brier_ipcw"), n_boot: int = 1000, seed: int = 0) -> pd.DataFrame:
    """Resample patients; 95% CIs per formulation and for the paired difference vs `reference`."""
    rng = np.random.default_rng(seed)
    pid = d["patient_id"].to_numpy()
    groups = {p: np.where(pid == p)[0] for p in np.unique(pid)}
    pats = np.array(list(groups))
    draws = {f: {m: [] for m in metrics} for f in preds}
    for _ in range(n_boot):
        idx = np.concatenate([groups[p] for p in rng.choice(pats, len(pats))])
        db = d.iloc[idx].reset_index(drop=True)
        if db[f"label_{horizon}"].nunique(dropna=True) < 2:
            continue
        try:
            vals = {f: point_metrics(db, p[idx], horizon) for f, p in preds.items()}
        except ValueError:
            continue
        for f in preds:
            for m in metrics:
                draws[f][m].append(vals[f][m])
    rows = []
    for f in preds:
        row = {"formulation": f}
        for m in metrics:
            a = np.asarray(draws[f][m])
            row[f"{m}_lo"], row[f"{m}_hi"] = np.percentile(a, [2.5, 97.5])
            if f != reference:
                diff = a - np.asarray(draws[reference][m])
                row[f"d_{m}_vs_{reference}"] = float(np.mean(diff))
                row[f"d_{m}_lo"], row[f"d_{m}_hi"] = np.percentile(diff, [2.5, 97.5])
        rows.append(row)
    return pd.DataFrame(rows)
