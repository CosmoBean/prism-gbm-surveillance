#!/usr/bin/env bash
# Step 1: MU index + cohort + folds, LUMIERE cohort, image measurements (~1 min on 100 CPUs).
#
#   scripts/01_prepare_data.sh               uses data already under data/
#   scripts/01_prepare_data.sh --reference   first download the original PRISM radiomics (needed by c1, c2, c3)
#
# Writes outputs/data/{mu_index,mu_cohort,mu_flow,folds,lumiere_cohort}.csv and outputs/features/measurements.csv.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_env

if [[ "${1:-}" == "--reference" ]]; then
  if [[ -e "$REFERENCE_FEATURES" ]]; then
    echo "== reference features already present"
  else
    run_step download_reference uvx --from huggingface_hub hf download sbandred/mu-glioma-post-processed \
      --repo-type dataset --local-dir "$PRISM_DATA/mu-reference-processed"
  fi
fi

require_mu
require_lumiere
[[ -e "$REFERENCE_FEATURES" ]] || echo "NOTE: original PRISM radiomics not found - c1, c2, c3 will need --reference"

run_step mu prism mu
run_step lumiere prism lumiere
run_step measurements prism measurements
