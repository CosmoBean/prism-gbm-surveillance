**Not adopted (2026-11-20, author's decision).** PRISM keeps its current models: I_pure for imaging, B1 + I_pure combined, the reduced forms externally, and the released masks, exactly as before 2026-11-19. This note and `prism/analyses/adopt_ab.py` record what adopting A and B would have changed, as a design analysis only. The adoption commits were reverted (code at 914ba1f reproduces these results; `adopt_ab.py` needs `system.mu_predict` / `mu_oof` from that commit). The A/B outputs are in `outputs/results/analyses/_AB_design_2026-11-19/`.

# Adopting the stratified imaging model (A) and the offset combined model (B)

Date: 2026-11-19. Decision: the author adopts the two S2 models as PRISM's imaging and combined models. Adoption
follows the section "What would change in the system, if the author adopts them" of the S2 plan
(`docs/results/STRATIFIED_OFFSET_PLAN.md`, commit 1856aa9). The S2 results are in `docs/results/STRATIFIED_OFFSET.md`
(commit 6eb9e43) and the code is `prism/analyses/stratified_offset.py`.

This note is committed before any downstream stage is rerun. The results section is added after the reruns.

## The models

- **A, the stratified imaging model**, replaces the imaging model at every centre, with the same per-centre design as
  now:
  - MU and UCSF use A-Ipure (27 inputs);
  - LUMIERE uses the T_img analogue, with the 3-volume model for scans that have no previous scan.
  - All are fitted on MU with one unpenalised intercept per MU time window (before the end of radiotherapy, within 12
    weeks after it, later, unknown). The fit is `stratified_offset.fit_A`.
- **B, the offset combined model**, replaces the combined model: logit p = η_baseline + b₀ + β·z.
  - η_baseline is the logit of the timing-and-enhancement baseline, fitted on the same training rows and entered as a
    fixed offset. The fit is `stratified_offset.fit_B`.
  - On MU, z holds the current combined model's inputs.
  - Externally B uses the reduced form T, with the locked reduced baseline (early_post_rt, log ET, log ET ratio,
    has_prev) as the offset.
- **The clinical-history model is unchanged.**

## Implementation rules (fixed before any rerun)

1. **Ranking and agreement.** AUCs and the agreement statement use A's within-window score, β·x_img, with no window
   intercept. The agreement statement is score > cohort median. The median is taken over the same set of scans as
   now: MU, all labelled detection scans per repeat; LUMIERE, all detection scans; UCSF, the scan-2 evaluation set.
   The combined model's AUCs use B's probability p.
2. **The imaging probability in the record** is sigmoid(MU window intercept + β·x_img). It uses the scan's window
   where the window is known, and the "unknown" intercept otherwise, as in the S2 exploratory calibration.
   - **MU:** the scan's window, the card's phase cell (`system.mu_situation`). Out of fold, the intercepts come from
     the training fold's fit.
   - **LUMIERE:** the "unknown" intercept for every scan. LUMIERE records no radiotherapy dates, and its card phase
     is "unknown".
   - **UCSF:** the scan's approximated window, the card's phase cell from `rt_phase` (a six-week course is assumed).
     A scan whose `rt_phase` maps to no window gets "unknown".
   - The MU "before the end of radiotherapy" window holds no progression in training. Its intercept is about −15 on
     the logit scale, so scans in that window show an imaging probability near 0.
3. **The card and the agreement statement in the record.** The card shows the scan's imaging probability. Beside it,
   the card shows the cohort median of the within-window score, mapped to the scan's window:
   sigmoid(a_window + median of β·x_img).
   - Because the sigmoid is monotone and the scan's own intercept is used, "probability > mapped median" holds exactly
     when "score > cohort median" holds. The agreement decision is therefore rule 1's.
   - This keeps the existing facts views (`facts_v3_1`, `facts_v3_2`) and the prompts unchanged, with every displayed
     number between 0 and 1.
   - The record also stores the raw within-window score, its cohort median and the window intercept.
4. **New record fields**, in a new block `model`, next to `scores`:
   - `model.images`: `within_window_score`, `cohort_median_within_window_score`, `window`, `window_intercept`,
     `probability` (= `scores.images`) and `source`;
   - `model.combined`: `score` (= `scores.combined`), `increment` (β·z, logit scale), `baseline_logit` (η_baseline),
     `intercept` (b₀) and `source`.
   - The language model's facts views do not read this block, so the reports do not use it.
5. **Conformal sets.**
   - **Combined set:** uses B, refitted inside the same 70/30 proper-training / calibration patient split as
     `system.py` uses now (MU: inside each outer training fold, seed 10·repeat + fold; external: one MU split, seed
     0). Calibration scores are B's probabilities on the calibration rows.
   - **Imaging set:** uses A's probability (rule 2), refitted the same way. Calibration rows use their own MU windows.
     External scans use the window of rule 2.
   - The cost-of-splitting AUC of the imaging model uses the conformal fit's within-window score.
6. **Everything else stays exactly as it is now.** This covers the folds, seeds, bootstrap sizes, flags, card rules,
   tier rule, report model, prompt, seed and checker.
   - The UCSF-trained models (`ucsf_internal`, card cohort "ucsf_internal") are not PRISM's locked models and are
     unchanged.
   - Provenance model strings in the record (which describe the inputs) are unchanged, so the facts views map them
     as before. A new `provenance.objective` entry names A and B.
7. **Reference values.** `system.EXPECTED` is replaced by the new values. The system's MU, LUMIERE and UCSF imaging
   and combined AUCs must equal the S2 results to two decimals (MU A 0.67, B 0.81; LUMIERE A 0.64, B 0.75; UCSF A 0.77,
   B 0.87). The scores must also equal S2's `scores.npz` scan by scan. Otherwise the run stops.

## Backup

Before anything was overwritten, the current outputs were copied to `outputs/results/analyses/_pre_AB_2026-11-19/`.

## Results (2026-11-19 to 2026-11-20)

### What was rerun

Everything ran on Slurm allocation 173345 (26 CPUs, 1 H100), in dependency order. Logs are in `logs/adopt_ab/`.

1. **Card table.** `reliability_card --steps table`. Its MU, LUMIERE and locked-UCSF scores now come from
   `system.mu_predict`, `lumiere_cohort` and `ucsf_cohort`. The steps `records` and `evaluate` were not run, because
   they act on the report sets from before v3, which are not on disk.
2. **System.** `system`: scores, records and S1-S4.
   - The system's A and B scores equal S2's `scores.npz` scan by scan at every centre, with a maximum deviation of 0.
   - The combined sets at α 0.2 equal S2's B sets exactly.
   - The clinical-history scores equal the published ones (≤ 1.1 × 10⁻¹⁶).
3. **Analyses on the system's scores.**
   - `methods` (M1, M2) and `methods_extra` (E1, E2);
   - `clinician_baseline` (E4), `mask_sensitivity` (E5) and `review_analyses` (E6);
   - `revision_data` (R1, R2);
   - `christodoulou_faithful evaluate`, on the released masks and on the BraTS21 masks. A's out-of-fold score was added
     as an arm, and the bootstrap draws are unchanged;
   - the new `adopt_ab`: headline AUCs and CIs with each cohort's published bootstrap. The old values reproduce the
     published ones exactly (asserted).
4. **Reports.** Same model (Qwen3.8-27B, revision 1d4bf0f2, vLLM 0.31.0, bf16, greedy, seed 0, non-thinking), same
   prompts and the same frozen checker (blob 26d6637a). The prompt was not changed.
   - **v3.2 pipeline** (MU and LUMIERE; prompts v3.4 and v3.5): select, sets, requests, freeze, generate and evaluate
     on dev and eval. The freeze hashes are identical to those of 2026-11-13.
   - **v3.1 three-cohort run** (the 406 reports the paper cites; prompt v3.4): eval and stress.
     - The selection files lost on 2026-11-02 were redone by their deterministic rules: `report_v3/dev_patients.json`
       and `report_v3_1/dev_patients_v3_1.json`.
     - The 30-record perturbation set was redrawn by its rule (seed 1). It has 7 MU, 13 LUMIERE and 10 UCSF records,
       the same per-cohort counts as before.
5. **Verifier and checker.** `verifier_mutation` (synthetic and real v3.2 and template reports) and
   `verifier_independent`. `checker_mutation` was not rerun: it uses only synthetic records, which do not depend on the
   models.
6. **Figures.** Regenerated: fig2_performance (values updated from the outputs above), fig3_context_split,
   fig4_group_conformal (`generate_methods_figures.py`), fig_case_strips, fig_cohorts and fig5_report.
   `fig1_system.*` and `scripts/fig1_prism.py` were not touched.

### Reference values: `system.EXPECTED`, old → new

| key | old | new |
|---|---|---|
| MU grade 4 intended use, images | 0.709 | 0.6688 |
| MU grade 4 intended use, combined | 0.821 | 0.8137 |
| MU grade 4 all scans, images | 0.712 | 0.6688 (0.66875) |
| LUMIERE, images (3-volume model where no previous scan) | (not checked; 0.6539) | 0.6421 |
| LUMIERE, combined | 0.773 | 0.7537 |
| LUMIERE, images, T_img on all scans | 0.655 | 0.6414 |
| UCSF scan 2, images | 0.726 | 0.7690 |
| UCSF scan 2, combined | 0.856 | 0.8681 |
| clinical-history keys (MU 0.822 / 0.845 / 0.814, LUMIERE 0.689, UCSF 0.561) | unchanged | unchanged |

`reliability_card.EXPECTED` follows the same values (mu images 0.712 → 0.6688; lumiere images 0.655 → 0.6414, both
0.773 → 0.7537; ucsf_locked images 0.726 → 0.7690, both 0.856 → 0.8681), and gains mu both 0.8440, which was not
checked before.

**Sanity check against S2 (two decimals): passed.** MU A 0.6688 (S2 0.67), B 0.8137 (0.81); LUMIERE A 0.6421 (0.64),
B 0.7537 (0.75); UCSF A 0.7690 (0.77), B 0.8681 (0.87).

### Headline numbers, old → new

Sources:
- AUCs: `outputs/results/analyses/adopt_ab/auc_old_new.csv`, with the paper's bootstraps (MU 1,000 draws, seed
  20261021, intended use; LUMIERE the same; UCSF 1,000 draws, seed 20261025).
- Gains: `clinician_baseline/e4_reader_baseline.csv` (2,000 draws).
- Coverage: `system/conformal.csv` and `adopt_ab/conformal_old_new.csv`.

| quantity | old | new |
|---|---|---|
| MU imaging AUC | 0.709 (0.630–0.781) | 0.669 (0.580–0.741) |
| MU combined AUC | 0.821 (0.744–0.894) | 0.814 (0.733–0.895) |
| MU baseline AUC (E4) | 0.797 (0.706–0.880) | unchanged |
| LUMIERE imaging AUC (system, 3-volume model where no previous scan) | 0.654 (E4: 0.566–0.731) | 0.642 (0.544–0.734) |
| LUMIERE imaging AUC, T_img on all scans (paper's 0.65) | 0.655 (0.565–0.733) | 0.641 (0.541–0.734) |
| LUMIERE combined (reduced) AUC | 0.773 (0.679–0.857) | 0.754 (0.664–0.827) |
| LUMIERE baseline AUC (E4) | 0.734 (0.641–0.812) | unchanged |
| UCSF imaging AUC | 0.726 (0.603–0.835) | 0.769 (0.660–0.870) |
| UCSF combined (reduced) AUC | 0.856 (0.758–0.930) | 0.868 (0.781–0.940) |
| UCSF baseline AUC (S1 / S2; not in the paper) | 0.866 | unchanged |
| MU combined − baseline (E4) | +0.023 (−0.034 to +0.083) | +0.016 (−0.021 to +0.048) |
| LUMIERE combined − baseline (E4) | +0.039 (−0.014 to +0.100) | **+0.019 (+0.003 to +0.043)** |
| MU imaging − baseline (E4) | −0.088 (−0.192 to +0.020) | −0.129 (−0.232 to −0.033) |
| LUMIERE imaging − baseline (E4) | −0.080 (−0.162 to −0.002) | −0.092 (−0.183 to −0.010) |
| Conformal coverage, combined, α 0.2: MU / LUMIERE / UCSF | 0.823 / 0.871 / 0.783 | **0.800 / 0.764 / 0.739** |
| Conformal coverage, imaging, α 0.2: MU / LUMIERE / UCSF | 0.844 / 0.708 / 0.826 | 0.799 / **0.590** / **0.652** |
| Conformal coverage, clinical-history, α 0.2 | 0.795 / 0.798 / 0.696 | unchanged |
| Combined set, single outcome, α 0.2: MU / LUMIERE / UCSF | 0.752 / 0.624 / 0.638 | 0.804 / 0.809 / 0.899 |
| Reports passing the checker, v3.1 (MU / LUMIERE / UCSF) | 114/114, 162/162, 130/130 (406/406) | 114/114, 162/162, 130/130 (406/406) |
| Tier stated where required (S6) | 220/220 | 220/220 |
| Perturbed records followed (S7, rule ≥ 27) | 28/30 | **27/30** (agreement 5/6, ET change 4/6, others 6/6) |
| Reports v3.2 passing (MU / LUMIERE); v3.1 rerun inside v3.2; template | 114/114, 162/162; 276/276; 276/276 | unchanged |
| Verifier false rejections, language-model v3.2 reports | 1 of 276 (MU 1/114) | **2 of 276 (MU 2/114, rule V2)** |
| Verifier false rejections, template; development reports | 0 of 276; dev LM 47/48, template 48/48 | 0 of 276; dev LM 48/48, template 48/48 |

### Every number in `paper/main.tex` that changed

The numbers are listed in the order they appear in the text, and each old value is the one main.tex states. Numbers
that do not depend on the imaging or combined model are unchanged and not listed. These include the clinical-history
model, the baseline, the published pipeline's own AUC, enhancing volume, cohort counts, tier shares (37%, 89%, none)
and images from one scan.

| where | old (main.tex) | new | source |
|---|---|---|---|
| Abstract | reduced combined model 0.77 at LUMIERE | 0.75 (0.754) | adopt_ab/auc_old_new.csv |
| Abstract | 0.86 at UCSF-ALPTDG | 0.87 (0.868) | same |
| Abstract | "the combined model added no clear gain over a baseline … (AUC 0.80)" (MU) | still no clear gain at MU: +0.016 (−0.021 to +0.048) | e4_reader_baseline.csv |
| Abstract | 406 reports passed | 406 passed (unchanged) | report_v3_1/summary_eval.csv |
| Table 2, published pipeline below the imaging model on MU | **Yes**, −0.13 (−0.23 to −0.02) | −0.089 (−0.183 to +0.010). Below on the point estimate; **CI includes 0** | christodoulou_faithful/contrasts.csv (CHF − A_I_pure) |
| Table 2, MU masks from another segmenter | No for imaging AUC; Yes for combined, baseline and reading | same reading. Imaging brats21 − released −0.114 (−0.192 to −0.037); combined +0.002 (−0.027 to +0.031); combined − baseline on brats21 +0.038 (−0.006 to +0.077) | mask_sensitivity/e5_mask_sensitivity.csv |
| Table 2, published pipeline below the imaging model on the second masks | **Yes** | **No**: −0.028 (−0.122 to +0.073). The plan's rule (CI below 0) is not met | christodoulou_faithful_brats21/contrasts.csv |
| Table 2, all scans before progression as negatives (each change < 0.05) | No for imaging, −0.054; Yes for the others | No for imaging, −0.062 (−0.103 to −0.018); combined −0.030; clinical-history −0.015; reading unchanged | review_analyses/e6_review_analyses.csv |
| Table 2, unknown IDH / MGMT category (every paired CI includes 0) | Yes | Yes. Combined: MU +0.001 (−0.001 to +0.004), LUMIERE −0.002 (−0.013 to +0.010) | same |
| Table 2, combined at LUMIERE ≥ 0.65 | Yes | Yes (0.754, lower bound 0.664) | adopt_ab |
| Table 2, imaging at UCSF ≥ 0.65, lower bound > 0.5 | Yes | Yes (0.769, 0.660) | adopt_ab |
| Table 2, disagreement marks less well ranked scans | Yes at MU; not LUMIERE or UCSF | same: MU +0.183 (+0.077 to +0.288); LUMIERE +0.112 (−0.033 to +0.278); UCSF −0.016 (−0.222 to +0.170) | system/selective.csv |
| Table 2, combined over the baseline | No clear gain at MU or LUMIERE | **No clear gain at MU; gain at LUMIERE**, +0.019 (+0.003 to +0.043) | e4_reader_baseline.csv |
| Table 2, marginal sets, combined, coverage ≥ 0.78 in each cohort | Yes on point estimates | **No**: MU 0.800 met; LUMIERE 0.764 and UCSF 0.739 not met | system/conformal.csv |
| Table 2 note | imaging at LUMIERE (0.71) and clinical-history at UCSF (0.70) did not meet | imaging at LUMIERE 0.59 and at UCSF 0.65, clinical-history at UCSF 0.70 and the combined model at LUMIERE and UCSF did not meet | same |
| Table 2, reports pass the checker | Yes after one revision | unchanged (406/406) | report_v3_1 |
| 4.1 | imaging model 0.71 (0.63–0.78) | 0.67 (0.58–0.74) | adopt_ab (= christodoulou_faithful/auc.csv A_I_pure) |
| 4.1 | pipeline below imaging by 0.13 (0.02–0.23) | 0.09 (−0.01 to 0.18) | christodoulou_faithful/contrasts.csv |
| 4.1 | on the BraTS21 masks: pipeline below imaging by 0.10 (0.01–0.19) | 0.03 (−0.07 to 0.12) | christodoulou_faithful_brats21/contrasts.csv |
| 4.1 | on these masks the imaging model 0.63 (0.55–0.70) | 0.55 (0.47–0.65) (E5: 0.555, 0.471–0.645) | e5_mask_sensitivity.csv |
| 4.1 | combined model 0.80 (BraTS21 masks) | 0.82 (0.816) | same |
| 4.1 | all scans before progression: clinical-history, imaging, combined 0.81, 0.65, 0.78 | 0.81, 0.61 (0.607), 0.78 (0.784) | e6_review_analyses.csv (E6b secondary) |
| 4.2 | reduced combined 0.77 (0.68–0.86) at LUMIERE | 0.75 (0.66–0.83) | adopt_ab |
| 4.2 | imaging 0.65 (0.56–0.73) at LUMIERE | 0.64 (0.54–0.73) (system, 3-volume model where no previous scan); T_img on all scans 0.64 (0.54–0.73) | adopt_ab |
| 4.2 | UCSF imaging 0.73 (0.60–0.84) | 0.77 (0.66–0.87) | adopt_ab |
| 4.2 | UCSF reduced combined 0.86 (0.76–0.93) | 0.87 (0.78–0.94) | adopt_ab |
| 4.2 | MU combined 0.82, its reduced form 0.80 | 0.81 (0.814); reduced form, B with the reduced baseline as offset, 0.83 (0.833, 0.752–0.907) | adopt_ab; e6 E6d |
| 4.2 | MU calibration slopes about 0.75, CIs including 1 | clinical-history 0.78 (0.38–1.61), imaging (A's probability) 0.85 (0.62–1.18), combined 0.75 (0.45–1.25); all CIs include 1 | e6 E6a |
| 4.2 | calibration intercept of the imaging score at LUMIERE 0.41 | 1.49 (1.24–1.78): A's probability with the "unknown" intercept | e6 E6a |
| 4.2 | slope of the combined model at UCSF 3.3 | 2.03 (B; S2 exploratory calibration, `ucsf_external.calibration`) | stratified_offset/s2_calibration.csv |
| 4.3 | combined above baseline 0.02 (−0.03 to +0.08) MU | 0.02 (−0.02 to +0.05) | e4 |
| 4.3 | 0.04 (−0.01 to +0.10) at LUMIERE, "gains whose CIs include zero" | 0.02 (+0.003 to +0.04). The LUMIERE CI excludes zero | e4 |
| 4.3 | the reading the same with the second masks and with all scans | still no clear gain at MU in both: brats21 +0.038 (−0.006 to +0.077); secondary negatives +0.014 (−0.009 to +0.036) | e5, e6 |
| 4.3 | within one window imaging above the baseline by 0.10 (−0.04 to +0.26) MU | 0.10 (+0.01 to +0.21) (0.101, 0.007–0.206); the CI now excludes zero | e4 |
| 4.3 | imaging 0.68 (0.58–0.77) within a window and 0.73 across, difference includes zero | 0.68 (0.57–0.77) within, 0.66 across; difference −0.01 (−0.13 to +0.10) | methods/m1_auc_split.csv |
| 4.3 | combined 0.65 within and 0.92 across | 0.62 within, 0.94 across | same |
| 4.3 | adding clinical history to images raised the AUC by 0.11 (0.03–0.19) MU, 0.12 (0.04–0.21) LUMIERE, all in pairs across windows | MU 0.14 (0.06–0.24), LUMIERE 0.11 (0.03–0.19). Within-window changes −0.06 (−0.14 to +0.02) and −0.00 (−0.07 to +0.06), so the gain is still across windows | same |
| 4.3 | LUMIERE imaging within 0.71, across 0.51 | 0.70 within, 0.49 across | same |
| 4.3 | UCSF within-window AUCs: combined 0.87, imaging 0.73 | combined 0.87, imaging 0.78 | same |
| 4.4 | combined sets covered 82%, 87%, 78% at MU, LUMIERE, UCSF | 80%, 76%, 74% | system/conformal.csv |
| 4.4 | single outcome for 75%, 62%, 64% | 80%, 81%, 90% | same |
| 4.4 | UCSF: 97% of progression scans, 65% (51%–79%) without progression | 86% (73%–97%) and 65% (50%–79%) | methods/m2_coverage.csv (registered) |
| 4.4 | MU later + increased enhancement covered at 68% (55%–81%) | 68% (50%–84%) | same |
| 4.4 | group calibration lifted that group to 72%; size-matched marginal 74% | 70%; size-matched marginal (α 0.17) 73% | m2_coverage.csv; extra_m2.csv |
| 4.4 | group calibration held both outcomes for 31% of MU sets against 25%, 4% empty | 25% against 19%, 6% empty | m2_levels.csv |
| 4.4 | UCSF least covered group (later, not increased) 61% marginal, 54% within groups | 57% marginal, 64% within groups. Group calibration now lifts it | m2_coverage.csv |
| 4.4 | agreement: combined AUC 0.90 where the models agreed, 0.59 where they disagreed (MU) | 0.86 and 0.68 | system/selective.csv |
| 4.4 | LUMIERE 0.83 against 0.72, interval including zero | 0.82 against 0.71, interval including zero | same |
| 4.4 | at least one flag for 91% of MU scans and 93% at LUMIERE | 90% (0.903) and 92% (0.921) | same |
| Fig. 2 | MU, LUMIERE and UCSF imaging and combined points and gains | redrawn with the values above | scripts/fig2_performance.py |
| Fig. 3, Fig. 4 | the imaging and combined rows and the combined coverage | redrawn | methods outputs |
| Fig. case strips | strip A patient PatientID_0014 | strip A is now PatientID_0033 (selection rule unchanged). Strips B, C, D unchanged (0152, 0029, 0053), so Fig. 5's patient (strip C) is unchanged | fig_case_strips.py |
| 4.5 | 28 of 30 reports followed a changed field | 27 of 30 (rule ≥ 27: met, at the threshold) | report_v3_1/summary_stress.csv |
| 4.5 / Table verifier | the verifier rejected one LM report at MU (Table: "1 of 276"; LM column "275 reports") | 2 of 276 (both MU, rule V2), so the LM column holds 274 | verifier_mutation/false_rejections.csv |
| Table verifier, LM column | direction flipped 194, rewritten 194, FLAIR as enhancing 260, number changed 0.999 (3261), tier word 0.55 (275), diagnosis/advice 1.00 (1375) | 193, 193, 259, 0.999 (3197), 0.57 (274), 1.00 (1370) | verifier_mutation/mutants.csv |
| Table verifier, template column | number changed 0.999 (3264), tier word 0.67 (276) | number changed 0.999 (3210), tier word 0.67 (276) (unchanged rate) | same |
| Discussion | the published pipeline ranked below both of PRISM's separate models, on two sets of masks | for the imaging model the CI includes zero on the released masks (−0.09, −0.18 to +0.01), and the point estimate on the BraTS21 masks is −0.03 (−0.12 to +0.07) | as 4.1 |
| Conclusion | simple models … ranked scans better than the published pipeline | holds for the clinical-history model (−0.24, −0.34 to −0.15). For the imaging model, see above | same |

The synthetic and agent-written columns of the verifier table are unchanged. So are the C2 note and the "Removing the
conformal sentence" caption sentence. The C2 rate changed, however: 0.60 → 0.80 for both writers. The caption's
statement that every report passing without the conformal sentence still stated the set elsewhere was not rechecked.

### Supplement tables and text that changed

- **Table S8 / R1** (`revision_data/r1_conformal.csv`). Each entry gives coverage, progression covered, no progression
  covered, both outcomes and the errors at both and other.
  - MU planned: 0.800, 0.832, 0.776, 19%, 35% and 23%.
  - MU displayed: 0.781, 0.813, 0.757, 8%, 49% and 24%.
  - LUMIERE planned: 0.764, 0.644, 0.848, 19%, 41% and 28%.
  - LUMIERE displayed: 0.713, 0.562, 0.819, 8%, 43% and 29%.
  - Displayed-score sets for the clinical-history model: 0.801 / 0.758 (unchanged). For the imaging model: 0.771 /
    0.590 (was 0.836 / 0.736).
  - **The R1 rule (MU ≥ 0.78 and LUMIERE ≥ 0.75) now fails** at LUMIERE (0.713). It was met before.
- **R2 text**: one MU scan changed tier, the shares are 37% and 89%, and no flag changed. All unchanged.
- **Table S10 (M1)**:
  - MU, imaging 0.67 [0.59, 0.75] / 0.68 [0.57, 0.77] / 0.66 [0.57, 0.76] / −0.01 [−0.13, 0.10];
  - MU, combined 0.81 [0.73, 0.89] / 0.62 [0.47, 0.75] / 0.94 [0.87, 0.98] / 0.32 [0.17, 0.48];
  - LUMIERE, imaging 0.64 [0.54, 0.73] / 0.70 [0.58, 0.80] / 0.49 [0.37, 0.62] / −0.20 [−0.35, −0.04];
  - LUMIERE, combined 0.75 [0.66, 0.83] / 0.69 [0.58, 0.78] / 0.92 [0.83, 0.99] / 0.23 [0.12, 0.37];
  - lower panel: MU combined − clinical-history −0.01 [−0.07, 0.05] / −0.02 [−0.16, 0.11] / 0.00 [−0.04, 0.03];
    MU combined − imaging 0.14 [0.06, 0.24] / −0.06 [−0.14, 0.02] / 0.27 [0.15, 0.39]; LUMIERE combined −
    clinical-history 0.06 [−0.06, 0.16] / 0.10 [−0.07, 0.24] / −0.04 [−0.08, −0.00]; LUMIERE combined − imaging 0.11
    [0.03, 0.19] / −0.00 [−0.07, 0.06] / 0.43 [0.29, 0.57].
  - The text "0.64 and 0.68" (registered within-window audit) still holds (0.64, 0.675).
  - Not caused by A and B: the LUMIERE "enhancing volume alone" row reads 0.56 [0.43, 0.68]. The pre-adoption CSV
    already gave 0.66 [0.56, 0.75], so this row of the supplement was out of date before this rerun.
- **Table S11 (E1)**, AUC within each window, imaging / combined:
  - later 0.64 / 0.58 (was 0.65 / 0.62);
  - early 0.95 / 0.92 (was 0.92 / 0.93);
  - the context-only row is unchanged.
- **Table S12 (M2)**. Each entry gives coverage, progression, no progression, both, empty and worst gap.
  - MU imaging, marginal 0.80 [0.73, 0.86], 0.85, 0.76, 19.5%, 1.5%, 0.11;
  - MU imaging, group-conditional 0.80 [0.74, 0.85], 0.87, 0.74, 24.1%, 4.4%, 0.09;
  - MU combined, marginal 0.80 [0.74, 0.86], 0.83, 0.78, 18.6%, 1.0%, 0.12;
  - MU combined, group-conditional 0.79 [0.73, 0.85], 0.88, 0.73, 24.8%, 5.6%, 0.10;
  - LUMIERE imaging, marginal 0.59 [0.51, 0.65], 0.00, 1.00, 0%, 0%, 0.37;
  - LUMIERE imaging, group-conditional 0.58 [0.50, 0.64], 0.00, 0.98, 0%, 2.2%, 0.37;
  - LUMIERE combined, marginal 0.76 [0.70, 0.82], 0.64, 0.85, 19.1%, 0%, 0.20;
  - LUMIERE combined, group-conditional 0.85 [0.79, 0.90], 0.74, 0.93, 36.5%, 0%, 0.20;
  - the clinical-history rows and the level shares are unchanged.
- **Table S13 (M2 by group, combined; marginal / group-conditional)**:
  - MU early, increased 0.89 / 0.89;
  - MU early, not increased 0.78 / 0.85;
  - MU early, no previous 0.99 / 0.82;
  - MU later, absent 0.73 / 0.73;
  - MU later, increased 0.68 / 0.70;
  - MU later, not increased 0.75 / 0.81;
  - LUMIERE absent 0.81 / 0.81;
  - LUMIERE increased 0.82 / 0.98;
  - LUMIERE not increased 0.74 / 0.89;
  - LUMIERE unknown 0.60 / 0.60.
- **Table S14 (E2)**, for marginal, group-conditional, size-matched (now α 0.17, was 0.175) and outcome-conditional
  sets:
  - coverage 0.80 / 0.79 / 0.82 / 0.79;
  - both 19% / 25% / 24% / 12%;
  - empty 1.0% / 5.6% / 0% / 0.7%;
  - the worst group with at least 9 or 10 scans is now "later, increased" for every set: 0.68 / 0.70 / 0.73 / 0.66.
  - The text's four-group comparison becomes:
    - early, no previous 0.99 / 0.82 / 0.99;
    - later, not increased 0.75 / 0.81 / 0.78;
    - later, increased 0.68 / 0.70 / 0.73;
    - later, absent 0.73 / 0.73 / 0.78.
- **S26.3 (verifier)**:
  - development reports: language model 48 of 48, template 48 of 48 (was 47 of 48);
  - evaluation: 2 of 114 MU language-model reports rejected (rule V2, was 1);
  - Table S15 real-report columns as in the main-text verifier table above, and A2 for the language model 0.96 (274;
    was 0.99).

### Failures and deviations, stated plainly

1. **The published-pipeline margin over the imaging model no longer holds with A.**
   - Released masks: −0.089 (−0.183 to +0.010). The CI includes 0, and the pipeline is below A only on the point
     estimate.
   - BraTS21 masks: −0.028 (−0.122 to +0.073), so the BraTS masks plan's rule (CI below zero) is not met.
   - The comparison with the clinical-history model is unchanged.
2. **S1 coverage of the combined sets fails at LUMIERE (0.764) and UCSF (0.739).** S2 had shown this already
   (exploratory).
   - The imaging sets at LUMIERE cover 0.590: every LUMIERE scan gets "no progression only", so progression coverage
     is 0.
   - This follows from rule 2. LUMIERE scans take the "unknown" intercept (−1.66 in the locked T_img fit), while the
     MU calibration rows are mostly in the later window (+0.57).
   - The same mismatch gives the LUMIERE calibration intercept of 1.49.
3. **The R1 rule now fails at LUMIERE** (0.713 < 0.75).
4. **S7 is 27/30**, exactly at the planned minimum. It was 28/30.
5. **E4 at LUMIERE now shows a gain of the combined model over the baseline** (+0.019, +0.003 to +0.043). The
   paper's "no clear gain at MU or LUMIERE" holds at MU only.
6. **The verifier rejected 2 language-model reports** at MU (rule V2), not adjudicated. It was 1 before.
7. **Not rerun.**
   - The six other ladder models (Fig. 5b, NUMBERS.md 7). Their counts in `fig5_report.py` are from the old records.
   - The checker mutation test (synthetic only).
   - The reliability card's `records` and `evaluate` steps (old report sets not on disk).
   - The UCSF-trained models (`ucsf_internal`), which are unchanged by design.
   - The detection analyses that do not use the system's imaging or combined model (P, I, I_scan, deep arms, UCSF
     Parts A-C).
   - UCSF M1 / M2 were rerun. The baseline at UCSF stays as in S1 / S2.
8. **Implementation choices made here**, beyond rule 1-7:
   - The card's agreement uses the window-mapped median (rule 3), which is exactly the within-window rule (asserted
     scan by scan in `system.build_record`).
   - The reduced combined model on MU (E6d) uses B with the reduced baseline, fitted in the same fold, as its offset.
   - The models with unknown-status indicators (E6c) use B with the same offset as B.
   - The published-pipeline comparison keeps the old I_pure arm and adds A as `A_I_pure`. The BraTS21 A arm is read
     from `mask_sensitivity/preds_brats21.npz`.
   - `fig_case_strips.py` now defines its own `show_scan`. `fig1_prism.py` (commit 9fb7afb, another session) no longer
     has it, and the case strips would not draw without it. The drawing is the same as before.
9. **Records.**
   - A MU scan in the "before the end of radiotherapy" window shows an imaging probability near 0 (intercept −14.8 in
     the locked fit, about −15 in folds).
   - Its card shows the mapped median in the same window, so the agreement text stays correct.
