# C3 — Can radiomics improve on a clinical + timing + treatment baseline? (2026-10-06)

Code: `prism/radiomics_v2.py` (corrected extraction), `prism/features.py:treatment`, `prism/experiments/c3_radiomics.py`.
Setup: verified 120-d labels, 5×5 repeated patient-grouped CV, all steps in-fold; IPCW AUC(120 d); paired ΔAUC vs the ridge baseline with a patient-cluster bootstrap (1000).

**Baseline** = clinical (age, sex, IDH/MGMT incl. unknown) + timing (days since diagnosis / RT end, early post-RT, visit) + treatment (RT given, dose, fractions, hypofractionation, RT start/duration, chemo, surgery day, biopsy-first, prior tumour).
**Radiomics configurations (70):** variants legacy / corrected whole lesion / corrected per compartment (ET, NETC, SNFH, core, lesion, 5 mm cavity rim + shape) / corrected all 4 sequences × stability filter (ICC ≥ 0.75 vs 1-voxel erosion, in-fold) × selection (top-10, top-30, L1, PCA-10, decorrelate + top-20) × integration (concatenate, stacked radiomics score).
Corrected extraction: whole-brain z-score, fixed 32 bins (GLCM joint entropy 4.7–6.3 bits vs ≤ 2 legacy), no second N4.

## grade4

| Model | AUC(120 d) [95% CI] | ΔAUC vs baseline [95% CI] |
|---|---|---|
| Baseline, ridge | 0.694 [0.613, 0.775] | — |
| Baseline, regularised boosting | 0.723 [0.633, 0.806] | +0.027 [-0.026, +0.083] |
| Best radiomics config (post hoc: legacy, top10, concat) | 0.720 [0.643, 0.792] | +0.024 [-0.032, +0.079] |
| **Nested choice over all 70 radiomics configs (honest)** | **0.686** [0.603, 0.770] | -0.009 [-0.047, +0.025] |

Median ΔAUC by variant: legacy +0.006, v2_all4 -0.008, v2_compartments -0.015, v2_lesion -0.005. Configurations with ΔAUC CI above 0: **0 / 70**.

## all_glioma

| Model | AUC(120 d) [95% CI] | ΔAUC vs baseline [95% CI] |
|---|---|---|
| Baseline, ridge | 0.719 [0.648, 0.788] | — |
| Baseline, regularised boosting | 0.743 [0.666, 0.816] | +0.024 [-0.029, +0.073] |
| Best radiomics config (post hoc: legacy, top10, concat) | 0.754 [0.691, 0.815] | +0.034 [-0.018, +0.082] |
| **Nested choice over all 70 radiomics configs (honest)** | **0.733** [0.662, 0.796] | +0.013 [-0.031, +0.054] |

Median ΔAUC by variant: legacy +0.023, v2_all4 -0.012, v2_compartments -0.015, v2_lesion -0.002. Configurations with ΔAUC CI above 0: **0 / 70**.

## Legacy radiomics ablation (top-10, concatenated, ridge)

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

1. **Radiomics does not meaningfully improve on the baseline.** No configuration has a ΔAUC CI above 0 (0/70 in both populations). Honest nested estimate: Δ −0.009 (grade 4), +0.013 (all gliomas).
2. **Correcting the discretisation did not help — it removed the small signal there was.** The legacy texture, computed on 2 grey levels after within-lesion z-scoring, behaves as a *binary habitat descriptor* (spatial arrangement of above- vs below-lesion-mean voxels: fragmentation, rim vs core), which is scanner-invariant by construction. Brain-referenced 32-bin texture carries no added signal. The best legacy subset adds ~+0.03 (not significant).
3. **Treatment features strengthen the baseline:** ridge 0.694 (grade 4) vs ~0.65–0.67 for clinical/timing-only ridge in C2; regularised boosting 0.723 with calibration slope ~0.97 (vs ~0.6–0.7 for the unregularised boosting in C2).
4. **Stacking beats concatenation** (median Δ −0.003 vs −0.026): with ~180 training scans, appending tens of radiomics columns hurts; a single radiomics score is safer.

## Implication
Within MU-Glioma-Post, conventional radiomics adds at most ~0.02–0.03 AUC over clinical + treatment information, and not significantly. Previously reported radiomics performance (0.80) reflects a favourable split and a missing treatment-aware baseline, not image signal.

## Head-to-head on the PRISM report split (127 train / 30 test patients, all gliomas)

PRISM report split = same 30 test patients as the shipped PRISM radiomics model (`radiomics/models/calibrated/test_predictions.csv`); our models trained once on its training patients with configurations fixed beforehand from repeated CV (no tuning on this split).

| Model | AUC (original naive label) | AUC IPCW(120 d) |
|---|---|---|
| PRISM report radiomics model (as shipped) | 0.802 | 0.811 |
| Clinical + timing + treatment, ridge | **0.870** | 0.844 |
| Clinical + timing + treatment, regularised boosting | **0.901** | 0.881 |
| Baseline + legacy 2-level texture (top-10) | 0.870 | 0.849 |
| Baseline + legacy radiomics (top-10) | 0.869 | 0.848 |
| Baseline + corrected compartment radiomics (stacked, ICC) | 0.869 | 0.843 |

On the PRISM report split, a model without imaging beats the published radiomics model by +0.07 to +0.10 AUC, and adding radiomics changes it by ≤ +0.005. The same models average 0.72–0.74 under repeated CV, so this split is favourable for every model; the ranking (treatment-aware baseline ≥ baseline + radiomics > radiomics-led model) is consistent across both evaluations.
