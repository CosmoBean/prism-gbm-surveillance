# C1 — Censoring-aware endpoint: results (2026-10-06; numbers updated to the final run 2026-10-11)

Code: `prism/` (cohort, folds, features, formulations, metrics), `prism/experiments/c1_endpoint.py`; tests: `tests/test_prism_cohort.py`.
Run: `uv run prism mu && uv run prism c1` (~1 min).
Full tables (both populations, H = 90/120/180, both feature sets): [C1_full_tables.md](C1_full_tables.md). Cohort flow: [cohort_flow.csv](cohort_flow.csv).

## Data layer delivered (D1, D2, D3, D4, D7)
- **Cohort (D1):** 596 timepoints → 314 eligible index scans / 157 patients at the time (flow logged). Matches the legacy cohort except `PatientID_0007/Timepoint_3`, which legacy code included despite an unknown MRI date (`label_for_case` returns 0 for non-progressors before checking the date). After the label fixes (`FIX_LABELS.md`) the final cohort is **308 scans / 155 patients** ([cohort_flow.csv](cohort_flow.csv), `docs/manuscript/FLOW.md`).
- **Follow-up (D2):** last known day = latest dated MRI or clinical event (therapy, progression, death). Death without progression = verified non-event *(superseded: in the final labels death without documented progression censors, giving 52 censored at 120 d, 39 in grade 4; `FIX_LABELS.md`)*. Censored at 120 d dropped from 59 (MRI dates only) to 37 at the time (19 recovered by death, 3 by treatment dates).
- **Codebook (D3):** IDH/MGMT/ATRX/1p19q mapped to documented levels; undocumented codes → explicit `unknown`.
- **Timing (D4):** days since RT end, ≤ 12-week post-RT flag (104 scans), visit index, grade/GBM flags.
- **Folds (D7):** 5 × 5 repeated patient-grouped folds stratified by 120-d status (incl. censored) and grade 4.

## Primary result — grade 4, H = 120 d (249 scans, 126 patients, 93 positives, 39 censored)

**Final numbers** (full re-run, `outputs/results/c1/c1_summary.md` / `c1_results.csv`, 2026-10-11, label-fixed cohort, mean over
5 repeats of per-repeat pooled-OOF AUC, paired patient-cluster bootstrap). The 2026-10-06 version of this table (253 scans,
92 positives, 25 censored, repeat-averaged estimator) is superseded.

| Features | Formulation | AUC(120 d) IPCW [95% CI] | ΔAUC vs naive [95% CI] | Brier IPCW | O/E | Cal. slope |
|---|---|---|---|---|---|---|
| volumes + clinical | naive | 0.651 [0.567, 0.727] | — | 0.230 | 1.14 | 0.95 |
| | verified | 0.657 [0.577, 0.732] | +0.006 [−0.020, +0.030] | 0.227 | 0.95 | 0.91 |
| | IPCW | 0.656 [0.578, 0.731] | +0.005 [−0.021, +0.029] | 0.227 | 0.97 | 0.92 |
| | hazard | 0.653 [0.574, 0.726] | +0.002 [−0.018, +0.022] | 0.242 | 0.87 | 0.50 |
| legacy radiomics + clinical | naive | 0.648 [0.553, 0.736] | — | 0.239 | 1.13 | 0.52 |
| | verified | 0.655 [0.575, 0.730] | +0.007 [−0.021, +0.038] | 0.237 | 0.96 | 0.51 |
| | IPCW | 0.654 [0.575, 0.730] | +0.006 [−0.022, +0.036] | 0.237 | 0.98 | 0.51 |
| | hazard | 0.669 [0.583, 0.746] | +0.021 [−0.027, +0.068] | 0.250 | 0.90 | 0.33 |

## Findings (final run)
1. **Discrimination is insensitive to the formulation**: all 36 ΔAUC CIs (2 populations × 2 feature sets × 3 horizons × 3
   formulations) include 0; ΔAUC ranges from −0.011 to +0.033, the hazard formulation trending highest (+0.000 to +0.033).
2. **The naive label systematically under-predicts risk**: O/E 1.12–1.19 in all 12 settings vs 0.95–0.99 for verified/IPCW.
   Censoring-aware formulations fix calibration-in-the-large at no discrimination cost.
3. **IPCW ≈ verified**: censoring is moderate (39 of 249 grade-4 scans at 120 d) and not strongly covariate-dependent.
4. **Honest performance is far below the PRISM report's 0.80**: grade 4 AUC 0.65–0.67 at 120 d under repeated
   patient-grouped CV (volumes or legacy radiomics + clinical). The single 30-patient split overstated performance.
5. **All gliomas > grade 4 only** (IPCW, 120 d: 0.690 vs 0.656 volumes + clinical; 0.726 vs 0.654 radiomics + clinical): part of
   the signal separates tumour types (lower-grade progress less) rather than timing.
6. **Hazard model is over-confident** (calibration slope 0.30–0.71).

## Implications for the paper
- C1 stands as a **methods/calibration** result, not a discrimination gain: adopt the landmark discrete-time hazard (or IPCW) as the default formulation, report the naive-label under-prediction, and the follow-up repair.
- Novelty weight shifts to **C2** (compartment + longitudinal concepts) and **C5** (shortcut/bias audit). Corrected radiomics (C3) is needed before any texture claim — the "legacy radiomics" rows use 2-gray-level texture.

## Next
- Fix hazard regularisation (don't penalise interval terms; tune on IPCW Brier) and add bootstrap CIs for O/E and slope.
- D5 measurement table with past-only Δ features → C2; D6 corrected radiomics → C3.
