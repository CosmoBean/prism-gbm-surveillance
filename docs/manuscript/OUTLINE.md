# Manuscript outline (2026-10-15, PRISM-paper framing)

**Framing (decided by the user, 2026-10-15).** This is the PRISM paper. PRISM (Post-treatment Response Intelligence
and Surveillance Monitor) is the authors' own, unpublished system (first version: `report/original_prism_report/`).
PRISM = the full multimodal pipeline (clinical + treatment phase + volumes + radiomics + deep encoder), every branch
ablated honestly; the deployed configuration is the clinical + treatment-phase **core model** with the imaging branches
as optional modules. The report generator is kept and rebuilt on the per-scan audit record (grounded; every statement
traceable to a record field), with a faithfulness evaluation (results pending from the report-generator work stream).
The original 0.80 single-split result is "our initial single-split evaluation": a transparent self-correction.

Source of truth: `paper/main.tex`, `paper/supplement.tex`. Number sources: `paper/SOURCE_MAP.md`. Figures:
[FIGURES.md](FIGURES.md).

**Title.** *PRISM: an auditable, phase-aware pipeline for post-treatment glioma surveillance — rigorous evaluation of
imaging, clinical and treatment-course information* (alternatives in [DRAFT_NOTES.md](DRAFT_NOTES.md)).

**One-sentence message.** PRISM predicts documented progression within 120 days of a post-treatment glioma MRI and
returns an audit record and a grounded clinician report; its initial 0.80 came from a favourable split (composition,
phase of care, a treatment-date leak in a comparator), and under rigorous evaluation its clinical + treatment-phase
core reaches about 0.70 while radiomics and deep imaging branches add nothing measurable.

## Terminology (defined once in the text)
- **PRISM v1** — the initial pipeline: calibrated radiomics LR + random-weight SwinUNETR-style encoder + late-fusion
  MLP + agentic report (RANO rules, concordance, GPT-4.1-mini).
- **PRISM's initial radiomics model** (was "PRISM report model"); **initial radiomics pipeline** (its feature
  re-selection per split); **initial PRISM fusion pipeline** (v1 fusion MLP).
- **Our initial evaluation split** (was "PRISM report split"; seed 62 of v1's split search).
- **Core model** = clinical + timing + as-of-scan treatment, ridge (= "baseline" in tables, figures, Supplement).
- Never "published" for PRISM.

## 1. Introduction
1. Clinical problem: surveillance MRI, pseudoprogression, documented progression as a pragmatic endpoint; need for a
   checkable probability.
2. Imaging literature on the task; Christodoulou 2026 (separate work), Rai 2026; none returns a checkable account.
3. Known problems: split variance, external drops, missing clinical comparators.
4. Phase of care as an unrecognised confounder; leakage of future treatment.
5. PRISM's design goals: prediction, interpretability, auditable clinician report; PRISM v1 and our initial split.
6. Contributions: (i) rebuilt PRISM (as-of inputs, ablatable branches, audit record, grounded report); (ii)
   self-correction of the initial evaluation; (iii) branch-by-branch ablation, internal/external/third cohort, phase
   of care as driver; (iv) audit layer and report generator against pre-specified criteria.

## 2. Methods
2.1 **PRISM: architecture and data flow** (Fig 5A) — five branches, one ridge predictor, audit layer, report
generator; PRISM v1 and what changed (legacy reproduction numbers); deployed configuration.
2.2 Study design and reporting · 2.3 Data sources · 2.4 Index scans and outcome · 2.5 Predictors: PRISM's input
branches · 2.6 Initial radiomics model, initial evaluation split, as-of correction · 2.7 Split variance · 2.8 Repeated
CV and component ablation · 2.9 Phase of care · 2.10 Label, positive controls, re-segmentation · 2.11 External and
diffusion · 2.12 Audit layer · 2.13 **Report generator and faithfulness evaluation** [PENDING details] · 2.14 Further
analyses and software.

## 3. Results
3.1 Cohorts · 3.2 **PRISM's initial single-split result and why it misled** (re-scored split; treatment-date leak;
composition and phase of care) · 3.3 Split variance (500 splits) · 3.4 **Component ablation** (clinical → timing →
treatment; radiomics branch; deep branch; credit ≠ value) · 3.5 Phase of care · 3.6 Label, positive controls,
segmentation · 3.7 External (LUMIERE) and CFB-GBM · 3.8 Calibration and utility of the core model · 3.9 Audit layer
(P1 met, P2 not met, four problems found) · 3.10 **Report generator** [PENDING: REPORT_AGENT results].

## 4. Discussion
Summary of four findings → **What PRISM contributes** (auditable, phase-aware, honest about uncertainty; no triage
benefit) → **Why our initial evaluation misled** (reporting rules) → Phase of care as a confounder → **What imaging did
not add, and why** (incl. credit ≠ value; imaging kept as optional modules) → External validity → Comparison with other
work → Limitations (incl. report faithfulness ≠ clinical usefulness) → Conclusion.

## Figures and tables
1. PRISM's initial single-split result (panel labels still say "PRISM report"; regenerate).
2. Our initial evaluation split among 500 splits (same).
3. Component ablation: ladder, ΔAUC forest, SHAP shares.
4. Phase of care.
5. PRISM: (A) architecture `fig5a_architecture.pdf`, (B) example grounded report `fig5a_example_report.pdf` (both from
   the report-generator work stream; red placeholder via `\IfFileExists` until they exist), (C) risk–coverage
   `fig5_system_risk_coverage.png`.
Table 1 cohort; Table 2 single split vs 500 splits vs CV (rows renamed); Table 3 imaging branches vs core model.
Supplement: S7 now also covers PRISM v1's encoder and fusion components; new S19 report generator [PENDING].
