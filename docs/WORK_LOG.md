# PRISM work log (2026-09-14 to 2026-11-01)

A handover log for anyone (human or agent) picking up this repository with no context. It records everything that was
done, including what failed, was abandoned or was superseded, why, and what replaced it. It was assembled on 2026-11-01
from the git history (commits since 2026-09-14), `docs/results/` (analysis notes), `docs/manuscript/`, `docs/literature/`,
the code in `scripts/`, `prism/` and `legacy/`, and the project memory notes. Each entry names its source document and
code path; where code no longer exists this is said. Numbers are aggregate only; no patient or scan IDs appear, by rule.

**Status words used throughout:** kept (in the current pipeline), superseded (replaced by a named later version),
failed (tested, did not do what was hoped), abandoned (stopped without a result).

## Start here

0. **Branch (2026-11-02).** All work is done directly on `main`. `manuscript-week` was merged into `main` (111aa5d) and deleted. Commit hashes cited below are unchanged and reachable from `main`. A machine reset on 2026-11-02 wiped `data/`, `outputs/`, the external-cohort folders and the environments; see D5.

1. **Read the standing rules first: section D4.** In particular: no Claude co-author line in commits; never call PRISM
   "published"; patient data stays on the cluster and only local language models may see records; aggregate numbers
   only, and the UCSF download URL is secret; pre-specify a plan before any real-label run; rebuild and commit
   `paper/main.pdf` after every paper change; `submit.sh` was committed by the author on 2026-11-02; LOCKED text needs the author's approval.
2. **Current state in one paragraph.** PRISM is the author's own (unpublished) system for post-treatment glioma
   surveillance MRI: an image pathway (segmented tumour and its change), a treatment-timeline pathway and a combined
   score, each with a three-part confidence (conformal set, pathway disagreement, a reliability card by phase of care
   and enhancement), and a report written by a local language model and checked deterministically against the
   per-scan record. Developed on MU-Glioma-Post, tested locked on LUMIERE and UCSF-ALPTDG. The manuscript
   (`paper/main.tex`, target CMBBE: Imaging & Visualization) leads with the finding that what carries a progression
   score depends on how a cohort was scanned and labelled; four contributions were narrowed against prior art on
   2026-11-01 (`docs/literature/PRIOR_ART_2026-11-01.md`).
3. **Where the story got here:** the earlier 120-day forward-prediction question, imaging-vs-timing model searches,
   triage and detection feasibility (both NO-GO) and many label and evaluation fixes are in sections A and B; the
   system, external tests and reports in C; the dated timeline, manuscript history and infrastructure in D.
4. **What is pending:** section D5.

## Contents

- **A. Data, cohorts, segmentation and labels**: original PRISM report and its reproduction; datasets used and
  rejected; cohort flows; segmentation and masks; features; labels and endpoints; a table of every leak and bug found.
- **B. Models and experiments, including every failed one**: a summary table of what did not work; legacy pipelines;
  the forward 120-day task; diagnostics; deep models; triage and detection NO-GOs; Christodoulou replication; gotchas.
- **C. The PRISM system, external tests and reports**: design; confidence parts and audit; LUMIERE and UCSF tests with
  every pre-specified rule met or failed; the report agent (v1 to v3.1, model ladder, ablations); how to run; gotchas.
- **D. Timeline, manuscript history, infrastructure and working rules**: dated phases with commit hashes; framings
  tried and dropped; author reactions; councils; build; environment and cluster; standing rules (D4); pending (D5).

Note on names: "C1" and "C2" each refer to two different things in this repo (analysis notes vs model names); see B.12.

---

# A. Data, cohorts, segmentation and labels

Scope: what the original PRISM course-project pipeline did with the data, what reproduced, every dataset that was used,
considered or rejected, how cohorts, masks, features and labels were built, and every data-handling bug or leak found and
how it was fixed. Modelling results appear here only where they were the evidence for a data decision. Aggregate numbers
only. Paths are relative to the repo root `/project/community/sbandred/prism-gbm-surveillance` unless absolute.

Status words: **kept** (in the current pipeline), **superseded** (replaced by a later version, which is named),
**failed** (tested and did not do what was hoped), **abandoned** (stopped without a result).

---

## A.1 The original PRISM report (starting point, before 2026-09-14)

Source: `docs/original_prism_report.pdf` (course report "PRISM: A Multimodal Pipeline for Post-Treatment Glioblastoma
Surveillance with Interpretable Clinical Reporting", five student authors; committed in 92e7544, 2026-10-10). The code is
the initial commit 21c1540 ("init: code reproducability"), now under `legacy/` (moved in 92e7544).

What the report claimed, and how the data were handled:

| Component | Report description | Code now |
|---|---|---|
| Dataset | MU-Glioma-Post, 203 patients, 594 post-treatment timepoints, ~75% progressors (3:1), 1-6 timepoints per patient; "patient-aware" train/val/test split | `legacy/radiomics/` |
| Imaging encoder | "Swin UNETR" encoder, BraTS-pretrained and fine-tuned (Methods); crop to tumour bbox + 10 voxels, resample to 128^3, 1-99th percentile clip, global average pooling to a 48-d embedding. The Discussion admits it was random-initialised and not fine-tuned | `legacy/swin_unetr/swinunetr-pipeline-kaggle.ipynb`, `extract_embeddings.py` |
| Radiomics | Optuna over LightGBM/LogReg/RF/SVM; exported calibrated LogReg on 48 features (23 T1c, 19 FLAIR, 6 clinical); ROI = labels 1-3 (cavity excluded); N4; LoG + wavelet; Platt; label = progression within 120 d of the scan | `legacy/radiomics/radiomics_pipeline/workflows/train.py`, `legacy/radiomics/models/calibrated/` |
| Fusion | Late-fusion MLP, ModDrop 30%, focal loss, threshold 0.48 | `legacy/mlp_fusion/` |
| Agent | 3-layer RANO 2.0 rules + concordance + GPT-4.1-mini report | `legacy/glioma_agent/` |
| Headline | Radiomics test AUC 0.8043, Brier 0.154, threshold 0.4553; fusion AUC 0.801, acc 80.95%, macro F1 0.768; "reframing from at-scan status to 120-d forward label raised AUC 0.599 -> 0.804" | `legacy/radiomics/README.md` table (rows 0.599 / 0.621 / 0.674 / 0.873 / 0.804) |

## A.2 Reproduction on the cluster (2026-10-04/05)

Docs: `legacy/reproduction/{README,FINDINGS,AUDIT,PROCEDURES,LITERATURE}.md` (commit 677139d, 2026-10-05); memory note
`reproduction-status.md`. Run on orchard-community-4 (4x H100). Code: `legacy/reproduction/` (`run_fusion_seeds.py`,
`run_agent.py`, `make_fusion_inputs.py`, `radiomics/{parallel_prep,run_train}.py`,
`validation/{fusion_validation,linear_probe,late_fusion_bootstrap,seed_sweep}.py`).

**What reproduced (all reported numbers reproduce from code + raw data):**

| Stage | Reported | Reproduced | Note |
|---|---|---|---|
| Radiomics prep | HF `sbandred/mu-glioma-post-processed` | 7/7 manifests identical, features to float noise | cached `label` in reference feature JSONs is stale (other label mode); training ignores it |
| Calibrated LogReg-48 | AUC 0.8043, Brier 0.154 | identical (same 30 test patients) | from the shipped bundle and from refitting its columns/params |
| Default `main.py train` | LogReg-48 | **selects SVM-32, AUC 0.7977** | shipped config came from run `repeated_forward_hybrid_basic_corrected/seed_62`, whose search command is not in the repo (root cause 2 below) |
| SWIN embeddings | 594 x 48 | identical only with `MODEL_BUILD_INDEX = 2` | root cause 1 below |
| Fusion MLP (shipped weights) | AUC 0.8006, acc 0.8095, F1 0.6522 | identical (probs within 1e-4) | |
| Fusion retrained 50 seeds | same | AUC ~0.80; acc at ~95th pct, F1 ~max | shipped fusion is a lucky draw |
| Agent demo patient | fusion probs | identical; SHAP within noise; LLM text not run (no API key) | demo patient was in-sample |
| Not reproduced | README rows 0.599, 0.621, 0.674, 0.873 | — | never re-run |

**Root causes found during reproduction:**
1. **SWIN build index.** The notebook built `SwinEncoder3D` three times after `seed(42)` before extracting; only the
   third build (index 2) reproduces the embeddings. Encoded as `MODEL_BUILD_INDEX = 2` in
   `legacy/swin_unetr/extract_embeddings.py` (line ~95).
2. **SVM vs LogReg search.** The shipped LogReg-48 came from an unrecorded run whose seed (62, called "preferred" in
   `main.py`) also draws the test patients (`train.py:1842`), so test-split selection cannot be excluded (AUDIT #7).
   The default search picks SVM-32 and then `export_calibrated` crashes, because `shap.LinearExplainer` cannot take a
   non-linear model.
3. Other gotchas: `openpyxl` is needed for build_index; preprocessing requires the dataset physically under `radiomics/`
   (a symlink outside fails `repo_relative`); `glioma_agent/models/MLPFusion` lacked `best_fusion_model.pth`; the
   shipped `model_bundle.pkl` only unpickles with `scripts.run_postoperative_progression_surveillance` aliased to
   `radiomics_pipeline.workflows.train`. The legacy root paths (`radiomics/PKG-MU-Glioma-Post`, `mu-glioma-post-raw`,
   `reference-processed`, `SWIN UNetR/`) no longer exist. Data now live in `data/` (A.3), code in `legacy/`.

**Fault audit (legacy/reproduction/AUDIT.md, 15 faults; the data/label ones matter here):**

| # | Fault | Severity | Effect / what replaced it |
|---|---|---|---|
| 4 | "SWIN UNETR" is a ~0.1M-param random, untrained encoder | High | embeddings alone AUC ~0.50 in fusion; linear probe 0.55 CV / 0.62 test; PC1 (92% var) tracks cavity/lesion size |
| 8 | Model uses undocumented molecular codes (IDH1=2, IDH2=2, MGMT=4, ATRX=2; dictionary defines IDH 0/1, MGMT 0-3) | Medium | it learns testing practice (e.g. IDH2=2 progression 0.57 vs 0.79). Fixed in the PRISM codebook (D3): undocumented -> explicit `unknown` |
| 9 | 59/97 never-progressor negatives have < 120 d follow-up (`train.py:660-661` labels them 0) | Medium | led to the censoring-aware labels (A.6) |
| 10 | Bootstrap CI resamples scans, not patients | Medium | patient-level CI ~[0.66, 0.91]; all later work uses patient-cluster bootstraps |
| 11 | Feature ranking on all training labels before CV search (`train.py:1873`) | Low | CV AUCs optimistic; all later selection is in-fold |
| 12 | README rows compare different test designs (96/84/30 scans); "LogReg-32" but bundle has 48 features | Low | — |
| 13 | `LABEL_MAP` in `legacy/radiomics/radiomics_tools/metrics/constants.py` says 1=ET, 3=SNFH; data are **1=NETC, 2=SNFH, 3=ET, 4=RC** | Low | confirmed by BraTS21 zero-shot (ET output vs label 3 Dice 0.81, vs label 1 0.00). Not fixed in legacy (still wrong there); shipped model unaffected (uses 1-3 as a union). PRISM uses `prism/config.py` `LABEL_NETC, LABEL_SNFH, LABEL_ET, LABEL_RC = 1, 2, 3, 4` |
| 14 | Notebook cell ran 3x; fusion unseeded; `train_predictions.csv` (= radiomics OOF, raw + calibrated) not produced by any script | Low | root cause 1 |
| — | Legacy `label_for_case` returns 0 for non-progressors before checking the MRI date, so one scan with an unknown MRI date was included | Low | found when building the PRISM cohort (C1_endpoint.md, D1); PRISM excludes unknown MRI days |
| — | Legacy radiomics texture used a within-lesion z-score + binWidth 25 -> about **2 grey levels** | — | found 2026-10-06; replaced by v2 extraction (A.5) |

Fusion faults (test-loss checkpointing, hand-tuned 0.48, operating-point "gain") are in the modelling section. The
verdict here: the radiomics test protocol itself was clean (calibration and threshold on OOF training predictions,
patient-grouped CV). The radiomics model has real timing signal: AUC 0.73 among progressors only (<= 120 d vs > 120 d).

**BraTS SwinUNETR rebuild (2026-10-04/05, user's chosen direction then; superseded).** Code `legacy/swin_unetr/`
(`swin_common.py`, `zero_shot_check.py`, `finetune_seg.py`, `make_crops.py`, `finetune_progression.py`,
`run_stage2_lanes.sh`, `export_swin_embeddings.py`). Weights: MONAI research-contributions BraTS21 fold 1
(`fold1_f48_ep300_4gpu_dice0_9059`; now `data/weights/brats21_swinunetr_fold1_f48/model.pt`). Channel order BraTS
flair,t1ce,t1,t2 = MU t2f,t1c,t1n,t2w. Zero-shot WT Dice 0.85. Stage-1 seg fine-tune (adds a resection-cavity head):
val mean Dice 0.495 -> 0.697 (RC 0.01 -> 0.53). **Bug found:** global-average-pooled swinViT features are almost
identical across scans (corr ~1.0); lesion-masked multi-scale pooling + BatchNorm needed. Stage 2 image-only AUC: OOF
0.59-0.60, test 0.635 (seg init) / 0.652 (pretrained init); late fusion with radiomics delta -0.014 / +0.005, CIs span
0. `fusion_mlp.py` `LayerNorm(vision_dim)` zeroes a 1-d input, so a single image score cannot be fused. The stage-1/2
checkpoints were lost in the storage wipe and not retrained in that form. Later deep work (FINETUNE_DEEP.md) is in the
modelling section.

**Storage wipe (2026-10-05 ~15:04).** `/project/community/sbandred` was wiped (cause unknown, not by Claude). The user
restored git 21c1540. Session code was restored from `~/.claude/file-history` + transcripts and committed (5a2c234,
677139d). Raw data, BraTS weights and reference manifests were downloaded again.

**Literature consequence (legacy/reproduction/LITERATURE.md).** Christodoulou 2026 already reports binary radiomics AUC
0.80 on MU, so matching it is not novel. BraTS 2024 contains about 400 Missouri cases, so BraTS-2024-pretrained encoders
risk leakage on MU. This led to the PRISM v2 plan (a47ee3a, `docs/ARCHITECTURE_AND_CONTRIBUTIONS.md`): censoring-aware
endpoint (C1), compartment + delta features (C2), corrected radiomics (C3), LUMIERE external test.

---

## A.3 Datasets: used, considered, rejected

On-disk locations (`prism/config.py`; all overridable with `PRISM_DATA`, `PRISM_MU`, `PRISM_LUMIERE`,
`PRISM_UCSF_ROOT`, `PRISM_OUTPUTS`):

| Dataset | Path | Size on disk | Role | Status |
|---|---|---|---|---|
| MU-Glioma-Post (TCIA; HF mirror `sbandred/mu-glioma-post-raw`) | `data/mu-glioma-post/` (`MU-Glioma-Post/` 203 patient dirs, `MU-Glioma-Post_ClinicalData-July2025.xlsx`, `MU-Glioma-Post_Segmentation_Volumes.xlsx`) | 12 GB | development | kept |
| PRISM legacy processed features (HF `sbandred/mu-glioma-post-processed`) | `data/mu-reference-processed/` | 192 MB | legacy 2-grey-level radiomics comparator | kept as comparator only |
| LUMIERE (figshare, CC0; Suter 2022) | `data/lumiere` -> `/project/community/sbandred/lumiere/` (`Imaging-v202211.zip`, `LUMIERE-ExpertRating-v202211.csv`, demographics, MRinfo, completeness) | 33 GB | external test (forward + detection) | kept |
| UCSF-ALPTDG (DUA, non-commercial) | `/project/community/sbandred/ucsf/` (298 subject dirs, xlsx, zip 27.7 GiB kept, `INVENTORY.md`) | 56 GB | second external cohort (detection at scan 2) | kept. The download URL is a secret presigned link and is not recorded anywhere |
| CFB-GBM v4 (TCIA, CC BY 4.0) | `data/cfb-gbm/clinical/` (clinical v03, treatment v02, MRI/CT availability v02, RANO v04, PyRadiomics v03) | 6.9 MB tables | ADC test without images (A.5) | tables only. Images (208 GB) are Aspera-only and were blocked (TCP 33001/443 outbound blocked, HTTPS 8443 fallback 502) |
| UCSD-PTGBM v3 (TCIA, CC BY 4.0) | `data/ucsd-ptgbm/clinical/` | 108 KB | considered (perfusion) | tables only. Images (45 GB) Aspera-blocked; also in BraTS 2024 (IDs `BraTS-GLI-...`), so BraTS-trained models have seen them |
| Public report text (RadGenome-Brain MRI, MultiCaRe) | `data/public_reports/` | 230 MB | style reference for the report generator | used only for form (DATASETS.md second half) |
| Weights (BraTS21 SwinUNETR, BrainSegFounder BraTS fine-tune) | `data/weights/` | 489 MB | re-segmentation, deep arms | kept |

MU image layout: `MU-Glioma-Post/<patient>/<timepoint>/<stem>_brain_{t1n,t1c,t2f,t2w}.nii.gz` + `<stem>_tumorMask.nii.gz`.
The images are FeTS-preprocessed, skull-stripped, 1 mm BraTS/SRI24 space, 240x240x155, LPS. Masks are 4-class
(automated then neuroradiologist-refined, per the dataset paper). Clinical: single centre, ~97.5% Siemens, 94.6% White;
64% of FLAIR and almost all T2 acquired 2D (~5 mm), so texture is interpolated (PIPELINE_REVIEW.md F1, F3).

**Considered and not used** (docs/literature/DATASETS.md 2026-10-15, commit 9cc58e0; TRIAGE_DATASETS.md 2026-10-21,
commit 4dd40ae):

| Dataset | Why not |
|---|---|
| Burdenko-GBM-Progression (TCIA, 180 pts, 651 labelled follow-ups, RT start/end dates, pseudoprogression labels) | Ranked #1 to acquire, but dbGaP controlled access needs a tenure-track/senior PI requester. Only the open clinical CSV was summarised (forward 120 d: 71 events / 157 non-events / 131 censored). Not acquired |
| RHUH-GBM (40 pts, recurrence scans only) | every follow-up is positive; cannot test discrimination |
| Brain-Tumor-Progression (20 pts) | too small |
| ACRIN-DSC-MR-Brain, ACRIN-FMISO, QIN-GBM-Treatment-Response | recurrent/bevacizumab or baseline-only settings |
| BraTS 2024 post-treatment (~2,200 cases incl. ~400 Missouri, ~600 UCSF, ~350 UCSD) | no outcome labels; leakage source for MU/UCSF/UCSD |
| UPENN-GBM, TCGA-GBM, GLIS-RT, EGD, IMAGO, UTSW-Glioma, Yale, IvyGAP | pre-operative, planning-only, or labels unclear |
| MR-RATE (real report corpus) | gated form; not submitted on the user's behalf |

Triage pooling verdict (TRIAGE_DATASETS.md section 5): a realistic pool is ~1,000 scans / 500 patients / 250-300 events
over 5 centres. Forward 120-d triage at AUC >= 0.75 on an unseen centre: unlikely. Concurrent detection: uncertain.
Perfusion triage: not testable with public data. UCSF-ALPTDG was then acquired (2026-10-24).

---

## A.4 Cohort construction and flow

### MU-Glioma-Post (development)

Code: `prism/data/mu.py` (`python -m prism mu` -> `outputs/data/{mu_index,mu_cohort,mu_flow}.csv`); folds
`prism/models/folds.py` -> `outputs/data/folds.csv`. First built 2026-10-06 (bb479a2, then `prism/features.py`);
restructured 2026-10-10 (92e7544); label fixes 2026-10-11 (19747c7, 2dd60c8). Tests: `tests/test_prism_cohort.py`,
`tests/test_label_fixes.py`, `tests/test_labels_and_folds.py`.

Final flow (`docs/results/cohort_flow.csv`, `docs/manuscript/FLOW.md`, byte-identical to `outputs/`):

| Step | Scans | Patients | Excluded |
|---|---|---|---|
| All timepoints | 596 | 203 | – |
| All four sequences and mask present | 594 | 203 | 2 |
| Tumour (labels 1-3) present | 592 | 203 | 2 |
| MRI day known | 589 | 202 | 3 |
| MRI day plausible (>= -365 d, not before an earlier timepoint) | 588 | 202 | 1 |
| Progression date known for progressors | 588 | 202 | 0 |
| MRI not after recorded death | 580 | 202 | 8 |
| Before late treatment (2nd-line, immunotherapy, new treatment) | 501 | 199 | 79 |
| **Before first progression (index scans)** | **308** | **155** | 193 |
| Grade 4 subset (primary population) | 249 | 126 | – |

History: 2026-10-06 version 314 scans / 157 patients (grade 4 253/128), which matched legacy except the unknown-date
scan (A.2). The label fixes removed 6 scans and added none (one implausible MRI day, two single scans after death, three
scans of former "flag 0" progressors on or after their progression date) -> 308/155, grade 4 249/126.
Measurement table covers 591 timepoints (all MU scans with images and mask), so priors and nadir can use non-index scans.

Folds (D7): 5 x 5 repeated patient-grouped folds, stratified by 120-d status (incl. censored) and grade 4. They were
regenerated after the label fixes, because the stratification labels changed. Every later analysis (detection, phase
censoring, UCSF-trained-on-MU, deep arms) reuses `outputs/data/folds.csv`. Detection scans inherit their patient's fold.

Table 1 (`docs/manuscript/TABLE1_COHORT.md`, `table1.csv`): MU all gliomas median age 61, 52% male, IDH wt/mut/unknown
77/14/8%, MGMT meth/unmeth/unknown 34/47/19%, grade 4 81%. RT documented 66%, TMZ 61%. Grade 4 RT-completed-by-scan 67%,
early post-RT 39% with 65 unknown (63 RT never documented + 2 RT end date missing; this was resolved in
PHASE_CENSORING.md, after first being reported as just "unknown"). Single centre.

Derived populations used later:

| Population | Definition | Size (grade 4) | Doc |
|---|---|---|---|
| Forward 120-d cohort | index scans | 249 scans / 126 pts; 93 events / 117 non-events / 39 censored | FIX_LABELS.md |
| post_rt | RT completed by scan | 167 / 84 | PHASE_LADDER.md, CLEAN_LABEL.md |
| rt_pathway | RT documented at any time (uses future information, so an intended-use statement, not an as-of rule) | 186 / 89, 1 censored | PHASE_CENSORING.md |
| **rt_started (scan-day intended use)** | RT started by the scan day (as-of) | **173 / 86, 88 events, 1 censored** | INTENDED_USE.md (plan 74eaaf5) |
| Detection cohort | positive = first MRI with mask on/after progression date; primary negative = index scan with verified 120-d non-event; secondary = all index scans | all scans 64 pos / 117 neg; intended use 62 / 84 (80 pts) | DETECTION_TASK.md, `outputs/data/detection_cohort{.csv,_README.md}` (written before any model) |

Detection cohort note: 120 progression scans have complete images; 47 of them (42 grade 4) belong to patients with no
index scan, so they are absent from `folds.csv` and were excluded.

### LUMIERE (external)

Code: `prism/data/lumiere.py` (`python -m prism lumiere` -> `outputs/data/lumiere_cohort.csv`; the module asserts that
the flow's last step equals the cohort file). First external test 2026-10-09 (35d841e).

| Step | Studies | Patients | Excluded |
|---|---|---|---|
| All rated studies (expert RANO file) | 616 | 91 | – |
| Post-operative (week >= 2 after surgery) | 456 | 81 | 160 |
| Rated SD / PR / CR / Post-Op | 199 | 70 | 257 |
| Before first PD | 132 | 61 | 67 |
| **Not after recorded death (index scans)** | **132** | **61** | 0 |

Label at 120 d: 47 positive / 76 negative / 9 censored. Time = rating week x 7 since first surgery. No treatment fields
(no RT dates, dose or chemo), so MU's treatment block cannot be transported. `early_post_rt` = rater's "LessThan3Months"
flag (< ~90 d after RT), not MU's 0-84 d after the RT end date. This difference is documented and not harmonised.
Survival weeks exist for 56/61 patients with no censoring indicator, so a recorded survival time is used only as a
censoring time in the primary label. Detection cohort (`lumiere_detection()`): 178 scans; positive = first PD-rated scan,
negatives = earlier SD/PR/CR scans (rating-defined, not 120-d verified; 24 patients contribute positives with no
negative). Three studies are rated twice; one row per study is used (caught by the `past_only` duplicate assertion in
the segmentation figure, A.5).

### UCSF-ALPTDG (second external)

Code: `prism/data/ucsf.py` (`python -m prism.data.ucsf` -> `outputs/data/ucsf/{scans,flags}.csv`), test
`tests/test_ucsf.py`; docs UCSF_DATA.md (f461f11, 2026-10-25, descriptive only, no model), UCSF_PLAN.md (pre-specified,
0e7c9fe). 298 patients x 2 consecutive post-treatment scans = 596 scans; grade 4 140 patients, WHO 2021 GBM 80. One
scanner (GE 3T Discovery MR750). 59 grade-4 patients are also in UCSF-PDGM. UCSF and MU are both in BraTS 2024.

Data handling decided before any model (UCSF_DATA.md):
- **Sign conventions.** Column names ("from X to Y") and the dictionary ("Y - X") often disagree. Each event is
  re-expressed as days from scan 1 (positive = after), with the sign chosen from evidence. Examples: surgery -> RT median
  38 d under the chosen sign vs 1,125 d under the other; RT start = chemo start +-3 d in 187/240 vs 0/240.
  "Number of surgeries" is the total listed, not "prior to scan 1" as the dictionary says, so it was recomputed.
- **Date artefacts.** |days| > 20,000 (an empty date read as Excel day 0, or a typo) -> NaN. 31 patients / 40 flags in
  `flags.csv`. No scan was dropped.
- Progression dated before scan 1: 12 within 7 d are treated as progression at scan 1. The other 2 have an earlier
  progression, so the "next" progression is unknown and both their scans are excluded from all labels.
- Phase is only *plausible*: first RT start only, no end or dose, so a 6-week course is assumed. UCSF is almost entirely
  later post-RT surveillance (median RT start -> scan 1 = 383 d in GBM).
- Not buildable: RT end, dose, fractions, visit index, true nadir, full B1 timeline. The LUMIERE-transportable model T is
  buildable.
- **Primary label** `pos_s2_pm30`: scan 2 with first progression within +-30 d and nearer scan 2. Primary negatives =
  progression >= 120 d later, or >= 120 d of dated follow-up. Grade 4: 29 pos / 103 neg / 92 pts. Scan-2 evaluation set
  29 / 40. The label was chosen by Claude overnight and the author may change it. `et_increased` (an image-defined
  category) is only a secondary, circular reference.
- **Scan-2-only evaluation (UCSF_PLAN.md).** Positives can only be scan 2, so has-previous, days since previous and
  change features (all zero at scan 1) would separate the classes by design. The primary set is scan 2 only. All-scan
  analyses use only inputs that do not encode the timepoint.

---

## A.5 Segmentation and image features

### MU masks (kept) and their QA

`prism/analyses/diagnostics_imaging.py` (fc09ac4, 2026-10-11; DIAGNOSTICS_IMAGING.md):
- Volumes reproduce `MU-Glioma-Post_Segmentation_Volumes.xlsx`: r 0.9957-0.9998, exact voxel match 84-100% by label
  (NETC lowest). Disagreements are concentrated in a few patients where the xlsx has extra timepoints or a second mask
  version. Label permutation matrix: diagonal 0.94-0.97, off-diagonal <= 0.003. Intensity sanity: ET T1c/normal median
  1.45 (> 1 in 98%), SNFH FLAIR/normal 1.44 (> 1 in 100%). Visual QA of 12 random scans: no wrong masks.
- **Data issues logged, not changed:** 3 cross-patient pairs with identical masks plus 4 near-identical pairs (possible
  duplicate patients; should be reported to the data owners). A few implausible ET jumps of 3-20x within 3-12 days.
  22% of progressors have no MRI on or after the progression date.
- **Positive control failed (data, not code).** ET is larger at the progression scan than at the previous scan in only
  49% of 74 pairs (p 0.54). Lesion growth from nadir is larger in 79%. Imaging-only detection AUC 0.62-0.70. The median
  ET change within <= 14 d is 3.2x, larger than over 45-90 d; change size is unrelated to the gap (Spearman -0.01).

### Re-segmentation with one consistent model (2026-10-11, d82969b; RESEGMENTATION.md) - failed by pre-specified rule

Code `prism/features/reseg.py` (GPU inference), `prism/analyses/reseg_eval.py`. Outputs `outputs/features/seg_swin/`
(label maps per scan, `volumes_{brats21,bsf}.csv`), `outputs/results/analyses/reseg/`. Primary model: MONAI BraTS21
SwinUNETR. Sensitivity: BrainSegFounder BraTS fine-tune (loads strictly as a full SwinUNETR). Input order FLAIR/T1c/T1/T2,
`NormalizeIntensity(nonzero, channel_wise)`, sliding window 128^3, overlap 0.5, sigmoid > 0.5 on (TC, WT, ET). Mapped to
MU labels 3 ET, 1 NETC = TC - ET, 2 SNFH = WT - TC. No cavity class, so RC is taken from the MU mask. 447 s on 2 H100s.
- Rule (written before results): helps if primary detection AUC (progression scan vs verified negatives, all gliomas,
  ridge, imaging only) rises >= 0.05 with CI excluding 0, **or** ET is larger at progression in > 65% of pairs.
- Agreement with MU: Dice ET 0.80, TC 0.62, WT 0.85. TC is **not comparable**, because BraTS models label most of the
  cavity as NETC (TC 1.35x MU's). ET and WT are the comparable compartments.
- Short-gap noise falls somewhat (ET |log ratio| -18% at <= 30 d), but a 2.4x ET change within 14 d remains.
- Result: detection 0.681 -> 0.665 (delta -0.016 [-0.057, +0.025]); ET larger at progression 49% -> 45%; bsf 0.677 /
  41%. **Rule not met.** Conclusion: the limit lies in the labels and data, not the segmenter. Downstream analyses were
  not rebuilt. An exploratory forward plain-AUC GBM gain of +0.059 was one of more than 20 comparisons and is not
  confirmed by IPCW ridge.

### LUMIERE masks: DeepBraTumIA three-compartment (kept, with harmonisation)

DeepBraTumIA atlas `seg_mask.nii.gz` labels: 1 ET (enhancing core), 2 necrotic / non-enhancing **including the resection
cavity**, 3 oedema (SNFH). Read directly from `Imaging-v202211.zip` (`Imaging/<patient>/<week>/DeepBraTumIA-segmentation/
atlas/...`). Atlas 182x218x182 at 1 mm, stored LAS. The mapping was verified by voxel counts against
`measured_volumes_in_mm3.json` (8 studies) and by intensity ratios (6 studies). HD-GLIO masks exist in LUMIERE but were not used.
- **Bug (FIX_FEATURES.md section 1, major, 19747c7):** LUMIERE "necrotic" (with cavity) had been mapped to MU NETC (no
  cavity). Grade-4 medians: MU NETC 0.00 cc (49% zero) vs LUMIERE necrotic 7.40 cc. Fix: shared column
  `log_necrosis_cavity_cc` = MU NETC+RC / LUMIERE necrotic. `SHARED["volumes"] = [log_et_cc, log_necrosis_cavity_cc,
  log_snfh_cc]`. The pre-fix list is kept as `SHARED_VOLUMES_UNHARMONISED`. Honest result: the correct definition does
  **not** improve transfer (locked AUC fell in 6/8 cells). The earlier, better all-glioma number came from the
  mismatched feature.
- **Scale shift (section 2):** ET medians 5.45 vs 0.61 cc and SNFH 42.9 vs 19.1 cc (MU vs LUMIERE). Added
  `prism.features.tabular.within_cohort_normalise` (rank / z-score) as a transductive sensitivity analysis, not the primary.
  Rank normalisation raised locked AUC in 8/8 cells (+0.007 to +0.069), but volume-only models stay <= 0.60.
- **Empty segmentations (section 5, 2dd60c8):** 11 studies have an all-empty DeepBraTumIA mask (7 of them index scans).
  These were 0 cc before and are now NaN (segmentation failure). With the 7 index scans that have no segmentation at
  all, 14/132 index scans have no volumes. Locked imputation uses MU training medians, which is correct for a locked
  model but on the MU scale.
- No re-segmentation of LUMIERE with the MU pipeline was attempted (limitation).

### UCSF masks (kept)

Same BraTS post-treatment convention as MU (1 NCR, 2 SNFH, 3 ET, 4 RC); no remapping. Volumes match the xlsx exactly in
596/596 scans for every label. **xlsx header bugs:** "WT_Volume_Label1+2+3" is really 1+2+3+4, "TC_Volume_Label_1+2" is
really 1+3, and the duplicated "SNFH_OverallChange_Volume" header is the ET change (read by position). Subtraction segs
equal the xlsx Inc/Dec columns in 298/298 pairs. The provenance of the UCSF segmentations is undocumented, as are bias
correction and skull-stripping; only ratio intensities are used. Distribution shift vs MU: less enhancement (ET 0 in 37%
of UCSF scans vs 8% MU), larger cavities, change features 3.5-6x narrower (UCSF_IMAGING.md).

### Segmentation figure for report v3 (2026-10-25, b8aa565; SEG_FIGURE.md) - kept

`prism/report/seg_figure.py`, `tests/test_seg_figure.py`. Deterministic: the LLM never sees images. RAS reorientation and
radiological display (unit-tested). Slice rule: largest ET -> largest lesion -> largest cavity -> largest brain. The
previous scan is shown at the same slice if the brain-mask Dice is >= 0.80; the lowest Dice was 0.85, so the fallback
never fired. `past_only()` asserts that there are no later scans and no duplicates. 631 scans rendered (MU 313, LUMIERE
178, UCSF 140), 0 errors. Panel volumes equal mask voxel counts (max diff 0.0 cc). Outputs are git-ignored under `outputs/`.

### Measurement table (compartment concepts + change) - kept

Code `prism/features/measurements.py` (`python -m prism measurements` -> `outputs/features/measurements.csv`; first
version 701a46e, 2026-10-06). Per timepoint: volumes (ET, NETC, SNFH, RC, tumour = ET+NETC, lesion = all non-cavity);
morphology (ET fraction, multifocality / `et_n_components`, max axial ET area, ET-to-cavity proximity); relative
intensities (median T1c / FLAIR in compartment / normal-appearing brain); past-only deltas vs the prior scan and the nadir,
growth rate, >= 40% ET flag, new component. The UCSF adapter `prism/features/ucsf_imaging.py` reuses
`concepts_from_paths` unchanged (3 MU scans match to 2e-16; `change_features` matches `detection.change_nadir` exactly).

Fixes (FIX_FEATURES.md, 19747c7 / 2dd60c8):
| Fix | Before | After |
|---|---|---|
| `vol_pd_flag` fired from a ~0 cc ET nadir (any >= 1 cc is ">= 40%" of 0) | 72 cohort scans flagged | requires nadir >= `PD_MIN_NADIR_CC` = 0.1 cc -> 57; growth from smaller nadir = new column `et_new_from_zero_nadir` (15) |
| `d_t1c_et_rel` undefined (< 10 ET voxels) for 31/153 scans with a prior was zero-filled like "no change" | silent 0 | `d_t1c_et_rel_missing`, `d_flair_snfh_rel_missing` flags; delta group 22 -> 25 columns; `load_measurements` raises on a stale table |
| Normal-brain reference used `binary_dilation(iterations=10)` = city-block distance (~5.8 mm on diagonals) | L1 margin | `reference_mask()`: Euclidean > 10 mm (`NAWM_MARGIN_MM`); negligible effect (median rel. change 0.1%) |
| 5 mm peri-cavity rim in radiomics uses 5-iteration city-block dilation | — | documented, not changed (would need re-extraction) |

**Change from the previous scan / nadir as timing proxies (DETECTION_TASK.md, exploratory 2026-10-22, 70c3270).** The
"imaging-only" detection arm I contained days since the previous scan, a has-previous flag and an RT-anchored nadir
window. These encode the schedule and treatment phase, not the image: on their own, days-since-previous gives 0.740 and
has-previous 0.726. With pure image inputs (I_pure: volumes, morphology, log ratios to the previous scan,
whole-history nadir), the AUC is 0.709 vs 0.806, and I_scan (scan only) is 0.659. I_pure / I_scan became the image
arms used on LUMIERE and UCSF (on UCSF scan 2, I_pure's history is truncated to scan 1). Leak check: every
previous-scan and nadir feature was recomputed with all later scans of the patient deleted (max deviation 0, asserted).

### Radiomics (corrected v2 kept as comparator; no added value)

- **Legacy** (`legacy_features()`, from `data/mu-reference-processed`): within-lesion z-score + binWidth 25 -> about 2
  grey levels (GLCM joint entropy <= 2 bits), T1c + FLAIR, 2,446 columns incl. LoG/wavelet. Found 2026-10-06.
- **v2** (`prism/features/radiomics.py`, aa4b34d; -> `outputs/features/{radiomics,radiomics_eroded}.csv`): whole-brain
  z-score, fixed 32-bin count (joint entropy 4.7-6.3 bits), no second N4 (FeTS inputs are already bias-corrected). Six
  ROIs: ET, NETC, SNFH, core, lesion, 5 mm peri-cavity rim. All 4 sequences, 2,316 columns, original image only. A
  1-voxel-eroded pass supports an in-fold ICC >= 0.75 filter. Limitations: bin count rather than IBSI fixed width; the
  ICC pass covers only T1c/FLAIR texture + first-order (1,116 of 2,316 columns); T1/T2 texture and shape pass unfiltered.
- **Clipping fix (FIX_RADIOMICS_CLIP.md, bc4bc0c, 2026-10-11).** Legacy columns held **1e6**, apparently the PyRadiomics
  sentinel for NGTDM Coarseness on a flat ROI. It appears in 3 FLAIR LoG sigma 1/2/3 mm `ngtdm_Coarseness` columns, in 4
  scans (2 grade 4); v2 never has it. One 1e6 inflated the training SD, so PCA and the stacked radiomics score depended on
  those scans: inner-OOF stacked scores of -1e4 to -4.6e6 in 20/25 grade-4 fits, and saturated predictions
  (|phi| ~1e5) in SHAP. Fix: `QuantileClip(q=0.01)` in `prism/experiments/c3_radiomics.py`, the first step of
  `selector()`. It is fitted per training (and inner) fold to the 1st/99th order statistics; test scans are clipped with
  training bounds; NaNs pass through. Effect: grade-4 nested delta -0.026 -> -0.032 [-0.084, +0.017]; slope 0.50 -> 0.60;
  max change in any configuration 0.020; no conclusion changed. **Not covered** (still exposed to the 1e6): C2's
  radiomics group, C1's `radiomics_clinical`, `feature_conflicts.py` radiomics rows. Two runs predate the fix: the
  head-to-head on the PRISM report split (radiomics rows) and the split-variance per-split table. Later uses
  (CFB_ADC, Christodoulou re-implementation) apply QuantileClip.
- **CFB-GBM ADC test (2026-10-15, c0bc537; CFB_ADC.md; `prism/analyses/cfb_adc.py`) - rule not met.** Shipped GTV
  PyRadiomics tables, no images. Task: t1 -> t2 volumetric RANO 2.0 PD, one row per patient. Pre-specified rule: ADC adds
  >= 0.03 with CI excluding 0. Result: +0.007 (-0.019, +0.035), perm p 0.151, on 77 patients / 19 events (MDE 0.038).
  Clinical alone 0.50-0.57 (no IDH/MGMT in CFB-GBM). GTV volume + change +0.15 to +0.19, but this is partly circular with
  a GTV-volume label. Conventional texture adds nothing beyond volume. Data facts: t1 falls ~6-8 weeks after RT, inside
  the pseudoprogression window. RANO v04 sizes equal GTV `MeshVolume` (Spearman 1.00), confirming that the label is GTV
  volume and that v03 radiomics IDs line up with v04 RANO.

---

## A.6 Labels and endpoints

### Primary forward label (C1, 2026-10-06, bb479a2; C1_endpoint.md) - kept, with fixes

- Event: documented first progression within H = 120 d of the index scan (90/180 as sensitivities).
  `prism/models/formulations.py`: naive / verified / IPCW / discrete-time hazard.
- Follow-up (D2): last known day = latest dated MRI or clinical event (therapy, progression, death). Censored at 120 d
  dropped from 59 (MRI dates only) to 37 at the time.
- Codebook (D3): IDH/MGMT/ATRX/1p19q mapped to documented levels; undocumented codes -> `unknown` (fixes AUDIT #8).
- Timing (D4): days since RT end, <= 84-d post-RT flag (`EARLY_POST_RT_DAYS = 84`, RANO 2.0 12 weeks), visit index.
- Result (final run): discrimination does not depend on the formulation (36/36 delta CIs include 0). The naive label
  under-predicts (O/E 1.12-1.19 vs 0.95-0.99 for verified/IPCW). Grade-4 AUC 0.65-0.67, far below the report's 0.80.
  Hazard is over-confident (slope 0.30-0.71). Verdict: a calibration/methods result, not a discrimination gain.

### Label fixes (FIX_LABELS.md, 2026-10-11, 19747c7 + 2dd60c8) - kept

| # | Problem | Rule now |
|---|---|---|
| 1 | Death without progression was a verified negative at every horizon (`status_known_indefinitely`) | **Death censors** at the death day (primary). Composite progression-or-death is a sensitivity (`label_{H}_composite`). Label 0 needs progression-free follow-up >= H |
| 1b | 15/96 MU deaths have an MRI after the death day | > 1 record after death -> the death date is treated as the error (`death_date_conflict`, 7 patients, censored at the last record); exactly 1 record after death -> that scan is excluded (flow step). The same rule applies in LUMIERE |
| 2 | `clinical_progression = 0` with a progression date (3 patients); the two date fields disagree in 29 | any progression date = progressor; primary date `date_of_first_progression`, fallback `time_to_first_progression_days`; reverse order = sensitivity `label_{H}_altdate` |
| 3 | One MRI day at -965 d was in the cohort as a positive with t = 989 d | new flow step: MRI day >= -365 and in timepoint order; `prism mu` asserts that no cohort scan postdates a used death date and that all times are > 0 |
| 4 | Hazard person-period counted a mid-interval censored scan as surviving the whole interval | censored scans contribute only fully observed intervals |
| 5 | Follow-up extended by non-imaging dates | kept as primary; imaging-only follow-up is a sensitivity (`label_{H}_imgfu`; 23 scans, median 81 extra days) |
| 6 | Unknown RT end coded `early_post_rt = 0` | 1/0/NaN (94 scans NaN; 65 grade 4) - later replaced, see "look-aheads" below |

Effect at 120 d on the 308 common scans: 17 negatives -> censored (16 deaths within 120 d), 1 negative -> positive, no
positive changed. Final counts: all gliomas 100 / 156 / 52 (pos / neg / censored); grade 4 93 / 117 / 39; LUMIERE
47 / 76 / 9 (one scan 0 -> censored). Logged, not changed: one patient recorded dead without a death day (censored at
the last record); MU death dates are unreliable overall, which is a further reason for death-as-censoring.

### As-of-scan treatment features (FIX_TREATMENT_ASOF.md, 2026-10-11, e037007) - kept

**Leak:** `treatment()` and `timing()` in `prism/features/tabular.py` read the clinical workbook as of the end of
follow-up. `rt_given`/`chemo_given` meant "will receive". The prescription, start day and duration of a course not yet
started or finished were visible. `days_since_rt_end` used a future RT end date. Surgery day was visible for a scan before
surgery. Affected grade-4 / all scans: 13/23 (RT), 13/21 (chemo), 17/29 (duration, days since RT end), 1/1 (surgery).
**Rule:** a treatment fact enters only once its documented start day <= scan day. New `rt_started`, `rt_completed`,
`chemo_started`; not-yet-known values are NaN + in-fold imputation. Assumption: therapy marked given with no start date is
taken as started before the scan (2 RT, 2 chemo patients). Added `early_post_rt_x_mgmt_methylated` (adds nothing, kept
for interpretability). Tests `tests/test_treatment_asof.py`. **Effect:** removing the leak *raised* the treatment-aware
ridge baseline (grade 4 0.694 -> 0.729 on intermediate inputs; final 0.698 [0.615, 0.774] after all fixes). Timing alone
fell (boosting 0.718 -> 0.696), because part of its signal was the future RT end date. The earlier one-off "0.694 -> 0.732"
in PIPELINE_REVIEW.md T1 has no script or output and cannot be reproduced. Other future dates (progression, death, last
follow-up, late treatment) are used only for labels/censoring/eligibility; `visit_index` and deltas use earlier scans only.

### Three further look-aheads found later (AUDIT_SYSTEM.md 2026-10-15; PHASE_CENSORING.md 2026-10-15, plan c98febe) - fixed in C2

1. **Unknown-marker shortcut.** IDH unknown occurs in 0/93 grade-4 events vs 6/117 non-events and 5/39 censored: "test
   not recorded -> no progression" is data recording, not biology. Dropping `idh_unknown`/`mgmt_unknown` costs -0.023
   [-0.047, -0.001]. It is also the main cause of LUMIERE under-prediction (`idh_unknown` -0.68 logits; refit without it:
   LUMIERE O/E 1.33 -> 0.89).
2. **Molecular look-ahead.** IDH/MGMT used at 8 grade-4 / 11 all-glioma scans taken 1-58 d before the diagnosis date.
   Found by the audit layer's per-input as-of check (`checks.csv: inputs_not_known_by_scan`).
3. **RT-documentation look-ahead.** The imputer's missingness indicator for `early_post_rt` (NaN under label rule 6)
   separates "RT pending" from "RT never documented" at a pre-RT scan, which uses information from after the scan. The
   as-of check missed it, because it checks raw values, not imputer-added indicators.

**C2 = corrected core model** (`prism/analyses/phase_censoring.py` arm `C2`): no unknown indicators; IDH/MGMT masked
before diagnosis; `early_post_rt` = 1 only if RT completed by the scan and <= 84 d since its end, else 0 (never NaN).
Grade 4 0.678 (0.596-0.755) vs core 0.698 (delta -0.020); almost all of the cost is from dropping the unknown indicators.
On LUMIERE the shared-feature version moves O/E 1.33 -> 0.99 and slope 0.38 -> 0.97. C2 is the deployed model in the
paper; in the scan-day intended use it gives 0.601 (0.515-0.686) (INTENDED_USE.md, c080794).

### Phase-of-care vs censoring (PHASE_CENSORING.md, plan c98febe, results f75ce82) - claim robust by pre-specified rule

Descriptives: 38 of 39 censored grade-4 scans are pre-RT. All come from 37 patients whose RT *and* chemo fields are
blank (not "No"): median follow-up 0 d, 14 died without progression. This looks like a group treated elsewhere or not
treated. Pre-specified rule on the phase gain R2 - R0 (+0.080 marginal KM): robust if both phase-stratified KM and the
`rt_pathway` refit are >= +0.040. Result: +0.124 and +0.057, so **robust**. About 30% of the gain comes from the
never-documented group. The worst-case bound (all censored = events) gives -0.044. Within phases, R2 is no better than R0.
Consequence: the intended use was restricted to scans with RT started by the scan day (INTENDED_USE.md), because
`rt_pathway` uses future information.

### Clean (imaging-defined) label (CLEAN_LABEL.md, 2026-10-15, 77c694f) - rule not met

MU codes the type of first progression (1 imaging, 2 clinical only, 3 both). The existing label ignored it. Pre-specified
test: type 2 -> censored at the progression date; supported if imaging or baseline+imaging beats the baseline by
>= 0.03 with CI excluding 0 (grade 4, full, ridge). Only 12/93 grade-4 events are clinical-only. Result: baseline +
imaging +0.027 (-0.033, +0.082); imaging alone 0.628 vs baseline 0.696. **Not met**, so the documented-progression label
is not shown to be the bottleneck. Within-LUMIERE CV is at or below chance (61 patients too few), so it cannot answer.
`prism/analyses/clean_label.py`.

### Label-schedule coupling and detection vs forward horizon

- PIPELINE_REVIEW.md L1/L2 (2026-10-09): 59/99 positive progression dates fall within 3 d of a later MRI. 15% of positives
  progress <= 14 d after the index scan. "Progression within 120 d" largely equals "the next scan is the progression
  scan" (79% agreement, kappa 0.53; DIAGNOSTICS_IMAGING section 3). In MU, 75% of detection positives are scanned on the
  progression day itself (48/64). The dataset timepoints are a curated sample (<= 6 per patient), so visit index and
  deltas are relative to included scans (L3).
- SCHEDULE_COUPLING.md: the gap to the next MRI alone gives 0.639 (MU) / 0.788 (LUMIERE). It is partly caused by the
  outcome, so conditioning on it over-adjusts.
- Horizon curve (DIAGNOSTICS_IMAGING section 4): imaging ~0.6 at every H from 60 to 270 d; it does not gain at short horizons.
- **Detection at the scan** (DETECTION_TASK.md, plan 2b4c927, results f13942b): a different estimand, chosen because the
  published 0.80 (MU) and 0.81 (LUMIERE) address detection, not forecasting. Timing alone almost solves it on MU (B1
  0.822): positives are 56/62 later post-RT and negatives 51/84 early post-RT, and a verified 120-d non-event is never a
  patient's last scan. Within later post-RT every arm is ~0.62-0.64.
- **UCSF label = enhancement call at the same scan** (UCSF_AUDIT.md, exploratory, 0b5fa74): 27/29 positives are ET
  "Increased"; progression is dated a median of +7 d after scan 2; log ET volume alone gives AUC 0.88. Within ET-increased
  scans, A-Ipure falls to 0.53. No code leakage: ET was recomputed from NIfTI for 6 random patients with 0 mismatches,
  and the analysed row is scan 2 in 69/69. Easy negatives: 10/40 have no ET. Reading: labels decide what a model learns.

### Christodoulou 2026: their patient-level label (CHRISTODOULOU_REPLICATION.md, 0c62665 then 9810dc4, 2026-10-25/26)

- First plan (pre-specified) assumed a per-scan progression-status label and evaluated our scan-level detection variant:
  0.565 (0.490-0.641) under 5x5 CV on grade-4 all scans; only 1/100 single 20% splits reach 0.80; locked on UCSF 0.80
  (tracks ET volume). This corrected an earlier docs claim (`docs/literature/comparison.md`) that C1's 0.64-0.70 was a
  replication of their setting; it was not.
- **Source check of their public code (repo cloned at commit 643c888).** The label is **patient-level**: `y =
  df["Time to First Progression (Days)"].notna()` (`bin_class/lightGBM__5b.py` lines 105, 217), carried to every
  timepoint. So scans long before progression (41 > 180 d) are positive, and so are scans at or after progression (213 of
  593). **Population leak:** the GBM filter is applied to the clinical table, but a left join on the radiomics table
  keeps non-GBM patients with a missing progression time, so they are labelled 0 (146 scans of 46 non-GBM patients). The
  effective label is "GBM and ever progresses". Test split: 30 patients, seed 42. Feature ranking used a non-grouped
  `StratifiedKFold`. Their committed log gives test AUC 0.7995. The abstract's Brier 0.093 -> 0.088 is not in the logs
  (0.17-0.20). The two repository names/READMEs are swapped with the authors' MGMT paper.
- Exploratory re-run with their label (`prism/analyses/christodoulou_patient_label.py`): GBM only 0.439 (0.376-0.502)
  under 5x5 CV (clinical 0.567; clinical + follow-up length 0.754, a patient-future leak check); as coded 0.727 (clinical
  alone 0.811); 23% of 30-patient splits reach >= 0.80 as coded. Scan-level results and UCSF are unchanged.

---

## A.7 Leaks and bugs in data handling: consolidated list

| # | Date | Bug / leak | Where | Fix | Commit | Effect |
|---|---|---|---|---|---|---|
| 1 | 10-04 | SWIN embeddings need the 3rd model build | legacy notebook | `MODEL_BUILD_INDEX = 2` | 5a2c234 | reproduction only |
| 2 | 10-04 | Shipped radiomics config from an unrecorded seed-62 run that also picks the test split | legacy `train.py` | documented; replaced by repeated grouped CV | — | 0.80 judged split luck (100-split and 5x5 analyses) |
| 3 | 10-04 | Wrong `LABEL_MAP` (1=ET, 3=SNFH) | legacy constants | PRISM config 1 NETC, 2 SNFH, 3 ET, 4 RC | — | legacy still wrong |
| 4 | 10-04 | Undocumented molecular codes used as predictors | legacy | codebook -> `unknown` | bb479a2 | — |
| 5 | 10-04 | Never-progressors with < 120 d follow-up labelled 0 | legacy `train.py:660` | censoring-aware labels + IPCW | bb479a2 | O/E 1.12-1.19 -> ~0.97 |
| 6 | 10-04 | Scan-level bootstrap; ranking outside CV | legacy | patient-cluster bootstrap; in-fold selection | — | — |
| 7 | 10-06 | Legacy radiomics = ~2 grey levels | legacy extraction | v2 extraction | aa4b34d | v2 adds nothing either |
| 8 | 10-06 | Legacy cohort included a scan with unknown MRI date | `label_for_case` | flow step "MRI day known" | bb479a2 | 1 scan |
| 9 | 10-11 | Treatment/timing read as of end of follow-up | `tabular.py` | as-of-scan rule | e037007 | baseline rose; timing alone fell |
| 10 | 10-11 | Death without progression = verified negative | `mu.py` | death censors | 19747c7 | 17 neg -> censored |
| 11 | 10-11 | MRIs after recorded death; implausible MRI day; flag/date conflicts | `mu.py`, `lumiere.py` | rules 1b-3 | 19747c7 | 6 scans out |
| 12 | 10-11 | Hazard person-period overcounted censored intervals | `formulations.py` | full intervals only | 19747c7 | hazard rows |
| 13 | 10-11 | LUMIERE necrosis includes cavity, mapped to MU NETC | `lumiere.py`, `tabular.py` | `log_necrosis_cavity_cc` | 19747c7 | transfer not better |
| 14 | 10-11 | Empty LUMIERE segmentations counted as 0 cc | `lumiere.py` | NaN | 2dd60c8 | -0.002 to -0.018 |
| 15 | 10-11 | `vol_pd_flag` from ~0 nadir; zero-filled undefined deltas; L1 margin | `measurements.py` | nadir >= 0.1 cc, missing flags, Euclidean | 19747c7 | 72 -> 57 flags |
| 16 | 10-11 | PyRadiomics 1e6 sentinel blew up the stacked score | C3 `selector()` | in-fold `QuantileClip` 1/99% | bc4bc0c | max 0.020; C2/C1/feature-conflict paths not covered |
| 17 | 10-15 | Unknown-marker shortcut | core model | C2 drops indicators | f75ce82 | -0.023 |
| 18 | 10-15 | IDH/MGMT before diagnosis (8 grade-4 scans) | core model | masked in C1/C2 | f75ce82 | ~0 |
| 19 | 10-15 | `early_post_rt` NaN indicator = future RT documentation | `c3.BASE_PRE` imputer | as-of 0/1 coding in C2 | f75ce82 | +0.003, O/E closer to 1 |
| 20 | 10-21 | `rt_pathway` intended use uses the future | PHASE_CENSORING | scan-day `rt_started` | 74eaaf5 / c080794 | headline 0.601 |
| 21 | 10-22 | "Imaging-only" detection arm carried timing proxies | DETECTION_TASK I | I_pure / I_scan | 70c3270 | 0.806 -> 0.709 |
| 22 | 10-25 | UCSF timepoint encodes the label | UCSF design | scan-2-only evaluation | 0e7c9fe | pre-specified |
| 23 | 10-25 | UCSF xlsx header names and sign conventions wrong | UCSF xlsx | positional read, evidence-based signs, date-artefact NaN | f461f11 | — |
| 24 | 10-26 | Christodoulou label is patient-level; non-GBM leak as 0 | their code | exploratory re-run with their label | 9810dc4 | their 0.80 not supported |

Open items for a successor:
- Bug 16 is not fixed in C2's radiomics group, C1 `radiomics_clinical` or `feature_conflicts.py`. The PRISM-report-split
  head-to-head radiomics rows predate the fix.
- The legacy `LABEL_MAP` is still wrong in `legacy/radiomics/radiomics_tools/metrics/constants.py`.
- Possible duplicate MU patients (identical masks across patients) were not reported to the data owners.
- No re-segmentation of LUMIERE with the MU pipeline; no fixed-bin-width radiomics sensitivity analysis.
- UCSF labels were chosen without the author and may be changed. RT end and dose are missing, so the full timeline
  model cannot be built there.
- Pre-fix snapshots: `outputs/results_pre_fix_2026-10-11/`, `/project/community/sbandred/prism-golden-outputs-20261009/`.
  UCSF deep crop cache: `outputs/features/finetune_cache/ucsf/` (7.6 GB).


---

# B. Models and experiments, including every failed one

Scope: every model family and modelling experiment run in this repository, from the 2026-10-04 reproduction of the
legacy PRISM report pipeline to the 2026-10-26 exploratory detection add-ons. All numbers are aggregate and come from the
named doc under `docs/results/` (or `legacy/reproduction/FINDINGS.md`, or user memory). Unless stated otherwise:

- MU-Glioma-Post ("MU") final cohort is 308 index scans / 155 patients. Grade 4 (the primary population) is 249 / 126. At 120 d,
  grade 4 has 93 events, 117 non-events and 39 censored scans.
- The headline estimator (since `c1532dd`, 2026-10-11) is the **mean over 5 repeats of the per-repeat pooled-OOF IPCW
  AUC(120 d)** on the shared 5x5 patient-grouped folds (`outputs/data/folds.csv`). CIs and paired ΔAUC come from a 1000-draw
  patient-cluster bootstrap (`prism/models/metrics.py: evaluate_repeated`). Models are fitted on "verified" labels: scans
  censored before 120 d are dropped from the fit and kept in the IPCW evaluation.
- "Baseline" / "core" / "R3" means the ridge on clinical + timing + as-of-scan treatment
  (`prism/experiments/c3_radiomics.py: fit_predict`, `BASE_PRE`). It scores **0.698 [0.615, 0.774]** in grade 4 and
  **0.720 [0.638, 0.792]** in all gliomas.
- **Naming trap.** "C2" means two different things. (a) `C2_feature_search` is the 2026-10-06 group-search experiment.
  (b) From 2026-10-15, "C2" is the corrected core model (`prism/analyses/phase_censoring.py: arm_design("C2")`, core +
  as-of-scan `early_post_rt`, no look-ahead). Its result is IPCW AUC **0.601 (0.515-0.686)** in the scan-day intended
  use (grade-4 scans with RT started, 173 scans). The triage and detection G5 arms are stacked on meaning (b).
  "C1" has the same problem: it is both the endpoint experiment and a phase_censoring arm.
- "Intended use" (IU) means grade-4 scans on or after the documented RT start, as of the scan day (`INTENDED_USE.md`,
  `c080794`, 2026-10-21).
- The framing rule (memory `prism-unpublished-naming.md`) applies here. The "PRISM report" model is the author's own
  earlier, unpublished system, and this log never calls it published.

---

## B.0 Summary table: everything that did not work

"Rule" names the pre-specified decision rule and the plan doc or commit, where one exists. "Post hoc" means there was
none.

| # | Date | Experiment | What was hoped | Result (key number) | Rule met? | Verdict |
|---|---|---|---|---|---|---|
| 1 | 10-04 | Legacy SWIN embeddings (notebook) | Image signal for fusion | Random untrained encoder; embeddings alone AUC ~0.50, linear probe 0.55 / 0.62 | post hoc | failed, dropped |
| 2 | 10-04 | Legacy MLP fusion (radiomics score + SWIN embeddings) | Beat radiomics alone (0.8043) | Never beats it; score-only fusion = 0.8043; checkpoint chosen on test loss; 0.48 cutoff hand-tuned | post hoc | failed, dropped |
| 3 | 10-04 | Legacy radiomics default search | Reproduce shipped LogReg-48 | Search picks SVM-32 (0.7977); shipped config came from an unrecorded run | n/a | reproduced only with shipped config |
| 4 | 10-04/05 | BraTS21 SwinUNETR seg fine-tune, then progression fine-tune | Image score adds to radiomics | Image-only OOF 0.59-0.60, test 0.64-0.65; late fusion Δ CI spans 0 | post hoc | failed |
| 5 | 10-06/11 | C2 feature-group search (126 candidates, nested) | Find a better feature set | Nested 0.664 vs post-hoc best 0.714; permutation p = 0.050 (grade 4) | n/a | honest estimate < baseline; superseded by C3 baseline |
| 6 | 10-06/11 | C3 radiomics on the baseline (70 configs, nested), **primary** | Radiomics adds to baseline | Grade 4 ΔAUC **−0.032 [−0.084, +0.017]**; 0/70 configs CI > 0 | primary analysis (plan §3.3): no gain | **failed (headline negative result)** |
| 7 | 10-06 | Corrected radiomics (v2: brain z-score, 32 bins, compartments, ICC filter) | Better than legacy texture | Median ΔAUC −0.017 to +0.005; legacy 2-level texture was the only positive variant | n/a | failed |
| 8 | 10-11 | Literature baselines (RANO-style volumetric rule, ET persistence, Hashim Cox) | Competitive comparators | Rule 0.551 (Δ −0.147), ET 0.636, Cox 0.628, all below baseline | n/a | kept as comparators; all weaker |
| 9 | 10-11 | Hyperparameter tuning of the baseline | Higher AUC | Within ±0.025, all CIs span 0; tuned boosting slope 0.59 | n/a | failed; fixed ridge kept |
| 10 | 10-11 | Frozen SwinUNETR deep features (BraTS21, BrainSegFounder; D1 nested over 32) | Deep image features add | Grade 4 ΔAUC −0.004 [−0.069, +0.063]; LUMIERE gain not above random-weight control | `DL_COMPARISON_DESIGN.md` | failed |
| 11 | 10-11 | Imbalance handling (class weight, oversample, SMOTE, XGBoost, LightGBM) | Better discrimination | ΔAUC −0.031 to +0.023; 4/190 CIs > 0 (all-glioma ridge only); O/E worsens | post hoc | failed; unweighted ridge kept |
| 12 | 10-11 | Feature pruning (pre-stated correlation rule, nested) | Remove conflicting features | ΔAUC −0.018 to +0.011, all CIs span 0 | rule stated in module | no gain; redundancy diagnosed instead |
| 13 | 10-11 | Phase ladder primary: imaging on clinical + phase, post-RT | Imaging helps once phase is known | ΔAUC +0.061 (−0.038, +0.156), permutation p = 0.21 | pre-specified in module docstring: **not supported** | failed |
| 14 | 10-11 | Imaging positive control (detect the progression scan from volumes) | AUC ≥ 0.8 | 0.62-0.70 | post hoc | **failed** (data limitation, no bug found) |
| 15 | 10-11 | Re-segmentation (BraTS21 SwinUNETR, BrainSegFounder) | Better masks give better features | Pre-specified rule not met (`RESEGMENTATION.md`, `d82969b`) | not met | failed (section of another log part) |
| 16 | 10-15 | CFB-GBM ADC vs conventional radiomics | Diffusion adds | +0.007 [−0.019, +0.035], perm. p 0.151 (`CFB_ADC.md`, `c0bc537`) | not met | failed (other section) |
| 17 | 10-15/16 | Fine-tuned SwinUNETR on the 120-d label (5 arms, 500 fine-tunes) | Core + score ΔAUC ≥ 0.03, CI > 0 | +0.009 [−0.022, +0.040]; permuted stack +0.005 (validity flag missed) | `FINETUNE_DEEP.md` §G (`9aaa8d3`): **not met** | failed |
| 18 | 10-21 | Triage T1: C2 + longitudinal volume trajectory | ΔAUC ≥ 0.03, CI > 0 in IU | −0.008 (−0.074 to +0.052) | `fc2d247`: **fails** | NO-GO |
| 19 | 10-21 | Triage T2: rule-out operating point | ≥ 20% low risk with NPV lower bound ≥ 0.85 | Best NPV 0.669 (0.515-0.803) | `fc2d247`: **fails** | NO-GO |
| 20 | 10-21 | Detection at the scan, tabular (P vs B1) | P ≥ 0.75 and P − B1 ≥ 0.03, CI > 0 | P 0.837 but P − B1 +0.015 (−0.032 to +0.063) | `2b4c927` rule 1: **fails** | NO-GO |
| 21 | 10-21/22 | Detection deep arms G1-G4 + 4 all-glioma arms (800 fine-tunes) | Stack beats P by ≥ 0.03 | Image-only 0.45-0.57 (= permuted control); stacks = B1 ± 0.004 | rule 2: **fails**; rule 4 met | failed |
| 22 | 10-22 | G5 triage retest (subtraction network, forward label) | C2 + G5 − C2 ≥ 0.03 | +0.006 [−0.021, +0.034] | rule 3: **fails** | failed |
| 23 | 10-22 | Detection "imaging only" arm I (0.806) | Pure image signal | Contained timing proxies; pure images 0.709 | exploratory correction | number corrected |
| 24 | 10-25/26 | Christodoulou-style re-implementation (LightGBM + Optuna + Platt, 256 radiomics) | Reproduce their 0.80 | 0.565 (0.490-0.641) under 5x5 CV; 1% of 100 splits ≥ 0.80 | pre-specified reading: **not reproduced** | failed; their label is patient-level |
| 25 | 10-11 | Recalibration / adaptation on LUMIERE | Better transport | No arm beats locked; the old "recalibration costs AUC" claim was an estimator artefact | n/a | no gain |

Experiments that were **kept** or that changed the story are not failures, but they are listed in the body:
- the C3 ridge baseline / core model (headline comparator);
- the evaluation fixes (estimator, permutations);
- the radiomics clipping fix;
- split variance (the PRISM report's 0.80 is an upper-tail split);
- SHAP and schedule coupling (where the signal comes from);
- the phase ladder's secondary finding (a phase block recovers about 70% of the baseline's gain);
- clinical utility and Riley sample size (underpowered);
- the detection "two pathways" exploratory finding.

---

## B.1 Legacy pipelines (before the `prism/` package; 2026-09-14 to 2026-10-05)

The repo was initialised on 2026-09-14 (`21c1540`) with the original code. That code was moved to `legacy/` on 2026-10-10
(`92e7544`). The reproduction and validation run on 2026-10-04/05 is in `legacy/reproduction/` (FINDINGS.md, AUDIT.md,
PROCEDURES.md, LITERATURE.md; `5a2c234`, `677139d`).

### B.1.1 Legacy radiomics, the "PRISM report" model (`legacy/radiomics/`)
- **Question.** Can radiomics predict progression within 120 d of a post-operative scan?
- **Design.**
  - T1c + FLAIR PyRadiomics features, with lesion masks made from labels 1/2/3, N4 correction and lesion z-score.
  - Molecular and basic clinical codes added ("hybrid_basic").
  - One patient-held-out split of 30 patients / 84 scans (seed 62).
  - Selection by L1 + permutation consensus, then an Optuna search.
- **Shipped model.** Calibrated L2 LogReg-48 (liblinear, C = 0.0087, balanced weights) with Platt scaling on top, test AUC
  **0.8043** (`legacy/radiomics/models/calibrated/`).
- **README history** (`legacy/radiomics/README.md`):

  | Variant | AUC |
  |---|---|
  | LightGBM-64 radiomics only, "paper-style" | 0.599 |
  | Hybrid paper-style | 0.621 |
  | Forward radiomics-only LogReg-32 | 0.674 |
  | Earliest-scan screen | 0.873 |
  | Calibrated forward hybrid | 0.804 |

- **Reproduction (2026-10-04).** Manifests and features match the HF processed set. The shipped bundle reproduces 0.8043
  exactly. The default `main.py train` search, however, selects **SVM-32 (0.7977)**, so the shipped configuration came from
  a run whose search command is not in the repo (`repeated_forward_hybrid_basic_corrected/seed_62`).
- **Gotchas.**
  - `export_calibrated` crashes if the search picks a non-linear model (it calls `shap.LinearExplainer`).
  - Unpickling the bundle needs a module alias (`scripts.run_postoperative_progression_surveillance` must point to
    `radiomics_pipeline.workflows.train`).
  - `radiomics_tools/metrics/constants.py` LABEL_MAP is wrong. The true mapping is 1 = NETC, 2 = SNFH, 3 = ET, 4 = RC.
    It does not affect the shipped model, which uses the union of labels 1-3.
  - 59 of 97 never-progressor negatives have < 120 d follow-up, so their labels are unverified.
- **What it led to.** It became the object of every later "is 0.80 real?" analysis:
  - split variance (B.8);
  - SHAP on the PRISM split (B.9);
  - head-to-head (B.3.3);
  - the shipped model applied to LUMIERE: 0.613 [0.500, 0.729], O/E 1.24 (`FINAL_RESULTS.md`; file dated 2026-10-09, not
    regenerated).

### B.1.2 Legacy SWIN embeddings (`legacy/swin_unetr/`, original notebook `swinunetr-pipeline-kaggle.ipynb`)
- **Design.** A "SwinEncoder3D" gave 594 x 48-d embeddings for fusion.
- **Root cause found.**
  - It is not a SwinUNETR. It is a small transformer with **random, untrained weights**.
  - It reproduces only with the **3rd model built after `seed(42)`** ("build index 2", now encoded in
    `legacy/swin_unetr/extract_embeddings.py`).
  - PC1 (92% of variance) tracks cavity and lesion size.
- **Result.** Embeddings alone gave AUC ~0.50 in the fusion MLP. A linear probe gave 0.55 (train CV) / 0.62 (test).
- **Verdict.** Failed. This is also why the later frozen-feature work kept a random-weight encoder as a mandatory control
  (B.5): the PRISM report's random encoder could not have carried signal.

### B.1.3 Legacy MLP fusion (`legacy/mlp_fusion/fusion_mlp.py`, `unified_fusion_results.csv`, `best_fusion_model.pth`)
- **Design.** An MLP takes the upstream radiomics score plus the SWIN embedding.
- **Reported.** AUC 0.8006, accuracy 0.8095, F1 0.6522. The shipped weights reproduce to 1e-4.
- **Validation** (`legacy/reproduction/validation/fusion_validation.py`: 50 seeds x 6 protocols; `run_fusion_seeds.py`):
  - Retrained AUC is about 0.80. The shipped accuracy sits at about the 95th percentile and the F1 at about the maximum
    (a lucky seed).
  - **The checkpoint was selected on test loss**, a leak worth about +0.01 AUC.
  - The 0.48 cutoff was hand-tuned. The radiomics model was compared at 0.48 instead of its own 0.455, so the reported
    recall/F1 "gain" is an operating-point shift.
  - Score-only fusion = 0.8043, the same as radiomics alone, and adding embeddings lowers it.
  - `LayerNorm(vision_dim)` zeroes a 1-d vision input, so the MLP cannot fuse a single image score.
- **Verdict.** Failed. Fusion never beats radiomics alone. Dropped.
- The downstream LLM agent (`legacy/glioma_agent/`, report for one example patient) reproduced except for the LLM text
  (no API key).

### B.1.4 BraTS21 SwinUNETR fine-tuning, legacy lane (`legacy/swin_unetr/{finetune_seg,finetune_progression,make_crops,zero_shot_check}.py`, `run_stage2_lanes.sh`)
- **Choice and design.** This was the user's chosen direction on 2026-10-04 ("no more radiomics models"). MONAI BraTS21
  fold-1 weights were used, with the BraTS channel order flair, t1ce, t1, t2 = MU t2f, t1c, t1n, t2w. All 30 PRISM test
  patients were excluded from every training and selection step.
- **Zero-shot.** WT Dice 0.85; ET corresponds to label 3 (0.81).
- **Stage 1: segmentation fine-tune** (DDP, new RC head). Validation mean Dice 0.495 → **0.697** (RC 0.01 → 0.53).
- **Bug found.** Global-average-pooled swinViT features are about identical across scans (corr ≈ 1.0). Lesion-masked
  multi-scale pooling + BatchNorm is required. This design choice carried into `prism/features/deep.py`.
- **Stage 2: progression fine-tune.**
  - Image-only OOF 0.59-0.60, test 0.635 (seg init) / 0.652 (pretrained init). Stage 1 did not help.
  - Late fusion [radiomics score, image prob]: test Δ vs 0.8043 = −0.014 / +0.005, with CIs spanning 0.
- **Verdict.** Failed. Re-done properly inside the nested framework as FINETUNE_DEEP (B.6), which failed again.
- **Gotcha.** `/project/community/sbandred` was wiped on 2026-10-05 around 15:04. The code was restored from file history
  and the data re-downloaded (memory `reproduction-status.md`).

---

## B.2 Evaluation fixes that changed numbers (FIX_EVALUATION.md, `c1532dd`, 2026-10-11)

These are not models, but every later number depends on them. A successor must know them.

- **Headline estimator.**
  - The old headline was the AUC of OOF predictions **averaged over 5 repeats**. That is an ensemble of 5 models per
    scan, so it is optimistic, and more so for nested pipelines.
  - The new headline is the mean over repeats of the per-repeat AUC. The old value is kept as `*_averaged`.
  - Effect on the validation inputs: the C3 nested radiomics ΔAUC went from +0.009 [−0.027, +0.040] to −0.002
    [−0.030, +0.024], **changing sign**.
- **C2 permutation control.**
  - The old control was 5 scan-level shuffles: too narrow, and no p-value possible.
  - The new control is 100 **patient-block** permutations among patients with the same scan count
    (`permute_patients`), with the full nested pipeline re-run each time.
  - The validation-run grade-4 p was 0.010. **In the final run it is p = 0.050**, so the earlier "p = 0.010" statement is
    wrong for grade 4. All gliomas: p = 0.0099.
- **C2 nested search now includes boosting** (126 candidates). Boosting is chosen in 15/25 outer folds. Nested
  calibration slope 0.40.
- **External LUMIERE estimator.**
  - Before, "Raw" was pooled while the adapted arms were per-fold means. Pooling OOF predictions recalibrated differently
    in each fold produced recalibrated ridge = 0.414 (slope −0.96), an artefact.
  - Now every arm is scored on the same LUMIERE 5x5 folds (`fold_mean_metrics`).
  - Result: **the old "recalibration costs 0.04-0.12 AUC" was purely an estimator artefact.** No adaptation arm beats
    locked, and LUMIERE-only training is worst.
- **Minor fixes.**
  - The L1 selector padded to 30 features with zero-coefficient columns (`threshold=-inf`); it now keeps 17-22.
  - Missing-ROI patterns get explicit missingness flags.
  - `legacy/shipped_on_lumiere.py adapt()` was defined after the `__main__` block and **never ran**; fixed.
  - Warnings are no longer globally silenced.
- **Validation-run numbers** in sections 1-5 of FIX_EVALUATION.md (253 grade-4 scans, before the label and feature fixes)
  are superseded. The final equivalents are in its header table and in FINAL_RESULTS.md.

---

## B.3 Feature-set experiments on the forward 120-day task

### B.3.1 C2: feature-group search (`prism/experiments/c2_feature_search.py`, `prism/features/measurements.py`; C2_feature_search.md, first `701a46e` 2026-10-06, final numbers 2026-10-11)
- **Question.** Which combination of 6 groups predicts best: clinical, timing, volumes, morphology, delta, radiomics
  (legacy top-20 in-fold)?
- **Design.** 63 combinations x 2 learners (ridge with inner-CV penalty; shallow boosting). Grids are in
  `docs/results/C2_grid_{grade4,all_glioma}.csv` (126 rows each, with train AUC and overfit gap).
- **Results, grade 4.**
  - Post-hoc best: boosting on clinical + timing, **0.714 [0.643, 0.785]** (train 0.961, slope 0.61).
  - **Nested 0.664 [0.601, 0.722]**, slope 0.49.
  - Permutation null mean 0.548, 95th percentile 0.636; **p = 0.050**.
- **Results, all gliomas.** Post-hoc best 0.744 (ridge, with radiomics); nested 0.707 [0.647, 0.766]; p = 0.010.
- **Single groups, grade 4, ridge.** Radiomics 0.675, morphology 0.650, volumes 0.611, clinical 0.585, timing 0.559,
  delta 0.537.
- **Findings.**
  - The best grade-4 model uses no imaging.
  - Boosting overfits: train AUC ≥ 0.95, median gap 0.36.
  - The nested null is centred at about 0.55, not 0.5, because choosing among 126 candidates is optimistic even with no
    signal.
  - Nested choices add a **different** imaging group from fold to fold (23/25 folds add one), which is consistent with
    noise.
- **Gotchas.**
  - C2's radiomics group is **not clipped** (no `c3.selector`), so its radiomics rows still carry the 1e6 sentinel (B.4.2).
  - The 2026-10-06 numbers (253 scans, old estimator, ridge-only nested search, 5 shuffles) are superseded.
- **Verdict.** Superseded as the comparator. C2 had no treatment block. It led to C3's treatment-aware baseline.

### B.3.2 Literature baselines and the tuning grid (`prism/analyses/baselines.py`; BASELINES.md, `766c511` 2026-10-11)
- **Question.** How do published-style comparators do against the C3 ridge?
- **Grade-4 results** (Δ vs 0.698):

  | Model | AUC | Δ [95% CI] |
  |---|---|---|
  | Clinical only | 0.585 | −0.113 [−0.208, −0.026] |
  | Timing only | 0.559 | |
  | Clinical + timing | 0.644 | −0.054 [−0.103, −0.012] |
  | B0 log ET volume (persistence) | 0.636 | |
  | B0 ΔET | 0.546 | |
  | **B1 volumetric RANO-style rule** (ET ≥ 40% and ≥ 1 cc over past-only nadir) | **0.551** | **−0.147 [−0.239, −0.062]** |
  | B1 + new ET component | 0.513 | |
  | B1, RANO 2.0 12-week window | 0.508 | |
  | B1 continuous | 0.562 | |
  | B4 Hashim-style Cox (log ET + age + IDH + MGMT) | 0.628 | −0.070 [−0.179, +0.031] |

- **Gotcha.** The in-fold 1-D logistic map costs 0.02-0.06 AUC for score baselines: pooling OOF scores from 5 fold maps
  breaks ties and order. The unfitted `auc_raw` values (B1 rule 0.611, ET 0.659) are still below the baseline.
- **Nested hyperparameter grid.** Every tuned arm is within ±0.025 and all CIs span 0. Nested ridge + boosting gives
  0.674 (Δ −0.024). Choices are unstable, and tuned boosting's slope drops 0.82 → 0.59.
- **LUMIERE (locked).** Everything is 0.51-0.64. Hashim Cox is nominally best (0.640, slope 0.94) with no significant Δ.
  The segmenter differs: median grade-4 ET is 0.61 cc on LUMIERE vs 5.45 cc on MU, so the 1 cc / 40% thresholds
  transfer poorly.
- **Verdict.** Kept as comparators. They showed that imaging-only rules are weaker than the timeline, and that tuning
  does not matter.

### B.3.3 C3: radiomics on the treatment-aware baseline, the PRIMARY analysis (`prism/experiments/c3_radiomics.py`, `prism/features/radiomics.py`; C3_radiomics.md, `aa4b34d` 2026-10-06, final 2026-10-11 after the clipping fix)
- **Question (pre-specified primary, plan §3.3).** Does radiomics, chosen by nested selection over 70 configurations,
  improve grade-4 ridge on clinical + timing + treatment?
- **70 configurations.**
  - Variants: legacy; corrected v2 whole lesion; v2 per compartment (ET, NETC, SNFH, core, lesion, 5 mm cavity rim +
    shape); v2 all 4 sequences.
  - Each crossed with: ICC ≥ 0.75 stability filter (vs 1-voxel erosion, in-fold); top-10 / top-30 / L1 / PCA-10 /
    decorrelate + top-20 selection; concatenation vs stacked score.
- **Results.**

  | | Grade 4 | All gliomas |
  |---|---|---|
  | Baseline ridge | 0.698 | 0.720 |
  | Baseline boosting | 0.687 | 0.718 |
  | **Nested radiomics** | **0.666 [0.586, 0.739], ΔAUC −0.032 [−0.084, +0.017]**, slope 0.60 | 0.747, ΔAUC +0.028 [−0.017, +0.071] |
  | Configs with CI > 0 | 0/70 (8/70 below 0) | 1/70 (`legacy|none|pca10|stack`, +0.035 [+0.002, +0.068]; about 1.75 expected by chance) |
  | Best post-hoc config | +0.023 | +0.035 |

- **Sub-findings.**
  - Correcting the discretisation did not help (v2 median Δ −0.017 to +0.005).
  - The only positive variant is legacy 2-level texture, which acts as a binary habitat descriptor.
  - Stacking beats concatenation in grade 4 (median −0.003 vs −0.027).
  - Treatment features lift the ridge from 0.644 to 0.698.
- **Legacy ablation table** (2026-10-06): not re-run, superseded inputs, record only.
- **Head-to-head on the PRISM report split** (29 test patients / 82 scans, `prism/analyses/head_to_head.py`):
  - PRISM report model 0.802 naive / 0.817 IPCW.
  - Baseline ridge **0.871 / 0.851**; PRISM model vs baseline Δ −0.034 [−0.186, +0.109].
  - Radiomics on the baseline −0.010 to +0.007. These radiomics rows were **not re-run after the clipping fix**.
- **Verdict.** **Failed. This is the headline negative result:** radiomics adds nothing measurable over clinical +
  treatment. It is robust in sensitivity analyses (B.7.2).

### B.3.4 Imaging vs non-imaging synthesis (IMAGING_VS_NONIMAGING.md, `6f43236` 2026-10-10)
- **Question.** Is imaging worth more than non-imaging information? This doc compiles C2, C3, deep and LUMIERE.
- **Grade 4.**
  - Imaging only (volumes + morphology + delta): 0.635 ridge.
  - With legacy radiomics: 0.678.
  - Clinical + timing boosting: 0.714.
  - With boosting, every imaging addition lowers grade-4 AUC (to 0.632-0.705).
- **All gliomas.** The gap closes (imaging only 0.725 vs 0.739), because imaging partly separates tumour grades.
- **Verdict.** It fixed the claim to be made: "imaging does not add measurable value over clinical + treatment
  information", not "clinical beats imaging". It also fixed the caveat that the setting is conventional MRI, one centre,
  120 d.

### B.3.5 Class imbalance (`prism/analyses/imbalance.py`; IMBALANCE.md, `3364bb8` 2026-10-11)
- **Question (user).** "Does XGBoost help with the imbalance, or should we be upsampling?"
- **Premise.** The imbalance is mild: 44% / 39% minority. The models never used IPCW training weights; ipcw vs unit
  weights gives Δ ≤ 0.001.
- **Design.**
  - Learners: ridge, HistGB, XGBoost and LightGBM (fixed small-data settings), plus 16-point nested grids.
  - Re-balancing: none, balanced weights, patient-aware oversampling, SMOTE using neighbours from other patients only.
  - 192 MU configurations, and LUMIERE locked.
  - XGBoost 3.2.0 came from an ephemeral `uv --with` overlay; the shared `.venv` was not changed.
- **Results.**
  - ΔAUC vs ridge ranges −0.031 to +0.023. 4/190 CIs are above 0, all all-glioma ridge with re-balancing (+0.009 to
    +0.014).
  - Grade-4 ridge balanced: +0.008 [−0.001, +0.019], O/E 1.04 → 0.94.
  - Median O/E falls 1.01 → 0.88.
  - Nested boosting slope 0.52-0.73.
  - On LUMIERE, XGBoost transports worse (0.56 vs 0.61).
- **Theory confirmed.** The prior shift logit + log k predicts the observed mean-risk shift (0.463 predicted vs 0.459
  observed).
- **Verdict.** Failed. Do not re-balance. Keep the unweighted ridge. Choose thresholds on calibrated risk instead.

### B.3.6 Feature conflicts (`prism/analyses/feature_conflicts.py`; FEATURE_CONFLICTS.md, `3364bb8` 2026-10-11)
- **Question.** Do features hurt one another (collinearity, sign flips, colliding encodings)?
- **Results.**
  - Leave-one-group-out: no group measurably hurts.
  - The real issue is redundancy. The timing x treatment interaction is −0.066 to −0.073, with the CI excluding 0 in
    3 of 4 cells.
  - The baseline has 9 columns with VIF = ∞. The bit "RT completed by the scan" appears in ≥ 5 columns
    (rt_date_unknown = 1 − rt_completed, missingness indicators, ...).
  - `rt_completed` univariate +0.43 collapses to −0.002 in the multivariable model.
  - Imaging sign flips are small suppression effects.
- **Pruning** (rule stated in the module as `PRUNE_RULE`).
  - Nested: ΔAUC −0.018 to +0.011, all CIs span 0.
  - Global (leaky): +0.009 to +0.018, which is selection optimism.
  - P_base cuts the baseline from 31 to about 21 columns with no loss.
- **Gotcha.** The "B+radiomics (legacy)" row is unclipped (calibration slope 0.34); treat it as reference only.
- **Verdict.** No gain from pruning. The redundancy finding motivated the compact phase block of the phase ladder (B.7.3).

### B.3.7 Fix: radiomics outlier clipping (FIX_RADIOMICS_CLIP.md; code `bc4bc0c`, doc `3364bb8`, 2026-10-11)
- **Bug, found by SHAP.**
  - The PyRadiomics **1e6 sentinel** (NGTDM Coarseness on a flat ROI) sits in 3 legacy FLAIR LoG σ = 1/2/3 mm columns
    of 4 scans (2 grade 4).
  - After `StandardScaler`/PCA, the stacked radiomics score had inner-OOF training values of −1e4 to −4.6e6 in 20/25
    grade-4 fits. A held-out affected scan got |φ| ≈ 1e5 and saturated.
  - The v2 radiomics never contain the value.
- **Fix.** `QuantileClip(q=0.01)` as the first step of `c3.selector`, fitted in-fold, with no labels involved. It applies
  to all 70 radiomics configurations and to the deep arms.
- **Effect.**
  - Grade-4 nested ΔAUC −0.026 → −0.032 (slope 0.50 → 0.60).
  - All gliomas +0.012 → +0.028; 0/70 → 1/70 configs with CI > 0.
  - Largest single-config change 0.020.
  - The baseline is unchanged.
- **Not covered.** C2's radiomics group, C1 `radiomics_clinical`, feature_conflicts B+radiomics, and the head-to-head and
  split-variance `baseline_rad` rows are still unclipped.
- **Re-run downstream.** C3, deep, baselines, schedule, sensitivity, utility, SHAP and feature conflicts were re-run after
  the fix (18:20-18:52 on 2026-10-11).

---

## B.4 Diagnostics: is the imaging pipeline broken? (DIAGNOSTICS_IMAGING.md, `prism/analyses/diagnostics_imaging.py`, `fc09ac4` 2026-10-11)
- **Question.** Imaging-only and clinical-only both reach about 0.60, and only timing lifts that to about 0.70. Is there a
  bug?
- **PASS: volumes.** Volumes match MU's own xlsx at r ≥ 0.996 (ET 98% exact voxel match). The label mapping is verified,
  intensities agree with the labels, and visual QA of 12 scans found no wrong masks.
- **FAIL: positive control.** Imaging separates the progression scan from other scans at only **0.62-0.70**; the target was
  ≥ 0.8.
  - ET volume is larger at the progression scan than at the previous scan in only 49% of pairs (p = 0.54). Lesion growth
    from nadir: 79%.
  - **Volume series are very noisy.** Pairs ≤ 14 days apart change by a median 3.2x in ET, which is more than over 45-90
    day gaps. The size of the change is unrelated to the gap (ρ −0.01).
  - Some of the noise is re-resection. Some is implausible: 3-20x ET jumps within days in a few patients.
- **PASS: label alignment.**
  - The progression date equals an MRI date for 62% of progressors.
  - label_120 is largely "the next scan is the progression scan" (79% agreement, κ 0.53).
  - 22% of progressors have no MRI on or after the progression date.
- **Horizon curve.** Imaging stays at about 0.6 at every horizon from 60 to 270 d.
- **Addendum.** Even for imaging-called progression, ET is no larger in half of the pairs. Clinical-only progression is
  undetectable from masks.
- **Side findings** (report to the data owners):
  - 3 cross-patient pairs have identical masks (possible duplicate patients), plus 4 near-identical pairs. IDs are in the
    doc's CSV; they are not repeated here.
- **Verdict.** No bug. The task is hard because of the data. This reframed "imaging fails" from a pipeline concern into a
  data/label property, and it motivated the trajectory features of triage T1 (B.10.1).

---

## B.5 Frozen deep features (`prism/features/deep.py`, `prism/analyses/deep_features.py`; DEEP_FEATURES.md, `c1532dd` 2026-10-11; design `docs/DL_COMPARISON_DESIGN.md`)
- **Question.** Do frozen pretrained SwinUNETR encoder features add to the baseline?
- **Design.**
  - Encoders: BraTS21 (MONAI, Apache-2.0), BrainSegFounder (UK Biobank MTA; **no redistribution**; weights live in
    gitignored `data/weights/`), and a random-weight control.
  - Pooling: mask-weighted, stages 0-3, 720 features per region, with 8-flip test-time augmentation.
  - The 768-d bottleneck was dropped: for BraTS21 its between-scan SD is 3e-4, i.e. constant.
  - Arms, all through `c3.fit_predict`: D1 nested over 32 configs, D0 random over 16, D1b radiomics + deep, DS shared
    regions, DV with volumes.
  - D2 fine-tuning and D3 diffusion were not run in this round.
- **MU results.**
  - Grade-4 **D1 ΔAUC −0.004 [−0.069, +0.063]** (it was +0.006 before the clipping fix). All gliomas +0.011
    [−0.032, +0.056].
  - D0 random −0.049 [−0.085, −0.014].
  - Configs with CI > 0: 0/80 grade 4, 3/80 all gliomas (about 2 expected by chance).
  - Nested D1 slope 0.55 (overfit).
  - Image-only: pretrained 0.65-0.72 vs random 0.57-0.59. The D1 score correlates with log tumour volume at r = 0.58.
- **LUMIERE (locked DS config).**
  - Gains of +0.05 to +0.09; 1 of 4 CIs is just above 0.
  - **But a random encoder with the same configuration gains up to +0.045.** Pretrained vs random is +0.011 to +0.069
    with no CI above 0.
  - Deep features identify the cohort (AUC ≈ 0.8, random weights too).
  - The deep models under-predict (O/E 1.35-2.08).
- **Verdict.** Failed. The external "gain" is as consistent with a scanner/cohort shift as with biology.
- **Gotcha.** The pretrained-vs-random paired numbers come from a scratchpad verifier (`deepv/check_clip.log`), not from
  repo outputs.

## B.6 Fine-tuned SwinUNETR on the 120-day label (`prism/analyses/finetune_deep.py`; FINETUNE_DEEP.md; plan `9aaa8d3` 2026-10-15, results `7bbad8f` 2026-10-16)
- **Pre-specified rule (§G).** Grade 4, arm 1: core + fine-tuned score ΔAUC ≥ 0.03 with the CI excluding 0.
- **Validity rule.** The permuted-label image-only CI must cover 0.5 **and** the permuted stack Δ must be ≤ 0.
- **Design.**
  - Cross-fit bagging: 4 inner networks per outer split, giving 100 fine-tunes per arm. Early stopping on a 20%-of-patients
    split drawn only from the inner training data.
  - Partial unfreezing of stages 3-4; lesion-centred 128³ crop; fixed hyperparameters; deterministic seeds.
  - Arms: BraTS21 grade 4 (primary), permuted control, all gliomas, BrainSegFounder, +previous scan (siamese).
  - Run time: about 2.3 h on 3 H100s for 400 jobs.
- **Results, grade 4.**

  | Arm | Image-only | Core + score ΔAUC |
  |---|---|---|
  | **BraTS21 (primary)** | 0.644 | **+0.009 [−0.022, +0.040]** |
  | Permuted | 0.476 (valid) | **+0.005 [−0.006, +0.015]**: validity "Δ ≤ 0" missed |
  | BrainSegFounder | 0.594 | −0.005 |
  | +previous scan | 0.647 | +0.014 [−0.010, +0.040] |

  All gliomas: +0.017 [−0.009, +0.044].
- **Diagnostics.**
  - The score tracks volume (r 0.57).
  - Best epoch averages 3.9: the networks barely move from their starting weights at about 100 training scans.
  - MDE is 0.045, so the run rules out large gains, not small ones.
- **Three OOM jobs** (3 processes per GPU) were rerun at 1 per GPU. The jobs are deterministic, so no number changed.
- **Verdict.** **Rule not met; fine-tuning does not help.** The validity miss was reported as written, without relaxing
  the rule. Adding any uninformative score buys about +0.005 by chance.

---

## B.7 Where the baseline's signal comes from, and robustness

### B.7.1 Schedule coupling (`prism/analyses/schedule.py`; SCHEDULE_COUPLING.md, plan 3.2, `766c511` 2026-10-11)
- **Question.** Is the baseline a proxy for the surveillance schedule, i.e. the gap to the next MRI?
- **Results.**
  - The gap alone gives 0.639 on MU and **0.788 on LUMIERE**. The gap is not known at prediction time and is partly caused
    by the outcome.
  - The baseline's conditional AUC within gap tertiles is 0.687, against 0.698 overall.
  - Its coefficient barely moves after adjusting for log gap (0.91 → 0.86 per SD).
  - The features cannot predict the gap (CV R² −0.05).
  - Excluding early post-RT scans or scans whose next scan is > 120 d away gives 0.723-0.777.
- **LUMIERE.** The volume-containing model's coefficient becomes indistinguishable from 0 after gap adjustment.
- **Verdict.** Kept. On MU the baseline is not a schedule proxy. The LUMIERE external AUCs are partly schedule-dependent.

### B.7.2 Sensitivity of the primary comparison (`prism/analyses/sensitivity.py`; SENSITIVITY.md, `766c511` 2026-10-11)
- **Nine variants:** horizons of 90 and 180 d; composite outcome (progression or death); alternative progression date;
  imaging-only follow-up; all gliomas; excluding 12-week post-RT scans; excluding one patient with conflicting dates.
- **Results.**
  - Baseline AUC 0.642-0.725.
  - Nested radiomics ΔAUC −0.032 to +0.028; **no CI excludes 0**; 6 of 9 point estimates are negative.
  - Excluding the single conflicting patient moves ΔAUC from −0.032 to −0.004.
- **Verdict.** Kept. The null result is more robust than the baseline's level.
- **Gotcha.** The primary ΔAUC (−0.032) differs from the FIX_EVALUATION validation value (−0.002) because of the label
  fix (249 vs 253 scans, death censored) and the clipping.

### B.7.3 Phase-of-care ladder (`prism/analyses/phase_ladder.py`; PHASE_LADDER.md, `5925056` + verifier corrections `461210b`, 2026-10-11)
- **Pre-specified primary.** Grade 4, post-RT cohort: R2 (clinical + 4-level phase) + I2 (volumes + morphology + delta)
  vs R2.
- **Plan provenance.** The plan was written in the module docstring and committed together with the results, after a
  smoke run had printed I0-I2 numbers. The plan was not changed after either run.
- **Primary result.** **+0.061 (−0.038, +0.156), permutation p = 0.208.**
  - The permutation null mean is +0.028: adding 44 permuted columns to a weak base already raises AUC.
  - Key secondary I3 (radiomics): +0.061, slope 0.44.
  - **Not supported.**
- **Secondary findings (kept).**
  - The 4-column phase block gives 0.664, recovering about 70% of the baseline's gain over clinical alone (0.585 →
    0.698).
  - R2 + volumes = 0.696, about R3.
  - Within post-RT, every model is 0.55-0.66.
  - The later-post-RT cohort (69 scans) is too small. Bases fall below chance (0.34-0.47), which inflates every Δ there.
  - The Riley requirement is about 750 scans for R2 and about 4040 for R2 + I2, against 167 available.
- **Exploratory.** Age alone (0.586) beats R2 (0.549) in post-RT. Part of the +0.061 is the uninformative phase columns
  dragging the base down.
- **External check.** Not feasible: LUMIERE has no RT dates.
- **Verdict.** Primary failed. It established "the baseline is a where-in-the-treatment-course model" and "within phase
  nothing discriminates well". This led to phase_censoring / C2 (2026-10-15) and the intended-use framing (2026-10-21),
  which other sections cover.

### B.7.4 SHAP (`prism/analyses/shap_contrib.py`; SHAP.md, `3364bb8` 2026-10-11)
- **Design.** OOF exact linear SHAP for ridge. TreeSHAP for HistGB in `tree_path_dependent` mode. The `interventional`
  mode gave a wrong expected value and broke additivity by up to 0.77 logits, so it was not used.
- **Baseline ridge credit.** Treatment 58%, clinical 25%, timing 17%. Time-relative features hold 35% (ridge) / 47%
  (boosting).
- **Full imaging models.** Imaging takes 45-51% of the credit with **no AUC gain**: it takes credit from correlated
  features.
- **LUMIERE under-prediction.** It is driven by `idh_unknown`, contributing −0.71 logits (IDH is unknown far more often in
  LUMIERE), together with lower DeepBraTumIA ET volumes and a never-set missingness indicator.
- **Bug found.** The 1e6 sentinel (B.3.7).
- **Verdict.** Kept as the explanation.

### B.7.5 Split variance of the PRISM report split (`prism/analyses/split_variance.py`; SPLIT_VARIANCE.md, `e037007` 2026-10-11, exploratory add-on `2877c83` 2026-10-25)
- **Design.** The PRISM report's own split search was replayed for 500 seeds. Seed 62 reproduces the original 30 patients.
- **Results.**
  - The PRISM pipeline re-selected per split gives **0.720 ± 0.055**. Seed 62 (0.801) ranks at the 92nd percentile; 7% of
    splits reach 0.802.
  - The baseline ranks at the 91st percentile on the same split, so the split favours every model.
  - The honest pipeline loses to the baseline in 88% of splits.
  - The "shipped features" variant (0.815) is optimistic, because its features were selected on other splits' test
    patients.
- **Verifier.**
  - Re-running Optuna makes things worse (−0.064). Its inner-CV objective is 0.865 against a test AUC of 0.654.
  - On seed 62, Optuna gives 0.762, so the shipped hyperparameters were not reproducible by the search either.
- **Exploratory (2026-10-26).** Images alone (I_scan / I_pure) average 0.72 over the splits, matching the PRISM pipeline.
- **Gotcha.** The `baseline_rad` per-split rows are unclipped.
- **Verdict.** Kept. This is the core of "the 0.80 is an upper-tail draw".

### B.7.6 SHAP on the PRISM split: why seed 62 is easy (`prism/analyses/shap_prism_split.py`; SHAP_PRISM_SPLIT.md, `f5b6ea2` 2026-10-11)
- **Shipped model.** Reconstructed to 1e-15. Its SHAP matches the shipped CSV (Spearman 0.997). Shares: T1c 52%, FLAIR
  26%, clinical codes 22%.
- **Why the split is easy.**
  - 36 of 82 test scans are pre-RT, and **none progresses** (89th percentile of pre-RT share across splits).
  - 60% of case-control pairs are therefore near-free wins.
  - Composition explains about 2/3 of the excess AUC.
- **Post-RT test scans only.** PRISM report model 0.778, baseline 0.730, with wide CIs.
- **Bug fixed.** `censoring_survival` crashed on bootstrap resamples with no censoring. It now uses G = 1
  (`prism/models/formulations.py`).
- **Verdict.** Kept.

### B.7.7 Clinical utility and sample size (`prism/analyses/utility.py`; CLINICAL_UTILITY.md, `766c511` 2026-10-11)
- **Calibration.** Baseline O/E 0.96, slope 0.89. Nested radiomics slope 0.60 and nested deep 0.55 (overfit).
- **Net benefit, grade 4.**
  - Radiomics vs baseline ΔNB at 30% is **−0.020 [−0.038, −0.004]**: radiomics is worse.
  - Deep ΔNB ≈ 0.
  - The baseline beats treat-all only above about a 20% threshold.
- **Gotcha: NRI.** Deep NRI is +0.48 [0.24, 0.73] while ΔAUC and ΔNB are null. Continuous NRI rewards miscalibrated
  upward shifts, so it is only reported beside ΔAUC and ΔNB.
- **LUMIERE.** The locked boosting model is about treat-all. The locked ridge under-predicts. In-fold recalibration on 61
  patients does not help.
- **Riley.** The baseline has 3 EPP; it needs 2190 scans (970 events). With 10 radiomics features it needs 2896; with the
  full pool, 174,942.
- **Verdict.** Kept. The study is underpowered by design, which explains the unstable imaging results.

---

## B.8 Triage feasibility, NO-GO (TRIAGE_FEASIBILITY.md, `prism/analyses/triage_feasibility.py`; plan `fc2d247`, results `0d252bf`, 2026-10-21; memory `triage-feasibility.md`)
- **Trigger.** The user asked whether PRISM could become triage-grade. The intended-use AUC of C2 (meaning (b)) is only
  0.601.
- **T1: trajectory features.** 11 features (Theil-Sen slopes, EW level/deviation, nadir ratio, days since nadir for ET and
  lesion), past-only. The leakage check (perturbing and dropping future scans) gave 0 deviation.
  - Result: **C2 + trajectory − C2 = −0.008 (−0.074 to +0.052)** in IU. Trajectory alone 0.543.
  - Refitted inside IU (secondary): +0.020 (−0.038 to +0.067).
- **T2: rule-out operating points.**
  - Lowest 20% of predictions: NPV **0.664 (0.508-0.786)** for C2 and 0.669 (0.515-0.803) with trajectory. The rule needs
    a lower bound ≥ 0.85.
  - About 13% of events are missed.
  - The NPV curve never reaches 0.85 at any fraction (peak 0.80 at 5%, about 9 scans).
  - The decision curve shows no useful positive range.
- **Verdict.** Both rules fail. **NO-GO on MU alone**, with no deviation from the plan.
- **Public-data map** (`docs/literature/TRIAGE_DATASETS.md`, `4dd40ae`):
  - Pooling 5 centres gives about 1000 scans and 250-300 events, with no perfusion at surveillance scale.
  - Forward triage at AUC ≥ 0.75 is unlikely.
- **Decision.** The user chose to leave the paper unchanged. Triage would be a separate paper.

## B.9 Detection at the scan, NO-GO (DETECTION_TASK.md + DETECTION_DEEP.md; plan `2b4c927` 2026-10-21, tabular `f13942b`, deep code `dd4812e`, deep results `baf2b8f` 2026-10-22)
- **Motivation.** The published 0.80 (MU) and 0.81 (LUMIERE) results address detection at the scan, not forward
  prediction. Does detection work here?
- **Label.** The positive is the first MRI on or after the documented progression. Primary negatives are verified 120-d
  non-events. The primary set is grade-4 IU.
- **Exclusions.** 47 progression scans from patients with no index scan were excluded.
- **Cohort.** The cohort file `outputs/data/detection_cohort.csv` was written before any model was fitted.
- **Tabular arms** (`prism/analyses/detection.py`), grade-4 IU (62 positives / 84 negatives):

  | Arm | AUC |
  |---|---|
  | B0 clinical | 0.530 |
  | **B1 timing + treatment** | **0.822** |
  | **P = B1 + imaging** | **0.837 (0.763-0.904)** |
  | P + radiomics | 0.833 |
  | I imaging | 0.806 |

  - **P − B1 = +0.015 (−0.032 to +0.063).** Rule 1 requires ≥ 0.03 with the CI excluding 0, so it **fails: NO-GO**.
  - **Why.** 56 of 62 positives are later post-RT, while 51 of 84 negatives are early post-RT. Timing alone nearly solves
    the task: visit index alone gives 0.775. Within later post-RT every arm is 0.62-0.64.
  - The leakage check gives 0 deviation with future scans deleted (asserted).
- **LUMIERE (locked transportable T).** **0.773 (0.679-0.857)** vs 0.804 internally, so transport holds. The no-imaging
  Tbase gives 0.689 (T − Tbase +0.084, CI just covering 0).
  - Deviations: grade-4 training rows were used, and the Tbase reference was added.
  - The estimand differs: negatives are rating-defined.
- **Deep arms G1-G4 plus all-glioma variants** (`prism/analyses/finetune_detection.py`, which reuses finetune_deep).
  - 900 fine-tunes in 5.3 h on 4 GPUs.
  - Arms: G1 current scan; G2 siamese; G3 subtraction channels; G4 permuted.
  - Image-only AUC is **0.45-0.57**, indistinguishable from G4 (0.483). Every stack equals B1 ± 0.004.
  - Rule 2 fails and rule 4 (validity) is met.
  - The pooled AUCs below 0.5 come from the CV prevalence effect (train/test prevalence r = −0.99). They are not a sign
    error.
  - Deviation: G4_all and G2_all were added and labelled.
- **G5 triage retest.** C2 + G5 − C2 = **+0.006 [−0.021, +0.034]**, so rule 3 fails.
- **EXPLORATORY correction (`70c3270`, 2026-10-22, `scripts/exploratory_pure_imaging_detection.py`).**
  - Arm I (0.806) contained timing proxies: days since the previous scan alone gives 0.740, the has-previous flag 0.726,
    and the nadir window is anchored at RT.
  - Pure images (I_pure) give **0.709**, and 0.677 within phase. Images at the scan alone (I_scan) give 0.659.
  - Timing gives 0.822 overall but only 0.640 within phase. B1 + I_pure = 0.821.
  - **Lesson.** Audit every "imaging only" arm for days and flag inputs.
- **Exploratory, 2026-10-25 (`b23d7c9`).** Clinical + I_pure = 0.706. Clinical adds nothing to images; the timeline's
  gain is all between phases.
- **Exploratory, 2026-10-26 (`e636313`).** Clinical alone on LUMIERE gives 0.554 (MU 0.530).
- **Exploratory, 2026-10-24 (`2b141ab`, `scripts/exploratory_pure_imaging_forward_lumiere.py`).**
  - Forward 120-d risk in IU: images alone 0.62 vs core 0.60.
  - LUMIERE detection: images alone 0.655, timeline 0.69, both 0.77 (`docs/manuscript/NUMBERS.md`).
- **Story impact.** The "two pathways / inductive bias" framing (images vs timeline; coupling as a display, not a model)
  comes from this work. The user liked it but had not approved it for the paper as of 2026-10-22 (memory). Later STORY
  commits (`0e5b4f8`) carry it forward as exploratory.

## B.10 Christodoulou 2026 re-implementation (CHRISTODOULOU_REPLICATION.md; `prism/analyses/christodoulou_replication.py`, `christodoulou_patient_label.py`; `0c62665`, `9810dc4` 2026-10-25)
- **Correction made.** The repo's earlier "0.64-0.70 (C1)" citation as a replication of this study was wrong: C1 is a
  forward-label ridge. The legacy "LightGBM-64 0.599" was also pre-fix. Both are replaced by this doc.
- **Pre-specified design (scan-level detection variant).**
  - v2 radiomics: 2316 columns, original image only. This is a deviation: no LoG or wavelet filters.
  - 256 features selected in-fold by univariate AUC.
  - LightGBM + Optuna (40 trials, patient-grouped inner CV) + Platt calibration.
- **Results.**
  - 5x5 CV: **0.565 (0.490-0.641)** on all grade-4 scans and 0.579 in IU. The CIs exclude 0.80, so it is **not
    reproduced**.
  - In IU it is below I_scan (−0.08) and I_pure (−0.13).
  - 100 single 20% hold-outs: mean 0.614, range 0.37-0.81; **1% reach ≥ 0.80**.
  - Platt lowers the Brier score but never beats predicting the prevalence.
  - Sanity checks: logistic regression on the same 256 features gives 0.64, and ET volume 0.62, so the shortfall is
    about data size, not a broken pipeline.
- **Locked on UCSF scan 2** (exploratory). 0.804, but the score tracks ET volume (ρ 0.67). Volume alone gives 0.88, and
  within ET-increased scans the score drops to 0.63.
- **Source check (2026-10-26).** Their code uses a **patient-level label**: "ever progresses", copied to every timepoint.
  A left-join leak also labels non-GBM patients 0.
- **Exploratory re-run with their label.**
  - GBM only: CH **0.44** under 5x5 CV, below clinical (0.57). Follow-up length leaks the class: clinical + follow-up gives
    0.75.
  - As coded: 0.73, with 23% of 30-patient splits ≥ 0.80. Clinical alone gives 0.81: the task becomes "GBM vs other
    gliomas".
- **Verdict.** Not reproduced. Their 0.80 is a single split of a patient-level, leaky estimand. This replaced the
  comparison row in the literature docs.

---

## B.11 FINAL_RESULTS.md (`7ee8e2d`, last `f5b6ea2`, 2026-10-11): what it is and its known gaps
- **What it is.** The single manuscript table as of 2026-10-11:
  - cohort; baseline; nested radiomics (primary); C2; C1; baselines ladder; schedule; split variance; head-to-head;
  - LUMIERE locked (ridge 0.608, boosting 0.620; volume rank-normalised boosting 0.659); shipped model on LUMIERE 0.613;
  - calibration; net benefit; NRI/IDI; Riley; 9 sensitivities; deep; clipping fix; feature conflicts; SHAP; PRISM split
    composition; imbalance.
- **Not in it.** Later work (the 2026-10-15 C2 / phase_censoring core, the intended-use 0.601, triage, detection, UCSF,
  Christodoulou) is not in it. It predates the "final system" story (memory `paper-story-final-system.md`), so use
  `docs/manuscript/NUMBERS.md` for current manuscript numbers.
- **Known gaps** (from the doc):
  - The shipped-model CSVs were not regenerated.
  - The C3 legacy ablation and the split-variance verifier checks are old.
  - Stale artefacts: `c3/grade4_ablation_masking_only/` and `head_to_head_{before,after}.csv`.
  - Unclipped radiomics in: C2, C1, feature_conflicts, head-to-head and split-variance `baseline_rad`.
  - `docs/results/C3_results_{grade4,all_glioma}.csv` match **neither** the pre- nor the post-fix outputs. Use
    `outputs/results/c3/` instead.

---

## B.12 Cross-cutting gotchas for a successor
1. **Old estimator.** Never quote repeat-averaged OOF AUCs (`*_averaged` columns). They are optimistic and flipped the sign
   of the C3 Δ.
2. **Post-hoc single configurations are optimistic.** Always quote the nested estimate. With 70-80 configurations, 1-3
   "significant" ones are expected by chance.
3. **Model selection inflates the null.** Selection over many candidates centres the permutation null above 0.5 (C2:
   0.55). Adding columns to a weak base raises AUC by about 0.03 even with permuted imaging (phase ladder).
4. **Uninformative scores still buy a little.** A stacked uninformative score buys about +0.005 (FINETUNE perm, G4).
   Compare real arms to the permuted arm, not to 0.
5. **CV prevalence bias.** Near-null models under grouped CV score below 0.5 (later post-RT bases, G1/G3, CH under the
   patient label). It is not a reversed signal.
6. **Timing proxies hide in imaging inputs.** Days since the previous scan, has-previous flags and RT-anchored nadir
   windows are timing, not image (B.9 correction).
7. **The 1e6 PyRadiomics sentinel.** Any radiomics path not going through `c3.selector`'s `QuantileClip` is still exposed
   to it.
8. **The random-weight encoder is mandatory.** On LUMIERE it gains almost as much as the pretrained encoders. Deep
   features identify the cohort (AUC ≈ 0.8).
9. **Fine-tuned networks at about 100 scans stop at epochs 0-4** and learn mostly a size direction (r ≈ 0.55 with ET
   volume). The image score tracks ET volume everywhere (MU, UCSF, Christodoulou).
10. **Label leaks found in other people's code.**
    - Legacy fusion selected its checkpoint on test loss.
    - Legacy LABEL_MAP is wrong.
    - Christodoulou uses a patient-level label with a non-GBM left-join leak.
    - Follow-up length encodes the class under a patient-level label.
11. **"C2" and "C1" are overloaded names** (see the header).
12. **Plans that pre-registered rules.**
    - FINETUNE_DEEP §G (`9aaa8d3`): not met.
    - Triage (`fc2d247`): T1 and T2 fail.
    - Detection (`2b4c927`): rules 1, 2 and 3 fail; rule 4 met.
    - Phase ladder (docstring, committed with the results): not supported.
    - Christodoulou (pre-specified reading): not reproduced.
    - RESEGMENTATION and CFB_ADC: rules not met.
    - No positive pre-specified imaging result exists anywhere in the repo.


---

# C. The PRISM system, external tests and reports

Scope: the system around the models (records, confidence, audit layer, reliability card), the locked external tests
(LUMIERE, UCSF-ALPTDG), which planned rules held or failed, and the LLM report agent (v1 to v3.1, field ablations).
All numbers are aggregates copied from the cited docs (`docs/results/*.md` unless stated). PRISM is the author's own
unpublished system. Patient-level files stay in `outputs/` (git-ignored); never copy record or scan IDs into docs.
Several result docs (AUDIT_SYSTEM, REPORT_AGENT, REPORT_USEFULNESS) contain scan IDs in example tables: do not quote them.

## C.0 Timeline at a glance

| date | commit | step | verdict |
|---|---|---|---|
| 2026-10-05 | 74ef0e1 | `docs/ARCHITECTURE_AND_CONTRIBUTIONS.md`: "PRISM v2" design (landmark 120-d risk, compartment concepts, trust layer, LUMIERE) | superseded by detection-at-scan system (2026-10-21 onward) |
| 2026-10-09/11 | 35d841e, 7ee8e2d | EXTERNAL_LUMIERE (120-day task) | headline of 10-09 withdrawn; final 10-11 numbers kept as secondary |
| 2026-10-15 | 1f28fec | AUDIT_SYSTEM: locked model, conformal, audit record, shortcut audit (P1/P2) | P1 met, P2 not met; layer kept as code base |
| 2026-10-15 | e33541b | REPORT_AGENT v1 (3 arms, checker) | primary 236/249 = 0.948, target 0.95 missed by 1 report |
| 2026-10-15 | de9c487 → ee3e099 | REPORT_USEFULNESS v2 (planned) | all rules met; v2 replaced v1 |
| 2026-10-21 | 74eaaf5 → c080794 | INTENDED_USE (scan-day RT-started population) | rules held; C2 0.601 |
| 2026-10-21 | 2b4c927 → f13942b | detection-at-scan plan + LUMIERE locked T 0.773 | MU NO-GO for imaging gain; LUMIERE no transport failure |
| 2026-10-25 | f461f11, 0e7c9fe | UCSF prep, UCSF_PLAN (pre-specified) | |
| 2026-10-25 | c20cfd6, 8d38097, f983c44, 0b5fa74 | UCSF Parts A/B/C + audit | Q1–Q4 "yes"; audit: AUCs re-detect enhancement |
| 2026-10-25 | 0bb211d | RELIABILITY_CARD (exploratory lookup) | kept as the card; tier = evidence, not accuracy |
| 2026-10-25 | e7cba80 → 2d72093 | SYSTEM_PLAN (S1–S7) → SYSTEM_RESULTS (S1–S4) | S1 met for combined; S2/S3 met for disagreement only at MU |
| 2026-10-25 | 3d20c41 | EXPLORATORY reduced flag design (D1–D4) | dropped from main text (round 4, RESERVE C17) |
| 2026-10-25 | 81ea83c | REPORT_V3 | S5 failed: LUMIERE 0/178 (design error) |
| 2026-10-25/26 | 4f7e7b9 → 98a84b1 → c842a1c | REPORT_V3_1 plan, freeze, results + 7-model ladder | S5–S7 met, 406/406 |
| 2026-10-26 | ac4d9ae | EXPLORATORY review-round-3 analyses (MU-fixed medians, calibration, ET baselines) | informs caveats |
| 2026-10-26 | ea5bdc0 … 10e5c91 | REPORT_FIELD_ABLATION v1 | 0/406 facts-only: prompt–checker mismatch, uninterpretable |
| 2026-10-27 | 6099fc8 → fd9fe6c | REPORT_FIELD_ABLATION_V2 | gate met 406/406 both arms |

Note: SYSTEM_PLAN says "Written 2026-10-26" but its commit e7cba80 is dated 2026-10-25 locally (UTC vs local
timezone; the overnight runs crossed midnight). Same for REPORT_V3_1_PLAN.

## C.1 Design history and package layout

**ARCHITECTURE_AND_CONTRIBUTIONS.md (2026-10-05, "PRISM v2").** Paths in it are pre-restructure (now `legacy/`).
Facts that drove later design, all still valid: radiomics texture computed on 2 grey levels (within-lesion z-score +
binWidth 25); 28% of 120-d negatives unverifiable (censored); half of scans have a prior; one third in the ≤12-week
post-RT window; cohort not GBM-only (grade 4: 254); deep features ≈ chance; GAP pooling collapses (scan-to-scan corr ≈ 1).
It proposed contributions C1–C7 (censoring-aware landmark endpoint, compartment concepts, radiomics discretisation audit,
deep benchmark, trust layer, LUMIERE external, temporal SSL). The 120-day risk framing was later replaced by
**detection at the scan** (DETECTION_TASK.md, 2026-10-21) and the "one story about the final system" rule (memory
`paper-story-final-system.md`; no v1/v2 framing in the paper). C7 never done.

**Final system (SYSTEM_PLAN.md, author direction 2026-10-26):** modular — (1) clinical+timeline pathway,
(2) engineered image-measurement pathway, (3) segmentation supplies measurements and report images, (4) confidence =
card tier + numeric per-scan measure (conformal), (5) a local LLM writes a report from the record only, checked by a
deterministic checker. Title (9446e40): "PRISM: a modular system for glioma progression surveillance on MRI".

**Package layout (current, all exist):**
- `prism/audit/`: `model.py` (locked model, `ood_ranges`/`ood_flags`), `conformal.py` (patient-weighted split conformal),
  `record.py` (per-scan audit record), `provenance.py` (MANIFEST, hashes), `reliability.py` (card situations, tier rule,
  agreement, `build_card`, `render_text`).
- `prism/analyses/`: `audit_system.py` (`python -m prism audit`), `intended_use.py` (`intendeduse`),
  `reliability_card.py` (`card`), `system.py` (`system`), `ucsf_external.py`, `ucsf_internal.py`, `ucsf_deep.py`
  (no stage; run as modules), `report_agent.py` (`report`), `report_usefulness.py` (`reportuse`), `report_v3.py`,
  `report_v3_1.py`, `report_field_ablation.py`, `report_field_ablation_v2.py` (module-only).
- `prism/experiments/external_lumiere.py` (`external`, the 120-day LUMIERE test); `prism/data/{lumiere,ucsf}.py`;
  `prism/features/ucsf_imaging.py`.
- `prism/report/`: `records.py`, `facts.py` (v1), `facts_v2.py`, `facts_card.py`, `facts_v3.py`, `facts_v3_1.py`
  (wrapper), `facts_only_v2.py` (ablation v2 spec), `field_ablation.py`, `prompts{,_v2,_v3,_v3_1}.py`,
  `sections{,_v3}.py`, `checker.py` (all versions; v3 rules selected by `F["system.version"]=="v3"`), `llm.py`,
  `vllm_run.py`, `judge.py`, `usefulness.py`, `style.py`, `figures.py`, `seg_figure.py`.
- `legacy/shipped_on_lumiere.py` (original PRISM radiomics model on LUMIERE; needs `--legacy` env + LUMIERE imaging zip),
  `legacy/glioma_agent/src/agent_pipeline.py` (original PRISM report agent; used OpenAI API, GradientExplainer SHAP on
  the fusion MLP, 0.48 alert / 0.75 "high confidence" cut-offs, a probability-based "RANO" engine).
- Tests: `tests/test_system.py`, `test_reliability_card.py`, `test_report_usefulness.py`, `test_report_v3.py`,
  `test_report_v3_1.py`, `test_report_field_ablation{,_v2}.py`, `test_seg_figure.py`, `test_ucsf.py`
  (`PYTHONPATH=. .venv/bin/python -m unittest discover -s tests`; 95 passed at v3.1 freeze).
- `report/` is NOT the LLM report: it is a LaTeX technical report on the 120-day question (`report/main.tex`, 6f43236,
  2026-10-10) plus `report/original_prism_report/` (word-for-word LaTeX remake of `docs/original_prism_report.pdf`).
  The manuscript lives in `paper/` (rebuild `paper/main.pdf` after every change).

## C.2 Audit layer around the 120-day baseline (AUDIT_SYSTEM.md, 1f28fec, 2026-10-15) — superseded task, kept code

Plan written before output (`PLAN_snapshot.md`). Model: C3 baseline ridge (clinical+timing+treatment, 23 raw / 31 cols),
reproduced to 1.7e-16. Locked artifact + model card (sha256 of inputs, git state), 200 patient-bootstrap refits for
intervals, split-conformal 70/30 (seed 10·repeat+fold), exact additive contributions (intercept+Σ = logit, err 1.3e-15),
referral flags (early post-RT, OOD, conformal {0,1}). Run: `scripts/11_audit_system.sh` (~2 min, 24 CPUs).

| rule | result | verdict |
|---|---|---|
| P1 coverage α=0.2 ≥ 0.78 | grade 4 0.841 (0.790–0.885); all gliomas 0.823 | **met**; conditional failures: during RT 0.57 (6 scans), pre-RT progressions 0/5 covered, all-glioma events 0.698 |
| P2 retained AUC at ~70% coverage − composition-matched | +0.006 (−0.023 to +0.036) / +0.003 | **not met**: abstention gain is phase mix only |

Findings that matter (gotchas): (1) missingness shortcut — dropping `idh_unknown`/`mgmt_unknown` costs ΔAUC −0.023
(−0.047 to −0.001): "molecular test not recorded → no progression"; (2) treatment-only model 0.701 ≈ baseline 0.698:
it is a treatment-course model; (3) **molecular look-ahead**: IDH/MGMT used at 8 grade-4 scans dated 1–58 d before
diagnosis (later masked in C2); (4) LUMIERE miscalibration (O/E 1.33) is mostly `idh_unknown` shift (4.4% → 40.9%;
refit without it O/E 0.89); MU-calibrated conformal on LUMIERE 0.715 (events 0.34). Post-plan code fixes: as-of rule for
age/sex/history; CITL NaN for single-class strata (was −32); subset O/E estimator unified. Env drift: scipy 1.17.1 vs
1.18.1 in uv.lock. Assessment: audit value yes, decision value not shown; flags refer 58–73% of scans.

## C.3 Intended use (INTENDED_USE.md, plan 74eaaf5 → results c080794, 2026-10-21)

Why: a referee noted the earlier "documented RT pathway" population used future information. New scan-day definition:
**grade-4 scans on or after documented RT start** (173 scans / 86 patients / 88 events / 1 censored). It removes 38 of
39 censored scans and all 14 deaths without progression. Deployed C2 (trained on all, scored on IU): **0.601
(0.515–0.686), O/E 1.01, slope 0.53**; pooled within-phase 0.616. Rule verdicts: imaging conclusions hold under
phase-specific censoring and deaths-as-non-events (no contrast ≥ +0.03 with CI > 0); C2 headline lower bound > 0.5 under
all schemes; "above chance in the intended-use population". Deviations: one 50-draw pipeline test on real labels before
the 1000-draw run; rule item used scheme-bootstrap CI. The "intended use" (RT started as of the scan day) is the
`intended_use` population flag in every later system record.

## C.4 Reliability card (RELIABILITY_CARD.md, 0bb211d, 2026-10-25) — EXPLORATORY, post hoc

A **lookup of results already measured**, not a learned confidence (author decision, OUTLINE decisions 8–10).
Situation = phase (before RT end / early post-RT ≤84 d / later / unknown) × enhancement (ET absent <0.1 cc / no previous /
not increased / increased by `measurements.volumetric_pd` / unknown). Tier: **tested** ≥10 pos and ≥10 neg in the exact
cell (AUC + patient-bootstrap CI, seed 20261021); **few cases** (counts only); **not tested**. Council (3 advisers):
exact cell only (2 vs 1), never pool cohorts, LUMIERE phase = unknown (rater "<3 months" flag not mapped).
- Only **4 tested cells**: MU later post-RT · ET not increased (38/16: timeline 0.58, images 0.77, both 0.61) and three
  LUMIERE "unknown phase" cells; UCSF none. Of 249 MU report scans: 35 tested, 212 few cases, 2 not tested.
- Agreement rule: each pathway above/below its cohort-evaluation-set median (labels not used). Agreeing scans are easy
  (combined AUC 0.83–0.92 vs 0.64–0.74 disagreeing, except UCSF locked). Which pathway is right on disagreement is
  cohort-dependent (MU timeline, UCSF images, LUMIERE neither).
- OOD (1st–99th pct + IDH/MGMT unknown) flags ~half of scans by construction (~60 inputs × 2% tails).
- Checker `card_check` / `check(..., card=True)`: no off-card performance number, tier must be stated when thin, no
  overclaim. Applied retrospectively to v1/v2 reports: they fail only by omission (35/249 pass = the tested scans); arm B
  (original prompt) also wrote off-card confidence numbers.

## C.5 Full system records and confidence (SYSTEM_PLAN e7cba80 → SYSTEM_RESULTS 2d72093, 2026-10-25)

Run: `PYTHONPATH=. .venv/bin/python -m prism system --workers 10` (~2.5 min). Outputs `outputs/results/analyses/system/`:
`records_{mu,lumiere,ucsf,mu_all_glioma}.jsonl` (schema `prism.system_record/1`), labels separately in
`*_EVALUATION_ONLY.csv`, `RECORDS_READY` sentinel, `conformal*.csv`, `selective.csv`, `tiers.csv`, `checks.csv`.
`assert_no_label` rejects label-like keys; tests check records do not change when labels flip; evaluation-set membership
is also kept out (on MU the secondary-only scans are all negatives — membership would leak).

Pathways per cohort: MU timeline B1 / images I_pure / combined B1+I_pure (OOF 5×5); LUMIERE Tbase / T_img (+ locked
3-volume model at the 10 scans without a previous scan) / T; UCSF A-Tbase / A-Ipure / A-T (locked). Records: MU 313
grade-4 detection scans, LUMIERE 178, UCSF 140. Evaluation sets: MU IU 62/84/80 pts; LUMIERE 73/105/79; UCSF 29/40/69.
All pre-evaluation checks passed (scores equal stored OOF / locked scores to 1e-16; AUCs reproduce to 3 dp).

| rule (SYSTEM_PLAN §3) | MU | LUMIERE | UCSF | verdict |
|---|---|---|---|---|
| S1 coverage α=0.2 ≥ 0.78, combined | 0.823 | 0.871 | 0.783 (LB 0.68) | **met all** |
| S1 timeline / images | 0.795 / 0.844 | 0.798 / **0.708** | **0.696** / 0.826 | images fail LUMIERE (events 0.29); timeline fails UCSF (non-events 0.50) |
| S2 AUC unflagged − flagged, disagreement | **+0.307** (+0.175 to +0.432) | +0.105 (CI ∋ 0) | −0.019 | **MU only** |
| S2 conformal {0,1} | **+0.228** | **+0.248** | +0.087 | MU, LUMIERE |
| S3 retained − phase-matched, disagreement | **+0.083** (+0.046 to +0.123) | +0.051 | −0.004 | **MU only** |
| S3 conformal {0,1} | +0.024 (LB −0.000) | +0.041 | **+0.073** | UCSF only |
| S2/S3 tier flag | reversed (−0.224) | n.s. | n/a (100% flagged) | not met |
| S2/S3 out of range, any flag | not met | not met (any-flag LUMIERE "met" on 12 unflagged scans) | n/a | not met |
| S4 Brier/error by tier (descriptive) | "few cases" *easier* than tested | tested better (0.187 vs 0.258) | all few cases | tier = evidence, not accuracy |

Gotchas: the MU tier flag is reversed because MU's only tested cell is the hard later post-RT phase, while "few cases"
cells are mostly easy early-post-RT stable scans. "Any flag" removes 91–100% of scans. Sets are wide (singleton rate
0.62–0.75). Mondrian (secondary) breaks externally (UCSF non-event coverage 0.18). Cost of split: UCSF combined
conformal model 0.775 vs displayed 0.856. **The median rule that defines disagreement was written after results had
been seen** — the paper daggers every disagreement result (paper/main.tex Table 2).

Council decisions recorded before reading S1–S4: LUMIERE image pathway = T_img + 3-volume model (MU I_pure cannot be
computed: DeepBraTumIA has 3 labels, no morphology); S3 matched by phase (LUMIERE single stratum → plain random);
conformal flag = combined {0,1} at α=0.2; OOR external = union of pathway inputs; flags with no unflagged scans = n/a.

**EXPLORATORY reduced design (3d20c41, after S1–S4):** D1 disagree, D2 conformal {0,1}, D3 or, D4 and
(`scripts/exploratory_reduced_flags.py`). D4 was the only rule with S3 lower bound > 0 in every cohort (+0.023/+0.047/
+0.038), flags 12–27%, flagged error 0.52/0.54/0.38 vs 0.22–0.25. Proposed a three-part confidence statement (evidence,
80% set, warning when set {0,1} AND disagree). Never tested on new data; removed from the main text in council round 4
(RESERVE item C17).

**EXPLORATORY review round 3 (ac4d9ae, `scripts/exploratory_review_round3.py`, outputs `review_round3/`):**
- A. Medians fixed on MU (locked model's training-row median): disagreement then passes S2 **and** S3 at LUMIERE
  (+0.222; +0.115), still not UCSF; agreement changes for 31% (LUMIERE) / 48% (UCSF) of scans.
- B. Class-conditional coverage: standard sets hold both classes only on MU; LUMIERE progression 0.767, UCSF
  non-progression 0.650.
- C. Raw log ET volume: MU-IU 0.622, LUMIERE 0.662, **UCSF 0.878** (≥ locked image pathway 0.726).
- D. MU-median threshold externally: calls 66% (LUMIERE) / 90% (UCSF) positive; UCSF specificity 0.175.
- F. **Calibration**: LUMIERE T slope 1.45 (0.85–2.54), O/E 0.97 — holds. **UCSF A-T slope 3.29 (1.96–6.28), O/E 0.72
  (0.55–0.91)** — overpredicts and compressed (planned secondary in UCSF_PLAN; reproduced).

## C.6 LUMIERE external tests

**(a) 120-day task (EXTERNAL_LUMIERE.md, final 2026-10-11, HEAD cc2e3a3).** Code `prism/experiments/external_lumiere.py`,
`scripts/06_external_lumiere.sh [--shipped]`. 132 index scans / 61 patients (47 pos / 76 neg / 9 censored); shared
features only (no treatment dates). **The 2026-10-09 headline (boosting 0.719) was withdrawn**: after label, treatment,
feature, evaluation and empty-segmentation fixes the same model gives 0.620 (0.495–0.733). Pre-specified primary
(clinical+timing+volumes, grade-4-trained): ridge 0.608 (O/E 1.33), boosting 0.620 (O/E 0.99), vs 0.667/0.675 in MU CV.
Volumes do not transport as-is (0.53–0.57; DeepBraTumIA scale + cavity labelled necrosis; 11 all-empty segmentations
now NaN, not 0 cc); cohort-rank normalisation lifts them (sensitivity, transductive). Fine-tuning/LUMIERE-only never
beat locked. Time-to-next-scan alone 0.79 (SCHEDULE_COUPLING). **Shipped original PRISM radiomics model**
(`legacy/shipped_on_lumiere.py`): 0.80 on its own MU split → 0.613 (0.500–0.729) on LUMIERE, O/E 1.24; files dated
2026-10-09 were **not regenerated** after the final label definition (open item: re-run `--shipped` before submission).

**(b) Detection at the scan (DETECTION_TASK.md, plan 2b4c927, run f13942b, 2026-10-21).** Positive = first scan rated
PD; negatives = earlier SD/PR/CR scans: 73/105/79. Locked T (clinical, log days since surgery, rater "<3 months" flag as
early post-RT, harmonised volumes + log ratios to previous, has-previous, days since previous): **0.773 (0.679–0.857)**,
Tbase 0.689, T − Tbase +0.084 (−0.006 to +0.164). Transport-failure flag (< 0.65) not triggered. **DEVIATION: fitted on
MU grade-4 detection rows (181 rows, 35% pos) instead of "all MU detection scans"**; all-glioma fit 0.768, same verdict.
Same grade-4 choice carried into UCSF Part A (NUMBERS.md 2.3, RESERVE.md). Clinical alone on LUMIERE 0.554
(EXPLORATORY, e636313).

## C.7 UCSF-ALPTDG external test

**Data (UCSF_DATA.md, UCSF_IMAGING.md, f461f11).** Downloaded under DUA to `/project/community/sbandred/ucsf/` (zip kept;
ask before deleting; the download URL is secret — never write it). Loader `prism/data/ucsf.py`, features
`prism/features/ucsf_imaging.py` (MU measurement code; volumes match the dataset table exactly). 298 patients, grade 4
140, WHO GBM 80; **one consecutive scan pair per patient** (median 56 d apart); 60 also in UCSF-PDGM. Gotchas: column
names and dictionary disagree on sign — every event re-expressed as days from scan 1 (evidence table in UCSF_DATA);
"Number of surgeries" is total, not prior; empty dates read as Excel day 0 (|days| > 20,000 → NaN); 12 progressions
within 7 d before scan 1 treated as progression at scan 1; no RT end date → MU B1 cannot be built; RT phase assumed
6-week course. Labels chosen by Claude overnight while the author slept (`pos_s2_pm30` vs primary negatives); the author
may change them.

**Plan (UCSF_PLAN.md, 0e7c9fe, pre-specified 2026-10-25).** Primary evaluation = **scan 2 only** (positives exist only
at scan 2, so has-previous / days-since-previous / change features would separate timepoints by design). Primary set
grade 4 scan 2: 29 pos / 40 neg / 69 pts. Bootstrap 1000, seed 20261025. Run on allocation 160994 overnight 2026-10-25
(26 CPUs + 1 H100; `srun --jobid=160994 --overlap ... --export=ALL`, env vars set before srun).

| question | rule | result | verdict |
|---|---|---|---|
| Q1 MU images transport | A-Ipure ≥ 0.65, LB > 0.5 | 0.726 (0.603–0.835); A-Iscan 0.795; A-Timg 0.889 | met |
| Q2 images add to clinical | A-B0+Ipure − A-B0 CI > 0 | +0.248 (+0.096 to +0.392); A-B0 0.502 | met |
| Q3 UCSF-trained beats locked | descriptive | B-Ipure 0.863 vs 0.726, +0.137 (+0.033 to +0.257) | yes (change inputs lose on transfer) |
| Q4 deep nets learn on UCSF | G1/G3 > G4, G4 covers 0.5 | G1 0.742–0.754, +0.201 over G4 0.541 (0.480–0.603) | met (but see audit) |
| timeline transfer (A-Tbase, secondary) | failure flag < 0.65 | **0.561 (0.420–0.687)** | **failed** (approximate timing; log days since surgery extrapolates: UCSF median 474 d vs MU 174 d) |
| calibration (secondary) | slope / O/E | A-T slope 3.29, O/E 0.72; A-Tbase O/E 0.67; image arms O/E 1.1–1.2, A-Iscan slope 2.20 | **not calibrated** for the combined/timeline models |

Other Part A/B/C facts: change features transfer worse (A-Ipure − A-Iscan −0.069; UCSF change 3–6× narrower than MU);
clinical at chance (B0 0.41 internal, consistent with negative CV bias under null; permuted-label check 0.40–0.46);
**UCSF's own TRAIN/TEST split** puts B-Tl at 0.450 vs random-split median 0.717 (1st percentile) — split variance again.
120-day from scan 1 (secondary): locked F-Iscan 0.668 (just above flag), internal Iscan 0.709. Deep (Part C,
`prism/analyses/ucsf_deep.py`, ~5.6 h on one H100, 400 fine-tunes, crop cache 7.6 GB in
`outputs/features/finetune_cache/ucsf/`): **MU detection runs had saved logits but no weights**, so locked G1/G3 were
retrained once on MU grade-4 rows (not the 100 cross-fitted MU nets); G2 not run. Council chose to train on all-glioma
scan-2 rows and read grade 4 off them. G4 validity would have failed at repeat 0 alone (0.710); 5 repeats were fixed in
advance, so not optional stopping. Engineering restarts (GPU dataset leak, OOM with 3 diff-input processes, OOM-retry bug)
did not affect numbers.

**UCSF_AUDIT.md (0b5fa74 + 2877c83, EXPLORATORY, `scripts/exploratory_ucsf_audit.py`).** No code leak found, but
"real but narrow": 27/29 positives are UCSF "ET Increased", progression dated a median 7 d after scan 2, a quarter of
negatives have no ET; **log ET volume alone 0.878** (Spearman 0.97 with A-Timg). Within "ET Increased" scans, locked
A-Ipure 0.53, deep nets 0.37–0.42 (below 0.5). Deep logits are a linear readout of log ET (r ≥ 0.76 trained; random sign
untrained; residual AUC ≤ 0.52). Conclusion used in the paper: UCSF AUCs measure agreement with an enhancement-based call
made at the same scan, not better generalisation.

**Pre-specified rules met / failed, summary:** met — Q1, Q2, Q4, combined S1 at UCSF, S5–S7 (v3.1). Failed — UCSF
timeline transfer (A-Tbase 0.561; S1 timeline 0.696), UCSF calibration of A-T, disagreement S2/S3 at UCSF and LUMIERE
(met at MU only), LUMIERE image coverage, v3 S5 at LUMIERE. Deviations — grade-4 fitting rows; deep training rows
(council); LUMIERE image pathway substitution (council); MU-fixed medians only exploratory.

## C.8 The LLM report agent

Data rule throughout: local open-weight models on the cluster only; no hosted model (Claude API or other) ever sees a
facts view, report or per-scan value (REPORT_V3_1_PLAN §5). LLM env `/project/community/sbandred/envs/prism-llm`
(Python 3.12, vLLM 0.31.0, flashinfer; never the project `.venv`), `HF_HUB_OFFLINE=1`, greedy, seed 0, non-thinking.

### v1 (REPORT_AGENT.md, e33541b, 2026-10-15) — 120-day risk report
Record = audit record + tertile risk tier + past-only volumes (B1 volumetric rule "indicative, not RANO"). Flat facts view
(`facts.py`) is the LLM's only input and the checker's only reference. Deterministic sections + LLM summary. Dropped from
the original agent: 0.48/0.75 thresholds, probability-based "RANO engine", unvalidated pseudoprogression score, printed
ground-truth label. Arms: A grounded Qwen3.8-27B (4×H100, JSON `{"sentences":[{"text","fields"}]}`), B original prompt
verbatim, C grounded Qwen3.5-9B. Checker (`checker.py`): numbers must equal a cited field (rounding, %), flags mentioned,
tier consistent, forbidden content (diagnosis, RANO category, management, unhedged certainty). Dev set: 59 non-grade-4
scans. Eval: 249 grade-4 scans (repeat 0). Run `scripts/12_report_agent.sh` (549 s).
- **Primary A: 236/249 = 0.948 (0.913–0.969), target ≥ 0.95 NOT met by one report.** All 13 failures: risk sentence says
  "within 120 days" without citing `risk.horizon_days` (all early post-RT). Zero numbers absent from the record.
- B: pass vs record **0/249**; forbidden content 100% (RANO verdict 241, management 242, steroids invented 84,
  "12-month" 41); omits 18% of flags. C: 243/249 but 7 forbidden hits (1 real).
- Stress 30 perturbed: A 27/30 by rule, followed the change in 30/30 on reading (failures = horizon omission, a coincident
  interval bound, an invented key). Manual reading was by an AI agent, not a clinician (36d8c9a).

### v2 (REPORT_USEFULNESS.md, plan de9c487 → ee3e099, 2026-10-15) — planned
Horizon fix (`risk.horizon` statements), public-report style (FINDINGS → IMPRESSION), usefulness criteria U1–U8 (lexical,
`usefulness.py`). Eval on CV repeat 1. **All rules met:** P1 249/249; P2a complete 247/249; P2b usefulness +0.325
(+0.312 to +0.337); guardrails 0 forbidden, 0 omitted flags. v1 on repeat 1: 238/249 (meets 0.95 there — v1's miss was
~1 report either way). Stress 27/30 (failures: prior-scan risk rounds to the old value). LLM-as-judge (Gemma 4 31B-it):
uninformative (all 5s, position bias 92/249) — do not rely on it. A clinician reader-study protocol is in the supplement
of that doc; never run. Superseded by the detection task's v3.

### v3 (REPORT_V3.md, 81ea83c, 2026-10-25) — system record, planned S5–S7
Facts v3 (`facts_v3.py`) pre-write every fixed phrase (`*statement` fields: pathway scores vs median, agreement, tier
in words, conformal sets as 4 fixed phrases, volume changes, 4 flags). Report: header, segmentation figure
(`seg_figure.py`, deterministic; the LLM never sees images; SEG_FIGURE.md, b8aa565), four sections + tables, fixed
limitations. Prompt v3.3 adds: no recommendation/review/decision, no probability words, copy fixed phrases. Checker v3
adds number words as unsupported, conformal/agreement/required-content rules. Frozen 2026-10-25T22:43:43Z (blobs in
`report_v3/FROZEN_hashes.txt`: checker `26d6637a…`). Qwen3.8-27B bf16 on one H100 (job 161514). Dev: 20 MU patients
(32 scans, seed 20261026); v3.0 23/32 → checker fix → v3.1 12/32 (schema cap cut flag sentences) → v3.3 32/32.
- **S5: MU 114/114, UCSF 140/140, LUMIERE 0/178 → not met.** Root cause: the prompt (added in dev v3.1) asks for
  the rater flag "within 3 months after radiotherapy", but the fact held only yes/no, so "3" was never in a cited field;
  5 reports also copied "three" (a forbidden number word from the facts). **Development held no LUMIERE/UCSF record**, so
  this could not be seen before evaluation. Post hoc fix gives 178/178 but the v3 result stays 0/178.
- S6 230/230 met; S7 follows 29/30 met (miss = rule artefact: old ET change 0.0 equals current volume 0.0).
- Qwen3.5-9B EXPLORATORY: 85/432 (fabricated rater sentence for MU/UCSF).

### v3.1 (REPORT_V3_1_PLAN.md 4f7e7b9 → freeze 98a84b1 → results c842a1c, 2026-10-26) — the prompt revision
Second evaluation after a seen failure, labelled as such. Checker unchanged (`26d6637a…`). `facts_v3_1.py`:
`scan.rater_statement` carries its own words incl. "3"; number words → digits. Prompt v3.4 (`prompts_v3_1.py`): lines
only for fields present. **Author decision: no RANO anywhere** (applied before freeze; acda812). Dev: same 20 MU +
10 LUMIERE + 10 UCSF patients (`default_rng(20261027)`), 58 records, 2 of 4 iterations, 58/58. Eval excludes dev
patients: MU 114, LUMIERE 162, UCSF 130.
- **S5 met all cohorts: 406/406**; S6 220/220; S7 follows 28/30 (2 ET zero-value artefacts; read: 30/30). 0 unsupported,
  0 forbidden, 0 flag errors. No report text was read by an AI agent (data rule).
- **Seven-model ladder (L1, descriptive, same frozen prompt):**

| model | S5 MU / LUMIERE / UCSF | meets all | s/report |
|---|---|---|---|
| Qwen3.5-2B | 0 / 21 / 0 | no | 0.13 |
| Qwen3.5-4B | 44 / 155 / 107 | no | 0.17 |
| gemma-4-E4B-it | 33 / 73 / 11 | no | 0.17 |
| Qwen3.5-9B | 98 / 156 / 114 | no | 0.21 |
| **Qwen3.8-27B** (primary) | 114 / 162 / 130 | **yes** | 1.08 |
| gemma-4-31B-it | 114 / 162 / 130 | yes | 4.86 |
| Qwen3.5-35B-A3B (MoE) | 97 / 162 / 130 | no (MU: combined 80% set omitted) | 0.74 |

  Below 27B failures are omissions (scores, ET volume, combined set), not invention. Serving gotchas: 35B-A3B refused to
  start at `max_num_seqs` 256 (Mamba state blocks) → bf16 with 128; the fallback script auto-ran an FP8 checkpoint by
  mistake (reported EXPLORATORY only); gemma-E4B served text-only; gemma-31B slow because KV cache ~9 GiB.

### Report-field ablation v1 (REPORT_FIELD_ABLATION{,_PLAN}.md, 2026-10-26) — failed, uninterpretable
Question: what do model-derived fields (`pathway.`, `pathways.`, `conformal.`, `card.`, `flags.`) add? Arms: full = the
immutable v3.1 reports (imported byte for byte); facts-only = those prefixes removed, own prompt/checker
(`check_facts_only`), Qwen3.8-27B, job 162122. Provenance gate re-checked every frozen artefact before every step.
- **Facts-only 0/406 vs full 406/406.** Post hoc diagnosis (`scripts/exploratory_field_ablation_diagnosis.py`):
  four co-occurring prompt–checker mismatches (availability sentence never in an accepted exact form 406; unlicensed
  narrative words 402; `meas.available` not covered 403; semantic mismatch 397) plus banned word "below" inside supplied
  change statements (59). The facts-only prompt/checker were frozen **without a development iteration**. Not an arm contrast.
- Deviations: first run failed at vLLM start (flashinfer could not JIT: `ninja` missing because the runner did not put the
  LLM env `bin/` on PATH; 0 outputs; archived in `deviation_2026-10-26_path/`; fix b10fcea with regression test; the doc cites f259c38, the same commit before a history rewrite, now on no branch); committed
  manifest listed 406 record IDs → removed (10e5c91; unsalted hashes of pseudonyms are reversible), manifest sha changed
  `dbb0e3d0…` → `bca995bb…`. Recommendation: nothing from v1 in the paper.

### Report-field ablation v2 (REPORT_FIELD_ABLATION_V2{,_PLAN}.md, 6099fc8 → fd9fe6c, 2026-10-27) — gate met
Author-approved protocol before code; one shared spec `prism/report/facts_only_v2.py` renders both prompt forms and
checker forms; banned list minus above/below/higher/lower; one `fail_` column per criterion; synthetic preflight;
dev on the 58 v3.1 dev records (≤3 iterations; iteration 0 passed 58/58 and was frozen, tag `ablation-v2-freeze`,
commit e03ec0c). Job 162548. Gate (≥386/406, ≥0.90 per cohort): **met, 406/406 both arms**. Full reports cite a median
16 model-derived keys in supported claims and drop no shared measurement fact. Stress (v1's 6 records): facts-only 6/6,
full 0/6 under the verbatim rule (exploratory: magnitude and direction written in 6/6). Clinical-inference pattern 278/406
full reports, all traced to supplied `card.situation` text (`scripts/exploratory_field_ablation_v2_diagnosis.py`).
Allowed paper text: one supplement sentence, no clinical-benefit claim. Implementation plans:
`docs/superpowers/plans/2026-10-26-report-field-ablation.md`, `2026-10-27-report-field-ablation-v2.md`.

### Standing limits of all report work
The checker is lexical (numbers, flags, tier words, citations). It cannot see a correct number attached to the wrong
concept. No clinician has read any report; no reader, decision, workload or outcome endpoint was ever measured.

## C.9 How to run each piece

| piece | command | where / time |
|---|---|---|
| audit layer (120-d) | `scripts/11_audit_system.sh` (= `prism audit --workers 24`) | CPU, ~2 min |
| intended use | `python -m prism intendeduse --workers N` | CPU, < 1 min |
| reliability card | `PYTHONPATH=. .venv/bin/python -m prism card [--steps table records evaluate]` | 4 CPUs, minutes |
| system records + S1–S4 | `PYTHONPATH=. .venv/bin/python -m prism system --workers 10` | ~2.5 min |
| reduced flags / round 3 | `scripts/exploratory_reduced_flags.py`, `scripts/exploratory_review_round3.py` | CPU |
| LUMIERE 120-d | `scripts/06_external_lumiere.sh [--shipped]` | CPU; `--shipped` needs legacy env |
| LUMIERE detection | `python -m prism detection` (DETECTION_TASK.md) | CPU |
| UCSF prep | `python -m prism.data.ucsf`; `PRISM_WORKERS=24 ... python -m prism.features.ucsf_imaging` | ~2 min, 24 CPUs |
| UCSF A / B / C | `python -m prism.analyses.ucsf_external` / `ucsf_internal` / `ucsf_deep` | 3 min / 3 min / ~5.6 h 1 H100 |
| UCSF audit | `scripts/exploratory_ucsf_audit.py [--within-et-increased]` | 4 CPUs |
| report v1 / v2 | `scripts/12_report_agent.sh` (needs `PRISM_LLM_ENV`); `python -m prism reportuse` | 4 H100 / 1 H100 |
| seg figures | `python -m prism.report.seg_figure --all --workers 6` | CPU |
| report v3 / v3.1 | `python -m prism.analyses.report_v3 --steps select sets stress requests generate evaluate render examples`; `report_v3_1 --steps ... [--sets dev eval stress] [--model ...]` | 1 H100, ~15 min |
| ablation v1 / v2 | `python -m prism.analyses.report_field_ablation --steps freeze stress requests generate evaluate evaluate-stress render`; v2: `--steps consistency`, `dev --iteration k`, `preflight`, `freeze`, `requests generate evaluate [--sets stress]` | 1 H100; parent interpreter `.venv` (LLM env lacks pandas) |

Cluster: work from the login node with `srun --jobid=<alloc> --overlap -N1 -n1 --cpus-per-task=<≤free> --export=ALL`
into the user's interactive allocation (memory `cluster-workflow.md`); `env` as the srun command fails; requesting more
than the free CPUs blocks. `submit.sh` (untracked, repo root) is a generic batch wrapper for the A3 Mega H100 partitions.
Allocations by date from the empty `slurm-*.out` files: 160994 (10-24, UCSF), 161514 (10-25, v3/v3.1), 162122 (10-26,
ablation v1), 162548 (10-27, ablation v2), 163973 (11-01).

## C.10 Gotchas for a successor (system, external, reports)
1. Never put labels or evaluation-set membership in a system record; on MU membership itself leaks the label.
2. Development sets must contain every cohort the evaluation contains (v3 LUMIERE 0/178).
3. Freeze prompt + facts + checker by git blob hash before evaluation; record any second evaluation after a seen failure
   as such and never revise the first result.
4. A prompt and its checker must be rendered from one shared spec, with a consistency test (ablation v1 0/406).
5. LLM runners must put the LLM env `bin/` on PATH (flashinfer needs `ninja`); do a synthetic preflight.
6. Do not commit record IDs, even hashed.
7. Agreement medians are a post-results rule; use MU-fixed medians if this is rerun prospectively.
8. UCSF high image AUCs are enhancement re-detection; always report log ET volume alone as the reference.
9. MU detection deep runs saved no weights; any locked deep test needs retraining.
10. The `follows` perturbation rule cannot score a zero-valued old change; the verbatim rule penalises paraphrase.
11. Shipped-model LUMIERE files (2026-10-09) are stale relative to final LUMIERE labels.


---

# D. Timeline, manuscript history, infrastructure and working rules

Scope: the whole project from 2026-09-14 to 2026-11-01 as seen in git (220 commits on `manuscript-week`; `origin/main`
is at 6ad5e0e, 2026-10-27, and `manuscript-week` is 31 commits ahead of it and in sync with `origin/manuscript-week`),
the manuscript's evolution, the infrastructure, and the standing rules any successor agent must follow. Detailed
results (numbers, root causes) are in sections A-C of this work log; here each result is named only as far as it
dates or explains a turn in the project. All numbers are aggregates; the source doc is named.

---

## D1. Chronological timeline

Hashes are short git hashes. "Plan" = a pre-specified analysis plan committed before any real-label run.

### Phase 0. Inherited code and audit (2026-09-14 to 2026-09-26)

| Date | Commits | What happened |
|---|---|---|
| 09-14 | d3b132f, 21c1540 | Initial commit (author's account) and "init: code reproducability": the original PRISM code (radiomics pipeline, MLPFusion, a "SWIN UNetR" notebook, glioma_agent report generator). 21c1540 is the audit baseline and the commit the user restored after the 10-05 wipe. |
| 09-14 | (doc committed later in 74ef0e1) | `docs/CURRENT_STATE_AND_NEXT_STEPS.md`: static audit of 21c1540. Key findings: endpoint is 120-day forward risk, not current progression; the report's "RANO" is derived from probability changes, not measurements; the "SwinUNETR" is a random-init generic transformer; fusion picks its checkpoint on test loss; reports leak future visits/labels; visit-level (not patient-level) bootstrap; feature selection not nested; recalculated shipped metrics radiomics AUC 0.8043 vs fusion 0.8006 on 84 test visits / 30 patients (operating-point difference, not superiority). |
| 09-26 | (committed in 74ef0e1) | `docs/ACTION_ITEMS.md`: "reproduce first, then improve" plan (Stage 1 reproduce LogReg 0.8043; Stage 2 data layer: cohort builder, censoring, codebook, timing, discretisation check, measurement table, repeated grouped CV; Stage 3 re-baseline; Stage 4 PUBLICATION_PLAN.md Parts C-D). Both docs carry a header note that paths predate the 10-10 restructure into `legacy/`. They are historical: almost every checkbox was overtaken by Phases 1-3 and the checkboxes were never ticked. |

### Phase 1. Reproduction (2026-10-04 to 2026-10-05)

| Date | Commits | What happened |
|---|---|---|
| 10-04 | (uncommitted until 10-05) | Reproduction on orchard-community-4 (memory `reproduction-status.md`): manifests and feature JSONs match the HF reference `sbandred/mu-glioma-post-processed`; shipped LogReg-48 AUC 0.8043 reproduces, but the default search picks SVM-32 (0.7977), so the shipped config came from an unrecorded run; SWIN embeddings reproduce only with the 3rd `SwinEncoder3D` build after seed 42 (build index 2); fusion metrics are a lucky seed (acc ~95th pct of 50 seeds); encoder untrained (embeddings alone AUC ~0.50). BraTS21 SwinUNETR fine-tuning stage 1 Dice 0.495 -> 0.697; stage 2 image-only test 0.635/0.652, late fusion delta CIs span 0. Bug: global-avg-pooled swinViT features identical across scans -> lesion-masked pooling. |
| 10-05 | - | `/project/community/sbandred` wiped about 15:04 (cause unknown, not Claude). User restored git to 21c1540; session code restored from `~/.claude/file-history` and the transcript; data re-downloaded. |
| 10-05 | 2324d04, 5a2c234, 677139d, 74ef0e1, a47ee3a | uv environment (Python 3.11, torch CUDA 13.0, MONAI); SwinUNETR reproduction + fine-tuning code; reproduction/validation scripts and FINDINGS/PROCEDURES/AUDIT/LITERATURE docs (now `legacy/reproduction/`); audit docs; `docs/ARCHITECTURE_AND_CONTRIBUTIONS.md` ("PRISM v2" architecture with candidate contributions C1 censoring-aware endpoint, C2 measurement/feature search, C3 corrected radiomics vs clinical baseline). Lit review: Christodoulou 2026 already does binary radiomics ~0.80 on MU, so that alone is not novel. |

### Phase 2. New data layer and contributions C1-C3 (2026-10-06)

| Commits | What |
|---|---|
| bb479a2, 2736c34 | `prism/` data layer (cohort 596 timepoints -> 314 index scans / 157 patients; follow-up, codebook, timing) and C1 censoring-aware endpoint experiment (`docs/results/C1_endpoint.md`); scikit-survival added. |
| 701a46e | C2 measurement table and feature-group search (`C2_feature_search.md`). |
| aa4b34d, 3009e95 | C3 corrected radiomics vs clinical + treatment baseline; head-to-head on the original PRISM split (then misnamed "published split"; renamed "PRISM report split" on 10-10). All 10-06 numbers were later superseded by the 10-11 fixes. |

### Phase 3. Review, external test, restructure (2026-10-09 to 2026-10-11 morning)

| Date | Commits | What |
|---|---|---|
| 10-09 | b570ad8 | `docs/PIPELINE_REVIEW.md`, comparative methods, paper plan (`PUBLICATION_PLAN.md`). |
| 10-09 | 35d841e | External test on LUMIERE (raw and fine-tuned). Headline 0.719 later withdrawn: after the 10-11 fixes the same model gives 0.620 (`EXTERNAL_LUMIERE.md`). |
| 10-10 | 92e7544 | Restructure into `prism/{data,features,models,...}`; original code moved to `legacy/` (`radiomics/`, `MLPFusion/`->`mlp_fusion/`, `glioma_agent/`, `SWIN UNetR/`->`swin_unetr/`, `reproduction/`). |
| 10-10 | 6f43236 | Imaging vs non-imaging summary, LaTeX technical report in `report/`, the "PRISM report" naming (user correction: PRISM is unpublished). |
| 10-11 | 86bca95, 01af14b | `docs/literature/RELATED_WORK.md` (top 10 per topic, APA 7); `docs/MANUSCRIPT_ONE_WEEK_PLAN.md` + `MANUSCRIPT_PLAN_SUMMARY.md`. |

### Phase 4. Fixes and the full re-run (2026-10-11)

| Commits | What (details and root causes in sections A-C) |
|---|---|
| e037007 | As-of-scan treatment features (treatment known at the scan date only), post-RT x MGMT flag, split-variance analysis (`SPLIT_VARIANCE.md`: the PRISM report split vs 500 random splits), DL comparison design (`docs/DL_COMPARISON_DESIGN.md`). |
| 19747c7 | Label fixes (death without progression censors; flag/date conflicts; data errors) and feature fixes (LUMIERE necrosis+cavity, delta flags, Euclidean margin): `FIX_LABELS.md`, `FIX_FEATURES.md`. |
| c1532dd, 87de654 | Evaluation fixes (mean-over-repeats AUC, per-fold external estimators, patient-level permutations, nested boosting), stages head2head/splitvar/deep, `scripts/` pipeline (`FIX_EVALUATION.md`, `DEEP_FEATURES.md`). |
| 766c511, 2dd60c8, 7ee8e2d | Baselines ladder, schedule coupling, clinical utility, sensitivity, manuscript tables; cleanup from verification; `FINAL_RESULTS.md` from the full re-run. |
| bc4bc0c, 3364bb8 | Radiomics clipped to training-fold 1st/99th percentiles: a PyRadiomics 1e6 sentinel blew up the stacked score (`FIX_RADIOMICS_CLIP.md`); feature conflicts, SHAP, imbalance. |
| f5b6ea2 | SHAP on the PRISM report split; IPCW survival handles no-censoring resamples. |
| 5925056, 461210b | Phase-of-care ladder, pre-specified primary contrast (`PHASE_LADDER.md`: clinical 0.585 -> + timing 0.644 -> + treatment 0.698, grade 4); verifier corrections. |
| 3d28aeb | `docs/literature/COMPARABLE_RESULTS.md` (verified published numbers, task caveat). |
| fc09ac4, d82969b | Imaging positive controls (`DIAGNOSTICS_IMAGING.md`); re-segmentation with BraTS21 SwinUNETR and BrainSegFounder, pre-specified rule not met (`RESEGMENTATION.md`). |

### Phase 5. Imaging search continued, first manuscript, report v1/v2 (2026-10-15 to 2026-10-16)

| Date | Commits | What |
|---|---|---|
| 10-15 | 9cc58e0 | Candidate datasets CFB-GBM, UCSD-PTGBM (`docs/literature/DATASETS.md`); TCIA Aspera blocked from the cluster. |
| 10-15 | 77c694f, c0bc537 | Clean-label test: imaging-defined MU endpoint, imaging 0.628 vs baseline 0.696 (`CLEAN_LABEL.md`); CFB-GBM ADC vs conventional radiomics, pre-specified rule (delta >= 0.03, CI excl. 0) (`CFB_ADC.md`). |
| 10-15 | 1f28fec | Auditable decision-support layer around the baseline model (`AUDIT_SYSTEM.md`; per-scan audit record, locked artefact, model card). |
| 10-15 | f4cf52c, e33e560, cd7b688 | Figures 1-5, Markdown draft (`docs/manuscript/DRAFT.md`, `SUPPLEMENT.md`, `DRAFT_NOTES.md`; now frozen), LaTeX conversion into `paper/` with `build.sh`. |
| 10-15 | 65d2e26 | Reframe as "the PRISM paper" (user: PRISM is the author's own system; not a re-evaluation of others). |
| 10-15 | e33541b, 8cc9f0f, c4d0599 | Report generator v1 rebuilt on the per-scan audit record (`REPORT_AGENT.md`, local vLLM), Figure 5, supplement S19. |
| 10-15 | 01c9500 | Formatted for CMBBE: Imaging & Visualization (T&F Interact, CSE refs). |
| 10-15 | e429c24, 95e904e, 36d8c9a | Internal review with verification (`INTERNAL_REVIEW.md`); one-narrative rewrite; disclosure that the 15 reports were read by an AI assistant, not a clinician. |
| 10-15 | c98febe -> f75ce82 | Plan then results: phase of care vs censoring (`PHASE_CENSORING.md`). |
| 10-15 | 9aaa8d3 | Plan: fine-tuned SwinUNETR encoder (`FINETUNE_DEEP.md`). |
| 10-15 | de9c487 -> ee3e099, 2b5314a | Plan then results: report v2 (usefulness, public-report style; all pre-specified rules met; `REPORT_USEFULNESS.md`); manuscript gets the corrected core model, report v2, S20-S21. |
| 10-15 | (history rewrite) | User asked to strip `Co-Authored-By: Claude` from all commits; history on `manuscript-week` after `origin/main` rewritten and force-pushed. No commit in the repo now carries the trailer (checked 2026-11-01). |
| 10-16 | 0a5ad0e, 7bbad8f, 0e9bb8e | Fine-tuned encoder arms 1-5: does not help; permuted control missed its limit by +0.005; manuscript S22. |
| 10-16 | d247be1, a8daf88, e5b7ef1 | `JOURNAL_RULES.md` (live T&F rules pasted by the user); generative-AI declaration draft; Tables 4-5, study-design placeholder. |

### Phase 6. Final-system restructure, intended use, triage and detection (2026-10-21 to 2026-10-22)

| Date | Commits | What |
|---|---|---|
| 10-21 | 74eaaf5 -> c080794, 12f2056 | Plan then results: scan-day intended use (RT started): corrected core C2 0.601 (0.515-0.686) (`INTENDED_USE.md`); S23. |
| 10-21 | b510824 | Manuscript restructured "around the final system: one story, no version history"; Rai 2026 removed (author). |
| 10-21 | cc8f567, ca59cd8 | Study design and imaging-example figures; no deployment claim ("not ready to guide care"). |
| 10-21 | fc2d247 -> 0d252bf, 4f58376 | Triage feasibility plan then NO-GO (trajectory adds -0.008; best rule-out NPV 0.67 at 20%) (`TRIAGE_FEASIBILITY.md`). Paper deliberately left unchanged. |
| 10-21 | 4dd40ae | `docs/literature/TRIAGE_DATASETS.md`: public post-treatment glioma datasets; pooling about 1,000 scans; forward triage at AUC >= 0.75 unlikely. |
| 10-21 | 2b4c927 -> f13942b | Plan then results: detection at the scan: P 0.837 but P - B1 +0.015 (CI -0.032 to +0.063); NO-GO on MU alone; LUMIERE locked 0.773 (`DETECTION_TASK.md`). |
| 10-21/22 | dd4812e -> baf2b8f | Detection deep arms (9 arms incl. siamese/subtraction): none adds to B1; G5 triage retest fails rule 3 (`DETECTION_DEEP.md`). |
| 10-22 | 70c3270 | EXPLORATORY: the planned "imaging-only" arm (0.806) contained timing proxies (days since previous scan, has-previous, RT-anchored nadir); pure imaging 0.709. Origin of the image-model "ladder" 0.66 -> 0.71 -> 0.81. |
| 10-22 | 15771d0, 0432ed7 | Tooling: task-observer skill and superpowers plugin at project scope. |

### Phase 7. Writing method, story, locked abstract (2026-10-23 to 2026-10-24)

| Date | Commits | What |
|---|---|---|
| 10-23 | 49a8e75 | `STYLE.md` (models, 80/20 disclosure, numbers, prose, layers, tests), `RESERVE.md`, new argument outline, `.claude/skills/paper-writing/`. Trigger: author judged the 10-22 draft "really really bad", an analysis report. |
| 10-23 | 5b616a0, b562af1, 7b3f27b, 5323b43 | Abstract drafts 2 and 3 (rejected: too many numbers; Claude's default voice); `STORY.md` (story in one paragraph, every result mapped to step/status/place); abstract back to draft 1 with a new ending. |
| 10-24 | 6f8854a | Abstract locked (`LOCKED.md`, 149 words); the skill reads LOCKED.md and STORY.md first. |
| 10-24 | 2b141ab | Exploratory gap-fill: images alone vs timeline for 120-day risk (0.62 vs 0.60 in intended use); LUMIERE image-only detection 0.66, both pathways 0.77. |
| 10-24/25 | 69fbbac, ffa9e9e, acda812, dd1d853 | OUTLINE decisions log 1-7 (task = detection at the scan; UCSF in; name PRISM without acronym; RANO left out); author disliked the five-step outline brief. |

### Phase 8. External tests and the full system (2026-10-25)

| Commits | What |
|---|---|
| f461f11 | UCSF-ALPTDG preparation: loader `prism/data/ucsf.py`, image measurements `prism/features/ucsf_imaging.py`; volumes match the dataset table exactly; descriptive only (`UCSF_DATA.md`, `UCSF_IMAGING.md`). |
| 0e7c9fe | `UCSF_PLAN.md`, pre-specified: scan-2 evaluation (positives only at scan 2), locked MU models, UCSF-trained models, deep arms. Labels chosen by Claude while the author slept. |
| b23d7c9, 2877c83 | Exploratory: images + clinical without timeline 0.71; image-only on the first split 0.79 vs 500 splits 0.72. |
| c20cfd6, 8d38097, 0b5fa74, f983c44 | UCSF Parts A (locked MU: scan-alone 0.80, pure 0.73, clinical 0.50), B (UCSF-trained images 0.83-0.91; clinical at chance; UCSF timeline 0.67), audit (ET volume alone 0.88: labels are an enhancement call at the same scan), C (deep 0.71-0.76, permuted 0.54) (`UCSF_RESULTS.md`, `UCSF_AUDIT.md`). |
| b720b0e, 75ea111, 75ec9e0 | STORY "labels decide what a model learns"; OUTLINE draft 2 / 2.1 (system first, three cohorts, reliability card). |
| 0bb211d | Reliability card (exploratory lookup by phase x enhancement) (`RELIABILITY_CARD.md`). |
| 0c62665, 9810dc4 | Christodoulou-style re-implementation 0.565 under repeated CV; their label is patient-level (exploratory re-run) (`CHRISTODOULOU_REPLICATION.md`). |
| e7cba80, 2d72093, 3d20c41 | `SYSTEM_PLAN.md` (S1-S7, pre-specified) -> `SYSTEM_RESULTS.md`: conformal coverage met in all cohorts; disagreement flag meets S2/S3 on MU; exploratory reduced-confidence design D4. |
| ba3ee4e, 275f0d4 | STYLE framing rule (capabilities first, challenges paired with mitigations); `SYSTEM_LANDSCAPE.md` (47 references; nearest system Jabal 2026). |
| b8aa565 | Segmentation figure for report v3 (`SEG_FIGURE.md`; no later scans, checked twice). |
| 81ea83c | Report v3 (checker frozen first): MU 114/114, UCSF 140/140, LUMIERE 0/178 (prompt asked for a fact not in the record) (`REPORT_V3.md`). |
| 4f7e7b9, 336f289, dcce99c, c1c3b9f, 98a84b1, 097d9be, ff894e2, c842a1c | Report v3.1: plan, facts/prompt v3.4, development patients selected first, no RANO, freeze with hashes, Qwen3.5-35B-A3B serving fixes, results 406/406 faithful, tiers 220/220, perturbations 28/30; model ladder: Qwen3.8-27B and gemma-4-31B-it pass every cohort (`REPORT_V3_1.md`). |
| 74f790e | OUTLINE draft 3 (five known challenges, each with a PRISM module). |

### Phase 9. Manuscript week 1: skeleton, prose, council, report ablation (2026-10-26)

| Commits | What |
|---|---|
| 9446e40, 69d6e09 | Title "PRISM: a modular system for glioma progression surveillance on MRI" (author); skeleton on draft 3 with authors/CMU affiliations. |
| 1e5c595 | Backup before council: tag `backup-before-council-2026-10-26`, copies in `paper/backup/`. |
| 8e7cc05, a89e2f8 | `META_PATTERNS.md` (author's instruction patterns, sentence checklist); `NUMBERS.md` (verified fact sheet with CI, population, source, planned/exploratory). |
| e636313 | Exploratory: clinical alone on LUMIERE detection 0.554. |
| c2f7929, da7d2e7 | Full prose draft and review fixes. |
| 0995568 ... 06bccb1, 9a30030 | Council rounds 1-5 (see D2.4). |
| f82f395, a9e1a17, df463d6, 4e21c81, a9bc9e0, ea9acd5, ff05dd5, 5c43c0a | "System-first" rewrite (superpowers spec/plan in `docs/superpowers/`): STORY/OUTLINE "System-first revision (approved 2026-10-26)"; first `generate_system_first_figures.py`; ORCID and funding disclosure. Commit style switches to `docs:/feat:/fix:/build:` prefixes. |
| ea5bdc0 ... 10e5c91 | Report-field ablation v1 (facts-only vs full evidence), plan and pipeline; result facts-only 0/406 vs full 406/406, diagnosed post hoc as prompt-checker mismatches (`REPORT_FIELD_ABLATION.md`); record IDs removed from the committed manifest (10e5c91). |

### Phase 10. Report ablation v2 (2026-10-27)

| Commits | What |
|---|---|
| 6099fc8, 030387b | v2 protocol pre-specified, author approval recorded before any v2 code. |
| ec5a44d ... ef9d90b | Shared spec/prompt/checker, dev iterations, freeze criterion, preflight bound to frozen code, paired stress test. Tags `ablation-v2-dev-iter0`, `ablation-v2-freeze`. |
| e03ec0c, a159ea3, fd9fe6c, 6ad5e0e | Freeze record; results facts-only v2 406/406 = full arm, gate met (`REPORT_FIELD_ABLATION_V2.md`); shared-key reading exploratory. 6ad5e0e is the current `origin/main`. |
| c47ae73 | Author's reaction to the proposed system-first abstract ("reads as fragments") recorded in STYLE 10. |

### Phase 11. Overnight paper passes (2026-10-28)

| Commits | What |
|---|---|
| 37d815e ... eacf6df | Loops 1-9: real data figures replace placeholders; notebook residue cut; definitions; voice; number audit (two wrong claims fixed); 4 cold + 3 hostile reads. Pre-pass copy `paper/backup/main_pre-overnight_2026-10-28.*`. |
| 7ff7997 ... 30b6132, 2ac4fb8 | Loops 10-18 (author: "concise and right"): figures in text, 3,867 -> 2,794 words, Table 1 = the scores, figure redraw (12b), validation rounds restoring lost qualifiers/daggers. Copy `paper/backup/main_pre-loop10_2026-10-28.*`. |
| 57a6eda, af9bc46 | Supplement pointers stated inline (no red placeholders); Figure 5A as a plain clinical report with a drawn segmentation strip. |

### Phase 12. Supervisor review, prior art, title (2026-11-01)

| Commits | What |
|---|---|
| 44abf6f | Illustrated prism Figure 1 (`scripts/fig1_prism.py`); finding-first figure titles 2-4. |
| 7c6b383 | Finding-first abstract, title and Introduction with four numbered contributions (supervisor). |
| cf869ae | `docs/literature/PRIOR_ART_2026-11-01.md`: adversarial prior-art search; all four contributions PARTIAL. |
| 5962717, 0b9fa31 | Title council (`council/titles_2026-11-01.md`), framing rules; each contribution stated against its nearest precedent; ~14 references added to refs.bib; title "Timing or tumour? ..." |
| 3b2a423, b3cf90c, a037d75 | Abstract names MU-Glioma-Post as "the public development cohort", 150 words; STYLE 10 rule. |

Unattributed lull: no commits 10-16 -> 10-21 and 10-28 -> 11-01.

---

## D2. Manuscript evolution

### D2.1 Framings in order (tried, superseded, current)

| Dates | Framing | Why dropped / changed | Where recorded |
|---|---|---|---|
| 10-05 to 10-11 | "PRISM v2": contributions C1 censoring-aware endpoint, C2 measurement search, C3 corrected radiomics vs baseline; plus re-evaluation of "the published model" | PRISM is not published (10-10); radiomics adds nothing over clinical+treatment; contributions shifted | `ARCHITECTURE_AND_CONTRIBUTIONS.md`, `PUBLICATION_PLAN.md`, `report/main.tex` (technical report) |
| 10-11 to 10-15 | "Does MRI add to clinical information for 120-day risk?" (imaging vs non-imaging; one-week plan) | Became a negative-results report | `MANUSCRIPT_ONE_WEEK_PLAN.md`, `DRAFT.md` (frozen) |
| 10-15 | "We present PRISM" (full pipeline, branches ablated honestly, deployed core = clinical + treatment model, audit layer, report agent); 0.80 single split as "our initial evaluation" | Framing kept in spirit, but the paper was a v1/v2 history | 65d2e26; memory `prism-unpublished-naming.md` |
| 10-15 to 10-21 | v1 vs v2 versions (PRISM v1 radiomics + fusion; v2 corrected core, report v1 vs v2, Table 5) | Author 10-21: one story about the final system, no version history; drop leaky boosting model, Rai 2026 | b510824; memory `paper-story-final-system.md` |
| 10-21/22 | Triage story (could PRISM triage?) | NO-GO twice (triage 0d252bf, detection f13942b/baf2b8f); author: "let the paper be"; triage would be a separate paper | memory `triage-feasibility.md` |
| 10-22 to 10-24 | "Two pathways / inductive bias": images vs timeline; the 0.80 split as the hook; locked abstract | Predates UCSF; no external tests or confidence in it | `LOCKED.md`, `STORY.md` steps 1-5 |
| 10-25 | Five-step brief ("a good score that measured the test set" ... "where the system says it isn't reliable") | Author disliked it (no reason given); revisit after UCSF | dd1d853, STYLE 10 |
| 10-25/26 | Draft 2/2.1 then draft 3: capabilities first, five known challenges C1-C5 each paired with a module; no accusation of the field; modular PRISM | Accepted 10-26; base of the skeleton and council | OUTLINE draft 3 |
| 10-26 | "System-first / evidence reporting" (superpowers spec): PRISM as a transparent reporting system; v3.1 as primary report evidence | Overlaid on draft 3; still in OUTLINE/STORY headers | `docs/superpowers/specs/2026-10-26-prism-system-first-manuscript-design.md` |
| 10-27 | Proposed system-first abstract | Author: reads as fragments (component inventory, five AUCs); needs one narrative, punchline first | c47ae73 |
| 10-28 | Finding-first proposal (P1): what carries a score differs by cohort (timing at MU, enhancement at UCSF) | Adopted 11-01 | `OVERNIGHT_PROPOSALS.md` P1 |
| 11-01 (current) | Finding first, system as the response; four numbered contributions narrowed by prior art: (1) a measurement of a partly known effect, within phases of care and across externally tested centres; (2) per-scan confidence joining conformal set, pathway disagreement and the situation record; (3) locked tests at two external centres under rules fixed in advance; (4) deterministic check of every local report and the model size it needs | Pending author approval of title | OUTLINE "Contributions and framing (2026-11-01)" |

Elements removed for good: RANO (decision 3, 10-25; extended 10-26 to figures and report wording: "indicative
volumes", not "not RANO"; only remaining trace is RANO in a cited LUMIERE paper's title, author's call); Rai 2026;
the leaky boosting model; v1/v2/v3 report results as main-text numbers (development history only); 120-day risk as
headline (kept in the body with intended-use 0.60); go/no-go language; "first"/"novel"; "development centre".

### D2.2 Doc roles in `docs/manuscript/`

| File | Role | State |
|---|---|---|
| `STORY.md` | Results mapped to story step, status (planned/exploratory), destination and source | Header "System-first narrative map (approved 2026-10-26)"; older step tables kept below |
| `OUTLINE.md` | Argument, figure plan, decisions log 1-19 | Top section dated 2026-11-01; older draft 3 sections kept as record |
| `STYLE.md` | Writing rules; section 10 = dated author reactions (rules) | Last entry 2026-11-01 |
| `LOCKED.md` | Author-approved passages | Only the 2026-10-24 abstract; main.tex abstract differs and is a flagged proposal |
| `RESERVE.md` | Reviewer questions held back with answers (80/20 rule; only items that leave the conclusion unchanged) | Active |
| `NUMBERS.md` | Verified fact sheet for prose (628 lines) | Active; source for figures |
| `META_PATTERNS.md` | Author's instruction/reaction patterns, wording rules | 10-26 |
| `OVERNIGHT_LOG.md` / `OVERNIGHT_PROPOSALS.md` | 10-28 loops 1-18; proposals P1-P12 | See D2.5 |
| `council/` | Rounds 1-5 reviews and decisions, `COUNCIL_SUMMARY.md`, `titles_2026-11-01.md` | |
| `JOURNAL_RULES.md` | Target journal rules and submission checklist | |
| `DRAFT.md`, `SUPPLEMENT.md`, `DRAFT_NOTES.md` | Frozen 10-15 snapshots; do not edit | Frozen |
| `INTERNAL_REVIEW.md`, `FIGURES.md`, `FLOW.md`, `TABLE1_COHORT.md`, `CHECKLIST_TRIPOD_AI.md`, `CHECKLIST_CLEAR.md`, `LITERATURE_TABLE.md` | 10-15/16 era support docs | Partly stale (pre-final-system) |

### D2.3 STYLE section 10: the author's reactions (dated rules)

- 10-21 one story about the final system; no version history; drop leaky boosting model and Rai 2026.
- 10-22 imaging is not worthless; each kind of evidence "speaks for what it is"; most datasets lack timing so the image
  pathway must stand alone; coupling can be a display, not a model.
- 10-23 about 80% shown, 20% left to reviewers (selection, not disinformation); abstract with one or two numbers;
  120-day risk not the headline; do not say the AUC was wrong, say what an AUC cannot tell; voice needs its own check
  (contrast slogans, staccato, abstractions as subjects are Claude tics); revise conservatively (draft 1 voice
  preferred); agree STORY before prose.
- 10-25 every main-text result must answer "so what?"; report gets little space, deep learning only as much as it
  adds; five-step brief disliked; RANO out.
- 10-26 no accusing the field; capabilities first, challenges paired with mitigations; PRISM modular (deep networks
  are the segmenters, not failed classifiers); no RANO anywhere.
- 10-27 abstract must be one narrative with a punchline, not an inventory.
- 10-28 "the 100 words that drive the impact"; figures/tables next to first mention; no "see Supplementary"
  red placeholders; example report looks like a standard clinical report (serif, black/grey, drawn strip, never a
  patient image).
- 11-01 supervisor: be clear on contributions; Introduction ends with four numbered contributions (overrides
  section 9); explain how PRISM differs from a chat model; explain the name (a prism splits a score into its
  evidence); illustrative figures, not box flowcharts.
- 11-01 author: state each contribution against its nearest precedent, by name; claim combinations and measurements,
  not components; field terms (covariate-specific AUC, incorporation bias, late fusion, deterministic check); no
  "first"/"novel". Short title (~12 words), clinician's question first, no system name, no "language model".
  MU-Glioma-Post is "the public development cohort", never "the development centre".

### D2.4 Council rounds 1-5 (2026-10-26, overnight under the author's authorisation)

Reviewers only wrote reviews; an editor applied them under a coordinator's rulings. LOCKED.md never edited. All
rulings "pending author" (OUTLINE decisions 15-19). Revert: `git diff backup-before-council-2026-10-26 -- paper/main.tex`.

| Round | Reviews | Editor | Key rulings |
|---|---|---|---|
| 1 | cold+hostile 0995568, show/hide+integrity 4d66592, tone 785d4b7 | dcfd00a (106/159 items) | UCSF gets both planned image models (0.80 single scan; 0.73 with change); claim transfer not best performance; coverage "on point estimates"; faithfulness always "after one revision" |
| 2 | show/hide e8941f6, tone 60d56a3, numbers 7f2489c | ed1b3cd (92/114) | card claim = distribution by cohort; MU age 62.5; `\todo{Supplementary section}` pointers; 3,898 words |
| 3 | cold e07d306, reviewer 2 db1d6c8, voice ec83502; exploratory analyses ac4d9ae | 18d7861 | abstract opens on the clinical reason; narrower coverage/agreement/card/report claims; dagger for exploratory; no volumetric response-rule baseline (no RANO); ET volume alone as simple reference |
| 4 | integrity 823aea6, trim 4e77e51 | 4dc208e | "transfer" = ranking; calibration and MU threshold do not carry over (UCSF O/E 0.72, MU-median threshold calls 90% positive); coverage "on average", short for one outcome externally; agreement rule with MU-fixed medians; one-sentence Conclusion |
| 5 | fresh editor bf8f50a, audit 9e2fa0c, 996705c | 06bccb1, 9a30030 | nine wrong claims fixed; 3,946 words; council summary; title/name settled (later superseded 11-01) |

### D2.5 Overnight 10-28 proposals (`OVERNIGHT_PROPOSALS.md`)

| # | Item | Status 11-01 |
|---|---|---|
| P1 | Abstract "bait and switch": lead with the finding | Applied in 7c6b383 / b3cf90c as a proposal; author approval of abstract pending |
| P2 | Should the report say which evidence carried the score (cohort-level sentence)? | Open (design change) |
| P3 | Table of scans/patients per analysis | Open (cohort flow exists `docs/manuscript/cohort_flow.png`) |
| P4 | Figure 5B three 100% bars | Done: now the report-model ladder |
| P5 | Move the report earlier | Partly (Figure 1 illustrates; 5A plain report) |
| P6 | Reports use each cohort's own medians, text claimed MU-fixed | Done in text (2.1, 3.4, Fig 4B, Table 3 note); regenerating reports with MU-fixed medians not done |
| P7 | Table naming every score | Done (Table 1) |
| P8 | MU age 62.5 vs 62 | Open |
| P9/Tikhonov | Tikhonov 2025 (arXiv:2509.06511) unverified, not in refs.bib; `\todo` in Discussion line ~507 | Open |
| P10 | Label caveat in the Conclusion | Partly carried |
| P11 | Flag results as a grid | Partly |
| P12 | Supplement stale (M2.x refs, v1/v2 framing in S7/S21, no UCSF/system/v3.1 results) | Open, separate reconciliation pass |

### D2.6 Title history

1. 10-26 (author) "PRISM: a modular system for glioma progression surveillance on MRI" (9446e40).
2. 11-01 (7c6b383) "Which evidence carries a glioma progression score? PRISM separates image and treatment evidence
   on surveillance MRI": author judged it a mouthful.
3. 11-01 title council (4 personas, shortlist of 5): adopted, pending author approval, "Timing or tumour? The
   evidence behind glioma progression scores on post-treatment MRI" (`paper/macros.tex` `\papertitle`). Cautions:
   "pseudoprogression" would promise pathology labels; "shifts between centres" is only two centres.

### D2.7 Prior-art pass 2026-11-01 (`docs/literature/PRIOR_ART_2026-11-01.md`)

Three adversarial agents, focused web search (not systematic). All four contributions PARTIAL:
- C1 finding: timing as top feature (Gomaa 2025), scan interval as dataset signal on LUMIERE (TRACE/Tarek 2026),
  timepoint-specific evaluation (Guo & Mirzaei 2025), process variables explain image skill (Badgeley 2019), within-
  stratum evaluation (Janes & Pepe 2008; Oakden-Rayner 2020), incorporation bias (Worster 2008; Kohn 2013) = the
  classical name for the UCSF result. Ours: the measurement within phases and across externally tested centres.
- C2 system: Jabal 2026 nearest; TumorBoard 2026 (provenance + per-claim confidence); Boehm 2022 (late fusion);
  Habas 2007 / Angelopoulos 2024 (per-case reliability).
- C3 external tests: CLARITY 2026 already moved an MU model to UCSF (for survival).
- C4 reports: BTReport (Heras Rivera 2026), Valerio 2025 (segmentation -> JSON -> open LLMs), Zeba 2026 (numeric
  fact-checking).
All "must cite" items listed in the doc are now in `paper/refs.bib` (checked by grep 11-01) except Tikhonov.

### D2.8 Target journal

CMBBE: Imaging & Visualization (Taylor & Francis), chosen 10-15 against two dormant/low-indexed alternatives
(`DRAFT_NOTES.md` "Target journal"). `JOURNAL_RULES.md`: sections A-B from the live page pasted by the user 10-16
(T&F blocks automated access); section C from a 2022 snapshot (abstract unstructured 100-150 words, <= 3 keywords,
British -ise spelling, Interact LaTeX class, CSE name-year `tfcse.bst`, single-anonymous, APC US$2,630). Figures:
1200 dpi line / 600 grey / 300 colour; submission wants TIFF/EPS. Submission checklist in section D.

### D2.9 Paper build and figures

- Source of truth: `paper/main.tex`, `paper/supplement.tex`, `paper/macros.tex` (shared preamble, `\papertitle`,
  `\todo`/`\flag` red placeholders, `\graphicspath{{../docs/manuscript/figures/}}`, line numbers on), `paper/refs.bib`.
- Build: `paper/build.sh` (tectonic at `~/.local/opt/texenv/bin/tectonic`, override `TECTONIC=`); compiles both
  documents into `paper/build/`, copies `main.pdf`, `supplement.pdf` to `paper/`; fails on undefined refs/citations,
  overfull boxes > 10pt or BibTeX errors; the only expected BibTeX warning is the CFB-GBM dataset year.
- Figures: `scripts/generate_system_first_figures.py` draws Figures 2-5 (and the shared palette, `schematic_slice`,
  panel/title helpers) from aggregate values typed from NUMBERS.md; no patient data read; Figure 5A is a synthetic
  report. `scripts/fig1_prism.py` draws the illustrated Figure 1 (imports helpers from the former). Outputs
  `docs/manuscript/figures/fig{1..5}_*.pdf/png`; older figures in that directory (fig1_single_split, fig2_split_variance,
  fig3_clinical_vs_radiomics, fig4_phase_of_care, fig5a_*, fig6a_*, fig_study_design, fig_imaging_examples) belong to
  the 10-15/10-21 drafts and are unused by main.tex. Test: `tests/test_system_first_figures.py`.
- main.tex now: about 2.8k words of main text (6,795 words in the file incl. comments/back matter); sections
  Introduction, Methods 2.1-2.3, Results 3.1-3.5, Discussion, one-sentence Conclusion; source comments `% Sources:`
  above paragraphs. Open `\todo`s: Tikhonov citation; Acknowledgements; Disclosure; generative-AI declaration
  (draft, says Claude wrote and ran analysis code); Ethics; Data availability (derived data/DOI, code link/tag);
  Notes on contributors.
- supplement.tex state: last substantive edit 765084a (10-28) but its content dates from 10-15/10-21: sections S1-S23
  incl. "PRISM v1" (S7), report v1 (S19), report v2 (S21), fine-tuned encoder (S22), intended use (S23). It has no
  UCSF, system (coverage/flags/card) or v3.1 results, uses old "M2.x" main-text references and v1/v2 framing. Main
  text still cites S8, S19, S23 by number. Rebuild is pending (P12, COUNCIL_SUMMARY item 9).
- `report/main.tex` is the separate 10-10 technical report (pdflatex); `report/original_prism_report/` is a LaTeX
  remake of `docs/original_prism_report.pdf`. Not the manuscript.
- Backups: `paper/backup/` (skeleton, pre-overnight, pre-loop10), tag `backup-before-council-2026-10-26`.

### D2.10 Open author decisions (as of 2026-11-01)

1. Title "Timing or tumour? ..." (pending approval).
2. Abstract: main.tex finding-first abstract (150 words) vs LOCKED 2026-10-24 abstract; LOCKED.md unchanged until the
   author approves. Earlier open points: no calibration/scope clause; exploratory numbers marked?
3. Council rulings 15-19 and decision 14 (split variance as Methods paragraph + S8/Fig S2 vs a Results section),
   all "pending author".
4. Agreement rule medians (MU-fixed in the text; evaluated reports used each cohort's own medians; regenerate?).
5. Card denominator (54 of 146 intended-use vs 35 of 249 report scans).
6. P2, P3, P8, P10, P11 (D2.5); RANO in a cited LUMIERE paper title.
7. Rejected reviewer items the author may want back (COUNCIL_SUMMARY item 5).
8. Front matter: full name/email/ORCID confirmation, acknowledgements, disclosure, funding, ethics, data availability
   (repository/DOI), code link/tag, biographies, CRediT roles, generative-AI declaration.
9. Two-pathways/ladder framing beyond what is in the text (memory: author weighing, not approved as of 10-22; now in
   the paper as exploratory).
10. UCSF labels (pos_s2_pm30 vs primary negatives) were chosen by Claude; the author may change them.

---

## D3. Infrastructure

### D3.1 Environment

- uv project, Python 3.11 (`.python-version`), lock `uv.lock`, `pyproject.toml` (extras `legacy`, notebook extras).
  `scripts/setup_env.sh [--legacy|--all]` installs uv if needed, `uv sync --frozen`, checks imports and runs tests.
- Run everything as `uv run --frozen --no-sync python -m prism <stage>` from the repo root (wrappers `prism()`/`py()`
  in `scripts/common.sh`, which also `unset VIRTUAL_ENV`, set `PYTHONPATH=$REPO`, `PRISM_DATA/MU/LUMIERE/OUTPUTS`,
  `BLAS_THREADS=4`).
- Do not `uv sync` the shared `.venv`. uv sync is exact: without `--legacy` it strips the legacy packages the shared
  env now holds (torch 2.14.0+cu130, MONAI 1.6.1, LightGBM); a known drift (scipy 1.17.1 installed vs 1.18.1 in the
  lock) is recorded in analysis manifests (`AUDIT_SYSTEM.md`) and frozen report runs record their environment.
  For a different env use `UV_PROJECT_ENVIRONMENT=<dir> uv sync --frozen --extra legacy` (as `DL_COMPARISON_DESIGN.md`
  did). One-off packages: `uv run --frozen --no-sync --with xgboost ...`.
- LLM env (separate, Python 3.12): `/project/community/sbandred/envs/prism-llm` with vLLM 0.31.0
  (`scripts/12_report_agent.sh` header gives the build line; `PRISM_LLM_ENV` overrides). Runner
  `prism/report/vllm_run.py`: offline (`HF_HUB_OFFLINE=1`), bf16, greedy temperature 0, seed 0, structured outputs
  (JSON schema or regex), `--gpu-mem`, `--max-num-seqs` (<= hybrid-attention state blocks; Qwen3.5-35B-A3B needed 128),
  `--tp`. Models used: Qwen3.8-27B (primary v3.1), gemma-4-31B-it, Qwen3.5-9B/4B/2B ladder, Qwen3.5-35B-A3B (FP8 entry
  exploratory). HF cache `HF_HOME=/project/community/sbandred/cache/huggingface` (set in `~/.bashrc`); other caches under
  `/project/community/sbandred/cache`.
- LaTeX: tectonic `~/.local/opt/texenv/bin/tectonic`, pandoc alongside.

### D3.2 Cluster workflow (memory `cluster-workflow.md`, `ucsf-external.md`)

- Claude may run on the login node (orchard-login-001) or a compute node (this session: orchard-community-4). The
  user holds interactive Slurm allocations named "FLARE" (e.g. 155346 on 10-08, 4x H100, 104 CPUs; 160994 on 10-24/25
  with 26 CPUs + 1 GPU; on 11-01 `squeue` shows 163973 advanced on orchard-community-4 and 164020 general on
  orchard-community-3). Job ids change: always `squeue -u $USER`.
- Run work with `srun --jobid=<id> --overlap -N1 -n1 --cpus-per-task=<= free CPUs> <cmd>`; asking for more CPUs than
  free blocks. With env vars, set them before srun and pass `--export=ALL` (`env` as the srun command fails).
- No heavy jobs on the login node. Never `pkill -f <pattern>` where the pattern is in the same command line (killed
  the calling shell once, an edit was lost).
- One GPU per job (`CUDA_VISIBLE_DEVICES=0`) unless tensor-parallel; report runs on 4 GPUs take ~15 min (v1).
- `slurm-*.out` in the repo root (157490 ... 163973, 10-16 to 11-01) are empty interactive-allocation logs; ignored by git.
- `submit.sh` (untracked, repo root): user's generic sbatch/interactive helper for the A3 Mega H100 cluster
  (`--script`, `-p advanced|preempt|general`, `-t`, `-n`, `-N`). Stays uncommitted.
- Network: TCIA Aspera blocked (ports 33001/443 to the faspex host; 8443 returns 502); plain HTTPS to TCIA works
  (`docs/literature/DATASETS.md`).

### D3.3 Data locations (paths only)

| Data | Location |
|---|---|
| MU-Glioma-Post images + clinical workbook (July 2025) + segmentation volumes table | `data/mu-glioma-post/` (`data/` is git-ignored) |
| Original PRISM processed features (HF `sbandred/mu-glioma-post-processed`) | `data/mu-reference-processed/` |
| LUMIERE (CSVs, `Imaging-v202211.zip`, extracted DeepBraTumIA `imaging/`) | `/project/community/sbandred/lumiere` (symlink `data/lumiere`) |
| UCSF-ALPTDG (images and the original zip) | `/project/community/sbandred/ucsf/` - do not delete the zip without asking |
| CFB-GBM clinical/feature tables, UCSD-PTGBM sources | `data/cfb-gbm/`, `data/ucsd-ptgbm/` |
| Public reference reports (report v2 style) | `data/public_reports/` |
| Segmentation/encoder weights (BraTS21 SwinUNETR fold 1, BrainSegFounder) | `data/weights/` |
| Everything the pipeline writes (features, results, logs, LLM outputs, UCSF crop cache 7.6 GB) | `outputs/` (git-ignored); `outputs/results_pre_fix_2026-10-11` is the pre-fix snapshot |
| Golden outputs snapshot | `/project/community/sbandred/prism-golden-outputs-20261009` |
| Legacy code and its large artefacts | `legacy/` (embeddings, runs, pretrained weights git-ignored) |
| Original report PDF | `docs/original_prism_report.pdf` |

MU mask labels: 1 NETC, 2 SNFH, 3 ET, 4 RC (`prism/config.py`); the legacy `radiomics_tools/metrics/constants.py`
LABEL_MAP is wrong. LUMIERE has no cavity label (cavity is "necrosis"). BraTS channel order flair,t1ce,t1,t2 =
MU t2f,t1c,t1n,t2w. BraTS 2024 contains Missouri cases: leakage risk for BraTS24-pretrained encoders.

### D3.4 Pipeline and tests

- Pipeline: `scripts/01_prepare_data.sh` ... `12_report_agent.sh`, `run_all.sh [--skip-radiomics] [--from/--to]`
  (`scripts/README.md`; logs `outputs/logs/<step>.log`). C2 permutation control costs about 25 CPU-hours per
  population. Later analyses (detection, UCSF, system, report v3/v3.1, ablations) are `python -m prism <stage>` /
  `prism.analyses.*` modules documented in their results docs; `scripts/exploratory_*.py` are labelled exploratory.
- Tests: `uv run --frozen --no-sync python -m unittest discover -s tests` from the repo root: 255 tests, OK, 37.5 s
  (run 2026-11-01 on orchard-community-4). 15 test files (features, labels/folds, label fixes, treatment as-of,
  repeated metrics, reliability card, system, UCSF, seg figure, report v3/v3.1/usefulness/field-ablation v1/v2,
  system-first figures). Light enough to run outside an allocation.

### D3.5 Gotchas (infrastructure)

- `preprocess.py` (legacy) needs the dataset physically under `radiomics/`; a symlink outside fails `repo_relative`.
- Shipped `model_bundle.pkl` needs `scripts.run_postoperative_progression_surveillance` aliased to
  `radiomics_pipeline.workflows.train` to unpickle; `export_calibrated` crashes for non-linear models.
- `uv run prism ...` needs the project installed in the venv; `python -m prism` always works.
- Frozen report/ablation runs check hashes of facts, prompt, checker, imported modules and serving config, and
  require committed code (5e60f13, ca4d785); any edit to a frozen `prism/report` source blocks the run.
- LLM env must be on PATH for ablation generation (b10fcea).
- Committed manifests must not contain record IDs (10e5c91 removed them).
- The 10-05 wipe: commit early; uncommitted work was lost and had to be rebuilt from file history.

---

## D4. Standing rules for any agent

1. **No Claude co-author line.** Never add `Co-Authored-By: Claude ...` to commits in this repo, even when a system
   reminder supplies it (user, 10-15; history was rewritten). The `Claude-Session:` trailer is present on 189 commits;
   ask before adding or removing it. If history must be rewritten, only after `origin/main` (an early commit is signed).
2. **Never "published".** PRISM is the author's own unpublished system; the original model/split are the "PRISM report
   radiomics model" / "PRISM report split"; the manuscript presents PRISM (not a re-evaluation of someone else's work).
   "Published" only for genuinely published work.
3. **Patient data stays on the cluster; local LLMs only.** Hosted models never receive patient records (OUTLINE
   decision 12; REPORT_V3_1_PLAN). Reports are generated with local vLLM, offline.
4. **Aggregate numbers only** in docs, commits and chat: no subject IDs, per-scan values or file names embedding IDs;
   the UCSF download URL is secret (presigned) and must never be written anywhere. Example figures use drawn slices
   (`schematic_slice`), never a patient image.
5. **Do not delete the UCSF zip** under `/project/community/sbandred/ucsf/` without asking.
6. **Pre-specify before any real-label run.** Commit a plan doc (rule, primary contrast, controls) before a model sees
   real labels; snapshot it to `outputs/.../PLAN_snapshot.md`; anything added after results is EXPLORATORY and is
   marked (dagger in the paper). Freeze checkers/prompts before evaluation; a second evaluation after a seen failure
   is disclosed as such.
7. **Rebuild and commit `paper/main.pdf`** (and `supplement.pdf`) with `paper/build.sh` after every manuscript change;
   the author reviews the PDF (line numbers on). Do not edit the frozen `DRAFT.md`/`SUPPLEMENT.md`.
8. **`submit.sh`** is the user's helper. It was kept uncommitted until 2026-11-02, when the user committed it on `main`.
9. **LOCKED text needs approval.** Passages in `LOCKED.md` are not changed, not even for polish; if a result makes one
   wrong, flag it and propose the smallest edit. Proposals sit beside the locked text, flagged.
10. **Writing method.** For any work on `paper/*.tex` load the `paper-writing` skill (reads LOCKED.md and STORY.md
    first), follow `STYLE.md` and record each new author reaction as a dated rule in STYLE section 10; work in layers
    (outline -> first sentences -> prose -> polish) and get the author's reaction at each; held-back results go to
    `RESERVE.md`; the "always in the main text" list (intended-use 0.60, timing baseline, within-phase results,
    planned vs exploratory labels, scope limits, no clinician has read the reports) is never withheld.
11. **Paper scope.** One story about the final system; no v1/v2 history; no RANO; no triage results unless asked
    (separate paper); Rai 2026 ignored; claims "moderate": transport means ranking, not calibration; no "first",
    "novel", deployment or clinical-benefit claims.
12. **Agents' outputs:** when sub-agents were told not to commit, the coordinator commits their outputs (UCSF night).
13. **Cluster etiquette:** heavy work via `srun --overlap` into the user's allocation, never on the login node.

---

## D5. What is pending now (2026-11-01)

- **2026-11-02 machine reset:** `data/`, `outputs/`, `/project/community/sbandred/{lumiere,ucsf,prism-golden-outputs-20261009,envs/prism-llm}`, `.venv` and the local LLM weights are gone. Git history is intact. Re-download the data (MU from the HF mirror, LUMIERE from its public release, UCSF with a fresh link from the author), rebuild the environments, and rerun the pipelines before any result is regenerated.

- Author approvals: title, finding-first abstract (vs LOCKED 2026-10-24), council rulings, decisions in D2.10.
- Supplement rebuild (P12): remove v1/v2 framing (S7, S19, S21), add UCSF, system (coverage by outcome, flags under
  both median rules, card, calibration/thresholds, Brier by tier), deep networks at MU/UCSF, report v3.1 revision and
  model ladder, deviations from plans; fix M2.x references and renumber; then cite by real section number.
- Tikhonov 2025 reference: verify or cut.
- Front matter and declarations; data/code release decision (repository, DOI, tag); figures exported to TIFF/EPS at
  journal resolution before submission; cover letter; recheck live T&F instructions.
- Possible new runs if the author wants: regenerate reports with MU-fixed medians (P6); report-without-model
  ablation was done (v2 406/406) but a clinician reader study is future work; Burdenko-GBM-Progression (dbGaP, PI-level
  request) and UCSD-PTGBM as follow-up cohorts.
- `docs/CURRENT_STATE_AND_NEXT_STEPS.md` (09-14) and `docs/ACTION_ITEMS.md` (09-26) are historical; they do not
  describe the current state and should not be used as a to-do list. The current state is in OUTLINE.md (top
  section), COUNCIL_SUMMARY.md, OVERNIGHT_PROPOSALS.md and this work log.


---

