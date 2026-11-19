# Council round 5: fresh editor read of `paper/main.tex`

Read as a senior editor seeing the submission for the first time, from `paper/main.tex` only (text, tables, legends). Line numbers refer to the file as read on 2026-10-26.

## 1. The claim, and whether the paper tells one story

**Claim in two sentences.** PRISM scores each post-treatment glioma scan through separate treatment-timeline and image pathways, attaches a conformal set, an agreement statement and a reliability-card tier to each score, and writes a checked report with a local language model. Developed on MU-Glioma-Post, its models ranked scans at two other centres without refitting (combined 0.77 at LUMIERE; image pathway 0.73 and single-scan 0.80 at UCSF), but an audit shows the scores rested on different evidence at each centre (scan schedule at MU, enhancing volume at UCSF) and the risk scale did not transfer to UCSF.

**Do the abstract, the first sentences and the Conclusion agree?** Largely yes, and better than most submissions: the last Introduction paragraph (lines 85--90), the abstract's second half and the Discussion opener (lines 326--331) are near-paraphrases of one another, and every Results heading is a claim that its paragraph supports. Three places drift:

- **The Conclusion and the abstract lead with different things.** The Conclusion (line 380) says the point is *keeping the evidence apart and stating how far each has been tested*; the abstract spends its weight on numbers and only says "so the clinician sees what each score uses" in passing. The Conclusion is the better story; the abstract should carry it.
- **The combined score at UCSF is never given in the text.** The abstract reports the combined score at LUMIERE (0.77) and then switches to pathway results at UCSF; Section 3.2 does the same; Figure 2 presumably shows it. A first-time reader notices the switch and assumes the number is bad. Whatever it is, state it once (Section 3.2) and let the abstract either name it or say explicitly that at UCSF the image pathway is the transferable score.
- **"Both pathways detected the progression scan" (abstract, heading 3.1) versus "mostly by separating phases of care" (line 212) versus "the scan schedule alone separates most progression scans from most non-progression scans" (line 250).** The abstract's audit sentence says "used mainly the timeline", which a reader takes to mean "treatment variables mattered", not "when the patient was scanned mattered". The first-sentence story and the Results story differ here by one word; fix it in the abstract (see Section 6).

The MU denominators also do not tell one story: 146 scans in the intended use (line 210), 181 over all scans (Table 1), 249 in the card (line 300), 114 reports (line 312), 126 patients characterised for a *different* task (Table 1 note a). Each may be right, but nothing in the main text reconciles them, and Table 1 note b (181 + 47 excluded = 228, not 249) makes the reader do arithmetic that does not come out. One flow figure in the supplement and one sentence in Section 2.2 would settle it.

## 2. Does the paper show what the system can do, at a credible strength?

Yes, and its strength is well judged in most places: pre-committed external tests with commit hashes, a planned gain that was *not* met and is said so in the first Results paragraph, an audit that explains its own headline number away, a first report evaluation that failed at 0 of 178. A reviewer will trust this paper. Where it misjudges:

**Oversells (mild, but each is the kind a reviewer seizes on).**

1. *Agreement warning, Section 3.4 (lines 290--296).* The paragraph leads with the exploratory MU-fixed-median result at LUMIERE (difference 0.22, CI excluding zero) and ends with the pre-specified version (0.11, CI crossing zero). The pre-specified result must come first; the exploratory one may follow as the explanation. The Table 2 "Met" cells for S2 and S3 are unreadable for the same reason: they try to say yes-and-no-and-exploratory in one cell.
2. *Enhancing volume alone at UCSF (0.88) beats every model, including the one trained there (0.86).* Section 3.3 says so plainly (line 266), but the abstract reports 0.80 / 0.73 / 0.86 and omits the one number that puts them in proportion. The Discussion (line 330) says "the image measurements provided the score" where it should say "the simplest baseline, enhancing volume, scored as well".
3. *"Every report passes a check" (heading 3.5; line 319 "therefore gives the clinician ... exactly as the record holds them").* The check is lexical, 100% was reached after a prompt revision developed on 20 external patients, and the sentence at line 319 draws a conclusion the check cannot support. The heading is fine; line 319 is not.
4. *Heading 3.2 "The models rank scans at two external centres without refitting."* At UCSF the reduced timeline transferred at 0.56 and the combined score is not reported. "The image models rank scans..." or "The locked models rank scans..." with the UCSF combined number stated would be exact.

**Undersells (the paper is more useful than it says).**

1. *The schedule finding is a field-level result and is buried as an audit.* A model trained on dated clinical records learns the scan schedule; at MU the schedule alone separates most positives from most negatives (line 250), the timeline's gain disappears within a phase ($-$0.02), and the planned imaging model's gain over all gliomas (+0.041, Table 2 note) "may reflect the schedule inputs". This is a warning for every surveillance model trained on records of this kind. It deserves one sentence of its own in the Introduction's challenge list and one in the Discussion, not a clause.
2. *Within a phase of care the images gave as much evidence as the timeline (0.68 vs 0.64; line 254).* This is the paper's best argument that the image pathway is worth having at MU, and it is a subordinate clause.
3. *Q2 at UCSF, +0.248 (+0.096 to +0.392) for images over clinical data (Table 2 only).* The clearest pre-specified positive result in the paper is not in the text.
4. *The split-variance result (0.80 on one split, 0.72 over 500; lines 181--183)* justifies the whole evaluation design and is tucked into a Methods sentence. One clause in the Introduction's third challenge would do.
5. *The reliability card's main finding, that most situations at MU and all at UCSF are few-case, including every situation in the first 12 weeks after radiotherapy,* is the honest centre of the paper (it says: the system knows where it has not been tested). It is in 3.4 and in the Discussion illustration, but the abstract does not mention the card at all.

## 3. Fifteen sentences to fix (quote, then replacement)

1. **Abstract, line 34.** "Treatment effects can mimic glioma progression on MRI; most datasets lack treatment dates, centres document progression differently and the hardest scans are few."
   → "Treatment effects can mimic glioma progression on MRI, and models of progression are hard to validate: most datasets lack treatment dates, centres document progression differently, and the hardest scans are few." *(The three clauses need a subject; without "hard to validate" the reader does not see why they are listed.)*

2. **Abstract, line 35.** "We built PRISM, which scores each scan through separate timeline and image pathways, so the clinician sees what each score uses, and adds a confidence and a local language model's report."
   → "PRISM scores each scan through separate treatment-timeline and image pathways, so the clinician sees what each score uses, attaches a confidence to each, and writes a checked report with a local language model."

3. **Introduction, line 58.** "In routine care, progression is therefore documented from the images together with symptoms and the course of treatment, and the date on which it is recorded depends on when the patient was scanned, so a model trained on such records can learn from the schedule as well as from the images."
   → "In routine care, progression is documented from the images together with symptoms and the course of treatment, and its date depends on when the patient happened to be scanned; a model trained on such records can therefore learn the scan schedule as well as the images." *("therefore" was attached to the wrong clause.)*

4. **Introduction, line 71.** "Repeated cross-validation addresses the third challenge and external tests the second, which 3 of 20 studies in a recent systematic review of automated response assessment included \citep{shi2025}; we planned two."
   → "Repeated cross-validation addresses the third challenge and external tests the second; only 3 of 20 studies in a recent systematic review of automated response assessment included an external test \citep{shi2025}. We planned two."

5. **Introduction, line 86.** "On MU both pathways detected the scan at which progression was documented; the ranking of scans by the models fitted there transferred to LUMIERE, and by the image measurements to UCSF."
   → "On MU both pathways detected the scan at which progression was documented. The combined model's ranking of scans transferred to LUMIERE, and the image pathway's to UCSF."

6. **Methods 2.1, line 105.** "On MU its inputs are age, sex, IDH mutation and MGMT promoter methylation, which alone form the clinical-only reference model, together with the days since diagnosis and since surgery, the start, end and dose of radiotherapy, chemotherapy and the visit index, each taken as of the scan day."
   → "On MU its inputs are age, sex, IDH mutation and MGMT promoter methylation (which alone form the clinical-only reference model), the days since diagnosis and since surgery, the start, end and dose of radiotherapy, chemotherapy, and the visit index, each as of the scan day."

7. **Methods 2.1, line 136.** "It comes from the combined model refitted on 70\% of the MU patients and calibrated on the remaining 30\% (...); on MU this split is made inside each training fold, and for the external cohorts one MU-calibrated set was applied unchanged, which assumes that their scans are exchangeable with MU's."
   → "It is calibrated on 30\% of the MU patients after the combined model is refitted on the other 70\% (...); on MU this split is made inside each training fold, and at the external cohorts the MU-calibrated set is applied unchanged, which assumes their scans are exchangeable with MU's."

8. **Methods 2.1, line 138.** "The two pathways agree when both scores lie on the same side of that pathway's median score over the MU training scans of the locked models (on MU, over the held-out scores of the other folds), so the rule can be applied at a single scan; it uses scores only, never labels."
   → "The two pathways agree when each score lies on the same side of its own median, taken over the MU training scans (on MU, over the held-out scores of the other folds); the rule needs only the two scores, never a label, so it can be applied to a single scan."

9. **Methods 2.3, lines 194--200 (the enumeration).** "They are the definition of the image pathway on MU (its use at UCSF and in the system tests was planned); the three-step comparison ... and the operating point of a threshold fixed on MU."
   → "They are listed in Supplementary Table~S\todo{x}; the Results mark each ``(exploratory)'' where it first appears in a paragraph, as do the figure and table notes." *(The 110-word list is a confession, not an argument; the supplement table keeps the disclosure complete.)*

10. **Results 3.1, line 212.** "The combined score also reached 0.82; on MU the images did not raise the timeline's AUC, and the planned imaging model fell short of the pre-specified gain of 0.03 (Table~\ref{tab:2})."
    → "The combined score also reached 0.82: on MU the images did not raise the timeline's AUC, and the pre-specified imaging model, which adds three schedule inputs (Section~\ref{sec:3.3}), gained 0.015 against the planned 0.03 (Table~\ref{tab:2})." *(A first-time reader meets "planned imaging model", "image pathway" and "combined score" in one paragraph and cannot tell them apart until Section 3.3.)*

11. **Results 3.2, line 225.** "Enhancing tumour volume alone, with no fitted model (exploratory), scored 0.62 on MU, below the image pathway, and 0.66 on LUMIERE, as high as the image pathway, so at LUMIERE the transfer rests on the combined score (Figure~\ref{fig:2})."
    → "Enhancing tumour volume alone, with no fitted model (exploratory), scored 0.62 on MU, below the image pathway, and 0.66 on LUMIERE, level with it; at LUMIERE only the combined score did better than this simplest baseline (Figure~\ref{fig:2})."

12. **Results 3.3, line 270.** "At UCSF an AUC therefore largely measures agreement with a progression call made from enhancement at the same scan, which the image pathway measures directly."
    → "At UCSF an AUC therefore largely measures agreement with a progression call that was itself made from enhancement at the same scan, and enhancement is what the image pathway measures."

13. **Results 3.4, line 279.** "At the 80\% level, the conformal sets of the combined score covered between 0.78 and 0.87 of scans in the three cohorts, meeting on point estimates the threshold of 0.78 fixed in advance, a tolerance of 0.02 below the nominal level (Figure~\ref{fig:4}A)."
    → "At the 80\% level, the combined score's conformal sets covered 0.78 to 0.87 of scans across the three cohorts, meeting on point estimates the pre-specified threshold of 0.78 (the nominal level less a tolerance of 0.02; Figure~\ref{fig:4}A)."

14. **Results 3.4, lines 293--296 (reorder; replaces "At LUMIERE the AUCs were 0.89 and 0.67 ... With each cohort's own medians, as in the tests fixed in advance, the LUMIERE difference was 0.11, $-$0.05 to 0.27").**
    → "At LUMIERE the difference was 0.11 ($-$0.05 to 0.27) with the cohort's own medians, as fixed in advance, and 0.22 (0.10--0.34) with medians fixed on MU (exploratory); at UCSF neither version had an interval that excluded zero."

15. **Discussion, lines 328--331.** "At the development centre the timeline provided most of the evidence, largely because of when patients were scanned, and within a phase of care the images provided about as much; at UCSF the image measurements provided the score, and training there raised it further; the locked results therefore measure transfer, and a model fitted at the centre can do better."
    → "At the development centre the timeline provided most of the evidence, largely because of when patients were scanned; within a phase of care the images provided about as much. At UCSF enhancing volume provided the score, and the simplest baseline, enhancing volume alone, did as well as any model, including one trained there. The locked results therefore measure transfer; a model fitted at the centre can do better."

Two more, outside the fifteen, that are short enough to just do: line 319 "The report therefore gives the clinician ... exactly as the record holds them." → "Within what a lexical check can test, the report gives the clinician the segmentation figure and its volumes, the two scores and the confidence as the record holds them."; and the Discussion first sentence (line 326) should end at "in the scan's situation." with "which for most scans at MU and UCSF is little" promoted to its own next sentence, so the claim is made before it is qualified.

## 4. Hiding, spinning, or apologising too much

**Looks like hiding (even where it probably is not).**

- The missing combined-score AUC at UCSF (see Section 1). This is the single thing a reviewer will ask for first.
- The order of the agreement-warning results (pre-specified last, exploratory first), and the S2/S3 "Met" cells in Table 2 that say "Both at MU; set at LUMIERE, and disagreement there with medians fixed on MU (exploratory); none at UCSF". Replace each cell with Yes/No for the pre-specified rule in each cohort, and put the MU-fixed-median variant in the note.
- Table 1 note a: the patient characteristics describe the 120-day cohorts, not the detection cohorts the table is about. Characterise the detection cohorts, or say in the caption which rows describe what.
- The 249-scan card denominator with no derivation (Section 1).
- Line 237--244 on calibration: "overpredicted progression at UCSF (observed over expected 0.72)" and "a threshold set at the MU median called 90\% of UCSF scans positive" are stated and then immediately framed as a recalibration instruction. That is the right conclusion, but the Discussion's limitations paragraph says only "at UCSF its risk scale did not" transfer. Say the 90\% once more there; it is the practical consequence.

**Spin.**

- Abstract "both pathways detected the progression scan" for an image pathway at 0.71 (exploratory) and a timeline at 0.82 that the audit attributes to the schedule. Give the numbers and the audit result in the same breath (Section 6).
- Figure 4 caption and heading 3.4 "keeps its coverage" is acceptable only with "on average", which both have; fine. But "Most sets were informative, holding a single outcome for 62\% to 75\% of scans" (line 281) sits beside the by-outcome shortfall (0.65 coverage of non-progression scans at UCSF) without noting that single-outcome sets are exactly where the shortfall lives. One clause.

**Apologising too much.**

- "(exploratory)" appears roughly twenty times in the Results and in every figure caption. It is honest, and the Methods paragraph says it will be done, but by Section 3.4 it reads as a tic and dilutes the one place it matters (the agreement rule and card being defined post hoc). Keep the tag on the first mention in each subsection and in the figure and table notes; drop the rest.
- The Methods 2.3 enumeration paragraph (fix 9) and the sentence "Comparisons within a phase of care or within an enhancement category are diagnostics of what a score depends on; none of them is a decision rule" (line 201), which no reader would have mistaken for a decision rule.
- The limitations paragraph (lines 363--368) is a list of seven clipped sentences ("Subgroups are small." "No clinician has yet read the reports.") that reads as hurried rather than candid. Two or three full sentences would carry the same content with more authority.
- Discussion opener "which for most scans at MU and UCSF is little" undercuts the claim inside the sentence that makes it (see end of Section 3).

## 5. What the main text does not need, and what it lacks

**Move to the supplement.**

- The unplanned-analyses enumeration (Methods 2.3, lines 194--200), as a table.
- The three-step image ladder paragraph (Section 3.3, lines 258--262). Keep one sentence: the schedule inputs raise the AUC across phases of care (+0.10) but not within them ($-$0.01); the rest is the supplement's.
- The Brier scores in the card paragraph (lines 302--305). Keep "at MU the order was reversed, because the few-case scans there were mostly easy non-progression scans early after radiotherapy".
- Report-count housekeeping (line 312--315: 114/162/130; the 10 + 10 excluded development patients). Keep the counts in Figure 5; the exclusion belongs in Methods or the supplement.
- Table 2 note, the all-glioma re-fit sentences ("The locked models were fitted on grade 4 rows where the UCSF-ALPTDG plan named all MU-Glioma-Post detection scans ..."). This is a deviation log, and the text already points to a supplementary section for deviations.
- The seven-model report comparison (L1) can stay as a table row; the "six other open-weight models" detail in the AI-use declaration is enough.

**Missing; I would require before review.**

1. The combined-score AUC at UCSF, in Section 3.2.
2. A scan-flow figure (supplement) and one Methods sentence reconciling 126 patients / 146 / 181 / 249 / 114 scans at MU and the analogous counts at LUMIERE (61 patients; 178 scans in the first report evaluation; 162 in the second) and UCSF (140 patients; 69 detection scans; 130 reports).
3. How missing inputs are handled. Table 1 shows IDH unknown for 46 of 140 UCSF patients and MGMT unknown for 26; the Methods never say how a ridge model receives "unknown".
4. One sentence on what the pre-specified gain of 0.03 could have detected: the CI on the MU gain is about $\pm$0.05 wide, so the study was not powered to find 0.03 and the "No" in Table 2 row 1 is partly a sample-size result. Saying so protects the authors.
5. A sentence on segmentation quality or at least on its variability across the three mask sources (three different segmentation pipelines feed the same locked image model; "harmonised volumes" is promised to a supplementary section but never defined in the text).
6. The title (`\papertitle` macro, not visible in this file) must carry the Conclusion's claim, not a numbers claim.
7. The Tikhonov 2025 reference (line 357) is unverified; either verify or cut the clause.

## 6. The abstract

The current abstract works for a careful reader and fails for a busy one: the UCSF sentence ("single-scan measurements reached 0.80 and the image pathway, with change between scans, 0.73, against 0.86 when trained there") takes three reads, the card is absent, and "used mainly the timeline" hides the schedule finding. Proposed replacement, same facts, 149 words (the [PROPOSED] flag excluded from the count):

> Treatment effects can mimic glioma progression on MRI; most datasets lack treatment dates, centres document progression differently, and the hardest scans are few. PRISM scores each scan through separate treatment-timeline and image pathways, so the clinician sees what each score uses, attaches a confidence, and writes a checked report with a local language model. Developed on MU-Glioma-Post, where the timeline pathway reached AUC 0.82 and the image pathway 0.71, its models were applied unchanged at two centres: the combined score reached 0.77 at LUMIERE, and at UCSF-ALPTDG single-scan measurements 0.80 and the image pathway 0.73 (0.86 when trained there). The scores rested mainly on the patient's position in treatment at MU-Glioma-Post and on enhancing volume at UCSF-ALPTDG. Conformal sets met planned coverage on average at every centre but fell short for one outcome at both external centres, and after one revision every report passed a check against its record.

If the authors can spare four words, "and the reliability card states where evidence is thin" is the one fact the abstract still lacks; it would replace "attaches a confidence".
