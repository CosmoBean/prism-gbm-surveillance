# Council round 5: final number, label and tone audit

Reviewer only. `paper/main.tex` (600 lines, built from the tree at the start of this round) read against NUMBERS.md
(all sections, incl. 12), META_PATTERNS.md checklist, STYLE.md "always in the main text", and the four plan docs
(UCSF_PLAN, SYSTEM_PLAN, REPORT_V3_1_PLAN, DETECTION_TASK). CSVs were re-read where a number had no NUMBERS.md row
(`review_round3/A_agreement_mu_fixed.csv`). Line numbers are `paper/main.tex`. Nothing in `paper/` was edited.

Result: no number in the abstract, Results text, Tables 1 and 2 or the captions disagrees with NUMBERS.md in value or
rounding. The WRONG items below are claims, labels and cross-references, not values.

---

## A. WRONG (fix before submission)

1. **L187 "plans committed before any external label was read" is false as written.**
   UCSF_PLAN.md states the 29 / 40 label counts and was "committed before the first run that reads UCSF labels
   *together with model scores*"; DETECTION_TASK.md says "before any model saw a real label" (LUMIERE labels had been
   used to build the cohort). Fix: "before any model score was compared with an external label". The Ethics statement
   (L406) "Analysis plans were committed ... before each external test" is true and can stay.
2. **L122-124 "the interval since the previous scan, its one schedule input" is wrong for the external combined score.**
   NUMBERS.md 2.1 (T): adds log days since the previous scan **and a has-previous flag**, plus log days since surgery
   and the early-post-RT flag. Fix: "the interval since the previous scan and whether there was one".
3. **L290-295 the LUMIERE disagreement result is stated as the planned test, but every LUMIERE number in the paragraph
   except the last is the post hoc MU-fixed-median variant.**
   0.89 / 0.67, difference 0.22 (0.10-0.34) and the 60% flagged share are `A_disagree_mu_median` (CSV-checked:
   0.8892 / 0.6671, +0.2220, 0.1025 to 0.3366, 60.1%). The planned own-median S2 is +0.105 (-0.049 to +0.266), not met
   (the last sentence gives it, 0.11, but after the reader has taken 0.22 as the result). The opening sentence "picked
   out the less accurate scans at MU and LUMIERE" therefore claims more than the planned test. Fix: put "with medians
   fixed on MU (exploratory)" in the sentence that first gives 0.89 / 0.67 / 0.22, and give the planned 0.11 beside it.
   Same wording applies to Fig 4 caption (B) and Table 2 S2/S3 rows (already labelled exploratory there, which is fine).
4. **L195-199 lists "the comparison of report models" as an unplanned analysis; Table 2 row L1 lists it as fixed in
   advance.** REPORT_V3_1_PLAN.md section 4 plans the model-size ladder and question L1 (descriptive) before any v3.1
   report; NUMBERS.md 7 calls it "descriptive, EXPLORATORY secondary". One label for both places. Suggest: remove it
   from the unplanned list and keep "Descriptive" in Table 2 (the ladder itself was planned; only its reading is
   descriptive), or relabel both as exploratory.
5. **L272 "Deep networks fine-tuned on UCSF scans also tracked enhancing volume (Table 2, Q4 ...)".** Table 2 Q4 shows
   that the networks beat a permuted-label control (+0.201), not that they track ET volume (r >= 0.76, NUMBERS.md 4,
   EXPLORATORY diagnostic). The cited cell does not support the sentence. Fix: cite the supplement section only, or add
   the correlation (one number) and mark it exploratory.
6. **L300 "35 of the 249 MU scans fell in a tested situation" sits beside Brier scores from a different set.** The
   tested-cell Brier 0.222 (L304) is the 54-scan tested tier of the 146 intended-use scans (S4: 38 / 16); 35 of 249 uses
   all 249 grade-4 index scans with reports (NUMBERS.md mismatch 14). A reader sees two counts for the MU tested tier
   within four lines. Fix: state the denominator ("of the 249 grade 4 index scans") or drop the 35 and use 54 of 146.
7. **L319-320 "gives the clinician ... exactly as the record holds them"** contradicts L312-313 (the check is lexical and
   cannot judge emphasis or order). Also the "therefore" does not follow: a passing lexical check shows that numbers,
   flags and wording match the record, not that figure and volumes are shown exactly. Fix: "gives the clinician the
   segmentation figure and volumes, the two scores and the confidence, each taken from the record".
8. **L181 "no patient appears in more than one of fitting, calibration and testing" in Sections 3.1 to 3.4 is not true of
   the reliability card.** The card's tiers and the AUCs it displays for a scan's situation are computed from the same
   cohort's out-of-fold scores, including that scan's patient (NUMBERS.md 6, card CI from 1,000 draws on the cohort's own
   scores; S4 tiers are evaluated on those same scans). Either restrict the sentence ("the models and the conformal
   sets") or state that the card is a descriptive lookup from the cohort's own results. Needs the analysis lead to
   confirm; I could not find a held-out card construction in the sources.
9. **L213 "The combined score also reached 0.82" is an exploratory model (B1 + I_pure) with no label, in a paragraph
   whose next clause cites the planned model (Table 2, 0.837).** Two "combined" numbers (0.82 here, 0.837 in Table 2 row 1,
   called "planned model" there and "planned imaging model" in the text) are one reader step apart. Label the 0.82
   "(exploratory)" and say the planned model is a different one, or give 0.84 for it in the text.

## B. Smaller number and label issues (right, but easy to misread)

- **Duplicated values meaning different things in nearby text.**
  - 0.77 is the LUMIERE combined AUC (L222) and the coverage of LUMIERE progression scans (L283).
  - 0.65 is LUMIERE images alone (L223), the UCSF single-scan model within "increased enhancement" (L270), and UCSF
    non-progression coverage (L284).
  - 0.86 is the UCSF-trained image pathway (abstract, L232) and the locked UCSF combined score in Fig 2 (0.856). The
    abstract says "against 0.86 when trained there" and a reader looking at Fig 2 finds 0.86 twice at UCSF.
  - 0.80 is the UCSF single-scan AUC (abstract) and the nominal 80% level; 0.79-0.95 CI of ET volume vs 0.80 AUC.
  Not errors, but L283-284 could give coverage as percentages (77%, 65%) to separate it from AUCs.
- **L259 "(-0.00 to +0.11)"** should read "0.00 to +0.11" or "-0.003 to +0.106" is rounded; the minus on zero is the only
  such case. Also the first step has no stated value in text (0.66, single scan), only in Fig 3C; fine, but "0.05 higher"
  is then a difference from a number the reader has not seen.
- **L253 lower CI "0.04" for +0.114 (0.035 to 0.196)**: 0.035 rounds either way; the CSV carries more digits than
  NUMBERS.md. Not checked to the third decimal. Use 0.03 or 0.04 after reading `phase_ladder/results.csv`.
- **L232-233 "difference 0.14, 0.03-0.26"** is the planned descriptive Q3 (Ipure) and is correctly the planned arm; the
  next clause (single-scan "about the same", +0.031, -0.052 to +0.116) is exploratory and labelled. OK.
- **Abstract "met their planned coverage on average at every centre"** is true on point estimates (UCSF 0.783, CI
  0.681-0.870); L281-282 says so. The abstract carries no "on point estimates"; L4 of the round-4 header says it was cut
  for length. Acceptable at 150 words (the limit), but the abstract's audit sentence ("An audit found ...") is
  exploratory and unlabelled; no room to add.
- **Table 2 S2 "Met" cell: "Both at MU-Glioma-Post"** does not say which two. Write "Disagreement and conformal {0,1}".
- **Table 2 caption "Each rule was committed to the repository before the analysis it governs"** and the "Met" column for
  S2/S3 includes exploratory LUMIERE results; the cells are labelled "(exploratory)", so keep, but the caption could
  read "Each rule ... (agreement rule and tiers excepted, see note)".
- **NUMBERS.md and TABLE1_COHORT.md print MU grade 4 age as 62 [53-70]; Table 1 prints 62.5** (round 2 ruled 62.5 is the
  unrounded median). Paper is right; the fact sheet should say 62.5 to stop a repeat flag.
- **NUMBERS.md "Plans" header omits the detection plan commit 2b4c927** that Table 2 cites (it exists in `git log`; all
  six plan commits resolve).
- **Q1-Q4, S1-S7, L1 codes** in Table 2 are plan IDs a reader cannot decode (see D).

## C. Always-in-main list (STYLE.md section 4)

| Item | Where | Status |
|---|---|---|
| Intended-use result beside the flattering one | 3.1 (146 scans; 120-day 0.60 in the intended use) | present |
| 120-day intended-use 0.60 in Discussion | L367-368 says "less well" with no number | **missing the number** (STYLE.md: "stays in the Results and Discussion"); add "0.60" |
| Strongest baseline (timing) | timeline 0.82; clinical 0.53; combined not above timeline | present |
| Within-phase result | 3.3 (-0.02; 0.68 vs 0.64); abstract/Discussion | present |
| Planned vs exploratory | 2.3 list, per-paragraph labels, Table 2 note | present; items 3, 4, 9 above are the gaps |
| Scope limits (one centre, documentation-based label, no clinician read) | L363-368 | present |
| Results that contradict the claim | P - B1 fails; S2/S3 fail externally; first report evaluation 0/178; calibration at UCSF; MU tier reversal | present. Not in text: the "tier" flag reversed on MU (S2 -0.224, CI excludes 0 the wrong way) and the "any flag" rule failing S2 (91% flagged); Table 2 note points to the supplement. Acceptable under the reserve, but it is a contradicting result |

## D. Checklist sweep (META_PATTERNS.md) in main.tex prose, tables and captions

Count: **19 remaining violations** (12 clearer, 7 judgement calls marked *).

- Colon reveal / list colon (5): L114 "27 inputs: the", L127 "each cohort: the", L142 "tier: tested", L158 "own record: as",
  L170 "phases of care: during". All introduce a list or clause; recast with "such as", "namely", or a full stop.
- Contrast slogan / quotable closer (1): L332-333 "Keeping the pathways apart is what let us measure these differences at
  each centre." (L89 "..., but not within each outcome class" and L227 "so at LUMIERE the transfer rests on the combined
  score" are factual contrasts; left alone.)
- Abstraction as subject (7): L100 "The confidence gives the clinician" ; L249 "The audit ... shows"; L271 "an AUC ...
  measures agreement"; L295 "The warning is broad"; L319 "The report therefore gives"; L332 "Keeping the pathways apart";
  L365 "the label agrees closely" (the last two overlap with other items; counted once each).
- Em dash (0). Verified by grep of `---`, the Unicode dash and ` -- `.
- Intensifier (3): L267 "follow enhancement closely", L365 "agrees closely", L320 "exactly". Hedges "mainly"
  (L87, L249, abstract) and "largely" (L271, L329) are frequent; *judgement calls, 4 of the 7 flagged with asterisk in
  the total below*.
- Verdict word (1): L235 "transferred worst of the pathways" (say "had the lowest AUC of the three pathways, 0.56").
  "failed" at L315 is the disclosed failure and is fine.
- Accusation (0 firm). Watch L357-360 (Christodoulou: "predicted a label assigned at the patient level ... none of these is
  detection at the scan"): neutral in wording, and consistent with the source check (EXPLORATORY, 9810dc4); keep, but do
  not add numbers.
- Model codes (1 cluster): Table 2 uses Q1-Q4, S1-S7, L1 and L272 says "Q4"; replace with the plain question or number
  the rows 1-14. No B1 / I_pure / T / P codes appear in the prose.
- Hyphen chain (1): L234 "early-post-radiotherapy flag" (write "the flag for the early weeks after radiotherapy").
- RANO (0), "published" (0), American -ize spelling (0; British "harmonisation", "tumour", "oedema" throughout).
- Number density: 3.4 first paragraph carries 14 numbers; the checklist wants one per claim. Suggest moving
  0.78 / 0.87 / 62-75% to Fig 4A and keeping the two class-conditional numbers. (Counted as a * item.)

Totals: colons 5, slogan 1, abstraction subject 7, intensifier 3, verdict 1, codes 1, hyphen 1 = 19.

## E. Remaining \todo and \flag (20 \todo, 1 \flag)

**Author decision (11)**
- Title block L17: first author's full name; contact (email, ORCID). (2)
- Abstract L34: `\flag{[PROPOSED, awaiting approval]}`; abstract is 150 words, at the journal limit. (1 flag)
- Acknowledgements L385. Disclosure L388. Generative AI declaration L392 (draft; confirm wording, including that Claude
  wrote and ran analysis code). Funding L400. Ethics L404 (institutional determination or waiver). Data availability L410
  (released tables, fold assignments, DOI). Code repository link and tag L412. Notes on contributors L419.

**Supplement to write (8 sections; 9 todo marks)**
- Image pathway inputs and their harmonisation at LUMIERE and UCSF (L117).
- System results: conformal split and MU calibration (L136); thresholds fitted per outcome (L286); S2/S3 for each flag and
  each cohort with own and MU-fixed medians and the any-flag rule (L296, Table 2 note a at L516). One section can serve
  all four marks.
- Deviations from the plans (L188): the grade-4 training rows vs "all MU detection scans", A-T approximation at UCSF,
  v3.1 as a second evaluation.
- Calibration and thresholds (L242): slopes, O/E, MU-median operating point (NUMBERS.md 12D, 12F).
- Deep networks at MU and UCSF (L272): includes the ET-tracking correlation (see WRONG 5).
- Second report evaluation and model comparison (L318): v3 vs v3.1, model-size ladder, failure categories.
- Existing S7 ("PRISM v1"), S21 ("Report generator version 2") and the supplement's v1/v2 framing conflict with the
  "final system only" direction; out of scope here, noted for the supplement pass.

**Figure to build (5)**: `fig1_system.pdf` .. `fig5_report.pdf` do not exist in `docs/manuscript/figures/` (only older
single-split, phase and architecture figures); all five render as red placeholders. Inputs are in NUMBERS.md section 11.

**Citation to verify (1 todo, plus a check)**
- L357 Tikhonov 2025 (arXiv:2509.06511): no entry in `paper/refs.bib`. Every other `\cite` key resolves in refs.bib; I did
  not verify the 2025-2026 entries (christodoulou2026, chen2026, jabal2026, gomaa2025, elyassirad2025, shi2025) against
  their sources. Shi 2025 "3 of 20" matches SYSTEM_LANDSCAPE.md row 6.3.

## F. Checked and correct (no action)

Abstract: 0.82, 0.77, 0.80, 0.73, 0.86, coverage statement, 114 / 162 / 130. Section 3.1: 146 scans, 0.71 (0.63-0.78),
0.82 (0.75-0.90), 0.53, 0.60 (0.52-0.69). 3.2: 0.77 (0.68-0.86), 0.65, 0.69, 0.62, 0.66, 0.80 (0.69-0.89), 0.73 (0.60-0.84),
0.86, 0.14 (0.03-0.26), 0.56, O/E 0.72 (0.55-0.91), 90% called positive. 3.3: -0.02 (-0.13 to +0.11), 0.68 (0.58-0.77)
vs 0.64 (0.51-0.78), +0.10 (0.05-0.15), -0.01 (-0.06 to +0.04), 0.88 (0.79-0.95), 27 of 29, 7 days, 37 scans, 0.65
(0.44-0.84). 3.4: 0.78-0.87, 62-75%, 0.68-0.87, 0.77 (0.67-0.87), 0.65 (0.51-0.79), 0.94 and 0.97, 40%, 0.90 / 0.59,
11 of 11 percentage and CI values for 12A, four tested situations (1 + 3), 0.222 vs 0.147. 3.5: 0 of 178, 28 of 30.
Discussion: 1 of 9 scans. Table 1: every row against NUMBERS.md 2.2 (age 62.5 per round 2). Table 2: all values, plan
commits 2b4c927, 0e7c9fe, e7cba80, 4f7e7b9 (all in `git log`), +0.041 (+0.006 to +0.081) and +0.036 (-0.014 to +0.085).
"Pre-specified" claims for S1, S5-S7, Q1-Q4, LUM-1, MU-1, MU-2 match the plan docs. Not pre-specified and labelled so:
agreement rule, card tiers, MU-fixed medians, class-conditional coverage, operating point, ladder, ET baselines, clinical
alone at LUMIERE, LUMIERE calibration. No RANO, no "published", no v1/v2 in the main text.
