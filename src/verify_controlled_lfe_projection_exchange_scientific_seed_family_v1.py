#!/usr/bin/env python3
"""CPU-only 4/4 completeness and scalar-hash verifier for the seed-shard family."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import controlled_lfe_projection_exchange_protocol_v1 as protocol
import verify_controlled_lfe_projection_exchange_scientific_generation_v1 as shard_verifier


class ScientificSeedFamilyVerificationError(RuntimeError):
    """Raised when the four-shard scientific family is incomplete or inconsistent."""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def verify_family(run_dirs: list[Path], private_dirs: list[Path]) -> dict:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ScientificSeedFamilyVerificationError("family verifier must be CUDA-hidden")
    if len(run_dirs) != 4 or len(private_dirs) != 4:
        raise ScientificSeedFamilyVerificationError("exactly four shard run and private directories required")
    all_plan_keys: set[tuple[str, str]] = set()
    all_private_paths: set[Path] = set()
    all_private_hashes: set[str] = set()
    baseline_acquisitions: dict[str, str] | None = None
    baseline_directions: dict[tuple[str, str, int], tuple[str, str]] | None = None
    total_bytes = 0
    total_gpu_hours = 0.0
    for seed_index, (run_dir, private_dir) in enumerate(zip(run_dirs, private_dirs, strict=True), 1):
        result = shard_verifier.verify_outputs(run_dir, private_dir, seed_index)
        verification_path = run_dir / "independent_verification_v1.json"
        if not verification_path.is_file() or json.loads(verification_path.read_text(encoding="utf-8")) != result:
            raise ScientificSeedFamilyVerificationError(f"shard {seed_index} independent verification missing or drifted")
        rows = _read_csv(run_dir / "trajectory_status_v1.csv")
        for row in rows:
            key = (row["planned_task_id"], row["condition"])
            if key in all_plan_keys:
                raise ScientificSeedFamilyVerificationError("duplicate trajectory across shards")
            all_plan_keys.add(key)
            path = Path(row["private_latent_path"])
            digest = row["private_latent_sha256"]
            if path in all_private_paths or digest in all_private_hashes:
                raise ScientificSeedFamilyVerificationError("duplicate private latent path or hash across shards")
            all_private_paths.add(path)
            all_private_hashes.add(digest)
        acquisitions = {row["planned_unit_id"]: row["lfe_sha256"] for row in _read_csv(run_dir / "acquisition_scalar_hashes_v1.csv")}
        directions = {
            (row["attribute"], row["formal_pair_id"], int(row["token_index"])):
            (row["direction_sha256"], row["sham_direction_sha256"])
            for row in _read_csv(run_dir / "direction_scalar_diagnostics_v1.csv")
        }
        if baseline_acquisitions is None:
            baseline_acquisitions = acquisitions
            baseline_directions = directions
        elif acquisitions != baseline_acquisitions or directions != baseline_directions:
            raise ScientificSeedFamilyVerificationError("cross-shard acquisition or direction scalar hashes differ")
        total_bytes += int(result["private_final_latent_bytes"])
        total_gpu_hours += float(result["gpu_hours"])
    expected_keys = {(str(row["planned_task_id"]), str(row["condition"])) for row in protocol.execution_plan()}
    if all_plan_keys != expected_keys or len(all_private_paths) != 480:
        raise ScientificSeedFamilyVerificationError("4/4 seed-shard family does not reconstruct exact frozen 480-trajectory plan")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_CONTROLLED_INTERVENTION_SCIENTIFIC_FOUR_SEED_SHARD_FAMILY_VERIFICATION",
        "shard_family_id": "controlled_lfe_projection_exchange_scientific_seed_shards_v1",
        "complete_seed_shards": 4, "scientific_trajectories": 480,
        "scheduler_steps": 24000, "source_tasks": 160, "formal_units": 40,
        "cross_condition_input_invariants_verified": 160,
        "cross_shard_acquisition_hashes_identical": True,
        "cross_shard_direction_and_sham_hashes_identical": True,
        "private_final_latent_files": 480, "private_final_latent_bytes": total_bytes,
        "total_gpu_hours": total_gpu_hours, "global_gpu_hours_ceiling": 72.0,
        "condition_sharding_used": False, "reduced_family_used": False,
        "decode_authorized": False, "outcomes_opened": False, "model_loaded_by_verifier": False,
        "gpu_used_by_verifier": False, "network_used": False,
        "next_gate": "SEPARATE_RESEARCHER_AUTHORIZATION_FOR_DECODE_ONLY_AFTER_4_OF_4_PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard-run-dir", action="append", required=True, type=Path)
    parser.add_argument("--shard-private-dir", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if "torch" in sys.modules:
        raise ScientificSeedFamilyVerificationError("family verifier CLI must start torch-free")
    result = verify_family(args.shard_run_dir, args.shard_private_dir)
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ScientificSeedFamilyVerificationError, shard_verifier.ScientificGenerationVerificationError, OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
