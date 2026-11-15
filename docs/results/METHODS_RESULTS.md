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
| MU | clinical-history | 0.82 (0.75-0.90) | 0.64 (0.51-0.78) | 0.94 (0.88-0.97) | 0.30 (0.16-0.43) |
| MU | imaging | 0.71 (0.63-0.78) | 0.68 (0.58-0.77) | 0.73 (0.64-0.81) | 0.05 (-0.04 to 0.14) |
| MU | combined | 0.82 (0.75-0.89) | 0.65 (0.52-0.78) | 0.92 (0.88-0.96) | 0.27 (0.15-0.40) |
| MU | context only | 0.70 (0.60-0.80) | 0.34 * | 0.93 (0.86-0.98) | |
| MU | enhancing volume | 0.62 (0.53-0.71) | 0.68 (0.54-0.80) | 0.59 (0.49-0.69) | -0.09 (-0.22 to 0.05) |
| LUMIERE | clinical-history | 0.69 (0.60-0.80) | 0.59 (0.49-0.71) | 0.96 (0.89-1.00) | 0.37 (0.23-0.49) |
| LUMIERE | imaging | 0.65 (0.57-0.73) | 0.71 (0.60-0.80) | 0.51 (0.39-0.63) | -0.20 (-0.34 to -0.04) |
| LUMIERE | combined | 0.77 (0.68-0.86) | 0.72 (0.60-0.82) | 0.93 (0.86-0.99) | 0.22 (0.12-0.34) |
| LUMIERE | context only | 0.62 (0.57-0.70) | 0.50 | 0.96 (0.88-1.00) | |
| LUMIERE | enhancing volume | 0.56 (0.43-0.68) | 0.61 (0.46-0.75) | 0.41 (0.30-0.53) | -0.21 (-0.36 to -0.04) |

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
closes the two known blind spots (B1, B2) and the held-out direction rewrite (B3). B4 and B5 were already caught by
the frozen checker (the wrong value is not in the cited sentence's own field). Remaining blind spots, unchanged by
the verifier: removing the conformal statement (40% of real reports pass without it; the frozen v3.1 rule does not
require the statement as such, and its removal is caught only when it also removes a required flag mention) and swapping the card's tier word (33% to 45% of real mutants
pass; a swap to "tested" has no pattern to catch). The template and the language model are caught equally on every operator.
