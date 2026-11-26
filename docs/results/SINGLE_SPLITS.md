# PRISM on single held-out splits (2026-11-26, exploratory)

Question (PI review, 2026-11-25): what would PRISM report on one held-out split, the design of the radiomics study?

Design: the 100 random single splits of the radiomics re-implementation (`christodoulou_replication.py`: seeds 0–99,
18 of 92 grade 4 patients held out). PRISM's ridge models are refitted on the other 74 patients, and the AUC is taken
over the held-out intended-use scans (20–42 scans and 8–16 with progression per split). Code:
`scripts/prism_single_splits.py`; outputs: `outputs/results/analyses/single_splits/`. Check: 5 × 5 CV with the same code
gives the paper's AUCs (released 0.82 / 0.71 / 0.82; segmenter 0.82 / 0.71 / 0.82).

| model | masks | mean | 2.5–97.5% | min | max | share ≥ 0.80 | share ≥ 0.90 |
|---|---|---|---|---|---|---|---|
| combined | segmenter (22 inputs) | 0.84 | 0.68–0.96 | 0.65 | 1.00 | 0.75 | 0.22 |
| combined | released | 0.84 | 0.68–0.96 | 0.62 | 0.98 | 0.73 | 0.22 |
| clinical history | — | 0.84 | 0.69–0.99 | 0.65 | 1.00 | 0.67 | 0.28 |
| imaging | segmenter (22 inputs) | 0.74 | 0.55–0.89 | 0.50 | 0.93 | 0.28 | 0.01 |
| imaging | released | 0.73 | 0.56–0.88 | 0.47 | 0.93 | 0.26 | 0.02 |

Reference (paper, Section 3.1): the radiomics re-implementation ranged 0.32–0.88 (mean 0.63) over 100 sets of the same
design. Those per-split values were lost in the 11-02 reset, so the two are not yet paired split by split.
