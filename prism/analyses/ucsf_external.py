"""UCSF-ALPTDG Part A: locked MU models applied once to UCSF (external test, no refit), and the locked 120-day forward
models applied to UCSF scan 1.

ANALYSIS PLAN: docs/results/UCSF_PLAN.md (commit 0e7c9fe, written before any outcome model on UCSF).

Detection arms, each fitted ONCE on the MU detection training rows of detection.context(pop, "primary") (positives +
primary negatives, all phases; grade-4 models for the grade-4 / GBM sets, all-glioma models for the all-glioma set)
with the verified ridge pipeline of the LUMIERE locked test (c3.BASE_PRE + c3._ridge, seed 0):
  A-B0        age, sex, IDH, MGMT (C2 rules: unknown -> 0, no indicators)
  A-Iscan     measurement_groups volumes + morphology / relative intensity
  A-Ipure     A-Iscan + log volume ratios to the previous scan + ET / lesion ratio to the whole-history minimum
  A-B0+Iscan, A-B0+Ipure
  A-Timg      LUMIERE image set (ET, necrosis + cavity, oedema volumes and their ratios to the previous scan)
  A-Tbase     clinical + log days since surgery + early post-RT flag; A-T = A-Tbase + A-Timg + has_prev + log days
              since the previous scan (UCSF: days since surgery = days from diagnosis, diagnosis = first surgery;
              early post-RT = 42-125 d after the RT start, an assumed 6-week course + 84 d)
120-day forward (secondary): F-B0, F-Iscan, F-B0+Iscan fitted once on MU index scans (verified label_120), applied
to UCSF scan 1. I_pure is not defined at UCSF scan 1 (no earlier scan in the dataset).
Evaluation: plain AUC, patient-cluster bootstrap (1,000 draws, seed 20261025), paired contrasts on the same draws;
calibration slope and O/E for the locked models (secondary). Transport-failure flag: AUC < 0.65.

    PYTHONPATH=. .venv/bin/python -m prism.analyses.ucsf_external [--n-boot 1000]
    -> $PRISM_OUTPUTS/results/analyses/ucsf/locked/
"""

from __future__ import annotations

import argparse
import json
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression

from prism.analyses import detection as D
from prism.config import RESULTS

OUT = RESULTS / "analyses" / "ucsf" / "locked"
SEED = 20261025
NEG_PRIMARY = ("verified_by_later_progression", "no_progression_followed_120")
TIMG = ["log_et_cc", "log_necrosis_cavity_cc", "log_snfh_cc", "logratio_prev_et", "logratio_prev_necrosis_cavity",
        "logratio_prev_snfh"]
NADIR = ["nadir_all_et", "nadir_all_lesion"]
ARMS = ("A-B0", "A-Iscan", "A-Ipure", "A-B0+Iscan", "A-B0+Ipure", "A-Timg", "A-Tbase", "A-T")
SINGLE_SCAN = ("A-B0", "A-Iscan", "A-B0+Iscan")
CONTRASTS = [("A-B0+Ipure", "A-B0"), ("A-T", "A-Tbase"), ("A-Ipure", "A-Iscan")]
FWD_ARMS = ("F-B0", "F-Iscan", "F-B0+Iscan")
FWD_CONTRASTS = [("F-B0+Iscan", "F-B0"), ("F-Iscan", "F-B0")]
H = 120


# ---------------------------------------------------------------- MU designs
def _nadir_all(d, meas):
    from prism.analyses.triage_feasibility import _features_one
    by_pat = {p: g.sort_values("mri_day") for p, g in meas.groupby("patient_id")}
    rows = [_features_one(by_pat[pid][by_pat[pid].mri_day <= day], day, -np.inf)
            for pid, day in zip(d.patient_id, d.mri_day)]
    return pd.DataFrame({"nadir_all_et": [r["traj_logratio_nadir_et"] for r in rows],
                         "nadir_all_lesion": [r["traj_logratio_nadir_lesion"] for r in rows]}, index=d.index)


def _arms(b0, iscan, ipure_extra, T):
    ipure = pd.concat([iscan, ipure_extra], axis=1)
    return {"A-B0": b0, "A-Iscan": iscan, "A-Ipure": ipure, "A-B0+Iscan": pd.concat([b0, iscan], axis=1),
            "A-B0+Ipure": pd.concat([b0, ipure], axis=1), "A-Timg": T[TIMG], "A-Tbase": T[D.T_BASE], "A-T": T}


def mu_detection(pop):
    """MU detection frame (training label in label_120) and every Part-A design, built as the exploratory scripts."""
    from prism.features.tabular import measurement_groups
    meas = D._base()[3]
    d, X, _, _, F = D.context(pop, "primary")
    mg = measurement_groups(d)
    iscan = pd.concat([mg["volumes"], mg["morphology"]], axis=1)
    prevr = F[[f"logratio_prev_{v}" for v in D.VOLS]]
    T = X["T"]
    assert TIMG == [c for c in T.columns if c not in D.T_BASE + ["has_prev", "log_days_from_prev"]]
    return d, _arms(X["B0"], iscan, pd.concat([prevr, _nadir_all(d, meas)], axis=1), T)


def mu_forward(pop):
    """MU index scans (mu_cohort, verified label_120) with the forward designs F-B0, F-Iscan, F-B0+Iscan."""
    from prism.analyses import phase_censoring as pc
    from prism.features.tabular import measurement_groups
    c = pc.load(pop)[0].reset_index(drop=True)
    mg = measurement_groups(c)
    b0, iscan = D.masked_clinical(c), pd.concat([mg["volumes"], mg["morphology"]], axis=1)
    c2, _ = pc.arm_design("C2", c, pc.load_index())
    dev = np.nanmax(np.abs(c2[list(b0.columns)].to_numpy(float) - b0.to_numpy(float)))
    assert dev == 0, "forward B0 differs from the C2 clinical columns"
    return c, {"F-B0": b0, "F-Iscan": iscan, "F-B0+Iscan": pd.concat([b0, iscan], axis=1)}


# ---------------------------------------------------------------- UCSF designs
def ucsf_frame():
    """scans.csv joined 1:1 with the image features; the columns masked_clinical needs (age = age at diagnosis)."""
    from prism.data.ucsf import load_scans
    from prism.features.ucsf_imaging import FEATURES
    s = load_scans()
    f = pd.read_csv(FEATURES, dtype={"SubjectID": str})
    assert len(s) == len(f) == 596 and set(s.scan_id) == set(f.scan_id)
    fh = f.set_index("scan_id").has_prev.reindex(s.scan_id).to_numpy()
    assert (fh == s.has_prev.to_numpy()).all(), "image has_prev differs from the clinical table"
    u = s.merge(f.drop(columns=["SubjectID", "timepoint", "has_prev"]), on="scan_id", how="left",
                validate="one_to_one")
    u["patient_id"] = u.subject_id
    # MU "age" is age at diagnosis; UCSF gives age at each scan (integer years). Per patient from scan 1.
    s1 = u[u.timepoint.eq(1)].set_index("subject_id")
    age_dx = (s1.age - s1.days_from_diagnosis_to_mri.fillna(0) / 365.25)
    u["age_at_scan"] = u.age
    u["age"] = age_dx.reindex(u.subject_id).to_numpy()
    assert u.idh.isin(["mutant", "wildtype", "unknown"]).all() and u.mgmt.isin(
        ["methylated", "unmethylated", "unknown"]).all()
    u["primary_neg"] = u.neg_class.isin(NEG_PRIMARY)
    return u


def ucsf_designs(u, mu_arms):
    """Part-A designs on UCSF, column for column as on MU (image inputs as stored by ucsf_imaging.model_inputs)."""
    b0 = D.masked_clinical(u)
    iscan = u[list(mu_arms["A-Iscan"].columns)].astype(float)
    pre = u[[f"logratio_prev_{v}" for v in D.VOLS] + NADIR].astype(float)
    T = b0.copy()
    T["log_days_since_surgery"] = np.log1p(u.days_from_diagnosis_to_mri.clip(lower=0))
    T["early_post_rt"] = u.rt_phase.eq("early_post_rt").astype(float)
    for c in ("log_et_cc", "log_necrosis_cavity_cc", "log_snfh_cc"):
        T[c] = u[c].to_numpy(float)
    T["has_prev"] = u.has_prev.astype(float)
    T["log_days_from_prev"] = np.log1p(u.days_from_prev.fillna(0))
    for c in TIMG[3:]:
        T[c] = u[c].to_numpy(float)
    A = _arms(b0, iscan, pre, T)
    for arm, X in A.items():
        assert list(X.columns) == list(mu_arms[arm].columns), arm
    return A


def ucsf_label_120(u):
    """Scan 1: 1 = progression 1-120 d after it; 0 = progression > 120 d after it or >= 120 d follow-up without
    progression; NaN otherwise (progression at scan 1 [-7, 1) d, earlier progression, unknown follow-up)."""
    p = u.days_to_progression
    y = np.where(p.between(1, H), 1.0, np.where((p > H) | u.neg_class.eq("no_progression_followed_120"), 0.0, np.nan))
    y[~u.timepoint.eq(1).to_numpy() | u.label_excluded_prior_progression.to_numpy()] = np.nan
    return y


# ---------------------------------------------------------------- locked fit
def lock(Xmu, d, Xext):
    """Fit BASE_PRE + verified ridge once on the MU rows with a label; return (MU-fit object, external risk)."""
    from prism.experiments import c3_radiomics as c3
    assert list(Xext.columns) == list(Xmu.columns), "external columns differ from MU (names / order)"
    tr = np.where(d.label_120.notna())[0]
    bp = clone(c3.BASE_PRE).fit(Xmu.iloc[tr])
    assert list(bp.feature_names_in_) == list(Xext.columns)
    m = c3._ridge(bp.transform(Xmu.iloc[tr]), d, tr, 0)
    return (bp, m), m.predict_proba(bp.transform(Xext.astype(float)))[:, 1]


def checks_mu(d4, A4):
    """Before any UCSF label: (1) the UCSF image builder (ucsf_imaging.model_inputs) on the MU pool reproduces the MU
    designs; (2) the locked-fit code reproduces the LUMIERE locked T / Tbase AUCs of detection.lumiere_locked."""
    from prism.features.ucsf_imaging import model_inputs
    out = []
    meas = D._base()[3]
    mi = model_inputs(meas).set_index("scan_id").reindex(d4.scan_id)
    for arm in ("A-Iscan", "A-Ipure", "A-Timg"):
        a, b = A4[arm].to_numpy(float), mi[list(A4[arm].columns)].to_numpy(float)
        dev = float(np.nanmax(np.abs(a - b)))
        same = bool(np.array_equal(np.isnan(a), np.isnan(b)))
        out.append({"check": f"MU grade 4: {arm} design == ucsf_imaging.model_inputs on MU (max dev)", "value": dev,
                    "ok": dev < 1e-12 and same})
        assert dev < 1e-12 and same, arm
    X = D.context("grade4", "primary")[1]
    for arm, ref in (("A-B0", "B0"), ("A-T", "T"), ("A-Tbase", "Tbase")):
        ok = A4[arm].equals(X[ref])
        out.append({"check": f"MU grade 4: {arm} design == detection.context {ref}", "value": float(not ok), "ok": ok})
        assert ok
    L, LX, _ = D.lumiere_detection()
    ref = pd.read_csv(D.OUT / "lumiere.csv")
    for arm in ("A-T", "A-Tbase"):
        _, p = lock(A4[arm], d4, LX[list(A4[arm].columns)])
        a = float(D.aucs(L.label_det.to_numpy(), p[None])[0])
        r = float(ref[(ref.subset == "all") & (ref.arm == f"{arm[2:]}@grade4")].auc.iat[0])
        out.append({"check": f"locked {arm} on LUMIERE reproduces detection.lumiere_locked ({r:.4f})", "value": a,
                    "ok": abs(a - r) < 1e-9})
        assert abs(a - r) < 1e-9
    return out


# ---------------------------------------------------------------- evaluation
def calibration(y, p):
    """(calibration slope, O/E, calibration-in-the-large) of risk p against y."""
    if len(np.unique(y)) < 2:
        return np.nan, np.nan, np.nan
    lp = np.log(np.clip(p, 1e-12, 1) / np.clip(1 - p, 1e-12, 1))
    slope = LogisticRegression(penalty=None, max_iter=5000).fit(lp[:, None], y).coef_[0, 0]
    a = 0.0  # intercept with logit(p) as offset (Newton)
    for _ in range(50):
        q = 1 / (1 + np.exp(-(a + lp)))
        a += (y - q).sum() / max((q * (1 - q)).sum(), 1e-12)
    return float(slope), float(y.sum() / p.sum()), float(a)


def evaluate(name, u, rows, y, preds, contrasts, n_boot, models):
    """AUC (+ CI, failure flag), paired contrasts and calibration for one evaluation set."""
    y, g = y[rows].astype(int), u.patient_id.to_numpy()[rows]
    oo = {a: p[None, rows] for a, p in preds.items()}
    pt, dr = D.bootstrap(y, oo, g, n_boot, SEED)
    base = {"set": name, "models": models, "n_scans": int(len(y)), "n_pos": int(y.sum()),
            "n_neg": int((y == 0).sum()), "n_patients": int(len(np.unique(g)))}
    auc, con, cal = [], [], []
    for a in oo:
        lo, hi = D.ci(dr[(a, "all")])
        auc.append({**base, "arm": a, "auc": pt[(a, "all")], "auc_lo": lo, "auc_hi": hi,
                    "p_le_half": float(np.mean(dr[(a, "all")] <= 0.5)),
                    "transport_failure_flag": bool(pt[(a, "all")] < 0.65)})
    for a, b in contrasts:
        if a in oo and b in oo:
            x = dr[(a, "all")] - dr[(b, "all")]
            lo, hi = D.ci(x)
            con.append({**base, "contrast": f"{a} - {b}", "diff": pt[(a, "all")] - pt[(b, "all")], "diff_lo": lo,
                        "diff_hi": hi, "p_le0": float(np.mean(x <= 0))})
    by = {k: np.where(g == k)[0] for k in np.unique(g)}
    pats = np.array(list(by))
    for a, p in oo.items():
        p = p[0]
        s, oe, citl = calibration(y, p)
        rng = np.random.default_rng(SEED)
        bs = []
        for _ in range(n_boot):
            ii = np.concatenate([by[k] for k in rng.choice(pats, len(pats))])
            bs.append(calibration(y[ii], p[ii])[:2])
        bs = np.array(bs)
        (slo, shi), (olo, ohi) = D.ci(bs[:, 0]), D.ci(bs[:, 1])
        cal.append({**base, "arm": a, "calibration_slope": s, "slope_lo": slo, "slope_hi": shi, "o_over_e": oe,
                    "oe_lo": olo, "oe_hi": ohi, "calibration_in_the_large": citl, "mean_risk": float(p.mean()),
                    "observed_rate": float(y.mean())})
    return auc, con, cal


def detection_sets(u):
    """(name, models, rows, label, arms) for every Part-A evaluation set of the plan."""
    t2, t1, g4 = u.timepoint.eq(2).to_numpy(), u.timepoint.eq(1).to_numpy(), u.grade4.to_numpy()
    neg, ver = u.primary_neg.to_numpy(), u.neg_class.eq("verified_by_later_progression").to_numpy()
    pm30, betw, s1at = (u[c].eq(1).to_numpy() for c in ("pos_s2_pm30", "pos_s2_between", "pos_s1_at"))
    lab = lambda pos: pos.astype(float)
    prim = t2 & g4 & (pm30 | neg)
    late = u.rt_phase.eq("later_post_rt").to_numpy()
    eti = u.et_increased.to_numpy(float)
    return [
        ("grade4|scan2|pm30 (PRIMARY)", "grade4", prim, lab(pm30), ARMS),
        ("gbm_who|scan2|pm30", "grade4", prim & u.gbm_who.to_numpy(), lab(pm30), ARMS),
        ("grade4|scan2|between", "grade4", t2 & g4 & (betw | neg), lab(betw), ARMS),
        ("grade4|scan2|pm30|verified_negatives", "grade4", t2 & g4 & (pm30 | ver), lab(pm30), ARMS),
        ("grade4|scan2|pm30|later_post_rt", "grade4", prim & late, lab(pm30), ARMS),
        ("grade4|all_scans|pm30+s1_at (single-scan inputs)", "grade4",
         g4 & ((t2 & pm30) | (t1 & s1at) | neg), lab((t2 & pm30) | (t1 & s1at)), SINGLE_SCAN),
        ("grade4|scan2|et_increased (imaging-defined reference)", "grade4", t2 & g4 & ~np.isnan(eti),
         np.nan_to_num(eti), ARMS),
        ("all_glioma|scan2|pm30", "all_glioma", t2 & (pm30 | neg), lab(pm30), ARMS),
    ]


def single_inputs(u, rows, y, A):
    """EXPLORATORY: univariable AUC of each locked input on an evaluation set."""
    out = []
    for c in A["A-T"].columns.union(A["A-Ipure"].columns, sort=False):
        X = A["A-T"] if c in A["A-T"] else A["A-Ipure"]
        v = X[c].to_numpy(float)[rows]
        ok = ~np.isnan(v)
        out.append({"feature": c, "n": int(ok.sum()), "auc": float(D.aucs(y[rows][ok].astype(int), v[ok][None])[0])})
    return pd.DataFrame(out)


# ---------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="ucsf_external", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--checks-only", action="store_true", help="MU / LUMIERE checks only (reads no UCSF label)")
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    mu = {pop: mu_detection(pop) for pop in D.POPS}
    checks = checks_mu(*mu["grade4"])
    pd.DataFrame(checks).to_csv(OUT / "checks.csv", index=False)
    print(pd.DataFrame(checks).to_string(index=False), f"\nchecks {time.time() - t0:.0f}s", flush=True)
    u = ucsf_frame()
    A = ucsf_designs(u, mu["grade4"][1])
    for pop, (d, M) in mu.items():
        for arm in ARMS:
            assert list(A[arm].columns) == list(M[arm].columns), (pop, arm)
    if a.checks_only:
        return

    # locked detection models: one fit per (population, arm), applied once to all UCSF scans
    preds, coefs = {}, []
    for pop, (d, M) in mu.items():
        for arm in ARMS:
            (bp, m), p = lock(M[arm], d, A[arm])
            preds[(pop, arm)] = p
            names = list(bp.get_feature_names_out())
            coefs += [{"models": pop, "arm": arm, "feature": n, "coef": float(c), "C": float(m.C)}
                      for n, c in zip(names, m.coef_[0])]
    # locked forward 120-day models (MU index scans) applied to UCSF scan 1
    fwd = {}
    for pop in D.POPS:
        c, M = mu_forward(pop)
        for arm in FWD_ARMS:
            src = {"F-B0": "A-B0", "F-Iscan": "A-Iscan", "F-B0+Iscan": "A-B0+Iscan"}[arm]
            fwd[(pop, arm)] = lock(M[arm], c, A[src])[1]
    sc = u[["scan_id", "patient_id", "timepoint", "grade4", "gbm_who", "rt_phase"]].copy()
    for (pop, arm), p in {**preds, **fwd}.items():
        sc[f"{arm}@{pop}"] = p
    sc.to_csv(OUT / "scores.csv", index=False)
    pd.DataFrame(coefs).to_csv(OUT / "coefficients.csv", index=False)

    AUC, CON, CAL = [], [], []
    for name, pop, rows, y, arms in detection_sets(u):
        r_, c_, k_ = evaluate(name, u, rows, y, {arm: preds[(pop, arm)] for arm in arms}, CONTRASTS, a.n_boot, pop)
        AUC += r_; CON += c_; CAL += k_
        print(f"{name} {time.time() - t0:.0f}s", flush=True)
    y120 = ucsf_label_120(u)
    ok = ~np.isnan(y120)
    for name, pop, m in (("grade4|scan1|120d", "grade4", u.grade4.to_numpy()),
                         ("gbm_who|scan1|120d", "grade4", u.gbm_who.to_numpy()),
                         ("all_glioma|scan1|120d", "all_glioma", np.ones(len(u), bool))):
        r_, c_, k_ = evaluate(name, u, ok & m, np.nan_to_num(y120), {arm: fwd[(pop, arm)] for arm in FWD_ARMS},
                              FWD_CONTRASTS, a.n_boot, pop)
        AUC += r_; CON += c_; CAL += k_
    auc, con, cal = pd.DataFrame(AUC), pd.DataFrame(CON), pd.DataFrame(CAL)
    auc.to_csv(OUT / "auc.csv", index=False)
    con.to_csv(OUT / "contrasts.csv", index=False)
    cal.to_csv(OUT / "calibration.csv", index=False)
    name, pop, rows, y, _ = detection_sets(u)[0]
    single_inputs(u, rows, y, A).to_csv(OUT / "single_input_auc_primary.csv", index=False)

    key = "grade4|scan2|pm30 (PRIMARY)"
    p = auc[(auc.set == key) & (auc.arm == "A-Ipure")].iloc[0]
    q = con[(con.set == key) & (con.contrast == "A-B0+Ipure - A-B0")].iloc[0]
    rule = [{"question": "Q1: A-Ipure AUC >= 0.65 with lower bound > 0.5 (grade 4, scan 2)", "value": p.auc,
             "lo": p.auc_lo, "hi": p.auc_hi, "met": bool(p.auc >= 0.65 and p.auc_lo > 0.5)},
            {"question": "Q2: A-B0+Ipure - A-B0 CI excludes 0", "value": q["diff"], "lo": q.diff_lo,
             "hi": q.diff_hi, "met": bool(q.diff_lo > 0 or q.diff_hi < 0)}]
    pd.DataFrame(rule).to_csv(OUT / "questions.csv", index=False)
    pr = u[rows]
    info = {"n_boot": a.n_boot, "seed": SEED, "seconds": round(time.time() - t0),
            "primary_set_rt_phase": pr.rt_phase.value_counts().to_dict(),
            "primary_set_early_post_rt_flag": int(pr.rt_phase.eq("early_post_rt").sum()),
            "primary_set_days_from_diagnosis_missing": int(pr.days_from_diagnosis_to_mri.isna().sum()),
            "scan1_120d": {"pos": int((y120 == 1).sum()), "neg": int((y120 == 0).sum())},
            "mu_training_rows": {pop: int(d.label_120.notna().sum()) for pop, (d, _) in mu.items()},
            "mu_training_prevalence": {pop: float(d.label_120.mean()) for pop, (d, _) in mu.items()}}
    (OUT / "run_info.json").write_text(json.dumps(info, indent=1, default=float))
    pd.set_option("display.width", 250)
    print(auc.round(3).to_string(index=False))
    print(con.round(3).to_string(index=False))
    print(cal.round(3).to_string(index=False))
    print(pd.DataFrame(rule).round(3).to_string(index=False), info)


if __name__ == "__main__":
    main()
