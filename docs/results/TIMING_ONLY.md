# Timestamp-only check (exploratory, 2026-11-20)

**Question.** How well does the timing of a scan alone rank it, on the paper's folds and evaluation sets? This was
asked by the author after the main results were seen, so it is exploratory.

**Code.** `prism/analyses/timing_only.py` (run 2026-11-20). Bootstrap: 1,000 patient samples, seed 1.

## MU (5 × 5 CV, intended use, 62 with progression vs 84 without)

| Score | AUC | Within one window | Across windows |
|---|---|---|---|
| Ridge on days since RT end (+ unknown indicator) | 0.641 (0.55–0.73) | 0.407 (0.31–0.51) | 0.787 |
| Ridge on all timestamps (days since RT end, days from diagnosis, visit number, early post-RT flag) | 0.757 (0.66–0.84) | 0.486 (0.37–0.60) | 0.925 |
| Clinical-history model (reference) | 0.822 (0.74–0.90) | 0.640 (0.50–0.78) | 0.935 |

Unfitted single inputs (AUC, scans):
- days since RT end: 0.768 (144);
- visit number: 0.775 (146);
- days from diagnosis: 0.742 (146).

The ridge fit on days since RT end alone ranks below its own unfitted ordering, because the relation is not linear.

## External centres (unfitted single inputs)

- **LUMIERE** (178 scans): days since surgery 0.608; rater's early-post-RT flag 0.378.
- **UCSF-ALPTDG** (grade 4, scan 2):
  - days from diagnosis 0.542 (68);
  - days from RT start 0.542 (67);
  - days since the previous scan 0.281 (69), that is 0.72 with shorter intervals ranked as progression.

## Reading

Timing alone ranks MU scans at about 0.77 but carries no ranking within a time window. It ranks scans at 0.61 at
LUMIERE and 0.54 at UCSF-ALPTDG, where the combined model still reaches 0.77 and 0.86.
