"""Stage `radiomics`: corrected, compartment-resolved PyRadiomics features.

Fixes vs the legacy extraction (train.py preprocess_image + binWidth 25):
  * intensity normalised by the whole-brain mean/SD (keeps lesion contrast vs normal brain), not within-lesion;
  * fixed bin count (32) -> ~30 grey levels per ROI instead of 2;
  * no second N4 (FeTS inputs are already bias-corrected);
  * one feature set per compartment: ET, NETC, SNFH, tumour core, whole lesion, 5 mm peri-cavity rim.
A second pass on 1-voxel-eroded ROIs (T1c + FLAIR) supports a label-free stability (ICC) filter.

    python -m prism radiomics [--limit N]   # -> outputs/features/{radiomics,radiomics_eroded}.csv

Known limitations (docs/results/FIX_FEATURES.md):
  * discretisation uses a fixed bin COUNT per ROI, not the IBSI-recommended fixed bin WIDTH for (z-scored) MRI: the
    grey-level width varies with each ROI's intensity range, so texture values mix contrast and range differences;
  * the eroded-ROI pass covers T1c/FLAIR texture + first-order only (1116 of 2316 columns), so the c3 ICC filter does
    not screen T1/T2 texture or shape features (those pass unfiltered);
  * the 5 mm peri-cavity rim is a 5-iteration city-block dilation (L1 <= 5 voxels), thinner than a Euclidean 5 mm.

legacy_features() loads the original PRISM extraction (within-lesion z-score, binWidth 25 -> ~2 grey levels)
from the optional processed download; it is kept only as a comparator.
"""

from __future__ import annotations

import argparse
import json
import logging
from concurrent.futures import ProcessPoolExecutor

import nibabel as nib
import numpy as np
import pandas as pd
import SimpleITK as sitk
from radiomics import featureextractor
from scipy import ndimage

from prism.config import (LABEL_ET, LABEL_NETC, LABEL_RC, LABEL_SNFH, LEGACY_FEATURES_DIR, RADIOMICS,
                          RADIOMICS_ERODED, WORKERS, mu_scan_paths)
from prism.data.mu import load_index

SEQUENCES = ("t1c", "flair", "t1", "t2")
PERTURB_SEQUENCES = ("t1c", "flair")
MIN_VOXELS = 30
RIM_MM = 5
SETTINGS = {"binCount": 32, "normalize": False, "force2D": False, "label": 1, "minimumROISize": MIN_VOXELS,
            "additionalInfo": False}
TEXTURE = ["firstorder", "glcm", "glrlm", "glszm", "gldm", "ngtdm"]


def rois(mask: np.ndarray, brain: np.ndarray) -> dict[str, np.ndarray]:
    et, netc, snfh, rc = (mask == LABEL_ET), (mask == LABEL_NETC), (mask == LABEL_SNFH), (mask == LABEL_RC)
    out = {"et": et, "netc": netc, "snfh": snfh, "core": et | netc, "lesion": et | netc | snfh}
    if rc.any():
        out["rim"] = ndimage.binary_dilation(rc, iterations=RIM_MM) & ~rc & brain
    return out


def _extractor(classes):
    logging.getLogger("radiomics").setLevel(logging.ERROR)
    ex = featureextractor.RadiomicsFeatureExtractor(**SETTINGS)
    ex.disableAllFeatures()
    ex.enableImageTypes(Original={})
    for c in classes:
        ex.enableFeatureClassByName(c)
    return ex


def _to_sitk(a: np.ndarray) -> sitk.Image:
    img = sitk.GetImageFromArray(np.ascontiguousarray(np.transpose(a, (2, 1, 0))))
    img.SetSpacing((1.0, 1.0, 1.0))
    return img


def extract_scan(args) -> tuple[dict, dict]:
    pid, tp = args
    stem = f"{pid}_{tp}"
    paths = mu_scan_paths(pid, tp)
    full, eroded = {"scan_id": stem}, {"scan_id": stem}
    try:
        mask = np.rint(np.asarray(nib.load(str(paths["mask"])).dataobj)).astype(np.uint8)
        imgs = {s: np.asarray(nib.load(str(paths[s])).dataobj).astype(np.float32) for s in SEQUENCES}
    except FileNotFoundError:
        return full, eroded
    brain = np.all([v > 0 for v in imgs.values()], axis=0)
    norm = {}
    for s, a in imgs.items():
        v = a[brain]
        norm[s] = _to_sitk(np.where(brain, (a - v.mean()) / (v.std() + 1e-6), 0).astype(np.float32))
    tex, shape = _extractor(TEXTURE), _extractor(["shape"])

    def run(ex, img, roi):
        if roi.sum() <= MIN_VOXELS:
            return {}
        try:
            r = ex.execute(img, _to_sitk(roi.astype(np.uint8)))
        except ValueError:  # pyradiomics mask checks (e.g. ROI at the minimum size)
            return {}
        return {k.replace("original_", ""): float(v) for k, v in r.items() if not k.startswith("diagnostics")}

    for rname, roi in rois(mask, brain).items():
        for k, v in run(shape, norm["t1c"], roi).items():
            full[f"{rname}_{k}"] = v
        er = ndimage.binary_erosion(roi)
        for s in SEQUENCES:
            for k, v in run(tex, norm[s], roi).items():
                full[f"{s}_{rname}_{k}"] = v
            if s in PERTURB_SEQUENCES:
                for k, v in run(tex, norm[s], er).items():
                    eroded[f"{s}_{rname}_{k}"] = v
    return full, eroded


def legacy_features(cohort: pd.DataFrame, modalities=("t1c", "flair")) -> pd.DataFrame:
    """Original PRISM PyRadiomics extraction (pre-correction: 2 grey levels for texture) for T1c + FLAIR."""
    if not LEGACY_FEATURES_DIR.exists():
        raise FileNotFoundError(f"{LEGACY_FEATURES_DIR} missing: download the optional processed release (README)")
    rows = []
    for pid, tp in zip(cohort.patient_id, cohort.timepoint):
        d = json.loads((LEGACY_FEATURES_DIR / pid / f"{tp}.json").read_text())
        rows.append({k: v for k, v in d.items() if k.split("_", 1)[0] in modalities and isinstance(v, (int, float))
                     and not isinstance(v, bool) and not k.endswith(("_mask_mean", "_mask_std", "_mask_voxels"))})
    return pd.DataFrame(rows, index=cohort.index)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism radiomics", description=__doc__)
    ap.add_argument("--workers", type=int, default=WORKERS)
    ap.add_argument("--limit", type=int, help="first N timepoints only (smoke test)")
    a = ap.parse_args(argv)
    index = load_index()
    jobs = list(zip(index.patient_id, index.timepoint))[: a.limit]
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(extract_scan, jobs, chunksize=1))
    RADIOMICS.parent.mkdir(parents=True, exist_ok=True)
    full = pd.DataFrame([r[0] for r in res])
    eroded = pd.DataFrame([r[1] for r in res])
    full.to_csv(RADIOMICS, index=False)
    eroded.to_csv(RADIOMICS_ERODED, index=False)
    print(f"{len(full)} scans, {full.shape[1] - 1} features; eroded {eroded.shape[1] - 1}")

