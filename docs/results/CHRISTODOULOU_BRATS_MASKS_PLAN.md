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

## Deviations recorded before results (2026-11-16)

Written after the mask check, the extraction and a one-fold smoke test (10 trials, no held-out prediction scored),
before any AUC was computed. Code: f857e7a (`christodoulou_faithful.py --masks brats21`; default unchanged).

- **Cavity (checked, as the plan requires).** The released masks' `> 0` region contains the resection cavity
  (label 4) in 520 of 594 scans; where present it is a median 10% (IQR 2-25%) of that region. The BraTS21 map has
  no cavity label (label 4 occurs in no map). It does not leave the cavity out, though: a median 81% of the released
  cavity voxels lie inside the BraTS21 `> 0` region, labelled as tumour or oedema. The two `> 0` regions agree with
  median Dice 0.90 (IQR 0.78-0.95; 0.85 against the released region without the cavity); median volume ratio
  BraTS21 / released 0.98. All 594 maps are on the released masks' grid. The authors' region (`> 0` of the map) is
  kept unchanged; the region therefore differs from the released one by the segmenter, not by a rule about the
  cavity.
- **Failed extractions: 14, all empty BraTS21 maps.** 14 of 594 BraTS21 maps contain no voxel (in one of them the
  released mask is cavity only). Their code stops on these ("No labels found in this mask"); the other 580 extracted
  without a warning or error (4,892 features, no missing or infinite value, no constant column). The 14 failures are
  exactly the 14 empty maps (scan ids in the git-ignored `extraction_info.json`).
- **Evaluation set kept identical; 5 of its scans have no features.** Of the 14, six are grade-4 detection-frame
  scans, five are training rows and five are in both evaluation sets (intended use and all scans; one progression).
  They are not dropped: the evaluation set is the faithful run's (asserted). Their features are missing, and the
  median imputation that opens both the authors' ranking and LightGBM pipelines fills them, so in each fold they
  receive the prediction of a median-feature scan. This is the authors' pipeline's own handling of missing values;
  no other choice keeps the set identical. The imaging model (BraTS21 table, E5) scores these scans from their
  measured zero volumes.
- **Ranking, as in the faithful run.** Permutation importance again never runs (0 of 10 inner folds reach 30 rows);
  in the smoke-test fold 474 features were ranked, 131 with a non-zero median coefficient; 256 kept; all 256 pass the
  tuned correlation filter in that fold.
- **Bootstrap.** As the plan states: one 2,000-sample patient bootstrap, seed 20261115, per evaluation set, shared by
  all arms (the faithful run used 1,000 draws, seed 20261021). The released-mask predictions and comparators are
  re-scored under this bootstrap, so their point estimates are the faithful run's and their CIs may differ in the
  third decimal.
- **Comparators.** B1 is mask-free and is taken once (asserted identical under both tables and equal to the detection
  run). I_pure and I_scan on the BraTS21 masks are refitted in a separate process with `PRISM_MEASUREMENTS` set to the
  E5 table (whose cavity column, as in E5, comes from the released masks); the frame, labels, intended-use flags and
  folds are asserted identical. The E5 reference (0.627) is checked against this I_pure, not E5's own process.
  Reported in addition to the plan's three outcomes: CHF (BraTS21) − I_scan (BraTS21), CHF (released) − I_pure
  (released), and I_pure BraTS21 − released.
- **Compute.** Extraction ran in two parts (the first `srun` step was stopped by a 2 h client time limit after 472
  scans; the cached per-scan results were kept and the remaining 122 run in a second step): about 2 h 26 min wall on
  20 CPUs, median 214 s per scan. Fits as in the faithful run (25 folds in 20 processes, one thread each).
