# PRISM System-First Manuscript Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a compiled, committed PRISM manuscript whose central contribution is a transparent longitudinal evidence report, supported by component and cross-site model evaluation.

**Architecture:** Preserve the current manuscript as a Git-reachable baseline, then rewrite the article around the approved system-first claim hierarchy. Use report v3.1 as the primary report evidence because it is the newest cross-cohort evaluation; retain older report versions only as labelled development history. Replace the five missing figure placeholders with displays made from verified outputs. A no-model report ablation remains future work unless it is newly run and validated.

**Tech Stack:** LaTeX/Taylor & Francis Interact template, Tectonic/BibTeX, existing Python/Matplotlib figure utilities, Git.

**Spec:** `docs/superpowers/specs/2026-10-26-prism-system-first-manuscript-design.md`

## Global Constraints

- Work in an isolated branch/worktree after user approval; leave the existing untracked `submit.sh` untouched.
- Preserve each material state with a focused Git commit; never overwrite or delete prior manuscript material.
- Use only verified results in `docs/results/` and `outputs/results/`; do not invent a model-removal result.
- Use v3.1 report evidence in the article: 406/406 checker passes, 220/220 required thin-evidence tiers stated, and 28/30 perturbation-rule passes. Describe this as automatic grounding/completeness evaluation, not clinical validation.
- Keep scan-level detection as the main task unless a report record is deliberately rebuilt for 120-day forecasting.
- Fill Sri Datta Ganesh Bandreddi and `sbandred@andrew.cmu.edu` as first and corresponding author; retain the affiliation and ORCID placeholder until corrected or supplied.
- Keep unresolved disclosure, funding, ethics, data-release, and co-author fields visibly pending rather than guessing.
- Final PDFs must have no visible figure placeholders, undefined citations/references, or build-script failures.

## Review Focus

- Scan-level detection and 120-day risk never appear as the same output.
- v3.1 is the only primary report result; v1/v2/v3 appear only as labelled development history.
- Automatic checker pass never becomes a clinician-usefulness or diagnostic-performance claim.
- Every figure target named in `main.tex` exists and matches its caption.
- Only owned files are staged; `submit.sh` remains unmodified and untracked.

---

### Task 1: Preserve the baseline and create an isolated rewrite branch

**Files:**

- Create: `docs/superpowers/specs/2026-10-26-prism-system-first-manuscript-design.md` (already drafted)
- Create: `docs/superpowers/plans/2026-10-26-system-first-manuscript-rewrite.md`
- Do not modify: `submit.sh`

**Interfaces:**

- Consumes: `manuscript-week` HEAD and the approved design specification.
- Produces: a clean isolated rewrite branch whose parent preserves the current manuscript state.

- [ ] Record baseline status, HEAD, and branch. Verify that `submit.sh` is untracked and only the design/plan are staged.
- [ ] Commit the approved design and this plan with message `docs: add system-first manuscript rewrite design`.
- [ ] Create an isolated `manuscript-system-first` worktree from that commit, using a verified ignored worktree directory.
- [ ] Run `./paper/build.sh` unchanged; record baseline build state and placeholder figures without altering source.

### Task 2: Establish one narrative and report-evidence source of truth

**Files:**

- Modify: `docs/manuscript/OUTLINE.md`
- Modify: `docs/manuscript/STORY.md`
- Modify: `docs/manuscript/FIGURES.md`
- Modify: `docs/manuscript/DRAFT_NOTES.md`
- Modify: `paper/SOURCE_MAP.md` if source mappings change

**Interfaces:**

- Consumes: the design specification, `docs/results/REPORT_V3_1.md`, current result documents, and the number registry.
- Produces: a prose/figure map that `paper/main.tex` and `paper/supplement.tex` can follow without version drift.

- [ ] Rewrite `OUTLINE.md` around: clinical surveillance problem -> limitation of a bare prediction -> PRISM evidence record/report -> component and cross-site evaluation -> automatic report grounding/completeness -> reader-study limitation.
- [ ] Re-map `STORY.md` by narrative role, retaining initial radiomics motivation, component evaluation, locked transfer, evidence audit, v3.1 report evidence, and bounded uncertainty.
- [ ] Record v3.1 as primary report evidence: 406/406 checker passes, 220/220 tiers stated, 28/30 perturbation-rule passes, lexical checker, and no clinician reader study. Label older report versions as development history.
- [ ] Replace `FIGURES.md` with a five-display inventory: system architecture, component performance, evidence audit, report anatomy, and report evaluation.
- [ ] Run targeted searches for `406/406`, `220/220`, `28/30`, `249/249`, `236/249`, `v3.1`, `120-day`, and `detection`; resolve version/endpoint ambiguity.
- [ ] Commit with message `docs: define system-first PRISM narrative`.

### Task 3: Rewrite the main article and fill supplied author information

**Files:**

- Modify: `paper/main.tex`
- Modify: `paper/macros.tex` only if revised layout needs a macro

**Interfaces:**

- Consumes: Task 2's narrative/display map and verified source documents.
- Produces: an article with a coherent system-first argument and accurate first/corresponding-author fields.

- [ ] Replace the author placeholder with `Sri Datta Ganesh Bandreddi` and `sbandred@andrew.cmu.edu`; retain only the ORCID placeholder.
- [ ] Rewrite the 100--150-word abstract with five moves: clinical need, bare-score gap, PRISM system, necessary evidence, reader-study scope.
- [ ] Rewrite Introduction and Methods in the order information reaches the report: cohorts/task, longitudinal inputs, separate pathways, structured evidence record, report generation/checking, evaluation.
- [ ] Rewrite Results and Discussion so performance validates report components; make model-removal a stated future ablation and state the absence of clinician-reader outcomes.
- [ ] Simplify Table 1 into cohort/evidence availability. Replace the current pre-specification ledger with a report-evaluation table or move it to the supplement.
- [ ] Run searches for visible `todo`/`flag` markers and unsupported clinician-benefit language; permit pending author-declaration markers only.
- [ ] Commit with message `docs: rewrite PRISM manuscript around evidence reporting`.

### Task 4: Build the five main manuscript displays from verified outputs

**Files:**

- Create: `docs/manuscript/figures/fig1_system.{pdf,png}`
- Create: `docs/manuscript/figures/fig2_transport.{pdf,png}`
- Create: `docs/manuscript/figures/fig3_evidence.{pdf,png}`
- Create: `docs/manuscript/figures/fig4_confidence.{pdf,png}`
- Create: `docs/manuscript/figures/fig5_report.{pdf,png}`
- Modify/create: focused figure-generation code under `prism/analyses/` only when existing assets cannot be composed reproducibly

**Interfaces:**

- Consumes: Task 2's display inventory and verified CSV/report artifacts.
- Produces: five non-placeholder PDF/PNG figures whose captions match their data.

- [ ] Inventory reusable assets and exact numeric sources. Use v3.1, rather than v2, for the report display/evaluation.
- [ ] Implement/adapt deterministic figure generation; it may arrange verified outputs but may not create new model claims.
- [ ] Generate vector PDFs and 300-dpi PNGs, then verify that every `figslot` target now exists.
- [ ] Inspect each figure at print size for labels, units, cohort names, panel claims, and caption agreement.
- [ ] Commit source and figures with message `figures: add system-first PRISM manuscript displays`.

### Task 5: Reconcile the supplement, compile, and verify the committed revision

**Files:**

- Modify: `paper/supplement.tex`
- Modify: `docs/manuscript/CHECKLIST_TRIPOD_AI.md`
- Modify: `docs/manuscript/CHECKLIST_CLEAR.md` when cross-references change
- Modify: `docs/manuscript/JOURNAL_RULES.md` only for an actual status change

**Interfaces:**

- Consumes: final main-text wording and final figure/table numbering.
- Produces: a supplement that supports rather than contradicts the article, and a buildable submission package.

- [ ] Make v3.1 the definitive cross-cohort report evaluation. Preserve old report evidence only as dated development history or remove it from the submitted supplement if it cannot be cleanly contextualised.
- [ ] Move long plan registers, model grids, checker implementation detail, and historical analyses out of the main story while retaining reproducibility detail in the supplement.
- [ ] Update checklist references and retain unsupplied ethics, funding, disclosure, data, code, ORCID, and co-author fields as pending.
- [ ] Run `./paper/build.sh`; resolve undefined references/citations, build failures, figure placeholders, and overfull boxes wider than 10pt.
- [ ] Verify figure-target existence, report-version labels, endpoint labels, whitespace with `git diff --check`, and the clean staging boundary around `submit.sh`.
- [ ] Commit source/figures/verification artifacts already tracked by convention with message `docs: complete system-first PRISM manuscript revision`.

### Task 6: Hand off a reversible, verified manuscript history

**Files:**

- Modify: none unless a verification note is needed

**Interfaces:**

- Consumes: the Task 1--5 commits.
- Produces: a clean branch, commit sequence, compiled PDFs, and a clear list of remaining author actions.

- [ ] Inspect the final Git log and status; confirm focused commits and no change to `submit.sh`.
- [ ] Re-run `./paper/build.sh` from committed state and confirm it creates no unstaged source edits.
- [ ] Report branch name, commit IDs, PDF artifacts, remaining author fields, and the untested no-model report ablation. Do not claim clinician benefit or full submission readiness while declarations remain open.
