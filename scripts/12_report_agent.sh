#!/usr/bin/env bash
# Step 12: clinician report written only from the per-scan audit record + faithfulness evaluation.
# Builds report records for every grade-4 out-of-fold scan (CV repeat 0), generates summaries with a local LLM
# (vLLM, Qwen3.8-27B / Qwen3.5-9B, greedy; separate env, no external API), checks them deterministically and renders
# reports and the Fig 5A candidates. Needs 4 GPUs (~15 min) and the LLM env:
#   uv venv $PRISM_LLM_ENV --python 3.12 && VIRTUAL_ENV=$PRISM_LLM_ENV uv pip install vllm==0.31.0
# Plan and results: docs/results/REPORT_AGENT.md. Writes outputs/results/analyses/report_agent/.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_env
require_output results/analyses/audit_system/cv_predictions_grade4.csv.gz scripts/11_audit_system.sh
export PRISM_LLM_ENV="${PRISM_LLM_ENV:-/project/community/sbandred/envs/prism-llm}"
[[ -x "$PRISM_LLM_ENV/bin/python" ]] || die "no LLM env at $PRISM_LLM_ENV (see the header of this script)"

run_step report_agent prism report --steps records requests generate evaluate render figures --sets eval stress
