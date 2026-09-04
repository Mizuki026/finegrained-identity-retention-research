#!/usr/bin/env python3
"""Fail-closed runner for the preregistered token-direction v2 transaction."""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import token_resolved_lfe_direction_protocol_v2 as protocol


REPO = Path(__file__).resolve().parents[1]
GOV = REPO / "governance/mechanism_token_direction_implementation_v2"
IMPLEMENTATION_AUTH = GOV / "researcher_implementation_authorization_v2.json"
DRY_STATUS = "TOKEN_DIRECTION_V2_NO_WEIGHT_DRY_RUN_AUTHORIZED"
ACTIVE_STATUS = "TOKEN_DIRECTION_V2_GPU_EXECUTION_AUTHORIZED"
AUDIT_PASS_STATUS = "FROZEN_PASS_TOKEN_DIRECTION_V2_FORMAL_INPUT_AUDIT"
CODE_PATHS = tuple(
    REPO / "src" / name
    for name in (
        "token_resolved_lfe_direction_protocol_v2.py",
        "analyze_token_resolved_lfe_direction_v2.py",
        "verify_token_resolved_lfe_direction_v2.py",
        "run_token_resolved_lfe_direction_v2.py",
        "token_resolved_lfe_direction_runtime_v2.py",
    )
)


class DirectionV2RunnerError(RuntimeError):
    pass


def git_value(repository: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repository), *args], text=True
    ).strip()


def binding(item: dict, label: str) -> Path:
    path = protocol.resolve(str(item.get("path", "")))
    try:
        protocol.verify_file(path, int(item.get("bytes", -1)), str(item.get("sha256", "")))
    except (TypeError, ValueError, protocol.DirectionV2ProtocolError) as error:
        raise DirectionV2RunnerError(f"{label} binding failed: {error}") from error
    return path


def validate_implementation_authority() -> dict:
    try:
        return protocol.validate_implementation_authority()
    except protocol.DirectionV2ProtocolError as error:
        raise DirectionV2RunnerError(str(error)) from error


def validate_code(auth: dict) -> None:
    code = auth.get("code", {})
    labels = ("protocol", "analyzer", "verifier", "runner", "runtime")
    if set(code) != set(labels):
        raise DirectionV2RunnerError("code universe mismatch")
    for label, path in zip(labels, CODE_PATHS):
        if binding(code[label], label).resolve() != path.resolve():
            raise DirectionV2RunnerError(f"code path mismatch: {path.name}")


def assert_no_top_level_ml_imports() -> None:
    for path in CODE_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            )
            if any(name.split(".")[0] in {"torch", "models", "diffusers", "transformers"} for name in names):
                raise DirectionV2RunnerError(f"top-level ML import: {path.name}")


def validate_dry(auth_file: Path, output: Path) -> dict:
    validate_implementation_authority()
    if auth_file.resolve() != protocol.DRY_RUN_AUTH.resolve():
        raise DirectionV2RunnerError("dry authorization path mismatch")
    try:
        auth = protocol.validate_dry_authority(output)
    except protocol.DirectionV2ProtocolError as error:
        raise DirectionV2RunnerError(str(error)) from error
    if auth.get("status") != DRY_STATUS:
        raise DirectionV2RunnerError("dry authorization status mismatch")
    validate_code(auth)
    return auth


def validate_active(auth_file: Path, output: Path) -> dict:
    validate_implementation_authority()
    auth = protocol.read_json(auth_file)
    if auth.get("status") != ACTIVE_STATUS or auth.get("gpu_execution_explicitly_approved") is not True:
        raise DirectionV2RunnerError("GPU execution lacks active authorization")
    validate_code(auth)
    if binding(auth.get("design_freeze", {}), "design freeze").resolve() != protocol.DESIGN_FREEZE.resolve():
        raise DirectionV2RunnerError("design freeze path mismatch")
    audit = binding(auth.get("formal_input_audit_freeze", {}), "formal input audit")
    if protocol.read_json(audit).get("status") != AUDIT_PASS_STATUS:
        raise DirectionV2RunnerError("formal input audit did not pass")
    exact = {
        "formal_units": 40,
        "source_records": 160,
        "fresh_preprocessing_calls": 160,
        "direct_lfe_calls": 200,
        "direct_control_rows": 40,
        "four_label_rows": 120,
        "current_pooled_rows": 20,
        "historical_rows": 20,
        "token_margin_rows": 640,
        "token_panel_rows": 64,
        "pair_sign_rows": 20,
        "transformer_step_ceiling": 0,
        "full_diffusion_trajectory_ceiling": 0,
    }
    if any(auth.get(key) != value for key, value in exact.items()):
        raise DirectionV2RunnerError("execution count drift")
    if not 0 < float(auth.get("phase_gpu_hours_ceiling", 0)) <= 2:
        raise DirectionV2RunnerError("GPU-hour ceiling drift")
    cuda = str(auth.get("cuda_visible_devices", ""))
    if not cuda.isdigit() or "," in cuda or os.environ.get("CUDA_VISIBLE_DEVICES") != cuda:
        raise DirectionV2RunnerError("single CUDA binding mismatch")
    if any(os.environ.get(name, "1") != "1" for name in ("WORLD_SIZE", "LOCAL_WORLD_SIZE")):
        raise DirectionV2RunnerError("distributed execution forbidden")
    if git_value(REPO, "branch", "--show-current") != "main" or git_value(REPO, "status", "--short"):
        raise DirectionV2RunnerError("execution requires clean main")
    consisid = Path(str(auth.get("consisid_repository", "")))
    if git_value(consisid, "rev-parse", "HEAD") != protocol.CONSISID_COMMIT or git_value(consisid, "status", "--short"):
        raise DirectionV2RunnerError("ConsisID state drift")
    staging = output.with_name(output.name + ".partial")
    if Path(str(auth.get("runtime_output_dir", ""))).resolve() != output.resolve() or output.exists() or staging.exists():
        raise DirectionV2RunnerError("runtime output mismatch or output/staging exists")
    return auth


def dry_run(auth_file: Path, output: Path) -> int:
    validate_dry(auth_file, output)
    assert_no_top_level_ml_imports()
    if output.exists():
        raise DirectionV2RunnerError("dry-run output exists")
    _, formal = protocol.formal_rows()
    plan = protocol.execution_plan(formal)
    output.mkdir(parents=True, exist_ok=False)
    protocol.atomic_csv(output / "token_direction_v2_execution_plan.csv", tuple(plan[0]), plan)
    summary = {
        "schema_version": 2,
        "status": protocol.DRY_STATUS,
        "plan_rows": 160,
        "formal_units": 40,
        "matched_pairs": 20,
        "fresh_preprocessing_calls_planned": 160,
        "direct_lfe_calls_planned": 200,
        "same_input_direct_repeat_controls_planned": 40,
        "four_label_comparisons_planned": 120,
        "current_pooled_rows_planned": 20,
        "historical_rows_planned": 20,
        "token_margin_rows_planned": 640,
        "token_panel_rows_planned": 64,
        "pair_sign_rows_planned": 20,
        "reference_images_opened": False,
        "preprocessing_run": False,
        "model_or_weight_loading": False,
        "gpu_used": False,
        "raw_tokens_captured": False,
        "formal_token_margins_computed": False,
        "outcomes_opened": False,
        "associations_computed": False,
        "generation_run": False,
        "intervention_run": False,
        "network_used": False,
        "torch_imported": "torch" in sys.modules,
    }
    if summary["torch_imported"]:
        raise DirectionV2RunnerError("dry-run imported torch")
    protocol.atomic_json(output / "token_direction_v2_no_weight_dry_run.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def execute(auth_file: Path, output: Path) -> int:
    validate_active(auth_file, output)
    os.environ.update(
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        TOKENIZERS_PARALLELISM="false",
    )
    from token_resolved_lfe_direction_runtime_v2 import execute_token_direction_v2

    return execute_token_direction_v2(output, auth_file)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("dry-run", "execute-token-direction-v2"))
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    return dry_run(args.authorization_file, args.output_dir) if args.mode == "dry-run" else execute(args.authorization_file, args.output_dir)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DirectionV2RunnerError, protocol.DirectionV2ProtocolError, ValueError, KeyError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
