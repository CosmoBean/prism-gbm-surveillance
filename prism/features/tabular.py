"""Scan-level feature groups. Each returns a raw matrix aligned to the cohort; fitted preprocessing happens in-fold."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from prism.data.mu import load_index
from prism.features.measurements import load_measurements
from prism.features.radiomics import legacy_features

COMPARTMENTS = {"netc": "label1_voxels", "snfh": "label2_voxels", "et": "label3_voxels", "rc": "label4_voxels"}
DELTA_REL = ("d_t1c_et_rel", "d_flair_snfh_rel")


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


def timing(cohort: pd.DataFrame) -> pd.DataFrame:
    """Time features as of the scan. Days since RT end only once RT has ended (the end date of an ongoing or future
    course is not known at the scan); early_post_rt = RANO 12-week pseudoprogression window, also x MGMT methylated."""
    rt = cohort["days_since_rt_end"].where(cohort["days_since_rt_end"] >= 0)
    early = cohort["early_post_rt"].astype(float)
    return pd.DataFrame({"days_from_diagnosis": cohort["days_from_diagnosis_to_mri"], "days_since_rt_end": rt,
                         "rt_date_unknown": rt.isna().astype(float),
                         "early_post_rt": early,
                         "early_post_rt_x_mgmt_methylated": early * cohort["mgmt"].eq("methylated").astype(float),
                         "visit_index": cohort["visit_index"]}, index=cohort.index)


def volumes(cohort: pd.DataFrame) -> pd.DataFrame:
    """log(1 + cc) per compartment, using the corrected MU label mapping."""
    return pd.DataFrame({f"log_{k}_cc": np.log1p(cohort[c].fillna(0) / 1000.0) for k, c in COMPARTMENTS.items()},
                        index=cohort.index)


def treatment(cohort: pd.DataFrame, index: pd.DataFrame | None = None) -> pd.DataFrame:
    """Treatment as of the scan day. A therapy counts only once its documented start day is <= the scan day; the RT
    prescription (dose, fractions) is known from RT start, the RT duration only from RT end. Not-yet-known values are
    NaN (imputed in-fold) with explicit rt_started / rt_completed / chemo_started indicators. A missing start date
    for a given therapy (2 RT, 2 chemo patients) is taken as started before the scan."""
    d = (load_index() if index is None else index).set_index("scan_id").reindex(cohort.scan_id)
    num = lambda c: pd.to_numeric(d[c].astype(str).str.extract(r"([-\d.]+)")[0], errors="coerce").to_numpy()
    mri = pd.to_numeric(cohort["days_from_diagnosis_to_mri"], errors="coerce").to_numpy(float)
    rt_start = num("clinical_number_of_days_from_diagnosis_to_radiation_therapy_start_date")
    rt_end = num("clinical_number_of_days_from_diagnosis_to_radiation_therapy_end_date")
    chemo_start = num("clinical_number_of_days_from_diagnosis_to_initial_chemo_therapy_start_date")
    surgery = num("clinical_number_of_days_from_diagnosis_to_first_surgery_or_procedure")
    by_scan = lambda day: np.isnan(day) | (day <= mri)
    rt_given = d["clinical_radiation_therapy"].astype(str).str.strip().isin(["Yes", "Proton Therapy"]).to_numpy()
    started = rt_given & by_scan(rt_start)
    completed = started & ~np.isnan(rt_end) & (rt_end <= mri)
    known = lambda x, ok: np.where(ok, x, np.nan)
    fractions = known(num("clinical_number_of_fractions"), started)
    return pd.DataFrame({
        "rt_started": started.astype(float),
        "rt_completed": completed.astype(float),
        "rt_dose_gy": known(num("clinical_dose"), started),
        "rt_fractions": fractions,
        "rt_hypofractionated": known((fractions <= 15).astype(float), ~np.isnan(fractions)),
        "rt_start_day": known(rt_start, started),
        "rt_duration_days": known(rt_end - rt_start, completed),
        "chemo_started": (d["clinical_initial_chemo_therapy"].astype(str).str.strip().eq("Yes").to_numpy()
                          & by_scan(chemo_start)).astype(float),
        "surgery_day": known(surgery, surgery <= mri),
        "biopsy_before_resection": known(num("clinical_stereotactic_biopsy_before_surgical_resection"), surgery <= mri),
        "previous_brain_tumor": d["clinical_previous_brain_tumor"].astype(str).str.strip().eq("Yes").to_numpy(float),
    }, index=cohort.index)


def measurement_groups(cohort: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Image measurements split into volumes, morphology/intensity and past-only change ("delta")."""
    m = load_measurements(cohort.scan_id)
    m.index = cohort.index
    log1p = lambda s: np.log1p(s.clip(lower=0))
    slog = lambda s: np.sign(s) * np.log1p(s.abs())
    return {
        "volumes": pd.DataFrame({f"log_{c}": log1p(m[c]) for c in
                                 ("et_cc", "netc_cc", "snfh_cc", "rc_cc", "tumor_cc", "lesion_cc")}),
        "morphology": pd.DataFrame({
            "et_fraction_of_tumor": m.et_fraction_of_tumor, "log_snfh_to_tumor": np.log1p(m.snfh_to_tumor_ratio),
            "has_cavity": m.has_cavity, "et_n_components": m.et_n_components,
            "et_largest_component_fraction": m.et_largest_component_fraction,
            "log_et_max_axial": log1p(m.et_max_axial_mm2), "et_near_cavity_fraction": m.et_near_cavity_fraction,
            "et_cavity_distance": log1p(m.et_cavity_distance_mm_p50), "t1c_et_rel": m.t1c_et_rel,
            "t1c_et_p90_rel": m.t1c_et_p90_rel, "t1c_netc_rel": m.t1c_netc_rel,
            "flair_snfh_rel": m.flair_snfh_rel, "flair_netc_rel": m.flair_netc_rel}),
        # No prior scan -> change set to 0 and flagged by has_prior. An intensity change that is undefined although a
        # prior exists (< 10 ET voxels now or before) is also set to 0 and flagged by <col>_missing.
        "delta": pd.concat([m[["has_prior", "n_prior_scans"]],
                            np.log1p(m[["days_since_prior"]].fillna(0)),
                            m.filter(regex=r"^logratio_").fillna(0),
                            slog(m.filter(regex=r"^rate_")).fillna(0),
                            m[["d_et_n_components", *DELTA_REL, "vol_pd_flag", "new_et_component"]].fillna(0),
                            pd.DataFrame({f"{c}_missing": (m.has_prior.eq(1) & m[c].isna()).astype(float)
                                          for c in DELTA_REL}),
                            m.reindex(columns=["et_new_from_zero_nadir"]).fillna(0)], axis=1),
    }


def groups(cohort: pd.DataFrame, legacy_radiomics: bool = True) -> dict[str, pd.DataFrame]:
    """All MU feature groups by name (clinical, timing, treatment, volumes, morphology, delta, radiomics)."""
    g = {"clinical": clinical(cohort), "timing": timing(cohort), "treatment": treatment(cohort),
         **measurement_groups(cohort)}
    if legacy_radiomics:
        g["radiomics"] = legacy_features(cohort).astype(float)
    return g


def feature_set(name: str, cohort: pd.DataFrame) -> tuple[pd.DataFrame, Pipeline]:
    """Raw features + an unfitted preprocessing pipeline (used by the endpoint experiment)."""
    if name == "volumes_clinical":
        X = pd.concat([volumes(cohort), clinical(cohort)], axis=1)
        pre = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
        return X, pre
    if name == "radiomics_clinical":
        rad, clin = legacy_features(cohort), clinical(cohort)
        X = pd.concat([rad, clin], axis=1)
        rad_pipe = Pipeline([("impute", SimpleImputer(strategy="median")), ("var", VarianceThreshold()),
                             ("scale", StandardScaler()), ("pca", PCA(n_components=20, random_state=0))])
        clin_pipe = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
        pre = Pipeline([("cols", ColumnTransformer([("rad", rad_pipe, list(rad.columns)),
                                                    ("clin", clin_pipe, list(clin.columns))]))])
        return X, pre
    raise ValueError(name)


# ---------------------------------------------------------------- features shared by MU and LUMIERE
# DeepBraTumIA (LUMIERE) has no resection-cavity label: its "necrotic / non-enhancing" compartment contains the cavity.
# The shared necrosis volume is therefore harmonised as MU NETC + RC <-> LUMIERE necrotic (log_necrosis_cavity_cc), and
# tumour core as MU ET + NETC + RC <-> LUMIERE enhancing + necrotic (log_core_cavity_cc). log_netc_cc is kept in both
# tables for reference but is NOT comparable across cohorts (MU NETC excludes the cavity) and is not in SHARED.
SHARED = {
    "clinical": ["age", "male", "idh_mutant", "idh_unknown", "mgmt_methylated", "mgmt_unknown"],
    "timing": ["log_days_since_surgery", "early_post_rt"],
    "volumes": ["log_et_cc", "log_necrosis_cavity_cc", "log_snfh_cc"],
}
SHARED_VOLUMES_UNHARMONISED = ["log_et_cc", "log_netc_cc", "log_snfh_cc"]  # pre-fix definition (sensitivity only)
SHARED_VOLUME_COLS = ["log_et_cc", "log_netc_cc", "log_snfh_cc", "log_necrosis_cavity_cc", "log_core_cavity_cc"]
LUMIERE_VOLUMES = {"et": "raw_Enhancing_Core", "netc": "raw_Necrotic_NonEnhancing", "snfh": "raw_Edema_Compartment"}


def shared_mu(cohort: pd.DataFrame) -> pd.DataFrame:
    """Features available in both cohorts, computed on MU."""
    m = load_measurements(cohort.scan_id)
    X = clinical(cohort)
    X["log_days_since_surgery"] = np.log1p((cohort.days_from_diagnosis_to_mri - treatment(cohort).surgery_day)
                                           .clip(lower=0))
    X["early_post_rt"] = cohort.early_post_rt.astype(float)
    for k in ("et", "netc", "snfh"):
        X[f"log_{k}_cc"] = np.log1p(m[f"{k}_cc"].to_numpy())
    X["log_necrosis_cavity_cc"] = np.log1p((m.netc_cc + m.rc_cc).to_numpy())
    X["log_core_cavity_cc"] = np.log1p((m.et_cc + m.netc_cc + m.rc_cc).to_numpy())
    return X


def shared_lumiere(cohort: pd.DataFrame) -> pd.DataFrame:
    """Features available in both cohorts, computed on LUMIERE."""
    X = clinical(cohort)
    X["log_days_since_surgery"] = np.log1p(cohort.days_since_surgery)
    X["early_post_rt"] = cohort.early_post_rt.astype(float)
    cc = {k: cohort[col] / 1000.0 if col in cohort else pd.Series(np.nan, index=cohort.index)
          for k, col in LUMIERE_VOLUMES.items()}
    for k, v in cc.items():
        X[f"log_{k}_cc"] = np.log1p(v)
    X["log_necrosis_cavity_cc"] = np.log1p(cc["netc"])
    X["log_core_cavity_cc"] = np.log1p(cc["et"] + cc["netc"])
    return X


def within_cohort_normalise(X: pd.DataFrame, cols=None, method: str = "rank") -> pd.DataFrame:
    """Sensitivity analysis for segmenter differences: re-express volume columns relative to their own cohort.
    Call separately on each cohort's table (MU training data, LUMIERE test data).
      rank   -> mid-rank percentile in (0, 1) (ties, e.g. many 0 cc, share their average rank)
      zscore -> (x - cohort mean) / cohort SD
    This is transductive for the test cohort (uses the unlabelled LUMIERE feature distribution, never its labels) and
    removes between-cohort differences in volume level by construction, so it is a sensitivity analysis only."""
    cols = [c for c in (SHARED_VOLUME_COLS if cols is None else cols) if c in X]
    out = X.copy()
    for c in cols:
        v = out[c]
        if method == "rank":
            out[c] = (v.rank(method="average") - 0.5) / v.notna().sum()
        elif method == "zscore":
            out[c] = (v - v.mean()) / (v.std(ddof=0) or 1.0)
        else:
            raise ValueError(method)
    return out
