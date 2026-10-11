"""Feature conflicts: do some non-imaging / imaging-measurement features work against each other?

C3 protocol throughout (verified 120-d labels, death censored; shared 5x5 patient-grouped folds; C3 preprocessing =
median imputation + missing indicators + scaling fitted in-fold; ridge = formulations.fit('verified'), boosting = C3 GBM;
headline = mean over repeats of the pooled-OOF IPCW AUC(120 d); paired patient-cluster bootstrap, 1000 draws).
Groups from features.tabular.groups(): clinical, timing, treatment (= baseline B), volumes, morphology, delta
(F = all six; legacy radiomics optional with --radiomics, group level only).

(a) Group level   add-one (B + g), leave-one-group-out from F (F - g; removal raising AUC = g hurts), leave-one-out
                  inside B, and additivity: interaction = Δ(A+B) - Δ(A) - Δ(B) for imaging pairs (on top of B) and for
                  timing x treatment (on top of clinical), with paired bootstrap CIs of every contrast.
(b) Feature level on the design matrix the ridge sees (F after in-fold preprocessing incl. missing indicators):
                  Spearman |r| > 0.8 clusters (connected components), VIF, univariate vs multivariable ridge coefficient
                  sign over the 25 fold fits (stability = share of fits with the majority sign), redundant pairs.
(c) Treatment x timing identities (rt_completed vs rt_date_unknown vs days_since_rt_end, end day = start + duration,
                  missing indicators that duplicate rt_started / rt_completed).
(d) Pruning by a rule stated before running (PRUNE_RULE below), applied inside every outer training fold
                  (nested, honest) and once on the full population (exploratory, optimistic).

    python -m prism.analyses.feature_conflicts [--workers 32] [--n-boot 1000] [--radiomics]
    -> $PRISM_OUTPUTS/results/analyses/feature_conflicts/{group_sets,contrasts,interactions,corr_pairs,corr_clusters,vif,
       coef_signs,treatment_timing,redundant_pairs,pruning,pruning_choices}.csv, oof_repeats.csv.gz, corr_clusters_<pop>.png
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from prism.config import RESULTS
from prism.data.mu import load_cohort
from prism.experiments.c3_radiomics import GBM
from prism.features.tabular import groups as feature_groups
from prism.models.folds import load_folds
from prism.models.formulations import fit as fit_ridge
from prism.models.metrics import counted_warnings, evaluate_repeated, fast_auc_brier, ipcw_context

H = 120
OUT = RESULTS / "analyses" / "feature_conflicts"
POPS = ("grade4", "all_glioma")
LEARNERS = ("ridge", "gbm")
BASE = ("clinical", "timing", "treatment")
IMAGING = ("volumes", "morphology", "delta")
ORDER = BASE + IMAGING + ("radiomics",)
PRE = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())])
R_CLUSTER, R_PRUNE = 0.8, 0.9
PRUNE_RULE = """Pre-stated pruning rule (fitted on training scans only):
 1. Start from F. Drop design columns (after median imputation + missing indicators) that are constant.
 2. Near-duplicates: walk the columns in priority order and keep a column only if its |Spearman r| with every column
    already kept is <= 0.9. Priority: original features before missing indicators; then group order clinical > timing >
    treatment > volumes > morphology > delta; then the column order of features/tabular.py (primary measure first,
    e.g. days_from_diagnosis before visit_index, log_et_cc before log_tumor_cc).
 3. Hurting groups: drop every imaging group (volumes, morphology, delta) whose removal from the step-2 set raises the
    inner 3-fold patient-grouped verified AUC (mean of folds). Baseline groups are never dropped.
 P_base applies step 1-2 to B only."""


# ---------------------------------------------------------------- data, sets, fitting
def load(population, radiomics=False):
    cohort = load_cohort(population)
    g = feature_groups(cohort, legacy_radiomics=radiomics)
    return cohort, load_folds(), {k: g[k] for k in ORDER if k in g}


def feature_sets(g):
    full = [k for k in ORDER if k in g and k != "radiomics"]
    s = {"B": list(BASE), "F": full}
    s["clinical_only"] = ["clinical"]
    for k in BASE:
        s[f"B-{k}"] = [b for b in BASE if b != k]
    for k in IMAGING:
        s[f"B+{k}"] = list(BASE) + [k]
    for i, a in enumerate(IMAGING):
        for b in IMAGING[i + 1:]:
            s[f"B+{a}+{b}"] = list(BASE) + [a, b]
    for k in full:
        s[f"F-{k}"] = [x for x in full if x != k]
    if "radiomics" in g:
        s["B+radiomics"], s["F+radiomics"] = list(BASE) + ["radiomics"], full + ["radiomics"]
    return s


def design(g, names):
    return pd.concat([g[k] for k in names], axis=1)


def fit_predict(X, cohort, tr, te, learner, seed=0, cols=None):
    """C3 fit: verified training scans, in-fold PRE; `cols` = callable(transformed train, names) -> kept column idx."""
    y = cohort[f"label_{H}"].to_numpy()
    tr = tr[~np.isnan(y[tr])]
    pre = clone(PRE).fit(X.iloc[tr])
    Xtr, Xte = pre.transform(X.iloc[tr]), pre.transform(X.iloc[te])
    names = np.array(pre.get_feature_names_out(), dtype=object)
    keep = np.arange(Xtr.shape[1]) if cols is None else cols(Xtr, names)
    Xtr, Xte, names = Xtr[:, keep], Xte[:, keep], names[keep]
    if learner == "ridge":
        model, _ = fit_ridge("verified", Xtr, cohort.iloc[tr].reset_index(drop=True), H, seed=seed)
        coef = model.coef_[0]
    else:
        model = clone(GBM).set_params(random_state=seed).fit(Xtr, y[tr].astype(int))
        coef = None
    return model.predict_proba(Xte)[:, 1], names, coef


def fold_ids(cohort, folds, r):
    return cohort.scan_id.map(folds[folds.repeat == r].set_index("scan_id").fold).to_numpy()


def cv(X, cohort, folds, learner, cols=None):
    nr = folds.repeat.nunique()
    oof, coefs = np.zeros((nr, len(cohort))), []
    for r in range(nr):
        f = fold_ids(cohort, folds, r)
        for k in np.unique(f):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            oof[r, te], names, coef = fit_predict(X, cohort, tr, te, learner, seed=r, cols=cols)
            if coef is not None:
                coefs.append(pd.Series(coef, index=names, name=(r, k)))
    return oof, coefs


@counted_warnings
def run_set(job):
    pop, name, members, learner, radiomics = job
    threadpool_limits(1)
    cohort, folds, g = load(pop, radiomics)
    oof, coefs = cv(design(g, members), cohort, folds, learner)
    return (pop, name, learner), oof, coefs


@counted_warnings
def run_univariate(job):
    pop, col = job
    threadpool_limits(1)
    cohort, folds, g = load(pop)
    X = design(g, list(feature_sets(g)["F"]))[[col]]
    oof, coefs = cv(X, cohort, folds, "ridge")
    return pop, col, oof, np.array([c.get(col, np.nan) for c in coefs])


# ---------------------------------------------------------------- pruning rule
def spearman_abs(X):
    with np.errstate(divide="ignore", invalid="ignore"):  # constant columns -> NaN -> 0 (dropped anyway)
        r = spearmanr(X).statistic if X.shape[1] > 1 else np.ones((1, 1))
    return np.abs(np.nan_to_num(np.atleast_2d(r)))


def priority(names, group_of):
    rank = {k: i for i, k in enumerate(ORDER)}
    def key(i):
        n = names[i]
        ind = n.startswith("missingindicator_")
        base = n.removeprefix("missingindicator_")
        return (ind, rank[group_of[base]], i)
    return sorted(range(len(names)), key=key)


def dedupe(Xtr, names, group_of, thr=R_PRUNE):
    """Steps 1-2 of PRUNE_RULE on a training design matrix; returns kept column indices (in original order)."""
    var = Xtr.std(0) > 1e-12
    r = spearman_abs(Xtr)
    keep = []
    for j in priority(names, group_of):
        if var[j] and all(r[j, k] <= thr for k in keep):
            keep.append(j)
    return np.sort(keep)


def dedupe_cols(group_of):
    return lambda Xtr, names: dedupe(Xtr, names, group_of)


def inner_auc(X, cohort, tr, learner, cols):
    y = cohort[f"label_{H}"].to_numpy()
    tr = tr[~np.isnan(y[tr])]
    aucs = []
    for a, b in GroupKFold(n_splits=3).split(tr, groups=cohort.patient_id.iloc[tr]):
        p, *_ = fit_predict(X, cohort, tr[a], tr[b], learner, cols=cols)
        aucs.append(roc_auc_score(y[tr[b]], p))
    return float(np.mean(aucs))


def prune_groups(g, cohort, tr, learner, group_of):
    """Step 3 on training rows: imaging groups whose removal raises inner AUC. Returns (kept groups, dropped, scores)."""
    full = feature_sets(g)["F"]
    cols = dedupe_cols(group_of)
    ref = inner_auc(design(g, full), cohort, tr, learner, cols)
    scores = {k: inner_auc(design(g, [x for x in full if x != k]), cohort, tr, learner, cols) - ref for k in IMAGING}
    dropped = [k for k, v in scores.items() if v > 0]
    return [k for k in full if k not in dropped], dropped, scores


@counted_warnings
def run_nested_prune(job):
    pop, learner, r, k = job
    threadpool_limits(1)
    cohort, folds, g = load(pop)
    group_of = {c: n for n, d in g.items() for c in d.columns}
    f = fold_ids(cohort, folds, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    kept, dropped, scores = prune_groups(g, cohort, tr, learner, group_of)
    p_full, names, _ = fit_predict(design(g, kept), cohort, tr, te, learner, seed=r, cols=dedupe_cols(group_of))
    p_base, names_b, _ = fit_predict(design(g, list(BASE)), cohort, tr, te, learner, seed=r, cols=dedupe_cols(group_of))
    return dict(population=pop, learner=learner, repeat=r, fold=k, te=te, p_full=p_full, p_base=p_base,
                dropped_groups="|".join(dropped), n_cols_full=len(names), n_cols_base=len(names_b),
                cols_full="|".join(names), cols_base="|".join(names_b), **{f"inner_d_{a}": v for a, v in scores.items()})


@counted_warnings
def run_global_prune(job):
    """Exploratory: rule applied once to all scans (dedupe + LOGO-hurting groups from the outer-CV table)."""
    pop, learner, dropped = job
    threadpool_limits(1)
    cohort, folds, g = load(pop)
    group_of = {c: n for n, d in g.items() for c in d.columns}
    full = [k for k in feature_sets(g)["F"] if k not in dropped]
    y = cohort[f"label_{H}"].to_numpy()
    X = design(g, full)
    pre = clone(PRE).fit(X.iloc[np.where(~np.isnan(y))[0]])
    Z = pre.transform(X.iloc[np.where(~np.isnan(y))[0]])
    names = np.array(pre.get_feature_names_out(), dtype=object)
    keep = set(names[dedupe(Z, names, group_of)])
    sel = lambda Xtr, nm: np.array([i for i, n in enumerate(nm) if n in keep], int)
    oof, _ = cv(X, cohort, folds, learner, cols=sel)
    return (pop, learner), oof, sorted(keep)


# ---------------------------------------------------------------- bootstrap of arbitrary contrasts
def boot_matrix(d, oofs, n_boot=1000, seed=0):
    """Mean-over-repeats IPCW AUC per model on the original data and on the same patient-cluster draws as
    metrics.repeated_bootstrap (same seed -> same resamples). Returns (names, point (m,), draws (b x m))."""
    names = list(oofs)
    mats = [np.atleast_2d(oofs[k]) for k in names]
    sizes = np.cumsum([0] + [len(m) for m in mats])
    P = np.vstack(mats)
    summ = lambda ctx, idx: (lambda a: np.array([a[sizes[i]:sizes[i + 1]].mean() for i in range(len(names))]))(
        fast_auc_brier(ctx, P if idx is None else P[:, idx])[0])
    point = summ(ipcw_context(d, H), None)
    rng = np.random.default_rng(seed)
    pid = d.patient_id.to_numpy()
    grp = {p: np.where(pid == p)[0] for p in np.unique(pid)}
    pats = np.array(list(grp))
    draws = []
    for _ in range(n_boot):
        idx = np.concatenate([grp[p] for p in rng.choice(pats, len(pats))])
        db = d.iloc[idx].reset_index(drop=True)
        if db[f"label_{H}"].nunique(dropna=True) < 2:
            continue
        ctx = ipcw_context(db, H)
        if ctx is not None:
            draws.append(summ(ctx, idx))
    return names, point, np.array(draws)


def contrast(names, point, draws, weights: dict, label: str):
    w = np.array([weights.get(n, 0.0) for n in names])
    v = draws @ w
    lo, hi = np.nanpercentile(v, [2.5, 97.5])
    return {"contrast": label, "estimate": float(point @ w), "lo": lo, "hi": hi, "p_le0": float(np.mean(v <= 0))}


# ---------------------------------------------------------------- descriptive feature-level analyses
def design_matrix(cohort, g, members):
    """Full-population design (verified + censored scans) after PRE imputation/indicators, before scaling."""
    X = design(g, members)
    imp = clone(PRE.named_steps["imp"]).fit(X)
    return pd.DataFrame(imp.transform(X), columns=imp.get_feature_names_out(), index=X.index)


def corr_tables(D, group_of, pop):
    Dv = D.loc[:, D.std() > 1e-12]
    r = pd.DataFrame(spearmanr(Dv).statistic, index=Dv.columns, columns=Dv.columns)
    gname = lambda c: group_of[c.removeprefix("missingindicator_")]
    iu = np.triu_indices(len(r), 1)
    pairs = pd.DataFrame({"feature_a": r.index[iu[0]], "feature_b": r.columns[iu[1]], "spearman_r": r.values[iu]})
    pairs["pearson_r"] = [np.corrcoef(Dv[a], Dv[b])[0, 1] for a, b in zip(pairs.feature_a, pairs.feature_b)]
    pairs = pairs[pairs.spearman_r.abs() > R_CLUSTER].assign(
        group_a=lambda t: t.feature_a.map(gname), group_b=lambda t: t.feature_b.map(gname), population=pop)
    pairs = pairs.reindex(pairs.spearman_r.abs().sort_values(ascending=False).index)
    # connected components of the |r| > 0.8 graph
    parent = {c: c for c in r.index}
    find = lambda c: c if parent[c] == c else find(parent[c])
    for a, b in zip(pairs.feature_a, pairs.feature_b):
        parent[find(a)] = find(b)
    comp = pd.Series({c: find(c) for c in r.index})
    sizes = comp.value_counts()
    comp = comp[comp.map(sizes) > 1]
    cid = {root: i + 1 for i, root in enumerate(sizes[sizes > 1].index)}
    clusters = pd.DataFrame({"feature": comp.index, "cluster": comp.map(cid).to_numpy(),
                             "group": [gname(c) for c in comp.index], "population": pop}).sort_values(["cluster", "feature"])
    vif = pd.concat([vif_table(Dv, gname).assign(design="F")] +
                    [vif_table(Dv[[c for c in Dv if gname(c) in BASE]], gname).assign(design="B")])
    return r, pairs, clusters, vif.assign(population=pop)


def vif_table(Dv, gname):
    """VIF = 1 / (1 - R^2) of each column regressed (OLS, least squares) on all others; inf for exact dependencies."""
    Z = ((Dv - Dv.mean()) / Dv.std()).to_numpy()
    rows = []
    for j, c in enumerate(Dv.columns):
        X = np.delete(Z, j, 1)
        res = Z[:, j] - X @ np.linalg.lstsq(X, Z[:, j], rcond=None)[0]
        r2 = 1 - (res ** 2).sum() / (Z[:, j] ** 2).sum()
        rows.append({"feature": c, "group": gname(c), "r2_on_others": r2, "vif": np.inf if r2 > 1 - 1e-9 else 1 / (1 - r2)})
    return pd.DataFrame(rows).sort_values("r2_on_others", ascending=False)


REDUNDANT = [  # (target, predictors) encoding the same information differently
    ("days_from_diagnosis", ["visit_index"]), ("days_from_diagnosis", ["n_prior_scans"]),
    ("days_from_diagnosis", ["rt_start_day", "days_since_rt_end", "rt_date_unknown"]),
    ("days_from_diagnosis", ["surgery_day"]), ("visit_index", ["n_prior_scans"]), ("visit_index", ["has_prior"]),
    ("days_since_rt_end", ["early_post_rt", "rt_date_unknown"]), ("rt_completed", ["rt_date_unknown"]),
    ("rt_completed", ["rt_started"]), ("chemo_started", ["rt_started"]),
    ("rt_fractions", ["rt_dose_gy", "rt_hypofractionated"]),
    ("log_tumor_cc", ["log_et_cc", "log_netc_cc"]), ("log_tumor_cc", ["log_et_cc"]),
    ("log_lesion_cc", ["log_tumor_cc", "log_snfh_cc"]), ("log_lesion_cc", ["log_snfh_cc"]),
    ("log_et_max_axial", ["log_et_cc"]), ("et_fraction_of_tumor", ["log_et_cc", "log_netc_cc"]),
    ("logratio_tumor_cc", ["logratio_et_cc"]), ("rate_tumor_cc_per30d", ["rate_et_cc_per30d"]),
    ("logratio_nadir_et_cc", ["logratio_et_cc"]),
]


def redundancy(D, cohort, pop):
    """R^2 (OLS on the imputed design) and Spearman r for pre-listed redundant encodings, plus exact identities."""
    rows = []
    for t, ps in REDUNDANT:
        if t not in D or any(p not in D for p in ps):
            continue
        X = np.column_stack([np.ones(len(D)), D[ps].to_numpy(float)])
        yv = D[t].to_numpy(float)
        res = yv - X @ np.linalg.lstsq(X, yv, rcond=None)[0]
        rows.append({"population": pop, "target": t, "predictors": " + ".join(ps),
                     "r2_ols": 1 - (res ** 2).sum() / ((yv - yv.mean()) ** 2).sum(),
                     "spearman_r": spearmanr(D[t], D[ps[0]]).statistic if len(ps) == 1 else np.nan})
    et, netc = np.expm1(D.log_et_cc), np.expm1(D.log_netc_cc)
    rows.append({"population": pop, "target": "log_tumor_cc", "predictors": "log1p(expm1(log_et_cc) + expm1(log_netc_cc))",
                 "r2_ols": np.nan, "spearman_r": np.nan,
                 "exact_share": float(np.mean(np.abs(np.log1p(et + netc) - D.log_tumor_cc) < 1e-6))})
    return pd.DataFrame(rows)


def treatment_timing(cohort, g, pop):
    t, tr = g["timing"], g["treatment"]
    mri = cohort.days_from_diagnosis_to_mri
    rt_end_from_timing = mri - t.days_since_rt_end
    rt_end_from_treat = tr.rt_start_day + tr.rt_duration_days
    both = rt_end_from_timing.notna() & rt_end_from_treat.notna()
    checks = {
        "rt_date_unknown == 1 - rt_completed": (t.rt_date_unknown == 1 - tr.rt_completed).mean(),
        "days_since_rt_end missing <=> rt_completed == 0": (t.days_since_rt_end.isna() == (tr.rt_completed == 0)).mean(),
        "rt_dose_gy missing <=> rt_started == 0": (tr.rt_dose_gy.isna() == (tr.rt_started == 0)).mean(),
        "rt_duration_days missing <=> rt_completed == 0": (tr.rt_duration_days.isna() == (tr.rt_completed == 0)).mean(),
        "rt end day: (days_from_diagnosis - days_since_rt_end) == rt_start_day + rt_duration_days (|diff| <= 1 d)":
            ((rt_end_from_timing - rt_end_from_treat).abs()[both] <= 1).mean(),
        "early_post_rt == 1 implies rt_completed == 1": ((t.early_post_rt != 1) | (tr.rt_completed == 1)).mean(),
        "early_post_rt missing <=> rt_completed == 0": (t.early_post_rt.isna() == (tr.rt_completed == 0)).mean(),
        "rt_completed == 1 implies rt_started == 1": ((tr.rt_completed != 1) | (tr.rt_started == 1)).mean(),
        "chemo_started == rt_started": (tr.chemo_started == tr.rt_started).mean(),
        "visit_index == n_prior_scans + 1": (t.visit_index == g["delta"].n_prior_scans + 1).mean()
        if "delta" in g else np.nan,
        "has_prior == (visit_index > 1)": (g["delta"].has_prior == (t.visit_index > 1)).mean() if "delta" in g else np.nan,
    }
    rows = [{"population": pop, "check": k, "share_true": float(v), "n": len(cohort)} for k, v in checks.items()]
    rows.append({"population": pop, "check": "n scans with both rt end-day encodings", "share_true": np.nan,
                 "n": int(both.sum())})
    for a, b in (("rt_completed", "early_post_rt"), ("rt_started", "rt_completed"), ("rt_completed", "chemo_started")):
        ct = pd.crosstab(pd.concat([t, tr], axis=1)[a].fillna(-1), pd.concat([t, tr], axis=1)[b].fillna(-1))
        rows.append({"population": pop, "check": f"crosstab {a} x {b} (-1 = missing)", "share_true": np.nan,
                     "n": len(cohort), "detail": ct.to_dict()})
    return pd.DataFrame(rows)


def heatmap(r, clusters, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    cols = clusters.sort_values(["cluster", "group", "feature"]).feature.tolist()
    m = r.loc[cols, cols].to_numpy()
    cmap = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f0efec", "#e34948"])
    n = len(cols)
    fig, ax = plt.subplots(figsize=(0.28 * n + 3.5, 0.28 * n + 2.5))
    im = ax.imshow(m, cmap=cmap, vmin=-1, vmax=1)
    short = [c.replace("missingindicator_", "miss:") for c in cols]
    ax.set_xticks(range(n), short, rotation=90, fontsize=7)
    ax.set_yticks(range(n), short, fontsize=7)
    edges = np.cumsum(clusters.sort_values(["cluster", "group", "feature"]).groupby("cluster").size().to_numpy())
    start = 0
    for e in edges:
        ax.add_patch(plt.Rectangle((start - 0.5, start - 0.5), e - start, e - start, fill=False, lw=1.2, ec="#222"))
        start = e
    ax.set_title(title, fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.6, label="Spearman r")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def sign_table(uni, multi_b, multi_f, uni_auc, D, y, pop):
    """Per original feature: univariate vs multivariable (B and F) ridge coefficient signs over the fold fits."""
    rows = []
    stab = lambda v: float(max(np.mean(v > 0), np.mean(v < 0))) if len(v) else np.nan
    for col, u in uni.items():
        u = u[np.isfinite(u)]
        known = ~np.isnan(y)
        rho = spearmanr(D[col][known], y[known]).statistic if D[col][known].std() > 0 else np.nan
        row = {"population": pop, "feature": col, "spearman_vs_label": rho, "univariate_cv_auc": uni_auc[col],
               "uni_coef_mean": u.mean() if len(u) else np.nan, "uni_sign_stability": stab(u)}
        for tag, M in (("B", multi_b), ("F", multi_f)):
            if col not in M:
                continue
            v = M[col].dropna().to_numpy()
            row.update({f"{tag}_coef_mean": v.mean(), f"{tag}_coef_sd": v.std(), f"{tag}_share_pos": np.mean(v > 0),
                        f"{tag}_sign_stability": stab(v)})
            row[f"{tag}_flip"] = bool(np.sign(v.mean()) != np.sign(row["uni_coef_mean"]))
            row[f"{tag}_stable_flip"] = bool(row[f"{tag}_flip"] and stab(v) >= 0.8 and row["uni_sign_stability"] >= 0.8)
        rows.append(row)
    for col in sorted(set(multi_b.columns) | set(multi_f.columns)):  # missing indicators (no univariate fit)
        if col in uni:
            continue
        row = {"population": pop, "feature": col}
        for tag, M in (("B", multi_b), ("F", multi_f)):
            if col in M:
                v = M[col].dropna().to_numpy()
                row.update({f"{tag}_coef_mean": v.mean(), f"{tag}_coef_sd": v.std(), f"{tag}_share_pos": np.mean(v > 0),
                            f"{tag}_sign_stability": stab(v)})
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m prism.analyses.feature_conflicts", description=__doc__)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--radiomics", action="store_true", help="also B+radiomics and F+radiomics (legacy, group level)")
    ap.add_argument("--populations", nargs="+", default=list(POPS))
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    print(PRUNE_RULE)

    jobs, uni_jobs, ctx = [], [], {}
    for pop in a.populations:
        cohort, folds, g = load(pop, a.radiomics)
        ctx[pop] = (cohort, folds, g)
        for name, members in feature_sets(g).items():
            jobs += [(pop, name, members, l, a.radiomics) for l in LEARNERS]
        uni_jobs += [(pop, c) for c in design(g, feature_sets(g)["F"]).columns]
    with ProcessPoolExecutor(a.workers) as ex:
        res = {k: (o, c) for k, o, c in ex.map(run_set, jobs)}
        uni = list(ex.map(run_univariate, uni_jobs))
        nested = list(ex.map(run_nested_prune, [(p, l, r, k) for p in a.populations for l in LEARNERS
                                                for r in range(5) for k in range(5)]))

    # (a) group sets + contrasts
    set_rows, con_rows, inter_rows, oof_cols = [], [], [], {}
    glob_jobs = []
    for pop in a.populations:
        cohort, folds, g = ctx[pop]
        for learner in LEARNERS:
            oofs = {n: o for (p, n, l), (o, _) in res.items() if p == pop and l == learner}
            # nested pruning OOF
            for tag in ("full", "base"):
                o = np.zeros((5, len(cohort)))
                for d in nested:
                    if d["population"] == pop and d["learner"] == learner:
                        o[d["repeat"], d["te"]] = d[f"p_{tag}"]
                oofs[f"P_{tag}_nested"] = o
            ev = evaluate_repeated(cohort, oofs, H, reference="B", n_boot=a.n_boot)
            ev = ev.assign(population=pop, learner=learner).rename_axis("set").reset_index()
            set_rows.append(ev)
            names, point, draws = boot_matrix(cohort, oofs, a.n_boot)
            C = lambda w, lab, kind: {"population": pop, "learner": learner, "kind": kind, **contrast(names, point, draws, w, lab)}
            for n in names:
                if n.startswith("B+") and n.count("+") == 1:
                    con_rows.append(C({n: 1, "B": -1}, f"{n} - B", "add_one"))
                if n.startswith("F-"):
                    con_rows.append(C({n: 1, "F": -1}, f"{n} - F (>0: group hurts)", "logo_from_F"))
                if n.startswith("B-"):
                    con_rows.append(C({n: 1, "B": -1}, f"{n} - B (>0: group hurts)", "loo_from_B"))
            con_rows.append(C({"F": 1, "B": -1}, "F - B", "full_vs_base"))
            for t in ("full", "base"):
                con_rows.append(C({f"P_{t}_nested": 1, "B": -1}, f"P_{t}_nested - B", "pruned"))
                con_rows.append(C({f"P_{t}_nested": 1, "F": -1}, f"P_{t}_nested - F", "pruned"))
            for i, x in enumerate(IMAGING):
                for z in IMAGING[i + 1:]:
                    w = {f"B+{x}+{z}": 1, f"B+{x}": -1, f"B+{z}": -1, "B": 1}
                    inter_rows.append({"population": pop, "learner": learner, "pair": f"{x} x {z} (on B)",
                                       "d_A": point[names.index(f"B+{x}")] - point[names.index("B")],
                                       "d_B": point[names.index(f"B+{z}")] - point[names.index("B")],
                                       "d_AB": point[names.index(f"B+{x}+{z}")] - point[names.index("B")],
                                       **contrast(names, point, draws, w, "interaction")})
            w = {"B": 1, "B-timing": -1, "B-treatment": -1, "clinical_only": 1}
            inter_rows.append({"population": pop, "learner": learner, "pair": "timing x treatment (on clinical)",
                               "d_A": point[names.index("B-treatment")] - point[names.index("clinical_only")],
                               "d_B": point[names.index("B-timing")] - point[names.index("clinical_only")],
                               "d_AB": point[names.index("B")] - point[names.index("clinical_only")],
                               **contrast(names, point, draws, w, "interaction")})
            for n, o in oofs.items():
                for r in range(len(o)):
                    oof_cols[f"{pop}|{learner}|{n}#r{r}"] = pd.Series(o[r], index=cohort.scan_id.to_numpy())
            hurt = [k for k in IMAGING if point[names.index(f"F-{k}")] > point[names.index("F")]]
            glob_jobs.append((pop, learner, hurt))
    with ProcessPoolExecutor(a.workers) as ex:
        glob = list(ex.map(run_global_prune, glob_jobs))
    prune_rows = []
    for (pop, learner), o, keep in glob:
        cohort = ctx[pop][0]
        oofs = {"B": res[(pop, "B", learner)][0], "F": res[(pop, "F", learner)][0], "P_full_global": o}
        ev = evaluate_repeated(cohort, oofs, H, reference="F", n_boot=a.n_boot).loc[["P_full_global"]]
        drop = [j for p_, l_, j in glob_jobs if p_ == pop and l_ == learner][0]
        prune_rows.append(ev.assign(population=pop, learner=learner, dropped_groups="|".join(drop), n_cols=len(keep),
                                    cols="|".join(keep)).rename_axis("set").reset_index())
        names, point, draws = boot_matrix(cohort, oofs, a.n_boot)
        con_rows.append({"population": pop, "learner": learner, "kind": "pruned_exploratory",
                         **contrast(names, point, draws, {"P_full_global": 1, "B": -1}, "P_full_global - B")})
    sets = pd.concat(set_rows)
    sets.to_csv(OUT / "group_sets.csv", index=False)
    pd.DataFrame(con_rows).to_csv(OUT / "contrasts.csv", index=False)
    pd.DataFrame(inter_rows).to_csv(OUT / "interactions.csv", index=False)
    pd.concat(prune_rows).to_csv(OUT / "pruning.csv", index=False)
    pd.DataFrame([{k: v for k, v in d.items() if k not in ("te", "p_full", "p_base")} for d in nested]
                 ).to_csv(OUT / "pruning_choices.csv", index=False)
    pd.DataFrame(oof_cols).rename_axis("scan_id").reset_index().to_csv(OUT / "oof_repeats.csv.gz", index=False)

    # (b), (c) feature level
    pairs_all, clus_all, vif_all, sign_all, tt_all, red_all = [], [], [], [], [], []
    for pop in a.populations:
        cohort, folds, g = ctx[pop]
        group_of = {c: n for n, d in g.items() for c in d.columns}
        D = design_matrix(cohort, g, feature_sets(g)["F"])
        r, pairs, clusters, vif = corr_tables(D, group_of, pop)
        pairs_all.append(pairs), clus_all.append(clusters), vif_all.append(vif)
        heatmap(r, clusters, OUT / f"corr_clusters_{pop}.png",
                f"{pop}: features in |Spearman r| > {R_CLUSTER} clusters (design incl. missing indicators)")
        y = cohort[f"label_{H}"].to_numpy(float)
        cx = ipcw_context(cohort, H)
        u = {c: v for p, c, _, v in uni if p == pop}
        uauc = {c: float(np.mean(fast_auc_brier(cx, o)[0])) for p, c, o, _ in uni if p == pop}
        mb = pd.DataFrame(res[(pop, "B", "ridge")][1])
        mf = pd.DataFrame(res[(pop, "F", "ridge")][1])
        sign_all.append(sign_table(u, mb, mf, uauc, D, y, pop))
        tt_all.append(treatment_timing(cohort, g, pop))
        red_all.append(redundancy(D, cohort, pop))
    pd.concat(pairs_all).to_csv(OUT / "corr_pairs.csv", index=False)
    pd.concat(clus_all).to_csv(OUT / "corr_clusters.csv", index=False)
    pd.concat(vif_all).to_csv(OUT / "vif.csv", index=False)
    pd.concat(sign_all).to_csv(OUT / "coef_signs.csv", index=False)
    pd.concat(tt_all).to_csv(OUT / "treatment_timing.csv", index=False)
    pd.concat(red_all).to_csv(OUT / "redundant_pairs.csv", index=False)

    cols = ["population", "learner", "set", "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "d_auc_ipcw_vs_B", "d_auc_ipcw_lo",
            "d_auc_ipcw_hi"]
    print(sets[cols].round(3).to_string(index=False))
    print(pd.DataFrame(con_rows).round(3).to_string(index=False))
    print(pd.DataFrame(inter_rows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
