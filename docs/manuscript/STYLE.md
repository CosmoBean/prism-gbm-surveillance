# How we write the PRISM paper

The current rules for `paper/main.tex`, consolidated on 2026-11-19. Only rules that hold now are here. Superseded
directions are listed once in section 9 so they are not reintroduced, and their full history is in git (this file
before consolidation: commit e647e79). When the author reacts to a passage, add the lesson to section 10, and fold it
into sections 1–8 when it settles.

**The one sentence to remember:** *elegance comes from the arrangement of ideas, not the sophistication of the
vocabulary.*

---

## 1. What the paper is

- **One system, one argument.** The paper presents PRISM, a local system for glioma follow-up MRI, as one argument. It
  is not an analysis report, a set of separate techniques or a version history. The analysis documents in
  `docs/results/` are the notebook; never transcribe the notebook into the paper.
- **Title:** "PRISM: an auditable local system for glioma follow-up MRI".
- **The spine** (the locked abstract, LOCKED.md) runs in this order:
  1. the premise: a score is useful only if the reader can see what it rests on, and a report only if it can be
     checked;
  2. PRISM, built for both;
  3. what the separation exposed: timing and the enhancing tumour carry most of the ranking, with no clear gain over
     the timing-and-enhancement baseline;
  4. locked transfer to LUMIERE and UCSF-ALPTDG;
  5. reports checked against the record, and the verifier.
- **What PRISM is, not only what it does** (the PI). PRISM is a local software system rather than a new model: a
  chain of deterministic stages around one language model, centred on the scan's record. Every value sits in the
  record under a fixed key with its source.
  - The language model is one writing step: schema-constrained, with no tools and no images.
  - Never call it an "agent" or "agentic", and never propose a multi-agent "council" (evidence:
    `docs/review/SIMILAR_SYSTEMS.md`).
  - Say "system", not "framework" or "pipeline".
- **Auditable** is defined once, in the Introduction: each score's inputs are reported separately, and every number
  in the report is traced to its entry in the record and checked automatically. It is used as defined after that.
- **Best foot forward.** Lead with what PRISM does, with moderate claims. Present the difficulties of follow-up data
  as known challenges, each paired with the part of PRISM that handles it. Do not accuse the field.
- **Against precedent, not novelty.** State each contribution against its nearest precedent, cited by name. Claim
  combinations and measurements, not components. Use the field's own terms. Never "first", "novel" or "state of the
  art".
- **Cross-site validation is featured.** The models were fitted once on MU-Glioma-Post and applied unchanged. Claim
  transfer, not better performance.
- **Clinical benefit** is answered with measured proxies only: what a score adds over timing and visible
  enhancement. "Clinical decision support" appears only as the intended use ("a system intended for clinical decision
  support"). A clinical reading of the reports is left to future work.

## 2. Names and terms

| Use | Never |
|---|---|
| clinical-history model; reduced clinical-history model | timeline model, timeline pathway, timeline score |
| imaging model; combined model; "model" for each | pathway |
| timing-and-enhancement baseline; clinical data alone; enhancing volume alone | model codes (B1, R2, I2) in the main text |
| time after radiotherapy; time window | phase, phase of care |
| MU-Glioma-Post, the public development cohort | the development centre |
| auditable; every value has a source and is checked | interpretable, explainable; LIME or SHAP |
| what the checker and the verifier catch, and what they miss | faithful (of the reports) |
| progression was recorded at a scan (narrative); the exact label definition (Methods) | diagnostic claims |
| PRISM (the author's own, unpublished system) | "published" PRISM; "the published approach" means Christodoulou et al. only |
| indicative volumes | any RANO category assigned, applied or implied by PRISM |
| system; record; report; writing step | agent, agentic, council, framework, pipeline |

- **RANO** appears only in the Introduction's literature review, as other people's criteria. PRISM never applies,
  assigns or names a RANO category in the methods, figures, tables or reports.
- A 27-billion-parameter model runs on a laptop. Do not present local model size as a barrier to deployment.
- **Words to avoid** unless the paper demonstrates them: novel, unique, powerful, robust, comprehensive, seamless,
  transformative, sophisticated, state-of-the-art, clinically actionable, real-world, scalable, end-to-end,
  leverage, unlock, harness, empower. Use the concrete fact instead: "passed the record check", not
  "hallucination-free".
- **Hyphens** only in formal names, abbreviations, identifiers and terms that lose their meaning without one. Keep
  one construction throughout.

## 3. What to show: the 80 / 20 rule

The main text shows about 80% of the story, everything a reader needs to follow and believe the argument. About 20%,
the detail behind each step, is left for reviewers in [RESERVE.md](RESERVE.md), with its answer ready. This is
selection, not concealment.

**Always in the main text:**
- the time-and-enhancement model, next to any model that uses timing;
- the contribution of each group of inputs to the score (share of the score, fall in AUC when left out);
- the planned tests and their outcomes (Table of planned tests), stated neutrally and framed by the argument;
- which analyses were planned and which exploratory, in one word where it applies. A pass rate measured after a
  revision prompted by evaluation failures is called exploratory;
- the scope limits, stated once and plainly: one public development cohort, a documentation-based label, and no
  clinician has read the reports (future work).

**Never in the paper:**
- commentary that argues against our own claims ("cannot show", "a defect", "part of the AUC comes from …");
- exploratory negatives on superseded pipelines. They go to the supplement or out;
- project history: versions, earlier prompts, rule revisions. Development history is stated once, in Methods, and
  never in the abstract or a heading;
- method statements that do not match the current code. Check against the code, not an older audit.

**The abstract** carries no radiomics comparison. It holds one or two numbers per claim.

The test for every sentence: *does the reader need this here to follow or believe the argument?* If not, move it to
the reserve, or cut it. Every result in the main text must answer "so what?".

## 4. Numbers

- One number per claim in the prose. Give intervals for the headline numbers only.
- Never give the same number twice across the text, tables and captions. Decide where each number lives.
- Give a number once the reader knows what it would mean. Contrasts beat levels.
- Two decimals in prose; three in tables only when the differences are small. No p-values where an interval says the
  same.
- Give each count its scope (cohort, evaluation, comparison).
- AUC measures ranking; the separate scores show what the ranking rests on. Present the two as complementary. Never
  say that the AUC "hid" something.
- Ranking language belongs to the evaluation. When the Introduction explains what a score is for, it describes a
  single scan.

## 5. Prose

**Register.** Write elegant British prose for a methods and medical AI journal: the voice of a scientist explaining
to a colleague what they did and found. It should read as a polished article, not a results log. Use British
spelling with -ise.

**Paragraphs**
- Every paragraph starts with its claim, so a reader of first sentences alone gets the whole argument.
- One idea per paragraph.
- A caveat comes after the claim it qualifies, once, where it applies.
- State the general problem before PRISM's response to it.
- Introduce a clinical term through the problem it names, then give its label.

**Sentences**
- Plain words and the active voice. Use "we" and the past tense for what we did, the present for what is true.
- Use concrete subjects (patients, scans, models, records, reports), not "the evidence" or "the story".
- Carry the reasoning with ordinary connectives (because, so, which suggested).
- Let sentence length follow the thought.
- Do not write as if defending every sentence. No staged definitions and no stacked hedges.
- Avoid Claude's default voice:
  - "X, not Y" slogans;
  - staccato announcements;
  - abstractions as subjects;
  - colon reveals;
  - triplets;
  - quotable closing lines.
- Use no intensifiers or signposts (notably, importantly, crucially, it is worth noting).
- Do not arrange prose with colons or semicolons. Use a full sentence, a comma or a parenthesis instead.
- Ask few rhetorical questions, or none.
- State a fact the reader needs inline, in one clause. Do not leave "see Supplementary section" placeholders.

**Revising**
- Revise conservatively. Change the sentences that are wrong and keep the ones that work.
- Preserve the actor, action and object the author liked. Never substitute a shorter but vaguer claim.

## 6. Sections

- **Title:** short. No unneeded adjectives.
- **Abstract** (≤ 150 words, unstructured): locked, and follows the spine in section 1.
- **Introduction** (about seven paragraphs):
  - a real literature review that sets up the abstract's premises;
  - then "We present PRISM", with "auditable" defined and the contributions;
  - the contributions follow the spine: four bullets, each a bold lead-in and one plain sentence, with no numbers or
    section references;
  - then a short paragraph on what PRISM is technically: the stages, the record at the centre, the tools underneath,
    and the nearest systems.
- **PRISM** (Section 2): inputs and measurements, the three models, the record and the report.
- **Evaluation** (Section 3): enough to make the argument checkable, in the order the Results need it.
- **Results:** declarative headings that state the finding, never "What/How …" headings. Development history does
  not belong in a heading.
- **Discussion:**
  - answer the premise first;
  - give the limits as the scope of the claim;
  - state future work once, at the end, as "left to future work".

## 7. Figures and tables

- **House style:** every figure uses `scripts/figure_style.py`.
  - Colour follows the score: clinical history purple, imaging teal, combined orange, navy for structure.
  - Use one sans-serif typeface and no titles inside plots.
- **Figure 1** is a methods schematic. It carries no results.
- **Figures that show the system's output** show a real held-out output laid out as a clinical page: BT-RADS order,
  numbers in tables and graphics, and each sentence once, with its cited fields. Never an invented example.
- **Tak et al. 2025 (NEJM AI)** is the model for the cohort and case figures. Figures are illustrative, not box
  flowcharts.
- Figures and tables sit next to their first mention.
- Tables use visibly shaded alternate rows (`\zebrarows`).
- The supplement keeps only what the current paper rests on.

## 8. How we work, and the tests

**Layers.** Work outline → skeleton (first sentences only) → prose → polish, and settle each with the author before
the next. Agree on the story ([OUTLINE.md](OUTLINE.md)) before writing prose.

**Before showing a draft:**
1. First-sentence test: do the paragraphs' first sentences read as the argument?
2. Cold reader: an agent with no project context states the claim and the numbers it remembers.
3. Hostile reviewer: every objection is answered in the main text, logged in RESERVE.md, or fixed.
4. Number audit: every number appears once, matches its source (`docs/manuscript/NUMBERS.md`,
   `docs/results/`), and is needed where it stands.
5. Integrity check: everything on the "always" list in section 3 is present.

**Housekeeping:**
- Rebuild and commit `paper/main.pdf` after every change to the paper.
- Locked passages (LOCKED.md) change only with the author's approval.
- Material awaiting the author's review goes in `docs/review/`.

## 9. Retired directions (do not reintroduce)

| Retired | Replaced by |
|---|---|
| The puzzle "what has the model learned to see", the claim "mostly the treatment timeline", the 120-day risk story, "within phase" | The system argument and the timing-and-enhancement baseline (section 1) |
| "Three or four introductory paragraphs, no list of contributions"; "two background paragraphs and five bullets" | About seven paragraphs, then four contributions (section 6) |
| Titles with no system name, the clinician's question first; "a modular system for … surveillance" | The current title (section 1) |
| Tagline "PRISM makes progression scores inspectable"; the light-through-a-prism metaphor | "Auditable", defined once |
| Ban on "clinical decision support" | Allowed as intended use only |
| The pitch "beat radiomics by 0.24" in the abstract; the methods-first framing (three technical contributions C1–C3) | Radiomics comparison in Results only; the system spine |
| "Private local agentic report" | One schema-bound writing step, never an agent |
| The example report drawn as a segmentation strip, never a patient image | A real held-out report page with the cohort's images |
| The AUC split by time window (2026-11-26: the data do not support a time-window argument) | Each group of inputs' contribution to the score (section 3) |
| VOICE.md, STORY.md and the council rounds as guides | This file, [OUTLINE.md](OUTLINE.md), [RESERVE.md](RESERVE.md) |

## 10. Reactions since consolidation

Add each new reaction as a dated one-line rule.
- 2026-11-19: guidance consolidated. Only the current rules are kept; the history guides are moved to
  `docs/manuscript/archive/`.
- 2026-11-19: table row shading is neutral grey (`rowgrey` = gray 0.92 in `paper/macros.tex`), never a blue tint; blue
  distracts.
- 2026-11-24: Prof. Zhang's marked copy (email 2026-11-23): her mechanical edits applied as marked (author name
  "Yongjie Jessica Zhang"; title ends "for Glioma Follow-up MRI"; abstract sentence split with semicolons; contributions
  open with PRISM or a verb; "The remainder of this paper is organized as follows."; Table 1 in footnotesize like
  Table 2; Figure 1 caption "The workflow of PRISM."). Her subjective items are with the author.
- 2026-11-26: every citation supports exactly the clause it sits on (numbers, population, method and verb strength as
  the source gives them). Cite a source for its own finding, never for PRISM's design or result; split a clause between
  sources when each carries only part. Name every tool, dataset, model and method with its reference. A reworded
  citing sentence is checked against the source again before it is committed, and `paper/build.sh` refuses a cited
  bibliography entry still marked CHECK.
- 2026-11-27: a source cited in several sentences is checked in each one separately, and a tone or wording pass that
  touches a citing sentence re-opens its source. A study's scope stays in the sentence (one cohort, chest radiographs,
  pre-operative reports, US figures); "can", "models" and "such" do not generalise one study. Language models used or
  compared are cited by their model card's own citation.
