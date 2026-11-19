# Locked text

Passages the author has approved. They are not changed without the author's explicit approval, not even for
polish. If a later result or a number check makes a locked passage wrong, flag it to the author and propose the
smallest edit; do not rewrite it.

## Abstract (locked 2026-11-18; 149 words; replaces the 2026-10-24 version)

A score for a follow-up MRI after glioma treatment is useful only if the reader can see what it rests on, and a generated report only if each statement can be checked against the record. PRISM is a local system built for both. It scores each scan with separate imaging, clinical-history and combined models, keeps every value in one record with its source, and a local language model writes a report checked against it. The separation exposed what a single score would hide. On MU-Glioma-Post, the time after radiotherapy and the enhancing tumour carried most of the ranking, and the combined model added no clear gain over a baseline of the two (AUC 0.80). Applied unchanged, the reduced combined model reached 0.77 at LUMIERE and 0.86 at UCSF-ALPTDG. All 406 reports for held-out patients passed the record check, and a verifier rejected every value placed under the wrong region.

Sources: METHODS_RESULTS.md E4 (0.80, no clear gain); NUMBERS.md 4 (0.77, 0.86); NUMBERS.md 7 (406, patients not
used to develop the prompt); Section 4.5, Table 5 (verifier). Development history (the prompt revision) belongs in
Methods, not the abstract.
