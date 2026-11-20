"""E5. Do the headline MU results depend on the released masks?
(plan: docs/results/MASK_SENSITIVITY_PLAN.md, commit b1ce85b; deviations recorded before results in c235649)

Every MU mask is replaced by the BraTS21 SwinUNETR label map (prism.features.reseg --model brats21). The measurement
table is rebuilt from those maps with reseg_eval.build_table (measurements.py logic; the resection cavity, which
BraTS21 does not segment, comes from the released mask where the new map is background). The E4 models (imaging,
clinical-history, combined, reader baseline) are refitted on each table in a separate process (PRISM_MEASUREMENTS),
same 5x5 folds, intended use. One 2,000-sample patient bootstrap (seed 20261115) over both mask sets gives every
AUC, the paired new - released differences and the E4 gains (score - reader). Mask noise: median fold change of the
enhancing volume between consecutive scans <= 30 days apart (RESEGMENTATION.md section 3).

    PRISM_SKIP_UCSF=1 PYTHONPATH=. .venv/bin/python -m prism.analyses.mask_sensitivity [--workers 6] [--n-boot 2000]
    -> outputs/results/analyses/mask_sensitivity/   (aggregate CSVs; per-set OOF predictions in preds_<set>.npz)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from prism.config import RESULTS

OUT = RESULTS / "analyses" / "mask_sensitivity"
SETS = ("released", "brats21")
SCORES = ("timeline", "images", "combined", "reader")
GAINS = ("images", "combined")
STAT = {"auc": 0, "a_within": 2, "a_across": 3}
REF = {"timeline": 0.822, "images": 0.6688, "combined": 0.8137, "reader": 0.797}  # E4 on the released masks; since
# 2026-11-19 images = A, combined = B (ADOPT_AB.md; before adoption 0.709 / 0.821), via clinician_baseline.mu_job


def new_table():
    from prism.analyses.reseg_eval import table_path
    return table_path("brats21")


# ---------------------------------------------------------------- one mask set (own process)
def predict(name: str, workers: int) -> None:
    """OOF predictions of the E4 models on the measurement table this process reads (config.MEASUREMENTS)."""
    from prism.analyses import clinician_baseline as E4
    from prism.analyses import detection as D
    from prism.analyses import system as S
    from prism.config import MEASUREMENTS
    want = new_table() if name == "brats21" else None
    assert (want is None and "PRISM_MEASUREMENTS" not in os.environ) or MEASUREMENTS == want, MEASUREMENTS
    d, _ = S.mu_designs("grade4")
    n = len(d)
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(E4.mu_job, [(r, k) for r in range(5) for k in range(5)]))
    P = {p: np.full((5, n), np.nan) for p in SCORES}
    for r, te, pr in res:
        for p, v in pr.items():
            P[p][r, te] = v
    assert all(np.isfinite(v).all() for v in P.values())
    ev = (d.label_120.notna() & d.intended_use).to_numpy()
    np.savez(OUT / f"preds_{name}.npz", scan_id=d.scan_id.to_numpy(str), patient_id=d.patient_id.to_numpy(str),
             y=d.label_120.to_numpy(float), phase=d.phase.astype(str).to_numpy(str), ev=ev,
             fold0=np.asarray(D.fold_ids(d, 0), dtype=float), measurements=str(MEASUREMENTS), **{f"p_{p}": v for p, v in P.items()})
    print(f"{name}: {n} scans, {int(ev.sum())} evaluated, table {MEASUREMENTS}")


def run_set(name: str, workers: int) -> None:
    env = {k: v for k, v in os.environ.items() if k != "PRISM_MEASUREMENTS"}
    if name == "brats21":
        env["PRISM_MEASUREMENTS"] = str(new_table())
    subprocess.run([sys.executable, "-m", "prism.analyses.mask_sensitivity", "--predict", name,
                    "--workers", str(workers)], env=env, check=True)


# ---------------------------------------------------------------- comparison
def load_sets():
    z = {s: np.load(OUT / f"preds_{s}.npz") for s in SETS}
    a, b = z["released"], z["brats21"]
    for k in ("scan_id", "patient_id", "y", "phase", "ev", "fold0"):
        assert np.array_equal(a[k], b[k], equal_nan=(k == "y")), f"{k} differs between mask sets"
    ev = a["ev"]
    scores = {f"{p}|{s}": z[s][f"p_{p}"][:, ev] for s in SETS for p in SCORES}
    return a["y"][ev], scores, a["phase"][ev], a["patient_id"][ev]


def check_reference(y, scores):
    from sklearn.metrics import roc_auc_score
    for p, ref in REF.items():
        v = float(np.mean([roc_auc_score(y, r) for r in scores[f"{p}|released"]]))
        assert abs(v - ref) < 1e-3, (p, v, ref)


def compare(y, scores, c, pid, n_boot) -> pd.DataFrame:
    from prism.analyses.methods import SEED, boot, ci, m1_stats
    est = m1_stats(y, scores, c)
    B = boot(y, scores, c, pid, n_boot, seed=SEED)
    rows = []

    def add(kind, score, maskset, stat, f):
        lo, hi = ci([f(b) for b in B])
        rows.append({"kind": kind, "score": score, "masks": maskset, "stat": stat, "est": f(est), "lo": lo, "hi": hi})

    for s in SETS:
        for p in SCORES:
            for st, j in STAT.items():
                add("model", p, s, st, lambda e, k=f"{p}|{s}", j=j: e[k][j])
        for p in GAINS:
            for st, j in STAT.items():
                add("e4_gain", f"{p}-reader", s, f"delta_{st}", lambda e, p=p, s=s, j=j: e[f"{p}|{s}"][j] - e[f"reader|{s}"][j])
    for p in SCORES:
        for st, j in STAT.items():
            add("paired_new_minus_released", p, "brats21-released", f"delta_{st}",
                lambda e, p=p, j=j: e[f"{p}|brats21"][j] - e[f"{p}|released"][j])
    for p in GAINS:
        for st, j in STAT.items():
            add("gain_change", f"{p}-reader", "brats21-released", f"delta_delta_{st}",
                lambda e, p=p, j=j: (e[f"{p}|brats21"][j] - e[f"reader|brats21"][j])
                - (e[f"{p}|released"][j] - e[f"reader|released"][j]))
    return pd.DataFrame(rows)


def mask_noise(n_boot) -> pd.DataFrame:
    """Median fold change of ET (and TC, WT) between consecutive scans <= 30 d apart, both mask sets."""
    from prism.analyses import reseg_eval as RE
    from prism.analyses.methods import SEED
    from prism.config import MEASUREMENTS
    from prism.data.mu import load_index
    tables = {"mu": pd.read_csv(MEASUREMENTS), "brats21": pd.read_csv(new_table())}
    p = RE.consecutive_pairs(tables, load_index())
    q = p[p.gap <= 30]
    rows = []
    for c in RE.COMP:
        new, old = f"abslog_{c}|brats21", f"abslog_{c}|mu"
        lo, hi = RE._cluster_boot(q, lambda d: d[new].median() - d[old].median(), n_boot, seed=SEED)
        rows.append({"window": "gap<=30d", "compartment": c, "n_pairs": len(q), "n_patients": q.patient_id.nunique(),
                     "fold_released": float(np.exp(q[old].median())), "fold_brats21": float(np.exp(q[new].median())),
                     "d_median_abslog": q[new].median() - q[old].median(), "d_lo": lo, "d_hi": hi})
    return pd.DataFrame(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--predict", choices=SETS, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.predict:
        return predict(a.predict, a.workers)
    t0 = time.time()
    assert "PRISM_MEASUREMENTS" not in os.environ, "run the comparison with the default table"
    if not new_table().exists():
        from prism.analyses.reseg_eval import build_table
        new_table().parent.mkdir(parents=True, exist_ok=True)
        m = build_table("brats21", a.workers)
        print(f"built {new_table()}: {len(m)} scans")
    for s in SETS:
        run_set(s, a.workers)
    y, scores, c, pid = load_sets()
    check_reference(y, scores)
    t = compare(y, scores, c, pid, a.n_boot)
    t.to_csv(OUT / "e5_mask_sensitivity.csv", index=False)
    noise = mask_noise(a.n_boot)
    noise.to_csv(OUT / "e5_mask_noise.csv", index=False)
    (OUT / "run_info.json").write_text(json.dumps({"n_boot": a.n_boot, "seconds": round(time.time() - t0),
                                                   "scans": int(len(y)), "patients": int(len(np.unique(pid))),
                                                   "positives": int((y == 1).sum())}, indent=1))
    pd.set_option("display.width", 200)
    print(t.round(3).to_string(index=False))
    print(noise.round(3).to_string(index=False))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
