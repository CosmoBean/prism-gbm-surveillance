# Internal review of the manuscript (2026-10-15)

Written by a reviewer agent against `paper/main.tex` **before** the story rewrite (line numbers refer to that
version: `git show 01c9500:paper/main.tex`). Verification and what was done are noted first.

## Verified by the coordinator, and status

| Finding | Verified | Status in the rewrite |
|---|---|---|
| 38 of 39 censored grade 4 scans are "pre-RT" | Yes (`cv_predictions_grade4.csv.gz`, repeat 0: pre-RT 38 censored / 33 negative / 5 positive) | Stated in Discussion and Limitations; **re-analysis not done** |
| "Pre-RT" mixes RT pending with RT never documented | Yes: 63 of 76 grade 4 pre-RT scans (37 patients) never have RT documented; all 38 censored pre-RT scans are among them; median follow-up of the censored ones 0 days; 14 died without progression. RT documented later: 13 scans (11 negative, 2 progression, 0 censored) | Stated; **re-analysis not done** |
| N1: "9% of pre-RT scans progressed" counted censored as negatives | Yes: 10 / 68 with known status (15%), all gliomas | Fixed |
| N2: abstract 29 vs 30 patients | Yes | Fixed (abstract now says 30, as for v1's evaluation) |
| Over-claim "imaging adds nothing" | Agreed | Reworded to "no measurable gain"; upper CI bounds 0.02 to 0.16 stated |
| Abstract external result is not the core model | Agreed | Abstract now says "a locked model"; Limitations say the core model was not tested externally |
| N4: chance-exclusion arithmetic | Agreed | Methods now say "about two in each direction" (two-sided 5%) |
| N5: leaky model "about 0.70" | Yes (0.723 / 0.743) | Fixed |
| SHAP comparison used ridge core for boosting | Yes | Fixed (boosting 0.694 vs boosting core 0.687) |
| Shortcut refit exists (0.676) | Yes (`shortcut_arms.csv`) | Reported in Results |
| Bootstrap CIs exclude refitting variability | Agreed | Added to Limitations |
| Death as censoring, not competing risk | Agreed | Added to Limitations |
| Who read the 15 reports | Not recorded | Red placeholder in Results |
| N6: Table 1 "unknown 65" for the early window | Not resolved | Open |

# Referee report: PRISM manuscript (paper/main.tex)

Line numbers refer to paper/main.tex unless a different file is named.

## Major weaknesses

**M1. The phase-of-care "signal" is tangled up with censoring and with missing RT records.** In the audit CV predictions (`outputs/results/analyses/audit_system/cv_predictions_grade4.csv.gz`, one repeat), 38 of the 39 censored grade 4 scans are pre-RT. Half of the 76 pre-RT scans are censored, against about 1 of 173 post-RT scans. PHASE_LADDER.md §A says "pre-RT" means `rt_started == 0`, which includes **63 grade 4 scans from patients with no RT documented**, some as late as day 579. The phase that drives discrimination is therefore mostly "RT never recorded, follow-up short". It is not mainly the biology of the early post-operative period. Three problems follow:
- IPCW uses a marginal Kaplan-Meier censoring distribution (prism/models/metrics.py:100), which assumes censoring is independent of covariates. That assumption clearly fails here. AUCs and the O/E values are biased in an unknown direction. A covariate-dependent (phase-stratified) censoring model is needed.
- The paper calls this "phase of care" (l.79-88, 638-649, abstract "Phase of care ... drove discrimination"). Nowhere does it say that "pre-RT" is mostly "no RT documented". A reviewer will read it as a data-completeness artefact.
- The pre-RT event rate is misstated (see N1).

The paper does say that RANO 2.0's 12-week rule makes progression documentation within 120 days unlikely for a pre-RT scan (l.46-48). The clinical question that matters is therefore discrimination *within* a phase. There the core model reaches only 0.555 / 0.663 / 0.597 (l.555-556). Repeat-1 verified-scan AUCs are even lower: pre-RT 0.45, early post-RT 0.63, later post-RT 0.58. The headline 0.70 is mostly something a clinician already knows.

**M2. The abstract's external claim is misleading.** "Locked external AUCs were 0.61-0.62" (l.32) sits right after the core model's 0.70, which implies PRISM was externally validated. The deployed core model was *not* transported, because LUMIERE has no treatment dates (l.672, 692-693). The 0.61-0.62 belongs to a different model (clinical + timing + volumes). External validation of the deployed system is effectively absent. On LUMIERE, the time to the next scan alone (0.788, l.520) beats every model, which shows how much the label depends on scheduling.

**M3. "Imaging adds nothing" is stated as a finding when the study could not have shown it.** The abstract says "added nothing measurable" (l.32) and the conclusion says "added no measurable discrimination" (l.714-715). The evidence does not exclude a real effect:
- Several CIs reach +0.07 to +0.16 (all-glioma radiomics +0.071, post-RT +0.156, LUMIERE deep +0.215).
- Point estimates for the cleaner label and the new masks move in the expected direction (+0.027, +0.030).
- The study sits at 3.0 events per parameter for the *core* model alone (l.535).

The Discussion admits this (l.660-662), but the abstract and conclusion do not. The authors should state minimal detectable effects for each primary contrast, as they already do for CFB-GBM (0.038). Rephrase as "not shown".

**M4. The imaging branches look set up to fail.**
- Encoders were frozen and trained for segmentation, features were mask-pooled and then reduced to PCA-10 (l.218-220, Table 3). There was no fine-tuning (l.697-698) and no longitudinal deep features.
- Radiomics used a fixed bin count against IBSI guidance, and the ICC filter covered only T1c and FLAIR (l.696-697).
- The core imaging signal, the volumes, comes from masks that change 3.2-fold between scans ≤14 days apart (l.499). It is unclear whether imaging change features (delta radiomics) were built from the noisy MU masks or the re-segmented ones.
- There was no perfusion or diffusion data in the development cohort.

Reviewers will want either a fine-tuned or longitudinal model, or the claim narrowed explicitly to "frozen, off-the-shelf features".

**M5. Pre-specification is weak, and the paper partly undermines it itself.**
- Every plan was written by the analysis team itself. None was registered.
- The phase-ladder plan was "not committed separately", and a smoke run printed I0-I2 numbers before the full run (supplement.tex l.49).
- The clean-label, re-segmentation, CFB and audit analyses were all designed after the imaging null was known (supplement.tex l.60-62).
- The headline estimator was changed "before the final run" but after earlier results were seen (l.258-259).
- The split-variance analysis was designed after the single-split result was known.

The paper discloses all of this honestly. Still, calling these analyses "pre-specified" in bold (l.270, 476, 571) oversells them. Use "rule fixed before run".

**M6. The CV uncertainty is probably understated.** The 95% CIs come from a patient-cluster bootstrap of fixed out-of-fold predictions (l.259-261). This ignores training-set variability. Nested-CV or bootstrap-refit intervals (e.g. Bates, Hastie & Tibshirani 2023) are wider. Uncorrected multiplicity across ~32 forest intervals plus 70-80 configurations is acknowledged, but the arithmetic is inconsistent (N4).

**M7. The audit-layer and conformal claims are mostly trivial or negative, yet the abstract presents them as successes.**
- Under exchangeability, split-conformal marginal coverage holds by construction. Meeting P1 is a sanity check, not an achievement.
- Coverage was computed only on verified scans, which excludes the censored scans, and those are almost all pre-RT (M1).
- Coverage of pre-RT progressions was 0 (l.548-549). Exchangeability is also violated by repeated scans per patient.
- P2 failed, and 72.6% of scans carried a referral flag, so the flags do not triage.

The abstract (l.32) reports P1 and leaves out P2.

**M8. Leakage the audit found but nobody fixed.**
- The IDH-unknown shortcut costs −0.023 (CI excludes 0; l.558-560). It is 0/93 in events, and it explains the LUMIERE miscalibration.
- The molecular look-ahead on 8 grade 4 scans "was not quantified" (l.700-701).

Both fixes are cheap and the headline should be rerun with them. Publishing a deployed model with a known shortcut is hard to defend. The reported core AUC (0.698) is thus slightly optimistic. A refit without the unknown indicators already exists: 0.676 [0.592, 0.752] (`shortcut_arms.csv`).

**M9. The report-generator evaluation is self-referential.**
- Faithfulness is judged by a lexical checker the authors wrote, plus "reading 15 reports" (l.590-592). The paper never says who read them. In docs/results/REPORT_AGENT.md the reading appears to be part of the automated pipeline, and no clinician is named.
- Arm B is a straw man. The v1 prompt was *designed* to give RANO verdicts and management advice, so it scoring 100% "forbidden" (l.582-583) tells us nothing.
- The abstract's "236 of 249 ... were fully faithful" (l.32) contradicts the pre-specified primary, which was *not met* (l.571). It also inflates what a lexical check can show; the limitations admit it does not check meaning (l.702-704).
- Clinical usefulness was not assessed at all (l.706-708).

**M10. The contribution is not clear.** The paper reads as three papers: a system paper, a negative-results and methods-caution paper (single split, phase confounding), and an LLM-grounding paper. Contributions (i)-(iv) (l.100-107) put "presents PRISM" first. Yet the deployed PRISM is a 31-column ridge model with near-trivial within-phase discrimination and no external test. Most of the evidence supports the methods-caution message. The self-correction story is admirable, but it makes up about 40% of the Results and invites the question "why should we trust v2's numbers?" Novelty against An 2021 (split instability) and Kapoor 2023 (leakage) is narrow. The phase-confounding mechanism is the real novelty, and it is weakened by M1.

## Minor weaknesses

- Death is treated as censoring rather than as a competing risk (l.182). In glioblastoma this is not negligible: 20 grade 4 scans. A cumulative-incidence (Aalen-Johansen) sensitivity analysis is needed.
- The CFB-GBM analysis is circular for the volume block (l.526), the t1 scan falls inside the 12-week window, and only 107 and 77 of 264 patients are used (l.522-525) with no reason given. Its contribution is marginal.
- The post-RT cohort is defined as "RT documented and completed", which excludes patients without documented RT. This is a selection issue, and it should be in the main text, not only in PHASE_LADDER.md.
- Later post-RT bases fall below 0.5 (0.343-0.472, l.484). This reflects instability of the method, not just "uninterpretable" contrasts.
- In the SHAP comparison (l.463-464), the boosting model (0.694) is compared with the *ridge* core (0.698) rather than the boosting core (0.687).
- l.671: "fell from 0.80 to 0.61" compares an optimistic single split with external performance. The fair comparison is 0.72 → 0.61.
- l.60 / l.681: Christodoulou 2026 ("calibrated, explainable radiomics", 0.80, MU-Glioma-Post) closely resembles PRISM v1. Reviewers will ask how the two relate and why the 500-split analysis was not applied to it.
- Unresolved `\flag{[CHECK]}` and `\todo` markers remain (l.61, 150, 166, 219, 680; author block, declarations). There are 9 CHECK entries in refs.bib, and Rai 2026 is unverified but used as a comparator (l.680).
- The LLM is "Qwen3.8-27B" (l.341). Give the HF revision hash in the main text so the model can be verified.
- Typo: "0.996-- 0.9998" (l.499).

## Number inconsistencies found

| # | Location | Conflict |
|---|---|---|
| N1 | l.381-382, l.409 | "8.7% / 9% of pre-RT scans were followed by progression". That is 10/115 *including censored scans* as non-events. Among verified scans it is 10/68 = 14.7% (all gliomas) and 5/38 = 13.2% (grade 4), from cv_predictions_*.csv.gz. This is the same naive-label error the paper criticises. |
| N2 | l.32 vs l.96 | Abstract: v1 scored 0.80 on a "29-patient test split". Intro: "30-patient split". v1 was scored on 30 patients / 84 scans (l.822, supplement l.514); 29/82 is the label-fixed version. |
| N3 | l.226 vs l.247 | v1 model "on 46 ... columns" vs "the shipped 48 features". SHAP_PRISM_SPLIT.md l.14 explains this (46 of 48 used), but the paper does not. |
| N4 | l.269, l.453 vs Fig 3 caption l.949 | "70-80 intervals → 1.75-2 expected to exclude 0" uses a one-sided 2.5% rate (two-sided gives 3.5-4). Fig 3 caption: "3 of 32 ... about 1.6 expected" uses two-sided 5%. Pick one convention. With two-sided, l.453's "fewer than the 1.75 expected" becomes 1 vs 3.5, and supplement l.430's "3/80" all-glioma deep configurations becomes 3 vs 4. |
| N5 | l.630-631 | "That model [leaky boosting] averaged about 0.70 under repeated CV". Under leaky inputs it averaged 0.723 (G4) and 0.743 (all), l.399 and Table 2. After the fix it was 0.687 and 0.718. |
| N6 | Table 1 l.793 vs l.381 | Table 1 says early post-RT status is "unknown" for 65 grade 4 scans, yet §3.1 assigns all 249 grade 4 scans to four phases (76/6/98/69). The 65 are mostly no-RT-documented patients folded into "pre-RT". Reconcile in the text. |
| N7 | l.384 vs l.564 | IDH unknown "36% of LUMIERE patients / 8% of MU patients" vs "40.9% of LUMIERE scans / 4.4% in MU" (grade 4 scans). The units differ (patients vs scans, all gliomas vs grade 4) and no label says so. |
| N8 | l.32 vs l.571 | Abstract "fully faithful" vs "Primary ... not met". |
| N9 | l.671 | "0.80 to 0.61" uses a single-split baseline (see Minor). |
| N10 | l.972 comment | Says Fig 5C is "PNG only, 150 dpi", but commit c4d0599 added a vector PDF. Stale comment only. |

These numbers checked out against the outputs: P1 0.841 [0.790, 0.885]; P2 +0.006 [−0.023, +0.036]; 0.731 / 0.725 / 0.698; shortcut −0.023 [−0.047, −0.001]; treatment-only 0.701; IDH-unknown 0/93, 6/117, 5/39; arm A 236/249, 0.948 [0.913, 0.969]; arm B 171/249, +0.261 [+0.197, +0.328], 48/269 flags; arm C 243/249, −0.028 [−0.062, +0.008]; post-RT 167/84/83; 120 d counts; 0.10-0.16 single-split excess; 2/3 composition share (71% / 65%).

## What a reviewer will ask for

1. **Phase-stratified (covariate-dependent) IPCW, and a phase × label × censoring table.** Re-estimate the headline AUCs. Moderate. Partly answered: the crosstab is computable from cv_predictions_*.csv.gz; the reweighting is not done.
2. **Split "pre-RT" into "RT pending" and "RT never documented" and report AUC with and without the latter.** Cheap to moderate. Not answered.
3. **Make within-phase discrimination the headline**, or a phase-stratified (conditional) AUC for every model, including imaging contrasts. Cheap. Partly answered (referral_within_phase.csv for the core model only).
4. **Refit the deployed core model without the unknown indicators and with the 8 look-ahead scans fixed; report it as the headline.** Cheap. Partly answered: shortcut_arms.csv gives 0.676 without indicators; the look-ahead fix is not done.
5. **A competing-risk label** (death as a competing event). Moderate. Not answered.
6. **Minimal detectable ΔAUC / power for each primary contrast** (radiomics G4, post-RT I2, clean label, re-segmentation). Cheap; can be derived from the bootstrap SDs. Only CFB has one.
7. **Fine-tuned or longitudinal deep model** (e.g. a fine-tuned SwinUNETR or a delta-embedding model with a nested inner loop), or a narrowed claim. Expensive. Not answered.
8. **Transport the core model to a cohort with treatment dates**, or approximate LUMIERE treatment phase from the < 3-month flag plus surgery dates. Moderate to expensive. Not answered; the gap is acknowledged.
9. **Refit-based CV uncertainty** (nested-CV CI or bootstrap-refit) for the primary ΔAUCs. Moderate. Not answered.
10. **Blinded clinician rating of reports** (factual accuracy, usefulness, harmful content) on a random sample, with inter-rater agreement. Arm B should be replaced by a fair baseline: the same constraints with ungrounded free text. Moderate. Not answered; the 15-report reading has no named reader.
11. **Fresh-record test of the report generator after the horizon-citation fix** (other CV repeats or the LUMIERE records). Cheap. Not answered.
12. **Decision-curve analysis within phase**, and a concrete use case (shortening the scan interval) showing net benefit over "treat by phase". Cheap. Partly answered (CLINICAL_UTILITY.md gives pooled values only).
13. **Re-evaluate Christodoulou 2026-style radiomics under the 500-split and phase framework**, or explain how it relates to PRISM v1. Moderate. Not answered.

## Presentation

- At about 1,000 lines with a 1,600-line supplement, the paper is too long. The history rows of Table 2, the leak arithmetic (l.396-405), the composition-regression detail (l.428-439), the Positive controls paragraph, the re-segmentation details, CFB-GBM, the report-generator stress test and arms B and C belong in the supplement.
- "PRISM's initial radiomics model", "initial radiomics pipeline", "our initial evaluation split", "PRISM v1" and "core model / baseline" are hard to keep apart. Use a glossary or shorten the terms.
- The audit layer's referral flags, conformal sets and risk tiers should be compressed to one paragraph, given that they do not triage.
- The Discussion repeats the Results nearly number for number (l.599-623, 651-668).
