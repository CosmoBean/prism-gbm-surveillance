# Reproduction & Validation Findings

Run on orchard-community-4 (4× H100), 2026-10-04. Raw data: `sbandred/mu-glioma-post-raw`.

## 1. Did the reported numbers reproduce?

| Stage | Reported | Reproduced | Status |
|---|---|---|---|
| Radiomics prep (manifests, features) | HF `mu-glioma-post-processed` | 7/7 manifests identical; features match to float noise | ✅ |
| Radiomics calibrated LogReg-48 | Test AUC 0.8043, Brier 0.154, CM 12/56/6/10 | Identical (shipped bundle on our features, and retrain with shipped config) | ✅ |
| Radiomics default `main.py train` | LogReg-48 | Selects SVM-32, test AUC 0.7977 | ⚠️ shipped model came from an unrecorded run |
| SWIN embeddings (notebook) | 594 × 48-d | Reproduce only with the 3rd model built after `seed(42)` | ✅ after fix |
| Fusion MLP (shipped weights) | AUC 0.8006, acc 0.8095, F1 0.6522 | Identical (all probs within 1e-4) | ✅ |
| Fusion MLP (retrained, 50 seeds) | same | AUC ≈ 0.80; acc/F1 reached only at ~95th pct / max | ⚠️ lucky seed |
| Agent (patient 0019) | Fusion prob 0.4306 / 0.5782, RANO, confounders | Identical; SHAP within sampling noise; LLM text not run | ✅ |

## 2. Validation issues found

**Embedding model (`SWIN UNetR/` notebook)**
- Not a SwinUNETR: a small transformer with **random, untrained weights**; no pretrained weights loaded.
- Embeddings carry ~no outcome signal: alone in fusion AUC 0.50; linear probe 0.55 (train CV) / 0.62 (test). Main variance tracks lesion/cavity size.

**Fusion MLP (`MLPFusion/fusion_mlp.py`)**
- Checkpoint chosen on **test loss** (leakage, ≈ +0.01 AUC).
- Cutoff 0.48 hand-tuned; radiomics compared at 0.48 instead of its own 0.455 → reported recall/F1 "gain" is an operating-point shift.
- No seeds; never beats radiomics alone (0.8043). Score-only fusion = 0.8043; adding embeddings lowers it.
- `LayerNorm(vision_dim)` zeroes a 1-d vision input → cannot fuse a single image score.

**Other**
- MU mask labels are **1=NETC, 2=SNFH, 3=ET, 4=RC** (confirmed by BraTS zero-shot); `radiomics/radiomics_tools/metrics/constants.py` `LABEL_MAP` is wrong (does not affect the shipped model, which uses labels 1–3 as a union).
- 59/97 never-progressor negatives have <120 days of follow-up (unverified labels).
- Test set is 84 scans / 30 patients: patient-bootstrap AUC CI ≈ [0.66, 0.91].

## 3. New work: BraTS-pretrained SwinUNETR (MONAI BraTS21 fold 1)

All 30 test patients excluded from every training/selection step.

| Step | Result |
|---|---|
| Zero-shot on MU | WT Dice 0.85; ET ↔ label 3 (0.81) |
| Stage 1: segmentation fine-tune (TC/WT/ET + new RC head) | Val mean Dice 0.495 → **0.697** (RC 0.01 → 0.53) |
| Stage 2: progression fine-tune (lesion-pooled, 5 OOF folds + full) | Image-only OOF AUC 0.59–0.60, test **0.64–0.65** |
| Late fusion [radiomics score, image prob] | Test AUC 0.790–0.809 vs 0.8043; Δ 95% CI spans 0 |

- Global-average-pooled encoder features are ~identical across scans (corr ≈ 1.0); lesion-masked multi-scale pooling is required.
- Segmentation fine-tuning did not improve the progression model over the pretrained start.

## 4. Bottom line

All reported numbers reproduce from the code. The radiomics model carries the signal; neither the original random embeddings nor the fine-tuned BraTS SwinUNETR add measurable value in fusion on this cohort (231 train scans, 30 test patients).
