# NUMBERS: verified fact sheet for the prose layer

Built 2026-10-26 from `paper/main.tex` (skeleton), `STORY.md`, `OUTLINE.md`, `TABLE1_COHORT.md` and `docs/results/*.md`,
and spot-checked against the CSVs under `outputs/results/analyses/` (read-only). Aggregate numbers only; no patient IDs.

**How to read.** Every row gives the value, the 95% CI where one exists, the population (positives / negatives / patients,
or scans), the exact source (file, section or table) and the status.
- **PLANNED** = the rule or model was written down before the run (plan commit named where it exists).
- **EXPLORATORY** = chosen or added after results were seen (post hoc). The text must say so wherever it appears.
- **DESCRIPTIVE / DIAGNOSTIC** = reported without a decision rule.
- "CSV-checked" = the value was re-read from the CSV and matches the doc.
- Set shorthand: **MU-IU** = MU grade 4, intended use, primary negatives = 62 / 84 / 80 patients (146 scans).
  **UCSF-P** = UCSF grade 4, scan 2, `pos_s2_pm30` vs primary negatives = 29 / 40 / 69 patients.
  **LUM** = LUMIERE detection set = 73 / 105 / 79 patients (178 scans).
- Plans: UCSF `0e7c9fe`; system `e7cba80`; report v3.1 `4f7e7b9`; reduced confidence (exploratory) `3d20c41`;
  Christodoulou source check (exploratory) `9810dc4`. All five exist in `git log`.

---

## Mismatches (skeleton / STORY / OUTLINE vs sources)

Ordered by how much they could change a sentence. "Fix" is a suggestion for the prose layer, not an edit made.

1. **"About as high as models trained there" holds for single-scan images, not for the planned comparison.**
   Skeleton 3.2 and the abstract compare locked single-scan images (A-Iscan 0.795) with UCSF-trained single-scan images
   (Iscan 0.826): B minus A = +0.031 (-0.052 to +0.116). That is true. But the plan's Q3 uses A-Ipure vs Ipure, and there
   training on UCSF is clearly higher: 0.863 vs 0.726, B - A = +0.137 (+0.033 to +0.257) (UCSF_RESULTS.md, Q3). The system's
   UCSF image pathway (cards, conformal sets, Fig 2 "images") is A-Ipure 0.726, not A-Iscan 0.795. The MU counterpart of
   the 0.80 is I_scan 0.659 (MU-IU), not I_pure 0.709. Fix: name the model each time (single-scan images), say once that
   the change inputs did not transport (A-Ipure - A-Iscan = -0.069, -0.126 to -0.014), and keep Fig 2's "images" column on
   one definition.
2. **"Combined" has two meanings on MU.** STORY Step 2 gives combined 0.84 (0.76-0.90) and "images add +0.015 (-0.03 to +0.06)";
   that is the planned model **P** (0.837, 0.763-0.904; P - B1 +0.015, -0.032 to +0.063). The skeleton, OUTLINE and the system
   use **B1 + I_pure** = 0.821 (0.744-0.894) (rounds to 0.82), and B1 + I_pure - B1 = -0.001 (-0.052 to +0.046). Skeleton 3.1
   "combined 0.82" is right for the system's combined score. Do not mix "+0.015" with it. P also contains timing inputs in
   its image block (see the ladder).
3. **LUMIERE images alone: 0.66 in skeleton and STORY, 0.65 in the sources.** Exact value 0.6545 (0.5646-0.7332)
   (system/checks.csv; RELIABILITY_CARD.md already notes the rounding). STORY's CI "0.57-0.73" should read 0.56-0.73.
   Use 0.65.
4. **"Wrong about half the time vs a quarter otherwise, in all three cohorts" is not true for UCSF.** Reduced rule D4
   (EXPLORATORY): flagged / unflagged error = MU 0.52 / 0.22, LUMIERE 0.54 / 0.22, **UCSF 0.38 / 0.25**. The difference
   (flagged - unflagged) is MU +0.30 (+0.17 to +0.43), LUMIERE +0.33 (+0.13 to +0.48), **UCSF +0.13 (-0.13 to +0.40)**, so on UCSF
   the CI includes 0 (SYSTEM_RESULTS.md, EXPLORATORY section). Fix: "about half on MU and LUMIERE, 0.38 on UCSF".
5. **S2 +0.31 and S3 +0.08 are for the disagreement flag alone, on MU only.** The plan's S2 reads "the system's flags", with each
   flag also reported alone. The "any flag" rule marks 91% of MU scans and fails S2 (-0.170, -0.503 to +0.147). Disagreement
   alone: LUMIERE S2 +0.105 (-0.049 to +0.266) not met; UCSF S2 -0.019 (-0.218 to +0.175) not met. Skeleton 3.4 mentions only
   UCSF; LUMIERE also fails for disagreement (conformal {0,1} is the only single flag that passes S2 on LUMIERE).
   Also, S3 compares with a *phase-composition-matched* removal on MU and UCSF (plain random removal on LUMIERE, which has one
   stratum), not with plain random removal; the skeleton's "the same number at random" should say matched.
6. **Segmentation source.** Skeleton 2.1 says "BraTS21 SwinUNETR (MU, LUMIERE: the cohorts' own masks or resegmentation; UCSF:
   provided masks)". In the system, the measurements come from the **cohorts' own masks**: MU BraTS-style masks, LUMIERE
   DeepBraTumIA atlas masks (3 labels, no separate cavity), UCSF provided seg files (SEG_FIGURE.md; UCSF_IMAGING.md;
   SYSTEM_RESULTS.md section "Deviations", item 1). The BraTS21 SwinUNETR re-segmentation of MU (RESEGMENTATION.md) was a
   pre-specified sensitivity analysis that did **not** help (primary detection AUC 0.681 -> 0.665, delta -0.016, -0.057 to
   +0.025; ET Dice vs MU masks median 0.80 [IQR 0.49-0.91]) and downstream analyses were not rebuilt. SwinUNETR enters only
   as the fine-tuned deep-network arms. "A deep segmentation network supplies these measurements" needs rewording.
7. **Table 1 population counts depend on the task.** TABLE1_COHORT.md is the 120-day index-scan cohort (MU grade 4: 126 patients,
   249 scans; LUMIERE 61 patients, 132 scans) and has **no UCSF column**. The detection task uses different rows: MU grade 4
   64 positive / 117 primary-negative scans (92 patients) in all scans, 62 / 84 (80 patients) in the intended use (or 62 / 173 with
   secondary negatives, 88 patients); LUMIERE 73 / 105 scans in **79 patients** (not 61, because the first PD scan counts);
   UCSF-P 29 / 40 in 69 patients of 140 grade-4 patients. 47 MU progression scans (47 patients, 42 grade 4) were excluded because
   their patients have no index scan. Table 1 must state which rows each count describes (see section 2.2 below).
8. **Ladder step 2 (+ change) has no verified CI.** STORY cites "0.71 (+0.05, -0.00 to +0.11)" from DETECTION_TASK.md, but the CI is
   not in that file, and `scripts/exploratory_pure_imaging_detection.py` prints it without saving it. Point values are verified
   (0.659, 0.709; difference +0.050). Step 3 is verified through I - I_pure = +0.097 (+0.047 to +0.153) (0.806 vs 0.709). Do not
   write "each step raised its AUC" with a CI-based claim for the middle step; STORY's own CI includes 0.
9. **Report numbers have two evaluations.** STORY's "full system" table is v3 (LUMIERE 0/178, UCSF 140/140, perturbations 29/30);
   the skeleton uses v3.1 (162/162, 130/130, 28/30). Both are right for their evaluation. The sets differ (v3.1 holds out 10
   LUMIERE and 10 UCSF development patients). OUTLINE still says "v3.1 numbers pending"; stale. v3 stays reported as 0/178 and
   the disclosure sentence is needed.
10. **"Smaller models left required content out" is only partly right.** Below 27B the dominant failure is missing content (4B: 93
    reports; 9B: 37; gemma-E4B: 132). But the 2B model also has 71 unsupported numbers, 62 invalid citations, 24 truncated outputs and
    15 forbidden-wording reports; gemma-E4B fails mostly on conformal / agreement statements (224); and a larger model (Qwen3.5-35B-A3B)
    also misses S5 on MU (97/114, 17 reports omit the combined 80% set). Fix: "mostly left required content out rather than
    invent it; the 2B model also invented".
11. **Split-variance comparison in STORY Step 1 mixes designs.** "No-image model 0.72 under repeated CV vs 0.87 on the first split" compares
    the C3 5 x 5 IPCW figure with the seed-62 naive AUC. Over the 500 design splits the same baseline averages **0.801 +/- 0.052** (naive)
    and 0.769 (IPCW); seed 62 ranks at the 91st percentile (SPLIT_VARIANCE.md). The skeleton's "0.80 vs 0.72" is correct but is about the
    **initial radiomics pipeline** (shipped 0.802; re-selected per split mean 0.720, rank 92%), not the current PRISM models.
12. **No source for LUMIERE "clinical alone".** Skeleton 3.2 ("clinical alone at chance in all cohorts") and Fig 2 need a locked
    clinical-only AUC on LUMIERE. None exists in any doc or CSV (only univariable inputs: age 0.535, IDH mutant 0.459, MGMT methylated 0.415;
    `detection/lumiere_single_feature_auc.csv`). Available: MU 0.530 (0.450-0.606); UCSF-P locked 0.502 (0.364-0.630). It has to be run
    before Fig 2 is drawn, or the LUMIERE cell left out.
13. **"Conformal sets kept their coverage at all three centres"** (abstract, 3.4) is true for the **combined** score at the point
    estimate. UCSF 0.783 has CI 0.681-0.870 (lower bound below 0.78); LUMIERE images (0.708) and UCSF timeline (0.696) are below
    target; conditional coverage fails in several cells (SYSTEM_RESULTS.md S1). Say "combined".
14. **Smaller items.**
    - UCSF log-ET AUC CI: 0.878 (0.790-0.946) in UCSF_AUDIT.md vs (0.791-0.949) in UCSF_RESULTS.md Part C (different bootstrap
      sets); pick one and cite it.
    - UCSF-trained Iscan: 0.826 (Part B, mean of repeats) vs 0.831 (audit, scores averaged over repeats). Use Part B.
    - STORY "9 deep arms: image-only 0.45-0.57": the 8 detection arms span 0.447-0.570; the 9th (G5, forward label) is 0.575.
    - The card's "tested cell holds 54 of 181" (RELIABILITY_CARD.md) and S4's 54 + 92 = 146 differ only in the set (all scans vs
      intended use); the tested cell is the same 54 scans (38 / 16).
    - "35 of 249 MU scans" uses all 249 grade-4 index scans that have reports (tested 35, few cases 212, not tested 2), a different
      denominator from the detection evaluation sets.
    - The whole reliability card is **EXPLORATORY (post hoc)**: situations, tier rule and agreement rule were defined after the MU,
      LUMIERE and UCSF results were seen, although S4 (tiers) is in the plan.
    - UCSF_AUDIT.md uses the word RANO in its own text; the paper does not (decision 3).

---

## 1. Abstract (proposed text in main.tex; every number)

| Claim in text | Value (CI) | Population | Source | Status |
|---|---|---|---|---|
| Timeline pathway, MU | 0.822 (0.749-0.902) | MU-IU, B1 | DETECTION_TASK.md, Primary table; CSV-checked | PLANNED (B1 is the baseline) |
| Image pathway, MU | 0.709 (0.630-0.781) | MU-IU, I_pure | DETECTION_TASK.md, EXPLORATORY "how much of imaging only"; system/checks.csv | EXPLORATORY model; used in the planned system |
| Combined, MU (0.82) | 0.821 (0.744-0.894) | MU-IU, B1 + I_pure | DETECTION_TASK.md same table; system/checks.csv 0.8205 | EXPLORATORY model |
| LUMIERE, locked (0.77) | 0.773 (0.679-0.857) | LUM, T, grade-4 trained | DETECTION_TASK.md, External test; lumiere.csv | PLANNED |
| UCSF single-scan images (0.80) | 0.795 (0.686-0.887) | UCSF-P, A-Iscan | UCSF_RESULTS.md Part A primary; locked/auc.csv | PLANNED arm (primary question was A-Ipure) |
| "About as high as models trained there" | 0.826 (0.729-0.909) trained; B - A +0.031 (-0.052 to +0.116) | UCSF-P, Iscan | UCSF_RESULTS.md Part B and Q3 | EXPLORATORY contrast for Iscan (Q3 was planned for Ipure only); see Mismatch 1 |
| Audit: treatment timeline at MU | +0.114 (+0.035 to +0.196) overall; -0.016 (-0.134 to +0.109) within phase | MU-IU, B1 + I_pure vs clinical + I_pure | DETECTION_TASK.md, EXPLORATORY images + clinical | EXPLORATORY |
| Audit: enhancing volume at UCSF | 0.878 (0.790-0.946); 27 of 29 progression scans rated "ET Increased" | UCSF-P | UCSF_AUDIT.md sections 4 and 6 | EXPLORATORY |
| Conformal coverage, three centres | 0.823 / 0.871 / 0.783 | combined, alpha 0.2 | SYSTEM_RESULTS.md S1 | PLANNED (S1) |
| Reports passed the check | 114/114, 162/162, 130/130 | v3.1 | REPORT_V3_1.md | PLANNED rule; second evaluation after a seen failure |

---

## 2. Methods

### 2.1 PRISM (modules)

| Item | Value | Source | Status |
|---|---|---|---|
| Timeline inputs on MU (B1) | age, sex, IDH, MGMT (no unknown indicators, markers masked before diagnosis); days since diagnosis and surgery; RT start/end/dose; chemotherapy; visit index; previous scans. Ridge, patient-grouped | DETECTION_TASK.md Plan; DETECTION_TASK.md Primary | PLANNED |
| Transportable timeline (Tbase / T) | age, sex, IDH, MGMT; log days since surgery; early post-RT flag (LUMIERE: the rater's "LessThan3Months"; UCSF: approximated as 42-125 d after the RT start); T adds harmonised volumes (ET, necrosis + cavity, oedema), log ratios to the previous scan, log days since the previous scan, has-previous | DETECTION_TASK.md External test; UCSF_RESULTS.md deviation 3 | PLANNED (T); Tbase EXPLORATORY reference |
| Image pathway on MU (I_pure) | 6 log volumes + 13 morphology / relative-intensity features + log ratios of 6 volumes to the previous scan + ET and lesion ratio to the smallest volume over the whole history; 27 inputs; no days, no flags | UCSF_IMAGING.md; SPLIT_VARIANCE.md (27 inputs) | EXPLORATORY definition |
| Single-scan image model (I_scan) | 19 inputs (volumes + morphology / intensity) | SPLIT_VARIANCE.md | EXPLORATORY definition |
| Image pathway on LUMIERE (T_img) | log ET, log necrosis + cavity, log oedema, log ratios of the same to the previous scan; at the 10 scans with no previous scan, a locked 3-volume MU model | SYSTEM_RESULTS.md Deviations item 1 | council decision, before evaluation |
| Image pathway on UCSF | A-Ipure (history truncated to one previous scan: scan 1) | UCSF_IMAGING.md; SYSTEM_PLAN.md section 1 | PLANNED |
| Segmentation source | MU: cohort masks (BraTS-style); LUMIERE: DeepBraTumIA atlas masks (182 x 218 x 182, 3 labels); UCSF: provided seg files (240 x 240 x 155) | SEG_FIGURE.md; UCSF_IMAGING.md | see Mismatch 6 |
| Conformal method | patient-level split conformal; alpha 0.2 (headline) and 0.1; MU: inside each outer training fold, a 70 / 30 patient split (conformal seed 10 x repeat + fold); external: one MU-calibrated model (MU patient split 70 / 30, seed 0) applied once | SYSTEM_PLAN.md section 2; SYSTEM_RESULTS.md Specification | PLANNED |
| Pathway agreement rule | both scores on the same side of that pathway's median over the cohort's evaluation set (per repeat on MU); scores only, no labels | RELIABILITY_CARD.md Pathway agreement | EXPLORATORY (post hoc) |
| Reliability card tiers | tested = >= 10 progression AND >= 10 non-progression scans in the exact cell (AUC + 95% CI shown); few cases = at least one scan, fewer than 10 of either class (counts only); not tested = none | RELIABILITY_CARD.md Tier rule | EXPLORATORY (post hoc) |
| Card situations | phase of care (before RT end / early post-RT <= 84 d / later post-RT > 84 d / unknown) x enhancement (ET absent < 0.1 cc / no previous / ET not increased / ET increased [>= 1 cc and >= 40%, or >= 1 cc new from ~0] / unknown) | RELIABILITY_CARD.md Situations | EXPLORATORY (post hoc) |
| Report model | Qwen3.8-27B (revision 1d4bf0f2...), bf16, one H100, vLLM 0.31.0, greedy (temperature 0), seed 0, non-thinking, structured JSON, offline; prompt v3.4 frozen 2026-10-26T00:39:20Z; checker blob 26d6637a... frozen 2026-10-25T22:43:43Z | REPORT_V3.md Design; REPORT_V3_1.md Rules | PLANNED |
| Checker | numbers (number words count as unsupported), flags, conformal phrases, agreement, required content, forbidden wording (diagnosis, advice / decision, probability words), card rule | REPORT_V3.md Checker v3 | PLANNED, frozen before evaluation |

### 2.2 Cohorts and the task (Table 1 inputs)

**Detection label (MU).** Positive = the progression scan (first MRI with a mask on or after the documented progression date).
Negative (primary) = index scan with a verified 120-day non-event (`label_120 == 0`); secondary negatives = all index scans before
progression. Primary evaluation set = scans on or after the documented RT start (the intended use). Source: DETECTION_TASK.md Plan.

**MU-Glioma-Post detection rows** (DETECTION_TASK.md Cohort; `outputs/data/detection_cohort_README.md`; CSV-checked). PLANNED.

| population | set | positives | primary negatives | secondary negatives | patients (primary set) |
|---|---|---|---|---|---|
| grade 4 | all scans | 64 | 117 | 249 | 92 (126 with secondary negatives) |
| **grade 4** | **intended use** | **62** | **84** | 173 | **80** (88 with secondary negatives) |
| grade 4 | pre-RT | 2 | 33 | 76 | 50 |
| all gliomas | all scans | 73 | 156 | 308 | 114 (155) |
| all gliomas | intended use | 64 | 98 | 193 | 87 (97) |

- 120 progression scans have complete sequences and a mask; 47 (from 47 patients, 42 grade 4) belong to patients with no index scan and are
  excluded.
- Grade-4 MU-IU by phase (positives / negatives): during RT 2 / 1, early post-RT 4 / 51, later post-RT 56 / 32. Source: DETECTION_TASK.md.
  (The detection_cohort README gives the all-primary-and-secondary counts by phase: early post-RT 4 / 98, later post-RT 56 / 69.)
- 56 of 62 progression scans are later post-RT; 51 of 84 primary negatives are early post-RT.
- Scans with a previous scan, MU-IU: 62 / 46 (108 scans, 74 patients).

**MU-Glioma-Post cohort (Table 1, `TABLE1_COHORT.md`, identical to `tables/table1.md`; 120-day index-scan cohort).**

| | all gliomas | grade 4 |
|---|---|---|
| patients | 155 | 126 |
| index scans | 308 | 249 |
| scans per patient, median (range) | 2 (1-6) | 2 (1-6) |
| age, median [IQR] | 61 [47-69] | 62 [53-70] |
| male | 80 (52%) | 66 (52%) |
| IDH wildtype / mutant / unknown | 120 / 22 / 13 | 112 / 8 / 6 |
| MGMT methylated / unmethylated / unknown | 53 / 73 / 29 | 45 / 62 / 19 |
| RT documented | 102 (66%) | 89 (71%) |
| RT completed by scan day | 185 (60%) | 167 (67%) |
| early post-RT window (0-84 d after RT end) | 104 (34%); unknown 94 | 98 (39%); unknown 65 |
| 120-day label: progression / no progression / censored | 100 / 156 / 52 | 93 / 117 / 39 |

**LUMIERE** (Table 1 = 120-day index-scan cohort; detection = locked set).

| item | value | source |
|---|---|---|
| patients / index scans | 61 / 132 (median 2, range 1-10) | TABLE1_COHORT.md |
| age median [IQR]; male | 62 [53-70]; 32 (52%) | same |
| IDH wildtype / mutant / unknown | 38 / 1 / 22 | same |
| MGMT methylated / unmethylated / unknown | 26 / 28 / 7 | same |
| treatment dates | not recorded; early post-RT window = the rater's "LessThan3Months" flag, 27 (20%) of scans | same |
| field strength 1.5 T / 3 T / other | 81 (61%) / 44 (33%) / 7 | same |
| 120-day label: progression / no / censored | 47 / 76 / 9 | same |
| progression documented after the scan (any time) | 122 (92%) | same |
| **Detection set (positives / negatives / patients)** | **73 / 105 / 79** (178 scans). Positive = first scan rated PD; negatives = earlier scans rated SD, PR or CR; 24 patients contribute only a positive; 15 scans lack a usable DeepBraTumIA segmentation (imputed by the locked pipeline); 168 of 178 have a previous scan | DETECTION_TASK.md External test; PLANNED |
| LUMIERE scans with rater flag "< 3 months after RT" = 0 | 72 positive / 78 negative | DETECTION_TASK.md |
| Report evaluation set (v3.1) | 162 scans, 69 patients (10 of 79 patients and 16 scans held in development) | REPORT_V3_1.md |

**UCSF-ALPTDG** (UCSF_DATA.md; DUA). PLANNED label (UCSF_PLAN.md).

| item | value | source |
|---|---|---|
| patients / scans | 298 patients x 2 scans = 596 scans; one consecutive post-treatment scan pair per patient | UCSF_DATA.md |
| grade 4 / WHO 2021 GBM / all gliomas | 140 / 80 / 298 patients | UCSF_DATA.md |
| age median (grade 4) | 57.5 y (GBM 59.5; all 53) | UCSF_DATA.md |
| male (grade 4) | 81 of 140 | UCSF_DATA.md |
| IDH mutant / wildtype / unknown (grade 4) | 13 / 81 / 46 | UCSF_DATA.md |
| MGMT methylated / unmethylated / unknown (grade 4) | 71 / 43 / 26 | UCSF_DATA.md |
| days diagnosis to scan 1, median (IQR), grade 4 | 424 (228-686); scan 1 to scan 2 median 56 d | UCSF_DATA.md |
| UCSF TRAIN / TEST split (grade 4) | 114 / 26 patients (all gliomas 248 / 50) | UCSF_DATA.md |
| also in UCSF-PDGM | 59 of grade 4 (60 overall) | UCSF_DATA.md |
| primary label | scan 2, progression dated within +/- 30 d of it and nearer scan 2 than scan 1; negatives = progression >= 120 d later or >= 120 d dated follow-up without progression | UCSF_PLAN.md; UCSF_DATA.md |
| **Primary set UCSF-P** | **29 positives / 40 negatives / 69 patients** (grade 4). WHO GBM 21 / 20 / 41. All gliomas 48 / 78 / 126 | UCSF_RESULTS.md Part A; auc.csv CSV-checked |
| all grade-4 scan-2 records (used by the system) | 140 | SYSTEM_RESULTS.md |
| all-scans sensitivity (pos_s2_pm30 + pos_s1_at) | 34 / 103 / 97 patients (grade 4) | UCSF_DATA.md |
| negatives, grade 4, primary | 63 from scan 1 + 40 from scan 2 = 103; verified only 78 (primary scan 2: 33 verified + 7 followed) | UCSF_DATA.md; UCSF_AUDIT.md section 2 |
| phase of care in UCSF-P | 65 of 69 later post-RT (27 positive / 38 negative), 2 early post-RT, 2 RT date unknown. UCSF gives only the first RT start; the phase assumes a 6-week course | UCSF_RESULTS.md reading; UCSF_DATA.md |
| positives dated vs scan 2 | median +7 d (IQR 0 to +11); 9 within +/- 1 d, 19 more than 1 d after (up to +30 d), 1 before | UCSF_AUDIT.md section 3 (EXPLORATORY) |
| MU for contrast: positive scanned on the progression day | 48 of 64 (median gap 0 d) | UCSF_AUDIT.md section 3 |
| UCSF buildable features | no RT end, dose, visit index, nadir; 18 scans with RT given but undated | UCSF_DATA.md "Which PRISM features can be built" |

**Secondary task (one sentence).** 120-day risk from the start of RT, MU grade 4, intended use (173 scans): AUC 0.601 (0.515-0.686), C2 corrected core
model. INTENDED_USE.md line 164; TRIAGE_FEASIBILITY.md line 153; DETECTION_DEEP.md. PLANNED. Forward locked on LUMIERE 0.61 (corrected 0.64): STORY.md only (EXTERNAL_LUMIERE.md not re-read).

### 2.3 Evaluation

| Item | Value | Source | Status |
|---|---|---|---|
| MU cross-validation | 5 x 5 patient-grouped folds (`outputs/data/folds.csv`); AUC = mean over repeats of the pooled held-out AUC; patient-cluster bootstrap, 1,000 paired draws | DETECTION_TASK.md Plan | PLANNED |
| System bootstrap | 1,000 draws, seed 20261026 | SYSTEM_RESULTS.md | PLANNED |
| UCSF bootstrap | 1,000 draws, seed 20261025; UCSF-trained: 5 x 5 StratifiedGroupKFold | UCSF_RESULTS.md Part B | PLANNED |
| Card CI | 2.5-97.5 percentiles of 1,000 patient-cluster draws, seed 20261021 | RELIABILITY_CARD.md | EXPLORATORY |
| Locked training rows | MU grade-4 detection rows (positives + primary negatives, all phases): 181 rows (35% positive); all gliomas 229 rows (32%) | UCSF_RESULTS.md Part A | PLANNED (DEVIATION from "all MU detection scans", reported with the all-glioma sensitivity: 0.768 vs 0.773) |
| **Split variance, MU (first split vs 500)** | initial radiomics pipeline: shipped model 0.802 on the original split; re-selected per split: mean 0.720 +/- 0.055 (2.5-97.5%: 0.610-0.819); seed-62 re-run 0.801 ranks above 92% of splits (94% IPCW); 7.2% of splits reach 0.802. IPCW mean 0.727 +/- 0.058 (475 splits) | SPLIT_VARIANCE.md Results table 1 | PLANNED (plan item 3.5) |
| Same, baseline (clinical + timing + treatment ridge) | 500-split mean 0.801 +/- 0.052 (0.694-0.895); seed 62 = 0.871 (rank 91%); IPCW 0.769 | SPLIT_VARIANCE.md | PLANNED |
| Same, shipped features (optimistic) | 0.815 +/- 0.044; honest minus optimistic 0.095 +/- 0.040 per split | SPLIT_VARIANCE.md | PLANNED |
| Design splits vs random 30-patient splits (baseline) | 0.800 +/- 0.054 (n = 500) vs 0.787 +/- 0.069 (n = 300); the design picks patients with many scans (85.5 vs 59.9 test scans) | SPLIT_VARIANCE.md sensitivity check 2 | verifier check |
| Re-running Optuna | made things worse: -0.064 +/- 0.055; inner CV 0.865 vs test 0.654 | SPLIT_VARIANCE.md sensitivity check 1 | verifier check |
| Split variance, images (EXPLORATORY) | seed 62 naive: I_scan 0.793, I_pure 0.783; 500-split means 0.716 and 0.718 (same spread as the radiomics pipeline); images lose to the baseline in 88% of splits; seed 62 favourable for every model (81-92%) and clinical-only most (99%; 0.791 vs usual 0.647) | SPLIT_VARIANCE.md EXPLORATORY | EXPLORATORY |
| **UCSF own split vs 100 random splits** | UCSF-trained timeline (B-Tl), grade 4, 6 / 10 test: **0.450** (0.143-0.750) vs random median **0.717** (2.5-97.5%: 0.492-0.940); UCSF split at the 1st percentile of random splits; repeated 5 x 5 CV gives 0.669. Images on the same split: Iscan 0.917 (random 0.874), Ipure 0.900 (0.875). One 16-patient split ranges about +/-0.15 (images) and +/-0.25 (clinical, timeline). 120-day, grade 4 (8 / 14 test): Iscan 0.786 vs 0.733 (0.535-0.930); B-Tl 0.464 vs 0.580 (0.359-0.806) | UCSF_RESULTS.md Part B "UCSF's own TRAIN / TEST split" and 120-day (internal) | PLANNED |
| Single-scan radiomics setting (Christodoulou-style), scan-level label | see section 8 | CHRISTODOULOU_REPLICATION.md | PLANNED (scan-level variant) |
| Questions fixed in advance | see Table 2 inputs (section 9) | | |

---

## 3. Results 3.1: each pathway on MU-Glioma-Post

All rows: MU-IU (62 / 84 / 80 patients, 146 scans), 5 x 5 CV, 1,000-draw patient bootstrap, CSV-checked (`detection/auc.csv`).
Source for every row: DETECTION_TASK.md.

| Quantity | AUC (95% CI) | Status |
|---|---|---|
| Clinical alone (B0) | 0.530 (0.450-0.606) | PLANNED |
| **Timeline + clinical (B1)** | **0.822 (0.749-0.902)** | PLANNED |
| Primary model P (B1 + imaging, includes timing inputs) | 0.837 (0.763-0.904) | PLANNED primary |
| P - B1 | +0.015 (-0.032 to +0.063): NO-GO rule fails (needs >= +0.03 with CI excluding 0) | PLANNED |
| P+R (radiomics added) | 0.833 (0.765-0.897); P+R - P -0.004 (-0.017 to +0.012) | PLANNED |
| I (imaging as run, contains timing inputs) | 0.806 (0.747-0.865); I - B1 -0.016 (-0.095 to +0.061) | PLANNED |
| B1 - B0 | +0.292 (+0.200 to +0.398) | PLANNED |
| Pure images, scan alone (I_scan) | 0.659 (0.567-0.733) | EXPLORATORY |
| **Pure images + change (I_pure) = image pathway** | **0.709 (0.630-0.781)** | EXPLORATORY |
| B1 + I_pure = system combined | 0.821 (0.744-0.894); minus B1 -0.001 (-0.052 to +0.046) | EXPLORATORY |
| Clinical + I_pure | 0.706 (0.622-0.780) | EXPLORATORY |
| Secondary: all grade-4 scans (64 / 117) | B0 0.514, B1 0.845 (0.781-0.906), P 0.859 (0.805-0.909), I 0.822; I_pure 0.712 | PLANNED / EXPLORATORY |
| Secondary: secondary negatives (62 / 173) | B1 0.807 (0.759-0.858), P 0.802, I_pure 0.655 | PLANNED |
| All gliomas, IU (64 / 98 / 87) | B0 0.573, B1 0.814 (0.737-0.888), P 0.851 (0.789-0.908), P - B1 +0.036 (-0.014 to +0.085) | PLANNED |
| All gliomas, all scans (73 / 156 / 114) | B1 0.814, P 0.855, P - B1 **+0.041 (+0.006 to +0.081)** | PLANNED |
| Timeline vs timing: why | 56 of 62 positives later post-RT; 51 of 84 negatives early post-RT. Single inputs: visit index 0.775, days since RT end 0.765, days from diagnosis 0.742 | PLANNED (surprises) |

**Within phase (grade 4 IU; positives / negatives).** Later post-RT 56 / 32: B0 0.530 (0.386-0.669), B1 0.638 (0.488-0.799), P 0.623, I 0.627 (0.523-0.720);
phase-stratified 62 / 84: B1 0.640 (0.508-0.784), P 0.659, I 0.664 (0.576-0.750). Early post-RT 4 / 51 and during RT 2 / 1 are descriptive only
(P 0.975 early). PLANNED (strata with >= 10 of each class get CIs). Pure images within phase: I_pure later post-RT 0.650 (0.541-0.742),
phase-stratified 0.677 (0.580-0.767); I_scan 0.655 and 0.680; B1 + I_pure 0.622 / 0.654 (EXPLORATORY).
Contrasts: I - I_pure +0.097 (+0.047 to +0.153) overall, -0.013 (-0.057 to +0.037) within phase; I_pure - B1 -0.113 (-0.227 to -0.012) overall,
+0.037 (-0.150 to +0.194) within phase; B1 + I_pure - B1 -0.001 (-0.052 to +0.046). EXPLORATORY.

**Gaps filled 2026-10-24 (STORY.md; script `exploratory_pure_imaging_forward_lumiere.py`; EXPLORATORY, not re-verified here).**
120-day risk, grade 4, all scans (249): images alone 0.65 (0.57-0.73), core 0.68 (0.60-0.76), both 0.69 (0.62-0.77); intended use (173): 0.62 / 0.60 / 0.62.

---

## 4. Results 3.2: the pathways at two external centres

### LUMIERE (locked; fitted once on MU grade-4 detection rows, applied once)

All: LUM (73 / 105 / 79), plain AUC, patient bootstrap 1,000 draws. Source: DETECTION_TASK.md External test; `detection/lumiere.csv` (CSV-checked).

| Quantity | AUC (95% CI) | Status |
|---|---|---|
| **T (combined; grade-4 trained)** | **0.773 (0.679-0.857)** | PLANNED |
| T, MU internal (grade 4, IU, same CV) | 0.804 (0.731-0.885): "transports without loss" | PLANNED |
| T (all-glioma trained) | 0.768 (0.670-0.857) | PLANNED sensitivity |
| Tbase (timeline alone, no imaging) | 0.689 (0.600-0.805); MU internal 0.757 (0.678-0.846) | EXPLORATORY reference |
| T - Tbase | +0.084 (-0.006 to +0.164) (all-glioma trained +0.093, +0.003 to +0.161); MU internal +0.046 (-0.011 to +0.106) | EXPLORATORY |
| T_img (images alone, all 178 scans) | **0.655** (0.565-0.733) (STORY writes 0.66; see Mismatch 3). The 3-volume model on the 10 scans without a previous scan: 0.654 | EXPLORATORY (gap fill 2026-10-24) |
| LUMIERE scans with rater flag = 0 (72 / 78) | T 0.715 (0.597-0.815); Tbase 0.590 (0.478-0.714); T - Tbase +0.125 (+0.007 to +0.232) | EXPLORATORY |
| Scans with a previous scan (70 / 98) | T 0.789 (0.690-0.876); Tbase 0.703; T - Tbase +0.086 (-0.013 to +0.171) | EXPLORATORY |
| Transport-failure flag (AUC < 0.65) | not raised | PLANNED rule |
| Strongest single inputs | log ET 0.662, log oedema 0.657, oedema / ET change 0.646 / 0.628; log days since surgery 0.608 | EXPLORATORY |
| Clinical alone (locked) | **not available** (Mismatch 12) | |
| Clinical alone (age, sex, IDH, MGMT; fitted once as Tbase, applied once) | **0.554 (0.458-0.635)**; MU internal OOF (= B0, grade 4, IU) 0.530 (0.450-0.606) | EXPLORATORY (2026-10-26; DETECTION_TASK.md EXPLORATORY section; `scripts/exploratory_lumiere_clinical_alone.py`; resolves Mismatch 12) |

Pathway statement: images alone 0.65, timeline alone 0.69, both 0.77 (complementary).

### UCSF-ALPTDG (locked MU models, applied once to UCSF-P: 29 / 40 / 69). Source: UCSF_RESULTS.md Part A (CSV-checked, `ucsf/locked/auc.csv`).

| Arm | Locked AUC (95% CI) | UCSF-trained AUC (95% CI), Part B | Status |
|---|---|---|---|
| Clinical alone (A-B0 / B0) | 0.502 (0.364-0.630) | 0.407 (0.314-0.494) | PLANNED |
| Timeline (A-Tbase approximate / B-Tl) | 0.561 (0.420-0.687) | 0.669 (0.549-0.784) | PLANNED (A-T arms "approximate"; B-Tl added arm) |
| **Images, scan alone (A-Iscan / Iscan)** | **0.795 (0.686-0.887)** | **0.826 (0.729-0.909)** | PLANNED |
| **Images + change (A-Ipure / Ipure)** | **0.726 (0.603-0.835)** | 0.863 (0.772-0.934) | PLANNED primary (Q1) |
| Clinical + Iscan | 0.788 (0.676-0.880) | 0.813 (0.721-0.901) | PLANNED |
| Clinical + Ipure | 0.750 (0.630-0.854) | 0.860 (0.774-0.931) | PLANNED |
| LUMIERE image set (A-Timg / Timg) | 0.889 (0.811-0.955) | 0.913 (0.843-0.967) | PLANNED |
| Combined (A-T) / B-Tl + Ipure | 0.856 (0.758-0.930) | 0.871 (0.790-0.938) | PLANNED (approximate) |

- Calibration (locked, secondary): O/E 1.12-1.24 for image arms; slopes Iscan 2.20 (1.34-3.46), Timg 5.69; A-T and A-Tbase over-predict (O/E 0.72, 0.67). UCSF prevalence 42%.
- Q1 (A-Ipure AUC >= 0.65, lower bound > 0.5): **met**, 0.726 (0.603-0.835). Q2 (A-B0 + Ipure - A-B0): **met**, +0.248 (+0.096 to +0.392).
- Contrasts: A-T - A-Tbase +0.295 (+0.167 to +0.432); A-Ipure - A-Iscan -0.069 (-0.126 to -0.014) (the change inputs transport worse; UCSF change is 3-6 times narrower than MU).
- Part B contrasts (UCSF-trained): B0 + Ipure - B0 +0.453 (+0.336 to +0.563); B-Tl + Ipure - B-Tl +0.203 (+0.089 to +0.316); Ipure - Iscan +0.037 (-0.018 to +0.095); B-Tl - B0 +0.262 (+0.145 to +0.374).
- **Q3** (B - A, Ipure, descriptive): **+0.137 (+0.033 to +0.257)** grade 4 (0.863 vs 0.726); all gliomas +0.108 (+0.043 to +0.185); GBM +0.048 (-0.088 to +0.191). EXPLORATORY for other arms: Iscan +0.031 (-0.052 to +0.116), Timg +0.024 (-0.039 to +0.083), B0 + Ipure +0.110 (+0.014 to +0.219).
- Part B label-permutation control (EXPLORATORY): 20 permutations, image arms mean AUC 0.40-0.46 (max 0.62) in grade 4. B0 at or below 0.5 is the usual negative bias, not a reversed signal.
- Sensitivity sets (A-Iscan / A-Ipure / A-Timg): WHO GBM (21 / 20) 0.793 / 0.740 / 0.888; `pos_s2_between` (39 / 40) 0.783 / 0.707 / 0.881; verified negatives (29 / 33) 0.798 / 0.739 / 0.916; later post-RT (27 / 38) 0.803 / 0.735 / 0.904; all gliomas (48 / 78, all-glioma models) 0.724 / 0.747 / 0.801; all scans (34 / 103 / 97) A-Iscan 0.795 (0.694-0.868). `et_increased` (71 / 69) is circular, a reference only.
- Single locked inputs, UCSF-P (EXPLORATORY): log ET 0.878, log ET max axial area 0.867, log tumour 0.876, log oedema 0.834, ET ratio to previous 0.822, to history minimum 0.839; every clinical input 0.40-0.49; log days since surgery 0.542; log days since previous scan 0.281.
- Within the "ET Increased" scans A-T keeps 0.870 (0.722-0.974) only because it holds the scan-1 to scan-2 interval (the inverted interval alone gives 0.72); it is not evidence for the images (UCSF_AUDIT.md, EXPLORATORY intervals).
- 120-day risk from scan 1, locked (45 / 63 / 108): F-B0 0.530 (0.421-0.629), **F-Iscan 0.668 (0.567-0.767)**, F-B0 + Iscan 0.679; UCSF-trained Iscan 0.709 (0.605-0.802). PLANNED, secondary task.

### Deep networks on UCSF (UCSF_RESULTS.md Part C; PLANNED; 5 repeats fixed before the run)

| Arm | Grade 4 (29 / 40) AUC (95% CI) |
|---|---|
| C-locked G1 / G3 (retrained MU networks, 4-network ensemble) | 0.754 (0.636-0.856) / 0.710 (0.587-0.826) |
| C-ucsf G1 / G3 | 0.742 (0.626-0.845) / 0.741 (0.625-0.843) |
| Transfer T1 | 0.748 (0.632-0.851) |
| G4 permuted-label control | **0.541 (0.480-0.603)**; validity met (CI covers 0.5; repeat 0 alone would have failed at 0.710) |
| G1 - G4 / G3 - G4 / T1 - G4 | +0.201 (+0.094 to +0.306) / +0.200 / +0.207: Q4 yes |
| T1 - G1 | +0.005 (-0.007 to +0.017) |
| EXPLORATORY: log ET volume alone; G1 - log ET | 0.878 (0.791-0.949); -0.136 (-0.207 to -0.065) |

Networks' logits track log ET volume: r >= 0.76 (median 0.82-0.88 per repeat; positive in 100 of 100 networks trained on real labels); MU networks r 0.86.
On MU the same networks learned nothing: inner OOF AUC 0.491 (G1), 0.565 (G3). Excluding the 60 patients also in UCSF-PDGM (16 / 20): locked G1 0.778, G1 - G4 +0.231.
(EXPLORATORY diagnostics.)

---

## 5. Results 3.3: what each score rests on

### MU: the timeline's gain lies between phases of care (EXPLORATORY audit)

| Quantity | Value (CI) | Source |
|---|---|---|
| Timeline added to clinical + images, overall | +0.114 (+0.035 to +0.196) | DETECTION_TASK.md "images + clinical" |
| Same, phase-stratified | -0.016 (-0.134 to +0.109) | same |
| Clinical + I_pure - I_pure | -0.003 (-0.020 to +0.015); within phase -0.007 | same |
| Clinical + I_pure - clinical | +0.176 (+0.084 to +0.271) | same |
| Pure images vs timeline within phase | I_pure 0.677 (0.580-0.767) vs B1 0.640 (0.508-0.784); contrast +0.037 (-0.150 to +0.194), supports "as much as", not "more than" | DETECTION_TASK.md; STORY gap 3 |
| Reliability-card tested cell (later post-RT, ET not increased; 38 / 16) | timeline 0.58 (0.44-0.77), images 0.77 (0.65-0.88), both 0.61 (0.43-0.80) | RELIABILITY_CARD.md (EXPLORATORY) |
| MU ET features | log ET volume AUC 0.635 (later post-RT 0.657); MU ET ratio to previous 0.487; MU positives ET 7.1 cc (2.8-14.2) vs negatives 3.4 cc (0.7-8.9); median ET log ratio at the positive scan -0.06 | UCSF_AUDIT.md section 6 |

### UCSF: enhancing volume (EXPLORATORY audit, UCSF_AUDIT.md; UCSF-P 29 / 40)

| Quantity | Value | Source |
|---|---|---|
| log ET volume alone | **0.878 (0.790-0.946)**; CV logistic 0.870; + ET ratio + log oedema 0.896 | section 6 |
| positives rated "ET Increased" at scan 2 | **27 of 29** (negatives 10 of 40; unchanged: 1 vs 25; decreased: 1 vs 5) | section 4 |
| "ET Increased" as a binary rule | AUC 0.841 (0.753-0.919); sensitivity 0.93, specificity 0.75 | section 4 |
| Oedema change unchanged | 0 of 29 positives vs 20 of 40 negatives | section 4 |
| ET volume | positives 13.5 cc (7.5-23.2) vs negatives 1.4 cc (0.0-6.4); 10 of 40 negatives have no ET (0 of 29 positives); median ET log ratio to scan 1 +0.60 vs 0.00 | sections 1 and 6 |
| Spearman with log ET | A-Timg 0.97, A-Iscan 0.81, A-Ipure 0.72, Iscan 0.91, Ipure 0.87 | section 6 |
| Within the 37 "ET Increased" scans (27 / 10) | locked A-Iscan 0.652 (0.444-0.836), A-Ipure 0.530 (0.302-0.738), A-Timg 0.756 (0.563-0.909), log ET 0.741 (0.556-0.897); UCSF-trained Timg 0.811 (0.610-0.976); deep G1 0.422 (0.215-0.638) | EXPLORATORY intervals table |
| Within ET-present scans (59; 29 / 30) | A-Iscan 0.726 (0.595-0.853), A-Ipure 0.634 (0.489-0.773), A-Timg 0.852, log ET 0.838 | section 1 |
| ET absent | 37% of all UCSF scans; 0 of 29 positives, 10 of 40 negatives; "ET present" indicator AUC 0.625 (MU 0.527) | section 1 |
| Days from diagnosis | AUC 0.542 (0.393-0.681): case mix by phase does not drive UCSF (unlike MU) | section 5 |
| Scan interval | positives 41 d (28-58) vs negatives 56 d (54-67); the inverted interval gives AUC 0.72 | section 2 |
| Progression dated vs scan 2 | median +7 d (IQR 0 to +11) | section 3 |
| Verdict sentence | "progression was dated a median of 7 days after the evaluated scan, 27 of 29 positive scans were rated by UCSF as showing increased enhancement, and enhancing-tumour volume alone gave an AUC of 0.88" | section "Overall verdict" |

### The image-model ladder (EXPLORATORY; Fig 3C; MU-IU)

| Rung | AUC (95% CI) | Within phase | Source |
|---|---|---|---|
| Single scan (I_scan) | 0.659 (0.567-0.733) | later post-RT 0.655; phase-stratified 0.680 | DETECTION_TASK.md |
| + change from earlier scans (I_pure) | 0.709 (0.630-0.781); difference +0.050 (-0.003 to +0.106), verified in section 12 (E); within phase -0.003 (-0.095 to +0.080) | 0.650; 0.677 | same; Mismatch 8 |
| + schedule context (I as run; adds days since previous scan, has-previous flag, RT-anchored nadir) | 0.806 (0.747-0.865); I - I_pure +0.097 (+0.047 to +0.153) | 0.627; 0.664; difference within phase -0.013 (-0.057 to +0.037) | same |
| Timeline B1 | 0.822 (0.749-0.902) | 0.638; 0.640 | PLANNED |

Days since previous scan alone 0.740, has-previous alone 0.726 (the schedule rung is timing).

### Deep networks on MU (one sentence; DETECTION_DEEP.md, PLANNED)

Image-only AUC of the fine-tuned networks, MU-IU: G1 0.461 (0.389-0.535), G3 0.447 (0.400-0.489), G2 0.514 (0.437-0.593), G1_all 0.529, G3_all 0.507, G2_all 0.570 (0.491-0.647);
permuted-label controls G4 0.483 (0.436-0.527), G4_all 0.481 (0.436-0.525). B1 + arm - B1 within -0.003 to +0.004 in all arms. The forward-label arm G5: C2 0.601, C2 + G5 0.608 (+0.006, -0.021 to +0.034), G5 image only 0.575.
Rule 4 (validity) met. UCSF: the deep scores track log ET volume (r about 0.8; see section 4).

---

## 6. Results 3.4: the confidence

All from SYSTEM_RESULTS.md unless noted; CSV-checked (`system/conformal.csv`, `selective.csv`). Sets: MU-IU 62 / 84 / 80 patients (146 scans, mean over 5 repeats); LUM 73 / 105 / 79; UCSF-P 29 / 40 / 69. Bootstrap seed 20261026. PLANNED unless stated.

### S1: coverage at alpha 0.2 (nominal 0.80; met if >= 0.78)

| Cohort | Timeline | Images | **Combined** (95% CI) | Combined events / non-events | Combined alpha 0.1 |
|---|---|---|---|---|---|
| MU grade 4 | 0.795 (0.731-0.853) met | 0.844 (0.797-0.890) met | **0.823 (0.759-0.883) met** | 0.819 / 0.826 | 0.922 |
| LUMIERE | 0.798 (0.732-0.868) met | **0.708 (0.648-0.759) not met** | **0.871 (0.807-0.924) met** | 0.767 / 0.943 | 0.978 |
| UCSF | **0.696 (0.594-0.812) not met** | 0.826 (0.739-0.913) met | **0.783 (0.681-0.870) met** | 0.966 / 0.650 | 0.957 |
| MU all gliomas (secondary) | 0.825 met | 0.848 met | 0.837 (0.790-0.881) met | 0.756 / 0.890 | 0.941 |

- Singleton rate at alpha 0.2, combined: MU 0.75, LUMIERE 0.62, UCSF 0.64.
- Conditional coverage fails: MU later post-RT 0.743 (ET increased 0.683, ET absent 0.667; the tested cell 0.781); LUMIERE events 0.767; UCSF non-events 0.650, later post-RT with ET not increased 0.607; early post-RT over-covered (0.971).
- Mondrian (secondary): MU combined 0.788; breaks externally (LUMIERE 0.652, UCSF 0.507).
- Cost of the split (conformal model's AUC vs displayed): MU combined 0.800 vs 0.821; LUMIERE 0.776 vs 0.773; **UCSF 0.775 vs 0.856**.

### S2 / S3 (combined score)

| Cohort | Flag | Flagged | AUC unflagged / flagged | S2 (95% CI) | S3 (95% CI) |
|---|---|---|---|---|---|
| MU grade 4 | **disagreement** | 40% | 0.901 / 0.594 | **+0.307 (+0.175 to +0.432) met** | **+0.083 (+0.046 to +0.123) met** |
| | conformal {0,1} | 25% | 0.860 / 0.633 | +0.228 (+0.074 to +0.370) met | +0.024 (-0.000 to +0.048) not met |
| | out of range | 56% | 0.847 / 0.796 | +0.051 (-0.066 to +0.183) not met | +0.015 not met |
| | tier | 63% | 0.609 / 0.832 | -0.224 (-0.409 to -0.017) reversed | -0.014 not met |
| | any flag | 91% | 0.646 / 0.816 | -0.170 (-0.503 to +0.147) not met | +0.025 not met |
| LUMIERE | disagreement | 57% | 0.826 / 0.721 | +0.105 (-0.049 to +0.266) not met | +0.051 (-0.028 to +0.144) not met |
| | conformal {0,1} | 38% | 0.814 / 0.567 | +0.248 (+0.102 to +0.412) met | +0.041 not met |
| | any flag | 93% | 1.000 / 0.750 | +0.250, rests on 12 unflagged scans | +0.226, same |
| UCSF | disagreement | 55% | 0.850 / 0.869 | -0.019 (-0.218 to +0.175) not met | -0.004 not met |
| | conformal {0,1} | 36% | 0.921 / 0.833 | +0.087 (-0.070 to +0.291) not met | **+0.073 (+0.014 to +0.138) met** |
| | tier, any flag | 100% | no unflagged scan | n/a | n/a |

MU all gliomas, disagreement: S2 +0.195 (+0.080 to +0.316), S3 +0.048 (+0.017 to +0.078). S3 reference = phase-composition-matched removal (MU detection phase; UCSF `rt_phase`; LUMIERE plain random).

### S4 (descriptive): Brier and error by tier, combined score

| Cohort | Tier | Scans (pos / neg) | Brier (95% CI) | Error rate (95% CI) |
|---|---|---|---|---|
| MU grade 4 | tested | 54 (38 / 16) | 0.222 (0.159-0.292) | 0.293 (0.155-0.426) |
| | few cases | 92 (24 / 68) | 0.147 (0.114-0.183) | 0.235 (0.167-0.305) |
| LUMIERE | tested | 159 (66 / 93) | 0.187 (0.165-0.212) | 0.289 (0.204-0.380) |
| | few cases | 19 (7 / 12) | 0.258 (0.155-0.395) | 0.421 (0.176-0.688) |
| UCSF | few cases | 69 (29 / 40) | 0.208 (0.176-0.240) | 0.275 (0.174-0.377) |

Reading: expected direction on LUMIERE; reversed on MU (the "few cases" MU scans are mostly easy early post-RT negatives). The tier states evidence, not accuracy.

### Reduced confidence design (EXPLORATORY; commit 3d20c41; chosen after S1-S4 were read; MU-IU, LUMIERE, UCSF-P)

| Rule | MU: flagged; S2; S3; error flagged / unflagged | LUMIERE | UCSF |
|---|---|---|---|
| D1 disagree | 40%; +0.307; +0.083; 0.43 / 0.14 | 57%; +0.105; +0.051 (ns); 0.36 / 0.22 | 55%; -0.019; -0.004; 0.26 / 0.29 |
| D2 conformal {0,1} | 25%; +0.228; +0.024 (ns); 0.37 / 0.22 | 38%; +0.248; +0.041 (ns); 0.48 / 0.20 | 36%; +0.087 (ns); +0.073; 0.32 / 0.25 |
| D3 or | 52%; +0.279; +0.090; 0.38 / 0.12 | 68%; +0.130 (ns); +0.086; 0.36 / 0.19 | 68%; +0.066 (ns); +0.086 (ns); 0.26 / 0.32 |
| **D4 and** | **12%**; +0.334 (+0.125 to +0.515); +0.023 (+0.010 to +0.041); **0.52 / 0.22** | **27%**; +0.300 (+0.129 to +0.519); +0.047 (+0.005 to +0.085); **0.54 / 0.22** | **23%**; +0.040 (ns); +0.038 (+0.001 to +0.087); **0.38 / 0.25** |

D4 flagged minus unflagged error: MU +0.30 (+0.17 to +0.43); LUMIERE +0.33 (+0.13 to +0.48); UCSF +0.13 (-0.13 to +0.40). D4 is the only rule with S3 lower bound > 0 in every cohort; it flags 12-27%. No reduced rule passes both S2 and S3 in all three cohorts. Not tested on new data.

### Reliability card (EXPLORATORY post hoc; RELIABILITY_CARD.md)

| Quantity | Value | Source |
|---|---|---|
| Report scans (MU grade-4 index scans, repeat 0): tested / few cases / not tested | **35 / 212 / 2** of 249 | RELIABILITY_CARD.md "Reading" |
| Tested cells in all | **4**: 1 on MU, 3 on LUMIERE, 0 on UCSF | same |
| MU tested cell | later post-RT, ET not increased: 38 / 16; timeline 0.58 (0.44-0.77), images 0.77 (0.65-0.88), both 0.61 (0.43-0.80) | lookup table |
| LUMIERE tested cells (phase unknown) | ET absent 13 / 44: 0.59 / 0.53 / 0.67 (timeline / images / both); ET increased 28 / 21: 0.91 / 0.61 / 0.83; ET not increased 25 / 28: 0.85 / 0.55 / 0.77 | lookup table |
| UCSF cells (all few cases) | later post-RT ET increased 20 / 5; ET not increased 7 / 21; ET absent 0 / 12; early post-RT / unknown ET not increased 0 / 2 and 2 / 0 | lookup table |
| Early post-RT window on MU | at most 3 progression scans in any cell; ET increased 1 / 8, ET not increased 3 / 8; none externally | card "Reading" |
| Overall reference rows (not card cells) | MU all scans 64 / 117: 0.84 (0.78-0.91) / 0.71 (0.64-0.78) / 0.84 (0.78-0.90); LUMIERE 73 / 105: 0.69 / 0.65 (0.56-0.73) / 0.77; UCSF locked 29 / 40: 0.56 / 0.73 / 0.86; UCSF-trained: 0.67 / 0.86 / 0.87 | lookup table |
| Agreement: MU | agree 42 / 70, combined 0.91 (0.86-0.96); disagree 22 / 47, combined 0.64 (0.54-0.76), timeline 0.74, images 0.31; progression share 73% both above vs 4% both below; timeline-only high 49%, images-only high 14% | agreement table |
| Agreement: LUMIERE | agree 33 / 43, combined 0.83; disagree 40 / 62, combined 0.72; 71% vs 16%; 41% vs 37% | same |
| Agreement: UCSF locked | agree 11 / 20, combined 0.85 (0.67-0.99); disagree 18 / 20, combined 0.87 (0.73-0.96); 53% vs 19%; timeline-only high 32%, images-only high 63% | same |
| Inputs inside training range (MU report scans) | 123 inside, 126 flagged; reasons MGMT unknown 39, RT duration 13, IDH unknown 11 | card "Inputs inside the training range" |
| Reliability checker on pre-card reports | the 214 report scans needing a tier statement: tier stated 0 of 214 (arms A, C, v1, v2) | card "Effect on existing reports" |

---

## 7. Results 3.5: the reports

### v3.1 (second evaluation after a seen failure; checker unchanged; plan 4f7e7b9). Source: REPORT_V3_1.md. Rules planned; the evaluation is a second look.

| Quantity | Value | Population |
|---|---|---|
| **S5: faithful** | MU **114/114** (Wilson 0.97-1.00); LUMIERE **162/162** (0.98-1.00); UCSF **130/130** (0.97-1.00); all 406/406 (0.99-1.00); met | MU intended use, 60 patients; LUMIERE 69 patients not in development; UCSF 130 patients not in development |
| **S6: tier stated** where evidence is thin | 71/71 MU; 19/19 LUMIERE; 130/130 UCSF; 220/220 | few cases / not tested |
| **S7: follows a changed field** | **28/30** (agreement 6/6, card tier 6/6, conformal 6/6, out of range 6/6, ET change 4/6); met (>= 27); full check passes on all 30; both ET misses = the rule artefact (old change 0.0 cc); exploratory reading 30/30 | 30 perturbed records (7 MU, 13 LUMIERE, 10 UCSF), seed 1 |
| Everything else, all 406 | 0 unparsed, 0 unsupported numbers, 0 invalid citations, 0 omitted or spurious flags, 0 forbidden content, 0 conformal / agreement errors; no report mentions RANO | |
| Length and cost | median 317 (MU), 305 (LUMIERE), 290 (UCSF) words; 1.08 s per report batched on one H100 | |
| Development (frozen prompt v3.4) | 58 records (MU 32, LUMIERE 16, UCSF 10): 58/58 after iteration 1; 2 of 4 allowed iterations used | |

### v3 (the failure that is disclosed). Source: REPORT_V3.md. PLANNED rule.

| Quantity | Value |
|---|---|
| S5 | MU 114/114; **LUMIERE 0/178 (0.00-0.02), not met**; UCSF 140/140; all 254/432 = 0.59 (0.54-0.63), not met |
| Cause | one design error: the rater flag sentence "within 3 months" had its "3" in no cited field (+ "three segmentation volumes" in 5 reports). EXPLORATORY: with the fix, 178/178 pass the frozen checker (v3 stays 0/178) |
| S6 | 71/71, 19/19, 140/140; 230/230 |
| S7 | 29/30 (agreement 6/6, card tier 6/6, conformal 6/6, out of range 6/6, ET change 5/6) |
| Development | 32 MU records, pass 32/32 at v3.3; iterations 23/32, 32/32, 12/32, 32/32 |
| EXPLORATORY smaller model (Qwen3.5-9B, v3 prompt) | 85/432 (20/114 MU, 21/178 LUMIERE, 44/140 UCSF); failures mostly fabrication |

### Model-size ladder (v3.1; descriptive, EXPLORATORY secondary; frozen prompt, no per-model tuning)

| Model | S5 MU | S5 LUMIERE | S5 UCSF | Total | >= 0.95 in every cohort | S6 | S7 | s / report | weights GiB |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | 0/114 | 21/162 | 0/130 | 21/406 | no | 204/220 | 21/30 | 0.13 | 3.6 |
| Qwen3.5-4B | 44/114 | 155/162 | 107/130 | 306/406 | no | 220/220 | 27/30 | 0.17 | 8.0 |
| gemma-4-E4B-it | 33/114 | 73/162 | 11/130 | 117/406 | no | 220/220 | 25/30 | 0.17 | 14.5 |
| Qwen3.5-9B | 98/114 (0.78-0.91) | 156/162 | 114/130 | **368/406** | no | 220/220 | 28/30 | 0.21 | 16.8 |
| **Qwen3.8-27B (primary)** | 114/114 | 162/162 | 130/130 | 406/406 | **yes** | 220/220 | 28/30 | 1.08 | 50.2 |
| gemma-4-31B-it | 114/114 | 162/162 | 130/130 | 406/406 | **yes** | 220/220 | 28/30 | 4.86 | 57.9 |
| Qwen3.5-35B-A3B (MoE) | 97/114 | 162/162 | 130/130 | 389/406 | no (MU 0.85) | 220/220 | 28/30 | 0.74 | 64.7 |

Totals computed from the per-cohort counts (they match STORY: 9B 368, 4B 306, 2B 21). L1: the smallest model meeting S5 >= 0.95 in every cohort is Qwen3.8-27B; the only other is gemma-4-31B-it (4.5 times slower); Qwen3.5-9B is closest (0.86 / 0.96 / 0.88).
Failure categories (reports of 406): Qwen3.5-4B missing content 93; 9B missing content 37 (enhancing volume), 1 unsupported number; E4B conformal / agreement 224, missing content 132, invalid citation 33; 2B unparsed 24, unsupported numbers 71, conformal / agreement 154, invalid citations 62, forbidden wording 15, missing content 339; 35B-A3B conformal 17 (combined 80% set not stated, MU). EXPLORATORY: Qwen3.5-35B-A3B-FP8 ran by mistake (93/114, 162/162, 127/130; not in the ladder).

---

## 8. Christodoulou 2026 replication (EXPLORATORY for the patient-level label; supplement + one Discussion sentence)

Source: CHRISTODOULOU_REPLICATION.md. Their reported result: test AUC 0.80 (abstract), single held-out set of 30 patients (96 scans, 53 positive); their committed log gives 0.7995 and Brier 0.173 (their abstract 0.093 to 0.088 not in the logs).

**Their label (source check, commit 9810dc4; code at their commit 643c888).** y = 1 for every timepoint of a patient with a non-missing "Time to First Progression"; the GBM filter leaks non-GBM patients as negatives. Their table: 593 scans of 203 patients; 380 positive scans of 122 patients; 146 scans of 46 non-GBM patients all labelled 0; 213 of 593 scans at or after progression.

**Scan-level variant (our label, PLANNED; features: v2 radiomics, 2316 columns -> 256 by univariate AUC, LightGBM + Optuna 40 trials + Platt).** MU-IU:

| Quantity | AUC (95% CI) |
|---|---|
| CH, intended use (62 / 84 / 80) | **0.579 (0.499-0.656)** |
| CH, all grade-4 scans (64 / 117 / 92) | 0.565 (0.490-0.641) |
| CH later post-RT / phase-stratified | 0.558 (0.435-0.674) / 0.579 (0.467-0.685) |
| CH - B1; CH - I_scan; CH - I_pure | -0.242 (-0.352 to -0.139); -0.079 (-0.140 to -0.005); -0.130 (-0.213 to -0.040) |
| Their design 100 times (18 of 92 grade-4 patients held out): CH | mean 0.614, SD 0.085, range 0.374-0.812, 1% of splits >= 0.80; B1 on the same splits 0.852 (72% >= 0.80) |
| Brier: raw -> Platt (IU) | 0.262 -> 0.251, versus 0.244 for predicting the prevalence |
| Locked on UCSF-P (29 / 40) | 0.804 (0.692-0.905); within "ET Increased" 0.63; Spearman with log ET 0.67 |

"Their 0.80 is not reproduced" under the scan-level label.

**EXPLORATORY: their patient-level label (run 2026-10-26; `christodoulou_patient_label.py`).**

| Population | Pos / neg scans | CH (radiomics pipeline) | Clinical only | Follow-up only | Clinical + follow-up |
|---|---|---|---|---|---|
| GBM only (447 scans, 157 patients; 123 positive, 34 negative patients) | 385 / 62 | **0.439 (0.376-0.502)** | 0.567 (0.398-0.727) | 0.611 (0.454-0.799) | 0.754 (0.605-0.900) |
| As coded (all diagnoses; 594 scans, 203 patients) | 385 / 209 | **0.727 (0.660-0.783)** | **0.811 (0.739-0.874)** | 0.480 | 0.885 (0.818-0.936) |

- As coded: CH - C0 -0.084 (-0.158 to -0.008); 100 single 30-patient splits: CH mean 0.746 (23% >= 0.80), C0 0.826 (67% >= 0.80). GBM: CH mean 0.573, 2% >= 0.80 (99 splits).
- Follow-up leakage check positive: follow-up alone 0.61 in GBM; C0 + FU - C0 = +0.187 (+0.085 to +0.329).
- Of 385 positive scans, 172 precede progression (41 by more than 180 d).
- Reading for the Discussion sentence: under their label the task is mostly patient-level (GBM vs other gliomas, follow-up length), clinical data alone reach 0.81, the radiomics pipeline 0.73 (0.44 in GBM only).

---

## 9. Table 2 inputs: questions fixed in advance and their answers

| ID | Question | Rule fixed in advance | Result | Met? | Plan |
|---|---|---|---|---|---|
| MU-1 | Does imaging add to timeline in detection (grade 4, IU)? | P >= 0.75 with lower bound >= 0.65, and P - B1 >= +0.03 with CI excluding 0 | P 0.837 (0.763-0.904) meets the first; P - B1 +0.015 (-0.032 to +0.063) fails the second | **No (NO-GO for detection on MU alone)** | DETECTION_TASK.md (commit 2b4c927) |
| MU-2 | Do deep arms add? | stack beats P by >= 0.03 with CI excluding 0; G4 CI covers 0.5 | none adds; G4 0.483 (0.436-0.527) covers 0.5 | No; validity met | same |
| LUM-1 | Does the locked T transport to LUMIERE? | external AUC >= 0.65 (below = transport failure flag) | T 0.773 (0.679-0.857); lower bound 0.679 | Yes (no transport failure) | same |
| UCSF-Q1 | Do MU image measurements transport? | A-Ipure AUC >= 0.65 with lower bound > 0.5 | 0.726 (0.603-0.835) | **Met** | UCSF_PLAN.md (0e7c9fe) |
| UCSF-Q2 | Do images add to clinical data without a timeline? | A-B0 + Ipure - A-B0, CI excludes 0 | +0.248 (+0.096 to +0.392) | **Met** | same |
| UCSF-Q3 | Does training on UCSF beat the locked model? | descriptive, B - A on Ipure | +0.137 (+0.033 to +0.257) | Yes (descriptive) | same |
| UCSF-Q4 | Do deep networks learn on UCSF? | G1 or G3 above G4, G4 covers 0.5 | G1 - G4 +0.201 (+0.094 to +0.306); G4 0.541 (0.480-0.603) | **Met** | same |
| S1 | Do conformal sets keep their coverage? | coverage >= 0.78 at alpha 0.2 on MU and each external cohort | combined 0.823 / 0.871 / 0.783; images LUMIERE 0.708 and timeline UCSF 0.696 not met | **Met (combined)** | SYSTEM_PLAN.md (e7cba80) |
| S2 | Do flags pick out wrong scans? | AUC unflagged - flagged > 0 with CI excluding 0 (MU; also LUMIERE, UCSF) | disagreement: MU +0.307 met; LUMIERE and UCSF not met. any flag: MU -0.170 not met | **Met on MU for disagreement and conformal {0,1}; not met externally** | same |
| S3 | Does abstaining beat matched removal? | retained AUC - composition-matched removal > 0, CI excluding 0 | disagreement MU +0.083 (+0.046 to +0.123) met; LUMIERE and UCSF not met; conformal {0,1} UCSF +0.073 met | **Met on MU (disagreement)** | same |
| S4 | Do the card's tiers mean something? | descriptive: tested should have lower Brier and error | LUMIERE yes (0.187 vs 0.258; 0.289 vs 0.421); MU reversed (0.222 vs 0.147) | Descriptive | same |
| S5 | Are reports faithful? | >= 95% of reports pass the checker in each cohort | v3: MU 114/114, LUMIERE **0/178**, UCSF 140/140 (**not met**); v3.1: 114/114, 162/162, 130/130 | v3 **not met**; v3.1 **met** (second evaluation) | SYSTEM_PLAN.md; REPORT_V3_1_PLAN.md (4f7e7b9) |
| S6 | Is the tier stated where evidence is thin? | 100% | v3.1 220/220 | **Met** | same |
| S7 | Do reports follow the record? | >= 27 of 30 perturbed records | v3 29/30; v3.1 28/30 | **Met** | same |
| L1 | Smallest model with S5 >= 0.95 in every cohort | descriptive | Qwen3.8-27B (gemma-4-31B-it also) | Descriptive, secondary | REPORT_V3_1_PLAN.md |

---

## 10. Discussion and Limits (numbers the prose may cite)

| Item | Value | Source | Status |
|---|---|---|---|
| Scenario: scan 8 weeks after RT, ET grown | MU early post-RT, ET increased: 1 progression / 8 non-progression scans (few cases); disagree: timeline below / images above -> 14% of such scans were progression; pathways-disagree AUCs timeline 0.74, images 0.31, both 0.64 | RELIABILITY_CARD.md example card | EXPLORATORY |
| Early post-RT window | 4 progression scans of 55 in MU-IU (4 / 51) | DETECTION_TASK.md | PLANNED |
| Literature: Christodoulou 2026 | 0.80 (their single held-out set); our scan-level variant 0.579; patient-level variant 0.73 as coded / 0.44 GBM only | section 8 | EXPLORATORY / PLANNED |
| Literature: Tikhonov 2025 (LUMIERE) | 0.81 | DETECTION_TASK.md header; docs/literature/COMPARABLE_RESULTS.md | context only |
| Literature: Shi 2025 | "only 3 of 20 automated response studies used external test data" | docs/literature/SYSTEM_LANDSCAPE.md row 6.3 | context |
| Limits | one development centre (MU; 155 patients, 126 grade 4); documented, not expert-read, progression; small subgroups (UCSF-P 29 positives; CIs of 0.15-0.25 width); ladder and reduced confidence exploratory; checker lexical; no clinician has read the reports | DETECTION_TASK.md; REPORT_V3_1.md Limits | |
| UCSF caveat | the UCSF AUCs measure agreement with an enhancement-based call made at the same scan; a quarter of negatives have no enhancement | UCSF_AUDIT.md "Caveat sentence" | EXPLORATORY |
| Previous 120-day work (origin) | forward 120-day, grade 4, intended use 0.601 (0.515-0.686); NO-GO for triage on MU alone | INTENDED_USE.md; TRIAGE_FEASIBILITY.md | PLANNED |

---

## 11. Figure inputs (where each panel's numbers live)

| Panel | Numbers | Section here |
|---|---|---|
| Fig 2 (AUC by pathway x cohort) | MU-IU: clinical 0.530, timeline 0.822, images 0.709, combined 0.821. LUMIERE locked: clinical NOT AVAILABLE, timeline 0.689, images 0.655, combined 0.773. UCSF locked: clinical 0.502, timeline 0.561 (approximate), images 0.726 (Ipure) or 0.795 (Iscan), combined 0.856. UCSF-trained: clinical 0.407, timeline 0.669, images 0.863 (Ipure) or 0.826 (Iscan), combined 0.871 | 3, 4 |
| Fig 3A | +0.114 overall, -0.016 within phase | 5 |
| Fig 3B | log ET 0.878; ET Increased 27 / 29 | 5 |
| Fig 3C | 0.659, 0.709, 0.806 | 5 |
| Fig 4A | coverage table | 6 |
| Fig 4B | S2 / S3 table (disagreement) | 6 |
| Fig 4C | card cells | 6 |
| Fig 5 | v3.1 counts by cohort | 7 |

---

## 12. EXPLORATORY: analyses requested in internal review round 3 (2026-10-26)

Added after review (round3_reviewer2.md, M2, M3, M4 and M6), not pre-specified. The exception is F for UCSF, which is
the planned secondary of UCSF_PLAN.md.
- Source: SYSTEM_RESULTS.md, section "EXPLORATORY: analyses requested in internal review (2026-10-26)".
- CSVs: `outputs/results/analyses/review_round3/` (all checks passed).
- Sets: MU-IU, LUM, UCSF-P.
- Bootstrap: patient-cluster, 1,000 draws, seed 20261026. E uses the detection seed 20261021; F uses the UCSF plan
  seed 20261025.

| Item | Value (95% CI) | Source (CSV) | Status |
|---|---|---|---|
| A. Agreement, MU-fixed medians (locked models' MU training-set medians); disagreement alone, S2 / S3 | LUM +0.222 (+0.102 to +0.337) / +0.115 (+0.049 to +0.190); UCSF +0.134 (-0.096 to +0.397) / +0.023 (-0.086 to +0.099); MU fold-held-out median +0.313 (+0.184 to +0.431) / +0.082 (+0.047 to +0.119) | A_agreement_mu_fixed.csv | EXPLORATORY |
| A. MU-fixed disagreement, AUC unflagged / flagged (LUMIERE) | 0.889 / 0.667 (flagged 60%); added 2026-10-28 from the CSV for the 3.4 sentence | A_agreement_mu_fixed.csv | EXPLORATORY |
| A. MU-fixed disagreement AND conformal {0,1}, S2 / S3 | MU +0.376 (+0.166 to +0.552) / +0.023 (+0.009 to +0.040); LUM +0.227 (+0.054 to +0.398) / +0.037 (-0.004 to +0.081); UCSF +0.024 (-0.162 to +0.322) / +0.023 (-0.028 to +0.076) | same | EXPLORATORY |
| A. Flagged share (MU-fixed disagreement); status changed vs own median | LUM 60%, 31% changed; UCSF 48%, 48% changed; MU 40% | same; run_info.json | EXPLORATORY |
| B. Combined set, alpha 0.2, coverage progression / non-progression (standard) | MU 0.819 (0.748-0.888) / 0.826 (0.731-0.908); LUM **0.767 (0.671-0.872)** / 0.943 (0.857-1.000); UCSF 0.966 (0.880-1.000) / **0.650 (0.511-0.791)** | B_class_conditional_coverage.csv | EXPLORATORY CIs (points PLANNED, conformal.csv) |
| B. Same, Mondrian | MU 0.868 / 0.729 (0.633-0.815); LUM 0.849 / 0.514 (0.392-0.642); UCSF 0.966 / 0.175 (0.062-0.308) | same | EXPLORATORY |
| B. Singleton share, progression / non-progression (standard) | MU 0.66 / 0.82; LUM 0.49 / 0.71; UCSF 0.69 / 0.60 | same | EXPLORATORY |
| C. log ET volume alone (raw, larger = progression) | MU-IU 0.622 (0.530-0.717); LUM 0.662 (0.563-0.751; 163 scans with ET, 68 / 95); UCSF 0.878 (0.793-0.948) | C_et_baselines.csv | EXPLORATORY |
| C. log ET ratio to the previous scan alone | MU-IU 0.488 (0.399-0.580); LUM 0.628 (0.532-0.722); UCSF 0.822 (0.707-0.930). With a previous scan only: MU 0.486 (62 / 46), LUM 0.633 | same | EXPLORATORY |
| D. Combined score at the MU median: sensitivity / specificity | MU (OOF median) 0.787 (0.705-0.872) / 0.712 (0.614-0.813); LUM (locked T, MU median 0.363) 0.890 (0.817-0.959) / 0.495 (0.357-0.636); UCSF (A-T, 0.363) 1.000 (1.000-1.000) / 0.175 (0.061-0.297); called positive 50% / 66% / 90% | D_operating_point.csv | EXPLORATORY |
| E. Ladder middle step I_pure - I_scan (MU-IU, paired) | **+0.050 (-0.003 to +0.106)**; within phase -0.003 (-0.095 to +0.080) | E_ladder_contrasts.csv | EXPLORATORY |
| F. Locked combined calibration, slope / O/E | LUM T 1.45 (0.85-2.54) / 0.97 (0.81-1.14); UCSF A-T 3.29 (1.96-6.28) / 0.72 (0.55-0.91) | F_calibration.csv; UCSF = ucsf/locked/calibration.csv | LUM EXPLORATORY; UCSF PLANNED secondary |

Prose cautions:
- **MU log ET.** MU-IU log ET is 0.622. UCSF_AUDIT.md's 0.635 is for another MU row set; use 0.622 beside Fig 2's
  MU-IU bars.
- **"Each step raised AUC".** Mismatch 8 is now resolved: the middle step's CI includes 0, so do not write "each step
  raised AUC" with CI support.
- **A threshold fixed on MU does not transfer.** At UCSF it calls 90% of scans positive.
