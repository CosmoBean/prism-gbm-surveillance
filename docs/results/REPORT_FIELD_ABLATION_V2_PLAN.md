# Paired report-field ablation, facts-only v2: pre-specified protocol

Written 2026-10-27, before any v2 code, prompt, request or generation. Status: **draft; awaiting the author's
approval.** No development iteration runs until the author approves this protocol. Implementation plan:
[2026-10-27-report-field-ablation-v2.md](../superpowers/plans/2026-10-27-report-field-ablation-v2.md).

This is the second pre-registered attempt at the facts-only arm. The first attempt
([REPORT_FIELD_ABLATION.md](REPORT_FIELD_ABLATION.md)) passed 0/406. It stays reported as the first attempt, and
nothing in it is revised or re-run.

**Disclosure.** This design was informed by the v1 post-hoc diagnosis, which used aggregate failure counts from the
406 evaluation records. No report text and no record IDs were used. So v2 is a second evaluation after a failure that
was seen, as v3.1 was after v3, and it is reported that way.

## Question and interpretation

v2 asks one question: on the same 406 locked records, when both arms meet their own grounding contract, what do the
model-derived fields add that is faithfully represented?

These limits are fixed now, before any result:
- If both arms pass their grounding checks (the interpretability gate below), v2 shows whether the model-derived
  fields add more information to the report, and whether the automatic checker finds that information faithfully
  represented.
- v2 does not show that clinicians understand those fields or benefit from them. Nobody reads a report, and no
  decision, workload or outcome endpoint is measured.
- "Faithfully represented" means only that the information passes the frozen automatic lexical checks.
- The v2 facts-only arm is a constrained-template arm. It tests whether the writer can state the shared facts
  faithfully. It does not test narrative quality.
- If the gate is not met, v2 is reported as a second failed attempt, and no information contrast is claimed.

## What stays the same as v1

- **Population and pairing.** The 406 locked v3.1 evaluation records: MU 114, LUMIERE 162, UCSF 130 (259
  patients). The source is `records/eval.jsonl` (SHA-256 `d5057aec…`). The per-line hashes and order come from the
  v1 manifest (manifest SHA-256 `bca995bb…`). Records are paired by record across the two arms.
- **Field contract.** `facts_only` removes exactly the keys that begin `pathway.`, `pathways.`, `conformal.`, `card.`
  or `flags.`, using `prism.report.field_ablation.facts_for_arm`, which is unchanged.
- **Full arm.** The immutable v3.1 reports. Its requests, outputs and metadata are imported byte for byte, and the
  frozen v3.1 checker (`26d6637a…`) applies. Nothing on the evaluation set is regenerated.
- **Writer and serving.** Qwen3.8-27B at revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`; vLLM 0.31.0, offline,
  one H100, bf16, greedy, seed 0, `max_model_len` 8192. Generation is one whole batch, with at most one identical
  whole-batch retry and no per-record retry. Every attempt is kept.
- **Provenance.** The v1 provenance gate (v3.1 artifacts, checker, every frozen `prism/report/*` blob, writer
  revision, baseline counts) runs before every v2 step. The v1 lock (`report_field_ablation/provenance.json`) and
  v1's outputs are read only.
- **Local only.** Records, facts, prompts and reports stay on the cluster. No hosted model receives them, Claude
  included. Documents hold aggregate numbers only.

## What changes in v2

### 1. One shared specification renders both the prompt and the checker

A new module, `prism/report/facts_only_v2.py`, holds a single specification. The v1 module stays frozen.
- **Sentence forms.** Each facts-only key has a finite list of accepted sentence forms, rendered from the key's
  value. The prompt shows the model the exact first form for every key present in that record. The checker accepts
  a sentence only if, after case-folding and whitespace normalisation, it equals an accepted form for the keys it
  cites.
- **Vocabulary rule.** Because each sentence must equal a rendered form, the v1 open-vocabulary rule is replaced.
  The words a sentence may use are exactly the words of its forms.
- **Iteration-0 forms**, which development may change:

| key | iteration-0 form(s) |
|---|---|
| `scan.phase` | "Scan timing: {value}." |
| `scan.previous_available` | yes: "A previous scan is available." / no: "No previous scan is available." |
| `scan.rater_statement` | the supplied statement, verbatim |
| `system.cohort` (optional, provenance) | "Source cohort: {MU-Glioma-Post / LUMIERE / UCSF-ALPTDG}." |
| `meas.available` | yes: "Segmentation volumes are available." / no: "No usable segmentation volumes are available." |
| `meas.label` | "Volumes are from the automatic segmentation and are indicative." |
| each volume key | "{Enhancing tumour / FLAIR hyperintensity / Necrosis / Resection cavity / Necrosis and cavity} volume is {value:.1f} cc." (optional leading "The") |
| each change statement | the supplied statement, verbatim, with an initial capital and a full stop |

- **Required keys and sections.** These are as in v1: the scan, measurements, longitudinal and provenance sections in
  order, and the required keys `scan.phase`, `scan.previous_available`, `meas.available`, plus `scan.rater_statement`
  when present. When volumes are available, `meas.label`, each volume and each change statement are also required.
- **Defence-in-depth checks**, applied to the whole text except verbatim copies of supplied statements:
  - unsupported numbers and invalid citations (the frozen `checker.check_claim`);
  - forbidden wording (`checker.forbidden_v3`);
  - the clinical-inference pattern;
  - the banned model-derived terms.
- **Banned-term list.** This is v1's list minus "above", "below", "higher" and "lower". Those words appear inside
  supplied statements (59 v1 hits, all "below"). Model-derived concepts (scores, models, prediction, pathways,
  conformal, tiers, flags, risk, probability, likelihood, uncertainty, confidence, outcomes, progression,
  recurrence, pseudoprogression, radiation necrosis, treatment effect, agreement, performance, accuracy,
  reliability) stay banned.
- **Consistency tests**, which must pass before every development run and at the freeze:
  - Every form the prompt shows for a record passes the checker for that record.
  - A deterministic reference report (the first form for every required key, in section order) passes the checker.
  - They are tested on synthetic records covering:
    - each `scan.phase` value;
    - a previous scan present and absent;
    - volumes available and unavailable;
    - the rater statement present and absent;
    - each volume key;
    - each change statement, including the "unchanged … (change below 0.1 cc)" form;
    - a cohort present and absent.
  - They are also run on the 58 development records' facts. This needs no model.

### 2. Development on the development partition only

- **Development set.** `records/dev.jsonl`, the v3.1 development partition (`dev_patients_v3_1.json`). It has 58
  records: MU 32 (20 patients), LUMIERE 16 (10), UCSF 10 (10). It is disjoint from the 406 by patient, and the
  pipeline asserts this.
- **Iterations.** At most three: iterations 0, 1 and 2.
  - Each iteration is one whole-batch facts-only generation on the 58 records, with the same writer and serving as the
    evaluation.
  - Each iteration's specification is a tagged commit (`ablation-v2-dev-iter<k>`).
  - Each iteration writes `summary_dev_iter<k>.csv`: pass and per-criterion failure counts, by cohort and overall.
- **What may change between iterations.** Only the specification module:
  - the sentence forms and their number per key;
  - the prompt wording rendered from it;
  - adding banned terms.

  These may not change:
  - the checker criteria and the field contract;
  - the required keys;
  - the clinical-inference pattern;
  - the forbidden-wording rules;
  - the writer, decoding and serving.

  Every change is listed in the result document.
- **What informs a change.** Only aggregate per-criterion counts and counts of non-form words; no sentence text and no
  record IDs. This keeps development text off any hosted model. The author may read development reports on the
  cluster, and any such reading is recorded.
- **Freeze criterion.** An iteration qualifies when all of these hold:
  - facts-only dev pass ≥ 55/58;
  - each cohort passes at least MU 29/32, LUMIERE 15/16 and UCSF 9/10;
  - the consistency tests pass.

  The first qualifying iteration is frozen at once, with no further tuning.
- **Stop rule.** If iteration 2 does not qualify, v2 stops. No evaluation request is built. The result document
  reports the three development pass rates as a v2 development failure.

### 3. Freeze

At the freeze, `report_field_ablation_v2/FROZEN_v2.json` records the following. The same values are appended to this
document in a tagged commit (`ablation-v2-freeze`) before the evaluation requests are built.
- the Git blob and SHA-256 of `facts_only_v2.py` and of the v2 runner;
- the writer ID and revision;
- the field prefixes;
- the v1 manifest SHA-256 and the per-line hashes of `eval.jsonl` and `dev.jsonl`;
- the frozen stress-set hash;
- the qualifying iteration.

The evaluation and stress request hashes are frozen by the `requests` step.

### 4. Preflight before the evaluation batch

The preflight runs the writer on one synthetic record, never a patient record, through the same runner, environment
and engine flags. It checks that the engine starts and that the output parses. A preflight failure is fixed before the
evaluation. It does not use up a whole-batch attempt, and it is logged.

### 5. One evaluation on the locked 406 records

After the freeze and preflight, the facts-only arm is generated once on the 406 records. The full arm is imported as in
v1. Then:
- **Checks.** `checks_facts_only_v2.csv` keeps one row per record. It has one `fail_` column per criterion:
  - `fail_unparsed`;
  - `fail_section_order`;
  - `fail_multi_sentence`;
  - `fail_form`;
  - `fail_required_missing`;
  - `fail_unsupported_number`;
  - `fail_invalid_citation`;
  - `fail_forbidden`;
  - `fail_banned_term`;
  - `fail_clinical_inference`.

  Missing or unparsed outputs are failures.
- **Reference check.** The deterministic reference report is checked on all 406 records' facts, with no model. It
  shows how many failures come from the writer and how many come from the specification.

## Outcomes and analysis (all pre-specified)

**Primary outcomes**
1. **Facts-only v2 pass rate.** Checker pass on the 406 records, overall and by cohort, with Wilson 95% CIs.
2. **Paired pass difference.** Full minus facts-only, with a patient-cluster bootstrap 95% CI (2000 draws, seed
   20261026), using v1's `_cluster_ci`.

**Interpretability gate.** "Both arms pass their grounding checks" holds only if facts-only v2 passes at least
386/406 (0.95) overall and at least 0.90 in each cohort. The full arm is 406/406. Secondary outcome 1 is computed in
any case, but it is interpreted as an information contrast only when the gate is met.

**Secondary outcomes**
1. **Information added.** Computed on records where both arms pass.
   - The share of full reports that cite at least one model-derived key in a sentence the v3.1 checker marks supported
     with valid citations.
   - The number of distinct model-derived keys cited per full report: median, IQR, and counts by prefix.
   - Shared-key coverage: shared keys cited by one arm and not the other. Paired difference with a cluster CI.
2. **Common grounding criteria.** The same arm-agnostic tests applied to both arms:
   - unsupported numbers;
   - invalid citations;
   - forbidden wording;
   - the clinical-inference pattern.

   Counts by arm, with paired differences.
3. **Paired shared-fact stress test.**
   - **Set.** v1's frozen 6-record `enhancing_volume_change` set (`stress_shared.jsonl` `82dfe422…`, seed 20261026,
     frame 217), read only. It is not resampled.
   - **Generation.** Facts-only v2 is generated on the 6 perturbed records. In a change from v1, the full arm is also
     generated on the same 6, with the frozen v3.1 prompt and writer, so the stress test is paired by record.
   - **Follows rule, for both arms.** A sentence citing `meas.enhancing_change_since_previous_statement` contains the
     new statement; the old statement is absent; and no written number equals an old changed value unless it also
     equals a perturbed fact. In that last case the record is unscorable.
   - **Reported per arm:** follows, follows and checker pass, unscorable and failed, each with its denominator.
   - **v1's strict rule.** v1's sentence-equality version of the rule is also reported for the facts-only arm.
4. **Descriptive.** Words, prompt and output tokens, batch and process runtime, and attempts. No dollar cost is given
   unless a GPU price is supplied.

## Reporting and manuscript

- The v2 result document reports v1's 0/406 as the first pre-registered attempt, alongside v2. It also reports:
  - every development iteration and every specification change;
  - the preflight;
  - every attempt and every deviation.
- Exploratory analyses are labelled exploratory.
- **Paper.** Nothing goes into the paper unless the gate is met and the author decides. If it is met, a one-sentence
  supplement result on the paired automatic pass rate and the information added is permitted, and it claims no
  clinical benefit. If it is not met, the paper keeps its existing limitation.

## Implementation tasks

The implementation plan below carries these out. No step runs a patient record through the writer until the author
approves this protocol.
1. Shared specification, prompt and checker, with consistency tests.
2. The v2 runner, with the provenance gate, development iterations, freeze criterion and preflight.
3. Freeze, evaluation and paired analyses.
4. The paired stress test.
5. Runs and the result document.
