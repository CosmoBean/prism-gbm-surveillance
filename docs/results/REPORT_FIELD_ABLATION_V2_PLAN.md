# Paired report-field ablation, facts-only v2: pre-specified protocol

Written 2026-10-27, before any v2 code, prompt, request or generation. Status: **approved by the author on
2026-10-27**, before any v2 code, prompt, request or generation. Implementation plan:
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

## Freeze (appended 2026-10-27, before any evaluation request)

- **Development.** Iteration 0 (specification `v2-iter0`, commit `ef9d90b`, tag `ablation-v2-dev-iter0`) passed
  58/58: MU 32/32, LUMIERE 16/16, UCSF 10/10. Every `fail_` count was 0, with one whole-batch attempt. It met the freeze
  criterion at the first iteration, so no specification change was made and iterations 1 and 2 were not used.
- **Checks before development.** The model-free consistency check found 0 of 58 development records with errors. The
  synthetic preflight completed and parsed.
- **Frozen code.** `facts_only_v2.py` blob `a32e79c5fb3836526381ccb207a09303800ffdd5`; runner blob `c0f76119473a8f91253ec6486fabcaffc60c0d99`; and the imported
  modules below. The runner blob equals the qualifying iteration's.
- **`FROZEN_v2.json`** SHA-256 `6c1e530de044df1b8a3eb14e57c31b504a6739565def5e59f17bb25c37868e92`. Its content follows. The per-line hashes are in
  source order and hold no record IDs.

```json
{
 "spec_version": "v2-iter0",
 "spec_blob": "a32e79c5fb3836526381ccb207a09303800ffdd5",
 "spec_sha256": "88a1d8144943e256c03015fc3fb7fadceb762dcbaba9b7cac4bad0b74ead52bf",
 "runner_blob": "c0f76119473a8f91253ec6486fabcaffc60c0d99",
 "runner_sha256": "1bfa12e0322b5394a2dc7f654f3f7c1b7f4a279e0ab6e628290010ba675845a7",
 "import_blobs": {
  "prism/report/field_ablation.py": "f1fad42fc0623541a6af9b929d9495ea16ff0c2d",
  "prism/analyses/report_field_ablation.py": "35743f0abeb54658338ef1cd00b72962857958f2",
  "prism/report/vllm_run.py": "b179d7e972a60c6c9faba969d681f12b832606ed",
  "prism/analyses/report_v3.py": "35562be0372d24386b6e627bae912e64abe4a221",
  "prism/analyses/report_v3_1.py": "b52c3af2091d6b5f03654dd2edff54541359e52d"
 },
 "serving": {
  "key": "qwen3.8-27b",
  "id": "Qwen/Qwen3.8-27B",
  "revision": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
  "chat_kwargs": {
   "enable_thinking": false
  },
  "extra_args": [],
  "llm_env": "/project/community/sbandred/envs/prism-llm"
 },
 "writer": {
  "key": "qwen3.8-27b",
  "id": "Qwen/Qwen3.8-27B",
  "revision": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
 },
 "prefixes": [
  "pathway.",
  "pathways.",
  "conformal.",
  "card.",
  "flags."
 ],
 "v1_manifest_sha256": "bca995bbfd21d0cccfef0363aa84991fa8537a0b85609eb303bae6dcea1a2ff3",
 "eval_sha256": "d5057aec85da38523c0d515165cc9dcb476811c1889b4543137792e9229abb1e",
 "eval_line_sha256": [
  "63be1c9a8a93436600cb1640de328500ab3ce8e4f64a10640effc06c679953f0",
  "d24d625142fb487520ba7ba3832dbe933cbdb806afb1007c1051e4e506126652",
  "dabe6da524ca9d73944a98f203880704ca4ceb2eb37f4cd8f3fc60507363e45a",
  "6b2e6768bff0350988c4d552359095fbdca1e260b08b381c390711fc9a640e14",
  "f109ab56c93f9928ed872371541e5c69f629cd861d3b266c55f581f2bc777250",
  "2040d8b0360edfd4b3d772f50c6493f0e85b4ebc8fafc083c3c052dc12e0b6c4",
  "9e817cd8aa22529e8cbe9c9019d0cc7fbb63d8e37ea960c571aeadbea2b0b00a",
  "9ab624c94e668a91f244da83392ceded08cf37cc2af4e27135e18df6f176012e",
  "bd6d2c5ebf84da0be777996bf1f2be48c4e0bcee46f19ca3301a0d928fcb8e69",
  "561715118c1b3a4a01c87e7239cecd0a6d622eb0412bbfb31f5a6590379cadd2",
  "44bcfe9781d9149fe4272b12795454a7be9a1149d4309fdfddec66251084771c",
  "d6e942827e5d9781a949227dbfee6c2d773ece10fdc9e5c95e087b3e169c7de7",
  "92bfa0b26f1f2f194f0b593e571005a30a63ea1e4a2b326bc58dc839737ebe36",
  "d94d3a03d1479d2add5d9226ba5b3345f6171c5dbf37e9f610b1633b74a994b1",
  "5f1f23dfa7eb75eae05c29af2db583d20b41c9b53bdc5be6db122c8c5d238cf8",
  "f7eb865c0e6b39f960db9d82170b9ded73d0c110b442947dd8c09dd33949e16c",
  "281202a0eba460ab5329caecfccbd8faa5c78df9124e34822a0b9391ea05808e",
  "b83b056c2a4230528b5cc57c455ecf2b550948761fa9ff43ddce26780490e0a4",
  "ce63d9d82021038d6db47d2d43d8ab946c70756298be8837c040b87d364737ad",
  "86eb0bcb262f9fe59c943289be17105e3639ca0b4acc6a8fb7490139ab2041df",
  "2d8d2b0c244006d5641830740ce28d1d7ca3e776dfde285828b605084327c1de",
  "137046da14cb901231e7f2b3b7a8eb88d910459f62c00024be8d0d173bf40513",
  "f6eb528ef6a701ed04c56606eeb17bae999b6c2b637c37f7d6e2825c78134df2",
  "546d8e6a6d87fdccdbcca296cbc97b6e8a7afbcd0e99e7f5f6f42249d349237a",
  "b751562e0ffb7402d11fa86c595d791b0dbebb49dd8eb30c2eb4e6ef852439a7",
  "52a13d77bbae1777be45a5c3cd19561419ecefa8c6cb9fb9d8375fc2d61d4cd3",
  "b1dab3583f86da0fb59826409272f5fc9381d442dc84e86149a084f29b1d6305",
  "7bcda9805f07c8dbfd650ceff520677ffefcedd5917571577062554f46bf8a77",
  "ee37e7af271cfaefd97345f18571aa18954b8e64cd15dad9e86b78ae2bb9c47e",
  "c1f7c3a7df4044e98d4d5061e24d2c17c589ea2e0cbd717f834130c260fd9a6b",
  "891624c63712e5fd658ed759ab8403f912e64709f33d6ac166ee868193e5c1f3",
  "bbad151afab7dc8232264c61f2be2c707178e41ab91539c0b2dce7dfbd077032",
  "1107588052ef5c61cdb5f579f197d801fa4a2351d561059154f6873be268cf5e",
  "3b3b16d8fdab9dafc71a98ddfdc8124e8a7ece23dfb92a1f66bd3fd1a9991b81",
  "cd531c743041214a43914def14532586309dc41888b91cfcb973912619f16c36",
  "700a188cb9198662f7e72cd2f4719e5634e0c85cbdfa303d9ac0a64d9403e510",
  "0c8771df7a08ba6061eee46c1b7a65c80ec35487627e556ae7ef60220fd1b85d",
  "bd11cf007a20aec83295cecc5cb7d386c207b458ba8d29e137fbc22b5fb419b1",
  "5ff82a4ba4d6db2084e0a61d9df38d508a16460a7121e11ef2d5979e6c72ac89",
  "5dbb415bef8fb0d69059dac8aaf96292df3a638501ab167b5961dd8d895b1d33",
  "37d2a378715350b298565409f6806e7da60de8816740cff8bf3f5b61c20396a8",
  "cf2baa2f2aaa9ee2a4cd7ad14f8c73829197957fe073274812350124b72c9ddd",
  "e12e3830065618dfe5e33fb52976f9f4db3a8ee9d6e7a7c237c142b25ee3caad",
  "c059c22967ae3c3e92c9d8451795d5fd901c5533ed735eb3e334bad2a627d352",
  "3c6c52b772da781650177e8c531e74caf9ad7c1d82d13728760264badac87b8c",
  "5c17de82f0ae27a0966134dfaf387436133bfbdc1d03e12af6ab9fe0831c52c4",
  "9e97add7523b4c3b5ae96ba2bbc283dbee02b78773adf3b0fc125f4aea784af3",
  "e1c004d89f5372be3df578cd2654ed6987a08d7eea4f8ab895a2799c890c552e",
  "d8188ca8f1426aa23044f73ebc7400c34295792299098743a1e24bc305bbe296",
  "dee649312c45adda9051d99dc7d7767725631bb0aa20fc17110c1150d5d2ad63",
  "260c958fd31345c773df6759c270412fed27679a5df91164813f0c62f27761a8",
  "d7e3f5f57b6f3b3eba7063b6f75ef2cb9d67d9470c836ed14baf10cdee97b8d2",
  "b07c5edefe134696d284a630b52c5a33975e18994c41e391683cf4e82a260b2f",
  "92de896fccdd09a8cb1407f77ceaf688420fa00dff2cf9abc7552323836f6365",
  "3a05d3c659210ccc5d528f1bdd645c40a4655a47f4f037724f9e7219ef52c75d",
  "0b88da36dcfc97c6422032e5db1828f30cbc97934826d457fc825d0c7a09c7e9",
  "01a36afc44b7d685d5d5ec8b9af1d9fc8a42b4dab767e0de7febbb705bda07b7",
  "93ab7be7addb751e3931d84ae75011c015dbc8b31baa70356799680d071cebe1",
  "a3f4a85aabaea93109ef996efd8743bdd7f1622525521050f82d7d6c017d5940",
  "69c4cb040d0c1b04fa7e6e1ee204d7c4d776cc728ffb6201781a4804eaaea17c",
  "0c9dbb162dc1e2e9d27180ab299a48aef5d0911e7fd5ea39124319f5f7744825",
  "6c16a419546e988d7577a00ea27e611f9427ba02707d1af439447fa320eab8f1",
  "69083940ec6bb0a7807545b915ecc447b643c426596f9b72414546367091fcbf",
  "04364d7c8e8320099b8759ef0d320aad877043b77751c0cd51d877d791ce861e",
  "acb55cc3767b58b3fb29411bc65178a059f76d238b77fb5559cab85dd0b26d4b",
  "e8af1767979d45c0d4d39b07f4353a109c9b7a275ee4585e35a161392aa96d38",
  "74effcf82faa0e5a3b179a2f0e59348e2961789880868a44711a9332b28e004b",
  "de2dafe587647c070e7b10b09a68da737aa36ae91aceb08cbfe5916d72bc906c",
  "1568e90db5a4685d06a65baa008cb90072aa9e4f9ef793af61ac57c3924c0c00",
  "3e9a10e634355f03ad42d375d45ba2fd353e3ec9d4be465f79a5ef0379ac42fd",
  "900ac5c09052a65cf017c42d453e4adddc3f9902cd55788b48e41df0cadfb708",
  "05a3270266649647f51efe09f14b1a44f1e721c1f5086abaa57bbf53772bd344",
  "7aea7b190d0e2bdc4a5483f44403fb0111cbbd9d63cf7df4a66701d4cc845ee8",
  "1384c1eeb985410943aa66c1e1f7f63e69df6b68d533370aaec69a4a76306544",
  "49c996f3418bd63d61c143dd8dee5d70d641d30b039458cce560ba52cdc1b129",
  "8385b8606bfb4d129cce0b19d0e218c2c49ae90af5d0d98349cf08a4e4c4539d",
  "cf54fe4159b7a73fc9abe42c02d6b244144f52ad8a37e59f5e4d7b16e32507ed",
  "635d3b423e8af0010ee4239dc34bbe99841c94826709354473b2f54b44d80018",
  "9b7c1a8abf291b1acc88a6e0cecfa884562b156b32ffdc278ce824df4384ae50",
  "c4d6a31d831b2bb43a96910abf6b27862bb5b7d76a7e2f4e83c2d72ec097255d",
  "1604377352783d75bc01fa22b435908f581ae03279b3bebec35915336461b4c2",
  "13e79862d155cd22b55a6f521953b645f9bb789ae9d05c831f2e11727e2f173b",
  "c4c914aae8bd2e828c0112502fa3c28f250e01ec3f49d2b2c774f24dd7aeb4af",
  "ec4738ca141aaceb19bc395e385dbdae61224a92d20c4c4d300c53cde42e2473",
  "deafc35d7f85ea61efbeae542f1f41a5d9eef37ce9bbcba4395c6b3e8e101eee",
  "1362c6ce88856b8c15364827ce8c922d60fa5f93373d4e9471139de233311e33",
  "a360f9f59206caff2eaf2397203a79abc797eec43035fba81e6650231943cb08",
  "e3e53a9099e6bef06de20d88f0f62698b10f64c544dccf143a32fe0579cff58f",
  "1f9ff0b8a38dbbb8c11ab95693c9b0f8c1b62a29b6654a19fba1203e52ba986d",
  "40067368fa8b7c625f37a8377cfaf83b6be77be92a6c006874c268df8b2aa533",
  "0f9cf25fe471f7a59246f32b7e31c293761e3a5b70bc0ace7dd977d91f46e843",
  "989fbd19876d3f5fb5470159c02105dcadce8aa1cf1ef689e87da5bc905acca3",
  "8a754236206f84e3e5db6f9c85942a546670e4b63f29a49d0d42fd69e5d23719",
  "a01d9bdec792ae5cd79085c02d5e3dbbec80baf3c053d7602e99c9747d09e49b",
  "bf59e50ef244400469d88525c91cd17d6adfcb5e568e294e8bf256dd1b6018e9",
  "fde4909d747257ebc8ac950f0e17b98a89608c369ff68c99ea62b9296a9358c7",
  "38ddffe2abd584b848579f3023bce19f1cf416c3817f547c8c66a05d0b48b7bb",
  "332ca3909db8a50cbd80a4e6381d9a6d78cff6929286cab6f3d407adeeff6d88",
  "2c483856a1dfe7e929e1fec82a6434225f9c37e892cfaa629aea606576d2623c",
  "6703916c203b12a7dc453cb61140ecbd41813d7ac01bc958ed0618061a7b0834",
  "34a77ec017d90b7f8a6102f321efbae1443a11575322a148b199ec90e7fd40fe",
  "b6d281da0b8fccc1c248b878d523c0683a27f88d48382154b315426109cdb1cb",
  "025dbf532032c033919ec646de3600751eb2e75ba68b8cc11479eba3b1884c80",
  "1815ab249ae69054bc4a31094d879ff09a3429317d5d2436d91952e041e144f2",
  "05c831b74eb45e4d2b5456389a85ba85cc643dbd0380d43186f2be001604b0f8",
  "0d1a0e68b9dbd83745181a94e408bbac404988112839931bce46144627f47228",
  "bee442df3c43d8721048e8558a517fe6d71c00bdcfb9bfbb6a7cb121726be4e0",
  "b06208731fd7367bda405e9c5fd59e17949cf3b4fca1d4cf468c4250423f33d7",
  "9c693a8e7332446c9a916b867cf45abe23beec38be44f4619a8c9d37d245496f",
  "fe8fefe7e106e28d602fb3ab35cf4458f1a310225f13f4a4b6a1f32feb567d1f",
  "4dc5df0f376d8ecd2a8dd91f515a732ddb7dba37d50f9026b5ef2c04e0836e57",
  "52132a3e4dde8e521d8d93e924ba98f16d26fc1751f865d7d6b82865360e0938",
  "59cc37504b4312d85ee0d7ea97be2c77b719e93f21520632355dda5aac0f8930",
  "e55ebc741c431df4081bc183f88b198265ed8493fdc58dd92f4e4c5607600ef2",
  "53b7b07f8dd81ec73c939cd3dcdceb3f612d3e7edadef18e9635836b1df37b50",
  "e0c8a81cd1b5c4e694830d29068a2fa8ffadc58d5fc3d64a09ba8ac4dad1c9ff",
  "6bea0f452cea3a8baf095959497fbe7e1b86b109eba84fee1a1a0d34a6bb040e",
  "ad82f9e84d03c95df31d6b038f1f5c3238f8b2853067c537bc52c468757a2170",
  "ab382cade2270e96a3b26237a4a9e761e750cd586edba38335c451e80f84504e",
  "dd3b3e765aec50496a886511e8c18ce4809112653291416d371d014d20cc0592",
  "dcc7f5d875ae17528a58a7db594288fa748025881457ebd67b0439917e483b57",
  "ae5d51f26e85ddab90f78b573e928fa9290dc16021c1c535e5846cc018963676",
  "f1fd131b9111522355171f079dc819b9572b5f6183f7c787262e5a4df0b91d77",
  "d674f5fb9b1cb1d1a9875e809d6c4b34e61ef56d32b01b265507b906cb58c6bb",
  "ee837e22059da050a5a2774fb90f5af964bd7ed04d1acb24a972180824da71d1",
  "f34dd524d2a7337d3b83ba28128eb704a1c7fe52b7684080bb689539ab7d3328",
  "91cd1daa301357f8be333939438eee2dc7d33468389a44a8747c0dcc709ac63b",
  "a57a201d652964c240a17e221bcda31c25499deeaccfb6c1490586c4ccaada6f",
  "cddca23a01b568bf0a29c0e3d404956d3279db5e2e1e62802a16688d7c70b1f9",
  "e45a7bb567a940c60ad39fcf5dba38450c8b92a013e1b90a644f3b172eef5913",
  "642bcac950dbe15ae0d36eb441f39e9b5bbcffb02164178fd79d45da094d5fa0",
  "03e5252ab35550875d426a29f46503e31c55f56d2aef2d98a69d8545bfd610ba",
  "801ad6b6c5868b2767aca4289853ef85d1a7094ed6c2ebf7bd31219f5607f417",
  "e35b4b4f4b971bc831bd1c6671c8dbf8701521086e5293f70f585431a774006f",
  "fda9e2642e9b1216daf713efa7041790efccbce0c8052395bd53ed66372f0fb5",
  "91fba89c55d6b3c63285fb1a871122d4e2020808648cd0472d36df66c0b3a49a",
  "ca7fffdea8c091cd2bcd03a65a4ba773ff70658b093dec632593d4798ed343ca",
  "413b94af3481c38997a34b8e9d4afca986f406196ae4cb307389ca240a8a3fc1",
  "987c7f857c8984cbf084c1324905aacb9d4c47c6991293b99d37a59199ab6662",
  "49252f21b6840aba3b2971b45f77ad93a5b47f31c80505a5933e31d626b8b412",
  "10af8bb7632270fa1e1f5389d56d7614fa60ddbbb8d708beb0abfd8b03897c49",
  "860ba5132f9452e98d8ab42f2e41849aec434083a76fb3473f0cc16d41997018",
  "2733478172351b47be400f264f86aa8d9e7eab73df0b7adce6bf8d49261136a6",
  "40073b512effc8023fcc5ca876774c95daeb51829eab4d77102d83efa49b673a",
  "a6f9ced78ce5bff970f271af97446cd7c4e14a7196e68b375488f4665c6e0727",
  "776be85b50a21f65e29183fc9b17c272f71fe206ac040db0dfafe7dbfa3548fe",
  "b44fa286bdb0622afc27659fb33e85a0fb5545d7e1f68df9cb7348014ccc9f5d",
  "7d4620f1e1281224b2b06834a47ddec0a8ae2ef497c5975c7fa08f26b68055f2",
  "07cacf1226dd9a45055d7d5cd85729d42f1bb494088874ce2c72dcbdb84ef300",
  "c1dee1f6bd2f0095ed5fe69535f75870ad83a42083c5b8ba68496051af405004",
  "439bb2527dd2a32104c403198e64f0c61cd0a47f7c5c6bf41ddc2bb3f0b34d83",
  "a35516fe568b9509a9b0ab351a2fddf97001ba6788d84f3b7deeb6f6ce113029",
  "c934822f0d18c596d58d72d234262c0b9a5c79a107e5f732a7fc9243b2eb4be1",
  "1e6df4e1f200103e655227abe7d33692b06a51b6d218e12ea23c14993432ecdf",
  "fca2341a174503e1962a5c12c73f3f3cef6643e4639e4274cd7bd9f7ee826d43",
  "8d689156d7c49af6f74d88eb9b41dde047e4810c25be313c48c5490c280d5171",
  "18647d4db5c8cb772bc717d1abd49d05afa69f384ae47decb57c85e53eeb1527",
  "3070b8023c63921a1cf232caf72a35d2738223d4ca078e98419ca69983a9e0e0",
  "80263a498004cbd030e672666f605d78c5f7a436197d80180d369f6f914cd75a",
  "917f858a741023cad938c891a7c23a77eb90e1f5bb81c884b265becc87ee2650",
  "284ed576724770d80cc38763843b63a14f3a9fa51bc1a4bf577b4ebb052d2617",
  "09e98a607b995beecb47ce647caffab0eec1833c61344adfa53d56533ee6c812",
  "2b485f1abe900031b7d0db1745af8b655393614e48576da05315d2f4990a14dc",
  "37570776db572cb2386153edcd8494a298346ad25fa9d4f1ca600035aa2e1062",
  "f45e952b069e49080f5f2e3711172a6bc1fb03920a06690fd42419421de4a541",
  "6de3f551e54543ea466158edbe6569006451c42650a766c826ae976130070051",
  "39c760428eaa5b5ec590ebfa0125d5882c9025aac7f502f2a1fae390e4fe989b",
  "982b43b4ee206a75c07ab50e780c9aba7b508484539ec7c23809c94f58f997ac",
  "5ae89fd46bbbf4d0362c94094e64a20cfccfeddaeca49ea75d0e41558938640a",
  "07024c9fd9957db9d5644419984fcee4f601021c4487b6771db008351bd86b91",
  "6e03facbe917d7c3a3b74b0866c6946f50d8e000e42d2ade8fd714802d2cd7d9",
  "d3e424d270eb5331e34e0f8397c5613a473ac7209bbb801fbfda85a90d722f77",
  "1bc16aef86396b2ac891f60fb6338f203dd8e60d89b47c59805c5c9139b12f11",
  "9d094f73c407d3a50526be1bc6aab740cb9f5dbd4d675b5be5c5375f245d3869",
  "b0dd1c606c46a71cb2b3890c9f0f2ae7970add1a412d50184e40a060325aa4c4",
  "574064ea5937f380c18e49a51431823e05aaf86efc9007bc28bd4695707ab62a",
  "99a911e392d059009ad4f1aa8f85230ef3a604c4f14c1f7c53a70c92f23853dc",
  "d33dd0a0b0bd118f37d2778286c0d6400df2bfbb78fc59f46fd56bd4ac46551b",
  "cff63b56349e566d987fda4abe58586649c3b00fe177768df14193caca3dabe3",
  "1b0c2bb64644220aa4310b156e9e98c5b3b59eff91c8a4291d88d5213954d21b",
  "04fd7a796feb5fb37997efe492d42fdf582144adf8be2326111880c644810e5c",
  "eef7f519ebdfa86ac533460444c0f23315ff6e5c999b9605a2df2a6af0eca9bd",
  "19aeb8b6cc4e856050bff846a7f4d3eab2cb32ca0adfe8fda59edb75cea8bd77",
  "a123a5b9e0a888913a9d75db7d63a8f03f93620b50f4767726679279aae1e487",
  "ab825ce691b8c105a62d379190b93109ad47df8970efb2580576b621e7867d1f",
  "bbd6223058f8107d6c316a91faa83ca53983141603509aa4e9e280917fdd3363",
  "9918390c6601c6259a8b6a0f6751d22c8aa7899d443f3e18786d04ecc5da59e9",
  "271c2715e786bbc91d1b5c45c5bed91c833927467195f13d8d9cd9dc5a4ea23a",
  "64118bbafec2fa9246ef5aa0f2ae1bb5f6bb601e2270b1a0795804425e38cb1a",
  "f8af0130e9175192e572707576a44f854ac21a8f0915aa0ef34143ffe277d54f",
  "d2f6c1caba1da94f4bea1bfa9941b2391c2ec13ba8805d85274222d315e7a659",
  "900764a4c709876e5a91f1041ff2a7250a3ccefaaba67ee52e88eee808d90c35",
  "694ca63d499ed90d14cb3f22187bf856914d7e6d7fad073497fc523085c15867",
  "984ae18991e06a81a8057b1765e4d2eab5f281189bd4e89f97a99b649185cb54",
  "8f22072a5adfe81fdb40933186c2d32e2ae2cd2b8d5182100310af2492bc8a1b",
  "71eebc8246bf67a53542157fa932be954d2cb2596f582a04d163e15ebdd90024",
  "5f4ff009fea83085f2e9ff50e78d9ad1ab7e2cd825df35839a372cd5e157817f",
  "ec8f0ac2ca2839962f31135f81b415e152d8beebba570c9444ffabc6239361d1",
  "65ae9bc1c7383954c101fb4ece758a03a4886bc675d2b77b6ac87d6a5deb897a",
  "953c5d61ebb3ed1f4fb3363878c465ce3d4b66beb77e79332fe7bfe4bd0aac1e",
  "61866bbc6b90d3944113fb90d0cf9c85b53f4ed182ce1b1d7b9c35f43f528626",
  "eff72489b1d8a9e4c08fe8f86a899f448db0cd3deb37cae5a30555d1b12661c9",
  "8f11033b832a470f16ae3353e3393f235ec26d3c6820b2be2076826d2c6f7a76",
  "357880ee33aa2fe799c1229735523a0c61ce3c74e158d5e6e056ab94f9de0012",
  "b343a1fd355ba5d927e3a46b3ace5fdeec82bcd8efe88f993234b819af32a914",
  "b5cbdda21a4e577dd1633b065f2596fd27efc9b6b10a8c94a9cbb3d89f90eb56",
  "0a3c4dcc612d8751700b65f347feb8d6216adc892669e9d5ea21c90ec3f02632",
  "3504cd0042d8fe50e5568a508ba5f3a7639825de0c763a08d82613468504433b",
  "4ea2cb5ad760e0552953ebf431721234ed4deb1556727c6a0532e38cfddceb32",
  "865d21832b2c4b65be243cfcf4e39e73f3484a7f407c9363984299f6a53529ba",
  "9e7dc78292cd9dd02d72c2956bc74a4e7fea4ebe46f9ef1d8bbeee23c0b2728c",
  "7b29ad2aaabc91d7843f0e73d81d6a1e973cba31ebfaadbe2a74f266ab4964c3",
  "8a33c87b1486ba8fd23609182938aeb1375449831ca71f2d770db704f9d5455c",
  "5361d8c2cf8b20301e76e58c6a7043ac44ddb6af1ca037aae25eb5d539899f66",
  "b4020ce582bbb83f48c9dde9c478bd6e676dcff8d9c5d520381806eee5b1567e",
  "dcba0cf3ae29c17560b7bf9c259d6a9d72b56fb70d2603471cdb1cfbd024fca2",
  "72907d6e36544762975bb04eb0de801c06df7729866e97d00d1000e47cf7a0f9",
  "514a491837b7e6bd1a575b82e19fa737d992fc6fb9b8165823c6a3dc9f399830",
  "96f6c11f0f8bb24b8c1f464ffb8f3db2546e63b3f7192eb784c52f839833bfcd",
  "a0a08cc4751aa6f2345fd69d2229425902f70cdb1c575e12e3a7d02350a731d1",
  "db691f134dccf3648d3caa357c5cfd0971a2dfd6b4de86975c9e623050a0c7c8",
  "9c4570266f0ce8d03e7aecb188e38fd2756d51b53fbfe435bfcc64b7a3c008c4",
  "236486a9ec36e2f9f7f2ba99737fb1cfe746469201fd292ea227519910f0e563",
  "4eff9693eaf5855d96b959d64a74182cefb486f0bfa06610b58746c4f2fbb3db",
  "777f9cc2ffca402ff49b4bc3abc5c053eb3abfa576e6078a2daeec0e70875c5f",
  "0f13879c6eb442f7fcb28140c1356783a99676e3809d0157bafd565de944e7f8",
  "022787e51d1ec8854a902a1fd3d22afda64dfcd87a5d4f3eac9d8f9849ed6dc1",
  "a7f51f1516cf92fe29f9893626478acb4247eec0a9627684ed0dc05c7d827f55",
  "6584dad20abb5211f66228a2627d06cfb48e0c435f4187ea02742fce78e7f808",
  "05563554da97e16fc762f4712292dac339070ce2f45fde5f462f3647cb87b330",
  "64aebd642968a4bccf8b5386019401519c59acb7ed747ad848cfabe87744cd2d",
  "609efaf7e757511ac49eec697b7865c3bad43288de1a209818e736c55b922f31",
  "0efd0b23dd7113173151d7996c9183dcee3091290fee6e061b497cfbf0754a9f",
  "0aba72d3a20b583cd8b0e01756f751279623744e595c20207dae8d9232b41e7c",
  "3de44140366d0601d211b9cd108f1a6fc7f6b526196a3696946604a203525651",
  "9b478b6dd3fa606805741409f30815940c410aac77da7fccf3cc880de014c2d6",
  "2a61c4725614cc25cfb22d0fc7e4173a29bea87917e8b213aa7c6c38604fb8f3",
  "c618fcb53858ccb0c1b51f9dc36ecd411dfe3aa417d351c24e7983e150c13cee",
  "0adc21c97d463a97d76b0d52a20f20af6a6762b689dfec1ab899fa8d910a66e9",
  "fb18db1eda6c67e4cfe317d1f3637134101ac70dc9df00844c43a14ce55aed95",
  "a2baac3eb4b2845a65f87073b439d89c478a63f9ee6e4c5c94192d31f0fd24b4",
  "136d55770290c53b8e1e3fa197a117261a94f32babad80760e93104b4be11cc6",
  "d2df823eceb4d3bb6dfe3dbda848092c3ac7f5d80f5526aa18956a3200585c10",
  "18f2f8055898c80018bd051919900389be9f31722da1796c25c0e68a5198a798",
  "2c4badc2b8a0f408065579e776cb04f8c860d9cb75ba5431b5492060074af39b",
  "ffd43348f76f166b511266ff04f83bed94c446bb36b0d34118442ac297dcc354",
  "53fee35756f8f42f69c4d89acf44dc0dffd6692f3177570c44a428f97d4e78ec",
  "8d8ee6c1777a8eb8f158a513e24e843e44dada59c3cff3a819ba3889a413d0f8",
  "d626b3d569f854d939cc6ca5aa5d32b3dfb9f9202a0eaf6c025e8939e233a0c0",
  "5b0b8ac90ffda6b19afad39c5b51342916adada8ccd066bc1db664725e37b9b6",
  "2a10f44a261c0ddb8c9694b6b735ddab6b353f4bd79da324ac7a12f99e715aa5",
  "8f08648aa735938a7fc7c9af1e916bf656e6b59ab683ef03c04a409a54613091",
  "cd9dfd9f0e8e28bd2da70306ac59bd5f02249153d35b1bf5bda674ddb8c736a0",
  "2f197b7134497daf575183514cf7d202b6a39f3903633c99046174df89986cdf",
  "732845a4267966ff28324f9778fb6569f38cc41f26a4c5bfd050cc72d1ba9506",
  "a61db18d4b602254b2129864e8f84cabecbe5e7813c90208fd566f4417e66a52",
  "c316521c46c4b321b0f74cd730006bc448b8f2449fbaf1e284f14454a068dbfc",
  "64c803f6dd7b2ee67bdad493038ccf401697f4868a2039c385a1c2433370b41c",
  "f1fee55960a2e14b9b5badf21704f69eee614c819e8c0d0770e2b35395ee7231",
  "ed61d83de00985641442604cbd63073f2862bb94ea761289e4039f9d04702986",
  "256cf56b78c371bfb1eb8c87980ab2512bc92da7ac0d514bfcee2c640fbdf48e",
  "b130874cf7ff8c3ac95b5acb3005e200058ea08c9297cd3e27337f7d4927acec",
  "906a73966511c5a138cd3c751d50c84f6065922fa9934c04824ec854e57cbad2",
  "231a7e44b6bfe050c6f28a6be1692c778e0d20e7b1822cca58a9e6c7e15c45a2",
  "24e89694ac180926ca32b1e4d5842f1bd1e43dbbf0c68905a80bcf967359533c",
  "dfd7d7f18f93a9104ea60806b774094d6f4adb4e6f8077552654f48df046342d",
  "8a2843839d01d20ff5ffc46ac9f7e46840150af6eef7054e5f1b4599b52c8d8b",
  "f082068976f870cebe4c5b09772bfb1a60b4fc9dd3211f476e2b6bac469dcee4",
  "06cffa666b87632debebd5a585909ce86774fe5d04ac1e0f874e7cf2a2e694eb",
  "67cd753002267b0e69eee54587665bc81e4c492c42e10ebfa7773c4940a84da2",
  "2f9c3a36ae7b8f2be50532e8aebb658fb62733e864ef129c1717c0e0c4b1e1c3",
  "ffdf11c837d6608daf1fa5533238a100721feaf481e5b1995ed572a009a550eb",
  "db9318d803335a5ed1571d8b32d66f1497d07500c97496203f70c01d6c1c1581",
  "223dad6bd832e0aa920f9e9f44f6e24ff1250393a5c1cd978b638f1d408e9aeb",
  "22c4235b641409f2de4de12d5d2e2d6799ae39fd39c1919b4697e0f88c771644",
  "eb31b03a1795b2432ca5ed1801f43f09c6a930b33e855b84036c46c0793e8588",
  "bdad182f12b3100dd83104e6d903c83b23ea5ed049a3c801e81a26b66f362501",
  "0fb2dbdb372200814976d7d9ee7a6be1eb5ec4f91841463da463f9d90189add4",
  "3dbb417c0c302b3c20044f6095558438762aa8beb2a719c0b250cc0bd5cfc475",
  "18d2742cd3fbd8d73cb9e57984d30da873939d7d4092052ca01c20c2f08f8e3c",
  "e2dfaba18eb716dc021fb3ed0a6aafd69b0cfb6097e6518f48fe73a1b3357afe",
  "d86adf26867b5b55f38332a736f81f3f6e9108d60c3d486fcd417bb6bad62788",
  "4601fe716879452e90bcefbd9f08957f869a1f2da7e692e812ba270e6906f306",
  "d25d56ebc5b43dcb12b4c4e302eb3c6917d247cb4c69ebd4d408b8096ed8946a",
  "03f00d0ff86c32345493a3bd0d1220b90cee9d345f56f18a0c8072c0188a2052",
  "37b17d79f136f9fea41e0d34e3e1f732e1e5592f3dae8303ef5b4768c37318d9",
  "12aa44d793f8b51fe6c2a6186920cc0ec63cd401d9002845a1ccca8b87651cf3",
  "bc1fc1a22aa6f8db76d2a52c11987e928106b8c7de17d430660ce8b7146e24b7",
  "c491041fe3da3b4a4bb0b4229d739069550911a0ad146db7ca51bc649f51f4af",
  "75f9fbce432c4e8baa4789a3bdf783bbd84fafa27f87436929f18b40ca66a728",
  "efcc5ddcaef5f018b7c06e1db5a9c0b622ac55c2d35970007424f51780b9ac59",
  "d19745feaf213afc95f2a2eae41e9273a78394416a769b21d345c2888d523de6",
  "c138ca965072ee2cc28aa468fe4afc57bd579d4c7d13f8519bf96d8dffdc2705",
  "92ec96af6f2e3c5d6d7df0c829f6fbe51d1228bfcc348f615619c81b3396cbac",
  "f809925b05d1c8d428944c7337e75987650bff954ce2e1ea0d0950cb821a56f3",
  "373dc17feb0e916575cfb19da67e8f5487960d10bf85ba1bd4ce2ae291dcbbb2",
  "5faf26c25a9912efb62feda0481aff160d3dcdb820ad3e8e5b79567dc09a45d6",
  "1f0f90ae1c4d39b15c133364f19d2575de02408b785188f7b214d5ba703260a7",
  "06f63609254a4a96e189386b2f7d5c6fec24f513a0698a742c768ad6a073b090",
  "2ef9e4bae6baf8acff1e1dc4d95341e43e805c84cf295eecc24bcbca6bbaba8e",
  "6a77c29addfdf5dd6873d6fb5154ec6302f77cece7e45373b53c85fd42685976",
  "e91889b619ae759e1a88b1cb4e79b053080953f135299d28a35d99e61dfb29c8",
  "5cb84550f4e16c713b763c7b9c59c54e6f8a99c0d81d5541607405f4013e8adf",
  "20ef899917aae1780ae9161527d1ea9feecab9e55cbca0d84fd2e06f593782fb",
  "364a44cf70b96f6826ef5eb3d7e64f2c0860011dfd28da9a6ad1101d6a5ee1a6",
  "5f3cecf61112c3c93be9bea5f775f5298c8fd683a10a3cec2306b034e75580b9",
  "3b4b5994b1988c5c51af5047e8dede976fea6015417b854daae40c5c879be207",
  "8d41b0e905ae3330f44d8a627e1fe079ef5eee03745b727d11bbfc49e3abc751",
  "ba29a66f7f1720769d9d104426621da8db5e6281cc2b3c94860d973add81726f",
  "8172b859d3cfdb752ba8acc8c0c861b7f67008568f114b0abd11537b4c6a0e62",
  "63ec616a7a4f1a55c7f5a4dd218fb4503a37aff0faf291fdd70912c9a01aec7c",
  "9590717827e4d9178b5269b5e907f87d53c2781e2348e2bf66dd1290262e5087",
  "ea33da9a0e4cdac5725d554a9540b037e94403e5054b7d2016c07d6e3d613843",
  "b337a7b237fdbee13d5e0b68f7031ffc33ad5c6b5b348bc22c002a4cbbcdfc4d",
  "bc9bcabbedbdcb727483ebcac5255f3f0e7c61778aba6fcab2e0daf761744ba5",
  "8cb63dd575a90f4788334f72cf4b3f1f4c1a36a9cf267eb1bb46991b6c33a0e3",
  "1268eda87fdce3d2787e7e942292cac3d85ae78c909b010fdfe789216d73e421",
  "02ba24085fdb3cf71dd097885fd11cc5944c150d9b9ba5e1b478f71b3ec714b3",
  "fa1d4eb16efdb86502a5d6ad5022189adfbe47c652e7701c51247f27467e5e5a",
  "18c13ac618332203b2e05b572e472f4d8df4aa7c31c2094d1e7b724c1daabcd4",
  "3fcccd16ad2486aa0178461e112c0104ce2b408050ad412dd4db3b6ff2a00076",
  "7bc4b60e19f6469e66332e54b080fc718d63bb2881b1bd5b8613133b69d6266b",
  "70deeb055bfa1b53610711756c84dd1f53739b084cbebae80cf7dfc84aa1094a",
  "b53e2e751d53e89550566c687befd8614e9d3a46d05d0e84c8fa08b2a92517ca",
  "af28550601765ecf517433756adaeb3938651cf5e012a1e2890f0cf53cdae4c7",
  "ebe89d07a4c031be960d245c59d53898535c9c5495b3e9c0f40f5ec5a54c80b4",
  "915b71695bc20eb0e5266ea4a4cf4b3aec3fbea77b4e173876129b726415cf69",
  "5537275448b1cf7a129847622e10b20aa4e5191daa41cedf034848f5b3789d02",
  "2b5266380fa294eb3b17cbf1602b91e353db0f342e21e35c2a4035c3e19dc5ba",
  "6fc1148be59f167c85ec52d42b3d6ccfd8c53550b1eac0babfcfb41221224179",
  "ab945e96df17c6252855d04ed2cfb79dbcccd0bf6b2ec49f9bdbf0936ab829a6",
  "e033fb8883ad316ccb5053f952b320a008c6a66651eeee436134a6f47cb1bb53",
  "c78e5e2b23bd5a696e1d20889f16881e3c70cfdf3ef8034c9cca607bfa878377",
  "45c5b892613285325bee7020228387e559a27c345b0ac554edaf7ea40dd8ae32",
  "5b52379132dd256a9bfe3f90b2666b4cc84419366bc0e8061b305da07971d430",
  "907fe9ed555dfd124c8fc2aa896af9a08764726451e3e88765a8c8e8e7e26e32",
  "eb2c1f9bc07637955caf7b30b4d65449573e6bc0421a5f7b438c9b505bdf27a2",
  "ed0668862f9a4a9b6cd9996fcae291096a214df4c3b69c78328ac96585780ecf",
  "0e0af10bb0c50bbb016bdab670876ba59dc0d1f6db1e5331e06bffe5b6c3183a",
  "7d1108885a9948773d2af8d531189e131141185acc27051276db1018a1c7dde0",
  "2949ee30ee54abd7f4db985613f1cf5c1fe6b4b8503a5f97547517956234c87e",
  "b2c6e68a9685108dbc779ef7590469169029420ddfceb6d2515809f1defb04d6",
  "e8d4e156f0776d894da9710a802bfbd07bb95199f0814d254367e14cea882166",
  "435217b73c03b49761b0f783edffc40e403f882eb10bdcee87cd3a7139ab3e32",
  "6bae80dd58f7c402c31dafa132cfbfeb23f9a68242b8270076382a250a2b076c",
  "c30fc4577380c91d78a3c5c1f6439a6741bf3d3c11f4b3a72d8aedc7b9609419",
  "7e3a69eafd7947c5f46d094c54f569fceb6083ed36420cb944fe380213f17ab3",
  "3c42a5a059d3490f49454f7c4110ada979984780a9baae8a674cfb9961ad87a9",
  "f3452839332752e37f84afe0bc9f8b733e5291f5e2f2183186470f3d2c037b73",
  "a7e6b11794ae7a36434d54b14bd37ba3e2cc38e55744e0f030f787436f58916e",
  "40b42dc66876cc6c46db657c833691fb82cb8f976548af8b642e0300266743b9",
  "44be78cafc5451a5942de9b30727f2d99ba13064521fb5d0d37c67a2dcb4885e",
  "82a38bc4aada3c765012dba0e54dbf36412eda73a937955ba111f2e6b57fcff3",
  "d1293e1fa059aff43f2706c0bbc8b0918e6be4a63d24d48dd52a44d64782de08",
  "50dea1663408ed4c04dc6123c1aebf7ac04d90b301faf4a08d294f696b712945",
  "c7f6c629abb59e83dc7eba3f4d95249453fdeb3c85c39a8746f2560bee2fbceb",
  "a063e04ad7ed974e43ebbfc1fe2caedc9dc4211657c42c735851539eac0c3f41",
  "438d54493330235d85042a8d0a8d7a8281cdac965af6a5f11c92bd3446bc722d",
  "31d31f747df00135ea5dadcca679c24af87857b2fe1f4efaaf48e32b60ddadf8",
  "bf10438ad18afe021ab3c51a2dc14d142c47cb8ffaa5db4783bb5469f68004a1",
  "d2e6e1d6ecb41bad0abcdb109b1fdee0daf969b93f990db384120fb887d99ff2",
  "be0d3ee8614caa17b28af73b01b53eb25f7bd4b53d4b58a6a30e42519f27e3dc",
  "99f355ed38af25e81c9daee76709daca47545f22a73607892af654cfa0755251",
  "937a2c39080f7483770dd99991a96df7726cc02713cae0eb807461a3550b61c9",
  "ada4551167c3ce445240bee9a751ad616b2a034a60cbce8778f2935047340d2e",
  "e8adb80059050eebc3284d364a90ce868057f3adf617bded08c620354a9038b2",
  "dda111d12e898e50a81edff44d4e5fcd4adb7bb5a1d92c5a044f065d60e2ca82",
  "599ecba0c32430d3ab739f84f2ce137d9a1e190d8d91d4a00a8cdca22be1ad4d",
  "b519a4b010cfa4529513a5606f922370435a4ee45ccb483e2992e97b6c09f90c",
  "2910ffc0caa0f9a814d2ac3c1f22c8fc13c8f9bad8f4a3ef8f2decc1dcdd119a",
  "9d0910b0547b6f18f4d14fa05948416465c788481732da68f4faa00e3bde976a",
  "bb2774abfe1e1f9439987d54ab70ab7752142262f56b030afc2c2af59d30ed20",
  "b2d0f7b57f5e76d368611aa3f60ebe09ff5743e8d70da5174abaa7d58b6d5caa",
  "094a89b59fa256df43748c86a4c7f068630379a39b99c2d0407206624522c245",
  "33bb161e6b0874a9ecd61e3091fe15fa664ce1e646135bef757007baa161bbbe",
  "53dddab72db4c48b99a9584353b317144c05606dcaeb01bbc6ef8b2de9dbbc14",
  "727e453c53e30d33142847b18654b42b6235eb16cbed7c86c51ec508d56fd289",
  "40e9b45245023281ac9000293caef7e855d907b662c5f4dbafeda0a66138606f",
  "481d04d74a640e2c932f981daeda42f07b69d947d824c70a7afafad958328eb0",
  "b1f38513d2acf3d28af783e211fd7dc8d139a0ae9bb82cc6485ee24813784879",
  "694c065e55b85bbf8924e767fcba972326c228a41074274e433ca84aeb650078",
  "10fe70ed52e4115096a639e2ab49a79e33123bcef9b3aae7ae57f5df0502fe19",
  "c1b9811705963249278c871b3f787441c280855e35711f3f835c2f0a448bc255",
  "0c16f2f517fee9ca94d0ccd01f3dd9d4c8f9618386d00156c723bc4c42e8e02b",
  "e6b60104cf1920e34707634c53963fd6326973babf75e777a15657061064d4a1",
  "d764ae08940191f13936f19e8ed766e6654765eab9d8dadeacb7f53b04fa512f",
  "a8bfb17a73e26077e008a045e860b6a6e882d878988b2bd15de01442aff055da",
  "db19fd7d12fecd89ccd39cee220a4eb582bd03155ce30c74deb1f1ab11d9d392",
  "e6a075e532d61e2d34acf1cbce82f1f05d516882c63dd50e029dcc43c9a93dd4",
  "4d37e277f9847ac9bcef2e14d0809a894d2aeffbe9f54b12264757687298d8f1",
  "e3494985ddb642355523b6648bad7690223823022340a72deb80dd59329b39fd",
  "1880df019b70ec2ad1bc9871981384613288999ca3b994ac5b86d4547b30cbc5",
  "94b52381a26fe3ba9f04ab9c3f7f21023a06241af603cd70b33b9be3e1afb315",
  "04c766c8e89f6b756f3341ffd966e46ba45afd7adc8268f201260f14e92cd7b0",
  "3f5ed703ff94e0c9ed1209ee39e000bfbac772fe9b351ce2485aacee462f7f5e",
  "c619b99e290d1847a021f808bfa80208699237b0f91f68a5dec05fd61562acd5",
  "e5faf87b69aa45165894efb43cd9bcb21e9373e94402bdfa89b7aad3780c5b70",
  "f2c0c33f25a25cdc4340c6f2b83df333b6e36d2622d727fd68045d4e704313a7",
  "efaa4e8ed907fffc302ce649b65a71479c8b867206257d3a0642208667276e0e",
  "46aeb04b09fd157f245b25a61b2739abd58cbb77bf62ead8606d6f3946d28e3b",
  "27f69bc2dea9a943f0c13765bcb18b95a602005c359b04a3b75a78bbf2244e99",
  "f0dce4cb2ea2a3de71f5b11e5674c78b72055f8ba13c2e5a72e6b7ec67e828b5",
  "a2a4f2f6a2789e42593a9ebbcec4c54b9cfd7b24f9f87c11ba4d309cd0dca41d",
  "f4a70c2af6a4436c5fd261f83e70e123bebc0d55c82bbf893c5496f1e22d6ada",
  "1695e82b973d9fe8000efb83eb478e7edb26c2ac2f140cb06c25f89b553387a2",
  "f6835b1cf6fd5616fe88c40cd8a8b37332d6766665e932561202b6df07b9563c"
 ],
 "dev_sha256": "792e8b9e2fd48ad5c5faa4ba9c7d23a76929cfed7bbb39186a1e26ad08889a7f",
 "dev_line_sha256": [
  "f504541cd4befea67741b138e51114de5dfd14c97931f218b1407353b1b5f35b",
  "19efae1437a5e571ad24fab3aff731477910a9cbad365b3c294ec83aee2ffcd6",
  "617f93372e1cde61d624fc041f652917873f8c894ecc5ff4a745f23fe785a1c0",
  "a890730afa9e36eb415b91e93837bcdacc1b38c890af84b6db67b89b8c6b65f1",
  "1147062c665deb416e7ef39404efdc40042038cee04266bcf820306b4faeeeaa",
  "c55ade602f23ca4c3ea4c54e29190d56593a9e522efe78d40e04cf5d7fe2d930",
  "606b626f54c3ebea4803081949bd1097abdee43eed282e154d5de3b1aab4e907",
  "0bf42eeb8b3d9fc143d92f95fa692517b7d0db85aed7537325cd811ed7f09f0d",
  "522d32b7119862bd1f79a848dcc03aae28e05726158b328352e79816e9173d8e",
  "c051fead0343d25f1afe455f4a38692e92020970aefe2c5c40ed6f83d58630bb",
  "56218f2d4444eea1a160aef1cab0e6ba7a16412bb07948b177676458f4d42835",
  "834273e29c1e1e893a9dce167bf947600a18ad28a6cf2e2ed32c2e91810cf6dc",
  "e4dac6400b35180ef2071591b9f34cdee95369d9c5d31c22fc61a9a75abbfe66",
  "edc2af93b3c7f8f40e113511a30000fe2d4a1c148acb406ba67b14558603eb42",
  "32e4cd6678d68cac60aa1e00f5fa5937eaee06cafe75857bdfcab86282a2e8d8",
  "594bc3f4978baccf4d3b48fd4529229e8157e1f7a49ad70f1d088b246c74ef2f",
  "28aa1c3737cb9442d0b0376f50ee8e457910b7c18da5a5f3a4d85392e022ed23",
  "c79addbd231cdf645aa467162f76fa07f19b5d8e2db9c672c13714cd8929e70e",
  "6a6ed40bb4a053220ac0397d0ca8702ca3866eaf5a99f23d48d39207b86f665b",
  "40ce9272da7197022133a9dba1799733db842da0859d88d2bbaf3b1fbbf560c5",
  "6fe5aeba6849cf24dea90ed20641c0957ce7e67f2364d93b3b0cfeddcb9103b3",
  "fdf98080e5dee376799cd958cfc521c259bbc0be557e8a80ea46d4baab29570f",
  "6d50ab2340637c481376ddd88ded90d8a19a407e2bfecb4a7fbb1615f7f6d806",
  "3f4371c947e5f57dc488e33b7edaffa2182ed8c9490e881a13aa134b3e7b2811",
  "b9077c2d68efd9dbfbe4de00d9e79de21d8170c4ecf2ad7e3f1fcb2b41ce774a",
  "a5bed05974114ba08a8b48ecc1e819b55d11ce2a610e4ca5d77ba424805f1627",
  "86758d0c69e9cf631ba9c1aa5b60524da9994dee49502c901c8f6f4120d05ff7",
  "33db0ba4dc2e3cd00cc02d02dbacec27b32fcdda1e287a19ea06901fda3b9bb1",
  "1e3d2514c0b043493e49ca788645636e6fd8df2143de4fa85f2498923fc3d742",
  "6d88fbaba1a300973801eee13b87069a1f904234b9bbc4bec6804b524078915a",
  "11f48bf5044a202143f59e267b113a09684fdb8ef5da2381330ff3eec0faf353",
  "65b600fa51846cce3845c384ed2d2c81b6383cc0965c8512e20f5d92133b07ba",
  "184fd0334418a25e3811449ad451b689e94e84aca9a93de7c429bad0f589a24a",
  "594d63c6c0441947034affddf411c05c5a43ab4ddffdc4d84e029e8d2708469e",
  "7beab542b15a18b6cab187a13114521b13afa8a4e27dff2e50405c04f56f7840",
  "596aa41a52581cf4583dc310760dfb759b021fac5e13e7360d31674413172ebf",
  "b797c66a754ba342b415b6d994d69eed7047fda2b4e9a8e63b2118fe9c385eb9",
  "a23936b119338767897ef920928e6116208459863ba9db59efabcb780a6a3231",
  "6a0b0827dbb3b528f9f67149e57e1082a5ad37c8b17999aaa406736d7db9fb9f",
  "a10b2e05f93b28c2f742280bc2d72605069550d35c6c2cb28788994490f0011d",
  "b3977517cac8406d79a40905570ece455b268211f6dd8fb8c35e8e81f35528bc",
  "b6ec39aa8cb679b6ce2e3763b64457c7ee0d96416a832842bc29c27dd40efb9e",
  "25a4d6d59207b86814861eb0a453f5f810f9cdc97647fc6fb9309bd7e253ff2b",
  "51d7e20a13003df8b723faa933473137968d476e7893224ebbc304261e00c91e",
  "c6147e6bcd44062c2b4f9fbcfbc9d8ab3727c8bbca06d3c9318d2a07d1f7e684",
  "c77f17626aa05ef5750fb99bb2370b86f477b6e5fe0d9d27c454c9a97a2edb46",
  "2411c3b89baad19f54c65c6cb97cd05e03384cd9dc3de497629462d82a3398d1",
  "fc3e7eaceb3410c81cd63e8ab578bb0d439a8b98370ddbafaa8b3fb2bcbde6bc",
  "7bd8e79cc4996e416776136781fc8333329d2586d7cb1ef97748e890a8c0edbe",
  "a22a201177a34fdf6552bd1e1030c2023bc045b45835b298902f406fcaca0c1d",
  "763185085bae374185b86ee5869f1e7abd8056e15966166151619d01e15766d6",
  "b8656523eccfd9e6503da321759b931f919f329b05b9f8fb509d6da0d2954d3f",
  "7b4689856a464bee949fb38244972d010494098284b980fd80e2982fccb9f947",
  "23b33defe4eff207e0eb2f0c78b476b580724be5f73467d3503600a75fc9cf6a",
  "7f566eb28eaa863cf09976765e5edb8db03254406738c7fe61d8e0bf545f8c37",
  "e8c90d6b3ea454e2219a4cdb30ad1f9e2e81be76f9619f10f5c353a0c818f501",
  "e41067dd02b48e78d43d0e59a589ea32171a9d1a0d2634c5391e378fab23df25",
  "868bc1f163e4e07ba1dfcfe5f0b1124496945ccff1d6f9ff42026e17b1c9b459"
 ],
 "stress_sha256": "82dfe4224915b0a6dca44bb96e793dabfd5091f73c3191b601640aa241b56be5",
 "stress_log_sha256": "b059cb8531b740b6f3948dc8e02615ce08b1869957710b6c9546a96d86adbb19",
 "qualifying_iteration": 0,
 "dev_iter_sha256": "3f3a700975112959425154bd9e343ac57476ebcfbba2e37455529ab1776fc7d2",
 "commit": "ef9d90bf8f2216b2daee0f052308e188211c3007"
}
```
