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

## Story rewrite (2026-10-15)

Main text rewritten as one narrative: the initial split scored high for every model → why the split was easy (500
splits, composition) → what carries the signal (ablation, phase of care) → imaging given every chance (surveillance
cohort, label, segmentation, external, diffusion) → auditing a modest model → reports that can be checked. Detail
that the story does not need now lives only in the Supplement (every cut number was checked to be there, except
97.6%, which stayed in the main text). No em dashes; hyphenated forms replaced where a plain form exists
(prespecified, resegmentation, grouped by patient, held-out). Title: *PRISM: an auditable pipeline for post-treatment
glioma surveillance, evaluated branch by branch*. Figures renumbered in order of first citation: Figure 1 is now the
architecture, Figure 6 the grounded report and risk–coverage curves. Typography: STIX Two text and maths, 1.5 line
spacing, 9.5 pt captions and 9 pt tables (were 8 pt), upright grey running head. Previous version:
`git show 01c9500:paper/main.tex`.

| | Before | After |
|---|---|---|
| Main text, Introduction to Conclusion (words, from the PDF) | 8,997 | 5,839 |
| main.pdf pages | 35 | 22 |
| Abstract (words) | 142 | 149 |

Weaknesses found by the internal review, with verification: [INTERNAL_REVIEW.md](INTERNAL_REVIEW.md). The most
important one (censoring concentrated in patients whose RT was never documented, so part of the "phase of care"
signal may be loss to follow-up) is stated in the text but needs a re-analysis before submission.

## Target journal: CMBBE: Imaging & Visualization (2026-10-15)

Current rules and the paper's status against each: [JOURNAL_RULES.md](JOURNAL_RULES.md) (live rules pasted by the user
2026-10-16).

Checked on 2026-10-15 for the two journals the user named.

| | CMBBE: Imaging & Visualization (Taylor & Francis) | Int. J. for Computational Vision and Biomechanics (MUK) | Int. J. of Imaging and Robotics (CESER) |
|---|---|---|---|
| Status | Active (vol. 14, 2026); full open access since vol. 12 (2024) | Dormant: last issue vol. 6(2), Jul–Dec 2020 | Active (vol. 26, 2026) |
| Indexing | Scopus, Web of Science ESCI, DBLP, DOAJ; IF about 1.3 | Google Scholar, EBSCO, Index Copernicus | Index Copernicus and similar; no DOIs |
| Deadline | None: rolling submission; no current call for papers found | Rolling (special issues by call) | Rolling |
| Cost | APC US$2,630 (DOAJ); waivers and institutional agreements | None | None; subscription access only |
| Review | Single-anonymous; about 13 weeks to publication (DOAJ) | Three board members | 5–14 weeks |
| Length | No word limit | 15–30 A4 pages, one column, double spaced, PDF by email | Not stated |
| Abstract / keywords | Unstructured, 100–150 words; no more than 3 keywords | Abstract and keywords | Under 250 words; up to 5 keywords; running title < 40 characters; MSC codes |
| Format | Word or LaTeX (T&F Interact template); CSE author-date references; British -ise spelling | PDF | Word or LaTeX (journal template); author-year references; plagiarism report required |
| Other | Disclosure, funding, data availability statement, notes on contributors (≤ 200 words each); figures 300 dpi colour / 1,200 dpi line art; supplement via Figshare | — | Reprints may not be posted online (arXiv, ResearchGate) |

Sources: DOAJ record and API for ISSN 2168-1171; T&F instructions for authors (latest readable copy is the
2022-06-19 Web Archive snapshot; T&F blocks automated access, so re-check the live page before submitting);
T&F CSE reference guide v2.0 (CSE-9); T&F Interact CSE LaTeX bundle; mukpublications.com/ijcvb.php and its
instructions page; ceser.in/ceserp/index.php/iji (about, author instructions, archive).

**Decision.** CMBBE: Imaging & Visualization. IJCV&B has published nothing since 2020, and IJIR has weak
indexing, no DOIs and forbids posting the article. CMBBE:I&V has no word limit, so the main text (about 8,400
words) needs no cuts for length; the cut list below is now optional.

**Changes made for CMBBE:I&V.**
- `main.tex` uses the T&F `interact` class (`largeformat`, double spaced, line numbers kept for review);
  `interact.cls`, `tfcse.bst`, `jabbrv*.{sty,ldf}` copied into `paper/` from the official bundle.
- References: T&F CSE name-year (`tfcse.bst`) in main and supplement; CFB-GBM data set entry completed from
  DataCite (Moreau et al. 2025, version 4).
- Abstract: unstructured, 142 words. Keywords: 3.
- Key points and clinical relevance statement removed (not part of the journal's structure); kept below.
- Back matter in the journal's order: acknowledgements, disclosure statement, funding, ethics, data availability,
  supplemental material, notes on contributors, references, tables, figures.
- Fig 5C regenerated as vector PDF (and 300 dpi PNG); the other figures are vector PDFs or 300 dpi PNGs.

**Still to do before submission.** Authors, affiliations, ORCIDs, contact, biographies; disclosure, funding,
ethics, data availability; upload figures as separate files (EPS/TIFF/JPEG, or PDF if accepted) and the
supplement as a separate file; LaTeX source with the PDF; confirm the live instructions (keyword limit, APC).
**Conflict of interest:** if an author or adviser sits on this journal's advisory board (the CV entry the user
quoted: associate editor 2013–2017, advisory board since 2017), declare it in the cover letter and the disclosure
statement and ask that they not handle the manuscript.

### Removed front matter (pre-CMBBE:I&V version, kept for other journals)

```latex
\section*{Abstract}

\textbf{Background.} PRISM (Post-treatment Response Intelligence and Surveillance Monitor), our multimodal
pipeline, predicts documented progression after a glioma surveillance MRI and explains it in a clinician report. Its first version scored AUC 0.80 on one 30-patient split of MU-Glioma-Post.

\textbf{Purpose.} To present PRISM, evaluate every branch and explain the optimistic initial result.

\textbf{Methods.} PRISM reads clinical, molecular and treatment-course data as of the scan day, adds volumes,
radiomics and a frozen SwinUNETR encoder, and writes an audit record and a grounded report per scan.
Development: MU-Glioma-Post (308 index scans, 155 patients; grade 4:
249 scans, 126 patients); locked external evaluation: LUMIERE (132 scans, 61 patients). Outcome: documented
progression within 120 days (death censored; IPCW AUC). We ran 500 splits of the initial split's design and
ablated each branch under 5$\times$5 patient-grouped nested cross-validation; key analyses had pre-specified rules.

\textbf{Results.} On the initial split, PRISM's initial radiomics model scored 0.802 and a model
without imaging 0.871; with treatment dates leaking from the future, a boosting model reached 0.901. Over 500
splits its pipeline averaged 0.720 $\pm$ 0.055, and 7\% of splits reached 0.802. Under
repeated cross-validation the clinical + treatment-phase core reached 0.698 (95\% CI 0.615--0.774) in grade 4.
Radiomics changed this by $-$0.032 ($-$0.084 to +0.017) and deep features by $-$0.004 ($-$0.069 to +0.063). In
post-radiotherapy scans, imaging added +0.061 ($-$0.038 to +0.156; permutation p = 0.21). Locked external AUCs
were 0.608--0.620. The audit layer met its coverage target (0.841, 0.790--0.885), did not improve
discrimination beyond case mix, and exposed a missingness shortcut. Local-language-model reports were faithful to the record in
236/249 scans (0.948; target 0.95 missed by one report, all failures one missing citation), with no omitted flag
or forbidden content.

\textbf{Conclusion.} PRISM's signal comes from phase of care, not MRI texture. It is deployed as the clinical +
treatment-phase core with auditable records; imaging branches are optional.

\section*{Key points}

\begin{itemize}
\item \textbf{Question.} Which parts of a multimodal surveillance pipeline (PRISM) predict documented
progression within 120 days of a post-treatment glioma MRI, and how far did our own initial single-split
evaluation mislead?
\item \textbf{Findings.} On our favourable 29-patient initial evaluation split, models scored 0.80--0.90; the
same pipelines averaged about 0.70 under repeated cross-validation, and PRISM's initial radiomics pipeline
averaged 0.720 over 500 splits of the same design. Radiomics, frozen deep features and re-segmentation added no
measurable discrimination to PRISM's clinical + treatment-phase core (AUC 0.698 in grade 4), internally or on
an external cohort.
\item \textbf{Meaning.} PRISM is deployed as its clinical + treatment-phase core. Its audit records and grounded
reports state what was known at the scan date, the uncertainty and the weak points of each prediction, but
abstention does not triage scans better than case mix does. Single-split AUCs on cohorts of this size measure
the split.
\end{itemize}

\section*{Clinical relevance statement}
At a surveillance MRI after glioma treatment, PRISM's core --- age, molecular markers and where the scan sits in
the treatment course --- predicts documented progression within 120 days about as well as any MRI-based branch
tested here (AUC about 0.70), and each prediction comes with an audit record of its inputs, interval and
referral flags. Conventional MRI radiomics should not be expected to add to it, and a single test-split AUC
near 0.80, including our own initial one, should not be taken at face value.
```

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

- **Target journal**: decided 2026-10-15, CMBBE: Imaging & Visualization (see above).
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
