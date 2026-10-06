#!/usr/bin/env python3
"""C2: which feature groups predict 120-day progression? All 63 combinations of 6 groups, 2 learners.

Every fitted step (imputation, scaling, radiomics selection, penalty) is inside the training fold.
Because picking the best of 126 configurations is itself optimistic, the search is also run *nested*:
in each outer fold the combination is chosen by inner patient-grouped CV on training patients only,
and the outer-fold score of that choice is the honest estimate of "search + model".

    uv run python -m prism.experiments.c2_feature_search [--population grade4] [--n-boot 500]
    -> outputs/c2/{grid.csv, nested.csv, permutation.csv, summary.md}
"""

from __future__ import annotations

import argparse
import itertools
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from prism.config import OUTPUTS
from prism.features import clinical, legacy_radiomics
from prism.formulations import fit as fit_logistic
from prism.metrics import cluster_bootstrap, point_metrics

H = 120
GROUPS = ("clinical", "timing", "volumes", "morphology", "delta", "radiomics")
LEARNERS = ("ridge", "gbm")
RADIOMICS_K = 20


# ---------------------------------------------------------------- feature groups
def build_groups(cohort: pd.DataFrame) -> dict[str, pd.DataFrame]:
    m = pd.read_csv(OUTPUTS / "measurements" / "measurements.csv").set_index("scan_id").reindex(cohort.scan_id)
    m.index = cohort.index
    log1p = lambda s: np.log1p(s.clip(lower=0))
    slog = lambda s: np.sign(s) * np.log1p(s.abs())
    rt = cohort["days_since_rt_end"]
    groups = {
        "clinical": clinical(cohort),
        "timing": pd.DataFrame({"days_from_diagnosis": cohort["days_from_diagnosis_to_mri"],
                                "days_since_rt_end": rt, "rt_date_unknown": rt.isna().astype(float),
                                "early_post_rt": cohort["early_post_rt"].astype(float),
                                "visit_index": cohort["visit_index"]}),
        "volumes": pd.DataFrame({f"log_{c}": log1p(m[c]) for c in
                                 ("et_cc", "netc_cc", "snfh_cc", "rc_cc", "tumor_cc", "lesion_cc")}),
        "morphology": pd.DataFrame({
            "et_fraction_of_tumor": m.et_fraction_of_tumor, "log_snfh_to_tumor": np.log1p(m.snfh_to_tumor_ratio),
            "has_cavity": m.has_cavity, "et_n_components": m.et_n_components,
            "et_largest_component_fraction": m.et_largest_component_fraction,
            "log_et_max_axial": log1p(m.et_max_axial_mm2), "et_near_cavity_fraction": m.et_near_cavity_fraction,
            "et_cavity_distance": log1p(m.et_cavity_distance_mm_p50), "t1c_et_rel": m.t1c_et_rel,
            "t1c_et_p90_rel": m.t1c_et_p90_rel, "t1c_netc_rel": m.t1c_netc_rel,
            "flair_snfh_rel": m.flair_snfh_rel, "flair_netc_rel": m.flair_netc_rel}),
        # No prior scan -> change set to 0 and flagged by has_prior.
        "delta": pd.concat([m[["has_prior", "n_prior_scans"]],
                            np.log1p(m[["days_since_prior"]].fillna(0)),
                            m.filter(regex=r"^logratio_").fillna(0),
                            slog(m.filter(regex=r"^rate_")).fillna(0),
                            m[["d_et_n_components", "d_t1c_et_rel", "d_flair_snfh_rel",
                               "vol_pd_flag", "new_et_component"]].fillna(0)], axis=1),
        "radiomics": legacy_radiomics(cohort).astype(float),
    }
    return groups


def preprocessor(combo: tuple[str, ...], groups: dict[str, pd.DataFrame]) -> ColumnTransformer:
    parts = []
    for g in combo:
        cols = list(groups[g].columns)
        if g == "radiomics":
            pipe = Pipeline([("imp", SimpleImputer(strategy="median")), ("var", VarianceThreshold()),
                             ("sc", StandardScaler()), ("sel", SelectKBest(f_classif, k=RADIOMICS_K))])
        else:
            pipe = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())])
        parts.append((g, pipe, cols))
    return ColumnTransformer(parts)


GBM = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=15,
                                     l2_regularization=1.0, random_state=0)


def fit_predict(learner, combo, groups, X, cohort, tr, te, seed=0):
    """Train on verified labels of `tr` (censored dropped), predict risk for `te`. Returns (p_te, p_tr)."""
    y = cohort[f"label_{H}"].to_numpy()
    tr_known = tr[~np.isnan(y[tr])]
    pre = preprocessor(combo, groups).fit(X.iloc[tr_known], y[tr_known])
    Xtr, Xte = pre.transform(X.iloc[tr_known]), pre.transform(X.iloc[te])
    if learner == "ridge":
        d = cohort.iloc[tr_known].reset_index(drop=True)
        model, _ = fit_logistic("verified", Xtr, d, H, seed=seed)
    else:
        model = clone(GBM).set_params(random_state=seed).fit(Xtr, y[tr_known].astype(int))
    return model.predict_proba(Xte)[:, 1], (model.predict_proba(Xtr)[:, 1], y[tr_known])


ALL_COMBOS = [c for r in range(1, len(GROUPS) + 1) for c in itertools.combinations(GROUPS, r)]


def _context(population):
    cohort = pd.read_csv(OUTPUTS / "cohort" / "cohort.csv")
    if population == "grade4":
        cohort = cohort[cohort.grade4].reset_index(drop=True)
    folds = pd.read_csv(OUTPUTS / "cohort" / "folds.csv")
    groups = build_groups(cohort)
    X = pd.concat(groups.values(), axis=1)
    return cohort, folds, groups, X


def _fold_ids(cohort, folds, r):
    return cohort.scan_id.map(folds[folds.repeat == r].set_index("scan_id").fold).to_numpy()


# ---------------------------------------------------------------- grid: every combination x learner
def run_grid_job(job):
    population, learner, combo, n_boot = job
    warnings.filterwarnings("ignore")
    threadpool_limits(1)
    cohort, folds, groups, X = _context(population)
    n_rep = folds.repeat.nunique()
    oof = np.zeros((n_rep, len(cohort)))
    train_aucs = []
    for r in range(n_rep):
        f = _fold_ids(cohort, folds, r)
        for k in np.unique(f):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            oof[r, te], (ptr, ytr) = fit_predict(learner, combo, groups, X, cohort, tr, te, seed=r)
            train_aucs.append(roc_auc_score(ytr, ptr))
    p = oof.mean(axis=0)
    pm = point_metrics(cohort, p, H)
    rep_aucs = [point_metrics(cohort, oof[r], H)["auc_ipcw"] for r in range(n_rep)]
    row = {"population": population, "learner": learner, "combo": "+".join(combo), "n_groups": len(combo),
           **pm, "auc_ipcw_repeat_sd": float(np.std(rep_aucs)), "train_auc": float(np.mean(train_aucs)),
           "overfit_gap": float(np.mean(train_aucs) - np.mean(rep_aucs))}
    if n_boot:
        b = cluster_bootstrap(cohort, {"m": p}, H, reference="m", n_boot=n_boot).iloc[0]
        row.update(auc_ipcw_lo=b.auc_ipcw_lo, auc_ipcw_hi=b.auc_ipcw_hi)
    return row, p


# ---------------------------------------------------------------- nested: choose the combination inside each fold
def inner_score(combo, groups, X, cohort, tr):
    """Mean inner patient-grouped 3-fold AUC (verified labels) of the ridge model on training patients."""
    y = cohort[f"label_{H}"].to_numpy()
    aucs = []
    for itr, ite in GroupKFold(n_splits=3).split(tr, groups=cohort.patient_id.iloc[tr]):
        a, b = tr[itr], tr[ite]
        p, _ = fit_predict("ridge", combo, groups, X, cohort, a, b)
        known = ~np.isnan(y[b])
        aucs.append(roc_auc_score(y[b][known], p[known]))
    return float(np.mean(aucs))


def run_nested_job(job):
    population, r, k, permute_seed = job
    warnings.filterwarnings("ignore")
    threadpool_limits(1)
    cohort, folds, groups, X = _context(population)
    if permute_seed is not None:  # permutation test: same shuffle as in nested() for this seed
        cohort = _permute_outcomes(cohort, np.random.default_rng(permute_seed))
    f = _fold_ids(cohort, folds, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    scores = {c: inner_score(c, groups, X, cohort, tr) for c in ALL_COMBOS}
    best = max(scores, key=scores.get)
    p, _ = fit_predict("ridge", best, groups, X, cohort, tr, te, seed=r)
    return {"repeat": r, "fold": k, "permute_seed": permute_seed, "chosen": "+".join(best),
            "inner_auc": scores[best]}, te, p


OUTCOME_COLS = ["event", "time_to_event", "status_known_indefinitely", "label_90", "label_120", "label_180",
                "naive_label_90", "naive_label_120", "naive_label_180"]


def _permute_outcomes(cohort, rng):
    """Shuffle outcome rows across scans while keeping features fixed (breaks any feature-outcome link)."""
    c = cohort.copy()
    idx = rng.permutation(len(c))
    for col in OUTCOME_COLS:  # per column, so dtypes are preserved
        c[col] = c[col].to_numpy()[idx]
    return c


def nested(population, workers, permute_seeds=(None,)):
    cohort, folds, _, _ = _context(population)
    jobs = [(population, r, k, s) for s in permute_seeds for r in sorted(folds.repeat.unique()) for k in range(5)]
    with ProcessPoolExecutor(workers) as ex:
        outs = list(ex.map(run_nested_job, jobs))
    rows, results = [], {}
    for meta, te, p in outs:
        rows.append(meta)
        results.setdefault((meta["permute_seed"], meta["repeat"]), np.zeros(len(cohort)))[te] = p
    summary = []
    for s in permute_seeds:
        oofs = [results[(s, r)] for r in sorted(folds.repeat.unique())]
        c = cohort if s is None else _permute_outcomes(cohort, np.random.default_rng(s))
        aucs = [point_metrics(c, o, H)["auc_ipcw"] for o in oofs]
        summary.append({"permute_seed": s, "auc_ipcw_mean_over_repeats": float(np.mean(aucs)),
                        "auc_ipcw_sd": float(np.std(aucs)), "auc_ipcw_of_averaged": point_metrics(c, np.mean(oofs, 0), H)["auc_ipcw"]})
    return pd.DataFrame(rows), pd.DataFrame(summary)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--population", default="grade4", choices=["grade4", "all_glioma"])
    ap.add_argument("--n-boot", type=int, default=500)
    ap.add_argument("--workers", type=int, default=64)
    ap.add_argument("--n-permutations", type=int, default=5)
    ap.add_argument("--skip-nested", action="store_true")
    ap.add_argument("--skip-grid", action="store_true")
    a = ap.parse_args()
    out = OUTPUTS / "c2" / a.population
    out.mkdir(parents=True, exist_ok=True)

    if a.skip_grid:
        grid = pd.read_csv(out / "grid.csv")
    else:
        jobs = [(a.population, l, c, a.n_boot) for l in LEARNERS for c in ALL_COMBOS]
        with ProcessPoolExecutor(a.workers) as ex:
            outs = list(ex.map(run_grid_job, jobs))
        grid = pd.DataFrame([o[0] for o in outs]).sort_values("auc_ipcw", ascending=False)
        grid.to_csv(out / "grid.csv", index=False)
    print(grid[["learner", "combo", "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "auc_ipcw_repeat_sd", "train_auc",
                "overfit_gap", "cal_slope", "oe_ratio"]].head(20).round(3).to_string(index=False))

    if not a.skip_nested:
        seeds = (None, *range(a.n_permutations))
        choices, summ = nested(a.population, a.workers, seeds)
        choices.to_csv(out / "nested_choices.csv", index=False)
        summ.to_csv(out / "nested.csv", index=False)
        print(summ.round(3).to_string(index=False))
        print(choices[choices.permute_seed.isna()].chosen.value_counts().to_string())


if __name__ == "__main__":
    main()
