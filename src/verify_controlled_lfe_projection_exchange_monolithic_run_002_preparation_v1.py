#!/usr/bin/env python3
"""CPU-only, torch-free verifier for monolithic run-002 preparation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import controlled_lfe_projection_exchange_monolithic_runtime_v2 as runtime
import controlled_lfe_projection_exchange_protocol_v1 as protocol
import run_controlled_lfe_projection_exchange_monolithic_v2 as runner
import verify_controlled_lfe_projection_exchange_scientific_monolithic_v2 as scientific_verifier


class PreparationVerificationError(RuntimeError):
    """Raised when the prospective CPU-only preparation drifts."""


def verify(dry_run_path: Path) -> dict[str, object]:
    protocol.require_cpu_only()
    if "torch" in sys.modules:
        raise PreparationVerificationError("preparation verifier imported torch")
    dry_run = protocol.read_json(dry_run_path)
    expected = {
        "status": "PASS_MONOLITHIC_RUN_002_CPU_ONLY_NO_WEIGHT_DRY_RUN",
        "plan_rows": 480, "source_tasks": 160, "formal_units": 40,
        "formal_pairs": 20, "conditions": 3, "scientific_trajectories": 480,
        "scientific_scheduler_steps": 24000, "fresh_preprocessing_calls": 40,
        "direct_lfe_acquisitions": 40, "held_pair_out_directions": 640,
        "single_acquisition_transaction_planned": True,
        "four_seeds_same_process_planned": True,
        "acquisition_scalar_hashes_planned": 40,
        "direction_and_sham_scalar_hash_pairs_planned": 640,
        "active_gpu_authorization_present": False,
        "complete_plan_csv_persisted": True, "complete_plan_csv_rows": 480,
        "formal_manifest_opened": False, "reference_opened_or_preprocessed": False,
        "outcome_opened": False, "model_modules_imported": False,
        "weights_loaded": False, "gpu_used": False,
        "trajectory_or_intervention_executed": False,
        "latent_or_video_generated_or_decoded": False,
        "network_used": False, "torch_imported": False,
    }
    if any(dry_run.get(key) != value for key, value in expected.items()):
        raise PreparationVerificationError("no-weight dry-run evidence drift")
    rows = runtime._phase_rows()
    if rows != protocol.execution_plan() or len(rows) != 480:
        raise PreparationVerificationError("monolithic runtime plan drift")
    plan_path = dry_run_path.with_name("monolithic_run_002_no_weight_plan_v1.csv")
    persisted_plan = protocol.read_csv(plan_path)
    expected_plan = [
        {key: str(row[key]) for key in protocol.PLAN_FIELDS}
        for row in protocol.execution_plan()
    ]
    if persisted_plan != expected_plan:
        raise PreparationVerificationError("complete no-weight plan CSV drift")
    instrumentation_source = runner.CODE_PATHS["instrumentation"].read_text(encoding="utf-8")
    runtime_source = runner.CODE_PATHS["runtime"].read_text(encoding="utf-8")
    if instrumentation_source.count('"direction_sha256": tensor_scalar_sha256(direction)') != 1:
        raise PreparationVerificationError("target direction hash wiring missing or duplicated")
    if instrumentation_source.count('"sham_direction_sha256": tensor_scalar_sha256(sham)') != 1:
        raise PreparationVerificationError("sham direction hash wiring missing or duplicated")
    required_runtime_fragments = (
        "controlled_lfe_projection_exchange_instrumentation_v2",
        "trajectory_status_v2.csv", "acquisition_scalar_hashes_v2.csv",
        "direction_scalar_diagnostics_v2.csv", "execution_summary_v2.json",
        "single_acquisition_transaction=True", "four_seeds_same_process=True",
    )
    if any(fragment not in runtime_source for fragment in required_runtime_fragments):
        raise PreparationVerificationError("runtime v2 evidence wiring incomplete")
    if scientific_verifier.PERSISTED_PLAN_FIELDS != (
        "planned_task_id", "planned_unit_id", "formal_pair_id", "attribute", "role",
        "seed_index", "seed", "condition_position", "condition", "scheduler_positions",
    ):
        raise PreparationVerificationError("verifier persisted schema drift")
    if runner.ACTIVE_AUTH.exists():
        raise PreparationVerificationError("GPU execution authorization unexpectedly exists")
    if runner.RUNTIME_OUTPUT.exists() or runner.RUNTIME_OUTPUT.with_name(runner.RUNTIME_OUTPUT.name + ".partial").exists():
        raise PreparationVerificationError("run-002 scalar runtime unexpectedly exists")
    if runner.PRIVATE_OUTPUT.exists():
        raise PreparationVerificationError("run-002 private runtime unexpectedly exists")
    private_parent = runner.PRIVATE_OUTPUT.parent
    if not private_parent.is_dir() or private_parent.stat().st_mode & 0o777 != 0o700:
        raise PreparationVerificationError("private parent is absent or not mode 0700")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_MONOLITHIC_RUN_002_CPU_ONLY_PREPARATION_VERIFICATION",
        "scientific_trajectories": 480, "scheduler_steps": 24000,
        "complete_plan_csv_rows_verified": 480,
        "single_acquisition_transaction": True, "four_seeds_same_process": True,
        "runtime_persisted_plan_fields": list(scientific_verifier.PERSISTED_PLAN_FIELDS),
        "direction_hash_wiring_verified": True, "sham_direction_hash_wiring_verified": True,
        "active_gpu_authorization_present": False,
        "runtime_output_present": False, "private_output_present": False,
        "private_parent_mode": "0700", "cuda_visible_devices": "",
        "torch_imported": False, "model_or_weights_loaded": False,
        "formal_manifest_or_reference_opened": False, "outcome_opened": False,
        "trajectory_or_intervention_executed": False, "network_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.dry_run)
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PreparationVerificationError, protocol.ControlledInterventionProtocolError, OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
