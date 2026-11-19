"""Draw the manuscript figures from verified aggregate values (docs/manuscript/NUMBERS.md).

Every value below is an aggregate from NUMBERS.md (section named beside it); no patient-level data are read.
Figure 5 (a real held-out report and the checker ladder) is drawn by scripts/fig5_report.py.
Figure 1 (the method) is drawn by scripts/fig1_prism.py; Figures 3 and 4 by scripts/generate_methods_figures.py.
All share scripts/figure_style.py.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import figure_style as st

WIDTH = st.WIDTH


def ci(v):
    return [[v[0] - v[1]], [v[2] - v[0]]]


def fig2(output: Path) -> None:
    """AUC by model and cohort. NUMBERS.md 3, 4, 11, 12C."""
    groups = ["MU-Glioma-Post", "LUMIERE", "UCSF-ALPTDG", "UCSF-ALPTDG"]
    series = [  # label, colour, marker, filled, [(auc, lo, hi) or None per group]
        ("Clinical data alone", st.CLIN, "o", True, [(0.530, 0.450, 0.606), (0.554, 0.458, 0.635), (0.502, 0.364, 0.630), (0.407, 0.314, 0.494)]),
        ("Clinical-history model", st.HIST, "o", True, [(0.822, 0.749, 0.902), (0.689, 0.600, 0.805), (0.561, 0.420, 0.687), (0.669, 0.549, 0.784)]),
        ("Imaging model", st.IMG, "o", True, [(0.709, 0.630, 0.781), (0.655, 0.565, 0.733), (0.726, 0.603, 0.835), (0.863, 0.772, 0.934)]),
        ("Imaging, current scan only", st.IMG, "o", False, [None, None, (0.795, 0.686, 0.887), (0.826, 0.729, 0.909)]),
        ("Combined model", st.COMB, "o", True, [(0.821, 0.744, 0.894), (0.773, 0.679, 0.857), (0.856, 0.758, 0.930), (0.871, 0.790, 0.938)]),
        ("Enhancing volume alone\u2020", st.ET, "D", False, [(0.622, 0.530, 0.717), (0.662, 0.563, 0.751), (0.878, 0.793, 0.948), None]),
    ]
    fig = plt.figure(figsize=(WIDTH, 2.6))
    ax = fig.add_axes([0.075, 0.12, 0.66, 0.76])
    ax.axvspan(2.5, 3.5, color=st.PANEL, lw=0, zorder=0)
    ax.axhline(0.5, color=st.MUTED, lw=0.6, ls=(0, (3, 2)), zorder=1)
    # What each group is, headed as Figure 1 heads its stages (development | locked external | reference).
    for x0, x1, text in [(-0.45, 0.45, "Development (CV)"), (0.55, 2.45, "Locked MU models, applied externally"),
                         (2.55, 3.45, "Refitted at UCSF (reference)")]:
        st.section_label(ax, x0, x1, text)
    step = 0.8 / 6
    for g in range(len(groups)):
        present = [s for s in series if s[4][g] is not None]
        for i, (label, colour, marker, filled, values) in enumerate(present):
            v = values[g]; x = g + (i - (len(present) - 1) / 2) * step
            ax.errorbar(x, v[0], yerr=ci(v), fmt=marker, ms=4.6 if marker == "o" else 4.0, color=colour,
                        mfc=colour if filled else "white", mec=colour, mew=0.9, elinewidth=1.0, zorder=3)
    handles = [Line2D([], [], marker=m, ms=4.6 if m == "o" else 4.0, color=c, mfc=c if f else "white", mec=c, mew=0.9,
                      lw=1.0, label=label) for label, c, m, f, _ in series]
    handles.append(Line2D([], [], ls=(0, (3, 2)), lw=0.6, color=st.MUTED, label="Chance"))
    ax.set(xticks=range(len(groups)), xlim=(-0.5, 3.5), ylim=(0.3, 1.0), ylabel="AUC (95% CI)")
    ax.set_xticklabels(groups)
    ax.tick_params(axis="x", length=0)
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5), handlelength=1.4, labelspacing=0.8)
    st.save(fig, output, "fig2_transport")


# Synthetic report: the Discussion's scenario (eight weeks after radiotherapy, growing enhancement, models
# disagree). Volumes and the score are invented; the card row is MU's (NUMBERS.md 10; Discussion).
def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    from fig1_prism import fig1
    from fig5_report import fig5
    fig1(output); fig2(output); fig5(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output-dir", type=Path, default=Path("docs/manuscript/figures"))
    generate(parser.parse_args().output_dir)
