#!/usr/bin/env python3
"""Fail-closed runner for controlled LFE projection exchange v1."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import controlled_lfe_projection_exchange_protocol_v1 as protocol


class ControlledInterventionRunnerError(RuntimeError):
    """Raised before a forbidden or incompletely authorized runner action."""


CODE_PATHS = {
    "protocol": protocol.REPO / "src/controlled_lfe_projection_exchange_protocol_v1.py",
    "instrumentation": protocol.REPO / "src/controlled_lfe_projection_exchange_instrumentation_v1.py",
    "runtime": protocol.REPO / "src/controlled_lfe_projection_exchange_runtime_v1.py",
    "runner": protocol.REPO / "src/run_controlled_lfe_projection_exchange_v1.py",
    "analyzer": protocol.REPO / "src/analyze_controlled_lfe_projection_exchange_v1.py",
    "verifier": protocol.REPO / "src/verify_controlled_lfe_projection_exchange_v1.py",
}
FORMAL_AUDIT_STATUS = "FROZEN_PASS_CONTROLLED_INTERVENTION_FORMAL_INPUT_AUDIT"
CORRECTION_FREEZE_STATUS = (
    "FROZEN_PASS_CONTROLLED_INTERVENTION_MEMORY_LIFECYCLE_CORRECTION_"
    "CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_ONLY"
)
SHAM_CORRECTION_FREEZE_STATUS = (
    "FROZEN_PASS_CPU_ONLY_SHAM_PROJECTION_NUMERICAL_DIAGNOSTIC_AND_"
    "THRESHOLD_PRESERVING_CORRECTION_TESTS"
)
CONSTRUCTION_CORRECTION_FREEZE_STATUS = (
    "FROZEN_PASS_CPU_ONLY_SHAM_DISPLACEMENT_CONSTRUCTION_DIAGNOSTIC_AND_"
    "FROZEN_DESIGN_PRESERVING_CORRECTION_TESTS"
)
TARGET_CORRECTION_FREEZE_STATUS = (
    "FROZEN_PASS_CPU_ONLY_TARGET_PROJECTION_CONSTRUCTION_DIAGNOSTIC_AND_"
    "FROZEN_DESIGN_PRESERVING_CORRECTION_TESTS"
)
FORMAL_SCALE_SHAM_CORRECTION_FREEZE_STATUS = (
    "FROZEN_PASS_CPU_ONLY_FORMAL_SCALE_SHAM_DISPLACEMENT_ORTHOGONALITY_DIAGNOSTIC_AND_"
    "FROZEN_DESIGN_PRESERVING_CORRECTION_TESTS"
)
ABORT_FREEZE_STATUS = (
    "FROZEN_ABORTED_FAIL_CLOSED_CONSTRUCTED_SHAM_DISPLACEMENT_"
    "ORTHOGONALITY_INVARIANT_BEFORE_ANY_TRAJECTORY"
)
ENGINEERING_PASS_FREEZE_STATUS = "FROZEN_PASS_COMPLETE_INDEPENDENTLY_VERIFIED_SINGLE_GPU_ENGINEERING"
SHARDING_DIR = protocol.REPO / "governance/mechanism_controlled_intervention_scientific_seed_sharding_v1"
SHARDING_FREEZE = SHARDING_DIR / "scientific_seed_sharding_preparation_freeze_v1.json"
SHARDING_FREEZE_STATUS = "FROZEN_PASS_PROSPECTIVE_FOUR_SEED_SHARD_PREPARATION_ONLY_NO_GPU_EXECUTION"
SHARD_AUTH_STATUS = "CONTROLLED_INTERVENTION_SCIENTIFIC_SEED_SHARD_GPU_EXECUTION_AUTHORIZED"
SHARD_VERIFIER = protocol.REPO / "src/verify_controlled_lfe_projection_exchange_scientific_generation_v1.py"
FAMILY_VERIFIER = protocol.REPO / "src/verify_controlled_lfe_projection_exchange_scientific_seed_family_v1.py"


def _git(repository: Path, *args: str) -> str:
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(repository), *args], text=True).strip()


def _validate_code(auth: dict) -> None:
    items = auth.get("code", {})
    if set(items) != set(CODE_PATHS):
        raise ControlledInterventionRunnerError("authorized code universe mismatch")
    for label, path in CODE_PATHS.items():
        if protocol.bound(items[label], label).resolve() != path.resolve():
            raise ControlledInterventionRunnerError(f"authorized code path mismatch: {label}")


def validate_dry_authority(auth_file: Path, output_dir: Path) -> dict:
    protocol.require_cpu_only()
    protocol.validate_implementation_authority()
    resolved = auth_file.resolve()
    auth = protocol.read_json(auth_file)
    if resolved == protocol.DRY_RUN_AUTH.resolve():
        if auth.get("status") != protocol.DRY_RUN_STATUS:
            raise ControlledInterventionRunnerError("original no-weight dry-run authorization status drift")
        expected_item = auth.get("implementation_authorization", {})
        expected_path = protocol.IMPLEMENTATION_AUTH
        label = "implementation authorization"
    elif resolved == protocol.CORRECTION_DRY_RUN_AUTH.resolve():
        protocol.validate_correction_authority()
        if auth.get("status") != protocol.CORRECTION_DRY_RUN_STATUS:
            raise ControlledInterventionRunnerError("correction no-weight dry-run authorization status drift")
        expected_item = auth.get("correction_authorization", {})
        expected_path = protocol.CORRECTION_AUTH
        label = "memory-lifecycle correction authorization"
    else:
        raise ControlledInterventionRunnerError("dry-run authorization path mismatch")
    if auth.get("gpu_execution_explicitly_approved") is not False:
        raise ControlledInterventionRunnerError("no-weight dry-run cannot approve GPU execution")
    if protocol.bound(expected_item, label).resolve() != expected_path.resolve():
        raise ControlledInterventionRunnerError(f"{label} path drift")
    _validate_code(auth)
    authority = auth.get("authority", {})
    if authority.get("cpu_only_no_weight_dry_run") is not True or authority.get("independent_verification") is not True:
        raise ControlledInterventionRunnerError("dry-run authority incomplete")
    forbidden = (
        "formal_input_audit", "formal_manifest_access", "reference_access_or_preprocessing",
        "outcome_access", "model_module_or_weight_loading", "gpu_execution",
        "trajectory_or_intervention_execution", "generation_or_decode", "formal_analysis", "network",
    )
    if any(authority.get(key) is not False for key in forbidden):
        raise ControlledInterventionRunnerError("dry-run authorization enables forbidden action")
    if Path(str(auth.get("output_dir", ""))).resolve() != output_dir.resolve():
        raise ControlledInterventionRunnerError("dry-run output path mismatch")
    return auth


def dry_run(auth_file: Path, output_dir: Path) -> int:
    validate_dry_authority(auth_file, output_dir)
    if output_dir.exists() or output_dir.with_name(output_dir.name + ".partial").exists():
        raise ControlledInterventionRunnerError("dry-run output or staging path exists")
    rows = protocol.execution_plan()
    summary = {
        "schema_version": 1, "status": protocol.DRY_PASS_STATUS,
        **protocol.plan_summary(rows),
        "engineering_pairs_by_frozen_hash": {key: list(value) for key, value in protocol.engineering_pairs().items()},
        "formal_binding_status": "DEFERRED_TO_SEPARATELY_AUTHORIZED_INPUT_AUDIT",
        "formal_manifest_opened": False, "reference_opened_or_preprocessed": False,
        "outcome_opened": False, "model_modules_imported": False, "weights_loaded": False,
        "gpu_used": False, "trajectory_executed": False, "video_or_latent_generated": False,
        "video_decoded": False, "intervention_executed": False,
        "formal_analysis_computed": False, "network_used": False,
        "memory_lifecycle_correction_bound": auth_file.resolve() == protocol.CORRECTION_DRY_RUN_AUTH.resolve(),
        "acquisition_inference_mode_planned": auth_file.resolve() == protocol.CORRECTION_DRY_RUN_AUTH.resolve(),
        "identity_handles_cpu_resident_planned": auth_file.resolve() == protocol.CORRECTION_DRY_RUN_AUTH.resolve(),
        "pipeline_load_after_40_acquisitions_planned": auth_file.resolve() == protocol.CORRECTION_DRY_RUN_AUTH.resolve(),
        "face_models_release_before_pipeline_load_planned": auth_file.resolve() == protocol.CORRECTION_DRY_RUN_AUTH.resolve(),
        "torch_imported": "torch" in sys.modules,
    }
    if summary["torch_imported"]:
        raise ControlledInterventionRunnerError("dry-run imported torch")
    staging = output_dir.with_name(output_dir.name + ".partial")
    staging.mkdir(parents=True, exist_ok=False)
    protocol.atomic_csv(staging / "controlled_intervention_no_weight_plan_v1.csv", protocol.PLAN_FIELDS, rows)
    protocol.atomic_json(staging / "controlled_intervention_no_weight_dry_run_v1.json", summary)
    staging.replace(output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def validate_active(auth_file: Path, output_dir: Path, phase: str) -> dict:
    protocol.validate_implementation_authority()
    auth = protocol.read_json(auth_file)
    expected_status = (
        "CONTROLLED_INTERVENTION_ENGINEERING_GPU_EXECUTION_AUTHORIZED"
        if phase == "engineering" else SHARD_AUTH_STATUS
    )
    if auth.get("status") != expected_status or auth.get("execution_explicitly_approved") is not True:
        raise ControlledInterventionRunnerError("active phase execution lacks separate authorization")
    if auth.get("phase") != phase:
        raise ControlledInterventionRunnerError("phase authorization mismatch")
    _validate_code(auth)
    audit = protocol.bound(auth.get("formal_input_audit_freeze", {}), "formal input audit")
    if protocol.read_json(audit).get("status") != FORMAL_AUDIT_STATUS:
        raise ControlledInterventionRunnerError("formal input audit is not frozen pass")
    correction = protocol.bound(
        auth.get("memory_lifecycle_correction_freeze", {}), "memory lifecycle correction freeze"
    )
    if protocol.read_json(correction).get("status") != CORRECTION_FREEZE_STATUS:
        raise ControlledInterventionRunnerError("memory lifecycle correction is not frozen pass")
    sham_correction = protocol.bound(
        auth.get("sham_projection_correction_freeze", {}), "sham projection correction freeze"
    )
    if protocol.read_json(sham_correction).get("status") != SHAM_CORRECTION_FREEZE_STATUS:
        raise ControlledInterventionRunnerError("sham projection correction is not frozen pass")
    construction_correction = protocol.bound(
        auth.get("sham_construction_correction_freeze", {}), "sham construction correction freeze"
    )
    if protocol.read_json(construction_correction).get("status") != CONSTRUCTION_CORRECTION_FREEZE_STATUS:
        raise ControlledInterventionRunnerError("sham construction correction is not frozen pass")
    target_correction = protocol.bound(
        auth.get("target_projection_correction_freeze", {}), "target projection correction freeze"
    )
    if protocol.read_json(target_correction).get("status") != TARGET_CORRECTION_FREEZE_STATUS:
        raise ControlledInterventionRunnerError("target projection correction is not frozen pass")
    formal_scale_sham_correction = protocol.bound(
        auth.get("formal_scale_sham_correction_freeze", {}), "formal scale sham correction freeze"
    )
    if protocol.read_json(formal_scale_sham_correction).get("status") != FORMAL_SCALE_SHAM_CORRECTION_FREEZE_STATUS:
        raise ControlledInterventionRunnerError("formal scale sham correction is not frozen pass")
    abort = protocol.bound(auth.get("prior_engineering_abort_freeze", {}), "prior engineering abort freeze")
    abort_payload = protocol.read_json(abort)
    if (
        abort_payload.get("status") != ABORT_FREEZE_STATUS
        or abort_payload.get("reuse_policy", {}).get("run_005_reusable") is not False
    ):
        raise ControlledInterventionRunnerError("prior run_005 abort or non-reuse binding drift")
    if phase == "engineering" and (
        auth.get("engineering_run_id") != "run_006"
        or auth.get("prior_execution_reused") is not False
    ):
        raise ControlledInterventionRunnerError("new engineering transaction identity drift")
    if phase == "scientific":
        engineering = protocol.bound(auth.get("engineering_freeze", {}), "engineering pass freeze")
        if protocol.read_json(engineering).get("status") != ENGINEERING_PASS_FREEZE_STATUS:
            raise ControlledInterventionRunnerError("engineering pass freeze drift")
        amendment = protocol.bound(auth.get("seed_sharding_preparation_freeze", {}), "seed sharding preparation freeze")
        if amendment.resolve() != SHARDING_FREEZE.resolve() or protocol.read_json(amendment).get("status") != SHARDING_FREEZE_STATUS:
            raise ControlledInterventionRunnerError("prospective seed-sharding amendment is not frozen pass")
        for label, expected_path in (
            ("scientific_generation_verifier", SHARD_VERIFIER),
            ("scientific_seed_family_verifier", FAMILY_VERIFIER),
        ):
            if protocol.bound(auth.get(label, {}), label).resolve() != expected_path.resolve():
                raise ControlledInterventionRunnerError(f"{label} path drift")
        try:
            seed_index = int(auth.get("scientific_seed_index"))
        except (TypeError, ValueError) as error:
            raise ControlledInterventionRunnerError("scientific seed shard index missing") from error
        if seed_index not in range(1, 5):
            raise ControlledInterventionRunnerError("scientific seed shard index outside 1..4")
        expected_shard = f"seed_{seed_index}"
        researcher_shard = protocol.bound(
            auth.get("researcher_shard_execution_authorization", {}), "researcher shard execution authorization"
        )
        researcher_payload = protocol.read_json(researcher_shard)
        if researcher_payload.get("status") != SHARD_AUTH_STATUS or researcher_payload.get("scientific_shard_id") != expected_shard:
            raise ControlledInterventionRunnerError("researcher shard execution authorization drift")
        if (
            auth_file.resolve() != (SHARDING_DIR / f"scientific_{expected_shard}_execution_authorization_v1.json").resolve()
            or auth.get("status") != SHARD_AUTH_STATUS
            or auth.get("shard_family_id") != "controlled_lfe_projection_exchange_scientific_seed_shards_v1"
            or auth.get("scientific_shard_id") != expected_shard
            or auth.get("scientific_seed") != protocol.SEEDS[seed_index - 1]
            or auth.get("prior_execution_reused") is not False
            or auth.get("superseded_monolithic_run_001_reused") is not False
        ):
            raise ControlledInterventionRunnerError("scientific seed shard transaction identity drift")
        expected_output = Path(
            f"/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_shards/{expected_shard}"
        )
        expected_private = Path(
            f"/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_private_shards/{expected_shard}"
        )
        private_root = Path(str(auth.get("private_latent_output_dir", "")))
        if output_dir.resolve() != expected_output.resolve() or private_root.resolve() != expected_private.resolve():
            raise ControlledInterventionRunnerError("scientific shard output path drift")
        if not private_root.is_absolute() or protocol.REPO.resolve() in private_root.resolve().parents:
            raise ControlledInterventionRunnerError("private latent path must be absolute and outside Git")
        private_parent = private_root.parent
        if not private_parent.is_dir() or private_parent.stat().st_mode & 0o777 != 0o700:
            raise ControlledInterventionRunnerError("private latent parent must exist with mode 0700")
        minimum_free = int(auth.get("minimum_private_filesystem_free_bytes", 0))
        if minimum_free < 20 * 1024**3 or shutil.disk_usage(private_parent).free < minimum_free:
            raise ControlledInterventionRunnerError("private latent filesystem free-space gate failed")
        if float(auth.get("phase_gpu_hours_ceiling", 0)) != 18.0:
            raise ControlledInterventionRunnerError("scientific seed shard GPU ceiling must be exactly 18 hours")
        authority = auth.get("authority", {})
        required = (
            "scientific_generation", "private_final_latent_persistence",
            "complete_120_trajectory_seed_shard", "all_three_conditions_co_resident",
            "fresh_40_unit_acquisition", "scalar_lfe_and_direction_hash_evidence",
        )
        if any(authority.get(key) is not True for key in required):
            raise ControlledInterventionRunnerError("scientific seed shard authority incomplete")
        forbidden = (
            "condition_sharding", "selective_trajectory_resume_or_rerun", "decoded_media",
            "outcome_access", "annotation", "unblinding", "formal_analysis",
        )
        if any(authority.get(key) is not False for key in forbidden):
            raise ControlledInterventionRunnerError("scientific seed shard authorization enables a forbidden phase")
    cuda = str(auth.get("cuda_visible_devices", ""))
    if not cuda.isdigit() or "," in cuda or os.environ.get("CUDA_VISIBLE_DEVICES") != cuda:
        raise ControlledInterventionRunnerError("single-GPU binding mismatch")
    if any(os.environ.get(name, "1") != "1" for name in ("WORLD_SIZE", "LOCAL_WORLD_SIZE")):
        raise ControlledInterventionRunnerError("distributed execution forbidden")
    if _git(protocol.REPO, "branch", "--show-current") != "main" or _git(protocol.REPO, "status", "--short"):
        raise ControlledInterventionRunnerError("execution requires a clean main research worktree")
    if Path(str(auth.get("runtime_output_dir", ""))).resolve() != output_dir.resolve():
        raise ControlledInterventionRunnerError("runtime output path differs from authorization")
    return auth


def execute(auth_file: Path, output_dir: Path, phase: str) -> int:
    auth = validate_active(auth_file, output_dir, phase)
    from controlled_lfe_projection_exchange_runtime_v1 import (
        execute_with_adapter,
        prepare_active_runtime,
    )

    bindings, adapter = prepare_active_runtime(auth, phase)
    execute_with_adapter(phase, bindings, adapter, output_dir, auth)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("dry-run", "execute-engineering", "execute-scientific"))
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.mode == "dry-run":
        return dry_run(args.authorization_file, args.output_dir)
    return execute(args.authorization_file, args.output_dir, args.mode.removeprefix("execute-"))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ControlledInterventionRunnerError, protocol.ControlledInterventionProtocolError, KeyError, ValueError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
