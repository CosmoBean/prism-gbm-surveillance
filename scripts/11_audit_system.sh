#!/usr/bin/env bash
# Step 11: auditable decision-support layer on the clinical + timing + treatment ridge baseline
# (locked model + model card, per-scan audit records, conformal / selective prediction, referral rules,
#  shortcut / subgroup / LUMIERE-transport audit, explanation stability, MANIFEST.json). ~10 min on 24 CPUs.
# Plan and results: docs/results/AUDIT_SYSTEM.md. Writes outputs/results/analyses/audit_system/.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_env
require_output results/c3/grade4/oof_repeats.csv.gz scripts/05_c3_radiomics.sh
require_output results/c3/all_glioma/oof_repeats.csv.gz scripts/05_c3_radiomics.sh
require_output results/analyses/utility/calibration.csv scripts/10_analyses.sh

export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
run_step audit_system prism audit --workers "${AUDIT_WORKERS:-24}" ${EXTRA:-}
