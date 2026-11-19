"""Draw two manuscript figures from aggregate CSVs only (no patient-level data are read).

fig3_context_split: AUC within one time window and across time windows, per score and cohort (m1_auc_split.csv);
MU-Glioma-Post, LUMIERE and UCSF-ALPTDG.
fig4_group_conformal: coverage of the planned marginal and the group-conditional conformal sets of the combined
model, per group of scans (m2_coverage.csv).

Style: scripts/figure_style.py (colour follows the score, as in every figure; marker shape gives the AUC part or
the kind of conformal set). No titles inside the figure (captions are in LaTeX).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

import figure_style as st

REPO = Path(__file__).resolve().parents[1]
DEFAULT_AGG = REPO / "outputs/results/analyses/methods"
OUTPUT = REPO / "docs/manuscript/figures"
WIDTH = st.WIDTH

COHORTS = [("mu", "MU-Glioma-Post"), ("lumiere", "LUMIERE"), ("ucsf", "UCSF-ALPTDG")]
SCORES = [("timeline", "clinical-history"), ("images", "imaging"), ("combined", "combined"),
          ("enhancing_volume", "enhancing volume"), ("context_only", "time window only")]
TIME = {"later_post_rt": "later after RT", "early_post_rt": "within 12 weeks after RT",
        "before_rt_end": "before end of RT", "unknown": "time unknown"}
ENHANCEMENT = {"et_increased": "enhancement increased", "et_not_increased": "not increased",
               "et_absent": "no enhancement", "no_previous": "no previous scan", "unknown": "enhancement unknown"}


def save(fig, name: str) -> None:
    st.save(fig, OUTPUT, name)


def cohort_label(ax, text):
    lo, hi = ax.get_xlim()
    st.section_label(ax, lo, hi, text, y=1.03)


def errorbar(ax, x, y, lo, hi, colour, filled, marker, ms):
    ax.errorbar([x], [y], xerr=[[x - lo], [hi - x]], fmt=marker, ms=ms, color=colour, ecolor=colour,
                mfc=colour if filled else "white", mec=colour, mew=0.9, elinewidth=0.9, lw=0, zorder=3)


def reference_line(ax, x, dashes=(0, (3, 2))):
    ax.axvline(x, color=st.MUTED, ls=dashes, lw=0.6, zorder=0)


def context_split(agg: Path) -> None:
    df = pd.read_csv(agg / "m1_auc_split.csv")
    fig, axes = plt.subplots(1, len(COHORTS), figsize=(WIDTH, 2.3), sharey=True)
    fig.subplots_adjust(left=0.135, right=0.985, top=0.80, bottom=0.17, wspace=0.10)
    off = 0.16
    for ax, (cohort, cohort_name) in zip(axes, COHORTS):
        sub = df[df.cohort == cohort].set_index(["score", "stat"])
        for y, (score, _) in enumerate(SCORES):
            colour = st.SCORE[score]
            if y % 2 == 0:
                ax.axhspan(y - 0.5, y + 0.5, color=st.PANEL, lw=0, zorder=0)
            if score != "context_only":   # within point: artefact at MU, degenerate 0.5 without interval at LUMIERE
                r = sub.loc[(score, "a_within")]
                errorbar(ax, r.est, y - off, r.lo, r.hi, colour, True, "o", 4.0)
            r = sub.loc[(score, "a_across")]
            errorbar(ax, r.est, y + off, r.lo, r.hi, colour, False, "s", 3.8)
            r = sub.loc[(score, "auc")]
            ax.plot([r.est, r.est], [y - 0.34, y + 0.34], color=st.INK, lw=1.4, zorder=2)
        reference_line(ax, 0.5)
        ax.set_xlim(0.3, 1.0)
        ax.set_ylim(len(SCORES) - 0.5, -0.5)
        ax.set_yticks(range(len(SCORES)), [label[0].upper() + label[1:] for _, label in SCORES])
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
        ax.set_xlabel("AUC (95% CI)")
        cohort_label(ax, cohort_name)
    handles = [Line2D([], [], marker="o", ls="none", ms=4.0, color=st.INK, label="Within one time window"),
               Line2D([], [], marker="s", ls="none", ms=3.8, mfc="white", mec=st.INK, mew=0.9,
                      label="Across time windows"),
               Line2D([], [], marker="|", ls="none", ms=8, mew=1.4, color=st.INK, label="Overall"),
               Line2D([], [], ls=(0, (3, 2)), lw=0.6, color=st.MUTED, label="Chance")]
    fig.legend(handles=handles, loc="upper center", ncol=4, bbox_to_anchor=(0.56, 1.0))
    save(fig, "fig3_context_split")


def group_label(group: str, n: int) -> str:
    time, enhancement = group.removeprefix("group ").split("|")
    text = f"{TIME.get(time, time)}, {ENHANCEMENT.get(enhancement, enhancement)}"
    return f"{text[0].upper()}{text[1:]} (n = {n})"


def group_conformal(agg: Path) -> None:
    df = pd.read_csv(agg / "m2_coverage.csv")
    df = df[df.model == "combined"]
    sets = [("registered", "Marginal (planned)", True, "o", 4.0),
            ("mondrian", "Group-conditional", False, "s", 3.8)]
    rows = {}
    for cohort, _ in COHORTS:
        sub = df[(df.cohort == cohort) & (df.set == "registered")]
        groups = sub[sub.group.str.startswith("group ") & (sub.n_scans >= 9)].sort_values("n_scans", ascending=False)
        summary = [(g, f"{g[0].upper()}{g[1:]} (n = {int(sub[sub.group == g].n_scans.iloc[0])})")
                   for g in ("all", "progression", "no progression")]
        rows[cohort] = summary + [(g, group_label(g, int(n))) for g, n in zip(groups.group, groups.n_scans)]
    # Panels stacked (one cohort above the other): the group labels are too long for two side-by-side panels.
    counts = [len(rows[c]) for c, _ in COHORTS]
    row_in, gap_in, top_in, bottom_in = 0.18, 0.42, 0.42, 0.40
    height = top_in + bottom_in + gap_in + row_in * sum(counts)
    height += gap_in * (len(COHORTS) - 2)
    fig, axes = plt.subplots(len(COHORTS), 1, figsize=(WIDTH, height), gridspec_kw={"height_ratios": counts})
    fig.subplots_adjust(left=0.37, right=0.97, top=1 - top_in / height, bottom=bottom_in / height,
                        hspace=gap_in / (row_in * sum(counts) / len(COHORTS)))
    off = 0.16
    for ax, (cohort, cohort_name) in zip(axes, COHORTS):
        sub = df[df.cohort == cohort]
        ax.axhspan(-0.5, 2.5, color=st.PANEL, lw=0, zorder=0)       # the three summary rows
        for row, (group, _) in enumerate(rows[cohort]):
            for k, (key, _, filled, marker, ms) in enumerate(sets):
                r = sub[(sub.set == key) & (sub.group == group)].iloc[0]
                errorbar(ax, r.coverage, row + (off if k else -off), r.lo, r.hi, st.COMB, filled, marker, ms)
        reference_line(ax, 0.8)
        ax.set_xlim(0.4, 1.0)
        ax.set_ylim(len(rows[cohort]) - 0.5, -0.5)
        ax.set_yticks(range(len(rows[cohort])), [label for _, label in rows[cohort]])
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
        cohort_label(ax, cohort_name)
    axes[-1].set_xlabel("Coverage of the 80% sets (95% CI)")
    handles = [Line2D([], [], ls="none", marker=marker, ms=ms, color=st.COMB, mfc=st.COMB if filled else "white",
                      mec=st.COMB, mew=0.9, label=label) for _, label, filled, marker, ms in sets]
    handles.append(Line2D([], [], ls=(0, (3, 2)), lw=0.6, color=st.MUTED, label="Nominal 80%"))
    fig.legend(handles=handles, loc="upper center", ncol=3, bbox_to_anchor=(0.67, 1.0))
    save(fig, "fig4_group_conformal")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agg", type=Path, default=DEFAULT_AGG, help="directory with the aggregate CSVs")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    context_split(args.agg)
    group_conformal(args.agg)


if __name__ == "__main__":
    main()
