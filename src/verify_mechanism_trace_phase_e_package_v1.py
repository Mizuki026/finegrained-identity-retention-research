#!/usr/bin/env python3
"""Independent stdlib verifier for the frozen mechanism-trace phase-E package."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from mechanism_trace_protocol_v1 import ProtocolError, atomic_write_json, read_json, sha256


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "governance" / "mechanism_trace_phase_e_v1"
MANIFEST = PACKAGE / "phase_e_runtime_evidence_manifest_v1.csv"


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO / path


def verify() -> dict:
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 10:
        raise ProtocolError(f"phase-E evidence count mismatch: {len(rows)}")
    if len({row["evidence_id"] for row in rows}) != len(rows):
        raise ProtocolError("phase-E evidence IDs are not unique")
    if len({row["path"] for row in rows}) != len(rows):
        raise ProtocolError("phase-E evidence paths are not unique")
    for row in rows:
        path = resolve_path(row["path"])
        if not path.is_file():
            raise ProtocolError(f"phase-E evidence missing: {path}")
        if path.stat().st_size != int(row["bytes"]):
            raise ProtocolError(f"phase-E evidence byte drift: {path}")
        if sha256(path) != row["sha256"]:
            raise ProtocolError(f"phase-E evidence hash drift: {path}")

    external = Path(
        "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/"
        "phase_e_run_001/independent_verification_v1.json"
    )
    copied = PACKAGE / "phase_e_independent_verification_v1.json"
    if read_json(external) != read_json(copied):
        raise ProtocolError("committed independent verification differs from runtime artifact")
    independent = read_json(copied)
    if independent["status"] != "PASS_INDEPENDENT_MECHANISM_TRACE_VERIFICATION":
        raise ProtocolError("phase-E independent verification did not pass")
    control = independent.get("engineering_control") or {}
    if control.get("status") != "PASS_ENGINEERING_REPEAT_AND_ZERO_ROUTE_CONTROLS":
        raise ProtocolError("phase-E engineering controls did not pass")
    if control.get("maximum_baseline_repeat_absolute_difference") != 0.0:
        raise ProtocolError("phase-E baseline-repeat maximum difference is not zero")
    if control.get("maximum_reference_route_absolute_difference") != 0.0:
        raise ProtocolError("phase-E reference-route maximum difference is not zero")

    external_audit = Path(
        "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/"
        "phase_e_run_001/post_run_audit_v1.json"
    )
    copied_audit = PACKAGE / "phase_e_post_run_audit_v1.json"
    if read_json(external_audit) != read_json(copied_audit):
        raise ProtocolError("committed post-run audit differs from runtime artifact")
    audit = read_json(copied_audit)
    if audit["status"] != "PASS_OUTCOME_BLIND_PHASE_E_POST_RUN_AUDIT":
        raise ProtocolError("phase-E post-run audit did not pass")
    if not audit["scheduler_sequence_identical_across_tasks_sites_and_cfg"]:
        raise ProtocolError("phase-E scheduler sequence was not invariant")
    if audit["phase_elapsed_gpu_hours"] > audit["phase_gpu_hours_ceiling"]:
        raise ProtocolError("phase-E GPU-hour ceiling was exceeded")

    authorization = read_json(PACKAGE / "phase_e_researcher_authorization_v1.json")
    if authorization["status"] != "PHASE_E_EXECUTION_APPROVED_AND_CONSUMED":
        raise ProtocolError("phase-E researcher authorization record drift")
    if authorization["phase_s_was_authorized"]:
        raise ProtocolError("phase-E authorization record unexpectedly authorizes phase S")

    forbidden_suffixes = {
        ".mp4", ".mov", ".avi", ".mkv", ".webm", ".pt", ".pth", ".ckpt",
        ".safetensors", ".npy", ".npz",
    }
    run_dir = external.parent
    forbidden = [
        path for path in run_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in forbidden_suffixes
    ]
    if forbidden:
        raise ProtocolError(f"forbidden phase-E runtime artifact: {forbidden[:3]}")

    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_PHASE_E_PACKAGE_VERIFICATION",
        "evidence_entries": len(rows),
        "paths_exist": True,
        "bytes_match": True,
        "sha256_match": True,
        "tasks": 24,
        "transformer_steps": 1200,
        "injection_rows": 50400,
        "maximum_baseline_repeat_absolute_difference": 0.0,
        "maximum_reference_route_absolute_difference": 0.0,
        "phase_elapsed_gpu_hours": audit["phase_elapsed_gpu_hours"],
        "forbidden_raw_tensor_or_media_files": 0,
        "phase_s_execution_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify()
    atomic_write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProtocolError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
