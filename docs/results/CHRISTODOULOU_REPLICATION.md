# Christodoulou 2026 setting, re-implemented on the current MU cohort and folds

Christodoulou RC et al. *Eur J Radiol AI* 2026;5:100074 ("Explainable radiomics with probability calibration for
postoperative glioblastoma surveillance"). Only the abstract was accessible. It reports: conventional radiomics from T1,
T1c, T2 and FLAIR of each post-operative scan (single scan, no change features), about 256 features, LightGBM tuned
with Optuna, Platt calibration, patient-aware 5-fold CV for tuning, one held-out patient test set; label = progression
status of each post-operative scan; test AUC 0.80, Brier 0.093 → 0.088 after calibration.

**Why the earlier "0.64–0.70" is not this study.** `docs/literature/comparison.md` cites "0.64–0.70 (C1)" as our
replication of this setting. C1 (`C1_endpoint.md`, `C1_full_tables.md`) is a ridge on the legacy T1c/FLAIR radiomics
+ clinical, scored on the *forward* 120-day label (grade 4: 0.648–0.684; all gliomas up to 0.744). It is not
LightGBM, not the status/detection label and predates the label fixes (`FIX_LABELS.md`) and the radiomics clipping fix
(`FIX_RADIOMICS_CLIP.md`). The only LightGBM "paper-style" attempt is in `legacy/radiomics/README.md` (LightGBM-64,
radiomics only, PRISM-report split of 30 patients: 0.599), also pre-fix. This document replaces both as the comparison.

## Plan (pre-specified, 2026-10-25, written before any run that reads labels with scores)

**Label and populations** (as in [DETECTION_TASK.md](DETECTION_TASK.md); cohort `outputs/data/detection_cohort.csv`).
- Positive: the progression scan. Training negatives: index scans with a verified 120-day non-event (primary negatives).
- Population: grade 4 (primary), all gliomas (secondary).
- Their label ("progression status of each post-op scan") may also count later post-progression scans as positive; we
  keep the detection label by design (first progression scan only), so the estimand is ours, not a copy of theirs.

**Features.** The v2 radiomics table (`prism.config.RADIOMICS`, the `v2_all4` set of `detection.context`): all four
sequences (T1, T1c, T2, FLAIR), six ROIs (ET, NETC, SNFH, core, lesion, peri-cavity rim), first-order + texture
(2232 columns) + shape (84 columns) = 2316 columns, original image only (no LoG / wavelet filters: a deviation from
their extraction, recorded). Selection to 256 **inside each training set only**: drop columns with > 20% missing or
zero variance on the training rows, then keep the 256 with the largest |univariate AUC − 0.5| on the training rows.
No clinical, timing, volume-change or previous-scan input.

**Learner.** LightGBM 4.6.0 (`n_jobs=1`, parallel over outer fits). Optuna 4.8.0 TPE sampler (seeded), 40 trials,
objective = mean inner AUC over a 5-fold patient-grouped, label-stratified CV of the training rows (their "patient-aware
5-fold CV"). Search space: `num_leaves` 4–31, `max_depth` 2–6, `learning_rate` 0.01–0.2 (log), `n_estimators`
50–500, `min_child_samples` 5–40, `subsample` 0.5–1 (bagging every iteration), `colsample_bytree` 0.2–1,
`reg_lambda` 1e-3–10 (log). Feature selection is redone inside each inner fold (so the inner AUC is honest).
**Platt calibration** fitted inside the training set: logistic regression of the label on the logit of the inner
cross-fitted predictions of the tuned model; the final model is refitted on all training rows and its test logits are
mapped through the Platt fit. No test row is touched by selection, tuning or calibration.

**Evaluation.**
1. *Shared 5 × 5 patient-grouped folds* (`detection.fold_ids`, from `outputs/data/folds.csv`). Plain AUC = mean over
   repeats of the pooled held-out AUC; 95% CI from the paired patient-cluster bootstrap (1,000 draws,
   `detection.evaluate_set`). Brier score before and after Platt (mean over repeats; patient bootstrap CI).
2. *Their design, 100 times*: 100 random single splits holding out about 20% of patients (seeds 0–99, not
   stratified, grade 4), the full pipeline refitted on the remaining patients, test AUC on all held-out detection rows
   (positives + primary negatives, all scans, as in their single test set). Report mean, SD, 2.5–97.5 percentiles,
   range, and the share of splits ≥ 0.80. The timeline baseline B1 (ridge, `c3.fit_predict`) is refitted on the same
   splits as a reference.
3. *PRISM evaluation*: the setting's 5 × 5 OOF predictions evaluated with `detection.eval_sets` / `evaluate_set` in
   the intended use (primary set: grade 4, intended use, primary negatives) and all scans, with within-phase and
   phase-stratified AUCs, beside B1 (timeline + clinical, 0.822), I_scan (0.659) and I_pure (0.709) recomputed on the
   same rows and folds exactly as in DETECTION_TASK.md. Paired contrasts: CH − B1, CH − I_scan, CH − I_pure.
4. *EXPLORATORY*: the locked model (fitted once on all MU grade-4 detection training rows) applied to UCSF grade-4
   scan 2 (primary UCSF label, [UCSF_PLAN.md](UCSF_PLAN.md)), only if the same radiomics can be extracted there in
   < 1 h with the MU extraction code; otherwise skipped and stated.

No decision rule: this is a replication of a published comparator. Reading fixed in advance: their 0.80 is "reproduced"
if the 5 × 5 AUC in grade 4, all scans, has a CI covering 0.80; the 100-split distribution shows how much a single
split can move. Patient-level outputs: `outputs/results/analyses/christodoulou/` (git-ignored).
Code: `prism/analyses/christodoulou_replication.py`.

## Results (run 2026-10-25)

Code: `prism/analyses/christodoulou_replication.py` (`PYTHONPATH=. .venv/bin/python -m prism.analyses.christodoulou_replication
--workers 10`, 8 min on 10 CPUs; `--ucsf` for step 4, 7 min). Outputs (git-ignored):
`outputs/results/analyses/christodoulou/` (auc.csv, contrasts.csv, within_phase.csv, brier.csv, splits.csv,
splits_summary.csv, cv_params.csv, oof_<pop>.csv.gz, locked_model.pkl, locked_params.json, ucsf_locked.csv,
ucsf_radiomics_scan2.csv, PLAN_snapshot.md, run_info.json). Checks: the B1 OOF predictions equal the detection run's
saved ones (asserted, max deviation < 1e-9). B1, I_scan and I_pure reproduce DETECTION_TASK.md to the third decimal.
No labelled scan lacks radiomics. Mean inner (tuning) AUC of the best Optuna trial: 0.64 (range 0.58–0.78).

### (1) and (3): shared 5 × 5 folds, PRISM evaluation sets

CH = the Christodoulou setting (Platt-calibrated; Platt is monotone, so its AUC equals the raw model's).

| evaluation set (grade 4 unless stated) | pos/neg/patients | **CH** | B1 (timeline) | I_scan | I_pure |
|---|---|---|---|---|---|
| **intended use (primary set)** | 62/84/80 | **0.579 (0.499–0.656)** | 0.822 (0.749–0.902) | 0.659 (0.567–0.733) | 0.709 (0.630–0.781) |
| all scans (their population) | 64/117/92 | **0.565 (0.490–0.641)** | 0.845 (0.781–0.906) | 0.657 (0.580–0.731) | 0.712 (0.640–0.781) |
| intended use, secondary negatives | 62/173/88 | 0.568 (0.506–0.633) | 0.807 | 0.599 | 0.655 |
| intended use, later post-RT | 56/32 | 0.558 (0.435–0.674) | 0.638 (0.488–0.799) | 0.655 (0.542–0.755) | 0.650 (0.541–0.742) |
| intended use, phase-stratified | 62/84 | 0.579 (0.467–0.685) | 0.640 (0.508–0.784) | 0.680 (0.573–0.777) | 0.677 (0.580–0.767) |
| all gliomas, intended use | 64/98/87 | 0.584 (0.514–0.656) | 0.814 (0.737–0.888) | 0.692 (0.614–0.769) | 0.747 (0.677–0.812) |
| all gliomas, all scans | 73/156/114 | 0.562 (0.492–0.626) | 0.814 (0.754–0.869) | 0.681 (0.611–0.748) | 0.747 (0.688–0.807) |

Paired contrasts, grade 4, intended use: CH − B1 −0.242 (−0.352 to −0.139), phase-stratified −0.062 (−0.226 to
+0.102); CH − I_scan −0.079 (−0.140 to −0.005), phase-stratified −0.102 (−0.175 to −0.013); CH − I_pure −0.130
(−0.213 to −0.040). Repeat-to-repeat SD of CH's AUC: 0.02. Early post-RT (4/51, descriptive): CH 0.76, I_scan 0.90.

**Brier** (mean over repeats, patient bootstrap; "reference" = predicting the prevalence, p(1 − p)):

| set | prevalence | raw LightGBM | after Platt | Platt − raw | reference |
|---|---|---|---|---|---|
| grade 4, intended use | 0.42 | 0.262 (0.230–0.297) | 0.251 (0.226–0.278) | −0.011 (−0.026 to +0.004) | 0.244 |
| grade 4, all scans | 0.35 | 0.252 (0.225–0.285) | 0.234 (0.213–0.258) | −0.019 (−0.037 to −0.002) | 0.229 |
| grade 4, all scans, secondary negatives | 0.20 | 0.227 (0.206–0.247) | 0.197 (0.184–0.208) | −0.030 (−0.045 to −0.017) | 0.163 |

Platt lowers the Brier score, as in the paper (0.093 → 0.088), but the calibrated model stays worse than predicting
the prevalence in every set. Their 0.09 implies a much lower prevalence of positive scans than our detection rows, so
the absolute values are not comparable.

### (2) Their design, 100 times (grade 4, 18 of 92 patients held out, 23–48 test scans, 9–16 positives)

| metric | mean | SD | 2.5–97.5% | range | share ≥ 0.80 |
|---|---|---|---|---|---|
| **CH test AUC (all scans)** | **0.614** | 0.085 | 0.417–0.768 | 0.374–0.812 | **1%** |
| CH test AUC (intended-use scans) | 0.627 | 0.096 | 0.439–0.828 | 0.318–0.875 | 4% |
| B1 on the same splits (all scans) | 0.852 | 0.070 | 0.713–0.958 | 0.700–1.000 | 72% |
| CH Brier raw → Platt | 0.252 → 0.233 | | | | |

A single 20% patient hold-out moves the AUC by ± 0.17 (95% range). One split in 100 reaches their 0.80.

### (4) EXPLORATORY: locked model on UCSF grade-4 scan 2

Feasible in < 1 h: the MU extraction code (`radiomics.extract_scan`, same normalisation and settings) ran on the 140
UCSF grade-4 scan-2 images (1 mm, 240 × 240 × 155, same label convention) in 7 min. The model was fitted once on all
MU grade-4 detection training rows and applied unchanged.

| UCSF set | pos/neg | AUC (95% CI) | Brier raw / Platt |
|---|---|---|---|
| grade 4, scan 2, primary label | 29/40 | 0.804 (0.692–0.905) | 0.187 / 0.219 |
| verified negatives | 29/33 | 0.863 (0.770–0.942) | 0.163 / 0.224 |
| later post-RT | 27/38 | 0.819 (0.719–0.916) | 0.182 / 0.216 |
| imaging-defined reference (ET increased) | 71/69 | 0.775 (0.700–0.843) | – |

This is the UCSF pattern again ([UCSF_AUDIT.md](UCSF_AUDIT.md)). The CH score tracks enhancing-tumour volume (Spearman
0.67 with log ET volume, which alone reaches 0.88 on the same rows). Within scans whose ET increased (27/10), CH falls to
0.63. Platt (fitted on MU) worsens the Brier score on UCSF.

### Reading

- **Their 0.80 is not reproduced.** Under the shared 5 × 5 folds the setting reaches 0.565 (0.490–0.641) on all
  grade-4 scans and 0.579 (0.499–0.656) in the intended use. Both CIs exclude 0.80, and the lower bounds touch 0.5.
- The 100-split distribution shows how a single split can mislead: 0.61 on average, from 0.37 to 0.81, and 1 in 100
  splits at ≥ 0.80.
- In the intended use it is below the timeline (−0.24) and below the simple image measurements I_scan (−0.08) and
  I_pure (−0.13). Within phase it is 0.56–0.58, also below the image measurements. 2316 radiomic columns, 256 kept
  and a tuned boosted learner, on about 145 training scans, recover less than the handful of volume and intensity measurements of I_scan in
  a ridge. A logistic regression on the same 256 features (sanity check, one repeat, not prespecified) gave 0.64, and ET
  volume alone 0.62. So the shortfall reflects the data size, not a broken pipeline.
- Calibration helps only relative to the uncalibrated booster, never beyond predicting the prevalence.
- On UCSF the same locked model reaches 0.80, but there, as for every image model, the score mostly re-detects
  enhancing-tumour growth on the scan where progression was called.

### Deviations and specification details

- **DEVIATION (features):** original-image PyRadiomics only (no LoG or wavelet filters, which the paper used and the
  v2 table does not contain). The 256 are selected by univariate AUC on the training rows, not by their stability
  ranking (the method is not given in the abstract).
- **DEVIATION (label):** first progression scan versus verified-stable scans (detection label), not the paper's
  "progression status" of every post-operative scan. This is by design (plan).
- **Specification (100 splits):** unstratified draws of 18 of the 92 grade-4 patients with a labelled scan; the full
  pipeline (selection, Optuna, Platt) is redone on each training set; B1 is refitted with `c3.fit_predict`.
- **Added (not prespecified, diagnostic only):** the sanity check above (logistic regression / default LightGBM on
  the same 256, LightGBM on shape only: 0.59–0.64, one repeat, intended use), the reference Brier column, and on UCSF
  the ET-volume correlation and the ET-increased stratum. None changes a number above.
- Optuna 4.8.0 was available, so no grid-search fallback was needed. Nothing was installed.
