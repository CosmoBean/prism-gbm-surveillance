"""Literature baselines ladder (docs/literature/comparison.md §5: B0, B1, B4) and a nested hyperparameter grid, under the
C3 protocol: shared 5x5 patient-grouped folds (outputs/data/folds.csv), verified 120-d labels for fitting, headline =
mean over repeats of the pooled-OOF IPCW AUC(120 d), paired patient-cluster bootstrap ΔAUC vs the C3 ridge baseline
(clinical + timing + treatment).

B0  persistence      log(1 + ET cc) now; log-ratio ET vs the previous scan (past-only, 0 without a prior)
B1  volumetric RANO  ET >= 40% and >= 1 cc above the past-only nadir (measurable nadir >= 0.1 cc; MU: nadir over post-RT
                     scans where an RT end date and an earlier post-RT scan exist), or >= 1 cc from a ~0 cc nadir.
                     Variants: + new ET component (MU), RANO 2.0 (no call inside the 12-week post-RT window), and the
                     continuous log-ratio vs nadir. Rules and scores get an in-fold 1-D logistic map (calibration only;
                     `auc_raw` = AUC of the unfitted score).
B4  Hashim-style Cox Cox PH (log ET + age + IDH + MGMT [+ grade 4 in all gliomas]) fitted in-fold on all training scans
                     with follow-up; risk = 1 - S(120 d | x). Harrell C reported for every model.
Ladder rows          clinical only, timing only, clinical + timing (ridge, inner log-loss C as in C3), baseline boosting.
Nested grid          ridge C in {0.01..3} and boosting depth {2,3} x lr {0.03,0.1} x min_samples_leaf {10,20}, each
                     chosen by inner 3-fold patient-grouped AUC within every outer training fold; also over both families.
LUMIERE (locked)     trained once on all MU scans (grade 4 / all gliomas), applied to LUMIERE; harmonised shared
                     volumes (DeepBraTumIA vs MU masks: different segmenters), ET history from all DeepBraTumIA studies
                     except pre-op; no RT end date (nadir over all priors; RANO 2.0 window = rater's < 3 months flag);
                     no component counts. Reference = locked shared clinical + timing ridge.

    python -m prism.analyses.baselines [--workers 8] [--n-boot 1000]
    -> $PRISM_OUTPUTS/results/analyses/baselines/{ladder.csv, lumiere.csv, nested_choices.csv, oof_repeats.csv.gz,
       forest.png}
"""

from __future__ import annotations

import argparse
import functools
import itertools
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sksurv.linear_model import CoxPHSurvivalAnalysis
from sksurv.metrics import concordance_index_censored
from threadpoolctl import threadpool_limits

from prism.config import MEASUREMENTS, RESULTS
from prism.data import lumiere, mu
from prism.features.tabular import SHARED, clinical, groups, shared_lumiere, shared_mu
from prism.models.folds import load_folds
from prism.models.formulations import CS, fit as fit_ridge
from prism.models.metrics import cluster_bootstrap, counted_warnings, evaluate_repeated, point_metrics

H = 120
OUT = RESULTS / "analyses" / "baselines"
PRE = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())])
GBM = HistGradientBoostingClassifier(max_depth=2, learning_rate=0.03, max_iter=150, min_samples_leaf=20,
                                     l2_regularization=2.0, max_features=0.5, random_state=0)  # = C3 baseline boosting
GBM_GRID = [dict(max_depth=d, learning_rate=lr, min_samples_leaf=m)
            for d, lr, m in itertools.product((2, 3), (0.03, 0.1), (10, 20))]
REF = "baseline ridge (C3)"
COX_COLS = ["log_et_cc", "age", "idh_mutant", "idh_unknown", "mgmt_methylated", "mgmt_unknown"]


# ---------------------------------------------------------------- past-only ET history
def et_history(index: pd.DataFrame, long: pd.DataFrame, post_rt_from: pd.Series | None = None) -> pd.DataFrame:
    """B0/B1 scores for index scans (scan_id, patient_id, day, et_cc[, early]) from all timepoints of the patient in
    `long` (patient_id, day, et_cc[, et_n_components]). `post_rt_from` (by patient): nadir over priors on/after that
    day when there is one (RANO post-RT baseline), else over all priors."""
    by_pat = {p: g.sort_values("day") for p, g in long.groupby("patient_id")}
    rows = []
    for r in index.itertuples():
        g = by_pat.get(r.patient_id, long.iloc[:0])
        prev = g[g.day < r.day]
        et = r.et_cc
        out = {"has_prior": float(len(prev) > 0)}
        if len(prev) and np.isfinite(et):
            base = prev
            if post_rt_from is not None and np.isfinite(post_rt_from.get(r.patient_id, np.nan)):
                post = prev[prev.day >= post_rt_from[r.patient_id]]
                base = post if len(post) else prev
            nadir = base.et_cc.min()
            grew, measurable = et - nadir >= 1.0, nadir >= 0.1
            out.update(et_logratio_prev=np.log((et + 0.1) / (prev.et_cc.iat[-1] + 0.1)),
                       et_logratio_nadir=np.log((et + 0.1) / (nadir + 0.1)),
                       vol_pd=float(measurable and grew and et >= 1.4 * nadir),
                       new_from_zero=float(not measurable and grew))
            if "et_n_components" in g:
                out["new_component"] = float(r.et_n_components > prev.et_n_components.iat[-1])
        rows.append(out)
    h = pd.DataFrame(rows, index=index.index).reindex(
        columns=["has_prior", "et_logratio_prev", "et_logratio_nadir", "vol_pd", "new_from_zero", "new_component"])
    h = h.fillna(0.0)
    h["log_et_cc"] = np.log1p(index.et_cc.to_numpy())
    h["rule"] = np.maximum(h.vol_pd, h.new_from_zero)
    h["rule_component"] = np.maximum(h.rule, h.new_component)
    h["rule_rano2"] = h.rule * (1 - index.early.fillna(0).to_numpy())
    return h


def mu_history(cohort: pd.DataFrame) -> pd.DataFrame:
    m = pd.read_csv(MEASUREMENTS).rename(columns={"mri_day": "day"})
    idx = cohort[["scan_id", "patient_id"]].assign(
        day=cohort.days_from_diagnosis_to_mri.to_numpy(float), early=cohort.early_post_rt,
        **m.set_index("scan_id").reindex(cohort.scan_id)[["et_cc", "et_n_components"]].reset_index(drop=True))
    rt_end = (cohort.days_from_diagnosis_to_mri - cohort.days_since_rt_end).groupby(cohort.patient_id).first()
    return et_history(idx, m[["patient_id", "day", "et_cc", "et_n_components"]], rt_end)


def lumiere_history(lc: pd.DataFrame) -> pd.DataFrame:
    v = lumiere.deepbratumia_volumes()
    r = pd.read_csv(lumiere.ROOT / "LUMIERE-ExpertRating-v202211.csv").iloc[:, [0, 1, 4]]
    r.columns = ["patient_id", "date", "rating"]
    preop = set(r.patient_id[r.rating.astype(str).str.strip().eq("Pre-Op")] + "_" + r.date[r.rating.astype(str).str.strip().eq("Pre-Op")])
    v = v[~v.scan_id.isin(preop)]
    v["patient_id"] = v.scan_id.str.split("_").str[0]
    v["day"] = v.scan_id.str.extract(r"week-(\d+)")[0].astype(float) * 7
    v["et_cc"] = v.raw_Enhancing_Core / 1000.0
    idx = lc[["scan_id", "patient_id"]].assign(day=lc.days_since_surgery.to_numpy(float), early=lc.early_post_rt,
                                               et_cc=lc.raw_Enhancing_Core.to_numpy(float) / 1000.0)
    return et_history(idx, v[["patient_id", "day", "et_cc"]].dropna())


# ---------------------------------------------------------------- learners (fit on train rows, predict test rows)
def _verified(cohort, rows):
    y = cohort[f"label_{H}"].to_numpy()
    return rows[~np.isnan(y[rows])], y


def ridge_fit(X, cohort, tr, seed=0):
    k, _ = _verified(cohort, tr)
    pre = clone(PRE).fit(X.iloc[k])
    model, _ = fit_ridge("verified", pre.transform(X.iloc[k]), cohort.iloc[k].reset_index(drop=True), H, seed=seed)
    return lambda Z: model.predict_proba(pre.transform(Z))[:, 1]


def plain_fit(X, cohort, tr, est, seed=0):
    """Fixed-hyperparameter learner (LogisticRegression or HistGradientBoosting) on verified training scans."""
    k, y = _verified(cohort, tr)
    pre = clone(PRE).fit(X.iloc[k])
    est = clone(est)
    if "random_state" in est.get_params():
        est.set_params(random_state=seed)
    est.fit(pre.transform(X.iloc[k]), y[k].astype(int))
    return lambda Z: est.predict_proba(pre.transform(Z))[:, 1]


def score_fit(s, cohort, tr, seed=0):
    """Monotone map of a one-column score: unpenalised 1-D logistic on verified training scans."""
    k, y = _verified(cohort, tr)
    med = float(np.nanmedian(s.iloc[tr]))  # missing volume (7 LUMIERE scans) -> training median
    m = LogisticRegression(penalty=None, max_iter=1000).fit(s.iloc[k].fillna(med).to_numpy(float)[:, None],
                                                           y[k].astype(int))
    return lambda Z: m.predict_proba(Z.fillna(med).to_numpy(float)[:, None])[:, 1]


def cox_fit(X, cohort, tr, seed=0):
    from sksurv.util import Surv
    pre = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]).fit(X.iloc[tr])
    d = cohort.iloc[tr]
    y = Surv.from_arrays(d.event.to_numpy(bool), np.maximum(d.time_to_event.to_numpy(float), 0.5))
    m = CoxPHSurvivalAnalysis(alpha=0.1, ties="efron").fit(pre.transform(X.iloc[tr]), y)

    def predict(Z):
        return np.array([1.0 - f(H) for f in m.predict_survival_function(pre.transform(Z))])
    return predict


def ridge_grid():
    return [("ridge", dict(C=c)) for c in CS]


def make_est(kind, hp):
    return (LogisticRegression(penalty="l2", max_iter=5000, **hp) if kind == "ridge"
            else clone(GBM).set_params(**hp))


def nested_fit(X, cohort, tr, candidates, seed=0):
    """Choose (kind, hp) by mean inner 3-fold patient-grouped AUC on verified training scans, refit on all of tr."""
    k, y = _verified(cohort, tr)
    scores = {}
    for i, (kind, hp) in enumerate(candidates):
        aucs = []
        for a, b in GroupKFold(n_splits=3).split(k, groups=cohort.patient_id.iloc[k]):
            p = plain_fit(X, cohort, k[a], make_est(kind, hp), seed)(X.iloc[k[b]])
            aucs.append(roc_auc_score(y[k[b]].astype(int), p))
        scores[i] = float(np.mean(aucs))
    best = max(scores, key=scores.get)
    kind, hp = candidates[best]
    return plain_fit(X, cohort, tr, make_est(kind, hp), seed), f"{kind}|{hp}", scores[best]


# ---------------------------------------------------------------- MU ladder
@functools.lru_cache(maxsize=2)
def mu_tables(population):
    cohort = mu.load_cohort(population)
    g = groups(cohort, legacy_radiomics=False)
    hist = mu_history(cohort)
    cox = pd.concat([hist[["log_et_cc"]], clinical(cohort)], axis=1)
    if population == "all_glioma":
        cox["grade4"] = cohort.grade4.astype(float)
    return cohort, g, hist, cox


def model_specs(population):
    """name -> (kind, payload). kind: ridge (feature groups), score (history column), cox, gbm, ridge_fixed, nested."""
    s = {
        REF: ("ridge", ["clinical", "timing", "treatment"]),
        "clinical only (ridge)": ("ridge", ["clinical"]),
        "timing only (ridge)": ("ridge", ["timing"]),
        "clinical + timing (ridge)": ("ridge", ["clinical", "timing"]),
        "B0 persistence: log ET volume": ("score", "log_et_cc"),
        "B0 prior trend: ET log-ratio vs previous": ("score", "et_logratio_prev"),
        "B1 volumetric rule (>=40% vs nadir or new ET)": ("score", "rule"),
        "B1 rule + new ET component": ("score", "rule_component"),
        "B1 rule, RANO 2.0 (no call <12 wk post-RT)": ("score", "rule_rano2"),
        "B1 continuous: ET log-ratio vs nadir": ("score", "et_logratio_nadir"),
        "B4 Hashim Cox (ET + age + grade + IDH + MGMT)": ("cox", None),
        "baseline boosting fixed (C3)": ("fixed", ("gbm", {})),
        "baseline ridge fixed C=0.1": ("fixed", ("ridge", {"C": 0.1})),
        "baseline ridge nested C (inner AUC)": ("nested", ridge_grid()),
        "baseline boosting nested grid": ("nested", [("gbm", hp) for hp in GBM_GRID]),
        "baseline nested ridge+boosting": ("nested", ridge_grid() + [("gbm", hp) for hp in GBM_GRID]),
    }
    return s


@counted_warnings
def run_fold(job):
    population, name, r, k = job
    threadpool_limits(1)
    cohort, g, hist, cox = mu_tables(population)
    kind, payload = model_specs(population)[name]
    folds = load_folds()
    f = cohort.scan_id.map(folds[folds.repeat == r].set_index("scan_id").fold).to_numpy()
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    base = pd.concat([g["clinical"], g["timing"], g["treatment"]], axis=1)
    choice = None
    if kind == "ridge":
        X = pd.concat([g[n] for n in payload], axis=1)
        p = ridge_fit(X, cohort, tr, r)(X.iloc[te])
    elif kind == "score":
        p = score_fit(hist[payload], cohort, tr, r)(hist[payload].iloc[te])
    elif kind == "cox":
        p = cox_fit(cox, cohort, tr, r)(cox.iloc[te])
    elif kind == "fixed":
        p = plain_fit(base, cohort, tr, make_est(*payload), r)(base.iloc[te])
    else:
        fn, choice, inner = nested_fit(base, cohort, tr, payload, r)
        p = fn(base.iloc[te])
        choice = {"population": population, "model": name, "repeat": r, "fold": k, "chosen": choice, "inner_auc": inner}
    return population, name, r, te, p, choice


def harrell(d, P):
    e, t = d.event.to_numpy(bool), d.time_to_event.to_numpy(float)
    return float(np.mean([concordance_index_censored(e, t, p)[0] for p in np.atleast_2d(P)]))


# ---------------------------------------------------------------- LUMIERE locked
def lumiere_rows(train_pop, n_boot):
    mc = mu.load_cohort(train_pop)
    lc = lumiere.load_cohort()
    MX, LX = shared_mu(mc), shared_lumiere(lc)
    mh, lh = mu_history(mc), lumiere_history(lc)
    MC, LC = MX[COX_COLS].copy(), LX[COX_COLS].copy()
    if train_pop == "all_glioma":
        MC["grade4"], LC["grade4"] = mc.grade4.astype(float).to_numpy(), 1.0
    all_rows = np.arange(len(mc))
    ct = SHARED["clinical"] + SHARED["timing"]
    preds = {
        "clinical + timing, shared (ridge) [reference]": ridge_fit(MX[ct], mc, all_rows)(LX[ct]),
        "clinical only, shared (ridge)": ridge_fit(MX[SHARED["clinical"]], mc, all_rows)(LX[SHARED["clinical"]]),
        "clinical + timing + volumes, shared (ridge)": ridge_fit(MX[ct + SHARED["volumes"]], mc, all_rows)(
            LX[ct + SHARED["volumes"]]),
        "B4 Hashim Cox (ET + age + grade + IDH + MGMT)": cox_fit(MC, mc, all_rows)(LC),
    }
    raw = {}
    for name, col in [("B0 persistence: log ET volume", "log_et_cc"),
                      ("B0 prior trend: ET log-ratio vs previous", "et_logratio_prev"),
                      ("B1 volumetric rule (>=40% vs nadir or new ET)", "rule"),
                      ("B1 rule, RANO 2.0 (no call <12 wk post-RT)", "rule_rano2"),
                      ("B1 continuous: ET log-ratio vs nadir", "et_logratio_nadir")]:
        preds[name] = score_fit(mh[col], mc, all_rows)(lh[col])
        raw[name] = point_metrics(lc, lh[col].fillna(lh[col].median()).to_numpy(float), H)["auc_ipcw"]
    ref = "clinical + timing, shared (ridge) [reference]"
    boot = cluster_bootstrap(lc, preds, H, reference=ref, n_boot=n_boot).set_index("formulation")
    rows = []
    for name, p in preds.items():
        rows.append({"population": f"LUMIERE (locked, trained on MU {train_pop})", "model": name,
                     **point_metrics(lc, p, H), "auc_raw": raw.get(name, np.nan), "harrell_c": harrell(lc, p),
                     **boot.loc[name].dropna().to_dict()})
    t = pd.DataFrame(rows).rename(columns={f"d_auc_ipcw_vs_{ref}": "d_auc_ipcw"})
    prev = {"B1 rule positive (LUMIERE)": float(lh.rule.mean()), "has prior (LUMIERE)": float(lh.has_prior.mean())}
    return t, prev


# ---------------------------------------------------------------- report
def forest(table, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pops = list(dict.fromkeys(table.population))
    ncol = 2
    nrow = int(np.ceil(len(pops) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(13, nrow * (0.3 * table.groupby("population").size().max() + 1.4)),
                             sharex=True, squeeze=False)
    for ax in axes.ravel()[len(pops):]:
        ax.set_visible(False)
    for ax, pop in zip(axes.ravel(), pops):
        t = table[(table.population == pop) & table.d_auc_ipcw.notna()].iloc[::-1]
        y = np.arange(len(t))
        ax.axvline(0, color="#52514e", lw=1)
        ax.hlines(y, t.d_auc_ipcw_lo, t.d_auc_ipcw_hi, color="#2a78d6", lw=2)
        ax.plot(t.d_auc_ipcw, y, "o", color="#2a78d6", ms=6, mec="#fcfcfb", mew=1.5)
        ax.set_yticks(y, t.model, fontsize=8, color="#0b0b0b")
        ref = table[(table.population == pop) & table.d_auc_ipcw.isna()].iloc[0]
        title = pop.replace("all_glioma", "all gliomas").replace("MU grade4", "MU grade 4")
        ax.set_title(f"{title}\nreference: {ref.model.replace(' [reference]', '')} (AUC {ref.auc_ipcw:.3f})",
                     fontsize=9, color="#0b0b0b", loc="left")
        ax.set_xlabel("ΔAUC(120 d) vs reference [95% CI]", fontsize=9, color="#52514e")
        ax.grid(axis="x", color="#e6e5e0", lw=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor="#fcfcfb")
    plt.close(fig)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m prism.analyses.baselines", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    folds = load_folds()
    R, K = folds.repeat.nunique(), folds.fold.nunique()
    pops = ("grade4", "all_glioma")
    jobs = [(pop, name, r, k) for pop in pops for name in model_specs(pop) for r in range(R) for k in range(K)]
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(run_fold, jobs, chunksize=4))
    tables, choices, oof_frames, notes = [], [], [], {}
    for pop in pops:
        cohort, _, hist, _ = mu_tables(pop)
        oofs = {name: np.zeros((R, len(cohort))) for name in model_specs(pop)}
        for p_, name, r, te, p, ch in res:
            if p_ == pop:
                oofs[name][r, te] = p
                if ch:
                    choices.append(ch)
        ev = evaluate_repeated(cohort, oofs, H, reference=REF, n_boot=a.n_boot)
        ev = ev.rename(columns={f"d_auc_ipcw_vs_{REF}": "d_auc_ipcw"})
        ev["harrell_c"] = [harrell(cohort, oofs[n]) for n in ev.index]
        specs = model_specs(pop)
        ev["auc_raw"] = [point_metrics(cohort, hist[specs[n][1]].fillna(hist[specs[n][1]].median()).to_numpy(float), H)["auc_ipcw"]
                         if specs[n][0] == "score" else np.nan for n in ev.index]
        ev.insert(0, "population", {"grade4": "MU grade 4", "all_glioma": "MU all gliomas"}[pop])
        tables.append(ev.reset_index().rename(columns={"index": "model"}))
        oof_frames.append(pd.concat([pd.DataFrame(o.T, columns=[f"{pop}|{n}#r{r}" for r in range(R)])
                                     for n, o in oofs.items()], axis=1).assign(scan_id=cohort.scan_id))
        for c in ("rule", "rule_component", "rule_rano2", "has_prior"):
            notes[f"{pop} {c} positive"] = float(hist[c].mean())
    lum = []
    for pop in pops:
        t, prev = lumiere_rows(pop, a.n_boot)
        lum.append(t)
        notes.update(prev)
    lum = pd.concat(lum, ignore_index=True)
    ladder = pd.concat(tables, ignore_index=True)
    ladder.to_csv(OUT / "ladder.csv", index=False)
    lum.to_csv(OUT / "lumiere.csv", index=False)
    pd.DataFrame(choices).to_csv(OUT / "nested_choices.csv", index=False)
    pd.concat(oof_frames, axis=0).to_csv(OUT / "oof_repeats.csv.gz", index=False)
    pd.Series(notes).to_csv(OUT / "prevalence.csv", header=["fraction"])
    cols = ["population", "model", "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "d_auc_ipcw", "d_auc_ipcw_lo",
            "d_auc_ipcw_hi", "cal_slope", "oe_ratio", "harrell_c", "auc_raw"]
    both = pd.concat([ladder[cols], lum[[c for c in cols if c in lum]]], ignore_index=True)
    forest(both, OUT / "forest.png")
    pd.set_option("display.width", 250)
    print(both.round(3).to_string(index=False))
    print(pd.Series(notes).round(3).to_string())
    ch = pd.DataFrame(choices)
    if len(ch):
        print(ch.groupby(["population", "model"]).chosen.value_counts().to_string())
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
