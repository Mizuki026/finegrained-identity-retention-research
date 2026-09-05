#!/usr/bin/env python3
"""Fail-closed runner for controlled LFE projection exchange v1."""
from __future__ import annotations

import argparse
import json
import os
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
    if auth_file.resolve() != protocol.DRY_RUN_AUTH.resolve():
        raise ControlledInterventionRunnerError("dry-run authorization path mismatch")
    auth = protocol.read_json(auth_file)
    if auth.get("status") != protocol.DRY_RUN_STATUS or auth.get("gpu_execution_explicitly_approved") is not False:
        raise ControlledInterventionRunnerError("no-weight dry-run authorization status drift")
    if protocol.bound(auth.get("implementation_authorization", {}), "implementation authorization").resolve() != protocol.IMPLEMENTATION_AUTH.resolve():
        raise ControlledInterventionRunnerError("implementation authorization path drift")
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
    expected_status = f"CONTROLLED_INTERVENTION_{phase.upper()}_GPU_EXECUTION_AUTHORIZED"
    if auth.get("status") != expected_status or auth.get("execution_explicitly_approved") is not True:
        raise ControlledInterventionRunnerError("active phase execution lacks separate authorization")
    if auth.get("phase") != phase:
        raise ControlledInterventionRunnerError("phase authorization mismatch")
    _validate_code(auth)
    audit = protocol.bound(auth.get("formal_input_audit_freeze", {}), "formal input audit")
    if protocol.read_json(audit).get("status") != FORMAL_AUDIT_STATUS:
        raise ControlledInterventionRunnerError("formal input audit is not frozen pass")
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
