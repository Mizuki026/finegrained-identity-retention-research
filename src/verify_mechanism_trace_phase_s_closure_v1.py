#!/usr/bin/env python3
"""Verify the Phase-S run-003 closure package without ML imports."""
from __future__ import annotations

import argparse
import csv
import json
import stat
import sys
from pathlib import Path

from mechanism_trace_protocol_v1 import ProtocolError, atomic_write_json, read_json, sha256
from verify_mechanism_trace_phase_s_run_003_package_v1 import verify as verify_result_package


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "governance" / "mechanism_trace_phase_s_run_003_v1"
MANIFEST = PACKAGE / "phase_s_run_003_closure_evidence_manifest_v1.csv"
RUN = Path("/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003")
ANALYSIS = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003_analysis_v1"
)


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO / path


def require_read_only(path: Path) -> None:
    if stat.S_IMODE(path.stat().st_mode) & 0o222:
        raise ProtocolError(f"closed Phase-S evidence remains writable: {path}")


def verify() -> dict:
    if "torch" in sys.modules:
        raise ProtocolError("closure verifier imported torch before verification")
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 6:
        raise ProtocolError(f"closure evidence count mismatch: {len(rows)}")
    if len({row["evidence_id"] for row in rows}) != len(rows):
        raise ProtocolError("closure evidence IDs are not unique")
    if len({row["path"] for row in rows}) != len(rows):
        raise ProtocolError("closure evidence paths are not unique")
    for row in rows:
        path = resolve_path(row["path"])
        if not path.is_file():
            raise ProtocolError(f"closure evidence missing: {path}")
        if path.stat().st_size != int(row["bytes"]):
            raise ProtocolError(f"closure evidence byte drift: {path}")
        if sha256(path) != row["sha256"]:
            raise ProtocolError(f"closure evidence hash drift: {path}")

    result_package = verify_result_package()
    if result_package["status"] != "PASS_INDEPENDENT_PHASE_S_RUN_003_RESULT_PACKAGE_VERIFICATION":
        raise ProtocolError("underlying Phase-S result package did not pass")

    decisions = read_json(PACKAGE / "researcher_result_decisions_v1.json")
    if decisions["status"] != "PHASE_S_RUN_003_RESULTS_ACCEPTED_AND_MECHANISM_TRACE_WINDOW_CLOSED":
        raise ProtocolError("researcher result-decision status drift")
    accepted = decisions["accepted_decisions"]
    required_true = (
        "independent_verification_and_frozen_evidence_package_accepted",
        "all_160_tasks_retained",
        "primary_mixed_direction_conservative_description_accepted",
        "all_36_injection_cells_retained",
        "mechanism_trace_window_closed",
    )
    if any(accepted[key] is not True for key in required_true):
        raise ProtocolError("a required Phase-S closure decision is not accepted")
    if accepted["fallback_messages_retained_as_run_level_limitation"] != 76:
        raise ProtocolError("fallback limitation count drift")
    if accepted["eva_results_role"] != "SECONDARY_STAGE_SPECIFIC_DIAGNOSTICS_ONLY":
        raise ProtocolError("EVA diagnostic role drift")
    prohibited_true = (
        "fallback_based_exclusion_or_regeneration_authorized",
        "primary_consistent_readability_claim_supported",
        "secondary_endpoint_elevation_authorized",
        "injection_cell_selection_authorized",
        "localization_or_causal_flow_claim_supported",
    )
    if any(accepted[key] is not False for key in prohibited_true):
        raise ProtocolError("a prohibited Phase-S interpretation was accepted")
    if (
        decisions["new_analysis_authorized"]
        or decisions["new_model_loading_authorized"]
        or decisions["new_gpu_execution_authorized"]
    ):
        raise ProtocolError("closure decisions unexpectedly authorize new work")

    closure = (PACKAGE / "phase_s_run_003_closure_v1.md").read_text(encoding="utf-8")
    if "this mechanism-trace window is closed" not in closure:
        raise ProtocolError("closure status text missing")
    if "separate prospective design" not in closure:
        raise ProtocolError("future preregistration gate missing")

    for directory in (RUN, ANALYSIS):
        require_read_only(directory)
        for path in directory.iterdir():
            if path.is_file():
                require_read_only(path)
    if "torch" in sys.modules:
        raise ProtocolError("closure verifier imported torch during verification")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_PHASE_S_RUN_003_CLOSURE_VERIFICATION",
        "closure_evidence_entries": len(rows),
        "underlying_result_package_status": result_package["status"],
        "researcher_decisions_accepted": 6,
        "all_160_tasks_retained": True,
        "fallback_messages_reported_as_limitation": 76,
        "primary_conservative_description_accepted": True,
        "eva_role": "SECONDARY_STAGE_SPECIFIC_DIAGNOSTICS_ONLY",
        "all_36_injection_cells_retained": True,
        "mechanism_trace_window_closed": True,
        "runtime_artifacts_read_only": True,
        "analysis_artifacts_read_only": True,
        "new_analysis_authorized": False,
        "new_model_loading_authorized": False,
        "new_gpu_execution_authorized": False,
        "model_loaded": False,
        "gpu_compute_used": False,
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
