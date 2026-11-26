# S1. A segmentation stage: PRISM from the images (plan, fixed before any result)

Author's direction (2026-11-19). Make the BraTS network a stage of PRISM. PRISM then takes the four MRI sequences of
a scan, segments them with one fixed public network, and measures, scores and reports from that segmentation. The
masks released with each cohort become a comparison rather than an input. This plan is committed before any
segmenter-derived number is linked to a label at LUMIERE or UCSF. At MU the segmenter's label maps exist (E5, commit
c235649), and E5 compared the MU AUCs with the cavity taken from the released mask. No cavity-free model has been
fitted.

## Segmenter (fixed, not tuned on any cohort)

- **Model:** the MONAI BraTS 2021 Swin UNETR, fold 1, feature size 48 (`data/weights/brats21_swinunetr_fold1_f48`),
  as in `prism/features/reseg.py`.
- **Input channels:** FLAIR, T1c, T1, T2.
- **Inference:** `NormalizeIntensity(nonzero, channel-wise)`; sliding window 128³ with overlap 0.5; sigmoid > 0.5
  on (TC, WT, ET).
- **Output labels:** ET; NETC = TC − ET; SNFH = WT − TC.
- **No resection cavity:** the network has no cavity class.
- **Inputs by cohort:**

| Cohort | Images | Note |
|---|---|---|
| MU | as stored (FeTS-preprocessed, 1 mm BraTS space) | existing maps reused |
| LUMIERE | DeepBraTumIA `atlas/skull_strip/{flair,ct1,t1,t2}_skull_strip.nii.gz`, from the released zip | — |
| UCSF-ALPTDG | `<id>_time{1,2}_{flair,t1ce,t1,t2}.nii.gz` (240×240×155, 1 mm, LPS) | — |

- **Orientation check:** inference on 3 scans per cohort is checked against the released masks before the full
  run. If the median WT Dice is below 0.70, the orientation and channel order are investigated before going on. No
  label is read.

## Measurements

- **Code:** the same measurement code as the released masks, run on the segmenter maps.
- **One input set for every cohort ("segmenter inputs"):**
  - the 27 measurements, minus every input that needs the resection cavity (the cavity volume and its change);
  - the dropped inputs are listed in the results file before fitting.
- **LUMIERE then gets the same set as MU:** volumes, shape and intensity, and change since the previous scan and
  since the smallest volume. The three-volume model is no longer needed there.
- **Patient history:** at each scan it uses only earlier scans, as now.

## Models

- **What is refitted:** on MU segmenter inputs, in the same 5×5 patient-grouped folds and the same intended-use
  population:
  - the imaging model;
  - the combined model in its reduced form;
  - the timing-and-enhancement baseline (enhancing volume and its change from the segmenter).
- **Everything else as now:** the clinical-history models, penalty grid, imputation and conformal settings do not
  change.
- **Locking:** after fitting on all MU rows, each model is locked. It is then applied unchanged at LUMIERE and UCSF
  on the segmenter inputs, in the same evaluation sets as the paper:
  - LUMIERE: all 178 labelled scans;
  - UCSF: grade 4 scan 2.

## Questions and rules

### P1 (planned, primary): does PRISM from the images reproduce PRISM from the released masks?

- **Scores compared, per cohort:** the imaging, reduced combined and timing-and-enhancement baseline AUCs,
  segmenter inputs against released inputs.
- **Statistics:** paired differences, with a 2,000-sample patient bootstrap (seed 20261119).
- **The stage reproduces the released-mask results if:**
  - every paired difference has a CI that includes 0 or lies above 0; and
  - at MU and LUMIERE, the gain of the combined model over the baseline is read the same way: its CI includes 0
    with both mask sets, or excludes 0 with both.
- **Otherwise:** the result is reported as it is, with the scores and cohorts where the stage differs.

### P2 (planned, secondary): agreement with the released masks

- **What is reported:** median ET and WT Dice per cohort against the released masks.
  - LUMIERE has three labels, so it is compared on WT and on the enhancing label.
  - UCSF uses its own label convention, which is mapped before the comparison.
- **No pass rule:** this is descriptive.

### P3 (planned, secondary): repeatability

- **Statistic:** the median fold change of the enhancing volume between consecutive scans at most 30 days apart,
  segmenter against released masks, at MU and LUMIERE (wherever such pairs exist).
- **Expected (stated before the run):** the fixed segmenter is at least as repeatable as the released masks.
- **Reading:** reported as a point estimate with its bootstrap CI.

### Exploratory

- Calibration of the locked segmenter-input models.
- The same comparison with BrainSegFounder.

## What does not change

- **The paper's primary numbers stay on the released masks.** That includes the locked abstract, unless the author
  decides otherwise after seeing P1.
- **Reports:** regenerating them on segmenter-derived records is a separate step. It is planned only after P1, with
  the same model, prompt and checker.

## Outputs

- **Segmenter label maps:** `outputs/features/seg_swin/{mu,lumiere,ucsf}/…`.
- **Measurements:** `outputs/features/seg_swin/measurements_{cohort}.csv`.
- **Results:** `docs/results/SEGMENTER_STAGE.md`, with every deviation from this plan marked and dated.
