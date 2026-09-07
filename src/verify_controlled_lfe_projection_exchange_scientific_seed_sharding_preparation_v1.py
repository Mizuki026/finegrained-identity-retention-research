#!/usr/bin/env python3
"""CPU-only verifier for prospective four-seed-shard preparation; grants no execution authority."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import controlled_lfe_projection_exchange_protocol_v1 as protocol
import controlled_lfe_projection_exchange_runtime_v1 as runtime

REPO = Path(__file__).resolve().parents[1]
GOV = REPO / "governance/mechanism_controlled_intervention_scientific_seed_sharding_v1"
AMENDMENT_STATUS = "PROSPECTIVE_FOUR_SEED_SHARD_PROTOCOL_AMENDMENT_CPU_PREPARATION_AUTHORIZED_ONLY"
SUPERSESSION_STATUS = "SUPERSEDED_NEVER_EXECUTED_MONOLITHIC_SCIENTIFIC_RUN_001_NOT_REUSABLE"


class SeedShardingPreparationVerificationError(RuntimeError):
    """Raised when preparation is incomplete, active, or design-drifting."""


def read_json(name: str) -> dict:
    return json.loads((GOV / name).read_text(encoding="utf-8"))


def verify_preparation() -> dict:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise SeedShardingPreparationVerificationError("preparation verifier must be CUDA-hidden and torch-free")
    auth = read_json("researcher_seed_sharding_amendment_authorization_v1.json")
    prereg = read_json("prospective_four_seed_shard_preregistration_v1.json")
    supersession = read_json("monolithic_scientific_run_001_supersession_v1.json")
    if auth.get("status") != AMENDMENT_STATUS or auth.get("gpu_execution_authorized") is not False:
        raise SeedShardingPreparationVerificationError("amendment authority drift")
    if prereg.get("condition_sharding") != "REJECTED" or prereg.get("seed_complete_sharding") != "ACCEPTED":
        raise SeedShardingPreparationVerificationError("seed/condition sharding decision drift")
    if supersession.get("status") != SUPERSESSION_STATUS or supersession.get("prior_scientific_execution_started") is not False:
        raise SeedShardingPreparationVerificationError("monolithic supersession drift")
    for item in supersession.get("superseded_artifacts", {}).values():
        protocol.bound(item, "superseded monolithic artifact")
    with (GOV / "scientific_seed_shard_preparation_matrix_v1.csv").open(newline="", encoding="utf-8") as handle:
        matrix = list(csv.DictReader(handle))
    if len(matrix) != 4:
        raise SeedShardingPreparationVerificationError("shard preparation matrix must contain exactly four rows")
    combined = []
    for seed_index, row in enumerate(matrix, 1):
        expected_id = f"seed_{seed_index}"
        rows = runtime._phase_rows("scientific", seed_index)
        if (
            row.get("scientific_shard_id") != expected_id
            or int(row.get("scientific_seed_index", 0)) != seed_index
            or int(row.get("scientific_seed", 0)) != protocol.SEEDS[seed_index - 1]
            or int(row.get("trajectories", 0)) != 120
            or int(row.get("scheduler_steps", 0)) != 6000
            or row.get("conditions") != "baseline|target_projection_exchange|orthogonal_sham"
            or row.get("preparation_status") != "PREPARED_REQUIRES_SEPARATE_GPU_AUTHORIZATION"
            or row.get("gpu_execution_authorized") != "False"
            or len(rows) != 120
        ):
            raise SeedShardingPreparationVerificationError(f"shard preparation drift: {expected_id}")
        combined.extend(rows)
        scalar = Path(row["runtime_output_dir"])
        private = Path(row["private_latent_output_dir"])
        if scalar.exists() or scalar.with_name(scalar.name + ".partial").exists() or private.exists():
            raise SeedShardingPreparationVerificationError(f"shard output already exists: {expected_id}")
    combined_keys = {(row["planned_task_id"], row["condition"]) for row in combined}
    expected_keys = {(row["planned_task_id"], row["condition"]) for row in protocol.execution_plan()}
    if combined_keys != expected_keys or len(combined) != 480:
        raise SeedShardingPreparationVerificationError("four shards do not reconstruct the exact frozen plan")
    old_scalar = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific/run_001")
    old_private = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_private/run_001")
    if old_scalar.exists() or old_scalar.with_name(old_scalar.name + ".partial").exists() or old_private.exists():
        raise SeedShardingPreparationVerificationError("superseded monolithic transaction has runtime state")
    active_files = list(GOV.glob("scientific_seed_*_execution_authorization_v1.json"))
    if active_files:
        raise SeedShardingPreparationVerificationError("active shard execution authorization exists during preparation-only phase")
    private_parent = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_private_shards")
    if not private_parent.is_dir() or private_parent.stat().st_mode & 0o777 != 0o700:
        raise SeedShardingPreparationVerificationError("private shard parent missing or not mode 0700")
    if "torch" in sys.modules:
        raise SeedShardingPreparationVerificationError("preparation verification imported torch")
    return {
        "schema_version": 1,
        "status": "PASS_PROSPECTIVE_FOUR_SEED_SHARD_CPU_ONLY_PREPARATION_VERIFICATION",
        "seed_complete_shards": 4, "trajectories_per_shard": 120,
        "scheduler_steps_per_shard": 6000, "combined_trajectories": 480,
        "combined_scheduler_steps": 24000, "all_three_conditions_per_shard": True,
        "condition_sharding_rejected": True, "monolithic_run_001_superseded": True,
        "monolithic_execution_started": False, "active_shard_gpu_authorizations": 0,
        "shard_runtime_roots_absent": True, "shard_private_roots_absent": True,
        "torch_imported": False, "model_or_weights_loaded": False, "reference_accessed": False,
        "outcome_accessed": False, "gpu_used": False, "trajectory_executed": False,
        "decode_performed": False, "network_used": False,
        "next_gate": "SEPARATE_RESEARCHER_AUTHORIZATION_FOR_ONE_SINGLE_GPU_SCIENTIFIC_SEED_SHARD_EXECUTION",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify_preparation()
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SeedShardingPreparationVerificationError, protocol.ControlledInterventionProtocolError, OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
