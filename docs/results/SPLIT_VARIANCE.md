# Split variance: the PRISM report split among 500 splits of the same design

Plan item 3.5; follows An et al. 2021 (*PLOS ONE*, doi:10.1371/journal.pone.0256152).

## Method
- **Design.** The PRISM report's own split search (`legacy/radiomics/.../train.py` `choose_test_patients`). For each seed it makes
  20 000 random draws of 30 patients and keeps the draw closest to 96 test scans and 53 positives. Seed 62 gives back the PRISM report split
  exactly (same 30 patients, 84 scans, 22 positives). Seeds 0–499 gave 500 distinct splits (test scans 82–94, mean 86.1; positives 10–33). The splits are not stratified, and neither was the original. The search prefers patients with many scans, so the test sets overlap a lot: all 157 patients appear, and the most frequent one is in 71% of splits.
- **Cohort, label, features.** These are the PRISM report's: 315 scans / 157 patients, label = progression within 120 d, pre-progression scans only, scans before late treatment, T1c + FLAIR legacy radiomics + `hybrid_basic` clinical codes. This label equals our `naive_label_120` on all 314 scans the two cohorts share.
- **Models** (trained on each split's training patients):
  - `prism_reselect`: the PRISM report pipeline with the L1 + permutation consensus ranking redone on each split (5 folds and 5
    repeats instead of the shipped 10 and 100), then top 48 and the shipped C. Optuna is not re-run. **This is the honest
    version.** On seed 62 it gives 0.800, against 0.802 for the shipped model.
  - `prism_fixed`: the shipped 48 columns, preprocessing thresholds and C, refitted. **Optimistic (features selected using
    other splits' test patients):** the columns were chosen on the PRISM report split's training patients, and most test
    patients of the other splits are among them. Treat it as an upper bound.
  - `baseline`: clinical + timing + treatment ridge. `baseline_rad`: baseline + legacy radiomics top-10. Both use the C3 code (`c3.fit_predict`).
- **Metric.** Test AUC on the MU-cohort scans of the 30 test patients, with the naive label (500 splits) and as IPCW AUC(120 d).
  IPCW AUC is undefined on 22 splits, so the IPCW column has **478 splits**.
- **Rank of the PRISM report split.** Throughout, "rank" is the share of splits whose AUC is strictly lower than **that model's
  own AUC on the PRISM report split (seed 62), re-run in this analysis** (`pct_rank_prism_split_value` in `summary.csv`). It is not
  the rank of the reported 0.802. For `prism_reselect` the two are almost the same value (0.800 vs 0.802).

## Results

| Model | Naive AUC mean ± SD (n = 500) | 2.5–97.5% | Seed 62 re-run (rank) | Splits ≥ 0.802 | Beats baseline | Mean Δ vs baseline |
|---|---|---|---|---|---|---|
| PRISM report pipeline, re-selected per split | 0.719 ± 0.056 | 0.606–0.816 | 0.800 (92%) | 6.2% | 11% | −0.081 |
| PRISM report model, shipped features (optimistic) | 0.818 ± 0.044 | 0.727–0.893 | 0.802 (34%) | 66% | 60% | +0.018 |
| Clinical + timing + treatment ridge | 0.800 ± 0.054 | 0.690–0.907 | 0.880 (93%) | 50% | – | – |
| Baseline + legacy radiomics | 0.814 ± 0.048 | 0.712–0.902 | 0.871 (91%) | 63% | 64% | +0.014 |

| Model | IPCW AUC(120) mean ± SD (n = 478) | 2.5–97.5% | Seed 62 re-run (rank) | Beats baseline | Mean Δ vs baseline |
|---|---|---|---|---|---|
| PRISM report pipeline, re-selected per split | 0.715 ± 0.057 | 0.591–0.815 | 0.811 (96%) | 18% | −0.066 |
| PRISM report model, shipped features (optimistic) | 0.818 ± 0.045 | 0.723–0.894 | 0.811 (41%) | 72% | +0.037 |
| Clinical + timing + treatment ridge | 0.781 ± 0.057 | 0.673–0.896 | 0.860 (91%) | – | – |
| Baseline + legacy radiomics | 0.797 ± 0.050 | 0.694–0.893 | 0.852 (87%) | 65% | +0.016 |

Figure: `outputs/results/analyses/split_variance/split_variance.png`: histograms of per-split AUC per model, n per panel,
x-axis from 0.5, triangles + dotted lines at each model's seed-62 re-run value with its rank, black line at the reported 0.802.
Data: `per_split_auc.csv`, `summary.csv` and `run_info.json` in the same folder.

## Sensitivity checks (verifier, `scratchpad/verify_splitvar/`)

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
  average, and its seed-62 re-run (0.800) ranks above 92% of splits (96% with IPCW AUC). Only 6% of splits reach the reported
  0.802. The PRISM report split is favourable for every model: the baseline ranks 93% there.
- **Keeping the shipped features does not rescue it.** The shipped 48 columns average 0.82 over other splits, but this is
  optimistic: the features were selected using other splits' test patients. The gap between the honest and optimistic versions
  is 0.099 ± 0.040 per split.
- **Radiomics against the baseline.** The honest radiomics pipeline loses to the clinical + timing + treatment baseline in 89%
  of splits (mean −0.08). Adding legacy radiomics to the baseline gives +0.014 on average and helps in 64% of splits. Both are
  within the noise: one 30-patient split has an SD of about 0.05.
- **Absolute levels are higher than in repeated CV** (baseline 0.80 here against 0.72–0.74 in C3). This design favours patients
  with many scans and scores with the naive label. Compare models within this analysis, not with the C3 tables.

## Reproducibility
Command: `uv run --frozen --no-sync python -m prism.analyses.split_variance --workers 22 --n-splits 500` (15.4 min on 22 processes).
Figure and `summary.csv` only, from the existing `per_split_auc.csv` (no refit): `python -m prism.analyses.split_variance --replot`.
Feature version: git HEAD `7112486`, with `prism/features/tabular.py` **modified** while this ran: the as-of-scan treatment masking was in progress, and the diff SHA-1 is `e797bd09…`; the full diff is in `run_info.json`. This may explain why the baseline gives 0.880 on the PRISM report split here against 0.870 in C3_radiomics.md. Once the treatment-feature change is final, re-run so that `baseline` and `baseline_rad` use it. The PRISM report models do not depend on `tabular.py`.
