# Literature baselines ladder and nested hyperparameter grid (2026-10-11)

Code: `prism/analyses/baselines.py` (`python -m prism.analyses.baselines [--workers 8] [--n-boot 1000]`).
Outputs: `$PRISM_OUTPUTS/results/analyses/baselines/{ladder.csv, lumiere.csv, nested_choices.csv, prevalence.csv,
oof_repeats.csv.gz, forest.png}`. Numbers below come from a private run (`PRISM_OUTPUTS=<scratchpad>/out-baselines`:
post-fix `outputs/data` (308 scans / 155 patients; grade 4 = 249 scans) + the fixed `measurements.csv` from FIX_FEATURES).
Regenerate them on the final outputs.

Protocol (same as C3): shared 5x5 patient-grouped folds (`outputs/data/folds.csv`), models fitted on verified 120-d
labels, headline = mean over repeats of the pooled-OOF IPCW AUC(120 d), 95% CI and paired ΔAUC vs the **C3 ridge
baseline** (clinical + timing + treatment) from a 1000-draw patient-cluster bootstrap (`metrics.evaluate_repeated`).
Calibration slope and O/E = mean over repeats. The reference reproduces `c3_radiomics.fit_predict` exactly (max |Δp| = 0
on the folds checked).

Baselines (docs/literature/comparison.md §5):
- **B0** persistence: log(1 + ET cc) now; prior trend: log-ratio of ET vs the previous scan (0 without a prior).
- **B1** volumetric RANO-style rule: ET ≥ 40 % and ≥ 1 cc above the past-only nadir (measurable nadir ≥ 0.1 cc; nadir
  over post-RT scans when an RT end date and an earlier post-RT scan exist), or ≥ 1 cc from a ~0 cc nadir. Positive in
  25 % of grade-4 scans; the post-RT baseline changes 1 of 249 flags vs the all-prior nadir. Variants: + new ET component,
  RANO 2.0 (no call in the 12-wk post-RT window), continuous log-ratio vs nadir. Scores get an in-fold 1-D logistic map
  for calibration only (unfitted-score AUC in `auc_raw`).
- **B4** Hashim-style Cox PH (log ET + age + IDH + MGMT [+ grade 4 indicator in all gliomas]; sksurv, ridge α = 0.1),
  fitted in-fold on all training scans, risk = 1 − S(120 d). lifelines is not in the environment.

## MU ladder

| Model | Grade 4 AUC [95% CI] | ΔAUC [95% CI] | slope | O/E | All gliomas AUC [95% CI] | ΔAUC [95% CI] | slope | O/E |
|---|---|---|---|---|---|---|---|---|
| **Baseline ridge (C3, reference)** | **0.698** [0.615, 0.774] | — | 0.89 | 1.04 | **0.720** [0.638, 0.792] | — | 0.88 | 1.06 |
| Clinical only | 0.585 [0.496, 0.666] | −0.113 [−0.208, −0.026] | 1.01 | 0.96 | 0.619 [0.540, 0.696] | −0.101 [−0.177, −0.031] | 0.86 | 0.97 |
| Timing only | 0.559 [0.475, 0.637] | −0.139 [−0.214, −0.070] | 0.53 | 1.04 | 0.607 [0.528, 0.684] | −0.112 [−0.175, −0.059] | 0.74 | 1.05 |
| Clinical + timing | 0.644 [0.560, 0.721] | −0.054 [−0.103, −0.012] | 0.98 | 1.03 | 0.693 [0.617, 0.766] | −0.027 [−0.061, +0.007] | 0.93 | 1.05 |
| B0 log ET volume | 0.636 [0.541, 0.723] | −0.062 [−0.183, +0.043] | 0.77 | 0.97 | 0.673 [0.591, 0.752] | −0.046 [−0.142, +0.054] | 0.84 | 0.97 |
| B0 ΔET vs previous | 0.546 [0.479, 0.614] | −0.153 [−0.241, −0.056] | 0.51 | 0.98 | 0.531 [0.465, 0.590] | −0.189 [−0.285, −0.101] | 0.35 | 0.98 |
| B1 rule (binary) | 0.551 [0.480, 0.620] | −0.147 [−0.239, −0.062] | 0.77 | 0.98 | 0.554 [0.488, 0.615] | −0.166 [−0.258, −0.087] | 0.79 | 0.99 |
| B1 rule + new ET component | 0.513 [0.440, 0.581] | −0.185 [−0.267, −0.100] | 0.31 | 0.98 | 0.530 [0.464, 0.588] | −0.189 [−0.274, −0.116] | 0.56 | 0.98 |
| B1 rule, RANO 2.0 window | 0.508 [0.440, 0.577] | −0.191 [−0.289, −0.098] | 0.50 | 0.97 | 0.509 [0.448, 0.568] | −0.210 [−0.301, −0.119] | 0.54 | 0.97 |
| B1 continuous (vs nadir) | 0.562 [0.492, 0.633] | −0.136 [−0.232, −0.036] | 0.45 | 0.97 | 0.538 [0.464, 0.603] | −0.182 [−0.281, −0.089] | 0.23 | 0.97 |
| B4 Hashim Cox | 0.628 [0.538, 0.711] | −0.070 [−0.179, +0.031] | 0.66 | 0.95 | 0.678 [0.596, 0.755] | −0.041 [−0.120, +0.039] | 0.92 | 0.96 |

Harrell C (mean over repeats): reference 0.646 / 0.673; B4 Cox 0.592 / 0.633; B0 ET 0.601 / 0.628; B1 rule 0.534 / 0.537.
Unfitted-score AUCs (`auc_raw`, grade 4): B0 ET 0.659, B0 ΔET 0.603, B1 rule 0.611, B1 continuous 0.626 — the
in-fold logistic map costs 0.02–0.06 AUC (pooling OOF scores from 5 different fold maps breaks ties and order across folds); still all
below the baseline.

## Nested hyperparameter grid (outer folds = C3 folds; inner 3-fold patient-grouped AUC on training patients)

| Arm | Grade 4 AUC | ΔAUC vs C3 ridge [95% CI] | All gliomas AUC | ΔAUC [95% CI] |
|---|---|---|---|---|
| C3 ridge (C by inner log-loss) | 0.698 | — | 0.720 | — |
| Ridge fixed C = 0.1 | 0.703 | +0.005 [−0.009, +0.019] | 0.728 | +0.008 [−0.005, +0.023] |
| Ridge, C ∈ {0.01…3} by inner AUC | 0.687 | −0.012 [−0.033, +0.008] | 0.724 | +0.004 [−0.003, +0.012] |
| Boosting fixed (C3) | 0.687 | −0.012 [−0.072, +0.048] | 0.718 | −0.002 [−0.052, +0.047] |
| Boosting, depth × lr × min_leaf grid | 0.690 | −0.009 [−0.065, +0.052] | 0.727 | +0.008 [−0.041, +0.059] |
| Nested over ridge + boosting (14) | 0.674 | −0.024 [−0.061, +0.011] | 0.729 | +0.009 [−0.021, +0.042] |

**Answer: unchanged.** Every tuned arm is within ±0.025 of the fixed baseline, all CIs include 0. Choices are unstable
(grade-4 ridge C: 0.01 in 11/25 folds, rest spread over 0.03–3; boosting: 8 different grid points chosen; nested family
picks ridge in 15/25 grade-4 folds) — `nested_choices.csv`. Boosting calibration worsens when tuned (slope 0.82 → 0.59
grade 4).

## LUMIERE (locked: trained once on all MU scans, applied to 132 scans / 61 patients; pooled IPCW AUC, patient bootstrap)

Reference = locked shared clinical + timing ridge (the C3 baseline's treatment block does not exist in LUMIERE).

| Model (trained on MU grade 4) | AUC [95% CI] | ΔAUC vs reference [95% CI] | slope | O/E |
|---|---|---|---|---|
| Clinical + timing, shared (reference) | 0.610 [0.497, 0.737] | — | 0.48 | 0.98 |
| Clinical only, shared | 0.610 [0.487, 0.737] | +0.000 [−0.049, +0.037] | 0.28 | 1.15 |
| Clinical + timing + volumes, shared | 0.615 [0.483, 0.741] | +0.005 [−0.063, +0.066] | 0.37 | 1.36 |
| B0 log ET volume | 0.620 [0.510, 0.708] | +0.011 [−0.155, +0.156] | 0.72 | 1.12 |
| B0 ΔET vs previous | 0.590 [0.472, 0.696] | −0.020 [−0.185, +0.138] | 0.25 | 0.90 |
| B1 rule (binary) | 0.559 [0.468, 0.641] | −0.051 [−0.209, +0.102] | 0.64 | 0.87 |
| B1 rule, RANO 2.0 window | 0.511 [0.434, 0.581] | −0.099 [−0.236, +0.043] | 0.21 | 0.88 |
| B1 continuous (vs nadir) | 0.583 [0.460, 0.699] | −0.027 [−0.213, +0.147] | 0.20 | 0.88 |
| B4 Hashim Cox | 0.644 [0.521, 0.755] | +0.034 [−0.067, +0.125] | 0.98 | 1.27 |

Trained on MU all gliomas: reference 0.605, B4 Cox 0.636 (Δ +0.031 [−0.057, +0.112], slope 0.97, O/E 1.29); B0/B1 AUCs
identical (monotone maps). LUMIERE caveats: volumes are DeepBraTumIA (MU: different segmenter; median grade-4 ET 0.61 vs
5.45 cc), so the 1 cc / 40 % thresholds and calibrated maps transfer imperfectly; ET history comes from all DeepBraTumIA
studies except pre-op (84 % of index scans have a prior vs 49 % in MU); no RT end date (nadir over all priors; RANO 2.0
window = rater's "< 3 months" flag); no component counts. Point estimates on locked single predictions (the external
experiment's fold-mean estimator is not used here).

## Reading

1. Imaging-only literature baselines are **weaker than the clinical + timing + treatment baseline** in MU: the volumetric
   RANO-style rule reaches 0.55 (ΔAUC −0.15 grade 4, CI excludes 0), prior-trend 0.55, persistence (ET volume) 0.64, the
   Hashim Cox 0.63 (Δ −0.07, CI includes 0). Adding the RANO 2.0 12-week exclusion or component counts makes the rule
   worse (0.51).
2. On LUMIERE every model is ~0.51–0.64 with wide CIs; the Hashim Cox is the best-calibrated (slope 0.98) and nominally
   highest (0.644), but no difference vs the reference is significant.
3. Hyperparameter tuning does not change the baseline (|Δ| ≤ 0.024, all CIs include 0).

![forest](../../outputs/results/analyses/baselines/forest.png)
