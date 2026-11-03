# PRISM manuscript voice guide

Use this before drafting or revising any manuscript passage. It is the compact companion to
[STYLE.md](STYLE.md) and [CHANGES.md](CHANGES.md): the first records the full editorial history; the second records
the argument and evidence limits. This guide turns them into a repeatable writing practice.

## The voice

Write as a researcher explaining a precise contribution to an informed colleague: direct, calm, and specific. The
paper is a selective argument about the final PRISM system, not a chronology of experiments and not a catalogue of
components.

Every sentence must earn its place. It should either move the argument forward, state a supported fact, explain how
that fact was obtained, or give a necessary limit on its meaning. If a word can be removed without changing the
claim or the reasoning, remove it.

## The writing rules

- Begin with the finding or claim, then give the evidence needed to believe it.
- Open an abstract or section with the concrete clinical or research situation before introducing the system or its
  components. Explain what a score, model, or measurement does before describing its limitation.
- Introduce a clinical term through the concrete situation it names, then give its label. Remove background details
  that do not return in the paper's argument.
- Use concrete subjects and verbs: scans, measurements, models, reports, cohorts, and clinicians do things. Avoid
  abstractions doing work for them.
- Name the actual object when it matters: say what the report lists or what the model uses rather than that the
  system “improves transparency” or “leverages evidence.”
- Give one main idea to a paragraph. Use only the numbers needed for that idea.
- State a boundary plainly, once, where it matters. Do not make every claim sound defensive.
- Prefer ordinary words unless a technical term makes the claim more exact. Technical vocabulary is useful when it
  identifies a method or a measurable property, not when it merely makes a sentence sound scientific.
- Let the paper's structure create emphasis. Do not add emphasis words to announce it.
- Give a count a reason to appear: attach its cohort, evaluation, or comparison rather than dropping it into a
  sentence without context.
- Do not build a sentence around an unnecessary definition, contrast, or colon. State the action directly: “models
  rank follow-up scans,” not “models reduce a scan to one number: a score.” Do not hedge a simple point into a
  methodological aside.

## PRISM-specific language

- The central claim is that PRISM turns a progression score into an inspectable scan-level record. It keeps
  image-derived measurements and treatment context distinct, displays their agreement and available support, and
  generates a checked report from that record.
- In narrative prose, say that progression was **recorded** at a scan. In Methods, define the cohort-specific endpoint
  precisely; do not turn either form into a diagnostic claim.
- A report check establishes agreement with the structured record; it does not establish clinical usefulness.
- Describe PRISM as a local multimodal decision-support system only as its intended role. Do not imply that clinical
  decisions or outcomes improved without evidence.
- When describing external evaluation, say that MU-trained cohort-compatible models were applied without refitting;
  do not imply that identical inputs or one invariant score were used at every site.
- When external sites require different prespecified models, use a compact plural description in the abstract and
  reserve the model-specific inputs for Methods and Results.
- Prefer “measurements and treatment context used to produce the score” to “evidence behind the score.”

## Words and moves to avoid

Avoid a word unless the manuscript defines or demonstrates it: *novel, unique, powerful, robust, comprehensive,
seamless, transformative, sophisticated, state-of-the-art, clinically actionable, real-world, scalable, end-to-end,
groundbreaking, leverage, unlock, harness,* and *empower*.

Also avoid generic AI phrases and slogan-shaped prose: “the model understands,” “PRISM empowers clinicians,” “the
evidence speaks for itself,” “not merely X but Y,” “crucially,” “importantly,” and “remarkably.” Replace them with
the precise observation. Do not claim novelty, general-purpose LLM advantage, clinical benefit, or a validated
confidence method unless the paper directly evaluates it.

Useful replacements:

| Instead of | Write the concrete fact |
|---|---|
| “leverages multimodal evidence” | “combines image-derived measurements and treatment context” |
| “enhances transparency” | “lists the measurements, treatment context, and provenance used for the assessment” |
| “robustly generalises” | “reached [metric] in [named cohort], within the stated evaluation scope” |
| “hallucination-free report” | “passed the defined automatic check against its structured record” |
| “confidence” | the exact component: conformal set, agreement indicator, or evidence tier |
| “framework” or “pipeline” | system, model, record, or report—whichever is actually meant |

## A quick final check

Before accepting a paragraph, ask:

1. What does the reader now know or believe that they did not before?
2. Can I point to the exact data, component, or result supporting each claim?
3. Have I named an action instead of an abstraction?
4. Did every adjective and technical label change the meaning?
5. Does the paragraph advance the paper's argument rather than recount project history?

## Paste-ready revision prompt

> Revise the following passage for the PRISM manuscript. Preserve its scientific accuracy and intended meaning.
> Write direct, precise prose for an informed research reader. The paper argues that PRISM turns a
> progression score into an inspectable scan-level record; it is not a project chronology or a general-purpose LLM
> paper. Use concrete subjects and verbs, and retain only details that advance the paragraph's claim. Do not add
> jargon, hype, novelty claims, slogan-shaped contrasts, generic AI language, or unsupported clinical benefit.
> Name the exact cohort, endpoint, model, or measurement when that specificity is necessary. In narrative prose, say
> that progression was recorded at a scan; define the exact cohort endpoint in Methods. State a limitation plainly
> only where it changes the claim.
>
> **Passage:**
> [Paste passage here]
>
> **What this paragraph must establish:**
> [State the one claim here]
