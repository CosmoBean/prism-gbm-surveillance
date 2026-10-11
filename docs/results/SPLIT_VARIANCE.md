# Split variance: the PRISM report split among 500 splits of the same design

Plan item 3.5; follows An et al. 2021 (*PLOS ONE*, doi:10.1371/journal.pone.0256152).

## Method
- **Design.** The PRISM report's own split search (`legacy/radiomics/.../train.py` `choose_test_patients`). For each seed it makes
  20 000 random draws of 30 patients and keeps the draw closest to 96 test scans and 53 positives. Seed 62 gives back the PRISM report split
  exactly (same 30 patients, 84 scans, 22 positives). Seeds 0–499 gave 500 distinct splits (test scans 82–94, mean 86.1; positives 10–33). The splits are not stratified, and neither was the original. The search prefers patients with many scans, so the test sets overlap a lot: all 157 patients appear, and the most frequent one is in 71% of splits.
- **Cohort, label, features.** These are the PRISM report's: 315 scans / 157 patients, label = progression within 120 d, pre-progression scans only, scans before late treatment, T1c + FLAIR legacy radiomics + `hybrid_basic` clinical codes. This label equals our `naive_label_120` on all 314 scans the two cohorts share.
- **Models** (trained on each split's training patients):
  - `prism_fixed`: the shipped 48 columns, preprocessing thresholds and C, refitted. The columns were chosen on the PRISM report split's training patients, and most of the other splits' test patients are among them. **Leaky, so it is an upper bound.**
  - `prism_reselect`: the same pipeline, but the L1 + permutation consensus ranking is redone on each split (5 folds and 5 repeats instead of 10 and 100), then top 48 and the shipped C. Optuna is not re-run. **This is the honest version.** On seed 62 it gives 0.800, against 0.802 for the shipped model.
  - `baseline`: clinical + timing + treatment ridge. `baseline_rad`: baseline + legacy radiomics top-10. Both use the C3 code (`c3.fit_predict`).
- **Metric.** Test AUC on the MU-cohort scans of the 30 test patients, once with the naive label and once as IPCW AUC(120 d).

## Results (500 splits)

| Model | Naive AUC mean ± SD | 2.5–97.5% | On PRISM report split (pctile) | Splits ≥ 0.802 | Beats baseline | Mean Δ vs baseline |
|---|---|---|---|---|---|---|
| PRISM pipeline, re-selected per split | 0.719 ± 0.056 | 0.606–0.816 | 0.800 (92nd) | 6.2% | 11% | −0.081 |
| PRISM model, shipped features (leaky) | 0.818 ± 0.044 | 0.727–0.893 | 0.802 (34th) | 66% | 60% | +0.018 |
| Clinical + timing + treatment ridge | 0.800 ± 0.054 | 0.690–0.907 | 0.880 (93rd) | 50% | – | – |
| Baseline + legacy radiomics | 0.814 ± 0.048 | 0.712–0.902 | 0.871 (91st) | 63% | 64% | +0.014 |

With IPCW AUC(120) the pattern is the same: re-selected 0.715 ± 0.057 (PRISM report split at the 96th percentile), baseline 0.781 ± 0.057, baseline + radiomics 0.797 ± 0.050.

Figure: `outputs/results/analyses/split_variance/split_variance.png`.
Data: `per_split_auc.csv`, `summary.csv` and `run_info.json` in the same folder.

## Interpretation
- **The 0.80 is an upper-tail draw.** When the PRISM report pipeline selects its own features on each split, its AUC is 0.72 on average, and 0.80 sits at the 94th percentile. Only 6% of splits of the same design reach the reported value. The PRISM report split is also favourable for our models: the baseline is at its 93rd percentile there.
- **Keeping the shipped features does not rescue it.** The shipped 48 columns average 0.82 over other splits, but this is leakage: those columns were picked using labels of patients who are test patients in most other splits. The gap between the honest and leaky versions is 0.099 ± 0.040 per split.
- **Radiomics against the baseline.** The honest radiomics pipeline loses to the clinical + timing + treatment baseline in 89% of splits (mean −0.08). Adding legacy radiomics to the baseline gives +0.014 on average and helps in 64% of splits. Both numbers are within the noise: one 30-patient split has an SD of about 0.05.
- **Absolute levels are higher than in repeated CV** (baseline 0.80 here against 0.72–0.74 in C3). This design favours patients with many scans and scores with the naive label. Compare models within this analysis, not with the C3 tables.

## Reproducibility
Command: `uv run --frozen --no-sync python -m prism.analyses.split_variance --workers 22 --n-splits 500` (15.4 min on 22 processes).
Feature version: git HEAD `7112486`, with `prism/features/tabular.py` **modified** while this ran: the as-of-scan treatment masking was in progress, and the diff SHA-1 is `e797bd09…`; the full diff is in `run_info.json`. This may explain why the baseline gives 0.880 on the PRISM report split here against 0.870 in C3_radiomics.md. Once the treatment-feature change is final, re-run so that `baseline` and `baseline_rad` use it. The PRISM report models do not depend on `tabular.py`.
