# CLEAR checklist (CheckList for EvaluAtion of Radiomics research)

Source: Kocak B, Baessler B, Bakas S, et al. CheckList for EvaluAtion of Radiomics research (CLEAR): a step-by-step reporting
guideline for authors and reviewers endorsed by ESR and EuSoMII. *Insights Imaging* 2023;14:75. doi:10.1186/s13244-023-01415-8
(CC BY 4.0). Item wording is copied from Table 1 of the full text (Europe PMC PMC10160267, retrieved 2026-10-11), which is
also the checklist linked from the EQUATOR Network page. [n/e] = not essential (as marked in the source). The source asks for
Yes / No / n/a and a page number for each item.

Radiomics here is a comparator arm: the study tests whether radiomics adds to a clinical + timing + treatment baseline
(`docs/results/C3_radiomics.md`). "Where addressed" points to the repository file that holds the content now. The manuscript
does not exist yet. **TODO** = not addressed anywhere yet.

| No | Section | Item | Where addressed |
|---|---|---|---|
| 1 | Title | Relevant title, specifying the radiomic methodology | TODO (draft title in `docs/MANUSCRIPT_ONE_WEEK_PLAN.md` §7) |
| 2 | Abstract | Structured summary with relevant information | TODO |
| 3 | Keywords | Relevant keywords for radiomics | TODO |
| 4 | Introduction | Scientific or clinical background | Partly: `docs/literature/RELATED_WORK.md`, `docs/manuscript/LITERATURE_TABLE.md` |
| 5 | Introduction | Rationale for using a radiomic approach | TODO (rationale: test the added value claimed by the PRISM report model and Christodoulou 2026) |
| 6 | Introduction | Study objective(s) | Partly: `docs/MANUSCRIPT_ONE_WEEK_PLAN.md` §0 |
| 7 | Method – Study design | Adherence to guidelines or checklists (e.g., CLEAR checklist) | This file and `CHECKLIST_TRIPOD_AI.md` |
| 8 | Method – Study design | Ethical details (e.g., approval, consent, data protection) | TODO (public de-identified datasets) |
| 9 | Method – Study design | Sample size calculation | Partly: `prism/analyses/utility.py` (Riley 2020). Write-up TODO |
| 10 | Method – Study design | Study nature (e.g., retrospective, prospective) | TODO (retrospective, two public cohorts) |
| 11 | Method – Study design | Eligibility criteria | `docs/manuscript/FLOW.md`, `docs/results/FIX_LABELS.md` |
| 12 | Method – Study design | Flowchart for technical pipeline | TODO (pipeline in `scripts/README.md`, `docs/ARCHITECTURE_AND_CONTRIBUTIONS.md`; no figure yet) |
| 13 | Method – Data | Data source (e.g., private, public) | Public: MU-Glioma-Post (TCIA doi:10.7937/7K9K-3C83), LUMIERE (Suter 2022, doi:10.1038/s41597-022-01881-7) |
| 14 | Method – Data | Data overlap | Partly: MU and LUMIERE are separate institutions; BraTS 2024 / MU overlap risk for pretrained encoders noted in `docs/literature/comparison.md` (Table B note) and `docs/results/DEEP_FEATURES.md`. Write-up TODO |
| 15 | Method – Data | Data split methodology | `docs/results/FIX_EVALUATION.md` (5 × 5 patient-grouped stratified CV, nested); `docs/results/SPLIT_VARIANCE.md` (single-split variance) |
| 16 | Method – Data | Imaging protocol (i.e., image acquisition and processing) | Partly: LUMIERE field strength in `TABLE1_COHORT.md`; MU acquisition metadata not distributed. TODO: cite the dataset papers' protocols and pre-processing |
| 17 | Method – Data | Definition of non-radiomic predictor variables | `prism/features/tabular.py`, `docs/results/FIX_TREATMENT_ASOF.md` |
| 18 | Method – Data | Definition of the reference standard (i.e., outcome variable) | `docs/results/FIX_LABELS.md`, `docs/results/C1_endpoint.md` |
| 19 | Method – Segmentation | Segmentation strategy | Partly: MU masks distributed with the dataset (labels 1–4, mapping verified in `prism/config.py`); LUMIERE DeepBraTumIA (`prism/data/lumiere.py`). TODO: cite how MU masks were made |
| 20 | Method – Segmentation | Details of operators performing segmentation | TODO (from the MU dataset paper; LUMIERE automatic) |
| 21 | Method – Pre-processing | Image pre-processing details | `prism/features/radiomics.py` docstring (whole-brain z-score; no second N4), `docs/results/FIX_FEATURES.md` |
| 22 | Method – Pre-processing | Resampling method and its parameters | TODO (state resampling settings from `prism/features/radiomics.py`) |
| 23 | Method – Pre-processing | Discretization method and its parameters | `prism/features/radiomics.py` (fixed bin count 32; limitation vs IBSI fixed bin width noted); legacy binWidth 25 |
| 24 | Method – Pre-processing | Image types (e.g., original, filtered, transformed) | TODO (list image types from `prism/features/radiomics.py`) |
| 25 | Method – Feature extraction | Feature extraction method | `prism/features/radiomics.py` (PyRadiomics) |
| 26 | Method – Feature extraction | Feature classes | Partly: `prism/features/radiomics.py`; write-up TODO |
| 27 | Method – Feature extraction | Number of features | Partly: 2,316 corrected columns (1,116 with an eroded-ROI pass), `prism/features/radiomics.py` docstring |
| 28 | Method – Feature extraction | Default configuration statement for remaining parameters | TODO |
| 29 | Method – Data preparation | Handling of missing data | In-fold imputation (`prism/features/tabular.py`, `docs/results/FIX_LABELS.md` rule 6) |
| 30 | Method – Data preparation | Details of class imbalance | TODO (report prevalence: 100/256 labelled scans positive at 120 d in MU, 47/123 in LUMIERE, `TABLE1_COHORT.md`; no rebalancing) |
| 31 | Method – Data preparation | Details of segmentation reliability analysis | Partly: eroded-ROI perturbation ICC filter (`prism/features/radiomics.py`, `docs/results/C3_radiomics.md`); no inter-reader analysis |
| 32 | Method – Data preparation | Feature scaling details (e.g., normalization, standardization) | In-fold standardisation (`prism/features/tabular.py` pipelines, `docs/results/C3_radiomics.md`) |
| 33 | Method – Data preparation | Dimension reduction details | `docs/results/C3_radiomics.md` (ICC filter; top10 / top30 univariate, L1, PCA-10, decorrelation + top20) |
| 34 | Method – Modeling | Algorithm details | `docs/results/C3_radiomics.md` (ridge, boosting), `prism/experiments/c3_radiomics.py` |
| 35 | Method – Modeling | Training and tuning details | `docs/results/FIX_EVALUATION.md` (nested tuning), `prism/analyses/baselines.py` (nested grid) |
| 36 | Method – Modeling | Handling of confounders | Partly: schedule coupling (`prism/analyses/schedule.py`), post-RT window sensitivity (`prism/analyses/sensitivity.py`). Write-up TODO |
| 37 | Method – Modeling | Model selection strategy | `docs/results/C3_radiomics.md`, `outputs/results/c3/<population>/nested_choices.csv` |
| 38 | Method – Evaluation | Testing technique (e.g., internal, external) | `docs/results/FIX_EVALUATION.md` (internal), `docs/results/EXTERNAL_LUMIERE.md` (external, locked) |
| 39 | Method – Evaluation | Performance metrics and rationale for choosing | `docs/results/FIX_EVALUATION.md`, `prism/models/metrics.py` |
| 40 | Method – Evaluation | Uncertainty evaluation and measures (e.g., confidence intervals) | Patient-cluster bootstrap CIs (`prism/models/metrics.py`, `docs/results/FIX_EVALUATION.md`) |
| 41 | Method – Evaluation | Statistical performance comparison (e.g., DeLong's test) | Paired patient-cluster bootstrap ΔAUC; patient-level permutation control (`docs/results/FIX_EVALUATION.md`) |
| 42 | Method – Evaluation | Comparison with non-radiomic and combined methods | `docs/results/C3_radiomics.md`, `docs/results/IMAGING_VS_NONIMAGING.md`, `prism/analyses/baselines.py` |
| 43 | Method – Evaluation | Interpretability and explainability methods | TODO |
| 44 | Results | Baseline demographic and clinical characteristics | `docs/manuscript/TABLE1_COHORT.md` |
| 45 | Results | Flowchart for eligibility criteria | `docs/manuscript/FLOW.md`, `cohort_flow.png` |
| 46 | Results | Feature statistics (e.g., reproducibility, feature selection) | Partly: `outputs/results/c3/<population>/nested_choices.csv`; ICC distribution TODO |
| 47 | Results | Model performance evaluation | `docs/results/C3_radiomics.md`, `docs/results/EXTERNAL_LUMIERE.md`, `docs/results/SPLIT_VARIANCE.md` |
| 48 | Results | Comparison with non-radiomic and combined approaches | `docs/results/IMAGING_VS_NONIMAGING.md`, `docs/results/C3_radiomics.md` |
| 49 | Discussion | Overview of important findings | TODO |
| 50 | Discussion | Previous works with differences from the current study | Partly: `docs/manuscript/LITERATURE_TABLE.md` |
| 51 | Discussion | Practical implications | TODO |
| 52 | Discussion | Strengths and limitations (e.g., bias and generalizability issues) | TODO (inputs: `FIX_FEATURES.md` known limitations, `FIX_LABELS.md` data issues) |
| 53 | Open science – Data availability | Sharing images along with segmentation data [n/e] | Public datasets (images + masks): MU-Glioma-Post TCIA, LUMIERE figshare |
| 54 | Open science – Data availability | Sharing radiomic feature data | TODO (`outputs/features/radiomics.csv` could be released) |
| 55 | Open science – Code availability | Sharing pre-processing scripts or settings | Partly: `prism/features/radiomics.py`; release TODO |
| 56 | Open science – Code availability | Sharing source code for modeling | Partly: this repository (`scripts/run_all.sh`); release TODO |
| 57 | Open science – Model availability | Sharing final model files | TODO |
| 58 | Open science – Model availability | Sharing a ready-to-use system [n/e] | Not planned (n/e) |
