# Scan-day intended use, within-phase performance and censoring sensitivity of the deployed model (C2)

Code: `prism/analyses/intended_use.py` (`python -m prism intendeduse`). Outputs:
`outputs/results/analyses/intended_use/`.

Status: plan written and committed before any of the new quantities below was computed.

## 0. Why

A referee pointed out that the intended-use statement in `PHASE_CENSORING.md` ("patients on a documented RT pathway",
`rt_pathway`: core 0.654, C2 0.625) uses future information. At a pre-RT scan, nobody knows on the scan day whether RT
will be documented later. The paper needs an intended-use population that can be defined on the scan day, and the
performance of the deployed model (C2) in that population.

The deployed model is C2 (ridge on clinical + timing + scan-day treatment; no unknown-marker indicators; IDH/MGMT
masked before diagnosis; `early_post_rt` coded as known on the scan day). Its headline is grade 4 IPCW AUC(120 d)
0.678 (0.596–0.755) (`phase_censoring/corrected.csv`).

**What is already known before this plan** (so the reader can judge what is truly pre-specified):

- `phase_censoring` already refitted core and C2 inside `rt_started` (RT started by the scan day): core 0.617
  (0.539–0.703), C2 0.595 (0.517–0.682), grade 4, 173 scans, 1 censored scan. These are the "refitted within the
  population" numbers below. They are not new and are re-reported only for completeness.
- `phase_censoring` also wrote the full-cohort OOF predictions scored on `rt_started` (`C2@full`, `R3@full` rows in
  `schemes.csv` / `within_phase.csv`). These numbers were never reported or looked at for this plan.
- For the full grade-4 cohort, C2 under phase-specific censoring weights (`phase5_km`) is 0.734, and under the
  unweighted `deaths_as_controls` scheme 0.708 (`PHASE_CENSORING.md` §2.2).
- Not known: the imaging contrasts (radiomics, phase-ladder imaging, fine-tuned encoder) under any censoring
  alternative, and C2 in the intended-use population with deaths recoded.

## Plan (pre-specified)

Horizon H = 120 d. Label: documented progression within 120 d; censored scans enter through IPCW. Evaluation machinery
unchanged: shared 5×5 patient-grouped folds (`outputs/data/folds.csv`); AUC = mean over the 5 repeats of the pooled
OOF IPCW AUC; 95% paired patient-cluster bootstrap, 1000 draws (`metrics.evaluate_repeated`); weighting schemes and
within-phase AUCs reuse `phase_censoring.py` (`km_scheme`, `wauc`, `bootstrap`, `contrast`), which re-estimates the
censoring weights inside every bootstrap draw. **No model is retrained.** All predictions are read from stored OOF
files:

| Model | OOF file | Column |
|---|---|---|
| C2, core (full-cohort fit) | `analyses/phase_censoring/oof_<pop>_full.csv.gz` | `C2#r*`, `R3#r*` |
| C2, core (refitted inside the intended-use population) | `analyses/phase_censoring/oof_<pop>_rt_started.csv.gz` | `C2#r*`, `R3#r*` |
| Core + nested radiomics vs core | `c3/grade4/oof_repeats.csv.gz` | `NESTED\|-\|-\|-\|ridge` vs `None\|none\|none\|none\|ridge` |
| R2 + I2 vs R2 (clinical + phase ± all non-radiomics imaging), post-RT surveillance scans | `analyses/phase_ladder/oof_repeats_grade4_post_rt.csv.gz` | `R2+I2\|ridge` vs `R2\|ridge` |
| Core + fine-tuned BraTS21 stack vs core | `analyses/finetune/grade4/oof_repeats.csv.gz` | `core+ft:brats21` vs `core` |

These are the primary contrasts of their own pre-specified analyses (`C3_radiomics.md`, `PHASE_LADDER.md`,
`FINETUNE_DEEP.md`). A check that the stored core / C2 OOF reproduce the published AUCs (0.698 / 0.678; R2 0.549 and
R2 + I2 0.610 in post-RT; fine-tune core 0.698 and stack 0.708) is written to `checks.csv`.

### (a) Intended-use population (scan-day information only)

- **Primary: grade-4 scans taken on or after the documented RT start date** (RT started by the scan day:
  `phase_ladder.phase_label` ≠ `pre_rt`, i.e. during RT, within 12 weeks after RT, and later). "RT started" uses
  `features.tabular.treatment`: RT is recorded as given and its documented start day is ≤ the scan day. Both are known
  on the scan day. (The 2 RT patients with a missing start date are counted as started, as in `treatment`.)
- **Rationale.** The clinical use is post-RT surveillance: deciding, at a follow-up MRI after chemoradiation has
  begun, whether progression is likely within 120 days. Pre-RT postoperative scans are out of scope. At that point the
  question is the treatment plan, not surveillance, and the outcome of most such scans in MU is unobserved (38 of the 39
  censored grade-4 scans are pre-RT). Out-of-scope scans are flagged in the audit record (`pre_rt_as_of_scan` flag).
  This is the `rt_started` cohort of `phase_censoring`, now named the intended-use population.
- **Secondary: the same rule in all gliomas.**

### (b) Quantities

1. **C2 IPCW AUC with CI in the intended-use population** (core reported alongside for reference), in two versions:
   - **PRIMARY: trained on all scans, evaluated on intended-use scans** (`C2@full`): the full-cohort OOF predictions
     restricted to intended-use scans. This is how the model is deployed: it is trained on everything and applied to
     in-scope scans. Censoring weights are re-estimated within the intended-use scans (marginal KM, the headline
     estimator, via `evaluate_repeated` on the subset).
   - Secondary: refitted within the population (`C2` from `oof_<pop>_rt_started`; already known, see §0).
   - ΔAUC C2 − core (paired bootstrap) for both versions.
2. **Calibration** of `C2@full` and refitted C2 in the intended-use population: O/E = Kaplan–Meier risk at 120 d of the
   population / mean predicted risk (`oe_ratio` of `evaluate_repeated`, the estimator used for the headline), and the
   IPCW-weighted calibration slope (`cal_slope`). Brier (IPCW) as a secondary.
3. **Within-phase AUCs of C2** (`C2@full`, primary; refitted C2 secondary) inside intended use: during RT, within 12
   weeks after RT (early post-RT), later post-RT, each under marginal KM estimated in the intended-use population, plus
   the **pooled within-phase pairs AUC** (only case–control pairs within the same phase count; `wauc(strata=phase)`).
   CIs only for strata with ≥ 10 verified events and ≥ 10 verified non-events (`MIN_STRATUM`); others are descriptive.
   The pooled within-phase AUC always gets a CI.
4. **Counts**: scans, patients, events, non-events and censored scans; deaths without progression within 120 d;
   for the full population and for each phase inside intended use; and the number of scans removed by the rule.

### (c) Sensitivity 1: phase-specific censoring weights (`phase5_km`)

One KM censoring curve per 5-level phase (RT pending / RT never documented / during RT / within 12 weeks after RT /
later). Cases weighted 1/G_phase(T_i), controls 1/G_phase(H). The 5-level phase is an analysis stratifier only (never
a model input). Applied to:

- C2 headline, full grade 4 (0.734 already known) and C2@full / refitted C2 in intended use;
- core + nested radiomics vs core (grade 4 full);
- R2 + I2 vs R2 (grade-4 post-RT cohort, where the strata are the two post-RT phases);
- core + fine-tuned stack vs core (grade 4 full).

For each: AUC of each arm, ΔAUC and paired 95% CI, and the change of ΔAUC vs the marginal scheme (difference of
differences, paired CI).

### (d) Sensitivity 2: death without documented progression within 120 d counted as a non-event

A scan whose patient died without documented progression within 120 days of the scan is recoded as a non-event (label
0, `status_known_indefinitely` = True, so it is a control with follow-up beyond H), instead of censored at death. All
other censored scans keep marginal KM IPCW, re-estimated after recoding. This differs from the existing unweighted
`deaths_as_controls` scheme, which drops the remaining censored scans; that scheme is reported alongside for reference.
Applied to C2 (full grade 4 and intended use, with O/E and slope from `evaluate_repeated` on the recoded data) and the
same three contrasts. Counts of recoded scans are reported per analysis set.

### (e) Decision rule (fixed now)

- **Imaging conclusions hold** if, for each of the three imaging contrasts, under Sensitivity 1 and under Sensitivity 2
  separately, it is **not** the case that ΔAUC ≥ +0.03 with a 95% CI excluding 0. If any contrast meets that bar under
  either sensitivity, the verdict is "imaging conclusion changed by censoring handling" for that contrast, and the paper
  must report it.
- **C2 headline holds** ("discrimination above chance in grade 4") if the lower 95% CI bound of C2 is > 0.5 under the
  marginal scheme, Sensitivity 1 and Sensitivity 2 in full grade 4.
- **Intended use.** C2's intended-use AUC (primary: C2@full) is reported in the paper whatever its value, with fixed
  wording: "discrimination above chance in the intended-use population" if the lower CI bound is > 0.5, otherwise "not
  distinguishable from chance in the intended-use population". Calibration in the large is called adequate if O/E is
  within 0.80–1.25.
- No multiplicity correction; everything except the rule items is secondary or descriptive. Any analysis added after the
  results are seen is labelled **EXPLORATORY**, and any change to this plan is labelled **DEVIATION**.
- Secondary, descriptive (no rule): the radiomics and fine-tune contrasts scored on intended-use scans only (full-cohort
  OOF restricted to RT-started scans, marginal KM within the subset).

**Run** (step 2): `python -m prism intendeduse --workers <n>`. It only rescores stored OOF predictions (bootstraps
only), so a few minutes on CPU.
