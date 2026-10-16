# Candidate datasets: more patients, diffusion, perfusion (2026-10-15)

Why we looked: on MU-Glioma-Post the clinical + treatment model reaches AUC ~0.70, and conventional-MRI imaging adds nothing
(radiomics, deep features, re-segmentation all tested). Two open questions: is the limit the *label* (documented progression), and
is it the *modality* (conventional MRI only)? These datasets can address one or both. Facts below were read from the TCIA collection
pages, the dataset papers and the downloaded clinical tables (`data/cfb-gbm/clinical`, `data/ucsd-ptgbm/clinical`).

## Summary

| Dataset | Patients / scans | MRI | Timepoints | Outcome labels | Molecular | Size | Access |
|---|---|---|---|---|---|---|---|
| MU-Glioma-Post (dev, on disk) | 155 / 308 usable | T1, T1c, T2, FLAIR | many per patient | documented progression date + type (imaging / clinical / both) | IDH, MGMT | 12 GB | TCIA |
| LUMIERE (external, on disk) | 91 total; 61 / 132 usable | T1, CT1, T2, FLAIR (checked in `data/lumiere/imaging`) | many per patient | **expert RANO rating per scan** | IDH, MGMT | — | figshare |
| CFB-GBM v4 | 264 Stupp patients | T1-Gd, T1 GE, T1 TSE, T2 TSE, FLAIR, T2*, **ADC**; CT, RTDOSE, GTV | t0 / t1 / t2 only | volumetric RANO 2.0 from GTV, survival (weeks) | **none** (WHO 2016 for 185, 2021 for 79) | 208 GB, NIfTI | TCIA, Aspera, CC BY 4.0 |
| UCSD-PTGBM v3 | 178 / 243 | T1, T1c, T2, FLAIR, **DSC + ASL perfusion**, multishell diffusion (RSI) | mostly 1 per patient | tumour vs post-treatment change (51 negatives, PsP/RN confirmed), PFS for 87 | IDH, MGMT, 1p19q, ATRX | 45 GB, NIfTI | TCIA, Aspera, CC BY 4.0 |

## CFB-GBM: facts from the clinical tables

- t0 is the RT-planning MRI (RT starts 1.5 weeks later on average; dose 25–60 Gy, mean 53 Gy). t1 is a median 14 weeks after t0
  (n = 170 patients), t2 a median 28 weeks (n = 120). With 6 weeks of RT, **t1 falls ~6–8 weeks after RT ends, inside the
  12-week pseudoprogression window** where RANO 2.0 asks for confirmation.
- Volumetric RANO labels (from GTV delineations, ~2/3 network-generated and oncologist-validated):
  t0→t1 PD 38 / SD 105 / PR 16 / CR 1; t0→t2 PD 30 / 112 labelled; **t1→t2 PD 30 / 107 labelled**.
- ADC availability: t0 129, t1 132, t2 91.
- Clinical: age, sex, WHO performance status, height, weight, survival. **No IDH, no MGMT, no progression dates.**

### CFB-GBM versions

"v2.0" in the arXiv paper is the authors' name for the extended release; it corresponds to TCIA versions 3–4, not to TCIA
"Version 2". TCIA history (collection page, read 2026-10-15):

| TCIA version | Date | Change |
|---|---|---|
| 1 | 2025-12-23 | Initial release: 264 subjects, 3,089 series, 208 GB MR/CT/RTDOSE (NIfTI), clinical/treatment/availability tables. GTV for ~35 % of timepoints (the original "CFB-GBM") |
| 2 | 2026-02-03 | Clinical tables corrected; earlier clinical files withdrawn as erroneous. Images unchanged |
| 3 | 2026-06-26 | 347 GTV files added (nnU-Net, oncologist-validated → ~97 % complete); two-lesion labels merged (subjects 125, 181, 201, 212, 231); 545 normalisation masks; RANO table; PyRadiomics table (= paper "v2.0") |
| 4 | 2026-09-11 (current) | RANO table corrected "to use measurements specific to enhancing tumours"; a subset of misnumbered folders renumbered. Images unchanged |

We use the current files: clinical v03, treatment/availability v02, RANO **v04**, PyRadiomics v03. Images are the same in all
versions, so the 208 GB download is v1-identical apart from the added masks. Checked 2026-10-15: the v04 RANO sizes equal
the PyRadiomics GTV `MeshVolume` on t1gd (Spearman 1.00; within 1 % for 156/165, 153/159, 107/112 patients at t0/t1/t2),
so (i) the RANO label is computed from the GTV volume, and (ii) patient IDs in the v03 radiomics table line up with the v04
RANO table despite the v4 folder renumbering. When the images arrive, re-check IDs against the v4 folders.

## UCSD-PTGBM: facts from the clinical tables

- 243 timepoints / 178 subjects, grade 4 in 240. Bevacizumab before the scan in 27.
- Days from scan to last RT is "Unknown" for 122/243 timepoints; PFS for 87 timepoints.
- The images carry BraTS 2024 IDs (`BraTS-GLI-02250-100`): they are in the BraTS 2024 post-treatment training data, so any
  segmenter or foundation model trained on BraTS 2024 has seen them.

## Download status (2026-10-15)

- Downloaded (HTTPS, small): all clinical tables above, into `data/cfb-gbm/clinical/` and `data/ucsd-ptgbm/clinical/`.
- CFB-GBM ships **PyRadiomics features on the GTV** for every timepoint and sequence (2,424 rows × 150 columns). ADC features
  exist for 126 / 122 / 85 patients at t0 / t1 / t2, so the t1→t2 conventional-vs-ADC test can run **without the images**.
- Images (CFB-GBM 208 GB, UCSD-PTGBM 45 GB) are Aspera-only. The `ascli` client and `ascp` work (package browsing succeeds), but
  from orchard-community-1 and orchard-login-001 outbound TCP 33001 to 144.30.235.113 is blocked, 443 is blocked, and the HTTPS
  fallback on 8443 returns 502. Options: ask HPC support to open TCP+UDP 33001 to that host, or download elsewhere and rsync.
  Client set-up for a retry: scratchpad `aspera/ascli.sh` (ruby + aspera-cli 4.27.5 + Transfer SDK 1.1.9).

## Sources

- CFB-GBM collection (TCIA), DOI [10.7937/v9pn-2f72](https://doi.org/10.7937/v9pn-2f72): <https://www.cancerimagingarchive.net/collection/cfb-gbm>
- CFB-GBM v2.0 paper, arXiv:2608.17884: <https://arxiv.org/abs/2608.17884> ([PDF](https://arxiv.org/pdf/2608.17884);
  Hugging Face paper page <https://huggingface.co/papers/2608.17884>, no data hosted there)
- SegCFB-GBM (the authors' fine-tuned nnU-Net used for the GTV completion): <https://huggingface.co/AlexLECLERCQ/SegCFB-GBM>
- Third-party predicted t0 GTV masks (~70 patients, masks only, superseded by TCIA v3): <https://huggingface.co/datasets/VendenIX/CFB-GBMnnUnetPredictedMasks>
- CFB-GBM clinical tables (TCIA uploads):
  [clinical](https://www.cancerimagingarchive.net/wp-content/uploads/CFB-GBM_clinical_data_v03_20260619.tsv),
  [treatment](https://www.cancerimagingarchive.net/wp-content/uploads/CFB-GBM_treatment_data_v02_20260129.tsv),
  [MRI availability](https://www.cancerimagingarchive.net/wp-content/uploads/CFB-GBM_mri_availability_v02_20260129.tsv),
  [CT availability](https://www.cancerimagingarchive.net/wp-content/uploads/CFB-GBM_ct_availability_v02_20260129.tsv),
  [RANO](https://www.cancerimagingarchive.net/wp-content/uploads/CFB-GBM_rano_criteria_v04_20260909.tsv),
  [PyRadiomics features](https://www.cancerimagingarchive.net/wp-content/uploads/CFB_GBM_features_extraction_pyradiomics_v03_20260619.tsv)
- UCSD-PTGBM collection (TCIA), DOI [10.7937/fwv2-dt74](https://doi.org/10.7937/fwv2-dt74): <https://www.cancerimagingarchive.net/collection/ucsd-ptgbm>
- UCSD-PTGBM paper: Gagnon et al. (2026), *Scientific Data* 13(1), <https://doi.org/10.1038/s41597-025-06499-z> ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12886825/))
- UCSD-PTGBM tables:
  [clinical](https://www.cancerimagingarchive.net/wp-content/uploads/UCSD_PTGBM-clinical-information_v3_2026-12-Mar.xlsx),
  [negative cases](https://www.cancerimagingarchive.net/wp-content/uploads/details_of_negative_cases_TCIA.xlsx),
  [bval/bvec](https://www.cancerimagingarchive.net/wp-content/uploads/UCSD-PTGBM-bval_bvec_20260109.txt)
- TCIA Brain-Tumor-Progression (20 patients, T1/T1c/T2/FLAIR/ADC/nCBF, post-CRT + progression scans): <https://wiki.cancerimagingarchive.net/x/hQNdC>
- Guo & Mirzaei (2026), timepoint-specific DL benchmark on follow-up MRI, arXiv:2511.18595: <https://arxiv.org/pdf/2511.18595>
- Comparable model results for our task: [COMPARABLE_RESULTS.md](COMPARABLE_RESULTS.md)

---

# Public brain-MRI report text for the report generator (2026-10-15)

Purpose: a style and vocabulary reference for the PRISM report summary (`prism/analyses/report_usefulness.py`,
[REPORT_USEFULNESS.md](../results/REPORT_USEFULNESS.md)). Only public text is used; no patient data leaves the node and
no external API is called with patient data. Downloaded to `data/public_reports/` (git-ignored) over HTTPS from Hugging
Face, pinned to a commit.

| Corpus | What it is | Licence | Downloaded | Size | Used |
|---|---|---|---|---|---|
| **RadGenome-Brain MRI** (`JiayuLei/RadGenome-Brain_MRI`, commit `0348ba42`) | Manually written, region-grounded brain MRI reports (findings, findings per sequence, impression) released with AutoRG-Brain (Lei et al., arXiv:2407.16684). They cover public BraTS 2023 GLI / MEN / MET, ISLES22 and WMH cases. The English wording reads as if translated (our observation) | MIT | BraTS_GLI/MEN/MET JSON + split file | 0.9 MB | BraTS-GLI, 230 reports: section structure, length, reading level, hedging (`reference` step) |
| **MultiCaRe** (`mauro-nievoff/MultiCaRe_Dataset`, commit `20bb8619`; Nievas Offidani & Delrieux, *Data in Brief* 2024, doi:10.1016/j.dib.2023.110008) | 75,382 open-access PubMed Central case-report articles (96,428 cases) with case text, figure captions and metadata | CC BY 4.0 for the dataset; each article keeps its own CC licence (CC BY, BY-NC, BY-NC-SA, BY-NC-ND) | `cases.parquet`, `captions_and_labels.csv`, `metadata.parquet`, README, data dictionary (images not downloaded) | 229 MB | 181 glioblastoma / high-grade glioma cases with post-treatment content (chemoradiation, temozolomide, pseudoprogression, radiation necrosis); only their MRI sentences: vocabulary for change over time and hedging |

Checked and not used:
- **TextBraTS** (`Jupitern52/TextBraTS`, MIT; BraTS 2020, MICCAI 2025): reports drafted by GPT-4o and then edited by
  radiologists. Not used as a style reference because the text is LLM-drafted. Pre-operative only.
- **MR-RATE** (`Forithmus/MR-RATE`, CC BY-NC-SA 4.0): about 98,000 real clinical brain and spine MRI reports, structured into
  clinical information / technique / findings / impression. This is the most relevant real-report corpus, but access is
  **gated**: it needs a form with the user's name, institution and acceptance of terms. We did not submit it on the user's
  behalf. It is the first choice for a follow-up comparison if the user requests access.
- **PMC-Patients** (`zhengyun21/PMC-Patients`, CC BY-NC-SA 4.0, 0.8 GB): patient summaries from PMC case reports. These
  overlap with MultiCaRe and are not needed.
- **MIMIC-CXR / MIMIC-IV-Note**: credentialed PhysioNet access, and the reports are chest or general. Not attempted.
- No TCIA neuro-oncology collection we know of distributes free-text follow-up radiology reports.

Limits of the reference. RadGenome-Brain reports are pre-operative, so they have no post-treatment change wording.
MultiCaRe sentences come from published case narratives, not radiology reports. Neither is a set of real post-treatment
glioma surveillance reports. We use them only for form: sections, length, reading level, and how change and
uncertainty are worded. They are not used as a content or accuracy standard.

Sources: <https://huggingface.co/datasets/JiayuLei/RadGenome-Brain_MRI>,
<https://huggingface.co/datasets/mauro-nievoff/MultiCaRe_Dataset>, <https://zenodo.org/records/10079370>,
<https://huggingface.co/datasets/Jupitern52/TextBraTS>, <https://huggingface.co/datasets/Forithmus/MR-RATE>,
<https://huggingface.co/datasets/zhengyun21/PMC-Patients>.
