# SHAP contributions (where the model signal comes from)

Code: `prism/analyses/shap_contrib.py` (`python -m prism.analyses.shap_contrib`, ~20 s on 32 CPUs).
Outputs: `outputs/results/analyses/shap/<population>/` (grade 4 primary, all gliomas secondary). Numbers below are from the
re-run after the radiomics clipping fix (2026-10-11 18:50, [FIX_RADIOMICS_CLIP.md](FIX_RADIOMICS_CLIP.md)), which this
analysis prompted. The non-radiomics models (1)–(3) and (5) are unchanged by the fix. Only model (4) changed.

## Setup

- C3 setup: same cohort, verified 120-d labels, shared 5×5 patient-grouped folds, in-fold `BASE_PRE` (median imputation +
  missingness indicators + scaling) and the same learners as `prism/experiments/c3_radiomics.py`. Feature groups are from
  `prism/features/tabular.py`.
- **Out-of-fold.** In each of the 25 fits, the model is fitted on the training patients and the held-out scans are explained.
  Every scan is explained once per repeat. Reproduced OOF predictions match `c3/<pop>/oof_repeats.csv.gz` exactly
  (max |Δ| = 0) for the baseline ridge, the baseline boosting model and the radiomics model (`model_auc.csv`).
- **Log-odds space.** Ridge: exact linear SHAP, φ_j = β_j (x_j − mean_train x_j), on the in-fold standardised features
  (= `shap.LinearExplainer`, independent masker). Boosting: `shap.TreeExplainer` run directly on sklearn's
  `HistGradientBoostingClassifier`, which shap 0.49 supports natively, so no LightGBM stand-in was needed. It uses the
  `tree_path_dependent` mode, and additivity to the decision function is asserted to 1e-6. The `interventional` mode was not
  used: with these models it returned a wrong expected value and broke additivity by up to 0.77 logits on 2 of the 5 folds checked during development.
- **Group SHAP** = the per-scan sum of a group's feature SHAP values. Missingness indicators count in their column's group.
  Share = mean |group SHAP| / sum over groups. **Stability**: features and groups are ranked by mean |SHAP| on each held-out
  fold, giving the median rank [IQR] over 25 fits.
- Models: (1) baseline ridge (headline); (2) baseline boosting; (3) full non-radiomics model (+ volumes, morphology, delta),
  ridge and boosting; (4) baseline + radiomics with the most-chosen nested C3 configuration,
  `legacy|none|pca10|stack|ridge` (chosen in 9/25 grade-4 fits and 14/25 all-glioma fits); (5) LUMIERE locked model
  (shared clinical + timing + volumes, from `external_lumiere.py`), ridge and boosting.

OOF IPCW AUC of the explained models (grade 4 / all gliomas, `model_auc.csv`):

| Model | Grade 4 | All gliomas |
|---|---|---|
| Baseline ridge | 0.698 | 0.720 |
| Baseline boosting | 0.687 | 0.718 |
| Full non-radiomics ridge | 0.692 | 0.727 |
| Full non-radiomics boosting | 0.694 | 0.739 |
| Baseline + radiomics, single most-chosen config | 0.721 | 0.754 |

The radiomics row is one fixed configuration, so it is post-hoc. The honest nested estimate is in FINAL_RESULTS.md.

## Grade 4 (primary)

| Model | Group shares (mean |group SHAP|, SD over 25 fits) | Top features: mean |SHAP|, median rank [IQR] |
|---|---|---|
| Baseline ridge | treatment 58% (5), clinical 25% (5), timing 17% (6) | rt_started 0.158, rank 2 [1–4]; previous_brain_tumor 0.146, rank 4 [2–6]; rt_start_day 0.144, rank 5 [2–9]; early_post_rt 0.114, rank 7 [4–10] |
| Baseline boosting | treatment 51% (6), clinical 35% (6), timing 14% (3) | age 0.409, rank 1 [1–2]; rt_start_day 0.313, rank 2 [2–3]; rt_started 0.240, rank 3 [2–4]; surgery_day 0.125, rank 5 [4–6] |
| Full ridge | treatment 34%, morphology 21%, delta 15%, clinical 13%, volumes 10%, timing 8% | rt_started 0.082; rt_start_day 0.080; age 0.079; previous_brain_tumor 0.077 (each ≤ 3.4%; credit spread over 84 columns) |
| Full boosting | treatment 26%, morphology 23%, clinical 21%, delta 13%, volumes 13%, timing 3% | age 0.345, rank 1 [1–2]; rt_start_day 0.272, rank 3 [1–4]; rt_started 0.179; t1c_et_p90_rel 0.173, rank 5 [3–6] |
| + radiomics | treatment 48%, clinical 20%, timing 16%, radiomics 16% (SD 6) | radiomics_score 0.226, rank 1 [1–3]; rt_started 0.155; rt_start_day 0.143; previous_brain_tumor 0.141 |

Sources: `grade4/{features,groups,imaging_share}.csv`. Figures for each model: `grade4/<model>_{bar,beeswarm,dependence}.png`.

**Do timing features dominate? Not the timing group by itself, but time-relative information does.** The timing group
accounts for only 17% (ridge) and 14% (boosting) of the baseline contribution. However, the "treatment" group, which is the
largest, is mostly time-relative:
- `rt_started` is whether RT had started by the scan, i.e. an early-scan indicator;
- `rt_start_day` and `surgery_day` are days from diagnosis;
- `missingindicator_rt_*` marks scans taken before RT.

Counting these and the delta history features as time-like gives 35% of the baseline ridge's feature-level |SHAP| and
47% of the boosting model's (`timelike_share_of_feature_sum`).

The boosting dependence plots (`base_gbm_dependence.png`) show:
- risk falls steeply with later `rt_start_day`;
- scans before RT start get −0.4 to −0.8 logits;
- age has a step near 60 years.

Most of the baseline signal is therefore *where the scan sits in the treatment course* plus age and molecular status. This
fits the schedule-coupling result (SCHEDULE_COUPLING.md). SHAP alone cannot tell biology from scheduling.

**Imaging vs non-imaging (model 3).** Imaging groups (volumes + morphology + delta) take **45%** (ridge) and **51%**
(boosting) of the contribution (`imaging_share.csv`; per-scan medians 42% / 50%). Moving the time-like delta columns
(has_prior, n_prior_scans, days_since_prior) to non-imaging barely changes this: 45% / 51%. The top imaging features are
in the boosting model: ET intensity (t1c_et_p90_rel, t1c_et_rel), ET extent (log_et_max_axial,
et_largest_component_fraction) and log_et_cc.

**Yet the full models are not better** than the baseline (0.692 / 0.694 vs 0.698). The imaging features take over credit
from correlated treatment and clinical features; they do not add new discrimination. Treatment's share falls from 58% to
34% (ridge) when they are added.

**Radiomics (model 4).**

*Defect found here (pre-fix run).* The stacked radiomics score had a pipeline defect:
- Legacy FLAIR LoG `ngtdm_Coarseness` has the PyRadiomics 1e6 sentinel in 0156_T2 and 0271_T6 (3 columns each) and in
  0242_T6 and 0268_T3 (1 column each); see FIX_RADIOMICS_CLIP.md.
- These scans gave inner-OOF stacked training scores of −10⁴ to −4.6×10⁶ in 20/25 grade-4 fits and 25/25 all-glioma fits.
- A held-out affected scan got |φ| ≈ 10⁵ and a saturated prediction.
- Untrimmed, radiomics took a meaningless 99.9% share. After the degenerate rows were dropped it got 9.5% in grade 4.
- Its rank was unstable (IQR 1–32), and its contribution was ≈ 0 (median |φ| < 0.01) in 12/25 fits.

C3 itself was affected, and `c3.selector` now clips every feature to its training 1st/99th percentiles (FIX_RADIOMICS_CLIP.md).

*After the fix* (`radiomics_outliers.csv`):
- No training fit has an outlier score, no held-out row is dropped, and no fit has median |φ| < 0.01. `rad_ridge_trim`
  is therefore identical to `rad_ridge`. The code still uses the training median as the stacked score's SHAP reference.
- Grade 4: radiomics takes a **16% share (SD 6)**, and radiomics_score is the top single feature (mean |SHAP| 0.226, median
  rank 1 [1–3], 9.7% of the feature-level sum). Treatment stays the largest group (48%).
- **Imaging share in model 4 = 23% (grade 4), 32% (all gliomas).**
- This model (0.721) is post hoc. The nested C3 estimate, which accounts for selection, is lower than the baseline
  (−0.032 [−0.084, +0.017]), so a large SHAP share for the radiomics score does not mean it adds discrimination.

## All gliomas (secondary)

The pattern is the same (`all_glioma/*.csv`):
- **Baseline ridge:** treatment 52%, clinical 29%, timing 19%. Top features are rt_started, chemo_started, rt_start_day,
  early_post_rt and idh_unknown (each 6–7%).
- **Baseline boosting:** age 24% (rank 1 in all 25 fits), rt_start_day 16%.
- **Full models:** imaging share 49% (ridge) / 53% (boosting).
- **Radiomics model (after the clipping fix, no rows trimmed):** radiomics_score has rank 1 [1–1] (14.7% of the
  feature-level sum), and the radiomics group has a 24% share, rank 2 after treatment (40%). Here the score carries more
  weight, which matches the +0.028 nested ΔAUC in all gliomas (CI spans 0).

## LUMIERE locked model (what drives transfer)

The models are fitted on MU (`external_lumiere.fit`) and explained on LUMIERE. Predictions match
`external_lumiere/locked_predictions.csv` exactly. Pooled AUC is 0.608 for ridge and 0.620 for boosting in grade 4
(`lumiere_check.csv`). In the comparisons below, "MU" means the same locked model explained in-sample on MU.
Sources: `lumiere_{features,groups}.csv` and `lumiere_{ridge,gbm}_mu_vs_lumiere.png`.

| Grade-4-trained | MU group shares | LUMIERE group shares | Mean logit shift, MU → LUMIERE |
|---|---|---|---|
| Ridge | clinical 39%, volumes 34%, timing 27% | clinical 56%, volumes 30%, timing 14% | −0.17 → **−0.81** |
| Boosting | clinical 38%, volumes 39%, timing 23% | volumes 46%, clinical 35%, timing 19% | −0.09 → −0.25 |

The shifts are not explained by the feature *rankings*, which are similar. They come from three **systematic signed
contributions** that appear only on LUMIERE:

1. **idh_unknown (ridge).** IDH is unknown far more often in LUMIERE (mean z +2.28 vs MU). The MU ridge learned
   "unknown IDH → lower risk", so this one feature contributes a mean −0.71 logits. Its mean |SHAP| is 0.77 on LUMIERE
   vs 0.13 on MU, which makes it the largest LUMIERE contributor. Boosting gives it no weight (0.000). This is the main
   reason ridge under-predicts on LUMIERE (O/E 1.33) while boosting is calibrated (O/E 0.99).
2. **log_et_cc (domain shift in the segmenter).** DeepBraTumIA ET volumes are lower (mean z −0.72). They contribute −0.32
   (ridge) and −0.28 (boosting) logits on average on LUMIERE, against ≈ 0 on MU. log_et_cc is the top LUMIERE feature for
   boosting (|SHAP| 0.52 vs 0.43 on MU).
3. **missingindicator_early_post_rt.** On MU this indicator (RT date unknown) is a strong contributor: |SHAP| 0.28 for
   ridge, 0.11 for boosting. It is never set in LUMIERE, which adds +0.11 / +0.05 logits there. This is a data-availability
   artefact, not biology.

The 10.6% of LUMIERE scans without segmentation receive MU-median volumes.

**Rank stability:** the MU-CV fold models applied to LUMIERE (`lumiere_folds_rank_*`) give the same picture. Group ranks on
LUMIERE vary less than on MU (ridge: clinical rank 1 in all 25 fits).

All gliomas shows the same direction: ridge LUMIERE shift −0.44 vs MU −0.17, driven by idh_unknown (−0.58) and log_et_cc
(−0.27).

## Caveats

- **Correlated features split credit.** The treatment, timing and clinical features are strongly inter-correlated, and so
  are the morphology and volume features. Group SHAP (summed within group) is more robust than single-feature values. Even
  so, a large share does not mean a feature or group is needed for discrimination: the full models give imaging about 50%
  of credit with no AUC gain.
- **Different SHAP flavours.** Ridge uses an interventional (independent) baseline and boosting uses path-dependent TreeSHAP,
  so their absolute magnitudes are not strictly comparable. Compare shares and ranks within a model.
- **SHAP is not causal.** It describes the fitted model, not the disease. The baseline relies mostly on timing relative to
  treatment, which is partly schedule-driven.
- **Repeated explanations.** Every MU scan is explained 5 times, once per repeat; plots show per-scan means. Censored scans
  are explained as well, because the model predicts for them.
