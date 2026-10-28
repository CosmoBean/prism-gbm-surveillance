# Overnight proposals: decisions for the author (2026-10-28)

Items the overnight pass did not change because they alter the argument, the abstract, locked text or a claim's
strength. Each comes from the cold-reader or hostile-reviewer reads (loop numbers in brackets).

## P1. The abstract sells the numbers the paper later explains away (loops 2: both readers)
Both readers felt a "bait and switch". The abstract gives MU timeline 0.82, UCSF 0.80 and 0.73 as performance, and
only page 5 says that MU's 0.82 comes mainly from when patients were scanned, and that UCSF's progression calls were
made from enhancement at the same scan (enhancing volume alone 0.88, above both locked image models). The cold reader:
"I re-read the abstract after this point and felt misled." This is the finding-first framing discussed on
2026-10-27. Proposal: lead the abstract with the finding (what carries a score differs by cohort: timing at MU,
enhancement at UCSF) and present PRISM as the response; give the UCSF 0.88 reference beside 0.80 / 0.73, and
describe 406/406 as a lexical consistency check rather than the closing result.

## P2. The report does not say *which* evidence carried a score (loop 2: hostile)
The Introduction claimed "the report makes that distinction visible". A report states each pathway's score and what
it is based on, but not that at MU the timeline mostly encodes the phase of care, or that at UCSF the images mostly
re-measure enhancement. Overnight, the claim was narrowed to what the report does ("shows the two pathway scores
separately, each with the inputs it is based on"). Deciding whether the report should carry a cohort-level sentence
on what the scores depend on is a design change for you.

## P3. One table of scans and patients per analysis (loop 2: hostile)
146 / 114 / 181 (MU), 178 / 162 (LUMIERE) and 69 / 130 / 140 (UCSF) are hard to reconcile from Table 1's notes. A
small table, or a flow figure in the supplement with one line in Table 1, would end that. (The cohort flow exists:
`docs/manuscript/cohort_flow.png`.)

## P4. Figure 5B is three 100% bars (loop 2: cold reader)
"That is one sentence, not a figure." Options: drop 5B and give 5A the full width; or replace it with the
model-size ladder (which models pass the check), which shows something the text does not.

## P5. Move the report earlier (loop 2: cold reader)
The synthetic report (Figure 5A) is the only place the cold reader understood what a clinician sees. Option: make it
Figure 1C or cite it from Section 2.1.

## P6. Which medians does the agreement rule use? (loop 4: cold reader) — needs a decision
Section 2.1 says the system places each pathway's score against its median **on MU** (rounds 4–5 of the council).
The evaluated reports (`prism/report/facts_v3.py`, the pathway statements and `pathways.agreement_statement`) place
it against "the median of its scores in the <cohort> evaluation scans", i.e. **each cohort's own** median, which
is the planned rule of Table 2. So the 406 checked reports implement the planned rule, not the rule the text calls
the system's. Figure 5A now copies the report's real wording (with invented numbers). Options: (a) say in 2.1 that
the reports use each cohort's own medians and that the MU-fixed rule is the one a new centre would compute at a
single scan (exploratory); or (b) regenerate reports with MU-fixed medians (a new run, out of scope tonight).
Overnight changed nothing on this point except making Figure 5A faithful.

## P7. A table naming every score once (loop 4: cold reader)
"Most re-reading came from losing track of which model a number belonged to": clinical-only, timeline (full and
reduced), image pathway, single-scan images, the planned imaging model, the combined score and enhancing volume
alone. A six-row Methods table (inputs, uses dates?, planned?) would end it. Not added tonight because it adds a
display item; ready to draft if you want it.

## P8. Table 1 MU age: 62.5 or 62? (loop 6: number audit)
Table 1 gives MU age 62.5 (IQR 53–70), following council decision 16 ("same population as TABLE1_COHORT.md").
TABLE1_COHORT.md shows 62 [53–70] in the grade 4 columns. Please confirm which population and value is meant;
the overnight pass left it unchanged.

## P9. Tikhonov "four response categories" (loop 6: number audit)
This is not in NUMBERS.md and the reference is still a `\todo`. Verify against arXiv:2509.06511 when the reference
is resolved.

## P10. Say that both external results partly reflect how the labels were made (loop 6: hostile)
At UCSF the progression call was made from enhancement at the same scan, and enhancing volume alone (0.88) beats
the locked image models. The reviewer asks for this to be stated as a limit of the transfer claim, and for the
Conclusion ("its models ranked scans at two other centres without refitting") to carry it. The Limits already say
that most UCSF progression scans were rated as showing increased enhancement. Softening the Conclusion changes a
council-ruled sentence, so it is left to you. Suggested: "…ranked scans at two other centres without refitting,
though at UCSF the ranking largely follows the enhancement on which progression was called."

## P11. Present the flag results as a grid (loop 8: hostile)
The flag evaluation (3.4, Table 2 rows 9–10 with footnote a, Figure 4B) mixes two flags, two tests and two median
rules, and the reviewer judged it the item most likely to draw a "major revision" on presentation: the planned rule
fails externally while the exploratory MU-median rule is the one the system uses (see also P6). Overnight, 3.4 was
split into two paragraphs (the planned result first and stated plainly, then the MU-median result marked †). A
fuller fix is a small grid in the supplement or as Table 2's replacement rows: cohorts × {disagreement, set} under
the planned rule, plus one † row for the MU medians. It changes a display item, so it is left to you.

## Status after the second pass
- P4 done (Figure 5B is now the report-model ladder). P6 done in the text (2.1, 3.4, Figure 4B, Table 3 note). P7
  done (Table 1, the scores). P11 partly done: 3.4 states the planned result first, and the Limits say which parts
  of the confidence held. P10 partly done: 3.3 and the Conclusion now carry the label point.

## P12. The supplement's cross-references are stale
`supplement.tex` refers to main-text sections as "M2.8", "M2.11" and so on, from an older structure, and to old table
numbers. The main text is now 2.1–2.3, 3.1–3.5, Table 1 (scores), Table 2 (cohorts) and Table 3 (planned
questions). Every `\todo{Supplementary section: …}` in the main text also still needs its supplement section.
This is a separate reconciliation pass.

## P1 draft abstract (150 words by wc, not applied; written to the STYLE.md §9 recipe and the 2026-10-27 reaction)

Surveillance MRI after treatment for glioblastoma is read against earlier scans and the course of treatment, but a progression score does not say which it used. We built PRISM, which scores each scan separately from its images and from its treatment timeline, states how far each score has been tested in the scan's situation, and writes a checked report locally. At the development centre, MU-Glioma-Post, the timeline carried most of the signal (AUC 0.82), largely because of when patients were scanned; within a phase of care, the images did as well. Applied unchanged at two other centres, the models still ranked scans (LUMIERE, 0.77), but at UCSF-ALPTDG the scores followed the enhancement on which progression was called, and enhancing volume alone reached 0.88. What carries a progression score depends on how a cohort was scanned and labelled, and separate evidence makes this visible. No clinician has yet used the reports.

Sources: MU timeline 0.82 (NUMBERS.md 3); within-phase images 0.68 vs timeline 0.64 (5); LUMIERE 0.77 (4); UCSF enhancing volume alone 0.88 (5, exploratory, which the Methods dagger covers). Three numbers. The punchline is the cohort finding, not a component list. Replaces the proposed system-first abstract only if you approve.
