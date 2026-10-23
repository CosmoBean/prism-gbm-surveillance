# How we write the PRISM paper

The rules for writing and editing `paper/main.tex`. They come from the author's direction (2026-10-22/23) and from
four models of the craft. Read this before drafting, and again before committing any prose. When the author reacts
to a passage, add the lesson to section 10 so it outlives the session.

**The one sentence to remember:** *elegance comes from the arrangement of ideas, not the sophistication of the
vocabulary.*

---

## 1. A paper is an argument, not an analysis report

The analysis documents in `docs/results/` are the lab notebook: complete, chronological, every number with its
interval, every deviation labelled. That is their job. The paper's job is different: to make **one argument** that
a reader can follow, remember and repeat, with the evidence a sceptical reader needs to believe it.

So the paper is written from the argument down, never from the results up.
- We do not ask "what did we find?" and then try to fit it all in.
- We ask "what is the claim?", "what does a reader need to see, in what order, to believe it?", and we show
  exactly that.

The notebook order (what we ran first) and the argument order (what the reader needs first) are different. Our first
draft followed the notebook. That is the main reason it read as a report.

## 2. The models

| Model | What it teaches | How it shows up in our paper |
|---|---|---|
| **Watson & Crick (1953)**, "We wish to suggest a structure for…" | **Directness.** The first sentence says what the paper does. No warm-up, no novelty claims, no literature tour before the idea. | The abstract and the introduction's last paragraph state the finding in the first clause. |
| **Rockman (2012)**, "But what is the question to which QTNs are the answer?" | **Curiosity.** Turn a research programme into a puzzle; question an assumption the reader holds. | Our puzzle: *when a surveillance model scores 0.80, what has it learned to see?* The assumption we question: that a high AUC on surveillance MRI means the images are doing the work. |
| **Feynman** | **Conversation.** Build the problem and its constraints with the reader, then the resolution, so the explanation feels like an investigation. | Results are a sequence of steps, each answering the question the previous one raised. |
| **Whitesides (2004)**, "Whitesides' Group: Writing a Paper" | **Outline before prose.** The paper is organised around its conclusions and the figures and tables that carry them; prose is written last. Write the outline while the research is still running; it shows what is missing. | We work in layers (section 7) and settle the outline before any paragraph is rewritten. |

The July 2026 Inorganic Chemistry editorial "The Art of Storytelling in Scientific Writing" is on the author's
list; its points are not yet included here (add them when the text is available).

## 3. The claim and the question

Every element of the paper must serve these. If a paragraph does not, it moves to the supplement or goes.

- **The question (Rockman):** when a model of glioma surveillance MRI scores well, what has it learned to see?
- **The claim (Watson & Crick):** mostly, where the patient is in treatment. PRISM separates the evidence of the
  images from the evidence of the treatment timeline and audits each, which shows what each contributes and where
  neither can be trusted.
- **The investigation (Feynman):** a model scores 0.80 → the test set's mix of treatment phases explains it →
  give a model more structure step by step and watch where its gains come from → what remains is what images
  contribute on their own → what a system can honestly offer with that.

The full spine with figures is in [OUTLINE.md](OUTLINE.md).

## 4. What to reveal: the 80 / 20 rule

The paper is persuasion, and persuasion is selection. We show the reader about 80% of the story: everything needed
to follow and believe the argument. We leave about 20%, the detail behind each step, for the reviewer to ask about.
A good reviewer question we can answer in one paragraph is a strength, not a weakness. Spoon-feeding every check
buries the argument and signals defensiveness.

Selection is not concealment. The line is drawn here:

**Always in the main text (never withheld). These would change what a reader concludes:**
- for any task the paper presents the system as doing, its performance where the system is meant to be used,
  next to the more flattering number. This belongs in the Results; the abstract carries it only if the abstract
  makes a claim about that task. (120-day risk: the intended-use AUC of 0.60 stays in the Results and Discussion.);
- the strongest baseline: what timing and treatment alone achieve, whenever we report a model that uses them;
- the within-phase result, whenever an across-phase number could be read as image signal;
- which analyses were planned in advance and which were exploratory (one word in place is enough);
- the scope limits that bound the claim: one development centre, a documentation-based label, no clinician has
  read the reports;
- any result that contradicts the claim.

**The reserve (supplement, or ready for the response to reviewers). Each is a reviewer question we welcome:**
- sensitivity analyses that leave the conclusion unchanged (censoring weights, deaths as non-events, alternative
  negative sets, gradient boosting vs ridge);
- the full list of imaging variants tried (70 radiomics configurations, 32 frozen encoders, nine fine-tuned arms,
  resegmentation, label variants, diffusion); the main text names the strongest test and says the rest agreed;
- calibration detail beyond one sentence; SHAP; the report generator's comparison arms;
- mechanistic explanations we suspect but have not proven (why ET volumes are noisy; why the networks failed).

Every reserve item is logged in [RESERVE.md](RESERVE.md) with where its answer lives, so a reviewer question is
answered in minutes.

**Cut entirely:** project history (versions, the leaky boosting model, earlier prompts), work by others we do not
use, and anything that exists only because we ran it.

Test for any sentence or number: *does the reader need this to follow or believe the argument at this point?* If
not now, perhaps later in the paper; if never, the reserve.

## 5. Numbers: the right metric at the right time

- **One number per claim in the prose.** The interval goes with the headline numbers (the claim's own evidence),
  not with every number. Other numbers live in tables and figures and are pointed to, not repeated.
- **Never the same number twice** across text, table and caption. Decide where each number lives.
- **Show a number when the reader is ready to interpret it.** A number arrives after the sentence that tells the
  reader what it would mean. "Timing alone, with no image at all, scored 0.82" lands only once the reader knows
  the full model scored 0.84.
- **Contrasts beat levels.** Readers remember "the same model fell from 0.87 to 0.72", not two separate AUCs in
  two paragraphs.
- **The abstract carries one or two numbers**, the ones the claim cannot do without. A sequence of numbers (a
  ladder, a list of AUCs) is told in words in the abstract and shown in a figure in the paper.
- **Do not argue against the metric you lean on.** AUC measures how well a model ranks scans; the audit shows what
  it uses. Frame the two as complementary ("an AUC cannot say what a model has learned to see"), never as "the
  audit found what the AUC hid" next to a column of AUCs.
- **Precision:** two decimals in prose (0.82); three in tables only when differences are small. No p-values when an
  interval says the same thing.
- **Name things by what they are, not by codes.** "The timing model", "images alone", "the full model": not B1,
  R2, I2, P. Codes stay in the supplement.
- **Counts that matter are concrete.** "56 of the 62 progression scans came more than 12 weeks after RT" persuades
  more than any statistic about phase imbalance.

## 6. Prose

**Paragraphs**
- The first sentence of every paragraph is its claim. A reader who reads only first sentences should get the
  whole argument. (We test this; see section 8.)
- One idea per paragraph. A second idea means a second paragraph.
- A caveat comes after the claim it qualifies, once, in the place where it applies. It does not come before the
  claim, and it is not repeated in every section.

**Sentences**
- Plain words, active voice, "we" for what we did. Short sentences for claims; longer ones only for reasoning.
- No intensifiers or signposts that do the reader's thinking: *notably, importantly, interestingly, crucially,
  remarkably, it is worth noting that.* If something is important, the arrangement shows it.
- No stacked hedges ("may potentially suggest"). Say what the evidence supports, at its strength.
- No lists of tests in place of a finding. "Radiomics, frozen and fine-tuned encoders, resegmentation, a cleaner
  label and diffusion showed no measurable gain" is a list. "Every way we gave the images more to work with raised
  the AUC only by teaching the model the treatment timeline" is a finding.
- British spelling with -ise; SI units upright (journal rules: [JOURNAL_RULES.md](JOURNAL_RULES.md)).

**Voice: what Claude's default sounds like, and what to write instead**

Rules about arrangement do not stop a writer's default voice from coming back. Claude's default is recognisable,
and the author noticed it in abstract draft 2. Check every draft for these and rewrite them:
- slogans built on contrast: "X, not Y", "not X but Y", "says how well…, not what…";
- dramatic short sentences that announce instead of explain: "Taking the evidence apart showed why.";
- abstractions doing things: "the record grounds a report", "the images held their own", "the evidence speaks";
- colon reveals, triplets, and a closing line written to be quoted;
- the same rhythm in every sentence.

Write instead as a scientist explaining to a colleague what they did and what they found:
- "we" and the past tense for what we did; the present for what is true;
- reasoning carried by ordinary connectives (because, so, which suggested, we therefore);
- sentences whose length follows the thought, some long, some short, none written for effect;
- concrete subjects: patients, scans, models, dates, not "the evidence" or "the story".

Watson & Crick's first sentence is modest and plain. Feynman reasons out loud. Neither uses a slogan.

**Before and after, from our first draft**

| First draft | Why it fails | Rewritten |
|---|---|---|
| "PRISM predicts documented progression within 120 days of a glioma surveillance MRI and returns an audit record and a clinician report per scan." (abstract, sentence 1) | Opens with a product description; the reader has no reason to care yet. | "A model that predicts glioma progression from surveillance MRI can score well without looking at the tumour." |
| "Radiomics, frozen and fine-tuned deep encoders, resegmentation, a cleaner label and diffusion showed no measurable gain, and a locked model scored 0.61 externally." | A list of tests; six results the reader cannot weigh. | "Giving the images more structure raised the AUC only by teaching the model the treatment timeline; within a phase of care, images alone held at about 0.68." |
| Section heading "Imaging adds nothing measurable" | A verdict that overstates and invites a fight. | "What the images contribute on their own" |
| Four sentences of censoring detail in the middle of the phase-of-care result | A reserve item in the main line; the reader loses the thread. | One clause: "the result held under every censoring correction we tried (Supplementary S20)". |

## 7. How we work: layers, cheapest first

Following Whitesides, each layer is settled with the author before the next is written.
1. **Outline** ([OUTLINE.md](OUTLINE.md)): title, question, claim, the argument as a sequence of figure claims,
   the abstract.
2. **Skeleton:** each section as its paragraphs' first sentences only. Reading the skeleton must give the whole
   argument.
3. **Prose:** paragraphs written under their first sentences.
4. **Polish:** numbers checked against sources (`paper/SOURCE_MAP.md`), rules in this file checked, PDF rebuilt.

Do not polish a section whose outline is still moving.

## 8. Tests before showing the author a draft

1. **First-sentence test:** extract the first sentence of every paragraph. Does it read as the argument?
2. **Cold reader:** an agent with no project context reads the draft and states the claim in two sentences and the
   three numbers it remembers. If it cannot, or remembers the wrong numbers, the arrangement is wrong.
3. **Hostile reviewer:** an agent reviews as a sceptical referee. Every objection it raises is either (a) answered
   in the main text because it is on the "always" list, (b) logged in RESERVE.md with its answer, or (c) a real
   weakness to fix.
4. **Number audit:** every number in the prose appears once, matches its source, and is needed where it stands.
5. **Integrity check:** everything on the "always" list in section 4 is present.

## 9. Sections: what each one does

- **Title:** the question or the finding, not the system's name and three adjectives. The system name can follow a
  colon.
- **Abstract (≤ 150 words, unstructured):** (1) the finding or the puzzle, in one sentence; (2) what we built and on
  what data; (3) the investigation in two or three sentences, with the two or three numbers that carry it; (4) what
  is left and what the system offers; (5) the scope limit.
- **Introduction (three or four paragraphs):** why surveillance MRI is hard and why this matters to a reader of
  this journal; why high reported AUCs should make us curious; the question; what we did and found, stated
  directly. No list of contributions.
- **Methods:** enough to make the argument checkable, in the order the Results need it. Definitions the reader needs
  to interpret a number come before that number. Everything else is in the supplement, pointed to once.
- **Results:** one subsection per step of the investigation. The heading states what the step found. The last
  sentence of each subsection raises the question the next one answers.
- **Discussion:** answer the question from the introduction in the first paragraph. Then what it means for people
  who build or evaluate such models, what the system offers, and the limits as the scope of the claim rather than an
  apology. End on the idea, not on future work.

## 10. Lessons from the author's reactions

Add each reaction as a dated, one-line rule.
- 2026-10-21: one story about the final system; no version history; drop the leaky boosting model and Rai 2026.
- 2026-10-22: do not frame imaging as worthless. Make the two kinds of evidence (images, treatment timeline)
  "speak for what they are"; most datasets have images but no timing, so the imaging pathway must stand on its own.
- 2026-10-22: the doctor weighs both kinds of evidence; coupling them can be a display in the record, not
  necessarily another model.
- 2026-10-23: tight, about 80%; leave the other 20% to the reviewers' curiosity. Not disinformation: selection of
  what to reveal, and when, for a better story.
- 2026-10-23: the abstract had too many numbers (0.66 → 0.81 and four others). Keep one or two; tell sequences in
  words.
- 2026-10-23: 120-day risk is not the headline. It is where the problem was found (the first 0.80) and stays in the
  body with its intended-use result; the abstract need not quote it.
- 2026-10-23: "exposes leaks that the AUC hid" reads as self-contradictory in a paper full of AUCs. Say what an
  AUC cannot tell (what the model uses), not that the AUC was wrong.
- 2026-10-23: draft 2 fell back into Claude's default voice (contrast slogans, staccato, abstractions as subjects).
  The rules above were about arrangement; voice needs its own check (section 6, "Voice"). Best remedy: imitate a
  sample of the author's own writing or a paragraph they choose, not rules alone.
