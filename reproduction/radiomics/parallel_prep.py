#!/usr/bin/env python3
"""Parallel version of the last two `main.py prep-data` steps (preprocess + build_index).

Runs preprocess.process_case for every timepoint in a process pool, then lets the repo's
unchanged preprocess.main() / build_index.main() consume the precomputed results, so the
written manifests are identical to the single-core run (~70 s instead of ~50 min).
Requires metadata/ from the audit + split steps (`main.py prep-data` runs those first).
"""
from __future__ import annotations

import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

RADIOMICS = Path(__file__).resolve().parents[2] / "radiomics"
os.chdir(RADIOMICS)
sys.path.insert(0, str(RADIOMICS))

import pandas as pd  # noqa: E402

from radiomics_pipeline.workflows import build_index, preprocess  # noqa: E402

ARGS = ["--dataset-root", "PKG-MU-Glioma-Post/MU-Glioma-Post", "--manifest-csv", "metadata/manifest.csv",
        "--summary-csv", "metadata/timepoint_summary.csv", "--splits-csv", "metadata/splits.csv", "--output-root", "processed"]
a = preprocess.parse_args(ARGS)
repo_root = Path.cwd().resolve()
manifest = pd.read_csv(a.manifest_csv)
split_map = {r.patient_id: r.split for r in pd.read_csv(a.splits_csv).itertuples(index=False)}
keys = pd.read_csv(a.summary_csv)[["patient_id", "timepoint"]].drop_duplicates()


def run(key):
    pid, tp = key
    rows = manifest[(manifest.patient_id == pid) & (manifest.timepoint == tp)].copy()
    return key, preprocess.process_case(
        case_rows=rows, split_name=split_map.get(pid, ""), dataset_root=a.dataset_root.resolve(),
        output_root=a.output_root.resolve(), repo_root=repo_root, clip_low=a.clip_low, clip_high=a.clip_high,
        roi_margin=a.roi_margin)


if __name__ == "__main__":
    for d in ("images_native", "images_reoriented", "images_resampled", "images_normalized", "roi_tumor", "masks",
              "radiomics_inputs", "manifests"):
        (a.output_root / d).mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(48) as ex:
        results = dict(ex.map(run, [tuple(k) for k in keys.itertuples(index=False)], chunksize=2))
    print(f"precomputed {len(results)} cases", flush=True)
    preprocess.process_case = lambda case_rows, **kw: results[(case_rows.patient_id.iloc[0], case_rows.timepoint.iloc[0])]
    preprocess.main(ARGS)
    build_index.main(["--clinical-xlsx", "PKG-MU-Glioma-Post/MU-Glioma-Post_ClinicalData-July2025.xlsx",
                      "--processed-root", "processed", "--output-dir", "processed/manifests"])
