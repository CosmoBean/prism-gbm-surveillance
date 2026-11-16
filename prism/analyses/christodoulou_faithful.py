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

OUT = RESULTS / "analyses" / "christodoulou_faithful"
FEATURES = OUTPUTS / "features" / "radiomics_christodoulou.csv"
PARTS = OUTPUTS / "features" / "radiomics_christodoulou_parts"
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
    pairs = V.discover_timepoints(MU_IMAGES)
    ok = [(p, t) for p, t in pairs if all(V.is_nonempty_file(f) for f in V.expected_files(p, t, MU_IMAGES).values())]
    return pairs, ok


def _extract_one(pt):
    _single_thread()
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
        futs = [ex.submit(_extract_one, pt) for pt in todo]
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
            "median_seconds_per_scan": float(np.median(secs)) if secs else None, "workers": workers}
    print(json.dumps(info, indent=1), flush=True)
    if limit:
        return
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
    r, k, n_trials = args
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
        plan = (REPO / "docs" / "results" / "CHRISTODOULOU_FAITHFUL_PLAN.md").read_text()
        snap.write_text(f"<!-- snapshot {time.strftime('%Y-%m-%dT%H:%M:%S')}, git {git_state()['commit'][:10]} -->\n"
                        + plan)
    jobs = [(r, k, n_trials) for r in range(5) for k in range(5)]
    if only:  # smoke test, e.g. "0,0"
        r, k = map(int, only.split(","))
        jobs = [(r, k, n_trials)]
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
    (OUT / "fit_info.json").write_text(json.dumps({"n_trials": n_trials, "workers": workers,
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


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("extract", "fit", "evaluate"))
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--limit", type=int, default=None, help="extract: smoke test on the first N scans")
    ap.add_argument("--trials", type=int, default=400)
    ap.add_argument("--only", default=None, help="fit: smoke test on one fold, 'repeat,fold'")
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    if a.step == "extract":
        extract(a.workers, a.limit)
    elif a.step == "fit":
        fit(a.workers, a.trials, a.only)
    else:
        evaluate(a.n_boot)


if __name__ == "__main__":
    main()
