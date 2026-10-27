# PRISM report-field ablation: full-evidence v3.1 reports against a strict facts-only arm

Plan: [REPORT_FIELD_ABLATION_PLAN.md](REPORT_FIELD_ABLATION_PLAN.md). It is frozen with its canonical input manifest and
perturbation contract, and was written before any ablation generation. Baseline: [REPORT_V3_1.md](REPORT_V3_1.md).

**Result: the facts-only arm passed its frozen checker in 0/406 reports, against 406/406 for the full-evidence arm.**
Every facts-only report parsed. A post-hoc diagnosis (not pre-registered; see below) finds that every one fails the
same structural rule: a sentence about whether segmentation volumes are available must take one of four exact forms,
and the facts-only prompt never states those forms. On that post-hoc reading, the result measures a mismatch between
the facts-only prompt and its checker. It is not a contrast in grounding between the two field sets. The shared-fact
perturbation followed 6/6. All results here are automatic lexical checks. No clinician,
decision, workload or outcome endpoint was measured.

## Design (fixed before generation)

- **Population.** The 406 locked v3.1 evaluation records: MU 114 (60 patients), LUMIERE 162 (69 patients), UCSF
  grade-4 scan 2 130 (130 patients); 259 patients in all. Source `records/eval.jsonl`, SHA-256 `d5057aec…`, each
  record line hashed in the manifest, source order kept.
- **Arms.** Both arms start from `facts_v3_1(rec)`.
  - `full_evidence` is the immutable v3.1 report. Its requests, outputs and metadata are imported byte for byte; nothing
    is regenerated.
  - `facts_only` removes exactly the keys that begin `pathway.`, `pathways.`, `conformal.`, `card.` or `flags.`. It has
    its own structured prompt, its own checker (`check_facts_only`) and the same pinned writer, Qwen3.8-27B at revision
    `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
  - Serving is vLLM 0.31.0, offline, one H100 (Slurm allocation 162122), bf16, greedy, seed 0, `max_model_len` 8192.
- **Provenance gate** (`freeze`, repeated before every step). It checks:
  - the manifest, the per-record hashes, and the v3.1 `FROZEN_hashes.txt` (`d9dc2ca6…`);
  - the v3.1 requests (`f3eb64b1…`), outputs (`669ae9ff…`), metadata, checks, summaries and stress files;
  - the checker blob `26d6637a…`;
  - 406/406 full reports passing, 220/220 required tiers stated, and 28/30 S7.

  The gate passed; the ablation manifest SHA-256 is `dbb0e3d0…`. Request hashes: full_evidence `f3eb64b1…` (identical
  to v3.1), facts_only `9ca0911b…`.
- **Shared-fact stress set** (facts-only arm only).
  - Kind and edit: `enhancing_volume_change`, the v3 `et_change` edit.
  - Frame: 353 records were eligible. The 136 that are ambiguous by construction were excluded (author-approved before
    sampling), leaving 217.
  - Draw: `default_rng(20261026)`, 6 records (LUMIERE 3, UCSF 3), written once (`stress_shared.jsonl` `82dfe422…`).
  - The model-only kinds (card tier, agreement, out-of-range flag, conformal set) have no facts-only field and are not
    run.
  - The full arm keeps its immutable v3.1 S7 result, which is not paired by record with the facts-only set.
- **Outcomes.** Checker pass with Wilson 95% CI; parsing and truncation; required content; failure categories; banned
  model-derived terms ("leakage"); words and tokens; batch runtime. Paired full-minus-facts-only differences come with
  patient-cluster bootstrap 95% intervals (2000 draws, seed 20261026). No usefulness score is computed.

## Results: evaluation set (406 records, paired by record)

Outputs are `summary_full_evidence.csv`, `summary_facts_only.csv` and `paired_summary.csv` in
`outputs/results/analyses/report_field_ablation/`. They are patient-level and not in git.

| cohort | n | full: pass (Wilson 95% CI) | facts-only: pass (Wilson 95% CI) | difference (cluster 95% CI) | facts-only parsed | facts-only required content |
|---|---|---|---|---|---|---|
| MU | 114 | 114/114 (0.97–1.00) | 0/114 (0.00–0.03) | 1.00 (1.00–1.00) | 114/114 | 2/114 |
| LUMIERE | 162 | 162/162 (0.98–1.00) | 0/162 (0.00–0.02) | 1.00 (1.00–1.00) | 162/162 | 0/162 |
| UCSF | 130 | 130/130 (0.97–1.00) | 0/130 (0.00–0.03) | 1.00 (1.00–1.00) | 130/130 | 1/130 |
| all | 406 | 406/406 (0.99–1.00) | 0/406 (0.00–0.01) | 1.00 (1.00–1.00) | 406/406 | 3/406 |

The required-content difference is 0.99 (0.98–1.00) overall. The parse difference is 0.00. Neither arm truncated or
missed an output. Facts-only failure categories in the pre-registered `summary_facts_only.csv`: `fail_unsupported` 397,
`fail_required_missing` 403, `fail_model_leak` 59, `fail_invalid_citation` 0, `fail_forbidden` 0.
`fail_unsupported` merges unsupported numbers with semantic mismatches.

### Post-hoc diagnosis (not pre-registered)

The finer breakdown below was not specified in the plan. It was added after seeing the 0/406 result.
`scripts/exploratory_field_ablation_diagnosis.py` reproduces it: it re-runs the frozen `check_facts_only` on the saved
facts-only outputs and writes aggregate counts only, with no IDs or text, to `diagnosis_posthoc.csv` (not in git).
A report can fail several criteria. No report text was read.

| criterion | reports failing (of 406) |
|---|---|
| availability or volume sentence not in an allowed exact form | 406 |
| narrative words outside the cited facts and the neutral list | 402 |
| required key not covered | 403 |
| cited key not reflected in the sentence (semantic mismatch) | 397 |
| banned model-derived term | 59 |
| unsupported number, invalid citation, forbidden wording, clinical inference, multiple sentences, section order | 0 |

Here the semantic mismatch (397) is shown on its own. In the pre-registered CSV, `fail_unsupported` (also 397) merges it
with unsupported numbers, of which there are 0. No report fails on a single criterion: 5 fail 2, 3 fail 3, 342 fail 4
and 56 fail 5. The mechanism is narrow:
- **Availability sentences (`meas.available` / `meas.label`).** None of the 784 is in one of the checker's four
  accepted forms (for example "Segmentation volumes are available."). The prompt gives the exact form only for volume
  sentences. Of the required keys, only `meas.available` (403/406) and `scan.phase` (165/406) are ever missed. The
  most frequent unlicensed words are "measurements" (393 sentences), "data" (238),
  "because" (159) and "derived" (116).
- **Volume sentences.** 1141 of 1417 single-volume sentences are in the accepted form.
- **Every one of the 59 "leakage" hits is the word "below".** It comes from a supplied change statement ("change below
  0.1 cc") that the prompt tells the model to copy. The 59 reports with the hit are exactly the 59 records whose
  facts-only facts contain "below" (59/59). The banned-term list and the fixed statements conflict, so these hits are not model-derived content.
- **What did hold.** 0 unsupported numbers, 0 invalid citations, 0 forbidden wording, 0 clinical-inference matches,
  and every report in section order.

**Length, tokens and runtime.**

| arm | median words (MU / LUMIERE / UCSF) | prompt tokens | output tokens | generation | attempts |
|---|---|---|---|---|---|
| full_evidence (v3.1, imported) | 303 (317 / 305 / 290) | 1,143,264 | 475,853 | 437 s batch (1.08 s / report) | 1 |
| facts_only | 95 (86 / 106 / 93) | 216,128 | 255,221 | 138 s batch (0.34 s / report); 261 s process incl. load | 1 (re-run, see Deviation) |

No GPU price was supplied, so no dollar cost is asserted. The two runtimes are measured differently: the full arm has
only the runner's batch time, while the facts-only process time includes model load.

## Results: perturbations

| arm | set | follows | check pass | rule |
|---|---|---|---|---|
| full_evidence | immutable v3.1 S7, 30 records (seed 1), 6 per kind | 28/30 (ET change 4/6; the 2 zero-value artefacts stay misses) | 30/30 | v3 S7 rule, not rescored |
| facts_only | shared-fact `enhancing_volume_change`, 6 records (seed 20261026, frame 217) | 6/6 (0 unscorable, 0 failed) | 0/6 | facts-only shared-field rule |

In all 6 facts-only records:
- the new change statement is written in a sentence citing the change key;
- the old statement is absent;
- no old changed number appears.

The checker fails all 6 for the same structural reason as the evaluation set. The stress batch ran in one attempt
(17 s batch, 139 s process). The two arms' stress results sit side by side and are not paired.

## Deviation

**The first facts-only evaluation run failed, was archived and was re-run.** It started 2026-10-26T22:50:02-04:00.
- Both pre-registered whole-batch attempts (240 s and 93 s, 334 s in total) stopped at vLLM engine start-up. flashinfer
  could not JIT-compile its sampling kernel because `ninja` was missing.
- The cause was a pipeline bug: the ablation runner, unlike the v3 and v3.1 runners, did not put the LLM env's `bin/` on
  PATH.
- No model output existed: 0/406 reports were generated.
- Both attempts' logs and metadata, the empty final output, and the checks, summaries, paired files and facts-only
  Markdown from that run were moved, not deleted, to
  `outputs/results/analyses/report_field_ablation/deviation_2026-10-26_path/`.
- Fix: commit `f259c38` (`fix: put the LLM env on PATH for ablation generation`, with a regression test).
- The re-run started 2026-10-26T22:59:35-04:00 and completed in one attempt.
- Unchanged between the two runs: the prompt, the request file (`9ca0911b…`), the seeds, the model and revision, the
  checker and the stress frame. The provenance gate passed again before every step.
- The stress set was sampled and generated only after the fix.

Other deviations from the brief's command lines, with no effect on behaviour:
- The CLI has no `--arms` or `--model` flags; the writer is pinned in `report_v3_1.MODELS`.
- Step 1's full-arm check is the freeze gate.
- The parent interpreter was `.venv`, because the LLM env has no pandas. The pipeline launches the LLM env itself.

## Limits

- **No clinician, decision, workload or outcome endpoint was measured.** Nobody read a report from either arm. The
  checks are lexical: they test grounding and form, not clarity or usefulness.
- **The facts-only prompt and checker were frozen without a development iteration.** The v3.1 prompt had two. On the
  post-hoc diagnosis, the 0/406 reflects a facts-only checker that accepts only availability sentences the prompt never
  specifies. It is not evidence that the model-derived fields are what make reports pass.
- The stress set has 6 records. It excludes records with zero or near-zero enhancing change (the ambiguous-by-construction
  frame exclusion) and is not paired with the full arm's S7 records. The edit leaves the earlier-minimum fields
  unchanged, as in v3.

## Manuscript options (not applied; the author decides)

The plan allows a compact automatic-ablation result only if the paired outputs are reproducible and interpretable. The
run is reproducible: hashed inputs, a single greedy batch, and every attempt retained. It is not interpretable as an
arm contrast. On the post-hoc diagnosis (not pre-registered), the facts-only failures come from a prompt–checker
mismatch and not from the removed fields.

- **Recommended:** add nothing from this ablation to the paper. Keep the existing limitation that the contribution of
  the model-derived fields to the reports has not been isolated, and that no reader or outcome study was done.
- **Only if a new, separately pre-registered facts-only prompt is developed** (a development set, the allowed
  availability forms written into the prompt, and the "below" conflict resolved) and then evaluated on the locked set:
  a one-sentence supplement result on the automatic paired pass rate. It would claim no clinical benefit.
- Statements that remain safe now: the facts-only reports had no unsupported numbers, invalid citations, forbidden
  wording or clinical-inference matches (0/406 each), and they followed the shared-fact edit in 6/6.
