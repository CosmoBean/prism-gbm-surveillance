"""Detection of progression at the scan: does this MRI show progression? (tabular arms, deep-arm stacking, LUMIERE)

ANALYSIS PLAN: docs/results/DETECTION_TASK.md, section "Plan (pre-specified)", committed (2b4c927) before any model in
this study saw a real label; snapshotted to outputs/results/analyses/detection/PLAN_snapshot.md by the first run.

Unit (MU-Glioma-Post): scans of diagnostics_imaging.scan_table with complete sequences and a mask.
  positive  the progression scan (first MRI with a mask on/after the documented progression date)
  negative  primary: index scans with a verified 120-day non-event (label_120 == 0); secondary: every index scan
  folds     the shared 5 x 5 folds (patient's fold); patients absent from folds.csv are excluded and counted
Arms (ridge = c3 BASE_PRE + verified ridge with inner patient-grouped C, audit.model.fit_pipeline, seed = repeat):
  B0   clinical with the C2 rules (no unknown indicators, markers masked before diagnosis)
  B1   the C2 design (clinical + timing + treatment, as-of early_post_rt)              <- baseline
  P    B1 + imaging measurements (volumes, morphology, change from the previous scan, nadir ratio since RT end,
       has-previous flag)                                                              <- PRIMARY
  P+R  P + radiomics, nested over c3.RAD_CONFIGS (inner patient-grouped AUC)
  I    imaging measurements alone
Evaluation: plain AUC, mean over repeats of the pooled held-out AUC, paired patient-cluster bootstrap (1,000 draws).
Primary: grade 4, trained on all detection scans (positives + primary negatives), evaluated on intended-use scans.

    python -m prism detection [--workers 32] [--n-boot 1000] [--cohort-only] [--deep-only]
    -> $PRISM_OUTPUTS/data/detection_cohort.csv (+ _README.md)
       $PRISM_OUTPUTS/results/analyses/detection/
"""

from __future__ import annotations

import argparse
import json
import os
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

import numpy as np
import pandas as pd

from prism.analyses.diagnostics_imaging import scan_table
from prism.analyses.phase_ladder import phase_label
from prism.config import EARLY_POST_RT_DAYS, FOLDS, MEASUREMENTS, OUTPUTS, REPO, RESULTS
from prism.data.mu import idh_status, load_cohort, load_index, mgmt_status

H = 120
OUT = RESULTS / "analyses" / "detection"
COHORT_CSV = OUTPUTS / "data" / "detection_cohort.csv"
COHORT_README = OUTPUTS / "data" / "detection_cohort_README.md"
_num = lambda s: pd.to_numeric(s, errors="coerce")


# ---------------------------------------------------------------- cohort
def _write_atomic(df_or_text, path):
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    if isinstance(df_or_text, pd.DataFrame):
        df_or_text.to_csv(tmp, index=False)
    else:
        tmp.write_text(df_or_text)
    os.replace(tmp, path)


def detection_frame(index: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Cohort-like frame (one row per detection scan, the columns the tabular feature functions need) + counts.

    Rows: progression scans (complete, mask) and every index scan (mu_cohort). Index-scan rows are copied from the
    cohort (same derivations); progression-scan rows are derived from the index with build_cohort's rules."""
    index = load_index() if index is None else index
    s = scan_table(index)
    cohort = load_cohort("all_glioma")
    prog = s[s.is_progression_scan & s.has_meas & s.complete.astype(bool)]
    assert not prog.scan_id.isin(cohort.scan_id).any(), "a progression scan is also an index scan"
    ix = index.set_index("scan_id").loc[prog.scan_id].reset_index()
    p = pd.DataFrame({"scan_id": ix.scan_id, "patient_id": ix.patient_id, "timepoint": ix.timepoint})
    p["days_from_diagnosis_to_mri"] = _num(ix.days_from_diagnosis_to_mri)
    rt_end = _num(ix.clinical_number_of_days_from_diagnosis_to_radiation_therapy_end_date)
    p["days_since_rt_end"] = (p.days_from_diagnosis_to_mri - rt_end).where(rt_end.notna())
    p["early_post_rt"] = p.days_since_rt_end.between(0, EARLY_POST_RT_DAYS).astype(float).where(rt_end.notna())
    n_idx = cohort.groupby("patient_id").size()
    p["visit_index"] = n_idx.reindex(p.patient_id).fillna(0).astype(int).to_numpy() + 1
    p["grade4"] = ix.clinical_grade_of_primary_brain_tumor.astype(str).str.strip().eq("4").to_numpy()
    p["idh"] = idh_status(ix.clinical_idh1_mutation, ix.clinical_idh2_mutation).to_numpy()
    p["mgmt"] = mgmt_status(ix.clinical_mgmt_methylation).to_numpy()
    p["age"] = _num(ix.clinical_age_at_diagnosis).to_numpy()
    p["male"] = ix.clinical_sex_at_birth.eq("Male").astype(int).to_numpy()
    p["label_120_forward"] = np.nan
    p["label_det"] = 1
    p["neg_primary"] = False
    p["neg_secondary"] = False
    keep = list(p.columns.drop(["label_120_forward", "label_det", "neg_primary", "neg_secondary"]))
    c = cohort[keep + ["label_120"]].rename(columns={"label_120": "label_120_forward"}).copy()
    c["label_det"] = 0
    c["neg_primary"] = c.label_120_forward.eq(0)
    c["neg_secondary"] = True
    d = pd.concat([p, c], ignore_index=True)
    d["mri_day"] = d.days_from_diagnosis_to_mri

    # previous MRI: most recent strictly earlier MRI of the patient with complete sequences and a mask
    q = s[s.complete.astype(bool) & s.has_meas][["scan_id", "patient_id", "mri_day"]]
    by_pat = {k: g.sort_values("mri_day") for k, g in q.groupby("patient_id")}
    prev_id, prev_day = [], []
    for sid, pid, day in zip(d.scan_id, d.patient_id, d.mri_day):
        g = by_pat.get(pid)
        g = g[g.mri_day < day] if g is not None else g
        if g is None or not len(g):
            prev_id.append("")
            prev_day.append(np.nan)
        else:
            prev_id.append(g.scan_id.iat[-1])
            prev_day.append(g.mri_day.iat[-1])
    d["prev_scan_id"] = prev_id
    d["days_from_prev"] = d.mri_day - np.array(prev_day, float)
    assert (d.days_from_prev.dropna() > 0).all(), "previous scan not strictly earlier"

    d["phase"] = phase_label(d)
    d["intended_use"] = d.phase.ne("pre_rt")
    folds = pd.read_csv(FOLDS)
    pf = folds.drop_duplicates(["patient_id", "repeat"]).pivot(index="patient_id", columns="repeat", values="fold")
    assert (folds.groupby(["patient_id", "repeat"]).fold.nunique() == 1).all()
    in_folds = d.patient_id.isin(pf.index)
    counts = {"excluded_scans_not_in_folds": int((~in_folds).sum()),
              "excluded_patients_not_in_folds": int(d.loc[~in_folds, "patient_id"].nunique()),
              "excluded_progression_scans_not_in_folds": int((~in_folds & d.label_det.eq(1)).sum()),
              "excluded_grade4_patients_not_in_folds": int(d.loc[~in_folds & d.grade4, "patient_id"].nunique())}
    d = d[in_folds].reset_index(drop=True)
    for r in pf.columns:
        d[f"fold_r{r}"] = pf[r].reindex(d.patient_id).astype(int).to_numpy()
    # index scans must inherit exactly the folds.csv scan-level fold
    fs = folds.pivot(index="scan_id", columns="repeat", values="fold")
    ci = d.label_det.eq(0)
    for r in pf.columns:
        assert (fs[r].reindex(d.scan_id[ci]).to_numpy() == d.loc[ci, f"fold_r{r}"].to_numpy()).all()
    return d.sort_values(["patient_id", "mri_day"]).reset_index(drop=True), counts


COHORT_COLS = ["scan_id", "patient_id", "grade4", "label_det", "neg_primary", "neg_secondary", "intended_use", "phase",
               "prev_scan_id", "days_from_prev", "fold_r0", "fold_r1", "fold_r2", "fold_r3", "fold_r4"]


def write_cohort() -> pd.DataFrame:
    d, counts = detection_frame()
    COHORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(d[COHORT_COLS + ["mri_day"]], COHORT_CSV)
    rows = []
    for pop, m in (("grade4", d.grade4), ("all_glioma", np.ones(len(d), bool))):
        for iu_name, iu in (("all", np.ones(len(d), bool)), ("intended_use", d.intended_use),
                            ("pre_rt", ~d.intended_use)):
            x = d[m & iu]
            rows.append(f"| {pop} | {iu_name} | {int(x.label_det.sum())} | {int(x.neg_primary.sum())} | "
                        f"{int(x.neg_secondary.sum())} | {x.patient_id.nunique()} | "
                        f"{int((x.prev_scan_id != '').sum())} |")
    ph = d.groupby(["grade4", "phase", "label_det"]).size().unstack(fill_value=0)
    text = f"""# detection_cohort.csv

Written by `python -m prism detection --cohort-only` (prism/analyses/detection.py), plan
docs/results/DETECTION_TASK.md (commit 2b4c927). One row per detection scan of MU-Glioma-Post, all gliomas.

Columns
- scan_id, patient_id; grade4 (WHO grade 4); mri_day (days from diagnosis to the MRI)
- label_det: 1 = progression scan (diagnostics_imaging.scan_table `is_progression_scan`: first MRI with a mask on or
  after the documented progression date; complete sequences and a mask required), 0 = index scan (mu_cohort.csv)
- neg_primary: index scan with a verified 120-day non-event (label_120 == 0: stable >= 120 days afterwards)
- neg_secondary: any index scan (all are before progression), whatever the follow-up (neg_primary is a subset)
- Primary training/evaluation rows: label_det == 1 or neg_primary. Secondary: label_det == 1 or neg_secondary.
- intended_use: RT started by the scan day (phase_ladder.phase_label != pre_rt, as in INTENDED_USE.md)
- phase: pre_rt | during_rt | early_post_rt (<= 84 d after RT end) | later_post_rt (as of the scan day)
- prev_scan_id: most recent strictly earlier MRI of the same patient with complete sequences and a mask (any MRI of
  the index, not only detection scans; empty if none); days_from_prev = mri_day - its mri_day
- fold_r0..fold_r4: the patient's fold in each repeat of outputs/data/folds.csv (index scans: identical to their
  folds.csv row, asserted)

Exclusions: patients absent from folds.csv (no index scan): {counts['excluded_patients_not_in_folds']} patients,
{counts['excluded_scans_not_in_folds']} scans (all progression scans: {counts['excluded_progression_scans_not_in_folds']};
grade-4 patients: {counts['excluded_grade4_patients_not_in_folds']}).

Counts (positives / primary negatives / secondary negatives / patients / scans with a previous scan)

| population | set | positives | neg primary | neg secondary | patients | with prev |
|---|---|---|---|---|---|---|
""" + "\n".join(rows) + "\n\nBy phase (rows: grade4, phase; columns: label_det)\n\n```\n" + ph.to_string() + "\n```\n"
    _write_atomic(text, COHORT_README)
    print(text, flush=True)
    return d




# ---------------------------------------------------------------- features (as of the scan day; past scans only)
VOLS = ("et", "netc", "snfh", "rc", "tumor", "lesion")
EPS = 0.1


@lru_cache(maxsize=1)
def _base():
    index = load_index()
    d, counts = detection_frame(index)
    s = scan_table(index)
    pool = s[s.complete.astype(bool) & s.has_meas][["scan_id", "patient_id", "mri_day"]]
    meas = pd.read_csv(MEASUREMENTS)
    meas = meas[meas.scan_id.isin(pool.scan_id)].reset_index(drop=True)
    assert np.allclose(meas.set_index("scan_id").mri_day.reindex(pool.scan_id).to_numpy(), pool.mri_day.to_numpy())
    return index, d, counts, meas


def change_nadir(d: pd.DataFrame, index: pd.DataFrame, meas: pd.DataFrame) -> pd.DataFrame:
    """Change from the previous complete+masked MRI and log ratio to the ET / lesion nadir since RT end.
    `meas` is the pool of earlier scans (measurements of complete+masked MRIs); only rows dated <= the scan are used."""
    from prism.analyses.triage_feasibility import trajectory
    by_pat = {p: g.sort_values("mri_day") for p, g in meas.groupby("patient_id")}
    rows = []
    for sid, pid, day in zip(d.scan_id, d.patient_id, d.mri_day):
        g = by_pat[pid]
        cur = g[g.scan_id == sid]
        assert len(cur) == 1, sid
        prev = g[g.mri_day < day]
        r = {"has_prev": float(len(prev) > 0), "prev_scan_id_used": prev.scan_id.iat[-1] if len(prev) else ""}
        if len(prev):
            p = prev.iloc[-1]
            assert p.mri_day < day
            r["log_days_from_prev"] = float(np.log1p(day - p.mri_day))
            for v in VOLS:
                r[f"logratio_prev_{v}"] = float(np.log((cur[f"{v}_cc"].iat[0] + EPS) / (p[f"{v}_cc"] + EPS)))
        else:
            r["log_days_from_prev"] = 0.0
            r.update({f"logratio_prev_{v}": 0.0 for v in VOLS})
        rows.append(r)
    out = pd.DataFrame(rows, index=d.index)
    tr = trajectory(d, index, meas)  # asserts its history is dated <= the scan day
    out["logratio_nadir_et"] = tr.traj_logratio_nadir_et.to_numpy()
    out["logratio_nadir_lesion"] = tr.traj_logratio_nadir_lesion.to_numpy()
    return out


def leakage_check(d, index, meas, F) -> float:
    """Recompute every scan's change/nadir features with all of the patient's later scans deleted: must be identical."""
    dev = 0.0
    for j in range(len(d)):
        row = d.iloc[[j]]
        m = meas[~((meas.patient_id == row.patient_id.iat[0]) & (meas.mri_day > row.mri_day.iat[0]))]
        f = change_nadir(row, index, m).iloc[0]
        a, b = f.drop("prev_scan_id_used").to_numpy(float), F.iloc[j].drop("prev_scan_id_used").to_numpy(float)
        assert f.prev_scan_id_used == F.prev_scan_id_used.iat[j]
        dev = max(dev, float(np.nanmax(np.abs(a - b), initial=0.0)))
        assert np.array_equal(np.isnan(a), np.isnan(b))
    assert dev == 0.0, f"previous-scan features depend on later scans (max dev {dev})"
    return dev


def masked_clinical(d):
    from prism.analyses.phase_censoring import masked_molecular
    m = masked_molecular(d, 0.0)
    return pd.DataFrame({"age": d.age.to_numpy(float), "male": d.male.to_numpy(float),
                         "idh_mutant": m.idh_mutant.to_numpy(), "mgmt_methylated": m.mgmt_methylated.to_numpy()},
                        index=d.index)


def transport_mu(d, F):
    """Transportable P (LUMIERE has no treatment dates): clinical, log days since surgery, as-of early post-RT flag,
    harmonised volumes (SHARED: et, necrosis+cavity, snfh) and their change from the previous scan."""
    from prism.analyses.phase_censoring import asof_early_post_rt
    from prism.features.tabular import treatment
    m = pd.read_csv(MEASUREMENTS).set_index("scan_id")
    cur = m.reindex(d.scan_id)
    X = masked_clinical(d)
    X["log_days_since_surgery"] = np.log1p((d.mri_day - treatment(d).surgery_day).clip(lower=0)).to_numpy()
    X["early_post_rt"] = asof_early_post_rt(d)
    nc = (cur.netc_cc + cur.rc_cc).to_numpy()
    X["log_et_cc"], X["log_necrosis_cavity_cc"], X["log_snfh_cc"] = (np.log1p(cur.et_cc.to_numpy()), np.log1p(nc),
                                                                     np.log1p(cur.snfh_cc.to_numpy()))
    prev = m.reindex(F.prev_scan_id_used.replace("", np.nan))
    hp = F.has_prev.to_numpy() == 1
    lr = lambda a, b: np.where(hp, np.log((a + EPS) / (b + EPS)), 0.0)
    X["has_prev"] = F.has_prev.to_numpy()
    X["log_days_from_prev"] = F.log_days_from_prev.to_numpy()
    X["logratio_prev_et"] = lr(cur.et_cc.to_numpy(), prev.et_cc.to_numpy())
    X["logratio_prev_necrosis_cavity"] = lr(nc, (prev.netc_cc + prev.rc_cc).to_numpy())
    X["logratio_prev_snfh"] = lr(cur.snfh_cc.to_numpy(), prev.snfh_cc.to_numpy())
    return X


T_BASE = ["age", "male", "idh_mutant", "mgmt_methylated", "log_days_since_surgery", "early_post_rt"]
ARMS = ("B0", "B1", "P", "I", "T", "Tbase")
POPS = ("grade4", "all_glioma")
NEGSETS = ("primary", "secondary")


@lru_cache(maxsize=8)
def context(pop: str, negset: str):
    """(frame with label_120 := training label for this negative set, designs, radiomics dict, eroded radiomics)."""
    from prism.analyses import phase_censoring as pc
    from prism.config import RADIOMICS, RADIOMICS_ERODED
    from prism.features.radiomics import legacy_features
    from prism.features.tabular import measurement_groups
    index, d, _, meas = _base()
    d = d[d.grade4].reset_index(drop=True) if pop == "grade4" else d.copy()
    neg = d.neg_primary if negset == "primary" else d.neg_secondary
    d["label_120"] = np.where(d.label_det.eq(1), 1.0, np.where(neg, 0.0, np.nan))
    F = change_nadir(d, index, meas)
    assert (F.prev_scan_id_used.to_numpy() == d.prev_scan_id.fillna("").to_numpy()).all()
    mg = measurement_groups(d)
    img = pd.concat([mg["volumes"], mg["morphology"], F.drop(columns="prev_scan_id_used")], axis=1)
    b1, _ = pc.arm_design("C2", d, index)
    T = transport_mu(d, F)
    X = {"B0": masked_clinical(d), "B1": b1, "P": pd.concat([b1, img], axis=1), "I": img, "T": T, "Tbase": T[T_BASE]}
    v2 = pd.read_csv(RADIOMICS).set_index("scan_id").reindex(d.scan_id)
    er = pd.read_csv(RADIOMICS_ERODED).set_index("scan_id").reindex(d.scan_id)
    v2.index = er.index = d.index
    pair = lambda c: c.startswith(("t1c_", "flair_"))
    shape_cols = [c for c in v2.columns if not c.startswith(("t1c_", "flair_", "t1_", "t2_"))]
    rad = {"legacy": legacy_features(d).astype(float),
           "v2_lesion": v2[[c for c in v2.columns if pair(c) and c.split("_")[1] == "lesion"]],
           "v2_compartments": v2[[c for c in v2.columns if pair(c)] + shape_cols], "v2_all4": v2}
    return d, X, rad, er, F


def fold_ids(d, r):
    return d[f"fold_r{r}"].to_numpy()


def cv_job(job):
    from threadpoolctl import threadpool_limits
    from prism.experiments import c3_radiomics as c3
    pop, negset, arm, r, k = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, X, rad, er, _ = context(pop, negset)
    f = fold_ids(d, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    if arm == "P+R":
        scores = {c: c3.inner_auc(c, d, X["P"], rad, er, tr) for c in c3.RAD_CONFIGS}
        best = max(scores, key=scores.get)
        return job, te, c3.fit_predict(best, d, X["P"], rad, er, tr, te, seed=r), "|".join(map(str, best))
    return job, te, c3.fit_predict(c3.BASELINES[0], d, X[arm], {}, None, tr, te, seed=r), ""


# ---------------------------------------------------------------- evaluation
def aucs(y, P, strata=None):
    """Plain AUC (ties 1/2) of each row of P; with strata, only case-control pairs within a stratum (pooled)."""
    P = np.atleast_2d(P)
    strata = np.zeros(len(y)) if strata is None else np.asarray(strata)
    num, den = np.zeros(len(P)), 0.0
    for s in np.unique(strata):
        m = strata == s
        c, n = m & (y == 1), m & (y == 0)
        if not c.any() or not n.any():
            continue
        den += c.sum() * n.sum()
        for i, p in enumerate(P):
            pk = np.sort(p[n])
            lo = np.searchsorted(pk, p[c] - 1e-12, side="left")
            hi = np.searchsorted(pk, p[c] + 1e-12, side="right")
            num[i] += (lo + 0.5 * (hi - lo)).sum()
    return num / den if den else np.full(len(P), np.nan)


def bootstrap(y, oofs: dict, groups, n_boot=1000, seed=20261021, strata=None, subsets: dict | None = None):
    """Paired patient-cluster bootstrap. Returns point and draws {(arm, subset): value}; value = mean over repeats."""
    subsets = {"all": np.ones(len(y), bool), **(subsets or {})}
    arms = list(oofs)

    def stat(idx):
        out = {}
        for sn, m in subsets.items():
            ii = idx[m[idx]]
            for a in arms:
                out[(a, sn)] = float(np.mean(aucs(y[ii], oofs[a][:, ii])))
            if strata is not None and sn == "all":
                for a in arms:
                    out[(a, "phase_stratified")] = float(np.mean(aucs(y[ii], oofs[a][:, ii], strata[ii])))
        return out
    point = stat(np.arange(len(y)))
    by = {g: np.where(groups == g)[0] for g in np.unique(groups)}
    pats = np.array(list(by))
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        idx = np.concatenate([by[p] for p in rng.choice(pats, len(pats))])
        draws.append(stat(idx))
    return point, {k: np.array([dr[k] for dr in draws]) for k in point}


def ci(x):
    x = x[np.isfinite(x)]
    return (float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))) if len(x) else (np.nan, np.nan)


MIN_STRATUM = 10
CONTRASTS = [("P", "B1"), ("B1", "B0"), ("P", "B0"), ("P+R", "P"), ("P+R", "B1"), ("I", "B1"), ("T", "Tbase"),
             ("P", "T")]


def evaluate_set(name, d, rows, oofs, n_boot, contrasts=CONTRASTS, seed=20261021):
    y = d.label_det.to_numpy()[rows]
    g = d.patient_id.to_numpy()[rows]
    oo = {a: o[:, rows] for a, o in oofs.items()}
    ph = d.phase.to_numpy()[rows]
    subsets = {f"phase={p}": ph == p for p in sorted(set(ph))}
    pt, dr = bootstrap(y, oo, g, n_boot, seed, strata=ph, subsets=subsets)
    res, con, wp = [], [], []
    base = {"set": name, "n_scans": int(len(y)), "n_pos": int(y.sum()), "n_neg": int((y == 0).sum()),
            "n_patients": int(len(np.unique(g)))}
    for a in oo:
        lo, hi = ci(dr[(a, "all")])
        res.append({**base, "arm": a, "auc": pt[(a, "all")], "auc_lo": lo, "auc_hi": hi,
                    "auc_repeat_sd": float(np.std(aucs(y, oo[a]))), "p_le_half": float(np.mean(dr[(a, "all")] <= 0.5))})
    for a, b in contrasts:
        if a in oo and b in oo:
            for sn in ("all", "phase_stratified"):
                x = dr[(a, sn)] - dr[(b, sn)]
                lo, hi = ci(x)
                con.append({**base, "subset": sn, "contrast": f"{a} - {b}", "arm": a, "reference": b,
                            "diff": pt[(a, sn)] - pt[(b, sn)], "diff_lo": lo, "diff_hi": hi,
                            "p_le0": float(np.mean(x <= 0))})
    for sn in list(subsets) + ["phase_stratified"]:
        m = subsets.get(sn)
        npos = int(y[m].sum()) if m is not None else int(y.sum())
        nneg = int((y[m] == 0).sum()) if m is not None else int((y == 0).sum())
        rep = m is None or (npos >= MIN_STRATUM and nneg >= MIN_STRATUM)
        for a in oo:
            lo, hi = ci(dr[(a, sn)]) if rep else (np.nan, np.nan)
            wp.append({"set": name, "arm": a, "phase": sn.replace("phase=", ""), "n_pos": npos, "n_neg": nneg,
                       "auc": pt[(a, sn)], "auc_lo": lo, "auc_hi": hi, "descriptive_only": not rep})
    return res, con, wp


def eval_sets(d, negset):
    pos = d.label_det.eq(1).to_numpy()
    prim = pos | d.neg_primary.to_numpy()
    sec = pos | d.neg_secondary.to_numpy()
    iu = d.intended_use.to_numpy()
    ev = prim if negset == "primary" else sec
    out = {"intended_use": ev & iu, "all_scans": ev}
    if negset == "primary":  # primary-trained model scored on the secondary negatives
        out["intended_use|secondary_negatives"] = sec & iu
        out["all_scans|secondary_negatives"] = sec
        out["intended_use|with_previous"] = ev & iu & d.prev_scan_id.fillna("").ne("").to_numpy()
    return out


# ---------------------------------------------------------------- LUMIERE (locked external test)
LUMIERE_VOLS_CACHE = OUTPUTS / "features" / "lumiere_deepbratumia_volumes_all_studies.csv"


def lumiere_volumes() -> pd.DataFrame:
    from prism.data.lumiere import deepbratumia_volumes
    if not LUMIERE_VOLS_CACHE.exists():
        _write_atomic(deepbratumia_volumes(), LUMIERE_VOLS_CACHE)
    return pd.read_csv(LUMIERE_VOLS_CACHE)


def lumiere_detection() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Positive: first study rated PD; negatives: earlier studies rated SD/PR/CR. Features as transport_mu.
    Previous scan: most recent strictly earlier post-operative study (not rated Pre-Op) with a usable segmentation."""
    from prism.config import LUMIERE_ROOT
    from prism.data.lumiere import _week, demographics
    r = pd.read_csv(LUMIERE_ROOT / "LUMIERE-ExpertRating-v202211.csv")
    r.columns = ["patient_id", "date", "lt3m", "nonmeas", "rating", "rationale"]
    r["rating"] = r.rating.astype(str).str.strip()
    r["day"] = r.date.map(_week) * 7
    r["scan_id"] = r.patient_id + "_" + r.date
    vol = lumiere_volumes().set_index("scan_id")
    for c in ("raw_Enhancing_Core", "raw_Necrotic_NonEnhancing", "raw_Edema_Compartment"):
        r[c] = vol[c].reindex(r.scan_id).to_numpy() / 1000.0 if c in vol else np.nan
    r["has_seg"] = r[["raw_Enhancing_Core", "raw_Necrotic_NonEnhancing", "raw_Edema_Compartment"]].notna().all(axis=1)
    rows = []
    for pid, g in r.sort_values(["patient_id", "day", "date"]).groupby("patient_id"):
        pdi = g.index[g.rating.str.contains("PD")]
        first = g.loc[pdi[0]] if len(pdi) else None
        for i, t in g.iterrows():
            if first is not None and i == pdi[0]:
                lab = 1
            elif t.rating in ("SD", "PR", "CR") and (first is None or t.day < first.day):
                lab = 0
            else:
                continue
            pool = g[(g.day < t.day) & g.has_seg & g.rating.ne("Pre-Op")]
            p = pool.iloc[-1] if len(pool) else None
            rows.append({"scan_id": t.scan_id, "patient_id": pid, "day": t.day, "rating": t.rating, "label_det": lab,
                         "early_post_rt": float(t.lt3m == "x"), "et": t.raw_Enhancing_Core,
                         "nc": t.raw_Necrotic_NonEnhancing, "snfh": t.raw_Edema_Compartment,
                         "prev_scan_id": p.scan_id if p is not None else "",
                         "days_from_prev": t.day - p.day if p is not None else np.nan,
                         "prev_et": p.raw_Enhancing_Core if p is not None else np.nan,
                         "prev_nc": p.raw_Necrotic_NonEnhancing if p is not None else np.nan,
                         "prev_snfh": p.raw_Edema_Compartment if p is not None else np.nan})
    L = pd.DataFrame(rows)
    assert (L.days_from_prev.dropna() > 0).all(), "LUMIERE previous scan not strictly earlier"
    dm = demographics()
    idh = dm.idh_raw.astype(str).str.strip().str.lower()
    mg = dm.mgmt_raw.astype(str).str.strip().str.lower()
    dm["idh_mutant"] = idh.str.contains("mut").astype(float)
    dm["mgmt_methylated"] = mg.eq("methylated").astype(float)
    dm["male"] = dm.sex.astype(str).str.lower().eq("male").astype(float)
    L = L.merge(dm[["patient_id", "age", "male", "idh_mutant", "mgmt_methylated"]], on="patient_id", how="left")
    hp = L.prev_scan_id.ne("")
    lr = lambda a, b: np.where(hp, np.log((a + EPS) / (b + EPS)), 0.0)
    X = pd.DataFrame({"age": L.age.astype(float), "male": L.male, "idh_mutant": L.idh_mutant,
                      "mgmt_methylated": L.mgmt_methylated, "log_days_since_surgery": np.log1p(L.day.clip(lower=0)),
                      "early_post_rt": L.early_post_rt, "log_et_cc": np.log1p(L.et), "log_necrosis_cavity_cc": np.log1p(L.nc),
                      "log_snfh_cc": np.log1p(L.snfh), "has_prev": hp.astype(float),
                      "log_days_from_prev": np.log1p(L.days_from_prev.fillna(0)),
                      "logratio_prev_et": lr(L.et, L.prev_et), "logratio_prev_necrosis_cavity": lr(L.nc, L.prev_nc),
                      "logratio_prev_snfh": lr(L.snfh, L.prev_snfh)})
    info = {"n_scans": len(L), "n_pos": int(L.label_det.sum()), "n_neg": int((L.label_det == 0).sum()),
            "n_patients": int(L.patient_id.nunique()), "n_pos_patients_without_negatives": int(
                (L.groupby("patient_id").label_det.agg(lambda v: (v == 1).any() and not (v == 0).any())).sum()),
            "n_without_segmentation": int(L[["et", "nc", "snfh"]].isna().any(axis=1).sum()),
            "n_with_previous": int(hp.sum()), "n_pos_with_previous": int((hp & L.label_det.eq(1)).sum())}
    return L, X, info


def lumiere_locked(n_boot, seed=20261021):
    """Transportable P (T) and its no-imaging base (Tbase) trained once on all MU grade-4 detection training rows
    (positives + primary negatives; sensitivity: all gliomas) and applied once to LUMIERE."""
    from sklearn.base import clone
    from prism.experiments import c3_radiomics as c3
    L, LX, info = lumiere_detection()
    rows, preds = [], {}
    for pop in POPS:
        d, X, *_ = context(pop, "primary")
        tr = np.where(d.label_120.notna())[0]
        for arm, cols in (("T", list(X["T"].columns)), ("Tbase", T_BASE)):
            assert list(LX[cols].columns) == list(X[arm].columns)
            bp = clone(c3.BASE_PRE).fit(X[arm].iloc[tr])
            m = c3._ridge(bp.transform(X[arm].iloc[tr]), d, tr, 0)
            preds[f"{arm}@{pop}"] = m.predict_proba(bp.transform(LX[cols]))[:, 1][None, :]
    y, g = L.label_det.to_numpy(), L.patient_id.to_numpy()
    sub = {"with_previous": L.prev_scan_id.ne("").to_numpy(), "early_post_rt_flag0": L.early_post_rt.eq(0).to_numpy()}
    pt, dr = bootstrap(y, preds, g, n_boot, seed, subsets=sub)
    for sn in ("all",) + tuple(sub):
        m = np.ones(len(y), bool) if sn == "all" else sub[sn]
        for a in preds:
            lo, hi = ci(dr[(a, sn)])
            rows.append({"subset": sn, "arm": a, "n_pos": int(y[m].sum()), "n_neg": int((y[m] == 0).sum()),
                         "n_patients": int(len(np.unique(g[m]))), "auc": pt[(a, sn)], "auc_lo": lo, "auc_hi": hi,
                         "transport_failure_flag": bool(pt[(a, sn)] < 0.65) if a.startswith("T@") else np.nan})
        for pop in POPS:
            x = dr[(f"T@{pop}", sn)] - dr[(f"Tbase@{pop}", sn)]
            lo, hi = ci(x)
            rows.append({"subset": sn, "arm": f"T@{pop} - Tbase@{pop}", "auc": pt[(f"T@{pop}", sn)] - pt[(f"Tbase@{pop}", sn)],
                         "auc_lo": lo, "auc_hi": hi})
    single = []
    for c in LX.columns:  # descriptive: univariable AUC of each transportable input on LUMIERE
        v = LX[c].to_numpy(float)
        ok = ~np.isnan(v)
        single.append({"feature": c, "auc_lumiere": float(aucs(y[ok], v[ok][None])[0])})
    pr = pd.concat([L[["scan_id", "patient_id", "day", "rating", "label_det", "prev_scan_id"]],
                    pd.DataFrame({k: v[0] for k, v in preds.items()})], axis=1)
    return pd.DataFrame(rows), info, pd.DataFrame(single), pr


# ---------------------------------------------------------------- deep arms (stream B score files)
DEEP_DIR = OUT / "deep"


def read_deep_scores(arm: str, d: pd.DataFrame):
    """scores.csv -> (test logits (5 x n), {(r, k): inner-OOF logits (n,) NaN outside the training side})."""
    sc = pd.read_csv(DEEP_DIR / arm / "scores.csv")
    sc["is_test"] = sc.is_test.astype(str).str.lower().isin(["1", "true"])
    pos = pd.Series(np.arange(len(d)), index=d.scan_id)
    assert sc.scan_id.isin(pos.index).all(), f"{arm}: scan_ids outside the population"
    sc["row"] = pos.reindex(sc.scan_id).to_numpy()
    n = len(d)
    test = np.full((5, n), np.nan)
    oof = {}
    for (r, k), g in sc.groupby(["repeat", "fold"]):
        t = g[g.is_test].groupby("row").logit.mean()
        f = fold_ids(d, int(r))
        assert (f[t.index] == k).all(), f"{arm}: test rows outside outer fold {r}/{k}"
        test[int(r), t.index] = t.to_numpy()
        o = np.full(n, np.nan)
        tt = g[~g.is_test]
        assert tt.groupby("row").size().max() == 1, f"{arm}: a training row scored by several inner networks"
        assert (f[tt.row] != k).all(), f"{arm}: OOF rows inside the outer test fold"
        o[tt.row.to_numpy()] = tt.logit.to_numpy()
        oof[(int(r), int(k))] = o
    return test, oof


def deep_stack(arm: str, pop: str, ref_oofs: dict, n_boot: int):
    """Stack a deep arm's score onto B1 exactly as finetune_deep.stack_predict (z-score with the inner-OOF mean/SD on
    the outer training rows, BASE_PRE on B1, verified ridge refit) and evaluate vs P and B1."""
    from prism.analyses.finetune_deep import stack_predict
    d, X, *_ = context(pop, "primary")
    test, oof = read_deep_scores(arm, d)
    lab = d.label_120.to_numpy()
    st = np.full((5, len(d)), np.nan)
    for r in range(5):
        f = fold_ids(d, r)
        for k in range(5):
            o = oof[(r, k)]
            tr_ver = np.where((f != k) & ~np.isnan(lab))[0]
            missing = int(np.isnan(o[tr_ver]).sum())
            assert missing == 0, f"{arm}: {missing} outer-training rows (r{r} k{k}) without an inner OOF logit"
            te = np.where((f == k) & ~np.isnan(test[r]))[0]
            st[r, te] = stack_predict(d, X["B1"], o, test[r], tr_ver, te, seed=r)
    oofs = {**ref_oofs, f"B1+{arm}": st, f"{arm}_image": 1 / (1 + np.exp(-test))}
    res, con, wp = [], [], []
    for name, rows in eval_sets(d, "primary").items():
        rows = rows & np.isfinite(st).all(0)
        extra = [(f"B1+{arm}", "P"), (f"B1+{arm}", "B1"), (f"{arm}_image", "I"), (f"{arm}_image", "B1")]
        a, b, c = evaluate_set(f"{pop}|{name}", d, rows, oofs, n_boot, contrasts=CONTRASTS + extra)
        res += a
        con += b
        wp += c
    return pd.DataFrame(res), pd.DataFrame(con), pd.DataFrame(wp)


def g5_triage(arm: str, n_boot: int):
    """G5: forward 120-day score on index scans, stacked onto C2, evaluated in the intended use as in
    TRIAGE_FEASIBILITY.md (evaluate_repeated, IPCW AUC(120 d), reference C2)."""
    from prism.analyses import phase_censoring as pc
    from prism.analyses.finetune_deep import stack_predict
    from prism.models.metrics import evaluate_repeated
    cohort, folds, index, p4, _ = pc.load("grade4")
    Xc, _ = pc.arm_design("C2", cohort, index)
    test, oof = read_deep_scores(arm, cohort.assign(**{f"fold_r{r}": c3_fold(cohort, folds, r) for r in range(5)}))
    lab = cohort[f"label_{H}"].to_numpy(float)
    st = np.full((5, len(cohort)), np.nan)
    for r in range(5):
        f = c3_fold(cohort, folds, r)
        for k in range(5):
            tr_ver = np.where((f != k) & ~np.isnan(lab))[0]
            assert not np.isnan(oof[(r, k)][tr_ver]).any(), f"{arm}: missing inner OOF logits r{r} k{k}"
            te = np.where(f == k)[0]
            st[r, te] = stack_predict(cohort, Xc, oof[(r, k)], test[r], tr_ver, te, seed=r)
    full = pd.read_csv(pc.OUT / "oof_grade4_full.csv.gz")
    assert (full.scan_id.to_numpy() == cohort.scan_id.to_numpy()).all()
    c2 = np.array([full[f"C2#r{r}"].to_numpy(float) for r in range(5)])
    iu = p4 != "pre_rt"
    oo = {"C2": c2[:, iu], f"C2+{arm}": st[:, iu], f"{arm}_image": 1 / (1 + np.exp(-test[:, iu]))}
    ev = evaluate_repeated(cohort[iu].reset_index(drop=True), oo, H, reference="C2", n_boot=n_boot)
    ev.index.name = "arm"
    return ev.reset_index()


def c3_fold(cohort, folds, r):
    from prism.experiments import c3_radiomics as c3
    return c3._fold_ids(cohort, folds, r)


# ---------------------------------------------------------------- main
def oof_matrix(results, pop, negset, n):
    out = {}
    for (p, s, arm, r, k), te, pr, _ in results:
        if (p, s) == (pop, negset):
            out.setdefault(arm, np.full((5, n), np.nan))[r, te] = pr
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism detection", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--cohort-only", action="store_true")
    ap.add_argument("--deep-only", action="store_true", help="only (re-)evaluate the deep arms found under deep/")
    ap.add_argument("--no-radiomics", action="store_true")
    ap.add_argument("--skip-leakage-check", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    warnings.filterwarnings("ignore")
    if a.cohort_only:
        write_cohort()
        return
    if not COHORT_CSV.exists():
        write_cohort()
    OUT.mkdir(parents=True, exist_ok=True)
    snap = OUT / "PLAN_snapshot.md"
    if not snap.exists():
        from prism.audit.provenance import git_state
        doc = (REPO / "docs" / "results" / "DETECTION_TASK.md").read_text()
        plan = doc.split("## Plan (pre-specified)", 1)[1].split("\n## ", 1)[0]
        snap.write_text(f"# PLAN snapshot ({time.strftime('%Y-%m-%dT%H:%M:%S')}, git {git_state()['commit'][:10]})\n\n"
                        "## Plan (pre-specified)" + plan)
    pd.set_option("display.width", 250)
    if a.deep_only:
        run_deep(a.n_boot)
        return
    checks = []
    index, dfull, counts, meas = _base()
    # cohort file == frame used here
    cf = pd.read_csv(COHORT_CSV, keep_default_na=False)
    assert (cf.scan_id.to_numpy() == dfull.scan_id.to_numpy()).all()
    # index-scan rows reproduce the C2 design of mu_cohort (same derivations for progression scans)
    from prism.analyses import phase_censoring as pc
    for pop in POPS:
        d, X, rad, er, F = context(pop, "primary")
        coh = load_cohort(pop)
        xc, _ = pc.arm_design("C2", coh, index)
        xc.index = coh.scan_id
        mine = X["B1"].set_index(d.scan_id).loc[d.scan_id[d.label_det.eq(0)]]
        dev = float(np.nanmax(np.abs(mine.to_numpy(float) - xc.loc[mine.index].to_numpy(float))))
        same_nan = bool(np.array_equal(np.isnan(mine.to_numpy(float)), np.isnan(xc.loc[mine.index].to_numpy(float))))
        checks.append({"check": f"{pop}: B1 design of index scans equals phase_censoring C2 design (max dev)",
                       "value": dev, "ok": dev == 0 and same_nan})
        assert dev == 0 and same_nan
        if not a.skip_leakage_check:
            checks.append({"check": f"{pop}: change/nadir features unchanged with all later scans deleted (max dev)",
                           "value": leakage_check(d, index, meas, F), "ok": True})
    print(f"context + checks {time.time() - t0:.0f}s", flush=True)

    jobs = [(p, s, arm, r, k) for p in POPS for s in NEGSETS for arm in ARMS for r in range(5) for k in range(5)]
    if not a.no_radiomics:  # nested radiomics: grade 4 first (primary population), primary negatives
        jobs = [(p, "primary", "P+R", r, k) for p in POPS for r in range(5) for k in range(5)] + jobs
    from prism.models.metrics import counted_warnings  # noqa: F401  (warnings silenced in workers)
    with ProcessPoolExecutor(a.workers) as ex:
        results = list(ex.map(cv_job, jobs, chunksize=1))
    print(f"fits {time.time() - t0:.0f}s", flush=True)
    nested = pd.DataFrame([{"population": j[0], "repeat": j[3], "fold": j[4], "chosen": c}
                           for j, _, _, c in results if j[2] == "P+R"])
    nested.to_csv(OUT / "nested_radiomics_choices.csv", index=False)

    T = {"auc": [], "contrasts": [], "within_phase": []}
    all_oofs = {}
    for pop in POPS:
        for s in NEGSETS:
            d = context(pop, s)[0]
            oofs = oof_matrix(results, pop, s, len(d))
            assert all(np.isfinite(o).all() for o in oofs.values()), (pop, s)
            all_oofs[(pop, s)] = (d, oofs)
            pd.concat([pd.DataFrame(o.T, columns=[f"{k}#r{r}" for r in range(5)]) for k, o in oofs.items()], axis=1
                      ).assign(scan_id=d.scan_id.to_numpy()).to_csv(OUT / f"oof_{pop}_{s}.csv.gz", index=False)
            for name, rows in eval_sets(d, s).items():
                r_, c_, w_ = evaluate_set(f"{pop}|train_{s}|{name}", d, rows, oofs, a.n_boot)
                T["auc"] += r_
                T["contrasts"] += c_
                T["within_phase"] += w_
            print(f"{pop}/{s} evaluated {time.time() - t0:.0f}s", flush=True)
    for k, v in T.items():
        pd.DataFrame(v).to_csv(OUT / f"{k}.csv", index=False)
    auc, con = pd.DataFrame(T["auc"]), pd.DataFrame(T["contrasts"])

    # decision rule 1
    key = "grade4|train_primary|intended_use"
    p = auc[(auc.set == key) & (auc.arm == "P")].iloc[0]
    c = con[(con.set == key) & (con.contrast == "P - B1") & (con.subset == "all")].iloc[0]
    a1 = bool(p.auc >= 0.75 and p.auc_lo >= 0.65)
    a2 = bool(c["diff"] >= 0.03 and c.diff_lo > 0)
    rule = [{"item": "P AUC >= 0.75 with lower 95% bound >= 0.65 (grade 4, intended use)", "value": p.auc,
             "lo": p.auc_lo, "hi": p.auc_hi, "met": a1},
            {"item": "P - B1 >= +0.03 with CI excluding 0", "value": c["diff"], "lo": c.diff_lo, "hi": c.diff_hi,
             "met": a2},
            {"item": "GO for a detection study" if a1 and a2 else "NO-GO for detection on MU alone", "value": np.nan,
             "lo": np.nan, "hi": np.nan, "met": a1 and a2}]

    # LUMIERE
    lum, linfo, lsingle, lpred = lumiere_locked(a.n_boot)
    lum.to_csv(OUT / "lumiere.csv", index=False)
    lsingle.to_csv(OUT / "lumiere_single_feature_auc.csv", index=False)
    lpred.to_csv(OUT / "lumiere_predictions.csv", index=False)
    x = lum[(lum.subset == "all") & (lum.arm == "T@grade4")].iloc[0]
    rule.append({"item": "LUMIERE locked T (grade-4 trained): AUC" + (" < 0.65: TRANSPORT FAILURE" if x.auc < 0.65 else
                                                                     " >= 0.65"),
                 "value": x.auc, "lo": x.auc_lo, "hi": x.auc_hi, "met": bool(x.auc >= 0.65)})
    pd.DataFrame(rule).to_csv(OUT / "rule.csv", index=False)
    pd.DataFrame(checks).to_csv(OUT / "checks.csv", index=False)
    (OUT / "run_info.json").write_text(json.dumps({"argv": vars(a), "seconds": round(time.time() - t0),
                                                   "cohort_exclusions": counts, "lumiere": linfo}, indent=1,
                                                  default=float))
    print(pd.DataFrame(checks).to_string(index=False))
    print(auc[auc.set.str.startswith("grade4")].round(3).to_string(index=False))
    print(con[con.set.str.startswith("grade4|train_primary")].round(3).to_string(index=False))
    print(lum.round(3).to_string(index=False), linfo)
    print(pd.DataFrame(rule).round(3).to_string(index=False))
    run_deep(a.n_boot)
    print(f"total {time.time() - t0:.0f}s")


def run_deep(n_boot):
    """Evaluate every deep arm with a scores.csv under deep/ (G5* = triage retest, else detection)."""
    if not DEEP_DIR.exists():
        print("no deep arms found")
        return
    arms = sorted(p.parent.name for p in DEEP_DIR.glob("*/scores.csv"))
    if not arms:
        print("no deep arms found")
        return
    out = []
    for arm in arms:
        if arm.upper().startswith("G5"):
            ev = g5_triage(arm, n_boot)
            ev.to_csv(DEEP_DIR / arm / "triage_eval.csv", index=False)
            print(arm, "\n", ev.round(3).to_string(index=False))
            continue
        sc = pd.read_csv(DEEP_DIR / arm / "scores.csv", usecols=["scan_id"])
        dfull = _base()[1]
        pop = "grade4" if dfull.set_index("scan_id").grade4.reindex(sc.scan_id.unique()).all() else "all_glioma"
        d = context(pop, "primary")[0]
        ref = pd.read_csv(OUT / f"oof_{pop}_primary.csv.gz").set_index("scan_id").loc[d.scan_id]
        ref_oofs = {k: np.array([ref[f"{k}#r{r}"].to_numpy(float) for r in range(5)]) for k in ("B1", "P", "I")}
        res, con, wp = deep_stack(arm, pop, ref_oofs, n_boot)
        for nm, df in (("auc", res), ("contrasts", con), ("within_phase", wp)):
            df.to_csv(DEEP_DIR / arm / f"{nm}.csv", index=False)
        out.append(con.assign(deep_arm=arm))
        print(arm, pop, "\n", res.round(3).to_string(index=False), "\n", con.round(3).to_string(index=False))
    if out:
        pd.concat(out).to_csv(DEEP_DIR / "summary_contrasts.csv", index=False)


if __name__ == "__main__":
    main()
