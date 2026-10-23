# Outline: the argument of the PRISM paper (layer 1)

**Status: draft for the author's reaction (2026-10-23).** It replaces the 2026-10-15 outline (in git history).
Rules: [STYLE.md](STYLE.md). Left for reviewers: [RESERVE.md](RESERVE.md). Once this outline is settled, the next
layer is the skeleton (first sentences only), then prose in `paper/main.tex`.

## Title

**What has a glioma surveillance model learned to see? Separating image and treatment-timeline evidence with PRISM**

Alternatives:
- *Images or the calendar? An auditable system for glioma surveillance MRI*
- *PRISM: keeping image and treatment-timeline evidence apart in glioma surveillance*

## The question, the claim, the investigation

- **Question:** when a model of glioma surveillance MRI scores well, what has it learned to see?
- **Claim:** mostly, where the patient is in treatment. Kept apart and audited, the two kinds of evidence each
  speak for what they are. The treatment timeline separates scans *between* phases of care. The images carry a
  smaller signal that holds *within* a phase, and they stand on their own where no treatment dates exist. Neither
  is reliable in the weeks after radiotherapy, where pseudoprogression lives.
- **Investigation:** 0.80 on one split → the split's mix of phases explains it → separate the two kinds of evidence
  → give the images more structure step by step and watch where each gain comes from → what is left in the
  intended use → what a system can honestly offer.

## Abstract (draft 4 = draft 1 with a new ending, 149 words)

> Models that predict glioma progression from surveillance MRI can score well without learning much about the
> tumour. We built PRISM, which keeps image and treatment-timeline evidence apart and records what each contributed
> at every scan. On MU-Glioma-Post, PRISM's first evaluation reached an AUC of 0.80 on one test split, but a model
> with no images did better on the same split, and over 500 splits the result averaged 0.72. At the scan where
> progression was called, clinical and timeline data alone reached 0.82. Each assumption built into the image model
> raised its AUC, from 0.66 to 0.81, but only by encoding the timeline; within a phase of care, images held at about
> 0.68, as much as the timeline. PRISM therefore shows both kinds of evidence side by side for every scan, and flags
> the weeks after radiotherapy, when pseudoprogression is common and neither has been shown to be reliable.

Draft 1's last two sentences (120-day AUC 0.60; "leaks the AUC hid"; reports) were removed at the author's request
(2026-10-23). Drafts 2 and 3 are in git history; the author preferred draft 1's voice.

## The argument in figures

Each figure makes one claim; its caption's first sentence is that claim.

| # | Claim the figure makes | Content | Source |
|---|---|---|---|
| **Fig 1** | PRISM keeps two kinds of evidence apart and records what each contributed. | System diagram redrawn around two pathways (images; treatment timeline + clinical) → risk → audit record → report; the phase of care marked on every scan. Replaces the current architecture and study-design figures (study design to the supplement). | redraw of `fig5a_architecture` |
| **Fig 2** | A score of 0.80 measured the test set as much as the model. | (A) first split: radiomics 0.80, timeline model 0.87, the no-training rule "scan is after RT" 0.74; (B) the same models over 500 splits, with the first split's rank; (C) per-split AUC against the split's phase mix. | merge of current Figs 3 and 4 |
| **Fig 3** | Each assumption built into the image model buys AUC by encoding the timeline; within a phase, images hold their own. | The ladder for detection at the scan: single scan → + comparison with earlier scans → + scan-schedule context, beside the timeline model and both together; bars for all scans and for pairs within the same phase. Inset or panel: fine-tuned networks given none of these assumptions score at the level of a shuffled-label control. | new; `DETECTION_TASK.md` exploratory section, `DETECTION_DEEP.md` |
| **Fig 4** | Where the system is reliable, and where it says it is not. | Scans along the treatment course (before RT, during, ≤ 12 weeks after, later) with events per phase; performance per phase for the timeline and the images; the early post-RT window flagged (4 progression scans among 55). | new, from `within_phase.csv` files; reuse of current Fig 6 (phase) panels where possible |
| **Fig 5** | The audit record shows what the AUC hides, and the report can be checked against it. | (A) the leaks the audit found and their effect; (B) a grounded report with its citations. | current Fig 8A plus a new panel from Section 3.5 |

**Tables**
- **Table 1:** cohorts (unchanged, trimmed).
- **Table 2: the evidence by pathway and task.** Rows: timeline only, images only, both. Columns: 120-day risk
  (all scans; intended use), detection at the scan (all scans; within phase), LUMIERE. The one table a reader needs
  to see the claim in numbers. It must not repeat Fig 3's ladder; it holds the levels, Fig 3 holds the steps.
- **Table 3: questions fixed in advance and their answers** (condensed from the current Table 4; keeps the
  planned / exploratory distinction visible).
- Report evaluation (current Table 5) moves to the supplement; one sentence in the text.

## Sections

**1. Introduction (four paragraphs)**
1. Surveillance MRI after glioma treatment, and why progression is hard to call (pseudoprogression in the weeks
   after RT; progression is a documented event).
2. Reported AUCs are high, and that should make us curious: single splits, missing clinical comparators, and a
   cohort that mixes phases of care with very different event rates.
3. The question.
4. What we did and found, directly: PRISM keeps the two kinds of evidence apart; the timeline explains most of the
   score; images hold a smaller within-phase signal; the audit and report make the system checkable.

**2. Methods** (in the order the Results need them)
- 2.1 PRISM: two pathways, the audit record, the report.
- 2.2 Data, the two questions (120-day risk; detection at the scan), phases of care and the intended use.
- 2.3 Evaluation: repeated grouped cross-validation, comparisons within a phase of care, planned vs exploratory.

**3. Results** (one step each; the heading states the finding)
1. *One split overstated the model* → Fig 2. Ends: what made that split easy?
2. *The treatment timeline carries most of the score* → Table 2. Timeline alone: 0.70 for 120-day risk in grade 4,
   0.82 at detection; 56 of 62 progression scans late. Ends: then what do the images bring?
3. *What each assumption buys the images* → Fig 3. Ladder 0.66 → 0.71 → 0.81; within phase about 0.68 throughout;
   networks without these assumptions at chance. For 120-day risk, no imaging branch added to the timeline (one
   sentence; the variants in the reserve). Ends: what is left where the system will be used?
4. *In the intended use* → Fig 4. 120-day risk 0.60; detection with both kinds of evidence; the early post-RT
   window where neither is reliable, and how PRISM flags it; LUMIERE, where there are no treatment dates and the
   images carry more.
5. *An audit that sees what the AUC cannot* → Fig 5. The leaks and the corrected model; reports faithful 249 / 249.

**4. Discussion**
1. The answer to the question, in the first sentence.
2. What it means for people who build and evaluate such models: report the timeline baseline and within-phase
   results; name the assumptions built into a model and what each buys.
3. What PRISM offers a clinician: both kinds of evidence side by side, each with its reliability, and a flag where
   neither holds.
4. Scope: one development centre, documented rather than expert-read progression, the ladder is exploratory, no
   clinician has read the reports.
5. Close on the idea: ask not only how well a surveillance model scores but what it has learned to see.

## Moves to the supplement or the reserve
- The five "giving imaging every chance" tests (label, segmentation, cohort, modality, encoder): one sentence in
  Results 3; details in the supplement.
- Censoring sensitivity, calibration detail, gradient boosting, SHAP, conformal sets and selective prediction (P1,
  P2), the report generator's comparison arms, the imaging-examples figure, the study-design figure.

## Open decisions for the author
1. Title.
2. ~~Both questions or detection first~~ (author, 2026-10-23): 120-day risk is not the headline. It is the
   setting of the first 0.80 (Results 1) and gets one paragraph with its intended-use result (Results 4); the
   argument is carried by detection at the scan, where the evidence can be taken apart.
3. The PRISM name (clash with arXiv 2610.13510) and the relation to Christodoulou 2026.

## Numbers still to confirm before prose
- Images alone for 120-day risk, with the timing proxies removed as in the detection ladder (current best estimate
  0.683 in `IMAGING_VS_NONIMAGING.md` may include them).
- Within-phase AUC of the timeline and the images for 120-day risk, to fill Table 2.
- LUMIERE images-only for detection (only the full transportable model and its no-imaging reference were run).
