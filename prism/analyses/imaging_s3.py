"""S3. Can the imaging model rank better within a time window? A wider penalty grid and window-by-enhancement
interactions (plan: docs/results/IMAGING_S3_PLAN.md, commit d56297e, fixed before any fit; results:
docs/results/IMAGING_S3.md). The system does not change; this is an analysis.

Arms (same 27 image measurements, released masks; LUMIERE T_img with the 3-volume model for scans without a previous
scan; S2's solver, stratified_offset.ridge):
  I0       the current imaging model (c3 pipeline on MU, system._fit externally), current grid
  A        S2's stratified model, current grid
  I-wide   I0's model refitted with the S2 solver, wide grid
  A-wide   A, wide grid
  A-int    A plus (within 12 weeks after RT) x {log_et_cc, logratio_prev_et, nadir_all_et, t1c_et_rel}, wide grid;
           the score is the image and interaction terms without the window intercepts
Implementation check: I-wide on the current grid ("I-std") reproduces I0's MU AUC to 0.01.

    PRISM_SKIP_UCSF=0 PYTHONPATH=. .venv/bin/python -m prism.analyses.imaging_s3 [--workers 20] [--n-boot 2000]
    -> outputs/results/analyses/imaging_s3/
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from prism.analyses import stratified_offset as SO
from prism.config import RESULTS

OUT = RESULTS / "analyses" / "imaging_s3"
SEED = 20261121
CS_CUR = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)
CS_WIDE = (0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0)
ENH = ["log_et_cc", "logratio_prev_et", "nadir_all_et", "t1c_et_rel"]
ARMS = ("I0", "A", "I-std", "I-wide", "A-wide", "A-int")
TESTS = ("I-wide", "A-wide", "A-int")


def with_int(X: pd.DataFrame, early: np.ndarray) -> pd.DataFrame:
    """X plus early x f for each enhancement measurement in X (0 outside the window, the value inside)."""
    Z = X.copy()
    for f in [f for f in ENH if f in X.columns]:
        Z[f"early_x_{f}"] = np.where(early, X[f].to_numpy(float), 0.0)
    return Z


def fit(X, d, rows, CS, win=None):
    """Fit on the labelled `rows`; return the score function (image terms only, window intercepts dropped) and the
    fitted model. Unstratified fits keep their single intercept (it does not change the ranking)."""
    rows = rows[d.label_120.notna().to_numpy()[rows]]
    bp = SO._pre(X, rows)
    Z = bp.transform(X.iloc[rows])
    y, g = d.label_120.to_numpy()[rows].astype(float), d.patient_id.to_numpy()[rows]
    m = SO.ridge(Z, y, g, CS, win=None if win is None else win[rows])
    cols = list(X.columns)
    return (lambda Xn: bp.transform(Xn[cols].astype(float)) @ m["beta"]), m, cols


def arms_on(Xi, d, rows, win, early):
    """The four refitted arms on one design; returns {arm: (score_fn, model, needs_early)}."""
    out = {}
    out["A"] = fit(Xi, d, rows, CS_CUR, win) + (False,)
    out["I-std"] = fit(Xi, d, rows, CS_CUR) + (False,)
    out["I-wide"] = fit(Xi, d, rows, CS_WIDE) + (False,)
    out["A-wide"] = fit(Xi, d, rows, CS_WIDE, win) + (False,)
    out["A-int"] = fit(with_int(Xi, early), d, rows, CS_WIDE, win) + (True,)
    return out


def score(arm, Xn, early_n):
    f, _, _, needs = arm
    return f(with_int(Xn, early_n) if needs else Xn)


# ---------------------------------------------------------------- MU, 5 x 5 folds
def mu_frame():
    from prism.analyses import system as S
    d, X = S.mu_designs("grade4")
    win = S.mu_situation(d)[0]
    return d, X["images"], win, (win == "early_post_rt")


def mu_job(job):
    from threadpoolctl import threadpool_limits
    from prism.analyses import detection as D
    from prism.experiments import c3_radiomics as c3
    r, k = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, Xi, win, early = mu_frame()
    f = D.fold_ids(d, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    o = {"r": r, "k": k, "te": te, "I0": c3.fit_predict(c3.BASELINES[0], d, Xi, {}, None, tr, te, seed=r)}
    for name, arm in arms_on(Xi, d, tr, win, early).items():
        o[name] = score(arm, Xi.iloc[te], early[te])
        o[f"C_{name}"] = arm[1]["C"]
    return o


def run_mu(workers):
    d, Xi, win, early = mu_frame()
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(mu_job, [(r, k) for r in range(5) for k in range(5)]))
    P = {a: np.full((5, len(d)), np.nan) for a in ARMS}
    for o in res:
        for a in ARMS:
            P[a][o["r"], o["te"]] = o[a]
    ev = (d.label_120.notna() & d.intended_use).to_numpy()
    fits = [{"r": o["r"], "k": o["k"], **{f"C_{a}": o[f"C_{a}"] for a in ARMS if a != "I0"}} for o in res]
    return {"y": d.label_120.to_numpy()[ev], "pid": d.patient_id.to_numpy()[ev],
            "ctx": d.phase.astype(str).to_numpy()[ev], "S": {a: v[:, ev] for a, v in P.items()}, "fits": fits}


# ---------------------------------------------------------------- locked: LUMIERE, UCSF
def run_locked(skip_ucsf):
    from prism.analyses import detection as D
    from prism.analyses import system as S
    from prism.analyses import ucsf_external as UX
    warnings.filterwarnings("ignore")
    d, A4 = UX.mu_detection("grade4")
    T = D.context("grade4", "primary")[1]["T"]
    win = S.mu_situation(d)[0]
    early = win == "early_post_rt"
    rows = np.arange(len(d))
    timg = [c for c in T.columns if c not in D.T_BASE + SO.T_EXTRA]
    i0_img, i0_v3, i0_ip = S._fit(T[timg], d, rows), S._fit(T[S.VOL3], d, rows), S._fit(A4["A-Ipure"], d, rows)
    a_img, a_v3, a_ip = (arms_on(T[timg], d, rows, win, early), arms_on(T[S.VOL3], d, rows, win, early),
                         arms_on(A4["A-Ipure"], d, rows, win, early))
    locked = {"T_img": a_img, "vol3": a_v3, "A-Ipure": a_ip}
    info = {k: {a: {"C": v[1]["C"], "beta": dict(zip(v[2], np.round(v[1]["beta"][:len(v[2])], 4).tolist()))}
                for a, v in arm.items()} for k, arm in locked.items()}
    out = {"locked_fits": info, "interactions": {k: [f for f in ENH if f in (timg if k == "T_img" else S.VOL3 if
                                                                            k == "vol3" else A4["A-Ipure"].columns)]
                                                for k in locked}}

    L, LX, _ = D.lumiere_detection()
    nop = L.prev_scan_id.eq("").to_numpy()
    eL = L.early_post_rt.eq(1).to_numpy()
    s = {"I0": np.where(nop, i0_v3(LX[S.VOL3]), i0_img(LX[timg]))}
    for a in ARMS[1:]:
        s[a] = np.where(nop, score(a_v3[a], LX[S.VOL3], eL), score(a_img[a], LX[timg], eL))
    out["lumiere"] = {"y": L.label_det.to_numpy(float), "pid": L.patient_id.to_numpy(),
                      "ctx": np.where(eL, "within_3m", "other"), "S": {k: v[None, :] for k, v in s.items()}}
    if not skip_ucsf:
        u = UX.ucsf_frame()
        A = UX.ucsf_designs(u, A4)
        keep = (u.timepoint.eq(2) & u.grade4).to_numpy()
        uk = u[keep].reset_index(drop=True)
        Xu = A["A-Ipure"][keep].reset_index(drop=True)
        yu = np.where(uk.pos_s2_pm30.eq(1), 1.0, np.where(uk.primary_neg, 0.0, np.nan))
        e = ~np.isnan(yu)
        eU = uk.rt_phase.eq("early_post_rt").to_numpy()
        s = {"I0": i0_ip(Xu)}
        for a in ARMS[1:]:
            s[a] = score(a_ip[a], Xu, eU)
        out["ucsf"] = {"y": yu[e].astype(int), "pid": uk.subject_id.to_numpy()[e],
                       "ctx": uk.rt_phase.astype(str).to_numpy()[e],
                       "S": {k: np.asarray(v, float)[None, e] for k, v in s.items()}}
    return out


# ---------------------------------------------------------------- statistics
def stats(cohort, c, n_boot):
    from prism.analyses.methods import boot, ci, m1_stats
    y, pid, ctx, sc = c["y"], c["pid"], c["ctx"], c["S"]
    est = m1_stats(y, sc, ctx)
    B = boot(y, sc, ctx, pid, n_boot, seed=SEED)
    rows = []
    for k in sc:
        for j, s in enumerate(("auc", "w", "a_within", "a_across")):
            lo, hi = ci([b[k][j] for b in B])
            rows.append({"cohort": cohort, "kind": "score", "score": k, "stat": s, "est": est[k][j], "lo": lo,
                         "hi": hi})
    for a in ("A",) + TESTS:
        for ref in ("I0", "A") if a != "A" else ("I0",):
            if a == ref:
                continue
            for j, s in ((0, "auc"), (2, "a_within"), (3, "a_across")):
                lo, hi = ci([b[a][j] - b[ref][j] for b in B])
                rows.append({"cohort": cohort, "kind": "paired_diff", "score": f"{a}-{ref}", "stat": s,
                             "est": est[a][j] - est[ref][j], "lo": lo, "hi": hi})
    return pd.DataFrame(rows)


def main(argv=None) -> None:
    import os
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    mu = run_mu(a.workers)
    from prism.analyses.methods import m1_stats
    est = m1_stats(mu["y"], {k: mu["S"][k] for k in ("I0", "I-std")}, mu["ctx"])
    check = {"I0_auc": est["I0"][0], "I-std_auc": est["I-std"][0]}
    assert abs(check["I0_auc"] - 0.709) < 1e-3, f"I0 does not reproduce the published MU AUC: {check}"
    assert abs(check["I0_auc"] - check["I-std_auc"]) < 0.01, f"implementation check failed: {check}"
    loc = run_locked(os.environ.get("PRISM_SKIP_UCSF", "1") == "1")
    res = [stats("mu", mu, a.n_boot), stats("lumiere", loc["lumiere"], a.n_boot)]
    if "ucsf" in loc:
        res.append(stats("ucsf", loc["ucsf"], a.n_boot))
    df = pd.concat(res, ignore_index=True)
    df.to_csv(OUT / "stats.csv", index=False)
    pd.DataFrame(mu["fits"]).to_csv(OUT / "mu_fits.csv", index=False)
    with open(OUT / "locked.json", "w") as fh:
        json.dump({"check": check, "locked_fits": loc["locked_fits"], "interactions": loc["interactions"],
                   "runtime_s": round(time.time() - t0, 1)}, fh, indent=1, default=float)
    print(json.dumps(check), f"{time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
