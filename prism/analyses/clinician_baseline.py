"""E4. What each PRISM score adds beyond the reader baseline B: time window + enhancing volume + its change
(plan: docs/results/CLINICIAN_BASELINE_PLAN.md, commit e8014a8, written before the run).

B is fitted with the same pipeline as the PRISM models. MU: five repeats of fivefold grouped CV, intended use.
LUMIERE: B fitted once on all MU grade 4 detection rows (locked-test design), PRISM scores as in M1.
Each gain (score - B) is split into the change in A_W and A_B over the M1 windows.

    PRISM_SKIP_UCSF=1 PYTHONPATH=. .venv/bin/python -m prism.analyses.clinician_baseline [--workers 20] [--n-boot 2000]
    -> outputs/results/analyses/clinician_baseline/   (aggregate CSV only)
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from prism.analyses import detection as D
from prism.analyses import system as S
from prism.analyses.methods import PW, SEED, boot, ci, m1_stats
from prism.config import RESULTS

OUT = RESULTS / "analyses" / "clinician_baseline"
STATS = ("auc", "w", "a_within", "a_across")
MU_REF = {"timeline": 0.822, "images": 0.709, "combined": 0.821}
LUM_REF = {"timeline": 0.689, "combined": 0.773}


def mu_reader_design(d, X):
    ph = d.phase.astype(str).to_numpy()
    B = pd.DataFrame({f"phase_{p}": (ph == p).astype(float) for p in ("pre_rt", "during_rt", "early_post_rt")},
                     index=X["images"].index)
    return pd.concat([B, X["images"][["log_et_cc", "logratio_prev_et"]]], axis=1)


def mu_job(job):
    from prism.experiments import c3_radiomics as c3
    r, k = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, X = S.mu_designs("grade4")
    X = dict(X, reader=mu_reader_design(d, X))
    f = D.fold_ids(d, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    return r, te, {p: c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr, te, seed=r) for p, Xa in X.items()}


def table(cohort, y, scores, c, pid, n_boot):
    est = m1_stats(y, scores, c)
    B = boot(y, scores, c, pid, n_boot, seed=SEED)
    rows = []
    for k in scores:
        for j, s in enumerate(STATS):
            lo, hi = ci([b[k][j] for b in B])
            rows.append({"cohort": cohort, "score": k, "stat": s, "est": est[k][j], "lo": lo, "hi": hi})
    for p in PW:
        for j, s in ((0, "auc"), (2, "a_within"), (3, "a_across")):
            lo, hi = ci([b[p][j] - b["reader"][j] for b in B])
            rows.append({"cohort": cohort, "score": f"{p}-reader", "stat": f"delta_{s}",
                         "est": est[p][j] - est["reader"][j], "lo": lo, "hi": hi})
    return pd.DataFrame(rows)


def run_mu(workers, n_boot):
    d, X = S.mu_designs("grade4")
    n = len(d)
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(mu_job, [(r, k) for r in range(5) for k in range(5)]))
    P = {p: np.full((5, n), np.nan) for p in (*PW, "reader")}
    for r, te, pr in res:
        for p, v in pr.items():
            P[p][r, te] = v
    y, pid = d.label_120.to_numpy(), d.patient_id.to_numpy()
    ev = (d.label_120.notna() & d.intended_use).to_numpy()
    from sklearn.metrics import roc_auc_score
    for p, ref in MU_REF.items():
        a = float(np.mean([roc_auc_score(y[ev], P[p][r, ev]) for r in range(5)]))
        assert abs(a - ref) < 1e-3, (p, a)
    phase = d.phase.astype(str).to_numpy()
    return table("mu", y[ev], {p: v[:, ev] for p, v in P.items()}, phase[ev], pid[ev], n_boot)


def run_lumiere(n_boot):
    c = S.lumiere_cohort()
    L = c["d"]
    y, pid = c["y"], c["patient_id"]
    dm, XX, *_ = D.context("grade4", "primary")
    cols = ["early_post_rt", "log_et_cc", "logratio_prev_et", "has_prev"]
    LX = D.lumiere_detection()[1]
    reader = S._fit(XX["T"][cols], dm, np.arange(len(dm)))(LX[cols])
    scores = {p: c["S"][f"p_{p}"] for p in PW}
    scores["reader"] = reader[None, :]
    from sklearn.metrics import roc_auc_score
    for p, ref in LUM_REF.items():
        a = roc_auc_score(y, scores[p][0])
        assert abs(a - ref) < 1e-3, (p, a)
    ctx = np.where(L.early_post_rt.to_numpy(float) == 1, "within_3m", "other")
    return table("lumiere", y, scores, ctx, pid, n_boot)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    t = pd.concat([run_mu(a.workers, a.n_boot), run_lumiere(a.n_boot)])
    t.to_csv(OUT / "e4_reader_baseline.csv", index=False)
    (OUT / "run_info.json").write_text(json.dumps({"n_boot": a.n_boot, "seed": SEED,
                                                   "seconds": round(time.time() - t0)}, indent=1))
    print(t.to_string())
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
