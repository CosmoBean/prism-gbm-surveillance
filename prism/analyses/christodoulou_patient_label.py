"""EXPLORATORY: the Christodoulou-style pipeline with THEIR patient-level label (not pre-specified).

Source check 2026-10-26 (docs/results/CHRISTODOULOU_REPLICATION.md): their code labels every timepoint of a patient
y = 1 if "Time to First Progression (Days)" is non-missing for the patient, else 0, after restricting the clinical
table to Primary Diagnosis == "GBM"; their test set is 30 random patients. Their merge is a left join on the radiomics
table, so non-GBM patients stay in the data with a missing progression time, i.e. labelled 0.

Populations (all MU scans with all four sequences, a mask and v2 radiomics; every timepoint):
  gbm        Primary Diagnosis == "GBM" only (the stated intent); y = progressor.
  as_coded   all patients (what the left join produces); y = GBM and progressor.
Arms (same rows, same folds):
  CH      v2 radiomics -> 256 by |AUC - 0.5| -> LightGBM + Optuna (40 trials) + Platt (christodoulou_replication.fit_ch)
  C0      clinical: age, sex, IDH mutant / unknown, MGMT methylated / unknown (L2 logistic regression)
  FU      follow-up only: log number of the patient's scans, log days from diagnosis to the patient's last MRI
  C0_FU   C0 + FU (leakage check: FU uses the patient's whole future)
Evaluation: (a) 5 x 5 patient-grouped stratified CV (seeds 0-4), pooled OOF AUC, mean over repeats, patient-cluster
bootstrap; subsets of positives by timing relative to progression; (b) 100 random 30-test-patient single splits.

    PYTHONPATH=. OMP_NUM_THREADS=1 .venv/bin/python -m prism.analyses.christodoulou_patient_label [--workers 8]
    -> $PRISM_OUTPUTS/results/analyses/christodoulou/patient_label/
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
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

from prism.analyses import detection as D
from prism.analyses.christodoulou_replication import OUT as CH_OUT, brier, fit_ch
from prism.config import RADIOMICS

OUT = CH_OUT / "patient_label"
POPS = ("gbm", "as_coded")
N_REP, N_FOLD, N_SPLITS, N_TEST_PATIENTS = 5, 5, 100, 30
ARMS = ("CH", "C0", "FU", "C0_FU")
CONTRASTS = [("CH", "C0"), ("CH", "C0_FU"), ("CH", "FU"), ("C0_FU", "C0")]


@lru_cache(maxsize=2)
def data(pop: str):
    from prism.data.mu import idh_status, load_index, mgmt_status
    ix = load_index()
    R = pd.read_csv(RADIOMICS).set_index("scan_id").astype(float)
    ix = ix[ix.complete.astype(bool) & ix.scan_id.isin(R.index[~R.isna().all(1)])].reset_index(drop=True)
    gbm = ix.clinical_primary_diagnosis.eq("GBM")
    if pop == "gbm":
        ix, gbm = ix[gbm].reset_index(drop=True), gbm[gbm].reset_index(drop=True)
    ttp = pd.to_numeric(ix.clinical_time_to_first_progression_days, errors="coerce")
    y = (ttp.notna() & gbm).astype(int).to_numpy()
    day = pd.to_numeric(ix.days_from_diagnosis_to_mri, errors="coerce")
    idh, mgmt = idh_status(ix.clinical_idh1_mutation, ix.clinical_idh2_mutation), mgmt_status(
        ix.clinical_mgmt_methylation)
    age = pd.to_numeric(ix.clinical_age_at_diagnosis, errors="coerce")
    C0 = pd.DataFrame({"age": age.fillna(age.median()), "male": ix.clinical_sex_at_birth.eq("Male").astype(float),
                       "idh_mutant": idh.eq("mutant").astype(float), "idh_unknown": idh.eq("unknown").astype(float),
                       "mgmt_methylated": mgmt.eq("methylated").astype(float),
                       "mgmt_unknown": mgmt.eq("unknown").astype(float)})
    g = ix.groupby("patient_id")
    FU = pd.DataFrame({"log_n_scans": np.log(g.scan_id.transform("size").to_numpy(float)),
                       "log_days_dx_to_last_mri": np.log1p(day.groupby(ix.patient_id).transform("max")
                                                           .clip(lower=0).fillna(0).to_numpy())})
    timing = np.select([ttp.isna() | ~gbm, day.isna(), day < ttp - 180, day < ttp],
                       ["neg", "day_unknown", "pre_gt180", "pre_le180"], "post")
    meta = pd.DataFrame({"patient_id": ix.patient_id, "y": y, "timing": timing, "day": day, "ttp": ttp})
    designs = {"C0": C0, "FU": FU, "C0_FU": pd.concat([C0, FU], axis=1)}
    return meta, R.reindex(ix.scan_id).to_numpy(), designs


def fit_lr(X, y, tr, te):
    sc = StandardScaler().fit(X[tr])
    return LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(X[tr]), y[tr]).predict_proba(
        sc.transform(X[te]))[:, 1]


def folds(meta, r):
    f = np.full(len(meta), -1)
    for k, (_, te) in enumerate(StratifiedGroupKFold(N_FOLD, shuffle=True, random_state=r).split(
            meta, meta.y, meta.patient_id)):
        f[te] = k
    return f


def job(j):
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    kind, pop, a, b = j
    meta, R, X = data(pop)
    y, g = meta.y.to_numpy().astype(float), meta.patient_id.to_numpy()
    if kind == "cv":
        f = folds(meta, a)
        tr, te = np.where(f != b)[0], np.where(f == b)[0]
    else:  # single split, seed a: 30 random test patients (all their timepoints)
        test_p = np.random.default_rng(a).choice(np.unique(g), N_TEST_PATIENTS, replace=False)
        tr, te = np.where(~np.isin(g, test_p))[0], np.where(np.isin(g, test_p))[0]
    try:
        raw, cal, best, inner = fit_ch(R, y, g, tr, te, seed=a)
    except ValueError:  # an inner tuning fold with one class (all Optuna trials NaN): split dropped, counted
        assert kind == "split"
        return j, te, None, None, np.nan, None
    ref = {k: fit_lr(v.to_numpy(), y.astype(int), tr, te) for k, v in X.items()}
    return j, te, raw, cal, inner, ref


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 250)
    desc = []
    for pop in POPS:
        meta = data(pop)[0]
        pp = meta.groupby("patient_id").y.max()
        desc.append({"population": pop, "scans": len(meta), "patients": len(pp), "pos_patients": int(pp.sum()),
                     "pos_scans": int(meta.y.sum()), **meta.timing.value_counts().add_prefix("scans_").to_dict(),
                     "scans_per_patient_pos": meta[meta.y == 1].groupby("patient_id").size().mean(),
                     "scans_per_patient_neg": meta[meta.y == 0].groupby("patient_id").size().mean()})
    desc = pd.DataFrame(desc)
    desc.to_csv(OUT / "cohort.csv", index=False)
    print(desc.round(2).to_string(index=False), flush=True)

    jobs = ([("cv", p, r, k) for p in POPS for r in range(N_REP) for k in range(N_FOLD)]
            + [("split", p, s, 0) for p in POPS for s in range(N_SPLITS)])
    with ProcessPoolExecutor(a.workers) as ex:
        results = list(ex.map(job, jobs, chunksize=1))
    print(f"fits {time.time() - t0:.0f}s", flush=True)

    auc_rows, con_rows, br_rows, sp_rows, summ = [], [], [], [], []
    for pop in POPS:
        meta = data(pop)[0]
        y, g, tm = meta.y.to_numpy(), meta.patient_id.to_numpy(), meta.timing.to_numpy()
        P = {k: np.full((N_REP, len(meta)), np.nan) for k in ("CH", "CHraw", *ARMS[1:])}
        inner = []
        for (kind, p, r, k), te, raw, cal, inn, ref in results:
            if kind == "cv" and p == pop:
                P["CH"][r, te], P["CHraw"][r, te] = cal, raw
                for kk, v in ref.items():
                    P[kk][r, te] = v
                inner.append(inn)
        assert all(np.isfinite(v).all() for v in P.values())
        neg = tm == "neg"
        subsets = {"pos_pre_progression": neg | np.isin(tm, ["pre_gt180", "pre_le180"]),
                   "pos_pre_gt180d": neg | (tm == "pre_gt180"), "pos_pre_le180d": neg | (tm == "pre_le180"),
                   "pos_at_or_after_progression": neg | (tm == "post")}
        oofs = {k: P[k] for k in ARMS}
        pt, dr = D.bootstrap(y, oofs, g, a.n_boot, seed=20261026, subsets=subsets)
        for sn in ["all", *subsets]:
            m = subsets.get(sn, np.ones(len(y), bool))
            row = {"population": pop, "set": sn, "n_pos": int(y[m].sum()), "n_neg": int((y[m] == 0).sum()),
                   "patients": len(np.unique(g[m]))}
            for k in ARMS:
                lo, hi = D.ci(dr[(k, sn)])
                row |= {k: pt[(k, sn)], f"{k}_lo": lo, f"{k}_hi": hi}
            auc_rows.append(row)
            for x1, x2 in CONTRASTS:
                lo, hi = D.ci(dr[(x1, sn)] - dr[(x2, sn)])
                con_rows.append({"population": pop, "set": sn, "contrast": f"{x1}-{x2}",
                                 "diff": pt[(x1, sn)] - pt[(x2, sn)], "lo": lo, "hi": hi})
        # patient-level summary score (mean OOF over the patient's scans), the estimand the label implies
        pm = pd.DataFrame({"g": g, "y": y, **{k: P[k].mean(0) for k in ARMS}}).groupby("g").mean()
        auc_rows.append({"population": pop, "set": "patient_mean_score", "n_pos": int(pm.y.sum()),
                         "n_neg": int((pm.y == 0).sum()), "patients": len(pm),
                         **{k: roc_auc_score(pm.y, pm[k]) for k in ARMS}})
        br_rows.append({"population": pop, "prevalence": y.mean(), "brier_raw": np.mean(
            [brier(y, P["CHraw"][r]) for r in range(N_REP)]), "brier_platt": np.mean(
            [brier(y, P["CH"][r]) for r in range(N_REP)]), "mean_inner_auc": np.mean(inner),
            "sd_repeat_CH": np.std(D.aucs(y, P["CH"]), ddof=1)})
        pd.DataFrame({"y": y, "timing": tm, **{f"{k}#r{r}": P[k][r] for k in P for r in range(N_REP)}}).to_csv(
            OUT / f"oof_{pop}.csv.gz", index=False)
        for (kind, p, s, _), te, raw, cal, inn, ref in results:
            if kind == "split" and p == pop:
                if raw is None:
                    sp_rows.append({"population": pop, "seed": s, "failed_inner_one_class": True})
                    continue
                yy = y[te]
                sp_rows.append({"population": pop, "seed": s, "n_test_scans": len(te), "n_pos": int(yy.sum()),
                                "auc_CH": roc_auc_score(yy, raw), **{f"auc_{k}": roc_auc_score(yy, v)
                                                                     for k, v in ref.items()},
                                "brier_raw": brier(yy, raw), "brier_platt": brier(yy, cal), "inner_auc": inn})
        sp = pd.DataFrame([r for r in sp_rows if r["population"] == pop and "auc_CH" in r])
        for c in [c for c in sp.columns if c.startswith(("auc_", "brier_", "n_"))]:
            x = sp[c]
            summ.append({"population": pop, "metric": c, "n_splits": len(x), "mean": x.mean(), "sd": x.std(), "p2.5": x.quantile(.025),
                         "p97.5": x.quantile(.975), "min": x.min(), "max": x.max(),
                         "share_ge_0.80": (x >= 0.80).mean()})
    for name, rows in [("auc", auc_rows), ("contrasts", con_rows), ("brier", br_rows), ("splits", sp_rows),
                       ("splits_summary", summ)]:
        pd.DataFrame(rows).to_csv(OUT / f"{name}.csv", index=False)
    (OUT / "run_info.json").write_text(json.dumps({"argv": vars(a), "seconds": round(time.time() - t0),
                                                   "n_rep": N_REP, "n_splits": N_SPLITS,
                                                   "n_test_patients": N_TEST_PATIENTS}, indent=1))
    for name in ("auc", "contrasts", "brier", "splits_summary"):
        print(pd.read_csv(OUT / f"{name}.csv").round(3).to_string(index=False))
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
