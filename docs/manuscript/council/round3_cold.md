# Council Round 3: Cold Read

**Reader:** Biomedical engineering graduate student, ML background, no glioma knowledge.

## (1) What the paper claims and why it matters

PRISM is a modular system that detects glioma progression on post-treatment MRI by combining clinical/treatment timeline evidence and tumor imaging evidence as separate pathways, then transfers to other hospitals without refitting and communicates uncertainty through conformal sets and evidence cards. The system matters because glioma surveillance datasets are fragmented (incomplete treatment dates, varying documentation methods, small cohorts), hard cases are rare in any single centre, and clinicians need to know which evidence drove each prediction and how much to trust it at their own hospital.

## (2) Ten places I got lost or had to re-read

1. **"when the MGMT promoter is methylated"** (line 56)
   - Why does MGMT status matter for pseudoprogression risk? Not explained before use or motivated. Clinical relevance unclear to outsider.

2. **"segmented tumour volumes are noisy and patient records often cannot leave the hospital, so the clinician must see what was measured, in a report written inside it"** (lines 67–68)
   - The causal logic jumps. Why can records not leave? Why must the clinician see what was measured *because* records can't leave? These seem like separate problems.

3. **"ridge logistic regressions, with every fitted step inside the training data"** (lines 109–110)
   - What does "every fitted step inside the training data" mean? Unclear phrasing; sounds like it's preventing data leakage, but how?

4. **"conformal set is a patient-level split conformal prediction set at the 80% level, holding one or both outcomes and built to contain the true outcome for at least 80% of scans"** (lines 135–136)
   - Jargon-heavy. What does "holding one or both outcomes" mean? Why would a set hold "both"? Not explained for readers unfamiliar with conformal prediction.

5. **"They form the imaging block of the planned model, so PRISM's image pathway leaves them out."** (line 259)
   - Paradoxical: these inputs achieved 0.81 AUC (highest in the ladder), but are excluded because they "encode the scan schedule." Why is encoding the schedule a *bad* thing if it improves detection?

6. **"the three-step comparison of image models"** (line 201)
   - Marked exploratory, mentioned in Section 3.3, but it's unclear which specific analyses are post-hoc and which were pre-planned until you cross-reference Table 2.

7. **"progression was dated a median of 7 days after the evaluated scan"** (lines 265–266)
   - At UCSF, why is progression dated *after* the scan? Is this a study design issue? How does this affect what the task is testing?

8. **"a model trained there did better"** (line 38, abstract; repeated line 234)
   - Vague. How much better? On what metric? Confidence interval? This is a key message but leaves me without numbers.

9. **"the intervals overlap"** (line 300)
   - Dismissing a finding based on CI overlap, but no p-value or reasoning given for why overlap means "no difference."

10. **"A reader study in which clinicians use PRISM's reports at the scan would show whether separate evidence and a stated confidence change their decisions."** (lines 373–374)
    - This is presented as future work, but the entire system's clinical utility rests on this. Is the paper claiming to have solved the clinical problem without evidence clinicians actually use the reports?

## (3) Terms or abbreviations not defined before use

- **MGMT** (line 56) – mentioned without definition; only later implied to be a promoter methylation status
- **chemoradiotherapy** (line 53) – not explicitly defined (though contextually clear)
- **grade 4 glioma** (line 157) – grades of glioma never explained; what is grade 4?
- **pseudoprogression** (line 55) – used before explained; definition comes later (treatment enhancing without tumor growth)
- **conformal prediction set** (line 135) – statistical method name, not explained
- **segmented** (line 68) – in context of tumour volumes; not clear if automatic or manual
- **expert response rating** (line 159) – what are the categories? (Answered later as "stable or responding" or "progressive disease")
- **patient-grouped cross-validation** (line 182) – standard method but not explained for clinical readers
- **scan schedule** (line 246) – used as if defined; took re-reading to understand this means timing of scans
- **AUC** (line 84, throughout) – not defined; assumed reader knows area-under-curve

## (4) Sentences that sound like marketing, hiding weakness, or over-apologizing

- **"The third challenge, small cohorts, is handled by how PRISM is evaluated"** (lines 100–101) – Deflection rather than solution. Repeated cross-validation is standard; this doesn't solve the fundamental small-sample problem.

- **"its use at UCSF and in the system tests was planned"** (line 120) – Defensive phrasing. Reads like "we planned to use it after seeing it worked."

- **"The agreement rule and the card were defined after the cohort results had been seen and are exploratory."** (lines 145–146) – Honest but raises credibility questions. Post-hoc analysis of exploratory features dominates Sections 3.4 and 3.5.

- **"the images did not raise the timeline's AUC"** (line 216) – Neutral framing of a null result, but then immediately pivots to "the planned imaging model fell short." This negative result is central to the paper's message but undersold.

- **"Each of PRISM's components has been described before, and we are not aware of a system that combines them."** (line 346) – Defensive novelty claim. Reads like "we didn't invent anything new, just combined things."

- **"Progression is the progression documented by each centre, without expert re-reading of the scans; at UCSF it agrees closely with an enhancement call at the same scan."** (lines 360–361) – This is a major limitation (ground truth is not independent of the imaging signal) but presented matter-of-factly.

- **"The coverage threshold was met on point estimates, and at UCSF the interval reached below it"** (line 362) – Emphasizing point estimate while downplaying the interval going below target. Borderline cherry-picking.

## (5) Did the abstract make me want to read on?

**No, not really.** 

The abstract (lines 32–42) is dense with numbers (0.82, 0.77, 0.80, 0.73) and results without context. As an outsider:
- I don't know if 0.82 AUC is good or barely useful (is that 82% accuracy? No? Then what?).
- "a model trained there did better" is vague and unexplained—*how much* better? 
- The phrase "after one revision every report passed a check against its record" sounds like the first version failed, which is downplayed.
- The separate pathways and confidence mechanism are mentioned but not *motivated*—why should I care that evidence is separated?

The abstract reads like a checklist of results rather than a story. It would be more compelling if it opened with the clinical problem (pseudoprogression confusion, fragmented data, need for clinical decision support) and then showed why PRISM's modular design solves it. Instead, it jumps to methods and numbers. A reader would need to skip to Introduction to understand why this matters.

---

## Summary for the author

**Confusions to prioritize (top 5):**
1. Why MGMT methylation matters clinically and how it relates to pseudoprogression
2. What exactly "documented" progression is (definition varies by cohort; is it the ground truth?)
3. Why the best-performing imaging inputs (0.81 AUC) were removed for "encoding the scan schedule"
4. Quantify "a model trained there did better"—how much better than 0.73?
5. The prevalence of exploratory analyses (image pathway definition, agreement rule, reliability card) makes it hard to know which results to trust going forward
