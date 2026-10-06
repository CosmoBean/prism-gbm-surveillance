# PRISM → Publication: Critique, Literature Position, and Proposed Explainable & Bias-Audited System

Prepared: 2026-09-26
Target: solid mid-tier journal (e.g., *Computers in Biology and Medicine*, *BMC Medical Imaging*, *Frontiers in Oncology*, *Cancers*, *Journal of Imaging Informatics in Medicine*, *Neuro-Oncology Advances*, *European Journal of Radiology AI*).
Scope: LLM report generation is deferred to future work. The focus is on **explainability, bias, and valid evaluation**.
Companion document: [CURRENT_STATE_AND_NEXT_STEPS.md](CURRENT_STATE_AND_NEXT_STEPS.md), a code-level audit.

> **Citation caveat.** Research agents gathered the literature in this document using web search. Each item was located at abstract level or better. Items marked *(UNVERIFIED)* could not be confirmed. Several 2025–2026 items are preprints. **Read the primary source of every citation before it goes into the manuscript.**

---

## Part A — Critique of the current manuscript

The results problems are covered in the audit: test-set checkpoint selection in fusion, a random image encoder, and a RANO proxy built from model probability. This part covers everything else a reviewer will hit. Items are ordered by how much damage they would do.

### A1. The core claim does not match the task that was modeled

| Paper says | What the code and data actually do | Consequence |
|---|---|---|
| The system distinguishes true progression from pseudoprogression (title, abstract, intro, "Clinical Relevance") | It predicts **clinically documented progression within 120 days of a pre-progression scan**. MU-Glioma-Post has **no pseudoprogression adjudication and no per-timepoint pathology**. Progression comes from EMR/clinical-note review, not RANO. | The central framing is unsupported. Reframe as **forward risk stratification during surveillance**. |
| "Outperforming the molecular-only baseline" | The baseline is the T1c+FLAIR radiomics model. Only about 13% of its SHAP mass is clinical. | The baseline is mislabeled, so the comparison is meaningless as stated. |
| Imaging and molecular data are "complementary rather than redundant" | Fusion probability correlates r = 0.989 with the radiomics probability. The paired patient-bootstrap ΔAUC CI is (−0.03, +0.016). | The claim is contradicted by the paper's own outputs. |
| "Feasibility for clinical deployment", "reliable discrimination" | 30 test patients, 14 of them with a positive scan. AUC 95% CI is 0.67–0.91. Sensitivity is 55% at the reported threshold. | Overclaiming. Reviewers read this as naïveté. |
| RANO 2.0 implemented with Criteria A/B/C | The code uses percentage change in the model's own probability. The paper also cites RANO 2010 (Wen 2010), not RANO 2.0 (Wen 2023, JCO, doi:10.1200/JCO.23.01059). | Methods do not describe the code. That is an integrity problem, not a style problem. |

### A2. Internal contradictions (reviewers catch these in minutes)

1. **Encoder training state.** Methods say "BraTS-pretrained Swin UNETR … fine-tuned on the study cohort". Limitations say "initialized with random weights … not fine-tuned". The code is a generic `nn.TransformerEncoder`: no shifted windows, no UNETR decoder, no pretrained weights.
2. **Class balance.**
   - The paper says progressors are the majority (3:1).
   - The modeled scan-level data is the reverse: 77 positive / 154 negative in training and 22 / 62 in test.
   - Focal loss is justified as up-weighting "the minority progression cases", which contradicts the 3:1 claim.
   - Separately, the focal-loss `alpha` in `fusion_mlp.py` weights both classes equally.
3. **Clinical features.**
   - The paper says the 6 clinical features are "age, sex, IDH1, MGMT, TERT".
   - `metadata.json` lists `idh1__2, atrx__0, idh2__2, mgmt__4, atrx__2, 1p_19q__1`. There is no age, no sex and no TERT.
   - Codes 2 and 4 appear to be **"unknown / not tested"** categories; the audit identified MGMT code 4 as unknown. Confirm against the codebook.
   - If confirmed, the model uses **whether a test was done** as a predictor. That is a classic missingness shortcut and a bias issue.
4. **Fusion results.** Macro-F1 0.7683 and recall 76.05% in the paper cannot be reproduced from `unified_fusion_results.csv`, which gives 0.7605 and 68.2%.
5. **Metric equality.** The abstract headlines fusion AUC 0.80 and accuracy 80.95%. The radiomics model has identical accuracy (80.95%) and a *higher* AUC (0.804).

### A3. Methodological problems in each component (beyond those in the audit)

**Radiomics branch (your strongest asset, but it has a serious preprocessing flaw)**
- **Degenerate gray-level discretization.**
  - `preprocess_image` (`train.py:743`) z-scores each image **using the mean and SD inside the tumor mask**.
  - PyRadiomics then runs with `binWidth: 25` and `normalize: false`.
  - Z-scored lesion intensities span roughly −4 to +6, so they fall into about **1–3 gray levels**.
  - GLCM, GLSZM, GLRLM, NGTDM and GLDM "texture" is therefore close to a binary partition above or below the lesion mean. It mostly encodes morphology and size, not texture.
  - Check this by counting unique binned values per ROI.
  - IBSI and the glioma normalization literature (Carré 2020 *Sci Rep*; Fatania 2022 *Eur Radiol*) recommend fixed bin **count** (e.g., 32–64) after normalization, or a bin width matched to the intensity range.
- **Within-lesion z-scoring removes clinically meaningful absolute contrast.** How bright the enhancing tissue is relative to normal-appearing white matter is lost. Use brain-mask z-score or WhiteStripe (Shinohara 2014) instead, fit per scan.
- **N4 bias correction is run with the lesion mask as the fitting mask.** N4 should use a brain mask. MU-Glioma-Post is already N4-corrected by the FeTS pipeline, so this is also double correction.
- **No resampling and no IBSI compliance statement.** The data are 1 mm isotropic after FeTS preprocessing, but **64% of FLAIR and 99.8% of T2 were acquired as 2D stacks with about 5 mm slices**. FLAIR texture is therefore interpolated texture.
- **Feature selection is not fully nested** (audit H). Model families and feature subsets were searched with Optuna, and the exported result lives in `repeated_forward_hybrid_basic_corrected/seed_62`.
  - Document how seed 62 was chosen.
  - If it was chosen by held-out performance among repeated seeds, the test set has been used for model selection.
- **"Brier 0.154 confirms well-calibrated".** The Brier score is not a calibration measure. With test prevalence 0.262, a constant predictor scores 0.193, so 0.154 is a modest improvement. Report calibration slope, calibration-in-the-large and a calibration curve (Van Calster 2016/2019).
- **Operating point.** Recall is 55% at the chosen threshold, so nearly half of the scans that precede progression are missed. The paper never discusses this for a surveillance tool.

**Image branch**
- **Bounding-box crop then per-axis resize to 128³** (notebook cell 6). Anisotropic stretching removes absolute size and shape, which are among the strongest known signals.
- **Global average pooling over the whole crop** mixes cavity, enhancing tumor, edema and normal brain. The segmentation masks you already have are not used for pooling.
- **The "encoder validation" is not validation.**
  - PCA explained variance on random-network features reflects input statistics, not information content.
  - Five hand-picked "diverging trajectories" are anecdotes.
  - Replace both with a linear probe against the label and against known quantities such as ET volume, plus a random-init control.

**Fusion**
- The late-fusion rationale ("likely degrading performance") is asserted without evidence. No early-fusion or single-branch ablation was run.
- ModDrop is claimed for robustness to missing modalities, but no missing-modality experiment exists.
- The 0.48 threshold is described as "favoring recall", yet it is essentially 0.5 and was not tuned on validation data.

**Evaluation**
- No confidence intervals anywhere. No patient-level vs visit-level weighting statement.
- No calibration plot. No subgroup results. No simple baselines (volume-only, clinical-only, time-since-diagnosis-only).
- No cohort flow diagram.
  - The CSVs contain 231 + 84 = 315 scans from 157 patients, against 594 scans from 203 patients in the dataset.
  - The exclusions (post-progression scans, scans after late treatment, missing masks, unlabeled) are never reported.
- **Censoring.**
  - Negatives include scans from non-progressors with no check that at least 120 days of follow-up exist. In test, 37 of 62 negatives are from patients with no recorded progression.
  - One test scan dated **on** the progression day is labeled 0 (`PatientID_0004`, Δ = 0). This points to an inconsistent clinical record.
- **The 0.599 → 0.804 jump after redefining the task** is presented as insight. A reviewer will ask whether the new task is just easier:
  - scans just before progression have visibly larger lesions, so the model may be doing volume detection;
  - dropping post-progression scans changes the population.
  - You need a volume-only and a time-only baseline to answer this.

### A4. Dataset description errors

- Segmentations are described as "automated". In MU-Glioma-Post they are automated (FeTS/FL-PoST) **and then refined by neuroradiologists**. Describe them accurately, and note that the final labels stay close to the automated output (Dice about 0.96–0.99).
- The cohort is not GBM-only: 77% GBM, plus about 28 grade-2 astrocytomas and others. The title says GBM. Either restrict to GBM or stratify.
- Scanners are 97.5% Siemens, with mixed 1.5 T and 3 T. This is relevant to bias and is not mentioned.
- The progression definition (EMR clinical impression; imaging-only, clinical-only or both) must be stated verbatim from the data descriptor.

### A5. Literature positioning

- **The closest prior work is under-described.** Christodoulou et al. 2026 (*Eur J Radiol AI* 5:100074) used **the same dataset**. They built calibrated radiomics (LightGBM, 256 features, Optuna, Platt), reported AUC 0.80 and added global SHAP.
  - Your radiomics branch is effectively a replication of theirs.
  - Your stated novelty was the LLM agent, which is now deferred, so the contribution statement must be rebuilt.
- Other MU-Glioma-Post progression works to cite and differentiate from:
  - Rai 2026 (*JIDMIS*): volume-derived label, nested CV AUC 0.728.
  - Hashim 2026 (*Cureus*): volume and radiomics for PFS; volume did not replicate externally.
  - Jung & Shin 2026 (arXiv): forecasting that barely beats persistence.
  - TRACE (Tarek 2026, arXiv): concept-bottleneck model on LUMIERE.
- Missing foundational citations:
  - RANO 2.0 (Wen 2023).
  - Kickingereder 2019 *Lancet Oncol* (automated volumetric response).
  - Chang 2019 *Neuro-Oncology* (AutoRANO).
  - Booth 2022 *Front Oncol* systematic review: ML for progression vs pseudoprogression, 100% high risk of bias for the reference standard.
  - Shi 2025 *Neuro-Oncology* systematic review of automated response assessment.
  - BraTS 2024 post-treatment challenge (de Verdier 2024).
  - TRIPOD+AI, CLAIM 2024, CLEAR.
- Weak or incorrect citations:
  - Ref [9] has no authors (a raw ScienceDirect URL). For pseudoprogression incidence use Abbasi 2018 (*Clin Neuroradiol*).
  - Ref [14] (Swin UNETR) should cite the BrainLes 2021 proceedings version.
  - Ref [16] (FDA transparency principles) supports nothing the system actually does.
- "None of these models have been deployed in clinical care" is too broad. "Therefore, there has yet to be an LLM-based clinical agent…" is a non sequitur.

### A6. Reporting-guideline compliance (currently essentially zero)

A mid-tier journal will expect **TRIPOD+AI** (Collins 2024, *BMJ*) for a prediction model, plus **CLAIM 2024** (Tejani 2024, *Radiol AI*) and **CLEAR** (Kocak 2023) for imaging and radiomics. CLAIM 2024 items that apply directly:

| CLAIM 2024 item | Requirement | Current status |
|---|---|---|
| 29 | Uncertainty for performance metrics | Absent |
| 31 | If explainability is used, describe it **and how it was validated** | An unvalidated SHAP bar chart does not satisfy this |
| 38 | Calibration curves | Absent |
| 39 | Failure analysis | Absent |

### A7. Presentation

- The IEEE conference template, "Clinical Relevance" line and 5-page length need converting to a structured journal article: Introduction, Methods, Results, Discussion, and a Data/Code availability statement.
- Typos and jargon to fix:
  - "((Post-treatment"
  - "calibrated logistic regressions"
  - "all tokens embeddings"
  - "exported corrected forward model"
  - "retained good ranking performance over a good threshold range"
- Figure 2 caption: "peak-model SHAP shared by input block".
- Replace per-branch prose with a single overview figure: data → segmentation/measurements → models → explanation → uncertainty.
- Author contributions: authorship order and seniority must be agreed before submission. Several branches will be demoted or replaced.

---

## Part B — Where the field is, and where a mid-tier paper fits

### B1. State of the art in brief

**Progression vs pseudoprogression / treatment-related change**
- Typical AUCs are 0.85–0.95 internally, about 0.75–0.85 externally.
- Conventional-MRI-only models do worse (about 0.65–0.76) than those with perfusion or DWI (Kim 2019 *Neuro-Oncol*; Park 2021 *Sci Rep*; Akbari 2020 *Cancer*).
- On Burdenko (n = 180), 11 deep architectures reached only **AUC 0.57–0.63** (Guo & Mirzaei 2025/26, *Cancers*).
- Systematic reviews:
  - Booth 2022: pooled AUC 0.77; only 6/18 studies had external tests; universal reference-standard bias.
  - Palavani 2025: specificity 63% in GBM.

**Automated response assessment**
- Kickingereder 2019: automated volumetric time-to-progression was a better overall-survival surrogate than central RANO (EORTC-26101, 532 patients).
- **No tool has been formally validated against RANO 2.0** (Šlachta 2026, *Front Neurol*; Shi 2025).

**Longitudinal / forward-risk models**
- Few exist. Delta-radiomics on post-treatment GBM with rigorous external validation is essentially absent; Christodoulou explicitly lists it as future work.
- Forecasting models often only match "carry the last scan forward" (Jung 2026; OncoTwin 2026 preprint).

**Explainability in glioma imaging**
- Mostly superficial Grad-CAM or SHAP with **no quantitative evaluation** (Ayaz 2025, *Comput Biol Med*, 65-study review).
- On glioma MRI, 16 heatmap methods all failed clinical requirements, and neurosurgeon agreement on explanations was near zero (Jin 2022 AAAI; Jin 2023 *MedIA*).
- Saliency sanity and trust problems are well documented: Adebayo 2018; Arun 2021 *Radiol AI*; Saporta 2022 *Nat Mach Intell*; Ghassemi 2021 *Lancet Digit Health*.
- The literature favors **interpretable-by-design models** (Rudin 2019): concept bottlenecks (Koh 2020; TRACE 2026 for GBM), prototype networks (MProtoNet 2023 for 3D brain-tumor MRI; PANIC 2023, which combines image prototypes with an additive model over tabular features), and GAMs/EBMs (Caruana 2015).

**Bias**
- Subgroup, scanner and shortcut auditing is **essentially absent** from post-treatment glioma ML.
- Relevant evidence from other imaging domains: shortcut learning (DeGrave 2021; Brown 2023 shortcut testing), demographic encoding (Gichoya 2022; Glocker 2023), and the limits of fairness transfer across sites (Yang 2024 *Nat Med*).
- Radiomics signatures that collapse to volume: Welch 2019 *Radiother Oncol*.

### B2. Gaps this project can credibly fill (the contribution statement)

1. **A properly specified endpoint.**
   - Forward-risk landmark prediction ("given a surveillance scan, risk of documented progression within H days"), handling censoring and the RANO 2.0 12-week post-RT window explicitly.
   - Sensitivity analyses at H = 90/120/180 days.
   - Existing MU-Glioma-Post papers either leave the endpoint loosely specified or use volume-derived labels.
2. **Explanations that are the model, not a post-hoc view of it.**
   - Clinically named concepts: compartment volumes, their change from prior scan and nadir, cavity-adjacent enhancement, relative enhancement, time since RT.
   - **Quantitative evaluation** of every explanation: faithfulness, stability, anatomical localization against ET/NETC/SNFH/RC masks.
   - No post-treatment GBM paper has evaluated attributions against sub-region masks.
3. **A systematic bias and shortcut audit.**
   - A confounder-only model.
   - Missingness-shortcut tests.
   - Scanner and field-strength predictability.
   - Subgroup discrimination and calibration with patient-clustered CIs.
   - Segmentation-perturbation robustness.
4. **An honest model ladder**, showing how much each layer of complexity adds:
   - persistence / volume-only / RANO-style rule
   - → concept glass box
   - → corrected radiomics
   - → pretrained 3D deep features
5. **Uncertainty-aware decision support.** Calibrated risk with patient-level conformal or selective prediction, plus a risk–coverage analysis: defer the uncertain cases to the radiologist.
6. **Locked-model external evaluation** on one or two independent public cohorts, with explicit endpoint-mismatch handling.

That is a coherent mid-tier paper. It does not need a new architecture to be publishable. Its value is rigor, interpretability and auditing, which is exactly what the field's own reviews say is missing.

---

## Part C — The proposed system

### C1. Clinical framing

A **surveillance risk-stratification aid** for post-treatment glioma. It is not a diagnostic tool and not a pseudoprogression classifier. For each follow-up MRI it outputs:

1. **Automated measurements.** ET, NETC, SNFH and RC volumes; change since the prior scan and since nadir; a RANO-2.0-style volumetric flag, labeled as **indicative, not adjudicated**.
2. **A calibrated risk of documented progression within H days**, with an uncertainty band.
3. **A concept-level explanation.** Which measured quantities drive the risk, and by how much, in probability units.
4. **An abstain/refer flag** when the case is out-of-distribution, uncertain, or inside the 12-week post-RT window where pseudoprogression dominates.

### C2. Data and endpoints

**Development set: MU-Glioma-Post** (203 patients, 594 timepoints, CC BY 4.0).
- **Primary endpoint:** first documented progression within **H = 120 days** after a pre-progression scan. The index scan must precede progression. Negatives require at least H days of documented follow-up (last contact or death date); otherwise the scan is censored and excluded, and the counts are reported.
- **Secondary analysis:** discrete-time or landmark survival model; time-dependent AUC at 120 days with IPCW (Blanche 2013); H = 90/180 sensitivity analyses.
- **Primary analysis restricted to GBM / grade 4.** Non-GBM gliomas are reported as a stratum.
- **RANO 2.0 window:** scans ≤12 weeks after RT are flagged and analyzed separately. This is where label noise from pseudoprogression is concentrated.

**External cohort 1: "GBM CBF" — confirm this is CFB-GBM (Centre François Baclesse, TCIA DOI 10.7937/v9pn-2f72; use v4 from 2026-09-11, which corrected the RANO labels).**

> **Mismatch warning.** From the data descriptor (Leclercq et al., arXiv 2608.17884):
> - 264 Stupp-treated GBM patients; all deceased.
> - 3 timepoints: pre-RT, about 16 weeks, about 30 weeks.
> - Mostly T1-Gd + FLAIR; native T1 and T2 are nearly absent after baseline.
> - A single GTV label (no ET/NETC/SNFH/RC split).
> - **No progression dates, no MGMT/IDH, no extent of resection.**
> - RANO labels are **algorithmic volumetric changes in GTV** (+40% counts as PD), not expert-adjudicated.
>
> It **cannot** validate the 120-day clinical-progression endpoint like-for-like.

Supported uses of CFB-GBM:
- (a) **Measurement transport.** Our segmentation and measurement pipeline vs their GTVs (Dice, volume agreement).
- (b) **Proxy endpoint.** Predict volumetric PD at the *next* scan from the *current* scan using the T1c+FLAIR model. The label comes from a future scan, so it is not circular.
- (c) **Overall-survival discrimination** of the risk score (C-index), since OS is available for everyone.
- (d) **Dataset-shift and calibration-transport analysis.**

**The primary model must therefore be T1c + FLAIR (+ masks) only**, so that it can run on CFB-GBM. A 4-sequence model can only be an internal ablation.

**Recommended additional external cohort: LUMIERE** (Suter 2022, *Sci Data*).
- 91 GBM patients, 638 dates.
- **Expert RANO ratings** at 616 timepoints, so "PD within 120 days" can be derived directly.
- MGMT for 80 patients; single center (Bern).
- It is the best like-for-like external test available publicly. Check the license.

Optional:
- **Burdenko-GBM-Progression**: 180 patients, per-follow-up progression / pseudoprogression / response labels; controlled access.
- **UCSD-PTGBM**: 178 patients, tumor vs treatment effect, 45 pathology-proven; mostly one timepoint per patient.

### C3. Model ladder

Every rung is trained with the **same patient-grouped nested CV** on MU, locked, then evaluated externally.

| Rung | Model | Role |
|---|---|---|
| M0a | **Confounder-only.** Days since diagnosis/RT, visit index, field strength, scanner. | Shortcut probe. If this scores near M1, the task is being solved by timing. |
| M0b | **Clinical-only.** Age, sex, MGMT and IDH with an explicit "unknown" level, extent of resection if available. | Baseline. |
| M0c | **Volume-only + RANO-style rule.** ET/SNFH volumes, Δ from nadir, ≥40% ET-volume flag. | The "is it just size?" baseline (Welch 2019). |
| **M1 (primary)** | **Concept glass box.** Explainable Boosting Machine or sparse spline-logistic GAM (see below). | The model that ships. Its shape functions *are* the explanation. |
| M2 | **Corrected radiomics.** Brain-mask z-score or WhiteStripe, fixed bin count, perturbation-stable features (ICC ≥ 0.75 under mask erosion/dilation), fully nested selection, penalized logistic regression; grouped (Owen) SHAP by sequence × compartment. | Head-to-head with Christodoulou 2026; tests whether texture adds anything beyond the concepts. |
| M3 | **Pretrained 3D deep features.** Frozen encoder, features pooled **per compartment mask** (ET, SNFH, RC, peritumoral ring) so each embedding has anatomical identity, with a linear or logistic probe. Includes a random-init control. | Tests whether deep features add information beyond the concepts. |
| M4 | **Concept-bottleneck 3D network**, optionally with a prototype layer. Image → predicted concepts → risk head. | Interpretable deep model; enables concept interventions and "similar prior cases". |

**M1 inputs:** about 15–25 pre-registered, named concepts computed with the existing `radiomics_tools/metrics` helpers (after fixing the semantics flagged in the audit):
- ET, NETC, SNFH and RC volumes (cc)
- Δ from prior scan and Δ from nadir, as absolute values and as %
- ET/NETC fraction
- cavity-adjacent ET fraction
- T1c/T1 enhancement ratio in ET (only where T1 exists; otherwise dropped for transport)
- FLAIR intensity in SNFH relative to NAWM
- days since RT end
- age, and MGMT with an explicit unknown level

Every concept must be computable on CFB-GBM, or be explicitly marked MU-only.

**M3 encoder choice** (all fit comfortably on 4×H100; frozen feature extraction takes under an hour):
- **Primary: BrainSegFounder** (Swin UNETR, SSL on UK Biobank then BraTS; *MedIA* 2024; GPL-3.0), or the **MONAI Swin UNETR BraTS21** weights. This is a genuinely pretrained Swin UNETR, so the name is finally accurate.
- **Comparator: BrainIAC** (*Nat Neurosci* 2026; single-sequence ViT, 96³; non-commercial license). Run it on T1c and FLAIR separately and concatenate.
- **Optional: BrainMVP** (CVPR 2025; handles missing modalities), useful for CFB-GBM.
- **Optional ablation only: continued SSL** on unlabeled post-treatment scans (BraTS 2024 GLI, UCSF-ALPTDG, LUMIERE). About 1–3 days on 4×H100. **Exclude all external-test cohorts and MU test folds** from pretraining.
- **Avoid:** Swin UNETR self-supervised weights from Tang 2022 (pretrained on **CT**, not MRI), Models Genesis (chest CT) and MedicalNet, except as weak baselines.

**Segmentation for the external cohorts:** the BraTS 2024 post-treatment winner (Ferreira et al., arXiv 2411.04632; nnU-Net + MedNeXt; Zenodo weights, MIT license), or the `brats` orchestrator's post-treatment segmenter.
- **Leakage disclosure:** Missouri contributed about 400 cases to BraTS 2024 GLI, and part of MU-Glioma-Post was used to build FL-PoST. Use MU's own released masks for MU, and never report this segmenter's MU performance as independent.
- On CFB-GBM, most patients lack T1n and T2, so the 4-channel segmenter may need synthesized or dropped channels. Check this, or fall back to their GTV plus a T1c+FLAIR segmenter.

**Longitudinal information** enters through the Δ-concepts, i.e. deltas from the prior scan and from nadir. Only if M1–M3 are stable, add a tiny time-aware aggregator (a GRU or attention over the prior 1–3 scans plus Δt). With about 200 patients, keep it small.

**Missing modalities:** train M3/M4 with modality dropout, and **test** it by evaluating with each sequence ablated.

### C4. Explainability — what gets claimed and how it is validated

This follows the requirements of CLAIM 2024 item 31 and FUTURE-AI Explainability-2.

| Explanation | Validation |
|---|---|
| **M1 shape functions** (per-concept risk contribution) | Bootstrap CIs on each shape function. Monotonicity or clinical-plausibility review with a clinician. Stability across CV folds (Kendall τ of importance ranks). **Concept-intervention tests:** set Δ-ET to 0 and measure the change in risk. |
| **M2 grouped SHAP** | State the output space (log-odds vs calibrated probability) and interventional vs observational SHAP (Chen 2020). Owen values over correlated groups. Stability across folds and background sets. Ablation that removes each group. |
| **M3/M4 image attribution** (Grad-CAM or Integrated Gradients, only if used) | **Sanity checks** (model and label randomization; Adebayo 2018). **Faithfulness:** deletion/insertion AUC; ROAR on a subset. **Anatomical localization:** fraction of attribution mass in ET / NETC / SNFH / RC / normal brain vs a random-map null, stratified by TP/FP/FN. Attribution on the cavity or normal brain is flagged as a shortcut. Use the Quantus toolkit. |
| **M4 concepts** | Concept prediction accuracy vs measured concepts. Task accuracy with predicted vs true concepts. Intervention curves. |
| **Similar-case retrieval** (optional prototypes) | Retrieval precision for the label. Blinded "is this a sensible comparison?" review. |

**Uncertainty layer**
- Deep ensemble (5 seeds) or bootstrap ensemble for M1.
- **Patient-level split conformal prediction.** Scans within a patient are not exchangeable, so calibrate by patient.
- Report risk–coverage curves and coverage by subgroup and on external data. Conformal coverage is known to break under shift (Mehrtens 2023), so report that as a finding, not a failure.

**Human-grounded evaluation (optional but valuable)**
- 1–2 neuroradiologists or neuro-oncologists rate about 40–50 cases, blinded, with and without the explanation panel.
- Measure agreement, correct reliance (do they catch model errors?) and time.
- Given Jin 2022's near-zero inter-rater agreement on explanations, report agreement honestly. This moves the paper from mid-tier toward upper-mid-tier.

### C5. Bias, shortcut and robustness audit (pre-registered)

1. **Leakage controls.**
   - Patient-grouped *nested* CV for every fitted step: normalization parameters, imputation, feature selection, harmonization, hyperparameters, threshold, calibration.
   - Export fold membership and freeze the pipeline before unblinding the external cohorts.
2. **Shortcut probes.**
   - M0a confounder-only AUC.
   - Predict scanner, field strength and visit index from the features and embeddings.
   - Glocker-style test of whether embeddings encode age, sex, MGMT or IDH.
   - Within-patient label-permutation test.
   - **Missingness shortcut:** compare models with and without "unknown" molecular indicators, and report how often each is unknown by label.
3. **Subgroups** (pre-specified), each with AUC, calibration-in-the-large (O/E) and sensitivity/specificity at the locked threshold, with **patient-clustered bootstrap CIs**:
   - age <65 / ≥65
   - sex
   - MGMT (methylated / unmethylated / unknown)
   - IDH
   - GBM vs non-GBM
   - extent of resection
   - field strength (1.5 T / 3 T)
   - scanner model
   - ≤12 weeks vs >12 weeks post-RT
   - bevacizumab exposure if recorded

   Strata with fewer than about 10 events are reported as descriptive only. **Race cannot be audited** (94.6% White). State this as an applicability limitation.
4. **Robustness.**
   - Mask perturbation: erode or dilate 1–2 mm; supervoxel contour randomization (Zwanenburg 2019). Report feature ICC, Δ-risk and ΔAUC.
   - Normalization sensitivity: z-score vs WhiteStripe vs Nyúl.
   - Image perturbations for M3.
   - ComBat by scanner/field strength as a **sensitivity analysis only**, fit on training folds.
5. **Label-noise sensitivity.**
   - Exclude the ≤12-week post-RT window.
   - Exclude scans with inconsistent clinical records (e.g., Δ = 0 labeled negative).
   - Vary H.
6. **External transport.**
   - Case-mix table.
   - Membership model (dev vs external).
   - Classifier two-sample test / MMD on embeddings.
   - Locked-model performance **first**, then intercept-only and intercept+slope recalibration reported separately.
   - A Riley sample-size check (Riley 2021/2024), with external validation labeled "exploratory" if underpowered.

### C6. Statistics and reporting

- AUROC and AUPRC with **patient-clustered bootstrap** 95% CIs (≥2000 resamples). Report visit-weighted and patient-weighted results.
- Model comparisons: paired cluster bootstrap of ΔAUC, or Obuchowski 1997 clustered AUC. Correct for the number of rungs compared.
- Calibration: O/E, slope, flexible curve, Brier (with the null-model Brier for reference), decision-curve analysis.
- Report against **TRIPOD+AI**; self-assess with **PROBAST+AI**, **CLAIM 2024** and **CLEAR**, with the checklists in the supplement.
- Release code, configs, patient-level fold IDs and locked model weights (the data is public, which strengthens the paper).

---

## Part D — Execution plan

About 10–14 weeks of part-time work across the team. GPU-heavy steps are marked ⚡.

| Phase | Weeks | Work | Exit criterion |
|---|---|---|---|
| 0. Freeze the question | 1 | Confirm the "GBM CBF" identity and version. Get the MU clinical codebook. Write the endpoint and censoring contract. Pre-register subgroups, rungs, metrics and the H sensitivity grid. Settle authorship. | One-page protocol committed to `docs/` |
| 1. Data foundation | 1–2 | Rebuild the cohort table with a flow diagram and censoring rules. Fix clinical coding (explicit unknowns). Fix the measurement-helper semantics (audit Priority 2). Unit tests. Generate nested patient folds. | Reproducible cohort table and flow diagram |
| 2. Baselines + M1 | 2–3 | M0a–c and M1 (EBM/GAM) with the full evaluation harness: clustered CIs, calibration, DCA, subgroup tables, shortcut probes. | First honest results table. **This alone is already a paper skeleton.** |
| 3. Corrected radiomics (M2) | 2 | Re-extract with corrected normalization and binning, run the perturbation-stability screen, nested selection, grouped SHAP with stability. | Answer to "does texture add beyond concepts?" |
| 4. ⚡ Deep features (M3) | 2–3 | Compartment-pooled frozen features from BrainSegFounder / Swin UNETR-BraTS21 / BrainIAC, plus a random-init control, linear probes, attribution sanity/faithfulness/localization. Optional continued-SSL ablation. | Answer to "do deep features add beyond concepts?" plus the explanation-evaluation tables |
| 5. ⚡ M4 (optional) | 2 | Concept-bottleneck 3D model with interventions; optional prototypes. | Include only if it matches M1/M3 performance |
| 6. Uncertainty + locked external | 2 | Ensemble plus patient-level conformal prediction, risk–coverage. Lock everything → CFB-GBM (proxy endpoints, OS, transport) and LUMIERE (120-day PD from expert RANO). | External results table and shift analysis |
| 7. Write | 2–3 | Full rewrite as a TRIPOD+AI-structured journal article; supplement with checklists; optional reader study in parallel. | Submission |

**Compute reality check:** apart from optional SSL (1–3 days), nothing here needs more than about a day on 4×H100. The H100s matter for M3/M4 and SSL. The paper's value comes from phases 0–3 and 6, which are CPU-bound.

---

## Part E — Decisions and inputs needed

1. **Identity of "GBM CBF".** CFB-GBM (Caen, TCIA) is assumed. If it is something else, such as a cerebral-blood-flow perfusion dataset, the external plan changes.
2. **Whether to add LUMIERE** as the like-for-like external cohort. Strongly recommended.
3. **The MU clinical codebook** (meaning of codes 2 and 4, follow-up and last-contact fields, RT end date, bevacizumab/steroid fields if present).
4. **A clinical collaborator** for a concept-plausibility review and optionally a small reader study.
5. **Primary horizon H.** 120 days is retained for continuity with prior work; 90/180 are sensitivity analyses.
6. **Authorship and lead-author agreement** before the rewrite starts.

## Part F — Suggested title and one-sentence contribution

*"Interpretable, bias-audited risk stratification for post-treatment glioblastoma surveillance: concept-based models, evaluated explanations, and external validation."*

*Hypothesis to test, not a result yet:* a small set of automatically measured, clinically named tumor-compartment concepts in a glass-box model does three things. First, it matches or approaches radiomics and pretrained 3D deep features for forward progression risk. Second, its explanations can be quantitatively validated and audited for shortcuts and subgroup bias. Third, uncertainty-aware deferral makes its behavior predictable under dataset shift.
