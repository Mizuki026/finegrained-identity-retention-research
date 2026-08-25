#!/usr/bin/env python3
"""Verify the frozen Phase-S correction execution package without ML imports."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
GOVERNANCE = REPO / "governance" / "mechanism_trace_phase_s_correction_v1"
MANIFEST = GOVERNANCE / "correction_evidence_manifest_v1.csv"
FUTURE_AUTHORIZATION = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/"
    "phase_s_run_002_execution_authorization_v1.json"
)
FUTURE_RUN = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_002"
)


class VerificationError(RuntimeError):
    """Fail-closed package verification error."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO / path


def verify() -> dict:
    require("torch" not in sys.modules, "package verifier imported torch")
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    require(len(rows) == 15, f"expected 15 evidence rows, found {len(rows)}")
    require(len({row["evidence_id"] for row in rows}) == 15, "duplicate evidence IDs")
    for row in rows:
        path = resolve(row["path"])
        require(path.is_file(), f"evidence missing: {path}")
        require(path.stat().st_size == int(row["bytes"]), f"byte mismatch: {path}")
        require(sha256(path) == row["sha256"], f"SHA256 mismatch: {path}")

    authorization = json.loads(
        (GOVERNANCE / "researcher_protocol_correction_authorization_v1.json").read_text()
    )
    independent = json.loads(
        (GOVERNANCE / "independent_protocol_correction_verification_v1.json").read_text()
    )
    dry_summary = json.loads(
        (GOVERNANCE / "no_weight_dry_run_v1" / "dry_run_summary_v1.json").read_text()
    )
    dry_verification = json.loads(
        (GOVERNANCE / "no_weight_dry_run_verification_v1.json").read_text()
    )
    require(
        independent["status"]
        == "PASS_INDEPENDENT_PHASE_S_PROTOCOL_CORRECTION_VERIFICATION",
        "independent correction verification did not pass",
    )
    require(independent["cpu_tests_passed"] == 17, "CPU test count mismatch")
    require(
        independent["representation_stages"] == 9
        and independent["deterministic_cross_seed_stages"] == 8,
        "representation stage structure mismatch",
    )
    require(
        independent["four_seed_mean_without_second_normalization"] is True,
        "four-seed mean policy mismatch",
    )
    require(
        dry_summary["task_count"] == 184
        and dry_summary["transformer_steps"] == 9200
        and dry_summary["torch_imported"] is False,
        "dry-run summary mismatch",
    )
    require(
        dry_verification["status"] == "PASS_INDEPENDENT_DRY_RUN_VERIFICATION",
        "independent dry-run did not pass",
    )
    require(
        authorization["gpu_execution_authorized"] is False
        and authorization["model_loading_authorized"] is False,
        "researcher authorization unexpectedly permits execution",
    )
    require(not FUTURE_AUTHORIZATION.exists(), "replacement authorization already exists")
    require(not FUTURE_RUN.exists(), "Phase-S run-002 directory already exists")
    require("torch" not in sys.modules, "package verifier imported torch during checks")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_PHASE_S_CORRECTION_PACKAGE_VERIFICATION",
        "evidence_entries": len(rows),
        "paths_exist": True,
        "bytes_match": True,
        "sha256_match": True,
        "cpu_tests_passed": 17,
        "representation_stages": 9,
        "deterministic_cross_seed_stages": 8,
        "dry_run_tasks": 184,
        "dry_run_transformer_steps": 9200,
        "cumulative_attempt_ceiling": 186,
        "cumulative_transformer_step_ceiling": 9300,
        "model_loaded": False,
        "gpu_compute_used": False,
        "replacement_phase_s_authorization_exists": False,
        "phase_s_run_002_exists": False,
        "phase_s_gpu_execution_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise VerificationError(f"refusing to overwrite package verification: {args.output}")
    result = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
