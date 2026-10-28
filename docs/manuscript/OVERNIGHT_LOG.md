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
