"""Class imbalance: does boosting (XGBoost / LightGBM) or re-balancing the training data help?

At 120 d the verified labels are 93 / 117 (grade 4) and 100 / 156 (all gliomas) progression / no progression, a minority
share of 39-44%. Under the C3 protocol (shared 5x5 patient-grouped folds, verified labels, mean-over-repeats pooled-OOF
IPCW AUC(120 d), paired patient-cluster bootstrap) this crosses

Features    baseline (clinical + timing + as-of-scan treatment, = C3) | ctv (shared clinical + timing + volumes, = external)
Learners    ridge (C by inner grouped log-loss, as formulations.fit) | histgb (= C3 boosting) | lgbm, xgb (fixed small-data
            settings) | lgbm_nested, xgb_nested (16-point grid chosen by inner 3-fold patient-grouped AUC per outer fold)
Weights     unit (verified labels unweighted: how C3 / external fit) | ipcw (formulations.training_rows('ipcw'): 1/G from
            the training fold's own censoring KM, mean 1)
Imbalance   none | balanced (class weights so both classes carry equal total weight; = scale_pos_weight) |
            oversample (positives duplicated by patient: draw training patients with a positive scan, append all their
            positive scans, until positives >= negatives; duplicates keep their patient id and weight) |
            smote (numpy SMOTE on the preprocessed features: anchor positive + one of its 5 nearest positives from other
            patients, x = a + u(b - a); group = anchor patient, weight = anchor weight)
Everything is fitted inside the training fold; inner CV (ridge C, boosting grid) re-balances each inner training split and
scores on the untouched inner validation split. Final weights are rescaled to mean 1.
Reference = C3 ridge baseline (baseline features, unit, none); a second paired Δ is vs the same learner/features/weights
with imbalance = none. LUMIERE: ctv models trained on all MU scans of the population, locked, scored pooled on LUMIERE
(point_metrics + cluster_bootstrap, paired vs the locked ridge/unit/none), as in external_lumiere.

    uv run --frozen --no-sync --with xgboost python -m prism.analyses.imbalance [--workers 32] [--n-boot 1000]
    (without xgboost the xgb learners are skipped and LightGBM stands in)
    -> $PRISM_OUTPUTS/results/analyses/imbalance/{mu.csv, lumiere.csv, oof_repeats.csv.gz, nested_choices.csv}
"""

from __future__ import annotations

import argparse
import functools
import itertools
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from prism.config import RESULTS
from prism.data import lumiere, mu
from prism.features.tabular import SHARED, groups as feature_groups, shared_lumiere, shared_mu
from prism.models.folds import load_folds
from prism.models.formulations import CS, _logloss, training_rows
from prism.models.metrics import (cluster_bootstrap, counted_warnings, evaluate_repeated, point_metrics,
                                  repeated_bootstrap)

try:
    from xgboost import XGBClassifier
except ImportError:  # shared .venv has no xgboost
    XGBClassifier = None

H = 120
OUT = RESULTS / "analyses" / "imbalance"
POPS = ("grade4", "all_glioma")
FEATURES = ("baseline", "ctv")
CTV = SHARED["clinical"] + SHARED["timing"] + SHARED["volumes"]
WEIGHTS = ("unit", "ipcw")
IMBALANCE = ("none", "balanced", "oversample", "smote")
PRE = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())])
HISTGB = HistGradientBoostingClassifier(max_depth=2, learning_rate=0.03, max_iter=150, min_samples_leaf=20,
                                        l2_regularization=2.0, max_features=0.5, random_state=0)  # = C3 boosting
BOOST = dict(max_depth=2, learning_rate=0.03, n_estimators=200, min_child_weight=5, subsample=0.8,
             colsample_bytree=0.8, reg_lambda=2.0)
GRID = [dict(max_depth=d, learning_rate=lr, n_estimators=n, min_child_weight=m)
        for d, lr, n, m in itertools.product((2, 3), (0.03, 0.05), (150, 300), (1, 5))]
REF = "baseline|ridge|unit|none"


def learners():
    return ["ridge", "histgb", "lgbm", "lgbm_nested"] + (["xgb", "xgb_nested"] if XGBClassifier is not None else [])


def boost(lib, seed, **kw):
    p = {**BOOST, **kw}
    if lib == "xgb":
        return XGBClassifier(**p, tree_method="hist", n_jobs=1, random_state=seed, verbosity=0)
    return LGBMClassifier(**p, num_leaves=2 ** p["max_depth"], min_child_samples=10, subsample_freq=1, n_jobs=1,
                          random_state=seed, verbose=-1)


# ---------------------------------------------------------------- data
@functools.lru_cache(maxsize=None)
def load(pop, fs):
    c = mu.load_cohort(pop)
    if fs == "baseline":
        g = feature_groups(c)
        X = pd.concat([g["clinical"], g["timing"], g["treatment"]], axis=1)
    else:
        X = shared_mu(c)[CTV]
    folds = load_folds()
    ids = np.array([c.scan_id.map(f.set_index("scan_id").fold).to_numpy() for _, f in folds.groupby("repeat")])
    return c, X, ids


@functools.lru_cache(maxsize=None)
def load_lumiere():
    lc = lumiere.load_cohort()
    return lc, shared_lumiere(lc)[CTV]


# ---------------------------------------------------------------- re-balancing (training rows only)
def rebalance(X, y, w, g, method, rng):
    """(X, y, w, g) of one training set after the imbalance step; weights rescaled to mean 1."""
    if method == "balanced":
        w = w * np.where(y == 1, w[y == 0].sum() / w[y == 1].sum(), 1.0)
    elif method == "oversample":
        pos_pats = np.unique(g[y == 1])
        add, n_add, need = [], 0, (y == 0).sum() - (y == 1).sum()
        while n_add < need:
            rows = np.where((g == rng.choice(pos_pats)) & (y == 1))[0]
            add.append(rows)
            n_add += len(rows)
        if add:
            a = np.concatenate(add)
            X, y, w, g = np.vstack([X, X[a]]), np.r_[y, y[a]], np.r_[w, w[a]], np.r_[g, g[a]]
    elif method == "smote":
        P = np.where(y == 1)[0]
        need = (y == 0).sum() - len(P)
        if need > 0:
            D = ((X[P, None, :] - X[None, P, :]) ** 2).sum(-1)
            D[g[P][:, None] == g[P][None, :]] = np.inf  # neighbours from other patients only
            nn = np.argsort(D, 1)[:, :5]
            a = rng.integers(len(P), size=need)
            b = nn[a, rng.integers(5, size=need)]
            b = np.where(np.isfinite(D[a, b]), b, a)
            u = rng.random((need, 1))
            Xs = X[P[a]] + u * (X[P[b]] - X[P[a]])
            X, y, w, g = np.vstack([X, Xs]), np.r_[y, np.ones(need, int)], np.r_[w, w[P[a]]], np.r_[g, g[P[a]]]
    elif method != "none":
        raise ValueError(method)
    return X, y, w / w.mean(), g


def _fit_one(learner, X, y, w, seed, params=None, C=None):
    if learner == "ridge":
        return LogisticRegression(penalty="l2", C=C, max_iter=5000, random_state=seed).fit(X, y, sample_weight=w)
    if learner == "histgb":
        return clone(HISTGB).set_params(random_state=seed).fit(X, y, sample_weight=w)
    return boost(learner.split("_")[0], seed, **(params or {})).fit(X, y, sample_weight=w)


def fit_model(learner, X, y, w, g, method, seed):
    """Fit one learner on preprocessed training rows (re-balanced inside, and inside every inner split).
    Returns (model, chosen hyperparameter or '')."""
    rng = np.random.default_rng(seed)
    if learner == "ridge" or learner.endswith("_nested"):
        cands = CS if learner == "ridge" else GRID
        scores = []
        for cand in cands:
            vals = []
            for tr, va in GroupKFold(n_splits=3).split(X, y, g):
                if len(np.unique(y[tr])) < 2:
                    continue
                Xr, yr, wr, _ = rebalance(X[tr], y[tr], w[tr], g[tr], method, np.random.default_rng(seed))
                if learner == "ridge":
                    m = _fit_one("ridge", Xr, yr, wr, seed, C=cand)
                    vals.append(_logloss(y[va], m.predict_proba(X[va])[:, 1], w[va]))
                else:
                    m = _fit_one(learner, Xr, yr, wr, seed, params=cand)
                    vals.append(-roc_auc_score(y[va], m.predict_proba(X[va])[:, 1], sample_weight=w[va]))
            scores.append(np.mean(vals))
        best = cands[int(np.argmin(scores))]
    else:
        best = None
    Xr, yr, wr, _ = rebalance(X, y, w, g, method, rng)
    if learner == "ridge":
        return _fit_one("ridge", Xr, yr, wr, seed, C=best), best
    return _fit_one(learner, Xr, yr, wr, seed, params=best), ("" if best is None else str(best))


def train(X, d, learner, weights, method, seed):
    """Fit on the verified rows of cohort slice d (features X: DataFrame). Returns (predict(Z), choice)."""
    known = ~np.isnan(d[f"label_{H}"].to_numpy(float))
    pre = clone(PRE).fit(X[known])
    # IPCW: censoring KM from all training scans (censored ones included); training_rows keeps the verified rows
    Xk, y, w, g = training_rows("verified" if weights == "unit" else "ipcw", pre.transform(X), d, H)
    model, choice = fit_model(learner, Xk, y, w, g, method, seed)
    return (lambda Z: model.predict_proba(pre.transform(Z))[:, 1]), choice


# ---------------------------------------------------------------- jobs
@counted_warnings
def run_cv(job):
    pop, fs, learner, weights, method = job
    threadpool_limits(1)
    c, X, ids = load(pop, fs)
    oof, choices = np.zeros(ids.shape), []
    for r, f in enumerate(ids):
        for k in np.unique(f):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            pred, ch = train(X.iloc[tr], c.iloc[tr].reset_index(drop=True), learner, weights, method, seed=r)
            oof[r, te] = pred(X.iloc[te])
            choices.append({"population": pop, "features": fs, "learner": learner, "weights": weights,
                            "imbalance": method, "repeat": r, "fold": k, "chosen": ch})
    return job, oof, choices


@counted_warnings
def run_locked(job):
    pop, learner, weights, method = job
    threadpool_limits(1)
    c, X, _ = load(pop, "ctv")
    _, LX = load_lumiere()
    pred, ch = train(X, c.reset_index(drop=True), learner, weights, method, seed=0)
    return job, pred(LX), ch


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m prism.analyses.imbalance", description=__doc__)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"boosting libraries: lightgbm + {'xgboost' if XGBClassifier is not None else 'NO xgboost (skipped)'}")
    grid = list(itertools.product(learners(), WEIGHTS, IMBALANCE))
    jobs = [(p, fs, *cfg) for p in POPS for fs in FEATURES for cfg in grid]
    ljobs = [(p, *cfg) for p in POPS for cfg in grid]
    with ProcessPoolExecutor(a.workers) as ex:
        cv = list(ex.map(run_cv, jobs))
        locked = list(ex.map(run_locked, ljobs))
    pd.DataFrame([r for *_, ch in cv for r in ch]).to_csv(OUT / "nested_choices.csv", index=False)

    rows, reps = [], []
    for pop in POPS:
        c, *_ = load(pop, "baseline")
        oofs = {"|".join(j[1:]): o for j, o, _ in cv if j[0] == pop}
        ev = evaluate_repeated(c, oofs, H, reference=REF, n_boot=a.n_boot)
        # paired Δ vs the same learner / features / weights without re-balancing
        within = []
        for key in oofs:
            fs, learner, weights, method = key.split("|")
            if method == "none":
                sub = {k: oofs[k] for k in oofs if k.rsplit("|", 1)[0] == key.rsplit("|", 1)[0]}
                b = repeated_bootstrap(c, sub, H, reference=key, n_boot=a.n_boot, seed=1).set_index("model")
                within.append(b.drop(index=key)[[f"d_auc_ipcw_vs_{key}", "d_auc_ipcw_lo", "d_auc_ipcw_hi", "d_brier_ipcw",
                                                 "d_brier_ipcw_lo", "d_brier_ipcw_hi"]]
                              .set_axis(["d_auc_vs_none", "d_auc_vs_none_lo", "d_auc_vs_none_hi", "d_brier_vs_none",
                                         "d_brier_vs_none_lo", "d_brier_vs_none_hi"], axis=1))
        ev = ev.join(pd.concat(within))
        for key, o in oofs.items():
            fs, learner, weights, method = key.split("|")
            rows.append({"population": pop, "features": fs, "learner": learner, "weights": weights, "imbalance": method,
                         "mean_pred": float(o.mean()), **ev.loc[key].dropna().to_dict()})
            reps.append(pd.DataFrame(o.T, columns=[f"{pop}|{key}#r{r}" for r in range(len(o))]))
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "mu.csv", index=False)
    pd.concat(reps, axis=1).to_csv(OUT / "oof_repeats.csv.gz", index=False)

    lc, _ = load_lumiere()
    lrows = []
    for pop in POPS:
        preds = {"|".join(j[1:]): p for j, p, _ in locked if j[0] == pop}
        ref = "ridge|unit|none"
        cb = cluster_bootstrap(lc, preds, H, reference=ref, n_boot=a.n_boot).set_index("formulation")
        for key, p in preds.items():
            learner, weights, method = key.split("|")
            ch = next(x for j, _, x in locked if j[0] == pop and "|".join(j[1:]) == key)
            lrows.append({"train": pop, "features": "ctv", "learner": learner, "weights": weights, "imbalance": method,
                          "chosen": ch, "mean_pred": float(p.mean()), **point_metrics(lc, p, H),
                          **cb.loc[key].dropna().to_dict()})
    lres = pd.DataFrame(lrows)
    lres.to_csv(OUT / "lumiere.csv", index=False)

    pd.set_option("display.width", 250)
    cols = ["auc_ipcw", "d_auc_ipcw_lo", "d_auc_ipcw_hi", "d_auc_vs_none", "brier_ipcw", "oe_ratio", "cal_slope"]
    for pop in POPS:
        print(f"\n== MU {pop} (Δ vs {REF}; d_auc_vs_none = vs same learner without re-balancing)")
        t = res[res.population == pop].set_index(["features", "learner", "weights", "imbalance"])
        print(t[[x for x in cols if x in t]].round(3).to_string())
    print("\n== LUMIERE locked (ctv), pooled")
    print(lres.set_index(["train", "learner", "weights", "imbalance"])[
        ["auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "d_auc_ipcw_lo", "d_auc_ipcw_hi", "brier_ipcw", "oe_ratio", "cal_slope"]
    ].round(3).to_string())


if __name__ == "__main__":
    main()
