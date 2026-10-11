# Table 2. Related studies and this study

Condensed from `docs/literature/comparison.md` (Tables A and B) and `docs/literature/RELATED_WORK.md` (section 2). Every number
and DOI comes from those two files, and was checked there against the primary source at the level marked ([full] = full text,
[abs] = abstract only, [sec] = secondary source). Metrics are as the authors report them and are **not comparable across rows**:
endpoints, units (scan, scan pair, patient) and validation designs differ. "External test" = performance reported on a cohort
from another institution or dataset that was not used for development.

| Study | Data | n | Endpoint / horizon | Validation | Metric as reported | External test |
|---|---|---|---|---|---|---|
| Christodoulou et al. 2026, *Eur J Radiol AI* 5:100074, [doi:10.1016/j.ejrai.2026.100074](https://doi.org/10.1016/j.ejrai.2026.100074) [abs] | MU-Glioma-Post; T1, T1c, T2, FLAIR radiomics | Not stated in abstract | Progression status of each post-operative scan; no horizon; censoring not mentioned | Patient-aware 5-fold CV for tuning; one patient-held-out test set | AUC 0.80 (test), no CI | No |
| Rai 2026, *J Intell Decis Mak Inf Sci* 3, [doi:10.59543/jidmis.v3.2236](https://doi.org/10.59543/jidmis.v3.2236) [abs] | MU-Glioma-Post; 4 sequences, radiomics + clinical event features | 391 scan pairs / 155 patients | ≥ 25% tumour-volume increase at the next scan (volume-derived); variable horizon | Nested patient-grouped CV | AUC 0.728 (95% CI 0.678–0.777) | No |
| Hashim et al. 2026, *Cureus* 18(7):e112298, [doi:10.7759/cureus.112298](https://doi.org/10.7759/cureus.112298) [abs] | MU-Glioma-Post (discovery) + UCSD-PTGBM, UCSF-PDGM, UPenn-GBM; volumes, radiomic score, clinical | 1,447 patients (MU 194) | Per-patient PFS (MU) and OS (UPenn); Cox | Discovery / external cohorts | MU active-tumour volume C-index 0.676 | Yes (other cohorts; PFS/OS, patient level) |
| Ding et al. 2025, CLARITY, [arXiv:2512.08029](https://arxiv.org/abs/2512.08029) [full] | MU-Glioma-Post; imaging latents, intervals, clinical, treatment | 203 patients / 654 follow-ups | Survival (one-year survival probability, risk score) and treatment choice | Patient-level 75/15/15 split + 5-fold CV | C-index 0.794 ± 0.02; treatment F1 57.1% | Zero-shot UCSF-ALPTDG (treatment F1 48.9%) |
| Suter et al. 2024, LNCS 14668:36–47, [doi:10.1007/978-3-031-76160-7_4](https://doi.org/10.1007/978-3-031-76160-7_4) [abs, via RELATED_WORK] | LUMIERE-type longitudinal GBM MRI; current + change radiomics | Not stated in our sources | Progression assessment | Not stated in our sources | ROC-AUC 0.748 (random forest) | Not stated |
| Matoso et al. 2025, [arXiv:2504.18268](https://arxiv.org/abs/2504.18268) [full] | LUMIERE; T1, T2, FLAIR; DenseNet264 | 91 patients / 638 timepoints | 4-class RANO of a consecutive scan pair (concurrent) | 5-fold CV, 80/20 stratified split; patient grouping not stated | Median balanced accuracy 50.96% | No |
| Tikhonov et al. 2025, [arXiv:2509.06511](https://arxiv.org/abs/2509.06511) [full] | LUMIERE (BraTS-Lighthouse 2025 training set); radiomics + clinical + ResNet-18 features, CatBoost | Not stated in our sources | 4-class RANO of a scan pair (concurrent) | 5-fold patient-wise stratified CV | Mean ROC AUC 0.81 ± 0.08; macro F1 0.50 ± 0.08; volumes only AUC 0.59 ± 0.05 | No |
| Tarek et al. 2026, TRACE, [arXiv:2606.30313](https://arxiv.org/abs/2606.30313) [full] | LUMIERE; paired MRI + masks, scan interval | 361 scan pairs (599 sessions) | 4-class RANO 2.0-aligned (concurrent); binary PD vs rest | 5-fold patient-wise CV | 4-class macro F1 0.477 ± 0.123; binary macro F1 0.709 ± 0.094; RANO rule oracle 0.681 ± 0.058 | No |
| Chen et al. 2026, *Bioengineering* 13(6):668, [doi:10.3390/bioengineering13060668](https://doi.org/10.3390/bioengineering13060668) [abs] | LUMIERE (train), XJYY-GBM, RHUH-GBM; pre- + post-operative T2 | 139 patients (59 / 40 / 40) | Recurrence within 6 months after surgery; censoring not mentioned | Train / internal validation / external test | AUC 0.887 internal, 0.762 external | Yes (RHUH-GBM, n = 40) |
| Tak et al. 2025, *NEJM AI* 2(5), [doi:10.1056/AIoa2400703](https://doi.org/10.1056/AIoa2400703) [abs] | Paediatric glioma (LGG + HGG), 3 institutions; serial post-operative MRI | 715 patients / 3,994 scans | Recurrence within 1 year of the last scan; censoring not stated | Multi-institutional (details not in abstract) | AUC 75–89% across datasets | Unclear from abstract |
| Yun et al. 2025, *J Neurooncol* 174:111–120, [doi:10.1007/s11060-025-05037-6](https://doi.org/10.1007/s11060-025-05037-6) [abs] | Single centre, 3 T; post-treatment MRI radiomics + age, sex, MGMT | 560 patients | RANO PFS at 6 and 12 months (binary); censoring not mentioned | 70/30 split | 12 mo, clinical + peri-CET radiomics: AUC 0.75 (0.65–0.85); 6 mo radiomics: 0.61 (0.51–0.70) | No |
| Li et al. 2023, *Quant Imaging Med Surg*, [doi:10.21037/qims-22-459](https://doi.org/10.21037/qims-22-459) [abs] | Pre-radiotherapy (post-operative) structural MRI radiomics, HGG | 162 patients | Progression at 6, 9, 12, 15, 18 months (binary per horizon) | Not confirmed | AUC 0.70 / 0.68 / 0.78 / 0.78 / 0.78 | Not confirmed |
| Patel et al. 2021, *Clin Radiol* 76(8):628.e17–e27, [doi:10.1016/j.crad.2021.03.019](https://doi.org/10.1016/j.crad.2021.03.019) [abs, via RELATED_WORK] | Early post-chemoradiotherapy MRI; clinical, MGMT, radiomics | 76 patients | Treatment response | Cross-validation | AUC 0.80 | No |
| Booth et al. 2022 (meta-analysis), *Front Oncol* 12:799662, [doi:10.3389/fonc.2022.799662](https://doi.org/10.3389/fonc.2022.799662) [abs] | 18 ML studies, progression vs treatment-related mimics (adjacent task) | 1,335 train / 384 test patients | Concurrent progression vs pseudoprogression | Mixed; high risk of bias, a third without hold-out test | Pooled ROC-AUC 0.765 (sens 0.769, spec 0.648) | Mixed |
| **This study: clinical + timing + treatment ridge, MU grade 4** | MU-Glioma-Post; clinical, timing, as-of-scan treatment | 249 scans / 126 patients | Progression within 120 d of each index scan; censoring-aware (IPCW) | 5 × 5 repeated patient-grouped stratified CV; patient-cluster bootstrap | IPCW AUC(120) {{C3_G4_BASELINE_AUC}} ({{lo}}–{{hi}}) | No (internal) |
| **This study: + radiomics, MU grade 4 (nested selection)** | + corrected compartment radiomics | 249 / 126 | Same | Same, nested over 70 radiomics configurations | ΔAUC vs baseline {{C3_G4_NESTED_DAUC}} ({{lo}}–{{hi}}) | No (internal) |
| **This study: all gliomas** | MU-Glioma-Post, all grades | 308 / 155 | Same | Same | Baseline {{C3_ALL_BASELINE_AUC}}; nested ΔAUC {{C3_ALL_NESTED_DAUC}} | No (internal) |
| **This study: locked external test** | Train MU grade 4 → test LUMIERE | 132 scans / 61 patients | RANO PD within 120 d; censoring-aware | Locked model, no refitting | IPCW AUC(120) {{EXT_BEST_AUC}} ({{lo}}–{{hi}}); shipped PRISM report model {{EXT_SHIPPED_AUC}} | Yes |
| **This study: PRISM report radiomics model, split variance** | MU-Glioma-Post, PRISM report design | 30 test patients per split, 500 splits | Naive 120-d label | 500 splits of the PRISM report design, features re-selected per split | 0.802 on the PRISM report split; 0.719 ± 0.056 across splits (seed-62 re-run ranks above 92%) | No |

Placeholders (the coordinator fills these from the final run; all are mean over 5 repeats of per-repeat pooled-OOF AUC with
patient-cluster bootstrap CIs, `docs/results/FIX_EVALUATION.md`):

| Placeholder | File | Row / column |
|---|---|---|
| `{{C3_G4_BASELINE_AUC}}` | `outputs/results/c3/grade4/results.csv` | baseline row (`variant` empty, stability/selection/integration `none`, learner `ridge`): `auc_ipcw`, `auc_ipcw_lo`, `auc_ipcw_hi` |
| `{{C3_G4_NESTED_DAUC}}` | `outputs/results/c3/grade4/results.csv`, row `variant` = NESTED | `d_auc_ipcw_vs_None\|none\|none\|none\|ridge`, `d_auc_ipcw_lo`, `d_auc_ipcw_hi` |
| `{{C3_ALL_BASELINE_AUC}}`, `{{C3_ALL_NESTED_DAUC}}` | `outputs/results/c3/all_glioma/results.csv` | as above |
| `{{EXT_BEST_AUC}}` | `outputs/results/external_lumiere/results.csv` | `arm` = locked, prespecified primary model: `auc_ipcw`, `auc_ipcw_lo`, `auc_ipcw_hi` |
| `{{EXT_SHIPPED_AUC}}` | `outputs/results/external_lumiere/shipped_model.csv` | `variant` = codes_as_unknown: `auc_ipcw` (`_lo`, `_hi`) |
| split variance (filled) | `outputs/results/analyses/split_variance/summary.csv` | `prism_reselect`, naive (`docs/results/SPLIT_VARIANCE.md`) |

Not included, with reasons (all in `comparison.md`): Jung 2026 (voxel-wise forecast, not risk), Li ID 2026 (MU used only for
pretraining), Pineda 2024 / Liu 2025 PHSP-Net (overall survival), Farzana 2023 and Pignotti 2024 (pre-RT or pre-operative
window), Suter 2023 / Asfaw 2026 (agreement of automated volumetry with RANO, not prediction), Amato 2025 (protocol unverified;
metric only from a secondary source).
