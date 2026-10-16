"""Auditable decision-support layer on the clinical + timing + treatment ridge baseline (no new predictor).

ANALYSIS PLAN: docs/results/AUDIT_SYSTEM.md, section "Plan" (snapshot written before any output of this module:
outputs/results/analyses/audit_system/PLAN_snapshot.md). Summary:
  1. locked artifact (all MU scans, grade 4 and all gliomas) + model card with hashes, git state, CV performance
  2. per-scan audit records (OOF fits, repeat 0): inputs with source + as-of day, phase of care, risk with patient-
     bootstrap interval, exact log-odds contributions (checked to sum to the logit), referral flags
     (i) early post-RT <= 84 d, (ii) out of distribution, (iii) conformal set {0, 1} at alpha = 0.2
  3. inside the 5x5 patient-grouped CV (every step fitted on the training fold; conformal calibration patients split
     from the training fold): risk-coverage curves vs random and phase-composition-matched removal, conformal sets at
     alpha 0.1 / 0.2, referral rules vs composition references, within-phase AUCs.
     P1 = conformal coverage at alpha = 0.2 (target >= 0.78), overall and per phase.
     P2 = AUC on retained scans at 70% coverage minus the composition-matched random-removal AUC (bootstrap CI).
  4. shortcut / bias audit: unknown-marker indicators, timing-only / treatment-only models, subgroups, LUMIERE transport
  5. explanation stability (25 CV fits, 200 patient bootstraps; LUMIERE refit of the shared-feature model)
  6. MANIFEST.json (hashes, git, versions, command line)

    python -m prism audit [--workers 24] [--n-boot 1000] [--n-fit-boot 200]
    -> $PRISM_OUTPUTS/results/analyses/audit_system/
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from prism.analyses.phase_ladder import phase_label
from prism.audit import conformal as cf
from prism.audit.model import (GROUPS, Locked, bootstrap_fits, design, fit_pipeline, ood_flags, ood_ranges,
                               source_feature)
from prism.audit.provenance import FEATURES, git_state, package_versions, sha256
from prism.audit.record import build, render_md
from prism.config import FOLDS, MU_CLINICAL, MU_COHORT, MU_INDEX, LUMIERE_COHORT, RESULTS, REPO
from prism.data.mu import load_cohort, load_index
from prism.experiments import c3_radiomics as c3
from prism.models.folds import load_folds
from prism.models.formulations import G_FLOOR, _observed_time, censoring_survival
from prism.models.metrics import evaluate_repeated, fast_auc_brier, ipcw_context, point_metrics

H = c3.H
OUT = RESULTS / "analyses" / "audit_system"
POPS = ("grade4", "all_glioma")
ALPHAS = (0.1, 0.2)
PHASES = ("pre_rt", "during_rt", "early_post_rt", "later_post_rt")
COVERAGES = tuple(np.round(np.arange(1.0, 0.29, -0.05), 2))
TARGET_COVERAGE = 0.70
UNKNOWN = ["idh_unknown", "mgmt_unknown"]


@lru_cache(maxsize=4)
def context(pop):
    cohort = load_cohort(pop)
    X, groups = design(cohort)
    return cohort, load_folds(), X, groups, phase_label(cohort)


def arms(X, groups):
    cols = list(X.columns)
    return {"no_unknown_markers": [c for c in cols if c not in UNKNOWN],
            "no_unknown_markers_no_rt_date_unknown": [c for c in cols if c not in UNKNOWN + ["rt_date_unknown"]],
            "timing_only": [c for c in cols if groups[c] == "timing"],
            "treatment_only": [c for c in cols if groups[c] == "treatment"]}


# ---------------------------------------------------------------- CV jobs
def cv_job(job):
    pop, r, k, n_fit_boot = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    cohort, folds, X, groups, phase = context(pop)
    y = cohort[f"label_{H}"].to_numpy()
    pid = cohort.patient_id.to_numpy()
    f = c3._fold_ids(cohort, folds, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    m = fit_pipeline(X, cohort, tr, groups, seed=r)
    Xte = X.iloc[te]
    p = m.predict(Xte)
    err = float(np.max(np.abs(m.intercept + m.contributions(Xte).sum(1).to_numpy() - m.logit(Xte))))
    p_tr = m.predict(X.iloc[tr])
    thr = float(np.quantile(np.maximum(p_tr, 1 - p_tr), 1 - TARGET_COVERAGE))
    ranges = ood_ranges(X, tr)
    ood = ood_flags(Xte, cohort.iloc[te], ranges)
    B = np.array([b.predict(Xte) for b in bootstrap_fits(X, cohort, tr, groups, n_fit_boot, seed=1000 * r + k)])
    proper, cal = cf.patient_split(pid[tr], 0.3, seed=10 * r + k)
    mc = fit_pipeline(X, cohort, tr[proper], groups, seed=r)
    cr = tr[cal][~np.isnan(y[tr[cal]])]
    s = cf.scores(mc.predict(X.iloc[cr]), y[cr])
    q = {a: cf.threshold(s, pid[cr], a) for a in ALPHAS}
    pc = mc.predict(Xte)
    arm_p = {n: fit_pipeline(X[c], cohort, tr, groups, seed=r).predict(X[c].iloc[te]) for n, c in arms(X, groups).items()}
    return {"pop": pop, "r": r, "k": k, "te": te, "p": p, "sum_err": err, "thr": thr, "ood": ood,
            "lo": np.percentile(B, 2.5, 0), "hi": np.percentile(B, 97.5, 0), "pc": pc, "q": q, "arms": arm_p,
            "fitted": m, "ranges": ranges, "C": m.C, "n_cal_patients": len(np.unique(pid[cr])), "n_cal_scans": len(cr)}


def locked_job(job):
    pop, n_fit_boot = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    cohort, folds, X, groups, phase = context(pop)
    y = cohort[f"label_{H}"].to_numpy()
    pid = cohort.patient_id.to_numpy()
    rows = np.arange(len(cohort))
    m = fit_pipeline(X, cohort, rows, groups, seed=0)
    boot = bootstrap_fits(X, cohort, rows, groups, n_fit_boot, seed=0)
    proper, cal = cf.patient_split(pid, 0.3, seed=0)
    mc = fit_pipeline(X, cohort, rows[proper], groups, seed=0)
    cr = rows[cal][~np.isnan(y[cal])]
    s = cf.scores(mc.predict(X.iloc[cr]), y[cr])
    return Locked(pop, m, boot, mc, {a: cf.threshold(s, pid[cr], a) for a in ALPHAS}, ood_ranges(X, rows),
                  len(cohort), int((~np.isnan(y)).sum()), cohort.patient_id.nunique())


# ---------------------------------------------------------------- metric helpers
def auc_brier(ctx, p, mask=None):
    a, b = fast_auc_brier(ctx, p[None, :], subset=mask)
    return a[0], b[0]


def ipcw_weights(d):
    G = censoring_survival(d, H)
    return 1.0 / np.maximum(G(np.minimum(_observed_time(d, H), H)), G_FLOOR)


def wlogistic(x, y, w, offset=False, iters=50):
    """Weighted logistic: slope model y ~ a + b x (returns a, b) or CITL y ~ a + offset(x) (returns a, 1)."""
    a, b = 0.0, 1.0
    for _ in range(iters):
        eta = a + b * x
        mu = 1 / (1 + np.exp(-eta))
        g = w * (y - mu)
        h = w * mu * (1 - mu)
        if offset:
            step = g.sum() / max(h.sum(), 1e-12)
            a += step
            if abs(step) < 1e-10:
                break
        else:
            J = np.array([[h.sum(), (h * x).sum()], [(h * x).sum(), (h * x * x).sum()]])
            try:
                da, db = np.linalg.solve(J, [g.sum(), (g * x).sum()])
            except np.linalg.LinAlgError:
                return np.nan, np.nan
            a, b = a + da, b + db
            if abs(da) + abs(db) < 1e-10:
                break
    return a, b


def km_risk(d):
    from sksurv.nonparametric import kaplan_meier_estimator
    t = _observed_time(d, H)
    times, km = kaplan_meier_estimator(d["event"].to_numpy(bool), t)
    return 1.0 - float(km[times <= H][-1]) if (times <= H).any() else 0.0


def stratum_metrics(d, P):
    """Mean over repeats of IPCW AUC/Brier (censoring re-estimated in d), IPCW slope and CITL, KM O/E."""
    ctx = ipcw_context(d, H)
    y = d[f"label_{H}"].to_numpy(float)
    k = ~np.isnan(y)
    w = ipcw_weights(d)
    obs = km_risk(d)
    out = {m: [] for m in ("auc_ipcw", "brier_ipcw", "cal_slope", "citl", "oe_ratio")}
    for p in np.atleast_2d(P):
        a, b = auc_brier(ctx, p) if ctx is not None else (np.nan, np.nan)
        lg = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
        two = len(np.unique(y[k])) == 2
        out["auc_ipcw"].append(a)
        out["brier_ipcw"].append(b)
        out["cal_slope"].append(wlogistic(lg[k], y[k], w[k])[1] if two else np.nan)
        out["citl"].append(wlogistic(lg[k], y[k], w[k], offset=True)[0] if two else np.nan)
        out["oe_ratio"].append(obs / p.mean())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return {m: float(np.nanmean(v)) for m, v in out.items()}


def patient_groups(d):
    pid = d.patient_id.to_numpy()
    g = {p: np.where(pid == p)[0] for p in np.unique(pid)}
    return g, np.array(list(g))


def stratum_job(job):
    pop, name, level, mask, P, n_boot, seed = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    cohort = context(pop)[0]
    d = cohort[mask].reset_index(drop=True)
    Ps = P[:, mask]
    y = d[f"label_{H}"]
    row = {"population": pop, "stratum": name, "level": level, "n_scans": len(d), "n_patients": d.patient_id.nunique(),
           "events": int((y == 1).sum()), "non_events": int((y == 0).sum()), "censored": int(y.isna().sum())}
    row["descriptive_only"] = row["events"] < 10
    try:
        row.update(stratum_metrics(d, Ps))
    except Exception as e:  # noqa: BLE001
        row["error"] = str(e)[:80]
        return row
    g, pats = patient_groups(d)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        idx = np.concatenate([g[p] for p in rng.choice(pats, len(pats))])
        db = d.iloc[idx].reset_index(drop=True)
        if db[f"label_{H}"].nunique(dropna=True) < 2:
            continue
        try:
            draws.append(stratum_metrics(db, Ps[:, idx]))
        except Exception:  # noqa: BLE001
            continue
    D = pd.DataFrame(draws)
    for m in D.columns:
        row[f"{m}_lo"], row[f"{m}_hi"] = np.nanpercentile(D[m], [2.5, 97.5]) if D[m].notna().any() else (np.nan,) * 2
    row["n_boot_ok"] = len(D)
    return row


def matched_draw(rng, keep, phase):
    """Random subset with the same number of kept scans per phase as `keep`."""
    out = np.zeros(len(keep), bool)
    for ph in np.unique(phase):
        pos = np.where(phase == ph)[0]
        n = int(keep[pos].sum())
        if n:
            out[rng.choice(pos, n, replace=False)] = True
    return out


def random_draw(rng, n_keep, n):
    out = np.zeros(n, bool)
    out[rng.choice(n, n_keep, replace=False)] = True
    return out


def p2_boot_job(job):
    pop, P, R, phase, seeds, n_ref = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    cohort = context(pop)[0]
    g, pats = patient_groups(cohort)
    out = []
    for s in seeds:
        rng = np.random.default_rng(s)
        idx = np.concatenate([g[p] for p in rng.choice(pats, len(pats))])
        ctx = ipcw_context(cohort.iloc[idx].reset_index(drop=True), H)
        if ctx is None:
            continue
        ph = phase[idx]
        ret, ref = [], []
        for r in range(len(P)):
            keep = R[r][idx]
            ret.append(auc_brier(ctx, P[r][idx], keep)[0])
            ref.append(np.nanmean([auc_brier(ctx, P[r][idx], matched_draw(rng, keep, ph))[0] for _ in range(n_ref)]))
        out.append((np.nanmean(ret), np.nanmean(ref)))
    return out


# ---------------------------------------------------------------- analyses
def risk_coverage(cohort, P, conf, phase, n_draw, seed=0, name="max_prob"):
    ctx = ipcw_context(cohort, H)
    n = P.shape[1]
    rng = np.random.default_rng(seed)
    rows = []
    for c in COVERAGES:
        nk = int(round(c * n))
        a_sel, b_sel, keeps = [], [], []
        for r in range(len(P)):
            keep = np.zeros(n, bool)
            keep[np.argsort(-conf[r], kind="stable")[:nk]] = True
            keeps.append(keep)
            a, b = auc_brier(ctx, P[r], keep)
            a_sel.append(a)
            b_sel.append(b)
        rand = np.array([[auc_brier(ctx, P[r], random_draw(rng, nk, n)) for r in range(len(P))] for _ in range(n_draw)])
        comp = np.array([[auc_brier(ctx, P[r], matched_draw(rng, keeps[r], phase)) for r in range(len(P))]
                         for _ in range(n_draw)])
        ra, rb = np.nanmean(rand[..., 0], 1), np.nanmean(rand[..., 1], 1)
        ca, cb = np.nanmean(comp[..., 0], 1), np.nanmean(comp[..., 1], 1)
        mix = pd.Series(phase[keeps[0]]).value_counts(normalize=True)
        rows.append({"confidence": name, "coverage": c, "n_retained": nk,
                     "auc_ipcw": np.mean(a_sel), "brier_ipcw": np.mean(b_sel),
                     "auc_random": ra.mean(), "auc_random_lo": np.percentile(ra, 2.5), "auc_random_hi": np.percentile(ra, 97.5),
                     "brier_random": rb.mean(),
                     "auc_composition": ca.mean(), "auc_composition_lo": np.percentile(ca, 2.5),
                     "auc_composition_hi": np.percentile(ca, 97.5), "brier_composition": cb.mean(),
                     **{f"share_{p}_r0": float(mix.get(p, 0.0)) for p in PHASES}})
    return rows


def coverage_table(pop, cohort, sets, phase, n_boot, seed=0):
    """Empirical coverage per alpha, overall / per phase / patient-weighted, with patient-bootstrap CIs."""
    y = cohort[f"label_{H}"].to_numpy(float)
    k = ~np.isnan(y)
    g, pats = patient_groups(cohort)
    rows = []
    for a in ALPHAS:
        h0, h1 = sets[a]
        cov = np.where(y == 1, h1, h0).astype(float)  # (R x n); only verified scans used
        single = (h0 ^ h1)
        empty = ~(h0 | h1)
        for ph in ("all",) + PHASES:
            m = k & (phase == ph if ph != "all" else True)
            if not m.any():
                continue
            stat = lambda idx: cov[:, idx][:, m[idx]].mean()
            point = stat(np.arange(len(y)))
            rng = np.random.default_rng(seed)
            boots = []
            for _ in range(n_boot):
                idx = np.concatenate([g[p] for p in rng.choice(pats, len(pats))])
                if m[idx].any():
                    boots.append(stat(idx))
            pw = pd.DataFrame({"pid": cohort.patient_id[m], "c": cov[:, m].mean(0)}).groupby("pid").c.mean().mean()
            mm = (phase == ph) if ph != "all" else np.ones(len(y), bool)
            rows.append({"population": pop, "alpha": a, "phase": ph, "n_verified_scans": int(m.sum()),
                         "events": int((y[m] == 1).sum()), "coverage": point,
                         "coverage_lo": np.percentile(boots, 2.5), "coverage_hi": np.percentile(boots, 97.5),
                         "coverage_patient_weighted": pw, "target": 0.78 if a == 0.2 else 1 - a,
                         "coverage_events": cov[:, m & (y == 1)].mean() if (m & (y == 1)).any() else np.nan,
                         "coverage_non_events": cov[:, m & (y == 0)].mean() if (m & (y == 0)).any() else np.nan,
                         "singleton_rate_all_scans": single[:, mm].mean(), "both_rate_all_scans": (h0 & h1)[:, mm].mean(),
                         "empty_rate_all_scans": empty[:, mm].mean()})
    return rows


def subset_row(cohort, P, mask, ctx):
    """AUC/Brier with cohort-level censoring weights + AUC, O/E, slope, CITL with censoring re-estimated in the subset."""
    a = [auc_brier(ctx, P[r], mask[r] if mask.ndim == 2 else mask) for r in range(len(P))]
    row = {"auc_ipcw": np.nanmean([x[0] for x in a]), "brier_ipcw": np.nanmean([x[1] for x in a])}
    pm = []
    for r in range(len(P)):
        mr = mask[r] if mask.ndim == 2 else mask
        try:
            pm.append(stratum_metrics(cohort[mr].reset_index(drop=True), P[r][mr]))
        except Exception:  # noqa: BLE001
            pass
    if pm:
        pm = pd.DataFrame(pm)
        row.update({"auc_ipcw_within_subset": pm.auc_ipcw.mean(), "oe_ratio": pm.oe_ratio.mean(),
                    "cal_slope": pm.cal_slope.mean(), "citl": pm.citl.mean()})
    return row


def referral_tables(pop, cohort, P, rules, phase, n_draw, seed=0):
    ctx = ipcw_context(cohort, H)
    y = cohort[f"label_{H}"]
    n = P.shape[1]
    rng = np.random.default_rng(seed)
    rows, within = [], []
    for name, M in rules.items():
        M = np.broadcast_to(M, P.shape)  # referred mask (R x n)
        keep = ~M
        rate = M.mean()
        base = {"population": pop, "rule": name, "referral_rate": rate,
                "n_referred_r0": int(M[0].sum()), "events_referred_r0": int((y[M[0]] == 1).sum()),
                "events_retained_r0": int((y[keep[0]] == 1).sum())}
        all_ = subset_row(cohort, P, np.ones_like(keep), ctx)
        ret = subset_row(cohort, P, keep, ctx)
        ref = subset_row(cohort, P, M, ctx) if M.any() else {}
        rand = np.array([np.mean([auc_brier(ctx, P[r], random_draw(rng, int(keep[r].sum()), n))[0] for r in range(len(P))])
                         for _ in range(n_draw)])
        comp = np.array([np.mean([auc_brier(ctx, P[r], matched_draw(rng, keep[r], phase))[0] for r in range(len(P))])
                         for _ in range(n_draw)])
        rows.append({**base, "auc_all": all_["auc_ipcw"], "auc_retained": ret["auc_ipcw"],
                     "auc_referred": ref.get("auc_ipcw", np.nan), "brier_retained": ret["brier_ipcw"],
                     "brier_referred": ref.get("brier_ipcw", np.nan),
                     "auc_retained_within_subset": ret.get("auc_ipcw_within_subset"),
                     "oe_retained": ret.get("oe_ratio"), "slope_retained": ret.get("cal_slope"),
                     "oe_referred": ref.get("oe_ratio"), "slope_referred": ref.get("cal_slope"),
                     "citl_retained": ret.get("citl"), "citl_referred": ref.get("citl"),
                     "auc_random_removal": rand.mean(), "auc_random_lo": np.percentile(rand, 2.5),
                     "auc_random_hi": np.percentile(rand, 97.5), "auc_composition_matched": np.nanmean(comp),
                     "auc_composition_lo": np.nanpercentile(comp, 2.5), "auc_composition_hi": np.nanpercentile(comp, 97.5),
                     "gain_vs_random": ret["auc_ipcw"] - rand.mean(),
                     "gain_vs_composition": ret["auc_ipcw"] - np.nanmean(comp)})
        for ph in PHASES:
            pm = phase == ph
            if not pm.any():
                continue
            a_all = np.nanmean([auc_brier(ctx, P[r], pm)[0] for r in range(len(P))])
            a_ret = np.nanmean([auc_brier(ctx, P[r], pm & keep[r])[0] for r in range(len(P))])
            within.append({"population": pop, "rule": name, "phase": ph, "n_scans": int(pm.sum()),
                           "events": int((y[pm] == 1).sum()), "non_events": int((y[pm] == 0).sum()),
                           "referred_share": float(M[:, pm].mean()), "auc_phase_all": a_all,
                           "auc_phase_retained": a_ret})
    return rows, within


def unknown_by_label(pop, cohort):
    y = cohort[f"label_{H}"].map({1.0: "progression", 0.0: "no_progression"}).fillna("censored")
    rows = []
    for mk in ("idh", "mgmt", "atrx", "codel_1p19q"):
        if mk not in cohort:
            continue
        unk = cohort[mk].astype(str).str.lower().isin(["unknown", "nan"])
        for lab in ("progression", "no_progression", "censored"):
            m = y == lab
            rows.append({"population": pop, "marker": mk, "label_120": lab, "n_scans": int(m.sum()),
                         "n_unknown": int((unk & m).sum()), "share_unknown": float(unk[m].mean()) if m.any() else np.nan,
                         "n_patients_unknown": cohort[unk & m].patient_id.nunique()})
    return rows


def strata(cohort, phase):
    s = {}
    if cohort.gbm.nunique() > 1:
        s["gbm"] = {"GBM": cohort.gbm.eq(True).to_numpy(), "non-GBM": cohort.gbm.eq(False).to_numpy()}
    s["mgmt"] = {lv: cohort.mgmt.eq(lv).to_numpy() for lv in ("methylated", "unmethylated", "unknown")}
    s["mgmt_known"] = {"known": cohort.mgmt.ne("unknown").to_numpy(), "unknown": cohort.mgmt.eq("unknown").to_numpy()}
    s["idh"] = {lv: cohort.idh.eq(lv).to_numpy() for lv in ("wildtype", "mutant", "unknown")}
    s["sex"] = {"male": cohort.male.eq(1).to_numpy(), "female": cohort.male.eq(0).to_numpy()}
    pa = cohort.groupby("patient_id").age.first()
    t1, t2 = np.quantile(pa, [1 / 3, 2 / 3])
    s["age_tertile"] = {f"<= {t1:g}": cohort.age.le(t1).to_numpy(),
                        f"({t1:g}, {t2:g}]": (cohort.age.gt(t1) & cohort.age.le(t2)).to_numpy(),
                        f"> {t2:g}": cohort.age.gt(t2).to_numpy()}
    s["phase"] = {ph: phase == ph for ph in PHASES}
    return s


def lumiere_transport(pop, n_fit_boot, seed=0):
    from prism.experiments import external_lumiere as ext
    mc, MX = ext.mu_table(pop == "grade4")
    lc, LX = ext.lumiere_table()
    cols = ext.FEATURE_SETS["clinical+timing+volumes"]
    smd = []
    for c in cols:
        a, b = MX[c].astype(float), LX[c].astype(float)
        sd = np.sqrt((a.var() + b.var()) / 2)
        smd.append({"population": pop, "feature": c, "mu_mean": a.mean(), "lumiere_mean": b.mean(),
                    "mu_missing": a.isna().mean(), "lumiere_missing": b.isna().mean(),
                    "smd": (b.mean() - a.mean()) / sd if sd > 0 else np.nan})
    pred, pre, model = ext.fit("ridge", MX[cols], mc, return_parts=True)
    names = [str(c) for c in pre.get_feature_names_out()]
    coef = model.coef_[0]
    cm = pd.DataFrame(pre.transform(MX[cols]) * coef, columns=names)
    cl = pd.DataFrame(pre.transform(LX[cols]) * coef, columns=names)
    contrib = pd.DataFrame({"population": pop, "column": names, "coef": coef, "mu_mean_contribution": cm.mean().values,
                            "lumiere_mean_contribution": cl.mean().values})
    contrib["shift"] = contrib.lumiere_mean_contribution - contrib.mu_mean_contribution
    contrib = contrib.reindex(contrib["shift"].abs().sort_values(ascending=False).index)
    lin_shift = float((cl.sum(1).mean() - cm.sum(1).mean()))
    oe = []
    for arm, cs in {"locked_shared": cols, "locked_shared_no_unknown_markers": [c for c in cols if c not in UNKNOWN]}.items():
        p = ext.fit("ridge", MX[cs], mc)(LX[cs])
        pm = point_metrics(lc, p, H)
        oe.append({"population": pop, "arm": arm, "auc_ipcw": pm["auc_ipcw"], "oe_ratio": pm["oe_ratio"],
                   "cal_slope": pm["cal_slope"], "mean_pred": p.mean(), "km_risk": km_risk(lc)})
    # conformal under shift: MU patient split 70/30 -> calibrate -> LUMIERE coverage
    pid = mc.patient_id.to_numpy()
    proper, cal = cf.patient_split(pid, 0.3, seed=seed)
    yM = mc[f"label_{H}"].to_numpy()
    fpred = ext.fit("ridge", MX[cols][proper].reset_index(drop=True), mc[proper].reset_index(drop=True))
    cr = cal & ~np.isnan(yM)
    s = cf.scores(fpred(MX[cols][cr]), yM[cr])
    yL = lc[f"label_{H}"].to_numpy()
    kL = ~np.isnan(yL)
    pL = fpred(LX[cols])
    conf_rows = []
    for a in ALPHAS:
        q = cf.threshold(s, pid[cr], a)
        h0, h1 = cf.prediction_sets(pL, q)
        cov = np.where(yL == 1, h1, h0)[kL]
        conf_rows.append({"population": pop, "alpha": a, "q": q, "lumiere_coverage": cov.mean(),
                          "lumiere_coverage_events": np.where(yL == 1, h1, h0)[kL & (yL == 1)].mean(),
                          "lumiere_coverage_non_events": np.where(yL == 1, h1, h0)[kL & (yL == 0)].mean(),
                          "lumiere_singleton_rate": (h0 ^ h1).mean(), "n_lumiere_verified": int(kL.sum())})
    # explanation stability of the shared-feature model refit on LUMIERE
    mu_coef = pd.Series(coef, index=names)
    _, lpre, lmodel = ext.fit("ridge", LX[cols], lc, return_parts=True)
    lcoef = pd.Series(lmodel.coef_[0], index=[str(c) for c in lpre.get_feature_names_out()])
    rng = np.random.default_rng(seed)
    g, pats = patient_groups(lc)
    bcoefs = []
    while len(bcoefs) < n_fit_boot:
        idx = np.concatenate([g[p] for p in rng.choice(pats, len(pats))])
        lb = lc.iloc[idx].reset_index(drop=True)
        if lb[f"label_{H}"].nunique(dropna=True) < 2:
            continue
        _, bp, bm = ext.fit("ridge", LX[cols].iloc[idx].reset_index(drop=True), lb, return_parts=True)
        bcoefs.append(pd.Series(bm.coef_[0], index=[str(c) for c in bp.get_feature_names_out()]))
    BC = pd.DataFrame(bcoefs)
    stab = [{"population": pop, "column": c, "mu_locked_coef": mu_coef.get(c, np.nan), "lumiere_refit_coef": lcoef.get(c, np.nan),
             "sign_agree_refit": bool(np.sign(mu_coef.get(c, np.nan)) == np.sign(lcoef.get(c, np.nan))),
             "lumiere_boot_sign_agree_with_mu": float((np.sign(BC[c].dropna()) == np.sign(mu_coef[c])).mean())
             if c in BC and c in mu_coef else np.nan,
             "lumiere_boot_present": float(BC[c].notna().mean()) if c in BC else 0.0}
            for c in sorted(set(mu_coef.index) | set(lcoef.index))]
    return smd, contrib, lin_shift, oe, conf_rows, stab


def stability(pop, locked, cv_fits):
    from scipy.stats import kendalltau
    ref = locked.model.coef_series()
    top5 = ref.abs().sort_values(ascending=False).index[:5]
    fits = {"cv": [m.coef_series() for m in cv_fits], "bootstrap": [b.coef_series() for b in locked.boot]}
    feat, summ = [], []
    for src, coefs in fits.items():
        C = pd.DataFrame(coefs).reindex(columns=ref.index)
        for c in ref.index:
            v = C[c].dropna()
            feat.append({"population": pop, "source": src, "column": c, "group": locked.model.group_of[c],
                         "locked_coef": ref[c], "locked_rank": int(ref.abs().rank(ascending=False)[c]),
                         "present": float(C[c].notna().mean()), "sign_agreement": float((np.sign(v) == np.sign(ref[c])).mean()),
                         "coef_median": v.median(), "coef_lo": v.quantile(0.025), "coef_hi": v.quantile(0.975)})
        taus, taus5, ov = [], [], []
        for _, row in C.iterrows():
            a = row.fillna(0).abs()
            taus.append(kendalltau(ref.abs(), a).statistic)
            taus5.append(kendalltau(ref.abs()[top5], a[top5]).statistic)
            ov.append(len(set(a.sort_values(ascending=False).index[:5]) & set(top5)) / 5)
        summ.append({"population": pop, "source": src, "n_fits": len(C), "locked_top5": "|".join(top5),
                     "kendall_tau_all_median": np.median(taus), "kendall_tau_all_iqr": f"{np.percentile(taus, 25):.2f}–{np.percentile(taus, 75):.2f}",
                     "kendall_tau_top5_median": np.nanmedian(taus5), "top5_overlap_mean": np.mean(ov),
                     "top5_overlap_all5_share": float(np.mean(np.array(ov) == 1.0)),
                     "share_features_sign_agree_ge_0.9": float(np.mean([f["sign_agreement"] >= 0.9 for f in feat if f["source"] == src])),
                     "top5_sign_agreement_min": min(f["sign_agreement"] for f in feat if f["source"] == src and f["column"] in top5)})
    return feat, summ


def group_shares(pop, fitted, X):
    c = fitted.contributions(X).abs()
    tot = c.sum(1)
    return {"population": pop, **{f"share_{g}": float((c[[k for k in fitted.columns if fitted.group_of[k] == g]].sum(1) / tot).mean())
                                  for g in GROUPS}}


# ---------------------------------------------------------------- model card, examples
def model_card(pop, locked, cohort, X):
    res = pd.read_csv(RESULTS / "c3" / pop / "results.csv")
    b = res[res.variant.isna() & res.learner.eq("ridge")].iloc[0]
    cal = pd.read_csv(RESULTS / "analyses" / "utility" / "calibration.csv")
    cb = cal[(cal.set == f"mu_{pop}") & (cal.model == "baseline_ridge")]
    y = cohort[f"label_{H}"]
    return {
        "name": f"PRISM-audit baseline ridge ({pop})", "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "git": git_state(),
        "inputs_sha256": {str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p): sha256(p)
                          for p in (MU_COHORT, MU_INDEX, FOLDS, MU_CLINICAL) if p.exists()},
        "model": {"type": "L2-penalised logistic regression (ridge), verified 120-d labels",
                  "preprocessing": "median imputation + missingness indicators, standardisation (fitted on training scans)",
                  "C": locked.model.C, "intercept": locked.model.intercept,
                  "coefficients_standardised": locked.model.coef_series().round(6).to_dict(),
                  "conformal": {"split": "patients 70/30 (seed 0)", "q": {str(a): q for a, q in locked.conformal_q.items()}},
                  "bootstrap_refits": len(locked.boot)},
        "features": [{"name": f, "group": g, "unit": FEATURES[f][0], "source": FEATURES[f][1],
                      "as_of_rule": FEATURES[f][2]} for f, g in design(cohort.head(1))[1].items()],
        "training": {"population": pop, "scans": len(cohort), "patients": int(cohort.patient_id.nunique()),
                     "verified_scans": int(y.notna().sum()), "events_120d": int((y == 1).sum()),
                     "non_events_120d": int((y == 0).sum()), "censored": int(y.isna().sum()),
                     "ood_ranges_p01_p99": locked.ranges.round(4).to_dict(orient="index")},
        "cv_performance": {"source": f"outputs/results/c3/{pop}/results.csv (row variant=None, learner=ridge); "
                                     f"outputs/results/analyses/utility/calibration.csv (set=mu_{pop}, model=baseline_ridge)",
                           "estimator": "5x5 patient-grouped CV, mean over repeats of pooled-OOF IPCW AUC(120 d)",
                           "auc_ipcw": b.auc_ipcw, "auc_ipcw_95ci": [b.auc_ipcw_lo, b.auc_ipcw_hi],
                           "brier_ipcw": b.brier_ipcw, "oe_ratio_km": b.oe_ratio, "cal_slope": b.cal_slope,
                           **({"citl": cb.citl.iat[0], "citl_95ci": [cb.citl_lo.iat[0], cb.citl_hi.iat[0]],
                               "slope_weighted": cb.slope.iat[0], "slope_95ci": [cb.slope_lo.iat[0], cb.slope_hi.iat[0]]}
                              if len(cb) else {})},
        "intended_use": ("Research decision-support prototype: estimated risk of documented progression within 120 days "
                         "of a post-diagnosis surveillance MRI in adult glioma (MU-Glioma-Post-like population), shown "
                         "with an uncertainty interval, an additive explanation and referral flags, to accompany - not "
                         "replace - radiologist and tumour-board assessment."),
        "out_of_scope": ["Diagnosis of progression vs pseudoprogression at the index scan (it predicts a future documented event).",
                         "Use without the treatment fields (RT start/end, dose, fractions, chemotherapy start, surgery day), "
                         "e.g. LUMIERE: the model cannot be applied there.",
                         "Scans inside the 12-week post-RT window without clinician review (flag (i)).",
                         "Patients with unknown IDH/MGMT or inputs outside the training range without review (flag (ii)).",
                         "Paediatric glioma, non-glioma tumours, other institutions without local recalibration/validation.",
                         "Treatment decisions; the outcome label mixes imaging and clinical progression from EMR records.",
                         "Any use as a validated clinical device (not prospectively or externally validated for this feature set)."],
        "limitations": ["Internal validation only (5x5 CV on one institution); AUC ~0.70 with wide CIs.",
                        "Signal is dominated by phase of care / treatment timing (see SHAP.md, PHASE_LADDER.md).",
                        "Acquisition metadata (field strength, scanner) not distributed with the MU tables: not audited."],
    }


def pick_examples(cohort, phase, seed=0):
    rng = np.random.default_rng(seed)
    y = cohort[f"label_{H}"]
    want = [("pre_rt", None), ("during_rt", None), ("early_post_rt", 1.0), ("early_post_rt", 0.0),
            ("later_post_rt", 1.0), ("later_post_rt", 0.0)]
    out = []
    for ph, lab in want:
        cand = np.where((phase == ph) & ((y == lab) if lab is not None else True))[0]
        if len(cand):
            out.append(int(rng.choice(cand)))
    return out


# ---------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism audit", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--n-boot", type=int, default=1000, help="patient-cluster bootstrap draws for CIs")
    ap.add_argument("--n-draw", type=int, default=1000, help="random-removal reference draws")
    ap.add_argument("--n-ref-p2", type=int, default=100, help="reference draws per P2 bootstrap draw")
    ap.add_argument("--n-fit-boot", type=int, default=200, help="bootstrap refits for intervals / stability")
    ap.add_argument("--populations", nargs="+", default=list(POPS))
    a = ap.parse_args(argv)
    t0 = time.time()
    warnings.filterwarnings("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "records").mkdir(exist_ok=True)
    tables = {k: [] for k in ("risk_coverage", "p2", "conformal", "referral", "referral_within_phase", "shortcut_arms",
                              "unknown_by_label", "subgroups", "lumiere_smd", "lumiere_contrib", "lumiere_oe",
                              "lumiere_conformal", "lumiere_stability", "stability_features", "stability_summary",
                              "group_shares", "checks")}
    md = ["# Audit record examples (out-of-fold fits, repeat 0)\n",
          "Generated by `python -m prism audit`. Risk interval: patient-cluster bootstrap of the training-fold pipeline. "
          "Conformal sets come from the training fold's split-conformal model.\n"]
    with ProcessPoolExecutor(a.workers) as ex:
        lfut = {p: ex.submit(locked_job, (p, a.n_fit_boot)) for p in a.populations}
        jobs = [(p, r, k, a.n_fit_boot) for p in a.populations for r in range(5) for k in range(5)]
        res = list(ex.map(cv_job, jobs))
        locked = {p: f.result() for p, f in lfut.items()}
    print(f"fits done {time.time() - t0:.0f}s", flush=True)

    index = load_index().set_index("scan_id")
    strata_jobs, p2_jobs = [], []
    for pop in a.populations:
        cohort, folds, X, groups, phase = context(pop)
        n = len(cohort)
        R5 = range(5)
        P, PC, LO, HI, THR = (np.zeros((5, n)) for _ in range(5))
        FOLD = np.zeros((5, n), int)
        OOD = np.zeros((5, n), bool)
        S = {al: (np.zeros((5, n), bool), np.zeros((5, n), bool)) for al in ALPHAS}
        ARM = {k: np.zeros((5, n)) for k in arms(X, groups)}
        fold_fit, ood_reasons, sum_err, qs = {}, {}, [], []
        for j in (j for j in res if j["pop"] == pop):
            r, te = j["r"], j["te"]
            P[r, te], PC[r, te], LO[r, te], HI[r, te], THR[r, te], FOLD[r, te] = j["p"], j["pc"], j["lo"], j["hi"], j["thr"], j["k"]
            OOD[r, te] = [bool(x) for x in j["ood"]]
            for al in ALPHAS:
                h0, h1 = cf.prediction_sets(j["pc"], j["q"][al])
                S[al][0][r, te], S[al][1][r, te] = h0, h1
            for k_, v in j["arms"].items():
                ARM[k_][r, te] = v
            fold_fit[(r, j["k"])] = j
            if r == 0:
                ood_reasons.update({int(i): rs for i, rs in zip(te, j["ood"])})
            sum_err.append(j["sum_err"])
            qs.append({"population": pop, "repeat": r, "fold": j["k"], "C": j["C"], "conf_threshold_70": j["thr"],
                       "n_cal_patients": j["n_cal_patients"], "n_cal_scans": j["n_cal_scans"],
                       **{f"q_alpha_{al}": j["q"][al] for al in ALPHAS}})
        pd.DataFrame(qs).to_csv(OUT / f"fold_params_{pop}.csv", index=False)
        # reproduce the C3 baseline exactly
        ref = pd.read_csv(RESULTS / "c3" / pop / "oof_repeats.csv.gz").set_index("scan_id").loc[cohort.scan_id]
        ref = np.array([ref[f"None|none|none|none|ridge#r{r}"].to_numpy() for r in R5])
        max_dev = float(np.abs(ref - P).max())
        tables["checks"].append({"population": pop, "max_abs_dev_vs_c3_oof": max_dev,
                                 "max_abs_contribution_sum_error": float(max(sum_err))})
        if max_dev > 1e-9:
            sys.exit(f"{pop}: CV predictions differ from the C3 baseline by {max_dev:.2e}; stopping")
        y = cohort[f"label_{H}"].to_numpy(float)
        conf = np.maximum(P, 1 - P)
        pd.concat([pd.DataFrame({"scan_id": cohort.scan_id, "patient_id": cohort.patient_id, "phase": phase,
                                 "label_120": y, "repeat": r, "fold": FOLD[r], "risk": P[r], "risk_lo": LO[r],
                                 "risk_hi": HI[r], "risk_conformal_model": PC[r], "confidence": conf[r],
                                 "conf_threshold_70": THR[r], "retained_70": conf[r] >= THR[r], "ood": OOD[r],
                                 **{f"set_alpha_{al}": cf.describe(S[al][0][r], S[al][1][r]) for al in ALPHAS}})
                   for r in R5]).to_csv(OUT / f"cv_predictions_{pop}.csv.gz", index=False)

        # 3a risk-coverage
        tables["risk_coverage"] += [{"population": pop, **row} for row in
                                    risk_coverage(cohort, P, conf, phase, a.n_draw, name="max_prob")]
        tables["risk_coverage"] += [{"population": pop, **row} for row in
                                    risk_coverage(cohort, P, -(HI - LO), phase, a.n_draw, name="bootstrap_width")]
        # 3b conformal
        tables["conformal"] += coverage_table(pop, cohort, S, phase, a.n_boot)
        ctx = ipcw_context(cohort, H)
        for al in ALPHAS:
            single = S[al][0] ^ S[al][1]
            tables["conformal"].append({
                "population": pop, "alpha": al, "phase": "singleton_performance",
                "auc_singletons_displayed_risk": np.nanmean([auc_brier(ctx, P[r], single[r])[0] for r in R5]),
                "brier_singletons_displayed_risk": np.nanmean([auc_brier(ctx, P[r], single[r])[1] for r in R5]),
                "auc_singletons_conformal_model": np.nanmean([auc_brier(ctx, PC[r], single[r])[0] for r in R5]),
                "auc_nonsingletons_displayed_risk": np.nanmean([auc_brier(ctx, P[r], ~single[r])[0] for r in R5]),
                "auc_conformal_model_all": np.nanmean([auc_brier(ctx, PC[r])[0] for r in R5]),
                "auc_displayed_all": np.nanmean([auc_brier(ctx, P[r])[0] for r in R5]),
                "singleton_rate_all_scans": single.mean(),
                "singleton_accuracy_verified": float(np.mean([np.where(y == 1, S[al][1][r], S[al][0][r])[single[r] & ~np.isnan(y)].mean()
                                                              for r in R5]))})
        # 3c P2
        R = conf >= THR
        ret_auc = np.nanmean([auc_brier(ctx, P[r], R[r])[0] for r in R5])
        rng = np.random.default_rng(1)
        comp = np.array([np.nanmean([auc_brier(ctx, P[r], matched_draw(rng, R[r], phase))[0] for r in R5])
                         for _ in range(a.n_draw)])
        rand = np.array([np.nanmean([auc_brier(ctx, P[r], random_draw(rng, int(R[r].sum()), n))[0] for r in R5])
                         for _ in range(a.n_draw)])
        tables["p2"].append({"population": pop, "realised_coverage": R.mean(),
                             "realised_coverage_by_repeat": "|".join(f"{x:.3f}" for x in R.mean(1)),
                             "auc_all": np.nanmean([auc_brier(ctx, P[r])[0] for r in R5]),
                             "auc_retained": ret_auc, "auc_composition_matched": comp.mean(),
                             "auc_random_removal": rand.mean(), "p2": ret_auc - comp.mean(),
                             "gain_vs_random": ret_auc - rand.mean(),
                             **{f"retained_share_{ph}": float(R[:, phase == ph].mean()) for ph in PHASES}})
        seeds = np.arange(a.n_boot) + 10_000
        p2_jobs += [(pop, P, R, phase, ch, a.n_ref_p2) for ch in np.array_split(seeds, a.workers)]
        # 3d referral rules
        early = np.broadcast_to(phase == "early_post_rt", P.shape)
        unc = S[0.2][0] & S[0.2][1]
        rules = {"i_early_post_rt": early, "ii_ood": OOD, "iii_uncertain": unc, "i_or_ii": early | OOD,
                 "any_i_ii_iii": early | OOD | unc}
        rr, wp = referral_tables(pop, cohort, P, rules, phase, a.n_draw)
        tables["referral"] += rr
        tables["referral_within_phase"] += wp
        # 4a/4b shortcut arms
        ev = evaluate_repeated(cohort, {"baseline": P, **ARM}, H, reference="baseline", n_boot=a.n_boot)
        keep_cols = ["auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "d_auc_ipcw_vs_baseline", "d_auc_ipcw_lo",
                     "d_auc_ipcw_hi", "brier_ipcw", "oe_ratio", "cal_slope"]
        tables["shortcut_arms"] += [{"population": pop, "arm": k_, **row[[c for c in keep_cols if c in row]].to_dict()}
                                    for k_, row in ev.iterrows()]
        tables["unknown_by_label"] += unknown_by_label(pop, cohort)
        # 4c subgroups
        for name, lv in strata(cohort, phase).items():
            for level, mask in lv.items():
                if mask.sum():
                    strata_jobs.append((pop, name, level, mask, P, a.n_boot, 0))
        # 5 stability + group shares
        cv_fits = [fold_fit[(r, k)]["fitted"] for r in R5 for k in range(5)]
        f_, s_ = stability(pop, locked[pop], cv_fits)
        tables["stability_features"] += f_
        tables["stability_summary"] += s_
        tables["group_shares"].append({**group_shares(pop, locked[pop].model, X), "model": "locked"})
        # 1 locked artifact + model card
        joblib.dump(locked[pop], OUT / f"locked_{pop}.joblib", compress=3)
        (OUT / f"model_card_{pop}.json").write_text(json.dumps(model_card(pop, locked[pop], cohort, X), indent=1,
                                                              default=float))
        # 2 audit records (repeat 0 OOF fits)
        if pop == "grade4":
            md.append(f"\n## {pop}\n")
            for i in pick_examples(cohort, phase):
                j = fold_fit[(0, int(FOLD[0, i]))]
                rec = build(cohort.iloc[i], X.iloc[i], index.loc[cohort.scan_id.iat[i]], j["fitted"], phase[i],
                            (LO[0, i], HI[0, i]), ood_reasons[i],
                            {al: cf.describe(S[al][0][0, [i]], S[al][1][0, [i]])[0] for al in ALPHAS},
                            {"source": "out-of-fold fit, repeat 0, fold %d (patient not in training)" % j["k"],
                             "C": j["C"], "population": pop},
                            {"label_120": None if np.isnan(y[i]) else int(y[i]), "event": bool(cohort.event.iat[i]),
                             "time_to_event": float(cohort.time_to_event.iat[i])})
                (OUT / "records" / f"{cohort.scan_id.iat[i]}.json").write_text(json.dumps(rec, indent=1, default=float))
                md.append(render_md(rec))
        # all-scan as-of check (repeat-0 fold models; inputs only)
        from prism.audit.provenance import as_of
        bad = [(cohort.scan_id.iat[i], f) for i in range(n) for f in X.columns
               if not as_of(f, X[f].iat[i], float(cohort.days_from_diagnosis_to_mri.iat[i]),
                            index.loc[cohort.scan_id.iat[i]])["known_by_scan"]]
        tables["checks"][-1]["inputs_not_known_by_scan"] = len(bad)
        tables["checks"][-1]["scans_with_inputs_not_known_by_scan"] = len({s_ for s_, _ in bad})
        tables["checks"][-1]["features_not_known_by_scan"] = "|".join(sorted({f_ for _, f_ in bad}))
        tables["checks"][-1]["inputs_not_known_examples"] = "|".join(f"{s}:{f}" for s, f in bad[:5])
        print(f"{pop} analyses done {time.time() - t0:.0f}s", flush=True)

    with ProcessPoolExecutor(a.workers) as ex:
        sfut = [ex.submit(stratum_job, j) for j in strata_jobs]
        pfut = [(j[0], ex.submit(p2_boot_job, j)) for j in p2_jobs]
        tables["subgroups"] = [f.result() for f in sfut]
        p2b = {}
        for pop, f in pfut:
            p2b.setdefault(pop, []).extend(f.result())
    for row in tables["p2"]:
        b = np.array(p2b[row["population"]])
        d = b[:, 0] - b[:, 1]
        row.update({"p2_lo": np.percentile(d, 2.5), "p2_hi": np.percentile(d, 97.5), "p2_boot_mean": d.mean(),
                    "auc_retained_lo": np.percentile(b[:, 0], 2.5), "auc_retained_hi": np.percentile(b[:, 0], 97.5),
                    "n_boot_ok": len(b), "p2_ci_excludes_0": bool(np.percentile(d, 2.5) > 0 or np.percentile(d, 97.5) < 0)})

    # 4d LUMIERE transport + shared-model stability
    for pop in a.populations:
        smd, contrib, shift, oe, crow, stab = lumiere_transport(pop, a.n_fit_boot)
        tables["lumiere_smd"] += smd
        tables["lumiere_contrib"] += contrib.assign(total_linear_shift=shift).to_dict("records")
        tables["lumiere_oe"] += oe
        tables["lumiere_conformal"] += crow
        tables["lumiere_stability"] += stab

    for k_, rows in tables.items():
        pd.DataFrame(rows).to_csv(OUT / f"{k_}.csv", index=False)
    (OUT / "records.md").write_text("\n".join(md))
    plot(pd.DataFrame(tables["risk_coverage"]), OUT / "risk_coverage.png")
    (OUT / "run_info.json").write_text(json.dumps({"argv": vars(a), "seconds": round(time.time() - t0)}, indent=1))
    manifest(a)
    print(pd.DataFrame(tables["p2"]).round(3).T.to_string())
    print(pd.DataFrame(tables["conformal"]).query("alpha == 0.2")[["population", "phase", "coverage", "coverage_lo",
                                                                   "coverage_hi"]].round(3).to_string(index=False))
    print(f"total {time.time() - t0:.0f}s")


def plot(rc, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pops = list(dict.fromkeys(rc.population))
    fig, axes = plt.subplots(2, len(pops), figsize=(5.5 * len(pops), 7), squeeze=False)
    for j, pop in enumerate(pops):
        s = rc[(rc.population == pop) & (rc.confidence == "max_prob")]
        for i, (m, lab) in enumerate((("auc", "IPCW AUC(120 d)"), ("brier", "IPCW Brier(120 d)"))):
            ax = axes[i, j]
            ax.plot(s.coverage, s[f"{m}_ipcw"], "o-", color="#1f4e79", ms=3, label="abstain least confident first")
            ax.plot(s.coverage, s[f"{m}_random"], "--", color="#888", label="random removal (mean)")
            ax.plot(s.coverage, s[f"{m}_composition"], ":", color="#c0504d", lw=2, label="phase-composition-matched (mean)")
            if m == "auc":
                ax.fill_between(s.coverage, s.auc_composition_lo, s.auc_composition_hi, color="#c0504d", alpha=0.12)
            ax.invert_xaxis()
            ax.set_xlabel("coverage (share of scans with a prediction)")
            ax.set_ylabel(lab)
            ax.set_title(pop, fontsize=10)
            if i == 0 and j == 0:
                ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    fig.savefig(str(path).rsplit(".", 1)[0] + ".pdf")
    plt.close(fig)


def manifest(a):
    outs = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "MANIFEST.json")
    ins = [MU_COHORT, MU_INDEX, FOLDS, MU_CLINICAL, LUMIERE_COHORT,
           RESULTS / "c3" / "grade4" / "results.csv", RESULTS / "c3" / "all_glioma" / "results.csv",
           RESULTS / "c3" / "grade4" / "oof_repeats.csv.gz", RESULTS / "c3" / "all_glioma" / "oof_repeats.csv.gz",
           RESULTS / "analyses" / "utility" / "calibration.csv"]
    rel = lambda p: str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p)
    (OUT / "MANIFEST.json").write_text(json.dumps({
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "git": git_state(), "versions": package_versions(),
        "command": " ".join(["python", "-m", "prism", "audit"] + sys.argv[2:]) if sys.argv[1:2] == ["audit"]
        else " ".join(sys.argv), "argv": vars(a),
        "rerun": "scripts/11_audit_system.sh  (= uv run --frozen --no-sync python -m prism audit --workers 24)",
        "code_sha256": {rel(p): sha256(p) for p in sorted((REPO / "prism" / "audit").glob("*.py"))
                        + [REPO / "prism" / "analyses" / "audit_system.py"]},
        "inputs_sha256": {rel(p): sha256(p) for p in ins if p.exists()},
        "outputs_sha256": {rel(p): sha256(p) for p in outs}}, indent=1))


if __name__ == "__main__":
    main()
