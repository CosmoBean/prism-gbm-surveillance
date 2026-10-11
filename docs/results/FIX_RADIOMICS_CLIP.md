# Radiomics outlier clipping (2026-10-11)

Code: `prism/experiments/c3_radiomics.py`, class `QuantileClip`, now the first step of `selector()`. As of this writing the
change is uncommitted on `manuscript-week`. Before = the final-run C3 outputs (code `cc2e3a3`, documented in `8c780df`), copied to
`<scratchpad>/c3_before_clip/{grade4,all_glioma}/`. After = `outputs/results/c3/{grade4,all_glioma}/` (2026-10-11 18:21–18:23).

## The bug

- Some legacy (PRISM report) PyRadiomics features hold the value **1e6**. This looks like PyRadiomics' sentinel for NGTDM
  Coarseness on a flat ROI.
- It appears in 3 of the 2446 legacy columns: FLAIR LoG σ = 1, 2 and 3 mm `ngtdm_Coarseness`. The other values in these
  columns have a median of 1e-4 to 8e-4.
- 4 scans are affected: 0156_T2 (3 columns), 0271_T6 (3), 0242_T6 (1) and 0268_T3 (1). 0156_T2 and 0268_T3 are grade 4.
  The corrected (v2) radiomics never have the value.
- In C3, `selector()` imputed and then applied `StandardScaler` → selection/PCA. A single 1e6 inflates that column's
  training SD by orders of magnitude. PCA and the stacked radiomics score then depend on these scans.
- `docs/results/SHAP.md` (pre-fix version) found that the stacked radiomics score had inner-OOF training values of −10⁴
  to −4.6×10⁶ in 20/25 grade-4 fits and 25/25 all-glioma fits. When an affected scan was held out, its prediction
  saturated (|φ| ≈ 10⁵).

## The fix

`QuantileClip(q=0.01)` is fitted in each training fold (and inner fold). It clips every radiomics or deep feature to that
fold's 1st and 99th order statistics (`np.nanquantile`, `method="higher"` / `"lower"`). It then passes values to imputation,
`VarianceThreshold`, `StandardScaler` and selection. NaNs are left for the imputer. Test scans are clipped with the
training bounds.

**Why it is defensible**
- **No leakage.** The bounds are learned from training scans only, like the scaler.
- **Standard practice.** It is ordinary 1%/99% winsorising, a common preprocessing step for heavy-tailed radiomics. It
  removes a pipeline artefact rather than tuning to the outcome. It does not look at labels, and it was not chosen by its
  effect on AUC.
- **Same rule for all configurations.** All 70 radiomics configurations get the same rule. The deep-feature arms use
  `c3.selector`, so they get it too. The ridge baseline is unaffected: its AUC is identical before and after.
- **Small effect.** It changes no conclusion. The largest change in any single configuration's AUC is 0.020.

## Before → after

Nested selection over 70 configurations (`results.csv`, row `NESTED`); paired ΔAUC vs the ridge baseline, 1000-draw
patient-cluster bootstrap:

| Population | Nested AUC before → after | ΔAUC before → after | Cal. slope | p(Δ ≤ 0) |
|---|---|---|---|---|
| Grade 4 (primary) | 0.672 [0.597, 0.743] → **0.666 [0.586, 0.739]** | −0.026 [−0.073, +0.017] → **−0.032 [−0.084, +0.017]** | 0.50 → 0.60 | 0.896 → 0.895 |
| All gliomas | 0.732 [0.664, 0.794] → **0.747 [0.678, 0.811]** | +0.012 [−0.029, +0.050] → **+0.028 [−0.017, +0.071]** | 0.77 → 0.85 | 0.285 → 0.118 |

The baseline is unchanged: ridge 0.698 / 0.720, boosting 0.687 / 0.718.

**Single configurations (70 per population).**
- Grade 4: CI above 0 in 0/70, both before and after. CI below 0 falls from 12/70 to 8/70.
- All gliomas: CI above 0 goes from 0/70 to **1/70**. The configuration is `legacy|none|pca10|stack|ridge`: 0.754, Δ
  +0.035 [+0.002, +0.068], p(Δ ≤ 0) = 0.021.
  - This count is uncorrected for multiple testing. At a one-sided 2.5% level, about 1.75 of 70 null configurations would
    exclude 0 by chance, so one is consistent with no effect.
  - The honest nested estimate, which accounts for the selection, still has a CI spanning 0.

**Most-affected configurations** (stacked legacy PCA, the modal nested choice, and the largest AUC changes):

| Configuration | Population | AUC before → after | ΔAUC [95% CI] after | Cal. slope before → after |
|---|---|---|---|---|
| legacy, pca10, stack | grade 4 | 0.708 → 0.721 | +0.023 [−0.013, +0.057] | 0.65 → 0.92 |
| legacy, pca10, stack | all gliomas | 0.749 → 0.754 | +0.035 [+0.002, +0.068] | 0.94 → 0.96 |
| v2_all4, l1, concat | grade 4 | 0.655 → 0.675 (+0.020, the largest) | −0.023 [−0.094, +0.041] | 0.28 → 0.32 |
| v2_all4, icc, l1, concat | all gliomas | 0.692 → 0.709 (+0.017) | −0.010 [−0.074, +0.048] | 0.38 → 0.43 |

The best post-hoc configuration is now `legacy|none|pca10|stack` in both populations: 0.721 / 0.754, Δ +0.023 / +0.035.
Before the fix it was `legacy|none|pca10|concat`: 0.717 / 0.751, Δ +0.019 / +0.031. Nested choices now pick legacy in 18/25
(grade 4) and 25/25 (all gliomas) outer folds, against 17/25 and 23/25 before. `legacy|none|pca10|stack` is chosen in 9/25
and 14/25 folds, against 7/25 and 11/25.

**Downstream.** Every stage that uses `c3.selector` or the C3 OOF predictions was re-run after the fix: C3, deep, step 10
(baselines, schedule, sensitivity, utility, tables, split-variance replot), SHAP and feature conflicts. The
updated numbers are in [FINAL_RESULTS.md](FINAL_RESULTS.md) and the linked documents.

**Not covered by the fix** (raw legacy radiomics still enter without clipping):
- C2's radiomics group (`c2_feature_search.py`: imputation → `StandardScaler` → top-K).
- C1's `radiomics_clinical` feature set.
- `feature_conflicts.py`'s B+radiomics / F+radiomics rows.

These pipelines are still exposed to the 1e6 values. Two runs use `c3.fit_predict` with radiomics but were not re-run,
so they predate the fix:
- the head-to-head on the PRISM report split (`c3/prism_report_split/head_to_head.csv`, radiomics rows);
- the split-variance per-split table (`baseline_rad`; only the figure was re-plotted).
