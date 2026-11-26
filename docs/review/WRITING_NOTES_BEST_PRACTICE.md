# Writing notes: paper/main.tex against clinical AI journal practice

2026-11-19. Notes only; the manuscript was not edited. Line numbers refer to `paper/main.tex` as of commit 20df108
(834 lines, with the cohort and case-strip figures included). Every suggestion keeps to the author's rules: elegant British prose, one
story about the final system, no self-undermining commentary, never "timeline", declarative headings, "left to
future work". Suggested rewrites are drafts. Numbers in them are copied from the manuscript and should be checked
against NUMBERS.md before use.

---

## 1. The principles that matter most for this paper

| # | Principle | Source | Why it bites here |
|---|---|---|---|
| P1 | **Old before new, with new information in the stress position.** "Put in the topic position the old information that links backward; put in the stress position the new information you want the reader to emphasize." Keep the subject next to its verb, and put the action in the verb. | Gopen & Swan 1990 | Many Results sentences end on a qualifier ("(exploratory)", "cannot be compared with ours", "not as warnings"), so the stress falls on the caveat and not on the finding. |
| P2 | **One central contribution, and context, content and conclusion at every level.** A paper that pursues several contributions convinces less about each. Every paragraph sets up its context, gives its content and draws its conclusion. | Mensh & Kording 2017, rules 1 and 3 | The abstract, the first paragraph of the Discussion and the Conclusion each put a different result first. |
| P3 | **The abstract tells the whole story and ends on a conclusion.** It runs from the gap, through "here we", to what it means. | Mensh & Kording rule 5; Nature summary-paragraph guidance | The abstract stops on a verifier result and never draws a conclusion. |
| P4 | **The Introduction narrows to a gap, and each paragraph earns the next.** | Mensh & Kording rule 6; Lancet "Research in context" (evidence before this study → added value → implications) | Two of the seven paragraphs carry a second message, and one "therefore" does not follow from the sentence before it. |
| P5 | **Results are a chain of statements, each answering a question.** Each paragraph opens with its conclusion. | Mensh & Kording rule 7 | In 4.1 and 4.3 the conclusion sits in the middle or at the end of a paragraph full of numbers. |
| P6 | **Write for the reader who is not you (the curse of knowledge).** Define terms, ration abbreviations, and avoid "zombie nouns" and the noun stacks they create. | Pinker 2014; Sword 2012; Mensh & Kording rule 2 | Terms and stacks such as "the reduced clinical-history model's across window AUC", "the reading" and "tier" only make sense from inside the project. |
| P7 | **Reporting guidelines decide some of the prose.** TRIPOD+AI asks the title and abstract to name the population, the outcome and the model type, the abstract to give participant and event counts and an overall interpretation, and the Discussion to state limitations "and their effects on biases, statistical uncertainty, and generalisability". CLAIM 2024 asks for "reference standard" in place of "ground truth", "external testing" in place of "external validation", and the intended use and role of the AI in the Introduction. | TRIPOD+AI (BMJ 2024); CLAIM 2024 | The abstract never uses the word *progression*. "Incorporation bias" is described but never named. |
| P8 | **Key results in one sentence, free of abbreviations.** Radiology: AI asks for a summary statement of at most 255 characters and up to three Key Results without vague language or abbreviations. Nature asks the summary paragraph to avoid numbers and abbreviations unless they are essential. | RSNA Radiology: AI checklist; Nature formatting guide | This is a good test even for a T&F journal. If the 255-character sentence cannot be written, the story is not settled (see section 9). |
| P9 | **Captions stand alone and lead with the finding.** A reader who looks only at figures should get the argument. | Nature formatting guide; T&F tables rule (JOURNAL_RULES.md A) | Fig. 2's title uses a phrase the author has banned. Fig. 1's caption contains development history. |

---

## 2. Abstract (lines 31–40)

**What works.** The opening premise (context) is followed by "PRISM is a local system built for both". This is the
"here we" move, and it is clean. The numbers are few, as STYLE.md §5 asks.

**Issues**
1. **The outcome is never named.** The word "progression" does not appear. "the time after radiotherapy and the enhancing tumour carried most of the ranking" (36–37) gives no answer to the question "ranking of what?"
   TRIPOD+AI abstract items 1 and 6 ask for the outcome. A cold reader cannot tell what the 0.80, 0.77 and 0.86 measure.
2. **The referent of the 0.80 is ambiguous.** "the combined model added no clear gain over a baseline of the two (AUC 0.80)". The
   parenthesis sits in the stress position, and the reader cannot tell whether 0.80 belongs to the model or to the baseline. It belongs to the baseline. The
   combined model's AUC is 0.82.
3. **The sentence that announces carries no content.** "The separation exposed what a single score would hide." (35–36) is the
   dramatic announcement that STYLE.md §6 bans ("abstractions doing things"). It costs nine words that the conclusion needs.
4. **There is no conclusion.** The abstract ends on the verifier (38–39). Mensh & Kording rule 5 and TRIPOD+AI abstract item 12
   both ask for an interpretation.
5. **There are no counts and no model type.** TRIPOD+AI abstract items 7 and 9 ask for them. Three words cover the model type ("ridge logistic
   regression"). One phrase covers the counts ("146 scans of 80 patients").
6. **Some terms are undefined.** "reduced combined model" (37–38), "record check" and "verifier" are never defined, and "AUC" is never expanded. The hyphen in
   "held-out" (38) is inconsistent with "held out" everywhere else.
7. The word count is about 150, so every addition needs a cut. Items 3 and 5 pay for each other.

**Suggested rewrite** (same spine, ~150 words; premise → system → separation → transfer → reports → conclusion):
> A score for progression on a follow-up MRI after glioma treatment is useful only if the reader can see what it
> rests on, and a generated report only if each statement can be checked against the record. PRISM is a local
> system built for both. Ridge logistic regressions score each scan from imaging measurements, from the clinical
> history and from both; every value enters one record with its source; and a local language model writes a report
> that is checked against that record. On 146 scans of 80 MU-Glioma-Post patients, a baseline of the time after
> radiotherapy and the enhancing tumour reached an area under the curve (AUC) of 0.80, and the combined model added no clear
> gain over it. Fitted once and applied unchanged, the combined model reached 0.77 at LUMIERE and 0.86 at
> UCSF-ALPTDG. All 406 held out reports passed the record check. Scored separately, a progression score shows what
> it rests on.

(The last sentence is a placeholder conclusion. Its job is to restate the premise as something the paper has now
shown. Choose the author's own wording. The verifier sentence can return if the count allows.)

---

## 3. Introduction (lines 48–132)

The seven-paragraph arc is sound: clinical problem → advanced imaging → machine-learning models → what an AUC means → uncertainty → report → gap.
The gap sentence (118) names three properties that mirror paragraphs 4, 5 and 6, which is good Lancet-style
"evidence before this study". The weaknesses are local.

1. **"therefore" at line 88 does not follow from what precedes it.** Paragraph 3 ends on Tak and Tarek (82–85), "Longitudinal and
   interpretable designs have begun to appear". "A high AUC in this setting therefore says little" (88) follows from
   Gomaa (80–81: "time since the end of treatment was the strongest input"), not from Tak and Tarek. *Fix:* move the Tak/Tarek
   sentences earlier in paragraph 3, or into the Discussion, so that Gomaa stands in the stress position directly before the "therefore". This is
   the old-before-new rule applied across a paragraph boundary.
2. **A banned word.** "interpretable" (82) is excluded by STYLE.md (2026-11-15: never "interpretable" or "explainable"). Use
   "Longitudinal designs, and designs whose intermediate quantities can be read, have begun to appear", or name the
   designs ("temporal models of serial scans and concept bottleneck models").
3. **Paragraph 2 carries two messages** (62–70): whether advanced imaging settles the question, and how reporting practice varies (BT-RADS).
   *Fix:* move "Practice also varies … \citep{gore2019}" into paragraph 6, which is about the written report. Structured reporting is
   the precedent for PRISM's report (243 cites BT-RADS), so it belongs there and returns later in the argument.
4. **Paragraph 6 also has two messages** (106–115): checking, then running locally. The locality argument could be one closing
   clause, or the opening of the gap paragraph.
5. **"a clinician already holds"** (92–93, and again at 371) conflicts with the 2026-11-17 rule: the baseline uses evidence "available to any
   reader", never evidence a reader already weighs. Suggested: "What a model adds beyond evidence available
   to any reader of the scan is the quantity worth measuring."
6. **"a radiomics model reported an AUC"** (79): models do not report. Write "a radiomics model reached a reported AUC of 0.80" or
   "Christodoulou et al. reported an AUC of 0.80 for a radiomics model…".
7. **Echo the gap in the topic positions.** Paragraphs 4, 5 and 6 open with "says little until its basis is known", "should also state how sure it is" and "the
   other half of the reading". The gap sentence (118) then uses "shows what each score rests on, states how sure it is,
   checks its written report". Matching the wording exactly (the abstract already says "what it rests on") lets the reader
   recognise old information when it returns in the gap sentence.
8. **Contributions (122–132).** Three bullets state findings or features, but "Locked transfer" (128–129) states only a procedure. Give it
   its result ("…and still ranked scans there: the reduced combined model reached 0.77 and 0.86") or fold it into
   "What the separation exposes". The bullets also do not follow the abstract's order exactly. STYLE.md 2026-11-18 says contributions follow the
   abstract's spine.
9. **CLAIM item 3** asks for the intended use and the role of the AI. The intended use appears only in Methods (259–261). One clause in the
   gap paragraph would do: "…intended to support, not replace, the reading of each follow-up scan".

---

## 4. Methods: PRISM and Evaluation (lines 135–500)

1. **A heading does not match its content.** 3.3 "Timing-and-enhancement baseline and AUC split" (347) opens with *The published
   approach* and *Mask sensitivity*. Rename it "Comparisons and sensitivity analyses", or give the first two their own subsection.
2. **The reliability card sentence is too long** (238–241). The subject "a reliability card" is separated from its object by a 40-word
   embedded clause with three parentheticals. *Rewrite:*
   > The other is a reliability card, after model cards \citep{mitchell2019}. For the scan's situation, its time window
   > and the state of its enhancing tumour, the card gives how many scans with and without progression the models were
   > tested on. Where there were at least 10 of each it also gives their AUCs (the tested tier); otherwise it gives the
   > counts alone (few cases).
   The clause "recomputed without the patient's own scans, it changed the tier of one MU scan" belongs in the reserve.
3. **Lists in parentheses.** "(2,000 for the timing-and-enhancement baseline, the AUC split, the group-conditional sets,
   the mask sensitivity analyses, the published approach on the second masks, and the calibration, spectrum and
   marker-coding analyses)" (321–322) is a notebook sentence. *Fix:* "AUCs carry 95% CIs from 1,000 or 2,000
   bootstrap samples of patients (Supplementary Section S5)".
4. **Logistics read as history.** "UCSF-ALPTDG was no longer on our hardware when they ran" (323). State the scope neutrally,
   with the formal reason if it is accurate: "These three analyses were run on MU and LUMIERE, because access to UCSF-ALPTDG had ended under its data use agreement."
5. **Too many numbers in one sentence.** "146 scans of 80 patients, out of 181 detection scans of 92 patients among the cohort's 126 grade 4
   patients" (260–261) puts five numbers in one clause. TRIPOD+AI item 20a expects a participant flow diagram. A small flow panel, or a
   row in Table 1, would let the sentence keep only "146 scans of 80 patients".
6. **The withdrawal rule ends on "withdrawn".** "the comparison with PRISM's imaging model would be withdrawn if the pipeline did not rank below it"
   (359–360; Table 2 row 478). In the stress position, "withdrawn" leaves the reader with the impression of selective reporting.
   State what the rule protects: "The plan, committed before the run, fixed the comparison and its reading: PRISM's
   imaging model would be compared with the pipeline only if it ranked scans above it." Better still, report the rule only in
   Table 2.
7. **"reading" has two meanings.** It is the clinical reading of a scan (51, 106) and also the verdict of a test ("the reading against the
   baseline", 368; "The plan fixed the reading in advance", 374; 573). Use "interpretation" or "verdict" for the second sense.
8. **Small caveats with emphasis.** "The weighting by patient makes *even* the average coverage approximate" (413–414). The "even" adds emphasis to a
   caveat. "With patient weighting the average coverage is approximate" says the same neutrally.
9. **Development history.** 446–450 ("The rules as first written … We then let the rules read…") is allowed once in Methods
   (STYLE.md 2026-11-18). It can be a single sentence: "Before evaluation, the rules were extended to read the region from the text of
   a cited field as well as its name; the change was tested only on synthetic records and the 48 development reports."
10. **"robust"** (367) is on VOICE.md's list of words to avoid unless defined. The plan defines it, but Table 2 says "unchanged", so use
    "unchanged" in both places.

---

## 5. Results (lines 503–747)

**Order.** Section 3.6 (460) names three primary results: the radiomics comparison, the external AUCs and the gain over the baseline.
The abstract leaves out the first (by the author's choice, STYLE.md 2026-11-18), but Results open with it (4.1) and the Conclusion
leads with it (787). Mensh & Kording rule 1 (one central contribution) is under strain. There are two options, and the choice is the author's:
(a) order Results by the abstract's spine (separation 4.3 → transfer 4.2 → confidence 4.4 → reports 4.5), with the
radiomics comparison after transfer as supporting evidence; or (b) keep the order but make 4.1's heading and topic
sentence say how the comparison serves the separation story.

**4.1 (505–528)**
- The heading is not declarative. Suggested: "PRISM's separate models ranked scans above the published radiomics pipeline on the
  same task".
- **Nine numbers in one sentence** (509–510). Keep the intervals on the difference only (STYLE.md §5): "…the published pipeline
  reached 0.58 and PRISM's clinical-history model 0.82, a difference of 0.24 (95% CI 0.15–0.34)".
- **The finding is buried.** "on MU the selected radiomic features ranked scans no better than enhancing volume alone" (514–515)
  sits mid-paragraph behind "An earlier re-implementation…", which is project history the author has asked to cut. Move that sentence to the reserve and
  make this finding the paragraph's last sentence.
- **The paragraph ends on a negative.** "…cannot be compared with ours" (517). Lead with the general point and end on the
  number: "Single held out sets vary widely at this size: over 100 random held out sets of 18 patients, the pipeline
  ranged from 0.32 to 0.88."
- **An orphan number.** The third paragraph (525–528) begins "Clinical data alone, without dates, reached 0.53" with no claim. This is the
  strongest evidence that the dates carry the clinical-history model, and it belongs in the topic position:
  > The clinical-history model's lead came from the treatment dates: the same patient variables without them
  > reached 0.53 (0.45–0.61).

**4.2 (530–565)**
- The heading and topic sentence are good.
- **Subject separated from its verb.** "The reduced combined model, whose inputs every cohort records (at UCSF with an approximated
  radiotherapy window), reached…" (534). Move the parenthesis to a separate clause after the number.
- **Repeated sentence starts.** "On MU … On MU …" (537–538) opens two sentences in a row. The calibration sentences (538–541) put three numbers in one clause. Leave one in the prose and the rest in the
  supplement.
- **The label paragraph** (562–565) sits after the figure and reads as an afterthought. Its claim ("at UCSF the label follows
  enhancement") explains the 0.86, so it belongs directly after the UCSF numbers. "Accordingly" is fine.

**4.3 (567–611)**
- The heading is good. The first sentence (570–571), however, reports the baseline's AUC, and the paragraph's finding (no clear gain) comes in sentence 2.
  Lead with the comparison:
  > The combined model ranked scans little above a baseline of the time window and the enhancing tumour: its gain was
  > 0.02 (−0.03 to 0.08) on MU and 0.04 (−0.01 to 0.10) at LUMIERE, where the baseline itself reached 0.80 and 0.73.
  ("little above" is evaluative. If it reads as self-undermining, use "The combined model's gain over … had intervals including zero".)
- **The second paragraph is too long** (577–590): about 16 numbers and five messages. Split it into MU (577–585) and LUMIERE
  (586–590). Its best sentence, "the window alone captured much of the clinical-history model's discrimination between
  windows" (580–581), should open the MU paragraph. It is the paragraph's conclusion.
- **A five-word noun stack.** "the reduced clinical-history model's across window AUC of 0.96 against 0.59 within one" (589). Unstack it:
  "the reduced clinical-history model ranked 0.96 of pairs across windows and 0.59 within one".
- The closing paragraph (609–611) is the best "so what" in the Results. Its wording could also open the Discussion.
- **"much" and "most".** "much of the ranking" (heading, 754) and "most of the ranking" (abstract 36, contribution 126) say different things. Pick one.

**4.4 (613–669)**
- **The heading is vague** and uses the wording VOICE.md asks to avoid ("evidence behind the score"). Suggested: "The conformal sets met
  their planned coverage at all three centres".
- **Mapping with "respectively".** "covering 82%, 87% and 78% of scans at MU, LUMIERE and UCSF, and named a single outcome for 75%, 62% and 64%"
  (616–617) asks the reader to map six numbers by position. Fig. 4 carries them. In the prose, keep one cohort's pair, or
  write "between 78% and 87%".
- **A hard-to-parse comparison.** "changed which groups were covered more than how well the worst ones were" (623). Rewrite: "Calibrating
  within groups mostly moved coverage from one group to another; once set size was matched, the worst-covered group
  gained little (Figure 4)."
- **A tautology.** "The two descriptive statements describe the evidence" (643). The paragraph also ends on "not as warnings" (650). That is
  a contrast slogan (STYLE.md §6), and it falls in the stress position. Suggested: "We therefore present the agreement and the card as
  descriptions of the evidence at each scan." The sentence pointing to the case figure (651–652) needs its own short paragraph, or it should move into the
  topic sentence.

**4.5 (671–747)**
- **The heading breaks the author's own rule.** "Reports passed the checker after one revision of the prompt" puts development history in a heading
  (STYLE.md 2026-11-18: "never in the abstract or headings"). Suggested: "All 406 held out reports passed the record
  check". Say "after one revision" **once**. At present it appears at 459, 490, the heading, 675, and in the Fig. 5 caption (692). Note also that the
  prompt revision is not described in Methods 3.5, so it has no single home.
- **The qualifier takes the stress position.** "…made because every LUMIERE report first failed (exploratory)" (675–676) ends on the qualifier. Move
  "exploratory" to the front so that the result falls in the stress position.
- **History again.** 679–681 (reports regenerated after renaming fields) is history. It belongs in the reserve or the Supplement.
- **Repetition.** "a swapped tier word" is said twice (698–699 and 702). The \todo at 708 is still open.
- **An unmotivated second clause.** "The checks apply equally to both writers; the language model's reports were a quarter shorter" (708–709) joins two ideas
  with a semicolon, and the second has no stated purpose.

---

## 6. Discussion and Conclusion (lines 750–790)

1. **Paragraph 1 answers the question.** That is good (Mensh rule 8). However, it does not set the result against the literature that frames it. Gomaa
   2025 ("time since the end of treatment was the strongest input") and Tarek 2026 (interval strongly affected output)
   support the timing finding and were cited in the Introduction. One sentence placing PRISM against them is the
   "added value" that Lancet's panel asks for.
2. **Paragraph 2** (761–764) is the paper's most portable recommendation ("Studies … could report two quantities beside the
   AUC"). Consider promoting it to second place in the Conclusion.
3. **An awkward relative clause.** "Direction words are bound through a fixed list, which a wider list and a fresh set of independent errors
   would extend" (771–772): a list cannot extend a list. Rewrite: "Direction words are bound through a fixed list; a wider list,
   tested on a fresh set of independent errors, is the next step."
4. **Name the bias.** The limitations paragraph (777–783) is well scoped and ends on "left to future work". TRIPOD+AI item 26 asks
   for the *effect* of each limitation. The sentence "at LUMIERE and UCSF it partly reflects the images the scores use" (778) describes
   incorporation bias without naming it (STYLE.md 2026-11-01: use the field's terms). Suggested: "…partly reflects the
   images the scores use (incorporation bias), which favours the imaging and enhancement scores at those centres."
   CLAIM 2024 would call the label the "reference standard".
5. **The Conclusion leads with the radiomics comparison** (787–789). The abstract leads with the separation. The Conclusion should end where the abstract ends
   (P2). Suggested order: the separation showed what the ranking rests on → the locked models transferred → the report
   was checked against its record → what this offers a reader of the scan.

---

## 7. Captions and tables

- **Fig. 1** (152–166): the caption is 15 lines long and includes protocol exceptions ("except the LUMIERE imaging and reduced
  clinical-history scores, added afterwards"). That is history and belongs in Table "Status". The title "The task and the method"
  is generic. Suggested: "PRISM scores each follow-up scan three ways and writes a checked report".
- **Fig. 2** (547): "Performance at the development centre" uses a phrase the author has banned (STYLE.md 2026-11-01: "the public development cohort").
  Suggested title: "The locked models ranked scans at two external cohorts".
- **Fig. 3** (597): "Where the ranking comes from" is good, and stating the finding would be better: "Pairs across time windows carry most of the
  clinical-history model's ranking".
- **Fig. 4 and Table 4 (verifier)**: Table 4's caption carries argument ("only because the rewritten sentence dropped content it
  requires, not because it detected the wrong label"). Shorten it to a table note.
- **Case-strip figure** (659–667): this is a model caption. It states how the patients were selected, which TRIPOD+AI and the Tak et al. figures both do.
- **Abbreviations in captions**: "T1c" and "MU" appear before their definition in the main text (151–163). Captions should expand them
  or name the cohort in full.

---

## 8. Sentence-level patterns across the paper

| Pattern | Examples (line) | Remedy |
|---|---|---|
| **Abbreviations.** The paper uses about 20: AUC, CI, MU, UCSF, IDH, MGMT, FLAIR, T1c, RANO, BT-RADS, IQR, JSON, L2, BraTS, UNETR, TCIA, CT, MRI and others. AUC is never expanded, and MU and UCSF are used for MU-Glioma-Post and UCSF-ALPTDG without definition. | 37, 63, 151, 252 | Expand AUC in the abstract and at first use in the text. Define "MU-Glioma-Post (MU)" and "UCSF-ALPTDG (UCSF)" once. Drop JSON, L2 and IQR from the prose where they are not needed. |
| **Noun stacks** (zombie nouns, and the abbreviations they collect) | "patient grouped inner folds" (355); "class weighted gradient boosted model" (354); "the size matched marginal sets" (636); "the within window AUC" (584) | Unstack into a verb or a relative clause, e.g. "inner folds grouped by patient", "marginal sets matched in size". |
| **Compound modifiers without hyphens**, which slow parsing | "held out folds" (512), "rule based checks" (435), "data to text systems" (436), "normal appearing brain" (206), "pair weighted analogue of the covariate adjusted AUC" (389) | The author bans hyphens unless they are needed, so rewrite: "the folds held out", "checks based on rules", "brain of normal appearance". Where no rewrite works, the hyphen is "needed". Make "held-out" (38) agree with the rest. |
| **Qualifier in the stress position** | "(exploratory)" at sentence end (514, 564, 625, 676); "cannot be compared with ours" (517); "not as warnings" (650) | Move the qualifier to the topic position or inside the sentence. Let the result end it. |
| **More than five numbers in a sentence** | 509–510 (9), 534–537 (9), 577–583 (10+), 616–617 (6), 260–261 (5) | One interval per claim. Leave other numbers to the figure or table they already sit in (STYLE.md §5). |
| **Abstractions as subjects** | "The separation exposed…" (35); "The design ties time to the label" (256) | The second is acceptable as a short claim. Replace the first. |
| **"evidence" stretched across four meanings** | "evidence statements" (159), "treatment-course evidence" (123), "evidence behind each score" (heading 4.4), "evidence a clinician already holds" (371) | Use the exact component (VOICE.md table): conformal set, agreement, card, the clinical-history inputs. |

---

## 9. A stress test worth running before submission

Write the Radiology: AI items for this paper, even though the target is a T&F journal: a 255-character summary statement and three Key Results with no
abbreviations. A draft:

> **Summary.** Scored separately, glioma follow-up MRI progression scores showed that time after radiotherapy and
> enhancing tumour carried most of the ranking; locked models transferred to two external cohorts, and every held out
> report passed its record check.

> **Key Results.** (1) On 146 scans of 80 patients, a baseline of time after radiotherapy and enhancing tumour reached
> an area under the curve of 0.80, and the combined model added no clear gain. (2) Fitted once and applied
> unchanged, the combined model reached 0.77 and 0.86 at two external cohorts. (3) All 406 held out reports passed
> the record check.

If the author disagrees with this summary, that disagreement shows what the abstract and the Conclusion still need to settle.

---

## Sources

- Gopen GD, Swan JA. The science of scientific writing. *American Scientist* 1990;78(6):550–558. Quotations via
  https://wstomv.win.tue.nl/quotes/science-of-scientific-writing.html
- Mensh B, Kording K. Ten simple rules for structuring papers. *PLoS Comput Biol* 2017;13(9):e1005619.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC5619685/
- Collins GS et al. TRIPOD+AI statement. *BMJ* 2024;385:e078378. https://pmc.ncbi.nlm.nih.gov/articles/PMC11019967/
- Tejani AS et al. Checklist for Artificial Intelligence in Medical Imaging (CLAIM): 2024 update. *Radiol Artif
  Intell* 2024;6(4):e240300. https://pmc.ncbi.nlm.nih.gov/articles/PMC11304031/
- RSNA, Radiology: Artificial Intelligence manuscript preparation checklist (summary statement ≤255 characters; Key
  Results ≤75 words, no abbreviations). https://pubs.rsna.org/page/ai/author-instructions/checklist (from a search
  snippet; the page blocks automated fetching)
- Nature, formatting guide and "How to construct a Nature summary paragraph" (context, "Here we show", avoid numbers
  and abbreviations unless essential). https://www.nature.com/nature/for-authors/formatting-guide (from a search
  snippet; the page requires login). Nature Medicine follows the Nature-family conventions. Its own page could not be fetched.
- The Lancet, Information for authors: the Research in context panel (evidence before this study; added value;
  implications of all the available evidence). From a search snippet.
- NEJM AI author centre (Original Articles: structured abstract of ≤250 words; Background, Methods, Results, Conclusions).
  From a search snippet. https://ai.nejm.org blocks automated fetching, so confirm before using.
- Sword H. Zombie nouns. *New York Times* Opinionator, 23 July 2012.
- Pinker S. Why academics stink at writing. *Chronicle of Higher Education*, 26 September 2014.
- The author's own rules: docs/manuscript/STYLE.md, VOICE.md and JOURNAL_RULES.md.
