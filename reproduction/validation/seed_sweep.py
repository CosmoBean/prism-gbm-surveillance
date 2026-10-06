#!/usr/bin/env python3
"""Re-run radiomics training (train.main, unmodified) across seeds, reusing one feature table.

The seed drives both the held-out patient split and the CV folds, so this measures how much
the reported test metrics depend on which split was drawn.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

RADIOMICS = Path(__file__).resolve().parents[2] / "radiomics"


def run(job: tuple[int, str, str, str, str]) -> dict:
    seed, out_root, feature_table, models, subsets = job
    os.chdir(RADIOMICS)
    from radiomics_pipeline.workflows import train

    out = Path(out_root) / f"seed_{seed:03d}"
    if not (out / "summary.json").exists():
        with contextlib.redirect_stdout(io.StringIO()):
            train.main([
                "--experiment-index", "processed/manifests/experiment_index.csv",
                "--radiomics-yaml", "configs/postoperative_progression_surveillance_radiomics.yaml",
                "--output-dir", str(out), "--feature-table", feature_table,
                "--label-mode", "within_window", "--progression-window-days", "120",
                "--pre-progression-only", "--exclude-after-late-treatment",
                "--models", models, "--modalities", "t1c,flair", "--clinical-feature-set", "hybrid_basic",
                "--feature-subsets", subsets, "--n-trials", "25", "--ranking-folds", "5", "--cv-folds", "5",
                "--permutation-repeats", "20", "--bootstrap-iterations", "300", "--max-workers", "1",
                "--progress-bar", "off", "--seed", str(seed),
            ])
    s = json.loads((out / "summary.json").read_text())
    return {
        "seed": seed,
        "model": s["best_model"]["model"],
        "subset": s["best_model"]["subset_size"],
        "cv_mean_auc": s["best_model"]["mean_fold_auc"],
        "test_auc": s["test_metrics_calibrated"]["roc_auc"],
        "test_brier": s["test_brier_calibrated"],
        "test_bal_acc": s["test_metrics_calibrated"]["balanced_accuracy"],
        "test_n": s["split_summary"]["selected_samples"],
        "test_pos": s["split_summary"]["selected_positives"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-root", required=True)
    p.add_argument("--feature-table", default=str(RADIOMICS / "results/calibrated_forward_hybrid/radiomics_features.csv"))
    p.add_argument("--models", default="lightgbm,logreg,rf,svm")
    p.add_argument("--feature-subsets", default="16,24,32,48")
    p.add_argument("--seeds", default="0-29,62")
    p.add_argument("--workers", type=int, default=31)
    a = p.parse_args()
    seeds: list[int] = []
    for part in a.seeds.split(","):
        lo, _, hi = part.partition("-")
        seeds += list(range(int(lo), int(hi or lo) + 1))
    jobs = [(s, str(Path(a.output_root).resolve()), str(Path(a.feature_table).resolve()), a.models, a.feature_subsets) for s in seeds]
    import pandas as pd
    with ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(run, jobs))
    df = pd.DataFrame(rows).sort_values("seed")
    df.to_csv(Path(a.output_root) / "sweep.csv", index=False)
    print(df.to_string(index=False))
    print(df[["cv_mean_auc", "test_auc", "test_brier", "test_bal_acc"]].describe().round(4).to_string())


if __name__ == "__main__":
    main()
