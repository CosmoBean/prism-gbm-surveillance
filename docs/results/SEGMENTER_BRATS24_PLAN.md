# S4. A post-treatment segmenter: the BraTS 2024 first-place model as PRISM's segmentation stage (plan, fixed before any result)

The author's direction (2026-11-20) was to try the newer post-treatment segmenters and compare them with Swin UNETR
(S1, [SEGMENTER_STAGE_PLAN.md](SEGMENTER_STAGE_PLAN.md)). This plan is committed before any segmenter-derived number
is linked to a label. It follows S1 in every respect not stated here. The design is unchanged: MU-Glioma-Post is the
development cohort, and LUMIERE and UCSF-ALPTDG are the locked external tests.

## Segmenter (fixed, not tuned on any cohort)

- **Model:** BraTS24_1, the first-place model of the BraTS 2024 adult glioma post-treatment challenge (Ferreira et
  al., arXiv:2411.04632). It is an nnU-Net / MedNeXt ensemble, distributed by the BraTS orchestrator as
  `brainles/brats24_adult_glioma_faking_it:latest`, imported with enroot and run unchanged with its own thresholds.
- **Code:** `prism/features/reseg_brats24.py`.
- **Labels:** 1 NETC, 2 SNFH, 3 ET, 4 resection cavity (RC). This is the MU numbering, so no mapping is needed.
- **Inputs:** T1c, T1, T2 and FLAIR.
  - MU and UCSF are used as stored.
  - LUMIERE's atlas images are reoriented to LPS and the label map is mapped back, the same fixed step as S1.
- **Orientation and label check:** 3 scans per cohort, Dice against the released masks, no label read. The rule is
  S1's: if the median WT Dice is below 0.70, investigate before going on.

**Training-data note, recorded for the analysis.**
- The challenge paper (arXiv:2405.18368, Table 1) lists UCSF (about 600 cases, described as the UCSF longitudinal
  post-treatment glioma dataset) and the University of Missouri (about 400 cases) among the training sites.
- No progression label was used to train the segmenter.
- Agreement with the released masks (P2) is reported per cohort, as in S1.

## Measurements and models

- **Measurements:** `measurements.concepts_from_paths` and `add_deltas`, unchanged, on the BraTS24 maps.
- **Inputs:** because the maps contain the cavity, **all 27 imaging inputs** are built in every cohort from the
  segmenter ("BraTS24 inputs"). LUMIERE thus gets the full set too.
- **Models:** the S1 models and folds, with the BraTS24 inputs in place of S1's 22 segmenter inputs:
  - the imaging model;
  - the reduced combined model;
  - the timing-and-enhancement baseline (enhancing volume from the segmenter);
  - at MU, also the full combined model (exploratory, as in S1).
- **Folds and evaluation sets:** fitted in the 5 × 5 MU folds (intended use, 146 scans), locked on all MU training
  rows, and applied unchanged to LUMIERE (178) and UCSF (grade 4 scan 2, 69).
- **Reference values:** the released-mask reference AUCs are asserted to 0.001 before any comparison, as in S1.

## Questions and rules

**P1 (planned, primary): does PRISM from the BraTS24 segmenter reproduce PRISM from the released masks?**
- Same statistic and rule as S1: paired BraTS24 − released AUC differences for the imaging, reduced combined and
  baseline scores at each cohort.
- One 2,000-sample patient bootstrap per cohort (seed 20261120).
- **The rule:** every paired CI must include 0 or lie above it. At MU and LUMIERE, the gain of the reduced combined
  model over the baseline must be read the same way under both mask sets.

**P2 (planned, secondary, descriptive): agreement with the released masks.**
- Median ET, WT and RC Dice per cohort.
- LUMIERE: ET and WT only, because its masks have no separate cavity.

**P3 (planned, secondary): repeatability.**
- Median fold change of the enhancing volume between consecutive scans at most 30 days apart, at MU and LUMIERE.
- Compared with the released masks and with Swin UNETR (S1).

**P4 (planned, secondary): BraTS24 against Swin UNETR.**
- Paired BraTS24 − Swin UNETR AUC differences for the same three scores. Both use their segmenter inputs: 27 for
  BraTS24, 22 for Swin UNETR.
- Paired Dice differences.
- **No pass rule:** it says which segmenter brings PRISM closer to its released-mask results.

**Exploratory:** BraTS24 on the 22 cavity-free inputs, which separates the effect of the segmenter from the effect
of the cavity inputs. The second- and third-place models, if time allows.

## What does not change

- The paper's primary numbers stay on the released masks.
- Fine-tuning is not part of this plan. It would be planned separately, in patient-grouped folds, only if P1 or P2
  shows a clear shortfall at LUMIERE.

## Outputs

- **Label maps:** `outputs/features/seg_brats24/{mu,lumiere,ucsf}/`.
- **Volumes and Dice:** `volumes_brats24_<cohort>.csv`.
- **Measurements:** `outputs/features/seg_brats24/measurements_<cohort>.csv`.
- **Results:** `docs/results/SEGMENTER_BRATS24.md`, with every deviation from this plan marked and dated.
