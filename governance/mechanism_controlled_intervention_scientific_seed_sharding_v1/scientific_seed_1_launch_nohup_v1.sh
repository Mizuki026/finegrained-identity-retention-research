#!/bin/bash
set -eu
umask 077
monitor=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_monitor/seed_1
command=/root/autodl-tmp/finegrained/research_pipeline/governance/mechanism_controlled_intervention_scientific_seed_sharding_v1/scientific_seed_1_terminal_command_v1.sh
scalar=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_shards/seed_1
private=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_private_shards/seed_1
if [ -e "$monitor" ] || [ -e "$scalar" ] || [ -e "$scalar.partial" ] || [ -e "$private" ]; then
  echo "BLOCKED: Seed 1 monitor or output state already exists; do not retry or resume." >&2
  exit 2
fi
install -d -m 0700 "$monitor"
nohup "$command" >"$monitor/console.log" 2>&1 </dev/null &
pid=$!
printf '%s
' "$pid" >"$monitor/pid"
sleep 2
if ! kill -0 "$pid" 2>/dev/null; then
  echo "BLOCKED: Seed 1 process exited during launch; inspect $monitor/console.log" >&2
  tail -n 40 "$monitor/console.log" >&2 || true
  exit 2
fi
echo "Seed 1 launched with PID $pid"
echo "Monitor log: $monitor/console.log"
