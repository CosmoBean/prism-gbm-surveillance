| Model | Single split: naive AUC | Single split: IPCW AUC [95% CI] | Single split: ΔAUC vs baseline ridge [95% CI] | 500 design splits: naive mean ± SD (2.5–97.5%) | 500 design splits: IPCW mean ± SD | 5×5 CV all gliomas: IPCW AUC [95% CI] | 5×5 CV grade 4: IPCW AUC [95% CI] |
|---|---|---|---|---|---|---|---|
| PRISM report model | 0.802 | 0.817 [0.690, 0.920] | -0.034 [-0.186, +0.109] | 0.720 ± 0.055 (0.610–0.819) (pipeline re-selected per split) | 0.727 ± 0.058 (pipeline re-selected per split) | n/a (fixed model) | n/a (fixed model) |
| Baseline ridge | 0.871 | 0.851 [0.735, 0.947] | – | 0.801 ± 0.052 (0.694–0.895) | 0.769 ± 0.056 | 0.720 [0.638, 0.792] | 0.698 [0.615, 0.774] |
| Baseline GBM | 0.844 | 0.824 [0.690, 0.916] | -0.027 [-0.127, +0.062] | not run | not run | 0.718 [0.642, 0.792] | 0.687 [0.601, 0.768] |
| Baseline + legacy radiomics | 0.862 | 0.845 [0.746, 0.936] | -0.006 [-0.081, +0.090] | 0.799 ± 0.053 (0.674–0.892) | 0.774 ± 0.058 | 0.743 [0.678, 0.803] | 0.703 [0.627, 0.774] |
| Clinical only (ridge) | 0.791 | 0.782 [0.638, 0.897] | -0.069 [-0.215, +0.058] | not run | not run | 0.619 [0.540, 0.696] | 0.585 [0.496, 0.666] |
| *History rows (added 2026-10-15; not comparable with the rows above — earlier cohort and inputs):* | | | | | | | |
| PRISM report model, pre-label-fix test set (30 pts / 84 scans) | 0.802 | 0.811 [0.694, 0.919] | not computed | not run | not run | n/a (fixed model) | n/a (fixed model) |
| Baseline ridge, **pre-fix (leaky)**: future RT dates in treatment/timing features (30 / 84) | 0.870 | 0.844 (no CI computed) | not computed | not run | not run | 0.719 [0.648, 0.788]ᵃ | 0.694 [0.613, 0.775]ᵃ |
| Baseline ridge, after as-of-scan fix, intermediate inputs (30 / 84) | 0.880 | 0.860 [0.730, 0.943] | not computed | not run | not run | 0.749 [0.675, 0.820]ᵇ | 0.729 [0.648, 0.811]ᵇ |
| Baseline GBM, **pre-fix (leaky)** (30 / 84) | 0.901 | 0.881 (no CI computed) | not computed | not run | not run | 0.743 [0.666, 0.816]ᵃ | 0.723 [0.633, 0.806]ᵃ |
| Baseline GBM, after as-of-scan fix, intermediate inputs (30 / 84) | 0.869 | 0.855 (no CI computed) | not computed | not run | not run | 0.740 [0.663, 0.815]ᵇ | 0.731 [0.641, 0.813]ᵇ |

History rows: the PRISM report split as it was scored before the label fixes (30 test patients / 84 scans; the final
rows above use the label-fixed cohort, 29 / 82). "Pre-fix (leaky)": `treatment()`/`timing()` read RT start/end dates,
dose and chemo status as of the end of follow-up, so pre-RT and on-RT scans carried facts about a course that had not
started or finished (`docs/results/FIX_TREATMENT_ASOF.md` §1). Single-split sources:
`outputs/results/c3/prism_report_split/head_to_head_before.csv` (pre-fix) and `head_to_head_after.csv` (after fix);
IPCW CIs for the PRISM report model and the after-fix ridge from `docs/results/FIX_EVALUATION.md` §5 (`prism head2head`
reproduction). The frozen pre-fix tree `outputs/results_pre_fix_2026-10-11/` holds no PRISM-split rows.
ᵃ `outputs/results_pre_fix_2026-10-11/c3/{all_glioma,grade4}/results.csv` (baseline rows `auc_ipcw`, `_lo`, `_hi`;
old repeat-averaged estimator, pre-label-fix cohort). ᵇ `docs/results/FIX_TREATMENT_ASOF.md` §3, "After" column (the
underlying outputs were overwritten by later runs).
