# Imaging diagnostics: positive controls for masks, measurements and label alignment (2026-10-11)

Code: `prism/analyses/diagnostics_imaging.py` (`python -m prism.analyses.diagnostics_imaging [--workers 24 --n-boot 500]`,
about 1 min). Outputs: `outputs/results/analyses/diagnostics_imaging/`.

**Question.** Imaging-only and clinical-only models reach about 0.60 AUC(120 d). Only timing/phase lifts this to about
0.70. Is something broken in the imaging pipeline, the masks or the label alignment? Positive controls: if the
pipeline is sound, imaging should clearly detect the scan at which progression is documented.

**Short answer.** We found no code bug. The volumes reproduce MU's own table, the label mapping is right, the masks look
right, and the labels are aligned with the scan dates. The positive control still **fails**: imaging volumes separate
the progression scan from other scans with AUC of only 0.62–0.70, not ≥ 0.8. On this data, compartment volumes are a
weak and noisy marker of documented progression, even at the progression scan itself. The forward task is therefore
hard for a data reason, not a code reason.

## 1. Volume cross-check against `MU-Glioma-Post_Segmentation_Volumes.xlsx` — PASS

**How the xlsx was matched.** The xlsx has one sheet per label. For 58 patients the ID carries the timepoint
(`-Post-treatment_N`); for the rest it gives only the patient ID, and some rows are duplicated (two mask versions).
Each of our scan × label pairs was therefore matched to the closest xlsx row of the same patient (and timepoint, when
the ID gives one). This best-match alignment is optimistic.

| compartment | Pearson r | exact voxel match | median rel. diff | scans > 10% (and ≥ 0.1 cc) |
|---|---|---|---|---|
| ET (label 3) | 0.9998 | 98.3% | 0 | 5 |
| SNFH (label 2) | 0.9994 | 99.7% | 0 | 1 |
| RC (label 4) | 0.9993 | 94.1% | 0 | 14 |
| NETC (label 1) | 0.9957 | 83.7% | 0 | 47 |

- **Where the disagreements are.** Almost all are in patients 0051, 0053 and 0205–0209. There the xlsx lists extra
  timepoints or a second mask version, for example NETC voxels where our mask has none
  (`volume_disagreements.csv`).
- **Measurements match the masks.** `measurements.csv` volumes equal the mask voxel counts exactly (max diff 0 cc).
- **Label mapping.** Matching xlsx label *j* against our label *k* (`label_permutation_match.csv`):
  - diagonal: 0.94–0.97
  - off-diagonal: ≤ 0.003
  - the xlsx sheet names agree with config: 1 = NETC, 2 = SNFH, 3 = ET, 4 = RC.
- **Intensities agree with the labels.**
  - ET T1c / normal brain: median 1.45, > 1 in 98% of scans.
  - ET is brighter than NETC on T1c in 99% of scans.
  - SNFH FLAIR / normal brain: median 1.44, > 1 in 100% of scans.

**Side finding: possible duplicate patients.** Three scan pairs from *different* patients have identical masks:

- 0018_T5 / 0032_T5
- 0060_T2 / 0062_T2
- 0113_T1 / 0132_T1

A further 4 pairs are near-identical, including 0006_T5 ≈ 0010_T4, which carry different dates
(`cross_patient_near_duplicates.csv`). These look like duplicated patients and should be reported to the data owners.

## 2. Concurrent detection (positive control) — FAIL

The progression scan is the first MRI with a mask on or after the documented progression date: 120 scans in all
gliomas. 46 of them have no earlier scan.

**(a) Progression scan vs the same patient's previous scan** (`paired_progression_vs_previous.csv`; 74 pairs, all
gliomas):

| feature | larger at progression scan | Wilcoxon p |
|---|---|---|
| ET volume | 49% | 0.54 |
| lesion volume | 65% | 0.033 |
| lesion growth from nadir | 79% (n = 42) | 0.0003 |
| ET growth from nadir | 50% | 0.95 |

Grade 4 gives the same pattern. **ET does not increase at the documented progression scan.**

**(b) Imaging-only classifier** (volumes + delta; 5×5 patient-grouped CV; plain AUC with patient-cluster 95% CI;
`detection_auc.csv`). Pairs are ridge / GBM:

| comparison | all gliomas | grade 4 |
|---|---|---|
| progression scans vs all index scans | 0.62 [0.57, 0.67] / 0.63 | 0.62 / 0.63 |
| progression scans vs verified 120-d negatives (cleanest) | 0.68 [0.62, 0.74] / 0.70 | 0.65 / 0.66 |
| both groups with a prior scan | 0.62 / 0.61 | 0.60 / 0.62 |

The best single features (`single_feature_auc.csv`) are ET / tumour volume at about 0.67. Changes since the last scan
are close to 0.5 (log ET ratio 0.50).

**Why the control fails.**

- **The volume series are very noisy.** Take consecutive scans ≤ 14 days apart (n = 25). Their median change is 3.2×
  in ET (|log ratio| 1.16) and 1.8× in lesion volume, which is larger than over 45–90 day gaps (0.58 / 0.44).
  Across all 389 pairs, the size of the change is unrelated to the gap (Spearman −0.01, p = 0.83;
  `volume_continuity_by_gap.csv`).
- **Some of that noise is real.** Many short-gap pairs straddle a re-resection: the cavity jumps up and ET drops,
  e.g. 0103, 0095.
- **Some is implausible.** In 0013, 0018, 0070 and 0123, ET rises 3–20× within 3–12 days while the cavity shrinks.
  This suggests either segmentation inconsistency or image/date order problems in a subset of patients.

## 3. Label/date alignment — PASS (no misalignment)

Source: `progression_date_vs_mri.csv`, `index_scan_alignment.csv`, `alignment.png`.

- **Progression date vs MRI date.**
  - The date coincides exactly with an MRI for 62% of progressors, within ±7 days for 69% and within 30 days for 73%.
  - 22% of progressors have no MRI on or after the progression date.
- **Positives (label_120 = 1, n = 100).**
  - Median time to progression: 66 days (IQR 44–92).
  - Median interval to the next scan: 63 days.
  - 76% are the last scan before progression.
  - For 58% the next scan is the progression scan.
- **Is label_120 just "the next scan is the progression scan"?** Largely yes. The two agree on 79% of scans
  (κ = 0.53; 12 negatives / 156 also have the progression scan as their next scan).

## 4. Horizon curve — imaging does not gain at short horizons

Ridge, repo folds, IPCW AUC(H) as the mean over repeats (`horizon_curve.csv`, `horizon_curve.png`). Grade 4:

| H (days) | events | imaging | clinical + phase | both |
|---|---|---|---|---|
| 30 | 16 | 0.48 | 0.39 | 0.47 |
| 60 | 36 | 0.63 | 0.55 | 0.65 (Δ +0.10 [0.02, 0.19]) |
| 90 | 62 | 0.62 | 0.63 | 0.68 |
| 120 | 93 | 0.60 | 0.66 | 0.69 |
| 180 | 131 | 0.58 | 0.59 | 0.63 |
| 270 | 157 | 0.59 | 0.55 | 0.63 |

All gliomas follow a similar pattern (imaging 0.51 / 0.67 / 0.67 / 0.64 / 0.62 / 0.66). Imaging stays at about 0.6
at every horizon. The 30-day estimates (16 events) are not interpretable.

## 5. Last scan before progression vs earlier scans (progressors only)

Imaging (volumes + delta), 5×5 grouped CV: ridge 0.61 / GBM 0.67 (all gliomas); 0.61 / 0.66 (grade 4). Single
features reach about 0.63–0.65: lesion growth from nadir 0.65, lesion growth rate 0.63. The scan date alone gives 0.62.
The separation is weak.

## 6. Visual QA (`qa/*.png`, `qa/qa_scans.csv`)

12 random scans (seed 0): 4 progression scans, 4 positive index scans and 4 negative index scans. Each shows the
largest-lesion axial slice of T1c, plus T1c and FLAIR with contours. In all 12, ET lies on the enhancing rim, SNFH
covers the FLAIR hyperintensity and RC covers the cavity. **No obviously wrong masks were seen.**

## Conclusion

- **No pipeline bug found.**
  - Volumes reproduce MU's own table (r ≥ 0.996).
  - Labels are mapped correctly and measurements equal the masks.
  - Labels sit where expected: positives are mostly the scan right before the progression scan.
- **But imaging is a weak marker of documented progression even at the progression scan itself** (AUC 0.62–0.70).
  - ET volume does not rise at the progression scan.
  - Scan-to-scan volume changes are dominated by noise and surgery: within-patient changes are as large over 1–2 weeks
    as over months.
  - Progression in MU is often declared at a scan whose predecessor already looked similar.
- **The forward 120-day task is therefore hard on this data, not broken.** Imaging adds a signal of about 0.6 that
  does not grow at short horizons.
- **Data issues to report:**
  - 3 identical cross-patient masks (possible duplicate patients);
  - a handful of implausible within-days volume jumps;
  - 22% of progressors without an MRI on or after the progression date.

## Addendum: concurrent growth by type of first progression (coordinator check)

MU codes the type of first progression (data dictionary): 1 = imaging criteria, 2 = clinical findings, 3 = both.
Progression scan vs the same patient's previous scan (`scan_table.csv`, pairs with a previous scan):

| Type | Pairs | ET larger at progression scan | Lesion larger | Median ET ratio |
|---|---|---|---|---|
| Imaging | 40 | 50% | 68% | 1.02 |
| Imaging + clinical | 27 | 52% | 63% | 1.05 |
| Clinical only | 7 | 29% | 57% | 0.72 |

Even when progression was called on imaging, segmented ET volume is no larger than at the previous scan in half of
the pairs; whole-lesion volume and growth from the lesion nadir carry the (modest) signal. Clinical-only progression
(19 patients overall) is by construction not detectable from the mask volumes.
