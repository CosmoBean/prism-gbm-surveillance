# Results: the three methods (2026-11-15)

Plan: [METHODS_PLAN.md](METHODS_PLAN.md) (commit 1363773, before any run). Code: `prism/analyses/methods.py`,
`prism/report/verifier.py`, `prism/analyses/verifier_mutation.py` (commits 3d5e710, f27d81e). Aggregate numbers only;
outputs in `outputs/results/analyses/{methods,verifier_mutation}/` (git-ignored). MU and LUMIERE only; UCSF-ALPTDG is
not on disk. Prior art: [PRIOR_ART_2026-11-15_METHODS.md](../literature/PRIOR_ART_2026-11-15_METHODS.md).

Checks before reading (all passed): MU displayed AUCs 0.822 / 0.709 / 0.821; MU within-context AUCs reproduce the
registered within-phase audit (clinical-history 0.640, imaging 0.677 against 0.64 and 0.68); the identity
AUC = w A_W + (1 - w) A_B holds to 1e-12 on every resample; LUMIERE registered marginal sets equal the system's.

## M1. AUC split by context (2000 patient resamples)

Context: MU time after radiotherapy (146 scans, 62 progression; strata during radiotherapy 2 / 1, early after it
4 / 51, later 56 / 32, progression / no progression); LUMIERE the rater's within-3-months flag (178 scans, 73
progression; flagged 1 / 27, other 72 / 78). Share of pairs within one context w: MU 0.38 (0.28-0.48), LUMIERE 0.74
(0.59-0.84).

| cohort | score | AUC | within context A_W | across contexts A_B | A_B - A_W |
|---|---|---|---|---|---|
| MU | clinical-history | 0.82 (0.75-0.89) | 0.64 (0.51-0.78) | 0.93 (0.88-0.97) | 0.29 (0.16-0.43) |
| MU | imaging | 0.71 (0.63-0.78) | 0.68 (0.58-0.77) | 0.73 (0.64-0.81) | 0.05 (-0.04 to 0.14) |
| MU | combined | 0.82 (0.75-0.89) | 0.65 (0.52-0.78) | 0.92 (0.88-0.96) | 0.27 (0.15-0.40) |
| MU | context only | 0.70 (0.60-0.80) | 0.34 * | 0.93 (0.86-0.98) | |
| MU | enhancing volume | 0.62 (0.53-0.71) | 0.68 (0.54-0.80) | 0.59 (0.49-0.69) | -0.09 (-0.22 to 0.05) |
| LUMIERE | clinical-history | 0.69 (0.60-0.80) | 0.59 (0.49-0.71) | 0.96 (0.89-1.00) | 0.37 (0.23-0.49) |
| LUMIERE | imaging | 0.65 (0.57-0.73) | 0.71 (0.60-0.80) | 0.51 (0.39-0.63) | -0.20 (-0.34 to -0.04) |
| LUMIERE | combined | 0.77 (0.68-0.86) | 0.72 (0.60-0.82) | 0.93 (0.86-0.99) | 0.22 (0.12-0.34) |
| LUMIERE | context only | 0.62 (0.57-0.70) | 0.50 | 0.96 (0.88-1.00) | |
| LUMIERE | enhancing volume † | 0.66 (0.56-0.75) | 0.74 (0.63-0.84) | 0.45 (0.35-0.58) | -0.29 (-0.42 to -0.13) |

† Correction 2026-11-17. LUMIERE has no enhancing volume for 15 of the 178 scans (5 progression). The first run
scored them as missing values that lose every comparison, which pulled the row down: AUC 0.56 (0.43-0.68), A_W 0.61
(0.46-0.75), A_B 0.41 (0.29-0.53), A_B - A_W -0.21 (-0.36 to -0.04), w 0.74 (0.59-0.84). The reference is now
evaluated on the 163 scans with a recorded volume (68 progression / 95 no progression), as in Figure 2 (AUC 0.662):
AUC 0.66 (0.56-0.75), A_W 0.74 (0.63-0.84), A_B 0.45 (0.35-0.58), A_B - A_W -0.29 (-0.42 to -0.13), w 0.72
(0.56-0.84). Same 2000 patient resamples and seed; within each resample the scans without a volume are dropped for this
score only. Every other row of m1_auc_split.csv and the M2 outputs are unchanged to the last digit. The interval
differs slightly from Figure 2's (0.563-0.751), which comes from that figure's own resampling.

\* Deviation from the plan, which said the context-only A_W is 0.5 by construction. At MU the stratum rates are
recomputed in each training fold, so scans of one stratum in different folds get slightly different rates, and a
fold whose test part holds more progression scans has a lower training rate. A_W 0.34 is this artefact; the
quantity of interest is A_B.

Increments (combined minus one model):
| cohort | | AUC | A_W | A_B |
|---|---|---|---|---|
| MU | combined - clinical-history | -0.00 (-0.05 to 0.05) | 0.01 (-0.09 to 0.13) | -0.01 (-0.04 to 0.02) |
| MU | combined - imaging | 0.11 (0.03-0.19) | -0.02 (-0.15 to 0.10) | 0.20 (0.12-0.27) |
| LUMIERE | combined - clinical-history | 0.08 (-0.01 to 0.16) | 0.12 (0.00-0.23) | -0.03 (-0.08 to 0.01) |
| LUMIERE | combined - imaging | 0.12 (0.04-0.21) | 0.01 (-0.08 to 0.10) | 0.43 (0.30-0.55) |

Reading (rule of the plan): the clinical-history and combined models draw part of their discrimination from the
context at both centres (A_B - A_W above zero with intervals clear of it); the imaging model does not (MU interval
includes zero; LUMIERE A_B below A_W). Adding clinical history to images gains only across contexts at both centres;
adding images to clinical history gains within contexts at LUMIERE (0.12, 0.00-0.23) and not at MU.

## M2. Group-conditional conformal sets (alpha 0.2, at least 10 calibration patients per level)

Share of scans calibrated at level 1 (its group) / 2 (enhancement state) / 3 (all): MU 0.29 / 0.45 / 0.26; LUMIERE
0 / 0.60 / 0.40 (time unknown, so it starts at level 2).

| cohort | combined | coverage | progression | no progression | both outcomes | empty | worst-group gap |
|---|---|---|---|---|---|---|---|
| MU | registered marginal | 0.82 (0.76-0.88) | 0.82 | 0.83 | 25% | 0.1% | 0.12 |
| MU | group-conditional | 0.83 (0.78-0.87) | 0.86 | 0.81 | 31% | 4.1% | 0.075 |
| LUMIERE | registered marginal | 0.87 (0.80-0.93) | 0.77 | 0.94 | 38% | 0% | 0 |
| LUMIERE | group-conditional | 0.89 (0.84-0.94) | 0.80 | 0.96 | 42% | 0% | 0 |

Worst-group gap: 0.8 minus the lowest coverage among groups with at least 10 evaluation scans. At MU the worst group
is later after radiotherapy with increased enhancement (24 scans, 16 progression): 0.68 (0.55-0.81) registered, 0.73
(0.59-0.85) group-conditional; later with enhancement not increased (54 scans) rises from 0.78 to 0.87. Clinical-history
and imaging (secondary): MU gap 0.07 -> 0.02 and 0.12 -> 0.07; LUMIERE 0.05 -> 0.05 and 0.16 -> 0.18.
Reading: group calibration narrows the shortfall in the worst MU group and raises coverage of progression scans, at
the cost of more two-outcome sets (25% -> 31% at MU) and some empty sets (4% at MU). At LUMIERE no group falls below
0.8 with either set. No guarantee holds externally without exchangeability with the MU calibration scans.

## M3. Bound verifier

v1.0 (commit 3d5e710, rules fixed before any report was checked) bound a number only to cited fields whose key names
the entity. It rejected every real report (276 / 276 language model, 276 / 276 template) and 24 of 52 correct
synthetic reports, because statement fields name the entity in their text, not their key. This is a failed
pre-specified rule and is reported as such. v1.1 (commit f27d81e, blob d4b93db5) also binds numbers and direction words
inside a cited text field to the entity named in their clause; it was developed on the synthetic records (52 / 52
correct reports pass) and the development reports (language model 47 / 48, template 48 / 48; counts only), then
applied once to the evaluation reports.

False rejections (v1.1, evaluation reports, all passing the frozen checker): language model MU 1 / 114 (rule V2),
LUMIERE 0 / 162; template 0 / 276. Not adjudicated (the reports are not read in a hosted context).

Planted errors, share rejected (frozen checker -> verifier):
| operator | synthetic (52 records) | real, language model | real, template |
|---|---|---|---|
| B1 direction word flipped in the change sentence | 0 -> 1.00 (52) | 0 -> 1.00 (194) | 0 -> 1.00 (194) |
| B2 enhancing and FLAIR volumes swapped | 0 -> 1.00 (52) | pattern absent | pattern absent |
| B3 change rewritten with the opposite direction (held out) | 0 -> 1.00 (52) | 0 -> 1.00 (194) | 0 -> 1.00 (194) |
| B4 imaging score value in the clinical-history sentence (held out) | 1.00 -> 1.00 | pattern absent | pattern absent |
| B5 FLAIR volume given as enhancing (held out) | 1.00 -> 1.00 | 1.00 -> 1.00 (260) | 1.00 -> 1.00 (261) |
| N1 a number changed | 1.00 | 0.999 (3261) | 0.999 (3264) |
| C2 conformal statement removed | 1.00 | 0.60 (275) | 0.60 (276) |
| T2 card tier word swapped | 0.46 | 0.55 (275) | 0.67 (276) |
| T1 tier statement removed where required | 1.00 | 0.90 (90) | 1.00 (90) |
| all other operators (A1, A2, C1, D1-D5, F1, F2, N2-N4, P1, R1) | 1.00 | 0.99-1.00 | 0.99-1.00 |

Reading (rule of the plan: closes a blind spot if at least 95% of synthetic mutants are rejected): the verifier
closes the two known blind spots (B1, B2) and the held-out direction rewrite (B3). One blind spot remains: a tier word
swapped to "tested" where the card has few cases (T2; 33% to 45% of real mutants pass), because no rule names the
word "tested".

Diagnostics added after the run (2026-11-15, exploratory; counts only):
- B4 and B5 were rejected by the frozen checker only through its required-content rule (the mutant replaces the
  sentence that stated the score or volume), not through the binding of the number. The binding rules V1 and V2
  alone reject every B1-B5 mutant in every set (synthetic 52 / 52 for each; real B1 and B3 194 / 194 per writer, B5
  260 / 260 language model, 261 / 261 template).
- C2 is not a blind spot. In the 111 real reports per writer whose C2 mutant passes, another sentence still states
  the combined 80% set (it cites `conformal.combined.80.*` or the flag), so the mutant is a correct report; in the
  other 165 the mutant is rejected. The operator removes only the sentences citing the `.statement` field.

## Exploratory checks asked for by the internal referee (2026-11-15, not in the plan)
`prism/analyses/methods_extra.py`; MU, combined model unless stated.

E1. Context-only score with the window rates computed once on all labelled MU scans: A_W 0.50 (ties), A_B 0.94, AUC
0.77. The window alone ranks pairs across windows as well as the clinical-history model (0.93). AUC within each window
(mean over repeats; progression / no progression): later than 12 weeks (56 / 32) clinical-history 0.64, imaging 0.65,
combined 0.62; within 12 weeks (4 / 51) 0.66, 0.92, 0.93; during radiotherapy (2 / 1) not interpretable. The later
window holds 1,792 of the 1,998 within-window pairs (90%), so A_W is close to the later window's AUC.

E2. Baselines for the group-conditional sets (alpha 0.2 unless stated):

| set | coverage | progression | no progression | both outcomes | empty | worst group, >= 9 scans | worst group, >= 10 scans |
|---|---|---|---|---|---|---|---|
| marginal (planned) | 0.82 | 0.82 | 0.83 | 25% | 0.1% | 0.67 (later, no enhancement, 9) | 0.68 (later, increased, 24) |
| group-conditional | 0.83 | 0.85 | 0.81 | 31% | 4.1% | 0.67 (same) | 0.72 (same) |
| marginal, alpha 0.175 (size-matched) | 0.86 | 0.86 | 0.86 | 32% | 0.1% | 0.69 (same) | 0.74 (same) |
| outcome-conditional | 0.79 | 0.87 | 0.73 | 16% | 0.7% | 0.64 (later, increased) | 0.64 (same) |

Per group (marginal / group-conditional / size-matched): within 12 weeks without previous scan (32 scans) 0.99 / 0.84 /
1.00; later with enhancement not increased (54) 0.78 / 0.87 / 0.83; later with increased enhancement (24) 0.68 / 0.72
/ 0.74; later without enhancement (9) 0.67 / 0.67 / 0.69.
Reading: a marginal set enlarged to the same share of two-outcome sets covers the worst groups at least as well as
the group-conditional set. The gain of M2 in the worst group comes from larger sets, not from calibration within
groups. What group calibration does differently is move coverage from over-covered groups (within 12 weeks, no
previous scan, 0.99 to 0.84) to the largest later group (0.78 to 0.87). With the figure's threshold of 9 scans the
worst group is unchanged (0.67 with both sets); the worst-group gap of M2 above used 10.

E3. Independent planted errors (`prism/analyses/verifier_independent.py`; errors in
`independent_mutants_2026-11-15.json`, written by a separate agent that had not seen the checker or verifier code,
on the 52 synthetic records). Share rejected, checker / verifier (binding rules alone):

| class | n | checker | verifier | binding rules |
|---|---|---|---|---|
| D direction stated wrongly in new wording (regressed, receded, less, a reduction, ...) | 208 | 0 | 0.32 | 0.32 |
| L a correct value under the wrong entity, citing both | 156 | 0.12 | 1.00 | 1.00 |
| S a score on the wrong side of its median, new wording (exceeds, under, ...) | 104 | 0.14 | 0.14 | 0 |
| CONTROL correct paraphrase | 104 | 0 | 0 | 0 |

Reading: entity binding (V1) generalises to independently written label errors with no false rejection of
paraphrases. Direction binding (V2) catches only the direction words on its list, so two thirds of direction errors in
other wording pass; the side of a score is not covered by either rule beyond the checker's above / below pattern.
The word list was not widened, because doing so on this set would spend it as a test. Limits: all 52 synthetic
records share the same volumes and an increase in every change, so the D errors are all false decreases.

## E4. What each PRISM score adds beyond the reader baseline (planned in CLINICIAN_BASELINE_PLAN.md, e8014a8)

The reader baseline B is ridge logistic regression on the time window plus log enhancing volume and its log ratio
to the previous scan. MU: 5x5 grouped CV, intended use (146 scans); LUMIERE: B locked on MU, 178 scans. Intervals
come from 2,000 bootstrap samples of patients (seed 20261115), without refitting. The PRISM AUCs reproduce M1
(asserted in code). Output: `outputs/results/analyses/clinician_baseline/e4_reader_baseline.csv`.

| cohort | score | AUC | A_W (within) | A_B (across) |
|---|---|---|---|---|
| MU | reader baseline | 0.80 (0.71-0.88) | 0.57 (0.43-0.71) | 0.94 (0.87-0.98) |
| MU | clinical-history | 0.82 | 0.64 | 0.94 |
| MU | imaging | 0.71 | 0.68 | 0.73 |
| MU | combined | 0.82 | 0.65 | 0.92 |
| LUMIERE | reader baseline | 0.73 (0.64-0.81) | 0.67 (0.56-0.75) | 0.92 (0.82-0.99) |
| LUMIERE | clinical-history (reduced) | 0.69 | 0.59 | 0.96 |
| LUMIERE | imaging | 0.65 | 0.71 | 0.51 |
| LUMIERE | combined (reduced) | 0.77 | 0.72 | 0.93 |

Gains over B (score - B):

| cohort | score | dAUC | dA_W | dA_B |
|---|---|---|---|---|
| MU | combined (primary) | +0.02 (-0.03 to +0.08) | +0.08 (-0.04 to +0.18) | -0.01 (-0.06 to +0.05) |
| MU | imaging | -0.09 (-0.19 to +0.02) | +0.10 (-0.04 to +0.26) | -0.21 (-0.31 to -0.10) |
| MU | clinical-history | +0.02 (-0.05 to +0.10) | +0.07 (-0.11 to +0.23) | -0.00 (-0.04 to +0.05) |
| LUMIERE | combined (primary) | +0.04 (-0.01 to +0.10) | +0.05 (-0.02 to +0.13) | +0.02 (-0.01 to +0.06) |
| LUMIERE | imaging | -0.08 (-0.16 to -0.00) | +0.04 (-0.03 to +0.12) | -0.41 (-0.55 to -0.27) |
| LUMIERE | clinical-history | -0.05 (-0.15 to +0.07) | -0.08 (-0.23 to +0.09) | +0.05 (+0.01 to +0.09) |

Reading, by the rules fixed in the plan:
- No PRISM score showed a clear gain over the reader baseline at either centre. Every dAUC interval includes zero,
  except the imaging model, which is lower overall because it does not see the window.
- No score showed a clear gain within a time window. All the dA_W point estimates are positive at MU (+0.07 to
  +0.10), and their intervals include zero.
- Timing plus enhancement alone reached 0.80 at MU and 0.73 at LUMIERE.

## E5. Mask sensitivity (planned in MASK_SENSITIVITY_PLAN.md, b1ce85b; deviations c235649)

Every released MU mask was replaced by the BraTS21 SwinUNETR label map (`prism.features.reseg`, 1 GPU, 981 s for
594 scans). Agreement with the released masks matches RESEGMENTATION.md: median Dice ET 0.80 [0.49, 0.91], TC 0.62,
WT 0.85 [0.74, 0.93]. The measurement table was rebuilt from the new maps with the `measurements.py` logic. The
cavity comes from the released mask. The table has the same 591 scans and columns
(`outputs/results/analyses/reseg/measurements_brats21.csv`). The E4 models were refitted on each table in the same
5x5 folds. MU intended use: 146 scans, 80 patients, 62 progressions; identical under both mask sets (asserted). One
set of 2,000 patient bootstrap samples (seed 20261115) covers both mask sets, so the differences are paired. On the
released masks the models reproduce M1 and E4 (asserted). Output: `outputs/results/analyses/mask_sensitivity/`.

| score | AUC, released | AUC, BraTS21 | paired difference | A_W difference | A_B difference |
|---|---|---|---|---|---|
| imaging | 0.71 (0.63-0.78) | 0.63 (0.55-0.70) | **-0.08 (-0.16 to -0.01)** | -0.11 (-0.20 to -0.03) | -0.07 (-0.15 to +0.02) |
| combined | 0.82 (0.75-0.89) | 0.80 (0.73-0.88) | -0.02 (-0.05 to +0.02) | -0.02 (-0.08 to +0.05) | -0.02 (-0.05 to +0.01) |
| reader baseline | 0.80 (0.71-0.88) | 0.78 (0.69-0.87) | -0.02 (-0.06 to +0.01) | -0.05 (-0.14 to +0.03) | -0.00 (-0.01 to +0.00) |
| clinical-history (check) | 0.82 | 0.82 | 0.00 | 0.00 | 0.00 |

The clinical-history model uses no mask and is unchanged, as it should be.

E4 gains (score - reader baseline) under each mask set:

| gain | masks | dAUC | dA_W | dA_B |
|---|---|---|---|---|
| combined - reader | released | +0.02 (-0.03 to +0.08) | +0.08 (-0.04 to +0.18) | -0.01 (-0.06 to +0.05) |
| combined - reader | BraTS21 | +0.03 (-0.04 to +0.09) | +0.11 (-0.02 to +0.23) | -0.03 (-0.08 to +0.03) |
| imaging - reader | released | -0.09 (-0.19 to +0.02) | +0.10 (-0.04 to +0.26) | -0.21 (-0.31 to -0.10) |
| imaging - reader | BraTS21 | -0.15 (-0.25 to -0.05) | +0.04 (-0.07 to +0.15) | -0.27 (-0.36 to -0.15) |

Change in the gain (BraTS21 - released): combined - reader +0.00 (-0.04 to +0.05); imaging - reader -0.06
(-0.14 to +0.01).

Mask noise. Median fold change of the enhancing volume between consecutive scans <= 30 days apart (54 pairs, 46
patients): 2.57 with the released masks, 2.17 with BraTS21 (difference in median |log ratio| -0.17, -0.47 to -0.02).
TC: 2.76 -> 2.02. WT: 1.62 -> 1.60. This is the RESEGMENTATION.md result, reproduced.

Reading, by the rule fixed in the plan:
- **Not every result is robust.** The imaging model's paired difference excludes zero. With the BraTS21 masks its AUC
  falls from 0.71 to 0.63. The loss lies mostly within a time window (A_W -0.11). The imaging AUC therefore depends
  on the masks, and the paper must say so.
- **The combined model and the reader baseline do not depend on the masks.** Both paired differences include zero
  (-0.02 each).
- **The E4 reading is unchanged.** Under both mask sets, the combined model shows no clear gain over the reader
  baseline, overall or within a window. Neither does the imaging model. With the BraTS21 masks the imaging model is
  clearly below the reader baseline (-0.15, -0.25 to -0.05), where on the released masks the interval reached
  +0.02.
- **The less noisy segmenter does not help.** It reduces the short-gap ET noise (2.57 -> 2.17), but it does not
  improve any model. The imaging model gets worse.

## E6. Analyses asked for by the second review round (planned in REVIEW_ANALYSES_PLAN.md, 161b353; deviations 6474aad)

Code: `prism/analyses/review_analyses.py` (c2fc7f3). Output: `outputs/results/analyses/review_analyses/
e6_review_analyses.csv`. MU: the paper's three scores and the reader baseline, 5x5 grouped CV, intended use (146
scans, 62 progressions, 80 patients). LUMIERE: the locked models (178 scans, 73 progressions, 79 patients). One set of
2,000 patient bootstrap samples per cohort (seed 20261117), no refit; at MU each sample averages over the five
repeats and is drawn over the 88 patients of the widest set (secondary negatives). Checks before reading (asserted,
all passed): MU 0.822 / 0.709 / 0.821, reader 0.797; LUMIERE combined 0.773; the LUMIERE refit code reproduces the
locked clinical-history and combined scores exactly. Run time 7 s on 20 CPUs.

### E6a. Calibration (descriptive, no rule)

Intercept: calibration-in-the-large (slope fixed at 1; > 0 means the score under-predicts). Slope: < 1 means the
predictions are too spread out, > 1 too compressed. Prevalence reference: the Brier score of always predicting the
prevalence (MU 0.244, LUMIERE 0.242).

| cohort | score | intercept | slope | Brier |
|---|---|---|---|---|
| MU | clinical-history | -0.06 (-0.53 to +0.45) | 0.78 (0.37-1.61) | 0.170 (0.136-0.209) |
| MU | imaging | +0.24 (-0.10 to +0.62) | 0.75 (0.45-1.21) | 0.213 (0.185-0.244) |
| MU | combined | -0.05 (-0.51 to +0.41) | 0.75 (0.27-1.64) | 0.175 (0.142-0.213) |
| MU | reader baseline | +0.00 (-0.45 to +0.47) | 0.94 (0.63-1.43) | 0.177 (0.141-0.216) |
| LUMIERE | clinical-history (reduced) | -0.14 (-0.55 to +0.32) | 1.03 (0.60-1.89) | 0.214 (0.190-0.240) |
| LUMIERE | imaging | +0.41 (+0.15 to +0.70) | 1.91 (0.81-3.20) | 0.239 (0.215-0.266) |
| LUMIERE | combined (reduced) | -0.07 (-0.37 to +0.30) | 1.45 (0.85-2.57) | 0.195 (0.173-0.221) |
| LUMIERE | reader baseline | +0.07 (-0.23 to +0.47) | 0.74 (0.37-1.43) | 0.202 (0.179-0.228) |

UCSF-ALPTDG (not on hand; quoted from UCSF_RESULTS.md, locked models, grade 4, scan 2): calibration slope
clinical-history (A-Tbase) 0.37 (-0.39 to 1.28), imaging (A-Ipure) 0.85 (0.44-1.43), combined (A-T) 3.29
(1.96-6.28); O/E 0.67 (0.50-0.88), 1.24 (0.93-1.58), 0.72 (0.55-0.91).

Reading (descriptive):
- At MU the intercepts are near zero and every interval includes zero. The slopes of the three PRISM scores are about
  0.75-0.78: cross-validated predictions are somewhat too spread out. Every interval includes 1.
- At LUMIERE the reduced clinical-history and combined models are calibrated in the large (intercepts include zero).
  The imaging score under-predicts (intercept +0.41, interval above zero) and its predictions are compressed
  (slope 1.91); so are the combined model's (1.45). Both slope intervals include 1.
- At UCSF the combined model is strongly compressed (slope 3.3) and over-predicts (O/E 0.72), as reported there.
- Every score has a lower Brier score than the prevalence reference at MU and LUMIERE; the LUMIERE imaging score
  only barely (0.239 against 0.242). The scores rank better than they are calibrated across sites, so a probability shown to a reader
  would need local recalibration.

### E6b. Scans shortly before progression (MU, intended use)

Models trained as now (primary negatives); evaluated with the secondary negatives (every index scan before
progression, whatever the follow up): 62 progressions against 173 negatives (88 patients). That adds 89 negative
scans (67 patients) that the primary label drops.

| score | AUC, primary negatives | AUC, secondary negatives | change | AUC, added scans only vs progression |
|---|---|---|---|---|
| clinical-history | 0.822 (0.746-0.897) | 0.807 (0.758-0.854) | -0.015 (-0.062 to +0.030) | 0.792 (0.739-0.847) |
| imaging | 0.709 (0.631-0.785) | 0.655 (0.590-0.720) | **-0.054 (-0.089 to -0.018)** | 0.604 (0.539-0.674) |
| combined | 0.821 (0.745-0.888) | 0.780 (0.730-0.826) | -0.041 (-0.084 to +0.004) | 0.742 (0.682-0.801) |
| reader baseline | 0.797 (0.705-0.882) | 0.769 (0.709-0.827) | -0.028 (-0.080 to +0.028) | 0.743 (0.671-0.811) |

Gains over the reader baseline (score - reader):

| score | primary negatives | secondary negatives |
|---|---|---|
| combined (planned outcome) | +0.023 (-0.039 to +0.082) | +0.010 (-0.034 to +0.057) |
| clinical-history | +0.025 (-0.043 to +0.097) | +0.037 (-0.009 to +0.087) |
| imaging | -0.088 (-0.195 to +0.022) | -0.115 (-0.192 to -0.035) |

Reading, by the rule fixed in the plan:
- **Not robust for the imaging model.** Its AUC falls by 0.054 (0.709 to 0.655), which is not less than 0.05; the
  paper must state this change. The clinical-history (-0.015) and combined (-0.041) changes are below 0.05. The
  reader baseline changes by -0.028.
- **The reader-baseline reading is unchanged.** No PRISM score has a gain whose interval lies above zero; combined -
  reader is +0.010 (-0.034 to +0.057). With the secondary negatives the imaging model is clearly below the reader
  baseline (-0.115, -0.192 to -0.035), where with the primary negatives its interval reached +0.022.
- The dropped scans are the harder negatives: against the progression scans every score separates them less well
  than the primary negatives, most of all the imaging score (0.60).

### E6c. Unknown IDH and MGMT status as its own category

An indicator per marker (status not available at the scan: unknown, or scan before diagnosis) was added to the
clinical-history and combined models at MU (refitted in the same folds) and to the locked reduced models at
LUMIERE (refitted once on MU). Unknown in the MU primary set: IDH 6, MGMT 20 scans; at LUMIERE: IDH 68, MGMT 16
scans.

| cohort | score | AUC, current coding | AUC, indicator coding | paired difference |
|---|---|---|---|---|
| MU | clinical-history | 0.822 | 0.829 (0.754-0.906) | +0.007 (-0.000 to +0.016) |
| MU | combined | 0.821 | 0.821 (0.745-0.889) | +0.001 (-0.005 to +0.008) |
| LUMIERE | clinical-history (reduced) | 0.689 (0.604-0.795) | 0.685 (0.615-0.765) | -0.004 (-0.087 to +0.082) |
| LUMIERE | combined (reduced) | 0.773 (0.683-0.859) | 0.737 (0.674-0.807) | -0.035 (-0.100 to +0.035) |

Reading, by the rule fixed in the plan:
- **Robust.** Every paired interval includes zero. At MU the clinical-history interval only just does (lower bound
  -0.0002). At LUMIERE, where IDH is unknown in 68 of 178 scans, the locked combined model loses 0.035 with the
  indicator, and the interval is wide.

### E6d. The reduced combined model on MU (descriptive)

The reduced combined model (design T, the model locked and applied externally), cross-validated on MU in the same
folds, intended use:

| model | AUC |
|---|---|
| full combined (B1 + I_pure) | 0.821 (0.745-0.888) |
| reduced combined (T) | 0.804 (0.732-0.879) |
| reduced - full | -0.017 (-0.071 to +0.036) |

Reading (descriptive): the reduced model that was applied at LUMIERE and UCSF reaches 0.80 on MU, 0.02 below the
full combined model, with an interval that includes zero.


## UCSF-ALPTDG added (2026-11-19)

The UCSF data were restored on 2026-11-19 and M1 and M2 were run on UCSF as the plan fixes (context `rt_phase`;
context-only score MU's rate for the matching stratum, MU's pooled rate for `no_rt` and `rt_date_unknown`; M2 groups
the card's situation, MU calibration split seed 0). Checks: the locked UCSF AUCs reproduce (0.561 / 0.726 / 0.856);
the registered marginal sets equal the system's; the MU and LUMIERE rows of every output are unchanged. Grade 4 scan 2,
69 scans of 69 patients, 29 progression. Share of pairs within one context w = 0.88 (0.76-0.98): almost all scans are
later than 12 weeks after radiotherapy, so A_B rests on few pairs.

| cohort | score | AUC | within context A_W | across contexts A_B |
|---|---|---|---|---|
| UCSF | clinical-history | 0.56 (0.42-0.70) | 0.56 (0.41-0.70) | 0.56 (0.05-1.00) |
| UCSF | imaging | 0.73 (0.59-0.84) | 0.73 (0.60-0.85) | 0.66 (0.46-0.84) |
| UCSF | combined | 0.86 (0.76-0.94) | 0.87 (0.78-0.95) | 0.73 (0.21-1.00) |
| UCSF | context only | 0.49 (0.43-0.55) | 0.50 (0.50-0.50) | 0.43 (0.00-1.00) |
| UCSF | enhancing volume | 0.88 (0.79-0.95) | 0.89 (0.81-0.96) | 0.75 (0.44-1.00) |

M2, combined model, 80% sets (groups with at least 9 scans):

| group | n | marginal (registered) | group-conditional |
|---|---|---|---|
| all | 69 | 0.78 (0.68-0.87) | 0.77 (0.67-0.87) |
| progression | 29 | 0.97 (0.89-1.00) | 0.97 (0.89-1.00) |
| no progression | 40 | 0.65 (0.49-0.79) | 0.62 (0.47-0.77) |
| later_post_rt × et_not_increased | 28 | 0.61 (0.42-0.79) | 0.54 (0.33-0.72) |
| later_post_rt × et_increased | 25 | 0.92 (0.80-1.00) | 0.96 (0.86-1.00) |
| later_post_rt × et_absent | 12 | 0.92 (0.73-1.00) | 0.92 (0.73-1.00) |

Reading (descriptive): at UCSF the AUC split adds little, because nearly every pair lies in one window. Group
calibration did not lift the least covered group (later, enhancement not increased).
