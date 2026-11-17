"""Draw the manuscript figures from verified aggregate values (docs/manuscript/NUMBERS.md).

Every value below is an aggregate from NUMBERS.md (section named beside it); no patient-level data are read. The
example report in Figure 5 is synthetic: an invented scan written in the v3.1 report format (its slices are drawn by
schematic_slice, not taken from any patient), with the MU card row quoted in the Discussion (1 of 9 scans).
Figure 1 (the method) is drawn by scripts/fig1_prism.py; Figures 3 and 4 by scripts/generate_methods_figures.py.
All share scripts/figure_style.py.
"""
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
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
    # What each group is: a bracket above the axes (development | locked external | reference).
    for x0, x1, text in [(-0.42, 0.42, "Development (cross validation)"), (0.58, 2.42, "Locked MU models, external"),
                         (2.58, 3.42, "Refitted at UCSF (reference)")]:
        y = 1.04
        ax.plot([x0, x0, x1, x1], [y - 0.015, y, y, y - 0.015], transform=ax.get_xaxis_transform(), color=st.MUTED,
                lw=0.6, clip_on=False)
        ax.text((x0 + x1) / 2, y + 0.02, text, transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                fontsize=6.5, color=st.MUTED)
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
REPORT = [
    ("Scan", "This scan was taken 8 weeks after the end of radiotherapy, early after radiotherapy.", "scan.phase"),
    ("Scan", "The automatic segmentation gives indicative volumes of 6.0 cc enhancing tumour and 31.0 cc FLAIR hyperintensity.", "meas.label, meas.enhancing_cc, …"),
    ("Scan", "Enhancing tumour is 2.0 cc larger than at the previous scan.", "meas.enhancing_change_…"),
    ("Models", "The clinical-history model is based on clinical data and the position in treatment: clinical-history score 0.21, below the median of its scores in the MU-Glioma-Post evaluation scans (0.38).", "model.clinical_history.*"),
    ("Models", "The imaging model is based on the segmented tumour and its change: imaging score 0.64, above the median of its scores in the MU-Glioma-Post evaluation scans (0.45).", "model.imaging.*"),
    ("Models", "The two models disagree: the clinical-history score is below its median and the imaging score is above its median.", "models.agreement_statement"),
    ("Combined", "The combined score, based on the inputs of both models, is 0.33.", "model.combined.*"),
    ("Combined", "Each score is a model output between 0 and 1 that ranks scans by how closely they resemble the progression scans of the training data; it is not a diagnosis and not a calibrated probability for this patient.", "models.score_meaning"),
    ("Combined", "The 80% conformal set holds both outcomes.", "conformal.combined.80.statement"),
    ("Trust", "This situation, early after radiotherapy with enhancing tumour increased, has few cases: 1 of 9 scans was progression.", "card.situation, card.tier_statement"),
    ("Trust", "The models disagree flag is raised: the clinical-history score is below its median and the imaging score is above its median.", "flags.models_disagree.*"),
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
        ax.text(x, y, s, color="white", fontsize=6.5, ha="center", va="center")
    ax.set(xlim=(-1, 1), ylim=(1, -1)); ax.axis("off")


def fig5(output: Path) -> None:
    """Report anatomy (synthetic example) and the automatic evaluation. NUMBERS.md 7."""
    height = 7.0
    fig = plt.figure(figsize=(WIDTH, height))
    left, width, bottom, ax_h = 0.035, 0.625, 0.012, 0.945
    ax = fig.add_axes([left, bottom, width, ax_h]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    st.letter(fig, 0.008, 0.995, "a")
    pt = 1 / (height * 72 * ax_h)                     # one point in axes-y units
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor=st.RULE, lw=0.6))
    ax.add_patch(plt.Rectangle((0, 1 - 3 * pt), 1, 3 * pt, facecolor=st.NAVY, edgecolor="none"))
    x0, x1 = 0.035, 0.965
    y = 1 - 12 * pt
    ax.text(x0, y, "PRISM surveillance report", fontsize=9, weight="bold", va="top", color=st.NAVY)
    ax.text(x1, y - 1 * pt, "SYNTHETIC EXAMPLE", fontsize=6, va="top", ha="right", color=st.MUTED, weight="bold")
    y -= 13 * pt
    ax.text(x0, y, "Scan 8 weeks after the end of radiotherapy  ·  compared with the previous scan  ·  "
            "models from MU", fontsize=6.5, va="top", color=st.MUTED)
    y -= 11 * pt
    ax.plot([x0, x1], [y, y], color=st.RULE, lw=0.6)

    # Segmentation figure strip (the real report attaches one per scan; this one is drawn).
    strip_h = 86 * pt
    y -= 7 * pt
    fx = lambda a: left + width * a                  # axes-x to figure-x
    fy = lambda b: bottom + ax_h * b
    img_w = 0.25
    for i, (scale, label) in enumerate([(1.0, "This scan"), (0.82, "Previous scan, same slice")]):
        a0 = x0 + i * (img_w + 0.02)
        iax = fig.add_axes([fx(a0), fy(y - strip_h), width * img_w, ax_h * strip_h])
        schematic_slice(iax, scale)
        iax.set_aspect("auto")
        ax.text(a0, y - strip_h - 2.5 * pt, label, fontsize=6.5, va="top", color=st.INK)
    vx = x0 + 2 * (img_w + 0.02) + 0.075
    vax = fig.add_axes([fx(vx), fy(y - strip_h + 16 * pt), width * (x1 - vx), ax_h * (strip_h - 18 * pt)])
    vax.plot([0, 1], [4.0, 6.0], "-o", color=st.INK, ms=3.2, lw=1.0, label="Enhancing")
    vax.plot([0, 1], [27.0, 31.0], marker="o", color=st.MUTED, mfc="white", ms=3.2, lw=1.0, ls=(0, (3, 2)), label="FLAIR")
    vax.set(xticks=[0, 1], xlim=(-0.3, 1.3), ylim=(0, 36), yticks=[0, 10, 20, 30], ylabel="Volume (cc)")
    vax.set_xticklabels(["Previous", "This scan"])
    vax.tick_params(axis="x", length=0)
    vax.legend(fontsize=6.3, loc="center left", handlelength=1.8, bbox_to_anchor=(0, 0.55))
    ax.text(vx - 0.075, y - strip_h - 2.5 * pt, "Dashed: FLAIR outline. Drawn, not a patient.", fontsize=6,
            va="top", color=st.MUTED, style="italic")
    y -= strip_h + 20 * pt

    body = 6.8
    current = None
    for section, text, keys in REPORT:
        if section != current:
            y -= 4 * pt if current else 0
            ax.text(x0, y, section.upper(), fontsize=6.3, weight="bold", va="top", color=st.NAVY)
            y -= 9 * pt
            ax.plot([x0, x1], [y, y], color=st.RULE, lw=0.5)
            y -= 4 * pt; current = section
        lines = textwrap.wrap(text, 92)
        ax.text(x0, y, "\n".join(lines), fontsize=body, va="top", linespacing=1.3, color=st.INK)
        y -= body * 1.3 * len(lines) * pt
        if len(lines[-1]) * 3.1 + len(keys) * 3.8 + 12 < 280:   # cited fields fit beside the last line
            ax.text(x1, y + body * 1.3 * pt, keys, fontsize=5.8, va="top", ha="right", color=st.MUTED,
                    family="DejaVu Sans Mono")
            y -= 4.0 * pt
        else:
            ax.text(x1, y, keys, fontsize=5.8, va="top", ha="right", color=st.MUTED, family="DejaVu Sans Mono")
            y -= 11.0 * pt
    ax.plot([x0, x1], [y + 1 * pt, y + 1 * pt], color=st.RULE, lw=0.6)
    ax.text(x0, y - 3 * pt, "\n".join(textwrap.wrap(LIMITATIONS, 112)), fontsize=6.3, va="top",
            color=st.MUTED, style="italic", linespacing=1.3)

    # Model-size ladder (NUMBERS.md 7: v3.1, frozen prompt, no per-model tuning; descriptive).
    bx = fig.add_axes([0.73, 0.50, 0.25, 0.44])
    st.letter(fig, 0.69, 0.995, "b")
    ladder = [("Qwen 2B", 3.6, 21, False), ("Qwen 4B", 8.0, 306, False), ("Gemma E4B", 14.5, 117, False),
              ("Qwen 9B", 16.8, 368, False), ("Qwen 27B (used)", 50.2, 406, True),
              ("Gemma 31B", 57.9, 406, True), ("Qwen 35B-A3B", 64.7, 389, False)]
    dark, light = st.NAVY, st.tint(st.NAVY, 0.72)
    for i, (name, gib, k, ok) in enumerate(ladder):
        y = len(ladder) - 1 - i
        bx.barh(y, k / 406, color=dark if ok else light, height=0.46)
        bx.text(0, y + 0.3, name, va="bottom", ha="left", fontsize=6.5, color=st.INK, weight="bold" if ok else "normal")
        bx.text(1.0, y + 0.3, f"{gib:.1f} GiB", va="bottom", ha="right", fontsize=6, color=st.MUTED)
        inside = k >= 330
        bx.text(k / 406 - 0.02 if inside else k / 406 + 0.02, y, str(k), va="center", ha="right" if inside else "left",
                fontsize=6.3, color="white" if ok else st.INK)
    bx.set(yticks=[], xlim=(0, 1), ylim=(-0.45, len(ladder) - 0.1), xlabel="Share of the 406 reports passing")
    bx.spines["left"].set_visible(False)
    bx.text(0, -0.15, "Dark: \u2265 95% passing in every cohort.\nSame prompt for every model.",
            transform=bx.transAxes, fontsize=6.2, va="top", color=st.MUTED, linespacing=1.3)
    st.save(fig, output, "fig5_report")


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    from fig1_prism import fig1
    fig1(output); fig2(output); fig5(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output-dir", type=Path, default=Path("docs/manuscript/figures"))
    generate(parser.parse_args().output_dir)
