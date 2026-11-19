# S2. A stratified imaging model and an offset combined model (plan, fixed before any result)

This plan follows the author's question of 2026-11-19: could a training objective build the paper's argument into
the scores themselves? It is committed before either model is fitted. The current models stay the reference, and
nothing in the paper changes until the author has seen the results.

## The two models

Both are ridge logistic regressions, as now. They use the same inputs, standardisation, imputation, penalty grid
(C in 0.01, 0.03, 0.1, 0.3, 1, 3, chosen by threefold patient-grouped CV, log loss), the same 5×5 MU folds and the same
intended-use evaluation set. The released masks are used, as in the paper. Only the objective changes.

**A. The stratified imaging model** (within-window objective).

- **Fit.** The model is fitted with one unpenalised intercept per time window (MU: during radiotherapy, within 12
  weeks after it, later, unknown). The 27 image measurements are penalised as now.
  - With four windows of many scans each, this fixed-effects fit approximates conditional logistic regression on the
    windows (Breslow and Day 1980). The image coefficients are then estimated from contrasts within a window.
- **Score.** The score is the image part of the linear predictor, β·x_img. The window intercepts are dropped, so the
  score needs no dates, as the imaging model does now.
- **Windows** are used only in training, on MU, so the locked model applies unchanged at LUMIERE and UCSF.

**B. The offset combined model** (gain-over-baseline objective).

- **Fit.** logit p = η_base + β·z. Here η_base is the logit of the timing-and-enhancement baseline (E4), fitted
  within the same training fold and entered as a fixed offset (coefficient 1, not refitted). z holds the combined
  model's inputs, penalised as now.
- **Two quantities are recorded:**
  - the score p, used for AUCs and conformal sets;
  - the increment β·z: what the images and the history add to the baseline at this scan.
- **Externally:** in the reduced form, with the locked reduced baseline as the offset (LUMIERE: the rater's window
  flag; UCSF: the approximated window, as in the paper).

## Questions and rules

### Q1 (planned, primary for A): does the within-window objective keep the within-window ranking?

- **Comparison:** the within-window AUC (A_W, the M1 split) of A against the current imaging model. These are paired
  patient-bootstrap differences (2,000 samples, seed 20261120) at MU and LUMIERE.
- **Rule:** A keeps the within-window ranking if the paired difference's CI includes 0 or lies above it at both
  centres.
- **Also reported:** the across-window AUC (A_B), the overall AUC of both models, and the UCSF overall AUC. At UCSF
  nearly all pairs lie within one window.
- **Expectation, stated now:** A_B and the overall AUC of A fall, while A_W holds.

### Q2 (planned, primary for B): does the offset model rank scans as well as the combined model?

- **Comparison:** the AUC of B against the current combined model (reduced form externally), as paired differences at
  MU, LUMIERE and UCSF.
- **Rule:** B ranks as well if every paired CI includes 0 or lies above it.

### Q3 (planned, secondary): the increment

- **What is reported:** the AUC gain of B over the baseline, with its CI, at each centre. Because B is defined as the
  baseline plus an increment, this restates E4's question for a score built that way.
- **No pass rule:** the reading (CI includes 0 or excludes it) is stated and compared with E4.

### Exploratory

- Calibration of A, after a per-window intercept fitted on MU, and of B.
- 80% conformal coverage with B in place of the combined model.
- The same fits on S1's segmenter inputs.

## What would change in the system, if the author adopts them

- **If Q1 holds:** the imaging score in the record becomes the within-window score. The card could then state
  "holding the time window fixed".
- **If Q2 holds:** the combined score is reported as the baseline plus its increment, and the record gains a field
  for the increment.
- **Either way:** the locked models, the paper's numbers and the abstract stay as they are unless the author decides
  otherwise.

## Outputs

- **Code:** `prism/analyses/stratified_offset.py`.
- **Results:** `outputs/results/analyses/stratified_offset/` and `docs/results/STRATIFIED_OFFSET.md`, with any
  deviation marked and dated before the result it affects is read.
