# Council round 2: tone, voice and flow

Reviewer lens: paragraph flow and the author's voice. Checked against META_PATTERNS.md, STYLE.md sections 6 and 10,
LOCKED.md (the voice of abstract draft 1: direct, concrete numbers, semicolon-joined contrasts, one idea per
sentence) and round1_decisions.md (rulings 1–10; rejected items are not raised again). Manuscript: paper/main.tex at
commit dcfd00a. Reviewer only; nothing in paper/ was edited.

## The first-sentence test

Read in a row, the first sentences tell the whole story, in this order: surveillance decisions are hard → five
challenges come from the data → we asked for a system that separates the evidence, transfers and states trust →
PRISM → the timeline pathway reaches 0.82 and images 0.71 on MU → the combined model reaches 0.77 at LUMIERE → both
image models transfer to UCSF → the audit shows schedule at MU and enhancement at UCSF → the UCSF calls rest on
enhancement → adding inputs to the image model raised its AUC → deep networks learned above control → the conformal
sets meet coverage → disagreement marks less accurate scans on MU → the card states how much evidence lies behind a
scan → the reports pass the check → PRISM gives separate evidence and transfers → it runs where data are
incomplete → an illustration → components exist, not combined → limits → next step.

The chain holds. Four links are weak: the Introduction's claim paragraph opens on "PRISM is a modular system built
for this" (no claim); 3.3 interrupts its MU argument with the UCSF paragraph and then returns to MU for the ladder;
the deep networks paragraph opens on a weak positive and ends on a shortfall; the limits paragraph opens on a
signpost. Items 3, 4, 8 and 12 fix them.

What reads well and should stay: Introduction P1 and P3; 2.3 P1; the 3.1 closing transition; the 3.2 closing
transition; 3.4 P2; the Discussion illustration; the Discussion's novelty sentence; the future-work paragraph.
Claim strength is mostly at the evidence's level; the residual default voice is now less in sentence tics than in
repetition (one verb, one long noun phrase, one participle phrase used everywhere; item G1–G3) and in paragraphs
that hold two ideas.

Ranked list, most important first. Each item: location, original, problem, exact replacement.

---

## 1. Abstract, sentence 2 (garden path)

Original: "We built PRISM, a modular system that detects the scan at which progression is documented through
separate image and treatment-timeline pathways, attaches a confidence to each scan and writes a report with a local
language model."

Problem: on first reading "progression is documented through separate image and treatment-timeline pathways"; the
pathways attach to the wrong verb. "attaches a confidence to each scan" is the scan, not the score. The sentence is
the reader's whole picture of the system and should parse at once.

Replacement: "We built PRISM, a modular system that scores each post-treatment MRI through separate
treatment-timeline and image pathways, attaches a confidence to each score and explains it in a report from a local
language model."

(The task, "the scan at which progression was documented", moves into the next sentence; see item 2.)

## 2. Abstract, the MU sentence (capability first)

Original: "On MU-Glioma-Post the timeline pathway reached an AUC of 0.82, above the image pathway."

Problem: the first result the reader meets is framed as the images losing, and "above the image pathway" invites the
question "by how much?" without answering it (pattern 5, 7). The text's own 3.1 heading says what the abstract
should: both pathways detect the scan.

Replacement: "On MU-Glioma-Post both pathways detected the scan at which progression was documented, the timeline
pathway with an AUC of 0.82."

## 3. Introduction P4, opening and system description

Original: "PRISM is a modular system built for this. We developed it on MU-Glioma-Post (MU) and tested it on LUMIERE
and UCSF-ALPTDG (UCSF) with models fitted once and external tests planned in advance. It scores each scan through two
pathways, ..."

Problem: the paragraph that states the paper's claim opens on a sentence with no content ("built for this"); the
claim arrives three sentences later. The paragraph also holds two ideas (what PRISM is; what it achieved) in eight
sentences.

Replacement (split into two paragraphs):
"We present PRISM, a modular system that scores each post-treatment scan through two pathways, one from clinical data
and the treatment timeline and one from measurements of the segmented tumour, and shows a combined score beside
them. It attaches a confidence made of a conformal prediction set, a statement of whether the pathways agree and a
reliability card, and writes a report with a local language model whose every sentence is checked against the
scan's record.

We developed PRISM on MU-Glioma-Post (MU) and tested it on LUMIERE and UCSF-ALPTDG (UCSF) with models fitted once
and external tests planned in advance. On MU both pathways detected the scan at which progression was documented;
..." (rest as now).

## 4. Results 3.3, paragraph order

Original order: (1) MU audit, (2) UCSF enhancement, (3) the MU image-model ladder, (4) deep networks (UCSF, then MU).

Problem: the section is one argument per cohort, but it goes MU → UCSF → MU → UCSF/MU. The ladder explains the MU
paragraph's finding (why images across phases look stronger than within them) and is what 2.1 points to for the
schedule inputs; separated from it by the UCSF paragraph, the reader has lost the thread. The deep networks paragraph
then follows naturally from UCSF ("their scores tracked enhancing volume").

Replacement: move the ladder paragraph ("Adding inputs to the image model raised its AUC on MU, ...") to directly
after the first MU paragraph. Order: MU audit → MU ladder → UCSF enhancement → deep networks. No sentence changes
needed beyond item 13.

## 5. Abstract, the transfer sentence ("the models")

Original: "Fitted once and applied unchanged, the models reached 0.77 on LUMIERE; on UCSF-ALPTDG, single-scan
measurements reached 0.80 and the image pathway with change from the previous scan 0.73, against 0.86 when trained
there."

Problem: "the models" is plural for one number (it is the combined model, 3.2). The second clause has three numbers
and a long unpunctuated noun phrase ("the image pathway with change from the previous scan 0.73"), which reads as one
name. A pair of commas makes the elision clear without adding a number.

Replacement: "Fitted once and applied unchanged, the combined model reached 0.77 on LUMIERE; on UCSF-ALPTDG,
single-scan measurements reached 0.80 and the image pathway, with change from the previous scan, 0.73, against 0.86
when trained there."

## 6. Results 3.2 and 3.3, the UCSF combined score is referenced before it is reported

Original (3.3, last sentence of the UCSF paragraph): "The combined score's higher AUC at UCSF (Figure~\ref{fig:2})
rests partly on the interval between the two scans, which was shorter before progression."

Problem: 3.2 never states the combined score at UCSF in the text, so "higher" refers to a number the reader has not
been given; it is also a second idea at the end of a paragraph about enhancement. The natural home is 3.2, beside the
reduced timeline, where the reader asks "what about the combined score?".

Replacement: delete the sentence from 3.3 and add to 3.2 after "...because UCSF records only the start of
radiotherapy.": "The combined score at UCSF scored above the image pathway (Figure~\ref{fig:2}), partly through the
interval between the two scans, which was shorter before progression." (If the author wants the number, it is in
NUMBERS.md section 4; one number is enough.)

## 7. Introduction P2, external tests and the third challenge

Original: "External tests address the second and third challenges."

Problem: 2.1 says the third challenge, small cohorts, "is handled by how PRISM is evaluated (Section 2.3)", and 2.3
answers it with repeated cross-validation. The Introduction assigns it to external tests, so the two sections
disagree, and the sentence opens a second idea (the literature) at the end of the challenges paragraph.

Replacement: "Repeated cross-validation addresses the third challenge and external tests the second; in a recent
systematic review of automated response assessment, 3 of 20 studies used external test data \citep{shi2025}, and
deep learning models in radiology usually lose some accuracy on external data \citep{yu2022}."

## 8. Results 3.3, deep networks paragraph

Original: "Deep networks fine-tuned to score UCSF scans directly learned above a permuted-label control
(Table~\ref{tab:2}), but their scores tracked enhancing volume (correlation about 0.8) and their AUC stayed below that
of enhancing volume alone; on MU they did not meet the planned gain over the timeline."

Problem: "X, but Y and Z; on MU they did not" builds to a verdict, and frames the networks as failed classifiers
(pattern 9; author: "So deep networks are useless for segmentation and localization as well?"). The finding that
matters to the argument is that the networks found the same evidence as the measurements, which supports the
modular design.

Replacement: "Deep networks fine-tuned to score UCSF scans directly learned from the images, above a permuted-label
control (Table~\ref{tab:2}), and their scores tracked enhancing volume (correlation about 0.8), so they found the
evidence the measurements already hold; their AUC stayed below that of enhancing volume alone, and on MU they did not
meet the planned gain over the timeline."

## 9. Abstract, ending

Original: "Conformal sets for the combined score met their pre-specified coverage at all three centres, and after one
revision every report passed a deterministic check against its record."

Problem: none in voice; this is fine and should stay if word count allows nothing else. Recorded here because the
locked abstract ended on what PRISM does for the clinician ("shows both kinds of evidence side by side for every
scan"), which the author liked and which the proposal lost. If the author wants that ending back, the only room is
by dropping "for the combined score" (the coverage claim is the combined score's in 3.4) and replacing the closer;
see the alternative closer under the abstract proposal below.

Replacement: keep as is (not a voice fault); optionally drop "for the combined score" (−4 words) to buy room.

## 10. Methods 2.1, the image-pathway paragraph holds the combined score

Original (end of the image-pathway paragraph): "The combined score is one ridge model fitted on both sets of inputs.
At LUMIERE and UCSF its inputs are the reduced timeline with harmonised volumes, their change and the interval since
the previous scan, so there it holds one schedule input, that interval."

Problem: the combined score is a third component, defined at the tail of a paragraph about the image pathway's
inputs and exploratory status. "so there it holds one schedule input, that interval" is an afterthought clause.

Replacement: make it its own two-sentence paragraph after the image pathway: "The combined score is one ridge model
fitted on both sets of inputs and is shown beside the two pathways. At LUMIERE and UCSF its inputs are the reduced
timeline, the harmonised volumes and their change, and the interval since the previous scan, its one schedule
input."

## 11. Results 3.3, the within-phase sentence (repetition)

Original: "Within a phase, images alone reached 0.68 (0.58--0.77) and the timeline 0.64 (0.51--0.78), so within a phase
the images gave about as much evidence as the timeline."

Problem: "within a phase" three times in two sentences (the previous sentence ends on it too). The repetition reads
as drafting, and the closing clause restates the numbers.

Replacement: "Within a phase, images alone reached 0.68 (0.58--0.77) and the timeline 0.64 (0.51--0.78), about the
same."

## 12. Discussion, limits paragraph opener

Original: "This study has limits. PRISM was developed at one centre, ..."

Problem: a signpost sentence that announces instead of states (STYLE.md 6, "dramatic short sentences"). The second
sentence is the claim.

Replacement: delete "This study has limits." The paragraph opens "PRISM was developed at one centre, with 126 grade 4
patients, and the two external tests are its only evidence of transfer."

## 13. Results 3.3, ladder: "added nothing"

Original: "within a phase these three inputs added nothing ($-$0.01, $-$0.06 to $+$0.04), because they encode the
scan schedule."

Problem: "added nothing" is the verdict form round 1 removed from 3.1 (pattern 7). The interval is the finding.

Replacement: "within a phase these three inputs did not raise the AUC ($-$0.01, $-$0.06 to $+$0.04), because they
encode the scan schedule."

## 14. Conclusion

Original: "PRISM shows that a surveillance system can keep its kinds of evidence apart, transfer them to other centres
without refitting and state how far each has been tested there. In our three cohorts the images and the treatment
timeline each contributed, in different proportions at each centre, and PRISM shows the clinician both scores and the
evidence behind them at every scan."

Problem: "PRISM shows" twice; "its kinds of evidence" is vague and evidence does not transfer, models do. The first
sentence is a triplet that echoes Discussion P1 almost word for word.

Replacement: "A surveillance system can keep image and treatment-timeline evidence apart, transfer its models to
other centres without refitting and state how far each score has been tested there. In our three cohorts the images
and the timeline each contributed, in different proportions at each centre, and PRISM puts both scores and the
evidence behind them in front of the clinician at every scan."

## 15. Results 3.2, LUMIERE "about as high as in cross-validation on MU"

Original: "the combined model reached 0.77 (0.68--0.86) on LUMIERE (Figure~\ref{fig:2}), about as high as in
cross-validation on MU, and met its planned transfer rule"

Problem: the reader has just read that the combined score reached 0.82 on MU (3.1), so "about as high" reads as 0.77
≈ 0.82, a generous claim. Round 1 (#10) meant the same reduced model's MU cross-validation; say so.

Replacement: "the combined model reached 0.77 (0.68--0.86) on LUMIERE (Figure~\ref{fig:2}), close to the same
model's cross-validated AUC on MU, and met its planned transfer rule"

## 16. Methods 2.1, first paragraph (abstractions as subjects)

Original: "The confidence addresses the rare situations, and the report presents all of it without the record leaving
the hospital."

Problem: abstractions doing things ("the confidence addresses", "presents all of it"). Concrete subject reads
better.

Replacement: "The confidence tells the clinician how much measured evidence lies behind a score in rare situations,
and the report is written inside the hospital, so the record never leaves it."

## 17. Methods 2.2, task paragraph closer (history)

Original: "Predicting progression within 120 days of a scan, the task with which this work began, is reported as a
secondary task."

Problem: "the task with which this work began" is project history (pattern 14). The Limits paragraph already gives
the reason it is secondary.

Replacement: "Predicting progression within 120 days of a scan is reported as a secondary task."

## 18. Methods 2.2, cohort paragraph ending

Original: "... we evaluated the second scan only. UCSF was obtained under a data use agreement. The primary population
in every cohort is grade 4 glioma."

Problem: two short tacked-on sentences after the paragraph's point; the population belongs at the start, where the
reader needs it, and access is in Table 1 and the Ethics statement.

Replacement: first sentence becomes "PRISM was developed on MU and tested on LUMIERE and UCSF, in each case on grade 4
glioma as the primary population, with models fitted once on MU and applied unchanged, which we call locked
(Table~\ref{tab:1})." Delete the last two sentences.

## 19. Methods 2.3, the locked-fit sentence

Original: "The locked models were fitted on all grade 4 detection scans of MU, progression and non-progression scans
from every phase of care; the UCSF plan named all MU detection scans, and fitting on all gliomas gave the same
results."

Problem: the deviation is disclosed (round 1 integrity 12) but in a sentence the reader has to parse twice; the
appositive "progression and non-progression scans from every phase of care" restates "all".

Replacement: "The locked models were fitted on all grade 4 detection scans of MU, from every phase of care. The UCSF
plan named all MU detection scans; fitting on all gliomas gave the same results."

## 20. Results 3.4, card paragraph opener

Original: "The reliability card states, for each scan, how much measured evidence lies behind its situation, and for
most scans in our cohorts this is little (exploratory)."

Problem: "this is little" is awkward and ends the claim on a deflation; the parenthesis splits the sentence's end.
State the capability and the fact side by side.

Replacement: "The reliability card states, for each scan, how much measured evidence lies behind its situation
(exploratory); in our cohorts most scans fall in situations with few cases."

## 21. Results 3.2, UCSF paragraph closer

Original: "These results show that PRISM's measurements transfer to a new centre, and that a model trained at the
centre can do better."

Problem: restates the paragraph's opening ("both planned image models transferred") and Q3; a summary line before
the transition. The transition sentence after it does the work.

Replacement: delete; the paragraph ends "...because UCSF records only the start of radiotherapy." (or with item 6's
sentence), then "Because similar AUCs at different centres can rest on different evidence, we audited what each score
used." If the author wants the summary kept, it belongs in the Discussion, where it already is (P1).

## 22. Results 3.5, order of the last two sentences

Original: "The clinician therefore reads the segmentation, both pathway scores and the confidence as they stand in the
record. Of the seven open-weight models we compared, the smallest that passed in every cohort had 27 billion
parameters and ran on one GPU (...)."

Problem: the paragraph's "so what" sits second to last and is followed by a detail; the section ends on hardware.

Replacement: swap them, so the paragraph ends "...The clinician therefore reads the segmentation, both pathway scores
and the confidence as they stand in the record."

## 23. Introduction P2, opening

Original: "Models for this task meet five challenges that come from the data rather than from any one method."

Problem: a mild "X rather than Y" contrast; the second half answers a question nobody asked and slightly implies
someone thought otherwise.

Replacement: "Models for this task meet five challenges that come from surveillance data themselves."

## 24. Discussion P1, last sentence

Original: "Because the pathways were kept apart, these differences could be measured at each centre, and the
confidence and the card bring them into each report."

Problem: abstractions as subjects ("the confidence and the card bring them").

Replacement: "Because the pathways were kept apart, we could measure these differences at each centre, and each
report states them through the confidence and the card."

## 25. Results 3.3, the UCSF interpretation clause

Original: "At UCSF the AUCs therefore largely measure agreement with a progression call made from enhancement at the
same scan, which is what PRISM's image pathway measures."

Problem: "measure ... measures" in one sentence, and "which is what PRISM's image pathway measures" can be read as
"the image pathway measures agreement with a call", which is circular. Ruling 2's meaning kept; only the referent
fixed.

Replacement: "At UCSF the AUCs therefore largely measure agreement with a progression call made from enhancement at
the same scan, and enhancement is what PRISM's image pathway quantifies."

## 26. Discussion P4, the 0.80 radiomics sentence

Original: "On MU, a radiomics model reached an AUC of 0.80 with a label assigned at the patient level and one held-out
set \citep{christodoulou2026}, so its result and ours answer different questions."

Problem: the reader met "a radiomics model reached an AUC of 0.80 on one test split" in 2.3 (our first evaluation);
here the same model type and number appear for another group, and the reader will conflate them. "and one held-out
set" next to our 500-split finding reads as a criticism (pattern 6).

Replacement: "On MU, \citet{christodoulou2026} predicted a label assigned at the patient level with a radiomics model,
a different question from detection at the scan." (The 0.80 and the split design stay in RESERVE.md, where the
Christodoulou replication already is.)

## 27. Introduction P4, the reports clause

Original: "and after one revision of the prompt, following a failure at one cohort, the reports were faithful to
their records."

Problem: two stacked participle phrases before the claim; the Introduction is the one place where "after one
revision" suffices (ruling 5), and the failure is told in 3.5.

Replacement: "and after one revision of the prompt every report passed a check against its record."

## 28. Results 3.1, the 120-day sentence

Original: "Predicting progression within 120 days was harder; PRISM's model reached 0.60 (0.52--0.69) in the intended
use (Supplementary Section~S23)."

Problem: a second task dropped into the middle of the detection paragraph, between the images pointer and the
transition, so the transition ("A timeline pathway needs treatment dates...") no longer follows from the sentence
before it.

Replacement: delete it from 3.1 and attach the number to item 17's sentence in 2.2: "Predicting progression within
120 days of a scan is reported as a secondary task; PRISM's model reached 0.60 (0.52--0.69) in the intended use
(Supplementary Section~S23)." 3.1 then runs result → images pointer → transition. (If a Results number must stay in
Results, put the same sentence as the last sentence of 3.1, after the transition is rephrased; the point is that it
not sit between the images pointer and the transition.)

## Global observations

**G1. "rest on" is the new "carry".** Ten uses: abstract ("rested mainly"), Introduction ("rested mainly"), 3.2
("can rest on different evidence"), 3.3 heading ("rests on"), 3.3 ("rest mainly", "rest largely", "rests partly"),
Fig 3 title. It is the right verb for the audit heading and the abstract; elsewhere vary it: "depend on", "came
mainly from", "followed". Suggested: 3.2 transition "Because similar AUCs at different centres can come from
different evidence, we audited what each score used."; 3.3 UCSF opener "At UCSF the progression calls follow
enhancement closely."

**G2. "the scan at which progression was documented".** Seven words, used in the abstract, Introduction, 2.2, 3.1,
Table 1 and two captions. After 2.2 defines the task, "the progression scan" (already the 3.1 heading) reads better
in prose; keep the full phrase in the abstract, 2.2 and captions.

**G3. "fitted once on MU and applied unchanged".** Eight uses. 2.2 defines "locked" for this; after 2.2, use
"locked" in prose (3.2 opening: "The locked combined model reached 0.77 ..."), keeping the long form in the
abstract, Introduction and Figure 2.

**G4. Paragraphs with two ideas.** The pattern behind items 3, 6, 7, 10, 18, 28: a paragraph makes its point and
then adds an unrelated fact in its last one or two sentences. A check for the next pass: read each paragraph's last
sentence and ask whether it follows from the one before.

**G5. Claim strength.** Now moderate throughout; nothing oversold. The one place it is timid where the evidence is
strong is the Introduction's "On MU both pathways detected the scan" without a number while LUMIERE gets one; with
item 3's split, the second paragraph can give "the timeline pathway with an AUC of 0.82" to match the abstract.

---

## Abstract proposal (150 words, `wc -w`; same facts as the current proposal)

Most glioma surveillance datasets lack treatment dates, centres document progression differently, cohorts are small
and the hardest scans are few. We built PRISM, a modular system that scores each post-treatment MRI through separate
treatment-timeline and image pathways, attaches a confidence to each score and explains it in a report from a local
language model. On MU-Glioma-Post both pathways detected the scan documenting progression, the timeline pathway with
an AUC of 0.82. Fitted once and applied unchanged, the combined model reached 0.77 on LUMIERE; on UCSF-ALPTDG,
single-scan measurements reached 0.80 and the image pathway, with change from the previous scan, 0.73, against 0.86
when trained there. An audit showed the scores rested mainly on the patient's position in treatment at
MU-Glioma-Post and on enhancing tumour volume at UCSF-ALPTDG. Conformal sets met their pre-specified coverage at all
three centres, and after one revision every report passed a deterministic check against its record.

What changed and why: sentence 2 parses at once and names the score as what carries the confidence (item 1);
sentence 3 opens on both pathways working (item 2); "the models" becomes "the combined model" and the UCSF clause is
punctuated (item 5); "that" and "for the combined score" dropped for length (the coverage claim is the combined
score's in 3.4, as in the current text's own Section 3.4 heading). Same numbers: 0.82, 0.77, 0.80, 0.73, 0.86; the
image pathway's 0.71 stays out (round 1 #26). "the scan documenting progression" saves three words over "the scan at
which progression was documented"; if the author prefers the house phrase, drop "post-treatment" and "separate" to
stay within 150.

Alternative closer, if the author wants the locked abstract's ending back (replaces the last sentence). It brings the
proposal to 161 words, so it fits only if something else goes, for example the single-scan clause at UCSF ("single-scan
measurements reached 0.80 and"), which ruling 1 asked to keep; this is the author's call: "Conformal sets met their pre-specified coverage at all three centres, every report passed
a check against its record after one revision, and PRISM shows both kinds of evidence side by side at every scan."
