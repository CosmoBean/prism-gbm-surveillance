"""Outcome formulations for P(progression <= H | scan). All share one ridge-logistic learner.

naive     legacy: censored-before-H scans labelled 0
verified  censored-before-H scans dropped
ipcw      verified scans weighted by 1 / G, G = Kaplan-Meier survival of the censoring time (Vock 2016)
hazard    discrete-time landmark hazard on person-period data (van Houwelingen 2007; Suresh 2022):
          censored scans contribute their observed at-risk intervals
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

FORMULATIONS = ("naive", "verified", "ipcw", "hazard")
CS = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)
N_INTERVALS = 4
G_FLOOR = 0.1


def _observed_time(d: pd.DataFrame, horizon: int) -> np.ndarray:
    """Follow-up used for survival bookkeeping; death without progression = never censored."""
    t = d["time_to_event"].to_numpy(float)
    return np.where(d["status_known_indefinitely"].to_numpy(), np.maximum(t, horizon + 1.0), t)


def censoring_survival(d: pd.DataFrame, horizon: int):
    """Kaplan-Meier G(t) = P(censoring time > t), returned as a left-continuous step function G(t-)."""
    t = _observed_time(d, horizon)
    censored = ~d["event"].to_numpy(bool) & ~d["status_known_indefinitely"].to_numpy(bool)
    times = np.unique(t[censored])
    surv, s = [], 1.0
    for u in times:
        at_risk = (t >= u).sum()
        s *= 1.0 - ((t == u) & censored).sum() / max(at_risk, 1)
        surv.append(s)
    times, surv = np.asarray(times), np.asarray(surv)

    def G_minus(x):
        idx = np.searchsorted(times, np.asarray(x, float), side="left") - 1  # last censoring time strictly < x
        return np.where(idx >= 0, surv[np.clip(idx, 0, None)], 1.0)
    return G_minus


def training_rows(form: str, X: np.ndarray, d: pd.DataFrame, horizon: int):
    """(X, y, sample_weight, groups) for the learner; for 'hazard' X gains interval indicators."""
    label = d[f"label_{horizon}"].to_numpy(float)
    groups = d["patient_id"].to_numpy()
    if form == "naive":
        return X, d[f"naive_label_{horizon}"].to_numpy(int), np.ones(len(d)), groups
    known = ~np.isnan(label)
    if form == "verified":
        return X[known], label[known].astype(int), np.ones(known.sum()), groups[known]
    if form == "ipcw":
        G = censoring_survival(d, horizon)
        t = _observed_time(d, horizon)
        w = 1.0 / np.maximum(G(np.minimum(t, horizon)), G_FLOOR)
        w = w[known] / w[known].mean()
        return X[known], label[known].astype(int), w, groups[known]
    if form == "hazard":
        return person_period(X, d, horizon)
    raise ValueError(form)


def person_period(X: np.ndarray, d: pd.DataFrame, horizon: int):
    edges = np.linspace(0, horizon, N_INTERVALS + 1)
    t = np.minimum(_observed_time(d, horizon), horizon)
    event_by_h = d["event"].to_numpy(bool) & (d["time_to_event"].to_numpy(float) <= horizon)
    rows, ys, gs = [], [], []
    for i in range(len(d)):
        for k in range(N_INTERVALS):
            if t[i] <= edges[k]:
                break
            ys.append(int(event_by_h[i] and edges[k] < t[i] <= edges[k + 1]))
            rows.append(np.concatenate([X[i], np.eye(N_INTERVALS)[k]]))
            gs.append(d["patient_id"].iat[i])
    return np.asarray(rows), np.asarray(ys), np.ones(len(ys)), np.asarray(gs)


def predict_risk(form: str, model, X: np.ndarray) -> np.ndarray:
    if form != "hazard":
        return model.predict_proba(X)[:, 1]
    surv = np.ones(len(X))
    for k in range(N_INTERVALS):
        h = model.predict_proba(np.hstack([X, np.tile(np.eye(N_INTERVALS)[k], (len(X), 1))]))[:, 1]
        surv *= 1.0 - h
    return 1.0 - surv


def _logloss(y, p, w):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -np.average(y * np.log(p) + (1 - y) * np.log(1 - p), weights=w)


def fit(form: str, X: np.ndarray, d: pd.DataFrame, horizon: int, seed: int = 0):
    """Ridge logistic; C chosen by inner patient-grouped CV on the formulation's own (weighted) log-loss."""
    Xr, y, w, g = training_rows(form, X, d, horizon)
    base = LogisticRegression(penalty="l2", max_iter=5000, random_state=seed)
    if form == "hazard":
        base.set_params(fit_intercept=False)  # interval indicators carry the baseline hazard
    scores = []
    for C in CS:
        losses = []
        for tr, va in GroupKFold(n_splits=3).split(Xr, y, g):
            if len(np.unique(y[tr])) < 2:
                continue
            m = clone(base).set_params(C=C).fit(Xr[tr], y[tr], sample_weight=w[tr])
            losses.append(_logloss(y[va], m.predict_proba(Xr[va])[:, 1], w[va]))
        scores.append(np.mean(losses))
    best_C = CS[int(np.argmin(scores))]
    return clone(base).set_params(C=best_C).fit(Xr, y, sample_weight=w), best_C
