#!/usr/bin/env python3
"""Independent CPU verifier for controlled-intervention engineering v1."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GOV = REPO / "governance/mechanism_controlled_intervention_engineering_v1"
AUTHORIZATION = GOV / "engineering_run_002_execution_authorization_v1.json"
CONSISID_REPO = Path("/root/autodl-tmp/consisid-smoketest/ConsisID")
CONSISID_COMMIT = "60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
ATTRIBUTES = ("eyeglasses", "facial_hair")
PREFIX = {"eyeglasses": "FEY", "facial_hair": "FFH"}
ROLES = ("positive", "control")
CONDITIONS = ("baseline", "target_projection_exchange", "orthogonal_sham")
SEED = "2686238281"
NAMESPACE = "controlled_lfe_projection_exchange_v1"
ENGINEERING_NAMESPACE = "controlled_lfe_projection_exchange_v1_engineering_pair_subset"
AUTH_STATUS = "CONTROLLED_INTERVENTION_ENGINEERING_GPU_EXECUTION_AUTHORIZED"
RESEARCHER_STATUS = "NEW_SINGLE_GPU_CONTROLLED_INTERVENTION_ENGINEERING_RUN_AUTHORIZED"
CORRECTION_FREEZE_STATUS = (
    "FROZEN_PASS_CONTROLLED_INTERVENTION_MEMORY_LIFECYCLE_CORRECTION_"
    "CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_ONLY"
)
ABORT_FREEZE_STATUS = "FROZEN_ABORTED_FAIL_CLOSED_GPU_OOM_BEFORE_ANY_ENGINEERING_TRAJECTORY"
SUMMARY_STATUS = "COMPLETE_PENDING_INDEPENDENT_PHASE_VERIFICATION"


class EngineeringVerificationError(RuntimeError):
    """Raised when an engineering output or frozen binding drifts."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path: Path, size: int, digest: str) -> None:
    if not path.is_file() or path.is_symlink() or path.stat().st_size != size or sha256(path) != digest:
        raise EngineeringVerificationError(f"binding mismatch: {path}")


def resolve(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO / path


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file() or path.is_symlink():
        raise EngineeringVerificationError(f"missing regular CSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def finite(raw: str, label: str) -> float:
    try:
        value = float(raw)
    except ValueError as error:
        raise EngineeringVerificationError(f"invalid scalar: {label}") from error
    if not math.isfinite(value):
        raise EngineeringVerificationError(f"nonfinite scalar: {label}")
    return value


def selected_pairs() -> dict[str, tuple[str, str]]:
    output = {}
    for attribute in ATTRIBUTES:
        pairs = [f"{PREFIX[attribute]}_{index:02d}" for index in range(1, 11)]
        ranked = sorted(pairs, key=lambda pair: hashlib.sha256(f"{pair}|{ENGINEERING_NAMESPACE}".encode()).hexdigest())
        output[attribute] = (ranked[0], ranked[1])
    return output


def condition_order(task: str) -> tuple[str, ...]:
    return tuple(sorted(CONDITIONS, key=lambda condition: hashlib.sha256(
        f"{NAMESPACE}|condition_order|{task}|{condition}".encode()
    ).hexdigest()))


def expected_rows() -> list[dict[str, str]]:
    chosen = selected_pairs()
    rows = []
    for attribute in ATTRIBUTES:
        for pair_index in range(1, 11):
            pair = f"{PREFIX[attribute]}_{pair_index:02d}"
            if pair not in chosen[attribute]:
                continue
            for role in ROLES:
                unit = f"CIU__{pair}__{role}"
                task = f"CIT__{unit}__S1"
                for position, condition in enumerate(condition_order(task), 1):
                    rows.append({
                        "planned_task_id": task, "planned_unit_id": unit,
                        "formal_pair_id": pair, "attribute": attribute, "role": role,
                        "seed_index": "1", "seed": SEED, "condition_position": str(position),
                        "condition": condition, "scheduler_positions": "1",
                    })
    if len(rows) != 24:
        raise EngineeringVerificationError("independent engineering enumeration drift")
    return rows


def validate_authority(run_dir: Path) -> dict:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise EngineeringVerificationError("engineering verifier must remain CUDA-hidden and torch-free")
    auth = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    if auth.get("status") != AUTH_STATUS or auth.get("phase") != "engineering":
        raise EngineeringVerificationError("engineering authorization status or phase drift")
    researcher_item = auth.get("researcher_authorization", {})
    researcher_path = resolve(str(researcher_item.get("path", "")))
    verify_file(
        researcher_path, int(researcher_item.get("bytes", -1)),
        str(researcher_item.get("sha256", "")),
    )
    researcher = json.loads(researcher_path.read_text(encoding="utf-8"))
    if researcher.get("status") != RESEARCHER_STATUS:
        raise EngineeringVerificationError("researcher engineering authorization drift")
    if Path(str(researcher.get("output_dir", ""))).resolve() != run_dir.resolve():
        raise EngineeringVerificationError("researcher-authorized output path drift")
    if auth.get("execution_explicitly_approved") is not True or auth.get("cuda_visible_devices") != "0":
        raise EngineeringVerificationError("single-GPU authorization drift")
    if float(auth.get("phase_gpu_hours_ceiling", 0)) != 2.0:
        raise EngineeringVerificationError("engineering GPU-hour ceiling drift")
    if auth.get("engineering_run_id") != "run_002" or auth.get("prior_execution_reused") is not False:
        raise EngineeringVerificationError("new engineering transaction identity drift")
    required = (
        "single_gpu_engineering", "frozen_model_and_weight_loading",
        "reference_preprocessing_and_direct_lfe_acquisition",
        "transient_direction_and_intervention", "maximum_24_one_step_conditions",
        "scalar_only_artifacts", "independent_verification",
    )
    forbidden = (
        "scientific_generation", "more_than_one_scheduler_position",
        "media_or_latent_persistence", "raw_tensor_or_image_persistence",
        "outcome_access_annotation_unblinding_construction_or_join",
        "formal_analysis_or_hypothesis_testing", "distributed_or_multi_gpu",
        "automatic_retry_or_resume", "network",
    )
    authority = auth.get("authority", {})
    if any(authority.get(key) is not True for key in required):
        raise EngineeringVerificationError("engineering authority is incomplete")
    if any(authority.get(key) is not False for key in forbidden):
        raise EngineeringVerificationError("engineering authority enables forbidden action")
    if run_dir.resolve() != Path(str(auth.get("runtime_output_dir", ""))).resolve():
        raise EngineeringVerificationError("engineering output path drift")
    code = auth.get("code", {})
    expected_code = {"protocol", "instrumentation", "runtime", "runner", "analyzer", "verifier"}
    if set(code) != expected_code:
        raise EngineeringVerificationError("runtime code universe drift")
    for item in code.values():
        verify_file(resolve(str(item.get("path", ""))), int(item.get("bytes", -1)), str(item.get("sha256", "")))
    verifier = auth.get("engineering_verifier", {})
    verify_file(resolve(str(verifier.get("path", ""))), int(verifier.get("bytes", -1)), str(verifier.get("sha256", "")))
    for key in (
        "formal_input_audit_freeze", "memory_lifecycle_correction_freeze",
        "prior_engineering_abort_freeze", "formal_generation_master", "formal_task_binding_manifest",
    ):
        item = auth.get(key, {})
        verify_file(resolve(str(item.get("path", ""))), int(item.get("bytes", -1)), str(item.get("sha256", "")))
    correction = json.loads(resolve(str(auth["memory_lifecycle_correction_freeze"]["path"])).read_text())
    if correction.get("status") != CORRECTION_FREEZE_STATUS:
        raise EngineeringVerificationError("memory lifecycle correction freeze status drift")
    abort = json.loads(resolve(str(auth["prior_engineering_abort_freeze"]["path"])).read_text())
    if abort.get("status") != ABORT_FREEZE_STATUS or abort.get("reuse_policy", {}).get("run_001_reusable") is not False:
        raise EngineeringVerificationError("prior run_001 abort or non-reuse binding drift")
    return auth


def verify_engineering(run_dir: Path) -> dict:
    validate_authority(run_dir)
    summary_path = run_dir / "execution_summary_v1.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    exact = {
        "phase": "engineering", "fresh_preprocessing_calls": 40,
        "direct_lfe_acquisitions": 40, "directions_constructed": 640,
        "trajectory_rows": 24, "scheduler_steps": 24,
        "raw_identity_lfe_or_direction_tensor_files": 0,
    }
    if summary.get("status") != SUMMARY_STATUS or any(summary.get(key) != value for key, value in exact.items()):
        raise EngineeringVerificationError("engineering summary count or status drift")
    elapsed = float(summary.get("elapsed_gpu_hours", -1))
    if not 0 <= elapsed <= 2.0 or float(summary.get("phase_gpu_hours_ceiling", 0)) != 2.0:
        raise EngineeringVerificationError("engineering elapsed time or ceiling drift")

    observed = read_rows(run_dir / "trajectory_status_v1.csv")
    expected = expected_rows()
    plan_keys = tuple(expected[0])
    if len(observed) != 24 or [tuple(row[key] for key in plan_keys) for row in observed] != [tuple(row[key] for key in plan_keys) for row in expected]:
        raise EngineeringVerificationError("trajectory plan or order mismatch")
    required = {
        "status", "initial_denoising_input_sha256", "spatial_reference_route_sha256",
        "hidden_shape", "hidden_dtype", "hidden_device_type", "lfe_hook_calls",
        "private_latent_persisted", "decoded_media_persisted",
    }
    if any(not required.issubset(row) for row in observed):
        raise EngineeringVerificationError("trajectory scalar schema drift")
    by_task: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in observed:
        if row["status"] != "COMPLETE" or row["lfe_hook_calls"] != "1":
            raise EngineeringVerificationError("trajectory completion or LFE hook count drift")
        if row["private_latent_persisted"] != "False" or row["decoded_media_persisted"] != "False":
            raise EngineeringVerificationError("engineering persisted latent or decoded media")
        if row["hidden_device_type"] != "cuda" or row["hidden_dtype"] != "torch.bfloat16":
            raise EngineeringVerificationError("engineering hidden device or dtype drift")
        by_task[row["planned_task_id"]].append(row)
    if len(by_task) != 8 or any(len(rows) != 3 for rows in by_task.values()):
        raise EngineeringVerificationError("engineering task-condition crossing drift")
    invariant_keys = (
        "initial_denoising_input_sha256", "spatial_reference_route_sha256",
        "hidden_shape", "hidden_dtype", "hidden_device_type",
    )
    for task, rows in by_task.items():
        if len({tuple(row[key] for key in invariant_keys) for row in rows}) != 1:
            raise EngineeringVerificationError(f"cross-condition invariant mismatch: {task}")

    diagnostics = read_rows(run_dir / "direction_scalar_diagnostics_v1.csv")
    expected_keys = {
        (attribute, f"{PREFIX[attribute]}_{pair_index:02d}", str(token))
        for attribute in ATTRIBUTES for pair_index in range(1, 11) for token in range(32)
    }
    observed_keys = {(row["attribute"], row["formal_pair_id"], row["token_index"]) for row in diagnostics}
    if len(diagnostics) != 640 or observed_keys != expected_keys:
        raise EngineeringVerificationError("direction diagnostic key universe drift")
    max_norm_error = 0.0
    max_abs_dot = 0.0
    for row in diagnostics:
        if row["training_pairs"] != "9" or row["held_pair_excluded"] != "True":
            raise EngineeringVerificationError("held-pair-out diagnostic drift")
        pre_norm = finite(row["pre_normalization_direction_norm"], "pre-normalization norm")
        direction_norm = finite(row["unit_direction_norm"], "direction norm")
        sham_norm = finite(row["sham_direction_norm"], "sham norm")
        dot = finite(row["direction_sham_dot"], "direction-sham dot")
        attempt = int(row["sham_attempt"])
        if pre_norm <= 1e-12 or not 0 <= attempt < 16:
            raise EngineeringVerificationError("degenerate direction or sham attempt drift")
        max_norm_error = max(max_norm_error, abs(direction_norm - 1.0), abs(sham_norm - 1.0))
        max_abs_dot = max(max_abs_dot, abs(dot))
    if max_norm_error > 1e-6 or max_abs_dot > 1e-6:
        raise EngineeringVerificationError("direction norm or sham orthogonality tolerance failure")

    forbidden_suffixes = {".pt", ".pth", ".npy", ".npz", ".safetensors", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".avi", ".mov"}
    forbidden_files = [path.name for path in run_dir.iterdir() if path.is_file() and path.suffix.lower() in forbidden_suffixes]
    if forbidden_files:
        raise EngineeringVerificationError(f"forbidden engineering artifact: {forbidden_files}")
    commit = subprocess.check_output(["git", "-C", str(CONSISID_REPO), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(["git", "-C", str(CONSISID_REPO), "status", "--porcelain=v1"], text=True)
    if commit != CONSISID_COMMIT or status:
        raise EngineeringVerificationError("ConsisID state drift")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_CONTROLLED_INTERVENTION_ENGINEERING_VERIFICATION",
        "engineering_pairs_by_frozen_hash": {key: list(value) for key, value in selected_pairs().items()},
        "formal_units_acquired": 40, "directions_verified": 640,
        "engineering_tasks": 8, "one_step_condition_executions": 24,
        "scheduler_steps": 24, "cross_condition_input_invariants_verified": 8,
        "max_direction_or_sham_unit_norm_abs_error": max_norm_error,
        "max_abs_direction_sham_dot": max_abs_dot,
        "raw_tensor_files": 0, "media_or_latent_files": 0,
        "reference_images_decoded_by_verifier": False, "model_loaded_by_verifier": False,
        "gpu_used_by_verifier": False, "outcomes_opened": False,
        "scientific_generation_authorized": False, "network_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify_engineering(args.run_dir)
    partial = args.output.with_suffix(args.output.suffix + ".partial")
    if args.output.exists() or partial.exists():
        raise EngineeringVerificationError("refusing to overwrite verifier output")
    partial.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    partial.replace(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EngineeringVerificationError, subprocess.SubprocessError, OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
