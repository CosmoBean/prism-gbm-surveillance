# The reserve: questions we leave to the reviewers

Results that are true, checked and ready, but deliberately not in the main text (the 80 / 20 rule,
[STYLE.md](STYLE.md) section 4). Each row gives the likely reviewer question, the short answer, and where the full
answer lives. When a reviewer asks, the response quotes the answer and points to the supplement section.

Rule: an item may sit here only if it leaves the paper's conclusion unchanged. Anything that would change what a
reader concludes belongs in the main text.

| Likely question | Short answer | Where |
|---|---|---|
| Is the phase effect an artefact of censoring? | No. Censoring sits almost entirely before RT (38 of 39 censored scans); phase-specific weights raised the phase gain (+0.080 → +0.124) and excluding patients with undocumented RT left +0.057. In the intended use, 1 scan is censored. | Supplementary S20, S23; `docs/results/INTENDED_USE.md` |
| Would deaths counted as non-events change anything? | Absolute AUCs move (corrected core 0.706); no imaging contrast moves by more than 0.011. | S23 |
| Did you try enough imaging? | Radiomics over 70 configurations, frozen encoders over 32, fine-tuned SwinUNETR / BrainSegFounder (forward: 5 arms; detection: 9 arms incl. siamese and subtraction inputs) with shuffled-label controls, resegmentation with two networks, an imaging-defined label, and ADC in CFB-GBM. None beat the timing model. | Table 3 / S13, S14, S18, S22; `docs/results/DETECTION_DEEP.md` |
| Why did the fine-tuned networks fail at detection? | Image-only AUC 0.45–0.51, indistinguishable from the permuted-label control (0.48); about 87 training scans per network, early stopping at epochs 0–3. With few positives, the networks never learned what the volume measurements encode. | `docs/results/DETECTION_DEEP.md` |
| Why is a pooled AUC below 0.5 for some deep arms? | Within each fold the AUC is about 0.50; pooling across folds lowers it because training and test prevalence are anti-correlated (r = −0.99). | `DETECTION_DEEP.md`, exploratory diagnostics |
| Are the volumes trustworthy? | Our volumes reproduce the dataset's own table (r ≥ 0.996); resegmentation agrees (median ET Dice 0.80). Volume series are noisy: median 3.2-fold ET change between scans ≤ 14 days apart. | S14; `docs/results/DIAGNOSTICS_IMAGING.md` |
| Is ridge the right learner? | Gradient boosting did not beat ridge (core 0.687 vs 0.698). | Table 2 / S12 |
| How well calibrated is it? | Corrected core: observed / expected 1.04, slope 0.85; intended use O/E 1.01, slope 0.53 (spread too wide because part of the range encodes pre- vs post-RT); LUMIERE O/E 0.99, slope 0.97. | S12, S23 |
| Which features does the model rely on? | SHAP gives imaging blocks about half of the credit in the full models without any gain in AUC; attribution is not evidence of value. | Fig. (ablation C) / S12 |
| Does the external test hold? | LUMIERE, locked: forward corrected core 0.635; detection 0.77 with imaging adding +0.08 (−0.01 to +0.16). LUMIERE has no treatment dates and rating-defined negatives. | S13; `docs/results/DETECTION_TASK.md` |
| What exactly is in the imaging-only detection model? | Volumes, shape and relative intensity at the scan; volume ratios to the previous scan; ratio to the smallest volume over the whole history. The version with days since the previous scan, a has-previous flag and an RT-anchored nadir window scored 0.81; those three inputs encode the schedule. | `DETECTION_TASK.md`, exploratory section; `scripts/exploratory_pure_imaging_detection.py` |
| Could the report generator be gamed, or is it model-specific? | The checker is deterministic; a smaller model (Qwen3.5-9B) passed 243 / 249; reports followed the changed field in all 30 perturbed records; the original ungrounded prompt gave advice in 99% of reports. | S19, S21 |
| Why not a forward triage model? | Volume-trajectory features add −0.008 in the intended use; no rule-out threshold reaches an NPV lower bound of 0.85 (best 0.66). A triage model needs multicentre data, expert-read labels and perfusion. | `docs/results/TRIAGE_FEASIBILITY.md` |
| How does this relate to Christodoulou 2026 (0.80 on MU-Glioma-Post)? | Different label (progression status of each scan, i.e. detection) and one held-out set; we did not re-evaluate it. Our detection timing model alone reaches 0.82 on this dataset. | Discussion (one sentence); `docs/literature/COMPARABLE_RESULTS.md` |
