"""Split variance (An et al. 2021): where does the PRISM report split's AUC sit among random splits of the same design?

Design = the PRISM report's own split search (legacy train.choose_test_patients): for each seed, 20 000 random draws of
30 patients, keep the draw closest to 96 test scans / 53 positives. Seed 62 reproduces the PRISM report split exactly
(30 patients / 84 scans). Cohort, label and features are the PRISM report's (within 120 d, pre-progression only, scans
before late treatment; T1c + FLAIR legacy radiomics + hybrid_basic clinical codes).

Models, trained on each split's training patients and scored on its test patients:
  prism_fixed      the PRISM report model as shipped: its 48 columns, preprocessing thresholds and C, refitted.
                   Optimistic: the features were selected using other splits' test patients (the PRISM report
                   split's training patients)
  prism_reselect   same pipeline with per-split feature ranking (L1 + permutation consensus, cheap settings), top 48
                   (no per-split Optuna search; hyperparameters fixed at the shipped values)
  baseline         clinical + timing + treatment ridge (C3)
  baseline_rad     baseline + legacy radiomics top-10 (C3 concat)
AUC: naive 120-d label (as in the PRISM report) and IPCW AUC(120) on the MU cohort test scans.

    python -m prism.analyses.split_variance [--workers 22 --n-splits 500]
    python -m prism.analyses.split_variance --replot   # summary + figure from the existing per_split_auc.csv
    # -> outputs/results/analyses/split_variance/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from types import SimpleNamespace

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

from prism.config import DATA, LEGACY_FEATURES_DIR, REPO, RESULTS
from prism.experiments import c3_radiomics as c3
from prism.models.metrics import point_metrics

LEGACY = REPO / "legacy" / "radiomics"
BUNDLE = LEGACY / "models" / "calibrated" / "model_bundle.pkl"
PRISM_SEED = 62
REPORT_AUC = 0.802  # PRISM report model on its split, naive label, MU cohort scans (C3_radiomics.md)
MODELS = ("prism_fixed", "prism_reselect", "baseline", "baseline_rad")
OUT = RESULTS / "analyses" / "split_variance"
_S = {}


def _surv():
    if str(LEGACY) not in sys.path:
        sys.path.insert(0, str(LEGACY))
    from radiomics_pipeline.workflows import train as surv
    sys.modules["scripts.run_postoperative_progression_surveillance"] = surv
    return surv


def legacy_table():
    """PRISM report case table (cohort + label) with legacy T1c/FLAIR radiomics and hybrid_basic clinical columns."""
    surv = _surv()
    args = surv.parse_args(["--label-mode", "within_window", "--progression-window-days", "120",
                            "--pre-progression-only", "--exclude-after-late-treatment", "--modalities", "t1c,flair",
                            "--clinical-feature-set", "hybrid_basic", "--seed", str(PRISM_SEED)])
    args.modalities = surv.parse_modalities(args.modalities)
    cases = surv.build_case_table(pd.read_csv(DATA / "mu-reference-processed/manifests/experiment_index.csv"), args)
    meta = surv.case_metadata_frame(cases)
    rows = []
    for pid, tp in zip(meta.patient_id, meta.timepoint):
        d = json.loads((LEGACY_FEATURES_DIR / pid / f"{tp}.json").read_text())
        rows.append({k: v for k, v in d.items() if k not in meta.columns})
    feats = pd.concat([meta.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    feats = surv.merge_clinical_features(feats, cases, "hybrid_basic", repo_root=LEGACY, cache_root=LEGACY)
    cols = surv.candidate_feature_columns(feats, allowed_modalities=args.modalities, include_clinical=True)
    feats["scan_id"] = feats.patient_id + "_" + feats.timepoint
    return feats, cols, args


def _init():
    warnings.filterwarnings("ignore")
    threadpool_limits(1)
    import pickle
    surv = _surv()
    feats, cols, args = legacy_table()
    cohort, _, base, rad, er = c3.load("all_glioma")
    _S.update(surv=surv, feats=feats, cols=cols, args=args, cohort=cohort, base=base, rad=rad, er=er,
              bundle=pickle.load(open(BUNDLE, "rb")))


def make_splits(n, feats, args, surv):
    """Unique test-patient sets from the PRISM report's split search, seeds 0..; seed 62 = PRISM report split."""
    seen, out, seed = set(), [], 0
    while len(out) < n:
        a = SimpleNamespace(**{**vars(args), "seed": seed})
        test, _ = surv.choose_test_patients(feats, a)
        key = tuple(sorted(test))
        if key not in seen:
            seen.add(key)
            out.append((seed, key))
        seed += 1
    if PRISM_SEED >= seed:  # make sure the PRISM report split is in the set
        a = SimpleNamespace(**{**vars(args), "seed": PRISM_SEED})
        out.append((PRISM_SEED, tuple(sorted(surv.choose_test_patients(feats, a)[0]))))
    return out


def _prism(train, test, columns, seed):
    surv, st = _S["surv"], _S["bundle"]["preprocessor_state"]
    Xtr, state = surv.fit_preprocessor(train[columns], st.variance_threshold, st.corr_threshold, scale=True)
    m = surv.build_model("logreg", {"C": _S["bundle"]["classifier"].C}, seed, "cpu").fit(Xtr, train.label)
    return surv.predict_positive_probability(m, surv.transform_preprocessor(test[columns], state))


def run_split(job):
    seed, test_pids, perm_repeats, rank_folds = job
    surv, feats, cohort = _S["surv"], _S["feats"], _S["cohort"]
    test_pids = set(test_pids)
    is_te = feats.patient_id.isin(test_pids)
    train, test = feats[~is_te], feats[is_te]
    p = {"prism_fixed": _prism(train, test, list(_S["bundle"]["selected_columns"]), seed)}
    a = SimpleNamespace(**{**vars(_S["args"]), "seed": seed, "ranking_folds": rank_folds,
                           "permutation_repeats": perm_repeats})
    ranking, _ = surv.rank_features(train[_S["cols"]], train.label, train.patient_id, a)
    p["prism_reselect"] = _prism(train, test, ranking.feature.head(48).tolist(), seed)
    # MU cohort (same scans minus one) for the C3 models and the censoring-aware metric
    te = np.where(cohort.patient_id.isin(test_pids))[0]
    tr = np.where(~cohort.patient_id.isin(test_pids))[0]
    pos = test.reset_index(drop=True).set_index("scan_id").index.get_indexer(cohort.scan_id.iloc[te])
    preds = {k: v[pos] for k, v in p.items()}
    preds["baseline"] = c3.fit_predict(c3.BASELINES[0], cohort, _S["base"], _S["rad"], _S["er"], tr, te)
    preds["baseline_rad"] = c3.fit_predict(("legacy", "none", "top10", "concat", "ridge"), cohort, _S["base"],
                                           _S["rad"], _S["er"], tr, te)
    d = cohort.iloc[te].reset_index(drop=True)
    row = {"seed": seed, "prism_report_split": seed == PRISM_SEED, "n_test_patients": len(test_pids),
           "n_test_scans_legacy": len(test), "n_test_pos_legacy": int(test.label.sum()), "n_test_scans_mu": len(te),
           "prism_fixed_auc_legacy": roc_auc_score(test.label, p["prism_fixed"]),
           "test_patients": "|".join(sorted(test_pids))}
    for k, v in preds.items():
        row[f"{k}_auc_naive"] = roc_auc_score(d.naive_label_120, v)
        try:
            row[f"{k}_auc_ipcw"] = point_metrics(d, v, 120)["auc_ipcw"]
        except Exception:  # IPCW can fail on degenerate test sets
            row[f"{k}_auc_ipcw"] = np.nan
    return row


def feature_version():
    diff = subprocess.run(["git", "diff", "HEAD", "--", "prism/features/tabular.py"], cwd=REPO, capture_output=True,
                          text=True).stdout
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    return {"git_head": head, "tabular_py_dirty": bool(diff), "tabular_py_diff_sha1": hashlib.sha1(diff.encode()).hexdigest(),
            "tabular_py_diff": diff}


def summarise(df):
    rows = []
    rep = df[df.prism_report_split].iloc[0]
    for m in MODELS:
        for metric in ("naive", "ipcw"):
            x = df[f"{m}_auc_{metric}"].dropna()
            rows.append({"model": m, "metric": metric, "n_splits": len(x), "mean": x.mean(), "sd": x.std(),
                         "p2.5": x.quantile(0.025), "median": x.median(), "p97.5": x.quantile(0.975),
                         "prism_split_value": rep[f"{m}_auc_{metric}"],
                         "pct_rank_prism_split_value": 100 * (x < rep[f"{m}_auc_{metric}"]).mean(),
                         "pct_rank_0.80": 100 * (x < REPORT_AUC).mean(), "frac_ge_0.80": (x >= REPORT_AUC).mean()})
    s = pd.DataFrame(rows)
    for metric in ("naive", "ipcw"):
        for m in ("prism_fixed", "prism_reselect", "baseline_rad"):
            d = (df[f"{m}_auc_{metric}"] - df[f"baseline_auc_{metric}"]).dropna()
            s.loc[(s.model == m) & (s.metric == metric), ["frac_beats_baseline", "mean_delta_vs_baseline"]] = \
                [(d > 0).mean(), d.mean()]
    return s


LABELS = {"prism_reselect": "PRISM report pipeline, features re-selected per split",
          "prism_fixed": "PRISM report model, shipped features (optimistic: selected\nusing other splits' test patients)",
          "baseline": "Clinical + timing + treatment (ridge)", "baseline_rad": "Baseline + legacy radiomics top-10"}
COLORS = {"baseline": "#2a78d6", "prism_reselect": "#eb6834", "baseline_rad": "#1baf7a", "prism_fixed": "#eda100"}
PLOT_ORDER = ("prism_reselect", "prism_fixed", "baseline", "baseline_rad")


def plot(df, path):
    """Histogram of per-split AUC per model; markers + dotted lines = each model's AUC on the PRISM report split (seed 62)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rep = df[df.prism_report_split].iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), sharey=True)
    bins = np.arange(0.5, 1.0001, 0.0125)
    top = max(np.histogram(df[f"{m}_auc_{k}"].dropna(), bins)[0].max() for m in MODELS for k in ("naive", "ipcw"))
    for ax, metric, title in zip(axes, ("naive", "ipcw"), ("Naive 120-d label (as in the PRISM report)",
                                                           "IPCW AUC(120 d)")):
        n = df[f"prism_reselect_auc_{metric}"].notna().sum()
        for i, m in enumerate(PLOT_ORDER):
            x, v = df[f"{m}_auc_{metric}"].dropna(), rep[f"{m}_auc_{metric}"]
            ax.hist(x.clip(lower=0.5), bins=bins, histtype="step", lw=2, color=COLORS[m],
                    ls="--" if m == "prism_fixed" else "-", label=LABELS[m])
            ax.axvline(v, color=COLORS[m], ls=":", lw=1.2, ymax=(1.1 + 0.1 * i) / 1.48)
            y = top * (1.1 + 0.1 * i)
            ax.plot(v, y, marker="v", ms=9, color=COLORS[m], mec="white", mew=1.2, clip_on=False)
            ax.annotate(f"{v:.3f} (> {100 * (x < v).mean():.0f}% of splits)", (v, y), xytext=(8, 0),
                        textcoords="offset points", va="center", fontsize=8, color="#333333")
        if metric == "naive":
            ax.axvline(REPORT_AUC, color="black", lw=1.2, ymax=1 / 1.48)
            ax.annotate(f"PRISM report value {REPORT_AUC}", (REPORT_AUC, top * 0.98), xytext=(-4, 0),
                        textcoords="offset points", ha="right", fontsize=8)
        ax.set_ylim(0, top * 1.48)
        ax.set_xlim(0.5, 1.0)
        ax.set_title(f"{title}   (n = {n} splits)", fontsize=11)
        ax.set_xlabel("Test AUC, 30-patient split")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="x", color="#e5e5e5", lw=0.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Number of splits")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, fontsize=8.5, frameon=False, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.1))
    fig.text(0.5, -0.135, "Triangles and dotted lines: each model's AUC on the PRISM report split (seed 62, re-run here); "
             "(> x% of splits) = share of splits with a lower AUC. "
             f"IPCW AUC is undefined on {len(df) - df['prism_reselect_auc_ipcw'].notna().sum()} splits"
             + ("; AUCs below 0.5 are binned at 0.5." if (df.filter(like="_auc_") < 0.5).any().any() else "."),
             ha="center", fontsize=8, color="#555555")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism split_variance", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=22)
    ap.add_argument("--n-splits", type=int, default=500)
    ap.add_argument("--perm-repeats", type=int, default=5, help="permutation repeats in per-split ranking (shipped: 100)")
    ap.add_argument("--rank-folds", type=int, default=5, help="folds in per-split ranking (shipped default: 10)")
    ap.add_argument("--replot", action="store_true", help="only redo summary.csv and the figure from per_split_auc.csv")
    a = ap.parse_args(argv)
    if a.replot:
        df = pd.read_csv(OUT / "per_split_auc.csv")
        summarise(df).to_csv(OUT / "summary.csv", index=False)
        plot(df, OUT / "split_variance.png")
        return
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    _init()
    splits = make_splits(a.n_splits, _S["feats"], _S["args"], _S["surv"])
    jobs = [(s, t, a.perm_repeats, a.rank_folds) for s, t in splits]
    with ProcessPoolExecutor(a.workers, initializer=_init) as ex:
        df = pd.DataFrame(list(ex.map(run_split, jobs, chunksize=1)))
    df.to_csv(OUT / "per_split_auc.csv", index=False)
    s = summarise(df)
    s.to_csv(OUT / "summary.csv", index=False)
    plot(df, OUT / "split_variance.png")
    (OUT / "run_info.json").write_text(json.dumps({**vars(a), "n_unique_splits": len(df), "seeds_scanned": max(df.seed) + 1,
                                                   "minutes": round((time.time() - t0) / 60, 1), **feature_version()},
                                                  indent=1))
    cols = ["model", "metric", "mean", "sd", "p2.5", "p97.5", "prism_split_value", "pct_rank_prism_split_value",
            "frac_ge_0.80", "frac_beats_baseline"]
    print(s[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
