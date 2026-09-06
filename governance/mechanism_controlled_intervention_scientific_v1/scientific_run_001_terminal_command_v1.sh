#!/bin/bash
set -eu
umask 077
cd /root/autodl-tmp/finegrained/research_pipeline
exec env \
  CUDA_VISIBLE_DEVICES=0 \
  WORLD_SIZE=1 \
  LOCAL_WORLD_SIZE=1 \
  HF_HUB_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  HF_HUB_DISABLE_TELEMETRY=1 \
  TOKENIZERS_PARALLELISM=false \
  PYTHONDONTWRITEBYTECODE=1 \
  /root/autodl-tmp/consisid-smoketest/env/bin/python \
  src/run_controlled_lfe_projection_exchange_v1.py \
  --mode execute-scientific \
  --authorization-file governance/mechanism_controlled_intervention_scientific_v1/scientific_run_001_execution_authorization_v1.json \
  --output-dir /root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific/run_001
