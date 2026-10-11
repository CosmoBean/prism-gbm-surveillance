"""Censoring-aware evaluation harness with patient-cluster bootstrap.

Primary: IPCW cumulative/dynamic AUC(H) and IPCW Brier(H) (scikit-survival; Uno/Blanche, Graf).
Repeated CV: headline = mean over repeats of each repeat's pooled-OOF metric (repeated_point_metrics,
repeated_bootstrap); the metric of the repeat-averaged prediction is kept as a secondary `_averaged` column.
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
from sksurv.nonparametric import CensoringDistributionEstimator, kaplan_meier_estimator
from sksurv.util import Surv

from prism.models.formulations import G_FLOOR, _observed_time, censoring_survival


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
    """Resample patients; 95% CIs per formulation and for the paired difference vs `reference`.

    For a single prediction vector per model. For repeated CV use repeated_bootstrap (mean-over-repeats estimator)."""
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
    point = {f: point_metrics(d, p, horizon) for f, p in preds.items()}
    rows = []
    for f in preds:
        row = {"formulation": f}
        for m in metrics:
            a = np.asarray(draws[f][m])
            row[f"{m}_lo"], row[f"{m}_hi"] = np.percentile(a, [2.5, 97.5])
            if f != reference:
                diff = a - np.asarray(draws[reference][m])
                row[f"d_{m}_vs_{reference}"] = point[f][m] - point[reference][m]  # point estimate, not boot mean
                row[f"d_{m}_boot_mean"] = float(np.mean(diff))
                row[f"d_{m}_lo"], row[f"d_{m}_hi"] = np.percentile(diff, [2.5, 97.5])
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- repeated-CV estimator (headline numbers)
# Headline AUC/Brier of an R x K repeated CV = mean over the R repeats of the metric of that repeat's pooled
# out-of-fold predictions. The AUC of the *repeat-averaged* prediction (the earlier headline) is an ensemble of R
# models per scan and is optimistic for unstable pipelines (nested selection); it is kept as `<metric>_averaged`.

def ipcw_context(d: pd.DataFrame, horizon: int) -> dict | None:
    """Outcome-only parts of IPCW AUC/Brier (sksurv definitions); None where sksurv would raise."""
    s = _surv(d, horizon)
    t, e = s["time"], s["event"]
    if not (t.min() <= horizon < t.max()):
        return None
    cens = CensoringDistributionEstimator().fit(s)
    case, ctrl = e & (t <= horizon), t > horizon
    g_t = cens.predict_proba(t)
    if (g_t[case] <= 0).any() or not case.any() or not ctrl.any():
        return None
    g_h = float(cens.predict_proba(np.array([horizon], float))[0])
    return {"case": case, "ctrl": ctrl, "w_case": 1.0 / g_t[case],
            "w_brier": np.where(case, 1.0 / np.where(g_t > 0, g_t, np.inf), 0.0) + ctrl / (g_h if g_h > 0 else np.inf)}


def fast_auc_brier(ctx: dict, P: np.ndarray, subset: np.ndarray | None = None, tied_tol: float = 1e-8):
    """IPCW AUC(H) and Brier(H) for each row of P (m x n) given ipcw_context; equals sksurv to float precision.

    `subset` (bool, n) restricts cases/controls to some scans but keeps the cohort-level censoring weights
    (used for per-fold estimates). Rows without a case or control give NaN."""
    P = np.atleast_2d(P)
    case, ctrl, w = ctx["case"], ctx["ctrl"], np.zeros(P.shape[1])
    w[case] = ctx["w_case"]
    if subset is not None:
        case, ctrl = case & subset, ctrl & subset
    auc = np.full(len(P), np.nan)
    if case.any() and ctrl.any():
        wc = w[case]
        for i, p in enumerate(P):
            pk = np.sort(p[ctrl])
            lo = np.searchsorted(pk, p[case] - tied_tol, side="left")
            hi = np.searchsorted(pk, p[case] + tied_tol, side="right")
            auc[i] = float((wc * (lo + 0.5 * (hi - lo))).sum() / (wc.sum() * len(pk)))
    m = np.ones(P.shape[1], bool) if subset is None else subset
    yb = case.astype(float)  # Brier on P(event by H): cases target 1, controls target 0
    brier = ((P[:, m] - yb[m]) ** 2 * ctx["w_brier"][m]).mean(1)
    return auc, brier


def repeated_point_metrics(d: pd.DataFrame, oof: np.ndarray, horizon: int) -> dict[str, float]:
    """Mean over repeats of point_metrics (rows of `oof` = repeats), plus SD and the repeat-averaged estimator."""
    oof = np.atleast_2d(oof)
    per = pd.DataFrame([point_metrics(d, o, horizon) for o in oof])
    out = per.mean().to_dict()
    out["auc_ipcw_repeat_sd"] = float(per["auc_ipcw"].std(ddof=0))
    out.update({f"{k}_averaged": v for k, v in point_metrics(d, oof.mean(0), horizon).items()
                if k in ("auc_ipcw", "brier_ipcw", "auc_verified", "cal_slope")})
    return out


def repeated_bootstrap(d: pd.DataFrame, oofs: dict[str, np.ndarray], horizon: int, reference: str | None = None,
                       n_boot: int = 1000, seed: int = 0) -> pd.DataFrame:
    """Patient-cluster bootstrap of the mean-over-repeats IPCW AUC/Brier (and of the repeat-averaged AUC).

    `oofs` maps model -> (n_repeats x n_scans) OOF predictions. Every resample draws patients once and evaluates
    every repeat of every model on the same draw, so differences vs `reference` are paired. Point estimates
    (incl. ΔAUC) are computed on the original data; the bootstrap gives percentile CIs only."""
    names = list(oofs)
    mats = [np.atleast_2d(oofs[k]) for k in names]
    sizes = np.cumsum([0] + [len(m) for m in mats])
    P = np.vstack(mats + [m.mean(0, keepdims=True) for m in mats])  # repeats ..., then averaged rows

    def summarise(ctx, idx=None):
        a, b = fast_auc_brier(ctx, P if idx is None else P[:, idx])
        nm = len(names)
        return (np.array([a[sizes[i]:sizes[i + 1]].mean() for i in range(nm)]),
                np.array([b[sizes[i]:sizes[i + 1]].mean() for i in range(nm)]), a[sizes[-1]:])

    point = summarise(ipcw_context(d, horizon))
    rng = np.random.default_rng(seed)
    pid = d["patient_id"].to_numpy()
    groups = {p: np.where(pid == p)[0] for p in np.unique(pid)}
    pats = np.array(list(groups))
    draws = []
    for _ in range(n_boot):
        idx = np.concatenate([groups[p] for p in rng.choice(pats, len(pats))])
        db = d.iloc[idx].reset_index(drop=True)
        if db[f"label_{horizon}"].nunique(dropna=True) < 2:
            continue
        ctx = ipcw_context(db, horizon)
        if ctx is not None:
            draws.append(summarise(ctx, idx))
    A, B, AV = (np.array([x[j] for x in draws]) for j in range(3))
    ci = lambda a: np.nanpercentile(a, [2.5, 97.5], axis=0)
    rows = []
    r = names.index(reference) if reference is not None else None
    for i, k in enumerate(names):
        row = {"model": k, "n_repeats": len(mats[i]), "auc_ipcw": point[0][i], "brier_ipcw": point[1][i],
               "auc_ipcw_averaged": point[2][i], "n_boot_ok": len(A)}
        row["auc_ipcw_lo"], row["auc_ipcw_hi"] = ci(A[:, i])
        row["brier_ipcw_lo"], row["brier_ipcw_hi"] = ci(B[:, i])
        row["auc_ipcw_averaged_lo"], row["auc_ipcw_averaged_hi"] = ci(AV[:, i])
        if r is not None and i != r:
            row[f"d_auc_ipcw_vs_{reference}"] = point[0][i] - point[0][r]
            row["d_auc_ipcw_lo"], row["d_auc_ipcw_hi"] = ci(A[:, i] - A[:, r])
            row["d_auc_ipcw_boot_mean"] = float(np.nanmean(A[:, i] - A[:, r]))
            row["d_auc_ipcw_p_le0"] = float(np.mean(A[:, i] - A[:, r] <= 0))
            row["d_auc_ipcw_averaged"] = point[2][i] - point[2][r]
            row["d_auc_ipcw_averaged_lo"], row["d_auc_ipcw_averaged_hi"] = ci(AV[:, i] - AV[:, r])
            row["d_brier_ipcw"] = point[1][i] - point[1][r]
            row["d_brier_ipcw_lo"], row["d_brier_ipcw_hi"] = ci(B[:, i] - B[:, r])
        rows.append(row)
    return pd.DataFrame(rows)


def evaluate_repeated(d: pd.DataFrame, oofs: dict[str, np.ndarray], horizon: int, reference: str | None = None,
                      n_boot: int = 1000, seed: int = 0) -> pd.DataFrame:
    """Headline table: repeated_point_metrics per model + repeated_bootstrap CIs (index = model)."""
    boot = repeated_bootstrap(d, oofs, horizon, reference, n_boot, seed).set_index("model")
    pm = pd.DataFrame({k: repeated_point_metrics(d, o, horizon) for k, o in oofs.items()}).T
    return pm.join(boot.drop(columns=["auc_ipcw", "brier_ipcw", "auc_ipcw_averaged"]))


def fold_mean_metrics(d: pd.DataFrame, P: np.ndarray, fold_ids: np.ndarray, horizon: int,
                      ctx: dict | None = None) -> dict[str, float]:
    """Per-fold IPCW AUC/Brier (cohort-level censoring weights), O/E and calibration slope, averaged over folds.

    P, fold_ids: (n_repeats x n_scans); each (repeat, fold) is one held-out set. Folds without a case or control
    are skipped for AUC; slope needs both verified classes. oe_ratio_pooled = Kaplan-Meier risk at H of the whole
    cohort / mean held-out prediction over all scans and repeats (calibration-in-the-large is a ratio of totals, so
    it can be pooled across folds; a mean of per-fold ratios is unstable with ~25-scan folds)."""
    ctx = ipcw_context(d, horizon) if ctx is None else ctx
    label = d[f"label_{horizon}"].to_numpy(float)
    s = _surv(d, horizon)
    G = censoring_survival(d, horizon)
    w = 1.0 / np.maximum(G(np.minimum(_observed_time(d, horizon), horizon)), G_FLOOR)
    vals = {"auc_ipcw": [], "brier_ipcw": [], "oe_ratio": [], "cal_slope": []}
    for r in range(len(P)):
        for k in np.unique(fold_ids[r]):
            m = fold_ids[r] == k
            a, b = fast_auc_brier(ctx, P[r], subset=m)
            vals["auc_ipcw"].append(a[0])
            vals["brier_ipcw"].append(b[0])
            times, km = kaplan_meier_estimator(s["event"][m], s["time"][m])
            obs = 1.0 - float(km[times <= horizon][-1]) if (times <= horizon).any() else 0.0
            vals["oe_ratio"].append(obs / float(P[r, m].mean()))
            kn = m & ~np.isnan(label)
            if len(np.unique(label[kn])) == 2:
                lg = np.log(np.clip(P[r, kn], 1e-6, 1 - 1e-6) / (1 - np.clip(P[r, kn], 1e-6, 1 - 1e-6)))
                fit = LogisticRegression(penalty=None, max_iter=1000).fit(lg[:, None], label[kn], sample_weight=w[kn])
                vals["cal_slope"].append(float(fit.coef_[0][0]))
    out = {}
    for k, v in vals.items():
        v = np.asarray(v, float)
        out[f"{k}_fold_mean"], out[f"{k}_fold_sd"] = float(np.nanmean(v)), float(np.nanstd(v))
        if k == "cal_slope":
            out["cal_slope_fold_median"] = float(np.nanmedian(v))
    times, km = kaplan_meier_estimator(s["event"], s["time"])
    obs = 1.0 - float(km[times <= horizon][-1]) if (times <= horizon).any() else 0.0
    out["oe_ratio_pooled"] = obs / float(np.mean(P))
    out["n_folds_auc"] = int(np.isfinite(vals["auc_ipcw"]).sum())
    return out


def fold_mean_bootstrap(d: pd.DataFrame, arms: dict[str, np.ndarray], fold_ids: np.ndarray, horizon: int,
                        reference: str | None = None, n_boot: int = 1000, seed: int = 0) -> pd.DataFrame:
    """Patient-cluster bootstrap CIs for the per-fold-mean IPCW AUC; resampled patients keep their folds (paired)."""
    names = list(arms)

    def stat(ctx, idx):
        out = []
        for k in names:
            P = arms[k][:, idx]
            a = [fast_auc_brier(ctx, P[r], subset=fold_ids[r, idx] == f)[0][0]
                 for r in range(len(P)) for f in np.unique(fold_ids[r])]
            out.append(np.nanmean(a))
        return np.array(out)

    n = len(d)
    point = stat(ipcw_context(d, horizon), np.arange(n))
    rng = np.random.default_rng(seed)
    pid = d["patient_id"].to_numpy()
    groups = {p: np.where(pid == p)[0] for p in np.unique(pid)}
    pats = np.array(list(groups))
    draws = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN fold means in degenerate resamples
        for _ in range(n_boot):
            idx = np.concatenate([groups[p] for p in rng.choice(pats, len(pats))])
            ctx = ipcw_context(d.iloc[idx].reset_index(drop=True), horizon)
            if ctx is not None:
                draws.append(stat(ctx, idx))
    A = np.array(draws)
    rows = []
    for i, k in enumerate(names):
        row = {"arm": k, "auc_ipcw_fold_mean": point[i]}
        row["auc_ipcw_fold_mean_lo"], row["auc_ipcw_fold_mean_hi"] = np.nanpercentile(A[:, i], [2.5, 97.5])
        if reference is not None and k != reference:
            j = names.index(reference)
            row[f"d_auc_fold_mean_vs_{reference}"] = point[i] - point[j]
            row["d_auc_fold_mean_lo"], row["d_auc_fold_mean_hi"] = np.nanpercentile(A[:, i] - A[:, j], [2.5, 97.5])
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- warnings in worker processes
# f_classif's divide warning is silenced at its call site (c3_radiomics.f_classif_quiet) and the SWIG import
# deprecation at the SimpleITK import (features/radiomics.py); every other RuntimeWarning is counted and logged.
KNOWN_NOISY = (  # (category, message regex): expected and harmless in these pipelines
    (UserWarning, r"Features .* are constant"),
    (UserWarning, r"Skipping features without any observed values"),
)


def counted_warnings(fn):
    """Decorator for worker jobs: silence KNOWN_NOISY warnings, count the rest (e.g. ConvergenceWarning) and log
    one line per job to stderr instead of hiding them with a global filter."""
    import functools
    import sys

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            for cat, msg in KNOWN_NOISY:
                warnings.filterwarnings("ignore", message=msg, category=cat)
            out = fn(*args, **kwargs)
        if rec:
            counts = {}
            for w in rec:
                key = f"{w.category.__name__}: {str(w.message)[:70]}"
                counts[key] = counts.get(key, 0) + 1
            job = str(args[0])[:90] if args else fn.__name__
            print(f"[warnings] {fn.__name__} {job}: " + "; ".join(f"{n}x {k}" for k, n in counts.items()),
                  file=sys.stderr, flush=True)
        return out
    return wrapper
