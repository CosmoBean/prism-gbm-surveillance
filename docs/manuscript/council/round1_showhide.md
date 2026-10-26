# Council round 1: what to show, what to hide, and integrity

Lens: STYLE.md section 4 (80 / 20, the "always in the main text" list) and section 10; META_PATTERNS.md (c); RESERVE.md rule
("hidden only if the conclusion is unchanged"). Read against `paper/main.tex` at da7d2e7 and NUMBERS.md (incl. Mismatches).
Line numbers are main.tex lines. Decisions: KEEP / SHORTEN / SUPP (move to supplement) / RESERVE / ADD / FIX (wording that
misleads). Proposed text follows the author's voice rules (no em dashes, plain names, one number per claim).

## Abstract (l. 31-39; 149 words)

| Paragraph / sentence | Decision | Reason | Proposed text or move |
|---|---|---|---|
| "Models of post-treatment glioma MRI face known challenges..." | KEEP | Sets up C1-C4 neutrally. | (cold reader wants the task named early; see round1_coldhostile) |
| "We built PRISM, a modular system ... measures the segmented tumour ..." | SHORTEN | "measures the segmented tumour" costs words that the integrity fixes below need; the image pathway already implies it. | "We built PRISM, a modular system that keeps image and treatment-timeline evidence in separate pathways, attaches a confidence to every scan and writes a report with a local language model." |
| "On MU-Glioma-Post, the timeline pathway ... 0.82 and the image pathway with 0.71." | KEEP | Timing baseline is on the always list whenever an image number is shown; it is here. 0.71 is an exploratory definition, but the audit sentence carries the exploratory word. | unchanged |
| "Fitted once and locked ... single-scan images reached 0.80 on UCSF-ALPTDG, about as high as when trained there." | **FIX (integrity)** | The abstract picks the flattering arm. PRISM's image pathway at UCSF (the one in Fig 2, the card, the conformal sets) is the change-feature model, 0.73, and the planned Q3 shows training at UCSF clearly better (0.86; +0.14, +0.03 to +0.26). "About as high as when trained there" is true only for the single-scan arm, an exploratory contrast (Mismatch 1). A reader would conclude the locked model is as good as a local one; it is not. | "Fitted once and locked, the models reached 0.77 on LUMIERE and the image pathway 0.73 on UCSF-ALPTDG, below a model trained there." |
| "An audit showed what each score rested on ..." | FIX | Both audits are exploratory (NUMBERS section 5); the abstract is where a reader decides what is evidence. | "An exploratory audit showed ..." |
| "Conformal sets for the combined score kept their coverage at all three centres" | FIX | "Kept their coverage" reads as a guarantee. UCSF is 0.783 against 0.78 with a CI of 0.68-0.87; the rule is met on the point estimate only. | "Conformal sets for the combined score met their pre-specified coverage at all three centres" |
| "... and reports passed a deterministic check against their records." | **ADD (always list)** | The faithfulness claim rests on a second evaluation after a seen failure (0 of 178 at LUMIERE). The header comment says mismatch 9 was fixed, but the text carries no disclosure. | "... and in a second evaluation every report passed a deterministic check against its record." |
| (missing) scope limit | ADD if words allow | STYLE 9 asks for the scope limit. With the text above the abstract is exactly 150 words, so the limit can only enter by cutting elsewhere (option: drop "On MU-Glioma-Post ... 0.71" to "On MU-Glioma-Post the timeline pathway reached 0.82" and add "no clinician has yet read the reports"). | Author's choice; flag it. |

Full proposed abstract (150 words, checked with `wc -w`): sentences 1-2 as above, then "On MU-Glioma-Post, the timeline pathway detected
the scan at which progression was called with an AUC of 0.82 and the image pathway with 0.71. Fitted once and locked, the
models reached 0.77 on LUMIERE and the image pathway 0.73 on UCSF-ALPTDG, below a model trained there. An exploratory audit
showed what each score rested on: the treatment timeline at MU, enhancing tumour volume at UCSF. Conformal sets for the
combined score met their pre-specified coverage at all three centres, and in a second evaluation every report passed a
deterministic check against its record."

## 1. Introduction

| Paragraph | Decision | Reason | Proposed text or move |
|---|---|---|---|
| "After surgery and chemoradiotherapy..." (l. 51) | KEEP | Its last two sentences set up the whole audit (date depends on when the patient was scanned). | unchanged |
| "Models for this task meet five challenges..." (l. 60) | KEEP, SHORTEN last sentence | The Shi / Yu sentence is context, not argument; one clause is enough. | "External tests address the second challenge and remain uncommon \citep{shi2025,yu2022}." (the "3 of 20" count to RESERVE / Discussion if wanted) |
| "We asked whether a system could..." (l. 73) | KEEP | The question. | unchanged |
| "PRISM is a modular system built for this ... plans written in advance." (l. 78) | FIX | (1) "plans written in advance" sits next to the confidence, whose agreement rule and card are post hoc; (2) "held at LUMIERE and UCSF" covers the timeline, which reached 0.56 at UCSF; (3) the report claim needs the second-evaluation word; (4) "kept their stated coverage" as in the abstract. | "...tested it on one development cohort and two external cohorts, with models fitted once and the external tests planned in advance." / "...models fitted there held at LUMIERE, and the image pathway at UCSF-ALPTDG." / "...met their pre-specified coverage at all three centres, and in a second evaluation the reports were faithful to their records." |

## 2. Methods

| Paragraph | Decision | Reason | Proposed text or move |
|---|---|---|---|
| "PRISM handles each scan in five modules..." (l. 94) | KEEP | Map of the paper. | unchanged |
| "The timeline pathway scores a scan..." (l. 102) | KEEP | The inputs are what the audit is about; a reader must see that visit index and RT dates are in. | unchanged |
| "The image pathway scores a scan from simple measurements..." (l. 111) | KEEP | Holds the disclosure that the pathway was defined after the planned model was seen to encode the schedule. This is the most important exploratory label in the paper; do not shorten it away. | Add after the last sentence: "At the external centres the combined score therefore contains one schedule input, the interval since the previous scan." (makes 3.3's UCSF interval finding unsurprising) |
| "Segmentation supplies these measurements..." (l. 124) | KEEP, SHORTEN | Honest after Mismatch 6 (cohort masks, not PRISM's network). The figure-rendering detail is supplement material. | Cut "From the same images and masks ... never sees an image." to "PRISM renders the report's figure from the same masks; the language model never sees an image." |
| "Each scan's confidence has three parts..." (l. 131) | KEEP, ADD one clause | Exploratory label for agreement rule and card is present. Missing: the conformal set comes from a model refitted on 70% of MU patients, not from the displayed combined score; at UCSF that model's AUC is 0.78 against 0.86 for the displayed score (NUMBERS 6, "cost of the split"). A reader assumes the set wraps the score they see. | After "...applied unchanged.": "The set therefore comes from a model fitted on the remaining 70%, which ranks scans slightly differently from the displayed score (Supplementary)." |
| "A local language model writes the report..." (l. 144) | KEEP | Two sentences, as decided. | unchanged |
| "PRISM was developed on MU-Glioma-Post..." (l. 152) | KEEP | Scan-2-only scope at UCSF is a scope limit. | unchanged |
| "The task is detection at the scan..." (l. 161) | KEEP | Intended use defined before its numbers. | Add: "LUMIERE and UCSF-ALPTDG are evaluated on all scans in their detection sets." (the reader otherwise assumes an intended-use filter there too) |
| "On MU-Glioma-Post, every model was evaluated by repeated..." (l. 174) | SHORTEN (answers OUTLINE open question: paragraph + Supp. figure, not a Results section) | Supports the design; the re-selection detail and the UCSF split are reviewer material. Keep one contrast (0.80 vs 0.72) because it is PRISM's own first evaluation and explains the design honestly. | "...from 1,000 patient-level bootstrap draws. In cohorts of this size one split can move an AUC by more than a change of model: PRISM's initial radiomics model reached 0.80 on one test split and averaged 0.72 over 500 splits of the same design (Supplementary Figure S1)." UCSF own split (0.45 vs 0.72) to Supp. S8 and RESERVE. |
| "For the external tests, each model was fitted once..." (l. 183) | KEEP | Locked design is the main strength. The grade-4-only training rows were a deviation from the plan (all MU detection scans); 0.768 vs 0.773, so RESERVE plus the supplement's deviations list is enough. | unchanged; RESERVE row 1 |
| "Analyses that were not planned are labelled exploratory..." (l. 190) | KEEP, ADD | On the always list. Incomplete: missing the LUMIERE images-alone and reduced-timeline-alone references, the single-scan locked-vs-trained comparison at UCSF, and both audits (MU timeline gain, UCSF enhancement). | "...the clinical-only, image-only and timeline-only models at LUMIERE, the single-scan comparison with models trained at UCSF-ALPTDG, the audits of what each score rests on, ..." |

## 3. Results

| Paragraph | Decision | Reason | Proposed text or move |
|---|---|---|---|
| 3.1 "In the intended use on MU-Glioma-Post, the timeline pathway..." (l. 202) | KEEP, FIX one phrase, ADD one clause | Timing baseline, clinical-alone, the planned NO-GO and the 120-day intended-use 0.60 are all here (always list). "Images added nothing measurable" is a verdict (STYLE 6); and STORY's "complicates the story" row (all gliomas, all scans: planned model +0.041, +0.006 to +0.081) is absent. The planned model's image block carries schedule inputs, so it does not contradict the claim, but a reader who finds it in Table S-x will ask why it was not mentioned. | "The combined score also reached 0.82, the same as the timeline alone." / after the planned-test sentence: "In all gliomas over all scans it gained 0.04 (0.01-0.08), through inputs that encode the scan schedule (Section 3.3)." Add "(within phases, Section 3.3)" after 0.82 so the across-phase number is not read as model skill. |
| 3.2 "Fitted once on MU-Glioma-Post and applied unchanged..." (l. 214) | FIX order, ADD labels | The heading's first numbers should be the pathways PRISM runs. At UCSF that is the image pathway with change, 0.73 (planned Q1, met); the 0.80 single-scan arm is a planned arm but not the system's pathway. LUMIERE 0.65 and 0.69 are exploratory and unlabelled. | "...the combined model reached 0.77 (0.68-0.86) on LUMIERE, and the image pathway reached 0.73 (0.60-0.84) on UCSF-ALPTDG, meeting its planned rule (Figure 2)." / "...images alone scored 0.65 and the reduced timeline alone 0.69 (both exploratory references)..." |
| 3.2 "At UCSF-ALPTDG, the locked single-scan image model was about as high..." (l. 222) | REORDER, SHORTEN | Q3 is the planned comparison and must come first; the single-scan arm second, with its exploratory label. The "three to six times narrower" mechanism is a suspected mechanism (STYLE 4: reserve). The closing transport-not-superiority sentence is exactly the author's line; keep. | "Training at UCSF-ALPTDG did better than the locked image pathway (0.86; difference 0.14, 0.03-0.26). The locked single-scan measurements, at 0.80 (0.69-0.89), were close to their UCSF-trained counterpart (0.83, exploratory), so the change inputs carried less well than the measurements of the scan itself. The reduced timeline transported least, at 0.56, because UCSF-ALPTDG records only the start of radiotherapy." Keep "We read these results as transport..." Mechanism to RESERVE row 2. |
| 3.3 "The audit shows that on MU the scores rest mainly..." (l. 236) | KEEP | The within-phase result is on the always list and is the paper's central diagnostic. Counts (56 of 62, 51 of 84) persuade. | Label: "The audit (exploratory) shows..." in the first sentence rather than mid-paragraph. |
| 3.3 "At UCSF-ALPTDG the scores rest on enhancement." (l. 245) | KEEP, ADD label, ADD within-category result | Exploratory, unlabelled. The UCSF image AUCs are the across-category number that could be read as image signal; the within-"increased enhancement" result is the analogue of the within-phase result and belongs in main text, explained (META 13: the author asked what 0.53-0.65 means). | "...(exploratory; Figure 3B). Among the 37 scans that UCSF rated as showing increased enhancement, the single-scan image model fell to 0.65 (0.44-0.84), so beyond that rating the measurements added little." Keep the interval sentence. |
| 3.3 "Each step of the image model's design raised its AUC..." (l. 254) | SHORTEN | Needed: it explains why the planned model was set aside and the pathway defined post hoc. Not needed: the sequence of numbers (Fig 3C carries it; META 13). "Each step raised" claims more than the middle step's unverified CI allows (Mismatch 8). | "Adding inputs to the image model raised its AUC on MU (exploratory; Figure 3C). The largest rise, to 0.81, came from the interval since the previous scan, a flag for whether there was one and the smallest volume counted from the end of radiotherapy; within a phase of care these three inputs added nothing ($-$0.01, $-$0.06 to $+$0.04), because they encode the scan schedule. They form the imaging block of the planned model, so PRISM's image pathway leaves them out." |
| 3.3 "Deep networks enter PRISM as segmenters..." (l. 262) | SHORTEN, FIX | "Enter PRISM as segmenters" overstates: PRISM's measurements come from masks supplied with each cohort, and PRISM's own SwinUNETR resegmentation was a sensitivity analysis that was not used (Mismatch 6). Resegmentation detail leaves the conclusion unchanged: RESERVE. Q4 is a planned "Yes" in Table 2, so one sentence on the direct-scoring networks stays. | "PRISM relies on automatic segmentation, through the masks supplied with each cohort. Networks fine-tuned to score scans directly scored above a permuted-label control at UCSF-ALPTDG (Table 2), but their scores followed enhancing volume (correlation about 0.8) and stayed below it, and at MU-Glioma-Post they did not separate the scans. Because the evidence behind a score differs by cohort and by situation, PRISM also has to say how far each score can be trusted." Resegmentation to RESERVE row 4. |
| 3.4 heading "The confidence keeps its coverage at all three centres" | FIX | Only the combined score's sets met S1; image pathway (LUMIERE) and timeline (UCSF) did not; conditional coverage fails in several cells. | "Conformal sets for the combined score meet their coverage at all three centres" |
| 3.4 "At the 80% level, the conformal sets of the combined score covered..." (l. 275) | KEEP | Discloses the UCSF lower bound and the per-pathway failures. Integrity item; keep both. Resolve the `\todo` with a supplement section number. | unchanged |
| 3.4 "When the two pathways disagreed on MU..." (l. 283) | KEEP first half; SUPP for the reduced design | "Disagreement works only on MU" is stated (l. 287); keep. The reduced design (D4) was chosen after S1-S4 were read and is untested; three sentences give a post hoc rescue more weight than the planned result and invite reading it as the system's flag. One sentence with the label is enough. | Replace l. 288-292 with: "A stricter rule chosen after these results, flagging a scan only when the pathways disagree and its set holds both outcomes, is described in Supplementary S-x (exploratory, untested on new data)." Numbers to RESERVE row 5. |
| 3.4 "For most scans the evidence behind any score is thin..." (l. 295) | KEEP, FIX denominator | Exploratory label present; the MU reversal of S4 is disclosed (contradicting result, always list). "249 MU scans with reports" uses a different set from the 146 detection scans and the 114 evaluated reports (Mismatch 14). | "Of the 249 grade 4 index scans at MU-Glioma-Post, 35 fell in..." |
| 3.5 "Every evaluation report written by the local model passed..." (l. 306) | KEEP; SUPP for the ladder | Second-evaluation disclosure and failure cause are here; keep both (always list). The seven-model ladder is development detail (report gets little space, STYLE 10 2026-10-25); its one useful fact is that a model that fits on one GPU is needed. | Replace l. 311-313 with: "The smallest open-weight model that passed in every cohort had 27 billion parameters and ran on one GPU (Supplementary S-x)." Ladder detail to RESERVE row 6. |

## 4. Discussion and Conclusion

| Paragraph | Decision | Reason | Proposed text or move |
|---|---|---|---|
| "PRISM gives the clinician separate image and treatment-timeline evidence..." (l. 319) | KEEP, ADD one clause | Answers the question. The locked models are a floor at UCSF (Q3); one clause stops "carries without refitting" from being read as "no need to refit". | After the UCSF sentence: "Training at UCSF-ALPTDG raised the image pathway further, so the locked results show transport, not the best a centre can reach." |
| "Because its modules are separate, PRISM runs where data are incomplete." (l. 327) | KEEP, FIX | "The combined score as a display beside both" contradicts Methods (l. 120: the combined score is one ridge model with both sets of inputs). | "...the timeline is added as a second pathway and a combined model is shown beside both, without changing the image model." |
| "Consider a scan eight weeks after radiotherapy..." (l. 334) | KEEP | The author asked for one scenario. 1 of 9 comes from the exploratory card; the pathway behaviour is stated as what the report "would" show, which is right. | "At MU-Glioma-Post, 1 of the 9 scans in this situation on the card (exploratory) was progression." |
| "Each of PRISM's components has been described before..." (l. 343) | KEEP, SHORTEN | Neutral; Christodoulou sentence is the decided one. Chen / Tikhonov clause can be one sentence. Resolve Tikhonov `\todo`. | unchanged except merge the last two clauses |
| "This study has limits." (l. 356) | KEEP, ADD two limits | Has the always-list limits (one centre, documented label, no clinician read, exploratory components, 120-day weak). Missing two that bound the confidence claim: the disagreement warning worked only at MU; UCSF coverage met on the point estimate. | Add: "The disagreement warning picked out less accurate scans only at MU-Glioma-Post, and at UCSF-ALPTDG the coverage interval reached below its threshold." |
| "The next step is to pool the rare situations..." (l. 367) | KEEP | Set-up, not apology (META 16). | unchanged |
| Conclusion | KEEP | Ends on the idea. | unchanged |

## Tables and figures

| Item | Decision | Reason | Proposed change |
|---|---|---|---|
| Table 1 | KEEP | Phase-of-care row carries the timing baseline's cause. Note (a) mixes the 120-day cohort with detection counts (Mismatch 7); clear enough. | none |
| Table 2 | KEEP, ADD | The planned-vs-exploratory ledger (always list). Q3 row should carry its number since the text may move: "+0.137 (+0.033 to +0.257)". S1 row: add "UCSF lower bound 0.68". The deviation (grade-4-only locked training rows) belongs in its note or the supplement. | as stated |
| Fig 2 caption | ADD | The UCSF combined bar (0.86) is the tallest locked bar and rests partly on the scan interval (exploratory, 3.3). Mark which UCSF image bar is the system's pathway. | "At UCSF-ALPTDG the image pathway is the model with change features; the combined score there includes the interval between the two scans." |
| Fig 3 caption | FIX | Panel B (UCSF audit) is exploratory too. | "All panels are exploratory." |
| Fig 4 title | FIX | "points to doubtful scans" holds at MU only. | "...and, at MU-Glioma-Post, points to doubtful scans." |
| Fig 5 caption | ADD | Second-evaluation word. | "...in the second evaluation (Section 3.5)." |

## Proposed new RESERVE.md rows

Also: several existing rows describe the old story (forward 0.635, "None beat the timing model", triage, calibration of the
120-day model). They are still true; re-word their answers to the detection framing when RESERVE.md is next edited.

| Likely question | Short answer | Where |
|---|---|---|
| 1. The UCSF plan said "all MU detection scans"; why were the locked models fitted on grade 4 rows? | A deviation, decided before UCSF labels were read; the all-glioma model gives 0.768 against 0.773 at LUMIERE and the same picture at UCSF. | UCSF_RESULTS.md Part A; supplement deviations |
| 2. Why did the change inputs transport worse to UCSF than single-scan measurements? | UCSF change between its two scans spans a range three to six times narrower than at MU; single-scan 0.80 vs change 0.73 (difference −0.07, −0.13 to −0.01). | UCSF_RESULTS.md contrasts |
| 3. Is the UCSF one-split evaluation trustworthy? | No single split is: UCSF's own train/test split gave a UCSF-trained timeline 0.45 against a median of 0.72 over 100 random splits (1st percentile); we used repeated CV. | Supp. S8; UCSF_RESULTS.md Part B |
| 4. Why not use PRISM's own segmentation for the measurements? | Pre-specified resegmentation with a BraTS 2021 SwinUNETR agreed with the MU masks (median ET Dice 0.80) and did not change detection (−0.016, −0.057 to +0.025), so the cohort masks were kept. | S14; RESEGMENTATION.md |
| 5. Is there a flag that works at all three centres? | Exploratory only: "disagree and set holds both outcomes" flags 12-27%; flagged error 0.52 / 0.54 / 0.38 vs 0.22 / 0.22 / 0.25 (UCSF difference CI includes 0); chosen after the planned results; untested on new data. | SYSTEM_RESULTS.md exploratory (3d20c41) |
| 6. Could a smaller report model do? | Same prompt and checker: 9B 368 / 406, 4B 306 / 406, 2B 21 / 406; only Qwen3.8-27B and gemma-4-31B pass everywhere (the latter 4.5 times slower). Smaller models mostly leave required content out; the 2B model also invents. | REPORT_V3_1.md ladder |
| 7. Did the first-evaluation report failure hide a deeper problem? | One design error (a "3" from the rater flag in no cited field); with the fix the original 178 pass (exploratory); v3 stays reported as 0 / 178. | REPORT_V3.md |
| 8. Does coverage hold within situations, or with Mondrian conformal? | Not uniformly: MU later post-RT 0.74, UCSF non-events 0.65; Mondrian breaks externally (0.65, 0.51). The marginal combined set is the planned claim. | SYSTEM_RESULTS.md S1 |
| 9. Is the conformal set built on the displayed score? | On a model refitted on 70% of MU patients: AUC 0.80 vs 0.82 (MU), 0.78 vs 0.77 (LUMIERE), 0.78 vs 0.86 (UCSF). | SYSTEM_RESULTS.md "cost of the split" |
| 10. Why is the UCSF combined score higher than the image pathway? | It holds the scan-1 to scan-2 interval, which is shorter before progression; the inverted interval alone gives 0.72. | UCSF_AUDIT.md intervals (exploratory) |
| 11. Is a UCSF-trained clinical model at 0.41 a reversed signal? | No: label permutation gives the same negative bias for small grouped CV; image arms under permutation average 0.40-0.46. | UCSF_RESULTS.md Part B control |
| 12. Overlap between UCSF-ALPTDG and UCSF-PDGM? | 59 grade 4 patients; excluding them, the locked deep arm G1 gives 0.778 and the margin over the control grows. | UCSF_RESULTS.md Part C |
| 13. Do images help where LUMIERE's rater did not flag the early post-RT window? | Exploratory: adding images to the reduced timeline gains +0.13 (+0.01 to +0.23) in those 150 scans. | DETECTION_TASK.md external |
| 14. And for 120-day risk, images vs timeline? | Equally weak where PRISM is meant to be used: about 0.62 each, 0.62 combined (exploratory). | STORY.md gaps filled |

## Integrity list (hiding or wording that would mislead)

1. **Abstract, UCSF "about as high as when trained there"** (l. 37): must change. It reports the exploratory single-scan
   contrast and hides the planned Q3 (+0.14 for the image pathway PRISM actually runs at UCSF). This is the one place where the
   current text could change what a reader concludes.
2. **Coverage at UCSF**: 0.783 vs 0.78, CI 0.68-0.87. Disclosed in 3.4 (keep); abstract, introduction and the 3.4 heading say
   "kept their coverage" without qualification. Use "met their pre-specified coverage"; add to Limits.
3. **Disagreement works only on MU**: disclosed in 3.4 and Table 2 (keep). Fig 4's title and the Discussion do not say it; the
   reduced design (D4) must stay labelled exploratory and must not read as the fix. Add to Limits; fix Fig 4 title.
4. **MU combined = timeline (0.82 = 0.82; −0.001)**: stated in 3.1 (keep, with the verdict wording softened). Discussion P2
   calls the combined score "a display", which contradicts Methods; fix.
5. **Reliability card and agreement rule post hoc**: labelled in Methods, 3.4, Table 2 note, Fig 4. The introduction's "plans
   written in advance" covers them by proximity; narrow it to the external tests. Scenario's 1 of 9 gets its label.
6. **Second evaluation of the reports**: disclosed in 3.5 and Table 2. Missing from the abstract, the introduction and Fig 5;
   add one phrase each.
7. **Unlabelled exploratory numbers**: LUMIERE images 0.65 and timeline 0.69 (3.2), the UCSF single-scan locked vs trained
   comparison (3.2), the UCSF enhancement audit (3.3, Fig 3B). Add the word; extend the Methods list (l. 190).
8. **"Deep networks enter PRISM as segmenters"**: PRISM did not use its own network; the measurements are the cohorts' masks.
   Rephrase so a reader does not credit PRISM with a segmentation result it did not produce.
9. **Conformal set vs displayed score**: the set comes from a model with a different AUC (UCSF 0.78 vs 0.86). One Methods
   clause; detail in the reserve. Hiding it entirely would mislead about what the set describes.
10. **UCSF combined 0.86**: it rests partly on the scan interval (stated, exploratory, 3.3). Fig 2 shows it as the tallest locked
    bar; the caption must say so, and Methods should note that the external combined score carries one schedule input.
11. **All gliomas, planned model +0.041 (CI above 0)**: the only result in the planned set where image inputs add with a CI
    above zero. Not contradictory (the block encodes the schedule), but one clause in 3.1 is safer than the reserve.
12. **Locked training-row deviation** (grade 4 rows vs plan's all scans): conclusion unchanged (0.768 vs 0.773); reserve and the
    supplement's deviation list are sufficient, but "plans committed before" in Methods must not imply no deviations.
13. **Safe to hide** (conclusion unchanged): resegmentation, the LLM size ladder, Mondrian and conditional coverage detail,
    the UCSF own-split result, the change-feature mechanism, UCSF-PDGM overlap, permutation bias, the D4 numbers.
