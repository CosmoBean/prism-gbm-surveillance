# Outline: the argument of the PRISM paper

Current outline only (consolidated 2026-11-19). Earlier framings, decision logs and council rulings are in git history
(this file before consolidation: commit e647e79) and in `archive/`. Rules: [STYLE.md](STYLE.md); locked text:
[LOCKED.md](LOCKED.md); reviewer reserve: [RESERVE.md](RESERVE.md); numbers: [NUMBERS.md](NUMBERS.md).

## Title and spine

**PRISM: an auditable local system for glioma follow-up MRI.**

The spine below is set by the locked abstract, and the author approved it on 2026-11-18. The contributions follow
the same order.
1. **Premise.** A score for a follow-up MRI is useful only if the reader can see what it rests on, and a generated
   report only if each statement can be checked against the record.
2. **The system.** PRISM is a local system built for both. It scores each scan with separate imaging,
   clinical-history and combined models. Every value goes into one record with its source, and a local language model
   writes a report that is checked against that record.
3. **What the separation exposed.** On MU-Glioma-Post, the time after radiotherapy and the enhancing tumour carried
   most of the ranking. The combined model added no clear gain over the timing-and-enhancement baseline.
4. **Locked transfer.** The models were fitted once on MU and applied unchanged at LUMIERE and UCSF-ALPTDG.
5. **Checked reports.** Every report for a held-out patient passed the record check, and a verifier rejected
   planted errors.

What PRISM *is* (the PI's emphasis) is stated at the end of the Introduction:
- a chain of deterministic stages around one schema-bound local language model, centred on the record;
- placed beside BTReport and the multi-agent BT-RADS system.

## Sections, figures and tables (as in `paper/main.tex`)

1. **Introduction:**
   - follow-up MRI after treatment;
   - advanced imaging and reporting practice;
   - machine learning in this setting;
   - shortcuts and what an AUC rests on;
   - conformal sets;
   - generated reports and checking;
   - "We present PRISM", "auditable" defined, four contributions;
   - what PRISM is technically.
2. **PRISM** (Figure 1, the method; Table 1, the scores in the paper):
   - 2.1 inputs and measurements;
   - 2.2 three models;
   - 2.3 record and report.
3. **Evaluation:**
   - 3.1 cohorts and the task (Table of the three cohorts; Figure 2, when the evaluation scans were taken);
   - 3.2 evaluation design (Table of the design by cohort);
   - 3.3 the timing-and-enhancement baseline and the AUC split;
   - 3.4 confidence statements;
   - 3.5 checking the reports;
   - 3.6 planned tests (Table of planned tests and their outcomes).
4. **Results:**
   - 4.1 comparison with the published radiomics pipeline on the same task (context, not in the abstract);
   - 4.2 the locked models ranked scans at two external centres (Figure 3, performance);
   - 4.3 timing and the enhancing tumour account for much of the ranking (Figure 4, where the ranking comes from);
   - 4.4 the confidence statements describe the evidence behind each score (Figure 5, coverage within groups;
     Figure 6, four patients' follow-up);
   - 4.5 reports and the checker (Figure 7, the report and the check; Table of planted errors).
5. **Discussion:** answer the premise first; limits as scope; future work once, at the end. Then the Conclusion.

## Supplement and reserve

The supplement holds only what the current paper rests on. Detail behind each step goes to RESERVE.md.

## Open for the author

- **The Section 4.5 heading** ("after one revision of the prompt") carries development history, against STYLE.md
  sections 3 and 6. A neutral replacement is needed.
- **The Figure 3 caption** says "development centre"; it should say "public development cohort" (STYLE.md section 2).
- **The locked abstract.** "AUC 0.80" can be read as the combined model's AUC, but it is the baseline's. The word
  "progression" never appears. Smallest edit to be proposed; author approval needed.
- **Figure 7.** Keep the real report (PatientID_0029, no enhancing tumour), or choose a scan with visible
  enhancement.
- **The UCSF row of Figure 2.** The UCSF data were restored on 2026-11-19; the records still need regenerating.
