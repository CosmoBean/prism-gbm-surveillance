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

## Second pass (same day): venues, report checking, per scan confidence

Three more web agents filled the first pass's gaps. [V] as above; [U] not verified. MICCAI, MIDL, ML4H and CHIL
were still searched only through general web search, not a proceedings sweep.

### What a score rests on
| Work | What it does | Effect on the claim |
|---|---|---|
| Brima et al. 2026, arXiv:2609.12410 [V] | Alzheimer's; image only, tabular only and fusion on ADNI vs OASIS-3; clinical strongest in one cohort, image in the other; argues external validation should check the evidence, not only discrimination | Anticipates the cross-cohort finding in another disease. Cite; claim the first demonstration in longitudinal oncology surveillance, with pathway models as the audit |
| D'Amour et al. 2022, JMLR, arXiv:2011.03395 [U] | Underspecification: equal AUC, different behaviour | General precedent |
| Gapp et al. 2025, IJCARS, 10.1007/s11548-025-03523-w [V] | Modality contribution by occlusion; unimodal collapse | Per dataset, not across cohorts |
| Ahadian et al. 2026, arXiv:2604.16333 [V]; Pierson et al. 2021, Nat Med, 10.1038/s41591-020-01192-7 [V] | Per patient discordance between image predicted and reported pain | Closest to the agreement flag. Narrow the claim to agreement of two predictive pathways for one endpoint, against cohort medians |
| Guo and Mirzaei 2025, Cancers, 10.3390/cancers18010036 [V] | GBM follow up deep learning benchmarked per timepoint | Supports "timing matters"; no timing baseline |
| Tikhonov et al. 2025, arXiv:2509.06511 [U] | Response prediction from volume change plus radiomics, LUMIERE | Likely the open "Tikhonov" reference; no pathway split |

Still nothing: a pseudoprogression paper beyond Gomaa that treats time since RT as a shortcut; image and clinical
scores shown side by side to a clinician. Unread (paywalled): "Explainable radiomics with probability calibration
for postoperative glioblastoma surveillance", ScienceDirect pii S3050577126000058.

### The report and its check
| Work | What it does | Effect on the claim |
|---|---|---|
| BTReport, arXiv:2602.16006 [V], full text read | Local gpt-oss-120b and Llama 3.1 70B; features computed upstream; no check of the generated text; one preoperative timepoint; no uncertainty | PRISM differs in the check, follow up and confidence content |
| Pham et al., EMBC 2026, "Evidence-Augmented Conformal Risk Control with Verifier-Gated LLM Reporting" [U, author PDF only] | ECG; local Phi-3-mini, sampling off; conformal set is the only diagnostic content; verifier rejects, one repair, then template fallback; bans numbers | Closest of all. Must be cited and contrasted: PRISM checks numbers against a typed record, never repairs, reports a pass rate, adds pathway agreement and a reliability card, imaging follow up |
| Mansour et al. 2026, arXiv:2610.34599 [V] | Liver lesions; numbers checked against measurement JSON, flagged for review | Numeric check against source is established |
| Maeng et al. 2026 STRIVE, arXiv:2608.24237 [V]; FactCheXcker, arXiv:2411.18672 [V] | Consistency gate or repair | Repair, not rejection |
| Zeba et al. 2025, arXiv:2512.16189 [V] (zeba2026 in refs.bib) | LLM free fact check of EHR summaries, per claim | Per claim labels |
| RadFact arXiv:2406.04449, GREEN arXiv:2405.03595, RaTEScore arXiv:2406.16845 [V] | Evaluation metrics | Not generation time checks |
| CONRep arXiv:2602.03910 [V]; Mohri and Hashimoto arXiv:2402.10978 [V] | Conformal over generated claims | Not a prediction set shown in the report |
| Jabal 2026, Radiology AI, 10.1148/ryai.260234 [V] (jabal2026) | Multi-agent BT-RADS on 492 follow up exams; category only | Main clinical task competitor; no uncertainty or check |
| Laukamp 2024, Radiology, 10.1148/radiol.232640 [V] | Hosted GPT-4 summarises GBM report histories | No check |

### Per scan confidence
| Work | What it does | Effect on the claim |
|---|---|---|
| CONSeg, Elyassirad 2025, AJNR, 10.3174/ajnr.A8914 [V] (elyassirad2025) | Voxelwise conformal for glioma segmentation, external UPenn | Glioma conformal, not progression |
| Angelopoulos et al. 2024, medRxiv 10.1101/2024.02.09.24302543 [V] | Conformal triage of head CT under deployment shift | Nearest neuroimaging precedent |
| Zhong et al. 2026, arXiv:2608.04254 [V] | Marginal coverage hides subgroup under coverage, ADNI and OASIS-3 | Justifies per stratum coverage and the few cases rule |
| Nicora et al. 2022, J Biomed Inform, 10.1016/j.jbi.2022.103996 [V] | Pointwise reliability by local fit to similar training cases | Same idea as the card, similarity in feature space |
| Cabitza et al. 2026, Artif Intell Med, 10.1016/j.artmed.2026.103366 [V] | Local predictive value near a case's confidence | Lookup by score, not clinical context |
| Kompa 2021 npj Digit Med 10.1038/s41746-020-00367-3 [V]; Dvijotham 2023 Nat Med 10.1038/s41591-023-02437-x [V] | Argument for per case uncertainty; learned deferral | Background |

Nothing found: conformal or abstention for glioma progression or pseudoprogression; one output combining a set, an
agreement flag and a subgroup lookup. To check by hand: UCSF news 2026-07, "Can uncertainty scores help experts
trust AI brain tumor analysis?" (page blocked, paper not identified).

### Revised assessment
- Strongest claim, unchanged: pathway restricted models as an audit of what a score rests on, and the finding that
  the support shifts between cohorts at similar AUC in glioma surveillance. Cite Brima 2026 and D'Amour 2022 so the
  claim is "first shown here with this instrument", not "first observed".
- Agreement flag: claim the narrow form; cite Ahadian 2026 and Pierson 2021.
- Confidence: an integration of established tools. New in application: first conformal set per follow up scan for
  glioma progression, one calibration carried unchanged to two external cohorts, clinically defined strata, the
  10 per outcome rule. State that coverage is marginal and cite Mehrtens 2025 and Zhong 2026.
- Report: incremental. Cite and contrast Pham 2026 (ECG). Claim whole report rejection against a typed record with
  no repair, and the population pass rate, as a safety property.
