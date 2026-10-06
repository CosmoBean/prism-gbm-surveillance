# PRISM: Current State and Next Steps

Audit date: September 14, 2026  
Inspected baseline commit: `21c154080b09f1185c370896218e9fa6c957449b`  
Scope: local source files, notebook source, metadata, prediction CSVs, and example Markdown reports.

## 1. Overall Assessment

PRISM contains a substantial radiomics development workflow, a retained calibrated model, a fusion prototype, an image-embedding notebook, and a report-generation prototype. The strongest starting point is the calibrated radiomics branch. The existing measurement helpers are also useful for connecting image-derived quantities to reports.

The repository does not yet establish a validated end-to-end clinical surveillance system. The immediate work is to repair evaluation and reporting contracts, recover missing experiment inputs, and evaluate explanations. Additional modeling can proceed on that foundation.

Three corrections should guide the paper:

1. The preferred training entry point predicts progression within **120 days**, using scans before recorded progression. This is a forward-risk endpoint, not contemporaneous RANO progression or pseudoprogression diagnosis.
2. The report's current RANO output is derived from probability changes, not tumor measurements. It cannot support a claim of implemented RANO assessment or an independent AI-versus-RANO comparison.
3. The imaging notebook contains a randomly initialized generic transformer encoder. It is not an implementation of Swin UNETR, despite the folder/notebook naming.

These findings revise assumptions in the earlier planning discussion. This document describes the supplied code rather than relying on the prior report's claims.

## 2. What Is Available

| Component | Present material | Status and reuse decision |
|---|---|---|
| Dataset audit and indexing | `radiomics/radiomics_pipeline/workflows/audit.py`, `build_index.py`, `split_patients.py` | Reuse; recover generated manifests and reconcile preprocessing splits with actual training splits |
| Preprocessing | `preprocess.py`, training-side preprocessing, PyRadiomics YAML, shell wrappers | Reuse after locating derivatives and checking geometry/intensity provenance |
| Feature/model development | Approximately 2,025-line `train.py`; logistic regression, LightGBM, RF, SVM search; feature ranking; grouped CV | Substantial implementation; strengthen nesting and freeze evaluation |
| Calibrated model export | `export_calibrated.py`, `model_bundle.pkl`, `metadata.json` | Retained model and metadata exist; checkpoint inference not rerun |
| Predictions | 231 training visits and 84 test visits in CSV files | Usable for artifact reconciliation and baseline metric recalculation |
| Tabular explainability | `LinearExplainer` in export; global importance and modality-share CSVs; L1/permutation feature ranking | Reuse and extend to per-case explanations and quantitative stability |
| Measurement helpers | Compartment volumes, enhancing-region bounding-box area, FLAIR intensity, T1c/T1 ratio, cavity-adjacent enhancement fraction | Reuse as measurement infrastructure; audit semantics and geometry before clinical interpretation |
| Image embeddings | One notebook with 4-channel preprocessing and a 48-dimensional encoder | Retain as an explicitly untrained control; embeddings and encoder state are absent locally |
| Fusion model | MLP code, `.pth` weights, 84-row predictions, ROC/confusion-matrix images | Architecture reusable; reported evaluation needs a new split protocol and retraining |
| Report generation | Agent orchestration, GradientExplainer, plots, LLM summary, Markdown-to-DOCX converter | Presentation and orchestration reusable; evidence inputs and validation need repair |
| Example reports | Two Markdown/DOCX reports for one patient, SHAP images, trend image | Examples of output only; not a report-validation cohort |
| Tests | Four measurement tests in `radiomics/tests/test_metrics.py` | Useful start; execution blocked by missing local SimpleITK dependency |
| Packaging | Radiomics requirements, two component READMEs, MIT license | No root usage guide, shared configuration, complete environment, or CI found |
| Second dataset | No CFB-GBM data, adapter, manifest, or results found in this checkout | Planned work; possession elsewhere remains possible |

Source navigation: [radiomics README](../radiomics/README.md), [training CLI](../radiomics/radiomics_pipeline/main.py), [training workflow](../radiomics/radiomics_pipeline/workflows/train.py), [export workflow](../radiomics/radiomics_pipeline/workflows/export_calibrated.py), [fusion](../MLPFusion/fusion_mlp.py), [agent](../glioma_agent/src/agent_pipeline.py), [notebook](../SWIN%20UNetR/swinunetr-pipeline-kaggle.ipynb).

## 3. Data and Artifact Inventory

| Artifact | Verified content |
|---|---|
| `glioma_agent/data/train_predictions.csv` | 231 visits, 127 unique patients; 77 positive and 154 negative labels |
| `radiomics/models/calibrated/test_predictions.csv` | 84 visits, 30 unique patients; 22 positive and 62 negative labels |
| Training/test patient overlap | Zero across these two supplied CSVs; 157 distinct patients in their union |
| `MLPFusion/unified_fusion_results.csv` | 84 rows with exactly the radiomics test case IDs and labels |
| Fusion upstream scores | Match radiomics calibrated probabilities within rounding error; maximum absolute difference approximately 0.000050 |
| Calibrated metadata | Logistic regression; T1c + FLAIR + hybrid basic clinical features; seed 62; 5 CV folds; threshold 0.4553296661 |
| Feature metadata | 48 selected columns before final preprocessing; exported SHAP CSV contains 46 features. Reconcile the two removed features with the fitted preprocessing state |
| Duplicate files | Fusion source and results under `glioma_agent/models/MLPFusion/` are byte-identical to the corresponding top-level fusion files |

The radiomics README describes a LogReg-32 result, while the retained metadata lists 48 selected columns. This is a provenance discrepancy to resolve before writing methods, not evidence that the retained metrics are wrong.

Missing locally: raw MRI, preprocessed MRI/masks, clinical workbook, experiment index, full radiomics feature table, original train/test patient lists, optimization trial results, embedding files, encoder checkpoint, and complete run configuration. The README links to processed data on Hugging Face, but that remote material was not downloaded or verified in this audit.

The fusion checkpoint exists at `MLPFusion/best_fusion_model.pth`; the agent expects it at `glioma_agent/models/MLPFusion/best_fusion_model.pth`, where it is absent. The agent also expects `glioma_agent/data/embeddings_all/`, which is absent. The top-level fusion script expects prediction files and an `embeddings/` directory relative to its working directory; those are not supplied in that layout.

## 4. Results Recalculated From Supplied Predictions

These are arithmetic checks of existing exports, not fresh model inference or independent validation. Fusion probabilities were exported to four decimal places.

| Metric | Calibrated radiomics | Fusion |
|---|---:|---:|
| Visits | 84 | 84 |
| AUROC | 0.8043 | 0.8006 |
| Brier score, lower is better | 0.1542 | 0.1732 |
| Threshold | 0.45533 | 0.48 |
| Accuracy | 0.8095 | 0.8095 |
| Sensitivity | 0.5455 | 0.6818 |
| Specificity | 0.9032 | 0.8548 |
| Macro F1 | 0.7375 | 0.7605 |
| True positives / false negatives | 12 / 10 | 15 / 7 |
| True negatives / false positives | 56 / 6 | 53 / 9 |

Fusion trades three fewer missed positives for three more false positives at the selected operating points. These thresholds differ, so this does not establish a superior model. Compare sensitivity at matched specificity, paired confidence intervals, and calibration after repairing the fusion evaluation.

The supplied fusion CSV does not reproduce the earlier discussion's macro F1 of 0.7683 or recall of 76.05%. Preserve those as historical claims pending recovery of their source run; use the table above for this checkout.

## 5. Findings That Change the Next Steps

### Priority 0: Evaluation and Clinical Meaning

**A. Fusion chooses its checkpoint using test-set loss.**

`MLPFusion/fusion_mlp.py:153-188` repeatedly evaluates the test loader during training and saves the best test-loss checkpoint; the same test loader is used for final evaluation. This is direct test-set reuse in model selection. The supplied fusion metrics should be treated as development results. Introduce patient-disjoint training, validation, and evaluation roles; select checkpoints and thresholds using validation data only.

**B. The current RANO module substitutes probability for measurement.**

`glioma_agent/src/agent_pipeline.py:113-145` calls a greater-than-25% change in the upstream score a bidimensional change and a greater-than-50% score increase from nadir a new lesion. The model's own score therefore influences both sides of the purported AI/RANO comparison. Connect actual measurements and independent lesion evidence; missing evidence must yield unavailable/partial assessment, not a fabricated measurement.

**C. Forward-risk predictions are described as current disease status.**

`radiomics/radiomics_pipeline/main.py`, function `run_train`, sets `within_window`, 120 days, pre-progression-only, and exclusion after late treatment. `train.py:656-679` defines the label. The report instead says whether progression is supported at the current timepoint. Align report wording with the frozen endpoint. Treat current response assessment and future-risk prediction as separate outputs, and do not call their differing values diagnostic discordance.

**D. Reports can include future visits and outcome labels.**

`agent_pipeline.py:86-99` computes nadir using all available visits; `run_agent` loads and processes all visits before selecting the requested timepoint. Tables and plots include all visits and labels. The saved Timepoint 5 report visibly includes Timepoint 6 and its outcome. Limit inference-facing history to information available as of the requested scan. Retrospective outcomes belong in a separately labeled evaluation view.

**E. Report clinical fields contain hardcoded or incorrectly mapped values.**

`agent_pipeline.py:163-165` uses days from diagnosis as days after radiotherapy. Around lines 557-567, the report prints fixed molecular/grade values. Unknown MGMT code 4 falls into a branch labeled unmethylated; absent steroid/cavity information defaults to zero/false. The Timepoint 5 example simultaneously prints MGMT unknown and assigns a methylation-based score contribution. Replace these with source-linked values and explicit unknown states. The weighted pseudoprogression score has no validation evidence in this checkout; retain only a clearly exploratory confounder checklist until independently evaluated.

### Priority 1: Models and Explanations

**F. The image encoder is misidentified and untrained.**

Notebook code cell 7 uses `Conv3d` patch embedding and four generic `TransformerEncoder` layers, with no shifted-window attention, UNet decoder, or positional encoding visible. It initializes the model and enters evaluation mode without loading trained weights; cell 9 extracts embeddings under `no_grad`. Use it as a random-feature control. A trained imaging comparison requires a compatible architecture/checkpoint and a reproducible local extractor; a Swin UNETR checkpoint cannot simply be assumed compatible with this architecture.

**G. SHAP exists, but its scope needs correction and evaluation.**

The radiomics export uses `shap.LinearExplainer(final_model, transformed_train)` and summarizes held-out attributions. For logistic regression, this describes the base linear model output in log-odds, not the final calibrated probability. The main training workflow only exports SHAP for LightGBM, while the export workflow unconditionally assumes a linear model. Model-specific explanation dispatch is needed because the CLI searches multiple model families.

The agent's GradientExplainer wraps the sigmoid fusion output, but its background pairs the first 20 sorted embedding files with **zero upstream scores** (`agent_pipeline.py:260-268`). No training-only membership filter is visible. Replace this with matched embedding/score pairs from the proper training fold. This background construction can distort the apparent branch contributions.

The agent labels the upstream score "Clinically Validated" and latent coordinates "Novel Signal" using a lookup, not validation. Rename these as model score and latent image features. Add output-space checks, baseline values, local explanations, reproducible background IDs, stability analyses, and branch-ablation comparisons. Do not interpret latent-coordinate attribution as a named biological mechanism.

**H. Radiomics CV is grouped, but feature selection is not fully nested.**

`rank_features` fits an initial filter across the training partition, uses fold labels for ranking, then `optimize_models` and `fit_oof_predictions` reuse selected columns. This preserves the separate test partition but makes the internal CV/OOF path conditional on selection using the broader training cohort. Move ranking and selection inside the appropriate inner folds for unbiased model comparisons and stacking inputs. Calibration is fitted on training OOF scores, which is a useful existing foundation; its reported training fit is not an independent calibration evaluation.

**I. Confidence intervals resample visits rather than patients.**

`train.py:1581-1592` bootstraps individual rows despite repeated visits. Replace this with patient-cluster resampling. Report paired model differences and specify whether aggregate results weight visits or patients equally.

**J. The existing upstream training predictions have unverified provenance.**

The file is present, but the inspected workflow/export code does not establish how that particular training CSV was generated. Recover its generating command and whether each score was out-of-fold. Fusion training should consume cross-fitted component scores; do not assume the filename proves this.

### Priority 2: Measurement, Packaging, and Coverage

- The bidimensional helper uses the largest axis-aligned slice bounding-box area across the enhancing mask (`radiomics_tools/metrics/geometry.py`). Disconnected lesions can be enclosed together. It is an engineered burden feature, not demonstrated clinical target-lesion measurement. Validate or rename before integrating it into response criteria.
- `WHOLE_TUMOR_LABELS` includes resection cavity label 4, whereas predictive union masks exclude it. Define cavity-inclusive burden separately from tumor burden and align variable names, report text, and tests.
- Native geometry is preserved in preprocessing; helper image loading does not establish complete spatial consistency across modalities. Add shape, spacing, origin, direction, and alignment checks before combining arrays.
- Intensity preprocessing differs between the radiomics and embedding paths. Record which inputs were fed to each branch; assess the appropriateness of the radiomics bin width of 25 after normalization.
- Nonprogressor labels are assigned zero without a follow-up adequacy check in `label_for_case`. Verify at least the chosen horizon of follow-up or define censoring exclusions before claiming 120-day prediction.
- The standalone `within_window` label mode permits negative time-to-progression values unless combined with pre-progression filtering. The preferred wrapper supplies that filter; make the contract explicit and test it.
- Fusion's focal-loss `alpha` multiplies both classes equally, despite its comment claiming positive-class weighting. Correct the implementation or description and compare against a simple weighted BCE baseline.
- Filtering missing fusion probabilities before plotting shifts their alignment with visit IDs; missing current embeddings can also cause formatting failure. Preserve keyed records and explicit missing-output behavior.
- LLM generation has prompts and a renderer, but no post-generation factual checker, schema validation, measured unsupported-claim rate, or fallback report implementation was found.
- A sigmoid output above 0.75 is labeled high confidence and agreement triggers definitive wording. No fusion calibration or confidence validation was found to support these statements.

## 6. Explainability Workstream

| Layer | Reuse now | Add next | Completion evidence |
|---|---|---|---|
| Named radiomics/clinical features | Linear SHAP and selected feature metadata | Per-case signed values, baseline, feature units, global beeswarm and local waterfall | Numeric attribution artifacts tied to held-out model/fold |
| Calibrated prediction | Existing classifier + calibrator | Explicitly explain base log-odds or the complete calibrated callable; label the distinction | Additivity/approximation check in the claimed output space |
| Feature families | Existing global modality sums | Patient-weighted summaries; correlation groups; background and seed sensitivity | Top-k overlap, rank correlation, attribution direction agreement |
| Fusion | GradientExplainer wrapper | Paired training backgrounds; branch-only baselines; branch removal/retraining | Quantitative attribution stability and performance comparisons |
| Image evidence | Notebook ROI preprocessing | Trained encoder, compatible spatial attribution, occlusion and model-dependence checks | Robustness and failure examples, not just heatmaps |
| Clinical report | Existing SHAP table/plots | Source-linked local explanations; no causal/biomarker novelty claims | Attribution sign, value, output-unit, and wording fidelity tests |

The retained global SHAP shares are approximately T1c 55.9%, FLAIR 31.1%, and clinical features 13.0%. These are normalized sums of mean absolute base-model attributions, not percentages of biological importance or independent modality benefit. Correlation, feature count, and the explained population affect them.

## 7. Ordered 7-14 Day Execution Backlog

### Days 1-2: Recover and Freeze

- [ ] Locate the processed dataset, workbook, full feature table, split lists, embeddings, and source experiment folder referenced by metadata.
- [ ] Recover the command and provenance for seed 62, selected columns, and the upstream training predictions.
- [ ] Establish one environment for the radiomics/measurement tests and a pinned environment for imaging/fusion/report execution.
- [ ] Write the endpoint contract: 120-day forward risk, available inputs, eligible diagnosis, index date, follow-up/censoring, and exclusions.
- [ ] Preserve the original outputs as historical development artifacts. Do not relabel previously inspected test data as untouched.
- [ ] Define a patient-grouped nested evaluation and export fold membership. Add overlap, duplicate-ID, and future-input checks.

Done when: original artifact provenance is documented, inputs are located, the measurement tests run, and the next experiment's cohort/splits are frozen.

### Days 3-4: Repair Comparisons and Begin SHAP

- [ ] Move supervised selection inside training folds; generate cross-fitted upstream predictions for fusion.
- [ ] Refit compact clinical/volume, radiomics logistic, and existing hybrid baselines on common splits.
- [ ] Give fusion a patient-disjoint validation set for checkpoints; keep evaluation labels out of selection.
- [ ] Fit calibration and thresholds within training/validation partitions; compute patient-cluster intervals.
- [ ] Export local linear SHAP for held-out samples and document its log-odds output space.

Done when: every prediction has model/fold provenance and the first comparable performance and SHAP tables are generated.

### Days 5-7: Build the Defensible Report Path

- [ ] Truncate history at the requested scan; keep outcome labels outside inference/report inputs.
- [ ] Connect compartment measurements; preserve unavailable measurements and clinical fields.
- [ ] Replace probability-proxy RANO with a scoped, measurement-based module and explicit unevaluable states.
- [ ] Separate 120-day risk wording from current response status; remove unsupported confidence and clinical-validation labels.
- [ ] Add a structured evidence record, deterministic report baseline, generated-report checks, and fallback behavior.
- [ ] Evaluate SHAP background sensitivity and local stability; select examples by a documented rule including errors.

Done when: an end-to-end case report is generated entirely from traceable as-of-time inputs, plus an internal evaluation table for prediction, explanation, and report fidelity.

### Days 8-10: Imaging and External Compatibility

- [ ] Retain the random encoder as a control and add one compatible trained encoder with checkpoint provenance.
- [ ] Evaluate imaging-only and fusion contributions, spatial explanations, missing inputs, and segmentation/acquisition sensitivity.
- [ ] Inventory the second dataset and map diagnosis, timing, features, masks, and labels before transferring the frozen pipeline.
- [ ] Use the second dataset for external endpoint evaluation only if inputs and reference standards match; otherwise identify the narrower supported analysis.

Done when: the imaging branch has an honest comparator and the external evaluation scope is demonstrated, not presumed.

### Days 11-14: Paper Evidence and Reproducibility

- [ ] Consolidate paired model comparisons, explanation stability, report-error ablations, and failure cases.
- [ ] Conduct blinded report review if a clinical reviewer is available; otherwise restrict conclusions to technical fidelity.
- [ ] Verify closest literature for the actual endpoint and contribution; attach primary-source links and a comparison matrix.
- [ ] Write methods/results from retained configurations and machine-generated result tables.
- [ ] Recreate figures and tables in a clean run; add root instructions, a data manifest template, and a limitations/claims checklist.

Done when: another researcher can recreate the evaluated outputs and each manuscript claim maps to an experiment or documented implementation.

## 8. Immediate Inputs to Recover

| Needed input | Why it is needed |
|---|---|
| Preprocessed data root and experiment index | Run existing features/models without repeating completed preprocessing |
| Original clinical workbook/codebook | Validate endpoint, follow-up, diagnosis eligibility, treatment dates, molecular codes |
| Seed-62 results folder | Resolve selected-feature count, split selection, hyperparameters, and original metrics |
| Training prediction generation command | Determine whether fusion inputs are out-of-fold |
| Embedding directory and encoder state/provenance | Reproduce old fusion and distinguish random versus trained embeddings |
| Any newer report/measurement/checker code | The supplied agent does not contain the stronger report implementation described earlier |
| Second-dataset location/version | Plan its supported role after primary-cohort evaluation is frozen |

## 9. Audit Verification and Limits

- Parsed all 34 Python source files successfully with the standard-library AST parser. This establishes syntax only.
- Parsed notebook JSON and inspected its code cells. Did not execute Google Drive authentication, downloads, or uploads.
- Recomputed AUROC using positive-negative pair comparisons, Brier score, confusion counts, accuracy, sensitivity, specificity, and macro F1 from the stored CSVs using the Python standard library.
- Checked patient overlap, fusion/radiomics case-label alignment, upstream score rounding, and duplicate source/results equality.
- Attempted `python3 -m unittest discover -s tests -v` from `radiomics/`. Collection failed because the active Python 3.13 environment lacks `SimpleITK`; the four tests did not execute. This is an environment blocker, not a demonstrated test assertion failure.
- Did not load pickle/checkpoint objects, rerun preprocessing/training/inference, call the LLM API, validate MRI geometry, or verify external literature/dataset contents in this audit.
- Root source files and historical artifacts were left unchanged. This document is the audit deliverable.

The recommended first implementation step is to recover the existing radiomics experiment inputs and establish the shared evaluation contract. That unlocks trustworthy SHAP, fusion comparisons, and clinical-report integration without discarding the work already completed.
