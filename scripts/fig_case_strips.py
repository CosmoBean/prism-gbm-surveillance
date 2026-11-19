"""Case strips: what each score says at each visit, modelled on Tak et al. 2025 (NEJM AI) Figure 4.

Four MU-Glioma-Post patients, one strip each: the T1c slice with most enhancement at every labelled scan, the weeks
after the end of radiotherapy and the interval between scans, and under each scan the clinical-history, imaging and
combined scores, the 80% conformal set of the combined score and the agreement statement, all read from the system
records. The scores rank scans; they are not probabilities for this patient. No diagnosis wording.

Patient selection (written rule, applied in pick_patients): among MU grade-4 patients with at least three scans in the
intended-use evaluation set, in patient-ID order, the first
  A. with progression, the models agreeing at every scan;
  B. without progression, the models agreeing at every scan;
  C. with progression, the models disagreeing at the progression scan;
  D. without progression, the models disagreeing at one or more scans.

Data
  - Records: outputs/results/analyses/system/records_mu.jsonl (prism/analyses/system.py, write_records). MU scores
    are out-of-fold (repeat 0 of the 5 x 5 cross validation); the patient was not in training. Key "timeline" is the
    clinical-history model.
  - Labels: records_mu_EVALUATION_ONLY.csv (label, eval_intended_use), joined by record_id; never in a record.
  - Images, masks and dates: data/mu-glioma-post through fig1_prism (scan_slice, scan_days); IDH and MGMT from
    outputs/data/mu_cohort.csv.

Example paper: docs/literature/examples/tak2025_nejmai.md (local, gitignored); notes in tak2025_NOTES.md.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Rectangle

import figure_style as st
from fig1_prism import CONTOUR, load_clinical, scan_days, scan_slice, show_scan

REPO = Path(__file__).resolve().parents[1]
RECORDS = REPO / "outputs" / "results" / "analyses" / "system"
COHORT = REPO / "outputs" / "data" / "mu_cohort.csv"
SCORES = [("timeline", "Clinical history", st.HIST), ("images", "Imaging", st.IMG), ("combined", "Combined", st.COMB)]
RULES = {"A": "progression; models agree at every scan", "B": "no progression; models agree at every scan",
         "C": "progression; models disagree at the progression scan",
         "D": "no progression; models disagree at one or more scans"}

W = 180.0                                  # drawing units (about 1 mm each)
LEFT, PITCH, IW = 21.0, 31.8, 20.0         # row-label column, scan pitch, image width
CELL = 3.3                                 # height of one score cell
ROW_H = 5.0 + 3.6 + IW + 2.6 + 5 * CELL + 4.0
LEGEND_H = 15.0


def load_records() -> pd.DataFrame:
    with open(RECORDS / "records_mu.jsonl") as f:
        recs = [json.loads(line) for line in f]
    for r in recs:
        assert r["provenance"]["scores"].startswith("out-of-fold"), r["record_id"]
        assert r["flags"]["pathways_disagree"] == (not r["card"]["agreement"]["agree"]), r["record_id"]
    df = pd.DataFrame([{"record_id": r["record_id"], "scan_id": r["scan_id"], "patient_id": r["patient_id"],
                        **r["scores"], "set80": r["conformal"]["alpha_0.2"]["combined"],
                        "agree": r["card"]["agreement"]["agree"]} for r in recs])
    lab = pd.read_csv(RECORDS / "records_mu_EVALUATION_ONLY.csv")[["record_id", "label", "eval_intended_use"]]
    df = df.merge(lab, on="record_id", validate="one_to_one")
    df = df[df.eval_intended_use & df.label.notna()].copy()
    df["tp"] = df.scan_id.str.extract(r"Timepoint_(\d+)$")[0].astype(int)
    return df.sort_values(["patient_id", "tp"])


def pick_patients(df: pd.DataFrame) -> dict[str, str]:
    """The written selection rule of the docstring: {case letter: patient_id}."""
    picks = {}
    for pid, g in df.groupby("patient_id", sort=True):
        if len(g) < 3:
            continue
        prog = bool(g.label.max() == 1)
        all_agree = bool(g.agree.all())
        tests = {"A": prog and all_agree, "B": not prog and all_agree,
                 "C": prog and not bool(g[g.label == 1].agree.iloc[0]), "D": not prog and not all_agree}
        for k, ok in tests.items():
            if ok and k not in picks:
                picks[k] = pid
    assert set(picks) == set(RULES), picks
    return dict(sorted(picks.items()))


def draw(output: Path) -> dict[str, str]:
    df = load_records()
    picks = pick_patients(df)
    clin = load_clinical().set_index("Patient_ID")
    cohort = pd.read_csv(COHORT).drop_duplicates("patient_id").set_index("patient_id")

    H = len(picks) * ROW_H + LEGEND_H
    fig = plt.figure(figsize=(st.WIDTH, st.WIDTH * H / W))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, W), ylim=(0, H)); ax.axis("off")

    def text(x, y, s, size=5.8, colour=st.INK, **kw):
        kw.setdefault("ha", "left"); kw.setdefault("va", "top")
        return ax.text(x, y, s, fontsize=size, color=colour, linespacing=1.3, **kw)

    for row, (case, pid) in enumerate(picks.items()):
        g = df[df.patient_id == pid]
        c = clin.loc[pid]
        days = scan_days(c)
        rt_end = float(c["Number of days from Diagnosis to Radiation Therapy end date"])
        top = H - row * ROW_H
        # header strip (after Tak: one line of patient facts)
        ax.add_patch(FancyBboxPatch((0.6, top - 4.4), W - 1.2, 3.8, boxstyle="round,pad=0,rounding_size=0.8",
                                    fc=st.PANEL, ec="none", zorder=1))
        prog = bool(g.label.max() == 1)
        text(1.8, top - 1.2, f"{case}   {pid}", size=6.4, weight="bold")
        info = (f"grade 4  |  IDH {cohort.loc[pid, 'idh']}  |  MGMT {cohort.loc[pid, 'mgmt']}  |  "
                f"progression documented: {'yes' if prog else 'no'}")
        text(31.0, top - 1.35, info, size=5.8)
        text(W - 1.8, top - 1.35, RULES[case], size=5.6, colour=st.MUTED, ha="right", style="italic")

        y_lab = top - 5.6                       # scan label line
        iy1 = y_lab - 3.6                       # image top
        iy0 = iy1 - IW
        y_wk = iy0 - 0.6
        cy = y_wk - 2.6                         # top of the first score cell
        names = [s[1] for s in SCORES] + ["80% set, combined", "Models"]
        for k, name in enumerate(names):
            text(LEFT - 1.4, cy - k * CELL - CELL / 2, name, size=5.4, ha="right", va="center",
                 colour=SCORES[k][2] if k < 3 else st.INK, weight="bold" if k < 3 else "normal")

        prev_weeks = None
        for j, (_, s) in enumerate(g.iterrows()):
            x = LEFT + j * PITCH + (PITCH - IW) / 2
            day = days[s.tp]
            weeks = (day - rt_end) / 7
            sl = scan_slice(pid, s.tp)
            iax = fig.add_axes([x / W, iy0 / H, IW / W, IW / H])
            show_scan(iax, sl)
            is_prog = s.label == 1
            text(x + IW / 2, y_lab, "Progression" if is_prog else "No progression", size=5.8, ha="center",
                 weight="bold" if is_prog else "normal")
            early = 0 <= weeks <= 12
            if early:
                ax.add_patch(Rectangle((x, y_wk - 2.3), IW, 2.3, fc=st.tint(st.HIST, 0.75), ec="none", zorder=1))
            text(x + IW / 2, y_wk, f"{weeks:.1f} wk after RT", size=5.4, ha="center", zorder=3)
            if prev_weeks is not None:
                gx0, gx1 = x - (PITCH - IW) + 0.8, x - 0.8
                ax.annotate("", xy=(gx1, iy0 + IW / 2), xytext=(gx0, iy0 + IW / 2),
                            arrowprops=dict(arrowstyle="-|>", color=st.MUTED, lw=0.6, mutation_scale=5))
                text((gx0 + gx1) / 2, iy0 + IW / 2 + 1.0, f"{weeks - prev_weeks:.0f} wk", size=5.4,
                     colour=st.MUTED, ha="center", va="bottom")
            prev_weeks = weeks
            for k, (key, _, colour) in enumerate(SCORES):
                v = float(s[key])
                amount = 0.92 - 0.85 * v
                ax.add_patch(Rectangle((x, cy - (k + 1) * CELL + 0.25), IW, CELL - 0.5,
                                       fc=st.tint(colour, amount), ec="none", zorder=2))
                text(x + IW / 2, cy - k * CELL - CELL / 2, f"{v:.2f}", size=5.6, ha="center", va="center",
                     colour="white" if amount < 0.45 else st.INK, zorder=3)
            text(x + IW / 2, cy - 3 * CELL - CELL / 2, s.set80, size=5.6,
                 ha="center", va="center")
            text(x + IW / 2, cy - 4 * CELL - CELL / 2, "agree" if s.agree else "disagree", size=5.6, ha="center",
                 va="center", colour=st.MUTED if s.agree else st.INK, weight="normal" if s.agree else "bold")
        ax.plot([0.6, W - 0.6], [top - ROW_H + 1.0, top - ROW_H + 1.0], color=st.RULE, lw=0.5)

    # legend: one ramp per score, the shading, the outline
    ly = LEGEND_H - 3.0
    x = LEFT
    for key, name, colour in SCORES:
        for i in range(10):
            v = (i + 0.5) / 10
            ax.add_patch(Rectangle((x + i * 2.2, ly - 3.0), 2.2, 3.0, fc=st.tint(colour, 0.92 - 0.85 * v), ec="none"))
        text(x, ly - 3.6, "0", size=5.2, colour=st.MUTED)
        text(x + 22.0, ly - 3.6, "1", size=5.2, colour=st.MUTED, ha="right")
        text(x + 23.5, ly - 1.5, f"{name.lower()}\nscore", size=5.4, va="center")
        x += 44.0
    ax.add_patch(Rectangle((x, ly - 2.6), 6.0, 2.3, fc=st.tint(st.HIST, 0.75), ec="none"))
    text(x + 7.2, ly - 1.5, "first 12 weeks\nafter RT", size=5.4, va="center")
    ax.plot([LEFT, LEFT + 4.0], [ly - 8.6, ly - 8.6], color=CONTOUR, lw=1.2)
    text(LEFT + 5.2, ly - 7.6, "enhancing outline (released mask); T1c slice with most enhancement (without enhancement, most lesion).  "
         "Agree: both models on the same side of their cohort medians.", size=5.4, colour=st.MUTED)

    st.save(fig, output, "fig_case_strips")
    return picks


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=REPO / "docs/manuscript/figures")
    a = p.parse_args()
    print(draw(a.output))
