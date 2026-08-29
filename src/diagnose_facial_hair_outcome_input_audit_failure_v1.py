#!/usr/bin/env python3
"""Authorized single-source diagnosis of the run-001 facial-hair audit failure."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path


STATUS = "FACIAL_HAIR_OUTCOME_SINGLE_SOURCE_CPU_DIAGNOSIS_APPROVED"
TARGET_COLUMN = "primary_positive_minus_control"


class DiagnosisError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise DiagnosisError("authorization must be a JSON object")
    return value


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise DiagnosisError(f"refusing to overwrite diagnosis: {path}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def diagnose(authorization_path: Path, output_path: Path) -> dict:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise DiagnosisError("CUDA_VISIBLE_DEVICES must be explicitly empty")
    if os.environ.get("HF_HUB_OFFLINE") != "1" or os.environ.get("TRANSFORMERS_OFFLINE") != "1":
        raise DiagnosisError("offline flags must be set")
    forbidden = ("torch", "transformers", "diffusers", "consisid")
    if any(
        any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)
        for name in sys.modules
    ):
        raise DiagnosisError("forbidden ML module imported")

    authorization = read_json(authorization_path)
    if authorization.get("status") != STATUS:
        raise DiagnosisError("single-source diagnosis is not authorized")
    if authorization["authorized"].get("source_name") != "facial_hair_outcome":
        raise DiagnosisError("authorization source mismatch")
    blocked = authorization.get("not_authorized", {})
    if any(blocked.get(name) is not True for name in (
        "numeric_value_export", "pair_outcome_construction", "outcome_trace_join",
        "association_computation", "cross_source_diagnosis", "model_loading", "gpu_execution",
    )):
        raise DiagnosisError("authorization no longer blocks a forbidden operation")
    expected_output = Path(authorization["run_001"]).resolve() / output_path.name
    if output_path.resolve() != expected_output:
        raise DiagnosisError("diagnosis output path mismatch")
    source = authorization["audited_source"]
    source_path = Path(source["path"]).resolve()
    if not source_path.is_file() or source_path.is_symlink():
        raise DiagnosisError("source is missing or a symlink")
    if source_path.stat().st_size != int(source["bytes"]) or sha256(source_path) != source["sha256"]:
        raise DiagnosisError("source bytes or SHA256 mismatch")

    with source_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        rows = list(reader)
    required = {"attribute", "formal_pair_id", TARGET_COLUMN}
    if not required <= set(header):
        raise DiagnosisError("required diagnostic columns missing")
    attribute_rows = Counter(row["attribute"] for row in rows)
    missing_by_attribute = Counter(
        row["attribute"] for row in rows if row[TARGET_COLUMN] == ""
    )
    missing_keys = sorted(
        f"{row['attribute']}|{row['formal_pair_id']}"
        for row in rows if row[TARGET_COLUMN] == ""
    )
    total_missing = len(missing_keys)
    target_missing = missing_by_attribute.get("facial_hair", 0)
    non_target_missing = total_missing - target_missing
    condition_passed = (
        total_missing == 9
        and target_missing == 0
        and non_target_missing == 9
        and set(missing_by_attribute) <= {"eyeglasses"}
    )
    result = {
        "schema_version": 1,
        "status": (
            "PASS_CONDITIONAL_CORRECTION_CRITERION_ALL_NINE_MISSING_ARE_NON_TARGET"
            if condition_passed else "FAIL_CONDITIONAL_CORRECTION_CRITERION"
        ),
        "source_name": "facial_hair_outcome",
        "source_path": str(source_path),
        "source_bytes": source_path.stat().st_size,
        "source_sha256": sha256(source_path),
        "header": header,
        "rows": len(rows),
        "rows_by_attribute": dict(sorted(attribute_rows.items())),
        "missing_target_field_total": total_missing,
        "missing_target_field_by_attribute": dict(sorted(missing_by_attribute.items())),
        "missing_target_field_keys": missing_keys,
        "target_facial_hair_missing": target_missing,
        "non_target_missing": non_target_missing,
        "conditional_correction_criterion_passed": condition_passed,
        "numeric_values_read": False,
        "numeric_values_exported": False,
        "other_sources_opened": 0,
        "pair_outcome_constructed": False,
        "outcome_trace_joined": False,
        "association_computed": False,
        "model_loaded": False,
        "gpu_used": False,
        "network_used": False,
    }
    atomic_json(output_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = diagnose(args.authorization, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["conditional_correction_criterion_passed"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DiagnosisError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
