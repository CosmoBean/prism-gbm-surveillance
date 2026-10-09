# PRISM v2 — Pipeline Review, Real Gap, Comparative Methods and Paper Plan

2026-10-09. Based on `prism/` at `3009e95`, results in `docs/results/` (C1–C3), [LITERATURE.md](../reproduction/LITERATURE.md), and new checks run for this review (§2). Target: a regular journal (impact factor ≈ 2–4).

---

## 1. Current pipeline

```
MU-Glioma-Post (203 pts, 596 timepoints, T1/T1c/T2/FLAIR, refined 4-label masks, EMR clinical sheet)
  │
  ├─ Cohort (prism/cohort.py): pre-progression scans, before late treatment, image+mask+date present
  │     → 314 scans / 157 patients (grade 4: 253 / 128)
  ├─ Outcome: progression within H = 90/120/180 d of the scan; verified negatives; censored scans flagged
  ├─ Folds (prism/folds.py): 5 × 5 repeated, patient-grouped, stratified
  │
  ├─ Features
  │    clinical  (age, sex, IDH/MGMT with explicit unknown)
  │    timing    (days since diagnosis / RT end, ≤12-wk post-RT, visit index)
  │    treatment (RT given/dose/fractions/hypofractionation/start/duration, chemo, surgery day, biopsy-first, prior tumour)
  │    volumes + morphology (prism/measurements.py: ET/NETC/SNFH/RC volumes, multifocality, ET–cavity proximity, intensity vs normal brain)
  │    delta     (vs prior scan and nadir, growth rate, ≥40 % ET flag)
  │    radiomics legacy (2 grey levels) and corrected v2 (prism/radiomics_v2.py: per compartment, 32 bins, ICC filter)
  │
  ├─ Learners: ridge logistic (penalty by inner grouped CV); regularised gradient boosting; stacking for radiomics
  ├─ Formulations (prism/formulations.py): naive / verified / IPCW / discrete-time landmark hazard
  └─ Evaluation (prism/metrics.py): IPCW AUC(H), IPCW Brier, O/E, calibration slope, patient-cluster bootstrap,
                                    paired ΔAUC, nested selection, label-permutation control
```

### Rating

| Component | Grade | Why |
|---|---|---|
| Cohort definition | **B** | Explicit, logged, matches legacy; but inherits rules never clinically reviewed and is driven by dataset timepoint sampling (§2 L3) |
| Outcome / label | **C** | Censoring handled, but the label is coupled to the surveillance schedule and partly to detection rather than forecasting (§2 L1–L2) |
| Features | **B−** | Broad and interpretable; treatment features needed as-of-scan masking (fixed in check, not yet in code); radiomics unharmonised |
| Models | **B** | Appropriate for n ≈ 250; boosting config chosen after seeing C2; no glass-box/survival model finalised |
| Evaluation | **B+** | Far stronger than the original (repeated grouped CV, IPCW, cluster bootstrap, nested search, permutation control); weakened by many analyses on the same folds and no external data |
| Reproducibility | **B** | One-command scripts, unit tests, committed results; outputs on wipe-prone storage; seed/split provenance of legacy model lost |
| Clinical relevance | **C+** | Forward-risk framing is sensible, but what the model "predicts" partly reflects when the next scan was booked |
| **Overall** | **B− as a research pipeline; C as a clinical tool** | Rigorous enough to support an evaluation/analysis paper; not a deployable predictor |

---

## 2. Issues

### Label and task definition (most important)

| # | Issue | Evidence | Consequence | Fix |
|---|---|---|---|---|
| L1 | **Progression is usually declared at the next MRI** | 59/99 positive progression dates fall within 3 d of a later MRI in the dataset | "Progression within 120 d" largely means "next scan within 120 d *and* it shows progression": label depends on scan scheduling (which itself reflects clinical suspicion) | Model *time to next-scan progression* with the inter-scan interval as part of the design; sensitivity: condition on next-scan interval; report interval-stratified results |
| L2 | **Part of the task is detection, not forecasting** | 15 % of positives progress ≤ 14 d after the index scan; 15/99 positives are clinical-only progression (type 2) | Some "predictions" detect change already visible; clinical-only progressions may have no imaging correlate | Exclude ≤ 14 d gaps as sensitivity; imaging-only (types 1/3) vs any-progression endpoints |
| L3 | **Dataset timepoints are a sample of clinical scans** (≤ 6 per patient) | Timepoints are "follow-up MRIs" selected by the dataset curators | Visit index, prior-scan deltas and nadir are relative to *included* scans, not the true clinical history | State as limitation; avoid visit index as predictor |
| L4 | Censoring evidence uses any dated clinical event | e.g. therapy start dates | Mostly reasonable; therapy dates can be planned rather than observed follow-up | Sensitivity with MRI/death-only follow-up |

### Leakage and timing

| # | Issue | Evidence | Status |
|---|---|---|---|
| T1 | Treatment features used post-scan information | 29/215 scans before RT end, 23 before RT start | **Checked: not inflating.** As-of-scan masking *raises* CV AUC (grade 4 ridge 0.694 → 0.732) because "RT not yet finished" is itself informative. Code must adopt as-of-scan features |
| T2 | Head-to-head on the PRISM report split is not fully independent | Our configurations were designed from repeated CV that included those 30 patients | Report as "same split, configurations fixed from CV"; the clean comparison is external (LUMIERE) |

### Evaluation

| # | Issue | Fix |
|---|---|---|
| E1 | Many analyses (C1–C3, ~200 configurations) on the same folds → forking-paths optimism | Pre-register final models; one locked external test; report nested estimates as primary |
| E2 | OOF averaged over 5 repeats before AUC (small ensemble effect) | Report per-repeat mean ± SD as primary (already computed) |
| E3 | Bootstrap CIs on fixed OOF predictions ignore training variability | Add repeat-level spread; or bootstrap the whole pipeline for key comparisons |
| E4 | Boosting hyperparameters chosen after observing overfit in C2 | Tune in inner CV or fix a priori and state it |

### Features and data

| # | Issue |
|---|---|
| F1 | 64 % of FLAIR and ~all T2 acquired 2D (~5 mm) → interpolated texture; no harmonisation across 1.5 T / 3 T |
| F2 | 14 % of compartment features missing (absent compartments) — imputed by median |
| F3 | IDH/MGMT largely unknown; race not auditable (94.6 % White); single centre, 97.5 % Siemens |
| F4 | 6 patients with timepoint ↔ clinical-day mismatches not reconciled; legacy `LABEL_MAP` still wrong in `radiomics_tools` |

---

## 3. Results to date (one table)

| Model | Repeated CV, grade 4 | Repeated CV, all gliomas | PRISM report split (all gliomas) |
|---|---|---|---|
| PRISM report radiomics model (legacy, as shipped) | — | ≈ 0.70 honest re-estimate | 0.802 |
| Clinical + timing + treatment, ridge (as-of-scan) | 0.732 | 0.756 | 0.889 |
| Clinical + timing + treatment, boosting (as-of-scan) | 0.726 | 0.744 | 0.885 |
| + best radiomics (nested choice over 70 configs) | Δ −0.009 | Δ +0.013 | ≤ +0.005 |
| Label-permutation control | ≈ 0.50 | ≈ 0.50 | — |

---

## 4. Comparative methods for this problem (post-treatment glioma / GBM)

| Family | Representative work | Data needs | Reported performance | Applicable to MU? | Expected value here |
|---|---|---|---|---|---|
| Radiomics + ML, single scan | Christodoulou 2026 (MU, LightGBM + Platt, AUC 0.80 single split); our C3 | T1c/FLAIR + masks | 0.70–0.80 internal | Yes (done) | Little over clinical + treatment |
| Volume / volumetric response | Kickingereder 2019 (HD-GLIO, volumetric TTP); Chang 2019 (AutoRANO); Rai 2026 (MU, volume label, nested CV 0.728) | Serial masks | Volumetric > bidimensional for OS surrogacy | Yes (masks exist) | Strong, simple baseline; already in our measurements |
| Delta / habitat radiomics | Moon 2025 (CBV/ADC habitats, prospective); Li 2025 (intra/peri-tumoral habitats) | Mostly perfusion/diffusion | 12-mo AUC 0.76 | Partly (no DWI/DSC) | **Our legacy finding suggests a conventional-MRI habitat signal** |
| PsP vs true progression classifiers | Jang 2018/2020, Kim 2019, Gomaa 2025, Zheng 2026 | Often perfusion/diffusion, pathology/RANO labels | Internal 0.75–0.95, external 0.65–0.80 | No PsP labels in MU | Context only |
| Serial-scan deep learning | Tak 2025 NEJM AI (temporal SSL, paediatric, code); Chen 2026 (pre/post-op siamese, LUMIERE → RHUH 0.76); Guo & Mirzaei 2026 (11 architectures, Burdenko ~0.70) | Many scans/patient | 0.70–0.89 | Weak (median 2 labelled scans/patient) | Low |
| Foundation encoders | BrainIAC, BrainMVP, BM-MAE, BiomedCLIP 2.5D; Hollet 2026 benchmark (radiomics + TabPFN > image FMs for IDH) | Images | Glioma IDH 0.6–0.85 frozen | Yes (GPU) | Low; useful as a negative control (C4) |
| Survival / landmark dynamic prediction | van Houwelingen landmarking; discrete-time hazard; LTSA, tdCoxSNN | Times + censoring | — | Yes (done, C1) | Correct formulation; no AUC gain |
| Clinical/treatment nomograms | Standard prognostic models (age, MGMT, EOR, RT schedule) | Clinical sheet | — | Yes | **Strongest single component here** |

**Takeaway:** for conventional-MRI, single-centre post-op surveillance at n ≈ 150, the literature and our data agree: image features add little over clinical/treatment information; reported AUCs ~0.80 come from single splits without treatment-aware baselines.

---

## 5. Overall architecture — final proposal and per-component plan

```
         ┌──────────── as-of-scan information only ────────────┐
scan_t → │ A. Clinical + treatment state (age, MGMT/IDH+unknown, RT given/finished, schedule, chemo, time since RT) │
         │ B. Burden: compartment volumes (ET, NETC, SNFH, RC)                                               │
         │ C. Change: Δ prior / Δ nadir where a prior exists (+ indicator)                                   │
         │ D. Habitat: within-lesion bright/dark spatial pattern (explicit, scanner-invariant)              │
         │ E. (control) corrected radiomics score; frozen encoder score                                       │
         └──────────────────────────────────────────────────────┘
                    ▼
   Primary model: penalised logistic / discrete-time hazard (glass box), nested patient-grouped CV
                    ▼
   Outputs: calibrated 120-d risk · additive contributions by block · abstain if early post-RT / OOD
                    ▼
   Evaluation: IPCW AUC, calibration, DCA, subgroups, label-sensitivity (L1/L2), locked LUMIERE test
```

| Block | Role | Status | Work left |
|---|---|---|---|
| A Clinical + treatment | Baseline and main signal | Built; as-of-scan masking verified in a check | Move as-of-scan logic into `features.py`; ablate each sub-group |
| B Burden | Simple imaging baseline | Built | — |
| C Change | Surveillance-with-history signal | Built | Separate analysis on scans with a prior (n = 158) |
| D Habitat | Candidate positive imaging finding | Implicit only (legacy 2-level texture) | Design explicit habitat features (Otsu/2–3-cluster partition of ET/lesion; fraction, fragmentation, rim thickness); test as in C3 |
| E Radiomics / deep | Negative controls for "does imaging add?" | Radiomics done; deep pending | Frozen encoder score (oc1 GPUs), stacked |
| Model | Glass box | Ridge/hazard built | Final pre-registered model; EBM optional |
| Trust | Calibration, abstention, subgroups | Partial | Subgroups, DCA, early-post-RT handling |
| External | Transport | Not started | LUMIERE download, segmentation, label harmonisation |

---

## 6. The real gap and the paper

### What is *not* a viable claim
- A better image-based progression predictor on MU-Glioma-Post (the data do not support it).
- Pseudoprogression discrimination (no PsP labels).

### The gap we can fill (supported by our results + literature)
1. **No rigorous re-evaluation of MRI-based progression prediction on MU-Glioma-Post exists.** Published/available models report ~0.80 on single splits without treatment-aware baselines.
2. **No study quantifies how the surveillance schedule shapes the "progression within H days" label** (L1) — relevant to every scan-level progression dataset where progression is declared at the next MRI.
3. **No study tests whether conventional post-op MRI adds to clinical + treatment information** for short-term progression under censoring-aware, patient-clustered evaluation.

### Recommended paper (regular journal, IF ≈ 2–4)
*"How much does post-operative MRI add to short-term progression prediction in glioblastoma? A censoring-aware re-evaluation on MU-Glioma-Post"*

| Section | Content | Status |
|---|---|---|
| Cohort & endpoint | Flow diagram, censoring repair, label-schedule coupling (L1), detection vs forecasting (L2) | Mostly done; L1/L2 sensitivity to run |
| Baselines | Clinical, timing, treatment (as-of-scan), volume | Done |
| Imaging | Volumes, change, habitat, corrected vs legacy radiomics, frozen encoder | Habitat + encoder to run |
| Evaluation | Repeated grouped CV, nested, permutation, IPCW, calibration, DCA, subgroups | DCA/subgroups to run |
| Replication | PRISM report split head-to-head; Christodoulou-style LightGBM + Platt re-implemented | LightGBM re-implementation to run |
| External | LUMIERE locked test (optional but strengthens to a solid IF 3–4 paper) | Not started |
| Reporting | TRIPOD+AI, CLAIM 2024, METRICS self-assessment | To do |

Candidate journals (check current scope/IF before submission): *BMC Medical Imaging*, *Diagnostics*, *Frontiers in Oncology*, *Cancers*, *Neuro-Oncology Advances*, *Journal of Imaging Informatics in Medicine*, *European Journal of Radiology Artificial Intelligence*.

### Minimum work to a submittable manuscript
1. Fix as-of-scan features in code; re-run C2/C3 tables (CPU, hours).
2. L1/L2 label sensitivity (interval-conditioned, ≤ 14 d exclusion, imaging-only progression) (CPU, hours).
3. Explicit habitat features (CPU, a day).
4. Christodoulou-style LightGBM re-implementation on both evaluations (CPU, hours).
5. Subgroups + DCA + calibration figures (CPU, a day).
6. Optional: frozen-encoder control on oc1 (GPU, a day); LUMIERE external test (several days).
