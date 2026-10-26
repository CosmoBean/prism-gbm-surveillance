# Council round 1: cold reader and hostile reviewer

Source read: paper/main.tex only (pdftotext is not installed; the text was read from the LaTeX). No docs/ or code opened.

## Part A. Cold reader (biomedical engineer, not a glioma person)

### What the paper claims, in 3 sentences
PRISM is a modular system for post-treatment glioma MRI that scores each scan for "is this the scan at which progression was called?" through a treatment-timeline pathway and an image-measurement pathway, adds a conformal-prediction confidence and a reliability card, and writes a checked text report with a local language model. Models fitted once on MU-Glioma-Post reached AUC 0.77 on LUMIERE and 0.80 on UCSF-ALPTDG, and an audit shows the scores rest on scan timing at MU and on enhancing-tumour volume at UCSF. The conformal sets kept roughly nominal coverage at all three centres and every generated report passed a lexical check against its record.

### Where I got lost
1. Abstract opens with "known challenges" and then says "the hardest situations". I do not learn what the task is (detect the scan at which progression is *documented*, not predict anything) until Methods 2.2. Put the task in the first two sentences.
2. "Detected the scan at which progression was called" is odd phrasing. Is this diagnosis, prediction, or reproducing a label? I only understood late that it is a retrospective label-matching task.
3. "Fitted once and locked" (abstract) is unexplained until Methods. "Locked" reads like a software term.
4. "Pathway", "module", "block", "arm", "score", "model" are used interchangeably. Is the "timeline pathway" the "clinical" model? Section 3.1 has "clinical data alone" scoring 0.53 vs timeline 0.82 and I could not tell what the timeline adds beyond clinical.
5. "Single-scan version", "image pathway with change features", "planned imaging model", "image pathway of Section 3.1", "reduced timeline", "reduced confidence design": at least six variants of image or timeline model with overlapping names. I could not keep track of which one each number belongs to.
6. "Planned" vs "exploratory" vs "pre-specified" vs "locked" are used heavily but no table maps them to numbers in the main text; Table 2 is referenced but its content is in the back.
7. "Situation", "phase of care", "tier", "enhancement category", "reliability card": the card's lookup key (phase crossed with enhancement change) is only defined in Methods; the term "situation" appears in the Introduction undefined.
8. Section 3.3 "Each step of the image model's design raised its AUC on MU ... they form the imaging block of the planned model": the ladder (0.66, 0.71, 0.81) is described by prose only; I could not tell which step is "PRISM" and why PRISM stops at the second step when the third scores higher (the reason is stated late and is counterintuitive: the better model is rejected because it leaks schedule).
9. Section 3.2 sentence "The same LUMIERE model scored 0.80 in cross-validation on MU" is unclear: the same model fitted where? A reduced model scored on MU?
10. "Qwen3.8-27B", "Gemma-4-31B", "SwinUNETR", "DeepBraTumIA", "BraTS 2021", "MGMT", "IDH", "pseudoprogression": model names are unexplained (the glioma terms are partly explained; the two LLM names are not, and "Qwen3.8" will look like a typo to anyone who knows Qwen3).
11. "Conformal set at the 80% level ... threshold of 0.78 fixed in advance": why 0.78 and not 0.80? Not explained in the main text.
12. Pathways "agree when both scores lie on the same side of their median in the cohort": the median of which cohort, computed on which data, at deployment? A cold reader cannot see how this works for one new patient.
13. The Introduction lists five challenges, but Section 2.1 maps modules to challenges differently ("five modules, each answering one of the challenges", yet challenge 3 is answered by evaluation, not a module, and challenge 5 bundles three problems). The one-to-one mapping looks forced.
14. Results 3.1 ends mid-argument with a hand-off sentence; 3.3 opens with a verdict ("the audit shows") before the evidence; 3.4 contains a to-do marker. Order: the audit (3.3) is the central finding but arrives after the transport result (3.2) which it reinterprets; a reader takes 3.2 as a success and then learns in 3.3 that the UCSF success is agreement with an enhancement call.

### Undefined terms or names
AUC (never expanded in the main text of the abstract, ok for this journal but note), ridge logistic regression, patient-grouped CV, pooled held-out AUC, split conformal, coverage, reliability card tiers, IQR, DeepBraTumIA, SwinUNETR, BraTS 2021, Qwen3.8-27B, Gemma-4-31B, "permuted-label control", "matched removal", "harmonised volumes", "index scans", "intended use" (as a population), "ladder".

### Numbers I could not interpret
- 0.82 vs 0.82: combined equals timeline at MU, so what does "combined" add? (stated, but the abstract does not.)
- "0.80 ... about as high as when trained there" (0.83): no interval given for the comparison in the abstract or 3.2 text; the Table 2 test is not visible in the text.
- "difference 0.14, 0.03--0.26" is the locked vs UCSF-trained image-with-change pathway; I cannot tell if this difference means transport failed. The text calls it "met its planned transport rule" while showing a 0.14 loss.
- "62 of 62 ..." counts: 56 of 62 progression scans "more than 12 weeks after RT", 51 of 84 non-progression "in the 12 weeks after"; Table 1 says "early after RT" is up to 84 days: consistent but the unit changes between weeks and days.
- 146 scans of 80 patients vs 64/117 (92) over all scans vs Table 1 patients 126: four denominators for MU. Which one is "the" cohort?
- Coverage 0.82, 0.87, 0.78 against "threshold of 0.78": 0.78 passes, yet UCSF interval reaches 0.68; a cold reader reads this as coverage below the nominal 0.80.
- "$-$0.02 ($-$0.13 to $+$0.11) within phases": difference between what and what is not stated in the sentence in which it appears.
- "28 of 30 perturbed records": what perturbation, why 30?
- "220 scans whose evidence was thin" vs 249 MU scans with reports vs 114 reports at MU: three different counts for MU reports.
- "35 of 249 fell in a situation tested on at least 10 and 10": fine, but "only four situations met that bar" then seems to contradict "35 scans" being in one MU situation.
- Table 1: LUMIERE and MU show identical age median/IQR (62, 53-70) and identical male 52%: looks like a copy error to a cold reader.

## Part B. Hostile reviewer (CMBBE: Imaging and Visualization)

### Eight strongest objections

1. **The UCSF label is the image evidence (circularity).** Trigger: "The UCSF AUCs therefore measure agreement with a call made from enhancement at the same scan" and "UCSF rated enhancement as increased at 27 of the 29 progression scans", with progression dated a median 7 days after the scan and positives defined as progression within 30 days. Enhancing volume alone gives 0.88. So 0.80 "transport" is the model reproducing the label's own source. The paper concedes this in 3.3 but the abstract and Discussion first sentence still say "carries to two external centres".
   Smallest fix: change the abstract and Discussion opening so the UCSF result is stated as agreement with an enhancement-based call, not as evidence of generalisation; retitle 3.2 "Scores hold at LUMIERE; at UCSF they track enhancement".

2. **Weak external evidence for the system claim.** Trigger: "The pathways hold at two external centres" and "carry to other centres without refitting". LUMIERE has no treatment dates (the timeline pathway is a reduced one built from the rater's own "within three months of RT" flag, which is itself a rater annotation correlated with the rating), and UCSF has 29 positives and a timeline AUC of 0.56. The full two-pathway system is therefore never tested outside MU.
   Fix: state in the abstract that the full timeline pathway was not tested externally, and rename section 3.2 "The image measurements hold at two external centres; the timeline pathway does not".

3. **Task validity: the label is documented-date, not clinical truth, and the timing shortcut dominates.** Trigger: "56 of the 62 progression scans came more than 12 weeks after radiotherapy, while 51 of the 84 non-progression scans came in the 12 weeks after it" and the within-phase timeline gain of -0.02. A scan-schedule separator is not surveillance. Within a phase the best AUCs are 0.68 and 0.64 with intervals spanning 0.51--0.78.
   Fix: lead the abstract with the within-phase numbers (the honest effect) beside the pooled 0.82, and add one sentence that detection-at-scan with a documented date is not prospective prediction.

4. **Selective, post hoc analysis choices.** Trigger: "We defined these inputs after finding that the planned imaging model contained inputs that encode the scan schedule", plus the agreement rule, the card, the reduced design and the second report evaluation are all post hoc. The headline MU image AUC 0.71 comes from a design chosen after seeing results; the planned test did not show gain (0.03 criterion failed).
   Fix: put "exploratory" in the abstract next to the 0.71 and the agreement/card claims, and move the planned-test failure into the abstract or the first Results paragraph's first sentence.

5. **The conformal claim is stronger than the intervals.** Trigger: "kept their coverage at all three centres" with UCSF 0.78 (0.68--0.87) against 0.80 nominal, a threshold of 0.78 chosen "in advance", and sets calibrated on MU applied unchanged under label shift. Also coverage "uneven across situations" with a to-do for the supplement; image-alone at LUMIERE and timeline-alone at UCSF fell short.
   Fix: say "coverage was close to the 80% target (0.82, 0.87, 0.78; UCSF interval 0.68--0.87)" and cut "kept"; state why 0.78 was the threshold in one clause (finite-sample or tolerance).

6. **Report faithfulness is a tautology as evaluated.** Trigger: "Every evaluation report ... passed the deterministic check: 114 of 114 ... 162 of 162 ... 130 of 130", after a first failure (0 of 178) fixed by editing the prompt and re-running on new patients, "followed a changed field in 28 of 30 perturbed records". A lexical checker that the prompt was tuned to satisfy shows only that the generator can copy fields; no clinician read any report. A reader will say the 100% is by construction.
   Fix: call it "consistent with the record by a lexical check" not "faithful"; report 28/30 as a failure rate (2 failures) with what they were; state in the Results that the first run failed 0/178.

7. **No baseline, no comparison with published systems on a shared task.** Trigger: "Each of PRISM's components has been described before, but we found no system that combines them" and the only comparison being "answer different questions". The novelty claim rests on absence of search hits; a journal reader will ask why a ridge logistic regression on volumes and RANO-like clinical items is not compared with, say, simple RANO volumetric thresholds (bidimensional or volumetric change rules), which is the standard comparator.
   Fix: add the simplest clinical rule (e.g. enhancing-volume growth threshold) as a reference row in a main table, and soften to "we are not aware of a system that combines all of these".

8. **Small, single-development-centre sample, with leakage risk.** Trigger: "126 grade 4 patients", 80 patients and 146 scans in the intended use, 29 UCSF positives; the 0.80 to 0.72 drop over 500 splits is reported for an earlier radiomics model, and the UCSF official split gave 0.45 against a median 0.72 over 100 random splits. These show the evaluation variance exceeds many of the reported differences. Also several scans per patient: confirm no patient overlap across CV, conformal calibration (30% of patients) and bootstrap (the text says patient-level, good, but the nested calibration split is not shown to preserve it in the external fit).
   Fix: add a sentence in Evaluation that the same patient never appears in fitting, calibration and test in any analysis, and report split-to-split SD next to the main AUCs; avoid ranking claims below the CI width.

### Claims stronger than the evidence
- "carries to two external centres without refitting" (Discussion, abstract). At UCSF this is agreement with an enhancement call; at LUMIERE the timeline is a reduced variant; the image-with-change variant lost 0.14 at UCSF.
- "about as high as when trained there" (abstract): 0.80 vs 0.83 with intervals of about 0.2 width cannot show equivalence; no non-inferiority margin.
- "kept their coverage at all three centres": see objection 5.
- "the reports were faithful to their records" and "passed": checker is lexical, prompt tuned after a failure.
- "images added nothing measurable" (3.1): the CI for the difference is not given; absence of evidence at n=80.
- "a clinician using PRISM can see which is which at every scan" (Conclusion): no clinician or reader study; the card has tested tiers for only 35 of 249 MU scans and no UCSF situation.
- "Deep networks ... contribute the masks": the masks used are the cohort-distributed ones, not PRISM's own; the segmentation module is demonstrated only as a re-segmentation sensitivity check. Say plainly that PRISM's segmentation was not the source of the reported measurements.
- "no system combines them": a negative literature claim.
- The worked example (eight weeks after RT, growth) is a constructed scenario with 1 of 9 MU scans; it reads as a validated behaviour and should be labelled "illustrative".

### Claims needlessly weaker
- Hedges such as "which suggests why", "about as high", "descriptive", "exploratory" are stacked in sentences that also carry planned, pre-specified results; separate them so the planned results (LUMIERE 0.77, UCSF single-scan 0.80, met transport rule, coverage) are stated flatly.
- The disagreement result (AUC 0.90 vs 0.59, difference 0.31, 0.18--0.43; matched-removal gain 0.08, 0.05--0.12) is the strongest and most useful finding but is buried in 3.4 and not in the abstract; its non-replication at LUMIERE and UCSF is stated, which is honest, but then the prominent claim should be the MU-only finding labelled as such.
- The 120-day forecast being weak (0.60) is a legitimate negative result; "so we present it as a detection system" reads as an apology. State it as a finding that scan-level detection is the supportable task.
- The audit itself (what each score rests on) is the paper's most original contribution and is only a Results section; the title/abstract could lead with it.
- The re-evaluation lesson (0.80 on one split, 0.72 over 500 splits; official UCSF split 0.45 vs median 0.72) is a methodological contribution suited to this journal; it is in Methods 2.3 only.

### Housekeeping flags a reviewer would catch
- Proposed abstract marker `[PROPOSED, awaiting approval]` and several `\todo` items (a Supplementary section reference in 3.4, a Tikhonov citation "not yet verified", author, funding, ethics, data availability) are still in the text.
- Abstract is at the 150-word limit; verify count after edits.
- "Qwen3.8-27B": confirm the model name and version; reviewers will check.
- Table 1: LUMIERE age/sex identical to MU (62, 53--70; 32 of 61 male = 52%) should be verified against the sources.
- Ethics statement says "no registered protocol" but the text says plans were committed before external tests; say where they are archived (DOI/commit hash) since the pre-specification claim carries weight.
