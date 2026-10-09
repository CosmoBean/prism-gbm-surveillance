#!/usr/bin/env python3
"""External test on LUMIERE with features shared by both cohorts.

Arms (same features, H = 120 d, verified labels for training, IPCW AUC for evaluation):
  mu_cv          MU repeated patient-grouped CV (internal reference)
  locked         model trained on all MU scans, applied once to LUMIERE
  recalibrated   locked model + logistic recalibration (intercept, slope) fitted on other LUMIERE patients (grouped CV)
  lumiere_only   model trained and tested within LUMIERE (grouped CV) — the local ceiling

    uv run python -m prism.experiments.external_lumiere
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from prism.config import OUTPUTS
from prism.features import clinical, treatment
from prism.formulations import fit as fit_ridge
from prism.metrics import cluster_bootstrap, point_metrics

H = 120
# DeepBraTumIA compartments mapped to MU: enhancing -> ET, necrosis -> NETC, edema -> SNFH.
FEATURE_SETS = {
    "clinical": ["age", "male", "idh_mutant", "idh_unknown", "mgmt_methylated", "mgmt_unknown"],
    "clinical+timing": ["age", "male", "idh_mutant", "idh_unknown", "mgmt_methylated", "mgmt_unknown",
                        "log_days_since_surgery", "early_post_rt"],
    "volumes": ["log_et_cc", "log_netc_cc", "log_snfh_cc"],
    "clinical+timing+volumes": ["age", "male", "idh_mutant", "idh_unknown", "mgmt_methylated", "mgmt_unknown",
                                "log_days_since_surgery", "early_post_rt", "log_et_cc", "log_netc_cc", "log_snfh_cc"],
}
GBM = HistGradientBoostingClassifier(max_depth=2, learning_rate=0.03, max_iter=150, min_samples_leaf=20,
                                     l2_regularization=2.0, max_features=0.5, random_state=0)
PRE = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())])


def mu_table(grade4_only: bool) -> pd.DataFrame:
    c = pd.read_csv(OUTPUTS / "cohort" / "cohort.csv")
    if grade4_only:
        c = c[c.grade4].reset_index(drop=True)
    m = pd.read_csv(OUTPUTS / "measurements" / "measurements.csv").set_index("scan_id").reindex(c.scan_id)
    t = treatment(c)
    X = clinical(c)
    X["log_days_since_surgery"] = np.log1p((c.days_from_diagnosis_to_mri - t.surgery_day).clip(lower=0))
    X["early_post_rt"] = c.early_post_rt.astype(float)
    for k in ("et", "netc", "snfh"):
        X[f"log_{k}_cc"] = np.log1p(m[f"{k}_cc"].to_numpy())
    return c, X


def lumiere_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    c = pd.read_csv(OUTPUTS / "lumiere" / "cohort.csv")
    X = clinical(c)
    X["log_days_since_surgery"] = np.log1p(c.days_since_surgery)
    X["early_post_rt"] = c.early_post_rt.astype(float)
    vol = {"et": "raw_Enhancing_Core", "netc": "raw_Necrotic_NonEnhancing", "snfh": "raw_Edema_Compartment"}
    for k, col in vol.items():
        X[f"log_{k}_cc"] = np.log1p(c[col] / 1000.0) if col in c else np.nan
    return c, X


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


def grouped_cv_predict(learner, X, cohort, n_rep=5):
    """Repeated patient-grouped CV within one cohort (MU internal reference)."""
    y = cohort[f"label_{H}"].to_numpy()
    strata = pd.Series(y).map({1.0: "p", 0.0: "n"}).fillna("c")
    oof = np.zeros((n_rep, len(cohort)))
    for r in range(n_rep):
        for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=r).split(X, strata, cohort.patient_id):
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


def adapt_on_lumiere(learner, cols, mc, MX, lc, LX, n_rep=5):
    """Grouped CV over LUMIERE patients. Each arm is adapted on training patients and scored on held-out ones."""
    from sklearn.metrics import roc_auc_score
    y = lc[f"label_{H}"].to_numpy()
    strata = pd.Series(y).map({1.0: "p", 0.0: "n"}).fillna("c")
    locked_fn, mu_pre, mu_model = fit(learner, MX[cols], mc, return_parts=True)
    locked = locked_fn(LX[cols])
    arms = ["locked", "recalibrated", "finetune_pooled", "lumiere_only"] + (["finetune_shrink"] if learner == "ridge" else [])
    oof = {a: np.zeros((n_rep, len(lc))) for a in arms}
    fold_auc = {a: [] for a in arms}
    for r in range(n_rep):
        for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=r).split(LX, strata, lc.patient_id):
            k = tr[~np.isnan(y[tr])]
            oof["locked"][r, te] = locked[te]
            cal = LogisticRegression(C=1.0).fit(_logit(locked[k])[:, None], y[k].astype(int))
            a, b = max(cal.coef_[0][0], 0.05), cal.intercept_[0]
            oof["recalibrated"][r, te] = 1 / (1 + np.exp(-(a * _logit(locked[te]) + b)))
            pooled_X = pd.concat([MX[cols], LX[cols].iloc[tr]], ignore_index=True)
            pooled_c = pd.concat([mc, lc.iloc[tr]], ignore_index=True)
            wts = np.r_[np.ones(len(mc)), np.full(len(tr), 3.0)]
            oof["finetune_pooled"][r, te] = fit(learner, pooled_X, pooled_c, seed=r, weights=wts)(LX[cols].iloc[te])
            oof["lumiere_only"][r, te] = fit(learner, LX[cols].iloc[tr], lc.iloc[tr].reset_index(drop=True), seed=r)(LX[cols].iloc[te])
            if learner == "ridge":
                Xs = mu_pre.transform(LX[cols])
                beta0, b0 = mu_model.coef_[0], mu_model.intercept_[0]
                # choose the shrinkage strength by inner grouped CV on the training patients
                best, best_loss = SHRINK_LAMBDAS[-1], np.inf
                for lam in SHRINK_LAMBDAS:
                    losses = []
                    for itr, ite in StratifiedGroupKFold(3, shuffle=True, random_state=r).split(k, y[k], lc.patient_id.iloc[k]):
                        bb, be = shrink_fit(Xs[k[itr]], y[k[itr]], beta0, b0, lam)
                        pz = 1 / (1 + np.exp(-(bb + Xs[k[ite]] @ be)))
                        losses.append(-np.mean(y[k[ite]] * np.log(pz + 1e-9) + (1 - y[k[ite]]) * np.log(1 - pz + 1e-9)))
                    if np.mean(losses) < best_loss:
                        best, best_loss = lam, np.mean(losses)
                bb, be = shrink_fit(Xs[k], y[k], beta0, b0, best)
                oof["finetune_shrink"][r, te] = 1 / (1 + np.exp(-(bb + Xs[te] @ be)))
            kt = te[~np.isnan(y[te])]
            if len(np.unique(y[kt])) == 2:
                for a_ in arms:
                    fold_auc[a_].append(roc_auc_score(y[kt], oof[a_][r, kt]))
    return oof, fold_auc


def main() -> None:
    warnings.filterwarnings("ignore")
    lc, LX = lumiere_table()
    have_vol = not LX["log_et_cc"].isna().all()
    if not have_vol:
        print("WARNING: LUMIERE volumes missing — volume feature sets will be skipped")
    rows, preds = [], {}
    for train_pop in ("grade4", "all_glioma"):
        mc, MX = mu_table(train_pop == "grade4")
        for fs, cols in FEATURE_SETS.items():
            if "log_et_cc" in cols and not have_vol:
                continue
            for learner in ("ridge", "gbm"):
                mu_oof = grouped_cv_predict(learner, MX[cols], mc)
                oof, fold_auc = adapt_on_lumiere(learner, cols, mc, MX, lc, LX)
                arm_preds = {"mu_cv": (mc, mu_oof.mean(0))} | {a: (lc, o.mean(0)) for a, o in oof.items()}
                for arm, (coh, p) in arm_preds.items():
                    pm = point_metrics(coh, p, H)
                    b = cluster_bootstrap(coh, {"m": p}, H, reference="m", n_boot=1000).iloc[0]
                    fa = fold_auc.get(arm, [])
                    rows.append({"train": train_pop, "features": fs, "learner": learner, "arm": arm, **pm,
                                 "auc_ipcw_lo": b.auc_ipcw_lo, "auc_ipcw_hi": b.auc_ipcw_hi,
                                 "auc_per_fold_mean": float(np.mean(fa)) if fa else np.nan,
                                 "auc_per_fold_sd": float(np.std(fa)) if fa else np.nan})
                preds[f"{train_pop}|{fs}|{learner}"] = oof["locked"][0]
    res = pd.DataFrame(rows)
    out = OUTPUTS / "external_lumiere"
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "results.csv", index=False)
    pd.DataFrame(preds).assign(scan_id=lc.scan_id).to_csv(out / "locked_predictions.csv", index=False)
    order = ["mu_cv", "locked", "recalibrated", "finetune_shrink", "finetune_pooled", "lumiere_only"]
    print("AUC: MU internal CV (pooled IPCW) and LUMIERE arms (per-fold mean over held-out LUMIERE patients)")
    t = res.assign(auc=np.where(res.arm == "mu_cv", res.auc_ipcw, res.auc_per_fold_mean))
    print(t.pivot_table(index=["train", "features", "learner"], columns="arm", values="auc")
          .reindex(columns=[o for o in order if o in set(t.arm)]).round(3).to_string())
    print("Calibration on LUMIERE (O/E | slope):")
    c = res[res.arm != "mu_cv"]
    print(c.pivot_table(index=["train", "features", "learner"], columns="arm", values=["oe_ratio", "cal_slope"]).round(2).to_string())
    print("Locked model on all of LUMIERE (pooled IPCW AUC, 95% CI):")
    print(res[res.arm == "locked"][["train", "features", "learner", "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
