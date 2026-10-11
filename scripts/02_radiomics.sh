#!/usr/bin/env bash
# Step 2: corrected compartment-wise PyRadiomics features (slow; only c3 needs them).
#
#   scripts/02_radiomics.sh [--workers N]
#
# Writes outputs/features/radiomics.csv and outputs/features/radiomics_eroded.csv.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_env
require_mu
require_output data/mu_cohort.csv scripts/01_prepare_data.sh

BLAS_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  run_step radiomics prism radiomics "$@"
