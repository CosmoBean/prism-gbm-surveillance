"""Segmentation stage: measurement tables from a segmenter's label maps (S1 Swin UNETR; S4 BraTS24_1).

PLANS: docs/results/SEGMENTER_STAGE_PLAN.md (S1, b5225c7), docs/results/SEGMENTER_BRATS24_PLAN.md (S4).
Results and choices: docs/results/SEGMENTER_STAGE.md (S1).

The same measurement code as the released masks (prism.features.measurements.concepts_from_paths + add_deltas) runs
on the segmenter maps.

  swin     (S1, default) MONAI BraTS21 Swin UNETR, prism.features.reseg. The network has no resection-cavity class,
           so nothing is borrowed from the released mask: the cavity is empty, and every input that needs it is
           dropped from the models (CAVITY_INPUTS). The intensity reference (normal-appearing brain beyond 10 mm of
           the lesion) therefore excludes only the segmented lesion.
  brats24  (S4) BraTS24_1, prism.features.reseg_brats24. Labels 1 NETC, 2 SNFH, 3 ET, 4 RC (MU numbering), so all
           27 image inputs are built. Scans: the run's scope (seg_brats24/ids_<cohort>.txt); MU keeps the scope
           scans that are in outputs/features/measurements.csv (their mri_day).

  mu       swin: the 591 scans of outputs/features/measurements.csv (same scan set and mri_day), MU T1c / FLAIR
  lumiere  every study with a segmenter map (brats24: the scope); DeepBraTumIA atlas ct1 / flair (stored grid);
           mri_day = week * 7
  ucsf     swin: all 596 scans (brats24: the scope); t1ce / flair; mri_day ordinal (time1 0, time2 1) as
           prism.features.ucsf_imaging, so the day-dependent columns (days_since_prior, rate_*) are dropped

    PYTHONPATH=. .venv/bin/python -m prism.features.seg_measurements [--segmenter swin|brats24]
        [--cohort mu lumiere ucsf] [--workers 24] [--complete-only] [--ids ID ... --out FILE]
    -> $PRISM_OUTPUTS/features/seg_swin/measurements_{cohort}.csv          (swin)
       $PRISM_OUTPUTS/features/seg_brats24/measurements_{cohort}.csv       (brats24)
"""

from __future__ import annotations

import argparse
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from prism.config import MEASUREMENTS, OUTPUTS, mu_scan_paths
from prism.features.measurements import add_deltas, concepts_from_paths
from prism.features.reseg import SEG, ext_ids, ext_paths, ext_seg_path, seg_path

COHORTS = ("mu", "lumiere", "ucsf")
SEGMENTERS = ("swin", "brats24")
# Model inputs (of the 27 image measurements) that need the resection cavity: dropped for the Swin UNETR inputs.
CAVITY_INPUTS = ("log_rc_cc", "has_cavity", "et_near_cavity_fraction", "et_cavity_distance", "logratio_prev_rc")
# The released MU measurement table (fixed path: PRISM_MEASUREMENTS may point a model process at a segmenter table).
RELEASED_MU = OUTPUTS / "features" / "measurements.csv"
SEG_BRATS24 = OUTPUTS / "features" / "seg_brats24"
# Folder of the brats24 measurement and volume tables (override only to test the analysis on stand-in tables).
B24_TABLES = Path(os.environ.get("PRISM_BRATS24_TABLES", SEG_BRATS24))


def table_path(cohort: str, segmenter: str = "swin") -> Path:
    return (SEG if segmenter == "swin" else B24_TABLES) / f"measurements_{cohort}.csv"


def map_path(cohort: str, sid: str, segmenter: str = "swin") -> Path:
    if segmenter == "brats24":
        from prism.features.reseg_brats24 import out_path
        return out_path(cohort, sid)
    return seg_path(sid, "brats21") if cohort == "mu" else ext_seg_path(cohort, sid)


def scope_ids(cohort: str) -> list[str]:
    """The S4 run's scope: every scan the plan's models and evaluation sets use."""
    return (SEG_BRATS24 / f"ids_{cohort}.txt").read_text().split()


def table_ids(cohort: str, segmenter: str = "swin") -> list[str]:
    """Scans the measurement table is built on."""
    if segmenter == "swin":
        if cohort == "mu":
            return pd.read_csv(RELEASED_MU).scan_id.tolist()
        return [i for i in ext_ids(cohort) if ext_seg_path(cohort, i).exists()]
    ids = scope_ids(cohort)
    if cohort == "mu":
        ref = set(pd.read_csv(RELEASED_MU).scan_id)
        ids = [i for i in ids if i in ref]
    return ids


def scope_status(cohort: str) -> tuple[int, int]:
    """(BraTS24 maps on disk, scans in scope)."""
    ids = scope_ids(cohort)
    return sum(map_path(cohort, i, "brats24").exists() for i in ids), len(ids)


def scope_complete(cohort: str, settle_s: float = 300) -> tuple[bool, str]:
    """All scope maps exist and the run has finished writing them: the run's volumes csv lists every scope scan, or
    the newest map is older than settle_s seconds."""
    import time
    done, n = scope_status(cohort)
    if done < n:
        return False, f"{done} of {n} maps"
    f = SEG_BRATS24 / f"volumes_brats24_{cohort}.csv"
    if f.exists() and set(scope_ids(cohort)) <= set(pd.read_csv(f, usecols=["scan_id"]).scan_id):
        return True, f"{n} of {n} maps"
    age = time.time() - max(map_path(cohort, i, "brats24").stat().st_mtime for i in scope_ids(cohort))
    return age > settle_s, f"{n} of {n} maps" + ("" if age > settle_s else ", newest written <5 min ago")


def _paths(cohort: str, sid: str, segmenter: str) -> dict:
    if cohort == "mu":
        pid, tp = sid.split("_Timepoint_")
        p = mu_scan_paths(pid, f"Timepoint_{tp}")
    else:
        p = ext_paths(cohort, sid)
    return {"mask": map_path(cohort, sid, segmenter), "t1c": p["t1c"], "flair": p["flair"]}


def _one(args) -> dict:
    cohort, sid, segmenter = args
    pid, tp = sid.split("_Timepoint_") if cohort == "mu" else sid.split("_", 1)
    if cohort == "mu":
        tp = f"Timepoint_{tp}"
    row = concepts_from_paths(_paths(cohort, sid, segmenter), {"scan_id": sid, "patient_id": pid, "timepoint": tp})
    if segmenter == "swin":
        assert row.get("rc_cc", 0.0) == 0.0, f"{sid}: segmenter map has a cavity label"
    return row


def build(cohort: str, workers: int, segmenter: str = "swin", ids: list[str] | None = None,
          out: Path | None = None) -> pd.DataFrame:
    ids = table_ids(cohort, segmenter) if ids is None else list(ids)
    if segmenter == "brats24":
        missing = [i for i in ids if not map_path(cohort, i, segmenter).exists()]
        assert not missing, f"{cohort}: {len(missing)} BraTS24 maps missing, e.g. {missing[:3]}"
    if cohort == "mu":
        ref = pd.read_csv(RELEASED_MU)
        day = ref.set_index("scan_id").mri_day
    with ProcessPoolExecutor(workers) as ex:
        c = pd.DataFrame(list(ex.map(_one, [(cohort, i, segmenter) for i in ids], chunksize=2)))
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
        ref_cols = list(ref.columns)
        assert sorted(m.columns) == sorted(ref_cols), set(m.columns) ^ set(ref_cols)
        m = m[ref_cols]
    path = table_path(cohort, segmenter) if out is None else Path(out)
    assert not path.exists(), f"{path} exists; not overwritten"
    path.parent.mkdir(parents=True, exist_ok=True)
    m.to_csv(path, index=False)
    return m


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism.features.seg_measurements", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--segmenter", default="swin", choices=SEGMENTERS)
    ap.add_argument("--cohort", nargs="+", default=list(COHORTS), choices=COHORTS)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--complete-only", action="store_true",
                    help="brats24: build only the cohorts whose scope is fully segmented; keep existing tables")
    ap.add_argument("--ids", nargs="+", help="test: these scans only (one cohort; needs --out)")
    ap.add_argument("--out", help="test: write the table here (one cohort)")
    a = ap.parse_args(argv)
    assert (a.ids is None or a.out) and (a.out is None or len(a.cohort) == 1), "--ids needs --out; --out 1 cohort"
    for c in a.cohort:
        if a.segmenter == "brats24" and a.ids is None:
            if a.complete_only and table_path(c, a.segmenter).exists():
                print(f"{c}: table exists, kept -> {table_path(c, a.segmenter)}")
                continue
            ok, why = scope_complete(c)
            if not ok:
                print(f"skipped: {c}, {why}")
                if a.complete_only:
                    continue
        m = build(c, a.workers, a.segmenter, a.ids, a.out)
        print(f"{c}: {len(m)} scans, {m.shape[1]} columns -> {a.out or table_path(c, a.segmenter)}; "
              f"median ET {m.et_cc.median():.2f} cc")


if __name__ == "__main__":
    main()
