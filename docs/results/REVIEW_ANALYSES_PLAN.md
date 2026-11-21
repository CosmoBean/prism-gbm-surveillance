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

## Deviations recorded before results (2026-11-17, before any E6 outcome was computed)
Operational choices the plan left open, fixed here before the run.
1. **E6c, what "unknown" means.** The current code sets `idh_mutant` / `mgmt_methylated` to 0 in two cases: marker
   unknown, and scan before the diagnosis date (`phase_censoring.masked_molecular`). Both are "status not available
   at the scan", so the indicator `idh_unknown` (`mgmt_unknown`) is 1 in either case; `idh_mutant` /
   `mgmt_methylated` and the `early_post_rt x mgmt_methylated` term stay as they are. The indicators are added as
   two more columns to B1 (clinical-history), B1 + I_pure (combined) and, for LUMIERE, to the locked reduced
   designs Tbase and T (fitted with `system._fit` on all MU grade-4 detection training rows, as locked). LUMIERE
   unknown follows the system's coding (`system.lumiere_cohort`): IDH "wt" wildtype, containing "mut" mutant,
   anything else unknown (this includes "na" and "idh1 neg, sequencing required"); MGMT "methylated" /
   "not methylated", anything else unknown. The imaging model uses no marker and is not refitted.
2. **E6b, how the secondary negatives enter.** No refit. In the MU 5x5 CV every row of a held-out fold already gets
   a held-out prediction (training uses labelled rows only), so the scans that are secondary but not primary
   negatives are scored by the same fitted models. Evaluation set: intended use and (progression scan or
   `neg_secondary`). E6b is MU only: LUMIERE negatives are every earlier study rated SD/PR/CR, with no follow-up
   requirement, so no scan is dropped there.
3. **Bootstrap.** One set of 2,000 patient resamples per cohort (seed 20261117). At MU it is drawn over the patients
   of the widest evaluation set (intended use, secondary negatives), and each analysis uses the rows of its own
   evaluation set within each resample; LUMIERE over its 79 patients. Percentile 95% intervals.
4. **E6a details.** Unpenalised maximum likelihood (Newton). Intercept: logistic model with offset logit(p) and slope
   fixed at 1. Slope: logistic regression of the outcome on logit(p). p clipped to [1e-6, 1 - 1e-6]. Prevalence
   reference = Brier score of always predicting the evaluation-set prevalence, p(1 - p). The reader baseline is
   reported as a fourth score, for reference. Bootstrap intervals are descriptive (no rule).
5. **E6d.** The paired difference (reduced − full combined) is reported too, descriptively. The reduced model is
   fitted with the same CV pipeline as the other MU scores (`c3.fit_predict`, BASELINES[0], seed = repeat).
6. **E6b reading.** "Each score" = the three PRISM scores (the reader's change is reported beside them). "Reader-
   baseline reading unchanged" = as in E4: no PRISM score has a gain over the reader baseline whose interval lies
   above zero. The gains of all three scores are computed for this; combined − reader is the planned outcome.
