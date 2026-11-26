"""S1 / S4. A segmentation stage: PRISM from the images.

Segmenter swin (S1, default; plan docs/results/SEGMENTER_STAGE_PLAN.md, commit b5225c7) or brats24 (S4; plan
docs/results/SEGMENTER_BRATS24_PLAN.md). The S1 description follows; S4 differences are listed after it.

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

S4 (--segmenter brats24): BraTS24_1 maps (labels 1 NETC, 2 SNFH, 3 ET, 4 RC), so the segmenter inputs are all 27
image inputs. Seed 20261120. Prediction sets, all in the same bootstrap per cohort:
  released     the released masks (as S1)
  segmenter    BraTS24, 27 inputs                                   P1 (segmenter - released)
  swin         Swin UNETR, its 22 inputs (S1's code path)           P4 (segmenter - swin)
  segmenter22  BraTS24 on the 22 cavity-free inputs                 exploratory
MU is required (the models are fitted on it); LUMIERE and UCSF are used when their measurement table covers the run's
scope, otherwise skipped and reported. The MU table is the scope only; the model process reads it padded to the
released scan set (scans outside the scope keep their released measurements, so the MU frame is unchanged; they are
never fitted, evaluated or used as history), and every labelled and evaluated MU row and every earlier scan of its
patient must have a BraTS24 row. P2 adds RC Dice (where the released mask has a cavity; not LUMIERE) and Swin UNETR's Dice
on the same scans; P3 adds Swin UNETR on the same pairs; P4 adds paired Dice differences.

    PYTHONPATH=. .venv/bin/python -m prism.analyses.segmenter_stage [--segmenter swin|brats24] [--workers 20]
        [--n-boot 2000] [--out DIR]
    -> outputs/results/analyses/segmenter_stage/   (swin)
       outputs/results/analyses/segmenter_brats24/ (brats24)
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
from prism.features.seg_measurements import CAVITY_INPUTS, COHORTS, table_ids, table_path

# variant: (segmenter whose table it reads, drop the cavity inputs); released reads the released masks
CFG = {"swin": {"out": RESULTS / "analyses" / "segmenter_stage", "seed": 20261119, "tag": "s1",
                "variants": {"released": None, "segmenter": ("swin", True)}},
       "brats24": {"out": RESULTS / "analyses" / "segmenter_brats24", "seed": 20261120, "tag": "s4",
                   "variants": {"released": None, "segmenter": ("brats24", False), "swin": ("swin", True),
                                "segmenter22": ("brats24", True)}}}
SEGMENTER = "swin"
OUT = CFG["swin"]["out"]
SEED = CFG["swin"]["seed"]
TAG = "s1"
VARIANTS = CFG["swin"]["variants"]
SCORES = ("images", "combined", "baseline")
MU_SCORES = SCORES + ("combined_full",)
T_EXTRA = ["has_prev", "log_days_from_prev"]
BASE_LOCKED = ["early_post_rt", "log_et_cc", "logratio_prev_et", "has_prev"]


def configure(segmenter: str, out=None) -> None:
    global SEGMENTER, OUT, SEED, TAG, VARIANTS
    c = CFG[segmenter]
    SEGMENTER, SEED, TAG, VARIANTS = segmenter, c["seed"], c["tag"], c["variants"]
    OUT = c["out"] if out is None else type(c["out"])(out)


def mu_table(mset: str):
    """MU measurement table the model process for this prediction set reads (None: the released table)."""
    v = VARIANTS[mset]
    if v is None:
        return None
    return table_path("mu", "swin") if v[0] == "swin" else OUT / "mu_table_brats24_padded.csv"


def write_padded_mu() -> None:
    """BraTS24 MU table (the scope) on the released scan set, for the model process. Scans outside the scope carry
    their released-mask measurements, so the MU frame (which scans have measurements) is the released one. They come
    after each patient's last labelled scan or belong to patients without one: they are never fitted, evaluated or
    used as an earlier scan (check_mu_scope), and their rows of the predictions are not read."""
    from prism.features.seg_measurements import RELEASED_MU
    ref = pd.read_csv(RELEASED_MU)
    b = pd.read_csv(table_path("mu", "brats24"))
    assert list(b.columns) == list(ref.columns)
    assert b.scan_id.isin(ref.scan_id).all()
    p = pd.concat([b, ref[~ref.scan_id.isin(b.scan_id)]]).set_index("scan_id").reindex(ref.scan_id).reset_index()
    assert np.allclose(p.mri_day.to_numpy(float), ref.mri_day.to_numpy(float)) and p.et_cc.notna().all()
    p.to_csv(OUT / "mu_table_brats24_padded.csv", index=False)


REF = {  # released-mask numbers of the paper (METHODS_RESULTS.md E4, E6d; system.EXPECTED; UCSF_RESULTS.md)
    "mu": {"images": 0.709, "combined": 0.804, "baseline": 0.797, "combined_full": 0.821},
    "lumiere": {"images": 0.6539, "combined": 0.7729, "baseline": 0.7342},
    "ucsf": {"images": 0.726, "combined": 0.856}}


# ---------------------------------------------------------------- designs
@lru_cache(maxsize=1)
def mu_designs(mset: str):
    """MU frame, CV designs and locked designs on the measurement table this process reads (config.MEASUREMENTS).
    mset: a prediction set of VARIANTS (S1: released, segmenter)."""
    from prism.analyses import clinician_baseline as CB
    from prism.analyses import detection as D
    from prism.analyses import ucsf_external as UX
    d, A4 = UX.mu_detection("grade4")
    X = D.context("grade4", "primary")[1]
    T, b1 = X["T"], X["B1"]
    if VARIANTS[mset] is None:
        img, comb = A4["A-Ipure"], T
    else:
        img = A4["A-Ipure"].drop(columns=list(CAVITY_INPUTS)) if VARIANTS[mset][1] else A4["A-Ipure"]
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


def lumiere_seg(L: pd.DataFrame, LX: pd.DataFrame, cols: list, seg: str = "swin") -> dict:
    """LUMIERE designs on the segmenter inputs, rows aligned with detection.lumiere_detection."""
    from prism.analyses import detection as D
    meas = pd.read_csv(table_path("lumiere", seg))
    no_images = 0
    if seg == "brats24":  # every labelled study and its previous study is in the scope, if its images exist
        from prism.features.reseg import ext_ids
        have, imaged = set(meas.scan_id), set(ext_ids("lumiere"))
        need = set(L.scan_id) | set(L.prev_scan_id[L.prev_scan_id.ne("")])
        miss = need - have
        assert miss <= need - imaged, f"LUMIERE: {len(miss - (need - imaged))} labelled or previous studies " \
                                      f"with images but without a BraTS24 row"
        no_images = len(set(L.scan_id) - imaged)
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
            "n_without_map": int(mi.log_et_cc.isna().sum()), "n_with_prev": int((hp == 1).sum()),
            "n_without_images": no_images}


def ucsf_seg(u: pd.DataFrame, A: dict, keep, cols: list, seg: str = "swin") -> dict:
    from prism.analyses import detection as D
    meas = pd.read_csv(table_path("ucsf", seg))
    if seg == "brats24":  # the evaluated scans (labelled scan 2) and their scan 1 are in the scope
        sub = u[keep]
        sub = sub[sub.pos_s2_pm30.eq(1) | sub.primary_neg.astype(bool)]
        need = set(sub.scan_id) | set(sub.subject_id.astype(str) + "_time1")
        assert need <= set(meas.scan_id), f"UCSF: {len(need - set(meas.scan_id))} evaluation scans without a row"
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
    seg, out, mset, r, k = job
    configure(seg, out)
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, _, _, cv = mu_designs(mset)
    f = D.fold_ids(d, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    return r, te, {p: c3.fit_predict(c3.BASELINES[0], d, X, {}, None, tr, te, seed=r) for p, X in cv.items()}


def check_mu_scope(d: pd.DataFrame) -> dict:
    """Every labelled MU row (so every evaluated one), its previous scan and every earlier scan of the patient (the change
    and nadir inputs) has a row in the BraTS24 table."""
    from prism.features.seg_measurements import RELEASED_MU
    have = set(pd.read_csv(table_path("mu", "brats24")).scan_id)
    ref = pd.read_csv(RELEASED_MU)
    lab = d.label_120.notna()
    use = lab  # the evaluated rows (labelled, intended use) are among them
    prev = d.prev_scan_id[use].fillna("")
    need = set(d.scan_id[use]) | set(prev[prev.ne("")])
    for pid, day in zip(d.patient_id[use], d.mri_day[use]):
        need |= set(ref.scan_id[(ref.patient_id == pid) & (ref.mri_day < day)])
    assert need <= have, f"MU: {len(need - have)} labelled, evaluated or earlier scans without a BraTS24 row"
    return {"mu_labelled_rows": int(lab.sum()), "mu_rows_needed": len(need), "mu_brats24_rows": len(have)}


def predict(mset: str, workers: int, cohorts=COHORTS) -> None:
    from prism.analyses import detection as D
    from prism.analyses import system as S
    from prism.analyses import ucsf_external as UX
    from prism.config import MEASUREMENTS
    want = mu_table(mset)
    assert (want is None and "PRISM_MEASUREMENTS" not in os.environ) or MEASUREMENTS == want, MEASUREMENTS
    warnings.filterwarnings("ignore")
    seg = None if VARIANTS[mset] is None else VARIANTS[mset][0]
    d, A4, T, cv = mu_designs(mset)
    n = len(d)
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(cv_job, [(SEGMENTER, str(OUT), mset, r, k) for r in range(5) for k in range(5)]))
    P = {p: np.full((5, n), np.nan) for p in MU_SCORES}
    for r, te, pr in res:
        for p, v in pr.items():
            P[p][r, te] = v
    assert all(np.isfinite(v).all() for v in P.values())
    ev = (d.label_120.notna() & d.intended_use).to_numpy()
    rows = np.arange(n)
    info = {"mu_columns": {p: list(X.columns) for p, X in cv.items()}}
    if seg == "brats24":
        info.update(check_mu_scope(d))

    # locked models (one fit on all MU training rows) and the external designs
    L, LX, _ = D.lumiere_detection()
    u = UX.ucsf_frame()
    A = UX.ucsf_designs(u, A4)
    keep = (u.timepoint.eq(2) & u.grade4).to_numpy()
    uk = u[keep].reset_index(drop=True)
    if seg is None:
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
        nan = np.full(len(L), np.nan)
        lum, uc = {p: nan for p in Xmu}, {p: np.full(len(uk), np.nan) for p in Xmu}
        ext = [c for c in ("lumiere", "ucsf") if seg == "swin" or c in cohorts]
        if "lumiere" in ext:
            ls = lumiere_seg(L, LX, img_cols, seg)
            assert all(list(ls[p].columns) == list(Xmu[p].columns) for p in Xmu)
            lum = {p: fits[p](ls[p]) for p in Xmu}
            info.update(lumiere_without_map=ls["n_without_map"], lumiere_with_prev=ls["n_with_prev"])
            if seg == "brats24":  # only the studies without images (7, as S1) lack a map; imputed as in S1
                assert ls["n_without_map"] == ls["n_without_images"], ls["n_without_map"]
                info["lumiere_without_images"] = ls["n_without_images"]
        if "ucsf" in ext:
            us = ucsf_seg(u, A, keep, img_cols, seg)
            assert all(list(us[p].columns) == list(Xmu[p].columns) for p in Xmu)
            uc = {p: fits[p](us[p]) for p in Xmu}
            info.update(ucsf_without_map=us["n_without_map"])
        if seg == "brats24" and "ucsf" in ext:  # rows outside the evaluation set have no map; not read
            ev_u = (uk.pos_s2_pm30.eq(1) | uk.primary_neg.astype(bool)).to_numpy()
            info["ucsf_evaluated_without_map"] = int(us["images"].log_et_cc.isna().to_numpy()[ev_u].sum())
            assert info["ucsf_evaluated_without_map"] == 0, info
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


def run_set(mset: str, workers: int, cohorts=COHORTS) -> None:
    env = {k: v for k, v in os.environ.items() if k != "PRISM_MEASUREMENTS"}
    if mu_table(mset) is not None:
        env["PRISM_MEASUREMENTS"] = str(mu_table(mset))
    subprocess.run([sys.executable, "-m", "prism.analyses.segmenter_stage", "--predict", mset,
                    "--workers", str(workers), "--segmenter", SEGMENTER, "--out", str(OUT),
                    "--cohorts", *cohorts], env=env, check=True)


# ---------------------------------------------------------------- P1
def load_cohorts(cohorts=COHORTS) -> dict:
    """{cohort: (y, scores {score|set: (R, n)}, context, patient ids)} on the evaluation scans, sets aligned."""
    sets = list(VARIANTS)
    z = {s: np.load(OUT / f"preds_{s}.npz") for s in sets}
    a = z["released"]
    for s in sets[1:]:
        for k in ("mu_scan_id", "mu_pid", "mu_y", "mu_phase", "mu_ev", "lum_scan_id", "lum_y", "ucsf_scan_id",
                  "ucsf_y"):
            assert np.array_equal(a[k], z[s][k], equal_nan=k.endswith("_y")), f"{k} differs between mask sets"
    out = {}
    ev = a["mu_ev"]
    out["mu"] = (a["mu_y"][ev], {f"{p}|{s}": z[s][f"mu_{p}"][:, ev] for s in sets for p in MU_SCORES},
                 a["mu_phase"][ev], a["mu_pid"][ev])
    out["lumiere"] = (a["lum_y"], {f"{p}|{s}": z[s][f"lum_{p}"][None, :] for s in sets for p in SCORES},
                      a["lum_ctx"], a["lum_pid"])
    e = ~np.isnan(a["ucsf_y"])
    out["ucsf"] = (a["ucsf_y"][e], {f"{p}|{s}": z[s][f"ucsf_{p}"][None, e] for s in sets for p in SCORES},
                   a["ucsf_ctx"][e], a["ucsf_pid"][e])
    out = {c: v for c, v in out.items() if c in cohorts}
    for c, (_, scores, _, _) in out.items():
        assert all(np.isfinite(v).all() for v in scores.values()), f"{c}: missing predictions"
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


# comparisons (new, reference) per table; P1 is S1's table exactly
COMPARE = {"p1": [("segmenter", "released")], "p4": [("segmenter", "swin")],
           "exploratory": [("segmenter22", "released"), ("segmenter22", "segmenter"), ("segmenter22", "swin")]}


def p1(cohorts, n_boot) -> dict:
    """{table: frame}: AUCs, paired AUC differences and combined - baseline gains for each comparison of COMPARE
    whose sets were predicted. One bootstrap per cohort covers every set."""
    from prism.analyses.methods import boot, ci, m1_stats
    rows = {t: [] for t in COMPARE}
    for c, (y, scores, ctx, pid) in cohorts.items():
        est = m1_stats(y, scores, ctx)
        B = boot(y, scores, ctx, pid, n_boot, seed=SEED)
        n = {"n_scans": len(y), "n_pos": int((y == 1).sum()), "n_patients": len(np.unique(pid))}
        pw = [p for p in MU_SCORES if f"{p}|released" in scores]
        for tab, pairs in COMPARE.items():
            for new, ref in pairs:
                if new not in VARIANTS or ref not in VARIANTS:
                    continue

                def add(kind, score, masks, f):
                    lo, hi = ci([f(b) for b in B])
                    rows[tab].append({"cohort": c, "kind": kind, "score": score, "masks": masks, "est": f(est),
                                      "lo": lo, "hi": hi, **n})

                for p in pw:
                    for s in (ref, new):
                        add("auc", p, s, lambda e, k=f"{p}|{s}": e[k][0])
                    add("paired_diff", p, f"{new}-{ref}", lambda e, p=p: e[f"{p}|{new}"][0] - e[f"{p}|{ref}"][0])
                for g in [p for p in pw if p.startswith("combined")]:
                    if f"baseline|released" not in scores:
                        continue
                    for s in (ref, new):
                        add("gain", f"{g}-baseline", s, lambda e, g=g, s=s: e[f"{g}|{s}"][0] - e[f"baseline|{s}"][0])
                    add("gain_change", f"{g}-baseline", f"{new}-{ref}",
                        lambda e, g=g: (e[f"{g}|{new}"][0] - e[f"baseline|{new}"][0])
                        - (e[f"{g}|{ref}"][0] - e[f"baseline|{ref}"][0]))
    return {t: pd.DataFrame(r) for t, r in rows.items() if r}


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
def _dice_summary(c: str, comp: str, seg: str, x: pd.Series, n_scans: int, n_empty) -> dict:
    return {"cohort": c, "compartment": comp, **({} if seg is None else {"segmenter": seg}), "n_scans": n_scans,
            "n_defined": int(x.notna().sum()), "n_released_empty": n_empty, "dice_median": x.median(),
            "dice_q25": x.quantile(.25), "dice_q75": x.quantile(.75),
            "frac_dice_lt_0.5": float((x.dropna() < 0.5).mean())}


def p2() -> pd.DataFrame:
    from prism.features.reseg import volumes_path
    rows = []
    for c in ("mu", "lumiere", "ucsf"):
        v = pd.read_csv(volumes_path("brats21", c))
        for comp in ("et", "wt"):
            rows.append(_dice_summary(c, comp, None, v[f"dice_{comp}"], len(v),
                                      int((v[f"mu_{comp}_voxels"] == 0).sum())))
    return pd.DataFrame(rows)


def _b24_dice_one(args) -> dict:
    """Dice of one BraTS24 map against the released mask (as prism.features.reseg_brats24.collect)."""
    import nibabel as nib
    from prism.features import reseg as R
    from prism.features.reseg_brats24 import LABEL_RC, out_path, released
    c, sid = args
    lab = np.rint(np.asarray(nib.load(str(out_path(c, sid))).dataobj)).astype(np.uint8)
    mu = released(c, sid)
    if mu is None:
        return {"scan_id": sid}
    new, old = R.compartments(lab), R.compartments(mu)
    row = {"scan_id": sid, **{f"dice_{k}": R.dice(new[k], old[k]) for k in new}}
    row["dice_rc"] = R.dice(lab == LABEL_RC, mu == LABEL_RC) if (mu == LABEL_RC).any() else np.nan
    return row


def b24_dice(c: str, workers: int) -> pd.DataFrame:
    """Per-scan BraTS24 Dice on the scope: volumes_brats24_<cohort>.csv where it has the scan, computed otherwise."""
    from prism.features.seg_measurements import B24_TABLES, scope_ids
    ids = scope_ids(c)
    f = B24_TABLES / f"volumes_brats24_{c}.csv"
    cols = ["scan_id", "dice_et", "dice_wt", "dice_rc"]
    v = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=cols)
    if len(v):  # rows the run wrote without a map ("error") are computed again
        ok = v.error.isna() if "error" in v else pd.Series(True, index=v.index)
        v = v[v.scan_id.isin(ids) & ok].drop_duplicates("scan_id", keep="last")
    todo = [i for i in ids if i not in set(v.scan_id)]
    if todo:
        with ProcessPoolExecutor(workers) as ex:
            v = pd.concat([v, pd.DataFrame(list(ex.map(_b24_dice_one, [(c, i) for i in todo], chunksize=2)))])
    v = v.set_index("scan_id").reindex(ids)
    if c == "lumiere":  # no separate cavity in the released LUMIERE masks
        v["dice_rc"] = np.nan
    return v.reset_index()[cols].assign(n_computed=len(todo))


def _pid(c: str, sid: pd.Series) -> pd.Series:
    return sid.str.split("_Timepoint_").str[0] if c == "mu" else sid.str.split("_", n=1).str[0]


def p2_b24(cohorts, workers: int, n_boot: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """P2 (BraTS24 and Swin UNETR Dice on the BraTS24 scope) and P4's paired Dice differences (BraTS24 - Swin)."""
    from prism.analyses.reseg_eval import _cluster_boot
    from prism.features.reseg import volumes_path
    rows, diffs = [], []
    for c in cohorts:
        b = b24_dice(c, workers)
        sw = pd.read_csv(volumes_path("brats21", c)).set_index("scan_id").reindex(b.scan_id)
        for comp in ("et", "wt", "rc"):
            if comp == "rc" and c == "lumiere":
                continue
            empty = (int(b.dice_rc.isna().sum()) if comp == "rc" else int((sw[f"mu_{comp}_voxels"] == 0).sum()))
            r = _dice_summary(c, comp, "brats24", b[f"dice_{comp}"], len(b), empty)
            r["n_computed_here"] = int(b.n_computed.iat[0])
            rows.append(r)
            if comp == "rc":
                continue
            rows.append(_dice_summary(c, comp, "swin", sw[f"dice_{comp}"].reset_index(drop=True), len(b), empty))
            q = pd.DataFrame({"patient_id": _pid(c, b.scan_id).to_numpy(),
                              "d": b[f"dice_{comp}"].to_numpy() - sw[f"dice_{comp}"].to_numpy()}).dropna()
            lo, hi = _cluster_boot(q, lambda d: d.d.median(), n_boot, seed=SEED)
            diffs.append({"cohort": c, "compartment": comp, "n_scans": len(q), "n_patients": q.patient_id.nunique(),
                          "median_diff_brats24_minus_swin": q.d.median(), "lo": lo, "hi": hi,
                          "mean_diff": q.d.mean(), "frac_brats24_higher": float((q.d > 0).mean())})
    return pd.DataFrame(rows), pd.DataFrame(diffs)


# ---------------------------------------------------------------- P3
def _pairs(tab: pd.DataFrame, max_gap: float = 30, sets=("rel", "seg")) -> pd.DataFrame:
    """Consecutive scans per patient (tab: scan_id, patient_id, day, et_<set>), gap <= max_gap days."""
    t = tab.sort_values(["patient_id", "day"])
    g = t.groupby("patient_id")
    p = pd.DataFrame({"patient_id": t.patient_id, "gap": t.day - g.day.shift(),
                      **{f"abslog_{s}": np.abs(np.log((t[f"et_{s}"] + 0.1) / (g[f"et_{s}"].shift() + 0.1)))
                         for s in sets}}).dropna()
    return p[p.gap <= max_gap].reset_index(drop=True)


def p3(n_boot, cohorts=("mu", "lumiere")) -> pd.DataFrame:
    """S1: released vs the segmenter. S4: released, BraTS24 and Swin UNETR on the scans all three have (the BraTS24
    scope), so the pairs are the same for the three."""
    from prism.analyses import detection as D
    from prism.analyses.reseg_eval import _cluster_boot
    from prism.config import MEASUREMENTS
    b24 = SEGMENTER == "brats24"
    sets = (("rel", "released"), ("seg", "segmenter")) + ((("swin", "swin"),) if b24 else ())
    mu_r, mu_s = pd.read_csv(MEASUREMENTS), pd.read_csv(table_path("mu", SEGMENTER))
    mu = mu_r[["scan_id", "patient_id", "mri_day", "et_cc"]].merge(mu_s[["scan_id", "et_cc"]], on="scan_id",
                                                                  suffixes=("_rel", "_seg"))
    mu = mu.rename(columns={"mri_day": "day", "et_cc_rel": "et_rel", "et_cc_seg": "et_seg"})
    if b24:
        sw = pd.read_csv(table_path("mu", "swin")).set_index("scan_id").et_cc
        mu["et_swin"] = sw.reindex(mu.scan_id).to_numpy()
        mu = mu.dropna()
    tabs = [("mu", mu)]
    if "lumiere" in cohorts:
        ls = pd.read_csv(table_path("lumiere", SEGMENTER))
        ls = ls[ls.scan_id.isin(lumiere_pool())]
        vol = D.lumiere_volumes().set_index("scan_id").raw_Enhancing_Core / 1000.0
        lu = pd.DataFrame({"scan_id": ls.scan_id, "patient_id": ls.patient_id, "day": ls.mri_day,
                           "et_rel": vol.reindex(ls.scan_id).to_numpy(), "et_seg": ls.et_cc.to_numpy()})
        if b24:
            sw = pd.read_csv(table_path("lumiere", "swin")).set_index("scan_id").et_cc
            lu["et_swin"] = sw.reindex(ls.scan_id).to_numpy()
        tabs.append(("lumiere", lu.dropna()))
    rows = []
    for c, tab in tabs:
        q = _pairs(tab, sets=[k for k, _ in sets])
        r = {"cohort": c, "n_pairs": len(q), "n_patients": q.patient_id.nunique(), "n_scans_in_pool": len(tab)}
        if len(q) < 3:
            rows.append(r)
            continue
        for s, name in sets:
            lo, hi = _cluster_boot(q, lambda d, s=s: d[f"abslog_{s}"].median(), n_boot, seed=SEED)
            r.update({f"fold_{name}": float(np.exp(q[f"abslog_{s}"].median())), f"fold_{name}_lo": float(np.exp(lo)),
                      f"fold_{name}_hi": float(np.exp(hi))})
        r["d_median_abslog"] = q.abslog_seg.median() - q.abslog_rel.median()
        r["d_lo"], r["d_hi"] = _cluster_boot(q, lambda d: d.abslog_seg.median() - d.abslog_rel.median(), n_boot,
                                             seed=SEED)
        if b24:
            r["d_swin_median_abslog"] = q.abslog_seg.median() - q.abslog_swin.median()
            r["d_swin_lo"], r["d_swin_hi"] = _cluster_boot(
                q, lambda d: d.abslog_seg.median() - d.abslog_swin.median(), n_boot, seed=SEED)
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


def available() -> tuple[list, dict]:
    """Cohorts whose measurement table covers the run's scope; {cohort: reason} for the others (brats24)."""
    from prism.features.seg_measurements import scope_status
    if SEGMENTER == "swin":
        return list(COHORTS), {}
    ok, skipped = [], {}
    for c in COHORTS:
        f = table_path(c, "brats24")
        done, n = scope_status(c)
        if f.exists() and set(table_ids(c, "brats24")) <= set(pd.read_csv(f, usecols=["scan_id"]).scan_id):
            ok.append(c)
        else:
            skipped[c] = f"{done} of {n} maps" + ("" if done < n else ", no measurement table")
    return ok, skipped


def _fmt(est, lo, hi):
    return f"{est:+.3f} [{lo:+.3f}, {hi:+.3f}]"


def summary(t: dict, v: dict, d2, d3, d2diff, skipped: dict) -> None:
    """Compact print: P1 with the verdict, P2, P3, P4 and the skipped cohorts."""
    pd.set_option("display.width", 250)
    name = ({"segmenter": "brats24", "segmenter22": "brats24_22in"} if SEGMENTER == "brats24" else {})
    nm = lambda m: "-".join(name.get(x, x) for x in m.split("-"))
    head = {"p1": "P1 (planned, primary): segmenter - released masks; AUC, and combined - baseline gain",
            "p4": "P4 (planned, secondary, no pass rule): BraTS24 (27 inputs) - Swin UNETR (22 inputs)",
            "exploratory": "EXPLORATORY: BraTS24 on the 22 cavity-free inputs (brats24_22in)"}
    for key, tab in t.items():
        print(f"== {head[key]}")
        rows = []
        for (c, score), g in tab.groupby(["cohort", "score"], sort=False):
            for r in g[g.kind.isin(["paired_diff", "gain_change"])].itertuples():
                newm, refm = r.masks.split("-")
                val = lambda m: g[g.kind.isin(["auc", "gain"]) & (g.masks == m)].est.iat[0]
                rows.append({"cohort": c, "score": score, "new - reference": nm(r.masks),
                             "reference": f"{val(refm):.3f}", "new": f"{val(newm):.3f}",
                             "difference [95% CI]": _fmt(r.est, r.lo, r.hi),
                             "scans (pos)": f"{r.n_scans} ({r.n_pos})"})
        print(pd.DataFrame(rows).to_string(index=False), "\n")
        if key == "p1":
            print(f"P1 verdict: {'REPRODUCES' if v['reproduces'] else 'DOES NOT REPRODUCE'} the released-mask "
                  f"results (rule: every paired CI of images, combined, baseline includes 0 or lies above it; the "
                  f"combined - baseline gain at MU and LUMIERE is read the same under both mask sets)")
            for f in v["paired_ci_below_0"]:
                print(f"  CI below 0: {f['cohort']} {f['score']} {_fmt(f['est'], f['lo'], f['hi'])}")
            for c, g in v["gain_reading"].items():
                print(f"  gain {c}: CI excludes 0 {g['excludes_0']} -> read the same: {g['same']}")
            print()
    print("== P2 Dice against the released masks" + (" (BraTS24 scope; Swin UNETR on the same scans)"
                                                     if d2diff is not None else ""))
    print(d2.round(3).to_string(index=False), "\n")
    print("== P3 repeatability: median fold change of the enhancing volume, consecutive scans <= 30 days apart"
          + (" (d: BraTS24 - released, d_swin: BraTS24 - Swin, median |log ratio|)" if d2diff is not None else ""))
    print(d3.round(3).to_string(index=False), "\n")
    if d2diff is not None:
        print("== P4 paired Dice differences (BraTS24 - Swin UNETR, per scan; no pass rule)")
        print(d2diff.round(3).to_string(index=False), "\n")
    print("skipped: " + ("; ".join(f"{c}, {r}" for c, r in skipped.items()) if skipped else "none"))
    if skipped:
        print(f"NOTE: the P1 verdict covers only the cohorts run ({', '.join(c for c in COHORTS if c not in skipped)})"
              f"; it is provisional until every cohort's scope is complete.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="prism.analyses.segmenter_stage", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--segmenter", default="swin", choices=tuple(CFG))
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--out", help="output folder (default: the segmenter's)")
    ap.add_argument("--predict", choices=tuple(CFG["brats24"]["variants"]), help=argparse.SUPPRESS)
    ap.add_argument("--cohorts", nargs="+", default=list(COHORTS), help=argparse.SUPPRESS)
    ap.add_argument("--skip-predict", action="store_true", help="reuse preds_<set>.npz")
    a = ap.parse_args(argv)
    configure(a.segmenter, a.out)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.predict:
        return predict(a.predict, a.workers, a.cohorts)
    t0 = time.time()
    assert "PRISM_MEASUREMENTS" not in os.environ, "run the comparison with the default table"
    cohorts_ok, skipped = available()
    for c, r in skipped.items():
        print(f"skipped: {c}, {r}")
    if "mu" not in cohorts_ok:
        sys.exit("MU is required (the models are fitted on it): its BraTS24 scope is not complete")
    if SEGMENTER == "brats24":
        write_padded_mu()
    if not a.skip_predict:
        for s in VARIANTS:
            run_set(s, a.workers, cohorts_ok)
    cohorts = load_cohorts(cohorts_ok)
    ref = check_reference(cohorts)
    pd.DataFrame(ref).to_csv(OUT / f"{TAG}_reference_check.csv", index=False)
    tabs = p1(cohorts, a.n_boot)
    t = tabs["p1"]
    for k, x in tabs.items():
        x.to_csv(OUT / f"{TAG}_{k}.csv", index=False)
    v = verdict(t)
    d2diff = None
    if SEGMENTER == "swin":
        d2 = p2()
        d2.to_csv(OUT / "s1_p2_dice.csv", index=False)
    else:
        d2, d2diff = p2_b24(cohorts_ok, a.workers, a.n_boot)
        d2.to_csv(OUT / f"{TAG}_p2_dice.csv", index=False)
        d2diff.to_csv(OUT / f"{TAG}_p4_dice.csv", index=False)
    d3 = p3(a.n_boot, [c for c in ("mu", "lumiere") if c in cohorts_ok])
    d3.to_csv(OUT / f"{TAG}_p3_repeatability.csv", index=False)
    cb = calibration(cohorts)
    cb.to_csv(OUT / f"{TAG}_calibration.csv", index=False)
    info = {"n_boot": a.n_boot, "seed": SEED, "seconds": round(time.time() - t0), "verdict": v}
    if SEGMENTER != "swin":
        info = {"segmenter": SEGMENTER, "cohorts": cohorts_ok, "skipped": skipped, **info}
    (OUT / "run_info.json").write_text(json.dumps(info, indent=1, default=str))
    pd.set_option("display.width", 220)
    for x in (pd.DataFrame(ref), *tabs.values(), d2, d3, cb) + (() if d2diff is None else (d2diff,)):
        print(x.round(3).to_string(index=False), "\n")
    print(json.dumps(v, indent=1, default=str))
    print("\n================ SUMMARY ================")
    summary(tabs, v, d2, d3, d2diff, skipped)
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
