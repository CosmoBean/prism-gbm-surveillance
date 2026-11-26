# S3. Can the imaging model rank better within a time window? (plan, fixed before any fit)

The author's question (2026-11-20) followed S2. Once timing is held fixed, the imaging measurements rank MU scans at
about 0.68 within a time window (M1: A_W 0.68 for the current imaging model and for the stratified model A). S3 tests
two cheap changes to the imaging model's fit. **The system does not change:** PRISM keeps its current models and the
released masks (ADOPT_AB.md, not adopted, 2026-11-20). S3 is an analysis of how far the imaging measurements can go.

## Arms

Every arm uses the same 27 image measurements from the released masks (LUMIERE: the T_img set, with the 3-volume model
for scans without a previous scan, as in S2). They also share the preprocessing (c3.BASE_PRE), the 5 × 5 MU folds
(intended-use evaluation set, 146 scans), the locked fit on all MU rows, the LUMIERE (178) and UCSF (grade 4 scan 2,
69) evaluation sets, and the S2 solver (`stratified_offset.ridge`).

| Arm | Fit | Penalty grid |
|---|---|---|
| I0 | the current imaging model (system, as published) | current: C in 0.01–3 |
| A | S2's stratified model (one intercept per time window, dropped from the score) | current |
| **I-wide** (test 1) | I0's model, refitted with the S2 solver | **wide: C in 0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3** |
| **A-wide** (test 1) | A | wide |
| **A-int** (test 2) | A plus interactions between "within 12 weeks after RT" and four enhancement measurements: `log_et_cc`, `logratio_prev_et`, `nadir_all_et`, `t1c_et_rel` (where a cohort lacks one, it is left out at that cohort and the fit is repeated without it) | wide |

- **Why the wide grid:** A chose C = 0.01 or 0.03, the two strongest penalties of the grid, in every fit (S2), so the
  best penalty may lie outside it.
- **Why the interaction:** new enhancement in the first 12 weeks after radiotherapy is often treatment effect and
  later more often progression, so the same measurement may carry the opposite meaning in the two windows.
- **The A-int score** is the image term plus the interaction terms, without the window intercepts. It needs the
  window at scoring time:
  - MU: the card's window (`system.mu_situation`);
  - LUMIERE: the rater's `early_post_rt` flag;
  - UCSF: its approximated radiotherapy window, as in the paper.
- **Implementation check before any comparison:** I-wide restricted to the current grid must reproduce I0's MU AUC
  to 0.01.

## Question and rule

**Primary (planned):** does a test arm rank scans better within a time window than the current imaging model?

- **Statistic:** A_W (M1 within-window AUC, the paper's strata) of each test arm minus I0, as paired differences in a
  2,000-sample patient bootstrap (seed 20261121), at MU and LUMIERE.
- **Rule:** an arm *improves the within-window ranking* if its paired A_W difference has a 95% CI above 0 at MU and a
  point estimate above 0 at LUMIERE. Otherwise it does not, and the result is reported as it is.
- **Multiplicity:** with three test arms, an arm whose MU CI only just excludes 0 is described as such, not as a
  clear gain.

**Also reported (descriptive):**
- the overall AUC and the across-window AUC (A_B) of every arm;
- the UCSF overall AUC (nearly all UCSF pairs lie within one window);
- the chosen C in every fit;
- for A-int, the fitted interaction coefficients from the locked fit.

## What follows from the result

- **If an arm improves:** it is reported as an analysis. Any change to PRISM's imaging model is the author's
  decision, and would need its own locked test.
- **If none improves:** the within-window AUC of about 0.68 is reported as what these image measurements carry once
  timing is held fixed.

## Outputs

- **Code:** `prism/analyses/imaging_s3.py`.
- **Results:** `outputs/results/analyses/imaging_s3/` and `docs/results/IMAGING_S3.md`, with any deviation marked and
  dated before the result it affects is read.
