"""Supplementary figure: calibration of PRISM's three scores per cohort, after Tak et al. 2025 (NEJM AI) Figure 6.

One panel per cohort. Each score's evaluation scans are split into five equal-size bins of predicted probability;
the point is the mean prediction against the observed share of progression scans in the bin (MU: per repeat of
cross validation, then averaged over the five repeats). The dashed diagonal is perfect calibration. The legend gives
each score's calibration slope and calibration-in-the-large (intercept with the logit as offset), computed as in
prism.analyses.ucsf_external.calibration (MU: mean over repeats), the numbers quoted in the Results.

Per-scan scores: fig2_performance.roc_data (the same scores as the ROC curves, asserted to reproduce the AUCs).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

import figure_style as st
from fig2_performance import roc_data
from prism.analyses.ucsf_external import calibration

SCORES = [("hist", "Clinical history", st.HIST, "o"), ("images", "Imaging", st.IMG, "s"),
          ("combined", "Combined", st.COMB, "D")]
BINS = 5


def reliability(y, P) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for p in P:
        edges = np.quantile(p, np.linspace(0, 1, BINS + 1))
        b = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, BINS - 1)
        xs.append([p[b == k].mean() for k in range(BINS)])
        ys.append([y[b == k].mean() for k in range(BINS)])
    return np.mean(xs, axis=0), np.mean(ys, axis=0)


def draw(output: Path) -> dict:
    data = roc_data()
    fig, axes = plt.subplots(1, 3, figsize=(st.WIDTH, 3.15))
    fig.subplots_adjust(left=0.07, right=0.99, top=0.90, bottom=0.30, wspace=0.32)
    out = {}
    for i, (ax, (cohort, (y, _, sc))) in enumerate(zip(axes, data.items())):
        ax.plot([0, 1], [0, 1], color=st.RULE, lw=0.7, ls=(0, (3, 2)), zorder=1)
        handles = []
        for k, name, colour, marker in SCORES:
            x, o = reliability(y, sc[k])
            ax.plot(x, o, color=colour, lw=0.9, marker=marker, ms=3.4, mfc=colour, mec=colour, zorder=3)
            cal = np.mean([calibration(y, p)[::2] for p in sc[k]], axis=0)   # slope, intercept
            out[(cohort, k)] = cal
            handles.append(Line2D([], [], color=colour, lw=0.9, marker=marker, ms=3.4,
                                  label=f"{name}: slope {cal[0]:.2f}, intercept {cal[1]:+.2f}".replace("-", "−")))
        ax.set(xlim=(0, 1), ylim=(0, 1), xticks=[0, 0.5, 1], yticks=[0, 0.5, 1], aspect="equal")
        ax.set_xticklabels(["0", "0.5", "1"])
        ax.set_yticklabels(["0", "0.5", "1"])
        ax.set_xlabel("Mean predicted probability", labelpad=1)
        if i == 0:
            ax.set_ylabel("Observed share of progression scans", labelpad=1)
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(-0.08, -0.17), fontsize=5.6, handlelength=1.6)
        st.letter(fig, ax.get_position().x0 - 0.055, 0.985, "abc"[i])
        fig.text(ax.get_position().x0 - 0.025, 0.983, cohort, fontsize=7, weight="bold", ha="left", va="top")
    st.save(fig, output, "figS_calibration")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "docs/manuscript/figures")
    for key, v in draw(p.parse_args().output).items():
        print(key, np.round(v, 2))
