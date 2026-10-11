#!/usr/bin/env bash
# Step 9 (optional): frozen deep-encoder (SwinUNETR) features vs the C3 baseline.
#
# The GPU feature extraction is manual and NOT run here (needs the legacy env with torch, a GPU and the encoder
# weights in $PRISM_DATA/weights; see docs/results/DEEP_FEATURES.md):
#   CUDA_VISIBLE_DEVICES=0 uv run --frozen --no-sync python -m prism.features.deep --cohort mu lumiere
# This script runs only the CPU analysis on the extracted features and skips cleanly if they are missing.
#
#   scripts/09_deep_features.sh
#   EXTRA="--workers 24 --population grade4" scripts/09_deep_features.sh
#
# Writes outputs/results/analyses/deep/.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_env
require_output features/measurements.csv scripts/01_prepare_data.sh

if ! compgen -G "$PRISM_OUTPUTS/features/deep_*.parquet" >/dev/null; then
  echo "== skipping deep: no outputs/features/deep_*.parquet (run the GPU extraction first, see header)"
  exit 0
fi
run_step deep prism deep ${EXTRA:-}
