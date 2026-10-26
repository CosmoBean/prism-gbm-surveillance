# Manuscript figures and tables (results sections 1–3 + phase of care)

## System-first display inventory (approved 2026-10-26)

| Display | One reader question | Source and scope |
|---|---|---|
| Figure 1, `fig1_system.pdf` | What does PRISM turn into a report? | System flow: serial MRI and record -> measurements and separate evidence streams -> structured record -> local checked report. Do not present it as a diagnostic decision engine. |
| Table 1 | What evidence can each cohort contribute? | Existing cohort table, reframed around images, treatment dates, masks, label/documentation and reportable longitudinal context. |
| Figure 2, `fig2_transport.pdf` | How do components behave across cohorts? | Verified internal and locked external image/timeline/combined results. Keep task definition beside the figure. |
| Figure 3, `fig3_evidence.pdf` | Why retain separate evidence streams? | Existing audit: timing/phase at MU and enhancement at UCSF. No new model claim. |
| Figure 4, `fig4_confidence.pdf` | What are the report's evidence limits? | Conformal coverage, disagreement and thin-evidence card; describe them as displayed evidence boundaries. |
| Figure 5, `fig5_report.pdf` | What does the reader receive, and what was verified? | v3.1 report anatomy plus automatic grounding/completeness: 406/406 lexical passes, 220/220 tier statements, 28/30 perturbation-rule passes. State that there is no clinician reader outcome. |

The existing figure plan below is retained while source assets are reconciled. It is not the final ordering or claim set.

---

Code: `prism/analyses/paper_figures.py` (`python -m prism figures [all|compute-single|compute-splitvar|plot]`).
Figures: `docs/manuscript/figures/fig{1..4}_*.{png,pdf}` (300 dpi PNG + vector PDF). Plot data and tables:
`outputs/results/analyses/paper_figures/*.csv` (copied to `docs/manuscript/figures/`).
Style: one palette for every figure (reference categorical palette, validated for colour-vision deficiency on adjacent
pairs; every series is also direct-labelled or keyed by marker shape), DejaVu Sans 7–8.5 pt, panels lettered.
Model colours are fixed across figures: PRISM report model/pipeline orange, shipped-features refit yellow, baseline
ridge blue, baseline GBM violet, baseline + radiomics green, clinical only grey, deep pink.

All AUCs are AUC(120 d). "IPCW" = inverse-probability-of-censoring-weighted cumulative/dynamic AUC; "naive" = the
PRISM report's label (progression within 120 d, censored scans counted as negatives). "Baseline" = clinical + timing +
as-of-scan treatment, ridge (C3).

## Figure plan (2026-10-16; manuscript numbering)

Section names below this one ("Figure 1. The PRISM report split", ...) use the old analysis numbering; this table maps
them to the manuscript. Planned figures appear in `main.pdf` as a red framed box (`\figslot` in `paper/macros.tex`)
that states what the figure must show, and are replaced automatically once the file exists in `figures/`.

| Manuscript | Content | File | Status |
|---|---|---|---|
| Figure 1 | PRISM architecture and data flow | `fig5a_architecture.pdf` | done |
| Figure 2 | **Study design**: cohorts and outcome; initial split → 500 splits → 5×5 repeated CV, LUMIERE locked test, CFB-GBM CV; prespecified questions pointing to Table 4 | `fig_study_design.pdf` | done (2026-10-21; `prism/analyses/figures_extra.py`) |
| Figure 3 | Initial evaluation split (old "Figure 1") | `fig1_single_split.pdf` | done |
| Figure 4 | 500 splits (old "Figure 2") | `fig2_split_variance.pdf` | done |
| Figure 5 | Ablation ladder, ΔAUC forest, SHAP shares (old "Figure 3") | `fig3_clinical_vs_radiomics.pdf` | done |
| Figure 6 | Phase of care (old "Figure 4") | `fig4_phase_of_care.pdf` | done |
| Figure 7 | Imaging examples: patient across phases with masks; dataset vs resegmented ET; ET volume noise (selection rules in the module docstring) | `fig_imaging_examples.pdf` | done (2026-10-21; `figures_extra.py`) |
| Figure 8 | (A) example report; (B) risk–coverage | `fig6a_example_report_v2.pdf`, `fig5_system_risk_coverage.pdf` | done |
| Graphical abstract | Optional journal extender (could adapt Figure 1 or 2) | — | not planned |

Tables (main text): 1 cohorts; 2 single split vs 500 splits vs CV; 3 imaging branches vs core (ΔAUC); **4 prespecified
questions, rules and answers** (new); **5 report v1 vs v2** (new).

**No repetition between tables and text (journal rule, 2026-10-16).** The decision rules now live only in Table 4;
Methods describe each analysis and point to it. Results tell the story with the key estimate and cite the table for
intervals and the remaining rows; numbers that appear only in the text (within-phase AUCs, SHAP shares, censoring
details, LUMIERE AUCs) stay in the text. Overlap between tables is limited to the primary estimates in Table 4, which
also appear as rows of Tables 2 and 3.

**Files for submission.** T&F asks for PS, JPEG or TIFF at the printed size: 300 dpi colour, 600 dpi greyscale or
mixed colour and line work, 1200 dpi line art. All figures exist as vector PDF; export each to TIFF at 600 dpi
(Figures 3 to 7 are charts with line work) and Figures 1 and 2 at 1200 dpi if they stay pure line art. Not done yet.

## What was re-run for these figures (2026-10-15)

1. **PRISM report split, all models re-fitted with the current (clipped) C3 code** (`compute-single`, 1000-draw
   patient-cluster bootstrap, seed 0, same estimator as `head_to_head.py`) → `paper_figures/single_split.csv`,
   `single_split_pairs.csv`. Adds a clinical-only ridge (not previously run on this split).
   - Non-radiomics rows reproduce `outputs/results/c3/prism_report_split/head_to_head.csv` exactly (PRISM report model
     0.802 / 0.817 [0.690, 0.920]; baseline ridge 0.871 / 0.851 [0.735, 0.947]; GBM 0.844 / 0.824 [0.690, 0.916]) and
     the post-RT rows reproduce `shap_prism_split/subset_auc.csv`.
   - **Baseline + legacy radiomics (top-10 concat) changes with the clip**: naive 0.867 → **0.862**, IPCW 0.847
     [0.745, 0.940] → **0.845 [0.746, 0.936]**, Δ vs baseline −0.004 → **−0.006 [−0.081, +0.090]**. The clipped values
     equal the (post-fix) `shap_prism_split/subset_auc.csv` row. `head_to_head.csv` itself was not overwritten.
2. **Split variance, `baseline_rad` arm re-run with the clip.** `split_variance.py` builds `baseline_rad` with
   `c3.fit_predict(("legacy","none","top10","concat","ridge"), ...)`, i.e. through `c3.selector`, which now starts with
   `QuantileClip`. So the arm could be re-run cleanly: same 500 test-patient sets (read from `per_split_auc.csv`), same
   cohort and features, 22 processes, 0.1 min. The `baseline` arm was re-fitted alongside as a check and matches the
   stored values to 1e-16 (`split_variance/run_info_clipped.json`). Outputs (originals untouched):
   `outputs/results/analyses/split_variance/{per_split_auc_clipped.csv, summary_clipped.csv, run_info_clipped.json,
   rerun_clipped.log}`. `per_split_auc_clipped.csv` keeps the old values as `baseline_rad_preclip_auc_{naive,ipcw}`.

   | `baseline_rad` (summary row) | pre-clip (`summary.csv`) | clipped (`summary_clipped.csv`) |
   |---|---|---|
   | naive mean ± SD | 0.801 ± 0.053 | **0.799 ± 0.053** |
   | naive 2.5–97.5% | 0.679–0.892 | **0.674–0.892** |
   | seed-62 value (rank) | 0.867 (90.4%) | **0.862 (89.2%)** |
   | ≥ 0.802 | 52.2% | **50.2%** |
   | beats baseline / mean Δ | 53.8% / −0.000 | **51.6% / −0.002** |
   | IPCW mean ± SD (n = 475) | 0.776 ± 0.058 | **0.774 ± 0.058** |
   | IPCW seed-62 (rank) | 0.847 (91.4%) | **0.845 (92.0%)** |
   | IPCW beats baseline / mean Δ | 60.4% / +0.006 | **56.8% / +0.005** |

   Per split, clipped − pre-clip naive AUC: mean −0.002, SD 0.009, range −0.052 to +0.047. No conclusion changes.
   `docs/results/SPLIT_VARIANCE.md` and `FINAL_RESULTS.md` still quote the pre-clip `baseline_rad` numbers; update them
   from `summary_clipped.csv`.

---

## Figure 1. The PRISM report split

**Caption draft.** *Discrimination on the PRISM report split (all gliomas; 126 training / 29 test patients, 82 test
scans, 22 naive positives). Every model except the PRISM report model was fitted once on the training patients with
the C3 pipeline; the PRISM report model enters with its shipped test-set probabilities. (A) IPCW AUC with 95%
patient-cluster bootstrap CI (1000 draws; dot and bar) and naive AUC (tick). (B) Naive AUC decomposed by the type of
negative scan: 36 of the 60 negative test scans were taken before radiotherapy started (none of the 36 progressed), so
60% of positive–negative pairs compare a progression scan with a pre-RT scan; solid bars, positives vs pre-RT
negatives; light bars, positives vs other negatives. (C) The same models on the 42 post-RT test scans (19 patients,
19 positives). Intervals are wide and overlap throughout; on post-RT scans no model differs from the baseline.*

| Number shown | Value | Source (path · column; row) |
|---|---|---|
| A: IPCW AUC [CI], PRISM report model | 0.817 [0.690, 0.920] | `outputs/results/analyses/paper_figures/single_split.csv` · `auc_ipcw`, `auc_ipcw_lo`, `auc_ipcw_hi`; subset=all, model=PRISM report model |
| A: baseline ridge | 0.851 [0.735, 0.947] | same; model=Baseline ridge |
| A: baseline GBM | 0.824 [0.690, 0.916] | same; model=Baseline GBM |
| A: baseline + legacy radiomics | 0.845 [0.746, 0.936] | same; model=Baseline + legacy radiomics |
| A: clinical only | 0.782 [0.638, 0.897] | same; model=Clinical only (ridge) |
| A: naive ticks | 0.802 / 0.871 / 0.844 / 0.862 / 0.791 | same · `auc_naive` |
| A: scans / patients | 82 / 29 | same · `n_scans`, `n_patients` |
| B: pos vs pre-RT neg | 0.823 / 0.962 / 0.933 / 0.934 / 0.789 (shown to 2 dp) | `paper_figures/single_split_pairs.csv` · `auc_vs_pre_rt_neg` |
| B: pos vs other neg | 0.771 / 0.735 / 0.710 / 0.754 / 0.793 | same · `auc_vs_other_neg` |
| B: pair share | 60% (22 pos, 36 pre-RT neg, 24 other neg) | same · `pair_share_pre_rt_neg`, `n_pos`, `n_neg_pre_rt`, `n_neg_other` |
| C: IPCW AUC [CI] post-RT | PRISM 0.770 [0.604, 0.907]; ridge 0.718 [0.481, 0.880]; GBM 0.699 [0.463, 0.846]; + radiomics 0.758 [0.605, 0.886]; clinical 0.818 [0.664, 0.924] | `single_split.csv` · `auc_ipcw(_lo/_hi)`; subset=post_rt |
| C: naive ticks | 0.778 / 0.730 / 0.705 / 0.769 / 0.826 | same · `auc_naive` |
| C: scans / patients | 42 / 19 | same · `n_scans`, `n_patients` |

Model order and the PRISM report model / baseline numbers match `c3/prism_report_split/head_to_head.csv` and
`shap_prism_split/{subset_auc,auc_pair_decomposition}.csv`. The clinical-only rows are new. Note for the text: on
post-RT scans the clinical-only ridge (0.818) is nominally the highest of all five; its Δ vs baseline is +0.100
[−0.015, +0.293] (`d_auc_ipcw_vs_baseline`), i.e. not distinguishable — another illustration of single-split noise.

## Figure 2. Split variance

**Caption draft.** *Where the PRISM report split sits among 500 splits of the same design. The PRISM report's own
split search (`choose_test_patients`: per seed, 20 000 random draws of 30 patients, keep the draw closest to 96 test
scans / 53 positives) was run for seeds 0–499, giving 500 distinct test sets; seed 62 reproduces the PRISM report
split. (A) Test AUC (naive label) per split; violin + points = 500 splits, grey dot and line = mean and 2.5–97.5%
range, diamond = the model's own value on the PRISM report split re-run in this analysis, with its percentile rank
(share of splits strictly lower); dashed line = the reported 0.802. **PRISM report pipeline, features re-selected per
split** (`prism_reselect`): the PRISM report pipeline with its L1 + permutation consensus feature ranking redone on
each split's training patients (5 folds × 5 repeats instead of the shipped 10 × 100), top 48 features, shipped
C; Optuna not re-run. This is the honest estimate of the pipeline. **PRISM report model, shipped features refitted**
(`prism_fixed`): the shipped 48 columns, preprocessing thresholds and C, refitted on each split's training patients.
It is optimistic — an upper bound — because those columns were selected on the PRISM report split's training
patients, who include most test patients of the other splits. Baseline and baseline + legacy radiomics (top-10,
concatenated, with in-fold 1%/99% clipping) use the C3 code. (B) Per-split AUC against a composition measure of the
test set: the AUC of the no-training rule "scan is post-RT" on that test set (higher = more pre-RT negatives and
fewer pre-RT events). Lines = least-squares fits; diamonds = PRISM report split.*

| Number shown | Value | Source |
|---|---|---|
| A: mean ± SD, prism_reselect | 0.720 ± 0.055 | `outputs/results/analyses/split_variance/summary_clipped.csv` · `mean`, `sd`; model=prism_reselect, metric=naive (identical to `summary.csv`) |
| A: 2.5–97.5%, prism_reselect | 0.610–0.819 | same · `p2.5`, `p97.5` |
| A: PRISM split value (rank), prism_reselect | 0.801 (92nd percentile; 92.2) | same · `prism_split_value`, `pct_rank_prism_split_value` |
| A: ≥ 0.802, prism_reselect | 7% (0.072) | same · `frac_ge_0.80` (threshold = `REPORT_AUC` 0.802 in `split_variance.py`) |
| A: prism_fixed | 0.815 ± 0.044; 0.726–0.887; 0.802 (38th); 62% | same; model=prism_fixed |
| A: baseline | 0.801 ± 0.052; 0.694–0.895; 0.871 (91st; 90.6); 50% | same; model=baseline |
| A: baseline_rad (clipped) | 0.799 ± 0.053; 0.674–0.892; 0.862 (89th; 89.2); 50% (0.502) | same; model=baseline_rad (`baseline_rad_source` = clipped re-run) |
| A: per-split points | 500 per model | `split_variance/per_split_auc_clipped.csv` · `{model}_auc_naive` |
| A: reported 0.802 | 0.802 | `split_variance.py` `REPORT_AUC`; `paper_figures/single_split.csv` PRISM report model `auc_naive` 0.8023 |
| B: x | per split | `outputs/results/analyses/shap_prism_split/per_split_composition.csv` · `score_phase_post_rt` |
| B: y | per split | same · `baseline_auc_naive`, `prism_reselect_auc_naive` (equal to `per_split_auc.csv`; these two arms were not affected by the clip) |
| B: Spearman ρ | baseline +0.57, prism_reselect +0.22 | computed in the figure from the two columns above; equal to `shap_prism_split/split_auc_vs_composition.csv` · `spearman` (auc=baseline_auc_naive / prism_reselect_auc_naive, composition=score_phase_post_rt) |
| B: PRISM split point | x 0.740; y 0.871 / 0.801 | same file, row `prism_report_split` = True |

Text numbers that belong with Fig 2 (not drawn): composition-predicted seed-62 AUC 0.851 (baseline) and 0.773
(prism_reselect), CV R² 0.42 / 0.10 — `shap_prism_split/split_auc_composition_ols.csv` · `seed62_predicted_from_composition`,
`r2_cv10`. The design narrows spread relative to fully random 30-patient splits (SD 0.054 vs 0.069; verifier,
earlier run, `SPLIT_VARIANCE.md`).

## Figure 3. Clinical vs radiomics, head-to-head

**Caption draft.** *(A) Feature-group ladder under 5×5 repeated patient-grouped CV (ridge; mean over repeats of
per-repeat pooled-OOF IPCW AUC, 95% patient-cluster bootstrap CI). Clinical (age, sex, IDH, MGMT) → + timing →
+ as-of-scan treatment (= baseline, B); the last three points each add one imaging block to B (not cumulative):
volumes, radiomics (nested choice over 70 configurations), frozen deep features (nested over 32 configurations).
(B) Paired ΔAUC with 95% patient-cluster bootstrap CI against the reference named in each section heading (baseline
unless stated). Asterisk = CI excludes 0 (3 of 32 intervals; uncorrected, ~1.6 expected by chance at a two-sided 5% level). "Single config" and "best post hoc" rows are optimistic; the nested rows account for selection. Deep encoder
rows use the same configuration (lesion, PCA-10, stacked) for both pretrained encoders. Re-segmentation rows compare
the same clinical + phase + imaging model on masks from a single consistent segmenter vs the MU masks. LUMIERE rows are
locked MU-trained models applied once to 132 (volumes) or 118 (deep) LUMIERE scans; reference = the shared
clinical + timing model (± volumes); treatment features do not exist in LUMIERE. (C) Share of mean |group SHAP| in
grade-4 out-of-fold explanations: imaging blocks take 45–51% of the credit in the full models, and the stacked radiomics
score 16%, without improving discrimination.*

**Panel A** (all from `outputs/results/analyses/phase_ladder/results.csv` · `auc_ipcw`, `auc_ipcw_lo`, `auc_ipcw_hi`;
learner=ridge, cohort=full; plot data `paper_figures/fig3a_ladder.csv`):

| Step (arm) | Grade 4 | All gliomas |
|---|---|---|
| Clinical (R0) | 0.585 [0.496, 0.666] | 0.619 [0.540, 0.696] |
| + timing (R1) | 0.644 [0.560, 0.721] | 0.693 [0.617, 0.766] |
| + treatment = B (R3) | 0.698 [0.615, 0.774] | 0.720 [0.638, 0.792] |
| B + volumes (R3+I1) | 0.702 [0.609, 0.781] | 0.733 [0.652, 0.801] |
| B + radiomics, nested (R3+I3) | 0.666 [0.586, 0.739] | 0.747 [0.678, 0.811] |
| B + deep, nested (R3+I4) | 0.694 [0.610, 0.773] | 0.731 [0.660, 0.798] |

R0/R1/R3 equal `baselines/ladder.csv` (clinical only / clinical + timing / baseline ridge); R3+I3 equals the C3
nested row and R3+I4 the deep NESTED_D1 row (same AUCs to 3 dp).

**Panel B** (plot data and exact source rows: `paper_figures/fig3b_forest.csv` · `d_auc`, `lo`, `hi`, `source`, `row`;
formatted copy `docs/manuscript/figures/table3_forest.csv`):

| Section · row | Grade 4 Δ [95% CI] | All gliomas Δ [95% CI] | Source (path · columns; row) |
|---|---|---|---|
| C3 · radiomics nested (primary) | −0.032 [−0.084, +0.017] | +0.028 [−0.017, +0.071] | `outputs/results/c3/{grade4,all_glioma}/results.csv` · `d_auc_ipcw_vs_None|none|none|none|ridge`, `d_auc_ipcw_lo`, `d_auc_ipcw_hi`; variant=NESTED |
| C3 · legacy top-10 concat (single config) | +0.005 [−0.059, +0.067] | +0.024 [−0.026, +0.075] | same; legacy|none|top10|concat|ridge |
| C3 · legacy PCA-10 stack (best post hoc) | +0.023 [−0.013, +0.057] | +0.035 [+0.002, +0.068] * | same; legacy|none|pca10|stack|ridge |
| Deep · nested D1 (both encoders) | −0.004 [−0.069, +0.063] | +0.011 [−0.032, +0.056] | `outputs/results/analyses/deep/{pop}/results.csv` · `d_auc_ipcw`, `d_auc_ipcw_lo`, `d_auc_ipcw_hi`; arm=NESTED_D1 |
| Deep · BraTS21 SwinUNETR lesion PCA-10 stack | +0.016 [−0.029, +0.059] | +0.017 [−0.014, +0.050] | same; arm=brats21:lesion|none|pca10|stack|ridge |
| Deep · BrainSegFounder lesion PCA-10 stack | +0.014 [−0.029, +0.057] | +0.024 [−0.013, +0.064] | same; arm=bsf:lesion|none|pca10|stack|ridge |
| Deep · random-weight control, nested D0 | −0.049 [−0.085, −0.014] * | −0.009 [−0.032, +0.009] | same; arm=NESTED_D0 |
| Imaging-defined label · B + volumes/delta vs B | +0.027 [−0.033, +0.082] | +0.008 [−0.036, +0.049] | `outputs/results/analyses/clean_label/results.csv` · `d_auc_ipcw(_lo/_hi)`; label=imaging, cohort=full, learner=ridge, model=baseline+imaging, reference=baseline (grade 4 = `rule.json` contrast) |
| Post-RT · R2 + I2 vs R2 (pre-specified primary) | +0.061 [−0.038, +0.156] | +0.033 [−0.054, +0.128] | `outputs/results/analyses/phase_ladder/results.csv` · `d_auc_ipcw(_lo/_hi)`; cohort=post_rt, learner=ridge, arm=R2+I2|ridge |
| Post-RT · R3 + I2 vs R3 | +0.017 [−0.069, +0.093] | +0.005 [−0.075, +0.082] | same; arm=R3+I2|ridge |
| Post-RT · R3 + I3 vs R3 | +0.005 [−0.070, +0.075] | +0.024 [−0.030, +0.076] | same; arm=R3+I3|ridge |
| Re-seg · BraTS21 SwinUNETR vs MU masks | +0.030 [−0.008, +0.069] | +0.029 [−0.010, +0.069] | `outputs/results/analyses/reseg/forward_ipcw120.csv` · `d_auc_ipcw_vs_mu`, `d_lo`, `d_hi`; model=clinical+phase+imaging, segmenter=brats21 |
| Re-seg · BrainSegFounder vs MU masks | +0.008 [−0.023, +0.040] | +0.003 [−0.025, +0.032] | same; segmenter=bsf |
| LUMIERE · C+T + volumes vs C+T | −0.001 [−0.073, +0.057] | −0.006 [−0.075, +0.055] | `outputs/results/analyses/baselines/lumiere.csv` · `d_auc_ipcw(_lo/_hi)`; model=clinical + timing + volumes, shared (ridge) |
| LUMIERE · C+T + deep vs C+T | +0.057 [−0.132, +0.235] | +0.064 [−0.011, +0.144] | `outputs/results/analyses/deep/lumiere/locked.csv` · `d_auc_ipcw_vs_baseline`, `d_auc_ipcw_lo`, `d_auc_ipcw_hi`; base=clinical+timing, arm=baseline+deep |
| LUMIERE · C+T+V + deep vs C+T+V | +0.089 [−0.026, +0.215] | +0.050 [+0.002, +0.109] * | same; base=clinical+timing+volumes, arm=baseline+deep |

**Panel C** (`outputs/results/analyses/shap/grade4/groups.csv` · `share`; labels shown when share ≥ 9%):

| Model (`model`) | Shares |
|---|---|
| Baseline ridge (base_ridge) | clinical 25%, timing 17%, treatment 58% |
| Baseline GBM (base_gbm) | clinical 35%, timing 14%, treatment 51% |
| B + volumes/morph./delta, ridge (full_ridge) | clinical 13%, timing 7%, treatment 34%, volumes 10%, morphology 21%, delta 14% |
| B + volumes/morph./delta, GBM (full_gbm) | clinical 21%, timing 3%, treatment 26%, volumes 13%, morphology 23%, delta 13% |
| B + radiomics score, legacy PCA-10 stack (rad_ridge) | clinical 20%, timing 16%, treatment 48%, radiomics 16% |

Imaging share 45% / 51% (full ridge / GBM) and 23% (rad_ridge): `shap/grade4/imaging_share.csv` · `imaging_share`.
The rad_ridge model is the post-hoc single configuration (OOF AUC 0.721, `shap/grade4/model_auc.csv`).

## Figure 4. Phase of care

**Caption draft.** *(A) Non-imaging bases (ridge, grade 4) in the full cohort (249 scans), the post-RT cohort (RT
completed; 167 scans, 84 patients, 83 events) and the later post-RT cohort (> 12 weeks after RT end; 69 scans), each
trained and evaluated within the cohort under 5×5 CV. R0 clinical; R1 + timing; R2 + a 4-level phase-of-care block;
R3 = baseline (clinical + timing + treatment). In the later post-RT cohort the bases fall below 0.5, the expected
small-sample anti-learning of a near-null model, so ΔAUCs there are not interpretable. (B) ΔAUC from adding each
imaging block to each base within post-RT grade-4 scans (paired cluster bootstrap 95% CI). Diamond = the
pre-specified primary contrast (R2 + all non-radiomics imaging vs R2): +0.061 [−0.038, +0.156], permutation
p = 0.21; the permutation null itself averages +0.03.*

| Number shown | Value | Source |
|---|---|---|
| A: AUC [CI] per base × cohort | full R0 0.585, R1 0.644, R2 0.664, R3 0.698; post_rt 0.552, 0.572, 0.549, 0.604; later_post_rt 0.343, 0.388, 0.376, 0.472 (CIs in `fig4_phase.csv`) | `outputs/results/analyses/phase_ladder/results.csv` · `auc_ipcw`, `auc_ipcw_lo`, `auc_ipcw_hi`; population=grade4, learner=ridge, arm=R{0..3}|ridge |
| A: scans per cohort | 249 / 167 / 69 | same · `n_scans` (also `phase_ladder/cohorts.csv`) |
| B: Δ [CI] per base × imaging | R0: +0.049, +0.058, +0.046, +0.079; R1: +0.030, +0.038, +0.042, +0.060; R2: +0.044, +0.061, +0.061, +0.076; R3: +0.008, +0.017, +0.005, +0.039 (I1–I4; CIs in `fig4_phase.csv`) | same · `d_auc_ipcw`, `d_auc_ipcw_lo`, `d_auc_ipcw_hi`; cohort=post_rt, arm=R{b}+I{k}|ridge |
| B: primary | +0.061 [−0.038, +0.156] | same; arm=R2+I2|ridge |
| B: permutation p | 0.21 (0.208 = 21/101) | `outputs/results/analyses/phase_ladder/permutation.csv` · `p_value` |

## Table 2. Single split vs repeated CV, same models

Files: `docs/manuscript/figures/table2_single_split_vs_cv.{md,csv}` (= `outputs/results/analyses/paper_figures/`).

**Caption draft.** *The same models scored three ways: on the PRISM report split alone (all gliomas; IPCW AUC with
patient-cluster bootstrap CI and paired Δ vs baseline ridge), across 500 splits of the PRISM report design (naive and
IPCW AUC; for the PRISM report model this is its pipeline with features re-selected per split), and under 5×5
repeated patient-grouped CV on the verified-label cohort (all gliomas, and grade 4). Single-split IPCW AUCs are 0.10–0.16
above the all-glioma repeated-CV values for every model, and the single-split differences between models lie
within their CIs. "Not run": the
split-variance analysis did not include that model. The PRISM report model is a fixed, shipped model and has no
repeated-CV analogue. Note that the split-variance and single-split AUCs use the naive label and a different cohort
definition (PRISM report case table), so their absolute level is not comparable with the CV column.*

| Cell | Source |
|---|---|
| Single split columns | `paper_figures/single_split.csv` · `auc_naive`, `auc_ipcw(_lo/_hi)`, `d_auc_ipcw_vs_baseline`, `d_auc_ipcw_lo`, `d_auc_ipcw_hi`; subset=all |
| 500-split columns | `split_variance/summary_clipped.csv` · `mean`, `sd`, `p2.5`, `p97.5`; PRISM report model → model=prism_reselect, Baseline ridge → baseline, + radiomics → baseline_rad (clipped) |
| 5×5 CV, baseline ridge / GBM / + legacy radiomics | `outputs/results/c3/{all_glioma,grade4}/results.csv` · `auc_ipcw`, `auc_ipcw_lo`, `auc_ipcw_hi`; rows (NaN)|none|none|none|ridge, (NaN)|none|none|none|gbm, legacy|none|top10|concat|ridge |
| 5×5 CV, clinical only | `phase_ladder/results.csv` · same columns; cohort=full, arm=R0|ridge (= `baselines/ladder.csv` clinical only) |

Values: single split naive / IPCW [CI] / Δ — PRISM report model 0.802 / 0.817 [0.690, 0.920] / −0.034 [−0.186, +0.109];
baseline ridge 0.871 / 0.851 [0.735, 0.947]; baseline GBM 0.844 / 0.824 [0.690, 0.916] / −0.027 [−0.127, +0.062];
+ legacy radiomics 0.862 / 0.845 [0.746, 0.936] / −0.006 [−0.081, +0.090]; clinical only 0.791 / 0.782 [0.638, 0.897] /
−0.069 [−0.215, +0.058]. 500 splits naive (IPCW): PRISM re-selected 0.720 ± 0.055 (0.727 ± 0.058); baseline 0.801 ±
0.052 (0.769 ± 0.056); + radiomics 0.799 ± 0.053 (0.774 ± 0.058). 5×5 CV all gliomas / grade 4: baseline ridge 0.720 /
0.698; GBM 0.718 / 0.687; + legacy top-10 0.743 / 0.703; clinical 0.619 / 0.585.

## Open issues

- `docs/results/SPLIT_VARIANCE.md`, `FINAL_RESULTS.md`, `IMAGING_VS_NONIMAGING.md` still quote the pre-clip
  `baseline_rad` and head-to-head radiomics numbers; the clipped values are above. `split_variance.png` (old figure)
  still shows the pre-clip arm.
- `c3/prism_report_split/head_to_head.csv` radiomics rows (two-level texture, corrected compartments) were not re-run
  with the clip; only the legacy top-10 row (used here) was.
- Figure 2 B shows one composition measure; the full set of correlates is in `split_auc_vs_composition.csv`.
- The forest (Fig 3B) mixes references by section; the section headings state each reference. The 32 intervals are
  uncorrected (3 exclude 0).
