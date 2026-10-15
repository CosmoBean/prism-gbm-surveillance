"""Clean-label test: is the documented-progression label the bottleneck for imaging?

ANALYSIS PLAN (pre-specified before any result of this module was seen; also in docs/results/CLEAN_LABEL.md section 1,
snapshot copied to outputs/results/analyses/clean_label/PLAN_snapshot.md before the first run. Anything added after the
results is labelled EXPLORATORY in the doc.)

Motivation. On MU-Glioma-Post, clinical + timing + treatment (ridge) reaches IPCW AUC(120 d) ~0.70 and conventional-MRI
imaging adds nothing. MU's endpoint is documented first progression of any type: 1 = imaging criteria, 2 = clinical
findings only, 3 = both (clinical workbook `Type of 1st progression`, read here from mu_index.csv
`clinical_type_of_1st_progression`; the existing label pipeline (prism/data/mu.py, FIX_LABELS.md) does NOT use the type:
every progressor is an event). A clinical-only progression cannot be seen on the images, so it may dilute imaging signal.

A. MU imaging-defined endpoint (label "imaging"). Same cohort, same scans, same horizon H = 120 d. Progression of type 1
   or 3 = event exactly as now. Type 2 (clinical only): NOT an event; the scan is censored at the progression date
   (time_to_event = days from scan to progression, event = 0; label_H = 0 if that date is >= H after the scan, else NaN).
   Non-progressors are unchanged. Every progressor must carry type 1/2/3 (asserted). Reference: the current label
   ("original") with the same models, so the effect of the relabelling is visible.
B. Feature sets (features.tabular): clinical (age, sex, IDH, MGMT + unknown flags) | baseline = clinical + timing +
   treatment | imaging = volumes + delta (compartment volumes + past-only change) | baseline+imaging.
C. Learners as in the phase ladder: ridge (formulations.fit on verified labels, via c3.fit_predict) primary; C3 GBM
   secondary. Populations: grade 4 primary, all gliomas secondary. Cohorts: full and post_rt (RT completed, defined
   exactly as in analyses.phase_ladder; patients keep their fold).
D. Evaluation: shared 5x5 repeated patient-grouped folds (outputs/data/folds.csv; stratified on the original 120-d status,
   kept unchanged so every arm sees the same splits). IPCW AUC(120 d) = mean over repeats of each repeat's pooled-OOF AUC
   (metrics.evaluate_repeated), censoring weights computed from the label's own event/time; paired patient-cluster
   bootstrap (1000) of ΔAUC vs the baseline and vs clinical (same label, learner, cohort, population).
E. PRE-SPECIFIED RULE. "The label is the bottleneck" is SUPPORTED if, on the imaging-defined endpoint, grade 4, full
   cohort, ridge, imaging-only OR baseline+imaging beats the baseline by ΔAUC >= 0.03 with the paired cluster-bootstrap
   95% CI excluding 0. Otherwise NOT SUPPORTED. Everything else (post_rt, all gliomas, GBM, original label, LUMIERE) is
   secondary; no multiplicity correction (two chances inside the rule itself are noted, not corrected).
F. LUMIERE. prism/data/lumiere.py already defines the label from the expert RANO ratings (event = first rating of PD
   within 120 d of the index scan; death censors), i.e. the requested expert-RANO forward label is the existing label.
   So instead: imaging vs clinical within LUMIERE-only CV. Feature sets (shared definitions, features.tabular
   SHARED): clinical | clinical + timing (log days since surgery, rater's <3-months-after-RT flag; LUMIERE has no
   treatment dates, so this is the baseline analogue) | imaging = DeepBraTumIA volumes (ET, necrosis/cavity, oedema)
   + delta vs the previous post-operative study (week >= 1) of the same patient with a usable segmentation (has_prior,
   log1p days since prior, log ratios of the three compartments and of their sum) | clinical + timing + imaging.
   Ridge primary, GBM secondary; 5x5 patient-grouped LUMIERE folds (external_lumiere.lumiere_fold_ids); same estimator
   and bootstrap as MU. Small n (61 patients): CIs reported, descriptive only.

    python -m prism cleanlabel [--workers 32] [--n-boot 1000]
    -> $PRISM_OUTPUTS/results/analyses/clean_label/{counts.csv, results.csv, lumiere_results.csv, rule.json,
       oof_repeats_<label>_<pop>_<cohort>.csv.gz, lumiere_oof_repeats.csv.gz, run_info.json}
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
from threadpoolctl import threadpool_limits

from prism.analyses import phase_ladder as pl
from prism.config import HORIZONS, RESULTS
from prism.data.mu import horizon_label, load_index
from prism.experiments import c3_radiomics as c3
from prism.models.metrics import counted_warnings, evaluate_repeated

H = c3.H
OUT = RESULTS / "analyses" / "clean_label"
LABELS = ("imaging", "original")
POPS = ("grade4", "all_glioma")
COHORTS = ("full", "post_rt")
LEARNERS = ("ridge", "gbm")
SETS = {"clinical": ("clinical",), "baseline": ("clinical", "timing", "treatment"), "imaging": ("volumes", "delta"),
        "baseline+imaging": ("clinical", "timing", "treatment", "volumes", "delta")}
PRIMARY = ("imaging", "grade4", "full", "ridge")
RULE_MIN_DELTA = 0.03


# ---------------------------------------------------------------- labels
@lru_cache(maxsize=1)
def progression_type() -> pd.Series:
    """MU type of first progression per patient: 1 imaging, 2 clinical only, 3 both, 0/NaN no progression."""
    idx = load_index().drop_duplicates("patient_id").set_index("patient_id")
    return pd.to_numeric(idx["clinical_type_of_1st_progression"], errors="coerce")


def relabel(cohort: pd.DataFrame, label: str) -> pd.DataFrame:
    """`original`: unchanged. `imaging`: clinical-only (type 2) progressions censored at their progression date."""
    c = cohort.copy()
    c["progression_type"] = c.patient_id.map(progression_type()).to_numpy()
    prog = c["event"].astype(bool).to_numpy()
    assert c.loc[prog, "progression_type"].isin([1, 2, 3]).all(), "progressor without a type of first progression"
    if label == "original":
        return c
    clin = prog & c["progression_type"].eq(2).to_numpy()
    t_prog = (pd.to_numeric(c["progression_day"]) - pd.to_numeric(c["days_from_diagnosis_to_mri"])).to_numpy(float)
    assert (t_prog[clin] > 0).all()
    c.loc[clin, "event"] = False
    c.loc[clin, "time_to_event"] = np.maximum(t_prog[clin], 0.5)
    for h in HORIZONS:
        c.loc[clin, f"label_{h}"] = horizon_label(np.zeros(clin.sum(), bool), t_prog[clin], t_prog[clin], h)
        c.loc[clin, f"naive_label_{h}"] = 0
    c["clinical_only_censored"] = clin
    return c


@lru_cache(maxsize=16)
def context(label, pop, coh):
    cohort, folds, g, *_ = pl.context(pop, coh)
    return relabel(cohort, label), folds, g


def design(g, name):
    return pd.concat([g[k] for k in SETS[name]], axis=1)


@counted_warnings
def run_mu(job):
    label, pop, coh, name, learner = job
    threadpool_limits(1)
    cohort, folds, g = context(label, pop, coh)
    return job, pl.cv(design(g, name), cohort, folds, learner)


def counts(label, pop, coh):
    c = context(label, pop, coh)[0]
    y = c[f"label_{H}"]
    t = c.progression_type
    return {"label": label, "population": pop, "cohort": coh, "n_scans": len(c), "n_patients": c.patient_id.nunique(),
            "events": int((y == 1).sum()), "non_events": int((y == 0).sum()), "censored": int(y.isna().sum()),
            "patients_with_event": c[y == 1].patient_id.nunique(),
            **{f"events_type{k}": int(((y == 1) & t.eq(k)).sum()) for k in (1, 2, 3)},
            "scans_of_type2_patients": int(t.eq(2).sum()), "patients_type2": c[t.eq(2)].patient_id.nunique()}


# ---------------------------------------------------------------- LUMIERE (within-cohort CV)
@lru_cache(maxsize=1)
def lumiere_features():
    from prism.config import LUMIERE_ROOT
    from prism.data import lumiere
    from prism.experiments.external_lumiere import lumiere_table
    from prism.features.tabular import SHARED
    lc, LX = lumiere_table()
    vols = lumiere.deepbratumia_volumes(LUMIERE_ROOT / "Imaging-v202211.zip")
    vols["patient_id"] = vols.scan_id.str.split("_").str[0]
    vols["day"] = vols.scan_id.str.extract(r"week-(\d+)")[0].astype(float) * 7
    vols = vols[(vols.day >= 7) & vols.filter(like="raw_").notna().all(axis=1)].sort_values(["patient_id", "day"])
    comp = {"et": "raw_Enhancing_Core", "necrosis": "raw_Necrotic_NonEnhancing", "edema": "raw_Edema_Compartment"}
    rows = []
    for t in lc.itertuples():
        prev = vols[(vols.patient_id == t.patient_id) & (vols.day < t.days_since_surgery)]
        cur = vols[vols.scan_id == t.scan_id]
        r = {"has_prior": 0.0, "log_days_since_prior": 0.0, **{f"logratio_{k}": 0.0 for k in (*comp, "total")}}
        if len(prev) and len(cur):
            p, q = prev.iloc[-1], cur.iloc[0]
            r["has_prior"], r["log_days_since_prior"] = 1.0, np.log1p(t.days_since_surgery - p.day)
            for k, col in comp.items():
                r[f"logratio_{k}"] = np.log1p(q[col] / 1000) - np.log1p(p[col] / 1000)
            tot = lambda s: sum(s[c] for c in comp.values()) / 1000
            r["logratio_total"] = np.log1p(tot(q)) - np.log1p(tot(p))
        rows.append(r)
    delta = pd.DataFrame(rows, index=lc.index)
    g = {"clinical": LX[SHARED["clinical"]], "timing": LX[SHARED["timing"]], "volumes": LX[SHARED["volumes"]],
         "delta": delta}
    sets = {"clinical": ("clinical",), "clinical+timing": ("clinical", "timing"), "imaging": ("volumes", "delta"),
            "clinical+timing+imaging": ("clinical", "timing", "volumes", "delta")}
    return lc, {k: pd.concat([g[b] for b in v], axis=1) for k, v in sets.items()}


@counted_warnings
def run_lumiere(job):
    name, learner = job
    threadpool_limits(1)
    from prism.experiments.external_lumiere import lumiere_fold_ids
    lc, X = lumiere_features()
    ids = lumiere_fold_ids(lc, 5)
    oof = np.zeros(ids.shape)
    for r, f in enumerate(ids):
        for k in np.unique(f):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            oof[r, te] = c3.fit_predict(pl.SINGLE(learner), lc, X[name], {}, None, tr, te, seed=r)
    return job, oof


# ---------------------------------------------------------------- main
def evaluate(cohort, oofs, ref, n_boot, meta):
    ev = evaluate_repeated(cohort, oofs, H, reference=ref, n_boot=n_boot).rename(
        columns={f"d_auc_ipcw_vs_{ref}": "d_auc_ipcw"})
    return [{**meta, "model": k.split("|")[0], "reference": ref.split("|")[0], **row.dropna().to_dict()}
            for k, row in ev.iterrows()]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism cleanlabel", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    t0 = time.time()
    warnings.filterwarnings("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    combos = [(l, p, c) for l in LABELS for p in POPS for c in COHORTS]
    pd.DataFrame([counts(*x) for x in combos]).to_csv(OUT / "counts.csv", index=False)

    jobs = [(l, p, c, s, m) for l, p, c in combos for s in SETS for m in LEARNERS]
    ljobs = [(s, m) for s in ("clinical", "clinical+timing", "imaging", "clinical+timing+imaging") for m in LEARNERS]
    with ProcessPoolExecutor(a.workers) as ex:
        futs_l = [ex.submit(run_lumiere, j) for j in ljobs]
        oofs = dict(ex.map(run_mu, jobs))
        loofs = dict(f.result() for f in futs_l)
    print(f"fits done {time.time() - t0:.0f}s", flush=True)

    rows = []
    for l, p, c in combos:
        cohort = context(l, p, c)[0]
        meta = {"label": l, "population": p, "cohort": c, "n_scans": len(cohort),
                "events": int((cohort[f"label_{H}"] == 1).sum()), "censored": int(cohort[f"label_{H}"].isna().sum())}
        mine = {f"{s}|{m}": oofs[(l, p, c, s, m)] for s in SETS for m in LEARNERS}
        pd.concat([pd.DataFrame(o.T, columns=[f"{k}#r{r}" for r in range(len(o))]) for k, o in mine.items()], axis=1
                  ).assign(scan_id=cohort.scan_id).to_csv(OUT / f"oof_repeats_{l}_{p}_{c}.csv.gz", index=False)
        for m in LEARNERS:
            arms = {f"{s}|{m}": mine[f"{s}|{m}"] for s in SETS}
            for ref in ("baseline", "clinical"):
                rows += [{**r, "learner": m} for r in evaluate(cohort, arms, f"{ref}|{m}", a.n_boot, meta)]
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "results.csv", index=False)

    lc = lumiere_features()[0]
    lrows = []
    lmeta = {"cohort": "LUMIERE", "n_scans": len(lc), "n_patients": lc.patient_id.nunique(),
             "events": int((lc[f"label_{H}"] == 1).sum()), "censored": int(lc[f"label_{H}"].isna().sum())}
    for m in LEARNERS:
        arms = {f"{s}|{m}": o for (s, mm), o in loofs.items() if mm == m}
        for ref in ("clinical+timing", "clinical"):
            lrows += [{**r, "learner": m} for r in evaluate(lc, arms, f"{ref}|{m}", a.n_boot, lmeta)]
    pd.DataFrame(lrows).to_csv(OUT / "lumiere_results.csv", index=False)
    pd.concat([pd.DataFrame(o.T, columns=[f"{s}|{m}#r{r}" for r in range(len(o))]) for (s, m), o in loofs.items()],
              axis=1).assign(scan_id=lc.scan_id).to_csv(OUT / "lumiere_oof_repeats.csv.gz", index=False)

    lab, pop, coh, learner = PRIMARY
    q = res[(res.label == lab) & (res.population == pop) & (res.cohort == coh) & (res.learner == learner)
            & (res.reference == "baseline") & res.model.isin(["imaging", "baseline+imaging"])]
    met = {r.model: bool(r.d_auc_ipcw >= RULE_MIN_DELTA and r.d_auc_ipcw_lo > 0) for r in q.itertuples()}
    rule = {"rule": "imaging-only or baseline+imaging beats baseline by >= 0.03 with paired 95% CI excluding 0 "
                    "(imaging-defined endpoint, grade 4, full cohort, ridge)",
            "contrasts": {r.model: {"d_auc": r.d_auc_ipcw, "lo": r.d_auc_ipcw_lo, "hi": r.d_auc_ipcw_hi}
                          for r in q.itertuples()},
            "supported": any(met.values())}
    (OUT / "rule.json").write_text(json.dumps(rule, indent=1, default=float))
    (OUT / "run_info.json").write_text(json.dumps({"argv": vars(a), "seconds": round(time.time() - t0)}, indent=1))
    show = ["label", "population", "cohort", "learner", "reference", "model", "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi",
            "d_auc_ipcw", "d_auc_ipcw_lo", "d_auc_ipcw_hi", "cal_slope"]
    print(res[res.reference.eq("baseline")][show].round(3).to_string(index=False))
    print(pd.DataFrame(lrows)[["learner", "reference", "model", "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "d_auc_ipcw",
                               "d_auc_ipcw_lo", "d_auc_ipcw_hi"]].round(3).to_string(index=False))
    print(json.dumps(rule, indent=1, default=float))
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
