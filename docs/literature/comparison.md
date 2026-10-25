# Literature comparison — post-treatment glioma progression prediction

Compiled 2026-10-09. Everything below was checked against a primary source (publisher page, PubMed/Europe PMC record, Crossref metadata, or the arXiv PDF). Each row says how much of the source was read:

- **[full]**: full text read (arXiv PDF).
- **[abs]**: abstract only. Methods detail beyond the abstract is not claimed.
- **[sec]**: number taken from a secondary source (named).
- **UNVERIFIED**: could not be confirmed.

Metric values are copied as the authors report them.

**Our reference point.** One follow-up scan plus the clinical and treatment information known at that time. Endpoint: progression within 120 days, censoring-aware. Validation: repeated patient-grouped CV on MU-Glioma-Post (grade 4: 253 scans / 128 patients), then a locked external test on LUMIERE (132 scans / 61 patients; label = RANO PD within 120 d).

- Clinical + timing + treatment: AUC about 0.69–0.74. Radiomics adds nothing significant.
- LUMIERE external test: AUC 0.61 for the shipped radiomics model and 0.72 for clinical + timing + volumes with boosting (`docs/results/EXTERNAL_LUMIERE.md`).

---

## 1. Summary

- **Nobody else reports our endpoint.** No published study predicts *forward, fixed-horizon* progression from a single post-treatment scan with explicit censoring handling, on MU-Glioma-Post or LUMIERE. Studies on these two datasets fall into four other groups:
  - classify the *current* progression state (Christodoulou 2026);
  - predict a *volume-defined* next-scan label (Rai 2026);
  - fit per-patient PFS/OS Cox models (Hashim 2026; CLARITY);
  - classify the *concurrent* RANO response of a scan pair (all LUMIERE work: Matoso, Amato, Tikhonov, TRACE).
- **No study externally validates a MU-Glioma-Post progression model on LUMIERE, or the reverse.**
  - Hashim 2026 validated *volume / radiomic Cox scores* on UCSD-PTGBM, UCSF-PDGM and UPenn-GBM, at the patient level (PFS/OS).
  - CLARITY tested zero-shot on UCSF-ALPTDG (survival).
  - Chen 2026 trained on LUMIERE and tested on RHUH-GBM (6-month recurrence from pre- and post-operative MRI).
- **The headline MU numbers are not comparable to ours.**
  - Christodoulou 2026 (AUC 0.80) comes from a single patient-held-out split. Our repo's earlier reading puts that split at 30 patients / 96 scans. The label is progression *status*, not forward risk. Correction (2026-10-26): a re-implementation of their setting (CHRISTODOULOU_REPLICATION.md, 2026-10-26) gives 0.565 under repeated CV on our detection label; the earlier "0.64–0.70" was a 120-day ridge model, not their setting.
  - Rai 2026 (nested AUC 0.728) defines progression as a ≥25 % volume increase at the next scan. That label is computed from the same segmentations used as features, so it is not a clinical endpoint.
- **LUMIERE response-classification results are modest and concurrent, not predictive.**
  - 4-class RANO macro F1 ranges from 0.477 to 0.616 (TRACE table).
  - Binary PD-vs-rest macro F1 is 0.7085 (TRACE).
  - The best 4-class ROC AUC is 0.81 (Tikhonov, 5-fold patient-wise CV).
  - "Volumes only" reaches 4-class AUC 0.59 (Tikhonov).
  - A RANO threshold rule applied to *ground-truth* measurements reaches only 0.681 binary macro F1 (TRACE). Expert RANO labels are not fully reproducible from segmentation-derived measurements, which matches our finding that volumes alone transport poorly (0.53–0.62).
- **Typical protocols.**
  - Patient-wise 5-fold CV without repetition (TRACE, Tikhonov, Christodoulou-CV, CLARITY), or a single holdout (Christodoulou test set; Yun 2025, 70/30).
  - Matoso 2025 uses an "80/20 stratified split" with no stated patient grouping, so leakage is possible.
  - Repeated CV, confidence intervals, calibration and censoring handling are rare. Rai 2026 (nested CV with CI) and Christodoulou 2026 (Platt calibration, Brier) are the partial exceptions.
- **Forward prediction from post-treatment scans (other cohorts) is rare and small.**
  - Tak 2025 (paediatric, 1-year recurrence from serial scans, AUC 75–89 %).
  - Yun 2025 (560 GBM, 6/12-month PFS from post-treatment MRI, AUC 0.61–0.75).
  - Li 2022 (162 HGG, pre-RT MRI, progression at 6–18 months, AUC 0.68–0.78).
  - Chen 2026 (139 GBM, 6-month recurrence, external AUC 0.762).
  - Only Tak 2025 uses many follow-up scans per patient. None uses a landmark or discrete-time survival formulation.
- **Adjacent task (progression vs pseudoprogression) has a different label and higher reported AUCs.**
  - Booth 2022 meta-analysis: pooled ROC-AUC 0.765 over 18 studies with high bias risk.
  - On public anatomical-only data, results are lower: Burdenko 11-architecture benchmark best AUC 0.57 (first follow-up) and 0.66 (second follow-up); Gomaa 2025 external AUC 75.3 % on n = 20.
  - These results should not be put on the same axis as ours.
- **The gap our work fills.**
  1. A clinically defined, censoring-aware, fixed-horizon per-scan endpoint (EMR progression on MU; RANO PD on LUMIERE).
  2. Repeated patient-grouped CV with CIs and calibration.
  3. The first MU → LUMIERE locked external test.
  4. A ladder of baselines from the literature (persistence/volume rule → volumetric RANO → Christodoulou / Rai / Yun / Hashim / Tikhonov-style feature models), all scored under one protocol.

  The honest message is that clinical, timing and treatment information carries most of the signal. Published imaging-only or radiomics numbers on these datasets are not comparable, and drop under our protocol.

---

## 2. Table A — studies reporting models on MU-Glioma-Post or LUMIERE

Column "Re-impl." = can it be re-implemented in our harness with our data (yes / partly / no + reason).

### A1. MU-Glioma-Post

| Study | Data (n) | Endpoint / horizon / censoring | Inputs | Method | Validation | Headline metric (as reported) | Code | Re-impl. | Strength / weakness |
|---|---|---|---|---|---|---|---|---|---|
| **Christodoulou RC, Vamvouras G, Pitsillos R, Solomou EE, Georgiou MF. 2026**, *Eur J Radiol AI* 5:100074, doi:10.1016/j.ejrai.2026.100074 **[abs]** (full text returned 403) | MU-Glioma-Post. n in abstract not stated. Our repo's earlier reading: test set 30 patients / 96 scans (`legacy/radiomics/README.md`, not re-verified) | "Progression status" of each post-op scan. No horizon; censoring not mentioned | T1, T1-CE, T2, FLAIR. nnU-Net masks refined by experts. PyRadiomics + LoG + wavelet; 256 features | LightGBM, Optuna, Platt calibration, SHAP | Patient-aware 5-fold CV for tuning; one patient-held-out test set | AUC 0.80 (test). Brier 0.093 → 0.088 after calibration. 16 FP, 6 FN. No CI in abstract | Not stated | **Yes**: features and learner reproducible. Their label must be swapped for ours (status ≠ forward risk) | + calibration, explicit patient-awareness. − single small test split, no CI, state label; not comparable (a re-implementation of their setting (CHRISTODOULOU_REPLICATION.md, 2026-10-26) gives 0.565 under repeated CV on our detection label; the earlier "0.64–0.70" was a 120-day ridge model, not their setting) |
| **Rai AK. 2026**, "Uncertainty Gated Residual Learning with Patient Level Bagging for Longitudinal Glioma Progression Prediction", *J Intell Decis Mak Inf Sci* 3, doi:10.59543/jidmis.v3.2236 **[abs]** (via Crossref) | MU-Glioma-Post: 391 non-leaky consecutive pairs / 155 patients; 38.1 % positive | **≥25 % tumour-volume increase at the next timepoint** (volume-derived). Horizon = next scan (variable). Censoring n/a | T1c, T1n, T2f, T2w; masks; 3D radiomics/texture; "time-safe clinical event features" | Anchor ensemble (LR, tree ensembles, XGBoost, CatBoost) + uncertainty-gated residual correction + monotonic tumour-kinetics expert + patient-level bagging | Strict nested, patient-grouped CV | Nested OOF AUC 0.728 (95 % CI 0.678–0.777) vs reference 0.713. Bal. acc 0.691, F1 0.638, sens 0.738, spec 0.645 | Not stated | **Yes** (simplified): label computable from our MU volumes, so we can reproduce *their* endpoint exactly and also run their learner on ours | + nested grouped CV with CI. − label defined from the same volumes used as features (circular); not a clinical progression endpoint; variable horizon |
| **Hashim U, Jalal A, Jabali AN, Rana H. 2026**, "Radiomics Outperforms Conventional Tumor Volume in Prognostic Stratification Across Independent Glioma Cohorts", *Cureus* 18(7):e112298, doi:10.7759/cureus.112298 **[abs]** | Four public cohorts, 1,447 patients. MU discovery: 194 patients (152 progressed). Also UCSD-PTGBM, UCSF-PDGM (n = 494), UPenn-GBM (n = 581) | Per-patient PFS (MU; median PFS / follow-up 159 d) and OS (UPenn). Cox (handles censoring) | Segmentation-derived active tumour volume; radiomic risk score; age, grade, IDH, MGMT | Cox regression | Discovery / external cohorts (patient-level) | MU: active tumour volume HR 1.045 per 10,000 mm³ (95 % CI 1.015–1.076), C-index 0.676. UCSD enhancing volume HR 1.144 (p = 0.191). UPenn radiomic score HR 1.634 (1.302–2.050) for OS | Not stated | **Yes** (Cox on volume + clinical, scored as 120-d risk) | + multi-cohort, censoring-aware. − per-patient (one scan per patient; which scan is not stated in abstract); radiomics validated on pre-op cohorts / OS, not the post-op task |
| **Ding T, Zou Y, Chen C, Shah M, Tian Y. 2025/2026, CLARITY**, arXiv:2512.08029 (accepted ECCV 2026) **[full]** | MU-Glioma-Post 203 patients / "654 MRI follow-ups". Zero-shot UCSF-ALPTDG 298 patients | (i) treatment-choice F1; (ii) survival: one-year survival probability + risk score. Survival endpoint type (OS vs PFS) not stated in the sections read | Imaging latents, inter-scan intervals, clinical context, treatment | Latent "world model" + survival predictor + planning loop | Patient-level 75/15/15 split + 5-fold CV over train/val | MU: treatment F1 57.1 %. C-index 0.794 ± 0.02 (DeepSurv 0.664, RSF 0.672, SurvTRACE 0.713). UCSF-ALPTDG treatment F1 48.9 % | Project page linked; repo not confirmed | **No**: heavy generative model; endpoint differs | + patient-level split, external zero-shot. − survival C-index is per-patient; treatment-recommendation "ground truth" is observed treatment |
| **Jung Y, Shin M. 2026**, "Observation-Anchored Selective Assimilation for Longitudinal Tumor-State Proxy Forecasting in Post-Treatment Glioma", arXiv:2609.12435 **[full]** | MU: 120 of 236 candidate triplets (no new treatment). 81/24/15 train/val/test triplets, patient-level | Voxel-wise forecast of a continuous tumour-state proxy map at t2 from t0/t1. Not a risk endpoint | Multimodal MRI + lesion-label-derived proxy maps | SegMamba forecaster + selective assimilation | Patient-level holdout (15 test triplets), 3 seeds | Dice@0.2 0.6071 ± 0.0025 vs persistence 0.6070. Dice@0.5 0.4269 ± 0.0079 vs 0.3981. CIs vs persistence include 0 | github.com/jsudg436/longitudinal-proxy-forecasting | **No** (different task). The *persistence* idea transfers as a baseline | + honest persistence comparison. − 15 test triplets; the authors state gains reflect "near-threshold support calibration rather than improved biological predictive capability" |
| **Li ID, Correia C, Ung CY. 2026**, *Cancers* 18(18):3015, doi:10.3390/cancers18183015 **[abs]** | 124 single-centre patients / 164 post-op timepoints (7 channels incl. RSI, ADC, CBF). Pretrained on "588 postoperative glioma samples". Europe PMC full text mentions MU-Glioma-Post, presumably as that pretraining set (UNVERIFIED) | Recurrence vs pseudoprogression; also MGMT, short-term survival, radiation decision | 7-channel MRI incl. diffusion/perfusion | Transfer learning + task heads | Nested 5-fold, patient-level, 3 seeds | Recurrence vs PsP AUC 0.935 (SD 0.014). Short-term survival AUC 0.514 (SD 0.027) | Not stated | **No**: needs RSI/ADC/CBF and PsP labels | + nested patient-level CV. − single centre; MU used only for pretraining; adjacent task |
| Christodoulou et al. 2026 *Front Oncol* 16:1790776 (IDH/MGMT CNN; MU = external) and 16:1900609 (PTEN radiomics on 195 MU patients) **[abs]** | — | Molecular status (not progression) | — | — | — | MU external IDH AUC 0.77 (0.71–0.82); MGMT 0.57 (0.52–0.63). PTEN OOF AUC 0.874 | — | n/a | Context: same group as the baseline; MU used as a molecular external test |

Not included (MU used only for segmentation / missing-modality / PET-synthesis work, no outcome model): Lteif 2025 *Hum Brain Mapp*; Anjum 2026 *Sci Rep*; arXiv 2607.22749; arXiv 2512.21264.

### A2. LUMIERE

All the response-classification studies label each *pair of consecutive scans* with the expert RANO rating of the later scan (CR/PR/SD/PD). This is concurrent assessment and does not predict future progression. Their numbers are not comparable to our forward 120-day AUC.

| Study | Data (n) | Endpoint / horizon / censoring | Inputs | Method | Validation | Headline metric (as reported) | Code | Re-impl. | Strength / weakness |
|---|---|---|---|---|---|---|---|---|---|
| **Suter Y, Knecht U, Valenzuela W, … Reyes M. 2022**, *Sci Data* 2022, doi:10.1038/s41597-022-01881-7 **[abs]** | 91 GBM, 638 study dates (616 scans with RANO) | Dataset: expert RANO per follow-up, OS | T1, T1c, T2, FLAIR; DeepBraTumIA + HD-GLIO-AUTO segmentations; radiomics | — | — | — | Figshare | (our external set) | Single centre; automated (not expert) segmentations |
| **Suter Y, Notter M, Meier R, … Knecht U. 2023**, *Front Radiol* 3:1211859, doi:10.3389/fradi.2023.1211859 **[abs]** | LUMIERE 80 patients / 502 post-op timepoints | Agreement of automated volumetry / bidimensional measures with expert RANO; TTP | DeepBraTumIA, HD-GLIO volumes | Threshold rules (RANO) | Whole cohort | Trend agreement HD-GLIO 81.1 %, BraTumIA 79.7 %. TTP–OS correlation 0.55 (HD-GLIO) | github.com/ysuter/gbm-longitudinaleval (per LITERATURE.md; not re-checked) | **Yes**: rule baseline on our LUMIERE volumes | + rule baseline on our external set. − not a predictive model; lesion count fails |
| **Matoso A, Passarinho C, Loureiro MP, Moreira JM, Figueiredo P, Nunes RG. 2025**, arXiv:2504.18268 (also ISMRM 2025 #1301) **[full]** | LUMIERE 91 patients / 638 timepoints; PD 67 %, SD 20 %, PR 6 %, CR 7 % | 4-class RANO of a consecutive pair (concurrent) | T1, T2, FLAIR (best); subtraction, clinical data tested | DenseNet264 and others | 5-fold CV "using an 80/20 stratified split". **Patient grouping not stated** | Median balanced accuracy 50.96 % | github.com/anamatoso/RANO-classification | Partly (code public; task differs) | + first LUMIERE DL benchmark, code. − possible patient leakage; concurrent label |
| **Amato D, Calderaro S, Reitano LD, Lo Bosco G, Rizzo R, Vella F. 2025**, IEEE BIBM 2025, doi:10.1109/BIBM66473.2025.11356532 **[abs via search snippet; metrics [sec] from TRACE Table 3]** | LUMIERE | Binary PD vs non-PD and 4-class RANO | Multimodal MRI, automatic segmentation, radiomics + deep features | Fusion classifier | Not confirmed | [sec] 4-class macro F1 0.616 ± 0.048, balanced acc 0.322 ± 0.055 | Not stated | Partly | Strongest published LUMIERE macro F1. Protocol unverified |
| **Tikhonov D, Scatolin M, Banerjee M, … Yaqub M. 2025**, arXiv:2509.06511 (BraTS-Lighthouse 2025 progression task) **[full]** | LUMIERE (challenge training set) | 4-class RANO of a pair (concurrent) | 4 MRI sequences; >4,800 radiomic/clinical features incl. **growth/shrinkage-mask radiomics, volume change vs nadir, centroid shift**; ResNet-18 2D features | CatBoost | **5-fold patient-wise** stratified CV | Mean ROC AUC 0.81 ± 0.08, macro F1 0.50 ± 0.08, acc 0.72 ± 0.05. Volumes only: AUC 0.59 ± 0.05, F1 0.30 | Not stated | **Partly/yes**: the handcrafted part (nadir change, growth/shrink masks) is doable on MU + LUMIERE masks | + patient-wise CV, informative ablation. − concurrent label; mean one-vs-rest AUC over 4 classes |
| **Tarek A, Saberr H, Elghonemy H, … Sonntag D. 2026, TRACE**, arXiv:2606.30313 (EXPLIMED @ IJCAI 2026) **[full]** | LUMIERE: 599 sessions → 361 consecutive pairs; PD 63.7 % | 4-class RANO 2.0-aligned (concurrent) | Paired baseline/follow-up MRI + masks (HD-GLIO); scan interval; new-lesion flag | Concept-bottleneck model, siamese 3D encoder, RANO DAG | 5-fold patient-wise CV | 4-class macro F1 0.4769 ± 0.1229. Binary PD-vs-rest macro F1 0.7085 ± 0.0935. **Rule-based RANO oracle on GT concepts: binary macro F1 0.681 ± 0.058**, 4-class 0.346 | github.com/yusufafify/TRACE-Temporal-Causal-Reasoning-with-Acyclic-Concept-Explanation | Partly (GPU; adapt head to 120 d) | + interpretable, reports a rule baseline. − concurrent label; wide fold SD |
| **Chen C, Guo F, Huang D, … Liu Y. 2026**, "Predicting Recurrence Risk of Glioblastoma Based on Preoperative-Postoperative Longitudinal MRI", *Bioengineering* 13(6):668, doi:10.3390/bioengineering13060668 **[abs]** | 139 GBM: LUMIERE train n = 59; XJYY-GBM internal val n = 40; RHUH-GBM external test n = 40 | **Recurrence within 6 months post-surgery** (binary). Censoring not mentioned | Pre-op + post-op T2WI | MambaDiff-Net (dual-stream + feature-difference) | Train / internal / external | AUC 0.887 internal, 0.762 external | Not stated | **No** on MU (MU has no pre-op scans) | + only LUMIERE-trained forward model with external test. − tiny sets (40/40); T2 only; censoring unaddressed |
| **Pineda G, … Tiwari P. 2024**, "SDDR …", *Neuro-Oncology* 26(Suppl 8) abstract NIMG-75 (PMC11553339) **[abs]** | 202 patients: UCSF 48, LUMIERE 67, xCures 13, Cleveland Clinic 74 | Overall survival | Pre- and post-treatment MRI; delta-GLCM of enhancing tumour | Similarity-distance delta radiomics | UCSF and LUMIERE as hold-out tests | LUMIERE C-index 0.65 (HR 1.9, p = 0.0061). UCSF C-index 0.69 | Not stated | Partly (delta radiomics on MU pairs) | + LUMIERE hold-out. − OS not progression; conference abstract |
| **Liu T, Zheng Y, Chen C, … Liu Y. 2025, PHSP-Net**, *Bioengineering* 12(9):978, doi:10.3390/bioengineering12090978 **[abs]** | 1,084 GBM (UPENN-GBM, UCSF-PDGM, LUMIERE, TCGA-GBM) | OS (pre-operative MRI) | Multiparametric MRI habitats | Habitat-aware DL | Internal + 2 external (LUMIERE, TCGA) | Internal AUROC 0.795 (0.731–0.852). LUMIERE external 0.707 | Not stated | No (pre-op, OS) | Uses LUMIERE pre-op scans only |
| **Guo W, Yin C, Giglio P, Cao W, Zhang P, Mirzaei G. 2026, STRIDE**, arXiv:2610.08848 **[abs + partial full]** | LUMIERE used for longitudinal *pretraining* only. Downstream Burdenko | 3-class SD / PsP / TP (Burdenko) | Paired post-treatment MRI + interval | Transformer + time-conditioned transition | Patient-level CV (Burdenko) | Burdenko macro ROC-AUC 0.816, macro F1 0.796 | Not confirmed | No | No LUMIERE result reported |
| **Asfaw ZK, … Germano IM. 2026**, *Neuro-Oncol Adv* 8(1):vdag045, doi:10.1093/noajnl/vdag045 **[abs/page]** | LUMIERE 91 (DeepBraTumIA) + RTOG 0625/ACRIN recurrent-GBM trial n = 123 | Agreement of AI volumetrics (Neosoma HGG) with expert / tumour-board response (PD vs non-PD) | Volumes | Commercial segmentation + rules | — | Cohen's κ = 0.45 (95 % CI 0.28–0.62). Which cohort this κ refers to is not confirmed | No | Rule only | Volumetric rule vs expert agreement is only moderate |
| BraTS-Lighthouse 2025 "Brain Tumor Progression" task **[sec: challenge description via search results]** | LUMIERE = training set; hidden multi-centre test | 4-class RANO between consecutive scans | MRI + HD-GLIO/DeepBraTumIA masks | — | Hidden test | No summary paper found | — | — | A LUMIERE-trained response model with an external hidden test exists as a benchmark; no forward endpoint |

Also using LUMIERE, but not outcome models: Kim JS et al. 2026 *Neurosurg Rev* 49:349 (post-op segmentation / EOR on LUMIERE + RHUH); Lundervold 2026 *J Med Eng Technol* (one LUMIERE patient). Europe PMC also lists Astaraki 2025 *Front Oncol* and Liu 2026 *Bioengineering* 13:179 (pre-op survival models); their abstracts do not confirm LUMIERE use (UNVERIFIED).

---

## 3. Table B — other forward-progression / TTP prediction studies

| Study | Data (n) | Endpoint / horizon / censoring | Inputs | Method | Validation | Headline metric | Code | Re-impl. | Strength / weakness |
|---|---|---|---|---|---|---|---|---|---|
| **Tak D, Garomsa BA, … Kann BH. 2025**, "Longitudinal Risk Prediction for Pediatric Glioma with Temporal Deep Learning", *NEJM AI* 2(5), doi:10.1056/AIoa2400703 **[abs]** | 715 paediatric patients / 3,994 scans, 3 institutions (LGG + HGG) | **1-year recurrence from the last scan**, using prior post-op surveillance scans. Censoring handling not stated in abstract | Serial post-op MRI | Self-supervised temporal ordering pretext + fine-tuning | Multi-institutional (details not in abstract) | AUC "75 to 89 %" across datasets. F1 up to +58.5 % vs traditional. Gains plateau at 3–6 scans | github.com/AIM-KannLab/TemporalLearning_PedsGlioma (per LITERATURE.md) | Partly: MU has ~2 labelled scans per patient; GPU | + closest analogue (forward, fixed horizon, serial). − paediatric; censoring unclear |
| **Yun YC, Jende JME, … Kurz FT. 2025**, "Combined peritumoral radiomics and clinical features predict 12-month progression free survival in glioblastoma", *J Neurooncol* 174:111–120, doi:10.1007/s11060-025-05037-6 **[abs]** | 560 GBM (Stupp), 3 T, single centre | RANO PFS at 6 and 12 months (binary). Censoring not mentioned | Post-treatment MRI (exact timepoint not stated in abstract); 418 radiomic features from CE, NE, peri-CET, NAWM; age, sex, MGMT | Logistic regression | 70/30 split | Peri-CET radiomics AUC 0.61 (0.51–0.70) at 6 mo, 0.71 (0.61–0.81) at 12 mo. Clinical + peri-CET 12 mo: 0.75 (0.65–0.85) | Not stated | **Yes**: shell ROI from our masks + LR | + large n, clinical + radiomics with CIs. − single split; censoring ignored; per-patient |
| **Li Z, Chen L, Song Y, … Bai. 2023 (online 2022)**, *Quant Imaging Med Surg*, doi:10.21037/qims-22-459 **[abs via PMC summary]** | 162 HGG (surgery + adjuvant chemoradiation) | Progression at 6, 9, 12, 15, 18 months (binary per horizon) | **Pre-radiotherapy (post-op) structural MRI** radiomics | ML classifiers | Not confirmed | AUC 0.70, 0.68, 0.78, 0.78, 0.78 for 6/9/12/15/18 months | Not stated | Partly (MU first post-op scan) | + multi-horizon. − protocol unverified; per-patient |
| **Farzana W, … Iftekharuddin KM. 2023**, arXiv:2306.16531 (submitted to MDPI) **[full, first page]** | 70 grade-4 glioma | Rapid early progression (REP) before RT (binary) + survival with dependent-censoring copula | Radiation-planning T1C radiomics + fractal + MGMT/IDH | Random-sampling ensemble | 5-fold CV × 1,000 iterations | AUC 0.793 ± 0.082 | Not stated | No (REP window precedes MU follow-ups) | + addresses dependent censoring for survival. − n = 70, pre-RT window |
| **Pignotti F, Ius T, … Sabatino G. 2024**, *Front Oncol* 14:1449235, doi:10.3389/fonc.2024.1449235 **[abs]** | 248 HGG (188 train / 60 external) | Early (6-month) recurrence | **Pre-operative** T1/T2 radiomics | XGBoost | External validation | AUC 0.72 (0.56–0.87) | Not stated | No (pre-op) | Context only: pre-op, not surveillance |
| **Chen 2026 MambaDiff-Net** (see Table A2) | — | 6-month recurrence | Pre-op + post-op T2 | — | LUMIERE → RHUH external | 0.762 external | — | No on MU | — |
| **Kebaili A, … Ruan S. 2025**, arXiv:2509.10824 **[full, partial]** | Burdenko GBM Progression (cohort of 112 used) + 5 local patients | Pixel-wise future FLAIR / tumour-evolution probability maps | 2 prior follow-ups, RT dose maps | Multi-task diffusion | Public train, private eval | Image/segmentation metrics (not risk) | Not stated | No | Spatial forecasting, not risk |
| **Glazar DJ, … Enderling H. 2025**, *CPT Pharmacometrics Syst Pharmacol* 14:495–509, doi:10.1002/psp4.13290 **[abs]** | **In silico** 2,000 recurrent-HGG patients | Bayesian individual dynamic PFS predictions (landmark) | Simulated longitudinal tumour volumes | Joint tumour-growth-inhibition + survival model | Simulation | AUC / Brier skill vs sample size (no clinical result) | Not stated | Partly (joint-model template on our volume trajectories) | + exactly the dynamic-prediction formulation. − no real data |
| **Cheng C, … Wang X. 2025**, arXiv:2509.01161 **[abs]** | Not stated in abstract | Early post-operative recurrence; C-index, time-dependent AUC, calibration, DCA | Structural MRI + clinical biomarkers | GBM, RSF, CoxBoost, XGBoost | Not stated | **No numbers in abstract** | Not stated | — | Insufficient detail to compare |
| Moon HH et al. — prospective habitat study (CBV/ADC habitats, TTP after CCRT) | Protocol: *BMC Cancer* 2024, doi:10.1186/s12885-024-12939-7 **[abs]** | TTP and site of progression after CCRT (prospective) | Physiologic MRI (DSC, DWI) | k-means habitats | Prospective (enrolment planned to Dec 2025) | Protocol only. The "Moon 2025 *Neuro-Oncol*, 12-month AUC 0.76" cited in our docs is **UNVERIFIED** (not found) | — | No (needs DSC/DWI) | — |

Searched with no qualifying hits: UCSF-ALPTDG forward-risk models (only CLARITY zero-shot survival), RHUH-GBM (only Chen 2026 as external), QIN-GBM, BraTS 2024 post-treatment (segmentation only; ~400 University of Missouri cases overlap MU per arXiv 2405.18368, so this is a leakage risk for any BraTS-2024-pretrained encoder). Hickman-Chow 2026 *J Neurooncol* (pre-op resting-state fMRI, n = 45, LOOCV, PFS R² 0.96) is pre-op and very likely overfit; it is excluded.

---

## 4. Table C — rule baselines and adjacent-task context (brief)

| Study | What it shows | Relevance to us |
|---|---|---|
| **Wen PY et al. 2023, RANO 2.0**, *J Clin Oncol* 41:5187–5199, doi:10.1200/JCO.23.01059 **[abs]** | Post-RT MRI (not post-surgical) is the baseline. Progression within 12 weeks post-RT needs confirmation (repeat MRI or histology). 2-D remains primary; volumetric is optional. Non-enhancing disease is no longer evaluated for IDH-wt GBM (except anti-angiogenic therapy) | Justifies our ≤12-week post-RT flag. A "RANO-2.0-style" volumetric rule (ET increase vs nadir) is a mandatory baseline |
| **Kickingereder P, Isensee F, … Maier-Hein KH. 2019**, *Lancet Oncol* 20:728–740, doi:10.1016/S1470-2045(19)30098-1 **[abs]** | HD-GLIO volumetric TTP was a better OS surrogate than central RANO (HR 2.59 [1.86–3.60] vs 2.07 [1.46–2.92]) in EORTC-26101 (532 patients, 2,034 scans). Reliability 87 % vs 51 % | HD-GLIO (public) can re-segment LUMIERE consistently (our DeepBraTumIA NETC/cavity mismatch). Volumetric rule baseline |
| **Chang K, Beers AL, … Kalpathy-Cramer J. 2019, AutoRANO**, *Neuro-Oncol* 21:1412–1422, doi:10.1093/neuonc/noz106 **[abs]** | Automated volumes / AutoRANO repeatable (ICC 0.986 / 0.991 / 0.977 on double baselines). Longitudinal-change ICC 0.917 / 0.966 / 0.850 | Volume-change rule is reliable enough to be a baseline |
| **Suter 2023** (Table A2) | Automated RANO thresholds vs expert TTP on LUMIERE | Rule baseline on our external set |
| **TRACE 2026 rule oracle** (Table A2) | RANO thresholds (new lesion, ΔV_enh ≥ 40 %, ΔSPD ≥ 25 %) on GT concepts give binary macro F1 0.681 ± 0.058 on LUMIERE | Upper bound for a pure measurement rule on concurrent labels |
| **Heugenhauser J, … Nowosielski M. 2026**, *Neuro-Oncol Adv* 8:vdag032, doi:10.1093/noajnl/vdag032 **[abs]** | Volumetric RANO / mRANO / RANO 2.0 on 137 GBM: median PFS 7.9 / 11.3 / 9.7 months. RANO 2.0 strongest landmark HR (3.6) | Label sensitivity: the progression definition shifts PFS by months; supports our MU-vs-LUMIERE label caveat |
| **Shi T, Kujawa A, Linares C, Vercauteren T, Booth TC. 2025**, *Neuro-Oncol*, doi:10.1093/neuonc/noaf037 **[abs]** | Systematic review of automated longitudinal response assessment: 20 studies (17 retrospective), high bias risk, no meta-analysis possible | Field lacks external validation against current criteria |
| **Booth TC, Grzeda M, … Ourselin S. 2022**, *Front Oncol* 12:799662, doi:10.3389/fonc.2022.799662 **[abs]** | ML for progression vs mimics (18 studies, 1,335/384 train/test patients): pooled sens 0.769, spec 0.648, ROC-AUC 0.765; high bias risk | Adjacent task. Explains why PsP AUCs ≠ our forward AUCs |
| **Kim JY, Park JE, … Kim HS. 2019**, *Neuro-Oncol* 21:404–414, doi:10.1093/neuonc/noy133 **[abs]** | PsP radiomics (61 + 34 ext + 23 prosp.): multiparametric AUC 0.90 vs conventional-MRI-only 0.76 | Conventional MRI alone is weaker; we only have conventional MRI |
| **Gomaa A, … Putz F. 2025**, *Sci Rep* 15:17133, doi:10.1038/s41598-025-02026-7 **[abs]** | PsP vs TP; Burdenko (n = 59) → Erlangen (n = 20): AUC 75.3 %; uses RT plan + clinical | Small external test; clinical / RT info helps, as in our results |
| **Guo W, Mirzaei G. 2026**, *Cancers* 18(1):36, doi:10.3390/cancers18010036 (arXiv 2511.18595) **[full]** | 11 DL families on Burdenko (n = 180), patient-level CV: accuracy ~0.70–0.74. Best AUC 0.57 (3D-ViT, 1st FU), 0.66 (2D-Mamba+CNN, 2nd FU) | Anatomical-only imaging DL is weak on public post-treatment data. (Our PUBLICATION_PLAN says "0.57–0.63"; the paper says 0.57 / 0.66, so it needs correcting) |
| Li 2026 *Cancers* (Table A1) | PsP AUC 0.935 with diffusion / perfusion channels; survival ≈ chance | Same pattern: state labels are easier than prognosis |

---

## 5. Re-implementable baselines under our exact protocol

Protocol for all: our MU grade-4 cohort and 120-d censoring-aware label; 5 × 5 repeated patient-grouped folds (D7); IPCW AUC(120 d), Brier, O/E, slope. Then a locked model on LUMIERE (132 scans / 61 patients), plus recalibrated / fine-tuned arms.

| # | Baseline (source) | What it needs from our data | Have it? | Effort |
|---|---|---|---|---|
| B0 | **Persistence / prior-trend** (Jung & Shin 2026 persistence idea). Score = current ET volume, or ΔET vs previous scan | ET volume per timepoint; previous scan | Yes (measurement table, C2) | < 0.5 day |
| B1 | **Volumetric RANO-style rule** (RANO 2.0; Kickingereder 2019; Chang 2019; TRACE oracle thresholds). Flag = ΔET vs nadir ≥ 40 % (volumetric analogue of 25 % 2-D) or new lesion; post-RT baseline; ≤12-wk window flagged. Report as binary rule and as continuous %-change score | ET/NETC volumes over time; RT end date; nadir tracking. New-lesion detection needs connected components | Mostly. New-lesion count from masks is to build. LUMIERE: rerun HD-GLIO for consistent masks | 1 day (+1 day HD-GLIO on LUMIERE) |
| B2 | **Christodoulou 2026**: PyRadiomics (orig + LoG σ 0.5–3 + wavelet) → stability ranking → LightGBM + Optuna → Platt | T1/T1c/T2/FLAIR + refined masks; our label instead of "status" | Yes (C3 corrected radiomics pipeline) | 1 day CPU (already planned, PIPELINE_REVIEW §5) |
| B3 | **Rai 2026**: (a) recompute *their* label (≥25 % volume increase at next scan, consecutive non-leaky pairs) and reproduce ~0.73 under nested grouped CV; (b) run their anchor ensemble (LR / XGBoost / CatBoost + patient-level bagging) on *our* endpoint | Consecutive pairs, total tumour volume, radiomics, "time-safe" clinical events | Yes | 1–2 days (skip uncertainty-gated residual stage initially) |
| B4 | **Hashim 2026**: Cox(active tumour volume + age + grade + IDH + MGMT), scored as 120-d risk; C-index + AUC(120) | Volumes, clinical codes, time-to-progression with censoring | Yes (lifelines / sksurv in env) | 0.5 day |
| B5 | **Yun 2025**: radiomics from CE, NE, **peritumoral shell** (peri-CET), NAWM + age/sex/MGMT → logistic regression | Masks for shell / NAWM construction (dilation minus lesion, brain mask) | Yes (masks; brain mask from skull-strip) | 1 day |
| B6 | **Tikhonov 2025 (handcrafted part)**: volumes, Δ vs nadir, growth / shrinkage-mask radiomics, centroid shift → CatBoost (skip ResNet-18) | Registered consecutive scans (MU in a common space?), masks | Partly: needs prior scan for each index scan (first follow-ups lack one → missing-indicator) | 2–3 days |
| B7 | **Tak 2025 temporal SSL** (public code): scan-order pretext on all 594 MU timepoints, fine-tune for 120-d risk | Serial images per patient; GPU | Partly: median ~2 labelled scans / patient; LUMIERE lacks treatment fields but has images | 1–2 weeks GPU; optional / negative control |
| B8 | **TRACE concept bottleneck** (public code), with the 4-class RANO head replaced by a 120-d risk head | Paired scans + masks; GPU | Partly | ~1 week; optional |

Not re-implementable on our data: Chen 2026 (needs pre-op MRI, absent in MU); CLARITY (heavy generative world model, treatment-recommendation target); Li 2026 *Cancers* and Kim 2019 (need diffusion / perfusion and PsP labels); Moon (DSC / DWI habitats); Matoso / Amato (4-class concurrent RANO; Matoso code exists but the task differs).

Suggested minimal ladder for the paper: **B0 → B1 → B4 → B3(b) → B2 → B5**, plus our clinical + timing + treatment model. Add B3(a) as a separate "reproduction of a published MU number" row. B6–B8 are optional.

---

## 6. References

MU-Glioma-Post / LUMIERE datasets
- Yaseen D, Garrett F, Gass J, et al. University of Missouri Post-operative Glioma Dataset (MU-Glioma-Post), TCIA 2025. https://doi.org/10.7937/7K9K-3C83
- Mahmoud E, Gass J, Dhemesh Y, et al. MU-Glioma Post. *Sci Data* 2025;12:1847. https://doi.org/10.1038/s41597-025-06011-7
- Suter Y, Knecht U, Valenzuela W, et al. The LUMIERE dataset. *Sci Data* 2022. https://doi.org/10.1038/s41597-022-01881-7

Table A
- Christodoulou RC, et al. *Eur J Radiol AI* 2026;5:100074. https://doi.org/10.1016/j.ejrai.2026.100074 (abstract: https://scholarship.miami.edu/esploro/outputs/journalArticle/Explainable-radiomics-with-probability-calibration-for/991032989340302976)
- Rai AK. *J Intell Decis Mak Inf Sci* 2026;3. https://doi.org/10.59543/jidmis.v3.2236
- Hashim U, Jalal A, Jabali AN, Rana H. *Cureus* 2026;18(7):e112298. https://doi.org/10.7759/cureus.112298 (PMID 42569793)
- Ding T, Zou Y, Chen C, Shah M, Tian Y. CLARITY. arXiv:2512.08029. https://arxiv.org/abs/2512.08029
- Jung Y, Shin M. arXiv:2609.12435. https://arxiv.org/abs/2609.12435
- Li ID, Correia C, Ung CY. *Cancers* 2026;18:3015. https://doi.org/10.3390/cancers18183015 (PMID 42794981)
- Christodoulou RC, et al. *Front Oncol* 2026;16:1790776. https://doi.org/10.3389/fonc.2026.1790776; *Front Oncol* 2026;16:1900609. https://doi.org/10.3389/fonc.2026.1900609
- Suter Y, Notter M, Meier R, et al. *Front Radiol* 2023;3:1211859. https://doi.org/10.3389/fradi.2023.1211859
- Matoso A, et al. arXiv:2504.18268. https://arxiv.org/abs/2504.18268 ; ISMRM 2025 #1301 https://archive.ismrm.org/2025/1301.html
- Amato D, et al. IEEE BIBM 2025. https://doi.org/10.1109/BIBM66473.2025.11356532
- Tikhonov D, et al. arXiv:2509.06511. https://arxiv.org/abs/2509.06511
- Tarek A, et al. TRACE. arXiv:2606.30313. https://arxiv.org/abs/2606.30313
- Chen C, et al. *Bioengineering* 2026;13(6):668. https://doi.org/10.3390/bioengineering13060668 (PMID 42351913)
- Pineda G, et al. SDDR, *Neuro-Oncology* 2024 suppl. NIMG-75. https://pmc.ncbi.nlm.nih.gov/articles/PMC11553339/
- Liu T, et al. PHSP-Net. *Bioengineering* 2025;12(9):978. https://doi.org/10.3390/bioengineering12090978
- Guo W, et al. STRIDE. arXiv:2610.08848. https://arxiv.org/abs/2610.08848
- Asfaw ZK, et al. *Neuro-Oncol Adv* 2026;8(1):vdag045. https://doi.org/10.1093/noajnl/vdag045
- Kim JS, et al. *Neurosurg Rev* 2026;49:349. https://doi.org/10.1007/s10143-026-04255-4
- BraTS 2025 Brain Tumor Progression challenge description. https://zenodo.org/records/15094823

Table B
- Tak D, et al. *NEJM AI* 2025;2(5). https://doi.org/10.1056/AIoa2400703 (PMID 40535328)
- Yun YC, et al. *J Neurooncol* 2025;174:111–120. https://doi.org/10.1007/s11060-025-05037-6 (PMID 40244521)
- Li Z, et al. *Quant Imaging Med Surg* 2023. https://doi.org/10.21037/qims-22-459 (PMC9816734)
- Farzana W, et al. arXiv:2306.16531. https://arxiv.org/abs/2306.16531
- Pignotti F, et al. *Front Oncol* 2024;14:1449235. https://doi.org/10.3389/fonc.2024.1449235
- Kebaili A, et al. arXiv:2509.10824. https://arxiv.org/abs/2509.10824
- Glazar DJ, et al. *CPT Pharmacometrics Syst Pharmacol* 2025;14:495–509. https://doi.org/10.1002/psp4.13290
- Cheng C, et al. arXiv:2509.01161. https://arxiv.org/abs/2509.01161
- Moon HH, et al. (protocol) *BMC Cancer* 2024. https://doi.org/10.1186/s12885-024-12939-7
- de Verdier MC, et al. BraTS 2024 post-treatment. arXiv:2405.18368. https://arxiv.org/abs/2405.18368

Table C
- Wen PY, et al. RANO 2.0. *J Clin Oncol* 2023;41:5187–5199. https://doi.org/10.1200/JCO.23.01059
- Kickingereder P, et al. *Lancet Oncol* 2019;20:728–740. https://doi.org/10.1016/S1470-2045(19)30098-1
- Chang K, et al. *Neuro-Oncol* 2019;21:1412–1422. https://doi.org/10.1093/neuonc/noz106
- Heugenhauser J, et al. *Neuro-Oncol Adv* 2026;8:vdag032. https://doi.org/10.1093/noajnl/vdag032
- Shi T, et al. *Neuro-Oncol* 2025. https://doi.org/10.1093/neuonc/noaf037
- Booth TC, et al. *Front Oncol* 2022;12:799662. https://doi.org/10.3389/fonc.2022.799662
- Kim JY, et al. *Neuro-Oncol* 2019;21:404–414. https://doi.org/10.1093/neuonc/noy133
- Gomaa A, et al. *Sci Rep* 2025;15:17133. https://doi.org/10.1038/s41598-025-02026-7
- Guo W, Mirzaei G. *Cancers* 2026;18(1):36. https://doi.org/10.3390/cancers18010036

## Corrections to earlier repo docs found during verification
- `PUBLICATION_PLAN.md` A5: Rai 2026 is *J Intell Decis Mak Inf Sci* (JIDMIS); the AUC 0.728 is confirmed. The label is volume-derived (≥25 %).
- `PUBLICATION_PLAN.md` B1: Guo & Mirzaei best AUCs are 0.57 (1st FU) and 0.66 (2nd FU), not "0.57–0.63".
- `LITERATURE.md` §0: the authors of Li 2026 *Cancers* 18:3015 are Li ID, Correia C, Ung CY (PubMed).
- "Moon 2025 *Neuro-Oncol*" (12-month AUC 0.76) could not be found. Only the 2024 *BMC Cancer* protocol was found. Treat it as UNVERIFIED.
- Christodoulou 2026: the full text was not accessible (403). The 30-patient / 96-scan test size comes from our repo, not re-verified.
