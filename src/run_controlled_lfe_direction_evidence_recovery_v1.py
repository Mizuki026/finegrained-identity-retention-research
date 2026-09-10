#!/usr/bin/env python3
"""Fail-closed single-GPU recovery of missing Seed 1 direction scalar hashes."""
from __future__ import annotations

import argparse
import gc
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import controlled_lfe_projection_exchange_protocol_v1 as protocol

REPO = Path(__file__).resolve().parents[1]
GOV = REPO / "governance/mechanism_controlled_intervention_scientific_seed_1_direction_recovery_v1"
AUTHORIZATION = GOV / "direction_evidence_recovery_run_001_authorization_v1.json"
STATUS = "SINGLE_GPU_SCIENTIFIC_SEED_1_DIRECTION_EVIDENCE_RECOVERY_AUDIT_AUTHORIZED"
OUTPUT = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_direction_recovery/seed_1_run_001")
CONSISID = Path("/root/autodl-tmp/consisid-smoketest/ConsisID")
CONSISID_HEAD = "60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
CODE_PATHS = {
    "protocol": REPO / "src/controlled_lfe_projection_exchange_protocol_v1.py",
    "instrumentation": REPO / "src/controlled_lfe_projection_exchange_instrumentation_v1.py",
    "base_runtime": REPO / "src/controlled_lfe_projection_exchange_runtime_v1.py",
    "recovery_math": REPO / "src/controlled_lfe_direction_evidence_recovery_v1.py",
    "recovery_runner": REPO / "src/run_controlled_lfe_direction_evidence_recovery_v1.py",
    "recovery_verifier": REPO / "src/verify_controlled_lfe_direction_evidence_recovery_v1.py",
}


class DirectionEvidenceRecoveryRunnerError(RuntimeError):
    """Raised before or during a non-conforming recovery audit."""


def _git(repository: Path, *args: str) -> str:
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(repository), *args], text=True).strip()


def validate_active(auth_file: Path, output_dir: Path) -> dict:
    auth = protocol.read_json(auth_file)
    if auth_file.resolve() != AUTHORIZATION.resolve() or auth.get("status") != STATUS:
        raise DirectionEvidenceRecoveryRunnerError("direction recovery authorization drift")
    if auth.get("execution_explicitly_approved") is not True or auth.get("gpu_execution_authorized") is not True:
        raise DirectionEvidenceRecoveryRunnerError("single-GPU recovery execution is not explicitly authorized")
    if auth.get("scientific_shard_id") != "seed_1" or auth.get("recovery_run_id") != "run_001":
        raise DirectionEvidenceRecoveryRunnerError("recovery transaction identity drift")
    if Path(str(auth.get("runtime_output_dir", ""))).resolve() != output_dir.resolve() or output_dir.resolve() != OUTPUT.resolve():
        raise DirectionEvidenceRecoveryRunnerError("recovery output path drift")
    if output_dir.exists() or output_dir.with_name(output_dir.name + ".partial").exists():
        raise DirectionEvidenceRecoveryRunnerError("recovery output or staging path already exists")
    for label, expected in CODE_PATHS.items():
        if protocol.bound(auth.get("code", {}).get(label, {}), label).resolve() != expected.resolve():
            raise DirectionEvidenceRecoveryRunnerError(f"recovery code path drift: {label}")
    for label in (
        "formal_generation_master", "formal_task_binding_manifest", "executed_acquisition_hashes",
        "executed_direction_diagnostics", "schema_correction_abort_freeze",
    ):
        protocol.bound(auth.get(label, {}), label)
    authority = auth.get("authority", {})
    required = (
        "single_gpu_40_unit_acquisition", "exact_40_of_40_lfe_hash_gate",
        "deterministic_640_direction_and_sham_reconstruction", "scalar_hash_persistence",
    )
    forbidden = (
        "trajectory_execution", "generation_pipeline_loading", "latent_or_media_generation",
        "private_latent_modification", "decode", "outcome_access", "analysis",
    )
    if any(authority.get(key) is not True for key in required) or any(authority.get(key) is not False for key in forbidden):
        raise DirectionEvidenceRecoveryRunnerError("recovery authority boundary drift")
    if float(auth.get("phase_gpu_hours_ceiling", 0)) != 2.0:
        raise DirectionEvidenceRecoveryRunnerError("recovery GPU ceiling must be exactly 2 hours")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0" or os.environ.get("WORLD_SIZE") != "1" or os.environ.get("LOCAL_WORLD_SIZE") != "1":
        raise DirectionEvidenceRecoveryRunnerError("single-GPU environment binding mismatch")
    if _git(REPO, "branch", "--show-current") != "main" or _git(REPO, "status", "--short"):
        raise DirectionEvidenceRecoveryRunnerError("recovery requires clean main research worktree")
    if _git(CONSISID, "rev-parse", "HEAD") != CONSISID_HEAD or _git(CONSISID, "status", "--short"):
        raise DirectionEvidenceRecoveryRunnerError("ConsisID state drift")
    return auth


def execute(auth_file: Path, output_dir: Path) -> dict:
    auth = validate_active(auth_file, output_dir)
    started = time.monotonic()
    deadline = started + 2 * 3600
    from controlled_lfe_direction_evidence_recovery_v1 import recover_scalar_hash_rows
    from controlled_lfe_projection_exchange_runtime_v1 import prepare_active_runtime

    bindings, adapter = prepare_active_runtime(auth, "recovery")
    original_rows = protocol.read_csv(protocol.bound(auth["executed_acquisition_hashes"], "executed acquisition hashes"))
    expected_hashes = {row["planned_unit_id"]: row["lfe_sha256"] for row in original_rows}
    tensors: dict[str, object] = {}
    metadata: dict[str, dict[str, str]] = {}
    try:
        for unit in sorted(bindings):
            if time.monotonic() >= deadline:
                raise DirectionEvidenceRecoveryRunnerError("GPU-hour ceiling reached during recovery acquisition")
            acquired = adapter.acquire(unit, bindings[unit])
            tensors[unit] = acquired["lfe"]
            metadata[unit] = {
                "attribute": str(bindings[unit]["attribute"]),
                "formal_pair_id": str(bindings[unit]["formal_pair_id"]),
                "role": str(bindings[unit]["role"]),
            }
            del acquired
        acquisition_rows, direction_rows = recover_scalar_hash_rows(tensors, metadata, expected_hashes)
        staging = output_dir.with_name(output_dir.name + ".partial")
        staging.mkdir(parents=True, exist_ok=False)
        protocol.atomic_csv(staging / "recovered_acquisition_hash_comparison_v1.csv", tuple(acquisition_rows[0]), acquisition_rows)
        protocol.atomic_csv(staging / "recovered_direction_scalar_hashes_v1.csv", tuple(direction_rows[0]), direction_rows)
        summary = {
            "schema_version": 1,
            "status": "COMPLETE_PENDING_INDEPENDENT_DIRECTION_EVIDENCE_RECOVERY_VERIFICATION",
            "scientific_shard_id": "seed_1", "recovery_run_id": "run_001",
            "recovered_acquisitions": 40, "exact_lfe_hash_matches": 40,
            "recovered_direction_hash_pairs": 640,
            "generation_pipeline_loaded": False, "trajectories_executed": 0,
            "latents_or_media_generated": 0, "private_latents_modified": 0,
            "elapsed_gpu_hours": (time.monotonic() - started) / 3600,
            "phase_gpu_hours_ceiling": 2.0,
        }
        protocol.atomic_json(staging / "recovery_summary_v1.json", summary)
        staging.replace(output_dir)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return summary
    finally:
        tensors.clear()
        if hasattr(adapter, "close"):
            adapter.close()
        gc.collect()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    execute(args.authorization_file, args.output_dir)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DirectionEvidenceRecoveryRunnerError, protocol.ControlledInterventionProtocolError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
