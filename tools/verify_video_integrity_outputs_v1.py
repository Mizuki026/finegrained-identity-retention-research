#!/usr/bin/env python3
"""Independent, no-decode verifier for Pilot v1.1 integrity-audit outputs.

This verifier never opens a video container and never reads video pixels. It
checks the frozen MP4 byte streams, output schemas, cross-file invariants,
aggregate decisions, and the audit checksum manifest.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_ID = "pilot_v1_1_video_integrity_audit_v1"
WORKSPACE = Path("/root/autodl-tmp/finegrained")
REPO = WORKSPACE / "research_pipeline"
PILOT = WORKSPACE / "experiments/pilot_v1_1"
OUTPUT = REPO / "derived/pilot_v1_1/video_integrity_audit_v1"
SCHEMA = REPO / "schemas/integrity_output_schema_v1.json"
MANIFEST = PILOT / "manifest.csv"
SUMMARY = PILOT / "generation_summary_v1.csv"
REPORT = OUTPUT / "independent_verification_v1.json"
EXPECTED_FRAMES = 49
EXPECTED_CONTACT_SIZE = (1200, 2280)

REQUIRED_OUTPUTS = {
    "README.md",
    "frame_inventory_v1.csv",
    "input_output_sha256_v1.csv",
    "pilot_output_audit_v1.json",
    "pilot_video_contact_sheet_v1.png",
    "run_environment_v1.json",
    "video_integrity_audit_v1.csv",
    "video_integrity_audit_v1.log",
}


class VerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerificationError(message)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def as_int(value: str, field: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        fail(f"invalid integer in {field}: {value!r}")
        raise AssertionError from exc


def as_bool(value: str, field: str) -> bool:
    if value not in {"true", "false"}:
        fail(f"invalid boolean in {field}: {value!r}")
    return value == "true"


def row_reasons(row: dict[str, str]) -> list[str]:
    values = [row["primary_reason_code"]]
    if row["secondary_reason_codes"]:
        values.extend(row["secondary_reason_codes"].split(";"))
    return [value for value in values if value]


def expected_status(reasons: list[str]) -> str:
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


def verify_png_header(path: Path) -> tuple[int, int]:
    """Read only PNG structure bytes, not image pixels."""
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        fail("contact sheet is not a structurally recognizable PNG")
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def main() -> int:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        fail("CUDA_VISIBLE_DEVICES must be explicitly empty")
    forbidden = {"cv2", "decord", "torch"}.intersection(sys.modules)
    if forbidden:
        fail(f"decode/model modules unexpectedly imported: {sorted(forbidden)}")
    if REPORT.exists():
        fail(f"refusing to overwrite existing verifier report: {REPORT}")
    if not OUTPUT.is_dir() or OUTPUT.is_symlink():
        fail(f"missing or invalid output directory: {OUTPUT}")
    observed_names = {path.name for path in OUTPUT.iterdir()}
    if observed_names != REQUIRED_OUTPUTS:
        fail(f"output file set mismatch: expected={sorted(REQUIRED_OUTPUTS)} observed={sorted(observed_names)}")

    schema = read_json(SCHEMA)
    video_fields, video_rows = read_csv(OUTPUT / "video_integrity_audit_v1.csv")
    frame_fields, frame_rows = read_csv(OUTPUT / "frame_inventory_v1.csv")
    checksum_fields, checksum_rows = read_csv(OUTPUT / "input_output_sha256_v1.csv")
    manifest_fields, manifest_rows = read_csv(MANIFEST)
    summary_fields, summary_rows = read_csv(SUMMARY)
    pilot = read_json(OUTPUT / "pilot_output_audit_v1.json")
    environment = read_json(OUTPUT / "run_environment_v1.json")
    del manifest_fields, summary_fields

    if video_fields != schema["video_csv_columns"]:
        fail("video CSV schema mismatch")
    if frame_fields != schema["frame_csv_columns"]:
        fail("frame CSV schema mismatch")
    if checksum_fields != schema["checksum_csv_columns"]:
        fail("checksum CSV schema mismatch")
    missing_json_keys = sorted(set(schema["pilot_json_required_keys"]) - set(pilot))
    if missing_json_keys:
        fail(f"pilot JSON missing required keys: {missing_json_keys}")
    if pilot.get("audit_id") != AUDIT_ID or environment.get("audit_id") != AUDIT_ID:
        fail("audit identity mismatch")

    manifest_by_id = {row["sample_id"]: row for row in manifest_rows}
    summary_by_id = {row["sample_id"]: row for row in summary_rows}
    video_by_id = {row["sample_id"]: row for row in video_rows}
    if len(manifest_rows) != 12 or len(manifest_by_id) != 12:
        fail("manifest is not exactly 12 unique samples")
    if len(summary_rows) != 12 or len(summary_by_id) != 12:
        fail("summary is not exactly 12 unique samples")
    if len(video_rows) != 12 or len(video_by_id) != 12:
        fail("video audit is not exactly 12 unique samples")
    expected_ids = set(manifest_by_id)
    if expected_ids != set(summary_by_id) or expected_ids != set(video_by_id):
        fail("sample_id sets differ across manifest, summary, and video audit")
    if pilot["expected_sample_ids"] != sorted(expected_ids) or pilot["observed_sample_ids"] != sorted(expected_ids):
        fail("pilot JSON expected/observed sample sets differ from frozen manifest")

    frames_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for frame in frame_rows:
        if frame["sample_id"] not in expected_ids:
            fail(f"unknown sample in frame inventory: {frame['sample_id']}")
        frames_by_id[frame["sample_id"]].append(frame)

    all_reasons: list[str] = []
    video_hashes: list[str] = []
    for sample_id in sorted(expected_ids):
        manifest = manifest_by_id[sample_id]
        summary = summary_by_id[sample_id]
        row = video_by_id[sample_id]
        expected_video = Path(manifest["output_dir"]) / f"{sample_id}_seed42.mp4"
        expected_metadata = Path(manifest["output_dir"]) / "generation_metadata_v1.json"
        if row["observed_video_path"] != str(expected_video) or summary["video_path"] != str(expected_video):
            fail(f"video path mapping mismatch: {sample_id}")
        if row["metadata_path"] != str(expected_metadata):
            fail(f"metadata path mapping mismatch: {sample_id}")
        if not expected_video.is_file() or expected_video.is_symlink() or expected_video.stat().st_size <= 0:
            fail(f"missing/invalid frozen MP4: {sample_id}")
        if not expected_metadata.is_file() or expected_metadata.is_symlink():
            fail(f"missing/invalid frozen metadata: {sample_id}")
        observed_hash = sha256_path(expected_video)
        video_hashes.append(observed_hash)
        if observed_hash != row["observed_video_sha256"] or observed_hash != summary["video_sha256"]:
            fail(f"frozen MP4 SHA256 mismatch: {sample_id}")
        if observed_hash != row["registered_video_sha256"] or observed_hash != row["summary_video_sha256"]:
            fail(f"registered/summary SHA256 mismatch: {sample_id}")
        if sha256_path(expected_metadata) != row["metadata_sha256"]:
            fail(f"metadata SHA256 mismatch: {sample_id}")
        if as_int(row["byte_size"], "byte_size") != expected_video.stat().st_size:
            fail(f"MP4 byte-size mismatch: {sample_id}")

        required_true = (
            "file_exists", "mapping_match", "sha256_match_registry", "sha256_match_summary",
            "metadata_match", "event_match", "opencv_opened", "decord_opened",
            "decoder_frame_count_match", "resolution_match", "fps_match", "duration_match",
        )
        for field in required_true:
            as_bool(row[field], field)
        as_bool(row["is_symlink"], "is_symlink")
        as_bool(row["frozen_run"], "frozen_run")
        as_bool(row["static_video_anomaly"], "static_video_anomaly")

        inventory = frames_by_id[sample_id]
        expected_inventory_count = max(
            as_int(row["opencv_decoded_frame_count"], "opencv_decoded_frame_count"),
            as_int(row["decord_frame_count"], "decord_frame_count"),
            EXPECTED_FRAMES,
        )
        if len(inventory) != expected_inventory_count:
            fail(f"frame inventory row count mismatch: {sample_id}")
        indices = [as_int(frame["frame_index"], "frame_index") for frame in inventory]
        if indices != list(range(expected_inventory_count)):
            fail(f"frame indices are not complete and ordered: {sample_id}")
        if sum(frame["black_frame"] == "true" for frame in inventory) != as_int(row["black_frame_count"], "black_frame_count"):
            fail(f"black-frame aggregate mismatch: {sample_id}")
        if sum(frame["exact_duplicate"] == "true" for frame in inventory) != as_int(row["exact_duplicate_transition_count"], "exact_duplicate_transition_count"):
            fail(f"exact-duplicate aggregate mismatch: {sample_id}")
        if sum(frame["near_duplicate"] == "true" for frame in inventory) != as_int(row["near_duplicate_transition_count"], "near_duplicate_transition_count"):
            fail(f"near-duplicate aggregate mismatch: {sample_id}")
        if sum(frame["duplicate_like"] == "true" for frame in inventory) != as_int(row["duplicate_like_transition_count"], "duplicate_like_transition_count"):
            fail(f"duplicate-like aggregate mismatch: {sample_id}")

        reasons = row_reasons(row)
        all_reasons.extend(reasons)
        if row["status"] != expected_status(reasons):
            fail(f"status/reason precedence mismatch: {sample_id}")
        if row["status"] == "PASS":
            if reasons:
                fail(f"PASS row has reason codes: {sample_id}")
            if any(row[field] != "true" for field in required_true):
                fail(f"PASS row has a failed required predicate: {sample_id}")
            if row["is_symlink"] != "false" or row["frozen_run"] != "false" or row["static_video_anomaly"] != "false":
                fail(f"PASS row has prohibited integrity flag: {sample_id}")
            if as_int(row["black_frame_count"], "black_frame_count") or as_int(row["corrupt_frame_count"], "corrupt_frame_count"):
                fail(f"PASS row has black/corrupt frames: {sample_id}")

    if len(video_hashes) != len(set(video_hashes)):
        fail("duplicate frozen MP4 SHA256 across sample IDs")

    status_counts = dict(sorted(Counter(row["status"] for row in video_rows).items()))
    reason_counts = dict(sorted(Counter(all_reasons).items()))
    anomaly_counts = {
        "black_frames": sum(as_int(row["black_frame_count"], "black_frame_count") for row in video_rows),
        "corrupt_frames": sum(as_int(row["corrupt_frame_count"], "corrupt_frame_count") for row in video_rows),
        "exact_duplicate_transitions": sum(as_int(row["exact_duplicate_transition_count"], "exact_duplicate_transition_count") for row in video_rows),
        "near_duplicate_transitions": sum(as_int(row["near_duplicate_transition_count"], "near_duplicate_transition_count") for row in video_rows),
        "videos_with_frozen_run": sum(row["frozen_run"] == "true" for row in video_rows),
        "videos_with_static_anomaly": sum(row["static_video_anomaly"] == "true" for row in video_rows),
    }
    expected_pilot_status = "PASS" if status_counts == {"PASS": 12} else "FAIL"
    if pilot["video_status_counts"] != status_counts or pilot["reason_codes"] != reason_counts:
        fail("pilot JSON status/reason aggregates mismatch")
    if pilot["anomaly_counts"] != anomaly_counts or pilot["pilot_status"] != expected_pilot_status:
        fail("pilot JSON anomaly/status aggregate mismatch")

    checksum_by_path: dict[str, dict[str, str]] = {}
    for checksum in checksum_rows:
        path_text = checksum["path"]
        if path_text in checksum_by_path:
            fail(f"duplicate path in checksum manifest: {path_text}")
        path = Path(path_text)
        if not path.is_file() or path.is_symlink():
            fail(f"checksum target missing/non-regular/symlink: {path}")
        if sha256_path(path) != checksum["sha256"] or path.stat().st_size != as_int(checksum["byte_size"], "byte_size"):
            fail(f"checksum manifest mismatch: {path}")
        checksum_by_path[path_text] = checksum
    expected_output_paths = {str(OUTPUT / name) for name in REQUIRED_OUTPUTS if name != "input_output_sha256_v1.csv"}
    observed_output_paths = {
        row["path"] for row in checksum_rows if row["artifact_scope"] == "output"
    }
    if observed_output_paths != expected_output_paths:
        fail("checksum manifest output path set mismatch")

    contact_dimensions = verify_png_header(OUTPUT / "pilot_video_contact_sheet_v1.png")
    if contact_dimensions != EXPECTED_CONTACT_SIZE:
        fail(f"contact sheet dimensions mismatch: {contact_dimensions}")

    report = {
        "schema_version": 1,
        "verification_id": "pilot_v1_1_video_integrity_independent_verification_v1",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "method": "independent_no_decode_cross_file_and_sha256_verification",
        "video_container_opened": False,
        "video_pixels_read": False,
        "models_loaded": False,
        "gpu_used": False,
        "network_used": False,
        "sample_count": len(video_rows),
        "frame_inventory_row_count": len(frame_rows),
        "sample_ids": sorted(expected_ids),
        "video_status_counts": status_counts,
        "reason_codes": reason_counts,
        "anomaly_counts": anomaly_counts,
        "pilot_status": expected_pilot_status,
        "contact_sheet_png_dimensions": list(contact_dimensions),
        "audit_checksum_manifest_sha256": sha256_path(OUTPUT / "input_output_sha256_v1.csv"),
        "verified_output_sha256": {
            name: sha256_path(OUTPUT / name) for name in sorted(REQUIRED_OUTPUTS)
        },
        "scientific_boundary": "Engineering verification only; no attribute, identity, H1-H4, or mechanism claim.",
    }
    with REPORT.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as exc:
        print(f"INDEPENDENT VERIFICATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
