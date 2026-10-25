# One-week manuscript plan: what to fix, what to add, what to leave

Prepared 2026-10-11. Builds on [literature/RELATED_WORK.md](literature/RELATED_WORK.md) (70 references, ranked by topic) and
[literature/comparison.md](literature/comparison.md) (study-by-study comparison, re-implementable baselines B0–B8).
Results quoted from [results/IMAGING_VS_NONIMAGING.md](results/IMAGING_VS_NONIMAGING.md), [results/C3_radiomics.md](results/C3_radiomics.md)
and [results/EXTERNAL_LUMIERE.md](results/EXTERNAL_LUMIERE.md).

## 0. Bottom line

- **The paper is a rigorous re-evaluation, not a better model.** Claim: *on conventional post-treatment MRI, a treatment-aware
  clinical baseline predicts 120-day progression as well as radiomics (honest AUC ≈ 0.69–0.73); the PRISM report's 0.80 came
  from a favourable single split, and the radiomics model drops to 0.61 on LUMIERE.*
- **Do not try to "win" on AUC in a week.** Across the literature, conventional-MRI models land at 0.65–0.77 once validated
  honestly (Booth 2022 pooled ≈ 0.77; Moassefi 2022 0.76; Suter 2024 0.75 on LUMIERE-type data). Only perfusion/diffusion pushes
  past 0.85 (Taylor 2022; Kim 2019), and MU-Glioma-Post has neither. Our numbers are in the normal range; the novelty is showing
  *why* and *what the baseline really is*.
- **The weakest part of the current draft is positioning, not modelling.** It cites ~16 references, compares against none of
  the published MU-Glioma-Post or LUMIERE work, and follows no reporting checklist. That is fixable in a week.
- **Drop the LLM agent from this manuscript.** It has fixed prompts and no tuning or clinician evaluation, so a reviewer cannot
  assess it, and it distracts from a clean prediction-model paper. One sentence in Future Work is enough.

## 1. How the related work fits with ours

| Related work | What it gives us | How we use it |
|---|---|---|
| Christodoulou 2026 (same MU task, AUC 0.80, one split) | The direct comparator | Re-implement on our folds (B2): reported 0.80; correction (2026-10-26): a re-implementation of their setting (CHRISTODOULOU_REPLICATION.md, 2026-10-26) gives 0.565 under repeated CV on our detection label; the earlier "0.64–0.70" was a 120-day ridge model, not their setting. Central comparison row |
| Rai 2026; Hashim 2026 (MU-Glioma-Post) | Other MU numbers with different endpoints | Comparison table; explain why their labels (volume-defined, PFS) are not ours |
| Suter 2024; TRACE; Tikhonov (LUMIERE) | LUMIERE ceilings (~0.75 AUC, macro F1 ≤ 0.71) | Shows our 0.72 external result is at the field's level, and that volumes alone transport poorly |
| Booth 2022; Bhandari 2022; Park 2020 (reviews) | High risk of bias, few external tests, missing clinical baselines | Introduction: the gap we fill. Discussion: our study as the "done properly" case |
| Abler 2025; Bae 2018; Vils 2021 | Radiomics adds little over age/sex/MGMT/IDH for survival; fails externally | Our result extends this to short-horizon progression during surveillance; this is the main supporting literature |
| Welch 2019; An 2021; Demircioğlu 2021; Kapoor 2023 | Volume surrogates, single-split inflation, leaky selection | Methods justification for nested CV, volume baselines, permutation control, split-variance figure |
| Brandes 2008; Taal 2008; Wen 2010/2023 | Pseudoprogression in the 12-week post-RT window, MGMT dependence | Explains why timing and treatment features carry signal; motivates a post-RT window feature and a stratified analysis |
| Perry 2017; Stupp 2005; Hegi 2005 | RT schedule follows age and performance status | Explains the RT-schedule × age signal: it is clinical selection, not leakage |
| Vock 2016; Blanche 2013; Uno 2007; Tutz & Schmid 2016 | IPCW labels and AUC(t), discrete-time hazards | Methods citations for C1; currently uncited |
| Van Calster 2019; Vickers & Elkin 2006; Pencina 2008; Riley 2020; TRIPOD+AI; CLEAR | Calibration, net benefit, added value, sample size, reporting | Each maps to a missing analysis or checklist (Section 3) |

## 2. Can we improve the model? What is worth implementing

Expected gains are small. Implement only what is cheap, defensible, and comes from the literature; each addition goes inside
nested CV.

| Idea (source) | Expected effect | Cost | Verdict |
|---|---|---|---|
| **As-of-scan treatment masking** (our own leakage fix) | One-off check: grade 4 ridge 0.694 → 0.732 | 0.5 day + rerun (~25 min) | **Must do.** Fixes leakage and probably raises the baseline |
| **Post-RT 12-week window flag × MGMT** (Brandes 2008; Taal 2008; RANO) | Small; makes the timing signal clinically interpretable | 0.5 day | Do. Cheap and clinically motivated |
| **Volumetric RANO-style rule** B1: ΔET vs nadir ≥ 40 %, past scans only (Kickingereder 2019; Ellingson 2017) | A standard clinical baseline, not a gain | 1 day | Do. Reviewers will ask "does it beat RANO?" |
| **Persistence baseline** B0: current ET volume or ΔET | Floor reference | < 0.5 day | Do |
| **Hashim-style Cox** B4 (volume + age + grade + IDH + MGMT) | Published MU-style baseline | 0.5 day | Do |
| **Patient-history features**: number of prior scans, prior growth rate, days since nadir (Suter 2024 change features) | Possibly +0.01–0.03; untested | 1 day | Optional, only if days 1–3 finish early |
| **Small nested hyperparameter grid** (ridge C; boosting depth / learning rate) | ~±0.01; mostly removes the "you didn't tune" objection | 0.5 day | Do, nested only, and report that the conclusion is unchanged |
| Recalibration for external sites | Already done (O/E 0.94–0.98 on LUMIERE) | — | Keep; present as the adaptation step |
| Peritumoral shell radiomics (Yun 2025, B5) | Unknown; likely the same null result | 1 day CPU | Optional extra radiomics row |
| Deep learning / temporal SSL / concept bottleneck (B7, B8) | Unknown; weeks of GPU | ≥ 1 week | **Not this week.** Future Work |
| Second external cohort (UCSF-ALPTDG; Burdenko; UCSD-PTGBM) | Strengthens transport claim | Data access + preprocessing: > 1 week | **Not this week.** Name it as the next step |
| Perfusion / diffusion features | The only route to > 0.85 in the literature | Not in the data | Limitation |

## 3. Must fix before submission (reviewer-blocking)

1. **As-of-scan treatment masking in code** (`prism/features/tabular.py:treatment()`), then rerun C2, C3 and external.
   Every headline number changes, so do this first.
2. **Schedule-coupling analysis.** Time to next MRI alone gives AUC 0.64. Report:
   (a) AUC stratified by next-scan-interval tertile;
   (b) the baseline model with that interval added as an adjustment-only covariate, to show timing features are not just
   proxying it;
   (c) excluding scans within 12 weeks after RT.
   If the effect survives (a)–(c), state that; if not, say so in the paper. This is the analysis most likely to be asked for.
3. **One pre-specified primary analysis.** Primary: grade 4, verified 120-day label with IPCW, ridge baseline vs baseline +
   radiomics (nested), ΔAUC with patient-cluster bootstrap. Everything else is secondary or sensitivity. This stops the 70
   configurations from looking like a fishing trip.
4. **Calibration and clinical usefulness.**
   - Calibration curve, slope and O/E for the primary models (Van Calster 2019).
   - Decision-curve analysis (Vickers & Elkin 2006) over thresholds of 10–40 %.
   - Added value as ΔAUC and continuous NRI/IDI (Pencina 2008).
   AUC alone cannot answer "is 0.70 useful?".
5. **Split-variance figure** (An 2021). Draw ≥ 500 random 30-patient splits with the PRISM report's design, plot the
   distribution of test AUC, and mark 0.80. This one figure makes the main argument.
6. **Sample-size statement** (Riley 2020): events per candidate parameter for the baseline and radiomics models.
7. **Cohort flow diagram** from `docs/results/cohort_flow.csv`: 594 → 314 scans, with censoring counts.
8. **Literature comparison table** in the manuscript: study, data, endpoint, validation, n, AUC, external test (from
   comparison.md Table A/B), with our numbers in the same format.
9. **Reporting checklists**: TRIPOD+AI (prediction model) and CLEAR (radiomics) as supplementary tables. Cite RANO 2.0, not
   only RANO 2010.
10. **Naming and claims.** "PRISM report model/split", never "published". The claim is "no measurable added value", not
    "clinical beats imaging in general".

## 4. What you can afford to tune, and what not

- **Can tune (nested, reported):** ridge C, boosting depth / learning rate / min-leaf, IPCW weight clipping, feature-group
  choice (already nested in C2). Report the grid in a supplementary table.
- **Should not tune:** the 120-day horizon (fixed a priori; report 90/180 d as sensitivity only), the fold seeds, the radiomics
  configuration after seeing results, or the external-test models. Any of these looks like p-hacking in a negative-result paper.
- **Fixed by design and worth saying so:** the PRISM report model is evaluated *as shipped* on LUMIERE; no retuning.

## 5. Better report examples to model the manuscript on

| Example | What to copy |
|---|---|
| Abler et al. 2025, *The added value for MRI radiomics and deep-learning for glioblastoma prognostication compared to clinical and molecular information* ([arXiv:2507.15548](https://doi.org/10.48550/arXiv.2507.15548)) | The closest template: same question (does imaging add to clinical?), feature-set ladder (clinical / imaging / combined), internal + external, cautious conclusion. Note it is a preprint |
| Bae et al. 2018, *Radiology* ([doi](https://doi.org/10.1148/radiol.2018180200)) | How to present added value over a clinical + molecular model (iAUC, nested comparison) |
| Vils et al. 2021, *Frontiers in Oncology* ([doi](https://doi.org/10.3389/fonc.2021.636672)) | How to report a model that fails external validation, in a mid-tier journal |
| Kickingereder et al. 2019, *Lancet Oncology* ([doi](https://doi.org/10.1016/S1470-2045(19)30098-1)) | Figure design for longitudinal response, external test presentation |
| An et al. 2021, *PLOS ONE* ([doi](https://doi.org/10.1371/journal.pone.0256152)) | The split-variance figure and argument |
| Kocak et al. 2023, CLEAR checklist, *Insights into Imaging* ([EQUATOR](https://www.equator-network.org/reporting-guidelines/checklist-for-evaluation-of-radiomics-research-clear-a-step-by-step-reporting-guideline-for-authors-and-reviewers-endorsed-by-esr-and-eusomii/)) | Supplementary checklist (58 items; CLEAR-S short form) |
| Collins et al. 2024, TRIPOD+AI, *BMJ* ([doi](https://doi.org/10.1136/bmj-2023-078378)) | Section-by-section structure and checklist |

Target journals in the requested range (check current impact factors before choosing): *Journal of Neuro-Oncology*,
*Neuroradiology*, *BMC Medical Imaging*, *Frontiers in Oncology*, *Cancers*, *Neuro-Oncology Advances*, *European Journal of
Radiology AI* (where Christodoulou 2026 appeared).

## 6. Seven-day schedule

Pipeline runs are cheap (`scripts/run_all.sh --skip-radiomics` ≈ 23 min), so the limit is writing, not compute.

| Day | Analysis | Writing |
|---|---|---|
| 1 | As-of-scan treatment masking in code; rerun C2/C3/external; post-RT window flag | Lock the claim and primary analysis (Section 3.3) |
| 2 | Schedule-coupling analysis (3.2); split-variance figure (3.5) | Methods: cohort, labels, censoring, CV |
| 3 | Baselines B0, B1, B4; nested hyperparameter grid | Methods: models, baselines, statistics |
| 4 | Calibration curves, DCA, NRI/IDI; sample-size statement | Results: primary analysis, baselines |
| 5 | Freeze numbers; make figures and tables | Results: external, sensitivity; comparison table |
| 6 | Optional: patient-history features or B5 if time | Introduction and Discussion with the new citations |
| 7 | Checklists (TRIPOD+AI, CLEAR); final consistency check of every number | Abstract, limitations, data/code availability |

## 7. Manuscript skeleton

- **Title** (suggestion): *Does MRI radiomics add to clinical and treatment information for short-term progression prediction
  in post-treatment glioblastoma? A censoring-aware re-evaluation with external validation.*
- **Figures:** (1) cohort flow + study design; (2) split-variance distribution with 0.80 marked; (3) model ladder:
  AUC with CIs for persistence, RANO rule, clinical, clinical + timing + treatment, + radiomics (MU and LUMIERE side by side);
  (4) calibration and decision curves; (5) ΔAUC across the 70 radiomics configurations.
- **Tables:** (1) cohort characteristics MU vs LUMIERE; (2) literature comparison; (3) primary results with ΔAUC;
  (4) sensitivity analyses (schedule coupling, post-RT window, 90/180 d, all gliomas).
- **Supplement:** TRIPOD+AI, CLEAR, hyperparameter grid, full C2/C3 grids, label formulations (C1).
