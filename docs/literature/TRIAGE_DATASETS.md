# Public data for a triage-grade post-RT surveillance model: what exists, what can be pooled, is AUC >= 0.75 on an unseen centre feasible? (2026-10-21)

Question. Can public data support a triage model for post-radiotherapy glioma surveillance (predicting or detecting progression
at a surveillance MRI) that reaches AUC >= 0.75 on a centre it has never seen? Today, MU-Glioma-Post gives IPCW AUC(120 d) 0.601
(0.515 to 0.686) in the scan-day intended use (grade 4, RT started: 173 scans, 86 patients, 88 events; `docs/results/INTENDED_USE.md`,
`docs/results/TRIAGE_FEASIBILITY.md`), and conventional imaging adds nothing. LUMIERE, CFB-GBM and UCSD-PTGBM (clinical tables) are
already in hand; their facts are in [DATASETS.md](DATASETS.md) and are not repeated here except where needed for pooling.

Method. Web search and the dataset landing pages and papers (TCIA, PMC, arXiv, RSNA Atlas, Europe PMC), read on 2026-10-21. One
small, openly licensed clinical table was downloaded to the scratchpad and summarised (Burdenko clinical CSV, CC BY 4.0, 29 KB;
no imaging was downloaded). Fields are marked **[V]** (verified, source given) or **[U]** (unverified: not stated in the sources
read, inferred, or from a secondary source only).

## 1. Summary table

"Surveillance labels" means a progression/response outcome attached to individual post-treatment scans, or a progression date
that lets one be derived per scan.

| Dataset | Centre (overlap with MU) | Patients / post-treatment scans | Sequences at follow-up | Perfusion / diffusion | Masks | Outcome label | RT dates | IDH / MGMT | Access | Size | Use for triage pool |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MU-Glioma-Post (dev, on disk) | Univ. Missouri | 203 / 596 (grade 4 intended use 86 / 173) | T1, T1c, T2, FLAIR | none | 4-class nnU-Net | EMR-documented progression date | yes | yes | open, CC BY 4.0 | 11 GB | development |
| LUMIERE (on disk) | Bern (no) | 91 / 638 dates; 61 / 132 index scans | T1, T1c, T2, FLAIR | none | DeepBraTumIA, HD-GLIO | expert RANO per scan | **no** | yes | open, CC0 | not recorded | training or test |
| CFB-GBM v4 (tables on disk) | Caen (no) | 264; t1 170, t2 120 | T1-Gd, T1, T2, FLAIR, T2* | **ADC** (t1 132, t2 91) | GTV ~97 % | volumetric RANO 2.0 from GTV (algorithmic) | t0 = RT planning | **no** | open, CC BY 4.0 (Aspera) | 208 GB | small secondary (30 PD events t1 to t2) |
| UCSD-PTGBM v3 (tables on disk) | UC San Diego (no; but in BraTS 2024 with MU) | 178 / 243 | T1, T1c, T2, FLAIR | **DSC, ASL**, DWI/ADC, RSI | yes | tumour vs post-treatment change at the scan (pathology or clinical); PFS for 87 | partly | yes | open, CC BY 4.0 (Aspera) | 45 GB | perfusion / detection sub-study |
| **Burdenko-GBM-Progression** | Burdenko, Moscow (no) | 180 / 657 follow-up dates; 651 labelled | 2 to 4 (minimum T1c + FLAIR) | none | RT GTV/CTV/PTV; longitudinal GTV for a subset | **response category per follow-up incl. pseudoprogression** | **yes (start and end)** | partial | **dbGaP controlled** | 131 GB | **best new external / pooled centre** |
| **UCSF-ALPTDG** | UCSF (no; in BraTS 2024) | 298 / 596 (2 consecutive scans each); 80 GBM | T1, T1c, T2, FLAIR | none | 4-class expert + longitudinal change masks | days to progression (multidisciplinary consensus) + volumetric change category | no (days from surgery) | yes | DUA, non-commercial | [U] | second new centre |
| RHUH-GBM | Río Hortega, Valladolid (no) | 40 / 40 recurrence scans (+ pre-op, early post-op) | T1, T1c, T2, FLAIR | ADC | expert-corrected 3-class | recurrence scan only (all positive); PFS, OS | dose details | IDH (MGMT not listed) | NIfTI CC BY 4.0; DICOM controlled | 19 GB | positives only; not a surveillance set |
| Brain-Tumor-Progression | [U] (Schmainda, likely MCW) | 20 / 40 (post-CRT and at progression) | T1, T1c, T2, FLAIR | ADC, **DSC (nCBF, nRCBV, sRCBV)** | binary | scan 2 = progression (clinical) | no file | [U] | controlled | 3.2 GB | too small |
| ACRIN-DSC-MR-Brain (ACRIN 6677 / RTOG 0625) | multicentre trial | 123 enrolled, 107 evaluable / 566 studies | T1, T1c, T2, FLAIR | **DSC**, DCE, DWI, MRS | [U] | Macdonald / RANO progression, PFS, OS | trial schedule | [U] | controlled; clinical CC BY 4.0 | 87 GB | different setting (recurrent GBM on bevacizumab) |
| ACRIN-FMISO-Brain (ACRIN 6684) | multicentre trial | 45 / mostly baseline | T1, T1c, T2, FLAIR | DSC 37, DCE 31, DTI 39 | [U] | progression dates, survival, KPS | [U] | MGMT | controlled | 96 GB | baseline only; not surveillance |
| QIN-GBM-Treatment-Response | [U] | 54 / 106 (two pre-therapy baselines) | T1, T1c, T2, FLAIR, MEMPRAGE | DSC, DCE, DWI | [U] | none | no | [U] | controlled | 34 GB | not surveillance |
| BraTS 2024 post-treatment glioma | Duke ~680, UCSF ~600, **Missouri ~400**, UCSD ~350, Heidelberg ~300, Michigan ~100, Indiana ~70 | ~2,200 cases | T1, T1c, T2, FLAIR | none | 4-class expert | **none** | no | no | open, CC BY 4.0 (Synapse) | [U] | pretraining / segmentation only |
| IvyGAP (radiology) | Swedish Neuroscience Inst. [U] | 39 / 390 studies (pre, post, follow-up) | [U] | [U] | [U] | outcomes in Ivy GAP clinical database [U] | [U] | [U] | controlled | 140 GB | too small, labels unclear |
| UPENN-GBM | Penn | 630 subjects; follow-up "for a few" | T1, T1c, T2, FLAIR, DSC, DTI [U for follow-up] | DSC, DTI (pre-op) | yes | OS, "tumour progression" in clinical CSV [U per scan] | [U] | yes | open, CC BY 4.0 | 357 GB | essentially pre-operative |
| TCGA-GBM | 8 centres | 259 with MRI, 575 dates, mostly pre-op | mixed | mixed | pre-op only | none per scan | no | yes | open | [U] | no |
| GLIS-RT | MGH | 230 (198 GBM), planning only | T1c, FLAIR | none | GTV, CTV | none | n/a | [U] | [U] | [U] | no |
| EGD (Erasmus) | Erasmus MC | 774, pre-operative | T1, T1c, T2, FLAIR | none | whole tumour | none | no | yes (WHO 2016) | DUA [U] | [U] | no |
| IMAGO release 1.0 | Amsterdam UMC | 500 pre-op; 381 early post-op (<= 14 d) | T1, T1c, T2, FLAIR | ADC 497 / 377; rCBV 269 pre-op, **24 post-op** | subset | survival [U]; no surveillance labels | [U] | IDH 500, 1p/19q 170 | EUCAIM registration | [U] | no surveillance scans yet ("1,700 patients", more releases planned) |
| UTSW-Glioma (2026) | UT Southwestern | 625, pre-operative | T1, T1c, T2, FLAIR | none | yes | none | no | yes | TCIA | [U] | no |
| Yale Glioma Dataset | Yale | 1,033 [U] | FLAIR, T1c | [U] | yes | grade, clinical [U] | [U] | [U] | [U] | [U] | follow-up not established [U] |

Nothing else with longitudinal post-RT glioma MRI plus per-scan outcomes was found in the 2025 to 2026 literature: the new 2025
to 2026 glioma releases found (IMAGO, UTSW-Glioma, a multi-hospital OpenNeuro GBM/MGMT set of 337 patients) are pre-operative or
early post-operative. The BraTS 2025 Lighthouse "brain tumour progression" task trains on LUMIERE and keeps its multi-centre
test set hidden; no labels are released.

## 2. Per-dataset records (new candidates only)

### 2.1 Burdenko-GBM-Progression (TCIA, DOI 10.7937/E1QP-D183)

- Centre and period: Burdenko National Medical Research Center of Neurosurgery, Moscow; primary GBM treated 2014 to 2020 **[V]**
  (TCIA page; arXiv:2511.18595). Independent of MU.
- Patients and scans: 180 patients, 645 studies, 4,956 series, 131.23 GB, DICOM **[V]**
  (<https://www.cancerimagingarchive.net/collection/burdenko-gbm-progression/>). RT-planning MRI (T1, T1c, T2, FLAIR), planning CT,
  RTSTRUCT (GTV, CTV, PTV, 10 organs), RTPLAN, RTDOSE; 1 to 8 follow-up MRIs with 2 to 4 sequences, minimum T1c + FLAIR **[V]**.
- Perfusion / diffusion: none described **[V, absence in page]**.
- Masks: RT structures on the planning scan; longitudinal GTV for a subset only **[V]**. Follow-up scans would need our own
  segmentation (T1c + FLAIR segmenter).
- Outcome labels, from the clinical CSV (our count, 2026-10-21; file
  <https://www.cancerimagingarchive.net/wp-content/uploads/Burdenko-GBM-clinical-data_20230410.csv>, CC BY 4.0) **[V]**:
  columns `Response_1st_fup` to `Response_10th_fup` with values stable 246, response 192, progression 162, pseudo progression 35,
  distant progression 9, mixed (e.g. "response, distant progression") 7. 178 / 180 patients have at least one label; 102 patients
  ever have progression; 33 ever have pseudoprogression. The TCIA page says response status is available "for all control
  studies" **[V]**. How the labels were assigned (reader, criteria, adjudication) is **not documented [U]**; all 36
  pseudoprogression labels fall within 83 days of RT end (median 21 d), which suggests retrospective assignment using the later
  course.
- Dates: anonymised (shifted) dates of surgery, RT start, RT end, topometric MRI, every follow-up, and death (78 deaths) **[V]**.
  First follow-up a median 20 days after RT end (n = 178) **[V, our count]**. This matches MU's treatment-aware design better than
  any other public set.
- Derived counts (our count; progression = "progression" or "distant progression", pseudoprogression = not progression; scans up to
  and including the first progression) **[V]**:
  - all post-RT follow-ups: 175 patients, 460 scans, 101 first-progression scans; forward 120-day label from the non-progression
    scans: 71 events, 157 non-events, 131 censored (no later follow-up);
  - scans >= 12 weeks after RT end: 139 patients, 279 scans, 87 first-progression scans; forward 120 d: 37 events, 84
    non-events, 71 censored.
- Clinical: sex, age, IDH1/2 (positive 13, negative 101, missing 66), MGMT (positive 37, negative 57, missing 86) **[V]**. KPS,
  steroids, chemotherapy dates: not in the CSV **[V, absence]**.
- Access: images under the NIH Controlled Data Access Policy **[V]**. Since 8 July 2025 TCIA no longer hosts controlled data:
  requests go through dbGaP and download through the NCI Cancer Research Data Commons with an API key and the TCIA Data Retriever
  **[V]** (<https://www.cancerimagingarchive.net/nih-controlled-data-access-policy/>). The requester must be at tenure-track
  professor or senior-scientist level; students and postdocs cannot apply on their own **[V]**. The exact dbGaP study accession
  (phs number) for this collection was not confirmed **[U]**.
- Published results on it: 11 deep architectures, best AUC 0.57 (first follow-up) and 0.66 (second) for progression vs
  pseudoprogression (Guo and Mirzaei 2026, *Cancers* 18:36); Gomaa et al. 2025 used 59 Burdenko patients (34 TP, 25 PsP) and
  reached external AUC 0.753 on 20 Erlangen patients, clinical-only 0.727 **[V]** (<https://pmc.ncbi.nlm.nih.gov/articles/PMC12085623/>).
  STRIDE (arXiv:2610.08848) reports macro AUC 0.816 for 3-class SD/PsP/TP with patient-level CV **[secondary, see comparison.md]**.

### 2.2 UCSF-ALPTDG (UCSF Adult Longitudinal Post-Treatment Diffuse Glioma)

- Paper: Fields et al., *Radiology: AI* 2024, doi:10.1148/ryai.230182 (PMC11294954) **[V]**.
- Centre and period: UCSF, single centre, January 2018 to December 2019 **[V]**. Not MU. Included in BraTS 2024 as "UCSF-LPTDG" **[V]**
  (<https://arxiv.org/html/2405.18368>), so BraTS-trained segmenters and foundation models have seen these images.
- Patients and scans: 298 patients, 2 consecutive post-treatment scans each (596) **[V]**; 248 train / 50 test split **[V]** (RSNA
  Atlas card). WHO 2021: 80 glioblastoma, 58 IDH-mutant astrocytoma, 9 IDH-wild-type astrocytoma, 62 oligodendroglioma **[V]**.
- Sequences: T1 pre and post contrast, T2, FLAIR **[V]**. No perfusion or diffusion **[V, absence]**.
- Masks: expert voxelwise ET, SNFH, NETC, resection cavity, plus longitudinal change masks for ET and SNFH **[V]**.
- Outcome: volumetric change category between the two scans (increased / decreased / unchanged / mixed), days from first scan to
  progression "based on expert multidisciplinary consensus in consideration of both radiologic and clinical factors", days to
  death **[V]**. Number who progressed: not stated **[U]**. A forward label from scan 1 (and scan 2) can be derived from days to
  progression; censoring follow-up for non-progressors not described **[U]**.
- Clinical: IDH, MGMT, 1p/19q, ATRX, treatment history incl. chemotherapy regimens, days from first surgery to first scan, inter-scan
  interval **[V]**. RT dates, time since RT, steroids, KPS, bevacizumab: not mentioned **[U]**.
- Access: "public, noncommercial use after agreeing to a data use agreement" via <https://imagingdatasets.ucsf.edu/dataset/2> **[V]**
  (portal is JavaScript; registration and DUA wording not read **[U]**). Contact listed: Jeff Rudie **[V]**. Size **[U]**.

### 2.3 RHUH-GBM (TCIA, DOI 10.7937/4545-c905)

- 40 GBM patients, 120 studies: pre-operative, early post-operative (< 72 h) and the scan at which recurrence was diagnosed; no
  intermediate surveillance scans **[V]** (<https://pmc.ncbi.nlm.nih.gov/articles/PMC10551826>).
- T1, T2, FLAIR, T1c, ADC; 3 scanners, 2 centres **[V]**. Expert-corrected necrosis / oedema / enhancing masks **[V]**.
- Clinical: age, sex, KPS, OS, PFS (median 198 d), extent of resection, systemic therapy, RT dose / technique / fractions, IDH, ATRX,
  Ki-67 **[V]**; recurrence by modified RANO **[V]**.
- Access: NIfTI + masks CC BY 4.0 (2.9 GB); DICOM controlled (16 GB) **[V]** (<https://www.cancerimagingarchive.net/collection/rhuh-gbm/>).
- Triage value: every follow-up scan is a positive, so it cannot test discrimination on its own.

### 2.4 Perfusion-bearing collections

- UCSD-PTGBM: DSC + ASL + DWI/ADC + RSI, 243 timepoints, 178 patients; 192 tumour (45 pathology-proven) vs 51 post-treatment change
  (4 pathology-proven PsP, 9 clinical PsP, 10 radiation necrosis, 28 non-specific) **[V]** (PMC12886825). How many timepoints have
  DSC vs ASL: not stated **[U]**. 40 patients / 60 timepoints held out for BraTS 2025 **[V]**. Enriched, mostly one scan per patient:
  a detection (not surveillance) design.
- ACRIN-DSC-MR-Brain: recurrent GBM on bevacizumab with irinotecan or temozolomide; 107 evaluable with baseline and 8- and 16-week
  scans; DSC, DCE, DWI; Macdonald and RANO progression, PFS, OS **[V]**
  (<https://www.cancerimagingarchive.net/collection/acrin-dsc-mr-brain/>). Anti-angiogenic therapy changes enhancement and rCBV,
  so it does not transport to first-line post-RT surveillance.
- Brain-Tumor-Progression: 20 patients, DSC-derived nCBF / nRCBV / sRCBV + ADC, one scan within 90 days after CRT and one at
  progression **[V]** (<https://www.cancerimagingarchive.net/collection/brain-tumor-progression/>).
- ACRIN-FMISO-Brain: newly diagnosed GBM, baseline within 2 weeks of therapy (mid- and post-therapy scans dropped after case 4);
  DSC 37, DCE 31 **[V]**.
- QIN-GBM-Treatment-Response: 54 patients, two pre-therapy scans 2 to 5 days apart (test-retest); DSC, DCE, DWI; no outcomes **[V]**.
- IMAGO: rCBV for 269 pre-operative and 24 post-operative cases (post-operative = within 14 days of surgery) **[V]** (Europe PMC
  abstract, doi:10.1038/s41597-026-07424-8).

**There is no public dataset with DSC/DCE perfusion at post-RT surveillance timepoints at scale.** The best is UCSD-PTGBM (a few
hundred enriched, mostly single timepoints); all others are < 25 patients, pre-therapy, or recurrent-GBM trials on bevacizumab.
ADC at follow-up exists in CFB-GBM (t1 132, t2 91), UCSD-PTGBM, RHUH-GBM (recurrence scan) and Brain-Tumor-Progression.

### 2.5 Checked and excluded

- BraTS 2024 GLI post-treatment: ~2,200 cases from 7 sites incl. ~400 from Missouri; images and masks only, no clinical or outcome
  data, CC BY 4.0 on Synapse **[V]** (<https://arxiv.org/html/2405.18368>). Useful only for self-supervised pretraining or
  segmentation; it contains MU, UCSF-ALPTDG and UCSD-PTGBM images, so any of them used as a test set must be excluded from
  pretraining.
- UPENN-GBM: pre-operative baseline for 611; "de novo and recurrent cases for a few"; CC BY 4.0; 357 GB **[V]**. Number with
  follow-up not stated **[U]**.
- TCGA-GBM: 259 patients, 575 dates, predominantly pre-operative **[V, LUMIERE paper via search]**.
- GLIS-RT: 230 MGH patients, RT-planning T1c + FLAIR with GTV/CTV only **[V]**.
- EGD: pre-operative only **[V]** (PubMed abstract). IMAGO, UTSW-Glioma: pre-operative or early post-operative **[V]**.
- IvyGAP radiology: 39 patients, 390 studies incl. follow-up; controlled; per-scan outcomes not documented **[U]**.
- QIN-GBM-Treatment-Response, ACRIN-FMISO-Brain: no surveillance timepoints **[V]**.
- Yale Glioma Dataset (1,033 patients, ISMRM 2023): follow-up content and access not established **[U]**.

## 3. Can these be pooled for a multicentre triage model?

### 3.1 Harmonised label

The label definitions differ at the source:

| Dataset | What "progression" means | Timing precision |
|---|---|---|
| MU | EMR-documented progression date (imaging and/or clinical) | date |
| LUMIERE | expert RANO PD at a rated scan | scan |
| Burdenko | centre-assigned "progression" at a follow-up; pseudoprogression separately labelled; method undocumented | scan |
| UCSF-ALPTDG | days to progression by multidisciplinary consensus | days |
| CFB-GBM | volumetric RANO 2.0 computed from GTV (algorithmic, no clinical input) | t1 / t2 only |
| UCSD-PTGBM | tumour vs treatment change at the scan (pathology or clinical follow-up) | scan (concurrent) |

A common definition is achievable for four of them: **first progression, dated at the scan (or day) at which it was declared;
pseudoprogression and treatment-related change count as non-progression; index scans after RT end (strict variant: >= 12 weeks after
RT end); horizon 120 d; death without progression and loss to follow-up censor**. This works for MU, Burdenko (RT end known),
UCSF-ALPTDG (with "days from surgery" standing in for time since RT, which is a real mismatch) and LUMIERE (no RT dates: time since
surgery only). CFB-GBM fits only as a small secondary set (one t1 to t2 interval per patient; algorithmic label). UCSD-PTGBM fits a
concurrent "detection" label, not a forward one.

Two task definitions should be kept apart:
- **Forward prediction** (progression within 120 d of a non-progression scan): the MU task. Burdenko, LUMIERE, UCSF-ALPTDG support it.
- **Concurrent detection** (is this scan the progression scan?): MU's documented-progression scan, Burdenko's first-progression
  follow-up, LUMIERE's first PD, UCSD-PTGBM tumour vs change. Easier and closer to radiologist triage, but the label is partly the
  reading of the same images.

### 3.2 Estimated pool (grade 4, post-RT surveillance, scans up to first progression)

| Dataset | Patients | Scans | Forward-120 d events / non-events / censored | Concurrent first-PD scans |
|---|---|---|---|---|
| MU (intended use, RT started) | 86 | 173 | 88 / 84 / 1 | [U, not recounted here] |
| LUMIERE (index scans) | 61 | 132 | 47 / 76 / 9 | ~61 or fewer [U] |
| Burdenko (all post-RT) | 175 | 460 | 71 / 157 / 131 | 101 |
| Burdenko (>= 12 weeks after RT) | 139 | 279 | 37 / 84 / 71 | 87 |
| UCSF-ALPTDG (GBM only) | 80 | 160 | [U]; at most ~80 if every GBM progressed | n/a (label is days, not scan) |
| CFB-GBM (t1 to t2) | 107 | 107 | 30 PD / 77 | n/a |
| **Total (forward, excluding UCSF events)** | **~510** | **~1,030** | **~236 events + UCSF** | |

So a realistic pooled forward-prediction set is about 1,000 scans, 500 patients and 250 to 300 events across 5 centres, of which
about 300 to 350 events would come from 3 to 4 centres with usable time-since-RT. With Burdenko held out as the unseen centre, the
test has 71 events and 157 non-events (all post-RT) or 37 / 84 (>= 12 weeks). At those sizes the 95 % CI of an AUC near 0.75 is
roughly +/- 0.06 to +/- 0.09, so the test can tell 0.75 from 0.60 but cannot confirm a lower bound above 0.70.

### 3.3 Common feature set

Only age, sex, IDH and MGMT (with unknowns), time since surgery, T1c and FLAIR are available in all candidate centres. Time since
RT end is available in MU, Burdenko and (approximately) CFB-GBM; not in LUMIERE or UCSF-ALPTDG. Burdenko follow-ups guarantee only
T1c + FLAIR. MU's treatment block (prescription, chemotherapy course), which carries most of the current 0.60, does not transport.

### 3.4 Main blockers

1. **No perfusion at surveillance scale.** The literature that reaches 0.75 to 0.85 externally relies on DSC/DCE or DWI (Booth 2022
   meta-analysis pooled AUC 0.77; conventional-only 0.65 to 0.76; `docs/PUBLICATION_PLAN.md`). Public post-RT surveillance data are
   conventional MRI only, apart from ADC in CFB-GBM and enriched single-timepoint DSC in UCSD-PTGBM.
2. **Labels are heterogeneous and partly undocumented.** Burdenko's labelling method is not described; UCSF's is consensus with
   clinical input; CFB's is algorithmic; MU's is EMR documentation. Label noise at the source caps attainable AUC, and between-centre
   differences in labelling will look like domain shift.
3. **Treatment timing is missing in two of four forward-label centres** (LUMIERE, UCSF-ALPTDG), and that is the information that
   carries the current signal.
4. **Access.** Burdenko is dbGaP controlled access (PI-level requester, institutional sign-off, NCI CRDC download); UCSF-ALPTDG needs
   a non-commercial DUA; CFB-GBM and UCSD-PTGBM images are Aspera-only and Aspera is blocked from the cluster
   ([DATASETS.md](DATASETS.md)).
5. **Leakage through BraTS 2024.** MU, UCSF-ALPTDG and UCSD-PTGBM are in BraTS 2024; any BraTS-pretrained encoder or segmenter has
   seen them. Burdenko, LUMIERE, CFB-GBM and RHUH are not listed among BraTS 2024 sites and are the clean unseen-centre candidates.
6. **Published ceiling on the best candidate.** On Burdenko itself, conventional-MRI deep models reach AUC 0.57 to 0.66 for TP vs
   PsP; the best externally tested conventional model (Gomaa 2025) reached 0.753 on 20 patients with clinical-only 0.727.

## 4. Ranked recommendation: what to acquire first

1. **Burdenko-GBM-Progression** (largest independent centre with per-follow-up labels, pseudoprogression adjudication and RT dates;
   the natural locked unseen-centre test, or a third training centre with LUMIERE as test). The clinical CSV is already open and
   summarised above. User steps:
   - Confirm that a PI at the user's institution at tenure-track or senior-scientist level will be the requester (students and
     postdocs cannot apply alone).
   - The PI logs into dbGaP with an eRA Commons (or NIH-recognised) account, finds the TCIA controlled-access study that contains
     Burdenko-GBM-Progression (the "face" collections; confirm the phs number on the TCIA policy page or with help@cancerimagingarchive.net),
     and submits a Data Access Request with a research-use statement; the institution's Signing Official approves it. The user is
     added as internal collaborator.
   - After approval: log into the NCI Cancer Research Data Commons, create an API key (JSON), and download with the TCIA Data
     Retriever using the Burdenko manifest (131 GB). Check that the cluster allows the Data Retriever's outbound connections (the
     Aspera block does not necessarily apply, but test first).
2. **UCSF-ALPTDG** (second independent centre, consensus progression, molecular markers, expert masks; 80 GBM, the rest lower
   grade). User steps: register at <https://imagingdatasets.ucsf.edu/dataset/2> with name, institution and email; accept the
   non-commercial DUA (check whether an institutional signature is required); download. Ask the authors (contact on the RSNA Atlas
   card) whether RT dates or time since RT can be shared, since that is the largest gap.
3. **UCSD-PTGBM images** (already open, CC BY 4.0; clinical tables on disk). The only public route to test whether perfusion (DSC,
   ASL) and advanced diffusion lift a concurrent tumour-vs-treatment-change model above conventional MRI; it does not serve the
   forward surveillance task. User step: ask HPC support to open TCP and UDP 33001 to 144.30.235.113 for Aspera, or download the
   45 GB on another machine and rsync. (The same unblocks CFB-GBM's 208 GB.)

Optional cheap addition: RHUH-GBM NIfTI + masks (CC BY 4.0, 2.9 GB, no controlled access) as 40 extra independent positive
recurrence scans with ADC, for sensitivity checks only.

## 5. Feasibility verdict

- **Forward prediction (progression within 120 d of a post-RT surveillance scan) at AUC >= 0.75 on an unseen centre: unlikely.**
  Reasons: (i) every public forward-label dataset is conventional MRI, and on conventional MRI the signal after RT is weak (MU 0.60,
  LUMIERE 0.61 to 0.72, Burdenko 0.57 to 0.66 in published work); (ii) the information that carries MU's signal (treatment timing)
  is missing in half of the candidate centres; (iii) labels differ in kind between centres; (iv) a pooled set of about 1,000 scans
  and 250 to 300 events is enough to estimate an AUC but not obviously enough to learn image features that published single-centre
  work has not found.
- **Concurrent detection (flag the scan at which progression is declared) at AUC >= 0.75: uncertain.** Concurrent RANO
  classification on LUMIERE reaches mean one-vs-rest AUC 0.81 with patient-wise CV (Tikhonov 2025) and STRIDE reports 0.82 on
  Burdenko, but neither is an unseen-centre test, the labels are readings of the same images, and the clinically hard part
  (pseudoprogression in the first 12 weeks) remains near chance in published work.
- **Perfusion-based triage: not testable at surveillance scale with public data.** It would need a data-sharing agreement with a
  centre that acquires DSC routinely at follow-up (for example the UCSD or Penn groups), not a public download.

Sources (read 2026-10-21): TCIA collection pages for
[Burdenko-GBM-Progression](https://www.cancerimagingarchive.net/collection/burdenko-gbm-progression/),
[RHUH-GBM](https://www.cancerimagingarchive.net/collection/rhuh-gbm/),
[QIN-GBM-Treatment-Response](https://www.cancerimagingarchive.net/collection/qin-gbm-treatment-response/),
[Brain-Tumor-Progression](https://www.cancerimagingarchive.net/collection/brain-tumor-progression/),
[ACRIN-DSC-MR-Brain](https://www.cancerimagingarchive.net/collection/acrin-dsc-mr-brain/),
[ACRIN-FMISO-Brain](https://www.cancerimagingarchive.net/collection/acrin-fmiso-brain/),
[IvyGAP](https://www.cancerimagingarchive.net/collection/ivygap/),
[UPENN-GBM](https://www.cancerimagingarchive.net/collection/upenn-gbm/),
[MU-Glioma-Post](https://www.cancerimagingarchive.net/collection/mu-glioma-post/);
[TCIA NIH controlled data access policy](https://www.cancerimagingarchive.net/nih-controlled-data-access-policy/);
[Burdenko clinical CSV](https://www.cancerimagingarchive.net/wp-content/uploads/Burdenko-GBM-clinical-data_20230410.csv);
[UCSF-ALPTDG paper (PMC11294954)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11294954) and
[RSNA Atlas card](https://atlas.rsna.org/cards/48595a48-e1e6-4ab5-8844-e895a3482c01);
[RHUH-GBM paper (PMC10551826)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10551826);
[UCSD-PTGBM paper (PMC12886825)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12886825/);
[BraTS 2024 post-treatment paper](https://arxiv.org/html/2405.18368);
[BraTS 2025 Lighthouse description](https://zenodo.org/records/15094823);
[Gomaa et al. 2025 (PMC12085623)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12085623/);
[Guo and Mirzaei, arXiv:2511.18595](https://arxiv.org/abs/2511.18595);
[public adult glioma dataset review, arXiv:2409.00109](https://arxiv.org/html/2409.00109v2);
IMAGO abstract via [Europe PMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%22IMAGO%22%20AND%20glioma%20AND%20%22Scientific%20Data%22&format=json&resultType=core)
(doi:10.1038/s41597-026-07424-8); UTSW-Glioma ([Scientific Data 2026](https://www.nature.com/articles/s41597-026-07274-4), via search snippet);
GLIS-RT, TCGA-GBM, EGD and Yale facts via search snippets of the TCIA wiki, the LUMIERE paper and PubMed.
