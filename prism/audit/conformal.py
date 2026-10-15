"""Patient-level split-conformal prediction sets for a binary label.

Calibration scans are weighted 1 / (number of the patient's calibration scans), so every calibration patient carries
total weight 1 and the test patient weight 1 in the finite-sample correction (a patient-level analogue of split
conformal; scans within a patient are not exchangeable). Score s = 1 - p_hat(y). Set = {y : 1 - p_hat(y) <= q}.
"""

from __future__ import annotations

import numpy as np


def patient_split(patients: np.ndarray, frac_cal: float = 0.3, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Boolean masks (proper-training, calibration) over the rows, split by patient."""
    rng = np.random.default_rng(seed)
    u = np.unique(patients)
    cal = set(rng.choice(u, int(round(frac_cal * len(u))), replace=False))
    m = np.array([p in cal for p in patients])
    return ~m, m


def threshold(scores: np.ndarray, patients: np.ndarray, alpha: float) -> float:
    """Weighted (1 - alpha) quantile with test weight 1; inf if the level cannot be reached."""
    _, inv, cnt = np.unique(patients, return_inverse=True, return_counts=True)
    w = 1.0 / cnt[inv]
    o = np.argsort(scores)
    s, w = scores[o], w[o]
    cum = np.cumsum(w) / (w.sum() + 1.0)
    k = np.searchsorted(cum, 1 - alpha - 1e-12, side="left")
    return float(s[k]) if k < len(s) else np.inf


def scores(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.where(y == 1, 1 - p, p)


def prediction_sets(p: np.ndarray, q: float) -> tuple[np.ndarray, np.ndarray]:
    """(contains 0, contains 1) per scan."""
    return p <= q, (1 - p) <= q


def describe(has0, has1) -> list[str]:
    return ["{0, 1}" if a and b else "{1}" if b else "{0}" if a else "{}" for a, b in zip(has0, has1)]
