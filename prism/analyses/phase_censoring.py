"""Phase of care vs censoring: is the phase-of-care finding partly a loss-to-follow-up artefact, and what fixes it?

ANALYSIS PLAN (pre-specified in STEP 1, before any model of this module was fitted or scored on real labels; the same
text is in docs/results/PHASE_CENSORING.md, section "Analysis plan (pre-specified)", and is snapshotted to
outputs/results/analyses/phase_censoring/PLAN_snapshot.md before the run. Anything added after results: EXPLORATORY.)

Why. Of the 39 censored grade-4 scans, 38 are pre-RT, all from patients whose treatment record is blank (RT and chemo
fields empty: "RT never documented"); most were censored on the scan day. The headline IPCW AUC uses one marginal
Kaplan-Meier censoring curve, which assumes censoring does not depend on phase. Step 1 also found that the core model
can see the future documentation status: `early_post_rt` is NaN (-> a missingness indicator) exactly when the RT end
date is never documented, so at a pre-RT scan it separates "RT pending" from "RT never documented" with information
from after the scan. This is the Table 1 "unknown 65" (grade 4): 63 pre-RT scans with no RT documented + 2 during-RT
scans with RT documented but no end date (all gliomas: 94 = 92 + 2).

1. Descriptives (no model): phase (4 and 5 levels) x 120-d status (event / non-event / censored) per population, with
   censored-on-scan-day (follow-up <= 1 d) and death-without-progression counts; never-documented vs documented RT
   patients (age, sex, grade, IDH, MGMT, chemo field, hospice, scans per patient, scan day, follow-up, deaths);
   the Table 1 "unknown" resolution; molecular look-ahead scans (scan before the diagnosis date).
2. Five-level phase (an ANALYSIS STRATIFIER, never a model input: "never documented" is only known afterwards):
   pre_rt_pending (RT documented, starts after the scan) | pre_rt_never_documented | during_rt | early_post_rt |
   later_post_rt (phase_ladder.phase_label otherwise unchanged).
3. Censoring weights (schemes), each giving case set, control set and weights; AUC = weighted concordance over
   case x control pairs, mean over the 5 repeats of each repeat's pooled OOF AUC (as metrics.evaluate_repeated):
     marginal_km     one KM censoring curve (reproduces the headline auc_ipcw; asserted to 1e-9)
     phase5_km       KM censoring curve per 5-level phase (cases 1/G_s(T_i), controls 1/G_s(H))  <- PRIMARY alternative
     phase4_km       KM per 4-level phase (secondary)
     logistic_ipw    verified scans weighted 1/P(verified | phase5, age, sex, log1p days from diagnosis[, grade 4 in
                     all gliomas]), logistic C=1, P floored at G_FLOOR = 0.1 (secondary)
     verified        unweighted verified scans (reference)
     deaths_as_controls  death without progression before H counted as a non-event (competing-risk view), else verified
     bound_cens_events / bound_cens_controls  every censored scan set to event / non-event (extreme bounds)
   Every scheme re-estimates its weights inside each patient-cluster bootstrap draw (1000 draws, paired across arms
   and schemes). Applied to the core model (R3) and the phase ladder R0 clinical | R1 +timing | R2 +phase | R3 core.
4. Cohorts (refit and evaluated inside the cohort, patients keep their shared fold, censoring re-estimated):
     full        all scans
     rt_pathway  patients whose RT is documented (excludes the never-documented patients; needs a treatment-plan
                 field at deployment, so it is an intended-use statement, not an as-of rule)
     rt_started  scans with RT started by the scan day (deployable as-of rule; = during + post RT)
   plus the full-cohort OOF predictions evaluated on each subset. Within-phase AUCs (4- and 5-level phase) for core,
   R0 (clinical only) and C2 under marginal_km (cohort weights) and phase5_km (= censoring re-estimated within the
   phase); a phase-stratified AUC that pools only within-phase case-control pairs. Within-phase AUCs are shown with
   CIs only if the stratum has >= 10 verified events and >= 10 verified non-events, otherwise descriptive.
5. Corrected core models (same pipeline: BASE_PRE + verified ridge, fit_pipeline, shared folds, seed = repeat):
     core_no_unknown  idh_unknown / mgmt_unknown dropped (reproduces audit shortcut arm 0.676; asserted 1e-6)
     C1  core_no_unknown + IDH/MGMT masked at scans before the diagnosis date (idh_mutant = mgmt_methylated = 0, the
         same coding unknown markers get once the indicators are dropped; the MGMT x early-post-RT term recomputed)
     C1_mean  as C1 but unknown/masked IDH, MGMT filled with the training-fold mean of the known values (sensitivity)
     C2  C1 + as-of early_post_rt: 1 iff RT completed by the scan and <= 84 d since RT end, else 0 (no missingness
         indicator, so no look-ahead to future RT documentation)  <- CANDIDATE CORRECTED HEADLINE MODEL
   C2 is preferred over C1 because it removes all three look-aheads found so far (unknown-marker shortcut, molecular
   look-ahead, RT-documentation look-ahead); C1 is reported as the coordinator-specified variant. Reported: IPCW AUC
   (all schemes), Brier, calibration slope, O/E, CITL, ΔAUC vs core (paired bootstrap). LUMIERE transport: the
   existing shared-feature model (clinical + log days since surgery + early_post_rt + volumes; LUMIERE has no RT dates
   so the core model itself cannot be applied) refit with the same corrections (shared_no_unknown, shared_C1,
   shared_C2: MU early_post_rt NaN -> as-of 0); AUC, O/E, slope on LUMIERE with patient-bootstrap CIs.
6. Mitigations, quantified on the core model and C2: (a) intended-use restriction to rt_pathway or rt_started
   (scans/patients/events/censored removed; AUC inside scope); (b) referral flags in the audit record,
   "pre-RT as of scan" (deployable) and "RT never documented" (needs a plan field), via audit_system.referral_tables
   (AUC retained / referred, gain vs random and phase-composition-matched removal); (c) within-phase reporting
   (item 4 table).

PRIMARY estimands (grade 4; all gliomas secondary):
  P1 (censoring): R2 - R0 ΔAUC under phase5_km, and its change vs marginal_km (diff of diffs, paired bootstrap).
     Co-primary: R2 - R0 ΔAUC refit in rt_pathway (marginal KM inside the cohort).
     Rule: the phase-of-care finding (R2 - R0 = +0.080 marginal) is "robust" if both estimates are >= +0.040 (half),
     "partly censoring-dependent" if exactly one is, "not supported once censoring is handled" if neither is.
     The bounds (bound_cens_events/controls) are reported as the range under arbitrary informative censoring.
  P2 (corrected headline): C2 IPCW AUC (marginal_km) with CI; ΔAUC C2 - core; calibration slope, O/E.
Everything else is secondary/descriptive, no multiplicity correction. Minimal detectable effects (Hanley-McNeil, 80%
power, two-sided 0.05, ignoring patient clustering, so optimistic) are tabulated per stratum in mde.csv, and for the
paired full-cohort contrasts from the existing bootstrap CI widths (phase_ladder rungs, audit shortcut arms).

    python -m prism phasecens [--workers 40] [--n-boot 1000] [--n-draw 1000] [--populations grade4 all_glioma]
                              [--descriptives-only] [--shuffle-labels SEED] [--selftest]
    -> $PRISM_OUTPUTS/results/analyses/phase_censoring/  (…_shuffled<SEED>/ for --shuffle-labels)
       descriptives_*.csv, mde.csv, schemes.csv, ladder_schemes.csv, within_phase.csv, corrected.csv, cohorts.csv,
       mitigations.csv, referral.csv, lumiere.csv, oof_<pop>_<cohort>.csv.gz, checks.csv, run_info.json
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sksurv.nonparametric import CensoringDistributionEstimator
from threadpoolctl import threadpool_limits

from prism.analyses.phase_ladder import phase, phase_label
from prism.audit.model import design, fit_pipeline
from prism.audit.provenance import git_state
from prism.config import REPO, RESULTS
from prism.data.mu import load_cohort, load_index
from prism.experiments import c3_radiomics as c3
from prism.features.tabular import clinical, timing
from prism.models.folds import load_folds
from prism.models.formulations import G_FLOOR, _observed_time
from prism.models.metrics import counted_warnings, evaluate_repeated, fast_auc_brier, ipcw_context

H = c3.H
OUT = RESULTS / "analyses" / "phase_censoring"
POPS = ("grade4", "all_glioma")
PHASE4 = ("pre_rt", "during_rt", "early_post_rt", "later_post_rt")
PHASE5 = ("pre_rt_pending", "pre_rt_never_documented", "during_rt", "early_post_rt", "later_post_rt")
UNKNOWN = ["idh_unknown", "mgmt_unknown"]
OUTCOME_COLS = ["event", "time_to_event", f"label_{H}", f"naive_label_{H}", f"label_{H}_composite",
                "death_without_progression", "follow_up_days", "status_known_indefinitely", "death_day"]
COHORTS = ("full", "rt_pathway", "rt_started")
ARMS = {"full": ("R0", "R1", "R2", "R3", "core_no_unknown", "C1", "C1_mean", "C2"),
        "rt_pathway": ("R0", "R2", "R3", "C2"), "rt_started": ("R0", "R2", "R3", "C2")}
SCHEMES = ("marginal_km", "phase5_km", "phase4_km", "logistic_ipw", "verified", "deaths_as_controls",
           "bound_cens_events", "bound_cens_controls")
MIN_STRATUM = 10  # verified events and non-events needed for a within-stratum AUC with CI


# ---------------------------------------------------------------- data
def rt_documented(cohort: pd.DataFrame, index: pd.DataFrame | None = None) -> np.ndarray:
    """RT documented at any time (the treatment() definition of RT given); patient-level, partly future knowledge."""
    d = (load_index() if index is None else index).set_index("scan_id").reindex(cohort.scan_id)
    return d["clinical_radiation_therapy"].astype(str).str.strip().isin(["Yes", "Proton Therapy"]).to_numpy()


def phase5_label(cohort: pd.DataFrame, index: pd.DataFrame | None = None) -> np.ndarray:
    """phase_label with pre-RT split by whether RT is ever documented (stratifier only, never a model input)."""
    p4 = phase_label(cohort)
    doc = rt_documented(cohort, index)
    return np.where(p4 == "pre_rt", np.where(doc, "pre_rt_pending", "pre_rt_never_documented"), p4)


def pre_diagnosis(cohort: pd.DataFrame) -> np.ndarray:
    """Scans taken before the diagnosis date: molecular pathology (IDH, MGMT) cannot be known yet."""
    if "days_from_diagnosis_to_mri" not in cohort:  # LUMIERE: scan days are relative to surgery, none before it
        return np.zeros(len(cohort), bool)
    return (pd.to_numeric(cohort["days_from_diagnosis_to_mri"], errors="coerce") < 0).to_numpy()


def shuffle_outcomes(cohort: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Pipeline test: permute the whole outcome tuple across scans (features, folds, patients unchanged)."""
    c = cohort.copy()
    perm = np.random.default_rng(seed).permutation(len(c))
    cols = [k for k in OUTCOME_COLS if k in c]
    for k in cols:
        c[k] = c[k].to_numpy()[perm]
    return c


@lru_cache(maxsize=8)
def load(pop: str, shuffle: int | None = None):
    cohort = load_cohort(pop)
    if shuffle is not None:
        cohort = shuffle_outcomes(cohort, shuffle)
    index = load_index()
    return cohort, load_folds(), index, phase_label(cohort), phase5_label(cohort, index)


def cohort_mask(name: str, cohort: pd.DataFrame, index: pd.DataFrame) -> np.ndarray:
    if name == "full":
        return np.ones(len(cohort), bool)
    if name == "rt_pathway":
        return rt_documented(cohort, index)
    if name == "rt_started":
        return phase_label(cohort) != "pre_rt"
    raise ValueError(name)


# ---------------------------------------------------------------- design matrices for the arms
def masked_molecular(cohort: pd.DataFrame, fill=0.0) -> pd.DataFrame:
    """idh_mutant / mgmt_methylated with unknown markers and pre-diagnosis scans set to `fill` (0 or NaN)."""
    blind = pre_diagnosis(cohort)
    out = {}
    for col, mk, pos in (("idh_mutant", "idh", "mutant"), ("mgmt_methylated", "mgmt", "methylated")):
        v = cohort[mk].eq(pos).astype(float).to_numpy()
        v[cohort[mk].eq("unknown").to_numpy() | blind] = fill
        out[col] = v
    return pd.DataFrame(out, index=cohort.index)


def asof_early_post_rt(cohort: pd.DataFrame) -> np.ndarray:
    """1 iff RT completed by the scan and <= 84 d since its end, else 0 (never NaN: no look-ahead)."""
    p = phase(cohort)
    return p.phase_early_post_rt.to_numpy(float)


def arm_design(arm: str, cohort: pd.DataFrame, index: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Raw design matrix + feature -> group map for an arm. C1_mean leaves masked markers NaN (filled in-fold)."""
    X, groups = design(cohort, index)
    cl, tm, ph = clinical(cohort), timing(cohort), phase(cohort)
    g = lambda df, name: {c: name for c in df.columns}
    if arm == "R0":
        return cl, g(cl, "clinical")
    if arm == "R1":
        return pd.concat([cl, tm], axis=1), {**g(cl, "clinical"), **g(tm, "timing")}
    if arm == "R2":
        return pd.concat([cl, ph], axis=1), {**g(cl, "clinical"), **g(ph, "phase")}
    if arm == "R3":
        return X, groups
    X = X.drop(columns=UNKNOWN)
    groups = {c: v for c, v in groups.items() if c not in UNKNOWN}
    if arm == "core_no_unknown":
        return X, groups
    m = masked_molecular(cohort, np.nan if arm == "C1_mean" else 0.0)
    X[["idh_mutant", "mgmt_methylated"]] = m[["idh_mutant", "mgmt_methylated"]].to_numpy()
    early = X["early_post_rt"].to_numpy(float)
    if arm == "C2":
        early = asof_early_post_rt(cohort)
        X["early_post_rt"] = early
    X["early_post_rt_x_mgmt_methylated"] = early * np.nan_to_num(m["mgmt_methylated"].to_numpy(), nan=0.0)
    if arm in ("C1", "C1_mean", "C2"):
        return X, groups
    raise ValueError(arm)


def fill_in_fold(X: pd.DataFrame, tr: np.ndarray, cols=("idh_mutant", "mgmt_methylated")) -> pd.DataFrame:
    """Training-fold mean of the known values (no missingness indicator), for C1_mean."""
    X = X.copy()
    for c in cols:
        X[c] = X[c].fillna(float(np.nanmean(X[c].to_numpy()[tr])))
    return X


@lru_cache(maxsize=64)
def subset_context(pop, coh, arm, shuffle):
    cohort, folds, index, p4, p5 = load(pop, shuffle)
    keep = cohort_mask(coh, cohort, index)
    sub = cohort[keep].reset_index(drop=True)
    X, groups = arm_design(arm, cohort, index)
    return sub, folds, X[keep].reset_index(drop=True), groups


@counted_warnings
def cv_job(job):
    """One (population, cohort, arm, repeat, fold) fit; returns test indices (within the cohort) and risks."""
    pop, coh, arm, r, k, shuffle = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    sub, folds, X, groups = subset_context(pop, coh, arm, shuffle)
    f = c3._fold_ids(sub, folds, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    Xf = fill_in_fold(X, tr) if arm == "C1_mean" else X
    m = fit_pipeline(Xf, sub, tr, groups, seed=r)
    return job, te, m.predict(Xf.iloc[te])


# ---------------------------------------------------------------- weighting schemes
def _cde_weights(t, e, rows, H_=H):
    """sksurv KM censoring estimate on `rows`: G(T_i) for rows, G(H); times clipped to the stratum's last time."""
    s = np.array(list(zip(e[rows], t[rows])), dtype=[("event", bool), ("time", float)])
    cens = CensoringDistributionEstimator().fit(s)
    tmax = t[rows].max()
    return cens.predict_proba(np.minimum(t[rows], tmax)), float(cens.predict_proba(np.array([min(H_, tmax)]))[0])


def km_scheme(d: pd.DataFrame, strata: np.ndarray | None = None):
    """(case, ctrl, w): IPCW with KM censoring curves per stratum (one stratum = the sksurv / headline estimator)."""
    t = _observed_time(d, H).astype(float)
    e = d["event"].to_numpy(bool)
    case, ctrl = e & (t <= H), t > H
    w = np.zeros(len(d))
    strata = np.zeros(len(d)) if strata is None else np.asarray(strata)
    for s in np.unique(strata):
        rows = np.where(strata == s)[0]
        g_t, g_h = _cde_weights(t, e, rows)
        c, k = case[rows], ctrl[rows]
        w[rows[c]] = 1.0 / np.where(g_t[c] > 0, g_t[c], G_FLOOR)  # G = 0 at a case time: floor (never in MU)
        w[rows[k]] = 1.0 / (g_h if g_h > 0 else G_FLOOR)
    return case, ctrl, w


def verification_covariates(d: pd.DataFrame, p5: np.ndarray) -> np.ndarray:
    Z = pd.get_dummies(pd.Categorical(p5, categories=PHASE5)).iloc[:, 1:].to_numpy(float)
    extra = [d["age"].to_numpy(float), d["male"].to_numpy(float),
             np.log1p(np.clip(pd.to_numeric(d["days_from_diagnosis_to_mri"]).to_numpy(float), 0, None))]
    if d["grade4"].nunique() > 1:
        extra.append(d["grade4"].to_numpy(float))
    return np.column_stack([Z] + extra)


def logistic_scheme(d: pd.DataFrame, p5: np.ndarray):
    y = d[f"label_{H}"].to_numpy(float)
    v = ~np.isnan(y)
    Z = StandardScaler().fit_transform(verification_covariates(d, p5))
    pi = LogisticRegression(C=1.0, max_iter=2000).fit(Z, v.astype(int)).predict_proba(Z)[:, 1] if 0 < v.mean() < 1 \
        else np.ones(len(d))
    w = np.where(v, 1.0 / np.maximum(pi, G_FLOOR), 0.0)
    return v & (y == 1), v & (y == 0), w


def label_scheme(d: pd.DataFrame, fill_censored=None, deaths_as_controls=False):
    y = d[f"label_{H}"].to_numpy(float).copy()
    cens = np.isnan(y)
    if deaths_as_controls:
        t_death = pd.to_numeric(d["death_day"], errors="coerce").to_numpy(float) - \
            pd.to_numeric(d["days_from_diagnosis_to_mri"], errors="coerce").to_numpy(float)
        y[cens & d["death_without_progression"].to_numpy(bool) & (t_death <= H)] = 0.0
    if fill_censored is not None:
        y[cens] = fill_censored
    return y == 1, y == 0, np.ones(len(d))


def scheme(name: str, d: pd.DataFrame, p4: np.ndarray, p5: np.ndarray):
    if name == "marginal_km":
        return km_scheme(d)
    if name == "phase5_km":
        return km_scheme(d, p5)
    if name == "phase4_km":
        return km_scheme(d, p4)
    if name == "logistic_ipw":
        return logistic_scheme(d, p5)
    if name == "verified":
        return label_scheme(d)
    if name == "deaths_as_controls":
        return label_scheme(d, deaths_as_controls=True)
    if name == "bound_cens_events":
        return label_scheme(d, fill_censored=1.0)
    if name == "bound_cens_controls":
        return label_scheme(d, fill_censored=0.0)
    raise ValueError(name)


def wauc(P: np.ndarray, case, ctrl, w, subset=None, strata=None, tol: float = 1e-8) -> np.ndarray:
    """Weighted concordance over case x control pairs (ties 1/2) for each row of P; with `strata`, only pairs within
    the same stratum count (phase-stratified AUC). Equals fast_auc_brier when control weights are constant."""
    P = np.atleast_2d(P)
    if subset is not None:
        case, ctrl = case & subset, ctrl & subset
    strata = np.zeros(P.shape[1]) if strata is None else np.asarray(strata)
    num, den = np.zeros(len(P)), 0.0
    for s in np.unique(strata[case | ctrl]):
        c, k = case & (strata == s), ctrl & (strata == s)
        if not (c.any() and k.any()):
            continue
        wc, wk = w[c], w[k]
        den += wc.sum() * wk.sum()
        for i, p in enumerate(P):
            o = np.argsort(p[k], kind="stable")
            pk, cw = p[k][o], np.concatenate([[0.0], np.cumsum(wk[o])])
            lo = np.searchsorted(pk, p[c] - tol, side="left")
            hi = np.searchsorted(pk, p[c] + tol, side="right")
            num[i] += float((wc * (cw[lo] + 0.5 * (cw[hi] - cw[lo]))).sum())
    return num / den if den > 0 else np.full(len(P), np.nan)


# ---------------------------------------------------------------- evaluation
def arm_scheme_matrix(d, oofs: dict, p4, p5, schemes=SCHEMES, subsets: dict | None = None, pair_strata=None):
    """Mean-over-repeats AUC -> {(scheme, arm, subset): value}; subset None = all scans of d."""
    out = {}
    subsets = {"all": None, **(subsets or {})}
    for sc in schemes:
        try:
            case, ctrl, w = scheme(sc, d, p4, p5)
        except Exception:  # noqa: BLE001 (degenerate bootstrap resample)
            continue
        for a, P in oofs.items():
            for sn, m in subsets.items():
                out[(sc, a, sn)] = float(np.nanmean(wauc(P, case, ctrl, w, subset=m)))
            if pair_strata is not None:
                out[(sc, a, "phase_stratified")] = float(np.nanmean(wauc(P, case, ctrl, w, strata=pair_strata)))
    return out


def boot_chunk(job):
    d, oofs, p4, p5, schemes, subsets, pair_strata, seeds = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    pid = d.patient_id.to_numpy()
    groups = {p: np.where(pid == p)[0] for p in np.unique(pid)}
    pats = np.array(list(groups))
    res = []
    for s in seeds:
        rng = np.random.default_rng(int(s))
        idx = np.concatenate([groups[p] for p in rng.choice(pats, len(pats))])
        db = d.iloc[idx].reset_index(drop=True)
        if db[f"label_{H}"].nunique(dropna=True) < 2:
            continue
        res.append(arm_scheme_matrix(db, {a: P[:, idx] for a, P in oofs.items()}, p4[idx], p5[idx], schemes,
                                     {k: m[idx] for k, m in (subsets or {}).items()},
                                     None if pair_strata is None else pair_strata[idx]))
    return res


def bootstrap(d, oofs, p4, p5, n_boot, workers, schemes=SCHEMES, subsets=None, pair_strata=None, seed=0):
    point = arm_scheme_matrix(d, oofs, p4, p5, schemes, subsets, pair_strata)
    seeds = np.arange(n_boot) + 1_000_000 * (seed + 1)
    chunks = [c for c in np.array_split(seeds, max(1, min(workers, n_boot))) if len(c)]
    jobs = [(d, oofs, p4, p5, schemes, subsets, pair_strata, c) for c in chunks]
    if workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            draws = [r for chunk in ex.map(boot_chunk, jobs) for r in chunk]
    else:
        draws = [r for j in jobs for r in boot_chunk(j)]
    keys = set().union(*[r.keys() for r in draws]) if draws else set()
    return point, {k: np.array([r.get(k, np.nan) for r in draws]) for k in keys}


def ci(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return (np.percentile(x, 2.5), np.percentile(x, 97.5)) if len(x) else (np.nan, np.nan)


def contrast(point, draws, a, b):
    """Point a - b and paired percentile CI (keys of arm_scheme_matrix)."""
    if a not in point or b not in point or a not in draws or b not in draws:
        return {}
    x = draws[a] - draws[b]
    x = x[np.isfinite(x)]
    lo, hi = ci(x)
    return {"diff": point[a] - point[b], "diff_lo": lo, "diff_hi": hi, "p_le0": float(np.mean(x <= 0)) if len(x) else np.nan}


def counts(d, mask=None):
    m = np.ones(len(d), bool) if mask is None else mask
    y = d[f"label_{H}"].to_numpy(float)[m]
    return {"n_scans": int(m.sum()), "n_patients": int(d.patient_id[m].nunique()), "events": int((y == 1).sum()),
            "non_events": int((y == 0).sum()), "censored": int(np.isnan(y).sum())}


# ---------------------------------------------------------------- descriptives (no model)
def descriptives(pop: str, shuffle=None) -> dict[str, pd.DataFrame]:
    cohort, _, index, p4, p5 = load(pop, shuffle)
    d = index.set_index("scan_id").reindex(cohort.scan_id)
    y = cohort[f"label_{H}"].map({1.0: "event", 0.0: "non_event"}).fillna("censored").to_numpy()
    fu = cohort.follow_up_days.to_numpy(float)
    rows = []
    for name, lab, levels in (("phase4", p4, PHASE4), ("phase5", p5, PHASE5)):
        for lv in levels + ("all",):
            m = (lab == lv) if lv != "all" else np.ones(len(cohort), bool)
            c = m & (y == "censored")
            rows.append({"population": pop, "phase_scheme": name, "phase": lv, **counts(cohort, m),
                         "censored_followup_le_1d": int((c & (fu <= 1)).sum()),
                         "censored_death_without_progression": int((c & cohort.death_without_progression).sum()),
                         "censored_median_followup_d": float(np.median(fu[c])) if c.any() else np.nan,
                         "share_censored": float(c.sum() / max(m.sum(), 1)),
                         "event_rate_verified": float((m & (y == "event")).sum() / max((m & (y != "censored")).sum(), 1))})
    tab = pd.DataFrame(rows)

    doc = rt_documented(cohort, index)
    first = cohort.assign(doc=doc, fu=fu, chemo=d["clinical_initial_chemo_therapy"].astype(str).str.strip().to_numpy(),
                          hospice=d["clinical_hospice"].astype(str).str.strip().to_numpy())
    pats = []
    for flag, g in first.groupby("doc"):
        pp = g.groupby("patient_id")
        p1 = pp.first()
        q = lambda s: f"{np.median(s):.0f} [{np.percentile(s, 25):.0f}-{np.percentile(s, 75):.0f}]"
        pats.append({"population": pop, "rt_documented": bool(flag), "patients": len(p1), "scans": len(g),
                     "scans_per_patient": q(pp.size()), "age": q(p1.age), "male_share": p1.male.mean(),
                     "grade4_share": p1.grade4.mean(), **{f"idh_{k}": int((p1.idh == k).sum()) for k in ("wildtype", "mutant", "unknown")},
                     **{f"mgmt_{k}": int((p1.mgmt == k).sum()) for k in ("methylated", "unmethylated", "unknown")},
                     "chemo_field_yes": int((p1.chemo == "Yes").sum()), "chemo_field_blank": int(p1.chemo.isin(["nan", ""]).sum()),
                     "hospice_yes": int((p1.hospice.isin(["Yes", "1", "1.0"])).sum()),
                     "scan_day_median_range": f"{g.days_from_diagnosis_to_mri.median():.0f} ({g.days_from_diagnosis_to_mri.min():.0f} to {g.days_from_diagnosis_to_mri.max():.0f})",
                     "followup_from_scan_d": q(g.fu), "followup_from_first_scan_d": q(pp.fu.max()),
                     "scans_followup_le_1d": int((g.fu <= 1).sum()),
                     "patients_died_without_progression": int(pp.death_without_progression.any().sum()),
                     "patients_with_progression": int(pp.event.any().sum()),
                     **{f"scans_{k}": int((y[g.index] == k).sum()) for k in ("event", "non_event", "censored")}})
    pats = pd.DataFrame(pats)

    unk = cohort.early_post_rt.isna().to_numpy()
    t1 = pd.DataFrame([{"population": pop, "table1_early_post_rt_unknown": int(unk.sum()),
                        **{f"unknown_in_{lv}": int((unk & (p5 == lv)).sum()) for lv in PHASE5},
                        "unknown_rt_never_documented": int((unk & ~doc).sum()),
                        "unknown_rt_documented_no_end_date": int((unk & doc).sum()),
                        "early_post_rt_window_scans": int((cohort.early_post_rt == 1).sum()),
                        "pre_diagnosis_scans": int(pre_diagnosis(cohort).sum()),
                        "pre_diagnosis_patients": int(cohort.patient_id[pre_diagnosis(cohort)].nunique()),
                        "pre_diagnosis_day_range": f"{cohort.days_from_diagnosis_to_mri[pre_diagnosis(cohort)].min():.0f} to "
                                                   f"{cohort.days_from_diagnosis_to_mri[pre_diagnosis(cohort)].max():.0f}"}])
    return {"phase_outcome": tab, "rt_documentation": pats, "table1_unknown": t1}


def hanley_mcneil_se(auc, n1, n0):
    q1, q2 = auc / (2 - auc), 2 * auc ** 2 / (1 + auc)
    return np.sqrt((auc * (1 - auc) + (n1 - 1) * (q1 - auc ** 2) + (n0 - 1) * (q2 - auc ** 2)) / (n1 * n0))


def mde_table(pop, shuffle=None) -> pd.DataFrame:
    """MDE of an AUC vs 0.5 per stratum (80% power, two-sided 0.05: 2.80 x SE at AUC 0.5), SE at AUC 0.7; scans
    treated as independent (patient clustering ignored, so optimistic)."""
    cohort, _, index, p4, p5 = load(pop, shuffle)
    y = cohort[f"label_{H}"].to_numpy(float)
    rows = []
    for coh in COHORTS:
        cm = cohort_mask(coh, cohort, index)
        strata = {"all": cm, **{lv: cm & (p5 == lv) for lv in PHASE5}, **{lv: cm & (p4 == lv) for lv in ("pre_rt",)}}
        for lv, m in strata.items():
            n1, n0 = int((y[m] == 1).sum()), int((y[m] == 0).sum())
            ok = n1 > 0 and n0 > 0
            rows.append({"population": pop, "cohort": coh, "stratum": lv, "events": n1, "non_events": n0,
                         "se_auc_0.5": hanley_mcneil_se(0.5, n1, n0) if ok else np.nan,
                         "se_auc_0.7": hanley_mcneil_se(0.7, n1, n0) if ok else np.nan,
                         "mde_auc_vs_0.5": 2.80 * hanley_mcneil_se(0.5, n1, n0) if ok else np.nan,
                         "auc_reportable": n1 >= MIN_STRATUM and n0 >= MIN_STRATUM})
    out = pd.DataFrame(rows)
    paired = []  # from existing, already reported bootstrap CIs
    rg = RESULTS / "analyses" / "phase_ladder" / "rungs.csv"
    sa = RESULTS / "analyses" / "audit_system" / "shortcut_arms.csv"
    if rg.exists():
        r = pd.read_csv(rg)
        r = r[(r.population == pop) & (r.learner == "ridge") & (r.reference == "R0|ridge") & r.d_auc_ipcw.notna()]
        for _, x in r.iterrows():
            se = (x.d_auc_ipcw_hi - x.d_auc_ipcw_lo) / 3.92
            paired.append({"population": pop, "cohort": x.cohort, "stratum": f"paired {x.arm} - R0 (phase_ladder)",
                           "se_paired_diff": se, "mde_paired_diff": 2.80 * se})
    if sa.exists():
        s = pd.read_csv(sa)
        for _, x in s[(s.population == pop) & s.d_auc_ipcw_vs_baseline.notna()].iterrows():
            se = (x.d_auc_ipcw_hi - x.d_auc_ipcw_lo) / 3.92
            paired.append({"population": pop, "cohort": "full", "stratum": f"paired {x.arm} - core (audit)",
                           "se_paired_diff": se, "mde_paired_diff": 2.80 * se})
    return pd.concat([out, pd.DataFrame(paired)], ignore_index=True)


# ---------------------------------------------------------------- LUMIERE transport of the shared-feature model
def lumiere_rows(pop, n_boot, shuffle=None):
    from prism.experiments import external_lumiere as ext
    from prism.models.metrics import cluster_bootstrap, point_metrics
    mc, MX = ext.mu_table(pop == "grade4")
    if shuffle is not None:
        mc = load(pop, shuffle)[0]
    lc, LX = ext.lumiere_table()
    if shuffle is not None:
        lc = shuffle_outcomes(lc, shuffle)
    cols = ext.FEATURE_SETS["clinical+timing+volumes"]
    nou = [c for c in cols if c not in UNKNOWN]

    def corrected(X, c, early_asof):
        X = X.copy()
        m = masked_molecular(c)
        X["idh_mutant"], X["mgmt_methylated"] = m.idh_mutant.to_numpy(), m.mgmt_methylated.to_numpy()
        if early_asof:
            X["early_post_rt"] = X["early_post_rt"].fillna(0.0)  # NaN = RT end never documented -> not post-RT
        return X
    arms = {"locked_shared": (MX, LX, cols), "shared_no_unknown": (MX, LX, nou),
            "shared_C1": (corrected(MX, mc, False), corrected(LX, lc, False), nou),
            "shared_C2": (corrected(MX, mc, True), corrected(LX, lc, True), nou)}
    preds = {k: ext.fit("ridge", A[c], mc)(B[c]) for k, (A, B, c) in arms.items()}
    boot = cluster_bootstrap(lc, preds, H, "locked_shared", metrics=("auc_ipcw", "brier_ipcw", "oe_ratio", "cal_slope"),
                             n_boot=n_boot).set_index("formulation")
    rows = []
    for k, p in preds.items():
        pm = point_metrics(lc, p, H)
        rows.append({"population": pop, "arm": k, **{m: pm[m] for m in ("auc_ipcw", "brier_ipcw", "oe_ratio", "cal_slope")},
                     "mean_pred": float(p.mean()), **boot.loc[k].to_dict(),
                     "mu_early_post_rt_nan": int(arms[k][0]["early_post_rt"].isna().sum()),
                     "lumiere_pre_diagnosis_scans": 0})
    return rows


# ---------------------------------------------------------------- main
def assemble(pop, coh, res, n):
    oofs = {}
    for (p, c, a, r, k, _), te, pr in res:
        if (p, c) == (pop, coh):
            oofs.setdefault(a, np.zeros((5, n)))[r, te] = pr
    return oofs


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism phasecens", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=40)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--n-draw", type=int, default=1000, help="random / composition-matched removal draws (referral)")
    ap.add_argument("--populations", nargs="+", default=list(POPS))
    ap.add_argument("--descriptives-only", action="store_true", help="item 1 tables + MDE only (no model)")
    ap.add_argument("--shuffle-labels", type=int, default=None, help="permute outcomes (pipeline test) -> separate dir")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    t0 = time.time()
    warnings.filterwarnings("ignore")
    sh = a.shuffle_labels
    out = OUT if sh is None else OUT.parent / f"phase_censoring_shuffled{sh}"
    out.mkdir(parents=True, exist_ok=True)
    snap = out / "PLAN_snapshot.md"
    if sh is None and not a.descriptives_only and not snap.exists():  # plan section, frozen before the first real run
        doc = (REPO / "docs" / "results" / "PHASE_CENSORING.md").read_text()
        plan = doc.split("## Analysis plan (pre-specified)", 1)[1].split("\n## ", 1)[0]
        snap.write_text(f"# PLAN snapshot ({time.strftime('%Y-%m-%dT%H:%M:%S')}, git {git_state()['commit'][:10]})\n\n"
                        "## Analysis plan (pre-specified)" + plan)
    desc = {k: [] for k in ("phase_outcome", "rt_documentation", "table1_unknown")}
    for pop in a.populations:
        for k, v in descriptives(pop, sh).items():
            desc[k].append(v)
    for k, v in desc.items():
        pd.concat(v).to_csv(out / f"descriptives_{k}.csv", index=False)
    pd.concat([mde_table(p, sh) for p in a.populations]).to_csv(out / "mde.csv", index=False)
    print(pd.concat(desc["table1_unknown"]).T.to_string())
    if a.descriptives_only:
        return

    jobs = [(p, c, arm, r, k, sh) for p in a.populations for c in COHORTS for arm in ARMS[c]
            for r in range(5) for k in range(5)]
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(cv_job, jobs, chunksize=4))
    print(f"fits done {time.time() - t0:.0f}s", flush=True)

    tables = {k: [] for k in ("schemes", "ladder_schemes", "within_phase", "corrected", "cohorts", "mitigations",
                              "referral", "referral_within_phase", "lumiere", "checks")}
    from prism.analyses.audit_system import referral_tables, stratum_metrics
    for pop in a.populations:
        cohort, _, index, p4, p5 = load(pop, sh)
        full_oofs = {}
        for coh in COHORTS:
            keep = cohort_mask(coh, cohort, index)
            d = cohort[keep].reset_index(drop=True)
            q4, q5 = p4[keep], p5[keep]
            oofs = assemble(pop, coh, res, len(d))
            if coh == "full":
                full_oofs = oofs
            else:  # full-cohort models evaluated on the subset scans
                oofs.update({f"{k}@full": v[:, keep] for k, v in full_oofs.items() if k in ("R0", "R2", "R3", "C2")})
            pd.concat([pd.DataFrame(o.T, columns=[f"{k}#r{r}" for r in range(len(o))]) for k, o in oofs.items()],
                      axis=1).assign(scan_id=d.scan_id.to_numpy(), phase4=q4, phase5=q5).to_csv(
                out / f"oof_{pop}_{coh}.csv.gz", index=False)
            # checks: reproduce stored predictions / AUCs (no new information)
            if coh == "full" and sh is None:
                ref = pd.read_csv(RESULTS / "c3" / pop / "oof_repeats.csv.gz").set_index("scan_id").loc[d.scan_id]
                ref = np.array([ref[f"None|none|none|none|ridge#r{r}"].to_numpy() for r in range(5)])
                lad = pd.read_csv(RESULTS / "analyses" / "phase_ladder" / f"oof_repeats_{pop}_full.csv.gz"
                                  ).set_index("scan_id").loc[d.scan_id]
                tables["checks"].append({"population": pop, "max_dev_core_vs_c3": float(np.abs(ref - oofs["R3"]).max()),
                                         **{f"max_dev_{b}_vs_phase_ladder": float(np.abs(np.array(
                                             [lad[f"{b}|ridge#r{r}"] for r in range(5)]) - oofs[b]).max())
                                            for b in ("R0", "R1", "R2")}})
            ctx = ipcw_context(d, H)
            marg = {k: float(np.mean(fast_auc_brier(ctx, v)[0])) for k, v in oofs.items()}
            subsets = {f"phase5={lv}": q5 == lv for lv in PHASE5 if (q5 == lv).any()}
            subsets.update({f"phase4={lv}": q4 == lv for lv in PHASE4 if (q4 == lv).any()})
            point, draws = bootstrap(d, oofs, q4, q5, a.n_boot, a.workers, subsets=subsets, pair_strata=q4)
            for k in oofs:
                assert abs(point[("marginal_km", k, "all")] - marg[k]) < 1e-9, (pop, coh, k, "marginal_km mismatch")
            base = {"population": pop, "cohort": coh, **counts(d)}
            for sc in SCHEMES:
                for k in oofs:
                    key = (sc, k, "all")
                    if key not in point:
                        continue
                    lo, hi = ci(draws[key]) if key in draws else (np.nan, np.nan)
                    row = {**base, "scheme": sc, "arm": k, "auc": point[key], "auc_lo": lo, "auc_hi": hi,
                           **{f"vs_marginal_{x}": v for x, v in contrast(point, draws, key, ("marginal_km", k, "all")).items()},
                           **{f"vs_R3_{x}": v for x, v in contrast(point, draws, key, (sc, "R3", "all")).items()},
                           "auc_phase_stratified": point.get((sc, k, "phase_stratified"), np.nan)}
                    if (sc, k, "phase_stratified") in draws:
                        row["auc_phase_stratified_lo"], row["auc_phase_stratified_hi"] = ci(draws[(sc, k, "phase_stratified")])
                    tables["schemes"].append(row)
                for b in ("R1", "R2", "R3", "C2"):  # ladder: gain over R0, and its change vs marginal (diff of diffs)
                    ka, k0 = (sc, b, "all"), (sc, "R0", "all")
                    if ka not in point or k0 not in point:
                        continue
                    g = contrast(point, draws, ka, k0)
                    dd = {}
                    if sc != "marginal_km" and ka in draws and k0 in draws:
                        m1, m0 = ("marginal_km", b, "all"), ("marginal_km", "R0", "all")
                        x = (draws[ka] - draws[k0]) - (draws[m1] - draws[m0])
                        dd = {"change_vs_marginal": (point[ka] - point[k0]) - (point[m1] - point[m0]),
                              "change_lo": ci(x)[0], "change_hi": ci(x)[1]}
                    tables["ladder_schemes"].append({**base, "scheme": sc, "arm": b, "reference": "R0",
                                                     **{f"gain_{x}": v for x, v in g.items()}, **dd})
            for sn, m in subsets.items():
                lv = sn.split("=", 1)[1]
                yv = d[f"label_{H}"].to_numpy(float)[m]
                rep = (yv == 1).sum() >= MIN_STRATUM and (yv == 0).sum() >= MIN_STRATUM
                for sc in ("marginal_km", "phase5_km", "logistic_ipw", "verified"):
                    for k in [x for x in ("R0", "R2", "R3", "C2", "R3@full", "C2@full") if x in oofs]:
                        key = (sc, k, sn)
                        if key not in point:
                            continue
                        lo, hi = ci(draws[key]) if (rep and key in draws) else (np.nan, np.nan)
                        tables["within_phase"].append({"population": pop, "cohort": coh, "phase_scheme": sn.split("=")[0],
                                                       "phase": lv, **counts(d, m), "scheme": sc, "arm": k,
                                                       "auc": point[key], "auc_lo": lo, "auc_hi": hi,
                                                       "descriptive_only": not rep})
            # headline-estimator table (Brier, calibration) for the corrected models and cohort arms
            ev = evaluate_repeated(d, {k: v for k, v in oofs.items() if "@" not in k}, H, reference="R3",
                                   n_boot=a.n_boot)
            for k, row in ev.iterrows():
                sm = stratum_metrics(d, oofs[k])
                tables["corrected" if coh == "full" else "cohorts"].append(
                    {**base, "arm": k, **{c: row.get(c) for c in ("auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "brier_ipcw",
                                                                    "d_auc_ipcw_vs_R3", "d_auc_ipcw_lo", "d_auc_ipcw_hi",
                                                                    "d_auc_ipcw_p_le0", "oe_ratio", "cal_slope",
                                                                    "auc_verified")},
                     "citl": sm["citl"], "cal_slope_audit": sm["cal_slope"]})
            if coh == "full":
                # mitigations (b): referral flags on the full-cohort OOF predictions
                for k in ("R3", "C2"):
                    rules = {"pre_rt_as_of_scan": q4 == "pre_rt", "rt_never_documented": q5 == "pre_rt_never_documented",
                             "i_early_post_rt": q4 == "early_post_rt",
                             "pre_rt_or_early_post_rt": np.isin(q4, ["pre_rt", "early_post_rt"])}
                    rr, wp = referral_tables(pop, d, oofs[k], rules, q4, a.n_draw)
                    tables["referral"] += [{**x, "arm": k} for x in rr]
                    tables["referral_within_phase"] += [{**x, "arm": k} for x in wp]
            # mitigations (a): scope restriction summary
            for k in ("R3", "C2"):
                for sc in ("marginal_km", "phase5_km"):
                    if (sc, k, "all") in point:
                        tables["mitigations"].append({**base, "mitigation": f"scope={coh}", "arm": k, "scheme": sc,
                                                      "auc": point[(sc, k, "all")],
                                                      "auc_phase_stratified": point.get((sc, k, "phase_stratified")),
                                                      "scans_removed": len(cohort) - len(d),
                                                      "censored_removed": int(cohort[f"label_{H}"].isna().sum()
                                                                              - d[f"label_{H}"].isna().sum())})
        tables["lumiere"] += lumiere_rows(pop, a.n_boot, sh)
        print(f"{pop} done {time.time() - t0:.0f}s", flush=True)
    for k, rows in tables.items():
        pd.DataFrame(rows).to_csv(out / f"{k}.csv", index=False)
    (out / "run_info.json").write_text(json.dumps({"argv": vars(a), "seconds": round(time.time() - t0)}, indent=1))
    s = pd.DataFrame(tables["ladder_schemes"])
    if len(s):
        print(s[s.arm.eq("R2")][["population", "cohort", "scheme", "gain_diff", "gain_diff_lo", "gain_diff_hi",
                                 "change_vs_marginal"]].round(3).to_string(index=False))
    print(f"total {time.time() - t0:.0f}s")


# ---------------------------------------------------------------- self-test (synthetic data + design checks)
def selftest() -> None:
    rng = np.random.default_rng(0)
    n = 300
    d = pd.DataFrame({"patient_id": rng.integers(0, 120, n), "event": rng.random(n) < 0.5,
                      "time_to_event": np.round(rng.exponential(150, n)) + 0.5, "status_known_indefinitely": False})
    cens0 = rng.random(n) < 0.15  # a block censored on the scan day, as in the MU pre-RT scans
    d.loc[cens0, "event"], d.loc[cens0, "time_to_event"] = False, 0.5
    t, e = d.time_to_event.to_numpy(), d.event.to_numpy()
    d[f"label_{H}"] = np.where(e & (t <= H), 1.0, np.where(t > H, 0.0, np.nan))
    P = rng.random((5, n)) + 0.3 * np.nan_to_num(d[f"label_{H}"].to_numpy())
    P[:, :10] = 0.5  # ties
    st = rng.choice(PHASE5, n)
    # 1. marginal scheme == sksurv / fast_auc_brier
    case, ctrl, w = km_scheme(d)
    ref = fast_auc_brier(ipcw_context(d, H), P)[0]
    assert np.allclose(wauc(P, case, ctrl, w), ref, atol=1e-12), "wauc != fast_auc_brier"
    from sksurv.metrics import cumulative_dynamic_auc
    from sksurv.util import Surv
    s = Surv.from_arrays(event=e, time=t)
    assert abs(cumulative_dynamic_auc(s, s, P[0], [H])[0][0] - wauc(P[:1], case, ctrl, w)[0]) < 1e-12
    # 2. one-level strata == marginal; subset restriction == fast_auc_brier subset
    assert np.allclose(wauc(P, *km_scheme(d, np.zeros(n))), ref)
    sub = st == "early_post_rt"
    assert np.allclose(wauc(P, case, ctrl, w, subset=sub), fast_auc_brier(ipcw_context(d, H), P, subset=sub)[0])
    # 3. stratified KM: equals marginal KM run inside each stratum (within-stratum AUC)
    c5, k5, w5 = km_scheme(d, st)
    ds = d[sub].reset_index(drop=True)
    assert np.allclose(wauc(P, c5, k5, w5, subset=sub), fast_auc_brier(ipcw_context(ds, H), P[:, sub])[0])
    # 4. phase-stratified AUC with one stratum == overall; unweighted label scheme == roc_auc on verified
    assert np.allclose(wauc(P, case, ctrl, w, strata=np.zeros(n)), ref)
    from sklearn.metrics import roc_auc_score
    y = d[f"label_{H}"].to_numpy()
    cv_, kv_, wv_ = label_scheme(d)
    assert abs(wauc(P[:1], cv_, kv_, wv_)[0] - roc_auc_score(y[~np.isnan(y)], P[0][~np.isnan(y)])) < 1e-12
    # 5. a censoring weight that depends on the stratum changes the AUC when strata differ in risk and censoring
    print("synthetic: marginal", ref.mean().round(4), "phase5", wauc(P, c5, k5, w5).mean().round(4))
    # 6. design checks on the real cohort (features only, no labels used)
    for pop, n_pre in (("grade4", 8), ("all_glioma", 11)):
        cohort = load_cohort(pop)
        index = load_index()
        assert pre_diagnosis(cohort).sum() == n_pre, (pop, pre_diagnosis(cohort).sum())
        p5 = phase5_label(cohort, index)
        unk = cohort.early_post_rt.isna().to_numpy()
        assert (unk == ((p5 == "pre_rt_never_documented") | (phase_label(cohort) == "during_rt") & unk)).all()
        X3, _ = arm_design("R3", cohort, index)
        for arm in ("core_no_unknown", "C1", "C1_mean", "C2"):
            X, g = arm_design(arm, cohort, index)
            assert not set(UNKNOWN) & set(X.columns) and set(g) == set(X.columns), arm
            assert len(X.columns) == len(X3.columns) - 2, arm
            if arm != "core_no_unknown":
                pd_ = pre_diagnosis(cohort)
                v = X.loc[pd_, ["idh_mutant", "mgmt_methylated"]]
                assert (v.fillna(0) == 0).all().all(), arm
                same = ~pd_ & cohort.idh.ne("unknown").to_numpy()
                assert (X.idh_mutant[same] == X3.idh_mutant[same]).all(), arm
        X2, _ = arm_design("C2", cohort, index)
        assert X2.early_post_rt.notna().all() and (X2.early_post_rt[~unk] == X3.early_post_rt[~unk]).all()
        from prism.experiments.c3_radiomics import BASE_PRE
        from sklearn.base import clone
        names = clone(BASE_PRE).fit(X2).get_feature_names_out()
        assert "missingindicator_early_post_rt" not in names and not any("idh" in c and "missing" in c for c in names)
        assert "missingindicator_early_post_rt" in clone(BASE_PRE).fit(X3).get_feature_names_out()
        Xm, _ = arm_design("C1_mean", cohort, index)
        f = fill_in_fold(Xm, np.arange(0, len(Xm), 2))
        assert f[["idh_mutant", "mgmt_methylated"]].notna().all().all()
        print(pop, "design ok:", len(X3.columns), "raw core columns;", int(unk.sum()), "early_post_rt unknown =",
              int((p5 == "pre_rt_never_documented").sum()), "never documented +", int((unk & (p5 == "during_rt")).sum()),
              "during RT without end date")
    print("selftest passed")


if __name__ == "__main__":
    main()
