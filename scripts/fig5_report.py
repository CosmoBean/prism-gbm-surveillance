"""Figure 5: the report PRISM writes, and the check.

(a) One real report for a held-out scan: MU-Glioma-Post PatientID_0029, Timepoint 4 (strip C of the case-strip figure),
written by the local language model (report v3.2, Qwen3.8-27B, greedy) and accepted by the checker. Laid out as a
report page in the order of the BT-RADS follow-up template (docs/review/REPORT_FORMAT_RESEARCH.md): header with the
comparison and the flags; the attached segmentation slices beside the measurement table; the three scores against
their cohort medians with their conformal sets; the reliability card; the language model's sentences verbatim,
numbered, with the record fields each cites; the fixed limitations. Every value is read from the record's facts
(prism.report.facts_v3_2) and the model output; nothing is typed in here. The images use the report's own segmentation
rules (prism.report.seg_figure: slice choice, masks, previous scan at the same atlas slice).

(b) Reports passing the checker for seven local models (NUMBERS.md 7; v3.1 prompt, no per-model tuning).

    cd scripts && ../.venv/bin/python fig5_report.py
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle

import figure_style as st

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from prism.report import seg_figure as SEG  # noqa: E402
from prism.report.facts_v3_2 import check_v3_2, facts_v3_2  # noqa: E402
from prism.report.sections_v3 import LIMITATIONS_V3_1  # noqa: E402

RUN = REPO / "outputs" / "results" / "analyses" / "report_v3_2"
RECORD = "mu|grade4|PatientID_0029_Timepoint_4"
PREVIOUS = "PatientID_0029_Timepoint_3"
MONO = "DejaVu Sans Mono"
SECTION = {"scan": "Scan", "models": "Models", "combined": "Combined", "trust": "Trust"}
MODELS = [("clinical_history", "Clinical history", st.HIST), ("imaging", "Imaging", st.IMG),
          ("combined", "Combined", st.COMB)]
ET_C, SNFH_C = "#F2C14E", "#FFFFFF"
SET_SYMBOL = {"both outcomes": "{0, 1}", "progression only": "{1}", "no progression only": "{0}"}

W = 180.0                       # drawing units (about 1 mm)
HB = 25.0                       # panel (b) height


def load():
    rec = next(json.loads(l) for l in open(RUN / "records" / "eval.jsonl") if json.loads(l)["record_id"] == RECORD)
    out = next(json.loads(l) for l in open(RUN / "llm" / "outputs_eval_v3_2.jsonl")
               if json.loads(l)["id"] == f"eval|{RECORD}")
    claims = json.loads(out["text"])["sentences"]
    F = facts_v3_2(rec)
    res = check_v3_2(claims, rec)
    assert res["pass"], res                    # the checker accepted this report
    for c in claims:
        assert all(k in F for k in c["fields"]), c
    return F, claims


def slices():
    """This scan (T1c, FLAIR) and the previous scan (FLAIR) at the report's own slice, cropped to the brain."""
    cur = SEG.load_scan("mu", RECORD.split("|")[-1])
    prev = SEG.load_scan("mu", PREVIOUS)
    brain = cur.t1c > 0
    k, rule, _ = SEG.choose_slice(cur.comp, brain)
    out = []
    for scan, seq, title in [(cur, "t1c", "This scan, T1c"), (cur, "flair", "This scan, FLAIR"),
                             (prev, "flair", "Previous scan, FLAIR")]:
        img = (scan.t1c if seq == "t1c" else scan.flair)[:, :, k]
        b = (scan.t1c > 0)[:, :, k]
        lo, hi = np.percentile(img[b], [0.5, 99.5])
        r, c = np.where(b)
        sl = (slice(r.min(), r.max() + 1), slice(c.min(), c.max() + 1))
        disp = lambda a: SEG.to_display(a[sl])
        out.append(dict(img=disp(np.clip((img - lo) / (hi - lo), 0, 1)), et=disp(scan.comp["et"][:, :, k]),
                        snfh=disp(scan.comp["snfh"][:, :, k]), title=title))
    return out, rule


def fig5(output: Path) -> None:
    F, claims = load()
    imgs, rule = slices()
    ha = draw(None, F, claims, imgs, rule, 300.0)          # dry run: height panel (a) needs
    draw(output, F, claims, imgs, rule, ha)


def key_lines(keys: list[str], width: int) -> list[str]:
    """Comma-separated keys wrapped at width; a key longer than width breaks after an underscore."""
    parts = []
    for k in keys:
        while len(k) > width:
            cut = k.rfind("_", 0, width) + 1 or width
            parts.append(k[:cut]); k = "  " + k[cut:]
        parts.append(k)
    lines, cur = [], ""
    for k in parts:
        add = k if not cur else cur + ", " + k
        if len(add) <= width or not cur:
            cur = add
        else:
            lines.append(cur + ","); cur = k
    return lines + [cur]


def draw(output, F, claims, imgs, rule, HA) -> float:
    H = HA + HB
    fig = plt.figure(figsize=(st.WIDTH, st.WIDTH * H / W))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, W), ylim=(0, H)); ax.axis("off")

    def text(x, y, s, size=6.0, colour=st.INK, **kw):
        kw.setdefault("ha", "left"); kw.setdefault("va", "top")
        kw.setdefault("linespacing", 1.3)
        return ax.text(x, y, s, fontsize=size, color=colour, **kw)

    def rule_line(y, x0=6.0, x1=W - 6.0, colour=st.RULE, lw=0.5):
        ax.plot([x0, x1], [y, y], color=colour, lw=lw)

    def head(y, s):
        text(6.0, y, s.upper(), size=6.0, colour=st.NAVY, weight="bold")
        return y - 4.2

    st.panel_header(fig, 0.998, "a", "A report PRISM wrote for a held-out scan (MU-Glioma-Post)")
    top = H - 6.0

    # ---------------------------------------------------------------- A header: scan, comparison, flags
    y = top - 3.0
    text(6.0, y, "PRISM follow-up MRI report", size=8.5, colour=st.NAVY, weight="bold")
    text(W - 6.0, y - 0.6, f"facts {F['system.facts_version']}  ·  checker: accepted", size=5.8, colour=st.MUTED,
         ha="right")
    y -= 5.4
    text(6.0, y, f"{F['scan.phase'][0].upper()}{F['scan.phase'][1:]}  ·  compared with the previous scan "
                 f"{F['scan.days_since_previous']} days earlier", size=5.8, colour=st.MUTED)
    y -= 3.3
    text(6.0, y, F["system.cohort"][0].upper() + F["system.cohort"][1:], size=5.8, colour=st.MUTED)
    y -= 4.4
    x = 6.0
    text(x, y - 0.4, "Flags", size=5.8, weight="bold")
    x += 9.0
    for f in ("models_disagree", "out_of_range", "card_tier", "conformal_both"):
        on = F[f"flags.{f}.active"]
        name = F[f"flags.{f}.name"]
        w = 1.25 * len(name) + 4.0
        ax.add_patch(FancyBboxPatch((x, y - 3.4), w, 3.4, boxstyle="round,pad=0,rounding_size=1.2",
                                    fc=st.NAVY if on else "white", ec=st.NAVY if on else st.RULE, lw=0.6))
        text(x + w / 2, y - 1.7, name, size=5.4, colour="white" if on else st.MUTED, ha="center", va="center")
        x += w + 2.0
    text(x + 1.0, y - 0.6, "filled: raised", size=5.2, colour=st.MUTED)
    y -= 6.6
    rule_line(y, lw=0.7, colour=st.NAVY)

    # ---------------------------------------------------------------- B images + measurements
    y -= 3.0
    y = head(y, "1  What the scan shows")
    iw, gap = 21.0, 1.6
    for i, im in enumerate(imgs):
        x0 = 6.0 + i * (iw + gap)
        iax = fig.add_axes([x0 / W, (y - iw) / H, iw / W, iw / H])
        iax.imshow(im["img"], cmap="gray", vmin=0, vmax=1, interpolation="bilinear", aspect="auto")
        if im["et"].any():
            iax.contour(im["et"].astype(float), levels=[0.5], colors=[ET_C], linewidths=0.6)
        if "FLAIR" in im["title"] and im["snfh"].any():
            iax.contour(im["snfh"].astype(float), levels=[0.5], colors=[SNFH_C], linewidths=0.5,
                        linestyles=[(0, (2, 1.4))])
        iax.set_xticks([]); iax.set_yticks([])
        for sp in iax.spines.values():
            sp.set_visible(False)
        iax.text(0.04, 0.96, "R", transform=iax.transAxes, color="white", fontsize=5, va="top")
        iax.text(0.96, 0.96, "L", transform=iax.transAxes, color="white", fontsize=5, va="top", ha="right")
        text(x0, y - iw - 0.8, im["title"], size=5.4)
    text(6.0, y - iw - 3.6, f"Slice: {rule}; dashed, FLAIR hyperintensity outline. "
                            "Attached to the report; the language model sees no image.", size=5.0, colour=st.MUTED)
    # measurement table
    tx = 6.0 + 3 * (iw + gap) + 3.0
    cols = [tx, tx + 29.0, tx + 44.0, tx + 72.0]
    text(cols[0], y, "Indicative volumes (cc)", size=5.6, colour=st.MUTED)
    for c, h in zip(cols[1:], ["This scan", f"vs previous ({F['scan.days_since_previous']} d)", "vs smallest earlier"]):
        text(c, y, h, size=5.6, colour=st.MUTED)
    rule_line(y - 3.4, tx, W - 6.0)

    def change(k):
        if f"meas.{k}_change_since_previous_cc" not in F:
            return "–"
        s = f"{F[f'meas.{k}_change_since_previous_cc']:+.1f}"
        if f"meas.{k}_change_since_previous_percent" in F:
            s += f" ({F[f'meas.{k}_change_since_previous_percent']:+d}%)"
        return s
    em = (f"{F['meas.enhancing_change_since_earlier_minimum_cc']:+.1f} (min {F['meas.enhancing_earlier_minimum_cc']:.1f})"
          if "meas.enhancing_change_since_earlier_minimum_cc" in F else "–")
    rows = [("Enhancing tumour", F["meas.enhancing_cc"], change("enhancing"), em),
            ("FLAIR hyperintensity", F["meas.flair_hyperintensity_cc"], change("flair_hyperintensity"), "–"),
            ("Necrosis", F.get("meas.necrosis_cc"), "–", "–"),
            ("Resection cavity", F.get("meas.cavity_cc"), "–", "–")]
    ry = y - 4.6
    for name, v, d1, d2 in rows:
        text(cols[0], ry, name, size=6.0)
        text(cols[1] + 10.0, ry, "–" if v is None else f"{v:.1f}", size=6.0, ha="right", weight="bold")
        text(cols[2], ry, d1, size=6.0)
        text(cols[3], ry, d2, size=6.0)
        ry -= 3.7
    rule_line(ry + 0.8, tx, W - 6.0)
    text(tx, ry - 0.2, F["meas.label"][0].upper() + F["meas.label"][1:] + ".", size=5.2, colour=st.MUTED)
    y -= iw + 6.0
    rule_line(y)

    # ---------------------------------------------------------------- C scores against their medians
    y -= 2.4
    y = head(y, "2  The two models and  3  the combined score")
    track0, track1 = 70.0, 118.0
    xs = lambda v: track0 + (track1 - track0) * v
    y -= 1.2
    text(track0, y + 0.6, "0", size=5.2, colour=st.MUTED, ha="center", va="bottom")
    text(track1, y + 0.6, "1", size=5.2, colour=st.MUTED, ha="center", va="bottom")
    for c, h in [(124.0, "Score"), (137.0, "Side of median"), (158.0, "80% set"), (168.0, "90% set")]:
        text(c, y + 0.6, h, size=5.4, colour=st.MUTED, va="bottom")
    y -= 1.6
    for key, name, colour in MODELS:
        cy = y - 1.6
        text(6.0, cy, name, size=6.2, colour=colour, weight="bold", va="center")
        based = F[f"model.{key}.based_on"].split(" (")[0].split(";")[0]
        text(6.0, cy - 2.6, based, size=4.9, colour=st.MUTED, va="center")
        ax.plot([track0, track1], [cy, cy], color=st.RULE, lw=0.8, solid_capstyle="round")
        med = F.get(f"model.{key}.cohort_median")
        if med is not None:
            ax.plot([xs(med)] * 2, [cy - 1.5, cy + 1.5], color=st.CLIN, lw=0.9)
        ax.add_patch(plt.Circle((xs(F[f"model.{key}.score"]), cy), 1.1, fc=colour, ec="white", lw=0.4, zorder=4))
        text(124.0, cy, f"{F[f'model.{key}.score']:.2f}", size=6.2, va="center", weight="bold")
        text(137.0, cy, F.get(f"model.{key}.side", "–") if med is not None else "–", size=6.0, va="center")
        for c, lvl in [(158.0, 80), (168.0, 90)]:
            text(c, cy, SET_SYMBOL[F[f"conformal.{key}.{lvl}.set"]], size=6.0, va="center", family=MONO)
        y -= 6.0
    text(track0, y + 1.6, "grey tick: median of the model's scores in the MU-Glioma-Post evaluation scans; "
         "sets: {0} no progression, {1} progression", size=5.0, colour=st.MUTED)
    y -= 1.4
    rule_line(y)

    # ---------------------------------------------------------------- D reliability card
    y -= 2.4
    y = head(y, "4  How much to trust this here")
    text(6.0, y, "Situation", size=5.8, colour=st.MUTED)
    text(24.0, y, F["card.situation"], size=6.0)
    y -= 4.2
    text(6.0, y - 0.4, "Card tier", size=5.8, colour=st.MUTED)
    x = 24.0
    for tier in ("tested", "few cases", "not tested"):
        on = F["card.tier"] == tier
        ax.add_patch(Rectangle((x, y - 3.2), 17.0, 3.2, fc=st.NAVY if on else st.PANEL, ec="white", lw=0.8))
        text(x + 8.5, y - 1.6, tier, size=5.6, colour="white" if on else st.MUTED, ha="center", va="center",
             weight="bold" if on else "normal")
        x += 17.0
    text(x + 3.0, y - 0.3, f"{F['card.n_progression']} progression and {F['card.n_no_progression']} "
                           "non-progression scans in this situation at MU-Glioma-Post", size=5.8)
    y -= 5.4
    rule_line(y)

    # ---------------------------------------------------------------- E the language model's text
    y -= 2.4
    text(6.0, y, "REPORT TEXT", size=6.0, colour=st.NAVY, weight="bold")
    text(28.0, y, "written by the local language model from the record alone; verbatim", size=5.4, colour=st.MUTED)
    text(123.0, y, "Record fields cited", size=5.4, colour=st.MUTED)
    y -= 4.4
    tw, kw = 102, 58                                  # wrap widths (characters)
    last = None
    for n, c in enumerate(claims, 1):
        if c["section"] != last:
            text(6.0, y, SECTION[c["section"]], size=5.6, colour=st.NAVY, weight="bold")
            last = c["section"]
        lines = textwrap.wrap(c["text"], tw)
        keys = key_lines(c["fields"], kw)
        text(19.0, y, f"{n}", size=5.4, colour=st.MUTED, ha="right")
        text(21.0, y, "\n".join(lines), size=5.6)
        text(123.0, y + 0.1, "\n".join(keys), size=4.2, colour=st.MUTED, family=MONO, linespacing=1.25)
        y -= max(2.45 * len(lines), 1.9 * len(keys)) + 0.9
    rule_line(y + 0.4)

    # ---------------------------------------------------------------- F limitations (fixed text)
    y -= 1.6
    lim = textwrap.wrap("Limitations (fixed text): " + LIMITATIONS_V3_1, 165)
    text(6.0, y, "\n".join(lim), size=5.1, colour=st.MUTED, style="italic")
    y -= 2.25 * len(lim) + 2.0
    used = top - y + 6.0                                # height panel (a) needs
    if output is None:
        plt.close(fig)
        return used
    ax.add_patch(FancyBboxPatch((2.0, y), W - 4.0, top - y, boxstyle="round,pad=0,rounding_size=1.5",
                                fc="none", ec=st.NAVY, lw=0.7, zorder=0))

    # ================================================================ (b) model-size ladder
    st.panel_header(fig, (HB - 0.5) / H, "b", "Reports passing the checker, of 406, by local language model")
    bx = fig.add_axes([0.20, 1.5 / H, 0.60, (HB - 6.5) / H])
    ladder = [("Qwen 2B", 3.6, 21, False), ("Qwen 4B", 8.0, 306, False), ("Gemma E4B", 14.5, 117, False),
              ("Qwen 9B", 16.8, 368, False), ("Qwen 27B (used)", 50.2, 406, True),
              ("Gemma 31B", 57.9, 406, True), ("Qwen 35B-A3B", 64.7, 389, False)]
    dark, light = st.NAVY, st.tint(st.NAVY, 0.72)
    for i, (name, gib, k, ok) in enumerate(ladder):
        yy = len(ladder) - 1 - i
        bx.barh(yy, k, color=dark if ok else light, height=0.62)
        bx.text(-6, yy, name, va="center", ha="right", fontsize=6.0, color=st.INK, weight="bold" if ok else "normal")
        bx.text(k + 4, yy, f"{k}", va="center", ha="left", fontsize=5.8, color=st.INK)
        bx.text(470, yy, f"{gib:.1f} GiB", va="center", ha="right", fontsize=5.6, color=st.MUTED)
    bx.set(yticks=[], xlim=(0, 470), ylim=(-0.6, len(ladder) - 0.4))
    bx.set_xticks([])
    for sp in ("left", "bottom"):
        bx.spines[sp].set_visible(False)
    bx.text(1.02, 0.5, "Dark: ≥ 95% passing\nin every cohort.\nSame prompt\nfor every model.",
            transform=bx.transAxes, fontsize=5.6, va="center", color=st.MUTED, linespacing=1.3)
    st.save(fig, output, "fig5_report")
    return HA


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=REPO / "docs/manuscript/figures")
    fig5(p.parse_args().output)
