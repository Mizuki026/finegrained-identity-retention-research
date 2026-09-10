#!/usr/bin/env python3
"""Independent CPU-only verifier for Seed 1 direction-evidence recovery."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import controlled_lfe_projection_exchange_protocol_v1 as protocol

STATUS = "COMPLETE_PENDING_INDEPENDENT_DIRECTION_EVIDENCE_RECOVERY_VERIFICATION"


class DirectionEvidenceRecoveryVerificationError(RuntimeError):
    """Raised when recovered scalar evidence is incomplete or inconsistent."""


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sha(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def verify(run_dir: Path) -> dict:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise DirectionEvidenceRecoveryVerificationError("recovery verifier must start CUDA-hidden and torch-free")
    summary = protocol.read_json(run_dir / "recovery_summary_v1.json")
    expected_summary = {
        "status": STATUS, "scientific_shard_id": "seed_1", "recovery_run_id": "run_001",
        "recovered_acquisitions": 40, "exact_lfe_hash_matches": 40,
        "recovered_direction_hash_pairs": 640, "generation_pipeline_loaded": False,
        "trajectories_executed": 0, "latents_or_media_generated": 0, "private_latents_modified": 0,
        "phase_gpu_hours_ceiling": 2.0,
    }
    if any(summary.get(key) != value for key, value in expected_summary.items()):
        raise DirectionEvidenceRecoveryVerificationError("recovery summary drift")
    elapsed = float(summary.get("elapsed_gpu_hours", -1))
    if not 0 <= elapsed <= 2:
        raise DirectionEvidenceRecoveryVerificationError("recovery elapsed GPU hours drift")
    acquisitions = _rows(run_dir / "recovered_acquisition_hash_comparison_v1.csv")
    expected_units = {protocol.unit_id(a, p, r) for a in protocol.ATTRIBUTES for p in protocol.pair_ids(a) for r in protocol.ROLES}
    if len(acquisitions) != 40 or {row.get("planned_unit_id") for row in acquisitions} != expected_units:
        raise DirectionEvidenceRecoveryVerificationError("recovered acquisition universe drift")
    if any(row.get("exact_match") != "True" or row.get("expected_lfe_sha256") != row.get("recovered_lfe_sha256") or not _sha(row.get("expected_lfe_sha256", "")) for row in acquisitions):
        raise DirectionEvidenceRecoveryVerificationError("40/40 exact recovered LFE hash gate failed")
    directions = _rows(run_dir / "recovered_direction_scalar_hashes_v1.csv")
    keys = {(row.get("attribute"), row.get("formal_pair_id"), int(row.get("token_index", -1))) for row in directions}
    expected_keys = {(a, p, t) for a in protocol.ATTRIBUTES for p in protocol.pair_ids(a) for t in range(protocol.LFE_TOKENS)}
    if len(directions) != 640 or keys != expected_keys or any(not _sha(row.get("direction_sha256", "")) or not _sha(row.get("sham_direction_sha256", "")) for row in directions):
        raise DirectionEvidenceRecoveryVerificationError("recovered 640 direction hash family drift")
    allowed = {"recovery_summary_v1.json", "recovered_acquisition_hash_comparison_v1.csv", "recovered_direction_scalar_hashes_v1.csv", "independent_recovery_verification_v1.json"}
    if {path.name for path in run_dir.iterdir() if path.is_file()} - allowed:
        raise DirectionEvidenceRecoveryVerificationError("unexpected recovery artifact")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_SCIENTIFIC_SEED_1_DIRECTION_EVIDENCE_RECOVERY_VERIFICATION",
        "exact_lfe_hash_matches": 40, "recovered_direction_hash_pairs": 640,
        "trajectory_execution": False, "generation_pipeline_loaded": False,
        "private_latents_modified": False, "gpu_used_by_verifier": False,
        "model_loaded_by_verifier": False, "reference_accessed_by_verifier": False,
        "outcome_accessed": False, "elapsed_recovery_gpu_hours": elapsed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.run_dir)
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DirectionEvidenceRecoveryVerificationError, protocol.ControlledInterventionProtocolError, OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
