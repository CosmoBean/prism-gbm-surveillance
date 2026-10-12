# SHAP on the PRISM report split, and why that split scores high

Code: `prism/analyses/shap_prism_split.py` (`python -m prism.analyses.shap_prism_split --n-boot 1000`, about 1 min, single
process). Outputs: `outputs/results/analyses/shap_prism_split/` (all numbers below come from there unless stated otherwise).
Split: the PRISM report split (seed 62). Its test patients are the ones in `legacy/radiomics/models/calibrated/test_predictions.csv`:
30 patients / 84 scans originally, and 29 patients / 82 scans in the label-fixed all-glioma cohort. The training set is the
other 126 patients. AUCs are on the naive 120-d label, as in the PRISM report, unless marked IPCW.

## 1. PRISM report model (as shipped)

- **Reconstruction.** The input matrix is rebuilt from the legacy feature JSONs plus the `hybrid_basic` clinical codes, using the
  PRISM report case table (`split_variance.legacy_table`). The bundle then reproduces `test_predictions.csv` on all 84 rows. Max abs
  difference: 1.1e-15 calibrated and 1.4e-15 raw (`shipped_check.csv`). The shared `.venv` unpickles the bundle, so no legacy env was needed.
- **Model.** It is an L2 logistic regression (`liblinear`, C = 0.0087, balanced class weights) on 46 standardised columns. Of the 48
  selected columns, the preprocessor's correlation filter drops `flair_glszm_ZoneEntropy` and `flair_wavelet-LLL_glszm_ZoneEntropy`. A
  Platt calibrator sits on top: sigmoid(3.78·p_raw − 2.62), which is monotone, so the ranking is unchanged.
- **Explainer.** The model is linear, so I used exact linear SHAP in the classifier's log-odds: φ_j = β_j (x_j − mean over the 231
  PRISM training scans), with base value −0.052. As a check, a PermutationExplainer on the *calibrated probability* (100 sampled
  training rows) ranks the features the same way (Spearman 0.996 on mean |SHAP|).
- **Agreement with the shipped SHAP csv.** Spearman with `shap_feature_importance.csv` is 0.997, and the top 10 are identical. The
  shipped modality shares (T1c 0.559 / FLAIR 0.311 / clinical 0.130) match this analysis's *share of summed feature mean |SHAP|*
  exactly (0.559 / 0.312 / 0.129). The shipped csv is therefore the same computation on the 84 test scans.

| Rank | Feature (82 test scans) | mean \|SHAP\| | Rank on training scans | Rank in shipped csv |
|---|---|---|---|---|
| 1 | t1c_log-sigma-3-0-mm-3D_firstorder_Variance | 0.140 | 10 | 1 |
| 2 | t1c_wavelet-LLL_glcm_ClusterTendency | 0.121 | 1 | 2 |
| 3 | t1c_glszm_GrayLevelVariance | 0.112 | 2 | 3 |
| 4 | t1c_wavelet-LLH_glszm_GrayLevelNonUniformityNormalized | 0.103 | 13 | 5 |
| 5 | clin_atrx_mutation__0 | 0.100 | 3 | 6 |
| 6 | t1c_wavelet-LLL_ngtdm_Complexity | 0.100 | 9 | 4 |
| 7 | t1c_log-sigma-1-0-mm-3D_firstorder_Minimum | 0.098 | 8 | 8 |
| 8 | t1c_wavelet-HLL_glszm_SmallAreaLowGrayLevelEmphasis | 0.098 | 6 | 7 |
| 9 | flair_glszm_SmallAreaHighGrayLevelEmphasis | 0.090 | 5 | 9 |
| 10 | clin_idh2_mutation__2 | 0.082 | 4 | 10 |

**Group shares** (`shipped_groups.csv`). There are two ways to measure them. The first is the share of mean |per-scan group sum|. The
second, in brackets, is the share of summed feature mean |SHAP|, which is the shipped csv's definition. The second hides cancellation
within a group.

- Modality: T1c 52% [56%], FLAIR 26% [31%], clinical codes 22% [13%].
- Texture class: GLSZM 28% [41%], first-order 26% [22%], clinical 18%, GLCM 13%, NGTDM 9%, GLRLM / GLDM / shape ≤ 2% each.
- Filter: wavelet 42% [54%], LoG 23%, clinical 21%, original 14%.

The six MU clinical code columns carry about a fifth of the per-scan signal. The rest is spread thinly over 40 texture and
first-order features: no single feature has more than 6% of the feature sum. The test-set profile is close to the training-set
profile (Spearman 0.94).

Plots: `shipped_beeswarm.png`, `shipped_bar.png`.

## 2. Our models on the same split

Fitted as in `head_to_head.py`. Predictions equal `c3.fit_predict` exactly (max abs difference 0, `ours_check.csv`). Ridge uses
exact linear SHAP and boosting uses TreeSHAP; both reuse the `shap_contrib` helpers.

| Model | AUC naive / IPCW | Group shares (mean \|group SHAP\|) | Same model, whole-cohort OOF shares |
|---|---|---|---|
| Baseline ridge | 0.871 / 0.851 | treatment 55%, clinical 29%, timing 16% | 52 / 29 / 19% |
| Baseline boosting | 0.844 / 0.824 | treatment 49%, clinical 34%, timing 17% | 50 / 35 / 15% |
| Baseline + legacy radiomics top10 (concat) | 0.862 / 0.845 | radiomics 49%, treatment 29%, clinical 15%, timing 7% | n/a |

Top features (`ours_features.csv`):

- **Ridge:** rt_start_day, idh_unknown, idh_mutant, chemo_started, mgmt_unknown, rt_started.
- **Boosting:** rt_start_day (32%), age (18%), surgery_day (16%), chemo_started, days_from_diagnosis.
- **Radiomics model:** its 10 selected legacy features are almost all T1c GLCM/GLDM wavelet-LLL or original-image texture
  (Autocorrelation, SumAverage, JointAverage, LargeDependenceLowGrayLevelEmphasis). Each one is about as large as rt_start_day.

Plots: `base_ridge_{beeswarm,bar}.png`, `base_gbm_{beeswarm,bar}.png`.

**Test-set profile vs whole-cohort OOF profile** (`profile_test_vs_oof*.csv`, OOF from `outputs/results/analyses/shap/all_glioma/`):

- **Group shares** are essentially the same as in the OOF profile (table above).
- **Feature ranks** move more: Spearman between the two profiles is 0.66 for ridge and 0.76 for boosting. In ridge, rt_start_day
  and the IDH codes move up and rt_started / early_post_rt move down. Boosting leans more on surgery_day (rank 3 vs 6).
- **Cause of the movement:** a single fit on 126 patients rather than the test patients themselves. In the 5×5 CV, the OOF SHAP
  profile of these 29 patients matches that of the other 126 (Spearman 0.95 ridge, 0.996 boosting).
- **Conclusion:** the split does not lean on unusual features. It uses the same treatment and timing signal as everywhere else.

## 3. Why is this split "magical"?

### Composition (`composition.csv`; percentile = rank among the 500 design splits)

| | Full cohort | PRISM report test set | 500 splits: mean (2.5–97.5%) | Percentile |
|---|---|---|---|---|
| Scans / patients | 308 / 155 | 82 / 29 | 84.5 / 29.8 | |
| Scans per patient | 1.99 | 2.83 | 2.84 (2.70–3.00) | 45 |
| Event rate, naive | 0.325 | 0.268 | 0.254 (0.165–0.348) | 62 |
| Censored before 120 d (verified label NaN) | 0.169 | 0.122 | 0.119 | 56 |
| Median days from diagnosis | 97 | 138.5 | 131 | 79 |
| Grade 4 / GBM | 0.81 / 0.70 | 0.80 / 0.77 | 0.82 / 0.63 | 44 / **97** |
| IDH-mutant scans | 0.195 | 0.146 | 0.271 (0.131–0.403) | **5** |
| Pre-RT scans (rt_started = 0) | 0.373 | **0.439** | 0.353 (0.220–0.474) | **89** |
| … event rate in pre-RT scans | 0.087 | **0.000 (0 / 36)** | 0.044 (0–0.138) | 15 |
| During RT | 0.026 | 0.049 (4 scans, 3 events) | 0.019 | 98 |
| ≤ 12 weeks post-RT | 0.338 | 0.244 | 0.283 | 16 |
| Later post-RT | 0.263 | 0.268 | 0.345 (0.243–0.450) | **6** |
| AUC of a no-training rule "scan is post-RT" | 0.677 | **0.740** | 0.675 (0.575–0.772) | **92** |

### Easy pairs

All 36 pre-RT test scans are negative. That makes 60% of the positive–negative pairs a progression scan against an immediately
post-operative, pre-RT scan (`auc_pair_decomposition.csv`):

| Model | AUC, all pairs | Positives vs pre-RT negatives | Positives vs other negatives |
|---|---|---|---|
| PRISM report model | 0.802 | 0.823 | 0.771 |
| Baseline ridge | 0.871 | 0.962 | 0.735 |
| Baseline boosting | 0.844 | 0.933 | 0.710 |
| Baseline + legacy radiomics top10 | 0.862 | 0.934 | 0.754 |

AUC within subsets of the test set (`subset_auc.csv`, naive AUC with 95% patient-cluster bootstrap CI, 1000 resamples). The
IPCW AUC with its 95% patient-cluster bootstrap CI is also given (an earlier run could not compute it: resamples without any
censoring crashed `censoring_survival`; fixed in `prism/models/formulations.py`, G = 1 when nothing is censored).

| Subset (n scans / patients / positives) | PRISM report model | Baseline ridge | Baseline ridge, whole-cohort OOF |
|---|---|---|---|
| All (82 / 29 / 22) | 0.802 [0.668–0.910] | 0.871 [0.762–0.956] | 0.775 |
| Post-RT only (42 / 19 / 19) | 0.778 [0.606–0.914], IPCW 0.770 [0.604–0.907] | 0.730 [0.483–0.889], IPCW 0.718 [0.481–0.880] | 0.677 |
| Pre-RT or during RT (40 / 16 / 3) | 0.793 [0.544–0.961] | 1.000 | 0.639 |

**Per-phase SHAP** (`phase_profile.csv`). On the 36 pre-RT scans, the PRISM report model's T1c features push the log-odds down by
−0.50 on average (total −0.65); the top feature, t1c LoG-σ3 Variance, alone contributes −0.17. The baseline ridge does the same
thing through treatment (−0.38) and timing (−0.15). Both models therefore recognise the post-operative pre-RT scan, through
different routes.

### Across the 500 splits

Source: `split_auc_vs_composition.csv`, `split_auc_composition_ols.csv`, `per_split_composition.csv`. Per-split composition was
recomputed from the test-patient lists in `split_variance/per_split_auc.csv`.

**Baseline ridge.** Per-split AUC tracks the phase mix:

| Composition variable | Spearman with naive AUC | Spearman with IPCW AUC |
|---|---|---|
| Pre-RT event rate | −0.61 | −0.57 |
| AUC of the "post-RT" rule | +0.57 | +0.51 |
| Fraction of later post-RT scans | −0.26 | |
| Fraction of pre-RT scans | +0.22 | |

Nine composition variables explain R² 0.42 of the AUC (10-fold CV). From composition alone they predict 0.851 for seed 62,
against a split mean of 0.801 and an observed 0.871.

**PRISM report pipeline, re-selected per split.** Composition explains much less (CV R² 0.10 naive, 0.15 IPCW). The strongest
correlates are:

| Composition variable | Spearman with naive AUC |
|---|---|
| IDH-mutant fraction | −0.30 |
| AUC of the "−visit index" rule | +0.28 |
| AUC of the "−days from diagnosis" rule | +0.24 |
| AUC of the "post-RT" rule | +0.22 |

Composition predicts 0.773 for seed 62, against a mean of 0.720 and an observed 0.801. So about two thirds of the split's excess
over the average is explained by its mix, and the rest is luck in the particular patients.

## Plain-language answer

The test set is unusually easy to rank. 44% of its scans are early post-operative scans taken before radiotherapy started, and none
of these 36 is followed by progression within 120 days; in the whole cohort, 9% of such scans are. Every model can tell that a scan
is a fresh post-op, pre-RT scan:

- the clinical baseline knows it from the treatment dates;
- the radiomics model knows it from how the T1c image looks.

So 60% of the case–control comparisons in this test set are near-free wins. On top of that, the set has few IDH-mutant patients
(5th percentile) and few late post-RT scans (6th percentile), the two harder groups for the radiomics pipeline. The SHAP profiles
show no unusual feature on this split. Restricted to post-RT scans, the hard and clinically relevant part, the PRISM report model
scores 0.78 [0.61–0.91] and the baseline 0.73 [0.48–0.89]. Both intervals are wide and overlap, and both values are in the range
the baseline reaches over the whole cohort (0.68 OOF). Composition explains about two thirds of the split's advantage over an
average split, for both the PRISM report pipeline and the baseline. The remainder is sampling luck among 29 patients.
