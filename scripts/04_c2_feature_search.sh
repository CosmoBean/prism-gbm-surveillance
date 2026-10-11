#!/usr/bin/env bash
# Step 4 (C2): feature-group search, nested selection (ridge + boosting) and a patient-level label-permutation control
# (100 permutations of the nested pipeline: ~25 CPU-hours per population, ~15 min on 104 CPUs; see scripts/README.md).
#
#   scripts/04_c2_feature_search.sh                    both populations
#   scripts/04_c2_feature_search.sh grade4             one population
#   EXTRA="--workers 32" scripts/04_c2_feature_search.sh
#
# Writes outputs/results/c2/<population>/.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_env
require_reference
require_output features/measurements.csv scripts/01_prepare_data.sh

for pop in $(populations "$@"); do
  run_step "c2_$pop" prism c2 --population "$pop" ${EXTRA:-}
done
