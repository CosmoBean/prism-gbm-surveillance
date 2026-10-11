"""External test on LUMIERE with features shared by both cohorts.

Arms (same features, H = 120 d, verified labels for training, IPCW AUC for evaluation):
  mu_cv            MU repeated patient-grouped CV on the shared folds (outputs/data/folds.csv; internal reference)
  locked           model trained on all MU scans, applied once to LUMIERE
  recalibrated     locked model + unpenalised logistic recalibration on the logit (intercept, slope; slope floored at
                   0.05 so it never reverses the ranking), fitted on the training LUMIERE patients of each fold
  finetune_shrink  ridge refit on training LUMIERE patients, penalised towards the MU coefficients
  finetune_pooled  refit on MU + training LUMIERE patients (LUMIERE weight 3)
  lumiere_only     model trained and tested within LUMIERE — the local ceiling
  locked+cohort_norm_{rank,zscore}
                   sensitivity (volume feature sets only): the locked model with the volume columns re-expressed
                   within each cohort (features.tabular.within_cohort_normalise: MU on the training population,
                   LUMIERE on all its index scans; transductive, never uses LUMIERE labels). Removes segmenter scale
                   differences by construction (docs/results/FIX_FEATURES.md section 2)

Estimator: every LUMIERE arm, locked included, is scored on the same 5x5 patient-grouped LUMIERE folds: IPCW AUC(H)
per held-out fold (cases/controls of the fold, censoring weights from the whole LUMIERE cohort), Brier, O/E and IPCW
calibration slope per fold, then averaged over the 25 folds; 95% CIs from a patient-cluster bootstrap in which
patients keep their folds (paired vs locked). Pooling out-of-fold predictions across differently adapted folds is not
a valid estimate for discrimination, so adapted arms have no pooled AUC; O/E is reported pooled (oe_ratio_pooled:
Kaplan-Meier risk of all LUMIERE / mean held-out prediction; per-fold mean kept as oe_ratio_fold_mean). The locked
arms are also reported pooled on all of LUMIERE.
MU CV is reported as the mean over repeats of the pooled-OOF AUC (as in c1-c3) and per fold.

Missing values (e.g. LUMIERE scans without a usable DeepBraTumIA segmentation) are imputed by the fitted pipeline
(PRE), i.e. with the medians of the data the model was trained on: MU medians for the locked / recalibrated / shrink
arms. That is the correct behaviour of a locked model (it carries no LUMIERE statistics), but MU and DeepBraTumIA
volumes differ in level, so an imputed LUMIERE volume is an MU-typical value; MU has no missing volumes, so there is
no missingness indicator for them either.

    python -m prism external   # -> outputs/results/external_lumiere/{results.csv, locked_predictions.csv}
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from prism.config import RESULTS
from prism.data import lumiere, mu
from prism.features.tabular import SHARED, shared_lumiere, shared_mu, within_cohort_normalise
from prism.models.formulations import fit as fit_ridge
from prism.models.folds import load_folds
from prism.models.metrics import (cluster_bootstrap, counted_warnings, fold_mean_bootstrap, fold_mean_metrics,
                                  point_metrics, repeated_bootstrap, repeated_point_metrics)

H = 120
FEATURE_SETS = {
    "clinical": SHARED["clinical"],
    "clinical+timing": SHARED["clinical"] + SHARED["timing"],
    "volumes": SHARED["volumes"],
    "clinical+timing+volumes": SHARED["clinical"] + SHARED["timing"] + SHARED["volumes"],
}
GBM = HistGradientBoostingClassifier(max_depth=2, learning_rate=0.03, max_iter=150, min_samples_leaf=20,
                                     l2_regularization=2.0, max_features=0.5, random_state=0)
# Fitted on the training rows only: a locked MU model imputes LUMIERE gaps with MU training medians (see docstring).
PRE = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())])
COHORT_NORMS = ("rank", "zscore")


def mu_table(grade4_only: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    c = mu.load_cohort("grade4" if grade4_only else "all_glioma")
    return c, shared_mu(c)


def lumiere_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    c = lumiere.load_cohort()
    return c, shared_lumiere(c)


def fit(learner, X, cohort, seed=0, weights=None, return_parts=False):
    """Fit on verified labels. Returns a predict function (and, for ridge, the preprocessor + model)."""
    y = cohort[f"label_{H}"].to_numpy()
    k = ~np.isnan(y)
    pre = clone(PRE).fit(X[k])
    Xk = pre.transform(X[k])
    w = None if weights is None else np.asarray(weights)[k]
    if learner == "ridge":
        if w is None:
            model, _ = fit_ridge("verified", Xk, cohort[k].reset_index(drop=True), H, seed=seed)
        else:
            model = LogisticRegression(C=0.1, max_iter=5000).fit(Xk, y[k].astype(int), sample_weight=w)
    else:
        model = clone(GBM).set_params(random_state=seed).fit(Xk, y[k].astype(int), sample_weight=w)
    predict = lambda Z: model.predict_proba(pre.transform(Z))[:, 1]
    return (predict, pre, model) if return_parts else predict


def mu_fold_ids(cohort):
    """(n_repeats x n_scans) fold ids of the shared MU folds (outputs/data/folds.csv)."""
    folds = load_folds()
    return np.array([cohort.scan_id.map(f.set_index("scan_id").fold).to_numpy() for _, f in folds.groupby("repeat")])


def lumiere_fold_ids(lc, n_rep=5):
    """(n_repeats x n_scans) patient-grouped LUMIERE folds, stratified on 120-d status; shared by every arm."""
    strata = lc[f"label_{H}"].map({1.0: "p", 0.0: "n"}).fillna("c")
    ids = np.zeros((n_rep, len(lc)), int)
    for r in range(n_rep):
        for k, (_, te) in enumerate(StratifiedGroupKFold(5, shuffle=True, random_state=r).split(lc, strata, lc.patient_id)):
            ids[r, te] = k
    return ids


def grouped_cv_predict(learner, X, cohort, fold_ids=None):
    """Repeated patient-grouped CV within one cohort (MU internal reference) on the given fold ids."""
    fold_ids = mu_fold_ids(cohort) if fold_ids is None else fold_ids
    oof = np.zeros(fold_ids.shape)
    for r, f in enumerate(fold_ids):
        for k in np.unique(f):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            oof[r, te] = fit(learner, X.iloc[tr], cohort.iloc[tr].reset_index(drop=True), seed=r)(X.iloc[te])
    return oof


def shrink_fit(Xs, y, beta0, b0, lam):
    """Logistic regression penalised towards (beta0, b0): MU coefficients as the prior."""
    from scipy.optimize import minimize

    def obj(theta):
        b, beta = theta[0], theta[1:]
        z = b + Xs @ beta
        loss = np.mean(np.logaddexp(0, z) - y * z)
        return loss + lam * (np.sum((beta - beta0) ** 2) + (b - b0) ** 2)
    res = minimize(obj, np.r_[b0, beta0], method="L-BFGS-B")
    return res.x[0], res.x[1:]


SHRINK_LAMBDAS = (0.003, 0.01, 0.03, 0.1, 0.3, 1.0)


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def recalibrate(p_train, y_train, p_test, min_slope=0.05):
    """Unpenalised logistic recalibration on the logit; returns (recalibrated test risk, slope before flooring)."""
    cal = LogisticRegression(penalty=None, max_iter=1000).fit(_logit(p_train)[:, None], y_train.astype(int))
    a, b = cal.coef_[0][0], cal.intercept_[0]
    return 1 / (1 + np.exp(-(max(a, min_slope) * _logit(p_test) + b))), float(a)


def choose_shrink(Xs, y, k, groups, beta0, b0, seed):
    """Shrinkage strength towards the MU coefficients by inner grouped CV (log-loss) on training rows k."""
    best, best_loss = SHRINK_LAMBDAS[-1], np.inf
    for lam in SHRINK_LAMBDAS:
        losses = []
        for itr, ite in StratifiedGroupKFold(3, shuffle=True, random_state=seed).split(k, y[k], groups.iloc[k]):
            bb, be = shrink_fit(Xs[k[itr]], y[k[itr]], beta0, b0, lam)
            pz = 1 / (1 + np.exp(-(bb + Xs[k[ite]] @ be)))
            losses.append(-np.mean(y[k[ite]] * np.log(pz + 1e-9) + (1 - y[k[ite]]) * np.log(1 - pz + 1e-9)))
        if np.mean(losses) < best_loss:
            best, best_loss = lam, np.mean(losses)
    return best


def adapt_on_lumiere(learner, cols, mc, MX, lc, LX, fold_ids=None):
    """Every arm adapted on the training LUMIERE patients of each fold and scored on the held-out ones.
    Returns ({arm: (n_repeats x n_scans) held-out predictions}, fold_ids, recalibration slopes)."""
    y = lc[f"label_{H}"].to_numpy()
    fold_ids = lumiere_fold_ids(lc) if fold_ids is None else fold_ids
    locked_fn, mu_pre, mu_model = fit(learner, MX[cols], mc, return_parts=True)
    locked = locked_fn(LX[cols])
    arms = ["locked", "recalibrated", "finetune_pooled", "lumiere_only"] + (["finetune_shrink"] if learner == "ridge" else [])
    oof = {a: np.zeros(fold_ids.shape) for a in arms}
    slopes = []
    for r, f in enumerate(fold_ids):
        for fk in np.unique(f):
            tr, te = np.where(f != fk)[0], np.where(f == fk)[0]
            k = tr[~np.isnan(y[tr])]
            oof["locked"][r, te] = locked[te]
            oof["recalibrated"][r, te], sl = recalibrate(locked[k], y[k], locked[te])
            slopes.append(sl)
            pooled_X = pd.concat([MX[cols], LX[cols].iloc[tr]], ignore_index=True)
            pooled_c = pd.concat([mc, lc.iloc[tr]], ignore_index=True)
            wts = np.r_[np.ones(len(mc)), np.full(len(tr), 3.0)]
            oof["finetune_pooled"][r, te] = fit(learner, pooled_X, pooled_c, seed=r, weights=wts)(LX[cols].iloc[te])
            oof["lumiere_only"][r, te] = fit(learner, LX[cols].iloc[tr], lc.iloc[tr].reset_index(drop=True), seed=r)(LX[cols].iloc[te])
            if learner == "ridge":
                Xs = mu_pre.transform(LX[cols])
                beta0, b0 = mu_model.coef_[0], mu_model.intercept_[0]
                lam = choose_shrink(Xs, y, k, lc.patient_id, beta0, b0, r)
                bb, be = shrink_fit(Xs[k], y[k], beta0, b0, lam)
                oof["finetune_shrink"][r, te] = 1 / (1 + np.exp(-(bb + Xs[te] @ be)))
    return oof, fold_ids, np.asarray(slopes)


def verified_fold_auc(lc, P, fold_ids):
    """Secondary: plain AUC on verified labels per held-out fold, averaged."""
    from sklearn.metrics import roc_auc_score
    y = lc[f"label_{H}"].to_numpy()
    a = []
    for r, f in enumerate(fold_ids):
        for k in np.unique(f):
            kt = (f == k) & ~np.isnan(y)
            if len(np.unique(y[kt])) == 2:
                a.append(roc_auc_score(y[kt], P[r, kt]))
    return float(np.mean(a))


@counted_warnings
def run_combo(job):
    train_pop, fs, learner, n_boot = job
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    cols = FEATURE_SETS[fs]
    lc, LX = lumiere_table()
    mc, MX = mu_table(train_pop == "grade4")
    base = {"train": train_pop, "features": fs, "learner": learner}
    rows = []
    mu_ids = mu_fold_ids(mc)
    mu_oof = grouped_cv_predict(learner, MX[cols], mc, mu_ids)
    b = repeated_bootstrap(mc, {"m": mu_oof}, H, n_boot=n_boot).iloc[0]
    rows.append({**base, "arm": "mu_cv", "cohort": "MU", **repeated_point_metrics(mc, mu_oof, H),
                 "auc_ipcw_lo": b.auc_ipcw_lo, "auc_ipcw_hi": b.auc_ipcw_hi, **fold_mean_metrics(mc, mu_oof, mu_ids, H)})
    oof, ids, slopes = adapt_on_lumiere(learner, cols, mc, MX, lc, LX)
    vol = [c for c in cols if c in SHARED["volumes"]]
    for norm in COHORT_NORMS if vol else ():
        p = fit(learner, within_cohort_normalise(MX, vol, norm)[cols], mc)(within_cohort_normalise(LX, vol, norm)[cols])
        oof[f"locked+cohort_norm_{norm}"] = np.tile(p, (len(ids), 1))
    fb = fold_mean_bootstrap(lc, oof, ids, H, reference="locked", n_boot=n_boot).set_index("arm")
    for arm, P in oof.items():
        row = {**base, "arm": arm, "cohort": "LUMIERE", **fold_mean_metrics(lc, P, ids, H),
               "auc_verified_fold_mean": verified_fold_auc(lc, P, ids), **fb.loc[arm].dropna().to_dict()}
        if arm.startswith("locked"):  # one prediction per scan: also pooled over all of LUMIERE
            pm = point_metrics(lc, P[0], H)
            cb = cluster_bootstrap(lc, {"m": P[0]}, H, reference="m", n_boot=n_boot).iloc[0]
            row.update({f"{k}_pooled": v for k, v in pm.items()})
            row.update(auc_ipcw_pooled_lo=cb.auc_ipcw_lo, auc_ipcw_pooled_hi=cb.auc_ipcw_hi)
        if arm == "recalibrated":
            row.update(recal_slope_median=float(np.median(slopes)), recal_slope_floored=int((slopes < 0.05).sum()))
        rows.append(row)
    return rows, f"{train_pop}|{fs}|{learner}", oof["locked"][0]


def main(argv=None) -> None:
    import argparse
    ap = argparse.ArgumentParser(prog="prism external", description=__doc__)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args(argv)
    lc, LX = lumiere_table()
    have_vol = not LX["log_et_cc"].isna().all()
    if not have_vol:
        print("WARNING: LUMIERE volumes missing — volume feature sets will be skipped")
    jobs = [(tp, fs, l, a.n_boot) for tp in ("grade4", "all_glioma") for fs, cols in FEATURE_SETS.items()
            for l in ("ridge", "gbm") if have_vol or "log_et_cc" not in cols]
    with ProcessPoolExecutor(a.workers) as ex:
        outs = list(ex.map(run_combo, jobs))
    res = pd.DataFrame([r for o in outs for r in o[0]])
    out = RESULTS / "external_lumiere"
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "results.csv", index=False)
    pd.DataFrame({k: p for _, k, p in outs}).assign(scan_id=lc.scan_id).to_csv(out / "locked_predictions.csv", index=False)
    order = ["mu_cv", "locked", "recalibrated", "finetune_shrink", "finetune_pooled", "lumiere_only",
             *[f"locked+cohort_norm_{n}" for n in COHORT_NORMS]]
    idx = ["train", "features", "learner"]
    print("IPCW AUC, mean over held-out folds (MU: shared MU folds; LUMIERE: identical 5x5 patient folds for every arm)")
    print(res.pivot_table(index=idx, columns="arm", values="auc_ipcw_fold_mean")
          .reindex(columns=[o for o in order if o in set(res.arm)]).round(3).to_string())
    print("MU CV, mean over repeats of pooled-OOF AUC:")
    print(res[res.arm == "mu_cv"][idx + ["auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi"]].round(3).to_string(index=False))
    print("Calibration on LUMIERE (O/E pooled over held-out predictions | per-fold slope median):")
    c = res[res.arm != "mu_cv"]
    print(c.pivot_table(index=idx, columns="arm", values=["oe_ratio_pooled", "cal_slope_fold_median"]).round(2).to_string())
    print("Locked model(s) on all of LUMIERE (pooled IPCW AUC, 95% CI, O/E, slope) and per fold:")
    print(res[res.arm.str.startswith("locked")][idx + ["arm", "auc_ipcw_pooled", "auc_ipcw_pooled_lo", "auc_ipcw_pooled_hi",
                                                       "oe_ratio_pooled", "cal_slope_pooled", "auc_ipcw_fold_mean",
                                                       "auc_ipcw_fold_mean_lo", "auc_ipcw_fold_mean_hi"]]
          .round(3).to_string(index=False))
