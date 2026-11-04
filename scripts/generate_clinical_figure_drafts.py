"""Create review drafts for a clinically grounded PRISM Figure 1.

The MRI pair is synthetic, illustrative artwork. All cohort names, example values, and methodological claims are
rendered below as editable Matplotlib text. This script writes versioned drafts only and never overwrites cited
manuscript figure assets.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402


INK = "#20303d"
MUTED = "#66727b"
RULE = "#c9d0d4"
PAPER = "#f7f8f8"
IMAGE = "#269f90"
TIMELINE = "#4b7fb7"
ACCENT = "#ee8b27"
WIDTH = 7.2

plt.rcParams.update(
    {
        "font.family": "Liberation Sans",
        "font.size": 7.5,
        "pdf.fonttype": 42,
        "axes.linewidth": 0.7,
    }
)


def label(ax, x, y, text, *, size=7.0, colour=INK, weight="normal", ha="left", va="top", **kwargs):
    return ax.text(x, y, text, fontsize=size, color=colour, weight=weight, ha=ha, va=va, **kwargs)


def card(ax, x, y, width, height, *, face="white", edge=RULE, radius=0.012):
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle=f"round,pad=0.006,rounding_size={radius}",
        facecolor=face,
        edgecolor=edge,
        linewidth=0.65,
    )
    ax.add_patch(patch)
    return patch


def fig1_clinical(output_dir: Path) -> None:
    """Write the versioned Figure 1 clinical-narrative draft."""
    asset = (
        Path(__file__).resolve().parents[1]
        / "docs/manuscript/figures/drafts/fig1_synthetic_mri_v2.png"
    )
    if not asset.is_file():
        raise FileNotFoundError(f"Synthetic MRI review asset not found: {asset}")

    fig = plt.figure(figsize=(WIDTH, 4.95))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")

    label(ax, 0.025, 0.956, "A", size=10, weight="bold")
    label(ax, 0.060, 0.958, "A progression score is more useful when its basis remains visible", size=10, weight="bold")
    label(
        ax,
        0.060,
        0.915,
        "One synthetic follow-up example. The report keeps image evidence and treatment context separate.",
        size=7.2,
        colour=MUTED,
    )
    ax.plot([0.060, 0.955], [0.885, 0.885], color=RULE, lw=0.7)

    # The generated asset supplies only the synthetic clinical texture. The labels and values remain editable text.
    image = plt.imread(asset)
    iax = fig.add_axes([0.060, 0.500, 0.300, 0.330])
    iax.imshow(image)
    iax.axis("off")
    label(ax, 0.120, 0.485, "Earlier scan", size=7.0, colour=MUTED, ha="center")
    label(ax, 0.302, 0.485, "Current scan", size=7.0, colour=MUTED, ha="center")
    label(ax, 0.060, 0.450, "Synthetic MRI illustration, not a patient image", size=6.5, colour=MUTED, style="italic")

    label(ax, 0.060, 0.415, "Treatment course", size=7.4, weight="bold")
    line_y = 0.355
    ax.plot([0.072, 0.350], [line_y, line_y], color=INK, lw=0.8)
    for x, event in ((0.092, "surgery"), (0.177, "chemoradiotherapy"), (0.332, "scan")):
        ax.plot([x, x], [line_y - 0.015, line_y + 0.015], color=INK, lw=1.4 if event == "scan" else 0.8)
        label(ax, x, 0.316, event, size=6.4, colour=MUTED, ha="center", va="center")
    ax.add_patch(Rectangle((0.134, line_y - 0.010), 0.097, 0.020, facecolor="#d9dee1", edgecolor="none"))
    label(ax, 0.332, 0.277, "8 weeks after radiotherapy", size=6.6, colour=MUTED, ha="center")

    # Evidence is the visual centre: no generic module stack, just the two sources the reader must distinguish.
    card(ax, 0.402, 0.255, 0.248, 0.580, face=PAPER, edge="#dde3e6")
    label(ax, 0.422, 0.805, "What PRISM keeps separate", size=8.0, weight="bold")
    label(ax, 0.422, 0.772, "Two sources can support a score differently.", size=6.7, colour=MUTED)

    card(ax, 0.422, 0.605, 0.208, 0.115, face="white", edge="#cae7e2")
    ax.add_patch(Rectangle((0.422, 0.605), 0.008, 0.115, facecolor=IMAGE, edgecolor="none"))
    label(ax, 0.444, 0.695, "Image evidence", size=7.4, weight="bold")
    label(ax, 0.444, 0.665, "Enhancing volume increased", size=6.5, colour=MUTED)
    label(ax, 0.444, 0.630, "Image score", size=6.3, colour=MUTED)
    label(ax, 0.610, 0.630, "0.64", size=7.2, weight="bold", ha="right", colour=IMAGE)

    card(ax, 0.422, 0.445, 0.208, 0.115, face="white", edge="#cedbed")
    ax.add_patch(Rectangle((0.422, 0.445), 0.008, 0.115, facecolor=TIMELINE, edgecolor="none"))
    label(ax, 0.444, 0.535, "Treatment context", size=7.4, weight="bold")
    label(ax, 0.444, 0.505, "Early after radiotherapy", size=6.5, colour=MUTED)
    label(ax, 0.444, 0.470, "Timeline score", size=6.3, colour=MUTED)
    label(ax, 0.610, 0.470, "0.21", size=7.2, weight="bold", ha="right", colour=TIMELINE)

    ax.plot([0.438, 0.614], [0.398, 0.398], color=ACCENT, lw=1.8)
    label(ax, 0.526, 0.372, "The pathways disagree", size=7.1, weight="bold", ha="center", colour=ACCENT)
    label(ax, 0.526, 0.342, "The report makes the disagreement", size=6.3, ha="center", colour=MUTED)
    label(ax, 0.526, 0.318, "visible instead of hiding it in one score.", size=6.3, ha="center", colour=MUTED)

    # The report reads as a clean clinical artifact, with record checking as a small provenance detail.
    card(ax, 0.690, 0.255, 0.265, 0.580, face="white", edge=INK)
    label(ax, 0.712, 0.804, "Report for this scan", size=8.0, weight="bold", family="Liberation Serif")
    label(ax, 0.933, 0.802, "SYNTHETIC", size=6.3, colour=MUTED, ha="right")
    ax.plot([0.712, 0.933], [0.753, 0.753], color=RULE, lw=0.7)
    report_lines = (
        ("Image evidence", ("Enhancing volume increased", "from the earlier scan.")),
        ("Treatment context", ("This scan is early after radiotherapy.",)),
        ("Pathways", ("Image and timeline scores disagree.",)),
        ("Evidence in this situation", ("Few comparable scans were available.",)),
    )
    y = 0.718
    for heading, sentences in report_lines:
        label(ax, 0.712, y, heading, size=6.8, weight="bold", family="Liberation Serif")
        for index, sentence in enumerate(sentences):
            label(ax, 0.712, y - 0.029 - 0.020 * index, sentence, size=6.2, colour="#3d464d", family="Liberation Serif")
        y -= 0.105 if len(sentences) == 1 else 0.125
    ax.plot([0.712, 0.933], [0.324, 0.324], color=RULE, lw=0.6)
    label(ax, 0.712, 0.302, "Each statement is checked against", size=6.2, colour=MUTED, style="italic")
    label(ax, 0.712, 0.281, "the source record.", size=6.2, colour=MUTED, style="italic")

    # Study-design strip gives the figure a quiet but direct connection to the external-validation claim.
    ax.plot([0.060, 0.955], [0.206, 0.206], color=RULE, lw=0.7)
    steps = (
        (0.060, "Developed on MU", "public development cohort"),
        (0.305, "Models fixed", "before external scoring"),
        (0.525, "Validated externally", "LUMIERE and UCSF"),
        (0.765, "Reports checked", "against source records"),
    )
    arrow_positions = ((0.250, 0.273), (0.475, 0.498), (0.710, 0.733))
    for i, (x, heading, detail) in enumerate(steps):
        label(ax, x, 0.165, heading, size=7.0, weight="bold")
        label(ax, x, 0.135, detail, size=6.4, colour=MUTED)
        if i < len(steps) - 1:
            start, end = arrow_positions[i]
            ax.plot([start, end], [0.158, 0.158], color=RULE, lw=1.0)
            ax.plot([end], [0.158], marker=">", color=RULE, ms=3)

    fig.savefig(output_dir / "fig1_clinical_v2.pdf", bbox_inches=None, facecolor="white")
    fig.savefig(output_dir / "fig1_clinical_v2.png", dpi=300, bbox_inches=None, facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("docs/manuscript/figures/drafts"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fig1_clinical(args.output_dir)


if __name__ == "__main__":
    main()
