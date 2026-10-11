#!/usr/bin/env bash
# Run the whole pipeline in order: data -> radiomics -> c1 -> c2 -> c3 -> external -> head2head -> splitvar -> deep.
#
#   scripts/run_all.sh                    everything (radiomics extraction is the slow part)
#   scripts/run_all.sh --skip-radiomics   reuse outputs/features/radiomics.csv from an earlier run
#   scripts/run_all.sh --from c2          start at a later step (data | radiomics | c1 | c2 | c3 | external |
#                                         head2head | splitvar | deep)
#   scripts/run_all.sh --to external      stop after a step
# The deep step only analyses already extracted deep features (GPU extraction is manual; see 09_deep_features.sh).
#
# Each step logs to outputs/logs/<step>.log; the run stops at the first failure.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
here="$REPO/scripts"

skip_radiomics=0
from=data
to=deep
while (($#)); do
  case "$1" in
    --skip-radiomics) skip_radiomics=1 ;;
    --from) from="$2"; shift ;;
    --to) to="$2"; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) die "unknown option $1" ;;
  esac
  shift
done

steps=(data radiomics c1 c2 c3 external head2head splitvar deep)
declare -A script=([data]=01_prepare_data.sh [radiomics]=02_radiomics.sh [c1]=03_c1_endpoint.sh
                   [c2]=04_c2_feature_search.sh [c3]=05_c3_radiomics.sh [external]=06_external_lumiere.sh
                   [head2head]=07_head_to_head.sh [splitvar]=08_split_variance.sh [deep]=09_deep_features.sh)
[[ -n "${script[$from]:-}" ]] || die "--from must be one of: ${steps[*]}"
[[ -n "${script[$to]:-}" ]] || die "--to must be one of: ${steps[*]}"

start=$SECONDS
started=0
for s in "${steps[@]}"; do
  [[ "$s" == "$from" ]] && started=1
  ((started)) || continue
  if [[ "$s" == radiomics && $skip_radiomics == 1 ]]; then
    echo "== skipping radiomics"
    continue
  fi
  echo
  echo "######## $s"
  bash "$here/${script[$s]}"
  [[ "$s" == "$to" ]] && break
done
echo
echo "== pipeline finished in $(((SECONDS - start) / 60)) min; results in ${PRISM_OUTPUTS#$REPO/}/results"
