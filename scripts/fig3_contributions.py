"""Figure 3: what each group of inputs contributes to PRISM's three scores at MU (exploratory).

Reads outputs/results/analyses/feature_contributions/{shares.csv, logo.csv} written by
scripts/prism_feature_contributions.py. Row (a): each group's share of a scan's score, median and IQR over the 146
evaluation scans. Row (b): the fall in AUC when the group is left out, with its paired 95% CI.
"""
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import figure_style as st

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "outputs/results/analyses/feature_contributions"
GROUPS = ["Patient characteristics", "Treatment course and dates", "Volumes", "Composition, shape and position",
          "Intensity", "Change since earlier scans"]
MODELS = [("history", "Clinical-history model", st.HIST), ("imaging", "Imaging model", st.IMG),
          ("combined", "Combined model", st.COMB)]


def fig3(output: Path) -> None:
    st.apply()
    shares, logo = pd.read_csv(SRC / "shares.csv"), pd.read_csv(SRC / "logo.csv")
    fig, axes = plt.subplots(2, 3, figsize=(st.WIDTH, 3.9), sharey=True,
                             gridspec_kw=dict(hspace=0.55, wspace=0.16, left=0.215, right=0.975, top=0.90,
                                              bottom=0.11))
    ys = {g: len(GROUPS) - 1 - i for i, g in enumerate(GROUPS)}
    for j, (m, title, colour) in enumerate(MODELS):
        a, b = axes[0, j], axes[1, j]
        a.set_title(title, color=colour, fontweight="bold", fontsize=7, pad=4)
        for _, r in shares[shares.model == m].iterrows():
            y = ys[r.group]
            a.plot([r.q1, r.q3], [y, y], color=colour, lw=1.4, solid_capstyle="butt")
            a.plot(r.median_share, y, "o", color=colour, ms=4)
        a.set_xlim(0, 1); a.set_xticks([0, .5, 1]); a.set_xticklabels(["0", "50%", "100%"])
        for _, r in logo[logo.model == m].iterrows():
            y = ys[r.group_left_out]
            b.plot([r.lo, r.hi], [y, y], color=colour, lw=1.4, solid_capstyle="butt")
            b.plot(r["drop"], y, "s", color=colour, ms=3.6)
        b.axvline(0, color=st.RULE, lw=0.8, zorder=0)
        b.set_xlim(-0.1, 0.36); b.set_xticks([0, .1, .2, .3])
        for ax in (a, b):
            ax.set_ylim(-0.6, len(GROUPS) - 0.4)
            ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(axis="y", length=0)
    axes[0, 0].set_yticks(list(ys.values())); axes[0, 0].set_yticklabels(list(ys.keys()))
    axes[0, 1].set_xlabel("Share of each scan's score (median, IQR)")
    axes[1, 1].set_xlabel("Fall in AUC when the group is left out (95% CI)")
    st.letter(fig, 0.004, 0.965, "a")
    st.letter(fig, 0.004, 0.47, "b")
    st.save(fig, output, "fig3_contributions")


if __name__ == "__main__":
    fig3(REPO / "docs/manuscript/figures")
