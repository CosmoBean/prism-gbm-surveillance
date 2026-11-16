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
