# PRISM report-field ablation: design

## Intent

Determine whether adding PRISM's model-derived fields to an otherwise identical longitudinal surveillance report
adds **grounded, inspectable information**. This is an automatic report-generation study. It does not test
clinical comprehension, decisions, diagnostic accuracy, workload, trust, or patient outcomes.

The result will be reviewed before deciding whether to include it in the manuscript. A null or mixed result will
remain a valid result and must not be hidden.

## Scope and non-goals

**In scope**

- Generate paired reports from the same locked v3.1 evaluation records.
- Compare a full PRISM evidence report with a strict facts-only report.
- Test grounding, required factual coverage, forbidden model language, perturbation response, report length,
  generation failure, runtime, and cost.
- Preserve record-level pairing, cohort membership, writer configuration and reproducibility metadata.

**Out of scope**

- Reader, clinician, workflow, diagnostic, or outcome evaluation.
- Retraining prediction, segmentation, confidence, or language models.
- Claiming that one arm is clinically more useful.
- Altering the existing v3.1 report evaluation or its locked outputs.

## Study arms

### Full-evidence arm

Use the current v3.1 report contract. It includes longitudinal facts, measurements, provenance, image and timeline
pathway outputs, combined score, conformal outcome-label set, agreement statement, evidence tier, and relevant
model-derived warning fields.

### Strict facts-only arm

Use the same patient/scan, longitudinal non-model context, segmentation-derived measurements, display image,
past-scan changes, treatment facts, data-availability/provenance fields, report layout, writer configuration and
word-budget target as the full-evidence arm. Exclude all prediction-derived content:

- image, timeline and combined scores or probabilities;
- conformal sets and any prediction uncertainty;
- pathway agreement/disagreement;
- reliability-card tiers or model-derived out-of-distribution and warning fields;
- descriptions of model inputs, model use, or score interpretation.

Pure data-completeness/provenance statements that do not depend on a model output remain allowed. The facts-only
prompt must not infer a progression conclusion from measurements. It must state that the report contains descriptive
longitudinal information only, where that clarification is needed for faithful rendering.

## Population and pairing

Use the existing v3.1 held-out evaluation population: 406 records (MU 114, LUMIERE 162, UCSF 130), subject to a
pre-run manifest confirming membership and record hashes. Generate both arms from each exact record. Use the same
pinned writer model, decoding settings, prompt version, renderer and compute environment unless the arm-specific
field contract requires a documented change.

The full-evidence reports may be regenerated rather than copied, but the run must verify that the full-arm grounding
and required-content results reproduce the v3.1 baseline before any arm comparison is interpreted.

## Implementation contract

1. Freeze a versioned field manifest, prompts, record manifest, writer configuration and checker rules before
   generation.
2. Implement arm-specific facts builders, prompts, deterministic sections and checker contracts. Do not implement
   the facts-only condition by deleting text after a full report is generated.
3. Require every report to include the shared factual fields specified in the manifest. Require the full arm to
   include its model-evidence fields. Require the facts-only arm to contain no forbidden model terminology or
   values.
4. Preserve all report text, checker output, generation metadata, hashes and failures in a new ablation output
   directory. Existing v3.1 files remain immutable.
5. Add unit tests for field partitioning, checker contracts, forbidden model leakage and paired-record alignment.

## Outcomes and analysis

### Automatic primary outcomes

- Report-level grounding pass rate under the arm-specific checker.
- Required shared-fact coverage in both arms.
- Required model-evidence coverage in the full-evidence arm.
- Forbidden model-field leakage in the strict facts-only arm.

### Automatic secondary outcomes

- Unsupported statements, omissions, malformed/truncated reports and generation failures.
- Paired report length, estimated reading time, generation runtime and cost.
- Response to controlled perturbations: shared factual fields perturbed in both arms; model fields perturbed only in
  the full-evidence arm.
- Cohort-stratified results, with thin-evidence and flag status reported only for the full-evidence arm.

Analyse paired differences with patient-cluster bootstrap confidence intervals where the outcome permits. Report
denominators and all failures. No automatic metric is called usefulness or clinical benefit.

## Interpretation rules

- If both arms are equally well grounded, the result shows that removing model fields does not by itself break
  generation; it does not establish that model fields lack clinical value.
- If the full arm adds grounded model-specific content, the result supports only that it exposes additional model
  evidence faithfully.
- If the facts-only arm has lower failure, cost, or length, report that trade-off without treating it as a failure of
  the full arm.
- No outcome justifies a claim about clinician decisions or patient benefit.

## Manuscript decision after results

Include the ablation only if it is reproducible, paired, transparent about its automatic scope, and supports a
compact answer to: “what extra grounded information do model fields add to the report?” Otherwise retain the
current limitation that the incremental report value of model fields is untested.

## Future clinical study

A reader study would compare matched full-evidence and strict facts-only reports using held-out cases, balanced
case--arm assignment, blinded conditions and prespecified clinician-facing endpoints. It is a separate study and is
not a fallback interpretation of this automatic ablation.
