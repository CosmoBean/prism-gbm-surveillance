# Plan: analyses asked for by the second review round (E6) (2026-11-17)

Written before any code for these analyses was written or run, and committed before the run. Results go to
METHODS_RESULTS.md section E6 unchanged, including unfavourable ones. No paper edits from the run.

Shared set-up, unless stated: the three PRISM scores of the paper (clinical-history, imaging, combined;
`prism/analyses/system.py` `mu_designs("grade4")`) and the reader baseline (`clinician_baseline.py`), MU by the same
5x5 grouped folds, intended use; LUMIERE by the locked models (`S.lumiere_cohort()`, reader baseline as in E4). One
2,000-sample patient bootstrap per cohort, seed 20261117; at MU each sample averages over the five repeats; no refit.
Reproduction check before anything is reported: MU 0.822 / 0.709 / 0.821 / reader 0.797; LUMIERE combined 0.773.

## E6a. Calibration (descriptive, no rule)
- For each score and cohort: calibration intercept (calibration-in-the-large, logit offset, slope fixed at 1) and
  calibration slope (logistic regression of the outcome on logit p), plus Brier and the prevalence reference.
- MU: computed per repeat on the pooled held-out predictions, averaged over repeats. LUMIERE: the locked
  predictions.
- UCSF-ALPTDG: not on hand; the planned slopes in UCSF_RESULTS.md are quoted, not recomputed.

## E6b. Scans shortly before progression (spectrum)
The primary label drops scans without progression that are followed by less than 120 days of progression-free
follow up, among them scans shortly before progression. The detection plan (2b4c927) already defines the secondary
negative set: every index scan before progression, whatever its follow up.
- Models trained exactly as now (primary negatives). Evaluated on the intended use with the secondary negatives.
- Outcomes: AUC of the three scores and the reader baseline; combined − reader baseline.
- Also, the AUC among only the added scans (secondary but not primary negatives) against the progression scans,
  per score, to show how the models score the dropped scans.
- Reading fixed now: the primary results are called robust to this choice if each score's AUC changes by less than
  0.05 and the reader-baseline reading (no clear gain) is unchanged; otherwise the paper states which change.

## E6c. Unknown IDH and MGMT status
Currently unknown status is coded with wildtype / unmethylated.
- Refit the clinical-history and combined models (and, at LUMIERE, the locked reduced models) with unknown coded as
  its own category (an indicator per marker), otherwise unchanged.
- Outcome: paired AUC difference (indicator coding − current) per score and cohort.
- Reading fixed now: robust if every paired CI includes zero; otherwise the paper states the change.

## E6d. The reduced combined model on MU (descriptive)
The model locked and applied externally is the reduced combined model (`D.context("grade4","primary")` design "T").
Report its MU cross-validated AUC in the intended use, same folds and bootstrap, next to the full combined model.

## Code
`prism/analyses/review_analyses.py`, reusing `methods.py`, `clinician_baseline.py`, `system.py` and `detection.py`.
Output: `outputs/results/analyses/review_analyses/` (aggregate CSV only).
