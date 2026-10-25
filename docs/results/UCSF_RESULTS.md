# UCSF-ALPTDG: external test results

Plan: [UCSF_PLAN.md](UCSF_PLAN.md) (pre-specified, 0e7c9fe). Data: [UCSF_DATA.md](UCSF_DATA.md), [UCSF_IMAGING.md](UCSF_IMAGING.md). Aggregate results only; patient-level files stay under `outputs/` (git-ignored).

## Part A

Locked MU models, applied once to UCSF with no refit. Code: `prism/analyses/ucsf_external.py`
(`PYTHONPATH=. .venv/bin/python -m prism.analyses.ucsf_external`, about 3 min on 6 CPUs). Outputs:
`outputs/results/analyses/ucsf/locked/`: auc.csv, contrasts.csv, calibration.csv, questions.csv, scores.csv,
coefficients.csv, checks.csv, single_input_auc_primary.csv, run_info.json. Plan: [UCSF_PLAN.md](UCSF_PLAN.md) (0e7c9fe).

**How the models were locked.** Each arm was fitted once on the MU detection training rows of
`detection.context(pop, "primary")`: positives plus primary negatives, all phases. That is 181 rows (35% positive)
in grade 4 and 229 rows (32% positive) in all gliomas. The pipeline is the LUMIERE locked test's: `c3.BASE_PRE`
(median imputation with missing indicators, then scaling) and the verified ridge (`c3._ridge`, seed 0). All imputation
values and indicators come from MU. Grade-4 models were used for the grade-4 and GBM sets, and all-glioma models
for the all-glioma set.

**Checks, made before any UCSF label was read** (`checks.csv`, all exact):
- The UCSF image builder (`ucsf_imaging.model_inputs`), run on the MU measurement pool, reproduces the MU A-Iscan,
  A-Ipure and A-Timg designs (max deviation 0, same missingness).
- A-B0, A-T and A-Tbase equal `detection.context`'s B0, T and Tbase.
- The locked-fit code reproduces the LUMIERE locked AUCs (T 0.7729, Tbase 0.6892).
- On UCSF, every arm's columns equal MU's in name and order, and this is asserted, including at the fitted
  imputer/scaler.

### Primary: grade 4, scan 2, `pos_s2_pm30` vs primary negatives (29 positives / 40 negatives / 69 patients)

| arm | AUC (95% CI) | calibration slope (95% CI) | O/E (95% CI) |
|---|---|---|---|
| A-B0 (clinical) | 0.502 (0.364–0.630) | 1.11 (−3.72 to 5.28) | 1.17 (0.88–1.54) |
| A-Iscan | **0.795 (0.686–0.887)** | 2.20 (1.34–3.46) | 1.12 (0.86–1.41) |
| **A-Ipure** | **0.726 (0.603–0.835)** | 0.85 (0.44–1.43) | 1.24 (0.93–1.58) |
| A-B0+Iscan | 0.788 (0.676–0.880) | 2.20 (1.34–3.48) | 1.12 (0.85–1.41) |
| A-B0+Ipure | 0.750 (0.630–0.854) | 1.29 (0.76–2.06) | 1.18 (0.89–1.48) |
| A-Timg (LUMIERE image set) | 0.889 (0.811–0.955) | 5.69 (3.86–9.34) | 1.19 (0.91–1.51) |
| A-Tbase (approximate) | 0.561 (0.420–0.687) | 0.37 (−0.39 to 1.28) | 0.67 (0.50–0.88) |
| A-T (approximate) | 0.856 (0.758–0.930) | 3.29 (1.96–6.28) | 0.72 (0.55–0.91) |

Pre-specified paired contrasts (ΔAUC, 95% CI):

| contrast | primary | WHO GBM | later post-RT |
|---|---|---|---|
| A-B0+Ipure − A-B0 (images over clinical) | **+0.248 (+0.096 to +0.392)** | +0.252 (+0.047 to +0.457) | +0.232 (+0.081 to +0.384) |
| A-T − A-Tbase (images over the transportable timeline) | +0.295 (+0.167 to +0.432) | +0.367 (+0.167 to +0.548) | +0.311 (+0.159 to +0.457) |
| A-Ipure − A-Iscan (change features) | −0.069 (−0.126 to −0.014) | −0.052 (−0.117 to +0.003) | −0.068 (−0.128 to −0.017) |

**Decisions fixed in advance.**
- **Q1, do MU image measurements transport? Yes.** A-Ipure reaches 0.726 (0.603–0.835), so AUC ≥ 0.65 and the
  lower bound is above 0.5. No image arm is flagged for transport failure (AUC < 0.65).
- **Q2, do images add to clinical data without a timeline? Yes.** A-B0+Ipure − A-B0 = +0.248 (+0.096 to +0.392).
  The clinical model alone is at chance (0.502), as on MU (0.530).

Reading:
- The locked image models do at least as well on UCSF as inside MU. MU cross-validated figures, grade 4, intended
  use: I_scan 0.659 and I_pure 0.709; later post-RT 0.655 and 0.650.
- UCSF is almost all later post-RT: 65 of the 69 primary scans, plus 2 early post-RT and 2 with the RT date unknown.
  So these AUCs are within-phase detection, the comparison where MU's timeline had no advantage.
- The change features did not transport as well as the single-scan inputs. A-Ipure falls 0.07 below A-Iscan, and
  the CI excludes 0 in grade 4.
  - UCSF change is about 3–6 times narrower than MU change ([UCSF_IMAGING.md](UCSF_IMAGING.md)).
  - The UCSF "history" is a single earlier scan.
- A-Timg (6 inputs) does best: 0.889.
- Calibration (secondary):
  - O/E is about 1.1–1.2 for the image arms. UCSF prevalence is 42%; MU training prevalence is 35%.
  - Slopes well above 1 for A-Iscan and A-Timg mean the predictions are too compressed on UCSF. They rank well but
    understate the spread.
  - A-T and A-Tbase overpredict (O/E about 0.7). UCSF grade-4 scan 2 lies much later after surgery (median 474 d)
    than the MU detection training rows (median 174 d), so log days since surgery extrapolates.

### Sensitivity and secondary sets (AUC, 95% CI)

| set (pos/neg/patients) | A-B0 | A-Iscan | A-Ipure | A-B0+Ipure | A-Timg | A-Tbase | A-T |
|---|---|---|---|---|---|---|---|
| WHO GBM, scan 2 (21/20/41) | 0.495 (0.316–0.682) | 0.793 (0.635–0.920) | 0.740 (0.560–0.887) | 0.748 (0.579–0.887) | 0.888 (0.765–0.964) | 0.464 (0.272–0.657) | 0.831 (0.677–0.943) |
| `pos_s2_between` (39/40/79) | 0.512 (0.386–0.639) | 0.783 (0.676–0.884) | 0.707 (0.587–0.822) | 0.733 (0.613–0.841) | 0.881 (0.800–0.944) | 0.572 (0.430–0.696) | 0.847 (0.754–0.923) |
| verified-only negatives (29/33/62) | 0.525 (0.386–0.662) | 0.798 (0.673–0.899) | 0.739 (0.602–0.852) | 0.764 (0.631–0.869) | 0.916 (0.840–0.972) | 0.562 (0.414–0.706) | 0.871 (0.775–0.946) |
| later post-RT subset (27/38/65) | 0.533 (0.384–0.673) | 0.803 (0.696–0.897) | 0.735 (0.614–0.843) | 0.765 (0.644–0.865) | 0.904 (0.821–0.966) | 0.561 (0.418–0.704) | 0.872 (0.776–0.945) |
| all scans, `pos_s2_pm30` + `pos_s1_at`, single-scan inputs (34/103/97) | 0.545 (0.434–0.661) | 0.795 (0.694–0.868) | – | – | – | – | – |
| all gliomas, scan 2, all-glioma models (48/78/126) | 0.553 (0.452–0.659) | 0.724 (0.620–0.812) | 0.747 (0.655–0.826) | 0.733 (0.640–0.818) | 0.801 (0.716–0.880) | 0.567 (0.464–0.666) | 0.801 (0.718–0.875) |
| *reference only:* `et_increased`, scan 2 (71/69/140) | 0.527 (0.435–0.619) | 0.830 (0.764–0.893) | 0.803 (0.728–0.871) | 0.823 (0.756–0.889) | 0.879 (0.826–0.929) | 0.521 (0.428–0.615) | 0.761 (0.687–0.833) |

- All-scans set: A-B0+Iscan 0.796 (0.696–0.872).
- A-B0+Iscan tracks A-Iscan within 0.01 in every scan-2 set (auc.csv).
- Every sensitivity set gives the same answers to Q1 and Q2. A-B0+Ipure − A-B0 runs from +0.18 to +0.25, and its
  CI excludes 0 in all of them (contrasts.csv).
- In all gliomas, A-Ipure − A-Iscan is +0.022 (−0.017 to +0.071).
- `et_increased` is defined on the images, so it is an upper reference and not a result.

### EXPLORATORY (not in the plan): single locked inputs on the primary set

These are univariable AUCs (`single_input_auc_primary.csv`):
- log ET volume 0.878, log ET max axial area 0.867, log tumour volume 0.876, log oedema 0.834;
- ET ratio to the previous scan 0.822, ET ratio to the history minimum 0.839;
- every clinical input 0.40–0.49; log days since surgery 0.542;
- log days since the previous scan 0.281: positives have shorter scan-1 to scan-2 intervals.

On UCSF, enhancing-tumour burden at scan 2 carries most of the signal. One raw volume does about as well as the
locked multivariable models. The UCSF progression date is a clinical call that was probably made largely from these
same scans, so part of this agreement may be built in. The progression definition is not documented
([UCSF_DATA.md](UCSF_DATA.md)).

### Deviations and decisions (Part A)

None of these needed a council: each follows from "same quantity as on MU" or from the plan's wording.
1. **Age.** MU `age` is age at diagnosis; UCSF gives age at each scan in integer years. UCSF age at diagnosis was
   computed as age at scan 1 − (days from diagnosis to scan 1) / 365.25, constant within a patient. Where the
   diagnosis day is missing, age at scan 1 was used.
2. **Days since surgery (A-Tbase / A-T).** This is UCSF `days_from_diagnosis_to_mri`, because diagnosis is the first
   surgery, so it is the same quantity as MU's. One primary scan has none and gets the locked MU median.
3. **Early post-RT flag (A-Tbase / A-T).** It is 1 for 42–125 d after the first RT start (`rt_phase` =
   early_post_rt: an assumed 6-week course + 84 d), otherwise 0. The flag is also 0 when there is no RT or the RT
   date is unknown; MU's as-of flag is never missing either. It is 1 in only 2 of the 69 primary scans.
4. **A-T previous-scan inputs.** `has_prev` = 1 and `log_days_from_prev` = log1p(UCSF days from scan 1) on every
   scan-2 row, so `has_prev` is constant in all scan-2 sets. The all-scans set uses only A-B0, A-Iscan and
   A-B0+Iscan, as the plan says.
5. **History truncation (A-Ipure / A-Timg).** The previous scan is scan 1, and the history minimum is min(scan 1,
   scan 2), as stated in the plan and in UCSF_IMAGING.md.
6. **Imputation.** ET-dependent morphology and intensity inputs are missing in 37% of UCSF scans (no ET) and in 6%
   of MU scans. They are filled with MU training medians, plus MU-learned missing indicators, inside the locked
   pipeline. This was not changed for UCSF.
7. **Calibration.** Calibration-in-the-large (in calibration.csv) is an addition. CIs use the same patient
   bootstrap and seed.
8. **Added outputs (EXPLORATORY):** the univariable input AUCs and the coefficient table. Neither enters Q1 or Q2.

## Part B

**Models trained on UCSF (internal).** Code: `prism/analyses/ucsf_internal.py`
(`PYTHONPATH=. .venv/bin/python -m prism.analyses.ucsf_internal`, about 3 min on 6 CPUs). Outputs:
`outputs/results/analyses/ucsf/internal/`: auc.csv, contrasts.csv, within_phase.csv, counts.csv,
split_variance.csv, permutation_control.csv, q3_b_minus_a.csv, oof.csv.gz, ucsf_split_scores.csv.gz, run_info.json.

**Method (as planned).**
- Pipeline: the verified ridge of `prism.analyses.detection` (`c3.fit_predict(c3.BASELINES[0])`), which picks C by
  inner patient-grouped CV. Each model is trained on the evaluation set of its analysis.
- Cross-validation: patient-grouped and label-stratified, 5 × 5 (`StratifiedGroupKFold`, seed 20261025 + repeat). The
  seeds were fixed in code before the run.
- AUC is the mean over repeats of the pooled out-of-fold AUC. CIs and paired contrasts come from a patient-cluster
  bootstrap: 1,000 draws, seed 20261025.
- In the scan-2 sets each patient contributes one row.

**The sets are small.** Primary: 29 positives and 40 negatives. WHO GBM: 21 and 20. The all-glioma scan-2 set
(48 / 78) gives the most stable estimate.

### Scan 2, `pos_s2_pm30` vs primary negatives (AUC, 95% CI)

| arm | **grade 4, PRIMARY (29/40/69)** | **all gliomas (48/78/126)** | WHO GBM (21/20/41) |
|---|---|---|---|
| B0 (clinical) | 0.407 (0.314–0.494) | 0.568 (0.475–0.666) | 0.402 (0.283–0.521) |
| B-Tl (UCSF timeline) | 0.669 (0.549–0.784) | 0.634 (0.544–0.719) | 0.581 (0.418–0.729) |
| Iscan | 0.826 (0.729–0.909) | 0.794 (0.714–0.872) | 0.770 (0.617–0.889) |
| **Ipure** | **0.863 (0.772–0.934)** | **0.855 (0.785–0.918)** | 0.789 (0.644–0.905) |
| B0+Iscan | 0.813 (0.721–0.901) | 0.795 (0.715–0.874) | 0.760 (0.597–0.887) |
| B0+Ipure | 0.860 (0.774–0.931) | 0.854 (0.782–0.917) | 0.783 (0.642–0.898) |
| Timg | 0.913 (0.843–0.967) | 0.905 (0.846–0.953) | 0.889 (0.780–0.966) |
| B-Tl+Ipure | 0.871 (0.790–0.938) | 0.859 (0.792–0.919) | 0.783 (0.638–0.905) |

Pre-specified paired contrasts (ΔAUC, 95% CI):

| contrast | grade 4 | all gliomas | WHO GBM |
|---|---|---|---|
| B0+Ipure − B0 | +0.453 (+0.336 to +0.563) | +0.286 (+0.188 to +0.382) | +0.382 (+0.217 to +0.529) |
| B-Tl+Ipure − B-Tl | +0.203 (+0.089 to +0.316) | +0.225 (+0.142 to +0.313) | +0.202 (+0.045 to +0.345) |
| Ipure − Iscan | +0.037 (−0.018 to +0.095) | +0.061 (+0.024 to +0.106) | +0.019 (−0.072 to +0.114) |
| B-Tl − B0 | +0.262 (+0.145 to +0.374) | +0.066 (−0.026 to +0.157) | +0.179 (+0.035 to +0.319) |

Reading:
- **On UCSF the images carry the signal; clinical data carry none.**
  - B0 lies at or below 0.5. The permuted-label control lands in the same range, so this is the usual negative bias
    of cross-validation under the null, not a reversed signal.
  - Images add +0.2 to +0.45 to clinical data, with or without the timeline.
  - The timeline adds about 0.01 once the images are in: B-Tl+Ipure 0.871 vs Ipure 0.863.
- **Change from the previous scan adds little to the current scan when the model is trained on UCSF.** Ipure − Iscan
  is +0.04 in grade 4 (CI covers 0) and +0.06 in all gliomas.
- **Timg does best everywhere (0.89–0.91),** even though it has only 6 inputs.
- **Within phase.** The later post-RT subset of the primary set (27 / 38) gives the same picture: Ipure 0.875
  (0.789–0.944), Timg 0.927 (0.861–0.978), B-Tl 0.662, B0 0.410. The set is almost all later post-RT, so there is no
  phase contrast for the timeline to exploit.
- **Caution.** These are internal estimates on a two-scan cohort. The UCSF progression call was probably made largely
  from these same scans (see Part A, single inputs), so part of the image–label agreement may be built in.

**EXPLORATORY validity check (not in the plan).** Labels were permuted across patients (20 permutations, the same
folds). Iscan, Ipure, Timg and B-Tl+Ipure then give mean AUCs of 0.40–0.46 (maximum 0.62) in grade 4 and 0.42–0.44 in
all gliomas. So the pipeline does not leak.

### Sensitivity and secondary sets (grade 4, AUC, 95% CI)

| arm | scan 2 `pos_s2_between` (39/40) | scan 2, verified negatives only (29/33) | *reference only:* `et_increased` (71/69) |
|---|---|---|---|
| B0 | 0.551 (0.434–0.667) | 0.441 (0.322–0.548) | 0.526 (0.443–0.605) |
| B-Tl | 0.708 (0.601–0.805) | 0.720 (0.593–0.828) | 0.688 (0.611–0.761) |
| Iscan | 0.843 (0.752–0.920) | 0.843 (0.744–0.927) | 0.844 (0.778–0.901) |
| Ipure | 0.847 (0.752–0.920) | 0.862 (0.763–0.940) | 0.945 (0.906–0.974) |
| B0+Ipure | 0.841 (0.751–0.914) | 0.860 (0.762–0.936) | 0.943 (0.904–0.972) |
| Timg | 0.893 (0.811–0.951) | 0.922 (0.852–0.974) | 0.960 (0.924–0.985) |
| B-Tl+Ipure | 0.859 (0.773–0.929) | 0.886 (0.796–0.952) | 0.937 (0.896–0.968) |

- The contrast signs are the same as in the primary set. B0+Ipure − B0 and B-Tl+Ipure − B-Tl exclude 0 in every set
  (contrasts.csv).
- `et_increased` is defined on the images, so it is an upper reference and not a result.

All scans (`pos_s2_pm30` + `pos_s1_at` vs primary negatives), single-scan inputs only:

| arm | grade 4 (34/103/97) | all gliomas (60/231/210) |
|---|---|---|
| B0 | 0.427 (0.333–0.518) | 0.522 (0.447–0.596) |
| Iscan | 0.858 (0.777–0.924) | 0.791 (0.723–0.854) |
| B0+Iscan | 0.835 (0.749–0.906) | 0.790 (0.722–0.854) |

### UCSF's own TRAIN / TEST split vs 100 random patient-grouped splits

Each model was fitted on the TRAIN rows of the set and tested on its TEST rows. The 100 random splits hold out the same
number of test patients. The split CI is the patient bootstrap on the test rows.

| arm | grade 4: UCSF split (6/10 test) | grade 4: random, median (2.5–97.5%) | all gliomas: UCSF split (8/14 test) | all gliomas: random, median (2.5–97.5%) |
|---|---|---|---|---|
| B0 | 0.517 (0.214–0.813) | 0.508 (0.291–0.801) | 0.670 (0.425–0.897) | 0.629 (0.367–0.795) |
| B-Tl | **0.450** (0.143–0.750) | 0.717 (0.492–0.940) | 0.705 (0.474–0.908) | 0.671 (0.474–0.906) |
| Iscan | 0.917 (0.714–1.000) | 0.874 (0.708–1.000) | 0.821 (0.628–0.964) | 0.821 (0.663–0.967) |
| Ipure | 0.900 (0.717–1.000) | 0.875 (0.723–1.000) | 0.875 (0.708–1.000) | 0.876 (0.755–0.991) |
| Timg | 0.983 (0.900–1.000) | 0.937 (0.831–1.000) | 0.929 (0.795–1.000) | 0.909 (0.809–1.000) |
| B-Tl+Ipure | 0.850 (0.603–1.000) | 0.889 (0.763–1.000) | 0.893 (0.733–1.000) | 0.887 (0.776–0.991) |

- One 16-patient test split ranges over about ±0.15 AUC for the image arms and ±0.25 for the clinical and timeline
  arms.
- In grade 4, UCSF's split lands at the 1st percentile of the random splits for B-Tl. On that split alone, the timeline
  would look worse than chance (0.45), while repeated CV gives 0.67.
- This repeats on new data the split-variance point made on MU. The GBM and 120-day rows are in split_variance.csv.

### Q3: does training on UCSF beat the locked MU model?

B is out-of-fold and A is Part A's locked scores.csv, on the same rows, with a paired patient bootstrap. Grade-4 and
GBM rows use the grade-4 MU model; all-glioma rows use the all-glioma MU model.

| set | B-Ipure | A-Ipure | B − A (95% CI) |
|---|---|---|---|
| **grade 4 (plan)** | 0.863 | 0.726 | **+0.137 (+0.033 to +0.257)** |
| all gliomas | 0.855 | 0.747 | +0.108 (+0.043 to +0.185) |
| WHO GBM | 0.789 | 0.740 | +0.048 (−0.088 to +0.191) |

- **Yes for Ipure,** in grade 4 and all gliomas. The plan calls this comparison descriptive.
- *EXPLORATORY:* the same comparison for the other image arms (grade 4):
  - Iscan +0.031 (−0.052 to +0.116);
  - Timg +0.024 (−0.039 to +0.083);
  - B0+Ipure +0.110 (+0.014 to +0.219).
- So the locked MU single-scan and LUMIERE image models are about as good as models trained on UCSF. What the MU
  models lose is the change inputs, whose UCSF distribution is much narrower than MU's (Part A; UCSF_IMAGING.md).

### Deviations and decisions (Part B)

No council was needed.
1. **Age is the patient's age at scan 1 on both rows.** It is constant within a patient, so it cannot encode the
   timepoint in the all-scan sets. Part A instead derived age at diagnosis for the locked models. The two differ by a
   constant shift within a patient, at most a few years, and this is immaterial for a model refitted on UCSF.
2. **B-Tl coding:**
   - raw days, as in MU timing;
   - days from RT start: NaN when RT has not started or its date is unknown, imputed in-fold with an indicator
     (BASE_PRE);
   - "on treatment" as two flags, on chemo and on RT, with "unknown" (2 scans) as NaN;
   - surgeries before scan 2 = surgeries before scan 1 + the 2nd / 3rd surgeries dated between the scans;
   - days since the previous scan in the scan-2 sets only;
   - chemo started is constant in the primary set.
3. **All-scan sets** use only B0, Iscan and B0+Iscan. Ipure, Timg and the timeline encode the timepoint or rise with
   it: days from diagnosis always increases from scan 1 to scan 2.
4. **Random splits.** Each draws as many test patients as UCSF's TEST split has in that set (seed 20261025). A split is
   redrawn until both sides have at least 2 positives and 2 negatives. The ridge seed is 0 for every single split.
5. **Additions, all EXPLORATORY:**
   - the permuted-label control;
   - the WHO GBM column for every analysis;
   - Q3 for arms other than Ipure.

## 120-day (locked)

This is the plan's secondary origin task. Models were fitted once on MU index scans (`mu_cohort`, verified
`label_120`, all phases), with the same pipeline, and applied once to UCSF scan 1:
- F-B0: clinical.
- F-Iscan: volumes + morphology at the scan.
- F-B0+Iscan.

**F-Ipure was not fitted.** UCSF scan 1 has no earlier scan in the dataset, so its change and history inputs would
be constant (0) and would mean "no history", not "no change". The MU forward B0 design was checked against the C2
clinical columns (identical).

UCSF label, scan 1:
- positive = progression 1–120 d after it;
- negative = progression > 120 d after it, or no progression with ≥ 120 d of dated follow-up;
- excluded: progression at scan 1 (−7 to < 1 d), an earlier progression, and unknown follow-up.

| set (pos/neg/patients) | F-B0 | F-Iscan | F-B0+Iscan | F-B0+Iscan − F-B0 |
|---|---|---|---|---|
| **grade 4, grade-4 models (45/63/108)** | 0.530 (0.421–0.629) | **0.668 (0.567–0.767)** | 0.679 (0.582–0.776) | +0.149 (+0.015 to +0.285) |
| WHO GBM, grade-4 models (30/33/63) | 0.544 (0.402–0.679) | 0.704 (0.573–0.836) | 0.733 (0.604–0.856) | +0.189 (−0.004 to +0.369) |
| all gliomas, all-glioma models (68/153/221) | 0.656 (0.583–0.731) | 0.758 (0.689–0.823) | 0.760 (0.689–0.825) | +0.104 (+0.039 to +0.171) |

- F-Iscan − F-B0: grade 4 +0.138 (−0.017 to +0.294); all gliomas +0.103 (+0.029 to +0.179).
- Calibration in grade 4:
  - F-Iscan: slope 1.10 (0.60–1.77), O/E 1.02 (0.81–1.24);
  - F-B0+Iscan: slope 1.19 (0.71–1.99), O/E 1.03 (0.81–1.25).
- The locked forward image model transports at about 0.67 in grade 4, just above the failure flag. Its lower bound
  is 0.567. On MU, 120-day risk in the intended use is about 0.60 (TRIAGE_FEASIBILITY.md).
- Detection at scan 2 (A-Iscan 0.795) is clearly easier than the 120-day forecast from scan 1.

Deviations and decisions (120-day):
1. **Progression in [0, 1) d after scan 1** (2 scans across all gliomas) counts as progression at scan 1 and is
   excluded, following the plan's "1–120 d" and "progression at scan 1 excluded".
2. **Populations.** The plan does not name one for this analysis. Grade 4 with grade-4 models is treated as primary,
   matching Part A. WHO GBM and all gliomas (with all-glioma models) are extra rows.
3. **Plain AUC, no IPCW,** as the plan says. Unknown-follow-up scans are excluded, not weighted.

## 120-day (internal)

**Label (scan 1).**
- Positive: progression 1–120 d after scan 1.
- Negative: progression > 120 d after scan 1, or no progression with ≥ 120 d of dated follow-up.
- Excluded: progression at scan 1 (−7 to < 1 d), an earlier progression, and unknown follow-up. The rules are the same
  as for the locked 120-day analysis.
- Method: the same pipeline, 5 × 5 CV and bootstrap as Part B. B-Tl has no days-since-previous input, because scan 1
  has no previous scan.

| arm | **grade 4 (45/63/108)** | all gliomas (68/153/221) | WHO GBM (30/33/63) |
|---|---|---|---|
| B0 | 0.415 (0.339–0.490) | 0.577 (0.507–0.648) | 0.357 (0.261–0.444) |
| B-Tl | 0.522 (0.432–0.615) | 0.693 (0.629–0.763) | 0.444 (0.339–0.565) |
| **Iscan** | **0.709 (0.605–0.802)** | 0.775 (0.709–0.837) | 0.669 (0.539–0.789) |
| B0+Iscan | 0.696 (0.591–0.789) | 0.769 (0.702–0.831) | 0.626 (0.489–0.750) |
| B-Tl+Iscan | 0.703 (0.600–0.797) | 0.783 (0.717–0.845) | 0.636 (0.499–0.758) |

| contrast | grade 4 | all gliomas | WHO GBM |
|---|---|---|---|
| B0+Iscan − B0 | +0.280 (+0.165 to +0.384) | +0.192 (+0.126 to +0.257) | +0.270 (+0.142 to +0.409) |
| B-Tl+Iscan − B-Tl | +0.181 (+0.065 to +0.284) | +0.090 (+0.034 to +0.146) | +0.191 (+0.067 to +0.328) |
| B-Tl − B0 | +0.107 (+0.034 to +0.187) | +0.116 (+0.055 to +0.176) | +0.088 (+0.007 to +0.179) |

- **The scan-1 image predicts progression within 120 d** (grade 4: 0.709), close to the locked F-Iscan (0.668).
  - Clinical data and the timeline add nothing to it.
  - Later post-RT only (grade 4, 40 / 51): Iscan 0.697, B-Tl 0.573.
- **In all gliomas the timeline carries some signal of its own (0.69).** It adds little to the image (B-Tl+Iscan 0.783
  vs Iscan 0.775).
- **The UCSF split, grade 4 (8 / 14 test), against the random-split median (2.5–97.5%):**
  - Iscan 0.786, vs 0.733 (0.535–0.930);
  - B-Tl 0.464, vs 0.580 (0.359–0.806).
- **Caution.** Many 120-day positives are the same patients as the scan-2 positives. The scans are a median of 56 d
  apart, so a scan 1 that already shows growing disease is likely to precede a progression call at scan 2.
