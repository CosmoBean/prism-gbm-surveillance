"""Generate the five system-first manuscript figures from verified manuscript values."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def save(fig, output: Path, name: str) -> None:
    for extension in ("pdf", "png"):
        fig.savefig(output / f"{name}.{extension}", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def boxed(ax, x, y, text, colour="#e8f1fa"):
    ax.add_patch(FancyBboxPatch((x, y), .22, .22, boxstyle="round,pad=.02", facecolor=colour, edgecolor="#234", linewidth=1.2))
    ax.text(x + .11, y + .11, text, ha="center", va="center", fontsize=8, wrap=True)


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 2.8)); ax.axis("off")
    for x, text, colour in [(0.02, "Serial MRI\nand treatment record", "#e8f1fa"), (.28, "Image and timeline\nevidence pathways", "#e8f1fa"), (.54, "Structured evidence record\nmeasurements • scores • limits", "#fff3d6"), (.80, "Local checked report\nfor clinician review", "#f8e5e5")]: boxed(ax, x, .38, text, colour)
    for x in (.24, .50, .76): ax.annotate("", (x + .03, .49), (x, .49), arrowprops={"arrowstyle": "->"})
    ax.set_title("PRISM turns longitudinal evidence into an inspectable report", loc="left", weight="bold")
    save(fig, output, "fig1_system")

    cohorts = ["MU\ninternal", "LUMIERE\nlocked", "UCSF\nlocked"]
    values = [[.71, .82, .82], [.65, .69, .77], [.73, .56, .86]]
    fig, ax = plt.subplots(figsize=(7, 3.5)); width=.22; xs=range(3)
    for i, label in enumerate(("Image pathway", "Timeline pathway", "Combined score")):
        ax.bar([x + (i-1)*width for x in xs], [row[i] for row in values], width, label=label)
    ax.set(xticks=list(xs), xticklabels=cohorts, ylim=(0,1), ylabel="AUC", title="PRISM components rank scans across cohorts")
    ax.legend(frameon=False, ncol=3, fontsize=8); ax.axhline(.5, color="0.6", lw=.8); save(fig, output, "fig2_transport")

    fig, ax = plt.subplots(figsize=(7, 3.5)); labels=["MU timeline", "MU image", "UCSF image", "UCSF enhancing\nvolume"]
    ax.bar(labels, [.82,.71,.73,.88], color=["#4c78a8", "#72b7b2", "#72b7b2", "#f58518"])
    ax.set(ylim=(0,1), ylabel="AUC", title="Separate streams show what carries each cohort's signal")
    ax.text(.5, .08, "MU: treatment timing is prominent\nUCSF: enhancing volume is prominent", transform=ax.transAxes, ha="center", fontsize=9)
    save(fig, output, "fig3_evidence")

    fig, ax = plt.subplots(figsize=(7, 3.5)); ax.bar(["MU", "LUMIERE", "UCSF"], [.82,.87,.78], color="#54a24b")
    ax.axhline(.78, color="#555", ls="--", label="prespecified threshold"); ax.set(ylim=(0,1), ylabel="Coverage", title="Confidence fields state both coverage and thin evidence")
    ax.legend(frameon=False); ax.text(.5, .08, "The report identifies pathway disagreement and few-case situations.", transform=ax.transAxes, ha="center", fontsize=9)
    save(fig, output, "fig4_confidence")

    fig, ax = plt.subplots(figsize=(8, 3.5)); ax.axis("off")
    boxed(ax, .04, .38, "Report contents\nlongitudinal context\nmeasurements\nseparate scores\nwhat was not used", "#e8f1fa")
    boxed(ax, .38, .38, "Evidence limits\nconformal set\npathway agreement\nfew-case tier\nprovenance", "#fff3d6")
    boxed(ax, .72, .38, "Automatic evaluation\n406/406 lexical passes\n220/220 tiers stated\n28/30 perturbations", "#f8e5e5")
    ax.set_title("The report presents evidence and its limits; evaluation is automatic, not clinical", loc="left", weight="bold")
    save(fig, output, "fig5_report")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output-dir", type=Path, default=Path("docs/manuscript/figures"))
    generate(parser.parse_args().output_dir)
