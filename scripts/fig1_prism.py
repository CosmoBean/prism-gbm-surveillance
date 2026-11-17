"""Figure 1: the method. (a) What PRISM computes at one follow-up scan, stage by stage; (b) the evaluation protocol.

A methods schematic, not a result: it carries no scores or outcomes, only what each stage computes, as specified in
the Methods (Sections 2.1-2.3, 3.1-3.5). The two MRI slices are drawn by `schematic_slice` (no patient image).
Colour follows the score as in every figure (scripts/figure_style.py); navy marks the system's own stages.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

import figure_style as st

W, H = 180.0, 113.0      # drawing units (about 1 mm each); W / H equals the figure aspect
MONO = "DejaVu Sans Mono"


def fig1(output: Path) -> None:
    from generate_system_first_figures import schematic_slice

    fig = plt.figure(figsize=(st.WIDTH, st.WIDTH * H / W))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, W), ylim=(0, H)); ax.axis("off")

    def text(x, y, s, size=6.0, colour=st.INK, **kw):
        kw.setdefault("ha", "left"); kw.setdefault("va", "top")
        return ax.text(x, y, s, fontsize=size, color=colour, linespacing=1.35, **kw)

    def arrow(a, b, colour=st.NAVY, lw=0.7, style="-|>", **kw):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=5.5, color=colour, lw=lw,
                                     shrinkA=0, shrinkB=0, zorder=4, **kw))

    def box(x0, y0, x1, y1, edge=st.NAVY, face="white", lw=0.7, ls="-"):
        ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=1.3",
                                    fc=face, ec=edge, lw=lw, ls=ls, zorder=2))

    def card(x0, y0, x1, y1, title, colour, body="", size=6.0, face=None, mono=None):
        """Outlined box: a bold title in the box's colour, a plain body, an optional monospace line."""
        box(x0, y0, x1, y1, edge=colour, face=face or "white")
        text(x0 + 1.8, y1 - 1.6, title, size=6.4, colour=colour, weight="bold")
        y = y1 - 5.6
        if body:
            text(x0 + 1.8, y, body, size=size)
            y -= 2.85 * (body.count("\n") + 1) * size / 6.0
        if mono:
            text(x0 + 1.8, y - 0.6, mono, size=5.6, colour=st.MUTED, family=MONO)

    # ================================================================ (a) the pipeline at one scan
    st.panel_header(fig, 0.995, "a", "PRISM at one follow-up scan")

    cols = [(2.0, 28.0), (32.0, 68.0), (72.0, 103.0), (107.0, 140.0), (144.0, 179.0)]
    stages = ["Inputs", "Features", "Models", "Evidence statements", "Record and report"]
    sy = H - 9.0
    for i, ((x0, x1), name) in enumerate(zip(cols, stages)):
        ax.add_patch(plt.Circle((x0 + 2.0, sy), 1.9, fc=st.NAVY, ec="none", zorder=3))
        text(x0 + 2.0, sy, str(i + 1), size=5.8, colour="white", weight="bold", ha="center", va="center")
        text(x0 + 5.2, sy, name, size=6.6, colour=st.NAVY, weight="bold", va="center")
        ax.plot([x0, x1], [sy - 3.0, sy - 3.0], color=st.RULE, lw=0.5)

    top = sy - 5.5             # top of the content rows
    # Lane centres: imaging above, clinical history below, the combined model between them.
    y_img, y_comb, y_hist = top - 11.0, top - 30.0, top - 49.0

    # ---- 1 Inputs
    x0, x1 = cols[0]
    for k, (scale, seed, label) in enumerate([(0.82, 3, "previous"), (1.0, 4, "current")]):
        sx = x0 + k * 14.5
        f0 = ((sx) / W, (top - 13.0) / H)
        iax = fig.add_axes([f0[0], f0[1], 13.0 / W, 13.0 / H])
        schematic_slice(iax, scale, seed=seed)
        for t in list(iax.texts):
            t.remove()
        text(sx + 6.5, top - 13.6, label, size=5.6, colour=st.MUTED, ha="center")
    text(x0, top - 17.4, "T1c and FLAIR MRI,\nreleased masks (enhancing,\nFLAIR, necrosis, cavity)", size=5.8)

    ty = y_hist + 7.0          # treatment course as of the scan day
    ax.plot([x0 + 0.5, x1 - 1.0], [ty, ty], color=st.INK, lw=0.6)
    ax.add_patch(Rectangle((x0 + 7.5, ty - 0.9), 9.0, 1.8, fc=st.tint(st.HIST, 0.7), ec="none", zorder=3))
    for x, s, below in [(x0 + 3.0, "surgery", False), (x0 + 12.0, "RT", True), (x1 - 3.0, "scan", False)]:
        ax.plot([x, x], [ty - 1.2, ty + 1.2], color=st.INK, lw=0.9 if s == "scan" else 0.6, zorder=4)
        text(x, ty - 2.0 if below else ty + 3.6, s, size=5.6, colour=st.MUTED, ha="center")
    text(x0, ty + 8.6, "Treatment course\nas of the scan day", size=5.8)
    text(x0, ty - 5.4, "Age, sex, IDH and\nMGMT status", size=5.8)

    # ---- 2 Features
    x0, x1 = cols[1]
    bt, bb = top, y_comb + 4.0
    card(x0, bb, x1, bt, "Imaging features", st.IMG)
    text(x1 - 1.8, bt - 1.6, r"$\mathbf{x}_{\mathrm{img}} \in \mathbb{R}^{27}$", size=6.2, ha="right")
    seg = [(6, "6", 0.0), (13, "13", 0.35), (8, "8", 0.62)]
    bx0, bw, by = x0 + 1.8, x1 - x0 - 3.6, bt - 9.6
    xx = bx0
    for n, label, amount in seg:
        w = bw * n / 27
        ax.add_patch(Rectangle((xx, by), w - 0.4, 2.6, fc=st.tint(st.IMG, amount), ec="none", zorder=3))
        text(xx + (w - 0.4) / 2, by + 1.3, label, size=5.6, colour="white" if amount < 0.5 else st.INK,
             ha="center", va="center", weight="bold")
        xx += w
    text(bx0, by - 1.6, "6  log volumes: four compartments,\n    core and whole lesion\n"
                        "13 shape; T1c and FLAIR intensity\n    relative to normal brain\n"
                        "8  change since the previous scan\n    and since the smallest volume", size=5.7)

    hb, ht = y_hist - 8.0, y_comb - 4.0
    card(x0, hb, x1, ht, "Clinical-history features", st.HIST,
         "days since diagnosis and surgery;\nradiotherapy start, end, dose,\nfractions; chemotherapy started;\n"
         "time window after RT: during,\n≤ 12 weeks, later, unknown;\nage, sex, IDH, MGMT", size=5.7)
    text(x1 - 1.8, ht - 1.6, r"$\mathbf{x}_{\mathrm{hist}}$", size=6.2, ha="right")
    arrow((cols[0][1] - 0.5, y_img + 2.0), (x0, y_img + 2.0))
    arrow((cols[0][1] - 0.5, y_hist - 1.0), (x0, y_hist - 1.0))

    # ---- 3 Models
    x0, x1 = cols[2]
    mh = 6.4
    models = [(y_img, "Imaging model", st.IMG, r"$\mathbf{x}_{\mathrm{img}}$, no dates"),
              (y_comb, "Combined model", st.COMB, r"$\mathbf{x}_{\mathrm{img}} \oplus \mathbf{x}_{\mathrm{hist}}$"),
              (y_hist, "Clinical-history model", st.HIST, r"$\mathbf{x}_{\mathrm{hist}}$")]
    for y, name, colour, inputs in models:
        box(x0, y - mh, x1, y + mh, edge=colour, face=st.tint(colour, 0.9))
        text(x0 + 1.8, y + mh - 1.6, name, size=6.4, colour=colour, weight="bold")
        text(x0 + 1.8, y - 0.4, r"$\hat p = \sigma(\beta_0 + \boldsymbol{\beta}^{\top}\mathbf{z})$", size=6.2)
        text(x0 + 1.8, y - 3.6, "on " + inputs, size=5.7, colour=st.MUTED)
    fx = cols[1][1]
    arrow((fx, y_img), (x0, y_img), st.IMG)
    arrow((fx, y_hist), (x0, y_hist), st.HIST)
    arrow((fx, y_comb + 6.0), (x0, y_comb + 2.0), st.IMG)
    arrow((fx, y_comb - 6.0), (x0, y_comb - 2.0), st.HIST)
    text(x0, y_hist - mh - 1.6,
         "Ridge (L2) logistic regression;\nstandardised inputs; median\nimputation with an indicator;\n"
         "penalty by 3-fold patient-\ngrouped CV (log loss)", size=5.7, colour=st.MUTED)

    # ---- 4 Evidence statements
    x0, x1 = cols[3]
    eb = y_hist - 14.0
    gap = 1.6
    span = (top - eb - 2 * gap) / 3
    e3 = (eb, eb + span); e2 = (e3[1] + gap, e3[1] + gap + span); e1 = (e2[1] + gap, top)
    card(x0, e1[0], x1, e1[1], "Split-conformal set", st.NAVY,
         r"$s_i = 1 - \hat p_i(y_i)$, weighted 1/scans" "\nper patient; $\\alpha = 0.2$\n"
         r"$C(\hat p) = \{y : 1 - \hat p(y) \leq \hat q\,\}$" "\nrefit 70% / calibrate 30% of\ntraining patients",
         size=5.7)
    card(x0, e2[0], x1, e2[1], "Model agreement", st.NAVY,
         r"$\mathbb{1}[\hat p_{\mathrm{img}} > m_{\mathrm{img}}] = \mathbb{1}[\hat p_{\mathrm{hist}} > m_{\mathrm{hist}}]$"
         "\n$m$: score median in the cohort's\nevaluation scans", size=5.7)
    card(x0, e3[0], x1, e3[1], "Reliability card", st.NAVY,
         "situation = time window ×\nenhancement state; tested if\n≥ 10 scans of each outcome,\n"
         "otherwise few cases", size=5.7)
    mx = cols[2][1]
    jx = mx + 2.0
    for y, _, colour, _ in models:
        ax.plot([mx, jx], [y, y], color=st.NAVY, lw=0.7)
    ax.plot([jx, jx], [y_hist, y_img], color=st.NAVY, lw=0.7)
    for y in ((e1[0] + e1[1]) / 2, (e2[0] + e2[1]) / 2, (e3[0] + e3[1]) / 2):
        arrow((jx, y), (x0, y))

    # ---- 5 Record and report
    x0, x1 = cols[4]
    rx = x1 - x0
    r1 = (top - 17.0, top)
    card(x0, r1[0], x1, r1[1], "Structured record", st.NAVY, "every value under a fixed\nkey, with its source", size=5.7)
    text(x0 + 1.8, r1[0] + 6.4, "meas.enhancing_cc\nmodel.imaging.score\nconformal.combined.80",
         size=5.3, colour=st.MUTED, family=MONO)
    r2 = (r1[0] - 3.0 - 17.0, r1[0] - 3.0)
    box(x0, r2[0], x1, r2[1], edge=st.NAVY, ls=(0, (3, 1.5)))
    text(x0 + 1.8, r2[1] - 1.6, "Local language model", size=6.4, colour=st.NAVY, weight="bold")
    text(x0 + 1.8, r2[1] - 5.6, "Qwen3.8-27B, greedy decoding\nconstrained to a JSON schema:\n"
                                "{section, sentence, cited keys};\nno images, no arithmetic", size=5.7)
    r3 = (eb, r2[0] - 3.0)
    card(x0, r3[0], x1, r3[1], "Deterministic checker", st.NAVY,
         "every number in a cited field;\nflags, set, agreement, tier\nstated; no diagnosis or advice;\n"
         "verifier binds each number and\ndirection to its region", size=5.7)
    text(x0 + 1.8, r3[0] + 3.0, "accept, or reject without repair", size=5.6, colour=st.NAVY, weight="bold")
    cx = (x0 + x1) / 2
    bus = cols[3][1] + 2.0                       # every statement (and the scores) enter the record
    for y in ((e1[0] + e1[1]) / 2, (e2[0] + e2[1]) / 2, (e3[0] + e3[1]) / 2):
        ax.plot([cols[3][1], bus], [y, y], color=st.NAVY, lw=0.7)
    ry = (r1[0] + r1[1]) / 2
    ax.plot([bus, bus], [(e3[0] + e3[1]) / 2, ry], color=st.NAVY, lw=0.7)
    arrow((bus, ry), (x0, ry))
    arrow((cx, r1[0]), (cx, r2[1]))
    arrow((cx, r2[0]), (cx, r3[1]))

    # ================================================================ (b) evaluation protocol
    by1 = eb - 7.0
    st.panel_header(fig, (by1 + 2.4) / H, "b", "Evaluation")
    bt, bb = by1 - 4.0, 7.5
    mid = (bt + bb) / 2
    card(2.0, bb, 50.0, bt, "Development: MU-Glioma-Post", st.NAVY,
         "126 grade 4 patients; 5 repeats of 5-fold\ncross validation grouped by patient; pooled\n"
         "held-out AUC on 146 scans of 80 patients", size=5.7)
    card(56.0, bb, 92.0, bt, "Lock", st.NAVY,
         "each model fitted once on all\n181 MU detection scans, then\nfrozen; reduced clinical history\n"
         "where a cohort lacks dates", size=5.7)
    eh = (bt - bb - 2.0) / 2
    for y0, title, body in [(bt - eh, "External: LUMIERE", "178 scans of 79 patients; 3-label masks"),
                            (bb, "External: UCSF-ALPTDG", "69 second scans of 69 patients")]:
        box(98.0, y0, 140.0, y0 + eh, edge=st.NAVY)
        text(99.8, y0 + eh - 1.4, title, size=6.4, colour=st.NAVY, weight="bold")
        text(99.8, y0 + eh - 4.9, body, size=5.7)
    card(146.0, bb, 179.0, bt, "Measured", st.NAVY,
         "AUC, 95% CI from bootstrap\nsamples of patients; coverage\nof the 80% sets; reports\npassing the checker",
         size=5.7)
    arrow((50.0, mid), (56.0, mid))
    arrow((92.0, mid), (95.0, mid), style="-")
    ax.plot([95.0, 95.0], [bt - eh / 2, bb + eh / 2], color=st.NAVY, lw=0.7)
    arrow((95.0, bt - eh / 2), (98.0, bt - eh / 2)); arrow((95.0, bb + eh / 2), (98.0, bb + eh / 2))
    arrow((140.0, mid), (146.0, mid))
    text(2.0, bb - 2.2,
         "Label: the first scan at documented progression versus a scan followed by \u2265 120 days without "
         "progression (LUMIERE: rated stable or responding).", size=5.7, colour=st.MUTED)

    st.save(fig, output, "fig1_system")


if __name__ == "__main__":
    fig1(Path(__file__).resolve().parents[1] / "docs/manuscript/figures")
