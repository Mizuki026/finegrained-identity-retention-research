#!/usr/bin/env python3
"""Verify the frozen Phase-S run-003 result package without ML imports."""
from __future__ import annotations

import argparse
import csv
import json
import stat
import sys
from pathlib import Path

from audit_mechanism_trace_phase_s_v1 import audit
from mechanism_trace_protocol_v1 import ProtocolError, atomic_write_json, read_json, sha256
from verify_mechanism_trace_phase_s_analysis_v1 import verify as verify_analysis


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "governance" / "mechanism_trace_phase_s_run_003_v1"
MANIFEST = PACKAGE / "phase_s_run_003_evidence_manifest_v1.csv"
RUN = Path("/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003")
ANALYSIS = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003_analysis_v1"
)
AUTHORIZATION = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/"
    "phase_s_run_003_execution_authorization_v1.json"
)
CONSOLE = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_console_run_003.log"
)
FORBIDDEN_SUFFIXES = {
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".pt", ".pth",
    ".ckpt", ".safetensors", ".npy", ".npz",
}


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO / path


def require_read_only(path: Path) -> None:
    if stat.S_IMODE(path.stat().st_mode) & 0o222:
        raise ProtocolError(f"frozen evidence remains writable: {path}")


def verify() -> dict:
    if "torch" in sys.modules:
        raise ProtocolError("package verifier imported torch before verification")
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 25:
        raise ProtocolError(f"Phase-S evidence count mismatch: {len(rows)}")
    if len({row["evidence_id"] for row in rows}) != len(rows):
        raise ProtocolError("Phase-S evidence IDs are not unique")
    if len({row["path"] for row in rows}) != len(rows):
        raise ProtocolError("Phase-S evidence paths are not unique")
    for row in rows:
        path = resolve_path(row["path"])
        if not path.is_file():
            raise ProtocolError(f"Phase-S evidence missing: {path}")
        if path.stat().st_size != int(row["bytes"]):
            raise ProtocolError(f"Phase-S evidence byte drift: {path}")
        if sha256(path) != row["sha256"]:
            raise ProtocolError(f"Phase-S evidence hash drift: {path}")

    independent = read_json(RUN / "independent_verification_v1.json")
    if independent["status"] != "PASS_INDEPENDENT_MECHANISM_TRACE_VERIFICATION":
        raise ProtocolError("Phase-S runtime verification did not pass")
    if independent["tasks"] != 160 or independent["injection_rows"] != 336000:
        raise ProtocolError("Phase-S runtime verification counts drift")
    if independent["representation_margin_rows"] != 180:
        raise ProtocolError("Phase-S representation-margin count drift")

    recorded_audit = read_json(RUN / "post_run_audit_v1.json")
    if recorded_audit["status"] != "PASS_OUTCOME_BLIND_PHASE_S_POST_RUN_AUDIT":
        raise ProtocolError("Phase-S post-run audit did not pass")
    recomputed_audit = audit(RUN, AUTHORIZATION, CONSOLE)
    if recorded_audit != recomputed_audit:
        raise ProtocolError("recorded Phase-S post-run audit differs from recomputation")

    recorded_analysis = read_json(ANALYSIS / "independent_analysis_verification_v1.json")
    if recorded_analysis["status"] != "PASS_INDEPENDENT_PHASE_S_PRESPECIFIED_ANALYSIS_VERIFICATION":
        raise ProtocolError("Phase-S analysis verification did not pass")
    recomputed_analysis = verify_analysis(RUN, ANALYSIS)
    if recorded_analysis != recomputed_analysis:
        raise ProtocolError("recorded Phase-S analysis verification differs from recomputation")

    summary = read_json(ANALYSIS / "analysis_summary_v1.json")
    if summary["status"] != "COMPLETE_PRESPECIFIED_FINITE_PANEL_DESCRIPTIONS_ONLY":
        raise ProtocolError("Phase-S analysis summary status drift")
    if summary["inferential_tests"] or summary["confidence_intervals"]:
        raise ProtocolError("Phase-S analysis unexpectedly contains inference")
    if summary["cross_attribute_ranking"]:
        raise ProtocolError("Phase-S analysis unexpectedly ranks attributes")

    authorization = read_json(AUTHORIZATION)
    if authorization["status"] != "AUTHORIZED_FOR_MECHANISM_TRACE_EXECUTION":
        raise ProtocolError("Phase-S execution authorization status drift")
    if authorization["trajectory_ceiling"] != 160:
        raise ProtocolError("Phase-S trajectory ceiling drift")
    if authorization["transformer_step_ceiling"] != 8000:
        raise ProtocolError("Phase-S Transformer-step ceiling drift")
    if authorization["cumulative_trajectory_ceiling"] != 219:
        raise ProtocolError("Phase-S cumulative trajectory ceiling drift")
    if authorization["cumulative_transformer_step_ceiling"] != 10947:
        raise ProtocolError("Phase-S cumulative Transformer-step ceiling drift")

    review = (PACKAGE / "phase_s_run_003_results_review_gate_v1.md").read_text(
        encoding="utf-8"
    )
    if "explicit researcher interpretation and disposition decisions required" not in review:
        raise ProtocolError("Phase-S result review gate status drift")
    if "## Six researcher decisions required" not in review:
        raise ProtocolError("Phase-S six-decision review gate missing")

    if list(RUN.glob("*.partial")) or list(ANALYSIS.glob("*.partial")):
        raise ProtocolError("unfinalized Phase-S partial artifact remains")
    forbidden = [
        path for root in (RUN, ANALYSIS) for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES
    ]
    if forbidden:
        raise ProtocolError(f"forbidden Phase-S artifact: {forbidden[:3]}")
    for directory in (RUN, ANALYSIS):
        require_read_only(directory)
        for path in directory.iterdir():
            if path.is_file():
                require_read_only(path)

    if "torch" in sys.modules:
        raise ProtocolError("package verifier imported torch during verification")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_PHASE_S_RUN_003_RESULT_PACKAGE_VERIFICATION",
        "evidence_entries": len(rows),
        "paths_exist": True,
        "bytes_match": True,
        "sha256_match": True,
        "tasks": 160,
        "transformer_steps": 8000,
        "injection_rows": 336000,
        "representation_margin_rows": 180,
        "finite_panel_3x3_rows": 36,
        "representation_finite_panel_rows": 18,
        "phase_elapsed_gpu_hours": recorded_audit["phase_elapsed_gpu_hours"],
        "insightface_aligned_face_fallback_messages": recorded_audit[
            "insightface_aligned_face_fallback_messages"
        ],
        "runtime_artifacts_read_only": True,
        "analysis_artifacts_read_only": True,
        "forbidden_raw_tensor_or_media_files": 0,
        "inferential_tests": False,
        "confidence_intervals": False,
        "cross_attribute_ranking": False,
        "post_run_model_loaded": False,
        "post_run_gpu_compute_used": False,
        "researcher_interpretation_and_disposition_review_required": True,
        "new_execution_authorized": False,
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
