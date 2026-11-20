"""Figure 2: performance by cohort, modelled on Tak et al. 2025 (NEJM AI) Figure 3.

One row per cohort. Left: the AUC of each score with its 95% CI. Right: the gain of each PRISM score over the
timing-and-enhancement baseline, with its paired 95% CI.

Every value is a verified aggregate; no patient-level data are read. Sources:
- MU AUCs: NUMBERS.md section 3 (DETECTION_TASK.md).
- LUMIERE AUCs: NUMBERS.md section 4.
- UCSF AUCs: NUMBERS.md section 4 (UCSF_RESULTS.md Part A).
- Baseline and gains over it: METHODS_RESULTS.md E4. The baseline was not run at UCSF.
- Since 2026-11-19 the imaging model is A (stratified) and the combined model is B (offset): their AUCs are
  outputs/results/analyses/adopt_ab/auc_old_new.csv (each cohort's published bootstrap; docs/results/ADOPT_AB.md) and
  their gains over the baseline METHODS_RESULTS.md E4 rerun (clinician_baseline/e4_reader_baseline.csv).
- Published radiomics pipeline on MU: CHRISTODOULOU_REPLICATION.md (intended use; the authors' code on PRISM's label
  and folds).
- Enhancing volume alone: NUMBERS.md 11 and 12C (as in the previous fig2_transport).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import figure_style as st

BASE = "#2E3440"  # the timing-and-enhancement baseline: dark neutral, square marker

# label, colour, marker, filled
SCORES = [
    ("Clinical-history model", st.HIST, "o", True),
    ("Imaging model", st.IMG, "o", True),
    ("Combined model", st.COMB, "o", True),
    ("Timing-and-enhancement baseline", BASE, "s", True),
    ("Enhancing volume alone", st.ET, "D", False),
    ("Published radiomics pipeline", st.CLIN, "^", False),
]

# cohort -> {score: (auc, lo, hi)}
AUC = {
    "MU-Glioma-Post": {
        "Clinical-history model": (0.822, 0.749, 0.902),
        "Imaging model": (0.669, 0.580, 0.741),
        "Combined model": (0.814, 0.733, 0.895),
        "Timing-and-enhancement baseline": (0.80, 0.71, 0.88),
        "Enhancing volume alone": (0.622, 0.530, 0.717),
        "Published radiomics pipeline": (0.579, 0.499, 0.656),
    },
    "LUMIERE": {
        "Clinical-history model": (0.689, 0.600, 0.805),
        "Imaging model": (0.642, 0.544, 0.734),
        "Combined model": (0.754, 0.664, 0.827),
        "Timing-and-enhancement baseline": (0.73, 0.64, 0.81),
        "Enhancing volume alone": (0.662, 0.563, 0.751),
    },
    "UCSF-ALPTDG": {
        "Clinical-history model": (0.561, 0.420, 0.687),
        "Imaging model": (0.769, 0.660, 0.870),
        "Combined model": (0.868, 0.781, 0.940),
        "Enhancing volume alone": (0.878, 0.793, 0.948),
    },
}
# gain over the baseline (score - baseline), paired CI
GAIN = {
    "MU-Glioma-Post": {
        "Clinical-history model": (0.02, -0.05, 0.10),
        "Imaging model": (-0.129, -0.232, -0.033),
        "Combined model": (0.016, -0.021, 0.048),
    },
    "LUMIERE": {
        "Clinical-history model": (-0.05, -0.15, 0.07),
        "Imaging model": (-0.092, -0.183, -0.010),
        "Combined model": (0.019, 0.003, 0.043),
    },
    "UCSF-ALPTDG": None,
}
SETTING = {"MU-Glioma-Post": "Development, cross validation",
           "LUMIERE": "External, locked MU models",
           "UCSF-ALPTDG": "External, locked MU models"}


def style(score):
    return next(s for s in SCORES if s[0] == score)


def draw(output: Path) -> None:
    cohorts = list(AUC)
    names_all = [x[0] for x in SCORES]
    rows = {c: [n for n in names_all if n in AUC[c] or n.startswith("Timing")] for c in cohorts}
    unit, head, gap_top = 0.040, 0.040, 0.02   # figure fraction per row, header band, top margin
    fig = plt.figure(figsize=(st.WIDTH, 6.2))
    y = 1 - gap_top
    for r, cohort in enumerate(cohorts):
        names = rows[cohort]; n = len(names); h = unit * n
        st.panel_header(fig, y, "abc"[r], f"{cohort}  \u00b7  {SETTING[cohort]}")
        y0 = y - head - h
        ax = fig.add_axes([0.235, y0, 0.40, h])
        bx = fig.add_axes([0.70, y0, 0.27, h])
        for i, name in enumerate(names):
            ypos = n - 1 - i
            _, c, m, f = style(name)
            v = AUC[cohort].get(name)
            if v is None:
                ax.text(0.31, ypos, "not run at this centre", fontsize=6, color=st.MUTED, va="center", ha="left",
                        style="italic")
            else:
                ax.errorbar(v[0], ypos, xerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt=m, ms=4.4, color=c,
                            mfc=c if f else "white", mec=c, mew=0.9, elinewidth=1.0, zorder=3)
                ax.text(v[2] + 0.012, ypos, f"{v[0]:.2f}", fontsize=6, color=st.INK, va="center", ha="left")
            g = GAIN[cohort]
            if g is not None and name in g:
                w = g[name]
                bx.errorbar(w[0], ypos, xerr=[[w[0] - w[1]], [w[2] - w[0]]], fmt=m, ms=4.4, color=c, mfc=c,
                            mec=c, mew=0.9, elinewidth=1.0, zorder=3)
                bx.text(0.195, ypos, f"{w[0]:+.2f}", fontsize=6, color=st.INK, va="center", ha="right")
        ax.axvline(0.5, color=st.RULE, lw=0.7, ls=(0, (3, 2)), zorder=1)
        ax.set(xlim=(0.3, 1.0), ylim=(-0.6, n - 0.4), yticks=range(n))
        ax.set_yticklabels(list(reversed(names)))
        for lab in ax.get_yticklabels():
            lab.set_color(style(lab.get_text())[1] if lab.get_text() in names_all[:3] else st.INK)
        ax.tick_params(axis="y", length=0)
        bx.axvline(0, color=st.MUTED, lw=0.7, zorder=1)
        bx.set(xlim=(-0.25, 0.2), ylim=(-0.6, n - 0.4), yticks=[])
        bx.spines["left"].set_visible(False)
        if GAIN[cohort] is None:
            bx.text(-0.025, (n - 1) / 2, "Baseline not run at this centre", fontsize=6.2, color=st.MUTED,
                    ha="center", va="center", style="italic", bbox=dict(fc="white", ec="none", pad=1.5))
        if r == 0:
            fig.text(0.70, y, "Gain over the timing-and-enhancement baseline", fontsize=6.6, weight="bold",
                     color=st.NAVY, va="top", ha="left")
        last = r == len(cohorts) - 1
        ax.set_xlabel("AUC (95% CI)" if last else "")
        bx.set_xlabel("Difference in AUC (95% CI)" if last else "")
        y = y0 - (0.065 if not last else 0)
    handles = [Line2D([], [], ls=(0, (3, 2)), lw=0.7, color=st.RULE, label="Chance"),
               Line2D([], [], lw=0.7, color=st.MUTED, label="No gain")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.005, 0.0), fontsize=6, ncol=2)
    st.save(fig, output, "fig2_performance")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "docs/manuscript/figures")
    draw(p.parse_args().output)
