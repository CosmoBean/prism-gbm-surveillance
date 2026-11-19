"""Segmentation stage S1: measurement tables from the BraTS21 Swin UNETR label maps (prism.features.reseg).

PLAN: docs/results/SEGMENTER_STAGE_PLAN.md (b5225c7). Results and choices: docs/results/SEGMENTER_STAGE.md.

The same measurement code as the released masks (prism.features.measurements.concepts_from_paths + add_deltas) runs
on the segmenter maps. The network has no resection-cavity class, so nothing is borrowed from the released mask: the
cavity is empty, and every input that needs it is dropped from the models (CAVITY_INPUTS). The intensity reference
(normal-appearing brain beyond 10 mm of the lesion) therefore excludes only the segmented lesion.

  mu       the 591 scans of outputs/features/measurements.csv (same scan set and mri_day), MU T1c / FLAIR
  lumiere  every study with a segmenter map; DeepBraTumIA atlas ct1 / flair (stored grid); mri_day = week * 7
  ucsf     all 596 scans; t1ce / flair; mri_day ordinal (time1 0, time2 1) as prism.features.ucsf_imaging, so the
           day-dependent columns (days_since_prior, rate_*) are dropped

    PYTHONPATH=. .venv/bin/python -m prism.features.seg_measurements [--cohort mu lumiere ucsf] [--workers 24]
    -> $PRISM_OUTPUTS/features/seg_swin/measurements_{cohort}.csv
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from prism.config import MEASUREMENTS, mu_scan_paths
from prism.features.measurements import add_deltas, concepts_from_paths
from prism.features.reseg import SEG, ext_ids, ext_paths, ext_seg_path, seg_path

COHORTS = ("mu", "lumiere", "ucsf")
# Model inputs (of the 27 image measurements) that need the resection cavity: dropped for the segmenter inputs.
CAVITY_INPUTS = ("log_rc_cc", "has_cavity", "et_near_cavity_fraction", "et_cavity_distance", "logratio_prev_rc")


def table_path(cohort: str):
    return SEG / f"measurements_{cohort}.csv"


def _paths(cohort: str, sid: str) -> dict:
    if cohort == "mu":
        pid, tp = sid.split("_Timepoint_")
        p = mu_scan_paths(pid, f"Timepoint_{tp}")
        return {"mask": seg_path(sid, "brats21"), "t1c": p["t1c"], "flair": p["flair"]}
    p = ext_paths(cohort, sid)
    return {"mask": ext_seg_path(cohort, sid), "t1c": p["t1c"], "flair": p["flair"]}


def _one(args) -> dict:
    cohort, sid = args
    pid, tp = sid.split("_Timepoint_") if cohort == "mu" else sid.split("_", 1)
    if cohort == "mu":
        tp = f"Timepoint_{tp}"
    row = concepts_from_paths(_paths(cohort, sid), {"scan_id": sid, "patient_id": pid, "timepoint": tp})
    assert row.get("rc_cc", 0.0) == 0.0, f"{sid}: segmenter map has a cavity label"
    return row


def build(cohort: str, workers: int) -> pd.DataFrame:
    if cohort == "mu":
        ref = pd.read_csv(MEASUREMENTS)
        ids, day = ref.scan_id.tolist(), ref.set_index("scan_id").mri_day
    else:
        ids = [i for i in ext_ids(cohort) if ext_seg_path(cohort, i).exists()]
    with ProcessPoolExecutor(workers) as ex:
        c = pd.DataFrame(list(ex.map(_one, [(cohort, i) for i in ids], chunksize=2)))
    assert c.et_cc.notna().all(), "a segmenter map failed to load"
    if cohort == "mu":
        c["mri_day"] = day.reindex(c.scan_id).to_numpy()
    elif cohort == "lumiere":
        from prism.data.lumiere import _week
        c["mri_day"] = c.timepoint.map(_week) * 7
    else:
        c["mri_day"] = c.timepoint.map({"time1": 0.0, "time2": 1.0})
    m = c.merge(add_deltas(c), on="scan_id", how="left")
    if cohort == "ucsf":
        m = m.drop(columns=[k for k in m if k == "days_since_prior" or k.startswith("rate_")])
    if cohort == "mu":
        ref_cols = list(pd.read_csv(MEASUREMENTS, nrows=1).columns)
        assert sorted(m.columns) == sorted(ref_cols), set(m.columns) ^ set(ref_cols)
        m = m[ref_cols]
    path = table_path(cohort)
    assert not path.exists(), f"{path} exists; not overwritten"
    m.to_csv(path, index=False)
    return m


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism.features.seg_measurements", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cohort", nargs="+", default=list(COHORTS), choices=COHORTS)
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args(argv)
    for c in a.cohort:
        m = build(c, a.workers)
        print(f"{c}: {len(m)} scans, {m.shape[1]} columns -> {table_path(c)}; median ET {m.et_cc.median():.2f} cc")


if __name__ == "__main__":
    main()
