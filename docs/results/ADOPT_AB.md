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

## Results

(Added after the reruns.)
