# Why our prose feels off: a diagnosis against Tak et al. 2025 (NEJM AI)

Written 2026-11-19. These are notes only; `paper/main.tex` is unchanged. `WRITING_NOTES_TAK_COMPARISON.md` gives
line-by-line edits. This file is the overall diagnosis: what kind of prose each paper is, and why ours reads wrong.

## 1. The measurements

Counted over the prose only (figures, tables and citations removed). Tak's Introduction row is left out because its
superscript citations break sentence splitting.

| Section | Words per sentence | Numbers per sentence | Brackets per sentence | "We" per 100 words |
|---|---|---|---|---|
| Tak, Methods | 28.8 | 0.24 | 0.71 | 0.66 |
| PRISM, Evaluation | 26.4 | 0.06 | 0.38 | 0.78 |
| Tak, Results | 28.4 | **2.33** | 1.12 | **0.62** |
| PRISM, Results | 25.6 | **1.76** | 0.87 | **0.12** |
| Tak, Discussion | 25.1 | 0.09 | 0.32 | **0.76** |
| PRISM, Discussion | 24.4 | 0.00 | 0.00 | **0.00** |

**The problem is not density.** Tak's Results carry more numbers and more brackets per sentence than ours, and
its sentences are just as long.

**The problem is that no one is in our paper.** In Results we write "we" once every 830 words; Tak writes it once
every 160. Our Discussion does not say "we" at all.

Our Results never say what we wanted to know, what we did, or what we concluded. Numbers attach to models
("the reduced combined model … reached 0.77") with nobody asking a question. That is the "analysis report" feel the
author has named several times.

## 2. Seven observations

### 2.1 Tak tells an investigation; we list states of affairs
Every Results paragraph in Tak has the same four moves:
1. **Question:** "Given the poor performance of single-scan prediction, we next investigated …"
2. **Action:** "Sequential scans were passed into the pipeline using the same splits …"
3. **Result:** "… yielded an AUROC of 0.77 (95% CI, 0.62 to 0.91), a substantial improvement …"
4. **Meaning:** "… indicating limited generalizability of learned features across institutions."

Our Results paragraphs open on a result (move 3) and usually stop there. Move 1 never appears, and move 4 is rare
or buried mid-paragraph. Example, Section 4.2: "The reduced combined model, whose inputs every cohort records (at
UCSF with an approximated radiotherapy window), reached 0.77 (0.68–0.86) at LUMIERE, and the imaging model 0.65
(0.56–0.73, exploratory)." The reader gets numbers before knowing what they are meant to settle.

### 2.2 Tak links sections; ours stand alone
Tak's Results subsections are chained, each motivated by the last ("Given …", "To determine how …", "Following …").
Ours could be shuffled without loss. Each starts cold, so the paper reads as five reports rather than one argument.
Our own rule asks that "the last sentence of each subsection raises the question the next one answers", but the
text does not do it.

### 2.3 Our qualifications ride inside the claims
Tak keeps protocol detail in Methods and lets a Results sentence be a finding. Ours carries the protocol in every
clause: "exploratory", "approximated there", "with CIs including 1", "whose interval includes zero", "with the
second masks", "locked". Sections 4.2 and 4.3 are the clearest cases.

Each is correct, but together they make the prose sound defensive. Tak states each limitation once, in a
paragraph that begins "This study has several limitations. First, …".

### 2.4 Our vocabulary is private
Tak uses the field's words: AUROC, external validation, holdout set, fine-tuning, calibration. We have coined a
dialect, and the reader must learn it before any sentence makes sense:
- "pairs across windows";
- "ranked 0.93 of the pairs correctly";
- "the reduced combined model";
- "images from one scan";
- "the rater's flag";
- "the second masks";
- "the tested tier";
- "few cases".

Several are needed, but they are introduced in passing and then used as though familiar.

### 2.5 Tak grounds the work in what a clinician does; we do not
Tak's second paragraph ends on a clinical action: earlier prediction "would provide actionable information to
counsel patients regarding adjuvant therapy initiation or the need for intensified surveillance regimens". Its
Conclusion returns to the same actions (reirradiation, second-line chemotherapy).

Our Introduction moves from the reading problem to literature, to shortcut learning, to conformal sets and to
report checking. It never says what decision a follow-up MRI feeds, and the Discussion never says what a clinician
would do differently with PRISM. The paper is about epistemics (what a score rests on), so it feels abstract.

### 2.6 Tak's Discussion has a recognisable shape; ours is compressed
Tak's Discussion runs in five parts:
1. "In this study, we …", what was done and why it matters;
2. the problem in the field;
3. "We hypothesized …", the mechanism;
4. comparison with prior work;
5. "This study has several limitations. First, … Second, …".

Our Discussion has five short paragraphs that each pack in a technical point and end on a caveat or a missing
analysis, with no "we" and no interpretation of what the findings mean. Our Conclusion repeats Results rather
than drawing a lesson.

### 2.7 Some of our own rules cause the problem
Rules added one reaction at a time have stripped out the connective tissue that Tak's prose relies on:
- no colons or semicolons;
- no signposts;
- no rhetorical questions;
- no "X, not Y";
- state facts inline;
- no self-undermining remarks;
- yet label every planned or exploratory result.

What remains is short declaratives about objects, with qualifications attached and no narrator. Several of these
rules are sound on their own. Together they remove the "we asked, we did, we found, this means" scaffold that makes
a journal article read as one.

## 3. What to take from Tak, and what not to take

**Take:**
- the four-move paragraph;
- "we" as the subject of the investigation;
- chained Results ("Given …, we next …");
- one interpretive sentence after the numbers;
- limitations gathered in one numbered paragraph;
- the clinical action named early and returned to at the end;
- standard terms.

**Do not take:**
- Tak's hype ("novel", "first", "leveraging", "robustly", "mimics an expert neuroradiologist");
- its number piles (twenty AUROCs and deltas in one paragraph);
- its overclaims about calibration.

Our target journal (CMBBE: Imaging & Visualization) also wants an unstructured abstract, unlike NEJM AI's
Background/Methods/Results/Conclusions. Take Tak's register, not its format.

## 4. What the change would look like (a demonstration, not applied)

**Section 4.2 now:**

> Fitted once on MU and applied unchanged, the combined and imaging models kept ranking scans at both external
> centres (Figure 3). The reduced combined model, whose inputs every cohort records (at UCSF with an approximated
> radiotherapy window), reached 0.77 (0.68–0.86) at LUMIERE, and the imaging model 0.65 (0.56–0.73, exploratory). At
> UCSF the imaging model reached 0.73 (0.60–0.84), images from one scan 0.80 (0.69–0.89) and the reduced combined model
> 0.86 (0.76–0.93), while the reduced clinical-history model, whose radiotherapy flag is approximated there, scored
> 0.56 (0.42–0.69). …

**In the four-move pattern, with the same numbers:**

> Having fixed the models on MU, we next asked whether they would rank scans at centres they had never seen. We
> applied them unchanged to LUMIERE and UCSF-ALPTDG (Figure 3). The combined model, in the reduced form whose inputs
> every cohort records, reached an AUC of 0.77 (0.68–0.86) at LUMIERE and 0.86 (0.76–0.93) at UCSF, against 0.80 on
> MU; the imaging model reached 0.65 and 0.73. The models therefore kept their ranking at both centres. Their
> probabilities transferred less well, and a centre would recalibrate them on its own scans before reading them as
> risks.

The rewrite gives the motivation, a "we", the headline numbers in one comparable form, and one sentence of meaning.
The protocol details ("exploratory", the approximated flag, single-scan images, calibration slopes) move to the
table, the caption or the limitations paragraph.

**The Discussion opening, in Tak's shape:**

> In this study we built PRISM, a local system that scores each follow-up MRI with separate imaging,
> clinical-history and combined models, and writes a report that is checked against the scan's record. Keeping the
> scores apart showed that, in these cohorts, the time after radiotherapy and the enhancing tumour carry much of the
> ranking, evidence available to any reader of the scan, which PRISM now states beside each score.

## 5. Suggested order of work (for the author to decide)

1. **Restructure the Results first** with the four-move pattern and chained subsections. This is the largest gain.
2. **Gather the limitations** into one numbered paragraph in the Discussion, and take the qualifiers out of the
   Results sentences.
3. **Add the clinical action:** one sentence in the Introduction's first paragraph on what decision the scan feeds,
   echoed in the Conclusion.
4. **Write a glossary** of the coined terms. Define each once, in Methods, and replace any that has a standard name.
5. **Relax the rules in STYLE.md** that remove connectives: allow "Given …, we next …", the occasional semicolon,
   and "we" as the default subject in Results and Discussion.
