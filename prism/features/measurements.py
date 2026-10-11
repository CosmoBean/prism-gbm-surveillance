"""Stage `measurements`: compartment concepts per timepoint + past-only longitudinal deltas.

Computed for every MU timepoint (not only eligible scans) so that priors/nadir can use all earlier MRIs.
Images are FeTS-preprocessed, skull-stripped, 1 mm isotropic (BraTS space), so voxels = mm^3.

    python -m prism measurements   # -> outputs/features/measurements.csv
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import nibabel as nib
import numpy as np
import pandas as pd
from scipy import ndimage

from prism.config import LABEL_ET, LABEL_NETC, LABEL_RC, LABEL_SNFH, MEASUREMENTS, WORKERS, mu_scan_paths
from prism.data.mu import load_index
NEAR_CAVITY_MM = 5
NAWM_MARGIN_MM = 10  # Euclidean margin around lesion + cavity excluded from the normal-brain reference
PD_MIN_NADIR_CC = 0.1  # below this the ET nadir is "no measurable enhancement": growth is a new lesion, not a % change
DELTA_SOURCES = ("et_cc", "netc_cc", "snfh_cc", "tumor_cc", "lesion_cc", "et_n_components", "et_max_axial_mm2",
                 "t1c_et_rel", "flair_snfh_rel")


def _load(path) -> np.ndarray:
    return np.asarray(nib.load(str(path)).dataobj)


def reference_mask(brain: np.ndarray, abnormal: np.ndarray, margin_mm: float = NAWM_MARGIN_MM,
                   spacing=(1.0, 1.0, 1.0)) -> np.ndarray:
    """Normal-appearing brain: brain voxels at Euclidean distance > margin_mm from any abnormal voxel."""
    if not abnormal.any():
        return brain.copy()
    return brain & (ndimage.distance_transform_edt(~abnormal, sampling=spacing) > margin_mm)


def scan_concepts(args: tuple[str, str]) -> dict:
    pid, tp = args
    paths = mu_scan_paths(pid, tp)
    row = {"scan_id": f"{pid}_{tp}", "patient_id": pid, "timepoint": tp}
    try:
        img = nib.load(str(paths["mask"]))
        spacing = tuple(float(z) for z in img.header.get_zooms()[:3])
        mask = np.rint(np.asarray(img.dataobj)).astype(np.uint8)
        t1c = _load(paths["t1c"]).astype(np.float32)
        flair = _load(paths["flair"]).astype(np.float32)
    except FileNotFoundError:
        return row
    et, netc, snfh, rc = (mask == LABEL_ET), (mask == LABEL_NETC), (mask == LABEL_SNFH), (mask == LABEL_RC)
    tumor, lesion = et | netc, et | netc | snfh
    cc = lambda m: float(m.sum()) / 1000.0
    row.update(et_cc=cc(et), netc_cc=cc(netc), snfh_cc=cc(snfh), rc_cc=cc(rc), tumor_cc=cc(tumor), lesion_cc=cc(lesion))
    row["et_fraction_of_tumor"] = row["et_cc"] / row["tumor_cc"] if row["tumor_cc"] > 0 else np.nan
    row["snfh_to_tumor_ratio"] = row["snfh_cc"] / row["tumor_cc"] if row["tumor_cc"] > 0 else np.nan
    row["has_cavity"] = float(rc.any())

    # Multifocality and a bidimensional-burden proxy (largest single-slice ET area; not RANO measurement).
    labels, n = ndimage.label(et, structure=np.ones((3, 3, 3)))
    sizes = np.bincount(labels.ravel())[1:] if n else np.array([])
    row["et_n_components"] = float((sizes >= 10).sum())  # ignore specks < 10 voxels
    row["et_largest_component_fraction"] = float(sizes.max() / sizes.sum()) if n else np.nan
    row["et_max_axial_mm2"] = float(et.sum(axis=(0, 1)).max()) if et.any() else 0.0

    # Enhancement relative to the resection cavity wall.
    if rc.any() and et.any():
        dist_to_rc = ndimage.distance_transform_edt(~rc)
        row["et_near_cavity_fraction"] = float((dist_to_rc[et] <= NEAR_CAVITY_MM).mean())
        row["et_cavity_distance_mm_p50"] = float(np.median(dist_to_rc[et]))
    else:
        row["et_near_cavity_fraction"] = np.nan
        row["et_cavity_distance_mm_p50"] = np.nan

    # Intensities relative to normal-appearing brain (brain minus everything within 10 mm of lesion/cavity).
    brain = (t1c > 0) & (flair > 0)
    nab = reference_mask(brain, lesion | rc, NAWM_MARGIN_MM, spacing)
    ref_t1c = np.median(t1c[nab]) if nab.sum() > 1000 else np.nan
    ref_flair = np.median(flair[nab]) if nab.sum() > 1000 else np.nan
    rel = lambda img, m, ref: float(np.median(img[m]) / ref) if m.sum() >= 10 and ref and np.isfinite(ref) else np.nan
    row.update(t1c_et_rel=rel(t1c, et, ref_t1c), t1c_netc_rel=rel(t1c, netc, ref_t1c),
               flair_snfh_rel=rel(flair, snfh, ref_flair), flair_netc_rel=rel(flair, netc, ref_flair),
               t1c_et_p90_rel=float(np.percentile(t1c[et], 90) / ref_t1c) if et.sum() >= 10 and np.isfinite(ref_t1c) else np.nan)
    return row


def add_deltas(concepts: pd.DataFrame) -> pd.DataFrame:
    """Past-only change features: vs the most recent earlier MRI and vs the nadir of all earlier MRIs."""
    df = concepts.sort_values(["patient_id", "mri_day"]).reset_index(drop=True)
    out = []
    for _, g in df.groupby("patient_id", sort=False):
        g = g.reset_index(drop=True)
        for i in range(len(g)):
            r = {"scan_id": g.scan_id[i]}
            prev = g.iloc[:i]
            prev = prev[prev.mri_day < g.mri_day[i]]
            r["has_prior"] = float(len(prev) > 0)
            r["n_prior_scans"] = float(len(prev))
            if len(prev):
                p = prev.iloc[-1]
                r["days_since_prior"] = g.mri_day[i] - p.mri_day
                for s in DELTA_SOURCES:
                    cur, old = g[s][i], p[s]
                    r[f"d_{s}"] = cur - old
                    if s.endswith("_cc"):
                        r[f"logratio_{s}"] = np.log((cur + 0.1) / (old + 0.1))
                        r[f"rate_{s}_per30d"] = (cur - old) / max(r["days_since_prior"], 1) * 30
                for s in ("et_cc", "tumor_cc", "snfh_cc", "lesion_cc"):
                    nadir = prev[s].min()
                    r[f"d_nadir_{s}"] = g[s][i] - nadir
                    r[f"logratio_nadir_{s}"] = np.log((g[s][i] + 0.1) / (nadir + 0.1))
                r.update(volumetric_pd(g.et_cc[i], prev["et_cc"].min()))
                r["new_et_component"] = float(g.et_n_components[i] > prev.iloc[-1].et_n_components)
            out.append(r)
    return pd.DataFrame(out)


def volumetric_pd(et_cc: float, nadir_et_cc: float) -> dict:
    """RANO-style volumetric flag (indicative only): >= 40% ET increase from a measurable nadir (>= PD_MIN_NADIR_CC)
    and >= 1 cc absolute. Growth >= 1 cc from a non-measurable (~0 cc) nadir is flagged separately as new enhancement."""
    grew = et_cc - nadir_et_cc >= 1.0
    measurable = nadir_et_cc >= PD_MIN_NADIR_CC
    return {"vol_pd_flag": float(measurable and grew and et_cc >= 1.4 * nadir_et_cc),
            "et_new_from_zero_nadir": float(not measurable and grew)}


def load_measurements(scan_ids) -> pd.DataFrame:
    """Measurement rows aligned to `scan_ids` (positional index)."""
    return pd.read_csv(MEASUREMENTS).set_index("scan_id").reindex(scan_ids).reset_index(drop=True)


def main(argv=None) -> None:
    index = load_index()
    jobs = list(zip(index.patient_id, index.timepoint))
    with ProcessPoolExecutor(min(WORKERS, 48)) as ex:
        concepts = pd.DataFrame(list(ex.map(scan_concepts, jobs, chunksize=4)))
    concepts["mri_day"] = pd.to_numeric(index["days_from_diagnosis_to_mri"], errors="coerce").to_numpy()
    concepts = concepts[concepts.mri_day.notna() & concepts.et_cc.notna()]
    meas = concepts.merge(add_deltas(concepts), on="scan_id", how="left")
    MEASUREMENTS.parent.mkdir(parents=True, exist_ok=True)
    meas.to_csv(MEASUREMENTS, index=False)
    print(f"{len(meas)} timepoints, {meas.shape[1]} columns; has_prior {int(meas.has_prior.sum())}")
    print(meas.describe().T[["count", "mean", "50%"]].round(3).head(45).to_string())

