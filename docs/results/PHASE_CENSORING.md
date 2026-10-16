# Phase of care vs censoring: is the phase-of-care finding a loss-to-follow-up artefact?

Code: `prism/analyses/phase_censoring.py` (`python -m prism phasecens`). Outputs:
`outputs/results/analyses/phase_censoring/`. Pipeline test on permuted outcomes:
`outputs/results/analyses/phase_censoring_shuffled<seed>/` (not results).

Status: **STEP 1** (plan, code, descriptives). No model has been fitted or scored on the real labels by this module.

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

Suggested Table 1 wording: "unknown 65 (63 with no RT documented, 2 with RT end date missing)". The phase analysis has
no unknowns: the 63 scans are pre-RT and the 2 are during RT.

## 2. Results

Not run yet (STEP 2, after GO).
