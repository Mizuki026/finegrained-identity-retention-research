#!/usr/bin/env python3
"""CPU-only independent verifier for private run-002 latent decoding."""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import controlled_lfe_private_decode_protocol_v1 as protocol
import run_controlled_lfe_private_decode_v1 as runner

SUMMARY_STATUS = "COMPLETE_PENDING_INDEPENDENT_PRIVATE_DECODE_VERIFICATION"
PASS_STATUS = "PASS_INDEPENDENT_PRIVATE_LATENT_DECODE_VERIFICATION"


class PrivateDecodeVerificationError(RuntimeError):
    """Raised when private decode authority, schema, or artifacts drift."""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_authority(auth_file: Path) -> dict:
    protocol.require_cpu_only()
    if "torch" in sys.modules:
        raise PrivateDecodeVerificationError("verifier must start torch-free")
    if auth_file.resolve() != runner.ACTIVE_AUTH.resolve():
        raise PrivateDecodeVerificationError("active decode authorization path drift")
    auth = protocol.read_json(auth_file)
    exact = {
        "status": runner.ACTIVE_STATUS,
        "execution_explicitly_approved": True,
        "phase": "private_latent_decode",
        "run_id": "monolithic_run_002_private_decode_v1",
        "gpu_hours_ceiling": protocol.GPU_HOURS_CEILING,
        "scalar_output_dir": str(protocol.DECODE_RUN),
        "private_video_output_dir": str(protocol.VIDEO_ROOT),
    }
    if any(auth.get(key) != value for key, value in exact.items()):
        raise PrivateDecodeVerificationError("active private decode authority drift")
    bindings = (
        ("researcher_authorization", runner.RESEARCHER_AUTH, runner.RESEARCHER_STATUS),
        ("preparation_freeze", runner.PREPARATION_FREEZE, runner.PREPARATION_STATUS),
        ("generation_freeze", protocol.GENERATION_FREEZE, runner.GENERATION_STATUS),
    )
    for key, expected_path, expected_status in bindings:
        path = protocol.bound(auth.get(key, {}), key)
        if path.resolve() != expected_path.resolve() or protocol.read_json(path).get("status") != expected_status:
            raise PrivateDecodeVerificationError(f"decode prerequisite drift: {key}")
    code = auth.get("code", {})
    if set(code) != set(runner.CODE_PATHS):
        raise PrivateDecodeVerificationError("authorized decode code universe drift")
    for label, expected_path in runner.CODE_PATHS.items():
        if protocol.bound(code[label], label).resolve() != expected_path.resolve():
            raise PrivateDecodeVerificationError(f"decode code binding drift: {label}")
    authority = auth.get("authority", {})
    required = ("vae_only_single_gpu_decode", "complete_480_video_transaction", "private_video_persistence")
    forbidden = (
        "reference_access", "outcome_access", "annotation", "unblinding", "analysis",
        "public_video", "upscale", "frame_interpolation", "network",
    )
    if any(authority.get(key) is not True for key in required) or any(
        authority.get(key) is not False for key in forbidden
    ):
        raise PrivateDecodeVerificationError("private decode authority boundary drift")
    if subprocess.check_output(
        ["git", "--no-optional-locks", "-C", str(protocol.CONSISID), "rev-parse", "HEAD"], text=True
    ).strip() != protocol.CONSISID_COMMIT:
        raise PrivateDecodeVerificationError("ConsisID HEAD drift")
    if subprocess.check_output(
        ["git", "--no-optional-locks", "-C", str(protocol.CONSISID), "status", "--short"], text=True
    ):
        raise PrivateDecodeVerificationError("ConsisID worktree drift")
    return auth


def verify_outputs(run_dir: Path, video_root: Path) -> dict[str, object]:
    if run_dir.resolve() != protocol.DECODE_RUN.resolve() or video_root.resolve() != protocol.VIDEO_ROOT.resolve():
        raise PrivateDecodeVerificationError("private decode output path drift")
    if run_dir.is_symlink() or not run_dir.is_dir() or video_root.is_symlink() or not video_root.is_dir():
        raise PrivateDecodeVerificationError("private decode output directory absent or unsafe")
    summary = protocol.read_json(run_dir / "private_decode_summary_v1.json")
    exact = {
        "schema_version": 1,
        "status": SUMMARY_STATUS,
        "run_id": "monolithic_run_002_private_decode_v1",
        "source_latents": 480,
        "decoded_private_videos": 480,
        "frames_per_video": 49,
        "fps": 8,
        "width": 720,
        "height": 480,
        "vae_only_model_loading": True,
        "vae_scaling_factor": 0.7,
        "upscale": False,
        "frame_interpolation": False,
        "public_video_files": 0,
        "reference_opened": False,
        "outcome_opened": False,
        "annotation_or_unblinding_performed": False,
        "gpu_hours_ceiling": protocol.GPU_HOURS_CEILING,
    }
    if any(summary.get(key) != value for key, value in exact.items()):
        raise PrivateDecodeVerificationError("private decode summary drift")
    elapsed = float(summary.get("elapsed_gpu_hours", -1))
    if not 0 <= elapsed <= protocol.GPU_HOURS_CEILING:
        raise PrivateDecodeVerificationError("private decode GPU-hour evidence drift")

    expected = protocol.build_plan()
    observed = read_csv(run_dir / "private_decode_status_v1.csv")
    if len(observed) != protocol.TRAJECTORIES or len(expected) != protocol.TRAJECTORIES:
        raise PrivateDecodeVerificationError("private decode status cardinality drift")
    if [tuple(row[key] for key in protocol.PLAN_FIELDS) for row in observed] != [
        tuple(str(row[key]) for key in protocol.PLAN_FIELDS) for row in expected
    ]:
        raise PrivateDecodeVerificationError("private decode persisted plan or order drift")

    required = {
        "status", "finished_at_utc", "latent_shape", "latent_dtype", "vae_scaling_factor",
        "video_bytes", "video_sha256", "frame_count", "fps", "width", "height",
        "private_video_persisted", "public_video_persisted",
    }
    videos: set[Path] = set()
    total_bytes = 0
    for index, row in enumerate(observed, 1):
        if not required.issubset(row):
            raise PrivateDecodeVerificationError(f"private decode status schema drift: {index}")
        exact_row = {
            "status": "COMPLETE",
            "latent_shape": str(list(protocol.LATENT_SHAPE)),
            "latent_dtype": protocol.LATENT_DTYPE,
            "vae_scaling_factor": str(protocol.VAE_SCALING_FACTOR),
            "frame_count": str(protocol.FRAMES),
            "fps": str(float(protocol.FPS)),
            "width": str(protocol.WIDTH),
            "height": str(protocol.HEIGHT),
            "private_video_persisted": "True",
            "public_video_persisted": "False",
        }
        if any(row.get(key) != value for key, value in exact_row.items()):
            raise PrivateDecodeVerificationError(f"private decode row invariant drift: {index}")
        video = Path(row["video_path"])
        expected_name = protocol.video_name(row["planned_task_id"], row["condition"])
        if video.parent.resolve() != video_root.resolve() or video.name != expected_name or video in videos:
            raise PrivateDecodeVerificationError(f"private decoded-video universe drift: {index}")
        if video.is_symlink() or not video.is_file():
            raise PrivateDecodeVerificationError(f"missing regular private decoded video: {index}")
        if video.stat().st_size != int(row["video_bytes"]) or protocol.sha256(video) != row["video_sha256"]:
            raise PrivateDecodeVerificationError(f"private decoded-video binding drift: {index}")
        metadata = protocol.inspect_video(video)
        if any(str(metadata[key]) != row[key] for key in ("frame_count", "fps", "width", "height")):
            raise PrivateDecodeVerificationError(f"private decoded-video metadata drift: {index}")
        videos.add(video)
        total_bytes += video.stat().st_size

    actual = set(video_root.iterdir())
    if actual != videos or len(videos) != protocol.TRAJECTORIES or any(
        path.is_symlink() or not path.is_file() or path.suffix != ".mp4" for path in actual
    ):
        raise PrivateDecodeVerificationError("private decoded-video file universe drift")
    allowed_scalar = {
        "private_decode_status_v1.csv", "private_decode_summary_v1.json",
        "independent_private_decode_verification_v1.json",
    }
    if any(path.is_symlink() or not path.is_file() or path.name not in allowed_scalar for path in run_dir.iterdir()):
        raise PrivateDecodeVerificationError("unexpected private decode scalar artifact")
    return {
        "schema_version": 1,
        "status": PASS_STATUS,
        "run_id": "monolithic_run_002_private_decode_v1",
        "source_latent_bindings_verified": protocol.TRAJECTORIES,
        "private_decoded_video_files": protocol.TRAJECTORIES,
        "private_decoded_video_bytes": total_bytes,
        "decoded_frames_verified": protocol.TRAJECTORIES * protocol.FRAMES,
        "fps": protocol.FPS,
        "width": protocol.WIDTH,
        "height": protocol.HEIGHT,
        "vae_only_decode_verified": True,
        "vae_scaling_factor": protocol.VAE_SCALING_FACTOR,
        "upscale": False,
        "frame_interpolation": False,
        "public_video_files": 0,
        "reference_or_outcome_opened": False,
        "annotation_unblinding_or_analysis_performed": False,
        "model_loaded_by_verifier": False,
        "gpu_used_by_verifier": False,
        "network_used_by_verifier": False,
        "decode_gpu_hours": elapsed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--private-video-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    validate_authority(args.authorization_file)
    result = verify_outputs(args.run_dir, args.private_video_dir)
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        PrivateDecodeVerificationError, protocol.PrivateDecodeProtocolError,
        OSError, ValueError, KeyError, subprocess.SubprocessError,
    ) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
