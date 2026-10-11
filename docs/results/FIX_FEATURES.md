# Feature-layer fixes (2026-10-11)

Scope: `prism/features/{tabular,measurements,radiomics}.py`, tests in `tests/test_features.py`. `treatment()` and the
as-of-scan `timing()` logic are unchanged. All numbers below were produced in a private output directory
(`PRISM_OUTPUTS=<scratchpad>/out-features`, a copy of `outputs/data` + `outputs/features` with `prism measurements`
re-run); shared `outputs/` was not touched. **`outputs/features/measurements.csv` must be regenerated
(`prism measurements`, ~75 s on 16 workers) before downstream experiments pick up fixes 3-4.**

## 1. MAJOR: LUMIERE "necrotic" contains the resection cavity -> harmonised necrosis volume

DeepBraTumIA (LUMIERE) has no cavity label; its necrotic/non-enhancing compartment includes the cavity. It was mapped
to MU NETC (which excludes the cavity, MU label 4).

| grade-4 median (cc) | MU | LUMIERE |
|---|---|---|
| NETC (MU label 1) | 0.00 (49% zero) | - |
| NETC + RC (MU labels 1+4) | 5.41 | - |
| DeepBraTumIA necrotic | - | 7.40 |
| ET | 5.45 | 0.61 |
| SNFH / edema | 42.85 | 19.11 |

Fix (shared MU<->LUMIERE table only; MU-only feature groups unchanged):
- new column `log_necrosis_cavity_cc` = log1p(MU NETC+RC) / log1p(LUMIERE necrotic);
- new column `log_core_cavity_cc` = log1p(MU ET+NETC+RC) / log1p(LUMIERE enhancing+necrotic) (available, not in `SHARED`);
- `SHARED["volumes"]` is now `["log_et_cc", "log_necrosis_cavity_cc", "log_snfh_cc"]`, so `external_lumiere.py` and
  `analyses/deep_features.py` use the harmonised definition without code changes. `log_netc_cc` stays in both tables
  (not comparable across cohorts); the pre-fix list is `SHARED_VOLUMES_UNHARMONISED` for sensitivity runs.

Locked MU->LUMIERE effect (point IPCW AUC(120 d), O/E, calibration slope; MU CV = 5x5 grouped CV, ridge):

| train | features | learner | pre-fix AUC | harmonised AUC | pre/post O/E | pre/post slope | MU CV pre -> post |
|---|---|---|---|---|---|---|---|
| grade 4 | volumes | ridge | 0.534 | 0.534 | 0.94 / 1.05 | 0.48 / 0.51 | 0.591 -> 0.599 |
| grade 4 | volumes | gbm | 0.554 | 0.533 | 1.03 / 1.10 | 0.34 / 0.21 | |
| grade 4 | clin+timing+volumes | ridge | 0.629 | 0.638 | 1.18 / 1.34 | 0.79 / 0.85 | 0.689 -> 0.699 |
| grade 4 | clin+timing+volumes | gbm | 0.717 | 0.679 | 1.19 / 1.22 | 1.21 / 1.04 | |
| all glioma | volumes | ridge | 0.616 | 0.563 | 1.38 / 1.31 | 0.97 / 0.56 | 0.608 -> 0.614 |
| all glioma | volumes | gbm | 0.585 | 0.572 | 1.24 / 1.35 | 0.45 / 0.31 | |
| all glioma | clin+timing+volumes | ridge | 0.640 | 0.619 | 1.75 / 1.74 | 0.43 / 0.37 | 0.694 -> 0.700 |
| all glioma | clin+timing+volumes | gbm | 0.692 | 0.682 | 1.65 / 1.60 | 0.96 / 0.91 | |

Honest reading: the harmonised definition is the correct one, but it does **not** improve transfer — locked AUC
falls in 6 of 8 cells, is unchanged in 1 and rises in 1 (largest drop: all-glioma volumes ridge 0.616 -> 0.563); internal MU CV rises slightly (+0.006 to
+0.010). The earlier, "better" all-glioma number was obtained with a mismatched feature. Point estimates on 132 scans /
61 patients; no CIs computed here (the external experiment re-run gives them).
Source: `<scratchpad>/out-features/fix_features_locked.csv` (script `<scratchpad>/fix_features_locked.py`).

## 2. MAJOR: different segmenters -> within-cohort scaling sensitivity

ET (5.45 vs 0.61 cc) and SNFH (42.9 vs 19.1 cc) medians differ by 2-9x between the MU masks and DeepBraTumIA, so a
locked model sees LUMIERE volumes far outside its training range (slopes 0.2-0.85 above). New exported function
`prism.features.tabular.within_cohort_normalise(X, cols=None, method="rank"|"zscore")` re-expresses the volume columns
relative to their own cohort (mid-rank percentile, ties shared; or cohort z-score). Call it separately on the MU and
LUMIERE tables before fitting/applying. It is transductive for LUMIERE (uses the unlabelled feature distribution, never
labels) and removes level differences by construction, so it is a sensitivity analysis, not the primary result.

Pipeline: `prism external` adds the arms `locked+cohort_norm_rank` and `locked+cohort_norm_zscore` for every feature
set with volumes (`outputs/results/external_lumiere/results.csv`; columns `auc_ipcw_pooled`, `oe_ratio_pooled`,
`cal_slope_pooled`; per-fold AUC with a paired bootstrap ΔAUC vs `locked` in `d_auc_fold_mean_*`).

Locked effect with harmonised volumes, pooled IPCW AUC(120 d) on all 132 LUMIERE scans (none -> rank / zscore), from
that stage (run 2026-10-11 on the label-fixed cohort, with the 7 empty LUMIERE segmentations as missing, section 5):

| train | features | learner | none | rank | zscore | slope none -> rank | O/E none -> rank | per-fold ΔAUC rank [95% CI] |
|---|---|---|---|---|---|---|---|---|
| grade 4 | volumes | ridge | 0.545 | 0.579 | 0.564 | 0.43 -> 0.63 | 1.00 -> 0.86 | +0.041 [−0.000, +0.091] |
| grade 4 | volumes | gbm | 0.529 | 0.598 | 0.590 | 0.21 -> 0.48 | 1.00 -> 0.86 | +0.061 [−0.037, +0.162] |
| grade 4 | clin+timing+volumes | ridge | 0.608 | 0.624 | 0.619 | 0.38 -> 0.44 | 1.33 -> 1.12 | +0.010 [−0.015, +0.046] |
| grade 4 | clin+timing+volumes | gbm | 0.620 | 0.659 | 0.637 | 0.73 -> 0.90 | 0.99 -> 0.87 | +0.047 [−0.002, +0.110] |
| all glioma | volumes | ridge | 0.552 | 0.584 | 0.567 | 0.52 -> 0.70 | 1.12 -> 0.97 | +0.044 [+0.004, +0.084] |
| all glioma | volumes | gbm | 0.573 | 0.580 | 0.546 | 0.31 -> 0.45 | 1.18 -> 0.92 | +0.013 [−0.060, +0.103] |
| all glioma | clin+timing+volumes | ridge | 0.599 | 0.623 | 0.612 | 0.38 -> 0.78 | 1.30 -> 1.04 | +0.029 [−0.001, +0.061] |
| all glioma | clin+timing+volumes | gbm | 0.619 | 0.652 | 0.641 | 0.66 -> 0.98 | 1.04 -> 0.86 | +0.050 [+0.004, +0.116] |

Rank normalisation raises the pooled locked AUC in 8/8 cells (+0.007 to +0.069) and moves the calibration slope towards
1 in 8/8; 2 of 8 per-fold ΔAUC CIs exclude 0. This is consistent with segmenter scale being part of the transfer gap,
but the gains are small and volume-only models stay weak (<= 0.60). The table first written here (development run,
before the label fixes and with empty segmentations counted as 0 cc) had the same direction (rank better in 8/8) with
different levels (e.g. grade 4 clin+timing+volumes gbm 0.679 -> 0.697); the numbers above replace it.

## 3. MINOR: delta features

- `d_t1c_et_rel` is undefined (< 10 ET voxels now or at the prior) for 31 of the 153 cohort scans with a prior (308-scan
  cohort after the label fixes; 32 of 157 in the earlier 314-scan cohort); it was zero-filled indistinguishably from
  "no change". Added `d_t1c_et_rel_missing` and `d_flair_snfh_rel_missing` (has_prior and value missing; 31 / 0 cohort
  scans) to the `delta` group; values are still 0-filled.
- `vol_pd_flag` fired from a ~0 cc ET nadir (any >= 1 cc enhancement is ">= 40%" of 0). It now requires a measurable
  nadir `>= PD_MIN_NADIR_CC = 0.1 cc`; growth >= 1 cc from a smaller nadir is the new column `et_new_from_zero_nadir`
  (also in the `delta` group). Cohort scans (308): `vol_pd_flag` 72 -> 57, `et_new_from_zero_nadir` 15 (all 591
  timepoints: 205 -> 175, 30). The delta group has 25 columns (was 22). Column names used downstream are unchanged.
  `load_measurements` raises if `measurements.csv` predates this fix (no `et_new_from_zero_nadir`) instead of
  zero-filling the column.

## 4. MINOR: normal-brain reference margin

Was `binary_dilation(lesion|cavity, iterations=10)` with the default cross structure = city-block (L1) distance <= 10
voxels, i.e. only ~5.8 mm along 3D diagonals. Now `reference_mask()`: brain voxels with Euclidean distance (header
spacing) > 10 mm from lesion or cavity. Effect on intensity ratios (old vs new, 314 eligible scans):

| feature | n | Pearson | Spearman | median old -> new | median / max abs. rel. change |
|---|---|---|---|---|---|
| t1c_et_rel | 274 | 1.0000 | 0.9999 | 1.4098 -> 1.4097 | 0.10% / 0.75% |
| t1c_et_p90_rel | 274 | 1.0000 | 0.9999 | 1.9258 -> 1.9253 | 0.10% / 0.75% |
| t1c_netc_rel | 126 | 1.0000 | 0.9998 | 0.9055 -> 0.9065 | 0.13% / 0.75% |
| flair_snfh_rel | 313 | 0.9999 | 0.9998 | 1.4264 -> 1.4244 | 0.08% / 0.61% |
| flair_netc_rel | 126 | 1.0000 | 0.9999 | 1.4777 -> 1.4784 | 0.09% / 0.44% |
| d_t1c_et_rel | 125 | 1.0000 | 0.9999 | 0.0467 -> 0.0493 | 0.73% / 49% (near-zero denominators) |

Conclusion: negligible; the reference is a median over a large region and robust to the margin shape. No other
measurement column changed except `vol_pd_flag` (fix 3).

## 5. LUMIERE missing volumes

- 11 LUMIERE studies have an all-empty DeepBraTumIA segmentation (no necrosis/cavity, enhancement or oedema), 7 of them
  index scans (Patient-023 weeks 24 and 39, Patient-030 week 17, Patient-043 weeks 18-53). In a post-operative
  glioblastoma that is a segmentation failure, not "no tumour", so `prism lumiere` now writes NaN volumes for them
  (was 0 cc). With the 7 index scans that have no segmentation at all, 14 of 132 index scans have no volumes. Effect
  on the locked model: pooled AUC of volume models −0.002 to −0.018; rows without volumes are unchanged.
- Missing values are imputed inside the fitted pipeline (`external_lumiere.PRE`), so a locked MU model fills LUMIERE
  gaps with MU training medians. That is the correct locked-model behaviour (no LUMIERE statistics enter the model),
  but MU medians are on the MU segmenter's scale, and MU has no missing volumes, so no missingness indicator exists
  for them. Adapted arms (`finetune_pooled`, `lumiere_only`) impute from their own training rows.

## 6. Documented limitations (no code change)

- **ICC stability filter scope** (`c3_radiomics.py`): the eroded-ROI pass covers T1c and FLAIR texture + first-order
  only (1116 of 2316 radiomics columns). T1/T2 texture (1116) and shape (84) features are never ICC-screened and pass
  the "icc" stability option unfiltered.
- **Discretisation**: `binCount: 32` per ROI rather than IBSI-recommended fixed bin width; grey-level width then
  depends on each ROI's intensity range, mixing contrast with range. A fixed-width sensitivity was not run.
- The 5 mm peri-cavity rim in `radiomics.py` uses a 5-iteration city-block dilation (same issue as fix 4; not changed,
  as it would require re-extracting radiomics).
- Volume differences between segmenters (fix 2) are only partly addressed by rank normalisation; no
  re-segmentation of LUMIERE with the MU pipeline was attempted.

Tests: `uv run --frozen --no-sync python -m unittest tests.test_features` (6 tests: harmonised mapping both cohorts,
normalisation, nadir threshold, past-only deltas, missing flags, Euclidean margin).
