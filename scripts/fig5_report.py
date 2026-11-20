"""Figure 5: the report PRISM writes, and the check.

(a) One real report for a held-out scan, written by the local language model (report v3.2, Qwen3.8-27B, greedy) and
accepted by the checker, laid out as a report page in the order of the BT-RADS follow-up template
(docs/review/REPORT_FORMAT_RESEARCH.md): header with the comparison and the flags; the attached segmentation slices
beside the measurement table; the two models' scores against their cohort medians, then the combined score, with their
conformal sets; the reliability card; the language model's sentences verbatim, numbered; the fixed limitations. Every
value is read from the record's facts (prism.report.facts_v3_2) and the model output; nothing is typed in here. The
images follow the report's own segmentation rules (prism.report.seg_figure: slice choice, masks, previous scan at the
same atlas slice when the brains overlap).

Example (written rule, fixed before drawing; it does not look at the scores): the progression scan of strip A of the
case-strip figure (PatientID_0014, Timepoint 6), so the reader can follow that patient from the strip to the report.
The scan is asserted to meet the selection criteria: an MU-Glioma-Post evaluation record scored out-of-fold, a report
accepted by the checker, at least 1 cc of enhancing tumour, a previous scan, and no out-of-training-range flag.

(b) Reports passing the checker for seven local models (NUMBERS.md 7; v3.1 prompt, no per-model tuning).

The record fields each sentence cites are drawn separately as a supplementary figure (fig5_report_fields).

    cd scripts && ../.venv/bin/python fig5_report.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch
from matplotlib.textpath import TextPath

import figure_style as st

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from prism.report import seg_figure as SEG  # noqa: E402
from prism.report.facts_v3_2 import check_v3_2, facts_v3_2  # noqa: E402
from prism.report.sections_v3 import LIMITATIONS_V3_1  # noqa: E402

RUN = REPO / "outputs" / "results" / "analyses" / "report_v3_2"
RECORD = "mu|grade4|PatientID_0014_Timepoint_6"
PREVIOUS = "PatientID_0014_Timepoint_5"
MONO = "DejaVu Sans Mono"
SECTION = {"scan": "Scan", "models": "Models", "combined": "Combined", "trust": "Trust"}
TWO_MODELS = [("clinical_history", "Clinical history", st.HIST), ("imaging", "Imaging", st.IMG)]
COMBINED = [("combined", "Combined", st.COMB)]
ET_C, SNFH_C = "#F2C14E", "#FFFFFF"
SET_WORDS = {"both outcomes": "both", "progression only": "progression", "no progression only": "no progression"}
FLAG_ORDER = ("models_disagree", "out_of_range", "card_tier", "conformal_both")
MINUS = "−"

W = 180.0                       # drawing units, 1 unit = 0.04 in (the figure is 7.2 in wide)
PT = 72 * 0.04                  # points per drawing unit
# Font sizes (pt at 7.2 in). Placed at the 34 pc text width the figure prints at 0.79 x (8.2 pt prints at 6.5 pt);
# the page holds the whole report and panel (b) only at about this size.
BODY, NOTE, HEAD, TITLE = 8.2, 7.2, 8.0, 9.5


def signed(v: float, fmt: str = "{:.1f}") -> str:
    s = fmt.format(abs(v))
    return ("+" if v > 0 else MINUS if v < 0 else "") + s


def width_units(s: str, size: float, **font) -> float:
    prop = FontProperties(family=font.get("family", st.FONT), weight=font.get("weight", "normal"))
    return TextPath((0, 0), s, size=size, prop=prop).get_extents().width / PT


def wrap(s: str, size: float, width: float, **font) -> list[str]:
    """Greedy word wrap to a width in drawing units, measured with the figure font."""
    lines, cur = [], ""
    for word in s.split():
        add = word if not cur else cur + " " + word
        if not cur or width_units(add, size, **font) <= width:
            cur = add
        else:
            lines.append(cur); cur = word
    return lines + [cur]


def line_h(size: float, spacing: float = 1.2) -> float:
    return size * spacing / PT


def load():
    rec = next(json.loads(l) for l in open(RUN / "records" / "eval.jsonl") if json.loads(l)["record_id"] == RECORD)
    out = next(json.loads(l) for l in open(RUN / "llm" / "outputs_eval_v3_2.jsonl")
               if json.loads(l)["id"] == f"eval|{RECORD}")
    claims = json.loads(out["text"])["sentences"]
    F = facts_v3_2(rec)
    res = check_v3_2(claims, rec)
    assert res["pass"], res                                   # the checker accepted this report
    for c in claims:
        assert all(k in F for k in c["fields"]), c
    # the selection criteria (module docstring)
    assert rec["cohort"] == "mu" and rec["provenance"]["scores"].startswith("out-of-fold"), rec["provenance"]
    assert F["meas.enhancing_cc"] >= 1.0 and F["scan.previous_available"] == "yes"
    assert not F["flags.out_of_range.active"]
    return F, claims


def slices():
    """This scan (T1c, FLAIR) at the report's own slice, and the previous scan's T1c at the same atlas slice (its own
    slice if the brains do not overlap), cropped to the brain."""
    cur = SEG.load_scan("mu", RECORD.split("|")[-1])
    prev = SEG.load_scan("mu", PREVIOUS)
    k, rule, _ = SEG.choose_slice(cur.comp, cur.brain)
    coreg = prev.t1c.shape == cur.t1c.shape and SEG.dice(prev.brain, cur.brain) >= SEG.COREG_DICE
    kp = k if coreg else SEG.choose_slice(prev.comp, prev.brain)[0]
    out = []
    for scan, kk, seq, title in [(cur, k, "t1c", "This scan, T1c"), (cur, k, "flair", "This scan, FLAIR"),
                                 (prev, kp, "t1c", "Previous scan, T1c")]:
        img = (scan.t1c if seq == "t1c" else scan.flair)[:, :, kk]
        b = scan.brain[:, :, kk]
        lo, hi = np.percentile(img[b], [0.5, 99.5])
        r, c = np.where(b)
        sl = (slice(r.min(), r.max() + 1), slice(c.min(), c.max() + 1))
        disp = lambda a: SEG.to_display(a[sl])
        out.append(dict(img=disp(np.clip((img - lo) / (hi - lo), 0, 1)), et=disp(scan.comp["et"][:, :, kk]),
                        snfh=disp(scan.comp["snfh"][:, :, kk]), seq=seq, title=title))
    where = "same atlas slice" if coreg else "its own slice with the most enhancement"
    return out, rule, where


def fig5(output: Path) -> None:
    F, claims = load()
    imgs, rule, where = slices()
    ha = draw(None, F, claims, imgs, rule, where, 400.0)        # dry run: the height panel (a) needs
    draw(output, F, claims, imgs, rule, where, ha)
    fields_figure(output, claims)
    ladder_figure(output)


HB = 0.0                        # no panel (b): the checker ladder is its own figure (ladder_figure)


def draw(output, F, claims, imgs, rule, where, HA) -> float:
    H = HA + HB
    fig = plt.figure(figsize=(st.WIDTH, st.WIDTH * H / W))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, W), ylim=(0, H)); ax.axis("off")

    def text(x, y, s, size=BODY, colour=st.INK, **kw):
        kw.setdefault("ha", "left"); kw.setdefault("va", "top")
        kw.setdefault("linespacing", 1.2)
        return ax.text(x, y, s, fontsize=size, color=colour, **kw)

    def rule_line(y, x0=6.0, x1=W - 6.0, colour=st.RULE, lw=0.5):
        ax.plot([x0, x1], [y, y], color=colour, lw=lw)

    def head(y, s):
        text(6.0, y, s.upper(), size=HEAD, colour=st.NAVY, weight="bold")
        return y - line_h(HEAD) - 1.6

    fig.text(0.004, 0.998, "A report PRISM wrote for a held-out scan (MU-Glioma-Post)", fontsize=7, weight="bold",
             ha="left", va="top", color=st.INK)
    top = H - 6.0

    # ---------------------------------------------------------------- header: scan, comparison, flags
    y = top - 3.0
    text(6.0, y, "PRISM follow-up MRI report", size=TITLE, colour=st.NAVY, weight="bold")
    text(W - 6.0, y - 0.4, "checker: accepted", size=NOTE, colour=st.MUTED, ha="right")
    y -= line_h(TITLE) + 1.2
    phase = F["scan.phase"][0].upper() + F["scan.phase"][1:]
    text(6.0, y, f"{phase}  ·  compared with the previous scan {F['scan.days_since_previous']} days earlier",
         size=NOTE, colour=st.MUTED)
    y -= line_h(NOTE)
    text(6.0, y, F["system.cohort"][0].upper() + F["system.cohort"][1:], size=NOTE, colour=st.MUTED)
    y -= line_h(NOTE) + 1.4
    raised = [F[f"flags.{f}.name"] for f in FLAG_ORDER if F[f"flags.{f}.active"]]
    text(6.0, y, "Flags", size=BODY, weight="bold")
    shown = "; ".join(raised) if raised else "none raised"
    text(18.0, y, shown, size=BODY)
    checked = ", ".join(F[f"flags.{f}.name"] for f in FLAG_ORDER)
    text(18.0 + width_units(shown, BODY) + 3.0, y - 0.3, f"(checked: {checked})", size=NOTE, colour=st.MUTED)
    y -= line_h(BODY) + 1.6
    rule_line(y, lw=0.7, colour=st.NAVY)

    # ---------------------------------------------------------------- 1 images + measurements
    y -= 2.6
    y = head(y, "1  What the scan shows")
    iw, gap = 23.0, 1.4
    for i, im in enumerate(imgs):
        x0 = 6.0 + i * (iw + gap)
        iax = fig.add_axes([x0 / W, (y - iw) / H, iw / W, iw / H])
        iax.imshow(im["img"], cmap="gray", vmin=0, vmax=1, interpolation="bilinear", aspect="auto")
        if im["seq"] == "t1c" and im["et"].any():
            iax.contour(im["et"].astype(float), levels=[0.5], colors=[ET_C], linewidths=0.8)
        if im["seq"] == "flair" and im["snfh"].any():
            iax.contour(im["snfh"].astype(float), levels=[0.5], colors=[SNFH_C], linewidths=0.7,
                        linestyles=[(0, (2, 1.4))])
        iax.set_xticks([]); iax.set_yticks([])
        for sp in iax.spines.values():
            sp.set_visible(False)
        iax.text(0.04, 0.96, "R", transform=iax.transAxes, color="white", fontsize=NOTE, va="top")
        iax.text(0.96, 0.96, "L", transform=iax.transAxes, color="white", fontsize=NOTE, va="top", ha="right")
        text(x0, y - iw - 0.8, im["title"], size=NOTE)
    # measurement table, right of the images
    tx = 6.0 + 3 * (iw + gap) + 3.0
    cols = [tx, tx + 46.0, tx + 49.0, tx + 70.0]           # name, this scan (right-aligned), vs previous, vs smallest
    text(cols[0], y, "Volume (cc)", size=NOTE, colour=st.MUTED)
    text(cols[1], y, "This\nscan", size=NOTE, colour=st.MUTED, ha="right")
    text(cols[2], y, f"Change since\nprevious ({F['scan.days_since_previous']} d)", size=NOTE, colour=st.MUTED)
    text(cols[3], y, "Change since\nsmallest earlier", size=NOTE, colour=st.MUTED)
    ry = y - 2 * line_h(NOTE) - 0.6
    rule_line(ry, tx, W - 6.0)

    def change(k):
        if f"meas.{k}_change_since_previous_cc" not in F:
            return "–"
        s = signed(F[f"meas.{k}_change_since_previous_cc"])
        if f"meas.{k}_change_since_previous_percent" in F:
            s += f" ({signed(F[f'meas.{k}_change_since_previous_percent'], '{:d}')}%)"
        return s

    em = "–"
    if "meas.enhancing_change_since_earlier_minimum_cc" in F:
        d = F["meas.enhancing_change_since_earlier_minimum_cc"]
        em = f"{signed(d)} (from {F['meas.enhancing_earlier_minimum_cc']:.1f})" if d else "none"
    rows = [("Enhancing tumour", F["meas.enhancing_cc"], change("enhancing"), em),
            ("FLAIR hyperintensity", F["meas.flair_hyperintensity_cc"], change("flair_hyperintensity"), "–"),
            ("Necrosis", F.get("meas.necrosis_cc"), "–", "–"),
            ("Resection cavity", F.get("meas.cavity_cc"), "–", "–")]
    ry -= 1.2
    for name, v, d1, d2 in rows:
        text(cols[0], ry, name)
        text(cols[1], ry, "–" if v is None else f"{v:.1f}", ha="right", weight="bold")
        text(cols[2], ry, d1)
        text(cols[3], ry, d2)
        ry -= line_h(BODY) + 0.5
    rule_line(ry + 0.6, tx, W - 6.0)
    text(tx, ry - 0.3, F["meas.label"][0].upper() + F["meas.label"][1:] + ".", size=NOTE, colour=st.MUTED)
    y = min(y - iw - line_h(NOTE) - 1.4, ry - line_h(NOTE) - 1.0)
    note = (f"Slice: {rule}; the previous scan at the {where}. Yellow, enhancing tumour; dashed white, FLAIR "
            "hyperintensity. The images are attached to the report; the language model sees no image.")
    nl = wrap(note, NOTE, W - 12.0)
    text(6.0, y, "\n".join(nl), size=NOTE, colour=st.MUTED)
    y -= len(nl) * line_h(NOTE) + 1.4
    rule_line(y)

    # ---------------------------------------------------------------- 2 the two models, 3 the combined score
    track0, track1 = 62.0, 102.0
    c_score, c_side, c80, c90 = 114.0, 118.0, 136.0, 157.0
    xs = lambda v: track0 + (track1 - track0) * v

    def score_rows(y, models, header):
        if header:
            text(track0, y, "0", size=NOTE, colour=st.MUTED, ha="center")
            text(track1, y, "1", size=NOTE, colour=st.MUTED, ha="center")
            text(c_score, y, "Score", size=NOTE, colour=st.MUTED, ha="right")
            text(c_side, y, "vs median", size=NOTE, colour=st.MUTED)
            text(c80, y, "80% set", size=NOTE, colour=st.MUTED)
            text(c90, y, "90% set", size=NOTE, colour=st.MUTED)
            y -= line_h(NOTE) + 0.4
        else:
            y -= line_h(HEAD) + 1.0
        for key, name, colour in models:
            cy = y - 1.8
            text(6.0, cy, name, colour=colour, weight="bold", va="center")
            ax.plot([track0, track1], [cy, cy], color=st.RULE, lw=0.9, solid_capstyle="round")
            med = F.get(f"model.{key}.cohort_median")
            if med is not None:
                ax.plot([xs(med)] * 2, [cy - 1.6, cy + 1.6], color=st.CLIN, lw=1.0)
            ax.add_patch(plt.Circle((xs(F[f"model.{key}.score"]), cy), 1.25, fc=colour, ec="white", lw=0.5,
                                    zorder=4))
            text(c_score, cy, f"{F[f'model.{key}.score']:.2f}", va="center", weight="bold", ha="right")
            text(c_side, cy, F.get(f"model.{key}.side", "–") if med is not None else "–", va="center")
            for c, lvl in [(c80, 80), (c90, 90)]:
                text(c, cy, SET_WORDS[F[f"conformal.{key}.{lvl}.set"]], va="center")
            y -= 4.4
        return y

    y -= 2.4
    hy = y
    y = head(y, "2  Model predictions")
    y = score_rows(hy, TWO_MODELS, True)                       # column heads on the section-heading line
    agree = F["models.agreement_statement"]
    text(6.0, y + 0.6, agree[0].upper() + agree[1:] + ".", size=NOTE, colour=st.MUTED)
    y -= line_h(NOTE) + 1.6
    y = score_rows(y + line_h(HEAD) + 0.6, COMBINED, False)                  # the combined score continues section 2
    text(6.0, y + 0.6, "Grey tick: median of the model's scores in the MU-Glioma-Post evaluation scans. A conformal "
                       "set lists the outcomes the score cannot rule out.", size=NOTE, colour=st.MUTED)
    y -= line_h(NOTE) + 0.6
    rule_line(y)

    # ---------------------------------------------------------------- 3 reliability card
    y -= 1.8
    y = head(y, "3  Match with previously seen scans")
    lab = 30.0
    text(6.0, y, "Situation", colour=st.MUTED)
    sl = wrap(F["card.situation"], BODY, W - 6.0 - lab)
    text(lab, y, "\n".join(sl))
    y -= len(sl) * line_h(BODY) + 0.6
    text(6.0, y, "Tier", colour=st.MUTED)
    text(lab, y, f"{F['card.tier']}: {F['card.n_progression']} progression and {F['card.n_no_progression']} "
                 "non-progression scans in this situation at MU-Glioma-Post")
    y -= line_h(BODY) + 0.6
    if "card.imaging.auc" in F:
        parts = []
        for key, name in [("clinical_history", "clinical history"), ("imaging", "imaging"), ("both", "combined")]:
            if f"card.{key}.auc" in F:
                parts.append(f"{name} {F[f'card.{key}.auc']:.2f} ({F[f'card.{key}.auc_low']:.2f}–"
                             f"{F[f'card.{key}.auc_high']:.2f})")
        text(6.0, y, f"AUC here", colour=st.MUTED)
        text(lab, y, "; ".join(parts) + f"  ({F['card.interval_level_percent']}% CI)")
        y -= line_h(BODY) + 0.6
    text(6.0, y, "Agreement", colour=st.MUTED)
    text(lab, y, f"{F['card.agreement_progression_percent']}% of the evaluation scans with this agreement pattern "
                 "were progression scans")
    y -= line_h(BODY) + 1.2
    rule_line(y)

    # ---------------------------------------------------------------- the language model's text
    y -= 2.4
    text(6.0, y, "REPORT TEXT", size=HEAD, colour=st.NAVY, weight="bold")
    text(6.0 + width_units("REPORT TEXT", HEAD, weight="bold") + 3.0, y + 0.1,
         "written by the local language model from the record alone; verbatim", size=NOTE, colour=st.MUTED)
    y -= line_h(HEAD) + 1.6
    tx0, tw = 29.0, W - 6.0 - 29.0
    last = None
    for n, c in enumerate(claims, 1):
        if c["section"] != last:
            text(6.0, y, SECTION[c["section"]], colour=st.NAVY, weight="bold")
            last = c["section"]
        lines = wrap(c["text"], BODY, tw)
        text(tx0 - 2.2, y, f"{n}", size=NOTE, colour=st.MUTED, ha="right")
        text(tx0, y, "\n".join(lines))
        y -= len(lines) * line_h(BODY) + 0.5
    rule_line(y + 0.2)

    # ---------------------------------------------------------------- limitations (fixed text)
    y -= 1.6
    lim = wrap("Limitations (fixed text): " + LIMITATIONS_V3_1, 6.8, W - 12.0)
    text(6.0, y, "\n".join(lim), size=6.8, colour=st.MUTED, style="italic")
    y -= len(lim) * line_h(6.8) + 2.0
    used = top - y + 6.0                                     # height panel (a) needs
    if output is None:
        plt.close(fig)
        return used
    ax.add_patch(FancyBboxPatch((2.0, y), W - 4.0, top - y, boxstyle="round,pad=0,rounding_size=1.5",
                                fc="none", ec=st.NAVY, lw=0.7, zorder=0))

    st.save(fig, output, "fig5_report")
    return HA


def ladder_figure(output: Path) -> None:
    """Reports passing the checker, of 406, by local language model (same prompt, no per-model tuning)."""
    ladder = [("Qwen3.5 2B", 3.6, 21, False), ("Qwen3.5 4B", 8.0, 306, False), ("Gemma-4 E4B", 14.5, 117, False),
              ("Qwen3.5 9B", 16.8, 368, False), ("Qwen3.8 27B (used)", 50.2, 406, True),
              ("Gemma-4 31B", 57.9, 406, True), ("Qwen3.5 35B-A3B", 64.7, 389, False)]
    fig = plt.figure(figsize=(st.WIDTH, 2.0))
    ax = fig.add_axes([0.40, 0.20, 0.52, 0.68])
    n = len(ladder)
    for i, (name, gib, k, ok) in enumerate(ladder):
        yv = n - 1 - i
        ax.barh(yv, k, height=0.62, color=st.INK if ok else st.tint(st.INK, 0.72), lw=0)
        ax.text(k + 5, yv, f"{k}", va="center", ha="left", fontsize=6.5, color=st.INK)
        fig.text(0.385, 0.20 + 0.68 * (yv + 0.5) / n, f"{gib:.1f}", va="center", ha="right", fontsize=6.5,
                 color=st.MUTED)
    ax.set(xlim=(0, 406), ylim=(-0.5, n - 0.5), yticks=range(n), xticks=[0, 100, 200, 300, 406])
    ax.set_yticklabels([x[0] for x in reversed(ladder)])
    for lab, (_, _, _, ok) in zip(ax.get_yticklabels(), reversed(ladder)):
        lab.set_weight("bold" if ok else "normal")
    ax.tick_params(axis="y", length=0, pad=52)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Reports passing the checker (of 406)", labelpad=2)
    fig.text(0.385, 0.92, "Weights (GiB)", va="bottom", ha="right", fontsize=6.3, color=st.MUTED)
    fig.text(0.40, 0.92, "Dark: at least 95% passing in every cohort. Same prompt for every model, no per-model "
             "tuning.", va="bottom", ha="left", fontsize=6.3, color=st.MUTED)
    st.save(fig, output, "fig_llm_checker")


def fields_figure(output: Path, claims) -> None:
    """Supplementary: each sentence of the Figure 5 report with the record fields it cites."""
    size, msize = 7.4, 6.4
    tx0, tw, kx = 10.0, 84.0, 98.0
    rows, h = [], 10.0
    for n, c in enumerate(claims, 1):
        lines = wrap(c["text"], size, tw)
        keys = c["fields"]
        rows.append((n, lines, keys))
        h += max(len(lines) * line_h(size), len(keys) * line_h(msize, 1.2)) + 1.6
    fig = plt.figure(figsize=(st.WIDTH, st.WIDTH * h / W))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set(xlim=(0, W), ylim=(0, h)); ax.axis("off")
    y = h - 3.0
    ax.text(tx0, y, "Sentence (verbatim)", fontsize=size, color=st.MUTED, va="top")
    ax.text(kx, y, "Record fields cited", fontsize=size, color=st.MUTED, va="top")
    y -= line_h(size) + 0.6
    ax.plot([4.0, W - 4.0], [y, y], color=st.RULE, lw=0.5)
    y -= 1.2
    for n, lines, keys in rows:
        ax.text(tx0 - 2.0, y, f"{n}", fontsize=size, color=st.MUTED, va="top", ha="right")
        ax.text(tx0, y, "\n".join(lines), fontsize=size, color=st.INK, va="top", linespacing=1.28)
        ax.text(kx, y, "\n".join(keys), fontsize=msize, color=st.MUTED, va="top", family=MONO, linespacing=1.2)
        y -= max(len(lines) * line_h(size), len(keys) * line_h(msize, 1.2)) + 1.6
    st.save(fig, output, "fig5_report_fields")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=REPO / "docs/manuscript/figures")
    fig5(p.parse_args().output)
