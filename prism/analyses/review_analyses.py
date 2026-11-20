"""E6. Analyses asked for by the second review round (plan: docs/results/REVIEW_ANALYSES_PLAN.md, commit 161b353,
deviations 6474aad, both before the run; results: docs/results/METHODS_RESULTS.md section E6).

E6a calibration (intercept with slope fixed at 1, slope, Brier, prevalence reference) of the three PRISM scores and
the reader baseline; E6b scans shortly before progression (primary-trained models on the secondary negatives);
E6c unknown IDH / MGMT as its own category (indicator per marker); E6d the reduced combined model (T) on MU.
MU: 5x5 grouped CV, intended use, no refit in the bootstrap; LUMIERE: locked models. One 2,000-sample patient
bootstrap per cohort, seed 20261117.

    PRISM_SKIP_UCSF=1 PYTHONPATH=. .venv/bin/python -m prism.analyses.review_analyses [--workers 20] [--n-boot 2000]
    -> outputs/results/analyses/review_analyses/   (aggregate CSV only)
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from threadpoolctl import threadpool_limits

from prism.analyses import detection as D
from prism.analyses import system as S
from prism.analyses.clinician_baseline import mu_reader_design
from prism.config import RESULTS

OUT = RESULTS / "analyses" / "review_analyses"
SEED = 20261117
PW = S.PW
MU_REF = {"timeline": 0.822, "images": 0.709, "combined": 0.821, "reader": 0.797}
LUM_REF = {"combined": 0.773}
CAL = ("timeline", "images", "combined", "reader")
UNK = ["idh_unknown", "mgmt_unknown"]
EPS = 1e-6


# ---------------------------------------------------------------- statistics
def auc(y, s):
    """AUC (ties 1/2) of each row of s (R, n) against y (n,)."""
    pos = y == 1
    n1, n0 = pos.sum(), (~pos).sum()
    if n1 == 0 or n0 == 0:
        return np.full(s.shape[0], np.nan)
    rk = rankdata(s, axis=1)
    return (rk[:, pos].sum(axis=1) - n1 * (n1 + 1) / 2) / (n1 * n0)


def _logit(p):
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def _newton(Z, y, off, it=100):
    """Unpenalised logistic MLE with offset; Z (n, k)."""
    b = np.zeros(Z.shape[1])
    for _ in range(it):
        eta = np.clip(Z @ b + off, -30, 30)
        mu = 1 / (1 + np.exp(-eta))
        g = Z.T @ (y - mu)
        H = (Z * (mu * (1 - mu))[:, None]).T @ Z
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            return np.full(Z.shape[1], np.nan)
        b += step
        if np.max(np.abs(step)) < 1e-10:
            break
    return b


def calib(y, p):
    """(intercept with slope 1, slope, Brier, prevalence reference) for one prediction vector."""
    z = _logit(p)
    one = np.ones((len(y), 1))
    a = _newton(one, y, z)[0]
    slope = _newton(np.column_stack([one, z]), y, np.zeros(len(y)))[1]
    prev = y.mean()
    return np.array([a, slope, np.mean((p - y) ** 2), prev * (1 - prev)])


def calib_mean(y, P):
    return np.nanmean([calib(y, P[r]) for r in range(P.shape[0])], axis=0)


def stats(y, sets: dict, P: dict, cal_set: str):
    """One sample: {key: value}. sets = {name: row mask}; P = {score: (R, n)}."""
    out = {}
    for sname, (m, scores) in sets.items():
        for k in scores:
            out[("auc", sname, k)] = float(np.mean(auc(y[m], P[k][:, m])))
    m = sets[cal_set][0]
    for k in CAL:
        v = calib_mean(y[m], P[k][:, m])
        for j, s in enumerate(("cal_intercept", "cal_slope", "brier", "brier_prevalence")):
            out[(s, cal_set, k)] = float(v[j])
    return out


def _boot_chunk(args):
    y, sets, P, cal_set, idxs = args
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    res = []
    for idx in idxs:
        res.append(stats(y[idx], {k: (m[idx], sc) for k, (m, sc) in sets.items()},
                         {k: v[:, idx] for k, v in P.items()}, cal_set))
    return res


def bootstrap(y, pid, sets, P, cal_set, n_boot, workers):
    rng = np.random.default_rng(SEED)
    u = np.unique(pid)
    rows = {p: np.where(pid == p)[0] for p in u}
    idxs = [np.concatenate([rows[p] for p in rng.choice(u, len(u))]) for _ in range(n_boot)]
    chunks = [idxs[i::workers] for i in range(workers)]
    with ProcessPoolExecutor(workers) as ex:
        parts = list(ex.map(_boot_chunk, [(y, sets, P, cal_set, c) for c in chunks]))
    out = [None] * n_boot
    for i, part in enumerate(parts):
        for j, r in enumerate(part):
            out[i + j * workers] = r
    return out


def ci(v):
    v = np.asarray(v, float)
    v = v[~np.isnan(v)]
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if len(v) else (np.nan, np.nan)


def rows_for(cohort, part, est, B, keys, label=None):
    out = []
    for key in keys:
        if isinstance(key, tuple) and key[0] == "diff":
            _, a, b = key
            e = est[a] - est[b]
            lo, hi = ci([x[a] - x[b] for x in B])
            stat, sset, score = f"delta_{a[0]}", f"{a[1]}-{b[1]}" if a[1] != b[1] else a[1], \
                f"{a[2]}-{b[2]}" if a[2] != b[2] else a[2]
        else:
            e = est[key]
            lo, hi = ci([x[key] for x in B])
            stat, sset, score = key
        out.append({"part": part, "cohort": cohort, "set": sset, "score": score, "stat": stat, "est": e,
                    "lo": lo, "hi": hi})
    return out


# ---------------------------------------------------------------- designs
def unknown_mu(d):
    from prism.analyses.phase_censoring import pre_diagnosis
    blind = pre_diagnosis(d)
    return pd.DataFrame({"idh_unknown": (d.idh.eq("unknown").to_numpy() | blind).astype(float),
                         "mgmt_unknown": (d.mgmt.eq("unknown").to_numpy() | blind).astype(float)}, index=d.index)


def mu_all_designs():
    d, X = S.mu_designs("grade4")
    dm, XX, *_ = D.context("grade4", "primary")
    assert (dm.scan_id.to_numpy() == d.scan_id.to_numpy()).all()
    U = unknown_mu(d)
    tl_u = pd.concat([X["timeline"], U], axis=1)
    return d, {**X, "reader": mu_reader_design(d, X), "reduced_combined": XX["T"],
               "timeline_unk": tl_u, "combined_unk": pd.concat([tl_u, X["images"]], axis=1)}


def mu_job(job):
    from prism.experiments import c3_radiomics as c3
    r, k = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, X = mu_all_designs()
    f = D.fold_ids(d, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    return r, te, {p: c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr, te, seed=r) for p, Xa in X.items()}


# ---------------------------------------------------------------- cohorts
def run_mu(workers, n_boot):
    d, X = mu_all_designs()
    n = len(d)
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(mu_job, [(r, k) for r in range(5) for k in range(5)]))
    P = {p: np.full((5, n), np.nan) for p in X}
    for r, te, pr in res:
        for p, v in pr.items():
            P[p][r, te] = v
    pos = d.label_det.eq(1).to_numpy()
    iu = d.intended_use.to_numpy()
    prim = iu & (pos | d.neg_primary.to_numpy())
    sec = iu & (pos | d.neg_secondary.to_numpy())
    assert (prim == (d.label_120.notna().to_numpy() & iu)).all() and (sec >= prim).all()
    added = sec & ~prim
    y = pos.astype(float)
    for p, ref in MU_REF.items():
        a = float(np.mean(auc(y[prim], P[p][:, prim])))
        assert abs(a - ref) < 1e-3, (p, a)
    assert np.isfinite(np.stack([P[p][:, sec] for p in X])).all()
    # restrict everything to the widest set (secondary) and bootstrap its patients
    yy, pid = y[sec], d.patient_id.to_numpy()[sec]
    m_prim, m_add = prim[sec], (added | (pos & iu))[sec]
    PP = {p: v[:, sec] for p, v in P.items()}
    sets = {"primary": (m_prim, list(X)), "secondary": (np.ones(sec.sum(), bool), list(CAL)),
            "added_only": (m_add, list(CAL))}
    est = stats(yy, sets, PP, "primary")
    B = bootstrap(yy, pid, sets, PP, "primary", n_boot, workers)
    counts = {"cohort": "mu", "primary": [int((pos & prim).sum()), int((prim & ~pos).sum()),
                                          int(d.patient_id[prim].nunique())],
              "secondary": [int((pos & sec).sum()), int((sec & ~pos).sum()), int(d.patient_id[sec].nunique())],
              "added_negatives": [int(added.sum()), int(d.patient_id[added].nunique())],
              "unknown_in_primary": {c: int(unknown_mu(d)[c].to_numpy()[prim].sum()) for c in UNK}}
    rows = []
    rows += rows_for("mu", "E6a", est, B, [(s, "primary", k) for k in CAL
                                          for s in ("cal_intercept", "cal_slope", "brier", "brier_prevalence")])
    keys = [("auc", "secondary", k) for k in CAL] + [("auc", "primary", k) for k in CAL]
    keys += [("diff", ("auc", "secondary", k), ("auc", "primary", k)) for k in CAL]
    keys += [("diff", ("auc", s, k), ("auc", s, "reader")) for s in ("secondary", "primary") for k in PW]
    keys += [("auc", "added_only", k) for k in CAL]
    rows += rows_for("mu", "E6b", est, B, keys)
    keys = [("auc", "primary", k) for k in ("timeline_unk", "combined_unk")]
    keys += [("diff", ("auc", "primary", f"{k}_unk"), ("auc", "primary", k)) for k in ("timeline", "combined")]
    rows += rows_for("mu", "E6c", est, B, keys)
    keys = [("auc", "primary", "reduced_combined"), ("auc", "primary", "combined"),
            ("diff", ("auc", "primary", "reduced_combined"), ("auc", "primary", "combined"))]
    rows += rows_for("mu", "E6d", est, B, keys)
    return rows, counts


def run_lumiere(workers, n_boot):
    from prism.data.lumiere import demographics
    c = S.lumiere_cohort()
    L = c["d"]
    y, pid = c["y"], c["patient_id"]
    dm, XX, *_ = D.context("grade4", "primary")
    LX = D.lumiere_detection()[1]
    cols = ["early_post_rt", "log_et_cc", "logratio_prev_et", "has_prev"]
    rows_ = np.arange(len(dm))
    P = {p: c["S"][f"p_{p}"] for p in PW}
    P["reader"] = S._fit(XX["T"][cols], dm, rows_)(LX[cols])[None, :]
    # current coding reproduces the locked scores
    assert np.allclose(S._fit(XX["T"], dm, rows_)(LX), P["combined"][0])
    assert np.allclose(S._fit(XX["T"][D.T_BASE], dm, rows_)(LX), P["timeline"][0])
    # unknown as its own category
    dmo = demographics()
    idh = dmo.idh_raw.astype(str).str.strip().str.lower()
    mg = dmo.mgmt_raw.astype(str).str.strip().str.lower()
    dmo["idh_unknown"] = (~(idh.eq("wt") | idh.str.contains("mut"))).astype(float)
    dmo["mgmt_unknown"] = (~(mg.eq("methylated") | mg.eq("not methylated"))).astype(float)
    mol = L[["patient_id"]].merge(dmo[["patient_id"] + UNK], on="patient_id", how="left")
    assert len(mol) == len(L) and mol[UNK].notna().all().all()
    LXu = pd.concat([LX.reset_index(drop=True), mol[UNK].reset_index(drop=True)], axis=1)
    LXu.index = LX.index
    Tu = pd.concat([XX["T"], unknown_mu(dm)], axis=1)
    P["timeline_unk"] = S._fit(Tu[D.T_BASE + UNK], dm, rows_)(LXu)[None, :]
    P["combined_unk"] = S._fit(Tu, dm, rows_)(LXu)[None, :]
    for p, ref in LUM_REF.items():
        a = float(auc(y, P[p])[0])
        assert abs(a - ref) < 1e-3, (p, a)
    sets = {"all": (np.ones(len(y), bool), list(P))}
    est = stats(y, sets, P, "all")
    B = bootstrap(y, pid, sets, P, "all", n_boot, workers)
    rows = rows_for("lumiere", "E6a", est, B, [(s, "all", k) for k in CAL
                                              for s in ("cal_intercept", "cal_slope", "brier", "brier_prevalence")])
    keys = [("auc", "all", k) for k in ("timeline", "combined", "timeline_unk", "combined_unk")]
    keys += [("diff", ("auc", "all", f"{k}_unk"), ("auc", "all", k)) for k in ("timeline", "combined")]
    rows += rows_for("lumiere", "E6c", est, B, keys)
    counts = {"cohort": "lumiere", "scans": int(len(y)), "positives": int((y == 1).sum()),
              "patients": int(len(np.unique(pid))), "unknown": {k: int(mol[k].sum()) for k in UNK}}
    return rows, counts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    r_mu, n_mu = run_mu(a.workers, a.n_boot)
    r_l, n_l = run_lumiere(a.workers, a.n_boot)
    t = pd.DataFrame(r_mu + r_l)
    t.to_csv(OUT / "e6_review_analyses.csv", index=False)
    (OUT / "run_info.json").write_text(json.dumps({"n_boot": a.n_boot, "seed": SEED, "counts": [n_mu, n_l],
                                                   "seconds": round(time.time() - t0)}, indent=1))
    pd.set_option("display.width", 200)
    print(t.to_string())
    print(json.dumps([n_mu, n_l]))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
