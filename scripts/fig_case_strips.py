"""PLANNED figure: case strips (what each score says at each visit), modelled on Tak et al. 2025 (NEJM AI) Figure 4.

STATUS (2026-11-18): spec and skeleton only. Not run. Finish on orchard, where outputs/ exists.

Example paper and notes
  Tak D et al. Longitudinal risk prediction for pediatric glioma with temporal deep learning. NEJM AI 2025;2(5).
  doi:10.1056/AIoa2400703. NIH author manuscript PMC12176428.
  - Full text and figures (local only, gitignored): docs/literature/examples/tak2025_nejmai.md, tak2025_figures/
    (their Figure 4 is nihms-2086176-f0004.jpg). To fetch them on another machine, see
    docs/literature/examples/README.md.
  - What to take from it, figure by figure: docs/literature/examples/tak2025_NOTES.md ("Figures" table, row Fig 4).

What their Figure 4 does
  Each patient is one rounded box: a header strip (sex | resection status | recurrence true/false), a row of real
  axial slices with "N Days" brackets between consecutive scans, a red arrow on the lesion in the first slice, and
  under each scan a colour cell holding the predicted 1-year risk (diverging blue-to-red map, value printed in the
  cell), ending in an EVENT marker. A shared colour bar sits at the right. Four patients: two with an event, two
  without.

The PRISM version
  - 3 or 4 patients from MU (or LUMIERE) records. Include at least one with progression, one without, and one where
    the imaging and clinical-history models disagree. Pick by a written rule (e.g. the first patient in ID order
    meeting each condition) and state it in the caption, as fig1_prism.py states its patient.
  - Header strip per patient: cohort | grade | progression documented (yes/no) | MGMT.
  - Row of T1c slices (the slice with most enhancement in each scan, enhancing outline in figure_style CONTOUR; reuse
    patient_scans()/show_scan() from scripts/fig1_prism.py). Over each scan: weeks after the end of radiotherapy.
    Shade scans inside the first 12 weeks, as Figure 1a does.
  - Under each scan, THREE cells instead of Tak's one: clinical-history, imaging and combined score, each in its house
    colour (figure_style HIST, IMG, COMB), with the cell's lightness set by the score and the value printed. To the
    right of the three cells, the 80% conformal set of the combined score ({0}, {1} or {0,1}), and a mark when the
    models disagree (agreement statement false).
  - Label under the row: "Progression" at the documented scan, "No progression" if >= 120 days without progression
    after it, otherwise "Not labelled" (same rule as Figure 1a).
  - No diagnosis wording anywhere. The scores rank scans; they are not probabilities for this patient.

Data on orchard
  - Per-scan records (scores, conformal set, agreement, card): outputs/results/analyses/system/<cohort>.jsonl,
    written by prism/analyses/system.py (write_records; RECORDS_READY lists the files and counts). Key names as in
    Figure 1b: model.imaging.score, model.clinical_history.score, model.combined.score,
    conformal.combined.80.*, models.agreement_statement (check the schema in system.py before relying on them).
  - Images and masks: prism.config.mu_scan_paths(patient_id, timepoint) (MU), LUMIERE via prism.data.
  - Clinical dates for weeks after RT: prism.data.mu.load_clinical().

Checks before it goes into the paper
  - Every score shown must equal the record value (assert, as fig2_performance.py's sources are checked).
  - The scores must be out-of-fold (MU) or locked (LUMIERE): never in-sample.
  - Add a \\figslot in paper/main.tex (a commented placeholder is there, after Figure 2) and a caption that states the
    patient-selection rule.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RECORDS = REPO / "outputs" / "results" / "analyses" / "system"


def load_records(cohort: str) -> list[dict]:
    """One dict per scan from the system records (see the docstring for the keys to check)."""
    with open(RECORDS / f"{cohort}.jsonl") as f:
        return [json.loads(line) for line in f]


def pick_patients(records: list[dict]) -> list[str]:
    """TODO: the written selection rule (progression / no progression / models disagree)."""
    raise NotImplementedError


def draw(output: Path, cohort: str) -> None:
    """TODO: one strip per patient, as specified above; save with figure_style.save(fig, output, "fig_case_strips")."""
    raise NotImplementedError


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--cohort", default="mu")
    p.add_argument("--output", type=Path, default=REPO / "docs/manuscript/figures")
    a = p.parse_args()
    draw(a.output, a.cohort)
