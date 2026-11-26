# Council round 4: editor's decisions

Applied to `paper/main.tex` on 2026-10-26 from `round4_integrity.md` and `round4_trim.md` under the coordinator's
rulings. Everything is pending the author's approval; the backup is tag `backup-before-council-2026-10-26`. LOCKED.md
was not touched; the abstract remains a flagged proposal (`[PROPOSED, awaiting approval]`). Every `\todo{round 4: ...}`
is filled; none remains. New numbers come from NUMBERS.md section 12 (SYSTEM_RESULTS.md, review-round-3 sections A to F).

Status words: **applied**, **modified** (point taken, text changed differently, reason given), **rejected** (reason
given).

## Coordinator rulings and how they were applied

1. **Conclusion.** One sentence (trim C29 fallback), rewritten so that "transfer" means ranking: "PRISM keeps image and
   treatment-timeline evidence apart and shows the clinician both scores at every scan with how far each has been
   tested there; its models ranked scans at two other centres without refitting."
2. **Agreement rule.** 2.1 now defines the rule with medians fixed on MU (the locked models' MU training scans; on MU,
   the other folds' held-out scores), "so the rule can be applied at a single scan". 3.4 P2: disagreement picked out
   the less accurate scans at MU and LUMIERE (LUMIERE 0.89 / 0.67, difference 0.22, 0.10 to 0.34); the UCSF interval
   includes zero; the warning flags 60% / 48% of scans; one clause gives the cohort-median result (the rule of the
   tests fixed in advance): LUMIERE 0.11, −0.05 to 0.27. 2.3 lists the MU-fixed version as exploratory. Table 2: the
   S2 / S3 Result cells keep the planned (cohort-median) numbers; the Met cells add "LUMIERE (disagreement, medians
   fixed on MU, exploratory)"; note a now names both median rules. Figure 4 title and panel B aligned. MU numbers
   unchanged (fold-held-out median gives the same 40%, 0.90, 0.59).
3. **Coverage.** Abstract: "met their planned coverage on average at every centre but fell short for one outcome at
   both external centres" (150 words, flag kept). Introduction: "on average at all three centres, but not within each
   outcome class". 3.4 heading "The confidence keeps its coverage on average and states where the evidence is thin"
   (also the trim's buried-capability fix: the card is in the heading). 3.4 P1: coverage by outcome (LUMIERE progression
   0.77, 0.67 to 0.87; UCSF non-progression 0.65, 0.51 to 0.79; 0.94 and 0.97 for the other outcome; MU similar) and one
   clause that MU-fitted class thresholds did not correct it. Figure 4 title "on average"; panel A note on the outcome
   shortfall. Table 2 S1 "met on average".
4. **Transfer = ranking.** 3.2 heading and Figure 2 title "The models rank scans at two external centres without
   refitting". New 3.2 paragraph: AUCs describe ranking; the combined score was calibrated in the large at LUMIERE
   (exploratory) and overpredicted at UCSF (O/E 0.72, 0.55 to 0.91; planned secondary); a threshold at the MU median
   (exploratory) called 90% of UCSF scans positive; a new centre recalibrates; pointer
   `\todo{Supplementary section: calibration and thresholds}`. Discussion P1: "What transferred was the ranking, so a
   group deploying PRISM at a new centre would recalibrate the score and set its threshold on local scans." Limits:
   "the two external tests are its only evidence that its ranking of scans transfers; at UCSF its risk scale did not."
   Introduction: "the ranking of scans by the models fitted there transferred". Discussion P1 S1 "ranks scans at two
   external centres".
5. **Ladder.** 3.3: the middle step "0.05 higher with an interval that included zero (−0.00 to +0.11)"; the schedule
   step "by a further 0.10 (0.05–0.15) across phases of care but not within them". Figure 3 caption: "the interval of
   the second step includes zero". "Each step raised AUC" appears nowhere.
6. **Enhancing-volume baselines.** 3.2 P1: enhancing tumour volume alone (exploratory) 0.62 on MU, below the image
   pathway, 0.66 on LUMIERE, as high as the image pathway, "so at LUMIERE the transfer rests on the combined score"
   (the honest LUMIERE clause). Figure 2 caption: "The grey bar is the log enhancing tumour volume of the scan alone,
   with no fitted model (exploratory)"; figure slot text names the bar. CIs for the bars live in Figure 2 (one number
   per claim in prose). ET change alone: RESERVE / supplement only.
7. **Capabilities first; one caveat per claim.** Each new caveat sits once beside its result; the round-3 Limits
   restatement of coverage and disagreement was deleted (C25) rather than updated. The transfer caveat appears in 3.2,
   the Discussion builder sentence and the Limits because the ruling asked for all three; the abstract does not carry
   it (see integrity item 2 below).

## Integrity review (round4_integrity.md)

| # | Item | Status | Note |
|---|---|---|---|
| 1 | Class-conditional coverage in 3.4 | modified | Integrity's text tightened (the two shortfalls in one sentence, "against 0.94 and 0.97 for the other outcome"); the summarising "on average, not within each outcome" clause dropped from 3.4 because it is a contrast slogan and the heading carries "on average". It replaces "uneven across situations within each cohort" (trim's suggestion); situations stay in RESERVE and on the card. Mondrian numbers not quoted (supplement). |
| 1 | 3.4 heading / Fig 4 title | modified | "on average" per the ruling; "not within each outcome" omitted from the heading (slogan; capability first); the card added to the 3.4 heading (trim buried capability 3). |
| 1 | Abstract coverage sentence | applied | Cuts: "most surveillance datasets" → "most datasets"; "the scan where progression was called" → "the progression scan"; "applied unchanged" → "unchanged"; plus "treatment-timeline" → "timeline", "a report from a local language model" → "a local language model's report", "enhancing tumour volume" → "enhancing volume", "Conformal sets for the combined score" → "The combined score's conformal sets". 150 words (`wc -w`, flag excluded). |
| 1 | Introduction coverage | applied | With trim C1 (UCSF threshold clause dropped; it stays in 3.4). |
| 1 | Limits coverage sentence | rejected | Replaced by C25 deletion: the result lives in 3.4 (one caveat per claim). |
| 2 | 3.2 calibration and threshold | modified | Own paragraph after the UCSF results (the todo sat in the LUMIERE paragraph, before UCSF is introduced). "The ranking transferred, the risk scale did not" rewritten (contrast slogan). One number with CI (UCSF O/E); slope 3.29, LUMIERE O/E and specificities to the supplement table and RESERVE. |
| 2 | 3.2 heading | applied | Also Figure 2 title. |
| 2 | Abstract clause on the risk scale | rejected | Did not fit in 150 words with the coverage sentence; the coordinator's ruling places the transfer caveat in 3.2, the Discussion and the Limits. The abstract quotes only AUCs, which are rankings. Flag for the author. |
| 2 | Discussion P1 builder clause | modified | A separate sentence ("What transferred was the ranking, so ...") rather than a clause in the long S2. |
| 2 | Limits sentence | modified | Folded into the first Limits sentence (with C23). |
| 2 | Conclusion "ranked scans" | applied | |
| 2 | 2.3 exploratory list | applied | Adds the MU-fixed rule, coverage by outcome, enhancing-volume references, LUMIERE calibration (UCSF planned), the MU-threshold operating point. |
| 3 | Agreement rule | applied | Ruling 2. Strict rule: RESERVE row updated with the MU-fixed LUMIERE line; no main-text sentence (C17). |
| 4 | Ladder middle step | applied | Ruling 5. Interval written −0.00 to +0.11 with the sign shown. |
| 5 | ET baselines | applied | Ruling 6. |

## Trim review (round4_trim.md)

| Cut | Words | Status | Note |
|---|---|---|---|
| C1 Intro UCSF threshold clause | 6 | applied | |
| C2 "We meet the third challenge" | 13 | applied | |
| C3 schedule-input history | 25 | applied | |
| C4 record-only clause | 11 | applied | |
| C6 "on one GPU" in 2.1 | +3 | applied | Pairs with C19. |
| C7 2.2 cohort descriptions | 31 | applied | |
| C8 2.2 120-day sentence | 14 | applied | |
| C9 2.3 split-variance reason | 23 | applied | |
| C10 2.3 plan deviation | 26 | applied | RESERVE "Where" updated. |
| C11 2.3 stricter rule in list | 4 | applied | Merged into the rewritten list. |
| C13 3.1 all-glioma sentence | 28 | applied | Clause appended to the Table 2 note; RESERVE row added. |
| C15 3.2 UCSF combined-score explanation | 24 | applied | Figure 2 caption keeps the interval; RESERVE row updated. |
| C17 3.4 stricter-rule pointer | 25 | applied | |
| C18 3.4 tier definition | 5 | applied | |
| C19 3.5 model-size sentence | 18 | applied | Pointer moved; Table 2 L1 "(supplement)". |
| C20 Discussion P1 third sentence | 11 | applied | |
| C21 combined-score definition | 8 | applied | Figure 1 caption definition kept (outside budget). |
| C22 three same-cohort studies | 8 | applied | |
| C23 Limits patient counts | 10 | applied | |
| C25 Limits coverage / disagreement | 27 | applied | Also removes the now-wrong "only at MU". |
| C26 Limits checker scope | 6 | applied | |
| C27 Limits 120-day | 9 | applied | |
| C28 future work | 10 | applied | |
| C29 Conclusion | 52 | modified | Coordinator: one-sentence fallback (saves 18). |
| R4 agreement restatement | 11 | modified | Rewritten with the MU-fixed definition and the on-MU held-out median; "so the rule can be applied at a single scan" added. |
| Tier B C5 refit caveat | 16 | applied | Needed for the budget; pointer moved after "30%"; RESERVE row updated. |
| Tier B C12 marking convention | 7 | applied | |
| Tier B C14 LUMIERE pathway levels | 4 | rejected | The ET sentence compares with the image pathway's 0.65, which must stay in prose. |
| Tier B C16 deep-network sentence | 14 | applied | Needed for the budget; the control result is Table 2 Q4. |
| Tier B C24 Limits UCSF count | 6 | applied | Needed for the budget; Table 1 holds 29 / 40. The Limits now carry no count. |
| Tier B C30 Intro three parts | 13 | rejected | Trim leaned to keep; first sight of the capability. |
| Buried capability: 3.5 "segmentation figure and its volumes" | +4 | applied | |
| Buried capability: Discussion P1 "in a report written inside the hospital" | +7 | applied | |
| Buried capability: 3.4 heading names the card | | applied | Ruling 3. |

## Word counts (main text; round-4 counter: comments, todos, flags, citations and references stripped; abstract excluded; headings not counted; reproduces 3,992 on commit 18d7861)

| Section | Before | After |
|---|---|---|
| Abstract | 150 | 150 |
| Introduction | 514 | 519 |
| Methods 2.1 PRISM | 754 | 704 |
| Methods 2.2 Cohorts and the task | 324 | 279 |
| Methods 2.3 Evaluation | 391 | 365 |
| Results 3.1 | 162 | 134 |
| Results 3.2 | 191 | 272 |
| Results 3.3 | 347 | 345 |
| Results 3.4 | 343 | 397 |
| Results 3.5 | 179 | 165 |
| Discussion | 735 | 684 |
| Conclusion | 52 | 34 |
| **Total (excluding abstract)** | **3,992** | **3,898** |

The first pass with all tier A cuts and the integrity text landed at 4,001: the integrity sentences ran longer than the
trim's 120 to 150 word estimate. The CIs for the enhancing-volume references and the UCSF agreement numbers moved to
Figure 2 and the supplement, the calibration paragraph was shortened, and tier B C5, C16 and C24 were taken.

## Self-check (META_PATTERNS checklist, every changed sentence)

- Concrete subjects: "the sets covered", "a threshold ... called", "the warning ... flagging", "a group deploying PRISM".
  "The transfer there rests on the combined score" (3.2) is the one abstract subject left; kept because it is the
  honest clause the ruling asked for and is short.
- Contrast slogans removed from the integrity text: "The ranking transferred, the risk scale did not"; "on average, not
  within each outcome" (3.4 text and heading). Kept as plain qualifications: "but not within each outcome class"
  (Introduction), "at UCSF its risk scale did not" (Limits).
- No em dashes, intensifiers, RANO, "published" or -ize spellings (grep).
- Verdict words: none added ("added nothing" avoided; the new text uses "fell short", "included zero").
- Numbers: one per claim with CI on the new headline numbers (class coverage, LUMIERE agreement, UCSF O/E, ladder
  steps); the other numbers live in Figure 2, Table 2, the supplement or RESERVE. No new number is repeated across text,
  table and caption.
- Planned vs exploratory: each new analysis is in the 2.3 list and marked "(exploratory)" where it first appears in
  its paragraph; UCSF calibration is the planned secondary and is not marked.
- Always-in-main list intact: intended-use 0.60 (3.1), timing baseline (3.1, 3.2), within-phase result (3.1, 3.3),
  planned vs exploratory (2.3), scope limits (one centre, documented label, no clinician read), contradicting results
  (the all-glioma gain in the Table 2 note; class undercoverage and the risk scale now in the main text).
- Locked text untouched.

## Open for the author

- Abstract proposal: coverage sentence changed; the risk-scale clause did not fit (integrity item 2).
- `\todo{Supplementary section: calibration and thresholds}` is a new supplement section to write (12D, 12F detail:
  slopes, O/E, sensitivity and specificity at the MU median in each cohort).
- Figure 2 needs the grey enhancing-volume bar; Figure 4 panel B needs the MU-fixed rule at LUMIERE and UCSF.
