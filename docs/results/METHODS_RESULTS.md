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
| LUMIERE | enhancing volume | 0.56 (0.43-0.68) | 0.61 (0.46-0.75) | 0.41 (0.29-0.53) | -0.21 (-0.36 to -0.04) |

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
