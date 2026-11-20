"""Cohort characteristics, modelled on Tak et al. 2025 (NEJM AI) Figure 2: how the evaluation scans differ between
cohorts before any model is shown.

One panel per cohort (a MU, b LUMIERE, c UCSF), headed by its scans, patients and share of progression scans, as in
Figure 2. Left: when each evaluation scan was taken, split by label: weeks after the end of radiotherapy at MU (first
12 weeks shaded); LUMIERE and UCSF have no radiotherapy end dates, so weeks after surgery (UCSF: after the first
surgery, which the release counts as the diagnosis). The time zero is named on each axis. Right: weeks since the
patient's previous scan. Both columns share one axis across cohorts; the few scans beyond it are drawn at the edge
as arrowheads and counted.

Evaluation sets as in the paper: MU, the grade-4 intended-use scans (146 scans, 80 patients); LUMIERE, all 178
labelled scans of 79 patients; UCSF-ALPTDG, the labelled grade-4 second scans (one per patient). Times and intervals come from the system records
(outputs/results/analyses/system/records_<cohort>.jsonl: measurements.previous.days_before) and the dates in the
released data (MU clinical workbook, via fig1_prism; LUMIERE week in the scan name, weeks after surgery; UCSF
days_from_diagnosis_to_mri in outputs/data/ucsf/scans.csv). Labels from records_<cohort>_EVALUATION_ONLY.csv.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import figure_style as st
from fig1_prism import load_clinical, scan_days

REPO = Path(__file__).resolve().parents[1]
RECORDS = REPO / "outputs" / "results" / "analyses" / "system"
PROG, NOPROG = st.INK, st.MUTED       # progression filled dark, no progression open grey (shape and fill, not hue)


def evaluation_scans(cohort: str) -> pd.DataFrame:
    with open(RECORDS / f"records_{cohort}.jsonl") as f:
        recs = [json.loads(line) for line in f]
    df = pd.DataFrame([{"record_id": r["record_id"], "scan_id": r["scan_id"], "patient_id": r["patient_id"],
                        "interval_days": (r["measurements"].get("previous") or {}).get("days_before")}
                       for r in recs])
    lab = pd.read_csv(RECORDS / f"records_{cohort}_EVALUATION_ONLY.csv")
    df = df.merge(lab[["record_id", "label"] + [c for c in lab.columns if c.startswith("eval_")]], on="record_id",
                  validate="one_to_one")
    keep = {"mu": "eval_intended_use", "lumiere": "eval_all", "ucsf": "eval_scan2_pm30"}[cohort]
    keep = df[keep].astype(bool)
    df = df[keep & df.label.notna()].copy()
    if cohort == "mu":
        clin = load_clinical().set_index("Patient_ID")
        def weeks(row):
            c = clin.loc[row.patient_id]
            tp = int(row.scan_id.rsplit("_", 1)[1])
            return (scan_days(c)[tp] - float(c["Number of days from Diagnosis to Radiation Therapy end date"])) / 7
        df["weeks"] = df.apply(weeks, axis=1)
    elif cohort == "ucsf":
        sc = pd.read_csv(REPO / "outputs" / "data" / "ucsf" / "scans.csv").set_index("scan_id")
        df["weeks"] = sc.days_from_diagnosis_to_mri.reindex(df.scan_id).to_numpy(float) / 7
    else:
        df["weeks"] = df.scan_id.str.extract(r"week-(\d+)")[0].astype(float)
    return df


def strip(ax, df, col, rng, xmax):
    """Two rows of jittered dots (progression above), each row's median as a short bar; values beyond xmax are drawn
    at the edge as arrowheads and counted."""
    for y, lab, colour, face in [(1, 1, PROG, PROG), (0, 0, NOPROG, "white")]:
        v = df.loc[df.label == lab, col].dropna().to_numpy()
        inside, over = v[v <= xmax], v[v > xmax]
        yy = y + rng.uniform(-0.22, 0.22, len(inside))
        ax.scatter(inside, yy, s=7, marker="o", facecolor=face, edgecolor=colour, linewidth=0.5, zorder=3)
        if len(over):
            ax.scatter([xmax * 1.012], [y], s=14, marker=">", facecolor=face, edgecolor=colour, linewidth=0.5,
                       zorder=3, clip_on=False)
            ax.text(xmax * 1.03, y, f"+{len(over)}", fontsize=5.6, color=colour, va="center", ha="left")
        if len(v):
            m = float(np.median(v))
            ax.plot([m, m], [y - 0.36, y + 0.36], color=colour, lw=1.4, zorder=4, solid_capstyle="butt")
    ax.set_yticks([0, 1], ["No progression", "Progression"])
    ax.set_ylim(-0.6, 1.6)
    ax.set_xlim(0, xmax)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)


def draw(output: Path) -> dict:
    cohorts = [("mu", "MU-Glioma-Post", "weeks after the end of radiotherapy"),
               ("lumiere", "LUMIERE", "weeks after surgery (no radiotherapy dates recorded)"),
               ("ucsf", "UCSF-ALPTDG", "weeks after the first surgery (no radiotherapy end dates)")]
    T_MAX, I_MAX = 240, 60
    rng = np.random.default_rng(20261119)
    H = 4.65
    fig = plt.figure(figsize=(st.WIDTH, H))
    summary = {}
    row_h, head, gap = 0.80 / H, 0.20 / H, 0.50 / H
    y = 1 - 0.06 / H
    for i, (key, name, tlabel) in enumerate(cohorts):
        df = evaluation_scans(key)
        n, npat, npos = len(df), df.patient_id.nunique(), int((df.label == 1).sum())
        summary[key] = dict(scans=n, patients=npat, progression=npos,
                            median_weeks={int(k): round(float(v), 1) for k, v in df.groupby("label").weeks.median().items()},
                            median_interval_weeks={int(k): round(float(v) / 7, 1) for k, v in
                                                   df.groupby("label").interval_days.median().items()})
        st.panel_header(fig, y, "abc"[i], f"{name}  \u00b7  {n} scans, {npat} patients, {npos} with progression "
                                          f"({100 * npos / n:.0f}%)")
        y0 = y - head - row_h
        ax = fig.add_axes([0.13, y0, 0.50, row_h])
        if key == "mu":
            ax.axvspan(0, 12, color=st.tint(st.HIST, 0.75), lw=0, zorder=1)
            ax.text(13.5, 1.45, "first 12 weeks", fontsize=5.6, color=st.HIST, ha="left", va="center")
        strip(ax, df, "weeks", rng, T_MAX)
        ax.set_xlabel(tlabel, labelpad=1)
        ax2 = fig.add_axes([0.70, y0, 0.26, row_h])
        df["interval_weeks"] = df.interval_days / 7
        strip(ax2, df, "interval_weeks", rng, I_MAX)
        ax2.set_yticklabels([])
        ax2.set_xlabel("weeks since the previous scan", labelpad=1)
        y = y0 - gap
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], ls="", marker="o", ms=3.5, mfc=PROG, mec=PROG, label="progression scan"),
               Line2D([], [], ls="", marker="o", ms=3.5, mfc="white", mec=NOPROG, mew=0.6, label="no-progression scan"),
               Line2D([], [], ls="", marker="|", ms=7, mew=1.4, color=st.INK, label="median"),
               Line2D([], [], ls="", marker=">", ms=4, mfc="white", mec=st.INK, mew=0.6,
                      label="beyond the axis (count)")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=4, fontsize=6.3)
    st.save(fig, output, "fig_cohorts")
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=REPO / "docs/manuscript/figures")
    a = p.parse_args()
    print(json.dumps(draw(a.output), indent=1))
