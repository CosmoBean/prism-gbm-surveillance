"""Figure 3: performance by cohort, modelled on Tak et al. 2025 (NEJM AI) Figure 3.

PRISM's primary pipeline (docs/results/SEGMENTER_SWITCH.md): imaging inputs from the BraTS24 segmenter, 22 cavity-free
inputs (S4 preds_segmenter22.npz); the clinical-history scores do not depend on masks. One row per cohort. Left: ROC
curves of the three PRISM scores and the time-and-enhancement model, 95% patient-bootstrap bands (MU: averaged
vertically over the five repeats). Middle: AUC with 95% CI, including the combined model on the released masks
(reference, hollow grey), the segmenter's enhancing volume alone and, at MU, the published radiomics pipeline (released
masks; CHRISTODOULOU_REPLICATION.md). Right: gain of each PRISM score over the time-and-enhancement model, paired 95% CI.
CIs: methods.boot (2,000 patient resamples, seed 20261120), asserted equal to S4 where they overlap. At UCSF the
time-and-enhancement model uses the approximated radiotherapy window.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from sklearn.metrics import roc_auc_score, roc_curve

import figure_style as st

BASE = "#2E3440"  # the time-and-enhancement model: dark neutral, square marker

# label, colour, marker, filled
SCORES = [
    ("Clinical-history model", st.HIST, "o", True),
    ("Imaging model", st.IMG, "o", True),
    ("Combined model", st.COMB, "o", True),
    ("Combined model, supplied masks", st.CLIN, "o", False),
    ("Time-and-enhancement model", BASE, "s", True),
    ("Enhancing volume alone", st.ET, "D", False),
    ("Published radiomics, supplied masks", st.CLIN, "^", False),
]
COHORTS = ["MU-Glioma-Post", "LUMIERE", "UCSF-ALPTDG"]
APPROX = {"UCSF-ALPTDG"}   # cohorts where the time-and-enhancement model uses the approximate RT window
SETTING = {"MU-Glioma-Post": "Development, cross validation",
           "LUMIERE": "External, locked MU models",
           "UCSF-ALPTDG": "External, locked MU models"}
RADIOMICS_MU = (0.579, 0.499, 0.656)   # CHRISTODOULOU_REPLICATION.md, on the released masks

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "outputs/results/analyses"
SEG = ROOT / "outputs/features/seg_brats24"
GRID = np.linspace(0, 1, 101)
SEED, N_BOOT = 20261120, 2000
ROC_SCORES = [("Clinical-history model", "hist"), ("Imaging model", "images"), ("Combined model", "combined"),
              ("Time-and-enhancement model", "baseline")]
KEYS = {"Clinical-history model": "hist", "Imaging model": "images", "Combined model": "combined",
        "Combined model, supplied masks": "combined_released", "Time-and-enhancement model": "baseline",
        "Enhancing volume alone": "et"}


def score_data() -> dict:
    """{cohort: (y, patient ids, context, {key: (R, n) scores})} on the evaluation scans: PRISM's primary pipeline
    (BraTS24 segmenter, 22 inputs; S4 preds_segmenter22.npz), the clinical-history scores (mask-independent), the
    released-mask combined model (reference) and the segmenter's enhancing volume."""
    z = np.load(RES / "segmenter_brats24/preds_segmenter22.npz", allow_pickle=True)
    r = np.load(RES / "segmenter_brats24/preds_released.npz", allow_pickle=True)
    for k in ("mu_scan_id", "lum_scan_id", "ucsf_scan_id"):
        assert np.array_equal(z[k], r[k]), k

    def et(cohort, ids):
        m = pd.read_csv(SEG / f"measurements_{cohort}.csv").set_index("scan_id")
        return m.et_cc.reindex(ids).to_numpy(float)[None]

    ev = z["mu_ev"].astype(bool)
    ids = z["mu_scan_id"][ev]
    oof = pd.read_csv(RES / "detection/oof_grade4_primary.csv.gz").set_index("scan_id").loc[ids]
    mu = {"hist": oof[[f"B1#r{k}" for k in range(5)]].to_numpy().T, "images": z["mu_images"][:, ev],
          "combined": z["mu_combined_full"][:, ev], "baseline": z["mu_baseline"][:, ev],
          "combined_released": r["mu_combined_full"][:, ev], "et": et("mu", ids)}
    lum = pd.read_csv(RES / "detection/lumiere_predictions.csv").set_index("scan_id").loc[z["lum_scan_id"]]
    lu = {"hist": lum["Tbase@grade4"].to_numpy()[None], **{k: z[f"lum_{k}"][None] for k in
                                                          ("images", "combined", "baseline")},
          "combined_released": r["lum_combined"][None], "et": et("lumiere", z["lum_scan_id"])}
    e = ~np.isnan(z["ucsf_y"].astype(float))
    uc = pd.read_csv(RES / "ucsf/locked/scores.csv").set_index("scan_id").loc[z["ucsf_scan_id"][e]]
    us = {"hist": uc["A-Tbase@grade4"].to_numpy()[None], **{k: z[f"ucsf_{k}"][None, e] for k in
                                                           ("images", "combined", "baseline")},
          "combined_released": r["ucsf_combined"][None, e], "et": et("ucsf", z["ucsf_scan_id"][e])}
    return {"MU-Glioma-Post": (z["mu_y"][ev].astype(int), z["mu_pid"][ev], z["mu_phase"][ev], mu),
            "LUMIERE": (z["lum_y"].astype(int), z["lum_pid"], z["lum_ctx"], lu),
            "UCSF-ALPTDG": (z["ucsf_y"][e].astype(int), z["ucsf_pid"][e], z["ucsf_ctx"][e], us)}


def aucs_and_gains(data) -> tuple[dict, dict]:
    """AUC (95% CI) per score and gain over the time-and-enhancement model (paired 95% CI): one patient bootstrap
    per cohort (methods.boot, 2,000 samples, seed 20261120; MU averaged over the five repeats), as S4."""
    from prism.analyses.methods import boot, ci, m1_stats
    AUC, GAIN = {}, {}
    for c, (y, pid, ctx, sc) in data.items():
        est, B = m1_stats(y, sc, ctx), boot(y, sc, ctx, pid, N_BOOT, seed=SEED)
        AUC[c] = {n: (est[k][0], *ci([b[k][0] for b in B])) for n, k in KEYS.items() if k in sc}
        GAIN[c] = {n: (est[k][0] - est["baseline"][0], *ci([b[k][0] - b["baseline"][0] for b in B]))
                   for n, k in KEYS.items() if k in ("hist", "images", "combined")}
    if "MU-Glioma-Post" in AUC:
        AUC["MU-Glioma-Post"]["Published radiomics, supplied masks"] = RADIOMICS_MU
    # the same numbers as S4 where they overlap (segmenter22 rows of s4_exploratory.csv)
    s4 = pd.read_csv(RES / "segmenter_brats24/s4_exploratory.csv")
    s4 = s4[s4.masks == "segmenter22"].drop_duplicates(["cohort", "kind", "score"]).set_index(["cohort", "kind", "score"])
    cmap = {"MU-Glioma-Post": "mu", "LUMIERE": "lumiere", "UCSF-ALPTDG": "ucsf"}
    for c in AUC:
        comb = "combined_full" if c == "MU-Glioma-Post" else "combined"
        for n, sk in (("Imaging model", "images"), ("Combined model", comb), ("Time-and-enhancement model", "baseline")):
            row = s4.loc[(cmap[c], "auc", sk)]
            assert np.allclose(AUC[c][n], (row.est, row.lo, row.hi), atol=1e-9), (c, n, AUC[c][n], row)
        row = s4.loc[(cmap[c], "gain", f"{comb}-baseline")]
        assert np.allclose(GAIN[c]["Combined model"], (row.est, row.lo, row.hi), atol=1e-9), (c, GAIN[c])
    return AUC, GAIN


def roc_data() -> dict:
    """{cohort: (y, patient ids, {name: (R, n) scores})} on the evaluation scans (primary pipeline)."""
    return {c: (y, pid, sc) for c, (y, pid, _, sc) in score_data().items()}


def mean_tpr(y, P) -> np.ndarray:
    """TPR on GRID, averaged vertically over repeats (rows of P)."""
    t = []
    for p in P:
        fpr, tpr, _ = roc_curve(y, p)
        t.append(np.interp(GRID, fpr, tpr))
    t = np.mean(t, axis=0)
    t[0] = 0.0
    return t


def roc_band(y, pid, P, n_boot=1000, seed=20261120) -> tuple:
    """Patient-bootstrap 95% band of the mean ROC curve."""
    rng = np.random.default_rng(seed)
    pats = np.unique(pid)
    idx = {q: np.flatnonzero(pid == q) for q in pats}
    curves = []
    while len(curves) < n_boot:
        b = np.concatenate([idx[q] for q in rng.choice(pats, len(pats))])
        if y[b].min() == y[b].max():
            continue
        curves.append(mean_tpr(y[b], P[:, b]))
    lo, hi = np.percentile(curves, [2.5, 97.5], axis=0)
    return mean_tpr(y, P), lo, hi


def draw_roc(ax, y, pid, sc) -> None:
    ax.plot([0, 1], [0, 1], color=st.RULE, lw=0.7, ls=(0, (3, 2)), zorder=1)
    for name, k in ROC_SCORES:
        if k not in sc:
            continue
        _, c, _, _ = style(name)
        m, lo, hi = roc_band(y, pid, sc[k])
        base = k == "baseline"
        if not base:
            ax.fill_between(GRID, lo, hi, color=c, alpha=0.13, lw=0, zorder=2)
        ax.plot(GRID, m, color=c, lw=1.0 if not base else 0.9, ls=(0, (2.5, 1.5)) if base else "-", zorder=3)
    ax.set(xlim=(0, 1), ylim=(0, 1.01), xticks=[0, 0.5, 1], yticks=[0, 0.5, 1], aspect="equal")
    ax.set_xticklabels(["0", "0.5", "1"])
    ax.set_yticklabels(["0", "0.5", "1"])
    ax.set_ylabel("Sensitivity", labelpad=1)


def style(score):
    return next(s for s in SCORES if s[0] == score)


def minus(text: str) -> str:
    return text.replace("-", "\u2212")


def draw(output: Path) -> None:
    full = score_data()
    AUC, GAIN = aucs_and_gains(full)
    cohorts = COHORTS
    data = {c: (y, pid, sc) for c, (y, pid, _, sc) in full.items()}
    names_all = [x[0] for x in SCORES]
    rows = {c: [n for n in names_all if n in AUC[c]] for c in cohorts}
    W, H = st.WIDTH, 7.0
    unit, head, gap = 0.235 / H * 1.0, 0.30 / H, 0.42 / H   # row pitch, header band, gap below a block (fig frac)
    roc_h = 1.30 / H                                         # ROC panel height (square: 1.30 in)
    fig = plt.figure(figsize=(W, H))
    y = 1 - 0.10 / H
    for r, cohort in enumerate(cohorts):
        names = rows[cohort]; n = len(names)
        block = max(unit * n, roc_h)
        st.panel_header(fig, y, "abc"[r], f"{cohort}  \u00b7  {SETTING[cohort]}")
        top = y - head
        rx = fig.add_axes([0.055, top - roc_h, roc_h * H / W, roc_h])
        h = unit * n
        y0 = top - (block + h) / 2
        ax = fig.add_axes([0.475, y0, 0.255, h])
        last = r == len(cohorts) - 1
        yv, pid, sc = data[cohort]
        draw_roc(rx, yv, pid, sc)
        rx.set_xlabel("1 \u2212 specificity", labelpad=1)
        for i, name in enumerate(names):
            ypos = n - 1 - i
            _, c, m, f = style(name)
            v = AUC[cohort][name]
            ax.errorbar(v[0], ypos, xerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt=m, ms=4.2, color=c,
                        mfc=c if f and not (name.startswith("Time-and") and cohort in APPROX) else "white",
                        mec=c, mew=0.9, elinewidth=1.0, zorder=3)
            ax.text(v[2] + 0.012, ypos, f"{v[0]:.2f}", fontsize=6, color=st.INK, va="center", ha="left")
        ax.axvline(0.5, color=st.RULE, lw=0.7, ls=(0, (3, 2)), zorder=1)
        ax.set(xlim=(0.3, 1.0), ylim=(-0.6, n - 0.4), yticks=range(n))
        ax.set_yticklabels([x + ("\u2020" if x.startswith("Time-and") and cohort in APPROX else "")
                            for x in reversed(names)])
        for lab in ax.get_yticklabels():
            lab.set_color(style(lab.get_text())[1] if lab.get_text() in names_all[:3] else st.INK)
        ax.tick_params(axis="y", length=0)
        ax.set_xlabel("AUC (95% CI)", labelpad=1)
        g = GAIN[cohort]
        if g is not None:
            bx = fig.add_axes([0.775, y0, 0.17, h])
            for i, name in enumerate(names):
                if name in g:
                    ypos = n - 1 - i
                    _, c, m, _ = style(name)
                    w = g[name]
                    bx.errorbar(w[0], ypos, xerr=[[w[0] - w[1]], [w[2] - w[0]]], fmt=m, ms=4.2, color=c, mfc=c,
                                mec=c, mew=0.9, elinewidth=1.0, zorder=3)
                    bx.text(1.03, ypos, minus(f"{w[0]:+.2f}"), fontsize=6, color=st.INK, va="center", ha="left",
                            transform=bx.get_yaxis_transform())
            bx.axvline(0, color=st.MUTED, lw=0.7, zorder=1)
            bx.set(xlim=(-0.5, 0.2), ylim=(-0.6, n - 0.4), yticks=[], xticks=[-0.4, -0.2, 0])
            bx.spines["left"].set_visible(False)
            bx.set_xlabel("Difference in AUC (95% CI)", labelpad=1)
        if r == 0:
            fig.text(0.775, y, "Gain over the\ntime-and-enhancement model", fontsize=6.6, weight="bold",
                     color=st.NAVY, va="top", ha="left")
        y = top - block - gap
    handles = [Line2D([], [], color=st.HIST, lw=1.0, label="Clinical-history model"),
               Line2D([], [], color=st.IMG, lw=1.0, label="Imaging model"),
               Line2D([], [], color=st.COMB, lw=1.0, label="Combined model"),
               Line2D([], [], color=BASE, lw=0.9, ls=(0, (2.5, 1.5)), label="Time-and-enhancement model"),
               Line2D([], [], ls=(0, (3, 2)), lw=0.7, color=st.RULE, label="Chance")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.022), fontsize=6.3, ncol=5)
    fig.text(0.5, 0.004, "\u2020 UCSF-ALPTDG records no radiotherapy end dates: the time-and-enhancement model uses the "
             "approximate radiotherapy window and was not in the planned comparison.", fontsize=5.8, color=st.MUTED,
             ha="center", va="bottom")
    st.save(fig, output, "fig2_performance")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "docs/manuscript/figures")
    draw(p.parse_args().output)
