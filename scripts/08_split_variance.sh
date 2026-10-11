#!/usr/bin/env bash
# Step 8: split variance - where does the PRISM report split's AUC sit among 500 random splits of the same design?
# CPU-bound; uses the legacy radiomics code under legacy/radiomics (importable from the base environment).
#
#   scripts/08_split_variance.sh
#   EXTRA="--workers 22 --n-splits 500" scripts/08_split_variance.sh
#
# Writes outputs/results/analyses/split_variance/.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_env
require_reference
require_output features/measurements.csv scripts/01_prepare_data.sh

run_step splitvar prism splitvar ${EXTRA:-}
