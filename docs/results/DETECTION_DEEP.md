# Detection at the scan: deep arms G1–G5 (stream B, GPU)

Plan: [DETECTION_TASK.md](DETECTION_TASK.md), "Plan (pre-specified)" (git 2b4c927). The plan was snapshotted to
`outputs/results/analyses/finetune_detection/PLAN_snapshot.md` (23:13:12, git dd4812e) before the first real-label
job. Code: `prism/analyses/finetune_detection.py` (stage `finetune_det`). It reuses `finetune_deep.py` by import:
network, HP, cross-fit splits, seeds, augmentation, TTA prediction and runner design. That module is unchanged, so
the FINETUNE_DEEP.md results stay reproducible. This file holds stream B's results; the tabular arms (B0, B1, P, P+R,
I, LUMIERE) are in DETECTION_TASK.md.

## Implementation (what the plan left open, fixed before any real-label run)

- **Cohort, labels, folds**: only `outputs/data/detection_cohort.csv` (stream A). Grade 4: 313 scans / 126 patients
  (64 progression scans, 117 primary negatives, 132 secondary-only negatives). All patients are in `folds.csv`.
- **Training rows** (G1–G4, G1_all, G3_all): label_det = 1 or neg_primary. The splits are those of
  `finetune_deep.job_spec`, applied to these rows:
  - outer fold of the repeat;
  - 4 patient-grouped inner folds (`GroupKFold`);
  - early-stopping validation of 20% of patients (`StratifiedGroupKFold(5, shuffle)`, seed 10000 + 100r + 10k + j).
- **Scored rows**: every population scan in the outer test fold, including secondary-only negatives (`is_test = 1`),
  plus the inner held-out training rows (`is_test = 0`). The patient-overlap check between fit, val, holdout and test
  is asserted in every job.
- **Previous scan**: `prev_scan_id` of the cohort file. In code, it must be the same patient and strictly earlier
  (`days_from_prev > 0`); this is rule 5. Its crop uses the current scan's atlas box (MU is SRI24-registered). The
  226 previous-scan crops are in `outputs/features/finetune_cache/detection_prev/`. Where the pair is the same as in
  `finetune_deep`'s prev cache, they are bit-identical to it (checked on 39 pairs).
- The 73 progression scans were added to the shared cache with the same crop rule. Existing files were not rewritten.
- **G3 input**:
  - 8 channels: the current scan (4) plus (current − previous) × has_prev (4). Both scans are brain-z-scored as in
    `finetune_deep`, and the difference is taken after the same augmentation is applied to both. The difference is
    zero when there is no previous scan.
  - The has-previous flag is appended to the 2112 pooled features (head input 2113).
  - **Patch embedding**: the pretrained BraTS21 Conv3d(4→48) weights are copied for the 4 image channels. The 4
    difference channels get the same weights × 0.5, and the bias is unchanged. As in `finetune_deep`, the patch
    embedding and stages 1–2 stay frozen, so the difference-channel weights stay at 0.5 × pretrained.
- **G2**: `finetune_deep`'s siamese +prev network (head on [f_cur, f_cur − f_prev, has_prev]).
- **G4**: G1 with the training labels permuted among the outer-training rows (seed 1000r + k), as in
  `finetune_deep`'s perm arm.
- **G1_all, G3_all** (and, added later, G4_all, G2_all): the same on all gliomas (381 scans; 73 positives, 156
  primary negatives).
- **G5**: label_120 on the 249 grade-4 index scans. Population, folds and splits are exactly `finetune_deep`'s
  grade-4 arm; it uses G3's 8-channel network. It is stacked onto C2 (`phase_censoring.arm_design("C2")`,
  `audit.model.fit_pipeline`). The score is z-scored with its inner-OOF mean and SD on the verified outer-training
  scans. The models are trained on all grade-4 scans and evaluated in the intended use (RT started) with
  `evaluate_repeated` (IPCW AUC(120 d), reference C2, paired patient-cluster bootstrap, 1000 draws). The C2 column
  reproduces `phase_censoring/oof_grade4_full` (max deviation 1e-16).
- **Image-only AUC** (detection arms): the mean over repeats of the pooled held-out AUC of the mean logit of the 4
  inner networks, with a patient-cluster bootstrap (1000 draws; `diagnostics_imaging.boot_auc`).
- The stacked ΔAUC vs B1 and P uses stream A's helper (`python -m prism detection --deep-only`).

## How to run

```bash
OMP_NUM_THREADS=1 .venv/bin/python -m prism finetune_det cache --workers 40        # CPU, no labels (28 s)
CUDA_VISIBLE_DEVICES=0 .venv/bin/python -m prism finetune_det smoke --inputs cur diff siamese
.venv/bin/python -m prism finetune_det run --arms G1 G4 --gpus 0 1 2 3 --per-gpu 3  # resumable; rerun after interruption
.venv/bin/python -m prism finetune_det run --arms G3 G5 G2 --gpus 0 1 2 3 --per-gpu 2
.venv/bin/python -m prism finetune_det scores --arms G1 G4 G3 G5 G2               # -> detection/deep/<arm>/scores.csv
.venv/bin/python -m prism finetune_det evaluate                                   # image-only AUC, G4 validity, G5 rule 3
.venv/bin/python -m prism detection --deep-only                                   # stream A: stacking vs B1 / P
```

## Step 1–2 checks (no real labels)

- Smoke test (shuffled labels, 24 scans, 3 epochs, H100): two runs with the same seed gave bit-identical test logits
  for the cur, diff and siamese inputs. Step time and 8-flip TTA time:

  | Input | s per step | s per scan (TTA) |
  |---|---|---|
  | cur | 0.15 | 0.30 |
  | diff | 0.15 | 0.31 |
  | siamese | 0.29 | 0.50 |

  Outputs: `outputs/results/analyses/finetune_detection/smoke/`.
- Runner test (whole-population shuffled labels, half the training rows, 2–3 jobs, full grade-4 population on the
  GPU): peak allocated memory per process and GPU memory per card (nvidia-smi):

  | Input | Peak per process | Processes per GPU | Per card |
  |---|---|---|---|
  | cur | 20.4 GB | 3 | 71 GB |
  | diff | 26.1 GB | 2 | 58 GB |
  | siamese | 29.0 GB | 2 | 64 GB |

  Packing used: 3 processes per GPU for the cur arms, 2 for the diff and siamese arms, on GPUs 0–3 with
  `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
- Evaluation test on random synthetic logits placed in the real job splits: image-only AUC 0.49–0.50, C2 + noise − C2
  −0.003. The C2 reproduction holds.

## Results (2026-10-21/22)

**Run.** All 9 arms finished, 900 fine-tunes, on GPUs 0–3 from 23:13 to 04:29. That is 5.3 h of wall time, about
21 GPU-hours of the allocation, and 43 process-hours.
- Order: G1 + G4 (3 processes per GPU), G3 + G5, G2, G1_all, G3_all, G4_all, G2_all (2 processes per GPU).
- No job failed or ran out of memory.
- **Deviation (packing only, no effect on any number).** G1_all started at 3 processes per GPU, reached 76 GB per
  card, and was stopped after 19 finished jobs. The remaining 81 were rerun at 2 per GPU (about 51 GB). Jobs are
  deterministic and the runner skips finished jobs.
- **Deviation (added arms, labelled).** G4_all and G2_all were not named in the plan. The plan's priority order was
  applied to the "all gliomas last" population because time remained. Both are secondary.
- Per job: best epoch 3.3–5.4 on average (range 0–24), 9–11 epochs run, 1.9–5.1 min, peak allocated 20–36 GB.

Files:
- `outputs/results/analyses/detection/deep/<arm>/scores.csv` (scan_id, repeat, fold, inner, is_test, logit) and
  `jobs.csv`.
- Stream A's stacking (`python -m prism detection --deep-only`): `<arm>/{auc,contrasts,within_phase}.csv`,
  `summary_contrasts.csv`, and `G5/triage_eval.csv`.
- Own evaluation: `evaluation/{image_only_auc.csv, g5_triage.csv, g5_rule3.json, g5_oof_repeats.csv.gz,
  exploratory_within_fold_auc.csv}`.
- Logs: `outputs/results/analyses/finetune_detection/{orchestrator*.log, logs/}`.

**Detection arms.** Plain AUC [95% CI]: the mean over repeats of the pooled held-out AUC, with a patient-cluster
bootstrap of 1000 draws. Positives are progression scans and negatives are the primary negatives. The stacked Δ
values are paired and computed with stream A's helper (score z-scored with its inner OOF and appended to B1).

| Arm | Image-only, intended use | Image-only, all scans | B1 + arm − B1 (IU) | B1 + arm − P (IU) | B1 + arm − B1 (all) | B1 + arm − P (all) |
|---|---|---|---|---|---|---|
| G1 | 0.461 [0.389, 0.535] | 0.477 [0.416, 0.544] | −0.002 [−0.007, +0.002] | −0.017 [−0.063, +0.030] | −0.001 [−0.005, +0.002] | −0.016 [−0.052, +0.023] |
| G4 (perm.) | 0.483 [0.436, 0.527] | 0.471 [0.428, 0.516] | +0.003 [−0.003, +0.009] | −0.012 [−0.059, +0.034] | +0.003 [−0.002, +0.007] | −0.012 [−0.048, +0.025] |
| G3 | 0.447 [0.400, 0.489] | 0.464 [0.423, 0.507] | +0.003 [−0.002, +0.007] | −0.012 [−0.060, +0.035] | +0.003 [−0.001, +0.007] | −0.011 [−0.047, +0.026] |
| G2 | 0.514 [0.437, 0.593] | 0.527 [0.461, 0.597] | +0.001 [−0.003, +0.005] | −0.015 [−0.061, +0.032] | +0.002 [−0.002, +0.006] | −0.012 [−0.048, +0.026] |
| G1_all | 0.529 [0.449, 0.607] | 0.553 [0.483, 0.620] | −0.001 [−0.010, +0.008] | −0.037 [−0.084, +0.011] | −0.003 [−0.009, +0.004] | −0.044 [−0.082, −0.010] |
| G4_all (perm.) | 0.481 [0.436, 0.525] | 0.480 [0.445, 0.514] | +0.004 [−0.001, +0.009] | −0.032 [−0.081, +0.017] | +0.003 [−0.002, +0.008] | −0.038 [−0.078, −0.004] |
| G3_all | 0.507 [0.441, 0.579] | 0.533 [0.477, 0.593] | +0.001 [−0.006, +0.006] | −0.036 [−0.085, +0.014] | −0.001 [−0.004, +0.003] | −0.042 [−0.081, −0.008] |
| G2_all | 0.570 [0.491, 0.647] | 0.592 [0.519, 0.660] | +0.001 [−0.007, +0.008] | −0.036 [−0.085, +0.014] | −0.000 [−0.006, +0.006] | −0.041 [−0.080, −0.006] |

Grade-4 counts: intended use 62 positives / 84 negatives (80 patients); all scans 64 / 117 (92). All-glioma counts:
64 / 98 and 73 / 156. For reference (stream A):

| | B1 | P | I |
|---|---|---|---|
| Grade 4, intended use | 0.822 | 0.837 | 0.806 |
| Grade 4, all scans | 0.845 | 0.859 | 0.822 |
| All gliomas, intended use | 0.814 | 0.851 | 0.837 |

The image-only AUCs against the secondary negatives (all index scans) are in `image_only_auc.csv`: 0.449–0.532 in
the intended use. Within-phase and phase-stratified AUCs are in `<arm>/within_phase.csv` and `contrasts.csv`. In
the grade-4 intended use, the phase-stratified B1 + arm − B1 ranges from −0.002 to +0.009, and every CI includes 0.

**Rule 2 (an arm "adds" if its stack beats P by ≥ 0.03 with the CI excluding 0).** No arm adds. Every stack is
below P (grade-4 intended use −0.012 to −0.017), and each stack equals B1 within ±0.004. This is because the
stacking ridge gives the image score almost no weight.

**Rule 4 (validity: G4 image-only CI covers 0.5).**
- **Met.** G4 is 0.483 [0.436, 0.527] in the intended use and 0.471 [0.428, 0.516] overall. G4_all is 0.481
  [0.436, 0.525].
- The real-label arms are not distinguishable from the permuted control. In the intended use, G3's CI lies just
  below 0.5 (upper bound 0.489).

**Rule 3 (G5 triage retest).** IPCW AUC(120 d), grade-4 intended use (173 scans), trained on all grade-4 scans,
paired vs C2:

| Model | AUC [95% CI] | Δ vs C2 [95% CI] | Cal. slope | O/E |
|---|---|---|---|---|
| C2 (reproduced, max dev 1e-16) | 0.601 [0.515, 0.686] | — | 0.53 | 1.01 |
| **C2 + G5** | 0.608 [0.522, 0.693] | **+0.006 [−0.021, +0.034]** | 0.63 | 1.01 |
| G5 image only | 0.575 [0.478, 0.665] | −0.027 [−0.163, +0.107] | 0.54 | 1.10 |

- **Rule 3 FAILS**: +0.006 < 0.03, and the CI includes 0.
- Grade 4 overall: C2 + G5 − C2 is +0.006 [−0.013, +0.025]; G5 image only is 0.593.
- Stream A's independent stacking (`fd.stack_predict` onto C2, `G5/triage_eval.csv`) gives the same Δ, +0.006
  [−0.021, +0.034].
- For comparison, the 4-channel forward-label arm of FINETUNE_DEEP had image-only 0.644 and core + score +0.009
  (all grade-4 scans, against the core model, not C2). The subtraction channels do not change the picture.

**EXPLORATORY diagnostics** (added after the results; `evaluation/exploratory_within_fold_auc.csv`).

The pooled image-only AUCs below 0.5 (G1, G3) are not a sign error.
- The mean within-fold AUC is about 0.50 for every grade-4 arm except G2:

  | Arm | Intended use | Overall |
  |---|---|---|
  | G1 | 0.496 | 0.516 |
  | G3 | 0.492 | 0.522 |
  | G4 | 0.507 | 0.499 |
  | G2 | 0.574 | 0.596 |

- The pooled values are pulled below 0.5 by the cross-validation prevalence effect. The training-fold and test-fold
  prevalences correlate at r = −0.99 across the 25 outer splits, and the mean test logit follows the training
  prevalence (r = 0.29).
- The G1 score correlates with log ET volume (r = 0.54–0.56). ET volume alone has an AUC of 0.635 on the same rows,
  but the score's residual after ET is anti-informative (0.36).
- With about 87 training scans per fine-tune and early stopping at epoch 0–3 in most jobs, the networks learn
  little beyond a size-like direction and fold-specific noise.
- The siamese arms (G2, G2_all) are the only ones with a weak signal within folds (about 0.57–0.60). They still add
  nothing to B1.

**Verdict (stream B).**
- No deep arm adds to B1 or P for detection (rule 2).
- The permuted control is valid (rule 4).
- The image-only fine-tuned networks do not detect progression at the scan on MU-Glioma-Post at this sample size.
  They are at the level of the permuted control, whereas the tabular imaging measurements (I) alone reach 0.81.
- G5 does not rescue triage (rule 3 fails: +0.006 [−0.021, +0.034]).
- Nothing in the deep arms changes stream A's NO-GO for detection or triage on MU alone.
- Not run: no external (LUMIERE) test of the deep arms. It was optional, and the deep arms show no internal signal.
