"""UCSF-ALPTDG Part B: models trained on UCSF (internal), and the internal half of the 120-day secondary analysis.

ANALYSIS PLAN: docs/results/UCSF_PLAN.md (committed 0e7c9fe before any outcome model on UCSF), Part B.

Inputs: outputs/data/ucsf/scans.csv (prism.data.ucsf) and imaging_features.csv (prism.features.ucsf_imaging).
Arms (verified ridge pipeline of prism.analyses.detection: c3.fit_predict(c3.BASELINES[0]), inner patient-grouped C):
  B0          age, sex, IDH, MGMT (C2 rules: unknown -> 0, no indicators)
  Iscan       6 log volumes + 13 morphology / relative-intensity features at the scan
  Ipure       Iscan + logratio_prev_* (6) + nadir_all_{et,lesion}  (history = scan 1)
  Timg        LUMIERE image set: log ET, necrosis + cavity, SNFH volumes + their log ratios to the previous scan
  B-Tl        B0 + days from diagnosis + days from RT start + chemo started + on chemo / on RT + surgeries before the
              scan + days since the previous scan (the last only in scan-2 sets)
  + the combinations B0+Iscan, B0+Ipure, B-Tl+Ipure (120-day: B-Tl+Iscan)
Training = evaluation set of each analysis. Repeated patient-grouped, label-stratified 5 x 5 CV (StratifiedGroupKFold,
seed 20261025 + repeat). All-scan sets use single-scan inputs only (B0, Iscan, B0+Iscan).
Evaluation: plain AUC, mean over repeats of pooled OOF AUC, paired patient-cluster bootstrap (1,000, seed 20261025).
Single split: UCSF TRAIN -> TEST, beside 100 random patient-grouped splits with the same number of test patients.

    PYTHONPATH=. .venv/bin/python -m prism.analyses.ucsf_internal [--workers 6] [--n-boot 1000]
    -> outputs/results/analyses/ucsf/internal/
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

from prism.analyses import detection as D
from prism.config import RESULTS

OUT = RESULTS / "analyses" / "ucsf" / "internal"
LOCKED = RESULTS / "analyses" / "ucsf" / "locked"
SEED = 20261025
N_REP, N_FOLD, N_SPLITS = 5, 5, 100
NEG_PRIMARY = ("verified_by_later_progression", "no_progression_followed_120")

VOL = [f"log_{c}_cc" for c in ("et", "netc", "snfh", "rc", "tumor", "lesion")]
MORPH = ["et_fraction_of_tumor", "log_snfh_to_tumor", "has_cavity", "et_n_components", "et_largest_component_fraction",
         "log_et_max_axial", "et_near_cavity_fraction", "et_cavity_distance", "t1c_et_rel", "t1c_et_p90_rel",
         "t1c_netc_rel", "flair_snfh_rel", "flair_netc_rel"]
ISCAN = VOL + MORPH
IPURE = ISCAN + [f"logratio_prev_{v}" for v in D.VOLS] + ["nadir_all_et", "nadir_all_lesion"]
TIMG = ["log_et_cc", "log_necrosis_cavity_cc", "log_snfh_cc", "logratio_prev_et", "logratio_prev_necrosis_cavity",
        "logratio_prev_snfh"]
TL = ["days_from_diagnosis", "days_from_rt_start", "chemo_started", "on_chemo", "on_rt", "surgeries_before_scan"]

ARMS_S2 = ("B0", "Iscan", "Ipure", "B0+Iscan", "B0+Ipure", "Timg", "B-Tl", "B-Tl+Ipure")
ARMS_ALL = ("B0", "Iscan", "B0+Iscan")
ARMS_120 = ("B0", "Iscan", "B0+Iscan", "B-Tl", "B-Tl+Iscan")
CON_S2 = [("B0+Ipure", "B0"), ("B-Tl+Ipure", "B-Tl"), ("Ipure", "Iscan"), ("B-Tl", "B0"), ("B0+Iscan", "B0")]
CON_ALL = [("B0+Iscan", "B0"), ("Iscan", "B0")]
CON_120 = [("B0+Iscan", "B0"), ("B-Tl+Iscan", "B-Tl"), ("B-Tl", "B0")]


# ---------------------------------------------------------------- data
@lru_cache(maxsize=1)
def scans() -> pd.DataFrame:
    from prism.analyses.phase_censoring import masked_molecular
    from prism.data.ucsf import event_days, load_scans, read_workbook
    s = load_scans()
    im = pd.read_csv(D.OUTPUTS / "data" / "ucsf" / "imaging_features.csv")
    assert im.scan_id.is_unique and s.scan_id.isin(im.scan_id).all()
    s = s.merge(im[["scan_id"] + sorted(set(IPURE + TIMG))], on="scan_id", how="left", validate="one_to_one")
    ev = event_days(read_workbook()["clinical"])[0].set_index("subject_id").reindex(s.subject_id)
    # surgeries before scan 2 = before scan 1 + 2nd / 3rd surgeries dated in (scan 1, scan 2]
    between = sum(((ev[c].to_numpy() > 0) & (ev[c].to_numpy() <= s.scan_day.to_numpy())).astype(int)
                  for c in ("surgery2_day", "surgery3_day"))
    s["surgeries_before_scan"] = s.n_surgeries_before_scan1.to_numpy() + np.where(s.timepoint.eq(2), between, 0)
    s["patient_id"] = s.subject_id
    s["age_s1"] = s.subject_id.map(s[s.timepoint.eq(1)].set_index("subject_id").age)
    s[["idh_mutant", "mgmt_methylated"]] = masked_molecular(s, 0.0).to_numpy()
    s["all"] = True
    return s


def design(s: pd.DataFrame, with_prev: bool) -> dict[str, pd.DataFrame]:
    b0 = pd.DataFrame({"age": s.age_s1, "male": s.male.astype(float), "idh_mutant": s.idh_mutant,
                       "mgmt_methylated": s.mgmt_methylated}, index=s.index)
    rt = s.days_from_rt_start_to_mri
    unk = s.on_tx.eq("unknown")
    tl = pd.DataFrame({"days_from_diagnosis": s.days_from_diagnosis_to_mri, "days_from_rt_start": rt.where(rt >= 0),
                       "chemo_started": s.chemo_started, "on_chemo": s.on_chemo.astype(float).mask(unk),
                       "on_rt": s.on_rt.astype(float).mask(unk), "surgeries_before_scan": s.surgeries_before_scan},
                      index=s.index)
    if with_prev:
        tl["days_since_prev"] = s.days_from_prev
    btl = pd.concat([b0, tl], axis=1)
    return {"B0": b0, "Iscan": s[ISCAN], "Ipure": s[IPURE], "Timg": s[TIMG], "B-Tl": btl,
            "B0+Iscan": pd.concat([b0, s[ISCAN]], axis=1), "B0+Ipure": pd.concat([b0, s[IPURE]], axis=1),
            "B-Tl+Ipure": pd.concat([btl, s[IPURE]], axis=1), "B-Tl+Iscan": pd.concat([btl, s[ISCAN]], axis=1)}


def sets() -> dict[str, dict]:
    """name -> {mask, y, arms, contrasts, plan}. y is 1 / 0 on the rows of mask."""
    s = scans()
    t1, t2 = s.timepoint.eq(1), s.timepoint.eq(2)
    neg = s.neg_class.isin(NEG_PRIMARY) & ~s.label_excluded_prior_progression
    ver = s.neg_class.eq("verified_by_later_progression") & ~s.label_excluded_prior_progression
    p30, btw, s1at = s.pos_s2_pm30.eq(1), s.pos_s2_between.eq(1), s.pos_s1_at.eq(1)
    out = {}
    s2 = lambda pop, pos, ng, plan="plan": dict(mask=s[pop] & t2 & (pos | ng), y=pos, arms=ARMS_S2, con=CON_S2,
                                                prev=True, plan=plan)
    out["grade4|scan2|pos_s2_pm30"] = s2("grade4", p30, neg)                       # PRIMARY
    out["gbm_who|scan2|pos_s2_pm30"] = s2("gbm_who", p30, neg)
    out["all|scan2|pos_s2_pm30"] = s2("all", p30, neg)
    out["grade4|scan2|pos_s2_between"] = s2("grade4", btw, neg)
    out["grade4|scan2|pos_s2_pm30|verified_neg"] = s2("grade4", p30, ver)
    et = s.et_increased.notna() & t2
    out["grade4|scan2|et_increased(reference)"] = dict(mask=s.grade4 & et, y=s.et_increased.eq(1), arms=ARMS_S2,
                                                        con=CON_S2, prev=True, plan="plan (circular reference)")
    for pop in ("grade4", "all"):
        pos = p30 | s1at
        out[f"{pop}|all_scans|pos_s2_pm30+pos_s1_at"] = dict(mask=s[pop] & (pos | neg), y=pos, arms=ARMS_ALL,
                                                             con=CON_ALL, prev=False, plan="plan")
    # 120-day risk from scan 1: pos = progression 1-120 d after scan 1; neg = > 120 d, or >= 120 d follow-up w/o
    d = s.days_to_progression
    usable = t1 & ~s.label_excluded_prior_progression & ~d.between(-7, 1, inclusive="left")
    pos120 = usable & d.between(1, 120)
    neg120 = usable & ((d > 120) | (~s.progression_listed & (s.inferred_follow_up_days >= 120)))
    for pop in ("grade4", "gbm_who", "all"):
        out[f"{pop}|scan1|forward_120d"] = dict(mask=s[pop] & (pos120 | neg120), y=pos120, arms=ARMS_120, con=CON_120,
                                                prev=False, plan="plan (120-day secondary)")
    return out


@lru_cache(maxsize=32)
def context(name: str):
    """(frame of the set with label_120 = training label, designs, CV folds (N_REP x n))."""
    from sklearn.model_selection import StratifiedGroupKFold
    st = sets()[name]
    s = scans()
    d = s[st["mask"].to_numpy()].reset_index(drop=True)
    y = st["y"][st["mask"]].to_numpy().astype(int)
    d["label_120"] = y.astype(float)
    d["label_det"] = y
    d["phase"] = d.rt_phase
    X = {a: v for a, v in design(d, st["prev"]).items() if a in st["arms"]}
    folds = np.full((N_REP, len(d)), -1)
    for r in range(N_REP):
        cv = StratifiedGroupKFold(n_splits=N_FOLD, shuffle=True, random_state=SEED + r)
        for k, (_, te) in enumerate(cv.split(np.zeros(len(d)), y, d.patient_id)):
            folds[r, te] = k
    assert (folds >= 0).all()
    return d, X, folds


def random_splits(name: str) -> list[np.ndarray]:
    """N_SPLITS random patient-grouped test masks with as many test patients as UCSF's TEST split has in the set;
    redrawn until both sides hold >= 2 positives and >= 2 negatives."""
    d = context(name)[0]
    pats = d.patient_id.unique()
    n_test = d[d.split.eq("TEST")].patient_id.nunique()
    rng = np.random.default_rng(SEED)
    out = []
    while len(out) < N_SPLITS:
        te = d.patient_id.isin(rng.choice(pats, n_test, replace=False)).to_numpy()
        y = d.label_det.to_numpy()
        if min(y[te].sum(), (1 - y[te]).sum(), y[~te].sum(), (1 - y[~te]).sum()) >= 2:
            out.append(te)
    return out


def _fit(d, Xa, tr, te, seed):
    from prism.experiments import c3_radiomics as c3
    return c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr, te, seed=seed)


def cv_job(job):
    from threadpoolctl import threadpool_limits
    name, arm, r = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, X, folds = context(name)
    o = np.full(len(d), np.nan)
    for k in range(N_FOLD):
        tr, te = np.where(folds[r] != k)[0], np.where(folds[r] == k)[0]
        o[te] = _fit(d, X[arm], tr, te, r)
    return job, o


def split_job(job):
    """UCSF split (i = -1) or random split i: AUC on the test patients (the UCSF split also returns its scores)."""
    from threadpoolctl import threadpool_limits
    name, arm, i = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, X, _ = context(name)
    te_m = d.split.eq("TEST").to_numpy() if i < 0 else random_splits(name)[i]
    tr, te = np.where(~te_m)[0], np.where(te_m)[0]
    p = _fit(d, X[arm], tr, te, 0)
    return job, te, p, float(D.aucs(d.label_det.to_numpy()[te], p[None])[0])


def perm_job(job):
    """Pipeline control: labels permuted across patients (seed SEED + i), same folds; must give AUC ~ 0.5."""
    from threadpoolctl import threadpool_limits
    name, arm, i = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, X, folds = context(name)
    d = d.copy()
    y = np.random.default_rng(SEED + i).permutation(d.label_det.to_numpy())
    d["label_120"], o = y.astype(float), np.full(len(d), np.nan)
    for k in range(N_FOLD):
        tr, te = np.where(folds[0] != k)[0], np.where(folds[0] == k)[0]
        o[te] = _fit(d, X[arm], tr, te, 0)
    return job, float(D.aucs(y, o[None])[0])


# ---------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="ucsf_internal", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    t0 = time.time()
    warnings.filterwarnings("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    S = sets()
    split_sets = [n for n in S if "|scan2|" in n and n.split("|")[-1] == "pos_s2_pm30"] + \
                 ["grade4|scan1|forward_120d", "all|scan1|forward_120d"]
    for n in S:
        context(n)
        if n in split_sets:
            random_splits(n)
    cv_jobs = [(n, arm, r) for n, st in S.items() for arm in st["arms"] for r in range(N_REP)]
    sp_jobs = [(n, arm, i) for n in split_sets for arm in S[n]["arms"] for i in range(-1, N_SPLITS)]
    with ProcessPoolExecutor(a.workers) as ex:
        cv = list(ex.map(cv_job, cv_jobs, chunksize=4))
        print(f"cv fits {time.time() - t0:.0f}s", flush=True)
        sp = list(ex.map(split_job, sp_jobs, chunksize=8))
        perm_jobs = [(n, arm, i) for n in ("grade4|scan2|pos_s2_pm30", "all|scan2|pos_s2_pm30")
                     for arm in ("Iscan", "Ipure", "Timg", "B-Tl+Ipure") for i in range(20)]
        pm = list(ex.map(perm_job, perm_jobs, chunksize=4))
    pm = pd.DataFrame([{"set": n, "arm": arm, "perm": i, "auc": v} for (n, arm, i), v in pm])
    pm.to_csv(OUT / "permutation_control.csv", index=False)
    print(pm.groupby(["set", "arm"]).auc.describe().round(3).to_string(), flush=True)
    print(f"split fits {time.time() - t0:.0f}s", flush=True)

    res, con, wp, counts, oof_frames = [], [], [], [], []
    for n, st in S.items():
        d = context(n)[0]
        oofs = {arm: np.full((N_REP, len(d)), np.nan) for arm in st["arms"]}
        for (nn, arm, r), o in cv:
            if nn == n:
                oofs[arm][r] = o
        assert all(np.isfinite(o).all() for o in oofs.values()), n
        r_, c_, w_ = D.evaluate_set(n, d, np.arange(len(d)), oofs, a.n_boot, contrasts=st["con"], seed=SEED)
        res += [{**x, "plan": st["plan"]} for x in r_]
        con += c_
        wp += w_
        counts.append({"set": n, "n_scans": len(d), "n_pos": int(d.label_det.sum()), "n_neg": int((1 - d.label_det).sum()),
                       "n_patients": d.patient_id.nunique(), "train_pos": int(d.label_det[d.split.eq("TRAIN")].sum()),
                       "train_neg": int((1 - d.label_det[d.split.eq("TRAIN")]).sum()),
                       "test_pos": int(d.label_det[d.split.eq("TEST")].sum()),
                       "test_neg": int((1 - d.label_det[d.split.eq("TEST")]).sum()),
                       "test_patients": d[d.split.eq("TEST")].patient_id.nunique()})
        oof_frames.append(pd.concat([pd.DataFrame(o.T, columns=[f"{k}#r{r}" for r in range(N_REP)])
                                     for k, o in oofs.items()], axis=1)
                          .assign(set=n, scan_id=d.scan_id.to_numpy(), label=d.label_det.to_numpy()))
    pd.concat(oof_frames).to_csv(OUT / "oof.csv.gz", index=False)
    res, con, wp = pd.DataFrame(res), pd.DataFrame(con), pd.DataFrame(wp)
    res.to_csv(OUT / "auc.csv", index=False)
    con.to_csv(OUT / "contrasts.csv", index=False)
    wp.to_csv(OUT / "within_phase.csv", index=False)
    pd.DataFrame(counts).to_csv(OUT / "counts.csv", index=False)

    # single split vs random splits
    rows, ucsf_scores = [], []
    for n in split_sets:
        d = context(n)[0]
        y, g = d.label_det.to_numpy(), d.patient_id.to_numpy()
        for arm in S[n]["arms"]:
            rnd = np.array([v for (nn, aa, i), _, _, v in sp if nn == n and aa == arm and i >= 0])
            (_, te, p, v), = [x for x in sp if x[0] == (n, arm, -1)]
            pt, dr = D.bootstrap(y[te], {arm: p[None]}, g[te], a.n_boot, SEED)
            lo, hi = D.ci(dr[(arm, "all")])
            rows.append({"set": n, "arm": arm, "ucsf_split_auc": v, "ucsf_split_lo": lo, "ucsf_split_hi": hi,
                         "ucsf_test_pos": int(y[te].sum()), "ucsf_test_neg": int((1 - y[te]).sum()),
                         "random_median": float(np.median(rnd)), "random_p2_5": float(np.percentile(rnd, 2.5)),
                         "random_p97_5": float(np.percentile(rnd, 97.5)), "random_min": float(rnd.min()),
                         "random_max": float(rnd.max()), "random_sd": float(rnd.std()),
                         "ucsf_split_percentile": float(np.mean(rnd < v) + 0.5 * np.mean(rnd == v)),
                         "n_random_splits": len(rnd)})
            ucsf_scores.append(pd.DataFrame({"set": n, "arm": arm, "scan_id": d.scan_id.to_numpy()[te], "score": p}))
    sp_tab = pd.DataFrame(rows)
    sp_tab.to_csv(OUT / "split_variance.csv", index=False)
    pd.concat(ucsf_scores).to_csv(OUT / "ucsf_split_scores.csv.gz", index=False)

    q3 = q3_contrast(a.n_boot)
    (OUT / "run_info.json").write_text(json.dumps({"argv": vars(a), "seconds": round(time.time() - t0), "seed": SEED,
                                                   "cv": "StratifiedGroupKFold(5, shuffle, SEED + r), 5 repeats",
                                                   "q3": "computed" if q3 is not None else "Part A scores not found"},
                                                  indent=1))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(counts).to_string(index=False))
    print(res[["set", "arm", "auc", "auc_lo", "auc_hi", "auc_repeat_sd"]].round(3).to_string(index=False))
    print(con[con.subset.eq("all")][["set", "contrast", "diff", "diff_lo", "diff_hi", "p_le0"]].round(3)
          .to_string(index=False))
    print(sp_tab.round(3).to_string(index=False))
    if q3 is not None:
        print(q3.round(3).to_string(index=False))
    print(f"total {time.time() - t0:.0f}s")


def q3_contrast(n_boot: int) -> pd.DataFrame | None:
    """Q3: B-arm (UCSF-trained, OOF) - A-arm (locked MU, Part A scores.csv) on the same rows, paired patient-cluster
    bootstrap. Plan: Ipure; Iscan, B0+Ipure and Timg are exploratory. Grade-4 / GBM sets use the grade-4-trained MU
    model, the all-glioma set the all-glioma-trained one."""
    f = LOCKED / "scores.csv"
    if not f.exists():
        return None
    A = pd.read_csv(f).set_index("scan_id")
    oof = pd.read_csv(OUT / "oof.csv.gz")
    rows = []
    for n, mu_pop in (("grade4|scan2|pos_s2_pm30", "grade4"), ("gbm_who|scan2|pos_s2_pm30", "grade4"),
                      ("all|scan2|pos_s2_pm30", "all_glioma")):
        d = context(n)[0]
        o = oof[oof.set.eq(n)].set_index("scan_id").loc[d.scan_id]
        y, g = d.label_det.to_numpy(), d.patient_id.to_numpy()
        for arm in ("Ipure", "Iscan", "B0+Ipure", "Timg"):
            col = f"A-{arm}@{mu_pop}"
            a_ = A[col].reindex(d.scan_id).to_numpy(float)
            assert np.isfinite(a_).all(), col
            B = np.array([o[f"{arm}#r{r}"].to_numpy(float) for r in range(N_REP)])
            pt, dr = D.bootstrap(y, {"B": B, "A": a_[None]}, g, n_boot, SEED)
            x = dr[("B", "all")] - dr[("A", "all")]
            lo, hi = D.ci(x)
            rows.append({"set": n, "arm": arm, "plan": "plan (Q3)" if arm == "Ipure" else "exploratory",
                         "locked_column": col, "B_auc": pt[("B", "all")], "A_auc": pt[("A", "all")],
                         "diff": pt[("B", "all")] - pt[("A", "all")], "diff_lo": lo, "diff_hi": hi,
                         "p_le0": float(np.mean(x <= 0))})
    q = pd.DataFrame(rows)
    q.to_csv(OUT / "q3_b_minus_a.csv", index=False)
    return q


if __name__ == "__main__":
    main()
