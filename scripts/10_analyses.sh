#!/usr/bin/env bash
# Step 10: manuscript analyses on the final C3 / external / deep outputs (~30 min on 104 CPUs).
#   baselines (literature ladder + nested grid), schedule coupling, sensitivity, clinical utility, tables, split-variance replot.
#
#   scripts/10_analyses.sh                 all
#   scripts/10_analyses.sh utility tables  a subset, in the order given
#
# Writes outputs/results/analyses/<name>/.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_env
require_output results/c3/grade4/oof_repeats.csv.gz scripts/05_c3_radiomics.sh
require_output results/external_lumiere/locked_predictions.csv scripts/06_external_lumiere.sh

steps=("$@")
((${#steps[@]})) || steps=(baselines schedule sensitivity utility tables)
for s in "${steps[@]}"; do
  case "$s" in
    baselines) run_step baselines prism baselines --workers 32 ;;
    sensitivity) run_step sensitivity prism sensitivity --workers 48 ;;
    *) run_step "$s" prism "$s" ;;
  esac
done
run_step splitvar_replot prism splitvar --replot
