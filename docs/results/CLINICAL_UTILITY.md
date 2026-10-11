# Clinical usefulness: calibration, decision curves, added value, sample size (2026-10-11, final)

**Status: final numbers.** Every number below comes from the final full re-run: `outputs/results/analyses/utility/`
(2026-10-11 07:40, HEAD `cc2e3a3`; `run_info.json`: per-repeat OOF for every MU model including the deep arm, 1000 bootstrap
resamples, LUMIERE from the final `external_lumiere/locked_predictions.csv`). The provisional version of this file used a
private C3 run, repeat-averaged deep predictions and pre-fix LUMIERE predictions; the MU baseline and radiomics rows are
unchanged, the deep and LUMIERE rows changed.

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

Sources: `calibration.csv`, `net_benefit.csv`, `added_value.csv`.

| Model | AUC (IPCW) | O/E (weighted) | CITL [95% CI] | Slope [95% CI] | ICI |
|---|---|---|---|---|---|
| Baseline ridge | 0.698 | 0.96 | −0.09 [−0.42, 0.28] | 0.89 [0.50, 1.43] | 0.032 |
| Baseline boosting | 0.687 | 0.94 | −0.12 [−0.47, 0.23] | 0.82 [0.44, 1.31] | 0.039 |
| Baseline + radiomics (nested) | 0.672 | 0.94 | −0.13 [−0.48, 0.25] | **0.50 [0.27, 0.86]** | 0.070 |
| Baseline + deep (nested D1) | 0.704 | 0.95 | −0.14 [−0.51, 0.30] | **0.49 [0.24, 0.87]** | 0.096 |

| Net benefit (IPCW) | 10% | 20% | 30% |
|---|---|---|---|
| Treat all | 0.369 | 0.291 | 0.189 |
| Baseline ridge | 0.372 | 0.300 | 0.232 |
| Δ, radiomics (nested) vs baseline | −0.001 [−0.006, 0.004] | +0.002 [−0.009, 0.012] | −0.014 [−0.031, 0.003] |
| Δ, boosting vs baseline | −0.002 [−0.007, 0.001] | −0.007 [−0.021, 0.006] | −0.011 [−0.039, 0.013] |
| Δ, deep (nested D1) vs baseline | −0.004 [−0.014, 0.005] | +0.006 [−0.012, 0.024] | +0.005 [−0.023, 0.030] |

Added value vs the baseline ridge (continuous NRI(>0), events / non-events, IDI):
- baseline + radiomics (nested): NRI +0.20 [−0.02, 0.42] (+0.22 events, −0.02 non-events); IDI +0.009 [−0.019, 0.035]
- baseline + deep (nested D1): NRI +0.52 [0.30, 0.75] (+0.37 events, +0.15 non-events); IDI +0.049 [0.002, 0.097]
- baseline boosting: NRI +0.06 [−0.17, 0.30]; IDI +0.004 [−0.032, 0.041]

All gliomas:
- AUC: baseline 0.720, radiomics (nested) 0.732, deep (nested D1) 0.725.
- Calibration slope: radiomics 0.77 [0.53, 1.09], deep 0.70 [0.47, 1.00] (baseline 0.88 [0.53, 1.35]).
- Δ net benefit, radiomics: +0.009 [0.001, 0.018] at 10%, +0.011 [−0.001, 0.025] at 20%, −0.001 [−0.020, 0.018] at 30%.
- Δ net benefit, deep: +0.004 [−0.002, 0.010] / +0.011 [−0.007, 0.029] / −0.000 [−0.025, 0.023].
- NRI radiomics +0.31 [0.11, 0.49], IDI +0.029 [−0.000, 0.054]; NRI deep +0.38 [0.17, 0.60], IDI +0.029 [−0.004, 0.062].

## LUMIERE (grade-4-trained, clinical + timing + volumes, locked; 132 scans / 61 patients)

| Model | AUC (IPCW, pooled) | O/E (weighted) | CITL [95% CI] | Slope [95% CI] | ICI |
|---|---|---|---|---|---|
| Locked boosting | 0.620 | 1.02 | 0.03 [−0.40, 0.49] | 0.73 [−0.01, 1.51] | 0.035 |
| Recalibrated boosting (in-fold) | — | 0.97 | −0.06 [−0.52, 0.45] | 0.24 [−0.62, 1.22] | 0.078 |
| Locked ridge | 0.608 | **1.37** (under-predicts) | **0.56 [0.06, 1.14]** | 0.38 [−0.12, 0.87] | 0.122 |
| Recalibrated ridge (in-fold) | — | 0.93 | −0.12 [−0.58, 0.43] | −0.15 [−1.14, 0.83] | 0.092 |

| Net benefit | 10% | 20% | 30% |
|---|---|---|---|
| Treat all | 0.308 | 0.222 | 0.111 |
| Locked boosting | 0.308 | 0.218 | 0.130 |
| Locked ridge | 0.279 | 0.161 | 0.095 |
| Δ recalibrated vs locked, boosting | +0.000 | −0.010 [−0.019, −0.003] | −0.049 [−0.099, −0.005] |
| Δ recalibrated vs locked, ridge | +0.029 [−0.010, 0.082] | +0.062 [−0.009, 0.138] | −0.022 [−0.111, 0.071] |

- The locked boosting model is calibrated in the large (O/E 1.02) but has no net benefit over treat-all up to 20% and only
  +0.019 at 30%. The locked ridge model under-predicts (CITL CI excludes 0) and is below treat-all at every threshold shown.
- In-fold recalibration on 61 patients does not help: it lowers net benefit for boosting (CIs exclude 0 at 20–30%) and the
  recalibrated slopes are unstable (CIs span 0).

## Sample size (Riley 2020), grade 4
- **Cohort:** 210 verified scans (126 patients), 93 events, φ = 0.443. R²cs = 0.119, derived from AUC 0.698; 15% of the maximum R² gives 0.112.

| Candidate parameters | Observed EPP | Criteria: risk / MAPE / shrinkage / optimism | Required n (events) |
|---|---|---|---|
| Baseline, 23 raw predictors | 4.0 | 380 / 1201 / 1625 / 567 | 1625 (720) |
| Baseline, 31 design columns | 3.0 | 380 / 1583 / 2190 / 764 | 2190 (970) |
| + 10 radiomics | 2.3 | 380 / 2051 / 2896 / 1010 | 2896 (1283) |
| + full radiomics pool (2477) | 0.04 | 380 / 91,623 / 174,942 / 61,019 | 174,942 (77,475) |

Source: `sample_size.csv` (`from_auc` rows). All gliomas: 256 verified scans, 100 events, baseline (31 columns) requires 1826 scans
(714 events). The requirements are in scans and assume independent scans, so with 126 patients the shortfall is understated.

## Findings
1. **Neither radiomics nor deep features add clinical value.**
   - Grade 4: Δ net benefit is within ±0.015 at every reported threshold for both, and every CI crosses 0.
   - Both nested image models are clearly overfit (slope 0.50 radiomics, 0.49 deep).
   - Their positive continuous NRI (and, for deep, an IDI whose CI just excludes 0: +0.049 [0.002, 0.097]) come mostly
     from upward risk shifts in events. Continuous NRI and IDI reward miscalibrated or overfit models (Hilden & Gerds 2014;
     Pepe 2015), so we report them only alongside ΔAUC and Δ net benefit, which are null (deep ΔAUC +0.006 [−0.058, +0.071],
     `DEEP_FEATURES.md`).
2. **Baselines are well calibrated in the large** (O/E 0.94–0.96, CITL CIs include 0) and only mildly over-fitted (slope 0.82–0.89).
3. **Clinical usefulness is modest.** The models beat treat-all only above ~20% threshold, because 120-d progression is common (φ ≈ 0.44). At 30% the baseline gains +0.043 net benefit over treat-all, about 4 extra true positives per 100 scans at equal false positives. On LUMIERE the locked model adds essentially nothing over treat-all (≤ +0.019).
4. **The study is underpowered by Riley's criteria even for the baseline.** It has 3–4 events per parameter, against the ~31 implied by the shrinkage criterion (970 events / 31 parameters); our n is about one tenth of the required 2190. Radiomics models are short by one to three orders of magnitude, which explains the null and unstable radiomics results.
