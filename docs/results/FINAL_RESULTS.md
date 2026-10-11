# Final results for the manuscript (2026-10-11)

All numbers come from the final full re-run on branch `manuscript-week`, HEAD `cc2e3a3` (outputs under `outputs/results/`,
logs under `outputs/logs/`). MU headline estimator: verified 120-d labels, 5×5 repeated patient-grouped CV, **mean over the 5
repeats of the per-repeat pooled-OOF IPCW AUC(120 d)**, 95% CI and paired ΔAUC from a 1000-draw patient-cluster bootstrap.
Primary analysis (pre-specified): grade 4, ridge baseline (clinical + timing + as-of-scan treatment) vs baseline + radiomics
chosen by nested selection over 70 configurations. Detail docs are linked per row.

| Item | Result | Source |
|---|---|---|
| **Cohort** | MU 308 index scans / 155 patients (grade 4: 249 / 126); 120 d: 100 / 156 / 52 progression / no progression / censored (grade 4: 93 / 117 / 39). LUMIERE 132 / 61; 47 / 76 / 9 | `outputs/data/mu_flow.csv`, `outputs/results/analyses/tables/table1.md`, `outputs/logs/lumiere.log`; [TABLE1](../manuscript/TABLE1_COHORT.md), [FLOW](../manuscript/FLOW.md) |
| **Baseline AUC (ridge)** | Grade 4 **0.698 [0.615, 0.774]**; all gliomas **0.720 [0.638, 0.792]**. Boosting 0.687 / 0.718 | `outputs/results/c3/{grade4,all_glioma}/results.csv` |
| **Radiomics, nested (primary)** | Grade 4 0.672 [0.597, 0.743], **ΔAUC −0.026 [−0.073, +0.017]**; all gliomas 0.732, **ΔAUC +0.012 [−0.029, +0.050]**. Single configurations with ΔAUC CI > 0: 0/70 in both (12/70 < 0 in grade 4). Best post-hoc config +0.019 / +0.031 (CIs span 0) | same; [C3](C3_radiomics.md) |
| **C2 group search, nested + permutation** | Grade 4 nested 0.664 [0.601, 0.722], permutation null mean 0.548 (95th pct 0.636), **p = 0.050** (4/100 ≥ observed); all gliomas 0.707 [0.647, 0.766], null 0.528, **p = 0.010** (0/100). Post-hoc grid best 0.714 / 0.744 | `outputs/results/c2/<pop>/{nested,permutation,grid}.csv`; [C2](C2_feature_search.md) |
| **C1 formulations** | All 36 ΔAUC (verified / IPCW / hazard vs naive) CIs include 0; naive label under-predicts (O/E 1.12–1.19 vs 0.95–0.99) | `outputs/results/c1/c1_results.csv`; [C1](C1_endpoint.md) |
| **Baselines ladder (grade 4)** | Clinical only 0.585; timing only 0.559; clinical + timing 0.644 (Δ −0.054 [−0.103, −0.012]); B0 ET volume 0.636; B0 ΔET 0.546; B1 volumetric RANO-style rule 0.551 (Δ −0.147 [−0.239, −0.062]), RANO 2.0 window 0.508; B4 Hashim Cox 0.628 (Δ −0.070 [−0.179, +0.031]). Tuned baselines within ±0.025 of 0.698, all CIs span 0 | `outputs/results/analyses/baselines/{ladder,nested_choices}.csv`; [BASELINES](BASELINES.md) |
| **Schedule coupling (grade 4)** | Gap to next MRI alone 0.639 [0.555, 0.721]. Baseline conditional AUC within gap tertiles 0.687 [0.595, 0.768]; coefficient per SD 0.91 → 0.86 [0.43, 1.41] after log-gap adjustment; features cannot predict gap (CV R² −0.05). Excluding early post-RT / next scan > 120 d: 0.723–0.777. LUMIERE: gap alone 0.788 | `outputs/results/analyses/schedule/`; [SCHEDULE](SCHEDULE_COUPLING.md) |
| **Split variance (PRISM report split)** | PRISM report pipeline re-selected per split: 0.720 ± 0.055 over 500 splits of the PRISM report design (2.5–97.5%: 0.610–0.819); seed-62 re-run 0.801 ranks above 92%; 7% of splits ≥ 0.802. Baseline ranks 91% on the PRISM report split | `outputs/results/analyses/split_variance/summary.csv`; [SPLIT_VARIANCE](SPLIT_VARIANCE.md) |
| **Head-to-head on the PRISM report split** (29 test patients, 82 scans) | PRISM report model 0.802 naive / 0.817 [0.690, 0.920] IPCW; baseline ridge 0.871 / 0.851 [0.735, 0.947]; PRISM report model vs baseline Δ −0.034 [−0.186, +0.109]; adding radiomics to the baseline −0.010 to +0.007 | `outputs/results/c3/prism_report_split/head_to_head.csv` |
| **External LUMIERE, locked** (pre-specified clinical + timing + volumes, grade-4-trained) | Pooled IPCW AUC ridge **0.608 [0.469, 0.739]** (O/E 1.33), boosting **0.620 [0.495, 0.733]** (O/E 0.99); MU CV 0.667 / 0.675. Clinical + timing only 0.610 / 0.632. Recalibration: O/E 0.93–0.97, ranking unchanged; no adaptation arm beats locked | `outputs/results/external_lumiere/results.csv`; [EXTERNAL](EXTERNAL_LUMIERE.md) |
| **External, cohort-normalised volumes** (sensitivity) | Rank: ridge 0.624 [0.491, 0.752], boosting 0.659 [0.529, 0.767] (per-fold Δ vs locked +0.047 [−0.002, +0.110]); z-score 0.619 / 0.637 | same (`arm` = locked+cohort_norm_{rank,zscore}) |
| **Shipped PRISM report model on LUMIERE** | 0.613 [0.500, 0.729] (118 scans; O/E 1.24); fine-tuned 0.570 pooled. File dated 2026-10-09, not regenerated in the final run | `outputs/results/external_lumiere/shipped_model{,_adaptation}.csv` |
| **Calibration (grade 4)** | Baseline ridge O/E 0.96, CITL −0.09 [−0.42, 0.28], slope 0.89 [0.50, 1.43]; nested radiomics slope 0.50 [0.27, 0.86]; nested deep 0.49 [0.24, 0.87] | `outputs/results/analyses/utility/calibration.csv`; [UTILITY](CLINICAL_UTILITY.md) |
| **Net benefit (grade 4)** | Baseline vs treat-all at 30%: 0.232 vs 0.189. ΔNB radiomics vs baseline −0.001 / +0.002 / −0.014 at 10/20/30% (all CIs span 0); deep −0.004 / +0.006 / +0.005 (CIs span 0). LUMIERE locked boosting ≈ treat-all (0.218 vs 0.222 at 20%) | `utility/net_benefit.csv` |
| **NRI / IDI (grade 4, vs baseline)** | Radiomics: NRI +0.20 [−0.02, 0.42], IDI +0.009 [−0.019, 0.035]. Deep: NRI +0.52 [0.30, 0.75], IDI +0.049 [0.002, 0.097] (driven by overfit, miscalibrated upward shifts in events; ΔAUC and ΔNB null) | `utility/added_value.csv` |
| **Riley sample size (grade 4)** | 210 verified scans, 93 events, 3.0 EPP for the 31-column baseline; required 2190 scans (970 events) by the shrinkage criterion; + 10 radiomics 2896; full radiomics pool 174,942 | `utility/sample_size.csv` |
| **Sensitivity (9 analyses)** | Baseline AUC 0.642–0.725; nested-radiomics ΔAUC −0.034 to +0.012, no CI excludes 0 (horizons 90/180 d, composite, alternative date, imaging-only follow-up, all gliomas, excluding post-RT scans, excluding patient 0145) | `outputs/results/analyses/sensitivity/summary.csv`; [SENSITIVITY](SENSITIVITY.md) |
| **Deep features (frozen SwinUNETR)** | MU nested pretrained (D1) ΔAUC +0.006 [−0.058, +0.071] grade 4, +0.005 [−0.044, +0.054] all gliomas; 0/80 single configs > 0; random-weight control D0 −0.041 [−0.077, −0.007]. LUMIERE locked + deep: +0.068 [−0.116, +0.238] (grade 4) / +0.078 [−0.010, +0.162] (all gliomas); vs random-weight encoder, same config: +0.029 [−0.078, +0.148] / +0.057 [−0.017, +0.131]. Deep features identify the cohort (AUC ≈ 0.8, random weights too) and under-predict LUMIERE risk (O/E 1.38–1.84) | `outputs/results/analyses/deep/`; paired pretrained-vs-random and cohort-ID numbers from the verifier's `check.log`; [DEEP](DEEP_FEATURES.md) |

**Bottom line.** A clinical + timing + treatment model reaches IPCW AUC ≈ 0.70 (grade 4) to 0.72 (all gliomas) under honest
repeated CV. Neither radiomics nor frozen deep features add measurable value (nested ΔAUC −0.026 to +0.012, all CIs span 0;
models overfit). The PRISM report's 0.80 is an upper-tail draw of its split design (7% of splits reach it). External transport
to LUMIERE is modest (locked ≈ 0.61–0.62; shipped PRISM report model 0.61), partly limited by segmenter scale, and the
external labels are strongly schedule-coupled (gap alone 0.79).

**Known gaps.** `shipped_model*.csv` were not regenerated in the final run (legacy env); the C3 legacy-radiomics ablation and
the split-variance verifier checks are from earlier runs; `c3/grade4_ablation_masking_only/` and
`c3/prism_report_split/head_to_head_{before,after}.csv` are stale artefacts from before the final run.
