# What each group of inputs contributes (2026-11-26, exploratory)

Replaces the AUC split by time window in the paper (author decision 2026-11-26). Code:
`scripts/prism_feature_contributions.py` (17 s on 32 workers); outputs: `outputs/results/analyses/feature_contributions/`.
Paper's 5 × 5 CV, label and 146 intended-use MU scans, supplied masks; full models reproduce 0.82 / 0.71 / 0.82.

| model | group | share of score, median (IQR) | fall in AUC when left out (95% CI) |
|---|---|---|---|
| combined | treatment course and dates | 44% (36–54) | 0.10 (0.02 to 0.18) |
| combined | intensity | 15% (10–24) | 0.02 (−0.01 to 0.04) |
| combined | patient characteristics | 9% (6–14) | 0.01 (−0.01 to 0.04) |
| combined | change since earlier scans | 8% (5–12) | −0.02 (−0.03 to 0.00) |
| combined | volumes | 8% (4–14) | −0.01 (−0.02 to 0.00) |
| combined | composition, shape, position | 6% (4–9) | −0.01 (−0.03 to −0.00) |
| history | treatment course and dates | 79% (66–87) | 0.24 (0.13 to 0.35) |
| history | patient characteristics | 21% (13–34) | 0.02 (−0.01 to 0.06) |
| imaging | intensity | 39% (26–49) | 0.04 (−0.00 to 0.08) |
| imaging | change since earlier scans | 33% (19–42) | 0.05 (−0.00 to 0.11) |
| imaging | composition, shape, position | 13% (9–19) | −0.02 (−0.04 to −0.00) |
| imaging | volumes | 12% (8–18) | −0.01 (−0.02 to 0.01) |

All image groups together: a median 44% (34–53%) of the combined score, and more than half at 33% of scans.
Share = |group's part of the linear score| / Σ|parts|, averaged over the five repeats per held-out scan.
