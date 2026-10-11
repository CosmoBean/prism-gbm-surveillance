# Schedule coupling: is the baseline a proxy for the surveillance schedule? (plan 3.2, 2026-10-11)

Code: `prism/analyses/schedule.py` (`python -m prism.analyses.schedule`), outputs in `outputs/results/analyses/schedule/`
(`strata_and_adjustment.csv`, `stratum_counts.csv`, `gap_combination.csv`, `sensitivity.csv`, `timing_vs_gap.csv`,
`describe.csv`, `gap_per_scan.csv`).

**Provenance: final numbers** (`outputs/results/analyses/schedule/`, re-run 2026-10-11 18:39 after the radiomics clipping
fix, [FIX_RADIOMICS_CLIP.md](FIX_RADIOMICS_CLIP.md); 1000 bootstraps). Cohort MU 308 scans / 155 patients (grade 4 249 / 126).
All three MU models use the per-repeat OOF of the C3 run (5 repeats). LUMIERE uses the final locked predictions
(`outputs/results/external_lumiere/locked_predictions.csv`). Compared with the `cc2e3a3` run, only the nested-radiomics
column changed. The ridge, boosting and LUMIERE numbers are unchanged.

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
| AUC, all scans | 0.698 [0.615, 0.774] (0.720) | 0.687 (0.718) | 0.666 (0.747) |
| gap tertile 1 / 2 / 3 (≤56 / 56–91 / >91 d) | 0.718 / 0.762 / 0.617 | 0.726 / 0.791 / 0.631 | 0.728 / 0.725 / 0.561 |
| no next scan (n = 60; 31 censored) | 0.613 | 0.532 | 0.549 |
| conditional AUC (pairs within gap tertile) | 0.687 [0.595, 0.768] (0.708) | 0.697 (0.723) | 0.654 (0.738) |
| logit(pred) coef per SD, unadjusted → adjusted for log gap | 0.91 → 0.86 [0.43, 1.41] | 0.83 → 0.87 [0.48, 1.33] | 0.78 → 0.71 [0.36, 1.10] |
| AUC on scans with a next scan: model / model + log gap (in-fold) | 0.710 / 0.719 | 0.710 / 0.733 | 0.681 / 0.695 |
| excl. early post-RT (151 scans) | 0.723 | 0.704 (refit 0.753) | 0.705 |
| next scan ≤ 120 d (161 scans) | 0.727 (refit 0.749) | 0.736 | 0.698 |
| both exclusions (85 scans) | 0.777 [0.653, 0.891] | 0.778 | 0.761 |

Sources: `strata_and_adjustment.csv` (AUCs, conditional AUC, coefficients), `gap_combination.csv` (+ log gap),
`sensitivity.csv` (subsets), `stratum_counts.csv`, `timing_vs_gap.csv`, `describe.csv`.

Timing vs schedule: grouped-CV R² of log gap is ≤ 0 for timing (−0.05; all gliomas 0.01), treatment, and the full baseline
(−0.05); the only notable Spearman is days from diagnosis (ρ = 0.20; later scans have longer gaps). The baseline prediction
correlates only weakly with gap (ρ = −0.17 ridge, −0.02 boosting).

LUMIERE (locked, grade-4-trained; 126 of 132 scans have a next scan): clinical + timing ridge 0.610 → conditional 0.690;
boosting 0.632 → 0.665; + volumes boosting 0.620 → 0.601. The prediction coefficient after adjustment for log gap is
0.51 [0.13, 1.00] (ridge) and 0.60 [0.11, 1.20] (boosting), CIs excluding 0, but 0.37 [−0.14, 0.89] for the + volumes boosting
model (CI includes 0). Gap alone gives 0.788 [0.703, 0.868] in LUMIERE, higher than any locked model. Subsets: 0.61–0.70.
Here early_post_rt does track the schedule (ρ = −0.27 with gap).

## Interpretation
The schedule is a strong correlate of the 120-d label, but the MU baseline's signal is not a proxy for it. Within gap strata the
baseline ranks scans almost as well as overall (0.69 vs 0.70 grade 4), its coefficient barely moves when log gap is added
(0.91 → 0.86 per SD), and the baseline features cannot predict the gap (CV R² ≤ 0). Gap and prediction are largely
complementary (adding gap in-fold gives +0.01 to +0.02 AUC), so a model using the gap would look better without being usable.
Discrimination is weakest in the longest-gap tertile and in scans without a next scan (0.53–0.62, wide CIs), where labels rely
on clinical follow-up or censoring. Excluding early post-RT scans or scans with a next scan > 120 d does not lower the baseline AUC
(0.70–0.78 vs 0.69–0.70), so the result is not driven by pseudoprogression-window scans or by sparsely followed scans.
The nested radiomics model is weakest in the longest-gap tertile (0.561) and its conditional AUC (0.654) is below the
baseline's (0.687). In LUMIERE the gap is far more predictive (0.79) than any locked model and the volume-containing model's
coefficient is no longer distinguishable from 0 after adjustment, so the external AUCs should be read as partly
schedule-dependent.
Caveat: strata are small (59–70 scans) and MU stratum CIs are 0.25–0.4 wide (LUMIERE up to 0.5).
