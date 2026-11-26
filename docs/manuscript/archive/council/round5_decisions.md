# Council round 5: final editor's decisions

Applied to `paper/main.tex` on 2026-10-26 from `round5_audit.md` and `round5_editor.md`. Everything is pending the
author's approval; the backup is tag `backup-before-council-2026-10-26` (commit 1e5c595) and `paper/backup/`.
LOCKED.md was not touched; the abstract remains a flagged proposal (`[PROPOSED, awaiting approval]`).

Status words: **applied**, **modified** (point taken, text changed differently, reason given), **rejected** /
**skipped** (reason given).

## Audit: the nine WRONG items

| # | Item | Status | Note |
|---|---|---|---|
| 1 | "plans committed before any external label was read" | applied | "before any model score was compared with an external label" (2.3). Ethics statement unchanged. |
| 2 | External combined score's schedule inputs | applied | "the interval since the previous scan and whether there was one" (2.1). |
| 3 | LUMIERE disagreement led with the post hoc rule | applied | 3.4 P2: MU result and the planned tests first; then "Those tests used each cohort's own medians, and with them neither external cohort met the tests; at LUMIERE the difference was 0.11"; then the MU-fixed rule (0.89 / 0.67, 0.22) marked †, "which the system uses because they can be computed at a single scan". First sentence now claims MU only. Table 2 Met cells give the planned answer per cohort ("MU-Glioma-Post: yes (...). LUMIERE: set only. UCSF-ALPTDG: no"); note a names the MU-fixed result. Figure 4 title and panel B aligned. |
| 4 | Report-model comparison listed as unplanned | applied | Removed from the unplanned list (REPORT_V3_1_PLAN.md section 4 plans it; Table 2 keeps "Descriptive"). |
| 5 | Q4 cell cited for "tracked enhancing volume" | applied | "learned above a permuted-label control (Table 2), and their scores tracked enhancing volume†" with the supplement pointer. |
| 6 | Card denominators 35 / 249 next to the 54-scan Brier | modified | The 249 denominator is gone: "54 of the 146 MU scans fell in the tested situation" (the S4 set, same as 3.1). The Brier numbers moved to RESERVE (editor's move list); the reversal stays in words. |
| 7 | "exactly as the record holds them" | applied | "A clinician reading a report therefore sees ... with every number, flag and statement taken from the record." |
| 8 | Card built from the same cohort's results | applied | 2.1: the card is "a table of each cohort's own held-out results, which include the scan being looked up". 2.3 restricted to "For the models and the conformal sets". |
| 9 | Combined 0.82 (exploratory B1 + image pathway) vs planned model 0.837 | applied | 3.1: "The combined score that PRISM shows, fitted on the inputs of both pathways†, also reached 0.82 ... The imaging model fixed in advance, a different model that adds measurements and three schedule inputs to the timeline, fell short of its pre-specified gain of 0.03". |
| + | 0.60 in the Discussion (STYLE always-in-main) | applied | Limits: "(AUC 0.60 in the intended use)". |

## Audit: the 19 checklist items

| Kind | Where | Fix |
|---|---|---|
| Colon (5) | 27 inputs; masks; tier; own record; phases | "its 27 inputs are"; "which are the automatic masks"; tier rule as three clauses; "own record, as"; "three phases of care, which are" |
| Slogan (1) | "Keeping the pathways apart is what let us ..." | deleted |
| Abstraction as subject (7) | confidence gives; audit shows; an AUC measures; warning is broad; report gives; keeping apart; label agrees | "With each score the clinician sees"; "When we audited ..., the scores at MU depended"; "a model therefore scores well largely by agreeing"; "This rule flagged"; "A clinician reading a report sees"; deleted; "most progression scans were also rated as showing increased enhancement" |
| Intensifier (3) | follow closely; agrees closely; exactly | removed |
| Verdict (1) | "transferred worst" | "had the lower AUC of the two pathways, 0.56" |
| Codes (1) | Table 2 Q1-Q4, S1-S7, L1; "Q4" in text | prefixes removed; L1 row reads "Smallest report model passing the checker rule"; note says "flag and tier tests" |
| Hyphen chain (1) | early-post-radiotherapy flag | "flag for the early weeks after radiotherapy" |

Audit section B, also applied: coverage given as percentages in 3.4 (separates it from AUCs); middle ladder step
"(0.00 to 0.11)". Not applied: the 0.77 / 0.65 / 0.86 duplicates (see editor item 1); 3.4 number density beyond the
percentages (the 62% to 75% singleton share stays: it is the capability).

## Fresh editor

| Item | Status | Note |
|---|---|---|
| UCSF combined-score AUC in 3.2 | applied | "The locked combined score reached 0.86 (0.76--0.93), but at UCSF its timeline inputs are approximated, and part of its AUC comes from the interval between the two scans, which was shorter before progression†." The Figure 2 caption's interval clause was removed (said once). Two 0.86 values at UCSF (trained image pathway 0.863, locked combined 0.856) remain; they are different models in adjacent sentences, each named. |
| Reconcile MU denominators | applied | Table 1 note b: 146 = 181 less the 35 pre-radiotherapy scans; 42 (not 47: that count was all gliomas) grade 4 progression scans excluded; reports on 114 scans of the 60 MU patients not in prompt development, 162 of 178 LUMIERE, 130 of 140 UCSF. |
| One marker for exploratory | applied | `\expl` (superscript dagger), defined once in 2.3; every "(exploratory)" in text, legends and Table 2 replaced; Limits "the analyses marked †". |
| Shorten the unplanned-analyses paragraph | applied | 110 words to about 60; the full list goes to `\todo{Supplementary section: analyses not fixed in advance}`; the agreement rule and card stay named as post hoc. |
| Within-phase images vs timeline in its own sentence | applied | "Within a phase of care, where the schedule cannot separate the scans, the image pathway gave about as much evidence as the timeline, with AUCs of 0.68 ... and 0.64 ...". |
| Missing-input handling | applied | 2.1, one sentence from DETECTION_TASK.md (B0 rules: no unknown indicators), AUDIT_SYSTEM.md 4(a) and UCSF_RESULTS.md deviation 6: unknown IDH / MGMT coded as the reference category; missing measurements filled with the training median plus a missing-value indicator inside the fitted pipeline. |
| Planned gain of 0.03 under-powered | skipped | No power calculation in any source; RESERVE row added. |
| Abstract proposal | modified | Taken as the base. Kept "after one revision" and "on average ... fell short for one outcome at both external centres"; added the card ("a confidence stating where evidence is thin"); "rested mainly on when in treatment patients were scanned" for the schedule finding; colon removed. 149 words. |
| Discussion opener and 3.2/Discussion UCSF sentence | applied | "For most scans at MU and all at UCSF, the card has few cases." as its own sentence; "At UCSF enhancing volume provided the score, and enhancing volume alone did as well as the image pathway trained there." ("as any model" was not used: the LUMIERE image set reached 0.89 / 0.91 at UCSF.) |
| LUMIERE ET clause | applied | "level with it; at LUMIERE only the combined score did better than this simplest baseline". |
| Other sentence fixes (abstract 1, Intro 3-5, Methods 6-8, 13) | rejected | Budget (main text at 3,946 of 3,950) and conservative revision; none is wrong as it stands. |
| Q2 +0.248 in text; schedule finding in the Introduction; split-variance clause in the Introduction; card in abstract | partly | Card now in the abstract; the rest skipped for budget. Q2 stays in Table 2. |
| Move ladder, report counts, Table 2 deviation note | rejected | The ladder's two steps with intervals were a round 4 ruling; the deviation note is the disclosure Methods 2.3 points to. |
| Limitations as fuller sentences; "90%" in the Limits | partly | Two short sentences merged; 90% not repeated (said once in 3.2). |
| Scan-flow figure, segmentation-quality sentence, title | rejected here | Figure is a supplement task; segmentation agreement is in RESERVE (Dice 0.80); title is the author's (OUTLINE decision 13). |

## Word counts (round-4 counter; abstract excluded)

| Section | Round 4 | Round 5 |
|---|---|---|
| Abstract | 150 | 149 |
| Introduction | 519 | 519 |
| Methods 2.1 | 704 | 751 |
| Methods 2.2 | 279 | 282 |
| Methods 2.3 | 365 | 278 |
| Results 3.1 | 134 | 159 |
| Results 3.2 | 272 | 307 |
| Results 3.3 | 345 | 369 |
| Results 3.4 | 397 | 390 |
| Results 3.5 | 165 | 169 |
| Discussion | 684 | 688 |
| Conclusion | 34 | 34 |
| **Total** | **3,898** | **3,946** |

## Self-check

- grep: no em dashes, RANO, "published", -ize spellings, "closely", "exactly", Q/S codes in the prose.
- Always-in-main: intended-use 0.60 (3.1 and now the Limits); timing baseline (3.1, 3.2); within-phase result (3.1,
  3.3, Discussion); planned vs exploratory (dagger, 2.3); scope limits; contradicting results (planned gain not met,
  external flag tests not met, first report evaluation 0 of 178, UCSF calibration, MU tier reversal in words; the
  per-pathway coverage misses now only in Table 2).
- `bash paper/build.sh` passes (main 17 pages, supplement 54).
