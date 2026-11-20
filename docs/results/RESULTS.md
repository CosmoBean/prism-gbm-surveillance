# PRISM results (one page)

Numbers only; detail in the linked documents. The decision record is [SEGMENTER_SWITCH.md](SEGMENTER_SWITCH.md)
(2026-11-20): primary = PRISM's own segmenter (BraTS24, 22 inputs); reference = released masks.

## 1. Primary: PRISM end to end (BraTS24 segmenter, 22 inputs)

System rerun 2026-11-20 (`PRISM_MASKS=brats24_22`, commit e06cca3; `outputs/results/analyses/system_brats24_22/`).
Scores equal S4's `segmenter22` predictions exactly. CIs: 2,000 patient-bootstrap samples (S4).

| cohort | clinical history | imaging | combined | time-and-enhancement |
|---|---|---|---|---|
| MU | 0.82 (0.75–0.90) | 0.71 (0.64–0.78) | 0.82 (0.76–0.89) | 0.78 (0.70–0.87) |
| LUMIERE | 0.69 (0.60–0.81) | 0.69 (0.61–0.77) | 0.79 (0.72–0.86) | 0.81 (0.73–0.87) |
| UCSF-ALPTDG | 0.56 (0.42–0.69) | 0.80 (0.68–0.89) | 0.81 (0.70–0.90) | 0.88 (0.79–0.95)† |

Combined at MU is the full combined model; at LUMIERE and UCSF it is the reduced one.

**Coverage of the combined 80% sets:**
- MU 0.82 (0.77–0.87);
- LUMIERE 0.82 (0.76–0.87);
- UCSF 0.80 (0.71–0.88).

**Reliability-card tiers (tested / few cases):**
- MU 51 / 95;
- LUMIERE 167 / 11;
- UCSF 0 / 69.

**Gain over the time-and-enhancement model** (segmenter; released masks in brackets):

| cohort | clinical history | imaging | combined |
|---|---|---|---|
| MU | +0.04 (+0.02) | −0.07 (−0.09) | +0.04 (+0.02) |
| LUMIERE | −0.12, CI below 0 (−0.05) | −0.11 (−0.08) | −0.02 (+0.04) |
| UCSF† | −0.31, CI below 0 (−0.30) | −0.08 (−0.14) | −0.07, CI below 0 (−0.01) |

**Enhancing volume alone:** MU 0.61, LUMIERE 0.70.

**Calibration slopes** (segmenter; released in brackets):
- MU imaging 0.83 (0.75).
- LUMIERE imaging 0.67 (1.91), intercept +0.32 (+0.41).
- LUMIERE combined 1.73 (1.45).
- UCSF combined 1.82 (3.29).

**Coverage by group (Figure 5):**
- LUMIERE progression scans 0.63 (released 0.77).
- UCSF overall 0.80 (0.78).

**Reports:** rerun pending.

## 2. Reference: released masks (current paper numbers)

AUC (95% CI), Figure 3:

| cohort | clinical history | imaging | combined | time-and-enhancement | enhancing volume alone |
|---|---|---|---|---|---|
| MU | 0.82 (0.75–0.90) | 0.71 (0.63–0.78) | 0.82 (0.74–0.89) | 0.80 (0.71–0.88) | 0.62 (0.53–0.72) |
| LUMIERE | 0.69 (0.60–0.81) | 0.65 (0.56–0.73) | 0.77 (0.68–0.86) | 0.73 (0.64–0.81) | 0.66 (0.56–0.75) |
| UCSF-ALPTDG | 0.56 (0.42–0.69) | 0.73 (0.60–0.84) | 0.86 (0.76–0.93) | 0.87 (0.77–0.94)† | 0.88 (0.79–0.95) |

† Approximated radiotherapy window, outside the planned comparison.

**Calibration (Supplementary Figure S1):**
- MU: slopes about 0.75.
- LUMIERE: imaging intercept +0.41.
- UCSF: combined slope 3.29.

**Reports:** 406 of 406 passed the checker (Qwen3.8-27B).

## 3. Segmenter comparisons

| | S1 Swin UNETR (22 inputs) | S4 BraTS24 (27 inputs, planned) | BraTS24 (22 inputs) |
|---|---|---|---|
| Rule: reproduces the released masks | no (MU imaging −0.08) | no (MU baseline −0.017; LUMIERE gain flips) | not tested by a rule |
| MU imaging | 0.63 | 0.68 | 0.71 |
| LUMIERE reduced combined | 0.75 | 0.75 | 0.79 |
| UCSF reduced combined | 0.82 | 0.80 | 0.81 |
| ET Dice, MU / LUMIERE / UCSF | 0.79 / 0.74 / 0.80 | 0.94 / 0.64 / 0.91 | same maps as S4 |
| ET fold change ≤30 d, LUMIERE | 4.7 | 14.4 (released 2.6) | same maps as S4 |

Documents:
- [SEGMENTER_STAGE.md](SEGMENTER_STAGE.md) (S1)
- [SEGMENTER_BRATS24.md](SEGMENTER_BRATS24.md) (S4)
- [IMAGING_S3.md](IMAGING_S3.md) (imaging improvement tests: no arm improves the within-window AUC)
