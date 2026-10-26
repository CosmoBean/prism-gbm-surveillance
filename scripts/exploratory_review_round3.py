"""EXPLORATORY (added after internal review round 3, 2026-10-26; not pre-specified): analyses requested by
docs/manuscript/council/round3_reviewer2.md (M2, M3, M4, M6; NUMBERS.md mismatch 8).

Populations as in prism/analyses/system.py: MU grade-4 intended use (out-of-fold, 5 repeats, mean over repeats),
LUMIERE detection (locked), UCSF grade-4 scan 2 pos_s2_pm30 vs primary negatives (locked).
Bootstrap: patient-cluster, 1,000 draws; draw i resamples patients with the first call of rng([system.SEED, i]),
exactly as system.boot_job (A, B, C, D). F reuses the UCSF plan's calibration bootstrap (ucsf_external.SEED) so that
the pre-specified UCSF row reproduces; E uses detection.evaluate_set (seed 20261021) so that it is paired with the
existing ladder intervals.

  A  agreement rule with medians fixed on MU instead of each cohort's own evaluation-set median.
     MU: the pre-specified rule already uses the MU OOF median (its rows are those of selective.csv); added here a
     fold-held-out variant (median of the OOF scores of the other four folds of the same repeat).
     External: median of each locked pathway model's scores on its MU training rows (grade-4 detection, positives +
     primary negatives); LUMIERE images use the T_img median, and the 3-volume model's median at its 10 scans.
     Flags: disagreement alone, and disagreement AND combined conformal set {0, 1} (alpha 0.2). S2 / S3 as system.py.
  B  class-conditional coverage of the combined conformal set at alpha 0.2 (standard and Mondrian), with CIs.
  C  raw single-input scores, direction fixed (larger = progression): log ET volume; log ET ratio to the previous scan
     (0 where there is no previous scan, as in the model inputs; also on scans with a previous scan only).
  D  sensitivity / specificity of the combined score at the MU median threshold (MU: OOF median over the
     intended-use set per repeat, as S4; external: median of the locked combined model on its MU training rows).
  E  ladder middle step: I_pure - I_scan on MU-IU, paired patient bootstrap (plus I - I_pure as a check).
  F  calibration slope and O/E of the locked combined model on LUMIERE (new) and UCSF (pre-specified secondary).

    PYTHONPATH=. OMP_NUM_THREADS=1 .venv/bin/python scripts/exploratory_review_round3.py [--workers 8]
    -> outputs/results/analyses/review_round3/   (aggregate numbers only)
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from prism.analyses import detection as D
from prism.analyses import reliability_card as RC
from prism.analyses import system as S
from prism.analyses import ucsf_external as UX
from prism.config import RESULTS

OUT = RESULTS / "analyses" / "review_round3"
STATUS = "EXPLORATORY: requested in internal review round 3 (2026-10-26), not pre-specified"
SETS = {"mu": "intended_use", "lumiere": "all", "ucsf": "scan2_pm30"}
EXP_LOG_ET_UCSF = 0.878  # UCSF_AUDIT.md section 6


# ---------------------------------------------------------------- shared
def draws(g, n_boot):
    """Patient resamples of system.boot_job: draw i = first call of rng([SEED, i]) on the sorted patients."""
    by = {p: np.where(g == p)[0] for p in np.unique(g)}
    pats = np.array(sorted(by))
    for i in range(n_boot):
        rng = np.random.default_rng([S.SEED, i])
        yield np.concatenate([by[p] for p in rng.choice(pats, len(pats))])


def ci(v):
    return S.ci(np.asarray(v, float))


def eval_view(c):
    m = c["eval"][SETS[c["cohort"]]]
    return m, c["y"][m].astype(int), c["patient_id"][m]


# ---------------------------------------------------------------- A: MU-fixed medians
def locked_mu_medians():
    """{cohort: {pathway: median on MU training rows}} of the locked models, and a scores check."""
    out, chk = {}, []
    # LUMIERE
    L, LX, _ = D.lumiere_detection()
    dm, X, *_ = D.context("grade4", "primary")
    timg = [c for c in X["T"].columns if c not in D.T_BASE + ["has_prev", "log_days_from_prev"]]
    Xmu = {"timeline": X["T"][D.T_BASE], "images": X["T"][timg], "combined": X["T"], "images_scan": X["T"][S.VOL3]}
    Xl = {"timeline": LX[D.T_BASE], "images": LX[timg], "combined": LX, "images_scan": LX[S.VOL3]}
    mods = S.locked_models(Xmu, dm)
    tr = dm.label_120.notna().to_numpy()
    out["lumiere"] = {p: float(np.median(mods[p][0](Xmu[p][tr]))) for p in Xmu}
    out["lumiere_scores"] = {p: mods[p][0](Xl[p]) for p in Xl}
    out["lumiere_nop"] = L.prev_scan_id.eq("").to_numpy()
    out["lumiere_scan_id"] = L.scan_id.to_numpy()
    # UCSF
    d4, A4 = UX.mu_detection("grade4")
    u = UX.ucsf_frame()
    A = UX.ucsf_designs(u, A4)
    keep = (u.timepoint.eq(2) & u.grade4).to_numpy()
    names = {"timeline": "A-Tbase", "images": "A-Ipure", "combined": "A-T"}
    mods = S.locked_models({p: A4[a] for p, a in names.items()}, d4)
    tr = d4.label_120.notna().to_numpy()
    out["ucsf"] = {p: float(np.median(mods[p][0](A4[a][tr]))) for p, a in names.items()}
    out["ucsf_scores"] = {p: mods[p][0](A[a][keep].reset_index(drop=True)) for p, a in names.items()}
    out["ucsf_X"] = A["A-Ipure"][keep].reset_index(drop=True)
    out["ucsf_scan_id"] = u[keep].scan_id.to_numpy()
    out["lumiere_X"] = LX
    out["n_mu_train"] = {"lumiere": int(dm.label_120.notna().sum()), "ucsf": int(tr.sum())}
    return out


def add_agreement_flags(c, M):
    """Append the A flags to c['flags'] (after the five pre-specified flags, so their random streams are unchanged)."""
    Sx = c["S"]
    conf = c["flags"]["conformal"]
    if c["cohort"] == "mu":
        lab = c["median_set"]
        F = c["fold"]
        above = {}
        for p in ("timeline", "images"):
            P = Sx[f"p_{p}"]
            ab = np.zeros_like(P, bool)
            for r in range(P.shape[0]):
                for k in range(5):
                    te = F[r] == k
                    med = np.median(P[r, lab & ~te])
                    ab[r, te] = P[r, te] > med
            above[p] = ab
        dis = above["timeline"] != above["images"]
        c["flags"]["A_disagree_fold_median"] = dis
        c["flags"]["A_disagree_fold_median_and_conformal"] = dis & conf
        return {"rule": "fold-held-out MU OOF median"}
    k = c["cohort"]
    med = M[k]
    if k == "lumiere":
        mi = np.where(M["lumiere_nop"], med["images_scan"], med["images"])
    else:
        mi = med["images"]
    dis = (Sx["p_timeline"] > med["timeline"]) != (Sx["p_images"] > mi)
    c["flags"]["A_disagree_mu_median"] = dis
    c["flags"]["A_disagree_mu_median_and_conformal"] = dis & conf
    own = c["flags"]["disagree"]
    m = c["eval"][SETS[k]]
    return {"rule": "MU training-set median of the locked models", "medians_mu": {p: med[p] for p in med},
            "medians_own": {p: float(v[0]) for p, v in c["medians"].items()},
            "share_status_changed": float((dis[:, m] != own[:, m]).mean())}


# ---------------------------------------------------------------- B: class-conditional coverage
def class_coverage(c, n_boot):
    m, y, g = eval_view(c)
    rows = []
    for kind in ("std", "mon"):
        h0, h1 = c["sets"][(kind, "combined", 0.2, 0)][:, m], c["sets"][(kind, "combined", 0.2, 1)][:, m]
        hit = np.where(y == 1, h1, h0)
        single = h0 ^ h1
        stat = lambda idx: [hit[:, idx][:, y[idx] == cl].mean() for cl in (1, 0)] + \
                           [hit[:, idx].mean()] + [single[:, idx][:, y[idx] == cl].mean() for cl in (1, 0)]
        pt = stat(np.arange(len(y)))
        B = np.array([stat(idx) for idx in draws(g, n_boot)])
        for j, name in enumerate(("coverage_progression", "coverage_non_progression", "coverage_all",
                                  "singleton_progression", "singleton_non_progression")):
            lo, hi = ci(B[:, j])
            rows.append({"cohort": c["cohort"], "kind": "standard" if kind == "std" else "mondrian",
                         "alpha": 0.2, "quantity": name, "value": float(pt[j]), "lo": lo, "hi": hi,
                         "n_pos": int(y.sum()), "n_neg": int((y == 0).sum()),
                         "below_0.78": bool(pt[j] < 0.78) if name.startswith("coverage") else None})
    return rows


# ---------------------------------------------------------------- C: raw ET baselines
def et_scores(c, M):
    """{name: (score over the cohort's rows, mask of usable rows)}."""
    k = c["cohort"]
    if k == "mu":
        X = S.mu_designs("grade4")[1]["images"]
        hp = c["d"].prev_scan_id.fillna("").ne("").to_numpy()
    elif k == "lumiere":
        assert (M["lumiere_scan_id"] == c["scan_id"]).all()
        X = M["lumiere_X"]
        hp = ~M["lumiere_nop"]
    else:
        assert (M["ucsf_scan_id"] == c["scan_id"]).all()
        X = M["ucsf_X"]
        hp = np.ones(len(X), bool)
    et, lr = X.log_et_cc.to_numpy(float), X.logratio_prev_et.to_numpy(float)
    return {"log_et_volume": (et, np.isfinite(et)), "log_et_ratio_prev": (lr, np.isfinite(lr)),
            "log_et_ratio_prev|with_previous": (lr, np.isfinite(lr) & hp)}


def et_baselines(c, M, n_boot):
    m, y, g = eval_view(c)
    rows = []
    for name, (s, ok) in et_scores(c, M).items():
        s, ok = s[m], ok[m]
        yy, ss, gg = y[ok], s[ok], g[ok]
        pt = S.R.auc(yy, ss)
        B = [S.R.auc(yy[idx], ss[idx]) for idx in draws(gg, n_boot)]
        lo, hi = ci(B)
        rows.append({"cohort": c["cohort"], "score": name, "direction": "larger = progression", "auc": pt,
                     "auc_lo": lo, "auc_hi": hi, "n_scans": int(ok.sum()), "n_pos": int(yy.sum()),
                     "n_neg": int((yy == 0).sum())})
    return rows


# ---------------------------------------------------------------- D: sensitivity / specificity at the MU median
def operating_point(c, M, n_boot):
    m, y, g = eval_view(c)
    P = c["S"]["p_combined"][:, m]
    if c["cohort"] == "mu":
        thr = np.median(P, axis=1, keepdims=True)
        tdesc = f"MU OOF median over MU-IU per repeat (mean {float(thr.mean()):.3f})"
    else:
        thr = np.full((1, 1), M[c["cohort"]]["combined"])
        tdesc = f"median of the locked combined model on its MU training rows ({float(thr[0, 0]):.3f})"
    call = P > thr

    def stat(idx):
        yi, ci_ = y[idx], call[:, idx]
        return [ci_[:, yi == 1].mean(), (~ci_[:, yi == 0]).mean(), ci_.mean(),
                np.mean([(ci_[r] != yi).mean() for r in range(len(ci_))])]
    pt = stat(np.arange(len(y)))
    B = np.array([stat(idx) for idx in draws(g, n_boot)])
    out = {"cohort": c["cohort"], "threshold": tdesc, "n_pos": int(y.sum()), "n_neg": int((y == 0).sum())}
    for j, name in enumerate(("sensitivity", "specificity", "share_called_positive", "error_rate")):
        lo, hi = ci(B[:, j])
        out.update({name: float(pt[j]), f"{name}_lo": lo, f"{name}_hi": hi})
    if c["cohort"] != "mu":  # reference: the cohort's own median (transductive), point only
        own = P > np.median(P, axis=1, keepdims=True)
        out["sensitivity_own_median"] = float(own[:, y == 1].mean())
        out["specificity_own_median"] = float((~own[:, y == 0]).mean())
    return out


# ---------------------------------------------------------------- F: calibration
def calibration_rows(cohorts, n_boot):
    rows = []
    for k in ("lumiere", "ucsf"):
        c = cohorts[k]
        m, y, g = eval_view(c)
        p = c["S"]["p_combined"][0, m]
        s, oe, citl = UX.calibration(y, p)
        by = {q: np.where(g == q)[0] for q in np.unique(g)}
        pats = np.array(list(by))
        rng = np.random.default_rng(UX.SEED)
        bs = np.array([UX.calibration(y[ii], p[ii])[:2] for ii in
                       (np.concatenate([by[q] for q in rng.choice(pats, len(pats))]) for _ in range(n_boot))])
        (slo, shi), (olo, ohi) = D.ci(bs[:, 0]), D.ci(bs[:, 1])
        rows.append({"cohort": k, "model": "T@grade4" if k == "lumiere" else "A-T@grade4",
                     "status": "PLANNED secondary (UCSF_PLAN.md)" if k == "ucsf" else STATUS,
                     "calibration_slope": s, "slope_lo": slo, "slope_hi": shi, "o_over_e": oe, "oe_lo": olo,
                     "oe_hi": ohi, "calibration_in_the_large": citl, "mean_risk": float(p.mean()),
                     "observed_rate": float(y.mean()), "n_pos": int(y.sum()), "n_neg": int((y == 0).sum())})
    return rows


# ---------------------------------------------------------------- E: ladder middle step
def ladder_job(job):
    from prism.experiments import c3_radiomics as c3
    arm, r = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, arms = ladder_arms()
    f = D.fold_ids(d, r)
    o = np.full(len(d), np.nan)
    for k in range(5):
        tr, te = np.where(f != k)[0], np.where(f == k)[0]
        o[te] = c3.fit_predict(c3.BASELINES[0], d, arms[arm], {}, None, tr, te, seed=r)
    return arm, r, o


def ladder_arms():
    """The arms of scripts/exploratory_pure_imaging_detection.py (same definitions)."""
    from prism.analyses.triage_feasibility import _features_one
    from prism.features.tabular import measurement_groups
    _, _, _, meas = D._base()
    d, X, _, _, F = D.context("grade4", "primary")
    mg = measurement_groups(d)
    by = {p: g.sort_values("mri_day") for p, g in meas.groupby("patient_id")}
    nad = []
    for pid, day in zip(d.patient_id, d.mri_day):
        h = by[pid][by[pid].mri_day <= day]
        f = _features_one(h, day, -np.inf)
        nad.append({"nadir_all_et": f["traj_logratio_nadir_et"], "nadir_all_lesion": f["traj_logratio_nadir_lesion"]})
    nad = pd.DataFrame(nad, index=d.index)
    prevr = F[[c for c in F.columns if c.startswith("logratio_prev_")]]
    return d, {"I": X["I"], "I_scan": pd.concat([mg["volumes"], mg["morphology"]], axis=1),
               "I_pure": pd.concat([mg["volumes"], mg["morphology"], prevr, nad], axis=1)}


def ladder(workers, n_boot):
    d, arms = ladder_arms()
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(ladder_job, [(a, r) for a in arms for r in range(5)]))
    oof = {a: np.full((5, len(d)), np.nan) for a in arms}
    for a, r, o in res:
        oof[a][r] = o
    rows = np.where(D.eval_sets(d, "primary")["intended_use"])[0]
    res, con, _ = D.evaluate_set("intended_use", d, rows, oof, n_boot,
                                 contrasts=[("I_pure", "I_scan"), ("I", "I_pure")])
    return pd.DataFrame(res), pd.DataFrame(con), oof, d


# ---------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--n-boot", type=int, default=S.N_BOOT)
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []

    # E first (independent of the system cohorts)
    lad, lcon, oof, dl = ladder(a.workers, a.n_boot)
    for arm, exp in (("I_scan", 0.659), ("I_pure", 0.709), ("I", 0.806)):
        v = float(lad[lad.arm == arm].auc.iat[0])
        checks.append({"check": f"ladder {arm} AUC (DETECTION_TASK.md)", "value": v, "published": exp,
                       "ok": abs(v - exp) < 0.0006})
    v = lcon[(lcon.contrast == "I - I_pure") & (lcon.subset == "all")].iloc[0]
    checks.append({"check": "ladder I - I_pure CI (NUMBERS.md: +0.097, +0.047 to +0.153)",
                   "value": f"{v['diff']:.3f} ({v.diff_lo:.3f} to {v.diff_hi:.3f})", "published": "0.097 (0.047 to 0.153)",
                   "ok": abs(v["diff"] - 0.097) < 0.0006 and abs(v.diff_lo - 0.047) < 0.0006 and abs(v.diff_hi - 0.153) < 0.0006})
    print(f"ladder {time.time() - t0:.0f}s", flush=True)

    cohorts = {"mu": S.mu_cohort("grade4", a.workers), "lumiere": S.lumiere_cohort(), "ucsf": S.ucsf_cohort()}
    table, _ = RC.load_table()
    for c in cohorts.values():
        S.derive(c, table)
    dev = float(np.nanmax(np.abs(oof["I_pure"] - pd.DataFrame(cohorts["mu"]["S"]["p_images"].T,
                                                              index=cohorts["mu"]["scan_id"]).reindex(dl.scan_id).to_numpy().T)))
    checks.append({"check": "ladder I_pure OOF vs system MU image pathway (max dev; informational)", "value": dev,
                   "published": 0.0, "ok": True})
    M = locked_mu_medians()
    for k in ("lumiere", "ucsf"):
        for p in S.PW:
            ref = cohorts[k]["S"][f"p_{p}"][0]
            new = M[f"{k}_scores"][p]
            if k == "lumiere" and p == "images":
                new = np.where(M["lumiere_nop"], M["lumiere_scores"]["images_scan"], new)
            dv = float(np.abs(new - ref).max())
            checks.append({"check": f"{k} locked {p} rebuilt == system scores (max dev)", "value": dv,
                           "published": 0.0, "ok": dv < 1e-9})
    print(f"cohorts {time.time() - t0:.0f}s", flush=True)
    ch = pd.DataFrame(checks)
    print(ch.to_string(index=False), flush=True)
    assert ch.ok.all(), "checks failed; stopping before evaluation"

    # A
    published = pd.read_csv(S.OUT / "selective.csv")
    reduced = pd.read_csv(S.OUT / "exploratory_reduced_flags" / "selective.csv")
    sel, agree_info = [], {}
    for k, c in cohorts.items():
        agree_info[k] = add_agreement_flags(c, M)
        res = S.evaluate_set(c, SETS[k], a.workers, a.n_boot, S.N_REF, S.N_DRAW)
        rows = pd.DataFrame(res["selective"])
        pub = published[(published.cohort == k) & (published.population == "grade4") & (published.set == SETS[k])]
        for orig in ("disagree", "conformal"):
            x, y_ = rows[rows.flag == orig].iloc[0], pub[pub.flag == orig].iloc[0]
            dv = max(abs(float(x[f]) - float(y_[f])) for f in ("S2_diff", "S2_lo", "S2_hi", "S3_diff", "S3_lo", "S3_hi"))
            checks.append({"check": f"{k}|{orig}: S2 / S3 == selective.csv (max dev)", "value": dv, "published": 0.0,
                           "ok": dv < 1e-9})
        keep = rows[rows.flag.str.startswith("A_") | rows.flag.eq("disagree")].copy()
        keep["flag"] = keep.flag.replace({"disagree": "own_median_disagree (pre-specified)"})
        d4 = reduced[(reduced.cohort == k) & (reduced.flag == "D4_disagree_and_conformal")].copy()
        d4["flag"] = "own_median_disagree_and_conformal (reduced D4)"
        sel.append(pd.concat([keep, d4[[c_ for c_ in keep.columns if c_ in d4.columns]]]))
        # B points must equal conformal.csv
        cv = pd.DataFrame(res["conformal"])
        cv = cv[(cv.kind == "standard") & (cv.pathway == "combined") & (cv.alpha == 0.2)].iloc[0]
        pc = pd.read_csv(S.OUT / "conformal.csv")
        pc = pc[(pc.cohort == k) & (pc.population == "grade4") & (pc.kind == "standard") & (pc.pathway == "combined")
                & (pc.alpha == 0.2)].iloc[0]
        dv = abs(cv.coverage_events - pc.coverage_events) + abs(cv.coverage_non_events - pc.coverage_non_events)
        checks.append({"check": f"{k}: class coverage == conformal.csv", "value": float(dv), "published": 0.0,
                       "ok": dv < 1e-9})
        print(f"A {k} {time.time() - t0:.0f}s", flush=True)
    sel = pd.concat(sel)
    sel.insert(0, "status", STATUS)

    # B, C, D, F
    cov = pd.DataFrame([r for c in cohorts.values() for r in class_coverage(c, a.n_boot)])
    et = pd.DataFrame([r for c in cohorts.values() for r in et_baselines(c, M, a.n_boot)])
    v = float(et[(et.cohort == "ucsf") & (et.score == "log_et_volume")].auc.iat[0])
    checks.append({"check": "UCSF log ET AUC (UCSF_AUDIT.md section 6)", "value": v, "published": EXP_LOG_ET_UCSF,
                   "ok": abs(v - EXP_LOG_ET_UCSF) < 0.0006})
    op = pd.DataFrame([operating_point(c, M, a.n_boot) for c in cohorts.values()])
    cal = pd.DataFrame(calibration_rows(cohorts, a.n_boot))
    pcal = pd.read_csv(RESULTS / "analyses" / "ucsf" / "locked" / "calibration.csv")
    pcal = pcal[pcal.set.str.startswith("grade4|scan2|pm30") & pcal.arm.eq("A-T")].iloc[0]
    u = cal[cal.cohort == "ucsf"].iloc[0]
    dv = max(abs(u[f] - pcal[f]) for f in ("calibration_slope", "slope_lo", "slope_hi", "o_over_e", "oe_lo", "oe_hi"))
    checks.append({"check": "UCSF A-T calibration == ucsf/locked/calibration.csv (max dev)", "value": float(dv),
                   "published": 0.0, "ok": dv < 1e-9})
    ch = pd.DataFrame(checks)
    ch.to_csv(OUT / "checks.csv", index=False)
    print(ch.to_string(index=False), flush=True)
    assert ch.ok.all(), ch[~ch.ok]

    for name, df in (("A_agreement_mu_fixed.csv", sel), ("B_class_conditional_coverage.csv", cov),
                     ("C_et_baselines.csv", et), ("D_operating_point.csv", op), ("F_calibration.csv", cal),
                     ("E_ladder_auc.csv", lad), ("E_ladder_contrasts.csv", lcon)):
        if "status" not in df.columns:
            df.insert(0, "status", STATUS)
        df.to_csv(OUT / name, index=False)
    pd.set_option("display.width", 250)
    print(sel[["cohort", "flag", "flagged_share", "auc_unflagged", "auc_flagged", "S2_diff", "S2_lo", "S2_hi",
               "S3_diff", "S3_lo", "S3_hi", "min_flagged_pos_neg"]].round(3).to_string(index=False))
    print(json.dumps(agree_info, indent=1, default=float))
    for df in (cov, et, op, cal, lad, lcon):
        print(df.drop(columns=["status"]).round(3).to_string(index=False))
    (OUT / "run_info.json").write_text(json.dumps({"status": STATUS, "n_boot": a.n_boot, "seed": S.SEED,
                                                   "agreement": agree_info, "n_mu_train_rows": M["n_mu_train"],
                                                   "seconds": round(time.time() - t0)}, indent=1, default=float))


if __name__ == "__main__":
    main()
