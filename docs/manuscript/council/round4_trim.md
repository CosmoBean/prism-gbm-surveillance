# Council round 4: trim to budget and show/hide balance

Reviewer only; `paper/main.tex` not edited. Read: STYLE.md (80/20, always-in-main list), META_PATTERNS.md, OUTLINE.md,
RESERVE.md, round3_decisions.md (its trim candidates), then main.tex at commit 18d7861.

**Where we are.** Main text 3,992 words (same counter and scale as rounds 2 and 3: comments, todos, flags, citations
and references stripped; abstract excluded; section headings not counted). Round 4 adds about four to six sentences
(class-conditional coverage, calibration and threshold transfer, MU-fixed agreement, ET-volume baseline): I budget
120 to 150 words for them. Target after round 4: at most 3,900.

**What this file proposes.** Tier A: 25 cuts, **391 words**, none of which changes what a reader concludes; every
number or caveat removed from the prose already lives in a table, a caption, another section, the supplement pointer
or RESERVE.md, and the file says where. Tier B: 6 further cuts, 60 words, that are the editor's call (each removes a
small disclosure that a reviewer could ask for). One saving of 11 words falls out of round 4's own 12A edit. Simulated:
tier A alone brings the text to 3,601; with round 4's additions it lands at about 3,720 to 3,750, so the editor can
reject up to about 150 words of tier A and still meet the budget. Tier A plus tier B: 3,541.

Words saved are measured with the council counter on the quoted text (old minus new). Quoted text is the exact
main.tex string, line breaks removed; each was checked to exist once.

---

## Tier A: cuts that leave the conclusion unchanged (391 words)

Ordered by section. "Destination" says where the removed content already lives or should go.

### Introduction

**C1. Intro P5, the UCSF coverage clause (6 words).**
> "...met their pre-specified coverage on point estimates at all three centres, at UCSF exactly at the threshold, and after one revision of the prompt..."

→ delete ", at UCSF exactly at the threshold".
Destination: 3.4 ("At UCSF the point estimate sat at the threshold and its interval reached below it"). The same caveat
is now in the Introduction, 3.4 and the Limits (C25). STYLE 6: a caveat once, where it applies. "On point estimates"
stays in the Introduction, so nothing is overclaimed.

### Methods 2.1

**C2. 2.1 P1, last sentence (13 words).**
> "We meet the third challenge, small cohorts, in how we evaluate PRISM (Section~\ref{sec:2.3})."

→ delete. Destination: Intro P2 already says "Repeated cross-validation addresses the third challenge", and 2.3 opens
on the design.

**C3. 2.1 P3, the schedule-input history (25 words).**
> "It holds no dates, intervals or treatment flags. A single-scan version keeps only the 19 measurements of the current scan. We defined these inputs after finding that the planned imaging model contained three inputs that encode the scan schedule (Section~\ref{sec:3.3}). Such inputs belong to the timeline pathway, because they carry when a scan was taken, which the timeline already holds, and the image pathway has to run where no dates exist."

→ "It holds no dates, intervals or treatment flags, because such inputs carry when a scan was taken, which the
timeline already holds, and the image pathway has to run where no dates exist (Section~\ref{sec:3.3}). A single-scan
version keeps only the 19 measurements of the current scan."
Why: "We defined these inputs after finding..." is project history (META 14). The exploratory status of the
definition is in the 2.3 list; the three schedule inputs are named in the 3.3 ladder sentence, which the pointer
reaches. The cold reader's "why are schedule inputs excluded" (round 3 ruling 5) is kept word for word.

**C4. 2.1 P4, the record-only clause (11 words).**
> "PRISM renders the report's figure from the same masks by code, and the language model receives only the record, not the image."

→ "PRISM renders the report's figure from the same masks by code."
Destination: 2.1 P7 says the model "receives only the record" four sentences later.

**C6. 2.1 P7 (adds 3 words; pairs with C19).**
> "The model (Qwen3.8-27B) runs offline at temperature 0 and receives only the record;"

→ "The model (Qwen3.8-27B) runs offline on one GPU at temperature 0 and receives only the record;"
Why: keeps the one-GPU feasibility fact when C19 removes the 3.5 sentence that carried it.

### Methods 2.2

**C7. 2.2 P1, cohort descriptions duplicated in Table 1 (31 words).**
> "PRISM was developed on MU and tested on LUMIERE and UCSF, in each case on grade 4 glioma as the primary population, with models fitted once on MU and applied unchanged, which we call locked (Table~\ref{tab:1}). MU records the dates of surgery, radiotherapy and chemotherapy \citep{mahmoud2025}. LUMIERE records no treatment dates, and the rater notes whether the scan falls within three months of radiotherapy \citep{suter2022}. UCSF holds one pair of consecutive post-treatment scans per patient, with the start of radiotherapy \citep{fields2024}. Progression is documented in each cohort's own record (Table~\ref{tab:1}): as a dated clinical decision at MU, as an expert rating of response at each scan at LUMIERE and as a progression date supplied with the dataset at UCSF. Because the first scan of each pair has no earlier scan, we evaluated the second scan only."

→ "PRISM was developed on MU and tested on LUMIERE and UCSF, in each case on grade 4 glioma as the primary population,
with models fitted once on MU and applied unchanged, which we call locked. Table~\ref{tab:1} lists what each cohort
records; UCSF holds one pair of consecutive post-treatment scans per patient, and because the first scan has no earlier
scan we evaluated the second only. Progression is documented in each cohort's own record: as a dated clinical decision
at MU, as an expert rating of response at each scan at LUMIERE and as a progression date supplied with the dataset at
UCSF."
Destination: Table 1 rows "Treatment dates" and "Scans per patient" say exactly this (rater flag within three months;
radiotherapy start only). The three dataset citations remain in 2.1 P4 (masks). The reduced timeline's flag source is
still stated in 2.1 P2, which 3.2 points to.

**C8. 2.2 P2, last sentence (14 words).**
> "Predicting progression within 120 days of a scan is reported as a secondary task."

→ delete. Destination: 3.1 introduces the task in its own sentence ("Predicting progression within 120 days of a scan
was harder; the model reached 0.60 ... in the intended use") and the Limits keep it (C27). The always-in-main item
(intended-use 0.60 in Results and Discussion) is untouched.

### Methods 2.3

**C9. 2.3 P1, the split-variance reason stated twice (23 words).**
> "We chose this design because in cohorts of this size one split can move an AUC by more than a change of model. We saw this in our first evaluation, in which a radiomics model reached an AUC of 0.80 on one test split and averaged 0.72 when re-selected and re-tested over 500 splits of the same design (Supplementary Section~S8 and Figure~S2)."

→ "We chose repeated splits because in our first evaluation a radiomics model reached an AUC of 0.80 on one test split
and averaged 0.72 when re-selected and re-tested over 500 splits of the same design (Supplementary Section~S8 and
Figure~S2)."
Destination: Intro P2, third challenge, is the same sentence verbatim ("one test split can move the AUC by more than a
change of model"). The 0.80 → 0.72 contrast, which is the evidence, stays.

**C10. 2.3 P2, the plan deviation duplicated in the Table 2 note (26 words).**
> "For the external tests, each model was fitted once on MU and applied once, under plans committed before any external label was read. The locked models were fitted on all grade 4 detection scans of MU, from every phase of care. The UCSF plan named all MU detection scans; fitting on all gliomas gave the same AUC at LUMIERE, and at UCSF the all-glioma models were tested on all-glioma scans (\todo{Supplementary section: deviations from the plans})."

→ "For the external tests, the locked models, fitted on all grade 4 detection scans of MU from every phase of care,
were applied under plans committed before any external label was read; the one deviation from a plan is in the note
to Table~\ref{tab:2} (\todo{Supplementary section: deviations from the plans})."
Destination: Table 2 note already carries the deviation in full ("The locked models were fitted on grade 4 rows where
the UCSF-ALPTDG plan named all MU-Glioma-Post detection scans; the all-glioma fit gave the same AUC at LUMIERE, and
at UCSF-ALPTDG the all-glioma models were tested on all-glioma scans"). RESERVE already says "one clause in 2.3 and the
Table 2 note"; this makes it one clause. "Fitted once ... applied unchanged ... locked" is defined in 2.2 and used as the
short form here (round 2 ruling on repeated phrases).

**C11. 2.3 P3, the exploratory list (4 words; pairs with C17).**
> "had been seen; a stricter flag rule; the second evaluation"

→ "had been seen; the second evaluation"
Why: with C17 the stricter rule no longer appears in the Results, and the list is of analyses marked there.

### Results

**C13. 3.1, the all-glioma gain sentence (28 words).**
> "In one secondary evaluation set, all scans of all gliomas, the planned model did gain 0.04 (Table~\ref{tab:2}), which may reflect image inputs that encode the scan schedule (Section~\ref{sec:3.3})."

→ delete; append to the Table 2 note after "+0.036 (−0.014 to +0.085) in the all-glioma intended use": ", which may
reflect the schedule inputs of Section~\ref{sec:3.3}" (9 words in a note, outside the budget).
Destination: Table 2 note already has both CIs (+0.041; +0.036). Round 1 logged this result as an integrity item
(a result that contradicts the claim) and round 3 named it a trim candidate (reviewer 2 minor 7: move to the Table 2
note). The table is main text, so the integrity item stays in main text; only the prose duplicate goes. 3.1 then runs
"...0.60 (0.52--0.69) in the intended use (Supplementary Section~S23). A timeline pathway needs treatment dates..."; the
closing question still follows.

**C15. 3.2 P2, the UCSF combined-score explanation (24 words).**
> "The combined score at UCSF scored above the image pathway (Figure~\ref{fig:2}), partly through the interval between the two scans, which was shorter before progression."

→ delete.
Destination: the Figure 2 caption already says "the combined score there includes the interval between the two scans";
2.1 P5 says the interval is the combined score's "one schedule input"; RESERVE has the row ("Why is the UCSF combined
score higher than the image pathway? ... the inverted interval alone gives 0.72"). This is a reviewer question the
80/20 rule leaves open; the abstract makes no claim on the UCSF combined score.

**C17. 3.4 P2, the stricter rule pointer (25 words).**
> "A stricter rule chosen after these results, flagging a scan only when the pathways disagree and its set holds both outcomes, is described in the \todo{Supplementary section: system results}."

→ delete.
Destination: RESERVE row "Is there a flag that works at all three centres?" (update its "Where" from "One labelled
sentence in 3.4" to the supplement section). Round 3 named this a trim candidate. Nothing in the main text depends on
it. If round 4's 12A sentence in 3.4 mentions the "disagree and set holds both outcomes" variant, it reintroduces the
rule in its proper place; this sentence would then be a duplicate anyway.

**C18. 3.4 P3, the tier definition repeated (5 words).**
> "Across the three cohorts only four situations held at least 10 progression and 10 non-progression scans, one at MU and three at LUMIERE;"

→ "Across the three cohorts only four situations reached the tested tier, one at MU and three at LUMIERE;"
Destination: 2.1 defines "tested" as at least 10 and 10.

**C19. 3.5, the model-size sentence (18 words; pairs with C6).**
> "The smallest open-weight model that passed in every cohort had 27 billion parameters and ran on one GPU (\todo{Supplementary section: second report evaluation and model comparison})."

→ delete; the supplement pointer moves to the end of the preceding sentence ("...in 28 of 30 perturbed records
(Table~\ref{tab:2}; \todo{Supplementary section: second report evaluation and model comparison})"). Table 2 row L1
then reads "Qwen3.8-27B (supplement)" instead of "(Section~\ref{sec:3.5})".
Destination: Table 2 L1 names the model; 2.1 names it and, with C6, says it runs on one GPU. RESERVE row "Could a
smaller report model do?" holds the ladder. Round 3 reduced the comparison to one sentence; this makes it a table row,
which is what a descriptive result of a listed exploratory comparison needs (META 12: the report gets little space).

### Discussion

**C20. P1, third sentence (11 words).**
> "Because the pathways were kept apart, we could measure these differences at each centre, and each report states them through the confidence and the card."

→ "Keeping the pathways apart is what let us measure these differences at each centre."
Why: the second half restates P1's first sentence ("states how far each score has been tested in the scan's
situation"). The first half is the builder's lesson and stays. P2 then opens "Because its modules are separate", so
the two paragraphs no longer start on the same clause.

**C21. P2, the combined-score definition, third occurrence (8 words).**
> "and the combined score, one ridge model on both sets of inputs, is shown beside both without changing the image model."

→ "and the combined score is shown beside both without changing the image model."
Destination: 2.1 P5 and the Figure 1 caption both define it. (The caption's "one ridge model on both sets of inputs"
could also go; captions are outside the budget.)

**C22. P4, the three same-cohort studies (8 words).**
> "On MU, \citet{christodoulou2026} predicted a label assigned at the patient level with a radiomics model, a different question from detection at the scan. On LUMIERE, \todo{cite Tikhonov 2025, arXiv:2509.06511; full reference not yet verified} classified each scan into four response categories, and \citet{chen2026} predicted recurrence risk from preoperative and postoperative MRI across centres; both address other labels."

→ "On MU \citet{christodoulou2026} predicted a label assigned at the patient level, on LUMIERE \todo{cite Tikhonov 2025,
arXiv:2509.06511; full reference not yet verified} classified each scan into four response categories, and
\citet{chen2026} predicted recurrence risk from preoperative and postoperative MRI across centres; none of these is
detection at the scan."
Why: one sentence, one point (other labels), said once instead of twice ("a different question from detection at the
scan" and "both address other labels"). Also fixes a reading error: "both" made Chen sound like a LUMIERE study.
Neutral, no claim about any model we did not run.

**C23. Limits, the patient counts (10 words).**
> "PRISM was developed at one centre, with 126 grade 4 patients (80 in the intended-use detection set), and the two external tests are its only evidence of transfer."

→ "PRISM was developed at one centre (Table~\ref{tab:1}), and the two external tests are its only evidence of transfer."
Destination: Table 1 (Patients 126; 80 in the intended use). STYLE 5: never the same number twice.

**C25. Limits, the coverage and disagreement restatement (27 words).**
> "The coverage threshold was met on point estimates, and at UCSF the interval reached below it; the disagreement warning picked out less accurate scans only at MU."

→ delete.
Destination: 3.4 carries both results, and round 4 adds class-conditional coverage (12B) beside them. The second half
will be wrong after round 4: with MU-fixed medians (12A) disagreement does pick out less accurate scans at LUMIERE
(+0.222, +0.102 to +0.337), so "only at MU" cannot stand. Removing the sentence now avoids restating a result twice and
having to keep two copies in step. The Limits still state the three scope limits of the always-in-main list (one
centre, label as documented, no clinician read).

**C26. Limits, the checker scope, second statement (6 words).**
> "The report checker is lexical, and no clinician has yet read the reports."

→ "No clinician has yet read the reports."
Destination: 3.5 says "a lexical check ... the check cannot judge emphasis, order or what a clinician would infer".
Round 3 shortened this sentence so the scope "is not stated twice"; it still is.

**C27. Limits, the 120-day sentence (9 words).**
> "PRISM forecast progression within 120 days less well than it detected it at the scan, so we present it as a detection system and report the forecast as a secondary task."

→ "PRISM forecast progression within 120 days less well than it detected it at the scan, so the forecast is a
secondary task."
Why: the same statement in fewer words; the Discussion keeps the 120-day result as the always-in-main list asks.

**C28. Future work, the rarity stated twice and the card repeated (10 words).**
> "The next step is to pool the rare situations across cohorts and train on them. Early progression after radiotherapy and growing enhancement without progression are rare at any one centre. The Burdenko and UCSD-PTGBM datasets add radiotherapy detail and advanced sequences, and each new cohort adds cases to the card's thin situations, which is where models fine-tuned on these long-tail cases could be tested."

→ "The next step is to pool the rare situations, early progression after radiotherapy and growing enhancement without
it, across cohorts and train on them. The Burdenko and UCSD-PTGBM datasets add radiotherapy detail and advanced
sequences, and their cases in the card's thin situations are where models fine-tuned on these long-tail cases could be
tested."
Destination: Intro P2 (fourth challenge) says these situations hold few cases in any one cohort; Discussion P2 says a
new cohort adds rows to the card.

**C29. The Conclusion subsection (52 words).**
> "PRISM keeps image and treatment-timeline evidence apart, and its models held at two other centres without refitting. In our three cohorts the images and the timeline each contributed, in different proportions at each centre, and PRISM shows the clinician both scores at every scan, with how far each has been tested there."

→ delete the subsection.
Why: its first sentence is Discussion P1's first sentence, and its second is P1's second sentence in vaguer words
("in different proportions"). The journal has no word limit and the Interact template does not require a Conclusion
(JOURNAL_RULES.md). The Discussion then ends on P6's last sentence; see "Does the Discussion end well?" below for why
that is acceptable and for the fallback (keep a one-sentence Conclusion, saving 19 instead of 52).

---

## Tier B: the editor's call (60 words)

Each removes a small disclosure that a reviewer could ask for, and each has a RESERVE row or a table cell to answer
from. I would take C12, C14 and C24; C5, C16 and C30 touch earlier rulings and are listed so the editor decides.

**C5. 2.1 P6, the refit caveat (16 words).** "Because of the refit, the set's model ranks scans slightly differently
from the displayed combined score (\todo{Supplementary section: system results})." → delete, moving the supplement
pointer to after "the remaining 30\%". RESERVE row "Is the conformal set built on the displayed score?" (AUC 0.80 vs
0.82 at MU) answers it. Reviewer 2 m4 asked about it in round 3 and was answered from the RESERVE row, which argues
for keeping one clause; the clause is the price of not being asked.

**C12. 2.3 P3, the marking convention (7 words).** "In the Results each is marked ``(exploratory)'' once, where it
first appears in a paragraph, and the figure and table notes mark exploratory panels and rows." → "The Results mark
each ``(exploratory)'' where it first appears in a paragraph, as do the figure and table notes."

**C14. 3.2 P1, the LUMIERE pathway levels (4 words).** "images 0.65 and the reduced timeline 0.69 (exploratory; the gain
over the timeline alone had an interval that included zero)" → "the reduced timeline at 0.69 (exploratory; the gain over
it had an interval that included zero)". Keeps the strongest baseline in prose (always-in-main); 0.65 is a Figure 2
bar.

**C16. 3.3 P3, the deep-network sentence (14 words).** "Deep networks fine-tuned to score UCSF scans directly learned
from the images, above a permuted-label control (Table~\ref{tab:2}), and their scores tracked enhancing volume
(correlation about 0.8; \todo{...})." → "Deep networks fine-tuned on UCSF scans also tracked enhancing volume
(Table~\ref{tab:2}, Q4; \todo{Supplementary section: deep networks at MU and UCSF})." Round 1 ruling 6 asked for one
sentence on Q4; this is still one sentence. Table 2 Q4 holds the control result and its CI.

**C24. Limits, the UCSF count (6 words).** "Subgroups are small, and UCSF contributes 29 progression scans." →
"Subgroups are small." Table 1 shows 29 / 40. (If the editor wants one concrete count in the Limits, keep this one and
take C23 instead; both is the duplication.)

**C30. Intro P4, the three parts of the confidence (13 words).** "The confidence has three parts, a conformal
prediction set, a statement of whether the pathways agree and a reliability card; a local language model writes the
report, and a checker tests it against the scan's record." → "PRISM attaches a confidence to each score; a local
language model writes the report, and a checker tests it against the scan's record." The three parts are listed again
in 2.1 P6 and the Figure 1 caption. Against: the Introduction is where the reader first sees the capability, and
"three parts" is concrete (see buried capabilities, item 3). I lean to keeping it.

---

## Saving that falls out of round 4's own edits (11 words)

**R4. 2.1 P6, the agreement rule with MU-fixed medians (NUMBERS.md 12A).** When round 4 restates the rule, the
transductive caveat goes with it:
> "The two pathways agree when both scores lie on the same side of that pathway's median score over the cohort's evaluation scans; the rule uses scores only, never labels, but as evaluated it needs the scores of a whole cohort (\todo{round 4: ...})."

→ "The two pathways agree when both scores lie on the same side of that pathway's median score in the MU training set;
the rule uses scores only, never labels." Saves 11 against the current text, and removes the reason the rule was
"not usable prospectively" (RESERVE round-3 row), which should be updated.

## Knock-on edits outside the budget

- Table 2 note: append the schedule-inputs clause (C13); row L1 points to the supplement instead of 3.5 (C19).
- Figure 1 caption: "one ridge model on both sets of inputs" can go (defined in 2.1); optional.
- RESERVE.md: "Is there a flag that works at all three centres?" → Where: supplement only (C17); "The agreement rule
  uses each cohort's median" → resolved by 12A (R4); "The UCSF plan said all MU detection scans" → "the Table 2 note
  and one clause in 2.3" (C10).

## Arithmetic

| | Words |
|---|---|
| Main text now | 3,992 |
| Tier A (25 cuts) | −391 |
| After tier A (simulated by applying the cuts and recounting) | 3,601 |
| Round 4 additions (four to six sentences, estimate) | +120 to +150 |
| Expected after round 4 | about 3,720 to 3,750 |
| Tier B, if all taken | −60 |
| R4 (12A restatement) | −11 |

Margin under 3,900 after tier A and the additions: about 150 words, so the editor can reject the larger tier A items
(C29, C7, C13, C25, C10) one or two at a time and still meet the budget. Rejecting all five would not.

---

## Buried capabilities: does the paper still show what PRISM does?

The four capabilities, checked against where a reader meets each.

1. **Pathways transfer.** Shown clearly: abstract, Intro P5, 3.2 heading and first sentence, Figure 2, Discussion P1.
   Not buried. Round 4's ET-volume bar in Figure 2 will put the simplest reference beside each pathway, which
   strengthens rather than dilutes the claim at MU (ET alone 0.62 against the timeline's 0.82 and the images' 0.71).
   At LUMIERE the bar needs one honest clause: ET alone is 0.66, above the locked image pathway's 0.65 and below the
   combined score's 0.77, so the transfer claim there rests on the combined score, not the images alone. At UCSF 3.3
   already says ET alone is higher.

2. **Audit.** Shown: 3.3 heading, Figure 3, Intro P5 ("When we audited the scores"), Discussion P1 S2. One gap: the
   general lesson for someone who evaluates such models, that similar AUCs at two centres can rest on different
   evidence and that the audit is how you find out, is stated only as 3.2's closing question ("Because similar AUCs at
   different centres can come from different evidence, we audited...") and never in the Discussion. C20's rewrite
   keeps "Keeping the pathways apart is what let us measure these differences at each centre", which is the builder's
   half of it. Enough; no words needed.

3. **Confidence.** Partly buried, in two ways.
   - The 3.4 heading names only the conformal coverage (17 words, one of three parts). The reliability card, which is
     the part the clinician reads ("how many scans like this one the system has been tested on") and the part the
     Discussion leans on (P1 "which for most scans at MU and UCSF is little"; P3 "the card has few cases"), is the
     third paragraph of 3.4 under a heading that does not mention it. Round 3 M3 fixed "on point estimates" in the
     heading, so I do not propose rewording the heading here; but the editor should know that a reader skimming
     headings sees "conformal sets meet coverage" and never "the card says where the evidence is thin". A shorter
     heading that keeps the ruling: "The confidence keeps its coverage on point estimates and says where the evidence
     is thin" (15 words). Flag for the coordinator.
   - Round 4's class-conditional coverage (12B: LUMIERE progression 0.767, UCSF non-progression 0.650) goes into 3.4
     P1, which already has three caveats (UCSF interval; pathways alone; uneven across situations). After the addition,
     P1 would be one claim and four qualifications. Suggest the 12B sentence replaces "and it was uneven across
     situations within each cohort" rather than following it, since class is the sharper statement and the
     by-situation unevenness is what the card reports anyway (P3).

4. **Local, faithful reports.** Shown: 3.5 heading, Figure 5, 2.1 P7 ("runs offline"), Intro P3 ("written inside the
   hospital"), 2.1 P1 ("so the record never leaves it"). Two small burials:
   - The fifth challenge's first half, "the clinician needs to see what was measured", is answered by the
     segmentation figure in the report (2.1 P4, Figure 5 caption) but never in the Results prose: 3.5's closing
     sentence lists "the volumes, the two scores and the confidence". Suggest "the segmentation figure and its volumes,
     the two scores and the confidence" (+4 words). Cheap, and it is the only C5 evidence the Results would otherwise
     not show.
   - The Discussion's answer to the question (P1 S1) covers three of the four parts of Intro P3 (separate evidence;
     transfer; how far trusted) and omits the fourth ("explain each score in a short report written inside the
     hospital"). Suggest in P1 S1: "...and states, in a report written inside the hospital, how far each score has been
     tested in the scan's situation..." (+7 words). With C20 this paragraph is still shorter than now.

Net cost of the two suggested additions: 11 words, inside the margin.

Nothing else is buried. The modularity benefits (image pathway alone where no dates; timeline added without a new
model; card rows added without refitting) are all in Discussion P2 with first-sentence status.

---

## The Discussion as a whole

**Does it answer the question?** Yes, in P1's first sentence, in the order Intro P3 asks it, with the one omission
noted above (the report). P1 S2 gives the finding per centre and the builder's lesson ("the locked results therefore
measure transfer, and a model fitted at the centre can do better"). It is honest about the card ("for most scans at MU
and UCSF is little"). First-sentence test on P1 to P6: "PRISM gives the clinician separate evidence... / Because its
modules are separate, PRISM runs where data are incomplete / Consider a scan eight weeks after radiotherapy / Each of
PRISM's components has been described before / PRISM was developed at one centre / The next step is to pool the rare
situations". That reads as the argument.

**Does it help the builder?** P1 S2 (transfer vs refit), P2 (what runs on what data, nothing refitted when a cohort is
added), P6 (where the next cases come from). After round 4, 12D and 12F add the sharpest builder's warning in the
paper: a threshold fixed on MU calls 90% of UCSF scans positive, and the locked combined score's slope at UCSF is
3.29. The Discussion should carry one clause of that, in P1 S2 after "a model fitted at the centre can do better":
"and a threshold or calibration fixed at MU does not carry over". The AUC transfer claim is then bounded where a
builder would misuse it. About 12 words; the round 4 editor should budget them.

**Does it help the clinician?** P3 is the paper's best paragraph for the clinician: a concrete scan, both scores,
disagreement, a set holding both outcomes, a card with few cases, and what the clinician then does with information
PRISM does not use. It should become the figure panel OUTLINE asks for. No change.

**Does it end well?** Now it ends twice: P6's reader-study sentence, then a Conclusion that repeats P1. With C29 it
ends on "A reader study in which clinicians use PRISM's reports at the scan would show whether separate evidence and a
stated confidence change their decisions." STYLE 9 says end on the idea, not on future work; this sentence is future
work, but the idea it names (separate evidence and a stated confidence) is the paper's, and the sentence poses it as
the thing still to be shown, which is where META 16 ("set up for later") points. I find it an acceptable ending and
better than the current duplicate. If the editor wants a closing sentence of the idea itself, the fallback is a
one-sentence Conclusion in place of the two: "PRISM keeps image and treatment-timeline evidence apart, held at two
other centres without refitting, and shows the clinician both scores at every scan with how far each has been tested
there." (33 words; saves 19 rather than 52.) I would not keep the current two-sentence Conclusion.

**One more thing the Discussion should not do after round 4.** P5 (Limits) currently restates two Results (C25). If
round 4 adds class-conditional coverage and the MU-fixed agreement result to 3.4, the temptation will be to add their
caveats to the Limits as well. One place each. The Limits are the scope of the claim (one centre, label as documented,
small subgroups, exploratory analyses untested, no clinician read, forecast secondary); result caveats stay with their
results.

---

## Top six cuts, for the coordinator

| # | Cut | Words |
|---|---|---|
| C29 | Conclusion subsection (duplicates Discussion P1) | 52 |
| C7 | 2.2 cohort descriptions already in Table 1 | 31 |
| C13 | 3.1 all-glioma sentence (both CIs already in the Table 2 note) | 28 |
| C25 | Limits restating coverage and disagreement (and stale after 12A) | 27 |
| C10 | 2.3 plan deviation duplicated in the Table 2 note | 26 |
| C17 | 3.4 stricter-rule pointer (RESERVE) | 25 |
