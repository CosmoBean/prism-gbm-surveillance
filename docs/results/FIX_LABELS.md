# Label and cohort fixes (manuscript week, 2026-10-11)

Code: `prism/data/mu.py`, `prism/data/lumiere.py`, `prism/models/formulations.py`.
Tests: `tests/test_label_fixes.py` (new), `tests/test_labels_and_folds.py` (updated). `python -m unittest discover -s tests`: 27 tests, all pass.
"Before" means the frozen tables in `outputs/data/` (= `outputs/results_pre_fix_2026-10-11` inputs). "After" was produced with
`PRISM_OUTPUTS=<scratch>/out-labels python -m prism mu --reuse-index` and `python -m prism lumiere`. The coordinator
regenerates `outputs/data/*` (cohorts, flow, **folds**) when everything is re-run. Folds change because the 120-day
stratification labels change.

## Estimand

- **Primary:** documented first progression within H = 120 d of the index scan (90 / 180 d as sensitivities). Death
  without documented progression is **censoring** at the death day, not an event and not a verified negative
  (`label_{H}`, `event`, `time_to_event`; IPCW AUC(H) treats it like any other loss to follow-up). Label 0 needs
  progression-free follow-up ≥ H.
- **Sensitivity:** composite event = progression **or death** within H (`label_{H}_composite`, `event_composite`,
  `time_to_event_composite`; `prism.analyses.sensitivity` variant `composite`). It answers a different question (any
  bad outcome) and is reported only as a sensitivity.
- **LUMIERE:** the demographics give a survival time (56/61 patients) but no death/censoring indicator. A recorded
  survival time is read as a death, so the LUMIERE composite is **not** identical to the primary label: at 120 d it
  has 51 positives / 5 censored vs 47 / 9 (table below; 4 scans whose patient died within 120 d without PD). If some
  survival times are in fact censoring times, the LUMIERE composite over-counts deaths; the primary label uses the
  survival time only as a censoring time. All external (LUMIERE) results use the primary label.

## Rules

| # | Problem (audit) | Rule now | Columns |
|---|---|---|---|
| 1 | Death without documented progression was a verified negative at every horizon (`status_known_indefinitely`) | **Primary: death censors** at the death day (death from an unknown or competing cause). Non-progressors: follow-up = death day if dead, else the last documented day. `status_known_indefinitely` is kept but always `False`. **Sensitivity:** composite event = progression or death. Label 0 needs progression after H, or progression-free follow-up ≥ H. A death after H on its own does not verify the absence of progression | `label_{H}`, `event`, `time_to_event`; `label_{H}_composite`, `event_composite`, `time_to_event_composite`, `death_day`, `death_without_progression` |
| 1b | MRIs dated after the recorded death (15/96 MU deaths have an MRI after the death day) | An MRI or a progression assessment needs a living patient. If **more than one** dated record (MRIs plus the first-progression date) falls after the death day, the **death date is treated as the error**: it is ignored (`death_date_conflict`), the scans are kept and the patient is censored at the last record. This applies to 7 patients (0031, 0034, 0042, 0044, 0065, 0074, 0145), and 3 of them have cohort scans (0044, 0065, 0145). If exactly **one** record falls after death, that scan is **excluded** (flow step "MRI not after recorded death"). The same rule applies in LUMIERE | `death_date_conflict`, `after_recorded_death` |
| 2 | `clinical_progression = 0` with a progression date (0004, 0013, 0196). Two date fields disagree in 29 patients | **Any patient with a progression date is a progressor.** Primary date = `date_of_first_progression`, with fallback `time_to_first_progression_days`. **Sensitivity:** the reverse order (`progression_day_alt`). The cohort is unchanged, and the alt label is NaN when the alt date is on or before the scan (6 scans) | `progression_flag_conflict`, `progression_day_alt`, `label_{H}_altdate` |
| 3 | 0081 TP2 MRI day −965 (it was in the cohort as a positive's scan with t = 989 d). Progressors who died before progression | New flow step: MRI day ≥ −365 and not earlier than an earlier timepoint (excludes only 0081 TP2). Death before progression is flagged. 0145 was the only case, and its death date is now ignored by rule 1b, so 0 cohort scans remain. `prism mu` prints a consistency report and asserts that no cohort scan postdates a used death date and that all times are > 0 | `death_before_progression` |
| 4 | Hazard person-period counted a scan censored mid-interval as surviving the whole interval | Censored scans contribute **only fully observed intervals** (censoring exactly at an interval edge counts as observed). Events contribute up to and including the event interval | `formulations.person_period` |
| 5 | Follow-up extended by non-imaging dates (therapy dates, etc.) | Kept as primary (the clinical record documents progression status, not only the images). **Sensitivity:** follow-up measured from MRIs only, capped at death. This affects 23 non-progressor scans, with a median of 81 extra days | `follow_up_days`, `follow_up_imaging_days`, `label_{H}_imgfu` |
| 6 | MU coded unknown RT end as `early_post_rt = 0` | `early_post_rt` is now 1/0/**NaN**. It is NaN when the RT end date is unknown: 94 scans, 65 grade 4. Most of these patients have no RT documented (`clinical_radiation_therapy` missing). The feature pipelines impute in-fold, and `tabular.timing` already has `rt_date_unknown`. LUMIERE keeps the rater's "LessThan3Months" flag (< ~90 d after RT, judged by the rater), while MU uses 0–84 d after the RT end date. The definitions differ, and this is documented, not harmonised | `early_post_rt` |

LUMIERE: survival weeks (demographics) are taken as days since surgery × 7, which is the same origin as the rating weeks. 56/61
cohort patients have a survival time, and there is no censoring indicator. Non-PD follow-up = min(last rating, death), so the
imaging follow-up is not extended to death. LUMIERE progression comes only from ratings, so PD between the last rating and death
would go unseen. Patient-073 has its death date ignored (>1 later rating). Patients 041, 083 and 086 each have one rating after
death, and none of those ratings is an index scan. `label_{H}_altdate` and `label_{H}_imgfu` equal `label_{H}` in LUMIERE (one
progression source, and the follow-up is imaging-only already).

## Cohort flow (MU-Glioma-Post)

| step | before: scans / patients (excl.) | after: scans / patients (excl.) |
|---|---|---|
| all timepoints | 596 / 203 | 596 / 203 |
| all four sequences and mask present | 594 / 203 (2) | 594 / 203 (2) |
| tumour (labels 1-3) present | 592 / 203 (2) | 592 / 203 (2) |
| MRI day known | 589 / 202 (3) | 589 / 202 (3) |
| MRI day plausible (≥ −365 d, in timepoint order) | — | 588 / 202 (1) |
| progression date known for progressors | 589 / 202 (0) | 588 / 202 (0) |
| MRI not after recorded death | — | 580 / 202 (8) |
| before late treatment | 508 / 199 (81) | 501 / 199 (79) |
| before first progression (index scans) | **314 / 157** (194) | **308 / 155** (193) |

Six scans left the cohort and none entered:
- 0081 TP2 (implausible MRI day).
- 0099 TP2 and 0212 TP3 (the single scan after death; the other 6 scans of the 8 in that step would have been excluded later anyway).
- 0004 TP1 and 0013 TP2 (on the progression day of a former "flag 0" patient).
- 0196 TP3 (after the progression date of a former "flag 0" patient).

Grade 4: 253/128 → 249/126.

## Label counts (positive / verified negative / censored)

| population | label | scans/patients | H = 90 | H = 120 | H = 180 |
|---|---|---|---|---|---|
| all | before | 314/157 | 65 / 214 / 35 | 99 / 178 / 37 | 143 / 129 / 42 |
| all | **after: primary** (`label_H`) | 308/155 | 65 / 195 / 48 | 100 / 156 / 52 | 144 / 105 / 59 |
| all | after: composite | 308/155 | 79 / 195 / 34 | 116 / 156 / 36 | 161 / 105 / 42 |
| all | after: alt. progression date | 308/155 | 63 / 191 / 54 | 99 / 151 / 58 | 141 / 102 / 65 |
| all | after: imaging-only follow-up | 308/155 | 65 / 187 / 56 | 100 / 149 / 59 | 144 / 99 / 65 |
| grade 4 | before | 253/128 | 62 / 168 / 23 | 92 / 136 / 25 | 130 / 96 / 27 |
| grade 4 | **after: primary** | 249/126 | 62 / 152 / 35 | 93 / 117 / 39 | 131 / 75 / 43 |
| grade 4 | after: composite | 249/126 | 74 / 152 / 23 | 107 / 117 / 25 | 146 / 75 / 28 |
| grade 4 | after: alt. progression date | 249/126 | 60 / 149 / 40 | 92 / 113 / 44 | 128 / 73 / 48 |
| grade 4 | after: imaging-only follow-up | 249/126 | 62 / 147 / 40 | 93 / 113 / 43 | 131 / 72 / 46 |

The 308 scans common to both versions, at H = 120, compared with before:
- 17 negatives became censored. 16 are deaths without progression within 120 d (this includes 0099 TP1), and 1 is 0044 TP6 (death date ignored, no follow-up after the scan).
- 1 negative became positive: 0013 TP1, a former "flag 0" patient who progressed 98 d after the scan.
- No positive changed.

At H = 90 and H = 180 there were 15 and 19 negatives → censored, and 0 and 1 negatives → positive.

Death without progression now affects 22 cohort scans (20 grade 4), and 16 of these die within 120 d of the scan. The audit counted
32 on the old cohort. The difference comes from the 0044 death date being ignored, the dropped scans and 0013 becoming a progressor.

Alternative date source at 120 d: 11 scans differ from primary, of which 5 flip between positive and negative and 6 move between labelled and NaN. In 6 scans the alt date falls on or before the scan.
Imaging-only follow-up at 120 d: 7 scans go from negative to censored.

LUMIERE (132 scans / 61 patients, unchanged cohort):

| label | H = 90 | H = 120 | H = 180 |
|---|---|---|---|
| before | 24 / 101 / 7 | 47 / 77 / 8 | 62 / 61 / 9 |
| after: primary | 24 / 101 / 7 | 47 / 76 / 9 | 62 / 61 / 9 |
| after: composite | 26 / 101 / 5 | 51 / 76 / 5 | 66 / 61 / 5 |

The one LUMIERE change at 120 d: Patient-083 week-002 (0 → censored; death at day 133, 119 d after the scan).

## Other data issues logged (not changed)

- PatientID_0116 is recorded as dead with no death day. The death is not used, and the patient is censored at the last record.
- MU death dates look unreliable overall: 15/96 deaths have an MRI after the death day. This is one more reason to keep death as
  censoring in the primary analysis rather than as a verified outcome.
- The hazard fix only changes the training rows of the `hazard` formulation. IPCW weights and evaluation (`metrics.py`) still read
  `event`, `time_to_event` and `status_known_indefinitely`, which now encode death as censoring.
