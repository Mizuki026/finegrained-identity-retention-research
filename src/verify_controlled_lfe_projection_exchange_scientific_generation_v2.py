#!/usr/bin/env python3
"""Corrected CPU-only verifier for the runtime-persisted seed-shard schema."""
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

REPO = Path(__file__).resolve().parents[1]
SHARDING_DIR = REPO / "governance/mechanism_controlled_intervention_scientific_seed_sharding_v1"
SHARDING_FREEZE = SHARDING_DIR / "scientific_seed_sharding_preparation_freeze_v1.json"
CONSISID = Path("/root/autodl-tmp/consisid-smoketest/ConsisID")
CONSISID_COMMIT = "60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
AUTH_STATUS = "CONTROLLED_INTERVENTION_SCIENTIFIC_SEED_SHARD_GPU_EXECUTION_AUTHORIZED"
RESEARCHER_STATUS = "CONTROLLED_INTERVENTION_SCIENTIFIC_SEED_SHARD_GPU_EXECUTION_AUTHORIZED"
AMENDMENT_STATUS = "FROZEN_PASS_PROSPECTIVE_FOUR_SEED_SHARD_PREPARATION_ONLY_NO_GPU_EXECUTION"
ENGINEERING_STATUS = "FROZEN_PASS_COMPLETE_INDEPENDENTLY_VERIFIED_SINGLE_GPU_ENGINEERING"
SUMMARY_STATUS = "COMPLETE_PENDING_INDEPENDENT_PHASE_VERIFICATION"
CORRECTION_DIR = REPO / "governance/mechanism_controlled_intervention_scientific_seed_1_verifier_schema_correction_v1"
CORRECTION_AUTHORIZATION = CORRECTION_DIR / "researcher_verifier_schema_correction_authorization_v1.json"
CORRECTION_STATUS = "SCIENTIFIC_SEED_1_SHARD_VERIFIER_PERSISTED_SCHEMA_CORRECTION_CPU_ONLY_AUTHORIZED"
PERSISTED_PLAN_FIELDS = (
    "planned_task_id", "planned_unit_id", "formal_pair_id", "attribute", "role",
    "seed_index", "seed", "condition_position", "condition", "scheduler_positions",
)


class ScientificGenerationVerificationError(RuntimeError):
    """Raised when scientific seed-shard authority or artifacts drift."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path: Path, item: dict) -> None:
    if path.is_symlink() or not path.is_file():
        raise ScientificGenerationVerificationError(f"missing regular binding: {path}")
    if path.stat().st_size != int(item.get("bytes", -1)) or sha256(path) != item.get("sha256"):
        raise ScientificGenerationVerificationError(f"binding mismatch: {path}")


def resolve(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO / path


def validate_correction_authority(correction_file: Path, original_auth_file: Path, run_dir: Path) -> dict:
    if correction_file.resolve() != CORRECTION_AUTHORIZATION.resolve():
        raise ScientificGenerationVerificationError("correction authorization path drift")
    correction = json.loads(correction_file.read_text(encoding="utf-8"))
    if correction.get("status") != CORRECTION_STATUS or correction.get("cpu_only") is not True:
        raise ScientificGenerationVerificationError("verifier correction authority drift")
    if correction.get("gpu_execution_authorized") is not False or correction.get("regeneration_authorized") is not False:
        raise ScientificGenerationVerificationError("correction authority enables GPU execution or regeneration")
    original_item = correction.get("original_execution_authorization", {})
    original_path = resolve(str(original_item.get("path", "")))
    verify_file(original_path, original_item)
    if original_path.resolve() != original_auth_file.resolve():
        raise ScientificGenerationVerificationError("original execution authorization path drift")
    original_verifier = correction.get("failed_original_verifier", {})
    verify_file(resolve(str(original_verifier.get("path", ""))), original_verifier)
    corrected_verifier = correction.get("corrected_verifier", {})
    corrected_path = resolve(str(corrected_verifier.get("path", "")))
    verify_file(corrected_path, corrected_verifier)
    if corrected_path.resolve() != Path(__file__).resolve():
        raise ScientificGenerationVerificationError("corrected verifier self-binding drift")
    runtime = correction.get("frozen_runtime_artifacts", {})
    expected_names = {
        "execution_summary_v1.json", "trajectory_status_v1.csv",
        "acquisition_scalar_hashes_v1.csv", "direction_scalar_diagnostics_v1.csv",
    }
    if set(runtime) != expected_names:
        raise ScientificGenerationVerificationError("frozen runtime artifact universe drift")
    for name, item in runtime.items():
        path = resolve(str(item.get("path", "")))
        verify_file(path, item)
        if path.resolve() != (run_dir / name).resolve():
            raise ScientificGenerationVerificationError(f"runtime artifact path drift: {name}")
    return correction


def validate_authority(auth_file: Path, run_dir: Path, private_root: Path) -> dict:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise ScientificGenerationVerificationError("verifier must start CUDA-hidden and torch-free")
    auth = json.loads(auth_file.read_text(encoding="utf-8"))
    try:
        seed_index = int(auth.get("scientific_seed_index"))
    except (TypeError, ValueError) as error:
        raise ScientificGenerationVerificationError("scientific seed index missing") from error
    if seed_index not in range(1, 5):
        raise ScientificGenerationVerificationError("scientific seed index outside 1..4")
    shard_id = f"seed_{seed_index}"
    if (
        auth_file.resolve() != (SHARDING_DIR / f"scientific_{shard_id}_execution_authorization_v1.json").resolve()
        or auth.get("status") != AUTH_STATUS
        or auth.get("phase") != "scientific"
        or auth.get("execution_explicitly_approved") is not True
        or auth.get("scientific_seed") != protocol.SEEDS[seed_index - 1]
        or auth.get("scientific_shard_id") != shard_id
        or auth.get("shard_family_id") != "controlled_lfe_projection_exchange_scientific_seed_shards_v1"
    ):
        raise ScientificGenerationVerificationError("scientific seed-shard authority drift")
    if Path(auth.get("runtime_output_dir", "")).resolve() != run_dir.resolve():
        raise ScientificGenerationVerificationError("scalar output path drift")
    if Path(auth.get("private_latent_output_dir", "")).resolve() != private_root.resolve():
        raise ScientificGenerationVerificationError("private output path drift")
    researcher_item = auth.get("researcher_shard_execution_authorization", {})
    researcher_path = resolve(str(researcher_item.get("path", "")))
    verify_file(researcher_path, researcher_item)
    if json.loads(researcher_path.read_text(encoding="utf-8")).get("status") != RESEARCHER_STATUS:
        raise ScientificGenerationVerificationError("researcher shard execution authority drift")
    amendment_item = auth.get("seed_sharding_preparation_freeze", {})
    amendment_path = resolve(str(amendment_item.get("path", "")))
    verify_file(amendment_path, amendment_item)
    if amendment_path.resolve() != SHARDING_FREEZE.resolve() or json.loads(amendment_path.read_text()).get("status") != AMENDMENT_STATUS:
        raise ScientificGenerationVerificationError("seed-sharding amendment freeze drift")
    engineering_item = auth.get("engineering_freeze", {})
    engineering_path = resolve(str(engineering_item.get("path", "")))
    verify_file(engineering_path, engineering_item)
    if json.loads(engineering_path.read_text()).get("status") != ENGINEERING_STATUS:
        raise ScientificGenerationVerificationError("engineering freeze is not pass")
    for item in auth.get("code", {}).values():
        verify_file(resolve(str(item.get("path", ""))), item)
    verifier_item = auth.get("scientific_generation_verifier", {})
    verify_file(resolve(str(verifier_item.get("path", ""))), verifier_item)
    if float(auth.get("phase_gpu_hours_ceiling", 0)) != 18.0:
        raise ScientificGenerationVerificationError("seed-shard GPU ceiling drift")
    if subprocess.check_output(["git", "-C", str(CONSISID), "rev-parse", "HEAD"], text=True).strip() != CONSISID_COMMIT:
        raise ScientificGenerationVerificationError("ConsisID HEAD drift")
    if subprocess.check_output(["git", "-C", str(CONSISID), "status", "--short"], text=True):
        raise ScientificGenerationVerificationError("ConsisID worktree drift")
    return auth


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def verify_outputs(run_dir: Path, private_root: Path, seed_index: int) -> dict:
    if seed_index not in range(1, 5):
        raise ScientificGenerationVerificationError("invalid seed shard index")
    seed = protocol.SEEDS[seed_index - 1]
    shard_id = f"seed_{seed_index}"
    summary = json.loads((run_dir / "execution_summary_v1.json").read_text(encoding="utf-8"))
    exact = {
        "phase": "scientific", "fresh_preprocessing_calls": 40, "direct_lfe_acquisitions": 40,
        "directions_constructed": 640, "trajectory_rows": 120, "scheduler_steps": 6000,
        "raw_identity_lfe_or_direction_tensor_files": 0,
        "shard_family_id": "controlled_lfe_projection_exchange_scientific_seed_shards_v1",
        "scientific_shard_id": shard_id, "scientific_seed_index": seed_index,
        "scientific_seed": seed, "seed_complete_shard": True,
        "conditions_co_resident": list(protocol.CONDITIONS),
    }
    if summary.get("status") != SUMMARY_STATUS or any(summary.get(key) != value for key, value in exact.items()):
        raise ScientificGenerationVerificationError("scientific seed-shard summary drift")
    elapsed = float(summary.get("elapsed_gpu_hours", -1))
    if not 0 <= elapsed <= 18 or float(summary.get("phase_gpu_hours_ceiling", 0)) != 18:
        raise ScientificGenerationVerificationError("scientific seed-shard time ceiling drift")
    observed = _read_csv(run_dir / "trajectory_status_v1.csv")
    expected = [row for row in protocol.execution_plan() if int(row["seed_index"]) == seed_index]
    plan_keys = PERSISTED_PLAN_FIELDS
    if len(observed) != 120 or [tuple(row[key] for key in plan_keys) for row in observed] != [tuple(str(row[key]) for key in plan_keys) for row in expected]:
        raise ScientificGenerationVerificationError("scientific seed-shard plan or order drift")
    required = {
        "status", "initial_denoising_input_sha256", "spatial_reference_route_sha256", "hidden_shape",
        "hidden_dtype", "hidden_device_type", "lfe_hook_calls", "private_latent_path",
        "private_latent_bytes", "private_latent_sha256", "decoded_media_persisted",
    }
    by_task: dict[str, list[dict[str, str]]] = defaultdict(list)
    paths: set[Path] = set()
    total_bytes = 0
    for row in observed:
        if not required.issubset(row) or row["status"] != "COMPLETE" or row["lfe_hook_calls"] != "50":
            raise ScientificGenerationVerificationError("trajectory completion or hook drift")
        if row["hidden_device_type"] != "cuda" or row["hidden_dtype"] != "torch.bfloat16" or row["decoded_media_persisted"] != "False":
            raise ScientificGenerationVerificationError("trajectory dtype/device/media drift")
        path = Path(row["private_latent_path"])
        expected_name = protocol.sha256_text(f"{protocol.NAMESPACE}|private_latent|{row['planned_task_id']}|{row['condition']}")[:32] + ".safetensors"
        if path.parent.resolve() != private_root.resolve() or path.name != expected_name or path in paths:
            raise ScientificGenerationVerificationError("private latent path or pseudonym drift")
        verify_file(path, {"bytes": row["private_latent_bytes"], "sha256": row["private_latent_sha256"]})
        paths.add(path)
        total_bytes += path.stat().st_size
        by_task[row["planned_task_id"]].append(row)
    actual_private = {path for path in private_root.iterdir() if path.is_file()}
    if actual_private != paths or len(paths) != 120 or any(path.suffix != ".safetensors" for path in actual_private):
        raise ScientificGenerationVerificationError("private latent universe drift")
    invariant_keys = ("initial_denoising_input_sha256", "spatial_reference_route_sha256", "hidden_shape", "hidden_dtype", "hidden_device_type")
    if len(by_task) != 40 or any(len(rows) != 3 or len({tuple(row[key] for key in invariant_keys) for row in rows}) != 1 for rows in by_task.values()):
        raise ScientificGenerationVerificationError("cross-condition invariant drift")
    acquisitions = _read_csv(run_dir / "acquisition_scalar_hashes_v1.csv")
    expected_units = {protocol.unit_id(attribute, pair, role) for attribute in protocol.ATTRIBUTES for pair in protocol.pair_ids(attribute) for role in protocol.ROLES}
    if len(acquisitions) != 40 or {row.get("planned_unit_id") for row in acquisitions} != expected_units or any(row.get("canonical_dtype") != "float32" or not _is_sha256(row.get("lfe_sha256", "")) for row in acquisitions):
        raise ScientificGenerationVerificationError("acquisition scalar hash evidence drift")
    directions = _read_csv(run_dir / "direction_scalar_diagnostics_v1.csv")
    direction_keys = {(row.get("attribute"), row.get("formal_pair_id"), int(row.get("token_index", -1))) for row in directions}
    expected_direction_keys = {(attribute, pair, token) for attribute in protocol.ATTRIBUTES for pair in protocol.pair_ids(attribute) for token in range(protocol.LFE_TOKENS)}
    if len(directions) != 640 or direction_keys != expected_direction_keys or any(not _is_sha256(row.get("direction_sha256", "")) or not _is_sha256(row.get("sham_direction_sha256", "")) for row in directions):
        raise ScientificGenerationVerificationError("direction scalar hash evidence drift")
    allowed = {"trajectory_status_v1.csv", "execution_summary_v1.json", "acquisition_scalar_hashes_v1.csv", "direction_scalar_diagnostics_v1.csv", "independent_verification_v1.json", "independent_verification_v2.json"}
    if any(path.name not in allowed for path in run_dir.iterdir() if path.is_file()):
        raise ScientificGenerationVerificationError("unexpected scalar artifact")
    return {
        "schema_version": 2,
        "verification_schema_version": 2,
        "persisted_plan_fields_verified": list(PERSISTED_PLAN_FIELDS),
        "nonpersisted_redundant_plan_fields_not_required": ["trajectory_kind", "formal_binding_status"],
        "status": "PASS_INDEPENDENT_CONTROLLED_INTERVENTION_SCIENTIFIC_SEED_SHARD_VERIFICATION",
        "shard_family_id": "controlled_lfe_projection_exchange_scientific_seed_shards_v1",
        "scientific_shard_id": shard_id, "scientific_seed_index": seed_index, "scientific_seed": seed,
        "scientific_trajectories": 120, "scheduler_steps": 6000, "formal_units": 40,
        "source_tasks": 40, "cross_condition_input_invariants_verified": 40,
        "acquisition_scalar_hashes": 40, "direction_scalar_hash_pairs": 640,
        "private_final_latent_files": 120, "private_final_latent_bytes": total_bytes,
        "decoded_media_files": 0, "raw_identity_lfe_or_direction_files": 0,
        "gpu_hours": elapsed, "outcomes_opened": False, "model_loaded_by_verifier": False,
        "gpu_used_by_verifier": False, "network_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--correction-authorization-file", required=True, type=Path)
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--private-latent-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    validate_correction_authority(
        args.correction_authorization_file, args.authorization_file, args.run_dir
    )
    auth = validate_authority(args.authorization_file, args.run_dir, args.private_latent_dir)
    result = verify_outputs(args.run_dir, args.private_latent_dir, int(auth["scientific_seed_index"]))
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ScientificGenerationVerificationError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
