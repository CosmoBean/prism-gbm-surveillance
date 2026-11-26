# S2. A stratified imaging model and an offset combined model (results)

Plan: `docs/results/STRATIFIED_OFFSET_PLAN.md` (commit 1856aa9), fixed before any fit. Code:
`prism/analyses/stratified_offset.py`. Output: `outputs/results/analyses/stratified_offset/`.

## How to run

    PRISM_SKIP_UCSF=0 PYTHONPATH=. .venv/bin/python -m prism.analyses.stratified_offset --workers 20 --n-boot 2000

`--reference-only` reproduces the current models' AUCs and stops. CPU only.

## 1. Implementation choices (written 2026-11-19, before any result of A or B was read)

- **Solver.** Both models minimise C · Σ log loss + ½|β|² with a custom L-BFGS objective (`fit_lr`). This is
  sklearn's ridge-logistic objective (lbfgs leaves the intercept unpenalised). The free intercepts (A: one per window;
  B: one overall) carry a penalty of 10⁻⁸ · ½a², which keeps an intercept finite in a window with only one outcome
  and is otherwise negligible (relative weight ≤ 10⁻⁶ on the grid). Toy checks, asserted at every run
  (`toy_checks.json`):
  - one intercept, no offset: coefficients equal sklearn's to < 10⁻⁹;
  - window intercepts: equal an independent Newton solve (< 10⁻⁷); with no informative inputs they equal the
    empirical window logits (< 10⁻⁵); they equal sklearn with the window dummies scaled by 10⁴ (< 2 × 10⁻⁴). The
    same dummies penalised as ordinary inputs differ by up to 2.6 on the logit scale, so the partial penalty matters;
  - offset: equals an independent Newton solve (< 10⁻⁹); adding a constant to the offset moves only the intercept
    (< 10⁻⁸), i.e. the offset's coefficient is fixed at 1.
- **Penalty choice.** C in (0.01, 0.03, 0.1, 0.3, 1, 3), GroupKFold(3) by patient on the labelled training rows,
  mean log loss (clipped at 10⁻⁶), as `formulations.fit`. The same inputs and `c3.BASE_PRE` (median imputation with
  missing indicators, standardisation) as the current models, fitted on the labelled training rows.
- **A, windows.** The plan's four MU windows (during RT, within 12 weeks after it, later, unknown) are the card's
  phase cells, `system.mu_situation`: before the end of RT (pre-RT and during-RT scans with RT dates), early post-RT,
  later post-RT, unknown (no RT dates). The intercepts use these cells. Q1's A_W keeps M1's strata (`d.phase` at MU;
  the rater's flag at LUMIERE), so the evaluation is M1's. "Before the end of RT" has no progression among the
  labelled MU rows (12 scans), so its intercept goes to a large negative value and those rows carry no information
  for β, as in conditional logistic regression.
- **A, inner CV.** The window intercepts are in the model during C selection. A validation row whose window is
  absent from the inner training rows takes the row-weighted mean of the fitted intercepts.
- **A, designs per centre.** A replaces the current imaging model with the same inputs at each centre: MU and UCSF
  A-Ipure (27 inputs); LUMIERE T_img (6 inputs), and the 3-volume model for the scans without a previous scan, as
  the paper's LUMIERE imaging score. All are fitted on MU with the MU windows.
- **B, offset.** η_base is the baseline's logit, fitted on the same training rows exactly as the E4 baseline (MU:
  `clinician_baseline.mu_reader_design` with the c3 pipeline; locked: early_post_rt + log ET + log ratio + has_prev
  on all MU rows, `system._fit`). The test-fold offset is asserted to equal the E4 baseline's prediction (< 10⁻⁶).
  During C selection the offset is the training-fold baseline's in-sample logit on every training row (it is not
  refitted inside the inner folds).
- **B, intercept.** B keeps one free intercept b₀ as well as the offset (logit p = η_base + b₀ + β·z), as every
  current model has one. The increment recorded is β·z; b₀ is reported per fit.
- **B, inputs.** MU: the current combined model's inputs (B1 + A-Ipure, 48). LUMIERE and UCSF: the reduced
  combined inputs T (14), with the locked reduced baseline as the offset. UCSF uses the approximated window
  (`early_post_rt` from `rt_phase`), as in S1.
- **References** (asserted to 0.001 before any comparison): MU imaging 0.709 (A_W 0.68, A_B 0.73, to 0.01),
  combined 0.821, baseline 0.797, reduced combined 0.804; LUMIERE imaging 0.654, reduced combined 0.773, baseline
  0.734; UCSF imaging 0.726, reduced combined 0.856, baseline 0.866 (S1; not in the paper).
- **Statistics.** One 2,000-sample patient-cluster bootstrap per cohort (seed 20261120) covers every score, so the
  differences are paired; held-out predictions are resampled without refitting. MU AUCs are means over the five
  repeats (M1's `m1_stats` / `boot`). Q1 and Q2 rules as the plan: pass if the paired CI's upper bound is ≥ 0.
- **Exploratory, as planned.** Calibration (slope, O/E, intercept) of A with its MU window intercepts (MU only:
  the external centres have no matching windows) and of B at each centre. Conformal coverage at α = 0.2 of B and
  of the current combined model, with the system's splits (MU: 70/30 inside each training fold, seed 10r + k;
  external: MU split seed 0). Not run: the same fits on S1's segmenter inputs.

## 2. Deviations

None at the time of writing.

## 3. Reference reproduction

Every reference reproduced within the asserted tolerance before any comparison (`s2_reference_check.csv`): MU
imaging 0.709 (A_W 0.677, A_B 0.729), combined 0.821, baseline 0.797, reduced combined 0.804; LUMIERE imaging 0.654,
reduced combined 0.773, baseline 0.734; UCSF imaging 0.726, reduced combined 0.856, baseline 0.866. The MU offset
equals the E4 baseline's held-out prediction in every fold (< 10⁻⁶).

Evaluation sets: MU 146 scans (62 progression, 80 patients); LUMIERE 178 (73, 79); UCSF 69 (29, 69).

## 4. Results

Output: `s2_auc.csv` (AUC, A_W, A_B with CIs; paired differences), `s2_calibration.csv`, `s2_conformal.csv`,
`s2_increment.csv`, `scores.npz`, `run_info.json` (chosen C and intercepts per fit), `toy_checks.json`.
Intervals: 95% percentile intervals over 2,000 patient-cluster bootstrap samples (seed 20261120), paired.

### Q1. The stratified imaging model A against the current imaging model

| cohort | stat | current imaging | A | A − current (paired) |
|---|---|---|---|---|
| MU | A_W (within window) | 0.68 (0.58–0.77) | 0.68 (0.58–0.78) | −0.00 (−0.09 to +0.08) |
| MU | A_B (across windows) | 0.73 (0.65–0.81) | 0.67 (0.57–0.76) | −0.06 (−0.12 to −0.01) |
| MU | AUC | 0.71 (0.63–0.78) | 0.67 (0.59–0.75) | −0.04 (−0.10 to +0.02) |
| LUMIERE | A_W | 0.71 (0.61–0.80) | 0.70 (0.59–0.79) | −0.01 (−0.07 to +0.04) |
| LUMIERE | A_B | 0.51 (0.39–0.64) | 0.49 (0.38–0.62) | −0.01 (−0.08 to +0.04) |
| LUMIERE | AUC | 0.65 (0.57–0.73) | 0.64 (0.55–0.73) | −0.01 (−0.06 to +0.03) |
| UCSF | AUC | 0.73 (0.59–0.83) | 0.77 (0.65–0.87) | +0.04 (−0.00 to +0.09) |

At UCSF, A_W (by `rt_phase`) was 0.74 for the current model and 0.78 for A (+0.04, −0.01 to +0.09); few pairs lie
across windows there.

**Verdict (plan's rule): A keeps the within-window ranking.** The paired A_W difference includes 0 at MU and at
LUMIERE. The point estimates are close to 0 at both centres (−0.00, −0.01): the within-window ranking is kept, not
raised. As the plan expected, the across-window AUC fell at MU (−0.06, interval below 0) and the overall AUC fell at
MU (−0.04, interval includes 0). At LUMIERE every difference is small and includes 0. At UCSF the overall AUC of A
was 0.04 higher (interval −0.00 to +0.09).

Fitted window intercepts (locked A-Ipure fit on all MU rows, logit scale): before the end of RT −14.8 (no
progression in that window), early post-RT −2.9, later post-RT +0.5, unknown −1.5. The chosen C was 0.01 or 0.03 in
every fit.

### Q2. The offset combined model B against the current combined model

| cohort | current combined | B | B − current (paired) |
|---|---|---|---|
| MU (full combined) | 0.82 (0.75–0.89) | 0.81 (0.73–0.89) | −0.01 (−0.05 to +0.03) |
| LUMIERE (reduced) | 0.77 (0.69–0.86) | 0.75 (0.67–0.83) | −0.02 (−0.07 to +0.02) |
| UCSF (reduced) | 0.86 (0.76–0.94) | 0.87 (0.78–0.94) | +0.01 (−0.05 to +0.08) |

**Verdict (plan's rule): B ranks scans as well as the combined model.** Every paired interval includes 0.

Within and across windows at MU, B − combined: A_W −0.04 (−0.09 to +0.01), A_B +0.01 (−0.04 to +0.06). At
LUMIERE: A_W −0.02 (−0.09 to +0.03), A_B −0.01 (−0.04 to +0.01).

The chosen C was the smallest of the grid (0.01) in 19 of the 25 MU fits and in the locked fit, so the increment is
strongly shrunk. Its spread (SD of β·z on the logit scale) was 0.85 at MU, 0.10 at LUMIERE and 0.11 at UCSF; the
free intercept b₀ was between −0.22 and −0.01 at MU and 0.003 in the locked fit.

### Q3. The increment: gain of B over the baseline, compared with E4

| cohort | B − baseline (S2) | combined − baseline, same bootstrap | E4 / S1 reference |
|---|---|---|---|
| MU | +0.02 (−0.02 to +0.05) | +0.02 (−0.04 to +0.08) | E4 +0.02 (−0.03 to +0.08) |
| LUMIERE | +0.02 (+0.00 to +0.04) | +0.04 (−0.01 to +0.10) | E4 +0.04 (−0.01 to +0.10) |
| UCSF | +0.00 (−0.01 to +0.02) | −0.01 (−0.08 to +0.05) | S1 −0.01 (−0.07 to +0.05) |

LUMIERE, exactly: +0.019 (+0.003 to +0.039).

**Reading (no pass rule).** At MU and UCSF the gain of B over the baseline has an interval that includes 0, as in
E4 and S1. At LUMIERE the interval excludes 0 (+0.02, +0.003 to +0.04), where E4's combined − baseline interval
included 0 (+0.04, −0.01 to +0.10). The point estimate is smaller than E4's; the interval is narrower because B
stays close to the baseline by construction. Within windows, B − baseline was +0.04 (−0.06 to +0.11) at MU and
+0.02 (+0.00 to +0.05) at LUMIERE.

### Exploratory

**The increment alone** (β·z as a score, without the offset): AUC 0.73 (0.66–0.80) at MU, 0.62 (0.53–0.70) at
LUMIERE and 0.52 (0.39–0.67) at UCSF; A_W 0.67 at MU and 0.62 at LUMIERE.

**Calibration** (slope, O/E, calibration-in-the-large; MU mean over repeats):

| cohort | score | slope | O/E | intercept |
|---|---|---|---|---|
| MU | A with its MU window intercepts | 0.85 | 1.01 | +0.03 |
| MU | current imaging | 0.75 | 1.13 | +0.24 |
| MU | B | 0.75 | 0.96 | −0.12 |
| MU | current combined | 0.75 | 0.98 | −0.05 |
| LUMIERE | B | 0.78 | 1.03 | +0.06 |
| LUMIERE | current reduced combined | 1.45 | 0.97 | −0.07 |
| UCSF | B | 2.03 | 0.74 | −0.69 |
| UCSF | current reduced combined | 3.29 | 0.72 | −0.73 |

**Conformal sets at α = 0.2** (target coverage 0.80):

| cohort | model | coverage | progression | no progression | {0, 1} sets |
|---|---|---|---|---|---|
| MU | B | 0.80 | 0.83 | 0.78 | 0.19 |
| MU | current combined | 0.82 | 0.82 | 0.83 | 0.25 |
| LUMIERE | B | 0.76 | 0.64 | 0.85 | 0.19 |
| LUMIERE | current reduced combined | 0.87 | 0.77 | 0.94 | 0.38 |
| UCSF | B | 0.74 | 0.86 | 0.65 | 0.10 |
| UCSF | current reduced combined | 0.78 | 0.97 | 0.65 | 0.36 |

**Not run:** the same fits on S1's segmenter inputs.

## 5. Summary

- Q1 (planned, primary for A): by the rule, the within-window objective keeps the within-window ranking at MU and
  LUMIERE. A_W is unchanged (−0.00 and −0.01); A_B fell at MU (−0.06, −0.12 to −0.01).
- Q2 (planned, primary for B): by the rule, B ranks scans as well as the current combined model at all three
  centres (−0.01, −0.02, +0.01; every interval includes 0).
- Q3 (secondary): B's gain over the baseline includes 0 at MU and UCSF and excludes it at LUMIERE (+0.02, +0.003 to
  +0.04); E4's combined − baseline gain included 0 at both MU and LUMIERE.
- Runtime: 33 s for the full run on 20 CPUs (Slurm), after a 9 s reference-only run.
