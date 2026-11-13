"""R1 conformal sets from the displayed model, R2 reliability card without the patient it describes
(plan: docs/results/REVISION_DATA_PLAN.md, written before the run; results: docs/results/REVISION_DATA.md).

R1 (cross-conformal). The displayed score is the one the system shows (on MU the out-of-fold fit on the outer
training fold; externally the MU model fitted on all training rows). Calibration scores are out-of-fold predictions of
the same model specification from fivefold cross validation grouped by patient over the same training rows (patients
shuffled with seed 10 x repeat + fold on MU, seed 0 externally). Threshold: conformal.threshold (patient weights);
set = {y : 1 - p_displayed(y) <= q}.

R2 (leave one patient out). For each scan, its situation's counts, tier and AUCs are recomputed from the card's own
cohort table without any scan of the scan's patient. Flags are recomputed with that tier.

    PRISM_SKIP_UCSF=1 PYTHONPATH=. .venv/bin/python -m prism.analyses.revision_data [--workers 20]
    -> outputs/results/analyses/revision_data/   (aggregate CSVs; per-scan files git-ignored)
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
from prism.analyses import reliability_card as RC
from prism.analyses import system as S
from prism.audit import conformal as cf
from prism.audit import reliability as R
from prism.config import RESULTS

OUT = RESULTS / "analyses" / "revision_data"
INNER = 5


def inner_folds(pid: np.ndarray, seed: int) -> np.ndarray:
    u = np.random.default_rng(seed).permutation(np.unique(pid))
    f = {p: i % INNER for i, p in enumerate(u)}
    return np.array([f[p] for p in pid])


def _q(oof, y, pid):
    lab = ~np.isnan(y)
    s = cf.scores(oof[lab], y[lab].astype(int))
    return {a: cf.threshold(s, pid[lab], a) for a in S.ALPHAS}


# ---------------------------------------------------------------- R1, MU
def mu_job(job):
    from prism.experiments import c3_radiomics as c3
    pop, r, k = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    d, X = S.mu_designs(pop)
    y, pid = d.label_120.to_numpy(), d.patient_id.to_numpy()
    f = D.fold_ids(d, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    inner = inner_folds(pid[tr], 10 * r + k)
    out = {"r": r, "k": k, "te": te}
    for p, Xa in X.items():
        p_te = c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr, te, seed=r)
        oof = np.full(len(tr), np.nan)
        for j in range(INNER):
            oof[inner == j] = c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr[inner != j], tr[inner == j], seed=r)
        out[p] = (p_te, _q(oof, y[tr], pid[tr]))
    return out


def mu_r1(workers, pop="grade4"):
    d, _ = S.mu_designs(pop)
    n = len(d)
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(mu_job, [(pop, r, k) for r in range(5) for k in range(5)]))
    P = {p: np.full((5, n), np.nan) for p in S.PW}
    sets = {(p, a, c): np.zeros((5, n), bool) for p in S.PW for a in S.ALPHAS for c in (0, 1)}
    for j in res:
        for p in S.PW:
            pt, q = j[p]
            P[p][j["r"], j["te"]] = pt
            for a in S.ALPHAS:
                h0, h1 = cf.prediction_sets(pt, q[a])
                sets[(p, a, 0)][j["r"], j["te"]], sets[(p, a, 1)][j["r"], j["te"]] = h0, h1
    return P, sets


# ---------------------------------------------------------------- R1, LUMIERE
def lumiere_r1():
    L, LX, _ = D.lumiere_detection()
    dm, X, *_ = D.context("grade4", "primary")
    timg = [c for c in X["T"].columns if c not in D.T_BASE + ["has_prev", "log_days_from_prev"]]
    Xmu = {"timeline": X["T"][D.T_BASE], "images": X["T"][timg], "combined": X["T"], "images_scan": X["T"][S.VOL3]}
    Xl = {"timeline": LX[D.T_BASE], "images": LX[timg], "combined": LX, "images_scan": LX[S.VOL3]}
    rows = np.arange(len(dm))
    y, pid = dm.label_120.to_numpy(), dm.patient_id.to_numpy()
    inner = inner_folds(pid, 0)
    full, q = {}, {}
    for name, Xa in Xmu.items():
        full[name] = S._fit(Xa, dm, rows)
        oof = np.full(len(dm), np.nan)
        for j in range(INNER):
            oof[inner == j] = S._fit(Xa, dm, rows[inner != j])(Xa.iloc[np.where(inner == j)[0]])
        q[name] = _q(oof, y, pid)
    nop = L.prev_scan_id.eq("").to_numpy()
    n = len(L)
    P = {p: np.full((1, n), np.nan) for p in S.PW}
    sets = {(p, a, c): np.zeros((1, n), bool) for p in S.PW for a in S.ALPHAS for c in (0, 1)}
    for p in S.PW:
        parts = [(p, ~nop), ("images_scan", nop)] if p == "images" else [(p, np.ones(n, bool))]
        for name, m in parts:
            pt = full[name](Xl[name])
            P[p][0, m] = pt[m]
            for a in S.ALPHAS:
                h0, h1 = cf.prediction_sets(pt[m], q[name][a])
                sets[(p, a, 0)][0, m], sets[(p, a, 1)][0, m] = h0, h1
    return P, sets, {k: {str(a): float(v) for a, v in d_.items()} for k, d_ in q.items()}


def coverage_rows(cohort, method, y, P_ref, sets, m, P_disp):
    """P_disp: the displayed combined score, for the error at the cohort median (as Table tab:hides)."""
    out = []
    y = y[m].astype(int)
    Pd = P_disp[:, m]
    err = ((Pd > np.median(Pd, axis=1, keepdims=True)).astype(int) != y)
    for p in S.PW:
        for a in S.ALPHAS:
            h0, h1 = sets[(p, a, 0)][:, m], sets[(p, a, 1)][:, m]
            hit = np.where(y == 1, h1, h0)
            out.append({"cohort": cohort, "method": method, "model": p, "alpha": a, "n_scans": int(m.sum()),
                        "coverage": float(hit.mean()), "coverage_progression": float(hit[:, y == 1].mean()),
                        "coverage_no_progression": float(hit[:, y == 0].mean()),
                        "both_share": float((h0 & h1).mean()), "empty_share": float((~h0 & ~h1).mean()),
                        "single_share": float((h0 ^ h1).mean()),
                        "error_where_both": float(err[h0 & h1].mean()) if (h0 & h1).any() else np.nan,
                        "error_other": float(err[~(h0 & h1)].mean()),
                        "auc_of_score_used": S.auc_m(y, P_ref[p][:, m], np.ones_like(P_ref[p][:, m], bool))})
    return out


# ---------------------------------------------------------------- R2
def lopo_tiers(c: dict, frame: pd.DataFrame) -> tuple[np.ndarray, list[dict]]:
    """Per scan: tier and AUCs of its situation in its own cohort's table, without its patient."""
    e = frame[frame.label.notna()].reset_index(drop=True)
    y, g = e.label.to_numpy(int), e.patient_id.to_numpy()
    cells = (e.phase + "|" + e.enhancement).to_numpy()
    Sm = {p: RC.score_matrix(e, p) for p in R.PATHWAYS}
    tiers, rows = [], []
    for sid, pid, ph, en in zip(c["scan_id"], c["patient_id"], c["card_phase"], c["enh"]):
        m = (cells == f"{ph}|{en}") & (g != pid)
        npos, nneg = int(y[m].sum()), int((y[m] == 0).sum())
        t = R.tier(npos, nneg)
        tiers.append(t)
        rows.append({"scan_id": sid, "n_pos": npos, "n_neg": nneg, "tier": t,
                     **{f"{p}_auc": (R.mean_auc(y, Sm[p], m) if t == "tested" else np.nan) for p in R.PATHWAYS}})
    return np.array(tiers), rows


def r2(cohorts, table):
    fr = {f.cohort.iat[0]: f for f in RC.frames()}
    out, per = [], []
    for key, setname in ((("mu", "grade4"), "intended_use"), (("lumiere", "grade4"), "all")):
        c = S.derive(cohorts[key], table)
        reg_tier = c["tier"].copy()
        lt, rows = lopo_tiers(c, fr[c["own"]])
        per += [{**r_, "cohort": key[0], "registered_tier": t0} for r_, t0 in zip(rows, reg_tier)]
        m = c["eval"][setname]
        y = c["y"][m].astype(int)
        P = c["S"]["p_combined"][:, m]
        Rn = P.shape[0]
        F = c["flags"]
        lt_flag = np.broadcast_to(lt != "tested", (Rn, len(lt)))
        any_lopo = F["disagree"] | F["out_of_range"] | lt_flag | F["conformal"]
        for name, tier, anyf, tf in (("registered", reg_tier, F["any"], F["tier"]), ("leave one patient out", lt,
                                                                                    any_lopo, lt_flag)):
            tm, am = np.asarray(tf)[:, m], np.asarray(anyf)[:, m]
            out.append({"cohort": key[0], "card": name, "n_scans": int(m.sum()),
                        "share_tested": float((tier[m] == "tested").mean()),
                        "share_few_cases": float((tier[m] == "few cases").mean()),
                        "share_not_tested": float((tier[m] == "not tested").mean()),
                        "tier_flag_share": float(tm.mean()), "any_flag_share": float(am.mean()),
                        "auc_all": S.auc_m(y, P, np.ones_like(P, bool)),
                        "auc_no_flag": S.auc_m(y, P, ~am), "auc_tier_tested": S.auc_m(y, P, ~tm),
                        "tier_changed_scans": int((reg_tier[m] != lt[m]).sum()),
                        "tested_to_few": int(((reg_tier[m] == "tested") & (lt[m] != "tested")).sum())})
    return out, per


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=20)
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    cohorts = S.build(a.workers)
    table, _ = RC.load_table()
    print(f"system cohorts rebuilt {time.time() - t0:.0f}s", flush=True)
    # R1
    rows = []
    c = cohorts[("mu", "grade4")]
    m = c["eval"]["intended_use"]
    regP = {p: c["S"][f"pc_{p}"] for p in S.PW}
    reg = {(p, al, k): c["sets"][("std", p, al, k)] for p in S.PW for al in S.ALPHAS for k in (0, 1)}
    rows += coverage_rows("mu", "registered (split, refitted model)", c["y"], regP, reg, m,
                          c["S"]["p_combined"])
    P, sets = mu_r1(a.workers)
    dev = max(float(np.nanmax(np.abs(P[p] - c["S"][f"p_{p}"]))) for p in S.PW)
    print(f"MU displayed-score check: max deviation {dev:.2e}", flush=True)
    assert dev < 1e-9
    rows += coverage_rows("mu", "cross-conformal (displayed model)", c["y"], P, sets, m, c["S"]["p_combined"])
    L = cohorts[("lumiere", "grade4")]
    m = L["eval"]["all"]
    regP = {p: L["S"][f"pc_{p}"] for p in S.PW}
    reg = {(p, al, k): L["sets"][("std", p, al, k)] for p in S.PW for al in S.ALPHAS for k in (0, 1)}
    rows += coverage_rows("lumiere", "registered (split, refitted model)", L["y"], regP, reg, m,
                          L["S"]["p_combined"])
    P, sets, q = lumiere_r1()
    dev = max(float(np.nanmax(np.abs(P[p] - L["S"][f"p_{p}"]))) for p in S.PW)
    print(f"LUMIERE displayed-score check: max deviation {dev:.2e}", flush=True)
    assert dev < 1e-9
    rows += coverage_rows("lumiere", "cross-conformal (displayed model)", L["y"], P, sets, m,
                          L["S"]["p_combined"])
    r1 = pd.DataFrame(rows)
    r1.to_csv(OUT / "r1_conformal.csv", index=False)
    mu_cov = r1.query("cohort == 'mu' and method.str.startswith('cross') and model == 'combined' and alpha == 0.2",
                      engine="python").coverage.iat[0]
    lu_cov = r1.query("cohort == 'lumiere' and method.str.startswith('cross') and model == 'combined' and alpha == 0.2",
                      engine="python").coverage.iat[0]
    adopt = bool(mu_cov >= 0.78 and lu_cov >= 0.75)
    pd.set_option("display.width", 250)
    print(r1.round(3).to_string(index=False), flush=True)
    print(f"R1 adoption rule (MU >= 0.78 and LUMIERE >= 0.75 at alpha 0.2, combined): {mu_cov:.3f}, {lu_cov:.3f} -> "
          f"{'adopt' if adopt else 'keep split sets'}", flush=True)
    # R2
    r2rows, per = r2(cohorts, table)
    pd.DataFrame(r2rows).to_csv(OUT / "r2_card.csv", index=False)
    pd.DataFrame(per).to_csv(OUT / "r2_card_per_scan.csv.gz", index=False)  # patient-level, git-ignored
    print(pd.DataFrame(r2rows).round(3).to_string(index=False), flush=True)
    (OUT / "run_info.json").write_text(json.dumps({"seconds": round(time.time() - t0), "r1_adopt": adopt,
                                                   "r1_mu_cov": mu_cov, "r1_lumiere_cov": lu_cov,
                                                   "lumiere_thresholds": q}, indent=1))


if __name__ == "__main__":
    main()
