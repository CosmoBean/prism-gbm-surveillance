# Council round 3: Reviewer 2

Reviewer profile: neuro-oncology imaging researcher with ML evaluation expertise. Based only on `paper/main.tex` (text, tables, legends; figures are placeholders in this build).

Recommendation: **major revision**. The study is unusually careful about pre-specification and honest about where its scores come from. But the headline numbers (abstract, Section 3.1, Figure 2) are presented more strongly than the paper's own audit (Section 3.3) supports, and three of the system's distinctive components (agreement, card, report) are exploratory or only lexically checked. Most of my concerns can be fixed by changing wording and moving existing numbers forward. Two need small analyses.

---

## Summary

The authors present PRISM, a modular post-treatment glioma surveillance system. It scores each MRI through a timeline pathway (clinical data plus position in treatment) and an image pathway (measurements from supplied segmentation masks), and shows a combined ridge score beside them. Each score gets a three-part confidence: an 80% split-conformal set, a pathway-agreement statement and a "reliability card" giving the evidence tier for the scan's situation (phase of care × change in enhancement). A local LLM (Qwen3.8-27B) writes a report, which a deterministic lexical checker verifies against the record.

The system was developed on MU-Glioma-Post with 5×5 patient-grouped CV (intended use: 146 scans, 80 patients). It was tested locked on LUMIERE (178 scans) and UCSF-ALPTDG (69 second scans, 29 progression), under plans committed beforehand. Key results:
- MU: timeline AUC 0.82, image 0.71, combined 0.82; images do not add (pre-specified gain not met).
- LUMIERE: combined 0.77.
- UCSF: single-scan image 0.80, image pathway 0.73; UCSF-trained 0.86.
- The audit shows the MU timeline gain lies almost entirely *between* phases of care (within-phase gain −0.02). UCSF labels largely track a same-scan enhancement call: enhancing volume alone reaches 0.88.
- Conformal coverage of the combined score is 0.78–0.87, against a 0.78 threshold.
- After one prompt revision, all reports pass the checker.

---

## Major concerns

### M1. The MU timeline AUC of 0.82 is mostly a schedule effect, yet it leads the abstract.

*Trigger (abstract):* "On MU-Glioma-Post both pathways detected the scan documenting progression, the timeline pathway with an AUC of 0.82."
*And Section 3.3:* "Across phases of care, adding the timeline ... gained 0.11 (0.04–0.20); within a phase it gained −0.02 (−0.13 to +0.11)." Table 1 shows 56/62 positives later after RT and 51/84 negatives early after RT.

The paper's own audit shows that, at MU, the timeline mostly encodes *when* a scan happened relative to RT, and that this is what separates the classes. That is partly a consequence of the label design. Pseudoprogression-window scans are negatives because progression is rarely documented there, and a negative needs 120 progression-free days afterwards. A reader of the abstract will take 0.82 as a capability, when the paper itself shows it is largely a property of the cohort's scan schedule.

*Smallest fix:*
- In the abstract and in Section 3.1, place the within-phase result next to the 0.82. For example: "...0.82, mainly by separating phases of care; within a phase, images (0.68) gave about as much evidence as the timeline (0.64)."
- Retitle Section 3.1 "Both pathways separate progression scans on MU, the timeline mostly through phase of care", or similar.
- Add a phase-only baseline (a model on phase of care alone) to Figure 2. Readers can then see the floor that the schedule gives by itself.

### M2. At UCSF, the transfer claim is weaker than a one-variable baseline, and the labels are close to circular.

*Trigger (Section 3.2):* "At UCSF, both planned image models transferred." *And Section 3.3:* "Enhancing tumour volume alone ... 0.88 (0.79–0.95), higher than the point estimates of the locked image models; ... progression was dated a median of 7 days after the evaluated scan."

If progression is called from enhancement at that same scan, then a model that measures enhancement will "detect" progression by construction. In that case the external AUC tests agreement between the mask and the radiologist, not detection. Also, a 27-input locked model that loses to raw enhancing volume has not shown that its added inputs are worth anything at that centre. Section 3.3 states the facts, but Figure 2 and the abstract do not show the baseline.

*Smallest fix:*
- Put enhancing volume alone (and, at MU and LUMIERE, the same baseline) in Figure 2 as a reference bar.
- In the abstract, replace "a model trained there did better" with something concrete, such as "enhancing tumour volume alone reached 0.88, as UCSF progression calls followed enhancement at the same scan."
- State in Section 2.2 that UCSF positives are dated within 30 days, and so are close to concurrent with the reading.

### M3. The conformal "coverage met at every centre" claim needs class-conditional reporting and softer wording.

*Trigger (abstract):* "Conformal sets for the combined score met their planned coverage at every centre." *And Section 3.4:* "At UCSF the point estimate sat at the threshold and its interval reached below it (0.68–0.87)."

Three problems:
1. Marginal coverage at 80% with a binary outcome can be met while coverage of the minority class (progression) is poor. That failure is the one that matters clinically.
2. The sets were calibrated on MU and applied to cohorts with different prevalence and label definitions, so exchangeability is not guaranteed. The marginal guarantee does not transfer, and the paper should say this explicitly.
3. At UCSF there are 69 scans, the point estimate is exactly at a threshold that already includes a 0.02 tolerance, and the CI goes down to 0.68. "Met" is technically correct, but it is the weakest possible pass.

*Smallest fix:*
- Report coverage by true class (progression / non-progression) in each cohort, plus the singleton share. One extra row in Figure 4A or a short table would do.
- Reword the abstract as "...reached their planned coverage on point estimates at every centre (at UCSF exactly at the threshold)".
- Add one sentence noting that the external use relies on approximate exchangeability with MU.
- Optional: a Mondrian (class-conditional) variant in the supplement.

### M4. The agreement rule and the reliability card carry the "states how far it can be trusted" claim, but they are post hoc, transductive and barely populated.

*Trigger (Section 2.1):* "The two pathways agree when both scores lie on the same side of that pathway's median score over the cohort's evaluation scans." *And Section 3.4:* "only four situations held at least 10 progression and 10 non-progression scans ... 35 of the 249 MU scans fell in a tested situation ... every situation at UCSF had few cases."

1. The agreement median is computed over each cohort's evaluation set. A prospective system scoring one scan cannot do that, so the rule is transductive and should use a threshold fixed on MU.
2. The rule worked only at MU, where it was defined after seeing the results (S2/S3).
3. The card is tested for 14% of MU scans and none at UCSF. At MU, its tiers are reversed in Brier score (0.222 tested vs 0.147 few-case).

The Discussion and Conclusion still say PRISM "states how far its scores can be trusted there". On this evidence, what the card reliably does is say that most situations are *not* tested. That is useful, but it is a narrower claim.

*Smallest fix:*
- Re-run the agreement rule with medians fixed on MU (folds) and applied unchanged externally, and report it in one sentence. If the result does not change, say so.
- Reword the Discussion and Conclusion to "states how much measured evidence lies behind each score, which for most situations is little", instead of implying that the confidence has been validated.
- Make the MU Brier reversal visible in the text of Section 3.4, not only in Table 2.

### M5. "The reports are faithful to the record" overstates what a lexical checker shows.

*Trigger (Section 3.5 heading and text):* "every number, flag and confidence statement in it could be traced to the record", and "The clinician therefore reads the segmentation, both pathway scores and the confidence as they stand in the record."

A lexical checker confirms that the tokens are present. It does not test emphasis, ordering, hedging, implied direction ("the timeline favours stable disease") or the omission of an inconvenient field beyond the required-content list. The prompt was also revised after a test-set failure. Was the second evaluation run on patients who were not in the failed LUMIERE run? The text says "patients not used in development", but 162 vs 178 LUMIERE reports suggests overlap with the first evaluation. Perturbation following also dropped from 29/30 to 28/30 between evaluations, which the text does not mention.

*Smallest fix:*
- Retitle the section "Every report passes a deterministic check against its record".
- Clarify how the second-evaluation patients relate to the first.
- Add one sentence listing what the checker cannot detect.
- If at all possible, add a small blinded read: one neuro-radiologist or neuro-oncologist rating 30 random reports for misleading emphasis. This is the one new analysis I would push for. Otherwise, move the "clinician reads..." sentence to the limitations.

### M6. There is no clinical-standard baseline, and no operating-point metrics.

*Trigger (Section 3.2):* "The locked combined model reached 0.77 (0.68–0.86) on LUMIERE." (Every result is an AUC.)

Neuro-oncology readers will ask how PRISM compares with a volumetric RANO-style rule: for example, a ≥25% (RANO) or ≥40% (RANO 2.0 volumetric) increase in enhancing volume from nadir, with the 12-week window. That rule is the field's default. The 0.88 at UCSF suggests it may be hard to beat. AUC alone also tells the reader nothing about sensitivity at a clinically usable specificity, or about calibration, which matters because the report displays the scores.

*Smallest fix:* Add a RANO-like volumetric rule as a reference row or bar in each cohort; the masks and nadir are already computed for the image pathway. Report sensitivity and specificity at one MU-fixed threshold, plus a calibration slope and intercept externally. All of this can go in a single supplementary table, with one sentence in the main text.

---

## Minor concerns

1. **Inconsistent scan counts.** MU has 146 scans (intended use), 181 (all scans, Table 1), 249 (Section 3.4, "all grade 4 detection scans") and 114 reports. A flow diagram (TRIPOD+AI / STARD style) showing which set feeds which analysis would remove the confusion. Table 1 note b's exclusion of 47 progression scans "with no index scan" also needs a reason in the text, because it is a large selective exclusion.
2. **Early-RT definitions differ between cohorts.** MU uses ≤84 days after RT end; LUMIERE uses the rater's "three months of radiotherapy" (from start or end?); UCSF assumes a six-week course from start. State that these differ and by roughly how much, since the card's situations depend on them.
3. **Ridge details.** How was the penalty chosen (nested CV?). How were missing IDH/MGMT values handled? Missingness is large at LUMIERE (22/61 IDH unknown) and UCSF (46/140). Is "unknown" a category the model uses, and therefore a site signal?
4. **Conformal model differs from the displayed score.** Section 2.1 says the conformal set's model "ranks scans slightly differently from the displayed combined score." A clinician could then see a high combined score with a set of {non-progression}. Quantify how often this happens, or build the set on the displayed model.
5. **Harmonisation of masks.** Three different segmentation sources (including DeepBraTumIA with three labels) feed one locked model. The harmonisation section is a TODO. At least one sentence in the main text should say how labels were mapped.
6. **Abstract density.** It carries eight numbers and two cohort names per sentence, which is hard to read. "A model trained there did better" is vague (see M2). "After one revision" in the last sentence reads as an admission without context.
7. **Section 3.1, last sentences.** The all-glioma +0.04 gain is a secondary set and is explained away in the same sentence. Either drop it from the main text (keep it in the Table 2 note) or leave it uninterpreted.
8. **Placeholders.** The Tikhonov citation is unverified (line 353). Several "Supplementary section" TODOs and all figures are placeholders. "Qwen3.8-27B": check that this is the exact released model name and give the version or hash.
9. **Table 2, row S2.** The cell is too long to read. Give the three cohorts as sub-rows, or move them to the supplement and keep "MU yes; LUMIERE set only; UCSF no" in the main table.
10. **Wording.** "Detected" (abstract, Section 3.1) suggests a decision. Use "separated" or "discriminated", since no threshold is used. The Section 3.4 heading is accurate but long; the Figure 4 caption repeats it.

---

## Claims I found well supported (keep these prominent)

- **Pre-specified, locked external testing with committed plans** (Table 2, commit hashes). This is rarer than it should be (3/20 in the cited review), and it is the paper's strongest methodological asset. It deserves a sentence in the abstract.
- **LUMIERE transfer of the locked combined model, 0.77 (0.68–0.86)**, meeting a pre-stated rule, on a cohort with a different label type (expert per-scan rating).
- **The images add to clinical data where there is no timeline at UCSF** (Q2: +0.25, CI 0.10–0.39). This supports the modular "image pathway runs without dates" argument.
- **Clinical-only near chance in all three cohorts.** This is a clean negative control for demographic or site leakage.
- **The schedule audit itself** (within- vs between-phase gain; schedule inputs in the planned imaging block). It is an important, generalisable warning for the field and is clearly shown. Rather than hiding it, frame it as a *finding*.
- **Deep networks above a permuted-label control, with scores tracking enhancing volume (r≈0.8).** This is a convincing demonstration that they rediscovered the measured evidence.
- **The split-variance demonstration** (0.80 on one split vs 0.72 over 500). It is a good justification for the evaluation design.
- **Report faithfulness under a fixed checker, plus the honest reporting of the failed first evaluation.**

---

## Tone, balance, and main text vs supplement

**Tone.** Mostly appropriately moderate, and refreshingly free of hype. The problem is the reverse of overclaiming in places. Almost every result sentence carries "(exploratory)", a CI qualifier or a pointer, and the cumulative effect is defensive. The labelling paragraph in Section 2.3 already lists what is exploratory, so repeating the label in every Results sentence is unnecessary. Keep it in figure captions and Table 2, and drop most of the inline repetitions. At the same time, the three places noted in M1, M3 and M5 (abstract 0.82, "met coverage at every centre", "faithful to the record") are slightly *stronger* than the evidence. The paper therefore manages to be over-hedged in its details and a little overstated in its headlines.

**Does it show what the system can do?** Partly. The genuine capabilities are:
- it runs where treatment dates are absent;
- it transfers locked to a centre with a different label type;
- it exposes, per scan, which evidence a score rests on;
- it produces reports that are checkable against the record.

These are real, but they are buried under the audit's caveats. The worked example in the Discussion (scan at 8 weeks with growing enhancement) is the most persuasive passage in the paper, and it is currently an "illustration" at the end. Move it, or a rendered version of it, into Figure 1 or Figure 5 and refer to it from the Introduction. It shows the system doing exactly the thing that the rest of the paper says it should do.

**Move to the supplement:**
- the three-step image ladder (Section 3.3, paragraph 2), leaving one sentence: "schedule inputs in the planned imaging block raised AUC across, not within, phases";
- most of the deep-network paragraph (keep one sentence);
- the LLM model-size comparison (L1);
- the S2/S3 per-cohort detail in Table 2;
- the all-glioma secondary gain in Section 3.1;
- the "stricter flag rule" sentence.

**Missing, and I would require it:**
- an enhancing-volume or RANO-like volumetric baseline in the main figure (M2, M6);
- class-conditional conformal coverage (M3);
- a scan-flow diagram (minor 1);
- calibration externally;
- an explicit statement of the exchangeability assumption;
- a TRIPOD+AI checklist in the supplement.

A small clinician read of the reports (M5) would considerably strengthen the system claim, but I would accept it as a stated limitation.
