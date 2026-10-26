# Council summary for the author (2026-10-26)

Five review rounds were run on `paper/main.tex` overnight under your authorisation. Each round had reviewers who
only wrote reviews, and then an editor who applied them under a coordinator's rulings. **Everything below is pending
your approval.** LOCKED.md was never edited. The abstract in main.tex is still a flagged proposal.

## What each round did

1. **Round 1**: cold and hostile read, show/hide and integrity, tone (0995568, 4d66592, 785d4b7). Editor dcfd00a:
   159 items, 106 applied. UCSF gets both planned image models, the claim is transfer and not best performance,
   coverage is "on point estimates", faithfulness is always "after one revision".
2. **Round 2**: show/hide, tone, numbers and integrity (e8941f6, 60d56a3, 7f2489c). Editor ed1b3cd: 114 items, 92
   applied. Card claim is the distribution by cohort, Table 1 MU age 62.5, unwritten supplement sections become
   `\todo{Supplementary section: ...}`.
3. **Round 3**: cold read, reviewer 2, voice (e07d306, db1d6c8, ec83502), then exploratory analyses ac4d9ae. Editor
   18d7861: new abstract opening on the clinical reason, narrower claims for coverage, agreement, card and reports.
4. **Round 4**: integrity after the new analyses, trim (823aea6, 4e77e51). Editor 4dc208e: "transfer" means ranking;
   calibration and the MU threshold do not carry over; coverage "on average"; agreement rule uses medians fixed on MU;
   one-sentence Conclusion; 3,898 words.
5. **Round 5**: fresh editor read and final audit (bf8f50a, 9e2fa0c, 996705c). Final editor (this commit): 9 wrong
   claims, 19 checklist items, the editor's integrity items; 3,946 words. Record: `round5_decisions.md`.

## Biggest content changes since the skeleton (tag backup-before-council-2026-10-26)

Integrity changes, the ones that change what a reader concludes:
- **UCSF has two image numbers.** Single-scan measurements 0.80 and the system's image pathway (with change) 0.73,
  which met its planned rule; trained at UCSF the pathway reached 0.86. The change inputs transferred less well. The
  locked combined score (0.86) is now given in 3.2, with the caveat that its timeline inputs are approximated at UCSF
  and part of it comes from the scan interval.
- **Enhancing volume alone** is the simple reference in every cohort (MU 0.62, LUMIERE 0.66, UCSF 0.88). At UCSF it
  did as well as the model trained there; the UCSF label follows enhancement at the same scan.
- **Ranking, not calibration.** AUCs describe ranking. The combined score overpredicted at UCSF (O/E 0.72), and a
  threshold at the MU median called 90% of UCSF scans positive, so a new centre recalibrates.
- **Coverage by outcome.** Coverage is met on average (on point estimates) at all three centres but falls short for
  one outcome at LUMIERE (progression 77%) and UCSF (non-progression 65%). In the abstract, the Introduction, 3.4 and
  Figure 4.
- **Agreement rule.** The planned tests (each cohort's own medians) were met at MU only. The system's rule now uses
  medians fixed on MU, so it can be computed at a single scan; with it LUMIERE also separates (0.22, marked as not
  fixed in advance). The planned result is given first.
- **Reports: second evaluation disclosed.** The first evaluation failed at LUMIERE (0 of 178). Every report passed
  after one prompt revision, with the checker unchanged. The second evaluation excludes the patients used to develop
  the revision. The check is lexical, and the text says what it cannot catch.
- **Card.** Only 4 tested situations (1 at MU, 3 at LUMIERE, none at UCSF). 54 of the 146 MU scans are tested. The
  card is a lookup of each cohort's own held-out results (said in 2.1). At MU the tier order is reversed.
- **Planned vs exploratory.** One marker (†), defined in 2.3. The full list goes to a supplement section.
- **Ladder.** The middle step's interval includes zero. "Each step raised the AUC" appears nowhere.
- **Combined 0.82 vs planned model.** The displayed combined score (exploratory) is named apart from the planned
  imaging model that missed its pre-specified gain of 0.03.

## New exploratory analyses run during the council

- **e636313**: clinical data alone on LUMIERE, 0.554 (0.458 to 0.635), for Figure 2.
- **ac4d9ae**: MU-fixed agreement medians; coverage by outcome (and Mondrian); enhancing-volume baselines; operating
  point at the MU median; CI for the ladder's middle step; external calibration (UCSF was the planned secondary).
  Results are in NUMBERS.md section 12 and SYSTEM_RESULTS.md.

## Decisions that need you

1. **Abstract.** Approve or edit the proposal in main.tex (149 words, flagged). It replaces the abstract in LOCKED.md
   (2026-10-24), which predates the external tests. Nothing changes in LOCKED.md until you approve.
2. **Abstract scope.** It has no clause on the risk scale (calibration) and no scope limit, for lack of words. The
   0.71 (MU image pathway) comes from an exploratory model and is not marked in the abstract.
3. **Split variance.** At present it is one paragraph in Methods 2.3 plus Supplementary S8 / Figure S2 (OUTLINE
   decision 14). The alternative is a short Results section.
4. **Agreement rule.** At present the system uses medians fixed on MU, with the planned own-median result reported
   first. The alternatives are to keep each cohort's own medians as the system rule (the planned one, not computable
   at one scan) or to drop the warning from the external claims. Neither rule is claimed to generalise.
5. **Reviewer items rejected that you might want back:**
   - the editor's "not powered for 0.03" sentence (skipped: no power calculation in the sources);
   - the Introduction sentence on the schedule finding and the split-variance clause there (skipped for budget);
   - UCSF Q2 (+0.25 for images over clinical data) in the text, now only in Table 2;
   - "90%" repeated in the Limits;
   - a risk-scale clause in the abstract;
   - the scan-flow figure and a segmentation-quality sentence;
   - the editor's Introduction and Methods rewrites 3 to 8 (not wrong, held back for conservative revision).
6. **Card denominator.** 3.4 now gives 54 of 146 intended-use scans, which is the evaluation set. Round 2 had ruled
   35 of 249, the report scans. Confirm.
7. **Front matter.** Your full name, email and ORCID. Acknowledgements, disclosure, funding, ethics determination,
   data availability (released tables, DOI), code link and tag, notes on contributors. Confirm the generative AI
   declaration (it says Claude wrote and ran analysis code).
8. **Figures to build.** `fig1_system.pdf` to `fig5_report.pdf` do not exist; they render as red placeholders. Their
   inputs are in NUMBERS.md section 11. Figure 2 needs the grey enhancing-volume bar, and Figure 4B needs both median
   rules. The worked example scan could be a panel in Figure 1 or Figure 5.
9. **Supplement sections to write** (each marked `\todo` in main.tex):
   - analyses not fixed in advance (new; the list cut from 2.3);
   - image pathway inputs and their harmonisation;
   - system results (conformal split, coverage by outcome, flag tests for each cohort with both median rules);
   - deviations from the plans;
   - calibration and thresholds;
   - deep networks at MU and UCSF;
   - second report evaluation and model comparison.
   The existing supplement still frames results as v1 / v2 (S7, S21). That conflicts with "final system only".
10. **Tikhonov 2025** (arXiv:2509.06511). It is not in `refs.bib` and not verified; the Discussion has a `\todo`.
    Verify it or cut the clause. The 2025 and 2026 references were not checked against their sources either.
11. **Title.** "PRISM: a modular system for glioma progression surveillance on MRI" (OUTLINE decision 13). Open if
    you want a name change.

## How to revert

- Everything since the skeleton: `git diff backup-before-council-2026-10-26 -- paper/main.tex`. To restore,
  check out `backup-before-council-2026-10-26 -- paper/main.tex`.
- Copies of the skeleton, the supplement and outline draft 3 are in `paper/backup/`.
- Each round is its own commit (hashes above), so you can revert one round with `git revert <hash>`.
