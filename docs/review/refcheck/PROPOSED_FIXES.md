# Introduction: proposed sentence fixes from the reference check (2026-11-20)

All 49 references in the Introduction exist and were checked twice, independently. The full verdicts are in
[RESULTS.md](RESULTS.md). Four author names in `paper/refs.bib` are already corrected (commit 6c05632). The sentences
below said more than their source. **All 15 were applied on 2026-11-20** in the Introduction rewrite.

| # | Key | Current text | Proposed text | Why |
|---|---|---|---|---|
| 1 | ostrom2023 | "Gliomas are the most common malignant primary brain tumours in adults, and glioblastoma, the most aggressive of them, accounts for about half of all malignant primary brain tumours" | "Gliomas make up about a quarter of all primary brain tumours, and glioblastoma alone about half of the malignant ones [ostrom2023]." | The registry gives 26.3% (gliomas) and 50.9% (glioblastoma), for all ages. It does not say "in adults" or "most aggressive"; the survival sentence that follows shows the aggressiveness. |
| 2 | taal2008 | "half of the scans that looked progressive were not" | "half of the patients whose first scan looked progressive had pseudoprogression [taal2008]" | The counts are patients (18 of 36), not scans. |
| 3 | taylor2022 | "Across 30 studies, diffusion and perfusion imaging separated pseudoprogression from progression with pooled AUCs near 0.9" | "In a meta-analysis of 30 small studies, 13 at high risk of bias, diffusion and perfusion MRI reached pooled AUCs of 0.90–0.93 [taylor2022]" | The AUCs were pooled from 25 of the 30 studies (DWI 0.93, DSC 0.93, DCE 0.90); 13 of 30 studies were at high risk of bias, with cut-offs chosen post hoc. The review does not restrict itself to enlarging lesions. |
| 4 | leone2023 | "they added nothing to clinical data and MGMT status" | "in 105 patients with suspected pseudoprogression, they did not significantly improve on clinical data and MGMT status [leone2023]" | AUC 0.69 → 0.71, P = 0.42; the cohort had suspected pseudoprogression. |
| 5 | gomaa2025 | "Where clinical inputs were compared with images on external data, the time since treatment was the strongest single input" | "On an external test set, a model of clinical data alone matched one using MRI, and the time from treatment to progression was its most influential input [gomaa2025]" | The time ranking is among clinical inputs on internal cross validation. On the external set, clinical alone gave 0.73 and MRI alone 0.72. |
| 6 | rudin2019 | "a model whose inputs can be read directly is preferable" | "a model that is interpretable by design is preferable to a black box explained after the fact [rudin2019]" | Rudin's argument. |
| 7 | hatamizadeh2022, ferreira2024 | The segmentation sentence implies Swin UNETR outlines the resection cavity; the BraTS 2024 model has no citation | "…either a Swin UNETR trained on BraTS 2021 [hatamizadeh2022], which marks the enhancing tumour, necrosis and FLAIR hyperintensity, or the first-placed BraTS 2024 post-treatment model [ferreira2024], which also marks the resection cavity…" | Swin UNETR has no cavity class. |
| 8 | thust2018 | "of 220 European centres, 60% reported them in free text and 27% applied RANO" | "of 220 European centres, 60% assessed them qualitatively, 27% applied RANO and 23% used a reporting template [thust2018]" | The survey says "qualitative assessment", not free text. |
| 9 | zhang2020, gore2019 | "reports more often recorded treatment and MGMT status and were rated more consistent by referring clinicians" | "reports mentioned bevacizumab and MGMT status more often [zhang2020] and were rated more consistent by the clinicians and radiologists caring for these patients [gore2019]" | zhang2020 counted words, and its only treatment term was Avastin. gore2019 surveyed radiologists and care providers. |
| 10 | valerio2025, herasrivera2026, tanno2025 | "Language models now draft reports … but they make errors a reader may not catch." | End that sentence after the citations. Start the next: "Such reports can contain errors a reader may not catch: AI-written chest radiograph reports contained clinically significant errors [tanno2025], …" | The cited systems claim fewer errors, so the clause must sit next to the sources that show errors. |
| 11 | gabriel2021 | "Automatic measures of factual accuracy disagree with one another" | "Automatic measures of factual accuracy track human judgements of factuality poorly [gabriel2021]" | The paper tests each metric against human judgement, not against other metrics. |
| 12 | rao2025rexerr | "checkers for radiology reports are tested on planted errors" | "errors can be planted in radiology reports to test such checkers [rao2025rexerr]" | One method, for chest X-ray reports. |
| 13 | mukherjee2023, nowak2025 | "open-weight models run on site now read radiology reports as well as closed ones [mukherjee2023, nowak2025]" | "open-weight models run on site can label radiology reports [mukherjee2023] and extract their findings as well as closed models [nowak2025]" | mukherjee2023 compared a local model with non-LLM labelling tools; the comparison with closed models is nowak2025. |
| 14 | yu2022 | "most radiology algorithms lose performance on external data" | "most deep learning algorithms for radiological diagnosis lose performance on external data [yu2022]" | Scope of the review. |
| 15 | hoebel2024 | "Experts disagree about the quality of the same glioma segmentation, so a volume measured from one set of outlines may not match another, even between scans a few weeks apart." | "Experts disagree about the quality of the same glioma segmentation [hoebel2024], so measured volumes depend on whose outlines are used." | The source covers experts' disagreement on quality. The rest is our inference, now stated as one. |

## Open points for the author

1. **christodoulou2026, "30 held-out patients".** The abstract gives no number. The 30 comes from the authors' public
   code (`N_TEST_PATIENTS = 30` in `rank_and_split__4.py`, seed 42; see `docs/results/CHRISTODOULOU_REPLICATION.md`).
   The full text was not reachable. Either keep "30 held-out patients" and confirm against the PDF, or write "a
   held-out set of 30 patients in the authors' public code".
2. **weinberg2018 (BT-RADS).** Paywalled. The claim was confirmed only through a later BT-RADS validation study.
   Confirm with journal access.
3. **Next.** Run the same double check on the references cited in Methods, Results and Discussion.
