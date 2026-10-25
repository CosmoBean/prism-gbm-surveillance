# UCSF-ALPTDG: clinical table, sign conventions and label candidates

**Status: descriptive only.** No outcome model was fitted and no AUC was computed on UCSF. This note fixes how the
workbook is read and counts what each candidate label would give, so that the external analysis can be
prespecified next. Aggregate counts only; patient-level outputs stay under `outputs/data/ucsf/` (git-ignored).

Code: `prism/data/ucsf.py` (`PYTHONPATH=. .venv/bin/python -m prism.data.ucsf`), test `tests/test_ucsf.py`.
Outputs: `outputs/data/ucsf/scans.csv` (596 rows = 298 patients × 2 scans) and `outputs/data/ucsf/flags.csv`
(affected SubjectIDs and the action taken for each data problem).

## Source

UCSF-ALPTDG (UCSF adult longitudinal post-treatment diffuse glioma), downloaded under the DUA to
`/project/community/sbandred/ucsf/` (see `INVENTORY.md` there). Each patient has **one consecutive post-treatment
scan pair** (time1, time2) and one row in the `Clinical Info` sheet. The `Clinical_Dictionary` sheet is the only
documentation. It defines no progression criteria and no threshold for the volumetric change categories.

| | WHO 2021 GBM | grade 4 | all gliomas |
|---|---|---|---|
| patients | 80 | 140 | 298 |
| age, median (years) | 59.5 | 57.5 | 53 |
| male | 49 | 81 | 177 |
| IDH mutant / wildtype / unknown | 0 / 80 / 0 | 13 / 81 / 46 | 123 / 96 / 79 |
| MGMT methylated / unmethylated / unknown | 40 / 31 / 9 | 71 / 43 / 26 | 82 / 47 / 169 |
| days from diagnosis to scan 1, median (IQR) | 423 (253–587) | 424 (228–686) | 734 (331–2322) |
| days scan 1 → scan 2, median | 56 | 56 | 65 |
| progression date listed | 55 | 97 | 177 |
| death date listed | 56 | 86 | 123 |
| TRAIN / TEST (UCSF's split) | 65 / 15 | 114 / 26 | 248 / 50 |
| also in UCSF-PDGM | 39 | 59 | 60 |

The grade-4 group adds 44 "Glioma NOS", 9 IDH-mutant astrocytomas, 4 "IDH mut NOS", 2 gliosarcomas and 1 "Other" to
the 80 WHO GBM. The PDGM mapping sheet has 62 rows for 61 distinct IDs, one of which is not in the cohort.

## Sign conventions

The column names ("from X to Y") and the dictionary ("Y − X") often disagree. Every event is therefore re-expressed
as **days from scan 1 to the event, positive = after scan 1**, using the convention that the data support. Day
values are fractional (the dates carry a time of day).

| column | decision (stored value) | evidence |
|---|---|---|
| Days from 1st surgery/DX to 1st scan | scan 1 − first surgery; positive = surgery before scan 1 | 296/298 positive in a postoperative cohort; first surgery → RT start median 38 d (GBM 34 d, IQR 28–39), the standard post-surgical interval |
| Days from 1st scan to 2nd scan | scan 2 − scan 1 | all positive, 18–413 d |
| Days from 1st scan to next progression | progression − scan 1; positive = after | progression between the scans → ET "Increased" in 21/32 (66%); progression after scan 2 → 54/131 (41%); no progression listed → 22/121 (18%). Death is on or after progression in 102/102 patients with both |
| Days from death to 1st scan | scan 1 − death; negative = death after scan 1 (as the dictionary says) | 123/126 negative; death ≥ progression in 102/102; no death before scan 2. The 3 positives are artefacts (below) |
| Days from 1st scan to 1st RT start | RT start − scan 1; negative = RT before scan 1 (as the header's "neg = RT first" says) | surgery → RT 38 d median under this sign (1,125 d under the other); RT start equals the chemo start ±3 d in 187/240 (concomitant TMZ), and in 0/240 under the opposite sign. One RT starting 33 d after scan 1 is flagged "on RT" at scan 2 |
| Days from 1st chemo start to 1st scan | scan 1 − chemo start; positive = chemo before scan 1 | 268/278 positive; surgery → chemo median 38 d; matches RT start as above; 99/105 patients "on chemo" at scan 1 started before scan 1 |
| Days from 1st scan to 2nd / 3rd SX | scan 1 − surgery; positive = before scan 1 (as the dictionary says) | the 50 negative 2nd surgeries all have a progression date, 36 of them within 1 d of it (median difference 0); 90/95 positive values lie between the first surgery and scan 1; 2nd before 3rd in 36/36 pairs |
| Number of surgeries | **total listed**, not "prior to the first scan" as the dictionary says | 1 surgery → no 2nd-surgery date in 148/148; 2 → 2nd date present and 3rd blank in 108/110; 50 patients counted with ≥ 2 have the 2nd surgery after scan 1. Surgeries before scan 1 are recomputed (`n_surgeries_before_scan1`) |
| On tx at 1st / 2nd scan | c = chemo, rt = RT, n = none, as dictionary | consistent with the chemo dates above. Two patients are "on RT" at scan 2 more than 1.5 years after their first RT start (re-irradiation; only the first RT is dated) |

Progression dated before scan 1 (14 patients). In 10 of them it lies within 1 d before scan 1 and in 2 it lies about 6 d
before, which is a time-of-day or same-visit offset. These 12 are treated as **progression at scan 1** (tolerance 7 d).
The other 2 (65 d and about 10 years before scan 1) are an earlier progression after which the "next" progression is
unknown, so both their scans are excluded from every label.

## Data problems and rules

No scan is dropped from `scans.csv`. Problems are handled per value and listed by SubjectID in `flags.csv`
(31 patients, 40 flags).

| problem | patients | rule |
|---|---|---|
| \|days\| > 20,000: an empty date read as Excel day 0 (values 41,000–43,600 = the other date's serial) or a typo (328,372) | surgery 7, RT 9, chemo 12, death 3, 2nd surgery 1 | that day is set to NaN. The event stays listed (RT/chemo given, date unknown), except the 3 death values, which mean no death date |
| first surgery dated after scan 1 | 2 | diagnosis day set to NaN |
| RT start > 3 d before the first surgery | 4 (includes the 2 above) | kept and flagged; their diagnosis day is suspect |
| progression > 7 d before scan 1 | 2 | both scans excluded from labels |

## The per-scan table (`scans.csv`)

| column(s) | meaning |
|---|---|
| scan_id, subject_id, timepoint, scan_day | `<SubjectID>_time<1/2>` (same as the imaging features); scan_day = days from scan 1 |
| days_from_prev, has_prev | scan 2 only: the interval to scan 1. Scan 1 has no earlier scan in the dataset (it is not the first post-op scan) |
| split, in_pdgm | UCSF's TRAIN/TEST split; patient also in UCSF-PDGM |
| who2021, presumed_dx, grade, grade4, gbm_who, gbm_or_gliosarcoma | diagnosis and population flags |
| idh, mgmt (mutant/wildtype/unknown; methylated/unmethylated/unknown), mgmt_index, codel_1p19q, atrx | molecular markers |
| age, male | age at that scan (it differs between the two scans in 76 patients), sex |
| eor_first_surgery, n_surgeries_total, n_surgeries_before_scan1 | surgery history |
| days_from_diagnosis_to_mri | diagnosis = first surgery (or MRI diagnosis when there was no surgery, 2 patients) |
| rt_listed, days_from_rt_start_to_mri, rt_started, rt_phase | first RT start only; rt_phase below |
| chemo_listed, chemo_type (free text), days_from_chemo_start_to_mri, chemo_started | first chemo |
| on_tx, on_chemo, on_rt | the per-scan "on treatment" flag |
| progression_listed, days_to_progression | first progression after scan 1, relative to this scan (negative = before this scan) |
| death_listed, days_to_death, days_to_next_surgery | |
| inferred_follow_up_days | lower bound: the latest dated event after the scan (scan 2, progression, death, later surgery, RT or chemo start). There is no last-contact date |
| snfh_/et_change, *_inc_mm3, *_dec_mm3, *_overall_mm3 | volumetric change categories and volumes, scan 2 only (the duplicated ET header is read by position) |
| neg_class, pos_*, et_increased, label_excluded_prior_progression | label candidates below |

## Label candidates for detection at the scan

The MU definition is: positive = the first scan on or after the progression date; primary negative = a scan with a
verified 120-day non-event. Because each UCSF pair is consecutive, scan 2 is the first scan after a progression dated
in the interval. Candidates:

- **pos_s2_pm30 / pos_s2_pm60**: scan 2, progression within ±30 / ±60 d of scan 2 and nearer scan 2 than scan 1.
  The MU-style rule "first scan on or after progression, with up to 30 d of dating lag" gives exactly the same
  positives as ±30 in every population.
- **pos_s2_between**: scan 2, progression between scan 1 and 30 d after scan 2 (literal; it includes progressions
  dated just after scan 1).
- **pos_s1_at**: scan 1, progression dated at scan 1 (−7 to 0 d). **pos_s1_le30**: −7 to +30 d and nearer scan 1.
- **Negatives** (shared by all candidates; never on or after a progression):
  - *verified*: progression dated ≥ 120 d after the scan;
  - *followed*: no progression listed, and a dated event ≥ 120 d after the scan (73 scans; the evidence overlaps: scan 2 in
    44, death in 25, RT or chemo start in 5 each);
  - *follow-up unknown*: no progression listed, no evidence of 120 d of follow-up.
  - Primary = verified + followed.
- **et_increased**: scan 2 ET "Increased" vs "Unchanged/Decreased". It is defined on the images and so is circular
  for an image model. It is a secondary, imaging-defined reference only.

Positives / negatives / patients (patients with both a positive and a negative in brackets). Primary negatives
throughout, except in the last three rows.

| candidate | WHO GBM | grade 4 | all gliomas |
|---|---|---|---|
| **pos_s2_pm30** | **21 / 53 / 54 (0)** | **29 / 103 / 92 (0)** | **48 / 231 / 198 (3)** |
| pos_s2_pm60 | 25 / 53 / 58 (0) | 35 / 103 / 98 (0) | 59 / 231 / 205 (7) |
| pos_s2_between | 26 / 53 / 59 (0) | 39 / 103 / 102 (0) | 65 / 231 / 215 (3) |
| pos_s1_at | 4 / 53 / 37 (0) | 5 / 103 / 68 (0) | 12 / 231 / 165 (0) |
| pos_s1_le30 | 9 / 53 / 42 (0) | 15 / 103 / 78 (0) | 29 / 231 / 182 (0) |
| pos_s2_pm30 + pos_s1_at | 25 / 53 / 58 (0) | 34 / 103 / 97 (0) | 60 / 231 / 210 (3) |
| negatives: verified only | 35 | 78 | 158 |
| negatives: follow-up unknown (not in primary) | 32 | 61 | 169 |
| et_increased (scan 2) | 48 / 32 / 80 | 71 / 69 / 140 | 101 / 197 / 298 |

- Primary negatives by scan: WHO GBM 33 scan 1 + 20 scan 2; grade 4 63 + 40; all gliomas 153 + 78.
- Almost no patient contributes both a positive and a negative. In MU the scan before a progression scan is
  usually within 120 d of it, so here the scan-1 negatives come from patients whose progression comes much later or
  never.
- pos_s2_between minus pos_s2_pm30 is the progressions dated just after scan 1 (5 GBM, 10 grade 4, 17 all), which
  are ambiguous between the two scans.
- To keep the prespecification clean, labels were not cross-tabulated against image features. The one exception is
  the progression × ET-category table used above as sign-convention evidence (it is also in INVENTORY.md).

## Phase of care

UCSF gives only the first RT start: no end date and no dose. The phase is therefore *plausible*, assuming a 6-week
course: during RT = 0–41 d after the start; early post-RT = 42–125 d (within 12 weeks of an assumed RT end); later
post-RT = ≥ 126 d. MU's intended use is scans on or after the documented RT start.

| scans | WHO GBM (160) | grade 4 (280) | all gliomas (596) |
|---|---|---|---|
| intended use (on/after RT start) | 156 | 272 | 471 |
| no RT listed | 0 | 2 | 76 |
| RT given, start date unknown | 4 | 6 | 18 |
| pre-RT | 0 | 0 | 31 |
| plausibly during RT (0–41 d) | 1 | 1 | 3 |
| plausibly early post-RT (42–125 d) | 14 | 23 | 40 |
| later post-RT (≥ 126 d) | 141 | 248 | 428 |
| sensitivity: RT start 0–180 d before the scan | 28 | 46 | 73 |

Recommended candidate (pos_s2_pm30, primary negatives) by phase:
- WHO GBM: positives 19 later post-RT and 2 with RT date unknown; negatives 45 later post-RT and 8 early post-RT.
- Grade 4: positives 27 later and 2 unknown; negatives 89 later, 13 early and 1 unknown.

So UCSF is almost entirely later post-RT surveillance (median RT start → scan 1 is 383 d in GBM). It is close to the
one MU phase where every arm was about 0.62–0.64, and the phase-of-care contrast that drove MU's 0.82 timing baseline
is largely absent.

## Which PRISM features can be built

| feature (MU / LUMIERE) | UCSF | note |
|---|---|---|
| age, male, IDH, MGMT (clinical; C2 masking rules) | yes | IDH unknown in 79 patients (none in GBM), MGMT unknown in 169 (9 in GBM) |
| days_from_diagnosis | yes | diagnosis = first surgery/DX; 9 patients missing |
| log days since surgery (LUMIERE T) | yes | same quantity |
| rt_started, rt_start_day | yes | from the first RT start; 18 scans RT date unknown |
| chemo_started | yes | 24 scans unknown (12 date artefacts) |
| surgery_day | trivially 0 | diagnosis is defined as the first surgery |
| days_since_rt_end, rt_completed, rt_duration_days, rt_dose_gy, rt_fractions, rt_hypofractionated | **no** | no RT end, dose or fractions |
| early_post_rt (MU: ≤ 84 d after RT end; LUMIERE: rater flag) and its × MGMT term | **approximate only** | from RT start + an assumed 42-d course (`rt_phase`); 14 GBM scans fall in it |
| visit_index | **no** | scan 1 is not the first post-op scan, and the number of earlier scans is unknown |
| previous-scan change, days_from_prev, has_prev | scan 2 only | scan 1 has no earlier scan in the data (has_prev = 0, as on MU for the first scan, though its meaning differs) |
| nadir (smallest volume since RT end) | **no** | only two scans, no RT end |
| biopsy_before_resection, previous_brain_tumor | **no** | EOR at first surgery (incl. biopsy) is given instead |
| volumes and morphology | from the masks | computed by the imaging stage, not here |

The LUMIERE-transportable model T (clinical, log days since surgery, early post-RT flag, harmonised volumes and change
from the previous scan) is buildable. Its early post-RT flag would be the approximate RT-start window. Its change
features exist for scan 2 only. Full B1 (timing + treatment) is not: its RT-end, dose and visit-index inputs are
missing.

## Recommended primary label

**Positive = scan 2 with the first progression dated within ±30 d of it (and nearer scan 2 than scan 1); negative =
a scan with no progression for ≥ 120 d after it, either verified by a later progression date or with ≥ 120 d of
dated follow-up; population grade 4 (as on MU), WHO GBM as a sensitivity analysis. Intended use: scans on or after RT
start.** Reasons:

1. It is the MU rule (first scan on or after progression) applied to a consecutive pair, with a 30-d tolerance for
   dating lag. The MU-style "nearer scan 2, up to 30 d after" rule picks the same scans.
2. It is clinical, not image-defined, so it is not circular for an image model (unlike et_increased).
3. ±60 d and "between" add only 6–10 grade-4 positives, mostly progressions dated just after scan 1, where the scan
   that showed progression is ambiguous. They suit sensitivity analyses.
4. Scan-1 positives (pos_s1_at) add 5 grade-4 positives with no previous scan. They can be pooled as a sensitivity
   analysis.
5. Negatives with unknown follow-up (61 grade-4 scans) are excluded from the primary set, as on MU; they can form
   the secondary "all scans before progression" set.

Expected size: grade 4 29 positives / 103 negatives / 92 patients (WHO GBM 21 / 53 / 54). Positives are few, so the
external CIs will be wide. It is a two-scan, mostly later post-RT cohort: the external question is detection within
later surveillance, not across phases of care.
