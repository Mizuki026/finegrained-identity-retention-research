#!/usr/bin/env python3
"""Fail-closed runner for prospective monolithic scientific run-002."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import controlled_lfe_projection_exchange_protocol_v1 as protocol


class MonolithicRun002RunnerError(RuntimeError):
    """Raised before an unauthorized or drifting action."""


GOVERNANCE = protocol.REPO / "governance/mechanism_controlled_intervention_scientific_monolithic_run_002_v1"
RESEARCHER_AUTH = GOVERNANCE / "researcher_protocol_amendment_authorization_v1.json"
PREPARATION_FREEZE = GOVERNANCE / "monolithic_run_002_preparation_freeze_v1.json"
ACTIVE_AUTH = GOVERNANCE / "scientific_monolithic_run_002_execution_authorization_v1.json"
RESEARCHER_EXEC_AUTH = GOVERNANCE / "researcher_scientific_monolithic_run_002_execution_authorization_v1.json"
HISTORY_NONREUSE = GOVERNANCE / "historical_transactions_nonreuse_and_supersession_v1.json"
RUNTIME_OUTPUT = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_monolithic/run_002")
PRIVATE_OUTPUT = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_private_monolithic/run_002")
CONSISID = Path("/root/autodl-tmp/consisid-smoketest/ConsisID")
CONSISID_COMMIT = "60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
RESEARCHER_STATUS = "MONOLITHIC_RUN_002_PROTOCOL_AMENDMENT_DIRECTION_HASH_WIRING_VERIFIER_CORRECTION_CPU_ONLY_AUTHORIZED"
PREPARATION_STATUS = "FROZEN_PASS_MONOLITHIC_RUN_002_PROTOCOL_AMENDMENT_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_NO_GPU"
ACTIVE_STATUS = "CONTROLLED_INTERVENTION_SCIENTIFIC_MONOLITHIC_RUN_002_SINGLE_GPU_EXECUTION_AUTHORIZED"
RESEARCHER_EXEC_STATUS = "RESEARCHER_AUTHORIZATION_FOR_SINGLE_GPU_CONTROLLED_INTERVENTION_SCIENTIFIC_MONOLITHIC_RUN_002_480_TRAJECTORY_EXECUTION"
FORMAL_MASTER = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/experiment_freeze_v1/pre_generation_master_freeze_v1.json")
FORMAL_BINDINGS = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_input_audit/run_001/formal_task_binding_manifest_v1.csv")
PREREQUISITES = (
    ("formal_input_audit_freeze", protocol.REPO / "governance/mechanism_controlled_intervention_input_audit_v1/formal_input_audit_freeze_v1.json", "FROZEN_PASS_CONTROLLED_INTERVENTION_FORMAL_INPUT_AUDIT"),
    ("memory_lifecycle_correction_freeze", protocol.REPO / "governance/mechanism_controlled_intervention_memory_correction_v1/memory_lifecycle_correction_freeze_v1.json", "FROZEN_PASS_CONTROLLED_INTERVENTION_MEMORY_LIFECYCLE_CORRECTION_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_ONLY"),
    ("sham_projection_correction_freeze", protocol.REPO / "governance/mechanism_controlled_intervention_sham_projection_correction_v1/sham_projection_correction_freeze_v1.json", "FROZEN_PASS_CPU_ONLY_SHAM_PROJECTION_NUMERICAL_DIAGNOSTIC_AND_THRESHOLD_PRESERVING_CORRECTION_TESTS"),
    ("sham_construction_correction_freeze", protocol.REPO / "governance/mechanism_controlled_intervention_sham_construction_correction_v1/sham_construction_correction_freeze_v1.json", "FROZEN_PASS_CPU_ONLY_SHAM_DISPLACEMENT_CONSTRUCTION_DIAGNOSTIC_AND_FROZEN_DESIGN_PRESERVING_CORRECTION_TESTS"),
    ("target_projection_correction_freeze", protocol.REPO / "governance/mechanism_controlled_intervention_target_projection_correction_v1/target_projection_correction_freeze_v1.json", "FROZEN_PASS_CPU_ONLY_TARGET_PROJECTION_CONSTRUCTION_DIAGNOSTIC_AND_FROZEN_DESIGN_PRESERVING_CORRECTION_TESTS"),
    ("formal_scale_sham_correction_freeze", protocol.REPO / "governance/mechanism_controlled_intervention_formal_scale_sham_correction_v1/formal_scale_sham_correction_freeze_v1.json", "FROZEN_PASS_CPU_ONLY_FORMAL_SCALE_SHAM_DISPLACEMENT_ORTHOGONALITY_DIAGNOSTIC_AND_FROZEN_DESIGN_PRESERVING_CORRECTION_TESTS"),
    ("engineering_freeze", protocol.REPO / "governance/mechanism_controlled_intervention_engineering_v1/engineering_run_006_freeze_v1.json", "FROZEN_PASS_COMPLETE_INDEPENDENTLY_VERIFIED_SINGLE_GPU_ENGINEERING"),
    ("historical_nonreuse", HISTORY_NONREUSE, "FROZEN_HISTORY_PRESERVED_NONREUSABLE_FOR_MONOLITHIC_RUN_002"),
)

CODE_PATHS = {
    "protocol": protocol.REPO / "src/controlled_lfe_projection_exchange_protocol_v1.py",
    "instrumentation": protocol.REPO / "src/controlled_lfe_projection_exchange_instrumentation_v2.py",
    "runtime": protocol.REPO / "src/controlled_lfe_projection_exchange_monolithic_runtime_v2.py",
    "runner": protocol.REPO / "src/run_controlled_lfe_projection_exchange_monolithic_v2.py",
    "verifier": protocol.REPO / "src/verify_controlled_lfe_projection_exchange_scientific_monolithic_v2.py",
}


def _git(repository: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "--no-optional-locks", "-C", str(repository), *args], text=True
    ).strip()


def _validate_plan() -> dict[str, object]:
    rows = protocol.execution_plan()
    tasks = {str(row["planned_task_id"]) for row in rows}
    if (
        len(rows) != 480
        or len(tasks) != 160
        or {int(row["seed_index"]) for row in rows} != {1, 2, 3, 4}
        or sum(int(row["scheduler_positions"]) for row in rows) != 24000
        or any(
            {str(row["condition"]) for row in rows if row["planned_task_id"] == task}
            != set(protocol.CONDITIONS)
            for task in tasks
        )
    ):
        raise MonolithicRun002RunnerError("frozen 480-trajectory plan drift")
    return protocol.plan_summary(rows)


def validate_preparation(output: Path) -> dict[str, object]:
    protocol.require_cpu_only()
    if "torch" in sys.modules:
        raise MonolithicRun002RunnerError("no-weight preparation imported torch")
    auth = protocol.read_json(RESEARCHER_AUTH)
    if auth.get("status") != RESEARCHER_STATUS or auth.get("gpu_hours_authorized") != 0:
        raise MonolithicRun002RunnerError("researcher CPU-only amendment authority drift")
    if any(value is not True for value in auth.get("not_authorized", {}).values()):
        raise MonolithicRun002RunnerError("CPU-only forbidden boundary incomplete")
    if ACTIVE_AUTH.exists():
        raise MonolithicRun002RunnerError("active GPU authorization unexpectedly exists")
    if RUNTIME_OUTPUT.exists() or RUNTIME_OUTPUT.with_name(RUNTIME_OUTPUT.name + ".partial").exists():
        raise MonolithicRun002RunnerError("run-002 scalar output already exists")
    if PRIVATE_OUTPUT.exists():
        raise MonolithicRun002RunnerError("run-002 private output already exists")
    if any(not path.is_file() for path in CODE_PATHS.values()):
        raise MonolithicRun002RunnerError("run-002 code universe incomplete")
    summary = _validate_plan()
    rows = protocol.execution_plan()
    plan_output = output.with_name("monolithic_run_002_no_weight_plan_v1.csv")
    protocol.atomic_csv(plan_output, protocol.PLAN_FIELDS, rows)
    result = {
        "schema_version": 1,
        "status": "PASS_MONOLITHIC_RUN_002_CPU_ONLY_NO_WEIGHT_DRY_RUN",
        **summary,
        "single_acquisition_transaction_planned": True,
        "four_seeds_same_process_planned": True,
        "acquisition_scalar_hashes_planned": 40,
        "direction_and_sham_scalar_hash_pairs_planned": 640,
        "active_gpu_authorization_present": False,
        "complete_plan_csv_persisted": True,
        "complete_plan_csv_rows": 480,
        "formal_manifest_opened": False,
        "reference_opened_or_preprocessed": False,
        "outcome_opened": False,
        "model_modules_imported": False,
        "weights_loaded": False,
        "gpu_used": False,
        "trajectory_or_intervention_executed": False,
        "latent_or_video_generated_or_decoded": False,
        "network_used": False,
        "torch_imported": False,
    }
    protocol.atomic_json(output, result)
    return result


def _validate_code_bindings(auth: dict) -> None:
    items = auth.get("code", {})
    if set(items) != set(CODE_PATHS):
        raise MonolithicRun002RunnerError("active code universe mismatch")
    for label, path in CODE_PATHS.items():
        if protocol.bound(items[label], label).resolve() != path.resolve():
            raise MonolithicRun002RunnerError(f"active code binding drift: {label}")


def validate_active(auth_file: Path, output_dir: Path) -> dict:
    if auth_file.resolve() != ACTIVE_AUTH.resolve():
        raise MonolithicRun002RunnerError("active authorization path drift")
    auth = protocol.read_json(auth_file)
    if (
        auth.get("status") != ACTIVE_STATUS
        or auth.get("execution_explicitly_approved") is not True
        or auth.get("phase") != "scientific"
        or auth.get("scientific_run_id") != "monolithic_run_002"
    ):
        raise MonolithicRun002RunnerError("separate run-002 GPU authority absent or drifting")
    _validate_code_bindings(auth)
    researcher_execution = protocol.bound(
        auth.get("researcher_execution_authorization", {}), "researcher run-002 execution authorization"
    )
    if (
        researcher_execution.resolve() != RESEARCHER_EXEC_AUTH.resolve()
        or protocol.read_json(researcher_execution).get("status") != RESEARCHER_EXEC_STATUS
    ):
        raise MonolithicRun002RunnerError("researcher run-002 GPU authority drift")
    freeze = protocol.bound(auth.get("preparation_freeze", {}), "run-002 preparation freeze")
    if freeze.resolve() != PREPARATION_FREEZE.resolve() or protocol.read_json(freeze).get("status") != PREPARATION_STATUS:
        raise MonolithicRun002RunnerError("run-002 preparation freeze drift")
    for key, expected_path, expected_status in PREREQUISITES:
        observed_path = protocol.bound(auth.get(key, {}), key)
        if observed_path.resolve() != expected_path.resolve() or protocol.read_json(observed_path).get("status") != expected_status:
            raise MonolithicRun002RunnerError(f"prerequisite drift: {key}")
    if protocol.bound(auth.get("formal_generation_master", {}), "formal generation master").resolve() != FORMAL_MASTER.resolve():
        raise MonolithicRun002RunnerError("formal generation master drift")
    if protocol.bound(auth.get("formal_task_binding_manifest", {}), "formal task binding manifest").resolve() != FORMAL_BINDINGS.resolve():
        raise MonolithicRun002RunnerError("formal task binding manifest drift")
    if (
        auth.get("prior_execution_reused") is not False
        or auth.get("seed_1_shard_merged") is not False
        or auth.get("prior_direction_evidence_reused") is not False
    ):
        raise MonolithicRun002RunnerError("historical non-reuse boundary drift")
    if output_dir.resolve() != RUNTIME_OUTPUT.resolve() or Path(str(auth.get("runtime_output_dir", ""))).resolve() != RUNTIME_OUTPUT.resolve():
        raise MonolithicRun002RunnerError("run-002 scalar output path drift")
    private = Path(str(auth.get("private_latent_output_dir", "")))
    if private.resolve() != PRIVATE_OUTPUT.resolve() or private.exists():
        raise MonolithicRun002RunnerError("run-002 private output path drift or collision")
    parent = private.parent
    if not parent.is_dir() or parent.stat().st_mode & 0o777 != 0o700:
        raise MonolithicRun002RunnerError("private parent must be mode 0700")
    minimum_free = int(auth.get("minimum_private_filesystem_free_bytes", 0))
    if minimum_free < 20 * 1024**3 or shutil.disk_usage(parent).free < minimum_free:
        raise MonolithicRun002RunnerError("private filesystem free-space gate failed")
    if float(auth.get("phase_gpu_hours_ceiling", 0)) != 72.0:
        raise MonolithicRun002RunnerError("run-002 GPU-hour ceiling must be exactly 72")
    authority = auth.get("authority", {})
    required = (
        "scientific_generation", "single_gpu", "complete_480_trajectory_transaction",
        "single_fresh_40_unit_acquisition", "four_seeds_same_process",
        "all_three_conditions_co_resident", "private_final_latent_persistence",
        "scalar_lfe_direction_and_sham_hash_evidence",
    )
    forbidden = (
        "seed_or_condition_sharding", "automatic_retry_resume_or_selective_rerun",
        "decoded_media", "outcome_access", "annotation", "unblinding", "formal_analysis",
    )
    if any(authority.get(key) is not True for key in required) or any(authority.get(key) is not False for key in forbidden):
        raise MonolithicRun002RunnerError("run-002 authority boundary incomplete")
    cuda = str(auth.get("cuda_visible_devices", ""))
    if not cuda.isdigit() or "," in cuda or os.environ.get("CUDA_VISIBLE_DEVICES") != cuda:
        raise MonolithicRun002RunnerError("single-GPU binding mismatch")
    if any(os.environ.get(name, "1") != "1" for name in ("WORLD_SIZE", "LOCAL_WORLD_SIZE")):
        raise MonolithicRun002RunnerError("distributed execution forbidden")
    expected_environment = {
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1", "TOKENIZERS_PARALLELISM": "false",
    }
    if any(os.environ.get(key) != value for key, value in expected_environment.items()):
        raise MonolithicRun002RunnerError("offline execution environment drift")
    if _git(protocol.REPO, "branch", "--show-current") != "main" or _git(protocol.REPO, "status", "--short"):
        raise MonolithicRun002RunnerError("execution requires clean main research worktree")
    if _git(CONSISID, "rev-parse", "HEAD") != CONSISID_COMMIT or _git(CONSISID, "status", "--short"):
        raise MonolithicRun002RunnerError("ConsisID repository drift")
    return auth


def execute(auth_file: Path, output_dir: Path) -> int:
    auth = validate_active(auth_file, output_dir)
    from controlled_lfe_projection_exchange_monolithic_runtime_v2 import (
        execute_with_adapter,
        prepare_active_runtime,
    )

    bindings, adapter = prepare_active_runtime(auth, "scientific")
    execute_with_adapter("scientific", bindings, adapter, output_dir, auth)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("dry-run", "execute-scientific"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--authorization-file", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.mode == "dry-run":
        if args.output is None:
            raise MonolithicRun002RunnerError("dry-run output is required")
        print(json.dumps(validate_preparation(args.output), indent=2, sort_keys=True))
        return 0
    if args.authorization_file is None or args.output_dir is None:
        raise MonolithicRun002RunnerError("active authorization and output dir are required")
    return execute(args.authorization_file, args.output_dir)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (MonolithicRun002RunnerError, protocol.ControlledInterventionProtocolError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
