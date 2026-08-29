#!/usr/bin/env python3
"""Independent verification of the linkage implementation-only package."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "governance/mechanism_outcome_linkage_implementation_v1"
MANIFEST = PACKAGE / "implementation_evidence_manifest_v1.csv"


class PackageError(RuntimeError):
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
        raise PackageError(f"expected JSON object: {path}")
    return value


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO / path


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise PackageError(f"refusing to overwrite package verification: {path}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def verify_stdlib_only(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden = {"torch", "transformers", "diffusers", "numpy", "scipy", "consisid"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    overlap = imported & forbidden
    if overlap:
        raise PackageError(f"forbidden implementation import in {path}: {sorted(overlap)}")


def verify() -> dict:
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 13:
        raise PackageError(f"implementation evidence count mismatch: {len(rows)}")
    if len({row["evidence_id"] for row in rows}) != len(rows):
        raise PackageError("duplicate implementation evidence ID")
    if len({row["path"] for row in rows}) != len(rows):
        raise PackageError("duplicate implementation evidence path")
    for row in rows:
        path = resolve(row["path"])
        if not path.is_file() or path.is_symlink():
            raise PackageError(f"missing or symlink evidence: {path}")
        if path.stat().st_size != int(row["bytes"]):
            raise PackageError(f"evidence byte drift: {path}")
        if sha256(path) != row["sha256"]:
            raise PackageError(f"evidence SHA256 drift: {path}")

    decision = read_json(PACKAGE / "researcher_design_authorization_v1.json")
    if decision.get("status") != "ALL_SEVEN_DESIGN_DECISIONS_ACCEPTED_IMPLEMENTATION_ONLY":
        raise PackageError("researcher decision status mismatch")
    forbidden_now = set(decision.get("not_authorized", []))
    if not {"outcome_trace_join", "association_computation_on_frozen_inputs", "model_loading", "gpu_execution"} <= forbidden_now:
        raise PackageError("researcher decision no longer blocks real execution or GPU work")

    plan = read_json(PACKAGE / "approved_analysis_plan_v1.json")
    execution = plan.get("execution", {})
    if not execution.get("implementation_authorized") or not execution.get("no_weight_dry_run_authorized"):
        raise PackageError("implementation authorization drift")
    if execution.get("formal_input_audit_authorized") or execution.get("input_join_authorized") or execution.get("association_computation_authorized"):
        raise PackageError("approved plan now permits forbidden real execution")
    if len(plan.get("secondary_representation_stages", [])) != 8:
        raise PackageError("secondary representation family count mismatch")
    if plan["secondary_injection_family"].get("cells_per_attribute") != 18:
        raise PackageError("secondary injection family count mismatch")

    template = read_json(PACKAGE / "cpu_execution_authorization_template_v1.json")
    if template.get("status") != "TEMPLATE_NOT_AUTHORIZATION" or any(template.get("authority", {}).values()):
        raise PackageError("CPU execution template accidentally grants authority")

    tests = read_json(PACKAGE / "cpu_test_verification_v1.json")
    if tests.get("status") != "PASS_CPU_ONLY_SYNTHETIC_TEST_SUITE" or tests.get("tests_run") != 9:
        raise PackageError("CPU synthetic test evidence mismatch")
    if tests.get("failures") or tests.get("errors") or tests.get("gpu_used") or tests.get("real_association_computed"):
        raise PackageError("CPU test evidence reports a forbidden or failed action")

    dry = read_json(REPO / "derived/mechanism_outcome_linkage_v1_dry_run/dry_run_summary_v1.json")
    dry_verify = read_json(REPO / "derived/mechanism_outcome_linkage_v1_dry_run/dry_run_independent_verification_v1.json")
    if dry.get("status") != "PASS_NO_WEIGHT_DRY_RUN_NO_REAL_INPUT_ACCESS":
        raise PackageError("no-weight dry-run did not pass")
    if dry.get("input_files_opened") or dry.get("association_computed") or dry.get("joined_rows_created") != 0:
        raise PackageError("no-weight dry-run reports real input, join, or association activity")
    if dry_verify.get("status") != "PASS_INDEPENDENT_NO_WEIGHT_DRY_RUN_VERIFICATION":
        raise PackageError("independent dry-run verification did not pass")

    for source in (
        REPO / "src/analyze_mechanism_outcome_linkage_v1.py",
        REPO / "src/verify_mechanism_outcome_linkage_v1.py",
        Path(__file__).resolve(),
    ):
        verify_stdlib_only(source)

    schema = read_json(PACKAGE / "output_schema_v1.json")
    if schema["aggregate_outputs"]["primary_associations_v1.csv"]["rows"] != 2:
        raise PackageError("primary output count drift")
    if schema["aggregate_outputs"]["secondary_representation_associations_v1.csv"]["rows"] != 16:
        raise PackageError("secondary representation output count drift")
    if schema["aggregate_outputs"]["secondary_injection_associations_v1.csv"]["rows"] != 36:
        raise PackageError("secondary injection output count drift")

    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_IMPLEMENTATION_ONLY_PACKAGE_VERIFICATION",
        "evidence_entries": len(rows),
        "paths_exist": True,
        "bytes_match": True,
        "sha256_match": True,
        "cpu_synthetic_tests_passed": 9,
        "dry_run_real_inputs_opened": False,
        "dry_run_joined_rows": 0,
        "dry_run_association_computed": False,
        "stdlib_only": True,
        "model_loaded": False,
        "gpu_used": False,
        "formal_input_audit_authorized": False,
        "input_join_authorized": False,
        "association_computation_authorized": False
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify()
    if args.output:
        atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PackageError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
