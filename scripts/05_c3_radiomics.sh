#!/usr/bin/env bash
# Step 5 (C3): does radiomics add to the clinical + timing + treatment baseline? 70 configurations + nested choice
# (~6 min per population on 104 CPUs). The PRISM report split head-to-head is step 7 (07_head_to_head.sh).
#
#   scripts/05_c3_radiomics.sh                 both populations
#   scripts/05_c3_radiomics.sh grade4          one population
#   EXTRA="--workers 48" scripts/05_c3_radiomics.sh
#
# Writes outputs/results/c3/<population>/.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_env
require_reference
require_output features/measurements.csv scripts/01_prepare_data.sh
require_output features/radiomics.csv scripts/02_radiomics.sh

for pop in $(populations "$@"); do
  run_step "c3_$pop" prism c3 --population "$pop" ${EXTRA:-}
done
