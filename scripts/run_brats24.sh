#!/usr/bin/env bash
# S4: BraTS24_1 label maps for the plan's scope (docs/results/SEGMENTER_BRATS24_PLAN.md), cohorts in turn on 4 GPUs.
# Resumable: rerun the script and finished scans are skipped.
set -u
cd "$(dirname "$0")/.."
export PYTHONPATH=. PRISM_SKIP_UCSF=0
# Node-local disk (container copies brats24_1_g0..g3 and the work folders); set both before running.
: "${PRISM_ENROOT_DATA:?set PRISM_ENROOT_DATA to the folder holding brats24_1_g0..g3}"
: "${PRISM_BRATS24_WORK:?set PRISM_BRATS24_WORK to a node-local work folder}"
export PRISM_ENROOT_DATA PRISM_BRATS24_WORK
for c in ucsf mu lumiere; do
  echo "== $c $(date)"
  .venv/bin/python -m prism.features.reseg_brats24 --cohort $c --gpus 4 --tag full_$c \
      --ids-file outputs/features/seg_brats24/ids_$c.txt --skip-done
  echo "== $c exit $? $(date)"
done
