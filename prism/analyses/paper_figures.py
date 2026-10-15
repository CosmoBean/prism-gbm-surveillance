"""Manuscript figures and tables (results sections 1-3 + phase of care) from the final outputs.

Steps (run in order; `all` = compute + plot):
    compute-single   re-fit the C3 models on the PRISM report split (all gliomas, 126 train / 29 test patients) with the
                     current, clipped c3 pipeline, plus a clinical-only ridge; IPCW AUC with 1000-draw patient-cluster
                     bootstrap CIs, paired delta vs baseline ridge, pair decomposition, post-RT subset
                     -> outputs/results/analyses/paper_figures/single_split*.csv
    compute-splitvar re-fit `baseline` and `baseline_rad` (legacy top-10 concat, via c3.fit_predict, now with the
                     in-fold QuantileClip) on the 500 test-patient sets of split_variance/per_split_auc.csv.
                     Does not overwrite the original files:
                     -> outputs/results/analyses/split_variance/{per_split_auc_clipped.csv, summary_clipped.csv}
    plot             figures 1-4 (PNG 300 dpi + PDF) and tables (markdown + CSV)
                     -> docs/manuscript/figures/, outputs/results/analyses/paper_figures/

    python -m prism figures [all|compute-single|compute-splitvar|plot] [--workers 24] [--n-boot 1000]
"""

from __future__ import annotations

import argparse
import shutil
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from prism.config import REPO, RESULTS

H = 120
AN = RESULTS / "analyses"
OUT = AN / "paper_figures"
SV = AN / "split_variance"
FIG = REPO / "docs" / "manuscript" / "figures"
TEST_PREDICTIONS = REPO / "legacy" / "radiomics" / "models" / "calibrated" / "test_predictions.csv"
RAD_CFG = ("legacy", "none", "top10", "concat", "ridge")
BASE_CFG = (None, "none", "none", "none", "ridge")
GBM_CFG = (None, "none", "none", "none", "gbm")

# ---------------------------------------------------------------- style (reference palette, validated; CVD-safe
# adjacent pairs; identity is always also given by direct labels)
C = {"prism": "#eb6834", "prism_fixed": "#eda100", "baseline": "#2a78d6", "gbm": "#4a3aa7", "rad": "#1baf7a",
     "clinical": "#8a8985", "deep": "#e87ba4", "other": "#52514e"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 7.5, "axes.titlesize": 8.5, "axes.labelsize": 7.5,
        "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "axes.edgecolor": INK2,
        "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False,
        "axes.spines.right": False, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 300, "figure.dpi": 100,
        "axes.titleweight": "bold", "axes.titlelocation": "left"})
    return plt


def _letter(ax, s, x=-0.02, y=1.04):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=11, fontweight="bold", va="bottom", ha="right", color=INK)


# display names for the PRISM paper (data keys keep the analysis names)
_RENAME = [("PRISM report pipeline,", "PRISM initial pipeline,"), ("PRISM report model, shipped", "PRISM initial model, shipped"),
           ("PRISM report model", "PRISM initial model"), ("PRISM report split", "initial evaluation split"),
           ("PRISM report design", "initial evaluation design"), ("PRISM split", "Initial split"),
           ("reported 0.802", "initial 0.802"), ("Baseline ridge", "Core model (ridge)"),
           ("Baseline GBM", "Core model (boosting)"), ("baseline ridge", "core model (ridge)"),
           ("Baseline + ", "Core + "), ("baseline + ", "core + ")]


def _display(s):
    import re
    for a, b in _RENAME:
        s = s.replace(a, b)
    return re.sub(r"\b([Bb])aseline\b", lambda m: "Core" if m.group(1) == "B" else "core", s)


def _rename_text(fig):
    from matplotlib.text import Text
    fig.canvas.draw()  # materialise tick labels
    for ax in fig.axes:
        for get, setl, axis in ((ax.get_yticklabels, ax.set_yticklabels, ax.yaxis),
                                (ax.get_xticklabels, ax.set_xticklabels, ax.xaxis)):
            labs = [t.get_text() for t in get()]
            if any(_display(s) != s for s in labs):
                setl([_display(s) for s in labs])
    for t in fig.findobj(Text):
        if t.get_text():
            t.set_text(_display(t.get_text()))


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    _rename_text(fig)
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", bbox_inches="tight", facecolor="white")


# ---------------------------------------------------------------- compute: PRISM report split
def _phases(cohort):
    from prism.features.tabular import treatment
    t = treatment(cohort)
    return np.where(t.rt_started == 0, "pre_rt", np.where(t.rt_completed == 0, "during_rt",
                    np.where(cohort.early_post_rt == 1, "early_post_rt", "later")))


def compute_single(n_boot):
    from prism.experiments import c3_radiomics as c3
    from prism.features.tabular import groups as feature_groups
    from prism.models.metrics import cluster_bootstrap, point_metrics
    warnings.filterwarnings("ignore")
    cohort, _, base, rad, er = c3.load("all_glioma")
    clin = feature_groups(cohort)["clinical"]
    tp = pd.read_csv(TEST_PREDICTIONS)
    tp["scan_id"] = tp.patient_id + "_" + tp.timepoint
    test = cohort.patient_id.isin(tp.patient_id).to_numpy()
    tr, te = np.where(~test)[0], np.where(test)[0]
    shipped = tp.set_index("scan_id").reindex(cohort.scan_id.iloc[te])
    d = cohort.iloc[te].reset_index(drop=True)
    preds = {
        "PRISM report model": shipped.calibrated_probability.to_numpy(),
        "Baseline ridge": c3.fit_predict(BASE_CFG, cohort, base, rad, er, tr, te),
        "Baseline GBM": c3.fit_predict(GBM_CFG, cohort, base, rad, er, tr, te),
        "Baseline + legacy radiomics": c3.fit_predict(RAD_CFG, cohort, base, rad, er, tr, te),
        "Clinical only (ridge)": c3.fit_predict(BASE_CFG, cohort, clin, rad, er, tr, te),
    }
    ph = _phases(cohort)[te]
    subsets = {"all": np.ones(len(d), bool), "post_rt": np.isin(ph, ["early_post_rt", "later"])}
    rows = []
    for sub, m in subsets.items():
        ds = d[m].reset_index(drop=True)
        ps = {k: v[m] for k, v in preds.items()}
        boot = cluster_bootstrap(ds, ps, H, reference="Baseline ridge", n_boot=n_boot).set_index("formulation")
        for k, p in ps.items():
            pm = point_metrics(ds, p, H)
            b = boot.loc[k]
            rows.append({"subset": sub, "model": k, "n_scans": len(ds), "n_patients": ds.patient_id.nunique(),
                         "n_pos_naive": int(ds.naive_label_120.sum()), "auc_naive": pm["auc_naive"],
                         "auc_ipcw": pm["auc_ipcw"], "auc_ipcw_lo": b.auc_ipcw_lo, "auc_ipcw_hi": b.auc_ipcw_hi,
                         "d_auc_ipcw_vs_baseline": b.get("d_auc_ipcw_vs_Baseline ridge", np.nan),
                         "d_auc_ipcw_lo": b.get("d_auc_ipcw_lo", np.nan), "d_auc_ipcw_hi": b.get("d_auc_ipcw_hi", np.nan)})
    res = pd.DataFrame(rows)
    # pair decomposition (naive label, as in shap_prism_split)
    y = d.naive_label_120.to_numpy()
    pre = ph == "pre_rt"
    pr = []
    for k, p in preds.items():
        pos, npre, noth = (y == 1), (y == 0) & pre, (y == 0) & ~pre
        a = lambda neg: roc_auc_score(np.r_[np.ones(pos.sum()), np.zeros(neg.sum())], np.r_[p[pos], p[neg]])
        pr.append({"model": k, "n_pos": int(pos.sum()), "n_neg_pre_rt": int(npre.sum()), "n_neg_other": int(noth.sum()),
                   "pair_share_pre_rt_neg": npre.sum() / (npre.sum() + noth.sum()), "auc_all": roc_auc_score(y, p),
                   "auc_vs_pre_rt_neg": a(npre), "auc_vs_other_neg": a(noth)})
    OUT.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT / "single_split.csv", index=False)
    pd.DataFrame(pr).to_csv(OUT / "single_split_pairs.csv", index=False)
    print(res.round(3).to_string(index=False))
    print(pd.DataFrame(pr).round(3).to_string(index=False))


# ---------------------------------------------------------------- compute: split variance, clipped radiomics arm
_S = {}


def _init():
    from threadpoolctl import threadpool_limits
    from prism.experiments import c3_radiomics as c3
    warnings.filterwarnings("ignore")
    threadpool_limits(1)
    cohort, _, base, rad, er = c3.load("all_glioma")
    _S.update(c3=c3, cohort=cohort, base=base, rad=rad, er=er)


def _split(job):
    from prism.models.metrics import point_metrics
    seed, pids = job
    c3, cohort = _S["c3"], _S["cohort"]
    is_te = cohort.patient_id.isin(set(pids.split("|"))).to_numpy()
    tr, te = np.where(~is_te)[0], np.where(is_te)[0]
    d = cohort.iloc[te].reset_index(drop=True)
    row = {"seed": seed}
    for k, cfg in (("baseline", BASE_CFG), ("baseline_rad", RAD_CFG)):
        p = c3.fit_predict(cfg, cohort, _S["base"], _S["rad"], _S["er"], tr, te)
        row[f"{k}_auc_naive"] = roc_auc_score(d.naive_label_120, p)
        try:
            row[f"{k}_auc_ipcw"] = point_metrics(d, p, H)["auc_ipcw"]
        except Exception:  # same handling as split_variance.run_split
            row[f"{k}_auc_ipcw"] = np.nan
    return row


def compute_splitvar(workers):
    from prism.analyses import split_variance as sv
    t0 = time.time()
    old = pd.read_csv(SV / "per_split_auc.csv")
    jobs = list(zip(old.seed, old.test_patients))
    with ProcessPoolExecutor(workers, initializer=_init) as ex:
        new = pd.DataFrame(list(ex.map(_split, jobs, chunksize=4))).set_index("seed")
    df = old.set_index("seed")
    chk = {m: float(np.nanmax(np.abs(df[f"baseline_auc_{m}"] - new[f"baseline_auc_{m}"]))) for m in ("naive", "ipcw")}
    for m in ("naive", "ipcw"):
        df[f"baseline_rad_preclip_auc_{m}"] = df[f"baseline_rad_auc_{m}"]
        df[f"baseline_rad_auc_{m}"] = new[f"baseline_rad_auc_{m}"]
        df[f"baseline_refit_auc_{m}"] = new[f"baseline_auc_{m}"]
    df = df.reset_index()
    df.to_csv(SV / "per_split_auc_clipped.csv", index=False)
    s = sv.summarise(df)
    s["baseline_rad_source"] = np.where(s.model == "baseline_rad", "clipped re-run (paper_figures)", "per_split_auc.csv")
    s.to_csv(SV / "summary_clipped.csv", index=False)
    info = pd.Series({"minutes": round((time.time() - t0) / 60, 1), "workers": workers,
                      "baseline_refit_max_abs_diff_naive": chk["naive"],
                      "baseline_refit_max_abs_diff_ipcw": chk["ipcw"]})
    info.to_json(SV / "run_info_clipped.json", indent=1)
    print(info.to_string())
    print(s[s.model == "baseline_rad"].round(3).to_string(index=False))


# ---------------------------------------------------------------- plotting helpers
def _ci(ax, y, est, lo, hi, color, size=4.5, marker="o", lw=1.4, z=3):
    ax.plot([lo, hi], [y, y], color=color, lw=lw, solid_capstyle="round", zorder=z)
    ax.plot(est, y, marker=marker, ms=size, color=color, mec="white", mew=0.8, zorder=z + 1)


def _ord(v):
    n = int(round(v))
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _fmt(x, nd=3):
    return "–" if pd.isna(x) else f"{x:.{nd}f}"


def _fmtci(e, lo, hi, nd=3, sign=False):
    if pd.isna(e):
        return "–"
    f = (lambda v: f"{v:+.{nd}f}") if sign else (lambda v: f"{v:.{nd}f}")
    return f"{f(e)} [{f(lo)}, {f(hi)}]" if not pd.isna(lo) else f(e)


SS_ORDER = ["PRISM report model", "Baseline ridge", "Baseline GBM", "Baseline + legacy radiomics", "Clinical only (ridge)"]
SS_COL = {"PRISM report model": C["prism"], "Baseline ridge": C["baseline"], "Baseline GBM": C["gbm"],
          "Baseline + legacy radiomics": C["rad"], "Clinical only (ridge)": C["clinical"]}


# ---------------------------------------------------------------- Figure 1: the PRISM report split
def fig1(plt):
    ss = pd.read_csv(OUT / "single_split.csv")
    pairs = pd.read_csv(OUT / "single_split_pairs.csv").set_index("model")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.9), gridspec_kw={"width_ratios": [1.25, 1.1, 1.1], "wspace": 0.42})
    # A: all test scans
    for ax, sub, title, letter in ((axes[0], "all", "All test scans\n(82 scans / 29 patients)", "A"),
                                   (axes[2], "post_rt", "Post-RT test scans only\n(42 scans / 19 patients)", "C")):
        s = ss[ss.subset == sub].set_index("model").loc[SS_ORDER]
        for i, (m, r) in enumerate(s.iterrows()):
            y = len(SS_ORDER) - 1 - i
            _ci(ax, y, r.auc_ipcw, r.auc_ipcw_lo, r.auc_ipcw_hi, SS_COL[m])
            ax.plot(r.auc_naive, y, marker="|", ms=7, color=INK2, mew=1.0, zorder=5)
            ax.text(1.005, y, f"{r.auc_ipcw:.3f}", va="center", ha="left", fontsize=6.5, color=INK,
                    transform=ax.get_yaxis_transform())
        ax.axvline(0.5, color=GRID, lw=0.8, zorder=0)
        ax.set_xlim(0.4, 1.0)
        ax.set_ylim(-0.6, len(SS_ORDER) - 0.4)
        ax.set_yticks(range(len(SS_ORDER)))
        ax.set_yticklabels(SS_ORDER[::-1] if ax is axes[0] else [])
        ax.set_xlabel("AUC(120 d)")
        ax.set_title(title, fontsize=7.5)
        ax.grid(axis="x", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        _letter(ax, letter, x=-0.04 if ax is axes[2] else -0.02, y=1.13)
    axes[0].text(0.41, -1.6, "dot + bar: IPCW AUC, 95% patient-cluster\nbootstrap CI;  | = naive AUC", fontsize=6,
                 color=INK2, va="top")
    # B: pair decomposition
    ax = axes[1]
    order = [m for m in SS_ORDER if m in pairs.index]
    w = 0.36
    for i, m in enumerate(order):
        y = len(SS_ORDER) - 1 - SS_ORDER.index(m)
        r = pairs.loc[m]
        ax.barh(y + w / 2, r.auc_vs_pre_rt_neg - 0.4, left=0.4, height=w - 0.04, color=SS_COL[m], alpha=1.0)
        ax.barh(y - w / 2, r.auc_vs_other_neg - 0.4, left=0.4, height=w - 0.04, color=SS_COL[m], alpha=0.45)
        ax.text(r.auc_vs_pre_rt_neg + 0.008, y + w / 2, f"{r.auc_vs_pre_rt_neg:.2f}", va="center", fontsize=6)
        ax.text(r.auc_vs_other_neg + 0.008, y - w / 2, f"{r.auc_vs_other_neg:.2f}", va="center", fontsize=6)
    ax.set_xlim(0.4, 1.06)
    ax.set_ylim(-0.6, len(SS_ORDER) - 0.4)
    ax.set_yticks(range(len(SS_ORDER)))
    ax.set_yticklabels([])
    ax.set_xlabel("Naive AUC on a subset of pairs")
    share = pairs.pair_share_pre_rt_neg.iloc[0]
    ax.set_title(f"Pair decomposition\n({share:.0%} of pairs: pre-RT neg.)", fontsize=7.5)
    ax.tick_params(axis="y", length=0)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=INK2, alpha=1.0, label="positives vs pre-RT negatives"),
                       Patch(color=INK2, alpha=0.45, label="positives vs other negatives")],
              loc="upper center", bbox_to_anchor=(0.5, -0.2), frameon=False, ncol=1, fontsize=6)
    ax.grid(axis="x", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    _letter(ax, "B", x=-0.04, y=1.13)
    _save(fig, "fig1_single_split")
    plt.close(fig)


# ---------------------------------------------------------------- Figure 2: split variance
SV_ORDER = ["prism_reselect", "prism_fixed", "baseline", "baseline_rad"]
SV_LAB = {"prism_reselect": "PRISM report pipeline,\nfeatures re-selected per split",
          "prism_fixed": "PRISM report model, shipped\n48 features refitted (optimistic)",
          "baseline": "Baseline ridge\n(clinical + timing + treatment)",
          "baseline_rad": "Baseline + legacy radiomics\n(top-10, clipped)"}
SV_COL = {"prism_reselect": C["prism"], "prism_fixed": C["prism_fixed"], "baseline": C["baseline"],
          "baseline_rad": C["rad"]}


def fig2(plt):
    df = pd.read_csv(SV / "per_split_auc_clipped.csv")
    s = pd.read_csv(SV / "summary_clipped.csv")
    comp = pd.read_csv(AN / "shap_prism_split" / "per_split_composition.csv")
    fig = plt.figure(figsize=(7.2, 3.3))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 1], wspace=0.95)
    ax = fig.add_subplot(gs[0])
    rng = np.random.default_rng(0)
    for i, m in enumerate(SV_ORDER):
        y = len(SV_ORDER) - 1 - i
        x = df[f"{m}_auc_naive"].dropna().to_numpy()
        r = s[(s.model == m) & (s.metric == "naive")].iloc[0]
        parts = ax.violinplot(x, positions=[y], vert=False, widths=0.8, showextrema=False)
        for b in parts["bodies"]:
            b.set_facecolor(SV_COL[m]); b.set_alpha(0.28); b.set_edgecolor("none")
        ax.scatter(x, y + rng.uniform(-0.12, 0.12, len(x)), s=1.6, color=SV_COL[m], alpha=0.55, lw=0, zorder=2)
        ax.plot([r["p2.5"], r["p97.5"]], [y - 0.36, y - 0.36], color=INK2, lw=0.8)
        ax.plot(r["mean"], y - 0.36, marker="o", ms=3, color=INK2)
        ax.plot(r.prism_split_value, y, marker="D", ms=6, color=SV_COL[m], mec=INK, mew=0.9, zorder=5)
        ax.text(1.01, y, f"PRISM split {r.prism_split_value:.3f}\n({_ord(r.pct_rank_prism_split_value)} percentile)\n"
                f"mean {r['mean']:.3f} ± {r['sd']:.3f}\n≥ 0.802: {r['frac_ge_0.80']:.0%} of splits",
                fontsize=5.8, color=INK, va="center", transform=ax.get_yaxis_transform())
    ax.axvline(0.802, color=INK, lw=0.8, ls=(0, (3, 2)), zorder=1)
    ax.text(0.802, len(SV_ORDER) - 0.35, "reported 0.802", ha="center", va="bottom", fontsize=6, color=INK)
    ax.set_yticks(range(len(SV_ORDER)))
    ax.set_yticklabels([SV_LAB[m] for m in SV_ORDER[::-1]], fontsize=6.3)
    ax.set_xlim(0.5, 1.0)
    ax.set_ylim(-0.6, len(SV_ORDER) - 0.05)
    ax.set_xlabel("Test AUC (naive 120-d label), 500 splits of the PRISM report design")
    ax.grid(axis="x", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    _letter(ax, "A")
    # B: composition
    ax = fig.add_subplot(gs[1])
    x = comp.score_phase_post_rt
    for m, mk in (("baseline", "o"), ("prism_reselect", "o")):
        yv = comp[f"{m}_auc_naive"]
        ax.scatter(x, yv, s=4, color=SV_COL[m], alpha=0.45, lw=0,
                   label={"baseline": "baseline ridge", "prism_reselect": "PRISM pipeline, re-selected"}[m])
        b = np.polyfit(x, yv, 1)
        xx = np.linspace(x.min(), x.max(), 10)
        ax.plot(xx, np.polyval(b, xx), color=SV_COL[m], lw=1.6)
        rep = comp[comp.prism_report_split]
        ax.plot(rep.score_phase_post_rt, rep[f"{m}_auc_naive"], marker="D", ms=6, color=SV_COL[m], mec=INK, mew=0.9,
                zorder=5)
    from scipy.stats import spearmanr
    rb = spearmanr(x, comp.baseline_auc_naive).statistic
    rp = spearmanr(x, comp.prism_reselect_auc_naive).statistic
    ax.text(0.03, 0.03, f"Spearman ρ: baseline {rb:+.2f},\nPRISM re-selected {rp:+.2f}\n◆ = PRISM report split",
            transform=ax.transAxes, fontsize=6, va="bottom", color=INK)
    ax.set_xlabel("Test-set AUC of the rule\n“scan is post-RT” (composition)")
    ax.set_ylabel("Test AUC (naive)")
    ax.legend(loc="upper left", frameon=False, fontsize=6, markerscale=2.5)
    ax.grid(color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    _letter(ax, "B", x=-0.12)
    _save(fig, "fig2_split_variance")
    plt.close(fig)


# ---------------------------------------------------------------- Figure 3: clinical vs radiomics
def _pl():
    r = pd.read_csv(AN / "phase_ladder" / "results.csv")
    return r[(r.learner == "ridge")].set_index(["population", "cohort", "arm"])


LADDER = [("R0|ridge", "Clinical"), ("R1|ridge", "+timing"), ("R3|ridge", "+treat-\nment\n(= B)"),
          ("R3+I1|ridge", "B +\nvolumes"), ("R3+I3|ridge", "B +\nradio-\nmics"),
          ("R3+I4|ridge", "B +\ndeep")]


def forest_rows():
    """(section, label, population, est, lo, hi, source, note)."""
    rows = []
    for pop, pl in (("grade4", "G4"), ("all_glioma", "All")):
        c3r = pd.read_csv(RESULTS / "c3" / pop / "results.csv")
        c3r["cfg"] = c3r[["variant", "stability", "selection", "integration", "learner"]].astype(str).agg("|".join, axis=1)
        dcol = "d_auc_ipcw_vs_None|none|none|none|ridge"
        for cfg, lab in (("NESTED|-|-|-|ridge", "Radiomics, nested over 70 configs (primary)"),
                         ("legacy|none|top10|concat|ridge", "Radiomics, legacy top-10 concat (single config)"),
                         ("legacy|none|pca10|stack|ridge", "Radiomics, legacy PCA-10 stacked (best post hoc)")):
            x = c3r[c3r.cfg == cfg].iloc[0]
            rows.append(("C3 radiomics (clipped) vs baseline", lab, pl, x[dcol], x.d_auc_ipcw_lo, x.d_auc_ipcw_hi,
                         f"outputs/results/c3/{pop}/results.csv", cfg))
        dp = pd.read_csv(AN / "deep" / pop / "results.csv").set_index("arm")
        for arm, lab in (("NESTED_D1", "Deep, nested over 32 (SwinUNETR + BrainSegFounder)"),
                         ("brats21:lesion|none|pca10|stack|ridge", "Deep, BraTS21 SwinUNETR (lesion PCA-10 stack)"),
                         ("bsf:lesion|none|pca10|stack|ridge", "Deep, BrainSegFounder (lesion PCA-10 stack)"),
                         ("NESTED_D0", "Deep, random-weight encoder (control)")):
            x = dp.loc[arm]
            rows.append(("Frozen deep features vs baseline", lab, pl, x.d_auc_ipcw, x.d_auc_ipcw_lo, x.d_auc_ipcw_hi,
                         f"outputs/results/analyses/deep/{pop}/results.csv", arm))
        cl = pd.read_csv(AN / "clean_label" / "results.csv")
        x = cl[(cl.label == "imaging") & (cl.population == pop) & (cl.cohort == "full") & (cl.learner == "ridge")
               & (cl.model == "baseline+imaging") & (cl.reference == "baseline")].iloc[0]
        rows.append(("Imaging-defined label (clinical-only progression censored)", "Baseline + volumes/delta vs baseline",
                     pl, x.d_auc_ipcw, x.d_auc_ipcw_lo, x.d_auc_ipcw_hi,
                     "outputs/results/analyses/clean_label/results.csv",
                     "label=imaging, cohort=full, learner=ridge, model=baseline+imaging, reference=baseline"))
        pl_ = _pl()
        for arm, lab in (("R2+I2|ridge", "Post-RT: clinical+phase + imaging (primary)"),
                         ("R3+I2|ridge", "Post-RT: baseline + imaging"),
                         ("R3+I3|ridge", "Post-RT: baseline + radiomics (nested)")):
            x = pl_.loc[(pop, "post_rt", arm)]
            rows.append(("Post-RT scans only (phase ladder)", lab, pl, x.d_auc_ipcw, x.d_auc_ipcw_lo, x.d_auc_ipcw_hi,
                         "outputs/results/analyses/phase_ladder/results.csv", f"cohort=post_rt, learner=ridge, arm={arm}"))
        rs = pd.read_csv(AN / "reseg" / "forward_ipcw120.csv")
        for seg, lab in (("brats21", "BraTS21 SwinUNETR masks vs MU masks"), ("bsf", "BrainSegFounder masks vs MU masks")):
            x = rs[(rs.population == pop) & (rs.model == "clinical+phase+imaging") & (rs.segmenter == seg)].iloc[0]
            rows.append(("Re-segmentation (ref. = same model on MU masks)", f"Clinical+phase+imaging: {lab}", pl,
                         x.d_auc_ipcw_vs_mu, x.d_lo, x.d_hi, "outputs/results/analyses/reseg/forward_ipcw120.csv",
                         f"model=clinical+phase+imaging, segmenter={seg}"))
    lu = pd.read_csv(AN / "baselines" / "lumiere.csv")
    lk = pd.read_csv(AN / "deep" / "lumiere" / "locked.csv")
    for pop, pl in (("grade4", "G4"), ("all_glioma", "All")):
        x = lu[(lu.population == f"LUMIERE (locked, trained on MU {pop})")
               & (lu.model == "clinical + timing + volumes, shared (ridge)")].iloc[0]
        rows.append(("LUMIERE external (locked, trained on MU)", "Clinical+timing + volumes vs clinical+timing", pl,
                     x.d_auc_ipcw, x.d_auc_ipcw_lo, x.d_auc_ipcw_hi,
                     "outputs/results/analyses/baselines/lumiere.csv", f"population={x.population}, model={x.model}"))
        for b, lab in (("clinical+timing", "Clinical+timing + deep vs clinical+timing"),
                       ("clinical+timing+volumes", "Clinical+timing+volumes + deep vs same")):
            x = lk[(lk.train == pop) & (lk.base == b) & (lk.arm == "baseline+deep")].iloc[0]
            if True:
                rows.append(("LUMIERE external (locked, trained on MU)", lab, pl, x.d_auc_ipcw_vs_baseline,
                             x.d_auc_ipcw_lo, x.d_auc_ipcw_hi, "outputs/results/analyses/deep/lumiere/locked.csv",
                             f"train={pop}, base={b}, arm={x.arm}, config={x.config}"))
    return pd.DataFrame(rows, columns=["section", "label", "population", "d_auc", "lo", "hi", "source", "row"])


def fig3(plt):
    pl = _pl()
    fig = plt.figure(figsize=(7.2, 8.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 2.35], width_ratios=[1.35, 1], hspace=0.32, wspace=0.42)
    # A: ladder
    ax = fig.add_subplot(gs[0, 0])
    lad = []
    for j, (pop, pl_lab, col, off) in enumerate((("grade4", "Grade 4", C["baseline"], -0.12),
                                                  ("all_glioma", "All gliomas", C["other"], 0.12))):
        xs, ys = [], []
        for i, (arm, lab) in enumerate(LADDER):
            r = pl.loc[(pop, "full", arm)]
            colr = col
            ax.plot([i + off] * 2, [r.auc_ipcw_lo, r.auc_ipcw_hi], color=colr, lw=1.2, alpha=0.8)
            ax.plot(i + off, r.auc_ipcw, "o" if j == 0 else "s", ms=4.5, color=colr, mec="white", mew=0.7, zorder=4)
            xs.append(i + off); ys.append(r.auc_ipcw)
            lad.append({"population": pop, "step": lab.replace("\n", " "), "arm": arm, "auc_ipcw": r.auc_ipcw,
                        "lo": r.auc_ipcw_lo, "hi": r.auc_ipcw_hi, "d_vs_ref": r.d_auc_ipcw, "ref": r.reference})
        ax.plot(xs[:3], ys[:3], color=col, lw=1.0, alpha=0.9)
    ax.axvspan(2.5, 5.5, color="#f3f2ee", zorder=0)
    ax.text(4, 0.815, "each added to B\n(not cumulative)", ha="center", va="top", fontsize=5.8, color=INK2)
    ax.set_xticks(range(len(LADDER)))
    ax.set_xticklabels([l for _, l in LADDER], fontsize=6)
    ax.set_ylim(0.45, 0.83)
    ax.set_xticks(range(len(LADDER)))
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylabel("IPCW AUC(120 d), 5×5 CV")
    ax.grid(axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.set_title("Feature-group ladder (ridge)", fontsize=7.5)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], marker="o", color=C["baseline"], ls="", label="grade 4 (249 scans)"),
                       Line2D([], [], marker="s", color=C["other"], ls="", label="all gliomas (308 scans)")],
              loc="lower right", frameon=False, fontsize=6)
    _letter(ax, "A", x=-0.1)
    pd.DataFrame(lad).to_csv(OUT / "fig3a_ladder.csv", index=False)
    # C: SHAP shares
    ax = fig.add_subplot(gs[0, 1])
    g = pd.read_csv(AN / "shap" / "grade4" / "groups.csv")
    models = [("base_ridge", "Baseline ridge"), ("base_gbm", "Baseline GBM"), ("full_ridge", "Baseline + volumes/\nmorph./delta (ridge)"),
              ("full_gbm", "Baseline + volumes/\nmorph./delta (GBM)"), ("rad_ridge", "Baseline + radiomics\nscore (PCA-10 stack)")]
    groups = ["clinical", "timing", "treatment", "volumes", "morphology", "delta", "radiomics"]
    gcol = {"clinical": "#8a8985", "timing": "#9ec5f0", "treatment": C["baseline"], "volumes": "#a7dfc6",
            "morphology": C["rad"], "delta": "#0d6b4a", "radiomics": C["deep"]}
    for i, (m, lab) in enumerate(models):
        y = len(models) - 1 - i
        left = 0
        sub = g[g.model == m].set_index("group")
        for grp in groups:
            if grp in sub.index:
                v = sub.loc[grp, "share"]
                ax.barh(y, v, left=left, color=gcol[grp], height=0.62, edgecolor="white", lw=1.0)
                if v >= 0.09:
                    ax.text(left + v / 2, y, f"{v:.0%}", ha="center", va="center", fontsize=5.6,
                            color="white" if grp in ("treatment", "delta", "morphology") else INK)
                left += v
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([l for _, l in models][::-1], fontsize=6)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Share of mean |group SHAP| (grade 4, OOF)")
    ax.set_title("Where the credit goes", fontsize=7.5)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=gcol[k], label=k) for k in groups], ncol=4, fontsize=5.6, frameon=False,
              loc="upper center", bbox_to_anchor=(0.45, -0.25), handlelength=1, columnspacing=0.8)
    _letter(ax, "C", x=-0.02)
    # B: forest
    ax = fig.add_subplot(gs[1, :])
    fr = forest_rows()
    fr.to_csv(OUT / "fig3b_forest.csv", index=False)
    y = 0
    yt, yl = [], []
    for sec, sdf in fr.groupby("section", sort=False):
        y -= 0.4
        ax.text(-0.335, y, sec, fontsize=6.6, fontweight="bold", color=INK, va="center")
        y -= 0.85
        for lab, ldf in sdf.groupby("label", sort=False):
            for _, r in ldf.iterrows():
                off = 0.18 if r.population == "G4" else -0.18
                col = C["baseline"] if r.population == "G4" else C["other"]
                excl = (r.lo > 0) or (r.hi < 0)
                _ci(ax, y + off, r.d_auc, r.lo, r.hi, col, size=4, marker="o" if r.population == "G4" else "s", lw=1.2)
                ax.text(0.345, y + off, f"{r.population}  {r.d_auc:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}]" + (" *" if excl else ""),
                        fontsize=5.6, va="center", ha="left", color=INK)
            yt.append(y); yl.append(lab)
            y -= 0.85
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(yt)
    ax.set_yticklabels(yl, fontsize=6.2)
    ax.set_xlim(-0.34, 0.34)
    ax.set_ylim(y + 0.3, 0.2)
    ax.set_xlabel("ΔAUC (IPCW, 120 d) vs reference, paired patient-cluster bootstrap 95% CI")
    ax.grid(axis="x", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.legend(handles=[Line2D([], [], marker="o", color=C["baseline"], ls="", label="grade 4 (G4)"),
                       Line2D([], [], marker="s", color=C["other"], ls="", label="all gliomas (All)")],
              loc="lower left", frameon=False, fontsize=6)
    _letter(ax, "B", x=-0.005, y=1.0)
    _save(fig, "fig3_clinical_vs_radiomics")
    plt.close(fig)


# ---------------------------------------------------------------- Figure 4: phase of care
def fig4(plt):
    pl = _pl()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.3), gridspec_kw={"width_ratios": [1, 1.2], "wspace": 0.42})
    ax = axes[0]
    bases = [("R0", "R0 clinical", C["clinical"]), ("R1", "R1 + timing", "#9ec5f0"), ("R2", "R2 + phase", C["gbm"]),
             ("R3", "R3 baseline", C["baseline"])]
    cohorts = [("full", "Full\n249 scans"), ("post_rt", "Post-RT\n167 scans"), ("later_post_rt", "Later post-RT\n69 scans")]
    rows = []
    for j, (b, lab, col) in enumerate(bases):
        xs, ys = [], []
        for i, (c, _) in enumerate(cohorts):
            r = pl.loc[("grade4", c, f"{b}|ridge")]
            x = i + (j - 1.5) * 0.14
            ax.plot([x, x], [r.auc_ipcw_lo, r.auc_ipcw_hi], color=col, lw=1.1)
            ax.plot(x, r.auc_ipcw, "o", ms=4.5, color=col, mec="white", mew=0.7, zorder=4)
            xs.append(x); ys.append(r.auc_ipcw)
            rows.append({"cohort": c, "base": b, "auc_ipcw": r.auc_ipcw, "lo": r.auc_ipcw_lo, "hi": r.auc_ipcw_hi})
        ax.plot(xs, ys, color=col, lw=0.8, alpha=0.7, label=lab)
    ax.axhline(0.5, color=INK2, lw=0.7, ls=(0, (3, 2)))
    ax.axvspan(1.6, 2.5, color="#f3f2ee", zorder=0)
    ax.text(2.05, 0.81, "69 scans:\nbases below\nchance", fontsize=5.6, ha="center", va="top", color=INK2)
    ax.set_xticks(range(3)); ax.set_xticklabels([l for _, l in cohorts], fontsize=6.3)
    ax.set_ylim(0.25, 0.82); ax.set_xlim(-0.5, 2.5)
    ax.set_ylabel("IPCW AUC(120 d), 5×5 CV")
    ax.set_title("Non-imaging bases by cohort (grade 4)", fontsize=7.5)
    ax.legend(frameon=False, fontsize=6, loc="lower left")
    ax.grid(axis="y", color=GRID, lw=0.5); ax.set_axisbelow(True)
    _letter(ax, "A", x=-0.1)
    ax = axes[1]
    imgs = [("I1", "volumes"), ("I2", "all non-radiomics imaging"), ("I3", "radiomics (nested)"), ("I4", "deep (nested)")]
    icol = {"I1": "#a7dfc6", "I2": C["rad"], "I3": C["deep"], "I4": C["prism"]}
    yt, yl = [], []
    for j, (b, lab, _) in enumerate(bases):
        y0 = -j * 1.25
        for k, (im, il) in enumerate(imgs):
            r = pl.loc[("grade4", "post_rt", f"{b}+{im}|ridge")]
            y = y0 - k * 0.22
            prim = (b == "R2" and im == "I2")
            _ci(ax, y, r.d_auc_ipcw, r.d_auc_ipcw_lo, r.d_auc_ipcw_hi, icol[im], size=5.5 if prim else 4,
                marker="D" if prim else "o", lw=1.2)
            rows.append({"cohort": "post_rt", "base": b, "imaging": im, "d_auc": r.d_auc_ipcw, "lo": r.d_auc_ipcw_lo,
                         "hi": r.d_auc_ipcw_hi})
            if prim:
                ax.text(r.d_auc_ipcw_hi + 0.008, y, f"primary {r.d_auc_ipcw:+.3f}\n[{r.d_auc_ipcw_lo:+.3f}, "
                        f"{r.d_auc_ipcw_hi:+.3f}], perm. p = 0.21", fontsize=5.6, va="center", color=INK)
        yt.append(y0 - 0.33); yl.append(lab)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(yt); ax.set_yticklabels(yl, fontsize=6.3)
    ax.set_xlim(-0.12, 0.33)
    ax.set_xlabel("ΔAUC from adding imaging, post-RT grade 4\n(paired bootstrap 95% CI)")
    ax.set_title("Imaging on top of each base, post-RT only", fontsize=7.5)
    ax.legend(handles=[Line2D_(icol[i], l) for i, l in imgs], frameon=False, fontsize=6, ncol=2, loc="upper center",
              bbox_to_anchor=(0.45, -0.27))
    ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
    _letter(ax, "B", x=-0.22)
    pd.DataFrame(rows).to_csv(OUT / "fig4_phase.csv", index=False)
    _save(fig, "fig4_phase_of_care")
    plt.close(fig)


def Line2D_(col, lab):
    from matplotlib.lines import Line2D
    return Line2D([], [], marker="o", color=col, ls="-", lw=1.2, ms=4, label=lab)


# ---------------------------------------------------------------- Table 2: single split vs repeated CV
def table2():
    ss = pd.read_csv(OUT / "single_split.csv")
    ss = ss[ss.subset == "all"].set_index("model")
    s = pd.read_csv(SV / "summary_clipped.csv").set_index(["model", "metric"])
    cv = {}
    for pop in ("all_glioma", "grade4"):
        r = pd.read_csv(RESULTS / "c3" / pop / "results.csv")
        r["cfg"] = r[["variant", "stability", "selection", "integration", "learner"]].fillna("None").astype(str).agg("|".join, axis=1)
        r = r.set_index("cfg")
        pl = _pl()
        cv[pop] = {"Baseline ridge": r.loc["None|none|none|none|ridge"], "Baseline GBM": r.loc["None|none|none|none|gbm"],
                   "Baseline + legacy radiomics": r.loc["legacy|none|top10|concat|ridge"],
                   "Clinical only (ridge)": pl.loc[(pop, "full", "R0|ridge")]}
    svmap = {"PRISM report model": "prism_reselect", "Baseline ridge": "baseline", "Baseline + legacy radiomics": "baseline_rad"}
    rows = []
    for m in SS_ORDER:
        x = ss.loc[m]
        row = {"Model": m, "Single split: naive AUC": _fmt(x.auc_naive),
               "Single split: IPCW AUC [95% CI]": _fmtci(x.auc_ipcw, x.auc_ipcw_lo, x.auc_ipcw_hi),
               "Single split: ΔAUC vs baseline ridge [95% CI]": _fmtci(x.d_auc_ipcw_vs_baseline, x.d_auc_ipcw_lo,
                                                                     x.d_auc_ipcw_hi, sign=True)}
        if m in svmap:
            a, b = s.loc[(svmap[m], "naive")], s.loc[(svmap[m], "ipcw")]
            row["500 design splits: naive mean ± SD (2.5–97.5%)"] = f"{a['mean']:.3f} ± {a['sd']:.3f} ({a['p2.5']:.3f}–{a['p97.5']:.3f})"
            row["500 design splits: IPCW mean ± SD"] = f"{b['mean']:.3f} ± {b['sd']:.3f}"
            if m == "PRISM report model":
                for k in ("500 design splits: naive mean ± SD (2.5–97.5%)", "500 design splits: IPCW mean ± SD"):
                    row[k] += " (pipeline re-selected per split)"
        else:
            row["500 design splits: naive mean ± SD (2.5–97.5%)"] = row["500 design splits: IPCW mean ± SD"] = "not run"
        for pop, lab in (("all_glioma", "all gliomas"), ("grade4", "grade 4")):
            if m in cv[pop]:
                c = cv[pop][m]
                dcol = "d_auc_ipcw_vs_None|none|none|none|ridge" if "d_auc_ipcw_vs_None|none|none|none|ridge" in c.index else "d_auc_ipcw"
                row[f"5×5 CV {lab}: IPCW AUC [95% CI]"] = _fmtci(c.auc_ipcw, c.auc_ipcw_lo, c.auc_ipcw_hi)
            else:
                row[f"5×5 CV {lab}: IPCW AUC [95% CI]"] = "n/a (fixed model)"
        rows.append(row)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "table2_single_split_vs_cv.csv", index=False)
    md = "| " + " | ".join(t.columns) + " |\n|" + "---|" * len(t.columns) + "\n"
    md += "\n".join("| " + " | ".join(map(str, r)) + " |" for r in t.itertuples(index=False))
    (OUT / "table2_single_split_vs_cv.md").write_text(md + "\n")
    shutil.copy(OUT / "table2_single_split_vs_cv.csv", FIG / "table2_single_split_vs_cv.csv")
    shutil.copy(OUT / "table2_single_split_vs_cv.md", FIG / "table2_single_split_vs_cv.md")
    # forest + ladder tables
    fr = pd.read_csv(OUT / "fig3b_forest.csv")
    fr["ΔAUC [95% CI]"] = [_fmtci(a, b, c, sign=True) for a, b, c in zip(fr.d_auc, fr.lo, fr.hi)]
    fr[["section", "label", "population", "ΔAUC [95% CI]", "source", "row"]].to_csv(FIG / "table3_forest.csv", index=False)
    print(t.to_string(index=False))


def plot():
    plt = _style()
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    fig1(plt)
    fig2(plt)
    fig3(plt)
    fig4(plt)
    table2()
    for f in OUT.glob("*.csv"):
        shutil.copy(f, FIG / f.name)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism figures", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", nargs="?", default="plot", choices=["all", "compute-single", "compute-splitvar", "plot"])
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    if a.step in ("all", "compute-single"):
        compute_single(a.n_boot)
    if a.step in ("all", "compute-splitvar"):
        compute_splitvar(a.workers)
    if a.step in ("all", "plot"):
        plot()


if __name__ == "__main__":
    main()
