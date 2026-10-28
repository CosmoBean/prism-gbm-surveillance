# Overnight paper pass (2026-10-28)

Goal: a paper a busy clinician-scientist reads start to finish, not an analysis log. Limits: no change to the
argument, outline or any claim's strength; LOCKED text and the proposed abstract untouched; no new numbers beyond
NUMBERS.md; structural ideas go to [OVERNIGHT_PROPOSALS.md](OVERNIGHT_PROPOSALS.md). The pre-pass PDF and source are
in `paper/backup/main_pre-overnight_2026-10-28.{pdf,tex}`.

## Loop 1: figures (commit 37d815e)

All five figures were placeholder charts: hard-coded bars without intervals, captions describing panels A–C that did
not exist. They are now drawn by `scripts/generate_system_first_figures.py` from the aggregate values in NUMBERS.md:
- Figure 1: (A) the system as a data flow, from scan and record to the checked report; (B) the evaluation design
  (MU cross-validation → locked models → LUMIERE and UCSF → 406 reports).
- Figure 2: AUC with 95% CIs by pathway and cohort, with enhancing volume alone as a hatched reference.
- Figure 3: (A) the MU timeline gain across and within phases; (B) UCSF enhancement; (C) the image-model ladder,
  across and within phases, against the timeline.
- Figure 4: (A) coverage by cohort and pathway; (B) agree-minus-disagree AUC, own vs MU-fixed medians; (C) scans in
  a tested situation by cohort.
- Figure 5: (A) the narrative of a report for a **synthetic** scan (the Discussion's eight-weeks-after-radiotherapy
  example; invented volumes, MU's card row), each sentence with the record fields it cites; (B) reports passing the
  check by cohort.

Captions for Figures 1, 2, 4 and 5 rewritten to match the panels.

## Loop 2: notebook residue, repeated caveats, text–table conflicts

Readers: the cold reader remembered 0.82, 0.88 and 406/406, and stated the claim correctly. Its main objection was
that the abstract sells AUCs which page 5 explains as timing (MU) and enhancement-based labels (UCSF). The hostile
reviewer added: project history in the Results; "no clinician" said five times; the perturbation count differed
between the text (28/30) and Table 2 (29/30); "transport" and "transfer" both used; a "set only" cell that was
never defined; and Table 2 running off its page.

Changed:
- Results opener: project history ("the initial radiomics exercise…") replaced by a one-sentence route map.
- Introduction: "the report makes that distinction visible" narrowed to what the report does. The reader caveat
  that was repeated there is gone (it stays in 3.5 and the Limits).
- The end of 3.3 no longer gives a fake reason for the confidence ("because the evidence differs… PRISM attaches");
  it now says what a clinician needs.
- The heading of 3.4 now matches its content (coverage and disagreement, not the report). The stacked hedge on
  coverage is removed.
- 3.5 rewritten: results first, then one sentence on the revision (the failure is still disclosed), then the
  check's scope once.
- Table 2: "transfer" throughout; the perturbation cell gives 28 of 30; "the card's tiers mean something" is now a
  question; the Met cells are shortened and "set" is defined; the notes are cut to half, without file names; the
  table is set in footnotesize so that it fits its page.
- Figure 4's caption no longer repeats "defined after the results".

Left: the abstract (P1), the report's content (P2), the scan-count table (P3), Figure 5B (P4) and the order of the
report figure (P5) are in OVERNIGHT_PROPOSALS.md.

## Loop 3: definitions a reader can follow on first reading

Source: the remaining items from loop 2's reads (sentences the cold reader read three times; terms used before they
were set up; overclaiming verbs in the Discussion).

Changed:
- 2.1: the agreement rule now says first what it is ("both scores above, or both below, their own median on MU")
  and gives the medians' origin in brackets. The card's sentence now says plainly that a scan's own result is in its
  row; this was disclosed before, but it read like leakage slipped in.
- 2.2: the phases of care are given without "84 days, 12 weeks"; the 120-day task is introduced as secondary
  before it appears in 3.1.
- 2.3: one sentence introduces the deep networks and their permuted-label control before 3.3 and Table 2 use them.
- 3.4: the agreement paragraph is reordered: the planned MU result, then the planned external tests (not met), then
  the MU-fixed medians the system uses (†).
- Discussion: "establish transfer of ranking" became "show that the ranking transferred, but the risk scale did
  not"; "runs where data are incomplete" became "can run where treatment dates are missing"; the card's
  no-refitting point is stated as a property of a table; the novelty sentence keeps its hedge and says what the
  combination is.
- Table 1: "index scans" (never defined) became "scans with a 120-day label".

## Loop 4: voice edit and the second cold read

Readers: a new cold reader (remembered 0.82 vs 0.71, 0.77 and 0.88; claim correct, and calibration now noticed)
and a copy editor checking the voice against STYLE.md §6 (25 edits). Most re-reading came from model names (P7) and
the two median rules (P6, a real system–text mismatch).

Changed (voice): the colon reveals and "X is not Y" slogans in the Introduction; "PRISM is that system."; the
Results route map and the 3.2→3.3 seam ("we audited…" twice); the signposts closing 3.3 and 3.4; "fixed in advance"
→ "planned" in prose (kept in the dagger definition and Table 2); "frozen" and "second evaluation"; sentences with
three or more qualifying clauses split in 2.1, 2.2, 3.2, 3.4 and 3.5; the risk-scale caveat is stated twice (3.2,
Discussion ¶1), not three times; "no clinician has read" stays in the Limits only.
Changed (clarity): within-phase AUC defined in 2.3 (pairs from the same phase); 3.3 and 3.4 paragraphs open on their
findings; Figure 4B's MU rows labelled (the system's rule on MU uses the other folds' medians); Figure 4C says no
scan was untested; Figure 5A uses the reports' real sentence forms.
Kept against the editor: the intended-use 0.60 stays in the Discussion (STYLE.md §4 requires it there and in 3.1).

## Loop 5: the cold reader's remaining confusions

Changed: the UCSF label definition in plain words (one negative clause, the same meaning); the third step of the
image-model ladder is identified as the planned imaging model's image inputs without its timeline, which explains
why Figure 3C (0.81) differs from the planned model (0.84); the Figure 2 caption explains the UCSF-trained
clinical-only bar below 0.5; Figure 1B gives the report counts by cohort (130 UCSF second scans against 69 in the
detection set). Checked P6 against the code: the report medians are taken over each cohort's own evaluation scans
(`prism/analyses/system.py`, `derive`).
