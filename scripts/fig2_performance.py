"""Figure 2: performance by cohort, modelled on Tak et al. 2025 (NEJM AI) Figure 3.

One row per cohort. Left: ROC curves of the three PRISM scores and the time-and-enhancement model, with 95%
patient-bootstrap bands. Middle: the AUC of each score with its 95% CI. Right: the gain of each PRISM score over the
baseline, with its paired 95% CI (MU and LUMIERE; the baseline was not run at UCSF).

ROC curves read per-scan scores that reproduce the AUCs below to 0.001 (asserted):
- imaging, combined, baseline: outputs/results/analyses/segmenter_stage/preds_released.npz (S1's released-mask
  predictions; MU: 5 repeats of 5-fold CV, curves averaged vertically over repeats; combined = full model at MU);
- clinical history: MU detection/oof_grade4_primary.csv.gz (B1), LUMIERE detection/lumiere_predictions.csv
  (Tbase@grade4), UCSF ucsf/locked/scores.csv (A-Tbase@grade4).

Every value is a verified aggregate; no patient-level data are read. Sources:
- MU AUCs: NUMBERS.md section 3 (DETECTION_TASK.md).
- LUMIERE AUCs: NUMBERS.md section 4.
- UCSF AUCs: NUMBERS.md section 4 (UCSF_RESULTS.md Part A).
- Baseline and gains over it: METHODS_RESULTS.md E4. The baseline was not run at UCSF.
- Published radiomics pipeline on MU: CHRISTODOULOU_REPLICATION.md (intended use; the authors' code on PRISM's label
  and folds).
- Enhancing volume alone: NUMBERS.md 11 and 12C (as in the previous fig2_transport).
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
    ("Time-and-enhancement model", BASE, "s", True),
    ("Enhancing volume alone", st.ET, "D", False),
    ("Published radiomics pipeline", st.CLIN, "^", False),
]

# cohort -> {score: (auc, lo, hi)}
AUC = {
    "MU-Glioma-Post": {
        "Clinical-history model": (0.822, 0.749, 0.902),
        "Imaging model": (0.709, 0.630, 0.781),
        "Combined model": (0.821, 0.744, 0.894),
        "Time-and-enhancement model": (0.80, 0.71, 0.88),
        "Enhancing volume alone": (0.622, 0.530, 0.717),
        "Published radiomics pipeline": (0.579, 0.499, 0.656),
    },
    "LUMIERE": {
        "Clinical-history model": (0.689, 0.600, 0.805),
        "Imaging model": (0.655, 0.565, 0.733),
        "Combined model": (0.773, 0.679, 0.857),
        "Time-and-enhancement model": (0.73, 0.64, 0.81),
        "Enhancing volume alone": (0.662, 0.563, 0.751),
    },
    "UCSF-ALPTDG": {
        "Clinical-history model": (0.561, 0.420, 0.687),
        "Imaging model": (0.726, 0.603, 0.835),
        "Combined model": (0.856, 0.758, 0.930),
        "Time-and-enhancement model": (0.866, 0.77, 0.94),   # approximate RT window (SEGMENTER_STAGE.md)
        "Enhancing volume alone": (0.878, 0.793, 0.948),
    },
}
# gain over the baseline (score - baseline), paired CI
GAIN = {
    "MU-Glioma-Post": {
        "Clinical-history model": (0.02, -0.05, 0.10),
        "Imaging model": (-0.09, -0.19, 0.02),
        "Combined model": (0.02, -0.03, 0.08),
    },
    "LUMIERE": {
        "Clinical-history model": (-0.05, -0.15, 0.07),
        "Imaging model": (-0.08, -0.16, -0.00),
        "Combined model": (0.04, -0.01, 0.10),
    },
    # UCSF: the model applied with the approximate radiotherapy flag (rt_phase), outside the planned comparison;
    # paired patient bootstrap, 2,000 resamples, seed 20261120, on preds_released.npz and ucsf/locked/scores.csv.
    "UCSF-ALPTDG": {
        "Clinical-history model": (-0.305, -0.474, -0.136),
        "Imaging model": (-0.141, -0.250, -0.046),
        "Combined model": (-0.010, -0.078, 0.048),
    },
}
APPROX = {"UCSF-ALPTDG"}   # cohorts where the time-and-enhancement model uses the approximate RT window
SETTING = {"MU-Glioma-Post": "Development, cross validation",
           "LUMIERE": "External, locked MU models",
           "UCSF-ALPTDG": "External, locked MU models"}


ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "outputs/results/analyses"
GRID = np.linspace(0, 1, 101)
ROC_SCORES = [("Clinical-history model", "hist"), ("Imaging model", "images"), ("Combined model", "combined"),
              ("Time-and-enhancement model", "baseline")]


def roc_data() -> dict:
    """{cohort: (y, patient ids, {name: (R, n) scores})} on the evaluation scans."""
    z = np.load(RES / "segmenter_stage/preds_released.npz", allow_pickle=True)
    ev = z["mu_ev"].astype(bool)
    oof = pd.read_csv(RES / "detection/oof_grade4_primary.csv.gz").set_index("scan_id").loc[z["mu_scan_id"][ev]]
    mu = {"hist": oof[[f"B1#r{r}" for r in range(5)]].to_numpy().T, "images": z["mu_images"][:, ev],
          "combined": z["mu_combined_full"][:, ev], "baseline": z["mu_baseline"][:, ev]}
    lum = pd.read_csv(RES / "detection/lumiere_predictions.csv").set_index("scan_id").loc[z["lum_scan_id"]]
    lu = {"hist": lum["Tbase@grade4"].to_numpy()[None], **{k: z[f"lum_{k}"][None] for k in
                                                          ("images", "combined", "baseline")}}
    e = ~np.isnan(z["ucsf_y"].astype(float))
    uc = pd.read_csv(RES / "ucsf/locked/scores.csv").set_index("scan_id").loc[z["ucsf_scan_id"][e]]
    us = {"hist": uc["A-Tbase@grade4"].to_numpy()[None], **{k: z[f"ucsf_{k}"][None, e] for k in
                                                           ("images", "combined", "baseline")}}
    out = {"MU-Glioma-Post": (z["mu_y"][ev].astype(int), z["mu_pid"][ev], mu),
           "LUMIERE": (z["lum_y"].astype(int), z["lum_pid"], lu),
           "UCSF-ALPTDG": (z["ucsf_y"][e].astype(int), z["ucsf_pid"][e], us)}
    for c, (y, _, sc) in out.items():   # the curves must be the published numbers
        for name, k in ROC_SCORES:
            if k in sc and name in AUC[c]:
                auc = np.mean([roc_auc_score(y, r) for r in sc[k]])
                assert abs(auc - AUC[c][name][0]) < 0.006, (c, name, auc)
    return out


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


def draw_roc(ax, y, pid, sc, cohort) -> None:
    ax.plot([0, 1], [0, 1], color=st.RULE, lw=0.7, ls=(0, (3, 2)), zorder=1)
    for name, k in ROC_SCORES:
        if k not in sc or name not in AUC[cohort]:
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
    cohorts = list(AUC)
    data = roc_data()
    names_all = [x[0] for x in SCORES]
    rows = {c: [n for n in names_all if n in AUC[c]] for c in cohorts}
    W, H = st.WIDTH, 6.6
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
        draw_roc(rx, yv, pid, sc, cohort)
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
