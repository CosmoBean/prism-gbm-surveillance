"""Feature sets. Each returns a raw scan-level matrix; all fitted preprocessing happens in-fold."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from prism.config import LEGACY_FEATURES_DIR

COMPARTMENTS = {"netc": "label1_voxels", "snfh": "label2_voxels", "et": "label3_voxels", "rc": "label4_voxels"}


def clinical(cohort: pd.DataFrame) -> pd.DataFrame:
    """Age, sex and molecular status with an explicit unknown level (reference: wildtype / unmethylated)."""
    return pd.DataFrame({
        "age": cohort["age"],
        "male": cohort["male"],
        "idh_mutant": cohort["idh"].eq("mutant").astype(float),
        "idh_unknown": cohort["idh"].eq("unknown").astype(float),
        "mgmt_methylated": cohort["mgmt"].eq("methylated").astype(float),
        "mgmt_unknown": cohort["mgmt"].eq("unknown").astype(float),
    }, index=cohort.index)


def volumes(cohort: pd.DataFrame) -> pd.DataFrame:
    """log(1 + cc) per compartment, using the corrected MU label mapping."""
    return pd.DataFrame({f"log_{k}_cc": np.log1p(cohort[c].fillna(0) / 1000.0) for k, c in COMPARTMENTS.items()},
                        index=cohort.index)


def legacy_radiomics(cohort: pd.DataFrame, modalities=("t1c", "flair")) -> pd.DataFrame:
    """Original PyRadiomics extraction (pre-correction: 2 gray levels for texture) for T1c + FLAIR."""
    rows = []
    for sid, pid, tp in zip(cohort.scan_id, cohort.patient_id, cohort.timepoint):
        d = json.loads((LEGACY_FEATURES_DIR / pid / f"{tp}.json").read_text())
        rows.append({k: v for k, v in d.items() if k.split("_", 1)[0] in modalities and isinstance(v, (int, float))
                     and not isinstance(v, bool) and not k.endswith(("_mask_mean", "_mask_std", "_mask_voxels"))})
    return pd.DataFrame(rows, index=cohort.index)


def feature_set(name: str, cohort: pd.DataFrame) -> tuple[pd.DataFrame, Pipeline]:
    """Raw features + an unfitted preprocessing pipeline for that set."""
    if name == "volumes_clinical":
        X = pd.concat([volumes(cohort), clinical(cohort)], axis=1)
        pre = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
        return X, pre
    if name == "radiomics_clinical":
        rad, clin = legacy_radiomics(cohort), clinical(cohort)
        X = pd.concat([rad, clin], axis=1)
        rad_pipe = Pipeline([("impute", SimpleImputer(strategy="median")), ("var", VarianceThreshold()),
                             ("scale", StandardScaler()), ("pca", PCA(n_components=20, random_state=0))])
        clin_pipe = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
        pre = Pipeline([("cols", ColumnTransformer([("rad", rad_pipe, list(rad.columns)),
                                                    ("clin", clin_pipe, list(clin.columns))]))])
        return X, pre
    raise ValueError(name)
