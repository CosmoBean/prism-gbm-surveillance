# Claims audit, 2026-11-27 (20 subagents, report only; findings verified and applied by the main session)

Coverage: 12 line-range claim checkers (every number against outputs/ and docs/results, every citation against its
source), 1 repeated-claims checker, 1 orphan-claims checker, 4 bibliography-link checkers (all 83 cited keys resolved
on Crossref/DataCite/arXiv), 2 system-comparison researchers (docs/literature/SYSTEM_COMPARISON_2026-11-27.md).
Agent findings were re-checked against the source files before any change (e.g. Dice 0.9347, CI +0.0348, AUC
difference 0.1151, planted-error rates from verifier_mutation/mutants.csv, journal versions on Crossref and PMLR).

## Corrected (wrong as written)
- MU enhancing tumour Dice 0.94 -> 0.93 (contribution 1, Table seg); Table seg LUMIERE combined CI +0.04 -> +0.03.
- Adding clinical history to images at MU: 0.11 -> 0.12.
- MU masks are automatic masks refined by neuroradiologists (Table 1); LUMIERE rates 616 of 638 study dates.
- "92 of the cohort's 126 grade 4 patients" -> of the 126 with a scan after treatment and before progression.
- Clinical-history inputs in Table models (no days-since-surgery input; missing inputs added).
- Figure 1 caption: first scan on or after documented progression.
- Methods: the time-and-enhancement model is reported at UCSF-ALPTDG (marked), not only in the segmentation comparison.
- Methods: "every report is counted as it was first written" was not true for LUMIERE; the text now states that the
  first evaluation run failed at LUMIERE, the prompt was revised on development records, and the reports regenerated.
- Statistics: intervals use 2,000 bootstrap samples (1,000 only for the supplied-mask radiomics comparison and the card).
- Radiomics comparison, perturbation test and language-model comparison labelled as supplied masks (and earlier prompt).
- Discussion: "rests largely on ... the enhancing volume" (contradicted by Section 3.2) replaced; claims about the
  baseline (needs the enhancing volume) and the shares (need weights and inputs of a linear model) corrected.
- Limitations: UCSF-ALPTDG progression is a multidisciplinary consensus; only UCSF-ALPTDG is small; calibration and
  label differences added; BraTS 2024 overlap names UCSF and Missouri (as in Methods).
- Figure 6 plotted the first re-implementation's radiomics interval; it now plots the authors'-code run (0.580, 0.502-0.662).
- shi2025 does not support "image alone / tested only within the cohort": booth2022 only (audit-4 C1 was wrong).
- refs.bib: jabal2026 -> Radiology: AI 8(6):e260234; herasrivera2026 -> MIDL 2026 (PMLR 315); ferreira2024 -> LNCS
  chapter; christodoulou2026code author G. Vamvouras (AUTHORS.md); arXiv DOIs added; siakallis2026 added.

## Added
- LUMIERE retrained (0.76) and fine-tuned (0.80) rows in Table "PRISM beside earlier models".
- Table "PRISM beside earlier systems" (contribution 2).
- Methods for analyses that had results but no method (timing-alone variants, enhancing volume alone, patient
  characteristics alone, the agreement AUC split, the earlier re-implementation).
- Abbreviations defined on first use (AUC, MGMT, RANO, BraTS, BT-RADS, IDH, MU).

## Waiting for the author: locked sentences (see the session reply).

## Not changed (noted)
- Calibration-slope CIs and the all-scans MU AUCs have no saved output file (the auditors' recomputations match).
- Notes on contributors still \todo.
