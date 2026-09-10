#!/usr/bin/env bash
set -euo pipefail

log_dir=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_monolithic_logs
log_file="$log_dir/run_002.log"
pid_file="$log_dir/run_002.pid"
private_output=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_private_monolithic/run_002
runtime_output=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_monolithic/run_002

if [[ -f "$pid_file" ]]; then
  pid=$(<"$pid_file")
  ps -p "$pid" -o pid=,etime=,stat=,%cpu=,%mem=,cmd= || true
else
  echo "PID file absent"
fi
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader
if [[ -d "$private_output" ]]; then
  find "$private_output" -maxdepth 1 -type f -name '*.safetensors' | wc -l
else
  echo "0"
fi
if [[ -d "$runtime_output" ]]; then
  echo "scalar runtime finalized: $runtime_output"
elif [[ -d "$runtime_output.partial" ]]; then
  echo "scalar staging exists: $runtime_output.partial"
else
  echo "scalar runtime not finalized"
fi
if [[ -f "$log_file" ]]; then
  tail -n 40 "$log_file"
else
  echo "log file absent"
fi
