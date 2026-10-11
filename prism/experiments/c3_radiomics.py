"""C3: can (corrected) radiomics improve on a clinical + timing + treatment baseline?

Radiomics variants  legacy (union mask, 2 grey levels) | v2_lesion (corrected, whole lesion, T1c+FLAIR)
                    v2_compartments (corrected, ET/NETC/SNFH/core/lesion/rim + shape, T1c+FLAIR) | v2_all4 (all 4 sequences)
Stability           none | icc (keep features with ICC >= 0.75 between full and 1-voxel-eroded ROI, training scans only)
Selection           top10 | top30 (univariate F) | l1 (sparse logistic) | pca10 | decor20 (drop |r|>0.9, then top20)
Integration         concat (baseline + selected radiomics, one ridge) | stack (baseline + in-fold radiomics score)

Every step is fitted on the training fold; the radiomics score for stacking comes from inner patient-grouped
OOF predictions. Nested selection over all radiomics configurations gives the honest "best radiomics" estimate.
Missing compartments (no ET / NETC / rim ROI) are median-imputed with one presence flag per missingness pattern.
Headline AUC = mean over repeats of each repeat's pooled-OOF IPCW AUC; ΔAUC vs the ridge baseline is the point
estimate with a paired patient-cluster bootstrap CI (`*_averaged` = AUC of the repeat-averaged prediction).

    python -m prism c3 --population grade4
    -> outputs/results/c3/<population>/{results.csv, oof.csv, oof_repeats.csv.gz, nested_choices.csv}
"""

from __future__ import annotations

import argparse
import itertools
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from prism.config import RADIOMICS, RADIOMICS_ERODED, RESULTS
from prism.data.mu import load_cohort
from prism.features.tabular import groups as feature_groups
from prism.models.folds import load_folds
from prism.models.formulations import fit as fit_ridge
from prism.models.metrics import counted_warnings, evaluate_repeated

H = 120
VARIANTS = ("legacy", "v2_lesion", "v2_compartments", "v2_all4")
STABILITY = ("none", "icc")
SELECTIONS = ("top10", "top30", "l1", "pca10", "decor20")
INTEGRATIONS = ("concat", "stack")
ICC_MIN = 0.75
GBM = HistGradientBoostingClassifier(max_depth=2, learning_rate=0.03, max_iter=150, min_samples_leaf=20,
                                     l2_regularization=2.0, max_features=0.5, random_state=0)


# ---------------------------------------------------------------- data
def load(population):
    cohort = load_cohort(population)
    folds = load_folds()
    g = feature_groups(cohort)
    base = pd.concat([g["clinical"], g["timing"], g["treatment"]], axis=1)
    v2 = pd.read_csv(RADIOMICS).set_index("scan_id").reindex(cohort.scan_id)
    er = pd.read_csv(RADIOMICS_ERODED).set_index("scan_id").reindex(cohort.scan_id)
    v2.index = er.index = cohort.index
    pair = lambda s: s.startswith(("t1c_", "flair_"))
    shape_cols = [c for c in v2.columns if not c.startswith(("t1c_", "flair_", "t1_", "t2_"))]
    rad = {
        "legacy": g["radiomics"],
        "v2_lesion": v2[[c for c in v2.columns if pair(c) and c.split("_")[1] == "lesion"]],
        "v2_compartments": v2[[c for c in v2.columns if pair(c)] + shape_cols],
        "v2_all4": v2,
    }
    return cohort, folds, base, rad, er


def icc_consistency(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """ICC(3,1) per column between two measurements of the same scans."""
    ok = ~(np.isnan(a) | np.isnan(b))
    out = np.full(a.shape[1], np.nan)
    for j in range(a.shape[1]):
        x, y = a[ok[:, j], j], b[ok[:, j], j]
        if len(x) < 10:
            continue
        m = np.stack([x, y], 1)
        n, k = m.shape
        ms_r = k * ((m.mean(1) - m.mean()) ** 2).sum() / (n - 1)
        ms_e = ((m - m.mean(1, keepdims=True) - m.mean(0, keepdims=True) + m.mean()) ** 2).sum() / ((n - 1) * (k - 1))
        out[j] = (ms_r - ms_e) / (ms_r + (k - 1) * ms_e) if ms_r + ms_e > 0 else np.nan
    return out


class Decorrelate(BaseEstimator, TransformerMixin):
    def __init__(self, threshold=0.9):
        self.threshold = threshold

    def fit(self, X, y=None):
        r = np.abs(np.corrcoef(X, rowvar=False))
        np.fill_diagonal(r, 0)
        keep = []
        for j in np.argsort(-np.nan_to_num(np.var(X, axis=0))):
            if all(r[j, k] <= self.threshold for k in keep):
                keep.append(j)
        self.keep_ = np.sort(keep)
        return self

    def transform(self, X):
        return X[:, self.keep_]


class QuantileClip(BaseEstimator, TransformerMixin):
    """Clip each feature to its training [q, 1-q] order statistics (NaN kept). Guards against extreme values such as
    the PyRadiomics 1e6 sentinel (NGTDM Coarseness of a flat ROI) dominating scaling, PCA and the stacked score."""

    def __init__(self, q=0.01):
        self.q = q

    def fit(self, X, y=None):
        X = np.asarray(X, float)
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            self.lo_ = np.nanquantile(X, self.q, axis=0, method="higher")
            self.hi_ = np.nanquantile(X, 1 - self.q, axis=0, method="lower")
        return self

    def transform(self, X):
        X = np.asarray(X, float)
        return np.where(np.isnan(X), X, np.clip(X, np.nan_to_num(self.lo_, nan=-np.inf), np.nan_to_num(self.hi_, nan=np.inf)))


class ImputeWithFlags(BaseEstimator, TransformerMixin):
    """Median imputation + one 0/1 missingness flag per distinct missingness pattern in training (e.g. 'no ET ROI'
    flags all ET features at once instead of one duplicate indicator per feature)."""

    def fit(self, X, y=None):
        X = np.asarray(X, float)
        miss = np.isnan(X)
        with np.errstate(all="ignore"):
            self.median_ = np.nan_to_num(np.nanmedian(np.where(miss.all(0), 0.0, X), axis=0))
        first = {}
        for j in np.where(miss.any(0) & ~miss.all(0))[0]:
            first.setdefault(miss[:, j].tobytes(), j)
        self.flag_cols_ = np.array(sorted(first.values()), int)
        return self

    def transform(self, X):
        X = np.asarray(X, float)
        miss = np.isnan(X)
        return np.hstack([np.where(miss, self.median_, X), miss[:, self.flag_cols_].astype(float)])


class L1Select(BaseEstimator, TransformerMixin):
    """Features with a nonzero L1-logistic coefficient (largest |coef| first, at most max_features). Unlike
    SelectFromModel(threshold=-inf) it never pads with zero-coefficient features; if nothing survives, the block
    is a single zero column (radiomics then contributes nothing)."""

    def __init__(self, C=0.1, max_features=30):
        self.C, self.max_features = C, max_features

    def fit(self, X, y):
        coef = np.abs(LogisticRegression(penalty="l1", C=self.C, solver="liblinear", random_state=0).fit(X, y).coef_[0])
        nz = np.where(coef > 1e-10)[0]
        self.keep_ = np.sort(nz[np.argsort(-coef[nz])][:self.max_features])
        return self

    def transform(self, X):
        return X[:, self.keep_] if len(self.keep_) else np.zeros((len(X), 1))


def f_classif_quiet(X, y):
    """f_classif without numpy's divide warning for a zero within-class variance (NaN score; SelectKBest ranks it
    last)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return f_classif(X, y)


def selector(name):
    steps = [("clip", QuantileClip()), ("imp", ImputeWithFlags()), ("var", VarianceThreshold(1e-8)), ("sc", StandardScaler())]
    if name.startswith("top"):
        steps.append(("sel", SelectKBest(f_classif_quiet, k=int(name[3:]))))
    elif name == "l1":
        steps.append(("sel", L1Select(C=0.1, max_features=30)))
    elif name == "pca10":
        steps.append(("sel", PCA(n_components=10, random_state=0)))
    elif name == "decor20":
        steps += [("dec", Decorrelate(0.9)), ("sel", SelectKBest(f_classif_quiet, k=20))]
    return Pipeline(steps)


BASE_PRE = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())])


# ---------------------------------------------------------------- one configuration on one split
def _ridge(X, cohort, rows, seed):
    model, _ = fit_ridge("verified", X, cohort.iloc[rows].reset_index(drop=True), H, seed=seed)
    return model


def fit_predict(cfg, cohort, base, rad, er, tr, te, seed=0):
    """cfg = (variant|None, stability, selection, integration, learner). Returns test risk."""
    variant, stab, sel, integ, learner = cfg
    y = cohort[f"label_{H}"].to_numpy()
    tr = tr[~np.isnan(y[tr])]
    bp = clone(BASE_PRE).fit(base.iloc[tr])
    Btr, Bte = bp.transform(base.iloc[tr]), bp.transform(base.iloc[te])
    if variant is None:
        Xtr, Xte = Btr, Bte
    else:
        R = rad[variant]
        cols = list(R.columns)
        if stab == "icc":
            shared = [c for c in cols if c in er.columns]
            icc = icc_consistency(R.loc[R.index[tr], shared].to_numpy(float), er.loc[er.index[tr], shared].to_numpy(float))
            unstable = {c for c, v in zip(shared, icc) if not (v >= ICC_MIN)}
            cols = [c for c in cols if c not in unstable]
        Rtr, Rte = R.iloc[tr][cols].to_numpy(float), R.iloc[te][cols].to_numpy(float)
        if integ == "concat":
            sp = clone(selector(sel)).fit(Rtr, y[tr].astype(int))
            Xtr, Xte = np.hstack([Btr, sp.transform(Rtr)]), np.hstack([Bte, sp.transform(Rte)])
        else:  # stack: radiomics-only ridge score, inner OOF on training patients
            score_tr = np.zeros(len(tr))
            for a, b in GroupKFold(n_splits=4).split(tr, groups=cohort.patient_id.iloc[tr]):
                sp = clone(selector(sel)).fit(Rtr[a], y[tr][a].astype(int))
                m = LogisticRegression(C=0.1, max_iter=5000).fit(sp.transform(Rtr[a]), y[tr][a].astype(int))
                score_tr[b] = m.decision_function(sp.transform(Rtr[b]))
            sp = clone(selector(sel)).fit(Rtr, y[tr].astype(int))
            m = LogisticRegression(C=0.1, max_iter=5000).fit(sp.transform(Rtr), y[tr].astype(int))
            score_te = m.decision_function(sp.transform(Rte))
            Xtr, Xte = np.hstack([Btr, score_tr[:, None]]), np.hstack([Bte, score_te[:, None]])
    if learner == "ridge":
        model = _ridge(Xtr, cohort, tr, seed)
    else:
        model = clone(GBM).set_params(random_state=seed).fit(Xtr, y[tr].astype(int))
    return model.predict_proba(Xte)[:, 1]


def _fold_ids(cohort, folds, r):
    return cohort.scan_id.map(folds[folds.repeat == r].set_index("scan_id").fold).to_numpy()


RAD_CONFIGS = [(v, s, sel, i, "ridge") for v, s, sel, i in itertools.product(VARIANTS, STABILITY, SELECTIONS, INTEGRATIONS)
               if not (v == "legacy" and s == "icc")]
BASELINES = [(None, "none", "none", "none", "ridge"), (None, "none", "none", "none", "gbm")]


@counted_warnings
def run_config(job):
    population, cfg = job
    threadpool_limits(1)
    cohort, folds, base, rad, er = load(population)
    oof = np.zeros((folds.repeat.nunique(), len(cohort)))
    for r in range(oof.shape[0]):
        f = _fold_ids(cohort, folds, r)
        for k in np.unique(f):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            oof[r, te] = fit_predict(cfg, cohort, base, rad, er, tr, te, seed=r)
    return cfg, oof


def inner_auc(cfg, cohort, base, rad, er, tr):
    y = cohort[f"label_{H}"].to_numpy()
    aucs = []
    for a, b in GroupKFold(n_splits=3).split(tr, groups=cohort.patient_id.iloc[tr]):
        p = fit_predict(cfg, cohort, base, rad, er, tr[a], tr[b])
        k = ~np.isnan(y[tr[b]])
        aucs.append(roc_auc_score(y[tr[b]][k], p[k]))
    return float(np.mean(aucs))


@counted_warnings
def run_nested(job):
    population, r, k, candidates = job
    threadpool_limits(1)
    cohort, folds, base, rad, er = load(population)
    f = _fold_ids(cohort, folds, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    scores = {c: inner_auc(c, cohort, base, rad, er, tr) for c in candidates}
    best = max(scores, key=scores.get)
    return r, k, te, fit_predict(best, cohort, base, rad, er, tr, te, seed=r), "|".join(map(str, best)), scores[best]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism c3", description=__doc__)
    ap.add_argument("--population", default="grade4", choices=["grade4", "all_glioma"])
    ap.add_argument("--workers", type=int, default=96)
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    out = RESULTS / "c3" / a.population
    out.mkdir(parents=True, exist_ok=True)
    cohort, folds, *_ = load(a.population)

    configs = BASELINES + RAD_CONFIGS
    with ProcessPoolExecutor(a.workers) as ex:
        res = dict(ex.map(run_config, [(a.population, c) for c in configs]))

    # Nested choice among radiomics configs (ridge) -> honest "best radiomics" estimate.
    jobs = [(a.population, r, k, RAD_CONFIGS) for r in range(folds.repeat.nunique()) for k in range(5)]
    with ProcessPoolExecutor(a.workers) as ex:
        nested = list(ex.map(run_nested, jobs))
    nested_oof = np.zeros((folds.repeat.nunique(), len(cohort)))
    for r, _, te, p, *_ in nested:
        nested_oof[r, te] = p
    res[("NESTED", "-", "-", "-", "ridge")] = nested_oof
    pd.DataFrame([{"repeat": r, "fold": k, "chosen": c, "inner_auc": s} for r, k, _, _, c, s in nested]
                 ).to_csv(out / "nested_choices.csv", index=False)

    key = lambda c: "|".join(map(str, c))
    oofs = {key(c): o for c, o in res.items()}
    ref_key = key(BASELINES[0])
    ev = evaluate_repeated(cohort, oofs, H, reference=ref_key, n_boot=a.n_boot)
    rows = []
    for c in res:
        rows.append({"variant": c[0], "stability": c[1], "selection": c[2], "integration": c[3], "learner": c[4],
                     **ev.loc[key(c)].dropna().to_dict()})
    table = pd.DataFrame(rows).sort_values("auc_ipcw", ascending=False)
    table.to_csv(out / "results.csv", index=False)
    pd.DataFrame({k: o.mean(0) for k, o in oofs.items()}).assign(scan_id=cohort.scan_id).to_csv(out / "oof.csv", index=False)
    pd.concat([pd.DataFrame(o.T, columns=[f"{k}#r{r}" for r in range(len(o))]) for k, o in oofs.items()], axis=1
              ).assign(scan_id=cohort.scan_id).to_csv(out / "oof_repeats.csv.gz", index=False)
    cols = ["variant", "stability", "selection", "integration", "learner", "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi",
            f"d_auc_ipcw_vs_{ref_key}", "d_auc_ipcw_lo", "d_auc_ipcw_hi", "auc_ipcw_averaged", "cal_slope"]
    print(table[[c for c in cols if c in table]].head(25).round(3).to_string(index=False))
