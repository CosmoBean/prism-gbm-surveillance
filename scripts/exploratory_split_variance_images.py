# EXPLORATORY (post hoc, 2026-10-26): image-only models on the PRISM report split (seed 62) and over the 500 design
# splits of prism.analyses.split_variance. Same cohort (c3.load("all_glioma")), label (label_120 for training; naive_label_120
# and IPCW AUC(120) for scoring), same test patients per split (read from split_variance/per_split_auc.csv), same
# pipeline as the 'baseline' arm (c3.fit_predict, ridge). New arms:
#   I_scan  volumes + morphology / relative intensity at the scan
#   I_pure  I_scan + log volume ratios to the previous scan (0 if none) + ET / lesion log ratio to the smallest volume over
#           the whole history (no RT window). No days, no flags.  (as scripts/exploratory_pure_imaging_forward_lumiere.py)
#   clinical  clinical-only ridge (the table-2 "Clinical only" row; added over the 500 splits here)
#   baseline  re-fitted here as a check against split_variance/per_split_auc.csv
# Seed-62 CIs: patient-cluster bootstrap (prism.models.metrics.cluster_bootstrap, 1000 draws, seed 0, reference
# Baseline ridge), as in paper_figures.compute_single (table 2).
# Run: PYTHONPATH=. OMP_NUM_THREADS=1 srun ... .venv/bin/python scripts/exploratory_split_variance_images.py
# -> outputs/results/analyses/split_variance_images/
import json, time, warnings
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits
from prism.config import RESULTS
from prism.experiments import c3_radiomics as c3
from prism.models.metrics import cluster_bootstrap, point_metrics

SV = RESULTS / "analyses" / "split_variance"
OUT = RESULTS / "analyses" / "split_variance_images"
ARMS = ("I_scan", "I_pure", "clinical", "baseline")
_S = {}


def design():
    from prism.analyses import detection as D
    from prism.analyses.triage_feasibility import _features_one
    from prism.features.tabular import measurement_groups, groups as feature_groups
    cohort, _, base, rad, er = c3.load("all_glioma")
    index, _, _, meas = D._base()
    d = cohort.copy(); d["mri_day"] = pd.to_numeric(d.days_from_diagnosis_to_mri)
    F = D.change_nadir(d, index, meas)
    by_pat = {p: g.sort_values("mri_day") for p, g in meas.groupby("patient_id")}
    nad = pd.DataFrame([{k: _features_one(by_pat[pid][by_pat[pid].mri_day <= day], day, -np.inf)[f"traj_logratio_nadir_{k}"]
                         for k in ("et", "lesion")} for pid, day in zip(d.patient_id, d.mri_day)], index=d.index)
    nad.columns = ["nadir_all_et", "nadir_all_lesion"]
    mg = measurement_groups(cohort)
    img_scan = pd.concat([mg["volumes"], mg["morphology"]], axis=1)
    img_pure = pd.concat([img_scan, F[[c for c in F.columns if c.startswith("logratio_prev_")]], nad], axis=1)
    X = {"I_scan": img_scan, "I_pure": img_pure, "clinical": feature_groups(cohort)["clinical"], "baseline": base}
    return cohort, {k: v.reset_index(drop=True) for k, v in X.items()}


def _init():
    warnings.filterwarnings("ignore"); threadpool_limits(1)
    _S["cohort"], _S["X"] = design()


def predict(cohort, X, test_pids):
    te = np.where(cohort.patient_id.isin(test_pids))[0]
    tr = np.where(~cohort.patient_id.isin(test_pids))[0]
    return te, {a: c3.fit_predict(c3.BASELINES[0], cohort, X[a], {}, None, tr, te) for a in ARMS}


def run_split(job):
    seed, pids = job
    cohort = _S["cohort"]
    te, p = predict(cohort, _S["X"], set(pids))
    d = cohort.iloc[te].reset_index(drop=True)
    row = {"seed": seed, "n_test_scans_mu": len(te)}
    for a, v in p.items():
        row[f"{a}_auc_naive"] = roc_auc_score(d.naive_label_120, v)
        try:
            row[f"{a}_auc_ipcw"] = point_metrics(d, v, 120)["auc_ipcw"]
        except Exception:
            row[f"{a}_auc_ipcw"] = np.nan
    return row


def main():
    t0 = time.time(); OUT.mkdir(parents=True, exist_ok=True)
    old = pd.read_csv(SV / "per_split_auc.csv")
    _init()
    cohort, X = _S["cohort"], _S["X"]
    print({k: v.shape for k, v in X.items()}, "NaN frac", {k: float(v.isna().mean().mean()) for k, v in X.items()})
    jobs = [(int(s), t.split("|")) for s, t in zip(old.seed, old.test_patients)]
    with ProcessPoolExecutor(8, initializer=_init) as ex:
        df = pd.DataFrame(list(ex.map(run_split, jobs, chunksize=4)))
    m = old[["seed", "prism_report_split", "n_test_scans_mu", "prism_reselect_auc_naive", "prism_reselect_auc_ipcw",
             "prism_fixed_auc_naive", "prism_fixed_auc_ipcw", "baseline_auc_naive", "baseline_auc_ipcw"]].rename(
        columns=lambda c: c.replace("baseline_", "baseline_sv_"))
    df = m.merge(df, on="seed", suffixes=("_sv", ""))
    assert (df.n_test_scans_mu_sv == df.n_test_scans_mu).all()
    chk = float(np.nanmax(np.abs(df.baseline_auc_naive - df.baseline_sv_auc_naive)))
    print("baseline refit vs stored, max |d naive AUC|:", chk)
    df.to_csv(OUT / "per_split_auc.csv", index=False)
    rep = df[df.prism_report_split].iloc[0]
    rows = []
    for a in ("prism_reselect", "prism_fixed", "baseline_sv", *ARMS):
        for metric in ("naive", "ipcw"):
            x = df[f"{a}_auc_{metric}"].dropna(); v = rep[f"{a}_auc_{metric}"]
            r = {"model": a, "metric": metric, "n_splits": len(x), "mean": x.mean(), "sd": x.std(),
                 "p2.5": x.quantile(0.025), "p97.5": x.quantile(0.975), "seed62": v,
                 "pct_rank_seed62": 100 * (x < v).mean()}
            if a not in ("baseline", "baseline_sv"):
                dd = (df[f"{a}_auc_{metric}"] - df[f"baseline_sv_auc_{metric}"]).dropna()
                r.update(frac_beats_baseline=(dd > 0).mean(), mean_delta_vs_baseline=dd.mean())
            rows.append(r)
    s = pd.DataFrame(rows); s.to_csv(OUT / "summary.csv", index=False)
    # seed 62 with CIs (table-2 style)
    pids = set(dict(jobs)[int(rep.seed)])
    te, p = predict(cohort, X, pids)
    d = cohort.iloc[te].reset_index(drop=True)
    preds = {"Baseline ridge": p["baseline"], "Clinical only (ridge)": p["clinical"], "I_scan": p["I_scan"],
             "I_pure": p["I_pure"]}
    boot = cluster_bootstrap(d, preds, 120, reference="Baseline ridge", n_boot=1000).set_index("formulation")
    single = []
    for k, v in preds.items():
        pm, b = point_metrics(d, v, 120), boot.loc[k]
        single.append({"model": k, "n_scans": len(d), "n_patients": d.patient_id.nunique(),
                       "n_pos_naive": int(d.naive_label_120.sum()), "auc_naive": pm["auc_naive"],
                       "auc_ipcw": pm["auc_ipcw"], "auc_ipcw_lo": b.auc_ipcw_lo, "auc_ipcw_hi": b.auc_ipcw_hi,
                       "d_auc_ipcw_vs_baseline": b.get("d_auc_ipcw_vs_Baseline ridge", np.nan),
                       "d_auc_ipcw_lo": b.get("d_auc_ipcw_lo", np.nan), "d_auc_ipcw_hi": b.get("d_auc_ipcw_hi", np.nan)})
    single = pd.DataFrame(single); single.to_csv(OUT / "seed62_single_split.csv", index=False)
    (OUT / "run_info.json").write_text(json.dumps({"n_splits": len(df), "minutes": round((time.time() - t0) / 60, 1),
                                                   "baseline_refit_max_abs_diff_naive": chk,
                                                   "features": {k: list(v.columns) for k, v in X.items()}}, indent=1))
    print(s.round(3).to_string(index=False)); print(single.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
