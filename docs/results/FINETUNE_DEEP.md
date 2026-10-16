# Fine-tuned SwinUNETR encoder for the 120-day label (nested in the shared 5×5 folds)

**Status: plan and code only (step 1, 2026-10-15).** No fine-tuned model has been trained or scored against real
outcome labels. Code: `prism/analyses/finetune_deep.py` (stage `finetune`). The frozen-encoder results that this
extends are in [DEEP_FEATURES.md](DEEP_FEATURES.md).

## Analysis plan (pre-specified)

Written before any fine-tuned network saw a real label. Before the first real-label run, this section will be copied to
`outputs/results/analyses/finetune/PLAN_snapshot.md`. Anything added after results are seen is labelled EXPLORATORY.

**Question.** The paper evaluated only frozen SwinUNETR encoders: the nested D1 arm gave ΔAUC −0.004 [−0.069, +0.063]
for grade 4. Does fine-tuning the encoder on the 120-day label produce an image score that adds to the core model? The
core model is ridge on clinical + timing + as-of-scan treatment: 0.698 (grade 4) and 0.720 (all gliomas).

**A. Task and label.**
- Label: `label_120`, documented progression ≤ 120 d after the scan, with death censored.
- Scans censored before 120 d (label NaN) are excluded from the training loss. This is the "verified" formulation, the
  same one the core ridge uses, so the image score and the stack are trained on the same rows.
- We chose exclusion over IPCW weights for this reason: IPCW weights would make the network and the ridge disagree on
  the training target.
- Censored scans are still scored and enter the IPCW AUC(120 d), as in every other analysis.
- Populations: grade 4 primary (249 scans / 126 patients), all gliomas secondary (308 / 155).

**B. Splits (no outer-test information can leak).**
- Outer: the shared folds (`outputs/data/folds.csv`), 5 repeats × 5 folds.
- Inside each outer training set T, the verified scans T_ver are split into 4 patient-grouped inner folds with
  `GroupKFold(4)`. This is exactly the split that c3's stacking uses.
- For each inner fold j, a network is fine-tuned on T_ver minus fold j. It predicts fold j (its inner out-of-fold score)
  and the outer test fold.
- Early stopping uses a validation split of 20% of patients (`StratifiedGroupKFold(5, shuffle)`, first fold), drawn
  only from T_ver minus fold j. Neither fold j nor the outer test fold influences training or stopping.
- This gives 4 fine-tunes per outer split and 100 per arm.
- Leakage checks are run in the unit test (`<scratchpad>/ft/test_eval.py`). For every job, patients do not overlap
  between fit, val, holdout and test.

**C. Scores and stacking ("cross-fit bagging").**
- Outer-test image score: the mean of the 4 inner networks' logits.
- The training-side out-of-fold score and the test score come from the same 4 networks, so their scales match without a
  5th fit on all of T.
- Stack:
  - The score is z-scored with the mean and SD of its inner OOF values on T_ver.
  - It is appended to the core features (`c3.BASE_PRE`).
  - The core ridge (`formulations.fit`, "verified", C chosen by inner patient-grouped CV) is refitted on T_ver and
    predicts the outer test fold.
- Image-only arm: the sigmoid of the averaged logit. This is a ranking score, and its calibration is reported but not
  expected to be good.

**D. Network.** All hyperparameters are fixed here (`HP` in the code). None are tuned, and there is no choice among
settings.
- Architecture: MONAI SwinUNETR `swinViT` (feature size 48; 4 channels FLAIR/T1c/T1/T2). The decoder is discarded.
- Starting weights: BraTS 2021 (primary) or BrainSegFounder (secondary arm), the same files as
  `prism.features.deep`.
- Input:
  - The brain is z-scored as in `prism.features.deep`.
  - A cube is centred on the bounding box of the lesion + resection cavity, with side = max(128, extent + 16) mm.
  - Cubes larger than 128 are resampled to 128³; this applies to 37 of the 308 cohort scans
    (`outputs/features/finetune_cache/meta.csv`).
- Mask-guided pooling:
  - Mask-weighted means of stages 2, 3 and 4 within the lesion (ET ∪ NETC ∪ SNFH; every cohort scan has more than 30
    lesion voxels), plus the global mean of stage 4.
  - This gives 2112 features → LayerNorm → Dropout(0.3) → Linear(1).
- Partial unfreezing: the patch embedding and stages 1–2 are frozen and run without gradients. Stages 3–4 and the head
  are trained.
- Optimisation:
  - AdamW: encoder lr 2e-5, head lr 1e-3, weight decay 0.01.
  - Schedule: 1 warm-up epoch, then cosine over 25 epochs.
  - Batch 4, bf16 autocast, BCE loss.
- Early stopping on validation BCE: patience 5, at least 3 epochs, and the best epoch is restored.
- Augmentation: random flips (3 axes), translation ±8 voxels, and a per-channel intensity scale of 0.9–1.1 and shift
  of ±0.1 inside the brain.
- Prediction: mean logit over 8 flip test-time augmentations.
- Seeds are fixed per job (10000 + 100r + 10k + j). The cuDNN and torch deterministic flags are on.

**E. Arms.** They are run in this order, and each arm has 100 fine-tunes.

| # | Arm | Role |
|---|---|---|
| 1 | `brats21:grade4:real` | **PRIMARY** |
| 2 | `brats21:grade4:perm` | Control. The pipeline is identical, but the verified labels are permuted among the T_ver scans of each outer training set (one permutation per outer split, seed 1000r + k). The stacking ridge uses the real labels, so this arm shows what an uninformative fine-tuned score does to the stack. |
| 3 | `brats21:all_glioma:real` | Secondary population |
| 4 | `bsf:grade4:real` | Secondary encoder (BrainSegFounder) |
| 5 | `brats21+prev:grade4:real` | OPTIONAL secondary: change from the previous scan (below). Run only if arms 1–4 finish within the budget. |

**Change from the previous scan (arm 5): feasible, secondary.**
- MU volumes are SRI24-registered (240×240×155, 1 mm). The previous scan's brain-mask Dice with the current scan was
  0.97 in a spot check, so the patient's previous complete scan can be cropped at the same atlas box.
- 153 of the 308 cohort scans have a prior scan.
- Network: a siamese encoder with shared weights. The head takes [f_cur, f_cur − f_prev, has_prev], with f_prev = f_cur
  when there is no prior scan.
- Its cost is about twice that of arm 1.

**F. Evaluation (CPU).**
- `metrics.evaluate_repeated`:
  - Headline: the mean over repeats of the per-repeat pooled-OOF IPCW AUC(120 d).
  - Paired patient-cluster bootstrap, 1000 draws.
  - Reference: the core ridge, recomputed with `c3.fit_predict` on the same folds. It must reproduce 0.698 / 0.720.
- Reported per population:
  - Image-only fine-tuned AUC.
  - Core + fine-tuned score vs core: ΔAUC and 95% CI.
  - Calibration of every arm: slope, O/E and IPCW Brier.
  - Permuted-label control: image-only and stacked.
- The frozen reference is the NESTED_D1 OOF predictions from DEEP_FEATURES.md
  (`outputs/results/analyses/deep/<population>/oof_repeats.csv.gz`), placed in the same paired bootstrap.
- Diagnostics:
  - Best epochs, run time and memory per job (`jobs.csv`).
  - Correlation of the image score with log lesion volume and with the core logit (`diagnostics.csv`).

**G. Pre-specified rule.**
- Fine-tuning **helps** if, for grade 4 and arm 1, core + fine-tuned score beats core by ΔAUC ≥ 0.03 with the paired
  95% CI excluding 0. Otherwise it does not help.
- All other arms and populations are secondary, with no multiplicity correction.
- Validity check: the permuted-label control must give an image-only AUC of about 0.5 (CI covering 0.5) and a stack
  ΔAUC ≤ 0. If it does not, the run is flagged as invalid and is not interpreted.
- Minimal detectable effect: MDE = 2.8 × SE(ΔAUC), for 80% power at two-sided 5%, with SE = CI width / 3.92 from the
  bootstrap (column `mde_80` in `results.csv`).
  - Prior expectation from the frozen arms (DEEP_FEATURES.md): SE ≈ 0.034 for nested D1 grade 4, giving MDE ≈ 0.09.
  - SE ≈ 0.020 for DV, giving MDE ≈ 0.056.
  - So only an effect of roughly +0.06 to +0.09 is reliably detectable. A "does not help" result therefore rules out
    large gains, not small ones.

**H. Not done.** No external LUMIERE test (that would need a locked refit on all of MU; out of scope). No IPCW-weighted
loss (see A). No hyperparameter search.

## How to run

```bash
# 0. image cache (CPU, no labels; done in step 1: 308 scans + 153 prior scans, 27 s with 30 workers, 5.8 GB on disk, gitignored)
OMP_NUM_THREADS=1 .venv/bin/python -m prism finetune cache --workers 30
# 1. smoke test on shuffled labels (done in step 1)
CUDA_VISIBLE_DEVICES=1 .venv/bin/python -m prism finetune smoke --n 24 --epochs 3 --encoders brats21 bsf
# 2. fine-tunes: arms 1-4 on GPUs 1-3, 3 processes per GPU; resumable (rerun the same command after an interruption)
.venv/bin/python -m prism finetune run --gpus 1 2 3 --per-gpu 3
#    optional arm 5 afterwards (more memory per process)
.venv/bin/python -m prism finetune run --arms brats21+prev:grade4:real --gpus 1 2 3 --per-gpu 2
# 3. evaluation (CPU)
OMP_NUM_THREADS=1 .venv/bin/python -m prism finetune evaluate [--arms ... --population grade4 all_glioma]
```

Outputs:
- `outputs/results/analyses/finetune/jobs/<arm>/r{r}_k{k}_j{j}.npz`: per-job logits plus history.
- `logs/worker_gpu*.log`.
- `<population>/{results.csv, jobs.csv, diagnostics.csv, oof_repeats.csv.gz}`.
- The runner claims each job with an atomic lock file, skips finished jobs, and clears stale locks at start. Every job
  writes its result atomically, so the job is the checkpoint unit (a job takes about 2 min).
- Only the GPUs listed in `--gpus` are used: each worker gets its own `CUDA_VISIBLE_DEVICES`. GPU 0 is not used.
- No new packages were needed. The shared `.venv` already has torch 2.14.0+cu130 and MONAI 1.6.1.

## Step 1 checks (no real labels used)

- **Cache** (`outputs/features/finetune_cache/meta.csv`):
  - All 308 cohort scans were cached, with 153 prior-scan crops.
  - 37 scans were resampled (side > 128).
  - The pooling mask is the lesion for all 308.
- **Smoke test** (`outputs/results/analyses/finetune/smoke/smoke.json` holds the last run, n = 130; the n = 24 run
  printed the numbers below). Labels were a random permutation and were never evaluated. H100, GPU 1.
  - Determinism: two runs with the same seed gave bit-identical test logits (max |Δ| = 0.0) for brats21 and bsf.
  - Speed: 0.12–0.15 s per training step (batch 4, including the per-epoch validation pass) and 0.30 s per scan for
    8-flip TTA. The +prev arm takes 0.24–0.29 s per step and 0.48 s per scan.
  - Memory (peak allocated, including the cached cohort on the GPU): 16.6 GB with 130 scans and 19 GB with the full
    grade-4 cohort; 25–32 GB for +prev.
- **Runner test**: a test-only label mode `shuf` (whole-cohort permutation, 1/4 of the training rows, first 3 jobs) was
  run on GPUs 1–3, outputs in the scratchpad.
  - Jobs took 0.3–0.8 min. A rerun skipped all finished jobs (resume works).
  - The early-stopping validation loss is noisy on small validation sets (4–8 scans in the test). In the real runs the
    sets have about 20–25 scans.
- **Evaluation unit test** (`<scratchpad>/ft/test_eval.py`). It uses outcomes shuffled across rows and synthetic job
  scores, not the real outcomes.
  - Patients are disjoint across fit, val, holdout and test for every job.
  - Every OOF entry is filled.
  - A synthetic informative score is picked up (stack ΔAUC +0.32).
  - A synthetic noise score gives image-only 0.50 and stack ΔAUC 0.000.

**Compute estimate.**
- Grade 4: one fine-tune trains on about 100 scans (26 steps per epoch, at most 25 epochs, so at most 80 s), plus
  about 30 s of TTA prediction on about 90 scans and about 10 s of setup. That is roughly 1.5–2.5 min on a dedicated
  GPU; all gliomas is about 20% more.
- Arms 1–4: 400 fine-tunes, about 800 GPU-minutes. With 9 processes on 3 GPUs (contention assumed to halve
  per-process speed), this is about **2–3.5 h of wall time**.
- Optional arm 5: 100 fine-tunes at about twice the cost, about 1–1.5 h more with 6 processes.
- CPU: the evaluation takes a few minutes. Memory: about 20 GB of GPU memory per process.

## Results

Not run yet (waiting for GO).
