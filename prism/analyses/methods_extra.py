"""Exploratory checks asked for by the internal referee of the methods rewrite (2026-11-15; not in METHODS_PLAN.md).

E1. Context-only score with stratum rates computed once on all labelled MU scans (not per fold), and the AUC within
    each time window separately, for every MU score (M1 pools them by pair counts).
E2. Baselines for the group-conditional sets (combined model, MU): (a) marginal sets at the alpha whose share of
    two-outcome sets matches the group-conditional sets (size-matched), (b) outcome-conditional sets (Mondrian by
    outcome). Worst-group coverage over groups with at least 9 evaluation scans (the figure's threshold) and 10.

    PRISM_SKIP_UCSF=1 PYTHONPATH=. .venv/bin/python -m prism.analyses.methods_extra
    -> outputs/results/analyses/methods/extra_*.csv   (aggregate only)
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from prism.analyses import methods as M
from prism.analyses import system as S
from prism.audit import conformal as cf

OUT = M.OUT


def auc(y, s):
    return M.split_auc(y, s, np.zeros(len(y)))[0]


def main():
    d, X = S.mu_designs("grade4")
    n = len(d)
    with ProcessPoolExecutor(25) as ex:
        res = list(ex.map(M.mu_job, [(r, k) for r in range(5) for k in range(5)]))
    y, pid = d.label_120.to_numpy(), d.patient_id.to_numpy()
    ev = (d.label_120.notna() & d.intended_use).to_numpy()
    phase = d.phase.astype(str).to_numpy()
    cph, enh = S.mu_situation(d)
    g1 = np.array([f"{a}|{b}" for a, b in zip(cph, enh)])
    P = {p: np.full((5, n), np.nan) for p in S.PW}
    for j in res:
        for p in S.PW:
            P[p][j["r"], j["te"]] = j[f"p_{p}"]
    # E1
    lab = ~np.isnan(y)
    rate = pd.Series(y[lab]).groupby(phase[lab]).mean()
    ctx = pd.Series(phase).map(rate).to_numpy(float)
    ye, ce = y[ev], phase[ev]
    rows = [{"score": "context_only_once", "stat": k, "est": v} for k, v in
            zip(("auc", "w", "a_within", "a_across"), M.split_auc(ye, ctx[ev], ce))]
    for p in S.PW:
        for st in np.unique(ce):
            m = ce == st
            if (ye[m] == 1).any() and (ye[m] == 0).any():
                rows.append({"score": p, "stat": f"auc_in_{st}",
                             "est": float(np.mean([auc(ye[m], P[p][r, ev][m]) for r in range(5)])),
                             "n_pos": int((ye[m] == 1).sum()), "n_neg": int((ye[m] == 0).sum())})
    pd.DataFrame(rows).to_csv(OUT / "extra_m1.csv", index=False)
    # E2: combined model
    p = "combined"
    out = []

    def cover(h0, h1):
        return np.where(y == 1, h1, h0)

    def summary(name, H0, H1):
        cov = cover(H0, H1)[:, ev]
        r = {"set": name, "coverage": float(cov.mean()), "both": float((H0 & H1)[:, ev].mean()),
             "empty": float((~H0 & ~H1)[:, ev].mean()),
             "cov_progression": float(cov[:, ye == 1].mean()), "cov_no_progression": float(cov[:, ye == 0].mean())}
        ge = g1[ev]
        for thr in (9, 10):
            big = [g for g in np.unique(ge) if (ge == g).sum() >= thr]
            gc = {g: float(cov[:, ge == g].mean()) for g in big}
            w = min(gc, key=gc.get)
            r[f"worst_group_{thr}"], r[f"worst_cov_{thr}"] = w, gc[w]
        for g in np.unique(ge):
            if (ge == g).sum() >= 9:
                r[f"cov|{g}"] = float(cov[:, ge == g].mean())
        out.append(r)

    def sets_for(alpha_fn):
        H0, H1 = np.zeros((5, n), bool), np.zeros((5, n), bool)
        for j in res:
            r, te, cr = j["r"], j["te"], j["cr"]
            pc, pcal = j[f"pc_{p}"], j[f"pccal_{p}"]
            h0, h1 = alpha_fn(pcal, y[cr].astype(int), pid[cr], pc, cr, te)
            H0[r, te], H1[r, te] = h0, h1
        return H0, H1

    def marginal(a):
        def f(pcal, yc, pc_id, pte, cr, te):
            q = cf.threshold(cf.scores(pcal, yc), pc_id, a)
            return pte <= q, 1 - pte <= q
        return f

    def outcome_cond(a):
        def f(pcal, yc, pc_id, pte, cr, te):
            s = cf.scores(pcal, yc)
            q0 = cf.threshold(s[yc == 0], pc_id[yc == 0], a)
            q1 = cf.threshold(s[yc == 1], pc_id[yc == 1], a)
            return pte <= q0, 1 - pte <= q1
        return f

    def mondrian(pcal, yc, pc_id, pte, cr, te):
        _, h0, h1, _, _ = M.mondrian_sets(pcal, yc, pc_id, g1[cr], enh[cr], pte, g1[te], enh[te], start2=False)
        return h0, h1

    Hm = sets_for(mondrian)
    summary("group-conditional", *Hm)
    target = float((Hm[0] & Hm[1])[:, ev].mean())
    summary("marginal alpha 0.2", *sets_for(marginal(0.2)))
    best = None
    for a in np.round(np.arange(0.10, 0.205, 0.005), 3):
        H = sets_for(marginal(a))
        b = float((H[0] & H[1])[:, ev].mean())
        if best is None or abs(b - target) < abs(best[1] - target):
            best = (a, b, H)
    summary(f"marginal size-matched alpha {best[0]}", *best[2])
    summary("outcome-conditional alpha 0.2", *sets_for(outcome_cond(0.2)))
    pd.DataFrame(out).to_csv(OUT / "extra_m2.csv", index=False)
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print(pd.DataFrame(out).round(3).T.to_string())


if __name__ == "__main__":
    main()
