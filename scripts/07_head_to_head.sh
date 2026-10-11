#!/usr/bin/env bash
# Step 7: C3 pipelines vs the PRISM report radiomics model on the PRISM report split (127 train / 30 test patients,
# all gliomas), plus the "masking only" ablation without the early-post-RT x MGMT flag (~1 min).
#
#   scripts/07_head_to_head.sh
#
# Writes outputs/results/c3/prism_report_split/{head_to_head.csv, head_to_head_masking_only.csv}.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_env
require_reference
require_file "$REPO/legacy/radiomics/models/calibrated/test_predictions.csv" "PRISM report test predictions (in git)"
require_output features/radiomics.csv scripts/02_radiomics.sh

run_step head2head prism head2head ${EXTRA:-}
run_step head2head_masking_only prism head2head --drop-mgmt-flag ${EXTRA:-}
