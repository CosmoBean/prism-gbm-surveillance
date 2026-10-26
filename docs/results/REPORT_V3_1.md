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

## Results: primary model (Qwen3.8-27B; 406 evaluation reports, 30 perturbed)

Evaluation generation started 2026-10-26T00:40:37Z, after the freeze. Outputs: `summary_eval.csv`,
`summary_stress.csv` in `outputs/results/analyses/report_v3_1/` (patient-level, not in git).

| cohort | n | S5: pass (Wilson 95% CI) | S5 | S6: tier stated (few cases / not tested) | S6 |
|---|---|---|---|---|---|
| MU (intended use, 60 patients) | 114 | 114/114 = 1.00 (0.97–1.00) | **met** | 71/71 | **met** |
| LUMIERE (69 patients not in development) | 162 | 162/162 = 1.00 (0.98–1.00) | **met** | 19/19 | **met** |
| UCSF grade-4 scan 2 (130 patients not in development) | 130 | 130/130 = 1.00 (0.97–1.00) | **met** | 130/130 | **met** |
| all | 406 | 406/406 = 1.00 (0.99–1.00) | met | 220/220 | met |

- **S7 (new perturbation set, seed 1; 7 MU, 13 LUMIERE, 10 UCSF records): follows 28/30, met** (≥ 27). By kind:
  agreement 6/6, card tier 6/6, conformal 6/6, out of range 6/6, ET change 4/6. The full check passes on all 30
  perturbed records. Both ET-change misses are the rule artefact already seen in v3: the old change was 0.0 cc, and
  "0.0" is also, correctly, the current enhancing volume (and other zero-valued fields), so the rule's "old value
  absent" cannot hold. In both, the new magnitude and the right direction are written (checked as booleans; the text
  was not read). *EXPLORATORY reading:* the reports followed the change in 30/30.
- **Everything else, all 406:** 406 parsed, 0 truncated; 0 unsupported numbers (no number words); 0 invalid
  citations; 0 active flags omitted, 0 spurious; 0 forbidden content in any category; 0 conformal or agreement
  errors; required content present in all; card rule passed in all. No rendered report (406 markdown, 3 HTML
  examples) mentions RANO.
- **Length and cost.** Median 317 words (MU), 305 (LUMIERE), 290 (UCSF). Batched 1.08 s per report on one H100 (437 s
  for 406), plus about 1 min model load.
- **Answer to the v3 failure.** The LUMIERE pass rate goes from 0/178 (v3) to 162/162 on the LUMIERE patients not
  in development. The rater sentence is now supported by the field it cites. The v3 result is not revised.

## Model-size ladder (secondary, descriptive; frozen prompt v3.4 and the unchanged checker, no per-model tuning)

Same evaluation and perturbation sets, all local and offline, pinned revisions:
Qwen3.5-2B `15852e8c…`, Qwen3.5-4B `851bf6e8…`, Qwen3.5-9B `c2022362…`, Qwen3.8-27B `1d4bf0f2…`,
Qwen3.5-35B-A3B `59d61f3c…`, gemma-4-E4B-it `ee0ef602…`, gemma-4-31B-it `842da379…`
(full shas in `prism/analyses/report_v3_1.py` and `ladder.csv`). All in bf16; none was dropped.

| model | S5 MU (CI) | S5 LUMIERE (CI) | S5 UCSF (CI) | S5 ≥ 0.95 in every cohort | S6 | S7 follows | s / report | weights GiB |
|---|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | 0/114 (0.00–0.03) | 21/162 (0.09–0.19) | 0/130 (0.00–0.03) | no | 204/220 | 21/30 | 0.13 | 3.6 |
| Qwen3.5-4B | 44/114 (0.30–0.48) | 155/162 (0.91–0.98) | 107/130 (0.75–0.88) | no | 220/220 | 27/30 | 0.17 | 8.0 |
| gemma-4-E4B-it | 33/114 (0.21–0.38) | 73/162 (0.38–0.53) | 11/130 (0.05–0.15) | no | 220/220 | 25/30 | 0.17 | 14.5 |
| Qwen3.5-9B | 98/114 (0.78–0.91) | 156/162 (0.92–0.98) | 114/130 (0.81–0.92) | no | 220/220 | 28/30 | 0.21 | 16.8 |
| **Qwen3.8-27B (primary)** | 114/114 (0.97–1.00) | 162/162 (0.98–1.00) | 130/130 (0.97–1.00) | **yes** | 220/220 | 28/30 | 1.08 | 50.2 |
| gemma-4-31B-it | 114/114 (0.97–1.00) | 162/162 (0.98–1.00) | 130/130 (0.97–1.00) | **yes** | 220/220 | 28/30 | 4.86 | 57.9 |
| Qwen3.5-35B-A3B (MoE, 3B active) | 97/114 (0.77–0.90) | 162/162 (0.98–1.00) | 130/130 (0.97–1.00) | no | 220/220 | 28/30 | 0.74 | 64.7 |

Failure categories (reports out of 406; a report can be in more than one):

| model | unparsed | unsupported number | missing flag | spurious flag | forbidden wording | conformal / agreement | invalid citation | required content missing | card rule |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | 24 (truncated) | 71 | 24 | 0 | 15 | 154 | 62 | 339 | 18 |
| Qwen3.5-4B | 0 | 4 | 1 | 0 | 0 | 4 | 0 | 93 | 0 |
| gemma-4-E4B-it | 0 | 0 | 0 | 0 | 0 | 224 | 33 | 132 | 0 |
| Qwen3.5-9B | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 37 | 0 |
| Qwen3.8-27B | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gemma-4-31B-it | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Qwen3.5-35B-A3B | 0 | 0 | 0 | 0 | 0 | 17 | 0 | 0 | 0 |

What fails (aggregate counts; no report text was read):
- **Below 27B the main failure is omission, not invention.** Qwen3.5-4B leaves out the timeline and image scores
  (92 reports; the value is written in 7 of them, never in a claim citing the score), mostly on MU (69). Qwen3.5-9B
  leaves out the enhancing volume (37). gemma-4-E4B-it leaves out the combined score (104) and the combined 80%
  conformal set (222). Spurious flags: 0 for every model. Forbidden wording: only Qwen3.5-2B (15).
- **Qwen3.5-35B-A3B** fails only by not stating the combined score's 80% conformal set, in 17 MU reports. It meets
  S5 on both external cohorts and overall (389/406 = 0.96), but not on MU (0.85).
- **The conditional prompt removed the v3 fabrication.** In v3, Qwen3.5-9B wrote the LUMIERE rater sentence for MU
  and UCSF scans (85/432 passed). With v3.4 it passes 368/406, and none of its failures is a citation of a key that
  does not exist.
- **GPU memory.** "Weights" is the vLLM model memory. The peak `nvidia-smi` memory is 69–75 GB for every model,
  because vLLM reserves 0.90 of the GPU for the KV cache. gemma-4-31B-it is slow (4.86 s per report) because its
  weights leave about 9 GiB for the KV cache (about 11k tokens, 1.3 requests at a time). The others batch freely.

**L1 (the smallest model with S5 ≥ 0.95 in every cohort): Qwen3.8-27B**, the primary model. The only other model
that meets it is gemma-4-31B-it, which is larger and 4.5 times slower here. No model below 27B meets it.
Qwen3.5-9B comes closest (0.86 / 0.96 / 0.88). The 35B mixture of experts misses on MU only.

*EXPLORATORY: Qwen3.5-35B-A3B-FP8* (`9d1823d2…`, 33.4 GiB weights, 0.21 s per report). It ran by mistake: the
fallback script started it after the first bf16 attempt failed on a serving setting, not on memory (see
Deviations). S5 93/114 MU, 162/162 LUMIERE, 127/130 UCSF; S6 220/220; S7 28/30. Its failures are again the combined
80% set not stated (24). It is not part of the ladder, because bf16 fits.

## Deviations

- **RANO removed (author decision 2026-10-26, not in the plan)**, applied before the freeze, as a second development
  iteration: facts `meas.label`, prompt rules 4 and 9 and line b, the limitations paragraph and the figure title.
  Renderer only for the last two; v3 renders unchanged.
- **Qwen3.5-35B-A3B serving.** At the default `max_num_seqs` 256, vLLM refused to start (158 Mamba state blocks at
  `gpu_memory_utilization` 0.90), although the bf16 weights fit (64.7 GiB). The fallback script then ran the FP8
  checkpoint automatically (reported above as EXPLORATORY). The ladder entry is bf16 with `max_num_seqs` 128, a
  batching limit that does not change greedy decoding. No FP8 was needed for any ladder model.
- **gemma-4-E4B-it** served text-only (`limit_mm_per_prompt` image, video and audio 0). The others use the default
  image 0, video 0.
- **Changed after the freeze, no effect on the rules:** `report_v3_1.py` (the `--gpu-mem` option, the FP8 entry and
  the 35B `max_num_seqs`; frozen blob `8fa1b71b…`). Facts, prompt and checker are unchanged (blobs above, checked
  after all runs).
- **Failure categories** extended by "required content missing" and "card rule", so that every failing report has a
  category.
- **"Number words"** is defined as the frozen checker's list (above). "One", "two" and "both" stay as words.
- **Model cache.** Qwen3.5-9B and gemma-4-31B-it were already complete in the cache. Their model folders are small
  because the weights sit in the cache's shared blob store; the revisions were checked against the hub. The
  missing models were downloaded on the login node at the pinned revisions.
- **No report text was read by an AI agent in v3.1** (data rule, plan section 5). All failure descriptions above are
  counts from the checker output. v3 had paraphrased examples; v3.1 has none.

## Limits

- **This is a second evaluation after a seen failure.** LUMIERE's v3 reports were read, and the fix was designed
  after that. Development now holds 10 LUMIERE and 10 UCSF patients, and evaluation excludes them, but the LUMIERE
  scans in evaluation are the same scans whose v3 reports showed the error.
- The checker is lexical. 406/406 means every number, flag, conformal set, agreement statement and tier is
  faithful to the record and no forbidden wording appears. It does not mean the reports are clear or useful. No
  clinician has read a v3.1 report.
- S7 uses 30 perturbed records. The `follows` rule for the ET change cannot score a record whose old change equals
  another value written correctly (2/30 here, 1/30 in v3).
- The ladder is one prompt tuned on one model (Qwen3.8-27B). Smaller models might do better with their own prompt;
  the plan does not test that.
