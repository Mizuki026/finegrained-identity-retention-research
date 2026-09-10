#!/usr/bin/env bash
set -euo pipefail

repo=/root/autodl-tmp/finegrained/research_pipeline
governance_dir="$repo/governance/mechanism_controlled_intervention_scientific_monolithic_run_002_v1"
runtime_output=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_monolithic/run_002
private_output=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_private_monolithic/run_002
log_dir=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_monolithic_logs
log_file="$log_dir/run_002.log"
pid_file="$log_dir/run_002.pid"

if [[ -e "$runtime_output" || -e "$runtime_output.partial" || -e "$private_output" ]]; then
  echo "BLOCKED: run-002 output, partial, or private directory already exists" >&2
  exit 2
fi
if [[ -e "$log_file" || -e "$pid_file" ]]; then
  echo "BLOCKED: run-002 log or PID file already exists" >&2
  exit 2
fi

mkdir -p "$log_dir"
cd "$repo"
nohup env \
  CUDA_VISIBLE_DEVICES=0 \
  WORLD_SIZE=1 \
  LOCAL_WORLD_SIZE=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  HF_HUB_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  HF_HUB_DISABLE_TELEMETRY=1 \
  TOKENIZERS_PARALLELISM=false \
  /root/autodl-tmp/consisid-smoketest/env/bin/python \
  src/run_controlled_lfe_projection_exchange_monolithic_v2.py \
  --mode execute-scientific \
  --authorization-file "$governance_dir/scientific_monolithic_run_002_execution_authorization_v1.json" \
  --output-dir "$runtime_output" \
  >"$log_file" 2>&1 &
pid=$!
printf '%s\n' "$pid" >"$pid_file"
echo "started PID=$pid"
echo "log=$log_file"
