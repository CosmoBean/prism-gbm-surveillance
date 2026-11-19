"""Figure 1: the task and the method. (a) One MU-Glioma-Post patient's follow-up, on real scans, against the time
since radiotherapy (modelled on Tak et al. 2025, NEJM AI, Figure 1A); (b) what PRISM computes at one follow-up scan,
stage by stage; (c) the evaluation protocol.

Panel (a) reads the public MU-Glioma-Post images, masks and clinical workbook (data/mu-glioma-post, see
prism/config.py), and PRISM's own segmentation of each scan by the BraTS 2021 Swin UNETR
(outputs/features/seg_swin/mu, written by prism/features/reseg.py; plan docs/results/SEGMENTER_STAGE_PLAN.md). Weeks after radiotherapy, enhancing volumes and the label of each scan are computed here from those
files with the paper's label rule; no model score is shown. Panels (b) and (c) are a methods schematic as specified in
the Methods (Sections 2.1-2.3, 3.1-3.5); the two input slices in (b) are the patient's last two scans from (a).
Colour follows the score as in every figure (scripts/figure_style.py); navy marks the system's own stages.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

import figure_style as st

W, H0, PT = 180.0, 113.0, 53.0   # drawing units (about 1 mm each); H0 = panels (c)-(d), PT = panel (a)
SG = 50.0                         # panel (b), the segmenter
H = H0 + SG + PT                       # W / H equals the figure aspect
REPO = Path(__file__).resolve().parents[1]
MU = REPO / "data" / "mu-glioma-post"
PATIENT = "PatientID_0204"        # early enhancement that resolved, then progression (selection in the docstring)
ET_LABEL = 3                      # enhancing tumour in the released masks (prism/config.py)
CONTOUR = "#F2C14E"               # PRISM's segmentation (Swin UNETR, BraTS 2021)
RELEASED = "#7FD3F0"              # the mask released with the cohort, for comparison
SEG = REPO / "outputs" / "features" / "seg_swin" / "mu"
MONO = "DejaVu Sans Mono"
BLACK = "#000000"        # Figure 1 structure (boxes, arrows, stage labels) in black, not the house navy


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
    enhancing mask and the enhancing volume (cc)."""
    import nibabel as nib
    import numpy as np
    d = MU / "MU-Glioma-Post" / patient / f"Timepoint_{n}"
    t1c = np.asarray(nib.load(str(d / f"{patient}_Timepoint_{n}_brain_t1c.nii.gz")).dataobj, dtype=np.float32)
    lesion = np.asarray(nib.load(str(d / f"{patient}_Timepoint_{n}_tumorMask.nii.gz")).dataobj)
    et = lesion == ET_LABEL
    # the slice with most enhancement; without enhancement, most lesion; without a lesion, most brain
    pick = et if et.any() else (lesion > 0) if (lesion > 0).any() else (t1c > 0)
    z = int(np.argmax(pick.sum(axis=(0, 1))))
    img = t1c[:, :, z]
    ys, xs = np.nonzero(img > 0)
    cy, cx = (ys.min() + ys.max()) // 2, (xs.min() + xs.max()) // 2
    half = max(ys.max() - ys.min(), xs.max() - xs.min()) // 2 + 4
    lo, hi = np.percentile(img[img > 0], [1, 99.5])
    crop = lambda a: np.rot90(a[max(cy - half, 0):cy + half, max(cx - half, 0):cx + half])   # anterior up
    net = np.asarray(nib.load(str(SEG / patient / f"Timepoint_{n}.nii.gz")).dataobj) == ET_LABEL
    return dict(img=crop(np.clip((img - lo) / (hi - lo), 0, 1)), msk=crop(et[:, :, z]), net=crop(net[:, :, z]),
                et_cc=float(et.sum()) / 1000, net_cc=float(net.sum()) / 1000)


def sequence_slices(patient: str, n: int) -> dict:
    """The four sequences of one scan at its slice with most enhancement (released mask, as in scan_slice), cropped
    alike, and PRISM's label map on that slice (3 enhancing, 1 necrosis, 2 FLAIR hyperintensity)."""
    import nibabel as nib
    import numpy as np
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
    """The patient's post-radiotherapy scans: weeks after RT end, enhancing volume (cc), label, and a T1c slice
    with its enhancing mask, cropped around the lesion. Label rule as in the paper: progression scan = the scan
    dated within 14 days of documented progression; no progression = followed by >= 120 days without progression."""
    clin = load_clinical()
    row = clin[clin["Patient_ID"] == PATIENT].iloc[0]
    rt = float(row["Number of days from Diagnosis to Radiation Therapy end date"])
    prog = float(row["Number of days from Diagnosis to date of First Progression"])
    scans = []
    for n, day in sorted(scan_days(row).items()):
        if day < rt or day > prog + 14 or not (MU / "MU-Glioma-Post" / PATIENT / f"Timepoint_{n}").exists():
            continue
        label = ("Progression" if abs(day - prog) <= 14 else
                 "No progression" if prog - day >= 120 else "Not labelled")
        scans.append(dict(tp=n, weeks=(day - rt) / 7, label=label, **scan_slice(PATIENT, n)))
    return scans


def show_scan(iax, scan):
    iax.imshow(scan["img"], cmap="gray", vmin=0, vmax=1, interpolation="bilinear")
    if scan["msk"].any():
        iax.contour(scan["msk"].astype(float), levels=[0.5], colors=[RELEASED], linewidths=0.45, linestyles="--")
    if scan["net"].any():
        iax.contour(scan["net"].astype(float), levels=[0.5], colors=[CONTOUR], linewidths=0.6)
    iax.set_xticks([]); iax.set_yticks([])
    for sp in iax.spines.values():
        sp.set_visible(False)


SEQ_LABELS = [("t2f", "FLAIR"), ("t1c", "T1c"), ("t1n", "T1"), ("t2w", "T2")]
LABEL_RGB = {3: "#F2C14E", 1: "#D65F5F", 2: "#7BC67B"}   # enhancing, necrosis, FLAIR hyperintensity


def draw_segmenter(fig, ax, text, arrow, box, seq) -> None:
    """Panel (b): the scan's four sequences, the Swin UNETR (MONAI, feature size 48; stage sizes, window and heads
    checked against the instantiated network), the inside of a Swin stage (two successive blocks, regular and shifted
    windows), and the network's label map on the same slice."""
    import numpy as np
    from matplotlib.colors import to_rgb
    top = H0 + SG
    st.panel_header(fig, (top - 0.6) / H, "b", "PRISM's segmenter: a Swin UNETR applied to every scan")
    cy0, cy1 = H0 + 3.0, top - 8.0            # content band

    # ---- inputs: the four sequences, 2 x 2
    tw = 10.6
    for k, (key, name) in enumerate(SEQ_LABELS):
        r, c = divmod(k, 2)
        x, y = 2.0 + c * (tw + 1.2), cy1 - 2.0 - (r + 1) * tw - r * 3.4
        iax = fig.add_axes([x / W, y / H, tw / W, tw / H])
        iax.imshow(seq[key], cmap="gray", vmin=0, vmax=1, interpolation="bilinear")
        iax.set_xticks([]); iax.set_yticks([]); [sp.set_visible(False) for sp in iax.spines.values()]
        text(x + tw / 2, y - 0.4, name, size=5.2, colour=st.MUTED, ha="center")
    ym = cy1 - 2.0 - tw - 1.7
    arrow((25.2, ym), (30.8, ym))
    text(28.0, ym - 1.4, "4 ch.,\n128³\nwindows", size=4.5, colour=st.MUTED, ha="center")

    # ---- the network: Swin Transformer encoder, convolutional decoder, skip connections
    lv, bh = 6.0, 3.6
    y_of = lambda i: cy1 - 5.0 - i * lv
    enc = [("patch embedding", 48, 64), ("Swin stage 1", 96, 32), ("Swin stage 2", 192, 16),
           ("Swin stage 3", 384, 8), ("Swin stage 4", 768, 4)]
    ex0, dx1, step, bw = 31.0, 106.0, 3.2, 24.0
    mid = (ex0 + dx1) / 2
    text(ex0, cy1 + 1.6, "Swin Transformer encoder", size=5.8, colour=st.IMG, weight="bold")
    for i, (name, ch, res) in enumerate(enc):
        y = y_of(i)
        x0 = ex0 + step * i if i < 4 else mid - bw / 2
        box(x0, y - bh / 2, x0 + bw, y + bh / 2, edge=st.IMG, face=st.tint(st.IMG, 0.55 - 0.1 * i), lw=0.6)
        ink = "white" if i >= 2 else st.INK
        text(x0 + 1.0, y + 0.1, name, size=5.0, colour=ink, va="center")
        text(x0 + bw - 1.0, y + 0.1, f"{ch} × {res}³", size=5.0, colour=ink, va="center", ha="right")
        if i < 3:
            arrow((x0 + step + 1.4, y - bh / 2), (x0 + step + 1.4, y_of(i + 1) + bh / 2), st.IMG, lw=0.6)
        elif i == 3:
            ax.plot([x0 + 1.4, x0 + 1.4], [y - bh / 2, y_of(4)], color=st.IMG, lw=0.6)
            arrow((x0 + 1.4, y_of(4)), (mid - bw / 2, y_of(4)), st.IMG, lw=0.6)
    for i, ch, res in [(0, 48, 64), (1, 96, 32), (2, 192, 16), (3, 384, 8)]:
        y, x1 = y_of(i), dx1 - step * i
        box(x1 - bw, y - bh / 2, x1, y + bh / 2, edge=st.IMG, face=st.tint(st.IMG, 0.88), lw=0.6)
        text(x1 - bw + 1.0, y + 0.1, "up-conv, residual", size=4.9, va="center")
        text(x1 - 1.0, y + 0.1, f"{ch} × {res}³", size=5.0, va="center", ha="right")
        arrow((x1 - 2.6, y_of(i + 1) + bh / 2 if i < 3 else y_of(4)), (x1 - 2.6, y - bh / 2), st.IMG, lw=0.6)
        ax.plot([ex0 + step * i + bw, x1 - bw], [y, y], color=st.MUTED, lw=0.5, ls=(0, (2, 1.5)), zorder=1)
    ax.plot([mid + bw / 2, dx1 - step * 3 - 2.6], [y_of(4), y_of(4)], color=st.IMG, lw=0.6)
    text(mid, y_of(0) + 0.2, "skip", size=4.6, colour=st.MUTED, ha="center", va="center",
         bbox=dict(fc="white", ec="none", pad=0.3))
    oy = y_of(0) + lv
    box(dx1 - bw, oy - bh / 2, dx1, oy + bh / 2, edge=BLACK, face="white", lw=0.6)
    text(dx1 - bw + 1.0, oy + 0.1, "1×1×1 conv", size=4.9, va="center")
    text(dx1 - 1.0, oy + 0.1, "TC, WT, ET", size=4.9, va="center", ha="right", weight="bold")
    text(dx1 - bw - 1.6, oy + 0.1, "Convolutional decoder", size=5.8, colour=st.IMG, weight="bold", ha="right",
         va="center")
    arrow((dx1 - 2.6, y_of(0) + bh / 2), (dx1 - 2.6, oy - bh / 2), st.IMG, lw=0.6)
    text(mid, cy0 - 0.4, "62 M parameters; trained on BraTS 2021 and fixed, with no tuning on any cohort;\n"
         "sliding-window inference, overlap 0.5; patch merging halves the resolution", size=4.8,
         colour=st.MUTED, ha="center", va="bottom")

    # ---- inside each Swin stage: two successive blocks (regular, then shifted windows)
    bx0 = 111.0
    text(bx0, cy1 + 1.6, "Inside each Swin stage", size=5.8, colour=st.IMG, weight="bold")
    cw, eh, es = 11.0, 2.6, 3.7
    for c, attn in enumerate(["W-MSA", "SW-MSA"]):
        x0 = bx0 + c * (cw + 3.4)
        xc = x0 + cw / 2
        y = cy1 - 1.4
        text(xc, y - 0.6, f"block {'l' if c == 0 else 'l+1'}", size=4.8, colour=st.MUTED, ha="center", style="italic", va="bottom")
        y -= 2.6
        ys = {}
        for k, name in enumerate(["LN", attn, "+", "LN", "MLP", "+"]):
            yc = y - k * es
            ys[k] = yc
            if name == "+":
                ax.add_patch(plt.Circle((xc, yc), 1.0, fc="white", ec=st.IMG, lw=0.6, zorder=3))
                text(xc, yc + 0.05, "+", size=5.6, colour=st.IMG, ha="center", va="center", weight="bold")
            else:
                face = st.tint(st.IMG, 0.55) if "MSA" in name else (st.tint(st.IMG, 0.75) if name == "MLP"
                                                                     else st.tint(st.IMG, 0.92))
                box(x0, yc - eh / 2, x0 + cw, yc + eh / 2, edge=st.IMG, face=face, lw=0.5)
                text(xc, yc + 0.05, name, size=4.9, ha="center", va="center",
                     colour="white" if "MSA" in name else st.INK)
            if k:
                arrow((xc, ys[k - 1] - (1.0 if k - 1 in (2,) else eh / 2)), (xc, yc + (1.0 if name == "+" else eh / 2)),
                      st.IMG, lw=0.5)
        for a, b in [(0, 2), (3, 5)]:              # residual connections
            rx = x0 + cw + 1.0
            ya = ys[a] + eh / 2 + 0.7
            ax.plot([xc, rx, rx], [ya, ya, ys[b]], color=st.IMG, lw=0.5)
            arrow((rx, ys[b]), (xc + 1.0, ys[b]), st.IMG, lw=0.5)
    text(bx0, ys[5] - 2.2,
         r"$\hat{z}^{l} = \mathrm{W\text{-}MSA}(\mathrm{LN}(z^{l-1})) + z^{l-1}$" "\n"
         r"$z^{l} = \mathrm{MLP}(\mathrm{LN}(\hat{z}^{l})) + \hat{z}^{l}$", size=5.0)
    # windows: regular, and shifted by half a window (patch grid 8 x 8, windows of 4 x 4 patches)
    g, gx = 9.6, bx0 + 2 * (cw + 3.4) + 0.6
    for r, (lab, cuts) in enumerate([("windows", [0.5]), ("shifted", [0.25, 0.75])]):
        gy = cy1 - 2.4 - (r + 1) * g - r * 4.2
        for t in np.linspace(0, 1, 9):
            ax.plot([gx + t * g, gx + t * g], [gy, gy + g], color=st.RULE, lw=0.3)
            ax.plot([gx, gx + g], [gy + t * g, gy + t * g], color=st.RULE, lw=0.3)
        ax.add_patch(Rectangle((gx, gy), g, g, fc="none", ec=st.IMG, lw=0.7))
        for t in cuts:
            ax.plot([gx + t * g, gx + t * g], [gy, gy + g], color=st.IMG, lw=0.7)
            ax.plot([gx, gx + g], [gy + t * g, gy + t * g], color=st.IMG, lw=0.7)
        text(gx + g / 2, gy - 0.4, lab, size=4.8, colour=st.MUTED, ha="center")
    text(gx + g / 2, cy1 - 0.4, "7³ windows", size=4.6, colour=st.MUTED, ha="center")

    # ---- output: the label map on the T1c slice
    ow = 20.0
    ox, oy0 = 158.5, cy1 - 1.0 - ow
    lx = (dx1 + 2.4)
    ax.plot([dx1, lx, lx], [oy, oy, cy1 + 4.0], color=BLACK, lw=0.6)
    ax.plot([lx, ox + ow / 2], [cy1 + 4.0, cy1 + 4.0], color=BLACK, lw=0.6)
    arrow((ox + ow / 2, cy1 + 4.0), (ox + ow / 2, oy0 + ow + 0.2))
    iax = fig.add_axes([ox / W, oy0 / H, ow / W, ow / H])
    iax.imshow(seq["t1c"], cmap="gray", vmin=0, vmax=1, interpolation="bilinear")
    rgba = np.zeros(seq["label"].shape + (4,))
    for lab, colour in LABEL_RGB.items():
        rgba[seq["label"] == lab] = (*to_rgb(colour), 0.6)
    iax.imshow(rgba, interpolation="nearest")
    iax.set_xticks([]); iax.set_yticks([]); [sp.set_visible(False) for sp in iax.spines.values()]
    for k, (lab, name) in enumerate([(3, "enhancing"), (1, "necrosis"), (2, "FLAIR")]):
        ly = oy0 - 2.2 - k * 2.6
        ax.add_patch(Rectangle((ox, ly - 0.7), 1.5, 1.5, fc=LABEL_RGB[lab], ec="none"))
        text(ox + 2.2, ly + 0.8, name, size=4.8, colour=st.MUTED)
    text(ox, oy0 - 10.2, "volumes and shape\n→ (c), step 2", size=4.8, colour=st.MUTED)


def fig1(output: Path) -> None:
    scans = patient_scans()

    fig = plt.figure(figsize=(st.WIDTH, st.WIDTH * H / W))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, W), ylim=(0, H)); ax.axis("off")

    def text(x, y, s, size=6.0, colour=st.INK, **kw):
        kw.setdefault("ha", "left"); kw.setdefault("va", "top")
        return ax.text(x, y, s, fontsize=size, color=colour, linespacing=1.35, **kw)

    def arrow(a, b, colour=BLACK, lw=0.7, style="-|>", **kw):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=5.5, color=colour, lw=lw,
                                     shrinkA=0, shrinkB=0, zorder=4, **kw))

    def box(x0, y0, x1, y1, edge=BLACK, face="white", lw=0.7, ls="-"):
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

    # ================================================================ (a) one patient's follow-up
    st.panel_header(fig, 0.995, "a", "One patient's follow-up after radiotherapy (MU-Glioma-Post)")
    n = len(scans)
    iw, gap_x, ix0 = 27.0, 9.0, 40.0                 # image width, gap, left edge of the first image
    iy0 = H - 8.0 - iw                              # image bottom
    for k, sc in enumerate(scans):
        x = ix0 + k * (iw + gap_x)
        iax = fig.add_axes([x / W, iy0 / H, iw / W, iw / H])
        show_scan(iax, sc)
        colour = BLACK if sc["label"] == "Progression" else (st.INK if sc["label"] == "No progression" else st.MUTED)
        text(x + iw / 2, H - 4.6, sc["label"], size=6.2, colour=colour, ha="center",
             weight="bold" if sc["label"] == "Progression" else "normal",
             style="italic" if sc["label"] == "Not labelled" else "normal")
        text(x + iw / 2, iy0 - 1.2, f"{sc['weeks']:.1f} weeks after RT\nenhancing {sc['net_cc']:.1f} cc ({sc['et_cc']:.1f})", size=5.6,
             ha="center")
        if k:
            px = x - gap_x
            ax.annotate("", xy=(x - 0.8, iy0 + iw / 2), xytext=(px + 0.8, iy0 + iw / 2),
                        arrowprops=dict(arrowstyle="-|>", color=st.MUTED, lw=0.6, mutation_scale=5))
            text(px + gap_x / 2, iy0 + iw / 2 + 1.0, f"{sc['weeks'] - scans[k - 1]['weeks']:.0f} wk", size=5.4,
                 colour=st.MUTED, ha="center", va="bottom")
    # time axis, to scale: weeks since the end of radiotherapy, with the first 12 weeks shaded
    tx0, tx1, ty = ix0, ix0 + n * iw + (n - 1) * gap_x, iy0 - 10.5
    wmax = 36.0
    wx = lambda w: tx0 + (tx1 - tx0) * w / wmax
    ax.add_patch(Rectangle((wx(0), ty - 1.4), wx(12) - wx(0), 2.8, fc=st.tint(st.HIST, 0.75), ec="none", zorder=2))
    ax.plot([tx0, tx1], [ty, ty], color=st.INK, lw=0.6, zorder=3)
    for w in range(0, int(wmax) + 1, 6):
        ax.plot([wx(w), wx(w)], [ty - 0.7, ty], color=st.INK, lw=0.5)
        text(wx(w), ty - 1.2, str(w), size=5.4, colour=st.MUTED, ha="center")
    for k, sc in enumerate(scans):
        xc = ix0 + k * (iw + gap_x) + iw / 2
        ax.plot([xc, wx(sc["weeks"])], [iy0 - 6.6, ty + 0.4], color=st.RULE, lw=0.5, zorder=1)
        ax.add_patch(plt.Circle((wx(sc["weeks"]), ty), 0.75, fc=BLACK, ec="white", lw=0.3, zorder=4))
    text(wx(6), ty + 2.0, "first 12 weeks", size=5.4, colour=st.HIST, ha="center", va="bottom")
    text((tx0 + tx1) / 2, ty - 4.0, "weeks after the end of radiotherapy", size=5.6, colour=st.MUTED, ha="center")
    text(2.0, H - 8.6, "T1c MRI, the axial slice\nwith most enhancement;\nenhancing tumour outlined", size=5.8)
    ax.plot([2.4, 5.4], [H - 18.4, H - 18.4], color=CONTOUR, lw=1.2)
    text(6.4, H - 17.4, "PRISM (Swin UNETR)", size=5.4, colour=st.MUTED)
    ax.plot([2.4, 5.4], [H - 21.4, H - 21.4], color=RELEASED, lw=0.9, ls="--")
    text(6.4, H - 20.4, "released mask (cc)", size=5.4, colour=st.MUTED)
    text(2.0, H - 25.0, "Label: progression\ndocumented at this scan,\nor no progression for\n\u2265 120 days after it",
         size=5.4, colour=st.MUTED)
    ax.plot([1.0, W - 1.0], [H0 + SG + 1.2, H0 + SG + 1.2], color=st.RULE, lw=0.5)

    # ================================================================ (b) the segmenter
    draw_segmenter(fig, ax, text, arrow, box, sequence_slices(PATIENT, scans[-1]["tp"]))
    ax.plot([1.0, W - 1.0], [H0 + 1.2, H0 + 1.2], color=st.RULE, lw=0.5)

    # ================================================================ (a) the pipeline at one scan
    st.panel_header(fig, (H0 - 0.6) / H, "c", "PRISM at one follow-up scan")

    cols = [(2.0, 28.0), (32.0, 68.0), (72.0, 103.0), (107.0, 140.0), (144.0, 179.0)]
    stages = ["Inputs", "Features", "Models", "Evidence statements", "Record and report"]
    sy = H0 - 9.0
    for i, ((x0, x1), name) in enumerate(zip(cols, stages)):
        ax.add_patch(plt.Circle((x0 + 2.0, sy), 1.9, fc=BLACK, ec="none", zorder=3))
        text(x0 + 2.0, sy, str(i + 1), size=5.8, colour="white", weight="bold", ha="center", va="center")
        text(x0 + 5.2, sy, name, size=6.6, colour=BLACK, weight="bold", va="center")
        ax.plot([x0, x1], [sy - 3.0, sy - 3.0], color=st.RULE, lw=0.5)

    top = sy - 5.5             # top of the content rows
    # Lane centres: imaging above, clinical history below, the combined model between them.
    y_img, y_comb, y_hist = top - 11.0, top - 30.0, top - 49.0

    # ---- 1 Inputs
    x0, x1 = cols[0]
    for k, label in enumerate(["previous", "current"]):
        sx = x0 + k * 14.5
        iax = fig.add_axes([sx / W, (top - 13.0) / H, 13.0 / W, 13.0 / H])
        show_scan(iax, scans[k - 2])
        text(sx + 6.5, top - 13.6, label, size=5.6, colour=st.MUTED, ha="center")
    text(x0, top - 17.4, "T1c, T1, T2, FLAIR MRI;\nmasks from PRISM's\nsegmenter (b) or released\nwith the cohort", size=5.8)

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
    card(x0, e1[0], x1, e1[1], "Split-conformal set", BLACK,
         r"$s_i = 1 - \hat p_i(y_i)$, weighted 1/scans" "\nper patient; $\\alpha = 0.2$\n"
         r"$C(\hat p) = \{y : 1 - \hat p(y) \leq \hat q\,\}$" "\nrefit 70% / calibrate 30% of\ntraining patients",
         size=5.7)
    card(x0, e2[0], x1, e2[1], "Model agreement", BLACK,
         r"$\mathbb{1}[\hat p_{\mathrm{img}} > m_{\mathrm{img}}] = \mathbb{1}[\hat p_{\mathrm{hist}} > m_{\mathrm{hist}}]$"
         "\n$m$: score median in the cohort's\nevaluation scans", size=5.7)
    card(x0, e3[0], x1, e3[1], "Reliability card", BLACK,
         "situation = time window ×\nenhancement state; tested if\n≥ 10 scans of each outcome,\n"
         "otherwise few cases", size=5.7)
    mx = cols[2][1]
    jx = mx + 2.0
    for y, _, colour, _ in models:
        ax.plot([mx, jx], [y, y], color=BLACK, lw=0.7)
    ax.plot([jx, jx], [y_hist, y_img], color=BLACK, lw=0.7)
    for y in ((e1[0] + e1[1]) / 2, (e2[0] + e2[1]) / 2, (e3[0] + e3[1]) / 2):
        arrow((jx, y), (x0, y))

    # ---- 5 Record and report
    x0, x1 = cols[4]
    rx = x1 - x0
    r1 = (top - 17.0, top)
    card(x0, r1[0], x1, r1[1], "Structured record", BLACK, "every value under a fixed\nkey, with its source", size=5.7)
    text(x0 + 1.8, r1[0] + 6.4, "meas.enhancing_cc\nmodel.imaging.score\nconformal.combined.80",
         size=5.3, colour=st.MUTED, family=MONO)
    r2 = (r1[0] - 3.0 - 17.0, r1[0] - 3.0)
    box(x0, r2[0], x1, r2[1], edge=BLACK, ls=(0, (3, 1.5)))
    text(x0 + 1.8, r2[1] - 1.6, "Local language model", size=6.4, colour=BLACK, weight="bold")
    text(x0 + 1.8, r2[1] - 5.6, "Qwen3.8-27B, greedy decoding\nconstrained to a JSON schema:\n"
                                "{section, sentence, cited keys};\nno images, no arithmetic", size=5.7)
    r3 = (eb, r2[0] - 3.0)
    card(x0, r3[0], x1, r3[1], "Deterministic checker", BLACK,
         "every number in a cited field;\nflags, set, agreement, tier\nstated; no diagnosis or advice;\n"
         "verifier binds each number and\ndirection to its region", size=5.7)
    text(x0 + 1.8, r3[0] + 3.0, "accept, or reject without repair", size=5.6, colour=BLACK, weight="bold")
    cx = (x0 + x1) / 2
    bus = cols[3][1] + 2.0                       # every statement (and the scores) enter the record
    for y in ((e1[0] + e1[1]) / 2, (e2[0] + e2[1]) / 2, (e3[0] + e3[1]) / 2):
        ax.plot([cols[3][1], bus], [y, y], color=BLACK, lw=0.7)
    ry = (r1[0] + r1[1]) / 2
    ax.plot([bus, bus], [(e3[0] + e3[1]) / 2, ry], color=BLACK, lw=0.7)
    arrow((bus, ry), (x0, ry))
    arrow((cx, r1[0]), (cx, r2[1]))
    arrow((cx, r2[0]), (cx, r3[1]))

    # ================================================================ (b) evaluation protocol
    by1 = eb - 7.0
    st.panel_header(fig, (by1 + 2.4) / H, "d", "Evaluation")
    bt, bb = by1 - 4.0, 7.5
    mid = (bt + bb) / 2
    card(2.0, bb, 50.0, bt, "Development: MU-Glioma-Post", BLACK,
         "126 grade 4 patients; 5 repeats of 5-fold\ncross validation grouped by patient; pooled\n"
         "held-out AUC on 146 scans of 80 patients", size=5.7)
    card(56.0, bb, 92.0, bt, "Lock", BLACK,
         "each model fitted once on all\n181 MU detection scans, then\nfrozen; reduced clinical history\n"
         "where a cohort lacks dates", size=5.7)
    eh = (bt - bb - 2.0) / 2
    for y0, title, body in [(bt - eh, "External: LUMIERE", "178 scans of 79 patients; 3-label masks"),
                            (bb, "External: UCSF-ALPTDG", "69 second scans of 69 patients")]:
        box(98.0, y0, 140.0, y0 + eh, edge=BLACK)
        text(99.8, y0 + eh - 1.4, title, size=6.4, colour=BLACK, weight="bold")
        text(99.8, y0 + eh - 4.9, body, size=5.7)
    card(146.0, bb, 179.0, bt, "Measured", BLACK,
         "AUC, 95% CI from bootstrap\nsamples of patients; coverage\nof the 80% sets; reports\npassing the checker",
         size=5.7)
    arrow((50.0, mid), (56.0, mid))
    arrow((92.0, mid), (95.0, mid), style="-")
    ax.plot([95.0, 95.0], [bt - eh / 2, bb + eh / 2], color=BLACK, lw=0.7)
    arrow((95.0, bt - eh / 2), (98.0, bt - eh / 2)); arrow((95.0, bb + eh / 2), (98.0, bb + eh / 2))
    arrow((140.0, mid), (146.0, mid))
    text(2.0, bb - 2.2,
         "Label: the first scan at documented progression versus a scan followed by \u2265 120 days without "
         "progression (LUMIERE: rated stable or responding).", size=5.7, colour=st.MUTED)

    st.save(fig, output, "fig1_system")


if __name__ == "__main__":
    fig1(Path(__file__).resolve().parents[1] / "docs/manuscript/figures")
