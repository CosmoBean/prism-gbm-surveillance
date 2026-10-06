# Action Items: Reproduce First, Then Improve

Created: 2026-09-26. Companion to [PUBLICATION_PLAN.md](PUBLICATION_PLAN.md) and [CURRENT_STATE_AND_NEXT_STEPS.md](CURRENT_STATE_AND_NEXT_STEPS.md).

Rule for this phase: **no new modeling ideas until Stage 1 is done.** Each item has a "done when" so progress is unambiguous.

---

## Stage 1 — Reproduce the existing radiomics result exactly (about 1 week)

Only the calibrated radiomics model is reproduced. The fusion model and the random encoder are frozen as historical artifacts and are not re-run.

- [ ] **1.1 Environment.** Create `radiomics/.venv` from `requirements.txt` (Python 3.11; PyRadiomics 3.0.1 does not build cleanly on 3.13). Run `python -m unittest discover -s tests`.
  *Done when:* all 4 metric tests pass. The test failure found in the audit was only a missing SimpleITK.
- [ ] **1.2 Recover the original run folder** `/project/community/sbandred/radiomics/results/repeated_forward_hybrid_basic_corrected/` from the cluster. Include **all seeds**, not just `seed_62`.
  *Done when:* the folder is archived (read-only) with a checksum list.
- [ ] **1.3 Record how seed 62 was chosen.**
  - The test split is drawn at random from the seed (`train.py:893`, `split_search_iters` loop that matches target counts of 30 patients / 96 scans).
  - The manifest's own `split` column is not used; only 3 of the 30 model-test patients are in the manifest's test split.
  - Tabulate held-out AUC for **every** seed in the repeated run.
  *Done when:* there is a table of seed → test AUC, with mean, SD and range. If 62 was the best seed, the honest result is the mean across seeds, not 0.804.
- [ ] **1.4 Pin the inputs.**
  - Download the Hugging Face derivatives (`sbandred/mu-glioma-post-processed`: `manifests/`, `postoperative_progression_surveillance/features/`).
  - Download the TCIA clinical workbook version actually used (`MU-Glioma-Post_ClinicalData-July2025.xlsx`?).
  - Store SHA256 hashes in `docs/data_manifest.md`.
  *Done when:* a fresh clone plus these downloads is enough to train.
- [ ] **1.5 Re-run the exact command** (`python main.py train --seed 62`, with the flags recovered from the run folder's summary). Diff against `models/calibrated/`: selected columns, threshold, and per-row `calibrated_probability`.
  *Done when:* AUC is 0.8043 ± 0.001 and per-scan probabilities match to 1e-3, or every mismatch is explained.
- [ ] **1.6 Tag the commit** `v0-historical-baseline`. Everything after this tag counts as "improvement".

## Stage 2 — Fix the data layer (about 1–2 weeks)

Do this before training any new models. Every item here changes labels or features.

- [ ] **2.1 Cohort builder + flow diagram.**
  - Build one script that goes from 594 scans to the eligible index scans, logging the count removed at each rule: no mask, post-progression, after late treatment, missing MRI day, censored.
  - *Done when:* `cohort.csv` and a flow-diagram table can be regenerated with one command.
- [ ] **2.2 Censoring rule.**
  - A negative requires follow-up ≥ H days after the scan. Use last contact or `clinical_number_of_days_from_diagnosis_to_death_days`; locate the last-contact field in the workbook.
  - Scans without adequate follow-up are excluded and counted.
  - *Done when:* the negative-scan count and the excluded-scan count are reported for H = 90 / 120 / 180 days.
- [ ] **2.3 Reconcile timepoint ↔ clinical-day mismatches.**
  - 6 patients disagree between imaging folders and workbook MRI-day columns: 0006, 0007, 0210, 0220, 0258, 0261 (from `clinical_alignment_report.csv`).
  - Also flag records like `PatientID_0004` (scan on the progression day, patient marked non-progressor).
  - *Done when:* each case is either fixed with a documented reason or excluded.
- [ ] **2.4 Clinical codebook.**
  - Map every categorical code to a named level using the TCIA codebook, with an explicit `unknown`. Confirm what codes 2 and 4 mean for IDH, ATRX, MGMT and 1p/19q.
  - Report the missingness rate by label.
  - *Done when:* no model input is a raw numeric code.
- [ ] **2.5 Timing variables.**
  - Days since RT end, computed from `..._radiation_therapy_end_date`.
  - A ≤12-week post-RT flag.
  - Visit index.
  - These are used as **audit and stratification variables**, not silently as predictors.
- [ ] **2.6 Acquisition metadata.** Per scan: scanner model, field strength, and 2D vs 3D acquisition for T1c and FLAIR, taken from the TCIA metadata / DICOM headers or the data descriptor tables.
  - *Done when:* there is a column per scan, used later for the bias audit.
- [ ] **2.7 Confirm the discretization bug, then fix it.**
  - For about 20 ROIs, count the distinct gray levels after the current z-score (inside the lesion) followed by `binWidth: 25`.
  - If it is ≤ 3, switch to brain-mask z-score or WhiteStripe with a **fixed bin count** (32 or 64).
  - Drop the second N4 pass: FeTS already applied N4.
  - *Done when:* there is a before/after gray-level count table and the feature table has been re-extracted.
- [ ] **2.8 Measurement table.**
  - Per scan: ET / NETC / SNFH / RC volumes (cc), plus deltas from the prior scan and from nadir, using **only earlier scans**.
  - Fix the whole-tumor label definition, which currently includes the cavity (see audit, Priority 2).
  - *Done when:* unit tests cover nadir-uses-past-only and the cavity exclusion.
- [ ] **2.9 Splits.**
  - Stop using a single random 30-patient hold-out.
  - Generate **repeated (e.g. 5×) patient-grouped nested CV** over all eligible MU patients, stratified by outcome and GBM status. Commit the fold IDs.
  - The old 30-patient test set has been used for about 6 configurations (see the radiomics README table), so it is no longer untouched.
  - *Done when:* `folds.csv` is committed and every later model reads it.

## Stage 3 — Re-baseline on the fixed data (about 1 week)

- [ ] **3.1 Evaluation harness.**
  - Metrics: AUROC and AUPRC with patient-clustered bootstrap CIs, calibration (O/E, slope, curve), Brier plus null Brier, and decision curves.
  - Report both visit-weighted and patient-weighted results.
  - One function, used by every model.
- [ ] **3.2 Baselines.** Run all of these on the Stage-2 folds:
  - confounder-only (timing and scanner)
  - clinical-only
  - volume-only
  - RANO-style ≥40% ET rule
  - the **old** radiomics configuration
  - *Done when:* one results table exists. This shows how much of the 0.80 was real, and how much came from volume or timing.
- [ ] **3.3 Re-run the corrected radiomics** (from 2.7) under the same harness.
- [ ] **3.4 Checkpoint meeting.** Decide the primary model (the concept glass-box model is expected) and whether to proceed to the Stage 4 deep features on H100.

## Stage 4 onward

Follow [PUBLICATION_PLAN.md](PUBLICATION_PLAN.md), Parts C–D:
- glass-box concept model
- deep features (H100)
- explanation evaluation
- bias audit
- uncertainty
- locked external validation on LUMIERE (primary) and CFB-GBM (secondary)

Get data access for LUMIERE and CFB-GBM **during** Stage 2, so it is ready by Stage 4.
