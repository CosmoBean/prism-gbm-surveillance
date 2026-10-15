# Draft notes (2026-10-15)

LaTeX (paper/) is the source of truth from 2026-10-15; this markdown is a frozen snapshot.

Files: [DRAFT.md](DRAFT.md) (main text), [SUPPLEMENT.md](SUPPLEMENT.md), Table 2 history rows appended to
[figures/table2_single_split_vs_cv.md](figures/table2_single_split_vs_cv.md) / `.csv`, Figure 5 basis copied to
`figures/fig5_system_risk_coverage.png` (from `outputs/results/analyses/audit_system/risk_coverage.png`).

## Word counts

Counted with a whitespace tokenizer, headings excluded (script in the session scratchpad; re-count after edits).

| Part | Words | Target |
|---|---|---|
| Abstract (excluding the five bold labels) | 299 | ≤ 300 |
| Key points + clinical relevance statement | 216 | — |
| 1. Introduction | 886 | ~900 |
| 2. Methods | 2,196 | ~2,200 |
| 3. Results | 2,336 | ~2,200 |
| 4. Discussion (incl. limitations, conclusion) | 1,583 | ~1,500 |
| **Main text (Introduction to Discussion)** | **7,001** | 5,500–7,000 |
| Declarations | 128 | — |
| Tables 1–3 (with captions) | 1,247 | — |
| Figure legends 1–5 | 657 | — |
| References (39 entries incl. one dataset) | 1,241 | — |
| Source-map appendix (remove before submission) | 1,278 | — |
| Supplement (S1–S18, 25 tables, 7 figure pointers) | 11,664 | — |

The main text sits at the top of the target range. Journals with a 5,000-word limit would need about 2,000 words
moved to the Supplement (candidates: §2.5 second paragraph, §2.11 details, §3.2 history paragraph, §3.8).

## Open placeholders

- Declarations: ethics statement, funding, competing interests, data-availability wording, code link — `[PENDING AUTHOR DECISION]` / `[PENDING]` in DRAFT.md.
- Figure 5: panel A (system architecture + example audit record) still to be drawn; the risk–coverage panel exists.
- Supplement S17: TRIPOD+AI 5b (accrual dates; both datasets give relative days only), 22 (release model coefficients), CLEAR 53–58 (release).
- Supplement S16: public code release and tag; supplementary figures need export.
- No `[PENDING: AUDIT_SYSTEM results]` or `[PENDING: CFB_ADC results]` remain: both analyses finished and are reported (main §3.7, §3.9; Supplement S15, S18).

## [CHECK] items (citations not in the verified literature files, or flagged unverified there)

1. **Rai (2026)** — "repo, unverified (this pass)" in `COMPARABLE_RESULTS.md`; cited in Introduction and Discussion (0.728).
2. **Kocak et al. (2023), CLEAR** — reference taken from `CHECKLIST_CLEAR.md`, not from the literature files.
3. **Cox et al. (2024), BrainSegFounder** — DOI from `DEEP_FEATURES.md` only; title and authors incomplete.
4. **CFB-GBM dataset citation** (TCIA doi:10.7937/v9pn-2f72) — from `DATASETS.md`; the TCIA-recommended data citation and the arXiv:2608.17884 dataset paper should be added.
5. **Christodoulou et al. (2026) vs the PRISM report.** The draft treats them as separate (published single-test-set
   AUC 0.80 on MU-Glioma-Post vs the unpublished PRISM report model). `comparison.md` notes an earlier repo reading of a
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
- **How to present the PRISM report**: it is unpublished; decide whether to describe it as "an internal report" (as now)
  or name its authors/institution, and whether the history rows (pre-fix leaky results) stay in Table 2 or move to the
  Supplement.
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
