# Deep features: frozen SwinUNETR encoders vs the clinical + timing + treatment baseline (2026-10-11, final)

**Status: final numbers.** Evaluation re-run in the final full re-run (`outputs/results/analyses/deep/`, 2026-10-11 07:22–07:28,
HEAD `cc2e3a3`, clean tree; `run_info.json`), i.e. with the final labels, as-of-scan treatment features, the
mean-over-repeats estimator and the LUMIERE empty-segmentation fix. Features were not re-extracted. The pretrained-vs-random
paired comparisons on LUMIERE come from a separate verifier check
(`<scratchpad>/deepv/check.py` → `check.log`, 2026-10-11 07:10); its baseline / deep / random-deep AUCs, O/E and slopes equal
the final `lumiere/locked.csv` to 3 decimals, so the two are consistent.

Design: `docs/DL_COMPARISON_DESIGN.md` (arms D0, D1, D1b and a locked LUMIERE test; D2 fine-tuning and D3 diffusion features were not run).

## How to run

```bash
# 1. extraction (GPU, ~35 min MU + ~6 min LUMIERE on one H100); the shared .venv already has torch 2.14 + MONAI 1.6.1
CUDA_VISIBLE_DEVICES=1 uv run --frozen --no-sync python -m prism.features.deep
#    -> outputs/features/deep_{brats21,bsf,random}.parquet (594 MU scans) and deep_*_lumiere.parquet (132 rows)
# 2. evaluation (CPU, 24 processes, ~8 min for both populations + LUMIERE)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 uv run --frozen --no-sync python -m prism.analyses.deep_features
#    -> outputs/results/analyses/deep/{grade4,all_glioma}/{results,nested_choices,diagnostics,oof,oof_repeats}.csv, lumiere/locked.csv
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
| Baseline (clinical + timing + treatment, ridge) | 0.698 [0.615, 0.774] | — | 0.720 [0.638, 0.792] | — |
| **D1 pretrained deep, nested over 32** | 0.704 | **+0.006 [−0.058, +0.071]** | 0.725 | **+0.005 [−0.044, +0.054]** |
| D0 random-weight control, nested over 16 | 0.657 | −0.041 [−0.077, −0.007] | 0.716 | −0.003 [−0.019, +0.010] |
| D1b deep + legacy radiomics, nested over 16 | 0.704 | +0.006 [−0.018, +0.030] | 0.735 | +0.015 [−0.015, +0.046] |
| DS shared regions only, nested over 16 | 0.695 | −0.003 [−0.061, +0.062] | 0.726 | +0.006 [−0.035, +0.049] |
| DV: baseline+volumes+D1 vs baseline+volumes | 0.693 vs 0.702 | −0.009 [−0.049, +0.035] | 0.730 vs 0.733 | −0.003 [−0.034, +0.029] |

Sources: `outputs/results/analyses/deep/{grade4,all_glioma}/results.csv` (baseline row = C3 baseline, identical to
`c3/<population>/results.csv`).
- Single configurations (80 per population) with a ΔAUC CI above 0: **0 / 80** in both populations (grade 4: 3 / 80 below 0).
- Median ΔAUC per family: grade 4 D1 +0.008, D0 −0.023, D1b +0.007, DS +0.001; all gliomas D1 +0.015, D0 −0.009,
  D1b +0.018, DS +0.009.
- The nested D1 choice used bsf in 14/25 grade-4 folds and 17/25 all-glioma folds (`nested_choices.csv`).
- Calibration: nested D1 slope 0.49 (grade 4) / 0.70 (all gliomas) vs baseline 0.89 / 0.88 (`results.csv`; see also
  `CLINICAL_UTILITY.md`: Δ net benefit CIs all span 0).

**Diagnostics** (`diagnostics.csv`) use the image-only stacked score of the modal nested config:
- Grade 4: pretrained D1 image-only AUC 0.703 (DS 0.697, D1b 0.705); random encoder D0 0.568. The D1 score correlates with
  log tumour volume at r = 0.55 and with the baseline score at r = 0.26.
- All gliomas: pretrained 0.70–0.72, random 0.59.

So pretrained features carry image-only signal, largely related to size, that is not additive to the clinical + timing +
treatment baseline.

## Locked LUMIERE test

- The DS configuration was chosen by inner CV on all MU, refit on all MU, and applied once.
- The baseline uses shared features: clinical+timing (no treatment), ± volumes.
- 118 of 132 LUMIERE scans (57 patients) have deep features (7 without DeepBraTumIA output, 7 with an empty segmentation).

Results (`outputs/results/analyses/deep/lumiere/locked.csv`; pooled IPCW AUC, patient bootstrap):

| Train (MU) | Base | Arm (config) | AUC [95% CI] | ΔAUC vs baseline [95% CI] | O/E | Slope |
|---|---|---|---|---|---|---|
| grade 4 | clinical+timing | baseline | 0.622 [0.493, 0.746] | — | 1.00 | 0.58 |
| grade 4 | clinical+timing | + deep (brats21, shared, pca30, concat) | 0.690 [0.575, 0.789] | +0.068 [−0.116, +0.238] | 1.84 | 0.53 |
| grade 4 | clinical+timing | + random-encoder deep, same config | 0.660 [0.538, 0.768] | +0.039 [−0.149, +0.213] | 2.10 | 0.34 |
| grade 4 | clinical+timing+volumes | baseline → + deep | 0.635 → 0.686 | +0.051 [−0.123, +0.228] | 1.82 | 0.52 |
| all gliomas | clinical+timing | baseline → + deep (bsf, shared, l1, stack) | 0.624 → 0.702 | +0.078 [−0.010, +0.162] | 1.38 | 1.20 |
| all gliomas | clinical+timing | + random-encoder deep, same config | 0.645 | +0.021 [−0.029, +0.067] | 1.11 | 0.68 |
| all gliomas | clinical+timing+volumes | baseline → + deep | 0.626 → 0.678 | +0.052 [−0.002, +0.113] | 1.39 | 1.06 |

Deep score alone (no clinical): grade 4 brats21 0.642 vs random 0.641; all gliomas bsf 0.669 vs random 0.585.

**Pretrained vs random-weight control, paired** (from the verifier check `check.log`, same 118 scans, 1000 patient
bootstraps; "same config" = random encoder with the pretrained arm's selection/integration):

| Train · base | + deep vs + random deep (same config) | vs random deep (own inner-CV best) |
|---|---|---|
| grade 4 · clinical+timing | +0.029 [−0.078, +0.148] | +0.029 [−0.078, +0.148] (same config chosen) |
| grade 4 · clinical+timing+volumes | +0.027 [−0.075, +0.138] | +0.027 [−0.075, +0.138] (same config chosen) |
| all gliomas · clinical+timing | +0.057 [−0.017, +0.131] | +0.057 [−0.017, +0.131] (same config chosen) |
| all gliomas · clinical+timing+volumes | +0.048 [−0.012, +0.110] | +0.040 [+0.005, +0.083] |

**Cohort shift** (`check.log`): a 5-fold logistic classifier on the deep features separates LUMIERE from MU scans with
AUC 0.82 / 0.79 / 0.81 (brats21 / bsf / random; grade-4 MU), median |SMD| LUMIERE vs MU 0.37 / 0.59 / 0.28. Mean predicted
risk on LUMIERE falls from 0.388 (baseline) to 0.211 (+ deep, grade 4) while the MU in-sample mean is 0.42–0.43 for both,
hence the O/E of 1.8–2.1 for every grade-4 deep arm, random included.

**Reading.**
- **MU: no added value.** Nested pretrained deep features change the baseline by +0.006 [−0.058, +0.071] (grade 4) and
  +0.005 [−0.044, +0.054] (all gliomas), no single configuration has a CI above 0, and the nested models are overfit
  (slope 0.49). This matches C3 radiomics.
- Pretrained encoders do beat the random-weight control on MU (image-only AUC 0.70–0.72 vs 0.57–0.59; nested D0 is
  significantly worse than baseline in grade 4, −0.041), so the PRISM report's random encoder could not have carried signal.
- **LUMIERE: a non-significant gain that is not reliably above the random-weight control.** + deep gives +0.05 to +0.08 over
  the shared baseline with every CI spanning 0. A random-weight encoder with the same configuration gains +0.02 to +0.04 by
  itself, and pretrained beats random by only +0.03 to +0.06 (one of four paired comparisons has a CI above 0).
- **The features are cohort-separable and the deep models under-predict.** Deep features identify the cohort (AUC ≈ 0.8,
  random weights too), and the pretrained deep arms under-predict LUMIERE risk (O/E 1.38–1.84 vs 1.00–1.37 for the
  matching baselines). The external
  "gain" is therefore as consistent with a cohort/scanner shift that happens to re-rank scans as with transportable biology.
  A second external cohort would be needed to say more.

## Licences

- **MONAI BraTS21 SwinUNETR weights**: Apache-2.0. Redistribution and use are permitted with attribution.
- **BrainSegFounder** (Cox et al., *Med Image Anal* 2024, doi 10.1016/j.media.2024.103301):
  - The weights are released under `license: other`, `uk-biobank-mta`, i.e. the UK Biobank Material Transfer Agreement.
  - They derive from UK Biobank data, so use is limited to bona fide health-related research under the MTA terms.
  - We must not redistribute the weights or derived weights. Commercial use is not covered.
  - Cite the paper. Check that the MTA terms allow publishing features or derived models.
  - We only download the weights for local feature extraction. They are not committed or shared, and `data/` is gitignored.
- **LUMIERE**: CC0. **MU-Glioma-Post**: TCIA terms.
