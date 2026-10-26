# Council round 2: editor's decisions

Applied to `paper/main.tex` on 2026-10-26 from the three round-2 reviews (`round2_numbers.md`, `round2_tone.md`,
`round2_showhide.md`) under the coordinator's rulings. Priority: numbers (WRONG / UNSOURCED / overstated) first, then
tone, then show/hide cuts toward the word budget. Everything is pending the author's approval; the backup is tag
`backup-before-council-2026-10-26`. LOCKED.md was not touched; the abstract remains a flagged proposal.

Status words: **applied** (as proposed, or with wording trimmed only), **modified** (the point taken, the text changed
differently, reason given), **rejected** (not applied, reason given), **no action** (the reviewer marked it OK).

## Coordinator rulings and how they were applied

1. **Abstract.** UCSF numbers kept and compressed: single scan 0.80, the image pathway with change 0.73, then "a model
   trained there did better" (0.86 stays in Section 3.2). Tone's sentence 2 and MU-sentence fixes used. 150 words
   (`wc -w`, flag excluded), `[PROPOSED, awaiting approval]` kept. "No clinician has yet read the reports" did not fit
   (it would have taken the abstract to 157 after every other cut); it stays in the Limits.
2. **"About the same when trained there"** kept in words for the single-scan model in 3.2; 0.83 dropped from the prose
   (Figure 2 carries the UCSF-trained bars).
3. **Card claim** corrected to the distribution by cohort: "35 of the 249 MU scans fell in a tested situation, most
   LUMIERE scans did, and every situation at UCSF had few cases", with the card's point stated as "this differs by
   cohort".
4. **Table 1 MU age.** The round-1 recomputation (median 62.5, IQR 53–70) was re-run read-only from
   `outputs/data/mu_cohort.csv`, first index scan per patient, grade 4: 126 patients, the same population as
   `TABLE1_COHORT.md` (which prints 62 [53–70] by rounding). 62.5 kept.
5. **Supplement references.** Every pointer to a section that does not exist is now `\todo{Supplementary section:
   <topic>}`; list below. `Supplementary Section~S23` was kept because `sec:S23` exists ("Intended use and censoring
   sensitivity") and holds the 120-day intended-use result; S8 and S19 likewise exist.
6. **Deep networks** reframed as in tone item 8: they learned from the images and found the evidence the measurements
   already hold; no "failed classifier" framing.
7. **Repeated phrases.** "rest on" now appears in the abstract, the 3.3 heading and the Figure 3 title only (3.2 "come
   from", 3.3 opener "depend mainly on", 2.3 "used" / "depends on"). "Fitted once on MU and applied unchanged" appears
   in the Introduction, the 2.2 definition of "locked", 2.3 and the Figure 2 caption; 3.2 opens "The locked combined
   model". "The scan at which progression was documented" stays in the Introduction, 2.2 and Table 1; the abstract
   uses "the scan documenting progression" (word count) and 3.1 "the progression scan".

### Supplement sections still to be written (now `\todo{Supplementary section: ...}` in main.tex)

| Pointer in main.tex | Where | Content expected |
|---|---|---|
| image pathway inputs and their harmonisation at LUMIERE and UCSF | 2.1 image pathway | the 27 inputs, the 19-input single-scan version, the three-volume LUMIERE variant, the one-scan UCSF history |
| system results | 2.1 conformal refit; 3.4 coverage; 3.4 stricter rule | conformal model vs displayed score; conditional coverage by situation; the reduced flag rule (3d20c41) |
| deviations from the plans | 2.3 locked fit | grade 4 training rows vs "all MU detection scans"; all-glioma sensitivity at LUMIERE; all-glioma models on all-glioma UCSF scans |
| second report evaluation and model comparison | 3.5 | v3.1 evaluation sets, the model-size ladder |

Also still open: the Tikhonov 2025 reference (`\todo{cite ...}` in the Discussion); the bootstrap CI for the middle
step of the image-model ladder (point difference +0.05 quoted without an interval; see RESERVE.md).

## Word count per section (main text; comments, tables, legends and back matter excluded)

Counted with the editor's script (LaTeX commands, citations and references stripped); the show/hide reviewer's
counter gave 4,380 for the same starting text, so the two columns are comparable only within this table.

| Section | Before | After |
|---|---|---|
| Abstract | 150 | 150 |
| Introduction | 556 | 494 |
| Methods 2.1 PRISM | 788 | 721 |
| Methods 2.2 Cohorts and the task | 317 | 303 |
| Methods 2.3 Evaluation | 328 | 337 |
| Results 3.1 | 155 | 151 |
| Results 3.2 | 221 | 193 |
| Results 3.3 | 431 | 397 |
| Results 3.4 | 328 | 335 |
| Results 3.5 | 175 | 155 |
| Discussion | 792 | 749 |
| Conclusion | 62 | 63 |
| **Total** | **4,153** | **3,898** |

2.3 and 3.4 grew slightly because integrity items added words (the UCSF all-glioma clause; the exploratory label on
the agreement rule; the card distribution by cohort). The total sits at the top of the 3,650–3,900 budget.

## Numbers and integrity review (30 items)

| # | Item | Status | Reason / what was done |
|---|---|---|---|
| 1 | Table 1 MU age 62.5 | rejected | Ruling 4: the recomputation uses the same 126-patient population as TABLE1_COHORT.md; 62 there is 62.5 rounded. |
| 2 | "for most scans this is little" | modified | Ruling 3: distribution by cohort (35 of 249 at MU; most LUMIERE scans tested; UCSF none). |
| 3 | Table 2 S2 "MU only" | applied | Result column now gives disagreement and the set holding both outcomes for all three cohorts; Met: "Both at MU-Glioma-Post; set at LUMIERE; none at UCSF-ALPTDG". S3 keeps "MU only (disagreement)". |
| 4 | "S23" dangling | rejected | `\label{sec:S23}` exists in supplement.tex ("Intended use and censoring sensitivity", the 120-day intended-use analysis); the reviewer's section list stopped at S20. |
| 5 | Reduced timeline "least ... because" | applied | "transferred worst of the pathways, at 0.56"; the approximated flag stated as a fact of the inputs (Section 2.1), not as the cause. |
| 6 | "each pathway added to the other" | applied | "the combined score was above either pathway alone ... (the gain over the timeline alone had an interval that included zero)". |
| 7 | Ladder middle step without CI | applied | "gave the image pathway of Section 3.1, 0.05 higher": point difference only, no interval invented; RESERVE row asks for the CI to be recomputed before submission. |
| 8 | All-glioma gain selective | applied | "In one secondary evaluation set, all scans of all gliomas, the planned model did gain 0.04 (Table 2), which may reflect ..."; both CIs (all scans; intended use) in the Table 2 note. |
| 9 | "all gliomas gave the same results" | applied | 2.3 and the Table 2 note: same AUC at LUMIERE; at UCSF the all-glioma models were tested on all-glioma scans (supplement todo). |
| 10 | "about as high as in cross-validation" | applied | Comparison dropped (giving 0.80 would collide with the UCSF single-scan 0.80; round 1 G3); RESERVE row holds 0.80 vs 0.77. |
| 11 | 0.88 "above the locked image models" | applied | "higher than the point estimates of the locked image models". |
| 12 | "every sentence" checked | applied | 2.1: "tests the report against that record" with the checker's scope in the next sentence; Introduction: "checked against the scan's record"; Figure 1: "tests its numbers, flags and confidence statements". |
| 13 | 3.4 heading and Fig 4 title | applied | "The conformal sets of the combined score meet ...". |
| 14 | "every MU result below" | applied | "unless stated MU results are for this population". |
| 15 | Image pathway exploratory label in 3.1 | applied | "the image pathway, whose definition is exploratory (Section 2.1)". Abstract unchanged (round 1 ruling 3). |
| 16 | Agreement rule label in 3.4 | applied | "(the agreement rule is exploratory)" in the paragraph's first sentence. |
| 17 | 0.77 three times | applied | Introduction: "transferred to LUMIERE" without the number. |
| 18 | 0 of 178 twice | applied | Table 2 S5: "First evaluation failed at LUMIERE"; the count stays in 3.5. |
| 19 | 0.603 in Table 2 | applied | "Both conditions met (Section 3.2)". |
| 20 | S1 row numbers | no action | OK. |
| 21 | "126 grade 4 patients" | applied | "(80 in the intended-use detection set)". |
| 22 | Card population in the scenario | applied | "(all grade 4 detection scans)". |
| 23 | S4 LUMIERE hedge | applied | "(descriptive; the intervals overlap)". |
| 24 | "In no analysis" | applied | "In the analyses of Sections 3.1 to 3.4". |
| 25 | 120-day 0.60 | no action | OK. |
| 26 | Table 2 title note wording | rejected | Optional; the note already says "Each rule"; the S2–S4 and S5–S7 caveats are in the table note. |
| 27 | LUMIERE row rule / result | applied | Rule "External AUC ≥ 0.65 (below: transport failure)"; result "AUC above 0.65 (Section 3.2); no transport failure". |
| 28 | Table 1 note b wording | applied | "patients with no index scan (no scan with a 120-day label)". |
| 29 | Fig 2 two image definitions | no action | OK. |
| 30 | Fig 4 dashed line | no action | OK. |
| C | "seven models" exploratory label | applied | "(exploratory comparison; ...)" in 3.5. |

## Tone review (28 items, 5 global observations, abstract proposal)

| # | Item | Status | Reason |
|---|---|---|---|
| 1 | Abstract sentence 2 | applied | "scores each MRI through separate treatment-timeline and image pathways, attaches a confidence to each score and explains it in a report from a local language model" ("post-treatment" dropped for the word count). |
| 2 | Abstract MU sentence | applied | "both pathways detected the scan documenting progression, the timeline pathway with an AUC of 0.82". |
| 3 | Intro P4 split | modified | Split into two paragraphs as proposed; the module sentences compressed (show/hide P4) and "whose every sentence is checked" replaced by "checked against the scan's record" (numbers 12). |
| 4 | 3.3 paragraph order | applied | MU audit → MU ladder → UCSF (with the deep networks merged in, show/hide) → bridge. |
| 5 | Abstract transfer sentence | modified | "the combined model"; the UCSF clause punctuated with commas; "against 0.86 when trained there" became "; a model trained there did better" (ruling 1). |
| 6 | UCSF combined score referenced before reported | applied | Sentence moved to 3.2 after the reduced timeline, labelled exploratory. |
| 7 | Intro P2 third challenge | modified | "Repeated cross-validation addresses the third challenge and external tests the second; ... 3 of 20 studies ..." applied; the Yu clause cut (show/hide; the no-accusation rule). RESERVE row added. |
| 8 | Deep networks reframed | applied | Ruling 6. |
| 9 | Abstract ending | applied | Kept; "pre-specified" → "planned", "a deterministic check" → "a check", "at all three centres" → "at every centre" for the word count; "for the combined score" kept (NUMBERS mismatch 13). |
| 10 | Combined score its own paragraph | applied | |
| 11 | Within-phase repetition | modified | CIs kept (the diagnostic) and the finding stated first: "Within a phase the images also gave about as much evidence as the timeline, 0.68 (0.58–0.77) against 0.64 (0.51–0.78)"; the previous sentence now reads "within a phase it gained". |
| 12 | Limits opener | applied | "This study has limits." deleted. |
| 13 | "added nothing" | applied | "did not raise it". |
| 14 | Conclusion | applied | |
| 15 | "close to the same model's cross-validated AUC" | modified | Superseded by numbers 10: the comparison is dropped rather than given without its number. |
| 16 | 2.1 P1 abstractions | applied | |
| 17 | "the task with which this work began" | applied | |
| 18 | 2.2 cohort paragraph ending | applied | |
| 19 | Locked-fit sentence | applied | Plus the UCSF all-glioma clause (numbers 9). |
| 20 | Card opener | modified | "(exploratory), and this differs by cohort" (ruling 3) instead of "most scans fall in situations with few cases", which is not true at LUMIERE (numbers 2). |
| 21 | 3.2 UCSF closer | applied | Deleted; the bridge follows item 6's sentence. |
| 22 | 3.5 last two sentences | applied | Swapped. |
| 23 | Intro P2 opening | applied | |
| 24 | Discussion P1 last sentence | applied | |
| 25 | "measure ... measures" | applied | "and enhancement is what PRISM's image pathway quantifies". |
| 26 | Christodoulou sentence | applied | 0.80 and the split design to RESERVE (row extended). |
| 27 | Intro reports clause | applied | |
| 28 | 120-day sentence placement | modified | The sentence stays in 3.1 (STYLE "always in the main text": intended-use 0.60 in the Results) but moves before the all-glioma sentence, so the transition now follows the pointer to 3.3; the 2.2 sentence is shortened without the number. |
| G1 | "rest on" | applied | See ruling 7. |
| G2 | the long scan phrase | applied | See ruling 7. |
| G3 | "fitted once ... unchanged" | applied | See ruling 7. |
| G4 | Two-idea paragraphs | applied | Through items 3, 6, 7, 10, 18, 28. |
| G5 | Intro timid without a number | modified | No number added: 0.82 would then appear in the abstract, Introduction and 3.1 (numbers 17 applies the same rule to 0.77). The claim is stated as transfer in words. |
| Abstract proposal | | modified | Adopted with ruling 1's "a model trained there did better" in place of 0.86 and three word-count substitutions (item 9). 150 words. |

## Show/hide review (50 decisions)

| # | Item | Status | Reason |
|---|---|---|---|
| 1 | Abstract UCSF clause to words | modified | Ruling 1: 0.80 and 0.73 kept, 0.86 to words; the scope limit did not fit. |
| 2 | Abstract rest keep | applied | |
| 3 | Intro P1 keep | applied | |
| 4 | Intro P2 one sentence per challenge; Yu cut | applied | |
| 5 | Intro P3 keep | applied | |
| 6 | Intro P4 stop re-listing modules | modified | Tone 3 keeps a compressed module sentence (the reader's first picture of the system); the results sentences follow as proposed. |
| 7 | 2.1 P1 keep | applied | With tone 16. |
| 8 | 2.1 timeline flag shorten | applied | |
| 9 | 2.1 image inputs shorten | applied | Pointer is a supplement todo. |
| 10 | 2.1 LUMIERE / UCSF harmonisation to supplement | applied | RESERVE row added; same todo pointer. |
| 11 | 2.1 masks keep | applied | |
| 12 | 2.1 confidence shorten | applied | Model-card citation moved to "reliability card"; the one-or-both-outcomes sentence compressed to a clause. |
| 13 | 2.1 report keep | applied | |
| 14 | 2.2 cut DUA and population sentences | applied | Population moved into the first sentence (tone 18). |
| 15 | 2.2 task definitions keep | applied | |
| 16 | 2.3 keep, trim appositive | applied | |
| 17 | 3.1 keep 0.71 with CI | applied | |
| 18 | 3.1 all-glioma CI to Table 2 | applied | With numbers 8. |
| 19 | 3.1 "What the images contribute" cut | applied | |
| 20 | 3.1 120-day keep | applied | |
| 21 | 3.2 clinical-alone numbers to Fig 2 | applied | |
| 22 | 3.2 images / timeline alone keep | applied | |
| 23 | 3.2 drop 0.83 | applied | Ruling 2. |
| 24 | 3.2 mechanism clause to RESERVE | applied | Row exists. |
| 25 | 3.2 closing two sentences keep | modified | Tone 21 deletes the summary sentence; the bridge stays. |
| 26 | 3.3 within-phase promote, drop CIs | modified | Promoted; CIs kept (tone 11; Fig 3A does not show the pathway AUCs). |
| 27 | 3.3 time since diagnosis 0.54 to RESERVE | applied | Row added. |
| 28 | 3.3 UCSF numbers keep | applied | |
| 29 | 3.3 deep networks merged | applied | Into the UCSF paragraph, reframed (ruling 6). |
| 30 | 3.3 "close to the timeline" cut | applied | |
| 31 | 3.4 P1 keep; informative sentence second | applied | |
| 32 | 3.4 difference CI to Table 2 | applied | |
| 33 | 3.4 stricter rule keep | applied | |
| 34 | 3.4 S4 sentence shorten | applied | With numbers 23. |
| 35 | 3.5 misses explanation to RESERVE | applied | Row exists. |
| 36 | 3.5 "220" to words | applied | |
| 37 | 3.5 "seven models" cut | applied | |
| 38 | 3.5 first evaluation keep | applied | |
| 39 | Discussion P1 shorten | applied | Sentences 2–4 compressed into one; UCSF transfer clause kept. |
| 40 | Discussion P2 keep | applied | |
| 41 | Discussion P3 keep | applied | Population label added (numbers 22). |
| 42 | Discussion P4 cut Tikhonov / Chen | modified | OUTLINE decision 4 keeps Tikhonov and Christodoulou as context; the 0.81 is dropped and the sentence shortened; the Tikhonov todo stays; RESERVE row added. |
| 43 | Limits "a quarter" to RESERVE | applied | Row added. |
| 44 | Limits interval width shorten | applied | |
| 45 | Limits always-list sentences keep | applied | |
| 46 | Future work and Conclusion keep | applied | Conclusion reworded (tone 14). |
| 47 | Table 2 row 1 all-glioma gain | applied | In the note, with the intended-use CI (numbers 8). |
| 48 | Table 2 S2 MU difference | applied | |
| 49 | Fig 2 caption keep | applied | |
| 50 | RESERVE two rows | applied | Plus seven more (see RESERVE.md). |

## Counts

Numbers 30: 22 applied, 1 modified, 3 rejected, 4 no action. Tone 34 (28 + G1–G5 + abstract proposal): 25 applied,
9 modified, 0 rejected. Show/hide 50: 45 applied, 5 modified, 0 rejected.
**Total 114: 92 applied, 15 modified, 3 rejected, 4 no action.**

## Integrity check after the cuts

Every item on STYLE.md's "always in the main text" list is still present: intended-use 120-day 0.60 (3.1, Limits);
timeline-alone baselines (3.1; 3.2 LUMIERE 0.69 and UCSF 0.56; 3.3 enhancing volume 0.88); within-phase result (3.3,
now stated as the finding); planned vs exploratory (2.3 list; labels in 3.1, 3.2, 3.3, 3.4, 3.5; Table 2); scope
limits (Limits paragraph, including "no clinician has yet read the reports"); contradicting results (combined =
timeline on MU; S4 reversal; UCSF coverage interval; disagreement at MU only; first report failure; better when
trained at UCSF). No RANO, no "published", no em dashes, British -ise.

## Open for the author

- The proposed abstract (150 words) and all of the above.
- The four supplement sections named by `\todo{Supplementary section: ...}` (table above).
- The middle-step ladder CI (recompute before submission) and the Tikhonov reference.
- OUTLINE decision 16 (this round) is pending, like decision 15.
