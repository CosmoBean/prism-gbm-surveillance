# C3 — Can radiomics improve on a clinical + timing + treatment baseline? (2026-10-06; numbers updated after the clipping fix, 2026-10-11)

**Final numbers** from the re-run after the radiomics outlier-clipping fix: `outputs/results/c3/{grade4,all_glioma}/{results,nested_choices}.csv`
(2026-10-11 18:21–18:23, label-fixed cohort, as-of-scan treatment features, in-fold 1%/99% `QuantileClip` first in
`selector()`, see [FIX_RADIOMICS_CLIP.md](FIX_RADIOMICS_CLIP.md); headline = mean over 5 repeats of the per-repeat
pooled-OOF IPCW AUC, paired patient-cluster bootstrap ΔAUC, 1000 resamples). The head-to-head section is from
`outputs/results/c3/prism_report_split/head_to_head.csv` (06:44), which was **not** re-run after the clipping fix, so
its radiomics rows predate it. The 2026-10-06 numbers are superseded. The legacy ablation table was not re-run and is
kept only for the record.

Code: `prism/features/radiomics.py` (corrected extraction), `prism/features/tabular.py:treatment`, `prism/experiments/c3_radiomics.py`.
Setup: verified 120-d labels, 5×5 repeated patient-grouped CV, all steps in-fold; IPCW AUC(120 d); paired ΔAUC vs the ridge baseline with a patient-cluster bootstrap (1000).

**Baseline** = clinical (age, sex, IDH/MGMT incl. unknown) + timing (days since diagnosis / RT end, early post-RT, visit) + treatment (RT given, dose, fractions, hypofractionation, RT start/duration, chemo, surgery day, biopsy-first, prior tumour).
**Radiomics configurations (70):** variants legacy / corrected whole lesion / corrected per compartment (ET, NETC, SNFH, core, lesion, 5 mm cavity rim + shape) / corrected all 4 sequences × stability filter (ICC ≥ 0.75 vs 1-voxel erosion, in-fold) × selection (top-10, top-30, L1, PCA-10, decorrelate + top-20) × integration (concatenate, stacked radiomics score).
Corrected extraction: whole-brain z-score, fixed 32 bins (GLCM joint entropy 4.7–6.3 bits vs ≤ 2 legacy), no second N4.

## grade4 (249 scans / 126 patients)

| Model | AUC(120 d) [95% CI] | ΔAUC vs baseline [95% CI] | Cal. slope |
|---|---|---|---|
| Baseline, ridge | 0.698 [0.615, 0.774] | — | 0.89 |
| Baseline, regularised boosting | 0.687 [0.601, 0.768] | −0.012 [−0.072, +0.048] | 0.82 |
| Best radiomics config (post hoc: legacy, pca10, stack) | 0.721 [0.638, 0.793] | +0.023 [−0.013, +0.057] | 0.92 |
| **Nested choice over all 70 radiomics configs (honest)** | **0.666** [0.586, 0.739] | **−0.032 [−0.084, +0.017]** | 0.60 |

Median ΔAUC by variant: legacy +0.005, v2_all4 −0.016, v2_compartments −0.017, v2_lesion −0.001. Configurations with ΔAUC CI
above 0: **0 / 70**. Below 0: 8 / 70 (stacked v2_all4 / v2_compartments, Δ −0.007 to −0.009 with narrow paired CIs).
Nested choices: legacy in 18/25 outer folds, stacked integration in 13/25.

## all_glioma (308 scans / 155 patients)

| Model | AUC(120 d) [95% CI] | ΔAUC vs baseline [95% CI] | Cal. slope |
|---|---|---|---|
| Baseline, ridge | 0.720 [0.638, 0.792] | — | 0.88 |
| Baseline, regularised boosting | 0.718 [0.642, 0.792] | −0.002 [−0.052, +0.047] | 0.87 |
| Best radiomics config (post hoc: legacy, pca10, stack) | 0.754 [0.685, 0.823] | +0.035 [+0.002, +0.068] | 0.96 |
| **Nested choice over all 70 radiomics configs (honest)** | **0.747** [0.678, 0.811] | **+0.028 [−0.017, +0.071]** | 0.85 |

Median ΔAUC by variant: legacy +0.024, v2_all4 +0.000, v2_compartments −0.005, v2_lesion +0.005. Configurations with ΔAUC CI
above 0: **1 / 70**: `legacy|none|pca10|stack`, Δ +0.035 [+0.002, +0.068], p(Δ ≤ 0) = 0.021. This is uncorrected for
multiple testing: at a one-sided 2.5% level about 1.75 of 70 null configurations would exclude 0 by chance. Below 0:
0 / 70. Nested choices: legacy in 25/25 outer folds (`legacy|none|pca10|stack` in 14/25).

## Legacy radiomics ablation (top-10, concatenated, ridge) — 2026-10-06 run, not re-run (superseded inputs)

| Subset | Grade 4 | All gliomas |
|---|---|---|
| Baseline only | 0.694 | 0.719 |
| All legacy (2446) | 0.720 | 0.754 |
| Original image only (214) | 0.722 | 0.754 |
| Original shape (28) | 0.712 | 0.736 |
| Original first-order (36) | 0.708 | 0.742 |
| **Original 2-level texture (150)** | **0.725** | **0.756** |
| Filtered (LoG/wavelet) only (2232) | 0.712 | 0.750 |

## Findings

1. **Radiomics does not improve on the baseline.** Honest nested estimate: Δ −0.032 [−0.084, +0.017] in grade 4 (the
   pre-specified primary analysis) and +0.028 [−0.017, +0.071] in all gliomas. Both CIs span 0. No grade-4 configuration
   has a ΔAUC CI above 0 (0/70). In all gliomas 1/70 does (stacked legacy PCA-10, +0.035 [+0.002, +0.068]), which is
   fewer than the ~1.75 expected by chance among 70 uncorrected tests. The best post-hoc configuration adds +0.023 /
   +0.035.
2. **Correcting the discretisation did not help.** The only variant with a positive median Δ is the legacy 2-level texture
   (+0.005 / +0.024), which behaves as a *binary habitat descriptor* (spatial arrangement of above- vs below-lesion-mean
   voxels). Brain-referenced 32-bin texture (v2) carries no added signal (median Δ −0.017 to +0.005).
3. **Treatment features strengthen the baseline:** ridge 0.698 (grade 4) vs 0.644 for clinical + timing ridge in C2
   (`analyses/baselines/ladder.csv`: −0.054 [−0.103, −0.012]); regularised boosting does not beat ridge (0.687).
4. **Stacking beats concatenation in grade 4** (median Δ −0.003 vs −0.027): with ~200 training scans, appending tens of
   radiomics columns hurts; a single radiomics score is safer. In all gliomas both are ≈ 0 (+0.004 vs +0.000).
5. **Nested radiomics models are overconfident** (calibration slope 0.60 grade 4, 0.85 all gliomas, vs 0.89 / 0.88 baseline).
   Before the clipping fix the slopes were 0.50 / 0.77: part of the overconfidence came from the 1e6 sentinel values.

## Implication
Within MU-Glioma-Post, conventional radiomics adds nothing measurable over clinical + timing + treatment information (honest
grade-4 estimate slightly negative). Previously reported radiomics performance (0.80) reflects a favourable split and a
missing treatment-aware baseline, not image signal.

## Head-to-head on the PRISM report split (126 train / 29 test patients, 82 test scans, all gliomas)

_Not re-run after the clipping fix (2026-10-11 06:44): the three "Baseline + … radiomics" rows predate it. The PRISM
report model and baseline rows do not use `c3.selector` and are unaffected._

PRISM report split = same test patients as the shipped PRISM radiomics model (`legacy/radiomics/models/calibrated/test_predictions.csv`;
one of its 30 test patients has no index scan in the label-fixed cohort); our models trained once on its training patients with
configurations fixed beforehand from repeated CV (no tuning on this split). Source: `outputs/results/c3/prism_report_split/head_to_head.csv`
(`prism head2head`, patient-cluster bootstrap over the test patients, paired Δ vs baseline ridge).

| Model | AUC (original naive label) | AUC IPCW(120 d) [95% CI] | ΔAUC IPCW vs baseline ridge [95% CI] |
|---|---|---|---|
| PRISM report radiomics model (as shipped) | 0.802 | 0.817 [0.690, 0.920] | −0.034 [−0.186, +0.109] |
| Clinical + timing + treatment, ridge | **0.871** | 0.851 [0.735, 0.947] | — |
| Clinical + timing + treatment, regularised boosting | 0.844 | 0.824 [0.690, 0.916] | −0.027 [−0.127, +0.062] |
| Baseline + legacy 2-level texture (top-10) | 0.858 | 0.840 [0.745, 0.932] | −0.010 [−0.083, +0.083] |
| Baseline + legacy radiomics (top-10) | 0.867 | 0.847 [0.745, 0.940] | −0.004 [−0.081, +0.090] |
| Baseline + corrected compartment radiomics (stacked, ICC) | **0.878** | 0.858 [0.751, 0.954] | +0.007 [+0.001, +0.027] |

On the PRISM report split, a model without imaging beats the PRISM report radiomics model by +0.07 (naive label; IPCW +0.034,
CI spanning 0), and adding radiomics changes it by −0.010 to +0.007 (the +0.007 for corrected compartments has a CI just above 0
on 29 patients). Without the early-post-RT × MGMT flag (`head_to_head_masking_only.csv`) the baseline is 0.877 / 0.858 and the
PRISM report model's Δ is −0.041 [−0.190, +0.088]. The same baseline averages 0.720 under repeated CV, so this split is
favourable for every model (`SPLIT_VARIANCE.md`: the baseline ranks above 91% of 500 splits of the same design).

_Update 2026-10-09:_ the L1 selector (`liblinear`) now has a fixed `random_state`.
