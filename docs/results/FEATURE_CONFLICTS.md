# Feature conflicts: do features work against each other?

Question: are some features or feature groups hurting the model, by collinearity, sign flips or by colliding encodings?
Module `prism/analyses/feature_conflicts.py` (`python -m prism.analyses.feature_conflicts --radiomics`, 32 workers, about 2
min). Outputs are in `outputs/results/analyses/feature_conflicts/`. The protocol matches C3: verified 120-d labels (death
censored), shared 5×5 patient-grouped folds, in-fold median imputation + missing indicators + scaling, ridge
(`formulations.fit`, inner C) and the C3 boosting model. Headline = mean over repeats of the pooled-OOF IPCW AUC(120 d), with
paired 1000-draw patient-cluster bootstrap CIs for every contrast. B = clinical + timing + treatment (reproduces C3: ridge
0.698 grade 4 / 0.720 all gliomas). F = B + volumes + morphology + delta (no radiomics).

The module was re-run on 2026-10-11 at 18:52, after the radiomics clipping fix ([FIX_RADIOMICS_CLIP.md](FIX_RADIOMICS_CLIP.md)).
The group, interaction and pruning contrasts (`contrasts.csv`, `interactions.csv`) and the correlation and VIF counts
(`corr_pairs.csv`, `vif.csv`) were re-checked against the new outputs and are unchanged. The module does not use
`c3.selector`.

Caveat: the "B+radiomics (legacy)" row feeds all 2446 raw legacy columns through median imputation + `StandardScaler`
without clipping. It therefore still includes the 1e6 sentinel values in 3 FLAIR NGTDM Coarseness columns (2 grade-4
scans, 4 overall). Treat that row, and its calibration slope of 0.34, as an unclipped reference only.

## Bottom line

- **No feature group measurably hurts.** Leave-one-group-out from F: every "removal raises AUC" contrast has a CI that
  includes 0. The largest is timing, which is redundant given treatment (below). Adding any imaging group to B changes AUC by
  −0.004 to +0.019, and all CIs span 0.
- **The real conflict is redundancy, not antagonism.** Timing and treatment encode the same RT-status information. Their
  interaction is −0.066 to −0.073, and the CI excludes 0 in 3 of 4 population × learner cells. Within B, the ridge has 9
  exactly collinear columns (VIF = ∞), which split the "RT completed" signal into coefficients near 0.
- **Pruning by a pre-stated rule does not help** when it is evaluated honestly (nested): ΔAUC vs B ranges from −0.018 to
  +0.011, and all CIs span 0. The same rule applied once to the whole dataset gives +0.009 to +0.018. That gap is selection
  optimism.

## (a) Group level (`group_sets.csv`, `contrasts.csv`, `interactions.csv`)

ΔAUC [95% CI]. A positive value in a "−g" row means group g hurts.

| Contrast | G4 ridge | G4 GBM | All ridge | All GBM |
|---|---|---|---|---|
| B (AUC) | 0.698 | 0.687 | 0.720 | 0.718 |
| F − B | −0.007 [−0.073, 0.057] | +0.007 [−0.066, 0.073] | +0.008 [−0.041, 0.056] | +0.022 [−0.036, 0.085] |
| B+volumes − B | +0.004 [−0.055, 0.059] | +0.007 [−0.055, 0.068] | +0.013 [−0.030, 0.057] | +0.019 [−0.034, 0.073] |
| B+morphology − B | −0.004 [−0.069, 0.056] | +0.002 [−0.064, 0.069] | +0.011 [−0.031, 0.054] | +0.015 [−0.044, 0.073] |
| B+delta − B | +0.001 [−0.039, 0.037] | +0.019 [−0.020, 0.057] | +0.004 [−0.025, 0.032] | +0.016 [−0.015, 0.048] |
| F−clinical − F | −0.013 [−0.035, 0.007] | −0.042 [−0.076, −0.006] | −0.013 [−0.032, 0.003] | −0.037 [−0.065, −0.006] |
| F−timing − F | +0.006 [−0.005, 0.018] | +0.006 [−0.000, 0.012] | +0.004 [−0.004, 0.013] | −0.001 [−0.008, 0.005] |
| F−treatment − F | −0.022 [−0.051, 0.007] | −0.028 [−0.062, 0.008] | −0.010 [−0.031, 0.009] | −0.025 [−0.053, −0.001] |
| F−volumes − F | −0.001 [−0.013, 0.012] | +0.005 [−0.009, 0.020] | +0.001 [−0.011, 0.012] | +0.004 [−0.007, 0.013] |
| F−morphology − F | +0.003 [−0.022, 0.030] | +0.007 [−0.021, 0.035] | −0.001 [−0.019, 0.018] | +0.004 [−0.017, 0.025] |
| F−delta − F | +0.005 [−0.014, 0.027] | −0.014 [−0.039, 0.010] | +0.009 [−0.008, 0.029] | −0.007 [−0.023, 0.009] |
| B−timing − B | +0.008 [−0.023, 0.035] | −0.002 [−0.021, 0.016] | −0.001 [−0.022, 0.020] | +0.002 [−0.015, 0.017] |
| B−treatment − B | −0.054 [−0.103, −0.012] | +0.006 [−0.047, 0.059] | −0.027 [−0.061, 0.007] | +0.011 [−0.025, 0.045] |
| B+radiomics (legacy) − B | −0.018 [−0.113, 0.070] | −0.025 [−0.119, 0.060] | −0.012 [−0.084, 0.061] | +0.009 [−0.070, 0.092] |

Timing removal from F nominally raises AUC in 3 of 4 cells. The only near-significant case is G4 GBM (+0.006, p(Δ ≤ 0) =
0.034, CI lower bound −0.000), which is borderline and not robust. Legacy radiomics lowers the ridge calibration slope to
0.34 (G4).

**Additivity**, interaction = Δ(A+B) − Δ(A) − Δ(B):

- **Imaging pairs on B:** −0.001 to −0.020, all CIs span 0. The imaging groups overlap mildly but do not interfere.
- **Timing × treatment on clinical:**
  - G4 ridge −0.067 [−0.134, 0.002]
  - G4 GBM −0.066 [−0.116, −0.013]
  - all-glioma ridge −0.073 [−0.133, −0.012]
  - all-glioma GBM −0.066 [−0.115, −0.018]

  Either group alone carries almost all of the gain. In G4 ridge, clinical + treatment (Δ +0.121 over clinical) is higher
  than clinical + timing + treatment (Δ +0.113).

## (b) Feature level (`corr_pairs.csv`, `corr_clusters.csv`, `vif.csv`, `coef_signs.csv`, `redundant_pairs.csv`)

The design matrix is F after imputation + missing indicators: 83 columns (G4) / 84 (all gliomas).

**Collinearity**

- 125 (G4) / 113 (all) pairs have |Spearman r| > 0.8; 86 / 78 of them have |r| > 0.9. They form 13 clusters in G4. The
  heatmap is `corr_clusters_grade4.png` (and `_all_glioma.png`).
- VIF on the G4 F design: 20 columns have VIF = ∞ (exact linear dependence) and 54 have VIF > 10.
- VIF within the B design (31 columns): 9 columns have VIF = ∞ and 16 have VIF > 10.

**Exact or near-exact redundant encodings (G4)**

- rt_date_unknown = 1 − rt_completed, and both are identical to the missing indicators of days_since_rt_end and
  rt_duration_days (r = ±1).
- visit_index = n_prior_scans + 1 (R² = 1). has_prior vs visit_index: r = 0.94.
- days_from_diagnosis is predicted by rt_start_day + days_since_rt_end + rt_date_unknown with R² = 0.79. The RT end day
  identity (diagnosis-to-scan − days since RT end = RT start + RT duration) holds on all 167 scans that have both.
- days_from_diagnosis vs visit_index: r = 0.73, R² = 0.38. Not redundant.
- rt_fractions ~ dose + hypofractionation: R² = 0.99. chemo_started vs rt_started: R² = 0.96.
- log_tumor_cc = log1p(ET + NETC) exactly; vs log_et_cc alone r = 0.98. log_lesion_cc vs log_snfh_cc: r = 0.97.
- logratio_tumor vs logratio_et: R² = 0.996.

**Sign flips.** A flip is a multivariable-ridge sign that differs from the univariate-ridge sign, both computed over 25 fold
fits. A flip is "stable" when ≥ 80% of fits agree in both models.

- **In B:** no stable flips in G4. One in all gliomas: mgmt_methylated, univariate +0.035 vs B −0.050 (8% of fits
  positive). In G4 mgmt_methylated is univariately null (60% sign stability) but −0.060 in B (4% positive).
- **Collinearity-induced sign collapse in B (G4):**
  - rt_completed: univariate +0.43 (100% stable) vs B −0.002 (56% positive).
  - rt_date_unknown: −0.43 vs +0.002.

  Their signal is shared with rt_started (+0.16), the missing indicators (rt_dose, rt_fractions and
  rt_hypofractionated missing: each −0.090) and chemo_started (+0.11).
- **In F:** 5 stable flips per population, all small imaging features with |coefficient| ≤ 0.04:
  - G4: et_cavity_distance, logratio_netc_cc, logratio_snfh_cc, d_t1c_et_rel, d_flair_snfh_rel.
  - All gliomas: mgmt_methylated, et_near_cavity_fraction, et_cavity_distance, logratio_netc_cc, logratio_snfh_cc.

  These are suppression effects inside the delta and volume clusters (e.g. logratio_snfh against logratio_lesion). They do not
  cost AUC.
- **Univariate CV AUC is below 0.5 for many weak features** (e.g. days_from_diagnosis 0.42, male 0.40). This is typical of
  near-null predictors under CV, so the univariate sign is taken from the coefficient and the Spearman r instead.

## (c) Treatment × timing (`treatment_timing.csv`)

All of the following hold on 100% of scans unless a share is given:

- rt_date_unknown ⇔ ¬rt_completed.
- days_since_rt_end missing ⇔ ¬rt_completed.
- early_post_rt = 1 ⇒ rt_completed.
- rt_completed ⇒ rt_started.
- rt_dose missing ⇔ ¬rt_started (97% G4).
- chemo_started = rt_started (99% G4 / 97% all).

So a single bit, "RT completed by the scan", appears in at least 5 columns. "RT started" and "chemo started" add a near-copy of
a second bit. The ridge spreads the weight across these columns. That is harmless for AUC (dropping all timing: Δ +0.008
[−0.023, 0.035] in G4 ridge) but makes single coefficients uninterpretable.

## (d) Pruning (`pruning.csv`, `pruning_choices.csv`, rule printed in the module as `PRUNE_RULE`)

The rule was stated before evaluation:

1. Drop constant columns.
2. Greedily keep a column only if its |Spearman r| ≤ 0.9 with every column already kept. Priority: original columns before
   missing indicators, then the group order clinical > timing > treatment > volumes > morphology > delta, then column
   order.
3. Drop each imaging group whose removal raises inner 3-fold AUC.

P_base is steps 1–2 applied to B. Nested evaluation means the whole rule is fitted inside each outer training fold.

| ΔAUC vs B | G4 ridge | G4 GBM | All ridge | All GBM |
|---|---|---|---|---|
| P_base, nested | −0.007 [−0.018, 0.004] | −0.000 [−0.006, 0.007] | −0.001 [−0.010, 0.009] | −0.003 [−0.008, 0.002] |
| P_full, nested | −0.013 [−0.069, 0.038] | −0.018 [−0.063, 0.028] | −0.005 [−0.043, 0.033] | +0.011 [−0.029, 0.053] |
| P_full, global (exploratory, optimistic) | +0.009 [−0.044, 0.062] | +0.017 [−0.021, 0.052] | +0.018 [−0.028, 0.061] | +0.015 [−0.014, 0.045] |

- P_base cuts B from 31 to about 21 columns with no loss of AUC (calibration slope 0.857 vs 0.886, G4 ridge). It is a
  simpler, equivalent baseline, not a better one.
- Nested group dropping is unstable: in G4 ridge, delta is dropped in 72% of folds, volumes in 40% and morphology in 40%.
- The global variant picks the groups to drop from the outer-CV LOGO table, so it leaks test-fold information and is
  optimistic.
