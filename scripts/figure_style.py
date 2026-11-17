"""One visual style for every manuscript figure.

Colour follows the score, never the panel: clinical history is purple, imaging teal, combined orange, in every figure.
The three hues pass the dataviz validator (lightness band, chroma floor, all-pairs CVD separation >= 10 OKLab units).
Navy is structural (boxes, rules, the system itself) and never encodes a score; reference scores are grey and carry a
distinct marker shape, so no comparison rests on colour alone. One sans-serif face, no titles inside plots (captions
carry them), lowercase bold panel letters, open axes with outward ticks, figures 7.2 in wide saved as drawn.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

WIDTH = 7.2          # inches, every figure (double column)
FONT = "Liberation Sans"   # metric-compatible with Arial/Helvetica

# Scores (data colours).
HIST = "#6A4C9C"     # clinical-history model
IMG = "#0F9384"      # imaging model
IMG_1 = "#7CC4BA"    # imaging, current scan only (tint of IMG)
COMB = "#D9772B"     # combined model
CLIN = "#9A9FA8"     # clinical data alone (reference)
ET = "#4A5260"       # enhancing volume alone (reference)

# Structure and text.
NAVY = "#1F3A5F"     # the system: box outlines, arrows, emphasis
INK = "#1E2430"      # primary text
MUTED = "#5E6673"    # secondary text
RULE = "#C9CED6"     # hairlines, separators, chance lines
PANEL = "#F4F6F9"    # panel and band fill

SCORE = {"timeline": HIST, "images": IMG, "combined": COMB, "enhancing_volume": ET, "context_only": CLIN,
         "clinical": CLIN}


def tint(colour: str, amount: float) -> str:
    """Mix a colour with white (amount 0 = colour, 1 = white)."""
    rgb = mcolors.to_rgb(colour)
    return mcolors.to_hex([c + (1 - c) * amount for c in rgb])


def apply() -> None:
    plt.rcParams.update({
        "font.family": FONT, "font.size": 7, "axes.labelsize": 7, "axes.titlesize": 7,
        "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5,
        "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": INK,
        "xtick.color": INK, "ytick.color": INK,
        "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.direction": "out", "ytick.direction": "out",
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
        "legend.frameon": False, "legend.handletextpad": 0.4, "legend.columnspacing": 1.2,
        "lines.solid_capstyle": "butt", "errorbar.capsize": 0,
        "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 300, "savefig.facecolor": "white",
    })


def letter(fig, x: float, y: float, text: str) -> None:
    """Panel letter at figure coordinates (top-left anchor)."""
    fig.text(x, y, text, fontsize=9, weight="bold", ha="left", va="top", color=INK)


def heading(ax, text: str, pad: float = 3) -> None:
    """A short panel heading, left-aligned above the axes, in secondary weight (not a title)."""
    ax.set_title(text, loc="left", fontsize=7, weight="bold", color=INK, pad=pad)


def save(fig, output: Path, name: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for extension in ("pdf", "png"):
        fig.savefig(output / f"{name}.{extension}", bbox_inches=None)
    plt.close(fig)


apply()
