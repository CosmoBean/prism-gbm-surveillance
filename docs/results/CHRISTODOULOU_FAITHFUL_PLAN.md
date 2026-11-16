# Plan: the published MU radiomics pipeline run as published, on PRISM's task (2026-11-16)

Written before any code for this run. It is committed before the run. Results go to CHRISTODOULOU_REPLICATION.md
(new section "Faithful run"), reported as they come out.

## Why
The re-implementation in CHRISTODOULOU_REPLICATION.md (0c62665) departed from the published pipeline:
- original-image features from PRISM's six regions;
- univariate-AUC selection;
- no class weights;
- 40 Optuna trials.

This run uses the authors' own code and settings, from their public repository at commit 643c888 (BSD 3-Clause),
on PRISM's label and folds. The run answers whether the pipeline as published reaches more than 0.58 on PRISM's
task.

## What is taken unchanged from the authors' code
- **Extraction:** `code/pipeline_extract_catalogue__1.py` with `code/radiomics_params.yaml`. Only input and output
  paths change.
  - N4 bias correction inside the mask;
  - resampling to 1 mm isotropic (BSpline);
  - z-score within the mask;
  - one region (`tumorMask > 0`);
  - four sequences;
  - Original, LoG (sigma 0.5, 1, 2, 3) and Wavelet images;
  - shape, first order and all texture classes;
  - binWidth 25, normalize with scale 100.
  
  Run on every MU scan with all four sequences and a mask.
- **Ranking:** `code/bin_class/rank_and_split__4.py`, function `compute_importance_traincv`.
  - Pipeline: median imputation, VarianceThreshold, Spearman correlation filter at 0.80, StandardScaler, logistic
    regression with C = 1.
  - Ranked over 10-fold StratifiedKFold by the consensus of the median |coefficient| rank and the median permutation
    importance rank (100 repeats).
  - Top 256 kept. **Applied to the training rows of each outer fold only.**
- **Model:** `code/bin_class/lightGBM__5b.py`, function `train_lgbm`.
  - Their search space and pipeline (median imputation, VarianceThreshold, Spearman correlation filter with tuned
    threshold, LightGBM with `class_weight="balanced"`).
  - Optuna with 400 trials, maximising the mean AUC of 5-fold StratifiedGroupKFold by patient.
  - Platt calibration on the out-of-fold predictions of the best trial, then a refit on all training rows.
  - Their seeds (42).

## What is PRISM's, as in the first re-implementation
- **Label and rows:** the scan-level detection label and rows of `prism.analyses.detection` (grade 4). The authors'
  patient-level label is not used. The first re-implementation already reported it (EXPLORATORY section).
- **Folds and evaluation:**
  - the five repeats of fivefold patient-grouped folds (`D.fold_ids`);
  - mean pooled held-out AUC on the intended use (146 scans) and on all 181 grade 4 detection scans;
  - 1,000 bootstrap samples of patients, seed as in `christodoulou_replication.py`;
  - paired differences against the clinical-history model (B1) and the imaging model (I_pure), refitted on the same
    folds.

## Outcome and reading (fixed now)
- **Primary:** the AUC on the intended use with its CI, and its difference from the imaging model and from the
  clinical-history model.
- **Reading for the paper:**
  - this faithful run replaces the first re-implementation as the paper's comparison;
  - the first re-implementation moves to the supplement as a sensitivity analysis;
  - whatever the faithful run gives is reported. If it is not below the imaging model, the paper's claim that the
    imaging model ranks scans better than the radiomics pipeline is withdrawn.
- **Remaining deviations:** any deviation forced by the data is recorded here before results are read (for example,
  scans whose N4 or extraction fails).

## Code
- `prism/analyses/christodoulou_faithful.py`. The authors' functions are imported or copied verbatim, with
  attribution, into `prism/analyses/_christodoulou_vendor.py`.
- Feature table: `outputs/features/radiomics_christodoulou.csv`.
- Results: `outputs/results/analyses/christodoulou_faithful/`.
