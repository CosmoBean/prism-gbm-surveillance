"""Paths and study constants.

Every path can be overridden with an environment variable, so the pipeline runs anywhere the data is:

    PRISM_DATA      root for the datasets            (default: <repo>/data)
    PRISM_MU        MU-Glioma-Post TCIA package      (default: $PRISM_DATA/mu-glioma-post)
    PRISM_LUMIERE   LUMIERE figshare download        (default: $PRISM_DATA/lumiere)
    PRISM_OUTPUTS   everything the pipeline writes   (default: <repo>/outputs)
    PRISM_WORKERS   processes for image stages       (default: all CPUs)
"""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("PRISM_DATA", REPO / "data"))
MU_ROOT = Path(os.environ.get("PRISM_MU", DATA / "mu-glioma-post"))
MU_IMAGES = MU_ROOT / "MU-Glioma-Post"
MU_CLINICAL = MU_ROOT / "MU-Glioma-Post_ClinicalData-July2025.xlsx"
LUMIERE_ROOT = Path(os.environ.get("PRISM_LUMIERE", DATA / "lumiere"))
# Optional: original PRISM radiomics (2 grey levels) from huggingface.co/datasets/sbandred/mu-glioma-post-processed.
LEGACY_FEATURES_DIR = DATA / "mu-reference-processed" / "postoperative_progression_surveillance" / "features"

OUTPUTS = Path(os.environ.get("PRISM_OUTPUTS", REPO / "outputs"))
WORKERS = int(os.environ.get("PRISM_WORKERS", os.cpu_count() or 1))

# Stage outputs (one file per artifact; later stages only read these).
MU_INDEX = OUTPUTS / "data" / "mu_index.csv"
MU_COHORT = OUTPUTS / "data" / "mu_cohort.csv"
MU_FLOW = OUTPUTS / "data" / "mu_flow.csv"
FOLDS = OUTPUTS / "data" / "folds.csv"
LUMIERE_COHORT = OUTPUTS / "data" / "lumiere_cohort.csv"
MEASUREMENTS = OUTPUTS / "features" / "measurements.csv"
RADIOMICS = OUTPUTS / "features" / "radiomics.csv"
RADIOMICS_ERODED = OUTPUTS / "features" / "radiomics_eroded.csv"
RESULTS = OUTPUTS / "results"

HORIZONS = (90, 120, 180)
PRIMARY_HORIZON = 120
EARLY_POST_RT_DAYS = 84  # RANO 2.0: first 12 weeks after radiotherapy
N_REPEATS = 5
N_FOLDS = 5

# MU-Glioma-Post mask labels (verified with BraTS zero-shot: ET <-> label 3).
LABEL_NETC, LABEL_SNFH, LABEL_ET, LABEL_RC = 1, 2, 3, 4
# File suffixes per sequence in the MU package.
MU_SEQUENCES = {"t1": "t1n", "t1c": "t1c", "flair": "t2f", "t2": "t2w"}


def mu_scan_paths(patient_id: str, timepoint: str) -> dict[str, Path]:
    """Image and mask paths for one MU timepoint (keys: t1, t1c, flair, t2, mask)."""
    d = MU_IMAGES / patient_id / timepoint
    stem = f"{patient_id}_{timepoint}"
    paths = {s: d / f"{stem}_brain_{f}.nii.gz" for s, f in MU_SEQUENCES.items()}
    paths["mask"] = d / f"{stem}_tumorMask.nii.gz"
    return paths
