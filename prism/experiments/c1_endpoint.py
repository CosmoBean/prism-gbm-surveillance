"""C1: does the outcome formulation change what we learn and report?

Same features, same folds, four formulations (naive / verified / ipcw / hazard), evaluated with
censoring-aware metrics. Headline = mean over the CV repeats of each repeat's pooled out-of-fold metric; CIs from a
patient-cluster bootstrap of that mean (paired vs naive). `*_averaged` = metric of the repeat-averaged prediction.

    python -m prism c1 [--n-boot 1000]
    -> outputs/results/c1/{c1_results.csv, c1_oof_predictions.csv, c1_summary.md}
"""

from __future__ import annotations

import argparse
import itertools
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.base import clone
from threadpoolctl import threadpool_limits

from prism.config import HORIZONS, PRIMARY_HORIZON, RESULTS
from prism.data.mu import load_cohort
from prism.features.tabular import feature_set
from prism.models.folds import load_folds
from prism.models.formulations import FORMULATIONS, fit, predict_risk
from prism.models.metrics import counted_warnings, evaluate_repeated

POPULATIONS = {"grade4": lambda c: c["grade4"], "all_glioma": lambda c: pd.Series(True, index=c.index)}
FEATURE_SETS = ("volumes_clinical", "radiomics_clinical")


@counted_warnings
def run_combo(job):
    population, fset, horizon, n_boot = job
    threadpool_limits(1)  # many tiny fits per process: BLAS thread pools only oversubscribe the node
    cohort = load_cohort()
    folds = load_folds()
    cohort = cohort[POPULATIONS[population](cohort)].reset_index(drop=True)
    X_raw, pre = feature_set(fset, cohort)
    oof = {f: np.zeros((folds.repeat.nunique(), len(cohort))) for f in FORMULATIONS}
    chosen_C = []
    for r, fr in folds.groupby("repeat"):
        fold_of = cohort.scan_id.map(fr.set_index("scan_id").fold).to_numpy()
        for k in np.unique(fold_of):
            tr, te = np.where(fold_of != k)[0], np.where(fold_of == k)[0]
            p = clone(pre).fit(X_raw.iloc[tr])
            Xtr, Xte = p.transform(X_raw.iloc[tr]), p.transform(X_raw.iloc[te])
            dtr = cohort.iloc[tr].reset_index(drop=True)
            for f in FORMULATIONS:
                model, C = fit(f, Xtr, dtr, horizon, seed=r)
                oof[f][r, te] = predict_risk(f, model, Xte)
                chosen_C.append(C)
    preds = {f: oof[f].mean(axis=0) for f in FORMULATIONS}
    ev = evaluate_repeated(cohort, oof, horizon, reference="naive", n_boot=n_boot)
    rows = []
    for f in FORMULATIONS:
        row = {"population": population, "features": fset, "horizon": horizon, "formulation": f,
               "n_scans": len(cohort), "n_patients": cohort.patient_id.nunique(),
               "n_pos": int((cohort[f"label_{horizon}"] == 1).sum()),
               "n_censored": int(cohort[f"label_{horizon}"].isna().sum()), **ev.loc[f].dropna().to_dict()}
        rows.append(row)
    oof_df = cohort[["scan_id", "patient_id"]].assign(population=population, features=fset, horizon=horizon,
                                                       **{f"p_{f}": preds[f] for f in FORMULATIONS})
    return pd.DataFrame(rows), oof_df


def summary_markdown(res: pd.DataFrame) -> str:
    fmt = lambda r, m: f"{r[m]:.3f} [{r[m + '_lo']:.3f}, {r[m + '_hi']:.3f}]"
    lines = ["# C1 — outcome formulation results", "",
             "5×5 repeated patient-grouped CV; every metric is the mean over the 5 repeats of the metric of that "
             "repeat's pooled out-of-fold predictions. 95% CIs from a patient-cluster bootstrap of that mean; ΔAUC "
             "(point estimate, paired bootstrap CI) vs the naive formulation. Last column: AUC of the repeat-averaged "
             "prediction (earlier headline, optimistic).", ""]
    for (pop, fs, h), g in res.groupby(["population", "features", "horizon"], sort=False):
        r0 = g.iloc[0]
        lines += [f"## {pop} · {fs} · H = {h} d  (scans {r0.n_scans}, patients {r0.n_patients}, "
                  f"positives {r0.n_pos}, censored {r0.n_censored})", "",
                  "| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for _, r in g.iterrows():
            d = "—" if r.formulation == "naive" else (
                f"{r['d_auc_ipcw_vs_naive']:+.3f} [{r['d_auc_ipcw_lo']:+.3f}, {r['d_auc_ipcw_hi']:+.3f}]")
            lines.append(f"| {r.formulation} | {fmt(r, 'auc_ipcw')} | {d} | {fmt(r, 'brier_ipcw')} | "
                         f"{r.auc_verified:.3f} | {r.auc_naive:.3f} | {r.oe_ratio:.2f} | {r.cal_slope:.2f} | "
                         f"{r.auc_ipcw_averaged:.3f} |")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism c1", description=__doc__)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args(argv)
    jobs = [(p, f, h, a.n_boot) for p, f, h in itertools.product(POPULATIONS, FEATURE_SETS, HORIZONS)]
    with ProcessPoolExecutor(a.workers) as ex:
        outs = list(ex.map(run_combo, jobs))
    res = pd.concat([o[0] for o in outs], ignore_index=True)
    oof = pd.concat([o[1] for o in outs], ignore_index=True)
    out = RESULTS / "c1"
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "c1_results.csv", index=False)
    oof.to_csv(out / "c1_oof_predictions.csv", index=False)
    md = summary_markdown(res)
    (out / "c1_summary.md").write_text(md)
    prim = res[(res.population == "grade4") & (res.horizon == PRIMARY_HORIZON)]
    print(prim[["features", "formulation", "auc_ipcw", "auc_ipcw_averaged", "d_auc_ipcw_vs_naive", "brier_ipcw", "auc_verified",
                "auc_naive", "oe_ratio", "cal_slope"]].round(3).to_string(index=False))

