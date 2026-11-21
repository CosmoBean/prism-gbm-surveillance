# Results: analyses that needed the restored data (revision 2026-11-13)

Plan: [REVISION_DATA_PLAN.md](REVISION_DATA_PLAN.md) (commit 0df79e9, before any run). Aggregate numbers only.
Patient-level files stay under `outputs/` (git-ignored). UCSF-ALPTDG was not on disk (the download link expired on
2026-11-01), so every result here is MU and LUMIERE only.

## R0. Reproduction (passed)
Data restored 2026-11-13: LUMIERE from figshare (Imaging-v202211.zip and the CSVs), the processed MU reference release
from Hugging Face, Qwen3.8-27B at revision 1d4bf0f2, vLLM 0.31.0 in `/project/community/sbandred/envs/prism-llm`.
Rebuilt: MU radiomics (596 scans), LUMIERE cohort, detection, reliability card table, system records
(`PRISM_SKIP_UCSF=1`).
- `system/checks.csv`: all pass. MU grade 4 intended use AUC clinical-history 0.822, imaging 0.709, combined 0.821; all
  scans 0.845 / 0.712; all gliomas 0.814; LUMIERE clinical-history 0.689, combined 0.773, imaging (all scans) 0.655.
  Out-of-fold and locked scores equal the published ones to 1e-16.
- Card checks: all pass (MU 0.845 / 0.712, LUMIERE 0.689 / 0.655 / 0.773).
- Registered conformal coverage (combined, alpha 0.2) reproduces: MU 0.823, LUMIERE 0.871; Table tab:hides error
  rates reproduce (MU 37% / 22%, LUMIERE 48% / 20%).
- Secondary negatives (MU) 0.807 reproduces.

## R1. Conformal sets from the displayed model (cross-validated calibration)
`prism/analyses/revision_data.py`. Check before evaluation: the displayed scores equal the system's (max deviation 0).
Combined score, alpha 0.2 (80% sets):

| cohort | method | coverage | progression | no progression | both outcomes | error where both | error other |
|---|---|---|---|---|---|---|---|
| MU (146 scans) | registered: split, refitted on 70% | 0.823 | 0.819 | 0.826 | 25% | 37% | 22% |
| MU | cross-conformal, displayed model | 0.800 | 0.755 | 0.833 | 14% | 40% | 23% |
| LUMIERE (178) | registered: split, refitted on 70% | 0.871 | 0.767 | 0.943 | 38% | 48% | 20% |
| LUMIERE | cross-conformal, displayed model | 0.787 | 0.685 | 0.857 | 20% | 43% | 27% |

Errors: the combined score's error when every scan above the cohort median is called progression.
AUC of the score that forms the set: registered MU 0.800 (refitted) vs 0.821 (displayed); LUMIERE 0.776 vs 0.773.
No set was empty. Clinical-history and imaging models (alpha 0.2, cross-conformal): MU coverage 0.801 and 0.836,
LUMIERE 0.758 and 0.736.

**Adoption rule (fixed in the plan): met** (MU 0.800 >= 0.78, LUMIERE 0.787 >= 0.75). The paper describes the
displayed-model sets as the confidence statement and keeps the registered split sets as the planned result.
Reading: the sets now come from the score the clinician sees. They are sharper (both outcomes in 14% and 20% of scans
instead of 25% and 38%) and coverage sits at the nominal 80% at MU and just below it at LUMIERE, where progression
scans are covered less often (0.69). Correction to the plan's wording: the plan called this cross-conformal prediction with a 1 - 2 alpha
guarantee. What was run applies a threshold from held-out scores to the model fitted on all training rows, which is
not Vovk's cross-conformal predictor or CV+ (Barber et al. 2021) and has no finite-sample guarantee. It is judged by
its observed coverage only, which is what the adoption rule did.

## R2. Reliability card without the patient it describes
For every scan, the situation's counts, tier and AUCs recomputed without any scan of its patient.

| cohort | card | tested | few cases | not tested | any flag | AUC no flag | tier changed |
|---|---|---|---|---|---|---|---|
| MU (146) | registered | 37.0% | 63.0% | 0% | 91.2% | 0.646 | |
| MU | leave one patient out | 37.0% | 62.3% | 0.7% | 91.2% | 0.646 | 1 scan (few cases to not tested) |
| LUMIERE (178) | registered | 89.3% | 10.7% | 0% | 93.3% | (1.000, few scans) | |
| LUMIERE | leave one patient out | 89.3% | 10.7% | 0% | 93.3% | | 0 scans |

No scan moved between tested and few cases. The self-count did not change any tier that a flag depends on; the only
change is one MU scan, alone in its situation, that becomes not tested. The leave-one-patient-out card is the version
to deploy; its results are the same as the registered card's.

## R4. Reports with the new model names (v3.2)
`prism/analyses/report_v3_2.py`; facts `facts_v3_2.py`, prompt v3.5 `prompts_v3_2.py`, adapter `check_v3_2` to the frozen
checker (blob 26d6637a, unchanged). Development sets redone by the v3 and v3.1 rules: MU 20 patients (32 records),
LUMIERE 10 patients (16 records); evaluation MU 114, LUMIERE 162, the same counts as v3.1.
- Development: v3.2 passed 48/48 at the first run; no prompt iteration was used (two allowed).
- Frozen 2026-11-13T19:07:18Z before the evaluation requests: `facts_v3_2.py 52f373ed`, `prompts_v3_2.py 7888cf66`;
  `facts_v3_1.py 7cea11ae` and `prompts_v3_1.py 031605fb` equal the v3.1 freeze.
- Same run, also regenerated: v3.1 (the frozen version) on the same records, as a reproduction after the reset.

| version | MU pass (Wilson 95% CI) | LUMIERE pass | tier stated where required | median words | Flesch reading ease | old names used |
|---|---|---|---|---|---|---|
| v3.1 (reproduction) | 114/114 (0.97-1.00) | 162/162 (0.98-1.00) | 90/90 | 309 | 52.0 | 276/276 reports |
| v3.2 (new names) | 114/114 (0.97-1.00) | 162/162 (0.98-1.00) | 90/90 | 308 | 48.5 | 0 |
| template (R3) | 114/114 | 162/162 | 90/90 | 413 | 39.4 | 0 |

S5 (pass rate at least 0.95 in each cohort) met by v3.2 at MU and LUMIERE. No failure in any category; no report was
truncated. v3.1 reproduces its published MU and LUMIERE results (114/114, 162/162, 71/71 and 19/19 tiers).

## R3. Template baseline
A deterministic template in the v3.2 vocabulary, one fixed sentence per line a-j of the prompt, filled from the facts
view with values copied unchanged (`report_v3_2.template_claims`). The unit-test template of the plan covered only the
synthetic records' fields, so a template over every facts field was written instead; it was fixed on the development
records (48/48 pass at the first run) and committed (3f36a77) before it was applied to the evaluation records.
Result (table above): the template also passes the checker on every record, by construction. The language model's
reports are 25% shorter (median 308 against 413 words), cite slightly fewer fields (24 against 27) and score higher on
reading ease (48.5 against 39.4; higher is easier). These are the only measured differences. Whether a clinician
reads either more accurately or faster is not tested.
