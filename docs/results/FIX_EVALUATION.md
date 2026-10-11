# Evaluation fixes (2026-10-11)

Fixes from the evaluation audit. Code: `prism/models/metrics.py` (new estimator helpers), `prism/experiments/{c1_endpoint,
c2_feature_search,c3_radiomics,external_lumiere}.py`, `prism/analyses/head_to_head.py` (new stage),
`prism/__main__.py`, `scripts/`, `legacy/shipped_on_lumiere.py` (`adapt()` only). Tests: `tests/test_repeated_metrics.py`.

> **Numbers in sections 1–5 are from a validation run on intermediate inputs (253 grade-4 scans, before the label and
> feature fixes); they are superseded for reporting.** Final numbers: [FINAL_RESULTS.md](FINAL_RESULTS.md). The final
> equivalents of the section 1–5 rows (full re-run, HEAD `cc2e3a3`, same estimator) are:
>
> | Grade 4, H = 120 d | Final (mean over repeats) [95% CI] | Source |
> |---|---|---|
> | C1 volumes + clinical, naive / ipcw | 0.651 [0.567, 0.727] / 0.656 [0.578, 0.731] | `outputs/results/c1/c1_summary.md` |
> | C1 radiomics + clinical, naive / hazard | 0.648 [0.553, 0.736] / 0.669 [0.583, 0.746] | same |
> | C2 grid best (boosting, clinical + timing) | 0.714 [0.643, 0.785] | `outputs/results/c2/grade4/grid.csv` |
> | C2 nested (ridge + boosting); permutation p (100) | 0.664 [0.601, 0.722]; null mean 0.548, 95th pct 0.636, p = 0.050 (4 of 100 ≥ observed) | `c2/grade4/{nested,permutation}.csv` |
> | C3 baseline ridge / boosting | 0.698 [0.615, 0.774] / 0.687 [0.601, 0.768] | `outputs/results/c3/grade4/results.csv` |
> | **C3 nested radiomics; ΔAUC vs baseline ridge** | **0.672 [0.597, 0.743]; −0.026 [−0.073, +0.017]** | same |
> | C3 configs with ΔAUC CI > 0 / < 0 (of 70) | 0 / 12 | same |
> | External, grade-4 boosting, clinical + timing + volumes, locked: per fold / pooled | 0.608 [0.493, 0.691] / 0.620 [0.495, 0.733] | `outputs/results/external_lumiere/results.csv` |
> | Head-to-head (29 test patients, 82 scans): PRISM report model / baseline ridge, naive / IPCW | 0.802 / 0.817 [0.690, 0.920]; 0.871 / 0.851 [0.735, 0.947] | `outputs/results/c3/prism_report_split/head_to_head.csv` |
>
> In particular the section 3 statement "p = 0.010 (0 of 100 ≥ observed)" for grade 4 does **not** hold in the final run
> (p = 0.0495); all gliomas: p = 0.0099 (0 of 100).

**Validation run.** Private output dir (`$PRISM_OUTPUTS` = scratchpad `out-eval/`) with copies of `outputs/data` and
`outputs/features` taken 2026-10-11 04:31, i.e. the labels/features after the treatment-as-of fix and *before* any
concurrent data/feature fixes. Ran c1, c2 grade 4, c3 grade 4, external, head2head (both modes) and the shipped-model
adaptation. "Before" numbers come from the same inputs: the old estimator is kept as a column in every new
output (`*_averaged`), the old external code (git HEAD) was re-run on the same inputs, and for C1/C2/C3 the shared
`outputs/results/` was produced from identical inputs (checked: repeat-averaged AUCs match to 3 decimals).
`outputs/results/external_lumiere/results.csv` (shared) predates the current inputs and does **not** match them
(grade-4 locked boosting, clinical + timing + volumes: 0.717 there, 0.679 with the old code on today's inputs). So the
external before/after below compares both versions of the code on today's inputs.

## 1. Headline estimator for repeated CV (major)

Before, the headline was the AUC of the OOF prediction **averaged over the 5 repeats**. That is an ensemble of 5 models
per scan, so it is optimistic, more so for unstable pipelines (nested selection). Now the headline is the
**mean over repeats of the per-repeat pooled-OOF IPCW AUC** (and Brier, O/E, slope). The CI comes from a patient-cluster
bootstrap: each resample draws patients once, then computes the mean-over-repeats AUC of every model on that draw, so
differences are paired. ΔAUC is reported as the point estimate (not the bootstrap mean) with the bootstrap CI. The old
estimator is kept as `auc_ipcw_averaged` (with its own CI and `d_auc_ipcw_averaged`).
Helpers: `repeated_point_metrics`, `repeated_bootstrap`, `evaluate_repeated`. The bootstrap uses a vectorised
IPCW AUC/Brier (`ipcw_context`, `fast_auc_brier`). It matches sksurv to 2e-16 on real data and on bootstrap resamples
(unit-tested), and runs about 100x faster. `cluster_bootstrap` keeps its signature but now also reports the
ΔAUC point estimate; the old bootstrap mean is in `d_<metric>_boot_mean`.

| Grade 4, H = 120 d | Before (repeat-averaged) | After (mean over repeats) [95% CI] |
|---|---|---|
| C1 volumes + clinical, naive / ipcw | 0.638 / 0.629 | 0.630 [0.553, 0.704] / 0.621 [0.544, 0.698] |
| C1 radiomics + clinical, naive / hazard | 0.671 / 0.699 | 0.666 [0.580, 0.736] / 0.693 [0.608, 0.761] |
| C2 grid best (boosting, clinical + timing) | 0.755 [0.670, 0.831] | 0.739 [0.659, 0.810] |
| C3 baseline ridge | 0.729 | 0.722 [0.641, 0.801] |
| C3 baseline boosting | 0.731 | 0.724 [0.639, 0.803] |
| **C3 nested radiomics** | 0.738 (shared run) / 0.740 (this run) | **0.719 [0.645, 0.791]** |
| **C3 nested ΔAUC vs baseline ridge** | +0.009 [−0.027, +0.040] / +0.011 [−0.023, +0.042] | **−0.002 [−0.030, +0.024]** |
| C3 configs with ΔAUC CI > 0 / < 0 (of 70 + 2) | 0 / 5 | 0 / 16 |
| C3 best post-hoc config (legacy decor20 concat) | 0.744, Δ +0.015 | 0.734, Δ +0.012 [−0.042, +0.067] |

Sources: `out-eval/results/{c1/c1_results.csv, c2/grade4/grid.csv, c3/grade4/results.csv}`; before = shared
`outputs/results/` (same inputs). C1 conclusions do not change (ΔAUC vs naive moves ≤ 0.003). The audit's "C3 grade-4
nested 0.687 vs 0.671" refers to the pre-treatment-fix results (`outputs/results_pre_fix_2026-10-11/`). On current
inputs the gap is 0.740 vs 0.719. The nested radiomics ΔAUC changes sign: **radiomics adds nothing; the point estimate is
now slightly negative.** The 16 configs with a CI below 0 are mostly stacked v2 variants whose ΔAUC is −0.003 to −0.01
with very narrow CIs. These are paired differences over 5 repeats, so they are precise; they are negligible, not harmful.

## 2. External LUMIERE: one estimator for every arm (major)

Before, "Raw" was a pooled AUC while the adapted arms were per-fold means. Adapted arms were also reported pooled, which
means pooling OOF predictions that were recalibrated differently in each fold. That gave recalibrated ridge a pooled AUC
of 0.414 and a slope of −0.96, which is an artefact. Now every arm, locked included, is scored on the **same 5×5
patient-grouped LUMIERE folds** (`lumiere_fold_ids`). Each held-out fold gets an IPCW AUC: the fold's own cases and
controls, with censoring weights from the whole LUMIERE cohort (outcome-only nuisance). Brier, O/E (fold KM risk / mean
prediction) and the IPCW calibration slope are also computed per fold, then all are averaged over the 25 folds. CIs come
from a patient-cluster bootstrap in which patients keep their folds (`fold_mean_metrics`, `fold_mean_bootstrap`;
ΔAUC paired vs locked). Locked is also reported pooled (`*_pooled`). Recalibration is now an unpenalised logistic on the
logit (`penalty=None`). The slope is floored at 0.05 so that it can never reverse the ranking. No fold needed the floor in the
clinical + timing + volumes rows; up to 7 of 25 folds did in the weak feature sets (volumes, clinical), see
`recal_slope_floored`. `mu_cv` now uses `outputs/data/folds.csv` and the mean-over-repeats estimator (also given
per fold).

Clinical + timing + volumes, same inputs, old code vs new code (`out-eval-old/` vs `out-eval/results/external_lumiere/results.csv`):

| Train · learner | Arm | Old: pooled AUC (O/E, slope) | Old: per-fold AUC | **New: per-fold IPCW AUC [95% CI]** | New: O/E, slope (per fold) |
|---|---|---|---|---|---|
| grade 4 · boosting | MU CV | 0.714 | — | 0.706 [0.624, 0.774] (pooled, mean over repeats) | 1.00, 1.18 |
| | locked | 0.679 (1.22, 1.04) | 0.693 | **0.693 [0.590, 0.797]**; pooled 0.679 [0.559, 0.789] | 1.29, 0.98 |
| | recalibrated | 0.639 (0.96, 0.73) | 0.693 | 0.693 (= locked; Δ 0) | 1.07, 0.88 |
| | finetune pooled | 0.657 | 0.701 | 0.701, Δ +0.008 [−0.040, +0.055] | 1.13, 0.89 |
| | LUMIERE only | 0.582 | 0.624 | 0.624, Δ −0.069 [−0.158, +0.031] | 1.03, 0.87 |
| grade 4 · ridge | MU CV | 0.699 | — | 0.664 [0.582, 0.740] | 0.99, 1.01 |
| | locked | 0.638 (1.34, 0.85) | 0.642 | 0.643 [0.569, 0.756]; pooled 0.638 | 1.41, 0.58 |
| | recalibrated | **0.550 (0.96, 0.47)** | 0.642 | 0.643 (= locked) | 1.06, 0.61 |
| | finetune shrink | 0.602 | 0.649 | 0.649, Δ +0.007 [−0.059, +0.084] | 1.19, 1.07 |
| all gliomas · boosting | locked | 0.682 (1.60, 0.91) | 0.679 | 0.679 [0.589, 0.780]; pooled 0.682 [0.547, 0.807] | 1.70, 1.21 |
| | recalibrated | 0.637 (0.95, 0.62) | 0.679 | 0.679 | 1.06, 1.39 |

Slope = per-fold median (per-fold means are unstable with about 5 cases per fold; both are in the CSV). Per-fold IPCW AUCs
equal the old per-fold verified-label AUCs to 3 decimals: only 8 LUMIERE scans are censored. Reading: recalibration
leaves discrimination unchanged and brings O/E from 1.29–1.85 (locked) to 1.06–1.07. **The old "recalibration costs
0.04–0.12 AUC" was purely an artefact of the pooled estimator.** No adaptation arm beats locked (all Δ CIs span 0), and
LUMIERE-only is the worst.

Shipped PRISM report radiomics model (`legacy/shipped_on_lumiere.py adapt()`, 118 scans,
`out-eval/results/external_lumiere/shipped_model_adaptation.csv`): raw per-fold 0.617 [0.526, 0.724], pooled 0.613
[0.500, 0.729]. Recalibrated 0.617 (O/E 1.33 → 1.13 per fold). Fine-tuned (shrink) 0.602, Δ −0.016. The script now runs
`adapt()` after `main()` (before, `adapt()` was defined after the `__main__` block and never ran).

## 3. C2 permutation control (major)

Before: 5 permutations that shuffled outcome rows across scans. This breaks the within-patient outcome correlation, so
the null is too narrow, and 5 draws cannot give a p-value. Now `permute_patients` moves each patient's whole
outcome block (event, time, status, all labels, in visit order) to another patient with the **same number of scans**.
Features, scan order and folds stay fixed. All grade-4 scan-count strata (1–6 scans) have ≥ 2 patients, so every patient
can move. The full nested pipeline is re-run for each of **100 permutations**, and empirical p = (1 + #{perm ≥ obs}) / (1 + 100).

Grade 4 (`out-eval/results/c2/grade4/{nested.csv, permutation.csv}`): observed nested (ridge + boosting) 0.663;
permutation null mean 0.530, SD 0.044, 95th percentile 0.604, max 0.647; **p = 0.010** (0 of 100 ≥ observed, the
smallest p 100 permutations can give). Before: 5 scan-level shuffles, 0.42–0.56, no p-value. The null is centred above
0.5: selecting the best of 126 configurations on inner CV is optimistic even without signal. This is why the
permutation control is needed.

## 4. C2 nested search includes boosting (major)

The nested selection now searches all 126 (learner, combination) candidates (`--nested-learners ridge,gbm`, default;
`ridge` restores the old 63-candidate search). `nested_choices.csv` records `chosen_learner`, `chosen`, `fold`,
`inner_auc`. Grade 4: **0.663 [0.595, 0.733]** (repeat-averaged 0.704) vs ridge-only 0.659 before (same
mean-over-repeats estimator, shared `outputs/results/c2/grade4/nested.csv`). Boosting was chosen in 15 of 25 outer
folds, clinical + timing being the most frequent (6). The honest search estimate (0.663) stays well below the post-hoc
grid best (0.739). Nested calibration slope 0.40: the selected boosting models are overconfident.
Cost: about 35 s CPU per outer fold, so 100 permutations take about 25 CPU-hours per population (50 min on 30 workers).

## 5. Head-to-head, split variance and deep stages (major)

`prism head2head [--drop-mgmt-flag]` (`prism/analyses/head_to_head.py`) replaces the scratch script in
`outputs/results/c3/prism_report_split/` (no "before" mode, no scratch-path import). It adds a patient-cluster bootstrap
CI over the 30 test patients and a paired Δ vs baseline ridge. It reproduces `head_to_head_after.csv` and
`head_to_head_masking_only.csv` exactly (naive / IPCW: PRISM report model 0.802 / 0.811 [0.694, 0.919]; baseline ridge
0.880 / 0.860 [0.730, 0.943]; boosting 0.869 / 0.855; + legacy texture 0.871 / 0.852; + corrected compartments 0.886 /
0.870, Δ +0.010 [−0.017, +0.054]). Also registered: `prism splitvar` (`prism.analyses.split_variance`, logic
unchanged) and `prism deep` (`prism.analyses.deep_features`). Scripts: `07_head_to_head.sh`, `08_split_variance.sh`,
`09_deep_features.sh` (CPU analysis only; skips cleanly without `outputs/features/deep_*.parquet`; the GPU extraction
stays manual). `run_all.sh` has the new steps and a `--to STEP` option.

## 6. Minor

- **C3 missing ROIs**: `ImputeWithFlags` imputes with the median and adds one 0/1 flag per distinct missingness pattern
  in training. Grade 4 gives 3 flags (no ET 20/253, no NETC 142/253, no rim 33/253) instead of silently imputing.
- **C3 L1 selector**: `L1Select` keeps only nonzero coefficients (|coef| > 1e-10, at most 30). Before, `threshold=-inf`
  padded to 30 with zero-coefficient features. It now keeps 17–22 on full training folds. If none survive, the block is a
  single zero column. The plain `threshold=1e-10` crashed on a fold where nothing survived.
- **nested_choices.csv** (C3) now has `repeat, fold, chosen, inner_auc`.
- **Warnings**: workers no longer call `warnings.filterwarnings("ignore")`. `counted_warnings` silences only the known
  noisy ones (constant features in `f_classif`; columns without observed values) and logs a per-job count of everything
  else to stderr. `f_classif`'s divide warning is silenced at its call site (`c3_radiomics.f_classif_quiet`,
  `np.errstate`) and the SWIG deprecation at the SimpleITK import (`features/radiomics.py`; the earlier filter in the
  worker wrapper never applied because the warning fires at import time). Validation runs logged no convergence or other warnings.
- **mu_cv** in external uses `folds.csv`. **ΔAUC** everywhere is the point estimate with a bootstrap CI.

## 7. Scripts

`scripts/common.sh` runs every stage as `uv run --frozen --no-sync --project $REPO python -m prism …` in a subshell
`cd`'d to the repo root, with `PYTHONPATH=$REPO`. It no longer depends on the `prism` console script being installed
in the venv. Tested from an unrelated cwd.

## Reproduce

```
uv run --frozen --no-sync python -m unittest discover -s tests
uv run --frozen --no-sync python -m prism c1
uv run --frozen --no-sync python -m prism c2 --population grade4 --workers 30     # ~50 min (100 permutations)
uv run --frozen --no-sync python -m prism c3 --population grade4 --workers 10    # ~6 min
uv run --frozen --no-sync python -m prism external --workers 8                   # < 1 min
uv run --frozen --no-sync python -m prism head2head && uv run --frozen --no-sync python -m prism head2head --drop-mgmt-flag
```

Not run here: c2/c3 all_glioma, splitvar, deep. Numbers in the other docs/results files still use the old estimator.
