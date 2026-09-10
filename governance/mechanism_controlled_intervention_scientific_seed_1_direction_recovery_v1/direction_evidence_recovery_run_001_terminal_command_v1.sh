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
  src/run_controlled_lfe_direction_evidence_recovery_v1.py \
  --authorization-file governance/mechanism_controlled_intervention_scientific_seed_1_direction_recovery_v1/direction_evidence_recovery_run_001_authorization_v1.json \
  --output-dir /root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_direction_recovery/seed_1_run_001
