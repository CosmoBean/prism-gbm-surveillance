# Council round 1: editor's decisions

Applied to `paper/main.tex` on 2026-10-26 from the three reviews (`round1_tone.md`, `round1_showhide.md`,
`round1_coldhostile.md`) under the coordinator's rulings 1–10. Everything here is pending the author's approval; the
backup is tag `backup-before-council-2026-10-26`. LOCKED.md was not touched (the abstract remains a flagged proposal).

Status words: **applied** (as proposed, or with wording trimmed only), **modified** (the point taken, the text changed
differently, reason given), **rejected** (not applied, reason given).

## Coordinator rulings (how conflicts were settled)

1. UCSF in abstract and 3.2: both planned image models (single scan 0.80; with change 0.73, the system's pathway);
   UCSF-trained 0.86 with change (Q3), 0.83 single scan; transfer claimed, not best performance.
2. UCSF label: 3.3 states that the calls rest largely on enhancement; enhancing volume alone (0.88) is the simple
   baseline; within-enhancement 0.65 as one clause; Discussion moderate.
3. Capabilities first; abstract gets no "exploratory" or within-phase numbers but must not misstate; novelty as
   "we are not aware of a system that combines them".
4. Coverage "met the pre-specified threshold" (point estimates); UCSF interval in 3.4 and Limits; disagreement on MU
   only in 3.4, Fig 4, Limits; stricter rule one labelled sentence.
5. Faithfulness disclosed as after one revision wherever claimed; size ladder one sentence.
6. Measurements from the cohorts' masks; resegmentation to RESERVE; one sentence on UCSF Q4.
7. Combined score = one ridge model on both input sets everywhere; conformal model refitted on 70% of MU patients.
8. Tone list applied unless in conflict; no "carry"; no colon reveals or closers; full names then short (MU, UCSF).
9. Table 1 age and sex verified.
10. Split variance one paragraph in 2.3; OUTLINE decision 14, pending author.

## Table 1 verification (ruling 9)

Recomputed read-only from `outputs/data/mu_cohort.csv` and `lumiere_cohort.csv` (first index scan per patient):
MU grade 4, 126 patients: age median 62.5 (IQR 53.0–69.75), male 66 (52%); LUMIERE, 61 patients: age 62.0 (53.0–70.0),
male 32 (52%). The LUMIERE row is correct and the match with MU is a coincidence; the MU median was 62.5, printed as
62 by rounding, and is now 62.5. Note (a) now says MU age is at diagnosis and LUMIERE age at surgery. For the author:
the detection sets differ (MU intended use, 80 patients: age 60.5, IQR 52.75–68.0, 40 male; LUMIERE detection, 79
patients: 62.0, 53.5–69.5, 40 male); Table 1 keeps the 120-day cohort characteristics, as its note states.

## Tone review (40 items + 5 observations)

| # | Item | Status | Reason |
|---|---|---|---|
| 1 | 3.1 images verdict | applied | |
| 2 | Abstract first sentence | modified | Shortened further for the 150-word limit; same plain list, no colon. |
| 3 | Abstract audit sentence | applied | "mainly" kept; "that" dropped for word count. |
| 4 | 3.3 schedule sentence | applied | Counts left in Table 1. |
| 5 | 3.4 card opener | applied | |
| 6 | 3.3 UCSF interpretation | modified | Ruling 2: "largely measure agreement ... which is what PRISM's image pathway measures"; card clause dropped. |
| 7 | 3.2 transport reading | modified | Ruling 1: "PRISM's measurements transfer ... a model trained at the centre can do better". |
| 8 | Conclusion | applied | |
| 9 | Discussion P1 | applied | Plus the ruling-1 clause on UCSF training. |
| 10 | LUMIERE model's MU score | modified | Number dropped ("about as high as in cross-validation on MU") so 0.80 means only UCSF single scan. |
| 11 | Disagreement paragraph | applied | Opens on the capability (ruling 3). |
| 12 | Coverage sentence | applied | Range 0.78–0.87; UCSF interval follows (ruling 4). |
| 13 | Card counts | applied | |
| 14 | Tier and error sentence | applied | |
| 15 | 3.4 closer | applied | |
| 16 | Ladder numbers | applied | Merged with show/hide shortening. |
| 17 | Deep networks on MU | applied | Inside the single Q4 sentence (ruling 6). |
| 18 | Intro external tests | applied | |
| 19 | Training at UCSF | modified | Rewritten in the ruling-1 order (single scan, pathway, then Q3). |
| 20 | LUMIERE complementary | applied | Exploratory label added. |
| 21 | Single-scan "high" | modified | Superseded by the ruling-1 paragraph. |
| 22 | 3.1 cohort counts | applied | Count moved to the opening parenthesis with Table 1 pointer. |
| 23 | Within-phase gain | modified | Order fixed, but the within-phase estimate keeps its CI instead of "gained nothing" (it is the diagnostic). |
| 24 | Methods first evaluation | applied | |
| 25 | Diagnostics colon | applied | |
| 26 | Abstract number count | applied | 0.71 dropped ("above the image pathway"); ruling 1 still needs 0.80, 0.73, 0.86. |
| 27 | Intro claim with numbers | modified | 0.77 given; UCSF stated as transfer of the image measurements without the single flattering 0.80 (ruling 1). |
| 28 | 3.5 model comparison | modified | Ruling 5: one size-ladder sentence (27 billion parameters, one GPU). |
| 29 | 3.5 pass counts | applied | Short names after first-use definition. |
| 30 | Fig 4 title | modified | "The conformal sets meet their coverage threshold, and at MU-Glioma-Post disagreement marks the less accurate scans" (ruling 4). |
| 31 | Jabal sentence | applied | |
| 32 | Limits last sentence | applied | |
| 33 | Intro P1 closer | applied | |
| 34 | Within-phase images | applied | |
| 35 | Fifth challenge | applied | |
| 36 | Change range | applied | |
| 37 | 3.3 opener full names | modified | Ruling 8: full names defined once in the Introduction, short names after. |
| 38 | Ladder opener | modified | Merged with show/hide ("Adding inputs ..."), short name. |
| 39 | 3.2 closer | applied | |
| 40 | Report figure clause | applied | |
| G1 | "carry" tic | applied | No "carry" left in the prose. |
| G2 | Cohort names | applied | Full names in abstract, first Introduction use, tables and captions; MU and UCSF elsewhere. |
| G3 | 0.80 / 0.82 collisions | applied | Dice to RESERVE; LUMIERE MU-CV number dropped; coverage as a range. |
| G4 | Colon reveals and closers | applied | Remaining colons introduce definitions or lists only. |
| G5 | Timid where strongest | applied | Capability sentence first in 3.1, 3.2, 3.4, intro claim. |

## Show/hide and integrity review

| Item | Status | Reason |
|---|---|---|
| Abstract S1 keep | modified | Tone #2 rewrite. |
| Abstract S2 shorten | modified | Shortened and the task added (cold reader 1). |
| Abstract MU sentence keep | modified | 0.71 dropped (tone #26). |
| Abstract UCSF FIX | modified | Ruling 1: both models and 0.86 when trained there, instead of "0.73 ... below a model trained there" alone. |
| Abstract "exploratory audit" | rejected | Ruling 3: no exploratory hedge in the abstract; the audit is stated as what the scores rested on. |
| Abstract coverage | applied | "met their pre-specified coverage". |
| Abstract reports | applied | "after one revision". |
| Abstract scope limit | rejected | No words left at 150; limits are in the Discussion. |
| Intro P1 keep | applied | With tone #33. |
| Intro P2 shorten Shi/Yu | modified | Tone #18 (neutral, no "uncommon") kept both facts. |
| Intro P3 keep | applied | "carry" → "transfer". |
| Intro P4 fix | applied | External tests planned in advance; LUMIERE and image transfer; coverage met; one revision. |
| 2.1 P1 keep | modified | "each answering one of the challenges" dropped (cold reader 13). |
| 2.1 timeline keep | modified | Clause naming the clinical-only reference added (cold reader 4). |
| 2.1 schedule input at external centres | applied | Plus ruling 7 definition of the combined score. |
| 2.1 segmentation shorten | applied | Ruling 6 wording. |
| 2.1 conformal 70% clause | applied | Ruling 7; pointer to a supplement section still to be written. |
| 2.1 report keep | applied | |
| 2.2 cohorts keep | applied | "locked" defined here. |
| 2.2 add LUMIERE/UCSF all scans | applied | |
| 2.3 split variance shorten | applied | Ruling 10; UCSF own split to RESERVE. |
| 2.3 locked keep | modified | Deviation clause added (integrity 12). |
| 2.3 exploratory list | applied | |
| 3.1 fix and add | applied | Verdict softened; all-glioma +0.04 clause; within-phase pointer. |
| 3.2 P1 order and labels | modified | LUMIERE paragraph first, UCSF its own paragraph led by both planned models (ruling 1); exploratory labels added. |
| 3.2 P2 reorder | modified | Ruling 1 order; mechanism kept as one clause without the 3–6× number (number to RESERVE). |
| 3.3 exploratory label first | applied | |
| 3.3 UCSF within-category | applied | Ruling 2. |
| 3.3 ladder shorten | applied | |
| 3.3 deep networks | modified | Ruling 6: one Q4 sentence; the "relies on masks" sentence is in Methods 2.1. |
| 3.4 heading | modified | "The conformal sets meet their coverage threshold at all three centres". |
| 3.4 coverage keep, resolve todo | modified | Kept; the \todo stays because the supplement has no system-results section yet (S24 placeholder). |
| 3.4 reduced design to one sentence | applied | Ruling 4. |
| 3.4 card denominator 249 | rejected | Superseded: tone #13 removes the 249 / 35 sentence. |
| 3.5 ladder to one sentence | applied | Ruling 5; S25 placeholder for the supplement. |
| Discussion P1 clause | applied | |
| Discussion P2 "display" fix | applied | Ruling 7. |
| Discussion scenario label | applied | "as an illustration", "(exploratory)". |
| Discussion literature | modified | Novelty wording per ruling 3; the Tikhonov \todo remains (no verified reference in refs.bib). |
| Limits two additions | applied | |
| Future work keep | applied | |
| Conclusion keep | modified | Tone #8 rewrite. |
| Table 1 keep | modified | MU age corrected to 62.5; age-origin note. |
| Table 2 add Q3 number, S1 lower bound | modified | Deviation added to the note; numbers not repeated (STYLE 5, once per number; both are in the text). |
| Fig 2 caption | applied | |
| Fig 3 caption | applied | |
| Fig 4 title | applied | See tone #30. |
| Fig 5 caption | applied | |
| RESERVE rows 1–14 | applied | Added; two more (split SD; perturbation misses); 120-day rows reworded to the detection framing. |
| Integrity 1 (UCSF abstract) | applied | Ruling 1. |
| Integrity 2 (coverage wording) | applied | |
| Integrity 3 (disagreement MU only) | applied | |
| Integrity 4 (combined = timeline; "display") | applied | |
| Integrity 5 (post hoc card; intro "plans") | applied | |
| Integrity 6 (second evaluation everywhere) | applied | |
| Integrity 7 (unlabelled exploratory numbers) | applied | |
| Integrity 8 (segmenters) | applied | |
| Integrity 9 (conformal model) | applied | |
| Integrity 10 (UCSF combined interval) | applied | |
| Integrity 11 (all-glioma +0.041) | applied | |
| Integrity 12 (training-row deviation) | applied | |
| Integrity 13 (safe to hide list) | applied | All in RESERVE. |

## Cold reader

| Item | Status | Reason |
|---|---|---|
| 1 Task late | applied | Task in the abstract's second sentence. |
| 2 "called" odd | applied | "documented" throughout. |
| 3 "locked" unexplained | applied | Abstract says "fitted once and applied unchanged"; 2.2 defines locked. |
| 4 Timeline vs clinical | applied | 2.1 names the clinical-only reference. |
| 5 Too many variant names | modified | Fewer variants named in prose; no glossary added. |
| 6 Planned vs exploratory map | rejected | Table 2 and the 2.3 list do this. |
| 7 "situation" undefined in Intro | rejected | Used in its plain sense there; defined in 2.1. |
| 8 Why the pathway stops at step 2 | applied | Last ladder sentence says why. |
| 9 "same LUMIERE model" | applied | |
| 10 Model names | rejected | Identifiers checked against REPORT_V3.md / NUMBERS.md; journal readers expect them. |
| 11 Why 0.78 | applied | "a tolerance of 0.02 below the nominal level". |
| 12 Agreement median | applied | Median of that pathway's scores over the cohort's evaluation scans, scores only. |
| 13 Forced module mapping | applied | |
| 14 Order, todo | modified | 3.3 opens on its finding with the label; the supplement todo remains. |
| Numbers: 0.82 = 0.82 | applied | |
| Numbers: 0.80 vs 0.83 | applied | Both in 3.2 with labels. |
| Numbers: 0.14 loss vs rule met | applied | 3.2 states both. |
| Numbers: weeks vs days | applied | "84 days, 12 weeks". |
| Numbers: four MU denominators | modified | 3.1 points to Table 1; 249 removed from the prose. |
| Numbers: coverage vs 0.80 | applied | |
| Numbers: −0.02 unclear | applied | |
| Numbers: 28 of 30 | applied | Misses explained. |
| Numbers: 220 / 249 / 114 | modified | 220 described as scans in few- or no-case situations; 249 removed. |
| Numbers: 35 vs four situations | applied | Sentence removed. |
| Numbers: Table 1 identical | applied | Verified (see above). |

## Hostile reviewer

| Item | Status | Reason |
|---|---|---|
| H1 UCSF circularity | modified | Ruling 2: plain 3.3 statement with the 0.88 baseline and within-enhancement 0.65; no retitle; abstract states what UCSF scores rested on. |
| H2 Full system not tested externally | modified | 3.2 reports the reduced timeline's 0.56 and its cause; heading claims model transfer; abstract unchanged. |
| H3 Within-phase numbers in abstract | rejected | Ruling 3; within-phase results stay in 3.3. |
| H4 "exploratory" in abstract; planned failure first | rejected | Ruling 3; the planned test's result is in 3.1's first paragraph. |
| H5 Conformal claim | applied | "met", threshold reason, UCSF interval in 3.4 and Limits. |
| H6 Report faithfulness tautology | modified | "faithful" kept but defined as traceable to the record; revision, first failure and the two misses disclosed; lexical limit in Limits. |
| H7 Baseline; novelty | modified | Enhancing volume alone serves as the simple baseline at UCSF (ruling 2); novelty "we are not aware"; no new volumetric-rule analysis run. |
| H8 Leakage; split variance | modified | Sentence that no patient is in more than one of fitting, calibration and testing; split SD to RESERVE. |
| Stronger: "carries" | applied | |
| Stronger: "about as high" | applied | Removed from the abstract. |
| Stronger: "kept coverage" | applied | |
| Stronger: "faithful", "passed" | modified | See H6. |
| Stronger: "images added nothing" | applied | |
| Stronger: clinician sees | modified | Conclusion now "PRISM shows the clinician both scores"; no reader-study claim. |
| Stronger: segmentation source | applied | Ruling 6. |
| Stronger: "no system combines" | applied | |
| Stronger: worked example | applied | "as an illustration". |
| Weaker: stacked hedges | applied | Planned results stated flatly. |
| Weaker: disagreement in abstract | rejected | Word limit, and it holds at MU only. |
| Weaker: 120-day apology | applied | |
| Weaker: lead with the audit | rejected | Title is the author's decision (OUTLINE 13). |
| Weaker: re-evaluation lesson as contribution | rejected | Author's rule of 2026-10-26: supporting evidence, not the story (ruling 10). |
| Housekeeping: markers and todos | modified | Proposal marker kept for the author; two supplement placeholders (S24, S25) added. |
| Housekeeping: abstract count | applied | 150 words (`wc -w`). |
| Housekeeping: Qwen3.8-27B | rejected | Name matches REPORT_V3.md and the run record. |
| Housekeeping: Table 1 | applied | |
| Housekeeping: plan archive | applied | Ethics statement points to the commits in Table 2. |

## Counts

Tone 45 (40 + 5): 33 applied, 12 modified, 0 rejected. Show/hide and integrity 62: 42 applied, 17 modified, 3 rejected.
Cold reader 25: 18 applied, 4 modified, 3 rejected. Hostile 27: 13 applied, 8 modified, 6 rejected.
**Total 159: 106 applied, 41 modified, 12 rejected.**

## Open for the author

- The proposed abstract (150 words) and all of the above.
- Supplement sections S24 (system results: conditional coverage, stricter flag rule, conformal model) and S25 (second
  report evaluation, model comparison) are referenced but not yet written.
- Tikhonov 2025 reference still unverified.
- Split variance as a Methods paragraph (OUTLINE decision 14).
