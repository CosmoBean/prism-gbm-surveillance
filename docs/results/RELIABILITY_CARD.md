# PRISM reliability card: what has been measured for this scan's situation

**EXPLORATORY (post hoc).** The situations, the tier rule, the agreement rule and the checker rule were all defined
after the MU detection, LUMIERE and UCSF results had been seen. The card is a **lookup of results already measured**,
not a learned confidence model (author's decision: OUTLINE.md, decisions log items 8–10). Nothing is fitted for the card.
Aggregate numbers only; patient-level files stay under `outputs/` (git-ignored).

Code:
- `prism/audit/reliability.py`: situations, tier rule, bootstrap, agreement, building and rendering the card. The tier
  rule is in the module docstring.
- `prism/analyses/reliability_card.py` (`PYTHONPATH=. .venv/bin/python -m prism card [--steps table records evaluate]`).
  It takes a few minutes on 4 CPUs, most of it re-creating the MU I_pure out-of-fold scores.
- `prism/report/facts_card.py`: the `card.*` report facts.
- `prism/report/checker.py`: `card_check`, and `check(..., card=True)`.
- `tests/test_reliability_card.py`.

Outputs: `outputs/results/analyses/reliability_card/` (lookup.csv, agreement.csv, checks.csv, scans_<cohort>.csv.gz,
mu_scores.csv.gz, mu_ood.csv.gz, records/, checker_on_existing_reports*.csv, card_tiers_of_report_scans.csv, run.log).

## Purpose

At every scan, PRISM's report states four things:
1. which situation the scan is in;
2. how well each pathway (timeline, images, both) has been shown to detect progression in that situation, using only
   results already measured;
3. whether the two pathways agree at this scan;
4. whether the scan's inputs lie inside the range the model was trained on.

Where nothing was measured, or too little, the card says so. That is the point of it: the early post-RT window and
enhancement that grows without progression are exactly where the card should say "few cases".

## Situations

A situation is one cell: phase of care × enhancement state. Only the scan's **exact** cell is looked up. Cohorts are
**never pooled**, and the card shows no marginal (phase-only or enhancement-only) number in place of the exact cell.

| phase | definition |
|---|---|
| before RT end | pre-RT or during RT (merged; both are tiny and both come before post-RT change) |
| early post-RT | ≤ 84 d (12 weeks) after RT end |
| later post-RT | > 84 d after RT end |
| unknown | RT dates missing: all of LUMIERE; MU patients with no RT date in the record; UCSF scans with no RT or an undated RT |

| enhancement state | definition |
|---|---|
| ET absent | enhancing tumour < 0.1 cc (`PD_MIN_NADIR_CC`) |
| no previous | ET present, no earlier scan to compare with |
| ET not increased | ET present, not increased since the previous scan |
| ET increased | the volumetric rule `measurements.volumetric_pd`, applied to the previous scan: ≥ 1 cc and ≥ 40% from a measurable volume, or ≥ 1 cc of new enhancement from about 0 cc |
| unknown | no usable segmentation (LUMIERE only) |

**Council decision (3 independent advisers, recorded before the table was computed).** Two of the three chose
"exact cell only", which is also the most conservative option; it was adopted. The third chose "exact cell first,
with labelled marginal cells as context when it is not tested". The reason the majority gave: a marginal AUC mixes
situations. On MU, 56 of 64 progressions are later post-RT. On UCSF, ET volume alone separates the classes (0.88). So a
marginal number would imply performance that was never measured in the scan's own situation.

All three advisers agreed on the merges:
- pre-RT and during RT are merged;
- ET absent and no previous are not merged (nothing to detect is not the same as a comparison that cannot be made);
- LUMIERE's rater flag "< 3 months after RT" is not mapped onto early post-RT, because its definition differs. So
  LUMIERE's phase is unknown.

## Pathways and scores (all grade 4; every score existed or was re-created and checked)

| cohort | timeline | images | both | scores |
|---|---|---|---|---|
| MU (development) | B1 | I_pure | B1 + I_pure | detection out-of-fold, 5 × 5 CV; all scans, primary negatives (64 / 117) |
| LUMIERE (locked) | Tbase (no RT dates: days since surgery, rater flag) | T_img (LUMIERE image set) | T | locked MU fit (73 / 105) |
| UCSF (locked) | A-Tbase (approximate) | A-Ipure | A-T | locked MU fit; scan 2, `pos_s2_pm30` vs primary negatives (29 / 40) |
| UCSF (trained on UCSF) | B-Tl | Ipure | B-Tl + Ipure | UCSF 5 × 5 CV; same set |

Checks (`checks.csv`):
- MU B1 equals the published detection OOF to 1e-9 (asserted).
- LUMIERE Tbase and T equal the published locked predictions to 1e-9 (asserted).
- Every overall AUC reproduces the published value: MU 0.845 / 0.712; LUMIERE 0.689 / 0.655 / 0.773; UCSF locked
  0.561 / 0.726 / 0.856; UCSF internal 0.669 / 0.863 / 0.871.
- The MU I_pure and B1 + I_pure scores, and LUMIERE T_img, were re-created with the exploratory scripts' code. The
  earlier runs had printed these values but not saved them.
- The LUMIERE image-only AUC is 0.6545. STORY.md rounds it to 0.66, from 0.655.

## Tier rule

For each cohort × cell (the counts are the same for every pathway of a cohort):
- **tested**: ≥ 10 progression **and** ≥ 10 non-progression scans. The card shows the AUC and its 95% CI.
- **few cases**: at least one scan, but fewer than 10 of either class. The card shows counts only, never an AUC.
- **not tested**: no scan of this situation in that cohort.

How the AUC and CI are computed:
- AUC is the mean over CV repeats of the pooled AUC (a locked test has one "repeat").
- The CI is the 2.5–97.5 percentiles of 1,000 patient-cluster bootstrap draws (seed 20261021), resampling patients
  with all their scans.
- AUCs are computed only for tested cells.

## The lookup table

Positives / negatives per cell. AUC (95% CI) is shown only for tested cells. Cells with no scans in a cohort are not
listed (not tested).

| cohort | situation (phase · enhancement) | pos / neg | tier | timeline | images | both |
|---|---|---|---|---|---|---|
| MU | before RT end · no previous | 0 / 12 | few cases | | | |
| MU | early post-RT · ET absent | 0 / 3 | few cases | | | |
| MU | early post-RT · ET increased | 1 / 8 | few cases | | | |
| MU | early post-RT · ET not increased | 3 / 8 | few cases | | | |
| MU | early post-RT · no previous | 0 / 32 | few cases | | | |
| MU | later post-RT · ET absent | 2 / 7 | few cases | | | |
| MU | later post-RT · ET increased | 16 / 8 | few cases | | | |
| MU | **later post-RT · ET not increased** | 38 / 16 | **tested** | 0.58 (0.44–0.77) | 0.77 (0.65–0.88) | 0.61 (0.43–0.80) |
| MU | later post-RT · no previous | 0 / 1 | few cases | | | |
| MU | unknown · ET absent / increased / not increased / no previous | 0 / 3, 0 / 3, 4 / 9, 0 / 7 | few cases | | | |
| LUMIERE | **unknown · ET absent** | 13 / 44 | **tested** | 0.59 (0.38–0.81) | 0.53 (0.31–0.76) | 0.67 (0.47–0.86) |
| LUMIERE | **unknown · ET increased** | 28 / 21 | **tested** | 0.91 (0.80–0.99) | 0.61 (0.44–0.78) | 0.83 (0.68–0.94) |
| LUMIERE | **unknown · ET not increased** | 25 / 28 | **tested** | 0.85 (0.69–0.98) | 0.55 (0.39–0.72) | 0.77 (0.59–0.95) |
| LUMIERE | unknown · no previous / unknown | 2 / 2, 5 / 10 | few cases | | | |
| UCSF locked and UCSF-trained | later post-RT · ET increased | 20 / 5 | few cases | | | |
| UCSF locked and UCSF-trained | later post-RT · ET not increased | 7 / 21 | few cases | | | |
| UCSF locked and UCSF-trained | later post-RT · ET absent | 0 / 12 | few cases | | | |
| UCSF locked and UCSF-trained | early post-RT · ET not increased; unknown · ET not increased | 0 / 2; 2 / 0 | few cases | | | |
| *reference, not a card cell* | MU overall | 64 / 117 | | 0.84 (0.78–0.91) | 0.71 (0.64–0.78) | 0.84 (0.78–0.90) |
| *reference* | LUMIERE overall | 73 / 105 | | 0.69 (0.60–0.80) | 0.65 (0.56–0.73) | 0.77 (0.68–0.86) |
| *reference* | UCSF locked overall | 29 / 40 | | 0.56 (0.43–0.69) | 0.73 (0.60–0.84) | 0.86 (0.76–0.93) |
| *reference* | UCSF-trained overall | 29 / 40 | | 0.67 (0.55–0.78) | 0.86 (0.78–0.94) | 0.87 (0.79–0.94) |

Reading:
- **Four cells in all are tested: one on MU, three on LUMIERE, none on UCSF.**
  - MU's tested cell holds 54 of 181 evaluation scans.
  - Among the 249 grade-4 index scans that have reports, the card is tested for 35, few cases for 212 and not tested
    for 2.
  - So most of the time the honest answer is "few cases". The early post-RT window has at most 3 progression scans in
    any cell on MU and none externally.
- **Inside MU's one tested cell, the images rank better than the timeline:** later post-RT, ET present and not
  increased, images 0.77 against timeline 0.58. The intervals overlap. This is the within-phase direction already seen
  (images about 0.65–0.68 within phase, DETECTION_TASK.md), now within one enhancement state as well. It is a
  diagnostic, not a precise claim (decision 8).
- **On LUMIERE, within each enhancement state, the transportable timeline ranks better than the images (0.85–0.91 vs
  0.55–0.61).** Here the images' overall 0.65 comes mostly from telling enhancement states apart. On UCSF no cell is
  tested; the one with most scans (ET increased, 20 / 5) is where the UCSF audit found the images fall to 0.53–0.65.
- The overall rows are references. The card never shows them for a scan.

## Pathway agreement

**Rule.** Each pathway's score at the scan is "above" or "below" the median of that pathway's scores over the
cohort's evaluation set. This uses scores only, no labels; on MU and UCSF-trained the median is taken per CV repeat.
The pathways agree when both scores are on the same side.

The table is descriptive. For subsets that change with the repeat, counts are the mean over repeats, and the tier
uses the smallest repeat.

| cohort | subset | pos / neg | timeline | images | both | progression among scans with this direction |
|---|---|---|---|---|---|---|
| MU | agree | 42 / 70 | 0.91 (0.85–0.96) | 0.90 (0.86–0.94) | 0.91 (0.86–0.96) | both above 73%; both below 4% |
| MU | disagree | 22 / 47 | 0.74 (0.63–0.86) | 0.31 (0.18–0.44) | 0.64 (0.54–0.76) | timeline above, images below 49%; images above, timeline below 14% |
| LUMIERE | agree | 33 / 43 | 0.81 (0.67–0.96) | 0.80 (0.66–0.93) | 0.83 (0.68–0.95) | 71%; 16% |
| LUMIERE | disagree | 40 / 62 | 0.61 (0.51–0.76) | 0.54 (0.41–0.64) | 0.72 (0.62–0.82) | 41%; 37% |
| UCSF locked | agree | 11 / 20 | 0.71 (0.49–0.90) | 0.74 (0.54–0.90) | 0.85 (0.67–0.99) | 53%; 19% |
| UCSF locked | disagree | 18 / 20 | 0.44 (0.24–0.63) | 0.71 (0.54–0.87) | 0.87 (0.73–0.96) | 32%; 63% |
| UCSF-trained | agree | 17 / 23 | 0.84 (0.72–0.94) | 0.93 (0.85–0.99) | 0.92 (0.84–0.99) | 79%; 8% |
| UCSF-trained | disagree | 12 / 17 | 0.38 (0.19–0.58) | 0.74 (0.55–0.90) | 0.74 (0.55–0.89) | 24%; 57% |

Reading:
- **When the pathways agree, the scan is usually easy.** 53–79% of scans with both scores above the median are
  progression scans, against 4–19% with both below. The combined score ranks agreeing scans at 0.83–0.92, against
  0.64–0.74 for disagreeing ones on MU, LUMIERE and UCSF-trained. UCSF locked is the exception (0.85 vs 0.87).
- **When they disagree, which pathway is right depends on the cohort, as in the rest of the paper.**
  - On MU the timeline is right more often: 49% progression when only the timeline is high, 14% when only the images
    are.
  - On UCSF the images are right more often: 63% and 57% progression when only the images are high, 24–32% when only
    the timeline is.
  - On LUMIERE neither is (41% vs 37%).
- **Caution.** AUCs inside agree / disagree subsets are partly built in by the split. Agreeing scans have
  same-direction extreme scores. Among disagreeing scans, one pathway must rank against the other, hence images 0.31
  on MU and timeline 0.38–0.44 on UCSF. The progression shares are the readable part. They also depend on each
  cohort's case mix: the evaluation sets are 35–42% progression.

## Inputs inside the training range

The card reuses `prism.audit.model.ood_ranges` / `ood_flags` unchanged on the detection inputs (B1 + I_pure):
- the training 1st–99th percentile of each continuous input, taken on the training rows of the scan's outer fold;
- plus "IDH / MGMT unknown".

Among the 249 report scans (repeat 0), 123 are inside the range and 126 are flagged. The most common reasons are MGMT
unknown (39), RT duration (13), IDH unknown (11), and cavity volume or its change (10–11). With about 60 continuous
inputs, each with 2% tails, a flag on half the scans is expected. The flag says "this scan is atypical for training";
it is not a measured loss of accuracy. The card is not computed per scan for LUMIERE or UCSF, because no report records
exist there.

## Integration into the record and the report

- `reliability_card.attach_cards(recs, repeat)` adds a `reliability_card` block to each report record. The block holds
  the situation, the evidence for every cohort, the tier of the own cohort (MU), agreement and range. Nothing else in
  the record changes.
- The scan's pathway scores are its detection out-of-fold scores from the same CV repeat as the record. The patient is
  not in training.
- Card-augmented copies of the two evaluation sets are in `reliability_card/records/{report_agent_eval (repeat 0),
  report_usefulness_eval (repeat 1)}/`. The original record folders are untouched. No LLM was run, and no report was
  regenerated.
- `facts_card.card_facts(rec)` gives the `card.*` facts, which a card-aware report uses as `{**facts_v2(rec),
  **card_facts(rec)}`. They include:
  - `card.situation`, `card.tier`, `card.tier_statement`, counts;
  - `card.<pathway>.auc/auc_low/auc_high`, only when tested;
  - `card.<other cohort>.*`;
  - `card.agreement`, `card.agreement_progression_percent`, `card.agreement_<pathway>_auc*`;
  - `card.inputs_in_range`, `card.inputs_out_of_range`.
- AUC keys exist only for tested cells, so a report cannot cite an AUC the card does not show.

### Example card (MU scan, anonymised; rendered by `reliability.render_text`)

This is the scenario of the outline's Discussion: a scan 8 weeks after RT, with growing enhancement, where the
pathways disagree.

```
RELIABILITY CARD (EXPLORATORY: post hoc lookup of results already measured; not a learned confidence)
Situation: early post-RT (within 12 weeks of RT end); enhancing tumour increased since the previous scan
This situation in MU-Glioma-Post, development (cross-validated, out-of-fold): few cases: 1 progression / 8 non-progression scans
  elsewhere, LUMIERE, locked external test: not tested: 0 progression / 0 non-progression scans
  elsewhere, UCSF-ALPTDG scan 2, locked external test: not tested: 0 progression / 0 non-progression scans
  elsewhere, UCSF-ALPTDG scan 2, models trained on UCSF (cross-validated): not tested: 0 progression / 0 non-progression scans
Pathways: disagree: timeline below its cohort median, images above theirs (measured where they disagree: tested: 22 progression / 47 non-progression scans; AUC timeline 0.74 (0.63-0.86), images 0.31 (0.18-0.44), both 0.64 (0.54-0.76))
  scans with this direction in the cohort's evaluation set: 14% were progression scans
Inputs: inside the training range
Tier rule: tested = >= 10 progression and >= 10 non-progression scans in this exact situation (AUC and 95% patient-bootstrap CI shown); few cases = fewer (counts only); not tested = none.
```

## What the checker now enforces (`checker.card_check`, via `check(..., card=True)`)

The rule applies only when the facts contain `card.*` keys and the caller passes `card=True`. The default is
unchanged.
1. **No AUC or confidence that differs from the card.**
   - A claim is a performance claim if it mentions AUC, area under, c-statistic, concordance index, discrimination,
     performance (not "performance status"), performs, accuracy, reliability, or confidence (not "confidence
     interval").
   - Every number in such a claim must equal a number held by a `card.*` field, with the existing rounding and percent
     rules.
   - A cited non-card field does not count. So "development AUC 0.70" (the 120-day model's `model.cv_auc`) fails.
2. **No omitted tier.** When the card's tier is "few cases" or "not tested", a claim must state it:
   - it must match the tier's words ("few cases / too few / only N …", or "not tested / not measured / untested …");
   - in a cited report, it must cite `card.tier` or `card.tier_statement`; prose needs only the keywords;
   - a cited claim that uses the other tier's words is "tier inconsistent".
3. **No qualitative overclaim** when the tier is not "tested". "High confidence", "reliable performance", "well
   validated" or "tested in this situation" fail, unless the sentence has a negation word.
4. The report passes only if the existing checks and the card rule both pass.

### Effect on the existing reports (evaluated separately; `checker_on_existing_reports_summary.csv`)

The existing reports predate the card and were never asked to state it, so the new rule is evaluated on its own and
the published numbers stand. With the unchanged checker, the published counts are reproduced exactly:
- v1 arm A 236 / 249;
- arm B 171 / 249;
- arm C 243 / 249;
- v2 249 / 249;
- v1 on repeat 1 238 / 249.

Against card-augmented facts:

| report set | arm | card tier required (few cases / not tested) | tier stated | performance claims with a number not on the card | overclaims | pass, existing checks + card rule |
|---|---|---|---|---|---|---|
| REPORT_AGENT eval (repeat 0) | A | 214 | 0 of 214 | 0 | 0 | 35 / 249 |
| | B (original prompt) | 214 | 3 of 214 (keywords, by chance) | 15 reports | 5 | 24 / 249 |
| | C | 214 | 0 of 214 | 0 | 0 | 34 / 249 |
| REPORT_USEFULNESS eval (repeat 1) | v1 | 214 | 0 of 214 | 0 | 0 | 35 / 249 |
| | v2 | 214 | 0 of 214 | 0 | 0 | 35 / 249 |

So:
- The grounded reports never state an AUC or a confidence that conflicts with the card. Arms A, C, v1 and v2 have no
  performance claim with an off-card number.
- They fail the card rule only by omission: no report could state a tier it was never given. The 35 passes are the
  scans whose cell is tested.
- Arm B (the original PRISM prompt) also writes confidence language and numbers that are not on the card ("the
  model's confidence…", the 0.48 / 0.75 cut-offs).
- A card-aware prompt has to be written and tested on a development set before any claim about card faithfulness.
  That needs an LLM run, which was not done here.

## Limits

- **Exploratory and post hoc.** The cells, the volumetric "increased" rule, the median split and the checker rule were
  all chosen after the results were known.
- **Small cells.** Four tested cells in total. Even tested cells have wide intervals; MU's has 16 negatives.
- **Detection only.** The card describes the detection pathways (does this scan show progression). The existing
  report's headline is the 120-day risk of the timeline-only model. The two are kept apart: the card's AUCs are not
  the risk model's.
- **Pathways differ by cohort.** LUMIERE has no RT dates and a different segmentation (DeepBraTumIA). "Timeline"
  there is days since surgery plus the rater flag. UCSF has scan 2 only, with an assumed 6-week RT course. Cohort rows
  are therefore shown separately and never pooled.
- **Labels differ by cohort.** MU uses documented progression; LUMIERE uses the rater's PD; UCSF uses a clinical call,
  largely enhancement-based (UCSF_AUDIT.md). The same cell can mean a different task in different cohorts.
- **MU "unknown" phase** means no RT date anywhere in the patient's record, which is a property of the data. A pre-RT
  scan whose RT date is recorded later is "before RT end".
- **Out-of-range** reuses the audit layer's percentile rule. It flags half the scans and is not linked to measured
  accuracy.
- **Lexical checker.** The checker sees numbers, tier words and citations, not meaning. A sentence can match the
  tier's words and still misstate what the tier means.
- **Not evaluated by an LLM.** No report has yet been generated with the card. No clinician has read a card.
