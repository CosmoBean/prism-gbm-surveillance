# Does imaging add to clinical information? — summary across C2, C3 and LUMIERE (2026-10-10)

Compiled from existing results; no new runs. Sources: [C2_grid_grade4.csv](C2_grid_grade4.csv), [C2_grid_all_glioma.csv](C2_grid_all_glioma.csv),
`outputs/results/c2/<population>/nested_choices.csv`, [C3_radiomics.md](C3_radiomics.md), [EXTERNAL_LUMIERE.md](EXTERNAL_LUMIERE.md).
All MU numbers: verified 120-d labels, 5×5 repeated patient-grouped CV, IPCW AUC(120 d) with patient-cluster bootstrap 95% CI.

## Short answer

**Non-imaging information (clinical + timing + treatment) performs as well as, or better than, models that also use imaging;
imaging alone is worse; and no imaging addition is statistically significant on MU.**

"Clinical" here must be read carefully:

- **Demographics + molecular markers alone** (age, sex, IDH/MGMT) are weak: AUC 0.56–0.63 (grade 4). That is *not* the strong model.
- The strong non-imaging model adds **timing** (days since diagnosis / RT end, early post-RT) and, in C3, **treatment** (RT dose,
  fractions, schedule, chemo, surgery timing). Most of the signal is the RT schedule interacting with age.

## 1. Imaging vs non-imaging on MU (grade 4, n = 253 scans / 128 patients)

| Information used | Ridge | Boosting |
|---|---|---|
| Clinical only (age, sex, IDH/MGMT) | 0.556 [0.456, 0.647] | 0.634 [0.545, 0.713] |
| Clinical + timing | 0.662 [0.583, 0.754] | **0.758** [0.677, 0.838] |
| Clinical + timing + treatment (C3 baseline) | 0.694 [0.613, 0.775] | 0.723 [0.633, 0.806] ¹ |
| Imaging only: volumes + morphology + delta | 0.603 [0.515, 0.686] | 0.545 [0.462, 0.628] |
| Imaging only: + legacy radiomics | 0.660 [0.589, 0.736] | 0.652 [0.567, 0.730] |
| Clinical + timing + volumes | 0.681 [0.604, 0.768] | 0.733 [0.660, 0.805] |
| Clinical + timing + radiomics | 0.709 [0.631, 0.783] | 0.740 [0.669, 0.816] |
| Clinical + timing + all imaging | 0.687 [0.610, 0.767] | 0.717 [0.643, 0.797] |
| C3: baseline + best radiomics, nested over 70 configs (honest) | 0.687, Δ −0.008 [−0.046, +0.026] | — |

¹ C3 regularised boosting (depth 2); C2 boosting rows use depth 3 and overfit more (train AUC ≈ 0.96–1.00).

All gliomas (n = 314 / 157) shows the same pattern: clinical + timing boosting 0.777; adding radiomics 0.777, volumes 0.760,
all imaging 0.752; imaging only ≤ 0.695; C3 nested radiomics Δ +0.013 [−0.031, +0.054].

## 2. Findings

1. **Imaging alone is clearly weaker** than clinical + timing (grade 4: best imaging-only 0.660 vs 0.758).
2. **Adding imaging does not reliably help.** With boosting every imaging addition lowers the AUC (0.758 → 0.717–0.740). With
   ridge, radiomics raises clinical + timing from 0.662 to 0.709, but once treatment features are in the baseline (C3) the
   honest gain is −0.008 (grade 4) / +0.013 (all gliomas), and **0 of 70 radiomics configurations** have a ΔAUC CI above zero.
3. **Nested selection agrees.** Clinical + timing is part of the chosen combination in 22/25 (grade 4) and 24/25 (all gliomas)
   outer folds. An imaging group is usually added too (23/25, 24/25), but a *different* one from fold to fold (volumes,
   morphology, delta or radiomics) — consistent with imaging adding noise-level signal, not a stable effect.
4. **Head-to-head on the PRISM report split** (30 test patients): the PRISM report radiomics model 0.802; clinical + timing +
   treatment without imaging 0.870 (ridge) / 0.901 (boosting); adding radiomics changes this by ≤ +0.005.
5. **External (LUMIERE, 132 scans / 61 patients; no treatment fields available):** the shipped radiomics model drops to 0.61.
   Here tumour volumes *do* help the boosting model (clinical + timing 0.663 → + volumes 0.719), not the ridge model
   (0.628 → 0.629); CIs overlap ([0.513, 0.781] vs [0.609, 0.832]).

## 3. Caveats (state these in the paper)

- **Treatment features are not yet as-of-scan in code.** `prism/features/tabular.py:treatment()` uses RT dose/duration and chemo
  even for scans taken before RT ended (29/215 scans before RT end). A one-off check with as-of-scan masking gave a *higher*
  baseline (grade 4 ridge 0.694 → 0.732), so the conclusion is not driven by this leakage, but the tables must be re-run once
  the masking is in the code.
- **Timing features may partly encode the surveillance schedule.** The label is coupled to when the next MRI happens (time to
  next MRI alone, not available at prediction time, gives AUC 0.64 on grade 4). Early post-RT scans are followed more closely,
  so part of the "timing" signal may be schedule rather than biology.
- **"Imaging adds nothing" is specific to this setting:** conventional MRI (no perfusion/diffusion), one centre, ~130–160
  patients, short-horizon (120 d) progression. It does not mean imaging is uninformative about progression in general.
- Post-hoc rows in §1 (any single configuration) are optimistic; the nested and paired-Δ estimates are the ones to quote.
- Wide CIs throughout; the differences between the non-imaging and imaging-added models are within noise. The supported claim is
  **"imaging does not add measurable value over clinical + treatment information"**, not "clinical beats imaging" in general.
