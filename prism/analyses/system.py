"""The full PRISM system for detection at the scan: per-scan system records and the pre-specified S1-S4.

PLAN: docs/results/SYSTEM_PLAN.md (commit e7cba80; sections 1-3 and 5). Results, schema and deviations:
docs/results/SYSTEM_RESULTS.md. Reports from these records (S5-S7) are a separate stage.

Pathways (grade 4 primary; MU all gliomas secondary):
  cohort   timeline        images                                        combined
  MU       B1 OOF (5 x 5)  I_pure OOF                                    B1 + I_pure OOF
  LUMIERE  locked Tbase    locked T_img; locked 3-volume model if no     locked T
                           previous scan (council: the I_scan analogue;
                           MU I_pure is not computable on LUMIERE)
  UCSF     locked A-Tbase  locked A-Ipure (scan 2 always has scan 1)     locked A-T
Conformal (prism.audit.conformal, as AUDIT_SYSTEM.md): on MU, inside each outer training fold a 70 / 30 patient split
(seed 10 * repeat + fold) gives proper-training and calibration rows, and the pathway is refitted on the 70%. Externally
one MU-calibrated model per pathway (split seed 0, all MU training rows), applied once. Mondrian (class-conditional)
sets are a secondary output. Flags: pathways disagree (card agreement rule), out of range (prism.audit.model.ood_flags
on the union of the pathways' inputs), card tier "few cases" / "not tested", combined conformal set {0, 1} at
alpha 0.2 (council). Records carry no outcome label (labels: records_<cohort>_EVALUATION_ONLY.csv).

    PYTHONPATH=. .venv/bin/python -m prism system [--steps scores records evaluate] [--workers 10] [--n-boot 1000]
    -> outputs/results/analyses/system/   (patient-level, git-ignored)
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
from sklearn.base import clone
from threadpoolctl import threadpool_limits

from prism.analyses import detection as D
from prism.analyses import reliability_card as RC
from prism.analyses import ucsf_external as UX
from prism.audit import conformal as cf
from prism.audit import reliability as R
from prism.audit.model import ood_flags, ood_ranges
from prism.config import MEASUREMENTS, OUTPUTS, RESULTS

OUT = RESULTS / "analyses" / "system"
SEED = 20261026
N_BOOT, N_REF, N_DRAW = 1000, 100, 1000
ALPHAS = (0.2, 0.1)
PW = ("timeline", "images", "combined")             # record names; the card's names are R.PATHWAYS
CARD_PW = dict(zip(PW, R.PATHWAYS))
FLAGS = ("disagree", "out_of_range", "tier", "conformal", "any")
SCHEMA = "prism.system_record/1"
LABEL_KEYS = {"label", "label_det", "label_120", "neg_primary", "neg_secondary", "rating", "neg_class",
              "days_to_progression", "pos_s2_pm30", "pos_s2_between", "pos_s1_at", "is_progression_scan", "y"}
VOL3 = ["log_et_cc", "log_necrosis_cavity_cc", "log_snfh_cc"]
EXPECTED = {  # published AUCs (DETECTION_TASK.md, RELIABILITY_CARD.md, UCSF_RESULTS.md); checked before evaluation
    ("mu", "grade4", "intended_use", "timeline"): 0.822, ("mu", "grade4", "intended_use", "images"): 0.709,
    ("mu", "grade4", "intended_use", "combined"): 0.821, ("mu", "grade4", "all_scans", "timeline"): 0.845,
    ("mu", "grade4", "all_scans", "images"): 0.712, ("mu", "all_glioma", "intended_use", "timeline"): 0.814,
    ("lumiere", "grade4", "all", "timeline"): 0.689, ("lumiere", "grade4", "all", "combined"): 0.773,
    ("lumiere", "grade4", "all", "images_T_img_all_scans"): 0.655, ("ucsf", "grade4", "scan2", "timeline"): 0.561,
    ("ucsf", "grade4", "scan2", "images"): 0.726, ("ucsf", "grade4", "scan2", "combined"): 0.856}


# ---------------------------------------------------------------- fitting
def _fit(X, d, rows):
    """BASE_PRE + verified ridge (seed 0) on the labelled rows among `rows`: the locked-test pipeline."""
    from prism.experiments import c3_radiomics as c3
    rows = np.asarray(rows)
    rows = rows[d.label_120.notna().to_numpy()[rows]]
    bp = clone(c3.BASE_PRE).fit(X.iloc[rows])
    m = c3._ridge(bp.transform(X.iloc[rows]), d, rows, 0)
    return lambda Z: m.predict_proba(bp.transform(Z[list(X.columns)].astype(float)))[:, 1]


def _q(p, y, pid):
    """Standard and Mondrian thresholds on calibration rows: {alpha: q}, {alpha: (q0, q1)}."""
    s = cf.scores(p, y)
    std = {a: cf.threshold(s, pid, a) for a in ALPHAS}
    mon = {a: tuple(cf.threshold(s[y == c], pid[y == c], a) for c in (0, 1)) for a in ALPHAS}
    return std, mon


# ---------------------------------------------------------------- MU (out-of-fold)
@lru_cache(maxsize=2)
def mu_designs(pop):
    d, A = UX.mu_detection(pop)
    b1 = D.context(pop, "primary")[1]["B1"]
    return d, {"timeline": b1, "images": A["A-Ipure"], "combined": pd.concat([b1, A["A-Ipure"]], axis=1)}


def mu_job(job):
    from prism.experiments import c3_radiomics as c3
    pop, r, k = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, X = mu_designs(pop)
    y, pid = d.label_120.to_numpy(), d.patient_id.to_numpy()
    f = D.fold_ids(d, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    proper, cal = cf.patient_split(pid[tr], 0.3, seed=10 * r + k)
    cr = tr[cal][~np.isnan(y[tr[cal]])]
    out = {"pop": pop, "r": r, "k": k, "te": te, "n_cal_scans": len(cr), "n_cal_patients": len(np.unique(pid[cr]))}
    for p, Xa in X.items():
        out[f"p_{p}"] = c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr, te, seed=r)
        pc = c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr[proper], np.concatenate([cr, te]), seed=r)
        out[f"pc_{p}"] = pc[len(cr):]
        out[f"q_{p}"], out[f"qm_{p}"] = _q(pc[:len(cr)], y[cr].astype(int), pid[cr])
    lab = tr[~np.isnan(y[tr])]
    out["ood"] = ood_flags(X["combined"].iloc[te], d.iloc[te], ood_ranges(X["combined"], lab))
    return out


def mu_situation(d):
    """Card phase and enhancement exactly as reliability_card.mu_frame (any population)."""
    index = D._base()[0]
    m = pd.read_csv(MEASUREMENTS).set_index("scan_id")
    st = pd.to_numeric(index.clinical_number_of_days_from_diagnosis_to_radiation_therapy_start_date, errors="coerce")
    rt_known = index.assign(st=st.to_numpy()).groupby("patient_id").st.apply(lambda s: s.notna().any())
    phase = np.where(rt_known.reindex(d.patient_id).fillna(False).to_numpy(), [R.phase_cell(p) for p in d.phase],
                     "unknown")
    et = m.et_cc.reindex(d.scan_id).to_numpy(float)
    prev = m.et_cc.reindex(d.prev_scan_id.replace("", np.nan)).to_numpy(float)
    return phase, np.array([R.enhancement_state(a, b) for a, b in zip(et, prev)])


def mu_measurements(d):
    meas = D._base()[3]
    by = {p: g.sort_values("mri_day") for p, g in meas.groupby("patient_id")}
    cur = meas.set_index("scan_id")
    rows = []
    for sid, pid, day in zip(d.scan_id, d.patient_id, d.mri_day):
        g = by[pid]
        e = g[g.mri_day < day]
        c = cur.loc[sid]
        rows.append(_meas({"et": c.et_cc, "snfh": c.snfh_cc, "necrosis": c.netc_cc, "cavity": c.rc_cc},
                          [({"et": x.et_cc, "snfh": x.snfh_cc, "necrosis": x.netc_cc, "cavity": x.rc_cc}, day - x.mri_day)
                           for x in e.itertuples()], "MU segmentation (prism measurements: ET, SNFH, NETC, RC)"))
    return rows


def _meas(cur: dict, earlier: list, source: str) -> dict:
    """Volumes (cc) at the scan; change from the previous scan (last of `earlier`) and from the smallest earlier
    volume of each compartment. `earlier` = [(volumes, days before the scan)] in date order, strictly earlier."""
    f = lambda v: None if v is None or not np.isfinite(v) else round(float(v), 3)
    out = {"volumes_cc": {k: f(v) for k, v in cur.items()}, "source": source, "n_earlier_scans": len(earlier)}
    if earlier:
        pv, dd = earlier[-1]
        out["previous"] = {"days_before": f(dd), "volumes_cc": {k: f(v) for k, v in pv.items()}}
        out["change_from_previous_cc"] = {k: f(cur[k] - pv[k]) for k in cur}
        mn = {k: np.nanmin([e[0][k] for e in earlier]) if np.isfinite([e[0][k] for e in earlier]).any() else np.nan
              for k in cur}
        out["earlier_minimum_cc"] = {k: f(v) for k, v in mn.items()}
        out["change_from_earlier_minimum_cc"] = {k: f(cur[k] - mn[k]) for k in cur}
    else:
        out["previous"] = out["change_from_previous_cc"] = None
        out["earlier_minimum_cc"] = out["change_from_earlier_minimum_cc"] = None
    return out


def mu_cohort(pop, workers):
    d, X = mu_designs(pop)
    n = len(d)
    jobs = [(pop, r, k) for r in range(5) for k in range(5)]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(mu_job, jobs))
    S = {f"{a}_{p}": np.full((5, n), np.nan) for a in ("p", "pc") for p in PW}
    sets = {(kind, p, a, c): np.zeros((5, n), bool) for kind in ("std", "mon") for p in PW for a in ALPHAS for c in (0, 1)}
    ood = [[None] * n for _ in range(5)]
    fold = np.zeros((5, n), int)
    for j in res:
        r, te = j["r"], j["te"]
        fold[r, te] = j["k"]
        for p in PW:
            S[f"p_{p}"][r, te], S[f"pc_{p}"][r, te] = j[f"p_{p}"], j[f"pc_{p}"]
            for a in ALPHAS:
                h0, h1 = cf.prediction_sets(j[f"pc_{p}"], j[f"q_{p}"][a])
                sets[("std", p, a, 0)][r, te], sets[("std", p, a, 1)][r, te] = h0, h1
                q0, q1 = j[f"qm_{p}"][a]
                sets[("mon", p, a, 0)][r, te], sets[("mon", p, a, 1)][r, te] = j[f"pc_{p}"] <= q0, 1 - j[f"pc_{p}"] <= q1
        for i, t in enumerate(te):
            ood[r][t] = j["ood"][i]
    phase, enh = mu_situation(d)
    return {"cohort": "mu", "pop": pop, "d": d, "scan_id": d.scan_id.to_numpy(), "patient_id": d.patient_id.to_numpy(),
            "y": d.label_120.to_numpy(), "S": S, "sets": sets, "ood": ood, "fold": fold, "card_phase": phase,
            "enh": enh, "comp_phase": d.phase.to_numpy(), "own": "mu",
            "eval": {"intended_use": d.label_120.notna().to_numpy() & d.intended_use.to_numpy(),
                     "all_scans": d.label_120.notna().to_numpy()},
            "median_set": d.label_120.notna().to_numpy(), "meas": mu_measurements(d),
            "cal": [(j["r"], j["k"], j["n_cal_scans"], j["n_cal_patients"]) for j in res]}


# ---------------------------------------------------------------- external (locked)
def locked_models(Xmu: dict, d) -> dict:
    """{pathway: (full fit, conformal fit, std q, Mondrian q)} on the MU grade-4 detection training rows."""
    rows = np.arange(len(d))
    y, pid = d.label_120.to_numpy(), d.patient_id.to_numpy()
    proper, cal = cf.patient_split(pid, 0.3, seed=0)
    cr = rows[cal][~np.isnan(y[cal])]
    out = {}
    for p, X in Xmu.items():
        full, conf = _fit(X, d, rows), _fit(X, d, rows[proper])
        out[p] = (full, conf, *_q(conf(X.iloc[cr]), y[cr].astype(int), pid[cr]))
    return out


def _apply(models: dict, Xext: dict, use: dict | None = None):
    """Locked scores, conformal-model scores and sets. use = {pathway: (alt model name, rows mask)} substitutes."""
    n = len(next(iter(Xext.values())))
    S = {f"{a}_{p}": np.full((1, n), np.nan) for a in ("p", "pc") for p in PW}
    sets = {(kind, p, a, c): np.zeros((1, n), bool) for kind in ("std", "mon") for p in PW for a in ALPHAS for c in (0, 1)}
    for p in PW:
        parts = [(p, np.ones(n, bool))]
        if use and p in use:
            alt, m = use[p]
            parts = [(p, ~m), (alt, m)]
        for name, m in parts:
            full, conf, q, qm = models[name]
            pf, pc = full(Xext[name]), conf(Xext[name])
            S[f"p_{p}"][0, m], S[f"pc_{p}"][0, m] = pf[m], pc[m]
            for a in ALPHAS:
                h0, h1 = cf.prediction_sets(pc[m], q[a])
                sets[("std", p, a, 0)][0, m], sets[("std", p, a, 1)][0, m] = h0, h1
                sets[("mon", p, a, 0)][0, m], sets[("mon", p, a, 1)][0, m] = pc[m] <= qm[a][0], 1 - pc[m] <= qm[a][1]
    return S, sets


def lumiere_cohort():
    from prism.config import LUMIERE_ROOT
    from prism.data.lumiere import _week, demographics
    L, LX, _ = D.lumiere_detection()
    dm, X, *_ = D.context("grade4", "primary")
    timg = [c for c in X["T"].columns if c not in D.T_BASE + ["has_prev", "log_days_from_prev"]]
    Xmu = {"timeline": X["T"][D.T_BASE], "images": X["T"][timg], "combined": X["T"], "images_scan": X["T"][VOL3]}
    models = locked_models(Xmu, dm)
    Xl = {"timeline": LX[D.T_BASE], "images": LX[timg], "combined": LX, "images_scan": LX[VOL3]}
    nop = L.prev_scan_id.eq("").to_numpy()
    # check before substitution: T_img on all scans is the card's LUMIERE image score
    t_img_all = models["images"][0](Xl["images"])
    S, sets = _apply(models, Xl, {"images": ("images_scan", nop)})
    dmo = demographics()
    idh = dmo.idh_raw.astype(str).str.strip().str.lower()
    mg = dmo.mgmt_raw.astype(str).str.strip().str.lower()
    dmo["idh"] = np.select([idh.eq("wt"), idh.str.contains("mut")], ["wildtype", "mutant"], "unknown")
    dmo["mgmt"] = np.select([mg.eq("methylated"), mg.eq("not methylated")], ["methylated", "unmethylated"], "unknown")
    mol = L[["patient_id"]].merge(dmo[["patient_id", "idh", "mgmt"]], on="patient_id", how="left")
    mol = mol.fillna("unknown")
    tr = np.where(dm.label_120.notna())[0]
    ood = [ood_flags(LX, mol, ood_ranges(X["T"], tr))]
    # earlier studies for the measurements: same pool as the previous scan of lumiere_detection
    r = pd.read_csv(LUMIERE_ROOT / "LUMIERE-ExpertRating-v202211.csv")
    r.columns = ["patient_id", "date", "lt3m", "nonmeas", "rating", "rationale"]
    r["day"] = r.date.map(_week) * 7
    r["scan_id"] = r.patient_id + "_" + r.date
    vol = D.lumiere_volumes().set_index("scan_id")
    for c, k in (("raw_Enhancing_Core", "et"), ("raw_Necrotic_NonEnhancing", "nc"), ("raw_Edema_Compartment", "snfh")):
        r[k] = vol[c].reindex(r.scan_id).to_numpy() / 1000.0
    r = r[r[["et", "nc", "snfh"]].notna().all(axis=1) & r.rating.astype(str).str.strip().ne("Pre-Op")]
    by = {p: g.sort_values("day") for p, g in r.groupby("patient_id")}
    meas = []
    for t in L.itertuples():
        g = by.get(t.patient_id, r.iloc[:0])
        e = g[g.day < t.day]
        v = lambda a, b, c: {"et": a, "snfh": c, "necrosis_cavity": b}
        meas.append(_meas(v(t.et, t.nc, t.snfh), [(v(x.et, x.nc, x.snfh), t.day - x.day) for x in e.itertuples()],
                          "LUMIERE DeepBraTumIA (enhancing, necrosis + non-enhancing (necrosis and cavity together), "
                          "oedema); volumes in cc"))
    enh = np.array([R.enhancement_state(a, b if p else np.nan) for a, b, p in zip(L.et, L.prev_et, L.prev_scan_id.ne(""))])
    return {"cohort": "lumiere", "pop": "grade4", "d": L, "scan_id": L.scan_id.to_numpy(),
            "patient_id": L.patient_id.to_numpy(), "y": L.label_det.to_numpy(float), "S": S, "sets": sets, "ood": ood,
            "card_phase": np.array(["unknown"] * len(L)), "enh": enh, "comp_phase": np.array(["unknown"] * len(L)),
            "own": "lumiere", "eval": {"all": np.ones(len(L), bool)}, "median_set": np.ones(len(L), bool),
            "meas": meas, "image_model": np.where(nop, "images_scan (3 current volumes; no previous scan)", "T_img"),
            "check_t_img_all": t_img_all, "early_flag": L.early_post_rt.to_numpy()}


def ucsf_cohort():
    d4, A4 = UX.mu_detection("grade4")
    u = UX.ucsf_frame()
    A = UX.ucsf_designs(u, A4)
    keep = (u.timepoint.eq(2) & u.grade4).to_numpy()
    names = {"timeline": "A-Tbase", "images": "A-Ipure", "combined": "A-T"}
    models = locked_models({p: A4[a] for p, a in names.items()}, d4)
    Xu = {p: A[a][keep].reset_index(drop=True) for p, a in names.items()}
    S, sets = _apply(models, Xu)
    uk = u[keep].reset_index(drop=True)
    union = pd.concat([A4["A-T"], A4["A-Ipure"].drop(columns=[c for c in A4["A-Ipure"] if c in A4["A-T"]])], axis=1)
    uu = pd.concat([Xu["combined"], Xu["images"][[c for c in union.columns if c not in Xu["combined"]]]], axis=1)
    tr = np.where(d4.label_120.notna())[0]
    ood = [ood_flags(uu[list(union.columns)], uk, ood_ranges(union, tr))]
    im = pd.read_csv(OUTPUTS / "data" / "ucsf" / "imaging_features.csv").set_index("scan_id")
    meas = []
    for sid, dp in zip(uk.scan_id, uk.days_from_prev):
        s1 = sid.replace("_time2", "_time1")
        v = lambda x: {"et": im.et_cc.get(x, np.nan), "snfh": im.snfh_cc.get(x, np.nan),
                       "necrosis": im.netc_cc.get(x, np.nan), "cavity": im.rc_cc.get(x, np.nan)}
        meas.append(_meas(v(sid), [(v(s1), dp)] if s1 in im.index else [],
                          "UCSF-ALPTDG segmentation (ET, SNFH, NETC, RC); history = scan 1 only"))
    pm30, neg = uk.pos_s2_pm30.eq(1).to_numpy(), uk.primary_neg.to_numpy()
    e2 = im.et_cc.reindex(uk.scan_id).to_numpy(float)
    e1 = im.et_cc.reindex(uk.scan_id.str.replace("_time2", "_time1", regex=False)).to_numpy(float)
    return {"cohort": "ucsf", "pop": "grade4", "d": uk, "scan_id": uk.scan_id.to_numpy(),
            "patient_id": uk.subject_id.to_numpy(), "y": np.where(pm30, 1.0, np.where(neg, 0.0, np.nan)), "S": S,
            "sets": sets, "ood": ood, "card_phase": np.array([R.phase_cell(p) for p in uk.rt_phase]),
            "enh": np.array([R.enhancement_state(a, b) for a, b in zip(e2, e1)]), "comp_phase": uk.rt_phase.to_numpy(),
            "own": "ucsf_locked", "eval": {"scan2_pm30": pm30 | neg}, "median_set": pm30 | neg, "meas": meas,
            "check_scores": {p: S[f"p_{p}"][0] for p in PW}}


# ---------------------------------------------------------------- flags and records
def derive(c: dict, table) -> dict:
    """Per repeat: medians, agreement, flags. Adds c['flags'] {name: (R, n) bool}, c['tier'], c['agree_side']."""
    Rn = c["S"]["p_combined"].shape[0]
    m = c["median_set"]
    med = {p: np.median(c["S"][f"p_{p}"][:, m], axis=1) for p in ("timeline", "images")}
    above = {p: c["S"][f"p_{p}"] > med[p][:, None] for p in med}
    disagree = above["timeline"] != above["images"]
    tier = np.array([R.lookup(table, c["own"], R.cell(ph, e))["tier"] for ph, e in zip(c["card_phase"], c["enh"])])
    oor = np.array([[bool(x) for x in row] for row in c["ood"]])
    conf = c["sets"][("std", "combined", 0.2, 0)] & c["sets"][("std", "combined", 0.2, 1)]
    tf = np.broadcast_to(tier != "tested", (Rn, len(tier)))
    c["flags"] = {"disagree": disagree, "out_of_range": oor, "tier": tf, "conformal": conf,
                  "any": disagree | oor | tf | conf}
    c["tier"], c["medians"] = tier, med
    return c


def set_text(c, kind, p, a, r, i):
    return cf.describe([c["sets"][(kind, p, a, 0)][r, i]], [c["sets"][(kind, p, a, 1)][r, i]])[0]


def provenance(c, i, r=0):
    if c["cohort"] == "mu":
        return {"scores": f"out-of-fold, MU 5 x 5 CV (detection_cohort folds), repeat {r}, outer fold "
                          f"{int(c['fold'][r, i])}; patient not in training",
                "models": {"timeline": "B1 (C2 clinical + timing + treatment), c3 verified ridge, seed = repeat",
                           "images": "I_pure (volumes, morphology / relative intensity, log ratios to the previous "
                                     "scan, ET / lesion ratio to the whole-history minimum)",
                           "combined": "B1 + I_pure"},
                "conformal": f"patient split 70 / 30 inside the outer training fold, seed {10 * r + int(c['fold'][r, i])};"
                             " pathway refitted on the 70%", "population_model": c["pop"]}
    mid = {"lumiere": {"timeline": "Tbase@grade4", "images": str(c["image_model"][i]) if "image_model" in c else "",
                       "combined": "T@grade4"},
           "ucsf": {"timeline": "A-Tbase@grade4", "images": "A-Ipure@grade4", "combined": "A-T@grade4"}}[c["cohort"]]
    return {"scores": "locked MU grade-4 model (fitted once on the MU grade-4 detection training rows: positives + "
                      "primary negatives; c3.BASE_PRE + verified ridge, seed 0), applied once; no refit",
            "models": mid, "conformal": "one MU-calibrated model per pathway (MU patient split 70 / 30, seed 0), "
                                        "applied locked", "population_model": "grade4"}


def build_record(c: dict, i: int, table, atable, r: int = 0) -> dict:
    """One system record (no outcome label)."""
    S = c["S"]
    ph, en = c["card_phase"][i], c["enh"][i]
    reasons = list(c["ood"][r][i])
    card = R.build_card(ph, en, table, c["own"], {"timeline": S["p_timeline"][r, i], "images": S["p_images"][r, i]},
                        {k: float(v[r]) for k, v in c["medians"].items()}, reasons, atable)
    pf = c["flags"]
    flags = {"pathways_disagree": bool(pf["disagree"][r, i]), "out_of_range": bool(pf["out_of_range"][r, i]),
             "out_of_range_reasons": reasons, "tier_flag": bool(pf["tier"][r, i]), "tier": c["tier"][i],
             "conformal_uncertain": bool(pf["conformal"][r, i]), "any_flag": bool(pf["any"][r, i])}
    d = c["d"]
    rec = {"schema": SCHEMA, "record_id": f"{c['cohort']}|{c['pop']}|{c['scan_id'][i]}", "cohort": c["cohort"],
           "scan_id": str(c["scan_id"][i]), "patient_id": str(c["patient_id"][i]), "population": c["pop"],
           "population_flags": {"grade4": bool(d.grade4.iat[i]) if "grade4" in d else True}}
    if c["cohort"] == "mu":
        rec["population_flags"]["intended_use"] = bool(d.intended_use.iat[i])
        rec["phase_of_care"] = str(d.phase.iat[i])
    elif c["cohort"] == "ucsf":
        rec["population_flags"].update({"scan2": True, "gbm_who": bool(d.gbm_who.iat[i])})
        rec["phase_of_care"] = str(d.rt_phase.iat[i])
    else:
        rec["phase_of_care"] = "unknown (no RT dates)"
        rec["rater_flag_within_3_months_after_rt"] = bool(c["early_flag"][i] == 1)
    rec["situation"] = card["situation"]
    rec["scores"] = {p: float(S[f"p_{p}"][r, i]) for p in PW}
    rec["measurements"] = c["meas"][i]
    rec["card"] = card
    rec["conformal"] = {**{f"alpha_{a}": {p: set_text(c, "std", p, a, r, i) for p in PW} for a in ALPHAS},
                        "mondrian_secondary": {f"alpha_{a}": {p: set_text(c, "mon", p, a, r, i) for p in PW}
                                               for a in ALPHAS},
                        "conformal_model_scores": {p: float(S[f"pc_{p}"][r, i]) for p in PW},
                        "method": "patient-level split conformal, score 1 - p(y), set {y : 1 - p(y) <= q}"}
    rec["flags"] = flags
    rec["provenance"] = provenance(c, i, r)
    return rec


def _clean(x):
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def assert_no_label(rec: dict) -> None:
    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                assert k not in LABEL_KEYS, f"label-like key {path}/{k} in a system record"
                walk(v, f"{path}/{k}")
        elif isinstance(o, list):
            for v in o:
                walk(v, path)
    walk(rec)


def write_records(c: dict, table, atable, name: str) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / f".{name}.jsonl.tmp"
    with open(tmp, "w") as fh:
        for i in range(len(c["scan_id"])):
            rec = _clean(build_record(c, i, table, atable))
            assert_no_label(rec)
            fh.write(json.dumps(rec) + "\n")
    tmp.replace(OUT / f"{name}.jsonl")
    ev = pd.DataFrame({"record_id": [f"{c['cohort']}|{c['pop']}|{s}" for s in c["scan_id"]], "scan_id": c["scan_id"],
                       "patient_id": c["patient_id"], "label": c["y"],
                       **{f"eval_{k}": v for k, v in c["eval"].items()}})
    if c["cohort"] == "mu":
        ev["neg_secondary_only"] = c["d"].neg_secondary.to_numpy() & ~c["d"].label_120.notna().to_numpy()
    ev.to_csv(OUT / f"{name}_EVALUATION_ONLY.csv", index=False)
    return len(c["scan_id"])


# ---------------------------------------------------------------- evaluation
def auc_m(y, P, M):
    """Mean over repeats of the AUC of P[r] on rows M[r] (NaN if a class is missing everywhere)."""
    v = [R.auc(y[m], p[m]) for p, m in zip(P, M)]
    return float(np.nanmean(v)) if np.isfinite(v).any() else np.nan


def matched(rng, keep, phase):
    out = np.zeros(len(keep), bool)
    for ph in np.unique(phase):
        pos = np.where(phase == ph)[0]
        n = int(keep[pos].sum())
        if n:
            out[rng.choice(pos, n, replace=False)] = True
    return out


def s3_ref(y, P, K, phase, rng, n):
    """Expected composition-matched AUC over n draws (same per-repeat, per-phase retained counts)."""
    return float(np.nanmean([auc_m(y, P, [matched(rng, k, phase) for k in K]) for _ in range(n)]))


def s3_rand(y, P, K, rng, n):
    return float(np.nanmean([auc_m(y, P, [rng.permutation(k) for k in K]) for _ in range(n)]))


def boot_job(job):
    """Bootstrap draws for S1-S4 of one evaluation set. Each draw i uses rng([SEED, i])."""
    E, draws, n_ref = job
    threadpool_limits(1)
    y, g, P, F, ph, cov, tier, Pb, err = (E[k] for k in ("y", "g", "P", "F", "phase", "cov", "tier", "brier", "err"))
    by = {p: np.where(g == p)[0] for p in np.unique(g)}
    pats = np.array(sorted(by))
    out = []
    for i in draws:
        rng = np.random.default_rng([SEED, i])
        idx = np.concatenate([by[p] for p in rng.choice(pats, len(pats))])
        yi, Pi = y[idx], P[:, idx]
        row = {"cov": {k: float(v[:, idx].mean()) for k, v in cov.items()}}
        for f, M in F.items():
            Mi = M[:, idx]
            un, fl = auc_m(yi, Pi, ~Mi), auc_m(yi, Pi, Mi)
            ref = s3_ref(yi, Pi, ~Mi, ph[idx], rng, n_ref) if n_ref else np.nan
            row[f] = (un, fl, ref)
        for t in ("tested", "few cases", "not tested"):
            m = tier[idx] == t
            row[t] = (float(Pb[:, idx][:, m].mean()) if m.any() else np.nan,
                      float(err[:, idx][:, m].mean()) if m.any() else np.nan)
        out.append(row)
    return out


def ci(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if len(v) else (np.nan, np.nan)


def evaluate_set(c: dict, setname: str, workers: int, n_boot: int, n_ref: int, n_draw: int) -> dict:
    m = c["eval"][setname]
    y, g = c["y"][m].astype(int), c["patient_id"][m]
    P = c["S"]["p_combined"][:, m]
    Rn = P.shape[0]
    F = {f: np.asarray(v)[:, m] for f, v in c["flags"].items()}
    ph, tier, cell = c["comp_phase"][m], c["tier"][m], np.array([f"{a}|{b}" for a, b in zip(c["card_phase"][m],
                                                                                          c["enh"][m])])
    key = {"cohort": c["cohort"], "population": c["pop"], "set": setname, "n_scans": int(m.sum()),
           "n_pos": int(y.sum()), "n_neg": int((y == 0).sum()), "n_patients": int(len(np.unique(g)))}
    # S1 coverage
    cov = {}
    rows_s1 = []
    for kind in ("std", "mon"):
        for p in PW:
            for a in ALPHAS:
                h0, h1 = c["sets"][(kind, p, a, 0)][:, m], c["sets"][(kind, p, a, 1)][:, m]
                hit = np.where(y == 1, h1, h0)
                cov[(kind, p, a)] = hit
                w = 1.0 / pd.Series(g).map(pd.Series(g).value_counts()).to_numpy()
                r_ = {**key, "kind": "standard" if kind == "std" else "mondrian (class-conditional)", "pathway": p,
                      "alpha": a, "coverage": float(hit.mean()), "coverage_patient_weighted": float((hit * w).sum(1).mean() / w.sum()),
                      "coverage_events": float(hit[:, y == 1].mean()) if (y == 1).any() else np.nan,
                      "coverage_non_events": float(hit[:, y == 0].mean()) if (y == 0).any() else np.nan,
                      "singleton_rate": float((h0 ^ h1).mean()), "both_rate": float((h0 & h1).mean()),
                      "empty_rate": float((~h0 & ~h1).mean())}
                rows_s1.append(r_)
    # conditional coverage by card cell and by phase (standard, alpha 0.2 and 0.1)
    cond = []
    for p in PW:
        for a in ALPHAS:
            hit = cov[("std", p, a)]
            for by_name, lab in (("cell", cell), ("phase", ph), ("class", np.where(y == 1, "progression", "no progression"))):
                for v in np.unique(lab):
                    mm = lab == v
                    cond.append({**key, "pathway": p, "alpha": a, "by": by_name, "stratum": v, "n": int(mm.sum()),
                                 "n_pos": int(y[mm].sum()), "coverage": float(hit[:, mm].mean()),
                                 "below_0.78": bool(hit[:, mm].mean() < 0.78)})
    # conformal model AUC (cost of splitting)
    split = [{**key, "pathway": p, "auc_displayed": auc_m(y, c["S"][f"p_{p}"][:, m], np.ones_like(P, bool)),
              "auc_conformal_model": auc_m(y, c["S"][f"pc_{p}"][:, m], np.ones_like(P, bool))} for p in PW]
    # S4 inputs: Brier and error at the cohort-median threshold (median of the combined score over the set, per repeat)
    brier = (P - y) ** 2
    err = ((P > np.median(P, axis=1, keepdims=True)).astype(int) != y).astype(float)
    E = {"y": y, "g": g, "P": P, "F": F, "phase": ph, "cov": cov,
         "tier": tier, "brier": brier, "err": err}
    draws = np.array_split(np.arange(n_boot), workers)
    with ProcessPoolExecutor(workers) as ex:
        B = [r_ for part in ex.map(boot_job, [(E, list(dr), n_ref) for dr in draws]) for r_ in part]
    for r_ in rows_s1:
        k = ("std" if r_["kind"] == "standard" else "mon", r_["pathway"], r_["alpha"])
        lo, hi = ci([b["cov"][k] for b in B]) if k in E["cov"] else (np.nan, np.nan)
        r_.update({"coverage_lo": lo, "coverage_hi": hi})
        if r_["alpha"] == 0.2 and r_["kind"] == "standard":
            r_["S1_met"] = bool(r_["coverage"] >= 0.78)
    # S2 / S3
    rng = np.random.default_rng([SEED, 999_999])
    sel = []
    for f, M in F.items():
        un, fl = auc_m(y, P, ~M), auc_m(y, P, M)
        n_un_pos = min(int(y[~mm].sum()) for mm in M)
        n_un_neg = min(int((y[~mm] == 0).sum()) for mm in M)
        n_fl_pos = min(int(y[mm].sum()) for mm in M)
        n_fl_neg = min(int((y[mm] == 0).sum()) for mm in M)
        est2 = min(n_un_pos, n_un_neg, n_fl_pos, n_fl_neg) > 0
        est3 = min(n_un_pos, n_un_neg) > 0 and M.any()
        ref = s3_ref(y, P, ~M, ph, rng, n_draw) if est3 else np.nan
        rnd = s3_rand(y, P, ~M, rng, n_draw) if est3 else np.nan
        d2 = np.array([b[f][0] - b[f][1] for b in B])
        d3 = np.array([b[f][0] - b[f][2] for b in B])
        lo2, hi2 = ci(d2) if est2 else (np.nan, np.nan)
        lo3, hi3 = ci(d3) if est3 else (np.nan, np.nan)
        sel.append({**key, "flag": f, "flagged_share": float(M.mean()), "n_flagged_mean": float(M.sum(1).mean()),
                    "auc_all": auc_m(y, P, np.ones_like(M)), "auc_unflagged": un if est3 else np.nan,
                    "auc_flagged": fl if est2 else np.nan,
                    "S2_diff": (un - fl) if est2 else np.nan, "S2_lo": lo2, "S2_hi": hi2,
                    "S2_met": (bool(lo2 > 0) if est2 else "n/a"),
                    "auc_composition_matched": ref, "auc_random_removal": rnd,
                    "S3_diff": (un - ref) if est3 else np.nan, "S3_lo": lo3, "S3_hi": hi3,
                    "S3_met": (bool(lo3 > 0) if est3 else "n/a"),
                    "min_unflagged_pos_neg": f"{n_un_pos}/{n_un_neg}", "min_flagged_pos_neg": f"{n_fl_pos}/{n_fl_neg}"})
    tiers = []
    for t in ("tested", "few cases", "not tested"):
        mm = tier == t
        lb, hb = ci([b[t][0] for b in B])
        le, he = ci([b[t][1] for b in B])
        tiers.append({**key, "tier": t, "n_tier": int(mm.sum()), "n_pos_tier": int(y[mm].sum()),
                      "n_neg_tier": int((y[mm] == 0).sum()),
                      "brier": float(brier[:, mm].mean()) if mm.any() else np.nan, "brier_lo": lb, "brier_hi": hb,
                      "error_rate": float(err[:, mm].mean()) if mm.any() else np.nan, "error_lo": le, "error_hi": he})
    return {"conformal": rows_s1, "conformal_conditional": cond, "conformal_split_cost": split, "selective": sel,
            "tiers": tiers}


# ---------------------------------------------------------------- checks
def check_scores(cohorts: dict) -> pd.DataFrame:
    rows = []
    add = lambda k, v: rows.append({"check": "|".join(k), "value": v, "published": EXPECTED[k],
                                    "ok": abs(v - EXPECTED[k]) < 0.0006})
    for pop in ("grade4", "all_glioma"):
        c = cohorts[("mu", pop)]
        pub = pd.read_csv(D.OUT / f"oof_{pop}_primary.csv.gz").set_index("scan_id").reindex(c["scan_id"])
        dev = max(float(np.nanmax(np.abs(pub[f"B1#r{r}"].to_numpy() - c["S"]["p_timeline"][r]))) for r in range(5))
        rows.append({"check": f"mu|{pop}|B1 OOF == detection oof (max dev)", "value": dev, "published": 0.0,
                     "ok": dev < 1e-9})
        if pop == "grade4":
            card = pd.read_csv(RC.OUT / "mu_scores.csv.gz").set_index("scan_id").reindex(c["scan_id"])
            for p, a in (("images", "I_pure"), ("combined", "B1+I_pure")):
                dv = max(float(np.nanmax(np.abs(card[f"{a}#r{r}"].to_numpy() - c["S"][f"p_{p}"][r]))) for r in range(5))
                rows.append({"check": f"mu|grade4|{a} OOF == reliability-card scores (max dev)", "value": dv,
                             "published": 0.0, "ok": dv < 1e-9})
        y = c["y"]
        for s, m in c["eval"].items():
            for p in PW:
                k = ("mu", pop, s, p)
                if k in EXPECTED:
                    add(k, auc_m(y[m].astype(int), c["S"][f"p_{p}"][:, m], np.ones((5, m.sum()), bool)))
    L = cohorts[("lumiere", "grade4")]
    pub = pd.read_csv(D.OUT / "lumiere_predictions.csv").set_index("scan_id").reindex(L["scan_id"])
    for p, a in (("timeline", "Tbase@grade4"), ("combined", "T@grade4")):
        dv = float(np.abs(pub[a].to_numpy() - L["S"][f"p_{p}"][0]).max())
        rows.append({"check": f"lumiere|{a} == published locked predictions (max dev)", "value": dv, "published": 0.0,
                     "ok": dv < 1e-9})
        add(("lumiere", "grade4", "all", p), R.auc(L["y"].astype(int), L["S"][f"p_{p}"][0]))
    add(("lumiere", "grade4", "all", "images_T_img_all_scans"), R.auc(L["y"].astype(int), L["check_t_img_all"]))
    U = cohorts[("ucsf", "grade4")]
    sc = pd.read_csv(RESULTS / "analyses" / "ucsf" / "locked" / "scores.csv").set_index("scan_id").reindex(U["scan_id"])
    m = U["eval"]["scan2_pm30"]
    for p, a in (("timeline", "A-Tbase@grade4"), ("images", "A-Ipure@grade4"), ("combined", "A-T@grade4")):
        dv = float(np.abs(sc[a].to_numpy() - U["S"][f"p_{p}"][0]).max())
        rows.append({"check": f"ucsf|{a} == published locked scores (max dev)", "value": dv, "published": 0.0,
                     "ok": dv < 1e-9})
        add(("ucsf", "grade4", "scan2", p), R.auc(U["y"][m].astype(int), U["S"][f"p_{p}"][0][m]))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- main
def build(workers):
    t0 = time.time()
    cohorts = {("mu", p): mu_cohort(p, workers) for p in D.POPS}
    print(f"MU scores {time.time() - t0:.0f}s", flush=True)
    cohorts[("lumiere", "grade4")] = lumiere_cohort()
    cohorts[("ucsf", "grade4")] = ucsf_cohort()
    print(f"external scores {time.time() - t0:.0f}s", flush=True)
    ch = check_scores(cohorts)
    OUT.mkdir(parents=True, exist_ok=True)
    ch.to_csv(OUT / "checks.csv", index=False)
    print(ch.to_string(index=False), flush=True)
    assert ch.ok.all(), "scores do not reproduce the published values; stopping before any evaluation"
    return cohorts


NAMES = {("mu", "grade4"): "records_mu", ("mu", "all_glioma"): "records_mu_all_glioma",
         ("lumiere", "grade4"): "records_lumiere", ("ucsf", "grade4"): "records_ucsf"}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="system", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--n-ref", type=int, default=N_REF)
    ap.add_argument("--n-draw", type=int, default=N_DRAW)
    ap.add_argument("--no-evaluate", action="store_true")
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    t0 = time.time()
    (OUT / "RECORDS_READY").unlink(missing_ok=True)
    cohorts = build(a.workers)
    table, atable = RC.load_table()
    for k, c in cohorts.items():
        derive(c, table)
        n = write_records(c, table, atable, NAMES[k])
        print(f"{NAMES[k]}: {n} records {time.time() - t0:.0f}s", flush=True)
    from prism.audit.provenance import git_state
    (OUT / "RECORDS_READY").write_text(json.dumps({"schema": SCHEMA, "git": git_state(), "files": {
        NAMES[k]: len(c["scan_id"]) for k, c in cohorts.items()}, "written": time.strftime("%Y-%m-%d %H:%M:%S")},
        indent=1))
    if a.no_evaluate:
        return
    sets = [(("mu", "grade4"), "intended_use"), (("mu", "all_glioma"), "intended_use"), (("lumiere", "grade4"), "all"),
            (("ucsf", "grade4"), "scan2_pm30")]
    T = {}
    for k, s in sets:
        res = evaluate_set(cohorts[k], s, a.workers, a.n_boot, a.n_ref, a.n_draw)
        for name, rows in res.items():
            T.setdefault(name, []).extend(rows)
        print(f"evaluated {k} {s} {time.time() - t0:.0f}s", flush=True)
    for name, rows in T.items():
        pd.DataFrame(rows).to_csv(OUT / f"{name}.csv", index=False)
    pd.set_option("display.width", 250)
    cols = ["cohort", "population", "pathway", "alpha", "coverage", "coverage_lo", "coverage_hi", "coverage_events",
            "coverage_non_events", "singleton_rate"]
    cv = pd.DataFrame(T["conformal"])
    print(cv[cv.kind == "standard"][cols].round(3).to_string(index=False))
    print(pd.DataFrame(T["conformal_split_cost"]).round(3).to_string(index=False))
    print(pd.DataFrame(T["selective"]).drop(columns=["set"]).round(3).to_string(index=False))
    print(pd.DataFrame(T["tiers"]).round(3).to_string(index=False))
    info = {"n_boot": a.n_boot, "n_ref": a.n_ref, "n_draw": a.n_draw, "seed": SEED, "seconds": round(time.time() - t0),
            "calibration_sizes_mu": {p: cohorts[("mu", p)]["cal"] for p in D.POPS}}
    (OUT / "run_info.json").write_text(json.dumps(_clean(info), indent=1))


if __name__ == "__main__":
    main()
