# Re-segmentation with one consistent model: does it rescue the imaging positive controls? (2026-10-11)

Code: `prism/features/reseg.py` (GPU inference) and `prism/analyses/reseg_eval.py` (evaluation).
Outputs: `outputs/features/seg_swin/` and `outputs/results/analyses/reseg/`.

## Pre-specified decision rule (written before any result was looked at)

Primary segmenter: MONAI BraTS21 SwinUNETR (`brats21`). BrainSegFounder (`bsf`) is a sensitivity analysis.

The new segmentation **helps** if at least one of these holds:

1. **Concurrent detection improves.** Task: progression scan vs verified 120-day negatives, all gliomas, ridge,
   imaging only (volumes + delta). This is the cleanest task in `DIAGNOSTICS_IMAGING.md`, where MU masks gave 0.68.
   The AUC must rise by ≥ 0.05 over the MU masks, and the paired patient-cluster bootstrap 95% CI must exclude 0.
2. **ET is usually larger at progression.** Paired test, progression scan vs previous scan, all gliomas: the
   fraction of pairs with larger ET at the progression scan must exceed 65%. With MU masks it was 49%.

If the rule holds, the doc says which downstream analyses to rebuild. If not, we conclude that the limit lies in the
labels and data, not in the segmentation.

## Method

**Inference.** `python -m prism.features.reseg --gpus 2 [--model bsf]`.
- Inputs: 594 MU scans with complete sequences, in FLAIR/T1c/T1/T2 order.
- Normalisation: `NormalizeIntensity(nonzero=True, channel_wise=True)`, as in the MONAI BraTS21 tutorial.
- Sliding-window inference: roi 128³, overlap 0.5, sigmoid > 0.5 on (TC, WT, ET).
- Labels are written in the MU convention: 3 ET, 1 NETC = TC − ET, 2 SNFH = WT − TC.
- MU images are already 1 mm BraTS space (LPS, 240×240×155), so no resampling was needed. The label maps share the
  MU mask header.
- Smoke test on 3 scans of patient 0003: Dice vs MU was ET 0.86–0.90 and WT 0.93–0.96, so orientation and channel
  order are right.
- BrainSegFounder's BraTS checkpoint loads strictly as the full SwinUNETR, decoder included, so it was run as a second
  segmenter (`bsf`).

Outputs:
- label maps: `outputs/features/seg_swin/mu/<patient>/<timepoint>.nii.gz` (bsf: `seg_swin/mu_bsf/`)
- `outputs/features/seg_swin/volumes_{brats21,bsf}.csv`: voxel counts and Dice vs MU

Runtime: 447 s for both models together (2 H100s each).

**Evaluation.** `python -m prism.analyses.reseg_eval --workers 60` (8 min).
- For each segmenter, the measurement table is rebuilt with the `measurements.py` logic (volumes, morphology,
  intensity, past-only deltas). The positive controls in `diagnostics_imaging.py` are then re-run on the same 591 scans.
- **Compartments.** ET; TC = ET ∪ NETC (`tumor_cc`); WT = ET ∪ NETC ∪ SNFH (`lesion_cc`). BraTS models have no
  resection-cavity class, so RC is taken from the MU mask wherever the new map is background.
- **Caveat: TC is not comparable.** The BraTS models label most of the post-operative cavity as NETC (`qa/*0213*`).
  The new TC is therefore 1.35× MU's and partly measures the cavity. **ET and WT are the comparable compartments.**
- **Surgery between scans.** No re-resection dates exist. A pair was flagged when the MU cavity grew by ≥ 1 cc and
  ≥ 1.5×, or brachytherapy was inserted between the two scans. This flagged 65 of 389 consecutive pairs.

## 2. Agreement with the MU masks (`agreement.csv`)

| segmenter | Dice ET median [IQR] | Dice TC | Dice WT | Pearson log-vol ET / WT | median new/MU ET |
|---|---|---|---|---|---|
| brats21 | 0.80 [0.49, 0.91] | 0.62 | 0.85 [0.74, 0.93] | 0.92 / 0.91 | 0.97 |
| bsf | 0.81 [0.56, 0.91] | 0.68 | 0.86 | 0.94 / 0.92 | 0.94 |

Agreement is good for WT and moderate for ET. In 24% of scans, ET Dice is < 0.5, mostly where ET is small.

## 3. Longitudinal consistency (`consistency.csv`, `consecutive_pairs.csv`)

The table gives the median fold change between consecutive scans. Δ is the new − MU median |log ratio| with a paired
patient-cluster bootstrap 95% CI.

| window | n pairs | ET MU → brats21 (Δ) | TC MU → brats21 (Δ) | WT MU → brats21 (Δ) |
|---|---|---|---|---|
| ≤ 14 d | 25 | 3.20 → 2.45 (−0.27 [−1.03, 0.00]) | 3.18 → 2.19 (−0.37 [−1.25, −0.08]) | 1.80 → 1.61 (−0.12 [−0.32, 0.05]) |
| ≤ 14 d, no surgery flag | 18 | 3.29 → 2.50 | 3.31 → 2.21 | 1.70 → 1.59 |
| ≤ 30 d | 54 | 2.57 → 2.17 (−0.17 [−0.46, −0.02]) | 2.76 → 2.02 (−0.31 [−0.55, −0.02]) | 1.62 → 1.60 (−0.02 [−0.13, 0.23]) |
| > 90 d | 154 | 2.34 → 2.40 | 2.41 → 2.48 | 1.53 → 1.81 |

bsf is similar: ≤ 14 d ET 2.38, ≤ 30 d ET 2.14.

**Spearman of |log change| vs gap (all 389 pairs).**

| compartment | MU | brats21 | bsf |
|---|---|---|---|
| ET | −0.02 | −0.01 | 0.06 |
| WT | −0.01 | 0.07 | 0.06 |

**Reading.**
- One consistent segmenter removes some short-gap noise. At ≤ 30 d, the median |log ratio| falls by about 18% for ET
  and 30% for TC; WT is unchanged.
- Some MU jumps are clearly segmentation inconsistency. Examples: 0213 (ET 0 → 16 cc in 3 d under MU; the new mask
  gives 4.3 → 16.7 cc), 0211 (`qa/`) and 0237 (`consecutive_pairs.csv`).
- **But most of the short-gap noise remains.** A 2.4× ET change within 14 d is as large as the change over > 90 d.
  Change size is still unrelated to the gap.
- Of the implausible jumps named in DIAGNOSTICS_IMAGING, 0013 and 0070 persist under brats21 (|log ET| 2.3 and 3.5),
  while 0018 and 0123 shrink (2.28 → 1.39 and 1.16 → 0.93). Other large short-gap jumps (0022, 0065) also persist
  (|log ET| 3.1 and 2.0). So the images themselves differ between these closely spaced scans: early post-operative change,
  or acquisition/date issues. These are not masking artefacts.

## 4. Positive controls with the new volumes

**(a) Progression scan vs previous scan** (`paired_progression_vs_previous.csv`; 74 pairs; Δ is the bootstrap CI over
pairs):

| feature | MU | brats21 (Δ) | bsf |
|---|---|---|---|
| ET larger at progression | 49% (p 0.54) | 45% (−0.04 [−0.12, 0.05]) | 41% |
| TC larger | 53% | 47% | 36% |
| WT larger | 65% (p 0.03) | 57% (−0.08 [−0.16, −0.01]) | 58% |
| ET growth from nadir larger (n = 42) | 50% | 43% | 50% |
| WT growth from nadir larger | 79% | 74% | 71% |

By progression type (MU data dictionary 1 / 2 / 3; brats21):

| type | n | ET larger | ET growth from nadir larger | TC growth from nadir larger |
|---|---|---|---|---|
| 1 imaging | 40 | 52% (MU 50%) | 64% (MU 59%; p 0.046) | 73% (MU 59%) |
| 2 clinical | 7 | 29% | – | – |
| 3 both | 27 | 37% (MU 52%) | – | – |

**(b) Concurrent detection, imaging only** (volumes + delta, 5×5 patient-grouped CV; `detection_auc.csv`; all
gliomas):

| task | learner | MU | brats21 | Δ [95% CI] | bsf |
|---|---|---|---|---|---|
| progression scan vs verified 120-d negatives (**primary**) | ridge | 0.681 | 0.665 | **−0.016 [−0.057, 0.025]** | 0.677 |
| same | GBM | 0.698 | 0.677 | −0.021 [−0.061, 0.020] | 0.687 |
| progression scan vs all index scans | ridge | 0.620 | 0.603 | −0.017 [−0.057, 0.022] | 0.613 |
| both with a prior scan | ridge | 0.619 | 0.552 | −0.068 [−0.116, −0.018] | 0.567 |

Grade 4 shows the same pattern (primary task, ridge: 0.648 → 0.652).

**(c) Forward 120-day task, imaging only** (`forward_ipcw120.csv`; IPCW AUC(120), repo folds, ridge; Δ from
`evaluate_repeated`):

| population | MU | brats21 | Δ | bsf |
|---|---|---|---|---|
| all gliomas | 0.644 | 0.675 | +0.031 [−0.017, 0.084] | 0.643 |
| grade 4 | 0.600 | 0.629 | +0.028 [−0.018, 0.078] | 0.591 |
| clinical + phase + imaging, all gliomas | 0.712 | 0.740 | +0.029 [−0.010, 0.069] | 0.714 |

**Plain-AUC forward reference** (`detection_auc.csv`, `ref_label120_forward`). GBM: 0.653 → 0.712, Δ +0.059
[+0.014, +0.107] (all gliomas); 0.610 → 0.689 (grade 4). bsf GBM: +0.041. Ridge: +0.037 [−0.011, +0.085].

This is the only gain whose CI excludes 0. It is one of more than 20 comparisons, it was not pre-specified, and the
IPCW ridge estimate (the headline metric) does not confirm it. Treat it as exploratory.

## 5. QA (`qa/*.png`, `qa/qa_scans.csv`)

8 scans: 2 short-gap pairs with the largest MU ET jump (0211, 0213), plus 4 random index scans.

- On T1c, the new ET hugs the enhancing rim as well as MU's ET does.
- The new WT matches the FLAIR hyperintensity.
- The cavity is labelled as NETC (see the caveat above).
- In 0213 T1 (a day-0 post-operative scan), MU labels no ET even though a thin rim enhances. brats21 does label it.
- In 0186 T5, MU has ET of 0.5 cc and brats21 has almost none.

## Verdict

**The new segmentation does not help, by the pre-specified rule.**
- **Primary detection AUC:** 0.681 → 0.665, Δ −0.016 [−0.057, +0.025]. Not +0.05, and the CI includes 0.
- **ET larger at the progression scan:** 49% → 45%, not > 65%.
- **The second segmenter agrees:** bsf gives 0.677 and 41%.

A consistent segmenter removes part of the short-gap volume noise. However, ET still does not rise at the documented
progression scan, and imaging still detects the progression scan at only about 0.67.

**Conclusion: the limit lies in the labels and data, not the segmentation.** Three things point there:
- progression is often declared on non-volumetric or clinical grounds (type 2/3 pairs show ET *falling*);
- large real image changes occur between scans days apart (early post-op scans; possible date/order problems);
- the progression scan's predecessor often already looked similar.

Downstream analyses do **not** need rebuilding on the new masks. The exploratory forward plain-AUC gain (GBM +0.06)
could be checked as a sensitivity analysis, but it does not change the main conclusion.
