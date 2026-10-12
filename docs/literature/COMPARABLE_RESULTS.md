# Comparable results: post-treatment glioma progression prediction

Compiled 2026-10-11. This file extends `docs/literature/RELATED_WORK.md`, `docs/literature/comparison.md` and `docs/manuscript/LITERATURE_TABLE.md`. Every number below was read in a primary source during this pass: the Europe PMC / PubMed abstract, the publisher full text, or the arXiv abstract/HTML. The **Src** column records which:

- **abs**: abstract read this pass.
- **full**: full text (PMC, publisher or arXiv HTML) read this pass.
- **repo**: taken from `comparison.md` and not re-read this pass. These rows are marked "unverified (this pass)".

Metrics are copied as reported. They are **not on one axis**: endpoints differ (forward risk, concurrent state, PsP vs TP, survival), and so do units (scan, scan pair, patient) and validation designs.

**Our reference point.** Each post-treatment MRI, progression within 120 days, censoring-aware. Clinical + treatment-course model: AUC about 0.70 (repeated patient-grouped CV). Radiomics and deep features add nothing. Post-chemoradiation scans only: 0.55–0.66. External LUMIERE: 0.61–0.66.

Column key: **MRI** = conventional (T1/T1c/T2/FLAIR) vs advanced (DWI/ADC, DSC/DCE perfusion). **Clin-only?** = was a clinical-only baseline reported, and its value.

---


> **Task caveat.** Several of the closest clinical-vs-imaging comparisons (Leone 2023, Gomaa 2025, the section C meta-analyses)
> are *pseudoprogression vs true progression* classifiers on an already-suspicious lesion, often with ADC/CBV. Our task is
> forward prediction (progression documented within 120 d) from *every* surveillance scan, conventional MRI only. Their
> AUCs are context, not like-for-like comparators; the like-for-like ones are sections A and B.

## A. Studies on MU-Glioma-Post or LUMIERE

| Study | Link | Task | n | MRI | Validation | Headline (internal / external) | Clin-only? | Src |
|---|---|---|---|---|---|---|---|---|
| Christodoulou et al. (2026), *Eur J Radiol AI* 5:100074 | [doi](https://doi.org/10.1016/j.ejrai.2026.100074) | MU: progression *status* per post-op scan | not in abstract | Conv. (T1, T1c, T2, FLAIR) radiomics, LightGBM + Platt | Patient-aware 5-fold CV for tuning; one held-out patient test set | AUC 0.80 (test); Brier 0.093 → 0.088; 16 FP / 6 FN. No external test | No | abs |
| Rai (2026), *J Intell Decis Mak Inf Sci* 3 | [doi](https://doi.org/10.59543/jidmis.v3.2236) | MU: ≥25 % volume increase at next scan (volume-derived label) | 391 pairs / 155 pts | Conv. radiomics + "time-safe" clinical events | Nested patient-grouped CV | OOF AUC 0.728 (0.678–0.777) vs reference 0.713 | Unclear | repo, unverified (this pass) |
| Hashim et al. (2026), *Cureus* 18(7):e112298 | [doi](https://doi.org/10.7759/cureus.112298) | MU: per-patient PFS (Cox); external volume / radiomic score checks | MU 194 (152 progressed); total 1,447 across 4 cohorts | Conv.; segmentation volumes, radiomic score | Discovery (MU) + external cohorts (UCSD-PTGBM, UCSF-PDGM, UPenn) | MU active-tumour volume adjusted for age/grade/IDH/MGMT: C-index 0.676. UCSD enhancing volume not significant for PFS (p = 0.191) | Adjusted only; no separate clinical C-index in abstract | abs |
| Chen et al. (2026), *Bioengineering* 13(6):668 | [doi](https://doi.org/10.3390/bioengineering13060668) | Recurrence ≤6 mo after surgery (pre- + post-op MRI) | 139 (LUMIERE train 59 / internal 40 / RHUH external 40) | Conv. (T2 only), DL | Train / internal / external | AUC 0.887 internal → 0.762 external | No | abs |
| Pineda et al. (2024), *Neuro-Oncology* 26(Suppl 8), NIMG-75 | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11553339/) | Overall survival from pre/post-treatment delta radiomics | 150 reported in the abstract text (UCSF 48, LUMIERE 67, 2 proprietary) | Conv. (T1c GLCM delta) | UCSF and LUMIERE held out | C-index LUMIERE 0.65, UCSF 0.69 | No | full (abstract page) |
| Tikhonov et al. (2025), arXiv:2509.06511 | [arXiv](https://arxiv.org/abs/2509.06511) | LUMIERE: 4-class RANO of a scan pair (concurrent, not forward) | LUMIERE | Conv. radiomics + ResNet-18; CatBoost | 5-fold patient-wise CV (per repo full-text read) | Mean ROC-AUC 0.81, macro F1 0.50. Volumes-only AUC 0.59 (repo, unverified this pass) | No | abs + repo |
| Suter et al. (2024), LNCS 14668:36–47 | [doi](https://doi.org/10.1007/978-3-031-76160-7_4) | Automated progression classification from longitudinal radiomics | **unverified** (dataset not named in the abstract; likely LUMIERE-type Bern data) | Conv. radiomics (current + change) | **unverified** | Best ROC-AUC 0.748 (RF); best F1 0.792 (XGBoost, current + change features) | No | abs |
| Ding et al. (2025), CLARITY, arXiv:2512.08029 | [arXiv](https://arxiv.org/abs/2512.08029) | MU: survival + treatment recommendation (world model) | 203 pts / 654 follow-ups | Conv. latents + intervals + clinical | Patient-level 75/15/15 + 5-fold; zero-shot UCSF-ALPTDG | C-index 0.794 (DeepSurv 0.664) | No | repo, unverified (this pass) |

## B. Forward progression / outcome from post-treatment (follow-up) MRI

| Study | Link | Task | n | MRI | Validation | Headline (internal / external) | Clin-only? | Src |
|---|---|---|---|---|---|---|---|---|
| Yun et al. (2025), *J Neurooncol* 174:111–120 | [doi](https://doi.org/10.1007/s11060-025-05037-6) | RANO PFS at 6 and 12 mo from post-treatment MRI | 560 GBM (Stupp) | Conv. 3 T; radiomics from CET, NE, peri-CET, NAWM; LR | Single 70/30 split | Peri-CET radiomics AUC 0.61 (0.51–0.70) at 6 mo, 0.71 (0.61–0.81) at 12 mo. Clinical + peri-CET at 12 mo: 0.75 (0.65–0.85) | A clinical-only model (age, sex, MGMT) was trained, but its AUC is **not in the abstract (unverified)** | abs |
| Li et al. (2023), *Quant Imaging Med Surg* | [doi](https://doi.org/10.21037/qims-22-459) | Progression at 6/9/12/15/18 mo after RT | 162 HGG | Conv. (T1, T1c, T2, FLAIR) on **pre-RT planning MRI** | Not stated in the abstract | Best (clinical + GTV/CTV T2/FLAIR radiomics): 0.70 / 0.68 / 0.78 / 0.78 / 0.78 | Not in the abstract | abs |
| Tak et al. (2025), *NEJM AI* 2(5) | [doi](https://doi.org/10.1056/AIoa2400703) | 1-year recurrence from the last surveillance scan (paediatric LGG + HGG) | 715 pts / 3,994 scans, 3 institutions | Conv. serial MRI; temporal self-supervised DL | Multi-institution (details not in the abstract) | AUC 75–89 % across datasets; gains plateau at 3–6 prior scans | Compared with "traditional approaches" (F1 +6.6 to +58.5 %); no clinical-only AUC | abs |
| Balakumaran et al. (2026), Proc. SPIE | [doi](https://doi.org/10.1117/12.3088139) | OS and treatment response from delta radiomics of 2 consecutive post-treatment scans | 298, single institution (cohort size matches UCSF-ALPTDG; **unverified**) | Conv. (T1, T1c, T2, FLAIR) | Cox-L2; RF with CV; no external test | Survival C-index 0.80; response CV accuracy 0.731 | No | abs (repository page) |
| Kickingereder et al. (2019), *Lancet Oncol* 20:728–740 | [doi](https://doi.org/10.1016/S1470-2045(19)30098-1) | Automated volumetric TTP as OS surrogate | 532 pts / 2,034 scans (EORTC-26101) external | Conv. (ANN segmentation) | External multi-centre trial data | Volumetric TTP HR for OS 2.59 vs central RANO 2.07 (repo) | n/a | abs (design) + repo (HRs) |

## C. Pseudoprogression (PsP) vs true progression (TP)

| Study | Link | Task | n | MRI | Validation | Headline (internal / external) | Clin-only? | Src |
|---|---|---|---|---|---|---|---|---|
| Booth et al. (2022), *Front Oncol* 12:799662 (meta-analysis) | [doi](https://doi.org/10.3389/fonc.2022.799662) | ML monitoring biomarkers: TP vs mimics | 18 studies; 1,335 train / 384 test pts | Mixed | 33 % with external hold-out; 33 % with no hold-out | Pooled sens 0.769, spec 0.648, ROC-AUC 0.765. High risk of bias. About 28 % of studies restricted to 0–12 weeks post-RT | n/a | full (summary of the page) |
| Bhandari et al. (2022), *J Med Imaging Radiat Oncol* 66(6):781–797 | [doi](https://doi.org/10.1111/1754-9485.13436) | ML: treatment effects vs TTP | 25 studies; 9 meta-analysed (glioma PsP vs TTP) | Mixed | Mixed | Pooled sens 95.2 % (86.6–98.4), spec 82.4 % (67.0–91.6); highest single AUC 0.98 | n/a | abs |
| Taylor et al. (2022), *Sci Rep* 12:13258 | [doi](https://doi.org/10.1038/s41598-022-16726-x) | Imaging discriminators of PsP vs TTP (non-ML) | 30 studies, 1,372 pts | Advanced | Meta-analysis | DWI AUC 0.93 (0.91–0.95), DSC 0.93 (0.90–0.95), DCE 0.90 (0.87–0.93) | n/a | abs |
| van Dijken et al. (2017), *Eur Radiol* 27(10):4129–4144 | [doi](https://doi.org/10.1007/s00330-017-4789-9) | MRI techniques for HGG treatment response (non-ML) | Anatomical 5 studies / 166 pts; DSC 18 / 708 | Conv. vs advanced | Meta-analysis | Anatomical MRI sens 68 % / spec 77 %; ADC 71 / 87; DSC 87 / 86; DCE 92 / 85; MRS 91 / 95 | n/a | abs |
| Kim et al. (2019), *Neuro-Oncology* 21(3):404–414 | [doi](https://doi.org/10.1093/neuonc/noy133) | PsP within 3 mo after CRT | 61 train / 34 external / 23 prospective | Conv. + ADC + CBV radiomics | External (different scanner) + internal prospective | Multiparametric AUC 0.90 → external 0.85. **Conventional-MRI-only radiomics 0.76** | No | abs |
| Akbari et al. (2020), *Cancer* 126(11):2625–2636 | [doi](https://doi.org/10.1002/cncr.32790) | Histology-confirmed TP vs PsP | 40 discovery + 23 replication + 20 inter-institutional | Multiparametric (incl. advanced) | LOOCV, replication, external | AUC 0.92 (PsP, LOOCV) → 0.84 / 0.80 replication → 0.80 external (acc. 75 %) | No | abs |
| Moassefi et al. (2022), *J Neurooncol* 159(2):447–455 | [doi](https://doi.org/10.1007/s11060-022-04080-x) | TP vs PsP after Stupp | 124 (63 PsP / 61 TP) | Conv. (T1c + T2), 3D DenseNet121 | 5-fold CV, no external test | Mean AUC 0.756 (fold range 0.655–0.854) | No | abs |
| Ari et al. (2022), *Sci Rep* 12:5915 | [doi](https://doi.org/10.1038/s41598-022-09945-9) | PsP predicted from **pre-treatment** T1c | 131 (106 dev / 25 independent) | Conv. (T1c only) + age | Repeated 10-fold CV; random test; independent sample | AUC 91.5 % dev → 78.5 % test → 72.9 % independent | No | abs |
| Patel et al. (2021), *Clin Radiol* 76(8):628.e17–e27 | [doi](https://doi.org/10.1016/j.crad.2021.03.019) | Early TP vs PsP (labels to 6 mo post-CRT) | 76 (46 TP / 30 PsP) | Conv. (T1c, T2) + ADC | 5-fold CV, no external test | Final model AUC 0.80. Top features: age, MGMT, shape, ADC texture | No separate number | abs |
| Zhou et al. (2026), *Front Oncol* | [doi](https://doi.org/10.3389/fonc.2026.1892760) | PsP after RT in grade 3–4 glioma | 222 (60 PsP) | Conv. + DWI + DSC | Single 7:3 split, locked RadScore | Validation AUC: integrated 0.811; RadScore alone 0.771; clinical-imaging (rCBV, ADC, NLR, MGMT, TMZ) 0.744 | Clinical-*imaging* model 0.744 (includes rCBV/ADC) | abs |
| Guo & Mirzaei (2026), *Cancers* 18(1):36 | [doi](https://doi.org/10.3390/cancers18010036) | TP vs PsP, stage-specific (1st vs 2nd follow-up) | 180 (Burdenko) | Conv. (T1c, FLAIR); 11 DL families | Patient-level CV | Accuracy ~0.70–0.74. Best AUC 0.57 (1st FU), 0.66 (2nd FU) (repo full-text read). Abstract: "absolute discrimination remained modest" | No | abs + repo |

## D. Clinical-only vs imaging: added value of radiomics / DL

| Study | Link | Task | n | MRI | Validation | Headline (internal / external) | Clin-only? | Src |
|---|---|---|---|---|---|---|---|---|
| **Leone et al. (2023)**, *Neuro-Oncol Adv* 5(1):vdad016 | [doi](https://doi.org/10.1093/noajnl/vdad016) | PsP vs PD, suspected PsP ≤7 mo after CRT | 105, single centre | Conv. + ADC + nrCBV; radiomics; DL | 5 × 5 repeated CV; no external test | Clinical + MGMT **0.69 (0.55–0.83)**. + median ADC/nrCBV 0.71 (n.s.). + radiomics **0.52–0.54 (significantly worse)**. DL imaging ≤ 0.56 | **Yes: 0.69.** Clinical inputs include *time from end of RT to lesion* | full |
| **Gomaa et al. (2025)**, *Sci Rep* 15:17133 | [doi](https://doi.org/10.1038/s41598-025-02026-7) | PsP vs TP after RT | 59 train (Burdenko) / 20 external (Erlangen) | Conv. (T1c, FLAIR) ViT + clinical + RT dose | External test | External AUC: combined **0.753**; **clinical-only 0.727**; imaging-only 0.717 | **Yes: 0.727** (age, sex, IDH, MGMT, dose, time since treatment end) | full |
| **Abler et al. (2025)**, arXiv:2507.15548 | [arXiv](https://arxiv.org/abs/2507.15548) | OS ≤6 vs >6 mo (pre-treatment MRI) | 1,152 GBM, 5 Swiss centres + 1 public | Conv. (T1, T1c, T2, FLAIR); CR and DL | Internal + external | External AUC: CR combined 0.75 vs **clinical-only 0.74** vs imaging-only 0.68 (significant but small); DL similar trend, n.s. | **Yes: 0.74** (age, sex) | abs |
| Jang et al. (2018), *Sci Rep* 8:12516 | [doi](https://doi.org/10.1038/s41598-018-31007-2) | PsP vs PD after CCRT | 59 train / 19 test (second hospital) | Conv. (T1c, 9 slices), CNN-LSTM | External test | Test AUC: MRI + clinical 0.83; MRI-only 0.69; **clinical-only RF 0.52** | **Yes: 0.52** (includes interval from end of CCRT to lesion) | full |
| Bae et al. (2018), *Radiology* 289(3):797–806 | [doi](https://doi.org/10.1148/radiol.2018180200) | OS and PFS (pre-op) | 217 (3:1 split) | Multiparametric radiomics (796 features), RSF | Single split | Test iAUC radiomics model: OS 0.652 (0.524–0.769), PFS 0.590 (0.502–0.689). Adding radiomics to clinical + genetic improved prediction (p = .04 OS, .03 PFS) | Compared, but clinical-only iAUC **not in the abstract** | abs |
| Kickingereder et al. (2016), *Radiology* 280(3):880–889 | [doi](https://doi.org/10.1148/radiol.2016160845) | PFS and OS (pre-op) | 119 (79 / 40) | T1c + FLAIR radiomics; radiologic = nrCBV, ADC | 2:1 split | Validation C-index, PFS: radiomics 0.611, **clinical 0.599**, radiologic 0.554, radiomics + clinical 0.637. OS: 0.654 / **0.640** / 0.603 / 0.696 | **Yes: PFS 0.599, OS 0.640** (age, KPS) | abs |
| Vils et al. (2021), *Front Oncol* 11:636672 | [doi](https://doi.org/10.3389/fonc.2021.636672) | PFS2 and OS in recurrent GBM (DIRECTOR trial) | 69 train / 49 external | Conv. (T1c + peritumoral) radiomics | External validation | Training C-index PFS2 0.53–0.59, OS 0.62–0.63; **not confirmed externally** ("failed") | No | abs + full |

## E. Time since radiotherapy / phase of care

| Study | Link | What it says about timing | Src |
|---|---|---|---|
| **Gomaa et al. (2025)** (row D) | [doi](https://doi.org/10.1038/s41598-025-02026-7) | "The time between the treatment termination and the time point at which progression was observed has the greatest impact on the model's output." Clinical-only (0.727) beats imaging-only (0.717) externally | full |
| **Guo & Mirzaei (2026)** (row C) | [doi](https://doi.org/10.3390/cancers18010036) | Stage-specific benchmark: discrimination improves at the 2nd follow-up, "indicating richer separability later in the care pathway." Argues for evaluating by follow-up stage | abs |
| Leone et al. (2023) (row D) | [doi](https://doi.org/10.1093/noajnl/vdad016) | Clinical model includes time from end of RT to the lesion; that model (0.69) is the best one; adding imaging hurts | full |
| Jang et al. (2018); Jang et al. (2020), *Cancers* 12:2706 | [doi 2018](https://doi.org/10.1038/s41598-018-31007-2), [doi 2020](https://doi.org/10.3390/cancers12092706) | Both use the interval from end of CCRT to lesion as an input. In 2020 the 2018 model "showed limited performance" on a 104-patient multi-institutional set and was refit (10-fold AUPRC 0.86) | full / abs |
| Hoosemans et al. (2025), *J Neurooncol* 176 | [doi](https://doi.org/10.1007/s11060-025-05299-0) | n = 175. PsP <4 mo after CRT has shorter OS (11.3 mo) than PsP >4 mo (17.4 mo). No clinical factor predicted PsP | abs |
| Booth et al. (2022) (row C) | [doi](https://doi.org/10.3389/fonc.2022.799662) | About 28 % of studies restricted to 0–12 weeks post-RT and the rest used up to 6 months, so the windows are not comparable across studies | full (summary) |
| Wen et al. (2023), RANO 2.0, *J Clin Oncol* 41:5187–5199 | [doi](https://doi.org/10.1200/JCO.23.01059) | Post-RT MRI as baseline; progression within 12 weeks needs confirmation, so label definition depends on phase (repo) | repo |

## F. Validation-quality critiques

| Study | Link | Finding | Src |
|---|---|---|---|
| An et al. (2021), *PLOS ONE* 16(8):e0256152 | [doi](https://doi.org/10.1371/journal.pone.0256152) | Over 1,000 random splits of brain-tumour radiomics, the train–test AUC gap was 0.039 ± 0.032 (easy task) to 0.092 ± 0.071 (hard task, undersampled). One split gave 0.882 → 0.667, another 0.709 → 0.911 | abs |
| Varoquaux (2018), *NeuroImage* 180:68–77 | [doi](https://doi.org/10.1016/j.neuroimage.2017.06.061) | CV error bars are about ±10 % at n = 100; the across-fold SE strongly underestimates them | abs |
| Park et al. (2020), *BMC Cancer* 20:29 | [doi](https://doi.org/10.1186/s12885-019-6504-5) | 51 neuro-oncology radiomics studies: median RQS 11/36; only 29.4 % externally validated; test–retest 2 % | abs |
| Yu et al. (2022), *Radiol Artif Intell* 4(3):e210064 | [doi](https://doi.org/10.1148/ryai.210064) | 86 externally validated DL algorithms: 81 % lost performance externally, 49 % by ≥0.05, 24 % by ≥0.10 | abs |
| Vils (2021); Jang (2020); Akbari (2020); Chen (2026); Ari (2022) | above | Neuro-oncology external drops: Vils models failed; Jang 2018 model "limited performance" on new sites; Akbari 0.92 → 0.80; Chen 0.887 → 0.762; Ari 0.785 → 0.729 | — |

---

## Corrections and notes for the repo docs

1. **Patel 2021** is a TP vs PsP classifier (76 patients with early enhancing disease after CRT). It is not forward progression from surveillance. `RELATED_WORK.md` §2 lists it under "predicting progression from post-treatment MRI" and `LITERATURE_TABLE.md` calls the endpoint "treatment response". Move it to the PsP group.
2. **Gomaa 2025**: the repo cites only the 75.3 % AUC. The paper also reports clinical-only 0.727 vs imaging-only 0.717 externally, and names time since treatment end as the top feature. This is directly relevant to the phase-of-care argument.
3. **Leone 2023** is not in the repo docs. It is the closest analogue to our negative result: same cohort design scale, repeated CV, clinical + MGMT 0.69, and radiomics making the model significantly worse.
4. **Jang 2018** clinical-only RF scored 0.52 (vs 0.83 combined), the opposite direction to Gomaa and Leone. Worth citing as a counterexample (test n = 19).
5. **Ari 2022** predicts PsP from *pre-treatment* MRI. It is not a follow-up-scan model.
6. **Booth 2022**: the fetched page attributes the pooled estimates to a 10-study meta-analytic subset of the 18 included studies. Check the wording "across 18 ML studies, pooled …" in `RELATED_WORK.md`.
7. **Yun 2025** and **Bae 2018** trained clinical-only models, but their values are not in the abstracts (unverified). Get the full text before quoting them as clinical baselines.
8. **Kickingereder 2016** validation C-indices (clinical 0.599 PFS / 0.640 OS) are now verified from the abstract and can be added to the clinical-baseline paragraph.

## Search notes

- No new MU-Glioma-Post or LUMIERE outcome papers were found beyond those in `comparison.md`. CFB-GBM v2.0 (arXiv:2608.17884) is a new longitudinal dataset paper with RANO 2.0 labels. It reports no model results and does not mention LUMIERE or MU.
- Not found, so not added: any paper that stratifies performance *by phase of care* for a forward-progression endpoint, or that explicitly treats time since RT as a *confounder* of imaging-model AUC.

## References (APA 7; long author lists shortened with "et al." — complete them with a reference manager)

- Abler, D., Pusterla, O., Joye-Kühnis, A., et al. (2025). *The added value for MRI radiomics and deep-learning for glioblastoma prognostication compared to clinical and molecular information* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2507.15548
- Akbari, H., Rathore, S., Bakas, S., et al. (2020). Histopathology-validated machine learning radiographic biomarker for noninvasive discrimination between true progression and pseudo-progression in glioblastoma. *Cancer, 126*(11), 2625–2636. https://doi.org/10.1002/cncr.32790
- An, C., Park, Y. W., Ahn, S. S., Han, K., Kim, H., & Lee, S.-K. (2021). Radiomics machine learning study with a small sample size: Single random training-test set split may lead to unreliable results. *PLOS ONE, 16*(8), e0256152. https://doi.org/10.1371/journal.pone.0256152
- Ari, A. P., Akkurt, B. H., Musigmann, M., et al. (2022). Pseudoprogression prediction in high grade primary CNS tumors by use of radiomics. *Scientific Reports, 12*, 5915. https://doi.org/10.1038/s41598-022-09945-9
- Bae, S., Choi, Y. S., Ahn, S. S., Chang, J. H., Kang, S.-G., Kim, E. H., Kim, S. H., & Lee, S.-K. (2018). Radiomic MRI phenotyping of glioblastoma: Improving survival prediction. *Radiology, 289*(3), 797–806. https://doi.org/10.1148/radiol.2018180200
- Balakumaran, et al. (2026). Delta radiomics from multiparametric MRI predicts survival and treatment response in post-treatment glioma patients. *Proceedings of SPIE*. https://doi.org/10.1117/12.3088139 (author initials unverified)
- Bhandari, A., Marwah, R., Smith, J., Nguyen, D., Bhatti, A., Lim, C. P., & Lasocki, A. (2022). Machine learning imaging applications in the differentiation of true tumour progression from treatment-related effects in brain tumours: A systematic review and meta-analysis. *Journal of Medical Imaging and Radiation Oncology, 66*(6), 781–797. https://doi.org/10.1111/1754-9485.13436
- Booth, T. C., Grzeda, M., Chelliah, A., et al. (2022). Imaging biomarkers of glioblastoma treatment response: A systematic review and meta-analysis of recent machine learning studies. *Frontiers in Oncology, 12*, 799662. https://doi.org/10.3389/fonc.2022.799662
- Chen, C., Guo, F., Huang, D., et al. (2026). Predicting recurrence risk of glioblastoma based on preoperative-postoperative longitudinal MRI: A multicenter study. *Bioengineering, 13*(6), 668. https://doi.org/10.3390/bioengineering13060668
- Christodoulou, R. C., Vamvouras, G., Pitsillos, R., Solomou, E. E., & Georgiou, M. F. (2026). Explainable radiomics with probability calibration for postoperative glioblastoma surveillance. *European Journal of Radiology Artificial Intelligence, 5*, 100074. https://doi.org/10.1016/j.ejrai.2026.100074
- Ding, T., Zou, Y., Chen, C., Shah, M., & Tian, Y. (2025). *CLARITY* [Preprint]. arXiv. https://arxiv.org/abs/2512.08029
- Gomaa, A., Huang, Y., Stephan, P., et al. (2025). A self-supervised multimodal deep learning approach to differentiate post-radiotherapy progression from pseudoprogression in glioblastoma. *Scientific Reports, 15*, 17133. https://doi.org/10.1038/s41598-025-02026-7
- Guo, W., & Mirzaei, G. (2026). [Stage-specific DL benchmark on Burdenko GBM Progression]. *Cancers, 18*(1), 36. https://doi.org/10.3390/cancers18010036 (exact title: see arXiv:2511.18595)
- Hashim, U., Jalal, A., Jabali, A. N., & Rana, H. (2026). Radiomics outperforms conventional tumor volume in prognostic stratification across independent glioma cohorts. *Cureus, 18*(7), e112298. https://doi.org/10.7759/cureus.112298
- Hoosemans, L. J. N., Panayotopoulos, L. F., van Kuijk, S. M. J., et al. (2025). Clinical predictors of pseudoprogression in glioblastoma: A retrospective cohort analysis. *Journal of Neuro-Oncology, 176*. https://doi.org/10.1007/s11060-025-05299-0
- Jang, B.-S., Jeon, S. H., Kim, I. H., & Kim, I. A. (2018). Prediction of pseudoprogression versus progression using machine learning algorithm in glioblastoma. *Scientific Reports, 8*, 12516. https://doi.org/10.1038/s41598-018-31007-2
- Jang, B.-S., Park, A. J., Jeon, S. H., et al. (2020). Machine learning model to predict pseudoprogression versus progression in glioblastoma using MRI: A multi-institutional study (KROG 18-07). *Cancers, 12*(9), 2706. https://doi.org/10.3390/cancers12092706
- Kickingereder, P., Burth, S., Wick, A., et al. (2016). Radiomic profiling of glioblastoma: Identifying an imaging predictor of patient survival with improved performance over established clinical and radiologic risk models. *Radiology, 280*(3), 880–889. https://doi.org/10.1148/radiol.2016160845
- Kickingereder, P., Isensee, F., Tursunova, I., et al. (2019). Automated quantitative tumour response assessment of MRI in neuro-oncology with artificial neural networks: A multicentre, retrospective study. *The Lancet Oncology, 20*(5), 728–740. https://doi.org/10.1016/S1470-2045(19)30098-1
- Kim, J. Y., Park, J. E., Jo, Y., et al. (2019). Incorporating diffusion- and perfusion-weighted MRI into a radiomics model improves diagnostic performance for pseudoprogression in glioblastoma patients. *Neuro-Oncology, 21*(3), 404–414. https://doi.org/10.1093/neuonc/noy133
- Leone, R., Meredig, H., Foltyn-Dumitru, M., et al. (2023). Assessing the added value of apparent diffusion coefficient, cerebral blood volume, and radiomic magnetic resonance features for differentiation of pseudoprogression versus true tumor progression in patients with glioblastoma. *Neuro-Oncology Advances, 5*(1), vdad016. https://doi.org/10.1093/noajnl/vdad016
- Li, Z., Chen, L., Song, Y., et al. (2023). Predictive value of magnetic resonance imaging radiomics-based machine learning for disease progression in patients with high-grade glioma. *Quantitative Imaging in Medicine and Surgery*. https://doi.org/10.21037/qims-22-459
- Moassefi, M., Faghani, S., Conte, G. M., et al. (2022). A deep learning model for discriminating true progression from pseudoprogression in glioblastoma patients. *Journal of Neuro-Oncology, 159*(2), 447–455. https://doi.org/10.1007/s11060-022-04080-x
- Park, J. E., Kim, H. S., Kim, D., Park, S. Y., Kim, J. Y., Cho, S. J., & Kim, J. H. (2020). A systematic review reporting quality of radiomics research in neuro-oncology. *BMC Cancer, 20*(1), 29. https://doi.org/10.1186/s12885-019-6504-5
- Patel, M., Zhan, J., Natarajan, K., et al. (2021). Machine learning-based radiomic evaluation of treatment response prediction in glioblastoma. *Clinical Radiology, 76*(8), 628.e17–628.e27. https://doi.org/10.1016/j.crad.2021.03.019
- Pineda, G., et al. (2024). SDDR [Abstract NIMG-75]. *Neuro-Oncology, 26*(Suppl. 8). https://pmc.ncbi.nlm.nih.gov/articles/PMC11553339/
- Rai, A. K. (2026). Uncertainty gated residual learning with patient level bagging for longitudinal glioma progression prediction. *Journal of Intelligent Decision Making and Information Science, 3*. https://doi.org/10.59543/jidmis.v3.2236
- Suter, Y., Schuhmacher, F., Ermis, E., Knecht, U., Schucht, P., Wiest, R., & Reyes, M. (2024). Towards radiomics-based automated disease progression assessment for glioblastoma patients. In *Brainlesion* (LNCS 14668, pp. 36–47). Springer. https://doi.org/10.1007/978-3-031-76160-7_4
- Tak, D., Garomsa, B. A., Zapaishchykova, A., et al. (2025). Longitudinal risk prediction for pediatric glioma with temporal deep learning. *NEJM AI, 2*(5). https://doi.org/10.1056/AIoa2400703
- Taylor, C., Ekert, J. O., Sefcikova, V., Fersht, N., & Samandouras, G. (2022). Discriminators of pseudoprogression and true progression in high-grade gliomas: A systematic review and meta-analysis. *Scientific Reports, 12*, 13258. https://doi.org/10.1038/s41598-022-16726-x
- Tikhonov, D., et al. (2025). [BraTS-Lighthouse 2025 progression-task submission] [Preprint]. arXiv. https://arxiv.org/abs/2509.06511
- van Dijken, B. R. J., van Laar, P. J., Holtman, G. A., & van der Hoorn, A. (2017). Diagnostic accuracy of magnetic resonance imaging techniques for treatment response evaluation in patients with high-grade glioma, a systematic review and meta-analysis. *European Radiology, 27*(10), 4129–4144. https://doi.org/10.1007/s00330-017-4789-9
- Varoquaux, G. (2018). Cross-validation failure: Small sample sizes lead to large error bars. *NeuroImage, 180*, 68–77. https://doi.org/10.1016/j.neuroimage.2017.06.061
- Vils, A., Bogowicz, M., Tanadini-Lang, S., et al. (2021). Radiomic analysis to predict outcome in recurrent glioblastoma based on multi-center MR imaging from the prospective DIRECTOR trial. *Frontiers in Oncology, 11*, 636672. https://doi.org/10.3389/fonc.2021.636672
- Wen, P. Y., van den Bent, M., Youssef, G., et al. (2023). RANO 2.0. *Journal of Clinical Oncology, 41*(33), 5187–5199. https://doi.org/10.1200/JCO.23.01059
- Yu, A. C., Mohajer, B., & Eng, J. (2022). External validation of deep learning algorithms for radiologic diagnosis: A systematic review. *Radiology: Artificial Intelligence, 4*(3), e210064. https://doi.org/10.1148/ryai.210064
- Yun, Y. C., Jende, J. M. E., Garhöfer, F., et al. (2025). Combined peritumoral radiomics and clinical features predict 12-month progression free survival in glioblastoma. *Journal of Neuro-Oncology, 174*, 111–120. https://doi.org/10.1007/s11060-025-05037-6
- Zhou, J., et al. (2026). Radiomics and clinical data predict pseudoprogression after radiotherapy in high-grade glioma. *Frontiers in Oncology*. https://doi.org/10.3389/fonc.2026.1892760
