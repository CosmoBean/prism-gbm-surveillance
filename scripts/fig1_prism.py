"""Figure 1, illustrated: PRISM splits one progression score into its evidence, and how it was evaluated.

Drawn, not data: the MRI slices come from `schematic_slice` (no patient image), the scores are the synthetic
example of Figure 5A (timeline 0.21, images 0.64, combined 0.33), and Panel B carries only the cohort and report
counts of the earlier box diagram (NUMBERS.md 1, 7).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


def fig1(output: Path) -> None:
    from generate_system_first_figures import C, LETTER_X, WIDTH, panel, save, schematic_slice, tint, title

    ink, grey = C["ink"], "#4a5563"
    height = 6.1
    fig = plt.figure(figsize=(WIDTH, height))

    # ---------------------------------------------------------------- Panel A: one scan through PRISM
    xa, wa, ya, ha = 0.035, 0.955, 0.355, 0.585
    ax = fig.add_axes([xa, ya, wa, ha])
    ax.set(xlim=(0, 110), ylim=(0, 60)); ax.axis("off")
    panel(fig, LETTER_X, ax, "A"); title(ax, "What PRISM does at each scan")
    to_fig = lambda x, y: ((xa + wa * x / 110), (ya + ha * y / 60))

    def label(x, y, text, size=6.8, **kw):
        kw.setdefault("color", ink); kw.setdefault("ha", "center"); kw.setdefault("va", "center")
        ax.text(x, y, text, fontsize=size, **kw)

    def heading(x, y, text, colour=ink):
        label(x, y, text, size=7.4, weight="bold", color=colour)

    # Inputs: the scan and an earlier scan (drawn), the treatment timeline and the clinical record.
    heading(12, 57.5, "Inputs")
    for i, (dx, dy, scale, name) in enumerate([(5.0, 4.0, 0.82, "earlier scan"), (0.0, 0.0, 1.0, "this scan")]):
        x0, y0 = 2.0 + dx, 33.0 + dy
        f0, f1 = to_fig(x0, y0), to_fig(x0 + 15, y0 + 17)
        iax = fig.add_axes([f0[0], f0[1], f1[0] - f0[0], f1[1] - f0[1]])
        schematic_slice(iax, scale, seed=3 + i)
        iax.set_aspect("auto")
        if i == 0:                                   # back scan: no orientation letters (they would overlap)
            for t in list(iax.texts):
                t.remove()
        for s in iax.spines.values():
            s.set_visible(True)
        iax.patch.set_edgecolor("white")
        ax.add_patch(Rectangle((x0, y0), 15, 17, fill=False, ec=C["images"], lw=0.8 if i == 0 else 1.4, zorder=5))
    label(9.5, 31.4, "this scan", size=6.6, va="top")
    label(19.5, 54.6, "earlier scan", size=6.6, color=grey)
    label(12, 26.6, "scans and masks", size=6.6, color=grey, style="italic")

    # Treatment timeline.
    ty = 18.5
    ax.plot([1.5, 23], [ty, ty], color=ink, lw=0.9)
    ax.add_patch(FancyArrowPatch((22.5, ty), (24.2, ty), arrowstyle="-|>", mutation_scale=6, color=ink, lw=0.9))
    ax.plot(2.5, ty, marker="v", ms=4.5, color=ink)
    label(2.5, ty - 3.0, "surgery", size=6.5, color=grey, va="top")
    ax.add_patch(Rectangle((4.5, ty - 1.0), 6.5, 2.0, fc=tint(C["timeline"], 0.45), ec="none"))
    label(7.75, ty + 2.4, "chemo-RT", size=6.5, color=grey)
    for x in (13.5, 17.0):
        ax.plot([x, x], [ty - 1.2, ty + 1.2], color=grey, lw=0.9)
    ax.plot([20.8, 20.8], [ty - 1.8, ty + 1.8], color=ink, lw=1.6)
    label(22.6, ty - 3.0, "this scan", size=6.5, va="top", ha="right")
    label(12, 12.8, "treatment timeline", size=6.6, color=grey, style="italic")

    # Clinical record chips.
    for i, chip in enumerate(["age", "sex", "IDH", "MGMT"]):
        x = 0.8 + i * 5.7
        ax.add_patch(FancyBboxPatch((x, 4.6), 5.3, 3.2, boxstyle="round,pad=0,rounding_size=0.8",
                                    fc=tint(C["timeline"], 0.85), ec=C["timeline"], lw=0.8))
        label(x + 2.65, 6.2, chip, size=6.5)
    label(12, 1.6, "clinical record", size=6.6, color=grey, style="italic")

    # White light: everything enters the prism as one undivided beam.
    ax.add_patch(Polygon([(26.0, 52.0), (26.0, 3.0), (36.6, 27.0), (36.6, 31.0)], closed=True,
                         fc="#e9ecf0", ec="none", zorder=1))
    label(30.8, 29.0, "one score:\nevidence\nmixed", size=6.5, color=grey,
          linespacing=1.15, zorder=2)
    # Brackets: which inputs each pathway keeps (colours match the beams leaving the prism).
    for key, y_lo, y_hi in [("images", 27.5, 53.5), ("timeline", 0.5, 23.0)]:
        ax.plot([25.0, 25.0], [y_lo, y_hi], color=C[key], lw=1.6, solid_capstyle="butt")
        for y in (y_lo, y_hi):
            ax.plot([24.2, 25.0], [y, y], color=C[key], lw=1.6, solid_capstyle="butt")

    # The prism: a glass triangle with a soft vertical gradient.
    tri = [(35.0, 13.0), (49.0, 13.0), (42.0, 45.0)]
    glass = Polygon(tri, closed=True, fc="none", ec=ink, lw=1.1, zorder=4)
    ax.add_patch(glass)
    grad = np.linspace(0.0, 1.0, 64)[:, None] * np.ones((1, 8))
    im = ax.imshow(grad, extent=(35, 49, 13, 45), origin="lower", cmap="Greys", vmin=-0.6, vmax=2.4,
                   aspect="auto", zorder=3, alpha=0.9)
    im.set_clip_path(Polygon(tri, closed=True, transform=ax.transData))
    ax.plot([38.5, 42.0], [21.0, 37.0], color="white", lw=1.2, alpha=0.9, zorder=4)   # glint
    label(42.0, 9.6, "PRISM", size=8.4, weight="bold")
    label(42.0, 6.2, "splits the score\ninto its evidence", size=6.6, color=grey, linespacing=1.15)

    # Beams leaving the prism: images up, combined straight on, timeline down.
    exit_pt = (45.6, 29.0)
    beams = [("images", 47.5, "Image pathway", "from scans and masks;\nno dates", 0.64),
             ("combined", 29.0, "Combined score", "one model, both inputs", 0.33),
             ("timeline", 10.5, "Timeline pathway", "from timeline and\nclinical record", 0.21)]
    gx0, gx1 = 57.0, 69.0
    for key, y, name, detail, value in beams:
        ax.add_patch(Polygon([(exit_pt[0], exit_pt[1] - 0.9), (exit_pt[0], exit_pt[1] + 0.9),
                              (gx0 - 1.0, y + 1.5), (gx0 - 1.0, y - 1.5)], closed=True,
                             fc=tint(C[key], 0.35), ec="none", zorder=2))
        label(gx0, y + 6.3, name, size=7.2, weight="bold", ha="left", color=C[key] if key != "combined" else "#c4610a")
        label(gx0, y - 4.4, detail, size=6.5, ha="left", va="top", color=grey, linespacing=1.15)
        ax.add_patch(FancyBboxPatch((gx0, y - 1.3), gx1 - gx0, 2.6, boxstyle="round,pad=0,rounding_size=1.1",
                                    fc="#eef0f3", ec="none", zorder=3))
        ax.add_patch(FancyBboxPatch((gx0, y - 1.3), (gx1 - gx0) * value, 2.6,
                                    boxstyle="round,pad=0,rounding_size=1.1", fc=C[key], ec="none", zorder=4))
        label(gx1 + 1.0, y, f"{value:.2f}", size=7.0, ha="left", weight="bold")
    label(63.0, 1.6, "example values (Figure 5)", size=6.5, color=grey, style="italic")

    # Confidence: conformal set, pathway agreement, reliability card.
    cx = 83.5
    heading(cx, 57.5, "Confidence", C["thin"])
    for i, (txt, fc) in enumerate([("P", tint(C["thin"], 0.55)), ("NP", tint(C["thin"], 0.55))]):
        ax.add_patch(FancyBboxPatch((cx - 5.6 + i * 5.8, 47.2), 5.0, 3.6, boxstyle="round,pad=0,rounding_size=0.9",
                                    fc=fc, ec=ink, lw=0.6))
        label(cx - 3.1 + i * 5.8, 49.0, txt, size=6.8, weight="bold")
    label(cx, 44.6, "80% set: one\noutcome or both", size=6.5, color=grey, va="top", linespacing=1.15)

    ax.plot(cx - 4.2, 33.5, "o", ms=6.5, color=C["images"])
    ax.plot(cx + 4.2, 33.5, "o", ms=6.5, color=C["timeline"])
    ax.add_patch(FancyArrowPatch((cx - 4.2, 34.8), (cx - 4.2, 38.4), arrowstyle="-|>", mutation_scale=6,
                                 color=C["images"], lw=1.0))
    ax.add_patch(FancyArrowPatch((cx + 4.2, 32.2), (cx + 4.2, 28.6), arrowstyle="-|>", mutation_scale=6,
                                 color=C["timeline"], lw=1.0))
    ax.plot([cx - 7.5, cx + 7.5], [33.5, 33.5], color=grey, lw=0.6, ls=":")
    label(cx, 25.8, "agree: same side\nof the median?", size=6.5, color=grey, va="top", linespacing=1.15)

    ax.add_patch(FancyBboxPatch((cx - 6.0, 7.6), 12.0, 9.2, boxstyle="round,pad=0,rounding_size=0.9",
                                fc="white", ec=ink, lw=0.7))
    for j, (w, fc) in enumerate([(9.0, ink), (6.0, tint(C["thin"], 0.55)), (7.5, ink)]):
        ax.add_patch(Rectangle((cx - 4.6, 14.0 - j * 2.4), w, 1.3, fc=fc, ec="none"))
    label(cx, 5.6, "reliability card:\ntested or few cases", size=6.5, color=grey, va="top", linespacing=1.15)
    ax.plot([75.0, 75.0], [4.0, 55.0], color="#d5dae0", lw=0.6)

    # Record -> local language model -> checker -> report.
    rx = 102.0
    heading(rx, 57.5, "Report")
    ax.add_patch(Polygon([(rx - 5, 44.5), (rx + 3, 44.5), (rx + 5, 46.5), (rx + 5, 54.5), (rx - 5, 54.5)],
                         closed=True, fc=tint(C["combined"], 0.85), ec=ink, lw=0.7))
    for j in range(4):
        ax.plot([rx - 3.6, rx + 1.0], [52.6 - j * 2.0] * 2, color=grey, lw=0.6)
        ax.plot(rx + 2.6, 52.6 - j * 2.0, "s", ms=1.8, color=ink)
    label(rx, 43.6, "record: every value\nwith its source", size=6.5, color=grey, va="top", linespacing=1.15)

    ax.add_patch(FancyBboxPatch((rx - 4.5, 28.0), 9.0, 6.4, boxstyle="round,pad=0,rounding_size=0.8",
                                fc=ink, ec=ink, lw=0.7))
    for k in range(4):
        for side in (-1, 1):
            ax.plot([rx + side * 4.5, rx + side * 5.7], [29.0 + k * 1.45] * 2, color=ink, lw=0.8)
    label(rx, 31.2, "LLM", size=7.0, weight="bold", color="white")
    label(rx, 26.4, "local model writes;\nsees no images", size=6.5, color=grey, va="top", linespacing=1.15)

    ax.add_patch(Ellipse((rx - 3.6, 13.8), 4.6, 4.6, fc="white", ec=ink, lw=0.8))
    ax.plot([rx - 5.0, rx - 4.0, rx - 2.2], [13.9, 12.7, 15.2], color=ink, lw=1.1)
    ax.add_patch(Rectangle((rx + 0.2, 9.0), 6.4, 9.0, fc="white", ec=ink, lw=0.7))
    for j in range(5):
        ax.plot([rx + 1.2, rx + 5.6 - (j % 2) * 1.4], [16.6 - j * 1.5] * 2, color=grey, lw=0.6)
    label(rx, 5.6, "checked against the\nrecord, then sent", size=6.5, color=grey, va="top", linespacing=1.15)
    for y0, y1 in [(38.6, 35.0), (21.6, 18.8)]:
        ax.add_patch(FancyArrowPatch((rx, y0), (rx, y1), arrowstyle="-|>", mutation_scale=7, color=ink, lw=0.8))
    ax.plot([92.0, 92.0], [4.0, 55.0], color="#d5dae0", lw=0.6)

    # ---------------------------------------------------------------- Panel B: evaluation
    xb, wb, yb, hb = 0.035, 0.955, 0.01, 0.295
    bx = fig.add_axes([xb, yb, wb, hb])
    bx.set(xlim=(0, 110), ylim=(-7.5, 26)); bx.axis("off")
    panel(fig, LETTER_X, bx, "B"); title(bx, "How it was evaluated")

    def cylinder(x, y, w, h, colour):
        bx.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=colour, ec="none"))
        bx.plot([x - w / 2, x - w / 2], [y - h / 2, y + h / 2], color=ink, lw=0.7)
        bx.plot([x + w / 2, x + w / 2], [y - h / 2, y + h / 2], color=ink, lw=0.7)
        bx.add_patch(Ellipse((x, y - h / 2), w, h * 0.32, fc=colour, ec=ink, lw=0.7))
        bx.add_patch(Rectangle((x - w / 2 + 0.05, y - h / 2), w - 0.1, h * 0.1, fc=colour, ec="none"))
        bx.add_patch(Ellipse((x, y + h / 2), w, h * 0.32, fc=tint(colour, 0.5), ec=ink, lw=0.7))

    cylinder(6.0, 11.5, 6.0, 8.0, tint(C["timeline"], 0.55))
    bx.text(11.0, 15.4, "MU-Glioma-Post", fontsize=7.4, weight="bold", color=ink, va="center")
    bx.text(11.0, 13.2, "development: 5 × 5\npatient-grouped CV,\n146 intended-use scans;\n"
            "locked on all 181\ngrade 4 scans", fontsize=6.6, color=ink, va="top", linespacing=1.2)

    lock_x = 42.0
    bx.add_patch(FancyBboxPatch((lock_x - 2.2, 10.0), 4.4, 3.6, boxstyle="round,pad=0,rounding_size=0.5",
                                fc=ink, ec=ink))
    bx.add_patch(Ellipse((lock_x, 13.6), 3.0, 4.0, fc="none", ec=ink, lw=1.2))
    bx.text(lock_x, 6.8, "locked, plans\ncommitted in advance,\napplied unchanged", fontsize=6.5, color=grey, ha="center",
            va="top", linespacing=1.15)
    bx.add_patch(FancyArrowPatch((33.5, 11.8), (lock_x - 3.0, 11.8), arrowstyle="-|>", mutation_scale=7,
                                 color=ink, lw=0.8))
    for y in (19.0, 5.0):
        bx.add_patch(FancyArrowPatch((lock_x + 3.0, 11.8), (56.5, y), arrowstyle="-|>", mutation_scale=7,
                                     connectionstyle="arc3,rad=0", color=ink, lw=0.8))

    for y, name, detail in [(19.0, "LUMIERE", "178 scans, no treatment dates"),
                            (5.0, "UCSF-ALPTDG", "69 second scans scored\n(detection); 130 reported")]:
        cylinder(60.5, y, 5.0, 6.0, tint(C["images"], 0.55))
        bx.text(64.5, y + 1.3, name, fontsize=7.2, weight="bold", color=ink, va="center")
        bx.text(64.5, y - 0.6, detail, fontsize=6.6, color=ink, va="top", linespacing=1.15)

    bx.add_patch(FancyBboxPatch((90.6, 6.0), 19.3, 11.5, boxstyle="round,pad=0,rounding_size=1.2",
                                fc=tint(C["combined"], 0.85), ec=ink, lw=0.7))
    bx.text(100.25, 16.2, "406 reports\nchecked", fontsize=7.4, weight="bold", ha="center", va="top", color=ink,
            linespacing=1.1)
    bx.text(100.25, 11.0, "114 MU, 162 LUMIERE,\n130 UCSF second scans", fontsize=6.5, ha="center", va="top",
            color=ink, linespacing=1.15)
    for y in (19.0, 5.0):
        bx.add_patch(FancyArrowPatch((87.4, y), (90.2, 11.8), arrowstyle="-|>", mutation_scale=7, color=ink,
                                     lw=0.8))
    # MU reports go to the badge too: routed under the external cohorts.
    route_y = -6.0
    bx.plot([6.0, 6.0, 100.25], [6.4, route_y, route_y], color=ink, lw=0.8)
    bx.add_patch(FancyArrowPatch((100.25, route_y), (100.25, 5.6), arrowstyle="-|>", mutation_scale=7, color=ink,
                                 lw=0.8))
    bx.text(24.0, route_y + 0.8, "114 MU reports", fontsize=6.5, color=grey, va="bottom")
    save(fig, output, "fig1_system")
