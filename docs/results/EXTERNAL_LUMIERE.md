# External test on LUMIERE — locked, adapted and cohort-normalised (2026-10-11, final)

**Final numbers** from the final full re-run: `outputs/results/external_lumiere/results.csv` and `locked_predictions.csv`
(2026-10-11 07:22, HEAD `cc2e3a3`; log `outputs/logs/external.log`). This replaces the 2026-10-09 version, whose headline
(grade-4-trained boosting, clinical + timing + volumes, raw 0.719 [0.609, 0.832]) is **no longer supported**: after the label,
treatment, feature and evaluation fixes and the empty-segmentation fix, the same model gives 0.620 [0.495, 0.733].
The shipped PRISM report model rows come from `shipped_model.csv` / `shipped_model_adaptation.csv`, which were **not**
regenerated in the final run (dated 2026-10-09; `scripts/06_external_lumiere.sh --shipped` needs the legacy environment).

Code: `prism/data/lumiere.py` (cohort + labels), `prism/experiments/external_lumiere.py` (shared-feature models),
`legacy/shipped_on_lumiere.py` (shipped PRISM report radiomics model, legacy extraction unchanged).
Data: LUMIERE (Suter et al., Sci Data 2022; CC0) — 91 GBM patients, expert RANO per timepoint.

## Endpoint harmonisation
- Index scans: rated follow-ups (SD/PR/CR/Post-Op, ≥ week 2 after surgery) before the first RANO PD → **132 scans / 61 patients**
  (`docs/manuscript/FLOW.md`).
- Label (H = 120 d): PD within 120 d = 1; a later rated scan ≥ 120 d on without PD = 0; death without PD censors; otherwise
  censored → **47 positive, 76 negative, 9 censored** (`outputs/logs/lumiere.log`).
- Differences from MU: progression = expert RANO PD on imaging (MU: EMR-documented, imaging and/or clinical); time = weeks since
  surgery; no treatment fields (RT dates/dose/chemo) → MU's treatment block cannot be transported.
- Shared features: age, sex, IDH/MGMT (with unknown), log days since surgery, < 3 months post-RT flag (MU: ≤ 12 weeks after RT
  end), log ET / necrosis+cavity / SNFH volumes (LUMIERE: DeepBraTumIA, atlas space; `FIX_FEATURES.md` §1–2).
- **Volume caveats:** DeepBraTumIA labels the resection cavity as necrosis, and its volumes are on a different scale from MU's
  (`FIX_FEATURES.md`). 11 DeepBraTumIA studies have an all-empty segmentation; their volumes are now missing (imputed in-model)
  instead of 0 cc; 14 of 132 index scans have no volumes.

## Arms
| Arm | Meaning |
|---|---|
| MU CV | MU repeated patient-grouped CV (internal reference; mean over repeats of pooled-OOF IPCW AUC) |
| Locked | Trained on all MU scans, applied unchanged to LUMIERE |
| Recalibrated | Locked model + intercept/slope refit on other LUMIERE patients (ranking unchanged) |
| Fine-tuned (shrink) | Ridge refit on LUMIERE training patients, penalised towards MU coefficients (ridge only) |
| Fine-tuned (pooled) | Retrained on MU + LUMIERE training patients (LUMIERE weight 3) |
| LUMIERE only | Trained within LUMIERE (local ceiling) |
| Cohort-norm rank / z-score | Sensitivity (volume feature sets only): locked model with the volume columns re-expressed within each cohort (rank or z-score; MU on its training population, LUMIERE on all index scans, never using labels). Removes segmenter scale differences by construction. |

Every LUMIERE arm is scored on the same 5×5 patient-grouped LUMIERE folds: per-fold IPCW AUC averaged over 25 folds,
patient-cluster bootstrap CI, ΔAUC paired vs locked (`FIX_EVALUATION.md` §2). Locked and cohort-norm arms are also reported
pooled on all 132 scans. O/E = `oe_ratio_pooled` (Kaplan–Meier risk of all LUMIERE / mean prediction; > 1 = under-prediction).

## Results — models trained on MU grade 4

Pooled locked AUC [95% CI] and O/E; the other columns are per-fold means (25 held-out folds).

| Features | Learner | MU CV | Locked, pooled [95% CI] | O/E | Locked, per fold [95% CI] | Fine-tuned (shrink) | Fine-tuned (pooled) | LUMIERE only |
|---|---|---|---|---|---|---|---|---|
| clinical | ridge | 0.585 | 0.610 [0.487, 0.737] | 1.15 | 0.558 [0.469, 0.642] | 0.544 | 0.505 | 0.396 |
| clinical | boosting | 0.625 | 0.627 [0.514, 0.731] | 0.86 | 0.624 [0.526, 0.701] | — | 0.560 | 0.520 |
| clinical + timing | ridge | 0.612 | 0.610 [0.497, 0.737] | 0.98 | 0.603 [0.544, 0.714] | 0.591 | 0.603 | 0.586 |
| clinical + timing | boosting | 0.664 | 0.632 [0.501, 0.748] | 0.84 | 0.643 [0.544, 0.739] | — | 0.632 | 0.627 |
| volumes | ridge | 0.611 | 0.545 [0.410, 0.653] | 1.00 | 0.521 [0.377, 0.608] | 0.531 | 0.567 | 0.569 |
| volumes | boosting | 0.591 | 0.529 [0.389, 0.644] | 1.00 | 0.515 [0.378, 0.591] | — | 0.513 | 0.518 |
| **clinical + timing + volumes** | **ridge** | 0.667 | **0.608 [0.469, 0.739]** | **1.33** | 0.598 [0.508, 0.701] | 0.606 | 0.617 | 0.580 |
| **clinical + timing + volumes** | **boosting** | 0.675 | **0.620 [0.495, 0.733]** | **0.99** | 0.608 [0.493, 0.691] | — | 0.658 | 0.610 |

Recalibrated = locked per fold in every row (ΔAUC 0 by construction); its pooled O/E is 0.93–0.97.
No adaptation arm has a ΔAUC CI above 0 vs locked; LUMIERE-only is significantly worse for clinical ridge (Δ −0.162
[−0.238, −0.066]).

**Cohort-normalisation sensitivity (grade-4-trained).**

| Features | Learner | Locked pooled | Rank: pooled [95% CI] | Rank: per-fold Δ vs locked [95% CI] | Rank O/E | Z-score: pooled [95% CI] | Z-score: per-fold Δ [95% CI] | Z-score O/E |
|---|---|---|---|---|---|---|---|---|
| volumes | ridge | 0.545 | 0.579 [0.446, 0.673] | +0.041 [−0.000, +0.091] | 0.86 | 0.564 [0.437, 0.666] | +0.021 [−0.003, +0.053] | 0.86 |
| volumes | boosting | 0.529 | 0.598 [0.456, 0.700] | +0.061 [−0.037, +0.162] | 0.86 | 0.590 [0.449, 0.690] | +0.053 [−0.030, +0.150] | 0.93 |
| clinical + timing + volumes | ridge | 0.608 | 0.624 [0.491, 0.752] | +0.010 [−0.015, +0.046] | 1.12 | 0.619 [0.483, 0.749] | +0.007 [−0.006, +0.023] | 1.11 |
| clinical + timing + volumes | boosting | 0.620 | 0.659 [0.529, 0.767] | +0.047 [−0.002, +0.110] | 0.87 | 0.637 [0.500, 0.750] | +0.010 [−0.048, +0.069] | 0.92 |

## Results — models trained on MU all gliomas

| Features | Learner | MU CV | Locked, pooled [95% CI] | O/E | Locked, per fold | Cohort-norm rank, pooled (Δ per fold [95% CI]) | Z-score, pooled |
|---|---|---|---|---|---|---|---|
| clinical + timing | ridge | 0.674 | 0.605 [0.488, 0.734] | 1.10 | 0.588 | — | — |
| clinical + timing | boosting | 0.723 | 0.656 [0.519, 0.780] | 0.87 | 0.682 | — | — |
| volumes | ridge | 0.655 | 0.552 [0.428, 0.657] | 1.12 | 0.538 | 0.584 (+0.044 [+0.004, +0.084]) | 0.567 |
| volumes | boosting | 0.629 | 0.573 [0.437, 0.678] | 1.18 | 0.554 | 0.580 (+0.013 [−0.060, +0.103]) | 0.546 |
| clinical + timing + volumes | ridge | 0.713 | 0.599 [0.462, 0.728] | 1.30 | 0.576 | 0.623 (+0.029 [−0.001, +0.061]) | 0.612 |
| clinical + timing + volumes | boosting | 0.724 | 0.619 [0.477, 0.740] | 1.04 | 0.607 | 0.652 (+0.050 [+0.004, +0.116]) | 0.641 |

Clinical only: ridge 0.601, boosting 0.635 (pooled). Full table: `results.csv`.

## Shipped PRISM report radiomics model (legacy features re-extracted on LUMIERE, 118/132 scans; files of 2026-10-09)

| Arm | AUC per fold (mean ± SD) | Pooled AUC IPCW [95% CI] | O/E |
|---|---|---|---|
| Raw (locked) | 0.617 ± 0.146 | 0.613 [0.500, 0.729] | 1.24 |
| Recalibrated | 0.617 (ranking unchanged) | — | 0.98 |
| Fine-tuned (shrink to shipped coefficients) | 0.602 ± 0.155 | 0.570 | 0.88 |

Clinical-code columns set to "unknown" where status unknown; all-zero variant: 0.596 [0.487, 0.705]. Sources:
`shipped_model.csv`, `shipped_model_adaptation.csv`. These predate the final LUMIERE label definition (death censoring);
re-run with `--shipped` before submission.

## Findings
1. **The shipped PRISM report radiomics model drops from 0.80 (PRISM report split) to 0.61 on LUMIERE**, and fine-tuning does
   not recover it.
2. **Simple shared-feature models transport only modestly:** locked pooled AUCs are 0.53–0.66, with lower CI bounds of
   0.39–0.52. The pre-specified primary set (clinical + timing + volumes, grade-4-trained) gives 0.608 [0.469, 0.739]
   (ridge) and 0.620 [0.495, 0.733] (boosting), against 0.667 / 0.675 in MU CV. Adding volumes to clinical + timing does not
   help on LUMIERE (ridge 0.610 → 0.608, boosting 0.632 → 0.620).
3. **Volumes do not transport as-is** (locked 0.53–0.57). Re-expressing them within each cohort by rank lifts every volume
   model (pooled +0.007 to +0.069; z-score lifts 7 of 8; clinical + timing + volumes boosting 0.620 → 0.659 with rank normalisation, per-fold Δ +0.047
   [−0.002, +0.110]; all-glioma-trained +0.050 [+0.004, +0.116]), so part of the loss is segmenter scale, not biology.
   This is a sensitivity analysis (transductive use of the LUMIERE feature distribution).
4. **Calibration:** pooled O/E 0.84–1.33 for grade-4-trained locked models and 0.87–1.30 for all-glioma-trained; the ridge
   models with volumes under-predict (1.30–1.33). Recalibration brings O/E to 0.93–0.97 without changing ranking.
5. **Fine-tuning does not improve discrimination** (no Δ CI above 0); LUMIERE-only models are worse (0.40–0.63): 61 patients are
   too few to learn from scratch.
6. **Schedule dependence:** in LUMIERE the time to next scan alone has AUC 0.79 (`SCHEDULE_COUPLING.md`), higher than any
   locked model.

## Caveats
- 16 feature/learner/population combinations reported, plus 8 cohort-normalised arms; quote the pre-specified clinical + timing
  + volumes rows, not the best row.
- Wide CIs (61 patients). Endpoint, segmentation, and time-zero differences mean this is a transport test of the *approach*,
  not of an identical model.
