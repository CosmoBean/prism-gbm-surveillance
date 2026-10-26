# Outline: the argument of the PRISM paper (layer 1)

**Status: draft 3 (2026-10-26), for the author's reaction.** Rebuilt on the author's framing of 2026-10-26
(STYLE.md section 10): lead with what the system does, present the difficulties of surveillance data as known
challenges each paired with the module that handles it, PRISM as a modular system, no accusation of the field, no
RANO anywhere (text, figures, reports). Draft 2.1 and draft 1 are in git history. Rules: [STYLE.md](STYLE.md).
Reserve: [RESERVE.md](RESERVE.md). Results map: [STORY.md](STORY.md). Next layer: skeleton (first sentences only),
then prose in `paper/main.tex`.

## What changed from draft 2.1
- Opening: the system and what it delivers, not "a single AUC cannot tell".
- Spine: five known challenges of surveillance data, each with the PRISM module that handles it and the evidence
  that it does.
- PRISM is described as modules: clinical and treatment-timeline features; simple engineered image measurements;
  deep segmentation that supplies the measurements and the report's images; a confidence; a local report.
- Split variance and the Christodoulou-style replication move from a Results section to supporting evidence for
  how PRISM is tested (one paragraph and a supplementary figure).
- The confidence is a result of its own: conformal coverage at three centres, disagreement as the warning, the card
  as a statement of evidence.

## Title
**PRISM: a modular system for glioma progression surveillance on MRI** (author, 2026-10-26). The separated
evidence and the two external tests go in the abstract's first lines.

## The question, the claim, the investigation
- **Question:** can a surveillance system give the clinician, at each post-treatment scan, the image evidence and
  the treatment-timeline evidence separately, carry to other centres without refitting, and say how much each can be
  trusted there?
- **Claim:** PRISM does this. Its pathways hold at two external centres with models fitted once on MU-Glioma-Post;
  its audit shows what each score rests on in each cohort; its confidence keeps its stated coverage at all three
  centres; and its reports, written by a local language model and checked against the record, state the evidence
  without advice.
- **Investigation:** the modules → what each delivers on MU → locked tests on LUMIERE and UCSF → what each score
  rests on → the confidence → the report.

## The spine: challenges and the modules that handle them

| # | Known challenge of surveillance data | PRISM module | Evidence (Results) |
|---|---|---|---|
| C1 | Most datasets have images but no treatment dates | Separate pathways; the image pathway stands alone | Images alone transport to LUMIERE and UCSF (R2) |
| C2 | Progression is documented differently at each centre, so a score can rest on different evidence | Pathways kept apart, plus an audit of what each score rests on | MU: where the patient is in treatment; UCSF: enhancing volume (R3) |
| C3 | Cohorts are small, and a single split can move a score more than a model choice | Repeated patient-grouped CV; locked external tests with plans written in advance | Supporting paragraph + Supp. figure (split variance; single-scan radiomics setting) |
| C4 | The hardest situations (early after RT, growing enhancement) have few cases | Confidence: conformal set, pathway-disagreement warning, reliability card stating the evidence | Coverage at three centres; disagreement picks out errors on MU; 35 of 249 scans in a tested situation (R4) |
| C5 | Volumes are noisy, the clinician must see what was measured, and patient data cannot leave the hospital | Deep segmentation feeding measurements and a figure; a local language model with a deterministic checker | Faithful reports in all three cohorts (R5; v3.1 numbers pending) |

## Abstract (LOCKED 2026-10-24, text in [LOCKED.md](LOCKED.md))
**Flag for the author:** the locked abstract opens on the 0.80 split, has no external tests and no confidence, and
its order no longer matches this outline. A smallest edit will not fit; once this outline is accepted, a new
abstract will be proposed beside the locked one, and the locked text stays until you approve the change.

## The argument in figures

| # | Claim | Content |
|---|---|---|
| **Fig 1** | PRISM is built of modules, each answering a known challenge. | Scan + record → segmentation → measurements; clinical + timeline pathway; image pathway; combined score → confidence (conformal set, disagreement, card) → local report. One worked example scan. No RANO. |
| **Fig 2** | The pathways hold at two external centres without refitting. | AUC by pathway (clinical alone, timeline, images, combined) × cohort (MU internal, LUMIERE locked, UCSF locked, UCSF-trained as reference). |
| **Fig 3** | What each score rests on depends on the cohort, and the audit shows it. | (A) MU: the timeline's gain lies between phases of care. (B) UCSF: enhancing volume alone matches the image model. (C) The image-model ladder (single scan → + change → + schedule context), exploratory. |
| **Fig 4** | The confidence keeps its coverage and points to the doubtful scans. | (A) Conformal coverage at α 0.2 by cohort and pathway. (B) AUC with and without the disagreement warning. (C) The card: situations by cohort with their evidence tier. |
| **Fig 5** | The report states the evidence, faithful to the record. | One rendered report (segmentation figure, pathways, combined score, confidence) + faithfulness by cohort. |
| Supp. | How PRISM is tested, and why. | Split variance (MU first split vs 500 splits; UCSF's own split vs 100); single-scan radiomics setting under repeated CV. |

**Tables**
- Table 1: the three cohorts (images, treatment dates, how progression is documented, n).
- Table 2: questions fixed in advance and their answers (MU detection, LUMIERE, UCSF Q1–Q4, system S1–S7).
- Literature: three or four rows in the Discussion (Christodoulou, Tikhonov, Chen, Jabal), concise, neutral.

## Sections

**1. Introduction (four paragraphs)**
1. Surveillance MRI after glioma treatment: why calling progression is hard (treatment effects, timing after RT).
2. Known challenges for models of this task (C1–C5 in plain words), stated as properties of the data, without
   judging earlier work.
3. The question.
4. What PRISM is and what we found, directly.

**2. Methods**
- 2.1 PRISM's modules (Fig 1): the two pathways, the segmentation, the combined score, the confidence, the report
  (two sentences on the report, details in the supplement).
- 2.2 Cohorts and the task: detection at the scan (120-day risk as the secondary task); phases of care; the
  intended use.
- 2.3 Evaluation: repeated grouped CV, why (one paragraph with the supplementary figure); locked external tests
  with plans written in advance; planned vs exploratory.

**3. Results** (each heading states the finding)
1. *Each pathway carries evidence on MU*: timeline 0.82, images 0.71, combined 0.82; clinical alone at chance.
2. *The pathways hold at two external centres* → Fig 2. LUMIERE 0.77; UCSF single-scan images 0.80, about as
   high as models trained on UCSF.
3. *What each score rests on depends on the cohort* → Fig 3. MU: where the patient is in treatment; UCSF: how much
   the tumour enhances. Deep networks enter as the segmenters, and their direct scores track enhancing volume.
4. *The confidence keeps its coverage* → Fig 4. 0.82 / 0.87 / 0.78 against a target of 0.78; the disagreement
   warning picks out errors on MU; most scans sit where the evidence is thin, and the card says so.
5. *The reports are faithful to the record* → Fig 5. Numbers from v3.1 and the model-size ladder.

**4. Discussion**
1. The answer to the question, first sentence.
2. What the modules make possible: the image pathway where there are no dates; the timeline added without a new
   model; new cohorts add rows to the card.
3. A clinician's scan: eight weeks after RT, growing enhancement; the pathways disagree, the conformal set holds
   both outcomes, the card says the situation has few cases. PRISM states this; it does not decide.
4. Literature in context, concise and neutral (components exist separately; the combination appears new).
5. Limits: one development centre; documented, not expert-read, progression; small subgroups; the ladder and the
   reduced confidence design are exploratory; no clinician has read the reports.
6. Future work: pool the long-tail situations across cohorts and fine-tune on them; a clinician reader study.

## To the supplement or the reserve
Censoring, calibration, SHAP, the full flag set, the card's cells, UCSF label sensitivities and audit detail,
120-day risk detail, deep-network arms, report development and checker rules, the model-size ladder detail.

## Open for the author
- Split variance as supporting evidence (one paragraph + supplementary figure), or a short Results section?
- The new abstract, once this outline is accepted.

## Decisions log
1. (2026-10-25) Task and framing: detection at the scan is the task, a system that shows what a model uses is the
   framing, 120-day forecasting is the origin.
2. (2026-10-25) UCSF-ALPTDG enters the paper; Burdenko and UCSD-PTGBM are the follow-up.
3. (2026-10-25, extended 2026-10-26) RANO is not part of the paper: not in the text, the figures or the reports.
4. (2026-10-25) Christodoulou 2026 and Tikhonov 2025: concise context, results and a line on method.
5. (2026-10-25) New figures for this story; existing figures are not binding.
6. (2026-10-25) Space by contribution: the report gets little; deep learning only as much as it adds.
7. (2026-10-25) Name: PRISM, no acronym.
8. (2026-10-26) Within-phase and within-enhancement comparisons are diagnostics; the long tail is future work.
9. (2026-10-26) The reliability card is a lookup of measured results, not a learned confidence.
10. (2026-10-26) Two locked external tests are a main strength; claim transport, not better performance.
11. (2026-10-26) Capabilities first; challenges paired with modules; no accusation of the field; PRISM is modular.
12. (2026-10-26) Hosted models never receive patient records; reports are written by local models only.
13. (2026-10-26) Title: "PRISM: a modular system for glioma progression surveillance on MRI"; the name may still
    change (author open to alternatives), PRISM until decided.
