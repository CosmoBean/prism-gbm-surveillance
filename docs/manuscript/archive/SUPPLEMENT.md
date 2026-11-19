# Supplementary Material

**Single splits, phase of care and MRI radiomics in post-treatment glioma surveillance: re-evaluation of a radiomics
risk model and an auditable clinical alternative**

*Draft, 2026-10-15. Every number below is copied from the result documents in `docs/results/` and
`docs/manuscript/` or from `outputs/results/`; the file is named in each section. "Grade 4" (G4) is the primary
population; "all" = all gliomas. AUC = IPCW AUC(120 d), mean over 5 repeats of the per-repeat pooled out-of-fold
value, with 95% patient-cluster bootstrap CI (1,000 draws), unless stated otherwise. "PRISM report" refers to an
unpublished internal report; "PRISM report model" and "PRISM report split" are its model and split.*

## Contents

- S1. Pre-specification register
- S2. Cohort flow
- S3. Outcome, censoring rules and label formulations
- S4. Predictor definitions and the as-of-scan treatment rule
- S5. Radiomics: extraction, configurations and outlier clipping
- S6. Frozen deep features
- S7. The PRISM report model and the PRISM report split
- S8. Split variance: full tables and verifier checks
- S9. Estimator and evaluation details
- S10. Feature-group search with permutation control
- S11. Phase-of-care ladder: full results
- S12. Secondary analyses: baselines, sensitivity, imbalance, schedule, feature conflicts, SHAP, calibration and utility
- S13. External evaluation on LUMIERE: full results
- S14. Imaging-defined label, imaging diagnostics and re-segmentation
- S15. The auditable layer: full results and an example audit record
- S16. Reproducibility
- S17. Reporting checklists (TRIPOD+AI, CLEAR) cross-referenced to the manuscript
- S18. CFB-GBM diffusion analysis

---

## S1. Pre-specification register

| Analysis | Status | Plan record | Decision rule / primary quantity | Outcome |
|---|---|---|---|---|
| Radiomics vs baseline, nested over 70 configurations, grade 4 | Pre-specified primary (development) | Publication plan §3.3 | ΔAUC with 95% CI | −0.032 [−0.084, +0.017]; no gain |
| LUMIERE locked clinical + timing + volumes, grade-4-trained | Pre-specified external model | `EXTERNAL_LUMIERE.md` | Pooled IPCW AUC | 0.608 / 0.620 (ridge / boosting) |
| Phase-of-care ladder, post-RT R2 + I2 vs R2 | Pre-specified primary; plan in module docstring, not separately committed; a smoke run printed some I0–I2 numbers before the full run; plan unchanged | `PHASE_LADDER.md` §1 | ΔAUC with CI and 100-permutation p | +0.061 [−0.038, +0.156], p = 0.21; not supported |
| Imaging-defined (clean) label | Pre-specified; plan snapshot saved before the run | `outputs/results/analyses/clean_label/PLAN_snapshot.md` | ΔAUC ≥ 0.03 with CI excluding 0 | +0.027 [−0.033, +0.082]; not met |
| Re-segmentation | Rule written before any result was seen | `RESEGMENTATION.md` | Detection Δ ≥ 0.05 with CI > 0, or ET larger at progression in > 65% of pairs | −0.016 [−0.057, +0.025]; 45%; not met |
| CFB-GBM ADC | Pre-specified; plan snapshot saved before the run | `outputs/results/analyses/cfb_adc/PLAN_snapshot.md` | Δ(d − c) ≥ 0.03 with CI excluding 0 | +0.007 [−0.019, +0.035], p = 0.151; not met |
| Audit layer P1 (coverage) and P2 (abstention beyond case mix) | Pre-specified; plan snapshot saved before the run | `outputs/results/analyses/audit_system/PLAN_snapshot.md` | P1 coverage ≥ 0.78; P2 CI above 0 | P1 0.841 [0.790, 0.885], met; P2 +0.006 [−0.023, +0.036], not met |
| Split variance (500 splits) | Descriptive; designed after the single-split result was known | `SPLIT_VARIANCE.md` | — | — |
| Positive controls, SHAP, feature conflicts, imbalance, schedule coupling, baselines, sensitivity, utility | Secondary or exploratory | respective documents | — | — |

Sequence: the clean-label, re-segmentation, CFB-GBM and audit analyses were designed after the main imaging result
(no added value) was known. Each had its own rule fixed before its own run. Contrasts beyond the primary ones are not
corrected for multiplicity.

---

## S2. Cohort flow

Source: `docs/manuscript/FLOW.md` (`outputs/data/mu_flow.csv`, `outputs/results/analyses/tables/lumiere_flow.csv`).
Figure: `docs/manuscript/cohort_flow.png` (Figure S1).

**Table S1a. MU-Glioma-Post.**

| Step | Scans | Patients | Excluded |
|---|---|---|---|
| All timepoints | 596 | 203 | – |
| All four sequences and mask present | 594 | 203 | 2 |
| Tumour (labels 1–3) present | 592 | 203 | 2 |
| MRI day known | 589 | 202 | 3 |
| MRI day plausible (≥ −365 d, not before an earlier timepoint) | 588 | 202 | 1 |
| Progression date known for progressors | 588 | 202 | 0 |
| MRI not after recorded death | 580 | 202 | 8 |
| Before late treatment (2nd-line, immunotherapy, new treatment) | 501 | 199 | 79 |
| **Before first progression (index scans)** | **308** | **155** | 193 |
| Grade 4 subset | 249 | 126 | – |

**Table S1b. LUMIERE.**

| Step | Studies | Patients | Excluded |
|---|---|---|---|
| All rated studies | 616 | 91 | – |
| Post-operative (week ≥ 2 after surgery) | 456 | 81 | 160 |
| Rated SD / PR / CR / Post-Op | 199 | 70 | 257 |
| Before first progression | 132 | 61 | 67 |
| **Not after recorded death (index scans)** | **132** | **61** | 0 |

Censored scans (52 MU, 39 grade 4, 9 LUMIERE at 120 d) stay in the cohort and are handled by the censoring-aware
labels and IPCW.

**Table S2.** The full cohort table with definitions is `docs/manuscript/TABLE1_COHORT.md` (`table1.csv`). Additional
rows not in main Table 1: last documented follow-up after scan, median [IQR] days 275 [107–471] (all), 285 [112–478]
(G4), 462 [238–721] (LUMIERE); time to progression or censoring 125 [50–237], 111 [48–208], 168 [91–287]; progression
documented after the scan at any time 220 (71%), 190 (76%), 122 (92%); LUMIERE T1c field strength 1.5 T / 3 T / other or
missing 81 (61%) / 44 (33%) / 7; MU field strength not distributed. WHO grade in all gliomas: grade 1, 3 (2%); grade 2,
23 (15%); grade 3, 2 (1%); "3 vs 4", 1 (1%); grade 4, 126 (81%).

---

## S3. Outcome, censoring rules and label formulations

Source: `docs/results/FIX_LABELS.md`, `docs/results/C1_endpoint.md`, `docs/results/C1_full_tables.md`.

**Estimand.** Documented first progression within H = 120 d of the index scan (90 / 180 d as sensitivities). Death
without documented progression censors at the death day. Label 0 requires progression after H or progression-free
follow-up ≥ H. Composite (progression or death) is a sensitivity analysis only.

**Table S3. Rules adopted in the label audit.**

| # | Problem found | Rule |
|---|---|---|
| 1 | Death without documented progression treated as a verified negative at every horizon | Death censors at the death day (primary); composite event as sensitivity |
| 1b | MRIs dated after the recorded death (15/96 MU deaths) | If more than one dated record follows the death day, the death date is ignored (7 patients, 3 with cohort scans); if exactly one, that scan is excluded |
| 2 | Progression flag 0 with a progression date (3 patients); two date fields disagree (29 patients) | Any patient with a progression date is a progressor; primary date `date_of_first_progression`; reverse order as sensitivity |
| 3 | One MRI day of −965; progressor who died before progression | MRI day ≥ −365 and not before an earlier timepoint; death-before-progression flagged |
| 4 | Hazard formulation counted scans censored mid-interval as surviving the interval | Censored scans contribute only fully observed intervals |
| 5 | Follow-up extended by non-imaging dates | Kept as primary; imaging-only follow-up as sensitivity |
| 6 | Unknown RT end coded as "not early post-RT" | `early_post_rt` is 1 / 0 / missing (94 scans missing, 65 grade 4) |

Effect: six scans left the cohort (314 → 308; grade 4 253 → 249). At 120 d, 17 negatives became censored (16 deaths
within 120 d without progression, 1 ignored death date) and 1 negative became positive; no positive changed.

**Table S4. Label counts (positive / verified negative / censored).**

| Population | Label | H = 90 | H = 120 | H = 180 |
|---|---|---|---|---|
| All (308 / 155) | primary | 65 / 195 / 48 | 100 / 156 / 52 | 144 / 105 / 59 |
| All | composite | 79 / 195 / 34 | 116 / 156 / 36 | 161 / 105 / 42 |
| All | alternative progression date | 63 / 191 / 54 | 99 / 151 / 58 | 141 / 102 / 65 |
| All | imaging-only follow-up | 65 / 187 / 56 | 100 / 149 / 59 | 144 / 99 / 65 |
| Grade 4 (249 / 126) | primary | 62 / 152 / 35 | 93 / 117 / 39 | 131 / 75 / 43 |
| Grade 4 | composite | 74 / 152 / 23 | 107 / 117 / 25 | 146 / 75 / 28 |
| LUMIERE (132 / 61) | primary | 24 / 101 / 7 | 47 / 76 / 9 | 62 / 61 / 9 |
| LUMIERE | composite | 26 / 101 / 5 | 51 / 76 / 5 | 66 / 61 / 5 |

LUMIERE gives a survival time without a death indicator; a recorded survival time is read as a death and used only as a
censoring time in the primary label.

**IPCW AUC.** Cumulative/dynamic AUC at 120 d with Kaplan–Meier censoring weights (Uno et al., 2007; Blanche et al.,
2013). Cases are scans with an event by 120 d, weighted by the inverse of the censoring survival at their event time;
controls are scans event-free beyond 120 d. The vectorised implementation matches scikit-survival to 2 × 10⁻¹⁶
(`FIX_EVALUATION.md` §1). In the bootstrap, censoring weights are re-estimated in each resample; if a resample has no
censoring, G = 1.

**Table S5. Label formulations, grade 4, H = 120 d** (`C1_endpoint.md`; ΔAUC vs naive).

| Features | Formulation | AUC [95% CI] | ΔAUC vs naive [95% CI] | O/E | Slope |
|---|---|---|---|---|---|
| volumes + clinical | naive | 0.651 [0.567, 0.727] | — | 1.14 | 0.95 |
| | verified | 0.657 [0.577, 0.732] | +0.006 [−0.020, +0.030] | 0.95 | 0.91 |
| | IPCW | 0.656 [0.578, 0.731] | +0.005 [−0.021, +0.029] | 0.97 | 0.92 |
| | hazard | 0.653 [0.574, 0.726] | +0.002 [−0.018, +0.022] | 0.87 | 0.50 |
| legacy radiomics + clinical | naive | 0.648 [0.553, 0.736] | — | 1.13 | 0.52 |
| | verified | 0.655 [0.575, 0.730] | +0.007 [−0.021, +0.038] | 0.96 | 0.51 |
| | IPCW | 0.654 [0.575, 0.730] | +0.006 [−0.022, +0.036] | 0.98 | 0.51 |
| | hazard | 0.669 [0.583, 0.746] | +0.021 [−0.027, +0.068] | 0.90 | 0.33 |

All 36 ΔAUC CIs (2 populations × 2 feature sets × 3 horizons × 3 formulations) include 0. The naive label
under-predicts risk in all 12 settings (O/E 1.12–1.19 against 0.95–0.99 for verified / IPCW). The legacy radiomics
pipeline in C1 predates the clipping fix (S5).

---

## S4. Predictor definitions and the as-of-scan treatment rule

Source: `prism/features/tabular.py`; `docs/results/FIX_TREATMENT_ASOF.md`; `docs/results/FIX_FEATURES.md`; audit
record input tables (`outputs/results/analyses/audit_system/records.md`).

**Table S6. Baseline predictors (23 raw; 31 design columns after missingness indicators).**

| Group | Predictor | Definition (as of scan day) | Source column(s) |
|---|---|---|---|
| Clinical | age | age at diagnosis, years | `clinical_age_at_diagnosis` |
| | male | sex at birth | `clinical_sex_at_birth` |
| | idh_mutant, idh_unknown | IDH1/IDH2 mutant; neither documented | `clinical_idh1_mutation`, `clinical_idh2_mutation` |
| | mgmt_methylated, mgmt_unknown | MGMT promoter methylated; unknown code | `clinical_mgmt_methylation` |
| Timing | days_from_diagnosis | scan day | `days_from_diagnosis_to_mri` |
| | days_since_rt_end | days since documented RT end; missing until RT completed | RT end day vs scan day |
| | rt_date_unknown | no completed RT with known end date at the scan | RT end day |
| | early_post_rt | 0–84 d after RT end (RANO 12-week window); missing if RT end unknown | RT end day |
| | early_post_rt_x_mgmt_methylated | interaction | RT end day × MGMT |
| | visit_index | rank of the scan among the patient's MRIs | MRI days |
| Treatment | rt_started | RT start day ≤ scan day | `clinical_radiation_therapy` + RT start day |
| | rt_completed | RT end day ≤ scan day | RT end day |
| | rt_dose_gy, rt_fractions, rt_hypofractionated | prescription, visible once RT started; hypofractionation ≤ 15 fractions | `clinical_dose`, `clinical_number_of_fractions` |
| | rt_start_day | days from diagnosis to RT start, visible once started | RT start day |
| | rt_duration_days | RT end − start, visible once completed | RT start and end days |
| | chemo_started | initial TMZ / lomustine start ≤ scan day | initial chemotherapy fields |
| | surgery_day, biopsy_before_resection | visible once the first surgery has happened | first surgery fields |
| | previous_brain_tumor | history, known at any scan | `clinical_previous_brain_tumor` |

Unknown values are imputed in-fold with the training median plus a missingness indicator; nothing is zero-filled
silently. Therapy marked given without a start date (2 RT, 2 chemotherapy patients) is assumed to have started before
the scan.

**Table S7. What leaked before the as-of-scan fix** (scans affected, grade 4 / all gliomas).

| Feature | Problem | Affected |
|---|---|---|
| `rt_given`, `chemo_given` | "will receive RT / chemotherapy", true for scans before the course started | 13 / 23 (RT), 13 / 21 (chemo) |
| dose, fractions, hypofractionation, `rt_start_day` | prescription and start date of a course that had not started | 13 / 19–23 |
| `rt_duration_days` | duration of a course not yet finished (also reveals early stopping) | 17 / 29 |
| `days_since_rt_end`, `rt_date_unknown` | negative values from the future RT end date | 17 / 29 |
| `surgery_day`, `biopsy_before_resection` | one scan precedes the first surgery | 1 / 1 |

Progression, death, last follow-up and late-treatment dates are used only for labels, censoring and eligibility.
Change features use earlier scans only.

**Effect on repeated CV (intermediate inputs; earlier repeat-averaged estimator; `FIX_TREATMENT_ASOF.md` §3).**
Baseline ridge grade 4 0.694 [0.613, 0.775] → 0.729 [0.648, 0.811]; all gliomas 0.719 [0.648, 0.788] → 0.749
[0.675, 0.820]. Boosting grade 4 0.723 [0.633, 0.806] → 0.731 [0.641, 0.813]; all gliomas 0.743 [0.666, 0.816] →
0.740 [0.663, 0.815]. Timing-only boosting fell (grade 4 0.718 → 0.696; all 0.735 → 0.705): part of its earlier signal
came from the future RT end date. The MGMT × window flag changed repeated-CV AUC by ≤ 0.008. These intermediate values
are superseded by the final run (main Table 2).

**Molecular look-ahead found by the audit (exploratory).** IDH and MGMT are used at scans taken before the diagnosis
date: 8 grade 4 scans (7 patients; 1 event, 4 non-events, 3 censored) and 11 all-glioma scans, 1–58 days before
diagnosis (`AUDIT_SYSTEM.md` §2). Its effect on the baseline AUC was not quantified.

**Imaging measurements.** Volumes (ET, NETC, SNFH, RC, tumour = ET + NETC, lesion), morphology (ET fraction,
multifocality, largest axial ET area, ET-to-cavity distance and proximity, T1c / FLAIR intensities relative to brain
> 10 mm (Euclidean) from lesion and cavity), and past-only change (from previous scan and nadir, growth rate,
`vol_pd_flag` requiring a measurable nadir ≥ 0.1 cc, `et_new_from_zero_nadir`, missingness flags for undefined relative
change; 25 change columns). For LUMIERE transport, necrosis and cavity were merged (`log_necrosis_cavity_cc`) because
DeepBraTumIA labels the cavity as necrosis (`FIX_FEATURES.md` §1).

---

## S5. Radiomics: extraction, configurations and outlier clipping

Source: `docs/results/C3_radiomics.md`, `docs/results/FIX_RADIOMICS_CLIP.md`, `docs/results/FIX_FEATURES.md` §6,
`prism/features/radiomics.py`.

**Extraction.** PyRadiomics (van Griethuysen et al., 2017). *Legacy* features are those of the PRISM report: T1c and
FLAIR, original, LoG and wavelet images, 2,446 columns. Under the legacy within-lesion z-score and fixed bin width the
texture matrices are effectively two-level (GLCM joint entropy ≤ 2 bits), so legacy texture behaves as a binary habitat
descriptor (above vs below lesion mean). *Corrected* (v2) features use a whole-brain z-score, a fixed bin count of 32
(joint entropy 4.7–6.3 bits), no second N4 correction, and are extracted per compartment (ET, NETC, SNFH, core, lesion,
5 mm peri-cavity rim, shape) and for all four sequences (2,316 columns). Known limitations: a fixed bin count rather
than the IBSI-recommended fixed bin width (Zwanenburg et al., 2020); the ICC stability pass covers T1c and FLAIR
texture and first-order features only (1,116 of 2,316 columns); the 5 mm rim uses a city-block dilation.

**Configurations (70).** Variant (legacy; corrected whole lesion; corrected per compartment; corrected all four
sequences) × stability filter (none; ICC ≥ 0.75 under 1-voxel erosion, in-fold) × selection (top-10 or top-30
univariate F; L1 with non-zero coefficients only, at most 30; PCA-10; decorrelation + top-20) × integration
(concatenation with the baseline; or a stacked radiomics score from inner out-of-fold predictions). Nested choice:
inner 3-fold patient-grouped AUC in each outer training fold. Missing compartments are imputed with the median and one
indicator per missingness pattern.

**Outlier clipping.** Three legacy columns (FLAIR LoG σ = 1, 2, 3 mm NGTDM Coarseness) held the PyRadiomics sentinel
10⁶ in four scans (two grade 4); other values in these columns have medians of 10⁻⁴ to 8 × 10⁻⁴. One such value inflates
a training SD by orders of magnitude and makes PCA and the stacked score depend on these scans. Before the fix, the
stacked score had inner-OOF training values of −10⁴ to −4.6 × 10⁶ in 20/25 grade 4 fits. The fix, `QuantileClip(q =
0.01)`, is fitted in each training (and inner) fold, clips to the fold's 1st/99th order statistics, and applies the
same bounds to test scans. It does not look at labels and applies to all configurations and to deep features.

**Table S8. Effect of the clipping fix** (`FIX_RADIOMICS_CLIP.md`).

| Population | Nested AUC before → after | ΔAUC before → after | Cal. slope |
|---|---|---|---|
| Grade 4 | 0.672 [0.597, 0.743] → 0.666 [0.586, 0.739] | −0.026 [−0.073, +0.017] → −0.032 [−0.084, +0.017] | 0.50 → 0.60 |
| All gliomas | 0.732 [0.664, 0.794] → 0.747 [0.678, 0.811] | +0.012 [−0.029, +0.050] → +0.028 [−0.017, +0.071] | 0.77 → 0.85 |

Largest change in any single configuration: 0.020. Single configurations with CI above 0: grade 4 0/70 before and
after (below 0: 12/70 → 8/70); all gliomas 0/70 → 1/70 (`legacy|none|pca10|stack|ridge`, 0.754, +0.035 [+0.002,
+0.068], p(Δ ≤ 0) = 0.021). Not covered by the fix: the radiomics group of the feature-group search (S10), the C1
radiomics feature set (S3), and the feature-conflict B + radiomics row (S12).

**Table S9. Radiomics results by population** (`C3_radiomics.md`; `outputs/results/c3/{grade4,all_glioma}/results.csv`).

| Model | Grade 4 AUC | Δ [95% CI] | Slope | All gliomas AUC | Δ [95% CI] | Slope |
|---|---|---|---|---|---|---|
| Baseline ridge | 0.698 [0.615, 0.774] | — | 0.89 | 0.720 [0.638, 0.792] | — | 0.88 |
| Baseline boosting | 0.687 [0.601, 0.768] | −0.012 [−0.072, +0.048] | 0.82 | 0.718 [0.642, 0.792] | −0.002 [−0.052, +0.047] | 0.87 |
| Best post hoc (legacy PCA-10 stack) | 0.721 [0.638, 0.793] | +0.023 [−0.013, +0.057] | 0.92 | 0.754 [0.685, 0.823] | +0.035 [+0.002, +0.068] | 0.96 |
| **Nested over 70 (honest)** | **0.666 [0.586, 0.739]** | **−0.032 [−0.084, +0.017]** | 0.60 | **0.747 [0.678, 0.811]** | **+0.028 [−0.017, +0.071]** | 0.85 |

Median ΔAUC by variant, grade 4: legacy +0.005, v2 all four sequences −0.016, v2 compartments −0.017, v2 lesion −0.001;
all gliomas +0.024, +0.000, −0.005, +0.005. Nested choices: legacy in 18/25 (grade 4) and 25/25 (all) outer folds.
Stacking beat concatenation in grade 4 (median Δ −0.003 vs −0.027).

---

## S6. Frozen deep features

Source: `docs/results/DEEP_FEATURES.md`; `outputs/results/analyses/deep/`.

**Encoders.** MONAI SwinUNETR (four channels FLAIR / T1c / T1 / T2, feature size 48), encoder only: BraTS 2021 weights;
BrainSegFounder (UK Biobank self-supervised pretraining, BraTS fine-tuning; Cox et al., 2024 [CHECK]); and random
weights (seed 0) as the control. **Input.** Skull-stripped 1 mm volumes, z-scored within the brain, reoriented to LPS,
zero-padded to a multiple of 32; eight flip test-time augmentations. **Features.** Mask-weighted mean pooling at stages
0–3 (48 + 96 + 192 + 384 = 720 per region); MU regions lesion, ET, NETC, SNFH, 5 mm rim and ET ∪ SNFH; LUMIERE regions
ET, SNFH, ET ∪ SNFH and lesion. The 768-d bottleneck was not used (between-scan SD 3 × 10⁻⁴ for BraTS 2021 weights).
**Families.** D1 pretrained, 32 configurations (2 encoders × {lesion, compartments} × 4 selections × 2 integrations);
D0 random, 16; D1b deep + legacy radiomics stacked, 16; DS shared regions, 16. **Licences.** BraTS 2021 SwinUNETR
weights Apache-2.0; BrainSegFounder weights under the UK Biobank material transfer agreement (not redistributed).

**Table S10. Deep features on MU.**

| Arm | Grade 4 AUC | Grade 4 Δ [95% CI] | All AUC | All Δ [95% CI] |
|---|---|---|---|---|
| Baseline | 0.698 [0.615, 0.774] | — | 0.720 [0.638, 0.792] | — |
| D1 pretrained, nested over 32 | 0.694 | −0.004 [−0.069, +0.063] | 0.731 | +0.011 [−0.032, +0.056] |
| D0 random weights, nested over 16 | 0.649 | −0.049 [−0.085, −0.014] | 0.711 | −0.009 [−0.032, +0.009] |
| D1b deep + legacy radiomics, nested over 16 | 0.709 | +0.011 [−0.032, +0.054] | 0.751 | +0.031 [−0.003, +0.066] |
| DS shared regions, nested over 16 | 0.699 | +0.001 [−0.057, +0.060] | 0.725 | +0.005 [−0.035, +0.046] |
| Baseline + volumes + D1 vs baseline + volumes | 0.694 vs 0.702 | −0.008 [−0.045, +0.033] | 0.739 vs 0.733 | +0.007 [−0.021, +0.036] |

Single configurations with CI above 0: 0/80 (grade 4); 3/80 (all gliomas; +0.035 to +0.040, lower bounds +0.001 to
+0.004); about 2 of 80 expected by chance. Image-only stacked score, grade 4: pretrained 0.652 (modal configuration),
random 0.566; correlation with log tumour volume r = 0.58 and with the baseline score r = 0.28. Calibration slope of
nested D1: 0.55 (grade 4), 0.79 (all).

---

## S7. The PRISM report model and the PRISM report split

Source: `docs/results/SHAP_PRISM_SPLIT.md`; `docs/manuscript/FIGURES.md` (Figure 1); `outputs/results/analyses/
shap_prism_split/`; `outputs/results/analyses/paper_figures/single_split{,_pairs}.csv`.

**Reconstruction.** The input matrix was rebuilt from the legacy feature files plus the clinical codes using the PRISM
report case table; the shipped bundle reproduced the stored test predictions on all 84 rows (maximum absolute difference
1.1 × 10⁻¹⁵ calibrated, 1.4 × 10⁻¹⁵ raw). The model is an L2 logistic regression (liblinear, C = 0.0087, balanced class
weights) on 46 standardised columns (two of 48 selected columns are dropped by a correlation filter), with a monotone
Platt calibrator. Exact linear SHAP reproduced the shipped importance table (Spearman 0.997, identical top 10). Modality
shares: T1c 52%, FLAIR 26%, clinical codes 22% (share of mean absolute per-scan group sum).

**Table S11. Composition of the PRISM report test set** (percentile among 500 design splits).

| | Full cohort | PRISM report test set | 500 splits: mean (2.5–97.5%) | Percentile |
|---|---|---|---|---|
| Scans / patients | 308 / 155 | 82 / 29 | 84.5 / 29.8 | |
| Event rate, naive | 0.325 | 0.268 | 0.254 (0.165–0.348) | 62 |
| Grade 4 / GBM | 0.81 / 0.70 | 0.80 / 0.77 | 0.82 / 0.63 | 44 / 97 |
| IDH-mutant scans | 0.195 | 0.146 | 0.271 (0.131–0.403) | 5 |
| Pre-RT scans | 0.373 | 0.439 | 0.353 (0.220–0.474) | 89 |
| Event rate in pre-RT scans | 0.087 | 0.000 (0 / 36) | 0.044 (0–0.138) | 15 |
| ≤ 12 weeks post-RT | 0.338 | 0.244 | 0.283 | 16 |
| Later post-RT | 0.263 | 0.268 | 0.345 (0.243–0.450) | 6 |
| AUC of the rule "scan is post-RT" | 0.677 | 0.740 | 0.675 (0.575–0.772) | 92 |

**Table S12. Pair decomposition (naive AUC)** (`single_split_pairs.csv`; 22 positives, 36 pre-RT negatives, 24 other
negatives; 60% of pairs involve a pre-RT negative).

| Model | All pairs | Positives vs pre-RT negatives | Positives vs other negatives |
|---|---|---|---|
| PRISM report model | 0.802 | 0.823 | 0.771 |
| Baseline ridge | 0.871 | 0.962 | 0.735 |
| Baseline GBM | 0.844 | 0.933 | 0.710 |
| Baseline + legacy radiomics | 0.862 | 0.934 | 0.754 |
| Clinical only (ridge) | 0.791 | 0.789 | 0.793 |

On the 36 pre-RT scans the PRISM report model's T1c features lowered the log-odds by −0.50 on average; the baseline
ridge did the same through treatment (−0.38) and timing (−0.15). Our models' SHAP profiles on this split match their
whole-cohort out-of-fold profiles at group level (baseline ridge: treatment 55%, clinical 29%, timing 16% on the split;
52 / 29 / 19% out of fold); the split does not lean on unusual features.

**Post-RT test scans** (42 scans, 19 patients, 19 positives; IPCW AUC [95% CI], naive in brackets): PRISM report model
0.770 [0.604, 0.907] (0.778); baseline ridge 0.718 [0.481, 0.880] (0.730); baseline GBM 0.699 [0.463, 0.846] (0.705);
+ legacy radiomics 0.758 [0.605, 0.886] (0.769); clinical only 0.818 [0.664, 0.924] (0.826), Δ vs baseline +0.100
[−0.015, +0.293].

**Before and after the as-of-scan fix** (30 test patients / 84 scans, naive / IPCW; `head_to_head_{before,after}.csv`):
PRISM report model 0.802 / 0.811 in both; baseline ridge 0.870 / 0.844 → 0.880 / 0.860; baseline boosting 0.901 / 0.881
→ 0.869 / 0.855; baseline + legacy radiomics 0.869 / 0.848 → 0.871 / 0.852; baseline + corrected compartments 0.869 /
0.843 → 0.886 / 0.870. With the final labels (29 / 82): ridge 0.871 / 0.851, boosting 0.844 / 0.824.

---

## S8. Split variance: full tables and verifier checks

Source: `docs/results/SPLIT_VARIANCE.md`; `docs/manuscript/FIGURES.md` §2 (clipped `baseline_rad`);
`outputs/results/analyses/split_variance/{summary,summary_clipped,per_split_auc_clipped}.csv`.

**Design.** Seeds 0–499 of the PRISM report's split search gave 500 distinct test sets (82–94 test scans, mean 86.1;
10–33 positives). The search favours patients with many scans: all 157 patients of the PRISM report case table appear,
and the most frequent is in 71% of splits. Cohort, label and features are the PRISM report's (315 scans / 157 patients;
naive label, equal to ours on all 314 shared scans). Rank = share of splits with strictly lower AUC than the model's own
seed-62 value re-run here.

**Table S13. Naive AUC over 500 splits.**

| Model | Mean ± SD | 2.5–97.5% | Seed 62 (rank) | ≥ 0.802 | Beats baseline | Mean Δ vs baseline |
|---|---|---|---|---|---|---|
| PRISM report pipeline, re-selected per split | 0.720 ± 0.055 | 0.610–0.819 | 0.801 (92%) | 7.2% | 12% | −0.081 |
| PRISM report model, shipped features refitted (optimistic) | 0.815 ± 0.044 | 0.726–0.887 | 0.802 (38%) | 62% | 58% | +0.014 |
| Baseline ridge | 0.801 ± 0.052 | 0.694–0.895 | 0.871 (91%) | 50% | – | – |
| Baseline + legacy radiomics (clipped) | 0.799 ± 0.053 | 0.674–0.892 | 0.862 (89%) | 50.2% | 51.6% | −0.002 |

**Table S14. IPCW AUC over 475 splits.**

| Model | Mean ± SD | Seed 62 (rank) | Beats baseline | Mean Δ |
|---|---|---|---|---|
| PRISM report pipeline, re-selected | 0.727 ± 0.058 (0.602–0.832) | 0.816 (94%) | 25% | −0.042 |
| Shipped features refitted (optimistic) | 0.825 ± 0.045 (0.737–0.901) | 0.817 (40%) | 81% | +0.055 |
| Baseline ridge | 0.769 ± 0.056 (0.654–0.876) | 0.851 (92%) | – | – |
| Baseline + legacy radiomics (clipped) | 0.774 ± 0.058 | 0.845 (92.0%) | 56.8% | +0.005 |

Per split, clipped minus pre-clip naive AUC of the radiomics arm: mean −0.002, SD 0.009. Gap between honest and
optimistic PRISM versions: 0.095 ± 0.040.

**Composition.** Baseline ridge per-split AUC correlates with the pre-RT event rate (Spearman −0.61 naive, −0.57 IPCW),
the AUC of the "post-RT" rule (+0.57, +0.51), the later post-RT share (−0.26) and the pre-RT share (+0.22). Nine
composition variables explain CV R² 0.42 and predict 0.851 for seed 62 (observed 0.871, mean 0.801). For the PRISM
report pipeline: CV R² 0.10 (naive), 0.15 (IPCW); strongest correlates IDH-mutant fraction (−0.30) and the "post-RT"
rule (+0.22); predicted 0.773 for seed 62 (observed 0.801, mean 0.720).

**Verifier checks (earlier per-split table; not repeated on the final run).** (1) On seed 62 and 15 other splits,
redoing the ranking at full cost (10 folds × 100 permutation repeats) gave 0.718 ± 0.054 on the 15 splits (cheap
ranking 0.726 ± 0.057; cheap − full +0.008 ± 0.033, r = 0.83). Re-running the shipped Optuna search as well gave
0.654 ± 0.054 (−0.064 ± 0.055 against full ranking with the shipped C); its inner-CV objective averaged 0.865
(optimism ≈ 0.21), and on seed 62 it gave 0.762, not 0.802. (2) Against 300 fully random 30-patient splits, the design
splits had more test scans (85.5 vs 59.9) and a narrower baseline AUC spread (SD 0.054 vs 0.069), so spread under the
design underestimates what a fresh split would show (Varoquaux, 2018).

---

## S9. Estimator and evaluation details

Source: `docs/results/FIX_EVALUATION.md`.

- **Headline estimator.** Mean over the 5 repeats of the per-repeat pooled-OOF IPCW AUC (and Brier, O/E, slope). The
  earlier estimator — the AUC of the OOF prediction averaged over repeats — is an ensemble of five models per scan and
  is optimistic, more so for unstable nested pipelines. On intermediate inputs, the nested radiomics ΔAUC moved from
  +0.009 (repeat-averaged) to −0.002 (mean over repeats) under the change.
- **Bootstrap.** Patient-cluster bootstrap, 1,000 draws; each draw resamples patients once and recomputes the
  mean-over-repeats statistic of every model on that draw, so differences are paired. ΔAUC is the point estimate (not
  the bootstrap mean) with the bootstrap CI.
- **Calibration.** O/E (Kaplan–Meier risk / mean prediction, or IPCW-weighted), calibration-in-the-large with a logit
  offset, calibration slope by IPCW-weighted logistic regression on the logit, flexible calibration curves (restricted
  cubic spline, 3 knots) and ICI (Van Calster et al., 2019).
- **External estimator.** Every LUMIERE arm is scored on the same 5 × 5 patient-grouped LUMIERE folds (per-fold IPCW
  AUC averaged over 25 folds, censoring weights from the whole LUMIERE cohort); locked models are also scored pooled.
  An earlier pooled score of differently recalibrated folds produced an artefactual AUC of 0.414 for recalibrated
  ridge; recalibration leaves discrimination unchanged by construction.
- **Selection inside folds.** Feature selection, PCA, ICC filtering, stacking and hyperparameter choice are all inside
  the training fold, with inner patient-grouped CV for every choice (Varma & Simon, 2006; Cawley & Talbot, 2010;
  Demircioğlu, 2021).

---

## S10. Feature-group search with permutation control

Source: `docs/results/C2_feature_search.md`; `docs/results/FINAL_RESULTS.md`.

Six groups — clinical, timing, volumes, morphology, change, legacy radiomics (top 20 in-fold; unclipped) — give 63
combinations × 2 learners (ridge; fixed shallow boosting). The treatment block is not part of this search. The honest
estimate selects one of the 126 candidates per outer fold by inner CV. The permutation control moves each patient's
whole outcome block to another patient with the same number of scans, keeps features and folds, and re-runs the full
nested pipeline 100 times; p = (1 + #{perm ≥ obs}) / 101.

| | Grade 4 | All gliomas |
|---|---|---|
| Post-hoc best configuration (optimistic) | boosting, clinical + timing: 0.714 [0.643, 0.785] | ridge, clinical + timing + volumes + morphology + radiomics: 0.744 [0.679, 0.804] |
| Nested over 126 (honest) | 0.664 [0.601, 0.722], slope 0.49 | 0.707 [0.647, 0.766] |
| Permutation null mean (95th percentile) | 0.548 (0.636) | 0.528 |
| Permutation p | 0.050 (4/100 ≥ observed) | 0.010 (0/100) |

Single groups, grade 4 (ridge / boosting): radiomics 0.675 / 0.628; morphology 0.650 / 0.538; volumes 0.611 / 0.573;
clinical 0.585 / 0.612; timing 0.559 / 0.649; change 0.537 / 0.565. The permutation null is centred above 0.5 because
selecting the best of 126 configurations is optimistic even without signal. Boosting was chosen in 15/25 outer folds;
selected boosting models had large train–test gaps (for example training AUC 0.961 for the best grade 4 configuration).

---

## S11. Phase-of-care ladder: full results

Source: `docs/results/PHASE_LADDER.md`; `outputs/results/analyses/phase_ladder/{results,cohorts,permutation,
subset_of_full,nested_choices}.csv`; `docs/manuscript/figures/fig4_phase.csv`.

**Phase definitions** (grade 4 / all-glioma scans): pre-RT, `rt_started == 0`, including patients with no RT documented
(76 / 115); during RT, started but not completed (6 / 8); early post-RT, completed and ≤ 84 d after RT end (98 / 104);
later post-RT, > 84 d (69 / 81). RT without a documented start date counts as started; RT without an end date is never
"completed".

**Table S15. Cohorts.**

| Population · cohort | Scans | Patients | Events | Non-events | Censored | EPP R2 (10 params) | EPP R2 + I2 (54) |
|---|---|---|---|---|---|---|---|
| Grade 4 · full | 249 | 126 | 93 | 117 | 39 | 9.3 | 1.7 |
| Grade 4 · post-RT | 167 | 84 | 83 | 83 | 1 | 8.3 | 1.5 |
| Grade 4 · later post-RT | 69 | 40 | 36 | 32 | 1 | 3.6 | 0.7 |
| All · full | 308 | 155 | 100 | 156 | 52 | 10.0 | 1.9 |
| All · post-RT | 185 | 92 | 84 | 96 | 5 | 8.4 | 1.6 |
| All · later post-RT | 81 | 46 | 37 | 40 | 4 | 3.7 | 0.7 |

By the Riley criteria (anticipated R²cs 15% of maximum), the primary post-RT cohort would need about 750 scans (375
events) for R2 and about 4,040 scans (2,022 events) for R2 + I2. Nearly all censoring is in pre-RT and early scans. In
post-RT cohorts two phase dummies are constant, so R2 has about 8 effective parameters (exploratory note).

**Table S16. Primary and key secondary results** (grade 4, post-RT, ridge).

| Model | AUC (95% CI) | Δ vs R2 (95% CI) | Slope | O/E |
|---|---|---|---|---|
| R2 (clinical + phase) | 0.549 (0.458–0.642) | — | 0.76 | 0.99 |
| R2 + I2 (primary) | 0.610 (0.529–0.688) | +0.061 (−0.038, +0.156) | 0.68 | 0.99 |
| R2 + I3 (key secondary) | 0.609 (0.543–0.676) | +0.061 (−0.041, +0.157) | 0.44 | 0.96 |
| R2 + I1 | 0.593 | +0.044 (−0.054, +0.137) | 0.60 | 0.98 |
| R2 + I4 | 0.625 | +0.076 (−0.041, +0.192) | 0.30 | 0.97 |
| R3 (baseline), reference | 0.604 (0.520–0.690) | — | 0.85 | 0.99 |

Permutation test of the primary contrast: p = 0.208 (20 of 100 permutations ≥ +0.061; p = 21/101); null mean +0.028,
median +0.025, range −0.104 to +0.162. The nested radiomics choice was unstable (most common configuration in 12 of 25
outer folds).

**Table S17. Bases by cohort (grade 4, ridge; AUC [95% CI])** (`fig4_phase.csv`).

| Base | Full | Post-RT | Later post-RT |
|---|---|---|---|
| R0 clinical | 0.585 [0.496, 0.666] | 0.552 [0.456, 0.646] | 0.343 [0.281, 0.418] |
| R1 + timing | 0.644 [0.560, 0.721] | 0.572 [0.485, 0.667] | 0.388 [0.291, 0.503] |
| R2 + phase | 0.664 [0.569, 0.753] | 0.549 [0.458, 0.642] | 0.376 [0.294, 0.470] |
| R3 baseline | 0.698 [0.615, 0.774] | 0.604 [0.520, 0.690] | 0.472 [0.339, 0.617] |

Full grade 4 cohort: R1 − R0 +0.059 (−0.016, +0.133); R2 − R0 +0.080 (+0.005, +0.152); R3 − R0 +0.113 (+0.026,
+0.208); R3 − R2 +0.034 (−0.027, +0.090). R2 + I1 0.696 vs R3 0.698 (Δ −0.002, −0.081 to +0.074). Imaging on top of
each base (full grade 4; I1 / I2 / I3 / I4): R0 +0.074 / +0.071 / +0.065 / +0.063; R1 +0.030 / +0.026 / +0.008 / +0.018;
R2 +0.031 / +0.023 / +0.002 / +0.020; R3 +0.004 / −0.007 / −0.032 / −0.004; no CI excludes 0. Post-RT grade 4 (I1 /
I2 / I3 / I4): R0 +0.049 / +0.058 / +0.046 / +0.079; R1 +0.030 / +0.038 / +0.042 / +0.060; R2 +0.044 / +0.061 / +0.061 /
+0.076; R3 +0.008 / +0.017 / +0.005 / +0.039; no CI excludes 0. All gliomas, full: R0 0.619, R1 0.693, R2 0.700, R3
0.720. Boosting (secondary): grade 4 full R2 0.698, R1 0.693; imaging never helped boosting (−0.027 to +0.007); post-RT
R2 + I2 vs R2 +0.012 (−0.069, +0.102).

**Sensitivity analyses.** Later post-RT only (grade 4: 69 scans, 40 patients, 36 events): bases below chance (R0 0.343,
calibration slope −2.0), the known negative bias of CV for near-null models with few events; large ΔAUCs there (e.g.
R2 + I3 +0.250) are measured against a below-chance reference and are not evidence. Full-cohort models evaluated on
post-RT scans only: grade 4 R2 0.570, R2 + I2 0.620, Δ +0.050 (−0.061, +0.157); R3 0.638, R3 + I2 Δ −0.014. Exploratory:
age alone 0.586 in grade 4 post-RT; age + I2 vs age +0.022 (−0.103, +0.145). LUMIERE could not be used: no RT dates; the
rater flag marks 27 of 132 scans and leaves 83 scans with unknown phase.

---

## S12. Secondary analyses

### S12.1 Literature baselines and tuning

Source: `docs/results/BASELINES.md`.

**Table S18. MU ladder (reference = baseline ridge).**

| Model | Grade 4 AUC [95% CI] | Δ [95% CI] | All AUC [95% CI] | Δ [95% CI] |
|---|---|---|---|---|
| Baseline ridge (reference) | 0.698 [0.615, 0.774] | — | 0.720 [0.638, 0.792] | — |
| Clinical only | 0.585 [0.496, 0.666] | −0.113 [−0.208, −0.026] | 0.619 [0.540, 0.696] | −0.101 [−0.177, −0.031] |
| Timing only | 0.559 [0.475, 0.637] | −0.139 [−0.214, −0.070] | 0.607 [0.528, 0.684] | −0.112 [−0.175, −0.059] |
| Clinical + timing | 0.644 [0.560, 0.721] | −0.054 [−0.103, −0.012] | 0.693 [0.617, 0.766] | −0.027 [−0.061, +0.007] |
| B0 log ET volume | 0.636 [0.541, 0.723] | −0.062 [−0.183, +0.043] | 0.673 [0.591, 0.752] | −0.046 [−0.142, +0.054] |
| B0 ΔET vs previous | 0.546 [0.479, 0.614] | −0.153 [−0.241, −0.056] | 0.531 [0.465, 0.590] | −0.189 [−0.285, −0.101] |
| B1 volumetric RANO-style rule | 0.551 [0.480, 0.620] | −0.147 [−0.239, −0.062] | 0.554 [0.488, 0.615] | −0.166 [−0.258, −0.087] |
| B1 rule, RANO 2.0 window | 0.508 [0.440, 0.577] | −0.191 [−0.289, −0.098] | 0.509 [0.448, 0.568] | −0.210 [−0.301, −0.119] |
| B4 Hashim-style Cox | 0.628 [0.538, 0.711] | −0.070 [−0.179, +0.031] | 0.678 [0.596, 0.755] | −0.041 [−0.120, +0.039] |

The B1 rule: ET ≥ 40% and ≥ 1 cc above the past-only nadir (measurable nadir ≥ 0.1 cc), or ≥ 1 cc from a ~0 cc nadir;
positive in 25% of grade 4 scans. Nested hyperparameter grids: every tuned arm within ±0.025 of the baseline, all CIs
include 0 (e.g. nested over ridge + boosting −0.024 [−0.061, +0.011], grade 4); choices were unstable.

### S12.2 Sensitivity of the primary comparison

Source: `docs/results/SENSITIVITY.md`.

| Sensitivity | Scans / patients | Events / censored | Baseline AUC [95% CI] | + radiomics (nested) | ΔAUC [95% CI] |
|---|---|---|---|---|---|
| Primary: grade 4, 120 d | 249 / 126 | 93 / 39 | 0.698 [0.615, 0.774] | 0.666 | −0.032 [−0.084, +0.017] |
| Horizon 90 d | 249 / 126 | 62 / 35 | 0.663 [0.577, 0.739] | 0.664 | +0.001 [−0.057, +0.063] |
| Horizon 180 d | 249 / 126 | 131 / 43 | 0.667 [0.573, 0.752] | 0.636 | −0.032 [−0.092, +0.022] |
| Composite (progression or death) | 249 / 126 | 107 / 25 | 0.642 [0.566, 0.713] | 0.629 | −0.013 [−0.073, +0.052] |
| Alternative progression date | 244 / 124 | 92 / 39 | 0.670 [0.578, 0.757] | 0.648 | −0.023 [−0.066, +0.019] |
| Imaging-only follow-up | 249 / 126 | 93 / 43 | 0.685 [0.600, 0.761] | 0.667 | −0.018 [−0.070, +0.033] |
| All gliomas | 308 / 155 | 100 / 52 | 0.720 [0.638, 0.792] | 0.747 | +0.028 [−0.017, +0.071] |
| Excluding 12-week post-RT scans | 151 / 90 | 46 / 39 | 0.725 [0.602, 0.834] | 0.727 | +0.002 [−0.064, +0.067] |
| Excluding patient 0145 (conflicting dates) | 247 / 125 | 93 / 39 | 0.691 [0.602, 0.776] | 0.687 | −0.004 [−0.058, +0.048] |

### S12.3 Class imbalance

Source: `docs/results/IMBALANCE.md`. Event shares are 44% (grade 4) and 39% (all gliomas), a mild imbalance. Over
learners (ridge, boosting, XGBoost, LightGBM, nested variants) × re-balancing (none, class weights, patient-aware
oversampling, SMOTE with neighbours from other patients), ΔAUC against the ridge baseline ranged from −0.031 to +0.023;
4 of 190 CIs excluded 0 (ridge, all gliomas, +0.009 to +0.014). Re-balancing shifted predicted risk upward as expected
from a prior shift (median O/E 1.01 without re-balancing vs 0.88–0.89 with it) and raised Brier. Grade 4 ridge with
class weights: ΔAUC +0.008 [−0.001, +0.019], O/E 1.04 → 0.94. Fixed small-data XGBoost: +0.006 [−0.060, +0.072] (grade 4);
nested-tuned XGBoost had calibration slope about 0.6 and transported worse to LUMIERE (0.562 vs 0.608). No re-balancing
is used in any reported model.

### S12.4 Schedule coupling

Source: `docs/results/SCHEDULE_COUPLING.md`. The interval to the next MRI is unknown at prediction time and partly
caused by the outcome (scans are brought forward when progression is suspected), so conditioning on it is a
conservative test. Grade 4: positive rate 0.54 when the next scan is ≤ 60 d away and 0.10 when > 180 d; interval alone
AUC 0.639 [0.555, 0.721]. Baseline AUC within interval tertiles 0.718 / 0.762 / 0.617; conditional AUC (pairs within a
tertile) 0.687 [0.595, 0.768]; logit coefficient per SD 0.91 → 0.86 [0.43, 1.41] after adjusting for log interval;
baseline features cannot predict the interval (grouped-CV R² −0.05). Excluding early post-RT scans and scans whose next
scan is > 120 d away: 0.777 [0.653, 0.891] (85 scans). Nested radiomics conditional AUC 0.654, below the baseline. In
LUMIERE the interval alone scores 0.788 [0.703, 0.868], and the + volumes boosting model's coefficient is no longer
distinguishable from 0 after adjustment (0.37 [−0.14, 0.89]).

### S12.5 Feature conflicts

Source: `docs/results/FEATURE_CONFLICTS.md`. No feature group measurably hurts: every leave-one-group-out contrast that
would mean "group hurts" has a CI including 0; adding any imaging group to the baseline changes AUC by −0.004 to
+0.019 (CIs span 0). The conflict is redundancy: timing and treatment encode the same RT-status information
(interaction −0.066 to −0.073, CI excluding 0 in 3 of 4 population × learner cells). Within the baseline, 9 design
columns are exactly collinear (VIF = ∞) and 16 have VIF > 10; "RT completed" appears in at least five columns.
Pre-stated pruning evaluated nested: ΔAUC −0.018 to +0.011, all CIs include 0; the same rule applied once globally gives
+0.009 to +0.018, which is selection optimism.

### S12.6 SHAP attributions

Source: `docs/results/SHAP.md`. Ridge: exact linear SHAP on in-fold standardised features; boosting: TreeSHAP
(path-dependent), additivity checked to 10⁻⁶; explanations out of fold, 25 fits. Group share = mean |per-scan group
sum| / sum over groups.

| Model (grade 4) | OOF AUC | Group shares |
|---|---|---|
| Baseline ridge | 0.698 | treatment 58%, clinical 25%, timing 17% |
| Baseline boosting | 0.687 | treatment 51%, clinical 35%, timing 14% |
| Full non-radiomics ridge | 0.692 | treatment 34%, morphology 21%, change 15%, clinical 13%, volumes 10%, timing 8% |
| Full non-radiomics boosting | 0.694 | treatment 26%, morphology 23%, clinical 21%, change 13%, volumes 13%, timing 3% |
| Baseline + radiomics score (post hoc configuration) | 0.721 | treatment 48%, clinical 20%, timing 16%, radiomics 16% |

Time-relative features hold 35% (ridge) / 47% (boosting) of feature-level credit in the baseline. Imaging takes 45% /
51% of credit in the full models without an AUC gain. On LUMIERE, the locked ridge's under-prediction is driven by
`idh_unknown` (mean −0.71 logits; mean |SHAP| 0.77 on LUMIERE vs 0.13 on MU), by lower DeepBraTumIA ET volumes (−0.32
logits) and by a missingness indicator that is never set in LUMIERE.

### S12.7 Calibration, decision curves, added value and sample size

Source: `docs/results/CLINICAL_UTILITY.md`.

| Model (grade 4) | AUC | O/E (weighted) | CITL [95% CI] | Slope [95% CI] | ICI |
|---|---|---|---|---|---|
| Baseline ridge | 0.698 | 0.96 | −0.09 [−0.42, 0.28] | 0.89 [0.50, 1.43] | 0.032 |
| Baseline boosting | 0.687 | 0.94 | −0.12 [−0.47, 0.23] | 0.82 [0.44, 1.31] | 0.039 |
| Baseline + radiomics (nested) | 0.666 | 0.94 | −0.13 [−0.46, 0.25] | 0.60 [0.33, 0.93] | 0.063 |
| Baseline + deep (nested D1) | 0.694 | 0.94 | −0.15 [−0.52, 0.28] | 0.55 [0.28, 0.91] | 0.085 |

| Net benefit (grade 4, IPCW) | 10% | 20% | 30% |
|---|---|---|---|
| Treat all | 0.369 | 0.291 | 0.189 |
| Baseline ridge | 0.372 | 0.300 | 0.232 |
| Δ radiomics (nested) | −0.000 [−0.004, 0.004] | −0.001 [−0.013, 0.011] | −0.020 [−0.038, −0.004] |
| Δ boosting | −0.002 [−0.007, 0.001] | −0.007 [−0.021, 0.006] | −0.011 [−0.039, 0.013] |
| Δ deep (nested D1) | −0.002 [−0.013, 0.006] | +0.002 [−0.014, 0.018] | +0.001 [−0.023, 0.026] |

Added value vs baseline (continuous NRI; IDI): radiomics +0.17 [−0.05, 0.41]; +0.000 [−0.030, 0.029]. Deep +0.48
[0.24, 0.73]; +0.036 [−0.009, 0.082]. The positive NRI reflects upward risk shifts in events by over-fitted models;
ΔAUC and Δ net benefit are null (Pencina et al., 2008). All gliomas: radiomics Δ net benefit +0.011 [0.004, 0.020] at
10% and +0.014 [0.001, 0.027] at 20%, with ΔAUC +0.028 [−0.017, +0.071]; nothing similar in grade 4. LUMIERE locked
boosting: net benefit ≈ treat-all (0.218 vs 0.222 at 20%).

**Sample size (Riley et al., 2020; grade 4).** 210 verified scans, 93 events, outcome proportion 0.443, R²cs 0.119
(from AUC 0.698). Baseline with 31 design columns: 3.0 events per parameter; required 2,190 scans (970 events) by the
shrinkage criterion. Adding 10 radiomics features: 2,896; the full radiomics pool (2,477 candidate parameters): 174,942.
Requirements assume independent scans, so the shortfall is understated.

---

## S13. External evaluation on LUMIERE: full results

Source: `docs/results/EXTERNAL_LUMIERE.md`; `outputs/results/external_lumiere/results.csv`.

Shared features: age, sex, IDH and MGMT (with unknown), log days since surgery, < 3 months post-RT flag, log ET /
necrosis + cavity / SNFH volumes (DeepBraTumIA; 14 of 132 index scans without usable volumes, imputed with MU training
medians inside the locked pipeline).

**Table S19. Models trained on MU grade 4.** Pooled locked AUC [95% CI] and O/E; other columns are per-fold means.

| Features | Learner | MU CV | Locked, pooled | O/E | Locked, per fold | Fine-tuned (shrink) | Fine-tuned (pooled) | LUMIERE only |
|---|---|---|---|---|---|---|---|---|
| Clinical | ridge | 0.585 | 0.610 [0.487, 0.737] | 1.15 | 0.558 | 0.544 | 0.505 | 0.396 |
| Clinical | boosting | 0.625 | 0.627 [0.514, 0.731] | 0.86 | 0.624 | — | 0.560 | 0.520 |
| Clinical + timing | ridge | 0.612 | 0.610 [0.497, 0.737] | 0.98 | 0.603 | 0.591 | 0.603 | 0.586 |
| Clinical + timing | boosting | 0.664 | 0.632 [0.501, 0.748] | 0.84 | 0.643 | — | 0.632 | 0.627 |
| Volumes | ridge | 0.611 | 0.545 [0.410, 0.653] | 1.00 | 0.521 | 0.531 | 0.567 | 0.569 |
| Volumes | boosting | 0.591 | 0.529 [0.389, 0.644] | 1.00 | 0.515 | — | 0.513 | 0.518 |
| **Clinical + timing + volumes** | **ridge** | 0.667 | **0.608 [0.469, 0.739]** | **1.33** | 0.598 | 0.606 | 0.617 | 0.580 |
| **Clinical + timing + volumes** | **boosting** | 0.675 | **0.620 [0.495, 0.733]** | **0.99** | 0.608 | — | 0.658 | 0.610 |

Recalibration equals locked per fold (pooled O/E 0.93–0.97). No adaptation arm has a ΔAUC CI above 0; LUMIERE-only is
significantly worse for clinical ridge (Δ −0.162 [−0.238, −0.066]). Cohort normalisation of volumes (rank) raised the
pooled locked AUC of every volume model (+0.007 to +0.069); clinical + timing + volumes boosting 0.620 → 0.659 [0.529,
0.767], per-fold Δ +0.047 [−0.002, +0.110]. This is transductive and a sensitivity analysis only. All-glioma-trained
locked clinical + timing + volumes: ridge 0.599 [0.462, 0.728] (O/E 1.30), boosting 0.619 [0.477, 0.740] (O/E 1.04).

**Deep features on LUMIERE** (118 scans with deep features; `deep/lumiere/locked.csv`): grade 4 clinical + timing 0.622
→ + deep 0.679 (Δ +0.057 [−0.132, +0.235], O/E 2.08); random encoder same configuration 0.667 (+0.045). With volumes:
0.635 → 0.725 (+0.089 [−0.026, +0.215]). All gliomas: +0.064 [−0.011, +0.144]; with volumes +0.050 [+0.002, +0.109].
Pretrained vs random, same configuration: +0.011 to +0.069, no CI above 0. A classifier separates LUMIERE from MU on
deep features with AUC 0.82 / 0.79 / 0.81 (BraTS 2021 / BrainSegFounder / random).

**Shipped PRISM report model** (legacy features re-extracted, 118 scans; files dated 2026-10-09, before the final
LUMIERE label definition): raw 0.613 [0.500, 0.729] pooled (O/E 1.24); recalibrated O/E 0.98; fine-tuned 0.570 pooled.

**Literature baselines on LUMIERE** (locked; `BASELINES.md`): clinical + timing 0.610 [0.497, 0.737]; Hashim-style Cox
0.640 [0.508, 0.754] (Δ +0.030 [−0.080, +0.127]); volumetric RANO-style rule 0.559.

**Harmonisation note.** DeepBraTumIA ET and SNFH medians (grade 4: 0.61 and 19.11 cc) are far below MU's (5.45 and
42.85 cc). The harmonised necrosis + cavity definition is correct but did not improve transfer in a development run
(`FIX_FEATURES.md` §1).

---

## S14. Imaging-defined label, imaging diagnostics and re-segmentation

Source: `docs/results/CLEAN_LABEL.md`; `docs/results/DIAGNOSTICS_IMAGING.md`; `docs/results/RESEGMENTATION.md`;
`outputs/results/analyses/{clean_label,diagnostics_imaging,reseg}/`.

**Imaging-defined label.** MU codes the type of first progression: imaging, clinical only, or both. Censoring the
clinical-only progressions at their progression date changed grade 4 events from 93 (44 / 12 / 37 by type) to 81 and
censored scans from 39 to 51; no non-event changed. Primary (grade 4, full, ridge): clinical 0.563 (0.474–0.642);
baseline 0.696 (0.610–0.776); imaging (volumes + change) 0.628 (0.549–0.701), Δ −0.068 (−0.167, +0.033); baseline +
imaging 0.722 (0.639–0.799), Δ +0.027 (−0.033, +0.082). On the original label, baseline + imaging was 0.694 (Δ −0.004,
−0.060 to +0.051). Secondary contrasts (post-RT, all gliomas, boosting) gave baseline + imaging Δ +0.008 to +0.028 with
all CIs including 0; imaging alone in all gliomas was worse than the baseline (−0.090, −0.176 to −0.007). Within-LUMIERE
CV with the expert RANO label: every model at or below chance (ridge clinical + timing 0.466), so LUMIERE cannot answer
the label question. Rule not met.

**Volume cross-check against the dataset's own volume table (pass).** Pearson r: ET 0.9998 (exact voxel match 98.3%),
SNFH 0.9994 (99.7%), RC 0.9993 (94.1%), NETC 0.9957 (83.7%); disagreements are concentrated in seven patients with extra
timepoints or a second mask version in the table. Measurement volumes equal mask voxel counts exactly. Label mapping:
diagonal agreement 0.94–0.97, off-diagonal ≤ 0.003. Intensities agree with labels (ET/brain on T1c median 1.45, > 1 in
98% of scans; SNFH/brain on FLAIR median 1.44, > 1 in 100%).

**Concurrent detection (positive control; fail).** Progression scan = first MRI with a mask on or after the documented
progression date (120 scans, all gliomas).

| Comparison (imaging only, 5 × 5 grouped CV; ridge / boosting) | All gliomas | Grade 4 |
|---|---|---|
| Progression scans vs all index scans | 0.62 [0.57, 0.67] / 0.63 | 0.62 / 0.63 |
| Progression scans vs verified 120-d negatives | 0.68 [0.62, 0.74] / 0.70 | 0.65 / 0.66 |
| Both groups with a prior scan | 0.62 / 0.61 | 0.60 / 0.62 |

Progression scan vs the same patient's previous scan (74 pairs): ET larger in 49% (Wilcoxon p = 0.54); lesion larger in
65% (p = 0.033); lesion growth from nadir larger in 79% (n = 42, p = 0.0003); ET growth from nadir 50% (p = 0.95). By
progression type: imaging (40 pairs) ET larger in 50%; imaging + clinical (27) 52%; clinical only (7) 29%.

**Why the control fails.** Between consecutive scans ≤ 14 days apart (n = 25), the median change was 3.2-fold in ET and
1.8-fold in lesion volume, larger than over 45–90 day gaps; across 389 pairs the size of the change was unrelated to the
gap (Spearman −0.01, p = 0.83). Some short-gap jumps straddle a re-resection; others (four patients) are implausible.

**Label–date alignment (pass).** The progression date coincides with an MRI for 62% of progressors (±7 d: 69%; 30 d:
73%); 22% of progressors have no MRI on or after the progression date. Positives: median time to progression 66 d (IQR
44–92); 76% are the last scan before progression. Agreement between the 120-d label and "the next scan is the
progression scan": 79% (κ = 0.53).

**Horizon curve (grade 4, IPCW AUC(H); imaging / clinical + phase / both).** 60 d: 0.63 / 0.55 / 0.65; 90 d: 0.62 / 0.63
/ 0.68; 120 d: 0.60 / 0.66 / 0.69; 180 d: 0.58 / 0.59 / 0.63; 270 d: 0.59 / 0.55 / 0.63. Imaging stays at about 0.6 at
every horizon; 30-d estimates (16 events) are not interpretable.

**Data issues to report to the data owners.** Three scan pairs from different patients have identical masks
(0018_T5 / 0032_T5, 0060_T2 / 0062_T2, 0113_T1 / 0132_T1) and four further pairs are near-identical; a few implausible
within-days volume jumps; 15 of 96 recorded deaths precede a dated MRI (S3).

**Re-segmentation.** BraTS 2021 SwinUNETR and BrainSegFounder were run on all 594 complete scans (sliding window, ROI
128³, overlap 0.5; labels written in the MU convention; RC taken from the MU mask where the new map is background,
because BraTS models have no cavity class and label most of the cavity as NETC, so tumour core is not comparable).

| Agreement with MU masks | Dice ET median [IQR] | Dice WT | Pearson log-volume ET / WT |
|---|---|---|---|
| BraTS 2021 SwinUNETR | 0.80 [0.49, 0.91] | 0.85 [0.74, 0.93] | 0.92 / 0.91 |
| BrainSegFounder | 0.81 [0.56, 0.91] | 0.86 | 0.94 / 0.92 |

Short-gap consistency (≤ 30 d, 54 pairs): median ET fold change 2.57 → 2.17 (Δ median |log ratio| −0.17 [−0.46, −0.02]);
WT unchanged. Positive controls with the new masks: primary detection (progression scan vs verified negatives, ridge)
0.681 → 0.665, Δ −0.016 [−0.057, +0.025] (BrainSegFounder 0.677); ET larger at progression 49% → 45% (BrainSegFounder
41%). Forward 120-d task, imaging only: all gliomas 0.644 → 0.675, Δ +0.031 [−0.017, +0.084]; clinical + phase +
imaging 0.712 → 0.740, Δ +0.029 [−0.010, +0.069]. An exploratory plain-AUC boosting gain (+0.059 [+0.014, +0.107]) was
one of more than 20 comparisons, not pre-specified and not confirmed by the IPCW ridge estimate. Verdict by the
pre-specified rule: the new segmentation does not help.

---

## S15. The auditable layer: full results and an example audit record

Source: `docs/results/AUDIT_SYSTEM.md`; `outputs/results/analyses/audit_system/`. Run: 2026-10-15, `python -m prism
audit --workers 24`, 114 s. Checks (`checks.csv`): CV predictions reproduce the baseline OOF predictions (max |Δ|
1.7 × 10⁻¹⁶); intercept + Σ contributions = logit (max error 1.3 × 10⁻¹⁵). Code changes after the plan were confined to
an as-of rule for demographics, a NaN rule for one-class strata, and a shared estimator for referral subsets; none
changed a model or a rule.

**Locked artifact and model card.** Grade 4: 249 training scans, 126 patients, 210 verified, 93 events; C = 0.1;
conformal threshold q at α = 0.2 / 0.1: 0.613 / 0.683 (all gliomas 0.529 / 0.620). Out of scope: pseudoprogression
diagnosis; cohorts without treatment fields (including LUMIERE); other institutions without validation.

**Table S20. Example audit records** (out-of-fold, repeat 0, grade 4; label shown for evaluation only).

| Scan | Phase | Risk [95% bootstrap] | Conformal set α = 0.2 | Flags | 120-d label |
|---|---|---|---|---|---|
| 0201_T3 | pre-RT | 0.04 [0.01, 0.27] | {0} | OOD (MGMT unknown) | 0 |
| 0136_T2 | during RT | 0.47 [0.36, 0.77] | {0} | none | 1 |
| 0117_T1 | early post-RT | 0.50 [0.39, 0.61] | {0, 1} | (i) 26 d after RT; (iii) | 1 |
| 0059_T1 | early post-RT | 0.48 [0.22, 0.77] | {0, 1} | (i); (ii) rt_start_day below training 1st percentile; (iii) | 0 |
| 0089_T5 | later post-RT | 0.45 [0.34, 0.72] | {0, 1} | (ii) rt_start_day above 99th percentile; (iii) | 1 |
| 0014_T4 | later post-RT | 0.63 [0.44, 0.86] | {1} | none | 0 (set misses) |

**Example record (PatientID_0117_Timepoint_1, day 85 from diagnosis), abridged from `records.md`.**

- Phase of care: early post-RT (≤ 84 d after RT end).
- Risk of documented progression within 120 d: 0.50 (95% bootstrap interval 0.39–0.61); conformal set at α = 0.2 {0, 1}.
- Referral: REFER — early post-RT window (scan 26 d after RT end); uncertain (the α = 0.2 set contains both classes).
- Log-odds: intercept −0.33 + clinical +0.22 + timing −0.14 + treatment +0.24 = −0.01 (check error 5.6 × 10⁻¹⁷).
- Inputs known by scan day: yes, all. Examples: `rt_started` = 1 (source event day 21 ≤ scan day); `rt_completed` = 1
  (day 59); `days_since_rt_end` = 26; prescription 60 Gy in 30 fractions (visible from day 21); `surgery_day` −4.
- Largest terms: `early_post_rt` −0.12; `visit_index` −0.12; `previous_brain_tumor` +0.07; `rt_started` +0.07; `male`
  −0.07; `mgmt_unknown` +0.07 (log-odds).
- Evaluation only: 120-d label 1 (progression at 111 d).

The displayed risk (model fitted on the whole training fold) and the conformal set (model fitted on 70% of training
patients) can disagree in direction (e.g. 0136_T2: risk 0.47, set {0}); this occurred in 1.8% / 2.9% of singleton sets
(exploratory). Median width of the 95% bootstrap interval: 0.37 (IQR 0.32–0.44) in grade 4 and 0.31 in all gliomas.

**Table S21. P1, conformal coverage at α = 0.2** (`conformal.csv`).

| Population | Overall [95% CI] | Pre-RT | During RT | Early post-RT | Later post-RT | Events / non-events | Singleton rate |
|---|---|---|---|---|---|---|---|
| Grade 4 | 0.841 [0.790, 0.885] | 0.868 (0/5 events covered) | 0.567 (6 scans) | 0.871 | 0.806 | 0.824 / 0.855 | 0.595 |
| All gliomas | 0.823 [0.776, 0.865] | 0.850 (0/10) | 0.550 (8 scans) | 0.852 | 0.790 | 0.698 / 0.904 | 0.696 |

Per-patient coverage 0.828 / 0.796. At α = 0.1: 0.949 [0.916, 0.975] / 0.928 [0.896, 0.955], singleton rate 0.296 /
0.422. Conformal model AUC 0.667 / 0.709 (cost of the 70/30 split). Displayed-risk AUC on singleton scans 0.732 / 0.723
(non-singletons 0.628 / 0.594).

**Table S22. P2 and referral rules** (`p2.csv`, `referral.csv`, `referral_within_phase.csv`).

| | Realised coverage | AUC retained [95% CI] | Composition-matched | Random removal | P2 [95% CI] |
|---|---|---|---|---|---|
| Grade 4 | 0.671 | 0.731 [0.635, 0.812] | 0.725 | 0.698 | +0.006 [−0.023, +0.036] |
| All gliomas | 0.685 | 0.735 [0.654, 0.820] | 0.733 | 0.720 | +0.003 [−0.031, +0.036] |

| Grade 4 rule | Referred | AUC kept | AUC referred | Random removal | Composition-matched |
|---|---|---|---|---|---|
| (i) early post-RT | 39.4% (98 scans, 47 events) | 0.723 | 0.663 | 0.699 [0.673, 0.723] | 0.723 (the rule itself) |
| (ii) out of distribution | 29.8% | 0.671 | 0.665 | 0.698 | 0.695 |
| (iii) uncertain | 40.5% | 0.732 | 0.628 | 0.699 | 0.734 [0.709, 0.760] |
| any of (i)–(iii) | 72.6% | 0.735 | 0.687 | 0.698 | 0.753 |

Within-phase AUC (grade 4 / all): pre-RT 0.555 / 0.493; during RT 0.448 / 0.671; early post-RT 0.663 / 0.678; later
post-RT 0.597 / 0.644. On OOD-referred scans the model over-predicts (O/E 0.70, slope 0.66).

**Shortcut audit.** Unknown marker share by 120-d label (progression / no progression / censored), grade 4: IDH unknown
0/93, 6/117, 5/39; MGMT unknown 6/93, 25/117, 8/39. Dropping both unknown indicators: grade 4 0.676 [0.592, 0.752], Δ
−0.023 [−0.047, −0.001]; also dropping `rt_date_unknown` Δ −0.022 [−0.045, −0.001]; all gliomas Δ −0.011 [−0.031,
+0.008]. Timing only 0.559, Δ −0.139 [−0.214, −0.070]; treatment only 0.701 [0.622, 0.776], Δ +0.003 [−0.050, +0.048]
(all gliomas 0.710, Δ −0.009).

**Table S23. Subgroups (grade 4; † fewer than 10 events, descriptive).**

| Stratum | Scans / events | AUC [95% CI] | Slope | O/E [95% CI] |
|---|---|---|---|---|
| GBM | 214 / 86 | 0.68 [0.58, 0.76] | 0.78 | 1.10 [0.90, 1.31] |
| Non-GBM grade 4 † | 35 / 7 | 0.72 [0.54, 0.95] | 1.34 | 0.66 [0.30, 1.00] |
| MGMT methylated | 88 / 34 | 0.64 [0.52, 0.77] | 0.62 | 0.99 |
| MGMT unmethylated | 122 / 53 | 0.72 [0.61, 0.84] | 1.11 | 1.14 |
| IDH wild type | 208 / 87 | 0.66 [0.56, 0.77] | 0.78 | 1.09 |
| Male / female | 119 / 44, 130 / 49 | 0.67 [0.55, 0.79] / 0.72 [0.61, 0.83] | 0.85 / 0.94 | 1.02 / 1.06 |
| Age ≤ 56.7 / (56.7, 67] / > 67 | 109 / 30, 68 / 35, 72 / 28 | 0.71 / 0.64 / 0.68 | 0.89 / 0.73 / 0.89 | 0.81 / 1.39 [1.07, 1.77] / 1.06 |
| Early post-RT | 98 / 47 | 0.66 [0.55, 0.76] | 1.06 | 0.95 |
| Later post-RT | 69 / 36 | 0.60 [0.45, 0.74] | 0.50 | 1.03 |

The middle age tertile is under-predicted (O/E CI excludes 1); uncorrected for 19 strata. Field strength, scanner and
race could not be audited (no acquisition metadata in MU).

**LUMIERE transport audit** (shared-feature ridge, grade-4-trained; reproduces AUC 0.608, O/E 1.33). Largest
standardised mean differences MU → LUMIERE: `idh_unknown` +0.97 (4.4% → 40.9%), `log_et_cc` −0.84, `early_post_rt`
−0.72, `log_snfh_cc` −0.56. Mean contribution shift: `idh_unknown` −0.68 logits; net linear-predictor shift −0.64.
Refit without the molecular unknown indicators: LUMIERE O/E 1.33 → 0.89, slope 0.38 → 0.73, AUC 0.608 → 0.614 (all
gliomas O/E 1.30 → 0.96). MU-calibrated conformal coverage on LUMIERE (α = 0.2): 0.715 (events 0.340, non-events 0.947).

**Table S24. Explanation stability** (`stability_summary.csv`).

| | Grade 4: 25 CV fits | Grade 4: 200 bootstraps | All: CV | All: bootstrap |
|---|---|---|---|---|
| Kendall τ-b, \|coef\| vs locked, median (IQR) | 0.63 (0.56–0.67) | 0.42 (0.36–0.49) | 0.54 (0.48–0.60) | 0.39 (0.32–0.46) |
| Top-5 overlap, mean (all 5 identical) | 0.67 (4%) | 0.52 (1.5%) | 0.65 (4%) | 0.52 (2%) |
| Minimum sign agreement over the top 5 | 1.00 | 0.92 | 1.00 | 0.97 |
| Features with sign agreement ≥ 0.9 | 61% | 55% | 68% | 61% |

Locked top 5 (grade 4): `rt_start_day`, `previous_brain_tumor`, `idh_unknown`, `rt_started`,
`biopsy_before_resection`. Group shares of mean |contribution|: treatment 51%, timing 25%, clinical 24%. On a LUMIERE
refit of the shared-feature model, 9 of 11 coefficients keep the MU sign; `early_post_rt` and the necrosis + cavity
volume flip.

---

## S16. Reproducibility

Every stage is a command of one Python package (`python -m prism <stage>`), wrapped by numbered scripts in `scripts/`
(`run_all.sh` with a `--to STEP` option). Shared fold assignments are in `outputs/data/folds.csv`; every analysis
writes its outputs, a `run_info.json` and a log under `outputs/`. Seeds are fixed (bootstrap, permutations, conformal
splits). The audit layer writes a `MANIFEST.json` with SHA-256 hashes of inputs, code and outputs, the git state and
package versions (one recorded drift: scipy 1.17.1 installed against 1.18.1 in the lock file). Pretrained weights are
downloaded locally and not redistributed. Unit tests cover label rules, as-of-scan treatment features, feature fixes and
the repeated-CV estimator. Commands for each analysis are listed at the end of the corresponding result document in
`docs/results/`. [PENDING: public code release and tag.]

---

## S17. Reporting checklists cross-referenced to the manuscript

Item wording: TRIPOD+AI (Collins et al., 2024), `docs/manuscript/CHECKLIST_TRIPOD_AI.md`; CLEAR (Kocak et al., 2023
[CHECK]), `docs/manuscript/CHECKLIST_CLEAR.md`. "M" = main text section; "S" = Supplement section.

**TRIPOD+AI.**

| Item | Topic | Where reported |
|---|---|---|
| 1 | Title | Title (development + external evaluation, population, outcome) |
| 2 | Abstract | Structured abstract |
| 3a–c | Background, intended use, inequalities | M1; intended use in Key points and S15 model card; inequalities: race not auditable (M4 Limitations, S15) |
| 4 | Objectives | M1 final paragraph |
| 5a–b | Data sources, dates | M2.2; accrual dates: [PENDING — relative days only in both datasets; take from dataset papers] |
| 6a–c | Setting, eligibility, treatments | M2.2–2.3, S2; as-of treatment handling M2.4–2.5, S4 |
| 7 | Data preparation | M2.4, S4, S5, S14 |
| 8a–c | Outcome, assessors, blinding | M2.3, S3; MU assessor not documented, LUMIERE expert RANO; no blinding (M4 Limitations) |
| 9a–c | Predictors | M2.4, S4–S6; MU masks from the dataset, LUMIERE automatic |
| 10 | Sample size | Fixed by public datasets; Riley calculation S12.7, M3.8 |
| 11 | Missing data | In-fold imputation with indicators (M2.4, S4) |
| 12a–g | Analysis methods | M2.5–2.11, S8–S9, S13 (recalibration, locked predictions) |
| 13 | Class imbalance | None used; S12.3 |
| 14 | Fairness | Subgroup audit S15; limits M4 |
| 15 | Model output | Probabilities; decision curves S12.7; no threshold chosen |
| 16 | Development vs evaluation differences | M2.10, S13 |
| 17 | Ethics | Declarations [PENDING] |
| 18a–f | Funding, conflicts, protocol, registration, data, code | Declarations [PENDING]; plans S1; code S16 |
| 19 | Patient and public involvement | Declarations (none) |
| 20a–c | Flow, characteristics, comparison with development data | Table 1, S2 (Figure S1, Table S2) |
| 21 | Participants and events per analysis | Tables 1, S4, S15; each result table |
| 22 | Full model specification | Locked model files and model card (S15) [PENDING: release coefficients] |
| 23a–b | Performance with CIs, subgroups, heterogeneity | M3, Tables 2–3, S11–S15; heterogeneity only MU vs LUMIERE |
| 24 | Model updating | S13 (recalibration, fine-tuning) |
| 25–26 | Interpretation, limitations | M4 |
| 27a–c | Usability, input quality, next steps | S15 (OOD flags, as-of checks), M4 |

**CLEAR (selected items; full table in `CHECKLIST_CLEAR.md`).**

| Items | Topic | Where reported |
|---|---|---|
| 1–6 | Title, abstract, keywords, background, rationale, objectives | Title, Abstract, Keywords, M1 |
| 7–11 | Guidelines, ethics, sample size, study nature, eligibility | M2.1, Declarations, S12.7, M2.3, S2 |
| 13–18 | Data source, overlap, split, imaging protocol, non-radiomic predictors, reference standard | M2.2, S6 (BraTS pretraining overlap risk), M2.6–2.7, S4, S3; MU protocol not distributed |
| 19–24 | Segmentation, pre-processing, resampling, discretisation, image types | M2.2, S5, S14 |
| 25–28 | Extraction method, classes, number, defaults | S5 |
| 29–33 | Missing data, imbalance, reliability, scaling, dimension reduction | S4, S12.3, S5 (ICC filter), S5 |
| 34–37 | Algorithm, tuning, confounders, model selection | M2.7, S5, S12.4 (schedule), M2.8 (phase of care) |
| 38–43 | Testing, metrics, uncertainty, comparisons, explainability | M2.7, M2.10, S9, S12.6 |
| 44–48 | Characteristics, flow, feature statistics, performance, comparison | Table 1, S2, S5, M3, Table 3 |
| 49–52 | Discussion items | M4 |
| 53–58 | Open science | Declarations, S16 [PENDING: release] |

---

## S18. CFB-GBM diffusion analysis

Source: `docs/results/CFB_ADC.md`; `outputs/results/analyses/cfb_adc/{results.csv, rule.json}`; dataset facts
`docs/literature/DATASETS.md`.

**Data.** TCIA CFB-GBM clinical v03, treatment and MRI availability v02, RANO v04, PyRadiomics features v03 on the GTV;
no images used. t0 is the RT-planning MRI; t1 lies a median 14 weeks after t0, about 6–8 weeks after the end of RT,
inside the 12-week pseudoprogression window. t1→t2 labels: 30 progressions among 107 labelled patients. No IDH, MGMT
or progression dates. The RANO label is computed from the GTV volume (RANO sizes equal the PyRadiomics GTV mesh volume,
Spearman 1.00).

**Design.** One row per patient; outcome t1→t2 progressive disease. Feature sets (a) clinical (age, sex, WHO
performance status, WHO edition, RT dose, fractions, delay to RT, weeks t0→t1); (b) + log GTV volume at t1 and change
t0→t1; (c) + T1-Gd and FLAIR first-order and texture at t1 plus GTV shape; (d) + ADC first-order and texture at t1.
Each radiomics block: in-fold 1% clipping, median imputation, variance filter, scaling, top-k univariate F (k ∈ {5,
10}); ridge with C ∈ {0.01 … 3}; k and C by inner stratified 3-fold CV. 20 repeats of stratified 5-fold CV, identical
splits for all sets; patient bootstrap CIs (1,000); 1,000 permutations of the ADC block for the primary contrast.

**Table S25. Results** (AUC = mean over 20 repeats of pooled-OOF ROC AUC).

| Set | Conventional cohort (107 patients, 30 events) | ADC cohort (77 patients, 19 events) |
|---|---|---|
| (a) clinical | 0.501 (0.403–0.596) | 0.565 (0.437–0.689) |
| (b) + GTV volume and change | 0.685 (0.569–0.781) | 0.713 (0.589–0.814) |
| (c) + conventional radiomics | 0.676 (0.575–0.769) | 0.691 (0.576–0.788) |
| (d) + ADC radiomics | 0.696 (0.593–0.785)ᵃ | 0.698 (0.577–0.800) |

| Contrast | Conventional cohort | ADC cohort |
|---|---|---|
| (b) vs (a) | +0.185 (+0.064, +0.293) | +0.148 (+0.031, +0.266) |
| (c) vs (b) | −0.009 (−0.067, +0.051) | −0.022 (−0.074, +0.025) |
| (d) vs (c) | +0.019 (−0.006, +0.045) | **+0.007 (−0.019, +0.035)** (primary; permutation p = 0.151; minimal detectable Δ 0.038) |

ᵃ ADC block imputed for 30 patients without ADC at t1; secondary only. **Rule not met.** Clinical features are at
chance (no molecular markers and no phase variation: every t1 scan is at the same post-RT stage). Volume is the only
informative block and is partly circular with the volumetric label. Conventional texture adds nothing beyond volume;
ADC adds nothing measurable beyond conventional radiomics. Gains larger than about 0.04 are unlikely; smaller gains
cannot be excluded. Perfusion was not available.

---

## Supplementary figures

- **Figure S1.** Cohort flow (`docs/manuscript/cohort_flow.png`).
- **Figure S2.** Split-variance histograms per model, original analysis figure
  (`outputs/results/analyses/split_variance/split_variance.png`; pre-clip radiomics arm — superseded by main Figure 2).
- **Figure S3.** Phase-ladder overview (`outputs/results/analyses/phase_ladder/ladder.png`).
- **Figure S4.** Sensitivity forest plot (`outputs/results/analyses/sensitivity/forest.png`).
- **Figure S5.** Calibration curves and decision curves (`outputs/results/analyses/utility/calibration_dca.png`).
- **Figure S6.** Imaging diagnostics: label–date alignment and horizon curve
  (`outputs/results/analyses/diagnostics_imaging/{alignment,horizon_curve}.png`); visual QA panels (`qa/*.png`).
- **Figure S7.** SHAP summaries for the baseline and full models (`outputs/results/analyses/shap/grade4/*_{bar,beeswarm}.png`).
- [PENDING: export to the journal format.]
