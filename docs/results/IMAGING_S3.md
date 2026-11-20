# S3 results: a wider penalty grid and window-by-enhancement interactions for the imaging model

**Plan:** [IMAGING_S3_PLAN.md](IMAGING_S3_PLAN.md), commit d56297e, fixed before any fit.
**Code:** `prism/analyses/imaging_s3.py`. **Outputs:** `outputs/results/analyses/imaging_s3/`
(`stats.csv`, `mu_fits.csv`, `locked.json`). **Run:** 2026-11-20, 2,000 patient-bootstrap samples (seed 20261121),
26 s on 20 CPUs.

**Deviations:** none.
- **Implementation check (passed):** I0 reproduced the published MU AUC (0.709), and the S2 solver on the current
  grid (I-std) gave 0.714 (planned tolerance 0.01).
- **LUMIERE interactions:** the T_img set has only `log_et_cc` and `logratio_prev_et`, and the 3-volume model only
  `log_et_cc`, so the A-int interactions there are those, as the plan provides.

## Primary: within-window AUC (A_W), test arm minus the current imaging model (I0)

| Arm | MU | LUMIERE | Meets the rule? |
|---|---|---|---|
| I-wide (wide grid) | +0.004 (−0.005 to +0.014) | +0.000 (−0.001 to +0.001) | no |
| A-wide (stratified, wide grid) | −0.011 (−0.095 to +0.069) | −0.011 (−0.064 to +0.037) | no |
| A-int (stratified, interactions) | −0.013 (−0.098 to +0.067) | −0.011 (−0.065 to +0.036) | no |

**Verdict (plan's rule): no arm improves the within-window ranking.** I0's A_W is 0.677 at MU and 0.707 at LUMIERE.

## Descriptive

**AUC, within-window AUC (A_W) and across-window AUC (A_B):**

| Arm | MU AUC | MU A_W | MU A_B | LUMIERE AUC | LUMIERE A_W | UCSF AUC |
|---|---|---|---|---|---|---|
| I0 | 0.709 | 0.677 | 0.729 | 0.654 | 0.707 | 0.726 |
| A (S2) | 0.669 | 0.675 | 0.665 | 0.642 | 0.695 | 0.769 |
| I-wide | 0.713 | 0.682 | 0.733 | 0.654 | 0.707 | 0.726 |
| A-wide | 0.660 | 0.666 | 0.656 | 0.642 | 0.695 | 0.769 |
| A-int | 0.633 | 0.664 | 0.613 | 0.619 | 0.695 | 0.792 |

**Chosen penalty (25 MU fits):**
- The wider grid barely changed the choice. I-wide picked C = 0.003 once; A-wide and A-int picked C = 0.0003, the
  strongest penalty, in 4 fits each, and otherwise 0.01 or 0.03. The locked fits chose 0.01–0.1.
- So the penalty was not the limit. The fits that went to the edge shrank the image terms towards zero, and their
  A_W did not rise.

**Interaction coefficients (locked fit, standardised inputs):**
- With the T_img set, `early × log_et_cc` was +0.10 next to a main effect of +0.29.
- With the full 27-measurement set every interaction was +0.03 or smaller.
- Positive means enhancement weighed slightly *more* towards progression within 12 weeks after radiotherapy, not
  less as the treatment-effect reasoning expected. The terms are small, and A-int's within-window AUC fell slightly
  at both centres.

**UCSF:**
- A-int's AUC was 0.792, against 0.726 for I0: +0.066 (+0.014 to +0.123); its A_W difference was +0.069 (+0.018 to
  +0.126).
- UCSF is not part of the rule. Its window is approximated, and its early-window scans are few. This is an
  exploratory observation that MU and LUMIERE do not support.

## Reading

Neither a wider penalty grid nor letting enhancement carry a different weight in the first 12 weeks raised the
within-window ranking at MU or LUMIERE.

The within-window AUC of about 0.68 at MU (0.71 at LUMIERE) is what these image measurements carry once timing is
held fixed. The current imaging model's overall MU AUC of 0.71 includes 0.73 on pairs across windows, which A shows
comes from timing.

Together with the earlier deep-network, radiomics and resegmentation analyses, this places the limit in the
measurements and the sample (62 progression scans in 80 patients), not in the fit.
