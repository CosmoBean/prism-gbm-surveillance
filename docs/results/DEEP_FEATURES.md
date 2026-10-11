# Deep features: frozen SwinUNETR encoders vs the clinical + timing + treatment baseline (2026-10-11, PROVISIONAL)

**Status: provisional.** Run on the working tree at commit `0faa26c` (branch `manuscript-week`). Uncommitted changes then in progress: label fixes (`prism/data/mu.py`), treatment as-of-scan features (`tabular.py`), and the new repeated-CV estimator (`metrics.py`, `c3_radiomics.py`). See `outputs/results/analyses/deep/run_info.json` for the exact dirty-file list. The evaluation reads cohort, labels, folds and baseline features from the code at run time. Re-run it after the fixes land; the features do not need to be re-extracted.

Design: `docs/DL_COMPARISON_DESIGN.md` (arms D0, D1, D1b and a locked LUMIERE test; D2 fine-tuning and D3 diffusion features were not run).

## How to run

```bash
# 1. extraction (GPU, ~35 min MU + ~6 min LUMIERE on one H100); the shared .venv already has torch 2.14 + MONAI 1.6.1
CUDA_VISIBLE_DEVICES=1 uv run --frozen --no-sync python -m prism.features.deep
#    -> outputs/features/deep_{brats21,bsf,random}.parquet (594 MU scans) and deep_*_lumiere.parquet (132 rows)
# 2. evaluation (CPU, 24 processes, ~8 min for both populations + LUMIERE)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 uv run --frozen --no-sync python -m prism.analyses.deep_features
#    -> outputs/results/analyses/deep/{grade4,all_glioma}/{results,nested_choices,diagnostics,oof}.csv, lumiere/locked.csv
```

Weights are in `data/weights/`, which is gitignored and never committed:
- `brats21_swinunetr_fold1_f48/model.pt`: from the GitHub release `Project-MONAI/MONAI-extra-test-data` 0.8.1.
- `brainsegfounder_brats_ft.pt`: `model_weights_BRATS-finetune.pt` from `huggingface.co/smilelab/BrainSegFounder`.

## Method

**Encoders.** All three are the same MONAI SwinUNETR (4 channels FLAIR/T1c/T1/T2, feature size 48); only the `swinViT` encoder is used.
- `brats21`: BraTS 2021 weights.
- `bsf`: BrainSegFounder, UK Biobank SSL followed by BraTS fine-tuning.
- `random`: the same architecture with random weights (torch seed 0). This is the mandatory control, and the same encoder type as the PRISM report's.

**Input.** Skull-stripped 1 mm volumes, z-scored within the brain, reoriented to LPS (LUMIERE MNI images are reoriented) and zero-padded to a multiple of 32. Features are averaged over 8 flip test-time augmentations.

**Features.**
- Mask-weighted mean pooling at feature-map resolution, stages 0–3 (48+96+192+384 = 720 per region).
- The 768-d bottleneck is extracted but not used: for `brats21` its between-scan SD is 3e-4, i.e. constant.
- Regions on MU:
  - lesion = ET ∪ NETC ∪ SNFH
  - ET, NETC, SNFH
  - 5 mm peri-cavity rim
  - ET ∪ SNFH
- Regions on LUMIERE (DeepBraTumIA): ET, SNFH, ET ∪ SNFH, lesion. NETC and cavity are not used, because DeepBraTumIA labels the cavity as necrosis.

**Evaluation.** This is exactly the C3 protocol, using `c3.fit_predict` and `c3.inner_auc` imported, not copied:
- Ridge, verified 120-d labels, 5×5 patient-grouped folds.
- In-fold selection: top-10 F, PCA-10, PCA-30, or L1.
- Integration: stacked inner-OOF deep score, or concatenation.
- Nested choice over each family:
  - **D1**: 2 pretrained encoders × {lesion, compartments} × 4 selections × 2 integrations = 32 configs.
  - **D0**: random encoder, 16 configs.
  - **D1b**: legacy radiomics + deep in one stacked score, 16 configs.
  - **DS**: shared regions only, 16 configs.
  - **DV**: baseline + volumes ± nested D1.
- Headline = mean over repeats of the per-repeat IPCW AUC(120 d). ΔAUC vs the ridge baseline is reported with a paired patient-cluster bootstrap (1000), using `metrics.evaluate_repeated`.

## Results on MU (nested = honest estimate)

| Arm | Grade 4: AUC | Grade 4: ΔAUC [95% CI] | All gliomas: AUC | All gliomas: ΔAUC [95% CI] |
|---|---|---|---|---|
| Baseline (clinical + timing + treatment, ridge) | 0.722 | — | 0.744 | — |
| **D1 pretrained deep, nested over 32** | 0.722 | **−0.000 [−0.043, +0.039]** | 0.736 | **−0.008 [−0.049, +0.032]** |
| D0 random-weight control, nested over 16 | 0.711 | −0.011 [−0.025, +0.001] | 0.738 | −0.006 [−0.020, +0.008] |
| D1b deep + legacy radiomics, nested over 16 | 0.721 | −0.001 [−0.020, +0.016] | 0.763 | +0.019 [−0.002, +0.041] |
| DS shared regions only, nested over 16 | 0.732 | +0.010 [−0.022, +0.040] | 0.741 | −0.003 [−0.038, +0.031] |
| DV: baseline+volumes+D1 vs baseline+volumes | 0.716 | −0.014 [−0.037, +0.008] | 0.730 | −0.020 [−0.048, +0.004] |

Sources: `outputs/results/analyses/deep/{grade4,all_glioma}/results.csv`.
- Single configurations with a ΔAUC CI above 0: **2 / 84** in each population. Expected by chance: about 2.
- Median ΔAUC per family:
  - Grade 4: D1 +0.010, D0 −0.012.
  - All gliomas: D1 +0.007, D0 −0.014.
- The nested D1 choice used brats21 in 16/25 grade-4 folds and bsf in 15/25 all-glioma folds.

**Diagnostics** (`diagnostics.csv`) use the image-only stacked score of the modal nested config:
- Grade 4:
  - Pretrained encoder: image-only AUC 0.64–0.68.
  - Random encoder: 0.48.
  - The D1 score correlates with log tumour volume at r = 0.56. It correlates with the baseline score at r = 0.16.
- All gliomas: pretrained 0.68–0.70, random 0.57.

So pretrained features carry real image-only signal, largely related to size. That signal is not additive to the clinical + timing + treatment baseline.

## Locked LUMIERE test

- The DS configuration was chosen by inner CV on all MU, refit on all MU, and applied once.
- The baseline uses shared features: clinical+timing, with no treatment.
- 118 of 132 LUMIERE scans (57 patients; 43 positive / 68 negative / 7 censored) have features:
  - 7 scans have no DeepBraTumIA output.
  - 7 have an empty segmentation.

Results (`outputs/results/analyses/deep/lumiere/locked.csv`):

| Train (MU) | Arm (config) | AUC [95% CI] | ΔAUC vs baseline [95% CI] | O/E | Calibration slope |
|---|---|---|---|---|---|
| grade 4 | baseline clinical+timing | 0.630 [0.513, 0.750] | — | 1.19 | 0.76 |
| grade 4 | + deep (brats21, shared regions, top10, concat) | **0.751** [0.630, 0.848] | **+0.121 [+0.011, +0.211]** | 2.32 | 1.11 |
| grade 4 | + random-encoder deep, same config | 0.616 | −0.014 [−0.130, +0.081] | 1.29 | 0.39 |
| grade 4 | deep score alone / random alone | 0.702 / 0.574 | — | — | — |
| grade 4 | baseline +volumes → + deep | 0.647 → 0.733 | +0.086 [+0.015, +0.153] | 2.19 | 1.08 |
| all gliomas | baseline → + deep (bsf, shared, l1, concat) | 0.627 → 0.721 | +0.094 [−0.030, +0.206] | 2.88 | 0.57 |

**Reading.**
- On MU, frozen deep features do not improve the baseline. The nested ΔAUC is about 0 with CIs of roughly ±0.04, matching C3 radiomics.
- Pretrained encoders beat the random-weight control. This holds in image-only AUC (0.64–0.70 vs 0.48–0.57) and in median ΔAUC (+0.01 vs −0.01). It also shows that the PRISM report's random encoder could not have carried signal.
- The locked LUMIERE gain (+0.12) is large but should be treated with caution, for four reasons:
  - It is a single test on 57 patients with wide CIs.
  - The LUMIERE baseline is weak (no treatment features, 0.63).
  - The MU internal estimate for the same family is only +0.010.
  - Predictions are badly miscalibrated (O/E 2.3).
- What favours a real image effect on LUMIERE is that the random-encoder control gives no gain there. Confirm this after the label fixes, and preferably on a second external cohort.

## Licences

- **MONAI BraTS21 SwinUNETR weights**: Apache-2.0. Redistribution and use are permitted with attribution.
- **BrainSegFounder** (Cox et al., *Med Image Anal* 2024, doi 10.1016/j.media.2024.103301):
  - The weights are released under `license: other`, `uk-biobank-mta`, i.e. the UK Biobank Material Transfer Agreement.
  - They derive from UK Biobank data, so use is limited to bona fide health-related research under the MTA terms.
  - We must not redistribute the weights or derived weights. Commercial use is not covered.
  - Cite the paper. Check that the MTA terms allow publishing features or derived models.
  - We only download the weights for local feature extraction. They are not committed or shared, and `data/` is gitignored.
- **LUMIERE**: CC0. **MU-Glioma-Post**: TCIA terms.
