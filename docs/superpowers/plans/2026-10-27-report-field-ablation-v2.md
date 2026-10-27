# PRISM Report-Field Ablation v2 (Facts-Only) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A second, pre-specified facts-only arm. Its prompt and checker are rendered from one shared specification
and developed on the v3.1 development partition. It is evaluated once against the frozen full-evidence v3.1 reports,
paired on the 406 locked records, with a paired shared-fact stress test.

**Architecture:**
- **Specification module.** A new `prism/report/facts_only_v2.py` holds the sentence-form specification and renders
  both the prompt and the checker from it. The v1 module `field_ablation.py` stays frozen.
- **Runner.** A new `prism/analyses/report_field_ablation_v2.py` reuses the v1 runner's provenance gate, whole-batch
  generator, cluster bootstrap and follows rule by import. It adds development iterations, the freeze criterion, a
  preflight, information-added analyses and a paired stress test.
- **Outputs.** Everything is written under `outputs/results/analyses/report_field_ablation_v2/`. The v1 and v3.1
  outputs are read only.

**Tech Stack:** Python 3.13, pandas, numpy, unittest, local vLLM 0.31.0 in `/project/community/sbandred/envs/prism-llm`,
and the existing `prism.report` modules (`checker`, `facts_v3_1`, `prompts_v3_1`, `field_ablation`).

**Spec:** `docs/results/REPORT_FIELD_ABLATION_V2_PLAN.md` (the pre-specified protocol). Where this plan and the
protocol differ, the protocol wins.

## Global Constraints

- **Population.** The evaluation set is the 406 locked v3.1 records (MU 114, LUMIERE 162, UCSF 130). The development
  set is the 58 `records/dev.jsonl` records (MU 32, LUMIERE 16, UCSF 10), disjoint by patient.
- **No evaluation generation before the freeze.** No evaluation-set facts-only request is built before
  `FROZEN_v2.json` exists. No development iteration runs before the author approves the protocol.
- **Iterations.** At most 3 development iterations (0, 1, 2). The freeze criterion is: overall ≥ 55/58; MU ≥ 29/32;
  LUMIERE ≥ 15/16; UCSF ≥ 9/10; and the consistency tests pass. If no iteration qualifies, stop.
- **Field contract.** `facts_for_arm` is unchanged, and the excluded prefixes are `pathway.`, `pathways.`,
  `conformal.`, `card.`, `flags.`.
- **Writer and serving.** Qwen3.8-27B at revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`; greedy, seed 0, bf16,
  `max_model_len` 8192, one whole-batch retry at most.
- **Read-only sources.** `report_v3_1/` and `report_field_ablation/` are read only. The v1 gate
  (`verify_v31_baseline`) runs before every v2 step.
- **Local only.** Records, facts and reports stay local. Committed documents and test fixtures contain no record IDs,
  only synthetic records and aggregate numbers. Development changes are informed only by aggregate counts.
- **Bootstrap.** Patient-cluster bootstrap with 2000 draws and seed 20261026. Wilson 95% CIs.
- **Commits.** No `Co-Authored-By` trailer. End every commit message with
  `Claude-Session: https://claude.ai/code/session_01Babxa1wrvcFxdvDZgq2Hhv`.
- **Test command.** `.venv/bin/python -m unittest`. Never install into `.venv`.

## Review Focus

- **Prompt and checker drift.** A form shown in the prompt that the checker rejects must fail a test. Task 1 pins this
  with a consistency test over every synthetic edge record.
- **Banned terms around copied statements.** The supplied "unchanged … (change below 0.1 cc)" statement must pass,
  and a banned model-derived term outside a copied statement must still fail. Task 1 pins this.
- **Overlap between evaluation and development.** A development record whose patient is in the evaluation set must
  stop the development step. Task 2 pins this.
- **Iteration-cap bypass.** Iteration 3 must be refused, and so must re-running a completed iteration or iterating
  after a qualifying one. Task 2 pins this.
- **Evaluation generation before the freeze.** `requests --sets eval` must refuse without a valid `FROZEN_v2.json`
  whose hashes match the current spec module. Task 3 pins this.

---

## File Structure

- Create `prism/report/facts_only_v2.py`: the specification (forms, banned terms), prompt, parser reuse, checker and
  reference report.
- Create `prism/analyses/report_field_ablation_v2.py`: the CLI steps `dev`, `freeze`, `preflight`, `requests`,
  `generate`, `evaluate`, `stress`, `evaluate-stress` and `render`.
- Create `tests/test_report_field_ablation_v2.py`: tests on synthetic records only.
- Create `docs/results/REPORT_FIELD_ABLATION_V2.md`, after the runs only.

### Task 1: Shared specification, prompt and checker

**Files:**
- Create: `prism/report/facts_only_v2.py`
- Test: `tests/test_report_field_ablation_v2.py`

**Interfaces:**
- Consumes: `field_ablation.facts_for_arm`, `FACTS_ONLY`, `FACTS_SECTIONS`, `FACTS_SCHEMA`, `parse_facts_only` and
  `_required_keys`, plus `checker.check_claim`, `checker.forbidden_v3`, `checker.numbers` and `checker.matches`.
- Produces:
  - `SPEC_VERSION: str` (`"v2-iter0"`, bumped per iteration).
  - `SECTION_OF: dict[str, str]`: key → section.
  - `sentence_forms(key: str, facts: dict) -> list[str]`: accepted forms. The first is canonical. Returns `[]` for a
    key without forms.
  - `required_keys(facts) -> list[str]`: delegates to v1 `_required_keys`.
  - `reference_report(facts) -> list[dict]`: `{section, text, fields}` claims, using the canonical form of every
    required key plus `system.cohort` if present, in section order.
  - `messages(facts) -> list[dict]`: the system prompt lists, for each present key, its canonical form verbatim.
  - `check(claims, facts) -> dict`: returns `pass`, `parsed`, `n_claims` and one boolean per criterion:
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

    It also returns `missing: list[str]` and `non_form_words: list[str]` (aggregate-safe words only).
  - `BANNED_V2: re.Pattern`.

- [ ] **Step 1: Write failing tests** using `tests.test_report_v3.record` and `tests.test_report_v3_1.lumiere`,
  edited into these edge records:
  - each `PHASE_TEXT` value;
  - a previous scan absent;
  - `meas.available == "no"`;
  - a rater statement present;
  - each volume key present;
  - an "unchanged … (change below 0.1 cc)" statement.

```python
def test_every_prompt_form_passes_the_checker(self):
    for facts in edge_facts():
        for key in facts:
            for form in facts_only_v2.sentence_forms(key, facts)[:1]:
                self.assertIn(form, facts_only_v2.messages(facts)[0]["content"])
        r = facts_only_v2.check(facts_only_v2.reference_report(facts), facts)
        self.assertTrue(r["pass"], r)

def test_below_inside_a_copied_statement_is_not_banned(self):
    facts = unchanged_change_facts()  # statement contains "change below 0.1 cc"
    r = facts_only_v2.check(facts_only_v2.reference_report(facts), facts)
    self.assertFalse(r["fail_banned_term"]); self.assertTrue(r["pass"])

def test_model_derived_terms_outside_statements_fail(self):
    for word in ("risk", "progression", "pathway", "confidence"):
        claims, facts = reference_with_extra_sentence(f"The {word} is not stated.")
        self.assertTrue(facts_only_v2.check(claims, facts)["fail_banned_term"])
```

  Add one negative test per criterion. Each changes the reference report minimally:
  - a changed volume number → `fail_form` and `fail_unsupported_number`;
  - a cited key not in the facts → `fail_invalid_citation`;
  - a dropped required sentence → `fail_required_missing`, with `missing` naming the key;
  - swapped sections → `fail_section_order`;
  - two sentences in one claim → `fail_multi_sentence`;
  - "The tumour has grown." → `fail_clinical_inference`;
  - `None` claims → `fail_unparsed`.

  Also test that the leading "The " volume form passes.

- [ ] **Step 2: Run the tests to verify they fail.** Run
  `.venv/bin/python -m unittest tests.test_report_field_ablation_v2 -v`. Expected: an ImportError for
  `facts_only_v2`.

- [ ] **Step 3: Implement `facts_only_v2.py`** with the iteration-0 forms copied verbatim from the protocol table.
  - `BANNED_V2` is v1 `_BANNED` without `above|below|higher|lower`.
  - `fail_form` is true when any claim's case-folded, whitespace-normalised text is not in
    `{f for k in claim.fields for f in sentence_forms(k, facts)}`, or when the claim cites no key.
  - The banned-term, forbidden and clinical-inference checks run on the text with every verbatim supplied statement
    (`*_statement` and `scan.rater_statement` values) removed.

- [ ] **Step 4: Run the tests to verify they pass.** Then run the full suite: `.venv/bin/python -m unittest`. Expected:
  all pass, with 158 or more tests.

- [ ] **Step 5: Commit:** `feat: add the shared facts-only v2 specification, prompt and checker`.

### Task 2: v2 runner, development iterations and preflight

**Files:**
- Create: `prism/analyses/report_field_ablation_v2.py`
- Test: `tests/test_report_field_ablation_v2.py`

**Interfaces:**
- Consumes: from `prism.analyses.report_field_ablation as V1`:
  - `verify_v31_baseline(root, output_root)`;
  - `_whole_batch(root, request, target, guard) -> dict`;
  - `_digest`, `_jsonl` and `_git_blob`;
  - `BASE` and `OUT` (the v1 lock directory).

  From Task 1, everything listed in its Interfaces block.
- Produces:
  - `OUT2 = RESULTS / "analyses" / "report_field_ablation_v2"`.
  - `MAX_ITERATIONS = 3`.
  - `DEV_CRITERION = {"all": 55, "mu": 29, "lumiere": 15, "ucsf": 9}`.
  - `guard_v2(root, output_root) -> dict`. It runs the v1 gate and checks the v1 `provenance.json` hash. It checks the
    `dev.jsonl` SHA-256, recorded at first run in `dev_lock.json`, and that no development patient is in the
    evaluation set.
  - `dev_step(root, output_root, iteration: int) -> dict`. It refuses when:
    - `iteration >= MAX_ITERATIONS`;
    - the iteration's output already exists;
    - an earlier iteration qualified;
    - `iteration > 0` and iteration `iteration-1` has no summary.

    Before generating, it runs the Task 1 consistency check on every development record's facts and refuses on any
    failure. It writes `llm/requests_dev_iter<k>.jsonl`, `outputs_dev_iter<k>.jsonl`, `checks_dev_iter<k>.csv` and
    `summary_dev_iter<k>.csv` (pass and the sum of each `fail_` column, by cohort and overall). It also writes
    `dev_iter<k>.json` with `{"spec_version", "spec_blob", "qualifies"}`.
  - `qualifies(summary: pd.DataFrame) -> bool`.
  - `preflight_step(root, output_root) -> dict`. It builds a one-row request from a synthetic record (from
    `tests.test_report_v3.record`, rebuilt in-module with no test import) and runs it through `V1._whole_batch` into
    `preflight/`. It writes `preflight.json` with `{"complete", "parsed", "request_sha256"}`, and that result never
    counts as an evaluation attempt.

- [ ] **Step 1: Write failing tests:**
  - `test_dev_refuses_fourth_iteration`;
  - `test_dev_refuses_after_a_qualifying_iteration`;
  - `test_dev_refuses_rerun_of_existing_iteration`;
  - `test_dev_refuses_patient_overlap_with_eval`;
  - `test_dev_refuses_when_consistency_check_fails` (patch `sentence_forms` so that it drops a form);
  - `test_qualifies_thresholds`. This runs at 55/58 with each cohort at its minimum (→ True), at 54/58 (→ False) and
    at overall 55 with UCSF 8/10 (→ False);
  - `test_preflight_uses_no_patient_record`. This asserts that the preflight request JSON contains none of the eval or
    dev record IDs and matches no `SUBJECT_ID` pattern; reuse the regex from `tests/test_report_field_ablation.py`;
  - `test_dev_summary_has_one_column_per_criterion`.

  Mock generation by patching `V1._whole_batch` to write synthetic outputs, following the v1 tests'
  `_copy_gated_root` pattern.

- [ ] **Step 2: Run the tests to verify they fail.**
- [ ] **Step 3: Implement the steps above.** Add a `main()` CLI: `--steps`, `--iteration`, `--sets {eval,stress}` and
  `--gpu-hour-price-usd`.
- [ ] **Step 4: Run the new tests, then the full suite.** Expected: all pass.
- [ ] **Step 5: Commit:** `feat: add facts-only v2 development iterations, freeze criterion and preflight`.

### Task 3: Freeze, evaluation and paired analyses

**Files:**
- Modify: `prism/analyses/report_field_ablation_v2.py`
- Test: `tests/test_report_field_ablation_v2.py`

**Interfaces:**
- Consumes: Task 2's `guard_v2`, `qualifies` and `dev_iter<k>.json`, plus `V1._cluster_ci(frame, outcome, seed,
  draws)`, `V1.paired_rows` and `V1._batch_fields`. The v3.1 per-record check details come from
  `report_v3_1/check_details_eval.json`.
- Produces:
  - `freeze_step(root, output_root) -> dict`.
    - It requires a qualifying `dev_iter<k>.json` whose `spec_blob` equals the current `facts_only_v2.py` blob.
    - It writes `FROZEN_v2.json` with:
      - the spec blob and SHA-256, and the runner blob and SHA-256;
      - the writer and revision, and the prefixes;
      - the v1 manifest SHA-256;
      - the `eval.jsonl` and `dev.jsonl` SHA-256s;
      - the stress-set SHA-256 (`stress_shared.jsonl`, v1);
      - the qualifying iteration.
    - It refuses to overwrite an existing `FROZEN_v2.json` that differs.
  - `guard_frozen(root, output_root)`: `guard_v2` plus checks that every `FROZEN_v2.json` hash still matches.
  - `requests_step(..., "eval")`: requires `guard_frozen` and `preflight.json["complete"] and ["parsed"]`. The full
    arm's request is the v3.1 `requests_eval.jsonl`, byte for byte. The facts-only request uses `messages` and
    `FACTS_SCHEMA`, with IDs `eval|<rid>` in manifest order. It writes `request_hashes.json`.
  - `generate_step(..., "eval")`: as in v1, importing the full output and metadata byte for byte.
  - `evaluate_step`. It writes:
    - `checks_facts_only_v2.csv`, one row per record, with every `fail_` column;
    - `reference_check.csv`, with the reference report checked on all 406 facts and no model;
    - `summary_facts_only_v2.csv`, with Wilson CIs and batch fields;
    - `paired_summary.csv`, with the full-minus-facts-only pass difference and the cluster CI;
    - `gate.json`, with `{"overall_pass", "by_cohort", "met"}`, where met = overall ≥ 386 and each cohort ≥ 0.90;
    - `information_added.csv`;
    - `common_criteria.csv`.
  - `information_added(paired, full_details, facts_only_claims) -> pd.DataFrame`. It works on records where both arms
    pass and gives:
    - the share of full reports citing at least one model-derived key in a supported claim with valid citations;
    - the median and IQR of distinct model-derived keys per report;
    - counts by prefix;
    - the shared-key coverage difference, with a cluster CI.
  - `common_criteria(full_claims, facts_only_claims, facts) -> pd.DataFrame`. For each arm and record, it gives
    unsupported numbers, invalid citations, forbidden wording and clinical inference.

- [ ] **Step 1: Write failing tests:**
  - `test_eval_requests_refuse_without_freeze`;
  - `test_eval_requests_refuse_when_spec_changed_after_freeze` (write `FROZEN_v2.json`, then alter the spec blob via
    patch);
  - `test_eval_requests_refuse_without_successful_preflight`;
  - `test_freeze_refuses_nonqualifying_iteration`;
  - `test_gate_threshold` (386/406 with each cohort ≥ 0.90 → met; 385 → not met; overall 390 but UCSF 116/130 → not
    met);
  - `test_information_added_counts_only_supported_model_keys_on_both_pass_records`, a synthetic 3-record frame where
    one full claim cites `card.tier` but is unsupported, so it is not counted;
  - `test_missing_facts_only_output_is_a_failure_in_every_summary`.

- [ ] **Step 2: Run the tests to verify they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the new tests, then the full suite.** Expected: all pass.
- [ ] **Step 5: Commit:** `feat: add facts-only v2 freeze, evaluation and paired analyses`.

### Task 4: Paired shared-fact stress test

**Files:**
- Modify: `prism/analyses/report_field_ablation_v2.py`
- Test: `tests/test_report_field_ablation_v2.py`

**Interfaces:**
- Consumes: the v1 frozen `report_field_ablation/records/stress_shared.jsonl` and `stress_log.csv`, read only and
  hash-checked against `FROZEN_v2.json`. Also `V1._stress_entries`, `V1._numeric_values`, `V1.summarise_stress`,
  `V1.facts_only_follows`, `prompts_v3_1.grounded_v3_1`, `prompts_v3_1.SCHEMA`, and `checker.check(claims, F,
  card=True)`.
- Produces:
  - `shared_follows(entry, old, new, claims) -> dict`. This is the v1 rule with criterion (1) relaxed: a claim citing
    `meas.enhancing_change_since_previous_statement` whose case-folded text contains the new statement, with the
    trailing full stop ignored. The `status` and `follows` semantics are the same as `V1.facts_only_follows`.
  - The stress requests for both arms: facts-only v2, and full with `grounded_v3_1` on the perturbed records' full
    facts.
  - `generate --sets stress` for both arms, with one whole batch per arm.
  - `stress_paired.csv`, one row per perturbed record per arm, with:
    - status and follows;
    - `check_pass` (facts-only: v2 `check`; full: v3.1 `checker.check`);
    - `follows_and_pass`;
    - for facts-only only, `follows_v1_strict` from `V1.facts_only_follows`.
  - `summary_stress_paired.csv`, with every denominator, per arm.

- [ ] **Step 1: Write failing tests:**
  - `test_shared_follows_accepts_new_statement_inside_longer_full_sentence`;
  - `test_shared_follows_rejects_old_statement_present`;
  - `test_shared_follows_marks_zero_value_ambiguity_unscorable`;
  - `test_stress_refuses_changed_v1_stress_set` (alter a byte → RuntimeError);
  - `test_stress_rows_pair_both_arms_by_record`.

- [ ] **Step 2: Run the tests to verify they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the new tests, then the full suite.** Expected: all pass.
- [ ] **Step 5: Commit:** `feat: add the paired shared-fact stress test for facts-only v2`.

### Task 5: Runs and result document

These are operational steps, run by the controller in the Slurm allocation. Each run is logged, and every stop point
below is final.

- [ ] **Step 1:** Confirm that the author's protocol approval is recorded in the protocol (Status line) and committed.
- [ ] **Step 2: Development iteration 0.** Run `python -m prism.analyses.report_field_ablation_v2 --steps dev
  --iteration 0`. Tag `ablation-v2-dev-iter0`. Read only `summary_dev_iter0.csv` and the aggregate non-form word
  counts.
- [ ] **Step 3: Further iterations.** If iteration 0 does not qualify, change only `facts_only_v2.py` within the
  protocol's allowed changes. Bump `SPEC_VERSION`, commit, tag, and run the next iteration. Repeat at most through
  iteration 2. If none qualifies, skip to Step 7 and report a development failure.
- [ ] **Step 4: Freeze.** Run `--steps freeze`. Append the `FROZEN_v2.json` values to the protocol under
  "## Freeze (appended)". Commit and tag `ablation-v2-freeze`.
- [ ] **Step 5: Preflight.** Run `--steps preflight`. Fix and log any failure. The preflight uses no evaluation
  attempt.
- [ ] **Step 6: Evaluation.** Run `--steps requests generate evaluate --sets eval`, then `--steps requests generate
  evaluate-stress --sets stress`, then `--steps render`. If both whole-batch attempts fail, keep every artifact and
  report it. Do not re-run.
- [ ] **Step 7: Result document.** Write `docs/results/REPORT_FIELD_ABLATION_V2.md`. It reports:
  - v1's 0/406 as the first attempt;
  - each development iteration and each specification change;
  - the freeze and the preflight;
  - the primary outcomes, the gate, the secondary outcomes and the stress test;
  - deviations;
  - the protocol's interpretation limits, verbatim in substance;
  - manuscript options, which are not applied.

  Aggregates only. Add a test in the style of `test_committed_docs_hold_no_record_ids` that covers the new documents.
  Commit, and push `manuscript-week`.
