#!/usr/bin/env bash
# Step 3 (C1): naive vs censoring-aware outcome formulations (~1 min).
#
#   scripts/03_c1_endpoint.sh [--n-boot 1000] [--workers 12]
#
# Writes outputs/results/c1/.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_env
require_reference
require_output features/measurements.csv scripts/01_prepare_data.sh

run_step c1 prism c1 "$@"
