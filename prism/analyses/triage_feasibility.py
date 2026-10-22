"""Triage feasibility on the existing data: longitudinal volume trajectory (T1) and rule-out operating points (T2).

ANALYSIS PLAN: docs/results/TRIAGE_FEASIBILITY.md, section "Plan (pre-specified)", committed (fc2d247) before any T1/T2
quantity was computed on real labels; snapshotted to outputs/results/analyses/triage_feasibility/PLAN_snapshot.md by
the first run.

T1  C2 + 11 trajectory features (as of the scan day: Theil-Sen slope, exponentially weighted level and deviation,
    log ratio to and days since the nadir since RT end, number of prior scans; ET and lesion) vs C2. Ridge pipeline of
    C2 (audit.model.fit_pipeline: in-fold imputation, scaling, inner choice of C), shared 5x5 folds, trained on all
    grade-4 scans; PRIMARY evaluation on the intended-use scans (RT started by the scan day). Secondary: grade 4
    overall, refitted inside intended use. Rule: dAUC >= 0.03 and paired 95% CI lower bound > 0.
T2  Rule-out operating points in intended use (lowest 20/30/40% of predictions = low risk): IPCW NPV (primary), verified
    NPV, sensitivity, specificity, events missed; patient-cluster bootstrap with the quantile threshold and weights
    re-derived in every draw. Decision curve (net benefit vs treat-all / treat-none). Rule: some q classifies >= 20% as
    low risk with IPCW NPV lower 95% bound >= 0.85.
GO if T1 or T2 succeeds, else NO-GO on MU-Glioma-Post alone.

    python -m prism triage [--workers 25] [--n-boot 1000]
    -> $PRISM_OUTPUTS/results/analyses/triage_feasibility/
       features.csv, oof_<set>.csv.gz, auc.csv, coefficients.csv, operating_points.csv, npv_curve.csv,
       decision_curve.csv, rule.csv, checks.csv, run_info.json
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.stats import theilslopes
from threadpoolctl import threadpool_limits

from prism.analyses import phase_censoring as pc
from prism.audit.model import fit_pipeline
from prism.audit.provenance import git_state
from prism.config import MEASUREMENTS, REPO, RESULTS
from prism.experiments import c3_radiomics as c3
from prism.features.tabular import treatment
from prism.models.metrics import counted_warnings, evaluate_repeated

H = pc.H
POP = "grade4"
OUT = RESULTS / "analyses" / "triage_feasibility"
EPS_CC = 0.1
HALF_LIFE = 90.0
VOLS = {"et": "et_cc", "lesion": "lesion_cc"}
ARMS = ("C2", "C2+traj", "traj")
SETS = ("full", "rt_started")  # training sets: all grade-4 scans (primary) / refitted inside intended use
QS = (0.20, 0.30, 0.40)
Q_CURVE = tuple(np.round(np.arange(0.05, 0.501, 0.05), 2))
PT = tuple(np.round(np.arange(0.05, 0.801, 0.05), 2))
GAIN_BAR, NPV_BAR, FRAC_BAR = 0.03, 0.85, 0.20


# ---------------------------------------------------------------- trajectory features (as of the scan day)
def _features_one(hist: pd.DataFrame, day: float, win_start: float) -> dict:
    """hist: the patient's measured scans, all dated <= day, including the index scan (sorted by day)."""
    assert (hist.mri_day.to_numpy() <= day).all(), "trajectory history contains a scan after the index day"
    t = hist.mri_day.to_numpy(float)
    idx = np.where(t == day)[0]
    assert len(idx) == 1, "index scan missing from (or duplicated in) its history"
    i = idx[0]
    prior = t < day
    out = {"traj_n_prior_scans": float(prior.sum())}
    w_all = 0.5 ** ((day - t) / HALF_LIFE)
    for k, col in VOLS.items():
        x = np.log(hist[col].to_numpy(float) + EPS_CC)
        out[f"traj_slope_log_{k}"] = float(theilslopes(x, t)[0] * 30.0) if len(t) >= 2 else np.nan
        out[f"traj_ew_level_log_{k}"] = float(np.sum(w_all * x) / np.sum(w_all))
        out[f"traj_ew_dev_log_{k}"] = (float(x[i] - np.sum(w_all[prior] * x[prior]) / np.sum(w_all[prior]))
                                       if prior.any() else np.nan)
        win = (t >= win_start) | (t == day) if np.isfinite(win_start) else np.ones(len(t), bool)
        xm = x[win].min()
        out[f"traj_logratio_nadir_{k}"] = float(x[i] - xm)
        out[f"traj_days_since_nadir_{k}"] = float(day - t[win][x[win] == xm].max())
    return out


def nadir_window_start(cohort: pd.DataFrame, index: pd.DataFrame) -> np.ndarray:
    """RT end day if RT is completed by the scan, else RT start day if started, else -inf (whole history)."""
    tr = treatment(cohort, index)
    start = tr.rt_start_day.to_numpy(float)
    end = start + tr.rt_duration_days.to_numpy(float)
    ws = np.where(tr.rt_completed.eq(1), end, np.where(tr.rt_started.eq(1), start, -np.inf))
    return np.where(np.isnan(ws), -np.inf, ws)  # RT started/completed without a documented day: whole history


def trajectory(cohort: pd.DataFrame, index: pd.DataFrame, meas: pd.DataFrame | None = None) -> pd.DataFrame:
    meas = pd.read_csv(MEASUREMENTS) if meas is None else meas
    by_pat = {p: g.sort_values("mri_day") for p, g in meas.groupby("patient_id")}
    days = pd.to_numeric(cohort.days_from_diagnosis_to_mri, errors="coerce").to_numpy(float)
    ws = nadir_window_start(cohort, index)
    rows = []
    for j, (sid, pid) in enumerate(zip(cohort.scan_id, cohort.patient_id)):
        g = by_pat[pid]
        assert g.loc[g.scan_id == sid, "mri_day"].item() == days[j], sid
        rows.append(_features_one(g[g.mri_day <= days[j]], days[j], ws[j]))  # past and current scans only
    return pd.DataFrame(rows, index=cohort.index)


def leakage_check(cohort, index, F: pd.DataFrame, seed=0) -> float:
    """Perturb every scan dated after each index scan (volumes x random factor, plus dropping some) and recompute:
    features must not change. Returns the max absolute deviation (asserted 0)."""
    meas = pd.read_csv(MEASUREMENTS)
    rng = np.random.default_rng(seed)
    days = pd.to_numeric(cohort.days_from_diagnosis_to_mri, errors="coerce").to_numpy(float)
    dev = 0.0
    for j in range(len(cohort)):
        m = meas.copy()
        fut = (m.patient_id == cohort.patient_id.iat[j]).to_numpy() & (m.mri_day.to_numpy(float) > days[j])
        for col in VOLS.values():
            m.loc[fut, col] = m.loc[fut, col] * rng.uniform(0.1, 10, fut.sum()) + rng.uniform(0, 50, fut.sum())
        m = m[~(fut & (rng.uniform(size=len(m)) < 0.3))]
        f = trajectory(cohort.iloc[[j]], index, m).iloc[0]
        dev = max(dev, float(np.nanmax(np.abs(f.to_numpy(float) - F.iloc[j].to_numpy(float)), initial=0.0)))
        assert np.array_equal(np.isnan(f.to_numpy(float)), np.isnan(F.iloc[j].to_numpy(float)))
    assert dev == 0.0, f"trajectory features depend on future scans (max dev {dev})"
    return dev


# ---------------------------------------------------------------- fits
@lru_cache(maxsize=4)
def context():
    cohort, folds, index, p4, _ = pc.load(POP)
    F = trajectory(cohort, index)
    Xc, gc = pc.arm_design("C2", cohort, index)
    gt = {c: "trajectory" for c in F.columns}
    designs = {"C2": (Xc, gc), "C2+traj": (pd.concat([Xc, F], axis=1), {**gc, **gt}), "traj": (F, gt)}
    return cohort, folds, index, p4, F, designs


def set_mask(name, p4):
    return np.ones(len(p4), bool) if name == "full" else p4 != "pre_rt"


@counted_warnings
def cv_job(job):
    st, arm, r, k = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    cohort, folds, _, p4, _, designs = context()
    keep = set_mask(st, p4)
    sub = cohort[keep].reset_index(drop=True)
    X, groups = designs[arm]
    X = X[keep].reset_index(drop=True)
    f = c3._fold_ids(sub, folds, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    m = fit_pipeline(X, sub, tr, groups, seed=r)
    return job, te, m.predict(X.iloc[te]), m.coef_series()


# ---------------------------------------------------------------- T2: operating points and decision curve
def op_metrics(P, case, ctrl, w, y, q):
    """Mean over repeats (rows of P) for the 'lowest q fraction = low risk' rule."""
    out = []
    for p in P:
        low = p <= np.quantile(p, q, method="lower")
        ver = ~np.isnan(y)
        wl = w * low
        a = {"frac_low": low.mean(),
             "npv_ipcw": wl[ctrl].sum() / wl[case | ctrl].sum() if wl[case | ctrl].sum() > 0 else np.nan,
             "npv_verified": ((y == 0) & low).sum() / (ver & low).sum() if (ver & low).any() else np.nan,
             "sens_ipcw": (w * ~low)[case].sum() / w[case].sum(),
             "spec_ipcw": wl[ctrl].sum() / w[ctrl].sum(),
             "n_low": float(low.sum()), "events_low": float(((y == 1) & low).sum())}
        a["missed_ipcw"] = 1 - a["sens_ipcw"]
        out.append(a)
    return pd.DataFrame(out).mean().to_dict()


def net_benefit(P, case, ctrl, w, pt):
    den = w[case | ctrl].sum()
    odds = pt / (1 - pt)
    nb = np.array([((w * (p >= pt))[case].sum() - (w * (p >= pt))[ctrl].sum() * odds) / den for p in P]).mean()
    allnb = (w[case].sum() - w[ctrl].sum() * odds) / den
    return nb, allnb


def t2_stats(d, oofs):
    case, ctrl, w = pc.km_scheme(d)
    y = d[f"label_{H}"].to_numpy(float)
    res = {}
    for a, P in oofs.items():
        for q in sorted(set(QS) | set(Q_CURVE)):
            for k, v in op_metrics(P, case, ctrl, w, y, q).items():
                res[("op", a, q, k)] = v
        for pt in PT:
            nb, allnb = net_benefit(P, case, ctrl, w, pt)
            res[("dca", a, pt, "nb")] = nb
            res[("dca", "treat_all", pt, "nb")] = allnb
            res[("dca", a, pt, "nb_minus_default")] = nb - max(allnb, 0.0)
    return res


def t2_boot_chunk(job):
    d, oofs, seeds = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    pid = d.patient_id.to_numpy()
    groups = {p: np.where(pid == p)[0] for p in np.unique(pid)}
    pats = np.array(list(groups))
    out = []
    for s in seeds:
        rng = np.random.default_rng(int(s))
        idx = np.concatenate([groups[p] for p in rng.choice(pats, len(pats))])
        db = d.iloc[idx].reset_index(drop=True)
        if db[f"label_{H}"].nunique(dropna=True) < 2:
            continue
        out.append(t2_stats(db, {a: P[:, idx] for a, P in oofs.items()}))
    return out


def t2_bootstrap(d, oofs, n_boot, workers):
    point = t2_stats(d, oofs)
    seeds = np.arange(n_boot) + 7_000_000
    jobs = [(d, oofs, c) for c in np.array_split(seeds, max(1, min(workers, n_boot))) if len(c)]
    with ProcessPoolExecutor(max(1, workers)) as ex:
        draws = [r for ch in ex.map(t2_boot_chunk, jobs) for r in ch]
    return point, {k: np.array([r.get(k, np.nan) for r in draws]) for k in point}


# ---------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism triage", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=25)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--skip-leakage-check", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    warnings.filterwarnings("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    snap = OUT / "PLAN_snapshot.md"
    if not snap.exists():
        doc = (REPO / "docs" / "results" / "TRIAGE_FEASIBILITY.md").read_text()
        plan = doc.split("## Plan (pre-specified)", 1)[1].split("\n## ", 1)[0]
        snap.write_text(f"# PLAN snapshot ({time.strftime('%Y-%m-%dT%H:%M:%S')}, git {git_state()['commit'][:10]})\n\n"
                        "## Plan (pre-specified)" + plan)
    cohort, folds, index, p4, F, _ = context()
    checks = []
    if not a.skip_leakage_check:
        checks.append({"check": "trajectory features unchanged when future scans are perturbed/dropped (max dev)",
                       "value": leakage_check(cohort, index, F), "ok": True})
    F.assign(scan_id=cohort.scan_id.to_numpy(), phase4=p4).to_csv(OUT / "features.csv", index=False)
    print(f"features done {time.time() - t0:.0f}s", flush=True)

    jobs = [(s, arm, r, k) for s in SETS for arm in ARMS for r in range(5) for k in range(5)]
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(cv_job, jobs, chunksize=2))
    print(f"fits done {time.time() - t0:.0f}s", flush=True)
    oof = {s: {} for s in SETS}
    coefs = []
    for (s, arm, r, k), te, pr, cf in res:
        n = int(set_mask(s, p4).sum())
        oof[s].setdefault(arm, np.full((5, n), np.nan))[r, te] = pr
        coefs.append(cf.rename(f"{s}|{arm}|{r}|{k}"))
    for s in SETS:
        assert all(np.isfinite(v).all() for v in oof[s].values())
        sid = cohort.scan_id[set_mask(s, p4)].to_numpy()
        pd.concat([pd.DataFrame(o.T, columns=[f"{k}#r{r}" for r in range(5)]) for k, o in oof[s].items()],
                  axis=1).assign(scan_id=sid).to_csv(OUT / f"oof_{s}.csv.gz", index=False)
        ref = pd.read_csv(pc.OUT / f"oof_{POP}_{s}.csv.gz").set_index("scan_id").loc[sid]
        dev = float(np.abs(np.array([ref[f"C2#r{r}"] for r in range(5)]) - oof[s]["C2"]).max())
        checks.append({"check": f"C2 OOF ({s}) reproduces phase_censoring/oof_{POP}_{s} (max dev)", "value": dev,
                       "ok": dev < 1e-6})
        assert dev < 1e-6, (s, dev)
    cf = pd.concat(coefs, axis=1)
    cf = pd.DataFrame({"column": cf.index, **{f"{s}|{arm}_mean": cf[[c for c in cf if c.startswith(f"{s}|{arm}|")]]
                                              .mean(1) for s in SETS for arm in ARMS}})
    cf.to_csv(OUT / "coefficients.csv", index=False)

    # ---- T1: AUCs
    iu = p4 != "pre_rt"
    d_full, d_iu = cohort.reset_index(drop=True), cohort[iu].reset_index(drop=True)
    has_prior = F.traj_n_prior_scans.to_numpy() >= 1
    evals = {"intended_use|trained_all": (d_iu, {k: v[:, iu] for k, v in oof["full"].items()}),
             "grade4_overall|trained_all": (d_full, oof["full"]),
             "intended_use|refitted": (d_iu, oof["rt_started"]),
             "intended_use_with_prior|trained_all": (cohort[iu & has_prior].reset_index(drop=True),
                                                     {k: v[:, iu & has_prior] for k, v in oof["full"].items()})}
    auc_rows = []
    for name, (d, oo) in evals.items():
        ev = evaluate_repeated(d, oo, H, reference="C2", n_boot=a.n_boot)
        cn = pc.counts(d)
        for arm, r in ev.iterrows():
            auc_rows.append({"set": name, "arm": arm, **cn, **{c: r.get(c) for c in (
                "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "d_auc_ipcw_vs_C2", "d_auc_ipcw_lo", "d_auc_ipcw_hi",
                "d_auc_ipcw_p_le0", "oe_ratio", "cal_slope", "brier_ipcw", "auc_verified")}})
        print(f"{name} done {time.time() - t0:.0f}s", flush=True)
    auc = pd.DataFrame(auc_rows)
    auc.to_csv(OUT / "auc.csv", index=False)
    # bootstrap point == point estimate of the headline machinery is guaranteed by evaluate_repeated

    # ---- T2: operating points and decision curve (intended use, trained on all scans)
    oo = {k: oof["full"][k][:, iu] for k in ("C2", "C2+traj")}
    pt, dr = t2_bootstrap(d_iu, oo, a.n_boot, a.workers)
    lo_hi = lambda k: pc.ci(dr[k])
    op_rows, curve_rows, dca_rows = [], [], []
    metrics = ("frac_low", "npv_ipcw", "npv_verified", "sens_ipcw", "spec_ipcw", "missed_ipcw", "n_low", "events_low")
    for arm in oo:
        for q in QS:
            row = {"arm": arm, "q": q}
            for m in metrics:
                k = ("op", arm, q, m)
                row[m], (row[f"{m}_lo"], row[f"{m}_hi"]) = pt[k], lo_hi(k)
            if arm != "C2":
                x = dr[("op", arm, q, "npv_ipcw")] - dr[("op", "C2", q, "npv_ipcw")]
                row["d_npv_vs_C2"] = pt[("op", arm, q, "npv_ipcw")] - pt[("op", "C2", q, "npv_ipcw")]
                row["d_npv_lo"], row["d_npv_hi"] = pc.ci(x)
            op_rows.append(row)
        for q in Q_CURVE:
            curve_rows.append({"arm": arm, "q": q, **{m: pt[("op", arm, q, m)] for m in metrics}})
        for p_t in PT:
            k = ("dca", arm, p_t, "nb_minus_default")
            lo, hi = lo_hi(k)
            dca_rows.append({"arm": arm, "p_t": p_t, "nb": pt[("dca", arm, p_t, "nb")],
                             "nb_treat_all": pt[("dca", "treat_all", p_t, "nb")], "nb_treat_none": 0.0,
                             "nb_minus_default": pt[k], "lo": lo, "hi": hi})
    ops = pd.DataFrame(op_rows)
    ops.to_csv(OUT / "operating_points.csv", index=False)
    pd.DataFrame(curve_rows).to_csv(OUT / "npv_curve.csv", index=False)
    pd.DataFrame(dca_rows).to_csv(OUT / "decision_curve.csv", index=False)

    # ---- decision rules
    x = auc[(auc.set == "intended_use|trained_all") & (auc.arm == "C2+traj")].iloc[0]
    t1 = bool(x.d_auc_ipcw_vs_C2 >= GAIN_BAR and x.d_auc_ipcw_lo > 0)
    rule = [{"item": "T1: C2+traj - C2 dAUC >= 0.03 with CI lower bound > 0 (intended use, trained on all)",
             "value": x.d_auc_ipcw_vs_C2, "lo": x.d_auc_ipcw_lo, "hi": x.d_auc_ipcw_hi, "succeeds": t1}]
    t2 = False
    for _, r in ops.iterrows():
        ok = bool(r.frac_low >= FRAC_BAR - 1e-9 and r.npv_ipcw_lo >= NPV_BAR)
        t2 |= ok
        rule.append({"item": f"T2: {r.arm} q={r.q:.2f}: frac low {r.frac_low:.3f} >= 0.20 and IPCW NPV lower >= 0.85",
                     "value": r.npv_ipcw, "lo": r.npv_ipcw_lo, "hi": r.npv_ipcw_hi, "succeeds": ok})
    rule.append({"item": "T2 overall", "value": np.nan, "lo": np.nan, "hi": np.nan, "succeeds": t2})
    rule.append({"item": "GO (T1 or T2)" if (t1 or t2) else "NO-GO on MU-Glioma-Post alone", "value": np.nan,
                 "lo": np.nan, "hi": np.nan, "succeeds": t1 or t2})
    pd.DataFrame(rule).to_csv(OUT / "rule.csv", index=False)
    pd.DataFrame(checks).to_csv(OUT / "checks.csv", index=False)
    (OUT / "run_info.json").write_text(json.dumps({"argv": vars(a), "seconds": round(time.time() - t0),
                                                   "git": git_state()["commit"][:10]}, indent=1))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(checks).to_string(index=False))
    print(auc.round(3).to_string(index=False))
    print(ops.round(3).to_string(index=False))
    print(pd.DataFrame(rule).round(3).to_string(index=False))
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
