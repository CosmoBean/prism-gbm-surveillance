# Split variance: the PRISM report split among 500 splits of the same design

Plan item 3.5; follows An et al. 2021 (*PLOS ONE*, doi:10.1371/journal.pone.0256152).

**Final numbers** from `outputs/results/analyses/split_variance/{summary.csv, per_split_auc.csv, run_info.json}` (final run,
git HEAD `bea5b7c`, `tabular.py` clean, 14.0 min). The figure and `summary.csv` were re-plotted on 2026-10-11 18:50 from the
same `per_split_auc.csv`, and `summary.csv` is unchanged. Earlier versions of this file used a run with an in-progress
`tabular.py`. The PRISM report rows barely moved, and the baseline rows now use the final as-of-scan treatment features.
**Caveat:** the per-split fits predate the radiomics clipping fix ([FIX_RADIOMICS_CLIP.md](FIX_RADIOMICS_CLIP.md)). The
`baseline_rad` row (legacy top-10, concatenated, via `c3.fit_predict`) was therefore fitted without clipping. The PRISM
report and baseline rows do not use `c3.selector` and are unaffected.

## Method
- **Design.** The PRISM report's own split search (`legacy/radiomics/.../train.py` `choose_test_patients`). For each seed it makes
  20 000 random draws of 30 patients and keeps the draw closest to 96 test scans and 53 positives. Seed 62 gives back the PRISM report split
  exactly (same 30 patients, 84 scans, 22 positives). Seeds 0–499 gave 500 distinct splits (test scans 82–94, mean 86.1; positives 10–33). The splits are not stratified, and neither was the original. The search prefers patients with many scans, so the test sets overlap a lot: all 157 patients appear, and the most frequent one is in 71% of splits.
- **Cohort, label, features.** These are the PRISM report's: 315 scans / 157 patients, label = progression within 120 d, pre-progression scans only, scans before late treatment, T1c + FLAIR legacy radiomics + `hybrid_basic` clinical codes. This label equals our `naive_label_120` on all 314 scans the two cohorts share. Test AUCs are computed on the test patients' scans in our post-fix MU cohort (79–92 scans per split; 82 on seed 62).
- **Models** (trained on each split's training patients):
  - `prism_reselect`: the PRISM report pipeline with the L1 + permutation consensus ranking redone on each split (5 folds and 5
    repeats instead of the shipped 10 and 100), then top 48 and the shipped C. Optuna is not re-run. **This is the honest
    version.** On seed 62 it gives 0.801, against 0.802 for the shipped model.
  - `prism_fixed`: the shipped 48 columns, preprocessing thresholds and C, refitted. **Optimistic (features selected using
    other splits' test patients):** the columns were chosen on the PRISM report split's training patients, and most test
    patients of the other splits are among them. Treat it as an upper bound.
  - `baseline`: clinical + timing + treatment ridge. `baseline_rad`: baseline + legacy radiomics top-10. Both use the C3 code (`c3.fit_predict`).
- **Metric.** Test AUC on the MU-cohort scans of the 30 test patients, with the naive label (500 splits) and as IPCW AUC(120 d).
  IPCW AUC is undefined on 25 splits, so the IPCW column has **475 splits**.
- **Rank of the PRISM report split.** Throughout, "rank" is the share of splits whose AUC is strictly lower than **that model's
  own AUC on the PRISM report split (seed 62), re-run in this analysis** (`pct_rank_prism_split_value` in `summary.csv`). It is not
  the rank of the reported 0.802. For `prism_reselect` the two are almost the same value (0.801 vs 0.802).

## Results

| Model | Naive AUC mean ± SD (n = 500) | 2.5–97.5% | Seed 62 re-run (rank) | Splits ≥ 0.802 | Beats baseline | Mean Δ vs baseline |
|---|---|---|---|---|---|---|
| PRISM report pipeline, re-selected per split | 0.720 ± 0.055 | 0.610–0.819 | 0.801 (92%) | 7.2% | 12% | −0.081 |
| PRISM report model, shipped features (optimistic) | 0.815 ± 0.044 | 0.726–0.887 | 0.802 (38%) | 62% | 58% | +0.014 |
| Clinical + timing + treatment ridge | 0.801 ± 0.052 | 0.694–0.895 | 0.871 (91%) | 50% | – | – |
| Baseline + legacy radiomics | 0.801 ± 0.053 | 0.679–0.892 | 0.867 (90%) | 52% | 54% | −0.000 |

| Model | IPCW AUC(120) mean ± SD (n = 475) | 2.5–97.5% | Seed 62 re-run (rank) | Beats baseline | Mean Δ vs baseline |
|---|---|---|---|---|---|
| PRISM report pipeline, re-selected per split | 0.727 ± 0.058 | 0.602–0.832 | 0.816 (94%) | 25% | −0.042 |
| PRISM report model, shipped features (optimistic) | 0.825 ± 0.045 | 0.737–0.901 | 0.817 (40%) | 81% | +0.055 |
| Clinical + timing + treatment ridge | 0.769 ± 0.056 | 0.654–0.876 | 0.851 (92%) | – | – |
| Baseline + legacy radiomics | 0.776 ± 0.058 | 0.646–0.875 | 0.847 (91%) | 60% | +0.006 |

Figure: `outputs/results/analyses/split_variance/split_variance.png`: histograms of per-split AUC per model, n per panel,
x-axis from 0.5, triangles + dotted lines at each model's seed-62 re-run value with its rank, black line at the reported 0.802.
Data: `per_split_auc.csv`, `summary.csv` and `run_info.json` in the same folder.

## Sensitivity checks (verifier, `scratchpad/verify_splitvar/`)

These checks were run by the verifier on the earlier (pre-final) per-split table and were not repeated on the final run.
The PRISM report pipeline does not depend on `tabular.py`; the baseline numbers in check 2 are from the earlier table.

**1. Full-cost selection and Optuna (15 splits + seed 62; `fullsel.csv`, `fullsel.py`).** On the PRISM report split and the first
15 other design splits, the per-split ranking was redone with the shipped settings (10 folds × 100 permutation repeats, "full")
and, in addition, the shipped Optuna search (logreg, subsets 128/64/48/32, 200 trials, 5-fold CV) was re-run on the training
patients. AUC here is on the legacy (PRISM report) case table and label, so seed 62 "cheap" = 0.802 rather than 0.800.

| Selection per split | Seed 62 | 15 other splits: mean ± SD (min–max) | Overlap with shipped 48 columns (other splits) |
|---|---|---|---|
| Cheap ranking (5 × 5), top 48, shipped C (= `prism_reselect`) | 0.802 | 0.726 ± 0.057 (0.607–0.814) | 14.3 / 48 |
| Full ranking (10 × 100), top 48, shipped C | 0.810 | 0.718 ± 0.054 (0.615–0.800) | 14.0 / 48 |
| Full ranking + Optuna (k, C, thresholds) | 0.762 | 0.654 ± 0.054 (0.530–0.747) | – |

- The cheap ranking does not bias the result: cheap minus full = +0.008 ± 0.033 per split (r = 0.83). The full ranking on seed 62
  is higher than on all 15 other splits.
- Re-running Optuna makes things **worse**, not better: −0.064 ± 0.055 against full ranking with the shipped C. Its inner-CV
  objective averages 0.865 against a test AUC of 0.654 (optimism ≈ 0.21). Optuna picks k = 128 in 5/15 splits.
  On seed 62 the re-run Optuna gives 0.762, not 0.802, so the shipped hyperparameters were not reproduced by the search either.
- So the 500-split `prism_reselect` distribution is, if anything, generous to the PRISM report pipeline.

**2. Design splits vs fully random 30-patient splits (baseline ridge; `randsplit.csv`, `randsplit.py`).** 300 random draws of
30 patients (seed 0) against the 500 design splits:

| Splits | n | Test scans mean (range) | Positives mean | Baseline AUC mean ± SD | 2.5–97.5% | ≥ 0.802 |
|---|---|---|---|---|---|---|
| PRISM report design | 500 | 85.5 (81–93) | 21.3 | 0.800 ± 0.054 | 0.690–0.907 | 49.6% |
| Fully random | 300 | 59.9 (45–79) | 18.5 | 0.787 ± 0.069 | 0.643–0.910 | 45.3% |

- The design picks patients with many scans (85.5 vs 59.9 test scans) and its test sets overlap heavily: all 157 patients appear,
  10 appear in more than half the splits, and the most frequent in 71%. This narrows the spread (SD 0.054 vs 0.069) and raises
  the mean a little (+0.013). Spread under the design is therefore an underestimate of what a fresh 30-patient split would show.
- With the tabular features at verification time, the baseline design-split AUCs equal the stored ones exactly (r = 1.0,
  mean difference 0.000), so the `tabular.py` caveat below does not change the baseline numbers in this run.

## Interpretation
- **The 0.80 is an upper-tail draw.** When the PRISM report pipeline selects its own features on each split, its AUC is 0.72 on
  average, and its seed-62 re-run (0.801) ranks above 92% of splits (94% with IPCW AUC). Only 7% of splits reach the reported
  0.802. The PRISM report split is favourable for every model: the baseline ranks 91% there (92% IPCW).
- **Keeping the shipped features does not rescue it.** The shipped 48 columns average 0.82 over other splits, but this is
  optimistic: the features were selected using other splits' test patients. The gap between the honest and optimistic versions
  is 0.095 ± 0.040 per split (`per_split_auc.csv`).
- **Radiomics against the baseline.** The honest radiomics pipeline loses to the clinical + timing + treatment baseline in 88%
  of splits (mean −0.08). Adding legacy radiomics to the baseline gives −0.000 on average (IPCW +0.006) and helps in 54% of
  splits (60% IPCW). Both are within the noise: one 30-patient split has an SD of about 0.05.
- **Absolute levels are higher than in repeated CV** (baseline 0.80 here against 0.720 for all gliomas in C3). This design favours patients
  with many scans and scores with the naive label. Compare models within this analysis, not with the C3 tables.

## Reproducibility
Command: `uv run --frozen --no-sync python -m prism.analyses.split_variance --workers 22 --n-splits 500` (final run: 14.0 min on 22 processes).
Figure and `summary.csv` only, from the existing `per_split_auc.csv` (no refit): `python -m prism.analyses.split_variance --replot`.
Feature version (final run): git HEAD `bea5b7c`, `tabular.py` unmodified (`run_info.json`: `tabular_py_dirty: false`), so
`baseline` and `baseline_rad` use the final as-of-scan treatment features. The baseline's seed-62 value (naive 0.871, IPCW
0.851) equals the head-to-head stage (`outputs/results/c3/prism_report_split/head_to_head.csv`). The PRISM report models
do not depend on `tabular.py`.

## EXPLORATORY (2026-10-26): image-only models on the first split and over 500 splits

Post hoc, not in the plan. Question: how does a model that sees only the images do on the PRISM report split and over the
500 design splits, beside the PRISM report model, the baseline ridge and clinical only? Script:
`scripts/exploratory_split_variance_images.py`, outputs in `outputs/results/analyses/split_variance_images/`
(`per_split_auc.csv`, `summary.csv`, `seed62_single_split.csv`, `run_info.json`); existing outputs untouched.

- **Same design as above.** Same MU all-glioma cohort (`c3.load("all_glioma")`, 308 scans), same test patients per split
  (read from `split_variance/per_split_auc.csv`), training on `label_120`, scoring with the naive 120-d label (500 splits)
  and IPCW AUC(120) (475 splits). Same pipeline as `baseline`: `c3.fit_predict`, ridge.
- **Arms.** I_scan = volumes + morphology / relative intensity at the scan (19 inputs). I_pure = I_scan + log volume ratios
  to the previous scan (0 if none) + ET / lesion log ratio to the smallest volume over the whole history (27 inputs); no
  days, no flags (as in `exploratory_pure_imaging_forward_lumiere.py`). Clinical only (age, sex, IDH, MGMT) was also run
  over the 500 splits; before this it had only the single-split row.
- **Checks.** The refitted baseline equals the stored per-split AUCs (max |Δ| 1e-16). On seed 62, baseline and clinical
  reproduce table 2 exactly (0.851 [0.735, 0.947]; 0.782 [0.638, 0.897]).
- Seed-62 CIs: patient-cluster bootstrap over the 29 test patients (82 scans, 22 positives), 1000 draws, as in table 2.

| Model | Seed 62: naive | Seed 62: IPCW [95% CI] | Seed 62: Δ IPCW vs baseline [95% CI] | 500 splits: naive mean ± SD (2.5–97.5%) | rank of seed 62 | 475 splits: IPCW mean ± SD (2.5–97.5%) | rank of seed 62 | beats baseline (naive / IPCW) |
|---|---|---|---|---|---|---|---|---|
| PRISM report model (seed 62: shipped; splits: re-selected per split) | 0.802 | 0.817 [0.690, 0.920] | −0.034 [−0.186, +0.109] | 0.720 ± 0.055 (0.610–0.819) | 92% | 0.727 ± 0.058 (0.602–0.832) | 94% | 12% / 25% |
| Baseline ridge | 0.871 | 0.851 [0.735, 0.947] | – | 0.801 ± 0.052 (0.694–0.895) | 91% | 0.769 ± 0.056 (0.654–0.876) | 92% | – |
| Clinical only (ridge) | 0.791 | 0.782 [0.638, 0.897] | −0.069 [−0.215, +0.058] | 0.647 ± 0.061 (0.522–0.754) | 99% | 0.644 ± 0.061 (0.513–0.757) | 99% | 1% / 3% |
| **I_scan** (images, scan alone) | 0.793 | 0.787 [0.671, 0.878] | −0.064 [−0.205, +0.059] | 0.716 ± 0.056 (0.601–0.814) | 92% | 0.727 ± 0.061 (0.600–0.842) | 83% | 12% / 30% |
| **I_pure** (images + change) | 0.783 | 0.786 [0.675, 0.892] | −0.065 [−0.197, +0.077] | 0.718 ± 0.056 (0.605–0.819) | 86% | 0.730 ± 0.061 (0.612–0.839) | 81% | 12% / 32% |

Rank = share of splits with a strictly lower AUC than the model's own seed-62 value. The PRISM report rows' seed-62
naive / IPCW are the shipped model (0.802 / 0.817); its re-selected re-run on seed 62 is 0.801 / 0.816.

Reading:
- **Images alone do as well as the PRISM report pipeline.** Over the 500 splits, I_scan and I_pure (0.72 naive, 0.73
  IPCW) match the re-selected PRISM report pipeline (0.720 / 0.727), with the same spread. On seed 62 they give 0.79
  (IPCW 0.79), within 0.03 of the shipped 0.80 / 0.82.
- **The baseline stays ahead.** Images lose to the clinical + timing + treatment ridge in 88% of splits (naive; 68–70%
  IPCW), by about 0.08 naive and 0.04 IPCW on average. On seed 62 the gap is −0.06 with a CI that crosses 0.
- **Seed 62 is favourable for every model,** images included (81–92%), and most of all for clinical only (99%): its 0.79
  on seed 62 is far above its usual 0.65.
- The change inputs add almost nothing here: I_pure − I_scan is +0.003 ± 0.017 naive (+0.003 ± 0.019 IPCW) per split.
