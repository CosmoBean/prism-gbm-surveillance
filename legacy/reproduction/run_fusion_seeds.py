#!/usr/bin/env python3
"""Re-train MLPFusion/fusion_mlp.py (unmodified) under many seeds and summarize test metrics.

Each run executes the script in its own directory containing train_predictions.csv,
test_predictions.csv, and an embeddings/ link, exactly as the script expects.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import runpy
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "MLPFusion" / "fusion_mlp.py"


def run_one(job: tuple[int, str, str, str]) -> dict:
    seed, inputs_dir, emb_dir, run_dir = job
    import matplotlib
    matplotlib.use("Agg")
    import torch
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

    torch.set_num_threads(1)
    run = Path(run_dir)
    run.mkdir(parents=True, exist_ok=True)
    for name in ("train_predictions.csv", "test_predictions.csv"):
        link = run / name
        if not link.exists():
            link.symlink_to(Path(inputs_dir).resolve() / name)
    if not (run / "embeddings").exists():
        (run / "embeddings").symlink_to(Path(emb_dir).resolve())

    os.chdir(run)
    torch.manual_seed(seed)
    np.random.seed(seed)
    with contextlib.redirect_stdout(io.StringIO()) as log:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    (run / "train.log").write_text(log.getvalue())

    df = pd.read_csv(run / "unified_fusion_results.csv")
    y, p = df.ground_truth, df.unified_fusion_prob
    pred = (p >= 0.48).astype(int)
    return {
        "seed": seed,
        "auc": roc_auc_score(y, p),
        "accuracy": accuracy_score(y, pred),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred),
        "f1": f1_score(y, pred),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs-dir", required=True, help="Folder with train_predictions.csv and test_predictions.csv")
    parser.add_argument("--embeddings-dir", default=str(REPO / "SWIN UNetR" / "embeddings_all"))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seeds", type=int, default=50)
    parser.add_argument("--workers", type=int, default=50)
    args = parser.parse_args()

    out = Path(args.output_dir).resolve()
    jobs = [(s, args.inputs_dir, args.embeddings_dir, str(out / f"seed_{s:03d}")) for s in range(args.seeds)]
    with ProcessPoolExecutor(args.workers) as pool:
        rows = list(pool.map(run_one, jobs))
    res = pd.DataFrame(rows)
    res.to_csv(out / "seed_metrics.csv", index=False)
    summary = res.drop(columns="seed").describe(percentiles=[0.05, 0.5, 0.95]).T[["mean", "std", "min", "5%", "50%", "95%", "max"]]
    print(summary.round(4).to_string())
    (out / "summary.json").write_text(json.dumps(summary.round(4).to_dict(orient="index"), indent=2))


if __name__ == "__main__":
    main()
