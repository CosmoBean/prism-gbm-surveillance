# UCSF-ALPTDG: adversarial audit of the image AUCs (EXPLORATORY)

**EXPLORATORY, not in the plan.** This audit asks why the UCSF image AUCs are higher than MU's (locked A-Iscan 0.80,
A-Timg 0.89 and UCSF-trained 0.83–0.91, against about 0.62–0.66 within phase on MU). It checks whether they come from
label construction, missingness, design or a code fault. No analysis module was changed. Aggregate numbers only.

Script: `scripts/exploratory_ucsf_audit.py`. It reads `outputs/data/ucsf/{scans,imaging_features}.csv`,
`outputs/results/analyses/ucsf/locked/scores.csv`, `internal/oof.csv.gz` and the MU detection frame
(`detection.context("grade4", "primary")`).

```
PYTHONPATH=. OMP_NUM_THREADS=1 srun --jobid=160994 --overlap -N1 -n1 --cpus-per-task=4 --export=ALL \
    .venv/bin/python scripts/exploratory_ucsf_audit.py
```

How to read the numbers:
- The set is the primary set: grade 4, scan 2, `pos_s2_pm30` against primary negatives, 29 positives / 40 negatives.
- Bootstrap CIs are simple (one row per patient). Brackets give positives / negatives.
- "Ipure" etc. without a prefix are the Part B out-of-fold scores, averaged over the 5 repeats (ranking only). Their
  AUCs differ by about 0.01 from the published mean-of-repeat AUCs.

## Summary

Nothing here is a code artefact. The UCSF label is easier than MU's, for three reasons:
- **Positives look the way RANO says progression looks.** Enhancing tumour grew at scan 2: 27 of 29 positives are
  UCSF "ET Increased", the median ET log ratio to scan 1 is +0.60, and the median ET is 13.5 cc.
- **Negatives carry little enhancement.** The median ET is 1.4 cc, and 10 of 40 negatives have no ET at all.
- **The call was made at or just after scan 2.** Progression is dated a median of 7 d after it.

One input, log ET volume, gives AUC 0.88. That equals the best locked model (A-Timg 0.89, Spearman 0.97 with log ET).
In the 37 scans that UCSF rated "ET Increased", the locked A-Ipure falls to 0.53.

MU positives look different, even though MU is at least as circular in timing (75% of MU positives are scanned on the
progression day itself):
- the median MU ET log ratio at the positive scan is −0.06;
- MU log ET volume gives AUC 0.635.

So the UCSF AUCs do not show that the models transport *better* than they work on MU. They show that, on UCSF, the
models reproduce an enhancement-based clinical call made from the scan they read.

## 1. ET absent and imputation

| | value |
|---|---|
| ET absent: all UCSF scans / primary positives / primary negatives | 37% / **0 of 29** / **10 of 40** |
| MU training rows (grade 4), ET absent in positives / negatives | 3% / 9% |
| AUC of the binary indicator "ET present" | **0.625** (0.562–0.694); MU 0.527 |

Image AUCs, all 69 scans against the 59 with ET present (29 / 30):

| arm | all | ET present |
|---|---|---|
| A-Iscan | 0.795 | **0.726** (0.595–0.853) |
| A-Ipure | 0.726 | **0.634** (0.489–0.773) |
| A-Timg | 0.889 | **0.852** (0.741–0.934) |
| Iscan | 0.831 | 0.775 |
| Ipure | 0.856 | 0.808 |
| Timg | 0.917 | 0.891 |
| log ET volume | 0.878 | 0.838 |

How the missing values are filled:
- When ET = 0, every ET-dependent morphology and intensity input is NaN (100%; 0–8% when ET is present).
- The locked pipeline fills them with the MU training median plus an MU-learned missing indicator.
- The indicator coefficients are small: about −0.01 to −0.03 standardised. The NETC indicators carry −0.10, the
  largest in A-Iscan.
- The ET-absent negatives score low (median A-Iscan 0.19) mainly because log ET = 0, not because of the imputation.
- NETC is present in 76% of positives and 42% of negatives. Present/absent alone gives AUC 0.67 (0.60 within
  ET-present scans).

**Verdict:** ET-absent negatives are easy negatives. They add about 0.04–0.09 to every image arm (0.09 for A-Ipure).
The imputation does not create the separation. Even within ET-present scans A-Ipure is only 0.63, with a lower bound
below 0.5, so Q1 would not be met there.

## 2. Label asymmetry (negatives need ≥ 120 d without progression)

| | positives | negatives |
|---|---|---|
| days from diagnosis, median (IQR) | 460 (334–583) | 439 (236–688) |
| days scan 1 → scan 2 | **41** (28–58) | **56** (54–67) |
| WHO GBM / IDH-mutant | 21 / 1 | 20 / 4 |
| on chemo at scan 2 | 17 / 29 | 12 / 40 |
| death listed; days from scan 2 to death | 86%; 194 d | 60%; 489 d |
| negatives: verified by a later progression / followed | – | 33 / 7 (later progression a median of 392 d after scan 2) |

AUC when the negatives are restricted to closer comparisons:

| negatives restricted to | A-Iscan | A-Ipure | A-Timg | Ipure | log ET |
|---|---|---|---|---|---|
| verified by a later progression (29 / 33) | 0.798 | 0.739 | 0.916 | 0.886 | 0.905 |
| progressing 120–365 d after scan 2 (29 / 15) | 0.811 | 0.713 | 0.901 | 0.924 | 0.894 |
| no progression, followed (29 / 7) | 0.778 | 0.665 | 0.759 | 0.714 | 0.754 |
| WHO GBM only (21 / 20) | 0.793 | 0.740 | 0.888 | 0.850 | 0.888 |

- IDH mutant alone gives AUC 0.467.
- **Verdict:** this is not grade, IDH or follow-up selection. Negatives matched for later progression (the more severe
  cases) separate *at least* as well.
- The asymmetry that does show is the scan interval. Positives have shorter scan 1 → scan 2 intervals: the inverted
  interval gives AUC 0.72. This fits a scan 2 brought forward because of suspicion. Only A-T uses the interval.

## 3. Circularity: when progression was dated

- Progression minus scan 2 in the positives: median **+7 d** (IQR 0 to +11).
  - 9 within ±1 d;
  - 1 more than 1 d before;
  - 19 more than 1 d after (up to +30 d).
- The "before scan 2" group is a single scan, so the planned before/after contrast cannot be estimated.
- Positives dated more than 1 d *after* scan 2 (19 / 40): A-Iscan 0.786, A-Ipure 0.722, A-Timg 0.871, log ET 0.861.
- Positives dated within ±1 d (9 / 40): A-Iscan 0.808, A-Timg 0.917, log ET 0.906.
- MU: the positive is the first scan on or after the progression date. The gap is a median of 0 d (IQR 0–0), and 48 of
  64 positives were scanned on the progression day itself.

**Verdict:**
- On both cohorts the positive scan is the scan at or right after the clinical call, so circularity in timing is the
  same or greater on MU.
- On UCSF the call comes days after scan 2, consistent with a call made from scan 2 (or from a confirmatory scan
  within a month).
- Timing alone does not explain the gap between cohorts. What scan 2 *shows* does (check 4).

## 4. UCSF's own ET change category

| scan 2 ET change | negatives | positives |
|---|---|---|
| Increased | 10 | **27** |
| Unchanged | 25 | 1 |
| Decreased | 5 | 1 |

- SNFH change: Unchanged in 0 of 29 positives, against 20 of 40 negatives.
- AUC of ET "Increased" (binary): **0.841** (0.753–0.919), sensitivity 0.93, specificity 0.75. Within ET-present
  scans: 0.799.
- AUC of the ordinal ET category: 0.832. SNFH category: 0.798.
- Within the 37 "ET Increased" scans (27 / 10):
  - A-Iscan 0.652 (0.450–0.838);
  - **A-Ipure 0.530** (0.308–0.747);
  - A-Timg 0.756;
  - Ipure 0.696;
  - log ET 0.741.

**Verdict:** the clinical positive nearly coincides with UCSF's categorical "enhancement increased". Once that is
fixed, the locked change model is at chance, and the others keep only modest signal (wide CIs, 10 negatives).

## 5. Case mix: time since diagnosis

- Days from diagnosis: AUC **0.542** (0.393–0.681). Days from RT start: 0.542.
- Positives and negatives sit at similar points in follow-up (medians 460 and 439 d).
- **Verdict:** unlike MU, phase or time of care does not drive UCSF. This part of the UCSF result is genuinely
  within-phase.

## 6. Does enhancing burden alone explain it?

| single input / rule | AUC |
|---|---|
| log ET volume | **0.878** (0.790–0.946) |
| log ET max axial area | 0.867 |
| log tumour (ET + NETC) volume | 0.876 |
| ET ratio to scan 1 (log) | 0.822 |
| CV logistic, log ET | 0.870 |
| CV logistic, log ET + ET ratio + log SNFH | 0.896 |

- ET > 0.5 cc: sensitivity 1.00, specificity 0.38. ET > 2 cc: 0.90 / 0.55.
- Spearman with log ET: A-Timg **0.97**, A-Iscan 0.81, A-Ipure 0.72, Iscan 0.91, Ipure 0.87.
- ET volume, UCSF: positives 13.5 cc (7.5–23.2), negatives 1.4 cc (0.0–6.4).
- ET volume, MU: positives 7.1 cc (2.8–14.2), negatives 3.4 cc (0.7–8.9).
- Median ET log ratio to the previous scan: UCSF positives +0.60, negatives 0.00; MU positives −0.06, negatives
  0.00. MU log ET AUC 0.635 (later post-RT 0.657), MU ET ratio AUC 0.487.
- Within halves of log ET (ET-present scans), A-Iscan gives 0.69 and 0.48.

**Verdict, plainly:** on UCSF the image signal is dominated by enhancing-tumour burden, and its growth, at the scan
where progression was called. One volume does as well as any locked or UCSF-trained model. The models add at most
about +0.02 over log ET, inside the noise.

## 7. Code-level leakage and mismatches

- ET was recomputed from the seg NIfTIs for 6 random primary patients (time1 and time2), along with the ET log ratio.
  This gave 0 mismatches against `imaging_features.csv` and the analysed row. The analysed row is time2 in all 69,
  with one row per patient.
- Days from diagnosis are larger at scan 2 than at scan 1 in every patient: no time1/time2 swap.
- The ET subtraction maps (UCSF's own time1 → time2) agree with the sign of our ET log ratio in 93% of the 131
  non-empty maps.
- The xlsx volumes match the segs exactly, scan for scan (UCSF_IMAGING.md).
- No image column is a label proxy beyond ET volume itself. The most label-associated columns are et_cc /
  vox_label3 / log_et_cc (0.878) and tumour volume.
- Part B:
  - every OOF set has unique scan_ids;
  - the scan-2 sets have one row per patient;
  - the all-scans sets (137 rows / 97 patients; 291 / 210) use `StratifiedGroupKFold` grouped by patient, and the
    inner C search runs inside the training fold;
  - the Part B OOF labels equal the primary label row for row.

**Verdict:** no leakage, row mismatch or timepoint swap was found.

## Overall verdict

**Real but narrow.** The pipelines compute what they claim. On UCSF, the models reproduce a progression call that
coincides with visible enhancing growth at the same scan:
- **Same scan.** 27 of 29 positives are UCSF "ET Increased", and the call is dated a median of 7 d after the scan.
- **Easy negatives.** A quarter of the negatives have no enhancement at all.
- **One volume matches the models.** ET volume alone gives 0.88.

They do not show better generalisation than on MU. The UCSF task is easier: an enhancement-defined call with
low-burden negatives, where MU positives show no ET growth. Within ET-present scans the locked A-Ipure is 0.63 (lower
bound below 0.5). Within "ET Increased" scans it is 0.53.

**Caveat sentence the paper needs:**
> "On UCSF, progression was dated a median of 7 days after the evaluated scan, 27 of 29 positive scans were rated by
> UCSF as showing increased enhancement, and enhancing-tumour volume alone gave an AUC of 0.88; the UCSF AUCs
> therefore measure agreement with an enhancement-based clinical call made at the same scan, and are higher than on
> MU because the UCSF case mix is easier to separate (a quarter of negatives had no enhancement), not because the
> models generalise better."
