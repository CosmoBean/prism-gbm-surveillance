# C1 — Censoring-aware endpoint: results (2026-10-06)

Code: `prism/` (cohort, folds, features, formulations, metrics), `prism/experiments/c1_endpoint.py`; tests: `tests/test_prism_cohort.py`.
Run: `uv run python -m prism.cohort && uv run python -m prism.folds && uv run python -m prism.experiments.c1_endpoint` (~1 min).
Full tables (both populations, H = 90/120/180, both feature sets): [C1_full_tables.md](C1_full_tables.md). Cohort flow: [cohort_flow.csv](cohort_flow.csv).

## Data layer delivered (D1, D2, D3, D4, D7)
- **Cohort (D1):** 596 timepoints → 314 eligible index scans / 157 patients (flow logged). Matches the legacy cohort except `PatientID_0007/Timepoint_3`, which legacy code included despite an unknown MRI date (`label_for_case` returns 0 for non-progressors before checking the date).
- **Follow-up (D2):** last known day = latest dated MRI or clinical event (therapy, progression, death). Death without progression = verified non-event. Censored at 120 d drops from 59 (MRI dates only) to **37** (19 recovered by death, 3 by treatment dates).
- **Codebook (D3):** IDH/MGMT/ATRX/1p19q mapped to documented levels; undocumented codes → explicit `unknown`.
- **Timing (D4):** days since RT end, ≤ 12-week post-RT flag (104 scans), visit index, grade/GBM flags.
- **Folds (D7):** 5 × 5 repeated patient-grouped folds stratified by 120-d status (incl. censored) and grade 4.

## Primary result — grade 4, H = 120 d (253 scans, 128 patients, 92 positives, 25 censored)

| Features | Formulation | AUC(120 d) IPCW [95% CI] | ΔAUC vs naive [95% CI] | Brier IPCW | O/E | Cal. slope |
|---|---|---|---|---|---|---|
| volumes + clinical | naive | 0.638 [0.556, 0.715] | — | 0.226 | 1.08 | 0.96 |
| | verified | 0.629 [0.546, 0.709] | −0.009 [−0.030, +0.012] | 0.229 | 0.97 | 0.76 |
| | IPCW | 0.629 [0.546, 0.709] | −0.009 [−0.030, +0.012] | 0.229 | 0.97 | 0.75 |
| | hazard | 0.645 [0.563, 0.723] | +0.007 [−0.011, +0.024] | 0.232 | 0.92 | 0.56 |
| legacy radiomics + clinical | naive | 0.671 [0.580, 0.746] | — | 0.222 | 1.08 | 0.67 |
| | verified | 0.671 [0.584, 0.742] | −0.000 [−0.013, +0.012] | 0.224 | 0.98 | 0.62 |
| | IPCW | 0.670 [0.583, 0.741] | −0.001 [−0.013, +0.012] | 0.224 | 0.99 | 0.62 |
| | hazard | 0.699 [0.609, 0.770] | +0.028 [−0.010, +0.068] | 0.225 | 0.94 | 0.50 |

## Findings
1. **Discrimination is insensitive to the formulation**: ΔAUC CIs include 0 in 23/24 comparisons; the hazard formulation trends +0.01 to +0.03.
2. **The naive label systematically under-predicts risk**: O/E 1.07–1.12 in all 12 settings vs 0.98–1.00 for verified/IPCW. Censoring-aware formulations fix calibration-in-the-large at no discrimination cost.
3. **IPCW ≈ verified**: after the follow-up repair, censoring is light (~10% of scans) and not strongly covariate-dependent.
4. **Honest performance is far below the reported 0.804**: grade 4 AUC 0.64–0.70 under repeated patient-grouped CV (legacy radiomics features + clinical). The single 30-patient split overstated performance.
5. **All gliomas > grade 4 only** (e.g. 0.72 vs 0.67 at 120 d): part of the signal separates tumour types (lower-grade progress less) rather than timing — a confound to audit in C5.
6. **Hazard model is over-confident** (calibration slope 0.50–0.70): needs stronger/unpenalised-baseline regularisation or post-hoc recalibration.

## Implications for the paper
- C1 stands as a **methods/calibration** result, not a discrimination gain: adopt the landmark discrete-time hazard (or IPCW) as the default formulation, report the naive-label under-prediction, and the follow-up repair.
- Novelty weight shifts to **C2** (compartment + longitudinal concepts) and **C5** (shortcut/bias audit). Corrected radiomics (C3) is needed before any texture claim — the "legacy radiomics" rows use 2-gray-level texture.

## Next
- Fix hazard regularisation (don't penalise interval terms; tune on IPCW Brier) and add bootstrap CIs for O/E and slope.
- D5 measurement table with past-only Δ features → C2; D6 corrected radiomics → C3.
