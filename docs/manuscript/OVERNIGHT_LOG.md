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

## Loop 6: number audit and a third hostile read

Number audit (every number in the text, tables, captions and figure generator against NUMBERS.md): all figure
values matched. Fixed: "at LUMIERE only the combined score did better than [enhancing volume alone]" was wrong (the
timeline at 0.69 also did); missing daggers on enhancing volume alone (3.3, Discussion); the ladder's middle-step
interval had lost its sign (now −0.003 to +0.106); "the same AUC" for the all-glioma fit became "almost the same
(0.77)". The LUMIERE AUCs 0.89 and 0.67 (MU-fixed medians) were not in NUMBERS.md; they were verified in the
aggregate CSV and added to NUMBERS.md 12A. MU age (P8) and the Tikhonov detail (P9) were left for the author.

Hostile read, fixed: Table 1 now says LUMIERE records days from surgery (used by the reduced timeline); the card's
three tested LUMIERE situations are explained (no phase recorded, so they differ by enhancement only); the deviation
promised in 2.3 is now stated there; the conformal-set flag's results are given in 3.4 (it met one planned test at
each external centre); unquantified claims now carry numbers (matched-removal gain 0.08, 0.05–0.12; MU coverage by
outcome 82% and 83%; the paired transfer difference of the change inputs, −0.07, −0.13 to −0.01); "the risk scale did
not transfer" is now limited to UCSF (it was calibrated at LUMIERE); "no measured basis" became "too few tested
cases"; the claim that the Discussion's PRISM "ran without treatment dates" became "without full treatment dates";
the Figure 3 caption no longer calls the planned UCSF AUCs exploratory. Figure 1: the combined score is labelled as
one model on both inputs, and the MU box says that the locked models were fitted on all 181 grade 4 scans. Figure 4:
the threshold label no longer collides with a bar.
Left: P10 (the label-circularity caveat in the Conclusion).

## Loop 7: my own whole read after six loops of edits

First-sentence test passed: read alone, the paragraph openers give the argument. Two small breakages from earlier
loops were fixed: an ambiguous "They" in the Introduction, and in 3.4 "the rule then flagged…", which after loop 6
referred to the wrong rule (now attached to the MU-median rule, before the conformal-set sentence).

## Loop 8: fresh cold and hostile reads (convergence check)

Cold reader: "Methods, 3.1–3.3 and the Discussion now read as an argument; 3.4 is still a log", scored 7/10. Hostile
reader: most numbers agree; the flag evaluation is the remaining presentation risk (P11).

Changed: 3.4 split into a planned-result paragraph that opens on the plain finding ("marked the less accurate scans at
MU but not, under the planned rule, at the external centres") and a † paragraph for the MU medians the system uses
(now with the LUMIERE removal gain, 0.12, 0.05–0.19, against random removal, so footnote a's "both tests" is
visible in the text); coverage by outcome in one sentence; the conformal-set flag result is stated for all three
cohorts; the 2.3 deviation, the ladder's third step and the card's tested situations are split into readable
sentences; the term "planned imaging model" is no longer used before it is defined; the 3.3 closing signpost is cut;
the 3.4 heading uses the figure's wording ("less accurate"); LUMIERE's clinical-only result is marked †; "transferred
less well" is qualified by "with coefficients fitted on MU"; "measurements added little" became "added little that
this sample could detect"; in Table 2 the coverage cell says "not for every outcome" and the training-at-UCSF cell
names both image models; Figure 1B says "406 reports".

## Loop 9: last cold read; stopped here

The cold reader again scored the paper 7/10 ("reads as an argument… 3.4 is still a log of medians, rules and
tests"), the same as loop 8, so the sentence-level gains have levelled off. What remains is structural (P1 abstract,
P6/P11 flags and medians, P7 model table) and needs the author. Loop 10 was not run.

Changed: the MU-median paragraph now opens on its finding; the deviation, the UCSF combined-score caveat and the
card's tiers are split into plain sentences; the card sentence says why a scan's own result is in its row (the card
is a record of measured results); the ladder paragraph opens on what it showed; the Figure 3 caption describes
panel B as drawn; the Figure 5 caption names the card's population.

## Morning summary

- 9 loops, 9 commits on `manuscript-week` (37d815e → this one). Pre-pass copy: `paper/backup/main_pre-overnight_2026-10-28.{pdf,tex}`.
- Readers: 4 cold reads (loops 2, 4, 8, 9), 3 hostile reads (2, 6, 8), 1 voice edit (4), 1 number audit (6).
  Cold-reader recall moved from "felt misled" (loop 2) to a correct claim with the right numbers and 7/10 "reads
  as an argument" (loops 8–9).
- Unchanged by design: the abstract (verified identical), LOCKED.md, the argument and outline, every number's
  source. One number was added to NUMBERS.md (LUMIERE 0.889 / 0.667, from the aggregate CSV).
- Two wrong statements were found and fixed (LUMIERE baseline sentence; Table 2's 29/30). One system–text mismatch
  was found and not fixed (P6: the reports use each cohort's own medians, while the text says MU medians).
- Decisions for you: OVERNIGHT_PROPOSALS.md, P1–P11. The most important are P1 (abstract), P6 (medians) and P11
  (flag grid).

# Second pass (2026-10-28, author: "concise and right, not just look right"; figures in the text)

Pre-pass copy: `paper/backup/main_pre-loop10_2026-10-28.{pdf,tex}`. Author direction recorded in STYLE.md §10.

## Loop 10: figures in the text, the concise rewrite, the score table, the median fix

- Floats: figures and tables now sit after the paragraph that first cites them (no "Tables" / "Figure legends"
  sections); figures enlarged; 17 → 14 pages.
- Concision: main text 3,867 → 2,736 words (−29%). Every section was rewritten from its findings; the "always in the
  main text" items (STYLE.md §4) were kept: intended-use 0.60 (3.1 and Limits), the timing baseline, the
  within-phase result, the planned/† marking, the scope limits, the results that fail (planned flag tests externally,
  the report's first failure).
- P7 done: new Table 1, "The scores in this paper" (inputs, dates, planned or †), so the prose names each score once.
- P6 fixed in the text: the evaluated system and the reports place each pathway score against the median of its own
  cohort's evaluation scans (`prism/analyses/system.py`, `derive`); the text had said the system uses MU medians.
  Now 2.1 says so, the MU-median rule is the exploratory variant, and 3.4, Figure 4B and the Table 3 note follow.
  **This weakens one sentence** (the LUMIERE agreement result is now plainly exploratory), so check it.
- Captions rewritten at about half their length; Figure 5's title is now "What the clinician receives, and the check".

## Loop 11: validation of the rewrite (integrity audit, cold read, hostile read)

Audit (old vs new text and NUMBERS.md): every number correct; 18 items fixed. These were lost qualifiers ("an
interval that included zero", "point estimates", "re-selected and re-tested", "segmentation" in elyassirad2025,
"preoperative and postoperative MRI" in chen2026), lost content (the locked models' training set, 181 grade 4
scans; external CIs; caption clauses), missing daggers (Discussion ¶1, Figure 4C, Figure 5B), and two claims made
stronger in the rewrite (the 3.5 heading, now "After one revision, every report passed…"; the novelty sentence,
whose condition was restored).
Cold read: 7/10 article, 6/10 concise. Too-compressed spots were expanded (the UCSF positive, why MU medians are
needed, why a scan's own result in the card is acceptable). Overlong sentences were split (3.2, 3.4 coverage). The
3.4 heading was shortened.
Hostile read: the planned-or-post-hoc status of the agreement rule is now consistent. The flag and its tests were
planned and the median rule was written down later (2.3, Table 3 note, 3.4). Overclaims were calibrated: "keeping
the pathways apart does" → "the separate pathways and the audits of 3.3 can"; UCSF "scores well largely by agreeing"
→ "can score well there by tracking enhancement"; "the clinician sees" → "the report states"; the card "is designed
so that" a cohort adds rows. One Limits sentence now says which parts of the confidence held externally (only
average coverage). The Conclusion now carries the cohort finding. The locked combined model's MU cross-validation
AUC (0.80) is now given, so "applied unchanged" is checkable.
Figure 5B replaced (P4): the reports passing the check for seven local models with the same prompt; the two largest
dense models pass in every cohort.
Supplement: two "main Table 1" references now point to Table 2 (cohorts). The supplement's other cross-references
were already stale (old "M2.x" numbering); see P12.
Main text: 2,898 words (loop 10: 2,736; before the second pass: 3,867).

## Loop 12: the impact edit

An editor-in-chief read marked the ~100 words that carry the paper and proposed a further 15% of cuts. They were
applied, with three changes: numbers that had no interval got one (clinical alone 0.53, 0.45–0.61; MU combined
0.82, 0.74–0.89; UCSF reduced timeline 0.56, 0.42–0.69; Limits 0.60, 0.52–0.69) instead of being cut; the locked
model's MU cross-validation AUC stays (0.80, 0.73–0.89); and the fitting details (ridge, missing values) moved into
Table 1's caption rather than out of the paper. Cut: sentences that repeated Table 1 or Figures 1, 2 and 5 (input
lists, LUMIERE pathway AUCs, enhancing volume at MU and LUMIERE, the card's "1 of 9" in the Discussion); the
recalibration implication in 3.2 (the Discussion carries it); restatements of the UCSF label point; and the
Discussion's opening design restatement (the Conclusion carries it). Reordered: 2.3 now opens with the locked
models and the plans; the within-phase definition moved to where it is first used (3.3); in 3.3 the UCSF rating
comes before the 0.88 it explains; the Discussion's second sentence states the thesis. MU disagreement is now the
planned statistic with its interval (0.31, 0.18–0.43) rather than two AUCs without intervals.
Main text: 2,511 words (start of the second pass: 3,867; −35%).

## Loop 12b: figure redraw after a design review

A figure designer reviewed the five PNGs, and the script was revised to its list, with no data changed. All
figures are now 7.2 in wide and saved as drawn, with no text under 6.5 pt and the same panel-letter style. Figures 2
and 4A are now points with intervals on a marked axis; bars starting at 0.3 had exaggerated the gaps. Figure 2 makes
the combined score primary and shades "UCSF trained there" as a reference. Figure 1's boxes are a name plus one
line, with no overflow. Figures 3A and 3C use the same filled/open encoding (across/within phases). Figure 4A shows
the nominal 0.80 beside the 0.78 threshold. Figure 5B uses ink colours, since orange means "combined score"
elsewhere. Captions for Figures 2 and 4 were updated.

## Loop 13: validation after the impact edit (audit, cold read, hostile read)

Hostile verdict: minor revision. The one reason was inconsistent dagger labelling of the disagreement result. Cold
read: 7 article, 6 concise, 7 figures; several cuts had gone too far.
Fixed:
- The audit found no wrong numbers, but it did find lost disclosures and meanings that had shifted. The deviation
  says what it was again; the UCSF paragraph states its claim again; "every report passed" now names Qwen3.8-27B,
  since smaller models did not (Figure 5B); MU and LUMIERE enhancing volume (0.62, 0.66) are back as the cohort
  contrast; coverage is "uneven at the external centres"; Gomaa's fusion paper is described accurately; the Intro
  says "mostly" again.
- Daggers: the card in 2.1, the MU timeline audit, the UCSF rating, the MU disagreement result (its median rule was
  post hoc), and the exploratory points listed in Figure 2's caption.
- Hostile read:
  - The conformal model is said to be refitted on 70% of MU and calibrated on 30%, which answers "calibrated on
    patients it was fitted on?".
  - The within-phase comparison is said to come mostly from the later phase (56/32).
  - Figure 2 explains the full and reduced combined forms and the UCSF-trained clinical point below 0.5.
  - "Untested: none" is now in the text and Figure 4C.
  - The perturbation test says what was perturbed.
  - Table 3 names the image pathway in the +0.248 row.
  - The Discussion's UCSF claim now cites evidence instead of an inference.
  - Coverage is given "on point estimates".
  - The Discussion no longer says "and so" between disagreement and the card tier.
- Too-compressed spots from the cold read were expanded: the deviation, "external form" (now "reduced form used
  externally"), the tiers, and why the UCSF scan interval matters ("carries the schedule rather than the tumour").
- Layout: float pages are aligned to the top.
Main text: 2,706 words. That is up from 2,511 because clarity and disclosures came back; it is −30% from 3,867.

## Loop 14: voice, clinical wording and statistical wording

Readers: a copy editor (20 voice edits), a neuro-oncologist (clinical wording; the takeaway "PRISM shows separately
what the scan and the treatment calendar say, and states when it has not been tested on cases like this one") and a
statistically literate referee (minor revision; the reason was the planned-or-post-hoc wording of the disagreement
rule).
Changed:
- The disagreement rule is settled once (2.3): the flag and its tests were planned, but the median rule was written
  down after the results had been seen, so every disagreement result carries a dagger. "Under the planned rule" is
  gone from 3.4, the Discussion and Figure 4B; the legend reads "own medians†" and "MU medians†".
- Statistical wording: every "about the same", "did not raise" and "did not correct" now has its number. These are
  MU combined vs timeline −0.001 (−0.05 to +0.05); UCSF single scan trained there 0.03 (−0.05 to +0.12); LUMIERE
  calibration O/E 0.97 (0.81–1.14); per-outcome calibration non-progression coverage 51% (39–64%) at LUMIERE and 18%
  (6–31%) at UCSF, which suggests the external scans are not exchangeable with MU's; MU Brier 0.22 vs 0.15. Overlap
  of intervals is no longer used as an argument. "At least as well" became "as high a point estimate". "About as
  much" became "no difference detectable". "Most of the advantage lay between phases" became "the gain appeared
  across phases but not within them". "Measurements added little" became "this sample cannot show whether…". "So
  carries the schedule" became "an input that reflects when scans were taken". The card's MU reversal is "possibly
  because". The heading of 3.4 now says "on point estimates".
- 3.5 gives the 220 by cohort (71, 19, 130). The check "confirms that a report matches its record; it cannot judge
  emphasis, what a clinician would infer, or whether the segmentation is right" (clinician).
- Clinical wording: "the volume of enhancing tissue" and "change in enhancing volume" replace "how much the tumour
  enhanced" where the text describes the evidence. Figure 5A now carries the report's real "each score… is not a
  calibrated probability for this patient" sentence, because the clinician read the scores as probabilities.
  Suggestions that would add RANO were not taken (project rule). The report's own wording in Figure 5A was kept,
  because it is the system's output format.
- Voice: colon reveals, triplets and stacked clauses were split in the Introduction, 2.1, 2.3, 3.2–3.5 and the
  Discussion. Section 3.3 and Figure 3 now say concretely what drove the scores ("followed the treatment schedule
  at MU and enhancement at UCSF") instead of "what carries a score".
Main text: 2,813 words.

## Loop 15: validation of loop 14 (audit, cold read, hostile read)

Cold read: 7 article, 6 concise, 7 figures; 3.2 and 3.4 still stacked secondary contrasts. Hostile: minor revision
(missing daggers on disagreement results; causal phrasing). Audit: every number correct; 11 fixes.
Changed:
- 3.2 and 3.4 trimmed harder. Secondary contrasts now live in Table 3 and Figures 2 and 4: the single-scan change
  when trained at UCSF, the share flagged by MU medians, the conformal-set flag, and the Brier details. The text
  keeps the planned results, the failures and one line per exploratory result.
- Daggers are on every disagreement result (Table 3 rows and Met cells, 3.4, Limits) and on the 3.1 between-phase
  statement and the Discussion's enhancing-volume point.
- Causal wording calibrated: "partly because the interval…" became "part of its AUC tracks the interval…"; "so its
  change inputs transferred less well" became the difference itself (−0.07, −0.13 to −0.01); "the audits showed it"
  became "did"; the Conclusion no longer gives a post-hoc finding as the design reason.
- The per-outcome calibration result is now the honest one: it left non-progression coverage below the threshold
  even on MU (73%, 63–82%). The overreaching "not exchangeable" inference is gone.
- The deviation is checked on the right terms (all-glioma fit 0.768 vs 0.773 at LUMIERE; at UCSF the all-glioma
  models were tested on all-glioma scans). The reduced combined form on MU is marked planned. LUMIERE enhancing
  volume names its scan set. The 3.2 heading and Figure 2 title name the combined and image models; the reduced
  timeline at UCSF did not rank well. "Smaller models did not" became "only Gemma-4 31B also did".
- Figures: the Figure 4B legend moved below the axis, with the dagger in the caption; Figure 5B weights to one
  decimal.
Main text: 2,725 words.

## Loop 16: structural concision (a structure editor's plan)

The diagnosis was that the paper said status, results and definitions three times each. Applied:
- **Lean Table 3.** It is now a verdict register: question, rule, outcome, with Yes/No first. The three
  descriptive rows went to the figures and the supplement. Every failed planned test is still there, including the
  first report evaluation ("every LUMIERE report failed"). The notes went from about 120 words to 50.
- **Results 3.1 and 3.2 merged** into one subsection, "The timeline led at MU, and the combined and image models
  transferred without refitting". The forward pointer is gone, and Results now run 3.1–3.4.
- **Reference-only numbers moved to Figure 2**: enhancing volume at MU and LUMIERE. The card's Brier detail moved
  to the supplement.
- **The deviation is one disclosed clause** (it changed the LUMIERE AUC by less than 0.01).
- **The Discussion opener** no longer re-runs the Results.
Not applied: the proposal to signal exploratory status only by paragraph-level grouping or figure markers. It would
weaken "marked at first appearance", so the daggers stay.
Main text: 2,642 words; Table 3 about half its former length.

## Loop 17: validation of the structural edit

Cold read: 7 article, 7 concise (up from 6), 8 figures (up from 7). Hostile: minor revision. Audit: every number
correct, including each cell of the lean Table 3; 9 fixes.
Changed:
- **Restored a planned result that partly contradicts the claim** (STYLE.md §4): over all scans of all gliomas the
  planned imaging model gained +0.041 (+0.006 to +0.081). It is now in the Table 3 note.
- **Table 3.** The single-pathway coverage failures are back in the coverage cell (images at LUMIERE 0.708,
  timeline at UCSF 0.696); the deep-network control reads as valid; the section heading no longer calls fine-tuned
  networks "locked"; the +0.248 row names the locked comparison; the report rows point to 3.4 instead of repeating
  counts.
- **Statistical wording.** "Calibrated in the large" became "no detectable miscalibration in the large"; "less
  accurate scans" became "scans the combined score ranks less well"; the MU coverage interval also reaches below
  the threshold, which is now stated; the per-outcome MU result is a point-estimate shortfall only. One sentence
  discloses that the MU intervals do not include refitting variance. The LUMIERE gain over the timeline has its
  interval, 0.08 (−0.01 to +0.16), instead of pointing to a figure that does not show it.
- **Calibrated claims.** The Introduction names the combined and image models; UCSF labels "coincided with" a rated
  increase in enhancement; the audits "suggested" what a model used, and the pathways "put it in front of the
  clinician"; "whatever a cohort holds" became "given scans and masks". The Limits now say the deployed disagreement
  rule needs a batch of scans and the single-scan version is exploratory. The report-model comparison discloses that
  the prompt was revised for Qwen3.8-27B.
- The 3.1 pointer to the between-phase result is restored with its dagger; the orphan label was removed; the Figure
  4 caption carries its dagger; the Figure 5B key explains the light bars.
Main text: 2,759 words.

## Loop 18: convergence check, then the last fixes

Cold read: 7 article, 6–7 concise, 8 figures (stable over loops 17–18). Hostile: minor revision; the one remaining
reason was scope wording ("the scores" or "PRISM's models" where the evidence covers specific models). Audit: every
number and dagger correct; every STYLE.md §4 item present, each listed with its location in audit_loop18.md.
Changed: scope words name the models ("combined and image models"; "the timeline and combined scores … the image
scores"); the 3.1 between-phase sentence now says the within-phase gain "was not detectable, although its interval
cannot exclude a gain as large as the overall one"; the Limits no longer suggest that the cohort-median rule was
planned; Table 3 asks "Does the combined score rank flagged scans less well?" and defines the all-grade secondary
population; the conformal-set flag result is back in 3.3; the card comparison says LUMIERE yes, MU no; "PRISM has too
few tested cases" became "the evidence PRISM holds for this situation is too thin"; the Conclusion no longer repeats
the Discussion's phrase; small fixes to the Figures 3 and 5 captions.
Stopped here: three successive reads are stable and the remaining points are wording. Figure 5A's sentence "how
closely they resemble the progression scans" was kept, because it is the system's real report sentence.
Main text: 2,794 words.

## Summary of the second pass (loops 10–18)

- Figures and tables sit in the text after their first mention. The figures were redrawn after a design review
  (honest axes, one canvas width, consistent panel letters, readable print sizes). Figure 5B now shows which local
  report models pass the check.
- Main text 3,867 → 2,794 words (−28%). It reached 2,511 and was allowed to grow back where readers could not follow
  or a disclosure had been lost. The paper is 17 → 15 pages; Table 3 is about half its former length.
- New Table 1 names every score once (P7). The agreement-rule wording matches the evaluated system (P6). The rule
  status is consistent: the flag and its tests were planned, the median rule was post hoc, and every disagreement
  result carries a dagger.
- Every kept number has its interval; loose wording ("about the same", "did not raise", "calibrated", "at least as
  well") was replaced by the numbers. Two planned results that a cut had dropped were restored (+0.041 over all
  gliomas; the single-pathway coverage failures).
- Readers across both passes: 8 cold reads, 7 hostile reads, 5 integrity or number audits, 2 voice edits, 1
  clinician, 1 impact editor, 1 structure editor, 1 figure designer. Cold scores ended at 7 article, 6–7 concise, 8
  figures; the hostile verdict moved from a long list to minor revision on wording only.
- Still for the author: P1 (the abstract; a 150-word draft is in OVERNIGHT_PROPOSALS.md), P8 (MU age 62.5 or 62),
  P9 (Tikhonov reference), P10 (the Conclusion's label caveat, now partly carried), P12 (supplement
  cross-references), and RANO in the cited LUMIERE paper's title (a citation; your call).
