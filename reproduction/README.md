# Reproduction, Audit & Research Direction — Overview

Work done on orchard-community-4 (4× H100), October 2026. This folder documents reproducing the reported results, auditing how they were obtained, rebuilding the image branch, and a literature review to position a publishable follow-up.

## Documents

| File | Contents |
|---|---|
| [FINDINGS.md](FINDINGS.md) | What reproduced, validation issues, BraTS SwinUNETR results |
| [AUDIT.md](AUDIT.md) | 15 faults in the procedures behind the reported results, with file:line evidence and fixes |
| [PROCEDURES.md](PROCEDURES.md) | Commands to regenerate everything, splits, output locations |
| [LITERATURE.md](LITERATURE.md) | Verified literature review (~110 sources), comparative methods, datasets, novelty ranking |

## 1. Reproduction — all reported numbers reproduce

| Stage | Reported | Reproduced |
|---|---|---|
| Radiomics calibrated LogReg-48 | Test AUC 0.8043, Brier 0.154 | Identical (same 30 test patients) |
| SWIN embeddings → fusion MLP | AUC 0.8006, acc 0.8095, F1 0.6522 | Identical with shipped weights (notebook model cell ran 3× → `MODEL_BUILD_INDEX = 2`) |
| Agent (patient 0019) | Fusion probs 0.4306 / 0.5782 | Identical; SHAP within noise; LLM text not run |

Caveats: default `main.py train` selects SVM-32 (AUC 0.7977), not the shipped model; fusion acc/F1 only reached on a lucky seed (unseeded, test-loss checkpointing).

## 2. Audit — key faults (details in AUDIT.md)

1. Agent "RANO bidimensional change" is computed from the radiomics score, not measurements.
2. Fusion selects its checkpoint on test loss; 0.48 cutoff hand-tuned; no seeds.
3. Fusion "improvement" is an operating-point shift — fusion AUC (0.8006) < radiomics alone (0.8043).
4. "SWIN UNETR" is a random, untrained encoder (embeddings carry ~no signal).
5. Also: possible test-split selection (seed 62), undocumented "not tested" molecular codes used as predictors, 59/97 censored never-progressor negatives, scan-level bootstrap CIs, wrong `LABEL_MAP`.

## 3. Rebuilt image branch — BraTS-pretrained SwinUNETR (`SWIN UNetR/`)

| Step | Result |
|---|---|
| Zero-shot on MU | WT Dice 0.85; confirmed MU labels 1=NETC, 2=SNFH, 3=ET, 4=RC |
| Stage 1: segmentation fine-tune (+ resection-cavity head) | Val mean Dice 0.495 → 0.697 |
| Stage 2: progression fine-tune (lesion-masked pooling) | Image-only AUC: OOF 0.59–0.60, test 0.64–0.65 |
| Late fusion with radiomics | 0.790–0.809 vs 0.8043 — no significant gain (patient-bootstrap CI spans 0) |

Lesson: global-average-pooled encoder features are ~identical across scans; lesion-masked pooling is required. Trained checkpoints were lost in the 2026-10-05 storage wipe and must be retrained (~1.5 h on 4 GPUs).

## 4. Literature — positioning (details in LITERATURE.md)

- The baseline paper already reports binary radiomics + calibration on MU-Glioma-Post (AUC 0.80) → matching it is not novel.
- No published forward, per-scan, censoring-aware progression model on MU-Glioma-Post, and none externally validated.
- Literature agrees with our results: deep image features add ≤ ~0.04 over clinical/radiomics at this scale; frozen encoders + simple heads and 2.5D slice encoders win at < 500 scans.
- BraTS 2024 contains ~400 Missouri cases → leakage risk for BraTS-2024-pretrained encoders.

### Ranked novelty directions

1. **Censoring-aware dynamic (landmark / discrete-time) prediction of 120-day progression** from serial post-op MRI, vs the naive binary label.
2. **Compartment-resolved + delta features incl. resection cavity** (radiomics and frozen-encoder tokens).
3. **External validation** on LUMIERE (± Burdenko, CFB-GBM).
4. **Leakage-free benchmark of frozen brain-MRI foundation encoders** for post-op progression.
5. **Label-definition sensitivity** (naive vs IPCW vs landmark; RANO 2.0 baseline).

Suggested framing: *dynamic, censoring-aware prediction of short-term progression from serial post-operative glioblastoma MRI using compartment-resolved features* (1 + 2 + 5, with 3 or 4), reported per TRIPOD+AI / CLAIM 2024 / METRICS.

## 5. Status & next steps

- Code restored after the storage wipe and committed; raw data, BraTS weights and reference manifests re-downloaded (git-ignored).
- To regenerate outputs: radiomics prep + training (~45 min CPU) → fusion inputs → embeddings → SwinUNETR fine-tuning (GPU). See PROCEDURES.md.
- Next: prototype direction 1 (landmark discrete-time model with patient-clustered nested CV and IPCW AUC(120 d)).
