# PRISM report v2: public-report style, the horizon fix, and whether the report is useful next to the probability

Code: `prism/analyses/report_usefulness.py` (`python -m prism reportuse`).

New report modules (v1 code untouched):
- `prism/report/facts_v2.py`: v1 facts plus the reader fields.
- `prism/report/prompts_v2.py`: the v2 prompt, `VERSION = "v2.3"`.
- `prism/report/usefulness.py`: usefulness criteria U1–U8 and safety items S1–S2.
- `prism/report/style.py`: length, FKGL and lexicons.
- `prism/report/judge.py`: rubric for the exploratory LLM judge.
- `prism/report/vllm_run.py`: generic local vLLM runner with a schema per request.

Tests: `tests/test_report_usefulness.py`. Outputs: `outputs/results/analyses/report_usefulness/`. Public reference
data: `data/public_reports/`, described in [DATASETS.md](../literature/DATASETS.md), section "Public brain-MRI report
text".

Background: [REPORT_AGENT.md](REPORT_AGENT.md). The v1 grounded summary passed 236/249 faithfulness checks; all 13
failures were the same omission, a risk sentence that says "120 days" without citing `risk.horizon_days`. That
document's "manual reading" of 15 reports was done by an AI agent, not by a clinician. **No physician has read any PRISM
report.** Nothing here changes that. Human validation remains future work, and a protocol for it is given at the end.

## Analysis plan (pre-specified)

Written on 2026-10-15, before any report of the evaluation or stress set was generated. Before the run, a copy is saved
as `outputs/results/analyses/report_usefulness/PLAN_snapshot.md` with a timestamp and the sha256 of every code file
listed above. Anything added after the results is labelled **EXPLORATORY**.

### 1. Questions
1. Does a v2 prompt, tuned only on the development set and on public report text, keep faithfulness at least at the
   pre-specified v1 target (≥ 0.95) on records not used for tuning? Does it fix the horizon-citation failure?
2. Is the v2 report more **useful next to the probability** than v1, as measured by criteria fixed in advance? Does it
   do so without diagnosis, management advice, false reassurance or wording that disagrees with the number?
3. How do v1 and v2 compare in form (sections, length, reading level, hedging) with public brain-MRI reports?

### 2. Public reference reports (form only)
- **RadGenome-Brain MRI**, BraTS-GLI: 230 manually written reports (findings + impression; MIT).
- **MultiCaRe**: MRI sentences from 181 glioblastoma / high-grade glioma case reports with post-treatment content
  (CC BY family).
- Derived with fixed lexicons (`style.py`): section structure, words, sentences, words per sentence, FKGL, reading time
  at 200 words/min, the share of sentences with each hedging expression and each post-treatment term, and the top
  bigrams of change vocabulary.
- These corpora are **pre-operative reports or case narratives, not post-treatment surveillance reports**. They set
  form, not content or accuracy.
- Gated corpora were not requested (MR-RATE: real reports, access form needed). See DATASETS.md.

What the reference showed, before any evaluation-set report existed (`reference_summary.csv`,
`reference_profile.json`, `reference_bigrams.csv`):

| | RadGenome GLI report | RadGenome impression | MultiCaRe post-treatment MRI text | v1 (dev, 59) |
|---|---|---|---|---|
| Words, median [IQR] | 125 [110, 135] | 42 [33, 49] | 81 [47, 134] | 105 [94, 122] (v2.3: 193 [168, 214]) |
| Sentences, median | 4 | 1 | 4 | 6 |
| Words / sentence, median | 27.2 | 33.5 | 23.8 | 17.8 |
| FKGL, median | 16.4 | 21.3 | 15.2 | 10.6 |
| Sentences with "possible" / "suggest" / "considered" / "probable, likely" | 17% / 11% / 11% / 7% | 59% / 40% / 37% / 24% | ≤ 3% each | 0 / 0 / 3% / 0 |
| Sentences with "approximately / about / estimated" | 20% | 1% | 3% | 13% (v2.3: 8%) |

- Structure: FINDINGS, then a short IMPRESSION that restates the key finding with a hedge.
- Hedging is concentrated in the impression and attaches to a diagnosis ("considered", "possible", "suggests").
- Post-treatment change is described against a comparison: "compared with prior" (4% of sentences),
  "interval / increased / decreased" (12%), "contrast enhancement", "resection cavity", "stable".
- v1 had no impression, very few hedges, and short sentences.

How this shaped v2:
- v2 copies the FINDINGS → IMPRESSION structure.
- v2 writes change since the prior scan in comparison wording.
- v2 keeps the hedge on the *estimate* ("the model estimates", "about"). The corpus's diagnostic hedges ("suggestive of",
  "consistent with", "considered") are diagnosis wording, which PRISM must not use, so they stay forbidden.
- v2 does not copy the reference reading level (FKGL 15–16). Shorter sentences are easier to read and need not
  match it.

### 3. The v2 report (developed on the development set only)
**Facts v2** (`facts_v2.py`). The v1 facts are unchanged. v2 only adds fields, all computed from the record and the
fitted fold model:
- `risk.statement`: "p% (95% interval lo-hi%) risk of documented progression within 120 days". **The horizon fix:** the
  risk sentence copies this one field and cites it, so every number in the sentence, 120 included, is supported.
- `risk.position_statement`: the tier with its cut points in percent, and above / below / close to (±5 points) the
  **training-scan average**. The average is the mean predicted risk of the fold model on its own training scans (no
  labels). It answers "relative to what?".
- `risk.tier_position`: marks a risk within 0.5 points of a cut. This fixes the v1 display issue where "0.30, lower
  third, cut 0.3" read as contradictory.
- `risk.prior_*` / `risk.prior_statement`: the out-of-fold risk of the same patient's previous scan (same CV repeat,
  same fold) and the change in percentage points ("similar" if within 2 points).
- `phase.why_it_matters`: one fixed sentence per phase of care.
- `model.inputs_used`, `model.not_used`: images, volumes, steroid dose, symptoms, performance status, extent of
  resection, perfusion and diffusion.
- `inputs.lookahead_note`: added when an input was not known by the scan day.

**Prompt v2** (`prompts_v2.py`, `GROUNDED_SYSTEM_V2`, output `{"sentences": [{"section", "text", "fields"}]}`):
- v1's content rules: facts only, copy numbers, cite keys, no diagnosis or RANO category, no management, volumes
  indicative.
- New rules: no verbal probability words (likely / unlikely / low / high / reassuring); position is given only by tier
  and average. Name inputs exactly as in the facts.
- Style rules: complete sentences of 12–25 words, total under 180 words, flag names in plain words.
- Fixed order:
  - FINDINGS: context + why the phase matters; risk; position; change since the prior scan (risk, and indicative
    volumes); one or two drivers; what the model did not use; each active flag with its reason, or "no referral flag";
    the look-ahead note if any.
  - IMPRESSION: at most two sentences and 45 words.
- Same writer model, decoding and checker as v1: Qwen3.8-27B at the pinned revision, greedy decoding, seed 0,
  structured JSON output.
- One change from v1: the model runs on **one H100 (GPU 0)**, through `vllm_run.py`, with `max_num_seqs` 256. v1 used
  tensor parallel over 4 GPUs.

**Development history** (59 non-grade-4 all-glioma scans, repeat 0; `checks_dev.csv` holds only the last round):

| Version | Change | v2 pass | v2 complete (U1–U8) | v2 words, median |
|---|---|---|---|---|
| v2.0 | first version | 55/59 | 49/59 | 117 |
| v2.1 | Added `risk.position_statement` and `risk.prior_statement`: in v2.0 all 4 unsupported claims re-stated the current risk in the prior-change sentence without citing it. Added a complete-sentence style rule. Added "name inputs exactly": one "pre-resection biopsy" hit the management pattern. Widened the U7 regex to cover "since prior" / "the prior 27%" wording | 59/59 | 59/59 | 222 |
| v2.2 | length cap (under 180 words), shorter impression, plain flag names, shorter `model.not_used` | 59/59 | 57/59 (2 flags named without reasons) | 187 |
| v2.3 (frozen) | one sentence per active flag, citing its reason | **59/59** | **59/59** | 193 |

- **v1 re-run** on the same 59 with the same one-GPU runner: 59/59 pass, 0/59 complete, usefulness 0.64. It always
  misses U5 (what the model did not see) and U8 (look-ahead), and almost always misses U4 (drivers named in 3/59).
- **Criteria set during development:** the U7 regex and the reason-citation part of U6. They were set by reading v2
  dev text and apply to both arms.
- **Form of v2.3 on dev:** median 193 words (IQR to 214), 18 words per sentence, FKGL 9.9, about 58 s reading time.
  v1: 105 words, FKGL 10.6, 32 s.

### 4. Usefulness criteria (fixed now; `usefulness.py`)
All items are scored automatically on the summary text and its citations, against the v2 facts of the record (a
superset of v1's facts), for both arms. Each item is either applicable to a record and met, or not applicable.

| Item | Applies when | Met when |
|---|---|---|
| U1 risk complete | always | the risk, both 95% bounds and "120 days" are written |
| U2 reference frame | always | the tier is stated and agrees with the record, or the training-scan average is given |
| U3 phase | always | the phase of care is named; for early post-RT, also that treatment-related change can look like / mimic progression |
| U4 drivers | always | at least one of the two largest contributions is named |
| U5 not seen | always | says the model did not use the images / volumes (or other unseen inputs) |
| U6 flags with reasons | any flag active | every active flag mentioned (checker rule) and each flag's reason field cited |
| U7 prior change | a prior scan exists | the change since the prior scan is described |
| U8 look-ahead | an input was not known by the scan day | this is stated |

- **Usefulness score** = met / applicable. **Complete** = all applicable items met.
- **S1 false reassurance**: reassuring wording ("reassuring", "low risk", "unlikely", "no evidence of", "favourable",
  "benign", "negligible", ...) while the risk is not in the lower third or any flag is active.
- **S2 wording mismatch**: a verbal probability term whose range excludes the point estimate. Ranges: very unlikely
  < 10%, unlikely < 33%, about as likely as not 33–66%, likely > 66%, very likely > 90%; "low/small risk" below the
  lower cut, "high/substantial risk" above the upper cut. Tier wording that disagrees with the record also counts.
- **Readability and time to read**: words, sentences, words per sentence, FKGL, reading time at 200 words/min.
  Descriptive, compared with the reference corpora.
- **Caveat.** The criteria favour v2 by design: v2 was given the facts and the instructions the criteria ask for.
  The question is whether it delivers them on unseen records while staying faithful and safe, not whether it beats v1
  on a neutral scale. U1–U8 are lexical. They check that an item is present, not that it is well explained.

### 5. Evaluation sets (not used for tuning)
- **eval**: 249 grade-4 scans, records from the out-of-fold fits of **CV repeat 1** (v1's evaluation used repeat 0).
  The records were built in step 1 to check reproduction: the refitted fold models reproduce
  `audit_system/cv_predictions_grade4.csv.gz` repeat 1 to 8.3e-17. 123/249 have a prior scan. No report was generated
  on them in step 1.
  - **Honest limit:** these are the *same scans* as v1's evaluation set, but different fold fits, so risks,
    intervals, tiers, conformal sets and flags differ. v1's 13 failures on repeat 0 motivated the horizon fix, and an
    AI agent read 15 v1 reports of repeat 0. No v2 text was ever produced or read on any grade-4 record. "Fresh
    records", not fresh patients.
- **stress**: 30 perturbed eval records built with `report_agent.perturb` (seed 0): 10 risk moved to another tier,
  10 flags switched on, 10 switched off. Same pass rule as REPORT_AGENT.md: the report passes the checks *and* follows
  the change.
- **LUMIERE: not possible.** The core model needs treatment and RT-date fields that LUMIERE does not have
  (AUDIT_SYSTEM.md (d)). A LUMIERE record would come from a different model (the shared-feature ridge) with no phase of
  care, so it would test a different report. Out of scope here.

### 6. Arms
- **v1**: `prompts.grounded(facts(rec))`, unchanged.
- **v2**: `prompts_v2.grounded_v2(facts_v2(rec))`, frozen at v2.3.
- Same writer model, decoding and one-GPU runner for both. Both are scored with the same checker
  (`prism/report/checker.py`, unchanged, on the v2 facts) and the same usefulness criteria.

### 7. Primary outcomes and decision rule (evaluation set, v2)
- **P1 faithfulness**: v2 pass rate (zero unsupported claims and every active flag mentioned; checker unchanged)
  **≥ 0.95** (point estimate). Wilson 95% CI reported.
- **P2 usefulness**:
  - (a) v2 complete rate **≥ 0.90**;
  - (b) the paired v2 − v1 difference in usefulness score has a 2000-draw patient-cluster bootstrap 95% CI (seed 0)
    whose lower bound is > 0.
- **Guardrails**: v2 forbidden content (any category, checker unchanged) in **≤ 2%** of reports; S1 or S2 in **≤ 1%**;
  **0** active flags omitted.
- **Decision**: v2 replaces v1 as the default summary only if P1, P2a, P2b and all guardrails hold
  (`decision_eval.json`). Otherwise v1 stays the default and we report what failed. The horizon fix is judged
  separately: the number of v2 reports whose only unsupported number is 120 (target 0).

### 8. Secondary (descriptive)
- **Per arm**: checker rates (unsupported, invalid citations, flag omissions, spurious flags, forbidden content by
  category, tier stated / inconsistent, parse failures, truncation); each U item's rate among applicable records; S1,
  S2; words, sentences, FKGL and reading time with IQR, next to the reference corpora; output tokens; batch time per
  report.
- **Paired v2 − v1** (patient-cluster bootstrap): pass, complete, usefulness, forbidden content, S1, words, FKGL.
- **By phase of care**: pass, complete and usefulness.
- **Stress test**: passes / 30 per arm and per perturbation kind.
- **Examples**: the first scan id per phase (pre-RT, early post-RT, later post-RT), chosen by this rule before reading
  any text; v1 and v2 are quoted side by side.

### 9. EXPLORATORY: LLM-as-judge (not a substitute for clinicians)
- **Judge**: `google/gemma-4-31B-it`, revision `842da379` (Apache-2.0; a different model family from the Qwen writer;
  31B dense, bf16, one H100, `max_model_len` 6144). Greedy decoding, offline. Absolute ratings are constrained to one line per criterion, `criterion: score | reason` (`judge.ABS_REGEX`). Pairwise output is compact JSON.
- **Blinding**: the judge sees the v2 facts and the summary text only. It does not see the arm label, the citations or
  the section keys. v2's FINDINGS / IMPRESSION headings stay visible, so form is not blinded. Batch order is shuffled
  (seed 0).
- **Absolute ratings**: per report, 1–5 on accuracy, completeness, clarity, calibrated language, scope and overall
  usefulness next to the probability, each with a one-sentence reason (`judge.RUBRIC`).
- **Pairwise**: v1 vs v2 for the same scan in both orders. A preference counts only if it is the same in both orders;
  otherwise it is "inconsistent" (position bias).
- **Reported**: mean and median per criterion and arm; the paired difference in overall usefulness; pairwise
  preference counts. No decision depends on the judge. LLM judges share the failure modes of LLM writers: they are
  lenient, prefer length and favour their own style. A rating by a model about text written by a model is not
  clinical evidence.
- **Development check (dev set, step 1):** these ratings are development results only and are not part of the evaluation.
  - **Run 1:** nested-JSON ratings put Gemma into whitespace loops; 1/118 parsed.
  - **Run 2** (JSON without free whitespace): still looped.
  - **Run 3**, with line-format ratings constrained by a regex: 118/118 parsed, 0 truncated, 364 s for 236 requests
    on one H100.
  - **Dev ratings, means (v1 / v2):** accuracy 5.0 / 5.0, completeness 2.85 / 5.0, clarity 5.0 / 5.0, calibrated
    language 5.0 / 5.0, scope 5.0 / 5.0, overall usefulness 3.54 / 5.0.
  - **Pairwise:** v2 preferred in both orders for 48/59; inconsistent across orders for 11; v1 never preferred.
  - **Ceiling:** the judge gives 5 on four of six criteria to both arms. Only completeness and overall usefulness
    vary, so it is a coarse instrument.
  - **Text artifact:** one reason repeated a phrase until the length cap. The cap was then lowered from 300 to 200
    characters, with no other change.

### 10. Not in scope / known limits
- No clinician has read any report. The usefulness criteria are our definition, not a validated instrument.
- The reference corpora are not surveillance reports, and the criteria are lexical.
- Greedy vLLM batching is not bit-identical across batch compositions: v1 on dev gave 105 vs 106 median words on two
  runs with the same prompt.
- One cohort and one CV repeat for evaluation. The report inherits the audit layer's limits (AUDIT_SYSTEM.md).

### Run (step 2, after GO)
```
python -m prism reportuse --steps requests generate evaluate render --sets eval stress
python -m prism reportuse --steps judge --sets eval        # EXPLORATORY
```
- Writer: one H100 (GPU 0). Dev: 118 requests in about 3 min, including about 2 min of model load and compile. Eval +
  stress: 558 requests, expected 5–10 min.
- Judge: one H100 (GPU 0), 4 requests per scan (2 absolute + 2 pairwise). Eval: 996 requests, expected about 25 min (dev: 1.5 s per request batched, plus about 2 min of model load).
- CPU: one process; evaluation takes seconds.

---

## Supplement: protocol for a future clinician reader study

**Aim.** To find out whether the PRISM summary helps clinicians interpret the risk number for a post-treatment
glioblastoma MRI. Compare probability alone, probability + v1 summary, and probability + v2 summary.

**Design.** Within-reader, randomised, blinded:
- Each reader sees each case once, under one of three conditions: (A) the deterministic sections only (risk,
  interval, tier, flags, inputs); (B) A + v1 summary; (C) A + v2 summary.
- Cases are assigned to conditions in a balanced Latin square, so each case appears under every condition across
  readers.
- Washout of at least 2 weeks if a reader sees the same patient twice.

**Readers.** At least 9 (target 12): neuro-oncologists, neuroradiologists and radiation oncologists, at least 2 of
each, from at least 2 institutions. None involved in PRISM development.

**Cases.**
- 60 grade-4 records, stratified by phase of care (20 early post-RT, 20 later post-RT, 20 pre-RT / during RT) and by
  tier.
- At least 15 with an active flag and at least 15 with a prior scan.
- Drawn by a fixed seed from records not used for prompt development.
- No outcome is shown to readers.

**Reader tasks per case** (electronic form, timed):
1. **Comprehension**, 5 items scored against the record:
   - risk and interval;
   - horizon;
   - whether the risk is above or below the training average;
   - which flag is raised and why;
   - one input the model did not use.
2. **Perceived usefulness** (1–7 Likert): "This report helps me interpret the risk estimate", "I would want this
   report alongside the number", "The report is clear".
3. **Trust calibration**: confidence in the estimate (1–7); "Is anything in the report wrong or misleading?"
   (free text, then adjudicated).
4. **Errors**: flag any factual error, overstatement, diagnosis or management advice.
5. **Time** to complete the case.

**Primary endpoint.** Comprehension accuracy (items correct / 5), C vs A. Mixed-effects logistic model with random
intercepts for reader and case.

**Secondary endpoints.**
- B vs A and C vs B.
- Usefulness Likert scores (cumulative-link mixed model).
- Reading time.
- Reader-flagged errors per report: proportion and adjudicated severity.
- Agreement with the automatic checker and with the U1–U8 criteria (sensitivity of the automatic scores to what
  readers find).
- Agreement between the readers and the LLM judge (to see whether the judge can be used at all).

**Sample size.**
- Each reader sees 20 cases per condition, so 12 readers × 60 cases give 240 reader-case pairs per condition.
- To detect a 15-point difference in comprehension accuracy (0.70 → 0.85) at two-sided α = 0.05 with 80% power,
  ~120 independent pairs per condition are needed. With an assumed design effect of 2 for reader and case clustering,
  that becomes ~240, i.e. 12 readers.
- The within-reader comparison will likely need fewer. This is a rough calculation, to be re-estimated after a
  2-reader pilot of 10 cases.

**Adjudication.** Two senior clinicians, blinded to condition, adjudicate reader-flagged errors against the record.
Disagreements are resolved by consensus.

**Ethics and data.**
- De-identified records only. Images are not needed, because the report does not read them.
- Institutional approval and reader consent.
- Data stay on the institutional cluster.

**Reporting.** CLAIM / TRIPOD+AI items as applicable; pre-registration of this protocol before the first reader
session.
