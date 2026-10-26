# PRISM report version 3.1: the LUMIERE fix, external records in development, and a model-size ladder

Plan: [REPORT_V3_1_PLAN.md](REPORT_V3_1_PLAN.md) (commit 4f7e7b9, written before any v3.1 report). Earlier result:
[REPORT_V3.md](REPORT_V3.md).

**The v3 result stays as reported: LUMIERE S5 0/178.** v3.1 is a second evaluation after a failure that was seen.
It runs on LUMIERE scans whose v3 reports were read (their labels were not), and it is reported as such.

## Rules fixed before evaluation (written 2026-10-26, before any evaluation request)

Where the plan leaves a detail open, these choices were made during development and before any v3.1 evaluation or
perturbation request was built.

- **Checker unchanged.** `checker.py` blob `26d6637a6570549e46a5ca7be7a059033e3a0ac7` (the v3 freeze). The v3.1
  facts keep `system.version = "v3"`, so the frozen checker applies its v3 rules (S5–S7 definitions, thresholds and
  the perturbation `follows` rule as in REPORT_V3.md). `system.facts_version = "v3.1"` marks the new view.
- **Facts v3.1** (`prism/report/facts_v3_1.py`, a wrapper around the unchanged `facts_v3.py`):
  - `scan.rater_statement` = "The rater recorded this scan as within 3 months after radiotherapy: yes." / "no.",
    replacing the bare yes / no field;
  - "number words" means the words the frozen checker counts as unsupported (`checker.NUMBER_WORDS`: three … ninety,
    hundred, half, twice, …). They are written as digits in every facts value; the only one present in the records was
    "the three segmentation volumes" (one-scan image model), now "the 3 segmentation volumes". "One", "two" and
    "both" are not on the checker's list and stay as words;
  - **no RANO** (author decision 2026-10-26, applied before the freeze: RANO is out of the paper): `meas.label` =
    "volumes from the automatic segmentation; indicative". This change is not in the plan.
- **Prompt v3.4** (`prism/report/prompts_v3_1.py`): the v3.3 text, with the system prompt built from the facts
  present. The rater line, the necrosis / cavity / necrosis-with-cavity volumes, each change statement (including the
  change from the smallest earlier volume, whose key the v3.3 prompt had misnamed), the card's agreement statistic,
  and the "no volumes" line for an unmeasured scan each appear only when the field exists. No RANO (author decision):
  rule 4 reads "Do not use response categories such as progressive disease, stable disease, partial or complete
  response"; rule 9 and line b say "indicative" only.
- **Renderer** (no effect on S5–S7): for v3.1 facts, the limitations paragraph and the segmentation-figure title
  ("Segmentation of this scan (automatic; indicative volumes)") omit RANO, and the timing row shows the rater
  statement. v3 facts render exactly as before (all 432 v3 markdown reports re-render byte-identical). The example
  figures are re-rendered into `report_v3_1/figures/`; the v3 figures are left as they are.
- **Development set** (`dev_patients_v3_1.json`, selected 2026-10-26T00:26:05Z, before any v3.1 report): MU, the same
  20 patients (32 intended-use scans); LUMIERE, 10 of 79 patients (16 scans); UCSF, 10 of 140 patients (10 scan-2
  records). Rule: `numpy.random.default_rng(20261027).choice(sorted patient ids, 10, replace=False)`, a fresh
  generator per cohort; the population is the v3 evaluation population of that cohort.
- **Evaluation set**: MU 114 (60 patients, unchanged), LUMIERE 162 (the 69 patients not in development), UCSF 130
  (the 130 patients not in development). The sets are disjoint from development by patient (asserted).
- **Perturbation set (S7)**: 30 v3.1 evaluation records, `default_rng(1)`, 6 per kind, the same kinds and
  `perturb_one` as v3.
- **Failure categories** (ladder): unparsed; unsupported number (including number words); missing flag; spurious
  flag; forbidden wording; conformal or agreement error; invalid citation; plus required content missing and card
  rule, so that every failing report has a category. A report can fall into more than one.
- **Serving**: vLLM 0.31.0 (`/project/community/sbandred/envs/prism-llm`), offline (`HF_HUB_OFFLINE=1`), one H100
  of Slurm job 161514, bf16, greedy, seed 0, `max_model_len` 8192, `gpu_memory_utilization` 0.90, structured JSON
  output. Qwen in non-thinking mode (`enable_thinking: false`, as v3), Gemma with its default chat template. GPU
  memory is reported as the weights' memory from the vLLM log ("Model loading took … GiB") and the peak `nvidia-smi`
  memory, which includes the KV cache vLLM reserves (about 0.90 × 80 GB for every model).

## Development (58 records; Qwen3.8-27B at revision `1d4bf0f2…`, as v3)

| version | change | MU | LUMIERE | UCSF | all | median words |
|---|---|---|---|---|---|---|
| v3.4 (iteration 0) | first version: rater statement, digits, conditional lines | 32/32 | 16/16 | 10/10 | 58/58 | 340 |
| v3.4 (iteration 1, frozen) | no RANO (author decision; facts label, prompt rules 4 and 9, line b) | 32/32 | 16/16 | 10/10 | 58/58 | 304 |

Two of the 4 allowed iterations were used. In iteration 1, no report mentions RANO (iteration 0: 58/58 did, as the
v3.3 prompt asked). The rater statement is cited in 16/16 LUMIERE reports and in no MU or UCSF report.

**Frozen 2026-10-26T00:39:20Z**, before any evaluation request. Git blob hashes (`git hash-object`; also in
`outputs/results/analyses/report_v3_1/FROZEN_hashes.txt`):
`checker.py 26d6637a6570549e46a5ca7be7a059033e3a0ac7`, `facts_v3_1.py 7cea11ae329e08c6064ab4d68084feb51232eca9`,
`prompts_v3_1.py 031605fb0dcad096dd6371bd0b56d9b4039939e6`, `facts_v3.py a14b2fbf6b6c2a40082e734bea07648a09873b55`,
`prompts_v3.py a621edc45e26fbb88e1ee7a6fdaeff3373d571c3`, `sections_v3.py b78c6fe3049b2487a492da02b8f6d4e601301baa`,
`report_v3_1.py 8fa1b71bc8d1f45f93632665e76b7d5603aa2cae`. Unit tests: 16 in `tests/test_report_v3_1.py`
(95 in the suite, all pass).

## Results

*(to follow)*
