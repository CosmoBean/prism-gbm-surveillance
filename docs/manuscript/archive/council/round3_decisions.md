# Council round 3: editor's decisions

Applied to `paper/main.tex` on 2026-10-26 from the three round-3 reviews (`round3_cold.md`, `round3_reviewer2.md`,
`round3_voice.md`) under the coordinator's rulings. Everything is pending the author's approval; the backup is tag
`backup-before-council-2026-10-26`. LOCKED.md was not touched; the abstract remains a flagged proposal
(`[PROPOSED, awaiting approval]`).

Status words: **applied**, **modified** (point taken, text changed differently, reason given), **rejected** (reason
given), **deferred** (round 4, `\todo{round 4: ...}` in main.tex).

The exploratory analyses the reviewers asked for (NUMBERS.md section 12, commit ac4d9ae) landed while this round was
being edited. Per the coordinator, no number from them was written into the prose; each request has a
`\todo{round 4: ...}` that names its NUMBERS.md item. Two of them change what the text says and need care in round 4:
**12A** (with medians fixed on MU, disagreement does pick out less accurate scans at LUMIERE, +0.222) and **12B**
(class-conditional coverage: LUMIERE progression 0.767, UCSF non-progression 0.650).

## Coordinator rulings and how they were applied

1. **Abstract.** The voice proposal is the base. Changes: the first sentence opens on the clinical reason ("Treatment
   effects can mimic glioma progression on MRI"), then the challenges (cohorts small dropped for length; it is in the
   Introduction); "so the clinician sees what each score uses" says why the pathways are separate (cold reader 5);
   "a model trained there did better" is quantified as "against 0.86 when trained there" (the image pathway trained at
   UCSF, Section 3.2); "fitted once and" dropped for length; coverage "on point estimates" (ruling M3); "a confidence
   and a report from a local language model". 150 words (`wc -w`, flag excluded). The UCSF "exactly at the threshold"
   clause did not fit in the abstract; it is in the Introduction and in 3.4.
2. **Reviewer 2.**
   - RANO-like baseline: **rejected** (author: no RANO). Enhancing tumour volume alone is the simple reference: UCSF
     0.88 stays in 3.3; MU and LUMIERE deferred to round 4 (NUMBERS.md 12C) with todos in 3.2 and the Figure 2 caption.
   - M1: one clause after the MU 0.82 in 3.1: "mostly by separating phases of care, within which it did no better than
     the images (Section 3.3)". The within-phase numbers stay once, in 3.3. Heading not retitled (the reviewer's
     alternative would change the agreed outline; flagged for the author).
   - M3: coverage "on point estimates" in the abstract, Introduction (plus "at UCSF exactly at the threshold"), 3.4
     heading, 3.4 text and Figure 4 caption; exchangeability stated in one clause in 2.1; class-conditional coverage
     deferred (todo in 3.4, NUMBERS.md 12B). The singleton share was already in 3.4.
   - M4: 2.3 says the agreement rule and the card were "defined post hoc, after the cohort results had been seen"; 2.1
     says the agreement rule as evaluated needs the scores of a whole cohort, with a todo for the MU-fixed re-run (12A)
     and a second todo in 3.4 where the LUMIERE result will change. The MU Brier reversal (0.222 vs 0.147) moved from
     Table 2 into the 3.4 text. Discussion P1 and the Conclusion narrowed to "how far each score has been tested in the
     scan's situation, which for most scans at MU and UCSF is little".
   - M5: 3.5 heading "Every report passes a check of its numbers, flags and wording against the record"; the text says
     "a lexical check of its numbers, flags and wording", one clause on what it cannot judge (emphasis, order, what a
     clinician would infer), and that the second-evaluation records exclude the 10 LUMIERE and 10 UCSF development
     patients and are otherwise those of the first evaluation. Figure 5 caption aligned. Limits shortened to "The report
     checker is lexical, and no clinician has yet read the reports" so the checker's scope is not stated twice. No
     clinician read (not available; stays a stated limit).
   - M6: sensitivity / specificity at one MU-fixed threshold and external calibration deferred (todo in 3.2; 12D, 12F).
3. **Over-hedging.** Methods 2.3 now lists every exploratory analysis once and states the convention: "(exploratory)"
   once, where it first appears in a paragraph; figure and table notes mark panels and rows. Results markers went from about
   10 inline labels (several twice in a paragraph) to one per paragraph at most (3.1, 3.2 P1, 3.2 P2, 3.3 P1, 3.3 P2,
   3.4 P2, 3.4 P3, 3.5). Removed: the exploratory sentence in 2.1 for the image pathway and for the agreement rule and
   card (now in 2.3), "(both exploratory ...)", the second marker in 3.2 P2, "(the agreement rule is exploratory)",
   "(exploratory, not tested on new data)", "(exploratory comparison; ...)", "(descriptive; ...)". The Limits list of
   exploratory analyses became "The exploratory analyses listed in Section 2.3 need testing on new data."
4. **Moved to supplement / RESERVE.**
   - Deep networks: one sentence kept in 3.3 (learned above control, tracked enhancing volume); "their AUC stayed below
     enhancing volume alone, and on MU they did not meet the planned gain" moved (MU result remains in Table 2 row 2).
     Pointer `\todo{Supplementary section: deep networks at MU and UCSF}`; RESERVE row.
   - Language-model comparison: already one sentence; "exploratory comparison" label dropped (it is in the 2.3 list).
   - Per-cohort S2 / S3: Table 2 keeps the MU disagreement result; per-cohort numbers to RESERVE and a table note
     pointing to `\todo{Supplementary section: system results}`. The S3 "Met" cell corrected: it said "MU only
     (disagreement)" although the set met S3 at UCSF; now "MU (disagreement); UCSF (set)".
   - Image-model ladder: two sentences (Fig 3C). "The current scan alone scored lowest" and "They form the imaging block
     of the planned model, so PRISM's image pathway leaves them out" moved: the first to RESERVE, the second into 2.1 as
     the reason (cold reader ruling below). Middle-step CI deferred (12E).
5. **Cold reader.** MGMT defined in the Introduction ("the promoter of MGMT, a DNA-repair gene"). AUC spelled out at
   first use. Documented progression defined once per cohort in 2.2, pointing to Table 1, whose row is renamed
   "Documented progression (the label)"; the duplicate mentions in the 2.2 cohort sentences removed. Schedule inputs: one
   sentence in 2.1, "Such inputs belong to the timeline pathway, because they carry when a scan was taken, which the
   timeline already holds, and the image pathway has to run where no dates exist."
6. **Worked example** kept in the Discussion; OUTLINE notes it should become a panel in Fig 1 or Fig 5 (Fig 1 row and
   decision 17).

## Word counts (main text; same script as round 2: comments, todos, flags, citations and references stripped)

| Section | Before | After |
|---|---|---|
| Abstract | 150 | 150 |
| Introduction | 494 | 514 |
| Methods 2.1 PRISM | 721 | 754 |
| Methods 2.2 Cohorts and the task | 303 | 324 |
| Methods 2.3 Evaluation | 337 | 391 |
| Results 3.1 | 151 | 162 |
| Results 3.2 | 193 | 191 |
| Results 3.3 | 397 | 347 |
| Results 3.4 | 335 | 343 |
| Results 3.5 | 155 | 179 |
| Discussion | 749 | 735 |
| Conclusion | 63 | 52 |
| **Total (excluding abstract)** | **3,898** | **3,992** |

The total is about 90 words above the 3,650–3,900 budget. The growth is the rulings' additions (definitions for the
cold reader, the 2.3 list and convention, the narrowing clauses in 2.1, 3.4 and 3.5); the moves cut 3.3 by 50 words.
Round 4 will add sentences for the deferred analyses, so a trim pass is needed then (candidates: the 3.1 all-glioma
sentence, which reviewer 2 minor 7 suggests moving to the Table 2 note; the 3.4 stricter-rule sentence; Discussion P4).

## Voice review (abstract + 20 rewrites)

| Section | Item | Status | Note |
|---|---|---|---|
| Abstract | Proposal | modified | Ruling 1. |
| Intro | 1 "Surveillance data set five challenges" | applied | |
| Intro | 2 Fifth challenge split by semicolon | applied | Also answers cold reader 2 (the causal jump). |
| Intro | 3 "3 of 20 ... included; we planned two" | applied | |
| Intro | 4 Confidence in three parts; checker | applied | |
| Intro | 5 "When we audited the scores" | applied | |
| Methods | 1 Confidence sentence | modified | "gives the clinician a set of plausible outcomes and how many scans like this one the system has been tested on": the voice version described only the card. |
| Methods | 2 "We meet the third challenge" | applied | |
| Methods | 3 Ridge: "scaling and any selection were fitted on the training data only" | applied | Also cold reader 3. |
| Methods | 4 Task sentence without colon question | applied | |
| Methods | 5 "diagnostics of what a score depends on; none of them is a decision rule" | applied | |
| Results | 1 120-day sentence | applied | |
| Results | 2 Schedule sentence with "because" | applied | |
| Results | 3 "We built the image model ... to see which inputs raised its AUC" | applied | |
| Results | 4 UCSF closers | applied | Deep-network sentence then trimmed (ruling 4); bridge now "PRISM attaches a confidence to each score" (M4: no "how far ... trusted"). |
| Results | 5 "The report therefore gives the clinician ... exactly as the record holds them"; card "how many tested cases its situation holds" | applied | |
| Discussion | 1 "the locked results therefore measure transfer" | applied | |
| Discussion | 2 "The label is progression as each centre documented it" | applied | |
| Discussion | 3 Checker limit | modified | Shortened further; the checker's scope is now in 3.5 (M5). |
| Conclusion | 4, 5 | applied | |

## Reviewer 2

| # | Item | Status | Reason |
|---|---|---|---|
| M1 | Within-phase next to 0.82 | applied (3.1) / modified | Abstract unchanged on this point (ruling placed it in 3.1); heading and phase-only baseline not added (the within-phase and between-phase audit in 3.3 is the floor; flag for author). |
| M2 | Enhancing volume baseline; UCSF timing in 2.2 | modified / deferred | UCSF 0.88 already in 3.3; MU / LUMIERE and Figure 2 bar deferred (12C). 2.2 already says positives are dated within 30 days. Abstract replacement not taken (ruling 1 quantifies 0.86 instead). |
| M3 | Coverage wording; class-conditional; exchangeability | applied / deferred | Ruling 2. Mondrian already in RESERVE. |
| M4 | Agreement post hoc and transductive; card; Brier reversal | applied / deferred | Ruling 2. |
| M5 | Reports wording; overlap; checker limits; clinician read | applied / rejected (read) | Ruling 2; the 29 / 30 to 28 / 30 change is in Table 2 S7 and RESERVE. |
| M6 | RANO-like rule | rejected | Author: no RANO. Operating points and calibration deferred (12D, 12F). |
| m1 | Scan-flow diagram | deferred | Not in this round's rulings; `docs/manuscript/FLOW.md` and `cohort_flow.png` exist for the supplement. |
| m2 | Early-RT definitions differ | no action | Table 1 note c and 2.1 already say how each is defined; flag for author. |
| m3 | Ridge penalty, missing IDH / MGMT | no action | Supplement methods; flag for author. |
| m4 | Conformal model vs displayed score | no action | RESERVE row exists ("cost of the split"). |
| m5 | Mask harmonisation sentence | no action | Supplement todo exists; RESERVE row exists. |
| m6 | Abstract density | modified | Ruling 1. |
| m7 | All-glioma +0.04 in 3.1 | no action | Kept (round 2 ruling); trim candidate for round 4. |
| m8 | Placeholders, Tikhonov, model name | no action | Open items unchanged; the model revision hash is in NUMBERS.md. |
| m9 | Table 2 S2 too long | applied | Ruling 4. |
| m10 | "Detected" → "separated" | rejected | The task is detection at the scan (2.2); the voice reviewer keeps "detected". Long 3.4 heading not shortened because ruling M3 adds "on point estimates". |
| Tone | Over-hedged details | applied | Ruling 3. |
| Move | Ladder, deep networks, LLM comparison, S2/S3 | applied | Ruling 4. All-glioma gain and stricter rule not moved (not in the rulings). |
| Missing | TRIPOD+AI checklist | no action | `docs/manuscript/CHECKLIST_TRIPOD_AI.md` exists for the supplement. |

## Cold reader

| # | Item | Status | Reason |
|---|---|---|---|
| 1 | MGMT | applied | Ruling 5. |
| 2 | Fifth challenge causal jump | applied | Voice Intro 2. |
| 3 | "every fitted step inside the training data" | applied | Voice Methods 3. |
| 4 | Conformal "one or both outcomes" | applied | "it holds one outcome when the score is clear and both when it is not". |
| 5 | Why schedule inputs are excluded | applied | Ruling 5, in 2.1. |
| 6 | Which analyses are exploratory | applied | Ruling 3 (list once in 2.3). |
| 7 | UCSF progression dated after the scan | no action | 2.2 defines the 30-day window; 3.3 explains what it means for the AUC. |
| 8 | "a model trained there did better" | applied | Abstract gives 0.86. |
| 9 | "the intervals overlap" | modified | Now "with overlapping intervals" in a descriptive comparison; no difference is claimed. |
| 10 | Reader study | no action | Stated as a limit and as the next step. |
| Terms | AUC, MGMT, documented progression | applied | Others (grade 4, conformal prediction, grouped CV) are standard for the journal's readers; not expanded. |
| Marketing (4) | "handled by how PRISM is evaluated"; "its use ... was planned"; novelty sentence; label limit; coverage | modified | First two rewritten (voice Methods 2; the planned use moved into the 2.3 list); the label limit rewritten (voice Discussion 2); coverage now says "on point estimates" everywhere; the novelty sentence kept (voice keep). |
| Abstract motivation | applied | Ruling 1. |

## Round-4 todos in main.tex

1. 2.1: agreement rule with medians fixed on MU, applied unchanged externally (NUMBERS.md 12A).
2. 2.3: add the new exploratory analyses to the list.
3. 3.2: enhancing tumour volume alone at MU and LUMIERE (12C); sensitivity / specificity at one MU-fixed threshold
   (12D); external calibration (12F); one sentence and a supplementary table.
4. 3.3: bootstrap CI for the ladder's middle step (12E; it includes 0, so no "each step raised" wording).
5. 3.4: coverage by true class with the single-outcome share by class (12B).
6. 3.4: restate the LUMIERE / UCSF disagreement sentence with the MU-fixed rule (12A changes LUMIERE).
7. Figure 2 caption: enhancing tumour volume alone as a reference bar in each cohort (12C).

New supplement pointers: `deep networks at MU and UCSF`; Table 2 note a (`system results`, per-cohort S2 / S3).

## Integrity check

STYLE.md "always in the main text": intended-use 120-day 0.60 (3.1); timeline baselines (3.1, 3.2) and the enhancing
volume baseline (3.3); within-phase result (3.1 clause, 3.3 numbers); planned vs exploratory (2.3 list, markers,
captions, Table 2 notes); scope limits (Limits: one centre, label as documented, no clinician read); contradicting
results (images did not raise the timeline on MU; Brier reversal at MU, now in the text; UCSF coverage interval;
disagreement at MU only; first report failure; better when trained at UCSF, now in the abstract). No RANO, no
"published", no em dashes, British -ise. `bash paper/build.sh` passes (main 18 pages, supplement 54).
