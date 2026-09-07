#!/bin/bash
set -u
monitor=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_monitor/seed_1
scalar=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_shards/seed_1
private=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_private_shards/seed_1
printf 'UTC: '; date -u '+%Y-%m-%dT%H:%M:%SZ'
if [ -r "$monitor/pid" ]; then
  pid=$(sed -n '1p' "$monitor/pid")
  if kill -0 "$pid" 2>/dev/null; then
    echo "PROCESS: RUNNING pid=$pid"
    ps -p "$pid" -o pid=,etime=,%cpu=,%mem=,cmd=
  else
    echo "PROCESS: NOT_RUNNING recorded_pid=$pid"
  fi
else
  echo "PROCESS: NOT_LAUNCHED_OR_NO_PID_FILE"
fi
if [ -d "$private" ]; then
  count=$(find "$private" -maxdepth 1 -type f -name '*.safetensors' | wc -l)
  bytes=$(find "$private" -maxdepth 1 -type f -name '*.safetensors' -printf '%s
' | awk '{sum += $1} END {print sum + 0}')
  echo "PRIVATE_LATENTS: $count/120 files, $bytes bytes"
else
  echo "PRIVATE_LATENTS: 0/120 files (acquisition may still be running, or not launched)"
fi
if [ -f "$scalar/execution_summary_v1.json" ]; then
  echo "SCALAR_OUTPUT: COMPLETE_PENDING_INDEPENDENT_PHASE_VERIFICATION"
else
  echo "SCALAR_OUTPUT: NOT_FINALIZED"
fi
echo "GPU:"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader
echo "LAST_LOG_LINES:"
if [ -f "$monitor/console.log" ]; then tail -n 20 "$monitor/console.log"; else echo '(no console log)'; fi
