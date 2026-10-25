"""EXPLORATORY adversarial audit of the UCSF-ALPTDG image results (docs/results/UCSF_AUDIT.md).

Reads the existing UCSF outputs (scans.csv, imaging_features.csv, locked/scores.csv, internal/oof.csv.gz) and the
MU detection frame for comparison. Changes nothing; prints aggregate numbers only (no SubjectIDs).

    PYTHONPATH=. .venv/bin/python scripts/exploratory_ucsf_audit.py
    PYTHONPATH=. .venv/bin/python scripts/exploratory_ucsf_audit.py --within-et-increased   # 2026-10-26 section only
    (the 2026-10-26 section writes aggregate AUCs to outputs/results/analyses/ucsf/audit/within_et_increased_cis.csv)
"""

from __future__ import annotations

import warnings

import nibabel as nib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from prism.config import OUTPUTS, RESULTS

warnings.filterwarnings("ignore")
U = OUTPUTS / "data" / "ucsf"
R = RESULTS / "analyses" / "ucsf"
NEG = ("verified_by_later_progression", "no_progression_followed_120")
RNG = np.random.default_rng(20261025)
ARMS_A = ["A-B0@grade4", "A-Iscan@grade4", "A-Ipure@grade4", "A-Timg@grade4"]
ARMS_B = ["B0", "Iscan", "Ipure", "Timg"]


def auc(y, s, n_boot=1000):
    """AUC with a simple bootstrap CI (scan-2 sets: one row per patient)."""
    y, s = np.asarray(y, int), np.asarray(s, float)
    ok = ~np.isnan(s)
    y, s = y[ok], s[ok]
    if len(np.unique(y)) < 2:
        return "n/a"
    a = roc_auc_score(y, s)
    bs = []
    for _ in range(n_boot):
        i = RNG.integers(0, len(y), len(y))
        if len(np.unique(y[i])) == 2:
            bs.append(roc_auc_score(y[i], s[i]))
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return f"{a:.3f} ({lo:.3f}-{hi:.3f}) [{int(y.sum())}/{int((1 - y).sum())}]"


def frame():
    s = pd.read_csv(U / "scans.csv", dtype={"subject_id": str})
    f = pd.read_csv(U / "imaging_features.csv", dtype={"SubjectID": str})
    sc = pd.read_csv(R / "locked" / "scores.csv", dtype={"patient_id": str})
    oof = pd.read_csv(R / "internal" / "oof.csv.gz")
    oof = oof[oof.set.eq("grade4|scan2|pos_s2_pm30")].set_index("scan_id")
    for a in ARMS_B:
        oof[a] = oof[[f"{a}#r{r}" for r in range(5)]].mean(axis=1)  # mean OOF over repeats (ranking only)
    u = s.merge(f.drop(columns=["SubjectID", "timepoint", "has_prev"]), on="scan_id", validate="one_to_one")
    u = u.merge(sc[["scan_id"] + ARMS_A], on="scan_id", validate="one_to_one")
    u = u.join(oof[ARMS_B + ["label"]], on="scan_id")
    u["neg"] = u.neg_class.isin(NEG)
    return u, s, f


def main():
    u, s, f = frame()
    t2 = u.timepoint.eq(2) & u.grade4
    P = u[t2 & (u.pos_s2_pm30.eq(1) | u.neg)].copy()
    y = P.pos_s2_pm30.eq(1).astype(int).to_numpy()
    assert len(P) == 69 and y.sum() == 29
    assert (P.label.to_numpy() == y).all(), "Part-B OOF labels differ from the primary label"
    P["et_absent"] = (P.et_cc == 0).astype(float)
    P["log_ratio_et"] = P.logratio_prev_et
    print("=== baseline: primary set AUCs")
    for c in ARMS_A + ARMS_B + ["log_et_cc", "logratio_prev_et"]:
        print(f"  {c:16s} {auc(y, P[c])}")

    # ---------------------------------------------------------------- 1. ET absent
    print("\n=== 1. ET absent")
    print("  ET absent, all 596 UCSF scans: %.2f; primary set: pos %d/%d, neg %d/%d" % (
        (u.et_cc == 0).mean(), P.et_absent[y == 1].sum(), (y == 1).sum(), P.et_absent[y == 0].sum(), (y == 0).sum()))
    print("  AUC of 'ET present' indicator:", auc(y, 1 - P.et_absent))
    m = P.et_absent.eq(0).to_numpy()
    print("  ET-present subset:")
    for c in ARMS_A + ARMS_B + ["log_et_cc", "logratio_prev_et", "log_snfh_cc", "log_lesion_cc"]:
        print(f"    {c:16s} {auc(y[m], P[c][m])}")
    print("  ET-absent subset (score ranking among no-ET scans):")
    for c in ARMS_A + ARMS_B:
        print(f"    {c:16s} {auc(y[~m], P[c][~m])}")
    et_dep = [c for c in ["et_fraction_of_tumor", "log_snfh_to_tumor", "et_largest_component_fraction",
                          "et_near_cavity_fraction", "et_cavity_distance", "t1c_et_rel", "t1c_et_p90_rel",
                          "t1c_netc_rel", "flair_netc_rel"]]
    print("  NaN fraction when ET absent / present (primary set):")
    for c in et_dep:
        print(f"    {c:30s} {P[c][~m].isna().mean():.2f} / {P[c][m].isna().mean():.2f}")
    # MU imputation values (median of MU training rows) vs UCSF ET-present values
    coef = pd.read_csv(R / "locked" / "coefficients.csv")
    cg = coef[(coef.models == "grade4") & (coef.arm == "A-Iscan")].set_index("feature").coef
    print("  locked A-Iscan@grade4 coefficients (standardised), top |coef|:")
    print(cg.reindex(cg.abs().sort_values(ascending=False).index).head(12).round(3).to_string())
    # what does the model score look like for ET-absent scans vs ET-present negatives?
    for c in ["A-Iscan@grade4", "Iscan"]:
        print(f"  {c}: median score ET-absent neg {P[c][~m & (y == 0)].median():.3f}, ET-absent pos "
              f"{P[c][~m & (y == 1)].median():.3f}, ET-present neg {P[c][m & (y == 0)].median():.3f}, "
              f"ET-present pos {P[c][m & (y == 1)].median():.3f}")

    # ---------------------------------------------------------------- 2. label asymmetry
    print("\n=== 2. negatives vs positives")
    pos, neg = P[y == 1], P[y == 0]
    q = lambda v: f"{np.nanmedian(v):.0f} ({np.nanpercentile(v, 25):.0f}-{np.nanpercentile(v, 75):.0f})"
    print("  neg class:", neg.neg_class.value_counts().to_dict())
    for c in ["days_from_diagnosis_to_mri", "days_from_prev", "days_from_rt_start_to_mri", "age"]:
        print(f"  {c:28s} pos {q(pos[c])}  neg {q(neg[c])}")
    for c in ["idh", "mgmt", "gbm_who", "on_tx", "et_change", "split", "in_pdgm"]:
        print(f"  {c}: pos {pos[c].value_counts().to_dict()}  neg {neg[c].value_counts().to_dict()}")
    print(f"  death listed: pos {pos.death_listed.mean():.2f} neg {neg.death_listed.mean():.2f}; days scan2->death"
          f" pos {q(pos.days_to_death)} neg {q(neg.days_to_death)}")
    print(f"  verified negatives: days scan2 -> later progression {q(neg.days_to_progression)}")
    ver = neg.neg_class.eq("verified_by_later_progression")
    for lab, mm in [("verified-only negatives", (y == 1) | P.neg_class.eq("verified_by_later_progression")),
                    ("followed-only (no progression) negatives", (y == 1) | P.neg_class.eq(
                        "no_progression_followed_120")),
                    ("negatives progressing 120-365 d after scan 2", (y == 1) | (P.neg & P.days_to_progression.between(
                        120, 365))),
                    ("IDH-wildtype only", P.idh.eq("wildtype")),
                    ("WHO GBM only", P.gbm_who.astype(bool))]:
        mm = mm.to_numpy()
        print(f"  {lab}:")
        for c in ["A-Iscan@grade4", "A-Ipure@grade4", "A-Timg@grade4", "Ipure", "log_et_cc"]:
            print(f"    {c:16s} {auc(y[mm], P[c][mm])}")
    print("  AUC of IDH-mutant indicator:", auc(y, P.idh.eq("mutant").astype(float)))

    # ---------------------------------------------------------------- 3. timing of the progression call
    print("\n=== 3. progression dated before vs after scan 2 (positives), all negatives")
    dp = P.days_to_progression  # relative to scan 2 (negative = before)
    print(f"  positives: days progression - scan2 {q(dp[y == 1])}; |d| <= 1 d: {(dp[y == 1].abs() <= 1).sum()}; "
          f"before (< -1 d): {(dp[y == 1] < -1).sum()}; after (> 1 d): {(dp[y == 1] > 1).sum()}")
    for lab, pm in [("same day (|d| <= 1)", dp.abs() <= 1), ("before scan 2 (< -1 d)", dp < -1),
                    ("after scan 2 (> 1 d)", dp > 1), ("on or before scan 2 (<= 1 d)", dp <= 1)]:
        mm = ((y == 1) & pm.to_numpy()) | (y == 0)
        print(f"  positives {lab}:")
        for c in ["A-Iscan@grade4", "A-Ipure@grade4", "A-Timg@grade4", "Ipure", "log_et_cc"]:
            print(f"    {c:16s} {auc(y[mm], P[c][mm])}")

    # ---------------------------------------------------------------- 4. ET change category
    print("\n=== 4. UCSF ET change category (scan 2)")
    print(pd.crosstab(P.et_change.fillna("NA"), np.where(y == 1, "pos", "neg")).to_string())
    print(pd.crosstab(P.snfh_change.fillna("NA"), np.where(y == 1, "pos", "neg")).to_string())
    ordc = P.et_change.map({"Decreased": 0, "Unchanged": 1, "Increased": 2}).astype(float)
    print("  AUC ET change (Dec<Unch<Inc):", auc(y, ordc))
    print("  AUC ET 'Increased' binary:", auc(y, P.et_change.eq("Increased").astype(float)))
    inc = P.et_change.eq("Increased").to_numpy()
    print(f"  sens {inc[y == 1].mean():.2f}, spec {1 - inc[y == 0].mean():.2f}")
    sn = P.snfh_change.map({"Decreased": 0, "Unchanged": 1, "Increased": 2}).astype(float)
    print("  AUC SNFH change category:", auc(y, sn))
    print("  AUC ET or SNFH Increased:", auc(y, (P.et_change.eq("Increased") | P.snfh_change.eq("Increased"))
                                         .astype(float)))
    for lab, mm in [("ET not Increased", ~inc), ("ET Increased", inc)]:
        print(f"  within {lab}:")
        for c in ["A-Iscan@grade4", "A-Ipure@grade4", "A-Timg@grade4", "Ipure", "log_et_cc"]:
            print(f"    {c:16s} {auc(y[mm], P[c][mm])}")

    # ---------------------------------------------------------------- 5. case mix / timing
    print("\n=== 5. days from diagnosis")
    print("  AUC days from diagnosis:", auc(y, P.days_from_diagnosis_to_mri))
    print("  AUC days from RT start:", auc(y, P.days_from_rt_start_to_mri))
    print("  AUC days scan1->scan2:", auc(y, P.days_from_prev), "(inverse:", auc(y, -P.days_from_prev), ")")

    # ---------------------------------------------------------------- 6. simple thresholds
    print("\n=== 6. one-variable rules")
    for c in ["log_et_cc", "log_et_max_axial", "log_tumor_cc", "logratio_prev_et", "nadir_all_et", "log_snfh_cc"]:
        print(f"  {c:18s} {auc(y, P[c])}")
    et = P.et_cc.to_numpy()
    for thr in [0.0, 0.1, 0.5, 1.0, 2.0]:
        r = et > thr
        print(f"  ET > {thr} cc: sens {r[y == 1].mean():.2f} spec {1 - r[y == 0].mean():.2f}")
    # incremental value over log ET: logistic regression with CV (LOO) on log_et_cc vs log_et_cc + locked score
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_predict, StratifiedKFold
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    for cols in (["log_et_cc"], ["log_et_cc", "logratio_prev_et"], ["log_et_cc", "log_snfh_cc"],
                 ["log_et_cc", "logratio_prev_et", "log_snfh_cc"]):
        X = P[cols].to_numpy(float)
        pr = np.mean([cross_val_predict(LogisticRegression(), X, y, cv=StratifiedKFold(5, shuffle=True,
                                         random_state=r), method="predict_proba")[:, 1] for r in range(5)], axis=0)
        print(f"  CV logistic on {cols}: {auc(y, pr)}")
    # partial: does the locked score still rank within ET-volume tertiles (ET-present)?
    pe = P[m].copy()
    ye = y[m]
    tert = pd.qcut(pe.log_et_cc, 2, labels=False)
    for k in range(2):
        mm = (tert == k).to_numpy()
        print(f"  ET-present, log ET half {k}: A-Iscan {auc(ye[mm], pe['A-Iscan@grade4'][mm])}, "
              f"Ipure {auc(ye[mm], pe['Ipure'][mm])}, logratio_prev_et {auc(ye[mm], pe.logratio_prev_et[mm])}")
    print("  Spearman(log_et_cc, score) primary set:",
          {c: round(P[c].corr(P.log_et_cc, method="spearman"), 3) for c in ARMS_A + ARMS_B})

    # ---------------------------------------------------------------- MU comparison
    print("\n=== MU comparison (grade 4 detection training rows)")
    try:
        from prism.analyses import detection as D
        from prism.features.tabular import measurement_groups
        d, X, _, _, F = D.context("grade4", "primary")
        mg = measurement_groups(d)
        lab = d.label_120.to_numpy()
        ok = ~np.isnan(lab)
        etc = mg["volumes"]["log_et_cc"].to_numpy()
        ym = lab[ok].astype(int)
        print("  MU rows", ok.sum(), "pos", ym.sum(), "phase cols:", [c for c in d.columns if "phase" in c][:6])
        print("  MU log_et_cc AUC (all phases):", auc(ym, etc[ok]))
        print(f"  MU ET absent: pos {(etc[ok][ym == 1] == 0).mean():.2f}, neg {(etc[ok][ym == 0] == 0).mean():.2f}")
        print("  MU ET-present indicator AUC:", auc(ym, (etc[ok] > 0).astype(float)))
        print("  MU logratio_prev_et AUC:", auc(ym, F.logratio_prev_et.to_numpy()[ok]))
        if "phase" in d:
            late = d.phase.astype(str).str.contains("later").to_numpy() & ok
            yl = lab[late].astype(int)
            print("  MU later post-RT: log_et_cc", auc(yl, etc[late]), "ET absent pos/neg %.2f/%.2f" % (
                (etc[late][yl == 1] == 0).mean(), (etc[late][yl == 0] == 0).mean()))
            print("  MU later post-RT: logratio_prev_et", auc(yl, F.logratio_prev_et.to_numpy()[late]))
        dd = d.days_from_diagnosis.to_numpy() if "days_from_diagnosis" in d else None
        if dd is not None:
            print("  MU days from diagnosis AUC:", auc(ym, dd[ok]))
        # How close is the MU progression date to the positive scan? (positive = first scan on/after it)
        from prism.analyses.diagnostics_imaging import scan_table
        st = scan_table(D._base()[0]).set_index("scan_id")
        gap = (d.mri_day - st.progression_day.reindex(d.scan_id).to_numpy()).to_numpy()[ok][ym == 1]
        print("  MU positives: scan day - progression day, median (IQR) %.0f (%.0f-%.0f); <= 1 d: %d/%d" % (
            np.median(gap), *np.percentile(gap, [25, 75]), (gap <= 1).sum(), len(gap)))
        etv = np.expm1(etc[ok])
        print("  MU ET cc median (IQR): pos %.2f (%.2f-%.2f), neg %.2f (%.2f-%.2f)" % (
            np.median(etv[ym == 1]), *np.percentile(etv[ym == 1], [25, 75]), np.median(etv[ym == 0]),
            *np.percentile(etv[ym == 0], [25, 75])))
        print("  MU days_from_prev median: pos %.0f neg %.0f" % (np.nanmedian(d.days_from_prev.to_numpy()[ok][ym == 1]),
                                                            np.nanmedian(d.days_from_prev.to_numpy()[ok][ym == 0])))
        uet = P.et_cc.to_numpy()
        print("  UCSF ET cc median (IQR): pos %.2f (%.2f-%.2f), neg %.2f (%.2f-%.2f)" % (
            np.median(uet[y == 1]), *np.percentile(uet[y == 1], [25, 75]), np.median(uet[y == 0]),
            *np.percentile(uet[y == 0], [25, 75])))
        lr = F.logratio_prev_et.to_numpy()[ok]
        print("  logratio_prev_et median: MU pos %.2f neg %.2f; UCSF pos %.2f neg %.2f" % (
            np.median(lr[ym == 1]), np.median(lr[ym == 0]), P.logratio_prev_et[y == 1].median(),
            P.logratio_prev_et[y == 0].median()))
    except Exception as e:  # noqa: BLE001
        print("  MU comparison failed:", repr(e))

    # ---------------------------------------------------------------- 7. leakage / mismatch checks
    print("\n=== 7. code-level checks")
    from prism.features.ucsf_imaging import ucsf_paths
    samp = P.sample(6, random_state=1)
    bad = 0
    for _, r in samp.iterrows():
        for tp in (1, 2):
            sid = r.subject_id
            seg = np.rint(np.asarray(nib.load(str(ucsf_paths(sid, tp)["mask"])).dataobj)).astype(np.int16)
            et_cc = (seg == 3).sum() / 1000
            row = f[f.scan_id.eq(f"{sid}_time{tp}")].iloc[0]
            bad += abs(et_cc - row.et_cc) > 1e-9
            if tp == 2:
                bad += abs(et_cc - r.et_cc) > 1e-9  # row used in analysis is time2
                prev = f[f.scan_id.eq(f"{sid}_time1")].iloc[0]
                exp = np.log((r.et_cc + 0.1) / (prev.et_cc + 0.1))
                bad += abs(exp - r.logratio_prev_et) > 1e-9
    print(f"  6 random primary patients: seg-recomputed ET (time1, time2) and logratio mismatches: {bad}")
    print("  primary rows all timepoint 2:", bool(P.timepoint.eq(2).all()), "; one row per patient:",
          bool(P.subject_id.is_unique))
    # scan-2 days from diagnosis > scan-1 for every patient
    w = s.pivot(index="subject_id", columns="timepoint", values="days_from_diagnosis_to_mri").dropna()
    print("  days_from_diagnosis scan2 > scan1 in all patients:", bool((w[2] > w[1]).all()))
    # ET subtraction map direction agrees with sign of ET change (time2 - time1)
    t2f = f[f.timepoint.eq("time2")]
    inc = t2f.get("t1ce_subtraction_seg_vox1", 0).fillna(0)
    dec = t2f.get("t1ce_subtraction_seg_vox2", 0).fillna(0)
    nz = (inc + dec) > 0
    print("  sign(subtraction inc - dec) == sign(logratio_prev_et), non-empty maps: %.2f (n=%d)" % (
        (np.sign(inc - dec) == np.sign(t2f.logratio_prev_et))[nz].mean(), nz.sum()))
    # Does any image feature column correlate perfectly with the label (label leakage)?
    feats = [c for c in f.columns if c not in ("scan_id", "SubjectID", "timepoint")]
    a = {c: roc_auc_score(y, P[c].fillna(P[c].median())) for c in feats if P[c].nunique() > 1}
    top = sorted(a.items(), key=lambda kv: -abs(kv[1] - 0.5))[:8]
    print("  most label-associated image columns (any, incl. checks):", [(k, round(v, 3)) for k, v in top])
    # Part B folds: patient-grouped? (scan-2 sets have one row per patient; all-scan set checked via code)
    oof = pd.read_csv(R / "internal" / "oof.csv.gz")
    for n, g in oof.groupby("set"):
        pid = g.scan_id.str.split("_").str[0]
        print(f"  oof set {n}: rows {len(g)}, scan_id unique {g.scan_id.is_unique}, patients {pid.nunique()}")


# ---------------------------------------------------------------- EXPLORATORY (2026-10-26): CIs within "ET Increased"
DEEP_LOCKED = ("MU_G1", "MU_G3")
DEEP_UCSF = ("G1", "G3", "T1")


def _boot_rows(y, scores, groups, n_boot=1000, seed=20261025):
    """Patient-cluster bootstrap on shared draws. A score is (R x n): AUC = mean over the R rows (R = 1 for a single
    score), as in prism.analyses.ucsf_deep.boot."""
    auc_ = lambda S, i: float(np.mean([roc_auc_score(y[i], s[i]) for s in S]))
    rng = np.random.default_rng(seed)
    by = {g: np.where(groups == g)[0] for g in np.unique(groups)}
    pats = np.array(list(by))
    draws = {k: [] for k in scores}
    for _ in range(n_boot):
        i = np.concatenate([by[p] for p in rng.choice(pats, len(pats))])
        if len(np.unique(y[i])) < 2:
            continue
        for k, S in scores.items():
            draws[k].append(auc_(S, i))
    ia = np.arange(len(y))
    return [{"arm": k, "auc": auc_(S, ia), "lo": np.percentile(draws[k], 2.5), "hi": np.percentile(draws[k], 97.5),
             "n_draws": len(draws[k]), "n_pos": int(y.sum()), "n_neg": int((1 - y).sum())} for k, S in scores.items()]


def within_et_increased(out_csv=True):
    """CIs for every image arm within scans UCSF rated "ET Increased" at scan 2 (primary label, scan 2), grade 4 and
    all gliomas. Locked arms use the population's own locked models (@grade4 / @all_glioma). UCSF-trained tabular arms:
    Part B OOF averaged over the 5 repeats (ranking only, as in the rest of this audit). Deep arms: locked = mean logit of
    the 4 MU networks; UCSF-trained = (R x n) outer-test logits, AUC = mean over repeats (as in ucsf_deep.evaluate)."""
    from prism.analyses import ucsf_deep as ud
    s = pd.read_csv(U / "scans.csv", dtype={"subject_id": str})
    f = pd.read_csv(U / "imaging_features.csv", dtype={"SubjectID": str})
    sc = pd.read_csv(R / "locked" / "scores.csv", dtype={"patient_id": str})
    oof_all = pd.read_csv(R / "internal" / "oof.csv.gz")
    upop = ud.UPop()
    deep = {}
    for arm in DEEP_LOCKED:
        z = np.load(ud.locked_path(arm))
        assert (z["scan_id"] == upop.scan_id).all()
        deep[f"deep locked_{arm[3:]}"] = z["logit"].mean(0)[None]
    for arm in DEEP_UCSF:
        nrep = ud.complete_repeats(arm)
        if nrep:
            deep[f"deep UCSF {arm}" + (" (transfer)" if arm == "T1" else "")] = ud.collect(arm, upop, nrep)[0]
    pos_deep = {sid: j for j, sid in enumerate(upop.scan_id)}
    u = s.merge(f[["scan_id", "log_et_cc"]], on="scan_id", validate="one_to_one").merge(sc, on="scan_id",
                                                                                        validate="one_to_one",
                                                                                        suffixes=("", "_sc"))
    u["neg"] = u.neg_class.isin(NEG)
    rows = []
    for pop, mask, setname, mod in (("grade4", u.grade4.astype(bool), "grade4|scan2|pos_s2_pm30", "grade4"),
                                    ("all_glioma", pd.Series(True, index=u.index), "all|scan2|pos_s2_pm30",
                                     "all_glioma")):
        P = u[u.timepoint.eq(2) & mask & (u.pos_s2_pm30.eq(1) | u.neg)].copy()
        o = oof_all[oof_all.set.eq(setname)].set_index("scan_id")
        assert len(o) == len(P) and set(o.index) == set(P.scan_id), (pop, len(o), len(P))
        o = o.reindex(P.scan_id)
        y_all = P.pos_s2_pm30.eq(1).astype(int).to_numpy()
        assert (o.label.to_numpy() == y_all).all()
        inc = P.et_change.eq("Increased").to_numpy()
        y = y_all[inc]
        cols = {f"locked A-{a}": P[f"A-{a}@{mod}"].to_numpy(float)[None] for a in ("Iscan", "Ipure", "Timg", "T")}
        for a in ("Iscan", "Ipure", "Timg"):
            cols[f"UCSF-trained {a}"] = o[[f"{a}#r{r}" for r in range(5)]].mean(axis=1).to_numpy(float)[None]
        di = np.array([pos_deep[sid] for sid in P.scan_id])
        cols.update({k: v[:, di] for k, v in deep.items()})
        cols["log ET volume"] = P.log_et_cc.to_numpy(float)[None]
        sc_ = {k: v[:, inc] for k, v in cols.items()}
        assert all(np.isfinite(v).all() for v in sc_.values())
        print(f"\n=== within ET Increased, {pop}: n = {inc.sum()} ({y.sum()} pos / {(1 - y).sum()} neg), "
              f"of {len(P)} primary-set scans")
        for r in _boot_rows(y, sc_, P.subject_id.to_numpy()[inc]):
            r.update(population=pop, subset="ET Increased", n_scans=int(inc.sum()))
            rows.append(r)
            print(f"  {r['arm']:28s} {r['auc']:.3f} ({r['lo']:.3f}-{r['hi']:.3f}) [{r['n_pos']}/{r['n_neg']}]")
    res = pd.DataFrame(rows)
    if out_csv:
        (R / "audit").mkdir(exist_ok=True)
        res.to_csv(R / "audit" / "within_et_increased_cis.csv", index=False)
    return res


if __name__ == "__main__":
    import sys
    if "--within-et-increased" in sys.argv:  # EXPLORATORY 2026-10-26 section only
        within_et_increased()
    else:
        main()
        within_et_increased()
