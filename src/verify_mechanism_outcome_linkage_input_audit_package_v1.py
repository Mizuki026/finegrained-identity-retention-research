#!/usr/bin/env python3
"""Independent package verification for formal linkage input-audit run-002."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import stat
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "governance/mechanism_outcome_linkage_input_audit_v1"
RUN_ROOT = Path("/root/autodl-tmp/finegrained/mechanism_outcome_linkage_v1_input_audit")
SOURCE_COUNTS = {
    "eyeglasses_outcome": (40, 40, 40),
    "facial_hair_outcome": (20, 20, 10),
    "representation_margins": (180, 180, 180),
    "injection_pair_grid": (360, 360, 360),
}


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


def verify_file_binding(binding: dict, label: str) -> Path:
    path = resolve(binding["path"])
    if not path.is_file() or path.is_symlink():
        raise PackageError(f"missing or symlink binding: {label}")
    if path.stat().st_size != int(binding["bytes"]) or sha256(path) != binding["sha256"]:
        raise PackageError(f"byte or SHA256 drift: {label}")
    return path


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
    if imported & forbidden:
        raise PackageError(f"forbidden import in {path}")


def verify() -> dict:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise PackageError("CUDA_VISIBLE_DEVICES must be explicitly empty")
    authorization = read_json(PACKAGE / "input_audit_run_002_execution_authorization_v1.json")
    if authorization.get("status") != "CPU_ONLY_FORMAL_INPUT_AUDIT_APPROVED" or authorization.get("run_id") != "run_002":
        raise PackageError("run-002 authorization status mismatch")
    blocked = authorization.get("not_authorized", {})
    for name in (
        "pair_outcome_construction", "outcome_trace_join", "spearman_or_other_association",
        "cross_source_value_comparison", "model_loading", "gpu_execution", "network_access",
    ):
        if blocked.get(name) is not True:
            raise PackageError(f"run-002 authorization no longer blocks {name}")
    verify_file_binding(authorization["correction_binding"], "correction freeze")
    verify_file_binding(authorization["run_001_abort_binding"], "run-001 abort freeze")
    for label, binding in authorization["code"].items():
        verify_stdlib_only(verify_file_binding(binding, label))

    run_001 = RUN_ROOT / "run_001"
    writable_run_001 = [
        path for path in run_001.rglob("*")
        if stat.S_IMODE(path.stat().st_mode) & 0o222
    ]
    if stat.S_IMODE(run_001.stat().st_mode) & 0o222 or writable_run_001:
        raise PackageError("run-001 immutable history contains writable entries")
    abort = read_json(PACKAGE / "input_audit_run_001_abort_freeze_v1.json")
    if abort.get("status") != "IMMUTABLE_AUDIT_ABORT_NO_REUSE_NO_LINKAGE_EXECUTION":
        raise PackageError("run-001 abort status mismatch")
    diagnosis = read_json(run_001 / "facial_hair_outcome_failure_diagnosis_v1.json")
    if not diagnosis.get("conditional_correction_criterion_passed"):
        raise PackageError("conditional correction criterion did not pass")
    if diagnosis.get("target_facial_hair_missing") != 0 or diagnosis.get("non_target_missing") != 9:
        raise PackageError("run-001 diagnosis counts drift")

    run_002 = RUN_ROOT / "run_002"
    if run_002.resolve() != Path(authorization["external_runtime"]).resolve():
        raise PackageError("run-002 runtime binding mismatch")
    expected_names = {
        "audit_summary_v1.json", "binding_v1.json", "keys_v1.csv",
        "independent_verification_v1.json",
    }
    for source_name, (rows, keys, finite) in SOURCE_COUNTS.items():
        source_dir = run_002 / source_name
        actual_names = {path.name for path in source_dir.iterdir() if path.is_file()}
        if actual_names != expected_names:
            raise PackageError(f"run-002 artifact universe mismatch: {source_name}")
        summary = read_json(source_dir / "audit_summary_v1.json")
        verification = read_json(source_dir / "independent_verification_v1.json")
        binding = read_json(source_dir / "binding_v1.json")
        if summary.get("status") != "PASS_FORMAL_SINGLE_SOURCE_INPUT_AUDIT":
            raise PackageError(f"source audit did not pass: {source_name}")
        if verification.get("status") != "PASS_INDEPENDENT_FORMAL_SINGLE_SOURCE_INPUT_AUDIT_VERIFICATION":
            raise PackageError(f"source independent verification did not pass: {source_name}")
        if (summary.get("rows"), summary.get("unique_keys"), summary.get("finite_values_checked")) != (rows, keys, finite):
            raise PackageError(f"source count mismatch: {source_name}")
        if binding.get("expected_keys") is None or len(binding["expected_keys"]) != keys:
            raise PackageError(f"external exact key binding mismatch: {source_name}")
        source_binding = authorization["sources"][source_name]
        source_path = verify_file_binding(source_binding, source_name)
        if binding.get("path") != str(source_path.resolve()):
            raise PackageError(f"audited source path mismatch: {source_name}")
        forbidden_true = (
            "pair_outcome_constructed", "outcome_trace_joined", "association_computed",
            "numeric_values_exported", "model_loaded", "gpu_used", "network_used",
        )
        if any(summary.get(field) is not False for field in forbidden_true):
            raise PackageError(f"source audit reports forbidden action: {source_name}")
        if summary.get("other_sources_opened") != 0 or verification.get("other_sources_opened") != 0:
            raise PackageError(f"cross-source access reported: {source_name}")

    forbidden_runtime_names = [
        path for path in run_002.rglob("*")
        if path.is_file() and any(token in path.name for token in ("joined", "association", "spearman"))
    ]
    if forbidden_runtime_names:
        raise PackageError("forbidden linkage output found in input-audit runtime")
    tests = read_json(PACKAGE / "cpu_test_verification_v1.json")
    if tests.get("status") != "PASS_CPU_ONLY_INPUT_AUDIT_SYNTHETIC_TESTS" or tests.get("tests_run") != 5:
        raise PackageError("CPU test evidence mismatch")
    summary = read_json(PACKAGE / "run_002_input_audit_summary_v1.json")
    if summary.get("status") != "PASS_ALL_FOUR_FORMAL_INPUT_AUDITS_AND_INDEPENDENT_VERIFICATIONS":
        raise PackageError("run-002 package summary status mismatch")
    if any(summary["safety_state"].get(name) for name in (
        "numeric_values_in_git", "pair_outcome_constructed", "outcome_trace_joined",
        "association_computed", "model_loaded", "gpu_used", "network_used",
    )):
        raise PackageError("package summary reports a forbidden action")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_FORMAL_INPUT_AUDIT_PACKAGE_VERIFICATION",
        "run_001_immutable_nonreusable": True,
        "run_002_sources_passed": 4,
        "run_002_independent_verifications_passed": 4,
        "exact_headers_bound": True,
        "exact_key_universes_bound_external_only": True,
        "missing_target_values": 0,
        "duplicate_keys": 0,
        "nonfinite_target_values": 0,
        "pair_outcome_constructed": False,
        "outcome_trace_joined": False,
        "association_computed": False,
        "model_loaded": False,
        "gpu_used": False,
        "network_used": False,
        "linkage_execution_authorized": False,
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
