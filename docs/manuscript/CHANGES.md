# PRISM manuscript change register

**Purpose.** This is the editorial control document for the publication manuscript. It records the argument we are
building, the changes approved by the author, and the evidence limits that constrain the prose. It is not an
experiment log: `docs/WORK_LOG.md` is the evidence archive; this document controls the paper.

**Status key:** proposed · approved · implemented · verified.

## Governing argument — approved 2026-11-02

PRISM is a locally generated surveillance support system that turns a scalar progression score into an inspectable
scan-level record. It keeps image-derived measurements and treatment-context information separate, shows their
agreement and the support available for that situation, and generates a checked report from the resulting record.

The paper's empirical reason for this system is that progression-score discrimination can arise from different
cohort-specific signals: treatment timing at MU and enhancement aligned with the documented endpoint at UCSF. The
paper does **not** claim that PRISM diagnoses progression, improves clinical decisions, replaces clinical judgement,
or validates a clinician-facing workflow.

### The question the paper answers

For a surveillance MRI, what information produced the system's assessment, do image-derived and treatment-context
signals agree, and how much comparable evidence supports that assessment?

### What a scalar score cannot provide

A scalar progression score alone cannot show whether its ranking reflects image measurements, the treatment course,
or a sparsely represented situation; it cannot display disagreement between those sources or guarantee that generated
prose contains only record-backed statements.

## Non-negotiable writing guardrails

- The manuscript is a selective argument about the final PRISM system, not a thesis chronology or a catalogue of
  failed experiments.
- Negative experiments constrain claims and may appear in the supplement or limitations only when needed to interpret
  a main-text claim.
- Call the task the scan at which each cohort **documented progression**; do not imply adjudicated biological
  progression or diagnosis.
- External implementations are MU-trained, cohort-compatible locked models. Do not describe them as one invariant
  score unchanged in every input.
- Call conformal sets, pathway disagreement and the reliability card **uncertainty/evidence indicators**, not a
  clinically validated per-scan confidence method.
- The language model is a bounded reporting component: local, record-only, no images or calculations, and checked
  deterministically. Automatic record consistency is not clinical usefulness or reader validation.
- Do not claim a low LLM learning curve, a required model size, novelty/firstness, or clinical benefit.

## Revision order

| order | section / display | intended change | status |
|---|---|---|---|
| 1 | Abstract | Replace the finding-inventory abstract with one clinical-to-system narrative. State what a score cannot show, what PRISM makes visible, one internal and one result per external cohort, the cohort-dependent evidence finding, and the narrow report-check result. | verified |
| 2 | Introduction | Establish the scan-level professional question, then define the system response and its four concise contributions. Make the audit the reason PRISM exists, not a competing paper. | verified |
| 3 | Figure 1 and report display | Add a score-alone versus PRISM evidence scenario using the existing synthetic example; simplify report-facing field-code/debug styling. | proposed |
| 4 | Results | Reorder around: transport; what drives apparent discrimination; evidence indicators; bounded report check. Reduce lists and move model-ladder detail out of the main narrative. | proposed |
| 5 | Discussion and conclusion | State the system's precise contribution and clinical boundary without defensive repetition. | proposed |
| 6 | Figures, tables and supplement | Reconcile source mismatches, simplify dense captions, rebuild the stale supplement, and resolve submission placeholders. | proposed |

## Abstract: approved and implemented 2026-11-03

**Premise.** Following treatment for aggressive glioma, changes on serial MRI must be interpreted alongside the
treatment course. A progression score cannot show whether it reflects MRI measurements or treatment context.

**Five beats.**

1. The clinical problem and the limitation of a progression score.
2. PRISM as a local multimodal support system that produces an inspectable scan-level report.
3. One internal result: the MU combined score, AUC 0.82 for the cohort-documented progression scan.
4. One external result per cohort, stated with the correct cohort-compatible locked model: LUMIERE combined score,
   AUC 0.77; UCSF single-scan image model, AUC 0.80. The prose must not imply these are one invariant model.
5. The system-level finding and boundary: signals differed by cohort; 406 reports passed the automatic record check
   after revision; reader studies are the next test of clinical interpretation and decisions.

**Excluded from the abstract.** Detailed pathway ladder, disagreement-rule result, model-size ladder, generic-chat
comparison, and the full confidence taxonomy.

## Evidence checks before each section is committed

- Every stated metric and population is checked against `docs/manuscript/NUMBERS.md`.
- Planned and exploratory status is retained where it changes interpretation.
- The contribution is checked against `docs/literature/PRIOR_ART_2026-11-01.md`; claim combinations and evaluations,
  not component novelty.
- The section passes a first-sentence test: its opening sentences alone state the paper's argument.
- The paper does not use the work log as prose source.

## Known correctness and presentation work

- Reconcile or remove the LUMIERE clinical-only point in Figure 2: the current plot and `NUMBERS.md` disagree about
  whether that value is available.
- State the LUMIERE reduced-timeline/rater-field limitation in the appropriate Methods/Discussion location.
- Keep the UCSF endpoint alignment with enhancement as an audit finding, not proof of biological progression.
- State the v3 report failure and the post-failure v3.1 revision with the scope of the automatic checker.
- Rebuild the supplement after the main-text structure is settled; it currently predates the UCSF, system and v3.1
  work.

## Change log

| date | decision | status |
|---|---|---|
| 2026-11-02 | Treat `WORK_LOG.md` as evidence control, not the manuscript outline. | approved |
| 2026-11-02 | Revise section by section, beginning with the abstract. | approved |
| 2026-11-03 | Approve and insert the 149-word abstract; state external results compactly as prespecified PRISM models and contextualise the 406-report check across all three cohorts. | verified |
| 2026-11-03 | Reframe the Introduction around PRISM as an evaluated scan-level evidence-record system; credit report-generation and deterministic-check precedents, then state the system's four bounded contributions. | verified |
| 2026-11-03 | Refine the Introduction for the author's full read-through: begin with the clinical ambiguity, explain the score gap in plain language, and state the system's evidence record and boundaries without component hype. | verified |
| 2026-11-03 | Revise Introduction paragraphs 1--2: define pseudoprogression through the treatment-related MRI ambiguity, remove unrelated radiation-necrosis context, and introduce the progression-prediction score before stating what it cannot show. | verified |
| 2026-11-03 | Remove the colon-based score definition while preserving the author-approved description of what progression models do. Record the standing rule against defensive definitions and colon reveals. | verified |
| 2026-11-03 | Restore the author-approved score-introduction sentence. Record a revision-control rule: preserve approved surrounding prose and make the smallest change that resolves a specifically identified problem. | verified |
| 2026-11-03 | Correct the voice rule after author feedback: an approved phrase identifies the informational shape to preserve, not a ban on rewriting. Rewrite the faulty passage while retaining its useful actor, action and object. | verified |
| 2026-11-03 | Simplify Introduction paragraph 2: remove AUC-ranking language from the account of the score's purpose and move the external-validation rationale out of the paragraph for later placement. | verified |
