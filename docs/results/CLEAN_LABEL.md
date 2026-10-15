# Clean-label test: is the documented-progression label the bottleneck for imaging?

Code: `prism/analyses/clean_label.py` (`python -m prism cleanlabel`). Outputs: `outputs/results/analyses/clean_label/`.

## 0. Why

On MU-Glioma-Post the clinical + timing + treatment ridge (the "baseline") reaches IPCW AUC(120 d) about 0.70 and
conventional-MRI imaging adds nothing over it (C3, phase ladder, deep features, re-segmentation). MU's event is
*documented first progression of any type*. MU codes the type of first progression: 1 = imaging criteria, 2 = clinical
findings only, 3 = both. A clinical-only progression is invisible to the images by construction, so it may dilute any
imaging signal. The existing label pipeline (`prism/data/mu.py`, `FIX_LABELS.md`) does **not** use the type: every
progressor is an event.

## 1. Analysis plan (pre-specified)

Written into this doc and the module docstring before any model of this module was run. A copy of this section was saved
to `outputs/results/analyses/clean_label/PLAN_snapshot.md` before the run. Anything added after the results is labelled
**EXPLORATORY**. Before the plan was fixed, only descriptive counts were looked at (how many events change type), no
model output.

**A. Imaging-defined endpoint (MU).** Same cohort, same scans, H = 120 d.

- Type 1 (imaging) or 3 (both): event, as now.
- Type 2 (clinical only): **not an event**. The scan is censored at the progression date (event = 0, time = days from
  scan to progression). At 120 d the label is 0 if the progression date is ≥ 120 d after the scan, otherwise censored.
- Non-progressors: unchanged.
- The type is read from `mu_index.csv` `clinical_type_of_1st_progression`; every progressor must have type 1/2/3
  (asserted).
- Reference: the current label ("original") with the same models.

**B. Feature sets** (`features.tabular`):

| Set | Blocks |
|---|---|
| clinical | age, sex, IDH, MGMT (+ unknown flags) |
| baseline | clinical + timing + treatment |
| imaging | volumes + delta (compartment volumes + past-only change) |
| baseline+imaging | baseline + volumes + delta |

**C. Models, populations, cohorts.** As in the phase ladder: ridge (primary) and C3 GBM (secondary). Grade 4 primary,
all gliomas secondary. Cohorts: full and post_rt (RT completed; definition and fold handling exactly as in
`PHASE_LADDER.md`).

**D. Evaluation.** Shared 5×5 repeated patient-grouped folds (`outputs/data/folds.csv`; stratified on the original
120-d status and kept unchanged so all arms share splits). IPCW AUC(120 d) = mean over repeats of each repeat's
pooled-OOF AUC (`evaluate_repeated`); censoring weights from the label's own event/time. Paired patient-cluster
bootstrap (1000) of ΔAUC vs baseline and vs clinical (same label, learner, cohort, population).

**E. Pre-specified rule.** "The label is the bottleneck" is **supported** if, on the imaging-defined endpoint, in
grade 4 (full cohort, ridge), imaging-only **or** baseline+imaging beats the baseline by **ΔAUC ≥ 0.03** with the paired
cluster-bootstrap **95% CI excluding 0**. Otherwise not supported. All other contrasts (post_rt, all gliomas, GBM,
original label, LUMIERE) are secondary, with no multiplicity correction. The rule itself has two chances (noted, not
corrected).

**F. LUMIERE.** `prism/data/lumiere.py` already defines the label from the expert RANO ratings
(`LUMIERE-ExpertRating-v202211.csv`): event = first rating of Progressive Disease within 120 d of the index scan, death
censors. So the requested expert-RANO forward label *is* the existing LUMIERE label. Instead we report imaging vs
clinical within LUMIERE-only CV:

| Set | Features |
|---|---|
| clinical | age, sex, IDH, MGMT (+ unknown flags) |
| clinical+timing | + log days since surgery, rater's "< 3 months after RT" flag (no treatment dates exist; baseline analogue) |
| imaging | DeepBraTumIA volumes (ET, necrosis/cavity, oedema) + delta vs the previous post-operative study (week ≥ 1) with a usable segmentation: has_prior, log days since prior, log ratios of the 3 compartments and their sum |
| clinical+timing+imaging | all of the above |

Ridge primary, GBM secondary; 5×5 patient-grouped LUMIERE folds (`external_lumiere.lumiere_fold_ids`); same estimator
and bootstrap as MU. Small n (61 patients): CIs reported, descriptive only.

## 2. Cohorts and label change

Source: `counts.csv`. Run time 64 s on 16 workers (`run_info.json`).

| Label · population · cohort | Scans | Patients | Events (type 1 / 2 / 3) | Non-events | Censored |
|---|---|---|---|---|---|
| original · grade 4 · full | 249 | 126 | 93 (44 / 12 / 37) | 117 | 39 |
| **imaging · grade 4 · full** | 249 | 126 | **81** (44 / 0 / 37) | 117 | 51 |
| original · grade 4 · post_rt | 167 | 84 | 83 (41 / 7 / 35) | 83 | 1 |
| imaging · grade 4 · post_rt | 167 | 84 | 76 (41 / 0 / 35) | 83 | 8 |
| original · all gliomas · full | 308 | 155 | 100 (48 / 15 / 37) | 156 | 52 |
| imaging · all gliomas · full | 308 | 155 | 85 (48 / 0 / 37) | 156 | 67 |
| original · all gliomas · post_rt | 185 | 92 | 84 (42 / 7 / 35) | 96 | 5 |
| imaging · all gliomas · post_rt | 185 | 92 | 77 (42 / 0 / 35) | 96 | 12 |

Clinical-only progression is a small part of the events: 12 of 93 grade-4 events (10 patients). All 12 become
censored; no non-event changes (every type-2 scan with label 0 already had its progression > 120 d away). Every
progressor in the cohort has a type of 1, 2 or 3 (assertion passed).

**Sanity check.** On the original label, the ridge numbers reproduce `PHASE_LADDER.md` exactly: grade 4 full clinical
0.585, baseline 0.698; grade 4 post_rt baseline 0.604.

## 3. Primary result (pre-specified rule)

Source: `results.csv` (reference = baseline) and `rule.json`. Imaging-defined endpoint, grade 4, full cohort, ridge.

| Model | IPCW AUC (95% CI) | ΔAUC vs baseline (95% CI) | Calibration slope |
|---|---|---|---|
| clinical | 0.563 (0.474–0.642) | −0.133 (−0.227, −0.054) | 0.75 |
| baseline (clinical + timing + treatment) | 0.696 (0.610–0.776) | — | 0.97 |
| imaging (volumes + delta) | 0.628 (0.549–0.701) | −0.068 (−0.167, +0.033) | 0.72 |
| **baseline + imaging** | 0.722 (0.639–0.799) | **+0.027 (−0.033, +0.082)** | 0.90 |

**Rule: NOT met.** Neither imaging arm beats the baseline by ≥ 0.03 with a CI excluding 0. The best case,
baseline + imaging, gains +0.027 and its CI includes 0. "The label is the bottleneck" is **not supported**.

**Direction.** Cleaning the label moves imaging the expected way, but by little:

| Grade 4, full, ridge | Original label | Imaging-defined label |
|---|---|---|
| imaging only | 0.600 | 0.628 |
| baseline | 0.698 | 0.696 |
| baseline + imaging | 0.694 (Δ −0.004, CI −0.060 to +0.051) | 0.722 (Δ +0.027, CI −0.033 to +0.082) |
| imaging only vs clinical | +0.015 (−0.106, +0.141) | +0.065 (−0.046, +0.167) |

The imaging gain over the baseline moves from about 0 to about +0.03. That shift is of the size that the removal of
12 events and a different censoring pattern can produce by chance; the two labels are not compared formally (no paired
test across labels was pre-specified).

## 4. Secondary results

Source: `results.csv`. ΔAUC vs baseline (95% CI). No CI below excludes 0.

| Label · population · cohort | Learner | Baseline AUC | imaging Δ | baseline + imaging Δ |
|---|---|---|---|---|
| imaging · grade 4 · full | GBM | 0.702 | −0.080 (−0.190, +0.030) | +0.026 (−0.037, +0.091) |
| imaging · grade 4 · post_rt | ridge | 0.598 | −0.026 (−0.149, +0.082) | +0.027 (−0.055, +0.102) |
| imaging · grade 4 · post_rt | GBM | 0.634 | −0.041 (−0.181, +0.104) | +0.021 (−0.063, +0.107) |
| imaging · all gliomas · full | ridge | 0.744 | −0.090 (−0.176, −0.007) | +0.008 (−0.036, +0.049) |
| imaging · all gliomas · full | GBM | 0.733 | −0.068 (−0.163, +0.034) | +0.021 (−0.027, +0.075) |
| imaging · all gliomas · post_rt | ridge | 0.650 | −0.055 (−0.170, +0.060) | +0.012 (−0.057, +0.083) |
| imaging · all gliomas · post_rt | GBM | 0.665 | −0.042 (−0.163, +0.076) | +0.028 (−0.045, +0.104) |
| original · grade 4 · post_rt | ridge | 0.604 | −0.060 (−0.181, +0.048) | +0.016 (−0.058, +0.083) |
| original · all gliomas · full | ridge | 0.720 | −0.076 (−0.164, +0.014) | +0.007 (−0.037, +0.047) |

(The all-gliomas imaging-only Δ of −0.090 has a CI excluding 0 in the *negative* direction: imaging alone is worse
than the baseline.)

- **Post-RT.** With the imaging-defined label, grade-4 post-RT baseline + imaging reaches 0.625 vs 0.598 for the
  baseline (+0.027, CI −0.055 to +0.102), against +0.016 on the original label. Same picture: a small move in the
  expected direction, CI wide.
- **Imaging vs clinical** (reference = clinical). Imaging alone does not beat clinical alone in any cohort
  (grade 4 full ridge +0.065, −0.046 to +0.167). Every model that includes timing + treatment beats clinical in the
  full cohorts.

## 5. LUMIERE (expert RANO label, within-LUMIERE CV)

`prism/data/lumiere.py` already uses the expert RANO ratings as the label (event = first PD rating within 120 d). So no
new label was built; this is imaging vs clinical within LUMIERE. Source: `lumiere_results.csv`. 132 scans, 61 patients,
47 events, 9 censored.

| Model (ridge) | IPCW AUC (95% CI) | Δ vs clinical + timing (95% CI) | Calibration slope |
|---|---|---|---|
| clinical | 0.313 (0.256–0.380) | −0.153 (−0.225, −0.097) | −2.37 |
| clinical + timing | 0.466 (0.389–0.568) | — | −0.08 |
| imaging (volumes + delta) | 0.373 (0.301–0.458) | −0.094 (−0.198, +0.001) | −2.13 |
| clinical + timing + imaging | 0.421 (0.338–0.522) | −0.046 (−0.102, +0.007) | −0.57 |

GBM: clinical 0.473, clinical + timing 0.563, imaging 0.428, clinical + timing + imaging 0.516; imaging vs
clinical + timing −0.135 (−0.242, −0.034).

**Every within-LUMIERE model is at or below chance, with negative calibration slopes.** This is the small-sample
anti-learning seen in the phase ladder's later_post_rt cohort: models with no real signal, trained on 4/5 of 61
patients, predict opposite to the held-out fold's class balance. The pooled-OOF estimator used here is harsher than
the per-fold mean in `EXTERNAL_LUMIERE.md` (LUMIERE-only clinical ridge 0.396 per fold vs 0.313 pooled), but both say the
same: 61 patients are too few to train a model from scratch. **The LUMIERE arm cannot answer the label question;**
it shows neither imaging nor clinical features can be learned within LUMIERE.

## 6. Conclusion

- **Pre-specified rule not met.** On MU's imaging-defined endpoint (clinical-only progression censored), imaging adds
  +0.027 (95% CI −0.033 to +0.082) to clinical + timing + treatment in grade 4, and imaging alone is 0.068 below the
  baseline. The documented-progression label is **not shown to be the bottleneck**.
- The clean label is only modestly cleaner: 12 of 93 grade-4 events are clinical-only. Type 1 and type 3 events still
  depend on a clinician calling progression from the images, the timing of the next scan, and treatment decisions.
  The test therefore removes the most obvious label noise, not all of it. An expert per-scan RANO re-read of MU would
  be the stronger test; LUMIERE has such a label but is too small to learn from.
- Point estimates move consistently in imaging's favour after relabelling (+0.03 in grade 4 full and post-RT). This is
  compatible with a small real effect, or with noise; these data cannot tell the two apart.
