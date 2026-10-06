# PRISM v2 — Architecture Improvements and Research Contributions

Prepared 2026-10-05. Synthesises [PUBLICATION_PLAN.md](PUBLICATION_PLAN.md), [reproduction/LITERATURE.md](../reproduction/LITERATURE.md), [reproduction/AUDIT.md](../reproduction/AUDIT.md), and new data checks (§1). Purpose: decide *what* to build and *what we can claim* before executing the data-layer fixes.

---

## 1. Facts that constrain the design (checked on the data, 2026-10-05)

| Fact | Evidence | Design consequence |
|---|---|---|
| **Radiomics texture is computed on 2 gray levels** | Within-lesion z-score + `binWidth: 25` → every lesion has exactly 2 levels (24/24 scans, T1c and FLAIR); original-feature GLCM joint entropy ≤ 2 bits. 31/48 shipped features are texture-class. Fixed bin count 32 → ~30–32 levels | Current "texture" ≈ above/below lesion mean (shape/size proxy). Re-extract with brain-referenced normalisation + fixed bin count before any radiomics claim |
| **28% of negatives are unverifiable at 120 d** | H=120: 99 positives, 156 verified negatives, **60 censored** (all never-progressors). H=90: 55; H=180: 67 | Binary label is biased → censoring-aware formulation is justified, not cosmetic |
| **Half the scans have a prior scan** | 158/315 (50%) have an earlier MRI; median 2 labeled scans/patient (84 patients ≥ 2) | Δ-features feasible for half the cohort (need "no prior" handling); heavy sequence models (LTSA, Tak-style) under-powered on labels alone |
| **One third of scans sit in the pseudoprogression window** | 104 scans ≤ 12 weeks after RT end (RT date known for 215) | Must be flagged/stratified (RANO 2.0); likely label-noise concentration |
| **Cohort is not GBM-only** | 217 GBM, 50 astrocytoma, 35 diffuse glioma, … (grade 4: 254, grade 2: 51) | Primary analysis GBM/grade 4; others as stratum |
| **Deep image features add nothing so far** | Random encoder ≈ chance; BraTS SwinUNETR fine-tuned → image-only test AUC ≈ 0.64; fusion Δ CI spans 0 | Image branch must be justified by a controlled comparison, not assumed |
| **Global pooling of encoder features collapses** | Scan-to-scan corr ≈ 1.0 for GAP; lesion-masked pooling restores variation | Compartment-resolved pooling is a design requirement (and a reportable finding) |

---

## 2. Current architecture (v1) → proposed (v2)

| Layer | v1 (as shipped) | Problem | v2 |
|---|---|---|---|
| Endpoint | Binary "progression ≤ 120 d", censored scans labelled 0; single 30-patient split | Biased labels; test reused | **Landmark forward risk**: each scan is an index date; P(progression ≤ H \| scan, history); censoring handled; repeated nested patient-grouped CV |
| Imaging evidence | Whole-lesion radiomics (2 gray levels); random 48-d encoder, GAP | Degenerate texture; no image signal | **Three compartment-resolved evidence streams** (ET, NETC, SNFH, RC, peri-cavity ring): (a) measurements/concepts, (b) corrected radiomics, (c) frozen foundation-encoder tokens pooled per compartment |
| Time | None (single scan) | Ignores trajectory | **Past-only Δ features** (prior, nadir, Δt, days since RT); optional small time-aware aggregator |
| Clinical | Raw codes incl. undocumented "not tested" | Missingness shortcut | Codebook with explicit `unknown`; shortcut test with/without |
| Fusion | MLP, test-loss checkpoint, 0.48 cutoff | Leakage; no gain | **Penalised stacking / single additive model** on the streams; ladder of nested models |
| Trust | Unvalidated SHAP; confidence words | Not faithful/validated | **Glass-box concept model** + grouped explanations with stability/faithfulness tests; **calibration + patient-level conformal abstention**; early-RT-window referral |
| Report | Probability-proxy "RANO", future visits leak | Misleading | (Deferred) as-of-time, source-linked report; measurement-based volumetric flag labelled indicative |

### v2 diagram

```
scan_t (T1c, FLAIR [+T1, T2]) + masks (ET/NETC/SNFH/RC)        clinical (explicit unknowns) + timing (days since RT, ≤12-wk flag)
        │
        ├─► (a) Concepts: compartment volumes, ratios, cavity-adjacent ET, intensity vs NAWM ─┐
        ├─► (b) Corrected radiomics per compartment (brain z-score, fixed bins, stable)  ─────┤
        └─► (c) Frozen encoder → tokens pooled per compartment (+ random-init control) ───────┤
                                                                                             ▼
history ≤ t ──► Δ prior / Δ nadir / Δt (past-only) ───────────────────────────►  Landmark discrete-time hazard
                                                                                 (penalised; model ladder M0→M3)
                                                                                             │
                                               calibrated P(prog ≤ H) ◄──────────────────────┤
                                               additive concept explanation ◄────────────────┤
                                               conformal abstain / early-RT referral ◄───────┘
```

---

## 3. Candidate contributions

Novelty statements are "not found in our searches" (see LITERATURE.md), not proofs of absence.

| # | Contribution | Why it is new / needed (literature) | Evidence we must produce | Effort | Risk |
|---|---|---|---|---|---|
| **C1** | **Censoring-aware landmark forward-risk endpoint**, with a label-definition sensitivity analysis (naive-binary vs verified-only vs IPCW vs landmark; H = 90/120/180; ≤12-wk RT window) | GBM-recurrence radiomics reviews: single timepoint, binary endpoints, no time-to-event; baseline paper is single-split binary; Vock 2016 / van Houwelingen 2007 never applied to post-op GBM imaging | Table: same features, four label/formulation choices → AUC(120 d, IPCW), calibration; quantified bias from censored negatives | Low (CPU) | Low |
| **C2** | **Compartment-resolved longitudinal concepts incl. resection cavity** in a glass-box model | MU uniquely ships refined RC masks; no cavity-compartment time-varying covariate study found; field favours interpretable-by-design (Rudin 2019) | Concept model vs radiomics vs deep, same folds; does it match? which concepts drive risk? | Medium (CPU) | Medium (signal size) |
| **C3** | **Radiomics discretisation audit** — degenerate 2-level texture under within-lesion z-score + fixed bin width; effect of correction | IBSI / Carré 2020 give the rule, but impact on this endpoint unquantified; directly relevant to MU-based radiomics | Gray-level table; original vs corrected radiomics performance; "texture beyond concepts?" | Low | Low (supporting result) |
| **C4** | **Does deep imaging add? — compartment-pooled frozen foundation-encoder benchmark** (BraTS SwinUNETR, BrainSegFounder, BrainMVP/BM-MAE, BiomedCLIP 2.5D, random-init control) incl. global-vs-compartment pooling ablation and site-fingerprint check | No FM benchmark for post-op progression; pooling collapse documented only in 2D CXR (Muthyala 2026); site encoding (Rahbar 2026) | Linear-probe + stacking ΔAUC with clustered CIs; pooling ablation; scanner-decodability | Medium (GPU, mostly feature extraction) | Likely neutral/negative — still publishable if rigorous |
| **C5** | **Trust layer: shortcut/bias audit + abstention** — missingness-code shortcut, confounder-only model, subgroups (GBM vs non-GBM, MGMT unknown, 1.5 T vs 3 T, early-RT window), patient-level conformal deferral, explanation stability/faithfulness | Bias/shortcut auditing essentially absent in post-treatment glioma ML (PUBLICATION_PLAN B1); CLAIM 2024 item 31 | Audit tables; risk–coverage curves; explanation stability metrics | Medium | Low |
| **C6** | **Locked external validation on LUMIERE** (expert RANO per timepoint → PD within H) | No MU forward model externally validated | External AUC/calibration, transport analysis | Medium (download, segment, harmonise label) | Medium (endpoint mismatch) |
| C7 (stretch) | Temporal self-supervision (scan-order pretext, Tak 2025) on all 594 MU timepoints | Only paediatric precedent | Ablation vs frozen encoder | High | High |

**Recommended paper = C1 + C2 (+ C3 as an ablation) + C5 + C6**, with C4 as the deep-learning section. Working title (from PUBLICATION_PLAN, adapted): *"Censoring-aware, interpretable risk stratification for post-treatment glioblastoma surveillance from compartment-resolved serial MRI."*

---

## 4. Data layer required (what each contribution depends on)

| Task | Needed by | Notes |
|---|---|---|
| D1 Cohort builder + flow diagram (594 → eligible), GBM flag | all | One command; logs each exclusion |
| D2 Follow-up / censoring per scan (last MRI, death; last-contact if available) for H = 90/120/180 | C1 | Progressor negatives verified by progression date |
| D3 Codebook with explicit `unknown` for IDH/ATRX/MGMT/1p19q; reconcile 6 mismatched patients | C2, C5 | Removes missingness shortcut by construction; keep a "with codes" arm for the shortcut test |
| D4 Timing: days since RT end, ≤12-wk flag, visit index | C1, C5 | Audit/stratification variables first, predictors only if pre-registered |
| D5 Measurement table: ET/NETC/SNFH/RC volumes, ratios, cavity-adjacent ET, intensities vs NAWM; Δ prior / Δ nadir **past-only**; fix `LABEL_MAP` (1=NETC, 2=SNFH, 3=ET, 4=RC) | C2 | Unit tests: nadir uses past only; cavity excluded from tumour burden |
| D6 Corrected radiomics: brain-mask z-score (or WhiteStripe), fixed bin count (32), no second N4, per compartment, mask-perturbation stability (ICC) | C3 | ~45 min CPU per extraction |
| D7 Folds: repeated (5×) patient-grouped nested CV, stratified by outcome & GBM; committed `folds.csv` | all | Replaces single 30-patient test |
| D8 Acquisition metadata (scanner, field strength, 2D/3D) | C4, C5 | From TCIA/DICOM headers or descriptor tables |
| D9 LUMIERE download + label harmonisation | C6 | Start in parallel |

## 5. Fastest path to results

| Step | Output | Compute |
|---|---|---|
| 1. D1–D5, D7 + evaluation harness (clustered bootstrap, IPCW AUC(H), calibration, DCA) | Frozen cohort, folds, concepts | CPU, days |
| 2. **First results table**: M0 confounder / clinical / volume / RANO-style rule, M1 concept glass box; C1 label-sensitivity table | Paper skeleton (C1 + C2) | CPU |
| 3. D6 + M2 corrected radiomics (+ original as C3 ablation) | "Does texture add beyond concepts?" | CPU |
| 4. M3 compartment-pooled frozen encoders (C4); stacking | "Does deep imaging add?" | GPU ~1 day |
| 5. C5 trust layer; C6 LUMIERE locked evaluation | Audit + external tables | CPU/GPU |

## 6. Decisions needed before starting

1. **Primary population**: GBM/grade 4 only (recommended) or all gliomas with stratum?
2. **Primary horizon** H = 120 d (continuity) with 90/180 sensitivity? **Primary formulation**: landmark discrete-time hazard (recommended) vs IPCW-binary?
3. **Primary sequences**: T1c + FLAIR (transportable to LUMIERE/CFB-GBM) with 4-sequence as ablation?
4. **External cohort**: LUMIERE primary (recommended); CFB-GBM only for proxy endpoints?
5. **Scope**: report agent deferred to future work (as in PUBLICATION_PLAN)?
