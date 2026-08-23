#!/usr/bin/env python3
"""Independent stdlib verification of the mechanism-trace implementation package."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from mechanism_trace_protocol_v1 import ProtocolError, atomic_write_json, read_json, sha256


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "governance" / "mechanism_trace_implementation_v1"
MANIFEST = PACKAGE / "implementation_evidence_manifest_v1.csv"


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO / path


def verify() -> dict:
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 34:
        raise ProtocolError(f"implementation evidence count mismatch: {len(rows)}")
    if len({row["evidence_id"] for row in rows}) != len(rows):
        raise ProtocolError("implementation evidence IDs are not unique")
    if len({row["path"] for row in rows}) != len(rows):
        raise ProtocolError("implementation evidence paths are not unique")
    for row in rows:
        path = resolve_path(row["path"])
        if not path.is_file():
            raise ProtocolError(f"implementation evidence missing: {path}")
        if path.stat().st_size != int(row["bytes"]):
            raise ProtocolError(f"implementation evidence byte drift: {path}")
        if sha256(path) != row["sha256"]:
            raise ProtocolError(f"implementation evidence SHA256 drift: {path}")

    authorization = read_json(PACKAGE / "researcher_implementation_authorization_v1.json")
    if authorization["status"] != "IMPLEMENTATION_CPU_TEST_AND_NO_WEIGHT_DRY_RUN_APPROVED":
        raise ProtocolError("implementation authorization status drift")
    forbidden = set(authorization["not_authorized"])
    if not {"model_weight_loading", "model_forward_pass", "gpu_execution"} <= forbidden:
        raise ProtocolError("implementation authorization no longer blocks runtime work")

    tests = read_json(PACKAGE / "cpu_test_verification_v1.json")
    if tests["status"] != "PASS_CPU_ONLY_TEST_SUITE" or tests["tests_run"] != 14:
        raise ProtocolError("CPU test evidence mismatch")
    if tests["failures"] or tests["errors"] or tests["gpu_used"]:
        raise ProtocolError("CPU test evidence reports failure, error, or GPU use")

    compilation = read_json(PACKAGE / "static_compilation_verification_v1.json")
    if compilation["status"] != "PASS_PY_COMPILE_CPU_ONLY" or compilation["syntax_errors"]:
        raise ProtocolError("static compilation evidence mismatch")

    model_inventory = read_json(PACKAGE / "model_inventory_verification_v1.json")
    if model_inventory["status"] != "PASS_MODEL_INVENTORY_ALL_FILES":
        raise ProtocolError("model inventory verification status mismatch")
    if model_inventory["inventory_entries"] != 72 or model_inventory["model_weights_loaded"]:
        raise ProtocolError("model inventory count or no-load assertion mismatch")

    dry_run = read_json(REPO / "derived/mechanism_trace_v1_dry_run/dry_run_summary_v1.json")
    dry_verify = read_json(
        REPO / "derived/mechanism_trace_v1_dry_run/dry_run_independent_verification_v1.json"
    )
    if dry_run["task_count"] != 184 or dry_run["transformer_steps"] != 9200:
        raise ProtocolError("dry-run ceiling enumeration mismatch")
    if dry_run["torch_imported"] or dry_run["consisid_modules_imported"]:
        raise ProtocolError("dry-run reports forbidden runtime imports")
    if dry_verify["status"] != "PASS_INDEPENDENT_DRY_RUN_VERIFICATION":
        raise ProtocolError("independent dry-run verification did not pass")

    environment = read_json(PACKAGE / "environment_snapshot_v1.json")
    if environment["gpu_compute_used"] or environment["model_loaded"] or environment["forward_pass_run"]:
        raise ProtocolError("implementation environment evidence reports runtime work")

    schema = read_json(PACKAGE / "output_schema_v1.json")
    if schema["phase_e_expected_outputs"]["injection_summaries_v1.csv"]["rows"] != 50400:
        raise ProtocolError("phase-E output schema count drift")
    if schema["phase_s_expected_outputs"]["injection_summaries_v1.csv"]["rows"] != 336000:
        raise ProtocolError("phase-S output schema count drift")
    if schema["scientific_cpu_analysis_outputs"]["injection_finite_panel_3x3_v1.csv"]["rows"] != 36:
        raise ProtocolError("fixed 3x3 finite-panel schema count drift")

    forbidden_suffixes = {".mp4", ".pt", ".pth", ".safetensors", ".npy", ".npz"}
    forbidden_files = [
        path for root in (PACKAGE, REPO / "derived/mechanism_trace_v1_dry_run")
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in forbidden_suffixes
    ]
    if forbidden_files:
        raise ProtocolError(f"forbidden implementation-package payload: {forbidden_files[:3]}")

    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_IMPLEMENTATION_PACKAGE_VERIFICATION",
        "evidence_entries": len(rows),
        "paths_exist": True,
        "bytes_match": True,
        "sha256_match": True,
        "cpu_tests_passed": 14,
        "dry_run_tasks": 184,
        "dry_run_transformer_steps": 9200,
        "model_inventory_entries_verified": 72,
        "model_loaded": False,
        "forward_pass_run": False,
        "gpu_used": False,
        "phase_e_execution_authorized": False,
        "phase_s_execution_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify()
    if args.output:
        atomic_write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProtocolError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
