#!/usr/bin/env python3
"""Fail-closed post-generation integrity audit for formal experiment v1.

This is an engineering audit only. It verifies the frozen task universe,
execution records, MP4 bytes, complete OpenCV decoding, and media properties.
Pixel diagnostics are retained descriptively and never authorize exclusion,
replacement generation, or a scientific claim.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


ROOT = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime")
FREEZE = ROOT / "experiment_freeze_v1"
MASTER = FREEZE / "pre_generation_master_freeze_v1.json"
MANIFEST = FREEZE / "generation_manifest_v1.csv"
GENERATION_SUMMARY = (
    ROOT / "formal_generation_v1/execution_records/formal_generation_summary_v1.json"
)
EXPECTED_MASTER_SHA256 = (
    "149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8"
)
EXPECTED_TASKS = 160
EXPECTED_FRAMES = 49
EXPECTED_FPS = 8.0
EXPECTED_WIDTH = 720
EXPECTED_HEIGHT = 480

VIDEO_COLUMNS = [
    "schema_version", "audit_id", "task_id", "formal_unit_id",
    "formal_pair_id", "attribute", "role", "seed_index", "seed",
    "video_path", "video_sha256", "byte_size", "execution_record_path",
    "execution_record_sha256", "record_status", "return_code",
    "master_freeze_sha256", "reference_image_sha256", "decoded_frames",
    "fps", "width", "height", "black_frame_count",
    "exact_duplicate_transition_count", "minimum_adjacent_nmae",
    "mean_adjacent_nmae", "engineering_status", "diagnostic_flags",
]
FRAME_COLUMNS = [
    "schema_version", "audit_id", "task_id", "frame_index",
    "timestamp_seconds", "shape", "canonical_bgr_sha256", "mean_luma",
    "black_pixel_fraction", "black_frame", "previous_frame_index",
    "adjacent_nmae", "exact_duplicate", "frame_status",
]


class AuditError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise AuditError(message)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv_new(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_json_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def git_commit() -> str:
    repo = Path("/root/autodl-tmp/finegrained/research_pipeline")
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def validate_frozen_inputs(confirm_sha: str) -> tuple[dict, list[dict[str, str]]]:
    if confirm_sha != EXPECTED_MASTER_SHA256:
        fail("explicit master-freeze SHA256 confirmation mismatch")
    for path in (MASTER, MANIFEST, GENERATION_SUMMARY):
        if not path.is_file() or path.is_symlink():
            fail(f"missing or invalid required input: {path}")
    if sha256_path(MASTER) != EXPECTED_MASTER_SHA256:
        fail("master-freeze byte stream drift")
    master = json.loads(MASTER.read_text(encoding="utf-8"))
    if master.get("status") != "FROZEN_READY_FOR_FORMAL_GENERATION":
        fail("unexpected master-freeze status")
    for artifact_id, artifact in master["artifacts"].items():
        path = Path(artifact["path"])
        if not path.is_file() or path.is_symlink():
            fail(f"frozen artifact missing: {artifact_id}")
        if path.stat().st_size != artifact["size_bytes"]:
            fail(f"frozen artifact size drift: {artifact_id}")
        if sha256_path(path) != artifact["sha256"]:
            fail(f"frozen artifact SHA256 drift: {artifact_id}")
    manifest = read_csv(MANIFEST)
    if len(manifest) != EXPECTED_TASKS:
        fail("generation manifest is not exactly 160 tasks")
    task_ids = [row["task_id"] for row in manifest]
    if len(set(task_ids)) != EXPECTED_TASKS:
        fail("generation manifest contains duplicate task IDs")
    units = Counter(row["formal_unit_id"] for row in manifest)
    seeds = Counter(row["seed"] for row in manifest)
    if len(units) != 40 or set(units.values()) != {4}:
        fail("formal unit x seed structure mismatch")
    if len(seeds) != 4 or set(seeds.values()) != {40}:
        fail("shared seed crossing mismatch")
    summary = json.loads(GENERATION_SUMMARY.read_text(encoding="utf-8"))
    if summary.get("status") != "FORMAL_GENERATION_ALL_160_PASS":
        fail("formal generation summary is not complete")
    if summary.get("tasks") != EXPECTED_TASKS:
        fail("formal generation summary task count mismatch")
    if summary.get("master_freeze_sha256") != EXPECTED_MASTER_SHA256:
        fail("formal generation summary master-freeze mismatch")
    return master, manifest


def inspect_task(row: dict[str, str]) -> tuple[dict, list[dict]]:
    task_id = row["task_id"]
    video = Path(row["expected_video_path"])
    record_path = Path(row["execution_record_path"])
    if not video.is_file() or video.is_symlink() or video.stat().st_size <= 0:
        fail(f"missing, empty, or symlink MP4: {task_id}")
    if not record_path.is_file() or record_path.is_symlink():
        fail(f"missing or symlink execution record: {task_id}")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    expected = {
        "task_id": task_id,
        "formal_unit_id": row["formal_unit_id"],
        "formal_pair_id": row["formal_pair_id"],
        "attribute": row["attribute"],
        "role": row["role"],
        "seed_index": int(row["seed_index"]),
        "seed": int(row["seed"]),
        "video_path": str(video),
        "reference_image_sha256": row["reference_image_sha256"],
        "master_freeze_sha256": EXPECTED_MASTER_SHA256,
        "return_code": 0,
        "status": "SUCCESS_FROZEN_OUTPUT",
        "seed_change": False,
        "manual_substitution": False,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            fail(f"execution record mismatch {task_id}: {key}")
    observed_video_sha = sha256_path(video)
    if observed_video_sha != record.get("video_sha256"):
        fail(f"video SHA256 mismatch: {task_id}")
    if video.stat().st_size != record.get("video_size_bytes"):
        fail(f"video byte-size mismatch: {task_id}")

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        fail(f"OpenCV cannot open video: {task_id}")
    declared_fps = float(cap.get(cv2.CAP_PROP_FPS))
    declared_width = int(round(cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
    declared_height = int(round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    frame_rows: list[dict] = []
    previous: np.ndarray | None = None
    adjacent: list[float] = []
    exact_duplicates = 0
    black_frames = 0
    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame.shape != (EXPECTED_HEIGHT, EXPECTED_WIDTH, 3):
            fail(f"decoded frame shape mismatch: {task_id} frame {index}")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_luma = float(gray.mean())
        black_fraction = float((gray <= 5).mean())
        black = black_fraction >= 0.99
        black_frames += int(black)
        exact = False
        nmae = ""
        if previous is not None:
            diff = np.abs(frame.astype(np.int16) - previous.astype(np.int16))
            value = float(diff.mean() / 255.0)
            adjacent.append(value)
            nmae = f"{value:.10f}"
            exact = bool(np.array_equal(frame, previous))
            exact_duplicates += int(exact)
        frame_rows.append({
            "schema_version": "1", "audit_id": "formal_post_generation_integrity_v1",
            "task_id": task_id, "frame_index": str(index),
            "timestamp_seconds": f"{index / EXPECTED_FPS:.6f}",
            "shape": "720x480x3", "canonical_bgr_sha256": sha256_bytes(frame.tobytes()),
            "mean_luma": f"{mean_luma:.8f}",
            "black_pixel_fraction": f"{black_fraction:.8f}",
            "black_frame": str(black).lower(),
            "previous_frame_index": str(index - 1) if index else "",
            "adjacent_nmae": nmae, "exact_duplicate": str(exact).lower(),
            "frame_status": "PASS",
        })
        previous = frame
        index += 1
    cap.release()
    if index != EXPECTED_FRAMES:
        fail(f"decoded frame count mismatch: {task_id}: {index}")
    if abs(declared_fps - EXPECTED_FPS) > 0.01:
        fail(f"FPS mismatch: {task_id}: {declared_fps}")
    if (declared_width, declared_height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        fail(f"resolution mismatch: {task_id}")
    if (record.get("frame_count"), record.get("fps"), record.get("width"), record.get("height")) != (
        EXPECTED_FRAMES, EXPECTED_FPS, EXPECTED_WIDTH, EXPECTED_HEIGHT
    ):
        fail(f"execution-record media metadata mismatch: {task_id}")
    flags = []
    if black_frames:
        flags.append("BLACK_FRAME_PRESENT")
    if exact_duplicates:
        flags.append("EXACT_DUPLICATE_TRANSITION_PRESENT")
    video_row = {
        "schema_version": "1", "audit_id": "formal_post_generation_integrity_v1",
        "task_id": task_id, "formal_unit_id": row["formal_unit_id"],
        "formal_pair_id": row["formal_pair_id"], "attribute": row["attribute"],
        "role": row["role"], "seed_index": row["seed_index"], "seed": row["seed"],
        "video_path": str(video), "video_sha256": observed_video_sha,
        "byte_size": str(video.stat().st_size), "execution_record_path": str(record_path),
        "execution_record_sha256": sha256_path(record_path),
        "record_status": record["status"], "return_code": str(record["return_code"]),
        "master_freeze_sha256": record["master_freeze_sha256"],
        "reference_image_sha256": record["reference_image_sha256"],
        "decoded_frames": str(index), "fps": f"{declared_fps:.6f}",
        "width": str(declared_width), "height": str(declared_height),
        "black_frame_count": str(black_frames),
        "exact_duplicate_transition_count": str(exact_duplicates),
        "minimum_adjacent_nmae": f"{min(adjacent):.10f}",
        "mean_adjacent_nmae": f"{float(np.mean(adjacent)):.10f}",
        "engineering_status": "PASS", "diagnostic_flags": ";".join(flags),
    }
    return video_row, frame_rows


def run(output_dir: Path, confirm_sha: str) -> None:
    if output_dir.exists():
        fail(f"refusing to overwrite output directory: {output_dir}")
    master, manifest = validate_frozen_inputs(confirm_sha)
    output_dir.mkdir(parents=True)
    videos: list[dict] = []
    frames: list[dict] = []
    for index, row in enumerate(manifest, 1):
        video_row, frame_rows = inspect_task(row)
        videos.append(video_row)
        frames.extend(frame_rows)
        if index % 10 == 0 or index == EXPECTED_TASKS:
            print(f"integrity {index}/{EXPECTED_TASKS}", flush=True)
    if len(videos) != EXPECTED_TASKS or len(frames) != EXPECTED_TASKS * EXPECTED_FRAMES:
        fail("audit output universe mismatch")
    if len({row["video_sha256"] for row in videos}) != EXPECTED_TASKS:
        fail("duplicate MP4 SHA256 values detected")
    write_csv_new(output_dir / "video_integrity_v1.csv", VIDEO_COLUMNS, videos)
    write_csv_new(output_dir / "frame_integrity_v1.csv", FRAME_COLUMNS, frames)
    audit = {
        "schema_version": 1,
        "audit_id": "formal_post_generation_integrity_v1",
        "completed_at_utc": now(),
        "producing_code_commit": git_commit(),
        "producing_script_sha256": sha256_path(Path(__file__)),
        "master_freeze_sha256": EXPECTED_MASTER_SHA256,
        "generation_manifest_sha256": sha256_path(MANIFEST),
        "generation_summary_sha256": sha256_path(GENERATION_SUMMARY),
        "task_count": len(videos), "frame_count": len(frames),
        "engineering_status_counts": dict(Counter(row["engineering_status"] for row in videos)),
        "black_frame_count": sum(int(row["black_frame_count"]) for row in videos),
        "exact_duplicate_transition_count": sum(int(row["exact_duplicate_transition_count"]) for row in videos),
        "diagnostic_flag_counts": dict(Counter(
            flag for row in videos for flag in row["diagnostic_flags"].split(";") if flag
        )),
        "environment": {"python": platform.python_version(), "opencv": cv2.__version__},
        "generation_or_regeneration_performed": False,
        "exclusion_performed": False,
        "scientific_outcome_inspected": False,
        "status": "POST_GENERATION_ENGINEERING_INTEGRITY_PASS",
        "boundary": "Engineering integrity only; diagnostics do not authorize exclusion or scientific claims.",
    }
    write_json_new(output_dir / "integrity_audit_v1.json", audit)
    hashes = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file():
            hashes.append({"file": path.name, "sha256": sha256_path(path), "bytes": path.stat().st_size})
    write_csv_new(output_dir / "output_hashes_v1.csv", ["file", "sha256", "bytes"], hashes)
    write_json_new(output_dir / "integrity_freeze_v1.json", {
        "schema_version": 1, "freeze_id": "formal_post_generation_integrity_v1",
        "frozen_at_utc": now(), "master_freeze_sha256": EXPECTED_MASTER_SHA256,
        "output_hash_inventory_sha256": sha256_path(output_dir / "output_hashes_v1.csv"),
        "task_count": len(videos), "frame_count": len(frames),
        "status": "FROZEN_ENGINEERING_INTEGRITY_PASS",
    })


def verify(output_dir: Path, verification_path: Path, confirm_sha: str) -> None:
    validate_frozen_inputs(confirm_sha)
    required = {
        "video_integrity_v1.csv", "frame_integrity_v1.csv", "integrity_audit_v1.json",
        "output_hashes_v1.csv", "integrity_freeze_v1.json",
    }
    if not output_dir.is_dir() or {p.name for p in output_dir.iterdir()} != required:
        fail("integrity output file set mismatch")
    videos = read_csv(output_dir / "video_integrity_v1.csv")
    frames = read_csv(output_dir / "frame_integrity_v1.csv")
    if len(videos) != EXPECTED_TASKS or len(frames) != EXPECTED_TASKS * EXPECTED_FRAMES:
        fail("integrity row-count mismatch")
    if Counter(row["engineering_status"] for row in videos) != {"PASS": EXPECTED_TASKS}:
        fail("not all videos passed engineering integrity")
    if any(Counter(row["task_id"] for row in frames)[row["task_id"]] != EXPECTED_FRAMES for row in videos):
        fail("frame inventory does not contain 49 rows per task")
    for row in read_csv(output_dir / "output_hashes_v1.csv"):
        path = output_dir / row["file"]
        if not path.is_file() or sha256_path(path) != row["sha256"] or path.stat().st_size != int(row["bytes"]):
            fail(f"integrity output hash mismatch: {path}")
    freeze = json.loads((output_dir / "integrity_freeze_v1.json").read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN_ENGINEERING_INTEGRITY_PASS":
        fail("integrity freeze status mismatch")
    if verification_path.exists():
        fail(f"refusing to overwrite verification: {verification_path}")
    write_json_new(verification_path, {
        "schema_version": 1,
        "verification_id": "formal_post_generation_integrity_independent_verification_v1",
        "verified_at_utc": now(), "task_count": len(videos), "frame_count": len(frames),
        "all_listed_hashes_verified": True, "generation_performed": False,
        "scientific_outcome_inspected": False,
        "status": "PASS_INDEPENDENT_ENGINEERING_INTEGRITY_VERIFICATION",
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("dry-run", "run", "verify"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confirm-master-sha256", required=True)
    parser.add_argument("--verification-path", type=Path)
    args = parser.parse_args()
    if args.mode == "dry-run":
        _, manifest = validate_frozen_inputs(args.confirm_master_sha256)
        print(json.dumps({
            "status": "PREFLIGHT_PASS", "tasks": len(manifest),
            "videos_opened": False, "outputs_written": False,
        }, indent=2))
    elif args.mode == "run":
        run(args.output_dir, args.confirm_master_sha256)
        print(json.dumps({"status": "POST_GENERATION_ENGINEERING_INTEGRITY_PASS", "output_dir": str(args.output_dir)}, indent=2))
    else:
        verification = (
            args.verification_path
            or args.output_dir.parent / "integrity_independent_verification_v1.json"
        )
        verify(args.output_dir, verification, args.confirm_master_sha256)
        print(json.dumps({"status": "PASS_INDEPENDENT_ENGINEERING_INTEGRITY_VERIFICATION", "verification": str(verification)}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except AuditError as exc:
        raise SystemExit(f"INTEGRITY AUDIT FAILED: {exc}")
