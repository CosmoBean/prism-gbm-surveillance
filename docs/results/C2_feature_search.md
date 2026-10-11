# C2 — Feature-group search: results (2026-10-06; numbers updated to the final run 2026-10-11)

**Final numbers** from the final full re-run: `outputs/results/c2/<population>/{grid,nested,nested_choices,permutation}.csv`
(2026-10-11, label-fixed cohort: grade 4 249 scans / 126 patients, all gliomas 308 / 155; mean over 5 repeats of the
per-repeat pooled-OOF IPCW AUC with patient-cluster bootstrap CIs; nested search over ridge + boosting; 100 patient-block
permutations). Copies of the grids: [C2_grid_grade4.csv](C2_grid_grade4.csv), [C2_grid_all_glioma.csv](C2_grid_all_glioma.csv).
The 2026-10-06 numbers (253 scans, repeat-averaged estimator, ridge-only nested search, 5 scan-level shuffles) are superseded.
C2 has no treatment block; the treatment-aware baseline is in [C3_radiomics.md](C3_radiomics.md).

Code: `prism/features/measurements.py` (compartment concepts + past-only deltas), `prism/experiments/c2_feature_search.py`.
Run: `scripts/04_c2_feature_search.sh` (both populations).
Setup: 63 combinations of 6 groups × 2 learners (ridge logistic with inner-CV penalty; gradient boosting, fixed shallow config); verified 120-d labels; 5×5 repeated patient-grouped CV; all fitting in-fold; IPCW AUC(120 d) with patient-cluster bootstrap CIs.

Groups: **clinical** (age, sex, IDH/MGMT incl. unknown) · **timing** (days since diagnosis, days since RT end, early post-RT, visit index) · **volumes** (ET/NETC/SNFH/RC/tumour/lesion) · **morphology** (ET fraction, multifocality, max axial ET area, ET-to-cavity proximity, intensities vs normal-appearing brain) · **delta** (vs prior scan and nadir, growth rate, ≥40 % ET flag, new component) · **radiomics** (legacy T1c+FLAIR, top-20 in-fold).

## grade4

Top 8 configurations (selected post hoc → optimistic):

| Learner | Groups | AUC(120 d) [95% CI] | Train AUC | Overfit gap | Cal. slope |
|---|---|---|---|---|---|
| gbm | clinical+timing | 0.714 [0.643, 0.785] | 0.961 | 0.247 | 0.61 |
| gbm | clinical+timing+volumes+delta | 0.705 [0.634, 0.776] | 0.998 | 0.293 | 0.52 |
| gbm | clinical+timing+delta | 0.704 [0.634, 0.774] | 0.980 | 0.276 | 0.53 |
| gbm | clinical+timing+volumes | 0.697 [0.623, 0.768] | 0.998 | 0.301 | 0.51 |
| ridge | clinical+timing+volumes+radiomics | 0.697 [0.612, 0.770] | 0.811 | 0.114 | 0.81 |
| ridge | clinical+volumes+morphology+radiomics | 0.696 [0.617, 0.769] | 0.808 | 0.112 | 0.82 |
| ridge | clinical+volumes+radiomics | 0.695 [0.618, 0.766] | 0.798 | 0.103 | 0.77 |
| ridge | clinical+timing+volumes+morphology+radiomics | 0.692 [0.608, 0.765] | 0.826 | 0.133 | 0.78 |

Single groups (ridge / boosting):

- radiomics: 0.675 [0.595, 0.746] / 0.628
- morphology: 0.650 [0.561, 0.730] / 0.538
- volumes: 0.611 [0.526, 0.694] / 0.573
- clinical: 0.585 [0.496, 0.669] / 0.612
- timing: 0.559 [0.478, 0.634] / 0.649
- delta: 0.537 [0.460, 0.606] / 0.565

**Nested search over all 126 (learner, combination) candidates (honest):** 0.664 [0.601, 0.722] (calibration slope 0.49). **Permutation control (100 patient-block permutations, full nested pipeline):** null mean 0.548, 95th percentile 0.636, max 0.690; 4 of 100 ≥ observed, **p = 0.050**. Nested choices: boosting in 15/25 outer folds; clinical + timing in 17/25 chosen combinations, an imaging group added in 23/25 (most frequent: clinical+timing+delta, 5/25).

## all_glioma

Top 8 configurations (selected post hoc → optimistic):

| Learner | Groups | AUC(120 d) [95% CI] | Train AUC | Overfit gap | Cal. slope |
|---|---|---|---|---|---|
| ridge | clinical+timing+volumes+morphology+radiomics | 0.744 [0.679, 0.804] | 0.844 | 0.100 | 0.89 |
| ridge | clinical+timing+morphology+radiomics | 0.744 [0.680, 0.804] | 0.842 | 0.098 | 0.89 |
| ridge | clinical+volumes+morphology+radiomics | 0.742 [0.676, 0.801] | 0.834 | 0.093 | 0.86 |
| ridge | clinical+timing+volumes+radiomics | 0.740 [0.674, 0.801] | 0.830 | 0.090 | 0.87 |
| gbm | clinical+timing+delta | 0.739 [0.675, 0.805] | 0.975 | 0.235 | 0.61 |
| ridge | clinical+radiomics | 0.739 [0.675, 0.801] | 0.817 | 0.077 | 0.86 |
| gbm | clinical+timing | 0.739 [0.674, 0.807] | 0.955 | 0.215 | 0.61 |
| ridge | clinical+volumes+radiomics | 0.739 [0.673, 0.799] | 0.822 | 0.083 | 0.85 |

Single groups (ridge / boosting):

- radiomics: 0.714 [0.646, 0.770] / 0.683
- morphology: 0.687 [0.612, 0.755] / 0.593
- volumes: 0.659 [0.575, 0.737] / 0.580
- clinical: 0.619 [0.538, 0.691] / 0.648
- timing: 0.607 [0.531, 0.686] / 0.677
- delta: 0.557 [0.488, 0.630] / 0.592
**Nested search (honest):** 0.707 [0.647, 0.766] (calibration slope 0.65). **Permutation control (100):** null mean 0.528,
95th percentile 0.592, max 0.655; 0 of 100 ≥ observed, **p = 0.010** (the smallest p 100 permutations can give). Nested choices:
ridge in 18/25 outer folds; clinical + timing in 12/25, an imaging group in 22/25 (most frequent: clinical+volumes+radiomics, 5/25).

## Findings

1. **The best grade-4 model uses no imaging.** Gradient boosting on clinical + timing: 0.714 (grade 4); in all gliomas it ties
   (0.739) with ridge models that add radiomics/morphology (0.744). Available at scan time, so a legitimate baseline, not
   leakage. Imaging must be judged against it; none of the imaging groups clearly beats it.
2. **Average gain from adding a group (ridge, paired over all other combos):** grade 4 radiomics +0.045, clinical +0.027,
   morphology +0.017, volumes +0.012, timing +0.007, delta −0.003 (all gliomas: +0.043, +0.030, +0.021, +0.012, +0.016, −0.006);
   computed from `grid.csv`.
3. **Delta features** add nothing cohort-wide (single-group ridge 0.537 grade 4); half of scans have no prior. (The has-prior
   subgroup analysis of the 2026-10-06 version was not re-run.)
4. **Overfitting:** boosting train AUC 0.84–1.00 (≥ 0.95 for every combination with clinical + timing) vs test ≈ 0.70
   (median gap 0.36 grade 4, 0.30 all gliomas); ridge gap 0.04–0.15 (median 0.12 / 0.10).
5. **Honest performance:** nested 0.664 (grade 4) / 0.707 (all gliomas) vs the PRISM report's 0.80, well below the post-hoc
   grid best (0.714 / 0.744). The grade-4 nested estimate is only marginally above the permutation null (p = 0.050): the null
   is centred at 0.55, not 0.5, because choosing among 126 candidates on inner CV is optimistic even without signal.
