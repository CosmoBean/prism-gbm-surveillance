# Scan-day intended use, within-phase performance and censoring sensitivity of the deployed model (C2)

Code: `prism/analyses/intended_use.py` (`python -m prism intendeduse`). Outputs:
`outputs/results/analyses/intended_use/`.

Status: plan committed before any of the new quantities was computed (74eaaf5); full run 2026-10-21 (Results below).

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

## Results

Run on 2026-10-21 (`run_info.json`: 32 workers, 1000 bootstrap draws, 19 s; Slurm allocation, CPU only). All files are
in `outputs/results/analyses/intended_use/`. Plan snapshot: `PLAN_snapshot.md` (git 74eaaf5). AUC = mean over the 5
repeats of the pooled-OOF IPCW AUC(120 d), 95% paired patient-cluster bootstrap CIs (1000 draws).

**Checks** (`checks.csv`). The stored OOF predictions reproduce every published AUC to < 0.0006: core 0.698, C2 0.678,
core + nested radiomics 0.666, core + fine-tuned stack 0.708, post-RT R2 0.549 and R2 + I2 0.610, and the refitted
intended-use core 0.617 / C2 0.595. The bootstrap point estimate of each scheme equals the `evaluate_repeated` point
estimate (asserted to 1e-9).

### R1. Counts (`counts.csv`)

| Set | Scans / patients | Events | Non-events | Censored | Deaths w/o progression ≤ 120 d (recoded in S2) |
|---|---|---|---|---|---|
| Grade 4, full | 249 / 126 | 93 | 117 | 39 | 14 |
| … removed by the rule (pre-RT as of the scan) | 76 / 50 | 5 | 33 | 38 | 14 |
| **Grade 4, intended use** | **173 / 86** | **88** | **84** | **1** | **0** |
| … during RT | 6 / 6 | 5 | 1 | 0 | 0 |
| … within 12 weeks after RT | 98 / 76 | 47 | 51 | 0 | 0 |
| … later post-RT | 69 / 40 | 36 | 32 | 1 | 0 |
| Grade 4, post-RT (phase-ladder cohort) | 167 / 84 | 83 | 83 | 1 | 0 |
| All gliomas, full | 308 / 155 | 100 | 156 | 52 | 16 |
| All gliomas, intended use | 193 / 95 | 90 | 98 | 5 | 0 |

The rule removes 38 of the 39 censored grade-4 scans and all 14 deaths without progression within 120 d. Inside the
intended-use population (and the post-RT cohort) both sensitivities therefore change essentially nothing. This is a
property of the data, not of the methods: every death without documented progression within 120 d follows a pre-RT scan.

### R2. C2 in the intended-use population (`headline.csv`, `contrasts.csv`)

Marginal KM within the population (headline estimator). Calibration: O/E = KM risk at 120 d / mean prediction; slope
IPCW-weighted.

| Population | Model | AUC (95% CI) | Δ vs core (95% CI) | O/E | Slope | Brier |
|---|---|---|---|---|---|---|
| Grade 4, intended use | **C2, trained on all scans (PRIMARY)** | **0.601 (0.515–0.686)** | −0.028 (−0.060 to −0.002) | 1.01 | 0.53 | 0.245 |
| | core, trained on all scans | 0.629 (0.547–0.714) | – | 1.01 | 0.65 | 0.240 |
| | C2, refitted in intended use | 0.595 (0.517–0.682) | −0.022 (−0.047 to −0.002) | 0.98 | 0.71 | 0.245 |
| | core, refitted in intended use | 0.617 (0.539–0.703) | – | 0.98 | 0.75 | 0.240 |
| All gliomas, intended use | C2, trained on all scans | 0.637 (0.550–0.721) | −0.015 (−0.049 to +0.013) | 1.03 | 0.91 | 0.236 |
| | C2, refitted in intended use | 0.661 (0.579–0.741) | −0.013 (−0.045 to +0.014) | 0.99 | 0.93 | 0.230 |
| Grade 4, full (reference) | C2 | 0.678 (0.596–0.755) | −0.020 (−0.043 to +0.000) | 1.04 | 0.85 | 0.223 |

Under the pre-specified wording: in grade 4 the deployed model shows **discrimination above chance in the
intended-use population** (lower bound 0.515 > 0.5, by a small margin), and **calibration in the large is adequate**
(O/E 1.01). It loses 0.077 AUC compared with the full cohort, because the easy pre-RT controls leave the evaluation set.
The calibration slope of 0.53 means that, inside intended use, the full-cohort model's predictions are too spread out:
part of their range encodes the pre-RT vs post-RT difference, which no longer varies here. Refitting in the population
gives slope 0.71 without improving AUC. All gliomas: 0.637 (0.550–0.721), above chance, O/E 1.03.

### R3. Within-phase AUCs inside intended use (`within_phase.csv`)

Marginal KM within the intended-use population. CIs only for strata with ≥ 10 verified events and non-events.

| Phase (events / non-events) | C2, all scans (PRIMARY) | core, all scans | C2, refitted | core, refitted |
|---|---|---|---|---|
| during RT (5 / 1) | 0.400 (descriptive only) | 0.440 | 0.040 | 0.160 |
| within 12 weeks after RT (47 / 51) | 0.631 (0.518–0.734) | 0.663 (0.556–0.765) | 0.613 (0.499–0.720) | 0.639 (0.528–0.739) |
| later post-RT (36 / 32) | 0.583 (0.431–0.742) | 0.598 (0.447–0.755) | 0.529 (0.375–0.687) | 0.552 (0.404–0.713) |
| **pooled within-phase pairs** (88 / 84) | **0.616 (0.524–0.698)** | 0.642 (0.555–0.724) | 0.585 (0.498–0.671) | 0.610 (0.526–0.697) |

All gliomas, C2 (all scans): early post-RT 0.660 (0.553–0.762), later 0.637 (0.490–0.773), pooled within-phase 0.652
(0.568–0.732).

The pooled within-phase AUC of C2 (0.616) is close to its intended-use AUC (0.601), so little of the intended-use
discrimination comes from ranking one phase against another. The later post-RT CI spans 0.5.

### R4. Sensitivity 1 (phase-specific censoring) and Sensitivity 2 (deaths as non-events)

Source: `schemes.csv`, `contrasts.csv`. S1 = `phase5_km`; S2 = `deaths_nonevent_km` (deaths recoded, remaining
censoring by marginal KM). The existing unweighted `deaths_as_controls` scheme gives the same values to ±0.002 and is
in the files. Under S1 and S2, CIs come from `phase_censoring.bootstrap` (weights re-estimated in every draw).

**C2 headline**

| Set | Marginal (headline) | S1 phase-specific weights | S2 deaths as non-events |
|---|---|---|---|
| Grade 4, full | 0.678 (0.596–0.755) | 0.734 (0.648–0.814); Δ vs marginal +0.056 (+0.025 to +0.091) | 0.706 (0.628–0.787); Δ +0.028 (+0.011 to +0.050) |
| Grade 4, intended use (C2 all scans) | 0.601 (0.515–0.686) | 0.601 (0.518–0.684); Δ −0.000 | 0.601 (identical: nothing recoded) |
| All gliomas, full | 0.706 (0.628–0.777) | 0.740 (0.671–0.810) | 0.723 (0.655–0.794) |
| All gliomas, intended use (C2 all scans) | 0.637 (0.550–0.721) | 0.637 (0.557–0.716) | 0.637 (identical) |

S2 also improves calibration in the full cohort (grade 4 C2: O/E 1.04 → 0.99, slope 0.85 → 0.99).

**Imaging contrasts (grade 4)**: ΔAUC (95% CI), and the change vs marginal (difference of differences).

| Contrast | Marginal | S1 phase-specific weights | S2 deaths as non-events |
|---|---|---|---|
| core + nested radiomics − core (full) | −0.032 (−0.077 to +0.017) | −0.021 (−0.061 to +0.019); change +0.011 (−0.005 to +0.029) | −0.035 (−0.075 to +0.010); change −0.002 (−0.011 to +0.005) |
| core + fine-tuned stack − core (full) | +0.009 (−0.021 to +0.042) | +0.011 (−0.012 to +0.035); change +0.002 (−0.008 to +0.010) | +0.009 (−0.018 to +0.038); change −0.000 |
| R2 + I2 − R2 (post-RT surveillance) | +0.061 (−0.033 to +0.155) | +0.061 (−0.032 to +0.155); change +0.000 | +0.061 (−0.033 to +0.155); nothing recoded |

Secondary, descriptive (scored on intended-use scans only, marginal KM within the subset): core + nested radiomics −
core −0.033 (−0.097 to +0.034); core + fine-tuned stack − core +0.010 (−0.031 to +0.054).

The sensitivities move the absolute AUCs of the full cohort (because they mostly reweight pre-RT controls), but they
move the imaging contrasts by at most 0.011. That is expected: both arms of each contrast share the same censoring
weights, and the reweighted scans are ones every model ranks the same way.

### R5. Verdict under the pre-specified rule (`rule.csv`)

| Rule item | Result | Verdict |
|---|---|---|
| Any imaging contrast with ΔAUC ≥ +0.03 and CI excluding 0 under S1 or S2 | Radiomics −0.021 / −0.035; fine-tuned +0.011 / +0.009; R2 + I2 +0.061 / +0.061, but its CI includes 0 under both (lower −0.032 / −0.033) | **No: imaging conclusions hold** |
| C2 headline lower CI > 0.5 in grade 4 under marginal, S1, S2 | 0.596 / 0.648 / 0.628 | **Holds** |
| C2 (trained on all scans) in grade-4 intended use | 0.601 (0.515–0.686), O/E 1.01 | **"Discrimination above chance in the intended-use population"; calibration in the large adequate** |
| Same, all gliomas | 0.637 (0.550–0.721), O/E 1.03 | Above chance; adequate |

**Headline conclusions hold.** The R2 + I2 point gain stays above +0.03 under both sensitivities (unchanged from the
primary phase-ladder result, where it is "not supported", permutation p = 0.208). Its CI still includes 0, so it does not
meet the bar.

### R6. Deviations and notes

- **DEVIATION (procedure).** Before the 1000-draw run, the module was run once as a pipeline test with 50 bootstrap
  draws on the real labels (grade 4 only). That test wrote `PLAN_snapshot.md`, from the committed plan text (git
  74eaaf5). The plan was not changed after it. The point estimates do not depend on the number of draws.
- **DEVIATION (minor).** The rule's "C2 headline under marginal" item in `rule.csv` uses the scheme bootstrap CI
  (0.598–0.763), not the `evaluate_repeated` CI (0.596–0.755) that the plan names for the headline. Both lower bounds
  are > 0.5, so the verdict is the same. The tables above report the `evaluate_repeated` CI.
- Inside intended use the 5-level phase has no pre-RT levels, so S1 there is the same as stratifying by the 3
  remaining phases. With 1 censored scan (grade 4) or 5 (all gliomas), any weighting gives the same AUC to 0.001.
- During RT (5 events / 1 non-event) has no interpretable AUC (values from 0.04 to 0.44 depend on one control).
- **Suggested text for the paper** (not applied; `paper/` untouched): define the intended use as "scans on or after the
  documented start of radiotherapy", which can be checked on the scan day. Report the deployed model there as 0.601
  (0.515–0.686), O/E 1.01, slope 0.53, with within-phase pooled 0.616 (0.524–0.698). Use this in place of the
  `rt_pathway` statement (0.625), which needs future information.
