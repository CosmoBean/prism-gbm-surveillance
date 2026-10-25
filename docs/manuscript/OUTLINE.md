# Outline: the argument of the PRISM paper (layer 1)

**Status: draft 2.1 (2026-10-26), for the author's reaction; adds the split, replication and card results.** It folds in the UCSF results, the two locked external
tests, the reliability card and the decisions since 2026-10-23. Draft 1 (2026-10-23) is in git history; the author
did not like its brief. Rules: [STYLE.md](STYLE.md). Reserve: [RESERVE.md](RESERVE.md). Results map:
[STORY.md](STORY.md). Next layer: skeleton (first sentences only), then prose in `paper/main.tex`.

## What changed from draft 1
- Order: the system and its solid numbers come first; the single-split lesson moves from the opening to the
  evidence for why the system is needed. Draft 1 opened on our own number falling apart.
- Three cohorts instead of one: MU (development), LUMIERE and UCSF (both locked, plans written in advance).
- New finding: what a model leans on depends on how the cohort labels progression (the timeline on MU, enhancement
  on UCSF). The audit is what shows it.
- New system part: a reliability card at each scan, built only from measured results.
- RANO is out. Within-phase comparisons are a diagnostic, not a headline. The long tail is future work.

## Title
**What has a glioma surveillance model learned to see? Separating image and treatment-timeline evidence with PRISM**
(kept; alternatives in git history). Option that names the external tests: *PRISM: showing what a glioma
surveillance model relies on, across three cohorts*.

## The question, the claim, the investigation
- **Question:** when a model of glioma surveillance MRI scores well, what has it learned to see?
- **Claim:** it depends on the cohort, and a single AUC cannot tell. PRISM keeps image and treatment-timeline
  evidence apart, and its models transport to two external centres without refitting. Its audit shows that on MU
  the score rests on where the patient is in treatment, and on UCSF on how much enhancing tumour the scan shows.
  So PRISM reports, at each scan, both kinds of evidence and how well each has been shown to work in that
  situation, and says so where nobody knows.
- **Investigation:** build the two pathways → solid numbers in three cohorts → ask what each score rests on (the
  ladder on MU, enhancement on UCSF) → why single numbers mislead (our split, UCSF's split, the literature) → what
  the system does with this (the reliability card; the early post-RT window).

## Abstract (LOCKED 2026-10-24, text in [LOCKED.md](LOCKED.md))
**Flag for the author:** the locked text predates UCSF. It has no external tests and opens on the 0.80 split. If
draft 2 is accepted, the abstract no longer matches the paper's order. Not changed; the smallest edit will be
proposed once the outline settles.

## The argument in figures

| # | Claim | Content |
|---|---|---|
| **Fig 1** | PRISM keeps two kinds of evidence apart and says how far each can be trusted at this scan. | Two pathways (images; clinical + treatment timeline) → scores → audit record → reliability card → report. One worked example scan. |
| **Fig 2** | The models hold up at two external centres without refitting. | AUC by pathway (images, timeline, both) × cohort (MU internal, LUMIERE locked, UCSF locked, UCSF-trained). |
| **Fig 3** | Each design choice in the image model buys AUC, and the audit shows what it buys. | The MU ladder: single scan 0.66 → + change 0.71 → + schedule context 0.81; the last step encodes the timeline; between vs within phase. Deep networks as one panel (at control level on MU; tracking ET volume on UCSF). |
| **Fig 4** | The same kind of model leans on different evidence in different cohorts. | MU: the timeline's gain is between phases (+0.11 overall, −0.02 within). UCSF: ET volume alone 0.88; among enhancement-increased scans images fall to 0.53–0.65. |
| **Fig 5** | One split can move a score more than any model choice. | (A) MU first split vs 500 splits for every model (clinical alone 0.79 vs 0.65; images 0.79 vs 0.72; PRISM's first model 0.80 vs 0.72). (B) A single-scan radiomics setting of the kind reported at 0.80: 0.57 under repeated CV, 1 of 100 single splits ≥ 0.80. (C) UCSF's own split vs 100 random splits (timeline 0.45 vs 0.72). |
| **Fig 6** | Where the system says it does not know. | Reliability card: situations (phase × enhancement) by cohort with their tier; 35 of 249 report scans in a tested situation; no early post-RT situation has more than 3 progressions; when the pathways disagree, the timeline is usually right on MU and the images on UCSF. |

**Tables**
- Table 1: the three cohorts (what each has: images, RT dates, labels, n).
- Table 2: evidence by pathway, task and cohort (levels; the ladder stays in Fig 3).
- Table 3: questions fixed in advance and their answers (MU detection, LUMIERE, UCSF Q1–Q4).
- Literature comparison: three or four rows (Christodoulou, Tikhonov, Chen), concise, in the Discussion or Table 4.

## Sections

**1. Introduction (four paragraphs)**
1. Surveillance MRI after glioma treatment and why progression is hard to call.
2. Reported models score well, on single splits, often without a clinical comparator or an external test, so we
   do not know what they have learned.
3. The question.
4. What PRISM is and what we found, directly.

**2. Methods**
- 2.1 PRISM: two pathways, the audit record, the reliability card, the report (the report in two sentences).
- 2.2 Cohorts and the task: detection at the scan (120-day risk as secondary); phases of care; intended use.
- 2.3 Evaluation: repeated grouped CV; locked external tests with plans written in advance; within-phase and
  within-enhancement comparisons as diagnostics; planned vs exploratory (the ladder is exploratory).

**3. Results** (heading states the finding)
1. *PRISM's pathways hold up at two external centres* → Fig 2, Table 2. MU: timeline 0.82, images 0.71, both
   0.82. Locked: LUMIERE 0.77; UCSF single-scan images 0.80, about the same as trained on UCSF (0.83). Clinical
   data alone at chance everywhere.
2. *What each design choice buys the images* → Fig 3. The ladder; deep networks in one sentence.
3. *The evidence a model leans on depends on the cohort* → Fig 4. MU: the timeline; UCSF: enhancement. PRISM's
   audit is what tells them apart.
4. *One split can move a score more than any model choice* → Fig 5. Our first split flattered every model by
   0.07–0.14; a single-scan radiomics setting of the kind reported at 0.80 gives 0.57 under repeated CV and reaches
   0.80 in 1 of 100 splits; UCSF's own split put the timeline at 0.45 against 0.72.
5. *Where PRISM says it does not know* → Fig 6. For most scans the evidence behind any score is thin: 35 of 249
   are in a situation tested on ≥ 10 progression and ≥ 10 stable scans. Pathway disagreement resolves differently
   by cohort. The audit's leaks and the report: one paragraph.

**4. Discussion**
1. The answer to the question, first sentence.
2. For people who build these models: a no-image baseline, a locked external test, and an audit of what the model
   leans on. Literature in context (concise).
3. For a clinician: a small scenario (a scan eight weeks after RT with growing enhancement: images point one way,
   the timeline another, the card says this situation has not been tested; PRISM flags it for follow-up rather than
   scoring it).
4. Extensible: the image pathway runs where datasets have no treatment dates (LUMIERE, UCSF); adding the timeline
   needs no new model; new cohorts add rows to the card.
5. Limits: one development centre; documented, not expert-read, progression; small subgroups; the ladder is
   exploratory; no clinician has read the reports.
6. Future work: pool the long-tail cases across cohorts (early post-RT progression, growing enhancement without
   progression; Burdenko's 35 pseudoprogressions) and fine-tune on them; clinician evaluation.

## To the supplement or the reserve
Censoring, calibration, GBM, SHAP, conformal sets, the report's comparison arms, the "giving imaging every chance"
tests, UCSF label sensitivities and the audit detail, 120-day risk detail.

## Work needed for this outline
- Done 2026-10-26: reliability card (RELIABILITY_CARD.md), image-only on the first split (SPLIT_VARIANCE.md),
  Christodoulou-style re-implementation (CHRISTODOULOU_REPLICATION.md), UCSF subset intervals (UCSF_AUDIT.md).
- Open: the author's note that Christodoulou used closed-source data needs the repository link and their wording.
- Open: card design choice (exact cells, no pooling across cohorts) for the author.

## Decisions log (author, 2026-10-25)
1. Task and framing: B (detection at the scan) is the task, C (a system that shows what a model uses) is the
   framing, A (120-day forecast) is the origin story.
2. External data: UCSF-ALPTDG obtained (DUA); it enters this paper if its labels allow. Burdenko and UCSD-PTGBM are
   the follow-up.
3. RANO 12-week rule: not part of the paper (author, 2026-10-25). The transportable model holds on LUMIERE
   (0.80 internal, 0.77 external) with images carrying more there, so the timeline is not just the labelling rule; the
   calendar follows the biology as well. The timeline is described as where the patient is in treatment, without
   arguing why it works.
4. Christodoulou 2026 and Tikhonov 2025: mentioned concisely for context, with their results and a line on method.
5. Figures: new figures built for this story; the existing ones are not binding.
6. Space by contribution to the argument. Report generator: little (one or two sentences and a figure panel at
   most). Deep learning: only as much as it adds to the story.
7. Name: PRISM, no acronym (the old expansion, "Post-treatment Response Intelligence and Surveillance Monitor",
   is dropped from main.tex when the prose is rewritten). Mythical names were considered and rejected as too much
   for a scientific paper.
8. (2026-10-26) Within-phase and within-enhancement comparisons are diagnostics: they show the direction, they do
   not carry precise claims. The long tail (early post-RT progression, growing enhancement without progression) is
   future work: pool across cohorts and fine-tune.
9. (2026-10-26) The reliability card: a lookup of measured results by situation (not a learned confidence model).
10. (2026-10-26) Two locked external tests are a main strength; claim transport, not better performance on UCSF.
