# Locked text

Passages the author has approved. They are not changed without the author's explicit approval, not even for
polish. If a later result or a number check makes a locked passage wrong, flag it to the author and propose the
smallest edit; do not rewrite it.

## Abstract (approved 2026-11-20; 145 words; replaces the 2026-11-18 version)

Follow-up MRI after glioma treatment is difficult because progression and treatment effects can look alike. We developed PRISM, a local system for follow-up MRI. PRISM includes a Swin UNETR segmenter; primary analyses used the masks released with each cohort. It measures tumour volume and change from the current and earlier masks. Three ridge logistic-regression models separately score imaging measurements, clinical history, and their combination. The combined score receives a split-conformal uncertainty set. A local language model writes a report from the structured record, and deterministic rules check its claims against the source fields. On MU-Glioma-Post, time after radiotherapy and enhancing tumour carried most of the ranking, and the combined model added no clear gain over the timing-and-enhancement baseline (AUC 0.80). Applied unchanged, the reduced combined model reached 0.77 at LUMIERE and 0.86 at UCSF-ALPTDG. All 406 held-out reports passed the record check.

Sources: METHODS_RESULTS.md E4 (0.80, no clear gain); NUMBERS.md 4 (0.77, 0.86); NUMBERS.md 7 (406, patients not
used to develop the prompt); Section 4.5, Table 5 (verifier). Development history (the prompt revision) belongs in
Methods, not the abstract.
