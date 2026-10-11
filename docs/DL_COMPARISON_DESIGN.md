# Deep-learning / "diffusion" comparison: feasibility and design (2026-10-11)

Question from the user: *would comparing "diffusion models" to the current radiomics give us a better chance?*
There are two readings, and they have different answers.

| Reading | Feasible on our data? | Verdict |
|---|---|---|
| **A. Diffusion-weighted / perfusion MRI** (DWI/ADC, DSC/ASL), the route to AUC ~0.9 in the literature | **No.** Neither MU-Glioma-Post nor LUMIERE has any DWI, ADC or perfusion series | Limitation + future work. It would need a different cohort, a different endpoint and a new study |
| **B. Deep models on the conventional MRI we have**, including generative diffusion models used as frozen feature extractors | **Yes.** Data are already preprocessed, GPUs are free, and two pretrained encoders were smoke-tested | Worth **one** pre-registered, frozen-encoder arm (about half a day of GPU time). Expect a null result. A fine-tuned CNN is optional and low priority |

---

## A. Diffusion-weighted and perfusion MRI

### What we have (checked on disk)

**MU-Glioma-Post** (`data/mu-glioma-post/MU-Glioma-Post/PatientID_*/Timepoint_*/`):
- File suffixes over all 203 patient folders: `brain_t1c` 596, `brain_t1n` 596, `brain_t2f` 596, `brain_t2w` 596, `tumorMask` 594.
- That is 4 structural sequences only. No DWI, ADC, DTI, DSC, DCE or ASL file exists anywhere in the tree.

**LUMIERE** (`/project/community/sbandred/lumiere/`):
- `LUMIERE-MRinfo.csv` lists the sequences CT1 632, T1 617, T2 626 and FLAIR 612. Nothing else.
- The archive `Imaging-v202211.zip` holds `CT1/T1/T2/FLAIR.nii.gz` plus DeepBraTumIA and HD-GLIO-AUTO derivatives. Again, no diffusion or perfusion.

**Count of scans with DWI/ADC/perfusion: 0 in MU and 0 in LUMIERE.**

### Why the ~0.9 numbers do not transfer to our task

- **Different task.** The AUC ~0.90–0.94 studies classify the *current* enhancing lesion as true progression or pseudoprogression/radiation necrosis, usually with pathology or follow-up adjudication. Examples are Kim 2019 *Neuro-Oncol* (multiparametric 0.90 vs conventional 0.76) and Li 2026 *Cancers* (0.935 with RSI/ADC/CBF). See `docs/literature/comparison.md`, rows at lines ~76, 135 and 138.
- **Our endpoint is forward risk.** We predict documented progression within 120 days of a surveillance scan. The same Li 2026 model scores ≈ chance (0.514) on a forward survival task.
- **Conclusion.** Perfusion and diffusion help state classification. There is no evidence of comparable gains for forward risk.

### Public cohorts that do have diffusion/perfusion

| Cohort | Content | Labels relevant to us | Access | Effort |
|---|---|---|---|---|
| **UCSD-PTGBM** (Sci Data 2026, doi 10.1038/s41597-025-06499-z) | 178 patients / 243 post-treatment timepoints, 3 T. T1/T1c/T2/FLAIR + multishell diffusion (RSI, 4 b-values) + DSC (leakage-corrected CBV) + ASL. Registered 1 mm 256³, expert masks | 45 pathology-proven recurrences vs treatment effect; OS/PFS for 94 patients. Mostly one timepoint per patient, so **no dated follow-up for a 120-d label** | TCIA, CC BY 4.0, no DUA | Download ~1 day. A recurrence-vs-treatment-effect study is a *new* paper, not a comparison inside ours |
| **Burdenko GBM Progression** (TCIA) | 180 patients, RT planning MRI + CT + RT dose; 1–8 follow-ups with **2–4 structural sequences (minimum T1c + FLAIR)** | Progression / pseudoprogression / response for a subset | TCIA, open | **No routine DWI/perfusion** (structural only), so it does not answer reading A. It is a good *second external* cohort for reading B, and it has RT dose |
| **UCSF-ALPTDG** | 298 patients × 2 consecutive post-treatment timepoints, T1/T1c/T2/FLAIR, ET/SNFH/NETC/RC masks + change annotations | Change labels, clinical history | UCSF IDSC, non-commercial **DUA** | Diffusion/perfusion are not part of the released set (as far as the descriptions state; unverified). DUA turnaround is days to weeks |
| TCIA Brain-Tumor-Progression (Schmainda) | 20 patients × 2 timepoints, ADC + DSC (nCBF, nRCBV, sRCBV) + structural | Progression timepoint only | TCIA, open | Too small for modelling; illustration only |

**Recommendation for A:**
- Report it as a limitation: conventional-MRI-only data, and perfusion/diffusion is the established route to state-classification gains.
- If the team wants a diffusion/perfusion paper, UCSD-PTGBM is the only open, sizeable option. It supports a *recurrence vs treatment-effect* task, not our 120-d forward endpoint.
- Do not attempt it in the manuscript week.

---

## B. Deep models on our conventional MRI

### Infrastructure (checked)

**GPUs**
- `nvidia-smi` shows 4 × H100 80 GB, all idle at the time of writing.
- The brief says 3; use one GPU (`CUDA_VISIBLE_DEVICES=0`) per job.

**Software**
- The shared `.venv` has no torch.
- A separate env built with `UV_PROJECT_ENVIRONMENT=<scratchpad>/venv-dl uv sync --frozen --extra legacy` gives torch 2.14.0+cu130, MONAI 1.6.1 and CUDA OK.
- The shared `.venv` was not touched.

**MU images**
- BraTS-style preprocessing: co-registered, skull-stripped, 1 mm isotropic, 240×240×155 (SRI24 grid, LPS).
- Masks are labelled 1 = NETC, 2 = SNFH, 3 = ET, 4 = RC (`prism/config.py`). RC is present in 220/253 grade-4 scans (`outputs/data/mu_cohort.csv`, `label4_voxels > 0`).

**LUMIERE images**
- DeepBraTumIA atlas space: skull-stripped, 1 mm, 182×218×182 (MNI), all 4 sequences.
- Segmentation labels: Necrotic/NonEnhancing, Enhancing, Edema (`measured_volumes_in_mm3.json`).
- There is **no resection-cavity label**: DeepBraTumIA calls the cavity "necrosis" (see `docs/results/EXTERNAL_LUMIERE.md`).
- The extracted folder `imaging/Imaging/` holds DeepBraTumIA outputs for 125 timepoints. The other cohort scans must be read from `Imaging-v202211.zip`, as `legacy/shipped_on_lumiere.py` already does.

### Legacy deep-learning code (what exists and what was wrong)

**`legacy/swin_unetr/extract_embeddings.py` and `legacy/mlp_fusion/fusion_mlp.py`: the PRISM report pipeline**
- The "Swin UNETR" is a generic `nn.TransformerEncoder` with **random weights** (build index 2 after seed 42).
- It has no shifted windows, no pretraining and no fine-tuning (`docs/PUBLICATION_PLAN.md` A2.1).
- The embeddings carry no signal: about 0.50 alone in the fusion MLP and a 0.55 / 0.62 linear probe. PC1 tracks lesion/cavity size (reproduction notes).

**The later legacy code is a genuine MONAI SwinUNETR with BraTS21 weights**
- Files: `swin_common.py`, `zero_shot_check.py`, `finetune_seg.py`, `finetune_progression.py`, `export_swin_embeddings.py`.
- Weights: `legacy/swin_unetr/pretrained/fold1_.../` is **empty**. They were re-downloaded for this check (below).
- Fixed bug: global-average-pooled features are near-identical across scans (corr ~1). Lesion-masked multi-scale pooling is needed.
- Earlier results were obtained **on the PRISM report split, naive labels, no clinical baseline**, so they are only indicative (`legacy/reproduction/FINDINGS.md`):
  - Frozen lesion-pooled linear probe: 0.59 train-CV / 0.63 test.
  - Fine-tuned progression head: image-only OOF 0.59–0.60, test 0.64–0.65.
  - Late fusion with radiomics: Δ −0.014 / +0.005, CIs spanning 0.

### Candidate pretrained encoders (weights and licences verified 2026-10-11)

| Encoder | Architecture / input | Pretraining data | Weights | Licence | MU leakage risk | Fit |
|---|---|---|---|---|---|---|
| **MONAI BraTS21 SwinUNETR** (fold1_f48) | SwinUNETR, 4-ch (FLAIR, T1c, T1, T2), 96³ patches, 62 M params | BraTS 2021 (pre-operative) | GitHub release `MONAI-extra-test-data/0.8.1`, 231 MB, ungated | Apache-2.0 | Low (MU entered BraTS in 2024) | **Primary.** Smoke-tested |
| **BrainSegFounder** BRATS-finetune (+ UKB/BRATS SSL checkpoints) | Same SwinUNETR, 4-ch; SSL checkpoints are 2-ch SwinViT | UK Biobank 41k (SSL) → BraTS 1,470 | HF `smilelab/BrainSegFounder`, ungated, 5 checkpoints | "uk-biobank-mta" (UKB Material Transfer Agreement; academic use; check redistribution of derived weights) | Low (BraTS 2021-size set) | **Co-primary.** Smoke-tested |
| BrainIAC (Nat Neurosci 2026) | ViT, single sequence, 96³ (per our plan; README does not state) | Large multi-cohort brain MRI | Dropbox link, ungated | Non-commercial academic (Mass General Brigham) | Unknown; check whether UPENN-GBM/BraTS 2024 were used | Secondary: T1c and FLAIR embedded separately and concatenated |
| BrainMVP (CVPR 2025) | UniFormer / UNet, multi-modal | BrainMVP-16k (3,755 patients) | Google Drive | **No licence file** in repo | Check whether BraTS 2023/24 is inside the 16k set | Optional only |
| SAM-Med3D | ViT, 1-ch, 128³, promptable segmentation | SA-Med3D-140K (multi-organ, multi-modal) | HF | Apache-2.0 | Possible (BraTS in pool) | Weak fit (segmentation prompts, not brain-specific) |
| MedicalNet, Models Genesis | 3D ResNet / UNet | Mostly CT | GitHub | NOASSERTION | — | Avoid except as weak baselines |
| **Generative diffusion as feature extractor:** MONAI `brats_mri_generative_diffusion` (3D LDM) | VAE + latent DDPM UNet, 1-ch | BraTS 2016/17 Decathlon, 388 volumes, FLAIR-like | MONAI model zoo | Apache-2.0 | Low | Toy-scale ("demonstration network" per its README). Not defensible as a primary encoder |
| **Generative diffusion:** NVIDIA NV-Generate-MR-Brain (MAISI v2 rectified-flow LDM, 240 M) | 3D latent diffusion UNet; modalities T1, FLAIR, T2, SWI (**no T1c**) | MR-RATE (Forithmus) | HF `nvidia/NV-Generate-MR-Brain`, ungated | NVIDIA Open Model License (commercial use allowed) | Unknown | Exploratory: noised-latent UNet activations at small t. Not validated for discriminative use in 3D brain MRI (only arXiv-level evidence, e.g. DDPM-UKB linear probes, D-Cube) |

**Diffusion-feature verdict:**
- "Diffusion-model features" are not an established 3D brain-MRI discriminative representation.
- The available brain LDMs are either toy-scale (BraTS LDM) or lack T1c (NV-Generate-MR-Brain).
- Use one only as a clearly labelled exploratory arm, after the SwinUNETR arms, and only if time remains.

### Smoke test (done, GPU 0 only)

Script: `<scratchpad>/smoke_encoders.py`. It is ephemeral; move it into `prism/features/deep.py` when implementing.

Setup:
- Scan: MU `PatientID_0003/Timepoint_1`, channels (FLAIR, T1c, T1, T2), z-scored within brain.
- Inference: sliding window 96³, bf16.

| Encoder | Load | Zero-shot Dice TC / WT / ET vs MU mask | Time / peak memory |
|---|---|---|---|
| MONAI BraTS21 SwinUNETR | strict, 0 missing / 0 unexpected keys | 0.935 / 0.903 / 0.906 | 1.5 s / 11.1 GB |
| BrainSegFounder BRATS-finetune | strict, 0 missing / 0 unexpected keys | 0.937 / 0.970 / 0.889 | 1.1 s / 11.4 GB |

Both encoders understand MU geometry and contrast. Stage feature maps on a 224×224×144 crop are 48 / 96 / 192 / 384 / 768 channels, which gives 1,488-d per lesion-masked pooling region.

Extraction cost for all 314 MU + 132 LUMIERE scans × 2 encoders × 4 compartments is minutes, not days.

### Sample-size realism

Counts:
- Grade 4: 253 scans / 128 patients. 228 have a 120-d label: **92 positive / 136 negative**, 25 censored (`outputs/data/mu_cohort.csv`).
- All gliomas: 277 labelled (99 / 178).
- LUMIERE: 132 scans / 61 patients, 47 / 77 / 8 censored.

What that means:
- A training fold holds ~180 scans from ~100 patients with ~70 events.
- **Fine-tuning a 62 M-parameter 3D network end-to-end on ~70 events is not credible as a headline.** The legacy attempt reached image-only OOF 0.59–0.60.
- **A frozen encoder plus a linear model on a stacked score is the only setup** whose variance is comparable to the C3 radiomics arms.
- Detectable effect: C3 nested ΔAUC CIs are ~0.07 wide (grade 4 [−0.046, +0.026]). Under the identical protocol a deep arm would need **ΔAUC ≳ +0.04** to exclude 0.
- Nothing in the literature or in our legacy probes suggests an image-only forward-risk signal that large on top of clinical + treatment + timing.

### Design (pre-specify before running; mirrors C3 exactly)

**Labels, folds and metrics**
- Same verified/IPCW 120-d labels (`prism/models/formulations.py`).
- Same 5×5 patient-grouped folds (`outputs/data/folds.csv`, `load_folds`).
- Same IPCW AUC(120 d), paired ΔAUC vs the ridge baseline with patient-cluster bootstrap (1,000), and the same permutation control.
- Populations: grade 4 (primary) and all gliomas.

**Arm D1: frozen pretrained encoder (primary)**
1. **Inputs:**
   - MU 4-channel 1 mm volumes, z-scored within brain (`brain_*` != 0).
   - LUMIERE: DeepBraTumIA atlas `*_skull_strip` CT1/FLAIR/T1/T2, same normalisation.
2. **Features:**
   - Encoder: `swinViT` hidden stages 1–4 (the 768-d bottleneck is optional) over a lesion-centred crop of ≥128³ (whole brain is also fine, as above).
   - **Mask-weighted mean pooling** per region, at feature-map resolution: (i) whole lesion (ET ∪ NETC ∪ SNFH), (ii) ET, (iii) SNFH, (iv) 5 mm peri-cavity rim, as in C3.
   - **Do not use RC/NETC compartments for LUMIERE transport**: the cavity is unlabelled there.
   - Add **test-time flips (8×)**, averaged.
   - Output: `outputs/features/deep_{encoder}.csv`, one row per scan_id.
3. **In-fold reduction:** z-score → PCA-10 / PCA-30 / top-10 univariate F / L1 logistic. These are the same selectors as C3, all fitted on training folds only.
4. **Integration:** **stacked score** (inner patient-grouped OOF logistic on deep features → one score added to the baseline ridge). This is the C3 winner. Concatenation is secondary.
5. **Configurations:** 2 encoders (BraTS21, BrainSegFounder) × 2 pooling sets (lesion-only, compartments) × 4 selectors × 2 integrations = 32. Report a **nested choice** over all 32 as the honest estimate, as in C3.

**Arm D0: random-init control (mandatory)**
- The same SwinUNETR architecture with random weights, through the identical pipeline.
- Pretraining is credited only if D1 beats D0.
- This also directly tests the PRISM report's random encoder.

**Arm D1b: deep + radiomics**
- One stacked score built from radiomics (legacy top-10) + deep features.
- Answers whether either imaging channel adds beyond the other.

**Arm D2: small fine-tuned 3D model (optional upper bound, run only if D1 is positive or time remains)**
- **Model:** BrainSegFounder/BraTS21 encoder + lesion-pooled linear head.
- **Training:** discrete-time hazard or IPCW-weighted BCE; freeze stages 0–2, LR 1e-5 encoder / 1e-3 head; 30 epochs; flips/intensity augmentation.
- **Model selection:** early stopping on an *inner* patient-grouped split (never on the test fold).
- **Output:** OOF image score → stacked into the baseline as in D1.
- **Cost:** ~180 scans × 30 epochs at 128³ ≈ 10–15 min per fold on one H100 → 25 folds ≈ 5–6 h per configuration. Two inits = one GPU-day.

**Arm D3: exploratory diffusion features (optional, clearly labelled exploratory)**
- Model: NV-Generate-MR-Brain (or the MONAI BraTS LDM).
- Encode FLAIR (and T1 as a T1c proxy) to latents, add noise at t ∈ {50, 100, 200}, take mid-UNet activations, pool within the lesion (downsampled mask), then the same pipeline as D1.
- Results are not part of the primary claim.

**External test (locked)**
- The best D1 configuration is fixed by MU nested CV, refit on all MU, and applied unchanged to LUMIERE.
- Shared features (no treatment features), as in `prism/experiments/external_lumiere.py`.
- Report the raw score and recalibrated O/E.
- Domain-shift caveat: SRI24 vs MNI grid, different segmenters, no RC label.

**Explanation hygiene**
- Report the correlation of the deep score with log lesion volume and with the baseline score.
- The legacy embeddings' PC1 tracked size, so the deep arm must be shown to add beyond the volume features in `outputs/features/measurements.csv`. Add a volume-adjusted variant: baseline + volumes ± deep score.

### Compute budget

| Step | GPU time | Wall |
|---|---|---|
| Implement `prism/features/deep.py` + `prism/experiments/c4_deep.py` (reuse `c3_radiomics.fit_predict`, `run_nested`) | — | ~0.5 day |
| D0 + D1 extraction (3 encoders incl. random, 446 scans, 8× TTA) | < 1 h, 1 GPU | — |
| D1/D1b CV + nested + bootstrap (CPU, same as C3) | — | ~2–4 h on 16 CPUs |
| LUMIERE locked test | minutes | — |
| D2 fine-tuning (optional) | ~1 GPU-day | 1 day |
| D3 diffusion features (optional) | ~2 h | 0.5 day |

The core (D0, D1, D1b, locked LUMIERE) fits in **~1 day of work and < 1 GPU-hour**. With D2 and D3 it is 2–3 days.

### Recommendation

1. **Reading A: not feasible.** We hold zero diffusion/perfusion scans. State this as a limitation. If wanted, propose UCSD-PTGBM (CC BY 4.0) for a separate recurrence-vs-treatment-effect study.
2. **Reading B: do D0 + D1 (+ D1b) first.**
   - It is cheap, it uses the exact C3 protocol, and it closes the obvious reviewer question: "radiomics adds nothing, but did you try deep features?"
   - It corrects the PRISM report's random-encoder claim with a pretrained-vs-random comparison.
3. **Expected outcome: a null or small (≤ +0.03) ΔAUC.**
   - Basis: the legacy BraTS21 probes (0.59–0.65 image-only) and 70/70 null radiomics configurations.
   - A null with a pretrained-vs-random control and a locked external test is still a stronger, more complete paper.
   - It is **not** a "better chance" of a positive imaging result. That honest framing should go to the user.
4. **D2 (fine-tuning)** only if D1 shows ΔAUC CI lower bound > −0.01. **D3 (diffusion-model features)** only as a labelled exploratory supplement; do not headline it.
5. **Burdenko GBM Progression** (open, T1c + FLAIR follow-ups, RT dose) is the best candidate for a second external test of any imaging arm. That is next-phase work.
