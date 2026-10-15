"""CFB-GBM: does diffusion (ADC) radiomics at t1 add to conventional radiomics for predicting t1->t2 progression?

ANALYSIS PLAN (pre-specified before any result of this module was seen; also in docs/results/CFB_ADC.md section 1,
snapshot copied to outputs/results/analyses/cfb_adc/PLAN_snapshot.md before the first run. Anything added after the
results is labelled EXPLORATORY in the doc.)

Data: data/cfb-gbm/clinical/ (TCIA CFB-GBM clinical, treatment, MRI availability, RANO v04, PyRadiomics v03 features on
the GTV per patient x timepoint x sequence). No images are used. One row per patient.

Task. Outcome y = (rano_t1_to_t2 == "Progressive Disease (PD)"); patients without a t1->t2 RANO label are dropped
(SD / PR / CR = 0). Predictors are measured at t1 or earlier.
Feature sets:
  (a) clinical: age at t0, male, WHO performance status, who_guideline (2021 vs 2016), RT dose (Gy), fractions,
      delay t0 -> RT (weeks), weeks t0 -> t1 (MRI availability `time_diff_t0` at t1)
  (b) (a) + GTV volume at t1 (log1p cm3, RANO table size_t1) + change t0 -> t1 (log1p(size_t1) - log1p(size_t0))
  (c) (b) + conventional radiomics at t1: t1gd and flair `original_*` first-order + texture features, plus the GTV
      shape features once (taken from the t1gd row; the mask is shared across sequences)
  (d) (c) + ADC `original_*` first-order + texture features at t1
Cohorts: conv = labelled patients with t1gd AND flair features at t1; adc = conv patients with ADC features at t1.
Contrasts: PRIMARY (d) vs (c) on the adc cohort. Secondary: (c) vs (b) and (b) vs (a) on the conv cohort; all four sets
are also reported on the adc cohort.
Learner (all fitted inside the outer training fold): non-radiomics block -> median impute (+ missingness indicators) ->
standardise. Each radiomics block (conventional; ADC separately) -> QuantileClip(1%) (c3_radiomics) -> median impute ->
variance filter (VarianceThreshold 1e-8) -> standardise -> top-k univariate F (k in {5, 10}; the same k for both
blocks). Concatenate -> L2 ("ridge") logistic regression, C in {0.01, 0.03, 0.1, 0.3, 1, 3}. k and C are chosen by
inner stratified 3-fold CV AUC on the training fold (ties -> smaller k, smaller C).
Evaluation: repeated stratified 5-fold CV, 20 repeats (RepeatedStratifiedKFold, random_state 0; identical splits for
every feature set within a cohort, so contrasts are paired). AUC = mean over repeats of each repeat's pooled-OOF ROC AUC.
95% CIs: patient bootstrap (1000 draws; every repeat of every model evaluated on the same draw -> paired ΔAUC).
Permutation test for the primary contrast only: the whole ADC feature row is moved between patients (base features,
conventional radiomics, outcome and splits unchanged), (d) is refitted; p = (1 + #{Δ_perm >= Δ_obs}) / (1 + n_perm),
n_perm = 1000 (fewer only if run time forces it; the number used is recorded).
Reported per contrast: n patients, n events. Power caveat from the bootstrap SE of Δ (minimal detectable Δ at 80% power,
two-sided 5%: ~2.8 x SE).
PRE-SPECIFIED RULE: ADC "helps" if Δ(d - c) >= 0.03 with the bootstrap 95% CI excluding 0. Otherwise "not shown".
Caveats stated in the doc: no IDH / MGMT; the label is volumetric RANO from the GTV (partly circular for the volume
and shape features, whose t1 value is the denominator of the t1->t2 change); t1 lies ~6-8 weeks after RT
(pseudoprogression window), so a "PD" t1->t2 can be the resolution of an early increase, or a late pseudoprogression.

    python -m prism cfbadc [--workers 32] [--n-boot 1000] [--n-perm 1000] [--repeats 20]
    -> $PRISM_OUTPUTS/results/analyses/cfb_adc/{cohort.csv, results.csv, permutation.csv, chosen.csv, oof_<cohort>.csv.gz,
       rule.json, run_info.json}
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
from sklearn.base import clone
from sklearn.feature_selection import SelectKBest, VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from prism.config import DATA, RESULTS
from prism.experiments.c3_radiomics import QuantileClip, f_classif_quiet

SRC = DATA / "cfb-gbm" / "clinical"
OUT = RESULTS / "analyses" / "cfb_adc"
PD = "Progressive Disease (PD)"
KS = (5, 10)
CS = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)
SETS = ("a", "b", "c", "d")
PRIMARY = ("adc", "d", "c")
SECONDARY = (("conv", "c", "b"), ("conv", "b", "a"))
RULE_MIN_DELTA = 0.03


# ---------------------------------------------------------------- data
def _tsv(name):
    return pd.read_csv(next(SRC.glob(name)), sep="\t", low_memory=False)


@lru_cache(maxsize=1)
def load():
    """One row per labelled patient: y, clinical, volume, and the radiomics blocks at t1 (NaN rows if unavailable)."""
    clin = _tsv("CFB-GBM_clinical_data_*.tsv").set_index("id_patient")
    trt = _tsv("CFB-GBM_treatment_data_*.tsv").set_index("id_patient")
    mri = _tsv("CFB-GBM_mri_availability_*.tsv")
    rano = _tsv("CFB-GBM_rano_criteria_*.tsv").set_index("id_patient")
    rad = _tsv("CFB_GBM_features_extraction_pyradiomics_*.tsv")
    lab = rano["rano_t1_to_t2"].dropna()
    pid = lab.index
    y = lab.str.strip().eq(PD).astype(int)
    weeks_t1 = mri[mri.temporality == "t1"].set_index("id_patient")["time_diff_t0 (weeks)"]
    A = pd.DataFrame({
        "age": clin["age_at_t0 (years)"], "male": clin["gender"].eq("M").astype(float),
        "who_ps": clin["who_performance_status"], "who_2021": clin["who_guideline"].eq(2021).astype(float),
        "dose_gy": trt["dose (Gy)"], "fractions": trt["fractions_number"],
        "delay_to_rt_weeks": trt["delay_t0_to_radiotherapy (weeks)"], "weeks_t0_t1": weeks_t1}).reindex(pid)
    s0, s1 = rano["size_t0 (cm3)"].reindex(pid), rano["size_t1 (cm3)"].reindex(pid)
    B = pd.DataFrame({"log_gtv_t1": np.log1p(s1), "dlog_gtv_t0_t1": np.log1p(s1) - np.log1p(s0)})
    feat = [c for c in rad.columns if c.startswith("original_")]
    shape = [c for c in feat if c.startswith("original_shape_")]
    tex = [c for c in feat if c not in shape]
    r1 = rad[rad.Temporality == "t1"]
    block = lambda seq, cols, pre: (r1[r1.Sequence == seq].set_index("Patient")[cols].apply(pd.to_numeric, errors="coerce")
                                    .add_prefix(pre).reindex(pid))
    conv = pd.concat([block("t1gd", shape, "shape_"), block("t1gd", tex, "t1gd_"), block("flair", tex, "flair_")], axis=1)
    adc = block("adc", tex, "adc_")
    has = lambda seq: pd.Series(pid.isin(r1[r1.Sequence == seq].Patient), index=pid)
    meta = pd.DataFrame({"y": y, "has_t1gd": has("t1gd"), "has_flair": has("flair"), "has_adc": has("adc"),
                         "rano_t1_to_t2": lab})
    meta["conv"] = meta.has_t1gd & meta.has_flair
    meta["adc"] = meta.conv & meta.has_adc
    return meta, A, B, conv, adc


def cohort(name):
    meta, A, B, conv, adc = load()
    k = meta[name].to_numpy()
    r = lambda d: d[k].reset_index(drop=True)
    return r(meta), r(A), r(B), r(conv), r(adc)


# ---------------------------------------------------------------- model
BASE_PRE = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())])


def rad_pre(k):
    return Pipeline([("clip", QuantileClip(0.01)), ("imp", SimpleImputer(strategy="median", keep_empty_features=True)),
                     ("var", VarianceThreshold(1e-8)), ("sc", StandardScaler()),
                     ("sel", SelectKBest(f_classif_quiet, k=k))])


def blocks(fs, A, B, conv, adc):
    base = A if fs == "a" else pd.concat([A, B], axis=1)
    rads = {"a": [], "b": [], "c": [conv], "d": [conv, adc]}[fs]
    return base.to_numpy(float), [r.to_numpy(float) for r in rads]


def fit_predict(base, rads, y, tr, te, k, C):
    bp = clone(BASE_PRE).fit(base[tr])
    Xtr, Xte = [bp.transform(base[tr])], [bp.transform(base[te])]
    for R in rads:
        sp = rad_pre(min(k, R.shape[1])).fit(R[tr], y[tr])
        Xtr.append(sp.transform(R[tr]))
        Xte.append(sp.transform(R[te]))
    m = LogisticRegression(C=C, max_iter=5000).fit(np.hstack(Xtr), y[tr])
    return m.predict_proba(np.hstack(Xte))[:, 1]


def tuned_predict(base, rads, y, tr, te, seed):
    grid = [(k, C) for k in (KS if rads else (None,)) for C in CS]
    inner = list(StratifiedKFold(3, shuffle=True, random_state=seed).split(tr, y[tr]))
    score = {}
    for k, C in grid:
        score[(k, C)] = np.mean([roc_auc_score(y[tr][b], fit_predict(base, rads, y, tr[a], tr[b], k, C))
                                 for a, b in inner])
    best = max(grid, key=lambda g: score[g])  # first maximum: smaller k, smaller C
    return fit_predict(base, rads, y, tr, te, *best), best


def splits(y, repeats):
    out = np.zeros((repeats, len(y)), int)
    for i, (_, te) in enumerate(RepeatedStratifiedKFold(n_splits=5, n_repeats=repeats, random_state=0).split(y, y)):
        out[i // 5, te] = i % 5
    return out


def run_cv(base, rads, y, ids):
    oof, chosen = np.zeros(ids.shape), []
    for r, f in enumerate(ids):
        for k in range(5):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            oof[r, te], best = tuned_predict(base, rads, y, tr, te, seed=1000 * r + k)
            chosen.append((r, k, *best))
    return oof, chosen


def job_set(job):
    coh, fs, repeats = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    meta, A, B, conv, adc = cohort(coh)
    y = meta.y.to_numpy()
    oof, chosen = run_cv(*blocks(fs, A, B, conv, adc), y, splits(y, repeats))
    return job, oof, chosen


def job_perm(job):
    seed, repeats = job
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    meta, A, B, conv, adc = cohort(PRIMARY[0])
    y = meta.y.to_numpy()
    perm = np.random.default_rng(seed).permutation(len(y))
    base, (Rc, Ra) = blocks("d", A, B, conv, adc)
    oof, _ = run_cv(base, [Rc, Ra[perm]], y, splits(y, repeats))
    return seed, mean_auc(y, oof)


# ---------------------------------------------------------------- evaluation
def mean_auc(y, P):
    return float(np.mean([roc_auc_score(y, p) for p in np.atleast_2d(P)]))


def bootstrap(y, oofs, n_boot, seed=0):
    """Patient bootstrap of the mean-over-repeats AUC; all models on the same draws (paired)."""
    rng = np.random.default_rng(seed)
    names = list(oofs)
    draws = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() == y[i].max():
            continue
        draws.append([mean_auc(y[i], oofs[k][:, i]) for k in names])
    return names, np.array(draws)


def summarise(coh, oofs, n_boot):
    meta = cohort(coh)[0]
    y = meta.y.to_numpy()
    names, D = bootstrap(y, oofs, n_boot)
    point = {k: mean_auc(y, oofs[k]) for k in names}
    rows = []
    for i, k in enumerate(names):
        aucs = [roc_auc_score(y, p) for p in oofs[k]]
        row = {"cohort": coh, "n_patients": len(y), "n_events": int(y.sum()), "set": k, "auc": point[k],
               "auc_lo": np.percentile(D[:, i], 2.5), "auc_hi": np.percentile(D[:, i], 97.5),
               "auc_repeat_sd": float(np.std(aucs)), "n_boot_ok": len(D),
               "brier": float(np.mean([np.mean((p - y) ** 2) for p in oofs[k]]))}
        prev = {"b": "a", "c": "b", "d": "c"}.get(k)
        for ref in [r for r in (prev, "a") if r is not None and r != k]:
            j = names.index(ref)
            d = D[:, i] - D[:, j]
            row.update({f"d_vs_{ref}": point[k] - point[ref], f"d_vs_{ref}_lo": np.percentile(d, 2.5),
                        f"d_vs_{ref}_hi": np.percentile(d, 97.5), f"d_vs_{ref}_se": float(np.std(d)),
                        f"d_vs_{ref}_mde80": 2.8 * float(np.std(d))})
        rows.append(row)
    return rows


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism cfbadc", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--n-perm", type=int, default=1000)
    ap.add_argument("--repeats", type=int, default=20)
    a = ap.parse_args(argv)
    t0 = time.time()
    warnings.filterwarnings("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    meta = load()[0]
    meta.to_csv(OUT / "cohort.csv")
    cnt = {c: {"n_patients": int(meta[c].sum()), "n_events": int(meta.y[meta[c]].sum())} for c in ("conv", "adc")}
    cnt["labelled"] = {"n_patients": len(meta), "n_events": int(meta.y.sum())}
    print(json.dumps(cnt), flush=True)

    jobs = [(c, fs, a.repeats) for c in ("adc", "conv") for fs in SETS]
    with ProcessPoolExecutor(a.workers) as ex:
        futs = [ex.submit(job_set, j) for j in jobs]
        perm_f = [ex.submit(job_perm, (s, a.repeats)) for s in range(a.n_perm)]
        res = [f.result() for f in futs]
        print(f"sets done {time.time() - t0:.0f}s", flush=True)
        perm = dict(f.result() for f in perm_f)
    oofs = {c: {fs: o for (cc, fs, _), o, _ in res if cc == c} for c in ("adc", "conv")}
    pd.DataFrame([{"cohort": c, "set": fs, "repeat": r, "fold": k, "k": kk, "C": C}
                  for (c, fs, _), _, ch in res for r, k, kk, C in ch]).to_csv(OUT / "chosen.csv", index=False)
    for c, o in oofs.items():
        pd.concat([pd.DataFrame(v.T, columns=[f"{fs}#r{r}" for r in range(len(v))]) for fs, v in o.items()], axis=1
                  ).assign(y=cohort(c)[0].y).to_csv(OUT / f"oof_{c}.csv.gz", index=False)
    rows = [r for c in ("adc", "conv") for r in summarise(c, oofs[c], a.n_boot)]
    table = pd.DataFrame(rows)
    table.to_csv(OUT / "results.csv", index=False)

    coh, k1, k0 = PRIMARY
    y = cohort(coh)[0].y.to_numpy()
    obs = mean_auc(y, oofs[coh][k1]) - mean_auc(y, oofs[coh][k0])
    null = np.array([perm[s] for s in sorted(perm)]) - mean_auc(y, oofs[coh][k0])
    p = (1 + (null >= obs).sum()) / (1 + len(null))
    pd.DataFrame({"seed": sorted(perm), "d_auc_perm": null}).assign(d_auc_obs=obs, p_value=p).to_csv(
        OUT / "permutation.csv", index=False)
    pr = table[(table.cohort == coh) & (table.set == k1)].iloc[0]
    rule = {"rule": "ADC helps if AUC(d) - AUC(c) >= 0.03 with the bootstrap 95% CI excluding 0 (adc cohort)",
            "d_auc": pr.d_vs_c, "lo": pr.d_vs_c_lo, "hi": pr.d_vs_c_hi, "perm_p": p, "n_perm": len(null),
            "n_patients": int(pr.n_patients), "n_events": int(pr.n_events),
            "met": bool(pr.d_vs_c >= RULE_MIN_DELTA and pr.d_vs_c_lo > 0), "counts": cnt}
    (OUT / "rule.json").write_text(json.dumps(rule, indent=1, default=float))
    (OUT / "run_info.json").write_text(json.dumps({"argv": vars(a), "seconds": round(time.time() - t0)}, indent=1))
    print(table.round(3).to_string(index=False))
    print(json.dumps(rule, indent=1, default=float))
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
