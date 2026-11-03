"""Figure 1: PRISM splits one progression score into its evidence (A), and how it was evaluated (B).

Drawn, not data: the MRI slices come from `schematic_slice` (no patient image), the scores are the synthetic
example of Figure 5A (timeline 0.21, images 0.64, combined 0.33), and Panel B carries only cohort and report counts
(NUMBERS.md 1, 7). Plain journal style: hairlines, square corners, one sans-serif face, colour only for the three
kinds of evidence.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle


def fig1(output: Path) -> None:
    from generate_system_first_figures import C, LETTER_X, WIDTH, panel, save, schematic_slice, title

    ink, grey, rule = "#1a1a1a", "#5f5f5f", "#bdbdbd"
    height = 5.2
    fig = plt.figure(figsize=(WIDTH, height))

    # ---------------------------------------------------------------- Panel A: one scan through PRISM
    xa, wa, ya, ha = 0.035, 0.955, 0.375, 0.565
    ax = fig.add_axes([xa, ya, wa, ha])
    ax.set(xlim=(0, 110), ylim=(0, 60)); ax.axis("off")
    panel(fig, LETTER_X, ax, "A"); title(ax, "What PRISM reports at each scan")
    to_fig = lambda x, y: ((xa + wa * x / 110), (ya + ha * y / 60))

    def text(x, y, s, size=6.6, colour=ink, **kw):
        kw.setdefault("ha", "left"); kw.setdefault("va", "center")
        ax.text(x, y, s, fontsize=size, color=colour, linespacing=1.2, **kw)

    def arrow(a, b, colour=ink, lw=0.6):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=5.5, color=colour, lw=lw,
                                     shrinkA=0, shrinkB=0))

    # Column headings over a hairline.
    for x, s in [(0.5, "Inputs"), (29.0, "Evidence"), (49.0, "Scores"), (69.5, "Confidence"), (91.5, "Report")]:
        text(x, 57.3, s, size=7.0, weight="bold", va="baseline")
    ax.plot([0.5, 110], [56.0, 56.0], color=rule, lw=0.5)

    # Inputs: previous and current scan (drawn) with the tumour outline, the timeline, the clinical record.
    for i, (x0, name, scale) in enumerate([(0.5, "previous scan", 0.82), (13.0, "current scan", 1.0)]):
        f0, f1 = to_fig(x0, 38.0), to_fig(x0 + 11.5, 53.5)
        iax = fig.add_axes([f0[0], f0[1], f1[0] - f0[0], f1[1] - f0[1]])
        schematic_slice(iax, scale, seed=3 + i)
        iax.set_aspect("auto")
        for t in list(iax.texts):
            t.remove()
        text(x0, 36.4, name, size=6.3, colour=grey, va="top")
    text(0.5, 31.6, "T1-contrast MRI with tumour masks", size=6.3, colour=grey, style="italic")

    ty = 22.5
    ax.plot([0.5, 24.0], [ty, ty], color=ink, lw=0.6)
    ax.add_patch(Rectangle((4.0, ty - 0.9), 7.0, 1.8, fc="#d9d9d9", ec="none"))
    for x, s in [(1.2, "surgery"), (7.5, "chemoRT"), (21.0, "scan")]:
        ax.plot([x, x], [ty - 0.9, ty + 0.9], color=ink, lw=0.6 if x != 21.0 else 1.2)
        text(x, ty + 2.1, s, size=6.2, colour=grey, ha="center")
    text(21.0, ty - 2.2, "8 wk after RT", size=6.2, colour=grey, ha="center")
    text(0.5, 16.4, "Treatment timeline", size=6.3, colour=grey, style="italic")

    ax.add_patch(Rectangle((0.5, 6.0), 23.5, 5.6, fc="none", ec=rule, lw=0.5))
    text(1.5, 8.8, "age   sex   IDH   MGMT", size=6.4)
    text(0.5, 3.4, "Clinical record", size=6.3, colour=grey, style="italic")

    # A single grey ray gathers the inputs and enters the prism; three coloured rays leave it.
    ax.plot([25.5, 25.5], [6.0, 53.5], color=rule, lw=0.5)
    ax.plot([25.5, 33.2], [29.5, 29.5], color=grey, lw=1.0)
    tri = [(32.0, 18.0), (43.0, 18.0), (37.5, 39.0)]
    ax.add_patch(Polygon(tri, closed=True, fc="#f4f4f4", ec=ink, lw=0.7, zorder=3))
    text(37.5, 14.6, "PRISM", size=7.0, weight="bold", ha="center")
    text(37.5, 11.2, "splits the score\ninto its evidence", size=6.2, colour=grey, ha="center", va="top")
    exit_pt = (41.1, 28.5)
    rows = [("images", 47.0, "Image pathway", "tumour volumes and change", 0.64),
            ("combined", 29.5, "Combined score", "both kinds of input", 0.33),
            ("timeline", 12.0, "Timeline pathway", "timeline and clinical record", 0.21)]
    sx0, sx1 = 49.0, 61.5
    for key, y, name, detail, value in rows:
        ax.plot([exit_pt[0], 47.5], [exit_pt[1], y], color=C[key], lw=1.1, zorder=2)
        text(sx0, y + 3.4, name, size=6.8, weight="bold")
        ax.add_patch(Rectangle((sx0, y - 0.7), sx1 - sx0, 1.4, fc="#ececec", ec="none"))
        ax.add_patch(Rectangle((sx0, y - 0.7), (sx1 - sx0) * value, 1.4, fc=C[key], ec="none"))
        text(sx1 + 0.8, y, f"{value:.2f}", size=6.6)
        text(sx0, y - 3.0, detail, size=6.2, colour=grey)
    text(sx0, 3.4, "example values (Figure 5)", size=6.2, colour=grey, style="italic")

    # Confidence: three statements, each with what it measures.
    ax.plot([67.5, 67.5], [3.0, 53.5], color=rule, lw=0.5)
    conf = [(47.0, "Conformal set", "both outcomes", "80% set: one outcome or both"),
            (29.5, "Pathway agreement", "disagree", "image and timeline on opposite\nsides of the cohort median"),
            (12.0, "Reliability card", "few cases", "measured in this phase of care\nand enhancement state")]
    for y, name, value, detail in conf:
        text(69.5, y + 3.4, name, size=6.8, weight="bold")
        text(69.5, y, value, size=6.6)
        text(69.5, y - 2.4, detail, size=6.2, colour=grey, va="top")

    # Report: record -> local language model -> deterministic check -> report.
    ax.plot([89.5, 89.5], [3.0, 53.5], color=rule, lw=0.5)
    steps = [(49.5, "Per-scan record", "every value with its source"),
             (37.0, "Local language model", "writes the text; sees no\nimages, does no arithmetic"),
             (23.5, "Check", "every number matched\nagainst the record"),
             (10.0, "Report", "")]
    bw, bh, bx0 = 18.5, 7.6, 91.5
    for i, (y, name, detail) in enumerate(steps):
        ax.add_patch(Rectangle((bx0, y - bh / 2), bw, bh, fc="white", ec=ink if name == "Report" else rule, lw=0.5))
        text(bx0 + 1.0, y + bh / 2 - 1.7, name, size=6.6, weight="bold")
        if detail:
            text(bx0 + 1.0, y + bh / 2 - 3.6, detail, size=6.0, colour=grey, va="top")
        else:
            for j in range(3):
                ax.plot([bx0 + 1.0, bx0 + bw - 1.0 - 3.0 * (j % 2)], [y - 0.4 - 1.3 * j] * 2, color="#9e9e9e", lw=0.4)
        if i < len(steps) - 1:
            arrow((bx0 + bw / 2, y - bh / 2), (bx0 + bw / 2, steps[i + 1][0] + bh / 2))

    # ---------------------------------------------------------------- Panel B: evaluation
    xb, wb, yb, hb = 0.035, 0.955, 0.02, 0.27
    bx = fig.add_axes([xb, yb, wb, hb])
    bx.set(xlim=(0, 110), ylim=(0, 26)); bx.axis("off")
    panel(fig, LETTER_X, bx, "B"); title(bx, "How it was evaluated")

    def block(x, y, w, h, name, detail, edge=rule):
        bx.add_patch(Rectangle((x, y), w, h, fc="white", ec=edge, lw=0.5))
        bx.text(x + 1.0, y + h - 1.6, name, fontsize=6.8, weight="bold", color=ink, va="top")
        bx.text(x + 1.0, y + h - 4.6, detail, fontsize=6.3, color=grey, va="top", linespacing=1.2)

    def barrow(a, b):
        bx.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=5.5, color=ink, lw=0.6,
                                     shrinkA=0, shrinkB=0))

    block(0.5, 7.0, 21.0, 13.0, "MU-Glioma-Post", "public development cohort\n5 × 5 patient-grouped CV\n"
          "146 intended-use scans")
    block(27.0, 7.0, 20.0, 13.0, "Models locked", "fitted on 181 grade 4 scans\ntransfer rules fixed\n"
          "before external scoring")
    block(53.0, 14.5, 25.0, 10.5, "LUMIERE", "178 scans\nno treatment dates")
    block(53.0, 1.0, 25.0, 10.5, "UCSF-ALPTDG", "69 second scans scored\n130 reported")
    block(84.0, 7.0, 25.5, 13.0, "Reports checked", "406 in total\n114 MU, 162 LUMIERE,\n130 UCSF", edge=ink)
    barrow((21.5, 13.5), (27.0, 13.5))
    barrow((47.0, 13.5), (53.0, 19.75)); barrow((47.0, 13.5), (53.0, 6.25))
    barrow((78.0, 19.75), (84.0, 15.0)); barrow((78.0, 6.25), (84.0, 12.0))
    save(fig, output, "fig1_system")
