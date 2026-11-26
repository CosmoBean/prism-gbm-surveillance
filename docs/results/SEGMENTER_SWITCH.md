# Decision: PRISM's own segmenter becomes the primary pipeline (2026-11-20)

Author's decision, 2026-11-20, after the S4 results ([SEGMENTER_BRATS24.md](SEGMENTER_BRATS24.md), commit 24059e9).
Recorded before any rerun.

## Decision

- **Segmenter:** the BraTS 2024 first-place model (BraTS24_1), as in S4, replaces the released masks as the source of
  every imaging input in the primary analyses. PRISM then runs end to end from the MRI.
- **Inputs:** the 22 cavity-free segmenter inputs (S4's exploratory arm `segmenter22`), not the planned 27.
- **Reference analysis:** the released-mask results, as published so far, are kept and reported as the reference
  ("PRISM with expert-corrected masks").

## What was known when deciding

- S4's planned rule failed: MU time-and-enhancement −0.017 (−0.037 to −0.003), and the LUMIERE gain reading changed.
- The 22-input arm was chosen **after** seeing that the cavity inputs lowered the BraTS24 results:
  - MU imaging 0.68 → 0.71;
  - LUMIERE reduced combined 0.75 → 0.79.
- That is a post hoc choice and must be stated as such wherever the primary results are reported.
- Training overlap: BraTS 2024 training includes UCSF data (confirmed) and University of Missouri data (MU overlap
  possible, not established). No progression label was used to train the segmenter.

## Rules for the rerun

1. **Nothing else changes:** models, folds, seeds, conformal levels, card rules, prompts, checker and verifier (frozen
   hashes in `report_v3_2/FROZEN_hashes.txt`).
2. **Only the measurement source changes.**
3. **No further changes chosen on the rerun's results.** Any later change is a new dated entry here.
4. **Paper reporting:** the paper reports both sets:
   - primary: the segmenter;
   - reference: the released masks;
   - S1 and S4 stay in the supplement;
   - the switch and the post hoc input choice are stated in Methods.

## To rerun

- The system records for all three cohorts: scores, conformal sets, cards and flags.
- The reports (Qwen3.8-27B), the checker and the verifier.
- Figures 3–8, S1 and S2, and every number in the Results.
- Changing the segmenter's name in the abstract needs author approval (LOCKED.md).

## Deviations during the rerun

- **2026-11-20, report freeze.** The `freeze` step was run after generation by mistake, and its guard refused to
  run.
  - The five frozen files (facts and prompts v3.1/v3.2, checker) were checked to have the same git blob hashes as
    the original freeze of 2026-11-13.
  - That original `FROZEN_hashes.txt` was copied into `report_v3_2_brats24_22/` instead of writing a new one.
- **2026-11-20, model descriptions in the switched records.** In segmenter mode the records described the models
  with new names that the report facts did not recognise.
  - The combined model was described with the clinical-history text, and the imaging model with a non-standard text.
  - The checker passed those reports because they matched their records.
  - Fix: the switched model names now start with the released-mask model keys, so they map to the same "based on"
    texts (`system.py`).
  - Records were rebuilt and the reports regenerated. The superseded run is kept in
    `report_v3_2_brats24_22/_superseded_based_on_bug/`.
