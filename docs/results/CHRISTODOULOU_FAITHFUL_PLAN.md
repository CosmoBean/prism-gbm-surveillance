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

## Deviations recorded before results (2026-11-16)

Written after the extraction and a one-fold smoke test (10 trials, no held-out prediction scored), before any
held-out AUC was computed.

- **Extraction: none forced.** 596 MU timepoints, 594 with all four sequences and a non-empty `tumorMask`; their
  extraction ran on all 594 without a warning or error (4,892 features per scan, no missing or infinite value, no
  constant column). All 181 grade-4 detection scans (and all 313 grade-4 scans of the detection frame) have features.
  Wall time 2 h 36 min on 20 CPUs (median 282 s per scan, single-threaded).
- **Ranking: their permutation importance never runs on our data.** `compute_importance_traincv` computes it only on
  inner test folds with at least 30 rows (`MIN_TEST_SIZE_FOR_PI = 30`). Our outer training sets have 132-155 rows, so
  the 10 inner folds have 13-16 rows and their code sets every permutation importance to 0. The consensus rank then
  reduces to the median |coefficient| rank. In the smoke-test fold, 88 of the 495 ranked features had a non-zero
  median coefficient; the remaining 168 places of the top 256 are ties that their sort leaves in column-name order.
  This is their code's behaviour on a training set of this size; it is kept unchanged and reported.
- **Objective (clarification, not a change).** Their `train_lgbm` maximises the pooled out-of-fold AUC of the 5-fold
  StratifiedGroupKFold (`oof_auc`), not the mean of the fold AUCs written above; their code is used. Their Platt
  calibrator is fitted on the out-of-fold probabilities (not logits) of the best parameters, refitted with the same
  folds, as in their code.
- **Threads (compute only).** Their code runs Optuna and LightGBM with `n_jobs=-1`. To stay within 20 CPUs, the 25
  outer folds run in 20 parallel processes, each with Optuna `n_jobs=1` and LightGBM `n_jobs=1`. Sequential trials
  make the TPE search deterministic (seed 42); their threaded search is not. Nothing else in the search changes.
- **Seeds.** Their constants are kept: the ranking's StratifiedKFold, the inner StratifiedGroupKFold, the TPE sampler
  and LightGBM all use 42 in every outer fold (not the repeat index used by the first re-implementation).
- **Plumbing.** Their patient-level label column is filled with PRISM's detection label (non-missing = positive, as
  their code reads it); rows are the training rows (positives and primary negatives) of each outer fold; the model
  predicts every grade-4 scan of the held-out fold.
