# PRISM results (one page)

Numbers only; detail in the linked documents. The decision record is [SEGMENTER_SWITCH.md](SEGMENTER_SWITCH.md)
(2026-11-20): primary = PRISM's own segmenter (BraTS24, 22 inputs); reference = released masks.

## 1. Primary: PRISM end to end (BraTS24 segmenter, 22 inputs)

From S4's `segmenter22` arm (`outputs/results/analyses/segmenter_brats24/`). **Rerun of the full system (conformal
sets, cards, reports) pending.**

| cohort | imaging | combined (reduced) | combined (full, MU) | time-and-enhancement |
|---|---|---|---|---|
| MU | 0.71 | 0.84 | 0.82 | 0.78 |
| LUMIERE | 0.69 | 0.79 | — | 0.81 |
| UCSF-ALPTDG | 0.80 | 0.81 | — | 0.88 (approximated window) |

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
