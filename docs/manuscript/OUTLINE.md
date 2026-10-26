# Outline: the argument of the PRISM paper (layer 1)

## System-first revision (approved 2026-10-26)

This revision supersedes the earlier model-audit-first framing below. The paper begins with the clinical problem:
glioblastoma and other aggressive gliomas need repeated MRI surveillance, but a scan is interpreted against prior
images and the course of treatment rather than in isolation. An initial radiomics model on MU-Glioma-Post motivates
the work; its prediction is evidence, not the clinical product. A bare score does not show the clinician its inputs,
the longitudinal picture, what it omitted or how competing evidence aligns.

**Question.** Can a system turn longitudinal imaging, treatment context and model evidence into a transparent report
for a surveillance scan, while showing how its components behave across cohorts?

**Claim.** PRISM assembles image-derived measurements, treatment context, separate image and timeline pathways,
uncertainty, provenance and a locally generated checked report. Its component models are evaluated internally and at
locked external cohorts; the report exposes their evidence and limits rather than substituting for clinical judgement.

**What the paper does not claim.** No clinician has evaluated a PRISM report, so the study does not establish improved
diagnosis, decision-making, workload or outcomes. The present results compare report versions and test automatic
grounding/completeness; they do not isolate the value of model fields against an otherwise identical no-model report.
That comparison is a stated next study, not an implied result.

### Main-text sequence

1. **Clinical need and motivation.** Progressive gliomas require longitudinal surveillance; the initial radiomics
   exercise motivates a move from prediction to a reportable evidence record.
2. **PRISM as the product.** A structured record joins measurements, treatment history, separate scores, confidence,
   provenance and a locally written report.
3. **Why separate components are retained.** Internal and locked external results establish how image and timeline
   pathways behave; the audit shows that the evidence carrying a score can differ by cohort.
4. **What a clinician receives.** One report shows the longitudinal facts, model evidence, what was not used and the
   situations in which evidence is thin. The report evaluation tests lexical grounding and required content, not
   clinical usefulness.
5. **What remains to test.** A report-without-model ablation and a clinician reader study.

### Primary report evidence

Report v3.1 is the primary report result because it is the newest, frozen cross-cohort evaluation: 406/406 reports
passed the lexical checker, all 220 reports requiring a thin-evidence tier stated it, and 28/30 perturbed records met
the prespecified follows rule. The checker verifies numbers, flags, confidence fields and forbidden wording against a
structured record. It is not a clinician assessment. Earlier v1/v2/v3 results are development history only.

### Displays

- **Figure 1:** PRISM as a system from serial data to a checked report.
- **Table 1:** cohorts and the evidence available to the report.
- **Figure 2:** component performance across MU, LUMIERE and UCSF.
- **Figure 3:** why one fused score hides the evidence each cohort supplies.
- **Figure 4:** report anatomy: longitudinal facts, separate evidence, uncertainty, provenance and omissions.
- **Table 2:** v3.1 automatic grounding/completeness evaluation, with its scope stated in the title and note.

The existing detailed outline is retained below as an analysis record until the main text and supplement have been
fully reconciled.

---

**Status: draft 3 (2026-10-26), accepted by the author 2026-10-26; skeleton in `paper/main.tex`.** **Council rounds 1 to 5 done (2026-10-26); read [council/COUNCIL_SUMMARY.md](council/COUNCIL_SUMMARY.md) for what changed and the decisions waiting for you.** Rebuilt on the author's framing of 2026-10-26
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
- **Claim:** PRISM does this. Its pathways rank scans at two external centres with models fitted once on
  MU-Glioma-Post (the risk scale and threshold need local recalibration; round 4); its audit shows what each score
  rests on in each cohort; its confidence keeps its stated coverage on average at all three centres (short for one
  outcome at each external centre); and its reports, written by a local language model and checked against the record, state the evidence
  without advice.
- **Investigation:** the modules → what each delivers on MU → locked tests on LUMIERE and UCSF → what each score
  rests on → the confidence → the report.

## The spine: challenges and the modules that handle them

| # | Known challenge of surveillance data | PRISM module | Evidence (Results) |
|---|---|---|---|
| C1 | Most datasets have images but no treatment dates | Separate pathways; the image pathway stands alone | Images alone transport to LUMIERE and UCSF (R2) |
| C2 | Progression is documented differently at each centre, so a score can rest on different evidence | Pathways kept apart, plus an audit of what each score rests on | MU: where the patient is in treatment; UCSF: enhancing volume (R3) |
| C3 | Cohorts are small, and a single split can move a score more than a model choice | Repeated patient-grouped CV; locked external tests with plans written in advance | Supporting paragraph + Supp. figure (split variance; single-scan radiomics setting) |
| C4 | The hardest situations (early after RT, growing enhancement) have few cases | Confidence: conformal set, pathway-disagreement warning, reliability card stating the evidence | Coverage on average at three centres; disagreement (medians fixed on MU) picks out errors on MU and LUMIERE; 35 of 249 scans in a tested situation (R4) |
| C5 | Volumes are noisy, the clinician must see what was measured, and patient data cannot leave the hospital | Deep segmentation feeding measurements and a figure; a local language model with a deterministic checker | Faithful reports in all three cohorts after one revision (R5) |

## Abstract (LOCKED 2026-10-24, text in [LOCKED.md](LOCKED.md))
**Flag for the author:** the locked abstract opens on the 0.80 split, has no external tests and no confidence, and
its order no longer matches this outline. A smallest edit will not fit; once this outline is accepted, a new
abstract will be proposed beside the locked one, and the locked text stays until you approve the change.

## The argument in figures

| # | Claim | Content |
|---|---|---|
| **Fig 1** | PRISM is built of modules, each answering a known challenge. | Scan + record → segmentation → measurements; clinical + timeline pathway; image pathway; combined score → confidence (conformal set, disagreement, card) → local report. One worked example scan. No RANO. **Round 3:** the Discussion's worked example (eight weeks after RT, growing enhancement, pathways disagree, set holds both outcomes, card has few cases) should become a panel here or in Fig 5; the text stays in the Discussion until the figure exists. |
| **Fig 2** | The models rank scans at two external centres without refitting. | AUC by pathway (clinical alone, timeline, images, combined) × cohort (MU internal, LUMIERE locked, UCSF locked, UCSF-trained as reference). Round 3: enhancing tumour volume alone as a reference bar in each cohort (NUMBERS.md 12C). |
| **Fig 3** | What each score rests on depends on the cohort, and the audit shows it. | (A) MU: the timeline's gain lies between phases of care. (B) UCSF: enhancing volume alone matches the image model. (C) The image-model ladder (single scan → + change → + schedule context), exploratory. |
| **Fig 4** | The confidence keeps its coverage on average and points to the doubtful scans. | (A) Conformal coverage at α 0.2 by cohort and pathway. (B) AUC with and without the disagreement warning. (C) The card: situations by cohort with their evidence tier. |
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
2. *The models rank scans at two external centres* → Fig 2 (enhancing volume alone as a reference bar; calibration
   and the MU threshold do not carry over, so a new centre recalibrates). LUMIERE 0.77; UCSF single-scan images 0.80 and the image
   pathway with change 0.73 (Q1 met); trained at UCSF 0.83 and 0.86 (council round 1).
3. *What each score rests on depends on the cohort* → Fig 3. MU: where the patient is in treatment; UCSF: how much
   the tumour enhances. Measurements come from the cohorts' masks; deep networks scoring UCSF scans directly track enhancing volume (Q4).
4. *The confidence keeps its coverage on average* → Fig 4 (coverage by outcome in the text). 0.82 / 0.87 / 0.78 against a target of 0.78; the disagreement
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
- Split variance as supporting evidence (one paragraph + supplementary figure), or a short Results section? Council
  round 1 recommends the paragraph (Methods 2.3, Supplementary S8 and Figure S2); pending author (decision 14).
- The proposed abstract (in `paper/main.tex`, flagged) to replace the locked one: approve or edit.

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
14. (2026-10-26) Split variance: one paragraph in Methods 2.3 with a pointer to Supplementary S8 / Figure S2; the UCSF
    own-split result goes to RESERVE.md. Council round 1 recommendation, pending author.
15. (2026-10-26) Council round 1 (coordinator rulings, pending author): UCSF gives both planned image models (single scan
    0.80; with change 0.73, the system's pathway; UCSF-trained 0.86 / 0.83); claim transfer, not best performance. UCSF
    calls rest largely on enhancement (enhancing volume alone 0.88 as the simple baseline). Coverage "met the
    pre-specified threshold" on point estimates. Faithfulness always disclosed as after one revision. Deep networks:
    measurements come from the cohorts' masks; one sentence on UCSF Q4. Short cohort names (MU, UCSF) after first use.
    Record: `docs/manuscript/council/round1_decisions.md`.
16. (2026-10-26) Council round 2 (coordinator rulings, pending author): abstract keeps the UCSF numbers 0.80 and 0.73 and
    says "a model trained there did better" (0.86 in 3.2); 3.2 keeps "about the same when trained there" in words (0.83 in
    Figure 2); the card's claim is the distribution by cohort (MU 35 of 249 tested, LUMIERE mostly tested, UCSF none);
    Table 1 MU age 62.5 (same population as TABLE1_COHORT.md); pointers to unwritten supplement sections are
    `\todo{Supplementary section: <topic>}`; deep networks described as having found the evidence the measurements hold;
    repeated phrases ("rest on", "fitted once ... unchanged", the long scan phrase) defined once, short forms after. Main
    text 3,898 words. Record: `docs/manuscript/council/round2_decisions.md`.
17. (2026-10-26) Council round 3 (coordinator rulings, pending author): abstract from the voice reviewer's proposal, opening
    on the clinical reason, with 0.86 for the UCSF-trained image pathway and coverage "on point estimates" (150 words). The
    within-phase result follows the MU 0.82 in 3.1. Coverage, the agreement rule (cohort medians; MU-fixed re-run in
    round 4), the card (post hoc) and the reports ("a lexical check of numbers, flags and wording"; what it cannot catch;
    second-evaluation records exclude the revision's development patients) narrowed. Exploratory analyses listed once
    in Methods 2.3 and marked "(exploratory)" at most once per Results paragraph. Deep-network detail, per-cohort S2 / S3
    numbers and the image-model ladder's first step to RESERVE / supplement; the ladder is two sentences; the report-model
    comparison one sentence. No volumetric response-rule baseline (author: no RANO); enhancing volume alone is the simple
    reference. The worked example stays in the Discussion and should become a panel in Fig 1 or Fig 5. Main text 3,992
    words (round 2: 3,898). Record: `docs/manuscript/council/round3_decisions.md`.
18. (2026-10-26) Council round 4 (coordinator rulings, pending author): "transfer" means ranking; calibration and the MU
    threshold do not carry over to UCSF, stated in 3.2, one Discussion sentence for builders and the Limits. Coverage
    "on average", short for one outcome at LUMIERE and UCSF (abstract, Introduction, 3.4 heading and text, Figure 4).
    The agreement rule uses medians fixed on MU (computable at a scan); the cohort-median result is one clause.
    Enhancing volume alone is the reference bar in Figure 2 (MU 0.62, LUMIERE 0.66; UCSF 0.88 in 3.3). The ladder's
    middle step is given with its interval, which includes zero. One-sentence Conclusion. Trim to 3,898 words (round 3:
    3,992). Record: `docs/manuscript/council/round4_decisions.md`.
19. (2026-10-26) Council round 5 (final editor, pending author): audit's nine wrong claims fixed (plan timing wording;
    external schedule inputs; planned agreement result first, MU-fixed rule second; report-model comparison planned;
    card built from the cohort's own held-out results, 54 of 146 MU scans tested; combined 0.82 named apart from the
    planned model); UCSF combined 0.86 in 3.2 with its caveat; one dagger marker for analyses not fixed in advance;
    missing-input handling in 2.1; 0.60 in the Limits; abstract proposal revised (149 words). Main text 3,946 words.
    Record: `docs/manuscript/council/round5_decisions.md`; overview: `docs/manuscript/council/COUNCIL_SUMMARY.md`.
