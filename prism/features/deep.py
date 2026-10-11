"""Frozen deep features: SwinUNETR (swinViT) encoder activations pooled within tumour compartments.

Encoders (same MONAI SwinUNETR architecture, 4 channels FLAIR/T1c/T1/T2, feature size 48):
  brats21   MONAI BraTS 2021 SwinUNETR fold 1 (Apache-2.0; GitHub release MONAI-extra-test-data/0.8.1)
  bsf       BrainSegFounder BraTS-finetune (UK Biobank MTA; huggingface.co/smilelab/BrainSegFounder)
  random    same architecture, random weights (torch seed 0): the mandatory control (and the PRISM report's encoder type)

Input: skull-stripped 1 mm volumes in LPS orientation, z-scored within brain per channel, zero-padded to a multiple of 32.
All five swinViT stages (48/96/192/384/768 ch) are mask-weighted mean pooled per region at feature-map resolution
(area-downsampled mask), averaged over 8 flip test-time augmentations -> 1488 features per region.

Regions  MU       lesion (ET|NETC|SNFH), et, netc, snfh, etsnfh (ET|SNFH), rim (5 mm peri-cavity ring, as in radiomics)
         LUMIERE  et, snfh, etsnfh, lesion (DeepBraTumIA; its "necrosis" includes the cavity, so lesion/netc differ)
Regions with <= 30 voxels are NaN.

    CUDA_VISIBLE_DEVICES=1 uv run --frozen --no-sync python -m prism.features.deep [--limit N] [--cohort mu lumiere]
    # -> outputs/features/deep_{encoder}.parquet (MU, all index scans), deep_{encoder}_lumiere.parquet
Weights are read from $PRISM_DATA/weights (gitignored; see docs/results/DEEP_FEATURES.md for sources and licences).
"""

from __future__ import annotations

import argparse
import itertools
import time
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from scipy import ndimage

from prism.config import (DATA, LABEL_ET, LABEL_NETC, LABEL_RC, LABEL_SNFH, LUMIERE_COHORT, LUMIERE_ROOT, OUTPUTS,
                          mu_scan_paths)
from prism.data.mu import load_index

WEIGHTS = DATA / "weights"
ENCODERS = {
    "brats21": (WEIGHTS / "brats21_swinunetr_fold1_f48" / "model.pt", "state_dict"),
    "bsf": (WEIGHTS / "brainsegfounder_brats_ft.pt", None),
    "random": (None, None),
}
STAGE_DIMS = (48, 96, 192, 384, 768)
MIN_VOXELS = 30
RIM_MM = 5
LUMIERE_IMAGES = LUMIERE_ROOT / "imaging" / "Imaging"
LUMIERE_SEQ = {"flair": "flair", "t1c": "ct1", "t1": "t1", "t2": "t2"}  # DeepBraTumIA atlas skull_strip files
LUMIERE_LABELS = {"et": 1, "necrosis": 2, "snfh": 3}  # seg_mask.nii.gz (checked against measured_volumes_in_mm3.json)
CHANNELS = ("flair", "t1c", "t1", "t2")  # MONAI BraTS21 / BrainSegFounder channel order


def feature_path(encoder: str, cohort: str = "mu") -> Path:
    return OUTPUTS / "features" / (f"deep_{encoder}.parquet" if cohort == "mu" else f"deep_{encoder}_{cohort}.parquet")


def load_features(encoder: str, scan_ids, cohort: str = "mu") -> pd.DataFrame:
    return pd.read_parquet(feature_path(encoder, cohort)).set_index("scan_id").reindex(list(scan_ids))


def load_encoder(name: str, device="cuda"):
    from monai.networks.nets import SwinUNETR
    torch.manual_seed(0)
    m = SwinUNETR(in_channels=4, out_channels=3, feature_size=48, use_checkpoint=False)
    path, key = ENCODERS[name]
    if path is not None:
        sd = torch.load(path, map_location="cpu", weights_only=False)
        sd = sd[key] if key else sd
        sd = sd.get("state_dict", sd)
        m.load_state_dict({k.replace("module.", ""): v for k, v in sd.items()}, strict=True)
    return m.to(device).eval()


# ---------------------------------------------------------------- inputs
def _to_lps(img: nib.Nifti1Image) -> np.ndarray:
    ornt = nib.orientations.ornt_transform(nib.io_orientation(img.affine), nib.orientations.axcodes2ornt("LPS"))
    return nib.orientations.apply_orientation(np.asarray(img.dataobj), ornt)


def _prepare(vols: dict[str, np.ndarray], regions: dict[str, np.ndarray]):
    img = np.stack([vols[c].astype(np.float32) for c in CHANNELS])
    brain = (img != 0).any(0)
    for c in range(len(img)):
        v = img[c][brain]
        img[c] = np.where(brain, (img[c] - v.mean()) / (v.std() + 1e-6), 0)
    pad = [(0, 0)] + [(0, -s % 32) for s in img.shape[1:]]
    img = np.pad(img, pad)
    reg = {k: np.pad(r, pad[1:]).astype(np.float32) for k, r in regions.items() if r.sum() > MIN_VOXELS}
    return img, reg


def mu_inputs(scan_id: str):
    pid, tp = scan_id.split("_Timepoint_")[0], "Timepoint_" + scan_id.split("_Timepoint_")[1]
    p = mu_scan_paths(pid, tp)
    vols = {s: np.asarray(nib.load(str(p[s])).dataobj) for s in CHANNELS}
    mask = np.rint(np.asarray(nib.load(str(p["mask"])).dataobj)).astype(np.uint8)
    brain = np.all([v > 0 for v in vols.values()], axis=0)
    et, netc, snfh, rc = (mask == LABEL_ET), (mask == LABEL_NETC), (mask == LABEL_SNFH), (mask == LABEL_RC)
    regions = {"lesion": et | netc | snfh, "et": et, "netc": netc, "snfh": snfh, "etsnfh": et | snfh}
    if rc.any():
        regions["rim"] = ndimage.binary_dilation(rc, iterations=RIM_MM) & ~rc & brain
    return _prepare(vols, regions)


def lumiere_inputs(scan_id: str):
    pid, date = scan_id.split("_", 1)
    d = LUMIERE_IMAGES / pid / date / "DeepBraTumIA-segmentation" / "atlas"
    vols = {s: _to_lps(nib.load(str(d / "skull_strip" / f"{f}_skull_strip.nii.gz"))) for s, f in LUMIERE_SEQ.items()}
    seg = np.rint(_to_lps(nib.load(str(d / "segmentation" / "seg_mask.nii.gz")))).astype(np.uint8)
    et, nec, snfh = (seg == LUMIERE_LABELS[k] for k in ("et", "necrosis", "snfh"))
    return _prepare(vols, {"lesion": et | nec | snfh, "et": et, "snfh": snfh, "etsnfh": et | snfh})


def _identity(x):
    return x


class _Scans(torch.utils.data.Dataset):
    def __init__(self, ids, fn):
        self.ids, self.fn = list(ids), fn

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, i):
        try:
            return self.ids[i], *self.fn(self.ids[i])
        except FileNotFoundError:
            return self.ids[i], None, {}


# ---------------------------------------------------------------- features
FLIPS = [tuple(a for a, f in zip((2, 3, 4), fl) if f) for fl in itertools.product((0, 1), repeat=3)]


@torch.no_grad()
def pooled(model, img: np.ndarray, regions: dict[str, np.ndarray], device="cuda", batch=4) -> dict[str, float]:
    x = torch.from_numpy(img)[None].to(device)
    acc = None
    for i in range(0, len(FLIPS), batch):
        fl = FLIPS[i:i + batch]
        xb = torch.cat([x.flip(f) if f else x for f in fl])
        with torch.autocast("cuda", dtype=torch.bfloat16):
            hid = model.swinViT(xb, model.normalize)
        hid = [torch.stack([h[j].flip([a - 1 for a in f]) if f else h[j] for j, f in enumerate(fl)]).float().sum(0)
               for h in hid]
        acc = hid if acc is None else [a + h for a, h in zip(acc, hid)]
    acc = [a / len(FLIPS) for a in acc]
    out = {}
    for rname, r in regions.items():
        m = torch.from_numpy(r)[None, None].to(device)
        for s, h in enumerate(acc):
            w = F.adaptive_avg_pool3d(m, h.shape[1:])[0, 0]
            v = (h * w).sum((1, 2, 3)) / w.sum().clamp(min=1e-6)
            out.update({f"{rname}_s{s}_{c}": float(x_) for c, x_ in enumerate(v.cpu().numpy())})
    return out


def extract(ids, fn, encoders, workers=8):
    models = {e: load_encoder(e) for e in encoders}
    rows = {e: [] for e in encoders}
    loader = torch.utils.data.DataLoader(_Scans(ids, fn), batch_size=None, num_workers=workers, prefetch_factor=2,
                                         collate_fn=_identity)
    t = time.time()
    for i, (sid, img, regions) in enumerate(loader):
        for e, m in models.items():
            rows[e].append({"scan_id": sid, **(pooled(m, img, regions) if img is not None else {})})
        if i % 25 == 0:
            print(f"  {i + 1}/{len(ids)} {sid} {time.time() - t:.0f}s", flush=True)
    return {e: pd.DataFrame(r) for e, r in rows.items()}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism deep", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--encoders", nargs="+", default=list(ENCODERS))
    ap.add_argument("--cohort", nargs="+", default=["mu", "lumiere"])
    ap.add_argument("--limit", type=int, help="first N scans only (smoke test; nothing is written)")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    torch.backends.cuda.matmul.allow_tf32 = True
    for cohort in a.cohort:
        if cohort == "mu":
            idx = load_index()
            ids, fn = idx.loc[idx.complete.astype(bool), "scan_id"].tolist(), mu_inputs
        else:
            ids, fn = pd.read_csv(LUMIERE_COHORT).scan_id.tolist(), lumiere_inputs
        ids = ids[: a.limit]
        print(f"== {cohort}: {len(ids)} scans, encoders {a.encoders}", flush=True)
        res = extract(ids, fn, a.encoders, a.workers)
        for e, df in res.items():
            print(f"{cohort} {e}: {len(df)} scans, {df.shape[1] - 1} features, "
                  f"{int(df.drop(columns='scan_id').notna().any(axis=1).sum())} with features")
            if a.limit is None:
                feature_path(e, cohort).parent.mkdir(parents=True, exist_ok=True)
                df.astype({c: np.float32 for c in df.columns if c != "scan_id"}).to_parquet(feature_path(e, cohort), index=False)


if __name__ == "__main__":
    main()
