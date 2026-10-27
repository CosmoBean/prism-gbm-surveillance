# PRISM Report-Field Ablation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible paired automatic evaluation of full PRISM reports versus strict facts-only reports on the locked v3.1 evaluation records.

**Architecture:** Preserve the frozen v3.1 full-evidence outputs as the canonical full arm. Build a separate facts-only field contract, prompt, renderer and checker rather than removing sentences after full-report generation. A new analysis module reads the frozen 406-record set, verifies its provenance before generating facts-only reports locally, and writes isolated ablation outputs and paired summaries.

**Tech Stack:** Python 3.13, pandas, numpy, unittest, local vLLM 0.31.0, existing PRISM report facts/prompt/checker modules, CSV/JSONL result artifacts.

**Spec:** `docs/superpowers/specs/2026-10-26-report-field-ablation-design.md`

## Global Constraints

- Use only the locked v3.1 evaluation records: MU 114, LUMIERE 162 and UCSF 130 (406 total).
- Keep patient-level facts, records and reports on the local cluster; do not send them to hosted services.
- Do not modify `outputs/results/analyses/report_v3_1/` or reinterpret its results.
- The strict facts-only arm excludes `pathway.*`, `pathways.*`, `conformal.*`, `card.*` and `flags.*` fields.
- The facts-only arm must not state or infer progression, make a recommendation, or contain prediction-model outputs or interpretation.
- Preserve record pairing, all failed outputs and generation metadata; do not retry individual reports.
- Report automatic grounding/transparency properties only, never clinical usefulness or benefit.
- Do not change manuscript claims until the author reviews the ablation results.

## Review Focus

- **Field partition:** a model-derived field must never enter the facts-only JSON, prompt, deterministic table or rendered report; Task 1 and Task 2 pin this.
- **Shared clinical facts:** scan timing, availability, volumes and longitudinal changes must have identical values in both arms; Task 1 pins this.
- **Frozen provenance:** a changed record count, record hash, full-arm checker hash or writer revision must stop the production run; Task 3 pins this.
- **Checker scope:** facts-only reports must be checked for shared-fact support and model leakage without requiring v3.1 score/tier content; Task 2 pins this.
- **Paired failure accounting:** missing/unparsed output, batch retry and perturbation failure must remain visible rather than disappearing from summaries; Task 3 and Task 4 pin this.

---

## File Structure

- Create `prism/report/field_ablation.py` — immutable arm names, field partition, facts-only prompt and arm-specific checker helpers.
- Create `prism/analyses/report_field_ablation.py` — freeze, request, generate, evaluate, perturb, render and summarise CLI steps.
- Create `tests/test_report_field_ablation.py` — synthetic-record tests for the partition, prompt, checker, provenance and paired summaries.
- Create `docs/results/REPORT_FIELD_ABLATION_PLAN.md` — pre-generation protocol with canonical v3.1 artifacts, field manifest, production command and interpretation rules.
- Create `docs/results/REPORT_FIELD_ABLATION.md` — result report, created only after the production run completes.
- Modify `prism/report/sections_v3.py` only if a small arm-aware rendering hook avoids duplicating stable Markdown/HTML renderer code; otherwise keep the facts-only renderer in `field_ablation.py`.

### Task 1: Freeze the field contract and canonical input manifest

**Files:**
- Create: `prism/report/field_ablation.py`
- Create: `docs/results/REPORT_FIELD_ABLATION_PLAN.md`
- Create: `tests/test_report_field_ablation.py`

**Interfaces:**
- Consumes: `prism.report.facts_v3_1.facts_v3_1(rec) -> dict` and `outputs/results/analyses/report_v3_1/records/eval.jsonl`.
- Produces: `FACTS_ONLY = "facts_only"`, `FULL_EVIDENCE = "full_evidence"`, `facts_for_arm(rec: dict, arm: str) -> dict`, and `freeze_manifest() -> dict`.

- [ ] **Step 1: Write failing field-contract tests**

```python
def test_facts_only_excludes_every_model_prefix():
    facts = facts_for_arm(record(), FACTS_ONLY)
    assert not [key for key in facts if key.startswith(FULL_ONLY_PREFIXES)]

def test_shared_facts_match_the_full_contract():
    full = facts_for_arm(record(), FULL_EVIDENCE)
    facts_only = facts_for_arm(record(), FACTS_ONLY)
    assert facts_only == {key: value for key, value in full.items()
                          if not key.startswith(FULL_ONLY_PREFIXES)}
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_report_field_ablation -v`

Expected: FAIL because `field_ablation` and `facts_for_arm` do not exist.

- [ ] **Step 3: Implement the exact field partition and manifest builder**

Implement `FULL_ONLY_PREFIXES = ("pathway.", "pathways.", "conformal.", "card.", "flags.")` and call
`facts_v3_1` once before filtering only those prefixes. `freeze_manifest()` must record: v3.1 evaluation record IDs
and SHA-256 hashes, counts by cohort, the v3.1 `FROZEN_hashes.txt` contents, primary writer ID/revision from
`report_v3_1.MODELS[PRIMARY]`, and the field-prefix contract. Write the same immutable values into
`REPORT_FIELD_ABLATION_PLAN.md` before production generation.

- [ ] **Step 4: Add representative availability-edge tests**

Use the existing synthetic MU, LUMIERE-with-rater and no-measurement records. Verify that allowed rater wording,
missing-volume wording and scan-change fields remain available when present, while score/tier/flag keys never do.

- [ ] **Step 5: Run the field-contract tests**

Run: `.venv/bin/python -m unittest tests.test_report_field_ablation -v`

Expected: PASS.

- [ ] **Step 6: Commit the contract**

```bash
git add prism/report/field_ablation.py tests/test_report_field_ablation.py docs/results/REPORT_FIELD_ABLATION_PLAN.md
git commit -m "feat: define facts-only report contract"
```

### Task 2: Build and test the facts-only report contract

**Files:**
- Modify: `prism/report/field_ablation.py`
- Modify: `tests/test_report_field_ablation.py`
- Modify: `prism/report/sections_v3.py` only if needed for arm-aware rendering

**Interfaces:**
- Consumes: `facts_for_arm(rec, FACTS_ONLY) -> dict` from Task 1.
- Produces: `facts_only_messages(facts: dict) -> list[dict]`, `render_facts_only(scan_label: str, facts: dict, claims: list[dict] | None) -> str`, and `check_facts_only(claims: list[dict] | None, facts: dict) -> dict`.

- [ ] **Step 1: Write failing prompt and checker tests**

```python
def test_facts_only_prompt_names_only_available_shared_keys():
    facts = facts_for_arm(record(), FACTS_ONLY)
    prompt = facts_only_messages(facts)[0]["content"]
    assert "pathway." not in prompt
    assert "conformal." not in prompt
    assert "card." not in prompt

def test_facts_only_checker_rejects_model_leakage():
    facts = facts_for_arm(record(), FACTS_ONLY)
    claims = [{"section": "scan", "text": "The combined score is 0.80.", "fields": []}]
    assert not check_facts_only(claims, facts)["pass"]
```

- [ ] **Step 2: Run the prompt/checker tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_report_field_ablation.TestFactsOnlyContract -v`

Expected: FAIL because the facts-only prompt and checker do not exist.

- [ ] **Step 3: Implement the fixed facts-only output schema and prompt**

Use the existing structured JSON sentence schema and four ordered sections: `scan`, `measurements`, `longitudinal`,
`provenance`. Require only available shared fields; preserve v3.1 restrictions on unsupported information,
diagnosis and recommendations. Do not mention scores, models, uncertainty, confidence, tiers, flags, pathway,
conformal, risk, progression or a model-derived conclusion in required wording.

- [ ] **Step 4: Implement arm-specific checking and rendering**

Reuse `checker.parse_structured` and numeric/citation support where compatible. Define facts-only pass as: parses;
all cited fields exist and support their claims; all present required shared content is included; no forbidden clinical
conclusion/recommendation; and no banned model-output terminology or numbers. Render only facts-only tables and
fixed limitations; never call `sections_v3.tables`, which requires the excluded fields.

- [ ] **Step 5: Add completeness and leakage tests**

Test a valid synthetic report; a missing required volume/change statement; citation of a filtered key; direct score
wording; indirect pathway/conformal/tier wording; and an allowed sentence that merely states a segmentation volume.

- [ ] **Step 6: Run report-contract tests**

Run: `.venv/bin/python -m unittest tests.test_report_v3_1 tests.test_report_field_ablation -v`

Expected: PASS.

- [ ] **Step 7: Commit the facts-only contract**

```bash
git add prism/report/field_ablation.py prism/report/sections_v3.py tests/test_report_field_ablation.py
git commit -m "feat: add facts-only report generation contract"
```

### Task 3: Implement the paired ablation pipeline and provenance gate

**Files:**
- Create: `prism/analyses/report_field_ablation.py`
- Modify: `tests/test_report_field_ablation.py`
- Modify: `docs/results/REPORT_FIELD_ABLATION_PLAN.md`

**Interfaces:**
- Consumes: Task 1 manifest, existing v3.1 `records/eval.jsonl`, `llm/outputs_eval.jsonl`, `checks_eval.csv`,
  `summary_eval.csv`, `FROZEN_hashes.txt`, and `prism.report.vllm_run`.
- Produces: CLI `python -m prism.analyses.report_field_ablation --steps freeze requests generate evaluate render`;
  output root `outputs/results/analyses/report_field_ablation/`; `checks_<arm>.csv`, `summary_<arm>.csv`,
  `paired_summary.csv`, request/output JSONL and report Markdown for each arm.

- [ ] **Step 1: Write failing provenance and pairing tests**

```python
def test_freeze_rejects_a_changed_v31_record_hash(tmp_path):
    with self.assertRaisesRegex(RuntimeError, "record hash"):
        verify_v31_baseline(tmp_path)

def test_pairing_retains_missing_output_as_a_failure():
    paired = paired_rows(records={"a": rec}, full={"a": full_ok}, facts_only={})
    assert paired.loc[0, "facts_only_missing_output"]
```

Use `unittest` assertions rather than pytest in the actual test file.

- [ ] **Step 2: Run the provenance tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_report_field_ablation.TestProvenanceAndPairing -v`

Expected: FAIL because the pipeline module does not exist.

- [ ] **Step 3: Implement `freeze_step` and `verify_v31_baseline`**

`verify_v31_baseline()` must require the canonical 406-record manifest, original frozen hashes, writer revision,
and baseline full-arm totals: 406/406 parsed/pass, 220/220 required tiers stated and 28/30 formal perturbation
follows. Any mismatch raises `RuntimeError` and blocks `requests`, `generate` and `evaluate`.

- [ ] **Step 4: Implement requests, generation and evaluation**

Write separate request/output paths for `full_evidence` and `facts_only`. The full arm initially imports the immutable
v3.1 outputs rather than regenerating them; the facts-only arm uses the pinned Qwen3.8-27B local vLLM configuration.
Allow one whole-batch infrastructure retry only: retain the failed stdout/log/meta artifact with `_attempt1`, rerun
the identical frozen request as `_attempt2`, and count records with no final output as failures. Never retry a
single report.

- [ ] **Step 5: Implement arm summaries and paired output**

Write cohort and all-record denominators, Wilson intervals for report-level pass rates, required-content coverage,
model-leak counts, parse/truncation/failure counts, words, token counts, runtime and cost metadata. Pair rows by
record ID; calculate patient-cluster bootstrap CIs only for full-minus-facts-only differences in report-level
automatic outcomes. Do not label any column “usefulness.”

- [ ] **Step 6: Run pipeline unit tests**

Run: `.venv/bin/python -m unittest tests.test_report_field_ablation -v`

Expected: PASS without loading a language model or patient records.

- [ ] **Step 7: Commit the pipeline**

```bash
git add prism/analyses/report_field_ablation.py tests/test_report_field_ablation.py docs/results/REPORT_FIELD_ABLATION_PLAN.md
git commit -m "feat: add paired report field ablation pipeline"
```

### Task 4: Add the frozen perturbation and report-output evaluation

**Files:**
- Modify: `prism/analyses/report_field_ablation.py`
- Modify: `tests/test_report_field_ablation.py`
- Modify: `docs/results/REPORT_FIELD_ABLATION_PLAN.md`

**Interfaces:**
- Consumes: Task 3 frozen evaluation manifest and `report_v3_1` perturbation functions.
- Produces: CLI steps `stress`, `evaluate-stress`, `render`; `records/stress_shared.jsonl`, `stress_log.csv`,
  `stress_<arm>.csv`, `summary_stress_<arm>.csv`, and arm-separated rendered reports.

- [ ] **Step 1: Write failing controlled-perturbation tests**

```python
def test_shared_volume_change_is_tested_in_both_arms():
    records = shared_stress_records([record()])
    assert records[0]["kind"] == "enhancing_volume_change"

def test_model_only_v31_perturbations_are_not_run_for_facts_only():
    assert eligible_kinds(FACTS_ONLY) == ("enhancing_volume_change",)
```

- [ ] **Step 2: Run perturbation tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_report_field_ablation.TestStressContract -v`

Expected: FAIL because arm-specific perturbation selection does not exist.

- [ ] **Step 3: Implement two frozen perturbation contracts**

For the immutable full arm, reuse the existing 30 v3.1 perturbations and report their existing 28/30 formal follows
result separately. For the facts-only arm, generate a new fixed shared-fact set before its requests: six eligible
enhancing-volume/change perturbations sampled with a documented seed, preserving record pairing and exact expected
field updates. Do not report model-only kinds for facts-only reports. Define facts-only follows as changed shared
value/wording is supported and the old changed value is absent when it has a unique representation; flag the known
zero-value ambiguity as unscorable rather than a failure.

- [ ] **Step 4: Add rendered-report checks**

Render Markdown for both arms and test that the facts-only report has no model-only headings/tables, whereas the
full-arm report remains byte-identical to the v3.1 canonical renderer for a frozen fixture.

- [ ] **Step 5: Run report and stress tests**

Run: `.venv/bin/python -m unittest tests.test_report_v3_1 tests.test_report_field_ablation -v`

Expected: PASS.

- [ ] **Step 6: Commit perturbation and rendering support**

```bash
git add prism/analyses/report_field_ablation.py tests/test_report_field_ablation.py docs/results/REPORT_FIELD_ABLATION_PLAN.md
git commit -m "feat: evaluate report-field ablation perturbations"
```

### Task 5: Run the locked ablation and document results without changing the paper

**Files:**
- Create: `docs/results/REPORT_FIELD_ABLATION.md`
- Create: `outputs/results/analyses/report_field_ablation/` artifacts (not assumed Git-tracked)

**Interfaces:**
- Consumes: completed Tasks 1–4 and local Qwen3.8-27B revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
- Produces: a result document that distinguishes automatic transparency evidence from clinical utility and gives a
  manuscript-inclusion recommendation without editing `paper/main.tex`.

- [ ] **Step 1: Run pre-generation verification**

Run: `PYTHONPATH=. .venv/bin/python -m prism.analyses.report_field_ablation --steps freeze evaluate --arms full_evidence`

Expected: exact canonical v3.1 counts/hashes and a written immutable ablation manifest; stop on any mismatch.

- [ ] **Step 2: Generate and evaluate the strict facts-only arm locally**

Run: `PYTHONPATH=. /project/community/sbandred/envs/prism-llm/bin/python -m prism.analyses.report_field_ablation --steps requests generate evaluate render --arms facts_only --sets eval --model qwen3.8-27b`

Expected: one local, offline batch for all 406 frozen records, then arm-specific checks and paired summaries.

- [ ] **Step 3: Generate and evaluate the frozen shared-fact perturbation set**

Run: `PYTHONPATH=. /project/community/sbandred/envs/prism-llm/bin/python -m prism.analyses.report_field_ablation --steps stress requests generate evaluate-stress --arms facts_only --sets stress --model qwen3.8-27b`

Expected: a documented fixed shared-fact stress set, no model-only perturbations, and all failures retained.

- [ ] **Step 4: Write the results document**

Document population, frozen hashes, arm manifests, full-arm baseline, all automatic outcomes with denominators/CIs,
generation attempts and failures, shared-fact perturbations, trade-offs, and the exact limitation: no clinician,
decision, workload or outcome endpoint was measured. Give conditional manuscript options: include a compact
automatic-ablation result only if the paired outputs are reproducible and interpretable; otherwise retain the
unresolved limitation.

- [ ] **Step 5: Run regression and artifact verification**

Run: `.venv/bin/python -m unittest tests.test_report_v3_1 tests.test_report_field_ablation -v && git diff --check && git status --short`

Expected: all relevant tests pass; no modified v3.1 artifact; only intended new code/docs/output artifacts changed.

- [ ] **Step 6: Commit source, tests and results document separately from patient-level outputs**

```bash
git add prism/report/field_ablation.py prism/analyses/report_field_ablation.py tests/test_report_field_ablation.py docs/results/REPORT_FIELD_ABLATION_PLAN.md docs/results/REPORT_FIELD_ABLATION.md
git commit -m "feat: evaluate report field ablation"
```

## Self-Review

- **Spec coverage:** Tasks 1–2 implement field separation and arm contracts; Task 3 freezes/reuses the canonical
  full arm and evaluates pairing; Task 4 covers arm-appropriate perturbations and rendering; Task 5 runs and
  reports the automatic study without changing manuscript claims.
- **Step scan:** every task has a failing test, a specific implementation interface, passing verification and a
  separate commit.
- **Type consistency:** `facts_for_arm`, `facts_only_messages`, `check_facts_only`, `freeze_manifest` and the
  pipeline step names are defined once and used consistently in later tasks.
- **Review focus:** each listed failure class is covered by an explicit task test.
- **Proportion:** this plan specifies contracts and decisions, not implementation bodies; the exact prompts and
  checker patterns remain focused modules to be written test-first.
