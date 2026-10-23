---
name: paper-writing
description: Write or edit the PRISM manuscript (paper/main.tex, paper/supplement.tex) as a persuasive scientific argument rather than an analysis report. Use whenever drafting, restructuring, rewriting, tightening or reviewing any part of the paper - title, abstract, introduction, results, discussion, captions, tables - or when deciding which results belong in the main text versus the supplement or the reviewer reserve.
---

# Writing the PRISM paper

The manuscript is an argument. The analysis documents in `docs/results/` are the notebook. Never transcribe the
notebook into the paper.

## Before writing anything

Read, in this order:
1. `docs/manuscript/STYLE.md`: the rules (the models, the claim, the 80 / 20 disclosure rule, numbers, prose,
   section recipes, the author's recorded reactions in section 10).
2. `docs/manuscript/OUTLINE.md`: the current argument spine. If the requested change conflicts with it, raise that
   with the author before writing; do not drift the story silently.
3. `docs/manuscript/RESERVE.md`: what is deliberately left for reviewers, and the answers.
4. `docs/manuscript/JOURNAL_RULES.md`: the journal's hard constraints (abstract ≤ 150 words, ≤ 3 keywords,
   British -ise, back-matter order).

## Workflow

Work in layers and settle each with the author before the next: outline → skeleton (first sentences only) → prose →
polish. Do not polish prose whose outline is still moving.

When writing prose:
- Start every paragraph with its claim. One idea per paragraph. Caveats after the claim they qualify, once.
- One number per claim; intervals on the headline numbers only; never the same number twice across text, tables
  and captions; plain names instead of model codes.
- Apply the 80 / 20 test to every sentence: does the reader need this here to follow or believe the argument? If
  not, move it to the supplement and log it in RESERVE.md.
- Never drop an item on STYLE.md's "always in the main text" list. Selection, not concealment.

## Before showing a draft

Run the tests in STYLE.md section 8:
- first-sentence test (do it yourself);
- cold-reader and hostile-reviewer reads (spawn agents that have no project context; give them only the PDF text
  or the section);
- number audit against the source documents;
- integrity check.

Report briefly what the tests found and what was changed.

## After the author reacts

Record each reaction as a dated one-line rule in STYLE.md section 10. If it changes the story, update OUTLINE.md.
Standing project rules still apply: rebuild and commit `paper/main.pdf` after every change to the paper; atomic
commits on `manuscript-week`; no Co-Authored-By line for Claude; never call PRISM "published".
