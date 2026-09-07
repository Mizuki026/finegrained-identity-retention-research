#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import controlled_lfe_projection_exchange_protocol_v1 as protocol
import verify_controlled_lfe_projection_exchange_scientific_generation_v1 as verifier
import verify_controlled_lfe_projection_exchange_scientific_seed_family_v1 as family_verifier


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def make_shard(root: Path, seed_index: int) -> tuple[Path, Path]:
    run_dir, private = root / f"scalar_{seed_index}", root / f"private_{seed_index}"
    run_dir.mkdir()
    private.mkdir()
    seed = protocol.SEEDS[seed_index - 1]
    summary = {
        "status": verifier.SUMMARY_STATUS, "phase": "scientific",
        "fresh_preprocessing_calls": 40, "direct_lfe_acquisitions": 40,
        "directions_constructed": 640, "trajectory_rows": 120,
        "scheduler_steps": 6000, "raw_identity_lfe_or_direction_tensor_files": 0,
        "elapsed_gpu_hours": 10.0, "phase_gpu_hours_ceiling": 18.0,
        "shard_family_id": "controlled_lfe_projection_exchange_scientific_seed_shards_v1",
        "scientific_shard_id": f"seed_{seed_index}", "scientific_seed_index": seed_index,
        "scientific_seed": seed, "seed_complete_shard": True,
        "conditions_co_resident": list(protocol.CONDITIONS),
    }
    (run_dir / "execution_summary_v1.json").write_text(json.dumps(summary) + "\n", encoding="utf-8")
    rows = []
    for plan in protocol.execution_plan():
        if int(plan["seed_index"]) != seed_index:
            continue
        task, condition = str(plan["planned_task_id"]), str(plan["condition"])
        name = protocol.sha256_text(f"{protocol.NAMESPACE}|private_latent|{task}|{condition}")[:32] + ".safetensors"
        path = private / name
        path.write_bytes(f"synthetic:{seed_index}:{task}:{condition}".encode())
        rows.append({
            **plan, "status": "COMPLETE",
            "initial_denoising_input_sha256": hashlib.sha256(task.encode()).hexdigest(),
            "spatial_reference_route_sha256": hashlib.sha256((task + "|spatial").encode()).hexdigest(),
            "hidden_shape": "1x13x32x60x90", "hidden_dtype": "torch.bfloat16",
            "hidden_device_type": "cuda", "lfe_hook_calls": 50,
            "private_latent_path": str(path), "private_latent_bytes": path.stat().st_size,
            "private_latent_sha256": verifier.sha256(path), "decoded_media_persisted": False,
        })
    write_csv(run_dir / "trajectory_status_v1.csv", rows)
    acquisitions = []
    for attribute in protocol.ATTRIBUTES:
        for pair in protocol.pair_ids(attribute):
            for role in protocol.ROLES:
                unit = protocol.unit_id(attribute, pair, role)
                acquisitions.append({
                    "planned_unit_id": unit, "attribute": attribute, "formal_pair_id": pair,
                    "role": role, "canonical_dtype": "float32",
                    "lfe_sha256": hashlib.sha256(f"lfe:{unit}".encode()).hexdigest(),
                })
    write_csv(run_dir / "acquisition_scalar_hashes_v1.csv", acquisitions)
    directions = []
    for attribute in protocol.ATTRIBUTES:
        for pair in protocol.pair_ids(attribute):
            for token in range(protocol.LFE_TOKENS):
                directions.append({
                    "attribute": attribute, "formal_pair_id": pair, "token_index": token,
                    "direction_sha256": hashlib.sha256(f"direction:{attribute}:{pair}:{token}".encode()).hexdigest(),
                    "sham_direction_sha256": hashlib.sha256(f"sham:{attribute}:{pair}:{token}".encode()).hexdigest(),
                })
    write_csv(run_dir / "direction_scalar_diagnostics_v1.csv", directions)
    return run_dir, private


class ScientificGenerationVerifierTests(unittest.TestCase):
    def test_complete_seed_shard_and_missing_file_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, private = make_shard(Path(temporary), 1)
            result = verifier.verify_outputs(run_dir, private, 1)
            self.assertEqual(result["private_final_latent_files"], 120)
            self.assertEqual(result["cross_condition_input_invariants_verified"], 40)
            next(iter(private.iterdir())).unlink()
            with self.assertRaises(verifier.ScientificGenerationVerificationError):
                verifier.verify_outputs(run_dir, private, 1)

    def test_complete_four_seed_family_and_hash_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shard_paths = [make_shard(root, index) for index in range(1, 5)]
            for index, (run_dir, private) in enumerate(shard_paths, 1):
                result = verifier.verify_outputs(run_dir, private, index)
                (run_dir / "independent_verification_v1.json").write_text(
                    json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
            result = family_verifier.verify_family(
                [item[0] for item in shard_paths], [item[1] for item in shard_paths]
            )
            self.assertEqual(result["scientific_trajectories"], 480)
            self.assertTrue(result["cross_shard_direction_and_sham_hashes_identical"])
            with (shard_paths[3][0] / "direction_scalar_diagnostics_v1.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["direction_sha256"] = "0" * 64
            write_csv(shard_paths[3][0] / "direction_scalar_diagnostics_v1.csv", rows)
            with self.assertRaises(family_verifier.ScientificSeedFamilyVerificationError):
                family_verifier.verify_family(
                    [item[0] for item in shard_paths], [item[1] for item in shard_paths]
                )


if __name__ == "__main__":
    unittest.main()
