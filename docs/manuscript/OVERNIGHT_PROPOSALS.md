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
