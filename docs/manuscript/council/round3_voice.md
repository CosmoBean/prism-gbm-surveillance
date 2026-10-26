# Council round 3: would the author have written this?

Reviewer lens: imitate the author. Reference voice is the locked abstract (LOCKED.md: one idea per sentence, concrete
numbers, semicolon-joined contrasts, "we built", "PRISM therefore shows") and the author's words in META_PATTERNS.md
and STYLE.md section 10. Manuscript: paper/main.tex at commit ed1b3cd. Reviewer only; nothing in paper/ was edited.
Rulings from rounds 1 and 2 are not reopened. Every rewrite keeps the facts and numbers; only the sentence changes.

## Overall

The draft is close. What remains of the default voice is three small habits, not slogans: fronted participles
("Fitted once and applied unchanged, the combined model ..."), abstractions as subjects ("the scores rested on",
"evidence lies behind") and a closing clause written to be quoted at the end of five paragraphs (abstract S1, 3.3 P3,
3.5, Discussion P1, Conclusion). The author's own sentences name a concrete thing (a scan, a model, a date), say
what it did, and join the contrast with a semicolon.

## Abstract against the locked voice

Departures from the locked voice: (1) it opens on a four-item list of difficulties, where the locked version opened
on one idea in one sentence; (2) "the scan documenting progression" compresses the locked "the scan where progression
was called"; (3) "Fitted once and applied unchanged, the combined model" is a fronted participle; (4) "the scores
rested mainly on" makes the scores the actor. Same facts and numbers, 148 words (wc):

> Glioma surveillance data differ by centre; most datasets lack treatment dates, progression is documented
> differently, cohorts are small and the hardest scans are few. We built PRISM, which scores each scan through
> separate treatment-timeline and image pathways, attaches a confidence to each and explains it in a report from a
> local language model. On MU-Glioma-Post both pathways detected the scan where progression was called; the timeline
> pathway reached an AUC of 0.82. The combined model, fitted once and applied unchanged, reached 0.77 on LUMIERE; on
> UCSF-ALPTDG, single-scan measurements reached 0.80 and the image pathway, with change between scans, 0.73; a model
> trained there did better. An audit found the models used mainly the treatment timeline at MU-Glioma-Post and
> enhancing tumour volume at UCSF-ALPTDG. Conformal sets for the combined score met their planned coverage at every
> centre, and after one revision every report passed a check against its record.

## Introduction (original → rewrite)

1. L62 "Models for this task meet five challenges that come from surveillance data themselves." → "Surveillance data
   set five challenges for a model of this task."
2. L67–68 "Fifth, segmented tumour volumes are noisy and patient records often cannot leave the hospital, so the
   clinician must see what was measured, in a report written inside it." → "Fifth, segmented volumes are noisy, so the
   clinician needs to see what was measured; and patient records often cannot leave the hospital, so the report has to
   be written there."
3. L69–70 "...external tests the second; in a recent systematic review of automated response assessment, 3 of 20
   studies used external test data \citep{shi2025}." Reads as a count against the field. → "...and external tests the
   second, which 3 of 20 studies in a recent systematic review of automated response assessment included
   \citep{shi2025}; we planned two."
4. L80–81 "It attaches a confidence made of a conformal prediction set, a statement of whether the pathways agree and
   a reliability card, and writes a report with a local language model, checked against the scan's record." → "The
   confidence has three parts, a conformal prediction set, a statement of whether the pathways agree and a reliability
   card; a local language model writes the report, and a checker tests it against the scan's record."
5. L85–86 "An audit of the scores showed that they came mainly from the patient's position in treatment at MU and from
   the enhancing tumour volume at UCSF." → "When we audited the scores, the models at MU used mainly the patient's
   position in treatment, and at UCSF mainly the enhancing tumour volume."

Keep: P1 whole (L53–59, especially "so a model trained on such records can learn from the schedule as well as from
the images"); L73–75 "We asked whether a system could ..."; L84–85 "On MU both pathways detected the scan at which
progression was documented".

## Methods

1. L98–100 "The confidence tells the clinician how much measured evidence lies behind a score in rare situations, and
   the report is written inside the hospital, so the record never leaves it." → "The confidence tells the clinician how
   many scans like this one the system has been tested on; the report is written inside the hospital, so the record
   never leaves it."
2. L100–101 "The third challenge, small cohorts, is handled by how PRISM is evaluated (Section 2.3)." → "We meet the
   third challenge, small cohorts, in how we evaluate PRISM (Section 2.3)."
3. L110 "Both pathways are ridge logistic regressions, with every fitted step inside the training data." → "Both
   pathways are ridge logistic regressions; scaling and any selection were fitted on the training data only."
4. L166 "The task is detection at the scan: is this the scan at which progression is documented?" (colon and a
   rhetorical question) → "The task is to decide, at each scan, whether this is the scan at which progression is
   documented."
5. L204–205 "...are diagnostics; they test what a score depends on and set no decision rule." → "...are diagnostics of
   what a score depends on; none of them is a decision rule."

Keep: L96–98 (five modules, "keep the two kinds of evidence apart, so that the image pathway can run where no
treatment dates exist"); L117–120 "We defined these inputs after finding ..."; L139–140 "Because of the refit ...";
L149–150 (local model writes, deterministic checker tests); L185–188 "We chose this design because in cohorts of this
size one split can move an AUC by more than a change of model. We saw this in our first evaluation ..." (the locked
abstract's own sentence, and the best paragraph in the Methods).

## Results

1. L217–218 "Predicting progression within 120 days of a scan was harder still; PRISM's model reached 0.60 ..." →
   "Predicting progression within 120 days of a scan was harder; the model reached 0.60 (0.52–0.69) in the intended
   use (Supplementary Section S23)."
2. L246–248 "At MU the scan schedule alone separates most of the two classes; most progression scans came ..." → "At
   MU the scan schedule alone separates most progression scans from most non-progression scans, because most
   progression scans came more than 12 weeks after radiotherapy and most non-progression scans came within those 12
   weeks (Table 1)."
3. L254 "Building the image model on MU in three steps shows where its AUC comes from (Figure 3C)." → "We built the
   image model on MU in three steps to see which inputs raised its AUC (Figure 3C)."
4. L267–272 "At UCSF the AUCs therefore largely measure agreement with a progression call made from enhancement at
   the same scan, and enhancement is what PRISM's image pathway quantifies. Deep networks ... so they found the
   evidence the measurements already hold; ..." (two quotable closers) → "At UCSF an AUC therefore largely measures
   agreement with a progression call made from enhancement at the same scan, which the image pathway measures
   directly. Deep networks fine-tuned to score UCSF scans directly learned from the images, above a permuted-label
   control (Table 2), and their scores tracked enhancing volume (correlation about 0.8); their AUC stayed below that of
   enhancing volume alone, and on MU they did not meet the planned gain over the timeline."
5. L314–315 "The clinician therefore reads the segmentation, both pathway scores and the confidence as they stand in
   the record." → "The report therefore gives the clinician the volumes, the two scores and the confidence exactly as
   the record holds them." Also L295–296 "how much measured evidence lies behind its situation" → "how many tested
   cases its situation holds".

Keep: L215–216 "Clinical data alone, without the timeline, scored 0.53, close to chance"; L220–221 (timeline needs
dates, "so we next tested"); L235–236 "The change inputs therefore transferred less well ..."; L239–240 "Because
similar AUCs at different centres can come from different evidence, we audited what each score used"; L263 "At UCSF
the progression calls follow enhancement closely"; L286–288 (0.90 against 0.59); L307–311 (every report passed; "we
corrected the prompt and left the checker unchanged").

## Discussion and Conclusion

1. L322–325 "...and training there raised it further, so the locked results show transfer rather than the best a
   centre can reach." → "...and training there raised it further; the locked results therefore measure transfer, and
   a model fitted at the centre can do better."
2. L360–361 "Progression is the progression documented by each centre, without expert re-reading of the scans; at
   UCSF it agrees closely with an enhancement call at the same scan." → "The label is progression as each centre
   documented it; no scan was re-read for this study, and at UCSF the label agrees closely with an enhancement call at
   the same scan."
3. L364–366 "The report checker is lexical, so it can confirm ... but cannot judge how a clinician reads the report,
   and no clinician has yet read the reports." → "The report checker is lexical; it confirms that every number and
   statement is in the record and says nothing about how a clinician would read the report, which no clinician has
   yet done."
4. L379–380 (Conclusion) "A surveillance system can keep image and treatment-timeline evidence apart, transfer its
   models to other centres without refitting and state how far each score has been tested there." → "PRISM keeps image
   and treatment-timeline evidence apart, and its models held at two other centres without refitting."
5. L380–382 "...and PRISM puts both scores and the evidence behind them in front of the clinician at every scan." →
   "...and PRISM shows the clinician both scores at every scan, with how far each has been tested there."

Keep: L330 "Because its modules are separate, PRISM runs where data are incomplete"; L333–334 (card adds rows); the
illustration P3 (L337–343), especially "decides with information PRISM does not use, such as symptoms, steroid dose
and the radiotherapy plan"; L346 (components described before, not combined); L366–367 (detection system, forecast
secondary); L370 "The next step is to pool the rare situations across cohorts and train on them"; L373–374.

## Five rewrites that matter most

Abstract S1 (claim before the list); Introduction L69–70 (the 3 of 20 count, made neutral); Results L267–272 (two
quotable closers in 3.3 P3); Discussion L322–325 ("transfer rather than the best"); Discussion L360–361 ("Progression
is the progression"). The rest is polish and can wait for the author's read.
