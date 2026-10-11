"""C2: which feature groups predict 120-day progression? All 63 combinations of 6 groups, 2 learners.

Every fitted step (imputation, scaling, radiomics selection, penalty) is inside the training fold.
Because picking the best of 126 configurations is itself optimistic, the search is also run *nested*:
in each outer fold the (learner, combination) is chosen by inner patient-grouped CV on training patients only,
and the outer-fold score of that choice is the honest estimate of "search + model". The nested search covers both
learners (126 candidates) by default; `--nested-learners ridge` restricts it to the 63 ridge combinations.

Permutation control: outcomes are permuted at the patient level (each patient's whole outcome block, i.e. the
outcome rows of its scans in visit order, is moved to another patient with the same number of scans), features and
folds stay fixed, and the full nested pipeline is re-run. Empirical p = (1 + #{perm >= observed}) / (1 + n_perm) on
the mean-over-repeats IPCW AUC.

Headline metric everywhere: mean over the 5 repeats of each repeat's pooled-OOF IPCW AUC (`*_averaged` = AUC of the
repeat-averaged prediction, the earlier optimistic headline); CIs from a patient-cluster bootstrap of that mean.

    python -m prism c2 [--population grade4] [--n-boot 500] [--n-permutations 100] [--nested-learners ridge,gbm]
    -> outputs/results/c2/<population>/{grid.csv, nested.csv, nested_choices.csv, permutation.csv}
"""

from __future__ import annotations

import argparse
import itertools
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from prism.config import RESULTS
from prism.data.mu import load_cohort
from prism.experiments.c3_radiomics import ImputeWithFlags, f_classif_quiet
from prism.features.tabular import groups as feature_groups
from prism.models.folds import load_folds
from prism.models.formulations import fit as fit_logistic
from prism.models.metrics import counted_warnings, repeated_bootstrap, repeated_point_metrics

H = 120
GROUPS = ("clinical", "timing", "volumes", "morphology", "delta", "radiomics")
LEARNERS = ("ridge", "gbm")
RADIOMICS_K = 20


# ---------------------------------------------------------------- models
def preprocessor(combo: tuple[str, ...], groups: dict[str, pd.DataFrame]) -> ColumnTransformer:
    parts = []
    for g in combo:
        cols = list(groups[g].columns)
        if g == "radiomics":
            pipe = Pipeline([("imp", ImputeWithFlags()), ("var", VarianceThreshold()),  # same imputation as c3
                             ("sc", StandardScaler()), ("sel", SelectKBest(f_classif_quiet, k=RADIOMICS_K))])
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
    cohort = load_cohort(population)
    folds = load_folds()
    groups = {g: x for g, x in feature_groups(cohort).items() if g in GROUPS}
    X = pd.concat(groups.values(), axis=1)
    return cohort, folds, groups, X


def _fold_ids(cohort, folds, r):
    return cohort.scan_id.map(folds[folds.repeat == r].set_index("scan_id").fold).to_numpy()


# ---------------------------------------------------------------- grid: every combination x learner
@counted_warnings
def run_grid_job(job):
    population, learner, combo, n_boot = job
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
    pm = repeated_point_metrics(cohort, oof, H)
    row = {"population": population, "learner": learner, "combo": "+".join(combo), "n_groups": len(combo),
           **pm, "train_auc": float(np.mean(train_aucs)), "overfit_gap": float(np.mean(train_aucs) - pm["auc_ipcw"])}
    if n_boot:
        b = repeated_bootstrap(cohort, {"m": oof}, H, n_boot=n_boot).iloc[0]
        row.update(auc_ipcw_lo=b.auc_ipcw_lo, auc_ipcw_hi=b.auc_ipcw_hi)
    return row, oof.mean(0)


# ---------------------------------------------------------------- nested: choose the combination inside each fold
def inner_score(cfg, groups, X, cohort, tr):
    """Mean inner patient-grouped 3-fold AUC (verified labels) of (learner, combo) on training patients."""
    learner, combo = cfg
    y = cohort[f"label_{H}"].to_numpy()
    aucs = []
    for itr, ite in GroupKFold(n_splits=3).split(tr, groups=cohort.patient_id.iloc[tr]):
        a, b = tr[itr], tr[ite]
        p, _ = fit_predict(learner, combo, groups, X, cohort, a, b)
        known = ~np.isnan(y[b])
        aucs.append(roc_auc_score(y[b][known], p[known]))
    return float(np.mean(aucs))


@counted_warnings
def run_nested_job(job):
    population, r, k, permute_seed, learners = job
    threadpool_limits(1)
    cohort, folds, groups, X = _context(population)
    if permute_seed is not None:  # permutation control: same patient-level shuffle as in nested() for this seed
        cohort = permute_patients(cohort, permute_seed)
    f = _fold_ids(cohort, folds, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    scores = {(l, c): inner_score((l, c), groups, X, cohort, tr) for l in learners for c in ALL_COMBOS}
    best = max(scores, key=scores.get)
    p, _ = fit_predict(best[0], best[1], groups, X, cohort, tr, te, seed=r)
    return {"repeat": r, "fold": k, "permute_seed": permute_seed, "learners": "+".join(learners),
            "chosen_learner": best[0], "chosen": "+".join(best[1]), "inner_auc": scores[best]}, te, p


OUTCOME_COLS = ["event", "time_to_event", "status_known_indefinitely", "label_90", "label_120", "label_180",
                "naive_label_90", "naive_label_120", "naive_label_180"]


def permute_patients(cohort, seed):
    """Patient-level permutation: move each patient's outcome block (its scans' outcome rows in visit order) to another
    patient with the same number of scans. Features, scan order and folds are unchanged; within-patient outcome
    correlation is preserved. Patients with a unique scan count keep their own outcomes."""
    rng = np.random.default_rng(seed)
    c = cohort.copy()
    order = c.sort_values(["patient_id", "visit_index"]).index
    blocks = {p: list(ix) for p, ix in c.loc[order].groupby("patient_id", sort=True).groups.items()}
    by_size = {}
    for p, ix in blocks.items():
        by_size.setdefault(len(ix), []).append(p)
    src = np.arange(len(c))
    for pats in by_size.values():
        for p, q in zip(pats, rng.permutation(pats)):  # patient p receives q's outcomes
            src[c.index.get_indexer(blocks[p])] = c.index.get_indexer(blocks[q])
    for col in OUTCOME_COLS:  # per column, so dtypes are preserved
        c[col] = c[col].to_numpy()[src]
    return c


def nested(population, workers, learners, permute_seeds=(None,), n_boot=0):
    cohort, folds, _, _ = _context(population)
    reps = sorted(folds.repeat.unique())
    jobs = [(population, r, k, s, learners) for s in permute_seeds for r in reps for k in range(5)]
    with ProcessPoolExecutor(workers) as ex:
        outs = list(ex.map(run_nested_job, jobs))
    rows, results = [], {}
    for meta, te, p in outs:
        rows.append(meta)
        results.setdefault((meta["permute_seed"], meta["repeat"]), np.zeros(len(cohort)))[te] = p
    summary = []
    for s in permute_seeds:
        oof = np.array([results[(s, r)] for r in reps])
        c = cohort if s is None else permute_patients(cohort, s)
        pm = repeated_point_metrics(c, oof, H)
        row = {"permute_seed": s, "learners": "+".join(learners), "auc_ipcw": pm["auc_ipcw"],
               "auc_ipcw_sd": pm["auc_ipcw_repeat_sd"], "auc_ipcw_averaged": pm["auc_ipcw_averaged"],
               "brier_ipcw": pm["brier_ipcw"], "cal_slope": pm["cal_slope"], "oe_ratio": pm["oe_ratio"]}
        if s is None and n_boot:
            b = repeated_bootstrap(c, {"m": oof}, H, n_boot=n_boot).iloc[0]
            row.update(auc_ipcw_lo=b.auc_ipcw_lo, auc_ipcw_hi=b.auc_ipcw_hi)
        summary.append(row)
    return pd.DataFrame(rows), pd.DataFrame(summary)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism c2", description=__doc__)
    ap.add_argument("--population", default="grade4", choices=["grade4", "all_glioma"])
    ap.add_argument("--n-boot", type=int, default=500)
    ap.add_argument("--workers", type=int, default=64)
    ap.add_argument("--n-permutations", type=int, default=100)
    ap.add_argument("--nested-learners", default="ridge,gbm", help="learners searched in the nested selection")
    ap.add_argument("--perm-learners", default=None,
                    help="learners of the nested pipeline re-run under permutation (default: same as --nested-learners)")
    ap.add_argument("--skip-nested", action="store_true")
    ap.add_argument("--skip-grid", action="store_true")
    a = ap.parse_args(argv)
    out = RESULTS / "c2" / a.population
    out.mkdir(parents=True, exist_ok=True)

    if a.skip_grid:
        grid = pd.read_csv(out / "grid.csv")
    else:
        jobs = [(a.population, l, c, a.n_boot) for l in LEARNERS for c in ALL_COMBOS]
        with ProcessPoolExecutor(a.workers) as ex:
            outs = list(ex.map(run_grid_job, jobs))
        grid = pd.DataFrame([o[0] for o in outs]).sort_values("auc_ipcw", ascending=False)
        grid.to_csv(out / "grid.csv", index=False)
    print(grid[["learner", "combo", "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "auc_ipcw_averaged", "auc_ipcw_repeat_sd",
                "train_auc", "overfit_gap", "cal_slope", "oe_ratio"]].head(20).round(3).to_string(index=False))
    if a.skip_nested:
        return

    nested_l, perm_l = tuple(a.nested_learners.split(",")), tuple((a.perm_learners or a.nested_learners).split(","))
    runs = [nested(a.population, a.workers, nested_l, (None,), a.n_boot)]
    if perm_l != nested_l:  # observed statistic of the pipeline that is permuted
        runs.append(nested(a.population, a.workers, perm_l, (None,), a.n_boot))
    perm_choices, perm = nested(a.population, a.workers, perm_l, tuple(range(a.n_permutations)))
    choices = pd.concat([r[0] for r in runs] + [perm_choices], ignore_index=True)
    summ = pd.concat([r[1] for r in runs], ignore_index=True)
    obs = summ.set_index("learners").loc["+".join(perm_l), "auc_ipcw"]
    n_ge = int((perm.auc_ipcw >= obs).sum())
    summ["perm_learners"] = "+".join(perm_l)
    summ["perm_n"] = a.n_permutations
    summ["perm_mean_auc"] = perm.auc_ipcw.mean()
    summ["perm_p95_auc"] = perm.auc_ipcw.quantile(0.95)
    summ["perm_p_value"] = np.where(summ.learners == "+".join(perm_l), (1 + n_ge) / (1 + a.n_permutations), np.nan)
    choices.to_csv(out / "nested_choices.csv", index=False)
    summ.to_csv(out / "nested.csv", index=False)
    perm.to_csv(out / "permutation.csv", index=False)
    print(summ.round(3).to_string(index=False))
    obs_choices = choices[choices.permute_seed.isna()]
    print(obs_choices.groupby("learners")[["chosen_learner", "chosen"]].value_counts().to_string())
