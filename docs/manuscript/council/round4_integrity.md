# Council round 4, lens: integrity after the new analyses (NUMBERS.md section 12)

Reviewer only; `paper/` not edited. Rule applied: RESERVE.md, "hide only what leaves the conclusion unchanged".
Capabilities stay first and moderate; each qualification is one clause or sentence. All numbers are from NUMBERS.md
12A-12F (EXPLORATORY unless noted; 12F UCSF is the planned secondary).

## Verdicts

| # | Question | Verdict |
|---|---|---|
| 1 | Class-conditional undercoverage | **Main text and abstract.** It changes what "coverage met" means: it is met on average, not for each outcome. |
| 2 | Ranking transfers, calibration and threshold do not (UCSF) | **Main text (3.2), Discussion, Limits, abstract clause, Conclusion word.** "Transfers" must mean ranking. Detail table to supplement. |
| 3 | Which agreement rule | **MU-fixed is the system's rule** (the only one a live system can compute). One clause reports that cohort medians did not show the LUMIERE effect. |
| 4 | Ladder middle step | Report the step with its interval and say it includes 0. Never "each step raised AUC". |
| 5 | ET-volume baselines | **Main text + Fig 2 reference bar.** Per-cohort ET-change baselines to supplement. |

## 1. Class-conditional coverage (12B)

Why main: the planned claim is marginal coverage >= 0.78. Marginal coverage is a prevalence-weighted average, so UCSF
(0.783) and LUMIERE hide LUMIERE progression 0.767 (0.671-0.872) and UCSF non-progression 0.650 (0.511-0.791); the
other class is over-covered (UCSF progression 0.966, LUMIERE non-progression 0.943). A reader who takes "the set
contains the true outcome for 80%" as a per-patient promise would be wrong at both centres. The conclusion about the
confidence changes in kind, not size, so this is not RESERVE material. Mondrian numbers (0.514, 0.175) stay in the
supplement; one clause says class-specific thresholds fitted on MU did not repair it.

Replace in 3.4, the todo (after "...within each cohort (\todo{Supplementary section: system results}).")
> Coverage also differed by outcome. At LUMIERE the sets covered 0.77 (0.67--0.87) of progression scans against 0.94
> of non-progression scans, and at UCSF 0.65 (0.51--0.79) of non-progression scans against 0.97 of progression scans;
> on MU the two were similar (0.82 and 0.83). The sets therefore keep their coverage on average, not within each
> outcome, and class-specific thresholds fitted on MU did not repair this (Supplementary Section~\todo{system results}).

Heading 3.4 and Fig 4 title: "The conformal sets of the combined score keep their coverage on average, not within each
outcome" (drop "meet their coverage threshold ... at all three centres"). Fig 4 caption: add "Coverage by outcome class
is in Section 3.4; the average hides a shortfall for one class at LUMIERE and UCSF-ALPTDG."
Abstract (replaces the last sentence; recount with `wc -w`, the proposal is 150 words):
> Conformal sets for the combined score met their planned coverage on average at every centre but fell short for one
> outcome at LUMIERE and UCSF-ALPTDG, and after one revision every report passed a check against its record.
Cuts to stay at 150: "scan where progression was called" -> "progression scan"; "applied unchanged," -> "unchanged,".
Introduction, last sentence: replace "met their pre-specified coverage on point estimates at all three centres, at UCSF
exactly at the threshold," with "met their pre-specified coverage on average at all three centres, at UCSF exactly at
the threshold, but not within each outcome class,".
Limits: replace "The coverage threshold was met on point estimates, and at UCSF the interval reached below it;" with
"The coverage threshold was met on average and on point estimates, not for each outcome class, and at UCSF the
interval reached below it;".
RESERVE: the row "Does coverage hold within situations, or with Mondrian conformal?" currently says "Not uniformly:
... UCSF non-events 0.65 ... The marginal combined set is the planned claim." After the change the 0.65 is in the main
text; rewrite the row to situations (MU later post-RT 0.74) and Mondrian only, pointing to 3.4.

## 2. Calibration and the MU threshold (12D, 12F)

Why main: AUC says the ranking transfers; the clinician and the reader of "transfers without refitting" will assume
the score also reads as a risk. At UCSF it does not (slope 3.29 (1.96-6.28), O/E 0.72 (0.55-0.91), mean risk 0.59
against 0.42 observed); a threshold fixed on MU calls 90% of UCSF scans positive (sensitivity 1.00, specificity 0.175
(0.06-0.30)) and 66% at LUMIERE (0.89 / 0.50). At LUMIERE calibration in the large holds (O/E 0.97, slope 1.45
(0.85-2.54)). Cause is not established; a likely one is the timing inputs extrapolating (the interval between two
scans at UCSF); say "consistent with", not more.

3.2, replace the round-4 todo (second half; ET part is item 5):
> The ranking transferred, the risk scale did not. At LUMIERE the combined score was calibrated in the large (observed
> over expected 0.97, 0.81--1.14); at UCSF it overpredicted (0.72, 0.55--0.91) and its slope was 3.3 (2.0--6.3). A
> threshold set at the MU median called 66% of LUMIERE and 90% of UCSF scans positive (specificity 0.50 and 0.18), so a
> new centre needs to recalibrate before the score is read as a probability or cut at a threshold
> (Supplementary Section~\todo{external calibration and operating points}).
3.2 heading: "The models rank scans at two external centres without refitting".
Abstract: after "against 0.86 when trained there" add "; its risk scale did not transfer to UCSF-ALPTDG" (+9 words,
cut 9 elsewhere: e.g. "most surveillance datasets lack treatment dates, centres document progression differently and
the hardest scans are few" -> "most datasets lack treatment dates, centres document progression differently and the
hardest scans are few").
Discussion P1, after "...a model fitted at the centre can do better;" add: "the score's ranking transferred but not its
scale at UCSF, so a deployment would recalibrate on local scans;".
Limits, new sentence: "The combined score overpredicted progression at UCSF and a threshold fixed on MU did not
hold there, so PRISM's risk scale needs local recalibration."
Conclusion: "its models held at two other centres" -> "its models ranked scans at two other centres".
2.3: add calibration and operating point to the list of exploratory analyses (UCSF calibration was planned; LUMIERE
and the operating points were not).

## 3. Agreement rule (12A)

Principle: the rule is defined post hoc already (2.3). Of the two post hoc variants, present the one that is
computable at a scan: medians fixed on MU (the locked models' MU training-set medians). The cohort-median result is
disclosed in one clause because choosing the variant after seeing it flips LUMIERE (cohort medians +0.105 (-0.049 to
+0.266); MU-fixed +0.222 (+0.102 to +0.337)); a reader must see that the finding depends on the rule. For MU use the
fold-held-out median (+0.313 (+0.184 to +0.431), AUC 0.90 / 0.59, 40% flagged), equal to the in-sample figure.

2.1, replace the todo: "...of that pathway's median score among the MU training scans of the locked models (for MU
itself, among the other folds' out-of-fold scores); the rule uses scores only, never labels."
3.4 P2, replace the sentences from "At LUMIERE and UCSF..." through the todo:
> With medians fixed on MU, disagreement also picked out less accurate scans at LUMIERE (AUC 0.89 where the pathways
> agreed, 0.67 where they disagreed; difference 0.22, 0.10--0.34) but not at UCSF (0.13, $-$0.10 to 0.40). The
> warning is blunt: it flagged 60% of LUMIERE and 48% of UCSF scans against 40% at MU. With medians taken from each
> cohort's own scans, the LUMIERE difference was smaller and its interval included zero (0.11, $-$0.05 to 0.27).
Strict rule (disagree and set holds both): 12% flagged at MU (S2 +0.376), 30% at LUMIERE (+0.227, 0.054-0.398), UCSF
CI includes 0; keep as the existing supplement pointer, add LUMIERE to its one-line summary only.
Table 2 S2 row, "Met": "Disagreement at MU-Glioma-Post; at LUMIERE only with medians fixed on MU (exploratory); none
at UCSF-ALPTDG"; the "planned" result (cohort medians) stays MU only, labelled. S3 row: LUMIERE MU-fixed +0.115
(+0.049 to +0.190) also meets S3, UCSF +0.023 does not. Fig 4B caption: replace "at LUMIERE and UCSF-ALPTDG
disagreement did not pick out the less accurate scans" with "with medians fixed on MU, disagreement also marked the
less accurate scans at LUMIERE but not at UCSF-ALPTDG". Limits: replace "the disagreement warning picked out less
accurate scans only at MU" with "the disagreement warning picked out less accurate scans at MU and LUMIERE but not
UCSF, and flagged about half of the scans there".
Do not claim the rule "generalises"; two cohorts, one post hoc.

## 4. Ladder middle step (12E)

3.3, replace "gave the image pathway, 0.05 higher (\todo...)," with:
> gave the image pathway, 0.05 higher (95\% CI $-$0.00 to 0.11, so the gain is not distinguishable from zero),
(use $-$0.003; round to $-$0.00 only with the sign shown, else write "$-$0.003 to $+$0.106"). Follow with: "and adding
the three schedule inputs ... raised the AUC by a further 0.10 (0.05--0.15) across phases of care but not within them
($-$0.01, $-$0.06 to $+$0.04)". Within phase the middle step is also nil ($-$0.003, $-$0.095 to $+$0.080); say nothing
stronger than "the only clear gain came with the schedule inputs". Never write "each step raised AUC". Fig 3C caption:
same wording. The image pathway keeps the change features on design grounds (they are the pathway's definition and are
what UCSF's planned test used), not because the step is proven.

## 5. Enhancing-volume baselines (12C)

Fig 2: add one reference bar per cohort, "enhancing tumour volume alone" (MU-IU 0.62, 0.53-0.72; LUMIERE 0.66,
0.56-0.75, 163 of 168 scans have ET; UCSF 0.88, 0.79-0.95). Use 0.622 for MU, not 0.635 (other row set). ET change
alone: supplement (MU 0.49, LUMIERE 0.63, UCSF 0.82); say only in the supplement that change alone is at chance on MU.
3.2, replace the ET part of the todo (before the calibration sentences above):
> A reference that uses no model, the log enhancing tumour volume alone, scored 0.62 (0.53--0.72) on MU, below the
> image pathway, and 0.66 (0.56--0.75) on LUMIERE, as high as the image pathway (0.65), and 0.88 at UCSF (Section 3.3).
Integrity point: at LUMIERE the image pathway adds nothing over enhancing volume, which belongs in the main text (it
is the same finding as at UCSF, in weaker form). At MU volume alone is clearly below the image pathway, which
supports the image pathway having something beyond volume there; say so only as "below".
Fig 2 caption: replace the todo with "The grey bar is the log enhancing tumour volume of the scan alone, with no fitted
model."

## Claims to re-check before the abstract is approved
- "transfers" / "held" anywhere in Intro, Discussion, Conclusion: means ranking only.
- "met ... coverage" anywhere: add "on average".
- Any sentence that says disagreement works only at MU (Limits, Fig 4B caption, Table 2).
- 2.3 exploratory list: add MU-fixed agreement, class-conditional coverage CIs, ET baselines, operating points,
  LUMIERE calibration (UCSF calibration is planned).
