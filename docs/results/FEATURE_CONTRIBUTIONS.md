# What each group of inputs contributes (2026-11-26, exploratory; primary rerun 2026-11-27)

Replaces the AUC split by time window in the paper (author decision 2026-11-26). Code:
`scripts/prism_feature_contributions.py` (17 s on 32 workers); outputs: `outputs/results/analyses/feature_contributions/`.
Paper's 5 × 5 CV, label and 146 intended-use MU scans, supplied masks; full models reproduce 0.82 / 0.71 / 0.82.

**Primary (paper since 2026-11-27): PRISM's segmenter, 22 inputs** (`PRISM_MASKS=brats24_22`; outputs
`feature_contributions_brats24_22/`; full models 0.82 / 0.71 / 0.82).

| model | group | share of score, median (IQR) | fall in AUC when left out (95% CI) |
|---|---|---|---|
| combined | treatment course and dates | 44% (36–56) | 0.09 (0.01 to 0.17) |
| combined | volumes | 13% (6–19) | −0.00 (−0.02 to 0.01) |
| combined | intensity | 13% (8–19) | 0.01 (−0.01 to 0.02) |
| combined | patient characteristics | 9% (6–17) | 0.01 (−0.01 to 0.04) |
| combined | change since earlier scans | 7% (5–11) | −0.01 (−0.03 to 0.00) |
| combined | composition, shape, position | 4% (3–7) | −0.00 (−0.01 to 0.01) |
| history | treatment course and dates | 79% (66–87) | 0.24 (0.13 to 0.35) |
| history | patient characteristics | 21% (13–34) | 0.02 (−0.01 to 0.06) |
| imaging | intensity | 36% (25–48) | 0.02 (−0.02 to 0.07) |
| imaging | change since earlier scans | 33% (19–45) | 0.07 (0.02 to 0.13) |
| imaging | volumes | 18% (11–25) | −0.02 (−0.03 to 0.00) |
| imaging | composition, shape, position | 8% (5–14) | −0.00 (−0.01 to 0.01) |

All image groups together: a median 43% (32–54%) of the combined score, and more than half at 34% of scans.

**Reference: supplied masks, 27 inputs** (`feature_contributions/`): dates 44% (36–54) of the combined score, drop
0.10 (0.02–0.18); image groups together 44% (34–53); imaging model intensity 39%, change 33%.

Share = |group's part of the linear score| / Σ|parts|, averaged over the five repeats per held-out scan.
