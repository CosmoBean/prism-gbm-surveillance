# Scripts

Run from anywhere; each script `cd`s to the repository root. Every step writes a log to `outputs/logs/<step>.log` and
stops with a clear message if an input is missing.

## 1. Environment

```bash
scripts/setup_env.sh            # uv (installed if missing) + Python 3.11 + .venv from uv.lock, import check, unit tests
scripts/setup_env.sh --legacy   # also legacy/ dependencies (torch, MONAI, LightGBM, SHAP, ...)
scripts/setup_env.sh --all      # legacy + notebook extras
```

`uv sync` is exact: running without `--legacy` removes legacy packages from an existing `.venv`.

## 2. Pipeline steps

| Script | Step | Needs | Time (measured, 104 CPUs) |
|---|---|---|---|
| `01_prepare_data.sh [--reference]` | MU cohort + folds, LUMIERE cohort, measurements. `--reference` first downloads the original PRISM radiomics from Hugging Face | MU-Glioma-Post, LUMIERE CSVs | 1 min |
| `02_radiomics.sh` | corrected PyRadiomics features | step 1 | slow (CPU-bound) |
| `03_c1_endpoint.sh` | C1: naive vs censoring-aware formulations | step 1, reference features | 1 min |
| `04_c2_feature_search.sh [grade4\|all_glioma]` | C2: feature-group search (126 configs), nested selection over ridge + boosting, 100 patient-level label permutations of the nested pipeline | step 1, reference features | see note below |
| `05_c3_radiomics.sh [grade4\|all_glioma]` | C3: radiomics vs clinical + timing + treatment baseline | steps 1–2, reference features | ~6 min / population |
| `06_external_lumiere.sh [--shipped]` | train on MU, test on LUMIERE (all arms scored per fold on identical LUMIERE folds); `--shipped` also runs the PRISM report radiomics model and its adaptation (needs `--legacy` env and the LUMIERE imaging zip) | step 1 | a few min |
| `07_head_to_head.sh` | C3 pipelines vs the PRISM report radiomics model on the PRISM report split (+ masking-only ablation) | steps 1–2 | ~1 min |
| `08_split_variance.sh` | the PRISM report split's AUC among 500 random splits of the same design | step 1, reference features | CPU-bound |
| `09_deep_features.sh` | optional: deep-encoder features vs the C3 baseline; analysis only — the GPU extraction (`python -m prism.features.deep`) is manual, the step is skipped when no `outputs/features/deep_*.parquet` exist | GPU features | |
| `10_analyses.sh [step ...]` | manuscript analyses: literature baselines + nested grid, schedule coupling, sensitivity, calibration/decision curves/NRI/sample size, Table 1 + flow, split-variance replot | steps 5–9 | ~30 min |
| `run_all.sh [--skip-radiomics] [--from STEP] [--to STEP]` | all of the above in order | | |

C2 cost is dominated by the permutation control: 100 permutations x 25 outer folds x 126 candidate configurations
(~35 s CPU per outer fold), i.e. ~25 CPU-hours per population. `EXTRA="--n-permutations 20"` or
`EXTRA="--perm-learners ridge"` (permute the ridge-only nested pipeline, about half the cost) for a quicker run.

All stages are run as `uv run --frozen --no-sync python -m prism <stage>` from the repository root (see `common.sh`),
so they work whether or not the `prism` console script is installed in the environment.

c2 and c3 run both populations unless one is given. Extra options go through `EXTRA`, e.g.
`EXTRA="--workers 32" scripts/04_c2_feature_search.sh grade4`; c1 and radiomics take options directly.

## Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `PRISM_DATA` / `PRISM_MU` / `PRISM_LUMIERE` | `data/`, `data/mu-glioma-post`, `data/lumiere` | input locations |
| `PRISM_OUTPUTS` | `outputs/` | where everything is written |
| `PRISM_WORKERS` | all CPUs | processes for image stages |
| `BLAS_THREADS` | 4 | numpy/scikit-learn threads per process |
| `UV_PROJECT_ENVIRONMENT` | `.venv` | use a different environment directory |

## On the cluster

Run heavy steps on a compute node, not the login node — e.g. inside an interactive allocation:

```bash
squeue -u $USER                                   # find your job id
srun --jobid=<id> --overlap -N1 -n1 --cpus-per-task=104 scripts/run_all.sh --skip-radiomics
```
