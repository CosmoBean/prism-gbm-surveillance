"""Measurement table (D5): compartment concepts per timepoint + past-only longitudinal deltas.

Computed for every MU timepoint (not only eligible scans) so that priors/nadir can use all earlier MRIs.
Images are FeTS-preprocessed, skull-stripped, 1 mm isotropic (BraTS space), so voxels = mm^3.

    uv run python -m prism.measurements   # -> outputs/measurements/{concepts.csv, measurements.csv}
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from scipy import ndimage

from prism.config import EXPERIMENT_INDEX, LABEL_ET, LABEL_NETC, LABEL_RC, LABEL_SNFH, OUTPUTS, REPO

RAW = REPO / "mu-glioma-post-raw" / "MU-Glioma-Post"
NEAR_CAVITY_MM = 5
NAWM_MARGIN_MM = 10
DELTA_SOURCES = ("et_cc", "netc_cc", "snfh_cc", "tumor_cc", "lesion_cc", "et_n_components", "et_max_axial_mm2",
                 "t1c_et_rel", "flair_snfh_rel")


def _load(path: Path) -> np.ndarray:
    return np.asarray(nib.load(str(path)).dataobj)


def scan_concepts(args: tuple[str, str]) -> dict:
    pid, tp = args
    d = RAW / pid / tp
    stem = f"{pid}_{tp}"
    row = {"scan_id": f"{pid}_{tp}", "patient_id": pid, "timepoint": tp}
    try:
        mask = np.rint(_load(d / f"{stem}_tumorMask.nii.gz")).astype(np.uint8)
        t1c = _load(d / f"{stem}_brain_t1c.nii.gz").astype(np.float32)
        flair = _load(d / f"{stem}_brain_t2f.nii.gz").astype(np.float32)
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

    # Intensities relative to normal-appearing brain (brain minus lesion/cavity dilated by 10 mm).
    brain = (t1c > 0) & (flair > 0)
    abnormal = ndimage.binary_dilation(lesion | rc, iterations=NAWM_MARGIN_MM)
    nab = brain & ~abnormal
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
                # RANO-style volumetric flag (indicative only): >= 40% ET increase from nadir and >= 1 cc absolute
                nadir_et = prev["et_cc"].min()
                r["vol_pd_flag"] = float(g.et_cc[i] >= 1.4 * nadir_et and g.et_cc[i] - nadir_et >= 1.0)
                r["new_et_component"] = float(g.et_n_components[i] > prev.iloc[-1].et_n_components)
            out.append(r)
    return pd.DataFrame(out)


def main() -> None:
    index = pd.read_csv(EXPERIMENT_INDEX, low_memory=False)
    jobs = list(zip(index.patient_id, index.timepoint))
    with ProcessPoolExecutor(48) as ex:
        concepts = pd.DataFrame(list(ex.map(scan_concepts, jobs, chunksize=4)))
    concepts["mri_day"] = pd.to_numeric(index["days_from_diagnosis_to_mri"], errors="coerce").to_numpy()
    concepts = concepts[concepts.mri_day.notna() & concepts.et_cc.notna()]
    meas = concepts.merge(add_deltas(concepts), on="scan_id", how="left")
    out = OUTPUTS / "measurements"
    out.mkdir(parents=True, exist_ok=True)
    concepts.to_csv(out / "concepts.csv", index=False)
    meas.to_csv(out / "measurements.csv", index=False)
    print(f"{len(meas)} timepoints, {meas.shape[1]} columns; has_prior {int(meas.has_prior.sum())}")
    print(meas.describe().T[["count", "mean", "50%"]].round(3).head(45).to_string())


if __name__ == "__main__":
    main()
