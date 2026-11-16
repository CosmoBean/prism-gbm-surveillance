"""Vendored code of the published MU-Glioma-Post radiomics pipeline (Christodoulou RC et al., Eur J Radiol AI 2026).

Source: https://github.com/georgeDV2002/Explainable-modality-adaptive-radiomics-for-MGMT-methylation-prediction-in-high-grade-glioma
(the repository titled "Radiomics-based Progression Classification on MU-Glioma-Post"), commit
643c888901180292d89ba09451842ebc308a916a (2026-01-09). Files:
  code/pipeline_extract_catalogue__1.py   (extraction; settings in _christodoulou_radiomics_params.yaml, a verbatim copy
                                           of code/radiomics_params.yaml)
  code/bin_class/rank_and_split__4.py     (feature ranking on the training rows)
  code/bin_class/lightGBM__5b.py          (LightGBM + Optuna + Platt)

The functions below are copied verbatim. Only paths and data plumbing differ, each marked "PRISM:":
  - extraction: the hard-coded paths are arguments; the body of the per-timepoint loop of main() is the function
    `extract_timepoint` (returns the feature row instead of appending it to a CSV; the availability report and the
    tqdm loop are left out);
  - ranking: unchanged (the caller passes a frame with the radiomics columns and the label column PROG_COL);
  - LightGBM: `train_lgbm` takes (X, y, groups) instead of reading traincv_set__4_topk.xlsx and returns the fitted
    objects instead of saving a joblib artifact; the thread counts (LightGBM n_jobs, Optuna n_jobs) are module
    variables so the caller can keep within its CPU budget (theirs: -1 and -1);
  - name clashes between the two bin_class files: lightGBM__5b's CorrelationFilter is `CorrelationFilterLGBM` and its
    N_SPLITS (5) is `N_SPLITS_LGBM`; rank_and_split__4's names are kept. The argparse blocks are left out.

---------------------------------------------------------------------------------------------------------------------
BSD 3-Clause License

Copyright (c) 2025, georgeDV2002

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
# ruff: noqa
from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

PARAMS_YAML = Path(__file__).with_name("_christodoulou_radiomics_params.yaml")  # PRISM: path


# =====================================================================================================================
# code/pipeline_extract_catalogue__1.py
# =====================================================================================================================
APPLY_N4           = True     # set False to skip N4 bias correction
ZSCORE_WITHIN_MASK = True     # z-score each modality within the (core) mask after resampling
OUTPUT_SPACING_MM  = (1.0, 1.0, 1.0)  # isotropic spacing (mm)

# Filename token -> sequence label (used as feature prefix)
MOD_MAP = {
    "brain_t1c": "t1ce",
    "brain_t1n": "t1",
    "brain_t2w": "t2",
    "brain_t2f": "flair",
}
MASK_KEY = "tumorMask"


def is_nonempty_file(p: Path) -> bool:
    try:
        return p.is_file() and p.stat().st_size > 0
    except OSError:
        return False

def expected_files(patient_id: str, timepoint: str, base_dir: Path) -> Dict[str, Path]:
    tp_dir = base_dir / patient_id / timepoint
    stub = f"{patient_id}_{timepoint}_"
    files = {k: tp_dir / f"{stub}{k}.nii.gz" for k in list(MOD_MAP.keys()) + [MASK_KEY]}
    return files


def discover_timepoints(base_dir: Path) -> List[Tuple[str, str]]:
    """Find (patient_id, timepoint) pairs like PatientID_XXXX/Timepoint_X."""
    pairs = []
    for pdir in sorted(base_dir.glob("PatientID_*")):
        if not pdir.is_dir():
            continue
        for tpdir in sorted(pdir.glob("Timepoint_*")):
            if tpdir.is_dir():
                pairs.append((pdir.name, tpdir.name))
    return pairs


def load_nifti(path: Path):
    import nibabel as nib
    return nib.load(str(path))


def to_sitk(nib_img):
    """Convert nibabel image to SimpleITK (with spacing set)."""
    import SimpleITK as sitk
    data = np.asarray(nib_img.get_fdata(dtype=np.float32))
    sitk_img = sitk.GetImageFromArray(np.transpose(data, (2, 1, 0)))  # nib (x,y,z) -> sitk (z,y,x)
    zooms = nib_img.header.get_zooms()[:3]
    sitk_img.SetSpacing((float(zooms[2]), float(zooms[1]), float(zooms[0])))
    return sitk_img


def n4_bias_correction(sitk_img, mask=None):
    import SimpleITK as sitk
    img = sitk.Cast(sitk_img, sitk.sitkFloat32)
    if mask is None:
        mask = sitk.OtsuThreshold(img, 0, 1, 200)
    corrector = sitk.N4BiasFieldCorrectionImageFilter()
    corrected = corrector.Execute(img, mask)
    return corrected


def resample_isotropic(img, spacing=(1.0, 1.0, 1.0), is_label: bool = False):
    """Resample to isotropic spacing with BSpline for images, NN for labels."""
    import SimpleITK as sitk
    original_spacing = img.GetSpacing()
    original_size = img.GetSize()
    new_size = [
        int(round(osz * ospc / nspc))
        for osz, ospc, nspc in zip(original_size, original_spacing, spacing)
    ]
    interp = sitk.sitkNearestNeighbor if is_label else sitk.sitkBSpline
    resampler = sitk.ResampleImageFilter()
    resampler.SetInterpolator(interp)
    resampler.SetOutputSpacing(spacing)
    resampler.SetSize(new_size)
    resampler.SetOutputDirection(img.GetDirection())
    resampler.SetOutputOrigin(img.GetOrigin())
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(img)


def zscore_within_mask(img, mask):
    """Z-score normalization using voxels inside the mask; returns a new sitk.Image."""
    import SimpleITK as sitk
    arr = sitk.GetArrayFromImage(img).astype(np.float32)
    msk = sitk.GetArrayFromImage(mask) > 0
    if msk.sum() == 0:
        return img
    vals = arr[msk]
    mu = float(vals.mean())
    sd = float(vals.std()) if float(vals.std()) > 1e-6 else 1.0
    arr_norm = (arr - mu) / sd
    out = sitk.GetImageFromArray(arr_norm)
    out.CopyInformation(img)
    return out


def extract_features_for_tp_inmemory(
    seq_imgs,                                  # e.g., {"brain_t1c": sitk.Image, ...}
    params_path: Path,
    subject_id: str,
    timepoint: str,
    mask_img,
    prefix: str,
) -> Dict[str, float]:
    """
    Extract PyRadiomics features from provided sitk images (already preprocessed) using mask_img.
    Returns a flat dict of features with keys like "{prefix}__t1ce__firstorder_Mean".
    """
    from radiomics.featureextractor import RadiomicsFeatureExtractor
    #extractor = RadiomicsFeatureExtractor(str(params_path))
    extractor = RadiomicsFeatureExtractor(str(params_path), enableCExtensions=True, verbose=False)
    extractor.settings["label"] = 1  # label 1 for binary masks (foreground)

    features = {"subject_id": subject_id, "timepoint": timepoint, "roi": prefix}

    for mod_key, seq_label in MOD_MAP.items():
        if mod_key not in seq_imgs:
            continue
        img_sitk = seq_imgs[mod_key]
        result = extractor.execute(img_sitk, mask_img)

        for k, v in result.items():
            if k.startswith("diagnostics_"):
                continue
            if isinstance(v, (int, float, np.floating)):
                features[f"{prefix}__{seq_label}__{k}"] = float(v)
            else:
                # Keep string values (rare) as-is
                features[f"{prefix}__{seq_label}__{k}"] = str(v)

    return features


def extract_timepoint(patient_id: str, timepoint: str, base: Path, params_path: Path = PARAMS_YAML):
    """PRISM: the body of the per-timepoint loop of main(), unchanged; returns the "core" row (or None) instead of
    writing it to radiomics_features.csv."""
    import SimpleITK as sitk
    from nibabel.filebasedimages import ImageFileError
    logging.getLogger("radiomics").setLevel(logging.ERROR)
    logging.getLogger("pykwalify").setLevel(logging.ERROR)
    files = expected_files(patient_id, timepoint, base)

    # --- Load and preprocess mask (core) ---
    # Need mask to proceed
    if not is_nonempty_file(files[MASK_KEY]):
        print(f"[WARN] Empty or missing mask: {files[MASK_KEY]} — skipping {patient_id} {timepoint}")
        return None
    try:
        mask_nib = load_nifti(files[MASK_KEY])
    except ImageFileError as e:
        print(f"[WARN] Failed to load mask {files[MASK_KEY]}: {e} — skipping {patient_id} {timepoint}")
        return None

    mask_sitk = to_sitk(mask_nib)
    mask_res  = resample_isotropic(mask_sitk, spacing=OUTPUT_SPACING_MM, is_label=True)
    mask_bin = sitk.Cast(mask_res > 0, sitk.sitkUInt8)   # binary 0/1 UInt8 mask

    # --- Preprocess each available modality in memory ---
    seq_imgs = {}
    for mod_key, seq_label in MOD_MAP.items():
        p = files[mod_key]
        if not is_nonempty_file(p):
            continue
        try:
            img_nib = load_nifti(p)
        except ImageFileError as e:
            print(f"[WARN] Failed to load {p}: {e} — skipping {mod_key}")
            continue
        img_sitk = to_sitk(img_nib)

        if APPLY_N4:
            img_sitk = n4_bias_correction(img_sitk, mask=mask_bin)

        img_res = resample_isotropic(img_sitk, spacing=OUTPUT_SPACING_MM, is_label=False)

        if ZSCORE_WITHIN_MASK:
            img_res = zscore_within_mask(img_res, mask_bin)

        seq_imgs[mod_key] = img_res

    # If no modalities are available, skip
    if not seq_imgs:
        return None

    # CORE
    try:
        core_feats = extract_features_for_tp_inmemory(
            seq_imgs=seq_imgs,
            params_path=Path(params_path),
            subject_id=patient_id,
            timepoint=timepoint,
            mask_img=mask_bin,
            prefix="core",
        )
        return core_feats
    except Exception as e:
        print(f"[ERROR] CORE radiomics failed for {patient_id} {timepoint}: {e}")
        return None


# =====================================================================================================================
# code/bin_class/rank_and_split__4.py
# =====================================================================================================================
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, log_loss
from sklearn.feature_selection import VarianceThreshold
from pandas.api.types import is_numeric_dtype

# label + meta
PROG_COL = "Time to First Progression (Days)"
SUBJECT_COL_CANDIDATES = ["subject_id", "Patient_ID", "Subject_ID"]

# importance (train-cv only)
N_SPLITS = 10
PERM_REPEATS = 100
CORR_THRESHOLD = 0.80
MAX_ITER = 10000
C_REG = 1.0
MIN_TEST_SIZE_FOR_PI = 30
RANDOM_STATE = 42
TINY = 1e-9


class CorrelationFilter(BaseEstimator, TransformerMixin):
    """Drop one feature from any pair whose |corr| >= threshold (fit on train only)."""
    def __init__(self, threshold=0.95, method="spearman"):
        self.threshold = threshold
        self.method = method
        self.keep_features_: list[str] | None = None

    def fit(self, X, y=None):
        Xdf = pd.DataFrame(X).copy()
        med = pd.Series(np.nanmedian(Xdf.values, axis=0), index=Xdf.columns)
        Xdf = Xdf.fillna(med)
        valid = Xdf.notna().sum(axis=0) >= 2
        Xdf = Xdf.loc[:, valid]
        corr = Xdf.corr(method=self.method).abs()
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        drop = set()
        for col in upper.columns:
            if col in drop:
                continue
            high = upper.index[upper[col] >= self.threshold].tolist()
            drop.update(high)
        self.keep_features_ = [c for c in Xdf.columns if c not in drop]
        return self

    def transform(self, X):
        Xdf = pd.DataFrame(X)
        return Xdf[self.keep_features_].values

def perm_importance_kept(pipe, Xte, yte, kept_names, repeats=50, random_state=42):
    """Permutation importance ONLY for features that reached the classifier.
       Metric: delta log-loss (positive = worse when shuffled = important).
    """
    rng = np.random.default_rng(random_state)
    # 1) impute with original names
    Xi = pd.DataFrame(pipe.named_steps["imp"].transform(Xte), columns=Xte.columns)
    # 2) VT names
    vt = pipe.named_steps["vt"]
    vt_cols = Xi.columns[vt.get_support()]
    Xi_vt = Xi.loc[:, vt_cols]
    # 3) align kept names
    kept = [c for c in kept_names if c in Xi_vt.columns]
    if not kept:
        return pd.Series(dtype=float)
    Xi_corr = Xi_vt.loc[:, kept]
    # 4) scale
    Zte = pipe.named_steps["sc"].transform(Xi_corr.values)
    # 5) baseline logloss
    clf = pipe.named_steps["clf"]
    p_base = clf.predict_proba(Zte)[:, 1]
    base = log_loss(yte, p_base, labels=[0, 1])
    # 6) permute one-by-one
    Z = Zte.copy()
    importances = np.zeros(Z.shape[1], dtype=float)
    for j in range(Z.shape[1]):
        drops = []
        for _ in range(repeats):
            saved = Z[:, j].copy()
            rng.shuffle(Z[:, j])
            p_perm = clf.predict_proba(Z)[:, 1]
            score = log_loss(yte, p_perm, labels=[0, 1])
            drops.append(score - base)
            Z[:, j] = saved
        importances[j] = float(np.mean(drops))
    return pd.Series(importances, index=[str(n) for n in kept])

# ===================== importance on train-cv =====================
def compute_importance_traincv(df_traincv: pd.DataFrame):
    # label
    df = df_traincv.copy()
    df.columns = df.columns.map(lambda c: str(c).strip())

    y = pd.to_numeric(df[PROG_COL], errors="coerce").notna().astype(int).values

    # features: numeric radiomics only (exclude IDs/clinical helpers)
    exclude = set(SUBJECT_COL_CANDIDATES) | {"timepoint", PROG_COL, "delta_days", "days_from_dx", "Patient_ID"}
    feat_cols = [c for c in df.columns if c not in exclude and is_numeric_dtype(df[c])]
    X = df[feat_cols].copy()
    X.columns = X.columns.astype(str)

    counts = pd.Series(y).value_counts(dropna=False).to_dict()
    min_class = min(counts.get(0, 0), counts.get(1, 0))
    n_splits = N_SPLITS
    if min_class < 1:
        raise RuntimeError(f"No negatives or positives under this label. Class counts: {counts}")
    if n_splits > min_class:
        print(f"[info] Reducing N_SPLITS from {n_splits} to {min_class} to avoid single-class folds.")
        n_splits = max(2, min_class)

    print("Sample-wise class counts (train-cv):", counts, "| samples:", len(y))
    print(f"Features used (train-cv): {len(feat_cols)}")

    pipe = Pipeline([
        ("imp",  SimpleImputer(strategy="median")),
        ("vt",   VarianceThreshold(threshold=1e-8)),
        ("corr", CorrelationFilter(threshold=CORR_THRESHOLD, method="spearman")),
        ("sc",   StandardScaler()),
        ("clf",  LogisticRegression(
            penalty="l1", solver="saga", C=C_REG, max_iter=MAX_ITER,
            class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1
        )),
    ])

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)

    aucs = []
    coef_list = []
    perm_list = []
    presence_counts = {}

    for fold_i, (tr, te) in enumerate(skf.split(X, y), start=1):
        Xtr, Xte = X.iloc[tr], X.iloc[te]
        ytr, yte = y[tr], y[te]

        pipe.fit(Xtr, ytr)

        # names after VT
        Xi = pd.DataFrame(pipe.named_steps["imp"].transform(Xtr), columns=Xtr.columns)
        vt = pipe.named_steps["vt"]
        vt_cols = Xi.columns[vt.get_support()]  # Index of original NAMES after VT

        # what CorrFilter kept (can be positions OR names)
        kept = pipe.named_steps["corr"].keep_features_

        if kept is None or len(kept) == 0:
            kept_names = []
        elif isinstance(kept[0], (int, np.integer)):
            kept_names = [vt_cols[k] for k in kept if 0 <= k < len(vt_cols)]
        else:
            kept_names = [k for k in kept if k in vt_cols]

        if not kept_names:
            continue

        # Coefficients aligned to kept_names
        coefs = pd.Series(pipe.named_steps["clf"].coef_[0], index=[str(k) for k in kept_names])
        coef_list.append(coefs)

        for f in kept_names:
            presence_counts[f] = presence_counts.get(f, 0) + 1

        # AUC + PI if both classes present
        if np.unique(yte).size == 2:
            prob = pipe.predict_proba(Xte)[:, 1]
            aucs.append(roc_auc_score(yte, prob))

            if len(yte) >= MIN_TEST_SIZE_FOR_PI:
                pi_kept = perm_importance_kept(pipe, Xte, yte, kept_names, repeats=PERM_REPEATS, random_state=RANDOM_STATE)
                perm_list.append(pi_kept)

    if aucs:
        print(f"Mean CV AUC (train-cv): {np.mean(aucs):.3f} ± {np.std(aucs):.3f}")
    else:
        print("Note: AUC skipped in all folds (likely single-class test sets).")

    print(f"[diag] folds with PI: {len(perm_list)} / {n_splits}")

    # Aggregate
    coef_df = pd.concat(coef_list, axis=1)  # keep NaNs
    coef_df.columns = [f"fold{i+1}" for i in range(len(coef_list))]

    median_abs_coef = coef_df.abs().median(axis=1, skipna=True)

    n_folds = len(coef_list)
    presence_freq = pd.Series(
        {f: presence_counts.get(f, 0) / n_folds for f in coef_df.index},
        dtype=float
    )

    sel_numer = (coef_df.abs() > 0).sum(axis=1, skipna=True)
    sel_denom = coef_df.notna().sum(axis=1).replace(0, np.nan)
    coef_nonzero_given_present = (sel_numer / sel_denom).fillna(0.0)

    if len(perm_list):
        perm_df = pd.concat(perm_list, axis=1)
        perm_df.index = perm_df.index.astype(str)
        perm_df.columns = [f"fold{i+1}" for i in range(len(perm_list))]
        median_perm = perm_df.median(axis=1, skipna=True)
        pi_numer = (perm_df > TINY).sum(axis=1)
        pi_denom = perm_df.notna().sum(axis=1).replace(0, np.nan)
        pi_gt0_freq = (pi_numer / pi_denom).fillna(0.0)

        with pd.option_context("display.float_format", "{:.3e}".format):
            print("[diag] PI median (head 10):")
            print(median_perm.sort_values(ascending=False).head(10))
    else:
        median_perm = pd.Series(0.0, index=median_abs_coef.index, dtype=float)
        pi_gt0_freq = pd.Series(0.0, index=median_abs_coef.index, dtype=float)

    all_feats = median_abs_coef.index.union(median_perm.index)
    imp = pd.DataFrame({
        "median_abs_coef":              median_abs_coef.reindex(all_feats).fillna(0.0),
        "median_perm_importance":       median_perm.reindex(all_feats).fillna(0.0),
        "presence_freq":                presence_freq.reindex(all_feats).fillna(0.0),
        "coef_nonzero_given_present":   coef_nonzero_given_present.reindex(all_feats).fillna(0.0),
        "pi_nonzero_freq":              pi_gt0_freq.reindex(all_feats).fillna(0.0),
    })

    rank_coef = imp["median_abs_coef"].rank(ascending=False, method="average")
    rank_perm = imp["median_perm_importance"].rank(ascending=False, method="average")
    imp["consensus_rank"] = (rank_coef + rank_perm)

    imp = imp.sort_values(["consensus_rank", "median_perm_importance", "median_abs_coef"],
                          ascending=[True, False, False])

    return imp, feat_cols


def top_k_features(imp: pd.DataFrame, columns, k: int) -> list:
    """rank_and_split__4.main(): `top_feats = [f for f in imp.index.tolist() if f in df_all.columns][:TOPK_FEATURES]`."""
    return [f for f in imp.index.tolist() if f in columns][:k]


# =====================================================================================================================
# code/bin_class/lightGBM__5b.py
# =====================================================================================================================
from sklearn.model_selection import StratifiedGroupKFold as SGKFold  # sklearn >= 1.3

CALIBRATE = True
N_SPLITS_LGBM = 5  # CV folds within train-cv   (lightGBM__5b: N_SPLITS)

# Hyperparameter search space
N_TRIALS = 400
LEARNING_RATE_MIN, LEARNING_RATE_MAX = 0.01, 0.3
N_ESTIMATORS_MIN, N_ESTIMATORS_MAX   = 100, 1200
NUM_LEAVES_MIN, NUM_LEAVES_MAX       = 8, 128
MIN_CHILD_SAMPLES_MIN, MIN_CHILD_SAMPLES_MAX = 5, 80
SUBSAMPLE_MIN, SUBSAMPLE_MAX         = 0.6, 1.0
COLSAMPLE_MIN, COLSAMPLE_MAX         = 0.6, 1.0
REG_ALPHA_MIN, REG_ALPHA_MAX         = 0.0, 2.0
REG_LAMBDA_MIN, REG_LAMBDA_MAX       = 0.0, 4.0
CORR_MIN, CORR_MAX                   = 0.75, 0.95

LGBM_N_JOBS = -1    # PRISM: thread count (theirs: n_jobs=-1 in build_pipeline)
OPTUNA_N_JOBS = -1  # PRISM: thread count (theirs: n_jobs=-1 in study.optimize)


def fit_platt_on_oof(y_true: np.ndarray, oof_proba: np.ndarray) -> LogisticRegression:
    """
    Fit Platt (sigmoid) calibration on OOF predictions: p_cal = sigmoid(a * p_raw + b).
    Uses scikit-learn LogisticRegression with one feature (p_raw).
    """
    lr = LogisticRegression(solver="lbfgs")
    lr.fit(oof_proba.reshape(-1, 1), y_true.astype(int))
    return lr

class CorrelationFilterLGBM(BaseEstimator, TransformerMixin):
    """Drop one feature from any pair whose |corr| >= threshold (fit on input only)."""
    def __init__(self, threshold: float = 0.80, method: str = "spearman"):
        self.threshold = threshold
        self.method = method
        self.keep_features_: list[int] | list[str] | None = None

    def fit(self, X, y=None):
        Xdf = pd.DataFrame(X).copy()
        med = pd.Series(np.nanmedian(Xdf.values, axis=0), index=Xdf.columns)
        Xdf = Xdf.fillna(med)
        valid = Xdf.notna().sum(axis=0) >= 2
        Xdf = Xdf.loc[:, valid]
        corr = Xdf.corr(method=self.method).abs()
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        drop = set()
        for col in upper.columns:
            if col in drop:
                continue
            high = upper.index[upper[col] >= self.threshold].tolist()
            drop.update(high)
        self.keep_features_ = [c for c in Xdf.columns if c not in drop]
        return self

    def transform(self, X):
        Xdf = pd.DataFrame(X)
        if self.keep_features_ is None:
            return Xdf.values
        return Xdf[self.keep_features_].values

def build_pipeline(params: dict, corr_threshold: float) -> Pipeline:
    """Light preprocessing + optional correlation pruning + LightGBM."""
    from lightgbm import LGBMClassifier
    clf = LGBMClassifier(
        objective="binary",
        boosting_type="gbdt",
        learning_rate=params["learning_rate"],
        n_estimators=params["n_estimators"],
        num_leaves=params["num_leaves"],
        min_child_samples=params["min_child_samples"],
        subsample=params["subsample"],
        colsample_bytree=params["colsample_bytree"],
        reg_alpha=params["reg_alpha"],
        reg_lambda=params["reg_lambda"],
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=LGBM_N_JOBS,  # PRISM: thread count (theirs: -1)
        verbose=-1,
    )
    pipe = Pipeline([
        ("imp",  SimpleImputer(strategy="median")),
        ("vt",   VarianceThreshold(threshold=1e-12)),
        ("corr", CorrelationFilterLGBM(threshold=corr_threshold, method="spearman")),
        ("clf",  clf),
    ])
    return pipe

def oof_cv_predict(X: pd.DataFrame, y: np.ndarray, groups: np.ndarray, pipe: Pipeline, n_splits: int, seed: int):
    """Return OOF probabilities, fold AUC list."""
    n = len(y)
    oof = np.full(n, np.nan, dtype=float)
    aucs = []

    skf = SGKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for tr, va in skf.split(X, y, groups):
        Xtr, Xva = X.iloc[tr], X.iloc[va]
        ytr, yva = y[tr], y[va]

        pipe.fit(Xtr, ytr)
        p = pipe.predict_proba(Xva)[:, 1]
        oof[va] = p

        if np.unique(yva).size == 2:
            aucs.append(roc_auc_score(yva, p))

    oof_auc = roc_auc_score(y, oof) if np.unique(y).size == 2 else np.nan
    return oof, oof_auc, aucs

def find_best_threshold(y_true: np.ndarray, proba: np.ndarray) -> tuple[float, dict]:
    """Choose threshold that minimizes FP + FN."""
    vals = np.unique(proba)
    if vals.size > 1000:
        thr_grid = np.quantile(proba, np.linspace(0.01, 0.99, 199))
        thr_grid = np.unique(thr_grid)
    else:
        thr_grid = vals

    best_thr, best_err = 0.5, float("inf")
    best_stats = {}
    n = len(y_true)

    for t in thr_grid:
        pred = (proba >= t).astype(int)
        tp = int(((pred == 1) & (y_true == 1)).sum())
        tn = int(((pred == 0) & (y_true == 0)).sum())
        fp = int(((pred == 1) & (y_true == 0)).sum())
        fn = int(((pred == 0) & (y_true == 1)).sum())
        err = fp + fn
        if err < best_err:
            best_err = err
            best_thr = float(t)
            acc = (tp + tn) / max(1, n)
            best_stats = {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "errors": err, "accuracy": acc}

    return best_thr, best_stats


def train_lgbm(X: pd.DataFrame, y: np.ndarray, groups: np.ndarray, n_trials: int = N_TRIALS):
    """PRISM: lightGBM__5b.train_lgbm with (X, y, groups) passed in (theirs: read from TRAIN_XLSX) and the fitted
    objects returned (theirs: saved to a joblib artifact). The body is unchanged."""
    import optuna
    warnings.filterwarnings("ignore", category=UserWarning)
    np.random.seed(RANDOM_STATE)
    X = X.copy()
    X.columns = X.columns.astype(str)

    def objective(trial):
        params = {
            "learning_rate": trial.suggest_float("learning_rate", LEARNING_RATE_MIN, LEARNING_RATE_MAX, log=False),
            "n_estimators":  trial.suggest_int("n_estimators", N_ESTIMATORS_MIN, N_ESTIMATORS_MAX),
            "num_leaves":    trial.suggest_int("num_leaves", NUM_LEAVES_MIN, NUM_LEAVES_MAX),
            "min_child_samples": trial.suggest_int("min_child_samples", MIN_CHILD_SAMPLES_MIN, MIN_CHILD_SAMPLES_MAX),
            "subsample":     trial.suggest_float("subsample", SUBSAMPLE_MIN, SUBSAMPLE_MAX),
            "colsample_bytree": trial.suggest_float("colsample_bytree", COLSAMPLE_MIN, COLSAMPLE_MAX),
            "reg_alpha":     trial.suggest_float("reg_alpha", REG_ALPHA_MIN, REG_ALPHA_MAX),
            "reg_lambda":    trial.suggest_float("reg_lambda", REG_LAMBDA_MIN, REG_LAMBDA_MAX),
        }
        corr = trial.suggest_float("corr_threshold", CORR_MIN, CORR_MAX)

        pipe = build_pipeline(params=params, corr_threshold=corr)
        oof, oof_auc, fold_aucs = oof_cv_predict(X, y, groups, pipe, N_SPLITS_LGBM, RANDOM_STATE)
        thr, stats = find_best_threshold(y, oof)

        trial.set_user_attr("oof_auc", oof_auc)
        trial.set_user_attr("threshold", thr)
        trial.set_user_attr("errors_fp_fn", stats.get("errors", None))
        return oof_auc

    sampler = optuna.samplers.TPESampler(seed=RANDOM_STATE)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.optimize(objective, n_trials=n_trials, n_jobs=OPTUNA_N_JOBS, show_progress_bar=False)  # PRISM: no bar

    best = study.best_trial
    best_params = {
        "learning_rate":  best.params["learning_rate"],
        "n_estimators":   best.params["n_estimators"],
        "num_leaves":     best.params["num_leaves"],
        "min_child_samples": best.params["min_child_samples"],
        "subsample":      best.params["subsample"],
        "colsample_bytree": best.params["colsample_bytree"],
        "reg_alpha":      best.params["reg_alpha"],
        "reg_lambda":     best.params["reg_lambda"],
        "corr_threshold": best.params["corr_threshold"],
    }

    # Recompute OOF with best params & pick threshold
    best_pipe = build_pipeline(
        params={k: v for k, v in best_params.items() if k != "corr_threshold"},
        corr_threshold=best_params["corr_threshold"],
    )

    oof_raw, oof_auc, fold_aucs = oof_cv_predict(X, y, groups, best_pipe, N_SPLITS_LGBM, RANDOM_STATE)

    calibrator = None
    if CALIBRATE:
        calibrator = fit_platt_on_oof(y, oof_raw)
        oof_cal = calibrator.predict_proba(oof_raw.reshape(-1, 1))[:, 1]
        # Choose threshold on CALIBRATED OOF
        thr, stats = find_best_threshold(y, oof_cal)
    else:
        thr, stats = find_best_threshold(y, oof_raw)

    # Fit on ALL train-cv
    best_pipe.fit(X, y)

    return {"pipeline": best_pipe, "platt_calibrator": calibrator, "threshold": thr, "params": best_params,
            "best_value": float(best.value), "train_oof_auc": float(oof_auc), "feature_cols": list(X.columns)}


def predict(art: dict, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """lightGBM__5b.test_lgbm(): raw = pipe.predict_proba(X)[:, 1]; calibrated = platt on raw (theirs, unchanged)."""
    X = X[art["feature_cols"]].copy()
    proba_raw = art["pipeline"].predict_proba(X)[:, 1]
    platt = art["platt_calibrator"]
    proba = platt.predict_proba(proba_raw.reshape(-1, 1))[:, 1] if platt is not None else proba_raw
    return proba_raw, proba
