"""Phase-of-care ladder: does imaging add value once the phase of care is known, and within post-RT surveillance?

ANALYSIS PLAN (pre-specified before any result of this module was seen; not changed afterwards. Anything added
later is labelled EXPLORATORY in docs/results/PHASE_LADDER.md.)

Motivation. The C3 baseline (clinical + timing + treatment) gets most of its signal from where the scan sits in the
treatment course (SHAP: treatment 55-58%; rt_started / rt_start_day on top). Imaging adds nothing over that baseline.
Hypothesis: imaging adds value when the phase of care is encoded compactly, or within the post-chemoradiation phase.

A. Phase-of-care block (as of the scan; from features.tabular.treatment() and the cohort's days_since_rt_end):
   pre-RT        rt_started == 0 (no RT started by the scan day; includes patients with no RT documented)
   during RT     rt_started == 1 and rt_completed == 0
   early post-RT rt_completed == 1 and days since RT end <= 84 (EARLY_POST_RT_DAYS, the early_post_rt definition)
   later post-RT rt_completed == 1 and days since RT end > 84 (reference level)
   Encoded as 3 dummies (phase_pre_rt, phase_during_rt, phase_early_post_rt) + log1p(days since RT end), 0 when RT has
   not been completed. RT dates unknown: handled exactly as treatment() does. RT documented without a start date ->
   started before the scan; without an end date -> never "completed" -> during RT (no days-since-end). rt_completed
   implies a known end day <= scan day, so days since RT end is never missing/negative for completed RT (asserted).
B. Non-imaging bases: R0 clinical (age, sex, IDH, MGMT with unknown flags) | R1 R0 + timing (current block) |
   R2 R0 + phase | R3 current baseline (R0 + timing + treatment).
   Imaging additions to each base: I0 none | I1 volumes | I2 volumes + morphology + delta (all non-radiomics imaging
   measurements) | I3 radiomics, nested choice over the 70 C3 radiomics configurations (c3.RAD_CONFIGS, incl.
   QuantileClip) with the base swapped in (c3.fit_predict with that base) | I4 (optional, secondary) frozen deep
   features, nested over the 32 D1 configurations of analyses.deep_features. Ridge (formulations.fit, verified labels)
   is primary; C3 GBM is secondary and run for I0-I2 only (I3/I4 nested choices are ridge, as in C3).
C. Cohorts: full (grade 4 primary, all gliomas secondary) | post_rt (RT completed: early + later post-RT) |
   later_post_rt (> 84 d after RT end; sensitivity). Subsets keep each patient's fold from outputs/data/folds.csv;
   models are trained AND evaluated within the subset (inner CV / nested selection also within the subset's training
   rows). Sensitivity (pre-specified): the full-cohort models' OOF predictions evaluated on the subset scans only.
   Counts per cohort: scans, patients, events, verified non-events, censored; events-per-parameter and Riley 2020
   criteria (utility.riley_binary; anticipated R2cs = 15% of max) for the primary contrast's two models.
D. Evaluation as in C3: 5x5 repeated patient-grouped CV, IPCW AUC(120 d) = mean over repeats of each repeat's
   pooled-OOF AUC (metrics.evaluate_repeated), paired patient-cluster bootstrap (1000) of ΔAUC vs the matching base
   (same learner, same cohort), calibration slope and O/E (mean over repeats). 100-permutation patient-level test for
   the primary contrast only: the I2 imaging block is moved between patients with the same number of scans in the
   cohort (whole visit-ordered blocks; base features, outcomes and folds unchanged) -> null of "imaging carries no
   information beyond R2"; p = (1 + #{Δ_perm >= Δ_obs}) / 101.
E. PRIMARY contrast: grade 4, post_rt cohort, ridge, R2 + I2 vs R2. Key secondary: grade 4, post_rt, R2 + I3 vs R2.
   Everything else (other rungs, cohorts, all gliomas, GBM, I1, I4, between-base contrasts R1/R2/R3 vs R0,
   R2 + imaging vs R3) is secondary/descriptive. About 2 pops x 3 cohorts x 4 bases x 4-5 additions x 2 learners
   contrasts are reported; no multiplicity correction, so isolated secondary CIs excluding 0 are not evidence.
F. External: LUMIERE has no RT start/end dates (only the rater's "< 3 months after RT" flag), so the phase block cannot
   be built there; no external run (counts in the doc).

    python -m prism.analyses.phase_ladder [--workers 80] [--n-boot 1000] [--n-perm 100] [--no-deep]
    -> $PRISM_OUTPUTS/results/analyses/phase_ladder/{cohorts.csv, results.csv, rungs.csv, subset_of_full.csv,
       permutation.csv, nested_choices.csv, oof_repeats_<pop>_<cohort>.csv.gz, ladder.png, run_info.json}
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
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits

from prism.config import EARLY_POST_RT_DAYS, RESULTS
from prism.experiments import c3_radiomics as c3
from prism.features.tabular import treatment
from prism.models.metrics import counted_warnings, evaluate_repeated, fast_auc_brier, ipcw_context

H = c3.H
OUT = RESULTS / "analyses" / "phase_ladder"
POPS = ("grade4", "all_glioma")
COHORTS = ("full", "post_rt", "later_post_rt")
BASES = {"R0": ("clinical",), "R1": ("clinical", "timing"), "R2": ("clinical", "phase"),
         "R3": ("clinical", "timing", "treatment")}
IMAGING = {"I0": (), "I1": ("volumes",), "I2": ("volumes", "morphology", "delta")}
NESTED = ("I3", "I4")
PRIMARY = ("grade4", "post_rt", "R2", "I2")
SINGLE = lambda learner: (None, "none", "none", "none", learner)


# ---------------------------------------------------------------- features, cohorts
def phase(cohort: pd.DataFrame) -> pd.DataFrame:
    """Phase of care as of the scan (reference: later post-RT) + log1p(days since RT end), 0 until RT is completed."""
    t = treatment(cohort)
    started, done = t.rt_started.eq(1), t.rt_completed.eq(1)
    d = cohort["days_since_rt_end"]
    assert not (done & ~(d >= 0)).any(), "completed RT without a known, past end day"
    early = done & (d <= EARLY_POST_RT_DAYS)
    return pd.DataFrame({"phase_pre_rt": (~started).astype(float), "phase_during_rt": (started & ~done).astype(float),
                         "phase_early_post_rt": early.astype(float),
                         "log_days_since_rt_end": np.log1p(d.where(done, 0.0))}, index=cohort.index)


def phase_label(cohort):
    p = phase(cohort)
    return np.select([p.phase_pre_rt.eq(1), p.phase_during_rt.eq(1), p.phase_early_post_rt.eq(1)],
                     ["pre_rt", "during_rt", "early_post_rt"], "later_post_rt")


@lru_cache(maxsize=8)
def context(pop: str, cohort_name: str, deep: bool = False):
    """(cohort, folds, feature blocks, radiomics dict, eroded radiomics, deep dict) restricted to the cohort."""
    from prism.features.tabular import groups
    cohort, folds, _, rad, er = c3.load(pop)
    g = groups(cohort, legacy_radiomics=False)
    g["phase"] = phase(cohort)
    lab = phase_label(cohort)
    keep = {"full": np.ones(len(cohort), bool), "post_rt": np.isin(lab, ["early_post_rt", "later_post_rt"]),
            "later_post_rt": lab == "later_post_rt"}[cohort_name]
    sub = lambda df: df[keep].reset_index(drop=True)
    dd = {}
    if deep:
        from prism.analyses import deep_features as dfeat  # also registers the pca30 selector in c3
        for v in sorted({c[0] for c in dfeat.FAMILIES["D1"]}):
            dd[v] = dfeat.deep_block(*v.split(":"), cohort.scan_id).set_axis(cohort.index)
    return (sub(cohort), folds, {k: sub(v) for k, v in g.items()}, {k: sub(v) for k, v in rad.items()}, sub(er),
            {k: sub(v) for k, v in dd.items()})


def design(g, base, img):
    return pd.concat([g[k] for k in BASES[base] + IMAGING.get(img, ())], axis=1)


def nested_configs(fam):
    if fam == "I3":
        return c3.RAD_CONFIGS
    from prism.analyses import deep_features as dfeat
    return dfeat.FAMILIES["D1"]


# ---------------------------------------------------------------- jobs
def cv(X, cohort, folds, learner, rad=None, er=None):
    oof = np.zeros((folds.repeat.nunique(), len(cohort)))
    for r in range(oof.shape[0]):
        f = c3._fold_ids(cohort, folds, r)
        for k in np.unique(f):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            oof[r, te] = c3.fit_predict(SINGLE(learner), cohort, X, rad or {}, er, tr, te, seed=r)
    return oof


@counted_warnings
def run_single(job):
    pop, coh, base, img, learner = job
    threadpool_limits(1)
    cohort, folds, g, *_ = context(pop, coh)
    return job, cv(design(g, base, img), cohort, folds, learner)


def inner_auc(cfg, cohort, X, rad, er, tr):
    """c3.inner_auc, skipping inner folds without both verified classes (small subsets). A configuration that cannot be
    fitted on an inner training set (pca30 with < 30 verified scans in later_post_rt) scores NaN and is never chosen."""
    y = cohort[f"label_{H}"].to_numpy()
    aucs = []
    for a, b in GroupKFold(n_splits=3).split(tr, groups=cohort.patient_id.iloc[tr]):
        try:
            p = c3.fit_predict(cfg, cohort, X, rad, er, tr[a], tr[b])
        except ValueError:
            return np.nan
        k = ~np.isnan(y[tr[b]])
        if len(np.unique(y[tr[b]][k])) == 2:
            aucs.append(roc_auc_score(y[tr[b]][k], p[k]))
    return float(np.mean(aucs)) if aucs else np.nan


@counted_warnings
def run_nested(job):
    pop, coh, base, fam, r, k = job
    threadpool_limits(1)
    cohort, folds, g, rad, er, deep = context(pop, coh, fam == "I4")
    feats, stab = (rad, er) if fam == "I3" else (deep, None)
    X = design(g, base, "I0")
    f = c3._fold_ids(cohort, folds, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    scores = {c: inner_auc(c, cohort, X, feats, stab, tr) for c in nested_configs(fam)}
    best = max(scores, key=lambda c: -np.inf if np.isnan(scores[c]) else scores[c])
    return (pop, coh, base, fam), r, k, te, c3.fit_predict(best, cohort, X, feats, stab, tr, te, seed=r), \
        "|".join(map(str, best)), scores[best]


def permute_blocks(X: pd.DataFrame, cohort: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Move each patient's visit-ordered feature block to another patient with the same number of scans."""
    rng = np.random.default_rng(seed)
    order = cohort.sort_values(["patient_id", "visit_index"]).index
    blocks = {p: list(ix) for p, ix in cohort.loc[order].groupby("patient_id", sort=True).groups.items()}
    by_size = {}
    for p, ix in blocks.items():
        by_size.setdefault(len(ix), []).append(p)
    src = np.arange(len(X))
    for pats in by_size.values():
        for p, q in zip(pats, rng.permutation(pats)):
            src[blocks[p]] = blocks[q]
    return pd.DataFrame(X.to_numpy()[src], columns=X.columns, index=X.index)


def mean_auc(cohort, oof):
    return float(np.mean(fast_auc_brier(ipcw_context(cohort, H), oof)[0]))


@counted_warnings
def run_perm(job):
    seed, = job
    threadpool_limits(1)
    pop, coh, base, img = PRIMARY
    cohort, folds, g, *_ = context(pop, coh)
    Xi = permute_blocks(pd.concat([g[k] for k in IMAGING[img]], axis=1), cohort, seed)
    return seed, mean_auc(cohort, cv(pd.concat([design(g, base, "I0"), Xi], axis=1), cohort, folds, "ridge"))


# ---------------------------------------------------------------- summaries
def cohort_counts(pop, coh):
    from prism.analyses.utility import riley_binary
    cohort, _, g, *_ = context(pop, coh)
    y = cohort[f"label_{H}"]
    ev, ne = int((y == 1).sum()), int((y == 0).sum())
    lab = pd.Series(phase_label(cohort)).value_counts()
    row = {"population": pop, "cohort": coh, "n_scans": len(cohort), "n_patients": cohort.patient_id.nunique(),
           "events": ev, "non_events": ne, "censored": int(y.isna().sum()),
           "patients_with_event": cohort[y == 1].patient_id.nunique(),
           **{f"n_{k}": int(lab.get(k, 0)) for k in ("pre_rt", "during_rt", "early_post_rt", "later_post_rt")}}
    prev = ev / max(ev + ne, 1)
    r2max = 1 - (prev ** prev * (1 - prev) ** (1 - prev)) ** 2
    for name, (base, img) in {"R2": ("R2", "I0"), "R2+I2": ("R2", "I2")}.items():
        p = design(g, base, img).shape[1]
        rl = riley_binary(p, prev, 0.15 * r2max)
        row.update({f"{name}_n_params": p, f"{name}_epp": ev / p, f"{name}_riley_required_n": rl["required_n"],
                    f"{name}_riley_required_events": rl["required_events"]})
    return row


def evaluate(cohort, oofs, ref, n_boot, meta):
    ev = evaluate_repeated(cohort, oofs, H, reference=ref, n_boot=n_boot).rename(
        columns={f"d_auc_ipcw_vs_{ref}": "d_auc_ipcw"})
    return [{**meta, "arm": k, "reference": ref, **row.dropna().to_dict()} for k, row in ev.iterrows()]


def arm(base, img, learner):
    return f"{base}+{img}|{learner}" if img != "I0" else f"{base}|{learner}"


def ladder_plot(res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    r = res[(res.learner == "ridge") & res.table.eq("vs_base")]
    imgs = [i for i in ("I0", "I1", "I2", "I3", "I4") if i in set(r.imaging)]
    colors = dict(zip(imgs, ["#4a4a4a", "#5b8def", "#2a9d8f", "#e76f51", "#9b5de5"]))
    fig, axes = plt.subplots(len(POPS), len(COHORTS), figsize=(13, 7.5), sharey=True, squeeze=False)
    for i, pop in enumerate(POPS):
        for j, coh in enumerate(COHORTS):
            ax = axes[i, j]
            s = r[(r.population == pop) & (r.cohort == coh)]
            for bi, base in enumerate(BASES):
                for ii, img in enumerate(imgs):
                    q = s[(s.base == base) & (s.imaging == img)]
                    if q.empty:
                        continue
                    x = bi + (ii - (len(imgs) - 1) / 2) * 0.16
                    q = q.iloc[0]
                    ax.errorbar(x, q.auc_ipcw, yerr=[[q.auc_ipcw - q.auc_ipcw_lo], [q.auc_ipcw_hi - q.auc_ipcw]],
                                fmt="o", color=colors[img], ms=4, lw=1, capsize=2,
                                label=img if (bi == 0 and i == 0 and j == 0) else None)
            ax.axhline(0.5, color="#999", lw=0.6, ls=":")
            ax.set_xticks(range(len(BASES)), ["R0 clin", "R1 +timing", "R2 +phase", "R3 baseline"], fontsize=8)
            c = s.iloc[0] if len(s) else None
            ax.set_title(f"{pop} · {coh}" + (f"\n{int(c.n_scans)} scans" if c is not None else ""), fontsize=9)
            if j == 0:
                ax.set_ylabel("IPCW AUC(120 d), mean over repeats")
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc="lower center", ncol=len(imgs), fontsize=8,
               title="I0 none · I1 volumes · I2 vol+morph+delta · I3 radiomics (nested) · I4 deep (nested)",
               title_fontsize=8)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism phaseladder", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=80)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--n-perm", type=int, default=100)
    ap.add_argument("--no-deep", action="store_true", help="skip I4 (deep features)")
    ap.add_argument("--populations", nargs="+", default=list(POPS))
    a = ap.parse_args(argv)
    t0 = time.time()
    warnings.filterwarnings("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    fams = ("I3",) if a.no_deep else NESTED
    combos = [(p, c) for p in a.populations for c in COHORTS]
    pd.DataFrame([cohort_counts(p, c) for p, c in combos]).to_csv(OUT / "cohorts.csv", index=False)

    single = [(p, c, b, i, l) for p, c in combos for b in BASES for i in IMAGING for l in ("ridge", "gbm")]
    nested = [(p, c, b, f, r, k) for f in fams for p, c in combos for b in BASES for r in range(5) for k in range(5)]
    perms = [(s,) for s in range(a.n_perm)]
    oofs, choices = {}, []
    with ProcessPoolExecutor(a.workers) as ex:
        futs = [ex.submit(run_nested, j) for j in nested]  # longest jobs first
        futs_p = [ex.submit(run_perm, j) for j in perms]
        for job, o in ex.map(run_single, single):
            oofs[job] = o
        for fu in futs:
            key_, r, k, te, p, chosen, score = fu.result()
            p_, c_, b_, f_ = key_
            n = len(context(p_, c_)[0])
            o = oofs.setdefault((p_, c_, b_, f_, "ridge"), np.zeros((5, n)))
            o[r, te] = p
            choices.append({"population": p_, "cohort": c_, "base": b_, "imaging": f_, "repeat": r, "fold": k,
                            "chosen": chosen, "inner_auc": score})
        perm = dict(fu.result() for fu in futs_p)
    pd.DataFrame(choices).to_csv(OUT / "nested_choices.csv", index=False)
    print(f"fits done {time.time() - t0:.0f}s", flush=True)

    counts = pd.read_csv(OUT / "cohorts.csv").set_index(["population", "cohort"])
    rows, rungs, sub_full = [], [], []
    for p, c in combos:
        cohort = context(p, c)[0]
        meta = {"population": p, "cohort": c, **counts.loc[(p, c)][["n_scans", "n_patients", "events", "censored"]]
                .to_dict()}
        mine = {arm(b, i, l): oofs[(p, c, b, i, l)] for (pp, cc, b, i, l) in oofs if (pp, cc) == (p, c)}
        pd.concat([pd.DataFrame(o.T, columns=[f"{k}#r{r}" for r in range(len(o))]) for k, o in mine.items()], axis=1
                  ).assign(scan_id=cohort.scan_id).to_csv(OUT / f"oof_repeats_{p}_{c}.csv.gz", index=False)
        for l in ("ridge", "gbm"):
            for b in BASES:
                arms = {arm(b, i, l): mine[arm(b, i, l)] for i in list(IMAGING) + list(fams) if arm(b, i, l) in mine}
                rows += [{**r_, "table": "vs_base", "learner": l, "base": b,
                          "imaging": r_["arm"].split("|")[0].partition("+")[2] or "I0"}
                         for r_ in evaluate(cohort, arms, arm(b, "I0", l), a.n_boot, meta)]
            for ref in ("R0", "R2"):
                arms = {arm(b, "I0", l): mine[arm(b, "I0", l)] for b in BASES}
                rungs += [{**r_, "learner": l} for r_ in evaluate(cohort, arms, arm(ref, "I0", l), a.n_boot, meta)]
        # R2 + imaging vs the full baseline R3 (ridge)
        arms = {arm("R3", "I0", "ridge"): mine[arm("R3", "I0", "ridge")],
                **{arm("R2", i, "ridge"): mine[arm("R2", i, "ridge")] for i in ("I0", "I1", "I2") + fams}}
        rungs += [{**r_, "learner": "ridge"} for r_ in evaluate(cohort, arms, arm("R3", "I0", "ridge"), a.n_boot, meta)]
        # sensitivity: full-cohort models evaluated on the subset scans
        if c != "full":
            full = context(p, "full")[0]
            idx = full.scan_id.reset_index().set_index("scan_id").loc[cohort.scan_id, "index"].to_numpy()
            for b in ("R2", "R3"):
                arms = {arm(b, i, "ridge"): oofs[(p, "full", b, i, "ridge")][:, idx] for i in ("I0", "I1", "I2") + fams}
                sub_full += [{**r_, "base": b, "learner": "ridge"}
                             for r_ in evaluate(cohort, arms, arm(b, "I0", "ridge"), a.n_boot, meta)]
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "results.csv", index=False)
    pd.DataFrame(rungs).to_csv(OUT / "rungs.csv", index=False)
    pd.DataFrame(sub_full).to_csv(OUT / "subset_of_full.csv", index=False)

    if perm:
        p, c, b, i = PRIMARY
        cohort = context(p, c)[0]
        obs = mean_auc(cohort, oofs[(p, c, b, i, "ridge")]) - mean_auc(cohort, oofs[(p, c, b, "I0", "ridge")])
        null = np.array([perm[s] for s in sorted(perm)]) - mean_auc(cohort, oofs[(p, c, b, "I0", "ridge")])
        pd.DataFrame({"seed": sorted(perm), "d_auc_ipcw_perm": null}).assign(
            d_auc_ipcw_obs=obs, p_value=(1 + (null >= obs).sum()) / (1 + len(null))).to_csv(OUT / "permutation.csv",
                                                                                           index=False)
        print(f"primary ΔAUC {obs:+.3f}; permutation p = {(1 + (null >= obs).sum()) / (1 + len(null)):.3f}")
    ladder_plot(res, OUT / "ladder.png")
    (OUT / "run_info.json").write_text(json.dumps({"argv": vars(a), "seconds": round(time.time() - t0)}, indent=1))
    show = ["population", "cohort", "learner", "arm", "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "d_auc_ipcw",
            "d_auc_ipcw_lo", "d_auc_ipcw_hi", "cal_slope", "oe_ratio"]
    print(res[res.learner.eq("ridge")][show].round(3).to_string(index=False))
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
