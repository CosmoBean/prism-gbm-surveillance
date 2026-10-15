# Draft notes (2026-10-15; PRISM-paper framing pass appended)

LaTeX (paper/) is the source of truth from 2026-10-15; this markdown is a frozen snapshot.

Files: [DRAFT.md](DRAFT.md) (main text), [SUPPLEMENT.md](SUPPLEMENT.md), Table 2 history rows appended to
[figures/table2_single_split_vs_cv.md](figures/table2_single_split_vs_cv.md) / `.csv`, Figure 5 basis copied to
`figures/fig5_system_risk_coverage.png` (from `outputs/results/analyses/audit_system/risk_coverage.png`).

## Framing pass (2026-10-15, PRISM paper)

The manuscript was re-framed as **the PRISM paper** (user decision): PRISM is the authors' own, unpublished system;
the full multimodal pipeline is presented and every branch ablated; the deployed configuration is the clinical +
treatment-phase **core model** with imaging branches as optional modules; the report generator is rebuilt on the
audit record; the original 0.80 is "our initial single-split evaluation" (self-correction). Terminology and new
structure: [OUTLINE.md](OUTLINE.md). Changes:

- `macros.tex`: new title and running title. `main.tex`: abstract, key points, clinical relevance, introduction
  (problem → PRISM design goals → contributions), new §2.1 *PRISM: architecture and data flow* (methods renumbered:
  old §2.1–2.11 → §2.2–2.12, new §2.13 report generator, old §2.12 → §2.14), results re-titled (§3.2 initial
  single-split result and why it misled; §3.4 component ablation; new §3.10 report generator), discussion
  restructured (what PRISM contributes; why our initial evaluation misled; what imaging did not add), conclusion,
  declarations ("PRISM versions"), Table 2/3 row names, Figure 1–5 legends; Figure 5 now has panels A/B (from
  `fig5a_architecture.pdf`, `fig5a_example_report.pdf`, red placeholder via `\IfFileExists` until they exist) and C
  (risk–coverage).
- `supplement.tex`: header definitions, S7 retitled and extended with PRISM v1 encoder/fusion components, new S19
  report generator (placeholder), S17 checklist cross-references renumbered to the new methods numbering, all
  "PRISM report" wording replaced.
- `SOURCE_MAP.md`: terminology, renumbering note, rows for the v1 component numbers and the report generator.

**Numbers.** No number was removed. New decimals in main.pdf: 0.8006 and 0.8043 (v1 fusion MLP vs its radiomics
input, v1's own scoring; `legacy/reproduction/AUDIT.md` fault 3, `README.md` §1). New in supplement S7 (same
sources, `FINDINGS.md` §2–3): encoder alone ≈ 0.50, linear probe 0.55 / 0.62, 0.48 threshold, BraTS SwinUNETR rebuild
image-only 0.64–0.65 and late fusion 0.790–0.809. All other decimals are unchanged (checked by diffing the decimal
sets of the old and new PDFs and `main.tex`). These legacy numbers are not in `docs/results/`.

## Title options

1. **PRISM: an auditable, phase-aware pipeline for post-treatment glioma surveillance — rigorous evaluation of
   imaging, clinical and treatment-course information** (current).
2. PRISM: auditable risk prediction at post-treatment glioma surveillance MRI, and what imaging, clinical and
   treatment-course information each contribute.
3. Phase of care, not MRI texture: development, self-correction and external evaluation of PRISM, an auditable
   pipeline for glioma surveillance.
4. (Shorter, for journals with a title limit) PRISM: an auditable, phase-aware model for post-treatment glioma
   surveillance.

## Report-generator results added (2026-10-15)

All `[PENDING: REPORT_AGENT results]` placeholders replaced from `docs/results/REPORT_AGENT.md` and
`outputs/results/analyses/report_agent/summary_eval.csv`: abstract (last results sentence), §2.13 rewritten to match
what was built (record + tier + indicative volumes; deterministic sections + local Qwen3.8-27B summary with cited
keys; lexical checker; arms A/B/C; frozen plan; stress test; kept/dropped v1 components), §3.10 (primary 236/249 =
0.948 [0.913, 0.969] vs target ≥ 0.95, not met by one report; 13 failures = horizon field not cited; 0/269 flags
omitted; no forbidden content; arm B 171/249, A − B +0.261 [+0.197, +0.328], forbidden 100%, 48/269 flags omitted;
arm C 243/249, forbidden 2.8% (1 real); stress A 27/30, B 17/30, C 28/30; 15 reports read), Discussion and
Limitations (lexical checker, one cohort/repeat, no clinician evaluation), Figure 5 (A full width, B + C side by
side; legend describes the actual panels). Supplement S19 now holds the full account with Tables S26 (arms) and S27
(stress). Every new number was checked against REPORT_AGENT.md; the only tokens not literally in it are "2,000"
and "1,024" (written "2000"/"1024" there) and the values printed inside the Figure 5 panels. The coordinator's
Figure 1–4 relabelling (HEAD 65d2e26) was kept.

## Word counts

Counted with a whitespace tokenizer on the LaTeX source after removing comments, commands, citations and labels,
headings excluded (`wc_tex.py` in the session scratchpad). "Before" = the manuscript before the PRISM reframing,
same counter.

| Part | Before reframing | Now | Target |
|---|---|---|---|
| Abstract (incl. five bold labels; 299 without) | 300 | 304 | ≤ 300 |
| Key points + clinical relevance statement | 210 | 229 | — |
| 1. Introduction | 809 | 891 | ~900 |
| 2. Methods | 2,093 | 3,003 | ~2,200 |
| 3. Results | 2,279 | 2,691 | ~2,200 |
| 4. Discussion (incl. limitations, conclusion) | 1,512 | 1,786 | ~1,500 |
| **Main text (Introduction to Discussion)** | **6,693** | **8,371** | 5,500–7,000 |
| Declarations | 123 | 144 | — |
| Tables 1–3 (with captions) | 898 | 922 | — |
| Figure legends 1–5 | 595 | 707 | — |
| Supplement (body) | 9,145 | 10,884 | — |

Pages: main.pdf 30 → 34, supplement.pdf 34 → 37.

**The main text is about 1,400 words over the upper target.** Candidates to move to the Supplement (S19 already holds
the full report-generator account): §2.13 kept/dropped v1 components and checker details (~200 words), §3.10
comparison arms and stress test (keep one sentence each, ~200), §2.6 second paragraph (as-of history), §2.12
audit-record details (keep P1/P2), §3.2 leak-history paragraph, §3.8, "Comparison with other work".

## Open placeholders

- Declarations: ethics, funding, competing interests, data availability, code link; **"PRISM versions"**: who wrote
  the v1 report and whether to cite it. Author list and affiliations.
- Supplement S17: TRIPOD+AI 5b, 22, CLEAR 53–58. Supplement S16: code release and tag; supplementary figure export.
- No `[PENDING: REPORT_AGENT results]` remains. Figure 5 panels A/B exist; the `\IfFileExists` fallback stays in the
  source but is not triggered.
- Report generator open issues to decide: whether to test the obvious horizon-citation fix on fresh records (another
  CV repeat) before submission; whether to add TRIPOD-LLM items.

## [CHECK] items (citations not in the verified literature files, or flagged unverified there)

1. **Rai (2026)** — "repo, unverified (this pass)" in `COMPARABLE_RESULTS.md`; cited in Introduction and Discussion (0.728).
2. **Kocak et al. (2023), CLEAR** — reference taken from `CHECKLIST_CLEAR.md`, not from the literature files.
3. **Cox et al. (2024), BrainSegFounder** — DOI from `DEEP_FEATURES.md` only; title and authors incomplete.
4. **CFB-GBM dataset citation** (TCIA doi:10.7937/v9pn-2f72) — from `DATASETS.md`; the TCIA-recommended data citation and the arXiv:2608.17884 dataset paper should be added.
5. **Christodoulou et al. (2026) vs PRISM v1.** The draft treats them as separate work (Christodoulou: single-test-set
   AUC 0.80 on MU-Glioma-Post; PRISM v1 itself cites it as separate work). `comparison.md` notes an earlier repo reading of a
   30-patient / 96-scan test set for Christodoulou, which matches the PRISM split-search target (96 test scans). The
   authors must state the relationship (if any) explicitly; the draft makes no claim either way.
6. Methods references not in the literature files and therefore **not cited** (add if wanted, after verification):
   Vickers & Elkin 2006 (decision curves), Hilden & Gerds 2014 / Pepe 2015 (NRI critique), Riley/Van Calster/Collins
   2021 (R² from AUC), Mehrtens 2023 (conformal under shift), split-conformal and SHAP primary references, SwinUNETR.
7. Author lists in the reference list are shortened with "et al." as in the source files; complete with a reference manager.

## Decisions for the authors

- **Target journal** and article type (e.g. a radiology-AI or neuro-oncology methods journal); this fixes word limits,
  abstract format and the key-points box format.
- **Author list, affiliations, contributions (CRediT).**
- **Ethics statement**: secondary analysis of public de-identified data; whether an institutional determination exists.
- **Data availability**: which derived tables, fold files, locked model files and model cards are released; licence
  constraints (BrainSegFounder weights under the UK Biobank MTA must not be redistributed; derived features — check).
- **Code availability**: repository, tag, licence.
- **Funding and competing interests.**
- **How to present PRISM v1**: it is unpublished; decide whether to cite the v1 report (and its authors) or only
  describe it, and whether the history rows (pre-fix leaky results) stay in Table 2 or move to the Supplement.
- **Reporting guideline for the report generator**: consider adding TRIPOD-LLM items once the report-generator
  results exist (not cited yet).
- **`paper/README.md`** still says 'write "the PRISM report model/split"' (not owned by this pass; update to the new
  terminology). The same rule is in the user's auto-memory note on PRISM naming.
- **Whether to report the duplicate-patient finding** (three identical cross-patient masks) to the MU-Glioma-Post
  maintainers before submission.
- **Molecular look-ahead** (IDH/MGMT used at 8 grade 4 scans taken before diagnosis): decide whether to re-run the
  baseline with these values masked before submission; the draft states the issue as a limitation, size unquantified.
- **Pre-registration wording**: the phase-ladder plan was not separately committed; keep the honest wording.

## Inconsistencies found between source documents (resolved in the draft as noted)

1. **Pre-clip radiomics numbers.** `SPLIT_VARIANCE.md`, `FINAL_RESULTS.md` and `C3_radiomics.md` (head-to-head section)
   still give pre-clip `baseline_rad` / legacy radiomics values (0.801 ± 0.053, 0.867 / 0.847, Δ −0.004). The draft uses
   the clipped values from `FIGURES.md` / `summary_clipped.csv` (0.799 ± 0.053, 0.862 / 0.845, Δ −0.006). The other
   radiomics rows of `head_to_head.csv` (2-level texture, corrected compartments) were never re-run with the clip; the
   draft quotes them only as before/after history in Supplement S7 (from `FIX_TREATMENT_ASOF.md`).
2. **PRISM split size.** `FIX_TREATMENT_ASOF.md` and `FIX_EVALUATION.md` §5 use 127 / 30 patients and 84 scans (pre-label
   fix; PRISM IPCW 0.811 [0.694, 0.919]); the final split is 126 / 29 / 82 (0.817 [0.690, 0.920]). Both appear in Table 2,
   labelled.
3. **"Ridge 0.880 → 0.871".** The as-of fix *raised* the single-split ridge (0.870 → 0.880, `head_to_head_before/after.csv`);
   0.871 is the later final-label value. The draft reports all three.
4. **Frozen pre-fix outputs.** `outputs/results_pre_fix_2026-10-11/` contains C1/C2/C3/external but **no PRISM-split
   rows**; the pre-fix single-split numbers come from `outputs/results/c3/prism_report_split/head_to_head_before.csv`.
   The "after fix" repeated-CV values exist only in `FIX_TREATMENT_ASOF.md` (outputs overwritten).
5. **O/E of the baseline.** `CLINICAL_UTILITY.md` gives weighted O/E 0.96; `BASELINES.md` and `IMBALANCE.md` give 1.04
   (Kaplan–Meier O/E). Different estimators; the draft quotes 0.96 as "weighted O/E" and 1.04 only in the imbalance context.
6. **Concurrent detection range.** `OUTLINE.md` says 0.62–0.68; `DIAGNOSTICS_IMAGING.md` says 0.62–0.70 (boosting
   reaches 0.70). The draft quotes the ridge value 0.68 [0.62, 0.74] and the table in S14.
7. **Phase-ladder permutation p.** `PHASE_LADDER.md` says "20 of 100 permutations reached" and p = 0.208; `FIGURES.md`
   writes 0.208 = 21/101. Consistent ((1 + 20)/101); the draft gives both forms in S11.
8. **Shipped PRISM report model on LUMIERE** (0.613) predates the final LUMIERE label (death censoring); flagged in S13.
9. **Split-variance verifier checks** (Optuna re-run, random splits) used an earlier per-split table (baseline 0.800 ±
   0.054 there vs 0.801 ± 0.052 final); S8 labels them as such.
10. **Audit referral share.** `AUDIT_SYSTEM.md` assessment says flags send "58–73%" of scans; the table gives 72.6% /
    68.0% for any flag; 58% is rules (i) or (ii) in all gliomas (`referral.csv`). The draft quotes 72.6%.
11. **Label-change count.** `FIX_LABELS.md`: 17 negatives → censored and 1 negative → positive at 120 d; the draft
    quotes these, not a combined count.
12. `docs/results/C3_results_{grade4,all_glioma}.csv` are stale copies (per `FINAL_RESULTS.md`); not used.

## Self-check performed

- Every 3-decimal number in DRAFT.md and SUPPLEMENT.md was checked to occur verbatim in a `docs/` source document or as a
  rounded value of an `outputs/results/` or `docs/manuscript/figures/` CSV; all matched (two Table S17 CIs are rounded
  from `fig4_phase.csv`).
- Results, Tables 2–3 and the Table 2 history rows were re-read line by line against `single_split.csv`,
  `head_to_head_{before,after}.csv`, the pre-fix C3 results, `summary_clipped.csv` (via `FIGURES.md`), `table3_forest.csv`,
  `AUDIT_SYSTEM.md` and `CFB_ADC.md` / `rule.json`.
- Derived statements (stated as such in the source map): external AUC loss of 0.05–0.06 (MU CV minus LUMIERE locked),
  "about one in eight" clinical-only events (12/93), "about ten times" the sample size (from "one tenth" in
  `CLINICAL_UTILITY.md`).
