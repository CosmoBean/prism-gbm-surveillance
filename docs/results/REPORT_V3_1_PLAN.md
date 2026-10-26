# PRISM report version 3.1: the LUMIERE fix and a model-size ladder (plan, pre-specified)

**Written 2026-10-26, after the v3 results ([REPORT_V3.md](REPORT_V3.md)) and before any v3.1 report.** Committed
before the first v3.1 generation. Anything added after the results is marked *EXPLORATORY*.

**Why a second evaluation.** v3 failed S5 on LUMIERE (0/178), and the cause was one design error: the prompt asks
for the "within 3 months after radiotherapy" rater flag, but the facts hold only yes / no, so the "3" is never in a
cited field. The development set held no LUMIERE or UCSF record, so the error was first seen in evaluation. v3.1
fixes the facts and the prompt, adds external records to development, and evaluates again. **The v3 result stays
as reported (0/178).** v3.1 is a second evaluation after a seen failure, on LUMIERE scans whose v3 reports were read
(their labels were not), and is reported as such.

## 1. What changes, and what does not

- **Unchanged and frozen:** the checker (`checker.py`, blob `26d6637a…`), the S5–S7 definitions and thresholds of
  REPORT_V3.md, the perturbation kinds and `follows` rule, the system records, the renderer.
- **Facts (`facts_v3.py` → v3.1):**
  - the rater flag carries its own words, number included: `scan.rater_statement` = "The rater recorded this scan as
    within 3 months after radiotherapy: yes / no.";
  - no number words in any fact value ("3 segmentation volumes", not "three").
- **Prompt (`prompts_v3.py` → v3.4):** built from the facts present. A line about a field (the rater flag, necrosis
  and cavity, the nadir change, the card's agreement statistic) is included only when that field exists, so no
  model is asked about something the record does not hold. Further changes only from the development set (§2).

## 2. Development (prompt iterated only here, with the primary model)

- MU: the same 20 patients (`dev_patients.json`).
- **Added:** 10 LUMIERE and 10 UCSF grade-4 patients, `numpy.random.default_rng(20261027).choice(sorted ids, 10,
  replace=False)` per cohort, written to `dev_patients_v3_1.json` before any v3.1 report and never overwritten.
- At most 4 prompt iterations. The prompt is frozen (git blob hashes of facts and prompt recorded) before any
  evaluation request.

## 3. Evaluation

- **Sets:** MU 114 (unchanged; none of these patients is in development), LUMIERE scans of the 60-odd patients not
  in development, UCSF grade-4 scan-2 records of the patients not in development.
- **Primary model:** Qwen3.8-27B, same revision and serving as v3 (bf16, 1 H100, greedy, seed 0, non-thinking).
- **Primary result:** S5 ≥ 0.95 in each cohort with Wilson 95% CI; S6 = 100%; S7 ≥ 27/30 on a new perturbation
  set of 30 v3.1 evaluation records (seed 1, 6 per kind).

## 4. Model-size ladder (secondary, descriptive)

The same frozen v3.1 prompt and checker, no per-model tuning, on the same evaluation sets and perturbation set:

| family | models |
|---|---|
| Qwen | Qwen3.5-2B, Qwen3.5-4B, Qwen3.5-9B, Qwen3.8-27B (primary), Qwen3.5-35B-A3B (mixture of experts) |
| Gemma | gemma-4-E4B-it, gemma-4-31B-it |

- All local, offline on the node, public weights at a pinned revision recorded in the results. bf16; FP8 of the
  same model only if bf16 does not fit one H100 (recorded as a deviation). A model that cannot be served by vLLM
  0.31.0 is dropped and listed.
- Reported per model: S5 per cohort, S6, S7, failure categories (unsupported number, missing flag, spurious flag,
  forbidden wording, conformal / agreement error, invalid citation, unparsed), seconds per report, GPU memory.
- **Question L1 (descriptive):** the smallest model with S5 ≥ 0.95 in every cohort.

## 5. Data rule

Patient-level records never leave the cluster. No hosted model (Claude API or other) receives a facts view, a report
or any derived per-scan value. A hosted model may be used only on synthetic records, and only as a separate,
labelled exploratory comparison.

Outputs: `outputs/results/analyses/report_v3_1/`. Results: `docs/results/REPORT_V3_1.md`.
