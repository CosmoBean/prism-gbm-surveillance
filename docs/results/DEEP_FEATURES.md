# Deep features: frozen SwinUNETR encoders vs the clinical + timing + treatment baseline (2026-10-11, final, after the clipping fix)

**Status: final numbers.** The evaluation was re-run after the radiomics clipping fix (`outputs/results/analyses/deep/`,
2026-10-11 18:23–18:33; `run_info.json`: commit `8c780df` + uncommitted `c3_radiomics.py`). Deep features go through
`c3.selector`, so they are now also clipped in-fold to their 1st/99th percentiles ([FIX_RADIOMICS_CLIP.md](FIX_RADIOMICS_CLIP.md)).
This run uses the final labels, as-of-scan treatment features, the mean-over-repeats estimator and the LUMIERE
empty-segmentation fix. Features were not re-extracted.

The pretrained-vs-random paired comparisons on LUMIERE come from the verifier script `<scratchpad>/deepv/check.py`, which
was re-run after the fix (`check_clip.log`, 2026-10-11). Its baseline / deep / random-deep AUCs, O/E and slopes equal
`lumiere/locked.csv` to 3 decimals. The pre-fix `check.log` (07:10) is superseded.

The clipping fix changed the deep results more than the radiomics results:
- Grade 4 nested D1 went from +0.006 to −0.004.
- All gliomas now has 3/80 single configurations with a CI above 0, against 0/80 before.
- The LUMIERE configurations chosen by inner CV changed in 2 of 4 cells.

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
| **D1 pretrained deep, nested over 32** | 0.694 | **−0.004 [−0.069, +0.063]** | 0.731 | **+0.011 [−0.032, +0.056]** |
| D0 random-weight control, nested over 16 | 0.649 | −0.049 [−0.085, −0.014] | 0.711 | −0.009 [−0.032, +0.009] |
| D1b deep + legacy radiomics, nested over 16 | 0.709 | +0.011 [−0.032, +0.054] | 0.751 | +0.031 [−0.003, +0.066] |
| DS shared regions only, nested over 16 | 0.699 | +0.001 [−0.057, +0.060] | 0.725 | +0.005 [−0.035, +0.046] |
| DV: baseline+volumes+D1 vs baseline+volumes | 0.694 vs 0.702 | −0.008 [−0.045, +0.033] | 0.739 vs 0.733 | +0.007 [−0.021, +0.036] |

Sources: `outputs/results/analyses/deep/{grade4,all_glioma}/results.csv` (baseline row = C3 baseline, identical to
`c3/<population>/results.csv`).
- Single configurations (80 per population) with a ΔAUC CI above 0:
  - Grade 4: **0 / 80**. 3 / 80 are below 0, all random-encoder D0.
  - All gliomas: **3 / 80**, all stacked at about +0.035 to +0.040 with lower bounds of +0.001 to +0.004:
    `rad+brats21:lesion|pca10|stack` +0.040 [+0.004, +0.074], `brats21:shared|pca30|stack` +0.037 [+0.003, +0.070] and
    `brats21:lesion|pca30|stack` +0.035 [+0.001, +0.070].
  - These counts are uncorrected. About 2 of 80 would exclude 0 by chance at a one-sided 2.5% level, and the nested D1
    estimate, which accounts for the selection, spans 0.
- Median ΔAUC per family: grade 4 D1 +0.010, D0 −0.023, D1b +0.004, DS +0.003; all gliomas D1 +0.017, D0 −0.011,
  D1b +0.025, DS +0.010.
- The nested D1 choice used bsf in 12/25 grade-4 folds and 13/25 all-glioma folds (`nested_choices.csv`).
- Calibration: nested D1 slope 0.55 (grade 4) / 0.79 (all gliomas) vs baseline 0.89 / 0.88 (`results.csv`; see also
  `CLINICAL_UTILITY.md`: no deep Δ net benefit CI excludes 0).

**Diagnostics** (`diagnostics.csv`) use the image-only stacked score of the modal nested config:
- Grade 4: pretrained D1 image-only AUC 0.652 (modal config `bsf:lesion|pca10|stack`, chosen in 6/25; DS 0.697, D1b 0.705);
  random encoder D0 0.566. The D1 score correlates with log tumour volume at r = 0.58 and with the baseline score at
  r = 0.28.
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
| grade 4 | clinical+timing | + deep (brats21, shared, pca30, concat) | 0.679 [0.552, 0.781] | +0.057 [−0.132, +0.235] | 2.08 | 0.55 |
| grade 4 | clinical+timing | + random-encoder deep, same config | 0.667 [0.542, 0.772] | +0.045 [−0.133, +0.213] | 2.06 | 0.45 |
| grade 4 | clinical+timing+volumes | baseline → + deep (bsf, shared, l1, concat) | 0.635 → 0.725 | +0.089 [−0.026, +0.215] | 1.76 | 0.87 |
| all gliomas | clinical+timing | baseline → + deep (brats21, shared, pca30, stack) | 0.624 → 0.688 | +0.064 [−0.011, +0.144] | 1.35 | 1.22 |
| all gliomas | clinical+timing | + random-encoder deep, same config | 0.631 | +0.007 [−0.054, +0.060] | 1.18 | 0.66 |
| all gliomas | clinical+timing+volumes | baseline → + deep (bsf, shared, l1, stack) | 0.626 → 0.676 | +0.050 [+0.002, +0.109] | 1.35 | 1.05 |

Deep score alone (no clinical), same configs: grade 4 brats21 0.633 vs random 0.659 (clinical+timing config) and bsf 0.693
vs random 0.661 (+ volumes config); all gliomas brats21 0.626 vs random 0.643, and bsf 0.674 vs random 0.607.

**Pretrained vs random-weight control, paired** (from the verifier re-run `<scratchpad>/deepv/check_clip.log`, same 118
scans, 1000 patient bootstraps). "Same config" means the random encoder with the pretrained arm's selection and
integration:

| Train · base | + deep vs + random deep (same config) | vs random deep (own inner-CV best) |
|---|---|---|
| grade 4 · clinical+timing | +0.011 [−0.095, +0.127] | +0.087 [−0.048, +0.233] (random pca10 concat) |
| grade 4 · clinical+timing+volumes | +0.069 [−0.004, +0.147] | +0.110 [+0.026, +0.205] (random pca10 concat) |
| all gliomas · clinical+timing | +0.057 [−0.007, +0.131] | +0.043 [−0.023, +0.106] (random l1 stack) |
| all gliomas · clinical+timing+volumes | +0.051 [−0.007, +0.113] | +0.035 [−0.000, +0.080] (random top10 stack) |

**Cohort shift** (`check_clip.log`; these feature-level numbers are identical to the pre-fix `check.log`):
- A 5-fold logistic classifier on the deep features separates LUMIERE from MU scans with AUC 0.82 / 0.79 / 0.81
  (brats21 / bsf / random; grade-4 MU).
- Median |SMD| LUMIERE vs MU is 0.37 / 0.59 / 0.28.
- Mean predicted risk on LUMIERE falls from 0.388 (baseline) to 0.186 (+ deep, grade 4, clinical + timing). The MU
  in-sample mean is 0.42–0.43 for both. This gives the O/E of 1.6–2.1 for every grade-4 deep arm, random included.

**Reading.**
- **MU: no added value.** Nested pretrained deep features change the baseline by −0.004 [−0.069, +0.063] (grade 4) and
  +0.011 [−0.032, +0.056] (all gliomas).
  - No grade-4 single configuration has a CI above 0. In all gliomas 3/80 do, about the number expected by chance.
  - The nested models are overfit (slope 0.55 grade 4). This matches C3 radiomics.
- Pretrained encoders do beat the random-weight control on MU. Image-only AUC is 0.65–0.72 vs 0.57–0.59, and nested D0 is
  significantly worse than the baseline in grade 4 (−0.049). So the PRISM report's random encoder could not have carried
  signal.
- **LUMIERE: a mostly non-significant gain that is not reliably above the random-weight control.**
  - + deep gives +0.05 to +0.09 over the shared baseline. One of four CIs is just above 0: all gliomas, clinical + timing +
    volumes, +0.050 [+0.002, +0.109].
  - A random-weight encoder with the same configuration gains −0.001 to +0.045 by itself.
  - Pretrained beats random by +0.011 to +0.069 with the same configuration, and no CI is above 0. Against random's own
    inner-CV best it wins by +0.035 to +0.110, and one of four CIs is above 0.
- **The features are cohort-separable and the deep models under-predict.** Deep features identify the cohort (AUC ≈ 0.8,
  random weights too). The pretrained deep arms under-predict LUMIERE risk: O/E 1.35–2.08, vs 1.00–1.37 for the
  matching baselines. The external
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
