# Plan: what each PRISM score adds beyond what the reader already has (E4)

Written 2026-11-15, before any code for this analysis was written or run. It is committed before the run. Results go
to METHODS_RESULTS.md (section E4) unchanged, including a null.

## Question
A clinician reading a follow up MRI already knows when the scan was taken relative to radiotherapy, and sees the
enhancing tumour and whether it grew since the previous scan. Does each PRISM score rank scans with and without
progression better than a score built from only that knowledge? Where does any gain lie: within one time window, or
across windows?

## The reader baseline (B)
A ridge logistic regression fitted with the same pipeline as every PRISM model (`c3.BASELINES[0]` through
`c3.fit_predict`, BASE_PRE imputation and scaling, the verified ridge). Its inputs:
- **MU (internal):**
  - the time window after radiotherapy, one indicator each for before radiotherapy, during radiotherapy and within
    12 weeks after its end (later is the reference);
  - log enhancing volume (`log_et_cc`);
  - its log ratio to the previous scan (`logratio_prev_et`, imputed by the pipeline when there is no previous
    scan).
- **LUMIERE (locked):**
  - the inputs that the locked models have there: `early_post_rt` (the rater's flag at LUMIERE), `log_et_cc`,
    `logratio_prev_et` and `has_prev`, taken from the locked-test design `D.context(...)["T"]`;
  - fitted once on all MU grade 4 detection training rows with `S._fit`, like every other locked model.
- **UCSF-ALPTDG:** not on our hardware, so not run. The planned results already give enhancing volume alone at 0.88
  against 0.86 for the locked combined model. That is quoted, not recomputed.

## Population and procedure
- **MU:** same as M1. Five repeats of fivefold CV grouped by patient (`D.fold_ids`); evaluation on the intended use
  (`label_120` known, `intended_use`); per repeat, B and the three PRISM scores are fitted in the same folds.
- **LUMIERE:**
  - all 178 detection scans;
  - the locked PRISM scores are taken exactly as in M1 (`S.lumiere_cohort()["S"]`), the imaging score using the
    three-volume model for scans with no previous scan.
- **Statistics:**
  - **Bootstrap:** 2,000 bootstrap samples of patients, seed 20261115. At MU each sample averages over the five
    repeats. Predictions are not refitted.
- **Reproduction check:** the PRISM AUCs must reproduce M1 (MU 0.822, 0.709, 0.821; LUMIERE 0.689, 0.773) before
  anything is reported.

## Outcomes (all estimates with 95% intervals; no pass rule)
1. **Primary.** The AUC gain of the combined model over B (combined − B), at MU and LUMIERE.
2. **Secondary.** The gain of the imaging model over B, and of the clinical-history model over B.
3. **Where the gain lies.** For each gain, the change in A_W (pairs within one time window) and in A_B (pairs
   across windows). The windows are the same as M1's (MU: during, within 12 weeks, later; LUMIERE: the rater's flag).
4. **The baseline itself.** B's own AUC, A_W and A_B.

## Reading fixed in advance
- **"Adds beyond what the reader has":** a gain whose 95% interval lies above zero.
- **"Adds beyond timing":** a gain in A_W whose interval lies above zero.
- **Otherwise:** a gain whose interval includes zero is reported as "no clear gain", never as "no gain".
- **The paper's wording** follows these readings, whatever they show.

## Code
`prism/analyses/clinician_baseline.py`. It reuses `split_auc`, `boot` and `ci` from `prism/analyses/methods.py` and
the fold and fitting machinery used there. Output goes to `outputs/results/analyses/clinician_baseline/` (aggregate
CSV only).
