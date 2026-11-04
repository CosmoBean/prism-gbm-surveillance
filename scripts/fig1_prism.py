"""Figure 1: PRISM as a flowchart (A), and how it was evaluated (B).

Drawn, not data: the MRI slices come from `schematic_slice` (no patient image), and every value is the synthetic
example of Figure 5 (enhancing 4.0 -> 6.0 cc, FLAIR 31.0 cc, timeline 0.21, images 0.64, combined 0.33, few cases
1 of 9). Panel B carries only cohort and report counts (NUMBERS.md 1, 7). Plain journal style: hairlines, square
corners, one sans-serif face, colour only for the two pathways and the combined score.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle


def fig1(output: Path) -> None:
    from generate_system_first_figures import C, LETTER_X, WIDTH, panel, save, schematic_slice, title

    ink, grey, rule, serif = "#1a1a1a", "#5f5f5f", "#9e9e9e", "Liberation Serif"
    W, H = 180.0, 118.0                      # drawing units; square because W/H equals the figure aspect
    fig = plt.figure(figsize=(WIDTH, WIDTH * H / W))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, W), ylim=(0, H)); ax.axis("off")
    to_fig = lambda x, y: (x / W, y / H)

    def text(x, y, s, size=6.6, colour=ink, **kw):
        kw.setdefault("ha", "left"); kw.setdefault("va", "center")
        return ax.text(x, y, s, fontsize=size, color=colour, linespacing=1.2, **kw)

    def arrow(a, b, colour=ink, lw=0.8):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=6, color=colour, lw=lw,
                                     shrinkA=0, shrinkB=0, zorder=4))

    def rect(x0, y0, x1, y1, edge=rule, lw=0.5, face="white", ls="-", accent=None):
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=face, ec=edge, lw=lw, ls=ls, zorder=2))
        if accent:
            ax.add_patch(Rectangle((x0, y0), 1.0, y1 - y0, fc=accent, ec="none", zorder=3))

    def heading(x, y, name, lines="", size=6.8):
        text(x, y, name, size=size, weight="bold", va="top")
        if lines:
            text(x, y - 3.6, lines, size=6.5, colour=grey, va="top")

    # ---------------------------------------------------------------- Panel A
    text(4.5, 113.0, "At each follow up MRI after treatment, has the tumour progressed?", size=8.5, weight="bold",
         va="baseline")
    panel_a = text(0.6, 113.0, "A", size=10, weight="bold", va="baseline")

    # Stage tags, and the bracket that marks what PRISM adds: two pathways kept apart, reported side by side.
    for x, s in [(1.0, "1  Inputs"), (44.0, "2  Measure"), (81.0, "3  Score"), (114.0, "4  Confidence"),
                 (151.0, "5  Report")]:
        text(x, 100.5, s, size=6.8, colour=grey, va="baseline")
    ax.plot([44, 44, 106, 106], [103.2, 104.6, 104.6, 103.2], color=ink, lw=0.6)
    text(75.0, 106.0, "PRISM keeps image and timeline evidence apart and reports them side by side", size=6.6,
         ha="center", va="bottom", style="italic")

    # Lane 1, images: previous and current scan -> segmentation and measurement -> image score.
    for x0, name, scale, seed in [(1.0, "previous", 0.82, 3), (20.0, "current", 1.0, 4)]:
        f0, f1 = to_fig(x0, 78.0), to_fig(x0 + 17.0, 95.0)
        iax = fig.add_axes([f0[0], f0[1], f1[0] - f0[0], f1[1] - f0[1]])
        schematic_slice(iax, scale, seed=seed)
        for t in list(iax.texts):
            t.remove()
        text(x0 + 8.5, 76.0, name, size=6.5, colour=grey, ha="center", va="top")
    text(1.0, 70.0, "T1-contrast and FLAIR MRI", size=6.5, colour=grey, style="italic", va="top")

    rect(44, 78, 74, 95, accent=C["images"])
    heading(46.5, 93.2, "Segmentation", "enhancing tumour\n4.0 → 6.0 cc\nFLAIR 31.0 cc")
    arrow((38.5, 86.5), (44, 86.5), C["images"])

    # Lane 2, timeline: treatment dates and clinical record -> position in treatment -> timeline score.
    ty = 55.0
    ax.plot([1.0, 38.0], [ty, ty], color=ink, lw=0.6)
    ax.add_patch(Rectangle((9.0, ty - 1.0), 8.0, 2.0, fc="#d9d9d9", ec="none"))
    for x, s, w in [(5.0, "surgery", 0.6), (13.0, "chemoRT", 0.6), (33.0, "scan", 1.3)]:
        ax.plot([x, x], [ty - 1.0, ty + 1.0], color=ink, lw=w)
        text(x, ty + 2.6 if s != "chemoRT" else ty - 2.8, s, size=6.5, colour=grey, ha="center")
    rect(1.0, 42.5, 38.0, 48.5)
    text(19.5, 45.5, "age  ·  sex  ·  IDH  ·  MGMT", size=6.5, ha="center")
    text(1.0, 40.5, "treatment dates, clinical record", size=6.5, colour=grey, style="italic", va="top")

    rect(44, 42, 74, 59, accent=C["timeline"])
    heading(46.5, 57.2, "Position in treatment", "8 weeks after the end\nof radiotherapy,\nwith the clinical record")
    arrow((38.5, 51.0), (44, 51.0), C["timeline"])

    # Scores: three separately fitted models; the combined model sees both lanes.
    scores = [("images", 86.5, "Image score", 0.64), ("combined", 68.5, "Combined score", 0.33),
              ("timeline", 50.5, "Timeline score", 0.21)]
    sx0, sx1 = 81.0, 106.0
    for key, y, name, value in scores:
        rect(sx0, y - 5.5, sx1, y + 5.5, accent=C[key])
        text(sx0 + 2.5, y + 2.4, name, size=6.8, weight="bold")
        ax.add_patch(Rectangle((sx0 + 2.5, y - 3.2), 15.0, 1.8, fc="#e6e6e6", ec="none", zorder=3))
        ax.add_patch(Rectangle((sx0 + 2.5, y - 3.2), 15.0 * value, 1.8, fc=C[key], ec="none", zorder=3))
        text(sx0 + 18.5, y - 2.3, f"{value:.2f}", size=6.6)
    arrow((74, 86.5), (sx0, 86.5), C["images"])
    arrow((74, 50.5), (sx0, 50.5), C["timeline"])
    arrow((74, 81.0), (sx0, 71.0), C["images"])
    arrow((74, 56.0), (sx0, 66.0), C["timeline"])
    text(sx0, 38.6, "example values (Figure 5)", size=6.5, colour=grey, style="italic", va="top")

    # All three scores feed one confidence statement.
    cx = 110.0
    for _, y, _, _ in scores:
        ax.plot([sx1, cx], [y, y], color=ink, lw=0.8)
    ax.plot([cx, cx], [50.5, 86.5], color=ink, lw=0.8)
    arrow((cx, 68.5), (114.0, 68.5))

    rect(114, 42, 145, 95, face="#f6f6f6")
    conf = [(93.0, "80% conformal set", "{progression,\n no progression}", "both outcomes"),
            (75.0, "Pathway agreement", "disagree", "image above, timeline below\ntheir cohort medians"),
            (57.0, "Reliability card", "few cases", "1 of 9 such scans was\nprogression")]
    for y, name, value, detail in conf:
        text(116.0, y, name, size=6.8, weight="bold", va="top")
        v = text(116.0, y - 3.6, value, size=6.6, va="top")
        text(116.0, y - 3.6 - 3.0 * (value.count("\n") + 1) - 0.6, detail, size=6.5, colour=grey, va="top")

    # Report chain: record -> local language model -> checker -> report.
    chain = [(84.5, 95.0, "Record for the scan", "every value with\nits source", "-"),
             (65.0, 79.0, "Local language model", "writes the text, sees\nno images, does no\narithmetic", "--"),
             (42.0, 59.0, "Checker", "every number and flag\nmust be in the record,\nor the text is rejected", "-")]
    for y0, y1, name, detail, ls in chain:
        rect(151, y0, 179.5, y1, edge=ink if ls == "--" else rule, ls=ls)
        heading(153.0, y1 - 1.8, name, detail)
    arrow((145, 89.5), (151, 89.5))
    arrow((165.5, 84.5), (165.5, 79.0))
    arrow((165.5, 65.0), (165.5, 59.0))
    arrow((165.5, 42.0), (165.5, 36.0))

    # The output a clinician reads: a synthetic report card.
    rx0, rx1, ry0, ry1 = 114.0, 179.5, 3.0, 36.0
    rect(rx0, ry0, rx1, ry1, edge=ink, lw=1.0)
    text(rx0 + 2.0, ry1 - 2.4, "PRISM surveillance report", size=7.6, weight="bold", va="top").set_family(serif)
    text(rx1 - 2.0, ry1 - 2.6, "SYNTHETIC EXAMPLE", size=6.5, colour=grey, ha="right", va="top")
    for i, (key, _, name, value) in enumerate(scores):
        y = ry1 - 9.6 - 3.4 * i
        text(rx0 + 2.0, y, name.replace(" score", ""), size=6.5).set_family(serif)
        ax.add_patch(Rectangle((rx0 + 15.0, y - 0.8), 20.0, 1.6, fc="#e6e6e6", ec="none", zorder=3))
        ax.add_patch(Rectangle((rx0 + 15.0, y - 0.8), 20.0 * value, 1.6, fc=C[key], ec="none", zorder=3))
        text(rx0 + 36.5, y, f"{value:.2f}", size=6.5).set_family(serif)
    body = ("Enhancing tumour is 2.0 cc larger than at the previous scan. The two pathways disagree, and the 80% "
            "conformal set holds both outcomes. This situation has few cases (1 of 9 scans was progression).")
    text(rx0 + 2.0, ry1 - 21.0, "\n".join(textwrap.wrap(body, 60)), size=6.5, va="top").set_family(serif)

    # ---------------------------------------------------------------- Panel B (strip)
    text(0.6, 28.5, "B", size=10, weight="bold", va="baseline")
    text(4.5, 28.5, "How it was evaluated", size=8.5, weight="bold", va="baseline")
    blocks = [(1.0, 29.0, "MU-Glioma-Post", "public development\ncohort, 5 × 5 cross\nvalidation by patient"),
              (35.0, 58.0, "Models locked", "fitted once\non MU"),
              (64.0, 91.0, "LUMIERE, UCSF", "applied\nunchanged"),
              (97.0, 108.0, "406", "reports\nchecked")]
    for i, (x0, x1, name, detail) in enumerate(blocks):
        rect(x0, 6.0, x1, 23.0, edge=ink if i == 3 else rule)
        heading(x0 + 1.5, 21.0, name, detail)
        if i:
            arrow((blocks[i - 1][1], 14.5), (x0, 14.5))
    del panel_a
    save(fig, output, "fig1_system")
