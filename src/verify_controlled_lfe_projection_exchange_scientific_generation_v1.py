#!/usr/bin/env python3
"""Independent CPU-only verifier for private scientific-generation artifacts."""
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
AUTHORIZATION = REPO / "governance/mechanism_controlled_intervention_scientific_v1/scientific_run_001_execution_authorization_v1.json"
CONSISID = Path("/root/autodl-tmp/consisid-smoketest/ConsisID")
CONSISID_COMMIT = "60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
AUTH_STATUS = "CONTROLLED_INTERVENTION_SCIENTIFIC_GPU_EXECUTION_AUTHORIZED"
RESEARCHER_STATUS = "CONTROLLED_INTERVENTION_SCIENTIFIC_PREPARATION_AND_GENERATION_AUTHORIZED_ONLY"
ENGINEERING_STATUS = "FROZEN_PASS_COMPLETE_INDEPENDENTLY_VERIFIED_SINGLE_GPU_ENGINEERING"
SUMMARY_STATUS = "COMPLETE_PENDING_INDEPENDENT_PHASE_VERIFICATION"


class ScientificGenerationVerificationError(RuntimeError):
    """Raised when scientific-generation authority or artifacts drift."""


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


def validate_authority(run_dir: Path, private_root: Path) -> dict:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise ScientificGenerationVerificationError("verifier must start CUDA-hidden and torch-free")
    auth = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    if auth.get("status") != AUTH_STATUS or auth.get("phase") != "scientific":
        raise ScientificGenerationVerificationError("scientific authorization status drift")
    if auth.get("scientific_run_id") != "run_001" or auth.get("execution_explicitly_approved") is not True:
        raise ScientificGenerationVerificationError("scientific transaction identity drift")
    if Path(auth.get("runtime_output_dir", "")).resolve() != run_dir.resolve():
        raise ScientificGenerationVerificationError("scalar output path drift")
    if Path(auth.get("private_latent_output_dir", "")).resolve() != private_root.resolve():
        raise ScientificGenerationVerificationError("private output path drift")
    researcher_item = auth.get("researcher_authorization", {})
    researcher_path = resolve(str(researcher_item.get("path", "")))
    verify_file(researcher_path, researcher_item)
    researcher = json.loads(researcher_path.read_text(encoding="utf-8"))
    if researcher.get("status") != RESEARCHER_STATUS:
        raise ScientificGenerationVerificationError("researcher authority drift")
    engineering_item = auth.get("engineering_freeze", {})
    engineering_path = resolve(str(engineering_item.get("path", "")))
    verify_file(engineering_path, engineering_item)
    if json.loads(engineering_path.read_text()).get("status") != ENGINEERING_STATUS:
        raise ScientificGenerationVerificationError("engineering freeze is not pass")
    for item in auth.get("code", {}).values():
        verify_file(resolve(str(item.get("path", ""))), item)
    verifier_item = auth.get("scientific_generation_verifier", {})
    verify_file(resolve(str(verifier_item.get("path", ""))), verifier_item)
    if float(auth.get("phase_gpu_hours_ceiling", 0)) != 72.0:
        raise ScientificGenerationVerificationError("scientific GPU ceiling drift")
    if subprocess.check_output(["git", "-C", str(CONSISID), "rev-parse", "HEAD"], text=True).strip() != CONSISID_COMMIT:
        raise ScientificGenerationVerificationError("ConsisID HEAD drift")
    if subprocess.check_output(["git", "-C", str(CONSISID), "status", "--short"], text=True):
        raise ScientificGenerationVerificationError("ConsisID worktree drift")
    return auth


def verify_outputs(run_dir: Path, private_root: Path) -> dict:
    summary = json.loads((run_dir / "execution_summary_v1.json").read_text(encoding="utf-8"))
    exact = {"phase": "scientific", "fresh_preprocessing_calls": 40, "direct_lfe_acquisitions": 40,
             "directions_constructed": 640, "trajectory_rows": 480, "scheduler_steps": 24000,
             "raw_identity_lfe_or_direction_tensor_files": 0}
    if summary.get("status") != SUMMARY_STATUS or any(summary.get(k) != v for k, v in exact.items()):
        raise ScientificGenerationVerificationError("scientific summary drift")
    elapsed = float(summary.get("elapsed_gpu_hours", -1))
    if not 0 <= elapsed <= 72 or float(summary.get("phase_gpu_hours_ceiling", 0)) != 72:
        raise ScientificGenerationVerificationError("scientific time ceiling drift")
    with (run_dir / "trajectory_status_v1.csv").open(newline="", encoding="utf-8") as handle:
        observed = list(csv.DictReader(handle))
    expected = protocol.execution_plan()
    plan_keys = tuple(expected[0])
    if len(observed) != 480 or [tuple(row[k] for k in plan_keys) for row in observed] != [tuple(str(row[k]) for k in plan_keys) for row in expected]:
        raise ScientificGenerationVerificationError("scientific plan or order drift")
    required = {"status", "initial_denoising_input_sha256", "spatial_reference_route_sha256", "hidden_shape",
                "hidden_dtype", "hidden_device_type", "lfe_hook_calls", "private_latent_path",
                "private_latent_bytes", "private_latent_sha256", "decoded_media_persisted"}
    by_task: dict[str, list[dict[str, str]]] = defaultdict(list)
    paths = set()
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
    if actual_private != paths or len(paths) != 480 or any(path.suffix != ".safetensors" for path in actual_private):
        raise ScientificGenerationVerificationError("private latent universe drift")
    invariant_keys = ("initial_denoising_input_sha256", "spatial_reference_route_sha256", "hidden_shape", "hidden_dtype", "hidden_device_type")
    if len(by_task) != 160 or any(len(rows) != 3 or len({tuple(row[k] for k in invariant_keys) for row in rows}) != 1 for rows in by_task.values()):
        raise ScientificGenerationVerificationError("cross-condition invariant drift")
    allowed = {"trajectory_status_v1.csv", "execution_summary_v1.json"}
    if any(path.name not in allowed and path.name != "independent_verification_v1.json" for path in run_dir.iterdir() if path.is_file()):
        raise ScientificGenerationVerificationError("unexpected scalar artifact")
    return {"schema_version": 1, "status": "PASS_INDEPENDENT_CONTROLLED_INTERVENTION_SCIENTIFIC_GENERATION_VERIFICATION",
            "scientific_trajectories": 480, "scheduler_steps": 24000, "formal_units": 40,
            "source_tasks": 160, "cross_condition_input_invariants_verified": 160,
            "private_final_latent_files": 480, "private_final_latent_bytes": total_bytes,
            "decoded_media_files": 0, "raw_identity_lfe_or_direction_files": 0,
            "gpu_hours": elapsed, "outcomes_opened": False, "model_loaded_by_verifier": False,
            "gpu_used_by_verifier": False, "network_used": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--private-latent-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    validate_authority(args.run_dir, args.private_latent_dir)
    result = verify_outputs(args.run_dir, args.private_latent_dir)
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ScientificGenerationVerificationError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
