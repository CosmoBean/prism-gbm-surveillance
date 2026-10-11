# Schedule coupling: is the baseline a proxy for the surveillance schedule? (plan 3.2, 2026-10-11)

Code: `prism/analyses/schedule.py` (`python -m prism.analyses.schedule`), outputs in `$PRISM_OUTPUTS/results/analyses/schedule/`
(`strata_and_adjustment.csv`, `stratum_counts.csv`, `gap_combination.csv`, `sensitivity.csv`, `timing_vs_gap.csv`,
`describe.csv`, `gap_per_scan.csv`).

**Provenance of the numbers below (development run, 1000 bootstraps).** Cohort = current tables (MU 308 scans / 155 patients;
grade 4 249 / 126). Baseline ridge / boosting OOF = C3 baselines recomputed with the current code on that cohort (5 repeats).
Baseline + radiomics (nested) = repeat-averaged OOF of the *previous* C3 run (1 "repeat"), LUMIERE = previous locked
predictions. Re-run the module on the final outputs before quoting; expect small changes for the nested and LUMIERE rows.

## Setup
gap = days from the index scan to the patient's next MRI (MU: any timepoint; LUMIERE: any rated timepoint). The gap is not
known at prediction time and is partly *caused* by the outcome (a scan is brought forward when progression is suspected;
in MU 55/164 grade-4 event scans have progression dated within ±7 d of the next scan). Conditioning on gap therefore
over-adjusts: it is a conservative test. AUC = IPCW AUC(120 d), mean over repeats, patient-cluster bootstrap 95% CI.

## Results (MU grade 4; all gliomas in brackets)
Positive rate falls from 0.54 (gap ≤ 60 d) to 0.10 (> 180 d). Gap alone: AUC 0.639 [0.555, 0.721] (0.666) on scans with a next
scan; LUMIERE 0.788 [0.703, 0.868].

| | ridge | boosting | + radiomics (nested) |
|---|---|---|---|
| AUC, all scans | 0.698 [0.615, 0.774] (0.720) | 0.687 (0.718) | 0.704 (0.743) |
| gap tertile 1 / 2 / 3 (≤56 / 56–91 / >91 d) | 0.718 / 0.762 / 0.617 | 0.726 / 0.791 / 0.631 | 0.713 / 0.775 / 0.640 |
| no next scan (n = 60; 31 censored) | 0.613 | 0.532 | 0.557 |
| conditional AUC (pairs within gap tertile) | 0.687 [0.595, 0.768] (0.708) | 0.697 (0.723) | 0.694 (0.730) |
| logit(pred) coef per SD, unadjusted → adjusted for log gap | 0.91 → 0.86 [0.43, 1.41] | 0.83 → 0.87 [0.48, 1.33] | 1.02 → 0.96 [0.50, 1.58] |
| AUC on scans with a next scan: model / model + log gap (in-fold) | 0.710 / 0.719 | 0.710 / 0.733 | 0.723 / 0.738 |
| excl. early post-RT (151 scans) | 0.723 | 0.704 (refit 0.753) | 0.727 |
| next scan ≤ 120 d (161 scans) | 0.727 (refit 0.749) | 0.736 | 0.736 |
| both exclusions (85 scans) | 0.777 [0.653, 0.891] | 0.778 | 0.781 |

Timing vs schedule: grouped-CV R² of log gap is ≤ 0 for timing (−0.05; all gliomas 0.01), treatment, and the full baseline
(−0.05); the only notable Spearman is days from diagnosis (ρ = 0.20; later scans have longer gaps). The baseline prediction
correlates only weakly with gap (ρ = −0.17 ridge, −0.02 boosting).

LUMIERE (locked, grade-4-trained): clinical + timing ridge 0.630 → conditional 0.696; boosting 0.668 → 0.669; + volumes boosting
0.714 → 0.698; prediction coefficient stays positive after adjustment (0.66–0.87 per SD, CIs exclude 0). Subsets: 0.63–0.71.
Here early_post_rt does track the schedule (ρ = −0.27 with gap).

## Interpretation
The schedule is a strong correlate of the 120-d label, but the baseline's signal is not a proxy for it. Within gap strata the
baseline ranks scans almost as well as overall (0.69 vs 0.70 grade 4), its coefficient barely moves when log gap is added
(0.91 → 0.86 per SD), and the baseline features cannot predict the gap (CV R² ≤ 0). Gap and prediction are largely
complementary (adding gap in-fold gives +0.01 to +0.02 AUC), so a model using the gap would look better without being usable.
Discrimination is weakest in the longest-gap tertile and in scans without a next scan (0.53–0.62, wide CIs), where labels rely
on clinical follow-up or censoring. Excluding early post-RT scans or scans with a next scan > 120 d does not lower the AUC
(0.70–0.78 vs 0.69–0.70), so the result is not driven by pseudoprogression-window scans or by sparsely followed scans.
Caveat: strata are small (59–70 scans) and MU stratum CIs are 0.25–0.4 wide (LUMIERE up to 0.5).
