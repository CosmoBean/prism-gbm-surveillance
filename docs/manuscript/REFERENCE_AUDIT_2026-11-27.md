# Reference audit 4 (2026-11-27): report only, nothing fixed

The fourth independent audit of the bibliography. It was run on commit `caf5944`. **Line numbers below are for
`f651e59`** (main.tex), and each item also quotes its clause, so it can be found with grep if lines move. Nothing in
the paper was changed. The author or the content session applies the fixes.

**How it was run.** Seven fresh agents each took a shuffled share of the 94 cited keys and all 164 uses (136 of them in
main.tex). For each key they checked:
- that the DOI or URL resolves and the metadata are right (Crossref, DataCite, arXiv, PubMed/PMC, publisher pages,
  Hugging Face cards);
- that the work is real;
- that the source supports each use separately, on the exact clause the citation sits on.

An eighth agent went through main.tex sentence by sentence. It looked for:
- uncited claims, tools, datasets and models;
- citations sitting on the wrong clause;
- `\ref` and `\cite` problems;
- references to the supplement.

The per-agent reports are in the appendix. Where I differ from an agent, the suggestion marked **Suggested** is mine.

**Clean.**
- No undefined or duplicate cite keys, and no undefined `\ref` or duplicate `\label`.
- main.tex has no reference to the supplement outside `%` comments.
- Every work exists, and every DOI or arXiv ID resolves to the work named. There are no wrong DOIs.

---

## A. Locked wording (LOCKED.md): the author decides

`check_locked.py` fails the build if these change, so each edit must be made in LOCKED.md as well, in the same commit.

**A1. L38 (abstract) and L157–158, christodoulou2026.** The text says "up to 1.00 (mean 0.84) on single held-out splits
of 18 patients, the design of earlier studies on this cohort".
- *Problem:* the cited study held out **30** patients (see L74), and 18 of 92 is PRISM's own re-implementation.
  "Studies" is plural but there is one source. Two agents independently rated this WRONG.
- **Suggested for the abstract:** "the design of an earlier study".
- **Suggested for L158:** "…and up to 1.00 (mean 0.84) over 100 random held-out sets of 18 patients, an analogue of the
  single held-out design of an earlier study on this cohort \citep{christodoulou2026}".

**A2. L486–489, christodoulou2026.** The text reads "For comparison with studies evaluated on one held-out split
\citep{christodoulou2026}, … drawn as in an earlier re-implementation of that study (exploratory)."
- *Problem:* "studies" is plural with one source. "An earlier re-implementation" reads as published work, but it is
  the authors' own and is described only in the supplement, which is not submitted.
- **Suggested:** "For comparison with a study evaluated on one held-out split \citep{christodoulou2026}, … drawn as in
  our re-implementation of that study (exploratory)." Also see B1.

**A3. L71, zhang2026meta.** The text reads "In a meta-analysis of 31 studies, models tested at another institution
reached a pooled AUC of 0.81, against 0.91 at the institution that developed them."
- *Problem:* the 0.81 pools **7 external test cohorts** (219 observations), not the 31 studies. The task is true
  progression versus pseudoprogression in glioblastoma. Source: "Seven external test cohorts, including 219 patient
  observations, entered the primary meta-analysis … AUC was 0.81 … Internal test cohorts showed higher apparent
  performance … (0.91 vs 0.81), but the difference was not statistically significant (P = 0.12)."
- This was flagged in audits 3 and 4.
- **Suggested:** "In a meta-analysis of 31 studies separating true progression from pseudoprogression, seven external
  test cohorts gave a pooled AUC of 0.81, against 0.91 for internal test cohorts \citep{zhang2026meta}."
- Whether to add "a difference that was not statistically significant" is the author's call. It is accurate, but it
  weakens the contrast.

**A4. L40 (abstract) and L163–164, zhang2026meta.** The text reads "against a pooled AUC of 0.81 for earlier models
tested at another centre/institution".
- *Problem (MINOR):* the earlier models do a different task.
- **Suggested for L164:** "…for earlier models separating true progression from pseudoprogression at another
  institution \citep{zhang2026meta}".
- The abstract has a 150-word limit, so it may keep its wording if L164 carries the precise version.

## B. Must fix (unlocked)

**B1. L593 and L851: an unsourced result.** L593: "Over 100 random held-out sets of 18 of the 92 grade 4 patients, an
earlier re-implementation of the radiomics model ranged from 0.32 to 0.88 (mean 0.63)". L851: "An earlier
re-implementation of that model ranged from 0.32 to 0.88 over random held-out sets."
- *Problem:* "earlier" implies prior published work, and the re-implementation is described only in the unsubmitted
  supplement. Agents in two batches and the sweep flagged it.
- **Suggested:** make it the authors' own analysis and point to the Methods paragraph that already describes running
  the authors' code (L505–516). For example: "PRISM's re-implementation of that model (Section~\ref{…}) ranged
  from 0.32 to 0.88…". Make the same change at L851.

**B2. L858, gomaa2025 and tarek2026.** The text reads "This is consistent with earlier reports
\citep{gomaa2025,tarek2026}."
- *Problem:* it is vague, and it follows the claim that treatment dates are the largest single group (44%). That claim
  goes beyond both sources:
  - Gomaa found that clinical data alone matched MRI alone in one external test of 20 patients.
  - Tarek ranked the scan interval 13th of 18 concepts (the top non-imaging one), in one cohort, with no treatment
    history.
- **Suggested:** "Earlier studies also found that clinical data alone matched MRI alone in an external test of 20
  patients \citep{gomaa2025}, and that the interval between scans influenced a model built on the RANO rules at
  LUMIERE \citep{tarek2026}." This was the audit-3 wording; it was shortened since then.

**B3. L871–872, jabal2026 and herasrivera2026.** The text reads "Other systems use language models to extract clinical
variables … \citep{jabal2026}. Others use them to write reports before surgery … \citep{herasrivera2026}."
- *Problem:* each sentence is plural but has one source.
- **Suggested:** "Another system uses a language model to extract clinical variables from notes, which rules then
  combine with tumour volumes to assign a BT-RADS category \citep{jabal2026}. A third uses one to write reports before
  surgery from extracted image features and demographics \citep{herasrivera2026}."

**B4. L103, gabriel2021.** The text reads "Automatic measures of factual accuracy track human judgement poorly".
- *Problem:* this is not GO FIGURE's own finding. Its introduction credits other work (Hashimoto 2019, Clark 2019,
  Sellam 2020), and the claim concerns standard metrics. Its own findings are: "Standard summarization metrics are not
  always valid measures of factuality", and that performance "is highly dependent on the way in which questions are
  generated".
- **Suggested:** "Automatic measures of factual accuracy are not always valid, and how well they work depends on the
  metric and the domain \citep{gabriel2021}."

**B5. L80, arun2021 and saporta2022.** The text reads "Saliency maps drawn after the fact localise abnormalities poorly and
can be insensitive to the model's own weights".
- *Problem:* both are chest-radiograph studies, but the sentence makes a general claim. This is the same scope rule
  STYLE §10 added on 2026-11-27.
- **Suggested:** "In chest radiographs, saliency maps drawn after the fact localise abnormalities poorly and can be
  insensitive to the model's own weights \citep{arun2021,saporta2022}."

**B6. L319–320 and L886, deverdier2024: an understated overlap.** This one needs the author's OK, because it changes
what the paper discloses.
- *Problem:* BraTS 2024 lists its UCSF data as "UCSF; which consists of the previously described UCSF Longitudinal
  Post-Treatment Diffuse Glioma [UCSF-LPTDG]) [17]". Its ref. 17 is Fields et al., the same dataset paper cited for
  UCSF-ALPTDG (`fields2024`).
- I checked this in the paper's text. The challenge's UCSF data are therefore the dataset UCSF-ALPTDG comes from. The
  current text understates it: L319 says "may include scans from UCSF-ALPTDG", and L886 says "may have seen".
- **Suggested for L319:** "The challenge's UCSF data are the longitudinal dataset that UCSF-ALPTDG comes from, and the
  University of Missouri also contributed scans \citep{deverdier2024,fields2024}. Its training data may therefore
  include scans of patients in both external and development cohorts, but the network learned outlines only, with no
  progression label."
- **Suggested for L886:** "The BraTS 2024 data include the UCSF dataset that UCSF-ALPTDG comes from
  \citep{deverdier2024}, so the segmenter may have been trained on scans of UCSF-ALPTDG patients."
- Not verified: whether the UCSF-ALPTDG scans themselves, as opposed to the same source dataset, were in the
  challenge's *training* split. The source gives a 70/10/20 split by site, not by patient.

**B7. L90, mehrtens2023.** The text reads "and it does not hold under distribution shift".
- *Problem:* the source says conformal predictions are "unreliable under distributional shifts". This was my own
  wording from audit 3, and it is too strong.
- **Suggested:** "and it is not guaranteed under distribution shift \citep{mehrtens2023}."

## C. Should fix

| # | Line | Key | Problem | Suggested |
|---|---|---|---|---|
| C1 | 65 | (none) | The topic sentence "built on the image alone and tested only within the cohort they were developed on" is uncited; L848 says the same with citations | Append `\citep{booth2022,shi2025}` after "image alone" and `\citep{booth2022,park2020,shi2025}` after "developed on", as at L848–849 |
| C2 | 152 | angelopoulos2023 | "calibrated to contain the true outcome in 80% of scans" states an exact rate; the guarantee is a lower bound on average | "in at least 80% of scans on average" |
| C3 | 146 | (none) | "Swin UNETR trained on BraTS 2021" does not cite the dataset | "trained on BraTS 2021 \citep{baid2021}" |
| C4 | 193 | (none) | "LUMIERE rates every scan" is uncited | add `\citep{suter2022}` |
| C5 | 322–323 | (none) / suter2022 | "they mark the same four regions" is uncited. LUMIERE also supplies HD-GLIO-AUTO masks, so "they are DeepBraTumIA masks" implies only one set | add `\citep{mahmoud2025,fields2024}`; "At LUMIERE, we used the supplied DeepBraTumIA masks, which have three labels (…) \citep{suter2022}" |
| C6 | 511–516 | (none) | The "authors' public code" for the radiomics model is described but not cited | add an `@misc` for the GitHub repository with URL, commit (643c888) and access date. First confirm which of the two repositories in CHRISTODOULOU_REPLICATION.md is right, because their names are swapped with the MGMT paper |
| C7 | 187 | (none) | "grade 4 glioma" has no grading-system citation | new `louis2021`: Louis DN et al., The 2021 WHO Classification of Tumors of the CNS: a summary, Neuro-Oncology 23(8):1231–1251, doi:10.1093/neuonc/noab106 (verified on Crossref in audit 3) |
| C8 | 849 | park2020 | Park covers all neuro-oncology radiomics (5.9% on treatment response), but it is cited for "models in this field" | keep it only on the external-validation clause with "in neuro-oncology radiomics", or drop it there (booth2022 and shi2025 remain) |
| C9 | 445 | btradsweb | "leaves out the template's category and advice": the management advice is in the BT-RADS category guide, not the follow-up template | "It leaves out the BT-RADS category and its management recommendation, because PRISM makes no decision." |
| C10 | 106 | (none) | "Patient records often cannot leave the hospital" is uncited | **Suggested:** cite only after reading a source that says so. The sweep proposed mukherjee2023 on its title ("privacy-preserving") alone, which is not enough |

## D. Optional wording (each source supports a narrower or more hedged form)

- **L105, rao2025rexerr.** Its abstract says the errors "ha[ve] the potential to aid". Suggested: "…which may help to
  develop and test methods that correct them".
- **L453, zeba2026.** "Similar rule-based checks": the source also matches statements with an entity recogniser and
  embeddings. Suggested: "Similar checks without a language model test generated text against its source record".
- **L352, lecessie1992.** "many correlated inputs and few patients": the abstract supports "many covariates compared
  with observations", and "correlated" could not be checked (paywall). Suggested: "many inputs and few patients", or
  keep "correlated" after reading the full text.
- **L399, johansson2015.** The paper studies Mondrian regressors. Suggested: "Small calibration groups make the
  thresholds conservative, as shown for Mondrian conformal regressors \citep{johansson2015}."
- **L875, pham2026.** "forbid numbers" becomes "forbid numeric measurements" (source: "disallows numeric measurements or
  interval values").
- **L102, wiseman2017.** The scope is basketball summaries. Optional: "Neural systems that write basketball summaries
  from tables misstate many of the values they report".
- **L106, mukherjee2023.** It is one model in a proof of concept, so "Open-weight models … can label" could be singular.

## E. Optional additional citations

- L316–317: the four BraTS 2024 labels, `\citep{deverdier2024}`.
- L342: the 12-week window in Methods, `\citep{wen2023}`.
- L218 (Table 1): "DeepBraTumIA \citep{suter2022}".
- L436: JSON-schema constrained decoding. Cite the backend only after checking which one vLLM used (xgrammar or
  guidance). Willard and Louf, arXiv:2307.09702, applies only if it was Outlines.
- L468–469: the planted-error precedent, `\citep{gabriel2021,rao2025rexerr}`.
- L472: name the model that wrote the planted-error variants, as the AI declaration does.
- AUC: `hanley1982` (Radiology 143(1):29–36, doi:10.1148/radiology.143.1.7063747).
- L780: add `weinberg2018` beside `btradsweb` where BT-RADS is expanded.
- L928: the LUMIERE figshare dataset record, doi:10.6084/m9.figshare.c.5904905.

## F. refs.bib

| Entry | Fix |
|---|---|
| gemma2026 | add `doi = {10.48550/arXiv.2607.02770}`. Its Table 1 lists both E4B and 31B, so citing it for E4B (L790) is fine |
| mansour2026 | add `doi = {10.48550/arXiv.2610.34599}` and `url = {https://arxiv.org/abs/2610.34599}` |
| ke2017 | add `url = {https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html}` (no DOI exists) |
| yaseen2025tcia | follow TCIA's own citation: `Layfield, L. J.`, `Tahon, N. H. M.`, and "(Version 1) [Data set]" in howpublished. Also check "Yaseen, D." and "Porgorzelski", which are DataCite spellings |
| herasrivera2026 | optional: the PDF byline has 8 authors (adds Ruzevick, J.), while the arXiv metadata has 7 |
| arun2021 | confirm `e200267` on the RSNA page, because Crossref has no article number |
| btradsweb | optional: year = 2019 (v1.03) or n.d.; keep "accessed 2026-11-26" |
| pham2026 | replace the author-copy URL with the IEEE EMBC DOI once it is issued |
| platt1999 | (supplement only) year = 2000, chapter DOI 10.7551/mitpress/1113.003.0008 |

## G. Supplement (not submitted, low priority)

- supplement.tex:340: the versioned web documents (sample v1.03, guide v1.01) are credited to weinberg2018 as well.
  Cite `\citep{btradsweb}` alone there.

## H. Could not be fully verified (paywall or block)

These uses look right from the abstracts and secondary sources, but nobody read the full text:
- **wen2010:** 20–30% pseudoprogression (L55).
- **weinberg2018:** template elements (L444; btradsweb carries the detail).
- **johansson2015:** "conservative".
- **christodoulou2026:** "30 patients" and "4,892 features" come from the authors' code and logs, not the paper.
- **lecessie1992:** "correlated".
- **mukherjee2023:** publisher page.

## I. Uncited entries (38, not printed)

abler2025, angelopoulos2024, barber2021, blanche2013, boehm2022, borkan2019, brima2026, cfbgbm, chen2026, damour2022,
ding2026, elyassirad2025, guo2025, habas2007, hashim2026, janes2008, janes2009, jang2018, kallus2019, kapoor2023,
kryscinski2020, liu2026, lu2022, mahapatra2026, matos2026, nam2026, rai2026, riley2020, rudie2022, sudjianto2025,
tak2025, tikhonov2025, tsue2023, vovk2015, welch2019, worster2008, yun2025, zwanenburg2020.

---

## Appendix: per-agent reports

The line numbers in these reports are for `caf5944` or `c4c91b0`, depending on the agent. They are kept verbatim.

### Batch 1

I wasn't able to write the report to a .md file: the harness blocks subagents from writing report files. The full report is below. Nothing in the repo was edited. Of the 13 keys, all metadata is correct; four uses need a wording change, one first mention of a dataset needs a citation, and the radiomics code needs a reference.

Sources I opened:
- **Metadata:** Crossref for all 13 DOIs.
- **Abstracts:** Semantic Scholar for Valerio, Romano and Geirhos, and the University of Miami repository page for Christodoulou 2026. The publisher full text returned 403, so for Christodoulou I read only the abstract.
- **Christodoulou code:** the authors' code as recorded in `docs/results/CHRISTODOULOU_REPLICATION.md` and `CHRISTODOULOU_FAITHFUL_PLAN.md` (code clone at commit 643c888).
- **Full texts:** PMC for Beaulieu-Jones (PMC8010071) and the EANO guideline (PMC7904519), the PubMed abstract of RANO 2.0 (PMID 37774317), the ACL Anthology PDFs of GO FIGURE and Wiseman 2017, and `audit3/romano.txt`.

#### christodoulou2026
**Metadata:** OK. Crossref: Christodoulou RC, Vamvouras G, Pitsillos R, Solomou EE, Georgiou MF. Eur J Radiol Artif Intell 5:100074 (March 2026), open access CC BY.

The abstract says: "The LightGBM model trained on 256 radiomics features achieved an AUC of 0.80 on the held-out patient test set". The test-set size of 30 patients is not in the abstract. It comes from the authors' code: `N_TEST_PATIENTS = 30`, seed 42, 96 test scans drawn from all 203 MU patients.

- **Use 1, main.tex:74: OK.** One held-out set and AUC 0.80 are in the abstract; "30 patients" comes from the code. Citing the code repository would make the 30 traceable (see Missing citations).
- **Use 2, main.tex:159: WRONG.** The text reads "single held-out splits of 18 patients, the design of earlier studies on this cohort \citep{christodoulou2026}". The cited study held out 30 patients. Holding out 18 of the 92 grade 4 patients is this manuscript's own re-implementation (`docs/results/SINGLE_SPLITS.md`). "Studies" is plural but has only one citation.
  - Fix: "and up to 1.00 (mean 0.84) over 100 random held-out sets of 18 patients, an analogue of the single held-out design of an earlier study on this cohort \citep{christodoulou2026}".
- **Use 3, main.tex:298 (table): OK.** "256 of 4,892 ... selected within training" matches the code, where ranking runs on the patients outside the test set.
- **Use 4, main.tex:484: MINOR.** "studies evaluated on one held-out split" is plural with one source. "An earlier re-implementation of that study" does not say whose it is; it is the author's own and unpublished.
  - Fix: "For comparison with a study evaluated on one held-out split \citep{christodoulou2026}, ... drawn as in our earlier re-implementation of that study (exploratory)."
- **Use 5, main.tex:507: OK.** LightGBM and 256 features are in the abstract. The 4,892 features, PyRadiomics, and the LoG and wavelet filters are from the code and its `radiomics_params.yaml`. The sentence says PRISM's label and folds were used, so the change of label is disclosed.
- **Use 6, main.tex:841 (the sentence is now at line 847): MINOR.** "An earlier re-implementation of that model ranged from 0.32 to 0.88" can be read as a published re-implementation. The numbers match the replication doc (0.318–0.875, intended-use scans). The first sentence ("0.71 against 0.58") is the manuscript's own result, and the citation only names the model, so it is OK.
  - Fix: "Our earlier re-implementation of that model ranged from 0.32 to 0.88 over random held-out sets."
- **Use 7, supplement.tex:929: OK (low priority).** These code settings match the replication notes: 400 Optuna trials, `class_weight="balanced"`, Platt on the out-of-fold predictions, `MIN_TEST_SIZE_FOR_PI = 30`, and inner folds of 13–16 rows.

#### beaulieujones2021
**Metadata:** OK. npj Digit Med 4(1):62, 2021. There are 7 authors, so "and others" after four is fine.

- **Use 1, main.tex:80: OK.** "the results provide baseline performance levels that should be exceeded prior to claims that machine learning models can provide tangible guidance to clinicians, rather than simply looking over their shoulders."
- **Use 2, main.tex:490: OK.** The same quote, and also: "it will be important to show that performance improvements are the result of non-clinician-initiated data (e.g., raw imaging results)".
- **Use 3, main.tex:859: OK.**

#### gabriel2021
**Metadata:** OK. Findings of ACL: ACL-IJCNLP 2021, pp. 478–487.

- **Use 1, main.tex:104: MINOR.** "Automatic measures of factual accuracy track human judgement poorly" is not the paper's own finding. Its findings are "Standard summarization metrics are not always valid measures of factuality" and that QA-metric "performance is highly dependent on the way in which questions are generated". The sentence about poor correlation with human judgement is in its introduction, credited to Hashimoto 2019, Clark 2019 and Sellam 2020, and it concerns standard metrics.
  - Fix: "Automatic measures of factual accuracy are not always valid, and how well they work depends on the metric and the domain \citep{gabriel2021}."
- **Use 2, main.tex:465: OK.** The paper uses "transformed versions of the reference summary with injected errors".

#### weller2021
**Metadata:** OK. Nat Rev Clin Oncol 18(3):170–186; published online December 2020, in the 2021 issue.

- **Use 1, main.tex:52: OK.** "an initial interval between scans of 2–6 months is common practice", and "in case of doubt, rescanning after shorter intervals (4–8 weeks) is a pragmatic approach."
- **Use 2, main.tex:57: OK.** "Pseudoprogression ... most likely to occur during the first 3 months of treatment ... Particular attention is needed when interpreting scans during this period".

#### wiseman2017
**Metadata:** OK. EMNLP 2017, pp. 2253–2263.

- **Use 1, main.tex:103: OK, optional scope note.** The paper reports how often the facts a model writes are correct: 47% for Joint Copy and 71% for the best system, "indicating that relationships are often generated incorrectly". The task is basketball summaries written from box scores.
  - Optional: "Neural systems that write basketball summaries from tables misstate many of the values they report".
- **Use 2, main.tex:450: OK.** "simple, high-precision information extraction models can serve as the basis for assessing ... the quality of automatic generations".

#### valerio2025
**Metadata:** OK. Comput Methods Programs Biomed 270:108922, October 2025.

- **Use 1, main.tex:98: OK.** "integrating state-of-the-art semantic segmentation models with atlas-based mapping and Large Language Models (LLMs) to produce ... medical reports"; the method "has been specifically tested for brain tumor detection in glioma".

#### romano2020
**Metadata:** OK. Harv Data Sci Rev 2(2), 2020; the journal has no page numbers.

- **Use 1, main.tex:387: OK.** Theorem 1: "If (Xi,Ai,Yi), i = 1,...,n+1 are exchangeable, then the prediction interval ...". The paper also notes samples "may be drawn i.i.d.". Its guarantee holds within each group, which is stronger than the average guarantee the sentence needs.

#### geirhos2020
**Metadata:** OK. Nat Mach Intell 2(11):665–673.

- **Use 1, main.tex:77: OK.** "Shortcuts are decision rules that perform well on standard benchmarks but fail to transfer to more challenging testing conditions". The manuscript's paraphrase is acceptable.
  - Optional closer wording: "signals that predict the label in the data at hand but fail to transfer".

#### tustison2010
**Metadata:** OK. IEEE TMI 29(6):1310–1320.
- **Use 1, supplement.tex:918: OK (low priority).**

#### hung2010
**Metadata:** OK. Can J Stat 38(1):8–26; published online November 2009, in the 2010 issue.
- **Use 1, supplement.tex:274: OK (low priority).** The paper gives estimation methods for time-dependent AUC. It is cited only in an older supplement table, so it will not reach the submission.

#### flesch1948
**Metadata:** OK. J Appl Psychol 32(3):221–233.
- **Use 1, supplement.tex:484: OK (low priority).**

#### wen2023
**Metadata:** OK. J Clin Oncol 41(33):5187–5199.
- **Use 1, main.tex:58: OK.** "Since the incidence of pseudoprogression is high in the 12 weeks after radiotherapy, continuation of treatment and confirmation of progression during this period with a repeat MRI, or histopathologic evidence of unequivocal recurrent tumor, are required to define tumor progression."

#### field2007
**Metadata:** OK. J R Stat Soc B 69(3):369–390.
- **Use 1, main.tex:532: OK.** Drawing patients with replacement and keeping all their scans is the clustered bootstrap that Field and Welsh analyse. The publisher withholds the abstract, so this rests on the title and the method's standard use. Not refitting the models is the manuscript's own choice and is not credited to the source.

#### Missing citations (verified)
- **main.tex:74:** the first mention of "MU-Glioma-Post" has no citation; the dataset is first cited at line 186. Add \citep{mahmoud2025} (Sci Data 12:1847, 2025; DOI 10.1038/s41597-025-06011-7, confirmed on Crossref).
- **main.tex:507:** "with its authors' public code and settings" has no code reference. The progression code is at https://github.com/georgeDV2002/Explainable-modality-adaptive-radiomics-for-MGMT-methylation-prediction-in-high-grade-glioma (the GitHub API returns 200). The authors swapped the names of this repository and their MGMT paper's repository, so a footnote should say this one holds the progression code.

ACTIONABLE:
- main.tex:159 | christodoulou2026 | The 18-patient held-out design is credited to "earlier studies on this cohort", but the cited study held out 30 patients; 18 of 92 is the manuscript's own re-implementation | "and up to 1.00 (mean 0.84) over 100 random held-out sets of 18 patients, an analogue of the single held-out design of an earlier study on this cohort \citep{christodoulou2026}"
- main.tex:484 | christodoulou2026 | Plural "studies" with one source; "an earlier re-implementation" does not say whose | "For comparison with a study evaluated on one held-out split \citep{christodoulou2026}, ... drawn as in our earlier re-implementation of that study (exploratory)."
- main.tex:841 (sentence at 847) | christodoulou2026 | "An earlier re-implementation" can be read as a published one | "Our earlier re-implementation of that model ranged from 0.32 to 0.88 over random held-out sets."
- main.tex:104 | gabriel2021 | The claim about human judgement is not the paper's own finding; its introduction credits it to other work | "Automatic measures of factual accuracy are not always valid, and how well they work depends on the metric and the domain \citep{gabriel2021}."
- main.tex:74 | missing mahmoud2025 | First mention of MU-Glioma-Post has no citation | add \citep{mahmoud2025} after "MU-Glioma-Post"
- main.tex:507 | missing code reference | "authors' public code" has no reference | add a misc bib entry or footnote with the GitHub URL above, noting the swapped repository names
- main.tex:103 (optional) | wiseman2017 | Scope is basketball summaries | "Neural systems that write basketball summaries from tables misstate many of the values they report"
### Batch 2

Report for batch 2 of the citation audit (14 keys, nothing edited). The harness would not let me save it as a .md file, so the full report is below and can be pasted into one. I checked the repo at /tmp/sbandred-prism/repo at commit c4c91b0. From main.tex line 186 on, citations sit 3 to 4 lines lower than in batch2.md (the earlier ones have not moved). The lines below are current, with the batch2.md line in brackets where it differs.

#### Citation audit, batch 2

**Result:** every key exists, and every DOI resolves to the details in its entry. No use is WRONG. Three uses need a wording change (main.tex:323, 850 and 444). The other items in the ACTIONABLE list are optional.

#### btradsweb
**Metadata: MINOR.** The site and both documents exist.
- The "Brief report sample" on btrads.com/resources is `BT-RADS-followup-template-v1_03_short-sample.pdf`, dated 2019-11-12, author M. Hoch, Emory.
- The "Category guide" is `BT-RADS-quick-reference-categories-2018_02_01.pdf`, headed "Post-treatment tumor categorization scheme version 1.01 - 8/1/2017".
- `year={2026}` is only the access year. `{2019}` (the template date) or `{n.d.}` would be more exact.

**Uses**
- **main.tex:444 [440]: citation OK.** The template has CLINICAL INDICATION (tumour type, surgical history, radiation history, medications), COMPARISON, and change phrases such as "No change in extent of enhancing component".
  - **MINOR in the next sentence**, "It leaves out the template's category and advice". The advice ("Associated management recommendation", e.g. "Decreased time interval of follow-up") is in the category guide, not the template.
  - Fix: "It leaves out the BT-RADS category and its management recommendation, because PRISM makes no decision." Check LOCKED.md first.
- **main.tex:775 [771]: OK.** The template starts "CLINICAL INDICATION ... Surgical History: [last surgery date] Radiation History: [radiation completion date]".
- **supplement.tex:340: OK.** Template v1.03 and category scheme v1.01 confirmed.
- **supplement.tex:346: OK.**

#### suter2022
**Metadata: OK.** Suter, Knecht, Valenzuela, Notter, Hewer, Schucht, Wiest and one more author; Sci Data 9(1):768, 2022.

**Uses**
- **main.tex:186 [183]: OK.** "The records of 91 GBM patients ... were reviewed retrospectively".
- **main.tex:323 [319]: MINOR.** The source says "DeepBraTumIA outputs labels for necrosis, contrast enhancement, and edema." But LUMIERE ships two automated segmentations: "DeepBraTumIA ... and HD-GLIO-AUTO ... are included". So "At LUMIERE, they are DeepBraTumIA masks" implies only one set is supplied.
  - Fix: "At LUMIERE, we used the supplied DeepBraTumIA masks, which have three labels (necrosis, contrast enhancement and oedema) \citep{suter2022}; ..."
- **main.tex:922 [918]: OK.** "The cantonal ethics committee of Bern approved the studies and waived written informed consent."
- **main.tex:928 [924]: OK.** "All records for this data collection are available through Figshare".
  - Optional: also cite the dataset record, DOI 10.6084/m9.figshare.c.5904905.v1 (confirmed on DataCite: Suter Y., figshare, 2022).

#### park2020
**Metadata: OK.** BMC Cancer 20(1):29, 2020.

**Uses**
- **main.tex:67: OK.** "Fifty-one articles ... were finally analyzed"; "Most studies included gliomas (90.1%)"; "Only 29.4% performed external validation."
- **main.tex:850 [846]: MINOR (scope).** In context, "this field" means progression versus pseudoprogression.
  - Park covers all neuro-oncology radiomics, and only 5.9% of its studies are on treatment response.
  - Its finding that "external validation was missing in 36 out of 51 studies (70.6%)" supports the broader field. booth2022 and shi2025 carry the specific claim.
  - Fix: drop park2020 from this sentence, or write "Most models in this field, and in neuro-oncology radiomics generally, ..."

#### qwen2026
**Metadata: OK.** The entry matches the recommended citation on the Hugging Face card word for word (Qwen3.8-Max blog, August 2026). Qwen/Qwen3.8-27B exists: created 2026-08-05, Apache-2.0, 27B parameters. The card calls it a "Causal Language Model with Vision Encoder". "The model sees no images" describes PRISM's design, so that is fine.

**Uses**
- **main.tex:431 [427]: OK.** The weights are public under Apache-2.0 and "compatible with Hugging Face Transformers, vLLM".
- **main.tex:791 [787]: OK.**

#### zhang2020
**Metadata: OK.** Acad Radiol 27(6):780-784, 2020; seven authors match.

**Uses**
- **main.tex:96: OK.** "Post-BT-RADS reports demonstrated greater reporting of history words, including "Avastin" (7.6% vs. 20.9%) and "methylguanine-DNA methyltransferase" (10.9% vs. 31.4%)".
  - This is one centre (Emory). Optional: "...reports at the centre that introduced it mentioned bevacizumab and MGMT status more often".
- **supplement.tex:349: OK.** "greater reporting of history words ... reduced usage of hedge words".

#### an2021
**Metadata: OK.** PLOS ONE 16(8):e0256152, 2021.

**Uses**
- **main.tex:70: OK.** "machine learning after a single random training-test set split may lead to unreliable results in radiomics studies especially with small sample sizes."
- **main.tex:486 [482]: OK.** "The AUCs in training and testing varied among different training-test set pairs, especially with the undersampled datasets".

#### rao2025rexerr
**Metadata: OK.** Biocomputing 2025 (PSB vol. 30), pp. 70-81; the five authors match arXiv:2409.10829.

**Use**
- **main.tex:105: OK.** "a methodology that leverages Large Language Models to generate representative errors within chest X-ray reports ... has the potential to aid in the development and evaluation of report correction algorithms."
  - Optional hedge to match the source: "Language models can insert realistic errors into chest radiograph reports, which may help to develop and test methods that correct them \citep{rao2025rexerr}."

#### taal2008
**Metadata: OK.** Cancer 113(2):405-410, 2008.

**Use**
- **main.tex:57: OK.** "In 36 patients (42%) the first followup scan 4 weeks after the end of RT indicated disease progression. Of these 36 patients, 18 (50%) were diagnosed with pseudo-progression."

#### uno2007
**Metadata: OK.** JASA 102(478):527-537, 2007.

**Use**
- **supplement.tex:274: OK.** A standard reference for IPCW accuracy measures, cited alongside hung2010.

#### kim2019
**Metadata: OK.** Neuro-Oncology 21(3):404-414; online 2018, issue 2019.

**Use**
- **main.tex:62: OK.** The model was developed in "61 glioblastomas" and "validated with an external cohort (n = 34) imaged on a different scanner and internal prospective registry data (n = 23)". The source concludes: "Incorporating diffusion- and perfusion-weighted MRI into a radiomics model improved diagnostic performance".
  - Optional: "...tested in 34 others imaged on a different scanner".

#### kocak2023
**Metadata: OK.** Insights Imaging 14(1):75, 2023.
- **supplement.tex:232: OK.**

#### loshchilov2019
**Metadata: OK.** "Published as a conference paper at ICLR 2019".
- Optional: change it to `@inproceedings` with `booktitle={International Conference on Learning Representations}`.
- **supplement.tex:254: OK.** AdamW is decoupled weight decay.

#### dunn2023
**Metadata: OK.** JASA 118(544):2491-2502; online 2022, issue 2023.

**Use**
- **main.tex:391 [387]: OK.** "exchangeability ... does not hold when groups of observations come from distinct distributions, such as multiple observations on each patient in a medical database."
  - The clause "weighting by patient makes the guarantee approximate" is the manuscript's own statement and is not attributed to Dunn. That is correct as written.

#### cawley2010
**Metadata: OK.** JMLR 11(70):2079-2107, 2010.
- **supplement.tex:146: OK.** Selection bias from tuning outside the evaluation loop, cited for nested selection.

#### Missing citations
None required.
- vLLM is already cited (kwon2023).
- SwinUNETR and BrainSegFounder are already cited at supplement.tex:167 (hatamizadeh2022, cox2024).
- The only optional addition is the LUMIERE figshare DOI at main.tex:928.

ACTIONABLE:
- main.tex:323 | suter2022 | LUMIERE supplies both DeepBraTumIA and HD-GLIO-AUTO masks; "they are DeepBraTumIA masks" implies only one set | "At LUMIERE, we used the supplied DeepBraTumIA masks, which have three labels (necrosis, contrast enhancement and oedema) \citep{suter2022}; ..."
- main.tex:850 | park2020 | scope: Park covers all neuro-oncology radiomics (5.9% on treatment response) but is cited for "models in this field" | drop park2020 here (booth2022, shi2025 remain) or write "Most models in this field, and in neuro-oncology radiomics generally, ..."
- main.tex:444 | btradsweb | the management advice is in the BT-RADS category guide, not the follow-up template | "It leaves out the BT-RADS category and its management recommendation, because PRISM makes no decision." (check LOCKED.md)
- refs.bib | btradsweb | year 2026 is the access year; the documents are dated 2017 (v1.01) and 2019 (v1.03) | optional: year = {2019} or {n.d.}, keep "accessed 2026-11-26"
- main.tex:928 | suter2022 | optional: cite the dataset record in the data availability statement | add @misc for figshare DOI 10.6084/m9.figshare.c.5904905.v1 (Suter Y. et al., 2022)
- main.tex:105 | rao2025rexerr | optional hedge to match the source's "has the potential to aid" | "Language models can insert realistic errors into chest radiograph reports, which may help to develop and test methods that correct them \citep{rao2025rexerr}."
### Batch 3

#### Citation audit, batch 3 (report only, no edits made)

Line numbers are from the current repo (/tmp/sbandred-prism/repo, HEAD c4c91b0); where the batch file gave a different number it is in brackets. Sources: Crossref, PubMed abstracts (PMIDs 29503151, 30661977, 40382400, 37815442, 41251553, 35652114, 34817740, 31304378), PMC full text (Gomaa), nature.com (Mahmoud), arXiv API and HTML (Jabal, Gemma 4), Ferreira arXiv 2411.04632 text.

#### weinberg2018
Metadata: OK. Crossref: Weinberg BD, Gore A, Shu H-KG, Olson JJ, Duszak R, Voloschin AD, Hoch MJ; JACR 15(5):767-771, 2018.
- main.tex:95 | OK. Cited as the source of BT-RADS. The paper's title is "Management-Based Structured Reporting of Posttreatment Glioma Response With the Brain Tumor Reporting and Data System".
- main.tex:444 [440] | UNVERIFIABLE (the JACR full text is behind a Cloudflare wall and is not open access) for the detail "history, comparison and change elements". As a reference for the BT-RADS system it is OK. btradsweb supports the template detail. No change needed if btradsweb shows those elements.
- supplement.tex:340 | MINOR (low priority). The versions "sample v1.03" and "category guide version 1.01" are web documents, not the 2018 paper. Fix: cite only \citep{btradsweb} for the versioned documents, or write "(sample v1.03 and category guide v1.01 \citep{btradsweb}; system described in \citealp{weinberg2018})".
- supplement.tex:346 | OK.

#### mahmoud2025
Metadata: OK. Scientific Data 12:1847 (published 20 Nov 2025); authors Mahmoud E, Gass J, Dhemesh Y, ... Nada A.
- main.tex:186 [183] | OK. The paper presents "a dataset of 203 glioma patients with 594 post-treatment timepoints".
- main.tex:922 [918] | OK. The paper says it was "approved by the University of Missouri Institutional Review Board (IRB #2096253 MU). The IRB granted a waiver of informed consent for the retrospective collection and sharing of de-identified patient data."
- supplement.tex:32 | OK.

#### gore2019
Metadata: OK. Acad Radiol 26(7):974-980, 2019.
- main.tex:97 | OK. The abstract says "After implementing BT-RADS, respondents reported improved attitudes ... report consistency (4.3 vs. 3.4; p < 0.001)". Respondents were "faculty members, house staff members, and nonphysician providers ... who participate in the direct care of brain tumor patients". Optional fix for scope: "...by the clinicians and radiologists caring for these patients at that centre".
- main.tex:444 [440] | OK.
- supplement.tex:348 | OK. The abstract confirms the survey before adoption and the follow-up "Nine months following structured reporting implementation", with consistency and ambiguity both improved.

#### gomaa2025
Metadata: OK. Sci Rep 15:17133 (2025); Gomaa A, Huang Y, Stephan P, et al.
- main.tex:78 | OK. Table 3 (external test, n = 20 at UKER) gives AUC 0.727 for clinical data and 0.717 for MRI alone (ensembled), and 0.698 vs 0.659 for the means. The text says "the clinical data outperformed the imaging modality across all metrics except for specificity." "Matched" is accurate and slightly conservative.
- main.tex:858 [854] | MINOR. "Consistent with earlier reports" is vague: the reader cannot tell what is consistent. Gomaa supports two specific findings. First, clinical data predicted as well as MRI. Second, in the SHAP analysis, "the time between the last treatment and the first progression has the greatest influence on the model's prediction". Fix: "In an earlier study, clinical data alone predicted progression as well as MRI alone, and the time since treatment was the most influential input \citep{gomaa2025}; the interval between scans also affected a model built on the RANO rules \citep{tarek2026}." (Re-check the tarek2026 clause against its own audit.)

#### jabal2026
Metadata: OK. arXiv:2603.21494 (v1 23 Mar 2026, v2 24 Mar 2026). The 9 authors match in order. The title matches.
- main.tex:140 | OK. The paper says "An extractor agent identified clinical variables (steroid status, bevacizumab status, radiation date) from unstructured clinical notes, while a scorer agent applied BT-RADS decision logic integrating extracted variables with volumetric measurements". The scorer "implements BT-RADS decision logic through sequential rule application", with "deterministic BT-RADS decision logic". The volumes are CNN-based automated segmentations.
- main.tex:872 [868] | MINOR. The sentence says "Other systems" (plural) but cites one system. Fix: "Another system uses a language model to extract clinical variables from notes, which rules then combine with tumour volumes to assign a BT-RADS category \citep{jabal2026}."

#### gemma2026
Metadata: MINOR. The arXiv:2607.02770 "Gemma 4 Technical Report" by Gemma Team (2 Jul 2026) exists. The entry has no doi field, unlike other arXiv entries (for example jabal2026). Fix: add doi = {10.48550/arXiv.2607.02770}.
- main.tex:767 [763] | OK. The citation only identifies the model, and the pass rate is the manuscript's own result. The report lists a 31B dense model ("dense architectures (2.3B, 4.5B, 12B, and 31B parameters)").
- main.tex:790 [786] | OK. Table 1 of the report lists both E4B and 31B.

#### mukherjee2023
Metadata: OK. Radiology 309(1):e231147, 2023.
- main.tex:106 | OK. The paper tested "an alternative LLM (Vicuna-13B) that can be run locally for labeling radiography reports", with "moderate to substantial agreement with existing labelers". Optional fix: the study is a single-model proof of concept, so "An open-weight model run on site labelled chest radiograph reports..." would match it more closely.

#### prucker2025
Metadata: OK. Radiology 317(2):e251844, Nov 2025. All 17 authors match Crossref in order.
- main.tex:102 | OK. The LLM was Llama 3.3 70B, which is open-weight. The abstract says "Radiologist review revealed factual errors in 6% (moderate, 2%; severe, 4%) ... of simplified reports".

#### badgeley2019
Metadata: OK. npj Digit Med 2:31, 2019.
- main.tex:77 | OK. The abstract says "the model performed randomly (AUC = 0.52 ...), indicating that these [patient and hospital process] variables were the main source of the model's fracture predictions."

#### demircioglu2021
Metadata: OK. Insights Imaging 12:172, 2021.
- supplement.tex:146 | OK (low priority). The paper shows that feature selection done outside cross validation biases AUC "up to 0.15". It supports the principle of doing selection inside folds. It is not specific to penalty choice, but it is co-cited with varma2006 and cawley2010, which cover that.

#### yu2022
Metadata: OK. Radiol Artif Intell 4(3):e210064, 2022.
- main.tex:71 | OK. The abstract says "The vast majority (70 of 86, 81%) reported at least some decrease in external performance". The scope (published external-validation studies) is implicit. Optional, more precise wording: "Of 86 deep learning algorithms for radiological diagnosis tested on external data, 81% performed worse there \citep{yu2022}."

#### mitchell2019
Metadata: OK. Proceedings of the Conference on Fairness, Accountability, and Transparency (FAT* '19), ACM, pp. 220-229; Mitchell, Wu, Zaldivar, Barnes, Vasserman, Hutchinson, Spitzer, Raji, Gebru.
- main.tex:409 [405] | OK. The text uses "modelled on" and claims only a design inspiration.

#### platt1999
Metadata: MINOR (supplement only). The chapter appeared in a book published in 2000 (Crossref: MIT Press, published 29 Sep 2000). The published chapter title is "Probabilities for SV Machines", pp. 61-74, DOI 10.7551/mitpress/1113.003.0008. The entry's title is that of the 1999 technical report, which is a common way to cite it. Fix (optional): year = {2000}, doi = {10.7551/mitpress/1113.003.0008}, and keep the title or change it to the chapter title.
- supplement.tex:925 | OK. Platt calibration fits a sigmoid (logistic) to held-out outputs. (Whether the code really fits on cross-validation held-out predictions is a code-matching question, not a citation one.)

#### roy2023
Metadata: OK. MICCAI 2023, LNCS 14223, pp. 405-415.
- main.tex:315 [311] | OK. Ferreira et al. (2411.04632) say the final ensemble was "the ensemble of all models", namely nnU-Net, Swin UNETR and MedNeXt ("The models trained with MedNeXt have less FP...; the ensemble of all models would have the greatest potential for the test phase"). Ferreira cites MedNeXt as Roy et al. MICCAI 2023, pp. 405-415.

#### Missing citations
None verified as needed in these paragraphs. Every named tool, dataset or model in them already has a citation.

ACTIONABLE:
main.tex:858 | gomaa2025 | "consistent with earlier reports" does not say what is consistent | "In an earlier study, clinical data alone predicted progression as well as MRI alone, and the time since treatment was the most influential input \citep{gomaa2025}" (handle the tarek2026 clause separately)
main.tex:872 | jabal2026 | the plural "Other systems use language models" is supported by one cited system | "Another system uses a language model to extract clinical variables from notes, which rules then combine with tumour volumes to assign a BT-RADS category \citep{jabal2026}."
refs.bib (gemma2026) | gemma2026 | no DOI, unlike the other arXiv entries | add doi = {10.48550/arXiv.2607.02770}
supplement.tex:340 | weinberg2018 | the versioned web documents (sample v1.03, guide v1.01) are attributed to the 2018 paper too | cite \citep{btradsweb} for the versioned documents only (low priority, supplement)
refs.bib (platt1999) | platt1999 | book published 2000; chapter DOI missing | year = {2000}, doi = {10.7551/mitpress/1113.003.0008} (optional, supplement only)

### Batch 4

I couldn't save the report as an .md file. The tool refused because a subagent here has to return text, so the full report is below. It can be pasted into a file as is. No repo files were edited.

All 14 references are real and their details are correct. One citation needs a wording change (main.tex:854), and two more are optional tightenings.

Line numbers are from `/project/community/sbandred/prism-gbm-surveillance/paper` at caf5944, which match batch4.md. The copy at `/tmp/sbandred-prism/repo` has uncommitted edits to main.tex, and its line numbers are about 4 higher (for example, hatamizadeh2022 is at 315 and 327 there).

**Sources opened:**
- Crossref for every DOI.
- arXiv abstract pages for 2606.30313 and 2107.02314.
- Full text of Swin UNETR, Ferreira 2024, TRACE and Shi 2025 (the audit3 extracts).
- Full text of Barber et al. (arXiv 1903.04684) and Hoebel 2024 (PMC10831514).
- PubMed abstracts for Stupp 2005 and Varma 2006, the OpenAlex abstract for le Cessie 1992, and the Semantic Scholar abstract for Cox 2024.

#### hatamizadeh2022
**Details: OK.** Crossref has the same 6 authors and title, LNCS BrainLes 2021, pp. 272–284, 2022. Volume 12962 is correct.
- **Use 1, main.tex:146: OK.** The source says it was "trained on BraTS 2021 dataset with 1251 and 219 cases".
- **Use 2, main.tex:311: OK.** Ferreira lists "RSg : Swin UNETR trained only with the real dataset" in the ensemble and cites Hatamizadeh as ref. [4].
- **Use 3, main.tex:323: OK.** The source says "three nested sub-regions: Whole Tumor (WT), Tumor Core (TC), and Enhancing Tumor".
  - The settings (z-score, 128³ blocks, overlap 0.5) describe PRISM's own run and are not credited to the paper.
  - The paper's own inference used "an overlapping of 0.7", so nothing needs changing.
- **Use 4, supplement.tex:167: OK.** This file is not submitted.

#### barber2021limits
**Details: OK.** Vol. 10(2), 455–482. The print issue is 2021; it was published online on 25 August 2020.
- **Use 1, main.tex:90: OK.** "conformal prediction offer marginal coverage guarantees, where predictive coverage holds on average over all possible test points … not merely on average over a population". Section 1 also gives an example of 0% coverage in a subgroup (patients under 25).
- **Use 2, main.tex:387: OK.** Split conformal "makes no assumptions … aside from requiring that the training data and the test point are exchangeable."
- **Use 3, main.tex:877: OK.** Same quote as Use 1.

#### shi2025
**Details: OK.** Shi, Kujawa, Linares, Vercauteren, Booth. Neuro-Oncology 27(8):1946–1971, 2025.
- **Use 1, main.tex:69: OK.** "few studies (15.0%, 3/20) explicitly stated that they considered relevant clinical characteristics important for final longitudinal treatment response assessment."
- **Use 2, main.tex:845 ("built on the image alone"): OK, but it is a paraphrase.**
  - Shi counts studies that *stated they considered* clinical characteristics (such as steroids or performance status). It does not count models that took clinical inputs.
  - Optional fix: "Most models in this field do not take the clinical history into account".
- **Use 3, main.tex:846 ("tested only within the cohort"): OK, but "most" is only narrowly supported.**
  - The source says: "Of 50.0% (10/20) studies that trained ML models … 40.0% (4/10) studies additionally employing external test data. The remaining study 5.0% (1/20) only used external test data".
  - That leaves 6 of the 11 studies that developed a model with internal test data only. The review adds that "few studies employed external testing".

#### stupp2005
**Details: OK.** NEJM 352(10):987–996, 2005.
- **Use 1, main.tex:51: OK.** "the median survival was 14.6 months with radiotherapy plus temozolomide". This is a trial population (newly diagnosed, 84% had debulking surgery), and "about 15 months" is fair.
- **Use 2, main.tex:360: OK.** "daily fractions of 2 Gy given 5 days per week for 6 weeks, for a total of 60 Gy".

#### lecessie1992
**Details: OK.** Applied Statistics 41(1):191–201, 1992. Crossref lists only the first page.
- **Use 1, main.tex:150: OK.** The paper presents ridge logistic regression.
- **Use 2, main.tex:345: OK for "many inputs and few patients".**
  - The abstract says: "the number of covariates is large compared with the number of observations and modelling without restrictions on the parameters leads to overfitting … ridge estimators … improve the parameter estimates".
  - "Correlated" is not in the abstract, and the full text is behind the JSTOR paywall, so that word is UNVERIFIABLE.
  - Optional fix: "This keeps them stable when there are many inputs and few patients."

#### tarek2026
**Details: OK.** arXiv:2606.30313 has the same 9 authors and title, submitted on 29 June 2026. arXiv spells one author "Saberr, Hamsa"; the PDF spells it "Saber".
- **Use 1, main.tex:79: OK.** "time_gap has a strong effect on the output, suggesting that scan interval captures dataset-level signal in LUMIERE". The model is "a RANO 2.0-aligned concept bottleneck model".
- **Use 2, main.tex:854: MINOR.**
  - The sentence before the citation says that treatment course and dates made up the largest single group (44%) of the combined score.
  - TRACE reports nothing of that size. Its time_gap "ranks thirteenth by CaCE-TV (0.069) but remains noteworthy as the highest-ranked non-imaging metadata concept".
  - TRACE also used one cohort (LUMIERE) and had no treatment history. "Consistent with" only holds in the general sense that timing carries signal.
  - Fix: "Earlier studies also found that clinical data or the scan interval carried part of a model's signal \citep{gomaa2025,tarek2026}."

#### isensee2021
**Details: OK.** Nature Methods 18(2):203–211. The issue is dated 2021; it was published online on 7 December 2020.
- **Use 1, main.tex:311: OK.** Ferreira's ensemble includes "RNg : nnUNet (3D full resolution)" and cites nnU-Net as ref. [5].

#### baid2021
**Details: OK.** arXiv:2107.02314. The title matches, and the first six authors match.
- **Use 1, main.tex:327: OK.** "…in pre-operative baseline mpMRI data from 2,040 patients."

#### cox2024
**Details: OK.** Medical Image Analysis 97:103301 (October 2024), with all 8 authors matching.
- **Use 1, supplement.tex:167: OK.** The citation only names the tool, and this file is not submitted.

#### varma2006
**Details: OK.** BMC Bioinformatics 7:91 (2006).
- **Use 1, supplement.tex:146: OK.** "The nested CV procedure reduces the bias considerably and gives an estimate of the error that is very close to that obtained on the independent testing set". This file is not submitted.

#### ke2017
**Details: OK.** NeurIPS 30 (2017), pp. 3146–3154; the authors are correct. The paper has no DOI.
- Optional: add `url = https://papers.nips.cc/paper/6907-lightgbm-a-highly-efficient-gradient-boosting-decision-tree`.
- **Use 1, main.tex:510: OK.** The citation names the software. The claim that the Christodoulou model uses LightGBM rests on christodoulou2026, which is not in this batch.

#### hoebel2024
**Details: OK.** Radiology: Artificial Intelligence 6(1):e220231 (2024), with 16 authors.
- **Use 1, main.tex:86: OK.** The source supports both parts of the sentence:
  - "a low interrater agreement (Krippendorff α, 0.34) in experts' segmentation quality perception".
  - "the average Dice score for the interreader agreement was 0.64".
  - The cases were post-operative glioblastoma (FLAIR abnormality, 54 patients), which fits the follow-up setting.

#### akiba2019
**Details: OK.** KDD 2019, pp. 2623–2631, ACM. Crossref gives the title as just "Optuna"; the full title in the entry is correct.
- **Use 1, supplement.tex:923: OK.** The citation names the tool. Optuna's default search method (TPE) fits "Bayesian search". This file is not submitted.

#### Missing citations in these paragraphs
None clearly needed. Every tool or dataset in these paragraphs is cited either in the same paragraph (MONAI, the BraTS orchestrator, PyRadiomics, Platt) or earlier in the text (RANO at main.tex:57, LUMIERE in the data section).

ACTIONABLE:
- main.tex:854 | tarek2026 | "This is consistent with earlier reports" follows the claim that treatment course and dates are the largest single group (44%). TRACE found the scan interval ranked 13th of 18 concepts (the top non-imaging one), in one cohort (LUMIERE) and with no treatment history. | "Earlier studies also found that clinical data or the scan interval carried part of a model's signal \citep{gomaa2025,tarek2026}."
- main.tex:345 | lecessie1992 (optional) | "Many correlated inputs": the source abstract supports only "many covariates compared with observations"; "correlated" could not be checked against the paywalled full text. | "This keeps them stable when there are many inputs and few patients." Or keep "correlated" once the full text confirms it.
- main.tex:845 | shi2025 (optional) | Shi counted studies that stated they considered clinical characteristics, not models that used image inputs only. | "Most models in this field do not take the clinical history into account \citep{booth2022,shi2025}"
### Batch 5

I could not write the report to a .md file: the tool refused it, saying subagents must return findings as text. The full report is below; it can be saved as-is. No repo files were edited.

None of the 13 keys has a metadata error. Two claims need changing: the zhang2026meta wording at main.tex:72 and :163-164, and an unsourced number at main.tex:849. A few other wording changes are optional. Line numbers refer to the current `/tmp/sbandred-prism/repo/paper/main.tex` (HEAD f651e59). The batch file's line numbers were a few lines out of date, but the cited paragraphs read the same. The new hits at main.tex:31, 312 and 372-373 are only LaTeX `%` comments, not citations.

#### deverdier2024
**Metadata: OK.** DataCite 10.48550/arXiv.2405.18368 has the same title, 85 authors starting de Verdier, Saluja, Gagnon, and arXiv 2024.
- **main.tex:85: OK.** "The combination of treatment-related changes, including resection cavities, blood products, post-radiation inflammation, and gliosis ... makes segmentation a challenging task ... The 2024 BraTS challenge is the first to focus on post-treatment gliomas."
- **main.tex:314: OK.** "...a new dataset consisting only of post-treatment MRIs of low- and high-grade diffuse gliomas"; the resection cavity is one of its labels.
- **main.tex:318-319: MINOR (understates the source).**
  - The source says "Data was contributed from seven different academic medical centers ... University of California San Francisco (UCSF; which consists of the previously described UCSF Longitudinal Post-Treatment Diffuse Glioma [UCSF-LPTDG]) [17], University of Missouri Columbia ...".
  - Its ref. 17 is Fields et al., "The University of California, San Francisco Longitudinal Post-Treatment Diffuse Glioma (UCSF-ALPTDG) MRI Dataset". Table 1 gives about 600 UCSF cases and about 400 Missouri cases.
  - So the UCSF data in BraTS 2024 *are* UCSF-ALPTDG. Which of those cases went into training is still unknown, so "may" stays.
  - Fix: "The challenge's UCSF data are the UCSF-ALPTDG dataset, and the University of Missouri also contributed scans \citep{deverdier2024}, so its training data may include scans of patients in UCSF-ALPTDG and MU-Glioma-Post, but the network learned outlines only, with no progression label."
- **main.tex:886: OK.** Same quote. Optionally make it the same as line 319: "The BraTS 2024 data include the UCSF-ALPTDG dataset \citep{deverdier2024}, ...".

#### booth2022
**Metadata: OK.** Crossref: Frontiers in Oncology 12, article 799662, 2022, 16 authors.
- **main.tex:66: OK.** "Small patient numbers, high bias risk, applicability concerns ... and low level of evidence, allow limited conclusions from studies."
- **main.tex:849 ("built on the image alone"): OK but weak.**
  - The review never says this in so many words. Its Table 1 shows it: most of the 18 studies use MRI features only.
  - Only a few add clinical data: Bani-Sadr adds MGMT status; Jang adds age, gender, MGMT, IDH, radiotherapy dose and follow-up interval.
  - shi2025 carries the explicit claim. If a reviewer pushes, keep only shi2025 on this clause.
- **main.tex:850 ("tested only within the cohort"): OK.** "A third of studies had external hold-out test sets (6/18, 33%)", and six had no hold-out set at all. "Most models" holds.

#### ferreira2024
**Metadata: OK.** DataCite 10.48550/arXiv.2411.04632: six authors match, arXiv 2024 (v2, 2 Dec 2024).
- **main.tex:123: OK.** Six models: "All" is "rGNg RNg rGSg RSg rGMg RMg". "each model was trained with a 5-fold cross-validation resampling method". It achieved "the best ranking in the testing phase" of Task 1.
- **main.tex:145: OK.** "the winning solution of task 1". "Used without fine-tuning" is PRISM's own choice and is not attributed to the paper.
- **main.tex:313: OK.** The nnU-Net (3D full resolution), MedNeXt L and Swin UNETR ensemble matches the paper.

#### zhang2026meta
**Metadata: OK.** Crossref 10.1093/neuonc/noag259: Neuro-Oncology advance article, 19 Oct 2026, article noag259, PMID 42898007. Check whether a volume and issue have been assigned before submission.

The abstract says: "Thirty-one studies including 2,344 patients ... Seven external test cohorts, including 219 patient observations, entered the primary meta-analysis ... summary [AUC] was 0.81 (bootstrap 95% CI, 0.69-0.91). Internal test cohorts showed higher apparent performance than external cohorts (AUC, 0.91 vs 0.81), but the difference was not statistically significant (... P = 0.12)."

- **main.tex:72: MINOR.**
  - The sentence suggests 0.81 comes from all 31 studies; it comes from 7 external test cohorts.
  - It presents 0.91 vs 0.81 as a drop; the source says the difference was not significant.
  - It leaves out the task: separating true progression from pseudoprogression.
  - Fix: "In a meta-analysis of 31 studies separating true progression from pseudoprogression, seven external test cohorts gave a pooled AUC of 0.81, against 0.91 for internal test cohorts, a difference that was not statistically significant \citep{zhang2026meta}."
- **main.tex:163-164: MINOR (different task).** The comparison models separate true progression from pseudoprogression; PRISM's label is progression at follow-up scans.
  - Fix: "..., against a pooled AUC of 0.81 for earlier models separating true progression from pseudoprogression at another institution \citep{zhang2026meta}."

#### johansson2015
**Metadata: OK.** Crossref: SLDS 2015, LNCS 9047, pp. 271-280, six authors match.
- **main.tex:399: OK, but I could not read the paper itself.** It is paywalled, with no open copy on Unpaywall and no abstract on Semantic Scholar.
  - Confirmation comes from the same group. Boström & Johansson 2020 (PMLR v128) say approaches "as suggested in (Johansson et al., 2015) ... [make] the approach less conservative for smaller bin sizes."
  - The paper studies regression, not classification sets, but the mechanism is the same.
  - Optional hedge: "..., as shown for Mondrian conformal regressors".
- **supplement.tex:592: OK** (low priority, not submitted).

#### taylor2022
**Metadata: OK.** Sci Rep 12(1):13258, 2022.
- **main.tex:61: OK.** All the numbers match:
  - "Thirty studies ... in 1372 patients".
  - "Thirteen of the included 30 studies were determined to have a high risk of bias".
  - "Three distinct methods across 25 studies" were pooled.
  - AUCs: DSC 0.93, DCE 0.90, DWI 0.93.
- **main.tex:889: OK.** "DWI, DSC-MRI and DCE-MRI have high potential for differentiating PsP and TTP".

#### pham2026
**Metadata: OK.** The PDF URL works (HTTP 200), and the authors' publication page lists the paper under EMBC 2026.
- **main.tex:875: OK.** The constraint prompt "disallows numeric measurements or interval values", and the base report "intentionally contains no numeric measurements". Optionally write "forbid numeric measurements".

#### ostrom2023
**Metadata: OK.** Crossref: Neuro-Oncology 25, Supplement_4, iv1-iv99. PubMed prints "25(12 Suppl 2)"; keep the publisher's version.
- **main.tex:50: OK.** "Gliomas accounted for 26.3% of all tumors ... glioblastoma (14.2% of all tumors and 50.9% of all malignant tumors)". The sentence states the US scope.

#### pedregosa2011
**Metadata: OK.** JMLR 12(85):2825-2830.
- **main.tex:354: OK.** Cited for the software used.

#### zech2018
**Metadata: OK.** PLOS Medicine 15(11):e1002683. The bib's "PLoS" is the old styling; changing it is optional.
- **main.tex:77: OK.** The pneumonia model picked up hospital-system and prevalence differences, a shortcut. It is cited only as an example.

#### vovk2022book
**Metadata: OK.** 2nd edition, Springer, Cham, 2022.
- **main.tex:396: OK.** Mondrian sets give validity within each group (Ch. 4, "Modifications of Conformal Predictors", pp. 107-142). I did not reopen the book; this is a standard result. Optionally cite `\citep[Ch.~4]{vovk2022book}`.

#### vancalster2019
**Metadata: OK.** BMC Medicine 17(1):230.
- **main.tex:540: OK.** "calibration intercept: has a target value of 0 ..."; "calibration slope: evaluates the spread of the estimated risks and has a target value of 1". The paper also recommends calibration curves, but citing it for intercept and slope only is not an error.

#### zolotova2023burdenko
**Metadata: OK.** DataCite 10.7937/E1QP-D183, TCIA 2023, 13 creators.
- **main.tex:890: OK.** Named as a future cohort: "a systematic data collection from 180 patients with primary glioblastoma ...".

#### Claims with no citation
- **main.tex:849:** "An earlier re-implementation of that model ranged from 0.32 to 0.88 over random held-out sets" has no source. If it is PRISM's own work, point to Section 3.1; if it is someone else's, it needs their citation. I found no outside source, so there is no DOI to offer.
- Nothing else is missing. RANO (wen2023, line 58), BT-RADS (weinberg2018, line 95) and the segmentation tools at line 313 are cited where first mentioned.

ACTIONABLE:
- main.tex:72 | zhang2026meta | The pooled 0.81 comes from 7 external cohorts (219 observations), not 31 studies; 0.91 vs 0.81 was not significant (P = 0.12); the true-progression-versus-pseudoprogression task is not stated | "In a meta-analysis of 31 studies separating true progression from pseudoprogression, seven external test cohorts gave a pooled AUC of 0.81, against 0.91 for internal test cohorts, a difference that was not statistically significant \citep{zhang2026meta}."
- main.tex:163-164 | zhang2026meta | The comparison models do a different task (true progression vs pseudoprogression) | "..., against a pooled AUC of 0.81 for earlier models separating true progression from pseudoprogression at another institution \citep{zhang2026meta}."
- main.tex:318-319 | deverdier2024 | The source says the BraTS 2024 UCSF data are UCSF-ALPTDG (its ref. 17); the sentence understates this | "The challenge's UCSF data are the UCSF-ALPTDG dataset, and the University of Missouri also contributed scans \citep{deverdier2024}, so its training data may include scans of patients in UCSF-ALPTDG and MU-Glioma-Post, but the network learned outlines only, with no progression label."
- main.tex:886 | deverdier2024 | Optional, same point as line 319 | "The BraTS 2024 data include the UCSF-ALPTDG dataset \citep{deverdier2024}, so the segmenter may have seen UCSF-ALPTDG patients."
- main.tex:849 | (none) | The "0.32 to 0.88" re-implementation has no source | If it is PRISM's own: "Our re-implementation of that model ranged from 0.32 to 0.88 over random held-out sets (Section~\ref{sec:3.1})"; otherwise cite its source.
- main.tex:399 | johansson2015 | Optional hedge (the paper studies regression; I could not read it, but a later paper by the same group confirms the claim) | "Small calibration groups make the thresholds conservative, as shown for Mondrian conformal regressors \citep{johansson2015}."
- main.tex:875 | pham2026 | Optional, more exact | "either forbid numeric measurements \citep{pham2026}"
### Batch 6

I checked all 13 keys in batch 6. No citation is wrong. Two citing sentences need a small wording fix, and three items are optional. I edited no repo file. The harness blocked writing the report to a .md file, so the full report is below.

I checked against repo commit c4c91b0. Line numbers are current main.tex lines, which sit 3 to 4 lines lower than in the batch file; the wording of the cited paragraphs has not changed. The extra matches at main.tex:312, 373 and 418 are `%` comments, so I did not audit them. Sources came from Crossref, PubMed, DataCite, the arXiv pages, the PMC page, the arXiv full texts of Zeba, Varoquaux, BTReport and Ding, and the audit3 copies.

#### fields2024
**Metadata:** OK. Radiology: Artificial Intelligence 6(4):e230182, 2024. All 11 authors match, in order.
- **main.tex:187** (cohort, UCSF-ALPTDG): OK.
- **main.tex:193** ("supplies two consecutive scans per patient"): OK. Source: "Two consecutive posttreatment scans were included for each patient, for a total of 596 scans."
- **main.tex:922** (ethics, approvals of the original studies): OK. Source: "HIPAA-compliant study was undertaken with approval from the UCSF Institutional Review Board; a waiver for informed consent was granted."
- **main.tex:928** (data use agreement): OK. Source: "readily available for public, noncommercial use after agreeing to a data use agreement" (imagingdatasets.ucsf.edu/dataset/2). Optional: add that URL.

#### angelopoulos2023
**Metadata:** OK. Foundations and Trends in Machine Learning 16(4):494–591, 2023.
- **main.tex:90:** OK. The source describes split-conformal sets whose coverage is at least 1−α on average.
- **main.tex:152** ("calibrated to contain the true outcome in 80% of scans"): MINOR.
  - The guarantee is a lower bound that holds on average, not an exact rate.
  - Because each patient is weighted once, the guarantee rests on patients, not scans.
  - Suggested fix: "calibrated to contain the true outcome in at least 80% of scans on average". The sentence is not in LOCKED.md.
- **main.tex:375** (split-conformal set, score 1−p̂(y)): OK. The per-patient weights and the cumulative-weight threshold are PRISM's own variant. The text presents them as PRISM's procedure, not as the source's, which is acceptable.

#### herasrivera2026
**Metadata:** MINOR. The arXiv and DataCite listings give 7 authors, which match the entry. The paper's own byline (arXiv HTML v1) lists 8 and adds Jacob Ruzevick after Low. Optional fix: insert "Ruzevick, J." after "Low, D. K.".
- **main.tex:98** (reports drafted from automated segmentations and measurements): OK. Source: masks "are derived from manual annotation or automated segmentation"; language models are used "only for syntactic structuring and narrative synthesis".
- **main.tex:443** ("This division of work… from extracted image features and demographics"): OK. Source: "deterministic feature extraction… then uses large language models only for syntactic structuring and narrative synthesis"; the features include "demographics, VASARI features, and 3D midline shift". Optional, to make the scope clear: "to write pre-operative brain tumour reports".
- **main.tex:873** ("Others use them to write reports before surgery"): MINOR.
  - The content is right: the source's dataset is "pre-operative mpMRI studies".
  - But "Others" is plural and rests on one citation.
  - Suggested fix: "Another system uses them to write reports before surgery from extracted image features and demographics \citep{herasrivera2026}."
  - The sentence before it has the same problem for jabal2026, which is outside this batch: "Another system uses language models to extract…".

#### vangriethuysen2017
**Metadata:** OK. Cancer Research 77(21):e104–e107, 2017.
- **main.tex:513** (PyRadiomics): OK. The 4,892 features, the 256 kept and LightGBM describe christodoulou2026's code, and the text does not credit them to this source.
- **supplement.tex:921** (LoG and wavelet filters in PyRadiomics): OK, low priority.

#### zeba2026
**Metadata:** OK. Expert Systems with Applications 329:132966, November 2026, 11 authors. The preprint is arXiv 2512.16189.
- **main.tex:105** ("tests each statement of a generated summary against the patient record"): OK. Source: "systematically verifying each proposition claim in a summary against the corresponding patient's EHRs".
- **main.tex:453** ("Similar rule-based checks test generated text against its source record"): OK.
  - Source: "a deterministic rule-based pipeline… logical rule-based evaluation… Each stage is independent of any large language reasoning model".
  - Strictly, the pipeline also uses a clinical entity recogniser and BioClinicalBERT/Sentence-BERT embeddings to match statements, so it is not purely rule-based.
  - Optional, more exact wording: "Similar checks without a language model test generated text against its source record".

#### ding2023
**Metadata:** OK. NeurIPS 36, pp. 64555–64576, DOI 10.52202/075280-2817, arXiv 2306.09335.
- **main.tex:401** (rare classes fall back to one pooled threshold): OK.
  - Source: the null cluster exists "to handle rare classes that do not have sufficient data".
  - Source: "For classes assigned to the null cluster, we compare the conformal score against the quantile that would be obtained from running standard [conformal] on the proper calibration set."
- **supplement.tex:594:** OK, low priority.

#### pencina2008
**Metadata:** OK. Statistics in Medicine 27(2):157–172. The issue is dated 2008; the article went online in 2007.
- **main.tex:80** ("what a model adds beyond what a clinician already knows"): OK as a paraphrase. The source evaluates what a new marker adds to an existing risk model.
- Not a citation error: Pencina argues that a rise in AUC is an insensitive measure of added value and proposes NRI and IDI instead. The manuscript measures added value by AUC drop and score share, and a reviewer may raise this.

#### rudin2019
**Metadata:** OK. Nature Machine Intelligence 1(5):206–215.
- **main.tex:82:** OK. Source: "There is a way forward - it is to design models that are inherently interpretable."

#### brandes2008
**Metadata:** OK. Journal of Clinical Oncology 26(13):2192–2197.
- **main.tex:55** (more often when the MGMT promoter is methylated): OK. Source: "PsPD was recorded in 21 (91%) of 23 methylated MGMT promoter and 11 (41%) of 27 unmethylated MGMT promoter (P = .0002) patients" (cohort of 103).

#### dice1945
**Metadata:** OK. Ecology 26(3):297–302.
- **main.tex:526:** OK (the Dice coefficient).

#### varoquaux2018
**Metadata:** OK. NeuroImage 180:68–77.
- **main.tex:486** (a single split of a small cohort gives a wide error): OK.
  - Source: "sample sizes… inherently lead to large error bars, eg ±10% for 100 samples".
  - Source: the variability "can clearly be traced to sampling noise in the test set".
  - The source also says repeated splitting "will not fix the problem of large error bars". This fits the text, which does not claim that repeated cross validation removes the error.

#### gagnon2026
**Metadata:** OK. Scientific Data 13(1):183, 2026, 20 authors. The title has a capital "Dataset", which is trivial.
- **main.tex:890** (UCSD-PTGBM as a further cohort): OK. Source: "243 timepoints on 178 subjects with histopathologically-proven glioblastoma".
- Optional: the same paragraph says no cohort had perfusion or diffusion imaging, and UCSD-PTGBM has both (RSI diffusion, ASL and DSC perfusion). This could be given as a reason to use it. No change is required.

#### tanno2025
**Metadata:** OK. Nature Medicine 31(2):599–608, 2025 (online 7 November 2024).
- **main.tex:101** (AI-written chest radiograph reports contained clinically significant errors): OK. Source: "24.8% of in/outpatient cases containing clinically significant errors in both report types, 22.8% in Flamingo-CXR reports only".

#### Uncited clauses
I found no missing citation in these paragraphs. PyRadiomics, LightGBM, Swin UNETR, BraTS 2024, ridge logistic regression, Mondrian sets, BT-RADS, RANO 2.0 and N4 are all already cited. "Patient records often cannot leave the hospital" (main.tex:105) is a general statement and can stay uncited.

ACTIONABLE:
- main.tex:873 | herasrivera2026 | "Others use them" is plural but rests on one cited system | "Another system uses them to write reports before surgery from extracted image features and demographics \citep{herasrivera2026}." (same fix in the sentence before, for jabal2026: "Another system uses language models to extract…")
- main.tex:152 | angelopoulos2023 | the guarantee is an average lower bound, but the text states an exact rate | "calibrated to contain the true outcome in at least 80% of scans on average" (not in LOCKED.md)
- references.bib (herasrivera2026) | herasrivera2026 | the paper's byline has 8 authors (adds Ruzevick, J.); the arXiv metadata has 7 | add "Ruzevick, J." after "Low, D. K." (optional)
- main.tex:453 | zeba2026 | "rule-based" slightly understates the source, which also matches statements with an entity recogniser and embeddings | "Similar checks without a language model test generated text against its source record" (optional)
### Batch 7

#### batch7: reference audit (report only, no repo files edited)

Line numbers are from the current `/tmp/sbandred-prism/repo/paper/main.tex`. Several have moved since batch7.md was made: 183→186, 323→327, 387→391, 428→432, 786/787→790/791, 872→876, 877→881, 923→927. The extra hits at `main.tex:373` (mehrtens2023) and `main.tex:418` (kwon2023) are LaTeX `%` comments, not citations.

---

#### mehrtens2023
**Metadata: OK.** Crossref: "Pitfalls of Conformal Predictions for Medical Image Classification", LNCS (UNSURE 2023), pp. 198–207, 2023, three authors: Mehrtens, Bucher (Tabea-Clara), Brinker. Preprint is arXiv:2506.18162.

- **main.tex:90 ("not within each subgroup"): OK.** The abstract says conformal predictions "are not reliable for subsets of the data, such as individual classes or patient attributes". Section 4 says "it does not guarantee this for individual instances or structured subgroups of the data."
- **main.tex:91 ("it does not hold under distribution shift"): MINOR.** The source says CP is "unreliable under distributional shifts in input and label variables". That is an empirical failure: the guarantee is not assured. It does not say coverage always fails. Suggested fix: "and it is not guaranteed under distribution shift \citep{mehrtens2023}."
- **main.tex:391 (exchangeability): OK.** "Conformal predictions … only necessitate the property of exchangeability between the datasets Dcal and Dtest."
- **main.tex:881 (average over scans, not within each group): OK.** Same Section 4 quote as line 90.

#### yaseen2025tcia
**Metadata: MINOR.** DataCite and the TCIA page give the dataset as "University of Missouri Post-operative Glioma Dataset (MU-Glioma-Post)", Version 1 (updated 2025/03/21), 203 subjects, CC BY 4.0. The TCIA citation spells two authors more fully: "Layfield, L. J." and "Tahon, N. H. M." Suggested fix: use `Layfield, L. J.` and `Tahon, N. H. M.`, and add `(Version 1) [Data set]` to howpublished. The title and DOI are correct.

- **main.tex:186: OK.** The dataset is the MU-Glioma-Post release.
- **main.tex:927: OK.** "available from The Cancer Imaging Archive" is correct and the dataset is CC BY 4.0. (Not this key: the same sentence's UCSF-ALPTDG data use agreement sits uneasily with "three public cohorts" at line 186. Leave it to the fields2024 audit.)
- **supplement.tex:32: OK.** Low priority, since the supplement is not submitted.

#### thust2018
**Metadata: OK.** European Radiology 28(8):3306–3317, 2018, 14 authors, first author Thust S. C. PMC6028837.

- **main.tex:94: OK.** The abstract says: "Responses were received from 220 institutions… For follow-up, most sites (60%) issue qualitative reports, while 27% report an assessment according to the RANO criteria. A minority of sites use a reporting template (23%)." Optional, closer wording: "60% issued qualitative follow-up reports".
- **supplement.tex:350: OK.** Same quote.

#### mansour2026
**Metadata: OK.** arXiv:2610.34599, published 25 October 2026. Title and the seven authors match.

- **main.tex:98: OK.** The abstract says segmentation feeds "deterministic quantification" and "an LLM organizes findings into predefined schemas with numerical consistency verification" for liver lesions.
- **main.tex:876 ("trace them without reporting a test of the check itself"): OK.** Section III-E has "numerical consistency checking against the source measurement JSON. Values without a corresponding computational source are flagged for review." No test of the checker is reported, and the paper says "Reporting accuracy and clinical usability were not quantitatively evaluated."

#### cardoso2022monai
**Metadata: OK.** DataCite 10.48550/arXiv.2211.02701, "MONAI: An open-source framework for deep learning in healthcare", 2022. The first four authors match (57 in total).

- **main.tex:327: OK.** It is cited as the framework that released the Swin UNETR; the pipeline details are the authors' own.
- **supplement.tex:250: OK.** Low priority.

#### qwen2026b
**Metadata: OK.** The Hugging Face cards for Qwen/Qwen3.5-2B, 4B, 9B and 35B-A3B (Apache-2.0, created 24–28 Feb 2026) carry exactly this BibTeX: `@misc{qwen3.5, title={{Qwen3.5}: Towards Native Multimodal Agents}, author={{Qwen Team}}, month={February}, year={2026}, url={https://qwen.ai/blog?id=qwen3.5}}`.

- **main.tex:790 and 791: OK.** The blog's launch announcement names only Qwen3.5-397B-A17B. The smaller models came out about a week later, but their own model cards point to this blog and ask for this citation, so it is acceptable. I could not fetch the qwen.ai page itself because it is a JavaScript page.

#### collins2024
**Metadata: OK.** BMJ 385:e078378, 16 April 2024, Collins, Moons, Dhiman et al. (34 authors).

- **supplement.tex:232: OK.** Low priority.

#### kwon2023
**Metadata: OK.** SOSP '23, ACM, pp. 611–626, nine authors matching exactly.

- **main.tex:432: OK.** vLLM is the PagedAttention serving system this paper introduced.

#### saporta2022
**Metadata: OK.** Nature Machine Intelligence 4(10):867–878, 2022, 12 authors matching.

- **main.tex:81: MINOR (scope).** The paper is on chest radiographs only: "all seven performed significantly worse compared with the human benchmark". It does not test weight randomisation, but Arun covers that part. Both cited studies are chest-radiograph studies, while the sentence reads as a general claim. Suggested fix: "In chest radiographs, saliency maps drawn after the fact localise abnormalities poorly and can be insensitive to the model's own weights \citep{arun2021,saporta2022}."

#### wen2010
**Metadata: OK.** J Clin Oncol 28(11):1963–1972, 2010, 19 authors, PMID 20231676.

- **main.tex:55: OK, but not checked against the full text.** ASCO returned 403 and PubMed and Europe PMC were blocked. Web-search summaries of the paper give "chemoradiotherapy for newly diagnosed glioblastomas results in pseudoprogression in 20% to 30% of patients". The well-known body sentence is about 20–30% of patients at their first post-radiation MRI. The citing clause matches. Re-check against the PDF if one is available.

#### arun2021
**Metadata: MINOR.** Crossref has Radiology: Artificial Intelligence 3(6), 2021 and 13 authors, matching the entry. It lists no page or article number, so `e200267` cannot be confirmed from Crossref; RSNA uses that e-number format.

- **main.tex:81: OK, with the scope caveat under saporta2022.** The abstract says: "All eight saliency map techniques failed at least one of the criteria and were inferior in performance compared with localization networks… Five and two saliency methods (of eight) failed the model randomization test… suggesting that these methods are not sensitive to changes in model parameters." The datasets were chest radiographs (SIIM-ACR pneumothorax and RSNA pneumonia).

#### kofler2025
**Metadata: OK.** DataCite: arXiv:2506.13807, 2025. The first six authors match (37 in total).

- **main.tex:316: OK.** The full text says the orchestrator depends on Docker ("This dependency necessitates the installation of Docker") and covers the "BraTS 2023 and BraTS 2024 challenges".

#### leone2023
**Metadata: OK.** Neuro-Oncology Advances 5(1):vdad016, 2023, 14 authors matching. PMC10034916.

- **main.tex:63: OK.** The abstract says: "105 patients with GB who developed a suspected imaging PsPD in the first 7 months after standard CRT… the addition of median ADC and nrCBV values resulted in a nonsignificant increase in performance (AUC = 0.71…, P = .416)" over the clinical + MGMT model. Optional: add "at one centre" to match the "In one cohort" style at line 55.

#### nowak2025
**Metadata: OK.** Radiology 314(1), 2025, 12 authors matching. Article number e240895 follows the DOI pattern.

- **main.tex:107: OK.** The abstract says: "privacy-ensuring open-weights LLMs being competitive with closed-weights GPT-4o" for extracting chest radiograph findings. Its data were 3,927 English and 18,500 German reports.

---

#### Missing citations
Every tool, dataset, model and method named in these paragraphs is cited. I found none that clearly needs a new citation.

---

ACTIONABLE:
- main.tex:91 | mehrtens2023 | "does not hold under distribution shift" is stronger than the source's "unreliable under distributional shifts" | change to "and it is not guaranteed under distribution shift \citep{mehrtens2023}."
- main.tex:81 | arun2021, saporta2022 | both studies are chest-radiograph studies; the sentence states a general claim | change to "In chest radiographs, saliency maps drawn after the fact localise abnormalities poorly and can be insensitive to the model's own weights \citep{arun2021,saporta2022}."
- references.bib | yaseen2025tcia | author initials and version do not match the TCIA recommended citation | use `Layfield, L. J.` and `Tahon, N. H. M.`, and add "(Version 1) [Data set]" to howpublished
- main.tex:55 | wen2010 | 20–30% confirmed only from secondary sources (full text blocked) | no wording change; check the sentence against the JCO PDF
- references.bib | arun2021 | pages `e200267` not confirmed by Crossref (no page or article number there) | confirm on the RSNA page and keep if it matches
### Missing-citation sweep

#### Citation-gap audit of paper/main.tex (report only, no files changed)

Source audited: `/tmp/sbandred-prism/repo/paper/main.tex` at commit caf5944 (933 lines), with `refs.bib`.
Scope: uncited factual or clinical claims, uncited named tools, datasets, methods and metrics, claims about prior work
with no source, places where a stronger source fits better, and `\cite` keys placed on the wrong clause. The
manuscript's own design, methods and results are not flagged. Lines starting with `%` were skipped.

Verification: each proposed reference was opened (arXiv, Crossref, publisher, GitHub or model card) unless marked
"title-level only" (the publisher page returned 403, so support rests on the title or on an earlier audit).

#### 1. Mechanical checks

| Check | Result |
|---|---|
| Undefined `\cite` keys | none (81 keys cited, all in refs.bib) |
| Duplicate bib keys | none (132 entries) |
| Undefined `\ref` | none |
| Duplicate `\label` | none |
| Labels never referenced | `sec:1` (harmless) |
| Supplement references in non-comment text | **none**. "Supplementary Section S10" appears only in `%` comments (lines ~385, 690, 802); see item C1 |
| Cited entries without DOI | `gemma2026` (arXiv:2607.02770, so DOI 10.48550/arXiv.2607.02770 exists); `mansour2026` (arXiv:2610.34599, so DOI 10.48550/arXiv.2610.34599 exists, and the entry has no url); `ke2017` (NeurIPS, no DOI, add the proceedings URL); `pedregosa2011` (JMLR, no DOI, URL present, fine); `pham2026` (EMBC 2026 author copy; add the IEEE DOI once indexed); `qwen2026`, `qwen2026b`, `btradsweb` (web sources, no DOI, fine) |

`qwen2026` check: the Qwen3.8-27B model card (https://huggingface.co/Qwen/Qwen3.8-27B) recommends exactly this
BibTeX ("Qwen3.8-Max: A New Bar for Coding and Cowork", Qwen Team, Aug 2026), so the entry is correct even though
its title names Max. `gemma2026`: the arXiv abstract gives the family as "ranging from 2.3B to 31B parameters". It
does not name E4B. Confirm that the body of the report covers E4B before citing it for that model (line 790).

#### 2. Findings, line by line

| # | main.tex line | Clause | Proposed reference | Supporting quote / evidence | Priority |
|---|---|---|---|---|---|
| F1 | 489, 593, 851 | "drawn as in an earlier re-implementation of that study"; "an earlier re-implementation of the radiomics model ranged from 0.32 to 0.88"; "An earlier re-implementation of that model ranged from 0.32 to 0.88" | **No external source exists.** Per docs/results/CHRISTODOULOU_REPLICATION.md this is the authors' own first re-implementation, which was moved to the supplement, and the supplement is not submitted. As written, it reads as a claim about prior work with no source. | CHRISTODOULOU_REPLICATION.md l.337: "this faithful run replaces the first re-implementation as the paper's comparison, and the first re-implementation moves to the supplement" | MUST |
| F2 | 157-158 (also 38) | "single held-out splits of 18 patients, the design of earlier studies on this cohort \citep{christodoulou2026}" | Keep christodoulou2026, but the cite does not support "18 patients": line 76 says that study held out **30 patients**. "Studies" is plural but has one source. | main.tex 76: "evaluated on a single held-out set of 30 patients (AUC 0.80) \citep{christodoulou2026}" | MUST |
| F3 | 65-66 | "Machine learning models for this decision are mostly built on the image alone and tested only within the cohort they were developed on." (no cite in the sentence) | booth2022 (in bib, already cited on the next sentence for another clause): Booth TC et al. Imaging biomarkers of glioblastoma treatment response: a systematic review and meta-analysis of recent machine learning studies. Front Oncol 2022;12:799662. doi:10.3389/fonc.2022.799662; plus shi2025 and park2020, as at Discussion line 847-848 | Booth 2022 (opened): "Most studies only analyzed imaging features alone (15/18, 83%)"; "A third of studies had external hold-out test sets (6/18, 33%)." | SHOULD |
| F4 | 105-106 | "Patient records often cannot leave the hospital, so the model should also run locally." | mukherjee2023 (in bib, cited one sentence later): Mukherjee P, Hou B, Lanfredi RB, Summers RM. Feasibility of using the privacy-preserving large language model Vicuna for labeling radiology reports. Radiology 2023;309(1):e231147. doi:10.1148/radiol.231147. Move or repeat the cite onto this clause. | Title-level only (RSNA 403): "privacy-preserving large language model". | SHOULD |
| F5 | 146 | "Swin UNETR trained on BraTS 2021 \citep{hatamizadeh2022}": BraTS 2021 is named at first mention with no dataset cite | baid2021 (in bib, cited only at line 333): Baid U et al. The RSNA-ASNR-MICCAI BraTS 2021 benchmark on brain tumor segmentation and radiogenomic classification. arXiv:2107.02314. doi:10.48550/arXiv.2107.02314 | Title names the BraTS 2021 benchmark | SHOULD |
| F6 | 187 | "the primary population was grade 4 glioma" (grading system unnamed and uncited) | NEW: Louis DN, Perry A, Wesseling P, et al. The 2021 WHO Classification of Tumors of the Central Nervous System: a summary. Neuro-Oncology 2021;23(8):1231-1251. doi:10.1093/neuonc/noab106 | Opened: glioblastoma IDH-wildtype is fixed at CNS WHO grade 4, and astrocytoma IDH-mutant can be grade 4 ("CDKN2A/B homozygous deletion results in a CNS WHO grade of 4"). | SHOULD |
| F7 | 193 | "LUMIERE rates every scan" | suter2022 (in bib): Suter Y et al. The LUMIERE dataset: Longitudinal glioblastoma MRI with expert RANO evaluation. Sci Data 2022. doi:10.1038/s41597-022-01881-7. Here only fields2024 is cited, at the end of the UCSF clause. | Title: "Longitudinal glioblastoma MRI with expert RANO evaluation" (title-level only; nature.com redirected to login) | SHOULD |
| F8 | 322-323 | "At MU-Glioma-Post and UCSF-ALPTDG, they mark the same four regions." | mahmoud2025 (doi:10.1038/s41597-025-06011-7) and fields2024 (doi:10.1148/ryai.230182), both in bib | Titles: "MU-Glioma Post: A comprehensive dataset of automated MR multi-sequence segmentation..."; the UCSF ALPTDG dataset paper (RSNA 403, title-level only). Earlier audit batches verified both. | SHOULD |
| F9 | 316-317 | "It marks the enhancing tumour, the non-enhancing tumour core ..., FLAIR hyperintensity and the resection cavity." | deverdier2024 (in bib), doi:10.48550/arXiv.2405.18368 | Opened: "four distinct tumor sub-regions consisting of enhancing tissue (ET), surrounding non-enhancing T2/fluid-attenuated inversion recovery (FLAIR) hyperintensity (SNFH), non-enhancing tumor core (NETC), and resection cavity (RC)." | OPTIONAL |
| F10 | 318-319 / 897 | "The challenge's data were contributed by centres including UCSF and the University of Missouri \citep{deverdier2024}" | Correct, verified. No change. | Opened (arXiv HTML): "Duke University, University of California San Francisco (UCSF; which consists of the previously described UCSF Longitudinal Post-Treatment Diffuse Glioma [UCSF-LPTDG]), University of Missouri Columbia, ..." | (verified) |
| F11 | 342 and 362 | 12-week window after radiotherapy (time-window input; "first 12 weeks after radiotherapy") | wen2023 (in bib): Wen PY et al. RANO 2.0. J Clin Oncol 2023. doi:10.1200/JCO.23.01059. It is cited in the Introduction (line 61) for this rule but not in Methods. | main.tex 61 already uses it for "within 12 weeks of radiotherapy" | OPTIONAL |
| F12 | 218 (Table 1) | "DeepBraTumIA (three labels)": named tool with no cite in the table | suter2022 (it is cited at line 323 in the text, so the table could carry it) | as F7 | OPTIONAL |
| F13 | 511-516 | "with its authors' public code and settings"; "The authors' code labels every scan of a patient who ever progressed as progression." The claim is about the content of prior work's code, and the code is not cited. | NEW @misc for the authors' repository: https://github.com/georgeDV2002/Explainable-Radiomics-with-Probability-Calibration-for-Postoperative-Glioblastoma-Surveillance (accessed date, commit hash). **Caution:** when opened, this repo's README title read "Explainable, Modality-Adaptive Radiomics for MGMT Methylation Prediction in High-Grade Glioma". Check that this is the correct repo and commit before citing it. CHRISTODOULOU_REPLICATION.md l.25 and l.30 list two different repos. | CHRISTODOULOU_REPLICATION.md l.33-36 quotes README section 4: "`y = 1` (progression) if `Time to First Progression (Days)` is non-missing for that patient" | SHOULD |
| F14 | 436 | "Its output is constrained to a JSON schema" (constrained-decoding method or tool unnamed) | NEW (choose whichever backend vLLM actually used): Willard BT, Louf R. Efficient guided generation for large language models. arXiv:2307.09702. doi:10.48550/arXiv.2307.09702 (Outlines). Or cite the vLLM structured-outputs backend actually used (e.g., xgrammar) in the run config. | Opened: the framework constrains output to "regular expressions and context-free grammars ... implemented in the open-source Outlines library" | OPTIONAL |
| F15 | 468-469 | "Planted errors are also used to evaluate other factuality checks \citep{gabriel2021}" | Add rao2025rexerr (in bib): Rao VM et al. ReXErr: Synthesizing clinically meaningful errors in diagnostic radiology reports. PSB 2025;30:70-81. doi:10.1142/9789819807024_0006. It is closer to the domain (radiology reports). kryscinski2020 (uncited, doi:10.18653/v1/2020.emnlp-main.750) uses rule-based error injection to build **training** data, so cite it only if the clause says "train or evaluate". | main.tex 105 already cites ReXErr for "developing and testing methods". Kryscinski abstract (opened): "Training data is generated by applying a series of rule-based transformations to the sentences of source documents." | OPTIONAL |
| F16 | 472 | "a separate language model that had not seen them rewrote the synthetic reports": the model is unnamed in Methods (named only in the AI declaration, line 910, as Claude) | Name the model and version in Methods (no bibliographic cite needed; give the vendor and model ID). | Declaration line 910-912 | OPTIONAL |
| F17 | 484, 535, 573 | AUC / ROC used as the primary metric with no metric citation | NEW: Hanley JA, McNeil BJ. The meaning and use of the area under a receiver operating characteristic (ROC) curve. Radiology 1982;143(1):29-36. doi:10.1148/radiology.143.1.7063747 | Crossref metadata opened. The method is standard; this is a reviewer convenience. | OPTIONAL |
| F18 | 350-352 | "The ridge (L2) penalty pulls the weights towards zero. This keeps them stable when there are many correlated inputs and few patients." | lecessie1992 (in bib, cited on line 349) already covers ridge logistic regression; optionally repeat it at the end of the stability sentence. | Earlier audit verified lecessie1992 for ridge logistic regression | OPTIONAL |
| F19 | 411 | "95% CIs from 1,000 bootstrap samples of patients" (reliability card) | field2007 (in bib): Field CA, Welsh AH. Bootstrapping clustered data. JRSS-B 2007;69(3):369-390. doi:10.1111/j.1467-9868.2007.00593.x. It is cited later at line 536, so a forward reference to the Statistics paragraph is enough. | | OPTIONAL |
| F20 | 780 | "BT-RADS denotes the Brain Tumor Reporting and Data System." | weinberg2018 (in bib) beside btradsweb, so the caption gives the primary paper | Earlier audit verified weinberg2018 as the BT-RADS source | OPTIONAL |
| F21 | whole paper | No reporting guideline named. The paper develops and externally validates a clinical prediction model, so reviewers may ask for TRIPOD+AI. | collins2024 (in bib, uncited): Collins GS et al. TRIPOD+AI statement. BMJ 2024;385:e078378. doi:10.1136/bmj-2023-078378. Cite it only if a TRIPOD+AI checklist is actually completed and submitted. | | OPTIONAL |

Clauses checked and found adequately cited (no action): lines 52-61 (ostrom2023, stupp2005, weller2021, wen2010,
brandes2008, taal2008, wen2023); 64-68 (taylor2022, kim2019, leone2023); 66-77 (booth2022, park2020, shi2025,
an2021, yu2022, zhang2026meta, christodoulou2026); 79-87; 89-92 (conformal); 94-106 (reports and LLM errors);
138-140 (jabal2026); 314-316 (isensee2021, roy2023, hatamizadeh2022, kofler2025); 330-333 (cardoso2022monai,
baid2021); 354 (pedregosa2011); 366 (stupp2005, six-week course); 380-404 (conformal block); 431 (qwen2026, kwon2023);
444-448 (herasrivera2026, btradsweb, weinberg2018, gore2019); 457-459 (zeba2026, wiseman2017); 486 (an2021,
varoquaux2018); 496 (beaulieujones2021); 513-515 (vangriethuysen2017, ke2017); 525 (dice1945); 536-542 (field2007,
vancalster2019); 751, 790 (gemma2026, qwen2026, qwen2026b, see the E4B note above); Discussion 847-848 (booth2022
verified for "image alone" 15/18 and for "external" 6/18); 856-900.

Uncited bib entries checked and not needed for any clause: akiba2019, platt1999 (used only in supplement text),
tustison2010 (no N4 step is described in main.tex), uno2007, blanche2013, hung2010, riley2020, kocak2023,
zwanenburg2020 (no radiomics feature definition in main.tex beyond PyRadiomics), tak2025 (only in figure-design
comments), rudie2022 (could support line 84 "post-treatment segmentation is harder", OPTIONAL, not verified this pass).

#### 3. Other cite / ref problems

- C1. Supplement: no non-comment reference. Indirectly, F1 depends on content that exists only in the supplement.
- C2. `gemma2026` and `mansour2026` are missing DOIs that exist (arXiv DOIs). `mansour2026` also has no `url`.
- C3. `ke2017` is missing a URL: https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html (verified: the page title is the LightGBM paper).

ACTIONABLE:
paper/main.tex:489 | "drawn as in an earlier re-implementation of that study" cites no source; the re-implementation is the authors' own and now appears only in the unsubmitted supplement | Rephrase as the authors' own procedure and state the draw rule inline (e.g., "drawn at random, 18 of the 92 grade 4 patients per set"), or delete the clause
paper/main.tex:593 | "an earlier re-implementation of the radiomics model ranged from 0.32 to 0.88" is a result with no source and no Methods description in main.tex | Either describe this re-implementation in Methods as the authors' own analysis or delete the sentence
paper/main.tex:851 | Same unsourced "earlier re-implementation" result repeated in the Discussion | Delete it or align it with whatever is decided for line 593
paper/main.tex:157-158 | "single held-out splits of 18 patients, the design of earlier studies on this cohort \citep{christodoulou2026}" contradicts line 76 (30 patients), and "studies" is plural with one source | Write "a single held-out split, the design of an earlier study on this cohort \citep{christodoulou2026}" and give the 18-patient size as PRISM's own choice
paper/main.tex:38 | Abstract "the design of earlier studies" has the same plural-with-one-source problem | Change to "the design of an earlier study"
paper/main.tex:65 | Topic sentence (image alone, tested only within cohort) has no cite | Append \citep{booth2022,shi2025,park2020}
paper/main.tex:105-106 | "Patient records often cannot leave the hospital" is uncited | Add \citep{mukherjee2023} after "run locally"
paper/main.tex:146 | BraTS 2021 named without its dataset cite | Change to "trained on BraTS 2021 \citep{baid2021}"
paper/main.tex:187 | "grade 4 glioma" has no grading-system cite | Add a new bib entry louis2021 (doi:10.1093/neuonc/noab106) and write "CNS WHO grade 4 glioma \citep{louis2021}"
paper/main.tex:193 | "LUMIERE rates every scan" is uncited | Add \citep{suter2022} after "every scan"
paper/main.tex:322-323 | "they mark the same four regions" is uncited | Add \citep{mahmoud2025,fields2024}
paper/main.tex:511,516 | The authors' public code is described but not cited | Add an @misc entry for the Christodoulou repository with URL, access date and commit, after confirming which of the two repos in CHRISTODOULOU_REPLICATION.md is correct
paper/main.tex:316-317 | The four BraTS 2024 labels are uncited | Optionally add \citep{deverdier2024}
paper/main.tex:342 | The 12-week window in Methods is uncited | Optionally add \citep{wen2023}
paper/main.tex:218 | Table 1 names DeepBraTumIA without a cite | Optionally write "DeepBraTumIA \citep{suter2022} (three labels)"
paper/main.tex:436 | The JSON-schema constrained decoding method is unnamed | Optionally name the vLLM structured-output backend and cite it (e.g., willard2023, doi:10.48550/arXiv.2307.09702)
paper/main.tex:468-469 | The planted-error precedent rests on one general-domain cite | Optionally add rao2025rexerr: \citep{gabriel2021,rao2025rexerr}
paper/main.tex:472 | The error-writing language model is unnamed in Methods | Optionally name the model and version (as in the declaration)
paper/main.tex:484 | The AUC metric is uncited | Optionally add a hanley1982 entry (doi:10.1148/radiology.143.1.7063747)
paper/main.tex:780 | The BT-RADS expansion cites only the web template | Optionally add \citep{weinberg2018}
paper/main.tex:790 | gemma2026 is cited for Gemma-4 E4B, but the arXiv abstract does not name E4B | Confirm that the report body covers E4B; if it does not, cite the Gemma 4 model card for E4B
paper/refs.bib:gemma2026 | DOI missing | Add doi = {10.48550/arXiv.2607.02770}
paper/refs.bib:mansour2026 | DOI and url missing | Add doi = {10.48550/arXiv.2610.34599} and url = {https://arxiv.org/abs/2610.34599}
paper/refs.bib:ke2017 | No DOI exists and the URL is missing | Add url = {https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html}
paper/refs.bib:pham2026 | Author-copy URL only | Replace it with the IEEE EMBC DOI once one is issued
