"""Generate the five manuscript figures from verified aggregate values (docs/manuscript/NUMBERS.md).

Every value below is an aggregate from NUMBERS.md (section named beside it); no patient-level data are read. The
example report in Figure 5 is synthetic: an invented scan written in the v3.1 report format, with the MU card row
quoted in the Discussion (1 of 9 scans).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.titlesize": 8.5, "axes.labelsize": 7.5,
                     "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "axes.spines.top": False,
                     "axes.spines.right": False, "pdf.fonttype": 42})

# One colour per kind of evidence, used in every figure.
C = {"clinical": "#9d9d9d", "timeline": "#4c78a8", "images": "#2a9d8f", "images2": "#8fd1c7",
     "combined": "#f58518", "et": "#5a5a5a", "ink": "#22313f", "soft": "#f3f5f8", "thin": "#e45756"}


def save(fig, output: Path, name: str) -> None:
    for extension in ("pdf", "png"):
        fig.savefig(output / f"{name}.{extension}", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def letter(ax, text, x=-0.08, y=1.04):
    ax.text(x, y, text, transform=ax.transAxes, fontsize=10, weight="bold", va="bottom", ha="left")


def box(ax, x, y, w, h, text, face, edge=None, size=7.2, weight="normal", align="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.012", facecolor=face,
                                edgecolor=edge or C["ink"], linewidth=0.8))
    tx = x + w / 2 if align == "center" else x + 0.012
    ax.text(tx, y + h / 2, text, ha=align, va="center", fontsize=size, weight=weight, color=C["ink"],
            linespacing=1.25)


def arrow(ax, start, end, colour=None):
    ax.annotate("", end, start, arrowprops={"arrowstyle": "-|>", "color": colour or C["ink"], "lw": 0.8,
                                            "shrinkA": 0, "shrinkB": 0, "mutation_scale": 7})


def tint(hex_colour: str, amount: float = 0.82) -> str:
    rgb = matplotlib.colors.to_rgb(hex_colour)
    return matplotlib.colors.to_hex([c + (1 - c) * amount for c in rgb])


def fig1(output: Path) -> None:
    """The system (A) and how it was evaluated (B). Counts: NUMBERS.md 2.2, 6, 7."""
    fig = plt.figure(figsize=(7.2, 5.0))
    ax = fig.add_axes([0, 0.30, 1, 0.70]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    letter(ax, "A", x=0.0, y=0.97)
    ax.text(0.04, 0.985, "What PRISM does at each scan", fontsize=8.5, weight="bold", va="top")

    # inputs
    box(ax, 0.01, 0.70, 0.17, 0.15, "Surveillance MRI\nand its masks\n(this and earlier scans)", C["soft"])
    box(ax, 0.01, 0.46, 0.17, 0.15, "Clinical record\nage, sex, IDH, MGMT", C["soft"])
    box(ax, 0.01, 0.22, 0.17, 0.15, "Treatment timeline\nsurgery, radiotherapy,\nchemotherapy dates", C["soft"])
    # measurements and pathways
    box(ax, 0.23, 0.70, 0.17, 0.15, "Measurements\nvolumes, shape,\nintensity and change", tint(C["images"]))
    box(ax, 0.45, 0.70, 0.15, 0.15, "Image pathway\nridge model,\nno dates", tint(C["images"], 0.6), weight="bold")
    box(ax, 0.45, 0.34, 0.15, 0.15, "Timeline pathway\nridge model on\ntreatment position", tint(C["timeline"], 0.6), weight="bold")
    box(ax, 0.45, 0.52, 0.15, 0.12, "Combined score\nshown beside both", tint(C["combined"], 0.6), weight="bold")
    arrow(ax, (0.18, 0.775), (0.23, 0.775)); arrow(ax, (0.40, 0.775), (0.45, 0.775))
    arrow(ax, (0.18, 0.535), (0.45, 0.43)); arrow(ax, (0.18, 0.295), (0.45, 0.40))
    arrow(ax, (0.525, 0.70), (0.525, 0.64)); arrow(ax, (0.525, 0.49), (0.525, 0.52))
    # confidence
    box(ax, 0.65, 0.73, 0.15, 0.11, "Conformal set (80%)\none outcome or both", tint(C["thin"], 0.85))
    box(ax, 0.65, 0.555, 0.15, 0.11, "Pathway agreement\nsame side of median?", tint(C["thin"], 0.85))
    box(ax, 0.65, 0.38, 0.15, 0.11, "Reliability card\nhow many tested\nscans like this one", tint(C["thin"], 0.85))
    ax.text(0.725, 0.865, "Confidence", ha="center", fontsize=7.5, weight="bold", color=C["thin"])
    for y in (0.785, 0.61, 0.435):
        arrow(ax, (0.60, 0.58), (0.65, y))
    # record and report
    box(ax, 0.84, 0.52, 0.15, 0.30, "Structured\nevidence record\n\nevery value\nwith its source", "#fff3d6", weight="bold")
    for y in (0.785, 0.61, 0.435):
        arrow(ax, (0.80, y), (0.84, 0.67))
    box(ax, 0.84, 0.30, 0.15, 0.13, "Local language model\nwrites the report\n(offline, one GPU)", C["soft"])
    box(ax, 0.84, 0.10, 0.15, 0.13, "Deterministic checker\nnumbers, flags and\nwording vs record", C["soft"])
    box(ax, 0.57, 0.10, 0.22, 0.13, "Report to the clinician\nfigure, scores, confidence\nand what was not used", tint(C["combined"], 0.85), weight="bold", size=6.9)
    arrow(ax, (0.915, 0.52), (0.915, 0.43)); arrow(ax, (0.915, 0.30), (0.915, 0.23)); arrow(ax, (0.84, 0.165), (0.79, 0.165))
    ax.text(0.30, 0.13, "Where a cohort records no treatment dates,\nthe timeline is reduced and the image\npathway runs on its own.",
            fontsize=6.8, color="#555555", ha="center", va="center", style="italic")

    bx = fig.add_axes([0, 0, 1, 0.28]); bx.set_xlim(0, 1); bx.set_ylim(0, 1); bx.axis("off")
    letter(bx, "B", x=0.0, y=0.92)
    bx.text(0.04, 0.99, "How it was evaluated", fontsize=8.5, weight="bold", va="top")
    box(bx, 0.01, 0.12, 0.27, 0.62, "MU-Glioma-Post (development)\n146 scans in the intended use\n5 × 5 patient-grouped\ncross-validation", tint(C["timeline"], 0.85))
    box(bx, 0.34, 0.25, 0.14, 0.36, "Fit once on MU,\nlock the models\nand write the plan", C["soft"])
    box(bx, 0.54, 0.42, 0.20, 0.36, "LUMIERE (locked)\n178 scans,\nno treatment dates", tint(C["images"], 0.85))
    box(bx, 0.54, 0.02, 0.20, 0.32, "UCSF-ALPTDG (locked)\n69 second scans", tint(C["images"], 0.85))
    box(bx, 0.80, 0.12, 0.19, 0.62, "Reports\n406 records from\nall three cohorts,\nunchanged checker", "#fff3d6")
    arrow(bx, (0.28, 0.43), (0.34, 0.43)); arrow(bx, (0.48, 0.48), (0.54, 0.59)); arrow(bx, (0.48, 0.38), (0.54, 0.21))
    arrow(bx, (0.74, 0.59), (0.80, 0.50)); arrow(bx, (0.74, 0.21), (0.80, 0.36))
    save(fig, output, "fig1_system")


def bars(ax, groups, series, title):
    """groups: cohort labels; series: list of (label, colour, [(auc, lo, hi) or None per group], hatch).
    Within each group the series present are centred, so a missing series leaves no gap."""
    width = 0.8 / max(sum(v[g] is not None for v in [s[2] for s in series]) for g in range(len(groups)))
    seen = set()
    for g in range(len(groups)):
        present = [s for s in series if s[2][g] is not None]
        for i, (label, colour, values, hatch) in enumerate(present):
            v = values[g]; x = g + (i - (len(present) - 1) / 2) * width
            ax.bar(x, v[0], width * 0.92, color=colour, hatch=hatch, edgecolor="#3c3c3c" if hatch else "white",
                   linewidth=0.4, label=None if label in seen else label)
            seen.add(label)
            ax.errorbar(x, v[0], yerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt="none", ecolor="#333333", elinewidth=0.7, capsize=1.5)
    ax.axhline(0.5, color="0.55", lw=0.7, ls=":")
    ax.set(xticks=range(len(groups)), xticklabels=groups, ylim=(0.3, 1.0), ylabel="AUC")
    if title:
        ax.set_title(title, loc="left", weight="bold")


def fig2(output: Path) -> None:
    """AUC by pathway and cohort. NUMBERS.md 3, 4, 11, 12C."""
    groups = ["MU-Glioma-Post\ninternal (CV)", "LUMIERE\nlocked", "UCSF-ALPTDG\nlocked", "UCSF-ALPTDG\ntrained there"]
    series = [
        ("Clinical data alone", C["clinical"], [(0.530, 0.450, 0.606), (0.554, 0.458, 0.635), (0.502, 0.364, 0.630), (0.407, 0.314, 0.494)], None),
        ("Timeline pathway", C["timeline"], [(0.822, 0.749, 0.902), (0.689, 0.600, 0.805), (0.561, 0.420, 0.687), (0.669, 0.549, 0.784)], None),
        ("Image pathway", C["images"], [(0.709, 0.630, 0.781), (0.655, 0.565, 0.733), (0.726, 0.603, 0.835), (0.863, 0.772, 0.934)], None),
        ("Images, single scan", C["images2"], [None, None, (0.795, 0.686, 0.887), (0.826, 0.729, 0.909)], None),
        ("Combined score", C["combined"], [(0.821, 0.744, 0.894), (0.773, 0.679, 0.857), (0.856, 0.758, 0.930), (0.871, 0.790, 0.938)], None),
        ("Enhancing volume alone†", "white", [(0.622, 0.530, 0.717), (0.662, 0.563, 0.751), (0.878, 0.793, 0.948), None], "////"),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    bars(ax, groups, series, "")
    ax.legend(frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0, 1.16))
    save(fig, output, "fig2_transport")


def forest(ax, rows, xlabel, ref=0.0, xlim=None):
    """rows: (label, est, lo, hi, colour, filled)."""
    for i, (label, est, lo, hi, colour, filled) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.plot([lo, hi], [y, y], color=colour, lw=1.4)
        ax.plot(est, y, "o", color=colour, mfc=colour if filled else "white", ms=4.5, mew=1.1)
    ax.axvline(ref, color="0.5", lw=0.7, ls=":")
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.set_xlabel(xlabel)
    if xlim:
        ax.set_xlim(*xlim)


def fig3(output: Path) -> None:
    """What each score rests on. NUMBERS.md 5 (MU audit, UCSF audit, ladder)."""
    fig = plt.figure(figsize=(7.2, 4.9))
    ax = fig.add_axes([0.25, 0.60, 0.27, 0.30])
    ax.set_title("A   MU: gain from adding the timeline\n     to clinical data and images", loc="left", weight="bold", x=-0.8)
    forest(ax, [("Across phases of care", 0.114, 0.035, 0.196, C["timeline"], True),
                ("Within a phase of care", -0.016, -0.134, 0.109, C["timeline"], False)], "AUC difference", xlim=(-0.2, 0.3))
    ax.set_ylim(-0.6, 1.6)

    bx = fig.add_axes([0.66, 0.60, 0.32, 0.30])
    bx.set_title("B   UCSF: progression calls\n     follow enhancement", loc="left", weight="bold", x=-0.2)
    labels = ["Enhancing\nvolume\nalone", "Single\nscan", "Image\npathway", "Single scan,\n'increased'\nscans only"]
    vals = [(0.878, 0.793, 0.948), (0.795, 0.686, 0.887), (0.726, 0.603, 0.835), (0.652, 0.444, 0.836)]
    cols = ["white", C["images2"], C["images"], tint(C["images2"], 0.4)]
    for i, (v, c) in enumerate(zip(vals, cols)):
        bx.bar(i, v[0], 0.7, color=c, edgecolor="#3c3c3c" if c == "white" else "white", hatch="////" if c == "white" else None, lw=0.4)
        bx.errorbar(i, v[0], yerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt="none", ecolor="#333", elinewidth=0.7, capsize=1.5)
    bx.axhline(0.5, color="0.55", lw=0.7, ls=":")
    bx.set(xticks=range(4), ylim=(0.3, 1.0), ylabel="AUC"); bx.set_xticklabels(labels, fontsize=6.3)
    bx.set_xlabel("Rated 'enhancement increased': progression\n27 of 29 scans, non-progression 10 of 40", fontsize=6.4, color="#444444")

    cx = fig.add_axes([0.10, 0.08, 0.86, 0.34])
    cx.set_title("C   MU: the image model built in three steps", loc="left", weight="bold", x=-0.07)
    steps = ["Current scan's\nmeasurements", "+ change from\nearlier scans\n(image pathway)", "+ three schedule\ninputs"]
    across = [(0.659, 0.567, 0.733), (0.709, 0.630, 0.781), (0.806, 0.747, 0.865)]
    within = [(0.680, None, None), (0.677, 0.580, 0.767), (0.664, 0.576, 0.750)]
    xs = [0, 1, 2]
    cx.errorbar([x - 0.06 for x in xs], [a[0] for a in across], yerr=[[a[0] - a[1] for a in across], [a[2] - a[0] for a in across]],
                fmt="-o", color=C["images"], ms=4.5, lw=1.2, capsize=2, label="Across phases of care")
    cx.plot([x + 0.06 for x in xs], [w[0] for w in within], "--o", color=C["images"], mfc="white", ms=4.5, lw=1.0, label="Within a phase of care")
    for x, w in zip(xs, within):
        if w[1] is not None:
            cx.plot([x + 0.06] * 2, [w[1], w[2]], color=C["images"], lw=0.8)
    cx.axhline(0.822, color=C["timeline"], lw=0.9, ls="-"); cx.text(2.32, 0.822, "timeline pathway,\nacross phases 0.82", color=C["timeline"], va="center", fontsize=6.3)
    cx.axhline(0.640, color=C["timeline"], lw=0.9, ls="--"); cx.text(2.32, 0.640, "timeline pathway,\nwithin a phase 0.64", color=C["timeline"], va="center", fontsize=6.3)
    cx.set(xticks=xs, xlim=(-0.3, 2.9), ylim=(0.5, 0.95), ylabel="AUC"); cx.set_xticklabels(steps)
    cx.legend(frameon=False, loc="upper left")
    save(fig, output, "fig3_evidence")


def fig4(output: Path) -> None:
    """The confidence. NUMBERS.md 6 (S1, S2, S4) and 12A."""
    fig = plt.figure(figsize=(7.2, 4.2))
    ax = fig.add_axes([0.07, 0.50, 0.40, 0.40])
    ax.set_title("A   Coverage of the 80% conformal sets", loc="left", weight="bold", x=-0.12)
    cov = {"Timeline": [(0.795, 0.731, 0.853), (0.798, 0.732, 0.868), (0.696, 0.594, 0.812)],
           "Images": [(0.844, 0.797, 0.890), (0.708, 0.648, 0.759), (0.826, 0.739, 0.913)],
           "Combined": [(0.823, 0.759, 0.883), (0.871, 0.807, 0.924), (0.783, 0.681, 0.870)]}
    cols = {"Timeline": C["timeline"], "Images": C["images"], "Combined": C["combined"]}
    for i, (k, vals) in enumerate(cov.items()):
        for g, v in enumerate(vals):
            x = g + (i - 1) * 0.26
            ax.bar(x, v[0], 0.24, color=cols[k], label=k if g == 0 else None)
            ax.errorbar(x, v[0], yerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt="none", ecolor="#333", elinewidth=0.7, capsize=1.5)
    ax.axhline(0.78, color="#333", ls="--", lw=0.8); ax.text(2.45, 0.78, "threshold\n0.78", fontsize=6.3, va="center")
    ax.set(xticks=range(3), xticklabels=["MU", "LUMIERE", "UCSF"], ylim=(0.5, 1.0), ylabel="Share of scans covered", xlim=(-0.5, 2.9))
    ax.legend(frameon=False, ncol=3, loc="upper left", fontsize=6.5)

    bx = fig.add_axes([0.70, 0.50, 0.28, 0.40])
    bx.set_title("B   Where the pathways agree\n     versus disagree", loc="left", weight="bold", x=-0.6)
    forest(bx, [("MU, own medians", 0.307, 0.175, 0.432, C["ink"], True),
                ("MU, other folds' medians†", 0.313, 0.184, 0.431, C["ink"], False),
                ("LUMIERE, own medians", 0.105, -0.049, 0.266, C["ink"], True),
                ("LUMIERE, MU-fixed†", 0.222, 0.102, 0.337, C["ink"], False),
                ("UCSF, own medians", -0.019, -0.218, 0.175, C["ink"], True),
                ("UCSF, MU-fixed†", 0.134, -0.096, 0.397, C["ink"], False)],
           "AUC difference, agree minus disagree\n(filled: planned test)", xlim=(-0.3, 0.5))

    cx = fig.add_axes([0.13, 0.10, 0.80, 0.22])
    cx.set_title("C   Reliability card†: scans in a tested situation", loc="left", weight="bold", x=-0.115)
    cohorts = ["MU (146)", "LUMIERE (178)", "UCSF (69)"]
    tested = [54, 159, 0]; few = [92, 19, 69]
    for i, (t, f) in enumerate(zip(tested, few)):
        tot = t + f; y = 2 - i
        cx.barh(y, t / tot, color=C["ink"], height=0.55, label="Tested (≥10 of each outcome)" if i == 0 else None)
        cx.barh(y, f / tot, left=t / tot, color=tint(C["thin"], 0.55), height=0.55, label="Few cases" if i == 0 else None)
        if t:
            cx.text(t / tot / 2, y, f"{t}", color="white", ha="center", va="center", fontsize=7)
        cx.text(t / tot + f / tot / 2, y, f"{f}", ha="center", va="center", fontsize=7)
    cx.set(yticks=[2, 1, 0], yticklabels=cohorts, xlim=(0, 1), xlabel="Share of scans")
    cx.legend(frameon=False, ncol=2, loc="upper right", bbox_to_anchor=(1, 1.32))
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
    ("Combined", "The 80% conformal set holds both outcomes.", "conformal.combined.80.statement"),
    ("Trust", "This situation, early after radiotherapy with enhancing tumour increased, has few cases: 1 of 9 scans was progression.", "card.situation, card.tier_statement"),
    ("Trust", "The pathways disagree flag is raised: the timeline score is below its median and the image score is above its median.", "flags.disagreement.*"),
]


def fig5(output: Path) -> None:
    """Report anatomy (synthetic example) and the automatic evaluation. NUMBERS.md 7."""
    fig = plt.figure(figsize=(7.2, 4.6))
    ax = fig.add_axes([0.0, 0.0, 0.66, 1.0]); ax.set_xlim(0, 1); ax.set_ylim(-0.06, 1); ax.axis("off")
    ax.text(0.01, 0.985, "A   A PRISM report (synthetic example)", fontsize=8.5, weight="bold", va="top")
    ax.add_patch(FancyBboxPatch((0.01, -0.05), 0.97, 0.99, boxstyle="round,pad=0.005,rounding_size=0.01",
                                facecolor="#fbfbfb", edgecolor="#9aa5b1", lw=0.8))
    y = 0.915; current = None
    sec_col = {"Scan": C["images"], "Pathways": C["timeline"], "Combined": C["combined"], "Trust": C["thin"]}
    import textwrap
    for section, text, keys in REPORT:
        if section != current:
            ax.text(0.03, y, section.upper(), fontsize=6.6, weight="bold", color=sec_col[section], va="top")
            y -= 0.030; current = section
        lines = textwrap.wrap(text, 74)
        ax.text(0.03, y, "\n".join(lines), fontsize=6.9, va="top", color=C["ink"], linespacing=1.2)
        y -= 0.027 * len(lines)
        ax.text(0.96, y + 0.004, f"cites: {keys}", fontsize=5.6, va="top", ha="right", color="#7b8794", family="DejaVu Sans Mono")
        y -= 0.026
    ax.plot([0.03, 0.95], [y + 0.012, y + 0.012], color="#c5ccd3", lw=0.6)
    ax.text(0.03, y - 0.004, "Fixed limitations section (excerpt): the scores rank scans; they are not a diagnosis and the\n"
            "report gives no recommendation or decision. No clinician has evaluated this report.", fontsize=6.3, va="top", color="#555", style="italic")

    bx = fig.add_axes([0.76, 0.55, 0.22, 0.33])
    bx.set_title("B   Reports passing the check", loc="left", weight="bold", x=-0.38)
    counts = [("MU", 114, 114), ("LUMIERE", 162, 162), ("UCSF", 130, 130)]
    for i, (name, k, n) in enumerate(counts):
        bx.barh(2 - i, k / n, color=C["combined"], height=0.55)
        bx.text(0.5, 2 - i, f"{k} of {n}", ha="center", va="center", color="white", fontsize=7, weight="bold")
    bx.set(yticks=[2, 1, 0], yticklabels=[c[0] for c in counts], xlim=(0, 1), xlabel="Share of reports")
    cx = fig.add_axes([0.70, 0.04, 0.29, 0.36]); cx.axis("off")
    cx.text(0.0, 1.0, "Also checked, all 406 reports:", fontsize=7, weight="bold", va="top")
    cx.text(0.0, 0.86, "• 220 of 220 state a few-case or\n   untested tier where one applies\n"
            "• 28 of 30 changed records followed\n   (planned minimum: 27)\n"
            "• no unsupported number, invalid\n   citation or forbidden wording\n\n"
            "Lexical check only: it cannot judge\nemphasis, order or what a\nclinician would infer.",
            fontsize=6.6, va="top", linespacing=1.3, color=C["ink"])
    save(fig, output, "fig5_report")


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    fig1(output); fig2(output); fig3(output); fig4(output); fig5(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output-dir", type=Path, default=Path("docs/manuscript/figures"))
    generate(parser.parse_args().output_dir)
