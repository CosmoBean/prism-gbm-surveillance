# Single splits, phase of care and MRI radiomics in post-treatment glioma surveillance: re-evaluation of a radiomics risk model and an auditable clinical alternative

*Draft manuscript, 2026-10-15. Authors, affiliations, ethics, funding and data-availability statements: see
[DRAFT_NOTES.md](DRAFT_NOTES.md). Article type: original research (development and external evaluation of a
multivariable prediction model; TRIPOD+AI and CLEAR reporting).*

**Running title.** Single splits and phase of care in glioma surveillance models

**Keywords.** glioma; glioblastoma; surveillance MRI; tumour progression; radiomics; deep learning; prediction model;
cross-validation; external validation; censoring; selective prediction; model audit

---

## Abstract

**Background.** Models that predict glioma progression from post-treatment MRI are often judged on one held-out
patient split. A radiomics model in an internal report (the PRISM report model) scored AUC 0.80 on one 30-patient
split of the MU-Glioma-Post cohort.

**Purpose.** To test whether that performance survives other splits, censoring-aware labels and a clinical
comparator, and whether MRI adds information once the phase of care is known.

**Methods.** Retrospective study of MU-Glioma-Post (308 post-treatment index scans, 155 patients; grade 4: 249 scans,
126 patients) with locked external evaluation on LUMIERE (132 scans, 61 patients). Outcome: documented progression
within 120 days of the scan, death censored, scored by IPCW AUC(120 d). We re-scored the PRISM report model on its own
split and over 500 splits of the same design, and compared a clinical + timing + as-of-scan treatment ridge model with
radiomics (70 configurations, nested selection) and frozen deep features under 5×5 patient-grouped cross-validation.
Phase-of-care, label, re-segmentation, diffusion and audit-layer analyses had pre-specified rules.

**Results.** On the PRISM report split the PRISM report model scored 0.802 and a model without imaging 0.871; with
treatment dates leaking from the future, a boosting model reached 0.901. Over 500 splits the PRISM report pipeline
averaged 0.720 ± 0.055, and 7% of splits reached 0.802. Under repeated cross-validation the clinical model reached
0.698 (95% CI 0.615–0.774) in grade 4. Radiomics changed this by −0.032 (−0.084 to +0.017) and deep features by −0.004
(−0.069 to +0.063). In post-radiotherapy scans, imaging added +0.061 (−0.038 to +0.156; permutation p = 0.21). Locked
external AUCs were 0.608–0.620. An audit layer met its coverage target (0.841, 0.790–0.885), did not improve discrimination
beyond case mix, and exposed a missingness shortcut.

**Conclusion.** The 0.80 reflected a favourable split. Phase of care, not MRI texture, carried the measurable signal.
Report repeated cross-validation, phase strata and a clinical comparator.

---

## Key points

- **Question.** Does MRI radiomics or deep learning add to clinical and treatment-phase information for predicting
  documented progression within 120 days of a post-treatment glioma MRI, and how far can one patient split mislead?
- **Findings.** On one favourable 29-patient split, models scored 0.80–0.90; the same pipelines averaged about 0.70
  under repeated cross-validation, and the radiomics pipeline averaged 0.720 over 500 splits of the same design.
  Radiomics, frozen deep features and re-segmentation added no measurable discrimination to a clinical +
  treatment-phase model (AUC 0.698 in grade 4), internally or on an external cohort.
- **Meaning.** Single-split AUCs on cohorts of this size measure the split. Imaging-model AUCs that mix pre-radiotherapy
  and surveillance scans are inflated by phase of care. A clinical model with an audit layer can state its uncertainty
  and its weak points, but it does not triage scans better than case mix does.

**Clinical relevance statement.** At a surveillance MRI after glioma treatment, a model built from age, molecular
markers and where the scan sits in the treatment course predicts documented progression within 120 days about as well
as any MRI-based model tested here (AUC about 0.70). Conventional MRI radiomics should not be expected to add to it,
and a single reported test-split AUC near 0.80 should not be taken at face value.

---

## 1. Introduction

Most patients with high-grade glioma progress after surgery and chemoradiotherapy. They are followed with MRI every few
months. Each surveillance scan raises the same question: how likely is it that progression will be documented before
the next decision point? The question is hard for two reasons. First, enhancement can increase after radiotherapy
without tumour growth. This pseudoprogression is most common in the first 12 weeks after chemoradiotherapy and is more
frequent with MGMT promoter methylation (Brandes et al., 2008; Taal et al., 2008). The RANO criteria therefore treat
early post-radiotherapy changes with caution (Wen et al., 2010), and RANO 2.0 asks for confirmation of progression
within the first 12 weeks (Wen et al., 2023). Second, "progression" in routine data is a clinical documentation event.
It depends on imaging, on symptoms and on when the next scan is scheduled. A model that
predicts it is a prognostic model for a pragmatic endpoint, and its intended user is the neuro-oncology team deciding
whether to shorten the interval to the next scan or to act on an equivocal finding. For that use, a well-calibrated
probability with an honest statement of uncertainty matters as much as a high AUC.

Radiomics and deep learning have been proposed to answer this question from the images. Most work addresses an
adjacent task, the separation of pseudoprogression from true progression at a lesion that is already suspicious. Here
pooled AUCs are about 0.77 for machine-learning models (Booth et al., 2022), and diffusion and perfusion measures reach
AUC 0.90–0.93 in meta-analysis (Taylor et al., 2022). Forward prediction from every surveillance scan has received
less attention. On the public MU-Glioma-Post dataset (Mahmoud et al., 2025), a calibrated radiomics model reported
AUC 0.80 on one held-out patient set (Christodoulou et al., 2026), and a nested-CV model of volume increase at the next
scan reported 0.728 (Rai, 2026) [CHECK: Rai 2026 is "repo, unverified (this pass)" in COMPARABLE_RESULTS.md]. An
earlier internal report on the same dataset, which we call the PRISM report, also described a radiomics model (the PRISM
report model) with test AUC 0.80 on one 30-patient split (the PRISM report split). That model is the starting point of
this study.

Three problems are well documented in this literature. First, single train–test splits are unstable in small radiomics
cohorts. Over 1,000 random splits of a brain-tumour radiomics dataset, one split gave 0.882 in training and 0.667 in
testing, and another 0.709 and 0.911 (An et al., 2021). Cross-validation error bars are about ±10% at n = 100
(Varoquaux, 2018). Second, performance drops on external data: 81% of externally validated deep-learning algorithms
lost performance, and 24% lost at least 0.10 (Yu et al., 2022), and only 29.4% of neuro-oncology radiomics studies
were externally validated (Park et al., 2020). Third, clinical-only comparators are rarely reported. Where they are,
they are competitive. In pseudoprogression classification, clinical variables with MGMT reached 0.69 and adding
radiomics made the model significantly worse (Leone et al., 2023). A clinical-only model reached 0.727 externally
against 0.717 for imaging alone (Gomaa et al., 2025). In survival prediction from pre-treatment MRI, clinical
variables reached 0.74 against 0.75 for the combined radiomics model (Abler et al., 2025). These are different tasks,
often with diffusion or perfusion inputs, so their AUCs are context rather than like-for-like comparators. One study
found the reverse: a clinical-only random forest scored 0.52 on a 19-patient test set (Jang et al., 2018).

A fourth problem has received little attention. In the two best-documented clinical comparators, time since the end of
radiotherapy was an input, and in one it was the most influential feature (Gomaa et al., 2025; Leone et al., 2023). A
surveillance cohort mixes scans taken before radiotherapy, during it, in the 12-week pseudoprogression window and in
later follow-up. Event rates differ sharply between these phases. A model that only recognises the phase can rank
scans well when the test set contains many easy phases. We found no study that treats phase of care as a confounder
of imaging-model AUC for forward progression prediction. A related issue is leakage of information that is not yet
available at prediction time (Kapoor & Narayanan, 2023). In routine clinical tables, treatment fields are recorded once
per patient. If they are read as of the end of follow-up, a scan taken before radiotherapy "knows" the radiotherapy
that follows it, and the model learns the phase of care from the future.

We therefore re-evaluated the PRISM report model and asked four questions. (i) What does a single split of this size
do to the AUC, and why was the PRISM report split favourable? (ii) Under repeated, patient-grouped, censoring-aware
evaluation, do MRI radiomics or frozen deep features add to a clinical model that knows where each scan sits in the
treatment course? (iii) Does the answer change within the post-radiotherapy surveillance phase, with a cleaner
imaging-defined label, with a consistent segmenter, on an external cohort, or with diffusion imaging? (iv) If the
imaging gain is absent, what can an auditable clinical model offer at AUC about 0.70? Our contributions are a
split-variance and composition analysis of the single split, a head-to-head of clinical and imaging features under
nested evaluation with internal and external testing, the identification of phase of care as the driver of
discrimination, and an auditable decision-support layer whose value and limits we test against pre-specified criteria.

## 2. Methods

### 2.1 Study design and reporting

This retrospective study of public, de-identified data develops and internally evaluates prediction models on one
cohort (MU-Glioma-Post), evaluates locked models on a second (LUMIERE) and runs a supporting analysis on a third
(CFB-GBM). Reporting follows TRIPOD+AI (Collins et al., 2024) and CLEAR (Kocak et al., 2023 [CHECK]); both checklists
are cross-referenced in Supplementary S17. Analyses labelled *pre-specified* had their plan and decision rule written
into the analysis document and code before any model output of that analysis was seen; for the clean-label, audit and
CFB-GBM analyses a dated plan snapshot was saved before the run (Supplementary S1). Everything else is secondary or
exploratory.

### 2.2 Data sources

**MU-Glioma-Post** (development; Mahmoud et al., 2025) is a single-centre collection of post-operative MRI (T1, T1c,
T2, FLAIR) with four-compartment masks (non-enhancing tumour core, NETC; surrounding FLAIR hyperintensity, SNFH;
enhancing tumour, ET; resection cavity, RC) and a clinical workbook. The workbook gives days from diagnosis to each MRI,
surgery, RT and chemotherapy start and end, first progression and death, plus age, sex, grade, IDH, MGMT and the type of
first progression (imaging, clinical or both). Images carry no acquisition metadata. **LUMIERE** (external; Suter et
al., 2022) is a single-centre longitudinal glioblastoma collection with an expert RANO rating per follow-up, automatic
DeepBraTumIA segmentations, IDH and MGMT, but no RT or chemotherapy dates; its only treatment-time variable is a
"< 3 months after RT" flag. **CFB-GBM** (supporting; TCIA doi:10.7937/v9pn-2f72 [CHECK]) contains 264 patients
treated with the Stupp protocol, imaged at RT planning (t0) and twice afterwards (t1, t2), including ADC, with
volumetric RANO 2.0 labels and precomputed PyRadiomics features on the gross tumour volume (GTV), but no IDH or MGMT. We
used only its released tables.

### 2.3 Index scans and outcome

An index scan is a post-treatment MRI before first documented progression and before late treatment, with all four
sequences and a mask, a known and plausible MRI day, and no recorded death before it. The flow from 596 timepoints of
203 patients to 308 index scans of 155 patients is in Supplementary S2. The grade 4 subset (249 scans, 126 patients) is
the pre-specified primary population. LUMIERE index scans are rated follow-ups at least two weeks after surgery, before
the first rating of progressive disease. Each patient contributes all eligible scans, and every analysis keeps a
patient's scans together.

The primary outcome is documented first progression within H = 120 days of the index scan (90 and 180 days as
sensitivity analyses). A scan is negative only if progression-free follow-up reaches 120 days; otherwise it is
censored. Death without documented progression censors at the death day. Rules for conflicting dates were fixed in an
audit before the final run; six index scans left the cohort, and at 120 days 17 negatives became censored and one
became positive (Supplementary S3). In LUMIERE, progression is the first expert rating of progressive disease. The
PRISM report used a "naive" label that counted censored scans as negatives; we use it only where we reproduce the PRISM
report. Models are fitted on scans whose 120-day status is known. Discrimination is the inverse-probability-of-
censoring-weighted (IPCW) cumulative/dynamic AUC at 120 days (Uno et al., 2007; Blanche et al., 2013). In a planned
comparison of label formulations, none changed discrimination (all 36 ΔAUC CIs included 0), but the naive label
under-predicted risk (observed/expected, O/E, 1.12–1.19 against 0.95–0.99; Supplementary S3).

### 2.4 Predictors

All predictors are defined as of the scan day (definitions in Supplementary S4).

- **Clinical**: age, sex, IDH (wild type, mutant, unknown), MGMT (methylated, unmethylated, unknown).
- **Timing**: days from diagnosis, days since RT end, an early post-RT flag (0–84 days after RT end, the RANO 12-week
  window) and its interaction with MGMT methylation, visit index, and an unknown-RT-end flag.
- **Treatment, as of the scan**: whether RT and chemotherapy had started, whether RT was completed, prescription, RT
  start day, RT duration, surgery day, biopsy before resection and previous brain tumour. A treatment fact enters only
  once its documented start day is on or before the scan day; RT duration and days since RT end appear only after RT
  has ended. Unknown values are imputed in-fold with missingness indicators. The **baseline** model is clinical +
  timing + treatment (23 predictors, 31 design columns).
- **Phase of care**: pre-RT, during RT, early post-RT (≤ 84 days) or later post-RT, plus log days since RT end.
- **Imaging measurements**: compartment volumes; morphology (ET fraction, multifocality, ET-to-cavity distance,
  intensities relative to normal brain); and past-only change from the previous scan and the nadir.
- **Radiomics**: the PRISM report's legacy T1c + FLAIR features (2,446 columns) and corrected features (whole-brain
  z-score, fixed 32-bin discretisation, per compartment, all four sequences). In every training fold each radiomics and
  deep feature is clipped to that fold's 1st and 99th percentiles, which removes a PyRadiomics sentinel value (10⁶) found
  in three legacy columns of four scans (Supplementary S5).
- **Deep features**: frozen SwinUNETR encoders with BraTS 2021 and BrainSegFounder weights (Cox et al., 2024 [CHECK]),
  and the same architecture with random weights as a control; mask-weighted pooled features per region (Supplementary S6).

### 2.5 The PRISM report model, its split and the as-of-scan correction

The PRISM report model is an L2-penalised logistic regression on 46 legacy radiomics and clinical-code columns with
Platt calibration; its features came from an L1 + permutation consensus ranking and its hyperparameters from an Optuna
search (Supplementary S7). The PRISM report split came from the report's own split search: for a seed, 20,000 random draws of 30
patients, keeping the draw closest to 96 test scans and 53 positives; seed 62 gives the split. We reproduced the
shipped model's stored test predictions to 1.1 × 10⁻¹⁵. In the label-fixed cohort the split has 126 training and 29
test patients with 82 test scans (22 naive positives). On it we fitted, once and without tuning on the split, a
baseline ridge, a baseline gradient-boosting model, the baseline plus legacy radiomics, and a clinical-only ridge.
CIs and paired ΔAUC against the baseline ridge come from a 1,000-draw patient-cluster bootstrap over test patients.

In earlier runs, treatment and timing features read the workbook as of the end of follow-up. A pre-RT scan therefore
carried the dose, start date and "RT given" status of a course that had not started, and a "days since RT end"
computed from a future date (RT status was wrong in 23 all-glioma scans and RT duration or days since RT end in 29;
Supplementary S4). We fixed this with the as-of rule above and report the split before and after the fix (Table 2).

### 2.6 Split variance

We ran the PRISM report's split search for seeds 0–499, giving 500 distinct 30-patient test sets (82–94 scans, 10–33
positives). On each split's training patients we refitted (a) the PRISM report pipeline with its feature ranking redone
(the honest estimate; Optuna not re-run), (b) the shipped 48 features (optimistic, because they were selected on
patients who are test patients in most other splits), (c) the baseline ridge and (d) the baseline plus legacy radiomics.
We report naive-label AUC (500 splits) and IPCW AUC (475 splits; undefined on 25), the percentile rank of the PRISM
report split, and the relation of per-split AUC to test-set composition. This analysis is descriptive; verifier checks
are in Supplementary S8.

### 2.7 Repeated cross-validation and model comparison

All repeated-CV analyses share one set of 5 × 5 repeated patient-grouped folds stratified by 120-day status and grade.
Every fitted step — imputation, clipping, scaling, selection, stacking and hyperparameters — is fitted inside the
training fold (Varma & Simon, 2006; Cawley & Talbot, 2010). The headline estimate is the mean over the five repeats of
the per-repeat pooled out-of-fold IPCW AUC(120 d); an earlier repeat-averaged estimator, which acts as an ensemble, was
replaced before the final run (Supplementary S9). 95% CIs and paired ΔAUC come from a 1,000-draw patient-cluster
bootstrap in which all models are scored on the same resampled patients.

The primary learner is ridge logistic regression with the penalty chosen by inner patient-grouped log-loss;
regularised gradient boosting is secondary. Radiomics enters through 70 configurations (feature variant × stability
filter × selection × concatenation or a stacked radiomics score; Supplementary S5). The honest estimate chooses one
configuration per outer training fold by inner 3-fold patient-grouped CV (nested selection). Deep features use the
same protocol over 32 configurations, with a 16-configuration random-weight control. With 70–80 uncorrected
intervals, about 1.75–2 single configurations are expected to exclude 0 by chance. **The pre-specified primary
development analysis** was grade 4: baseline ridge versus baseline + radiomics by nested selection.

### 2.8 Phase of care (pre-specified)

A ladder of non-imaging bases — R0 clinical; R1 + timing; R2 clinical + phase; R3 baseline — received four imaging
additions: I1 volumes; I2 all non-radiomics imaging measurements; I3 radiomics (nested); I4 deep features (nested).
Cohorts were the full cohort, the post-RT cohort (RT documented and completed; grade 4: 167 scans, 84 patients, 83
events) and the later post-RT cohort (> 84 days after RT end). Models were trained and evaluated within each cohort.
The primary contrast was grade 4, post-RT, ridge, R2 + I2 versus R2, with a 100-permutation test that moves the I2
block between patients with the same number of scans; the key secondary contrast was R2 + I3 versus R2. The plan was
written into the code before the full run but not committed separately (Supplementary S11).

### 2.9 Label, positive controls and re-segmentation

**Imaging-defined label (pre-specified).** Clinical-only first progressions were censored at the progression date.
Rule: the label is "the bottleneck" if, in grade 4 (ridge), imaging alone or baseline + imaging (volumes + change)
beats the baseline by ΔAUC ≥ 0.03 with a 95% CI excluding 0. **Positive controls.** We checked volumes against the
dataset's own volume table, label mapping, label–date alignment and 12 random masks, and measured concurrent detection
of the progression scan against verified 120-day negatives (imaging only). **Re-segmentation (pre-specified).** All
594 complete MU scans were re-segmented with the MONAI BraTS 2021 SwinUNETR (primary) and BrainSegFounder. The new
masks "help" if concurrent detection rises by ≥ 0.05 with a CI excluding 0, or if ET is larger at the progression scan
than at the previous scan in more than 65% of pairs.

### 2.10 External evaluation and diffusion

Models trained on all MU scans were applied unchanged to LUMIERE. Without treatment dates, the transportable features
are clinical + timing (log days since surgery, the < 3-month flag) ± harmonised volumes; the pre-specified external
model was clinical + timing + volumes trained on grade 4. We report pooled IPCW AUC, O/E and calibration slope, and on
5 × 5 LUMIERE folds recalibration, fine-tuning and a cohort-normalised volume sensitivity analysis (Supplementary S13).
The shipped PRISM report model was applied to legacy features re-extracted on LUMIERE.

In CFB-GBM (pre-specified; one row per patient), the outcome was volumetric RANO 2.0 progression from t1 to t2. Nested
feature sets were (a) clinical, (b) + GTV volume and its change from t0, (c) + conventional T1-Gd and FLAIR radiomics,
(d) + ADC radiomics, fitted by ridge with in-fold clipping and selection and evaluated by 20 repeats of 5-fold CV.
Rule: ADC helps if (d) − (c) ≥ 0.03 with a CI excluding 0, with a 1,000-permutation test of the ADC block.
Caveats were fixed in advance: no molecular markers; t1 falls inside the 12-week window; and volume at t1 is part of
the label, so (b) is partly circular.

### 2.11 The auditable decision-support layer

The system wraps the baseline ridge model; it adds no new predictor (plan snapshot saved before the run;
Supplementary S15). It has five parts. (1) A **locked model** with a model card: code version, hashes of every input
table, each input's definition, unit, source column and as-of rule, training counts, cross-validated performance,
intended use and out-of-scope uses. (2) A **per-scan audit record**: each input with its source and as-of day and a
check that it was known by the scan day; phase of care; risk with a 95% interval from 200 patient-cluster bootstrap
refits; exact additive log-odds contributions by group, checked against the logit; a split-conformal prediction set;
and referral flags with reasons — (i) early post-RT window, (ii) out of distribution (IDH or MGMT unknown, or an input
outside the training 1st–99th percentile), (iii) uncertain (conformal set {0, 1} at α = 0.2). (3) **Selective
prediction**: risk–coverage curves compared with random removal and with composition-matched removal (same retained
count per phase). (4) A **shortcut and bias audit**: refits without the "unknown" molecular indicators, timing-only and
treatment-only models, subgroup calibration and a transport audit on LUMIERE. (5) **Explanation stability** and a
reproducibility manifest. Everything was evaluated inside the shared folds with every fitted step, including the
conformal calibration split (70/30 of training patients), fitted on training patients only.

Two quantities were pre-specified. **P1:** conformal coverage at α = 0.2 on verified test scans ≥ 0.78 overall, with
per-phase coverage reported as conditional coverage. **P2:** AUC on scans retained at about 70% coverage minus the AUC
of composition-matched retention, met if its 95% CI lies above 0.

### 2.12 Further analyses and software

The Supplement reports a feature-group search with a permutation control (S10), literature baselines (including a Hashim-style Cox model; Hashim et al., 2026), hyperparameter
grids, class imbalance, schedule coupling, feature conflicts, SHAP, calibration and decision curves (Van Calster et
al., 2019; Pencina et al., 2008) and sample size by the Riley criteria (Riley et al., 2020). Code is Python
(scikit-learn, scikit-survival, PyRadiomics, MONAI, SHAP); every stage is one command with fixed seeds, and logs, folds
and hashes are kept with the outputs (Supplementary S16).

## 3. Results

### 3.1 Cohorts

MU-Glioma-Post contributed 308 index scans from 155 patients (Table 1). Most were grade 4 (126 patients, 81%), IDH
wild type (77%) and treated with RT (66%). At 120 days, 100 scans were followed by documented progression, 156 were not
and 52 were censored (grade 4: 93 / 117 / 39). Of the grade 4 scans, 76 were taken before RT, 6 during RT, 98 in the
early post-RT window and 69 later. Event rates differed by phase: in the full cohort, 8.7% of pre-RT scans were
followed by progression within 120 days. LUMIERE contributed 132 index scans from 61 glioblastoma patients (47 / 76 / 9
at 120 days). IDH status was unknown in 36% of LUMIERE patients and 8% of MU patients.

### 3.2 The PRISM report split

On the PRISM report split, every model scored high (Figure 1A; Table 2). The PRISM report model reached 0.802 on the
naive label and an IPCW AUC of 0.817 (95% CI 0.690–0.920). A ridge model with no imaging — clinical, timing and as-of-scan
treatment — reached 0.871 and 0.851 (0.735–0.947). The paired difference between the two was −0.034 (−0.186 to +0.109).
Adding legacy radiomics to the ridge model changed it by −0.006 (−0.081 to +0.090). A clinical-only ridge model, with
age, sex, IDH and MGMT alone, scored 0.791 and 0.782 (0.638–0.897). All intervals were wide and overlapping.

**How a 0.70 model scored 0.90.** Before the as-of-scan correction, the same clinical + timing + treatment design fitted
by gradient boosting scored 0.901 on the naive label on this split (30 test patients, 84 scans; Table 2, history rows).
Under repeated CV on the same pre-correction inputs, that model averaged 0.723 (0.633–0.806) in grade 4 and 0.743
(0.666–0.816) in all gliomas. Two things lifted it. The first was leakage: pre-RT and on-RT scans carried the RT start
date, dose and end date of a course that had not yet started or ended. After the correction, the boosting model scored
0.869 on the same split, and with the final labels and the 29-patient test set, 0.844 (IPCW 0.824, 0.690–0.916). Its
final repeated-CV AUC is 0.687 (0.601–0.768) in grade 4 and 0.718 (0.642–0.792) in all gliomas. The ridge model moved
less: 0.870 before the correction, 0.880 after it and 0.871 with the final labels. The second lift was the
split itself.

**Why the split is easy.** Of the 60 negative test scans, 36 were taken before RT started, and none of the 36 pre-RT
test scans was followed by progression (Figure 1B). In the whole cohort 9% of such scans were. So 60% of the
positive–negative pairs compared a progression scan with an early post-operative, pre-RT scan. The baseline ridge
ranked these pairs with AUC 0.962 and the remaining pairs with 0.735; the PRISM report model scored 0.823 and 0.771.
Among the 500 design splits, the PRISM report split was at the 89th percentile for the share of
pre-RT scans, the 5th for IDH-mutant scans and the 6th for later post-RT scans. A no-training rule, "the scan is
post-RT", scored 0.740 on this test set (92nd percentile). On the 42 post-RT test scans (19 patients), the PRISM report
model scored 0.770 (0.604–0.907) and the baseline 0.718 (0.481–0.880) (Figure 1C). The clinical-only model was
nominally highest there, at 0.818 (0.664–0.924), with a difference from the baseline of +0.100 (−0.015 to +0.293):
another illustration of single-split noise.

### 3.3 What a single split does: 500 splits of the same design

When the PRISM report pipeline re-selected its features on each split, its AUC averaged 0.720 ± 0.055 (2.5–97.5%
range 0.610–0.819) (Figure 2A). Its re-run on the PRISM report split scored 0.801, above 92% of splits. Only 7% of
splits reached the reported 0.802. Refitting the shipped 48 features gave 0.815 ± 0.044, but this is an upper bound:
those features were chosen on patients who are test patients in most other splits. Per split, the honest version was
0.095 ± 0.040 lower than the optimistic one. Re-running the full hyperparameter search did not rescue the pipeline
(Supplementary S8).

The baseline ridge averaged 0.801 ± 0.052 over the same splits, and the PRISM report split ranked it at the 91st
percentile. Adding legacy radiomics gave 0.799 ± 0.053, a mean difference of −0.002; radiomics helped in 51.6% of
splits. Per-split AUC
tracked the phase mix of the test set (Figure 2B): for the baseline, the Spearman correlation with the AUC of the
"post-RT" rule was +0.57. From composition alone, nine variables predicted 0.851 for the PRISM report split for the
baseline (observed 0.871, mean 0.801; CV R² 0.42) and 0.773 for the PRISM report pipeline (observed 0.801, mean 0.720;
CV R² 0.10). About two thirds of the split's excess over an average split is thus explained by its composition, and
the rest by the particular patients.

These AUCs use the naive label and the PRISM report's case table, so their level is not comparable with repeated CV;
for the same models, single-split IPCW AUCs were 0.10–0.16 above the all-glioma repeated-CV values (Table 2).

### 3.4 Clinical versus imaging features under repeated cross-validation

In grade 4, clinical features alone reached 0.585 (0.496–0.666). Adding timing raised this to 0.644 (0.560–0.721), and
adding as-of-scan treatment to 0.698 (0.615–0.774), the baseline (Figure 3A). In all gliomas the steps were 0.619,
0.693 and 0.720 (0.638–0.792). Boosting did not beat ridge (grade 4 0.687; all gliomas 0.718). Tuning changed the baseline
by at most ±0.025, and imaging-only literature baselines were weaker (for example, a volumetric RANO-style rule 0.551;
Supplementary S12).

**Radiomics (pre-specified primary analysis).** With nested selection over 70 configurations, radiomics changed the
grade 4 baseline by −0.032 (−0.084 to +0.017; AUC 0.666) and the all-glioma baseline by +0.028 (−0.017 to +0.071; AUC
0.747) (Table 3; Figure 3B). No grade 4 configuration had a CI above 0 (8 of 70 were below 0). In all gliomas 1 of 70
did — legacy PCA-10, stacked, +0.035 (+0.002 to +0.068) — fewer than the 1.75 expected by chance. Nested radiomics models were over-confident (calibration slope 0.60 in grade 4
against 0.89 for the baseline).

**Deep features.** Frozen pretrained encoders, nested over 32 configurations, changed the baseline by −0.004 (−0.069 to
+0.063) in grade 4 and +0.011 (−0.032 to +0.056) in all gliomas. The pretrained features did carry image-only signal
(grade 4 image-only AUC 0.652, against 0.566 with random weights), but it correlated with tumour volume (r = 0.58) and
was not additive. The random-weight control was worse than the baseline: −0.049 (−0.085 to −0.014).

**Credit is not value.** In models that included volumes, morphology and change features, these imaging groups took
45% (ridge) and 51% (boosting) of the mean absolute SHAP credit, yet the models did not improve on the baseline (0.692
and 0.694 against 0.698) (Figure 3C). In the baseline itself, treatment took 58% of the credit, clinical 25% and
timing 17%; the leading features were whether RT had started and the RT start day.

### 3.5 Phase of care

A compact four-level phase block recovered most of the baseline's gain over clinical features: grade 4 R0 0.585,
R2 0.664, R3 0.698 (R2 − R0 +0.080, +0.005 to +0.152) (Figure 4A). With phase known, volumes did as well as the full
treatment block (R2 + I1 0.696) but no better. Within the post-RT cohort no model discriminated well. Grade 4 bases
scored 0.549–0.604, and phase itself carried nothing (R2 − R0 −0.003).

**Primary contrast (pre-specified).** In grade 4 post-RT scans, adding all non-radiomics imaging measurements to
clinical + phase changed AUC from 0.549 (0.458–0.642) to 0.610 (0.529–0.688): ΔAUC +0.061 (−0.038 to +0.156), permutation
p = 0.21 (Figure 4B). The permutation null itself averaged +0.028: adding 44 permuted columns to a weak base raises its
AUC. The key secondary contrast, radiomics, gave +0.061 (−0.041 to +0.157) with calibration slope 0.44. **The
hypothesis that imaging adds value within the post-RT phase was not supported.** On top of the full baseline, every
imaging block changed post-RT AUC by +0.005 to +0.04 with all CIs including 0. In an exploratory check, age alone scored
0.586 in grade 4 post-RT scans, above R2, so part of the +0.061 reflects a weak base. In the later post-RT cohort
(69 scans) the bases fell below 0.5 (0.343–0.472), so contrasts there are not interpretable.

### 3.6 Label, positive controls and segmentation

**Imaging-defined label (pre-specified).** Clinical-only progression accounted for 12 of 93 grade 4 events (10
patients). With these censored, baseline + imaging reached 0.722 (0.639–0.799) against 0.696 (0.610–0.776) for the
baseline: ΔAUC +0.027 (−0.033 to +0.082). Imaging alone was 0.068 below the baseline. **The rule was not met**; the
documented-progression label was not shown to be the bottleneck.

**Positive controls.** No pipeline error was found. Our volumes reproduced the dataset's own table (Pearson r 0.996–
0.9998 by compartment), labels were aligned with scan dates and the 12 inspected masks were correct. Yet imaging
detected the progression scan itself against verified negatives with AUC only 0.68 (0.62–0.74). ET volume was larger at
the progression scan than at the previous scan in 49% of 74 pairs (p = 0.54); whole-lesion growth from the nadir was
larger in 79% (p = 0.0003). Volume series were noisy: between scans ≤ 14 days apart the median ET change was 3.2-fold.
The 120-day label largely meant "the next scan is the progression scan" (agreement 79%, κ 0.53; Supplementary S14).

**Re-segmentation (pre-specified).** The BraTS 2021 SwinUNETR agreed with the MU masks (median Dice ET 0.80, whole
tumour 0.85) and removed part of the short-interval noise, but primary detection fell from 0.681 to 0.665 (Δ −0.016,
−0.057 to +0.025), and ET was larger at progression in 45% of pairs. BrainSegFounder gave 0.677 and 41%. **The rule was
not met.** In the forward 120-day task the same clinical + phase + imaging model changed by +0.030 (−0.008 to +0.069)
in grade 4 with the new masks (Table 3).

### 3.7 External and third-cohort evaluation

On LUMIERE the pre-specified locked model (clinical + timing + volumes, trained on MU grade 4) scored 0.608
(0.469–0.739) with ridge and 0.620 (0.495–0.733) with boosting, against 0.667 and 0.675 in MU CV. Clinical + timing
alone scored 0.610 and 0.632; adding volumes did not help (ridge −0.001, −0.073 to +0.057). The ridge model
under-predicted risk (O/E 1.33); boosting was calibrated in the large (O/E 0.99). Recalibration brought O/E to
0.93–0.97 without changing the ranking, and no fine-tuning arm beat the locked model. Rank-normalising volumes within
each cohort raised the boosting model to 0.659 (0.529–0.767), suggesting that part of the loss is segmenter scale.
Frozen deep features added +0.050 to +0.089 (one of four CIs excluded 0), but a random-weight encoder
gained up to +0.045, and deep features identified the cohort with AUC about 0.8. The shipped PRISM report model scored 0.613 (0.500–0.729) on 118 LUMIERE scans. In LUMIERE the time to the
next scan alone scored 0.788 (0.703–0.868), higher than any locked model (Supplementary S13).

**CFB-GBM (pre-specified).** In 77 patients with ADC (19 events), adding ADC features to conventional radiomics
changed AUC by +0.007 (−0.019 to +0.035; permutation p = 0.151; minimal detectable difference 0.038). **The rule was not
met.** Clinical features alone were at chance (0.501 in the 107-patient conventional cohort, 0.565 in the ADC cohort).
GTV volume and its change added +0.185 (+0.064 to +0.293) and +0.148 (+0.031 to +0.266), but this block is partly
circular with a label defined by the same volume. Conventional texture added nothing beyond volume (−0.009 and −0.022).

### 3.8 Calibration and clinical utility

The grade 4 baseline was well calibrated in the large (weighted O/E 0.96; calibration-in-the-large −0.09, −0.42 to
0.28) and mildly over-fitted (slope 0.89, 0.50–1.43). At a 30% threshold its net benefit was 0.232 against 0.189 for
treating all. Radiomics lowered net benefit at 30% by −0.020 (−0.038 to −0.004); deep features changed it by at most
±0.002 at 10–30%. The study is under-powered by the Riley criteria even for the baseline: 3.0 events per parameter for
31 design columns, against 2,190 scans (970 events) required. The radiomics result held in nine sensitivity analyses (ΔAUC −0.032 to
+0.028, no CI excluding 0), and the baseline held within strata of the interval to the next scan (0.687, 0.595–0.768)
and against re-balancing or XGBoost (Supplementary S12).

### 3.9 The auditable layer

The system's cross-validated predictions reproduced the baseline's out-of-fold predictions (maximum difference
1.7 × 10⁻¹⁶), and the additive explanation reproduced every logit (maximum error 1.3 × 10⁻¹⁵). An example record is in Supplementary S15.

**P1 (coverage) was met overall, with conditional failures.** At α = 0.2, conformal coverage on verified test scans was
0.841 (0.790–0.885) in grade 4 and 0.823 (0.776–0.865) in all gliomas. Coverage failed in two places. Almost every pre-RT
scan received the set {0}, so all 5 grade 4 pre-RT progressions (10 in all gliomas) fell outside their sets. During RT,
coverage was 0.567 (6 scans).

**P2 (abstention beyond case mix) was not met.** At about 70% coverage, AUC on the retained scans was 0.731 (0.635–0.812)
against 0.698 for random removal, but composition-matched removal gave 0.725: P2 +0.006 (−0.023 to +0.036) in grade 4 and
+0.003 (−0.031 to +0.036) in all gliomas (Figure 5). Abstention kept 97.6% of pre-RT scans. The early post-RT referral
rule raised AUC to 0.723 only by removing a whole phase; within-phase AUCs were 0.555 (pre-RT), 0.663 (early post-RT)
and 0.597 (later post-RT), all below the pooled 0.698. Any referral flag applied to 72.6% of grade 4 scans.

**The audit found four problems that the headline AUC hides.** (1) A missingness shortcut: IDH was unknown in 0 of 93
progression scans but in 6 of 117 non-progression and 5 of 39 censored scans; removing the unknown-marker indicators
lowered grade 4 AUC by −0.023 (−0.047 to −0.001). (2) The model is a treatment-course model: treatment features alone
scored 0.701 (0.622–0.776), Δ +0.003 (−0.050 to +0.048) against the full baseline. (3) A molecular look-ahead: IDH and
MGMT were used at 8 grade 4 scans taken 1–58 days before the diagnosis date. (4) The LUMIERE miscalibration came mostly
from the same shortcut: IDH was unknown in 40.9% of LUMIERE scans against 4.4% in MU, and the mean contribution of the IDH-unknown
indicator shifted by −0.68 logits; refitting without the unknown indicators moved LUMIERE O/E from 1.33 to 0.89. Under this shift, conformal
coverage on LUMIERE fell to 0.715 (0.340 on events). Explanation signs were stable, but the exact top 5 features recurred in
at most 4% of refits.

## 4. Discussion

We set out to re-evaluate a radiomics model that scored AUC 0.80 on one 30-patient split of a public post-treatment
glioma cohort. Four findings stand out. First, the split was favourable: over 500 splits of the same design the
PRISM report pipeline averaged 0.72, and 7% of splits reached the reported value. Second, under repeated,
patient-grouped and censoring-aware evaluation, a model built from clinical variables and the as-of-scan treatment
course reached about 0.70, and neither radiomics, frozen deep features nor a consistent re-segmentation added
measurable discrimination. Third, the clinical model's signal is largely phase of care: whether and when RT started
and ended. Within the post-RT surveillance phase no model, with or without imaging, discriminated well. Fourth, an
audit layer around the clinical model met its coverage target and made each prediction traceable, but it did not
improve discrimination beyond case mix, and its main value was to expose problems that the AUC hides.

**What single splits do.** The single split did more than add noise. It changed the ranking question. When 60% of the
case–control pairs compare a progression scan with a fresh post-operative scan before RT, any model that recognises a
pre-RT scan scores well. The clinical model does this through treatment status. The radiomics model does it through
T1c texture. A no-training "post-RT" rule scored 0.740 on that test set. This mechanism is not specific to radiomics.
It also lifted a no-imaging model to 0.871, and, while future treatment dates still leaked into the features, a
boosting model to 0.901. That model averaged about 0.70 under repeated CV. This agrees with the instability across random splits shown by An et al. (2021) and
adds a specific mechanism: when cohorts mix phases of care with very different event rates, the composition of a
small test set is a major source of variance, explaining about two thirds of this split's excess. A split search that
targets the number of test scans and positives does not control it. We therefore suggest four reporting rules for
this task: repeated grouped CV; the distribution over splits when a single split is reported; results within phases
of care; and a clinical comparator that knows the treatment course.

**Phase of care as a confounder.** Event rates after a surveillance MRI depend strongly on where the scan sits in the
course of treatment. A scan before RT is rarely followed by documented progression within 120 days. A scan in the
early post-RT window often is, partly because of pseudoprogression and the follow-up imaging it triggers (Brandes et
al., 2008; Taal et al., 2008; Wen et al., 2023). A four-level phase block recovered most of the clinical model's gain
over clinical variables, treatment features alone reproduced the whole baseline (0.701), and SHAP gave treatment
status the largest share of credit. Two published clinical comparators also use time since the end of RT and find it
influential (Gomaa et al., 2025; Leone et al., 2023), though in a pseudoprogression task with an already suspicious
lesion. Imaging models that pool pre-RT and surveillance scans can therefore report high AUCs for phase recognition
rather than for progression biology. Our pre-specified test of imaging within the post-RT phase was negative
(+0.061, −0.038 to +0.156), and part of its point estimate was an artefact of adding columns to a weak base.

**Why imaging did not add.** We found no pipeline defect: volumes matched the dataset's own table, labels were aligned
and masks looked correct. Yet even at the scan where progression was documented, compartment volumes separated it from
verified negatives with AUC only 0.68, and ET volume was no larger than at the previous scan in half of the pairs. Three
features of the data explain this. The label is a documentation event: about one in eight grade 4 events was a
clinical-only progression, and the 120-day label mostly means that the next scan was the progression scan. Volume
series were noisy, with changes over days as large as over months; a consistent segmenter reduced but did not remove
this. And the cohort is small: by the Riley criteria even the 31-column baseline would need about ten times more
scans, and radiomics models far more (Riley et al., 2020). Cleaning the label and re-segmenting moved imaging in the
expected direction by about +0.03, but neither met its pre-specified rule. A real imaging effect of that size cannot be
excluded; our data cannot detect it. Diffusion did not change the picture in CFB-GBM, although that test was small (19
events) and used precomputed features. The task literature where imaging performs well uses diffusion and perfusion
for pseudoprogression classification (Kim et al., 2019; Taylor et al., 2022), a different question from forward risk
at every surveillance scan.

**Credit is not value.** Imaging took about half of the SHAP credit in models that included it, without any gain in
discrimination. Attribution shares among correlated features describe how a model divides its output, not whether a
feature group is needed; claims of imaging value need a paired difference with an interval.

**External validity.** Locked models lost about 0.05–0.06 AUC on LUMIERE, in line with the drops reported for externally
validated imaging models (Yu et al., 2022). The shipped PRISM report model fell from 0.80 to 0.61. LUMIERE lacks
treatment dates, so the treatment-aware model could not be transported, and the shared model's under-prediction came
mostly from a missingness indicator: IDH status is often unknown in LUMIERE, and in MU unknown IDH occurred only in
scans without progression. The time to the next scan alone predicted the LUMIERE label better than any model, so
external AUCs on this kind of label are partly schedule-dependent. In MU, by contrast, the baseline kept its ranking
within strata of the scan interval.

**What an auditable model offers at AUC about 0.70.** We did not find a triage benefit. Abstaining on uncertain scans
and referring early post-RT scans raised the AUC of the remaining scans only by changing their phase mix, and the flags
together covered most scans. The conformal sets met their marginal target, but they did so mainly by assigning
"no progression" to pre-RT scans, missing every pre-RT progression, and coverage broke under the shift to LUMIERE. What
the layer did provide is auditability. Each record shows what the model knew at the scan date, where the scan sits in
the treatment course, an interval, and an exact explanation. Running the audit found a missingness shortcut, a
look-ahead in the use of molecular results before diagnosis, and the cause of the external miscalibration, none of
which the cross-validated AUC revealed. We think this is the honest use of such a layer at this level of performance:
to make a modest model's reasoning and failure modes visible, not to claim better decisions.

**Comparison with other work.** Our grade 4 baseline (0.698) is close to the clinical comparators reported for adjacent
tasks (0.69 in Leone et al., 2023; 0.727 externally in Gomaa et al., 2025) and to the nested-CV result for a
volume-defined label on the same dataset (0.728; Rai, 2026 [CHECK]). It is below the single-test-set 0.80 reported on
MU-Glioma-Post (Christodoulou et al., 2026), whose label (progression status of each scan) differs from our forward
120-day label; we did not re-evaluate that model. Higher AUCs for forward recurrence prediction elsewhere (for example Chen et al.,
2026; Tak et al., 2025) use different cohorts, horizons and units, and some fall externally (0.887 to 0.762 in Chen et
al., 2026).

### Limitations

The development cohort is a single centre with 126 grade 4 patients and 93 events at 120 days, far below recommended
sample sizes; small imaging effects cannot be excluded. The outcome is documented progression from routine records,
not a blinded per-scan RANO read, and its timing depends on scheduling. MU images lack acquisition metadata, so scanner
and field-strength effects could not be audited, and race could not be studied. The external cohort is small (61
patients), uses a different segmenter and an expert RANO label, and lacks treatment dates, so the main model was not
externally tested. Several analyses were added after earlier results were known (for example the clean-label and
re-segmentation tests followed the imaging null), although each had its rule fixed before its own run; the phase-ladder
plan was written into the code but not separately committed. Radiomics discretisation used a fixed bin count rather
than the IBSI-recommended fixed bin width (Zwanenburg et al., 2020), and the ICC stability filter covered only T1c and
FLAIR. Deep features were frozen; fine-tuning and diffusion-based deep features were not run. Feature pipelines in two
secondary analyses (the feature-group search and one label-formulation set) still contain unclipped legacy radiomics.
The shipped PRISM report model's LUMIERE score predates the final external label definition. The audit found a small
molecular look-ahead (8 grade 4 scans) that also affects the reported baseline; its size was not quantified. There was
no reader study, so we cannot say whether the audit records change clinical decisions.

### Conclusion

On MU-Glioma-Post, a radiomics model's AUC of 0.80 reflected one favourable split; across splits its pipeline averaged
0.72, and a clinical model that knows the treatment course reached about 0.70 under repeated cross-validation. MRI
radiomics, frozen deep features, re-segmentation, a cleaner label and diffusion features added no measurable
discrimination. Phase of care drives discrimination on this task and should be reported as a stratum and controlled
as a confounder. An audit layer can make a modest model's knowledge and failure modes explicit, but on these data it
did not make triage better than case mix.

---

## Declarations

**Ethics.** [PENDING AUTHOR DECISION: secondary analysis of public de-identified datasets (MU-Glioma-Post, LUMIERE,
CFB-GBM); state the institutional determination or waiver and cite the source datasets' approvals.]
**Funding.** [PENDING AUTHOR DECISION]. **Competing interests.** [PENDING AUTHOR DECISION].
**Data availability.** [PENDING AUTHOR DECISION: MU-Glioma-Post (TCIA, doi:10.7937/7K9K-3C83), LUMIERE (figshare;
Suter et al., 2022) and CFB-GBM (TCIA, doi:10.7937/v9pn-2f72) are public; derived tables, fold assignments and locked
model files — state what is released.] **Code availability.** [PENDING: public repository link and release tag.]
**Protocol and registration.** No registered protocol. Analysis plans and dated plan snapshots are in the repository
(Supplementary S1). **Patient and public involvement.** None.
**Use of the name "PRISM".** The PRISM report is an unpublished internal report; "PRISM report model" and "PRISM report
split" refer to the model and split described there.

---

## Tables

### Table 1. Cohort characteristics

Index scans are post-treatment MRIs before first documented progression. Values are n (%) or median [IQR]. Patient rows
use each patient's first index scan. Full table with definitions: Supplementary Table S2.

| | MU all gliomas | MU grade 4 | LUMIERE |
|---|---|---|---|
| Patients / index scans | 155 / 308 | 126 / 249 | 61 / 132 |
| Index scans per patient, median (range) | 2 (1–6) | 2 (1–6) | 2 (1–10) |
| Age, years | 61 [47–69] | 62 [53–70] | 62 [53–70] |
| Male sex | 80 (52%) | 66 (52%) | 32 (52%) |
| IDH wild type / mutant / unknown | 120 (77%) / 22 (14%) / 13 (8%) | 112 (89%) / 8 (6%) / 6 (5%) | 38 (62%) / 1 (2%) / 22 (36%) |
| MGMT methylated / unmethylated / unknown | 53 (34%) / 73 (47%) / 29 (19%) | 45 (36%) / 62 (49%) / 19 (15%) | 26 (43%) / 28 (46%) / 7 (11%) |
| WHO grade 4 | 126 (81%) | 126 (100%) | 61 (100%) |
| Radiotherapy documented | 102 (66%) | 89 (71%) | not recorded |
| Initial chemotherapy documented | 96 (62%) | 88 (70%) | not recorded |
| Days from origin to scanᵃ | 97 [46–186] | 96 [54–182] | 119 [82–226] |
| RT completed by scan day (scans) | 185 (60%) | 167 (67%) | not recorded |
| Early post-RT windowᵇ (scans) | 104 (34%); unknown 94 | 98 (39%); unknown 65 | 27 (20%) |
| Gap to next MRI, days | 77 [50–103] | 74 [49–98] | 91 [77–117] |
| Death without documented progression (scans) | 22 (7%) | 20 (8%) | 7 (5%) |
| 120 d: progression / no progression / censored | 100 / 156 / 52 | 93 / 117 / 39 | 47 / 76 / 9 |
| 90 d | 65 / 195 / 48 | 62 / 152 / 35 | 24 / 101 / 7 |
| 180 d | 144 / 105 / 59 | 131 / 75 / 43 | 62 / 61 / 9 |

ᵃ MU: days since diagnosis; LUMIERE: days since first surgery. ᵇ MU: 0–84 days after the documented RT end date;
LUMIERE: rater's "< 3 months after RT" flag. Source: `docs/manuscript/TABLE1_COHORT.md`.

### Table 2. The same models on a single split, across 500 splits and under repeated cross-validation

IPCW AUC(120 d) with 95% patient-cluster bootstrap CI unless stated. Single split = PRISM report split (all gliomas;
29 test patients, 82 scans). 500 splits = the PRISM report split design (naive label; for the PRISM report model, its
pipeline with features re-selected per split). 5 × 5 CV = repeated patient-grouped CV on the label-fixed cohort.
History rows document the as-of-scan treatment correction on the earlier 30-patient / 84-scan version of the split;
"pre-fix (leaky)" means that future RT dates and RT status entered the treatment and timing features. Full table and
sources: `docs/manuscript/figures/table2_single_split_vs_cv.{md,csv}`.

| Model | Single split: naive AUC | Single split: IPCW AUC [95% CI] | Δ vs baseline ridge [95% CI] | 500 splits: naive mean ± SD (2.5–97.5%) | 5 × 5 CV, all gliomas | 5 × 5 CV, grade 4 |
|---|---|---|---|---|---|---|
| PRISM report model | 0.802 | 0.817 [0.690, 0.920] | −0.034 [−0.186, +0.109] | 0.720 ± 0.055 (0.610–0.819) | n/a (fixed model) | n/a (fixed model) |
| Baseline ridge | 0.871 | 0.851 [0.735, 0.947] | – | 0.801 ± 0.052 (0.694–0.895) | 0.720 [0.638, 0.792] | 0.698 [0.615, 0.774] |
| Baseline GBM | 0.844 | 0.824 [0.690, 0.916] | −0.027 [−0.127, +0.062] | not run | 0.718 [0.642, 0.792] | 0.687 [0.601, 0.768] |
| Baseline + legacy radiomics | 0.862 | 0.845 [0.746, 0.936] | −0.006 [−0.081, +0.090] | 0.799 ± 0.053 (0.674–0.892) | 0.743 [0.678, 0.803] | 0.703 [0.627, 0.774] |
| Clinical only (ridge) | 0.791 | 0.782 [0.638, 0.897] | −0.069 [−0.215, +0.058] | not run | 0.619 [0.540, 0.696] | 0.585 [0.496, 0.666] |
| *History rows (30 patients / 84 scans; earlier cohort and inputs)* | | | | | | |
| PRISM report model | 0.802 | 0.811 [0.694, 0.919] | not computed | – | – | – |
| Baseline ridge, pre-fix (leaky) | 0.870 | 0.844 (no CI) | not computed | not run | 0.719 [0.648, 0.788]ᶜ | 0.694 [0.613, 0.775]ᶜ |
| Baseline ridge, after as-of-scan fix | 0.880 | 0.860 [0.730, 0.943] | not computed | not run | 0.749 [0.675, 0.820]ᵈ | 0.729 [0.648, 0.811]ᵈ |
| Baseline GBM, pre-fix (leaky) | 0.901 | 0.881 (no CI) | not computed | not run | 0.743 [0.666, 0.816]ᶜ | 0.723 [0.633, 0.806]ᶜ |
| Baseline GBM, after as-of-scan fix | 0.869 | 0.855 (no CI) | not computed | not run | 0.740 [0.663, 0.815]ᵈ | 0.731 [0.641, 0.813]ᵈ |

ᶜ Pre-fix inputs, pre-label-fix cohort, earlier repeat-averaged estimator. ᵈ Intermediate inputs after the as-of-scan
fix, before the label fixes; repeat-averaged estimator. History-row CV values are not comparable with the final rows.

### Table 3. Does imaging add to non-imaging information? Paired ΔAUC with 95% patient-cluster bootstrap CI

Reference: the baseline (clinical + timing + treatment, ridge) unless stated in the section heading. Grade 4 (G4) is
primary. * = CI excludes 0 (uncorrected; 3 of the 32 intervals in Figure 3B; the CFB-GBM row is added here). Source: `docs/manuscript/figures/table3_forest.csv`.

| Analysis | G4 ΔAUC [95% CI] | All gliomas ΔAUC [95% CI] |
|---|---|---|
| **Radiomics vs baseline** | | |
| Nested over 70 configurations (pre-specified primary) | −0.032 [−0.084, +0.017] | +0.028 [−0.017, +0.071] |
| Legacy top-10, concatenated (single configuration) | +0.005 [−0.059, +0.067] | +0.024 [−0.026, +0.075] |
| Legacy PCA-10, stacked (best post hoc, optimistic) | +0.023 [−0.013, +0.057] | +0.035 [+0.002, +0.068]* |
| **Frozen deep features vs baseline** | | |
| Nested over 32 (BraTS21 SwinUNETR + BrainSegFounder) | −0.004 [−0.069, +0.063] | +0.011 [−0.032, +0.056] |
| BraTS21 SwinUNETR, lesion PCA-10 stacked | +0.016 [−0.029, +0.059] | +0.017 [−0.014, +0.050] |
| BrainSegFounder, lesion PCA-10 stacked | +0.014 [−0.029, +0.057] | +0.024 [−0.013, +0.064] |
| Random-weight encoder, nested (control) | −0.049 [−0.085, −0.014]* | −0.009 [−0.032, +0.009] |
| **Imaging-defined label (clinical-only progression censored)** | | |
| Baseline + volumes/change vs baseline (pre-specified rule) | +0.027 [−0.033, +0.082] | +0.008 [−0.036, +0.049] |
| **Post-RT scans only** | | |
| Clinical + phase + imaging vs clinical + phase (pre-specified primary) | +0.061 [−0.038, +0.156] | +0.033 [−0.054, +0.128] |
| Baseline + imaging measurements vs baseline | +0.017 [−0.069, +0.093] | +0.005 [−0.075, +0.082] |
| Baseline + radiomics (nested) vs baseline | +0.005 [−0.070, +0.075] | +0.024 [−0.030, +0.076] |
| **Re-segmentation (reference: same model on MU masks)** | | |
| Clinical + phase + imaging, BraTS21 SwinUNETR masks | +0.030 [−0.008, +0.069] | +0.029 [−0.010, +0.069] |
| Clinical + phase + imaging, BrainSegFounder masks | +0.008 [−0.023, +0.040] | +0.003 [−0.025, +0.032] |
| **LUMIERE, locked (reference: clinical + timing)** | | |
| + volumes | −0.001 [−0.073, +0.057] | −0.006 [−0.075, +0.055] |
| + deep features | +0.057 [−0.132, +0.235] | +0.064 [−0.011, +0.144] |
| + volumes + deep vs + volumes | +0.089 [−0.026, +0.215] | +0.050 [+0.002, +0.109]* |
| **CFB-GBM (77 patients, 19 events; reference: conventional radiomics)** | | |
| + ADC radiomics (pre-specified primary) | +0.007 [−0.019, +0.035] (permutation p = 0.151) | – |

---

## Figure legends

**Figure 1. The PRISM report split.** Discrimination on the PRISM report split (all gliomas; 126 training / 29 test
patients, 82 test scans, 22 naive positives). Every model except the PRISM report model was fitted once on the training
patients; the PRISM report model enters with its shipped test-set probabilities. (A) IPCW AUC with 95% patient-cluster
bootstrap CI (1,000 draws; dot and bar) and naive AUC (tick). (B) Naive AUC decomposed by the type of negative scan:
36 of the 60 negative test scans were taken before RT started, and none of them progressed, so 60% of positive–negative
pairs compare a progression scan with a pre-RT scan; solid bars, positives against pre-RT negatives; light bars,
positives against other negatives. (C) The same models on the 42 post-RT test scans (19 patients). Intervals are wide
and overlap throughout. File: `figures/fig1_single_split.{png,pdf}`.

**Figure 2. Where the PRISM report split sits among 500 splits of the same design.** The PRISM report's split search
was run for seeds 0–499; seed 62 reproduces the PRISM report split. (A) Test AUC (naive label) per split for the PRISM
report pipeline with features re-selected per split (honest estimate), the shipped features refitted (optimistic upper
bound), the baseline ridge and the baseline + legacy radiomics. Violin and points, 500 splits; grey dot and line, mean
and 2.5–97.5% range; diamond, each model's own value on the PRISM report split with its percentile rank; dashed line,
the reported 0.802. (B) Per-split AUC against the AUC of the no-training rule "scan is post-RT" on that test set
(higher = more pre-RT negatives and fewer pre-RT events); lines, least-squares fits; Spearman ρ +0.57 (baseline) and
+0.22 (PRISM report pipeline). File: `figures/fig2_split_variance.{png,pdf}`.

**Figure 3. Clinical versus imaging features under repeated cross-validation.** (A) Feature ladder (ridge; 5 × 5
repeated patient-grouped CV; IPCW AUC(120 d) with 95% patient-cluster bootstrap CI): clinical → + timing → + as-of-scan
treatment (= baseline, B); the last three points each add one imaging block to B (volumes; radiomics, nested over 70
configurations; frozen deep features, nested over 32). (B) Paired ΔAUC with 95% CI against the reference named in each
section (Table 3). Asterisks mark CIs excluding 0 (3 of 32, uncorrected; about 1.6 expected by chance). (C) Share of
mean absolute group SHAP in grade 4 out-of-fold explanations: imaging blocks take 45–51% of the credit in the full
models without improving discrimination. File: `figures/fig3_clinical_vs_radiomics.{png,pdf}`.

**Figure 4. Phase of care.** (A) Non-imaging bases (ridge, grade 4) in the full cohort (249 scans), the post-RT cohort
(167 scans, 84 patients, 83 events) and the later post-RT cohort (> 12 weeks after RT end; 69 scans), each trained and
evaluated within the cohort. R0 clinical; R1 + timing; R2 + four-level phase of care; R3 baseline. In the later post-RT
cohort the bases fall below 0.5, the expected anti-learning of a near-null model in a small sample, so contrasts there
are not interpretable. (B) ΔAUC from adding each imaging block (I1 volumes; I2 all non-radiomics measurements; I3
radiomics; I4 deep) to each base within grade 4 post-RT scans. Diamond, pre-specified primary contrast (R2 + I2 vs R2):
+0.061 (−0.038 to +0.156), permutation p = 0.21; the permutation null itself averages +0.03. File:
`figures/fig4_phase_of_care.{png,pdf}`.

**Figure 5. The auditable layer: selective prediction against case mix.** Risk–coverage curves for the baseline model
(5 × 5 CV, pooled out-of-fold predictions, mean over repeats), grade 4 (left) and all gliomas (right). Top, IPCW
AUC(120 d); bottom, IPCW Brier score, of the scans retained when the least confident scans (lowest max(p, 1 − p)) are
withheld first (solid), against random removal (dashed) and phase-composition-matched random removal (dotted; shaded
band, 2.5–97.5% of the composition-matched draws). The gain over random removal is almost entirely matched by the
composition-matched reference (pre-specified P2 at about 70% coverage: +0.006, −0.023 to +0.036, grade 4). File:
`figures/fig5_system_risk_coverage.png` (copy of `outputs/results/analyses/audit_system/risk_coverage.png`).
[PENDING: a panel A with the system architecture and an example audit record (Supplementary S15) is to be drawn.]

---

## References

APA 7. Entries taken from `docs/literature/COMPARABLE_RESULTS.md` (verified this pass) or from
`docs/literature/RELATED_WORK.md` (citation details checked against the source page). Long author lists are shortened
with "et al." as in those files; complete them with a reference manager. [CHECK] = not in the verified literature files
or flagged there as unverified. References cited only in the Supplement are included.

- Abler, D., Pusterla, O., Joye-Kühnis, A., et al. (2025). *The added value for MRI radiomics and deep-learning for glioblastoma prognostication compared to clinical and molecular information* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2507.15548
- An, C., Park, Y. W., Ahn, S. S., Han, K., Kim, H., & Lee, S.-K. (2021). Radiomics machine learning study with a small sample size: Single random training-test set split may lead to unreliable results. *PLOS ONE, 16*(8), e0256152. https://doi.org/10.1371/journal.pone.0256152
- Blanche, P., Dartigues, J.-F., & Jacqmin-Gadda, H. (2013). Estimating and comparing time-dependent areas under receiver operating characteristic curves for censored event times with competing risks. *Statistics in Medicine, 32*(30), 5381–5397. https://doi.org/10.1002/sim.5958
- Booth, T. C., Grzeda, M., Chelliah, A., et al. (2022). Imaging biomarkers of glioblastoma treatment response: A systematic review and meta-analysis of recent machine learning studies. *Frontiers in Oncology, 12*, 799662. https://doi.org/10.3389/fonc.2022.799662
- Brandes, A. A., Franceschi, E., Tosoni, A., et al. (2008). MGMT promoter methylation status can predict the incidence and outcome of pseudoprogression after concomitant radiochemotherapy in newly diagnosed glioblastoma patients. *Journal of Clinical Oncology, 26*(13), 2192–2197. https://doi.org/10.1200/JCO.2007.14.8163
- Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent selection bias in performance evaluation. *Journal of Machine Learning Research, 11*(70), 2079–2107. https://jmlr.org/papers/v11/cawley10a.html
- Chen, C., Guo, F., Huang, D., et al. (2026). Predicting recurrence risk of glioblastoma based on preoperative-postoperative longitudinal MRI: A multicenter study. *Bioengineering, 13*(6), 668. https://doi.org/10.3390/bioengineering13060668
- Christodoulou, R. C., Vamvouras, G., Pitsillos, R., Solomou, E. E., & Georgiou, M. F. (2026). Explainable radiomics with probability calibration for postoperative glioblastoma surveillance. *European Journal of Radiology Artificial Intelligence, 5*, 100074. https://doi.org/10.1016/j.ejrai.2026.100074
- Collins, G. S., Moons, K. G. M., Dhiman, P., et al. (2024). TRIPOD+AI statement: Updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ, 385*, e078378. https://doi.org/10.1136/bmj-2023-078378
- Cox, J., et al. (2024). BrainSegFounder [full title to be completed]. *Medical Image Analysis*. https://doi.org/10.1016/j.media.2024.103301 [CHECK: cited from DEEP_FEATURES.md only]
- Demircioğlu, A. (2021). Measuring the bias of incorrect application of feature selection when using cross-validation in radiomics. *Insights into Imaging, 12*(1), 172. https://doi.org/10.1186/s13244-021-01115-1
- Gomaa, A., Huang, Y., Stephan, P., et al. (2025). A self-supervised multimodal deep learning approach to differentiate post-radiotherapy progression from pseudoprogression in glioblastoma. *Scientific Reports, 15*, 17133. https://doi.org/10.1038/s41598-025-02026-7
- Hashim, U., Jalal, A., Jabali, A. N., & Rana, H. (2026). Radiomics outperforms conventional tumor volume in prognostic stratification across independent glioma cohorts. *Cureus, 18*(7), e112298. https://doi.org/10.7759/cureus.112298
- Jang, B.-S., Jeon, S. H., Kim, I. H., & Kim, I. A. (2018). Prediction of pseudoprogression versus progression using machine learning algorithm in glioblastoma. *Scientific Reports, 8*, 12516. https://doi.org/10.1038/s41598-018-31007-2
- Kapoor, S., & Narayanan, A. (2023). Leakage and the reproducibility crisis in machine-learning-based science. *Patterns, 4*(9), 100804. https://doi.org/10.1016/j.patter.2023.100804
- Kim, J. Y., Park, J. E., Jo, Y., et al. (2019). Incorporating diffusion- and perfusion-weighted MRI into a radiomics model improves diagnostic performance for pseudoprogression in glioblastoma patients. *Neuro-Oncology, 21*(3), 404–414. https://doi.org/10.1093/neuonc/noy133
- Kocak, B., Baessler, B., Bakas, S., et al. (2023). CheckList for EvaluAtion of Radiomics research (CLEAR): A step-by-step reporting guideline for authors and reviewers endorsed by ESR and EuSoMII. *Insights into Imaging, 14*, 75. https://doi.org/10.1186/s13244-023-01415-8 [CHECK: cited from CHECKLIST_CLEAR.md, not in the literature files]
- Leone, R., Meredig, H., Foltyn-Dumitru, M., et al. (2023). Assessing the added value of apparent diffusion coefficient, cerebral blood volume, and radiomic magnetic resonance features for differentiation of pseudoprogression versus true tumor progression in patients with glioblastoma. *Neuro-Oncology Advances, 5*(1), vdad016. https://doi.org/10.1093/noajnl/vdad016
- Mahmoud, E., Gass, J., Dhemesh, Y., et al. (2025). MU-Glioma Post: A comprehensive dataset of automated MR multi-sequence segmentation and clinical features. *Scientific Data, 12*(1), 1847. https://doi.org/10.1038/s41597-025-06011-7
- Park, J. E., Kim, H. S., Kim, D., et al. (2020). A systematic review reporting quality of radiomics research in neuro-oncology: Toward clinical utility and quality improvement using high-dimensional imaging features. *BMC Cancer, 20*(1), 29. https://doi.org/10.1186/s12885-019-6504-5
- Pencina, M. J., D'Agostino, R. B., Sr., D'Agostino, R. B., Jr., & Vasan, R. S. (2008). Evaluating the added predictive ability of a new marker: From area under the ROC curve to reclassification and beyond. *Statistics in Medicine, 27*(2), 157–172. https://doi.org/10.1002/sim.2929
- Rai, A. K. (2026). Uncertainty gated residual learning with patient level bagging for longitudinal glioma progression prediction. *Journal of Intelligent Decision Making and Information Science, 3*. https://doi.org/10.59543/jidmis.v3.2236 [CHECK: "repo, unverified (this pass)" in COMPARABLE_RESULTS.md]
- Riley, R. D., Ensor, J., Snell, K. I. E., et al. (2020). Calculating the sample size required for developing a clinical prediction model. *BMJ, 368*, m441. https://doi.org/10.1136/bmj.m441
- Suter, Y., Knecht, U., Valenzuela, W., et al. (2022). The LUMIERE dataset: Longitudinal glioblastoma MRI with expert RANO evaluation. *Scientific Data, 9*(1), 768. https://doi.org/10.1038/s41597-022-01881-7
- Taal, W., Brandsma, D., de Bruin, H. G., et al. (2008). Incidence of early pseudo-progression in a cohort of malignant glioma patients treated with chemoirradiation with temozolomide. *Cancer, 113*(2), 405–410. https://doi.org/10.1002/cncr.23562
- Tak, D., Garomsa, B. A., Zapaishchykova, A., et al. (2025). Longitudinal risk prediction for pediatric glioma with temporal deep learning. *NEJM AI, 2*(5). https://doi.org/10.1056/AIoa2400703
- Taylor, C., Ekert, J. O., Sefcikova, V., Fersht, N., & Samandouras, G. (2022). Discriminators of pseudoprogression and true progression in high-grade gliomas: A systematic review and meta-analysis. *Scientific Reports, 12*, 13258. https://doi.org/10.1038/s41598-022-16726-x
- Uno, H., Cai, T., Tian, L., & Wei, L. J. (2007). Evaluating prediction rules for t-year survivors with censored regression models. *Journal of the American Statistical Association, 102*(478), 527–537. https://doi.org/10.1198/016214507000000149
- Van Calster, B., McLernon, D. J., van Smeden, M., Wynants, L., & Steyerberg, E. W. (2019). Calibration: The Achilles heel of predictive analytics. *BMC Medicine, 17*, 230. https://doi.org/10.1186/s12916-019-1466-7
- van Griethuysen, J. J. M., Fedorov, A., Parmar, C., et al. (2017). Computational radiomics system to decode the radiographic phenotype. *Cancer Research, 77*(21), e104–e107. https://doi.org/10.1158/0008-5472.CAN-17-0339
- Varma, S., & Simon, R. (2006). Bias in error estimation when using cross-validation for model selection. *BMC Bioinformatics, 7*, 91. https://doi.org/10.1186/1471-2105-7-91
- Varoquaux, G. (2018). Cross-validation failure: Small sample sizes lead to large error bars. *NeuroImage, 180*, 68–77. https://doi.org/10.1016/j.neuroimage.2017.06.061
- Welch, M. L., McIntosh, C., Haibe-Kains, B., et al. (2019). Vulnerabilities of radiomic signature development: The need for safeguards. *Radiotherapy and Oncology, 130*, 2–9. https://doi.org/10.1016/j.radonc.2018.10.027
- Wen, P. Y., Macdonald, D. R., Reardon, D. A., et al. (2010). Updated response assessment criteria for high-grade gliomas: Response Assessment in Neuro-Oncology Working Group. *Journal of Clinical Oncology, 28*(11), 1963–1972. https://doi.org/10.1200/JCO.2009.26.3541
- Wen, P. Y., van den Bent, M., Youssef, G., et al. (2023). RANO 2.0: Update to the Response Assessment in Neuro-Oncology criteria for high- and low-grade gliomas in adults. *Journal of Clinical Oncology, 41*(33), 5187–5199. https://doi.org/10.1200/JCO.23.01059
- Yu, A. C., Mohajer, B., & Eng, J. (2022). External validation of deep learning algorithms for radiologic diagnosis: A systematic review. *Radiology: Artificial Intelligence, 4*(3), e210064. https://doi.org/10.1148/ryai.210064
- Yun, Y. C., Jende, J. M. E., Garhöfer, F., et al. (2025). Combined peritumoral radiomics and clinical features predict 12-month progression free survival in glioblastoma. *Journal of Neuro-Oncology, 174*, 111–120. https://doi.org/10.1007/s11060-025-05037-6
- Zwanenburg, A., Vallières, M., Abdalah, M. A., et al. (2020). The Image Biomarker Standardization Initiative: Standardized quantitative radiomics for high-throughput image-based phenotyping. *Radiology, 295*(2), 328–338. https://doi.org/10.1148/radiol.2020191145
- Dataset: CFB-GBM, The Cancer Imaging Archive. https://doi.org/10.7937/v9pn-2f72 [CHECK: formal data citation from TCIA page; cited from DATASETS.md]

---

## Appendix: Source map (not for submission)

Every number in this draft, by section, with its source file. `R/` = `docs/results/`, `M/` = `docs/manuscript/`,
`F/` = `docs/manuscript/figures/`, `O/` = `outputs/results/`. Where a doc quotes an output file, the doc is listed and
the output file is given in the doc's own source table. "Derived" = arithmetic on sourced numbers, stated as such.

| Claim (section) | Value(s) | Source |
|---|---|---|
| PRISM report model single-split AUC (Abstract, Intro, 3.2, Table 2, Fig 1) | 0.802 naive; 0.817 [0.690, 0.920]; Δ −0.034 [−0.186, +0.109] | `O/analyses/paper_figures/single_split.csv` (= `F/table2…`, `M/FIGURES.md` Fig 1); `O/c3/prism_report_split/head_to_head.csv` |
| Baseline ridge / GBM / + legacy radiomics / clinical-only on the split | 0.871 / 0.851 [0.735, 0.947]; 0.844 / 0.824 [0.690, 0.916], Δ −0.027 [−0.127, +0.062]; 0.862 / 0.845 [0.746, 0.936], Δ −0.006 [−0.081, +0.090]; 0.791 / 0.782 [0.638, 0.897], Δ −0.069 [−0.215, +0.058] | same; clipped radiomics row per `M/FIGURES.md` §1 |
| Split size | 126 train / 29 test patients, 82 scans, 22 naive positives; originally 30 / 84 | `M/FIGURES.md` Fig 1; `R/SHAP_PRISM_SPLIT.md` |
| Pre-fix / after-fix split AUCs (3.2, Table 2 history) | GBM 0.901 / 0.881 → 0.869 / 0.855; ridge 0.870 / 0.844 → 0.880 / 0.860; PRISM 0.802 / 0.811 | `O/c3/prism_report_split/head_to_head_before.csv`, `head_to_head_after.csv`; `R/FIX_TREATMENT_ASOF.md` §3 |
| After-fix CIs | ridge 0.860 [0.730, 0.943]; PRISM 0.811 [0.694, 0.919] | `R/FIX_EVALUATION.md` §5 |
| Pre-fix repeated-CV baseline | GBM 0.723 [0.633, 0.806] G4, 0.743 [0.666, 0.816] all; ridge 0.694 [0.613, 0.775], 0.719 [0.648, 0.788] | `outputs/results_pre_fix_2026-10-11/c3/{grade4,all_glioma}/results.csv` |
| After-fix intermediate CV | ridge 0.729 [0.648, 0.811] / 0.749 [0.675, 0.820]; GBM 0.731 [0.641, 0.813] / 0.740 [0.663, 0.815] | `R/FIX_TREATMENT_ASOF.md` §3 |
| Leak counts | RT status 23 all-glioma scans; RT duration / days since RT end 29 | `R/FIX_TREATMENT_ASOF.md` §1 |
| Pair decomposition, composition percentiles | 36 of 60 negatives pre-RT, 0 progressed, 60% of pairs; 0.962 / 0.735; 0.823 / 0.771; 89th, 5th, 6th, 92nd percentiles; rule 0.740; 9% / 8.7% pre-RT event rate | `R/SHAP_PRISM_SPLIT.md` §3; `F/single_split_pairs.csv` |
| Post-RT subset of the split | 42 scans / 19 patients; PRISM 0.770 [0.604, 0.907]; ridge 0.718 [0.481, 0.880]; clinical 0.818 [0.664, 0.924], Δ +0.100 [−0.015, +0.293] | `O/analyses/paper_figures/single_split.csv` (subset=post_rt); `M/FIGURES.md` Fig 1 note |
| 500 splits (3.3, Table 2, Fig 2) | 0.720 ± 0.055 (0.610–0.819); 0.801, 92nd pct; 7%; 0.815 ± 0.044; baseline 0.801 ± 0.052 (0.694–0.895), 91st pct; + radiomics 0.799 ± 0.053 (0.674–0.892), 51.6%, mean Δ −0.002; 475 IPCW splits; 82–94 scans, 10–33 positives | `O/analyses/split_variance/summary_clipped.csv` via `M/FIGURES.md` Fig 2; `R/SPLIT_VARIANCE.md` (design, non-radiomics rows) |
| Honest vs optimistic gap; loses to baseline | 0.095 ± 0.040; 88%, mean −0.081 | `R/SPLIT_VARIANCE.md` |
| Optuna verifier check | −0.064 ± 0.055; 0.865 vs 0.654; ≈ 0.21; 15 splits | `R/SPLIT_VARIANCE.md` sensitivity check 1 |
| Composition regression | ρ +0.57 / +0.22; predicted 0.851 / 0.773; CV R² 0.42 / 0.10; nine variables; two thirds | `R/SHAP_PRISM_SPLIT.md` §3; `M/FIGURES.md` Fig 2 |
| Single split 0.10–0.16 above CV | — | `M/FIGURES.md` Table 2 caption |
| Cohort and Table 1 | 596 / 203 → 308 / 155; 249 / 126; 100 / 156 / 52; 93 / 117 / 39; LUMIERE 132 / 61, 47 / 76 / 9; phase counts 76 / 6 / 98 / 69; all Table 1 cells | `M/FLOW.md`, `M/TABLE1_COHORT.md`; `R/PHASE_LADDER.md` §1–2 |
| Label fixes | six scans left; 17 negatives → censored; 1 negative → positive | `R/FIX_LABELS.md` |
| C1 formulations | 36 ΔAUC CIs include 0; O/E 1.12–1.19 vs 0.95–0.99 | `R/C1_endpoint.md` |
| Baseline design | 23 raw predictors, 31 design columns | `R/AUDIT_SYSTEM.md` §0; `R/CLINICAL_UTILITY.md` |
| Radiomics sentinel | 10⁶ in 3 columns, 4 scans | `R/FIX_RADIOMICS_CLIP.md` |
| Legacy columns; deep features | 2,446; 720 per region, 8 flips | `R/FIX_RADIOMICS_CLIP.md`; `R/DEEP_FEATURES.md` |
| Shipped-model reproduction | 1.1 × 10⁻¹⁵; 46 columns | `R/SHAP_PRISM_SPLIT.md` §1 |
| Ladder (3.4, Fig 3A) | 0.585 [0.496, 0.666]; 0.644 [0.560, 0.721]; 0.698 [0.615, 0.774]; 0.619; 0.693; 0.720 [0.638, 0.792]; GBM 0.687, 0.718 | `M/FIGURES.md` Fig 3A; `R/C3_radiomics.md` |
| Tuning grids; literature baselines | ±0.025; ET 0.636; rule 0.551, Δ −0.147 [−0.239, −0.062]; RANO 2.0 0.508; Cox 0.628 | `R/BASELINES.md` |
| Radiomics nested (Table 3) | −0.032 [−0.084, +0.017] (0.666); +0.028 [−0.017, +0.071] (0.747); 0/70, 8/70; 1/70 +0.035 [+0.002, +0.068]; 1.75; slope 0.60 vs 0.89 | `R/C3_radiomics.md`; `F/table3_forest.csv` |
| C2 search | 0.664 [0.601, 0.722], p = 0.050 | `R/C2_feature_search.md`; `R/FINAL_RESULTS.md` |
| Deep features | −0.004 [−0.069, +0.063]; +0.011 [−0.032, +0.056]; 0.652 vs 0.566; r = 0.58; D0 −0.049 [−0.085, −0.014] | `R/DEEP_FEATURES.md`; `F/table3_forest.csv` |
| SHAP | 45% / 51%; 0.692 / 0.694; treatment 58%, clinical 25%, timing 17% | `R/SHAP.md`; `M/FIGURES.md` Fig 3C |
| Phase ladder (3.5, Fig 4) | R2 0.664; R2 − R0 +0.080 [+0.005, +0.152]; R2 + I1 0.696; post-RT 0.549–0.604; −0.003; primary 0.549 (0.458–0.642) → 0.610 (0.529–0.688), +0.061 (−0.038, +0.156), p 0.21; null +0.028; 44 columns; secondary +0.061 (−0.041, +0.157), slope 0.44; +0.005 to +0.04; age 0.586; later 69 scans, 0.343–0.472; 167 / 84 / 83 | `R/PHASE_LADDER.md`; `F/fig4_phase.csv` |
| Clean label (3.6) | 12 of 93 (10 patients); 0.722 (0.639–0.799) vs 0.696 (0.610–0.776); +0.027 (−0.033, +0.082); −0.068 | `R/CLEAN_LABEL.md` |
| Positive controls | r 0.9957–0.9998; 0.68 [0.62, 0.74]; 49% of 74, p 0.54; 79%, p 0.0003; 3.2-fold, ≤ 14 d; ρ −0.01; 79%, κ 0.53; 3 identical pairs; 12 scans | `R/DIAGNOSTICS_IMAGING.md` |
| Re-segmentation | Dice 0.80 / 0.85; 0.681 → 0.665, Δ −0.016 [−0.057, +0.025]; 45%; bsf 0.677, 41%; forward +0.030 [−0.008, +0.069] | `R/RESEGMENTATION.md`; `F/table3_forest.csv` |
| LUMIERE (3.7) | 0.608 [0.469, 0.739]; 0.620 [0.495, 0.733]; MU CV 0.667 / 0.675; 0.610 / 0.632; −0.001 [−0.073, +0.057]; O/E 1.33 / 0.99; 0.93–0.97; rank 0.659 [0.529, 0.767]; deep +0.050 to +0.089, +0.050 [+0.002, +0.109]; random up to +0.045; cohort AUC ≈ 0.8; shipped 0.613 [0.500, 0.729], 118 scans; gap 0.788 [0.703, 0.868] | `R/EXTERNAL_LUMIERE.md`; `R/DEEP_FEATURES.md`; `R/BASELINES.md`; `R/SCHEDULE_COUPLING.md` |
| External loss 0.05–0.06 (Discussion) | derived: 0.667 − 0.608, 0.675 − 0.620 | `R/EXTERNAL_LUMIERE.md` |
| CFB-GBM | 77 pts / 19 events; +0.007 (−0.019, +0.035); p 0.151; MDE 0.038; 0.501 / 0.565; +0.185 (+0.064, +0.293), +0.148 (+0.031, +0.266); −0.009 / −0.022; 107 pts / 30 events; 264 patients; t1 6–8 weeks after RT | `R/CFB_ADC.md`; `O/analyses/cfb_adc/rule.json`; `docs/literature/DATASETS.md` |
| Calibration and utility (3.8) | O/E 0.96; CITL −0.09 [−0.42, 0.28]; slope 0.89 [0.50, 1.43]; NB 0.232 vs 0.189; −0.020 [−0.038, −0.004]; deep ±0.002; 3.0 EPP; 2,190 (970) | `R/CLINICAL_UTILITY.md` |
| Sensitivity, imbalance, schedule | 0.642–0.725; −0.032 to +0.028; −0.031 to +0.023; 0.687 [0.595, 0.768] | `R/SENSITIVITY.md`; `R/IMBALANCE.md`; `R/SCHEDULE_COUPLING.md` |
| Audit layer (3.9, Fig 5) | 1.7 × 10⁻¹⁶; 1.3 × 10⁻¹⁵; P1 0.841 [0.790, 0.885], 0.823 [0.776, 0.865]; 5 / 10 pre-RT events; 0.567 (6 scans); conformal AUC 0.667; P2 0.731 [0.635, 0.812], 0.725, 0.698, +0.006 [−0.023, +0.036], +0.003 [−0.031, +0.036]; 97.6%; rule (i) 0.723; within-phase 0.555 / 0.663 / 0.597; 72.6%; IDH unknown 0/93, 6/117, 5/39; −0.023 [−0.047, −0.001]; treatment-only 0.701 [0.622, 0.776], +0.003 [−0.050, +0.048]; 8 scans, 1–58 days; 40.9% vs 4.4%; −0.68 logits; O/E 1.33 → 0.89; coverage 0.715 (0.340 events); top 5 ≤ 4%; 200 bootstraps; 70/30 | `R/AUDIT_SYSTEM.md`; `O/analyses/audit_system/{p2,conformal,referral,shortcut_arms,lumiere_smd,lumiere_oe,stability_summary,checks}.csv` |
| Literature numbers (Intro, Discussion) | Booth 0.765 (≈0.77); Taylor 0.90–0.93; Christodoulou 0.80; Rai 0.728; An 0.882/0.667, 0.709/0.911; Varoquaux ±10%, n = 100; Yu 81%, 24%, 0.10; Park 29.4%; Leone 0.69; Gomaa 0.727 vs 0.717; Abler 0.74 vs 0.75; Jang 0.52, 19 patients; Chen 0.887 → 0.762; Tak 75–89%; Yun 0.75 | `docs/literature/COMPARABLE_RESULTS.md` |
| RANO windows | 12 weeks / 84 days | `R/FIX_TREATMENT_ASOF.md` §2; `R/PHASE_LADDER.md` |
