# Fault Audit: Procedures Behind the Reported Results

Severity: **High** = changes a reported claim · **Medium** = biases or overstates a number · **Low** = correctness/hygiene.
Evidence was re-checked on 2026-10-05 against the code at `21c1540` and the reference manifests (`sbandred/mu-glioma-post-processed`).

## Summary

| # | Stage | Fault | Severity | Effect on reported results |
|---|---|---|---|---|
| 1 | Agent | "RANO BD product change" and "new lesion" are computed from the radiomics **score**, not measurements | High | Report's RANO section is not RANO; "+71.6% BD change" is a score change |
| 2 | Fusion | Checkpoint selected on **test** loss | High | Test metrics optimistic (≈ +0.01 AUC); test set no longer held out |
| 3 | Fusion | "Improvement" over radiomics is an operating-point shift (radiomics scored at 0.48, not its own 0.455) | High | Recall/F1 gain claim unsupported; fusion AUC 0.8006 < radiomics 0.8043 |
| 4 | Embeddings | "SWIN UNETR" is a 0.1M-param **random, untrained** encoder | High | Image branch has no outcome signal (alone: AUC ≈ 0.50) |
| 5 | Fusion | 0.48 cutoff hand-tuned without validation data; no seeds | Medium | Shipped acc 0.8095 / F1 0.6522 ≈ 95th pct / best of 50 retrains |
| 6 | Agent | Fusion output for demo patient 0019 is **in-sample** (patient is in the fusion training set) | Medium | Demo reports show training-set predictions |
| 7 | Radiomics | Shipped model from a "repeated … seed_62" run; seed also picks the test split; command not in repo | Medium | Possible test-set selection; default `main.py train` gives SVM-32, AUC 0.7977 |
| 8 | Radiomics | Model relies on **undocumented** molecular codes (likely "not tested") | Medium | Learns testing practice: e.g. IDH1=2 progression 0.46 vs 0.77 |
| 9 | Labels | 59/97 never-progressor negatives have < 120 d follow-up (35 are the last record) | Medium | Negatives unverified; label noise (test AUC barely moves when removed) |
| 10 | Evaluation | Bootstrap CI resamples scans, not patients (84 scans / 30 patients) | Medium | CI too narrow; patient-level ≈ [0.66, 0.91] |
| 11 | Radiomics | Feature ranking uses all training labels before CV model search | Low | CV AUCs optimistic (test unaffected) |
| 12 | README | Rows compare different test designs (96 / 84 / 30 scans); "LogReg-32" but bundle has 48 features | Low | Table not comparable row-to-row; label wrong |
| 13 | Labels | `LABEL_MAP` says 1=ET, 3=SNFH; data are 1=NETC, 2=SNFH, 3=ET, 4=RC | Low | Mislabels per-region volume features (not used by shipped model) |
| 14 | Reproducibility | Notebook cell 7 ran 3× before extraction; fusion unseeded; `train_predictions.csv` not produced by any script | Low | Results not regenerable from repo as written |
| 15 | Agent | Molecular profile table is hardcoded placeholder; score described as "LightGBM … EGFR, tumor volumes" | Low | Report content does not match the model (LogReg, no EGFR/volume features) |

## Details and evidence

**1. Agent RANO is a score proxy** — `glioma_agent/src/agent_pipeline.py:116-133`: "Since we don't have raw BD product per timepoint, we use mol_score trajectory"; BD flag = score % change > 25 (`:129`), new-lesion flag = score > 50% above nadir (`:133`). The report then prints "Bidimensional (BD) Product Change … +71.6%" (`:595`). *Fix:* compute BD product from masks (`radiomics_tools/metrics/bidimensional_product.py` exists) or remove the RANO section.

**2–3, 5. Fusion evaluation** — `MLPFusion/fusion_mlp.py:153-189` saves the checkpoint with lowest test loss; `:230-232` applies 0.48 to both fusion and radiomics. 50-seed retrains: test-loss checkpoint median AUC 0.805 vs 0.796 (final epoch) / 0.798 (patient-grouped validation); score-only fusion = 0.8043. *Fix:* select on a patient-grouped validation split, derive thresholds from training data, compare each model at its own threshold, seed runs, report AUC with patient-level CIs.

**4. Embeddings** — notebook cell 7 builds `SwinEncoder3D` (Conv3d + 4 transformer layers) with no weight loading or training; cell 11 lists "load pretrained BraTS21 weights" as future work. Linear probe AUC 0.55 (train CV) / 0.62 (test); PC1 (92% variance) tracks resection-cavity/lesion size. The BraTS-pretrained, fine-tuned SwinUNETR (this project's rebuild) reaches image-only test AUC ≈ 0.64 and still adds nothing significant in fusion.

**6. In-sample demo** — PatientID_0019 is not in the radiomics test split; its rows are in `glioma_agent/data/train_predictions.csv`, the fusion training set.

**7. Seed/split selection** — `radiomics/models/calibrated/metadata.json` `source_result_dir` = `repeated_forward_hybrid_basic_corrected/seed_62`; `train.py:1842` draws test patients from the seed; `main.py` labels 62 the "preferred" seed. *Fix:* report the distribution over seeds/splits, or fix the split before any modelling.

**8. Undocumented codes** — shipped columns include `clin_idh1_mutation__2`, `clin_idh2_mutation__2`, `clin_mgmt_methylation__4`, `clin_atrx_mutation__2`; the data dictionary defines IDH 0/1, MGMT 0–3, ATRX 0–2. Progression rates: IDH2=2 0.57 vs 0.79; MGMT=4 0.59 vs 0.78. Not explained by follow-up length. *Fix:* recode as missing, report sensitivity with/without.

**9. Censoring** — `train.py:660-661` labels every never-progressor scan 0 without requiring ≥ 120 d of observed follow-up. *Fix:* exclude or censor scans without adequate follow-up.

**10. CI** — `train.py:1581-1592` resamples rows. *Fix:* cluster (patient) bootstrap.

**11. Ranking outside CV** — `train.py:1873` ranks on all training rows; `optimize_models` then cross-validates on those rows.

**13. Labels** — BraTS21 SwinUNETR zero-shot: ET output matches MU label 3 (Dice 0.81), not label 1 (0.00).

## What remains valid

- All reported numbers reproduce from the code and raw data (see `FINDINGS.md`).
- The radiomics test-set protocol itself is clean: test touched once, calibration and threshold fit on out-of-fold training predictions, patient-grouped CV.
- Radiomics model has genuine timing signal: AUC 0.73 among progressors only (≤ 120 d vs > 120 d before progression).
