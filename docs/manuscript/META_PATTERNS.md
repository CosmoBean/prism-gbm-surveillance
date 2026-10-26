# Meta-patterns in the author's direction

How the author instructs and reacts, distilled from the author's own messages (sessions 2026-09-26 to 2026-10-26),
STYLE.md section 10, OUTLINE.md, LOCKED.md and the project memory. Each pattern gives the pattern, the author's
words (verbatim, typos kept), and a wording rule with a before → after in the paper's domain. Use it with
[STYLE.md](STYLE.md); where they differ, the author's latest reaction wins.

---

## (a) Tone and voice

**1. Plain, direct, scientist-to-colleague; the author hears Claude's default voice immediately.**
- "I think you have gone back to defaulting to how you sound like while removing all the style you have tried to learn."
- "elegance comes from the arrangement of ideas, not the sophistication of the vocabulary." (from notes the author supplied)

Rule: write what we did and what we found, with "we", past tense for actions, ordinary connectives (because, so,
which). No sentence written to be quoted.
- Before: "Taking the evidence apart showed why."
- After: "We therefore compared the two pathways within each phase of care."

**2. Restraint over flourish: short, crisp, nothing showy.**
- "i think it would be a but much for a scientific paper" (on a mythical system name)
- "A shorter and more crisp name would be nice."
- "Let's use a new short and concise title."

Rule: prefer the plain descriptive word to the evocative one, in titles, headings and module names alike.
- Before: "PRISM: two faces of evidence watching over glioma surveillance"
- After: "PRISM: a modular system for glioma progression surveillance on MRI"

**3. Clean punctuation: no em dashes, no needless hyphenated compounds, no filler words.**
- "help me clean up, all the unnecessary words that have crept in. The em dashes and hyphenated words that are not required."

Rule: split or rejoin with a comma, semicolon or full stop instead of an em dash; open a compound adjective into a
phrase when it reads fine that way.
- Before: "a locked, no-refit, externally-validated image-only model — tested at two centres"
- After: "the image model, fitted once on MU-Glioma-Post and tested unchanged at two other centres"

**4. Revise conservatively; keep what the author approved.**
- "The first abstract was almost perfect except the ending ... can we work more with the first version and change the required places conservatively."
- "I like this part of the abstract, let's lock this in."

Rule: change the sentence that is wrong, not the passage around it. Locked text (LOCKED.md) changes only with
explicit approval; propose the smallest edit beside it. The approved voice is abstract draft 1: concrete numbers,
semicolon-joined contrasts, one idea per sentence.

---

## (b) Claims and framing

**5. Capabilities first: show what the system does, then the challenges it handles.**
- "I would like them to appreciate the system that we have tried to build, if cold emperical numbers are good that is ground zero for someone to even think it is worth giving their time."
- "We need to show what our models can do and not strongly but show what part of challenges are mitigated through the system."
- "We need to explain a system that helps and a story that helps the reader digest and concisely understand the methodology and the usefulness of this system."

Rule: open sections and paragraphs on a result the system achieves; introduce each difficulty as a known property
of surveillance data paired with the module that handles it. Never open on our own number falling apart.
- Before: "Our first evaluation's 0.80 did not survive repeated cross-validation."
- After: "Fitted once on MU-Glioma-Post, PRISM's image pathway reached an AUC of 0.77 on LUMIERE and 0.80 on UCSF without refitting."

**6. Never accuse the field or other groups; state challenges neutrally.**
- "Models that read glioma surveillance MRI report good AUCs, usually on one test split, so nobody knows what they have learned — the wording of this is an issue. We can’t say that"
- "(at the the same time, this is not a strong story either)"

Rule: describe properties of the data and of evaluation designs, not failings of people. Comparisons with other work
are concise, neutral, and side by side; nothing is claimed about a model we did not run.
- Before: "Published models report inflated AUCs from single splits."
- After: "In cohorts of this size, the choice of one test split can move an AUC by more than a change of model (Supplementary Figure S1)."

**7. Moderate claim strength: neither overclaim nor declare things worthless.**
- "just because we pick something and just blindly apply does not mean there is no signal, like you had told me images add nothing, although that may be true, images in themselves give a mindblowing AUCROC"
- "show limitations too (extent of limitations should not render the whole paper useless)"

Rule: claim at the strength of the evidence; no verdict headings ("adds nothing", "fails"), no superlatives. Say
what a module contributes and where it is untested.
- Before: "Imaging adds nothing measurable."
- After: "What the images contribute on their own" (heading), then "Within a phase of care, images alone reached about 0.68."

**8. PRISM is the author's own system and is not published; this is the PRISM paper.**
- "can you call it the PRISM report split? rather than published paper? because PRISM is not published yet."
- "I thought this was going to be the PRISM paper itself, not like a different paper"

Rule: present PRISM as the system this paper introduces. Never "published", never a re-evaluation of someone's
model. The original single-split result is "our first evaluation".
- Before: "We re-evaluate the published PRISM model."
- After: "We present PRISM, a modular system for ..."; "PRISM's first evaluation reached 0.80 on one test split."

**9. Frame the system as modular and complementary, the way a clinician uses evidence.**
- "See using both the measurements from a different parts of the pipeline, is only to say the doctor might be looking at both the values to actually help them diagnose"
- "the clinical features could be a part, and a simpler image and feature engineered image features can be a part and then segmentation can actually help the report. We can actually propose a system with a confidence score."
- "So deep networks are useless for segmentation and localization as well?"

Rule: each component has a positive job. Deep networks are the segmenters that supply the measurements and the
report's images, not failed classifiers. Pathways are shown side by side; combining them is a display, not a claim
that a fusion model wins.
- Before: "Fine-tuned deep encoders failed to beat the measurements."
- After: "Deep segmentation supplies the volumes both pathways use and the images shown in each report."

**10. Name design choices honestly as inductive bias, and keep internal logic consistent.**
- "one could always argue there is a context of feature engineering in this"
- "We say it exposes leaks that AUC hides, at the same time, we are reporting AUC, so the last two lines are like...do we really wanna go into that?"

Rule: state each built-in assumption and what it bought. Do not argue against the metric the paper relies on; say
what an AUC cannot tell, not that it was wrong.
- Before: "The audit exposed leaks the AUC hid."
- After: "An AUC says how well scans are ranked; the audit record shows which inputs the ranking used."

---

## (c) Show vs hide (the 80 / 20 rule)

**11. Disclose what the narrative needs, at the moment it needs it; leave about 20% to reviewers.**
- "there is a certain skill to writing a paper, where we only disclose what is necessary to make a narrative ... It’s not all about metrics, at the same time it’s about showing the right metrics at the right time."
- "I would want the reviewers to ask me those questions and not spoonfeed them everything they need. It should be tight maybe like 80 percent and usually that 20 percent of explainable bias is completely okay and better to be left to curiosity"
- "Not Disinformation, at the same time...it is persuasion"

Rule: main text carries the argument; sensitivity checks that leave the conclusion unchanged go to the supplement
and RESERVE.md. The "always in the main text" list (STYLE.md section 4) is never withheld.
- Before: four sentences on censoring weights inside the detection result.
- After: "The result held under each censoring correction we tried (Supplementary S20)."

**12. Every result must answer "so what?"; space follows contribution.**
- "We have to able to say so what? for these points as an internal dialogue"
- "for report generator, not much because that is essentialls just fluff, deep learning resuts depending on how much quality it would add to the story."
- "Ensuring the report is something that is useful along with the model probabilities is extremely important."

Rule: a paragraph earns its place by changing what the reader believes. The report gets a short, concrete
paragraph about its usefulness and faithfulness, not its development history.
- Before: a paragraph comparing three prompt versions of the report generator.
- After: "Reports written by a local language model were checked against the record; all passed in each cohort (Figure 5)."

**13. Few numbers; if the author cannot interpret a number, cut it or explain it.**
- "I wonder if 0.66 to 0.81, and throwing so many numbers around makes full sense."
- "i don’t understand what that two calibration estimators are even meant to convey"
- "Among the scans rated “enhancement increased”, the images drop to 0.53–0.65 can you explain what this is supposed to mean and what these numbers signify?"

Rule: one or two numbers in the abstract, one number per claim in prose, sequences told in words and shown in a
figure. A number comes after the sentence that says what it would mean.
- Before: "AUCs rose from 0.66 to 0.71 to 0.81 (0.64, 0.66, 0.68 within phase)."
- After: "Each assumption added to the image model raised its AUC, mostly by encoding where the patient was in treatment (Figure 3C)."

**14. Cut history, versions and dead ends; one story about the final system.**
- "We can completely ignore the numbers and mentioning the leaky boosting model, I don’t think that is worth it."
- "If need to remove details about our previous works that’s okay. We don’t need to be exhaustive about everything."
- "RANO doesn’t need to be a part anymore, it would also mean that the whole logic does not necessarily need to be explained anymore."

Rule: no "v1/v2", no abandoned models, no argument the author has dropped (RANO: not in text, figures or reports).
Describe the final system in the present tense.
- Before: "Report generator v3.1, after the v3 failure on LUMIERE, ..."
- After: "PRISM's report generator ..." (the run history lives in the supplement's methods, if anywhere).

---

## (d) Structure preferences

**15. Story and results settled before prose; work in layers.**
- "Even before we start writing, I think if we have a good clarity in what is the results we have and the story that we are trying to tell, both of us are going to have a much better and easier time going about it"
- "I want to be able to tell a story about the methodology and the findings along the way while being able to make them concrete in the writing."

Rule: outline → first-sentence skeleton → prose → polish, with the author's reaction at each layer. First
sentences alone must carry the argument.

**16. Leave open questions as set-ups, not as a full end-to-end account; balance answers with limits.**
- "It is not important for me to give the full end to end story. Give the reader a balance and some answers. Some of the answers need to be set up for later."
- "Maybe that is something we can put in the future work as to finetune the models for longtail events"

Rule: limits are the scope of the claim, stated once, and each points to what would settle it. End on the idea,
not on an apology.
- Before: "Our models cannot be trusted early after radiotherapy."
- After: "Few scans fall in the weeks after radiotherapy at any centre; PRISM's card states this, and pooling such scans across cohorts is the next step."

**17. A little real-world context, and the strengths stated plainly.**
- "If we can actually talk a very small bit of how we would percieve this system to be useful in the real world, that would help with a better context."
- "having two external datasets is definitely a strong sign in this field imo"

Rule: one short clinical scenario (Discussion) and the two locked external tests near the top. Claim transport,
not superiority.
- Before: "PRISM outperforms existing methods externally."
- After: "Models fitted once on MU-Glioma-Post held at two external centres without refitting."

---

## (e) What the author repeatedly corrected in the assistant's writing

| Default habit | Author's signal | Rewrite rule |
|---|---|---|
| Contrast slogans ("X, not Y"; "says how well…, not what…") | "gone back to defaulting to how you sound like" | State the positive claim; put the contrast in a figure or a semicolon-joined pair of facts. |
| Staccato, dramatic short sentences ("Taking the evidence apart showed why.") | same | Join to the reasoning: "so we compared ..." |
| Abstractions as subjects ("the images held their own", "the record grounds a report") | same | Concrete subject: scans, models, the image model, we. |
| Accusing the field ("nobody knows what they have learned") | "We can’t say that" | Neutral property of data or design, no actor blamed. |
| Verdicts and overclaims ("images add nothing", "deep networks failed") | "does not mean there is no signal" | Say what was measured and where; give each module its job. |
| Debunking arc (our number collapses, then failures) | "I don’t like the story outline right now" | Capability, then challenge with mitigation. |
| Number dumps and ladders in prose | "throwing so many numbers around" | One number per claim; sequence in a figure. |
| Arguing against the metric relied on | "do we really wanna go into that?" | What the AUC cannot tell, not that it was wrong. |
| Codes and jargon (B1, C2, "two calibration estimators") | "i don’t understand what ... are even meant to convey" | Plain names: the timing model, images alone. |
| Unproven mechanisms carried as argument (RANO window) | "you wanna know why i think your rano argument doesn’t hold?" | Keep mechanisms to what the data shows; speculation to the reserve. |
| Version history and deferred "v2" work | "I want you to work it into this paper" | Final system only; needed results in this paper. |
| Calling PRISM "published" | "PRISM is not published yet" | "our first evaluation", "the PRISM report split". |
| Em dashes, hyphen chains, filler | "The em dashes and hyphenated words that are not required" | Commas, semicolons, full stops; open compounds. |
| Full rewrites when one sentence was wrong | "change the required places conservatively" | Smallest edit; locked text untouched. |

---

## Sentence-by-sentence checklist

1. Is the subject concrete (scans, patients, a model, we), not an abstraction doing things?
2. Is there a contrast slogan ("X, not Y"), colon reveal, triplet or quotable closer? Rewrite as a plain claim.
3. Any em dash, needless hyphenated compound, intensifier ("notably", "importantly") or stacked hedge? Remove.
4. Does the paragraph's first sentence state its claim, and does that claim say what the system does or found?
5. Is a difficulty stated as a property of the data and paired with the module that handles it?
6. Does the sentence blame or imply a failing of other groups or the field? Make it neutral or cut it.
7. Is the claim at the evidence's strength: no verdicts ("nothing", "fails", "outperforms"), no superlatives?
8. Is there more than one number? Keep the one the claim needs; move the rest to a table or figure.
9. Has the reader been told what the number would mean before it appears? Is it stated anywhere else?
10. Are model codes or unexplained terms used? Use plain names the author would understand at first reading.
11. So what: does the reader believe something new after this sentence? If not, supplement or RESERVE.md.
12. Is this history, a version label, a dropped model or RANO? Cut it.
13. Is PRISM called "published", or framed as someone else's model? Fix.
14. Is anything on STYLE.md's "always in the main text" list missing (intended-use result, timing baseline, within-phase result, planned vs exploratory, scope limits)?
15. Does the edit touch locked or approved text, or rewrite more than the wrong sentence? Revert to the smallest change.
