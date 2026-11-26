# Brief for rewriting one block of Methods (PRISM paper, 2026-11-20)

The author rewrote the abstract and the Introduction with Claude, line by line. Apply the same standard to your block
of Methods. The finished Introduction (`paper/main.tex`, from `\section{Introduction}` to `\section{Methods}`) shows
the target voice: read it first.

## What the author asked for, again and again
1. **Direct and plain.** State the claim first, in simple words. No filler, no throat-clearing, no rhetorical
   flourish, no defensive tone, no stacked hedges. Prefer a short declarative sentence.
2. **One idea per paragraph, and the paragraphs flow.** Each paragraph opens with its point. Its last sentence leads
   naturally into the next paragraph (or the next block).
3. **Every sentence must earn its place.** For each sentence ask, as the author does: "What is the author trying to
   tell me by revealing this?" If the answer is unclear, either state the purpose or cut the sentence. Watch for:
   - facts that are dropped in with no stated purpose;
   - repeated points;
   - detail that belongs in the supplement.
4. **Explain the technology effectively.** This is Methods, so be technically exact: name the method, model, software,
   parameter and rule. But say in one plain clause what each one does before or as you name it.
   - Example from the Introduction: a conformal set became "the outcomes it cannot rule out (progression, no
     progression, or both), chosen so that they include the true outcome for 80% of scans".
   - Avoid unexplained coinages and private jargon, such as "pathway", "reduced form" with no explanation, "card"
     before it is explained, or "locked".
5. **Connectives only when the logic holds.** Use "therefore" only for a true consequence. Leave out "likewise",
   "notably", "importantly" and similar words; the reader can make the inference.
6. **No timing argument in Methods.** What the ranking rests on (timing against images) is a Results finding. Methods
   only describes the reference model and the AUC split as tools.
7. **Accuracy:**
   - **Method statements** must match the code (`prism/`), `docs/results/*.md` and `docs/manuscript/NUMBERS.md`.
   - **Numbers:** check every one you keep against those sources.
   - **Citations:** every citation in your block must say what the sentence claims. Check each against the source
     (Crossref, the DOI, PubMed or the arXiv abstract), as the Introduction's references were checked
     (`docs/review/refcheck/RESULTS.md`), and fix the wording where it overstates.
   - **Unverifiable claims:** flag them; do not invent.
8. **Keep relevant content.** Do not make the paper short for its own sake. Move to the supplement only what a reader
   of the main text does not need, and write `\todo{SUPPLEMENT: ...}` where it would go.
9. **Terms used across the paper:**
   - "time-and-enhancement model";
   - "without retraining";
   - "the masks supplied with each dataset";
   - "clinical-history model", never "timeline";
   - never "agent" for PRISM's language model;
   - never "novel", "first" or "state of the art";
   - British spelling.
10. **LaTeX:**
    - Keep every `\label`, `\ref`, `\citep` key, figure and table environment, and `\todo`.
    - Do not change figure and table environments except for wording in captions that the same rules require.
    - The output must compile in `paper/main.tex`.

## What to return
- **REVISED:** the full revised LaTeX of your block, in one fenced block, ready to paste in place of the original.
- **CHANGES:** a short list of what changed and why, one line each.
- **CHECKS:** each citation and each number you verified, with its source. Mark anything you could not verify.
- **QUESTIONS:** anything only the author can decide.

Do not edit `paper/main.tex` or any other file. Another five reviewers are rewriting the other blocks at the same
time.
