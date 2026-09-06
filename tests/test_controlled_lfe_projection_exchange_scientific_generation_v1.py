#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import controlled_lfe_projection_exchange_protocol_v1 as protocol
import verify_controlled_lfe_projection_exchange_scientific_generation_v1 as verifier


class ScientificGenerationVerifierTests(unittest.TestCase):
    def test_complete_synthetic_private_generation_and_missing_file_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, private = root / "scalar", root / "private"
            run_dir.mkdir()
            private.mkdir()
            summary = {
                "status": verifier.SUMMARY_STATUS, "phase": "scientific",
                "fresh_preprocessing_calls": 40, "direct_lfe_acquisitions": 40,
                "directions_constructed": 640, "trajectory_rows": 480,
                "scheduler_steps": 24000, "raw_identity_lfe_or_direction_tensor_files": 0,
                "elapsed_gpu_hours": 40.0, "phase_gpu_hours_ceiling": 72.0,
            }
            (run_dir / "execution_summary_v1.json").write_text(json.dumps(summary) + "\n")
            rows = []
            for plan in protocol.execution_plan():
                task, condition = str(plan["planned_task_id"]), str(plan["condition"])
                name = protocol.sha256_text(f"{protocol.NAMESPACE}|private_latent|{task}|{condition}")[:32] + ".safetensors"
                path = private / name
                path.write_bytes(f"synthetic:{task}:{condition}".encode())
                rows.append({**plan, "status": "COMPLETE",
                             "initial_denoising_input_sha256": hashlib.sha256(task.encode()).hexdigest(),
                             "spatial_reference_route_sha256": hashlib.sha256((task + "|spatial").encode()).hexdigest(),
                             "hidden_shape": "1x13x32x60x90", "hidden_dtype": "torch.bfloat16",
                             "hidden_device_type": "cuda", "lfe_hook_calls": 50,
                             "private_latent_path": str(path), "private_latent_bytes": path.stat().st_size,
                             "private_latent_sha256": verifier.sha256(path), "decoded_media_persisted": False})
            fields = tuple(rows[0])
            with (run_dir / "trajectory_status_v1.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            result = verifier.verify_outputs(run_dir, private)
            self.assertEqual(result["private_final_latent_files"], 480)
            self.assertEqual(result["cross_condition_input_invariants_verified"], 160)
            next(iter(private.iterdir())).unlink()
            with self.assertRaises(verifier.ScientificGenerationVerificationError):
                verifier.verify_outputs(run_dir, private)


if __name__ == "__main__":
    unittest.main()
