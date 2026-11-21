# Plan: do the headline MU results depend on the released masks? (2026-11-16)

Written before the run. It is committed before it. Results go to METHODS_RESULTS.md section E5.

## Why
The released MU masks are noisy. The median enhancing volume changes by a factor of 2.6 between consecutive scans
less than 30 days apart. A consistent segmenter (SwinUNETR BraTS21, RESEGMENTATION.md) reduced this only to 2.2,
and it did not improve imaging detection by the planned rule. This analysis asks whether PRISM's headline MU results
change when every mask comes from that one segmenter.

## Masks
- Regenerate the BraTS21 SwinUNETR label maps with `prism.features.reseg --model brats21`, unchanged code, on the GPU
  of the interactive allocation.
- Recompute PRISM's 27 measurements from those maps with the code that produced `outputs/features/measurements.csv`.
  Only the mask source changes.
- The resection cavity is not segmented by BraTS21, so the cavity measurements keep the released mask. This is
  recorded as a deviation.

## Outcomes (MU, intended use, the same 5x5 folds and 2,000 bootstrap samples as E4)
- **AUCs with the new masks:** the imaging model, the combined model and the reader baseline. Each is reported with
  its paired difference from the same model on the released masks.
- **E4 gains:** the combined model minus the reader baseline, and the imaging model minus the reader baseline (AUC
  and A_W).
- **Mask noise:** the median fold change of the enhancing volume between consecutive scans within 30 days, for both
  mask sets (from RESEGMENTATION.md).

## Reading (fixed now)
- **Headline results are robust** if every paired difference has a CI that includes zero and the E4 reading (no
  clear gain) is unchanged.
- **Otherwise** the paper states which results depend on the masks.

## Code
`prism/analyses/mask_sensitivity.py`, reusing `prism/analyses/clinician_baseline.py`. Output goes to
`outputs/results/analyses/mask_sensitivity/`.

## Deviations recorded before results
Written 2026-11-16, after the plan and before any AUC with the new masks was computed or seen.
- **1 GPU instead of 2.** The allocation now gives one GPU, so `prism.features.reseg --model brats21 --gpus 1`. The
  code is unchanged; only the sharding differs (runtime, not output).
- **Weights re-downloaded.** The storage reset removed `data/weights/`. The BraTS21 SwinUNETR fold 1 checkpoint was
  downloaded again from the public `Project-MONAI/MONAI-extra-test-data` 0.8.1 release to
  `data/weights/brats21_swinunetr_fold1_f48/model.pt`, sha256
  `62b649ecf98b05c73d7a36a7e290e85ad90a9b5d0dab442f296342406feb57ba`.
- **Measurement file.** The new table is written by `prism.analyses.reseg_eval.build_table("brats21")` (the
  `measurements.py` logic on the new label maps, cavity from the released mask where the new map is background) to
  `outputs/results/analyses/reseg/measurements_brats21.csv`. `outputs/features/measurements.csv` is not touched.
  The models read it through a new `PRISM_MEASUREMENTS` override in `prism/config.py` (default unchanged), in a
  separate process. The scans and patients evaluated must be identical under both mask sets (checked in code).
