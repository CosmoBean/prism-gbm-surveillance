# PRISM system-first manuscript redesign

## Intent

Recast the article as a paper about **transparent, longitudinal evidence reporting for glioma surveillance**.  PRISM is not presented as a replacement for clinician judgement or as a single superior progression predictor.  It is a system that puts the information relevant to a surveillance scan--image-derived measurements, treatment-course context, model outputs, uncertainty, provenance, and limitations--into one bounded, clinician-facing report.

The motivating sequence is:

1. Glioma surveillance is difficult because progression and treatment-related change can look alike on serial MRI.
2. An initial MU-Glioma-Post radiomics prediction model motivates the work, but prediction alone does not give a clinician the longitudinal context or show what evidence drove a score.
3. PRISM is built to assemble that context while keeping its evidence streams visible rather than collapsing them into an opaque verdict.
4. Internal and locked external tests establish how the model components behave across sites; report evaluation establishes whether the system can faithfully present the evidence it has.
5. A future reader study, not this study, must establish whether the report improves clinician decisions.

## Reader and desired takeaway

The primary reader is an imaging/biomechanics reviewer who wants a useful technical contribution with an honest clinical purpose.

After reading, they should be able to say: "PRISM is a reproducible surveillance-reporting system.  It keeps longitudinal image and treatment evidence distinct, tests its model components across centres, and gives a clinician the complete bounded evidence rather than a bare progression score."

They should **not** conclude that PRISM has been shown to diagnose progression, replace expert reads, improve patient outcomes, or outperform clinicians.

## Claim hierarchy

### Main claim

PRISM creates a transparent report for post-treatment glioma surveillance by assembling multiple longitudinal evidence streams and explicitly showing the model-derived evidence, its uncertainty, and what the models did not use.

### Supporting claims that the current evidence supports

- A radiomics/prediction result alone is insufficient for the intended clinical-facing output: it does not communicate inputs, temporal context, alternative evidence streams, or limits.
- PRISM's image and treatment-timeline pathways can be evaluated separately, and their score rankings transfer to the locked external cohorts under their documented evaluation definitions.
- Scores derive from different available evidence in different cohorts; retaining separate evidence streams makes that visible in the report rather than hiding it behind one score.
- The revised local report is faithful to the structured record and, compared with the earlier report format, is more complete under pre-specified automated usefulness criteria.  On 249 grade-4 MU records, the revised format passed the checker in 249/249 records and had mean criterion score 0.999 versus 0.674 for the previous format.

### Claims that must not appear without new evidence

- PRISM improves a physician's diagnostic accuracy, confidence, workload, treatment decision, or patient outcome.
- Models improve the report relative to a report that contains the same longitudinal facts but no model outputs.
- The report's automatic usefulness score is a validated measure of clinical usefulness.
- A score, prediction set, or report is a clinical diagnosis or recommendation.

## The unresolved, important question: do models add to the report?

The current manuscript has evidence that **a richer report format** adds required content relative to an earlier prompt.  It does not yet isolate the value of the model-derived fields.  The rewrite must say this plainly and must not manufacture an ablation result.

One optional, high-value follow-up analysis would compare three report records for the same held-out scans:

| Arm | Includes | Question it answers |
|---|---|---|
| Longitudinal facts | scan context, past-only volumes, treatment timeline, segmentation image, provenance | What can a careful structured summary show without a prediction? |
| Facts + model evidence | facts plus pathway/combined scores, intervals, agreement, contributions, and flags | What additional information does the model layer expose? |
| Full PRISM report | the prior arm rendered through the checked local report generator | Can the system express that additional information faithfully and readably? |

Until a clinician reader study is available, the appropriate outcomes are **content and transparency**, not clinical superiority: whether model fields change the report, whether they identify disagreement/uncertainty, whether their provenance is stated, and whether every claim remains grounded.  This analysis is a possible new workstream; it is not a prerequisite for rewriting the existing evidence honestly.

## Story structure

### Title

Retain the working title, which allows the contribution to be a system rather than an accuracy claim:

> PRISM: a modular system for glioma progression surveillance on MRI

### Abstract

Use five moves within the journal's 100--150 word limit:

1. Clinical need: surveillance MRI after treatment is difficult because progression and treatment effects overlap.
2. Gap: a prediction alone does not show the clinician the longitudinal evidence that produced it.
3. System: PRISM combines image measurements, treatment context, separate model pathways, uncertainty, and a local checked report.
4. Evidence: concise internal and locked external ranking results, followed by the report-faithfulness result.
5. Scope: PRISM is designed to present bounded evidence; clinical usefulness needs a reader study.

Avoid leading with a model score.  Do not use the abstract to recount every audit result.

### Introduction

1. **Clinical problem.** Glioblastoma and other aggressive gliomas require repeated surveillance; a scan is interpreted against the course of treatment and prior imaging, not in isolation.
2. **Why a score is incomplete.** Radiomics and other models can quantify image patterns, but an isolated probability neither gives the clinical timeline nor makes its evidence and omissions visible.
3. **System proposal.** Introduce PRISM as a longitudinal evidence-reporting system: measurements, timeline, separate pathways, uncertainty, provenance, and a report generated locally from a structured record.
4. **Study aims.** Evaluate component performance at the development and locked external cohorts; inspect what evidence drives scores; evaluate whether the report faithfully and completely conveys its structured evidence.  State that no clinician-impact claim is tested.

### Methods

Organise methods by what reaches the report, not by the chronological order analyses were created:

1. Cohorts and surveillance task.
2. Longitudinal inputs and image-derived measurements.
3. Prediction pathways and why they stay separate.
4. Structured report record: facts, model evidence, confidence/flags, provenance, and local generation/checking.
5. Evaluation: internal, locked external, audit, and report-faithfulness/usefulness-format comparison.

The task definition must use one stable phrase throughout.  The current main draft's scan-level detection task should be primary; the 120-day forecast belongs in a clearly labelled secondary analysis unless the report is rebuilt around that forecast instead.

### Results

1. **From prediction to a reportable evidence record.** State what the original radiomics exercise established and what it could not provide to a clinician.  Then show the PRISM report architecture.
2. **Component performance across cohorts.** Give the essential MU, LUMIERE, and UCSF results in one comparison figure.  The point is that components have measurable, tested behaviour--not that one AUC is the product.
3. **Why separate evidence streams matter.** Show the audit result: treatment-timeline evidence is prominent at MU and image/volume evidence at UCSF.  The reader should see why the report displays both rather than hiding them in a fused number.
4. **What the full report gives the reader.** Use one representative report/case and the revised-report evaluation.  Say exactly what passed: groundedness and pre-specified completeness criteria.  Then state the limit: these are not clinician-reader outcomes.
5. **Evidence boundaries.** Present disagreement, thin-evidence situations, and what the model did not use as report features, not as a claim of solved uncertainty.

### Discussion

Open with the system contribution and its intended clinical role: PRISM makes the evidence behind a surveillance output inspectable.  Then discuss transfer across sites as support for testing the components, not a declaration of deployment readiness.  Explain that the report is designed to support, not replace, clinician judgement.  End with the two needed next steps: the report-without-model ablation and a clinician reader study.

## Tables and figures

Every display must make one necessary point in the narrative.

| Display | Purpose | Evidence/source |
|---|---|---|
| Figure 1: Why PRISM is a system | Serial scan + treatment history -> measurements and separate pathways -> structured record -> checked local report.  Include an example of a field that comes from each source. | Existing architecture/report assets, redesigned as one coherent visual. |
| Table 1: Cohorts and evidence available | Show why PRISM needs modular inputs: which cohort contains longitudinal images, treatment dates, masks, progression documentation, and what the report can therefore contain. | Current Table 1, simplified and reframed. |
| Figure 2: Component behaviour across sites | One visual comparison of image, timeline, and combined pathways at MU, LUMIERE, UCSF. | Current locked and internal performance results. |
| Figure 3: Why a single score hides the story | A compact evidence audit: MU timing/phase, UCSF enhancement, and one example of pathway disagreement. | Current audit results; do not overload with exploratory model ladders. |
| Figure 4: What appears in a PRISM report | A rendered example with numbered callouts: longitudinal context, image measurement, separate scores, uncertainty/flag, provenance/what was not used. | Report v2/v3.1 artifacts; choose one final report version first. |
| Table 2: Report evaluation | Faithfulness, required-content completeness, safety/forbidden-content checks, and readability for the final report version.  Clearly label automated criteria. | `REPORT_USEFULNESS.md` or the final v3.1 evaluation, after versions are reconciled. |
| Supplement | Full statistical analyses, cross-validation/split detail, all model variants, calibration, checker rules, report prompt development, and reporting checklists. | Existing supplement, rebuilt to match the chosen report version. |

The existing Table 2 of pre-specified questions becomes supplementary or a much shorter methods table.  Repository commit hashes and broad analysis inventories do not belong in the main narrative.

## Required consistency pass before prose is final

1. Choose the report version used in the article.  The main text's v3.1 cross-site evaluation and the supplement's older v2/v1 report comparison are currently both present; they must be presented as a clear development sequence or one must be moved out.
2. Synchronise the endpoint used by the report with the endpoint described in the main task.  Do not mix scan-level detection and 120-day risk in the same sentence or figure.
3. State consistently that report evaluation is automatic grounding/completeness evaluation, not clinical validation.
4. Align every cited supplementary section with an existing section and delete all visible TODO/flag text from the submission build.
5. Build the five manuscript figures named by `main.tex`; the current requested figure files are absent and produce placeholders.

## Scope of implementation after approval

1. Replace the manuscript outline and write a new section-by-section prose map.
2. Reconcile report-version evidence and decide the primary report evaluation table.
3. Rewrite `paper/main.tex` from the map, preserving verified numbers and adding no unsupported outcome claim.
4. Redesign/build the necessary main figures and tables from existing outputs; mark any display requiring a new analysis.
5. Rewrite affected supplement sections and run a consistency/build review.

## Design choices made here

- The article is system-first, not prediction-first and not a report-generator-only article.
- Existing report-format evidence may support a claim of automated completeness/groundedness, but never a claim of clinical benefit.
- The no-model report ablation is identified as a valuable follow-up analysis, not retroactively implied by existing results.
