"""Figure 1: the task and the method, drawn in the visual language of Tak et al. 2025 (NEJM AI, Figure 1): database and
patient icons, one patient's real scans on a time axis, the network as stacked slabs, models as network glyphs.
(a) One MU-Glioma-Post patient's follow-up against the time since radiotherapy; (b) PRISM's segmenter, the BraTS 2024
post-treatment ensemble (Ferreira et al., arXiv:2411.04632; facts read from its container: 3 architectures x 2 training
sets x 5 folds, equal-weight mean of the probability maps, > 0.5 per region, WT and RC parts < 50 voxels removed); (c) PRISM at one follow-up scan, from inputs to the checked report, with the collation
of every value into the record as its own stage; (d) the evaluation protocol.

Panel (a) reads the public MU-Glioma-Post images, masks and clinical workbook (data/mu-glioma-post, see
prism/config.py), and PRISM's own segmentation of each scan by the BraTS 2024 ensemble
(outputs/features/seg_brats24/mu, written by prism/features/reseg_brats24.py; docs/results/SEGMENTER_SWITCH.md). Weeks
after radiotherapy, enhancing volumes and the label of each scan are computed here from those files with the paper's
label rule; no model score is shown. Panels (b)-(d) are a methods schematic as specified in the Methods; the models in
(c) are PRISM's current models (the stratified and offset forms of docs/results/ADOPT_AB.md were not adopted). The input slices
in (b) and (c) are the patient's scans from (a). Colour follows the score as in every figure
(scripts/figure_style.py); structure is black.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

import figure_style as st

W = 180.0                          # drawing units (about 1 mm each)
HA, HB, HC, HD = 54.0, 60.0, 66.0, 34.0   # panel heights, top to bottom
H = HA + HB + HC + HD
TB, TC, TD = H - HA, H - HA - HB, HD       # top edges of panels (b), (c), (d)
REPO = Path(__file__).resolve().parents[1]
MU = REPO / "data" / "mu-glioma-post"
PATIENT = "PatientID_0204"        # early enhancement that resolved, then progression
ET_LABEL = 3                      # enhancing tumour in the released masks (prism/config.py)
CONTOUR = "#F2C14E"               # PRISM's segmentation (BraTS 2024 ensemble)
RELEASED = "#7FD3F0"              # the mask released with the cohort, for comparison
SEG = REPO / "outputs" / "features" / "seg_brats24" / "mu"   # BraTS24 maps: 1 NETC, 2 SNFH, 3 ET, 4 RC
MONO = "DejaVu Sans Mono"
BLACK = "#000000"
DB = "#3B3F47"                    # database and patient icons (Tak's dark grey)


def load_clinical():
    import pandas as pd
    return pd.read_excel(MU / "MU-Glioma-Post_ClinicalData-July2025.xlsx", sheet_name="MU Glioma Post")


def scan_days(row) -> dict[int, float]:
    """{timepoint: days from diagnosis to the MRI} from one clinical-workbook row."""
    import re
    import pandas as pd
    out = {}
    for c in row.index:
        if (m := re.search(r"Timepoint_(\d+)", str(c))):
            day = pd.to_numeric(row[c], errors="coerce")
            if pd.notna(day):
                out[int(m.group(1))] = float(day)
    return out


def scan_slice(patient: str, n: int) -> dict:
    """The T1c axial slice with most enhancement (the visits are not co-registered), cropped to the brain, with its
    enhancing mask, PRISM's enhancing mask, both volumes (cc) and the lesion centre (for the pointer arrow)."""
    import nibabel as nib
    d = MU / "MU-Glioma-Post" / patient / f"Timepoint_{n}"
    t1c = np.asarray(nib.load(str(d / f"{patient}_Timepoint_{n}_brain_t1c.nii.gz")).dataobj, dtype=np.float32)
    lesion = np.asarray(nib.load(str(d / f"{patient}_Timepoint_{n}_tumorMask.nii.gz")).dataobj)
    et = lesion == ET_LABEL
    pick = et if et.any() else (lesion > 0) if (lesion > 0).any() else (t1c > 0)
    z = int(np.argmax(pick.sum(axis=(0, 1))))
    img = t1c[:, :, z]
    ys, xs = np.nonzero(img > 0)
    cy, cx = (ys.min() + ys.max()) // 2, (xs.min() + xs.max()) // 2
    half = max(ys.max() - ys.min(), xs.max() - xs.min()) // 2 + 4
    lo, hi = np.percentile(img[img > 0], [1, 99.5])
    crop = lambda a: np.rot90(a[max(cy - half, 0):cy + half, max(cx - half, 0):cx + half])   # anterior up
    net = np.asarray(nib.load(str(SEG / patient / f"Timepoint_{n}.nii.gz")).dataobj) == ET_LABEL
    msk, netc = crop(et[:, :, z]), crop(net[:, :, z])
    target = netc if netc.any() else msk
    ty, tx = (np.argwhere(target).mean(axis=0) if target.any() else (msk.shape[0] / 2, msk.shape[1] / 2))
    return dict(img=crop(np.clip((img - lo) / (hi - lo), 0, 1)), msk=msk, net=netc,
                et_cc=float(et.sum()) / 1000, net_cc=float(net.sum()) / 1000,
                centre=(tx / msk.shape[1], 1 - ty / msk.shape[0]))


def sequence_slices(patient: str, n: int) -> dict:
    """The four sequences of one scan at its slice with most enhancement (released mask, as in scan_slice), cropped
    alike, and PRISM's label map on that slice (3 enhancing, 1 necrosis, 2 FLAIR hyperintensity)."""
    import nibabel as nib
    d = MU / "MU-Glioma-Post" / patient / f"Timepoint_{n}"
    vol = {s: np.asarray(nib.load(str(d / f"{patient}_Timepoint_{n}_brain_{s}.nii.gz")).dataobj, dtype=np.float32)
           for s in ("t2f", "t1c", "t1n", "t2w")}
    lesion = np.asarray(nib.load(str(d / f"{patient}_Timepoint_{n}_tumorMask.nii.gz")).dataobj)
    z = int(np.argmax((lesion == ET_LABEL).sum(axis=(0, 1))))
    lab = np.asarray(nib.load(str(SEG / patient / f"Timepoint_{n}.nii.gz")).dataobj)[:, :, z]
    ys, xs = np.nonzero(vol["t1c"][:, :, z] > 0)
    cy, cx = (ys.min() + ys.max()) // 2, (xs.min() + xs.max()) // 2
    half = max(ys.max() - ys.min(), xs.max() - xs.min()) // 2 + 4
    crop = lambda a: np.rot90(a[max(cy - half, 0):cy + half, max(cx - half, 0):cx + half])
    out = {}
    for s, v in vol.items():
        img = v[:, :, z]
        lo, hi = np.percentile(img[img > 0], [1, 99.5])
        out[s] = crop(np.clip((img - lo) / (hi - lo), 0, 1))
    out["label"] = crop(lab)
    return out


def patient_scans():
    """The patient's post-radiotherapy scans up to and including the progression scan: weeks after RT end, enhancing
    volume (cc), label, and a T1c slice with its enhancing mask, cropped around the lesion. Label rule as in the paper
    (Section 2.1): the progression scan is the first scan on or after the documented progression date; a scan without
    progression must be followed by >= 120 days without progression; any other scan is not labelled."""
    clin = load_clinical()
    row = clin[clin["Patient_ID"] == PATIENT].iloc[0]
    rt = float(row["Number of days from Diagnosis to Radiation Therapy end date"])
    prog = float(row["Number of days from Diagnosis to date of First Progression"])
    scans = []
    for n, day in sorted(scan_days(row).items()):
        if day < rt or not (MU / "MU-Glioma-Post" / PATIENT / f"Timepoint_{n}").exists():
            continue
        label = ("Progression" if day >= prog else
                 "No progression" if prog - day >= 120 else "Not labelled")
        scans.append(dict(tp=n, weeks=(day - rt) / 7, label=label, **scan_slice(PATIENT, n)))
        if day >= prog:
            break
    return scans


SEQ_LABELS = [("t2f", "FLAIR"), ("t1c", "T1c"), ("t1n", "T1"), ("t2w", "T2")]
LABEL_RGB = {3: "#F2C14E", 1: "#D65F5F", 2: "#7BC67B", 4: "#F29CB7"}   # enhancing, necrosis, FLAIR, cavity


class Canvas:
    """One full-figure axes in drawing units, with the primitives and Tak-style icons used by every panel."""

    def __init__(self):
        self.fig = plt.figure(figsize=(st.WIDTH, st.WIDTH * H / W))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set(xlim=(0, W), ylim=(0, H))
        self.ax.axis("off")

    # ---------------------------------------------------------------- primitives
    def text(self, x, y, s, size=6.0, colour=st.INK, **kw):
        kw.setdefault("ha", "left"); kw.setdefault("va", "top")
        return self.ax.text(x, y, s, fontsize=size, color=colour, linespacing=1.3, zorder=6, **kw)

    def arrow(self, a, b, colour=BLACK, lw=0.7, style="-|>", ms=5.5, **kw):
        self.ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=ms, color=colour, lw=lw,
                                          shrinkA=0, shrinkB=0, zorder=4, **kw))

    def line(self, xs, ys, colour=BLACK, lw=0.7, **kw):
        kw.setdefault("zorder", 3)
        self.ax.plot(xs, ys, color=colour, lw=lw, solid_capstyle="butt", **kw)

    def box(self, x0, y0, x1, y1, edge=BLACK, face="white", lw=0.7, ls="-", r=1.3, z=2):
        self.ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle=f"round,pad=0,rounding_size={r}",
                                         fc=face, ec=edge, lw=lw, ls=ls, zorder=z))

    def image(self, x, y, w, h, img, **kw):
        iax = self.fig.add_axes([x / W, y / H, w / W, h / H])
        iax.imshow(img, cmap="gray", vmin=0, vmax=1, interpolation="bilinear", **kw)
        iax.set_xticks([]); iax.set_yticks([])
        for sp in iax.spines.values():
            sp.set_visible(False)
        return iax

    def chevron(self, x, y, s=3.0, colour=BLACK, lw=1.1):
        self.line([x, x + s * 0.7, x], [y + s, y, y - s], colour, lw)

    def header(self, top, letter, heading):
        st.panel_header(self.fig, (top - 0.8) / H, letter, heading)

    def rule(self, y):
        self.line([1.0, W - 1.0], [y, y], st.RULE, 0.5)

    # ---------------------------------------------------------------- icons (after Tak et al., Figure 1)
    def database(self, cx, cy, w, h, colour=DB, filled=True):
        """A cylinder with three bands."""
        e = w * 0.32
        face, edge = (colour, colour) if filled else ("white", colour)
        band = "white" if filled else colour
        self.ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, fc=face, ec="none", zorder=3))
        self.line([cx - w / 2, cx - w / 2], [cy - h / 2, cy + h / 2], edge, 0.9, zorder=3)
        self.line([cx + w / 2, cx + w / 2], [cy - h / 2, cy + h / 2], edge, 0.9, zorder=3)
        self.ax.add_patch(Ellipse((cx, cy - h / 2), w, e, fc=face, ec=edge, lw=0.9, zorder=2))
        for k in (1, 2):
            yk = cy - h / 2 + k * h / 3
            t = np.linspace(np.pi, 2 * np.pi, 40)
            self.ax.plot(cx + w / 2 * np.cos(t), yk + e / 2 * np.sin(t), color=band, lw=0.9, zorder=4)
        self.ax.add_patch(Ellipse((cx, cy + h / 2), w, e, fc=face, ec=band if filled else edge, lw=0.9, zorder=4))

    def person(self, cx, cy, s, colour=DB, filled=True):
        """A head and shoulders, height about 2 s."""
        fc = colour if filled else "white"
        self.ax.add_patch(Circle((cx, cy + 0.62 * s), 0.30 * s, fc=fc, ec=colour, lw=0.7, zorder=4))
        self.ax.add_patch(FancyBboxPatch((cx - 0.38 * s, cy - 0.85 * s), 0.76 * s, 1.2 * s,
                                         boxstyle=f"round,pad=0,rounding_size={0.3 * s}", fc=fc, ec=colour,
                                         lw=0.7, zorder=4))

    def crowd(self, x0, y0, cols, rows, s, dx, dy, colour=DB):
        for r in range(rows):
            for c in range(cols):
                off = dx / 2 if r % 2 else 0.0
                if r % 2 and c == cols - 1:
                    continue
                self.person(x0 + c * dx + off, y0 + r * dy, s, colour)

    def network(self, cx, cy, s, colour=BLACK):
        """Tak's model glyph: seven nodes, a small graph."""
        pts = {"l1": (-1.0, 0.5), "l2": (-1.0, -0.5), "m1": (0.0, 1.0), "m2": (0.0, 0.0), "m3": (0.0, -1.0),
               "r": (1.0, 0.0), "t": (0.0, 0.0)}
        edges = [("l1", "m1"), ("l1", "m2"), ("l2", "m2"), ("l2", "m3"), ("m1", "r"), ("m2", "r"), ("m3", "r"),
                 ("l1", "l2"), ("m1", "m2"), ("m2", "m3")]
        for a, b in edges:
            (xa, ya), (xb, yb) = pts[a], pts[b]
            self.line([cx + s * xa, cx + s * xb], [cy + s * ya, cy + s * yb], colour, 0.8, zorder=4)
        for k, (x, y) in pts.items():
            if k != "t":
                self.ax.add_patch(Circle((cx + s * x, cy + s * y), 0.24 * s, fc=colour, ec="none", zorder=5))

    def slab(self, x, y, w, h, depth, colour, alpha=0.85):
        """A layer drawn as a skewed, rounded-looking plate (Tak's ResNet slabs): front face plus top and side."""
        d = depth
        front = [(x, y), (x + w, y + d * 0.35), (x + w, y + h + d * 0.35), (x, y + h)]
        self.ax.add_patch(Polygon(front, closed=True, fc=colour, ec="white", lw=0.4, alpha=alpha, zorder=4))

    def vector(self, x, y, n, cw, ch, colour, edge=None):
        """A feature vector as a column of cells (Tak's t1, t2, t3 stacks)."""
        for k in range(n):
            self.ax.add_patch(Rectangle((x, y - (k + 1) * ch), cw, ch, fc=colour, ec=edge or BLACK, lw=0.4,
                                        zorder=5))

    def document(self, x, y, w, h, colour=BLACK, lines=4, face="white"):
        """A page with a folded corner and text lines."""
        f = min(w, h) * 0.28
        pts = [(x, y), (x + w, y), (x + w, y + h - f), (x + w - f, y + h), (x, y + h)]
        self.ax.add_patch(Polygon(pts, closed=True, fc=face, ec=colour, lw=0.8, zorder=4))
        self.line([x + w - f, x + w - f, x + w], [y + h, y + h - f, y + h - f], colour, 0.6, zorder=5)
        for k in range(lines):
            yk = y + h - f - 1.2 - k * (h - f - 1.6) / max(lines, 1)
            self.line([x + 0.18 * w, x + (0.82 if k % 3 else 0.6) * w], [yk, yk], colour, 0.5, zorder=5)

    def funnel(self, cx, top, w, h, colour=BLACK):
        pts = [(cx - w / 2, top), (cx + w / 2, top), (cx + w * 0.1, top - h * 0.62), (cx + w * 0.1, top - h),
               (cx - w * 0.1, top - h), (cx - w * 0.1, top - h * 0.62)]
        self.ax.add_patch(Polygon(pts, closed=True, fc="white", ec=colour, lw=0.9, zorder=4))

    def shield(self, cx, cy, s, colour=BLACK):
        pts = [(cx - s, cy + s), (cx + s, cy + s), (cx + s, cy), (cx, cy - 1.3 * s), (cx - s, cy)]
        self.ax.add_patch(Polygon(pts, closed=True, fc="white", ec=colour, lw=0.9, zorder=4, joinstyle="round"))
        self.line([cx - 0.45 * s, cx - 0.1 * s, cx + 0.5 * s], [cy + 0.05 * s, cy - 0.35 * s, cy + 0.5 * s],
                  colour, 1.1, zorder=5)

    def lock(self, cx, cy, s, colour=BLACK):
        t = np.linspace(0, np.pi, 30)
        self.ax.plot(cx + 0.55 * s * np.cos(t), cy + 0.35 * s + 0.6 * s * np.sin(t), color=colour, lw=1.2,
                     zorder=4)
        self.line([cx - 0.55 * s, cx - 0.55 * s], [cy, cy + 0.35 * s], colour, 1.2, zorder=4)
        self.line([cx + 0.55 * s, cx + 0.55 * s], [cy, cy + 0.35 * s], colour, 1.2, zorder=4)
        self.ax.add_patch(FancyBboxPatch((cx - 0.85 * s, cy - 0.9 * s), 1.7 * s, 1.2 * s,
                                         boxstyle=f"round,pad=0,rounding_size={0.15 * s}", fc=colour, ec="none",
                                         zorder=5))
        self.ax.add_patch(Circle((cx, cy - 0.3 * s), 0.16 * s, fc="white", ec="none", zorder=6))

    def chat(self, cx, cy, w, h, colour=BLACK):
        """A speech bubble with three dots: the language model's writing step."""
        self.box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, edge=colour, r=1.6, z=4, lw=0.9)
        self.ax.add_patch(Polygon([(cx - w * 0.25, cy - h / 2 + 0.05), (cx - w * 0.38, cy - h / 2 - 2.0),
                                   (cx - w * 0.05, cy - h / 2 + 0.05)], closed=True, fc="white", ec="none",
                                  zorder=5))
        self.line([cx - w * 0.25, cx - w * 0.38, cx - w * 0.05], [cy - h / 2, cy - h / 2 - 2.0, cy - h / 2],
                  colour, 0.9, zorder=5)
        for k in (-1, 0, 1):
            self.ax.add_patch(Circle((cx + k * w * 0.2, cy), 0.55, fc=colour, ec="none", zorder=6))

    def scan(self, x, y, s, sc, pointer=False):
        iax = self.image(x, y, s, s, sc["img"])
        if sc["msk"].any():
            iax.contour(sc["msk"].astype(float), levels=[0.5], colors=[RELEASED], linewidths=0.45,
                        linestyles="--")
        if sc["net"].any():
            iax.contour(sc["net"].astype(float), levels=[0.5], colors=[CONTOUR], linewidths=0.6)
        if pointer:                                      # Tak's lesion arrow, drawn from the top of the image
            fx, fy = sc["centre"][0], sc["centre"][1]
            iax.annotate("", xy=(fx, fy + 0.07), xytext=(fx - 0.05, 1.0), xycoords="axes fraction",
                         arrowprops=dict(arrowstyle="-|>", color="white", lw=0.9, mutation_scale=6))
        return iax


# ==================================================================== (a) one patient's follow-up
def panel_a(c: Canvas, scans) -> None:
    top = H
    c.header(top, "a", "MU-Glioma-Post: one patient's follow-up after radiotherapy")
    mid = top - 24.0
    c.database(10.0, mid, 10.0, 14.0)
    c.text(10.0, mid - 9.6, "MU-Glioma-Post", size=5.6, ha="center", weight="bold")
    c.chevron(18.0, mid, 3.2)
    c.crowd(23.6, mid - 9.5, 4, 4, 1.7, 4.4, 6.0)
    c.text(30.2, mid - 13.4, "126 grade 4\npatients", size=5.4, ha="center", colour=st.MUTED)
    # dashed bracket from the crowd to one patient's timeline
    c.line([39.5, 42.0, 42.0], [mid + 2.0, mid + 2.0, top - 9.0], DB, 0.6, ls=(0, (2, 1.5)))
    c.line([39.5, 42.0, 42.0], [mid - 2.0, mid - 2.0, top - 41.0], DB, 0.6, ls=(0, (2, 1.5)))
    c.line([42.0, 45.0], [top - 9.0, top - 9.0], DB, 0.6, ls=(0, (2, 1.5)))
    c.line([42.0, 45.0], [top - 41.0, top - 41.0], DB, 0.6, ls=(0, (2, 1.5)))

    n = len(scans)
    iw, gap = 19.0, 7.5
    ix0 = 52.0
    iy0 = top - 15.0 - iw
    xs = [ix0 + k * (iw + gap) for k in range(n)]
    # intervals between scans, bracketed above the images (Tak's "161 Days")
    by = top - 12.0
    for k in range(1, n):
        a, b = xs[k - 1] + iw / 2, xs[k] + iw / 2
        c.line([a, b], [by, by], BLACK, 0.6)
        for x in (a, b):
            c.line([x, x], [by - 0.7, by + 0.7], BLACK, 0.6)
        c.text((a + b) / 2, by + 0.6, f"{scans[k]['weeks'] - scans[k - 1]['weeks']:.0f} weeks", size=5.4,
               ha="center", va="bottom")
    for k, sc in enumerate(scans):
        x = xs[k]
        weight = "bold" if sc["label"] == "Progression" else "normal"
        style = "italic" if sc["label"] == "Not labelled" else "normal"
        colour = st.MUTED if sc["label"] == "Not labelled" else BLACK
        c.text(x + iw / 2, top - 6.0, sc["label"], size=6.2, ha="center", weight=weight, style=style,
               colour=colour)
        c.scan(x, iy0, iw, sc, pointer=True)
        c.text(x + iw / 2, iy0 - 1.0, f"enhancing {sc['net_cc']:.1f} cc ({sc['et_cc']:.1f})", size=5.2,
               ha="center", colour=st.MUTED)
    # the time axis, to scale, with the first 12 weeks shaded and "Follow-up" style labels
    ty = iy0 - 7.5
    tx0, tx1 = 47.0, W - 3.0
    wmax = 44.0
    wx = lambda w: ix0 + (W - 8.0 - ix0) * w / wmax
    c.ax.add_patch(Rectangle((wx(0), ty - 1.3), wx(12) - wx(0), 2.6, fc=st.tint(st.HIST, 0.75), ec="none",
                             zorder=2))
    c.text(wx(6), ty + 1.6, "first 12 weeks", size=5.0, colour=st.HIST, ha="center", va="bottom")
    c.arrow((tx0, ty), (tx1, ty), BLACK, 0.8, ms=6)
    for k, sc in enumerate(scans):
        c.line([xs[k] + iw / 2, wx(sc["weeks"])], [iy0 - 4.2, ty + 0.9], st.RULE, 0.5, zorder=1)
        c.ax.add_patch(Circle((wx(sc["weeks"]), ty), 0.85, fc=BLACK, ec="white", lw=0.3, zorder=5))
        c.text(wx(sc["weeks"]), ty - 1.6, f"{sc['weeks']:.1f} wk", size=5.2, ha="center")
    c.text(wx(0), ty - 1.6, "end of RT", size=5.0, ha="center", colour=st.MUTED)
    c.text(tx1, ty - 4.6, "weeks after the end of radiotherapy", size=5.2, colour=st.MUTED, ha="right")
    # legend
    c.line([2.4, 5.4], [top - 46.0, top - 46.0], CONTOUR, 1.2)
    c.text(6.2, top - 45.0, "PRISM's segmenter", size=5.0, colour=st.MUTED)
    c.line([2.4, 5.4], [top - 49.0, top - 49.0], RELEASED, 0.9, ls="--")
    c.text(6.2, top - 48.0, "released mask (cc)", size=5.0, colour=st.MUTED)
    c.rule(TB + 0.6)


# ==================================================================== (b) the segmenter
ARCHS = [("nnU-Net", "convolutional U-Net"), ("Swin UNETR", "transformer encoder"),
         ("MedNeXt-L", "ConvNeXt-style, kernel 5")]


def unet_glyph(c: Canvas, x, y, colour, w=15.0, h=8.0):
    """A small U-Net: plates shrinking to the bottleneck and growing back, with one skip arc."""
    hs = [1.0, 0.72, 0.48, 0.72, 1.0]
    step = w / len(hs)
    for i, f in enumerate(hs):
        hh = h * f
        col = st.tint(colour, 0.25 + 0.45 * (1 - f)) if i < 3 else st.tint(colour, 0.78)
        c.slab(x + i * step, y - hh / 2, step * 0.62, hh, 1.6, col, alpha=1.0)
    t = np.linspace(0, np.pi, 30)
    rx = (w - step) / 2
    c.ax.plot(x + step * 0.3 + rx - rx * np.cos(t), y + h / 2 + 1.0 + 1.2 * np.sin(t), color=st.MUTED, lw=0.4,
              ls=(0, (1.6, 1.0)), zorder=3)


def mednext_glyph(c: Canvas, x, y, colour, w=15.0, h=8.0):
    """MedNeXt: the same U shape, each stage an inverted bottleneck (narrow, wide, narrow) with large kernels."""
    hs = [1.0, 0.72, 0.48, 0.72, 1.0]
    step = w / len(hs)
    for i, f in enumerate(hs):
        hh = h * f
        col = st.tint(colour, 0.25 + 0.45 * (1 - f)) if i < 3 else st.tint(colour, 0.78)
        for j, (dx, g) in enumerate([(0.0, 0.62), (0.22, 1.0), (0.44, 0.62)]):
            c.ax.add_patch(Rectangle((x + i * step + dx * step, y - hh * g / 2), step * 0.18, hh * g,
                                     fc=col, ec="white", lw=0.3, zorder=4))
    t = np.linspace(0, np.pi, 30)
    rx = (w - step) / 2
    c.ax.plot(x + step * 0.3 + rx - rx * np.cos(t), y + h / 2 + 1.0 + 1.2 * np.sin(t), color=st.MUTED, lw=0.4,
              ls=(0, (1.6, 1.0)), zorder=3)


def swin_glyph(c: Canvas, x, y, colour, w=15.0, h=8.0):
    """Swin UNETR: a transformer encoder over a grid of image patches (windows outlined), then a convolutional
    decoder."""
    n, g = 4, h * 0.95
    cell = g / n
    x0, y0 = x, y - g / 2
    for i in range(n):
        for j in range(n):
            c.ax.add_patch(Rectangle((x0 + i * cell, y0 + j * cell), cell, cell, fc=st.tint(colour, 0.75),
                                     ec="white", lw=0.3, zorder=4))
    for i in (0, 2):                                      # 2 x 2 attention windows
        for j in (0, 2):
            c.ax.add_patch(Rectangle((x0 + i * cell, y0 + j * cell), 2 * cell, 2 * cell, fc="none", ec=colour,
                                     lw=0.6, zorder=5))
    c.ax.add_patch(Rectangle((x0 + cell, y0 + cell), 2 * cell, 2 * cell, fc="none", ec=colour, lw=0.5,
                             ls=(0, (1.2, 0.8)), zorder=5))   # shifted window
    dx = x0 + g + 1.0
    c.arrow((dx - 0.6, y), (dx + 0.6, y), st.MUTED, 0.4, ms=2.5)
    rest = x + w - dx - 0.6
    for i, f in enumerate([0.5, 0.75, 1.0]):              # decoder plates growing back to full size
        hh = h * f
        c.slab(dx + 1.0 + i * rest / 3, y - hh / 2, rest / 3 * 0.62, hh, 1.6, st.tint(colour, 0.78), alpha=1.0)


def panel_b(c: Canvas, seq) -> None:
    from matplotlib.colors import to_rgb
    top = TB
    c.header(top, "b", "PRISM's segmenter: the BraTS 2024 post-treatment ensemble applied to every scan")
    base = top - 28.0                                   # vertical centre line of the ensemble
    # ---- inputs: the four sequences stacked along a diagonal (Tak's scans along a time arrow)
    s = 12.5
    for k, (key, name) in enumerate(SEQ_LABELS):
        x, y = 2.0 + k * 3.6, base + 7.5 - k * 5.4
        c.image(x, y - s / 2, s, s, seq[key])
        c.text(x + 0.6, y + s / 2 - 0.5, name, size=4.6, colour="white", weight="bold")
    c.arrow((26.0, base - 2.0), (30.5, base - 2.0), BLACK, 0.8)

    # ---- six networks: three architectures (rows) x two training sets (columns), five folds each
    rows = [base + 11.0, base, base - 11.0]
    cx = [56.0, 77.0]
    c.line([31.0, 31.0], [rows[0], rows[-1]], BLACK, 0.6)
    for ry in rows:
        c.arrow((31.0, ry), (33.5, ry), BLACK, 0.6, ms=4)
    c.text(cx[0] + 7.5, top - 4.6, "BraTS 2024 data\n(1,350 cases)", size=4.8, ha="center", weight="bold")
    c.text(cx[1] + 7.5, top - 4.6, "plus synthetic images\n(15,651 cases)", size=4.8, ha="center", weight="bold")
    draw = {"nnU-Net": unet_glyph, "Swin UNETR": swin_glyph, "MedNeXt-L": mednext_glyph}
    for r, (ry, (name, kind)) in enumerate(zip(rows, ARCHS)):
        c.text(34.0, ry + 2.4, name, size=5.2, weight="bold", colour=st.IMG)
        c.text(34.0, ry - 0.2, kind, size=4.4, colour=st.MUTED)
        for col, x in enumerate(cx):
            for k in (2, 1):                              # two ghost plates behind: the other folds
                c.box(x - 1.2 + k * 0.9, ry - 4.4 + k * 0.9, x + 15.4 + k * 0.9, ry + 4.8 + k * 0.9,
                      edge=st.tint(st.IMG, 0.55), face="white", lw=0.4, r=0.6, z=1)
            c.box(x - 1.2, ry - 4.4, x + 15.4, ry + 4.8, edge=st.IMG, face="white", lw=0.5, r=0.6, z=2)
            c.text(x - 0.4, ry + 4.4, name, size=4.2, weight="bold", colour=st.IMG, va="top")
            draw[name](c, x + 0.4, ry - 1.4, st.IMG, w=13.2, h=4.6)
            c.text(x + 15.0, ry - 3.0, "×5", size=4.4, colour=st.MUTED, ha="right")
    gx0, gx1 = cx[0] - 3.0, cx[1] + 19.6                 # the 30 networks, enclosed; one arrow to the mean
    c.box(gx0, rows[-1] - 6.4, gx1, rows[0] + 7.6, edge=st.MUTED, face="none", lw=0.5, ls=(0, (2, 1.5)), r=1.0, z=0)
    c.text(gx0, rows[-1] - 7.4, "each network in five folds: 6 × 5 = 30 networks, fixed weights",
           size=4.6, colour=st.MUTED)
    c.arrow((gx1, base), (104.0 - 3.4, base), BLACK, 0.6, ms=4)

    # ---- ensemble: equal-weight mean of the 30 probability maps, then regions and the volume rule
    ex = 104.0
    c.ax.add_patch(Circle((ex, base), 3.4, fc="white", ec=BLACK, lw=0.7, zorder=5))
    c.text(ex, base + 0.1, "mean", size=4.8, ha="center", va="center", weight="bold")
    c.text(ex, base - 4.4, "of the 30\nprobability\nmaps", size=4.4, ha="center", colour=st.MUTED)
    bx0, bx1 = 111.0, 128.0
    c.arrow((ex + 3.4, base), (bx0, base), BLACK, 0.6, ms=4)
    c.box(bx0, base - 7.0, bx1, base + 7.0, edge=BLACK, r=0.8)
    c.text((bx0 + bx1) / 2, base + 5.6, "> 0.5 per region\n(WT, TC, ET, RC);\nWT and RC parts\n"
           "< 50 voxels\nremoved", size=4.5, ha="center")
    c.arrow((bx1, base), (bx1 + 3.0, base), BLACK, 0.8)
    ow = 19.0
    ox = bx1 + 3.4
    iax = c.image(ox, base - ow / 2, ow, ow, seq["t1c"])
    rgba = np.zeros(seq["label"].shape + (4,))
    for lab, colour in LABEL_RGB.items():
        rgba[seq["label"] == lab] = (*to_rgb(colour), 0.6)
    iax.imshow(rgba, interpolation="nearest")
    for k, (lab, name) in enumerate([(3, "enhancing"), (1, "necrosis"), (2, "FLAIR\nhyperintensity"),
                                     (4, "resection\ncavity")]):
        ly = base + ow / 2 - 1.6 - k * 4.0
        c.ax.add_patch(Rectangle((ox + ow + 1.0, ly - 0.7), 1.4, 1.4, fc=LABEL_RGB[lab], ec="none"))
        c.text(ox + ow + 3.0, ly + 0.8, name, size=4.6, colour=st.MUTED)
    c.text(ox, base - ow / 2 - 1.2, "first place, BraTS 2024 adult\nglioma post-treatment; trained\n"
                                    "and fixed, with no tuning\non any cohort", size=4.6, colour=st.MUTED)

    # ---- the building block of each architecture, in a row
    iy = TC + 5.6
    c.text(2.0, iy + 6.4, "The building block of each architecture:", size=5.0, colour=st.INK)
    chains = [("nnU-Net", ["conv 3³", "norm", "LReLU"], False, "× 2"),
              ("MedNeXt", ["depthwise\nconv 5³", "GroupNorm", "1×1×1\n×4 ch.", "GELU", "1×1×1"], True, ""),
              ("Swin UNETR", ["LN", "W-MSA", "LN", "MLP"], False, "each with a residual;\nthen shifted windows")]
    x = 2.0
    for name, cells, resid, note in chains:
        c.text(x, iy + 0.1, name, size=4.8, weight="bold", colour=st.IMG, va="center")
        x += {"nnU-Net": 10.0, "MedNeXt": 10.6, "Swin UNETR": 13.0}[name]
        start = x
        prev = None
        for cell in cells:
            w = 2.4 + 0.95 * max(len(t) for t in cell.split("\n"))
            face = st.IMG if "MSA" in cell else (st.tint(st.IMG, 0.6) if cell in ("MLP", "GELU", "LReLU")
                                                  else st.tint(st.IMG, 0.9))
            c.box(x, iy - 2.0, x + w, iy + 2.0, edge=st.IMG, face=face, lw=0.5, r=0.6, z=5)
            c.text(x + w / 2, iy + 0.05, cell, size=4.2, ha="center", va="center",
                   colour="white" if "MSA" in cell else st.INK)
            if prev is not None:
                c.arrow((prev, iy), (x, iy), st.IMG, 0.5, ms=3.5)
            prev = x + w
            x += w + 1.2
        if resid:                                           # residual connection, below the row
            c.line([start - 0.6, start - 0.6, prev + 0.6], [iy, iy - 3.4, iy - 3.4], st.IMG, 0.5)
            c.arrow((prev + 0.6, iy - 3.4), (prev + 0.6, iy - 0.2), st.IMG, 0.5, ms=3.5)
        if note:
            c.text(prev + 1.4, iy + 0.1, note, size=4.4, colour=st.MUTED, va="center")
            x += 7.0
        x += 6.0
    c.rule(TC + 0.6)


# ==================================================================== (c) PRISM at one scan
def panel_c(c: Canvas, scans) -> None:
    top = TC
    c.header(top, "c", "PRISM at one follow-up scan")
    cols = [(2.0, 25.0), (28.0, 49.0), (52.0, 88.0), (91.0, 114.0), (117.0, 142.0), (145.0, 179.0)]
    names = ["Inputs", "Features", "Models", "Evidence", "Collation", "Writing and checking"]
    sy = top - 8.0
    for i, ((x0, x1), name) in enumerate(zip(cols, names)):
        c.ax.add_patch(Circle((x0 + 1.9, sy), 1.8, fc=BLACK, ec="none", zorder=5))
        c.text(x0 + 1.9, sy + 0.05, str(i + 1), size=5.6, colour="white", weight="bold", ha="center", va="center")
        c.text(x0 + 4.8, sy + 0.05, name, size=6.4, weight="bold", va="center")
        c.line([x0, x1], [sy - 2.8, sy - 2.8], st.RULE, 0.5)
    y_img, y_comb, y_hist = top - 19.0, top - 36.0, top - 53.0

    # ---- 1 inputs: two scans, and the clinical history as a document
    x0, x1 = cols[0]
    for k, label in enumerate(["previous", "current"]):
        sx = x0 + k * 11.8
        c.scan(sx, y_img - 6.0, 10.6, scans[k - 2])
        c.text(sx + 5.3, y_img - 6.6, label, size=4.8, colour=st.MUTED, ha="center")
    c.text(x0, y_img - 10.4, "four MRI sequences;\nsegmenter masks (b)", size=5.0)
    c.document(x0 + 1.0, y_hist - 5.0, 8.0, 10.5, st.HIST, lines=5)
    c.text(x0 + 10.6, y_hist + 5.2, "treatment\ncourse as of\nthe scan day;\nage, sex,\nIDH, MGMT", size=5.0)

    # ---- 2 features as vectors of cells
    x0, x1 = cols[1]
    cwid, ch = 3.0, 1.15
    tints = [0.0] * 5 + [0.35] * 10 + [0.62] * 7
    for k, a in enumerate(tints):
        c.ax.add_patch(Rectangle((x0 + 1.0, y_img + 8.0 - (k + 1) * ch * 0.62), cwid, ch * 0.62,
                                 fc=st.tint(st.IMG, a), ec="white", lw=0.25, zorder=5))
    c.text(x0 + 5.4, y_img + 8.2, r"$\mathbf{x}_{\mathrm{img}}$ (22)", size=5.8, colour=st.IMG, weight="bold")
    c.text(x0 + 5.4, y_img + 4.4, "5 volumes\n10 shape and\n    intensity\n7 change since\n    earlier scans",
           size=4.9)
    for k in range(12):
        c.ax.add_patch(Rectangle((x0 + 1.0, y_hist + 4.5 - (k + 1) * 0.78), cwid, 0.78,
                                 fc=st.tint(st.HIST, 0.15 + 0.05 * (k % 3)), ec="white", lw=0.25, zorder=5))
    c.text(x0 + 5.4, y_hist + 4.7, r"$\mathbf{x}_{\mathrm{hist}}$", size=5.8, colour=st.HIST, weight="bold")
    c.text(x0 + 5.4, y_hist + 1.2, "dates of surgery,\nRT, chemo; time\nwindow; patient", size=4.9)
    c.arrow((cols[0][1] - 0.6, y_img + 2.0), (x0 + 0.6, y_img + 2.0))
    c.arrow((cols[0][1] - 0.6, y_hist), (x0 + 0.6, y_hist))

    # ---- 3 models: network glyphs with the fitted form
    x0, x1 = cols[2]
    models = [
        (y_img, "Imaging model", st.IMG,
         r"$\hat p = \sigma(\beta_0 + \boldsymbol{\beta}^{\top}\mathbf{x}_{\mathrm{img}})$", "no dates"),
        (y_comb, "Combined model", st.COMB,
         r"$\hat p = \sigma(\beta_0 + \boldsymbol{\beta}^{\top}\mathbf{z})$",
         r"$\mathbf{z} = \mathbf{x}_{\mathrm{img}} \oplus \mathbf{x}_{\mathrm{hist}}$"),
        (y_hist, "Clinical-history model", st.HIST,
         r"$\hat p = \sigma(\beta_0 + \boldsymbol{\beta}^{\top}\mathbf{x}_{\mathrm{hist}})$", "")]
    for y, name, colour, eq, note in models:
        c.network(x0 + 4.2, y, 2.6, colour)
        c.text(x0 + 9.0, y + 4.6, name, size=5.8, colour=colour, weight="bold")
        c.text(x0 + 9.0, y + 1.3, eq, size=5.4)
        if note:
            c.text(x0 + 9.0, y - 2.0, note, size=4.9, colour=st.MUTED)
    fx = cols[1][1]
    c.arrow((fx + 0.4, y_img), (x0 + 0.8, y_img), st.IMG)
    c.arrow((fx + 0.4, y_hist), (x0 + 0.8, y_hist), st.HIST)
    c.arrow((fx + 0.4, y_img - 2.0), (x0 + 0.8, y_comb + 0.8), st.IMG)
    c.arrow((fx + 0.4, y_hist + 2.0), (x0 + 0.8, y_comb - 0.8), st.HIST)
    c.text(x0, y_hist - 5.6, "ridge logistic regression, penalty by\npatient-grouped cross validation", size=4.8,
           colour=st.MUTED)

    # ---- 4 evidence statements, each a small icon
    x0, x1 = cols[3]
    ev = [(y_img + 2.0, "Conformal set", "80% set: {0}, {1}\nor {0, 1}"),
          (y_comb - 2.0, "Model agreement", "imaging and clinical\nhistory, each against\nits cohort median"),
          (y_hist - 4.0, "Reliability card", "results measured in\nthis time window and\nenhancement state")]
    for k, (y, title, body) in enumerate(ev):
        c.box(x0, y - 2.6, x0 + 5.2, y + 2.6, edge=BLACK, r=0.6, z=4)
        if k == 0:
            c.text(x0 + 2.6, y + 0.1, "{0,1}", size=4.0, ha="center", va="center")
        elif k == 1:
            c.arrow((x0 + 1.6, y - 1.6), (x0 + 1.6, y + 1.6), st.IMG, 0.8, ms=3.5)
            c.arrow((x0 + 3.6, y - 1.6), (x0 + 3.6, y + 1.6), st.HIST, 0.8, ms=3.5)
        else:
            for r in range(3):
                for q in range(3):
                    c.ax.add_patch(Rectangle((x0 + 0.9 + q * 1.2, y - 1.8 + r * 1.2), 1.0, 1.0,
                                             fc=st.tint(BLACK, 0.45 if (r + q) % 3 else 0.85), ec="none",
                                             zorder=5))
        c.text(x0 + 6.4, y + 2.6, title, size=5.6, weight="bold")
        c.text(x0 + 6.4, y - 0.4, body, size=4.8)
    jx = cols[2][1] + 1.0
    c.line([jx, jx], [y_hist, y_img], BLACK, 0.6)
    for y, *_ in models:
        c.line([jx - 1.5, jx], [y, y], BLACK, 0.6)
    for y, *_ in ev:
        c.arrow((jx, y), (x0 - 0.2, y), BLACK, 0.6, ms=4)

    # ---- 5 collation: every value gathered under a fixed key, with its source, into the record
    x0, x1 = cols[4]
    cx = (x0 + x1) / 2
    ft = y_img + 6.0
    c.funnel(cx, ft, 14.0, 8.0)
    sources = [y_img + 2.0, y_comb - 2.0, y_hist - 4.0]
    for y in sources:
        c.line([cols[3][1] + 0.5, cols[3][1] + 1.6], [y, y], BLACK, 0.6)
    bus = cols[3][1] + 1.6
    c.line([bus, bus], [min(sources), ft + 2.0], BLACK, 0.6)
    c.line([bus, cx], [ft + 2.0, ft + 2.0], BLACK, 0.6)
    c.arrow((cx, ft + 2.0), (cx, ft + 0.2), BLACK, 0.6, ms=4)
    # the scores and the measurements also enter the record directly (a bypass above the evidence column)
    yb = top - 12.4
    c.line([cols[2][1] - 1.0, cols[2][1] - 1.0], [y_img + 6.6, yb], BLACK, 0.6, ls=(0, (2, 1.2)))
    c.line([cols[2][1] - 1.0, cx - 3.0], [yb, yb], BLACK, 0.6, ls=(0, (2, 1.2)))
    c.arrow((cx - 3.0, yb), (cx - 3.0, ft + 0.3), BLACK, 0.6, ms=4, ls=(0, (2, 1.2)))
    c.text((cols[3][0] + cols[3][1]) / 2 + 1.0, yb + 0.05, "scores, measurements, history", size=4.4,
           colour=st.MUTED, ha="center", va="center", bbox=dict(fc="white", ec="none", pad=0.4))
    rd = (cx - 10.5, y_comb - 16.0, 21.0, 22.0)
    c.arrow((cx, ft - 8.0), (cx, rd[1] + rd[3] + 0.2), BLACK, 0.7, ms=4.5)
    x, y, w, h = rd
    c.document(x, y, w, h, BLACK, lines=0)
    c.text(x + 1.2, y + h - 4.2, "record", size=5.6, weight="bold")
    c.text(x + 1.2, y + h - 7.6, "meas.enhancing_cc\nmodel.imaging.score\nmodel.combined.\n  score\n"
           "conformal.80\nagreement\ncard.tier\n… + source", size=3.9, family=MONO, colour=st.MUTED)
    c.text(cx, y - 1.4, "deterministic code;\nevery value under a\nfixed key, with its\nsource", size=4.8,
           ha="center")

    # ---- 6 writing and checking
    x0, x1 = cols[5]
    lx = x0 + 6.0
    ex = rd[0] + rd[2] + 1.6
    c.line([rd[0] + rd[2], ex, ex], [y_comb, y_comb, y_img + 1.0], BLACK, 0.7)
    c.arrow((ex, y_img + 1.0), (lx - 4.6, y_img + 1.0), BLACK, 0.7, ms=4.5)
    c.chat(lx, y_img + 1.0, 9.0, 6.6)
    c.text(lx + 6.2, y_img + 5.6, "Local language model", size=5.6, weight="bold")
    c.text(lx + 6.2, y_img + 2.6, "Qwen3.8-27B; writes\nsentences that cite record\nkeys (JSON schema); no\n"
                                  "images, no arithmetic", size=4.8)
    c.arrow((lx, y_img - 4.2), (lx, y_comb + 4.6), BLACK, 0.7, ms=4.5)
    c.shield(lx, y_comb + 1.0, 3.2)
    c.text(lx + 6.2, y_comb + 4.4, "Deterministic checker", size=5.6, weight="bold")
    c.text(lx + 6.2, y_comb + 1.4, "every number in a cited field;\nflags stated; the verifier ties\n"
                                   "each number to its region", size=4.8)
    c.arrow((lx, y_comb - 4.0), (lx, y_hist + 4.6), BLACK, 0.7, ms=4.5)
    c.text(lx + 1.0, y_comb - 7.0, "accept or reject", size=4.6, colour=st.MUTED)
    c.document(lx - 4.0, y_hist - 6.0, 8.0, 10.5, BLACK, lines=5)
    c.text(lx + 6.2, y_hist + 2.4, "Report", size=5.6, weight="bold")
    c.text(lx + 6.2, y_hist - 0.6, "each sentence with the\nrecord keys it cites", size=4.8)
    c.rule(TD + 0.6)


# ==================================================================== (d) evaluation
def panel_d(c: Canvas) -> None:
    top = TD
    c.header(top, "d", "Evaluation")
    y = top - 15.0
    c.database(8.0, y, 8.0, 11.0)
    c.text(8.0, y - 7.8, "MU-Glioma-Post", size=5.2, ha="center", weight="bold")
    c.chevron(14.5, y, 2.6)
    c.crowd(19.5, y - 6.5, 3, 3, 1.6, 4.0, 5.6)
    c.text(32.0, y + 6.0, "development", size=5.6, weight="bold")
    c.text(32.0, y + 2.6, "5 repeats of 5-fold cross\nvalidation grouped by\npatient; held-out AUC on\n"
                          "146 scans of 80 patients", size=4.9)
    c.chevron(61.0, y, 2.6)
    c.lock(70.0, y + 1.0, 3.0)
    c.network(80.0, y + 0.6, 2.6, BLACK)
    c.text(75.0, y - 4.4, "each model fitted once\non all 181 MU scans,\nthen frozen", size=4.9, ha="center")
    c.chevron(90.0, y, 2.6)
    for k, (name, body) in enumerate([("LUMIERE", "178 scans of 79 patients"),
                                      ("UCSF-ALPTDG", "69 second scans of 69 patients")]):
        cx = 101.0 + k * 34.0
        c.database(cx, y, 8.0, 11.0, DB, filled=False)
        c.text(cx + 6.0, y + 4.0, name, size=5.6, weight="bold")
        c.text(cx + 6.0, y + 0.6, body.replace(" of ", "\nof "), size=4.9)
    c.chevron(160.0, y, 2.6)
    c.text(165.0, y + 6.0, "measured", size=5.6, weight="bold")
    c.text(165.0, y + 2.6, "AUC with patient\nbootstrap CI;\nset coverage;\nreports passing\nthe checker", size=4.9)
    c.text(2.0, 3.0, "Label: the first scan at documented progression versus a scan followed by ≥ 120 days "
                     "without progression (LUMIERE: rated stable or responding).", size=5.0, colour=st.MUTED,
           va="bottom")


def fig1(output: Path) -> None:
    scans = patient_scans()
    c = Canvas()
    panel_a(c, scans)
    panel_b(c, sequence_slices(PATIENT, scans[-1]["tp"]))
    panel_c(c, scans)
    panel_d(c)
    st.save(c.fig, output, "fig1_system")


if __name__ == "__main__":
    fig1(Path(__file__).resolve().parents[1] / "docs/manuscript/figures")
