# Phase-of-care ladder: does imaging add value once phase of care is known?

Code: `prism/analyses/phase_ladder.py` (`python -m prism phaseladder`; `uv run prism ...` needs the project installed in the venv, see scripts/common.sh).
Outputs: `outputs/results/analyses/phase_ladder/`.

## 0. Why

The headline baseline is clinical + timing + treatment, fitted with ridge. Its AUC is 0.698 in grade 4 and 0.720 in all
gliomas. Most of its signal comes from where the scan sits in the treatment course: SHAP gives treatment 55–58%, and
the top features are `rt_started` and `rt_start_day`. Adding to clinical only (0.585, grade 4):

- \+ timing: 0.644
- \+ treatment: 0.698

The timing and treatment columns overlap heavily (`FEATURE_CONFLICTS.md`). On the PRISM report split, 44% of test
scans were pre-RT and none of them progressed. On the post-RT test scans only, the PRISM report model scored 0.778 and
the baseline 0.730 (`SHAP_PRISM_SPLIT.md`).

**Hypothesis.** Imaging (volumes, change since earlier scans, radiomics) may add value in two settings:

- when phase of care is encoded compactly instead of through the redundant timing/treatment columns;
- within the post-chemoradiation surveillance phase.

This would hold even though imaging adds nothing over the full baseline.

## 1. Analysis plan (pre-specified)

This section was written into the module docstring before the full run. It was not separately committed: plan, code
and results arrived in one commit (10569cd), and a reduced smoke run had printed some I0–I2 numbers beforehand. The plan
was not changed after either run. Anything added after the results is labelled **EXPLORATORY**.

**A. Phase-of-care block.** Built as of the scan from `features.tabular.treatment()` and the cohort's
`days_since_rt_end`. There are 4 mutually exclusive phases:

| Phase | Definition | Grade 4 scans | All-glioma scans |
|---|---|---|---|
| pre-RT | `rt_started == 0` (includes patients with no RT documented, e.g. 63 grade-4 scans, some as late as day 579) | 76 | 115 |
| during RT | started, not completed | 6 | 8 |
| early post-RT | completed, ≤ 84 d after RT end (the `early_post_rt` / RANO 12-week definition) | 98 | 104 |
| later post-RT (reference) | completed, > 84 d after RT end | 69 | 81 |

The block is 3 dummies (`phase_pre_rt`, `phase_during_rt`, `phase_early_post_rt`) plus
`log1p(days since RT end)`, which is 0 until RT is completed.

How unknown RT dates are handled, exactly as in `treatment()`:

- RT documented without a start date: counted as started before the scan.
- RT documented without an end date: never "completed", so the scan is in the during-RT phase (2 grade-4 scans).
- Completed RT always has a known end day on or before the scan day (asserted in the code), so days since RT end is
  never imputed.

**B. Ladder of non-imaging bases.** Each base gets four imaging additions on top (I0–I3), plus an optional fifth (I4).

| Rung | Base |
|---|---|
| R0 | clinical: age, sex, IDH, MGMT, with unknown flags |
| R1 | R0 + current timing block |
| R2 | R0 + phase |
| R3 | current baseline (R0 + timing + treatment) |

| Addition | Imaging features |
|---|---|
| I0 | none |
| I1 | volumes |
| I2 | volumes + morphology + delta: all non-radiomics imaging measurements |
| I3 | radiomics: nested choice over the 70 C3 configurations (`c3.RAD_CONFIGS`, with QuantileClip) via `c3.fit_predict`, with the base swapped in |
| I4 | optional, secondary: frozen deep features, nested over the 32 D1 configurations of `analyses/deep_features.py` |

Ridge (`formulations.fit`, verified labels) is the primary learner. C3 GBM is secondary and is run for I0–I2 only.

**C. Cohorts.**

- **full:** grade 4 is primary; all gliomas is secondary.
- **post_rt:** RT completed (early + later post-RT).
- **later_post_rt:** more than 84 d after RT end. This is a sensitivity analysis.

The subsets keep each patient's fold from `outputs/data/folds.csv`. Models are trained and evaluated within the subset,
and inner CV and nested selection also run within the subset. A pre-specified sensitivity analysis evaluates the
full-cohort models' out-of-fold (OOF) predictions on the subset scans only. For each cohort the analysis reports:

- scans, patients, events and censored scans;
- events per parameter (EPP) and the Riley 2020 criteria for the primary pair.

**D. Evaluation.** As in C3:

- 5×5 repeated patient-grouped CV.
- IPCW AUC(120 d), computed as the mean over repeats of each repeat's pooled-OOF AUC (`evaluate_repeated`).
- Paired patient-cluster bootstrap (1000 draws) of ΔAUC against the matching base (same learner, same cohort).
- Calibration slope and O/E, as means over repeats.

The primary contrast only gets a 100-permutation patient-level test. The I2 block is moved between patients with the
same number of scans, as whole visit-ordered blocks; base features, outcomes and folds stay fixed. The p-value is
(1 + #{Δ_perm ≥ Δ_obs}) / 101.

**E. Contrasts.**

- **Primary:** grade 4, post_rt cohort, ridge, **R2 + I2 vs R2**.
- **Key secondary:** grade 4, post_rt cohort, R2 + I3 vs R2.

Everything else is secondary or descriptive: other rungs and cohorts, all gliomas, GBM, I1, I4, R1/R2/R3 vs R0, and
R2 + imaging vs R3. Roughly 2 populations × 3 cohorts × 4 bases × 4–5 additions × 2 learners gives about 150
contrasts, with no multiplicity correction. An isolated secondary CI that excludes 0 is therefore not evidence.

**F. External check.** LUMIERE is not feasible (section 6).

**Process notes (not changes to the plan).**

- A smoke run checked that the code ran end to end. It used truncated I3/I4 grids and 20 bootstrap draws, and it
  printed some I0–I2 numbers. Its outputs went to a scratch directory and were discarded.
- The first full run crashed. In later_post_rt, a D1 configuration with `pca30` cannot be fitted on an inner training
  set with fewer than 30 verified scans. `inner_auc` now scores such a configuration NaN, so it is never chosen.
  Nothing else changed.

Run time: 18 min 38 s wall clock on 80 worker processes (`run_info.json`: 1114 s).

## 2. Cohorts

Source: `cohorts.csv`.

| Population · cohort | Scans | Patients | Events | Non-events | Censored | Pre / during / early / later | EPP R2 (10 params) | EPP R2+I2 (54) |
|---|---|---|---|---|---|---|---|---|
| grade 4 · full | 249 | 126 | 93 | 117 | 39 | 76 / 6 / 98 / 69 | 9.3 | 1.7 |
| grade 4 · post_rt | 167 | 84 | 83 | 83 | 1 | 0 / 0 / 98 / 69 | 8.3 | 1.5 |
| grade 4 · later_post_rt | 69 | 40 | 36 | 32 | 1 | 0 / 0 / 0 / 69 | 3.6 | 0.7 |
| all gliomas · full | 308 | 155 | 100 | 156 | 52 | 115 / 8 / 104 / 81 | 10.0 | 1.9 |
| all gliomas · post_rt | 185 | 92 | 84 | 96 | 5 | 0 / 0 / 104 / 81 | 8.4 | 1.6 |
| all gliomas · later_post_rt | 81 | 46 | 37 | 40 | 4 | 0 / 0 / 0 / 81 | 3.7 | 0.7 |

**Riley note.** The Riley 2020 criteria use an anticipated R²cs of 15% of the maximum. For the primary cohort they
require about 750 scans (375 events) for R2 and about 4040 scans (2022 events) for R2+I2. The data have 167 scans and
83 events. Every model here, the non-imaging bases included, is far below the recommended size. Ridge shrinkage is
doing much of the work.

Censoring is almost absent after RT (1 censored scan in grade-4 post_rt). Nearly all of the cohort's censoring sits in
the pre-RT and early scans.

In the post_rt cohorts the pre/during dummies are constant (0), so R2 reduces to clinical +
`phase_early_post_rt` + `log_days_since_rt_end`. In later_post_rt it reduces to clinical + days since RT end.

## 3. Primary and key secondary result

Source: `results.csv` and `permutation.csv`; ridge, grade 4, post_rt.

| Model | IPCW AUC (95% CI) | ΔAUC vs R2 (95% CI) | Calibration slope | O/E |
|---|---|---|---|---|
| R2 (clinical + phase) | 0.549 (0.458–0.642) | — | 0.76 | 0.99 |
| **R2 + I2 (primary)** | 0.610 (0.529–0.688) | **+0.061 (−0.038, +0.156)** | 0.68 | 0.99 |
| R2 + I3 (key secondary) | 0.609 (0.543–0.676) | +0.061 (−0.041, +0.157) | 0.44 | 0.96 |
| R2 + I1 | 0.593 | +0.044 (−0.054, +0.137) | 0.60 | 0.98 |
| R2 + I4 | 0.625 | +0.076 (−0.041, +0.192) | 0.30 | 0.97 |
| R3 (current baseline), for reference | 0.604 (0.520–0.690) | — | 0.85 | 0.99 |

**Permutation test (primary only).** The observed ΔAUC is +0.061 and the permutation p-value is **0.208**: 20 of 100
permutations reached at least +0.061.

The null distribution is not centred on 0. Its mean is +0.028, its median +0.025, and its range −0.104 to +0.162.
Adding 44 columns of *permuted* imaging to the weak R2 base already raises the AUC by about 0.03 on average.
Part of the bootstrap ΔAUC is therefore a property of adding columns to a near-chance ridge model rather than imaging
information.

**Primary conclusion: not supported.** In grade-4 post-RT scans, adding all non-radiomics imaging measurements to
clinical + phase did not improve discrimination significantly:

- ΔAUC +0.061, CI includes 0, permutation p = 0.21.
- The model stays weak (0.61).
- Calibration slope 0.68: overfitted.

The key secondary (radiomics, I3) is the same: ΔAUC +0.061 with a CI that includes 0, and calibration slope 0.44.
The nested radiomics choice was unstable. The most common configuration (legacy pca10 concat) was picked in 12 of 25
outer folds (`nested_choices.csv`).

## 4. Ladder

Sources: `ladder.png`, `results.csv` (ΔAUC vs the matching base) and `rungs.csv` (base vs base). All are ridge unless
stated otherwise, and all are secondary.

**Full grade-4 cohort.**

| Base | AUC | Δ vs R0 (95% CI) |
|---|---|---|
| R0 clinical | 0.585 | — |
| R1 + timing | 0.644 | +0.059 (−0.016, +0.133) |
| R2 + phase | 0.664 | +0.080 (+0.005, +0.152) |
| R3 baseline | 0.698 | +0.113 (+0.026, +0.208) |

R0, R1 and R3 reproduce the `feature_conflicts` values (0.585 / 0.644 / 0.698). The 4-level phase block alone (4
columns) recovers about 70% of the baseline's gain over clinical. R3 − R2 is +0.034 (−0.027, +0.090).

Imaging on top of each base in the full grade-4 cohort:

| Base | I1 | I2 | I3 | I4 |
|---|---|---|---|---|
| R0 | +0.074 (−0.014, +0.157) | +0.071 | +0.065 | +0.063 |
| R1 | +0.030 | +0.026 | +0.008 | +0.018 |
| R2 | +0.031 (−0.039, +0.098) | +0.023 | +0.002 | +0.020 |
| R3 | +0.004 | −0.007 | −0.032 | −0.004 |

None of these CIs excludes 0. R2 + I1 reaches 0.696, the same as R3 at 0.698. Volumes plus a compact phase block
therefore do as well as the full treatment block, but no better (R2+I1 vs R3 −0.002, CI −0.081 to +0.074).

**All gliomas, full cohort.**

- Bases: R0 0.619, R1 0.693, R2 0.700, R3 0.720.
- Imaging adds +0.074 to +0.096 over clinical alone, with CIs that just exclude 0.
- Over R2 it adds +0.022 to +0.032; over R3, +0.008 to +0.028. No CI excludes 0.

**Post-RT cohorts.**

- Within post-RT, phase carries almost nothing. Grade 4: R0 0.552, R2 0.549 (Δ −0.003). All gliomas: R0 0.631, R2
  0.623.
- The current timing + treatment block adds a little: grade-4 R3 0.604, R3 − R2 +0.056 (−0.023, +0.128).
- Every imaging rung adds +0.015 to +0.08 to the clinical-type bases R0/R1/R2, and +0.005 to +0.04 to R3. No CI in
  grade-4 or all-glioma post_rt excludes 0.
- The best grade-4 post-RT model is R3 + I4 deep at 0.644; the best all-glioma post-RT model is R3 + I3 at 0.685.

**GBM (secondary).**

- In the full grade-4 cohort, GBM's non-imaging bases are as good as ridge's: R2 0.698, R1 0.693.
- Imaging never helps GBM over R1/R2/R3: ΔAUC −0.027 to +0.007.
- In grade-4 post_rt: R2 + I2 vs R2 is +0.012 (−0.069, +0.102).

## 5. Sensitivity analyses

**Later post-RT only (> 12 weeks after RT end; grade 4: 69 scans / 40 patients / 36 events).** This cohort is too
small to fit a model reliably.

- The non-imaging bases score *below* chance: R0 0.343 (calibration slope −2.0), R1 0.388, R2 0.376, R3 0.472.
- This is the known negative bias of cross-validation when a model has no real signal and very few events per fold.
  The training-fold class balance moves opposite to the test fold, so a nearly null model anti-predicts.
- The large ΔAUCs here, such as R2 + I3 +0.250 (+0.127, +0.366) and R0 + I2 +0.157, are measured against a
  below-chance reference. The absolute AUCs of the imaging models are only 0.42–0.63, with calibration slopes of
  −0.37 to 0.35.
- These are not evidence of imaging value, and in a cohort of 69 scans they would not justify a model either way.
- In all gliomas, later_post_rt (81 scans), only R0 + I3 has a CI that excludes 0 (+0.146), again against a
  near-chance base (0.486).

**Full-cohort models evaluated on the subset scans (`subset_of_full.csv`).** These models were trained on all scans
and evaluated on post-RT scans only.

- Grade 4, post_rt:
  - R2 0.570, R2 + I2 0.620: Δ +0.050 (−0.061, +0.157).
  - R2 + I3: Δ +0.026.
  - R3 0.638, R3 + I2 0.624: Δ −0.014.
- All gliomas, post_rt: R2 + I2 +0.047 (−0.048, +0.145); R3 + I3 +0.034 (−0.041, +0.111).
- No CI excludes 0. The conclusion does not depend on whether the model was trained within the subset.
- The full-cohort R3 evaluated on post-RT scans (0.638 grade 4) does slightly better than R3 trained within post-RT
  (0.604).

Compare the PRISM report split, where the PRISM report model scored 0.778 and the baseline 0.730 on post-RT test
scans. Across 25 folds of 84 post-RT grade-4 patients, the post-RT AUC of every model sits around 0.55–0.66. The
PRISM report split's post-RT numbers are higher than any model reaches here.

## 6. External check (LUMIERE)

This check is not feasible. LUMIERE (`prism/data/lumiere.py`, raw `LUMIERE-ExpertRating-v202211.csv`,
`LUMIERE-Demographics_Pathology.csv`) has no RT start or end dates and no RT/chemo variables. The only treatment-time
information is the rater's `LessThan3Months` flag, meaning "< ~3 months after RT".

From `outputs/data/lumiere_cohort.csv`, 27 of 132 index scans (22 of 61 patients) carry the flag. A rough phase proxy
was tried: before the first flagged scan, flagged, after the last flagged scan. It leaves 83 of 132 scans, from
patients who are never flagged, with an unknown phase. Only 12 scans could be placed in "later post-RT".

Neither R2 (pre/during/early/later + days since RT end) nor a post-RT subset can be built. The existing MU→LUMIERE
locked models (`EXTERNAL_LUMIERE.md`) already use the only shared timing information: `early_post_rt` and days since
surgery.

## 7. Conclusion

**Does imaging add value once phase of care is accounted for, in post-RT surveillance? On these data, no
detectably.**

- **Primary contrast.** Grade-4 post-RT scans, clinical + phase, with vs without all non-radiomics imaging
  measurements: ΔAUC +0.061 (95% CI −0.038 to +0.156), permutation p = 0.21. The model stays weak (AUC 0.61) and
  overfitted (calibration slope 0.68).
- **Key secondary.** Radiomics, nested: +0.061 (−0.041 to +0.157), calibration slope 0.44.
- **Direction.** The point estimates lean towards a small imaging gain on top of clinical-type bases.
  - That lean is about the same size as what permuted imaging adds to such a weak base (+0.03 on average).
  - It shrinks to about 0 on top of the current baseline: grade 4, full, R3 + any imaging −0.032 to +0.004.

**What the ladder does show.**

1. **A compact 4-level phase-of-care block recovers a large part of the baseline's gain over clinical.** Grade 4:
   clinical 0.585, R2 0.664, R3 0.698 (the R2 − R0 CI is +0.005 to +0.152, a single secondary contrast). The headline
   baseline is largely a "where in the treatment course" model.
2. **Within the post-RT phase, nobody discriminates well.** Clinical, phase, timing, treatment, volumes, radiomics and
   deep features all give AUC 0.55–0.66 in grade 4 (ridge and GBM) (167 scans, 83 events). Phase itself carries no signal there
   (R2 − R0 −0.003).
3. **With phase known, volumes substitute for the detailed treatment columns** (R2 + I1 0.696 ≈ R3 0.698) but add
   nothing beyond them.
4. **Later post-RT alone (69 scans) is too small to fit any model.** Non-imaging bases score below chance, which
   inflates every ΔAUC there.

**EXPLORATORY (independent check, after the results).** A ridge on age alone scores 0.586 in grade-4 post-RT scans, above
R2 (0.549); age + I2 vs age gives +0.022 (−0.103, +0.145). Part of the primary +0.061 therefore comes from R2's
uninformative phase columns dragging the base down. Note also that "post-RT" means *RT documented and completed*: scans
of patients with no documented RT are in the pre-RT phase and so outside the post-RT cohort. In post-RT scans two phase
dummies are constant, so R2 has about 8 effective parameters (EPP about 10, not 8.3).

All of this sits far below Riley-recommended sample sizes (EPP 1.5 for the primary imaging model). A real but modest
imaging effect of about +0.05 AUC in post-RT surveillance cannot be excluded. Detecting it would need a cohort several
times larger, or external post-RT data with RT dates, which LUMIERE does not provide.
