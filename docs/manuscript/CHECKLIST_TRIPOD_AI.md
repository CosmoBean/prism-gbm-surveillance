# TRIPOD+AI checklist

Source: Collins GS, Moons KGM, Dhiman P, et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models
that use regression or machine learning methods. *BMJ* 2024;385:e078378. doi:10.1136/bmj-2023-078378 (CC BY 4.0). Item wording
is copied from Table 2 of the full text (Europe PMC PMC11019967, retrieved 2026-10-11). D = development, E = evaluation.
Footnote markers in the original (†, ‡, §, ¶) are omitted.

This study does both: development on MU-Glioma-Post with repeated grouped CV (D) and a locked external evaluation on
LUMIERE (E). "Where addressed" points to the repository file that holds the content now. The manuscript does not exist yet,
so every item still needs a manuscript section. **TODO** = not addressed anywhere yet.

| Item | D/E | Section/topic | Checklist item | Where addressed |
|---|---|---|---|---|
| 1 | D;E | Title | Identify the study as developing or evaluating the performance of a multivariable prediction model, the target population, and the outcome to be predicted | TODO. Draft title in `docs/MANUSCRIPT_ONE_WEEK_PLAN.md` §7 does not yet name "prediction model" development + external evaluation |
| 2 | D;E | Abstract | See TRIPOD+AI for Abstracts checklist | TODO (abstract checklist below) |
| 3a | D;E | Background | Explain the healthcare context (including whether diagnostic or prognostic) and rationale for developing or evaluating the prediction model, including references to existing models | Partly: `docs/literature/RELATED_WORK.md`, `docs/manuscript/LITERATURE_TABLE.md`. Introduction TODO |
| 3b | D;E | Background | Describe the target population and the intended purpose of the prediction model in the context of the care pathway, including its intended users (eg, healthcare professionals, patients, public) | TODO (intended use: risk of progression within 120 d at a surveillance MRI, for neuro-oncology teams) |
| 3c | D;E | Background | Describe any known health inequalities between sociodemographic groups | TODO |
| 4 | D;E | Objectives | Specify the study objectives, including whether the study describes the development or validation of a prediction model (or both) | Partly: `docs/MANUSCRIPT_ONE_WEEK_PLAN.md` §0. Manuscript TODO |
| 5a | D;E | Data | Describe the sources of data separately for the development and evaluation datasets (eg, randomised trial, cohort, routine care or registry data), the rationale for using these data, and representativeness of the data | Partly: `prism/data/mu.py`, `prism/data/lumiere.py` docstrings; dataset DOIs in `docs/literature/comparison.md` §6. Representativeness TODO |
| 5b | D;E | Data | Specify the dates of the collected participant data, including start and end of participant accrual; and, if applicable, end of follow-up | TODO. Both datasets give relative days only; accrual years must be taken from the dataset papers |
| 6a | D;E | Participants | Specify key elements of the study setting (eg, primary care, secondary care, general population) including the number and location of centres | TODO (one centre each: University of Missouri; LUMIERE single centre per Suter 2022) |
| 6b | D;E | Participants | Describe the eligibility criteria for study participants | `docs/manuscript/FLOW.md`, `docs/results/FIX_LABELS.md` |
| 6c | D;E | Participants | Give details of any treatments received, and how they were handled during model development or evaluation, if relevant | `docs/manuscript/TABLE1_COHORT.md`; `docs/results/FIX_TREATMENT_ASOF.md` (as-of-scan treatment features); late-treatment exclusion in `FLOW.md` |
| 7 | D;E | Data preparation | Describe any data pre-processing and quality checking, including whether this was similar across relevant sociodemographic groups | Partly: `docs/results/FIX_FEATURES.md`, `prism/features/radiomics.py`, `docs/results/FIX_LABELS.md` (data error checks). Sociodemographic part TODO |
| 8a | D;E | Outcome | Clearly define the outcome that is being predicted and the time horizon, including how and when assessed, the rationale for choosing this outcome, and whether the method of outcome assessment is consistent across sociodemographic groups | `docs/results/FIX_LABELS.md`, `docs/results/C1_endpoint.md`; sensitivities in `prism/analyses/sensitivity.py`. Sociodemographic consistency TODO |
| 8b | D;E | Outcome | If outcome assessment requires subjective interpretation, describe the qualifications and demographic characteristics of the outcome assessors | TODO (MU: progression from the clinical record, assessor not documented; LUMIERE: expert RANO rating) |
| 8c | D;E | Outcome | Report any actions to blind assessment of the outcome to be predicted | TODO (retrospective public data; no blinding by us) |
| 9a | D | Predictors | Describe the choice of initial predictors (eg, literature, previous models, all available predictors) and any pre-selection of predictors before model building | `docs/results/C2_feature_search.md`, `docs/results/C3_radiomics.md`, `docs/results/IMAGING_VS_NONIMAGING.md` |
| 9b | D;E | Predictors | Clearly define all predictors, including how and when they were measured (and any actions to blind assessment of predictors for the outcome and other predictors) | `prism/features/tabular.py`, `docs/results/FIX_TREATMENT_ASOF.md`, `docs/results/FIX_FEATURES.md`. Predictor dictionary for the supplement TODO |
| 9c | D;E | Predictors | If predictor measurement requires subjective interpretation, describe the qualifications and demographic characteristics of the predictor assessors | TODO (segmentations: MU masks distributed with the dataset; LUMIERE DeepBraTumIA, automatic) |
| 10 | D;E | Sample size | Explain how the study size was arrived at (separately for development and evaluation), and justify that the study size was sufficient to answer the research question. Include details of any sample size calculation | Partly: fixed by the public datasets; Riley 2020 calculation in `prism/analyses/utility.py` (output `outputs/results/analyses/utility/`). Write-up TODO |
| 11 | D;E | Missing data | Describe how missing data were handled. Provide reasons for omitting any data | In-fold imputation with unknown indicators (`prism/features/tabular.py`, `docs/results/FIX_LABELS.md` rule 6); missing counts in `TABLE1_COHORT.md`; exclusions in `FLOW.md` |
| 12a | D | Analytical methods | Describe how the data were used (eg, for development and evaluation of model performance) in the analysis, including whether the data were partitioned, considering any sample size requirements | `docs/results/FIX_EVALUATION.md` (5 × 5 patient-grouped stratified CV, nested selection); `docs/results/EXTERNAL_LUMIERE.md` |
| 12b | D | Analytical methods | Depending on the type of model, describe how predictors were handled in the analyses (functional form, rescaling, transformation, or any standardisation) | `prism/features/tabular.py` (log volumes, in-fold scaling), `docs/results/C3_radiomics.md` |
| 12c | D | Analytical methods | Specify the type of model, rationale, all model building steps, including any hyperparameter tuning, and method for internal validation | `docs/results/C2_feature_search.md`, `docs/results/C3_radiomics.md`, `docs/results/FIX_EVALUATION.md` (nested boosting), `prism/analyses/baselines.py` |
| 12d | D;E | Analytical methods | Describe if and how any heterogeneity in estimates of model parameter values and model performance was handled and quantified across clusters (eg, hospitals, countries). See TRIPOD-Cluster for additional considerations | TODO (one centre per dataset; state that heterogeneity is assessed only as MU vs LUMIERE) |
| 12e | D;E | Analytical methods | Specify all measures and plots used (and their rationale) to evaluate model performance (eg, discrimination, calibration, clinical utility) and, if relevant, to compare multiple models | `docs/results/FIX_EVALUATION.md`, `prism/models/metrics.py` (IPCW AUC/Brier, O/E, slope), `prism/analyses/utility.py` (calibration curves, decision curves, NRI/IDI) |
| 12f | E | Analytical methods | Describe any model updating (eg, recalibration) arising from the model evaluation, either overall or for particular sociodemographic groups or settings | `docs/results/EXTERNAL_LUMIERE.md` (`recalibrated` arm in `outputs/results/external_lumiere/results.csv`) |
| 12g | E | Analytical methods | For model evaluation, describe how the model predictions were calculated (eg, formula, code, object, application programming interface) | `prism/experiments/external_lumiere.py`; `outputs/results/external_lumiere/locked_predictions.csv` |
| 13 | D;E | Class imbalance | If class imbalance methods were used, state why and how this was done, and any subsequent methods to recalibrate the model or the model predictions | TODO: state that none were used (no class weighting or resampling found in `prism/`) |
| 14 | D;E | Fairness | Describe any approaches that were used to address model fairness and their rationale | TODO |
| 15 | D | Model output | Specify the output of the prediction model (eg, probabilities, classification). Provide details and rationale for any classification and how the thresholds were identified | Partly: probabilities, threshold-free metrics; decision curves over 5–50% (`prism/analyses/utility.py`). Write-up TODO |
| 16 | D;E | Training versus evaluation | Identify any differences between the development and evaluation data in healthcare setting, eligibility criteria, outcome, and predictors | `docs/results/EXTERNAL_LUMIERE.md`, `docs/results/FIX_LABELS.md` (LUMIERE section), `TABLE1_COHORT.md` caveats |
| 17 | D;E | Ethical approval | Name the institutional research board or ethics committee that approved the study and describe the participant informed consent or the ethics committee waiver of informed consent | TODO (secondary use of public de-identified datasets; cite their approvals) |
| 18a | D;E | Funding | Give the source of funding and the role of the funders for the present study | TODO |
| 18b | D;E | Conflicts of interest | Declare any conflicts of interest and financial disclosures for all authors | TODO |
| 18c | D;E | Protocol | Indicate where the study protocol can be accessed or state that a protocol was not prepared | TODO (no registered protocol; analysis plan in `docs/MANUSCRIPT_ONE_WEEK_PLAN.md`) |
| 18d | D;E | Registration | Provide registration information for the study, including register name and registration number, or state that the study was not registered | TODO (not registered) |
| 18e | D;E | Data sharing | Provide details of the availability of the study data | Partly: public datasets (MU-Glioma-Post TCIA doi:10.7937/7K9K-3C83; LUMIERE, Suter 2022). Derived tables TODO |
| 18f | D;E | Code sharing | Provide details of the availability of the analytical code | Partly: this repository (`README.md`, `scripts/run_all.sh`). Public release link TODO |
| 19 | D;E | Patient and public involvement | Provide details of any patient and public involvement during the design, conduct, reporting, interpretation, or dissemination of the study or state no involvement | TODO (state none) |
| 20a | D;E | Participants | Describe the flow of participants through the study, including the number of participants with and without the outcome and, if applicable, a summary of the follow-up time. A diagram may be helpful | `docs/manuscript/FLOW.md` + `cohort_flow.png`; outcome counts and follow-up in `TABLE1_COHORT.md` |
| 20b | D;E | Participants | Report the characteristics overall and, where applicable, for each data source or setting, including the key dates, key predictors (including demographics), treatments received, sample size, number of outcome events, follow-up time, and amount of missing data. A table may be helpful. Report any differences across key demographic groups | `docs/manuscript/TABLE1_COHORT.md` (key calendar dates not available; differences across demographic groups TODO) |
| 20c | E | Participants | For model evaluation, show a comparison with the development data of the distribution of important predictors (demographics, predictors, and outcome) | `docs/manuscript/TABLE1_COHORT.md` (MU vs LUMIERE columns) |
| 21 | D;E | Model development | Specify the number of participants and outcome events in each analysis (eg, for model development, hyperparameter tuning, model evaluation) | Partly: `outputs/results/c1/c1_results.csv` (`n_scans`, `n_patients`, `n_pos`, `n_censored`), `TABLE1_COHORT.md`. Per-analysis table TODO |
| 22 | D | Model specification | Provide details of the full prediction model (eg, formula, code, object, application programming interface) to allow predictions in new individuals and to enable third party evaluation and implementation, including any restrictions to access or reuse (eg, freely available, proprietary) | TODO (final-model coefficients / saved object for the baseline ridge) |
| 23a | D;E | Model performance | Report model performance estimates with confidence intervals, including for any key subgroups (eg, sociodemographic). Consider plots to aid presentation | `docs/results/C3_radiomics.md`, `docs/results/EXTERNAL_LUMIERE.md`, `docs/results/IMAGING_VS_NONIMAGING.md`; subgroups grade 4 / all gliomas. Sociodemographic subgroups TODO |
| 23b | D;E | Model performance | If examined, report results of any heterogeneity in model performance across clusters. See TRIPOD-Cluster for additional details | TODO (not examined beyond MU vs LUMIERE; say so) |
| 24 | E | Model updating | Report the results from any model updating, including the updated model and subsequent performance | `docs/results/EXTERNAL_LUMIERE.md` (recalibrated arm) |
| 25 | D;E | Interpretation | Give an overall interpretation of the main results, including issues of fairness in the context of the objectives and previous studies | TODO (draft points in `docs/results/IMAGING_VS_NONIMAGING.md`, `docs/results/SPLIT_VARIANCE.md`) |
| 26 | D;E | Limitations | Discuss any limitations of the study (such as a non-representative sample, sample size, overfitting, missing data) and their effects on any biases, statistical uncertainty, and generalisability | TODO (inputs: `FIX_LABELS.md` data issues, `FIX_FEATURES.md` known limitations, schedule coupling `prism/analyses/schedule.py`) |
| 27a | D | Usability of the model in the context of current care | Describe how poor quality or unavailable input data (eg, predictor values) should be assessed and handled when implementing the prediction model | TODO |
| 27b | D | Usability of the model in the context of current care | Specify whether users will be required to interact in the handling of the input data or use of the model, and what level of expertise is required of users | TODO |
| 27c | D;E | Usability of the model in the context of current care | Discuss any next steps for future research, with a specific view to applicability and generalisability of the model | TODO |

## TRIPOD+AI for Abstracts

Item wording from Table 3 of the same source.

| Item | Section | Checklist item | Where addressed |
|---|---|---|---|
| 1 | Title | Identify the study as developing or evaluating the performance of a multivariable prediction model, the target population, and the outcome to be predicted | TODO |
| 2 | Background | Provide a brief explanation of the healthcare context and rationale for developing or evaluating the performance of all models | TODO |
| 3 | Objectives | Specify the study objectives, including whether the study describes model development, evaluation, or both | TODO |
| 4 | Methods | Describe the sources of data | TODO |
| 5 | Methods | Describe the eligibility criteria and setting where the data were collected | TODO |
| 6 | Methods | Specify the outcome to be predicted by the model, including time horizon of predictions in case of prognostic models | TODO |
| 7 | Methods | Specify the type of model, a summary of the model-building steps, and the method for internal validation | TODO |
| 8 | Methods | Specify the measures used to assess model performance (eg, discrimination, calibration, clinical utility) | TODO |
| 9 | Results | Report the number of participants and outcome events | TODO (numbers in `TABLE1_COHORT.md`) |
| 10 | Results | Summarise the predictors in the final model | TODO |
| 11 | Results | Report model performance estimates (with confidence intervals) | TODO |
| 12 | Discussion | Give an overall interpretation of the main results | TODO |
| 13 | Registration | Give the registration number and name of the registry or repository | TODO |
