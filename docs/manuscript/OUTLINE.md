# Manuscript outline (2026-10-15)

Structure agreed on 2026-10-15: (1) call out the splits, (2) show the results on the single split the project used for a
long time (the PRISM report split), (3) compare clinical and radiomics features head to head, (4) describe the auditable
system built around the model. Numbers below are from the docs cited; figures and their source mapping are in
[FIGURES.md](FIGURES.md) (in progress), the system in `docs/results/AUDIT_SYSTEM.md` (in progress).

**Working title.** *Single splits, phase of care and the value of MRI radiomics for post-treatment glioma surveillance:
a re-evaluation and an auditable risk model.*

**One-sentence message.** On MU-Glioma-Post, a single 30-patient split gives AUC 0.80 for an MRI radiomics model, but
that split is easy by composition; under repeated cross-validation, censoring-aware labels and external testing,
clinical + treatment-phase information reaches about 0.70, MRI radiomics and deep features add nothing measurable, and
the useful contribution is an auditable model that states what it knows and when it should not be trusted.

## 1. Introduction
- Surveillance MRI after glioma treatment: the clinical question (progression within ~4 months), pseudoprogression.
- Radiomics/DL reports on this task, often single split; Christodoulou 2026 (same dataset, 0.80, one split).
- Known problems: split variance (An 2021, Varoquaux 2018), external drops (Yu 2022), clinical-only baselines rarely
  reported (Leone 2023, Gomaa 2025, Abler 2025 found them competitive).
- Gap: nobody treats phase of care (time since RT) as a confounder of imaging AUC for forward prediction
  ([COMPARABLE_RESULTS.md](../literature/COMPARABLE_RESULTS.md) §E, "not found").
- Contributions: (i) split-variance and composition analysis of the single split; (ii) clinical vs radiomics/deep under
  rigorous evaluation, internal + external; (iii) phase of care as the driver; (iv) an auditable decision-support layer.

## 2. Methods
- Cohorts: MU-Glioma-Post (308 scans / 155 patients; grade 4 = 249 / 126), LUMIERE external (132 / 61). Flow:
  [FLOW.md](FLOW.md), Table 1: [TABLE1_COHORT.md](TABLE1_COHORT.md).
- Label: documented progression ≤ 120 d after the scan, death censored; IPCW AUC(120 d)
  ([FIX_LABELS.md](../results/FIX_LABELS.md), [C1_endpoint.md](../results/C1_endpoint.md)).
- Features: clinical, timing, treatment as of the scan date ([FIX_TREATMENT_ASOF.md](../results/FIX_TREATMENT_ASOF.md)),
  volumes, delta, radiomics (legacy + v2, clipped), deep (SwinUNETR, BrainSegFounder).
- Evaluation: 5×5 repeated patient-grouped CV, nested selection, paired patient-cluster bootstrap, permutation tests
  ([FIX_EVALUATION.md](../results/FIX_EVALUATION.md)). Pre-specified primary contrasts snapshotted before running.
- The PRISM report split and the 500-split design ([SPLIT_VARIANCE.md](../results/SPLIT_VARIANCE.md)).
- The system: locked model, per-scan audit record, abstention/referral, shortcut audit (AUDIT_SYSTEM.md).
- Reporting: TRIPOD+AI, CLEAR ([CHECKLIST_TRIPOD_AI.md](CHECKLIST_TRIPOD_AI.md), [CHECKLIST_CLEAR.md](CHECKLIST_CLEAR.md)).

## 3. Results

### 3.1 The single split (PRISM report split, seed 62; 29–30 test patients, 82 scans)
Source: [SHAP_PRISM_SPLIT.md](../results/SHAP_PRISM_SPLIT.md), [SPLIT_VARIANCE.md](../results/SPLIT_VARIANCE.md).
- PRISM report model 0.802 naive / 0.817 IPCW [0.690, 0.920].
- Clinical + timing + treatment ridge on the same split: 0.871 naive / 0.851 IPCW [0.735, 0.947] — higher, no imaging.
- Baseline + legacy radiomics 0.862–0.867; baseline GBM 0.844.
- Why it is easy: 36/82 test scans are pre-RT and none progresses (89th percentile among splits); 60 % of
  positive–negative pairs are against a pre-RT negative; a no-training "post-RT" rule scores 0.740.
- On the 42 post-RT test scans: PRISM report model 0.778, baseline 0.730 (wide CIs).

### 3.2 What single splits do (500 splits of the same design)
- PRISM report pipeline with feature selection redone per split: 0.720 ± 0.055 (2.5–97.5 %: 0.610–0.819); the PRISM
  report split is at the 92nd percentile; 7 % of splits reach ≥ 0.802.
- Shipped feature set refitted: 0.815 ± 0.044 — optimistic because its features were selected on patients that are test
  patients in other splits (selection leakage, upper bound).
- Baseline 0.801 ± 0.052; baseline + radiomics 0.801 ± 0.053 (mean Δ −0.000) — radiomics adds nothing across splits too.
- Composition (pre-RT share, IDH-mutant share, later post-RT share) explains about two thirds of the PRISM split's excess.
- Single-split AUC is also not comparable with the CV numbers: naive label vs IPCW, different cohort rules (§3.3).

### 3.3 Clinical vs radiomics, head to head
Source: [FINAL_RESULTS.md](../results/FINAL_RESULTS.md), [C3_radiomics.md](../results/C3_radiomics.md),
[DEEP_FEATURES.md](../results/DEEP_FEATURES.md), [PHASE_LADDER.md](../results/PHASE_LADDER.md),
[CLEAN_LABEL.md](../results/CLEAN_LABEL.md), [EXTERNAL_LUMIERE.md](../results/EXTERNAL_LUMIERE.md),
[RESEGMENTATION.md](../results/RESEGMENTATION.md), [DIAGNOSTICS_IMAGING.md](../results/DIAGNOSTICS_IMAGING.md).
- Ladder (grade 4): clinical 0.585 → + timing 0.644 → + treatment 0.698; all gliomas 0.720.
- Radiomics, nested (clipped): Δ −0.032 [−0.084, +0.017] grade 4; +0.028 [−0.017, +0.071] all gliomas; 1/70 configs
  nominally significant. Deep features: no gain. Re-segmentation: no gain.
- Phase of care: post-RT only, R2 0.549 → + imaging 0.610, Δ +0.061 [−0.038, +0.156], p = 0.21.
- Clean imaging-defined label: baseline + imaging Δ +0.027 [−0.033, +0.082] (rule not met).
- Positive control: imaging detects progression on the progression scan itself with only AUC 0.62–0.68.
- External LUMIERE (locked): clinical + timing 0.61–0.66.
- SHAP: imaging takes about half the credit in models that include it, with no AUC gain (credit ≠ value).
- CFB-GBM (third cohort, diffusion/ADC): [CFB_ADC.md](../results/CFB_ADC.md) — pending.

### 3.4 The system
Source: AUDIT_SYSTEM.md (in progress). Locked model + model card; per-scan audit record (as-of inputs, phase, risk with
interval, exact additive contributions, referral flags with reasons); selective prediction and conformal coverage;
early-post-RT referral evaluated against a composition-matched reference; shortcut/bias audit; explanation stability;
reproducibility manifest.

## 4. Discussion
- Single-split numbers on small cohorts measure the split; report repeated CV, the split distribution, phase strata and
  a no-imaging reference.
- Phase of care drives discrimination; imaging-model AUCs that mix pre-RT and surveillance scans are inflated.
- Why imaging fails here: label (documented progression), conventional MRI only, n; what would change it (diffusion,
  perfusion, expert per-scan labels, more patients).
- What the system offers at AUC ~0.70: calibrated risk, explicit uncertainty and referral, auditability.
- Limitations: single development cohort, small external cohort, retrospective labels, no reader study.

## 5. Figures (FIGURES.md)
1. Single split: model AUCs, pair decomposition, post-RT subset.
2. 500-split distributions with the PRISM split and 0.80 marked; AUC vs composition.
3. Clinical vs radiomics: feature ladder, ΔAUC forest plot, SHAP shares.
4. Phase of care.
5. The system: architecture, example audit record, risk–coverage / referral.
