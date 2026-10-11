"""Schedule coupling (plan 3.2): is the baseline's signal a proxy for the surveillance schedule?

The 120-d label is only observable when a scan (or a clinical event) falls within 120 d, and the next scan is brought
forward when progression is suspected, so the gap to the next scan is itself strongly associated with the label. The
gap is NOT known at prediction time; conditioning on it is a conservative check (it partly absorbs the outcome).

gap = days from the index scan to the next MRI of the patient (MU: any timepoint in mu_index; LUMIERE: any rated
timepoint); scans without a next scan form their own stratum.

  (a) strata      AUC per gap tertile (+ no-next-scan stratum): IPCW AUC(120) with cohort-level censoring weights,
                  restricted to the stratum's cases/controls, and verified-label AUC; mean over CV repeats
  (b) adjustment  IPCW-weighted logistic regression of the verified label on [z logit(OOF), z log gap] (scans with a
                  next scan); conditional AUC = concordance over case-control pairs within the same gap stratum
                  (tertiles and quintiles); AUC of -gap alone and of an in-fold 2-variable logistic [logit(OOF), log gap]
  (c) sensitivity re-evaluate OOF predictions excluding early_post_rt scans and/or scans whose next scan is > 120 d
                  away (or absent); plus a refit of the baseline ridge/boosting trained only on those scans (same folds)
  (d) timing      Spearman of each timing feature with gap; grouped-CV R^2 of log gap on timing / baseline features
  (e) LUMIERE     (a)-(c) on the locked MU-trained predictions (single prediction vector, no refit)

All CIs: patient-cluster bootstrap (MU: every repeat of every model evaluated on the same draw).

    python -m prism.analyses.schedule [--n-boot 1000]   # -> outputs/results/analyses/schedule/
"""

from __future__ import annotations

import argparse
import warnings

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from prism.config import LUMIERE_ROOT, RESULTS
from prism.data import lumiere, mu
from prism.features import tabular
from prism.models.folds import load_folds
from prism.models.formulations import G_FLOOR, _observed_time, censoring_survival
from prism.models.metrics import fast_auc_brier, ipcw_context, repeated_bootstrap

H = 120
OUT = RESULTS / "analyses" / "schedule"
MU_MODELS = {"baseline_ridge": "None|none|none|none|ridge", "baseline_boosting": "None|none|none|none|gbm",
             "baseline_radiomics_nested": "NESTED|-|-|-|ridge"}
REFIT = {"baseline_ridge": (None, "none", "none", "none", "ridge"),
         "baseline_boosting": (None, "none", "none", "none", "gbm")}
LUM_MODELS = {"ct_ridge": "grade4|clinical+timing|ridge", "ct_boosting": "grade4|clinical+timing|gbm",
              "ctv_boosting": "grade4|clinical+timing+volumes|gbm"}
NO_NEXT = "no next scan"


# ---------------------------------------------------------------- data
def mu_gap(cohort: pd.DataFrame) -> np.ndarray:
    idx = mu.load_index()
    days = idx.groupby("patient_id").days_from_diagnosis_to_mri.apply(lambda s: np.sort(s.dropna().unique()))
    return _next(cohort.patient_id, cohort.days_from_diagnosis_to_mri, days)


def lumiere_gap(cohort: pd.DataFrame) -> np.ndarray:
    r = pd.read_csv(LUMIERE_ROOT / "LUMIERE-ExpertRating-v202211.csv")
    r.columns = ["patient_id", "date", "lt3m", "nonmeas", "rating", "rationale"]
    r["day"] = r.date.map(lumiere._week) * 7
    days = r.groupby("patient_id").day.apply(lambda s: np.sort(s.unique()))
    return _next(cohort.patient_id, cohort.days_since_surgery, days)


def _next(pids, scan_days, days) -> np.ndarray:
    out = []
    for p, t in zip(pids, scan_days):
        later = days.get(p, np.array([]))
        later = later[later > t]
        out.append(later[0] - t if len(later) else np.nan)
    return np.asarray(out, float)


def strata(gap: np.ndarray, q: int = 3) -> tuple[np.ndarray, list[str]]:
    """Codes 0..q-1 = gap quantile groups (scans with a next scan), q = no next scan."""
    ok = ~np.isnan(gap)
    edges = np.quantile(gap[ok], np.linspace(0, 1, q + 1))
    code = np.full(len(gap), q)
    code[ok] = np.clip(np.searchsorted(edges, gap[ok], side="right") - 1, 0, q - 1)
    names = [f"Q{i + 1}/{q} gap {edges[i]:.0f}-{edges[i + 1]:.0f} d" for i in range(q)] + [NO_NEXT]
    return code, names


def load_oofs(population: str, cohort: pd.DataFrame) -> dict[str, np.ndarray]:
    """model -> (n_repeats x n_scans) OOF predictions; falls back to the repeat-averaged oof.csv (1 row)."""
    d = RESULTS / "c3" / population
    rep = d / "oof_repeats.csv.gz"
    t = pd.read_csv(rep if rep.exists() else d / "oof.csv").set_index("scan_id").reindex(cohort.scan_id)
    out = {}
    for name, key in MU_MODELS.items():
        cols = [c for c in t.columns if c.split("#")[0] == key]
        if cols and not t[cols].isna().any().any():
            out[name] = t[cols].to_numpy(float).T
        elif cols:
            print(f"[schedule] {population}/{name}: {t[cols].isna().any(axis=1).sum()} scans without OOF -> skipped")
    return out


def _w(d: pd.DataFrame) -> np.ndarray:
    G = censoring_survival(d, H)
    return 1.0 / np.maximum(G(np.minimum(_observed_time(d, H), H)), G_FLOOR)


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _z(x):
    return (x - x.mean()) / (x.std() or 1.0)


# ---------------------------------------------------------------- statistics on one (resampled) data set
def _pairs(ctx, p, m):
    """IPCW concordance numerator / denominator over case-control pairs inside mask m (cohort-level weights)."""
    w = np.zeros(len(p))
    w[ctx["case"]] = ctx["w_case"]
    case, ctrl = ctx["case"] & m, ctx["ctrl"] & m
    if not case.any() or not ctrl.any():
        return 0.0, 0.0
    pk = np.sort(p[ctrl])
    lo = np.searchsorted(pk, p[case] - 1e-8, side="left")
    hi = np.searchsorted(pk, p[case] + 1e-8, side="right")
    return float((w[case] * (lo + 0.5 * (hi - lo))).sum()), float(w[case].sum() * len(pk))


def _vauc(y, p, m):
    k = m & ~np.isnan(y)
    return roc_auc_score(y[k], p[k]) if len(np.unique(y[k])) == 2 else np.nan


def _cond_vauc(y, p, code):
    num = den = 0.0
    for s in np.unique(code):
        k = (code == s) & ~np.isnan(y)
        a, b = p[k & (y == 1)], p[k & (y == 0)]
        if len(a) and len(b):
            num += ((a[:, None] > b[None]) + 0.5 * (a[:, None] == b[None])).sum()
            den += len(a) * len(b)
    return num / den if den else np.nan


def _logreg(y, X, w):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return LogisticRegression(penalty=None, max_iter=1000).fit(X, y, sample_weight=w).coef_[0]


def stats(d: pd.DataFrame, preds: dict[str, np.ndarray], gap: np.ndarray, codes: dict[str, np.ndarray],
          names: list[str], logistic: bool = True) -> dict[str, float]:
    """All (a)/(b) statistics, averaged over the rows (repeats) of each prediction matrix."""
    ctx = ipcw_context(d, H)
    y = d[f"label_{H}"].to_numpy(float)
    has = ~np.isnan(gap)
    out = {}
    if ctx is None:
        return out
    w = _w(d)
    kn = has & ~np.isnan(y)
    lg = np.log(gap)
    for m, P in preds.items():
        acc = {}
        for p in np.atleast_2d(P):
            r = {}
            for i, nm in enumerate(names):
                r[f"auc_ipcw|{nm}"] = fast_auc_brier(ctx, p[None], subset=codes["t3"] == i)[0][0]
                r[f"auc_verified|{nm}"] = _vauc(y, p, codes["t3"] == i)
            r["auc_ipcw|all"] = fast_auc_brier(ctx, p[None])[0][0]
            r["auc_ipcw|has_next"] = fast_auc_brier(ctx, p[None], subset=has)[0][0]
            for q in ("t3", "q5"):
                num, den = map(sum, zip(*[_pairs(ctx, p, codes[q] == s) for s in np.unique(codes[q])]))
                r[f"cond_auc_ipcw|{q}"] = num / den if den else np.nan
                r[f"cond_auc_verified|{q}"] = _cond_vauc(y, p, codes[q])
            if logistic and len(np.unique(y[kn])) == 2:
                zp, zg = _z(_logit(p[kn])), _z(lg[kn])
                r["beta_pred_unadj"] = _logreg(y[kn], zp[:, None], w[kn])[0]
                r["beta_pred_adj"], r["beta_loggap_adj"] = _logreg(y[kn], np.c_[zp, zg], w[kn])
                r["beta_loggap_unadj"] = _logreg(y[kn], zg[:, None], w[kn])[0]
            for k, v in r.items():
                acc.setdefault(k, []).append(v)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # strata without cases or controls
            out.update({f"{m}|{k}": float(np.nanmean(v)) for k, v in acc.items()})
    out["gap_alone|auc_ipcw|has_next"] = fast_auc_brier(ctx, -np.where(has, gap, 0)[None], subset=has)[0][0]
    out["gap_alone|auc_verified|has_next"] = _vauc(y, -np.where(has, gap, 0), has)
    return out


def bootstrap(d, preds, gap, codes, names, n_boot, seed=0, logistic=True) -> pd.DataFrame:
    point = stats(d, preds, gap, codes, names, logistic)
    rng = np.random.default_rng(seed)
    pid = d.patient_id.to_numpy()
    groups = {p: np.where(pid == p)[0] for p in np.unique(pid)}
    pats = np.array(list(groups))
    draws = []
    for _ in range(n_boot):
        idx = np.concatenate([groups[p] for p in rng.choice(pats, len(pats))])
        s = stats(d.iloc[idx].reset_index(drop=True), {k: np.atleast_2d(v)[:, idx] for k, v in preds.items()},
                  gap[idx], {k: v[idx] for k, v in codes.items()}, names, logistic)
        draws.append(s)
    B = pd.DataFrame(draws)
    rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for k, v in point.items():
            lo, hi = np.nanpercentile(B[k], [2.5, 97.5]) if k in B and B[k].notna().any() else (np.nan, np.nan)
            row = {"key": k, "estimate": v, "lo": lo, "hi": hi}
            if k.split("|")[-1].startswith("beta"):
                row["p_le0"] = float(np.mean(B[k].dropna() <= 0))
            rows.append(row)
    t = pd.DataFrame(rows)
    parts = t.key.str.split("|", n=2, expand=True)
    return t.assign(model=parts[0], stat=parts[1], stratum=parts[2]).drop(columns="key")


def stratum_counts(d, gap, code, names) -> pd.DataFrame:
    y = d[f"label_{H}"]
    return pd.DataFrame([{"stratum": nm, "n_scans": int((code == i).sum()),
                          "n_patients": d.patient_id[code == i].nunique(),
                          "n_pos": int((y[code == i] == 1).sum()), "n_neg": int((y[code == i] == 0).sum()),
                          "n_censored": int(y[code == i].isna().sum()),
                          "pos_rate_verified": float(y[code == i].mean()),
                          "gap_median": float(np.nanmedian(gap[code == i])) if i < len(names) - 1 else np.nan}
                         for i, nm in enumerate(names)])


# ---------------------------------------------------------------- (b) in-fold combination, (c) refit, (d) timing
def combo_oof(d, P, gap, fold_ids) -> np.ndarray:
    """In-fold 2-variable logistic [logit(OOF), log gap] (verified labels, IPCW weights); NaN where gap missing."""
    y = d[f"label_{H}"].to_numpy(float)
    has = ~np.isnan(gap)
    w = _w(d)
    out = np.full(P.shape, np.nan)
    for r, p in enumerate(P):
        X = np.c_[_logit(p), np.log(np.where(has, gap, 1))]
        for k in np.unique(fold_ids[r]):
            tr = (fold_ids[r] != k) & has & ~np.isnan(y)
            te = (fold_ids[r] == k) & has
            sc = StandardScaler().fit(X[tr])
            m = LogisticRegression(penalty=None, max_iter=1000).fit(sc.transform(X[tr]), y[tr], sample_weight=w[tr])
            out[r, te] = m.predict_proba(sc.transform(X[te]))[:, 1]
    return out


def fold_matrix(cohort) -> np.ndarray:
    f = load_folds()
    return np.array([cohort.scan_id.map(f[f.repeat == r].set_index("scan_id").fold).to_numpy()
                     for r in sorted(f.repeat.unique())])


def refit_subset(population, mask, fold_ids) -> dict[str, np.ndarray]:
    """Baseline ridge / boosting trained only on `mask` scans of the training folds, scored on `mask` test scans."""
    from prism.experiments import c3_radiomics as c3
    cohort, _, base, rad, er = c3.load(population)
    out = {}
    for name, cfg in REFIT.items():
        P = np.full((len(fold_ids), len(cohort)), np.nan)
        for r in range(len(fold_ids)):
            for k in np.unique(fold_ids[r]):
                tr = np.where((fold_ids[r] != k) & mask)[0]
                te = np.where((fold_ids[r] == k) & mask)[0]
                if len(te):
                    P[r, te] = c3.fit_predict(cfg, cohort, base, rad, er, tr, te, seed=r)
        out[name] = P[:, mask]
    return out


def timing_vs_gap(cohort, gap, fold_ids) -> pd.DataFrame:
    g = tabular.groups(cohort, legacy_radiomics=False)
    has = ~np.isnan(gap)
    lg = np.log(gap[has])
    rows = []
    for c in g["timing"]:
        x = g["timing"][c].to_numpy(float)[has]
        ok = ~np.isnan(x)
        rho, pv = spearmanr(x[ok], lg[ok])
        rows.append({"feature": c, "spearman_rho": rho, "p": pv, "n": int(ok.sum())})
    sets = {"timing": ["timing"], "treatment": ["treatment"], "timing+treatment": ["timing", "treatment"],
            "baseline (clinical+timing+treatment)": ["clinical", "timing", "treatment"]}
    for nm, gs in sets.items():
        X = pd.concat([g[k] for k in gs], axis=1).to_numpy(float)[has]
        r2 = []
        for fr in fold_ids[:, has]:
            pred = np.zeros(len(lg))
            for k in np.unique(fr):
                tr, te = fr != k, fr == k
                m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                  RidgeCV(alphas=np.logspace(-2, 3, 20))).fit(X[tr], lg[tr])
                pred[te] = m.predict(X[te])
            r2.append(1 - ((lg - pred) ** 2).sum() / ((lg - lg.mean()) ** 2).sum())
        rows.append({"feature": f"[CV R2 of log gap] {nm}", "cv_r2": float(np.mean(r2)),
                     "cv_r2_sd": float(np.std(r2)), "n": int(has.sum())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- drivers
def subsets(d, gap) -> dict[str, np.ndarray]:
    early = d.early_post_rt.to_numpy(float) == 1
    near = ~np.isnan(gap) & (gap <= H)
    return {"all": np.ones(len(d), bool), "excl_early_post_rt": ~early, "next_scan_le_120d": near,
            "excl_early_and_next_le_120d": ~early & near}


def sensitivity(d, preds, gap, n_boot, refit=None) -> pd.DataFrame:
    rows = []
    for sname, m in subsets(d, gap).items():
        ds = d[m].reset_index(drop=True)
        oofs = {f"{k} (oof)": np.atleast_2d(v)[:, m] for k, v in preds.items()}
        if refit is not None and sname != "all":
            oofs.update({f"{k} (refit on subset)": v for k, v in refit(m).items()})
        b = repeated_bootstrap(ds, oofs, H, n_boot=n_boot)
        y = ds[f"label_{H}"]
        vauc = {k: np.mean([_vauc(y.to_numpy(float), p, np.ones(len(ds), bool)) for p in o]) for k, o in oofs.items()}
        b = b.assign(subset=sname, n_scans=len(ds), n_patients=ds.patient_id.nunique(), n_pos=int((y == 1).sum()),
                     n_neg=int((y == 0).sum()), n_censored=int(y.isna().sum()), auc_verified=b.model.map(vauc))
        rows.append(b[["subset", "model", "n_scans", "n_patients", "n_pos", "n_neg", "n_censored", "n_repeats",
                       "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "auc_verified"]])
    return pd.concat(rows, ignore_index=True)


def describe(d, gap, label) -> dict:
    y = d[f"label_{H}"].to_numpy(float)
    has = ~np.isnan(gap)
    ev = d.event.to_numpy(bool) & has
    t_prog = d.progression_day.to_numpy(float) - _scan_day(d)
    return {"cohort": label, "n_scans": len(d), "n_with_next": int(has.sum()), "gap_median": float(np.nanmedian(gap)),
            "gap_iqr": f"{np.nanpercentile(gap, 25):.0f}-{np.nanpercentile(gap, 75):.0f}",
            "event_scans_with_next": int(ev.sum()),
            "progression_at_next_scan_pm7d": int((np.abs(t_prog - gap)[ev] <= 7).sum()),
            "auc_verified_minus_gap": _vauc(y, -np.where(has, gap, 0), has),
            **{f"pos_rate_gap_{lo}-{hi}": float(np.nanmean(y[has & (gap > lo) & (gap <= hi)]))
               for lo, hi in ((0, 60), (60, 90), (90, 120), (120, 180), (180, 100000))}}


def _scan_day(d):
    return (d.days_from_diagnosis_to_mri if "days_from_diagnosis_to_mri" in d else d.days_since_surgery).to_numpy(float)


def run_mu(population, n_boot, do_refit=True):
    cohort = mu.load_cohort(population)
    gap = mu_gap(cohort)
    preds = load_oofs(population, cohort)
    t3, names = strata(gap, 3)
    q5, _ = strata(gap, 5)
    fold_ids = fold_matrix(cohort)
    combo = {f"{k}+loggap (in-fold)": combo_oof(cohort, np.atleast_2d(v), gap, fold_ids[:len(np.atleast_2d(v))])
             for k, v in preds.items()}
    codes = {"t3": t3, "q5": q5}
    a = bootstrap(cohort, preds, gap, codes, names, n_boot)
    has = ~np.isnan(gap)
    dh = cohort[has].reset_index(drop=True)
    cb = repeated_bootstrap(dh, {**{k: np.atleast_2d(v)[:, has] for k, v in preds.items()},
                                 **{k: v[:, has] for k, v in combo.items()},
                                 "gap alone (-gap)": -gap[has][None]}, H, n_boot=n_boot)
    cb.loc[cb.model == "gap alone (-gap)", [c for c in cb if c.startswith("brier")]] = np.nan  # not a probability
    refit = (lambda m: refit_subset(population, m, fold_ids)) if do_refit else None
    sens = sensitivity(cohort, preds, gap, n_boot, refit)
    tim = timing_vs_gap(cohort, gap, fold_ids)
    rho = {f"spearman_oof_vs_gap|{k}": spearmanr(np.atleast_2d(v).mean(0)[has], gap[has]) for k, v in preds.items()}
    tim = pd.concat([tim, pd.DataFrame([{"feature": k, "spearman_rho": v[0], "p": v[1], "n": int(has.sum())}
                                        for k, v in rho.items()])])
    return (a.assign(population=population), stratum_counts(cohort, gap, t3, names).assign(population=population),
            cb.assign(population=population, subset="has_next"), sens.assign(population=population),
            tim.assign(population=population), describe(cohort, gap, f"MU {population}"),
            cohort[["scan_id"]].assign(gap_days=gap, stratum=[names[i] for i in t3]))


def run_lumiere(n_boot):
    lc = lumiere.load_cohort()
    gap = lumiere_gap(lc)
    lp = pd.read_csv(RESULTS / "external_lumiere" / "locked_predictions.csv").set_index("scan_id").reindex(lc.scan_id)
    preds = {k: lp[c].to_numpy(float)[None] for k, c in LUM_MODELS.items()}
    t3, names = strata(gap, 3)
    q5, _ = strata(gap, 5)
    a = bootstrap(lc, preds, gap, {"t3": t3, "q5": q5}, names, n_boot)
    sens = sensitivity(lc, preds, gap, n_boot)
    has = ~np.isnan(gap)
    early = lc.early_post_rt.to_numpy(float)[has]
    tim = pd.DataFrame([{"feature": f, "spearman_rho": r[0], "p": r[1]} for f, r in
                        (("log_days_since_surgery", spearmanr(lc.days_since_surgery[has], gap[has])),
                         ("early_post_rt", spearmanr(early, gap[has])))]
                       + [{"feature": f"spearman_oof_vs_gap|{k}", "spearman_rho": r[0], "p": r[1]} for k, r in
                          ((k, spearmanr(v[0][has], gap[has])) for k, v in preds.items())])
    return (a.assign(population="lumiere"), stratum_counts(lc, gap, t3, names).assign(population="lumiere"),
            sens.assign(population="lumiere"), tim.assign(population="lumiere", n=int(has.sum())),
            describe(lc, gap, "LUMIERE"), lc[["scan_id"]].assign(gap_days=gap, stratum=[names[i] for i in t3]))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m prism.analyses.schedule", description=__doc__)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--no-refit", action="store_true")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    res = [run_mu(p, a.n_boot, not a.no_refit) for p in ("grade4", "all_glioma")]
    lum = run_lumiere(a.n_boot)
    pd.concat([r[0] for r in res] + [lum[0]]).to_csv(OUT / "strata_and_adjustment.csv", index=False)
    pd.concat([r[1] for r in res] + [lum[1]]).to_csv(OUT / "stratum_counts.csv", index=False)
    pd.concat([r[2] for r in res]).to_csv(OUT / "gap_combination.csv", index=False)
    pd.concat([r[3] for r in res] + [lum[2]]).to_csv(OUT / "sensitivity.csv", index=False)
    pd.concat([r[4] for r in res] + [lum[3]]).to_csv(OUT / "timing_vs_gap.csv", index=False)
    pd.DataFrame([r[5] for r in res] + [lum[4]]).to_csv(OUT / "describe.csv", index=False)
    pd.concat([res[1][6].assign(cohort="MU"), lum[5].assign(cohort="LUMIERE")]).to_csv(OUT / "gap_per_scan.csv",
                                                                                       index=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
