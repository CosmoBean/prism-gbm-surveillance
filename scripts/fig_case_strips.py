"""Case strips: what each score says at each visit, modelled on Tak et al. 2025 (NEJM AI) Figure 4.

Four MU-Glioma-Post patients, one strip each: the same axial T1c slice at every labelled scan, the weeks after the end
of radiotherapy and the interval between scans, and under each scan the clinical-history, imaging and combined scores,
the 80% conformal set of the combined score (in words) and the agreement statement, all read from the system records.
The scores rank scans; they are not probabilities for this patient. No diagnosis wording.

Slice (one per patient): MU scans are released on one atlas grid (240 x 240 x 155, 1 mm), so one axial index shows the
same anatomy at every visit. The index is the slice with most enhancing tumour in the released masks, summed over the
patient's evaluation scans; with no enhancement at any scan, most lesion. One crop per patient (the brain on that slice
at every visit) and one arrow at the lesion centre on that slice, placed alike at every visit.

Patient selection (written rule, applied in pick_patients): among MU grade-4 patients with at least three scans in the
intended-use evaluation set, in patient-ID order, the first
  A. with progression, the models agreeing at every scan;
  B. without progression, the models agreeing at every scan;
  C. with progression, the models disagreeing at the progression scan;
  D. without progression, the models disagreeing at one or more scans.
The strips are labelled Patient 1-4 in this order.

Data
  - Records: outputs/results/analyses/system/records_mu.jsonl (prism/analyses/system.py, write_records). MU scores
    are out-of-fold (repeat 0 of the 5 x 5 cross validation); the patient was not in training. Key "timeline" is the
    clinical-history model.
  - Labels: records_mu_EVALUATION_ONLY.csv (label, eval_intended_use), joined by record_id; never in a record.
  - Images, masks and dates: data/mu-glioma-post (load_clinical, scan_days from fig1_prism); PRISM's segmentation
    from outputs/features/seg_swin/mu; IDH and MGMT from outputs/data/mu_cohort.csv.

Example paper: docs/literature/examples/tak2025_nejmai.md (local, gitignored); notes in tak2025_NOTES.md.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

import figure_style as st
from fig1_prism import CONTOUR, ET_LABEL, MU, SEG, load_clinical, scan_days

RELEASED = "#7FD3F0"  # the mask released with the cohort, for comparison

REPO = Path(__file__).resolve().parents[1]
RECORDS = REPO / "outputs" / "results" / "analyses" / "system"
COHORT = REPO / "outputs" / "data" / "mu_cohort.csv"
SCORES = [("timeline", "Clinical history", st.HIST), ("images", "Imaging", st.IMG), ("combined", "Combined", st.COMB)]
SET_WORDS = {"{0}": "no progression", "{1}": "progression", "{0, 1}": "both", "{}": "neither"}
# Layout (drawing units, about 1 mm each). Row 1: patient 1; row 2: patients 2 and 3 side by side; row 3: patient 4.
LAYOUT = [["A"], ["B", "C"], ["D"]]

W = 180.0
LEFT = 21.0                                 # row-label column
GAP = 3.0                                   # between two strips sharing a row
IW = 20.0                                   # image width
CELL = 3.3                                  # height of one score cell
ROW_H = 5.0 + 3.6 + IW + 2.6 + 5 * CELL + 4.0
LEGEND_H = 9.0


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
    assert set(picks) == {"A", "B", "C", "D"}, picks
    return dict(sorted(picks.items()))


def patient_slices(pid: str, tps: list[int]) -> tuple[int, dict[int, dict], tuple[float, float]]:
    """The docstring's slice rule: (slice index, {timepoint: image, released ET, PRISM ET}, arrow target as
    (x, y) axes fractions). One crop and one window rule for every visit of the patient."""
    import nibabel as nib
    d = MU / "MU-Glioma-Post" / pid
    t1c, lesion, net = {}, {}, {}
    for tp in tps:
        stem = d / f"Timepoint_{tp}" / f"{pid}_Timepoint_{tp}"
        t1c[tp] = np.asarray(nib.load(f"{stem}_brain_t1c.nii.gz").dataobj, dtype=np.float32)
        lesion[tp] = np.asarray(nib.load(f"{stem}_tumorMask.nii.gz").dataobj)
        net[tp] = np.asarray(nib.load(str(SEG / pid / f"Timepoint_{tp}.nii.gz")).dataobj) == ET_LABEL
    et_sum = sum((lesion[tp] == ET_LABEL).sum(axis=(0, 1)) for tp in tps)
    les_sum = sum((lesion[tp] > 0).sum(axis=(0, 1)) for tp in tps)
    z = int(np.argmax(et_sum if et_sum.max() > 0 else les_sum))
    brain = np.any([t1c[tp][:, :, z] > 0 for tp in tps], axis=0)
    ys, xs = np.nonzero(brain)
    cy, cx = (ys.min() + ys.max()) // 2, (xs.min() + xs.max()) // 2
    half = max(ys.max() - ys.min(), xs.max() - xs.min()) // 2 + 4
    crop = lambda a: np.rot90(a[max(cy - half, 0):cy + half, max(cx - half, 0):cx + half])   # anterior up
    out = {}
    for tp in tps:
        img = t1c[tp][:, :, z]
        lo, hi = np.percentile(img[img > 0], [1, 99.5])
        out[tp] = dict(img=crop(np.clip((img - lo) / (hi - lo), 0, 1)),
                       msk=crop(lesion[tp][:, :, z] == ET_LABEL), net=crop(net[tp][:, :, z]))
    target = sum(crop((lesion[tp][:, :, z] == ET_LABEL) if et_sum.max() > 0 else (lesion[tp][:, :, z] > 0))
                 .astype(float) for tp in tps)
    rows, cols = np.nonzero(target > 0)
    n = target.shape[0]
    return z, out, (cols.mean() / n, 1 - rows.mean() / n)


def show_scan(iax, scan: dict, arrow: tuple[float, float]) -> None:
    """One slice with the released mask (dashed), PRISM's segmentation (solid) and an arrow at the lesion."""
    iax.imshow(scan["img"], cmap="gray", vmin=0, vmax=1, interpolation="bilinear", extent=(0, 1, 0, 1))
    n = scan["img"].shape[0]
    grid = (np.arange(n) + 0.5) / n
    if scan["msk"].any():
        iax.contour(grid, grid[::-1], scan["msk"].astype(float), levels=[0.5], colors=[RELEASED], linewidths=0.8,
                    linestyles=[(0, (2.2, 1.2))])
    if scan["net"].any():
        iax.contour(grid, grid[::-1], scan["net"].astype(float), levels=[0.5], colors=[CONTOUR], linewidths=1.0)
    tx, ty = arrow                                   # lesion centre
    sx = -1 if tx > 0.5 else 1                       # from the side nearer the midline
    sy = 1 if ty + 0.24 <= 0.97 else -1              # from above, else from below
    tip, tail = (tx + sx * 0.045, ty + sy * 0.045), (tx + sx * 0.2, ty + sy * 0.22)
    iax.annotate("", xy=tip, xytext=tail,
                 arrowprops=dict(arrowstyle="-|>", color="white", lw=0.9, mutation_scale=6,
                                 path_effects=[pe.withStroke(linewidth=1.8, foreground="black")]))
    iax.set(xlim=(0, 1), ylim=(0, 1), xticks=[], yticks=[])
    for sp in iax.spines.values():
        sp.set_visible(False)


def draw(output: Path) -> dict[str, str]:
    df = load_records()
    picks = pick_patients(df)
    number = {case: k + 1 for k, case in enumerate(picks)}
    clin = load_clinical().set_index("Patient_ID")
    cohort = pd.read_csv(COHORT).drop_duplicates("patient_id").set_index("patient_id")

    H = len(LAYOUT) * ROW_H + LEGEND_H
    fig = plt.figure(figsize=(st.WIDTH, st.WIDTH * H / W))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, W), ylim=(0, H)); ax.axis("off")

    def text(x, y, s, size=5.8, colour=st.INK, **kw):
        kw.setdefault("ha", "left"); kw.setdefault("va", "top")
        return ax.text(x, y, s, fontsize=size, color=colour, linespacing=1.3, **kw)

    names = [s[1] for s in SCORES] + ["Combined, 80% set", "Models"]

    def strip(case: str, x0: float, x1: float, top: float) -> None:
        pid = picks[case]
        g = df[df.patient_id == pid]
        c = clin.loc[pid]
        days = scan_days(c)
        rt_end = float(c["Number of days from Diagnosis to Radiation Therapy end date"])
        _, slices, arrow = patient_slices(pid, list(g.tp))
        pitch = (x1 - x0) / len(g)
        # header: panel letter, patient facts (after Tak: one line per patient)
        ax.text(x0 - (LEFT - 1.0 if x0 == LEFT else -0.4), top - 0.6, case.lower(), fontsize=9, weight="bold",
                color=st.INK, ha="left", va="top")
        hx = x0 + (4.6 if x0 != LEFT else 0.0)
        prog = bool(g.label.max() == 1)
        text(hx, top - 1.0, f"Patient {number[case]}", size=6.4, weight="bold")
        text(hx + 12.5, top - 1.15, f"grade 4 · IDH {cohort.loc[pid, 'idh']} · MGMT {cohort.loc[pid, 'mgmt']} · "
             f"{'progressed' if prog else 'did not progress'}", size=5.8)
        y_lab = top - 5.6                       # scan label line
        iy1 = y_lab - 3.6                       # image top
        iy0 = iy1 - IW
        y_wk = iy0 - 0.6
        cy = y_wk - 2.6                         # top of the first score cell
        prev_weeks = None
        for j, (_, s) in enumerate(g.iterrows()):
            x = x0 + j * pitch + (pitch - IW) / 2
            weeks = (days[s.tp] - rt_end) / 7
            iax = fig.add_axes([x / W, iy0 / H, IW / W, IW / H])
            show_scan(iax, slices[s.tp], arrow)
            is_prog = s.label == 1
            text(x + IW / 2, y_lab, "Progression" if is_prog else "No progression", size=5.8, ha="center",
                 weight="bold" if is_prog else "normal")
            if 0 <= weeks <= 12:
                ax.add_patch(Rectangle((x, y_wk - 2.3), IW, 2.3, fc=st.tint(st.HIST, 0.75), ec="none", zorder=1))
            text(x + IW / 2, y_wk, f"{weeks:.0f} wk after RT", size=5.4, ha="center", zorder=3)
            if prev_weeks is not None:
                gx0, gx1 = x - (pitch - IW) + 0.6, x - 0.6
                ax.annotate("", xy=(gx1, iy0 + IW / 2), xytext=(gx0, iy0 + IW / 2),
                            arrowprops=dict(arrowstyle="-|>", color=st.MUTED, lw=0.6, mutation_scale=5))
                text((gx0 + gx1) / 2, iy0 + IW / 2 + 0.8, f"{weeks - prev_weeks:.0f} wk", size=5.2,
                     colour=st.MUTED, ha="center", va="bottom")
            prev_weeks = weeks
            for k, (key, _, colour) in enumerate(SCORES):
                v = float(s[key])
                amount = 0.92 - 0.85 * v
                ax.add_patch(Rectangle((x, cy - (k + 1) * CELL + 0.25), IW, CELL - 0.5,
                                       fc=st.tint(colour, amount), ec="none", zorder=2))
                text(x + IW / 2, cy - k * CELL - CELL / 2, f"{v:.2f}", size=5.6, ha="center", va="center",
                     colour="white" if amount < 0.45 else st.INK, zorder=3)
            text(x + IW / 2, cy - 3 * CELL - CELL / 2, SET_WORDS[s.set80], size=5.4, ha="center", va="center")
            text(x + IW / 2, cy - 4 * CELL - CELL / 2, "agree" if s.agree else "disagree", size=5.4, ha="center",
                 va="center", colour=st.MUTED if s.agree else st.INK, weight="normal" if s.agree else "bold")
        return cy

    for row, cases in enumerate(LAYOUT):
        top = H - row * ROW_H
        span = (W - 0.6 - LEFT - GAP * (len(cases) - 1)) / len(cases)
        for k, case in enumerate(cases):
            x0 = LEFT + k * (span + GAP)
            cy = strip(case, x0, x0 + span, top)
            if k:
                ax.plot([x0 - GAP / 2] * 2, [top - 0.6, top - ROW_H + 2.0], color=st.RULE, lw=0.5)
        for k, name in enumerate(names):
            text(LEFT - 1.4, cy - k * CELL - CELL / 2, name, size=5.4, ha="right", va="center",
                 colour=SCORES[k][2] if k < 3 else st.INK, weight="bold" if k < 3 else "normal")
        ax.plot([0.6, W - 0.6], [top - ROW_H + 1.0, top - ROW_H + 1.0], color=st.RULE, lw=0.5)

    # legend: one ramp per score, the shading, the two outlines, the arrow
    ly = LEGEND_H - 1.6
    x = LEFT
    for key, name, colour in SCORES:
        for i in range(8):
            v = (i + 0.5) / 8
            ax.add_patch(Rectangle((x + i * 1.6, ly - 2.4), 1.6, 2.4, fc=st.tint(colour, 0.92 - 0.85 * v), ec="none"))
        text(x, ly - 2.8, "0", size=5.0, colour=st.MUTED)
        text(x + 12.8, ly - 2.8, "1", size=5.0, colour=st.MUTED, ha="right")
        text(x + 14.2, ly - 1.2, name.lower(), size=5.4, va="center")
        x += 32.0
    ax.add_patch(Rectangle((x, ly - 2.4), 5.0, 2.4, fc=st.tint(st.HIST, 0.75), ec="none"))
    text(x + 6.2, ly - 1.2, "first 12 weeks after RT", size=5.4, va="center")
    y2 = ly - 5.6
    ax.plot([LEFT, LEFT + 4.0], [y2, y2], color=CONTOUR, lw=1.2)
    text(LEFT + 5.2, y2, "PRISM's segmenter", size=5.4, va="center")
    ax.plot([LEFT + 30.0, LEFT + 34.0], [y2, y2], color=RELEASED, lw=1.0, ls=(0, (2.2, 1.2)))
    text(LEFT + 35.2, y2, "released mask", size=5.4, va="center")
    text(LEFT + 64.0, y2, "outlines: enhancing tumour;  arrow: lesion, same place at every scan", size=5.4,
         colour=st.MUTED, va="center")

    st.save(fig, output, "fig_case_strips")
    return picks


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=REPO / "docs/manuscript/figures")
    a = p.parse_args()
    print(draw(a.output))
