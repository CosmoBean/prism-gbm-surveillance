"""S1. A segmentation stage: PRISM from the images (plan: docs/results/SEGMENTER_STAGE_PLAN.md, commit b5225c7).

Segmenter  MONAI BraTS21 Swin UNETR (prism.features.reseg; MU maps of E5 reused, LUMIERE and UCSF added).
Inputs     prism.features.seg_measurements: the 27 image measurements minus the five that need the resection cavity
           (CAVITY_INPUTS) = 22 "segmenter inputs", the same set in every cohort.
Models     refitted on MU in the same 5x5 patient-grouped folds, intended use (146 scans):
             images    released: A-Ipure (27)                       segmenter: the 22 segmenter inputs
             combined  reduced form. released: T (detection.T_BASE + three volumes, their change, has_prev,
                       log days from prev); segmenter: T_BASE + has_prev + log days from prev + the 22 inputs
             baseline  timing-and-enhancement (E4 reader): MU phase dummies + log ET + its log ratio to the previous
                       scan; locked: early_post_rt + log ET + log ratio + has_prev (E4 LUMIERE design)
             combined_full (MU only, exploratory): B1 + images, the paper's MU combined model
           locked: one fit on all MU training rows (system._fit), applied unchanged to LUMIERE (178 scans) and UCSF
           (grade 4 scan 2, 69 scans). Released LUMIERE images = the paper's score (T_img, 3-volume model without a
           previous scan); released UCSF images = A-Ipure.
P1         paired segmenter - released AUC per cohort and score; combined - baseline gain under each mask set.
P2         median ET and WT Dice against the released masks.
P3         median fold change of the enhancing volume, consecutive scans <= 30 days apart (MU, LUMIERE).
Exploratory: calibration (slope, O/E, intercept) of the locked models.
One 2,000-sample patient bootstrap per cohort (seed 20261119) covers both mask sets, so differences are paired.
The MU models are fitted in a separate process per mask set (PRISM_MEASUREMENTS), as E5.

    PYTHONPATH=. .venv/bin/python -m prism.analyses.segmenter_stage [--workers 20] [--n-boot 2000]
    -> outputs/results/analyses/segmenter_stage/
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

import numpy as np
import pandas as pd

from prism.config import RESULTS
from prism.features.seg_measurements import CAVITY_INPUTS, table_path

OUT = RESULTS / "analyses" / "segmenter_stage"
SEED = 20261119
SETS = ("released", "segmenter")
SCORES = ("images", "combined", "baseline")
MU_SCORES = SCORES + ("combined_full",)
T_EXTRA = ["has_prev", "log_days_from_prev"]
BASE_LOCKED = ["early_post_rt", "log_et_cc", "logratio_prev_et", "has_prev"]
REF = {  # released-mask numbers of the paper (METHODS_RESULTS.md E4, E6d; system.EXPECTED; UCSF_RESULTS.md)
    "mu": {"images": 0.709, "combined": 0.804, "baseline": 0.797, "combined_full": 0.821},
    "lumiere": {"images": 0.6539, "combined": 0.7729, "baseline": 0.7342},
    "ucsf": {"images": 0.726, "combined": 0.856}}


# ---------------------------------------------------------------- designs
@lru_cache(maxsize=1)
def mu_designs(mset: str):
    """MU frame, CV designs and locked designs on the measurement table this process reads (config.MEASUREMENTS)."""
    from prism.analyses import clinician_baseline as CB
    from prism.analyses import detection as D
    from prism.analyses import ucsf_external as UX
    d, A4 = UX.mu_detection("grade4")
    X = D.context("grade4", "primary")[1]
    T, b1 = X["T"], X["B1"]
    if mset == "released":
        img, comb = A4["A-Ipure"], T
    else:
        img = A4["A-Ipure"].drop(columns=list(CAVITY_INPUTS))
        comb = pd.concat([T[D.T_BASE + T_EXTRA], img], axis=1)
    cv = {"images": img, "combined": comb, "baseline": CB.mu_reader_design(d, {"images": A4["A-Ipure"]}),
          "combined_full": pd.concat([b1, img], axis=1)}
    return d, A4, T, cv


def lumiere_pool():
    """Studies that can serve as history: rated, not 'Pre-Op' (as detection.lumiere_detection)."""
    from prism.config import LUMIERE_ROOT
    r = pd.read_csv(LUMIERE_ROOT / "LUMIERE-ExpertRating-v202211.csv")
    r.columns = ["patient_id", "date", "lt3m", "nonmeas", "rating", "rationale"]
    r["scan_id"] = r.patient_id + "_" + r.date
    return set(r.loc[r.rating.astype(str).str.strip().ne("Pre-Op"), "scan_id"])


def seg_inputs(meas: pd.DataFrame) -> pd.DataFrame:
    """Segmenter inputs (22) + has_prev + days from the previous scan, per scan of a segmenter measurement table."""
    from prism.features.ucsf_imaging import model_inputs
    mi = model_inputs(meas).set_index("scan_id")
    gap = {}
    for _, g in meas.groupby("patient_id"):
        days = g.mri_day.to_numpy(float)
        for sid, day in zip(g.scan_id, days):
            e = days[days < day]  # strictly earlier, as change_features
            gap[sid] = day - e.max() if len(e) else np.nan
    mi["days_from_prev"] = pd.Series(gap).reindex(mi.index)
    assert (mi.days_from_prev.notna() == (mi.has_prev == 1)).all()
    return mi


def lumiere_seg(L: pd.DataFrame, LX: pd.DataFrame, cols: list) -> dict:
    """LUMIERE designs on the segmenter inputs, rows aligned with detection.lumiere_detection."""
    from prism.analyses import detection as D
    meas = pd.read_csv(table_path("lumiere"))
    meas = meas[meas.scan_id.isin(lumiere_pool())].reset_index(drop=True)
    mi = seg_inputs(meas).reindex(L.scan_id)
    mi.index = L.index
    img = mi[cols].astype(float)
    hp = mi.has_prev.astype(float)
    t = LX[D.T_BASE].copy()
    t["has_prev"] = hp
    t["log_days_from_prev"] = np.log1p(mi.days_from_prev.fillna(0))
    base = pd.DataFrame({"early_post_rt": LX.early_post_rt, "log_et_cc": img.log_et_cc,
                         "logratio_prev_et": img.logratio_prev_et, "has_prev": hp})
    return {"images": img, "combined": pd.concat([t, img], axis=1), "baseline": base,
            "n_without_map": int(mi.log_et_cc.isna().sum()), "n_with_prev": int((hp == 1).sum())}


def ucsf_seg(u: pd.DataFrame, A: dict, keep, cols: list) -> dict:
    from prism.analyses import detection as D
    meas = pd.read_csv(table_path("ucsf"))
    mi = seg_inputs(meas).reindex(u.scan_id[keep])
    mi.index = range(int(keep.sum()))
    T = A["A-T"][keep].reset_index(drop=True)
    img = mi[cols].astype(float)
    base = pd.DataFrame({"early_post_rt": T.early_post_rt, "log_et_cc": img.log_et_cc,
                         "logratio_prev_et": img.logratio_prev_et, "has_prev": T.has_prev})
    return {"images": img, "combined": pd.concat([T[D.T_BASE + T_EXTRA], img], axis=1), "baseline": base,
            "n_without_map": int(mi.log_et_cc.isna().sum())}


# ---------------------------------------------------------------- one mask set (own process)
def cv_job(job):
    from threadpoolctl import threadpool_limits
    from prism.analyses import detection as D
    from prism.experiments import c3_radiomics as c3
    mset, r, k = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, _, _, cv = mu_designs(mset)
    f = D.fold_ids(d, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    return r, te, {p: c3.fit_predict(c3.BASELINES[0], d, X, {}, None, tr, te, seed=r) for p, X in cv.items()}


def predict(mset: str, workers: int) -> None:
    from prism.analyses import detection as D
    from prism.analyses import system as S
    from prism.analyses import ucsf_external as UX
    from prism.config import MEASUREMENTS
    want = table_path("mu") if mset == "segmenter" else None
    assert (want is None and "PRISM_MEASUREMENTS" not in os.environ) or MEASUREMENTS == want, MEASUREMENTS
    warnings.filterwarnings("ignore")
    d, A4, T, cv = mu_designs(mset)
    n = len(d)
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(cv_job, [(mset, r, k) for r in range(5) for k in range(5)]))
    P = {p: np.full((5, n), np.nan) for p in MU_SCORES}
    for r, te, pr in res:
        for p, v in pr.items():
            P[p][r, te] = v
    assert all(np.isfinite(v).all() for v in P.values())
    ev = (d.label_120.notna() & d.intended_use).to_numpy()
    rows = np.arange(n)
    info = {"mu_columns": {p: list(X.columns) for p, X in cv.items()}}

    # locked models (one fit on all MU training rows) and the external designs
    L, LX, _ = D.lumiere_detection()
    u = UX.ucsf_frame()
    A = UX.ucsf_designs(u, A4)
    keep = (u.timepoint.eq(2) & u.grade4).to_numpy()
    uk = u[keep].reset_index(drop=True)
    if mset == "released":
        timg = [c for c in T.columns if c not in D.T_BASE + T_EXTRA]
        f_img, f_vol3 = S._fit(T[timg], d, rows), S._fit(T[S.VOL3], d, rows)
        nop = L.prev_scan_id.eq("").to_numpy()
        lum = {"images": np.where(nop, f_vol3(LX[S.VOL3]), f_img(LX[timg])), "combined": S._fit(T, d, rows)(LX),
               "baseline": S._fit(T[BASE_LOCKED], d, rows)(LX)}
        Au = {k: v[keep].reset_index(drop=True) for k, v in A.items()}
        uc = {"images": S._fit(A4["A-Ipure"], d, rows)(Au["A-Ipure"]), "combined": S._fit(T, d, rows)(Au["A-T"]),
              "baseline": S._fit(T[BASE_LOCKED], d, rows)(Au["A-T"])}
        info["lumiere_images"] = "T_img; 3-volume model for the scans without a previous scan"
    else:
        img_cols = list(cv["images"].columns)
        Xmu = {"images": cv["images"], "combined": cv["combined"], "baseline": T[BASE_LOCKED]}
        fits = {p: S._fit(X, d, rows) for p, X in Xmu.items()}
        ls, us = lumiere_seg(L, LX, img_cols), ucsf_seg(u, A, keep, img_cols)
        for p in Xmu:
            assert list(ls[p].columns) == list(us[p].columns) == list(Xmu[p].columns), p
        lum = {p: fits[p](ls[p]) for p in Xmu}
        uc = {p: fits[p](us[p]) for p in Xmu}
        info.update(lumiere_without_map=ls["n_without_map"], lumiere_with_prev=ls["n_with_prev"],
                    ucsf_without_map=us["n_without_map"])
    ucsf_y = np.where(uk.pos_s2_pm30.eq(1), 1.0, np.where(uk.primary_neg, 0.0, np.nan))
    np.savez(OUT / f"preds_{mset}.npz", mu_scan_id=d.scan_id.to_numpy(str), mu_pid=d.patient_id.to_numpy(str),
             mu_y=d.label_120.to_numpy(float), mu_phase=d.phase.astype(str).to_numpy(str), mu_ev=ev,
             lum_scan_id=L.scan_id.to_numpy(str), lum_pid=L.patient_id.to_numpy(str),
             lum_y=L.label_det.to_numpy(float), lum_ctx=np.where(L.early_post_rt.eq(1), "within_3m", "other"),
             ucsf_scan_id=uk.scan_id.to_numpy(str), ucsf_pid=uk.subject_id.to_numpy(str), ucsf_y=ucsf_y,
             ucsf_ctx=uk.rt_phase.astype(str).to_numpy(str), measurements=str(MEASUREMENTS),
             **{f"mu_{p}": v for p, v in P.items()}, **{f"lum_{p}": v for p, v in lum.items()},
             **{f"ucsf_{p}": v for p, v in uc.items()})
    (OUT / f"design_{mset}.json").write_text(json.dumps(info, indent=1))
    print(f"{mset}: MU {n} scans ({int(ev.sum())} evaluated), LUMIERE {len(L)}, UCSF {len(uk)}; table {MEASUREMENTS}")


def run_set(mset: str, workers: int) -> None:
    env = {k: v for k, v in os.environ.items() if k != "PRISM_MEASUREMENTS"}
    if mset == "segmenter":
        env["PRISM_MEASUREMENTS"] = str(table_path("mu"))
    subprocess.run([sys.executable, "-m", "prism.analyses.segmenter_stage", "--predict", mset,
                    "--workers", str(workers)], env=env, check=True)


# ---------------------------------------------------------------- P1
def load_cohorts() -> dict:
    """{cohort: (y, scores {score|set: (R, n)}, context, patient ids)} on the evaluation scans, sets aligned."""
    z = {s: np.load(OUT / f"preds_{s}.npz") for s in SETS}
    a, b = z["released"], z["segmenter"]
    for k in ("mu_scan_id", "mu_pid", "mu_y", "mu_phase", "mu_ev", "lum_scan_id", "lum_y", "ucsf_scan_id", "ucsf_y"):
        assert np.array_equal(a[k], b[k], equal_nan=k.endswith("_y")), f"{k} differs between mask sets"
    out = {}
    ev = a["mu_ev"]
    out["mu"] = (a["mu_y"][ev], {f"{p}|{s}": z[s][f"mu_{p}"][:, ev] for s in SETS for p in MU_SCORES},
                 a["mu_phase"][ev], a["mu_pid"][ev])
    out["lumiere"] = (a["lum_y"], {f"{p}|{s}": z[s][f"lum_{p}"][None, :] for s in SETS for p in SCORES},
                      a["lum_ctx"], a["lum_pid"])
    e = ~np.isnan(a["ucsf_y"])
    out["ucsf"] = (a["ucsf_y"][e], {f"{p}|{s}": z[s][f"ucsf_{p}"][None, e] for s in SETS for p in SCORES},
                   a["ucsf_ctx"][e], a["ucsf_pid"][e])
    return out


def check_reference(cohorts) -> list:
    from prism.analyses.methods import m1_stats
    rows = []
    for c, (y, scores, ctx, pid) in cohorts.items():
        est = m1_stats(y, scores, ctx)
        for p, ref in REF[c].items():
            v = float(est[f"{p}|released"][0])
            rows.append({"cohort": c, "score": p, "paper": ref, "reproduced": v, "ok": abs(v - ref) < 1e-3})
    bad = [r for r in rows if not r["ok"]]
    assert not bad, f"released-mask numbers not reproduced: {bad}"
    return rows


def p1(cohorts, n_boot) -> pd.DataFrame:
    from prism.analyses.methods import boot, ci, m1_stats
    rows = []
    for c, (y, scores, ctx, pid) in cohorts.items():
        est = m1_stats(y, scores, ctx)
        B = boot(y, scores, ctx, pid, n_boot, seed=SEED)
        n = {"n_scans": len(y), "n_pos": int((y == 1).sum()), "n_patients": len(np.unique(pid))}

        def add(kind, score, masks, f):
            lo, hi = ci([f(b) for b in B])
            rows.append({"cohort": c, "kind": kind, "score": score, "masks": masks, "est": f(est), "lo": lo, "hi": hi,
                         **n})

        pw = [p for p in MU_SCORES if f"{p}|released" in scores]
        for p in pw:
            for s in SETS:
                add("auc", p, s, lambda e, k=f"{p}|{s}": e[k][0])
            add("paired_diff", p, "segmenter-released", lambda e, p=p: e[f"{p}|segmenter"][0] - e[f"{p}|released"][0])
        for g in [p for p in pw if p.startswith("combined")]:
            if f"baseline|released" not in scores:
                continue
            for s in SETS:
                add("gain", f"{g}-baseline", s, lambda e, g=g, s=s: e[f"{g}|{s}"][0] - e[f"baseline|{s}"][0])
            add("gain_change", f"{g}-baseline", "segmenter-released",
                lambda e, g=g: (e[f"{g}|segmenter"][0] - e["baseline|segmenter"][0])
                - (e[f"{g}|released"][0] - e["baseline|released"][0]))
    return pd.DataFrame(rows)


def verdict(t: pd.DataFrame) -> dict:
    """The plan's rule. Primary scores only (images, reduced combined, baseline); combined_full is exploratory."""
    d = t[(t.kind == "paired_diff") & t.score.isin(SCORES)]
    fails = d[d.hi < 0][["cohort", "score", "est", "lo", "hi"]].to_dict("records")
    g = t[(t.kind == "gain") & (t.score == "combined-baseline") & t.cohort.isin(["mu", "lumiere"])]
    reading = {}
    for c, q in g.groupby("cohort"):
        excl = {r.masks: bool(r.lo > 0 or r.hi < 0) for r in q.itertuples()}
        reading[c] = {"excludes_0": excl, "same": len(set(excl.values())) == 1}
    ok = not fails and all(v["same"] for v in reading.values())
    return {"reproduces": ok, "paired_ci_below_0": fails, "gain_reading": reading}


# ---------------------------------------------------------------- P2
def p2() -> pd.DataFrame:
    from prism.features.reseg import volumes_path
    rows = []
    for c in ("mu", "lumiere", "ucsf"):
        v = pd.read_csv(volumes_path("brats21", c))
        for comp in ("et", "wt"):
            x = v[f"dice_{comp}"]
            rows.append({"cohort": c, "compartment": comp, "n_scans": len(v), "n_defined": int(x.notna().sum()),
                         "n_released_empty": int((v[f"mu_{comp}_voxels"] == 0).sum()),
                         "dice_median": x.median(), "dice_q25": x.quantile(.25), "dice_q75": x.quantile(.75),
                         "frac_dice_lt_0.5": float((x.dropna() < 0.5).mean())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- P3
def _pairs(tab: pd.DataFrame, max_gap: float = 30) -> pd.DataFrame:
    """Consecutive scans per patient (tab: scan_id, patient_id, day, et_rel, et_seg), gap <= max_gap days."""
    t = tab.sort_values(["patient_id", "day"])
    g = t.groupby("patient_id")
    p = pd.DataFrame({"patient_id": t.patient_id, "gap": t.day - g.day.shift(),
                      **{f"abslog_{s}": np.abs(np.log((t[f"et_{s}"] + 0.1) / (g[f"et_{s}"].shift() + 0.1)))
                         for s in ("rel", "seg")}}).dropna()
    return p[p.gap <= max_gap].reset_index(drop=True)


def p3(n_boot) -> pd.DataFrame:
    from prism.analyses import detection as D
    from prism.analyses.reseg_eval import _cluster_boot
    from prism.config import MEASUREMENTS
    mu_r, mu_s = pd.read_csv(MEASUREMENTS), pd.read_csv(table_path("mu"))
    mu = mu_r[["scan_id", "patient_id", "mri_day", "et_cc"]].merge(mu_s[["scan_id", "et_cc"]], on="scan_id",
                                                                  suffixes=("_rel", "_seg"))
    mu = mu.rename(columns={"mri_day": "day", "et_cc_rel": "et_rel", "et_cc_seg": "et_seg"})
    ls = pd.read_csv(table_path("lumiere"))
    ls = ls[ls.scan_id.isin(lumiere_pool())]
    vol = D.lumiere_volumes().set_index("scan_id").raw_Enhancing_Core / 1000.0
    lu = pd.DataFrame({"scan_id": ls.scan_id, "patient_id": ls.patient_id, "day": ls.mri_day,
                       "et_rel": vol.reindex(ls.scan_id).to_numpy(), "et_seg": ls.et_cc.to_numpy()}).dropna()
    rows = []
    for c, tab in (("mu", mu), ("lumiere", lu)):
        q = _pairs(tab)
        r = {"cohort": c, "n_pairs": len(q), "n_patients": q.patient_id.nunique(), "n_scans_in_pool": len(tab)}
        if len(q) < 3:
            rows.append(r)
            continue
        for s, name in (("rel", "released"), ("seg", "segmenter")):
            lo, hi = _cluster_boot(q, lambda d, s=s: d[f"abslog_{s}"].median(), n_boot, seed=SEED)
            r.update({f"fold_{name}": float(np.exp(q[f"abslog_{s}"].median())), f"fold_{name}_lo": float(np.exp(lo)),
                      f"fold_{name}_hi": float(np.exp(hi))})
        r["d_median_abslog"] = q.abslog_seg.median() - q.abslog_rel.median()
        r["d_lo"], r["d_hi"] = _cluster_boot(q, lambda d: d.abslog_seg.median() - d.abslog_rel.median(), n_boot,
                                             seed=SEED)
        rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- exploratory: calibration
def calibration(cohorts) -> pd.DataFrame:
    from prism.analyses.ucsf_external import calibration as cal
    rows = []
    for c, (y, scores, _, _) in cohorts.items():
        for k, P in scores.items():
            v = np.array([cal(y[~np.isnan(p)], p[~np.isnan(p)]) for p in P])
            p, s = k.split("|")
            rows.append({"cohort": c, "score": p, "masks": s, "slope": v[:, 0].mean(), "o_e": v[:, 1].mean(),
                         "intercept": v[:, 2].mean(), "repeats": len(P)})
    return pd.DataFrame(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="prism.analyses.segmenter_stage", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--predict", choices=SETS, help=argparse.SUPPRESS)
    ap.add_argument("--skip-predict", action="store_true", help="reuse preds_<set>.npz")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.predict:
        return predict(a.predict, a.workers)
    t0 = time.time()
    assert "PRISM_MEASUREMENTS" not in os.environ, "run the comparison with the default table"
    if not a.skip_predict:
        for s in SETS:
            run_set(s, a.workers)
    cohorts = load_cohorts()
    ref = check_reference(cohorts)
    pd.DataFrame(ref).to_csv(OUT / "s1_reference_check.csv", index=False)
    t = p1(cohorts, a.n_boot)
    t.to_csv(OUT / "s1_p1.csv", index=False)
    v = verdict(t)
    d2 = p2()
    d2.to_csv(OUT / "s1_p2_dice.csv", index=False)
    d3 = p3(a.n_boot)
    d3.to_csv(OUT / "s1_p3_repeatability.csv", index=False)
    cb = calibration(cohorts)
    cb.to_csv(OUT / "s1_calibration.csv", index=False)
    (OUT / "run_info.json").write_text(json.dumps({"n_boot": a.n_boot, "seed": SEED, "seconds": round(time.time() - t0),
                                                   "verdict": v}, indent=1, default=str))
    pd.set_option("display.width", 220)
    for x in (pd.DataFrame(ref), t, d2, d3, cb):
        print(x.round(3).to_string(index=False), "\n")
    print(json.dumps(v, indent=1, default=str))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
