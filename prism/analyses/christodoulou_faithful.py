"""The published MU radiomics pipeline (Christodoulou 2026), run with the authors' code, on PRISM's detection task.

ANALYSIS PLAN: docs/results/CHRISTODOULOU_FAITHFUL_PLAN.md (committed b1ce85b before any code for this run);
snapshotted to outputs/results/analyses/christodoulou_faithful/PLAN_snapshot.md by the first fit run.

Authors' code: prism/analyses/_christodoulou_vendor.py (verbatim, BSD 3-Clause, commit 643c888).
  extract  their extraction (N4 in the mask, 1 mm BSpline, z-score in the mask, tumorMask > 0, four sequences,
           Original + LoG + Wavelet, _christodoulou_radiomics_params.yaml) on every MU scan with four sequences and
           a mask -> $PRISM_OUTPUTS/features/radiomics_christodoulou.csv (scan_id = PatientID_XXXX_Timepoint_X, the
           detection frame's key)
  fit      per outer fold (5 repeats x 5 folds, detection.fold_ids, grade 4, training rows = positives + primary
           negatives of the training folds): their ranking (compute_importance_traincv) -> top 256 -> their
           train_lgbm (Optuna 400 trials, 5-fold StratifiedGroupKFold by patient, Platt on the OOF of the best
           trial, refit on all training rows) -> held-out fold
  evaluate as christodoulou_replication: mean over repeats of the pooled held-out AUC, intended use (146) and all
           181 grade-4 detection scans, 1,000-draw patient bootstrap, paired differences against B1 and I_pure
           (ridge, refitted on the same folds)

    PYTHONPATH=. .venv/bin/python -m prism.analyses.christodoulou_faithful extract [--workers 20] [--limit 3]
    PYTHONPATH=. .venv/bin/python -m prism.analyses.christodoulou_faithful fit [--workers 20] [--trials 400]
    PYTHONPATH=. .venv/bin/python -m prism.analyses.christodoulou_faithful evaluate [--n-boot 1000]
    -> $PRISM_OUTPUTS/results/analyses/christodoulou_faithful/

--masks brats21 (plan: docs/results/CHRISTODOULOU_BRATS_MASKS_PLAN.md, cab32b3): the same steps with every MU mask
replaced by the BraTS21 SwinUNETR label map of E5 (prism.features.reseg, outputs/features/seg_swin/mu/); region
`label map > 0`. Default --masks released is the run above, unchanged.
    ... christodoulou_faithful --masks brats21 maskcheck          (cavity / empty-map check, before any AUC)
    ... christodoulou_faithful --masks brats21 extract|fit
    ... christodoulou_faithful --masks brats21 evaluate --n-boot 2000   (seed 20261115; also refits B1 / I_scan /
        I_pure, the imaging arms on the BraTS21 measurement table via PRISM_MEASUREMENTS in a subprocess)
    -> $PRISM_OUTPUTS/features/radiomics_christodoulou_brats21.csv,
       $PRISM_OUTPUTS/results/analyses/christodoulou_faithful_brats21/
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

from prism.config import MU_IMAGES, OUTPUTS, REPO, RESULTS

MASKS = ("released", "brats21")
OUT = RESULTS / "analyses" / "christodoulou_faithful"
FEATURES = OUTPUTS / "features" / "radiomics_christodoulou.csv"
PARTS = OUTPUTS / "features" / "radiomics_christodoulou_parts"
MASK_SOURCE = "released"
OUT_RELEASED = OUT
FEATURES_RELEASED = FEATURES


def configure(masks: str) -> None:
    """Point OUT / FEATURES / PARTS at the mask source (default "released" = the faithful run, unchanged)."""
    global OUT, FEATURES, PARTS, MASK_SOURCE
    assert masks in MASKS, masks
    sfx = "" if masks == "released" else f"_{masks}"
    MASK_SOURCE = masks
    OUT = RESULTS / "analyses" / f"christodoulou_faithful{sfx}"
    FEATURES = OUTPUTS / "features" / f"radiomics_christodoulou{sfx}.csv"
    PARTS = OUTPUTS / "features" / f"radiomics_christodoulou{sfx}_parts"


def mask_file(pid: str, tp: str, base) -> "os.PathLike":
    """The mask the extraction reads: the released tumorMask or the BraTS21 label map (same grid, reseg.py)."""
    if MASK_SOURCE == "released":
        from prism.analyses import _christodoulou_vendor as V
        return V.expected_files(pid, tp, base)[V.MASK_KEY]
    from prism.features.reseg import seg_path
    return seg_path(f"{pid}_{tp}", "brats21")


def _use_mask_source() -> None:
    """Swap the mask path in the vendored expected_files (their code reads files[MASK_KEY]); images unchanged."""
    from prism.analyses import _christodoulou_vendor as V
    if MASK_SOURCE == "released" or getattr(V.expected_files, "_prism_masks", None) == MASK_SOURCE:
        return
    orig = V.expected_files

    def expected_files(patient_id, timepoint, base_dir):
        f = orig(patient_id, timepoint, base_dir)
        f[V.MASK_KEY] = mask_file(patient_id, timepoint, base_dir)
        return f
    expected_files._prism_masks = MASK_SOURCE
    V.expected_files = expected_files
K_FEATURES = 256
CONTRASTS = [("CHF", "B1"), ("CHF", "I_pure"), ("CHF", "I_scan")]
META = ("scan_id", "subject_id", "timepoint", "roi")


def _single_thread():
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[v] = "1"
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    warnings.filterwarnings("ignore")


# ---------------------------------------------------------------- step 1: extraction
def scans_with_all_inputs():
    from prism.analyses import _christodoulou_vendor as V
    _use_mask_source()
    pairs = V.discover_timepoints(MU_IMAGES)
    ok = [(p, t) for p, t in pairs if all(V.is_nonempty_file(f) for f in V.expected_files(p, t, MU_IMAGES).values())]
    return pairs, ok


def _extract_one(pt, masks="released"):
    _single_thread()
    configure(masks)
    _use_mask_source()
    import SimpleITK as sitk
    sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(1)
    from prism.analyses import _christodoulou_vendor as V
    pid, tp = pt
    part = PARTS / f"{pid}_{tp}.pkl"
    if part.exists():
        return pt, "cached", 0.0
    t0 = time.time()
    try:
        row = V.extract_timepoint(pid, tp, MU_IMAGES)
    except Exception as e:  # recorded, not swallowed: the caller counts failures
        return pt, f"error: {type(e).__name__}: {e}", time.time() - t0
    if row is None:
        return pt, "none", time.time() - t0
    part.write_bytes(pickle.dumps({"scan_id": f"{pid}_{tp}", **row}))
    return pt, "ok", time.time() - t0


def extract(workers: int, limit: int | None):
    PARTS.mkdir(parents=True, exist_ok=True)
    pairs, ok = scans_with_all_inputs()
    todo = ok[:limit] if limit else ok
    print(f"timepoints {len(pairs)}, with four sequences + mask {len(ok)}, to run {len(todo)}", flush=True)
    t0, status, secs = time.time(), {}, []
    with ProcessPoolExecutor(workers) as ex:
        futs = [ex.submit(_extract_one, pt, MASK_SOURCE) for pt in todo]
        for i, f in enumerate(as_completed(futs), 1):
            pt, st, s = f.result()
            status[pt] = st
            if st == "ok":
                secs.append(s)
            if i % 20 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)} done, {time.time() - t0:.0f}s wall, median {np.median(secs) if secs else 0:.0f}s"
                      f"/scan", flush=True)
    fails = {f"{p}_{t}": s for (p, t), s in status.items() if s not in ("ok", "cached")}
    info = {"timepoints": len(pairs), "with_all_inputs": len(ok), "run": len(todo), "failed": len(fails),
            "failure_reasons": sorted(set(fails.values())), "wall_seconds": round(time.time() - t0),
            "median_seconds_per_scan": float(np.median(secs)) if secs else None, "workers": workers,
            "masks": MASK_SOURCE}
    print(json.dumps(info, indent=1), flush=True)
    if limit:
        return
    if MASK_SOURCE != "released":  # failures are listed by count and reason; ids go to the (git-ignored) json only
        print(f"failed: {len(fails)}", flush=True)
    rows = [pickle.loads(p.read_bytes()) for p in sorted(PARTS.glob("*.pkl"))]
    df = pd.DataFrame(rows)
    feat = sorted(c for c in df.columns if c not in META)
    df = df[list(META) + feat]
    df.to_csv(FEATURES, index=False)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "extraction_info.json").write_text(json.dumps({**info, "n_rows": len(df), "n_features": len(feat),
                                                          "failed_scan_ids": sorted(fails)}, indent=1))
    print(f"wrote {FEATURES}: {len(df)} scans x {len(feat)} features", flush=True)


# ---------------------------------------------------------------- step 2: per-fold fits
def frame():
    """(grade-4 detection frame, training label with NaN outside training rows, Christodoulou radiomics aligned)."""
    from prism.analyses import christodoulou_replication as CR
    d, y, _, _ = CR.data("grade4")
    R = pd.read_csv(FEATURES).set_index("scan_id")
    feat = [c for c in R.columns if c not in META]
    R = R[feat].apply(pd.to_numeric, errors="coerce").reindex(d.scan_id)
    R.index = d.index
    return d, y, R


def _fold_job(args):
    _single_thread()
    from prism.analyses import _christodoulou_vendor as V
    from prism.analyses import detection as D
    V.LGBM_N_JOBS, V.OPTUNA_N_JOBS = 1, 1
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    r, k, n_trials, masks = args
    configure(masks)
    t0 = time.time()
    d, y, R = frame()
    f = D.fold_ids(d, r)
    tr = np.where((f != k) & ~np.isnan(y))[0]
    te = np.where(f == k)[0]
    # their label column: non-missing = 1 (rank_and_split__4 / lightGBM__5b: y = df[PROG_COL].notna())
    dtr = R.iloc[tr].copy()
    dtr[V.PROG_COL] = np.where(y[tr] == 1, 1.0, np.nan)
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()) as log:
        imp, feat_cols = V.compute_importance_traincv(dtr)
    top = V.top_k_features(imp, R.columns, K_FEATURES)
    t_rank = time.time() - t0
    art = V.train_lgbm(R.iloc[tr][top], y[tr].astype(int), d.patient_id.to_numpy()[tr], n_trials=n_trials)
    raw, cal = V.predict(art, R.iloc[te][top])
    info = {"repeat": r, "fold": k, "n_train": len(tr), "n_test": len(te), "n_features_in": len(feat_cols),
            "n_ranked": len(imp), "n_top": len(top), "n_nonzero_coef": int((imp.median_abs_coef > 0).sum()),
            "pi_folds": log.getvalue().split("[diag] folds with PI: ")[1].split("\n")[0],
            "inner_best_auc": art["best_value"], "inner_refit_oof_auc": art["train_oof_auc"],
            "n_after_corr": len(art["pipeline"].named_steps["corr"].keep_features_),
            **{f"param_{a}": b for a, b in art["params"].items()},
            "seconds_rank": round(t_rank), "seconds_total": round(time.time() - t0)}
    return r, k, te, raw, cal, top, info


def fit(workers: int, n_trials: int, only: str | None):
    OUT.mkdir(parents=True, exist_ok=True)
    snap = OUT / "PLAN_snapshot.md"
    if not only and not snap.exists():
        from prism.audit.provenance import git_state
        plan = (REPO / "docs" / "results" / ("CHRISTODOULOU_FAITHFUL_PLAN.md" if MASK_SOURCE == "released"
                                             else "CHRISTODOULOU_BRATS_MASKS_PLAN.md")).read_text()
        snap.write_text(f"<!-- snapshot {time.strftime('%Y-%m-%dT%H:%M:%S')}, git {git_state()['commit'][:10]} -->\n"
                        + plan)
    jobs = [(r, k, n_trials, MASK_SOURCE) for r in range(5) for k in range(5)]
    if only:  # smoke test, e.g. "0,0"
        r, k = map(int, only.split(","))
        jobs = [(r, k, n_trials, MASK_SOURCE)]
    d, y, R = frame()
    print(f"grade-4 rows {len(d)}, training-label rows {int((~np.isnan(y)).sum())}, features {R.shape[1]}, "
          f"rows without features {int(R.isna().all(1).sum())} (training-label rows: "
          f"{int((R.isna().all(1) & ~np.isnan(y)).sum())})", flush=True)
    t0 = time.time()
    raw, cal = np.full((5, len(d)), np.nan), np.full((5, len(d)), np.nan)
    infos, tops = [], {}
    with ProcessPoolExecutor(min(workers, len(jobs))) as ex:
        for fu in as_completed([ex.submit(_fold_job, j) for j in jobs]):
            r, k, te, pr, pc, top, info = fu.result()
            raw[r, te], cal[r, te] = pr, pc
            infos.append(info)
            tops[f"r{r}f{k}"] = top
            print(f"  fold r{r}f{k} done in {info['seconds_total']}s (rank {info['seconds_rank']}s), "
                  f"{len(infos)}/{len(jobs)}, wall {time.time() - t0:.0f}s", flush=True)
    infos = pd.DataFrame(infos).sort_values(["repeat", "fold"])
    if only:
        print(infos.drop(columns=[c for c in infos.columns if c.startswith("inner")]).T.to_string())
        return
    assert np.isfinite(raw).all() and np.isfinite(cal).all()
    infos.to_csv(OUT / "fold_info.csv", index=False)
    (OUT / "top_features.json").write_text(json.dumps(tops, indent=0))
    pd.DataFrame({**{f"CHF#r{r}": cal[r] for r in range(5)}, **{f"CHFraw#r{r}": raw[r] for r in range(5)},
                  "scan_id": d.scan_id}).to_csv(OUT / "oof_grade4.csv.gz", index=False)
    (OUT / "fit_info.json").write_text(json.dumps({"n_trials": n_trials, "workers": workers, "masks": MASK_SOURCE,
                                                   "wall_seconds": round(time.time() - t0)}, indent=1))
    print(f"fits done {time.time() - t0:.0f}s", flush=True)


# ---------------------------------------------------------------- step 3: evaluation
def evaluate(n_boot: int):
    from prism.analyses import christodoulou_replication as CR
    from prism.analyses import detection as D
    d, y, R = frame()
    o = pd.read_csv(OUT / "oof_grade4.csv.gz")
    assert (o.scan_id.to_numpy() == d.scan_id.to_numpy()).all()
    cal = o[[f"CHF#r{r}" for r in range(5)]].to_numpy().T
    raw = o[[f"CHFraw#r{r}" for r in range(5)]].to_numpy().T
    oofs = {"CHF": cal, **CR.ridge_oofs("grade4")}
    saved = pd.read_csv(D.OUT / "oof_grade4_primary.csv.gz")
    assert (saved.scan_id.to_numpy() == d.scan_id.to_numpy()).all()
    dev = np.nanmax(np.abs(saved[[f"B1#r{r}" for r in range(5)]].to_numpy().T - oofs["B1"]))
    assert dev < 1e-9, f"B1 differs from the detection run ({dev})"
    sets = D.eval_sets(d, "primary")
    # reference check before anything is reported: B1 0.822 and I_pure 0.709 in the intended use (DETECTION_TASK.md)
    iu = np.where(sets["intended_use"])[0]
    yy = d.label_det.to_numpy()[iu]
    chk = {a: float(np.mean(D.aucs(yy, oofs[a][:, iu]))) for a in ("B1", "I_pure")}
    print(f"reference check (intended use): B1 {chk['B1']:.3f} (0.822), I_pure {chk['I_pure']:.3f} (0.709)")
    assert round(chk["B1"], 3) == 0.822 and round(chk["I_pure"], 3) == 0.709, chk
    T = {"auc": [], "contrasts": [], "within_phase": [], "brier": []}
    for name in ("intended_use", "all_scans"):
        rows = np.where(sets[name])[0]
        r_, c_, w_ = D.evaluate_set(f"grade4|{name}", d, rows, oofs, n_boot, contrasts=CONTRASTS)
        T["auc"] += r_
        T["contrasts"] += c_
        T["within_phase"] += w_
        yy = d.label_det.to_numpy()[rows]
        T["brier"].append({"set": f"grade4|{name}", "n_pos": int(yy.sum()), "n_neg": int((yy == 0).sum()),
                           **CR.brier_boot(yy, raw[:, rows], cal[:, rows], d.patient_id.to_numpy()[rows], n_boot)})
    for k_, v in T.items():
        pd.DataFrame(v).to_csv(OUT / f"{k_}.csv", index=False)
    (OUT / "eval_info.json").write_text(json.dumps({"n_boot": n_boot, "reference_check": chk,
                                                    "b1_max_dev_vs_detection": float(dev)}, indent=1))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(T["auc"])[["set", "n_scans", "n_pos", "n_neg", "n_patients", "arm", "auc", "auc_lo", "auc_hi",
                                  "auc_repeat_sd"]].round(3).to_string(index=False))
    print(pd.DataFrame(T["contrasts"]).round(3).to_string(index=False))
    print(pd.DataFrame(T["brier"]).round(4).to_string(index=False))


# ---------------------------------------------------------------- BraTS21 masks (CHRISTODOULOU_BRATS_MASKS_PLAN.md)
BRATS_SEED = 20261115
BRATS_REF = {"CHF_released": 0.580, "B1": 0.822, "I_pure_brats21": 0.627, "I_pure_released": 0.709}
BRATS_CONTRASTS = [("CHF_brats21", "I_pure_brats21"), ("CHF_brats21", "B1"), ("CHF_brats21", "CHF_released"),
                   ("CHF_brats21", "I_scan_brats21"), ("CHF_released", "I_pure_released"),
                   ("I_pure_brats21", "I_pure_released")]


def _maskcheck_one(pt):
    import nibabel as nib
    from prism.config import LABEL_RC
    from prism.features.reseg import seg_path
    from prism.config import mu_scan_paths
    pid, tp = pt
    rel_img = nib.load(str(mu_scan_paths(pid, tp)["mask"]))  # the released mask (not the patched expected_files)
    rel = np.rint(np.asarray(rel_img.dataobj)).astype(int)
    img = nib.load(str(seg_path(f"{pid}_{tp}", "brats21")))
    new = np.asarray(img.dataobj).astype(int)
    assert str(mu_scan_paths(pid, tp)["mask"]) != str(seg_path(f"{pid}_{tp}", "brats21"))
    same_grid = rel.shape == new.shape and np.allclose(rel_img.affine, img.affine, atol=1e-4)
    a, b, rc = rel > 0, new > 0, rel == LABEL_RC
    dice = lambda u, v: float(2 * (u & v).sum() / (u.sum() + v.sum())) if (u.sum() + v.sum()) else np.nan
    return {"scan_id": f"{pid}_{tp}", "same_grid": bool(same_grid), "rel_vox": int(a.sum()), "rel_rc_vox": int(rc.sum()),
            "new_vox": int(b.sum()), "new_has_rc": bool((new == LABEL_RC).any()),
            "new_labels": "|".join(map(str, sorted(set(np.unique(new)) - {0}))),
            "dice_gt0": dice(a, b), "dice_gt0_rel_without_rc": dice(a & ~rc, b),
            "rc_inside_new": int((rc & b).sum())}


def maskcheck(workers: int):
    """Before any AUC: does the released `> 0` region contain the cavity while the BraTS21 map does not? Which
    BraTS21 maps are empty, and are they in the evaluation sets? Aggregates only (per-scan table git-ignored)."""
    from prism.analyses import christodoulou_replication as CR
    from prism.analyses import detection as D
    assert MASK_SOURCE == "brats21"
    OUT.mkdir(parents=True, exist_ok=True)
    _, ok = scans_with_all_inputs()
    with ProcessPoolExecutor(workers) as ex:
        t = pd.DataFrame(list(ex.map(_maskcheck_one, ok, chunksize=4)))
    t.to_csv(OUT / "maskcheck_per_scan.csv", index=False)
    d, y, _, _ = CR.data("grade4")
    sets = D.eval_sets(d, "primary")
    empty = set(t.scan_id[t.new_vox == 0])
    m = d.scan_id.isin(empty).to_numpy()
    hasrc = t.rel_rc_vox > 0
    info = {"scans": len(t), "same_grid_all": bool(t.same_grid.all()), "brats21_label4_anywhere": bool(t.new_has_rc.any()),
            "released_with_cavity": int(hasrc.sum()),
            "cavity_share_of_released_gt0_median_when_present": float((t.rel_rc_vox / t.rel_vox)[hasrc].median()),
            "cavity_share_of_released_gt0_iqr_when_present": [float(x) for x in (t.rel_rc_vox / t.rel_vox)[hasrc].quantile([.25, .75])],
            "cavity_voxels_inside_brats21_gt0_share_median": float((t.rc_inside_new / t.rel_rc_vox)[hasrc].median()),
            "dice_gt0_median_iqr": [float(x) for x in t.dice_gt0.quantile([.5, .25, .75])],
            "dice_gt0_released_without_cavity_median_iqr": [float(x) for x in t.dice_gt0_rel_without_rc.quantile([.5, .25, .75])],
            "volume_ratio_new_over_released_median": float((t.new_vox / t.rel_vox.replace(0, np.nan)).median()),
            "released_empty": int((t.rel_vox == 0).sum()), "brats21_empty": len(empty),
            "brats21_empty_released_only_cavity": int(((t.new_vox == 0) & (t.rel_vox == t.rel_rc_vox)).sum()),
            "brats21_empty_in_grade4_frame": int(m.sum()), "brats21_empty_in_training_rows": int((m & ~np.isnan(y)).sum()),
            **{f"brats21_empty_in_{k}": int((m & sets[k]).sum()) for k in ("intended_use", "all_scans")},
            **{f"brats21_empty_in_{k}_positives": int((m & sets[k] & (d.label_det.to_numpy() == 1)).sum())
               for k in ("intended_use", "all_scans")}}
    (OUT / "maskcheck.json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info, indent=1))


def ridge_brats21():
    """Own process with PRISM_MEASUREMENTS = BraTS21 table (E5): B1 / I_scan / I_pure OOFs on the same folds."""
    from prism.analyses import christodoulou_replication as CR
    from prism.analyses.reseg_eval import table_path
    from prism.config import MEASUREMENTS
    assert MEASUREMENTS == table_path("brats21"), MEASUREMENTS
    d, _, _, _ = CR.data("grade4")
    o = CR.ridge_oofs("grade4")
    np.savez(OUT / "ridge_brats21.npz", scan_id=d.scan_id.to_numpy(str), label=d.label_det.to_numpy(float),
             iu=d.intended_use.to_numpy(bool), fold0=np.asarray(__import__("prism.analyses.detection", fromlist=["x"])
                                                                   .fold_ids(d, 0), float),
             measurements=str(MEASUREMENTS), **o)
    print(f"ridge on {MEASUREMENTS}: {len(d)} scans")


def evaluate_brats21(n_boot: int):
    import subprocess
    import sys
    from prism.analyses import christodoulou_replication as CR
    from prism.analyses import detection as D
    from prism.analyses.reseg_eval import table_path
    assert MASK_SOURCE == "brats21" and "PRISM_MEASUREMENTS" not in os.environ
    env = {**os.environ, "PRISM_MEASUREMENTS": str(table_path("brats21"))}
    subprocess.run([sys.executable, "-m", "prism.analyses.christodoulou_faithful", "--masks", "brats21", "ridge"],
                   env=env, check=True)
    d, y, R = frame()
    z = np.load(OUT / "ridge_brats21.npz")
    assert np.array_equal(z["scan_id"], d.scan_id.to_numpy(str)), "frame differs under the BraTS21 table"
    assert np.array_equal(z["label"], d.label_det.to_numpy(float), equal_nan=True)
    assert np.array_equal(z["iu"], d.intended_use.to_numpy(bool))
    assert np.array_equal(z["fold0"], np.asarray(D.fold_ids(d, 0), float))
    load = lambda out: pd.read_csv(out / "oof_grade4.csv.gz")
    o_new, o_rel = load(OUT), load(OUT_RELEASED)
    for o in (o_new, o_rel):
        assert (o.scan_id.to_numpy() == d.scan_id.to_numpy()).all()
    cal = o_new[[f"CHF#r{r}" for r in range(5)]].to_numpy().T
    raw = o_new[[f"CHFraw#r{r}" for r in range(5)]].to_numpy().T
    rel = CR.ridge_oofs("grade4")
    oofs = {"CHF_brats21": cal, "CHF_released": o_rel[[f"CHF#r{r}" for r in range(5)]].to_numpy().T,
            "B1": rel["B1"], "I_pure_brats21": z["I_pure"], "I_scan_brats21": z["I_scan"],
            "I_pure_released": rel["I_pure"]}
    saved = pd.read_csv(D.OUT / "oof_grade4_primary.csv.gz")
    dev = float(np.nanmax(np.abs(saved[[f"B1#r{r}" for r in range(5)]].to_numpy().T - rel["B1"])))
    dev_b1 = float(np.nanmax(np.abs(z["B1"] - rel["B1"])))
    assert dev < 1e-9 and dev_b1 < 1e-9, (dev, dev_b1)  # B1 uses no mask: identical under both tables
    sets = D.eval_sets(d, "primary")
    iu = np.where(sets["intended_use"])[0]
    yy = d.label_det.to_numpy()[iu]
    chk = {a: float(np.mean(D.aucs(yy, oofs[a][:, iu]))) for a in BRATS_REF}
    print("reproduction checks (intended use): " + ", ".join(f"{a} {v:.4f} ({BRATS_REF[a]})" for a, v in chk.items()))
    assert all(round(chk[a], 3) == BRATS_REF[a] for a in BRATS_REF), chk
    T = {"auc": [], "contrasts": [], "within_phase": [], "brier": []}
    for name in ("intended_use", "all_scans"):
        rows = np.where(sets[name])[0]
        r_, c_, w_ = D.evaluate_set(f"grade4|{name}", d, rows, oofs, n_boot, contrasts=BRATS_CONTRASTS,
                                    seed=BRATS_SEED)
        T["auc"] += r_
        T["contrasts"] += c_
        T["within_phase"] += w_
        yy = d.label_det.to_numpy()[rows]
        T["brier"].append({"set": f"grade4|{name}", "n_pos": int(yy.sum()), "n_neg": int((yy == 0).sum()),
                           **CR.brier_boot(yy, raw[:, rows], cal[:, rows], d.patient_id.to_numpy()[rows], n_boot,
                                           seed=BRATS_SEED)})
    for k_, v in T.items():
        pd.DataFrame(v).to_csv(OUT / f"{k_}.csv", index=False)
    (OUT / "eval_info.json").write_text(json.dumps({"n_boot": n_boot, "seed": BRATS_SEED, "reference_check": chk,
                                                    "b1_max_dev_vs_detection": dev, "b1_max_dev_tables": dev_b1,
                                                    "rows_without_features": int(R.isna().all(1).sum())}, indent=1))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(T["auc"])[["set", "n_scans", "n_pos", "n_neg", "n_patients", "arm", "auc", "auc_lo", "auc_hi",
                                  "auc_repeat_sd"]].round(3).to_string(index=False))
    print(pd.DataFrame(T["contrasts"]).round(3).to_string(index=False))
    print(pd.DataFrame(T["brier"]).round(4).to_string(index=False))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("maskcheck", "extract", "fit", "evaluate", "ridge"))
    ap.add_argument("--masks", choices=MASKS, default="released", help="mask source (default: the released masks)")
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--limit", type=int, default=None, help="extract: smoke test on the first N scans")
    ap.add_argument("--trials", type=int, default=400)
    ap.add_argument("--only", default=None, help="fit: smoke test on one fold, 'repeat,fold'")
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    configure(a.masks)
    if a.step in ("maskcheck", "ridge"):
        assert a.masks == "brats21", "maskcheck / ridge belong to the BraTS21-mask run"
        return maskcheck(a.workers) if a.step == "maskcheck" else ridge_brats21()
    if a.step == "extract":
        extract(a.workers, a.limit)
    elif a.step == "fit":
        fit(a.workers, a.trials, a.only)
    elif a.masks == "brats21":
        evaluate_brats21(a.n_boot)
    else:
        evaluate(a.n_boot)


if __name__ == "__main__":
    main()
