# Reference check of the Introduction (2026-11-20)

**Method.** The 49 references cited in the Introduction were checked by two independent agents each. Each confirmed
existence (DOI, Crossref, PubMed or arXiv) and read the abstract or full text against every sentence that cites the
work. A verdict stands only where both agreed; disagreements were checked by hand.

**Result.** All 49 exist, and no reference is fabricated. Four bibliography author names were wrong and are now
corrected:
- mehrtens2023: Tabea-Clara Bucher;
- zeba2026: Debopom Sutradhar;
- prucker2025: Mateo Jukic;
- deverdier2024: Correia de Verdier.

The 30 test patients of christodoulou2026 are confirmed from the authors' public code (`N_TEST_PATIENTS = 30`); see
CHRISTODOULOU_REPLICATION.md.

**Note on the group files.** The group*.md files list rudin2019, kwon2023 and pedregosa2011 as missing from refs.bib.
They are not missing; the extraction script mis-parsed them.

## Sentences that need a fix (both checkers agree)

| Key | Problem | Fix |
|---|---|---|
| ostrom2023 | "Gliomas … most common … in adults" and "most aggressive" are not stated; the 50.9% is for all ages | Gliomas are about a quarter of all primary brain tumours, and glioblastoma about half of the malignant ones |
| taal2008 | The counts are patients, not scans | "half of the patients whose first scan looked progressive had pseudoprogression" |
| taylor2022 | The AUCs were pooled from 25 of 30 studies (0.90–0.93); 13 studies were at high risk of bias; post hoc cut-offs | "a meta-analysis of 30 small studies, 13 at high risk of bias … pooled AUCs of 0.90–0.93" |
| leone2023 | "Added nothing" overstates the result: AUC 0.69 → 0.71, not significant; patients with suspected pseudoprogression | "did not significantly improve on" |
| gomaa2025 | Two results are merged: the time ranking is among clinical inputs on internal CV; externally, clinical alone matched images | Split the sentence |
| rudin2019 | Rudin argues for models interpretable by design, not for "inputs read directly" | Reword |
| hoebel2024 | The paper is about experts' disagreement on segmentation quality; the clause about volumes goes further | Mark that clause as our inference |
| hatamizadeh2022 | Swin UNETR has no cavity class; the BraTS 2024 model is uncited | Say which model segments what; cite ferreira2024 |
| thust2018 | 60% assessed scans qualitatively, which is not the same as "free text" | "60% assessed them qualitatively, 27% applied RANO, 23% used a template" |
| zhang2020 | Word counts; the only treatment term was Avastin | "mentioned bevacizumab and MGMT status more often" |
| gore2019 | Respondents included radiologists and care providers | "clinicians and radiologists who care for these patients" |
| valerio2025, herasrivera2026 | The clause "they make errors" sits next to papers that claim fewer errors | Move the clause next to tanno2025 and prucker2025 |
| gabriel2021 | The paper shows metrics track human judgement poorly, not that they disagree | Reword |
| rao2025rexerr | One method for planting errors in chest X-ray reports | "errors can be planted in reports to test such checkers" |
| mukherjee2023 | No comparison with closed models; that comparison is nowak2025 | Split the citations |
| yu2022, tanno2025 | Scope is deep learning diagnosis and chest radiographs | Add the scope |

**Primary not readable:** weinberg2018 (paywalled). It is supported by a later BT-RADS validation study. Confirm with
journal access.
