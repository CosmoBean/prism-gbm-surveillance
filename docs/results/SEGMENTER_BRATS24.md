# S4. The BraTS 2024 first-place model as PRISM's segmentation stage (results)

Plan: [SEGMENTER_BRATS24_PLAN.md](SEGMENTER_BRATS24_PLAN.md), committed before any segmenter-derived number was linked
to a label. Run 2026-11-20. Code: `prism/features/reseg_brats24.py` (maps), `scripts/analyse_brats24.sh` →
`prism.features.seg_measurements --segmenter brats24` and `prism.analyses.segmenter_stage --segmenter brats24`.
Outputs: `outputs/results/analyses/segmenter_brats24/` (`s4_*.csv`, `run_info.json`, `analyse_20261120_0951.log`).
2,000 patient-bootstrap samples per cohort, seed 20261120.

## Run

- **Maps:** every scan in the plan's scope, no failures.
  - MU: 258 of 258 (oc3, 4 GPUs, 05:30–08:42).
  - UCSF: 138 of 138 (oc3, 03:38–05:29).
  - LUMIERE: 328 of 328.
    - Chunks 00–02 (246 studies) ran on a second account's 4 GPUs with the same code, container and scan list (04:25–07:47).
    - Chunk 03 (82 studies) ran on oc3 (08:43–09:51).
- **Reference check:** the released-mask AUCs reproduced to 0.001 before any comparison (`s4_reference_check.csv`).
- **Deviations from the plan:** none beyond the scope narrowing recorded in the plan before the run. Running LUMIERE
  on a second account is an implementation detail: same code, same container image, same scan list.

## P1 (planned, primary): does PRISM from the BraTS24 segmenter reproduce PRISM from the released masks?

AUC from the released masks, from the BraTS24 maps (27 inputs), and the paired difference (95% CI):

| cohort | score | released | BraTS24 | BraTS24 − released |
|---|---|---|---|---|
| MU | imaging | 0.71 | 0.68 | −0.03 (−0.07 to +0.02) |
| MU | reduced combined | 0.80 | 0.82 | +0.02 (−0.02 to +0.05) |
| MU | time-and-enhancement | 0.80 | 0.78 | **−0.02 (−0.04 to −0.003)** |
| MU (exploratory) | full combined | 0.82 | 0.80 | −0.02 (−0.04 to +0.01) |
| LUMIERE | imaging | 0.65 | 0.67 | +0.01 (−0.06 to +0.09) |
| LUMIERE | reduced combined | 0.77 | 0.75 | −0.03 (−0.09 to +0.04) |
| LUMIERE | time-and-enhancement | 0.73 | 0.81 | +0.07 (+0.03 to +0.12) |
| UCSF | imaging | 0.73 | 0.80 | +0.08 (+0.01 to +0.15) |
| UCSF | reduced combined | 0.86 | 0.80 | −0.06 (−0.15 to +0.01) |
| UCSF | time-and-enhancement (approximated window) | 0.87 | 0.88 | +0.01 (−0.00 to +0.03) |

Gain of the reduced combined model over the time-and-enhancement model:

| cohort | released masks | BraTS24 | change |
|---|---|---|---|
| MU | +0.01 (−0.05 to +0.07) | +0.04 (−0.01 to +0.10) | +0.03 (−0.00 to +0.07) |
| LUMIERE | +0.04 (−0.01 to +0.10) | **−0.06 (−0.12 to −0.002)** | −0.10 (−0.16 to −0.04) |
| UCSF (descriptive) | −0.01 (−0.08 to +0.05) | −0.08 (−0.16 to −0.01) | −0.07 (−0.16 to +0.00) |
| MU, full combined (exploratory) | +0.02 (−0.04 to +0.08) | +0.02 (−0.04 to +0.09) | +0.00 (−0.03 to +0.03) |

**Verdict, by the plan's rule: the BraTS24 stage does not reproduce the released-mask results.** Two parts of the
rule fail:
- **One paired CI lies below zero:** the MU time-and-enhancement model, −0.017 (−0.037 to −0.003). It is a small
  loss.
- **The gain reading changes at LUMIERE:**
  - Released masks: the reduced combined model shows no clear gain over the time-and-enhancement model.
  - BraTS24 maps: it falls below that model (−0.06, CI excluding 0).
  - The change comes from the simpler model, whose LUMIERE AUC rises from 0.73 to 0.81 with the BraTS24 enhancing
    volume, while the combined model moves by −0.03.

**The other paired CIs include zero or lie above it.** The MU imaging model, which lost 0.08 with Swin UNETR (S1, CI
below zero), loses 0.03 here (CI includes 0).

## P2 (planned, secondary, descriptive): agreement with the released masks

Median Dice [IQR] on the scans of the scope; Swin UNETR (S1) on the same scans:

| cohort | compartment | BraTS24 | Swin UNETR | share of scans with Dice < 0.5 (BraTS24 / Swin) |
|---|---|---|---|---|
| MU | ET | 0.94 [0.82, 0.97] | 0.79 [0.45, 0.91] | 0.11 / 0.28 |
| MU | WT | 0.97 [0.94, 0.98] | 0.85 [0.75, 0.92] | 0.02 / 0.09 |
| MU | RC | 0.92 [0.69, 0.96] | not segmented | 0.18 |
| LUMIERE | ET | 0.64 [0.05, 0.92] | 0.74 [0.36, 0.93] | 0.45 / 0.32 |
| LUMIERE | WT | 0.82 [0.67, 0.91] | 0.90 [0.75, 0.95] | 0.08 / 0.11 |
| UCSF | ET | 0.91 [0.85, 0.94] | 0.80 [0.50, 0.89] | 0.01 / 0.25 |
| UCSF | WT | 0.92 [0.90, 0.95] | 0.82 [0.71, 0.88] | 0.00 / 0.09 |
| UCSF | RC | 0.93 [0.87, 0.96] | not segmented | 0.02 |

- **LUMIERE's reference masks** are DeepBraTumIA's automatic labels, not expert outlines.
  - They label enhancement along the cavity wall, which the BraTS 2024 label rules exclude, and their NETC includes
    the cavity (plan, orientation check).
  - Lower agreement at LUMIERE therefore partly measures a difference in label convention.
- **Training data (plan, training-data note):** the challenge lists UCSF (the UCSF post-treatment dataset) and the
  University of Missouri among its training sites. Agreement at UCSF, and possibly at MU, is not an external
  measure. LUMIERE is not a listed site.

## P3 (planned, secondary): repeatability

Median fold change of the enhancing volume between consecutive scans at most 30 days apart (95% CI):

| cohort | pairs (patients) | released | BraTS24 | Swin UNETR |
|---|---|---|---|---|
| MU | 14 (14) | 2.21 (1.24–3.44) | 2.10 (1.29–6.17) | 1.76 (1.49–3.09) |
| LUMIERE | 15 (13) | 2.60 (1.56–10.46) | 14.44 (5.19–39.49) | 4.69 (2.38–10.49) |

- **MU:** no difference from the released masks.
- **LUMIERE:** the BraTS24 enhancing volume changes far more between scans taken within 30 days than either the
  released or the Swin UNETR volume. The difference in median |log ratio| from the released masks is +1.71 (+0.58 to
  +2.41).
  - The pairs are few (15).
  - The likely mechanism is enhancement called present at one scan and absent at the next: 45% of LUMIERE scans have
    an ET Dice below 0.5.
  - This is not examined further here.

## P4 (planned, secondary, no pass rule): BraTS24 (27 inputs) against Swin UNETR (22 inputs)

| cohort | score | Swin UNETR | BraTS24 | BraTS24 − Swin |
|---|---|---|---|---|
| MU | imaging | 0.63 | 0.68 | +0.05 (−0.01 to +0.11) |
| MU | reduced combined | 0.81 | 0.82 | +0.01 (−0.02 to +0.04) |
| MU | time-and-enhancement | 0.78 | 0.78 | +0.00 (−0.02 to +0.03) |
| LUMIERE | imaging | 0.66 | 0.67 | +0.01 (−0.05 to +0.07) |
| LUMIERE | reduced combined | 0.75 | 0.75 | −0.01 (−0.06 to +0.06) |
| LUMIERE | time-and-enhancement | 0.78 | 0.81 | +0.03 (−0.01 to +0.07) |
| UCSF | imaging | 0.82 | 0.80 | −0.01 (−0.10 to +0.07) |
| UCSF | reduced combined | 0.82 | 0.80 | −0.03 (−0.11 to +0.06) |
| UCSF | time-and-enhancement | 0.88 | 0.88 | −0.00 (−0.03 to +0.03) |

Paired Dice, BraTS24 − Swin UNETR (median per-scan difference; share of scans where BraTS24 is higher):
- **MU:** ET +0.09 (0.92), WT +0.10 (0.97).
- **UCSF:** ET +0.11 (0.97), WT +0.10 (1.00).
- **LUMIERE:** ET −0.01 (0.29), WT −0.01 (0.43).

**Reading:**
- On AUC, the two segmenters bring PRISM about equally close to its released-mask results. BraTS24 is closer for the
  MU imaging model and Swin UNETR is closer at LUMIERE.
- On Dice, BraTS24 is clearly closer at MU and UCSF, the two cohorts drawn from its training sites, and slightly
  further at LUMIERE, the one cohort it was not trained on.

## Exploratory: BraTS24 on the 22 cavity-free inputs

This separates the segmenter from the cavity inputs. It is not part of any rule.

| cohort | score | released | BraTS24, 27 inputs | BraTS24, 22 inputs |
|---|---|---|---|---|
| MU | imaging | 0.71 | 0.68 | 0.71 |
| MU | reduced combined | 0.80 | 0.82 | 0.84 |
| LUMIERE | imaging | 0.65 | 0.67 | 0.69 |
| LUMIERE | reduced combined | 0.77 | 0.75 | 0.79 |
| UCSF | imaging | 0.73 | 0.80 | 0.80 |
| UCSF | reduced combined | 0.86 | 0.80 | 0.81 |

- **The cavity inputs lower the BraTS24 results** at MU and LUMIERE. Dropping them raises the imaging model by
  +0.03 at both (CIs above 0) and the reduced combined model by +0.02 at MU and +0.04 at LUMIERE (CIs above 0).
- **With 22 inputs, PRISM from the BraTS24 maps matches the released masks:**
  - MU imaging 0.708 against 0.709;
  - LUMIERE reduced combined 0.79 against 0.77.
- **The LUMIERE gain over the time-and-enhancement model** is −0.02 (released +0.04). The change, −0.06 (−0.11 to
  −0.01), still excludes 0.
- **It is the plan's exploratory arm**, reported as such. It cannot replace the planned 27-input result.

## Calibration (descriptive)

`s4_calibration.csv`. At LUMIERE the BraTS24 imaging score has slope 0.56 (released 1.91). The reduced combined
score has slope 0.97 (released 1.45), its intercept moving from −0.07 to +0.07.

## Summary

- **The planned stage does not reproduce the released-mask results**, by the plan's rule. The failures are small and
  specific:
  - a −0.02 loss for the MU time-and-enhancement model;
  - a change in the LUMIERE gain reading, driven by a better LUMIERE time-and-enhancement model rather than a worse
    combined model.
- **Compared with Swin UNETR (S1):**
  - BraTS24 removes S1's one failure (the MU imaging loss, −0.08 → −0.03).
  - It segments the cavity, so all 27 inputs can be built.
  - Its outlines agree far better with the released masks at the two cohorts drawn from its training sites.
- **At LUMIERE, the one unseen cohort,** it agrees slightly less with the reference masks than Swin UNETR does, and
  its enhancing volume is much less repeatable between closely spaced scans.
- **The paper's primary numbers stay on the released masks,** as the plan states. Whether to report S4 in the
  supplement, and with which framing, is the author's decision.
