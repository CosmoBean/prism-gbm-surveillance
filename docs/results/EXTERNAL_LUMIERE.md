# External test on LUMIERE — raw and fine-tuned (2026-10-09)

Code: `prism/lumiere.py` (cohort + labels), `prism/experiments/external_lumiere.py` (shared-feature models), `prism/experiments/shipped_on_lumiere.py` (shipped PRISM report radiomics model, legacy extraction unchanged).
Data: LUMIERE (Suter et al., Sci Data 2022; CC0) — 91 GBM patients, expert RANO per timepoint. Stored at `/project/community/sbandred/lumiere/`.

## Endpoint harmonisation
- Index scans: rated follow-ups (SD/PR/CR/Post-Op, ≥ week 2 after surgery) before the first RANO PD → **132 scans / 61 patients**.
- Label (H = 120 d): PD within 120 d = 1; a later rated scan ≥ 120 d on without PD = 0; otherwise censored → **47 positive, 77 negative, 8 censored**.
- Differences from MU: progression = expert RANO PD on imaging (MU: EMR-documented, imaging and/or clinical); time = weeks since surgery; no treatment fields (RT dates/dose/chemo) → MU's strongest block cannot be transported.
- Shared features: age, sex, IDH/MGMT (with unknown), log days since surgery, < 3 months post-RT flag (MU: ≤ 12 weeks after RT end), log ET/NETC/SNFH volumes (LUMIERE: DeepBraTumIA enhancing / necrotic-non-enhancing / edema, atlas space).
- **Volume caveat:** LUMIERE NETC median 7.4 cc vs MU 0.01 cc — DeepBraTumIA (not trained post-op) likely labels the resection cavity as necrosis; atlas-space volumes are also scaled.

## Arms
| Arm | Meaning |
|---|---|
| MU CV | MU repeated patient-grouped CV (internal reference) |
| Raw (locked) | Trained on all MU scans, applied unchanged to LUMIERE |
| Recalibrated | Raw model + intercept/slope refit on other LUMIERE patients (ranking unchanged) |
| Fine-tuned (shrink) | Ridge refit on LUMIERE training patients, penalised towards MU coefficients (strength by inner CV) |
| Fine-tuned (pooled) | Retrained on MU + LUMIERE training patients (LUMIERE weight 3) |
| LUMIERE only | Trained within LUMIERE (local ceiling) |

Adapted arms are scored on held-out LUMIERE patients (5×5 grouped CV, mean per-fold AUC); O/E from pooled out-of-fold predictions.

## Results — models trained on MU grade 4

| Features | Learner | MU CV | Raw on LUMIERE [95% CI] | Recalibrated | Fine-tuned (shrink) | Fine-tuned (pooled) | LUMIERE only |
|---|---|---|---|---|---|---|---|
| clinical | ridge | 0.578 | 0.609 [0.479, 0.735] | 0.552* | 0.546 | 0.522 | 0.399 |
| clinical + timing | ridge | 0.644 | 0.628 [0.521, 0.748] | 0.640* | 0.640 | 0.647 | 0.594 |
| clinical + timing | boosting | 0.714 | 0.663 [0.513, 0.781] | 0.690* | — | 0.675 | 0.638 |
| volumes | ridge | 0.591 | 0.534 [0.427, 0.629] | 0.514* | 0.527 | 0.539 | 0.567 |
| clinical + timing + volumes | ridge | 0.695 | 0.629 [0.505, 0.753] | 0.641* | 0.618 | 0.626 | 0.578 |
| **clinical + timing + volumes** | **boosting** | 0.709 | **0.719 [0.609, 0.832]** | 0.739* | — | 0.692 | 0.624 |

\* recalibration preserves ranking; per-fold AUC equals the raw model's per-fold AUC (pooled column shows raw on all of LUMIERE).

Calibration (O/E, observed / expected risk): raw 0.93–1.19 (grade-4-trained), 1.24–1.76 (all-glioma-trained, under-predicts); recalibrated 0.94–0.98; fine-tuned 0.94–1.13.

## Shipped PRISM report radiomics model (legacy features re-extracted on LUMIERE, 118/132 scans)

| Arm | AUC per fold (mean ± SD) | Pooled AUC IPCW | O/E |
|---|---|---|---|
| Raw | 0.617 ± 0.146 | 0.613 [0.500, 0.729] | 1.25 |
| Recalibrated | 0.617 (ranking unchanged) | — | 0.98 |
| Fine-tuned (shrink to shipped coefficients) | 0.602 ± 0.155 | 0.570 | 0.89 |

(Clinical-code columns set to "unknown" where status unknown; all-zero variant: 0.596.)

## Findings
1. **The shipped radiomics model drops from 0.80 (PRISM report split) to 0.61 externally**, and fine-tuning does not recover it.
2. **A simple clinical + timing + volume model transports:** raw 0.72 [0.61, 0.83] on LUMIERE (grade-4-trained boosting) vs 0.71 in MU CV — despite different progression definitions, segmentation tools, and no treatment features. Ridge versions: 0.63.
3. **Fine-tuning does not improve discrimination** (shrink/pooled within ±0.03 of raw); a LUMIERE-only model is worse (0.58–0.64) — 61 patients are too few to learn from scratch.
4. **Recalibration fixes calibration** (O/E → 0.94–0.98) at no cost: the practical adaptation step for a new hospital.
5. **Volumes alone do not transport** (0.53–0.62), consistent with the segmentation mismatch; they help in combination with clinical/timing in the boosting model.

## Caveats
- 16 feature/learner/population combinations reported; the best raw result (0.719) is one of them. Pre-specified primary for the paper should be the full shared set (clinical + timing + volumes) — which is also the best here.
- Wide CIs (61 patients). Endpoint, segmentation, and time-zero differences mean this is a transport test of the *approach*, not of an identical model.
