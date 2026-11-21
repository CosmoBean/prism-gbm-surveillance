"""Computational cost of PRISM's scoring stages (revision 2026-11-13, Section 2.5). Prints timings only.

1. Measurement extraction from the released masks and images: `concepts_from_paths` on the first N MU index scans
   (wall time per scan, one process). Prints no measured value.
2. Fitting one ridge model with its penalty search, scoring, and the conformal threshold, on synthetic data with MU's
   shape (181 scans, 92 patients; 14, 27 and 41 inputs). Costs depend on shape only, and the radiomics table needed to
   rebuild the MU designs was not restored after the 2026-11-02 reset.

    PYTHONPATH=. .venv/bin/python -m prism.analyses.timing [--n-scans 20]
"""

from __future__ import annotations

import argparse
import time

import numpy as np
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from prism.audit import conformal as cf
from prism.models.formulations import CS


def extraction(n: int) -> None:
    from prism.config import mu_scan_paths
    from prism.data.mu import load_index
    from prism.features.measurements import concepts_from_paths
    index = load_index().head(n)
    times = []
    for pid, tp in zip(index.patient_id, index.timepoint):
        t = time.perf_counter()
        concepts_from_paths(mu_scan_paths(pid, tp), {"scan_id": f"{pid}_{tp}"})
        times.append(time.perf_counter() - t)
    print(f"measurement extraction: {len(times)} scans, median {np.median(times):.2f} s, max {np.max(times):.2f} s")


def models() -> None:
    rng = np.random.default_rng(0)
    n, g, y = 181, rng.integers(0, 92, 181), rng.integers(0, 2, 181)
    for name, k in (("clinical-history", 14), ("imaging", 27), ("combined", 41)):
        X = rng.normal(size=(n, k)); X[rng.random((n, k)) < 0.05] = np.nan
        t = time.perf_counter()
        pre = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())]).fit(X)
        Z, base = pre.transform(X), LogisticRegression(penalty="l2", max_iter=5000)
        for C in CS:
            for tr, _ in GroupKFold(3).split(Z, y, g):
                clone(base).set_params(C=C).fit(Z[tr], y[tr])
        m = clone(base).set_params(C=0.1).fit(Z, y)
        tf = time.perf_counter() - t
        t = time.perf_counter()
        for _ in range(200):
            m.predict_proba(pre.transform(X))
        print(f"{name}: {k} inputs, fit with penalty search {tf:.3f} s, "
              f"scoring {(time.perf_counter() - t) / 200 / n * 1e6:.1f} us per scan in a batch")
    p, yy, pid = rng.random(60), rng.integers(0, 2, 60), rng.integers(0, 28, 60)
    t = time.perf_counter()
    cf.threshold(cf.scores(p, yy), pid, 0.2)
    print(f"conformal threshold: {(time.perf_counter() - t) * 1e3:.2f} ms")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-scans", type=int, default=20)
    a = ap.parse_args()
    extraction(a.n_scans)
    models()
