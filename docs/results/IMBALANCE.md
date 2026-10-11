# Class imbalance: XGBoost, class weights, oversampling, SMOTE (2026-10-11)

Question: *"Does using something like XGBoost help with the imbalance, or should we be upsampling?"*

**Short answer: neither is needed.** At 120 d the verified labels are 93 / 117 (grade 4) and 100 / 156 (all gliomas)
progression / no progression, a minority share of 44% / 39%. That is mild imbalance. No learner and no re-balancing scheme
changes discrimination by a meaningful amount: ΔAUC vs the C3 ridge baseline ranges from −0.031 to +0.023, and only 4 of 190 CIs exclude 0
(all of them ridge in all gliomas, +0.009 to +0.014). Re-balancing consistently makes calibration worse: O/E falls from
0.95–1.08 to 0.82–0.97, and IPCW Brier rises by up to +0.018. XGBoost/LightGBM do not beat ridge, and their nested-tuned
versions are badly overfit (calibration slope 0.52–0.73). Keep the unweighted ridge baseline.

Code: `prism/analyses/imbalance.py` (`uv run --frozen --no-sync --with xgboost python -m prism.analyses.imbalance --workers 32`;
xgboost 3.2.0 was loaded into an ephemeral overlay env, so the shared `.venv` was not changed. Without xgboost the module
skips the xgb learners and LightGBM 4.6.0 stands in.) Outputs: `outputs/results/analyses/imbalance/{mu.csv, lumiere.csv,
oof_repeats.csv.gz, nested_choices.csv, run.log}`. Run time is about 13 min on 32 CPUs.

## How the current models handle weights (correction to the premise)

The C3 models and the external models do **not** use IPCW sample weights. `c3_radiomics.fit_predict` fits ridge through
`formulations.fit("verified", …)`, which drops scans censored before 120 d and fits with unit weights. The C3 HistGB is
fitted on verified rows without `sample_weight`. `external_lumiere.fit` works the same way and only passes weights in the
`finetune_pooled` arm. IPCW weights enter the evaluation (IPCW AUC/Brier, the calibration-slope fit) and the C1 `ipcw`
training formulation, which C1 found equivalent to verified (all 36 ΔAUC CIs include 0). This analysis therefore crosses
**unit** weights (the current fit) with **ipcw** weights (`training_rows("ipcw")`, censoring KM from the training fold, mean 1).
The weighting makes no difference: ridge ipcw vs unit ΔAUC −0.000 [−0.001, +0.001] in grade 4 and +0.001 [−0.001, +0.003]
in all gliomas. Every rebalanced row below has a unit-weight twin with near-identical numbers in `mu.csv`.

## Design

Same cohort, verified labels, shared 5×5 patient-grouped folds (`outputs/data/folds.csv`) and estimator as C3: the mean over
repeats of the pooled-OOF IPCW AUC(120 d), `evaluate_repeated` with a 1000-draw paired patient-cluster bootstrap. Each model
gets two paired Δs: one vs the C3 ridge baseline (`baseline|ridge|unit|none`) and one vs the same learner, features and
weights with no re-balancing (`d_auc_vs_none`). Reproduction check: ridge/unit/none = 0.698 (grade 4) / 0.720 (all gliomas)
and HistGB = 0.687 / 0.718, identical to `outputs/results/c3/*/results.csv`. Locked LUMIERE ridge = 0.608 and HistGB = 0.620,
identical to `outputs/results/external_lumiere/results.csv`.

- **Features**: baseline (clinical + timing + as-of-scan treatment, = C3) and ctv (shared clinical + timing + volumes, = the
  external feature set).
- **Learners**:
  - ridge: C chosen by inner grouped log-loss, as in `formulations.fit`.
  - histgb: the C3 boosting model.
  - xgb / lgbm with fixed small-data settings: depth 2, lr 0.03, 200 trees, min_child_weight 5, subsample 0.8,
    colsample 0.8, λ 2.
  - xgb_nested / lgbm_nested: a 16-point grid (depth {2,3} × lr {0.03,0.05} × trees {150,300} × min_child_weight {1,5}),
    chosen by inner 3-fold patient-grouped AUC within every outer training fold.
- **Imbalance handling** (training fold only; inner CV re-balances each inner training split and scores the untouched inner
  validation split; weights rescaled to mean 1):
  - none.
  - balanced: class weights that give both classes equal total weight. This is the same as XGBoost's `scale_pos_weight`.
  - oversample: draws training patients that have a positive scan, with replacement, and appends all of that patient's
    positive scans until positives ≥ negatives. Duplicates keep their patient id and IPCW weight, so they never cross a
    train/test or inner-CV boundary.
  - smote: numpy SMOTE on the preprocessed features. Each synthetic point is anchor + u·(neighbour − anchor), using one of
    the anchor's 5 nearest positives **from other patients**, with the anchor's patient id and weight. It was cheap and safe
    to implement. One caveat: binary indicators become fractional (no SMOTE-NC).
- **LUMIERE**: ctv models trained once on all MU scans of the population (seed 0), locked, and scored pooled on LUMIERE
  (`point_metrics`, `cluster_bootstrap` paired vs locked ridge/unit/none), following `external_lumiere.py`.

## Why re-balancing should not change AUC but should break calibration (prior shift)

Suppose the positives are weighted by k, or duplicated k-fold. The fitted model then targets a population whose prevalence
odds are k times larger. For a flexible enough model the Bayes-optimal score becomes

    logit p_k(x) = logit p(x) + log k

This is a strictly increasing transform of p(x), so every rank-based metric is unchanged, including IPCW AUC. Only
calibration-in-the-large moves: every prediction is pushed up, so O/E falls and Brier rises. With balanced classes,
k = 117/93 = 1.26 (log k = 0.23) in grade 4 and 156/100 = 1.56 (log k = 0.44) in all gliomas. A finite, penalised or
tree-based model does not apply a pure intercept shift. The coefficients change a little, oversampling also changes the
effective sample size seen by the penalty, and SMOTE changes the feature distribution. So AUC can move slightly in either
direction, but nothing in the method adds information about who progresses. Imbalance hurts rank-based discrimination only
when it is severe enough that the learner effectively ignores the minority class (e.g. < 5–10%), and 39–44% is far from that.

**The data confirm it.**
- **Mean risk shifts exactly as predicted.** Applying the log k shift to the unweighted ridge OOF predictions predicts a
  mean risk of 0.463 (grade 4) and 0.449 (all gliomas). The balanced-weight ridge actually produced 0.459 and 0.444. For
  XGBoost the predicted values are 0.472 / 0.459 and the actual 0.464 / 0.446. The shifted values were computed from
  `oof_repeats.csv.gz` as `mean(expit(logit p + log k))`; the actual values are `mean_pred` in `mu.csv`.
- **Calibration-in-the-large worsens.** Across all 192 MU configurations the median O/E is 1.01 without re-balancing and
  0.88 / 0.89 / 0.88 with balanced / oversample / SMOTE. The models now over-predict by 10–17%. Median Brier change vs
  none is +0.005 to +0.007.
- **AUC barely moves.** Across the 144 re-balanced configurations, ΔAUC vs the same learner without re-balancing has a
  median of +0.004 (range −0.014 to +0.018). That is 27 of 144 CIs above 0 and 1 below, and every effect is tiny.
- **Calibration slope** is essentially unchanged for the fixed learners (it rose slightly for ridge). Nested boosting stays
  overfit (0.52–0.73) whether or not the data are re-balanced.

## Key results, MU (IPCW weights; mean-over-repeats IPCW AUC, 95% bootstrap CI)

| Pop. | Features | Learner | Imbalance | AUC | Δ vs C3 ridge | Δ vs same learner, none | Brier | O/E | Slope |
|---|---|---|---|---|---|---|---|---|---|
| grade 4 | baseline | **ridge (C3, unit)** | none | **0.698 [0.615, 0.774]** | — | — | 0.219 | 1.04 | 0.89 |
| grade 4 | baseline | ridge | balanced | 0.706 [0.621, 0.780] | +0.008 [−0.001, +0.019] | +0.008 [−0.001, +0.018] | 0.220 | 0.94 | 0.94 |
| grade 4 | baseline | ridge | oversample | 0.704 [0.618, 0.779] | +0.006 [−0.005, +0.018] | +0.006 [−0.005, +0.017] | 0.218 | 0.97 | 0.99 |
| grade 4 | baseline | ridge | smote | 0.706 [0.620, 0.778] | +0.008 [−0.005, +0.021] | +0.008 [−0.005, +0.020] | 0.219 | 0.97 | 0.90 |
| grade 4 | baseline | histgb (C3) | none | 0.687 [0.600, 0.768] | −0.011 [−0.073, +0.048] | — | 0.221 | 1.04 | 0.82 |
| grade 4 | baseline | xgb | none | 0.704 [0.621, 0.780] | +0.006 [−0.060, +0.072] | — | 0.218 | 1.03 | 0.78 |
| grade 4 | baseline | xgb | balanced (= scale_pos_weight) | 0.707 [0.623, 0.782] | +0.009 [−0.057, +0.074] | +0.003 [−0.001, +0.007] | 0.221 | 0.93 | 0.80 |
| grade 4 | baseline | xgb | oversample | 0.711 [0.628, 0.787] | +0.012 [−0.051, +0.075] | +0.007 [−0.002, +0.016] | 0.219 | 0.95 | 0.80 |
| grade 4 | baseline | xgb | smote | 0.713 [0.630, 0.790] | +0.015 [−0.048, +0.078] | +0.009 [−0.001, +0.022] | 0.218 | 0.96 | 0.79 |
| grade 4 | baseline | xgb_nested | none | 0.695 [0.611, 0.771] | −0.003 [−0.062, +0.057] | — | 0.227 | 1.03 | 0.57 |
| grade 4 | baseline | lgbm | none / smote | 0.703 / 0.719 | +0.005 / +0.021 (CIs −0.06…+0.09) | smote +0.017 [+0.004, +0.032] | 0.219 / 0.216 | 1.03 / 0.95 | 0.78 / 0.81 |
| grade 4 | ctv | ridge | none / balanced | 0.668 / 0.679 | −0.030 / −0.019 (CIs −0.12…+0.06) | +0.012 [+0.004, +0.020] | 0.226 / 0.228 | 1.02 / 0.90 | 0.88 / 0.97 |
| grade 4 | ctv | xgb | none / balanced | 0.692 / 0.696 | −0.007 / −0.002 (CIs −0.11…+0.10) | +0.005 [+0.000, +0.010] | 0.221 / 0.223 | 0.97 / 0.88 | 0.79 / 0.81 |
| all | baseline | **ridge (C3, unit)** | none | **0.720 [0.638, 0.792]** | — | — | 0.205 | 1.05 | 0.88 |
| all | baseline | ridge | balanced | 0.728 [0.647, 0.802] | +0.009 [+0.002, +0.016] | +0.008 [+0.001, +0.014] | 0.214 | 0.86 | 0.94 |
| all | baseline | ridge | oversample | 0.733 [0.655, 0.803] | +0.013 [+0.004, +0.023] | +0.012 [+0.002, +0.022] | 0.210 | 0.87 | 1.01 |
| all | baseline | xgb | none | 0.738 [0.660, 0.811] | +0.019 [−0.033, +0.073] | — | 0.199 | 1.04 | 0.86 |
| all | baseline | xgb | balanced | 0.741 [0.661, 0.813] | +0.021 [−0.031, +0.077] | +0.002 [−0.002, +0.007] | 0.208 | 0.86 | 0.86 |
| all | baseline | xgb | oversample / smote | 0.733 / 0.730 | +0.013 / +0.010 | −0.005 / −0.008 (CIs span 0) | 0.208 / 0.211 | 0.88 / 0.88 | 0.83 / 0.78 |
| all | baseline | xgb_nested / lgbm_nested | none | 0.730 / 0.743 | +0.011 / +0.023 (CIs span 0) | — | 0.205 / 0.200 | 1.03 / 1.02 | 0.63 / 0.65 |
| all | ctv | xgb | none / balanced | 0.730 / 0.731 | +0.011 / +0.011 (CIs −0.07…+0.09) | +0.001 [−0.003, +0.004] | 0.201 / 0.211 | 1.00 / 0.83 | 0.87 / 0.86 |

Source: `outputs/results/analyses/imbalance/mu.csv`. The full 192-row grid includes unit-weight twins, histgb and lgbm.
Columns: `d_auc_ipcw_vs_baseline|ridge|unit|none`, `d_auc_vs_none*`, `d_brier_vs_none*`, `oe_ratio`, `cal_slope`, `mean_pred`.

Reading:
- **XGBoost / LightGBM** with sensible small-data settings land within ±0.02 of ridge, and all CIs span about ±0.06. In
  grade 4 they are slightly less well calibrated (slope 0.78 vs 0.89). Tuning them by nested grid does not help AUC
  (grade 4 0.695–0.697) and drives the calibration slope down to 0.52–0.65, the familiar small-data overfit. Boosting is not
  an imbalance fix here; it is just a different learner, with no advantage at n ≈ 210–256 verified scans.
- **Ridge + re-balancing** is the only consistent AUC gain: +0.006 to +0.015. Its CI excludes 0 in all gliomas with
  baseline features (balanced +0.009 [+0.002, +0.016], oversample +0.013 [+0.004, +0.023]) but not in grade 4, the primary
  population. The gain is a small side effect of re-weighting a penalised, misspecified logistic model (the unpenalised
  intercept absorbs log k, and the slopes are re-weighted towards the positives). It sits within the repeat-to-repeat
  noise of these pipelines, it was found post hoc among 144 comparisons, and it costs calibration-in-the-large: O/E goes
  from 1.05–1.08 to 0.86–0.87 in all gliomas, and Brier rises from 0.205 to 0.210–0.214.

## LUMIERE locked test (clinical + timing + volumes, trained on all MU scans)

| Train | Learner | Imbalance | Pooled IPCW AUC | Δ vs locked ridge | Brier | O/E | Slope |
|---|---|---|---|---|---|---|---|
| grade 4 | ridge | none (unit; = external locked) | 0.608 [0.469, 0.739] | — | 0.247 | 1.33 | 0.38 |
| grade 4 | ridge | balanced / oversample / smote (ipcw) | 0.609 / 0.617 / 0.615 | +0.001 / +0.008 / +0.007 (CIs −0.014…+0.034) | 0.244 / 0.229 / 0.230 | 1.17 / 1.00 / 1.04 | 0.37 / 0.64 / 0.63 |
| grade 4 | histgb | none (unit; = external locked) | 0.620 [0.495, 0.733] | +0.011 [−0.131, +0.148] | 0.226 | 0.99 | 0.73 |
| grade 4 | xgb | none / balanced / oversample (ipcw) | 0.561 / 0.556 / 0.578 | −0.048 / −0.053 / −0.030 (CIs −0.20…+0.12) | 0.238 / 0.242 / 0.241 | 1.01 / 0.89 / 0.83 | 0.38 / 0.36 / 0.44 |
| grade 4 | xgb_nested | none (ipcw) | 0.562 [0.432, 0.683] | −0.046 [−0.202, +0.101] | 0.262 | 1.10 | 0.15 |
| all | ridge | none (unit) | 0.599 [0.462, 0.728] | — | 0.247 | 1.30 | 0.38 |
| all | ridge | balanced (ipcw) | 0.611 [0.480, 0.733] | +0.012 [−0.009, +0.036] | 0.231 | 0.92 | 0.63 |
| all | xgb | none / balanced (ipcw) | 0.577 / 0.587 | −0.023 / −0.012 (CIs −0.15…+0.12) | 0.239 / 0.245 | 1.02 / 0.82 | 0.41 / 0.42 |

Source: `outputs/results/analyses/imbalance/lumiere.csv` (all learners and weightings, `chosen` = nested grid point).

- **XGBoost/LightGBM transport worse than ridge or the C3 HistGB.** The C3 HistGB is more regularised (min_samples_leaf 20,
  max_features 0.5). The locked boosting fits use a single seed, so differences of a few points between them are noise.
- **Re-balancing does not change external discrimination** (ΔAUC ≤ 0.012, all CIs span 0).
- **The improved external O/E for re-balanced ridge is a coincidence, not a fix.** It moves from 1.33 to 1.00 because the
  locked MU model *under*-predicts LUMIERE risk, and re-balancing happens to push risks up by a similar amount. The
  principled tool for that is recalibration on the target cohort, which `EXTERNAL_LUMIERE.md` already reports (O/E 0.93–0.97).

## Recommendation

1. **Do not upsample, SMOTE or class-weight.** With a 39–44% minority, re-balancing cannot improve a rank-based metric in
   expectation. Here it moves IPCW AUC by ≤ 0.02 (no CI in the primary grade-4 analysis excludes 0) and it systematically
   biases risks upward: O/E 0.82–0.97, worse Brier. If a single number has to be quoted for the reviewer: grade-4 ridge
   balanced ΔAUC +0.008 [−0.001, +0.019], O/E 1.04 → 0.94.
2. **Do not switch to XGBoost for this.** Fixed small-data XGBoost: grade 4 ΔAUC +0.006 [−0.060, +0.072], all gliomas
   +0.019 [−0.033, +0.073]. The nested-tuned version is worse calibrated (slope ≈ 0.6) and transports worse to LUMIERE
   (0.56 vs 0.61). `scale_pos_weight` behaves exactly like class weights.
3. **Keep the C3 ridge baseline (verified labels, unit weights) as the headline model.** Adding IPCW training weights is
   harmless but unnecessary (ΔAUC ≤ 0.001).
4. **If a skewed operating point is wanted** (e.g. high sensitivity), choose the decision threshold on the calibrated risk
   (decision curves, `CLINICAL_UTILITY.md`) rather than re-balancing the training data.
5. **If re-weighting is ever used** (e.g. for a much rarer endpoint), undo the prior shift by subtracting log k from the
   logit, or recalibrate. This correction was not run here.

Limitations: one horizon (120 d); boosting hyperparameters are small-data defaults plus a 16-point grid, not an exhaustive
search; SMOTE interpolates binary indicators; LUMIERE boosting results are single-seed locked fits.
