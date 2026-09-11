#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp/finegrained/research_pipeline
export CUDA_VISIBLE_DEVICES=0
export WORLD_SIZE=1
export LOCAL_WORLD_SIZE=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
export TOKENIZERS_PARALLELISM=false
export PYTHONDONTWRITEBYTECODE=1
log_dir=/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_decode_monolithic_logs
if [[ -e "/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_decode_monolithic_logs/run_002.log" || -e "/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_decode_monolithic_logs/run_002.pid" ]]; then echo "BLOCKED: decode log or PID already exists" >&2; exit 2; fi
mkdir -p -m 0700 /root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_decode_monolithic_logs
nohup /root/autodl-tmp/consisid-smoketest/env/bin/python \
  src/run_controlled_lfe_private_decode_v1.py \
  --mode execute \
  --authorization-file governance/mechanism_controlled_intervention_scientific_monolithic_run_002_decode_v1/private_decode_execution_authorization_v1.json \
  > /root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_decode_monolithic_logs/run_002.log 2>&1 &
echo $! > /root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_decode_monolithic_logs/run_002.pid
echo "private decode started as PID $(</root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_decode_monolithic_logs/run_002.pid)"
