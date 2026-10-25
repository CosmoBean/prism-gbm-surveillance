# PRISM report version 3: detection at the scan, written from the system record

Plan: [SYSTEM_PLAN.md](SYSTEM_PLAN.md) sections 3 (S5–S7), 4 and 5 (commit e7cba80). Background:
[REPORT_AGENT.md](REPORT_AGENT.md), [REPORT_USEFULNESS.md](REPORT_USEFULNESS.md), [RELIABILITY_CARD.md](RELIABILITY_CARD.md).

## Rules fixed before any evaluation report (written 2026-10-25, during development)

Where the plan does not settle a detail, these choices were made during development and before any evaluation or
perturbation report was generated.

- **Evaluation set.** MU: records with `eval_intended_use` (grade 4, intended use, primary detection set) of the 60
  patients not in the development set; LUMIERE: all 178 detection scans; UCSF: all 140 grade-4 scan-2 records. Only
  the membership column of the `*_EVALUATION_ONLY.csv` files is read; labels are never read by this module.
- **S5.** A report passes when `checker.check(claims, facts_v3(record), card=True)` passes (v3 rules below). Met if
  the pass rate is ≥ 0.95 in each cohort (and overall), Wilson 95% CI reported.
- **S6.** Among reports whose card tier is "few cases" or "not tested", the share whose text states the tier (the
  card rule's `tier_mentioned`: tier words in a claim citing `card.tier` / `card.tier_statement`). Met if 100%.
- **S7.** 30 evaluation records (seed 0), 6 per kind, each with one field changed (`perturb_one`):
  - card tier: tested → few cases (4 / 6 scans, no AUC); few cases → not tested; not tested → few cases;
  - agreement: the image score moved 0.15 to the other side of its median (agreement flips; the measured agreement
    statistics are removed, since they would no longer apply);
  - ET change: the previous ET volume set so that the change is −5.0 cc (if it was ≥ 0) or +5.0 cc;
  - out-of-range flag: switched off (reasons removed) or on (one invented reason);
  - conformal set: the combined 80% set changed from both outcomes to a singleton, or from a singleton to both.

  **Follows** (primary): the report states the new value and not the old one — tier: the new tier stated as the card
  rule requires and none of the old tier's words (for "tested": no AUC); agreement: agreement described correctly
  for the new record and the new image score written; ET change: the new magnitude written with the right direction
  and the old magnitude absent; out of range: on → the flag mentioned, off → not described as raised and the old
  reason absent; conformal: the combined 80% set described with the new phrase and no other. S7 met if
  follows ≥ 27 / 30 (90%). Secondary: follows and the full check passes on the perturbed record.

## Design

Code: `prism/report/facts_v3.py`, `prompts_v3.py`, `sections_v3.py`, the v3 part of `checker.py`;
`prism/analyses/report_v3.py` (`PYTHONPATH=. .venv/bin/python -m prism.analyses.report_v3 --steps ...`; steps select,
sets, stress, requests, generate, evaluate, render, examples); `tests/test_report_v3.py`. Outputs:
`outputs/results/analyses/report_v3/` (patient-level, not in git).

- **Input.** One system record (`prism.system_record/1`, `outputs/results/analyses/system/records_*.jsonl`). Labels
  live in separate `*_EVALUATION_ONLY.csv` files and never reach the facts.
- **Facts v3** (the LLM's only input, the checker's only reference): flat, pre-rounded (scores and medians 2 dp,
  volumes 1 dp signed changes, percentages and days 0 dp, percent changes only from ≥ 1 cc). Everything whose
  wording can be fixed is pre-written as a `*statement` field:
  - each pathway's score with its side of the cohort median (the median comes from the card's agreement block; the
    combined score has no median in the record, so it is stated without one) and what the pathway is based on (by
    model: B1, I_pure, Tbase, T_img, the three-volume model, T; UCSF timing marked as approximated);
  - pathway agreement ("agree" / "disagree" and both sides);
  - the card tier in plain words ("few cases: only 3 progression and no non-progression scans of this situation in
    MU-Glioma-Post, too few to measure how well the pathways work here"; "tested: … AUC timeline 0.58 (95% CI …)";
    "not tested: …"), the measured agreement statistic;
  - each conformal set (80% and 90%, all three scores) as one of four fixed phrases ("both outcomes", "progression
    only", "no progression only", "empty") with its meaning;
  - volume changes from the previous scan and from the smallest earlier volume, in words;
  - the four flags (pathways disagree, out of training range with plain-language reasons, thin evidence = card tier
    few cases / not tested, conformal set with both outcomes) with reasons.
- **Report.** Header, the segmentation figure (attached by the renderer; the LLM never sees images), four sections
  each with LLM prose followed by a deterministic table (1 what the scan shows, 2 the two pathways, 3 the combined
  score, 4 how much to trust this here: card, flags), and a fixed limitations paragraph. Markdown and a
  self-contained HTML page.
- **Prompt v3** (`prompts_v3.py`, frozen at v3.3): v1/v2 content rules (facts only, copy numbers as digits, cite
  keys, no diagnosis, volumes indicative), plus: no recommendation, advice, review, referral or decision; no
  probability words; no "confidence / reliability / accuracy / performance" except a copied card AUC; copy the fixed
  tier, conformal and agreement phrases; British spelling; one sentence per active flag ("The <name> flag is raised:
  <reason>."). JSON output with a section tag per sentence (≤ 24 sentences).
- **Serving.** Qwen/Qwen3.8-27B at the pinned revision (`1d4bf0f2…`), bf16 (fits; no FP8 needed), vLLM 0.31.0 in
  `/project/community/sbandred/envs/prism-llm`, tensor parallel 1 on one H100 of job 161514, greedy, seed 0,
  non-thinking mode, structured JSON output, offline.

## Checker v3 (frozen before the evaluation reports)

Applied by `check(claims, F, card=True)` whenever `F["system.version"] == "v3"`; every earlier evaluation goes
through the unchanged v1/v2/card code. A report passes only if all hold:
1. **Numbers**: every number equals a number in a cited field (existing rule); **number words** (three … ninety,
   hundred, half, twice, …) count as unsupported (closes the gap found in REPORT_USEFULNESS.md).
2. **Flags**: every active flag mentioned (its words, citing the flag or its source keys); an inactive out-of-range
   flag described as raised is spurious.
3. **Conformal**: a claim about a conformal set must cite it and use exactly the fixed phrase(s) of the cited set(s);
   uncited conformal claims fail; the combined score's 80% set must be stated (citing the conformal-flag keys counts
   as citing that set).
4. **Agreement**: stated (citing `pathways.*`), never described the other way; a pathway placed above / below its
   median must match its side.
5. **Required content**: each of the three scores written from its field; the enhancing volume when measured.
6. **Forbidden**: v1 patterns plus diagnosis ("shows / indicates progression", "is a progression scan"), advice and
   decision ("should", "must", "need to", "clinician review", "next step", "decision / decide", "intervention"), and
   probability words ("likely", "high risk", "reassuring", "concerning", …).
7. **Card rule** (`card_check`, unchanged): tier stated when few cases / not tested; no performance number off the
   card; no overclaim.

Frozen 2026-10-25T22:43:43Z, before the first evaluation request (generation started 22:44:17Z). Git blob hashes
(`git hash-object`; also in `outputs/results/analyses/report_v3/FROZEN_hashes.txt`), unchanged after the run:
`checker.py 26d6637a6570549e46a5ca7be7a059033e3a0ac7`, `facts_v3.py a14b2fbf6b6c2a40082e734bea07648a09873b55`,
`prompts_v3.py a621edc45e26fbb88e1ee7a6fdaeff3373d571c3`. Unit tests: 16 in `tests/test_report_v3.py` (79 in the
suite, all pass).

## Development (20 MU patients, 32 intended-use scans; seed 20261026, selected before any generation)

`dev_patients.json` (selected 22:19Z, before any report). Before the records existed, the facts, checker and
renderer were built against mock records derived from the reliability-card tables; the mock was dropped when the
records arrived (no report was generated on it).

| version | change | pass | median words |
|---|---|---|---|
| v3.0 | first version | 23/32 | 206 |
| v3.0, checker fix | all 9 failures were the conformal flag sentence citing only the flag keys, whose reason *is* the combined 80% set; the checker now counts those keys as citing that set | 32/32 | 206 |
| v3.1 | volumes must say "indicative, not a RANO assessment"; agreement statistic copied whole or left out (v3.0 shortened it to "14% of similar scans were progression scans"); flag sentences copy the reason in full; score meaning in its own sentence; LUMIERE rater flag added to (a) | 12/32 | 284 |
| v3.2 | the 16-sentence schema cap had cut off the flag sentences (all 20 failures): cap 24, pathway basis and score in one sentence, flag sentences declared required | 32/32 | 302 |
| v3.3 (frozen) | facts wording: "no progression" instead of "only 0 progression", flag name "thin evidence", disagreement reason without repetition; capital letter and full stop rule | 32/32 | 332 |

The development set holds MU scans only, so the LUMIERE- and UCSF-specific facts (rater flag, necrosis with
cavity, the three-volume image model) reached the LLM for the first time in the evaluation.

## Results (432 evaluation reports, 30 perturbed; `summary_eval.csv`, `summary_stress.csv`)

| cohort | n | S5: pass (Wilson 95% CI) | S5 | S6: tier stated (few cases / not tested) | S6 |
|---|---|---|---|---|---|
| MU (intended use, 60 patients) | 114 | 114/114 = 1.00 (0.97–1.00) | **met** | 71/71 | **met** |
| LUMIERE | 178 | **0/178 = 0.00 (0.00–0.02)** | **not met** | 19/19 | **met** |
| UCSF grade-4 scan 2 | 140 | 140/140 = 1.00 (0.97–1.00) | **met** | 140/140 | **met** |
| all | 432 | 254/432 = 0.59 (0.54–0.63) | not met | 230/230 | met |

- **The LUMIERE failure is one design error, not the model.** Every LUMIERE report has the same unsupported number:
  "The rater did not record the scan as within 3 months after radiotherapy." The prompt (added in v3.1) asks for the
  rater flag in those words, but the fact holds only "yes" / "no", so the "3" is not in any cited field. Five reports
  also write "the three segmentation volumes" (copied from the facts, where "three" is a number word, which the
  checker forbids). Development could not show it: it has no LUMIERE record.
  **EXPLORATORY (post hoc):** with the "3" placed in the rater field and "three" written as a digit in the facts,
  178/178 LUMIERE reports pass the frozen checker; there is no other failure of any kind. The pre-specified result
  stays 0/178.
- **Everything else, all 432:** 432 parsed, 0 truncated; 0 invalid citations; 0 active flags omitted, 0 spurious;
  0 forbidden content in any category (diagnosis, RANO, advice / decision, certainty, probability words); 0 conformal
  sets misdescribed; 0 agreement errors; required content present in all; card rule passed in all.
- **S7 (perturbations): follows 29/30 — met** (agreement 6/6, card tier 6/6, conformal 6/6, out of range 6/6, ET
  change 5/6). The one miss is a rule artefact: a LUMIERE scan whose ET change was 0.0 cc and whose current ET is
  0.0 cc; the report states the new change correctly ("5.0 cc smaller … 100% less"), but "0.0" appears as the
  current volume. Read: the report followed the change in 30/30 (EXPLORATORY reading). Follows and full check:
  14/30; all 16 check failures are the LUMIERE rater "3" above.
- **Length and cost.** Median 347 words (MU), 360 (LUMIERE), 338 (UCSF); about 1,300 output tokens. Batched
  1.19 s per report on one H100 (516 s for 432), plus about 2 min model load; the whole evaluation and perturbation
  generation took 14 min.

### Failure and wording examples (paraphrased; read by an AI agent, not a clinician)
- Rater-flag sentence with a "3" that is not in the facts (all LUMIERE reports).
- Correct but awkward: the few-cases wording "only 16 progression and only 8 non-progression scans" when only one
  count is below 10; some change sentences have no verb ("Enhancing tumour 0.8 cc smaller than at the previous
  scan…").
- Correct but easy to misread: a UCSF report states the combined 80% set as "progression only" next to an agreement
  statistic of 19% progression among such scans. Both are faithful to the record; the locked combined score
  overpredicts on UCSF (UCSF_RESULTS.md), and the report does not reconcile the two. A reader study would have to
  test this.
- The three example reports (`examples.json`: the first record id with a figure per cohort, chosen by rule) were
  rendered as HTML with the figure embedded (`reports/eval/*.html`) and read: numbers match the record and the
  figure's volume table; no advice, no diagnosis.

### EXPLORATORY: smaller model (Qwen3.5-9B, same prompt, same checker)
Pass 20/114 MU, 21/178 LUMIERE, 44/140 UCSF (85/432); S6 230/230; S7 follows 28/30. Its failures are mostly
fabrication: it writes the LUMIERE rater sentence for MU and UCSF scans, where the record has no rater flag (citing a
key that does not exist), writes "three months" as a word, and writes "95% CI" without citing the field. No
forbidden content. 0.22 s per report batched. Not usable with this prompt.

## Deviations
- **External cohorts were not represented in development** (the plan fixes development to MU patients). The
  LUMIERE-specific fact and prompt line were therefore first tested on the evaluation set, where they failed.
- **Changed after the freeze, not affecting any result:** `sections_v3.py` (renderer: the combined score has no
  cohort median; LUMIERE's necrosis-with-cavity row; timing row) and in `report_v3.py` a key error in the S7
  evaluation (`r["card_tier_stated"]`). Checker, facts and prompt are unchanged (hashes above).
- No FP8 needed: bf16 fits one H100 at `gpu_memory_utilization` 0.90, `max_model_len` 8192.
- `__main__.py` was not given a stage (other agents edit it); run as `python -m prism.analyses.report_v3`.
- Words: the reports are long (≈ 350 words, about 1.75 min to read), longer than v2 (190). Not a pre-specified item.

## Limits
- The checker is lexical: it cannot see a correct number attached to the wrong idea, or a faithful report that is
  hard to read. No clinician has read any v3 report.
- A fix for the LUMIERE error (rater field carrying its own words, digits instead of number words in the facts)
  must be tested on records not used here; the post-hoc 178/178 is not evidence of it.
