#!/usr/bin/env python3
"""Fail-closed Phase-E engineering runner for token-resolved LFE direction v1.

No ML framework or ConsisID module is imported until an active, separately
approved GPU authorization has passed every prospective gate.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import token_resolved_lfe_direction_protocol_v1 as protocol


REPO = Path(__file__).resolve().parents[1]
GOVERNANCE = REPO / "governance/mechanism_token_direction_engineering_v1"
RUNNER_IMPLEMENTATION_AUTHORIZATION = GOVERNANCE / "researcher_runner_implementation_authorization_v1.json"
FORMAL_INPUT_AUDIT_FREEZE = (
    REPO
    / "governance/mechanism_token_direction_input_audit_v1"
    / "formal_input_audit_freeze_v1.json"
)
ACTIVE_STATUS = "TOKEN_DIRECTION_PHASE_E_GPU_EXECUTION_AUTHORIZED"
DRY_RUN_STATUS = "TOKEN_DIRECTION_PHASE_E_RUNNER_NO_WEIGHT_DRY_RUN_AUTHORIZED"
CODE_PATHS = (
    REPO / "src/token_resolved_lfe_direction_protocol_v1.py",
    REPO / "src/token_resolved_lfe_direction_instrumentation_v1.py",
    REPO / "src/run_token_resolved_lfe_direction_engineering_v1.py",
    REPO / "src/token_resolved_lfe_direction_engineering_runtime_v1.py",
    REPO / "src/verify_token_resolved_lfe_direction_engineering_v1.py",
)


class RunnerGateError(RuntimeError):
    """Raised before any forbidden runtime action can begin."""


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()


def _binding(path: Path) -> dict:
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": protocol.sha256(path)}


def _verify_binding(binding: dict, *, label: str) -> Path:
    path = protocol.resolve_repository_path(str(binding.get("path", "")))
    try:
        protocol.verify_file(path, int(binding.get("bytes", -1)), str(binding.get("sha256", "")))
    except (ValueError, protocol.DirectionProtocolError) as error:
        raise RunnerGateError(f"{label} binding failed: {error}") from error
    return path


def validate_runner_implementation_authorization() -> dict:
    auth = protocol.read_json(RUNNER_IMPLEMENTATION_AUTHORIZATION)
    if auth.get("status") != (
        "ENGINEERING_RUNNER_IMPLEMENTATION_AUDIT_AND_NO_WEIGHT_DRY_RUN_AUTHORIZED_"
        "GPU_EXECUTION_NOT_AUTHORIZED"
    ):
        raise RunnerGateError("runner implementation authorization status mismatch")
    _verify_binding(auth.get("formal_input_audit_freeze", {}), label="formal input audit")
    freeze = protocol.read_json(FORMAL_INPUT_AUDIT_FREEZE)
    required = auth["formal_input_audit_freeze"].get("required_status")
    if freeze.get("status") != required:
        raise RunnerGateError("formal input audit did not pass")
    for key in (
        "engineering_runner_implementation",
        "independent_runner_verifier_implementation",
        "cpu_only_static_and_synthetic_tests",
        "cpu_only_no_weight_runner_dry_run",
        "runner_code_and_binding_audit",
        "single_gpu_phase_e_execution_authorization_package_generation",
    ):
        if auth.get("authorized", {}).get(key) is not True:
            raise RunnerGateError(f"missing implementation authority: {key}")
    for key in (
        "phase_e_model_or_weight_loading",
        "phase_e_gpu_execution",
        "reference_image_decode_or_face_preprocessing",
        "raw_token_persistence",
        "scientific_reference_extraction",
        "scientific_analysis",
        "outcome_access_or_join",
        "generation",
        "network",
        "controlled_intervention",
    ):
        if auth.get("not_authorized", {}).get(key) is not True:
            raise RunnerGateError(f"implementation boundary drift: {key}")
    return auth


def _validate_code_bindings(auth: dict) -> None:
    bindings = auth.get("code", {})
    expected_names = {path.name for path in CODE_PATHS}
    if set(bindings) != expected_names:
        raise RunnerGateError("authorized code-file universe mismatch")
    for path in CODE_PATHS:
        bound = _verify_binding(bindings[path.name], label=path.name)
        if bound.resolve() != path.resolve():
            raise RunnerGateError(f"authorized code path mismatch: {path.name}")


def _assert_no_top_level_ml_imports() -> None:
    forbidden_roots = {"torch", "diffusers", "transformers", "models"}
    for path in CODE_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(name.split(".")[0] in forbidden_roots for name in names):
                raise RunnerGateError(f"top-level ML import forbidden: {path.name}")


def validate_dry_run_authorization(path: Path, output_dir: Path) -> dict:
    validate_runner_implementation_authorization()
    protocol.ensure_cpu_only()
    auth = protocol.read_json(path)
    if auth.get("status") != DRY_RUN_STATUS:
        raise RunnerGateError("runner dry-run authorization status mismatch")
    if auth.get("gpu_execution_explicitly_approved") is not False:
        raise RunnerGateError("runner dry-run authorization must explicitly forbid GPU")
    if Path(str(auth.get("output_dir", ""))).resolve() != output_dir.resolve():
        raise RunnerGateError("runner dry-run output directory mismatch")
    _validate_code_bindings(auth)
    _verify_binding(auth.get("runner_implementation_authorization", {}), label="runner authority")
    _verify_binding(auth.get("formal_input_audit_freeze", {}), label="formal input audit")
    return auth


def validate_active_execution_authorization(path: Path, output_dir: Path) -> dict:
    validate_runner_implementation_authorization()
    auth = protocol.read_json(path)
    if auth.get("status") != ACTIVE_STATUS or auth.get("gpu_execution_explicitly_approved") is not True:
        raise RunnerGateError("Phase-E GPU execution lacks final active researcher authorization")
    if auth.get("phase") != "engineering" or auth.get("scientific_extraction_authorized") is not False:
        raise RunnerGateError("Phase-E authorization scope mismatch")
    if Path(str(auth.get("runtime_output_dir", ""))).resolve() != output_dir.resolve():
        raise RunnerGateError("Phase-E output directory mismatch")
    if auth.get("engineering_units") != 8 or auth.get("direct_pass_ceiling") != 16:
        raise RunnerGateError("Phase-E direct-pass ceiling drift")
    if auth.get("hook_control_ceiling") != 8 or auth.get("transformer_step_ceiling") != 8:
        raise RunnerGateError("Phase-E hook/step ceiling drift")
    gpu_hours = float(auth.get("phase_gpu_hours_ceiling", 0))
    if not 0 < gpu_hours <= 4:
        raise RunnerGateError("Phase-E GPU-hour ceiling must be within (0,4]")
    cuda_device = str(auth.get("cuda_visible_devices", ""))
    if not cuda_device.isdigit() or "," in cuda_device:
        raise RunnerGateError("Phase-E must select exactly one numeric CUDA device")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != cuda_device:
        raise RunnerGateError("CUDA_VISIBLE_DEVICES differs from active authorization")
    for variable in ("WORLD_SIZE", "LOCAL_WORLD_SIZE"):
        if os.environ.get(variable, "1") != "1":
            raise RunnerGateError(f"distributed execution forbidden: {variable}")
    if git_value("branch", "--show-current") != "main":
        raise RunnerGateError("Phase-E execution requires branch main")
    if git_value("status", "--short"):
        raise RunnerGateError("Phase-E execution requires a clean research worktree")
    _validate_code_bindings(auth)
    _verify_binding(auth.get("formal_input_audit_freeze", {}), label="formal input audit")
    if auth.get("consisid_commit") != protocol.CONSISID_COMMIT:
        raise RunnerGateError("ConsisID commit binding mismatch")
    consisid_repo = Path(str(auth.get("consisid_repository", "")))
    if subprocess.check_output(["git", "-C", str(consisid_repo), "rev-parse", "HEAD"], text=True).strip() != protocol.CONSISID_COMMIT:
        raise RunnerGateError("ConsisID repository commit drift")
    if subprocess.check_output(["git", "-C", str(consisid_repo), "status", "--short"], text=True).strip():
        raise RunnerGateError("ConsisID worktree must be clean")
    if output_dir.exists():
        raise RunnerGateError("Phase-E output directory must not exist")
    return auth


def dry_run(auth_file: Path, output_dir: Path) -> int:
    auth = validate_dry_run_authorization(auth_file, output_dir)
    _assert_no_top_level_ml_imports()
    if output_dir.exists():
        raise RunnerGateError("runner dry-run output directory already exists")
    _, rows = protocol.validate_formal_master()
    plan = protocol.engineering_plan(rows)
    output_dir.mkdir(parents=True, exist_ok=False)
    protocol.atomic_csv(output_dir / "phase_e_engineering_plan_v1.csv", tuple(plan[0]), plan)
    summary = {
        "schema_version": 1,
        "status": "PASS_PHASE_E_RUNNER_CPU_ONLY_NO_WEIGHT_DRY_RUN",
        "authorization": _binding(auth_file),
        "engineering_units": len({row["formal_unit_id"] for row in plan}),
        "direct_passes": sum(row["operation"].startswith("direct_lfe_repeat_") for row in plan),
        "hook_controls": sum(row["operation"] == "one_step_hook_equivalence" for row in plan),
        "transformer_step_ceiling": 8,
        "phase_gpu_hours_ceiling": 4,
        "single_gpu_only": True,
        "top_level_ml_import_audit_passed": True,
        "torch_imported": "torch" in sys.modules,
        "consisid_modules_imported": any(name == "models" or name.startswith("models.") for name in sys.modules),
        "reference_images_opened": False,
        "reference_images_decoded": False,
        "face_preprocessing_run": False,
        "model_weights_loaded": False,
        "raw_tokens_captured_or_persisted": False,
        "pipeline_forward_run": False,
        "scientific_extraction_run": False,
        "outcomes_opened_or_joined": False,
        "gpu_used": False,
        "network_used": False,
        "gpu_execution_authorized_by_this_artifact": False,
    }
    if summary["torch_imported"] or summary["consisid_modules_imported"]:
        raise RunnerGateError("dry-run unexpectedly imported an ML runtime")
    protocol.atomic_json(output_dir / "phase_e_runner_no_weight_dry_run_v1.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def execute(auth_file: Path, output_dir: Path) -> int:
    validate_active_execution_authorization(auth_file, output_dir)
    os.environ.update(
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        TOKENIZERS_PARALLELISM="false",
    )
    # Runtime import is intentionally below every prospective authorization gate.
    from token_resolved_lfe_direction_engineering_runtime_v1 import execute_phase_e

    return execute_phase_e(output_dir, auth_file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("dry-run", "execute-engineering"))
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "dry-run":
        return dry_run(args.authorization_file, args.output_dir)
    return execute(args.authorization_file, args.output_dir)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RunnerGateError, protocol.DirectionProtocolError, ValueError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
