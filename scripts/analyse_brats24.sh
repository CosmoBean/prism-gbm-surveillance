#!/usr/bin/env bash
# S4 analysis (docs/results/SEGMENTER_BRATS24_PLAN.md), CPU only, one command:
#   1. measurement tables for every cohort whose BraTS24 scope (seg_brats24/ids_<cohort>.txt) is fully segmented
#      (existing tables are kept; incomplete cohorts are skipped and reported);
#   2. P1-P4, the exploratory 22-input run and calibration (MU required), written to
#      outputs/results/analyses/segmenter_brats24/; the compact summary is printed at the end.
# Usage: scripts/analyse_brats24.sh [--n-boot N]     (default 2000; CPUs: PRISM_CPUS, default 36)
set -euo pipefail
cd "$(dirname "$0")/.."
CPUS=${PRISM_CPUS:-36}
export PYTHONPATH=. OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PRISM_SKIP_UCSF=0
unset PRISM_MEASUREMENTS
OUT=outputs/results/analyses/segmenter_brats24
mkdir -p "$OUT"
LOG=$OUT/analyse_$(date +%Y%m%d_%H%M).log
echo "log: $LOG"
{
  echo "== measurement tables $(date)"
  .venv/bin/python -m prism.features.seg_measurements --segmenter brats24 --complete-only --workers "$CPUS"
  echo "== analysis $(date)"
  .venv/bin/python -m prism.analyses.segmenter_stage --segmenter brats24 --workers $(( CPUS < 25 ? CPUS : 25 )) "$@"
  echo "== finished $(date)"
} 2>&1 | tee "$LOG"
