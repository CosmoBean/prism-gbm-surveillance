# Novelty search: what in the PRISM framework is new (2026-11-12)

Why: the professor asked what is novel in "the framework" contribution. Two web research agents searched; key IDs
were then checked by us (Crossref for DOIs, arXiv API for preprints), marked [V]. No patient data used. Searches
were not exhaustive (MICCAI, CHIL, ML4H proceedings and 2026 preprints are thin).

## Closest prior work

| Work | What it does | Closeness to PRISM |
|---|---|---|
| Gomaa 2025, Sci Rep, 10.1038/s41598-025-02026-7 [V] (already cited) | Pseudoprogression; clinical only AUC 0.727, image only 0.717, multimodal 0.753; SHAP says time since RT dominates | Closest in the field. Cohort level, one cohort, treats timing as valid signal, nothing per scan |
| Badgeley 2019, npj Digit Med, 10.1038/s41746-019-0105-1 [V] (already cited) | Hip fracture score explained by patient and process variables; AUC falls on a matched test set | Same idea (non-image variables explain an image score), cohort level |
| Lotfinia 2026, arXiv:2606.17710 [V] | Chest X-ray VLMs; text only baselines match, "accuracy alone is not sufficient evidence" the image is used | Same message, different method (image swap, occlusion) |
| Jang 2018 Sci Rep 10.1038/s41598-018-31007-2 [V]; Jang 2020 Cancers 10.3390/cancers12092706 [V] | Pseudoprogression with clinical and MRI inputs; 2020 uses time since CRT as a feature | Modality comparison at cohort level only |
| Han 2023, TPAMI, 10.1109/TPAMI.2022.3171983 [V] | Per sample conflict between views as uncertainty | Mechanically closest per case signal; aim is fusion and noise, not confounding |
| Zech 2018, DeGrave 2021, Oakden-Rayner 2020 (10.1145/3368555.3384468 [V]), Geirhos 2020 | Shortcut and hidden stratification audits | Background for the audit framing |
| Romano 2020 HDSR 10.1162/99608f92.03f00592 [V]; Lu 2022 arXiv:2109.04392 [V] | Group conditional (equalised) conformal coverage; medical imaging case | Theory for per stratum coverage |
| Mehrtens 2025, arXiv:2506.18162 [V] | Conformal coverage breaks under shift and on subsets in medical imaging | Reviewers will cite it; expect stratum wise coverage at external sites |
| Olsson 2022, Nat Commun, 10.1038/s41467-022-34945-8 [V] | Conformal in pathology, flags unreliable cases and shift | Per case conformal with external validation |
| Sendak 2020, npj Digit Med, 10.1038/s41746-020-0253-3 [V] | Model facts label | Static, per model; PRISM's card is per scan by stratum |
| BTReport (herasrivera2026), arXiv:2602.16006 [V] (already cited) | LLM report from deterministic tumour features on BraTS | Closest report design; no number checker seen in the abstract (full text not read) |
| FactCheXcker, arXiv:2411.18672 [V] | Detects and repairs measurement hallucinations in CXR reports | Numeric fidelity by repair, not rejection against a typed record |

Found nothing: conformal prediction for post-treatment glioma progression; any pseudoprogression ML paper warning
that time since RT is a shortcut; any cross-cohort comparison showing the support for a score changes at similar AUC.

## Assessment

Established, so not to be claimed: that non-image variables can explain an image score; that a clinical baseline can
match imaging in pseudoprogression; per sample modality conflict; group conditional conformal; LLM reports from
deterministic features.

Appears new, and is what the contribution should claim:
1. Pathway restricted models used as an audit instrument for what a score rests on, not as ablations.
2. The finding that the support changes across cohorts at similar AUC (timing at MU, enhancing volume at UCSF).
3. Per scan image versus timeline agreement as a flag for dependence on treatment timing.
4. The combination with a per scan conformal set and a stratified reliability card for longitudinal surveillance
   (integration, not new conformal method).
5. Rejection (not repair) of any report whose numbers or flags are absent from the typed record. Frame as a safety
   property, not a method advance.

Positioning: build on Gomaa and Badgeley explicitly. Present timing as dependence the clinician should see, not as
error, since timing is real clinical signal (the 12 week rule).
