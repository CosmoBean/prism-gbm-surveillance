"""Generate the five manuscript figures from verified aggregate values (docs/manuscript/NUMBERS.md).

Every value below is an aggregate from NUMBERS.md (section named beside it); no patient-level data are read. The
example report in Figure 5 is synthetic: an invented scan written in the v3.1 report format (its slices are drawn by
schematic_slice, not taken from any patient), with the MU card row
quoted in the Discussion (1 of 9 scans).

Layout conventions shared by all five figures: the canvas is 7.2 in wide and is saved as drawn (no tight bounding
box), so every figure scales the same in print; no text is smaller than 6.5 pt; panel letters are drawn with
`panel()` at fixed figure positions and panel titles with `title()` (left-aligned on the axes).
"""
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.titlesize": 8.5, "axes.labelsize": 7.5,
                     "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "axes.spines.top": False,
                     "axes.spines.right": False, "pdf.fonttype": 42, "axes.linewidth": 0.7,
                     "xtick.major.width": 0.7, "ytick.major.width": 0.7})

# One colour per kind of evidence, used in every figure.
C = {"clinical": "#9d9d9d", "timeline": "#4c78a8", "images": "#2a9d8f", "images2": "#8fd1c7",
     "combined": "#f58518", "et": "#5a5a5a", "ink": "#22313f", "soft": "#f3f5f8", "thin": "#e45756"}

WIDTH = 7.2      # inches, every figure
LETTER_X = 0.01  # figure fraction, left column panel letters
MIN_PT = 6.5     # smallest text anywhere


def save(fig, output: Path, name: str) -> None:
    place_letters(fig)
    for extension in ("pdf", "png"):
        fig.savefig(output / f"{name}.{extension}", dpi=300, bbox_inches=None, facecolor="white")
    plt.close(fig)


def panel(fig, x, ax, text):
    """Bold panel letter at a fixed figure x, top-aligned with the top of that panel's title (placed at save time)."""
    fig.__dict__.setdefault("_letters", []).append((x, ax, text))


def place_letters(fig) -> None:
    fig.canvas.draw()
    height = fig.bbox.height
    for x, ax, text in getattr(fig, "_letters", []):
        top = ax._left_title.get_window_extent().y1 / height
        fig.text(x, top + 0.002, text, fontsize=10, weight="bold", va="top", ha="left")


def title(ax, text, pad=4):
    ax.set_title(text, loc="left", weight="bold", fontsize=8.5, pad=pad)


def tint(hex_colour: str, amount: float = 0.82) -> str:
    rgb = matplotlib.colors.to_rgb(hex_colour)
    return matplotlib.colors.to_hex([c + (1 - c) * amount for c in rgb])


def box(ax, x, y, w, h, name, detail="", face=C["soft"], edge=None, size=6.7):
    """Rounded box with a bold name line and up to a few plain detail lines, centred as one block."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.010", facecolor=face,
                                edgecolor=edge or C["ink"], linewidth=0.7, clip_on=False))
    lines = detail.split("\n") if detail else []
    step = size * 1.3                                  # line height, points
    top = (1 + len(lines)) * step / 2
    centre = (x + w / 2, y + h / 2)
    ax.annotate(name, centre, xytext=(0, top), textcoords="offset points", ha="center", va="top",
                fontsize=size + 0.4, weight="bold", color=C["ink"])
    if lines:
        ax.annotate("\n".join(lines), centre, xytext=(0, top - step - 0.6), textcoords="offset points", ha="center",
                    va="top", fontsize=size, color=C["ink"], linespacing=1.18)


def arrow(ax, start, end, colour=None):
    ax.annotate("", end, start, arrowprops={"arrowstyle": "-|>", "color": colour or C["ink"], "lw": 0.75,
                                            "shrinkA": 0, "shrinkB": 0, "mutation_scale": 7})


def ci(v):
    return [[v[0] - v[1]], [v[2] - v[0]]]


def fig1(output: Path) -> None:
    """The system (A) and how it was evaluated (B). Counts: NUMBERS.md 2.2, 6, 7."""
    fig = plt.figure(figsize=(WIDTH, 4.9))
    ax = fig.add_axes([0.045, 0.375, 0.945, 0.55]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    panel(fig, LETTER_X, ax, "A"); title(ax, "What PRISM does at each scan", pad=6)

    h, w = 0.165, 0.17
    col = (0.0, 0.205, 0.41, 0.625, 0.825)                     # column left edges
    row = (0.885, 0.63, 0.375, 0.10)                          # row centres
    mid = [x + w / 2 for x in col]

    def at(c, r, *args, **kw):
        box(ax, col[c], row[r] - h / 2, w, h, *args, **kw)

    # inputs
    at(0, 0, "Surveillance MRI", "+ masks, earlier scans")
    at(0, 1, "Clinical record", "age, sex, IDH, MGMT")
    at(0, 2, "Treatment timeline", "dates of each therapy")
    # measurements and pathways
    at(1, 0, "Measurements", "volume, shape, change", face=tint(C["images"]))
    at(2, 0, "Image pathway", "ridge model, no dates", face=tint(C["images"], 0.6))
    at(2, 1, "Combined score", "one model, both inputs", face=tint(C["combined"], 0.6))
    at(2, 2, "Timeline pathway", "ridge, position in care", face=tint(C["timeline"], 0.6))
    arrow(ax, (col[0] + w, row[0]), (col[1], row[0])); arrow(ax, (col[1] + w, row[0]), (col[2], row[0]))
    arrow(ax, (col[0] + w, row[1] - 0.04), (col[2], row[2] + 0.04)); arrow(ax, (col[0] + w, row[2]), (col[2], row[2]))
    arrow(ax, (mid[2], row[0] - h / 2), (mid[2], row[1] + h / 2)); arrow(ax, (mid[2], row[2] + h / 2), (mid[2], row[1] - h / 2))
    # confidence
    face = tint(C["thin"], 0.85)
    at(3, 0, "Conformal set (80%)", "one outcome or both", face=face)
    at(3, 1, "Pathway agreement", "same side of median?", face=face)
    at(3, 2, "Reliability card", "tested scans like this", face=face)
    ax.text(mid[3], row[0] + h / 2 + 0.02, "Confidence", ha="center", va="bottom", fontsize=7.4, weight="bold",
            color=C["thin"])
    for y0, y1 in zip((row[1] + 0.045, row[1], row[1] - 0.045), row[:3]):
        arrow(ax, (col[2] + w, y0), (col[3], y1))
    # record, then the report pipeline down the right-hand column and back along the bottom row
    box(ax, col[4], row[1] - h / 2, w, row[0] - row[1] + h, "Evidence record", "every value\nwith its source",
        face="#fff3d6")
    for y0, y1 in zip(row[:3], (row[1] + 0.20, row[1] + 0.06, row[1] - 0.06)):
        arrow(ax, (col[3] + w, y0), (col[4], y1))
    at(4, 2, "Language model", "local; writes the report")
    at(4, 3, "Checker", "numbers, flags, wording")
    arrow(ax, (mid[4], row[1] - h / 2), (mid[4], row[2] + h / 2)); arrow(ax, (mid[4], row[2] - h / 2), (mid[4], row[3] + h / 2))
    box(ax, col[2], row[3] - h / 2, col[3] + w - col[2], h, "Report to the clinician",
        "figure, scores, confidence\nand what was not used", face=tint(C["combined"], 0.85))
    arrow(ax, (col[4], row[3]), (col[3] + w, row[3]))
    ax.text(col[0], row[3], "Where a cohort lacks treatment dates,\nthe timeline is reduced; the image\npathway needs no dates at all.",
            fontsize=6.8, color="#555555", ha="left", va="center", style="italic", linespacing=1.2)

    bx = fig.add_axes([0.045, 0.015, 0.945, 0.255]); bx.set_xlim(0, 1); bx.set_ylim(0, 1); bx.axis("off")
    panel(fig, LETTER_X, bx, "B"); title(bx, "How it was evaluated", pad=6)
    hb = 0.42
    box(bx, 0.00, 0.29, 0.285, hb, "MU-Glioma-Post (development)",
        "5 × 5 patient-grouped CV,\n146 intended-use scans;\nlocked on all 181 grade 4 scans", face=tint(C["timeline"], 0.85))
    box(bx, 0.325, 0.29, 0.155, hb, "Fit once on MU", "lock the models\nand write the plan")
    box(bx, 0.53, 0.54, 0.205, hb, "LUMIERE (locked)", "178 scans,\nno treatment dates", face=tint(C["images"], 0.85))
    box(bx, 0.53, 0.03, 0.205, hb, "UCSF-ALPTDG (locked)", "69 second scans\n(detection)", face=tint(C["images"], 0.85))
    box(bx, 0.785, 0.29, 0.205, hb, "Reports checked", "406 reports:\n114 MU, 162 LUMIERE,\n130 UCSF second scans",
        face="#fff3d6")
    arrow(bx, (0.285, 0.50), (0.325, 0.50)); arrow(bx, (0.48, 0.58), (0.53, 0.75)); arrow(bx, (0.48, 0.42), (0.53, 0.24))
    arrow(bx, (0.735, 0.75), (0.785, 0.60)); arrow(bx, (0.735, 0.24), (0.785, 0.40))
    save(fig, output, "fig1_system")


def fig2(output: Path) -> None:
    """AUC by pathway and cohort. NUMBERS.md 3, 4, 11, 12C."""
    groups = ["MU-Glioma-Post\ninternal (CV)", "LUMIERE\nlocked", "UCSF-ALPTDG\nlocked", "UCSF-ALPTDG\ntrained there"]
    series = [  # label, colour, [(auc, lo, hi) or None per group], primary?, open reference marker?
        ("Clinical data alone", C["clinical"], [(0.530, 0.450, 0.606), (0.554, 0.458, 0.635), (0.502, 0.364, 0.630), (0.407, 0.314, 0.494)], False, False),
        ("Timeline pathway", C["timeline"], [(0.822, 0.749, 0.902), (0.689, 0.600, 0.805), (0.561, 0.420, 0.687), (0.669, 0.549, 0.784)], False, False),
        ("Image pathway", C["images"], [(0.709, 0.630, 0.781), (0.655, 0.565, 0.733), (0.726, 0.603, 0.835), (0.863, 0.772, 0.934)], False, False),
        ("Images, single scan", C["images2"], [None, None, (0.795, 0.686, 0.887), (0.826, 0.729, 0.909)], False, False),
        ("Combined score", C["combined"], [(0.821, 0.744, 0.894), (0.773, 0.679, 0.857), (0.856, 0.758, 0.930), (0.871, 0.790, 0.938)], True, False),
        ("Enhancing volume alone†", C["et"], [(0.622, 0.530, 0.717), (0.662, 0.563, 0.751), (0.878, 0.793, 0.948), None], False, True),
    ]
    fig = plt.figure(figsize=(WIDTH, 3.0))
    ax = fig.add_axes([0.075, 0.16, 0.655, 0.80])
    ax.axvspan(2.5, 3.5, color="#f1f2f4", lw=0, zorder=0)
    ax.axvline(2.5, color="0.65", lw=0.7)
    ax.text(3.0, 0.985, "reference, not locked", ha="center", va="top", fontsize=6.6, color="0.35", style="italic")
    ax.axhline(0.5, color="0.55", lw=0.7, ls=":", zorder=1)
    ax.text(3.45, 0.497, "chance", fontsize=6.5, color="0.45", va="top", ha="right")
    step = 0.8 / 6
    handles = []
    for g in range(len(groups)):
        present = [s for s in series if s[2][g] is not None]
        for i, (label, colour, values, primary, reference) in enumerate(present):
            v = values[g]; x = g + (i - (len(present) - 1) / 2) * step
            if primary:
                style = dict(fmt="o", ms=6, color=colour, mfc=colour, mec="white", mew=0.6, elinewidth=1.6, capsize=0, zorder=4)
            elif reference:
                style = dict(fmt="D", ms=4.2, color=colour, mfc="white", mec=colour, mew=1.0, elinewidth=0.8, capsize=0, zorder=3)
            else:
                style = dict(fmt="o", ms=4.2, color=colour, mfc=colour, mec=colour, alpha=0.6, elinewidth=0.8, capsize=0, zorder=3)
            ax.errorbar(x, v[0], yerr=ci(v), **style)
    for label, colour, _, primary, reference in series:
        if primary:
            handles.append(Line2D([], [], marker="o", ms=6, color=colour, mec="white", mew=0.6, lw=1.6, label=label))
        elif reference:
            handles.append(Line2D([], [], marker="D", ms=4.2, color=colour, mfc="white", mew=1.0, lw=0.8, label=label))
        else:
            handles.append(Line2D([], [], marker="o", ms=4.2, color=colour, alpha=0.6, lw=0.8, label=label))
    ax.set(xticks=range(len(groups)), xlim=(-0.5, 3.5), ylim=(0.3, 1.0), ylabel="AUC (axis from 0.3)")
    ax.set_xticklabels(groups)
    ax.tick_params(axis="x", length=0)
    ax.legend(handles=handles, frameon=False, loc="center left", bbox_to_anchor=(1.01, 0.5), handlelength=1.6,
              labelspacing=0.9, fontsize=7)
    save(fig, output, "fig2_transport")


def forest(ax, rows, xlabel, ref=0.0, xlim=None):
    """Point-and-interval rows, each labelled above its line. rows: (label, est, lo, hi, colour, filled)."""
    for i, (label, est, lo, hi, colour, filled) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.plot([lo, hi], [y, y], color=colour, lw=1.3, solid_capstyle="butt")
        ax.plot(est, y, "o", color=colour, mfc=colour if filled else "white", ms=4.8, mew=1.1, zorder=3)
        ax.text(xlim[0] if xlim else lo, y + 0.22, label, fontsize=6.9, va="bottom", ha="left", color=C["ink"],
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.6}, zorder=2)
    ax.axvline(ref, color="0.5", lw=0.7, ls=":", zorder=1)
    ax.set_yticks([]); ax.spines["left"].set_visible(False)
    ax.set_ylim(-0.45, len(rows) - 0.25)
    ax.set_xlabel(xlabel)
    if xlim:
        ax.set_xlim(*xlim)


def fig3(output: Path) -> None:
    """What each score rests on. NUMBERS.md 5 (MU audit, UCSF audit, ladder)."""
    fig = plt.figure(figsize=(WIDTH, 4.7))
    ax_top = 0.885
    ax = fig.add_axes([0.06, 0.61, 0.36, ax_top - 0.61])
    panel(fig, LETTER_X, ax, "A"); title(ax, "MU: gain from adding the timeline\nto clinical data and images")
    forest(ax, [("Across phases of care", 0.114, 0.035, 0.196, C["timeline"], True),
                ("Within a phase of care", -0.016, -0.134, 0.109, C["timeline"], False)], "AUC difference",
           xlim=(-0.2, 0.3))

    bx = fig.add_axes([0.585, 0.61, 0.395, ax_top - 0.61])
    panel(fig, 0.51, bx, "B"); title(bx, "UCSF: progression calls\nfollow enhancement")
    labels = ["Enhancing\nvolume\nalone", "Single\nscan", "Image\npathway", "Single scan,\n'increased'\nscans only"]
    vals = [(0.878, 0.793, 0.948), (0.795, 0.686, 0.887), (0.726, 0.603, 0.835), (0.652, 0.444, 0.836)]
    faces = ["white", C["images2"], C["images"], "white"]
    edges = ["#3c3c3c", "white", "white", C["images"]]
    hatches = ["////", None, None, "...."]
    for i, (v, f, e, hch) in enumerate(zip(vals, faces, edges, hatches)):
        bx.bar(i, v[0], 0.66, color=f, edgecolor=e, hatch=hch, lw=0.6 if f == "white" else 0.4)
        bx.errorbar(i, v[0], yerr=ci(v), fmt="none", ecolor="#333", elinewidth=0.7, capsize=1.5)
    bx.axhline(0.5, color="0.55", lw=0.7, ls=":")
    bx.set(xticks=range(4), yticks=[0, 0.2, 0.4, 0.6, 0.8, 1.0], ylim=(0, 1.27), xlim=(-0.5, 3.5), ylabel="AUC")
    bx.set_xticklabels(labels, fontsize=6.6); bx.spines["left"].set_bounds(0, 1.0)
    bx.tick_params(axis="x", length=0)
    bx.text(3.5, 1.27, "Rated 'enhancement increased': progression\n27 of 29 scans, non-progression 10 of 40",
            ha="right", va="top", fontsize=6.6, color="#444444", linespacing=1.15)

    cx = fig.add_axes([0.085, 0.085, 0.895, 0.305])
    panel(fig, LETTER_X, cx, "C"); title(cx, "MU: the image model built in three steps")
    steps = ["Current scan's\nmeasurements", "+ change from\nearlier scans\n(image pathway)", "+ three schedule\ninputs"]
    across = [(0.659, 0.567, 0.733), (0.709, 0.630, 0.781), (0.806, 0.747, 0.865)]
    within = [(0.680, None, None), (0.677, 0.580, 0.767), (0.664, 0.576, 0.750)]
    xs = [0, 1, 2]
    cx.errorbar([x - 0.06 for x in xs], [a[0] for a in across], yerr=[[a[0] - a[1] for a in across], [a[2] - a[0] for a in across]],
                fmt="-o", color=C["images"], ms=4.8, lw=1.2, elinewidth=0.9, capsize=2, label="Across phases of care")
    cx.plot([x + 0.06 for x in xs], [w[0] for w in within], "--o", color=C["images"], mfc="white", ms=4.8, mew=1.1,
            lw=1.0, label="Within a phase of care", zorder=3)
    wx = [x + 0.06 for x, w in zip(xs, within) if w[1] is not None]
    wv = [w for w in within if w[1] is not None]
    cx.errorbar(wx, [w[0] for w in wv], yerr=[[w[0] - w[1] for w in wv], [w[2] - w[0] for w in wv]], fmt="none",
                ecolor=C["images"], elinewidth=0.9, capsize=2)
    cx.axhline(0.822, color=C["timeline"], lw=0.9, ls="-")
    cx.text(2.58, 0.826, "timeline pathway,\nacross phases 0.82", color=C["timeline"], va="bottom", ha="right",
            fontsize=6.6, linespacing=1.1)
    cx.axhline(0.640, color=C["timeline"], lw=0.9, ls="--")
    cx.text(2.58, 0.644, "timeline pathway,\nwithin a phase 0.64", color=C["timeline"], va="bottom", ha="right",
            fontsize=6.6, linespacing=1.1)
    cx.set(xticks=xs, xlim=(-0.3, 2.6), ylim=(0.5, 0.95), ylabel="AUC"); cx.set_xticklabels(steps)
    cx.tick_params(axis="x", length=0)
    h, l = cx.get_legend_handles_labels()
    cx.legend(h[::-1], l[::-1], frameon=False, loc="upper left", ncol=2)
    save(fig, output, "fig3_evidence")


def fig4(output: Path) -> None:
    """The confidence. NUMBERS.md 6 (S1, S2, S4) and 12A."""
    fig = plt.figure(figsize=(WIDTH, 4.3))
    ax_top = 0.915
    ax = fig.add_axes([0.085, 0.515, 0.37, ax_top - 0.515])
    panel(fig, LETTER_X, ax, "A"); title(ax, "Coverage of the 80% conformal sets")
    cov = {"Timeline": [(0.795, 0.731, 0.853), (0.798, 0.732, 0.868), (0.696, 0.594, 0.812)],
           "Images": [(0.844, 0.797, 0.890), (0.708, 0.648, 0.759), (0.826, 0.739, 0.913)],
           "Combined": [(0.823, 0.759, 0.883), (0.871, 0.807, 0.924), (0.783, 0.681, 0.870)]}
    cols = {"Timeline": C["timeline"], "Images": C["images"], "Combined": C["combined"]}
    ax.axhline(0.80, color="0.6", lw=0.8, ls=":", label="nominal 0.80")
    ax.axhline(0.78, color="#333", ls="--", lw=0.8, label="planned threshold 0.78")
    for i, (k, vals) in enumerate(cov.items()):
        for g, v in enumerate(vals):
            ax.errorbar(g + (i - 1) * 0.24, v[0], yerr=ci(v), fmt="o", ms=4.8, color=cols[k], mec="white", mew=0.5,
                        elinewidth=1.1, capsize=0, label=k if g == 0 else None, zorder=3)
    ax.set(xticks=range(3), xlim=(-0.5, 2.5), ylim=(0.5, 1.0), ylabel="Share of scans covered\n(axis from 0.5)")
    ax.set_xticklabels(["MU", "LUMIERE", "UCSF"]); ax.tick_params(axis="x", length=0)
    h, l = ax.get_legend_handles_labels()
    ax.legend(h[2:], l[2:], frameon=False, ncol=3, loc="upper left", fontsize=6.8, handletextpad=0.2,
              columnspacing=0.9, borderaxespad=0.2)
    ax.add_artist(ax.legend_)
    ax.legend(h[:2][::-1], l[:2][::-1], frameon=False, ncol=2, loc="lower left", fontsize=6.6, handlelength=2.0,
              columnspacing=0.9, borderaxespad=0.2)
    ax.legend_.set_zorder(5)

    bx = fig.add_axes([0.585, 0.515, 0.395, ax_top - 0.515])
    panel(fig, 0.51, bx, "B"); title(bx, "Where the pathways agree versus disagree")
    forest(bx, [("MU, own medians", 0.307, 0.175, 0.432, C["ink"], True),
                ("MU, other folds' medians", 0.313, 0.184, 0.431, C["ink"], False),
                ("LUMIERE, own medians", 0.105, -0.049, 0.266, C["ink"], True),
                ("LUMIERE, MU-fixed", 0.222, 0.102, 0.337, C["ink"], False),
                ("UCSF, own medians", -0.019, -0.218, 0.175, C["ink"], True),
                ("UCSF, MU-fixed", 0.134, -0.096, 0.397, C["ink"], False)],
           "AUC difference, agree minus disagree", xlim=(-0.3, 0.5))
    for y in (1.5, 3.5):
        bx.axhline(y + 0.2, color="0.88", lw=0.6, zorder=0)
    bx.legend(handles=[Line2D([], [], marker="o", ls="none", color=C["ink"], ms=4.8, label="own medians"),
                       Line2D([], [], marker="o", ls="none", color=C["ink"], mfc="white", ms=4.8, mew=1.1,
                              label="medians fixed on MU")],
              frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=6.8, handletextpad=0.2)

    cx = fig.add_axes([0.145, 0.10, 0.55, 0.20])
    panel(fig, LETTER_X, cx, "C"); title(cx, "Reliability card†: scans in a tested situation")
    cohorts = ["MU (146)", "LUMIERE (178)", "UCSF (69)"]
    tested = [54, 159, 0]; few = [92, 19, 69]
    for i, (t, f) in enumerate(zip(tested, few)):
        tot = t + f; y = 2 - i
        cx.barh(y, t / tot, color=C["ink"], height=0.6, label="Tested (≥10 of each outcome)" if i == 0 else None)
        cx.barh(y, f / tot, left=t / tot, color=tint(C["thin"], 0.55), height=0.6, label="Few cases" if i == 0 else None)
        if t:
            cx.text(t / tot / 2, y, f"{t}", color="white", ha="center", va="center", fontsize=7)
        cx.text(t / tot + f / tot / 2, y, f"{f}", ha="center", va="center", fontsize=7)
    cx.set(yticks=[2, 1, 0], yticklabels=cohorts, xlim=(0, 1), ylim=(-0.5, 2.5), xlabel="Share of scans")
    cx.legend(frameon=False, loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=6.9, labelspacing=0.9)
    save(fig, output, "fig4_confidence")


# Synthetic report: the Discussion's scenario (eight weeks after radiotherapy, growing enhancement, pathways
# disagree). Volumes and the score are invented; the card row is MU's (NUMBERS.md 10; Discussion).
REPORT = [
    ("Scan", "This scan was taken 8 weeks after the end of radiotherapy, early after radiotherapy.", "scan.phase"),
    ("Scan", "The automatic segmentation gives indicative volumes of 6.0 cc enhancing tumour and 31.0 cc FLAIR hyperintensity.", "meas.label, meas.enhancing_cc, …"),
    ("Scan", "Enhancing tumour is 2.0 cc larger than at the previous scan.", "meas.enhancing_change_…"),
    ("Pathways", "The timeline pathway is based on clinical data and the position in treatment: timeline score 0.21, below the median of its scores in the MU-Glioma-Post evaluation scans (0.38).", "pathway.timeline.*"),
    ("Pathways", "The image pathway is based on the segmented tumour and its change: image score 0.64, above the median of its scores in the MU-Glioma-Post evaluation scans (0.45).", "pathway.images.*"),
    ("Pathways", "The two pathways disagree: the timeline score is below its median and the image score is above its median.", "pathways.agreement_statement"),
    ("Combined", "The combined score, based on the inputs of both pathways, is 0.33.", "pathway.combined.*"),
    ("Combined", "Each score is a model output between 0 and 1 that ranks scans by how closely they resemble the progression scans of the training data; it is not a diagnosis and not a calibrated probability for this patient.", "pathways.score_meaning"),
    ("Combined", "The 80% conformal set holds both outcomes.", "conformal.combined.80.statement"),
    ("Trust", "This situation, early after radiotherapy with enhancing tumour increased, has few cases: 1 of 9 scans was progression.", "card.situation, card.tier_statement"),
    ("Trust", "The pathways disagree flag is raised: the timeline score is below its median and the image score is above its median.", "flags.disagreement.*"),
]
LIMITATIONS = ("Fixed limitations section (excerpt): the scores rank scans; they are not a diagnosis and the "
               "report gives no recommendation or decision. No clinician has evaluated this report.")


def schematic_slice(ax, et_scale: float, seed: int = 3) -> None:
    """A drawn axial slice (schematic, no patient image): grey and white matter with folded cortex, crescent
    ventricles, an enhancing rim around a necrotic core and a dashed FLAIR outline, in the radiological convention."""
    n = 200
    yy, xx = np.mgrid[-1:1:n * 1j, -1:1:n * 1j]
    rng = np.random.default_rng(seed)
    f2 = np.fft.fftfreq(n)[:, None] ** 2 + np.fft.fftfreq(n)[None, :] ** 2
    noise = np.fft.ifft2(np.fft.fft2(rng.normal(size=(n, n))) * np.exp(-f2 * 2500)).real
    noise /= np.abs(noise).max()
    th, rad = np.arctan2(yy, xx / 0.8), np.hypot(xx / 0.8, yy / 0.95)
    ph = rng.uniform(0, 2 * np.pi, 6)
    folds = sum(a * np.sin(k * th + p) for a, k, p in zip((0.035, 0.03, 0.025, 0.02), (17, 23, 29, 11), ph))
    edge = 0.97 + 0.012 * np.sin(5 * th + ph[4]) + 0.006 * np.sin(31 * th)
    wm_edge = 0.80 + folds
    img = np.zeros((n, n))
    img[rad < edge] = 0.38                                    # grey matter
    img[rad < wm_edge] = 0.55                                 # white matter
    img += np.where(rad < edge, 0.05 * noise, 0)
    img[(rad > edge) & (rad < edge + 0.05)] = 0.80            # scalp fat
    for side in (-1, 1):                                      # lateral ventricles, curved
        v = ((xx - side * (0.10 + 0.12 * yy ** 2)) / 0.055) ** 2 + (yy / 0.36) ** 2 < 1
        img[v] = 0.12
    img[(np.abs(xx) < 0.012) & (rad < edge) & (np.abs(yy) > 0.45)] = 0.15   # interhemispheric fissure
    cx, cy, r = 0.40, -0.25, 0.15 * et_scale
    d = np.hypot((xx - cx) / 1.1, yy - cy) * (1 + 0.05 * np.sin(3 * np.arctan2(yy - cy, xx - cx) + 0.7))
    img[(d < r) & (d > 0.6 * r)] = 0.95                       # enhancing rim
    img[d <= 0.6 * r] = 0.26                                  # necrotic core
    ax.imshow(img, cmap="gray", vmin=0, vmax=1, interpolation="bilinear", extent=(-1, 1, 1, -1))
    t = np.linspace(0, 2 * np.pi, 200)
    rf = r * 1.9 + 0.06
    wob = 1 + 0.08 * np.sin(3 * t + 1) + 0.05 * np.sin(5 * t)
    ax.plot(cx - 0.04 + 1.05 * rf * wob * np.cos(t), cy + 0.03 + rf * wob * np.sin(t), color="white", lw=0.8,
            ls=(0, (2.2, 1.6)))
    for s, (x, y) in {"R": (-0.9, 0), "L": (0.9, 0), "A": (0, -0.88), "P": (0, 0.88)}.items():
        ax.text(x, y, s, color="white", fontsize=6.5, ha="center", va="center", family="DejaVu Sans")
    ax.set(xlim=(-1, 1), ylim=(1, -1)); ax.axis("off")


def fig5(output: Path) -> None:
    """Report anatomy (synthetic example) and the automatic evaluation. NUMBERS.md 7."""
    height, serif, grey = 7.15, "Liberation Serif", "#666666"
    fig = plt.figure(figsize=(WIDTH, height))
    left, width, bottom, ax_h = 0.04, 0.62, 0.012, 0.95
    ax = fig.add_axes([left, bottom, width, ax_h]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    panel(fig, LETTER_X, ax, "A"); title(ax, "A PRISM report (synthetic example)")
    pt = 1 / (height * 72 * ax_h)                     # one point in axes-y units
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor="#333333", lw=0.7))
    x0, x1 = 0.035, 0.965
    y = 1 - 9 * pt
    ax.text(x0, y, "PRISM surveillance report", family=serif, fontsize=10, weight="bold", va="top")
    ax.text(x1, y - 1.5 * pt, "SYNTHETIC EXAMPLE", fontsize=6.5, va="top", ha="right", color=grey)
    y -= 13 * pt
    ax.text(x0, y, "Scan 8 weeks after the end of radiotherapy  ·  compared with the previous scan  ·  "
            "models from MU", family=serif, fontsize=7.2, va="top", color=grey)
    y -= 11 * pt
    ax.plot([x0, x1], [y, y], color="#333333", lw=0.7)

    # Segmentation figure strip (the real report attaches one per scan; this one is drawn).
    strip_h = 100 * pt
    y -= 6 * pt
    fx = lambda a: left + width * a                  # axes-x to figure-x
    fy = lambda b: bottom + ax_h * b
    img_w = 0.25
    for i, (scale, label) in enumerate([(1.0, "This scan"), (0.82, "Previous scan, same slice")]):
        a0 = x0 + i * (img_w + 0.02)
        iax = fig.add_axes([fx(a0), fy(y - strip_h), width * img_w, ax_h * strip_h])
        schematic_slice(iax, scale)
        iax.set_aspect("auto")
        ax.text(a0, y - strip_h - 2 * pt, label, family=serif, fontsize=6.8, va="top")
    vx = x0 + 2 * (img_w + 0.02) + 0.07
    vax = fig.add_axes([fx(vx), fy(y - strip_h + 16 * pt), width * (x1 - vx), ax_h * (strip_h - 18 * pt)])
    vax.plot([0, 1], [4.0, 6.0], "-o", color="black", ms=3.5, lw=1.0, label="enhancing")
    vax.plot([0, 1], [27.0, 31.0], "--o", color="#888888", mfc="white", ms=3.5, lw=1.0, label="FLAIR")
    vax.set(xticks=[0, 1], xlim=(-0.3, 1.3), ylim=(0, 36), ylabel="Volume (cc)")
    vax.set_xticklabels(["previous", "this scan"], family=serif, fontsize=6.8)
    vax.legend(frameon=False, fontsize=6.5, loc="center left", handlelength=1.8, bbox_to_anchor=(0, 0.55))
    ax.text(vx - 0.06, y - strip_h - 2 * pt, "Dashed: FLAIR outline.\nDrawn, not a patient image.", family=serif, fontsize=6.5, va="top", color=grey, style="italic")
    y -= strip_h + 16 * pt

    body = 7.4
    current = None
    for section, text, keys in REPORT:
        if section != current:
            y -= 3 * pt if current else 0
            ax.text(x0, y, section.upper(), family=serif, fontsize=7.2, weight="bold", va="top")
            y -= 9 * pt
            ax.plot([x0, x1], [y, y], color="#bbbbbb", lw=0.5)
            y -= 3.5 * pt; current = section
        lines = textwrap.wrap(text, 92)
        ax.text(x0, y, "\n".join(lines), family=serif, fontsize=body, va="top", linespacing=1.22)
        y -= body * 1.22 * len(lines) * pt
        if len(lines[-1]) * 3.3 + len(keys) * 4.0 + 12 < 280:   # cited fields fit beside the last line
            ax.text(x1, y + body * 1.22 * pt, keys, fontsize=6.5, va="top", ha="right", color="#8a8a8a",
                    family="DejaVu Sans Mono")
            y -= 4.0 * pt
        else:
            ax.text(x1, y, keys, fontsize=6.5, va="top", ha="right", color="#8a8a8a", family="DejaVu Sans Mono")
            y -= 11.0 * pt
    ax.plot([x0, x1], [y + 2 * pt, y + 2 * pt], color="#333333", lw=0.6)
    ax.text(x0, y - 2 * pt, "\n".join(textwrap.wrap(LIMITATIONS, 100)), family=serif, fontsize=6.9, va="top",
            color="#444444", style="italic", linespacing=1.2)

    # Model-size ladder (NUMBERS.md 7: v3.1, frozen prompt, no per-model tuning; descriptive).
    bx = fig.add_axes([0.725, 0.45, 0.255, 0.49])
    panel(fig, 0.68, bx, "B"); title(bx, "Reports passing the check")
    ladder = [("Qwen 2B", 3.6, 21, False), ("Qwen 4B", 8.0, 306, False), ("Gemma E4B", 14.5, 117, False),
              ("Qwen 9B", 16.8, 368, False), ("Qwen 27B, used", 50.2, 406, True),
              ("Gemma 31B", 57.9, 406, True), ("Qwen 35B-A3B", 64.7, 389, False)]
    dark, light = C["ink"], tint(C["ink"], 0.7)
    for i, (name, gib, k, ok) in enumerate(ladder):
        y = len(ladder) - 1 - i
        bx.barh(y, k / 406, color=dark if ok else light, height=0.5)
        bx.text(0, y + 0.3, f"{name} ({gib:.1f} GiB)", va="bottom", ha="left", fontsize=6.8, color=C["ink"],
                weight="bold" if ok else "normal")
        inside = k >= 330
        bx.text(k / 406 - 0.02 if inside else k / 406 + 0.02, y, str(k), va="center", ha="right" if inside else "left",
                fontsize=6.7, color="white" if ok else C["ink"], weight="bold")
    bx.set(yticks=[], xlim=(0, 1), ylim=(-0.45, len(ladder) - 0.15), xlabel="Share of the 406 reports")
    bx.spines["left"].set_visible(False)
    bx.text(0, -0.13, "Dark: ≥ 95% in every cohort; light: below\n95% in at least one. Same prompt for all.", transform=bx.transAxes,
            fontsize=6.6, va="top", color="#444444", linespacing=1.2)
    save(fig, output, "fig5_report")


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    fig1(output); fig2(output); fig3(output); fig4(output); fig5(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output-dir", type=Path, default=Path("docs/manuscript/figures"))
    generate(parser.parse_args().output_dir)
