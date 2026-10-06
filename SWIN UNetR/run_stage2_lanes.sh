#!/usr/bin/env bash
# Stage 2 (both inits): 12 jobs as 4 GPU lanes x 3 sequential jobs (one job per GPU fits in memory).
#   bash "SWIN UNetR/run_stage2_lanes.sh" <output-prefix>   -> <prefix>_seg/, <prefix>_pretrained/
set -uo pipefail
cd "$(dirname "$0")"
PREFIX="$1"
PY="../.venv/bin/python"
mkdir -p "${PREFIX}_seg" "${PREFIX}_pretrained"
lane() {
  local gpu=$1; shift
  for spec in "$@"; do
    init=${spec%%:*}; fold=${spec##*:}
    out="${PREFIX}_${init}"
    "$PY" finetune_progression.py --fold "$fold" --init "$init" --output-dir "$out" --device "cuda:$gpu" > "$out/log_$fold.txt" 2>&1
    echo "$(date +%T) gpu$gpu done $init fold $fold: $(grep -h pred_auc "$out/log_$fold.txt" || echo FAILED)"
  done
}
lane 0 seg:0 seg:4    pretrained:2 &
lane 1 seg:1 seg:full pretrained:3 &
lane 2 seg:2 pretrained:0 pretrained:4 &
lane 3 seg:3 pretrained:1 pretrained:full &
wait
echo exit=0
