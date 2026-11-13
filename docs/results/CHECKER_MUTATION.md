# Checker mutation test: results (synthetic records only)

Plan: [CHECKER_MUTATION_PLAN.md](CHECKER_MUTATION_PLAN.md) (commit 4f854cb, written before the run). Run 2026-11-13,
`PYTHONPATH=. .venv/bin/python -m prism.analyses.checker_mutation`; frozen checker blob `26d6637a…`; outputs in
`outputs/results/analyses/checker_mutation/` (synthetic mutants only). No patient data read.

**Result.** The checker rejected none of the 52 correct synthetic reports and rejected 1,252 of 1,280 reports with one
error of a kind its rules target (97.8%). All 28 misses were one operator: the word "tested" written into the tier
sentence of a situation with few cases, while the rest of that sentence still gave the few counts. It rejected none of
the reports in the two expected blind spots: a flipped direction word ("larger" for "smaller") with the numbers
unchanged, and the enhancing and FLAIR volumes swapped between their labels.

| Operator | Error introduced | Mutants | Rejected |
|---|---|---|---|
| N1 | a cited number changed | 420 | 420 |
| N2 | a number written as a word | 52 | 52 |
| N3 | a number its cited field does not hold | 52 | 52 |
| N4 | a citation of a field that does not exist | 52 | 52 |
| F1 | raised out of range flag left out | 26 | 26 |
| F2 | out of range reported when not raised | 26 | 26 |
| C1 | wrong conformal set phrase | 52 | 52 |
| C2 | conformal sentence left out | 52 | 52 |
| A1 | agreement word flipped | 52 | 52 |
| A2 | one model's side flipped | 52 | 52 |
| T1 | tier sentence left out where evidence is thin | 28 | 28 |
| T2 | wrong tier phrase | 52 | 24 (all 28 misses: "tested" written for a few cases situation) |
| R1 | combined score left out | 52 | 52 |
| D1-D5 | diagnosis, advice, verbal probability, certainty, response category added | 260 | 260 |
| P1 | performance figure absent from the card | 52 | 52 |
| B1 (blind spot) | direction word flipped, numbers unchanged | 52 | 0 |
| B2 (blind spot) | enhancing and FLAIR volumes swapped between labels | 52 | 0 |

**Reading.** The checker reliably catches wrong or uncited numbers, omitted or invented flags, misstated confidence
statements and forbidden wording. It accepts a wrong tier word when the same sentence still states thin evidence, and it
cannot tell which label a cited number belongs to or whether a direction word is right. The checker was not changed
(frozen for the evaluated reports); a rule tying the tier word to the record's tier and a check of the direction word
are straightforward additions for a next version.
