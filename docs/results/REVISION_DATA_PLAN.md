# Plan: analyses that need the restored data (revision 2026-11-13)

Written 2026-11-13, before any run, after LUMIERE and the report model were downloaded again. Answers the limits the
overnight reviewers left open (REVISION_2026-11-13.md): the conformal set comes from a refitted model, the card counts
the scan it describes, there is no template baseline, and the reports use the old model names.

UCSF-ALPTDG is not available (the download link expired on 2026-11-01). Every analysis below runs on MU and LUMIERE;
UCSF is added when the data is restored, with the same code and no change to this plan.

All four analyses are sensitivity analyses of the frozen system (SYSTEM_PLAN.md, e7cba80; REPORT_V3_1_PLAN.md). They
do not replace the registered results, which stay in the paper as they are.

## R0. Reproduce before changing anything
Rebuild MU and LUMIERE outputs (`prism mu`, `prism lumiere`, `prism measurements`, `prism radiomics`, detection,
reliability card, system). Pass rule: `checks.csv` all pass for MU and LUMIERE, and the MU and LUMIERE AUCs in
`system.REF` reproduce to 0.001. If not, stop and report the difference; nothing below runs on unreproduced scores.

## R1. Conformal sets from the displayed model (cross-conformal)
Now: the set comes from a model refitted on 70% of the training patients and calibrated on the other 30%.
New: the set is formed from the displayed score itself. Calibration scores are out-of-fold predictions of the same
model specification, from fivefold cross validation grouped by patient over the training rows (seed as now: MU
10 x repeat + fold inside each outer training fold; external: seed 0 on all MU training rows). The threshold is
`conformal.threshold` on those scores (patient weights as now); the set uses the displayed probability.
This is cross-conformal prediction (Vovk 2015); its guarantee is weaker than split conformal (1 - 2 alpha in the
worst case), and this is stated.
Outputs per cohort at alpha 0.2: coverage overall and by outcome, share of two-outcome sets, share of empty sets,
next to the registered split sets.
Adoption rule, fixed now: the paper describes the displayed-model sets as the confidence statement if MU coverage
(intended use) is at least 0.78 and LUMIERE coverage is at least 0.75; otherwise the registered split sets stay and
R1 is reported as a sensitivity analysis. In both cases the registered numbers stay in the paper.

## R2. Reliability card without the patient it describes
Now: a scan's situation counts and AUCs include that scan and its patient's other scans.
New: for every scan, the counts, tier and AUCs of its situation are recomputed without any scan of its patient
(leave one patient out). AUC point estimates only (no per-scan bootstrap).
Outputs per cohort: scans whose tier changes (tested to few cases and back), share of scans in tested situations,
the share flagged by any flag, and the AUC of the combined score where no flag is raised, next to the registered card.
No adoption rule: the paper reports both; the leave-one-patient-out card is the version the text recommends for use.

## R3. Template baseline for the reports
Each real record also gets a deterministic template report: one fixed sentence per required fact, filled from the
facts view (the unit-test template `tests/test_report_v3.good_claims`, volume label as in v3.1, LUMIERE rater
sentence added). Checked by the frozen checker (`check(..., card=True)`).
Outputs per cohort: pass rate, median words, median distinct fields cited, Flesch reading ease, next to the v3.1
reports of the same records. No claim of usefulness is made from these numbers; they show what the language model
adds or costs over a template on measurable properties only.

## R4. Reports with the new model names (v3.2)
Change from v3.1, and nothing else: the names shown to the language model ("timeline pathway" becomes
"clinical-history model", "image pathway" becomes "imaging model", "pathway" becomes "model") in the facts labels
and the prompt. Record keys are renamed (`pathway.timeline.*` becomes `model.clinical_history.*`, and so on).
The frozen checker (blob 26d6637a) is not edited. A thin adapter maps the new keys and the new names back to the v3.1
vocabulary before calling it, so every v3.1 rule runs unchanged. The adapter is unit tested, and the checker mutation
test (CHECKER_MUTATION.md) is rerun through it; it must give the same counts as before.
Writer and serving as v3.1: Qwen3.8-27B at revision 1d4bf0f2, vLLM 0.31.0, bf16, one H100, greedy, seed 0. At most
two prompt iterations, on the v3.1 development patients only (MU 20, LUMIERE 10, chosen as in REPORT_V3_1_PLAN.md
section 2); then the facts and prompt are frozen (git blob hashes recorded) and the v3.1 evaluation records (MU 114,
LUMIERE 162) are generated once.
Primary outcome as v3.1: the share of reports that pass the checker, with the v3.1 rule (S5 at least 0.95 in each
cohort, with Wilson 95% intervals). Also: no report uses the words timeline or pathway.

## What changes in the paper
R1 to R4 are reported as sensitivity analyses in Validation and the supplement, with aggregate numbers only. Limits
in the Discussion are updated to what remains. No registered number is removed.
