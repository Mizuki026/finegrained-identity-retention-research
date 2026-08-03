#!/usr/bin/env python3
"""CPU-only, fail-closed Pilot v1.1 video integrity audit.

Purpose: implement governance/video_integrity_audit_protocol_v1.md exactly.
Inputs: immutable Pilot v1.1 CSV/JSON/log/metadata/MP4 artifacts.
Outputs: a new versioned derived directory; existing targets are never overwritten.
Runtime: seconds to minutes on CPU; no GPU, network, model, or weight access.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import traceback
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import decord
import numpy as np
from PIL import Image, ImageDraw


AUDIT_ID = "pilot_v1_1_video_integrity_audit_v1"
SCHEMA_VERSION = 1
WORKSPACE = Path("/root/autodl-tmp/finegrained")
REPO = WORKSPACE / "research_pipeline"
GOVERNANCE = REPO / "governance"
PILOT = WORKSPACE / "experiments/pilot_v1_1"
VIDEO_ROOT = PILOT / "outputs"
FINAL_ROOT = REPO / "derived/pilot_v1_1/video_integrity_audit_v1"
SCHEMA_PATH = REPO / "schemas/integrity_output_schema_v1.json"

INPUTS = {
    "manifest_v1_1": PILOT / "manifest.csv",
    "config_v1_1": PILOT / "config.json",
    "revision_lineage_v1_1": PILOT / "revision_lineage.json",
    "pre_generation_readiness_v1": PILOT / "metric_audit/pre_generation_readiness_v1.json",
    "video_evaluation_protocol_v1": PILOT / "metric_audit/video_evaluation_protocol_v1.json",
    "generation_summary_v1": PILOT / "generation_summary_v1.csv",
    "generation_events_v1": PILOT / "generation_events_v1.jsonl",
    "formal_generation_log_v1": PILOT / "formal_generation_v1.log",
    "artifact_registry_v1": GOVERNANCE / "artifact_registry_v1.csv",
    "video_integrity_audit_protocol_v1": GOVERNANCE / "video_integrity_audit_protocol_v1.md",
}

EXPECTED_HASHES = {
    "manifest_v1_1": "dcf66f0222986403493a7c9a09d310629909d4aef590634348b41ce12544f79d",
    "config_v1_1": "40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47",
    "revision_lineage_v1_1": "d254cc00a612fad8eb0ca77dfaac9784a7644f588454361fc65b0d7d72dcb1a4",
    "pre_generation_readiness_v1": "f0fbc9a8fe8e0b576dcbf4b6228dd655bd07484358420b09d7d533f5b61afed5",
    "video_evaluation_protocol_v1": "0a096f8e74af5fad769955ce331658bd9ef8373ba526279e96aba778c07a3964",
    "generation_summary_v1": "97389045205ca664e2f158d727c15da45a4c2b4a3f90cc6ad260605920fd31c8",
    "generation_events_v1": "79aeaeb37787b00c9bf2eff66115e03e334ce2e455b4609e273028f4635f43e3",
    "formal_generation_log_v1": "a1a00e620558b89bcbe5d960834e003d6c195adbca3b7d7e8ee9a289b19a066d",
    "artifact_registry_v1": "13f69b1b1948ee6ffdb74cda389ba51e56e45642aec362d1055cbd337029fc8f",
    "video_integrity_audit_protocol_v1": "5012d924f3ee5b35b45dc8538791b67a6d08a377b18301a9266105bd8f37bbb0",
}

EXPECTED_FRAMES = 49
EXPECTED_FPS = 8.0
EXPECTED_WIDTH = 720
EXPECTED_HEIGHT = 480
EXPECTED_DURATION = EXPECTED_FRAMES / EXPECTED_FPS
FPS_TOLERANCE = 0.01
DURATION_TOLERANCE = 1.0 / EXPECTED_FPS
CONTACT_INDICES = (0, 12, 24, 36, 48)


class AuditError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def as_bool(value: bool) -> str:
    return "true" if value else "false"


def as_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def float_equal(left: Any, right: Any, tolerance: float = 1e-9) -> bool:
    a = as_float(left)
    b = as_float(right)
    return a is not None and b is not None and abs(a - b) <= tolerance


def canonical_shape(array: np.ndarray) -> str:
    return "x".join(str(part) for part in array.shape)


def luma_and_small(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rgb32 = rgb.astype(np.float32)
    luma = 0.2126 * rgb32[:, :, 0] + 0.7152 * rgb32[:, :, 1] + 0.0722 * rgb32[:, :, 2]
    small = cv2.resize(luma, (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32)
    return luma, small


def pair_metrics(previous_small: np.ndarray, current_small: np.ndarray) -> tuple[float, float]:
    difference = np.abs(current_small.astype(np.float32) - previous_small.astype(np.float32))
    return float(difference.mean() / 255.0), float((difference <= 2.0).mean())


def max_true_run(flags: list[bool]) -> int:
    best = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def classify_status(reasons: list[str]) -> str:
    if not reasons:
        return "PASS"
    if any(code in reasons for code in ("PATH_MAPPING_MISMATCH", "DUPLICATE_PATH", "DUPLICATE_VIDEO_HASH")):
        return "FAIL_MAPPING"
    if any(code in reasons for code in ("OUTPUT_FILE_MISSING", "OUTPUT_FILE_EMPTY", "VIDEO_SHA256_MISMATCH")):
        return "FAIL_FILE_INTEGRITY"
    if any(code in reasons for code in ("CONTAINER_OPEN_FAILED", "FRAME_DECODE_FAILED", "DECODER_DISAGREEMENT", "CORRUPT_FRAME")):
        return "FAIL_CONTAINER_OR_DECODE"
    if any(code in reasons for code in ("FRAME_COUNT_MISMATCH", "FPS_MISMATCH", "DURATION_MISMATCH", "RESOLUTION_MISMATCH")):
        return "FAIL_MEDIA_SPEC"
    return "FAIL_VISUAL_INTEGRITY"


class AuditLog:
    def __init__(self, path: Path):
        self.path = path
        self.handle = path.open("x", encoding="utf-8", buffering=1)

    def write(self, event: str, **fields: Any) -> None:
        record = {"timestamp_utc": utc_now(), "event": event, **fields}
        self.handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")

    def close(self) -> None:
        if not self.handle.closed:
            self.handle.flush()
            os.fsync(self.handle.fileno())
            self.handle.close()


def compare_metadata(
    manifest: dict[str, str],
    summary: dict[str, str],
    event: dict[str, Any],
    metadata: dict[str, Any],
    config: dict[str, Any],
) -> tuple[bool, bool, list[str]]:
    errors: list[str] = []
    common = ("sample_id", "attribute", "label", "identity")
    for key in common:
        if str(summary.get(key)) != str(manifest.get(key)):
            errors.append(f"summary.{key}")
        if str(metadata.get(key)) != str(manifest.get(key)):
            errors.append(f"metadata.{key}")
        if str(event.get(key)) != str(manifest.get(key)):
            errors.append(f"event.{key}")
    for key in ("granularity", "reference_path", "reference_sha256"):
        if str(metadata.get(key)) != str(manifest.get(key)) or str(event.get(key)) != str(manifest.get(key)):
            errors.append(key)
    for key in ("video_path", "video_sha256", "status"):
        if str(metadata.get(key)) != str(summary.get(key)):
            errors.append(f"metadata.{key}")
        if str(event.get(key)) != str(summary.get(key)):
            errors.append(f"event.{key}")
    for key in ("frame_count", "width", "height"):
        if int(metadata.get(key, -1)) != int(summary.get(key, -2)) or int(event.get(key, -1)) != int(summary.get(key, -2)):
            errors.append(key)
    if not float_equal(metadata.get("fps"), summary.get("fps")) or not float_equal(event.get("fps"), summary.get("fps")):
        errors.append("fps")
    for source_name, source in (("metadata", metadata), ("event", event)):
        if int(source.get("seed", -1)) != int(config["seed"]):
            errors.append(f"{source_name}.seed")
        if int(source.get("num_inference_steps", -1)) != int(config["num_inference_steps"]):
            errors.append(f"{source_name}.num_inference_steps")
        if not float_equal(source.get("guidance_scale"), config["guidance_scale"]):
            errors.append(f"{source_name}.guidance_scale")
        environment = source.get("environment", {})
        for name, expected in (
            ("manifest_sha256", EXPECTED_HASHES["manifest_v1_1"]),
            ("config_sha256", EXPECTED_HASHES["config_v1_1"]),
            ("readiness_sha256", EXPECTED_HASHES["pre_generation_readiness_v1"]),
            ("protocol_sha256", EXPECTED_HASHES["video_evaluation_protocol_v1"]),
        ):
            if environment.get(name) != expected:
                errors.append(f"{source_name}.environment.{name}")
    metadata_errors = [item for item in errors if not item.startswith("event.")]
    event_errors = [item for item in errors if not item.startswith("metadata.")]
    return not metadata_errors, not event_errors, sorted(set(errors))


def preflight(require_clean_git: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        errors.append("CUDA_VISIBLE_DEVICES must be explicitly empty")
    if "torch" in sys.modules:
        errors.append("torch must not be imported")
    if FINAL_ROOT.exists():
        errors.append(f"final output already exists: {FINAL_ROOT}")
    if not SCHEMA_PATH.is_file():
        errors.append(f"schema missing: {SCHEMA_PATH}")

    observed_input_hashes: dict[str, str] = {}
    input_artifacts: list[dict[str, Any]] = []
    for artifact_id, path in INPUTS.items():
        if not path.is_file() or path.is_symlink():
            errors.append(f"missing/non-regular/symlink input: {path}")
            continue
        observed = sha256_path(path)
        observed_input_hashes[artifact_id] = observed
        input_artifacts.append(
            {"artifact_id": artifact_id, "path": str(path), "sha256": observed, "byte_size": path.stat().st_size}
        )
        if observed != EXPECTED_HASHES[artifact_id]:
            errors.append(f"hash mismatch {artifact_id}: {observed}")

    schema = read_json(SCHEMA_PATH) if SCHEMA_PATH.is_file() else {}
    if schema.get("schema_version") != SCHEMA_VERSION or schema.get("audit_id") != AUDIT_ID:
        errors.append("schema identity/version mismatch")

    manifest_rows = read_csv(INPUTS["manifest_v1_1"])
    summary_rows = read_csv(INPUTS["generation_summary_v1"])
    with INPUTS["generation_events_v1"].open("r", encoding="utf-8") as handle:
        event_rows = [json.loads(line) for line in handle if line.strip()]
    registry_rows = read_csv(INPUTS["artifact_registry_v1"])
    config = read_json(INPUTS["config_v1_1"])

    manifest_ids = [row["sample_id"] for row in manifest_rows]
    summary_ids = [row["sample_id"] for row in summary_rows]
    event_ids = [str(row["sample_id"]) for row in event_rows]
    if len(manifest_rows) != 12 or len(set(manifest_ids)) != 12:
        errors.append("manifest must contain 12 unique sample IDs")
    if Counter(row["attribute"] for row in manifest_rows) != Counter({"eyeglasses": 4, "facial_hair": 4, "hair_color": 4}):
        errors.append("manifest attribute counts are not four each")
    if len(summary_rows) != 12 or len(set(summary_ids)) != 12 or any(row["status"] != "SUCCESS" for row in summary_rows):
        errors.append("summary must contain 12 unique SUCCESS rows")
    if len(event_rows) != 12 or len(set(event_ids)) != 12:
        errors.append("events must contain 12 unique rows")
    if set(manifest_ids) != set(summary_ids) or set(manifest_ids) != set(event_ids):
        errors.append("manifest/summary/event sample sets differ")

    summary_by_id = {row["sample_id"]: row for row in summary_rows}
    event_by_id = {str(row["sample_id"]): row for row in event_rows}
    registry_by_path = {
        row["path"]: row for row in registry_rows if row["artifact_class"] == "frozen_generated_output"
    }
    if len(registry_by_path) != 12:
        errors.append("registry must contain 12 frozen generated outputs")

    actual_mp4 = sorted(path.resolve() for path in VIDEO_ROOT.rglob("*.mp4"))
    items: list[dict[str, Any]] = []
    expected_paths: list[Path] = []
    video_hashes: list[str] = []
    for manifest in manifest_rows:
        sample_id = manifest["sample_id"]
        summary = summary_by_id.get(sample_id, {})
        event = event_by_id.get(sample_id, {})
        output_dir = Path(manifest["output_dir"])
        expected_video = output_dir / f"{sample_id}_seed42.mp4"
        metadata_path = output_dir / "generation_metadata_v1.json"
        expected_paths.append(expected_video.resolve())
        if expected_video.is_symlink() or not expected_video.is_file():
            errors.append(f"missing/non-regular/symlink video: {expected_video}")
            continue
        if metadata_path.is_symlink() or not metadata_path.is_file():
            errors.append(f"missing/non-regular/symlink metadata: {metadata_path}")
            continue
        directory_mp4 = list(output_dir.glob("*.mp4"))
        if len(directory_mp4) != 1:
            errors.append(f"expected exactly one MP4 in {output_dir}")
        if summary.get("video_path") != str(expected_video):
            errors.append(f"summary path mismatch: {sample_id}")
        observed_video_sha = sha256_path(expected_video)
        registry = registry_by_path.get(str(expected_video))
        if registry is None:
            errors.append(f"video absent from registry: {sample_id}")
            registered_sha = ""
        else:
            registered_sha = registry["sha256"]
        if observed_video_sha != summary.get("video_sha256") or observed_video_sha != registered_sha:
            errors.append(f"video hash mismatch: {sample_id}")
        video_hashes.append(observed_video_sha)
        metadata = read_json(metadata_path)
        metadata_match, event_match, cross_errors = compare_metadata(manifest, summary, event, metadata, config)
        if cross_errors:
            errors.append(f"metadata/event mismatch {sample_id}: {';'.join(cross_errors)}")
        input_artifacts.extend(
            [
                {
                    "artifact_id": f"metadata_{sample_id}",
                    "path": str(metadata_path),
                    "sha256": sha256_path(metadata_path),
                    "byte_size": metadata_path.stat().st_size,
                },
                {
                    "artifact_id": f"video_{sample_id}",
                    "path": str(expected_video),
                    "sha256": observed_video_sha,
                    "byte_size": expected_video.stat().st_size,
                },
            ]
        )
        items.append(
            {
                "manifest": manifest,
                "summary": summary,
                "event": event,
                "metadata": metadata,
                "metadata_path": metadata_path,
                "video_path": expected_video,
                "video_sha256": observed_video_sha,
                "registered_sha256": registered_sha,
                "metadata_match": metadata_match,
                "event_match": event_match,
            }
        )

    if set(actual_mp4) != set(expected_paths):
        errors.append("actual and expected MP4 path sets differ")
    if len(video_hashes) != len(set(video_hashes)):
        errors.append("duplicate video SHA256 across sample IDs")
    if len(items) != 12:
        errors.append("preflight item count is not 12")

    git_commit = git_output("rev-parse", "HEAD")
    git_status = git_output("status", "--porcelain=v1", "--untracked-files=all")
    if require_clean_git and git_status:
        errors.append("research repository is not clean")
    upstream_status = subprocess.run(
        ["git", "-C", str(WORKSPACE / "code/ConsisID"), "status", "--porcelain=v1", "--untracked-files=all"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    if upstream_status:
        errors.append("upstream ConsisID worktree is not clean")
    disk = shutil.disk_usage(REPO)
    if disk.free < 100 * 1024 * 1024:
        errors.append("less than 100 MiB free for bounded derived outputs")
    if errors:
        raise AuditError("PREFLIGHT FAILED\n" + "\n".join(f"- {error}" for error in errors))

    cv2.setNumThreads(1)
    return {
        "schema": schema,
        "schema_sha256": sha256_path(SCHEMA_PATH),
        "script_sha256": sha256_path(Path(__file__).resolve()),
        "git_commit": git_commit,
        "git_status": git_status,
        "upstream_commit": git_output_from(WORKSPACE / "code/ConsisID", "rev-parse", "HEAD"),
        "items": items,
        "input_artifacts": input_artifacts,
        "observed_input_hashes": observed_input_hashes,
        "versions": {
            "python": platform.python_version(),
            "opencv": cv2.__version__,
            "decord": decord.__version__,
            "numpy": np.__version__,
            "pillow": getattr(sys.modules.get("PIL"), "__version__", "10.4.0"),
        },
        "disk_free_bytes": disk.free,
    }


def git_output_from(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, text=True, capture_output=True
    ).stdout.strip()


def audit_one(item: dict[str, Any], log: AuditLog) -> tuple[dict[str, Any], list[dict[str, Any]], dict[int, np.ndarray]]:
    sample_id = item["manifest"]["sample_id"]
    path: Path = item["video_path"]
    log.write("video_start", sample_id=sample_id, video_path=str(path))
    reasons: list[str] = []
    opencv_frames: list[np.ndarray] = []
    opencv_valid: list[bool] = []
    opencv_shapes: list[str] = []
    cap = cv2.VideoCapture(str(path))
    opencv_opened = bool(cap.isOpened())
    declared_count = int(round(cap.get(cv2.CAP_PROP_FRAME_COUNT))) if opencv_opened else 0
    opencv_fps = float(cap.get(cv2.CAP_PROP_FPS)) if opencv_opened else float("nan")
    opencv_width = int(round(cap.get(cv2.CAP_PROP_FRAME_WIDTH))) if opencv_opened else 0
    opencv_height = int(round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))) if opencv_opened else 0
    if not opencv_opened:
        reasons.append("CONTAINER_OPEN_FAILED")
    else:
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            valid = (
                isinstance(bgr, np.ndarray)
                and bgr.size > 0
                and bgr.ndim == 3
                and bgr.shape[2] == 3
                and np.isfinite(bgr).all()
            )
            opencv_valid.append(bool(valid))
            if valid:
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                if rgb.dtype != np.uint8:
                    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
                opencv_frames.append(rgb)
                opencv_shapes.append(canonical_shape(rgb))
            else:
                opencv_frames.append(np.empty((0, 0, 3), dtype=np.uint8))
                opencv_shapes.append("")
        cap.release()

    decord_opened = False
    decord_count = 0
    decord_fps = float("nan")
    decord_valid: list[bool] = []
    decord_shapes: list[str] = []
    try:
        reader = decord.VideoReader(str(path), ctx=decord.cpu(0), num_threads=1)
        decord_opened = True
        decord_count = len(reader)
        decord_fps = float(reader.get_avg_fps())
        for index in range(decord_count):
            array = reader[index].asnumpy()
            valid = (
                isinstance(array, np.ndarray)
                and array.size > 0
                and array.ndim == 3
                and array.shape[2] == 3
                and np.isfinite(array).all()
            )
            decord_valid.append(bool(valid))
            decord_shapes.append(canonical_shape(array) if valid else "")
    except Exception as exc:  # evidence is retained rather than repaired
        log.write("decord_exception", sample_id=sample_id, exception=repr(exc), traceback=traceback.format_exc())
        reasons.append("CONTAINER_OPEN_FAILED" if not decord_opened else "FRAME_DECODE_FAILED")

    opencv_count = len(opencv_frames)
    if not all(opencv_valid) or not all(decord_valid):
        reasons.append("CORRUPT_FRAME")
    if opencv_count != decord_count:
        reasons.append("DECODER_DISAGREEMENT")
    if opencv_count != EXPECTED_FRAMES or decord_count != EXPECTED_FRAMES or declared_count != EXPECTED_FRAMES:
        reasons.append("FRAME_COUNT_MISMATCH")

    resolution_match = (
        opencv_width == EXPECTED_WIDTH
        and opencv_height == EXPECTED_HEIGHT
        and all(shape == f"{EXPECTED_HEIGHT}x{EXPECTED_WIDTH}x3" for shape in opencv_shapes)
        and all(shape == f"{EXPECTED_HEIGHT}x{EXPECTED_WIDTH}x3" for shape in decord_shapes)
    )
    if not resolution_match:
        reasons.append("RESOLUTION_MISMATCH")
    fps_match = (
        math.isfinite(opencv_fps)
        and math.isfinite(decord_fps)
        and abs(opencv_fps - EXPECTED_FPS) <= FPS_TOLERANCE
        and abs(decord_fps - EXPECTED_FPS) <= FPS_TOLERANCE
        and abs(opencv_fps - decord_fps) <= FPS_TOLERANCE
    )
    if not fps_match:
        reasons.append("FPS_MISMATCH")
    opencv_duration = opencv_count / opencv_fps if opencv_fps > 0 else float("nan")
    decord_duration = decord_count / decord_fps if decord_fps > 0 else float("nan")
    duration_match = (
        math.isfinite(opencv_duration)
        and math.isfinite(decord_duration)
        and abs(opencv_duration - EXPECTED_DURATION) <= DURATION_TOLERANCE
        and abs(decord_duration - EXPECTED_DURATION) <= DURATION_TOLERANCE
    )
    if not duration_match:
        reasons.append("DURATION_MISMATCH")

    frame_rows: list[dict[str, Any]] = []
    selected: dict[int, np.ndarray] = {}
    duplicate_flags: list[bool] = []
    exact_count = near_count = black_count = corrupt_count = 0
    previous_small: np.ndarray | None = None
    previous_hash: str | None = None
    for index in range(max(opencv_count, decord_count, EXPECTED_FRAMES)):
        cv_valid = index < len(opencv_valid) and opencv_valid[index]
        dc_valid = index < len(decord_valid) and decord_valid[index]
        rgb = opencv_frames[index] if cv_valid else None
        frame_hash = ""
        mean_luma: float | None = None
        black_fraction: float | None = None
        black = False
        nmae: float | None = None
        close_fraction: float | None = None
        exact = near = duplicate = False
        frame_reasons: list[str] = []
        if not cv_valid or not dc_valid:
            frame_reasons.append("CORRUPT_FRAME")
            corrupt_count += 1
        if rgb is not None:
            frame_hash = sha256_bytes(rgb.tobytes(order="C"))
            luma, small = luma_and_small(rgb)
            mean_luma = float(luma.mean())
            black_fraction = float((luma <= 16.0).mean())
            black = black_fraction >= 0.98 and mean_luma <= 8.0
            if black:
                frame_reasons.append("BLACK_FRAME")
                black_count += 1
            if previous_small is not None and previous_hash is not None:
                nmae, close_fraction = pair_metrics(previous_small, small)
                exact = frame_hash == previous_hash
                near = (not exact) and nmae <= 0.002 and close_fraction >= 0.995
                duplicate = exact or near
                duplicate_flags.append(duplicate)
                exact_count += int(exact)
                near_count += int(near)
            previous_small = small
            previous_hash = frame_hash
            if index in CONTACT_INDICES:
                selected[index] = rgb.copy()
        elif index > 0:
            duplicate_flags.append(False)
            previous_small = None
            previous_hash = None
        frame_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "audit_id": AUDIT_ID,
                "sample_id": sample_id,
                "frame_index": index,
                "timestamp_seconds": index / EXPECTED_FPS,
                "opencv_decode_valid": as_bool(cv_valid),
                "decord_decode_valid": as_bool(dc_valid),
                "opencv_shape": opencv_shapes[index] if index < len(opencv_shapes) else "",
                "decord_shape": decord_shapes[index] if index < len(decord_shapes) else "",
                "canonical_rgb_sha256": frame_hash,
                "mean_luma": mean_luma,
                "black_pixel_fraction": black_fraction,
                "black_frame": as_bool(black),
                "previous_frame_index": index - 1 if index > 0 else "",
                "adjacent_nmae": nmae,
                "adjacent_close_fraction": close_fraction,
                "exact_duplicate": as_bool(exact),
                "near_duplicate": as_bool(near),
                "duplicate_like": as_bool(duplicate),
                "frame_status": "PASS" if not frame_reasons else "FAIL",
                "primary_reason_code": frame_reasons[0] if frame_reasons else "",
                "secondary_reason_codes": ";".join(frame_reasons[1:]),
            }
        )

    max_run = max_true_run(duplicate_flags)
    duplicate_count = sum(duplicate_flags)
    frozen_run = max_run >= 8
    static_anomaly = duplicate_count >= 44
    if black_count:
        reasons.append("BLACK_FRAME")
    if frozen_run:
        reasons.append("FROZEN_RUN")
    if static_anomaly:
        reasons.append("STATIC_VIDEO_ANOMALY")
    reasons = list(dict.fromkeys(reasons))
    status = classify_status(reasons)
    row = {
        "schema_version": SCHEMA_VERSION,
        "audit_id": AUDIT_ID,
        "sample_id": sample_id,
        "attribute": item["manifest"]["attribute"],
        "label": item["manifest"]["label"],
        "identity": item["manifest"]["identity"],
        "observed_video_path": str(path),
        "metadata_path": str(item["metadata_path"]),
        "metadata_sha256": sha256_path(item["metadata_path"]),
        "file_exists": "true",
        "is_symlink": "false",
        "byte_size": path.stat().st_size,
        "observed_video_sha256": item["video_sha256"],
        "registered_video_sha256": item["registered_sha256"],
        "summary_video_sha256": item["summary"]["video_sha256"],
        "mapping_match": "true",
        "sha256_match_registry": as_bool(item["video_sha256"] == item["registered_sha256"]),
        "sha256_match_summary": as_bool(item["video_sha256"] == item["summary"]["video_sha256"]),
        "metadata_match": as_bool(item["metadata_match"]),
        "event_match": as_bool(item["event_match"]),
        "opencv_opened": as_bool(opencv_opened),
        "decord_opened": as_bool(decord_opened),
        "opencv_declared_frame_count": declared_count,
        "opencv_decoded_frame_count": opencv_count,
        "decord_frame_count": decord_count,
        "opencv_fps": opencv_fps if math.isfinite(opencv_fps) else None,
        "decord_fps": decord_fps if math.isfinite(decord_fps) else None,
        "opencv_width": opencv_width,
        "opencv_height": opencv_height,
        "decord_width": int(decord_shapes[0].split("x")[1]) if decord_shapes and decord_shapes[0] else None,
        "decord_height": int(decord_shapes[0].split("x")[0]) if decord_shapes and decord_shapes[0] else None,
        "opencv_duration_seconds": opencv_duration if math.isfinite(opencv_duration) else None,
        "decord_duration_seconds": decord_duration if math.isfinite(decord_duration) else None,
        "decoder_frame_count_match": as_bool(opencv_count == decord_count),
        "resolution_match": as_bool(resolution_match),
        "fps_match": as_bool(fps_match),
        "duration_match": as_bool(duration_match),
        "corrupt_frame_count": corrupt_count,
        "black_frame_count": black_count,
        "exact_duplicate_transition_count": exact_count,
        "near_duplicate_transition_count": near_count,
        "duplicate_like_transition_count": duplicate_count,
        "max_duplicate_like_run_transitions": max_run,
        "frozen_run": as_bool(frozen_run),
        "static_video_anomaly": as_bool(static_anomaly),
        "primary_reason_code": reasons[0] if reasons else "",
        "secondary_reason_codes": ";".join(reasons[1:]),
        "status": status,
    }
    log.write("video_complete", sample_id=sample_id, status=status, reason_codes=reasons)
    return row, frame_rows, selected


def write_csv_new(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_json_new(path: Path, payload: Any) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def create_contact_sheet(path: Path, selected_by_sample: dict[str, dict[int, np.ndarray]]) -> None:
    thumb_w, thumb_h, label_h = 240, 160, 30
    sample_ids = sorted(selected_by_sample)
    canvas = Image.new("RGB", (thumb_w * len(CONTACT_INDICES), (thumb_h + label_h) * len(sample_ids)), "white")
    draw = ImageDraw.Draw(canvas)
    for row_index, sample_id in enumerate(sample_ids):
        selected = selected_by_sample[sample_id]
        for col_index, frame_index in enumerate(CONTACT_INDICES):
            x = col_index * thumb_w
            y = row_index * (thumb_h + label_h)
            if frame_index in selected:
                image = Image.fromarray(selected[frame_index], mode="RGB").resize((thumb_w, thumb_h), Image.Resampling.BILINEAR)
                canvas.paste(image, (x, y))
            else:
                draw.rectangle((x, y, x + thumb_w - 1, y + thumb_h - 1), fill=(230, 230, 230))
                draw.text((x + 8, y + 70), "FRAME UNAVAILABLE", fill=(160, 0, 0))
            label = f"{sample_id} | f{frame_index:02d}"
            draw.text((x + 4, y + thumb_h + 7), label, fill=(0, 0, 0))
    canvas.save(path, format="PNG", optimize=False)


def validate_generated(
    schema: dict[str, Any], video_rows: list[dict[str, Any]], frame_rows: list[dict[str, Any]], pilot: dict[str, Any]
) -> None:
    if len(video_rows) != 12 or len({row["sample_id"] for row in video_rows}) != 12:
        raise AuditError("generated video table must contain 12 unique sample IDs")
    if [*video_rows[0].keys()] != schema["video_csv_columns"]:
        raise AuditError("video table schema mismatch")
    if frame_rows and [*frame_rows[0].keys()] != schema["frame_csv_columns"]:
        raise AuditError("frame table schema mismatch")
    if any(key not in pilot for key in schema["pilot_json_required_keys"]):
        raise AuditError("pilot JSON required-key mismatch")
    for row in video_rows:
        sample_frames = [frame for frame in frame_rows if frame["sample_id"] == row["sample_id"]]
        expected_rows = max(int(row["opencv_decoded_frame_count"]), int(row["decord_frame_count"]), EXPECTED_FRAMES)
        if len(sample_frames) != expected_rows:
            raise AuditError(f"frame inventory count mismatch for {row['sample_id']}")


def run_audit() -> dict[str, Any]:
    context = preflight(require_clean_git=True)
    parent = FINAL_ROOT.parent
    parent.mkdir(parents=True, exist_ok=True)
    temp_root = parent / f".{FINAL_ROOT.name}.tmp-{uuid.uuid4().hex}"
    temp_root.mkdir(exist_ok=False)
    log = AuditLog(temp_root / "video_integrity_audit_v1.log")
    try:
        log.write(
            "audit_start",
            audit_id=AUDIT_ID,
            final_root=str(FINAL_ROOT),
            protocol_sha256=EXPECTED_HASHES["video_integrity_audit_protocol_v1"],
            script_sha256=context["script_sha256"],
            schema_sha256=context["schema_sha256"],
            git_commit=context["git_commit"],
            input_hashes=context["observed_input_hashes"],
            cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"),
            model_loaded=False,
            network_used=False,
        )
        video_rows: list[dict[str, Any]] = []
        frame_rows: list[dict[str, Any]] = []
        selected_by_sample: dict[str, dict[int, np.ndarray]] = {}
        for item in context["items"]:
            row, frames, selected = audit_one(item, log)
            video_rows.append(row)
            frame_rows.extend(frames)
            selected_by_sample[row["sample_id"]] = selected

        video_rows.sort(key=lambda row: row["sample_id"])
        frame_rows.sort(key=lambda row: (row["sample_id"], int(row["frame_index"])))
        status_counts = dict(sorted(Counter(row["status"] for row in video_rows).items()))
        all_reasons: list[str] = []
        for row in video_rows:
            if row["primary_reason_code"]:
                all_reasons.append(row["primary_reason_code"])
            if row["secondary_reason_codes"]:
                all_reasons.extend(row["secondary_reason_codes"].split(";"))
        reason_counts = dict(sorted(Counter(all_reasons).items()))
        pilot_status = "PASS" if status_counts == {"PASS": 12} else "FAIL"
        pilot = {
            "schema_version": SCHEMA_VERSION,
            "audit_id": AUDIT_ID,
            "protocol": {
                "path": str(INPUTS["video_integrity_audit_protocol_v1"]),
                "sha256": EXPECTED_HASHES["video_integrity_audit_protocol_v1"],
                "thresholds_changed_after_pixel_access": False,
            },
            "producing_code": {
                "script_path": str(Path(__file__).resolve()),
                "script_sha256": context["script_sha256"],
                "schema_path": str(SCHEMA_PATH),
                "schema_sha256": context["schema_sha256"],
                "research_pipeline_git_commit": context["git_commit"],
                "upstream_consisid_git_commit": context["upstream_commit"],
            },
            "execution": {
                "completed_at_utc": utc_now(),
                "cpu_only": True,
                "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                "model_loaded": False,
                "network_used": False,
                "dependencies_installed": False,
                "all_videos_audited": True,
                "contact_sheet_indices": list(CONTACT_INDICES),
            },
            "input_artifacts": context["input_artifacts"],
            "expected_sample_ids": sorted(item["manifest"]["sample_id"] for item in context["items"]),
            "observed_sample_ids": [row["sample_id"] for row in video_rows],
            "video_status_counts": status_counts,
            "anomaly_counts": {
                "black_frames": sum(int(row["black_frame_count"]) for row in video_rows),
                "corrupt_frames": sum(int(row["corrupt_frame_count"]) for row in video_rows),
                "exact_duplicate_transitions": sum(int(row["exact_duplicate_transition_count"]) for row in video_rows),
                "near_duplicate_transitions": sum(int(row["near_duplicate_transition_count"]) for row in video_rows),
                "videos_with_frozen_run": sum(row["frozen_run"] == "true" for row in video_rows),
                "videos_with_static_anomaly": sum(row["static_video_anomaly"] == "true" for row in video_rows),
            },
            "pilot_status": pilot_status,
            "reason_codes": reason_counts,
            "scientific_boundary": {
                "evidence_class": "fact_and_engineering_diagnostic_only",
                "does_not_measure": ["identity", "eyeglasses", "facial_hair", "hair_color", "H1-H4", "mechanism"],
                "contact_sheet_is_not_numerical_evidence": True,
            },
            "output_artifacts": [
                "video_integrity_audit_v1.csv",
                "frame_inventory_v1.csv",
                "pilot_output_audit_v1.json",
                "pilot_video_contact_sheet_v1.png",
                "video_integrity_audit_v1.log",
                "run_environment_v1.json",
                "input_output_sha256_v1.csv",
                "README.md",
            ],
        }
        validate_generated(context["schema"], video_rows, frame_rows, pilot)
        write_csv_new(temp_root / "video_integrity_audit_v1.csv", context["schema"]["video_csv_columns"], video_rows)
        write_csv_new(temp_root / "frame_inventory_v1.csv", context["schema"]["frame_csv_columns"], frame_rows)
        write_json_new(temp_root / "pilot_output_audit_v1.json", pilot)
        create_contact_sheet(temp_root / "pilot_video_contact_sheet_v1.png", selected_by_sample)
        environment = {
            "schema_version": 1,
            "audit_id": AUDIT_ID,
            "captured_at_utc": utc_now(),
            "versions": context["versions"],
            "platform": platform.platform(),
            "python_executable": sys.executable,
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "opencv_threads": cv2.getNumThreads(),
            "decord_context": str(decord.cpu(0)),
            "torch_imported": "torch" in sys.modules,
            "gpu_accessed": False,
            "model_loaded": False,
            "network_used": False,
            "dependencies_installed": False,
            "disk_free_bytes_at_preflight": context["disk_free_bytes"],
            "research_pipeline_git_commit": context["git_commit"],
            "upstream_consisid_git_commit": context["upstream_commit"],
        }
        write_json_new(temp_root / "run_environment_v1.json", environment)
        readme = f"""# Pilot v1.1 Video Integrity Audit v1\n\nStatus: `{pilot_status}`\n\nThis directory is a CPU-only engineering integrity audit of exactly 12 frozen MP4 files under protocol SHA256 `{EXPECTED_HASHES['video_integrity_audit_protocol_v1']}`. It does not evaluate identity or attributes and cannot test H1–H4.\n\nFiles:\n\n- `video_integrity_audit_v1.csv`: video-level mappings, media properties, diagnostics, and status.\n- `frame_inventory_v1.csv`: every decoded/expected frame and frozen diagnostics.\n- `pilot_output_audit_v1.json`: aggregate decision and provenance.\n- `pilot_video_contact_sheet_v1.png`: deterministic frames {list(CONTACT_INDICES)} for human engineering review only; it does not replace numerical auditing.\n- `video_integrity_audit_v1.log`: append-only JSONL execution log.\n- `run_environment_v1.json`: CPU runtime provenance.\n- `input_output_sha256_v1.csv`: source and derived artifact hashes; its own hash is reported by the independent verifier and Git handoff.\n\nNo frozen artifact was modified, moved, or regenerated.\n"""
        with (temp_root / "README.md").open("x", encoding="utf-8") as handle:
            handle.write(readme)
        log.write("outputs_validated", pilot_status=pilot_status, video_status_counts=status_counts, reason_codes=reason_counts)
        log.write("audit_complete", output_root=str(FINAL_ROOT))
        log.close()

        checksum_rows: list[dict[str, Any]] = []
        for artifact in context["input_artifacts"]:
            checksum_rows.append(
                {
                    "artifact_scope": "input",
                    "artifact_id": artifact["artifact_id"],
                    "path": artifact["path"],
                    "sha256": artifact["sha256"],
                    "byte_size": artifact["byte_size"],
                    "immutable": "true",
                    "parent_artifact_ids": "",
                    "notes": "read-only source",
                }
            )
        for output_path in sorted(path for path in temp_root.iterdir() if path.name != "input_output_sha256_v1.csv"):
            checksum_rows.append(
                {
                    "artifact_scope": "output",
                    "artifact_id": output_path.stem,
                    "path": str(FINAL_ROOT / output_path.name),
                    "sha256": sha256_path(output_path),
                    "byte_size": output_path.stat().st_size,
                    "immutable": "true",
                    "parent_artifact_ids": "video_integrity_audit_protocol_v1;pilot_v1_1_video_set",
                    "notes": "derived Stage 1 artifact",
                }
            )
        write_csv_new(
            temp_root / "input_output_sha256_v1.csv",
            context["schema"]["checksum_csv_columns"],
            checksum_rows,
        )
        temp_root.rename(FINAL_ROOT)
        return {"pilot_status": pilot_status, "status_counts": status_counts, "output_root": str(FINAL_ROOT)}
    except Exception:
        log.write("audit_exception", traceback=traceback.format_exc())
        log.close()
        failed_root = parent / f"{FINAL_ROOT.name}.failed-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        if temp_root.exists() and not failed_root.exists():
            temp_root.rename(failed_root)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="validate inputs and environment without opening any video")
    mode.add_argument("--run", action="store_true", help="execute the full CPU-only audit")
    args = parser.parse_args()
    if args.dry_run:
        context = preflight(require_clean_git=True)
        print(
            json.dumps(
                {
                    "status": "DRY_RUN_PASS",
                    "sample_count": len(context["items"]),
                    "git_commit": context["git_commit"],
                    "script_sha256": context["script_sha256"],
                    "schema_sha256": context["schema_sha256"],
                    "versions": context["versions"],
                    "video_container_opened": False,
                    "video_pixels_read": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(json.dumps(run_audit(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
