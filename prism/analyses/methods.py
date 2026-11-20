"""M1 AUC split by context and M2 group-conditional (Mondrian) conformal sets with a fallback
(plan: docs/results/METHODS_PLAN.md, commit 1363773, written before the run; results: docs/results/METHODS_RESULTS.md).

M1. For a score, the positive-negative pairs split into pairs within one context stratum (W) and across strata (B);
AUC = w A_W + (1 - w) A_B exactly, w = |W| / |P x N|. Context: MU time after radiotherapy from the dates (d.phase);
LUMIERE the rater's within-3-months flag. Context-only score: the stratum's progression rate (MU: training folds;
LUMIERE: MU's rate of the matching stratum).

M2. Groups = time after radiotherapy x enhancement state (the card's situation). Each scan is calibrated in the
finest level with >= 10 calibration patients: 1 its group, 2 its enhancement state, 3 all (the registered marginal
set). Unknown time externally starts at level 2. Calibration as registered (MU 70 / 30 patient split inside each outer
training fold, refitted on the 70%; external MU split seed 0).

Since 2026-11-19 (docs/results/ADOPT_AB.md) the imaging score is A's within-window score and the combined score is
B's probability, and the conformal models are A's probability and B, all from prism.analyses.system (mu_job and the
locked models of lumiere_cohort / ucsf_cohort), so M1 and M2 use the system's scores and sets.

    PRISM_SKIP_UCSF=1 PYTHONPATH=. .venv/bin/python -m prism.analyses.methods [--workers 20] [--n-boot 2000]
    -> outputs/results/analyses/methods/   (aggregate CSVs only)
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
from prism.audit import conformal as cf
from prism.config import RESULTS, SKIP_UCSF

OUT = RESULTS / "analyses" / "methods"
SEED = 20261115
ALPHA = 0.2
MIN_PAT = 10
PW = S.PW
WITHIN_REF = {"timeline": 0.64, "images": 0.68}      # MU within-phase AUCs (clinical-history; A: S2 Q1, 0.68)
MU_REF = {"timeline": 0.822, "images": 0.6688, "combined": 0.8137}   # system.EXPECTED (ADOPT_AB.md)
UCSF_REF = {"timeline": 0.561, "images": 0.7690, "combined": 0.8681}


# ---------------------------------------------------------------- M1 statistics
def split_auc(y, s, c):
    """(AUC, w, A_W, A_B) with ties 1/2, on the scans with a score (missing scores are dropped, not ranked)."""
    k = ~np.isnan(s)
    y, s, c = y[k], s[k], c[k]
    pos, neg = y == 1, y == 0
    a, b = s[pos][:, None], s[neg][None, :]
    M = (a > b) + 0.5 * (a == b)
    same = c[pos][:, None] == c[neg][None, :]
    auc, w = M.mean(), same.mean()
    aw = M[same].mean() if same.any() else np.nan
    ab = M[~same].mean() if (~same).any() else np.nan
    if same.any() and (~same).any():
        assert abs(w * aw + (1 - w) * ab - auc) < 1e-12
    return np.array([auc, w, aw, ab])


def m1_stats(y, scores: dict, c):
    """scores: {name: (R, n)}; mean over repeats of split_auc."""
    return {k: np.nanmean([split_auc(y, v[r], c) for r in range(v.shape[0])], axis=0) for k, v in scores.items()}


def boot(y, scores, c, pid, n_boot, seed=SEED):
    rng = np.random.default_rng(seed)
    u = np.unique(pid)
    rows = {p: np.where(pid == p)[0] for p in u}
    out = []
    for _ in range(n_boot):
        idx = np.concatenate([rows[p] for p in rng.choice(u, len(u))])
        out.append(m1_stats(y[idx], {k: v[:, idx] for k, v in scores.items()}, c[idx]))
    return out


def ci(v):
    v = np.asarray(v, float)
    v = v[~np.isnan(v)]
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if len(v) else (np.nan, np.nan)


def m1_table(cohort, y, scores, c, pid, n_boot):
    est = m1_stats(y, scores, c)
    B = boot(y, scores, c, pid, n_boot)
    rows = []
    for k in scores:
        for j, stat in enumerate(("auc", "w", "a_within", "a_across")):
            lo, hi = ci([b[k][j] for b in B])
            rows.append({"cohort": cohort, "score": k, "stat": stat, "est": est[k][j], "lo": lo, "hi": hi})
        lo, hi = ci([b[k][3] - b[k][2] for b in B])
        rows.append({"cohort": cohort, "score": k, "stat": "across_minus_within", "est": est[k][3] - est[k][2],
                     "lo": lo, "hi": hi})
    for a, b_ in (("combined", "timeline"), ("combined", "images")):
        for j, stat in ((0, "auc"), (2, "a_within"), (3, "a_across")):
            lo, hi = ci([b[a][j] - b[b_][j] for b in B])
            rows.append({"cohort": cohort, "score": f"{a}-{b_}", "stat": f"delta_{stat}",
                         "est": est[a][j] - est[b_][j], "lo": lo, "hi": hi})
    n = {"cohort": cohort, "scans": int(len(y)), "positives": int((y == 1).sum()), "negatives": int((y == 0).sum()),
         "patients": int(len(np.unique(pid))), "strata": {str(s): [int(((c == s) & (y == 1)).sum()),
                                                                     int(((c == s) & (y == 0)).sum())]
                                                          for s in np.unique(c)}}
    return pd.DataFrame(rows), n


# ---------------------------------------------------------------- MU jobs (scores, calibration rows)
def mu_job(job):
    """The system's fold job (system.mu_job): ranking scores p_, conformal-model probabilities on the calibration
    rows (pccal_) and the test rows (pc_)."""
    r, k = job
    return S.mu_job(("grade4", r, k))


# ---------------------------------------------------------------- M2
def levels(g1_cal, g2_cal, pid_cal, start2=False):
    """Function scan (g1, g2) -> (level, mask over calibration rows)."""
    def n_pat(m):
        return len(np.unique(pid_cal[m]))

    def pick(g1, g2):
        if not start2:
            m = g1_cal == g1
            if n_pat(m) >= MIN_PAT:
                return 1, m
        m = g2_cal == g2
        if n_pat(m) >= MIN_PAT:
            return 2, m
        return 3, np.ones(len(g1_cal), bool)
    return pick


def mondrian_sets(p_cal, y_cal, pid_cal, g1_cal, g2_cal, p_te, g1_te, g2_te, start2):
    s = cf.scores(p_cal, y_cal.astype(int))
    pick = levels(g1_cal, g2_cal, pid_cal, start2)
    cache, lev, h0, h1 = {}, [], [], []
    for p, a, b in zip(p_te, g1_te, g2_te):
        key = (a, b)
        if key not in cache:
            L, m = pick(a, b)
            cache[key] = (L, cf.threshold(s[m], pid_cal[m], ALPHA))
        L, q = cache[key]
        lev.append(L)
        h0.append(p <= q)
        h1.append(1 - p <= q)
    qm = cf.threshold(s, pid_cal, ALPHA)
    return np.array(lev), np.array(h0), np.array(h1), p_te <= qm, 1 - p_te <= qm


def m2_summary(cohort, model, y, pid, g1, lev, sets_m, sets_r, n_boot):
    """y (n,), lev (R, n), sets (R, n) x2 for Mondrian and registered marginal."""
    R = lev.shape[0]
    cov_m = np.where(y == 1, sets_m[1], sets_m[0])
    cov_r = np.where(y == 1, sets_r[1], sets_r[0])
    rows = []
    rng = np.random.default_rng(SEED)
    u = np.unique(pid)
    byp = {p: np.where(pid == p)[0] for p in u}
    idxs = [np.concatenate([byp[p] for p in rng.choice(u, len(u))]) for _ in range(n_boot)]

    def add(name, mask, kind, cov):
        if mask.sum() == 0:
            return
        est = float(cov[:, mask].mean())
        bs = [cov[:, i][:, mask[i]].mean() if mask[i].any() else np.nan for i in idxs]
        lo, hi = ci(bs)
        rows.append({"cohort": cohort, "model": model, "set": kind, "group": name, "n_scans": int(mask.sum()),
                     "n_progression": int((mask & (y == 1)).sum()), "coverage": est, "lo": lo, "hi": hi})

    for kind, cov in (("mondrian", cov_m), ("registered", cov_r)):
        add("all", np.ones(len(y), bool), kind, cov)
        for cls, nm in ((1, "progression"), (0, "no progression")):
            add(nm, y == cls, kind, cov)
        for g in np.unique(g1):
            add(f"group {g}", g1 == g, kind, cov)
    extra = {"cohort": cohort, "model": model}
    for L in (1, 2, 3):
        extra[f"share_level{L}"] = float((lev == L).mean())
    for kind, (h0, h1) in (("mondrian", sets_m), ("registered", sets_r)):
        extra[f"{kind}_both"] = float((h0 & h1).mean())
        extra[f"{kind}_empty"] = float((~h0 & ~h1).mean())
        gcov = [cov_m if kind == "mondrian" else cov_r][0]
        big = [g for g in np.unique(g1) if (g1 == g).sum() >= 10]
        extra[f"{kind}_worst_gap"] = float(1 - ALPHA - min(gcov[:, g1 == g].mean() for g in big)) if big else np.nan
    return rows, extra


# ---------------------------------------------------------------- cohorts
def run_mu(workers, n_boot):
    d, X = S.mu_designs("grade4")
    n = len(d)
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(mu_job, [(r, k) for r in range(5) for k in range(5)]))
    y = d.label_120.to_numpy()
    pid = d.patient_id.to_numpy()
    ev = (d.label_120.notna() & d.intended_use).to_numpy()
    phase = d.phase.astype(str).to_numpy()
    cphase, enh = S.mu_situation(d)
    g1 = np.array([f"{a}|{b}" for a, b in zip(cphase, enh)])
    P = {p: np.full((5, n), np.nan) for p in PW}
    ctx = np.full((5, n), np.nan)
    lev = {p: np.zeros((5, n), int) for p in PW}
    sm = {p: [np.zeros((5, n), bool), np.zeros((5, n), bool)] for p in PW}
    sr = {p: [np.zeros((5, n), bool), np.zeros((5, n), bool)] for p in PW}
    for j in res:
        r, te, cr, tl = j["r"], j["te"], j["cr"], j["tr_lab"]
        rate = pd.Series(y[tl]).groupby(phase[tl]).mean()
        ctx[r, te] = pd.Series(phase[te]).map(rate).fillna(float(np.mean(y[tl]))).to_numpy()
        for p in PW:
            P[p][r, te] = j[f"p_{p}"]
            L, a0, a1, b0, b1 = mondrian_sets(j[f"pccal_{p}"], y[cr], pid[cr], g1[cr], enh[cr], j[f"pc_{p}"],
                                              g1[te], enh[te], start2=False)
            lev[p][r, te], sm[p][0][r, te], sm[p][1][r, te], sr[p][0][r, te], sr[p][1][r, te] = L, a0, a1, b0, b1
    # reproduction: displayed AUCs equal the system's
    from sklearn.metrics import roc_auc_score
    chk = {p: float(np.mean([roc_auc_score(y[ev], P[p][r, ev]) for r in range(5)])) for p in PW}
    for p, ref in MU_REF.items():
        assert abs(chk[p] - ref) < 1e-3, (p, chk[p])
    et = X["images"]["log_et_cc"].to_numpy(float) if "log_et_cc" in X["images"] else None
    scores = {p: P[p][:, ev] for p in PW}
    scores["context_only"] = ctx[:, ev]
    if et is not None:
        scores["enhancing_volume"] = np.broadcast_to(et[ev], (5, ev.sum())).copy()
    t1, n1 = m1_table("mu", y[ev], scores, phase[ev], pid[ev], n_boot)
    for p, ref in WITHIN_REF.items():
        v = float(t1[(t1.score == p) & (t1.stat == "a_within")].est.iloc[0])
        assert abs(v - ref) < 0.01, (p, v, ref)
    rows, extras = [], []
    for p in PW:
        rr, ex_ = m2_summary("mu", p, y[ev], pid[ev], g1[ev], lev[p][:, ev], [a[:, ev] for a in sm[p]],
                             [a[:, ev] for a in sr[p]], n_boot)
        rows += rr
        extras.append(ex_)
    return t1, n1, rows, extras, chk


def run_lumiere(n_boot):
    c = S.lumiere_cohort()
    L = c["d"]
    y, pid = c["y"], c["patient_id"]
    flag = L.early_post_rt.to_numpy(float)
    ctxlab = np.where(flag == 1, "within_3m", "other")
    # MU context rates (all MU grade 4 labelled training rows), and MU calibration for M2 (registered split seed 0)
    dm, X, *_ = D.context("grade4", "primary")
    ym, pm = dm.label_120.to_numpy(), dm.patient_id.to_numpy()
    lab = ~np.isnan(ym)
    ph = dm.phase.astype(str).to_numpy()
    r_early = float(ym[lab & (ph == "early_post_rt")].mean())
    r_other = float(ym[lab & (ph != "early_post_rt")].mean())
    scores = {p: c["S"][f"p_{p}"] for p in PW}
    scores["context_only"] = np.where(flag == 1, r_early, r_other)[None, :]
    scores["enhancing_volume"] = np.log(np.asarray(L.et, float) + 1e-3)[None, :] if "et" in L else None
    if scores["enhancing_volume"] is None:
        del scores["enhancing_volume"]
    t1, n1 = m1_table("lumiere", y, scores, ctxlab, pid, n_boot)
    # M2: MU calibration rows and their groups
    dmu, _ = S.mu_designs("grade4")
    assert len(dmu) == len(dm) and (dmu.scan_id.to_numpy() == dm.scan_id.to_numpy()).all()
    cph, enh_mu = S.mu_situation(dmu)
    g1_mu = np.array([f"{a}|{b}" for a, b in zip(cph, enh_mu)])
    rows_ = np.arange(len(dm))
    proper, cal = cf.patient_split(pm, 0.3, seed=0)
    cr = rows_[cal][~np.isnan(ym[cal])]
    Xmu, Xl, wl = c["Xmu"], c["Xext"], c["wext"]   # the system's locked designs and windows
    nop = L.prev_scan_id.eq("").to_numpy()
    enh = c["enh"]
    n = len(L)
    rows, extras = [], []
    for p in PW:
        parts = [(p, ~nop), ("images_scan", nop)] if p == "images" else [(p, np.ones(n, bool))]
        lev = np.zeros((1, n), int)
        sm, sr = [np.zeros((1, n), bool) for _ in range(2)], [np.zeros((1, n), bool) for _ in range(2)]
        for name, m in parts:
            conf = c["models"][name]["conf"]   # the system's conformal model (70% proper split, seed 0)
            pcal = conf(Xmu[name].iloc[cr], cph[cr])
            pte = conf(Xl[name], wl)
            Lv, a0, a1, b0, b1 = mondrian_sets(pcal, ym[cr], pm[cr], g1_mu[cr], enh_mu[cr], pte,
                                               np.array(["unknown|" + e for e in enh]), enh, start2=True)
            lev[0, m], sm[0][0, m], sm[1][0, m], sr[0][0, m], sr[1][0, m] = Lv[m], a0[m], a1[m], b0[m], b1[m]
        # the registered marginal sets must equal the system's
        assert (sr[0][0] == c["sets"][("std", p, 0.2, 0)][0]).all() and (sr[1][0] == c["sets"][("std", p, 0.2, 1)][0]).all(), p
        g1 = np.array([f"unknown|{e}" for e in enh])
        rr, ex_ = m2_summary("lumiere", p, y, pid, g1, lev, sm, sr, n_boot)
        rows += rr
        extras.append(ex_)
    return t1, n1, rows, extras


def run_ucsf(n_boot):
    """UCSF-ALPTDG, grade 4 scan 2 (locked MU models). Context rt_phase, as the plan fixes; the context-only score takes
    MU's rate for the matching stratum and MU's pooled rate otherwise (no_rt, rt_date_unknown). M2 groups as the card's
    situation; scans whose time after radiotherapy is unknown fall to level 2, as at LUMIERE."""
    from prism.analyses import ucsf_external as UX
    c = S.ucsf_cohort()
    ev = ~np.isnan(c["y"])
    y, pid = c["y"][ev].astype(int), c["patient_id"][ev]
    ph = c["comp_phase"].astype(str)[ev]
    d4, A4 = UX.mu_detection("grade4")
    y4, p4 = d4.label_120.to_numpy(), d4.patient_id.to_numpy()
    lab = ~np.isnan(y4)
    ph4 = d4.phase.astype(str).to_numpy()
    rate = pd.Series(y4[lab]).groupby(ph4[lab]).mean()
    ctx = pd.Series(ph).map(rate).fillna(float(y4[lab].mean())).to_numpy(float)
    im = pd.read_csv(S.OUTPUTS / "data" / "ucsf" / "imaging_features.csv").set_index("scan_id")
    et = im.et_cc.reindex(c["scan_id"][ev]).to_numpy(float)
    scores = {p: c["S"][f"p_{p}"][:, ev] for p in PW}
    scores["context_only"] = ctx[None, :]
    scores["enhancing_volume"] = np.log(et + 1e-3)[None, :]
    from sklearn.metrics import roc_auc_score
    chk = {p: float(roc_auc_score(y, scores[p][0])) for p in PW}
    for p, ref in UCSF_REF.items():
        assert abs(chk[p] - ref) < 1e-3, (p, chk[p])
    t1, n1 = m1_table("ucsf", y, scores, ph, pid, n_boot)
    # M2: MU calibration rows (registered split seed 0) and their groups
    names = {"timeline": "A-Tbase", "images": "A-Ipure", "combined": "A-T"}
    u = UX.ucsf_frame()
    keep = (u.timepoint.eq(2) & u.grade4).to_numpy()
    A = UX.ucsf_designs(u, A4)
    rows_ = np.arange(len(d4))
    proper, cal = cf.patient_split(p4, 0.3, seed=0)
    cr = rows_[cal][~np.isnan(y4[cal])]
    cph, enh_mu = S.mu_situation(d4)
    g1_mu = np.array([f"{a}|{b}" for a, b in zip(cph, enh_mu)])
    g1 = np.array([f"{a}|{b}" for a, b in zip(c["card_phase"], c["enh"])])
    rows, extras = [], []
    for p in PW:
        conf = c["models"][p]["conf"]   # the system's conformal model (70% proper split, seed 0)
        pcal = conf(c["Xmu"][p].iloc[cr], cph[cr])
        pte = conf(c["Xext"][p], c["wext"])
        Lv, a0, a1, b0, b1 = mondrian_sets(pcal, y4[cr], p4[cr], g1_mu[cr], enh_mu[cr], pte, g1, c["enh"],
                                           start2=False)
        assert (b0 == c["sets"][("std", p, 0.2, 0)][0]).all() and (b1 == c["sets"][("std", p, 0.2, 1)][0]).all(), p
        rr, ex_ = m2_summary("ucsf", p, y, pid, g1[ev], Lv[None, ev], [a0[None, ev], a1[None, ev]],
                             [b0[None, ev], b1[None, ev]], n_boot)
        rows += rr
        extras.append(ex_)
    return t1, n1, rows, extras, chk


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    t_mu, n_mu, r_mu, e_mu, chk = run_mu(a.workers, a.n_boot)
    t_l, n_l, r_l, e_l = run_lumiere(a.n_boot)
    t_u, n_u, r_u, e_u, chk_u = ([], None, [], [], None) if SKIP_UCSF else run_ucsf(a.n_boot)
    pd.concat([t_mu, t_l, *([] if SKIP_UCSF else [t_u])]).to_csv(OUT / "m1_auc_split.csv", index=False)
    pd.DataFrame(r_mu + r_l + r_u).to_csv(OUT / "m2_coverage.csv", index=False)
    pd.DataFrame(e_mu + e_l + e_u).to_csv(OUT / "m2_levels.csv", index=False)
    (OUT / "run_info.json").write_text(json.dumps({"n_boot": a.n_boot, "seed": SEED, "min_patients": MIN_PAT,
                                                   "alpha": ALPHA, "mu_check_auc": chk, "ucsf_check_auc": chk_u,
                                                   "counts": [n_mu, n_l, n_u],
                                                   "seconds": round(time.time() - t0)}, indent=1))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
