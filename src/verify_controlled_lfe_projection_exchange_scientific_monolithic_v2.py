#!/usr/bin/env python3
"""CPU-only verifier for prospective scientific monolithic run-002 outputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import controlled_lfe_projection_exchange_protocol_v1 as protocol
import run_controlled_lfe_projection_exchange_monolithic_v2 as runner

SUMMARY_STATUS = "COMPLETE_PENDING_INDEPENDENT_PHASE_VERIFICATION"
PASS_STATUS = "PASS_INDEPENDENT_CONTROLLED_INTERVENTION_SCIENTIFIC_MONOLITHIC_RUN_002_VERIFICATION"
PERSISTED_PLAN_FIELDS = (
    "planned_task_id", "planned_unit_id", "formal_pair_id", "attribute", "role",
    "seed_index", "seed", "condition_position", "condition", "scheduler_positions",
)


class MonolithicRun002VerificationError(RuntimeError):
    """Raised when run-002 authority, schema, or artifacts drift."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path: Path, *, size: int, digest: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise MonolithicRun002VerificationError(f"missing regular file: {path}")
    if path.stat().st_size != size or sha256(path) != digest:
        raise MonolithicRun002VerificationError(f"file binding mismatch: {path}")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def validate_authority(auth_file: Path, run_dir: Path, private_root: Path) -> dict:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise MonolithicRun002VerificationError("verifier must start CUDA-hidden and torch-free")
    if auth_file.resolve() != runner.ACTIVE_AUTH.resolve():
        raise MonolithicRun002VerificationError("active authorization path drift")
    auth = protocol.read_json(auth_file)
    if (
        auth.get("status") != runner.ACTIVE_STATUS
        or auth.get("execution_explicitly_approved") is not True
        or auth.get("phase") != "scientific"
        or auth.get("scientific_run_id") != "monolithic_run_002"
        or float(auth.get("phase_gpu_hours_ceiling", 0)) != 72.0
    ):
        raise MonolithicRun002VerificationError("run-002 execution authority drift")
    if Path(str(auth.get("runtime_output_dir", ""))).resolve() != run_dir.resolve():
        raise MonolithicRun002VerificationError("scalar output path drift")
    if Path(str(auth.get("private_latent_output_dir", ""))).resolve() != private_root.resolve():
        raise MonolithicRun002VerificationError("private output path drift")
    researcher_execution = protocol.bound(
        auth.get("researcher_execution_authorization", {}), "researcher run-002 execution authorization"
    )
    if (
        researcher_execution.resolve() != runner.RESEARCHER_EXEC_AUTH.resolve()
        or protocol.read_json(researcher_execution).get("status") != runner.RESEARCHER_EXEC_STATUS
    ):
        raise MonolithicRun002VerificationError("researcher run-002 execution authority drift")
    freeze = protocol.bound(auth.get("preparation_freeze", {}), "run-002 preparation freeze")
    if freeze.resolve() != runner.PREPARATION_FREEZE.resolve() or protocol.read_json(freeze).get("status") != runner.PREPARATION_STATUS:
        raise MonolithicRun002VerificationError("preparation freeze drift")
    for key, expected_path, expected_status in runner.PREREQUISITES:
        observed_path = protocol.bound(auth.get(key, {}), key)
        if observed_path.resolve() != expected_path.resolve() or protocol.read_json(observed_path).get("status") != expected_status:
            raise MonolithicRun002VerificationError(f"prerequisite drift: {key}")
    if protocol.bound(auth.get("formal_generation_master", {}), "formal generation master").resolve() != runner.FORMAL_MASTER.resolve():
        raise MonolithicRun002VerificationError("formal generation master drift")
    if protocol.bound(auth.get("formal_task_binding_manifest", {}), "formal task binding manifest").resolve() != runner.FORMAL_BINDINGS.resolve():
        raise MonolithicRun002VerificationError("formal task binding manifest drift")
    if (
        auth.get("prior_execution_reused") is not False
        or auth.get("seed_1_shard_merged") is not False
        or auth.get("prior_direction_evidence_reused") is not False
    ):
        raise MonolithicRun002VerificationError("historical non-reuse boundary drift")
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
    if any(authority.get(key) is not True for key in required) or any(
        authority.get(key) is not False for key in forbidden
    ):
        raise MonolithicRun002VerificationError("run-002 authority boundary incomplete")
    items = auth.get("code", {})
    if set(items) != set(runner.CODE_PATHS):
        raise MonolithicRun002VerificationError("authorized code universe drift")
    for label, path in runner.CODE_PATHS.items():
        if protocol.bound(items[label], label).resolve() != path.resolve():
            raise MonolithicRun002VerificationError(f"code binding drift: {label}")
    if subprocess.check_output(["git", "-C", str(runner.CONSISID), "rev-parse", "HEAD"], text=True).strip() != runner.CONSISID_COMMIT:
        raise MonolithicRun002VerificationError("ConsisID HEAD drift")
    if subprocess.check_output(["git", "-C", str(runner.CONSISID), "status", "--short"], text=True):
        raise MonolithicRun002VerificationError("ConsisID worktree drift")
    return auth


def verify_outputs(run_dir: Path, private_root: Path) -> dict[str, object]:
    summary = json.loads((run_dir / "execution_summary_v2.json").read_text(encoding="utf-8"))
    exact = {
        "schema_version": 2, "phase": "scientific", "scientific_run_id": "monolithic_run_002",
        "fresh_preprocessing_calls": 40, "direct_lfe_acquisitions": 40,
        "acquisition_units": 40, "directions_constructed": 640,
        "direction_scalar_hash_pairs": 640, "trajectory_rows": 480,
        "scheduler_steps": 24000, "raw_identity_lfe_or_direction_tensor_files": 0,
        "single_acquisition_transaction": True, "four_seeds_same_process": True,
        "scientific_seed_indices": [1, 2, 3, 4], "scientific_seeds": list(protocol.SEEDS),
        "conditions_co_resident": list(protocol.CONDITIONS),
        "identity_handles_cpu": True, "acquisition_inference_mode": True,
        "face_models_released_before_pipeline_load": True,
        "pipeline_loaded_after_complete_acquisition": True,
    }
    if summary.get("status") != SUMMARY_STATUS or any(summary.get(key) != value for key, value in exact.items()):
        raise MonolithicRun002VerificationError("monolithic run-002 summary drift")
    elapsed = float(summary.get("elapsed_gpu_hours", -1))
    if not 0 <= elapsed <= 72 or float(summary.get("phase_gpu_hours_ceiling", 0)) != 72.0:
        raise MonolithicRun002VerificationError("run-002 time ceiling drift")

    observed = _read_csv(run_dir / "trajectory_status_v2.csv")
    expected = protocol.execution_plan()
    if (
        len(observed) != 480
        or [tuple(row[key] for key in PERSISTED_PLAN_FIELDS) for row in observed]
        != [tuple(str(row[key]) for key in PERSISTED_PLAN_FIELDS) for row in expected]
    ):
        raise MonolithicRun002VerificationError("runtime-persisted plan or order drift")
    required = {
        "status", "initial_denoising_input_sha256", "spatial_reference_route_sha256",
        "hidden_shape", "hidden_dtype", "hidden_device_type", "lfe_hook_calls",
        "private_latent_path", "private_latent_bytes", "private_latent_sha256",
        "decoded_media_persisted",
    }
    paths: set[Path] = set()
    by_task: dict[str, list[dict[str, str]]] = defaultdict(list)
    total_bytes = 0
    for row in observed:
        if not required.issubset(row) or row["status"] != "COMPLETE" or row["lfe_hook_calls"] != "50":
            raise MonolithicRun002VerificationError("trajectory completion or hook schema drift")
        if row["hidden_device_type"] != "cuda" or row["hidden_dtype"] != "torch.bfloat16" or row["decoded_media_persisted"] != "False":
            raise MonolithicRun002VerificationError("trajectory device, dtype, or media drift")
        path = Path(row["private_latent_path"])
        expected_name = protocol.sha256_text(
            f"{protocol.NAMESPACE}|monolithic_run_002|private_latent|{row['planned_task_id']}|{row['condition']}"
        )[:32] + ".safetensors"
        if path.parent.resolve() != private_root.resolve() or path.name != expected_name or path in paths:
            raise MonolithicRun002VerificationError("private latent path or pseudonym drift")
        verify_file(path, size=int(row["private_latent_bytes"]), digest=row["private_latent_sha256"])
        paths.add(path)
        total_bytes += path.stat().st_size
        by_task[row["planned_task_id"]].append(row)
    actual_private = set(private_root.iterdir())
    if actual_private != paths or len(paths) != 480 or any(
        not path.is_file() or path.is_symlink() or path.suffix != ".safetensors" for path in paths
    ):
        raise MonolithicRun002VerificationError("private latent universe drift")
    invariant_keys = (
        "initial_denoising_input_sha256", "spatial_reference_route_sha256",
        "hidden_shape", "hidden_dtype", "hidden_device_type",
    )
    if len(by_task) != 160 or any(
        len(rows) != 3 or len({tuple(row[key] for key in invariant_keys) for row in rows}) != 1
        for rows in by_task.values()
    ):
        raise MonolithicRun002VerificationError("cross-condition input invariant drift")

    acquisitions = _read_csv(run_dir / "acquisition_scalar_hashes_v2.csv")
    expected_units = {
        protocol.unit_id(attribute, pair, role)
        for attribute in protocol.ATTRIBUTES
        for pair in protocol.pair_ids(attribute)
        for role in protocol.ROLES
    }
    if len(acquisitions) != 40 or {row.get("planned_unit_id") for row in acquisitions} != expected_units or any(
        row.get("canonical_dtype") != "float32" or not _is_sha256(row.get("lfe_sha256", ""))
        for row in acquisitions
    ):
        raise MonolithicRun002VerificationError("acquisition scalar hash evidence drift")

    directions = _read_csv(run_dir / "direction_scalar_diagnostics_v2.csv")
    expected_direction_keys = {
        (attribute, pair, token)
        for attribute in protocol.ATTRIBUTES
        for pair in protocol.pair_ids(attribute)
        for token in range(protocol.LFE_TOKENS)
    }
    try:
        direction_keys = {
            (row.get("attribute"), row.get("formal_pair_id"), int(row.get("token_index", -1)))
            for row in directions
        }
        numerical_ok = all(
            row.get("held_pair_excluded") == "True"
            and row.get("training_pairs") == "9"
            and abs(float(row.get("unit_direction_norm", "nan")) - 1.0) <= protocol.DIRECTION_ATOL
            and abs(float(row.get("sham_direction_norm", "nan")) - 1.0) <= protocol.DIRECTION_ATOL
            and abs(float(row.get("direction_sham_dot", "nan"))) <= protocol.DIRECTION_ATOL
            and _is_sha256(row.get("direction_sha256", ""))
            and _is_sha256(row.get("sham_direction_sha256", ""))
            for row in directions
        )
    except ValueError as error:
        raise MonolithicRun002VerificationError("direction diagnostic numeric schema drift") from error
    if len(directions) != 640 or direction_keys != expected_direction_keys or not numerical_ok:
        raise MonolithicRun002VerificationError("direction/sham scalar evidence drift")

    allowed = {
        "execution_summary_v2.json", "trajectory_status_v2.csv",
        "acquisition_scalar_hashes_v2.csv", "direction_scalar_diagnostics_v2.csv",
        "independent_verification_v2.json",
    }
    if any(
        not path.is_file() or path.is_symlink() or path.name not in allowed
        for path in run_dir.iterdir()
    ):
        raise MonolithicRun002VerificationError("unexpected scalar artifact")
    return {
        "schema_version": 2,
        "status": PASS_STATUS,
        "scientific_run_id": "monolithic_run_002",
        "persisted_plan_fields_verified": list(PERSISTED_PLAN_FIELDS),
        "nonpersisted_redundant_plan_fields_not_required": ["trajectory_kind", "formal_binding_status"],
        "scientific_trajectories": 480, "scheduler_steps": 24000,
        "formal_units": 40, "source_tasks": 160,
        "single_acquisition_transaction_verified": True,
        "four_seeds_same_process_verified": True,
        "cross_condition_input_invariants_verified": 160,
        "acquisition_scalar_hashes": 40, "direction_scalar_hash_pairs": 640,
        "private_final_latent_files": 480, "private_final_latent_bytes": total_bytes,
        "decoded_media_files": 0, "raw_identity_lfe_or_direction_files": 0,
        "gpu_hours": elapsed, "outcomes_opened": False,
        "model_loaded_by_verifier": False, "gpu_used_by_verifier": False, "network_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--private-latent-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    validate_authority(args.authorization_file, args.run_dir, args.private_latent_dir)
    result = verify_outputs(args.run_dir, args.private_latent_dir)
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (MonolithicRun002VerificationError, protocol.ControlledInterventionProtocolError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
