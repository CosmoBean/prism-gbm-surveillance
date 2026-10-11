# Manuscript plan: summary (2026-10-11)

Snapshot of the chat answer that accompanied [MANUSCRIPT_ONE_WEEK_PLAN.md](MANUSCRIPT_ONE_WEEK_PLAN.md). The full plan, the day-by-day schedule, the model ladder and the manuscript skeleton are in that file.

**Bottom line:** in a week, don't chase the 0.80. The paper is a careful re-evaluation of the PRISM report model, not a better model. The weakest part right now is positioning against other work, not the model itself: the PRISM report cites 16 papers, compares against none of the published MU-Glioma-Post or LUMIERE studies, and follows no reporting checklist.

## How the related work fits with ours

- **Our numbers are normal for this field.** Models using only conventional MRI land at about 0.65–0.77 AUC once tested properly (Booth 2022 pooled ≈ 0.77; Moassefi 2022 0.76; Suter 2024 0.75 on LUMIERE-type data). Only perfusion or diffusion MRI pushes past 0.85, and MU-Glioma-Post has neither.
- **Radiomics adds little over clinical information for survival.** Abler 2025, Bae 2018 and Vils 2021 already found this. We extend it to 120-day progression during follow-up, which is the core argument of the paper.
- **Christodoulou 2026 is the direct comparator.** It works on the same MU-Glioma-Post task and reports AUC 0.80 from one split. Re-running that setting with repeated CV gives 0.64–0.70.

## Must fix (reviewer-blocking)

1. **Treatment leakage.** Add as-of-scan treatment masking to the code and re-run everything. A one-off check moved the baseline from 0.694 to 0.732, so every headline number changes.
2. **Schedule coupling.** Time to the next MRI alone gives AUC 0.64. Stratify by scan interval, adjust for it, and exclude scans in the 12-week post-RT window.
3. **One pre-specified primary analysis.** Otherwise the 70 radiomics configurations look like a fishing trip.
4. **Usefulness, not just AUC.** Add calibration curves, decision-curve analysis and NRI/IDI for added value.
5. **Split-variance figure.** Draw at least 500 random 30-patient splits and mark 0.80 on the distribution.
6. **Standard reporting.** Add a cohort flow diagram, a sample-size statement, a literature comparison table, and the TRIPOD+AI and CLEAR checklists.

## Worth adding to the model

These are cheap and literature-backed, and all run inside nested CV:

- a post-RT 12-week flag combined with MGMT;
- a volumetric RANO-style rule baseline;
- a persistence baseline;
- a Hashim-style Cox baseline;
- a small hyperparameter grid, mainly to pre-empt "you didn't tune".

Expected gains are about 0.01–0.04 at most. Deep learning, a second external cohort and perfusion features go to future work.

## Tuning

- **Can tune** inside nested CV, and report it: ridge C, boosting depth, learning rate and minimum leaf size, IPCW weight clipping, and feature-group choice.
- **Should not tune:** the 120-day horizon, the fold seeds, the radiomics configuration after seeing results, or anything on the external test. In a negative-result paper, any of these reads as p-hacking.

## The LLM agent

Fixed prompts, no tuning and no clinician evaluation mean reviewers can't assess it. Reduce it to one sentence under Future Work.

## Example reports to model the manuscript on

- **Abler 2025** (arXiv:2507.15548, preprint) — the closest template: same added-value question, a clinical → imaging → combined ladder, internal and external tests.
- **Vils 2021** — how a mid-tier journal reported a failed external validation.
- **An 2021** — the split-variance argument.
- **CLEAR** (Kocak 2023) and **TRIPOD+AI** (Collins 2024) — the reporting checklists.

## Sources

- [CLEAR checklist (EQUATOR Network)](https://www.equator-network.org/reporting-guidelines/checklist-for-evaluation-of-radiomics-research-clear-a-step-by-step-reporting-guideline-for-authors-and-reviewers-endorsed-by-esr-and-eusomii/)
- [CLEAR (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/10160267)
- [Abler et al. 2025 (arXiv:2507.15548)](https://arxiv.org/abs/2507.15548)
