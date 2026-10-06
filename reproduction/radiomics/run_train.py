#!/usr/bin/env python3
"""Same flow as `python main.py train` (radiomics_pipeline/main.py:run_train) with its defaults,
plus --reuse-case-features (cache only, results unchanged) and 96 extraction workers.

Exports to results/calibrated_forward_hybrid_model so the shipped models/calibrated is untouched.
Note: with the default search the winner is SVM-32, and export_calibrated then fails
(shap.LinearExplainer needs a linear model); the training results are written before that.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

RADIOMICS = Path(__file__).resolve().parents[2] / "radiomics"
os.chdir(RADIOMICS)
sys.path.insert(0, str(RADIOMICS))

from radiomics_pipeline.main import build_parser  # noqa: E402
from radiomics_pipeline.workflows import export_calibrated, train  # noqa: E402

args = build_parser().parse_args(["train", "--max-workers", "96"])
train.main([
    "--experiment-index", str(args.experiment_index), "--radiomics-yaml", str(args.radiomics_yaml),
    "--output-dir", str(args.result_dir), "--label-mode", "within_window", "--progression-window-days", "120",
    "--pre-progression-only", "--exclude-after-late-treatment", "--models", args.models,
    "--modalities", args.modalities, "--clinical-feature-set", args.clinical_feature_set,
    "--feature-subsets", args.feature_subsets, "--n-trials", str(args.n_trials),
    "--ranking-folds", str(args.ranking_folds), "--cv-folds", str(args.cv_folds),
    "--permutation-repeats", str(args.permutation_repeats), "--bootstrap-iterations", str(args.bootstrap_iterations),
    "--max-workers", str(args.max_workers), "--progress-bar", "off", "--seed", str(args.seed),
    "--reuse-case-features",
])
export_calibrated.main(["--result-dir", str(args.result_dir), "--output-dir", "results/calibrated_forward_hybrid_model",
                        "--seed", str(args.seed), "--cv-folds", str(args.cv_folds)])
