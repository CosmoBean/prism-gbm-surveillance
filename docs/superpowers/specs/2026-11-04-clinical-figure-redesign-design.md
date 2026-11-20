# Clinical figure redesign

## Intent

Replace the rigid system-flow presentation with two figures that make the scan-level clinical question visible before
they explain the machinery. The figures must remain scientifically bounded: they illustrate an evidence record and a
checked report, not a diagnostic decision engine or validated clinical workflow.

## Scope

- Redesign the cited `fig1_system` and `fig5_report` displays only.
- Preserve Figures 2--4 as data-bearing plots. Their data, labels, scales, and output files are not in scope.
- Use synthetic MRI illustrations and synthetic values only. Do not use patient images or invent outcome claims.
- Preserve the current document's monochrome-forward, journal-ready visual language, with restrained pathway colours.

## Visual approach selected

The redesign centers one follow-up scan. It moves from the scan and treatment course to separate image and treatment
evidence, then to the report a clinician would read. The record and automatic check remain visible but secondary.

Figure 1 becomes an editorial clinical narrative rather than a box-and-arrow architecture diagram. Figure 5 becomes
a readable report excerpt with the report-check result visually subordinate to the clinical artifact.

## Implementation choices

- Create versioned source scripts and versioned preview assets first; do not overwrite the existing figure source or
  cited files until a visual review selects them.
- Generate any new raster illustration as a synthetic, non-patient, no-text asset. Integrate labels and numerical
  content in the existing Matplotlib pipeline, where they remain auditable.
- Keep the existing synthetic values and all report-check counts unchanged.

## Acceptance criteria

1. A reader can identify the clinical question and the distinction between image and treatment evidence within a few
   seconds.
2. The figures do not resemble generic software architecture or a decorative medical illustration.
3. Every number, cohort name, and methodological claim remains generated from manuscript-controlled source code.
4. The final assets are suitable for PDF submission and retain accessible contrast and legible typography.
