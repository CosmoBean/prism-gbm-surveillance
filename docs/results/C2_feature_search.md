# C2 — Feature-group search: results (2026-10-06)

Code: `prism/measurements.py` (compartment concepts + past-only deltas), `prism/experiments/c2_feature_search.py`.
Run: `uv run python -m prism.measurements && uv run python -m prism.experiments.c2_feature_search --population grade4` (~15 min, 64 workers).
Setup: 63 combinations of 6 groups × 2 learners (ridge logistic with inner-CV penalty; gradient boosting, fixed shallow config); verified 120-d labels; 5×5 repeated patient-grouped CV; all fitting in-fold; IPCW AUC(120 d) with patient-cluster bootstrap CIs.

Groups: **clinical** (age, sex, IDH/MGMT incl. unknown) · **timing** (days since diagnosis, days since RT end, early post-RT, visit index) · **volumes** (ET/NETC/SNFH/RC/tumour/lesion) · **morphology** (ET fraction, multifocality, max axial ET area, ET-to-cavity proximity, intensities vs normal-appearing brain) · **delta** (vs prior scan and nadir, growth rate, ≥40 % ET flag, new component) · **radiomics** (legacy T1c+FLAIR, top-20 in-fold).

## grade4

Top 8 configurations (selected post hoc → optimistic):

| Learner | Groups | AUC(120 d) [95% CI] | Train AUC | Overfit gap | Cal. slope |
|---|---|---|---|---|---|
| gbm | clinical+timing | 0.758 [0.677, 0.838] | 0.963 | 0.220 | 0.72 |
| gbm | clinical+timing+radiomics | 0.740 [0.669, 0.816] | 0.999 | 0.284 | 0.62 |
| gbm | clinical+timing+volumes+delta+radiomics | 0.738 [0.662, 0.812] | 1.000 | 0.286 | 0.63 |
| gbm | clinical+timing+delta+radiomics | 0.736 [0.662, 0.819] | 1.000 | 0.289 | 0.62 |
| gbm | clinical+timing+volumes+radiomics | 0.736 [0.668, 0.807] | 1.000 | 0.288 | 0.60 |
| gbm | clinical+timing+volumes | 0.733 [0.660, 0.805] | 0.997 | 0.278 | 0.67 |
| gbm | clinical+timing+delta | 0.730 [0.646, 0.814] | 0.980 | 0.264 | 0.61 |
| gbm | clinical+timing+morphology+delta+radiomics | 0.724 [0.648, 0.807] | 1.000 | 0.299 | 0.57 |

Single groups (ridge):

- radiomics: 0.678 [0.601, 0.754]
- morphology: 0.612 [0.526, 0.688]
- volumes: 0.573 [0.487, 0.659]
- timing: 0.571 [0.481, 0.663]
- clinical: 0.556 [0.456, 0.647]
- delta: 0.491 [0.403, 0.567]

**Nested search (honest estimate of choosing the combination):** AUC 0.658 ± 0.008. **Label-permutation control (5 shuffles):** 0.42–0.57 (mean 0.50) → no leakage.

## all_glioma

Top 8 configurations (selected post hoc → optimistic):

| Learner | Groups | AUC(120 d) [95% CI] | Train AUC | Overfit gap | Cal. slope |
|---|---|---|---|---|---|
| gbm | clinical+timing+delta+radiomics | 0.779 [0.714, 0.839] | 0.998 | 0.252 | 0.77 |
| gbm | clinical+timing+radiomics | 0.777 [0.715, 0.838] | 0.997 | 0.249 | 0.75 |
| gbm | clinical+timing | 0.777 [0.704, 0.844] | 0.959 | 0.196 | 0.75 |
| gbm | clinical+timing+delta | 0.771 [0.706, 0.836] | 0.978 | 0.222 | 0.74 |
| gbm | clinical+timing+volumes+radiomics | 0.763 [0.698, 0.826] | 0.999 | 0.265 | 0.71 |
| gbm | clinical+timing+volumes+delta+radiomics | 0.762 [0.695, 0.824] | 0.999 | 0.266 | 0.71 |
| gbm | clinical+timing+morphology+delta+radiomics | 0.761 [0.694, 0.823] | 1.000 | 0.269 | 0.71 |
| gbm | clinical+timing+volumes | 0.760 [0.696, 0.830] | 0.995 | 0.251 | 0.69 |

Single groups (ridge):

- radiomics: 0.701 [0.633, 0.762]
- morphology: 0.637 [0.557, 0.706]
- timing: 0.617 [0.536, 0.698]
- volumes: 0.612 [0.526, 0.687]
- clinical: 0.591 [0.505, 0.670]
- delta: 0.504 [0.430, 0.582]

**Nested search (honest estimate of choosing the combination):** AUC 0.723 ± 0.012. **Label-permutation control (5 shuffles):** 0.40–0.53 (mean 0.49) → no leakage.

## Findings

1. **The best model uses no imaging.** Gradient boosting on clinical + timing: 0.758 (grade 4) / 0.777 (all). Signal comes from the **RT end day** (diagnosis → end of radiotherapy; progressors median 55 vs 61 d; alone AUC 0.66) interacting with age — consistent with short-course RT in older/frailer patients. Available at scan time, so a legitimate baseline, not leakage. Imaging must be judged against it; none of the imaging groups clearly beats it.
2. **Average gain from adding a group (ridge, paired over all other combos, grade 4):** radiomics +0.056, timing +0.035, clinical +0.033, morphology +0.012, volumes +0.005, delta −0.004.
3. **Delta features are informative only where defined**: on the 117 grade-4 scans with a prior, Δ-nadir ET AUC 0.65 and the ≥40 % ET flag 0.67 — but current ET volume alone is 0.69 on the same scans. Half of scans have no prior, so cohort-wide they add nothing.
4. **Overfitting:** gradient boosting train AUC ≈ 1.00 vs test ≈ 0.73 (gap ~0.3); ridge gap ~0.10–0.14. Nested selection picks clinical+timing in nearly every fold; imaging groups are added inconsistently.
5. **Honest performance:** nested 0.66 (grade 4) / 0.72 (all gliomas) vs the reported 0.80.

## Next
- Treatment features explicitly (RT dose/fractions, chemo, extent of resection) as a clinical+treatment baseline.
- Regularise boosting (shallower trees, fewer iterations, subsampling, monotone constraints) and add it to the nested search.
- Corrected radiomics (brain-referenced normalisation, fixed bin count, per compartment) to give imaging a fair test.
- Delta features for the 'has prior' subgroup as a separate analysis (surveillance with history).
