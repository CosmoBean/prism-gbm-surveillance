# Prior art for the three methods contributions (adversarial search, 2026-11-15)

Scope: web and published literature only; no project data or outputs were opened. `paper/refs.bib` was read to see
what is already cited. Marks: **[V]** existence and key content checked online this session (abstract page, full text,
or publisher record); **[V-meta]** existence and bibliographic data checked, content not read beyond the abstract;
**[U]** not verified, or a detail (DOI, venue) given from memory. Builds on `NOVELTY_SEARCH_2026-11-12.md`.

Note on existing keys: `barber2021` in refs.bib is the jackknife+ paper and `vovk2015` is cross-conformal. The
papers recommended below need new keys (`barber2021limits`, `vovk2013`, `vovk2022book`).

---

## M1. Within-context / across-context decomposition of the AUC

### (a) Closest work

1. **Kallus N, Zhou A. 2019.** The fairness of risk scores beyond classification: bipartite ranking and the xAUC
   metric. *NeurIPS 32*. arXiv:1902.05826. **[V]** (Proposition 1 read on ar5iv).
2. **Sudjianto A, Liu AJ. 2025.** Decomposing global AUC into cluster-level contributions for localized model
   diagnostics. arXiv:2508.07495. **[V]** (full HTML read).
3. **Matos J, Van Calster B, Riley RD, Dhiman P, Collins GS. 2026.** Collapsibility of performance metrics in
   clinical predictive AI. arXiv:2608.30568. **[V]** (HTML read).
4. **Borkan D, Dixon L, Sorensen J, Thain N, Vasserman L. 2019.** Nuanced metrics for measuring unintended bias with
   real data for text classification. *Companion Proc. WWW 2019*. arXiv:1903.04561. **[V]** (definitions read;
   DOI 10.1145/3308560.3317593 **[U]**).
5. **Janes H, Pepe MS. 2009.** Adjusting for covariate effects on classification accuracy using the
   covariate-adjusted receiver operating characteristic curve. *Biometrika* 96(2):371-382. doi:10.1093/biomet/asp002.
   **[V]**. (Companion: Janes & Pepe 2008, Am J Epidemiol, already cited as `janes2008`; Janes, Longton & Pepe 2009,
   *Stata J* 9(1):17-39 **[V-meta]**.)
6. **Van Oirbeek R, Lesaffre E. 2012.** Assessing the predictive ability of a multilevel binary regression model.
   *Comput Stat Data Anal* 56(6):1966-1980. doi:10.1016/j.csda.2011.11.023. **[V-meta]**. (Also Van Oirbeek &
   Lesaffre 2010, An application of Harrell's C-index to PH frailty models, *Stat Med* 29(30):3160-3171,
   doi:10.1002/sim.4058 **[V-meta]**.)

Supporting / framing (cite selectively):
- Tsue T, Mombourquette B, Taha A, Matthews TP, Vu YNT, Su J. 2023. Problems and shortcuts in deep learning for
  screening mammography. arXiv:2303.16417. **[V]** ("AUC paradox": pooled US+UK AUC 0.945 vs 0.838/0.892 within
  each dataset, driven by prevalence differing by dataset and the model scoring the dataset; no formal decomposition).
- Beutel A et al. 2019. Fairness in recommendation ranking through pairwise comparisons. *KDD 2019*, 2212-2220.
  arXiv:1903.00780. **[V-meta]** (intra-group vs inter-group pairwise accuracy; DOI 10.1145/3292500.3330745 **[U]**).
- Obuchowski NA. 1997. Nonparametric analysis of clustered ROC curve data. *Biometrics* 53(2):567-578. **[V-meta]**
  (DOI 10.2307/2533958 **[U]**). Variance of AUC under clustering; does not decompose by stratum. Relevant only for
  the confidence interval of each term if scans cluster within patients.
- Shortcut learning: Geirhos et al. 2020 *Nat Mach Intell* 2:665-673, doi:10.1038/s42256-020-00257-z **[V]**;
  DeGrave, Janizek & Lee 2021 *Nat Mach Intell* 3:610-619, doi:10.1038/s42256-021-00338-7 **[V]**; Zech et al. 2018
  *PLoS Med* 15(11):e1002683, doi:10.1371/journal.pmed.1002683 **[V]**; Oakden-Rayner et al. 2020 *ACM CHIL*,
  doi:10.1145/3368555.3384468 **[V]**; Brown, Tomasev, Freyberg, Schrouff 2023 *Nat Commun* 14:4314,
  doi:10.1038/s41467-023-39902-7 **[V]**; Badgeley 2019 (already cited).

### (b) What they already do

- **Kallus & Zhou, Prop. 1** state exactly the identity
  AUC = sum over (a, b) of Pr[A=a | Y=1] Pr[A=b | Y=0] Pr[R1^a > R0^b],
  i.e. the overall AUC is a weighted sum of within-group AUCs (a = b) and cross-group xAUCs (a != b), with weights
  equal to the share of positive-negative pairs in each group combination. They also decompose ranking loss into a
  within-group part and a cross-group "discrepancy" part, and audit real risk scores (recidivism, income, cardiac
  arrest) with it. They do **not** study how the terms change when features are added.
- **Sudjianto & Liu 2025** restate the same identity for arbitrary clusters (w_ij = |P_i||N_j| / |P||N|), separate
  diagonal (intra-cluster) from off-diagonal (inter-cluster) terms and use it for model diagnostics in credit and
  fraud data. They do not cite Kallus & Zhou, do no feature-block ablation, and have no medical application.
- **Matos et al. 2026** (Van Calster, Riley, Collins) use the same decomposition (citing Kallus & Zhou) to show AUC
  is non-collapsible: overall AUC can fall outside the range of subgroup AUCs; worked clinical example EuroSCORE II by
  sex; recommend reporting composition and prevalences with subgroup AUCs. This is the clinical-prediction community
  already knowing the identity; reviewers from that community will expect it to be cited.
- **Borkan et al. 2019**: Subgroup AUC (within subgroup), BPSN AUC (background positives vs subgroup negatives) and
  BNSP AUC (background negatives vs subgroup positives) are exactly cross-group pair AUCs for one subgroup vs the
  rest. They do **not** state an exact weighted decomposition of the overall AUC.
- **Janes & Pepe 2008/2009**: the pooled ROC differs from the covariate-adjusted ROC when a covariate is associated
  with both disease and marker; AROC(t) = E[ROC(t | Z_D)], a weighted average of covariate-specific ROCs with weights
  from the *case* distribution of the covariate. This is the established "within-stratum accuracy" estimand; it
  differs from the pair-share-weighted within part only in the weights (cases only vs n1z*n0z pairs). No across term.
- **Van Oirbeek & Lesaffre** define within-cluster, between-cluster and overall C-indices for multilevel binary and
  frailty models.
- **Tsue et al. 2023** document the inflation empirically in medical imaging ("AUC paradox") and recommend
  stratified evaluation, but give no formula.

### (c) Verdict: **ALREADY DONE (identity); PARTIAL (use)**

The decomposition itself, including pair-share weights and the within / across split, is published (Kallus & Zhou
2019; restated 2025 and 2026, the latter in clinical prediction). The idea that pooled AUC is inflated by a stratum
variable associated with both outcome and score is Janes & Pepe 2008/2009 and Tsue 2023. Nothing found that:
(i) uses the across-context term as a measure of discrimination obtainable from the context alone (a score constant
within each stratum has within-context AUC 0.5 and all its excess discrimination in the across term);
(ii) attributes the AUC gain from adding an input block (e.g. imaging to clinical/timing inputs) to the change in
the within term versus the change in the across term; and (iii) compares those parts across external centres with
strata defined by treatment timing.

Narrowest defensible claim: *"We use the pair decomposition of the AUC (Kallus & Zhou 2019) as an audit of context
reliance: the across-context term measures what treatment timing alone buys, and the change in each term when an
input block is added shows whether that block adds discrimination within a timing window or only between windows;
we report both terms at each external centre."* Do not say "we introduce a decomposition"; say "we use" or "we
apply". The delta-per-block reading and the external comparison are the contribution, and they are modest.
Caveat to state: the within term is a pair-weighted stratified AUC, so it is weighted toward strata with many
positives and negatives; give the per-stratum AUCs or the Janes-Pepe AAUC as a sensitivity check.

### (d) Must cite
kallus2019 (essential), matos2026 (essential: same identity, clinical setting, same author network as the
TRIPOD reviewers), janes2009 (plus existing janes2008), borkan2019, sudjianto2025; one or two shortcut papers
(geirhos2020, degrave2021 or zech2018, oakdenrayner2020) and tsue2023 for the imaging AUC paradox. Optional:
vanoirbeek2012, beutel2019.

---

## M2. Group-conditional (Mondrian) conformal sets with clinical-context groups and a small-group rule

### (a) Closest work

1. **Vovk V. 2013.** Conditional validity of inductive conformal predictors. *Mach Learn* 92:349-376.
   doi:10.1007/s10994-013-5355-6. arXiv:1209.2673. **[V-meta]**. With **Vovk V, Gammerman A, Shafer G. 2022.**
   *Algorithmic Learning in a Random World*, 2nd ed., Springer. doi:10.1007/978-3-031-06649-8. **[V-meta]** (Mondrian
   conformal predictors; object-, label- and category-conditional validity).
2. **Romano Y, Barber RF, Sabatti C, Candès EJ. 2020.** With malice toward none. *HDSR*. (already cited, `romano2020`).
3. **Foygel Barber R, Candès EJ, Ramdas A, Tibshirani RJ. 2021.** The limits of distribution-free conditional
   predictive inference. *Inf Inference* 10(2):455-482. doi:10.1093/imaiai/iaaa017. **[V-meta]**.
4. **Gibbs I, Cherian JJ, Candès EJ. 2025.** Conformal prediction with conditional guarantees. *JRSS-B*
   87:1100-1126. doi:10.1093/jrsssb/qkaf008. arXiv:2305.12616. **[V-meta]**.
5. **Ding T, Angelopoulos AN, Bates S, Jordan MI, Tibshirani RJ. 2023.** Class-conditional conformal prediction with
   many classes. *NeurIPS 36*. arXiv:2306.09335. **[V-meta]**.
6. **Johansson U, Ahlberg E, Boström H, Carlsson L, Linusson H, Sönströd C. 2015.** Handling small calibration sets
   in Mondrian inductive conformal regressors. *SLDS 2015*, LNCS 9047:271-280. doi:10.1007/978-3-319-17091-6_20.
   **[V-meta]**.

Also relevant:
- Jung C, Noarov G, Ramalingam R, Roth A. 2023. Batch multivalid conformal prediction. *ICLR 2023*.
  arXiv:2209.15145. **[V-meta]** (group-conditional coverage for overlapping groups).
- Lu C, Lemay A, Chang K, Höbel K, Kalpathy-Cramer J. 2022. Fair conformal predictors for applications in medical
  imaging. *AAAI* 36(11):12008-12016. doi:10.1609/aaai.v36i11.21459. **[V-meta]** (Mondrian by race / skin tone;
  breast density, dermatology).
- Sadinle M, Lei J, Wasserman L. 2019. Least ambiguous set-valued classifiers with bounded error levels. *JASA*
  114(525):223-234. doi:10.1080/01621459.2017.1395341. **[V-meta]** (class-conditional sets; set size as
  ambiguity).
- Mehrtens H, Bucher T-C, Brinker TJ. 2025. Pitfalls of conformal predictions for medical image classification.
  arXiv:2506.18162. **[V]** (unreliable under shift and for subgroups; little value with few classes).
- Zhong L, Wang X, Huang S, Shi Y. 2026. When is a conformal guarantee fair? Auditing silent subgroup under-coverage
  in Alzheimer's disease longitudinal prediction. arXiv:2608.04254. **[V]** (per-subgroup calibration plus
  cross-conformal pooling for rare subgroups).
- Rafe A, Das S. 2026. Socio-conformal calibration in complex survey data. arXiv:2605.05562. **[V]** (regularised
  Mondrian: shrink group thresholds toward the global quantile for small cells).
- Olsson H et al. 2022. Estimating diagnostic uncertainty in AI-assisted pathology using conformal prediction.
  *Nat Commun* 13:7761. doi:10.1038/s41467-022-34945-8. **[V-meta]** (clinical Mondrian/conformal precedent).
- Angelopoulos & Bates tutorial and Angelopoulos 2024 conformal triage: already cited.

### (b) What they already do
- Mondrian conformal (Vovk) is exactly "split calibration by a pre-specified taxonomy and calibrate each cell",
  with finite-sample coverage inside each cell; label-conditional (per class) is a special case.
- Romano 2020 applies this to protected groups and evaluates within-group coverage and set size; Lu 2022 does the
  same in medical imaging; Olsson 2022 in pathology.
- Barber 2021 proves exact conditional coverage on arbitrary sets is impossible without wide sets; Gibbs 2025 and
  Jung 2023 give coverage over finite/overlapping group families without partitioning.
- Small cells: Johansson 2015 (smoothed/interpolated p-values for small Mondrian cells), Ding 2023 (merge classes
  with similar score distributions into clusters and calibrate per cluster; null cluster falls back to marginal),
  Rafe 2026 (shrink to global), Zhong 2026 (pool rare subgroups). Fallback-to-pooled for a too-small cell is
  therefore established practice.
- Evaluation by within-group coverage plus set size / singleton rate is the standard report.

### (c) Verdict: **ALREADY DONE (method); application only**

Nothing in the method is new: groups defined by clinical context are just a Mondrian taxonomy, and merging or
falling back for small cells is covered by Johansson 2015, Ding 2023 and later work. No conformal or Mondrian work
on glioma progression / pseudoprogression was found (consistent with the 2026-11-12 search).

Narrowest defensible claim: *"To our knowledge, the first per-scan conformal prediction sets for progression on
glioma follow-up MRI; calibration is Mondrian by treatment-timing window and tumour state, with a pre-specified rule
for cells below n calibration scans (merge to the parent stratum / pooled), fitted on one public cohort and carried
unchanged to two external centres, with within-stratum coverage and the rate of uninformative (two-label) sets
reported at each."* Frame it as an application of Vovk's Mondrian predictor, not a method. State explicitly: (i) the
within-stratum guarantee holds only under exchangeability between calibration and test scans in that stratum, which
external centres need not satisfy (cite mehrtens2025, barber2021limits); (ii) for binary outcomes, group-conditional
is not label-conditional, so coverage among progressors can still be below nominal inside a stratum unless the
Mondrian cell also splits by label; (iii) the merge rule is a choice among established ones (cite ding2023,
johansson2015).

### (d) Must cite
vovk2022book or vovk2013 (Mondrian origin; essential), romano2020 (already), barber2021limits, ding2023 (small-group
merging; essential since the paper has a merge rule), lu2022 (medical imaging Mondrian), mehrtens2025, zhong2026.
Optional: gibbs2025, jung2023, johansson2015, sadinle2019, olsson2022.

---

## M3. Deterministic typed-claim verifier for LLM-written reports, evaluated by planted errors

### (a) Closest work

1. **Pham KD, Nguyen D, Le KTQ, Rutledge-Jukes H, Le Q, et al. 2026.** Evidence-augmented conformal risk control with
   verifier-gated LLM reporting for trustworthy ECG decision support. Author PDF
   (cs.emory.edu/~jyang71/files/ea-crc.pdf). **[V]** for content (methods read); venue (EMBC 2026) **[U]**, not
   printed in the PDF.
2. **Mansour FA, Ferdousi R, Ashor ZMM, Elshenawy MF, Shehaby I, Elmongi S, Ahmed S. 2026.** An agentic AI workflow
   for liver lesion segmentation and structured radiology reporting. arXiv:2610.34599. **[V]**.
3. **Nam Y, Jeong J, Kim N. 2026.** Deterministic integrity gates for LLM-assisted clinical manuscript preparation:
   an auditable biomedical informatics architecture. arXiv:2606.09500. **[V]**.
4. **Wiseman S, Shieber S, Rush A. 2017.** Challenges in data-to-document generation. *EMNLP 2017*.
   doi:10.18653/v1/D17-1239. arXiv:1707.08052. **[V-meta]**.
5. **Kryściński W, McCann B, Xiong C, Socher R. 2020.** Evaluating the factual consistency of abstractive text
   summarization. *EMNLP 2020*. doi:10.18653/v1/2020.emnlp-main.750. **[V-meta]**. With **Gabriel S, Celikyilmaz A,
   Jha R, Choi Y, Gao J. 2021.** GO FIGURE: a meta evaluation of factuality in summarization. *Findings ACL-IJCNLP
   2021*, 478-487. doi:10.18653/v1/2021.findings-acl.42. **[V-meta]**.
6. **Rao VM, Zhang S, Acosta JN, Adithan S, Rajpurkar P. 2025.** ReXErr: synthesizing clinically meaningful errors in
   diagnostic radiology reports. *Pac Symp Biocomput* 30 (PSB 2025). arXiv:2409.10829. **[V-meta]** (PSB venue
   inferred from psb.stanford.edu/psb25 PDF; page numbers **[U]**).

Also relevant (metrics, error typologies, structured fact checking):
- Thomson C, Reiter E. 2020. A gold standard methodology for evaluating accuracy in data-to-text systems. *INLG 2020*,
  158-168. doi:10.18653/v1/2020.inlg-1.22. **[V-meta]**.
- Dušek O, Kasner Z. 2020. Evaluating semantic accuracy of data-to-text generation with natural language inference.
  *INLG 2020*, 131-137. arXiv:2011.10819. **[V-meta]**.
- Pagnoni A, Balachandran V, Tsvetkov Y. 2021. FRANK. *NAACL 2021*. doi:10.18653/v1/2021.naacl-main.383. **[V-meta]**.
- Ribeiro MT, Wu T, Guestrin C, Singh S. 2020. CheckList. *ACL 2020*, 4902-4912. doi:10.18653/v1/2020.acl-main.442.
  **[V-meta]**.
- Sharma V, Bejar AM, Durak G, Bagci U. 2026. CTest-Metric. arXiv:2601.11488. **[V]** (synthetic error injection
  at graded severities to test CT report metrics).
- Radiology metrics: Jain S et al. 2021 RadGraph, NeurIPS Datasets & Benchmarks, arXiv:2106.14463 **[V-meta]**;
  Yu F et al. 2023 *Patterns* 4(9):100802, doi:10.1016/j.patter.2023.100802 **[V-meta]**; Ostmeier S et al. 2024
  GREEN, *Findings EMNLP*, doi:10.18653/v1/2024.findings-emnlp.21 **[V-meta]**; Zhao W et al. 2024 RaTEScore,
  *EMNLP*, doi:10.18653/v1/2024.emnlp-main.836 **[V-meta]**; Zhang X et al. 2024 ReXrank, arXiv:2411.15122 (PMLR 281)
  **[V-meta]**.
- Summary factuality: Wang A, Cho K, Lewis M. 2020 QAGS, *ACL*, doi:10.18653/v1/2020.acl-main.450 **[V-meta]**;
  Laban P et al. 2022 SummaC, *TACL* 10:163-177, doi:10.1162/tacl_a_00453 **[V-meta]**.
- Structured fact verification: Chen W et al. 2020 TabFact, *ICLR*, arXiv:1909.02164 **[V-meta]**; Aly R et al. 2021
  FEVEROUS, NeurIPS Datasets & Benchmarks, arXiv:2106.05707 **[V-meta]**.
- Attributed generation: Gao T, Yen H, Yu J, Chen D. 2023 ALCE, *EMNLP*, doi:10.18653/v1/2023.emnlp-main.398
  **[V-meta]**.
- From the 2026-11-12 search, still relevant: FactCheXcker arXiv:2411.18672 and STRIVE arXiv:2608.24237 (repair, not
  rejection); EHR-ReasonCon / EHR-INSPECTOR (Kwon et al. 2026, arXiv:2605.26463, **[V]**: LLM-based note-vs-table
  consistency, no injected errors); zeba2026, herasrivera2026, valerio2025 already cited.

### (b) What they already do
- **Pham 2026**: an LLM rewrites a deterministic base report; a deterministic verifier checks *code fidelity* (every
  diagnosis mentioned is in the conformal set) and *measurement safety* (blocks any number-like pattern); on failure
  one repair attempt, then fallback to the template base report. No typed claims, no numbers allowed, no planted-error
  evaluation, no false-rejection rate.
- **Mansour 2026**: deterministic numeric traceability: each value in the LLM report must have a computational source
  in the measurement JSON, otherwise flagged; schema validation. Explicitly no quantitative evaluation of the check.
- **Nam 2026**: 21 deterministic detectors (including numerical drift from source data) gate an LLM pipeline;
  evaluated on 27 seeded defects, all caught, zero false positives on clean fixtures, vs 11/27 for an LLM reviewer.
  This is the same *evaluation design* (seeded defects + false alarms on clean inputs) in a different text type.
- **Wiseman 2017**: extract (entity, value, type) relations from generated text and check them against the source
  record ("relation generation" precision); templates beat neural systems on factual metrics. This is the
  data-to-text precedent for record-level claim checking and for a template baseline.
- **FactCC / GO FIGURE / ReXErr / CTest-Metric**: rule-based or LLM-generated error injection (entity swap, number
  swap, negation, laterality, omission) to train or meta-evaluate factuality checkers; GO FIGURE and CTest-Metric
  evaluate metric sensitivity per injected error type. Mutation-style evaluation of a checker is established.
- **FRANK / Thomson & Reiter**: error typologies at claim level; Thomson & Reiter annotate numeric, name, word and
  context errors in data-to-text.
- **RadGraph F1, GREEN, RaTEScore, RadFact, CheXbert-based**: reference-based evaluation metrics comparing to a
  radiologist report; not generation-time gates against a structured record.
- **TabFact, FEVEROUS**: learned verifiers of claims against tables.

### (c) Verdict: **PARTIAL (incremental)**

Every ingredient exists: deterministic verification gating an LLM clinical report (Pham), numeric traceability to a
measurement record (Mansour), extractive claim checking against records with a template baseline (Wiseman),
per-class planted-error evaluation of a checker (FactCC/GO FIGURE/ReXErr/CTest-Metric) and seeded-defect recall
with false alarms on clean inputs for deterministic gates (Nam). No paper found does all of the following together:
a sentence-level *typed claim* schema (entity/region, quantity, direction word, value with unit, cited record
fields), every element checked deterministically against the structured source record of an imaging follow-up
scan, whole-report rejection without repair, and evaluation by planted-error recall per error class plus false
rejection of correct reports, with a fixed template writer as baseline.

Narrowest defensible claim: *"A reference-free, deterministic checker that verifies every element of every sentence
(region, quantity, direction, value and unit, cited fields) against the scan's structured record; on glioma
follow-up reports it caught X% of planted errors in each of K classes and rejected Y% of correct reports, and a
fixed template writer is the baseline."* Do not claim the verifier pattern, numeric checking, or mutation testing as
new. The contribution is the claim schema that makes direction words and units checkable, and the measured
recall / false-rejection profile in this domain. Note that recall is only measured on error classes the authors
planted, which the checker was designed against (circularity; GO FIGURE and Nam make the same caveat implicit);
say which classes the checker cannot see (e.g. clinically wrong but record-consistent statements, omissions).

### (d) Must cite
pham2026 (essential; closest), mansour2026, nam2026 (closest evaluation design), wiseman2017 (record-level checking
and template baseline), kryscinski2020 and gabriel2021 (error injection to evaluate factuality checkers), rao2025rexerr
(radiology error injection); one line citing reference-based radiology metrics (yu2023 RadGraph F1, ostmeier2024
GREEN, zhao2024ratescore) to say they need a reference report and are not generation-time gates. Optional:
thomson2020, pagnoni2021, dusek2020, ribeiro2020, sharma2026, chen2020tabfact, aly2021feverous, gao2023alce,
wang2020qags, laban2022, jain2021, zhang2024rexrank.

---

## Summary table

| | Closest | Verdict | Claim |
|---|---|---|---|
| M1 | Kallus & Zhou 2019 Prop. 1; Matos et al. 2026; Sudjianto & Liu 2025; Janes & Pepe 2009 | Identity ALREADY DONE; use PARTIAL | Use the published decomposition as a context-reliance audit: across term = timing alone; change of each term per added input block; compared across external centres |
| M2 | Vovk (Mondrian); Romano 2020; Ding 2023; Johansson 2015; Lu 2022 | ALREADY DONE (method) | First per-scan Mondrian sets for glioma progression, strata by timing and tumour state, pre-specified merge rule, transferred unchanged to two centres |
| M3 | Pham 2026; Mansour 2026; Nam 2026; Wiseman 2017; FactCC / GO FIGURE / ReXErr | PARTIAL | Typed-claim schema checked element-wise against the scan record; per-class planted-error recall and false rejection vs template writer, in imaging follow-up |

---

## BibTeX (verified entries not already in refs.bib)

Entries marked `% [U]` in a field contain a detail not confirmed online this session; check before use.

```bibtex
@inproceedings{kallus2019,
  author    = {Kallus, Nathan and Zhou, Angela},
  title     = {{The fairness of risk scores beyond classification: Bipartite ranking and the xAUC metric}},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {32},
  year      = {2019},
  eprint    = {1902.05826},
  archivePrefix = {arXiv}
}

@misc{matos2026,
  author       = {Matos, Jo{\~a}o and Van Calster, Ben and Riley, Richard D. and Dhiman, Paula and Collins, Gary S.},
  title        = {{Collapsibility of performance metrics in clinical predictive AI}},
  year         = {2026},
  eprint       = {2608.30568},
  archivePrefix= {arXiv},
  howpublished = {arXiv:2608.30568}
}

@misc{sudjianto2025,
  author       = {Sudjianto, Agus and Liu, Alice J.},
  title        = {{Decomposing global AUC into cluster-level contributions for localized model diagnostics}},
  year         = {2025},
  eprint       = {2508.07495},
  archivePrefix= {arXiv},
  howpublished = {arXiv:2508.07495}
}

@inproceedings{borkan2019,
  author    = {Borkan, Daniel and Dixon, Lucas and Sorensen, Jeffrey and Thain, Nithum and Vasserman, Lucy},
  title     = {{Nuanced metrics for measuring unintended bias with real data for text classification}},
  booktitle = {Companion Proceedings of the 2019 World Wide Web Conference},
  pages     = {491--500},
  year      = {2019},
  doi       = {10.1145/3308560.3317593}, % [U] DOI and pages from memory
  eprint    = {1903.04561},
  archivePrefix = {arXiv}
}

@article{janes2009,
  author  = {Janes, Holly and Pepe, Margaret S.},
  title   = {{Adjusting for covariate effects on classification accuracy using the covariate-adjusted receiver operating characteristic curve}},
  journal = {Biometrika},
  volume  = {96},
  number  = {2},
  pages   = {371--382},
  year    = {2009},
  doi     = {10.1093/biomet/asp002}
}

@article{janes2009stata,
  author  = {Janes, Holly and Longton, Gary and Pepe, Margaret S.},
  title   = {{Accommodating covariates in receiver operating characteristic analysis}},
  journal = {The Stata Journal},
  volume  = {9},
  number  = {1},
  pages   = {17--39},
  year    = {2009}
}

@article{vanoirbeek2012,
  author  = {Van Oirbeek, Robin and Lesaffre, Emmanuel},
  title   = {{Assessing the predictive ability of a multilevel binary regression model}},
  journal = {Computational Statistics \& Data Analysis},
  volume  = {56},
  number  = {6},
  pages   = {1966--1980},
  year    = {2012},
  doi     = {10.1016/j.csda.2011.11.023}
}

@misc{tsue2023,
  author       = {Tsue, Trevor and Mombourquette, Brent and Taha, Ahmed and Matthews, Thomas Paul and Vu, Yen Nhi Truong and Su, Jason},
  title        = {{Problems and shortcuts in deep learning for screening mammography}},
  year         = {2023},
  eprint       = {2303.16417},
  archivePrefix= {arXiv},
  howpublished = {arXiv:2303.16417}
}

@inproceedings{beutel2019,
  author    = {Beutel, Alex and Chen, Jilin and Doshi, Tulsee and Qian, Hai and Wei, Li and Wu, Yi and Heldt, Lukasz and Zhao, Zhe and Hong, Lichan and Chi, Ed H. and Goodrow, Cristos},
  title     = {{Fairness in recommendation ranking through pairwise comparisons}},
  booktitle = {Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery \& Data Mining},
  pages     = {2212--2220},
  year      = {2019},
  doi       = {10.1145/3292500.3330745} % [U] DOI from memory
}

@article{obuchowski1997,
  author  = {Obuchowski, Nancy A.},
  title   = {{Nonparametric analysis of clustered ROC curve data}},
  journal = {Biometrics},
  volume  = {53},
  number  = {2},
  pages   = {567--578},
  year    = {1997},
  doi     = {10.2307/2533958} % [U] DOI from memory
}

@article{geirhos2020,
  author  = {Geirhos, Robert and Jacobsen, J{\"o}rn-Henrik and Michaelis, Claudio and Zemel, Richard and Brendel, Wieland and Bethge, Matthias and Wichmann, Felix A.},
  title   = {{Shortcut learning in deep neural networks}},
  journal = {Nature Machine Intelligence},
  volume  = {2},
  number  = {11},
  pages   = {665--673},
  year    = {2020},
  doi     = {10.1038/s42256-020-00257-z}
}

@article{degrave2021,
  author  = {DeGrave, Alex J. and Janizek, Joseph D. and Lee, Su-In},
  title   = {{AI for radiographic COVID-19 detection selects shortcuts over signal}},
  journal = {Nature Machine Intelligence},
  volume  = {3},
  pages   = {610--619},
  year    = {2021},
  doi     = {10.1038/s42256-021-00338-7}
}

@article{zech2018,
  author  = {Zech, John R. and Badgeley, Marcus A. and Liu, Manway and Costa, Anthony B. and Titano, Joseph J. and Oermann, Eric Karl},
  title   = {{Variable generalization performance of a deep learning model to detect pneumonia in chest radiographs: A cross-sectional study}},
  journal = {PLoS Medicine},
  volume  = {15},
  number  = {11},
  pages   = {e1002683},
  year    = {2018},
  doi     = {10.1371/journal.pmed.1002683}
}

@inproceedings{oakdenrayner2020,
  author    = {Oakden-Rayner, Luke and Dunnmon, Jared and Carneiro, Gustavo and R{\'e}, Christopher},
  title     = {{Hidden stratification causes clinically meaningful failures in machine learning for medical imaging}},
  booktitle = {Proceedings of the ACM Conference on Health, Inference, and Learning},
  pages     = {151--159},
  year      = {2020},
  doi       = {10.1145/3368555.3384468}
}

@article{brown2023,
  author  = {Brown, Alexander and Toma{\v{s}}ev, Nenad and Freyberg, Jan and Liu, Yuan and Karthikesalingam, Alan and Schrouff, Jessica},
  title   = {{Detecting shortcut learning for fair medical AI using shortcut testing}},
  journal = {Nature Communications},
  volume  = {14},
  pages   = {4314},
  year    = {2023},
  doi     = {10.1038/s41467-023-39902-7}
}

@book{vovk2022book,
  author    = {Vovk, Vladimir and Gammerman, Alexander and Shafer, Glenn},
  title     = {{Algorithmic Learning in a Random World}},
  edition   = {2},
  publisher = {Springer},
  address   = {Cham},
  year      = {2022},
  doi       = {10.1007/978-3-031-06649-8}
}

@article{vovk2013,
  author  = {Vovk, Vladimir},
  title   = {{Conditional validity of inductive conformal predictors}},
  journal = {Machine Learning},
  volume  = {92},
  pages   = {349--376},
  year    = {2013},
  doi     = {10.1007/s10994-013-5355-6}
}

@article{barber2021limits,
  author  = {Foygel Barber, Rina and Cand{\`e}s, Emmanuel J. and Ramdas, Aaditya and Tibshirani, Ryan J.},
  title   = {{The limits of distribution-free conditional predictive inference}},
  journal = {Information and Inference: A Journal of the IMA},
  volume  = {10},
  number  = {2},
  pages   = {455--482},
  year    = {2021},
  doi     = {10.1093/imaiai/iaaa017}
}

@article{gibbs2025,
  author  = {Gibbs, Isaac and Cherian, John J. and Cand{\`e}s, Emmanuel J.},
  title   = {{Conformal prediction with conditional guarantees}},
  journal = {Journal of the Royal Statistical Society Series B: Statistical Methodology},
  volume  = {87},
  number  = {4},
  pages   = {1100--1126},
  year    = {2025},
  doi     = {10.1093/jrsssb/qkaf008}
}

@inproceedings{ding2023,
  author    = {Ding, Tiffany and Angelopoulos, Anastasios N. and Bates, Stephen and Jordan, Michael I. and Tibshirani, Ryan J.},
  title     = {{Class-conditional conformal prediction with many classes}},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {36},
  year      = {2023},
  eprint    = {2306.09335},
  archivePrefix = {arXiv}
}

@inproceedings{jung2023,
  author    = {Jung, Christopher and Noarov, Georgy and Ramalingam, Ramya and Roth, Aaron},
  title     = {{Batch multivalid conformal prediction}},
  booktitle = {International Conference on Learning Representations},
  year      = {2023},
  eprint    = {2209.15145},
  archivePrefix = {arXiv}
}

@inproceedings{johansson2015,
  author    = {Johansson, Ulf and Ahlberg, Ernst and Bostr{\"o}m, Henrik and Carlsson, Lars and Linusson, Henrik and S{\"o}nstr{\"o}d, Cecilia},
  title     = {{Handling small calibration sets in Mondrian inductive conformal regressors}},
  booktitle = {Statistical Learning and Data Sciences (SLDS 2015)},
  series    = {Lecture Notes in Computer Science},
  volume    = {9047},
  pages     = {271--280},
  publisher = {Springer},
  year      = {2015},
  doi       = {10.1007/978-3-319-17091-6_20}
}

@inproceedings{lu2022,
  author    = {Lu, Charles and Lemay, Andr{\'e}anne and Chang, Ken and H{\"o}bel, Katharina and Kalpathy-Cramer, Jayashree},
  title     = {{Fair conformal predictors for applications in medical imaging}},
  booktitle = {Proceedings of the AAAI Conference on Artificial Intelligence},
  volume    = {36},
  number    = {11},
  pages     = {12008--12016},
  year      = {2022},
  doi       = {10.1609/aaai.v36i11.21459}
}

@article{sadinle2019,
  author  = {Sadinle, Mauricio and Lei, Jing and Wasserman, Larry},
  title   = {{Least ambiguous set-valued classifiers with bounded error levels}},
  journal = {Journal of the American Statistical Association},
  volume  = {114},
  number  = {525},
  pages   = {223--234},
  year    = {2019},
  doi     = {10.1080/01621459.2017.1395341}
}

@misc{mehrtens2025,
  author       = {Mehrtens, Hendrik and Bucher, Tabea-Clara and Brinker, Titus J.},
  title        = {{Pitfalls of conformal predictions for medical image classification}},
  year         = {2025},
  eprint       = {2506.18162},
  archivePrefix= {arXiv},
  howpublished = {arXiv:2506.18162}
}

@misc{zhong2026,
  author       = {Zhong, Lujia and Wang, Xinkai and Huang, Shuo and Shi, Yonggang},
  title        = {{When is a conformal guarantee fair? Auditing silent subgroup under-coverage in Alzheimer's disease longitudinal prediction}},
  year         = {2026},
  eprint       = {2608.04254},
  archivePrefix= {arXiv},
  howpublished = {arXiv:2608.04254}
}

@article{olsson2022,
  author  = {Olsson, Henrik and Kartasalo, Kimmo and Mulliqi, Nita and others},
  title   = {{Estimating diagnostic uncertainty in artificial intelligence assisted pathology using conformal prediction}},
  journal = {Nature Communications},
  volume  = {13},
  pages   = {7761},
  year    = {2022},
  doi     = {10.1038/s41467-022-34945-8} % [U] author list after first author and article number from memory
}

@misc{pham2026,
  author       = {Pham, Khoa D. and Nguyen, Dang and Le, Khanh Tran Quoc and Rutledge-Jukes, Heath and Le, Quan and Huynh, Hung N. and Le, Trung Q. and Xu, Yanwen and Yadav, Om Prakash and Yang, Carl and Sun, Louise Y. and Huynh, Phat K. and Kpodonu, Jacques},
  title        = {{Evidence-augmented conformal risk control with verifier-gated LLM reporting for trustworthy ECG decision support}},
  year         = {2026},
  howpublished = {Author manuscript, \url{https://cs.emory.edu/~jyang71/files/ea-crc.pdf}},
  note         = {Venue (EMBC 2026) not confirmed} % [U] venue
}

@misc{mansour2026,
  author       = {Mansour, Fatma Ahmed and Ferdousi, Rahatara and Ashor, Zyad Medhat Mahmoud and Elshenawy, Manar Fathy and Shehaby, Ibrahim and Elmongi, Salma and Ahmed, S.},
  title        = {{An agentic AI workflow for liver lesion segmentation and structured radiology reporting}},
  year         = {2026},
  eprint       = {2610.34599},
  archivePrefix= {arXiv},
  howpublished = {arXiv:2610.34599}
}

@misc{nam2026,
  author       = {Nam, Yoojin and Jeong, Jinhoon and Kim, Namkug},
  title        = {{Deterministic integrity gates for LLM-assisted clinical manuscript preparation: An auditable biomedical informatics architecture}},
  year         = {2026},
  eprint       = {2606.09500},
  archivePrefix= {arXiv},
  howpublished = {arXiv:2606.09500}
}

@inproceedings{wiseman2017,
  author    = {Wiseman, Sam and Shieber, Stuart and Rush, Alexander},
  title     = {{Challenges in data-to-document generation}},
  booktitle = {Proceedings of the 2017 Conference on Empirical Methods in Natural Language Processing},
  pages     = {2253--2263},
  year      = {2017},
  doi       = {10.18653/v1/D17-1239}
}

@inproceedings{kryscinski2020,
  author    = {Kry{\'s}ci{\'n}ski, Wojciech and McCann, Bryan and Xiong, Caiming and Socher, Richard},
  title     = {{Evaluating the factual consistency of abstractive text summarization}},
  booktitle = {Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing},
  pages     = {9332--9346},
  year      = {2020},
  doi       = {10.18653/v1/2020.emnlp-main.750}
}

@inproceedings{gabriel2021,
  author    = {Gabriel, Saadia and Celikyilmaz, Asli and Jha, Rahul and Choi, Yejin and Gao, Jianfeng},
  title     = {{GO FIGURE: A meta evaluation of factuality in summarization}},
  booktitle = {Findings of the Association for Computational Linguistics: ACL-IJCNLP 2021},
  pages     = {478--487},
  year      = {2021},
  doi       = {10.18653/v1/2021.findings-acl.42}
}

@inproceedings{rao2025rexerr,
  author    = {Rao, Vishwanatha M. and Zhang, Serena and Acosta, Julian N. and Adithan, Subathra and Rajpurkar, Pranav},
  title     = {{ReXErr: Synthesizing clinically meaningful errors in diagnostic radiology reports}},
  booktitle = {Pacific Symposium on Biocomputing},
  volume    = {30},
  year      = {2025},
  eprint    = {2409.10829},
  archivePrefix = {arXiv}
}

@inproceedings{thomson2020,
  author    = {Thomson, Craig and Reiter, Ehud},
  title     = {{A gold standard methodology for evaluating accuracy in data-to-text systems}},
  booktitle = {Proceedings of the 13th International Conference on Natural Language Generation},
  pages     = {158--168},
  year      = {2020},
  doi       = {10.18653/v1/2020.inlg-1.22}
}

@inproceedings{dusek2020,
  author    = {Du{\v{s}}ek, Ond{\v{r}}ej and Kasner, Zden{\v{e}}k},
  title     = {{Evaluating semantic accuracy of data-to-text generation with natural language inference}},
  booktitle = {Proceedings of the 13th International Conference on Natural Language Generation},
  pages     = {131--137},
  year      = {2020},
  eprint    = {2011.10819},
  archivePrefix = {arXiv}
}

@inproceedings{pagnoni2021,
  author    = {Pagnoni, Artidoro and Balachandran, Vidhisha and Tsvetkov, Yulia},
  title     = {{Understanding factuality in abstractive summarization with FRANK: A benchmark for factuality metrics}},
  booktitle = {Proceedings of the 2021 Conference of the North American Chapter of the Association for Computational Linguistics},
  pages     = {4812--4829},
  year      = {2021},
  doi       = {10.18653/v1/2021.naacl-main.383}
}

@inproceedings{ribeiro2020,
  author    = {Ribeiro, Marco Tulio and Wu, Tongshuang and Guestrin, Carlos and Singh, Sameer},
  title     = {{Beyond accuracy: Behavioral testing of NLP models with CheckList}},
  booktitle = {Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics},
  pages     = {4902--4912},
  year      = {2020},
  doi       = {10.18653/v1/2020.acl-main.442}
}

@misc{sharma2026,
  author       = {Sharma, Vanshali and Bejar, Andrea Mia and Durak, Gorkem and Bagci, Ulas},
  title        = {{CTest-Metric: A unified framework to assess clinical validity of metrics for CT report generation}},
  year         = {2026},
  eprint       = {2601.11488},
  archivePrefix= {arXiv},
  howpublished = {arXiv:2601.11488}
}

@article{yu2023,
  author  = {Yu, Feiyang and Endo, Mark and Krishnan, Rayan and Pan, Ian and Tsai, Andy and Reis, Eduardo Pontes and others and Rajpurkar, Pranav},
  title   = {{Evaluating progress in automatic chest X-ray radiology report generation}},
  journal = {Patterns},
  volume  = {4},
  number  = {9},
  pages   = {100802},
  year    = {2023},
  doi     = {10.1016/j.patter.2023.100802}
}

@inproceedings{ostmeier2024,
  author    = {Ostmeier, Sophie and Xu, Justin and Chen, Zhihong and Varma, Maya and Blankemeier, Louis and Bluethgen, Christian and Michalson, Arne Edward and Moseley, Michael and Langlotz, Curtis and Chaudhari, Akshay S. and Delbrouck, Jean-Benoit},
  title     = {{GREEN: Generative radiology report evaluation and error notation}},
  booktitle = {Findings of the Association for Computational Linguistics: EMNLP 2024},
  pages     = {374--390},
  year      = {2024},
  doi       = {10.18653/v1/2024.findings-emnlp.21}
}

@inproceedings{zhao2024ratescore,
  author    = {Zhao, Weike and Wu, Chaoyi and Zhang, Xiaoman and Zhang, Ya and Wang, Yanfeng and Xie, Weidi},
  title     = {{RaTEScore: A metric for radiology report generation}},
  booktitle = {Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing},
  pages     = {15004--15019},
  year      = {2024},
  doi       = {10.18653/v1/2024.emnlp-main.836}
}

@inproceedings{jain2021,
  author    = {Jain, Saahil and Agrawal, Ashwin and Saporta, Adriel and Truong, Steven QH and Duong, Du Nguyen and Bui, Tan and Chambon, Pierre and Zhang, Yuhao and Lungren, Matthew P. and Ng, Andrew Y. and Langlotz, Curtis P. and Rajpurkar, Pranav},
  title     = {{RadGraph: Extracting clinical entities and relations from radiology reports}},
  booktitle = {Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks},
  year      = {2021},
  eprint    = {2106.14463},
  archivePrefix = {arXiv}
}

@misc{zhang2024rexrank,
  author       = {Zhang, Xiaoman and Zhou, Hong-Yu and Yang, Xiaoli and Banerjee, Oishi and Acosta, Juli{\'a}n N. and Miller, Josh and Huang, Ouwen and Rajpurkar, Pranav},
  title        = {{ReXrank: A public leaderboard for AI-powered radiology report generation}},
  year         = {2024},
  eprint       = {2411.15122},
  archivePrefix= {arXiv},
  howpublished = {arXiv:2411.15122}
}

@inproceedings{wang2020qags,
  author    = {Wang, Alex and Cho, Kyunghyun and Lewis, Mike},
  title     = {{Asking and answering questions to evaluate the factual consistency of summaries}},
  booktitle = {Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics},
  pages     = {5008--5020},
  year      = {2020},
  doi       = {10.18653/v1/2020.acl-main.450}
}

@article{laban2022,
  author  = {Laban, Philippe and Schnabel, Tobias and Bennett, Paul N. and Hearst, Marti A.},
  title   = {{SummaC: Re-visiting NLI-based models for inconsistency detection in summarization}},
  journal = {Transactions of the Association for Computational Linguistics},
  volume  = {10},
  pages   = {163--177},
  year    = {2022},
  doi     = {10.1162/tacl_a_00453}
}

@inproceedings{chen2020tabfact,
  author    = {Chen, Wenhu and Wang, Hongmin and Chen, Jianshu and Zhang, Yunkai and Wang, Hong and Li, Shiyang and Zhou, Xiyou and Wang, William Yang},
  title     = {{TabFact: A large-scale dataset for table-based fact verification}},
  booktitle = {International Conference on Learning Representations},
  year      = {2020},
  eprint    = {1909.02164},
  archivePrefix = {arXiv}
}

@inproceedings{aly2021feverous,
  author    = {Aly, Rami and Guo, Zhijiang and Schlichtkrull, Michael and Thorne, James and Vlachos, Andreas and Christodoulopoulos, Christos and Cocarascu, Oana and Mittal, Arpit},
  title     = {{FEVEROUS: Fact extraction and VERification over unstructured and structured information}},
  booktitle = {Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks},
  year      = {2021},
  eprint    = {2106.05707},
  archivePrefix = {arXiv}
}

@inproceedings{gao2023alce,
  author    = {Gao, Tianyu and Yen, Howard and Yu, Jiatong and Chen, Danqi},
  title     = {{Enabling large language models to generate text with citations}},
  booktitle = {Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing},
  pages     = {6465--6488},
  year      = {2023},
  doi       = {10.18653/v1/2023.emnlp-main.398}
}
```

Fields not confirmed online (check before adding): page ranges for borkan2019, wiseman2017, kryscinski2020,
pagnoni2021, oakdenrayner2020; full author lists for brown2023 (Liu, Karthikesalingam), olsson2022, yu2023, jain2021,
beutel2019 (Chen, Chi); DOIs for borkan2019, beutel2019, obuchowski1997; venue of pham2026.

## Sources consulted (main)
- arXiv/ar5iv: 1902.05826, 1903.04561, 2508.07495, 2608.30568, 2303.16417, 2607.15416, 2608.22097, 2608.04254,
  2605.05562, 2506.18162, 2610.34599, 2606.09500, 2605.26463, 2601.11488, 2409.10829, 2411.15122, 2406.16845,
  2405.03595, 2106.14463, 2106.05707, 1909.02164, 2305.12616, 2306.09335, 2209.15145, 1903.04684, 1209.2673
- PMC3371718 (Janes & Pepe 2009); econpapers (Van Oirbeek 2012, CSDA); ACL Anthology records (D17-1239,
  2020.emnlp-main.750, 2021.findings-acl.42, 2020.inlg-1.22, 2020.inlg-1.19, 2021.naacl-main.383, 2020.acl-main.442,
  2020.acl-main.450, 2022.tacl-1.10, 2023.emnlp-main.398, 2024.findings-emnlp.21, 2024.emnlp-main.836);
  ojs.aaai.org 21459; Springer records for vovk2013, vovk2022book, johansson2015; Pham et al. author PDF.
