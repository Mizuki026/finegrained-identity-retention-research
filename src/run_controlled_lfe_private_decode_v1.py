#!/usr/bin/env python3
"""Fail-closed preparation and execution runner for private latent decoding."""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import controlled_lfe_private_decode_protocol_v1 as protocol


class PrivateDecodeRunnerError(RuntimeError):
    """Raised before an unauthorized or drifting private decode action."""


RESEARCHER_AUTH = protocol.GOVERNANCE / "researcher_private_latent_decode_authorization_v1.json"
PREPARATION_FREEZE = protocol.GOVERNANCE / "private_decode_preparation_freeze_v1.json"
ACTIVE_AUTH = protocol.GOVERNANCE / "private_decode_execution_authorization_v1.json"
RESEARCHER_STATUS = "RESEARCHER_AUTHORIZATION_FOR_PRIVATE_LATENT_DECODE_PROTOCOL_PREPARATION_AND_EXECUTION"
PREPARATION_STATUS = "FROZEN_PASS_PRIVATE_LATENT_DECODE_PROTOCOL_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN"
ACTIVE_STATUS = "PRIVATE_LATENT_DECODE_SINGLE_GPU_EXECUTION_AUTHORIZED"
GENERATION_STATUS = "FROZEN_PASS_COMPLETE_INDEPENDENTLY_VERIFIED_SCIENTIFIC_MONOLITHIC_RUN_002_GENERATION"
CODE_PATHS = {
    "protocol": protocol.REPO / "src/controlled_lfe_private_decode_protocol_v1.py",
    "runtime": protocol.REPO / "src/controlled_lfe_private_decode_runtime_v1.py",
    "runner": protocol.REPO / "src/run_controlled_lfe_private_decode_v1.py",
    "verifier": protocol.REPO / "src/verify_controlled_lfe_private_decode_v1.py",
    "preparation_verifier": protocol.REPO / "src/verify_controlled_lfe_private_decode_preparation_v1.py",
}


def git(repository: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "--no-optional-locks", "-C", str(repository), *args], text=True
    ).strip()


def dry_run(output_dir: Path) -> dict[str, object]:
    protocol.require_cpu_only()
    if "torch" in sys.modules:
        raise PrivateDecodeRunnerError("no-weight dry-run imported torch")
    researcher = protocol.read_json(RESEARCHER_AUTH)
    if researcher.get("status") != RESEARCHER_STATUS:
        raise PrivateDecodeRunnerError("researcher private decode authority drift")
    if researcher.get("gpu_execution_authorized") is not True:
        raise PrivateDecodeRunnerError("private decode execution authority missing")
    generation = protocol.read_json(protocol.GENERATION_FREEZE)
    if generation.get("status") != GENERATION_STATUS:
        raise PrivateDecodeRunnerError("generation freeze is not independently verified pass")
    if protocol.DECODE_RUN.exists() or protocol.DECODE_RUN.with_name(protocol.DECODE_RUN.name + ".partial").exists():
        raise PrivateDecodeRunnerError("decode scalar output already exists")
    if protocol.VIDEO_ROOT.exists():
        raise PrivateDecodeRunnerError("private decoded-video output already exists")
    if ACTIVE_AUTH.exists():
        raise PrivateDecodeRunnerError("active decode authorization must not exist during dry-run")
    rows = protocol.build_plan()
    if output_dir.exists() or output_dir.with_name(output_dir.name + ".partial").exists():
        raise PrivateDecodeRunnerError("dry-run output path exists")
    staging = output_dir.with_name(output_dir.name + ".partial")
    staging.mkdir(parents=True, exist_ok=False)
    protocol.atomic_csv(staging / "private_decode_plan_v1.csv", protocol.PLAN_FIELDS, rows)
    summary = {
        "schema_version": 1,
        "status": "PASS_PRIVATE_LATENT_DECODE_CPU_ONLY_NO_WEIGHT_DRY_RUN",
        "source_latents": len(rows),
        "planned_private_videos": len(rows),
        "frames_per_video": protocol.FRAMES,
        "fps": protocol.FPS,
        "width": protocol.WIDTH,
        "height": protocol.HEIGHT,
        "latent_shape": list(protocol.LATENT_SHAPE),
        "latent_dtype": protocol.LATENT_DTYPE,
        "vae_scaling_factor": protocol.VAE_SCALING_FACTOR,
        "vae_only_model_loading_planned": True,
        "upscale": False,
        "frame_interpolation": False,
        "active_execution_authorization_present": False,
        "latent_tensor_opened": False,
        "model_or_weights_loaded": False,
        "gpu_used": False,
        "reference_or_outcome_opened": False,
        "decoded_video_generated": False,
        "annotation_unblinding_or_analysis": False,
        "torch_imported": False,
        "network_used": False,
    }
    protocol.atomic_json(staging / "private_decode_no_weight_dry_run_v1.json", summary)
    staging.replace(output_dir)
    return summary


def validate_active(auth_file: Path) -> dict:
    if auth_file.resolve() != ACTIVE_AUTH.resolve():
        raise PrivateDecodeRunnerError("active decode authorization path drift")
    auth = protocol.read_json(auth_file)
    if (
        auth.get("status") != ACTIVE_STATUS
        or auth.get("execution_explicitly_approved") is not True
        or auth.get("phase") != "private_latent_decode"
        or auth.get("run_id") != "monolithic_run_002_private_decode_v1"
    ):
        raise PrivateDecodeRunnerError("active private decode authority drift")
    researcher = protocol.bound(auth.get("researcher_authorization", {}), "researcher decode authorization")
    if researcher.resolve() != RESEARCHER_AUTH.resolve() or protocol.read_json(researcher).get("status") != RESEARCHER_STATUS:
        raise PrivateDecodeRunnerError("researcher decode authorization binding drift")
    preparation = protocol.bound(auth.get("preparation_freeze", {}), "decode preparation freeze")
    if preparation.resolve() != PREPARATION_FREEZE.resolve() or protocol.read_json(preparation).get("status") != PREPARATION_STATUS:
        raise PrivateDecodeRunnerError("decode preparation freeze drift")
    generation = protocol.bound(auth.get("generation_freeze", {}), "scientific generation freeze")
    if generation.resolve() != protocol.GENERATION_FREEZE.resolve() or protocol.read_json(generation).get("status") != GENERATION_STATUS:
        raise PrivateDecodeRunnerError("scientific generation freeze drift")
    code = auth.get("code", {})
    if set(code) != set(CODE_PATHS):
        raise PrivateDecodeRunnerError("decode code universe drift")
    for label, path in CODE_PATHS.items():
        if protocol.bound(code[label], label).resolve() != path.resolve():
            raise PrivateDecodeRunnerError(f"decode code binding drift: {label}")
    inventory = protocol.bound(auth.get("model_inventory", {}), "model inventory")
    if inventory.resolve() != protocol.MODEL_INVENTORY.resolve():
        raise PrivateDecodeRunnerError("model inventory path drift")
    with inventory.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["relative_path"].startswith("vae/")]
    if len(rows) != 2:
        raise PrivateDecodeRunnerError("VAE-only model inventory drift")
    bindings = auth.get("vae_files", {})
    if set(bindings) != {row["relative_path"] for row in rows}:
        raise PrivateDecodeRunnerError("VAE file binding universe drift")
    for row in rows:
        path = protocol.MODEL_ROOT / row["relative_path"]
        item = bindings[row["relative_path"]]
        if protocol.bound(item, row["relative_path"]).resolve() != path.resolve():
            raise PrivateDecodeRunnerError("VAE file path drift")
        if int(row["size_bytes"]) != path.stat().st_size or row["sha256"] != protocol.sha256(path):
            raise PrivateDecodeRunnerError("VAE file differs from frozen model inventory")
    if Path(str(auth.get("scalar_output_dir", ""))).resolve() != protocol.DECODE_RUN.resolve():
        raise PrivateDecodeRunnerError("decode scalar output path drift")
    if Path(str(auth.get("private_video_output_dir", ""))).resolve() != protocol.VIDEO_ROOT.resolve():
        raise PrivateDecodeRunnerError("private video output path drift")
    parent = protocol.VIDEO_ROOT.parent
    if not parent.is_dir() or parent.stat().st_mode & 0o777 != 0o700:
        raise PrivateDecodeRunnerError("private video parent must exist with mode 0700")
    minimum = int(auth.get("minimum_private_filesystem_free_bytes", 0))
    if minimum < 10 * 1024**3 or shutil.disk_usage(parent).free < minimum:
        raise PrivateDecodeRunnerError("private decode free-space gate failed")
    if float(auth.get("gpu_hours_ceiling", 0)) != protocol.GPU_HOURS_CEILING:
        raise PrivateDecodeRunnerError("decode GPU-hour ceiling drift")
    authority = auth.get("authority", {})
    required = ("vae_only_single_gpu_decode", "complete_480_video_transaction", "private_video_persistence")
    forbidden = ("reference_access", "outcome_access", "annotation", "unblinding", "analysis", "public_video", "upscale", "frame_interpolation", "network")
    if any(authority.get(key) is not True for key in required) or any(authority.get(key) is not False for key in forbidden):
        raise PrivateDecodeRunnerError("private decode authority boundary incomplete")
    cuda = str(auth.get("cuda_visible_devices", ""))
    if not cuda.isdigit() or "," in cuda or os.environ.get("CUDA_VISIBLE_DEVICES") != cuda:
        raise PrivateDecodeRunnerError("single-GPU binding mismatch")
    if any(os.environ.get(key) != value for key, value in {
        "WORLD_SIZE": "1", "LOCAL_WORLD_SIZE": "1", "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
        "TOKENIZERS_PARALLELISM": "false",
    }.items()):
        raise PrivateDecodeRunnerError("offline single-process environment drift")
    if git(protocol.REPO, "branch", "--show-current") != "main" or git(protocol.REPO, "status", "--short"):
        raise PrivateDecodeRunnerError("decode execution requires clean main worktree")
    if git(protocol.CONSISID, "rev-parse", "HEAD") != protocol.CONSISID_COMMIT or git(protocol.CONSISID, "status", "--short"):
        raise PrivateDecodeRunnerError("ConsisID repository drift")
    return auth


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("dry-run", "execute"))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--authorization-file", type=Path)
    args = parser.parse_args()
    if args.mode == "dry-run":
        if args.output_dir is None:
            raise PrivateDecodeRunnerError("dry-run output directory required")
        print(json.dumps(dry_run(args.output_dir), indent=2, sort_keys=True))
        return 0
    if args.authorization_file is None:
        raise PrivateDecodeRunnerError("active decode authorization required")
    auth = validate_active(args.authorization_file)
    from controlled_lfe_private_decode_runtime_v1 import execute

    execute(auth)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PrivateDecodeRunnerError, protocol.PrivateDecodeProtocolError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
