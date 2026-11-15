"""Draw two manuscript figures from aggregate CSVs only (no patient-level data are read).

fig3_context_split: AUC within one time window and across time windows, per score and cohort (m1_auc_split.csv).
fig4_group_conformal: coverage of the planned marginal and the group-conditional conformal sets of the combined
model, per group of scans (m2_coverage.csv).

Style follows scripts/generate_system_first_figures.py: Liberation Sans, 7.2 in wide, saved as drawn (pdf + png),
no text smaller than 6.5 pt, no titles inside the figure (captions are in LaTeX). Black and greys only.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 7.5, "axes.labelsize": 7.5,
                     "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "axes.spines.top": False,
                     "axes.spines.right": False, "pdf.fonttype": 42, "axes.linewidth": 0.7,
                     "xtick.major.width": 0.7, "ytick.major.width": 0.7})

REPO = Path(__file__).resolve().parents[1]
DEFAULT_AGG = Path("/tmp/claude-2719675/-project-community-sbandred-prism-gbm-surveillance/"
                   "98a30973-c6b6-48b8-97a3-8bec3815d33f/scratchpad/agg")
OUTPUT = REPO / "docs/manuscript/figures"
WIDTH = 7.2
INK, GREY, LIGHT = "#111111", "#777777", "#bbbbbb"

COHORTS = [("mu", "MU-Glioma-Post"), ("lumiere", "LUMIERE")]
SCORES = [("timeline", "clinical-history"), ("images", "imaging"), ("combined", "combined"),
          ("enhancing_volume", "enhancing volume"), ("context_only", "time window only")]
TIME = {"later_post_rt": "later after RT", "early_post_rt": "within 12 weeks after RT",
        "before_rt_end": "before end of RT", "unknown": "time unknown"}
ENHANCEMENT = {"et_increased": "enhancement increased", "et_not_increased": "not increased",
               "et_absent": "no enhancement", "no_previous": "no previous scan", "unknown": "enhancement unknown"}


def save(fig, name: str) -> None:
    for extension in ("pdf", "png"):
        fig.savefig(OUTPUT / f"{name}.{extension}", dpi=300, bbox_inches=None, facecolor="white")
    plt.close(fig)


def cohort_label(ax, text):
    ax.text(0.0, 1.02, text, transform=ax.transAxes, ha="left", va="bottom", fontsize=7.5, weight="bold")


def errorbar(ax, x, y, lo, hi, **style):
    ax.errorbar([x], [y], xerr=[[x - lo], [hi - x]], capsize=0, elinewidth=0.8, lw=0, **style)


def context_split(agg: Path) -> None:
    df = pd.read_csv(agg / "m1_auc_split.csv")
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.35), sharey=True)
    fig.subplots_adjust(left=0.135, right=0.99, top=0.80, bottom=0.17, wspace=0.08)
    off = 0.17
    for ax, (cohort, cohort_name) in zip(axes, COHORTS):
        sub = df[df.cohort == cohort].set_index(["score", "stat"])
        for y, (score, _) in enumerate(SCORES):
            if score != "context_only":   # within point: artefact at MU, degenerate 0.5 without interval at LUMIERE
                r = sub.loc[(score, "a_within")]
                errorbar(ax, r.est, y - off, r.lo, r.hi, fmt="o", ms=4.2, color=INK, mfc=INK, mec=INK)
            r = sub.loc[(score, "a_across")]
            errorbar(ax, r.est, y + off, r.lo, r.hi, fmt="s", ms=4.0, color=INK, mfc="white", mec=INK, mew=0.9)
            r = sub.loc[(score, "auc")]
            ax.plot([r.est, r.est], [y - 0.32, y + 0.32], color=GREY, lw=1.3, solid_capstyle="butt", zorder=1)
        ax.axvline(0.5, color=GREY, ls=":", lw=0.8, zorder=0)
        ax.set_xlim(0.3, 1.0)
        ax.set_ylim(len(SCORES) - 0.5, -0.5)
        ax.set_yticks(range(len(SCORES)), [label for _, label in SCORES])
        ax.tick_params(axis="y", length=0)
        ax.set_xlabel("AUC (95% CI)")
        cohort_label(ax, cohort_name)
    handles = [Line2D([], [], marker="o", ls="none", ms=4.2, color=INK, label="within one time window"),
               Line2D([], [], marker="s", ls="none", ms=4.0, mfc="white", mec=INK, mew=0.9,
                      label="across time windows"),
               Line2D([], [], marker="|", ls="none", ms=8, mew=1.3, color=GREY, label="overall")]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.56, 1.0),
               handletextpad=0.3, columnspacing=1.6)
    save(fig, "fig3_context_split")


def group_label(group: str, n: int) -> str:
    time, enhancement = group.removeprefix("group ").split("|")
    return f"{TIME.get(time, time)}, {ENHANCEMENT.get(enhancement, enhancement)} (n={n})"


def group_conformal(agg: Path) -> None:
    df = pd.read_csv(agg / "m2_coverage.csv")
    df = df[df.model == "combined"]
    sets = [("registered", "marginal (planned)", dict(fmt="o", ms=4.0, color=INK, mfc=INK, mec=INK)),
            ("mondrian", "group-conditional", dict(fmt="s", ms=3.8, color=INK, mfc="white", mec=INK, mew=0.9))]
    rows = {}
    for cohort, _ in COHORTS:
        sub = df[(df.cohort == cohort) & (df.set == "registered")]
        groups = sub[sub.group.str.startswith("group ") & (sub.n_scans >= 9)].sort_values("n_scans", ascending=False)
        summary = [(g, f"{g} (n={int(sub[sub.group == g].n_scans.iloc[0])})")
                   for g in ("all", "progression", "no progression")]
        rows[cohort] = summary + [(g, group_label(g, int(n))) for g, n in zip(groups.group, groups.n_scans)]
    # Panels stacked (one cohort above the other): the group labels are too long for two side-by-side panels.
    counts = [len(rows[c]) for c, _ in COHORTS]
    row_in, gap_in, top_in, bottom_in = 0.19, 0.45, 0.45, 0.40
    height = top_in + bottom_in + gap_in + row_in * sum(counts)
    fig, axes = plt.subplots(2, 1, figsize=(WIDTH, height), gridspec_kw={"height_ratios": counts})
    fig.subplots_adjust(left=0.37, right=0.97, top=1 - top_in / height, bottom=bottom_in / height,
                        hspace=gap_in / (row_in * sum(counts) / 2))
    off = 0.17
    for ax, (cohort, cohort_name) in zip(axes, COHORTS):
        sub = df[df.cohort == cohort]
        for row, (group, _) in enumerate(rows[cohort]):
            for k, (key, _, style) in enumerate(sets):
                r = sub[(sub.set == key) & (sub.group == group)].iloc[0]
                errorbar(ax, r.coverage, row + (off if k else -off), r.lo, r.hi, **style)
        ax.axhline(2.5, color=LIGHT, lw=0.6, zorder=0)
        ax.axvline(0.8, color=GREY, ls="--", lw=0.8, zorder=0)
        ax.set_xlim(0.4, 1.0)
        ax.set_ylim(len(rows[cohort]) - 0.5, -0.5)
        ax.set_yticks(range(len(rows[cohort])), [label for _, label in rows[cohort]])
        ax.tick_params(axis="y", length=0)
        cohort_label(ax, cohort_name)
    axes[-1].set_xlabel("coverage (95% CI)")
    handles = [Line2D([], [], ls="none", label=label, marker=style["fmt"],
                      **{k: v for k, v in style.items() if k != "fmt"}) for _, label, style in sets]
    fig.legend(handles=handles, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.65, 1.0),
               handletextpad=0.3, columnspacing=1.6)
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
