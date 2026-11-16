# Plan: the published pipeline on the BraTS21 masks (2026-11-16)

Written after E5 and the faithful run were reported. It is written before any radiomic feature has been extracted
from the BraTS21 masks, and committed before the run. Results go to CHRISTODOULOU_REPLICATION.md, section "Faithful
run on the BraTS21 masks", unchanged, including an unfavourable result.

## Why
On the released MU masks the published pipeline, run with its authors' code, ranked scans below PRISM's imaging
model: 0.580 against 0.709, difference −0.129 (−0.231 to −0.022). With every mask taken from the BraTS21 SwinUNETR
(E5), the imaging model fell to 0.627. The pipeline was not run on those masks, so the imaging comparison is known on
one mask set only. This run makes the comparison symmetric.

## What changes
Only the mask. Everything else is the faithful run as committed (CHRISTODOULOU_FAITHFUL_PLAN.md, b1ce85b;
deviations e636073; code a1cd1d7):
- **Masks:** the BraTS21 SwinUNETR label maps already produced for E5 (`outputs/features/seg_swin/mu/`, weights
  sha256 62b649ec…). The authors' region is `tumorMask > 0` of the label map. The cavity is not part of the BraTS21
  map; whether the released masks' `> 0` region contains the cavity is checked and recorded as a deviation before any
  AUC is computed.
- **Extraction:** the authors' code and settings unchanged, on the same scans as the faithful run. Scans whose
  BraTS21 map is empty or fails extraction are listed before results; the evaluation set must stay identical to the
  faithful run's (asserted), or the difference is recorded as a deviation.
- **Fitting:** the same 5x5 grouped folds, top 256 by their ranking, LightGBM with 400 Optuna trials, Platt, seeds
  and one thread per process as in the faithful run.
- **Comparators:** PRISM's imaging model and clinical-history model, refitted on the same folds; the imaging model on
  the BraTS21 measurement table (E5, `PRISM_MEASUREMENTS`), so both image pipelines see the same masks.

## Outcomes (MU, intended use; all with 95% CIs from one paired patient bootstrap, 2,000 samples, seed 20261115)
1. **Primary.** Published pipeline (BraTS21 masks) − imaging model (BraTS21 masks).
2. Published pipeline (BraTS21 masks) − clinical-history model.
3. Published pipeline, BraTS21 masks − released masks (paired; the released-mask predictions of the faithful run).
4. Also reported: all detection scans; Brier before and after Platt.

## Reading (fixed now)
- **If the CI of outcome 1 lies below zero:** the paper says the imaging model ranked scans better than the published
  pipeline on both mask sets.
- **Otherwise:** the paper limits that claim to the masks released with the cohort, and says the margin did not hold
  on the second mask set. The comparison with the clinical-history model then carries the result alone.
- Outcome 2 is reported as an estimate whatever it shows.

## Reproduction checks before anything is reported
- On the released masks the faithful run's saved predictions give 0.580 in the intended use.
- The imaging model on the BraTS21 table reproduces E5 (0.627), and the clinical-history model 0.822.

## Code
`prism/analyses/christodoulou_faithful.py` with a mask-source option (default unchanged) and separate output paths:
`outputs/features/radiomics_christodoulou_brats21.csv`, `outputs/results/analyses/christodoulou_faithful_brats21/`.
