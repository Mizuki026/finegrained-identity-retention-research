#!/usr/bin/env python3
"""Fail-closed scientific runner for token-resolved LFE direction v1."""
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
GOV = REPO / "governance/mechanism_token_direction_scientific_v1"
RESEARCHER_AUTH = GOV / "researcher_scientific_execution_authorization_v1.json"
ACTIVE_STATUS = "TOKEN_DIRECTION_SCIENTIFIC_GPU_EXECUTION_AUTHORIZED"
DRY_STATUS = "TOKEN_DIRECTION_SCIENTIFIC_RUNNER_NO_WEIGHT_DRY_RUN_AUTHORIZED"
CODE_PATHS = tuple(REPO / "src" / name for name in (
    "token_resolved_lfe_direction_protocol_v1.py",
    "token_resolved_lfe_direction_instrumentation_v1.py",
    "analyze_token_resolved_lfe_direction_v1.py",
    "verify_token_resolved_lfe_direction_v1.py",
    "run_token_resolved_lfe_direction_scientific_v1.py",
    "token_resolved_lfe_direction_scientific_runtime_v1.py",
    "verify_token_resolved_lfe_direction_scientific_outputs_v1.py",
))


class ScientificGateError(RuntimeError):
    pass


def git_value(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def verify_binding(binding: dict, label: str) -> Path:
    path = protocol.resolve_repository_path(str(binding.get("path", "")))
    try:
        protocol.verify_file(path, int(binding.get("bytes", -1)), str(binding.get("sha256", "")))
    except (ValueError, protocol.DirectionProtocolError) as error:
        raise ScientificGateError(f"{label} binding failed: {error}") from error
    return path


def validate_researcher_authority() -> dict:
    auth = protocol.read_json(RESEARCHER_AUTH)
    if auth.get("status") != "SCIENTIFIC_RUNNER_AND_SINGLE_GPU_FIXED_ANALYSIS_AUTHORIZED_SUBJECT_TO_FINAL_CODE_BOUND_EXECUTION_GATE":
        raise ScientificGateError("researcher scientific authority status mismatch")
    required = (
        "scientific_runner_implementation_and_audit", "cpu_only_tests_and_no_weight_dry_run",
        "single_gpu_scientific_reference_extraction", "transient_in_memory_raw_tokens",
        "fixed_640_margin_outcome_blind_analysis", "pooled_lfe_replication",
        "independent_in_memory_recomputation", "aggregate_output_persistence",
    )
    if any(auth.get("authorized", {}).get(key) is not True for key in required):
        raise ScientificGateError("scientific authority incomplete")
    forbidden = (
        "raw_identity_or_token_tensor_persistence", "outcome_access_or_join",
        "association_computation", "p_values_or_confidence_intervals",
        "token_selection_or_weight_fitting", "cross_attribute_ranking",
        "video_generation_or_decode", "full_diffusion_trajectory",
        "fallback_assignment_exclusion_or_rerun", "controlled_intervention", "network",
    )
    if any(auth.get("not_authorized", {}).get(key) is not True for key in forbidden):
        raise ScientificGateError("scientific forbidden-action boundary incomplete")
    return auth


def validate_code(auth: dict) -> None:
    bindings = auth.get("code", {})
    if set(bindings) != {path.name for path in CODE_PATHS}:
        raise ScientificGateError("scientific code universe mismatch")
    for path in CODE_PATHS:
        bound = verify_binding(bindings[path.name], path.name)
        if bound.resolve() != path.resolve():
            raise ScientificGateError(f"scientific code path mismatch: {path.name}")


def assert_no_top_level_ml_imports() -> None:
    forbidden = {"torch", "models", "diffusers", "transformers"}
    for path in CODE_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            names = []
            if isinstance(node, ast.Import): names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module: names = [node.module]
            if any(name.split(".")[0] in forbidden for name in names):
                raise ScientificGateError(f"top-level ML import forbidden: {path.name}")


def validate_common(auth: dict, output_dir: Path) -> None:
    validate_researcher_authority()
    validate_code(auth)
    verify_binding(auth.get("formal_input_audit_freeze", {}), "formal input audit")
    phase_e_path = verify_binding(auth.get("phase_e_freeze", {}), "Phase-E freeze")
    if protocol.read_json(phase_e_path).get("status") != "FROZEN_PASS_PHASE_E_EXECUTION_AND_INDEPENDENT_VERIFICATION":
        raise ScientificGateError("Phase-E did not pass")
    if Path(str(auth.get("runtime_output_dir", auth.get("output_dir", "")))).resolve() != output_dir.resolve():
        raise ScientificGateError("scientific output directory mismatch")


def validate_dry(auth_file: Path, output_dir: Path) -> dict:
    protocol.ensure_cpu_only()
    auth = protocol.read_json(auth_file)
    if auth.get("status") != DRY_STATUS or auth.get("gpu_execution_explicitly_approved") is not False:
        raise ScientificGateError("scientific dry-run authorization mismatch")
    validate_common(auth, output_dir)
    return auth


def validate_active(auth_file: Path, output_dir: Path) -> dict:
    auth = protocol.read_json(auth_file)
    if auth.get("status") != ACTIVE_STATUS or auth.get("gpu_execution_explicitly_approved") is not True:
        raise ScientificGateError("scientific GPU execution lacks active authorization")
    validate_common(auth, output_dir)
    exact = {
        "scientific_reference_records": 160, "formal_units": 40,
        "primary_margin_rows": 640, "transformer_step_ceiling": 0,
        "full_diffusion_trajectory_ceiling": 0,
    }
    if any(auth.get(key) != value for key, value in exact.items()):
        raise ScientificGateError("scientific execution count drift")
    if auth.get("raw_token_persistence") is not False or auth.get("outcome_access_or_join") is not False:
        raise ScientificGateError("scientific privacy/outcome boundary drift")
    if not 0 < float(auth.get("phase_gpu_hours_ceiling", 0)) <= 8:
        raise ScientificGateError("scientific GPU-hour ceiling must be within (0,8]")
    cuda = str(auth.get("cuda_visible_devices", ""))
    if not cuda.isdigit() or "," in cuda or os.environ.get("CUDA_VISIBLE_DEVICES") != cuda:
        raise ScientificGateError("scientific execution requires exactly the authorized CUDA device")
    for key in ("WORLD_SIZE", "LOCAL_WORLD_SIZE"):
        if os.environ.get(key, "1") != "1": raise ScientificGateError("distributed execution forbidden")
    if git_value(REPO, "branch", "--show-current") != "main" or git_value(REPO, "status", "--short"):
        raise ScientificGateError("scientific execution requires clean main")
    consisid = Path(str(auth.get("consisid_repository", "")))
    if git_value(consisid, "rev-parse", "HEAD") != protocol.CONSISID_COMMIT or git_value(consisid, "status", "--short"):
        raise ScientificGateError("ConsisID repository state drift")
    if output_dir.exists(): raise ScientificGateError("scientific output directory must not exist")
    return auth


def dry_run(auth_file: Path, output_dir: Path) -> int:
    validate_dry(auth_file, output_dir)
    assert_no_top_level_ml_imports()
    if output_dir.exists(): raise ScientificGateError("scientific dry-run output exists")
    _, rows = protocol.validate_formal_master()
    plan = protocol.scientific_reference_plan(rows)
    output_dir.mkdir(parents=True, exist_ok=False)
    protocol.atomic_csv(output_dir / "scientific_execution_plan_v1.csv", tuple(plan[0]), plan)
    summary = {
        "schema_version": 1, "status": "PASS_SCIENTIFIC_RUNNER_CPU_ONLY_NO_WEIGHT_DRY_RUN",
        "plan_rows": 160, "formal_units": 40, "matched_pairs": 20,
        "primary_margin_rows": 640, "gpu_used": False, "torch_imported": "torch" in sys.modules,
        "model_or_weight_loading": False, "reference_images_opened": False,
        "raw_tokens_captured_or_persisted": False, "scientific_analysis_run": False,
        "outcomes_opened_or_joined": False, "network_used": False,
    }
    if summary["torch_imported"]: raise ScientificGateError("dry-run imported torch")
    protocol.atomic_json(output_dir / "scientific_runner_no_weight_dry_run_v1.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def execute(auth_file: Path, output_dir: Path) -> int:
    validate_active(auth_file, output_dir)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false")
    from token_resolved_lfe_direction_scientific_runtime_v1 import execute_scientific
    return execute_scientific(output_dir, auth_file)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("dry-run", "execute-scientific"))
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    return dry_run(args.authorization_file, args.output_dir) if args.mode == "dry-run" else execute(args.authorization_file, args.output_dir)


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (ScientificGateError, protocol.DirectionProtocolError, ValueError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr); raise SystemExit(2)
