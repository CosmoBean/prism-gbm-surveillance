# Plan: does the report checker catch errors? (mutation test, synthetic records only)

Written 2026-11-13, before any run. Asked by the in-depth reviewer of the overnight revision ("S7 tests whether the
model follows a changed record, not whether the checker rejects wrong reports").

## Question
For reports that agree with their record, how often does the frozen checker (`prism/report/checker.py`, blob
`26d6637a6570549e46a5ca7be7a059033e3a0ac7`, `check(..., card=True)` as in report v3.1) wrongly reject them, and for
reports with one deliberately introduced error, how often does it reject them?

## Data
Synthetic records only, built with the unit-test fixtures (`tests/test_report_v3.py::record`, `tests/test_report_v3_1.py
::lumiere`) and `facts_v3_1`. No patient record, report or score is read. Grid: MU records over tier (few cases,
tested) x model sides (4 combinations) x combined 80% set ({0}, {1}, {0, 1}) x out of range flag (off, on) = 48, plus
LUMIERE records (rater flag no / yes, x out of range off / on) = 4. Total 52 records.

## Correct reports
`good_claims(F)` from the unit tests, with the volume sentence reworded to the v3.1 label ("indicative volumes from the
automatic segmentation"), the LUMIERE rater sentence added where the field exists. Each must pass; any failure is a
false rejection and is reported.

## Mutation operators (one error per mutant)
Expected to be caught (the checker's stated rules):
- N1 a cited number changed (each sentence holding a number; the first number +1 in its last decimal place x 10)
- N2 a number written as a word
- N3 a new sentence with a number that its cited field does not hold
- N4 a citation of a field that does not exist
- F1 the out of range sentence removed when the flag is raised
- F2 an out of range sentence added when the flag is not raised
- C1 the conformal phrase replaced with another set's phrase
- C2 the conformal sentence removed
- A1 the agreement word flipped (agree <-> disagree)
- A2 one model's side flipped (above <-> below)
- T1 the tier sentence removed where the tier is few cases
- T2 the tier phrase replaced with another tier
- R1 the combined score sentence removed
- D1 a diagnosis sentence added ("These findings are consistent with tumour progression.")
- D2 an advice sentence added ("A biopsy should be considered.")
- D3 a verbal probability added ("Progression is likely at this scan.")
- D4 a certainty sentence added ("This scan rules out progression.")
- D5 a response category added ("This scan shows stable disease.")
- P1 a performance figure absent from the card added ("The model's AUC in this situation is 0.91.")

Expected blind spots (no rule targets them; reported as limits, not failures):
- B1 the direction word in the enhancing change sentence flipped (larger <-> smaller), numbers unchanged
- B2 the enhancing and FLAIR volumes swapped between their labels, both still cited

## Outcome
Per operator: mutants made, rejected, rejection rate. False rejection count of correct reports. No threshold is
claimed in advance for B1 and B2. For the caught operators, the expectation is 100%; any miss is reported with its
mutant text (synthetic) and is a finding about the checker, not fixed in this run.

## Output
`docs/results/CHECKER_MUTATION.md` (aggregate table) and `outputs/results/analyses/checker_mutation/` (synthetic
mutants). Code: `prism/analyses/checker_mutation.py`.
