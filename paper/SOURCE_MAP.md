<!-- Moved verbatim from docs/manuscript/DRAFT.md (2026-10-15 snapshot); not part of main.pdf. Section and table numbers refer to paper/main.tex. -->

## Appendix: Source map (not for submission)

Every number in this draft, by section, with its source file. `R/` = `docs/results/`, `M/` = `docs/manuscript/`,
`F/` = `docs/manuscript/figures/`, `O/` = `outputs/results/`. Where a doc quotes an output file, the doc is listed and
the output file is given in the doc's own source table. "Derived" = arithmetic on sourced numbers, stated as such.

| Claim (section) | Value(s) | Source |
|---|---|---|
| PRISM report model single-split AUC (Abstract, Intro, 3.2, Table 2, Fig 1) | 0.802 naive; 0.817 [0.690, 0.920]; Δ −0.034 [−0.186, +0.109] | `O/analyses/paper_figures/single_split.csv` (= `F/table2…`, `M/FIGURES.md` Fig 1); `O/c3/prism_report_split/head_to_head.csv` |
| Baseline ridge / GBM / + legacy radiomics / clinical-only on the split | 0.871 / 0.851 [0.735, 0.947]; 0.844 / 0.824 [0.690, 0.916], Δ −0.027 [−0.127, +0.062]; 0.862 / 0.845 [0.746, 0.936], Δ −0.006 [−0.081, +0.090]; 0.791 / 0.782 [0.638, 0.897], Δ −0.069 [−0.215, +0.058] | same; clipped radiomics row per `M/FIGURES.md` §1 |
| Split size | 126 train / 29 test patients, 82 scans, 22 naive positives; originally 30 / 84 | `M/FIGURES.md` Fig 1; `R/SHAP_PRISM_SPLIT.md` |
| Pre-fix / after-fix split AUCs (3.2, Table 2 history) | GBM 0.901 / 0.881 → 0.869 / 0.855; ridge 0.870 / 0.844 → 0.880 / 0.860; PRISM 0.802 / 0.811 | `O/c3/prism_report_split/head_to_head_before.csv`, `head_to_head_after.csv`; `R/FIX_TREATMENT_ASOF.md` §3 |
| After-fix CIs | ridge 0.860 [0.730, 0.943]; PRISM 0.811 [0.694, 0.919] | `R/FIX_EVALUATION.md` §5 |
| Pre-fix repeated-CV baseline | GBM 0.723 [0.633, 0.806] G4, 0.743 [0.666, 0.816] all; ridge 0.694 [0.613, 0.775], 0.719 [0.648, 0.788] | `outputs/results_pre_fix_2026-10-11/c3/{grade4,all_glioma}/results.csv` |
| After-fix intermediate CV | ridge 0.729 [0.648, 0.811] / 0.749 [0.675, 0.820]; GBM 0.731 [0.641, 0.813] / 0.740 [0.663, 0.815] | `R/FIX_TREATMENT_ASOF.md` §3 |
| Leak counts | RT status 23 all-glioma scans; RT duration / days since RT end 29 | `R/FIX_TREATMENT_ASOF.md` §1 |
| Pair decomposition, composition percentiles | 36 of 60 negatives pre-RT, 0 progressed, 60% of pairs; 0.962 / 0.735; 0.823 / 0.771; 89th, 5th, 6th, 92nd percentiles; rule 0.740; 9% / 8.7% pre-RT event rate | `R/SHAP_PRISM_SPLIT.md` §3; `F/single_split_pairs.csv` |
| Post-RT subset of the split | 42 scans / 19 patients; PRISM 0.770 [0.604, 0.907]; ridge 0.718 [0.481, 0.880]; clinical 0.818 [0.664, 0.924], Δ +0.100 [−0.015, +0.293] | `O/analyses/paper_figures/single_split.csv` (subset=post_rt); `M/FIGURES.md` Fig 1 note |
| 500 splits (3.3, Table 2, Fig 2) | 0.720 ± 0.055 (0.610–0.819); 0.801, 92nd pct; 7%; 0.815 ± 0.044; baseline 0.801 ± 0.052 (0.694–0.895), 91st pct; + radiomics 0.799 ± 0.053 (0.674–0.892), 51.6%, mean Δ −0.002; 475 IPCW splits; 82–94 scans, 10–33 positives | `O/analyses/split_variance/summary_clipped.csv` via `M/FIGURES.md` Fig 2; `R/SPLIT_VARIANCE.md` (design, non-radiomics rows) |
| Honest vs optimistic gap; loses to baseline | 0.095 ± 0.040; 88%, mean −0.081 | `R/SPLIT_VARIANCE.md` |
| Optuna verifier check | −0.064 ± 0.055; 0.865 vs 0.654; ≈ 0.21; 15 splits | `R/SPLIT_VARIANCE.md` sensitivity check 1 |
| Composition regression | ρ +0.57 / +0.22; predicted 0.851 / 0.773; CV R² 0.42 / 0.10; nine variables; two thirds | `R/SHAP_PRISM_SPLIT.md` §3; `M/FIGURES.md` Fig 2 |
| Single split 0.10–0.16 above CV | — | `M/FIGURES.md` Table 2 caption |
| Cohort and Table 1 | 596 / 203 → 308 / 155; 249 / 126; 100 / 156 / 52; 93 / 117 / 39; LUMIERE 132 / 61, 47 / 76 / 9; phase counts 76 / 6 / 98 / 69; all Table 1 cells | `M/FLOW.md`, `M/TABLE1_COHORT.md`; `R/PHASE_LADDER.md` §1–2 |
| Label fixes | six scans left; 17 negatives → censored; 1 negative → positive | `R/FIX_LABELS.md` |
| C1 formulations | 36 ΔAUC CIs include 0; O/E 1.12–1.19 vs 0.95–0.99 | `R/C1_endpoint.md` |
| Baseline design | 23 raw predictors, 31 design columns | `R/AUDIT_SYSTEM.md` §0; `R/CLINICAL_UTILITY.md` |
| Radiomics sentinel | 10⁶ in 3 columns, 4 scans | `R/FIX_RADIOMICS_CLIP.md` |
| Legacy columns; deep features | 2,446; 720 per region, 8 flips | `R/FIX_RADIOMICS_CLIP.md`; `R/DEEP_FEATURES.md` |
| Shipped-model reproduction | 1.1 × 10⁻¹⁵; 46 columns | `R/SHAP_PRISM_SPLIT.md` §1 |
| Ladder (3.4, Fig 3A) | 0.585 [0.496, 0.666]; 0.644 [0.560, 0.721]; 0.698 [0.615, 0.774]; 0.619; 0.693; 0.720 [0.638, 0.792]; GBM 0.687, 0.718 | `M/FIGURES.md` Fig 3A; `R/C3_radiomics.md` |
| Tuning grids; literature baselines | ±0.025; ET 0.636; rule 0.551, Δ −0.147 [−0.239, −0.062]; RANO 2.0 0.508; Cox 0.628 | `R/BASELINES.md` |
| Radiomics nested (Table 3) | −0.032 [−0.084, +0.017] (0.666); +0.028 [−0.017, +0.071] (0.747); 0/70, 8/70; 1/70 +0.035 [+0.002, +0.068]; 1.75; slope 0.60 vs 0.89 | `R/C3_radiomics.md`; `F/table3_forest.csv` |
| C2 search | 0.664 [0.601, 0.722], p = 0.050 | `R/C2_feature_search.md`; `R/FINAL_RESULTS.md` |
| Deep features | −0.004 [−0.069, +0.063]; +0.011 [−0.032, +0.056]; 0.652 vs 0.566; r = 0.58; D0 −0.049 [−0.085, −0.014] | `R/DEEP_FEATURES.md`; `F/table3_forest.csv` |
| SHAP | 45% / 51%; 0.692 / 0.694; treatment 58%, clinical 25%, timing 17% | `R/SHAP.md`; `M/FIGURES.md` Fig 3C |
| Phase ladder (3.5, Fig 4) | R2 0.664; R2 − R0 +0.080 [+0.005, +0.152]; R2 + I1 0.696; post-RT 0.549–0.604; −0.003; primary 0.549 (0.458–0.642) → 0.610 (0.529–0.688), +0.061 (−0.038, +0.156), p 0.21; null +0.028; 44 columns; secondary +0.061 (−0.041, +0.157), slope 0.44; +0.005 to +0.04; age 0.586; later 69 scans, 0.343–0.472; 167 / 84 / 83 | `R/PHASE_LADDER.md`; `F/fig4_phase.csv` |
| Clean label (3.6) | 12 of 93 (10 patients); 0.722 (0.639–0.799) vs 0.696 (0.610–0.776); +0.027 (−0.033, +0.082); −0.068 | `R/CLEAN_LABEL.md` |
| Positive controls | r 0.9957–0.9998; 0.68 [0.62, 0.74]; 49% of 74, p 0.54; 79%, p 0.0003; 3.2-fold, ≤ 14 d; ρ −0.01; 79%, κ 0.53; 3 identical pairs; 12 scans | `R/DIAGNOSTICS_IMAGING.md` |
| Re-segmentation | Dice 0.80 / 0.85; 0.681 → 0.665, Δ −0.016 [−0.057, +0.025]; 45%; bsf 0.677, 41%; forward +0.030 [−0.008, +0.069] | `R/RESEGMENTATION.md`; `F/table3_forest.csv` |
| LUMIERE (3.7) | 0.608 [0.469, 0.739]; 0.620 [0.495, 0.733]; MU CV 0.667 / 0.675; 0.610 / 0.632; −0.001 [−0.073, +0.057]; O/E 1.33 / 0.99; 0.93–0.97; rank 0.659 [0.529, 0.767]; deep +0.050 to +0.089, +0.050 [+0.002, +0.109]; random up to +0.045; cohort AUC ≈ 0.8; shipped 0.613 [0.500, 0.729], 118 scans; gap 0.788 [0.703, 0.868] | `R/EXTERNAL_LUMIERE.md`; `R/DEEP_FEATURES.md`; `R/BASELINES.md`; `R/SCHEDULE_COUPLING.md` |
| External loss 0.05–0.06 (Discussion) | derived: 0.667 − 0.608, 0.675 − 0.620 | `R/EXTERNAL_LUMIERE.md` |
| CFB-GBM | 77 pts / 19 events; +0.007 (−0.019, +0.035); p 0.151; MDE 0.038; 0.501 / 0.565; +0.185 (+0.064, +0.293), +0.148 (+0.031, +0.266); −0.009 / −0.022; 107 pts / 30 events; 264 patients; t1 6–8 weeks after RT | `R/CFB_ADC.md`; `O/analyses/cfb_adc/rule.json`; `docs/literature/DATASETS.md` |
| Calibration and utility (3.8) | O/E 0.96; CITL −0.09 [−0.42, 0.28]; slope 0.89 [0.50, 1.43]; NB 0.232 vs 0.189; −0.020 [−0.038, −0.004]; deep ±0.002; 3.0 EPP; 2,190 (970) | `R/CLINICAL_UTILITY.md` |
| Sensitivity, imbalance, schedule | 0.642–0.725; −0.032 to +0.028; −0.031 to +0.023; 0.687 [0.595, 0.768] | `R/SENSITIVITY.md`; `R/IMBALANCE.md`; `R/SCHEDULE_COUPLING.md` |
| Audit layer (3.9, Fig 5) | 1.7 × 10⁻¹⁶; 1.3 × 10⁻¹⁵; P1 0.841 [0.790, 0.885], 0.823 [0.776, 0.865]; 5 / 10 pre-RT events; 0.567 (6 scans); conformal AUC 0.667; P2 0.731 [0.635, 0.812], 0.725, 0.698, +0.006 [−0.023, +0.036], +0.003 [−0.031, +0.036]; 97.6%; rule (i) 0.723; within-phase 0.555 / 0.663 / 0.597; 72.6%; IDH unknown 0/93, 6/117, 5/39; −0.023 [−0.047, −0.001]; treatment-only 0.701 [0.622, 0.776], +0.003 [−0.050, +0.048]; 8 scans, 1–58 days; 40.9% vs 4.4%; −0.68 logits; O/E 1.33 → 0.89; coverage 0.715 (0.340 events); top 5 ≤ 4%; 200 bootstraps; 70/30 | `R/AUDIT_SYSTEM.md`; `O/analyses/audit_system/{p2,conformal,referral,shortcut_arms,lumiere_smd,lumiere_oe,stability_summary,checks}.csv` |
| Literature numbers (Intro, Discussion) | Booth 0.765 (≈0.77); Taylor 0.90–0.93; Christodoulou 0.80; Rai 0.728; An 0.882/0.667, 0.709/0.911; Varoquaux ±10%, n = 100; Yu 81%, 24%, 0.10; Park 29.4%; Leone 0.69; Gomaa 0.727 vs 0.717; Abler 0.74 vs 0.75; Jang 0.52, 19 patients; Chen 0.887 → 0.762; Tak 75–89%; Yun 0.75 | `docs/literature/COMPARABLE_RESULTS.md` |
| RANO windows | 12 weeks / 84 days | `R/FIX_TREATMENT_ASOF.md` §2; `R/PHASE_LADDER.md` |
