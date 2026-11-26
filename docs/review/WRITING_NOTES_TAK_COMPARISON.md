# Writing notes: PRISM manuscript against Tak et al. 2025 (NEJM AI)

Notes only; `paper/main.tex` is unchanged. Written 2026-11-19 against the working tree of that date.
Line numbers are **source lines of `paper/main.tex`**, not the PDF's `\linenumbers`.
The abstract (LOCKED.md, 2026-11-18) and the title (STYLE 2026-11-18) are author-approved. Suggestions for them are
offered as the smallest possible edits, for the author's decision only.

## What to take from Tak, and what not to take

**Worth taking.** Each paragraph has one clear job.
- Each Results subsection is motivated by the one before ("Given the poor performance of single-scan prediction, we
  next investigated …").
- Clinical use is stated as an action a clinician takes ("could inform if and when to initiate therapy"; "may
  provide reassurance and the ability to deintensify surveillance").
- A weak baseline becomes the contrast that makes the method necessary.
- Captions are long, read on their own and end with the abbreviations.
- One hedge, placed where it matters ("external validation of calibration is recommended before clinical
  implementation").

**Not worth taking.** Tak's vocabulary breaks VOICE.md: "novel", "leveraging", "first", "robustly", "consistently
yielded superior performance", "mimics the behavior of an expert neuroradiologist". Its Results paragraphs pile up
numbers (around 20 AUROCs, deltas and F1 scores in one paragraph), which is worse than PRISM's. Its Discussion also
claims calibration "reliably reflect[s] true probabilities". Take the paragraph architecture and the clinical framing,
not the diction or the number density.

**The overall difference in one line.** Tak writes long sentences with a simple main clause and keeps the
subordinate material clinical. PRISM writes medium-length sentences that are dense with qualifications: what was
planned, what was exploratory, which masks, which cohort, which bootstrap. The reader carries the protocol inside
every claim. Tak keeps protocol in Methods and lets Results sentences read as findings.

---

## Title

**What works.** It is short and has no hype. "Auditable local system" names the two properties the paper defends,
and it fits the house rule (system name, colon, plain noun phrase).

**Changes** (author decision only; the title is settled).
1. Tak's title names the task and the clinical object ("Longitudinal risk prediction for pediatric glioma"). PRISM's
   title names the system's properties but not the task, so a reader cannot tell that the system scores progression.
   - Smallest edit: *PRISM: an auditable local system for **scoring progression on** glioma follow-up MRI*.
   - Alternative, keeping it short: *PRISM: auditable progression scores and reports for glioma follow-up MRI*.
2. If the title stays as it is, the first sentence of the Introduction has to supply the task. At present it does
   so only by implication (line 51).

## Abstract (locked; flag only)

**What works.**
- The premise opens the abstract (line 32) and has a rhythm Tak lacks.
- The abstract carries one baseline number and two external numbers, as STYLE section 5 asks.
- The negative result is used the way Tak uses it: "The separation exposed what a single score would hide" (line 35).
  This is the best sentence in the paper on Tak's own terms.

**Changes, smallest possible.**
1. **"AUC 0.80" is attached to the wrong noun** (line 37): "the combined model added no clear gain over a baseline of
   the two (AUC 0.80)". The number reads as the combined model's AUC, but 0.80 is the baseline's. Edit: "... over a
   baseline of the two, which alone reached an AUC of 0.80."
2. **"Applied unchanged, the reduced combined model ..."** (line 37). "Reduced" is defined only in Methods. Tak never
   puts an undefined variant name in the abstract. Edit: "Applied unchanged at two other centres, the combined model
   reached 0.77 at LUMIERE and 0.86 at UCSF-ALPTDG." The reduced form stays in Results.
3. Tak's abstract ends on the use ("point-of-care decision support"). PRISM's ends on the verifier, a technical
   detail. This change is optional, and the abstract is at 149 words. If a sentence can be freed, end on the intended
   use: "... so that a reader can see, at each scan, which evidence the score follows."

## Introduction (lines 51–132)

**What works.**
- Paragraph 1 opens on the clinical reading situation and ends on the paper's premise: "The timing of a scan is part
  of the evidence a clinician uses to read it" (line 58). This is better than Tak's first paragraph, which is a
  prognosis survey.
- The literature is cited by finding and number, never by name-dropping.
- "A high AUC in this setting therefore says little until its basis is known" (line 88) is a claim-first topic
  sentence of exactly Tak's kind.
- Where it is defined, "auditable" is defined operationally (lines 119–121).

**Changes.**
1. **Missing paragraph: the clinical need stated as an action.** Tak's second paragraph says what earlier knowledge
   would let clinicians *do*. PRISM goes from the reading problem (paragraph 1) to imaging methods (paragraph 2) and
   never says what decision a follow-up scan feeds. Add one or two sentences at the end of paragraph 1, framed as the
   decision a reader faces and not as a benefit:
   - Current (line 58): "The timing of a scan is part of the evidence a clinician uses to read it."
   - Target: "The timing of a scan is part of the evidence a clinician uses to read it, and the reading decides
     whether treatment continues, the scan is repeated, or second-line treatment is considered. A score offered at
     that moment is useful only if the reader can tell which of these sources it follows."
2. **Paragraph 3 has two jobs** (lines 73–85): weak validation, and then "Longitudinal and interpretable designs have
   begun to appear." Tak's third paragraph has one job, the technical gap. Split it.
   - End paragraph 3 at the Gomaa sentence, which is the strongest premise for PRISM ("time since the end of
     treatment was the strongest input").
   - Fold Tak and Tarek into paragraph 4 as the nearest precedents for inspectable inputs.
   - Also, "interpretable" (line 82) clashes with the house word "inspectable" (STYLE 2026-11-15). Write "Longitudinal
     designs, and designs whose inputs can be inspected, have begun to appear."
3. **The literature paragraphs read as a catalogue of counts.** Paragraph 2 (lines 62–70) gives six statistics from
   five studies. Tak's literature sentences each advance the gap ("none has leveraged multiple scans").
   - Keep one number per cited idea, and let the topic sentence carry the conclusion.
   - Current (line 66): "Of 220 European centres, 60\% reported follow-up scans in free text and 27\% applied RANO."
   - Target: "Centres also read these scans differently. Most of 220 European centres reported them in free text
     \citep{thust2018}, and structured systems such as BT-RADS make the clinical history part of the reading itself."
     The Zhang and Gore numbers then go, or move to one clause.
4. **The conformal paragraph (lines 99–102) ends on the method's weakness without linking it to PRISM.** Read cold,
   it argues against a component the paper then uses. Close it on what PRISM does with the limit:
   - Current (line 100): "... in medical image classification it does not hold within subgroups or under distribution
     shift."
   - Target: "... and in medical image classification it need not hold within subgroups or at another centre
     \citep{mehrtens2023}, so PRISM reports coverage by group and states, at each scan, how many comparable scans the
     models were tested on."
5. **End the Introduction the way Tak does, with one "we found" sentence and one forward sentence.** At present the
   finding is buried in bullet 2 (lines 125–127), and the list ends on the report.
   - Tak: "We found that temporal learning substantially improves recurrence prediction …"
   - Target, after the list: "On MU-Glioma-Post the separate scores showed that the time after radiotherapy and the
     enhancing tumour carried most of the ranking, and the models, locked, kept their ranking at two external
     centres."
   - Then remove the finding from bullet 2, so that the bullet names the measurement (the baseline and the split
     AUC), as STYLE 2026-11-15 asks: "each a technical object with how it is measured".

## Methods (Sections 2–3, lines 138–447)

**What works.**
- Methods follow the order the Results need.
- Every input is dated "as of the scan day" (line 211). Tak never states this guard so plainly.
- The AUC split is given as a two-line identity with a citation. Tak describes its intrapatient analysis in prose,
  and PRISM's version is clearer.
- Planned versus exploratory status is marked in one word where it applies, as STYLE section 4 asks.

**Changes.**
1. **Protocol stacked inside sentences.** The worst case is lines 305–309: one sentence lists eight analyses that used
   2,000 bootstrap samples, and the paragraph ends on "UCSF-ALPTDG was no longer on our hardware when they ran". That
   clause is report-style and reads as an excuse.
   - Target: "AUCs carry 95\% CIs from bootstrap samples of patients (1,000; 2,000 for the analyses of
     Sections~\ref{sec:3.3}–\ref{sec:3.4}), which resample held out predictions without refitting. The baseline, the
     AUC split and group calibration were each planned before they were coded and were run on MU and LUMIERE."
   - Table 3 already states "Not run (data not on hand)", which is enough.
2. **The heading of Section 3.3 does not match its content.** "Timing-and-enhancement baseline and AUC split"
   (line 332) heads four paragraphs, two of which are about the published pipeline and mask sensitivity. Tak's
   Methods headings are plain nouns that match their content. Use "Comparisons and baselines", or give the published
   pipeline and mask sensitivity their own subsection.
3. **Development history in the verifier paragraph** (lines 431–435): "The rules as first written ... rejected every
   evaluation report ... We then let the rules read the region from the text of a cited field as well ...". STYLE
   2026-11-18 allows the revision once in Methods. It should be one clause, stated as a rule rather than as a story:
   - Target: "Each rule reads the region from the names and the text of the cited fields. This form was fixed after
     testing on synthetic records and the 48 reports used to develop the prompt, before the evaluation reports were
     checked."
4. **The checker's blind spot is stated as a weakness, not as the reason for the verifier** (lines 422–424): "Because
   the checker accepts a number that equals a number in any cited field, it accepts a sentence that gives the FLAIR
   volume as the enhancing volume ...". Turn it into motivation, which is how Tak frames the shortfall of a baseline.
   - Target: "The checker matches each number to any field the sentence cites, so it cannot tell which region a
     number belongs to. The verifier adds that binding."
5. **Captions and table captions carry results.** Table 1 (line 175): "(coding it as its own category changed no AUC
   clearly)". This is a result in a caption, and it is already a row of Table 2. Delete it from the caption, following
   STYLE section 5 ("never the same number twice").

## Results (Section 4, lines 490–686)

**What works.**
- 4.2 and 4.3 have declarative headings.
- Most first sentences state the finding, and the number comes after the comparison is set up. Line 494 is an
  example: "On the same MU scans, masks, label and folds, the published radiomics pipeline ... reached 0.58".
- The baseline is used exactly as Tak uses its single-scan model: a planned comparison stated neutrally, which shows
  what the ranking rests on.

**Changes.**
1. **Make every heading a finding, and take development history out of 4.5** (STYLE 2026-11-18: never in headings).
   | Line | Current | Target |
   |---|---|---|
   | 490 | Comparison with the published radiomics pipeline on the same task | Simple models ranked scans above the published radiomics pipeline on the same task |
   | 608 | The confidence statements describe the evidence behind each score | Conformal sets met their planned coverage, and disagreement between the models marked harder scans |
   | 647 | Reports passed the checker after one revision of the prompt | Every report passed the record check, and the verifier caught each misplaced value |

   "Evidence behind the score" is on VOICE.md's list of phrases to avoid.
2. **Link the subsections the way Tak does.** Each PRISM subsection stops; none hands on to the next. The one
   exception is line 512, "Section 4.3 traces the source ...", which works.
   - Add a closing sentence to 4.2. It currently ends on the UCSF label paragraph (lines 557–560), so the section ends
     on a caveat.
   - Target, after line 560: "Because the label at each centre is tied to the timing and the enhancing tumour, the
     next question is how much of the ranking those two alone supply."
   - Move the label paragraph *before* the UCSF numbers (STYLE section 5: a number arrives after the sentence that
     tells the reader what it would mean). Then "enhancing volume alone reached 0.88 at UCSF" reads as a consequence
     of the label, not as a rebuttal of the 0.86.
3. **Take reserve material out of the main line of 4.1.** Lines 497–502 contain three items that belong in the
   supplement:
   - "An earlier re-implementation from the published description ..." is project history.
   - The 100-split range is a reviewer answer.
   - "cannot be compared with ours" is commentary.
   Lines 507–508 (all scans as negatives) repeat Table 2. Tak keeps each Results paragraph to one comparison.
   - Target for the end of the first paragraph: "Single held out sets of this size vary widely (0.32 to 0.88 over 100
     random sets of 18 patients), so the published estimate, from one held out set and a different label, is not
     comparable with ours." Everything else in that paragraph goes to Supplementary Section S-x and RESERVE.md.
4. **Line 644 ends a paragraph with a contrast slogan that reads as self-undermining**: "We therefore present the
   agreement and the card as descriptions of the evidence, not as warnings." This breaks two rules: "not X but Y"
   (STYLE section 6) and no commentary against the paper's own components (2026-11-17).
   - Target: "The agreement and the card therefore describe the evidence at each scan. At MU, scans on which the two
     models disagreed were those the combined score ranked less well." Lead with the MU result.
5. **Line 650–652 opens 4.5 with history**: "... after one revision of the prompt, made because every LUMIERE report
   first failed (exploratory)." Tak never reports a training retry in Results. The revision is stated once in Methods
   (Section 3.5) and in Table 2.
   - Target: "All 406 reports written by Qwen3.8-27B for patients not used to develop the prompt passed the record
     check (114 at MU, 162 at LUMIERE and 130 at UCSF; exploratory, Table~\ref{tab:2})."
   - Lines 655–657, the regenerated reports with renamed fields, are procedural and go to the supplement.

Also: line 684 still has a `\todo{AUTHOR: ...}` inside a Results sentence, and the phrase "kept ranking" appears at
lines 518, 733 and 764. Vary it, or let one instance carry the claim.

## Discussion (lines 729–766)

**What works.**
- The first paragraph answers the Introduction's question in its first clause, as STYLE section 9 asks.
- Paragraph 2 turns the method into advice for the field ("Studies ... could report two quantities beside the AUC").
  This is the most Tak-like move in the paper and is better than Tak's "we expect this strategy will improve …".
- The limits are stated as scope, and the paragraph ends with "left to future work".

**Changes.**
1. **No paragraph says what a reader does with PRISM at one scan.** Tak's second Discussion move ("could inform if and
   when to initiate therapy ... reassurance and the ability to deintensify surveillance") is what makes its paper read
   as clinical. Add a short paragraph after paragraph 1, framed as intended use and using the measured proxies
   (STYLE 2026-11-15):
   - "Consider a scan eight weeks after radiotherapy with growing enhancement. The clinical-history score follows the
     time window, the imaging score follows the measurements, and the record states whether they agree and that MU
     holds few comparable scans in that window. At MU, agreement between the two models marked the scans the combined
     score ranked well (AUC 0.90 against 0.59). This is the information a single score would not show."
   - Do not quote 0.90 against 0.59 again if it already appears in 4.4; point to it instead.
2. **Add a mechanism paragraph in clinical terms.** Tak's third Discussion paragraph explains *why* the method works
   in terms of what a clinician does. PRISM's mechanism is that follow-up schedules and the 12-week rule tie timing to
   the label. That mechanism is stated in Introduction paragraph 4 (line 91), but the Discussion never returns to it.
   - Target: "Timing carries much of the ranking because follow-up practice puts it there. The response criteria treat
     the first 12 weeks apart, few progressions are recorded inside them, and a model given the dates learns the
     schedule. PRISM does not remove this signal. It reports the signal as its own score, so that the reader can weigh
     it as RANO already asks them to."
   - Check this wording against the 2026-10-26 "no RANO" rule. Paragraph 1 of the Introduction now cites RANO 2.0; if
     RANO stays out, write "as the response criteria already ask them to".
3. **Paragraph 3 (lines 742–744) is two sentences without a claim of its own.** Fold it into the scope paragraph, or
   open it with its claim: "Calibrating within small groups moved coverage between groups rather than raising the
   worst." The second sentence then gives the remedy.
4. **The Conclusion leads with the radiomics comparison** (line 763). STYLE 2026-11-18 keeps that comparison out of
   the abstract, and the Conclusion should follow the abstract's spine. Tak's conclusion leads with what was built and
   what it enables.
   - Target: "PRISM keeps treatment-course and image evidence as separate scores in one checked record. On public
     glioma follow-up data this separation showed that timing and the enhancing tumour carry much of the ranking. The
     locked models kept their ranking at two other centres, and every report was checked against its record."

## Captions

**What works.**
- The Figure 1 caption reads on its own and describes the panels in order, as Tak's captions do.
- The Figure 3 title "Where the ranking comes from" is the kind of caption title Tak uses for its Figure 4 (a
  finding).
- Captions state how the intervals were obtained.

**Changes.**
1. **"Development centre" in the Figure 2 title** (line 532): "Performance at the development centre and at two
   external centres." STYLE 2026-11-01 bans this phrase.
   - Target: "**The locked models kept ranking scans at two external centres.** (a) MU-Glioma-Post, the public
     development cohort; (b) LUMIERE; (c) UCSF-ALPTDG. ..."
2. **End each caption with its abbreviations, as Tak does.** None of PRISM's captions does this, and "MU", "T1c",
   "FLAIR", "CI" and "UCSF" are used without expansion. Example line for Figure 1: "MU denotes MU-Glioma-Post; UCSF,
   UCSF-ALPTDG; T1c, contrast-enhanced T1-weighted MRI; FLAIR, fluid-attenuated inversion recovery."
3. **State a finding in every caption title.** "The task and the method", "Coverage within groups of comparable
   scans", "The report PRISM writes, and the check" and "Planted errors rejected by the checker and the verifier" are
   all labels.
   - Figure 4: "Calibrating within groups moved coverage between groups."
   - Table 5: "The verifier rejected every misplaced value that the checker accepted."
4. **History in captions.** The Figure 5 caption (line 668) says "after one revision of the prompt". Table 2 (line
   475) is the one place where the revision must appear, so delete it from the caption.

## Cross-cutting: jargon and signposting

- **Internal vocabulary.** "Tested tier", "few cases", "the card", "flag", "intended use scans", "detection scans",
  "reduced" and "situation" are project words. Tak defines each new term once, in a clause, and then uses it the same
  way every time. Define each of these at first use in Section 2.3 and use it identically after that. For example,
  "situation" (line 239) should be defined there as "time window and state of the enhancing tumour".
- **Signposting.** Tak signposts with figure pointers ("(Fig. 3 and Table S2)"), not with section cross-references.
  PRISM uses a mixture of both, which is fine. Avoid the "Section~X traces …" construction except at section ends.
- **Hedging.** PRISM's hedges are statistical ("CI includes zero", "exploratory"), not verbal. That is the right
  register. Do not import Tak's "may", "likely", "we hypothesize" except in the mechanism paragraph.

---

## Top 10, in priority order

1. **Make Results headings findings and take development history out of the 4.5 heading** (lines 490, 608, 647).
   This is cheap, the author's rules require it, and it is the most visible change.
2. **Add a Discussion paragraph on what a reader does at one scan.** Use the measured agreement result as the proxy
   (Tak's "if and when to initiate therapy" move), framed as intended use.
3. **Add the "clinical need as an action" sentence at the end of Introduction paragraph 1** (line 58): the decision
   the reading feeds.
4. **End the Introduction with one "we found" sentence after the contributions**, and turn bullet 2 into the
   measurement rather than the finding (lines 121–132).
5. **Move the UCSF label paragraph before the UCSF numbers and close 4.2 with a hand-on sentence to 4.3** (lines
   518–560). The section should end on the next question, not on a caveat.
6. **Clear reserve material and history from 4.1 and 4.5**: the earlier re-implementation, the 100 splits, the
   repeated sensitivity numbers, and the renamed-field regeneration (lines 497–508, 650–657).
7. **Rewrite the self-undermining contrasts**: line 644 ("not as warnings"), the checker blind spot (lines 422–424)
   restated as the motivation for the verifier, and the conformal paragraph in the Introduction (line 100) closed on
   what PRISM does.
8. **Fix the captions.** Remove "development centre" (line 532), add abbreviations at the end of each caption, give
   each caption a finding as its title, and remove results and history from captions (line 175, line 668).
9. **Strip protocol from Methods sentences** (lines 305–309, 431–435): one bootstrap clause, one clause for the rule
   revision, and no "no longer on our hardware". Rename Section 3.3 to match its content.
10. **For the author's decision on locked text**: in the abstract, attach "AUC 0.80" to the baseline and drop
    "reduced" (line 37); optionally put the task in the title ("scoring progression on").
