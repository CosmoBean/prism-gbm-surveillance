# Council round 2: show and hide, the balance after round 1

Lens: STYLE.md sections 4 (80 / 20, the "always" list), 5 (one number per claim) and 10; META_PATTERNS (c) 11-14;
RESERVE.md rule. Read against `paper/main.tex` at dcfd00a. Round 1 made the text honest; this round asks whether a
reader can still follow the argument through the caveats. Decisions: KEEP / CUT / MOVE (to supplement or RESERVE) /
SHORTEN / ADD. Nothing proposed below changes what a reader concludes; every moved number already has, or gets, a
RESERVE row. Line numbers are main.tex lines. Word counts exclude comments, tables, legends and back matter.

## The verdict in one paragraph

The main text is 4,380 words against a target of 3,500-4,000. It is not cluttered with caveats: the integrity
disclosures from round 1 are each one clause and sit where they belong. What clutters it is **numbers and
mechanism**: 3.1 has seven AUCs in one paragraph, 3.2 six, 3.3 fourteen; four of the Results subsections give a
contrast as two levels *and* a difference with its CI; and Methods 2.1 describes inputs cohort by cohort at a level
that only the supplement needs. The Discussion repeats the Results in words. Nothing that sells the system is
missing, but two things are buried: that the conformal set is *informative* (one outcome for most scans) is a
subordinate clause in 3.4, and the within-phase finding that images give as much evidence as the timeline, the one
result that answers the author's "do not frame imaging as worthless", is the last clause of 3.3's first paragraph.

## Word budget

| Section | Now | Target | Main cuts |
|---|---|---|---|
| Abstract | 152 | 150 | three UCSF numbers to words (author's choice; see below) |
| Introduction | 560 | 450 | P2 to one sentence per challenge; P4 stops re-listing the modules |
| Methods 2.1 PRISM | 790 | 620 | per-cohort input detail to supplement; timeline flag; card wording |
| Methods 2.2 Cohorts | 320 | 290 | duplicates of Table 1 |
| Methods 2.3 Evaluation | 325 | 300 | tighten; the exploratory list stays |
| Results 3.1 | 155 | 140 | CIs off non-headline numbers |
| Results 3.2 | 220 | 180 | mechanism clause; clinical-alone numbers; 0.83 |
| Results 3.3 | 430 | 360 | four paragraphs to three; time-since-diagnosis 0.54; redundant CIs |
| Results 3.4 | 325 | 290 | difference-with-CI duplicates; card paragraph tightened |
| Results 3.5 | 175 | 130 | misses explanation and "seven models" to RESERVE/supplement |
| Discussion | 800 | 680 | P1 stops restating 3.2-3.3; literature to one paragraph of four sentences; limits trimmed |
| Conclusion | 62 | 60 | unchanged |
| **Total** | **4,380** | **3,650** | |

## Abstract (l. 31-41)

| Text | Decision | Reason / replacement |
|---|---|---|
| "on UCSF-ALPTDG, single-scan measurements reached 0.80 and the image pathway with change from the previous scan 0.73, against 0.86 when trained there" | SHORTEN (author's call; ruling 1 chose the numbers) | Five AUCs in an abstract is the pattern the author rejected on 2026-10-23. Integrity needs only "trained there did better". "Fitted once and applied unchanged, the models reached 0.77 on LUMIERE, and the image measurements transferred to UCSF-ALPTDG, where a model trained there did better." (saves 14 words; spend them on the scope limit round 1 could not fit: "No clinician has yet read the reports.") |
| the rest | KEEP | Two numbers remain (0.82, 0.77), the audit, the coverage, the one-revision disclosure. |

## 1. Introduction (l. 53-90)

| Text | Decision | Reason / replacement |
|---|---|---|
| P1 | KEEP | Sets up the schedule effect; 117 words. |
| P2 "Models for this task meet five challenges..." (199 words) | SHORTEN to ~130 | Each challenge has a mechanism clause the Methods repeat. One sentence each: "First, most public surveillance datasets hold images but few treatment dates. Second, centres document progression differently, from dated clinical decisions to expert ratings of each scan. Third, cohorts are small, and one test split can move an AUC by more than a change of model \citep{an2021,varoquaux2018}. Fourth, the hardest situations, early after radiotherapy or when enhancement grows, hold few cases in any cohort. Fifth, segmented volumes are noisy and records often cannot leave the hospital, so the clinician must see what was measured, in a report written inside it." Keep the Shi 3 of 20 sentence; CUT the Yu clause ("deep learning models ... usually lose some accuracy"), which is the accusation-of-the-field register the author ruled out on 10-26. |
| P3 the question | KEEP | |
| P4 "PRISM is a modular system built for this..." (192 words) | SHORTEN to ~120 | Sentences 3-4 ("It scores each scan through two pathways ... checked against the scan's record") list the five modules; 2.1 and Fig 1 do this. Keep sentence 1-2, then go straight to what was found: "On MU both pathways detected the scan at which progression was documented; the models fitted there reached 0.77 at LUMIERE, and the image measurements transferred to UCSF. An audit showed ... The conformal sets ... and after one revision the reports were faithful to their records." |

## 2. Methods (l. 98-206)

| Text | Decision | Reason / replacement |
|---|---|---|
| 2.1 P1 module map | KEEP | 87 words; the reader's map. |
| 2.1 timeline pathway: "At LUMIERE the flag is the rater's note ...; at UCSF it is approximated from the start of radiotherapy." | SHORTEN | The reader needs only that the flag is weaker at UCSF (it explains 0.56 in 3.2). "The flag comes from the rater's note at LUMIERE and is approximated from the start of radiotherapy at UCSF." Full definitions in the supplement. |
| 2.1 image pathway: "the log volumes of six tumour compartments, including enhancing tumour, necrosis, the surrounding FLAIR hyperintensity and the resection cavity, with shape and relative intensity features; the log ratio ...; and the ratio ... history" | SHORTEN | A 27-input inventory is supplement material. "On MU it uses 27 inputs: volumes, shape and relative intensity of the segmented compartments at the scan, their change from the previous scan, and the enhancing and total volumes relative to the smallest in the patient's history (Supplementary Table S-x)." |
| 2.1 "At LUMIERE, whose masks have three labels, the pathway uses three volumes and their change ..., and at UCSF the history is the one earlier scan" | MOVE to supplement | Harmonisation detail; 2.2 already says UCSF has one pair. Keep "It holds no dates, intervals or treatment flags" and the exploratory disclosure and the combined-score definition (integrity 10): all three stay. |
| 2.1 masks paragraph | KEEP | 52 words; ruling 6. |
| 2.1 confidence (244 words) | SHORTEN to ~190 | Keep the 70 % refit clause (integrity 9), the agreement rule, the tier thresholds (needed to read Fig 4C), and the exploratory label. CUT "in the spirit of a model card \citep{mitchell2019}" (the citation can sit on "reliability card" at first mention) and "It holds one outcome when the score is clear and both outcomes when it is not" (said again in the next clause as "should contain the true outcome"). |
| 2.1 report | KEEP | Two sentences, as decided. |
| 2.2 "UCSF was obtained under a data use agreement. The primary population in every cohort is grade 4 glioma." | CUT | Both are in Table 1 (Access row; caption). |
| 2.2 task definitions | KEEP | Negatives per cohort are needed to read every AUC. |
| 2.3 all three paragraphs | KEEP | Split-variance paragraph per decision 14; the exploratory list is the always-list item; the deviation clause is integrity 12. Trim only "progression and non-progression scans from every phase of care" (l. 194-195), which repeats "all grade 4 detection scans". |

## 3. Results (l. 214-318)

| Text | Decision | Reason / replacement |
|---|---|---|
| 3.1 "and the image pathway with 0.71 (0.63--0.78)" | KEEP | Headline pair carries its intervals (STYLE 5). |
| 3.1 "Over all scans of all gliomas the planned model did gain 0.04 (0.01--0.08), through image inputs that encode the scan schedule" | SHORTEN | Integrity 11 wants the fact, not the CI in the prose: "gained 0.04 over all scans of all gliomas (Table 2), through image inputs that encode the scan schedule". Put the CI in Table 2 row 1 or its note. |
| 3.1 "What the images contribute on their own is examined within phases of care in Section 3.3." | CUT | The previous clause already points to 3.3; the last sentence is the bridge. |
| 3.1 120-day sentence | KEEP | Always list (intended-use 0.60). |
| 3.2 "Clinical data alone stayed close to chance in all three cohorts (0.55 at LUMIERE, exploratory, and 0.50 at UCSF)" | SHORTEN | "Clinical data alone stayed close to chance in all three cohorts (Figure 2)." Two numbers fewer; Fig 2 shows them. |
| 3.2 "images alone scored 0.65 and the reduced timeline alone 0.69 (both exploratory)" | KEEP | Timeline-alone is the strongest-baseline rule; images-alone is claim C1. |
| 3.2 "while the single-scan model scored about the same when trained there (0.83, exploratory)" | SHORTEN | Drop 0.83; "about the same" is the finding and Fig 2 has the bar. |
| 3.2 "which is consistent with the change between the two UCSF scans spanning a much narrower range than at MU" | MOVE to RESERVE (row exists) | A suspected mechanism (STYLE 4 reserve list). Sentence ends at "the measurements of the scan itself." |
| 3.2 closing two sentences | KEEP | The author's transfer-not-superiority line and the bridge. |
| 3.3 P1 "within a phase, images alone reached 0.68 (0.58--0.77) and the timeline 0.64 (0.51--0.78), so within a phase the images gave about as much evidence as the timeline" | SHORTEN and PROMOTE | Drop both CIs (Fig 3A). Make it its own sentence opening with the finding: "Within a phase of care the images gave about as much evidence as the timeline, 0.68 against 0.64 (Figure 3A)." This is the sentence that answers "images are not worthless"; it should not be a trailing clause. |
| 3.3 P2 "Time since diagnosis, which separates the classes at MU, gave 0.54 at UCSF." | MOVE to RESERVE (new row) | A fourth number in the paragraph; conclusion unchanged without it. |
| 3.3 P2 "Enhancing tumour volume alone ... 0.88 (0.79--0.95)"; "27 of the 29"; "median of 7 days"; "0.65 (0.44--0.84)" | KEEP | 0.88 is the baseline (always list); 27 of 29 and 7 days are the concrete counts that persuade; 0.65 is the within-category diagnostic (ruling 2). Drop the CI on 0.65 only if the author wants one number per sentence; Fig 3B can carry it. |
| 3.3 P4 deep networks (67 words) | MERGE | Four paragraphs become three: the Q4 sentence joins the end of the UCSF paragraph ("Deep networks fine-tuned to score UCSF scans directly learned above a permuted-label control (Table 2), but their scores tracked enhancing volume and stayed below it; on MU they did not meet the planned gain."). The bridge sentence ("Because the evidence behind a score differs ...") closes the ladder paragraph. |
| 3.3 P3 ladder "close to the timeline" | CUT two words | 0.81 stands on its own; the reader has 0.82 from 3.1. |
| 3.4 P1 | KEEP | Coverage range, threshold, UCSF interval, the per-pathway shortfalls: integrity 2, all one clause each. ADD emphasis by moving "Most sets were informative, holding a single outcome for 62 % to 75 % of scans" to the second sentence, before the UCSF caveat: capability, then caveat (STYLE 6). |
| 3.4 P2 "(difference 0.31, 0.18--0.43)" | MOVE to Table 2 row S2 | "0.90 where they agreed and 0.59 where they disagreed" is the contrast readers remember; the difference and CI duplicate it. Table 2 S2 currently points back to the text, so one of them must hold the number: the table. |
| 3.4 P2 stricter-rule sentence | KEEP | Ruling 4, one sentence. |
| 3.4 P3 "At LUMIERE scans in tested situations had lower error than scans with few cases; at MU the order was reversed, because ..." | SHORTEN | Contradicting result, always list, but Table 2 S4 holds the numbers. "Tested situations had lower error than few-case situations at LUMIERE but not at MU, where the few-case scans were mostly easy non-progression scans early after radiotherapy (Table 2)." |
| 3.5 "both misses were changes in enhancing volume from a previous value of zero" | MOVE to RESERVE (row exists) | Explanation of two misses out of 30; the count is enough. |
| 3.5 "The reports stated the evidence tier for all 220 scans in situations with few or no cases" | SHORTEN | "stated the evidence tier wherever the card had few or no cases (Table 2)". 220 is the fourth MU-related denominator in the paper. |
| 3.5 "Of the seven open-weight models we compared" | CUT four words | "The smallest open-weight model that passed in every cohort had 27 billion parameters and ran on one GPU (Supplementary S25)." |
| 3.5 first-evaluation sentence | KEEP | Always list; already one sentence. |

## 4. Discussion (l. 324-387)

| Text | Decision | Reason / replacement |
|---|---|---|
| P1 sentences 2-4 ("At the development centre the timeline provided ... Training at UCSF raised the image pathway further ...") | SHORTEN | They restate 3.2-3.3 in words. Keep sentence 1 (the answer), the UCSF "transfer rather than the best a centre can reach" clause (integrity, ruling 1), and the last sentence. Target 90 words. |
| P2 modules | KEEP | Sells the design; 94 words. |
| P3 scenario | KEEP | Author's request; the one place the reader sees the system act. |
| P4 literature (157 words) | SHORTEN to ~110 | Sentence 2 cites four components in one sentence; keep. CUT the Tikhonov/Chen sentence ("On LUMIERE, a classifier of four response categories ... both address other labels"): the reference is unverified and "other labels" adds nothing to the argument. Christodoulou and Jabal stay (decision 4). |
| P5 limits "and a quarter of the non-progression scans there show no enhancement" | MOVE to RESERVE (new row) | A diagnostic detail; the limit is already stated by "agrees closely with an enhancement call". |
| P5 "Subgroups are small; UCSF contributes 29 progression scans, and its intervals are 0.15 to 0.25 wide." | SHORTEN | "Subgroups are small, and UCSF contributes 29 progression scans." The interval width is visible in 3.2. |
| P5 exploratory list, coverage and disagreement sentence, checker sentence, 120-day sentence | KEEP | All always-list items, each once. |
| P6 future work, Conclusion | KEEP | |

## Tables, figures, RESERVE

| Item | Decision |
|---|---|
| Table 2 row 1 | ADD the all-glioma gain "+0.041 (+0.006 to +0.081)" in a second line or the note (receives the CI cut from 3.1). |
| Table 2 row S2 | ADD "MU-Glioma-Post +0.31 (+0.18 to +0.43)" (receives the CI cut from 3.4). |
| Fig 2 caption | KEEP; it now carries the UCSF clinical-alone, 0.83 and interval facts the prose drops. |
| RESERVE.md | ADD two rows: (1) "Does the MU-type timing signal exist at UCSF?" Time since diagnosis gave 0.54 at UCSF (UCSF_AUDIT.md). (2) "How clean is the UCSF negative set?" A quarter of non-progression scans show no enhancement (UCSF_AUDIT.md). Existing rows cover the change-range mechanism and the two perturbation misses. |

## Integrity check on the cuts

Every always-list item is still in the main text after the cuts: intended-use 0.60 (3.1, Discussion); timeline-alone
baselines (3.1, 3.2 LUMIERE 0.69, 3.2 UCSF 0.56, 3.3 UCSF enhancing volume 0.88); within-phase result (3.3, now
promoted); planned vs exploratory (2.3 list, labels in place, Table 2); scope limits (Discussion P5); contradicting
results (MU combined = timeline, S4 reversal, coverage interval at UCSF, disagreement at MU only, first report
failure, Q3 better when trained). Nothing moved out would change a reader's conclusion; each has a RESERVE row.
