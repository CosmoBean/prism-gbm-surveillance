# PRISM report-field ablation, facts-only v2: full-evidence v3.1 reports against a constrained facts-only arm

Protocol: [REPORT_FIELD_ABLATION_V2_PLAN.md](REPORT_FIELD_ABLATION_V2_PLAN.md). It was approved by the author on
2026-10-27, before any v2 code, and frozen as its "Freeze" section records. The first attempt is
[REPORT_FIELD_ABLATION.md](REPORT_FIELD_ABLATION.md).

**Result: the facts-only v2 arm passed its frozen checker in 406/406 reports, as did the full-evidence arm, so the
pre-specified interpretability gate was met.**
- **Model-derived fields.** Every full report cited model-derived fields in sentences that the frozen v3.1 checker
  found supported, with a median of 16 distinct fields per report.
- **Shared facts.** On these lexical checks, the model-derived fields were added without losing any clinical fact
  the facts-only arm stated: no volume or change statement was dropped. The facts-only arm cited 2.8 more shared keys
  per report; an exploratory count shows these were only the cohort, availability and previous-scan sentences.
- **Stress test.** The facts-only arm followed the shared-fact edit in 6/6. The full arm followed it in 0/6 under the
  pre-specified rule, which needs the new change statement verbatim. An exploratory count shows the full arm wrote
  the new magnitude and direction in 6/6, in its own wording.
- **Clinical-inference pattern.** It matched 278/406 full reports and no facts-only report. An exploratory count
  traces all 278 matches to the model-derived scan-situation text that the full arm is supplied with.

All results are automatic lexical checks. They show what the model-derived fields add to the report and that the
checker finds it faithfully represented. **They do not show that clinicians understand those fields or benefit from
them.** No reader, decision, workload or outcome endpoint was measured.

v2 is the second pre-registered attempt. The first (v1) passed 0/406, which a post-hoc diagnosis attributed to
mismatches between the prompt and the checker. v1 stays reported as it stands. The v2 design was informed by v1's
aggregate failure counts on the same 406 records, so v2 is a second evaluation after a failure that was seen.

## Design (fixed before generation)

- **Population and pairing.**
  - The 406 locked v3.1 evaluation records: MU 114 (60 patients), LUMIERE 162 (69), UCSF 130 (130).
  - They are paired by record. The per-line hashes come from the v1 manifest (`bca995bb…`).
- **Full arm.**
  - The immutable v3.1 reports, imported byte for byte and checked by the frozen v3.1 checker.
  - Per-claim support was recomputed with the same checker, because `check_details_eval.json` is empty. This
    reproduced 406/406.
- **Facts-only v2 arm.**
  - The v1 field contract: the keys that begin `pathway.`, `pathways.`, `conformal.`, `card.` or `flags.` are removed.
  - One specification (`prism/report/facts_only_v2.py`) gives every facts-only key its accepted sentence forms. The
    prompt shows each form, and the checker accepts a sentence only if it equals a form for the keys it cites.
  - Defence-in-depth checks cover unsupported numbers, invalid citations, forbidden wording, a clinical-inference
    pattern and the banned model-derived terms. The banned terms are v1's list minus "above", "below", "higher" and
    "lower".
- **Writer and serving.** Qwen3.8-27B at revision `1d4bf0f2…`, vLLM 0.31.0, offline, one H100 (Slurm allocation
  162548), bf16, greedy, seed 0. Each generation was one whole batch.
- **Development.** On the 58 v3.1 development records (MU 32, LUMIERE 16, UCSF 10; disjoint by patient). At most three
  iterations were allowed, with a fixed freeze criterion. Only aggregate counts were used.
- **Freeze.** `FROZEN_v2.json` pins the following, and every evaluation step rechecks it:
  - the specification and runner blobs;
  - five imported modules;
  - the serving settings and the writer;
  - the field prefixes;
  - the evaluation, development and stress-set hashes;
  - the qualifying iteration and the commit (`ef9d90b`).

## Development, freeze and preflight

| step | result |
|---|---|
| consistency check, no model (58 development records) | 0 records with errors |
| synthetic preflight, run 1 (before development) | completed and parsed |
| development iteration 0 (`v2-iter0`, tag `ablation-v2-dev-iter0`) | **58/58** pass: MU 32/32, LUMIERE 16/16, UCSF 10/10; every `fail_` count 0; one attempt, 24 s batch |
| freeze (tag `ablation-v2-freeze`, commit `e03ec0c`) | iteration 0 qualified, so it was frozen at once. No specification change was made, and iterations 1 and 2 were not used. The runner and specification blobs equal those of iteration 0. |
| synthetic preflight, run 2 (after the freeze; bound to the frozen code) | completed and parsed |

Evaluation generation started at 2026-10-27T17:43:51-04:00. Each of the three batches (evaluation and the two stress
arms) completed in one attempt.

## Results: evaluation set (406 records, paired by record)

**Primary outcomes.**

| cohort | n | full: pass (Wilson 95% CI) | facts-only v2: pass (Wilson 95% CI) | difference (cluster 95% CI) |
|---|---|---|---|---|
| MU | 114 | 114/114 (0.97–1.00) | 114/114 (0.97–1.00) | 0.00 (0.00–0.00) |
| LUMIERE | 162 | 162/162 (0.98–1.00) | 162/162 (0.98–1.00) | 0.00 (0.00–0.00) |
| UCSF | 130 | 130/130 (0.97–1.00) | 130/130 (0.97–1.00) | 0.00 (0.00–0.00) |
| all | 406 | 406/406 (0.99–1.00) | 406/406 (0.99–1.00) | 0.00 (0.00–0.00) |

- **Gate: met.** It required at least 386/406 overall and at least 0.90 in each cohort.
- **Facts-only failures.** Every facts-only `fail_` count is 0, across all ten criteria.
- **Parsing and truncation.** Neither arm truncated or failed to parse.
- **Reference check.** The deterministic reference report, checked with no model, passed 406/406.

**Secondary 1: information added** (406 records where both arms pass).

| measure | result |
|---|---|
| full reports citing ≥ 1 model-derived key in a supported claim with valid citations | 406/406 |
| distinct model-derived keys per full report | median 16 (IQR 14–18); MU 16, LUMIERE 16, UCSF 17 |
| reports citing each prefix (keys cited in total) | `pathway.` 406 (2436), `pathways.` 406 (812), `conformal.` 406 (406), `card.` 406 (1242), `flags.` 406 (1661) |
| shared keys cited per report, full vs facts-only | 8.08 vs 10.93; difference −2.85 (cluster 95% CI −2.90 to −2.78) |
| reports where the full arm cites a shared key that facts-only does not | 0 |
| reports where facts-only cites a shared key that the full arm does not | 406 |

*Exploratory (not pre-registered):* the shared keys that facts-only cites and the full arm does not are only:
- `system.cohort` (406 reports), which is optional in facts-only;
- `meas.available` (391);
- `scan.previous_available` (359).

No volume, change statement, phase or rater statement is among them.

**Secondary 2: common grounding criteria** (the same tests on both arms; only verbatim copies of shared statements are
exempt).

| criterion | full | facts-only v2 | difference (cluster 95% CI) |
|---|---|---|---|
| unsupported numbers | 0/406 | 0/406 | 0.00 |
| invalid citations | 0/406 | 0/406 | 0.00 |
| forbidden wording | 0/406 | 0/406 | 0.00 |
| clinical-inference pattern | 278/406 | 0/406 | 0.68 (0.62–0.75) |

*Exploratory (not pre-registered):* all 278 full-arm matches have these features:
- each is the pattern "tumour … increased/increase" (237 and 41);
- each sits in a sentence citing a model-derived key;
- in each record, the pattern also matches the supplied `card.situation` fact value. That is the description of the
  scan situation that the reliability card was measured on.

On this reading, the matches come from situation text the full arm is given and copies, not from an inference the
writer added. The pattern is lexical, and no report text was read.

## Results: paired shared-fact stress test

This is v1's frozen 6-record `enhancing_volume_change` set (`82dfe422…`; LUMIERE 3, UCSF 3), read only. Both arms
were generated on the same perturbed records.

| arm | follows | not follows | unscorable | failed | checker pass | follows and pass | ambiguous by construction |
|---|---|---|---|---|---|---|---|
| full (v3.1 prompt) | 0/6 | 6 | 0 | 0 | 6/6 | 0/6 | 2/6 |
| facts-only v2 | 6/6 | 0 | 0 | 0 | 6/6 | 6/6 | 0/6 |
| facts-only v2, v1 strict rule | 6/6 | 0 | 0 | 0 | 6/6 | 6/6 | – |

**The pre-specified rule.** A sentence citing the change statement must contain the new statement verbatim. The old
statement must be absent. No old changed value may be written unless it is also a perturbed fact.

*Exploratory (not pre-registered):* in all 6 full reports, a sentence cites the change statement and states the new
magnitude and direction. None of them reproduces the statement verbatim, so the miss is wording, not content.

**Ambiguity.**
- The ambiguity set for each arm is its own perturbed facts. For the full arm these include model-derived numbers.
  That makes 2/6 records ambiguous by construction for the full arm and 0/6 for facts-only.
- No record was unscorable.

**Comparison with v3.1.** The v3.1 S7 result for the full arm (28/30; ET change 4/6 under the v3 rule) is unchanged and
is not comparable.

## Length, tokens and runtime

| arm | median words (MU / LUMIERE / UCSF) | prompt tokens | output tokens | generation |
|---|---|---|---|---|
| full (v3.1, imported) | 303 (317 / 305 / 290) | 1,143,264 | 475,853 | 437 s batch (1.08 s / report) |
| facts-only v2 | 86 (86 / 92 / 86) | 300,024 | 244,976 | 142 s batch (0.35 s / report); 249 s process including load; 1 attempt |

- **Stress batches:** full 30 s batch (134 s process); facts-only 16 s (115 s).
- **Development batch:** 24 s (130 s).
- **Cost:** no GPU price was supplied, so no dollar cost is given.
- **Word counts:** they count failed or missing outputs as 0 words, but there were none.

## Deviations and implementation clarifications

None of these changed a frozen value or a result. All were fixed before the freeze unless stated otherwise.
- **Number and citation checks.** These run per claim on the full sentence text. The protocol lists them among the
  checks applied "except verbatim copies of supplied statements". Running them on the full text is stricter, and it
  cannot change a pass, because a copied statement must also equal its form.
- **Pooled forms.** The checker pools the accepted forms across all the keys a sentence cites, so an over-cited or
  repeated sentence can pass. The protocol's wording ("for the keys it cites") allows this. It affects no shared fact.
- **Extra preflights.** The preflight also ran before development (run 1), and `dev_step` required it. A failed
  development batch would have been set aside without using up an iteration. Neither happened.
- **No render step.** The runner has no `render` step, and no v2 Markdown reports were produced. The protocol does not
  require them, and the implementation plan was amended before the freeze.
- **Stress definitions.** The ambiguity set and the full arm's checker pass in the stress test are defined per arm, as
  set out in the stress section above. The full arm's stress `check_pass` also requires no truncation, which the
  imported evaluation pass does not; no output was truncated.
- **Development data.** The development set was locked on first use (`dev_lock.json`). Its SHA-256 (`792e8b9e…`) and
  per-line hashes are in the freeze section of the protocol.

## Limits

- **No clinician, decision, workload or outcome endpoint was measured.** The checks are lexical. "Faithfully
  represented" means only that the frozen automatic checks pass.
- **The facts-only v2 arm is a constrained-template arm.** It tests whether the writer states the shared facts
  faithfully, not narrative quality. Its 406/406 shows that the writer can fill the fixed forms. It is not a contrast in
  writing between free-text reports.
- **v2 is a second evaluation after a seen failure** on the same 406 records, and its design used v1's aggregate
  failure counts.
- **The stress test has 6 records** and excludes records with zero or near-zero enhancing change. Its pre-specified
  rule asks for verbatim statements, which the full arm's prompt does not require.
- **The exploratory readings** (the stress wording, the `card.situation` source and the shared-key composition) came
  after the results. They are reproduced by `scripts/exploratory_field_ablation_v2_diagnosis.py`, which prints counts
  only.

## Manuscript options (not applied; the author decides)

The gate was met, so the protocol allows a one-sentence supplement result that claims no clinical benefit. A
possible wording:

> In a pre-registered paired ablation on the 406 evaluation scans, reports written from the shared measurement facts
> alone and the full reports both passed their automatic grounding checks (406/406 each). Every full report added
> model-derived content that the checker found supported (median 16 fields), and it dropped no measurement fact. This
> is an automatic check only; whether readers understand or use these fields was not studied.

Not recommended for the paper:
- the 0/6 full-arm stress follow rate. It reflects a verbatim-wording rule, and on the exploratory reading the content
  was followed;
- the 278/406 clinical-inference matches. They trace to the supplied situation text.

Neither supports a claim in either direction without the exploratory readings.
