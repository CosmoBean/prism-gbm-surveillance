# S1. A segmentation stage: PRISM from the images (results)

Plan: `docs/results/SEGMENTER_STAGE_PLAN.md` (commit b5225c7, written before any segmenter-derived number was
linked to a label at LUMIERE or UCSF). Sections 1-3 were written on 2026-11-19 before the label-linked results were
computed; section 4 holds the results.

## 1. How to run

```
# segmenter label maps (MU maps of E5 reused; 1 GPU of job 172445)
mkdir -p outputs/features/seg_swin/lumiere_input
unzip -q -n /project/community/sbandred/lumiere/Imaging-v202211.zip \
  $(unzip -l .../Imaging-v202211.zip | awk '{print $4}' | \
    grep -E "DeepBraTumIA-segmentation/atlas/(skull_strip/(flair|ct1|t1|t2)_skull_strip|segmentation/seg_mask)\.nii\.gz$") \
  -d outputs/features/seg_swin/lumiere_input
export PYTHONPATH=. PRISM_RESEG_ORIENT=lps
srun --jobid=172445 --overlap -N1 -n1 --cpus-per-task=24 --export=ALL .venv/bin/python -m prism.features.reseg --cohort ucsf
srun --jobid=172445 --overlap -N1 -n1 --cpus-per-task=24 --export=ALL .venv/bin/python -m prism.features.reseg --cohort lumiere
# measurement tables from the maps (no cavity)
srun ... .venv/bin/python -m prism.features.seg_measurements --cohort mu lumiere ucsf --workers 12
# P1-P3 and calibration (two model-fitting subprocesses, one per mask set, then one bootstrap per cohort)
srun ... .venv/bin/python -m prism.analyses.segmenter_stage --workers 20 --n-boot 2000
```

Code: `prism/features/reseg.py` (cohort support added; the MU path is unchanged), `prism/features/seg_measurements.py`,
`prism/analyses/segmenter_stage.py`. Outputs: label maps `outputs/features/seg_swin/{mu,lumiere,ucsf}/`, volumes and
Dice `outputs/features/seg_swin/volumes_brats21_{lumiere,ucsf}.csv` (MU: `volumes_brats21.csv`, E5), measurement
tables `outputs/features/seg_swin/measurements_{mu,lumiere,ucsf}.csv`, results
`outputs/results/analyses/segmenter_stage/`.

## 2. Implementation choices (fixed before any label-linked result)

**Segmenter.** As in the plan and E5: Swin UNETR BraTS21 fold 1, channels FLAIR, T1c, T1, T2, non-zero channel-wise
normalisation, sliding window 128³ with overlap 0.5, bf16, sigmoid > 0.5 on (TC, WT, ET); ET = ET, NETC = TC − ET,
SNFH = WT − TC. The MU maps of E5 are reused unchanged.

**Released-mask label conventions** (for P2 and the orientation check).
- LUMIERE `atlas/segmentation/seg_mask.nii.gz` uses the DeepBraTumIA numbering **1 enhancing, 2 necrotic +
  non-enhancing (cavity included), 3 oedema**. This was checked against each study's
  `measured_volumes_in_mm3.json` on seven studies (exact voxel-count match). It is mapped to the MU numbering
  (3 ET, 1 NETC, 2 SNFH) before comparison, so WT = all three labels and ET = label 1.
- UCSF `<id>_time{t}_seg.nii.gz` uses the MU / BraTS post-treatment numbering (`prism.features.ucsf_imaging`): 1 NETC,
  2 SNFH, 3 ET, 4 resection cavity. WT = 1 | 2 | 3. The cavity (4) lies outside WT, as at MU.

**Orientation check** (3 scans per cohort, Dice against the released masks, no label read).
- UCSF images are 240×240×155, 1 mm, LPS, the same grid and axis order as MU. They were run as stored. Smoke scans
  100001_time1, 100002_time2 and 100003_time2 gave WT Dice 0.76, 0.93 and 0.81 (median 0.81). The released masks
  contain little or no enhancement in these three scans (0, 847 and 6,422 voxels), and the segmenter found none.
  Four further scans with larger released enhancing volumes were run to check the enhancing output (no label
  read). ET Dice was 0.93, 0.80, 0.96 and 0.82, and WT Dice 0.94, 0.94, 0.91 and 0.65.
- The LUMIERE atlas images are 182×218×182, 1 mm, LAS (MNI grid), whereas the BraTS training data and MU are LPS.
  Smoke scans Patient-002 week-021, Patient-006 week-000 and Patient-002 week-037 were run both as stored and
  reoriented to LPS. As stored, WT Dice was 0.34, 0.96 and 0.76 (median 0.76). Reoriented, it was 0.35, 0.96 and
  0.78 (median 0.78). ET Dice was 0.95 in both runs for the two scans with enhancement. Both pass the plan's 0.70
  threshold. **Choice:** the four LUMIERE images are reoriented to LPS for inference (the axis order of the
  network's training data), and the label map is mapped back to the stored grid (`PRISM_RESEG_ORIENT=lps`). This is
  a fixed preprocessing step, applied identically to every LUMIERE study.

**Measurements.** `measurements.concepts_from_paths` and `add_deltas` run unchanged on the segmenter maps. The maps
have no cavity label, and nothing is taken from the released masks. The MU table has the same 591 scans, mri_day and
columns as `outputs/features/measurements.csv`. Its ET, NETC and SNFH volumes equal the E5 table exactly; the E5
table's cavity is absent. LUMIERE takes every study with a segmenter map, with mri_day = week × 7. UCSF takes all 596
scans with an ordinal day (time1 0, time2 1), as `ucsf_imaging` does, so the day-dependent columns are dropped.
Because the cavity is unknown, the normal-brain intensity reference excludes only the 10 mm around the segmented
lesion. That follows from the measurement code, not from a new rule.

**Cavity-dependent inputs dropped (5 of the 27).** `log_rc_cc` (cavity volume), `has_cavity`,
`et_near_cavity_fraction`, `et_cavity_distance` (log median distance of ET to the cavity) and `logratio_prev_rc`
(cavity change since the previous scan). The remaining **22 segmenter inputs** are:
- volumes: log ET, NETC, SNFH, TC, WT;
- shape and intensity: ET fraction of TC, log SNFH/TC, ET component count, largest-component fraction, log maximum
  axial ET area, T1c ET median and p90, T1c NETC, FLAIR SNFH and FLAIR NETC relative to normal brain;
- change: log ratio to the previous scan of ET, NETC, SNFH, TC and WT, and of ET and WT to the smallest volume
  in the history.

They are built in every cohort with `ucsf_imaging.model_inputs`, the builder asserted to reproduce the MU designs
(`ucsf_external.checks_mu`).

**Models** (all `c3.BASE_PRE` + verified ridge, as now).

| score | released inputs (the paper) | segmenter inputs |
|---|---|---|
| imaging | MU, UCSF: A-Ipure (27). LUMIERE: three volumes and their change (T_img), and the three-volume model for scans without a previous scan (the paper's 0.65) | the 22 segmenter inputs, every cohort |
| reduced combined | T: reduced clinical history (6) + three volumes (necrosis + cavity as one), their change, has_prev, log days from the previous scan | reduced clinical history (6) + has_prev + log days from the previous scan + the 22 segmenter inputs |
| timing-and-enhancement baseline | MU (CV): phase dummies + log ET + its log ratio to the previous scan (E4). Locked: early-post-RT flag + log ET + log ratio + has_prev (E4 LUMIERE design) | same columns, ET from the segmenter |

- The reduced combined model keeps its form: the reduced clinical-history inputs, the previous-scan indicator and
  interval, and the image inputs. The image block is the segmenter input set, because the plan fixes one input set
  for every cohort.
- At MU the full combined model (B1 + imaging), the paper's MU combined score, is also refitted. It is reported as
  exploratory and is not part of the P1 rule.
- **Folds and locking.** MU: 5×5 patient-grouped folds of the paper, intended use (146 scans), with AUCs averaged
  over the five repeats. Locked: one fit on all MU training rows (`system._fit`), applied unchanged to LUMIERE
  (178 scans) and UCSF (grade 4 scan 2, 69 scans).
- **Baseline at UCSF.** The baseline was not run at UCSF in the paper. Here the locked baseline is applied with
  UCSF's approximated radiotherapy flag (`rt_phase`), under both mask sets.
- **LUMIERE history** (segmenter): the most recent strictly earlier rated study that is not "Pre-Op" and has a
  segmenter map. This is the released pool rule (`lumiere_detection`), with the segmenter map in place of the
  DeepBraTumIA volumes. The smallest-volume reference uses the same pool, up to and including the scan.
- **Reproduction of the released numbers.** Asserted to within 0.001 before any comparison: MU imaging 0.709, reduced
  combined 0.804, baseline 0.797, full combined 0.821; LUMIERE imaging 0.654, reduced combined 0.773, baseline 0.734;
  UCSF imaging 0.726, reduced combined 0.856.

**Statistics.**
- **Bootstrap.** One set of 2,000 patient bootstrap samples per cohort (seed 20261119) covers both mask sets, so
  the differences are paired. The bootstrap resamples held-out predictions without refitting.
- **P1 rule** (as planned). Every paired segmenter − released AUC difference (3 scores × 3 cohorts) has a CI that
  includes 0 or lies above 0. At MU and LUMIERE, the reduced combined − baseline gain has a CI that includes 0 under
  both mask sets, or excludes 0 under both.
- **P2.** Median ET and WT Dice over every scan with a defined Dice (a scan where both masks are empty for a
  compartment has none). MU uses all 594 scans of E5.
- **P3.** Consecutive scans ≤ 30 days apart; median fold change of ET = exp(median |log((v + 0.1)/(v0 + 0.1))|).
  - MU: all consecutive pairs of the 591-scan table (as E5).
  - LUMIERE: consecutive rated non-"Pre-Op" studies with both a released volume and a segmenter map. Days are
    week × 7, so ≤ 30 days means ≤ 4 weeks.
  - CIs come from a patient-cluster bootstrap (2,000 samples, seed 20261119).
- **Calibration** (exploratory). Slope, O/E and intercept of each score under both mask sets (MU: mean over
  repeats). Point estimates only.

## 3. Deviations from the plan

- **2026-11-19, GPU.** The brief assumed 4 GPUs. Job 172445 holds one (`gres/gpu=1`), so inference ran on one H100.
  The plan itself is unaffected.
- **2026-11-19, LUMIERE orientation.** Reorienting the LUMIERE images to LPS for inference (section 2) is a
  preprocessing step that the plan does not name. It was chosen on Dice in three scans, before any label was read.

- **2026-11-19, LUMIERE scans without images** (noted after the design build, before the P1 table was read).
  Seven of the 178 LUMIERE evaluation scans have no images in the archive, and so no segmenter map:
  Patient-009 week-026, Patient-033 week-011, Patient-074 week-011, Patient-082 week-042 and Patient-089
  weeks 013, 026 and 039. They also have no released volume (15 such scans under the released masks). Their image
  inputs are missing and are median-imputed by the locked pipeline, as the released arm already does. All 178
  scans stay in the evaluation set.

## 4. Results (run 2026-11-19)

**Run.**
- **Inference** on one H100: UCSF 596 scans in about 14 min, LUMIERE 599 studies in about 11 min.
- **Measurement tables:** about 2 min per cohort.
- **Analysis:** 37 s, with 2,000 bootstrap samples per cohort.
- **Reproduction check:** every released-mask number in section 2 reproduced to within 0.001 (asserted;
  `s1_reference_check.csv`).

**Populations.**
- MU: 146 scans, 62 progressions, 80 patients.
- LUMIERE: 178 scans, 73 progressions, 79 patients. 165 scans have a previous segmented scan.
- UCSF: 69 scans, 29 progressions, 69 patients.

### P1. Does PRISM from the images reproduce PRISM from the released masks?

AUC (95% CI) under each mask set and the paired difference, segmenter − released (`s1_p1.csv`):

| cohort | score | released | segmenter | paired difference |
|---|---|---|---|---|
| MU | imaging | 0.71 (0.63–0.78) | 0.63 (0.56–0.71) | **−0.08 (−0.15 to −0.01)** |
| MU | reduced combined | 0.80 (0.73–0.88) | 0.81 (0.74–0.87) | +0.00 (−0.04 to +0.05) |
| MU | timing-and-enhancement baseline | 0.80 (0.71–0.88) | 0.78 (0.68–0.87) | −0.02 (−0.06 to +0.01) |
| LUMIERE | imaging | 0.65 (0.57–0.74) | 0.66 (0.57–0.73) | +0.00 (−0.09 to +0.09) |
| LUMIERE | reduced combined | 0.77 (0.68–0.86) | 0.75 (0.67–0.83) | −0.02 (−0.09 to +0.04) |
| LUMIERE | timing-and-enhancement baseline | 0.73 (0.65–0.81) | 0.78 (0.69–0.85) | +0.04 (+0.02 to +0.08) |
| UCSF | imaging | 0.73 (0.60–0.84) | 0.82 (0.71–0.91) | +0.09 (−0.01 to +0.20) |
| UCSF | reduced combined | 0.86 (0.76–0.94) | 0.82 (0.72–0.91) | −0.04 (−0.12 to +0.04) |
| UCSF | timing-and-enhancement baseline | 0.87 (0.77–0.94) | 0.88 (0.79–0.95) | +0.01 (−0.02 to +0.05) |
| MU (exploratory) | full combined | 0.82 (0.74–0.89) | 0.81 (0.73–0.88) | −0.01 (−0.05 to +0.02) |

The released-mask baseline at UCSF (0.87) was not in the paper. It is computed here as section 2 states.

Gain of the reduced combined model over the baseline:

| cohort | released masks | segmenter | change (segmenter − released) |
|---|---|---|---|
| MU | +0.01 (−0.05 to +0.07) | +0.03 (−0.03 to +0.09) | +0.02 (−0.02 to +0.06) |
| LUMIERE | +0.04 (−0.02 to +0.10) | −0.03 (−0.10 to +0.04) | −0.07 (−0.14 to −0.01) |
| UCSF (descriptive) | −0.01 (−0.07 to +0.05) | −0.06 (−0.14 to +0.02) | −0.05 (−0.12 to +0.02) |
| MU, full combined (exploratory) | +0.02 (−0.04 to +0.08) | +0.03 (−0.04 to +0.10) | +0.01 (−0.04 to +0.06) |

**Verdict, by the plan's rule: the stage does not reproduce the released-mask results in full.**
- **Where it differs.** One of the nine paired differences has a CI below zero: the MU imaging model, −0.08
  (−0.15 to −0.01), 0.71 → 0.63. This matches E5 (−0.08 with the cavity borrowed from the released masks), so
  removing the cavity inputs did not change the MU imaging result.
- **The other eight paired CIs include zero or lie above it.**
  - The reduced combined model is within 0.04 of its released value at every centre.
  - The LUMIERE baseline is higher with the segmenter, +0.04 (+0.02 to +0.08).
  - The UCSF imaging model is +0.09 (−0.01 to +0.20).
- **The gain reading is the same under both mask sets at MU and at LUMIERE.** The combined model shows no clear
  gain over the baseline (every CI includes 0).
- **The size of the LUMIERE gain is not the same.** It moves from +0.04 to −0.03, a change whose CI excludes zero
  (−0.07, −0.14 to −0.01). The change comes mainly from the higher segmenter baseline.

### P2. Agreement with the released masks (descriptive)

Median Dice [IQR] over the scans with a defined Dice (`s1_p2_dice.csv`):

| cohort | scans | ET Dice | WT Dice | released ET empty | share ET Dice < 0.5 |
|---|---|---|---|---|---|
| MU (E5 maps) | 594 | 0.80 [0.49, 0.91] (n 550) | 0.85 [0.74, 0.93] | 48 | 0.26 |
| LUMIERE | 599 | 0.74 [0.28, 0.92] (n 540) | 0.90 [0.79, 0.95] | 64 | 0.34 |
| UCSF | 596 | 0.73 [0.00, 0.88] (n 397) | 0.78 [0.59, 0.86] | 223 | 0.37 |

- **LUMIERE** compares the segmenter's ET with DeepBraTumIA's enhancing label, and its WT with all three
  DeepBraTumIA labels.
- **UCSF.** WT excludes the released cavity label. Many UCSF scans have little or no released enhancement (223 of
  596 have none), so the ET Dice has a long lower tail.

### P3. Repeatability (consecutive scans ≤ 30 days apart)

Median fold change of the enhancing volume (95% CI) and the difference in median |log ratio|, segmenter −
released (`s1_p3_repeatability.csv`):

| cohort | pairs (patients) | released | segmenter | difference |
|---|---|---|---|---|
| MU | 54 (46) | 2.57 (2.21–3.20) | 2.17 (1.63–2.45) | −0.17 (−0.46 to −0.02) |
| LUMIERE | 52 (30) | 2.31 (1.85–4.70) | 3.10 (2.09–8.34) | +0.30 (−0.13 to +0.82) |

- **MU.** The expectation stated in the plan holds: the segmenter is more repeatable than the released masks. This
  reproduces E5.
- **LUMIERE.** The expectation is not confirmed. The point estimate favours DeepBraTumIA, and the CI includes zero.
  LUMIERE has few short-gap pairs (52 pairs from 30 patients), so the intervals are wide.

### Exploratory: calibration of the models (point estimates, `s1_calibration.csv`)

| cohort | score | slope, released | slope, segmenter | O/E, released | O/E, segmenter |
|---|---|---|---|---|---|
| MU | imaging | 0.75 | 0.42 | 1.13 | 1.11 |
| MU | reduced combined | 0.95 | 0.85 | 1.08 | 1.06 |
| MU | baseline | 0.94 | 0.95 | 1.00 | 1.01 |
| LUMIERE | imaging | 1.91 | 1.03 | 1.29 | 1.09 |
| LUMIERE | reduced combined | 1.45 | 1.02 | 0.97 | 1.00 |
| LUMIERE | baseline | 0.74 | 1.00 | 1.04 | 1.00 |
| UCSF | imaging | 0.85 | 2.59 | 1.24 | 1.12 |
| UCSF | reduced combined | 3.29 | 1.53 | 0.72 | 0.73 |
| UCSF | baseline | 2.00 | 2.24 | 0.75 | 0.74 |

These are descriptive and come without intervals.
- **LUMIERE.** On the segmenter inputs, the locked LUMIERE models have slopes near 1 and O/E near 1.
- **UCSF.** The models remain miscalibrated there: the combined slope is 1.53, and O/E is about 0.73 for every score
  under both mask sets.
- **MU imaging.** The cross-validated imaging score on the segmenter inputs is too spread out (slope 0.42).
