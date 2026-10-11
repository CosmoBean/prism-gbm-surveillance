# Clinical usefulness: calibration, decision curves, added value, sample size (2026-10-11, PROVISIONAL)

**Status: provisional.** The numbers below come from a private development run, not from the final shared outputs.
- C3 was re-run at HEAD `478e280` with 8 workers on the post-fix cohort (grade 4: 249 scans / 126 patients).
- The deep arm uses the provisional `analyses/deep/*/oof.csv`. That file holds repeat-averaged predictions only, because no `oof_repeats` file exists for it yet.
- LUMIERE uses the existing `external_lumiere/locked_predictions.csv`.

To regenerate the numbers on the final outputs, run:

```bash
uv run --frozen --no-sync python -m prism.analyses.utility            # ~10 min, 1 CPU, 1000 bootstrap resamples
# -> outputs/results/analyses/utility/{calibration,calibration_curves,net_benefit,added_value,sample_size}.csv,
#    calibration_dca.png, run_info.json
```

Code: `prism/analyses/utility.py`.

## Methods
- **Censoring.** Every statistic is computed on the verified scans (label known at 120 d). Each scan is weighted by 1/G(min(t, 120)−), where G is the Kaplan–Meier censoring survival floored at 0.1. These are the same weights as the calibration slope in `metrics.point_metrics` and the `ipcw` formulation. Rates are normalised by the weight sum. Unweighted verified-subset net benefit is kept in `net_benefit.csv` as a sensitivity analysis.
- **Repeated CV.** Each statistic is computed on each repeat's pooled out-of-fold predictions and then averaged over the 5 repeats, the same way as the headline AUC.
- **CIs.** 95% CIs come from a patient-cluster bootstrap with 1000 resamples. G is re-estimated in each resample, and every model is scored on the same resample, so differences are paired.
- **Calibration** (Van Calster 2019):
  - calibration-in-the-large: intercept with a logit offset
  - weighted O/E, plus the Kaplan–Meier O/E from `metrics.py`
  - calibration slope
  - a flexible curve: weighted logistic regression on a restricted cubic spline of logit(p) with 3 knots
  - ICI
- **Decision curves** (Vickers & Elkin 2006): net benefit at thresholds 5–50%, and Δ net benefit vs the ridge baseline.
- **Added value** (Pencina 2008/2011): continuous NRI(>0) and IDI.
- **Sample size** (Riley 2020): the four binary-outcome criteria from pmsampsize, re-implemented in Python. Checked against the pmsampsize example (P = 24, φ = 0.174, R² = 0.288 → 623 / 662 / 221, matching). The Cox–Snell R² is derived from the baseline AUC by the Riley–Van Calster–Collins 2021 simulation; 15% of the maximum R² is shown as an alternative.

## MU grade 4 (5×5 CV)

| Model | AUC (IPCW) | O/E (weighted) | CITL [95% CI] | Slope [95% CI] | ICI |
|---|---|---|---|---|---|
| Baseline ridge | 0.698 | 0.96 | −0.09 [−0.42, 0.28] | 0.89 [0.50, 1.44] | 0.032 |
| Baseline boosting | 0.687 | 0.94 | −0.12 [−0.47, 0.23] | 0.82 [0.44, 1.31] | 0.039 |
| Baseline + radiomics (nested) | 0.672 | 0.94 | −0.13 [−0.48, 0.25] | **0.51 [0.27, 0.86]** | 0.070 |

| Net benefit (IPCW) | 10% | 20% | 30% |
|---|---|---|---|
| Treat all | 0.369 | 0.291 | 0.189 |
| Baseline ridge | 0.372 | 0.300 | 0.232 |
| Δ, radiomics (nested) vs baseline | −0.001 [−0.006, 0.004] | +0.002 [−0.009, 0.012] | −0.014 [−0.031, 0.003] |
| Δ, boosting vs baseline | −0.002 [−0.007, 0.001] | −0.007 [−0.021, 0.006] | −0.011 [−0.039, 0.013] |

Added value of baseline + radiomics vs baseline:
- continuous NRI +0.20 [−0.02, 0.42], made up of +0.22 in events and −0.02 in non-events
- IDI +0.009 [−0.019, 0.035]

All glioma:
- AUC: baseline 0.720 vs radiomics (nested) 0.732.
- Radiomics calibration slope: 0.77 [0.53, 1.09].
- Δ net benefit: +0.009 [0.001, 0.018] at 10%, +0.011 [−0.001, 0.025] at 20%, −0.001 at 30%.
- NRI +0.31 [0.11, 0.49]; IDI +0.029 [−0.000, 0.054].

Deep (nested D1, repeat-averaged predictions, provisional):
- grade 4: Δ net benefit +0.004 / −0.000 / −0.008 at 10/20/30%; NRI +0.40 [0.08, 0.70]; IDI +0.015 [−0.012, 0.044].
- all glioma: Δ net benefit −0.029 [−0.058, −0.001] at 30%.

## LUMIERE (grade-4-trained, clinical + timing + volumes)
- **Locked boosting:**
  - AUC 0.714
  - O/E 1.21 (under-predicts)
  - CITL 0.33 [−0.12, 0.88]
  - slope 1.19 [0.51, 2.09]
- **Recalibrated in-fold boosting:**
  - O/E 0.97
  - CITL −0.07
  - slope 0.70 [0.21, 1.45]
- **Net benefit of the locked boosting model vs treat-all:**

  | Threshold | Locked | Treat all |
  |---|---|---|
  | 10% | 0.305 | 0.308 |
  | 20% | 0.227 | 0.222 |
  | 30% | 0.147 | 0.111 |

- **Recalibration does not add net benefit:** Δ −0.006 / −0.015 / −0.017 at 10/20/30%.

## Sample size (Riley 2020), grade 4
- **Cohort:** 210 verified scans (126 patients), 93 events, φ = 0.443. R²cs = 0.119, derived from AUC 0.698; 15% of the maximum R² gives 0.112.

| Candidate parameters | Observed EPP | Criteria: risk / MAPE / shrinkage / optimism | Required n (events) |
|---|---|---|---|
| Baseline, 23 raw predictors | 4.0 | 380 / 1201 / 1625 / 567 | 1625 (720) |
| Baseline, 31 design columns | 3.0 | 380 / 1583 / 2190 / 764 | 2190 (970) |
| + 10 radiomics | 2.3 | — / — / 2896 / — | 2896 (1283) |
| + full radiomics pool (2477) | 0.04 | — / — / 174,942 / — | 174,942 |

The requirements are in scans and assume independent scans, so with 126 patients the shortfall is understated.

## Findings
1. **Radiomics adds no clinical value.**
   - Grade 4: Δ net benefit is within ±0.015 at every reported threshold, and every CI crosses 0.
   - The nested radiomics model is clearly overfit (slope 0.51).
   - Its positive continuous NRI comes from upward risk shifts in events. Continuous NRI is known to reward miscalibrated or overfit models (Hilden & Gerds 2014; Pepe 2015), so we report it only alongside Δ net benefit and IDI, which are both null.
2. **Baselines are well calibrated in the large** (O/E 0.94–0.96, CITL CIs include 0) and only mildly over-fitted (slope 0.82–0.89).
3. **Clinical usefulness is modest.** The models beat treat-all only above ~20% threshold, because 120-d progression is common (φ ≈ 0.44). At 30% the baseline gains +0.043 net benefit over treat-all, about 4 extra true positives per 100 scans at equal false positives.
4. **The study is underpowered by Riley's criteria even for the baseline.** It has 3–4 events per parameter, against the ~31 implied by the shrinkage criterion (970 events / 31 parameters); our n is about one tenth of the required 2190. Radiomics models are short by one to three orders of magnitude, which explains the null and unstable radiomics results.
