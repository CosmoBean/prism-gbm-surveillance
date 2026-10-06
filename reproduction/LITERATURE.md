# Literature Review: Comparative Methods & Novelty Directions

Compiled 2026-10-05 from three verified web-search reviews (≈ 110 sources). Every entry was confirmed against a search result or fetched page; numbers are "as reported" — re-check in the PDF before citing. **[pv]** = partially verified.

---

## 0. Prior work on MU-Glioma-Post (novelty check)

| Paper | Task | Overlap with us |
|---|---|---|
| Christodoulou et al. 2026, *Eur J Radiol AI* — [10.1016/j.ejrai.2026.100074](https://doi.org/10.1016/j.ejrai.2026.100074) (the reproduced baseline) | Binary post-op surveillance, LightGBM + Platt + SHAP, single split, AUC 0.80 | **Same task & AUC** — "radiomics + calibration on MU" is no longer novel |
| Hashim et al. 2026, *Cureus* — [10.7759/cureus.112298](https://doi.org/10.7759/cureus.112298) | Per-patient PFS (Cox), MU = discovery; external UCSD-PTGBM/UPenn | Closest "MU + external validation"; per-patient, not per-scan |
| Jung & Shin 2026, arXiv — [2609.12435](https://arxiv.org/abs/2609.12435), [code](https://github.com/jsudg436/longitudinal-proxy-forecasting) | Voxel-wise longitudinal tumor-state forecasting | Uses MU longitudinally; no gain over persistence baseline; not risk prediction |
| Li et al. 2026, *Cancers* 18:3015 — [10.3390/cancers18183015](https://doi.org/10.3390/cancers18183015) **[pv]** (author list inconsistent across sources) | Recurrence vs pseudoprogression, MU used for encoder pretraining | Different task |
| Christodoulou et al. 2026 (IDH/MGMT CNN; PTEN radiomics), Crişan & Borza 2026 (segmentation), Lteif et al. 2025 | Molecular / segmentation | Not progression |

**No published forward, fixed-horizon, per-scan progression model on MU-Glioma-Post with external validation or censoring-aware formulation was found.**

---

## 1. Image encoder (replaces the "SWIN" branch)

**Evidence:** independent benchmarks find **frozen encoders + simple heads** beat fine-tuning at < 500 scans; **2D slice encoders on lesion-guided slices beat 3D brain foundation models**; **radiomics + TabPFN beats all image FMs** for glioma IDH.

| Model | Pretraining | Input fit | Weights / license | Independent glioma result |
|---|---|---|---|---|
| BiomedCLIP ([2303.00915](https://arxiv.org/abs/2303.00915), [HF](https://huggingface.co/microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224)) | PMC-15M 2D | 2.5D lesion slices | Yes / MIT | **Best image FM for IDH: 0.85 (ext 0.74)** — Hollet 2026 |
| DINOv2-L / DINOv3 ([dinov2](https://huggingface.co/facebook/dinov2-large), [dinov3](https://github.com/facebookresearch/dinov3)) | Natural images | 2.5D | Apache / gated | Weak with whole-slice pooling; needs ROI pooling |
| BrainMVP, CVPR 2025 ([2410.10604](https://arxiv.org/abs/2410.10604), [code](https://github.com/openmedlab/BrainMVP)) | 16k scans, 8 sequences incl. gliomas | 96³ @1 mm, per sequence | Yes / unstated | Best 3D brain FM: IDH 0.68 / 0.82 (10 / 100 % labels) |
| BM-MAE ([2505.00568](https://arxiv.org/abs/2505.00568), [code](https://github.com/Lucas-rbnt/BM-MAE)) | BraTS21 | **Exact match: T1/T1c/T2/FLAIR, 128³ @1 mm**, missing-modality tolerant | Yes (HF) | IDH 0.60–0.63 |
| BrainSegFounder, MedIA 2024 ([2406.10395](https://arxiv.org/abs/2406.10395), [HF](https://huggingface.co/smilelab/BrainSegFounder)) | UKB 41k + BraTS | **Same SwinUNETR as ours** → clean pretraining-source ablation | Yes / UKB MTA | Segmentation only |
| BrainIAC, Nat Neurosci 2026 ([paper](https://www.nature.com/articles/s41593-026-02202-6), [code](https://github.com/AIM-KannLab/BrainIAC)) | ~32k brain MRI, SimCLR ViT-B | 1 channel, 96³ MNI | Yes / non-commercial | Own paper IDH 0.79; **independent 0.58** — reference baseline |
| BrainDINO ([2604.27277](https://arxiv.org/abs/2604.27277)) | 6.6M brain slices | 2D | **Not released** | Strongest frozen brain FM (IDH 0.86–0.90) |
| MONAI BraTS21 SwinUNETR (ours) | BraTS21 | 4 ch, 128³ | Yes | Our image-only test AUC ≈ 0.64 |

**Key supporting findings**
- *Frozen FM embeddings discard small-lesion signal; ROI-token pooling recovers it* — Muthyala 2026 ([2606.11606](https://arxiv.org/abs/2606.11606)), 2D CXR only. Matches our global-pool collapse (scan-scan corr ≈ 1.0).
- Mean-pooling frozen slice embeddings ≥ attention-MIL & 3D CNNs on 4/6 neuroimaging tasks — Harvey 2026 ([2604.26807](https://arxiv.org/abs/2604.26807)).
- Frozen brain-FM embeddings encode acquisition site (~0.9 balanced acc) — Rahbar 2026 ([2608.10295](https://arxiv.org/abs/2608.10295)); needs a confound check.
- **Leakage warning:** BraTS 2024 post-treatment includes ~400 University of Missouri cases ([2405.18368](https://arxiv.org/abs/2405.18368)) — any BraTS-2024-pretrained encoder must be deduplicated against MU. (BraTS21 weights are pre-op data.)

## 2. Fusion (replaces `fusion_mlp.py`)

**Evidence:** in GBM, deep-imaging gains over clinical are ≤ 0.04 C-index/AUC even at n = 780; trees/linear models beat deep tabular models at small n.

| Method | Ref / code | Use for us |
|---|---|---|
| Stacking / late fusion with strong tabular model | — | **Primary**: penalised logistic/Cox or TabPFN on [radiomics, clinical, image score/PCs] |
| TabPFN | Hollmann 2025 *Nature* | Strong small-n baseline/fusion head |
| DAFT / FiLM conditioning | Wolf 2022 [2107.05990](https://arxiv.org/abs/2107.05990), [code](https://github.com/ai-med/DAFT); Perez 2018 | Clinical (age, MGMT, IDH) conditions frozen image features; cheap |
| Pathomic Fusion (gated/tensor) | Chen 2020 TMI, [code](https://github.com/mahmoodlab/PathomicFusion) | Gated variant with radiomics skip path only; tensor fusion overfits |
| TIP (masked tabular pretraining) | Du 2024 ECCV, [code](https://github.com/siyi-wind/TIP) | Principled handling of missing/"not tested" molecular codes |
| Cross-attention SSL ViT + clinical, GBM | Gomaa 2024 *NOA* ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11327617/), [code](https://gitlab.com/ai-radiomics/Survival-Prediction)) | Shows fused − clinical = +0.003…+0.04 C-index |
| DL features as LASSO covariates with radiomics | Zheng 2026 *Neuroradiology*; BraTS-Lighthouse 2025 (ResNet + radiomics + CatBoost) | Alternative to end-to-end branch |
| Reviews: deep vs generic radiomics | Demircioğlu 2022 *Insights Imaging* | External gain of deep models ≈ +0.025 AUC |

## 3. Longitudinal modelling (unused so far — MU has ~3.8 scans/patient)

| Method | Ref / code | Notes |
|---|---|---|
| **Temporal learning (scan-order SSL) + serial-scan pooling** | Tak 2025 *NEJM AI* ([10.1056/AIoa2400703](https://doi.org/10.1056/AIoa2400703)), [code](https://github.com/AIM-KannLab/TemporalLearning_PedsGlioma) | Closest analogue (pediatric, 1-yr recurrence; AUC 0.75–0.89; gains plateau at 3–6 scans). **No adult/GBM equivalent found** |
| LTSA: transformer with time-since-baseline encoding + discrete-time survival head | Holste 2024 *npj Digit Med*, [code](https://github.com/bionlplab/longitudinal_transformer_for_survival_analysis) | Best open template for serial MRI → censored time-to-progression |
| tdCoxSNN (neural time-dependent Cox) | Zeng 2025 JRSS-C, [code](https://github.com/langzeng/tdCoxSNN) | Longitudinal images as time-varying covariates |
| Dynamic-DeepHit | Lee 2019 TBME, [code](https://github.com/chl8856/Dynamic-DeepHit) | Competing risks (death before progression) |
| Time-aware LSTM | Baytas 2017 KDD, [code](https://github.com/illidanlab/T-LSTM) | Irregular intervals |
| Siamese / feature-difference (pre/post-op) | Chen 2026 *Bioengineering* — LUMIERE train → RHUH external 0.762 | Change features; public-data external validation precedent |
| Delta-radiomics / habitats | Moon 2025 *Neuro-Oncol* (needs DWI/DSC); Fave 2017 (delta added little in NSCLC) | Must be tested, not assumed |
| Benchmark of 11 DL architectures, Burdenko | Guo & Mirzaei 2026 *Cancers* | All ≈ 0.70–0.74 → formulation > architecture |

## 4. Outcome formulation (fixes censored negatives)

| Approach | Ref / library |
|---|---|
| **Landmarking: each scan = landmark, horizon τ = 120 d** | van Houwelingen 2007; Putter & van Houwelingen 2022 (Landmarking 2.0); R `dynpred` |
| Discrete-time hazard (person-period) = reuse logistic regression | Suresh 2022 *BMC MRM*; Kvamme & Borgan 2021; `pycox` LogisticHazard |
| IPCW-weighted binary label (minimal fix) | Vock 2016 *J Biomed Inform* |
| Cox with patient clustering | `lifelines` CoxPHFitter (`cluster_col`, `entry_col`) |
| No method significantly beat Cox on low-dim data | Burk 2026 *Bioinformatics* (34 datasets, 21 models) |
| Metrics: IPCW AUC(120 d), Uno's C, Brier/IBS | `scikit-survival`; `timeROC`; Blanche 2013; Uno 2011 |

## 5. Evaluation & reporting

- Nested, patient-grouped CV (Varma & Simon 2006); small-n error bars (Varoquaux 2018); avoid single split (Collins 2024 BMJ).
- Patient-cluster bootstrap (Field & Welsh 2007); clustered AUC (Obuchowski 1997) instead of DeLong.
- Calibration (Van Calster 2019; STRATOS 2025), DCA incl. censored (Vickers 2006/2008), stability plots (Riley & Collins 2023, `pminternal`), sample size (`pmsampsize`).
- Leakage taxonomy (Kapoor & Narayanan 2023); subject-level split inflation 30–55 % (Yagis 2021).
- Reporting: **TRIPOD+AI** (2024), **CLAIM 2024**, **METRICS** (2024), RQS 2.0, IBSI; **TRIPOD-LLM** if the report agent is included.
- Interpretability: SHAP misattributes with correlated radiomics (Aas 2021) → grouped/conditional Shapley (`shapr`) or exact logistic contributions; attention ≠ explanation (Jain & Wallace 2019); saliency maps unreliable (Arun 2021).

## 6. Automated response assessment (for the agent's "RANO" section)

| Ref | Finding |
|---|---|
| Kickingereder 2019 *Lancet Oncol*, HD-GLIO ([code](https://github.com/NeuroAI-HD/HD-GLIO)) | Volumetric TTP a better OS surrogate than central RANO |
| Chang 2019 *Neuro-Oncol* (AutoRANO) | Automated volumetric change more reliable than bidimensional |
| Suter 2023 *Front Radiol* ([code](https://github.com/ysuter/gbm-longitudinaleval)) on LUMIERE | 81 % trend agreement with expert SPD; cavity causes false positives |
| Wen 2023 RANO 2.0 *JCO* | Post-RT scan = baseline; confirmation scans |
| Heugenhauser 2026 *NOA* | PFS shifts ~3 months between RANO / mRANO / RANO 2.0 → label sensitivity |

## 7. External validation datasets

| Dataset | Size | Labels | Fit |
|---|---|---|---|
| **LUMIERE** ([Sci Data 2022](https://doi.org/10.1038/s41597-022-01881-7), CC BY 4.0) | 91 GBM, 638 dates | Expert RANO per timepoint, OS | **Best**: same 4 sequences, serial; 120-d label derivable |
| **Burdenko-GBM-Progression** ([TCIA](https://doi.org/10.7937/E1QP-D183)) | 180 GBM, 645 studies | Per-study progression / PsP, IDH/MGMT | Good; needs segmentation |
| CFB-GBM v2.0 ([2608.17884](https://arxiv.org/abs/2608.17884), TCIA) | 264 GBM | Volumetric RANO 2.0 at fixed intervals | New, strong candidate |
| UCSD-PTGBM ([Sci Data](https://doi.org/10.1038/s41597-025-06499-z)) | 178 pts | Same 4-label scheme; tumor vs TRC; PFS subset | PsP task / PFS check |
| UCSF-ALPTDG ([Radiol AI 2024](https://doi.org/10.1148/ryai.230182)) | 298 × 2 tps | Change masks | 2 timepoints only |
| RHUH-GBM | 40 | PFS/OS | Small |

---

## 8. Ranked novelty directions for this project

| Rank | Direction | Why novel (evidence) | Feasibility with current code/data | Risk |
|---|---|---|---|---|
| **1** | **Censoring-aware dynamic (landmark) prediction of 120-day progression from serial post-op MRI**, compared head-to-head with the naive binary label | Reviews state GBM-recurrence radiomics uses single timepoints and binary endpoints; baseline is single-split binary; no landmark/discrete-time per-scan GBM study found | **High** — reuses radiomics features + logistic code; `lifelines`/`scikit-survival` | Low |
| **2** | **Compartment-resolved & longitudinal (delta) features incl. resection cavity** — radiomics and frozen-encoder tokens pooled per NETC/SNFH/ET/RC + peri-cavity shell, and their change from prior scan/nadir | MU uniquely provides refined cavity masks; no cavity-compartment time-varying covariate study found; no 3D study of global vs lesion vs compartment pooling | **High** — masks, crops, lesion pooling already built | Medium (signal may be modest) |
| **3** | **External validation on LUMIERE (± Burdenko / CFB-GBM)** with harmonised 120-day label | No MU forward-prediction model externally validated | Medium — download + segment (HD-GLIO / our stage-1 SwinUNETR) + label harmonisation | Medium |
| **4** | **Benchmark of frozen brain-MRI foundation encoders for post-op progression** (BiomedCLIP/DINOv2 2.5D, BrainMVP, BM-MAE, BrainSegFounder, BrainIAC, ours) under one leakage-free protocol | No FM benchmark on post-op progression; FOMO25 had no glioma/post-op tasks | Medium — feature-extraction only, GPU hours modest | Likely a rigorous **negative/neutral** result — still publishable |
| **5** | **Label-definition sensitivity** (naive vs IPCW vs landmark; imaging-only vs any progression; RANO 2.0 post-RT baseline) | No imaging paper quantifies censored-negative bias explicitly | High | Low |
| **6** | **Temporal SSL (Tak-style scan ordering) on all 594 MU timepoints**, adult GBM | Only pediatric precedent | Medium — code public | Medium–high (n small) |

**Suggested paper framing (combining 1 + 2 + 5, with 3 or 4 as the second contribution):**
*"Dynamic, censoring-aware prediction of short-term progression from serial post-operative glioblastoma MRI using compartment-resolved features"* — landmark discrete-time hazard on MU-Glioma-Post, cavity/compartment + delta features, honest nested patient-clustered evaluation (IPCW AUC(120 d), calibration, DCA, stability), label-sensitivity analysis, external validation on LUMIERE, and a controlled test of whether frozen foundation-encoder features add value. Report per TRIPOD+AI / CLAIM 2024 / METRICS.

## 9. Caveats

- Several 2026 items are preprints; verify venue/status at submission.
- Unverified/missing: code for HyperFusion, Christodoulou 2026, Guo 2026, Gomaa 2025; exact TabPFN/TorchSurv repo paths; authorship of *Cancers* 18:3015.
- Baseline paper's abstract reports **LightGBM**; our repo's shipped model is LogReg-48 — state clearly which is compared.
