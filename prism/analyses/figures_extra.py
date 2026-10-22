"""Two manuscript figures: the study design (Figure 2) and real MU-Glioma-Post imaging examples.

    .venv/bin/python -m prism.analyses.figures_extra [design|imaging|all]
    -> docs/manuscript/figures/fig_study_design.{pdf,png}, fig_imaging_examples.{pdf,png}

Style follows prism/analyses/paper_figures.py (DejaVu Sans 7-8.5 pt, pdf.fonttype 42, panels lettered, fixed colours).
Images stay on the cluster; only the rendered figure files are written. Patient IDs are printed to the log only.

study_design()
    Boxes and arrows, three columns: data, evaluation, PRISM and the prespecified questions. Cohort numbers are taken
    from docs/manuscript/TABLE1_COHORT.md (155 / 308; grade 4 126 / 249; LUMIERE 61 / 132) and
    docs/results/CFB_ADC.md (adc cohort, 77 patients).

imaging_examples()
    Data: MU-Glioma-Post (TCIA, CC BY 4.0), FeTS/SRI24-registered 1 mm volumes, shipped four-compartment masks
    (1 NETC, 2 SNFH, 3 ET, 4 RC; prism.config). Display: axial slice z, array[:, :, z].T (anterior up, patient right on
    the viewer's left, radiological convention).

    Slice rule (every scan, all panels): the axial slice with the largest ET area in that scan's own mask; if the scan
    has no ET, the slice with the largest lesion area (labels 1-3), then the largest mask area.

    (A) Patient selection, programmatic. Candidates: grade 4 patients whose every candidate scan is complete (4
        sequences + mask) and who have a progression scan (diagnostics_imaging.scan_table: first MRI with a mask on or
        after the documented progression date). Phase of care per scan as in paper_figures._phases (before RT, during
        RT, within 84 d after RT end, later), from the documented RT dates as of the scan day. Rank by the number of
        distinct phases covered by the patient's index scans (outputs/data/mu_cohort.csv), then by the number of index
        scans, then by patient ID; take the first. Scans shown: the first index scan of each phase in time order,
        except that for the last phase before progression the LAST index scan is shown (the scan just before
        progression), followed by the progression scan. Four columns at most (the earliest phases are kept).
        Outcome line: label_120 of the index scan (documented progression within 120 d / none within 120 d /
        censored); the progression scan itself is labelled as such.
    (B) Scan selection: grade 4 index scans with MU ET >= 1 cc and a BraTS 2021 SwinUNETR re-segmentation
        (outputs/features/seg_swin/volumes_brats21.csv); the scan whose Dice(ET, MU vs re-segmentation) is the median
        (lower median), i.e. a typical, not a best or worst, agreement. Zoomed to the ET bounding box.
    (C) Patient selection: grade 4 patients with a consecutive-scan pair <= 14 d apart in
        outputs/results/analyses/reseg/consecutive_pairs.csv without surgery or brachytherapy flagged between the two
        scans, not involved in a cross-patient near-duplicate mask pair
        (diagnostics_imaging/cross_patient_near_duplicates.csv), and with >= 4 measured scans; the first 4 by patient
        ID. MU ET volume (outputs/features/measurements.csv) over days since diagnosis.
    (D) All 389 consecutive-scan pairs (consecutive_pairs.csv, MU masks): ET fold change max/min of (v + 0.1 cc) by gap,
        bins as in DIAGNOSTICS_IMAGING.md (volume_continuity_by_gap.csv).
"""

from __future__ import annotations

import sys

import nibabel as nib
import numpy as np
import pandas as pd

from prism.analyses.paper_figures import C, FIG, GRID, INK, INK2, _letter, _style
from prism.config import LABEL_ET, LABEL_NETC, LABEL_RC, LABEL_SNFH, MEASUREMENTS, RESULTS, mu_scan_paths

AN = RESULTS / "analyses"
CM = 1 / 2.54
# Okabe-Ito contour colours (CVD-safe on every pair; validated with the dataviz validator, all pairs)
MASK_COL = {LABEL_ET: "#D55E00", LABEL_NETC: "#F0E442", LABEL_SNFH: "#56B4E9", LABEL_RC: "#009E73"}
MASK_NAME = {LABEL_ET: "Enhancing tumour", LABEL_NETC: "Non-enhancing core", LABEL_SNFH: "Surrounding FLAIR signal",
             LABEL_RC: "Resection cavity"}
RESEG_COL = "#56B4E9"
PHASE_NAME = {"pre_rt": "before RT", "during_rt": "during RT", "early_post_rt": "within 12 wk after RT",
              "later": "later than 12 wk after RT"}
PHASE_ORDER = ["pre_rt", "during_rt", "early_post_rt", "later"]


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", facecolor="white", dpi=300)
    print("wrote", FIG / f"{name}.pdf", "and .png")


# ================================================================ Figure A: study design
def study_design():
    plt = _style()
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    W, H = 17.0, 9.6
    fig = plt.figure(figsize=(W * CM, H * CM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    FILL, PR = "#f3f2ef", C["prism"]

    def box(x, y, w, h, title, body="", edge=INK2, fill="white", lw=0.7, tsize=7.5, bsize=6.6, align="center"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.12", fc=fill, ec=edge, lw=lw))
        cx = x + w / 2 if align == "center" else x + 0.18
        if body:
            ax.text(cx, y + h - 0.16, title, ha=align, va="top", fontsize=tsize, fontweight="bold", color=INK)
            ax.text(cx, y + h - 0.52, body, ha=align, va="top", fontsize=bsize, color=INK2, linespacing=1.3)
        else:
            ax.text(cx, y + h / 2, title, ha=align, va="center", fontsize=tsize, fontweight="bold", color=INK)

    def arrow(x0, y0, x1, y1, col=INK2, ls="-"):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>,head_length=3,head_width=1.8",
                                     color=col, lw=0.8, ls=ls, shrinkA=0, shrinkB=0))

    # column headers
    cols = [(0.25, 5.0, "A", "Data"), (6.0, 4.9, "B", "Evaluation"), (11.55, 5.2, "C", "PRISM and the questions")]
    for x, w, L, t in cols:
        ax.text(x - 0.05, H - 0.25, L, fontsize=11, fontweight="bold", va="top", ha="left", color=INK)
        ax.text(x + 0.42, H - 0.33, t, fontsize=8.5, fontweight="bold", va="top", ha="left", color=INK)

    # ---- column 1: data
    x1, w1 = 0.25, 5.0
    box(x1, 6.95, w1, 1.75, "MU-Glioma-Post", "development\n155 patients, 308 index scans\ngrade 4: 126 patients, 249 scans",
        fill=FILL)
    box(x1, 5.35, w1, 1.3, "LUMIERE", "external test\n61 patients, 132 index scans", fill=FILL)
    box(x1, 3.75, w1, 1.3, "CFB-GBM", "diffusion (ADC)\n77 patients with ADC", fill=FILL)
    box(x1, 0.25, w1, 3.2, "Definitions",
        "Index scan: MRI before the first\ndocumented progression, with T1, T1c,\nT2, FLAIR and tumour mask\n\n"
        "Outcome: documented progression\nwithin 120 days; censored at last\nfollow-up or death",
        edge=GRID, align="left", bsize=6.8)

    # ---- column 2: evaluation
    x2, w2 = 6.0, 4.9
    box(x2, 7.6, w2, 1.1, "Initial single split", "29 test patients")
    box(x2, 6.05, w2, 1.1, "500 splits", "same design, different test patients")
    box(x2, 3.75, w2, 1.85, "Repeated cross-validation",
        "5 × 5 folds, grouped by patient\nevery fitted step inside\nthe training fold", lw=1.1, edge=INK)
    arrow(x2 + w2 / 2, 7.6, x2 + w2 / 2, 7.15)
    arrow(x2 + w2 / 2, 6.05, x2 + w2 / 2, 5.6)
    box(x2, 2.05, w2, 1.2, "LUMIERE", "locked external test", fill=FILL)
    box(x2, 0.25, w2, 1.2, "CFB-GBM", "cross-validation", fill=FILL)
    # data -> evaluation
    arrow(x1 + w1, 7.8, x2, 8.15)
    arrow(x1 + w1, 6.0, x2 - 0.05, 2.75)
    arrow(x1 + w1, 4.4, x2 - 0.05, 0.9)

    # ---- column 3: PRISM and the questions
    x3, w3 = 11.55, 5.2
    box(x3, 7.75, w3, 0.95, "Core model", "clinical + treatment course", edge=PR, lw=1.1)
    ax.text(x3 + w3 / 2, 7.6, "+", ha="center", va="center", fontsize=9, fontweight="bold", color=INK)
    box(x3, 6.35, w3, 1.1, "Optional imaging branches", "volumes, radiomics, deep encoder\n(frozen or fine-tuned)",
        edge=PR, lw=0.8)
    box(x3, 5.3, w3, 0.65, "Per-scan audit record", edge=PR, lw=1.1)
    box(x3, 4.25, w3, 0.65, "Grounded report", edge=PR, lw=1.1)
    arrow(x3 + w3 / 2, 6.35, x3 + w3 / 2, 5.95, col=PR)
    arrow(x3 + w3 / 2, 5.3, x3 + w3 / 2, 4.9, col=PR)
    box(x3, 0.25, w3, 3.6, "Prespecified questions (Table 4)",
        "1  Does imaging add to the core model?\n\n2  Is the phase of care a censoring\n    artefact?\n\n"
        "3  Does the audit work?\n\n4  Are reports faithful and complete?", edge=INK, lw=1.1, align="left", bsize=6.8)
    # evaluation -> questions ; PRISM -> questions
    arrow(x2 + w2, 4.67, x3, 3.2)
    arrow(x2 + w2, 2.65, x3, 2.2)
    arrow(x2 + w2, 0.85, x3, 1.2)
    arrow(x3 + w3 / 2, 4.25, x3 + w3 / 2, 3.85, col=PR)
    _save(fig, "fig_study_design")
    plt.close(fig)


# ================================================================ Figure B: imaging examples
def _load(scan_id, keys=("t1c", "flair", "mask")):
    pid, tp = scan_id.rsplit("_Timepoint_", 1)
    p = mu_scan_paths(pid, f"Timepoint_{tp}")
    out = {k: np.asarray(nib.load(str(p[k])).dataobj).astype(np.float32) for k in keys}
    if "mask" in out:
        out["mask"] = np.rint(out["mask"]).astype(np.int16)
    return out


def _slice(mask):
    """Axial slice with the largest ET area; else largest lesion (1-3) area; else largest mask area."""
    for sel in ((LABEL_ET,), (LABEL_NETC, LABEL_SNFH, LABEL_ET), (1, 2, 3, 4)):
        area = np.isin(mask, sel).sum(axis=(0, 1))
        if area.any():
            return int(np.argmax(area))
    return mask.shape[2] // 2


def _show(ax, img, z, crop=None, vmax=None):
    sl = img[:, :, z].T
    if vmax is None:
        vmax = np.percentile(sl[sl > 0], 99.5) if (sl > 0).any() else 1
    ax.imshow(sl, cmap="gray", vmin=0, vmax=vmax, interpolation="nearest")
    if crop is not None:
        (r0, r1), (c0, c1) = crop
        ax.set_xlim(c0 - 0.5, c1 - 0.5)
        ax.set_ylim(r1 - 0.5, r0 - 0.5)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def _contours(ax, mask, z, labels=(LABEL_RC, LABEL_SNFH, LABEL_NETC, LABEL_ET), lw=0.6):
    m = mask[:, :, z].T
    for lab in labels:
        b = m == lab
        if b.any():
            ax.contour(b.astype(float), levels=[0.5], colors=MASK_COL[lab], linewidths=lw * (1.3 if lab == LABEL_ET else 1))


def _phases_all(s, index):
    from prism.features.tabular import treatment
    d = s[["scan_id"]].copy()
    d["days_from_diagnosis_to_mri"] = s.mri_day.to_numpy()
    t = treatment(d, index)
    ix = index.set_index("scan_id").reindex(s.scan_id)
    rt_end = pd.to_numeric(ix["clinical_number_of_days_from_diagnosis_to_radiation_therapy_end_date"].astype(str)
                           .str.extract(r"([-\d.]+)")[0], errors="coerce").to_numpy()
    since = s.mri_day.to_numpy() - rt_end
    early = (t.rt_completed.to_numpy() == 1) & (since >= 0) & (since <= 84)
    return np.where(t.rt_started == 0, "pre_rt", np.where(t.rt_completed == 0, "during_rt",
                    np.where(early, "early_post_rt", "later")))


def _pick_patient(s):
    from prism.data.mu import load_cohort
    coh = load_cohort("all_glioma")[["scan_id", "label_120"]]
    s = s.merge(coh, on="scan_id", how="left")
    s["is_index"] = s.scan_id.isin(coh.scan_id)
    cand = []
    for pid, d in s[s.grade4].groupby("patient_id"):
        if not d.is_progression_scan.any():
            continue
        idx = d[d.is_index]
        shown = pd.concat([idx, d[d.is_progression_scan]])
        if not shown.complete.all():
            continue
        cand.append((-idx.phase.nunique(), -len(idx), pid))
    cand.sort()
    pid = cand[0][2]
    d = s[s.patient_id == pid].sort_values("mri_day")
    idx = d[d.is_index]
    phases = [p for p in PHASE_ORDER if p in set(idx.phase)]
    rows = []
    for p in phases:
        g = idx[idx.phase == p]
        rows.append(g.iloc[-1] if p == phases[-1] else g.iloc[0])
    rows = rows[:3] + [d[d.is_progression_scan].iloc[0]]
    print(f"[A] candidates (phases, n index scans): {[(c[2], -c[0], -c[1]) for c in cand[:5]]}")
    print(f"[A] chosen {pid}: " + ", ".join(f"{r.timepoint} day {r.mri_day:.0f} {r.phase}" for r in rows))
    return pd.DataFrame(rows)


def _pick_reseg(s):
    from prism.data.mu import load_cohort
    from prism.features.reseg import seg_path, volumes_path
    v = pd.read_csv(volumes_path("brats21"))
    coh = load_cohort("grade4")
    v = v[v.scan_id.isin(coh.scan_id) & (v.mu_et_voxels >= 1000) & v.dice_et.notna()]
    v = v[[seg_path(x).exists() for x in v.scan_id]].sort_values(["dice_et", "scan_id"]).reset_index(drop=True)
    r = v.iloc[(len(v) - 1) // 2]
    print(f"[B] {len(v)} eligible scans, median Dice ET {v.dice_et.median():.3f}; chosen {r.scan_id} Dice {r.dice_et:.3f}")
    return r, seg_path(r.scan_id)


def _pick_trajectories(s):
    cp = pd.read_csv(AN / "reseg" / "consecutive_pairs.csv")
    dup = pd.read_csv(AN / "diagnostics_imaging" / "cross_patient_near_duplicates.csv")
    dup_p = set(dup.scan_a.str.rsplit("_Timepoint_", n=1).str[0]) | set(dup.scan_b.str.rsplit("_Timepoint_", n=1).str[0])
    g4 = set(s.loc[s.grade4, "patient_id"])
    nmeas = s[s.has_meas].groupby("patient_id").size()
    short = cp[(cp.gap <= 14) & ~cp.surgery_between.astype(bool) & ~cp.brachy_between.astype(bool)]
    pats = sorted(p for p in short.patient_id.unique() if p in g4 and p not in dup_p and nmeas.get(p, 0) >= 4)
    print(f"[C] eligible patients: {pats}; chosen {pats[:4]}")
    return pats[:4], short, cp


def imaging_examples():
    plt = _style()
    import prism.analyses.diagnostics_imaging as di
    from matplotlib.gridspec import GridSpec
    from matplotlib.lines import Line2D
    from prism.data.mu import load_index

    index = load_index()
    s = di.scan_table(index)
    s["phase"] = _phases_all(s, index)
    sel = _pick_patient(s)
    n = len(sel)

    fig = plt.figure(figsize=(17 * CM, 16.5 * CM))
    gs = GridSpec(3, 1, figure=fig, height_ratios=[2.05, 0.3, 1.0], hspace=0.0,
                  left=0.035, right=0.99, top=0.925, bottom=0.07)
    gA = gs[0].subgridspec(2, n, wspace=0.03, hspace=0.03)
    gB = gs[2].subgridspec(1, 3, width_ratios=[0.8, 1.15, 1.15], wspace=0.42)

    # ---- (A) one patient across phases of care
    imgs = [_load(r.scan_id) for r in sel.itertuples()]
    brain = np.any([im["t1c"] > 0 for im in imgs], axis=(0, 3))  # (x, y) union of brain footprint
    xs, ys = np.where(brain)
    crop = ((ys.min() - 3, ys.max() + 4), (xs.min() - 3, xs.max() + 4))  # rows = y, cols = x after .T
    for j, (r, im) in enumerate(zip(sel.itertuples(), imgs)):
        z = _slice(im["mask"])
        for i, seq in enumerate(("t1c", "flair")):
            ax = fig.add_subplot(gA[i, j])
            _show(ax, im[seq], z, crop)
            _contours(ax, im["mask"], z)
            if j == 0:
                ax.set_ylabel("T1c" if seq == "t1c" else "FLAIR", fontsize=7.5, color=INK, labelpad=2)
            if i == 0:
                if r.is_progression_scan:
                    head, out = f"Day {r.mri_day:.0f}, progression scan", "documented progression"
                else:
                    head = f"Day {r.mri_day:.0f}, {PHASE_NAME[r.phase]}"
                    out = ("progression within 120 d" if r.label_120 == 1 else
                           "no progression within 120 d" if r.label_120 == 0 else "censored before 120 d")
                ax.set_title(f"{head}\n{out}", fontsize=7, fontweight="normal", loc="center", pad=3, color=INK)
                if j == 0:
                    _letter(ax, "A", x=-0.04, y=1.13)
    handles = [Line2D([], [], color=MASK_COL[k], lw=1.4) for k in (LABEL_ET, LABEL_NETC, LABEL_SNFH, LABEL_RC)]
    axL = fig.add_subplot(gs[1])
    axL.axis("off")
    axL.legend(handles, [MASK_NAME[k] for k in (LABEL_ET, LABEL_NETC, LABEL_SNFH, LABEL_RC)], loc="upper center",
               bbox_to_anchor=(0.5, 0.8), ncol=4, frameon=False, fontsize=7, handlelength=1.6, columnspacing=1.6)

    # ---- (B) original vs re-segmented ET
    r, path = _pick_reseg(s)
    im = _load(r.scan_id, ("t1c", "mask"))
    new = np.rint(np.asarray(nib.load(str(path)).dataobj)).astype(np.int16)
    z = _slice(im["mask"])
    et_mu, et_new = im["mask"][:, :, z].T == LABEL_ET, new[:, :, z].T == LABEL_ET
    rr, cc = np.where(et_mu | et_new)
    half = max(np.ptp(rr), np.ptp(cc)) // 2 + 14
    r0, c0 = (rr.min() + rr.max()) // 2, (cc.min() + cc.max()) // 2
    axB = fig.add_subplot(gB[0])
    _show(axB, im["t1c"], z, ((r0 - half, r0 + half), (c0 - half, c0 + half)),
          vmax=np.percentile(im["t1c"][:, :, z][im["t1c"][:, :, z] > 0], 99.5))
    axB.contour(et_mu.astype(float), levels=[0.5], colors=MASK_COL[LABEL_ET], linewidths=1.0)
    axB.contour(et_new.astype(float), levels=[0.5], colors=RESEG_COL, linewidths=1.0, linestyles=[(0, (2.2, 1.2))])
    axB.set_title("ET, two masks", fontsize=7.5, loc="left", pad=3)
    axB.legend([Line2D([], [], color=MASK_COL[LABEL_ET], lw=1.2), Line2D([], [], color=RESEG_COL, lw=1.2, ls=(0, (2.2, 1.2)))],
               ["Dataset mask", "Resegmentation"], loc="upper left", bbox_to_anchor=(-0.02, -0.01), frameon=False,
               fontsize=6.5, handlelength=1.8, borderaxespad=0.2)
    axB.text(0.03, 0.97, f"Dice {r.dice_et:.2f}", transform=axB.transAxes, ha="left", va="top", fontsize=6.5,
             color="white")
    _letter(axB, "B", x=-0.04, y=1.1)

    # ---- (C) ET volume over time, patients with closely spaced scans (small multiples, shared log y)
    pats, short, cp = _pick_trajectories(s)
    gC = gB[1].subgridspec(2, 2, wspace=0.12, hspace=0.32)
    axs = []
    for k, pid in enumerate(pats):
        a_ = fig.add_subplot(gC[k // 2, k % 2], sharey=axs[0] if axs else None)
        axs.append(a_)
        d = s[(s.patient_id == pid) & s.has_meas].sort_values("mri_day")
        a_.plot(d.mri_day, d.et_cc + 0.1, color=INK2, lw=0.8, marker="o", ms=2.6, mfc="white", mec=INK2, mew=0.7,
                zorder=2)
        notes = []
        for q in short[short.patient_id == pid].itertuples():
            a0 = d[d.scan_id == q.prev_scan_id].iloc[0]
            b0 = d[d.scan_id == q.scan_id].iloc[0]
            v0, v1 = a0.et_cc + 0.1, b0.et_cc + 0.1
            a_.plot([a0.mri_day, b0.mri_day], [v0, v1], color=MASK_COL[LABEL_ET], lw=2.0, solid_capstyle="round",
                    zorder=3)
            notes.append(f"{max(v0, v1) / min(v0, v1):.1f}× in {q.gap:.0f} d")
        a_.text(0.04, 0.04, "\n".join(notes), transform=a_.transAxes, fontsize=6, color=INK, ha="left", va="bottom")
        a_.set_yscale("log")
        a_.grid(axis="y", color=GRID, lw=0.5)
        a_.tick_params(labelsize=6)
        if k % 2:
            a_.tick_params(labelleft=False)
        lo, hi = d.mri_day.min(), d.mri_day.max()
        a_.set_xlim(lo - 0.08 * (hi - lo), hi + 0.08 * (hi - lo))
    axs[0].set_ylim(0.05, 300)
    axs[0].set_yticks([0.1, 1, 10, 100])
    axs[0].set_yticklabels(["0.1", "1", "10", "100"])
    fig.text(axs[0].get_position().x0 - 0.045, (axs[0].get_position().y1 + axs[2].get_position().y0) / 2,
             "ET volume + 0.1 (cc)", rotation=90, ha="center", va="center", fontsize=7.5, color=INK)
    fig.text((axs[2].get_position().x0 + axs[3].get_position().x1) / 2, axs[2].get_position().y0 - 0.05,
             "Days since diagnosis", ha="center", va="top", fontsize=7.5, color=INK)
    axs[0].set_title("ET volume, 4 patients", fontsize=7.5, loc="left", pad=3)
    _letter(axs[0], "C", x=-0.3, y=1.1)

    # ---- (D) fold change by gap, all consecutive pairs
    axD = fig.add_subplot(gB[2])
    bins = [(-1, 14, "≤ 14"), (14, 45, "15–45"), (45, 90, "46–90"), (90, 180, "91–180"), (180, 1e5, "> 180")]
    rng = np.random.default_rng(0)
    for i, (lo, hi, lab) in enumerate(bins):
        f = np.exp(cp.loc[(cp.gap > lo) & (cp.gap <= hi), "abslog_et|mu"].dropna().to_numpy())
        axD.scatter(i + rng.uniform(-0.28, 0.28, len(f)), f, s=4, color=INK2, alpha=0.45, lw=0, zorder=2)
        med = np.median(f)
        axD.plot([i - 0.34, i + 0.34], [med, med], color=MASK_COL[LABEL_ET] if i == 0 else INK, lw=1.8, zorder=3,
                 solid_capstyle="round")
        axD.text(i, 500, f"{med:.1f}×\nn = {len(f)}", ha="center", va="bottom", fontsize=6.0, color=INK)
    axD.set_yscale("log")
    axD.set_ylim(0.9, 2500)
    axD.set_yticks([1, 2, 5, 10, 100])
    axD.set_yticklabels(["1", "2", "5", "10", "100"])
    axD.set_xticks(range(len(bins)))
    axD.set_xticklabels([b[2] for b in bins])
    axD.set_xlabel("Days between consecutive scans")
    axD.set_ylabel("ET fold change")
    axD.set_title("All consecutive scan pairs", fontsize=7.5, loc="left", pad=3)
    axD.grid(axis="y", color=GRID, lw=0.5)
    _letter(axD, "D", x=-0.2, y=1.04)

    _save(fig, "fig_imaging_examples")
    plt.close(fig)


def main(argv=None) -> None:
    what = (argv if argv is not None else sys.argv[1:]) or ["all"]
    if what[0] in ("design", "all"):
        study_design()
    if what[0] in ("imaging", "all"):
        imaging_examples()


if __name__ == "__main__":
    main()
