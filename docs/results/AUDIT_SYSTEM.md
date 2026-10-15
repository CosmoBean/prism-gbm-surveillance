# Auditable decision-support layer ("the system") on the clinical + timing + treatment baseline

Code: `prism/audit/` (locked model, conformal, audit record, provenance) and `prism/analyses/audit_system.py`
(`python -m prism audit`). Outputs: `outputs/results/analyses/audit_system/`.

## Plan

This plan was written before any output of this module was produced. A copy is saved as
`outputs/results/analyses/audit_system/PLAN_snapshot.md`. It is not changed after the run. Anything added after the
results is labelled **EXPLORATORY**.

### 0. Model (not new)
The predictor is the existing C3 baseline. Features are clinical + timing + as-of-scan treatment
(`features.tabular.{clinical,timing,treatment}`, 23 raw columns; 31 after missingness indicators per FINAL_RESULTS). Preprocessing is `c3.BASE_PRE`: median imputation
with missingness indicators, then standardisation, fitted on the verified training scans. The model is ridge logistic
on the verified 120-d labels, with C chosen by inner 3-fold patient-grouped log-loss (`formulations.fit`). The CV
predictions are required to reproduce `outputs/results/c3/<pop>/oof_repeats.csv.gz` (column
`None|none|none|none|ridge`) to 1e-9; if they do not, the run stops. The primary population is grade 4; the
secondary is all gliomas. Horizon H = 120 d. There is no recalibration step: the displayed risk is the ridge output.

### 1. Locked artifact
- **Fit.** Fitted on all MU scans of each population, verified labels (`audit_system/locked_<pop>.joblib`).
- **Contents.**
  - preprocessor, coefficients and C;
  - feature names and groups;
  - training 1st/99th percentiles of each continuous feature, for the OOD flag;
  - 200 patient-cluster bootstrap refits of the whole pipeline (imputation, scaling, C selection), for the risk interval;
  - a split-conformal model and its threshold. Patients are split 70/30 into proper-training and calibration, seed 0.
- **Model card** (`model_card_<pop>.json`):
  - git commit and dirty flag;
  - sha256 of every input table (`mu_cohort.csv`, `mu_index.csv`, `folds.csv`, the MU clinical workbook);
  - feature list with unit and source column;
  - training counts;
  - CV performance read from `outputs/results/c3/<pop>/results.csv` and `outputs/results/analyses/utility/calibration.csv`, with paths cited;
  - intended use and out-of-scope statements.

### 2. Per-scan audit record
Records come from the out-of-fold fits (repeat 0), not from the locked model. Each record contains:
- **Inputs.** Each input with its raw value, source column and as-of day, with a check that it was known by the scan day (as-of day ≤ scan day).
- **Phase of care.** `phase_ladder.phase_label`: pre-RT / during RT / early post-RT (≤ 84 d after RT end) / later post-RT.
- **Risk.** Predicted risk with a 95% interval: the 2.5–97.5 percentiles over 200 patient-cluster bootstrap refits of that fold's training pipeline.
- **Contributions.** Exact additive log-odds contributions, coef × standardised value, summed into clinical / timing / treatment groups. Missingness indicators are assigned to their source feature's group. The record checks that intercept + Σ contributions = logit (|error| < 1e-8).
- **Referral flags with reasons.**
  - (i) Early post-RT window: phase = early post-RT.
  - (ii) Out of distribution: IDH or MGMT unknown, or any continuous input outside its training-fold [1st, 99th] percentile (missing values are not counted).
  - (iii) Uncertain: the α = 0.2 conformal set is {0, 1}.
- **Example selection.** Six examples from repeat 0, chosen with seed 0: one pre-RT, one during RT, and one event plus one non-event each from early post-RT and later post-RT. Output: JSON plus a markdown render.

### 3. Evaluation inside the existing 5×5 patient-grouped CV (`outputs/data/folds.csv`)
**No leakage.** Every fitted step is fitted on the training fold only: preprocessing, C, OOD percentiles, the
bootstrap, the conformal model and threshold, and the coverage threshold.

**Split conformal (patient-level).**
- Within each training fold, patients are split 70/30, seed = repeat×10+fold, into proper-training and calibration.
- The pipeline is refit on the proper-training patients.
- Score: s = 1 − p̂_y, on verified calibration scans.
- Threshold q̂: the weighted (1−α) quantile with each calibration scan weighted 1/(number of the patient's verified calibration scans). Each patient therefore has total weight 1, and the test patient gets weight 1 in the finite-sample correction.
- Prediction set: {y : 1 − p̂_y ≤ q̂}.
- The conformal model is distinct from the displayed-risk model, which is fitted on the whole training fold. The conformal model's own AUC is reported, as the cost of splitting.
- Coverage is evaluated on verified test scans only. Censored scans have no label, so coverage under censoring is not guaranteed; this is stated as a limitation.
- Coverage is reported per scan (primary) and patient-weighted.

**Selective prediction.**
- Confidence = max(p̂, 1 − p̂) of the displayed-risk model (primary).
- Secondary confidence: the negative width of the bootstrap 95% interval, and conformal singleton vs not.
- Risk–coverage curves: for each repeat, the pooled out-of-fold scans are ordered by confidence. At coverage c ∈ {1.0, 0.95, …, 0.3}, the IPCW AUC(120 d) and IPCW Brier(120 d) of the retained scans are computed with cohort-level censoring weights (`metrics.fast_auc_brier` subset) and averaged over the 5 repeats.
- Each curve is shown next to two references, each based on 1000 draws:
  - random removal of the same number of scans;
  - composition-matched random removal: the same number of retained scans in each phase of care as the confidence rule retained.

**Conformal sets** at α = 0.1 and 0.2. Reported:
- empirical coverage, overall and per phase;
- singleton rate;
- AUC and Brier on singleton scans.

**Referral rules.**
- Rule (i), early post-RT: AUC, Brier, O/E and calibration slope on non-referred vs referred scans. Alongside these:
  - random removal of the same number of scans (1000 draws);
  - within-phase AUCs, which carry no composition effect.
- The composition-matched reference for rule (i) is by construction the rule itself, because it removes a whole phase. Any AUC gain from rule (i) is therefore a composition effect unless within-phase AUCs say otherwise. This will be stated plainly.
- Rules (ii) and (iii), and their union with (i), are reported the same way (descriptive).

**Pre-specified primary quantities** (grade 4 primary, all gliomas secondary):
- **P1.** Conformal coverage at α = 0.2 on verified test scans, overall and per phase of care. Target ≥ 0.78 overall. P1 is "met" if overall coverage ≥ 0.78. A per-phase coverage < 0.78 is reported as a conditional-coverage failure. 95% CI from a patient-cluster bootstrap (1000).
- **P2.** AUC on retained scans at 70% coverage minus the composition-matched random-removal AUC.
  - Retained scans: test scans whose confidence ≥ the training fold's 30th percentile of in-sample confidence (all training scans), so realised coverage is approximately 70% and is reported.
  - AUC_retained: the mean over repeats of the pooled-OOF IPCW AUC on the retained scans.
  - Reference: the expectation, over 1000 draws, of the same statistic on random retained sets with the same per-repeat, per-phase counts.
  - CI: patient-cluster bootstrap with 1000 draws; each draw recomputes the reference with 100 draws. P2 is "met" if the CI excludes 0 (above 0).

### 4. Shortcut / bias audit
- **(a) Unknown-marker indicators.**
  - The baseline is refit without `idh_unknown` and `mgmt_unknown`: unknown merges into the reference level. As a secondary, `rt_date_unknown` is also dropped.
  - ΔAUC with a paired patient-cluster bootstrap CI (`metrics.evaluate_repeated`).
  - Counts of each marker unknown by 120-d label (progression / no progression / censored).
- **(b) Confounder-only models.** Timing-only and treatment-only ridge models, with the same CV and ΔAUC vs the baseline.
- **(c) Subgroups.**
  - Strata:
    - GBM vs non-GBM (all gliomas; also within grade 4 if both levels exist);
    - MGMT methylated / unmethylated / unknown, and unknown vs known;
    - IDH wildtype / mutant / unknown;
    - sex;
    - age tertiles (patient-level tertiles within the population);
    - phase of care.
  - Field strength and scanner: only if present in the prepared MU tables. The prepared tables have no acquisition columns (`analyses/tables.py` sets MU field strength to NaN, "not distributed"), so this is stated as unavailable.
  - Metrics per stratum, computed on the baseline out-of-fold predictions:
    - IPCW AUC with the censoring distribution re-estimated within the stratum;
    - calibration slope and calibration-in-the-large intercept, both IPCW-weighted logistic fits on verified scans;
    - Kaplan–Meier O/E.
  - Each metric is the mean over repeats, with a patient-cluster bootstrap 95% CI (1000).
  - Strata with fewer than 10 events are marked descriptive only.
- **(d) LUMIERE transport.** The baseline cannot be applied to LUMIERE, which has no treatment or RT-date fields (`EXTERNAL_LUMIERE.md`). The transport audit therefore uses the locked shared-feature ridge (clinical + timing + volumes, `external_lumiere.fit`, grade-4- and all-glioma-trained):
  - standardised mean difference per shared feature, MU vs LUMIERE (pooled SD);
  - mean exact contribution (coef × standardised value) per feature on MU vs LUMIERE, ranked by shift;
  - LUMIERE O/E with vs without the two molecular unknown indicators (refit on MU);
  - secondary: coverage on LUMIERE of an MU-calibrated split-conformal set (α = 0.2).

### 5. Explanation stability
- Sources:
  - standardised coefficients of the 25 CV fits;
  - 200 patient bootstraps of the full-data fit.
- Reported:
  - per-feature sign agreement with the locked model;
  - Kendall τ-b between |coef| vectors (each fit vs locked);
  - top-5 overlap (|∩|/5);
  - Kendall τ within the locked top 5;
  - group shares of mean |contribution|.
- LUMIERE: the baseline cannot be refit there. Instead, the shared-feature ridge is refit on LUMIERE (all 132 scans, plus 200 patient bootstraps), and its coefficient signs are compared with the MU locked shared-feature model.

### 6. Reproducibility
- `MANIFEST.json`:
  - sha256 of inputs and outputs;
  - git hash;
  - Python and package versions from `uv.lock` and the venv;
  - command line.
- `scripts/11_audit_system.sh`.

### Multiplicity
Only P1 and P2 are primary. All subgroup and shortcut contrasts are secondary or descriptive and are not corrected for
multiplicity.

---

## Run record

- **Full run.** 2026-10-15, `python -m prism audit --workers 24`, 114 s, log `outputs/logs/audit_system.log`. Code is
  uncommitted on `manuscript-week` (HEAD `6c45c85`); hashes are in `MANIFEST.json`.
- **Smoke run.** A reduced run (20 bootstrap / 20 reference draws, 10 refits) came after the plan was frozen and before
  the full run. The plan was not changed afterwards.
- **Code changes after the plan, none of which changes a model or a pre-specified rule:**
  1. **As-of rule for age, sex and previous brain tumour (after the smoke run).** These are now "demographic / history,
     known at any scan". Before, they were tied to diagnosis day 0. Why: a few scans predate the diagnosis date, which
     would otherwise flag age and sex there.
  2. **CITL is set to NaN when a stratum has only one class.** Before, it was −32 in the IDH-unknown stratum, which has
     0 events.
  3. **Within-subset O/E, slope and CITL of the referral rules now use the same estimator as the subgroups.** Before,
     `metrics.point_metrics` failed silently on some subsets. Fixes 2 and 3 came after the first full run; the
     reported tables are from the second full run, and all other numbers were identical between the two.
- **Two checks, both passed (`checks.csv`):**
  - the CV predictions reproduce `c3/<pop>/oof_repeats.csv.gz` (`None|none|none|none|ridge`), max |Δ| = 1.7e-16;
  - intercept + Σ contributions = logit on every out-of-fold prediction, max error 1.3e-15.
- **Environment drift:** `MANIFEST.json` shows scipy 1.17.1 installed against 1.18.1 in `uv.lock`. All other
  listed packages match. The venv was not re-synced (no `uv sync`).

## Results

All files are under `outputs/results/analyses/audit_system/`. Grade 4 is primary; all-glioma numbers are given after
a slash or in a second row. AUC means IPCW AUC(120 d), the mean over 5 repeats of the pooled out-of-fold value
(cohort-level censoring weights unless "within subset" is stated).

### 1. Locked artifact and model card
`locked_{grade4,all_glioma}.joblib` and `model_card_{grade4,all_glioma}.json`.

| | Grade 4 | All gliomas |
|---|---|---|
| Training scans / patients / verified / events | 249 / 126 / 210 / 93 | 308 / 155 / 256 / 100 |
| C | 0.1 | 0.1 |
| Conformal q at α = 0.2 / 0.1 (locked) | 0.613 / 0.683 | 0.529 / 0.620 |
| CV AUC [95% CI], read from `c3/<pop>/results.csv` | 0.698 [0.615, 0.774] | 0.720 [0.638, 0.792] |
| CITL [95% CI] / slope [95% CI], from `analyses/utility/calibration.csv` | −0.09 [−0.42, 0.28] / 0.89 [0.50, 1.43] | in card |

- **Card contents:** sha256 of `mu_cohort.csv`, `mu_index.csv`, `folds.csv` and the MU clinical workbook; unit, source
  column and as-of rule of all 23 features; intended use and out-of-scope list.
- **Out of scope:**
  - pseudoprogression diagnosis;
  - any cohort without the treatment fields, including LUMIERE;
  - other institutions without validation.
- **Git state:** the card records the commit and the 16 uncommitted paths present at run time.

### 2. Per-scan audit records
`records/<scan_id>.json` (6 scans) and the render `records.md`. All come from out-of-fold fits, repeat 0, grade 4.

| Scan | Phase | Risk [95% bootstrap] | Conformal set α = 0.2 | Flags | 120-d label (evaluation only) |
|---|---|---|---|---|---|
| PatientID_0201_Timepoint_3 | pre-RT | 0.04 [0.01, 0.27] | {0} | OOD (MGMT unknown) | 0 |
| PatientID_0136_Timepoint_2 | during RT | 0.47 [0.36, 0.77] | {0} | none | 1 |
| PatientID_0117_Timepoint_1 | early post-RT | 0.50 [0.39, 0.61] | {0, 1} | (i) 26 d after RT; (iii) | 1 |
| PatientID_0059_Timepoint_1 | early post-RT | 0.48 [0.22, 0.77] | {0, 1} | (i); (ii) rt_start_day −34 < training 1st pct; (iii) | 0 |
| PatientID_0089_Timepoint_5 | later post-RT | 0.45 [0.34, 0.72] | {0, 1} | (ii) rt_start_day 48 > 99th pct; (iii) | 1 |
| PatientID_0014_Timepoint_4 | later post-RT | 0.63 [0.44, 0.86] | {1} | none | 0 (set misses) |

Every input carries its source column and as-of day. The as-of check runs over **all** scans
(`checks.csv: inputs_not_known_by_scan`) and found one real problem (EXPLORATORY): IDH/MGMT are used at scans taken
before the diagnosis date. This affects 8 grade-4 scans (7 patients; 1 event, 4 non-events, 3 censored) and 11 scans
in all gliomas, 1–58 days before diagnosis, when molecular pathology cannot yet be known. This is a small look-ahead in
the existing baseline, not just in the audit layer. Everything else (timing, treatment) passes; the as-of treatment fix
holds (`FIX_TREATMENT_ASOF.md`).

The record shows the full-training-fold risk next to the split-conformal set, which comes from a model fitted on 70% of
the training patients. The two can disagree in direction (scan 0136: risk 0.47, set {0}). This happens in 1.8% / 2.9%
of singleton sets (EXPLORATORY, from `cv_predictions_<pop>.csv.gz`). The median width of the 95% bootstrap interval is
0.37 (IQR 0.32–0.44) / 0.31 (EXPLORATORY).

### 3. Selective prediction, conformal sets, referral rules

**P1: conformal coverage at α = 0.2 (target ≥ 0.78)** (`conformal.csv`, verified test scans, mean over repeats, 95%
patient-cluster bootstrap CI)

| Population | Overall | Pre-RT | During RT | Early post-RT | Later post-RT | Events / non-events | Singleton rate |
|---|---|---|---|---|---|---|---|
| Grade 4 | **0.841 [0.790, 0.885]** | 0.868 (5 events: **0/5 covered**) | 0.567 (6 scans) | 0.871 | 0.806 | 0.824 / 0.855 | 0.595 |
| All gliomas | **0.823 [0.776, 0.865]** | 0.850 (10 events: 0/10) | 0.550 (8 scans) | 0.852 | 0.790 | **0.698** / 0.904 | 0.696 |

- **P1 is met overall in both populations.** Per patient, coverage is 0.828 / 0.796.
- **Conditional coverage fails in two places:**
  - **During RT:** 0.57 / 0.55, but on only 6 and 8 scans.
  - **Pre-RT progressions:** almost every pre-RT scan gets the singleton {0} (98% / 99%), so all 5 / 10 pre-RT
    progressions fall outside their sets. Pre-RT coverage looks high only because non-events dominate there.
- **Class-conditional coverage of events in all gliomas** is 0.698, below target.
- **At α = 0.1,** coverage is 0.949 [0.916, 0.975] / 0.928 [0.896, 0.955] and the singleton rate 0.296 / 0.422.
- **Cost of the 70/30 split:** the conformal model's AUC is 0.667 / 0.709, against 0.698 / 0.720 for the displayed
  model.
- **Singletons vs the rest:** at α = 0.2, the displayed-risk AUC on singleton scans is 0.732 / 0.723 (non-singletons
  0.628 / 0.594), and 70.0% / 72.6% of verified singleton sets are correct.

**P2: AUC at about 70% coverage minus the composition-matched reference** (`p2.csv`). The coverage threshold is set
on the training fold.

| | Realised coverage | AUC retained [95% CI] | Composition-matched | Random removal | **P2 [95% CI]** | Retained share: pre-RT / early post-RT |
|---|---|---|---|---|---|---|
| Grade 4 | 0.671 (0.639–0.723 by repeat) | 0.731 [0.635, 0.812] | 0.725 | 0.698 | **+0.006 [−0.023, +0.036]** | 97.6% / 49.0% |
| All gliomas | 0.685 | 0.735 [0.654, 0.820] | 0.733 | 0.720 | **+0.003 [−0.031, +0.036]** | 97.9% / 44.4% |

**P2 is not met in either population: the CI includes 0.**
- Abstaining on the least confident scans raises AUC by +0.032 / +0.015 against random removal.
- Almost all of that rise comes from changing the phase mix: low-risk pre-RT scans are kept and post-RT scans are
  dropped.
- Within the phase composition, abstention adds nothing measurable.

**Risk–coverage curves** (`risk_coverage.csv`, `risk_coverage.png`; rank-based on pooled out-of-fold predictions):
- **Confidence = max(p, 1−p), at 70% coverage:**
  - grade 4: AUC 0.728 (composition-matched 0.723, random 0.698); Brier 0.189 (0.192, 0.219);
  - all gliomas: AUC 0.731 (0.732); Brier 0.166 (0.179).
  - Brier falls steeply with abstention, but mostly by composition as well. The one exception is all gliomas, where
    retained-scan Brier stays below the composition reference (0.166 vs 0.179 at 70%; no CI computed).
  - Below 50% coverage, all-glioma AUC collapses (0.635 at 30%) because the retained set is mostly pre-RT scans with
    few events.
- **Secondary confidence, bootstrap-interval width:** no gain in grade 4 (AUC 0.690 at 70%).

**Referral rules** (`referral.csv`, `referral_within_phase.csv`; random reference = 1000 draws)

| Grade 4 | Referred | AUC kept | AUC referred | Random removal [2.5–97.5%] | Composition-matched | Kept O/E / slope |
|---|---|---|---|---|---|---|
| (i) early post-RT | 39.4% (98 scans, 47 events) | 0.723 | 0.663 | 0.699 [0.673, 0.723] | 0.723 (= the rule itself) | 1.10 / 0.86 |
| (ii) OOD | 29.8% | **0.671** | 0.665 | 0.698 | 0.695 | 1.16 / 0.89 |
| (iii) uncertain | 40.5% | 0.732 | 0.628 | 0.699 | 0.734 [0.709, 0.760] | 0.97 / 0.79 |
| any of (i)–(iii) | 72.6% | 0.735 | 0.687 | 0.698 | 0.753 | 1.17 / 0.89 |

All gliomas: (i) 33.8%, AUC kept 0.732 vs random 0.719 [0.700, 0.740]; (ii) 32.3%, 0.680; (iii) 30.4%, 0.723 vs
composition-matched 0.731; any rule 68.0%, 0.670.

**Within-phase AUC** (grade 4 / all gliomas; these carry no composition effect):

| Phase | Grade 4 | All gliomas |
|---|---|---|
| Pre-RT | 0.555 (5 events) | 0.493 |
| During RT | 0.448 (6 scans) | 0.671 |
| Early post-RT | 0.663 | 0.678 |
| Later post-RT | 0.597 | 0.644 |

**Plain statement: abstention does not improve discrimination beyond composition.**
- **Rule (i)** raises AUC from 0.698 to 0.723 only because it removes a whole phase. The scans it keeps are
  discriminated no better than before: their within-phase AUCs are 0.555 and 0.597, both below the pooled 0.698.
- **Rule (iii)** sits at or below its composition-matched reference.
- **Rule (ii)** *lowers* AUC, because OOD scans are disproportionately easy non-progressions with unknown markers. On
  OOD scans themselves the model over-predicts: referred O/E 0.70, slope 0.66.
- **The referral rules are honest flags of where the model is weak.** The referred early-post-RT scans have AUC 0.663
  and Brier 0.276, against 0.181 for the kept scans. The rules are not a way to obtain a better model.

### 4. Shortcut and bias audit

**(a) Missingness codes** (`shortcut_arms.csv`, `unknown_by_label.csv`)

Unknown-marker share by 120-d label (progression / no progression / censored):

| Marker | Grade 4 | All gliomas |
|---|---|---|
| IDH unknown | **0/93** / 6/117 (5.1%) / 5/39 (12.8%) | **0/100** / 17/156 (10.9%) / 10/52 (19.2%) |
| MGMT unknown | 6/93 (6.5%) / 25/117 (21.4%) / 8/39 (20.5%) | 8/100 (8.0%) / 41/156 (26.3%) / 12/52 (23.1%) |

- **Effect on the model:** dropping `idh_unknown` and `mgmt_unknown` lowers grade-4 AUC to 0.676 [0.592, 0.752],
  **ΔAUC −0.023 [−0.047, −0.001]**. Also dropping `rt_date_unknown` gives Δ −0.022 [−0.045, −0.001]. In all gliomas
  the drop is Δ −0.011 [−0.031, +0.008].
- **Interpretation:**
  - Part of the grade-4 discrimination comes from "molecular test not recorded → no progression".
  - This is a data-recording shortcut, not biology.
  - It is the same feature that drives LUMIERE under-prediction (see (d)).
  - `idh_unknown` is a top-3 coefficient of the locked grade-4 model.

**(b) Confounder-only models**
- **Timing only:** 0.559 [0.475, 0.637], Δ −0.139 [−0.214, −0.070]. All gliomas: 0.607, Δ −0.112 [−0.175, −0.059].
- **Treatment only:** **0.701 [0.622, 0.776], Δ +0.003 [−0.050, +0.048]**. All gliomas: 0.710, Δ −0.009 [−0.050, +0.031].
- **Reading:** the as-of treatment block alone (whether and when RT/chemo started or ended, the prescription, and
  surgery day) reproduces the whole baseline. The model is a phase-of-care / treatment-course model, consistent with
  SHAP.md and PHASE_LADDER.md.

**(c) Subgroups** (`subgroups.csv`; censoring re-estimated within the stratum; 1000-draw patient bootstrap; † = fewer
than 10 events, descriptive only)

| Grade 4 stratum | Scans / events | AUC [95% CI] | Slope [95% CI] | CITL [95% CI] | O/E [95% CI] |
|---|---|---|---|---|---|
| GBM | 214 / 86 | 0.68 [0.58, 0.76] | 0.78 [0.36, 1.34] | −0.00 [−0.39, 0.38] | 1.10 [0.90, 1.31] |
| non-GBM grade 4 † | 35 / 7 | 0.72 [0.54, 0.95] | 1.34 | −0.67 [−1.72, −0.03] | 0.66 [0.30, 1.00] |
| MGMT methylated | 88 / 34 | 0.64 [0.52, 0.77] | 0.62 [0.25, 1.76] | −0.17 | 0.99 |
| MGMT unmethylated | 122 / 53 | 0.72 [0.61, 0.84] | 1.11 [0.37, 2.61] | 0.10 | 1.14 |
| MGMT unknown † | 39 / 6 | 0.62 [0.32, 0.83] | 0.51 | −0.66 | 0.70 [0.23, 1.38] |
| IDH wildtype | 208 / 87 | 0.66 [0.56, 0.77] | 0.78 | 0.01 | 1.09 |
| IDH mutant † | 30 / 6 | 0.68 [0.47, 0.95] | 0.62 | −0.52 | 0.73 |
| IDH unknown † | 11 / 0 | n/a | n/a | n/a | 0 events |
| Male / female | 119 / 44, 130 / 49 | 0.67 [0.55, 0.79] / 0.72 [0.61, 0.83] | 0.85 / 0.94 | −0.14 / −0.04 | 1.02 / 1.06 |
| Age ≤ 56.7 / (56.7, 67] / > 67 | 109 / 30, 68 / 35, 72 / 28 | 0.71 / 0.64 / 0.68 | 0.89 / 0.73 / 0.89 | −0.47 / **0.56 [−0.06, 1.28]** / −0.18 | 0.81 / **1.39 [1.07, 1.77]** / 1.06 |
| Pre-RT † | 76 / 5 | 0.57 [0.30, 0.87] | 0.63 | −0.73 | 0.53 [0.12, 1.14] |
| During RT † | 6 / 5 | 0.44 | — | 1.97 | 1.78 |
| Early post-RT | 98 / 47 | 0.66 [0.55, 0.76] | 1.06 [0.33, 2.30] | −0.11 | 0.95 |
| Later post-RT | 69 / 36 | 0.60 [0.45, 0.74] | 0.50 [−0.24, 1.61] | 0.06 | 1.03 |

- **CIs that exclude calibration:**
  - middle age tertile: under-prediction, O/E 1.39 [1.07, 1.77];
  - non-GBM grade 4 (descriptive, 7 events): over-prediction, CITL −0.67 [−1.72, −0.03].
  - These are uncorrected for 19 strata.
- **Within-phase AUCs** are all ≤ 0.66; the pooled AUC is higher than any phase.
- **All gliomas:**
  - GBM vs non-GBM 0.67 vs 0.65 (non-GBM: 94 scans, 14 events; O/E 0.76 [0.43, 1.22], slope 0.45);
  - IDH-mutant 0.56 [0.31, 0.77], slope 0.13;
  - pre-RT 0.49 [0.29, 0.71] (10 events).
- **Field strength and scanner:** unavailable. The prepared MU tables carry no acquisition metadata
  (`analyses/tables.py`: MU field strength "not distributed").
- **Race:** not audited (`PUBLICATION_PLAN.md`).

**(d) LUMIERE transport** (`lumiere_{smd,contrib,oe,conformal}.csv`)

The baseline cannot be applied to LUMIERE (no treatment or RT dates). The audit therefore uses the locked
shared-feature ridge (clinical + timing + volumes), which reproduces `EXTERNAL_LUMIERE.md` (AUC 0.608, O/E 1.33).

- **Largest standardised mean differences, MU → LUMIERE, grade 4:**
  - `idh_unknown` **+0.97** (4.4% → 40.9%);
  - `log_et_cc` −0.84 (segmenter scale);
  - `early_post_rt` −0.72 (53% → 21%; MU also has 26% missing);
  - `log_snfh_cc` −0.56;
  - `mgmt_methylated` +0.39.
- **Exact mean contribution shift:**
  - `idh_unknown` **−0.68 logits** (MU −0.03 → LUMIERE −0.71);
  - `log_et_cc` −0.32;
  - the `early_post_rt` missingness indicator +0.23 (never missing in LUMIERE);
  - net linear-predictor shift −0.64 logits.
  - This confirms SHAP.md.
- **Refit without the two molecular-unknown indicators:**
  - grade 4: LUMIERE O/E 1.33 → **0.89**, slope 0.38 → 0.73, AUC 0.608 → 0.614;
  - all gliomas: O/E 1.30 → 0.96, slope 0.38 → 0.89.
  - The miscalibration under transport is mostly the same missingness shortcut as in (a).
- **Conformal under shift (MU-calibrated, α = 0.2):**
  - LUMIERE coverage is **0.715**: 0.340 on events, 0.947 on non-events; all gliomas 0.715.
  - At α = 0.1 it is 0.772 / 0.797.
  - Coverage breaks under shift, as Mehrtens 2023 led us to expect; this is reported as a finding.

### 5. Explanation stability (`stability_summary.csv`, `stability_features.csv`, `group_shares.csv`, `lumiere_stability.csv`)

| | Grade 4: 25 CV fits | Grade 4: 200 bootstraps | All gliomas: CV | All gliomas: bootstrap |
|---|---|---|---|---|
| Kendall τ-b, \|coef\| vs locked, median (IQR) | 0.63 (0.56–0.67) | 0.42 (0.36–0.49) | 0.54 (0.48–0.60) | 0.39 (0.32–0.46) |
| Kendall τ within locked top 5, median | 0.60 | 0.50 | 0.60 | 0.60 |
| Top-5 overlap, mean (all 5 identical) | 0.67 (4%) | 0.52 (1.5%) | 0.65 (4%) | 0.52 (2%) |
| Minimum sign agreement over the top 5 | 1.00 | 0.92 | 1.00 | 0.97 |
| Features with sign agreement ≥ 0.9 | 61% | 55% | 68% | 61% |

- **Locked top 5:**
  - grade 4: `rt_start_day`, `previous_brain_tumor`, `idh_unknown`, `rt_started`, `biopsy_before_resection`;
  - all gliomas: `rt_start_day`, `idh_unknown`, `rt_started`, `early_post_rt`, `chemo_started`.
- **Signs vs ranking:** the signs of the leading terms are stable. Their ranking is only moderately stable: the exact
  top 5 recurs in ≤ 4% of refits. Bootstrap refits choose stronger shrinkage, so bootstrap coefficient medians are
  smaller than the locked ones.
- **Group shares of mean |contribution|, locked model:**
  - grade 4: treatment 51%, timing 25%, clinical 24%;
  - all gliomas: 45 / 32 / 23%.
- **LUMIERE refit (shared-feature model, 132 scans, 200 bootstraps):** 9 of 11 shared coefficients keep the MU sign.
  - `early_post_rt` flips: MU −0.06 vs LUMIERE +0.57; 0.5% of bootstraps agree with MU.
  - `log_necrosis_cavity_cc` flips: +0.19 vs −0.31; 13.5% agree.

### Does the system add clinical value? (assessment)
- **Audit value (yes):**
  - It makes every prediction traceable: inputs with source and as-of day, exact additive explanation, interval, model
    card, hashes.
  - It surfaced four problems that the headline AUC hides:
    1. a missingness shortcut (IDH unknown never progresses; ΔAUC −0.023 without it);
    2. the model is essentially a treatment-course model (treatment-only 0.701 ≈ 0.698);
    3. molecular look-ahead at 8 pre-diagnosis scans;
    4. the cause of LUMIERE miscalibration, together with conformal coverage that breaks under shift.
- **Decision value (not shown):**
  - Neither abstention nor any referral rule improves discrimination beyond case mix (P2 not met).
  - Within-phase AUCs are 0.49–0.68.
  - Conformal sets are informative mainly where risk is low anyway (pre-RT {0}), and there they miss every pre-RT
    progression.
  - Calibrated marginal coverage (P1 met) holds internally only.
- **What clinicians receive:** the flags send 58–73% of scans to the clinician. What the system offers is honest
  uncertainty communication, not triage that saves effort.

### How to re-run every number
```bash
scripts/11_audit_system.sh            # = uv run --frozen --no-sync python -m prism audit --workers 24 (~2 min)
```
- **Inputs:** `outputs/data/{mu_cohort,mu_index,folds,lumiere_cohort}.csv`, `outputs/results/c3/<pop>/{results.csv,oof_repeats.csv.gz}`
  (for the reproduction check and the card) and `outputs/results/analyses/utility/calibration.csv`.
  - These come from `scripts/01_prepare_data.sh`, `05_c3_radiomics.sh` and `10_analyses.sh utility`.
- **Code:** `prism/audit/{model,conformal,record,provenance}.py` and `prism/analyses/audit_system.py`.
- **Seeds are fixed:**
  - conformal split: 10·repeat + fold;
  - bootstrap refits: 1000·repeat + fold;
  - references: 0 and 1;
  - P2 bootstrap: 10000+.
  - A re-run reproduces every table exactly.
- **`MANIFEST.json`:** sha256 of inputs, code and outputs; git state; Python and package versions (uv.lock vs
  installed); command line.
