# Council round 1: tone and voice

Reviewer lens: tone and voice. Checked against META_PATTERNS.md (patterns 1--17, the correction table and the
15-item checklist), STYLE.md sections 6 and 10, and LOCKED.md (abstract draft 1's voice: direct, concrete numbers,
semicolon-joined contrasts, one idea per sentence). Manuscript: paper/main.tex at commit da7d2e7.

What was not found: no em dashes, no hyphen chains, no intensifiers (notably, importantly, interestingly,
crucially, remarkably, worth noting), no "published", no RANO, no v1/v2 labels, no B1/C2 codes in prose. The
skeleton's first sentences hold as claims. The remaining default-voice markers are colon reveals (about ten),
quotable closers, verdict phrases, number dumps, and one verb used as a tic.

Ranked list, most important first. Each item: location, original sentence, problem (checklist item in brackets),
exact replacement.

---

## 1. Results 3.1, the images verdict

Original: "The combined score also reached 0.82, so on top of the timeline the images added nothing measurable at
MU-Glioma-Post. The planned test agreed: the planned imaging model did not add the pre-specified 0.03 to the
timeline (Table~\ref{tab:2})."

Problem: "added nothing measurable" is the verdict the author rejected ("just because we pick something and just
blindly apply does not mean there is no signal"; STYLE.md section 6 before/after table). Colon reveal; "planned"
twice in one sentence. [7, 2]

Replacement: "The combined score also reached 0.82; on MU-Glioma-Post the images did not raise the timeline's AUC,
and the planned imaging model fell short of the pre-specified gain of 0.03 (Table~\ref{tab:2}). What the images
contribute on their own is examined within phases of care in Section~\ref{sec:3.3}."

## 2. Abstract, first sentence

Original: "Models of post-treatment glioma MRI face known challenges: most datasets lack treatment dates, centres
document progression differently, cohorts are small and the hardest situations have few cases."

Problem: Colon reveal introducing a four-item list; "models face challenges" and "situations have few cases" are
abstractions as subjects. Locked draft 1 opened on one concrete fact in one plain sentence. [1, 2]

Replacement: "Most surveillance datasets of post-treatment glioma MRI record no treatment dates, centres document
progression in different ways, cohorts are small, and the scans on which the decision is hardest are few at any one
centre."

## 3. Abstract, the audit sentence

Original: "An audit showed what each score rested on: the treatment timeline at MU, enhancing tumour volume at UCSF."

Problem: Colon reveal with a two-beat quotable ending; "MU" and "UCSF" are short names that the abstract has not
introduced (the sentence before uses the full names). [2, 10]

Replacement: "An audit showed that the scores rested on the treatment timeline at MU-Glioma-Post and on enhancing
tumour volume at UCSF-ALPTDG."

## 4. Results 3.3, the schedule sentence

Original: "At MU-Glioma-Post the scan schedule separates the classes before any image is read: 56 of the 62
progression scans came more than 12 weeks after radiotherapy, while 51 of the 84 non-progression scans came in the
12 weeks after it."

Problem: "before any image is read" is written for effect; colon reveal; four counts that Table 1 already holds.
[2, 8, 9]

Replacement: "At MU-Glioma-Post the scan schedule alone separates most of the two classes; most progression scans
came more than 12 weeks after radiotherapy and most non-progression scans came within those 12 weeks
(Table~\ref{tab:1})."

## 5. Results 3.4, the reliability card paragraph opener

Original: "For most scans the evidence behind any score is thin, and the reliability card says so (exploratory)."

Problem: The paragraph opens on a shortfall ("evidence ... is thin") with an abstraction as subject; pattern 5 says
open on what the module does. [1, 4, 5]

Replacement: "The reliability card states, for each scan, how much measured evidence lies behind its situation, and
for most scans in our cohorts this is little (exploratory)."

## 6. Results 3.3, the UCSF interpretation

Original: "The UCSF AUCs therefore measure agreement with a call made from enhancement at the same scan."

Problem: A flat verdict on our own strongest external result, stated at more than the evidence's strength
(enhancing volume gives 0.88, the model 0.80; the two are related, not identical). It reads as debunking rather
than audit. [7, 5]

Replacement: "At UCSF-ALPTDG the AUCs therefore largely measure agreement with a progression call made from
enhancement at the same scan, which is what PRISM's image pathway was built to measure and what the card records for
that cohort."

## 7. Results 3.2, the transport reading

Original: "We read these results as transport of PRISM's measurements to a new centre; they do not show that a
model fitted elsewhere does better than one fitted at UCSF-ALPTDG."

Problem: "X; not Y" contrast; "we read these results as" hedges a result that met its rule. A line break splits
"these / results" in the source. [2, 3, 7]

Replacement: "These results show that PRISM's measurements transfer to a new centre, and that a model fitted at
UCSF-ALPTDG does at least as well as the locked one (Q3, Table~\ref{tab:2})."

## 8. Conclusion, both sentences

Original: "PRISM shows that a surveillance system can keep its kinds of evidence apart, carry them to other centres
and say where they have and have not been shown to work. In our three cohorts the images and the treatment timeline
each carried evidence, in different amounts at different centres, and a clinician using PRISM can see which is which
at every scan."

Problem: "have and have not been shown to work" and "which is which" are closers written to be quoted; "carry" in
two senses in consecutive sentences. [2, 1]

Replacement: "PRISM shows that a surveillance system can keep its kinds of evidence apart, transfer them to other
centres without refitting and state how far each has been tested there. In our three cohorts the images and the
treatment timeline each contributed, in different proportions at each centre, and PRISM shows the clinician both
scores and the evidence behind them at every scan."

## 9. Discussion, first paragraph

Original: "PRISM gives the clinician separate image and treatment-timeline evidence at each scan, carries to two
external centres without refitting, and states how far its scores can be trusted there. At the development centre
the timeline carried most of the evidence, largely because of when patients were scanned, and within a phase of care
the images carried about as much. At UCSF-ALPTDG, where few treatment dates are recorded, the image measurements did
the work, and their scores matched the enhancement-based call made at the same scan. Because the pathways were kept
apart, these differences could be measured at each centre, and the confidence and the card carry them into each
report."

Problem: "carry/carried/carries" four times in four sentences, in two senses; "did the work" is colloquial. [1, 3]

Replacement: "PRISM gives the clinician separate image and treatment-timeline evidence at each scan, transfers to
two external centres without refitting, and states how far its scores can be trusted there. At the development
centre the timeline provided most of the evidence, largely because of when patients were scanned, and within a phase
of care the images provided about as much. At UCSF-ALPTDG, where few treatment dates are recorded, the image
measurements provided the score, and it matched the enhancement-based call made at the same scan. Because the
pathways were kept apart, these differences could be measured at each centre, and the confidence and the card bring
them into each report."

## 10. Results 3.2, the LUMIERE model's internal score

Original: "The same LUMIERE model scored 0.80 in cross-validation on MU-Glioma-Post, so it carried to LUMIERE with
little loss."

Problem: "The same LUMIERE model" is ambiguous (it is the MU-fitted model applied at LUMIERE); 0.80 here collides
with 0.80 on UCSF-ALPTDG in the sentence before, so a reader pairs the wrong numbers. [9, 10]

Replacement: "In cross-validation on MU-Glioma-Post the model applied at LUMIERE had scored 0.80, so it lost little
at LUMIERE."

## 11. Results 3.4, the disagreement paragraph

Original: "Disagreement marked 40\% of MU scans. The combined score's AUC was 0.90 where the pathways agreed and
0.59 where they disagreed (difference 0.31, 0.18--0.43), and setting the disagreeing scans aside gained 0.08
(0.05--0.12) over matched removal (Figure~\ref{fig:4}B)."

Problem: A staccato one-liner followed by five numbers and two intervals in one sentence; the matched-removal gain
is in Table 2. [2, 8]

Replacement: "The pathways disagreed on 40\% of MU-Glioma-Post scans; the combined score's AUC was 0.90 where they
agreed and 0.59 where they disagreed (difference 0.31, 0.18--0.43), and setting the disagreeing scans aside gained
more than removing the same number matched for phase of care (Table~\ref{tab:2}; Figure~\ref{fig:4}B)."

## 12. Results 3.4, the coverage sentence

Original: "At the 80\% level, the conformal sets of the combined score covered 0.82 of MU scans, 0.87 of LUMIERE
scans and 0.78 of UCSF scans, against a threshold of 0.78 fixed in advance (Figure~\ref{fig:4}A)."

Problem: Four numbers in one claim; short cohort names; 0.82 was the timeline AUC two sections earlier and now means
coverage. [8, 9, 10]

Replacement: "At the 80\% level, the conformal sets of the combined score covered between 0.78 and 0.87 of scans in
the three cohorts, against a threshold of 0.78 fixed in advance (Figure~\ref{fig:4}A)."

## 13. Results 3.4, the card counts

Original: "Of the 249 MU scans with reports, 35 fell in a situation tested on at least 10 progression and 10
non-progression scans. Across the three cohorts only four situations met that bar, one at MU-Glioma-Post and three at
LUMIERE, and every UCSF situation had few cases (Figure~\ref{fig:4}C)."

Problem: Nine counts in two sentences; the 249/35 pair restates in scans what the next sentence says in situations.
[8, 11]

Replacement: "Across the three cohorts only four situations held at least 10 progression and 10 non-progression
scans, one at MU-Glioma-Post and three at LUMIERE; every situation at UCSF-ALPTDG had few cases
(Figure~\ref{fig:4}C)."

## 14. Results 3.4, the tier and error sentence

Original: "The tier states how much evidence lies behind a situation's AUC. It tracked error at LUMIERE and ran the
other way at MU-Glioma-Post, where the scans with few cases were mostly non-progression scans early after
radiotherapy, which are easy to score."

Problem: "It tracked error" and "ran the other way" are an abstraction acting and a colloquialism; the first sentence
repeats the paragraph opener. [1, 11]

Replacement: "At LUMIERE scans in tested situations had lower error than scans with few cases; at MU-Glioma-Post the
order was reversed, because the few-case scans there were mostly non-progression scans early after radiotherapy,
which the models score easily (Table~\ref{tab:2})."

## 15. Results 3.4, the paragraph closer

Original: "The report is where the clinician meets these statements."

Problem: A quotable closer with "the report" as the actor. [2, 1]

Replacement: "The clinician reads these statements in the report, which we evaluated next."

## 16. Results 3.3, the image-model ladder

Original: "Measurements of the current scan alone reached 0.66, and adding change from earlier scans gave the image
pathway of Section~\ref{sec:3.1}. Adding the interval since the previous scan, a flag for whether there was one and
the smallest earlier volume counted only from the end of radiotherapy gave 0.81, close to the timeline itself."

Problem: The ladder told in numbers (0.66, implied 0.71, 0.81) is what the author objected to in the abstract; the
sequence is in Figure 3C. "gave the image pathway" is unclear. [8, 13]

Replacement: "Measurements of the current scan alone scored lowest, adding change from earlier scans gave the image
pathway of Section~\ref{sec:3.1}, and adding the interval since the previous scan, a flag for whether there was one
and the smallest earlier volume counted from the end of radiotherapy raised the AUC to 0.81, close to the timeline
itself."

## 17. Results 3.3, deep networks on MU-Glioma-Post

Original: "...and their AUC stayed below that of enhancing volume alone; on MU-Glioma-Post they did not separate the
scans."

Problem: "did not separate the scans" is a verdict on the networks (pattern 9: deep networks are segmenters, not
failed classifiers); Table 2 states the measured fact. [7]

Replacement: "...and their AUC stayed below that of enhancing volume alone; on MU-Glioma-Post they did not meet the
planned gain over the timeline (Table~\ref{tab:2})."

## 18. Introduction, external tests sentence

Original: "External tests address the second and third challenges, and they are uncommon: 3 of 20 studies of
automated response assessment in a recent systematic review used external test data \citep{shi2025}, and deep
learning models in radiology usually lose some accuracy on external data \citep{yu2022}."

Problem: "they are uncommon" is a judgement on the field before the fact; colon reveal. The count says it
neutrally. [6, 2]

Replacement: "External tests address the second and third challenges. In a recent systematic review of automated
response assessment, 3 of 20 studies used external test data \citep{shi2025}, and deep learning models in radiology
usually lose some accuracy on external data \citep{yu2022}."

## 19. Results 3.2, training at UCSF

Original: "For the image pathway with change features, training at UCSF-ALPTDG did better: the locked model scored
0.73 and the UCSF-trained model 0.86 (difference 0.14, 0.03--0.26)."

Problem: Colon reveal; the claim is carried by three numbers. [2, 8]

Replacement: "The image pathway with change features transferred less well; the locked model scored 0.73 where a
model trained at UCSF-ALPTDG scored 0.86 (difference 0.14, 0.03--0.26)."

## 20. Results 3.2, complementary evidence

Original: "At LUMIERE the two kinds of evidence were complementary: images alone scored 0.65 and the reduced
timeline alone 0.69, both below the combined score."

Problem: Colon reveal; "the two kinds of evidence were complementary" is an abstraction as subject. [2, 1]

Replacement: "At LUMIERE each pathway added to the other; images alone scored 0.65 and the reduced timeline alone
0.69, both below the combined score."

## 21. Results 3.2, the single-scan model

Original: "At UCSF-ALPTDG, the locked single-scan image model was about as high as when trained there (0.83)."

Problem: A model is not "high"; its AUC is. [1]

Replacement: "At UCSF-ALPTDG the locked single-scan image model scored about as high as a model trained there
(0.83)."

## 22. Results 3.1, the cohort counts

Original: "...and the image pathway with 0.71 (0.63--0.78), over 146 scans of 80 patients (62 progression, 84
non-progression)."

Problem: Four counts after two AUCs with intervals; Table 1 holds them. [8]

Replacement: "...and the image pathway with 0.71 (0.63--0.78), over the 146 scans of the intended use
(Table~\ref{tab:1})."

## 23. Results 3.3, the within-phase gain

Original: "When we compared models within each phase of care, the timeline's gain over clinical data and images,
0.11 (0.04--0.20) across phases, fell to $-$0.02 ($-$0.13 to $+$0.11) within them (exploratory;
Figure~\ref{fig:3}A)."

Problem: The sentence inverts its order (the within-phase comparison is announced, then the across-phase number
appears first) and carries two estimates with intervals. [8, 9]

Replacement: "Across phases of care, adding the timeline to clinical data and images gained 0.11 (0.04--0.20);
within a phase it gained nothing (Figure~\ref{fig:3}A, exploratory)."

## 24. Methods 2.3, the first evaluation

Original: "The need for this design showed in our own first evaluation: the initial radiomics model reached an AUC
of 0.80 on one test split, and when it was re-selected and re-tested over 500 splits of the same design it averaged
0.72."

Problem: Colon reveal; "the need ... showed" is an abstraction acting; "initial" is a version word. [2, 1, 12]

Replacement: "We saw the need for this design in our first evaluation, in which a radiomics model reached an AUC of
0.80 on one test split and averaged 0.72 when re-selected and re-tested over 500 splits of the same design."

## 25. Methods 2.3, diagnostics

Original: "Comparisons within a phase of care or within an enhancement category are diagnostics: they test what a
score rests on and carry no decision rule."

Problem: Colon reveal; "carry" tic. [2]

Replacement: "Comparisons within a phase of care or within an enhancement category are diagnostics; they test what
a score rests on and set no decision rule."

## 26. Abstract, number count

Original: "On MU-Glioma-Post, the timeline pathway detected the scan at which progression was called with an AUC of
0.82 and the image pathway with 0.71. Fitted once and locked, the models reached 0.77 on LUMIERE, and single-scan
images reached 0.80 on UCSF-ALPTDG, about as high as when trained there."

Problem: Four AUCs in the abstract; STYLE.md 10 (2026-10-23) asks for one or two and sequences in words. The 0.71
is the one the argument needs least here. [8]

Replacement: "On MU-Glioma-Post, the timeline pathway detected the scan at which progression was called with an AUC
of 0.82, and the image pathway lower. Fitted once and locked, the models reached 0.77 on LUMIERE, and single-scan
images reached 0.80 on UCSF-ALPTDG, about as high as when trained there."

## 27. Introduction, claim paragraph (too timid)

Original: "On MU-Glioma-Post, both pathways detected the scan at which progression was called, and models fitted
there held at LUMIERE and UCSF-ALPTDG."

Problem: The one paragraph that states the claim gives no number; the author wants capability shown moderately and
counts two external tests as the strong sign. One number each is the convention. [4, 5]

Replacement: "On MU-Glioma-Post, both pathways detected the scan at which progression was called, and models fitted
there held at LUMIERE and UCSF-ALPTDG with AUCs of 0.77 and 0.80."

## 28. Results 3.5, the model comparison

Original: "Of seven open-weight models (descriptive), only Qwen3.8-27B and Gemma-4-31B passed in every cohort;
smaller models mostly left required content out, and the 2B model also invented numbers."

Problem: "(descriptive)" is a plan label dropped into prose; "the 2B model" is jargon. [10]

Replacement: "Of the seven open-weight models we compared, only Qwen3.8-27B and Gemma-4-31B passed in every cohort;
the smaller models mostly left required content out, and the smallest also invented numbers."

## 29. Results 3.5, the pass counts

Original: "Every evaluation report written by the local model passed the deterministic check against its record:
114 of 114 on MU, 162 of 162 on LUMIERE and 130 of 130 on UCSF (Figure~\ref{fig:5})."

Problem: Colon reveal; "x of x" three times says the same as "every"; short names. [2, 8]

Replacement: "Every evaluation report written by the local model passed the deterministic check against its record
(114, 162 and 130 reports at MU-Glioma-Post, LUMIERE and UCSF-ALPTDG; Figure~\ref{fig:5})."

## 30. Figure 4 legend title

Original: "The confidence keeps its coverage and points to doubtful scans."

Problem: "points to doubtful scans" held at MU-Glioma-Post only (S2 and S3 met at MU only). The title overclaims
what panel B shows. [7]

Replacement: "The confidence keeps its coverage, and at MU-Glioma-Post disagreement marks the less accurate scans."

## 31. Discussion, the closest system

Original: "The closest system we found combines treatment variables extracted by a language model with tumour
volumes to assign a structured follow-up category at one centre, and it reports no uncertainty \citep{jabal2026}."

Problem: "it reports no uncertainty" reads as a mark against the other group; pattern 6 asks for a side-by-side
property. [6]

Replacement: "The closest system we found combines treatment variables extracted by a language model with tumour
volumes to assign a structured follow-up category at one centre, without an uncertainty attached to the output
\citep{jabal2026}."

## 32. Discussion, limits paragraph, last sentence

Original: "PRISM's 120-day forecast was weak in the intended use, so we present it as a detection system."

Problem: "weak" is a verdict on our own result, and the limits paragraph ends on it. [7, 16]

Replacement: "PRISM forecast progression within 120 days less well than it detected it at the scan, so we present
it as a detection system and report the forecast as a secondary task."

## 33. Introduction, paragraph 1 closer

Original: "A model trained on such records can learn from any of these sources."

Problem: A short announcing sentence at the end of the paragraph; the reasoning before it should carry it. [2]

Replacement: "...and the date on which it is recorded depends on when the patient was scanned, so a model trained on
such records can learn from the schedule as well as from the images."

## 34. Results 3.3, within-phase images

Original: "Within a phase, images alone reached 0.68 (0.58--0.77) and the timeline 0.64 (0.51--0.78), so there the
images carried about as much evidence as the timeline."

Problem: "so there the images carried" is awkward; "carry" tic. [1]

Replacement: "Within a phase, images alone reached 0.68 (0.58--0.77) and the timeline 0.64 (0.51--0.78), so within
a phase the images gave about as much evidence as the timeline."

## 35. Introduction, fifth challenge

Original: "Fifth, tumour volumes from automatic segmentation are noisy, the clinician needs to see what was measured,
and patient records often cannot leave the hospital."

Problem: A triplet of three unrelated facts presented as one challenge; the second clause is the consequence of the
first. [2, 5]

Replacement: "Fifth, tumour volumes from automatic segmentation are noisy, so the clinician needs to see what was
measured; and patient records often cannot leave the hospital, so any report must be written inside it."

## 36. Results 3.2, the change range

Original: "...but its change inputs carried less well than the single-scan measurements; change between the two UCSF
scans spanned a range three to six times narrower than at MU-Glioma-Post, which suggests why."

Problem: "which suggests why" is a closer; "three to six times" is a second number range in a sentence about
transport. [2, 8]

Replacement: "...but its change inputs transferred less well than the single-scan measurements, which is consistent
with the change between the two UCSF scans spanning a much narrower range than at MU-Glioma-Post."

## 37. Results 3.3, opening sentence

Original: "The audit shows that on MU the scores rest mainly on where the patient is in treatment, and on UCSF on
how much the tumour enhances (Figure~\ref{fig:3})."

Problem: Short cohort names in the one sentence that carries the section's claim. [10]

Replacement: "The audit shows that at MU-Glioma-Post the scores rest mainly on where the patient is in treatment,
and at UCSF-ALPTDG on how much the tumour enhances (Figure~\ref{fig:3})."

## 38. Results 3.3, ladder paragraph opener

Original: "Each step of the image model's design raised its AUC on MU, and the audit shows what each step added
(exploratory; Figure~\ref{fig:3}C)."

Problem: "MU" short name; "the audit shows" repeats the section opener's construction. [10, 1]

Replacement: "Each step of the image model's design raised its AUC on MU-Glioma-Post, and comparing within phases of
care shows what each step added (exploratory; Figure~\ref{fig:3}C)."

## 39. Results 3.2, section closer

Original: "Similar AUCs at different centres can rest on different evidence, which the audit examines next."

Problem: A transition written as an aphorism; "the audit examines" is an abstraction acting. [1, 2]

Replacement: "Because similar AUCs at different centres can rest on different evidence, we audited what each score
used."

## 40. Methods 2.1, the report figure

Original: "The figure is rendered by code; the language model never sees an image."

Problem: Mild; a semicolon-joined pair that ends on a quotable clause. Acceptable under the author's approved
voice, flagged only because "never" is absolute. [2]

Replacement: "The figure is rendered by code, and the language model receives only the record, not the image."

---

## Global observations

1. **"Carry" is a tic.** "carry / carries / carried" appears about a dozen times in two senses: transport to a
   centre ("carried to LUMIERE", "carries to two external centres") and conveying evidence ("the timeline carried
   most of the evidence", "carry no decision rule", "carry them into each report"). Pick "transfer" for transport and
   "provide" or "give" for evidence, and keep "carry" for the section 3.1 heading at most.

2. **Cohort names switch between long and short forms.** The abstract, 3.3, 3.4 and 3.5 use "MU" and "UCSF"
   while the Introduction, Methods and Discussion use "MU-Glioma-Post" and "UCSF-ALPTDG", sometimes in the same
   paragraph. Either define the short forms once in Methods 2.2 and use them throughout the Results, or use the
   full names everywhere. The abstract must use full names.

3. **0.80 means five different things.** It is the first evaluation's single-split AUC (Methods), the UCSF
   single-scan external AUC (abstract, 3.2), the MU cross-validation AUC of the LUMIERE model (3.2), the median Dice
   of the re-segmentation (3.3) and the Christodoulou AUC (Discussion); 0.82 is the timeline AUC and then the MU
   conformal coverage. Items 10 and 12 remove two of these collisions; the Dice could be stated as "0.8" or in the
   supplement.

4. **The author's voice is mostly present; the residue is colon reveals and closers.** No em dashes, no
   intensifiers, no stacked hedges, no field accusations beyond item 18. The default voice survives in about ten
   colons that announce a list or a number, and in one closing line per section ("before any image is read", "which
   is which", "did the work", "ran the other way", "The report is where the clinician meets these statements"). Those
   are the sentences that will read as Claude to the author.

5. **Tone leans a little timid where the system is strongest.** The claim paragraph of the Introduction gives no
   number (item 27), 3.1 ends the first result on a verdict against our own images (item 1), 3.2 reads its UCSF
   transport as something less than it is (item 7), 3.3 closes the UCSF audit by reducing the AUC to agreement
   (item 6), and 3.4 opens the card on thin evidence (item 5). Each is honest and each belongs, but in every case the
   capability sentence can come first and the limit second, which is the arrangement the author asked for on
   2026-10-26. The Discussion scenario and the modularity paragraph have the right balance and could be the model for
   the rest.
