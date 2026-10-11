"""Clinical usefulness: calibration, decision curves, added value (NRI/IDI) and sample size.

Calibration     Van Calster 2019: calibration-in-the-large (intercept with logit offset), weighted O/E, slope,
                flexible curve (logistic on a restricted cubic spline of logit(p), 3 knots) + ICI; plus the
                Kaplan-Meier O/E and slope of metrics.point_metrics for cross-checking.
Decision curves Vickers & Elkin 2006: net benefit NB(t) = TP/n - FP/n * t/(1-t), thresholds 5-50%.
Added value     Pencina 2008/2011: continuous NRI (>0) and IDI of a model vs the ridge baseline.
Sample size     Riley 2020 (BMJ) 4 criteria for a binary outcome (pmsampsize formulas, re-implemented), with the
                anticipated Cox-Snell R² derived from the achieved AUC (Riley, Van Calster & Collins 2021).

Censoring: everything is estimated on verified scans (label known at 120 d) weighted by 1 / G(min(t, H)-), G = Kaplan-
Meier censoring survival floored at 0.1 — the same weights as the calibration slope in metrics.point_metrics and the
'ipcw' training formulation. Rates are normalised by the weight sum, so they estimate per-scan rates in the whole
cohort. Unweighted verified-subset net benefit is kept as a sensitivity column.
Repeated CV: each statistic is computed per repeat on that repeat's pooled OOF predictions, then averaged (as the
headline AUC). CIs: patient-cluster bootstrap; every resample re-estimates G and evaluates every model on the same
patients (paired differences).

Inputs (under $PRISM_OUTPUTS/results): c3/<pop>/oof_repeats.csv.gz (falls back to the repeat-averaged oof.csv),
analyses/deep/<pop>/oof_repeats.csv.gz or oof.csv (if present), external_lumiere/locked_predictions.csv.

    python -m prism.analyses.utility [--populations grade4 all_glioma --n-boot 1000]
    # -> outputs/results/analyses/utility/
"""

from __future__ import annotations

import argparse
import json
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit, logit
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression

from prism.config import RESULTS
from prism.models.formulations import G_FLOOR, _observed_time, censoring_survival
from prism.models.metrics import point_metrics

H = 120
OUT = RESULTS / "analyses" / "utility"
THRESHOLDS = np.round(np.arange(0.05, 0.501, 0.01), 2)
REPORT_T = (0.10, 0.20, 0.30)
C3_MODELS = {"baseline_ridge": "None|none|none|none|ridge", "baseline_gbm": "None|none|none|none|gbm",
             "baseline+radiomics_nested": "NESTED|-|-|-|ridge"}
DEEP_MODELS = {"deep_baseline_ridge": "None|none|none|none|ridge", "baseline+deep_nested": "NESTED_D1"}
LUMIERE_FEATURES = ("grade4|clinical+timing+volumes|gbm", "grade4|clinical+timing+volumes|ridge")
REF = "baseline_ridge"
COLORS = {"baseline_ridge": "#2a78d6", "baseline_gbm": "#1baf7a", "baseline+radiomics_nested": "#eb6834",
          "baseline+deep_nested": "#e87ba4", "locked": "#2a78d6", "recalibrated": "#eb6834"}


# ---------------------------------------------------------------- inputs
def read_oof(path_dir, cohort, models):
    """{name: (n_repeats x n_scans)} aligned to cohort.scan_id; per-repeat file if present, else averaged (1 row)."""
    rep, avg = path_dir / "oof_repeats.csv.gz", path_dir / "oof.csv"
    if rep.exists():
        t = pd.read_csv(rep).set_index("scan_id").reindex(cohort.scan_id)
        out = {n: t[sorted([c for c in t if c.split("#r")[0] == k], key=lambda c: int(c.split("#r")[1]))].to_numpy().T
               for n, k in models.items() if any(c.split("#r")[0] == k for c in t)}
        return out, "per-repeat"
    if avg.exists():
        t = pd.read_csv(avg).set_index("scan_id").reindex(cohort.scan_id)
        return {n: t[[k]].to_numpy().T for n, k in models.items() if k in t}, "repeat-averaged (oof_repeats missing)"
    return {}, "missing"


def weights(d):
    """(known, y, w): verified mask, labels, IPCW weights 1/max(G(min(t,H)-), G_FLOOR) (metrics.point_metrics)."""
    y = d[f"label_{H}"].to_numpy(float)
    known = ~np.isnan(y)
    G = censoring_survival(d, H)
    w = 1.0 / np.maximum(G(np.minimum(_observed_time(d, H), H)), G_FLOOR)
    return known, np.nan_to_num(y), np.where(known, w, 0.0)


# ---------------------------------------------------------------- statistics on one prediction vector
def rcs(x, knots):
    """Restricted cubic spline basis (Harrell), columns: x, nonlinear terms."""
    k = knots
    cols = [x]
    for j in range(len(k) - 2):
        c = (np.clip(x - k[j], 0, None) ** 3 - np.clip(x - k[-2], 0, None) ** 3 * (k[-1] - k[j]) / (k[-1] - k[-2])
             + np.clip(x - k[-1], 0, None) ** 3 * (k[-2] - k[j]) / (k[-1] - k[-2]))
        cols.append(c / (k[-1] - k[0]) ** 2)
    return np.column_stack(cols)


def calibration(p, y, w, grid):
    """Weighted CITL intercept, O/E, slope, flexible curve on `grid`, ICI (mean |curve(p) - p| over all scans)."""
    m = w > 0
    lp, yy, ww = logit(np.clip(p, 1e-6, 1 - 1e-6)), y[m], w[m]
    f = lambda a: np.sum(ww * (yy - expit(a + lp[m])))
    citl = brentq(f, -10, 10)
    slope = LogisticRegression(penalty=None, max_iter=1000).fit(lp[m, None], yy, sample_weight=ww).coef_[0][0]
    knots = np.percentile(lp, [10, 50, 90])
    flex = LogisticRegression(penalty=None, max_iter=2000).fit(rcs(lp[m], knots), yy, sample_weight=ww)
    curve = flex.predict_proba(rcs(logit(grid), knots))[:, 1]
    ici = float(np.mean(np.abs(flex.predict_proba(rcs(lp, knots))[:, 1] - p)))
    return {"citl": citl, "oe_w": np.sum(ww * yy) / np.sum(ww * p[m]), "slope": slope, "ici": ici}, curve


def net_benefit(p, y, w, thr=THRESHOLDS):
    pos = p[:, None] >= thr[None, :]
    tp = (w * y) @ pos / w.sum()
    fp = (w * (1 - y)) @ pos / w.sum()
    return tp - fp * thr / (1 - thr)


def treat_all(y, w, thr=THRESHOLDS):
    prev = np.sum(w * y) / w.sum()
    return prev - (1 - prev) * thr / (1 - thr)


def nri_idi(pn, po, y, w):
    """Continuous NRI (event + non-event components) and IDI, IPCW-weighted."""
    e, ne = w * y, w * (1 - y)
    up, down = (pn > po).astype(float), (pn < po).astype(float)
    nri_e = (e @ (up - down)) / e.sum()
    nri_ne = (ne @ (down - up)) / ne.sum()
    idi = (e @ pn / e.sum() - ne @ pn / ne.sum()) - (e @ po / e.sum() - ne @ po / ne.sum())
    return {"nri": nri_e + nri_ne, "nri_events": nri_e, "nri_nonevents": nri_ne, "idi": idi}


# ---------------------------------------------------------------- one evaluation set (all models, all repeats)
def summarise(d, preds, grids, ref, idx=None):
    """Per model: mean over repeats of calibration stats, curve and NB; vs ref: NRI/IDI (repeat r vs r, or vs the
    ref's mean prediction when repeat counts differ) and ΔNB. idx = bootstrap row indices."""
    db = d if idx is None else d.iloc[idx].reset_index(drop=True)
    known, y, w = weights(db)
    yv = np.where(known, y, 0.0)
    out = {"treat_all": treat_all(yv[known], w[known])}
    for name, P in preds.items():
        P = P if idx is None else P[:, idx]
        cs, curves, nbs, nbv = [], [], [], []
        for p in P:
            c, cu = calibration(p, yv, w, grids[name])
            cs.append(c), curves.append(cu)
            nbs.append(net_benefit(p[known], yv[known], w[known]))
            nbv.append(net_benefit(p[known], yv[known], np.ones(known.sum())))
        out[name] = {"cal": pd.DataFrame(cs).mean().to_dict(), "curve": np.mean(curves, 0), "nb": np.mean(nbs, 0),
                     "nb_unweighted": np.mean(nbv, 0)}
    if ref is not None:
        R = preds[ref] if idx is None else preds[ref][:, idx]
        for name, P in preds.items():
            if name == ref:
                continue
            P = P if idx is None else P[:, idx]
            pairs = zip(P, R) if len(P) == len(R) else ((p, R.mean(0)) for p in P)
            out[name]["vs_ref"] = pd.DataFrame([nri_idi(p[known], r[known], yv[known], w[known]) for p, r in pairs]
                                               ).mean().to_dict()
            out[name]["d_nb"] = out[name]["nb"] - out[ref]["nb"]
    return out


def evaluate(d, preds, ref, n_boot, seed=0):
    grids = {k: np.linspace(*np.percentile(P, [2, 98]), 60) for k, P in preds.items()}
    point = summarise(d, preds, grids, ref)
    rng = np.random.default_rng(seed)
    pid = d["patient_id"].to_numpy()
    groups = {p: np.where(pid == p)[0] for p in np.unique(pid)}
    pats = np.array(list(groups))
    boots = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for _ in range(n_boot):
            idx = np.concatenate([groups[p] for p in rng.choice(pats, len(pats))])
            if d[f"label_{H}"].iloc[idx].nunique() < 2:
                continue
            try:
                boots.append(summarise(d, preds, grids, ref, idx))
            except (ValueError, RuntimeError):
                continue
    return point, boots, grids


def ci(boots, getter):
    a = np.array([getter(b) for b in boots], float)
    return np.nanpercentile(a, [2.5, 97.5], axis=0)


def tables(label, d, preds, ref, point, boots, grids, note, added_value=True):
    """Long tables: calibration (+ metrics.point_metrics cross-check), net benefit, added value, curves.
    Pooled AUC is left out for in-fold recalibrated LUMIERE predictions (folds adapted differently; see external)."""
    cal, nb, add, cur = [], [], [], []
    for name, P in preds.items():
        pm = pd.DataFrame([point_metrics(d, p, H) for p in P]).mean()
        row = {"set": label, "model": name, "n_repeats": len(P), "oof_source": note,
               "auc_ipcw": np.nan if name == "recalibrated" else pm.auc_ipcw,
               "oe_km": pm.oe_ratio, "cal_slope_metrics": pm.cal_slope}
        for k, v in point[name]["cal"].items():
            lo, hi = ci(boots, lambda b: b[name]["cal"][k])
            row.update({k: v, f"{k}_lo": lo, f"{k}_hi": hi})
        cal.append(row)
        clo, chi = ci(boots, lambda b: b[name]["curve"])
        cur += [{"set": label, "model": name, "p": g, "observed": o, "lo": a, "hi": b_}
                for g, o, a, b_ in zip(grids[name], point[name]["curve"], clo, chi)]
        nlo, nhi = ci(boots, lambda b: b[name]["nb"])
        dlo, dhi = ci(boots, lambda b: b[name]["d_nb"]) if "d_nb" in point[name] else (np.full(len(THRESHOLDS), np.nan),) * 2
        dpos = (np.mean([b[name]["d_nb"] > 0 for b in boots], 0) if "d_nb" in point[name]
                else np.full(len(THRESHOLDS), np.nan))
        for i, t in enumerate(THRESHOLDS):
            nb.append({"set": label, "model": name, "threshold": t, "nb": point[name]["nb"][i], "nb_lo": nlo[i],
                       "nb_hi": nhi[i], "nb_unweighted": point[name]["nb_unweighted"][i],
                       "treat_all": point["treat_all"][i], "d_nb_vs_ref": point[name].get("d_nb", [np.nan] * 99)[i],
                       "d_nb_lo": dlo[i], "d_nb_hi": dhi[i], "p_d_nb_gt0": dpos[i]})
        if added_value and "vs_ref" in point[name]:
            r = {"set": label, "model": name, "reference": ref, "pairing": "repeat r vs r" if len(P) == len(preds[ref])
                 else "vs mean reference prediction"}
            for k, v in point[name]["vs_ref"].items():
                lo, hi = ci(boots, lambda b: b[name]["vs_ref"][k])
                r.update({k: v, f"{k}_lo": lo, f"{k}_hi": hi})
            add.append(r)
    return pd.DataFrame(cal), pd.DataFrame(nb), pd.DataFrame(add), pd.DataFrame(cur)


# ---------------------------------------------------------------- sample size (Riley 2020; pmsampsize, binary)
def r2cs_from_auc(auc, prev, n=1_000_000, seed=0):
    """Cox-Snell R² implied by a C statistic (Riley, Van Calster & Collins 2021): LP ~ N(0,1) in non-events and
    N(sqrt(2) Phi^-1(C), 1) in events, prevalence prev; R²cs = 1 - exp(-LR / n) of a logistic fit on the LP."""
    rng = np.random.default_rng(seed)
    y = rng.random(n) < prev
    x = rng.standard_normal(n) + y * np.sqrt(2) * norm.ppf(auc)
    m = LogisticRegression(penalty=None, max_iter=1000).fit(x[:, None], y)
    p = m.predict_proba(x[:, None])[:, 1]
    ll = np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    ll0 = n * (prev * np.log(prev) + (1 - prev) * np.log(1 - prev))
    return 1 - np.exp(-2 * (ll - ll0) / n)


def riley_binary(n_params, prev, r2cs, shrinkage=0.9, delta_r2=0.05, mape=0.05, margin=0.05):
    """Minimum n for the four Riley 2020 criteria (binary outcome)."""
    r2max = 1 - (prev ** prev * (1 - prev) ** (1 - prev)) ** 2
    n_from = lambda S: n_params / ((S - 1) * np.log(1 - r2cs / S))
    s_r2 = r2cs / (r2cs + delta_r2 * r2max)
    crit = {"c1_overall_risk": (1.96 / margin) ** 2 * prev * (1 - prev),
            "c2_mape": np.exp((-0.508 + 0.259 * np.log(prev) + 0.504 * np.log(n_params) - np.log(mape)) / 0.544),
            "c3_shrinkage": n_from(shrinkage),
            "c4_optimism_r2": n_from(s_r2)}
    crit = {k: int(np.ceil(v)) for k, v in crit.items()}
    n = max(crit.values())
    return {**crit, "required_n": n, "required_events": int(np.ceil(n * prev)), "required_epp": n * prev / n_params,
            "r2cs_max": r2max, "shrinkage_c4": s_r2}


def sample_size(cohort, auc, n_params):
    y = cohort[f"label_{H}"]
    events, verified = int((y == 1).sum()), int(y.notna().sum())
    prev = events / verified
    r2 = {"from_auc": r2cs_from_auc(auc, prev)}
    r2["15pct_of_max"] = 0.15 * (1 - (prev ** prev * (1 - prev) ** (1 - prev)) ** 2)
    rows = []
    for model, P in n_params.items():
        for src, r in r2.items():
            rows.append({"model": model, "n_params": P, "r2cs_source": src, "r2cs": r, "auc_used": auc, "prevalence": prev,
                         "n_scans": len(cohort), "n_verified": verified, "n_patients": cohort.patient_id.nunique(),
                         "events": events, "epp_observed": events / P, **riley_binary(P, prev, r)})
    return pd.DataFrame(rows)


def candidate_params(population):
    """Design-matrix columns: baseline; + selected radiomics (top10 / top30); + full candidate pool (largest variant)."""
    from prism.experiments import c3_radiomics as c3
    _, _, base, rad, _ = c3.load(population)
    nb = c3.BASE_PRE.fit_transform(base).shape[1]
    pool = max(r.shape[1] for r in rad.values())
    return {"baseline_raw_predictors": base.shape[1], "baseline": nb, "baseline+radiomics_top10": nb + 10,
            "baseline+radiomics_top30": nb + 30,
            "baseline+radiomics_full_pool": nb + pool}


# ---------------------------------------------------------------- LUMIERE (locked vs recalibrated)
def lumiere_preds():
    from prism.data import lumiere
    from prism.experiments.external_lumiere import lumiere_fold_ids, recalibrate
    path = RESULTS / "external_lumiere" / "locked_predictions.csv"
    if not path.exists():
        return None, {}
    lc = lumiere.load_cohort()
    t = pd.read_csv(path).set_index("scan_id").reindex(lc.scan_id)
    y = lc[f"label_{H}"].to_numpy()
    ids = lumiere_fold_ids(lc)
    sets = {}
    for feat in LUMIERE_FEATURES:
        if feat not in t or t[feat].isna().any():
            continue
        locked = t[feat].to_numpy()
        rec = np.zeros(ids.shape)
        for r, f in enumerate(ids):
            for k in np.unique(f):
                tr, te = np.where(f != k)[0], np.where(f == k)[0]
                kk = tr[~np.isnan(y[tr])]
                rec[r, te] = recalibrate(locked[kk], y[kk], locked[te])[0]
        sets[feat] = {"locked": locked[None, :], "recalibrated": rec}
    return lc, sets


# ---------------------------------------------------------------- figure
def figure(cur, nb, sets, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(sets), 2, figsize=(11, 4.6 * len(sets)), squeeze=False)
    for row, (label, title) in zip(axes, sets):
        ax = row[0]
        ax.plot([0, 1], [0, 1], color="#9a9a94", lw=1, ls="--", label="ideal")
        c = cur[cur.set == label]
        for m, g in c.groupby("model", sort=False):
            col = COLORS.get(m, "#5f5e5a")
            ax.fill_between(g.p, g.lo, g.hi, color=col, alpha=0.12, lw=0)
            ax.plot(g.p, g.observed, color=col, lw=2, label=m)
        ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Predicted risk of progression by 120 d",
               ylabel="Observed (IPCW, flexible)", title=f"Calibration — {title}")
        ax.legend(frameon=False, fontsize=8, loc="upper left")
        ax = row[1]
        n = nb[nb.set == label]
        first = n[n.model == n.model.iloc[0]]
        ax.plot(first.threshold, first.treat_all, color="#5f5e5a", lw=1.5, label="treat all")
        ax.axhline(0, color="#9a9a94", lw=1, label="treat none")
        for m, g in n.groupby("model", sort=False):
            ax.plot(g.threshold, g.nb, color=COLORS.get(m, "#5f5e5a"), lw=2, label=m)
        lo = min(-0.05, n.nb.min() - 0.02)
        ax.set(xlim=(0.05, 0.5), ylim=(lo, max(n.treat_all.max(), n.nb.max()) + 0.03), xlabel="Threshold probability",
               ylabel="Net benefit (IPCW)", title=f"Decision curve — {title}")
        ax.legend(frameon=False, fontsize=8, loc="upper right")
        for a in row:
            a.spines[["top", "right"]].set_visible(False)
            a.grid(alpha=0.25, lw=0.5)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m prism.analyses.utility", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--populations", nargs="+", default=["grade4", "all_glioma"])
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    from prism.data.mu import load_cohort
    OUT.mkdir(parents=True, exist_ok=True)
    T = {k: [] for k in ("cal", "nb", "add", "cur", "ss")}
    info, fig_sets = {"n_boot": a.n_boot, "horizon": H, "sources": {}}, []

    def run(label, d, preds, ref, note, added_value=True):
        point, boots, grids = evaluate(d, preds, ref, a.n_boot)
        info["sources"][label] = {"oof": note, "n_boot_ok": len(boots), "models": list(preds)}
        for k, t in zip(("cal", "nb", "add", "cur"), tables(label, d, preds, ref, point, boots, grids, note, added_value)):
            T[k].append(t)
        print(f"[{label}] done ({len(boots)} bootstrap resamples)", flush=True)

    for pop in a.populations:
        cohort = load_cohort(pop)
        preds, note = read_oof(RESULTS / "c3" / pop, cohort, C3_MODELS)
        if REF not in preds:
            print(f"[{pop}] C3 predictions missing — skipped")
            continue
        run(f"mu_{pop}", cohort, preds, REF, note)
        fig_sets.append((f"mu_{pop}", f"MU {pop} (5x5 CV)"))
        dp, dnote = read_oof(RESULTS / "analyses" / "deep" / pop, cohort, DEEP_MODELS)
        if len(dp) == 2 and not any(np.isnan(P).any() for P in dp.values()):
            run(f"mu_{pop}_deep", cohort, dp, "deep_baseline_ridge", dnote)
        auc = float(np.mean([point_metrics(cohort, p, H)["auc_ipcw"] for p in preds[REF]]))
        T["ss"].append(sample_size(cohort, auc, candidate_params(pop)).assign(population=pop))
    lc, lsets = lumiere_preds()
    for feat, preds in lsets.items():
        label = "lumiere_" + feat.replace("|", "_")
        run(label, lc, preds, "locked", "locked = single MU-trained model; recalibrated = 5x5 patient-grouped in-fold",
            added_value=False)  # NRI/IDI of a monotone recalibration only measures the shift, not added information
        fig_sets.append((label, f"LUMIERE {feat.split('|')[-1]} (clinical+timing+volumes)"))

    cal, nb, add, cur, ss = (pd.concat(T[k], ignore_index=True) if T[k] else pd.DataFrame() for k in T)
    cal.to_csv(OUT / "calibration.csv", index=False)
    nb.to_csv(OUT / "net_benefit.csv", index=False)
    add.to_csv(OUT / "added_value.csv", index=False)
    cur.to_csv(OUT / "calibration_curves.csv", index=False)
    ss.to_csv(OUT / "sample_size.csv", index=False)
    figure(cur, nb, fig_sets, OUT / "calibration_dca.png")
    (OUT / "run_info.json").write_text(json.dumps(info, indent=1))

    pd.set_option("display.width", 200)
    r3 = lambda t: t.round(3).to_string(index=False)
    print("\nCalibration (mean over repeats; IPCW on verified scans):")
    print(r3(cal[["set", "model", "n_repeats", "auc_ipcw", "oe_km", "oe_w", "citl", "citl_lo", "citl_hi", "slope",
                  "slope_lo", "slope_hi", "ici"]]))
    print("\nNet benefit at 10/20/30% (Δ vs reference, 95% CI):")
    sel = nb[nb.threshold.isin(REPORT_T)]
    print(r3(sel[["set", "model", "threshold", "nb", "nb_lo", "nb_hi", "treat_all", "d_nb_vs_ref", "d_nb_lo", "d_nb_hi"]]))
    if len(add):
        print("\nAdded value vs reference (continuous NRI, IDI):")
        print(r3(add[["set", "model", "reference", "nri", "nri_lo", "nri_hi", "nri_events", "nri_nonevents", "idi",
                      "idi_lo", "idi_hi"]]))
    print("\nSample size (Riley 2020):")
    print(r3(ss[["population", "model", "n_params", "r2cs_source", "r2cs", "c1_overall_risk", "c2_mape", "c3_shrinkage",
                 "c4_optimism_r2", "required_n", "required_events", "events", "n_verified", "epp_observed"]]))


if __name__ == "__main__":
    main()
