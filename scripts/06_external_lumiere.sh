#!/usr/bin/env bash
# Step 6: train on MU, test on LUMIERE - locked, recalibrated, fine-tuned and LUMIERE-only arms (all arms scored per fold on identical LUMIERE folds).
#
#   scripts/06_external_lumiere.sh             shared-feature models
#   scripts/06_external_lumiere.sh --shipped   also the PRISM report radiomics model on LUMIERE + its adaptation
#                                              (legacy code; needs scripts/setup_env.sh --legacy and the LUMIERE imaging zip)
#
# Writes outputs/results/external_lumiere/.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_env
require_output data/lumiere_cohort.csv scripts/01_prepare_data.sh
require_output features/measurements.csv scripts/01_prepare_data.sh

run_step external prism external

if [[ "${1:-}" == "--shipped" ]]; then
  require_file "$PRISM_LUMIERE/Imaging-v202211.zip" "LUMIERE imaging archive from figshare"
  run_step external_shipped py legacy/shipped_on_lumiere.py
fi
