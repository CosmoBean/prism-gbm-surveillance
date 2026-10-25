"""Deterministic segmentation figure attached to each PRISM report v3 (SYSTEM_PLAN.md section 4).

The LLM never sees images: this module renders one PNG per scan from the images and masks, and the report code
attaches it. Nothing here is learned or random.

Panels
  A  this scan: the axial slice with the largest enhancing-tumour (ET) area, post-contrast T1 with ET, necrosis and
     cavity outlines, and the same slice on FLAIR with the SNFH (oedema / non-enhancing signal) outline. Without ET:
     the slice with the largest lesion (ET + necrosis + SNFH), then the largest any-label area, then the largest
     brain cross-section; the panel says which rule was used ("no enhancing tumour segmented").
  B  the previous scan (the system's own previous scan: strictly earlier) at the same slice index. All three cohorts
     store every timepoint in a common atlas space (MU, UCSF: BraTS / SRI24 240x240x155; LUMIERE: the DeepBraTumIA
     atlas 182x218x182), so the same index is the same anatomy up to each timepoint's own atlas registration. There is
     no direct longitudinal registration. If the shapes differ or the brain masks overlap poorly (Dice < COREG_DICE),
     the previous scan's own max-ET slice is shown and labelled as such.
  C  compartment volumes over the patient's scans up to and including this scan (never later scans: asserted), with
     this scan marked.

Conventions: arrays are reoriented to RAS (nibabel as_closest_canonical) and shown in the radiological convention
(patient's right on the viewer's left; anterior at the top), marked R / L / A / P on every image. Time is shown only
as days from RT start (MU; UCSF where known) or as the scan's position (LUMIERE has no RT dates; UCSF scan 1 / 2).
No identifiers, no dates. Colours: Okabe-Ito (colour-blind safe), each compartment also has its own line style.

Labels: MU and UCSF (BraTS post-treatment): 1 NETC (necrosis), 2 SNFH, 3 ET, 4 RC (cavity). LUMIERE DeepBraTumIA
atlas seg_mask: 1 enhancing core (ET), 2 necrotic / non-enhancing (necrosis; includes the cavity: no separate cavity
label), 3 oedema (SNFH); the mapping was checked against measured_volumes_in_mm3.json voxel counts and intensities.

    PYTHONPATH=. .venv/bin/python -m prism.report.seg_figure --examples          # 2 per cohort
    PYTHONPATH=. .venv/bin/python -m prism.report.seg_figure --all --workers 6   # every system-population scan
"""

from __future__ import annotations

import argparse
import gzip
import os
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import nibabel as nib
import numpy as np
import pandas as pd

from prism.config import (LABEL_ET, LABEL_NETC, LABEL_RC, LABEL_SNFH, LUMIERE_ROOT, MEASUREMENTS, MU_INDEX, OUTPUTS,
                          RESULTS, mu_scan_paths)

OUT = RESULTS / "analyses" / "system" / "figures"
COHORTS = ("mu", "lumiere", "ucsf")
COREG_DICE = 0.80  # 3-D brain-mask Dice below which the previous scan is treated as not co-registered
COMP = ("et", "netc", "rc", "snfh")
NAME = {"et": "enhancing tumour (ET)", "netc": "necrosis", "rc": "resection cavity", "snfh": "SNFH / oedema"}
NAME_LUMIERE = {**NAME, "netc": "necrosis / non-enh. (incl. cavity)"}
COLOR = {"et": "#E69F00", "netc": "#CC79A7", "rc": "#56B4E9", "snfh": "#009E73"}  # Okabe-Ito
STYLE = {"et": "-", "netc": "--", "rc": ":", "snfh": "-"}
MARK = {"et": "o", "netc": "s", "rc": "^", "snfh": "D"}
INK, MUTED = "#1f2933", "#52606d"
LABELS = {"mu": {"et": LABEL_ET, "netc": LABEL_NETC, "snfh": LABEL_SNFH, "rc": LABEL_RC},
          "ucsf": {"et": LABEL_ET, "netc": LABEL_NETC, "snfh": LABEL_SNFH, "rc": LABEL_RC},
          "lumiere": {"et": 1, "netc": 2, "snfh": 3}}
SOURCE = {"mu": "MU-Glioma-Post masks (BraTS space)", "ucsf": "UCSF-ALPTDG masks (BraTS space)",
          "lumiere": "DeepBraTumIA automatic segmentation (atlas space)"}
LUMIERE_ZIP = LUMIERE_ROOT / "Imaging-v202211.zip"


# ------------------------------------------------------------------ pure helpers (unit-tested)
def choose_slice(comp: dict[str, np.ndarray], brain: np.ndarray) -> tuple[int, str, float]:
    """Axial index (last RAS axis) and the rule used: largest ET area; else largest lesion (ET + NETC + SNFH); else
    largest any-label area (incl. cavity); else largest brain cross-section. Ties: the lowest (most inferior) index."""
    area = lambda m: m.sum(axis=(0, 1))
    et = comp["et"]
    lesion = et | comp["netc"] | comp["snfh"]
    anyl = lesion | comp["rc"]
    for m, rule in ((et, "largest ET area"), (lesion, "largest lesion (no ET)"),
                    (anyl, "largest cavity (no lesion)"), (brain, "largest brain section")):
        if m.any():
            a = area(m)
            k = int(np.argmax(a))
            return k, rule, float(a[k])
    return brain.shape[2] // 2, "middle slice (empty image)", 0.0


def past_only(hist: pd.DataFrame, scan_id: str) -> pd.DataFrame:
    """The patient's history rows up to and including `scan_id` ordered by `order`; later rows are dropped and the
    result is asserted to end at the current scan with nothing after it."""
    cur = hist.loc[hist.scan_id.eq(scan_id), "order"]
    assert len(cur) == 1, f"current scan {scan_id} must appear once in its history"
    t = cur.iat[0]
    h = hist[(hist.order < t) | hist.scan_id.eq(scan_id)].sort_values("order").reset_index(drop=True)
    assert h.scan_id.iat[-1] == scan_id and (h.order <= t).all() and h.order.is_monotonic_increasing
    assert not h.scan_id.duplicated().any()
    return h


def to_display(sl: np.ndarray) -> np.ndarray:
    """RAS axial slice (x, y) -> image rows = anterior..posterior, columns = patient right..left (radiological)."""
    return sl.T[::-1, ::-1]


def dice(a: np.ndarray, b: np.ndarray) -> float:
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else float("nan")


# ------------------------------------------------------------------ data access
@dataclass
class Scan:
    t1c: np.ndarray
    flair: np.ndarray
    comp: dict = field(default_factory=dict)
    seg_ok: bool = True  # False: mask missing or all empty (a failed segmentation)

    @property
    def brain(self) -> np.ndarray:
        return (self.t1c > 0) | (self.flair > 0)


def _canon(img) -> np.ndarray:
    return np.asarray(nib.as_closest_canonical(img).dataobj)


def _comp(mask: np.ndarray, cohort: str) -> dict:
    lab = LABELS[cohort]
    return {c: (mask == lab[c]) if c in lab else np.zeros(mask.shape, bool) for c in COMP}


@lru_cache(maxsize=1)
def _zip():
    return zipfile.ZipFile(LUMIERE_ZIP)


def _from_zip(name: str):
    return nib.Nifti1Image.from_bytes(gzip.decompress(_zip().read(name)))


def load_scan(cohort: str, scan_id: str) -> Scan | None:
    if cohort == "lumiere":
        pid, date = scan_id.split("_", 1)
        base = f"Imaging/{pid}/{date}/DeepBraTumIA-segmentation/atlas/"
        try:
            t1c = _canon(_from_zip(base + "skull_strip/ct1_skull_strip.nii.gz")).astype(np.float32)
            flair = _canon(_from_zip(base + "skull_strip/flair_skull_strip.nii.gz")).astype(np.float32)
        except KeyError:
            return None
        try:
            mask = np.rint(_canon(_from_zip(base + "segmentation/seg_mask.nii.gz"))).astype(np.int16)
        except KeyError:
            mask = np.zeros(t1c.shape, np.int16)
    else:
        if cohort == "mu":
            pid, tp = scan_id.split("_Timepoint_")
            p = mu_scan_paths(pid, f"Timepoint_{tp}")
        else:
            from prism.features.ucsf_imaging import ucsf_paths
            sid, tp = scan_id.split("_time")
            p = ucsf_paths(sid, int(tp))
        try:
            t1c = _canon(nib.load(str(p["t1c"]))).astype(np.float32)
            flair = _canon(nib.load(str(p["flair"]))).astype(np.float32)
        except FileNotFoundError:
            return None
        try:
            mask = np.rint(_canon(nib.load(str(p["mask"])))).astype(np.int16)
        except FileNotFoundError:
            mask = np.zeros(t1c.shape, np.int16)
    comp = _comp(mask, cohort)
    return Scan(t1c, flair, comp, seg_ok=bool(mask.any()))


@lru_cache(maxsize=1)
def _mu_tables():
    d = pd.read_csv(OUTPUTS / "data" / "detection_cohort.csv")
    m = pd.read_csv(MEASUREMENTS, usecols=["scan_id", "patient_id", "mri_day", "et_cc", "netc_cc", "snfh_cc", "rc_cc"])
    ix = pd.read_csv(MU_INDEX, usecols=["patient_id",
                                        "clinical_number_of_days_from_diagnosis_to_radiation_therapy_start_date"])
    rt = pd.to_numeric(ix.iloc[:, 1], errors="coerce").groupby(ix.patient_id).first()
    return d, m, rt


@lru_cache(maxsize=1)
def _lumiere_tables():
    from prism.analyses.detection import lumiere_detection
    from prism.data.lumiere import _week
    L, _, _ = lumiere_detection()
    r = pd.read_csv(LUMIERE_ROOT / "LUMIERE-ExpertRating-v202211.csv")
    r.columns = ["patient_id", "date", "lt3m", "nonmeas", "rating", "rationale"]
    r["scan_id"] = r.patient_id + "_" + r.date
    r = r.drop_duplicates("scan_id").reset_index(drop=True)  # 3 studies are rated twice; one row per study
    r["pre_op"] = r.rating.astype(str).str.strip().eq("Pre-Op")
    r["day"] = r.date.map(_week) * 7
    v = pd.read_csv(OUTPUTS / "features" / "lumiere_deepbratumia_volumes_all_studies.csv").set_index("scan_id")
    for c, k in (("raw_Enhancing_Core", "et_cc"), ("raw_Necrotic_NonEnhancing", "netc_cc"),
                 ("raw_Edema_Compartment", "snfh_cc")):
        r[k] = v[c].reindex(r.scan_id).to_numpy() / 1000.0
    r["rc_cc"] = np.nan  # no separate cavity label in DeepBraTumIA
    return L, r


@lru_cache(maxsize=1)
def _ucsf_tables():
    s = pd.read_csv(OUTPUTS / "data" / "ucsf" / "scans.csv", dtype={"subject_id": str})
    f = pd.read_csv(OUTPUTS / "data" / "ucsf" / "imaging_features.csv", dtype={"SubjectID": str},
                    usecols=["scan_id", "SubjectID", "timepoint", "et_cc", "netc_cc", "snfh_cc", "rc_cc"])
    return s, f


def population(cohort: str) -> list[str]:
    """System populations (SYSTEM_PLAN.md 1): MU grade-4 detection scans, LUMIERE detection scans, UCSF grade-4 scan 2."""
    if cohort == "mu":
        d = _mu_tables()[0]
        return d.loc[d.grade4, "scan_id"].tolist()
    if cohort == "lumiere":
        return _lumiere_tables()[0].scan_id.tolist()
    s = _ucsf_tables()[0]
    return s.loc[s.grade4 & s.timepoint.eq(2), "scan_id"].tolist()


def context(cohort: str, scan_id: str) -> dict:
    """prev_scan_id (or ''), the past-only history (scan_id, order, x, xlabel, *_cc), and the time label of the scan."""
    if cohort == "mu":
        d, m, rt = _mu_tables()
        row = d.set_index("scan_id").loc[scan_id]
        pid = row.patient_id
        h = m[m.patient_id.eq(pid)].rename(columns={"mri_day": "order"})
        h = past_only(h, scan_id)
        r0 = rt.get(pid, np.nan)
        if np.isfinite(r0):
            h["x"] = h.order - r0
            h["xlabel"] = [f"{x:+.0f}" for x in h.x]
            xname = "days from RT start"
        else:
            h["x"] = np.arange(1, len(h) + 1)
            h["xlabel"] = [f"scan {i}" for i in h.x]
            xname = "scan (RT start date not recorded)"
        prev = row.prev_scan_id if isinstance(row.prev_scan_id, str) else ""
    elif cohort == "lumiere":
        L, r = _lumiere_tables()
        row = L.set_index("scan_id").loc[scan_id]
        g = r[r.patient_id.eq(row.patient_id)].copy()
        g["order"] = g.day + g.date.rank(method="first") * 1e-3  # same-week studies keep their file order
        # the system's previous-scan pool: rated, post-operative, usable segmentation; plus this scan
        keep = (g.et_cc.notna() & ~g.pre_op) | g.scan_id.eq(scan_id)
        h = past_only(g[keep], scan_id)
        h["x"] = np.arange(1, len(h) + 1)
        h["xlabel"] = [f"scan {i}" for i in h.x]
        xname = "post-operative scan with a usable segmentation (no RT dates in LUMIERE)"
        prev = row.prev_scan_id if isinstance(row.prev_scan_id, str) else ""
    else:
        s, f = _ucsf_tables()
        sid, tp = scan_id.split("_time")
        h = f[f.SubjectID.eq(sid)].assign(order=lambda x: x.timepoint.str[-1].astype(int))
        h = past_only(h, scan_id)
        rtd = s.set_index("scan_id").days_from_rt_start_to_mri.reindex(h.scan_id).to_numpy()
        h["x"] = h.order.to_numpy()
        h["xlabel"] = [f"scan {o}" + (f"\n({d:+.0f} d from RT)" if np.isfinite(d) else "") for o, d in zip(h.order, rtd)]
        xname = "scan (UCSF supplies one consecutive pair)"
        prev = f"{sid}_time{int(tp) - 1}" if int(tp) > 1 else ""
    if prev:
        assert prev in set(h.scan_id) and prev != scan_id, "previous scan must be in the past-only history"
    when = {sid: (f"day {lab} from RT start" if xname == "days from RT start" else lab.replace("\n", " "))
            for sid, lab in zip(h.scan_id, h.xlabel)}
    return {"prev": prev, "hist": h, "xname": xname, "position": len(h), "time": when[scan_id],
            "time_prev": when.get(prev, "")}


# ------------------------------------------------------------------ drawing
def _window(img: np.ndarray, brain: np.ndarray) -> tuple[float, float]:
    v = img[brain & (img > 0)]
    return (float(np.percentile(v, 0.5)), float(np.percentile(v, 99.5))) if v.size else (0.0, 1.0)


def _crop(*masks2d) -> tuple[slice, slice]:
    u = np.zeros_like(masks2d[0], bool)
    for m in masks2d:
        u |= m
    if not u.any():
        return slice(None), slice(None)
    r, c = np.where(u)
    pad = 6
    return (slice(max(r.min() - pad, 0), r.max() + pad + 1), slice(max(c.min() - pad, 0), c.max() + pad + 1))


def _image(ax, scan: Scan, k: int, seq: str, comps, crop, title: str, note: str = ""):
    img = scan.t1c if seq == "t1c" else scan.flair
    lo, hi = _window(img, scan.brain)
    sl = to_display(img[:, :, k])[crop]
    ax.imshow(sl, cmap="gray", vmin=lo, vmax=hi, interpolation="nearest")
    for c in comps:
        m = to_display(scan.comp[c][:, :, k])[crop]
        if m.any():
            ax.contour(m.astype(float), levels=[0.5], colors=COLOR[c], linestyles=STYLE[c], linewidths=1.8)
    ax.set_xticks([]), ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title, fontsize=12, color=INK, loc="left")
    kw = dict(color="white", fontsize=11, weight="bold", transform=ax.transAxes)
    ax.text(0.015, 0.985, "R", ha="left", va="top", **kw)  # corners: never over the lesion (crop is padded)
    ax.text(0.985, 0.985, "L", ha="right", va="top", **kw)
    if note:
        ax.text(0.5, 0.10, note, ha="center", va="bottom", fontsize=10.5, color="black", transform=ax.transAxes,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9))


def _blank(ax, title, text):
    ax.set_xticks([]), ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#c8ced6")
    ax.set_title(title, fontsize=12, color=INK, loc="left")
    ax.text(0.5, 0.5, text, ha="center", va="center", fontsize=11, color=MUTED, transform=ax.transAxes, wrap=True)


def _note(scan: Scan, rule: str) -> str:
    if not scan.seg_ok:
        return "segmentation empty or missing"
    if not scan.comp["et"].any():
        return "no enhancing tumour segmented"
    return ""


def render(cohort: str, scan_id: str, out: Path) -> dict:
    t0 = time.time()
    ctx = context(cohort, scan_id)
    names = NAME_LUMIERE if cohort == "lumiere" else NAME
    t1_comps = [c for c in ("et", "netc", "rc") if c in LABELS[cohort]]
    cur = load_scan(cohort, scan_id)
    info = {"cohort": cohort, "scan_id": scan_id, "n_history": len(ctx["hist"]), "prev_scan_id": ctx["prev"]}
    fig = plt.figure(figsize=(16, 10.4), dpi=100)
    gs = fig.add_gridspec(2, 4, height_ratios=[1.0, 0.68], hspace=0.30, wspace=0.05, left=0.045, right=0.985,
                          top=0.84, bottom=0.135)
    axA1, axA2, axB1, axB2 = (fig.add_subplot(gs[0, i]) for i in range(4))
    axC = fig.add_subplot(gs[1, :3])
    axT = fig.add_subplot(gs[1, 3])
    fig.text(0.03, 0.968, "Segmentation of this scan (automatic; indicative volumes, not RANO)", fontsize=16,
             weight="bold", color=INK)
    fig.text(0.03, 0.937, f"{cohort.upper()}  |  this scan: {ctx['time']}"
             + ("" if ctx["time"].startswith("scan") else f" (scan {ctx['position']})") +
             f"; no later scans shown  |  {SOURCE[cohort]}  |  radiological convention: patient's right on image left "
             "(R / L marked), anterior at top", fontsize=11, color=MUTED)
    if cur is None:
        for a in (axA1, axA2):
            _blank(a, "A  This scan", "images not available")
        prev = load_scan(cohort, ctx["prev"]) if ctx["prev"] else None
        if prev is None:
            for a in (axB1, axB2):
                _blank(a, "B  Previous scan", "no previous scan" if not ctx["prev"] else "not available")
        else:
            kp, prule, _ = choose_slice(prev.comp, prev.brain)
            pcrop = _crop(to_display(prev.brain[:, :, kp]))
            _image(axB1, prev, kp, "t1c", t1_comps, pcrop, f"B  Previous scan: post-contrast T1\n"
                   f"own slice {kp + 1}, {prule}", _note(prev, ""))
            _image(axB2, prev, kp, "flair", ["snfh"], pcrop, f"B  Previous scan: FLAIR\n{ctx['time_prev']}")
        info.update(prev_loaded=prev is not None, coregistered=False, prev_slice=kp if prev is not None else None)
        info.update(slice=-1, rule="images not available")
        k = None
    else:
        k, rule, area = choose_slice(cur.comp, cur.brain)
        info.update(slice=k, rule=rule, slice_area_mm2=area, seg_ok=cur.seg_ok)
        prev = load_scan(cohort, ctx["prev"]) if ctx["prev"] else None
        coreg, kp, d3 = False, None, float("nan")
        if prev is not None:
            if prev.t1c.shape == cur.t1c.shape:
                d3 = dice(prev.brain, cur.brain)
            coreg = bool(np.isfinite(d3) and d3 >= COREG_DICE)
            kp, prule, _ = (k, "", 0.0) if coreg else choose_slice(prev.comp, prev.brain)
        info.update(prev_loaded=prev is not None, brain_dice=d3, coregistered=coreg, prev_slice=kp)
        crop = _crop(to_display(cur.brain[:, :, k]), *([to_display(prev.brain[:, :, k])] if coreg else []))
        sub = f"axial {k + 1}/{cur.t1c.shape[2]}, {rule}"
        _image(axA1, cur, k, "t1c", t1_comps, crop, f"A  This scan: post-contrast T1\n{sub}", _note(cur, rule))
        _image(axA2, cur, k, "flair", ["snfh"], crop, "A  This scan: FLAIR\nsame slice, SNFH outline")
        if not ctx["prev"]:
            for a in (axB1, axB2):
                _blank(a, "B  Previous scan", "no previous scan")
        elif prev is None:
            for a in (axB1, axB2):
                _blank(a, "B  Previous scan", "previous scan's images\nnot available")
        else:
            pcrop = crop if coreg else _crop(to_display(prev.brain[:, :, kp]))
            how = (f"same slice, atlas space (brain Dice {d3:.2f})" if coreg else
                   f"NOT co-registered: own slice {kp + 1}, {prule}")
            _image(axB1, prev, kp, "t1c", t1_comps, pcrop, f"B  Previous scan: post-contrast T1\n{how}",
                   _note(prev, ""))
            _image(axB2, prev, kp, "flair", ["snfh"], pcrop, f"B  Previous scan: FLAIR\n{ctx['time_prev']}")
        # volumes in the table must be the volumes of the mask shown
        row = ctx["hist"].iloc[-1]
        diffs = [abs(cur.comp[c].sum() / 1000.0 - row[f"{c}_cc"]) for c in LABELS[cohort]
                 if np.isfinite(row[f"{c}_cc"])]
        info["max_volume_diff_cc"] = float(max(diffs)) if diffs else float("nan")

    # Panel C: past-only history
    h = ctx["hist"]
    assert h.scan_id.iat[-1] == scan_id and (h.order <= h.order.iat[-1]).all()
    comps = [c for c in COMP if c in LABELS[cohort]]
    for c in comps[::-1]:  # ET drawn last (on top)
        y = h[f"{c}_cc"].to_numpy(float)
        axC.plot(h.x, y, STYLE[c], marker=MARK[c], color=COLOR[c], lw=2, ms=8, label=names[c],
                 mec="white", mew=1)
    axC.axvline(h.x.iat[-1], color=MUTED, lw=1, ls="-", zorder=0)
    vals = h[[f"{c}_cc" for c in comps]].to_numpy(float)
    ymax = float(np.nanmax(vals)) if np.isfinite(vals).any() else 0.0
    if np.isfinite(vals).any() and not np.isfinite(vals[-1]).any():
        axC.text(h.x.iat[-1], 0.5, "no volumes for\nthis scan ", ha="right", va="bottom", fontsize=10.5, color=MUTED,
                 transform=axC.get_xaxis_transform())
    if not np.isfinite(vals).any():
        axC.text(0.5, 0.5, "no volumes: segmentation empty or missing", ha="center", va="center", fontsize=11,
                 color=MUTED, transform=axC.transAxes)
    ymax = 1.0 if ymax <= 0 else ymax
    axC.set_ylim(0, ymax * 1.18)
    labs = h.xlabel.tolist()
    labs[-1] = labs[-1] + "\nTHIS SCAN"
    xs = h.x.to_numpy(float)
    crowded = len(h) > 1 and np.diff(xs).min() < 0.07 * (xs.max() - xs.min())
    rot = 0 if len(h) <= 8 and not crowded else 40
    axC.set_xticks(h.x.to_numpy(), labs, fontsize=10, rotation=rot, ha="center" if rot == 0 else "right",
                   rotation_mode="anchor")
    axC.get_xticklabels()[-1].set_fontweight("bold")
    if len(h) == 1:
        axC.set_xlim(h.x.iat[0] - 1, h.x.iat[0] + 1)
    axC.set_xlabel(ctx["xname"], fontsize=11, color=MUTED)
    axC.set_ylabel("volume (cc)", fontsize=11, color=MUTED)
    axC.set_title("C  Compartment volumes, this scan and earlier scans only", fontsize=12, color=INK, loc="left")
    axC.grid(axis="y", color="#e4e7eb", lw=0.8)
    for s in ("top", "right"):
        axC.spines[s].set_visible(False)
    # table to the right of C: this scan and the previous one
    axT.axis("off")
    pr = h[h.scan_id.eq(ctx["prev"])]
    lines = [("volume", "this scan", "previous")]
    for c in comps:
        v = row_v = h[f"{c}_cc"].iat[-1]
        p = pr[f"{c}_cc"].iat[0] if len(pr) else np.nan
        f = lambda z: "n/a" if not np.isfinite(z) else f"{z:.1f} cc"
        lines.append((names[c].split(" (")[0], f(v), f(p) if len(pr) else "-"))
    for i, (a, b, c) in enumerate(lines):  # the table doubles as the legend of panel C
        w = "bold" if i == 0 else "normal"
        yy = 0.88 - i * 0.13
        if i:
            cc = comps[i - 1]
            axT.plot([0.0, 0.09], [yy + 0.03] * 2, STYLE[cc], color=COLOR[cc], lw=2, transform=axT.transAxes,
                     clip_on=False)
            axT.plot([0.045], [yy + 0.03], MARK[cc], color=COLOR[cc], ms=7, mec="white", transform=axT.transAxes,
                     clip_on=False)
        axT.text(0.12, yy, a, fontsize=11, weight=w, color=INK, transform=axT.transAxes)
        axT.text(0.76, yy, b, fontsize=11, weight=w, color=INK, ha="right", transform=axT.transAxes)
        axT.text(1.0, yy, c, fontsize=11, weight=w, color=INK, ha="right", transform=axT.transAxes)
    foot = "Volumes from the full 3-D masks." + (" No separate cavity label in DeepBraTumIA." if cohort == "lumiere" else "")
    axT.text(0.0, 0.88 - len(lines) * 0.13 - 0.02, foot, fontsize=9.5, color=MUTED, transform=axT.transAxes, wrap=True,
             va="top")
    handles = [Line2D([], [], color=COLOR[c], ls=STYLE[c], lw=2.2, label=names[c]) for c in t1_comps + ["snfh"]]
    fig.text(0.03, 0.904, "Outlines:", fontsize=11, color=INK, weight="bold", va="center")
    fig.legend(handles=handles, loc="center left", bbox_to_anchor=(0.085, 0.904), ncol=len(handles), fontsize=11,
               frameon=False, handlelength=3.2, columnspacing=2.0)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=100, facecolor="white")
    plt.close(fig)
    info["seconds"] = round(time.time() - t0, 2)
    info["path"] = str(out)
    return info


def figure(scan_id: str, cohort: str) -> Path:
    """Render the figure of one scan and return its path (outputs/results/analyses/system/figures/<cohort>/<id>.png)."""
    assert cohort in COHORTS, cohort
    out = OUT / cohort / f"{scan_id}.png"
    render(cohort, scan_id, out)
    return out


def _job(a):
    cohort, sid = a
    try:
        return render(cohort, sid, OUT / cohort / f"{sid}.png")
    except Exception as e:  # recorded in the manifest, never silently skipped
        return {"cohort": cohort, "scan_id": sid, "error": f"{type(e).__name__}: {e}"}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--examples", action="store_true")
    ap.add_argument("--cohort", choices=COHORTS)
    ap.add_argument("--scan")
    ap.add_argument("--workers", type=int, default=min(6, os.cpu_count() or 1))
    a = ap.parse_args(argv)
    if a.scan:
        print(figure(a.scan, a.cohort))
        return
    jobs = [(c, s) for c in ((a.cohort,) if a.cohort else COHORTS) for s in population(c)]
    if a.examples:
        jobs = [(c, s) for c in COHORTS for s in pick_examples(c)]
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(_job, jobs, chunksize=2))
    m = pd.DataFrame(rows)
    name = "manifest_examples.csv" if a.examples else "manifest.csv"
    OUT.mkdir(parents=True, exist_ok=True)
    m.to_csv(OUT / name, index=False)
    print(f"{len(m)} scans in {time.time() - t0:.0f} s with {a.workers} workers -> {OUT}")
    print(m.groupby("cohort").size().to_string())
    if "error" in m:
        print("errors:", m.error.notna().sum())
        print(m[m.error.notna()][["cohort", "scan_id", "error"]].to_string())


def pick_examples(cohort: str) -> list[str]:
    """Two deterministic examples per cohort: the longest history with a previous scan, and an edge case (no ET, or
    else no previous scan)."""
    pop = population(cohort)
    ctxs = {s: context(cohort, s) for s in pop}
    with_prev = sorted((s for s in pop if ctxs[s]["prev"]), key=lambda s: (-ctxs[s]["position"], s))
    no_et = [s for s in pop if ctxs[s]["hist"].et_cc.iat[-1] == 0]
    no_prev = [s for s in pop if not ctxs[s]["prev"]]
    edge = (no_et or no_prev or pop)[0]
    return [with_prev[0], edge] if with_prev and with_prev[0] != edge else [pop[0], edge]

if __name__ == "__main__":
    main()
