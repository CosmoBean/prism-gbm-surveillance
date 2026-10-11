# Fix: as-of-scan treatment features and post-RT window × MGMT (2026-10-11)

> **Superseded numbers.** The AUCs in this file document the fix itself on intermediate inputs (before the later label,
> evaluation and empty-segmentation fixes, some with the old repeat-averaged estimator). They are not the reported results.
> Final numbers: [FINAL_RESULTS.md](FINAL_RESULTS.md) (e.g. grade-4 baseline ridge 0.698 [0.615, 0.774], nested radiomics
> ΔAUC −0.026 [−0.073, +0.017], `outputs/results/c3/grade4/results.csv`; LUMIERE in [EXTERNAL_LUMIERE.md](EXTERNAL_LUMIERE.md)).

Code: `prism/features/tabular.py` (`timing`, `treatment`), tests in `tests/test_treatment_asof.py`.
Before = `outputs/results_pre_fix_2026-10-11/`; after = `outputs/results/`; masking-only ablation (no new flag) =
`outputs/results/{c2,c3}/grade4_ablation_masking_only/`. PRISM report split head-to-head: `outputs/results/c3/prism_report_split/`.

## 1. What leaked

The cohort index date is the scan day (`days_from_diagnosis_to_mri`), but `treatment()` and `timing()` read the clinical
workbook as of the end of follow-up:

| Feature | Problem | Scans affected (grade 4 / all) |
|---|---|---|
| `rt_given`, `chemo_given` | "will receive RT / TMZ", true for scans taken before the course started | 13 / 23 (RT), 13 / 21 (chemo) |
| `rt_dose_gy`, `rt_fractions`, `rt_hypofractionated`, `rt_start_day` | prescription and start date of a course that had not started | 13 / 19–23 |
| `rt_duration_days` (= end − start) | duration of a course not yet finished (also reveals early stopping) | 17 / 29 |
| `days_since_rt_end`, `rt_date_unknown` (timing) | negative values used the future RT end date | 17 / 29 |
| `surgery_day`, `biopsy_before_resection` | one scan precedes the first surgery | 1 / 1 |

`early_post_rt` (0 ≤ days since RT end ≤ 84) was already as-of: it can only be 1 after RT has ended.
Search of the rest of `prism/` for future dates: progression, death, last follow-up and late-treatment dates are used only
for labels, censoring and cohort eligibility (`prism/data/mu.py`), not as features. `visit_index` and the measurement deltas
(`prism/features/measurements.py:add_deltas`) use earlier scans only. `clinical()` (age, sex, IDH, MGMT) is fixed at diagnosis.
C1 uses no treatment or timing features; its results are byte-identical after the fix. LUMIERE has no treatment fields.

## 2. Rule

A treatment fact enters the feature vector only once its documented start day is ≤ the scan day.

- **RT started** (scan day ≥ RT start): `rt_started = 1`; prescription (dose, fractions, hypofractionation ≤ 15 fx) and
  `rt_start_day` become visible. The prescription is fixed at planning, before the first fraction, so it is known at RT
  start; we do not expose it earlier (at the pre-RT scan the plan may not yet be final, and "will start RT" implies the
  patient stayed fit enough to start).
- **RT completed** (scan day ≥ RT end): `rt_completed = 1`; `rt_duration_days` and `days_since_rt_end` become visible. A
  course in progress has no known end date (it may be cut short), so these are NaN until it ends.
- **Chemo** (initial TMZ/lomustine): `chemo_started = 1` once scan day ≥ the workbook's initial-chemo start date.
- Not-yet-known values are NaN, imputed in-fold (median + missingness indicator, as before) next to the explicit
  `rt_started` / `rt_completed` / `chemo_started` indicators; nothing is zero-filled silently. `rt_date_unknown` now
  means "no completed RT with a known end date at the scan".
- Therapy marked given with no start date (2 RT, 2 chemo patients): taken as started before the scan (assumption).
- Surgery day and biopsy-first are visible only once the first surgery has happened (1 scan).

`rt_given` / `chemo_given` are replaced by `rt_started` / `chemo_started`; `rt_completed` is new.

**New flag** (timing): `early_post_rt_x_mgmt_methylated` = `early_post_rt` × MGMT methylated. `early_post_rt` is already
exactly the RANO 12-week (84 d) post-RT pseudoprogression window (Brandes 2008; Taal 2008; Wen 2010/2023), so only the
interaction was added (38 grade-4 scans have it = 1, of 98 in the window).

## 3. Before / after

IPCW AUC(120 d) [95% patient-cluster bootstrap CI]. "Masking only" = the fix without the new MGMT flag (grade 4 only).

### C2 (no treatment group in C2; it changes through timing only)

| Population | Row | Before | After | Masking only |
|---|---|---|---|---|
| grade 4 | clinical + timing, ridge | 0.662 [0.583, 0.754] | 0.668 [0.591, 0.752] | 0.676 [0.599, 0.764] |
| grade 4 | clinical + timing, boosting (best grid row) | 0.758 [0.677, 0.838] | 0.755 [0.670, 0.831] | 0.756 [0.670, 0.831] |
| grade 4 | timing, boosting | 0.718 | 0.696 | 0.700 |
| grade 4 | nested search (AUC of averaged / mean over repeats) | 0.677 / 0.658 | 0.677 / 0.659 | 0.677 / 0.662 |
| all | clinical + timing, ridge | 0.727 [0.657, 0.796] | 0.708 [0.634, 0.783] | — |
| all | clinical + timing, boosting | 0.777 [0.704, 0.844] | 0.770 [0.699, 0.838] | — |
| all | timing, boosting | 0.735 | 0.705 | — |
| all | nested search | 0.742 / 0.723 | 0.732 / 0.716 | — |

Permutation control unchanged (mean of 5 permuted runs 0.48–0.49 before and after).

### C3 baseline (clinical + timing + treatment) and radiomics

| Population | Row | Before | After | Masking only |
|---|---|---|---|---|
| grade 4 | Baseline, ridge | 0.694 [0.613, 0.775] | **0.729** [0.648, 0.811] | 0.730 [0.648, 0.812] |
| grade 4 | Baseline, boosting | 0.723 [0.633, 0.806] | 0.731 [0.641, 0.813] | 0.734 [0.644, 0.817] |
| grade 4 | Nested radiomics | 0.687; Δ −0.008 [−0.046, +0.026] | 0.738; Δ **+0.009** [−0.027, +0.040] | 0.736; Δ +0.006 [−0.030, +0.039] |
| grade 4 | Best config (post hoc) | legacy top10 concat 0.720; Δ +0.024 | legacy decor20 concat 0.744; Δ +0.015 [−0.044, +0.073] | 0.747; Δ +0.017 |
| grade 4 | Configs with Δ CI > 0 / < 0 (of 70) | 0 / 2 | **0** / 5 | 0 / 4 |
| all | Baseline, ridge | 0.719 [0.648, 0.788] | **0.749** [0.675, 0.820] | — |
| all | Baseline, boosting | 0.743 [0.666, 0.816] | 0.740 [0.663, 0.815] | — |
| all | Nested radiomics | 0.733; Δ +0.013 [−0.031, +0.054] | 0.763; Δ **+0.013** [−0.022, +0.047] | — |
| all | Best config (post hoc) | legacy top10 concat 0.754; Δ +0.034 | legacy pca10 stack 0.774; Δ +0.025 [+0.003, +0.046] | — |
| all | Configs with Δ CI > 0 / < 0 (of 70) | 0 / 2 | **1** / 4 | — |

Calibration slope of the grade-4 ridge baseline: 0.853 → 0.928.

### PRISM report split (127 train / 30 test patients, all gliomas; trained once, configurations fixed)

Reproduced exactly before the fix (`head_to_head_before.csv` matches C3_radiomics.md to 3 decimals).

| Model | Before naive / IPCW | After naive / IPCW | Masking only |
|---|---|---|---|
| PRISM report radiomics model (as shipped) | 0.802 / 0.811 | 0.802 / 0.811 | — |
| Baseline, ridge | 0.870 / 0.844 | 0.880 / 0.860 | 0.885 / 0.870 |
| Baseline, boosting | 0.901 / 0.881 | 0.869 / 0.855 | 0.883 / 0.868 |
| Baseline + legacy 2-level texture (top-10) | 0.870 / 0.849 | 0.871 / 0.852 | 0.875 / 0.856 |
| Baseline + legacy radiomics (top-10) | 0.869 / 0.848 | 0.871 / 0.852 | 0.873 / 0.855 |
| Baseline + corrected compartments (ICC, top-10, stacked) | 0.869 / 0.843 | 0.886 / 0.870 | 0.887 / 0.872 |

### LUMIERE external (`outputs/results/external_lumiere/results.csv`)

The shared features have no treatment block; the only change is one MU scan before first surgery (log days since surgery
now missing instead of 0). Largest change in any of the 88 rows: 0.015. Best locked rows:
grade-4-trained clinical + timing + volumes, boosting 0.719 [0.609, 0.832] → 0.717 [0.601, 0.823];
all-glioma-trained 0.697 [0.563, 0.816] → 0.692 [0.557, 0.810]. The PRISM report model on LUMIERE (`shipped_model.csv`,
0.61) does not use these features and was not re-run.

## 4. Reading

- **Removing the leakage raised the treatment-aware baseline** (ridge +0.035 grade 4, +0.030 all gliomas; grade 4
  0.694 → 0.729, "After" column of the C3 table in section 3). The earlier one-off check quoted in
  `docs/PIPELINE_REVIEW.md` (T1: 0.694 → 0.732) was an exploratory run; no script or output for it exists in docs/,
  outputs/ or the session scratchpad, so it cannot be reproduced; use the pipeline number. The leaked values gave pre-RT and on-RT scans the treatment profile of a
  completed course and mixed them with post-RT scans (negative days since RT end); with the masking they are an explicit
  state (`rt_started`, `rt_completed`). The gain is within the CIs.
- **The MGMT × window flag adds nothing**: masking-only and full results differ by ≤ 0.008 in every repeated-CV row (grade 4
  C3 ridge 0.730 vs 0.729; C2 clinical + timing ridge 0.676 vs 0.668), and the full model is slightly lower, not higher
  (≤ 0.014 on the 30-patient split). All of the change comes from the masking. Keeping the flag
  is harmless; its value is interpretability, not AUC.
- **Timing alone is weaker after the fix** (boosting 0.718 → 0.696 grade 4, 0.735 → 0.705 all): part of its earlier
  signal came from the future RT end date. C2 clinical + timing and nested search barely move.
- **Main conclusion unchanged**: radiomics does not improve on the corrected baseline. Nested ΔAUC +0.009 (grade 4) and
  +0.013 (all gliomas), both CIs spanning 0. One of 70 all-glioma configurations now has a CI above 0 (legacy, PCA-10,
  stacked: +0.025 [+0.003, +0.046]); with 70 unadjusted intervals about 1–2 are expected by chance, and the
  post-hoc best config is not the honest estimate. Report it, do not headline it.
- **PRISM report split**: the corrected non-imaging baseline still beats the PRISM report radiomics model (ridge 0.880 vs
  0.802 naive AUC). Boosting fell from 0.901 to 0.869, which is single-split noise (30 patients), and adding radiomics
  still changes the baseline by ≤ ±0.01 (ridge 0.880 → 0.871 legacy, 0.886 corrected compartments).

Numbers in the other docs/results files (C3_radiomics.md, IMAGING_VS_NONIMAGING.md, EXTERNAL_LUMIERE.md) are pre-fix.

## Reproduce

```
uv run --frozen --no-sync python -m unittest discover -s tests
uv run --frozen --no-sync python -m prism c1
uv run --frozen --no-sync python -m prism c2 --population grade4 --workers 40      # and all_glioma
uv run --frozen --no-sync python -m prism c3 --population grade4 --workers 40      # and all_glioma
uv run --frozen --no-sync python -m prism external
PYTHONPATH=. uv run --frozen --no-sync python outputs/results/c3/prism_report_split/head_to_head.py new out.csv
```
The head-to-head is not a `prism` stage; `head_to_head.py` (copied next to its outputs) rebuilds it from
`legacy/radiomics/models/calibrated/test_predictions.csv` with `prism.experiments.c3_radiomics.fit_predict`. Its `old`
mode imports the pre-fix `tabular.py` from a scratch path and is only for the before column.
The masking-only rows monkeypatch `timing()` to drop `early_post_rt_x_mgmt_methylated`.
