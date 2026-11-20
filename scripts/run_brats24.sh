#!/usr/bin/env bash
# S4: BraTS24_1 label maps for the plan's scope (docs/results/SEGMENTER_BRATS24_PLAN.md), cohorts in turn on 4 GPUs.
# LUMIERE runs in four chunks; each finished chunk is kept if the allocation ends. Several nodes may run this script
# at once: a node claims a chunk by creating outputs/features/seg_brats24/claims/<chunk> (mkdir is atomic on NFS).
# COHORTS (default "ucsf mu lumiere") chooses which cohorts this node runs.
# Resumable: rerun the script and finished scans are skipped.
set -u
cd "$(dirname "$0")/.."
export PYTHONPATH=. PRISM_SKIP_UCSF=0
# Node-local disk (container copies brats24_1_g0..g3 and the work folders); set both before running.
: "${PRISM_ENROOT_DATA:?set PRISM_ENROOT_DATA to the folder holding brats24_1_g0..g3}"
: "${PRISM_BRATS24_WORK:?set PRISM_BRATS24_WORK to a node-local work folder}"
export PRISM_ENROOT_DATA PRISM_BRATS24_WORK
run() {  # cohort tag ids-file
  echo "== $1 $2 $(date)"
  .venv/bin/python -m prism.features.reseg_brats24 --cohort $1 --gpus 4 --tag $2 --ids-file $3 --skip-done
  echo "== $1 $2 exit $? $(date)"
}
COHORTS=${COHORTS:-"ucsf mu lumiere"}
mkdir -p outputs/features/seg_brats24/claims
for c in $COHORTS; do
  if [ $c != lumiere ]; then run $c full_$c outputs/features/seg_brats24/ids_$c.txt; continue; fi
  for f in outputs/features/seg_brats24/ids_lumiere_[0-9][0-9].txt; do
    k=$(basename $f .txt)
    mkdir outputs/features/seg_brats24/claims/$k 2>/dev/null || { echo "== $k claimed elsewhere"; continue; }
    echo "$(hostname) $(date)" > outputs/features/seg_brats24/claims/$k/by
    run lumiere chunk_$k $f
  done
done
