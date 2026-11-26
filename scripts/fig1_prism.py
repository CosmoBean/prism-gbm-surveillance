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

# Every panel is drawn at its printed size: one drawing unit is one millimetre on the page, so the font sizes below
# are the printed sizes. W is the text width of the journal page (A4, 1 inch margins).
W = 159.0
MM = 1 / 25.4
T_HEAD, T_STAGE, T_TITLE, T_BODY, T_NOTE = 9.5, 8.5, 8.0, 7.5, 7.0   # points; nothing smaller than 7


class Canvas:
    """One panel, one axes in millimetres, with the primitives and Tak-style icons used by every panel."""

    def __init__(self, h: float):
        self.W, self.H = W, h
        self.fig = plt.figure(figsize=(W * MM, h * MM))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set(xlim=(0, W), ylim=(0, h))
        self.ax.axis("off")

    # ---------------------------------------------------------------- primitives
    def text(self, x, y, s, size=T_BODY, colour=st.INK, **kw):
        kw.setdefault("ha", "left"); kw.setdefault("va", "top")
        assert size >= 7.0 or kw.get("family") == "__allow_small__", s
        return self.ax.text(x, y, s, fontsize=size, color=colour, linespacing=1.25, zorder=6, **kw)

    def arrow(self, a, b, colour=BLACK, lw=0.8, style="-|>", ms=7.0, **kw):
        self.ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=ms, color=colour, lw=lw,
                                          shrinkA=0, shrinkB=0, zorder=4, **kw))

    def line(self, xs, ys, colour=BLACK, lw=0.8, **kw):
        kw.setdefault("zorder", 3)
        self.ax.plot(xs, ys, color=colour, lw=lw, solid_capstyle="butt", **kw)

    def box(self, x0, y0, x1, y1, edge=BLACK, face="white", lw=0.8, ls="-", r=1.3, z=2):
        self.ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle=f"round,pad=0,rounding_size={r}",
                                         fc=face, ec=edge, lw=lw, ls=ls, zorder=z))

    def image(self, x, y, w, h, img, **kw):
        iax = self.fig.add_axes([x / self.W, y / self.H, w / self.W, h / self.H])
        iax.imshow(img, cmap="gray", vmin=0, vmax=1, interpolation="bilinear", **kw)
        iax.set_xticks([]); iax.set_yticks([])
        for sp in iax.spines.values():
            sp.set_visible(False)
        return iax

    def chevron(self, x, y, s=3.0, colour=BLACK, lw=1.2):
        self.line([x, x + s * 0.7, x], [y + s, y, y - s], colour, lw)

    def header(self, letter, heading):
        self.ax.text(0.5, self.H - 0.5, letter, fontsize=11, weight="bold", ha="left", va="top", color=st.INK)
        self.ax.text(6.0, self.H - 0.9, heading, fontsize=T_HEAD, weight="bold", ha="left", va="top", color=st.INK)

    def stage(self, x0, x1, y, number, name):
        """A numbered stage heading over a hairline (panel c)."""
        self.ax.add_patch(Circle((x0 + 2.2, y), 2.1, fc=BLACK, ec="none", zorder=5))
        self.text(x0 + 2.2, y + 0.05, str(number), size=T_STAGE, colour="white", weight="bold", ha="center",
                  va="center")
        self.text(x0 + 5.6, y + 0.05, name, size=T_STAGE + 0.5, weight="bold", va="center")
        self.line([x0, x1], [y - 3.2, y - 3.2], st.RULE, 0.6)

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


# ==================================================================== network glyphs (panel b)
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


# ==================================================================== (a) one patient's follow-up
HA = 70.0


def panel_a(scans) -> Canvas:
    c = Canvas(HA)
    top = HA
    c.header("a", "MU-Glioma-Post: one patient's follow-up after radiotherapy")
    n = len(scans)
    iw, gap, ix0 = 22.0, 5.0, 28.0
    xs = [ix0 + k * (iw + gap) for k in range(n)]
    iy0 = top - 20.0 - iw
    mid = iy0 + iw / 2
    c.database(10.0, mid + 3.0, 9.0, 12.0)
    c.text(0.8, mid - 4.6, "MU-Glioma-Post", size=T_NOTE, weight="bold")
    c.text(0.8, mid - 7.8, "126 grade 4\npatients", size=T_NOTE, colour=st.MUTED)
    c.chevron(19.5, mid + 3.0, 2.6)
    by = top - 15.5                                        # intervals between scans (Tak's "161 Days")
    for k in range(1, n):
        a, b = xs[k - 1] + iw / 2, xs[k] + iw / 2
        c.line([a, b], [by, by], BLACK, 0.6)
        for x in (a, b):
            c.line([x, x], [by - 0.8, by + 0.8], BLACK, 0.6)
        c.text((a + b) / 2, by + 0.7, f"{scans[k]['weeks'] - scans[k - 1]['weeks']:.0f} weeks", size=T_NOTE,
               ha="center", va="bottom")
    for k, sc in enumerate(scans):
        x = xs[k]
        weight = "bold" if sc["label"] == "Progression" else "normal"
        style = "italic" if sc["label"] == "Not labelled" else "normal"
        colour = st.MUTED if sc["label"] == "Not labelled" else BLACK
        c.text(x + iw / 2, top - 6.6, sc["label"], size=T_TITLE, ha="center", weight=weight, style=style,
               colour=colour)
        c.scan(x, iy0, iw, sc, pointer=True)
        c.text(x + iw / 2, iy0 - 0.9, f"{sc['net_cc']:.1f} cc ({sc['et_cc']:.1f})", size=T_BODY, ha="center")
    # the time axis, to scale, with the first 12 weeks shaded
    ty = iy0 - 12.5
    wmax = 44.0
    wx = lambda w: ix0 + (W - 6.0 - ix0) * w / wmax
    c.ax.add_patch(Rectangle((wx(0), ty - 1.4), wx(12) - wx(0), 2.8, fc=st.tint(st.HIST, 0.75), ec="none",
                             zorder=2))
    c.text(wx(6), ty + 1.8, "first 12 weeks", size=T_NOTE, colour=st.HIST, ha="center", va="bottom")
    c.arrow((ix0 - 6.0, ty), (W - 1.5, ty), BLACK, 0.9, ms=7)
    for k, sc in enumerate(scans):
        c.line([xs[k] + iw / 2, wx(sc["weeks"])], [iy0 - 4.6, ty + 1.0], st.RULE, 0.6, zorder=1)
        c.ax.add_patch(Circle((wx(sc["weeks"]), ty), 1.0, fc=BLACK, ec="white", lw=0.3, zorder=5))
        c.text(wx(sc["weeks"]), ty - 1.9, f"{sc['weeks']:.1f}", size=T_BODY, ha="center")
    c.text(ix0 - 6.0, ty - 1.9, "end of\nradiotherapy", size=T_NOTE, ha="left", colour=st.MUTED)
    c.text(W - 1.0, ty - 5.4, "weeks after the end of radiotherapy", size=T_NOTE, colour=st.MUTED, ha="right")
    # legend
    ly = 3.2
    c.line([1.0, 5.0], [ly, ly], CONTOUR, 1.4)
    c.text(6.0, ly + 1.6, "PRISM's segmenter", size=T_NOTE, colour=st.MUTED)
    c.line([31.0, 35.0], [ly, ly], RELEASED, 1.1, ls="--")
    c.text(36.0, ly + 1.6, "released mask", size=T_NOTE, colour=st.MUTED)
    c.text(W - 1.0, ly + 1.6, "under each scan: enhancing volume, segmenter (released mask)", size=T_NOTE,
           colour=st.MUTED, ha="right")
    return c


# ==================================================================== (b) the segmenter
HB = 104.0
CHAINS = [("nnU-Net", ["conv 3³", "norm", "LReLU"], False, "twice per stage"),
          ("MedNeXt", ["depthwise conv 5³", "GroupNorm", "1×1×1, 4× channels", "GELU", "1×1×1"], True, ""),
          ("Swin UNETR", ["LN", "W-MSA", "LN", "MLP"], False, "each with a residual; then shifted windows")]


def panel_b(seq) -> Canvas:
    from matplotlib.colors import to_rgb
    c = Canvas(HB)
    top = HB
    c.header("b", "PRISM's segmenter: the BraTS 2024 post-treatment ensemble, applied to every scan")
    rows = [top - 25.0, top - 39.0, top - 53.0]           # three architectures
    base = rows[1]
    # ---- inputs: the four sequences stacked along a diagonal
    s = 14.0
    for k, (key, name) in enumerate(SEQ_LABELS):
        x, y = 1.0 + k * 3.0, base + 8.0 - k * 5.6
        c.image(x, y - s / 2, s, s, seq[key])
        c.text(x + 0.5, y + s / 2 - 0.4, name, size=T_NOTE, colour="white", weight="bold")
    c.arrow((24.0, base - 3.0), (28.0, base - 3.0), BLACK, 0.9)
    # ---- six networks: three architectures (rows) x two training sets (columns), five folds each
    cx = [31.5, 62.5]
    bw, bh = 26.0, 11.0
    c.text(cx[0] + bw / 2, top - 7.6, "BraTS 2024 data\n(1,350 cases)", size=T_NOTE, ha="center", weight="bold")
    c.text(cx[1] + bw / 2, top - 7.6, "plus synthetic images\n(15,651 cases)", size=T_NOTE, ha="center",
           weight="bold")
    draw = {"nnU-Net": unet_glyph, "Swin UNETR": swin_glyph, "MedNeXt-L": mednext_glyph}
    for ry, name in zip(rows, ["nnU-Net", "Swin UNETR", "MedNeXt-L"]):
        for x in cx:
            for k in (2, 1):                                # two ghost plates behind: the other folds
                c.box(x + k * 0.9, ry - bh / 2 + k * 0.9, x + bw + k * 0.9, ry + bh / 2 + k * 0.9,
                      edge=st.tint(st.IMG, 0.55), face="white", lw=0.5, r=0.7, z=1)
            c.box(x, ry - bh / 2, x + bw, ry + bh / 2, edge=st.IMG, face="white", lw=0.6, r=0.7, z=2)
            c.text(x + 0.8, ry + bh / 2 - 0.6, name, size=T_NOTE, weight="bold", colour=st.IMG)
            draw[name](c, x + 1.2, ry - 2.0, st.IMG, w=16.0, h=4.6)
            c.text(x + bw - 0.6, ry - bh / 2 + 0.6, "×5", size=T_NOTE, colour=st.MUTED, ha="right", va="bottom")
    gx0, gx1 = cx[0] - 2.0, cx[1] + bw + 3.6
    c.box(gx0, rows[-1] - bh / 2 - 2.0, gx1, rows[0] + bh / 2 + 3.4, edge=st.MUTED, face="none", lw=0.6,
          ls=(0, (2, 1.5)), r=1.0, z=0)
    # ---- ensemble: equal-weight mean of the 30 probability maps, then regions and the volume rule
    ex = 100.0
    c.arrow((gx1, base), (ex - 4.4, base), BLACK, 0.8)
    c.ax.add_patch(Circle((ex, base), 4.4, fc="white", ec=BLACK, lw=0.8, zorder=5))
    c.text(ex, base + 0.1, "mean", size=T_BODY, ha="center", va="center", weight="bold")
    c.text(ex, base - 5.6, "of the 30\nprobability\nmaps", size=T_NOTE, ha="center", colour=st.MUTED)
    bx0, bx1 = 107.5, 128.0
    c.arrow((ex + 4.4, base), (bx0, base), BLACK, 0.8)
    c.box(bx0, base - 9.0, bx1, base + 9.0, edge=BLACK, r=0.9)
    c.text((bx0 + bx1) / 2, base + 7.6, "> 0.5 per\nregion;\nparts under\n50 voxels\nremoved", size=T_NOTE,
           ha="center")
    c.arrow((bx1, base), (bx1 + 2.6, base), BLACK, 0.9)
    ow = 27.0
    ox = W - ow - 0.5
    iax = c.image(ox, base - ow / 2, ow, ow, seq["t1c"])
    rgba = np.zeros(seq["label"].shape + (4,))
    for lab, colour in LABEL_RGB.items():
        rgba[seq["label"] == lab] = (*to_rgb(colour), 0.6)
    iax.imshow(rgba, interpolation="nearest")
    # notes and the label legend, under the ensemble
    ny = rows[-1] - bh / 2 - 3.4
    c.text(gx0, ny, "3 architectures × 2 training sets × 5 folds = 30 networks, weights fixed, with no tuning on "
                    "any cohort;\nfirst place in the BraTS 2024 adult glioma post-treatment challenge", size=T_NOTE,
           colour=st.MUTED)
    lx = gx0
    ly = ny - 9.4
    for lab, name in [(3, "enhancing tumour"), (1, "necrosis"), (2, "FLAIR hyperintensity"), (4, "resection cavity")]:
        c.ax.add_patch(Rectangle((lx, ly - 1.0), 2.4, 2.4, fc=LABEL_RGB[lab], ec="none"))
        c.text(lx + 3.2, ly + 1.4, name, size=T_NOTE, colour=st.INK)
        lx += 8.0 + 1.3 * len(name)
    # ---- the building block of each architecture, one line each
    iy = 21.0
    c.line([1.0, W - 1.0], [iy + 5.2, iy + 5.2], st.RULE, 0.6)
    c.text(1.0, iy + 3.8, "The building block of each architecture", size=T_BODY, weight="bold")
    for r, (name, cells, resid, note) in enumerate(CHAINS):
        y = iy - 3.6 - r * 6.4
        c.text(1.0, y + 0.1, name, size=T_BODY, weight="bold", colour=st.IMG, va="center")
        x = 22.0
        start, prev = x, None
        for cell in cells:
            w = 3.0 + 1.42 * len(cell)
            face = st.IMG if "MSA" in cell else (st.tint(st.IMG, 0.6) if cell in ("MLP", "GELU", "LReLU")
                                                  else st.tint(st.IMG, 0.9))
            c.box(x, y - 2.3, x + w, y + 2.3, edge=st.IMG, face=face, lw=0.6, r=0.7, z=5)
            c.text(x + w / 2, y + 0.05, cell, size=T_NOTE, ha="center", va="center",
                   colour="white" if "MSA" in cell else st.INK)
            if prev is not None:
                c.arrow((prev, y), (x, y), st.IMG, 0.6, ms=5)
            prev = x + w
            x += w + 2.4
        if resid:                                           # residual connection, drawn around the row
            c.line([start - 0.8, start - 0.8, prev + 0.8], [y, y + 2.9, y + 2.9], st.IMG, 0.6)
            c.arrow((prev + 0.8, y + 2.9), (prev + 0.8, y + 0.3), st.IMG, 0.6, ms=5)
            c.text(prev + 2.2, y + 0.1, "with a residual", size=T_NOTE, colour=st.MUTED, va="center")
        if note:
            c.text(prev + 2.2, y + 0.1, note, size=T_NOTE, colour=st.MUTED, va="center")
    return c


# ==================================================================== (c) PRISM at one scan
HC = 136.0
COLS = [(1.0, 51.0), (55.0, 104.0), (108.0, 158.0)]


def panel_c(scans) -> Canvas:
    c = Canvas(HC)
    top = HC
    c.header("c", "PRISM at one follow-up scan, in six stages")
    # two rows of three stages; three lanes per row: imaging, combined, clinical history
    r1, r2 = top - 10.5, top - 78.0
    lane = lambda r: (r - 12.5, r - 30.0, r - 47.5)
    for i, ((x0, x1), name) in enumerate(zip(COLS, ["Inputs", "Features", "Models"])):
        c.stage(x0, x1, r1, i + 1, name)
    for i, ((x0, x1), name) in enumerate(zip(COLS, ["Evidence", "Collation", "Writing and checking"])):
        c.stage(x0, x1, r2, i + 4, name)
    y_img, y_comb, y_hist = lane(r1)

    # ---- 1 inputs: two scans, and the clinical history as a document
    x0, x1 = COLS[0]
    for k, label in enumerate(["previous", "current"]):
        sx = x0 + k * 17.0
        c.scan(sx, y_img - 7.5, 15.5, scans[k - 2])
        c.text(sx + 7.75, y_img - 8.2, label, size=T_NOTE, colour=st.MUTED, ha="center")
    c.text(x0 + 35.0, y_img + 7.5, "four MRI\nsequences;\nsegmenter\nmasks (b)", size=T_NOTE)
    c.document(x0 + 1.0, y_hist - 6.0, 10.0, 13.0, st.HIST, lines=5)
    c.text(x0 + 13.5, y_hist + 6.5, "treatment course as of\nthe scan day; age, sex,\nIDH and MGMT status",
           size=T_BODY)

    # ---- 2 features as vectors of cells
    x0, x1 = COLS[1]
    cw = 3.6
    tints = [0.0] * 5 + [0.35] * 10 + [0.62] * 7
    for k, a in enumerate(tints):
        c.ax.add_patch(Rectangle((x0 + 1.0, y_img + 8.0 - (k + 1) * 0.78), cw, 0.78,
                                 fc=st.tint(st.IMG, a), ec="white", lw=0.25, zorder=5))
    c.text(x0 + 7.0, y_img + 8.4, r"$\mathbf{x}_{\mathrm{img}}$ (22 inputs)", size=T_TITLE, colour=st.IMG,
           weight="bold")
    c.text(x0 + 7.0, y_img + 4.2, "5 volumes\n10 shape and intensity\n7 change since earlier\nscans", size=T_BODY)
    for k in range(12):
        c.ax.add_patch(Rectangle((x0 + 1.0, y_hist + 6.5 - (k + 1) * 1.05), cw, 1.05,
                                 fc=st.tint(st.HIST, 0.15 + 0.05 * (k % 3)), ec="white", lw=0.25, zorder=5))
    c.text(x0 + 7.0, y_hist + 6.9, r"$\mathbf{x}_{\mathrm{hist}}$", size=T_TITLE, colour=st.HIST, weight="bold")
    c.text(x0 + 7.0, y_hist + 2.7, "dates of surgery,\nradiotherapy and chemo-\ntherapy; time window",
           size=T_BODY)
    c.arrow((COLS[0][1] + 0.5, y_img), (x0 + 0.5, y_img))
    c.arrow((COLS[0][1] + 0.5, y_hist), (x0 + 0.5, y_hist))

    # ---- 3 models: network glyphs with the fitted form
    x0, x1 = COLS[2]
    models = [
        (y_img, "Imaging model", st.IMG,
         r"$\hat p = \sigma(\beta_0 + \boldsymbol{\beta}^{\top}\mathbf{x}_{\mathrm{img}})$", "no dates"),
        (y_comb, "Combined model", st.COMB,
         r"$\hat p = \sigma(\beta_0 + \boldsymbol{\beta}^{\top}\mathbf{z})$",
         r"$\mathbf{z} = \mathbf{x}_{\mathrm{img}} \oplus \mathbf{x}_{\mathrm{hist}}$"),
        (y_hist, "Clinical-history model", st.HIST,
         r"$\hat p = \sigma(\beta_0 + \boldsymbol{\beta}^{\top}\mathbf{x}_{\mathrm{hist}})$", "")]
    for y, name, colour, eq, note in models:
        c.network(x0 + 5.0, y, 3.2, colour)
        c.text(x0 + 11.0, y + 5.4, name, size=T_TITLE, colour=colour, weight="bold")
        c.text(x0 + 11.0, y + 1.6, eq, size=T_BODY)
        if note:
            c.text(x0 + 11.0, y - 2.6, note, size=T_NOTE, colour=st.MUTED)
    fx = COLS[1][1]
    c.arrow((fx, y_img), (x0 + 0.8, y_img), st.IMG)
    c.arrow((fx, y_hist), (x0 + 0.8, y_hist), st.HIST)
    c.arrow((fx, y_img - 3.0), (x0 + 0.8, y_comb + 1.0), st.IMG)
    c.arrow((fx, y_hist + 3.0), (x0 + 0.8, y_comb - 1.0), st.HIST)
    c.text(x0, y_hist - 5.0, "ridge logistic regression, penalty\nby patient-grouped cross validation",
           size=T_NOTE, colour=st.MUTED)

    # ---- the turn from row 1 to row 2: the three scores go on to stage 4
    ty = r2 + 5.6
    c.line([W - 0.6, W - 0.6], [y_img, ty], BLACK, 0.8)
    for y, *_ in models:
        c.line([W - 3.0, W - 0.6], [y, y], BLACK, 0.8)
    c.line([W - 0.6, 0.6], [ty, ty], BLACK, 0.8)
    c.text(2.0, ty + 0.9, "the three scores, with the measurements and the history, go on to stage 4", size=T_NOTE,
           colour=st.MUTED, va="bottom")
    e_img, e_comb, e_hist = lane(r2)
    c.line([0.6, 0.6], [ty, e_hist], BLACK, 0.8)
    for y in (e_img, e_comb, e_hist):
        c.arrow((0.6, y), (2.6, y), BLACK, 0.8, ms=5)

    # ---- 4 evidence statements, each a small icon
    x0, x1 = COLS[0]
    ev = [(e_img, "Conformal set", "80% set: {0}, {1} or {0, 1}"),
          (e_comb, "Model agreement", "imaging and clinical-history\nscores, each against its\ncohort median"),
          (e_hist, "Reliability card", "results measured in this\ntime window and\nenhancement state")]
    for k, (y, title, body) in enumerate(ev):
        c.box(x0 + 2.6, y - 3.0, x0 + 8.6, y + 3.0, edge=BLACK, r=0.7, z=4)
        if k == 0:
            c.text(x0 + 5.6, y + 0.1, "{0,1}", size=T_NOTE, ha="center", va="center")
        elif k == 1:
            c.arrow((x0 + 4.4, y - 2.0), (x0 + 4.4, y + 2.0), st.IMG, 0.9, ms=4.5)
            c.arrow((x0 + 6.8, y - 2.0), (x0 + 6.8, y + 2.0), st.HIST, 0.9, ms=4.5)
        else:
            for r in range(3):
                for q in range(3):
                    c.ax.add_patch(Rectangle((x0 + 3.4 + q * 1.5, y - 2.2 + r * 1.5), 1.2, 1.2,
                                             fc=st.tint(BLACK, 0.45 if (r + q) % 3 else 0.85), ec="none",
                                             zorder=5))
        c.text(x0 + 10.0, y + 4.0, title, size=T_TITLE, weight="bold")
        c.text(x0 + 10.0, y + 0.4, body, size=T_BODY)

    # ---- 5 collation: every value gathered under a fixed key, with its source, into the record
    x0, x1 = COLS[1]
    cx = (x0 + x1) / 2 + 2.0
    ft = e_img + 7.0
    c.funnel(cx, ft, 15.0, 8.0)
    bus = COLS[0][1] + 1.6
    for y in (e_img, e_comb, e_hist):
        c.line([bus - 2.0, bus], [y, y], BLACK, 0.8)
    c.line([bus, bus], [e_hist, ft + 2.2], BLACK, 0.8)
    c.line([bus, cx], [ft + 2.2, ft + 2.2], BLACK, 0.8)
    c.arrow((cx, ft + 2.2), (cx, ft + 0.2), BLACK, 0.8, ms=5)
    rd = (cx - 20.0, e_hist - 6.0, 40.0, 32.0)
    c.arrow((cx, ft - 8.0), (cx, rd[1] + rd[3] + 0.2), BLACK, 0.8, ms=6)
    x, y, w, h = rd
    c.document(x, y, w, h, BLACK, lines=0)
    c.text(x + 1.5, y + h - 1.4, "record", size=T_TITLE, weight="bold")
    c.text(x + 1.5, y + h - 12.2, "meas.enhancing_cc\nmodel.imaging.score\nmodel.combined.score\nconformal.80\n"
                                 "agreement\ncard.tier …", size=T_NOTE, family=MONO, colour=st.MUTED)
    c.text(x + 1.5, y + h - 5.0, "every value under a\nfixed key, with its source", size=T_NOTE, colour=st.INK)

    # ---- 6 writing and checking
    x0, x1 = COLS[2]
    lx = x0 + 6.0
    c.line([rd[0] + rd[2], rd[0] + rd[2] + 2.0, rd[0] + rd[2] + 2.0], [e_comb, e_comb, e_img], BLACK, 0.8)
    c.arrow((rd[0] + rd[2] + 2.0, e_img), (lx - 5.2, e_img), BLACK, 0.8, ms=6)
    c.chat(lx, e_img, 10.0, 7.4)
    c.text(lx + 7.0, e_img + 5.0, "Local language model", size=T_TITLE, weight="bold")
    c.text(lx + 7.0, e_img + 1.3, "Qwen3.8-27B; writes\nsentences that cite record\nkeys; no images, no arithmetic",
           size=T_BODY)
    c.arrow((lx, e_img - 4.8), (lx, e_comb + 5.4), BLACK, 0.8, ms=6)
    c.shield(lx, e_comb + 1.4, 3.6)
    c.text(lx + 7.0, e_comb + 5.0, "Deterministic checker", size=T_TITLE, weight="bold")
    c.text(lx + 7.0, e_comb + 1.3, "every number in a cited field;\nflags stated; the verifier ties\n"
                                   "each number to its region", size=T_BODY)
    c.arrow((lx, e_comb - 4.0), (lx, e_hist + 6.6), BLACK, 0.8, ms=6)
    c.text(lx + 1.5, e_comb - 8.6, "accept or reject", size=T_NOTE, colour=st.MUTED)
    c.document(lx - 4.6, e_hist - 6.0, 9.2, 12.4, BLACK, lines=5)
    c.text(lx + 7.0, e_hist + 5.0, "Report", size=T_TITLE, weight="bold")
    c.text(lx + 7.0, e_hist + 1.3, "each sentence with the\nrecord keys it cites", size=T_BODY)
    return c


# ==================================================================== (d) evaluation
HD = 46.0


def panel_d() -> Canvas:
    c = Canvas(HD)
    top = HD
    c.header("d", "Evaluation")
    y = top - 17.0
    c.database(6.0, y + 1.0, 8.0, 11.0)
    c.text(0.8, y - 6.6, "MU-Glioma-\nPost", size=T_NOTE, weight="bold")
    c.text(16.5, y + 7.5, "Development", size=T_TITLE, weight="bold")
    c.text(16.5, y + 3.7, "5 repeats of 5-fold cross\nvalidation grouped by\npatient; held-out AUC on\n"
                          "146 scans of 80 patients", size=T_BODY)
    c.chevron(48.0, y, 2.8)
    c.lock(56.0, y + 2.0, 3.0)
    c.network(66.0, y + 1.6, 2.8, BLACK)
    c.text(61.0, y - 3.6, "each model fitted\nonce on all 181 MU\nscans, then frozen", size=T_BODY, ha="center")
    c.chevron(75.0, y, 2.8)
    for k, (name, body) in enumerate([("LUMIERE", "178 scans of\n79 patients"),
                                      ("UCSF-ALPTDG", "69 second scans\nof 69 patients")]):
        cx = 84.0 + k * 38.0
        c.database(cx, y, 8.0, 11.0, DB, filled=False)
        c.text(cx + 5.8, y + 5.0, name, size=T_TITLE, weight="bold")
        c.text(cx + 5.8, y + 1.2, body, size=T_BODY)
    c.text(1.0, 11.0, "Measured: AUC with a 95% patient-bootstrap interval; coverage of the conformal sets; reports "
                     "passing the checker.", size=T_BODY)
    c.text(1.0, 6.6, "Label: the first scan at documented progression versus a scan followed by at least 120 days "
                     "without progression\n(LUMIERE: rated stable or responding).", size=T_NOTE, colour=st.MUTED)
    return c


def fig1(output: Path) -> None:
    scans = patient_scans()
    seq = sequence_slices(PATIENT, scans[-1]["tp"])
    for name, c in [("fig1a", panel_a(scans)), ("fig1b", panel_b(seq)), ("fig1c", panel_c(scans)),
                    ("fig1d", panel_d())]:
        st.save(c.fig, output, name)


if __name__ == "__main__":
    fig1(Path(__file__).resolve().parents[1] / "docs/manuscript/figures")
