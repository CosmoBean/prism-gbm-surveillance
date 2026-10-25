# UCSF-ALPTDG image measurements (external test cohort)

Image measurements for all 596 UCSF scans (298 patients x time1/time2), computed with the MU code so that MU-trained
image models can be applied unchanged. Features and agreement checks only: no labels, no clinical data, no models.

## Label mapping

UCSF seg labels follow the same BraTS post-treatment convention as MU, so no remapping is needed:

| UCSF seg | UCSF name | MU label (prism.config) | PRISM compartment |
|---|---|---|---|
| 1 | NCR | 1 = NETC | `netc_cc` |
| 2 | SNFH | 2 = SNFH | `snfh_cc` |
| 3 | ET | 3 = ET | `et_cc` |
| 4 | RC | 4 = RC | `rc_cc` |

No voxel carries any other value. The mapping is confirmed by the exact match to the xlsx volume columns (below).
The xlsx composite headers are misnamed. "WT_Volume_Label1+2+3" is labels 1+2+3+4 (it includes the cavity), and
"TC_Volume_Label_1+2" is labels 1+3 (NCR + ET).

## What was computed and how it matches MU

`prism/features/ucsf_imaging.py` is a thin adapter. It reuses the following MU code as is:
- `measurements.concepts_from_paths`: the MU per-scan function, factored out of `scan_concepts` with no change in
  behaviour. Re-running it on 3 MU scans matches `outputs/features/measurements.csv` to within 2e-16.
- `measurements.add_deltas`.
- `tabular.measurement_groups`: it takes a new optional `meas` table. With it, MU output is identical to the default.
- The `change_nadir` / `_features_one` definitions. `change_features` gives exactly 0 deviation from
  `detection.change_nadir` on all MU detection scans.

| arm | inputs | UCSF |
|---|---|---|
| I_scan | 6 log volumes + 13 morphology / relative-intensity features | **exact** (same code, same label semantics) |
| I_pure | I_scan + `logratio_prev_{et,netc,snfh,rc,tumor,lesion}` + `nadir_all_{et,lesion}` | **approximate** at the history level: time1 has no previous scan (change = 0, nadir = itself); time2 uses time1 as both the previous scan and the whole history |
| LUMIERE image-only (T_img) | `log_et_cc`, `log_necrosis_cavity_cc` (NETC + RC), `log_snfh_cc`, `logratio_prev_{et,necrosis_cavity,snfh}` | same as I_pure: exact per scan, truncated history |
| I (full) / T | also need days since the previous scan, `has_prev` and an RT-anchored nadir window | not computed here (needs clinical days; `has_prev` encodes the dataset design, not care) |

The relative intensities are the MU definition. They are the median of t1ce (or FLAIR) in the compartment divided by
the median over normal-appearing brain. Normal-appearing brain is t1ce > 0 and FLAIR > 0, at more than 10 mm from
lesion or cavity. These ratios do not depend on the global intensity scale. MU (FeTS-preprocessed, float32, values
around 300) and UCSF (float64, values around 2000) both have zero background, a 240x240x155 grid at 1 mm and the same
axis orientation. Their origins differ, which does not affect any feature. Two things are not documented for UCSF and
could shift the intensity ratios: bias-field correction and the skull-stripping method. Scan order uses an ordinal day
(time1 = 0, time2 = 1), so the day-dependent columns (`days_since_prior`, `rate_*`) are omitted.

## Agreement with the xlsx volumes (all 596 scans; xlsx units are mm^3 = voxels)

| xlsx column | labels | filled | Pearson | exact matches | median abs diff | blank -> label empty |
|---|---|---|---|---|---|---|
| NCR | 1 | 198 | 1.000 | 198/198 | 0 | 398/398 |
| SNFH | 2 | 596 | 1.000 | 596/596 | 0 | - |
| ET | 3 | 373 | 1.000 | 373/373 | 0 | 223/223 |
| RC | 4 | 536 | 1.000 | 536/536 | 0 | 60/60 |
| WT | 1+2+3+4 | 596 | 1.000 | 596/596 | 0 | - |
| TC | 1+3 | 373 | 1.000 | 373/373 | 0 | 223/223 |

A blank xlsx cell means 0 voxels. No filled cell is 0, and no filled cell has an empty label.

**Subtraction segs (time2 only, descriptive).** Values are 1 = increase and 2 = decrease. They equal the xlsx Inc /
Dec columns in 298/298 pairs, for both ET and SNFH. Four t1ce maps also contain 1-2 voxels of value 3. Against our
time2 − time1 change:

| | non-empty maps | Spearman (net vs ours) | sign agreement (non-empty) | median abs change, ours, where the map is empty |
|---|---|---|---|---|
| ET (t1ce) | 131/298 | 0.83 | 0.93 | 0 mm^3 (Q3 102) |
| SNFH (FLAIR) | 149/298 | 0.76 | 0.87 | 1276 mm^3 (Q3 2670) |

The subtraction maps count only changes that pass a threshold. An empty SNFH map often goes with a real difference of
1-3 cc between the two segmentations.

## Distribution shift, MU vs UCSF (no labels)

MU covers all 591 MU timepoints in the measurement table. UCSF covers all 596 scans. Change features use scans that
have a previous scan (MU 389, UCSF 298). The shift is the difference in medians in units of the MU IQR. Full table:
`outputs/data/ucsf/imaging_shift_mu_vs_ucsf.csv`.

| feature | MU median (IQR) | UCSF median (IQR) | shift / MU IQR |
|---|---|---|---|
| log_et_cc | 1.94 (0.79–2.70) | 0.48 (0.00–2.17) | −0.77 |
| log_et_max_axial | 5.83 (4.82–6.45) | 4.34 (0.00–5.98) | −0.91 |
| log_tumor_cc | 1.98 (0.79–2.84) | 0.48 (0.00–2.22) | −0.73 |
| et_n_components | 2 (1–3) | 1 (0–2) | −0.50 |
| log_lesion_cc | 3.98 (3.22–4.63) | 3.50 (2.82–4.22) | −0.34 |
| log_snfh_cc | 3.81 (3.04–4.43) | 3.38 (2.77–4.02) | −0.30 |
| log_rc_cc | 1.50 (0.34–2.56) | 2.14 (0.97–3.08) | +0.29 |
| flair_netc_rel | 1.48 (1.30–1.65) | 1.36 (1.19–1.52) | −0.31 |
| t1c_netc_rel | 0.88 (0.74–1.00) | 0.93 (0.84–1.03) | +0.22 |
| t1c_et_rel | 1.45 (1.29–1.64) | 1.43 (1.30–1.60) | −0.06 |
| flair_snfh_rel | 1.44 (1.37–1.53) | 1.46 (1.38–1.56) | +0.13 |
| logratio_prev_et | 0.12 (−0.53–1.01) | 0.00 (−0.01–0.27) | −0.08 (IQR 6x narrower) |
| logratio_prev_snfh | 0.11 (−0.35–0.51) | 0.04 (−0.06–0.19) | −0.08 (IQR 3.5x narrower) |
| nadir_all_et | 0.57 (0.00–1.78) | 0.00 (0.00–0.27) | −0.32 |

- **Burden.** UCSF has much less enhancement. ET is 0 in 37% of UCSF scans and 8% of MU scans, and NETC is 0 in 67%
  vs 47%. UCSF cavities are larger. The cohort includes all grades, and the pairs are mostly late surveillance, which
  probably explains this. Case mix was not examined here.
- **Intensity ratios.** The ET and SNFH ratios transfer well (shift of 0.13 MU IQR or less). The NETC ratios shift more
  (0.2–0.3 MU IQR) and are defined in only 33% of UCSF scans.
- **Change features.** UCSF change is much narrower than MU change: the scan interval is a median of 65 d in UCSF vs
  77 d in MU, and the UCSF segs may have been produced as a pair. `nadir_all_*` is truncated by design, because the
  UCSF history is only time1.

## Caveats

- **No earlier history.** UCSF has no scans before time1, unlike MU (median 3 scans per patient). At time1,
  `has_prev` = 0, all `logratio_prev_*` = 0 and `nadir_all_*` = 0. At time2, the "whole-history nadir" is the
  smaller of time1 and time2.
- **Segmentation source.** The provenance of the UCSF segmentations is not documented in the shipped files. MU
  segmentations were automated (FeTS) and then refined by neuroradiologists. The two segmentation styles may differ
  systematically, for example in how NCR is delineated.
- **Preprocessing.** Bias correction and skull-stripping for UCSF are undocumented. Only ratio features are used, so
  the global intensity scale does not matter.

## Reproduce

```
PRISM_WORKERS=24 PYTHONPATH=. srun --jobid=<alloc> --overlap -N1 -n1 --cpus-per-task=24 \
    .venv/bin/python -m prism.features.ucsf_imaging      # about 2 min on 24 CPUs
```

The command writes these files to `outputs/data/ucsf/` (git-ignored): `imaging_features.csv` (596 x 81),
`imaging_features_dictionary.csv`, `imaging_volume_agreement.csv`, `imaging_subtraction_check.csv` and
`imaging_shift_mu_vs_ucsf.csv`. The input path can be overridden with `PRISM_UCSF_ROOT`.
