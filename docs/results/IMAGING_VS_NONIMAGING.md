# Does imaging add to clinical information? — summary across C2, C3, deep features and LUMIERE (2026-10-10; numbers updated after the clipping fix, 2026-10-11)

**Final numbers.** Compiled from the final full re-run (HEAD `cc2e3a3`): `outputs/results/c2/<population>/{grid,nested_choices}.csv`
(copies: [C2_grid_grade4.csv](C2_grid_grade4.csv), [C2_grid_all_glioma.csv](C2_grid_all_glioma.csv)),
`outputs/results/c3/<population>/results.csv`, `outputs/results/analyses/{baselines,deep,schedule}/`,
`outputs/results/external_lumiere/results.csv`, `outputs/results/c3/prism_report_split/head_to_head.csv`. All MU numbers:
verified 120-d labels, 5×5 repeated patient-grouped CV, mean over repeats of per-repeat pooled-OOF IPCW AUC(120 d) with
patient-cluster bootstrap 95% CI. Summary of everything: [FINAL_RESULTS.md](FINAL_RESULTS.md).
The C3, deep and schedule numbers are from the re-run after the radiomics clipping fix
([FIX_RADIOMICS_CLIP.md](FIX_RADIOMICS_CLIP.md)). Two sources were not re-run and still use unclipped legacy radiomics:
the C2 rows with radiomics (`c2_feature_search.py` has no clipping) and the head-to-head radiomics rows. The LUMIERE
models use no radiomics and are unaffected.

## Short answer

**Non-imaging information (clinical + timing + treatment) performs as well as models that also use imaging; no imaging
addition is statistically significant on MU, and the honest (nested) grade-4 estimates are 0.666 (radiomics) and 0.694 (deep)
against 0.698 for the baseline.**

"Clinical" here must be read carefully:

- **Demographics + molecular markers alone** (age, sex, IDH/MGMT) are weak: AUC 0.585 (ridge) / 0.612 (boosting), grade 4.
- The strong non-imaging model adds **timing** (days since diagnosis / RT end, early post-RT) and, in C3, as-of-scan
  **treatment** (RT dose, fractions, schedule, chemo, surgery timing).

## 1. Imaging vs non-imaging on MU (grade 4, n = 249 scans / 126 patients)

| Information used | Ridge | Boosting |
|---|---|---|
| Clinical only (age, sex, IDH/MGMT) | 0.585 [0.496, 0.669] | 0.612 [0.541, 0.688] |
| Clinical + timing | 0.644 [0.567, 0.721] | **0.714** [0.643, 0.785] |
| Clinical + timing + treatment (C3 baseline) | **0.698** [0.615, 0.774] | 0.687 [0.601, 0.768] ¹ |
| Imaging only: volumes + morphology + delta | 0.635 [0.541, 0.709] | 0.568 [0.489, 0.641] |
| Imaging only: + legacy radiomics | 0.678 [0.596, 0.747] | 0.633 [0.563, 0.704] |
| Clinical + timing + volumes | 0.674 [0.581, 0.754] | 0.697 [0.623, 0.768] |
| Clinical + timing + radiomics | 0.687 [0.606, 0.764] | 0.673 [0.606, 0.746] |
| Clinical + timing + all imaging | 0.686 [0.601, 0.758] | 0.675 [0.603, 0.747] |
| C3: baseline + radiomics, nested over 70 configs (honest) | 0.666, Δ −0.032 [−0.084, +0.017] | — |
| Deep: baseline + frozen SwinUNETR features, nested over 32 (honest) | 0.694, Δ −0.004 [−0.069, +0.063] | — |

¹ C3 regularised boosting (depth 2); C2 boosting rows use depth 3 and overfit more (train AUC ≥ 0.96).
Sources: C2 rows `c2/grade4/grid.csv`; C3 rows `c3/grade4/results.csv`; deep row `analyses/deep/grade4/results.csv`.

All gliomas (n = 308 / 155): clinical + timing boosting 0.739; adding radiomics 0.723, volumes 0.728, all imaging 0.721 (boosting);
the best ridge models add radiomics (0.744) and the best imaging-only model reaches 0.725 (ridge, volumes + morphology +
radiomics) — imaging partly separates tumour grades in this population. C3 nested radiomics Δ +0.028 [−0.017, +0.071]; deep
Δ +0.011 [−0.032, +0.056].

## 2. Findings

1. **Imaging alone is weaker than clinical + timing in grade 4** (best imaging-only 0.683 vs 0.714). In all gliomas the gap
   closes (0.725 vs 0.739).
2. **Adding imaging does not reliably help.** With boosting every imaging addition lowers the grade-4 AUC (0.714 → 0.632–0.705).
   With ridge, radiomics raises clinical + timing from 0.644 to 0.687, but once treatment features are in the baseline (C3)
   the honest gain is −0.032 (grade 4) / +0.028 (all gliomas).
   - Radiomics configurations with a ΔAUC CI above 0: **0 of 70** in grade 4 (8/70 below 0) and 1 of 70 in all gliomas.
     The all-glioma one is stacked legacy PCA-10, +0.035 [+0.002, +0.068], uncorrected, against ~1.75 expected by chance.
   - Frozen deep features: 0/80 single configurations above 0 in grade 4 and 3/80 in all gliomas, against ~2 expected by
     chance (`DEEP_FEATURES.md`).
3. **Nested selection agrees.** Clinical + timing is in the chosen C2 combination in 17/25 (grade 4) and 12/25 (all gliomas)
   outer folds. An imaging group is usually added (23/25, 22/25), but a *different* one from fold to fold — consistent with
   imaging adding noise-level signal. The grade-4 nested C2 search (0.664) is only marginally above its permutation null
   (p = 0.050).
4. **Literature imaging baselines are weaker still** (`BASELINES.md`): volumetric RANO-style rule 0.551, ET volume 0.636,
   Hashim-style Cox 0.628, vs the baseline 0.698 (grade 4).
5. **Head-to-head on the PRISM report split** (29 test patients): the PRISM report radiomics model 0.802; clinical + timing +
   treatment without imaging 0.871 (ridge) / 0.844 (boosting); adding radiomics changes the ridge baseline by −0.010 to +0.007
   (this run predates the clipping fix).
6. **External (LUMIERE, 132 scans / 61 patients; no treatment fields available):** the shipped PRISM report radiomics model
   drops to 0.61. Tumour volumes do **not** help the locked models (grade-4-trained: ridge 0.610 → 0.608, boosting
   0.632 → 0.620; pooled, CIs ±0.12); within-cohort rank normalisation of the volumes recovers part of this (boosting 0.659).
   Frozen deep features give +0.05 to +0.09, with only one of four CIs just above 0, and the gain is not reliably above a
   random-weight encoder.

## 3. Caveats (state these in the paper)

- **Treatment features are now as-of-scan** (`FIX_TREATMENT_ASOF.md`); the earlier caveat about RT/chemo information leaking
  into pre-RT-end scans no longer applies to these numbers.
- **Timing features may partly encode the surveillance schedule.** Time to next MRI alone (not available at prediction time)
  gives AUC 0.639 in grade 4 and 0.788 in LUMIERE. In MU the baseline keeps its discrimination within gap tertiles
  (conditional AUC 0.687) and its coefficient barely changes after adjustment for log gap (`SCHEDULE_COUPLING.md`).
- **"Imaging adds nothing" is specific to this setting:** conventional MRI (no perfusion/diffusion), one centre, ~130–160
  patients, short-horizon (120 d) progression. It does not mean imaging is uninformative about progression in general.
- Post-hoc rows in §1 (any single configuration) are optimistic; the nested and paired-Δ estimates are the ones to quote.
- Wide CIs throughout; the supported claim is **"imaging does not add measurable value over clinical + treatment
  information"**, not "clinical beats imaging" in general.
