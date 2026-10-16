# Phase of care vs censoring: is the phase-of-care finding a loss-to-follow-up artefact?

Code: `prism/analyses/phase_censoring.py` (`python -m prism phasecens`). Outputs:
`outputs/results/analyses/phase_censoring/`. Pipeline test on permuted outcomes:
`outputs/results/analyses/phase_censoring_shuffled<seed>/` (not results).

Status: plan committed before any model run (c98febe); full run on 2026-10-15 (`run_info.json`: 40 workers, 1000
bootstrap draws, 81 s). Plan snapshot: `outputs/results/analyses/phase_censoring/PLAN_snapshot.md`.

## 0. Why

A review found that the phase-of-care finding (Section 2.5 of the manuscript: R2 clinical + phase 0.664 vs R0 clinical
0.585, +0.080, CI +0.005 to +0.152, grade 4, `outputs/results/analyses/phase_ladder/rungs.csv`) may partly come from
censoring. Of the 39 censored grade-4 scans, 38 are pre-RT. The headline IPCW AUC uses one marginal Kaplan–Meier
censoring curve (`prism/models/metrics.py`, `ipcw_context`), which assumes censoring does not depend on phase.

Step 1 found three more facts (descriptives below; none uses a model):

1. **The censored pre-RT scans belong to patients with no treatment record at all.** For the 37 grade-4 patients whose RT is
   never documented, the RT field and the chemotherapy field are both blank, not "No". All 38 censored pre-RT scans come
   from these patients. Their median follow-up after the scan is 0 days, and 14 of them died without documented progression.
2. **Table 1 "unknown 65" resolved.** `early_post_rt` is NaN when the RT end date is missing (`prism/data/mu.py`,
   `build_cohort`). This covers 63 pre-RT scans of patients with no RT documented, plus 2 during-RT scans where RT is
   documented but has no end date. In all gliomas the count is 94 = 92 + 2. Every one of these scans has a phase:
   pre_rt_never_documented (63) or during_rt (2).
3. **The core model can read future RT documentation.** `c3.BASE_PRE` adds a missingness indicator for `early_post_rt`
   (and for its MGMT interaction). At a pre-RT scan this indicator is 1 when RT is never documented and 0 when RT is
   documented later. It therefore separates "RT pending" from "RT never documented" using information from after the
   scan. This is a third look-ahead, alongside the unknown-marker shortcut and the molecular look-ahead (IDH/MGMT used
   at 8 scans taken before diagnosis, `AUDIT_SYSTEM.md`). The audit's as-of check did not flag it, because it checks
   raw values, not the missingness indicators added by the imputer.

## Analysis plan (pre-specified)

Written in step 1, before any model of this module was fitted or scored on the real labels. Saved to
`outputs/results/analyses/phase_censoring/PLAN_snapshot.md` by the first real run, and not changed afterwards. Anything
added after the results are seen is labelled **EXPLORATORY**. Populations: grade 4 (primary) and all gliomas
(secondary). Horizon H = 120 d.

**Shared machinery (unchanged).**
- Folds: the shared 5×5 patient-grouped folds (`outputs/data/folds.csv`).
- Pipeline: `prism.audit.model.fit_pipeline`, i.e. `c3.BASE_PRE` + ridge on verified labels with inner patient-grouped
  choice of C, seed = repeat. It reproduces the C3 core OOF; a check against `c3/<pop>/oof_repeats.csv.gz` and
  `phase_ladder/oof_repeats_<pop>_full.csv.gz` (R0/R1/R2) is written to `checks.csv`.
- Metrics: `metrics.evaluate_repeated` (mean over repeats of pooled-OOF IPCW AUC, Brier, O/E, slope, paired
  patient-cluster bootstrap) and `audit_system.stratum_metrics` (CITL), plus `audit_system.referral_tables`.
- No existing module was changed. New helpers live in `phase_censoring.py`.

**1. Descriptives (no model).**
- Phase (4-level and 5-level) × 120-day status (event / non-event / censored), with these counts for each cell:
  - censored on the scan day (follow-up ≤ 1 d);
  - censored deaths without progression;
  - median follow-up of the censored scans.
- RT-never-documented patients compared with RT-documented patients:
  - age, sex, grade;
  - IDH and MGMT;
  - chemotherapy and hospice fields;
  - scans per patient, scan day, follow-up;
  - deaths and progressions.
- Resolution of the Table 1 "unknown", and the scans taken before diagnosis.

**2. Five-level phase.** `pre_rt_pending` (RT documented, started after the scan) | `pre_rt_never_documented` |
`during_rt` | `early_post_rt` | `later_post_rt`. Otherwise it is identical to `phase_ladder.phase_label`. "Never
documented" is only known afterwards, so the 5-level phase is an **analysis stratifier and censoring-model covariate,
never a model input**.

**3. Censoring weights.** Each scheme defines cases, controls and weights. AUC is the weighted concordance over case ×
control pairs (ties ½), taken as the mean over the 5 repeats of each repeat's pooled-OOF AUC.

| Scheme | Definition |
|---|---|
| `marginal_km` | One KM censoring curve. Reproduces the headline `auc_ipcw` (asserted to 1e-9). |
| **`phase5_km`** (primary alternative) | One KM censoring curve per 5-level phase. Cases are weighted 1/G_s(T_i), controls 1/G_s(H). This is the Uno estimator with censoring that may depend on phase (MAR given phase). |
| `phase4_km` | One KM censoring curve per 4-level phase. |
| `logistic_ipw` | Verified scans weighted 1/P(verified \| 5-level phase, age, sex, log1p days from diagnosis, + grade 4 in all gliomas). Logistic with C = 1 on standardised covariates; P floored at 0.1 (`G_FLOOR`). |
| `verified` | Unweighted verified scans (reference). |
| `deaths_as_controls` | Death without progression before H counts as a non-event (competing-risk view: a patient who died cannot progress). |
| `bound_cens_events` / `bound_cens_controls` | Every censored scan is set to event / to non-event. These are extreme bounds under arbitrary informative censoring. |

- Every scheme re-estimates its weights in each of 1000 patient-cluster bootstrap draws. The draws are paired across
  arms and schemes.
- Applied to the core model (R3) and the phase ladder: R0 clinical | R1 + timing | R2 + phase | R3 core. Each is
  refitted here and checked against the stored phase-ladder OOF.
- Reported:
  - AUC by scheme;
  - change vs `marginal_km`;
  - gain over R0 and its change vs `marginal_km` (difference of differences, paired CI);
  - a phase-stratified AUC that counts only case-control pairs within the same 4-level phase.

**4. Cohorts and sensitivity.** Models are refitted and evaluated inside each cohort. Patients keep their shared fold,
and censoring is re-estimated inside the cohort.

| Cohort | Definition |
|---|---|
| `full` | All scans. |
| `rt_pathway` | Excludes the patients whose RT is never documented. This needs a treatment-plan field at deployment, so it is an intended-use statement, not an as-of rule. |
| `rt_started` | Scans with RT started by the scan day (during + post RT). This is a deployable as-of rule. |

- The full-cohort OOF predictions are also evaluated on each subset (arms `<arm>@full`).
- Within-phase AUCs (4- and 5-level phase) are computed for core (R3), R0 (clinical only), R2 and C2, under
  `marginal_km` (cohort-level weights) and `phase5_km` (the same as re-estimating censoring within the phase), plus
  `logistic_ipw` and `verified`.
- A within-stratum AUC gets a CI only if the stratum has ≥ 10 verified events and ≥ 10 verified non-events. Otherwise
  it is shown as descriptive only, as in the audit subgroups.

**5. Corrected core models.** All use the same pipeline as the core model.

| Arm | Change from the core model |
|---|---|
| `core_no_unknown` | `idh_unknown` and `mgmt_unknown` dropped. Reproduces the audit shortcut arm (0.676 grade 4, `audit_system/shortcut_arms.csv`). |
| `C1` | `core_no_unknown` + IDH/MGMT masked at scans before the diagnosis date (8 grade-4 / 11 all-glioma scans). `idh_mutant` = `mgmt_methylated` = 0, the coding unknown markers get once their indicators are dropped; the MGMT × early-post-RT term is recomputed. |
| `C1_mean` | As C1, but unknown/masked IDH and MGMT are filled with the training-fold mean of the known values (no indicator). Sensitivity analysis. |
| **`C2`** (candidate corrected headline) | C1 + as-of `early_post_rt`: 1 if RT was completed by the scan and ≤ 84 d have passed since its end, else 0. Never NaN, so there is no missingness indicator and no look-ahead to future RT documentation. |

- Why C2: it removes all three look-aheads known now. C1, the variant specified before step 1, is reported alongside.
- Reported for each arm:
  - IPCW AUC under every scheme;
  - IPCW Brier;
  - calibration slope, O/E (KM) and CITL;
  - ΔAUC vs core (paired bootstrap).
- **LUMIERE transport.** LUMIERE has no RT dates, so the core model cannot be applied there (as before). The existing
  shared-feature model (clinical + log days since surgery + `early_post_rt` + volumes, `external_lumiere`) is refitted
  on MU with the same corrections:
  - `shared_no_unknown`;
  - `shared_C1`: MU pre-diagnosis markers masked; LUMIERE scan days are relative to surgery, so none are masked;
  - `shared_C2`: C1 + MU `early_post_rt` NaN → 0, i.e. as of the scan.

  Each is compared with `locked_shared`, which reproduces `audit_system/lumiere_oe.csv`. Reported: LUMIERE AUC, O/E
  and slope with 1000-draw patient-bootstrap CIs.

**6. Mitigations.** Each is quantified on the core model and on C2.
- (a) **Intended-use restriction** to `rt_pathway` or `rt_started`. Reported: scans, patients, events and censored scans
  removed; AUC inside scope (`marginal_km`, `phase5_km`); phase-stratified AUC.
- (b) **Referral / out-of-scope flags** in the audit record, evaluated with `audit_system.referral_tables`. Each flag
  gets AUC retained / referred, gain vs random removal and gain vs phase-composition-matched removal (1000 draws). The
  flags:
  - `pre_rt_as_of_scan`: deployable;
  - `rt_never_documented`: needs a documented treatment plan;
  - the existing `i_early_post_rt`;
  - `pre_rt_or_early_post_rt`.
- (c) **Within-phase reporting**: the item-4 table.

**Primary estimands (grade 4).**
- **P1, censoring.** Two estimates of the phase-of-care gain R2 − R0:
  - its ΔAUC under `phase5_km`, and its change vs `marginal_km`;
  - co-primary: R2 − R0 refitted in `rt_pathway`.

  **Decision rule.** The finding is +0.080 under the marginal scheme. Half of that is +0.040. It is called:
  - **robust** if both estimates are ≥ +0.040;
  - **partly censoring-dependent** if exactly one is;
  - **not supported once censoring is handled** if neither is.

  The two bounds give the range of the gain under arbitrary informative censoring, and are reported alongside.
- **P2, corrected headline.** C2 IPCW AUC (`marginal_km`, the headline estimator) with CI; ΔAUC C2 − core; calibration
  slope and O/E.
- Everything else is secondary or descriptive, with no multiplicity correction.

**Minimal detectable effects** (`mde.csv`). These use Hanley–McNeil, 80% power, two-sided α = 0.05, MDE = 2.80 × SE
at AUC 0.5, and treat scans as independent, so they are optimistic. Grade 4:

| Contrast | Minimal detectable effect |
|---|---|
| Full-cohort AUC vs 0.5 (93 events / 117 non-events) | 0.113 |
| Early post-RT (47 / 51) | 0.164 |
| Later post-RT (36 / 32) | 0.198 |
| Pre-RT (5 / 33) | 0.393 (descriptive only) |
| RT pending (2 / 11) | 0.645 (descriptive only) |
| RT never documented (3 / 22 verified) | 0.507 (descriptive only) |
| Paired full-cohort contrasts, from the existing bootstrap CIs: R2 − R0 | 0.104 |
| Shortcut arm (no unknown markers) − core | 0.033 |
| Treatment-only − core | 0.070 |

- Changes of a few hundredths, which is the scale a reweighting can produce, can therefore be estimated but not
  distinguished from zero, except for contrasts as tightly paired as the shortcut arm.
- No within-phase AUC in the pre-RT strata can be interpreted.

**Run** (step 2): `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python -m prism phasecens
--workers 40`. This makes 800 ridge fits plus 1000-draw bootstraps. On 40 CPUs a 200-draw shuffled-label run took
24 s, so the full run should take a few minutes. No GPU is needed.

## 1. Descriptives (step 1; no model)

Source: `outputs/results/analyses/phase_censoring/descriptives_{phase_outcome,rt_documentation,table1_unknown}.csv`
(`python -m prism phasecens --descriptives-only`).

**Phase × 120-day status, grade 4**

| Phase (5-level) | Scans | Patients | Events | Non-events | Censored | Censored, follow-up ≤ 1 d | Censored deaths w/o progression | Verified event rate |
|---|---|---|---|---|---|---|---|---|
| pre-RT, RT pending | 13 | 13 | 2 | 11 | 0 | 0 | 0 | 0.15 |
| pre-RT, RT never documented | 63 | 37 | 3 | 22 | 38 | 20 | 14 | 0.12 |
| during RT | 6 | 6 | 5 | 1 | 0 | 0 | 0 | 0.83 |
| early post-RT | 98 | 76 | 47 | 51 | 0 | 0 | 0 | 0.48 |
| later post-RT | 69 | 40 | 36 | 32 | 1 | 1 | 0 | 0.53 |
| all | 249 | 126 | 93 | 117 | 39 | 21 | 14 | 0.44 |

The median follow-up of the censored scans is 0 days.

**Phase × 120-day status, all gliomas**

| Phase (5-level) | Scans | Events | Non-events | Censored |
|---|---|---|---|---|
| pre-RT, RT pending | 23 | 6 | 17 | 0 |
| pre-RT, RT never documented | 92 | 4 | 41 | 47 |
| during RT | 8 | 6 | 2 | 0 |
| early post-RT | 104 | 47 | 56 | 1 |
| later post-RT | 81 | 37 | 40 | 4 |

So 47 of the 52 censored scans in all gliomas fall in the RT-never-documented stratum.

**Patients with RT never documented vs documented (grade 4)**

| | RT never documented | RT documented |
|---|---|---|
| Patients / scans | 37 / 63 | 89 / 186 |
| Scans per patient, median [IQR] | 1 [1–2] | 2 [1–3] |
| Age, median [IQR] | 65 [58–78] | 61 [53–69] |
| Male | 57% | 51% |
| IDH wildtype / mutant / unknown (patients) | 32 / 2 / 3 | 80 / 6 / 3 |
| MGMT methylated / unmethylated / unknown | 12 / 17 / 8 | 33 / 45 / 11 |
| Chemotherapy field "Yes" / blank | 0 / 37 | 88 / 1 |
| Hospice field "Yes" | 10 | 15 |
| Scan day from diagnosis, median (range) | 20 (−58 to 579) | 103 (−29 to 1332) |
| Follow-up after the scan, median [IQR] (d) | 36 [0–298] | 317 [178–490] |
| Scans with follow-up ≤ 1 d | 21 | 1 |
| Patients who died without progression | 14 | 0 |
| Patients with documented progression | 3 | 88 |
| Scans: event / non-event / censored | 3 / 22 / 38 | 90 / 95 / 1 |

The never-documented group is older, was scanned early (around surgery), and has no treatment record. In almost every
case it is either lost right after the scan or dies without documented progression. It looks like a group treated or
followed elsewhere, or not treated, rather than a "pre-RT surveillance" group. Its censoring is very unlikely to be
independent of outcome: deaths dominate.

**Table 1 "unknown" and the molecular look-ahead**

| | Grade 4 | All gliomas |
|---|---|---|
| `early_post_rt` unknown (Table 1) | 65 | 94 |
| … pre-RT, RT never documented | 63 | 92 |
| … during RT, RT documented without end date | 2 | 2 |
| Scans in the early post-RT window | 98 | 104 |
| Scans before the diagnosis date (molecular look-ahead) | 8 (7 patients), −58 to −1 d | 11 (10 patients) |

**Corrected Table 1 wording (grade 4):** "Within 12 weeks after RT: 98 (39%); unknown 65 (63 with no RT documented, 2 with RT end date missing)"; all gliomas "104 (34%); unknown 94 (92 with no RT documented, 2 with RT end date missing)". The phase analysis has
no unknowns: the 63 scans are pre-RT and the 2 are during RT.

## 2. Results

All files below are in `outputs/results/analyses/phase_censoring/`. Grade 4 unless stated. AUC is the mean over the
5 repeats of the pooled-OOF IPCW AUC(120 d), with 95% patient-cluster bootstrap CIs (1000 draws).

**Consistency checks** (`checks.csv`). The refitted core model reproduces `c3/<pop>/oof_repeats.csv.gz`, and R0, R1 and
R2 reproduce `phase_ladder/oof_repeats_<pop>_full.csv.gz`, all to 1.7e-16. The `marginal_km` scheme reproduces
`fast_auc_brier` for every arm (asserted to 1e-9). Under it the core model scores 0.698 and the no-unknown-marker arm
0.676, the same as the headline and as `audit_system/shortcut_arms.csv`.

The bootstrap CIs of the ladder gains here come from this module's own draws. They differ slightly from
`phase_ladder/rungs.csv`: R2 − R0 under the marginal scheme is +0.080, with CI +0.019 to +0.160 here and +0.005 to
+0.152 there.

### 2.1 P1: is the phase-of-care gain a censoring artefact?

Source: `ladder_schemes.csv`. The gain is R2 (clinical + phase) − R0 (clinical); "Change vs marginal" is a
difference of differences.

| Weighting / cohort | Gain R2 − R0 (95% CI) | Change vs marginal (95% CI) |
|---|---|---|
| marginal_km, full (headline) | +0.080 (+0.019 to +0.160) | – |
| **phase5_km, full** (primary) | **+0.124 (+0.039 to +0.232)** | +0.045 (+0.005 to +0.104) |
| phase4_km, full | +0.125 (+0.044 to +0.224) | +0.046 (+0.019 to +0.090) |
| logistic_ipw, full | +0.118 (+0.022 to +0.221) | +0.038 (−0.018 to +0.092) |
| deaths_as_controls, full | +0.111 (+0.044 to +0.193) | +0.032 (+0.006 to +0.066) |
| bound: censored = events | −0.044 (−0.107 to +0.034) | −0.123 (−0.176 to −0.082) |
| bound: censored = non-events | +0.167 (+0.098 to +0.248) | +0.088 (+0.049 to +0.130) |
| **rt_pathway refit** (co-primary; 1 censored scan left) | **+0.057 (+0.009 to +0.117)** | – |
| rt_started refit (RT started by the scan) | +0.013 (−0.027 to +0.058) | – |

**Verdict under the pre-specified rule: robust.** Both primary estimates clear the +0.040 threshold: +0.124 under
phase-stratified censoring and +0.057 after excluding the RT-never-documented patients.

Three qualifications:

1. **The marginal curve was conservative, not inflating.** It spreads the scan-day censoring of the never-documented
   group over every phase. This under-weights the verified pre-RT scans, which are mostly low-risk controls. Allowing
   censoring to depend on phase therefore raises the phase gain, and every AUC (Section 2.2).
2. **About 30% of the gain comes from the never-documented group.** Excluding those patients leaves +0.057 of the +0.080.
3. **The gain does not survive the worst-case bound.** If the 38 censored never-documented scans had all progressed
   within 120 d, the gain would be −0.044. The descriptives make this unlikely: 14 of these patients died without
   documented progression, and only 3 of the 25 verified scans in the group are events. Counting deaths as non-events
   gives +0.111. Still, the data cannot rule it out.

In all gliomas the pattern is the same (`ladder_schemes.csv`):

| Weighting / cohort | Gain R2 − R0 |
|---|---|
| marginal_km | +0.082 |
| phase5_km | +0.121 |
| rt_pathway refit | +0.018 (−0.010 to +0.052) |
| bound: censored = events | −0.015 |

Here the rt_pathway gain falls below the threshold, so the all-glioma result would read "partly censoring-dependent".
All gliomas is the secondary population.

### 2.2 The core model under the alternative censoring weights

Source: `schemes.csv`, full cohort.

| Arm | marginal_km | phase5_km (Δ vs marginal) | logistic_ipw | deaths_as_controls | Bounds (events / non-events) | Phase-stratified AUC (marginal) |
|---|---|---|---|---|---|---|
| R0 clinical | 0.585 | 0.599 (+0.014) | 0.586 | 0.585 | 0.578 / 0.568 | 0.595 |
| R2 + phase | 0.664 | 0.723 (+0.059) | 0.704 | 0.697 | 0.534 / 0.736 | 0.577 |
| R3 core | 0.698 | 0.749 (+0.050, +0.021 to +0.081) | 0.728 | 0.726 | 0.561 / 0.759 | 0.637 (0.558–0.720) |
| C2 | 0.678 | 0.734 (+0.056) | 0.713 | 0.708 | 0.545 / 0.744 | 0.609 (0.529–0.689) |

The phase-stratified AUC counts only case-control pairs within the same phase. On that measure R2 (0.577) is no
better than R0 (0.595): phase information discriminates between phases, not within them. The core model keeps some
within-phase signal (0.637), mostly from treatment detail inside the early post-RT window.

### 2.3 Within-phase AUCs

Source: `within_phase.csv`, marginal_km, full-cohort OOF. CIs are shown only for strata with ≥ 10 events and ≥ 10
non-events.

| Phase (events / non-events) | R0 | R2 | R3 core | C2 |
|---|---|---|---|---|
| early post-RT (47 / 51) | 0.630 (0.519–0.729) | 0.627 | 0.663 (0.559–0.768) | 0.630 (0.528–0.734) |
| later post-RT (36 / 32) | 0.514 (0.359–0.662) | 0.480 | 0.597 (0.449–0.757) | 0.582 (0.425–0.745) |
| pre-RT, RT pending (2 / 11) | 0.546 | 0.583 | 0.696 | 0.625 (descriptive only) |
| pre-RT, RT never documented (3 / 22) | 0.732 | 0.513 | 0.449 | 0.432 (descriptive only) |
| during RT (5 / 1) | – | – | – | descriptive only |

In all gliomas the pre-RT stratum (10 / 58) is reportable: core 0.493 (0.299–0.715), C2 0.395 (0.189–0.609).

### 2.4 P2: the corrected core model (C2) and C1

Source: `corrected.csv`; LUMIERE in `lumiere.csv`.

| Arm | AUC (95% CI) | Δ vs core (95% CI) | Brier | O/E | Slope | CITL |
|---|---|---|---|---|---|---|
| core (R3) | 0.698 (0.615–0.774) | – | 0.219 | 1.04 | 0.89 | −0.09 |
| core_no_unknown | 0.676 (0.592–0.752) | −0.023 (−0.047 to −0.001) | 0.224 | 1.05 | 0.86 | −0.06 |
| C1 | 0.675 (0.591–0.751) | −0.023 (−0.047 to −0.002) | 0.224 | 1.05 | 0.85 | −0.06 |
| C1_mean | 0.681 (0.597–0.759) | −0.017 (−0.040 to +0.003) | 0.223 | 1.05 | 0.87 | −0.07 |
| **C2** | **0.678 (0.596–0.755)** | **−0.020 (−0.044 to +0.000)** | 0.223 | 1.04 | 0.85 | −0.08 |

All gliomas: C2 0.706 (0.628–0.777), Δ −0.014 (−0.036 to +0.005), O/E 1.03, slope 0.94.

Almost all of the cost comes from dropping the unknown-marker indicators (−0.023). Masking IDH/MGMT at the 8
pre-diagnosis scans changes nothing visible. Removing the RT-documentation look-ahead changes the AUC by +0.003 and
moves O/E closer to 1.

**LUMIERE transport of the shared-feature model**

| Model | Grade 4 AUC (95% CI) | O/E (95% CI) | Slope | All gliomas AUC | O/E | Slope |
|---|---|---|---|---|---|---|
| locked_shared | 0.608 (0.469–0.739) | 1.33 (1.01–1.77) | 0.38 | 0.599 | 1.30 | 0.38 |
| shared_C2 | 0.635 (0.501–0.745) | 0.99 (0.75–1.29) | 0.97 | 0.611 | 1.05 | 1.00 |

For grade 4, ΔAUC shared_C2 − locked_shared is +0.027 (−0.112 to +0.172). The corrections do not measurably change
discrimination on LUMIERE, but they remove the miscalibration that the indicator shortcut caused.

### 2.5 Mitigations

**(a) Intended-use restriction** (`mitigations.csv`, `cohorts.csv`; models refitted inside the scope):

| Scope | Scans / patients | Censored left | Core AUC | C2 AUC | R2 − R0 |
|---|---|---|---|---|---|
| full | 249 / 126 | 39 | 0.698 | 0.678 | +0.080 |
| rt_pathway (RT documented) | 186 / 89 | 1 | 0.654 (0.575–0.739) | 0.625 (0.548–0.706) | +0.057 |
| rt_started (as-of rule) | 173 / 86 | 1 | 0.617 (0.539–0.703) | 0.595 (0.517–0.682) | +0.013 |

Either restriction removes 38 of the 39 censored scans, so the AUC no longer depends on any censoring model. The price
is 0.04–0.08 of AUC, because the easy pre-RT controls leave the evaluation set. In the restricted scopes C2 is below
the core model by 0.029 (−0.057 to −0.004) for rt_pathway and 0.022 (−0.044 to −0.003) for rt_started.

**(b) Referral / out-of-scope flags** (`referral.csv`, full-cohort OOF):

| Flag | Rate | AUC on retained scans (core / C2) | Gain vs random removal | Gain vs composition-matched removal |
|---|---|---|---|---|
| pre-RT as of scan (deployable) | 31% | 0.629 / 0.601 | −0.069 / −0.077 | 0 by construction |
| RT never documented | 25% | 0.658 / 0.634 | −0.039 / −0.044 | +0.013 / +0.014 |

Neither flag improves the AUC on the scans the model keeps: both remove scans the model ranks easily. Their value is
scope honesty. Flagging out-of-scope scans makes the displayed AUC match the deployment population, and it keeps the
model from being judged, or used, on patients whose outcome is mostly unobserved.

**(c) Within-phase reporting**: Section 2.3. Only early and later post-RT have enough events for interpretable AUCs.

### 2.6 What this means for the paper's phase-of-care claim

- The claim survives, and it is not an artefact of the marginal censoring weights. Under phase-dependent censoring the
  phase gain is larger (+0.124), not smaller. Excluding the patients with no RT documented still leaves +0.057.
- The claim should be qualified in three ways:
  - **About 30% of the gain comes from the RT-never-documented group.** Its outcome is mostly unobserved: 38 of 63 scans
    are censored, at a median of 0 days.
  - **Arbitrary informative censoring could erase the gain.** Under the bound where every censored scan progressed, it
    is −0.044.
  - **Phase information discriminates between phases only.** Within phases R2 does no better than R0
    (phase-stratified AUC 0.577 vs 0.595), and once RT has started the gain is +0.013.
- **Suggested change to the text.** Report the core model as C2 (0.678; 0.706 in all gliomas), or add C2 next to the
  core model. Report the IPCW AUC under phase-stratified censoring as a sensitivity (0.749), and the in-scope
  rt_pathway AUC (0.654 core / 0.625 C2). State that the intended use is patients on a documented RT pathway, and that
  scans without a documented treatment plan are flagged as out of scope.
