# Procedures

Commands run from the repo root unless noted. Environment: `uv sync` (Python 3.11, torch cu130, MONAI). Caches live under `/project/community/sbandred/cache` (set in `~/.bashrc`).

## 0. Data
```bash
uv run hf download sbandred/mu-glioma-post-raw --repo-type dataset --local-dir radiomics/PKG-MU-Glioma-Post
ln -s radiomics/PKG-MU-Glioma-Post mu-glioma-post-raw          # radiomics code requires data inside radiomics/
uv run hf download sbandred/mu-glioma-post-processed --repo-type dataset --local-dir reference-processed \
  --include 'manifests/**' 'postoperative_progression_surveillance/features/*'   # reference for comparison only
```

## 1. Radiomics (reproduction)
```bash
cd radiomics && uv run --project .. python main.py prep-data   # audit → split → preprocess → build index (~65 min)
uv run python reproduction/radiomics/parallel_prep.py           # optional: redo preprocess + build index in ~70 s
uv run python reproduction/radiomics/run_train.py               # main.py train flow, cached features, 96 workers (~26 min)
uv run python reproduction/make_fusion_inputs.py                # refit shipped LogReg-48 → fusion_inputs/
```
- `prep-data`'s preprocess step is single-core (~50 min); `parallel_prep.py` gives identical manifests.
- `run_train.py`: default search picks SVM-32 and the export step then fails (non-linear model); results are already written.
- `make_fusion_inputs.py` writes `reproduction/fusion_inputs/{train,test}_predictions.csv` (train = out-of-fold).

## 2. Original embeddings + fusion + agent (reproduction)
```bash
uv run python "SWIN UNetR/extract_embeddings.py" --output-dir "SWIN UNetR/embeddings_all"   # CPU, ~3 min
uv run python reproduction/run_fusion_seeds.py --inputs-dir reproduction/fusion_inputs \
  --output-dir reproduction/fusion_runs/reproduced_inputs                               # 50-seed retrain
uv run python reproduction/run_agent.py                                                 # reports + docx
```

## 3. Validation analyses
```bash
uv run python reproduction/validation/fusion_validation.py --embeddings-dir <dir> [--protocols ...]
uv run python reproduction/validation/linear_probe.py <embedding dirs...>
uv run python reproduction/validation/late_fusion_bootstrap.py <image_probs.csv ...>
```
- Fusion protocols: A test-loss checkpoint (original), B final epoch, C patient-grouped val checkpoint, D score only, E shuffled embeddings, F vision only; 50 seeds each.
- Late fusion: logistic regression on [radiomics score, image prob], fit on train only; patient-level bootstrap of ΔAUC.

## 4. BraTS SwinUNETR fine-tuning (`SWIN UNetR/`)
Weights: `fold1_f48_ep300_4gpu_dice0_9059` from MONAI research-contributions → `SWIN UNetR/pretrained/`.
Input order `[t2f, t1c, t1n, t2w]` (= BraTS flair, t1ce, t1, t2), per-channel nonzero z-score.
```bash
uv run python "SWIN UNetR/zero_shot_check.py"                                            # sanity check
uv run torchrun --standalone --nproc_per_node=4 "SWIN UNetR/finetune_seg.py" \
  --output-dir "SWIN UNetR/runs/seg" --epochs 60 --max-minutes 75                        # stage 1 (~45 min)
uv run python "SWIN UNetR/make_crops.py"                                                 # 144³ lesion crops + masks
bash "SWIN UNetR/run_stage2_lanes.sh" runs/progression2                                  # stage 2, 12 jobs (~35 min)
uv run python "SWIN UNetR/export_swin_embeddings.py" --source {pretrained|seg|stage2} --output-dir <dir>
```
- Splits: radiomics test patients (30) excluded everywhere; stage 1 val = 15% of remaining patients; stage 2 = 5 patient-grouped stratified folds on the 231 train scans + one full-train model for test.
- Stage 2: fixed 30 epochs (no early stopping), encoder LR 1e-5, head LR 1e-3, batch 8, one job per GPU (3/GPU OOMs).

## Outputs (git-ignored)
| Path | Contents |
|---|---|
| `radiomics/results/calibrated_forward_hybrid/` | Radiomics retrain |
| `SWIN UNetR/embeddings_all/` | Reproduced original embeddings |
| `SWIN UNetR/runs/seg/` | Stage-1 checkpoints (`best.pt`) |
| `SWIN UNetR/runs/progression2_{seg,pretrained}/` | Stage-2 fold/full models, predictions |
| `SWIN UNetR/runs/embeddings/` | Exported features for fusion |
| `reproduction/fusion_runs/`, `reproduction/validation/*.csv` | Fusion sweeps |
