# Sensitivity of the primary comparison to label, horizon and population (2026-10-11)

Code: `prism/analyses/sensitivity.py` (`python -m prism.analyses.sensitivity --workers 48`). It reuses the C3 pipeline
(`c3_radiomics.fit_predict`, `inner_auc`, `RAD_CONFIGS`) unchanged.
Output: `outputs/results/analyses/sensitivity/{summary.csv, nested_choices.csv, oof_repeats.csv.gz, forest.png}`.
**Final numbers:** the table below was checked against the final full re-run (`outputs/results/analyses/sensitivity/summary.csv`,
2026-10-11 07:38, HEAD `cc2e3a3`); every row is identical to the earlier private run.

**Comparison.** The primary comparison is the grade-4 ridge baseline (clinical + timing + treatment) vs baseline +
radiomics, with the radiomics configuration chosen by **nested** selection over all 70 C3 configurations (inner 3-fold
patient-grouped CV in every outer fold). Nested selection is the pre-specified primary analysis (plan §3.3), and no
single radiomics configuration was fixed in advance, so using one would mean choosing it after seeing results. It is
also cheap: 8 sensitivities × 25 outer folds take 112 CPU-min (15 min on 8 CPUs; about 3 min on 48 CPUs).
**Estimator.** The headline is the mean over the 5 repeats of the per-repeat pooled-OOF IPCW AUC(H). ΔAUC is the point
estimate with a paired patient-cluster bootstrap CI (1000 resamples), computed with `metrics.evaluate_repeated`.
**Folds.** Every sensitivity uses `outputs/data/folds.csv`, which is stratified on the *primary* 120-d status. Subsets
keep each patient's fold. The other labels are not re-stratified, so their fold balance is slightly worse. This keeps
the patient partitions identical across rows.
**Outcome.** The sensitivity label replaces `label_H`, and its matching time-to-event pair is used for IPCW (asserted
consistent):
- composite: `event_composite` / `time_to_event_composite`;
- alternative date: time from `progression_day_alt`. The 5 grade-4 scans whose alternative date is on or before the scan
  are dropped;
- imaging-only follow-up: non-progressors are censored at `follow_up_imaging_days`;
- post-RT: scans with `early_post_rt == 1` (0–84 d after RT end) are removed. Scans with an unknown RT end are kept.
- excluding 0145: patient 0145 (2 grade-4 scans, both verified negative at 120 d) is removed. Its two progression-date
  fields disagree (day 495 vs 66) and its death date is ignored as contradicted by later records (FIX_LABELS.md 1b, 3).
  Added after the first run; its row and the primary row were re-run together (private outputs, 2026-10-11) and the
  primary row reproduced exactly.

| Sensitivity | Scans / pts | Events / censored | Baseline AUC [95% CI] | + radiomics (nested) | ΔAUC [95% CI] |
|---|---|---|---|---|---|
| **Primary: grade 4, 120 d** | 249 / 126 | 93 / 39 | 0.698 [0.615, 0.774] | 0.672 | −0.026 [−0.073, +0.017] |
| Horizon 90 d | 249 / 126 | 62 / 35 | 0.663 [0.577, 0.739] | 0.659 | −0.004 [−0.059, +0.050] |
| Horizon 180 d | 249 / 126 | 131 / 43 | 0.667 [0.573, 0.752] | 0.642 | −0.026 [−0.085, +0.032] |
| Composite (progression or death) | 249 / 126 | 107 / 25 | 0.642 [0.566, 0.713] | 0.624 | −0.017 [−0.081, +0.053] |
| Alternative progression date | 244 / 124 | 92 / 39 | 0.670 [0.578, 0.757] | 0.646 | −0.024 [−0.070, +0.021] |
| Imaging-only follow-up | 249 / 126 | 93 / 43 | 0.685 [0.600, 0.761] | 0.651 | −0.034 [−0.085, +0.015] |
| All gliomas | 308 / 155 | 100 / 52 | 0.720 [0.638, 0.792] | 0.732 | +0.012 [−0.029, +0.050] |
| Excluding 12-wk post-RT scans | 151 / 90 | 46 / 39 | 0.725 [0.602, 0.834] | 0.725 | +0.001 [−0.054, +0.059] |
| Excluding patient 0145 (conflicting dates) | 247 / 125 | 93 / 39 | 0.691 [0.602, 0.776] | 0.679 | −0.011 [−0.064, +0.038] |

![forest plot](../../outputs/results/analyses/sensitivity/forest.png)

## Findings

1. **"Radiomics adds no measurable value" is robust.** None of the 9 ΔAUC CIs excludes 0. The point estimates range
   from −0.034 to +0.012, and 7 of 9 are negative. Dropping patient 0145 (conflicting dates) moves the baseline by
   −0.007 and ΔAUC from −0.026 to −0.011. The largest upper bound is +0.059, after excluding post-RT scans,
   where n = 151. Δ IPCW Brier is ≥ −0.001 in every row (`summary.csv`), so radiomics never improves it either.
2. **The baseline is less robust than the null result.** Its AUC ranges from 0.64 (composite) to 0.73 (post-RT
   excluded). The composite outcome is the hardest: death without documented progression is less predictable from
   these features. Removing the post-RT window does not lower the baseline (0.725), so timing features are not only
   picking up pseudoprogression-window scans. The CI is wide at 46 events.
3. **Nested radiomics models are overconfident.** Their calibration slopes are 0.39–0.53 in grade 4 (0.60 without
   patient 0145; baseline 0.52–0.90) and 0.77 in all gliomas. Legacy radiomics is chosen in 10–23 of 25 outer folds per row
   (`nested_choices.csv`).
4. **The primary row is lower than the FIX_EVALUATION validation number.** Primary ΔAUC is −0.026 here, vs −0.002 in
   the FIX_EVALUATION validation run, because the final cohort is the post-label-fix one (249 scans, death censored), not
   the 253-scan inputs. Checked: the final `outputs/results/c3/grade4/results.csv` NESTED row matches the primary row
   exactly (0.672 [0.597, 0.743]; ΔAUC −0.026 [−0.073, +0.017]; baseline 0.698 [0.615, 0.774]), and so does the all-glioma
   row (`c3/all_glioma/results.csv`: 0.732, ΔAUC +0.012 [−0.029, +0.050]).

Open: one lbfgs ConvergenceWarning occurred (h180, repeat 0, fold 0, inner ridge fit).
