#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp/finegrained/research_pipeline
pid_file=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_decode_monolithic_logs/run_002.pid
log_file=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_decode_monolithic_logs/run_002.log
if [[ -f "$pid_file" ]]; then
  pid=$(<"$pid_file")
  if kill -0 "$pid" 2>/dev/null; then state=RUNNING; else state=NOT_RUNNING; fi
else
  pid=NONE
  state=NOT_STARTED
fi
completed=0
if [[ -f "$log_file" ]]; then
  completed=$(grep -c '^PRIVATE_DECODE_COMPLETE ' "$log_file" || true)
fi
echo "state=$state pid=$pid completed=$completed/480"
if [[ -f "$log_file" ]]; then tail -n 5 "$log_file"; fi
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
