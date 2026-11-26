"""S2. A stratified imaging model (A) and an offset combined model (B)
(plan: docs/results/STRATIFIED_OFFSET_PLAN.md, commit 1856aa9, fixed before any fit; results and implementation
choices: docs/results/STRATIFIED_OFFSET.md).

A  ridge logistic regression on the imaging model's inputs with one unpenalised intercept per MU time window (the
   card's phase cells: before the end of RT, within 12 weeks after it, later, unknown; system.mu_situation).
   Score = beta . x_img (window intercepts dropped). Same design per centre as the current imaging model
   (MU / UCSF: A-Ipure; LUMIERE: T_img, and the 3-volume model for scans without a previous scan).
B  logit p = eta_base + b0 + beta . z, eta_base = the timing-and-enhancement baseline's training-fold logit as a
   fixed offset (coefficient 1). z = the current combined model's inputs (MU: B1 + A-Ipure; externally the reduced
   form T, with the locked reduced baseline early_post_rt + log ET + log ratio + has_prev as the offset).
Both: c3.BASE_PRE (median imputation with indicators, standardisation), penalty C in formulations.CS chosen by
threefold patient-grouped CV (GroupKFold, as formulations.fit) on log loss; a custom L-BFGS objective
C * sum(log loss) + 0.5 |beta|^2 (+ 1e-8 * 0.5 |window intercepts|^2, effectively unpenalised), checked on toy data
against sklearn and an independent Newton solver (toy_checks.json).
MU: the 5 x 5 patient-grouped folds, intended use (146 scans); locked: one fit on all MU training rows, applied to
LUMIERE (178) and UCSF (grade 4 scan 2, 69). One 2,000-sample patient bootstrap per cohort (seed 20261120) covers
every score, so differences are paired. The current models' reference AUCs are asserted before any comparison.

    PRISM_SKIP_UCSF=0 PYTHONPATH=. .venv/bin/python -m prism.analyses.stratified_offset [--workers 20] [--n-boot 2000]
    -> outputs/results/analyses/stratified_offset/
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.base import clone
from sklearn.model_selection import GroupKFold

from prism.config import RESULTS

OUT = RESULTS / "analyses" / "stratified_offset"
SEED = 20261120
ALPHA = 0.2
EPS_WIN = 1e-8
BASE_LOCKED = ["early_post_rt", "log_et_cc", "logratio_prev_et", "has_prev"]
T_EXTRA = ["has_prev", "log_days_from_prev"]
REF = {  # current models (system.EXPECTED, E4, S1 released masks); asserted to 1e-3
    "mu": {"images": 0.709, "combined": 0.821, "baseline": 0.797, "reduced_combined": 0.804},
    "lumiere": {"images": 0.6539, "combined": 0.7729, "baseline": 0.7342},
    "ucsf": {"images": 0.7259, "combined": 0.8560, "baseline": 0.8664}}
REF_SPLIT = {("mu", "images"): (0.68, 0.73)}  # M1 A_W, A_B (to 0.01)


# ---------------------------------------------------------------- penalised logistic with free intercepts / offset
def _sig(x):
    return 1.0 / (1.0 + np.exp(-x))


def fit_lr(Z, y, C, W=None, off=None, eps=EPS_WIN):
    """argmin C * sum logloss(y, off + W a + Z beta) + 0.5 |beta|^2 + 0.5 eps |a|^2.
    W: (n, k) intercept columns (one-hot windows; default a single column of ones). Returns (a, beta)."""
    n, p = Z.shape
    W = np.ones((n, 1)) if W is None else W
    off = np.zeros(n) if off is None else off
    k = W.shape[1]
    M = np.hstack([W, Z])
    pen = np.r_[np.full(k, eps), np.ones(p)]

    def f(t):
        eta = off + M @ t
        loss = C * np.sum(np.logaddexp(0, eta) - y * eta) + 0.5 * np.sum(pen * t * t)
        g = C * (M.T @ (_sig(eta) - y)) + pen * t
        return loss, g

    r = minimize(f, np.zeros(k + p), jac=True, method="L-BFGS-B",
                 options={"maxiter": 50000, "gtol": 1e-9, "ftol": 1e-15, "maxcor": 30})
    return r.x[:k], r.x[k:]


def _logloss(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))


def _onehot(win, levels):
    return (np.asarray(win)[:, None] == np.asarray(levels)[None, :]).astype(float)


def _win_intercepts(a, levels, win_tr, win_new):
    """Intercept per row of win_new; a window absent from training gets the row-weighted mean of the others."""
    cnt = np.array([(win_tr == l).sum() for l in levels], float)
    seen = cnt > 0
    fill = float(np.sum(a[seen] * cnt[seen]) / cnt[seen].sum())
    m = {l: (a[i] if seen[i] else fill) for i, l in enumerate(levels)}
    return np.array([m.get(w, fill) for w in win_new])


def ridge(Z, y, g, CS, win=None, off=None):
    """C by GroupKFold(3) on log loss (as formulations.fit), then the full fit. win: window label per row (A);
    off: offset per row (B). Returns dict(C, a, beta, levels)."""
    levels = np.unique(win) if win is not None else None
    off = np.zeros(len(y)) if off is None else off
    losses = []
    for C in CS:
        ls = []
        for tr, va in GroupKFold(n_splits=3).split(Z, y, g):
            if len(np.unique(y[tr])) < 2:
                continue
            if win is None:
                a, b = fit_lr(Z[tr], y[tr], C, off=off[tr])
                eta = off[va] + a[0] + Z[va] @ b
            else:
                lv = np.unique(win[tr])
                a, b = fit_lr(Z[tr], y[tr], C, W=_onehot(win[tr], lv), off=off[tr])
                eta = off[va] + _win_intercepts(a, lv, win[tr], win[va]) + Z[va] @ b
            ls.append(_logloss(y[va], _sig(eta)))
        losses.append(np.mean(ls))
    C = CS[int(np.argmin(losses))]
    if win is None:
        a, b = fit_lr(Z, y, C, off=off)
    else:
        a, b = fit_lr(Z, y, C, W=_onehot(win, levels), off=off)
    return {"C": C, "a": a, "beta": b, "levels": levels, "cv_loss": losses}


# ---------------------------------------------------------------- toy checks
def _newton(M, y, C, pen, off):
    t = np.zeros(M.shape[1])
    for _ in range(200):
        p = _sig(off + M @ t)
        g = C * M.T @ (p - y) + pen * t
        H = C * (M.T * (p * (1 - p))) @ M + np.diag(pen)
        step = np.linalg.solve(H, g)
        t -= step
        if np.abs(step).max() < 1e-13:
            break
    return t


def toy_checks() -> dict:
    from sklearn.linear_model import LogisticRegression
    rng = np.random.default_rng(0)
    n, p = 600, 5
    Z = rng.normal(size=(n, p))
    win = rng.choice(["w0", "w1", "w2", "w3"], n, p=[.1, .3, .3, .3])
    shift = {"w0": -3.0, "w1": -1.0, "w2": 0.5, "w3": 2.5}
    beta0 = np.array([1.0, -0.5, 0.25, 0.0, 0.8])
    eta = np.array([shift[w] for w in win]) + Z @ beta0
    y = (rng.random(n) < _sig(eta)).astype(float)
    lv = np.unique(win)
    W = _onehot(win, lv)
    out = {}
    # 1. one intercept, no offset: equals sklearn (lbfgs leaves the intercept unpenalised)
    for C in (0.01, 1.0):
        a, b = fit_lr(Z, y, C)
        sk = LogisticRegression(C=C, tol=1e-12, max_iter=100000).fit(Z, y)
        out[f"plain_vs_sklearn_C{C}"] = float(max(abs(a[0] - sk.intercept_[0]), np.abs(b - sk.coef_[0]).max()))
    # 2. window intercepts unpenalised: (a) equal an independent Newton solve; (b) with beta forced to ~0 (tiny C)
    #    with no informative inputs they equal the empirical window logits at the smallest C of the grid; (c) sklearn with the dummies scaled by 1e4 (penalty negligible)
    a, b = fit_lr(Z, y, 0.05, W=W)
    pen = np.r_[np.full(4, EPS_WIN), np.ones(p)]
    t = _newton(np.hstack([W, Z]), y, 0.05, pen, np.zeros(n))
    out["windows_vs_newton"] = float(np.abs(np.r_[a, b] - t).max())
    a0, b0 = fit_lr(np.zeros((n, 1)), y, 0.01, W=W)
    emp = np.array([np.log(y[win == l].mean() / (1 - y[win == l].mean())) for l in lv])
    out["windows_noinputs_vs_empirical_logit"] = float(np.abs(a0 - emp).max())
    sk = LogisticRegression(C=0.05, tol=1e-12, max_iter=100000, fit_intercept=False).fit(np.hstack([W * 1e4, Z]), y)
    out["windows_vs_sklearn_scaled_dummies"] = float(np.abs(np.r_[sk.coef_[0][:4] * 1e4, sk.coef_[0][4:]]
                                                            - np.r_[a, b]).max())
    # the same windows with ordinary penalised dummies differ (shows the partial penalty matters)
    skp = LogisticRegression(C=0.05, tol=1e-12, max_iter=100000, fit_intercept=False).fit(np.hstack([W, Z]), y)
    out["windows_if_penalised_maxdiff"] = float(np.abs(skp.coef_[0][:4] - a).max())
    # 3. offset: equals an independent Newton solve with the same offset
    off = 0.7 * Z[:, 0] + rng.normal(size=n) * 0.3
    a, b = fit_lr(Z[:, 1:], y, 0.3, off=off)
    t = _newton(np.hstack([np.ones((n, 1)), Z[:, 1:]]), y, 0.3, np.r_[EPS_WIN, np.ones(p - 1)], off)
    out["offset_vs_newton"] = float(np.abs(np.r_[a, b] - t).max())
    # a constant shift of the offset moves only the free intercept (coefficient of the offset fixed at 1)
    a2, b2 = fit_lr(Z[:, 1:], y, 0.3, off=off + 5.0)
    out["offset_shift_moves_only_intercept"] = float(max(abs(a2[0] + 5.0 - a[0]), np.abs(b2 - b).max()))
    # offset gradient condition: sum(y - p) = 0 at the optimum (free intercept)
    out["offset_score_eq_intercept"] = float(abs(np.sum(y - _sig(off + a[0] + Z[:, 1:] @ b))))
    ok = (out["plain_vs_sklearn_C0.01"] < 1e-5 and out["plain_vs_sklearn_C1.0"] < 1e-5
          and out["windows_vs_newton"] < 1e-5 and out["windows_noinputs_vs_empirical_logit"] < 1e-4
          and out["windows_vs_sklearn_scaled_dummies"] < 1e-3 and out["offset_vs_newton"] < 1e-5
          and out["offset_shift_moves_only_intercept"] < 1e-5 and out["offset_score_eq_intercept"] < 1e-4)
    out["all_ok"] = bool(ok)
    assert ok, out
    return out


# ---------------------------------------------------------------- model wrappers on a design
def _pre(X, rows):
    from prism.experiments import c3_radiomics as c3
    return clone(c3.BASE_PRE).fit(X.iloc[rows])


def fit_A(X, d, rows, win):
    """Stratified imaging model on labelled `rows`. Returns score function and window-calibrated probability."""
    from prism.models.formulations import CS
    rows = rows[d.label_120.notna().to_numpy()[rows]]
    bp = _pre(X, rows)
    Z = bp.transform(X.iloc[rows])
    y, g = d.label_120.to_numpy()[rows].astype(float), d.patient_id.to_numpy()[rows]
    m = ridge(Z, y, g, CS, win=win[rows])
    wtr = win[rows]

    def score(Xn):
        return bp.transform(Xn[list(X.columns)].astype(float)) @ m["beta"]

    def prob(Xn, wn):
        return _sig(_win_intercepts(m["a"], m["levels"], wtr, wn) + score(Xn))
    return score, prob, m


def baseline_logit(R, d, rows, seed):
    """The baseline as c3.fit_predict / system._fit fit it (labelled rows), returning its logit function."""
    from prism.experiments import c3_radiomics as c3
    rows = rows[d.label_120.notna().to_numpy()[rows]]
    bp = _pre(R, rows)
    mb = c3._ridge(bp.transform(R.iloc[rows]), d, rows, seed)
    return lambda Xn: mb.decision_function(bp.transform(Xn[list(R.columns)].astype(float)))


def fit_B(Xc, R, d, rows, seed):
    """Offset combined model: offset = baseline logit fitted on the same rows. Returns (prob, increment, model)."""
    from prism.models.formulations import CS
    rows = rows[d.label_120.notna().to_numpy()[rows]]
    eb = baseline_logit(R, d, rows, seed)
    off = eb(R.iloc[rows])
    bp = _pre(Xc, rows)
    Z = bp.transform(Xc.iloc[rows])
    y, g = d.label_120.to_numpy()[rows].astype(float), d.patient_id.to_numpy()[rows]
    m = ridge(Z, y, g, CS, off=off)

    def incr(Xn):
        return bp.transform(Xn[list(Xc.columns)].astype(float)) @ m["beta"]

    def prob(Xn, Rn):
        return _sig(eb(Rn) + m["a"][0] + incr(Xn))
    return prob, incr, eb, m


# ---------------------------------------------------------------- MU (5 x 5 CV)
def mu_frame():
    from prism.analyses import clinician_baseline as CB
    from prism.analyses import detection as D
    from prism.analyses import system as S
    d, X = S.mu_designs("grade4")
    T = D.context("grade4", "primary")[1]["T"]
    win = S.mu_situation(d)[0]
    R = CB.mu_reader_design(d, X)
    return d, X, T, R, win


def mu_job(job):
    from threadpoolctl import threadpool_limits
    from prism.analyses import detection as D
    from prism.audit import conformal as cf
    from prism.experiments import c3_radiomics as c3
    r, k = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, X, T, R, win = mu_frame()
    y, pid = d.label_120.to_numpy(), d.patient_id.to_numpy()
    f = D.fold_ids(d, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    o = {"r": r, "k": k, "te": te}
    cur = {"images": X["images"], "combined": X["combined"], "baseline": R, "reduced_combined": T}
    for p, Xa in cur.items():
        o[p] = c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr, te, seed=r)
    sA, pA, mA = fit_A(X["images"], d, tr, win)
    o["A"], o["A_prob"], o["A_C"] = sA(X["images"].iloc[te]), pA(X["images"].iloc[te], win[te]), mA["C"]
    o["A_win"] = dict(zip(mA["levels"].tolist(), mA["a"].tolist()))
    pB, iB, eb, mB = fit_B(X["combined"], R, d, tr, r)
    o["B"], o["B_incr"], o["B_C"], o["B_b0"] = pB(X["combined"].iloc[te], R.iloc[te]), iB(X["combined"].iloc[te]), \
        mB["C"], float(mB["a"][0])
    o["offset_check"] = float(np.abs(_sig(eb(R.iloc[te])) - o["baseline"]).max())
    # exploratory conformal: 70 / 30 patient split inside the training fold (seed 10 r + k), as the system
    proper, cal = cf.patient_split(pid[tr], 0.3, seed=10 * r + k)
    cr = tr[cal][~np.isnan(y[tr[cal]])]
    pBc = fit_B(X["combined"], R, d, tr[proper], r)[0]
    pc_cur = c3.fit_predict(c3.BASELINES[0], d, X["combined"], {}, None, tr[proper], np.concatenate([cr, te]), seed=r)
    for name, pcal, pte in (("B", pBc(X["combined"].iloc[cr], R.iloc[cr]), pBc(X["combined"].iloc[te], R.iloc[te])),
                            ("combined", pc_cur[:len(cr)], pc_cur[len(cr):])):
        q = cf.threshold(cf.scores(pcal, y[cr].astype(int)), pid[cr], ALPHA)
        o[f"set0_{name}"], o[f"set1_{name}"] = cf.prediction_sets(pte, q)
    return o


def run_mu(workers):
    d, X, T, R, win = mu_frame()
    n = len(d)
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(mu_job, [(r, k) for r in range(5) for k in range(5)]))
    keys = ("images", "combined", "baseline", "reduced_combined", "A", "A_prob", "B", "B_incr",
            "set0_B", "set1_B", "set0_combined", "set1_combined")
    P = {p: np.full((5, n), np.nan) for p in keys}
    for o in res:
        for p in keys:
            P[p][o["r"], o["te"]] = o[p]
    ev = (d.label_120.notna() & d.intended_use).to_numpy()
    fits = [{"r": o["r"], "k": o["k"], "A_C": o["A_C"], "B_C": o["B_C"], "B_b0": o["B_b0"],
             "offset_check": o["offset_check"], **{f"A_win_{w}": v for w, v in o["A_win"].items()}} for o in res]
    assert max(f["offset_check"] for f in fits) < 1e-6, "baseline offset does not equal the E4 baseline"
    return {"y": d.label_120.to_numpy()[ev], "pid": d.patient_id.to_numpy()[ev], "ctx": d.phase.astype(str).to_numpy()[ev],
            "S": {p: v[:, ev] for p, v in P.items()}, "fits": fits, "n_eval": int(ev.sum())}


# ---------------------------------------------------------------- locked (LUMIERE, UCSF)
def run_locked(skip_ucsf):
    from prism.analyses import detection as D
    from prism.analyses import system as S
    from prism.analyses import ucsf_external as UX
    from prism.audit import conformal as cf
    warnings.filterwarnings("ignore")
    d, A4 = UX.mu_detection("grade4")
    T = D.context("grade4", "primary")[1]["T"]
    win = S.mu_situation(d)[0]
    rows = np.arange(len(d))
    y4, p4 = d.label_120.to_numpy(), d.patient_id.to_numpy()
    timg = [c for c in T.columns if c not in D.T_BASE + T_EXTRA]
    Rl = T[BASE_LOCKED]
    f_img, f_vol3, f_comb, f_base = (S._fit(T[timg], d, rows), S._fit(T[S.VOL3], d, rows), S._fit(T, d, rows),
                                     S._fit(Rl, d, rows))
    sA_img, pA_img, mA_img = fit_A(T[timg], d, rows, win)
    sA_v3, _, mA_v3 = fit_A(T[S.VOL3], d, rows, win)
    sA_ip, _, mA_ip = fit_A(A4["A-Ipure"], d, rows, win)
    pB, iB, eb, mB = fit_B(T, Rl, d, rows, 0)
    # conformal (exploratory): MU split seed 0, as system.locked_models
    proper, cal = cf.patient_split(p4, 0.3, seed=0)
    cr = rows[cal][~np.isnan(y4[cal])]
    pBc = fit_B(T, Rl, d, rows[proper], 0)[0]
    f_comb_c = S._fit(T, d, rows[proper])
    qB = cf.threshold(cf.scores(pBc(T.iloc[cr], Rl.iloc[cr]), y4[cr].astype(int)), p4[cr], ALPHA)
    qC = cf.threshold(cf.scores(f_comb_c(T.iloc[cr]), y4[cr].astype(int)), p4[cr], ALPHA)
    fits = {"A_T_img": mA_img, "A_vol3": mA_v3, "A_Ipure": mA_ip, "B_T": mB}
    out = {"fits": {k: {"C": v["C"], "a": np.round(v["a"], 4).tolist(),
                        "levels": None if v["levels"] is None else v["levels"].tolist()} for k, v in fits.items()}}

    def pack(Xc, Rn, img_cur, img_A, y, ctx, pid):
        s = {"images": img_cur, "combined": f_comb(Xc), "baseline": f_base(Rn), "A": img_A, "B": pB(Xc, Rn),
             "B_incr": iB(Xc)}
        for name, pc, q in (("B", pBc(Xc, Rn), qB), ("combined", f_comb_c(Xc), qC)):
            s[f"set0_{name}"], s[f"set1_{name}"] = cf.prediction_sets(pc, q)
        return {"y": y, "pid": pid, "ctx": ctx, "S": {k: np.asarray(v, float)[None, :] for k, v in s.items()}}

    L, LX, _ = D.lumiere_detection()
    nop = L.prev_scan_id.eq("").to_numpy()
    out["lumiere"] = pack(LX, LX[BASE_LOCKED], np.where(nop, f_vol3(LX[S.VOL3]), f_img(LX[timg])),
                          np.where(nop, sA_v3(LX[S.VOL3]), sA_img(LX[timg])), L.label_det.to_numpy(float),
                          np.where(L.early_post_rt.eq(1), "within_3m", "other"), L.patient_id.to_numpy())
    if not skip_ucsf:
        u = UX.ucsf_frame()
        A = UX.ucsf_designs(u, A4)
        keep = (u.timepoint.eq(2) & u.grade4).to_numpy()
        uk = u[keep].reset_index(drop=True)
        Au = {k: v[keep].reset_index(drop=True) for k, v in A.items()}
        yu = np.where(uk.pos_s2_pm30.eq(1), 1.0, np.where(uk.primary_neg, 0.0, np.nan))
        e = ~np.isnan(yu)
        c = pack(Au["A-T"], Au["A-T"][BASE_LOCKED], S._fit(A4["A-Ipure"], d, rows)(Au["A-Ipure"]),
                 sA_ip(Au["A-Ipure"]), yu, uk.rt_phase.astype(str).to_numpy(), uk.subject_id.to_numpy())
        out["ucsf"] = {"y": yu[e].astype(int), "pid": c["pid"][e], "ctx": c["ctx"][e],
                       "S": {k: v[:, e] for k, v in c["S"].items()}}
    return out


# ---------------------------------------------------------------- statistics
RANKED = ("images", "A", "combined", "B", "baseline", "reduced_combined", "B_incr")
DIFFS = (("A", "images"), ("B", "combined"), ("B", "baseline"), ("combined", "baseline"))


def stats(cohort, c, n_boot):
    from prism.analyses.methods import boot, ci, m1_stats
    y, pid, ctx = c["y"], c["pid"], c["ctx"]
    sc = {k: v for k, v in c["S"].items() if k in RANKED}
    est = m1_stats(y, sc, ctx)
    B = boot(y, sc, ctx, pid, n_boot, seed=SEED)
    rows = []
    n = {"n_scans": len(y), "n_pos": int((y == 1).sum()), "n_patients": len(np.unique(pid))}
    for k in sc:
        for j, s in enumerate(("auc", "w", "a_within", "a_across")):
            lo, hi = ci([b[k][j] for b in B])
            rows.append({"cohort": cohort, "kind": "score", "score": k, "stat": s, "est": est[k][j], "lo": lo,
                         "hi": hi, **n})
    for a, b_ in DIFFS:
        for j, s in ((0, "auc"), (2, "a_within"), (3, "a_across")):
            lo, hi = ci([b[a][j] - b[b_][j] for b in B])
            rows.append({"cohort": cohort, "kind": "paired_diff", "score": f"{a}-{b_}", "stat": s,
                         "est": est[a][j] - est[b_][j], "lo": lo, "hi": hi, **n})
    return pd.DataFrame(rows)


def check_reference(cohort, c):
    from prism.analyses.methods import m1_stats
    est = m1_stats(c["y"], {k: c["S"][k] for k in REF[cohort] if k in c["S"]}, c["ctx"])
    rows = []
    for k, ref in REF[cohort].items():
        rows.append({"cohort": cohort, "score": k, "stat": "auc", "reference": ref, "reproduced": float(est[k][0]),
                     "ok": abs(est[k][0] - ref) < 1e-3})
    for (co, k), (aw, ab) in REF_SPLIT.items():
        if co == cohort:
            for s, j, ref in (("a_within", 2, aw), ("a_across", 3, ab)):
                rows.append({"cohort": cohort, "score": k, "stat": s, "reference": ref,
                             "reproduced": float(est[k][j]), "ok": abs(est[k][j] - ref) < 0.01})
    return rows


def calibration(cohort, c):
    from prism.analyses.ucsf_external import calibration as cal
    rows = []
    for k in ("A_prob", "B", "combined", "baseline", "images"):
        if k not in c["S"]:
            continue
        v = np.array([cal(c["y"], p) for p in c["S"][k]])
        rows.append({"cohort": cohort, "score": k, "slope": v[:, 0].mean(), "o_e": v[:, 1].mean(),
                     "intercept": v[:, 2].mean(), "repeats": len(v)})
    return rows


def coverage(cohort, c):
    rows = []
    y = c["y"]
    for k in ("B", "combined"):
        h0, h1 = c["S"][f"set0_{k}"].astype(bool), c["S"][f"set1_{k}"].astype(bool)
        cov = np.where(y == 1, h1, h0)
        rows.append({"cohort": cohort, "model": k, "alpha": ALPHA, "coverage": float(cov.mean()),
                     "coverage_progression": float(cov[:, y == 1].mean()),
                     "coverage_no_progression": float(cov[:, y == 0].mean()),
                     "both": float((h0 & h1).mean()), "empty": float((~h0 & ~h1).mean())})
    return rows


def increment_summary(cohort, c):
    v = c["S"]["B_incr"]
    return {"cohort": cohort, "mean": float(np.mean(v)), "sd": float(np.mean(np.std(v, axis=1))),
            "q05": float(np.mean(np.percentile(v, 5, axis=1))), "q95": float(np.mean(np.percentile(v, 95, axis=1)))}


def main(argv=None):
    from prism.config import SKIP_UCSF
    ap = argparse.ArgumentParser(prog="prism.analyses.stratified_offset", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--reference-only", action="store_true", help="reproduce the current models' AUCs and stop")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    toy = toy_checks()
    (OUT / "toy_checks.json").write_text(json.dumps(toy, indent=1))
    cohorts = {"mu": run_mu(a.workers)}
    locked = run_locked(SKIP_UCSF)
    cohorts["lumiere"] = locked["lumiere"]
    if "ucsf" in locked:
        cohorts["ucsf"] = locked["ucsf"]
    ref = sum((check_reference(k, c) for k, c in cohorts.items()), [])
    pd.DataFrame(ref).to_csv(OUT / "s2_reference_check.csv", index=False)
    bad = [r for r in ref if not r["ok"]]
    print(pd.DataFrame(ref).to_string(index=False))
    assert not bad, f"reference not reproduced: {bad}"
    info = {"seed": SEED, "n_boot": a.n_boot, "toy_checks": toy, "mu_fits": cohorts["mu"]["fits"],
            "locked_fits": locked["fits"], "skip_ucsf": bool(SKIP_UCSF)}
    if a.reference_only:
        (OUT / "run_info_reference.json").write_text(json.dumps(info, indent=1, default=str))
        print(f"reference reproduced in {time.time() - t0:.0f}s")
        return
    t = pd.concat([stats(k, c, a.n_boot) for k, c in cohorts.items()])
    t.to_csv(OUT / "s2_auc.csv", index=False)
    pd.DataFrame(sum((calibration(k, c) for k, c in cohorts.items()), [])).to_csv(OUT / "s2_calibration.csv",
                                                                                 index=False)
    pd.DataFrame(sum((coverage(k, c) for k, c in cohorts.items()), [])).to_csv(OUT / "s2_conformal.csv", index=False)
    pd.DataFrame([increment_summary(k, c) for k, c in cohorts.items()]).to_csv(OUT / "s2_increment.csv", index=False)
    np.savez(OUT / "scores.npz", **{f"{k}_{s}": v for k, c in cohorts.items() for s, v in c["S"].items()},
             **{f"{k}_{f}": np.asarray(c[f]) for k, c in cohorts.items() for f in ("y", "pid", "ctx")})
    info["seconds"] = round(time.time() - t0)
    (OUT / "run_info.json").write_text(json.dumps(info, indent=1, default=str))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
