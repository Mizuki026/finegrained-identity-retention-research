#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import controlled_lfe_projection_exchange_instrumentation_v2 as instrumentation
import controlled_lfe_projection_exchange_monolithic_runtime_v2 as runtime
import controlled_lfe_projection_exchange_protocol_v1 as protocol
import run_controlled_lfe_projection_exchange_monolithic_v2 as runner
import verify_controlled_lfe_projection_exchange_scientific_monolithic_v2 as verifier
from tests.test_controlled_lfe_projection_exchange_v1 import synthetic_lfe_panel


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def make_monolithic_fixture(root: Path) -> tuple[Path, Path]:
    run_dir, private = root / "scalar", root / "private"
    run_dir.mkdir()
    private.mkdir()
    summary = {
        "schema_version": 2, "status": verifier.SUMMARY_STATUS, "phase": "scientific",
        "scientific_run_id": "monolithic_run_002", "fresh_preprocessing_calls": 40,
        "direct_lfe_acquisitions": 40, "acquisition_units": 40,
        "directions_constructed": 640, "direction_scalar_hash_pairs": 640,
        "trajectory_rows": 480, "scheduler_steps": 24000,
        "raw_identity_lfe_or_direction_tensor_files": 0,
        "single_acquisition_transaction": True, "four_seeds_same_process": True,
        "scientific_seed_indices": [1, 2, 3, 4], "scientific_seeds": list(protocol.SEEDS),
        "conditions_co_resident": list(protocol.CONDITIONS),
        "identity_handles_cpu": True, "acquisition_inference_mode": True,
        "face_models_released_before_pipeline_load": True,
        "pipeline_loaded_after_complete_acquisition": True,
        "elapsed_gpu_hours": 36.0, "phase_gpu_hours_ceiling": 72.0,
    }
    (run_dir / "execution_summary_v2.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    rows = []
    for row in protocol.execution_plan():
        condition = str(row["condition"])
        task = str(row["planned_task_id"])
        name = protocol.sha256_text(
            f"{protocol.NAMESPACE}|monolithic_run_002|private_latent|{task}|{condition}"
        )[:32] + ".safetensors"
        path = private / name
        path.write_bytes(f"synthetic:{task}:{condition}".encode())
        rows.append({
            **{key: row[key] for key in verifier.PERSISTED_PLAN_FIELDS},
            "status": "COMPLETE", "finished_at_utc": "synthetic",
            "initial_denoising_input_sha256": hashlib.sha256(f"latent:{task}".encode()).hexdigest(),
            "spatial_reference_route_sha256": hashlib.sha256(f"spatial:{task}".encode()).hexdigest(),
            "hidden_shape": "[1, 13, 60, 90, 128]", "hidden_dtype": "torch.bfloat16",
            "hidden_device_type": "cuda", "lfe_hook_calls": 50,
            "private_latent_path": str(path), "private_latent_bytes": path.stat().st_size,
            "private_latent_sha256": verifier.sha256(path), "decoded_media_persisted": False,
        })
    write_csv(run_dir / "trajectory_status_v2.csv", rows)
    acquisitions = []
    for attribute in protocol.ATTRIBUTES:
        for pair in protocol.pair_ids(attribute):
            for role in protocol.ROLES:
                unit = protocol.unit_id(attribute, pair, role)
                acquisitions.append({
                    "planned_unit_id": unit, "attribute": attribute,
                    "formal_pair_id": pair, "role": role, "canonical_dtype": "float32",
                    "lfe_sha256": hashlib.sha256(f"lfe:{unit}".encode()).hexdigest(),
                })
    write_csv(run_dir / "acquisition_scalar_hashes_v2.csv", acquisitions)
    directions = []
    for attribute in protocol.ATTRIBUTES:
        for pair in protocol.pair_ids(attribute):
            for token in range(protocol.LFE_TOKENS):
                directions.append({
                    "attribute": attribute, "formal_pair_id": pair, "token_index": token,
                    "training_pairs": 9, "held_pair_excluded": True,
                    "pre_normalization_direction_norm": 0.5, "unit_direction_norm": 1.0,
                    "direction_sha256": hashlib.sha256(f"direction:{attribute}:{pair}:{token}".encode()).hexdigest(),
                    "sham_attempt": 0, "sham_direction_norm": 1.0, "direction_sham_dot": 0.0,
                    "sham_direction_sha256": hashlib.sha256(f"sham:{attribute}:{pair}:{token}".encode()).hexdigest(),
                })
    write_csv(run_dir / "direction_scalar_diagnostics_v2.csv", directions)
    return run_dir, private


class MonolithicRun002Tests(unittest.TestCase):
    def test_runtime_plan_is_complete_single_transaction_family(self):
        rows = runtime._phase_rows()
        self.assertEqual(len(rows), 480)
        self.assertEqual({int(row["seed_index"]) for row in rows}, {1, 2, 3, 4})
        self.assertEqual(sum(int(row["scheduler_positions"]) for row in rows), 24000)
        with self.assertRaises(runtime.ControlledInterventionRuntimeError):
            runtime._phase_rows("engineering")

    def test_direction_and_sham_hashes_are_wired_on_real_synthetic_math(self):
        tensors, metadata = synthetic_lfe_panel()
        bundle = instrumentation.build_transient_interventions(tensors, metadata, expected_dim=8)
        self.assertEqual(len(bundle.diagnostics), 640)
        self.assertTrue(all(len(str(row["direction_sha256"])) == 64 for row in bundle.diagnostics))
        self.assertTrue(all(len(str(row["sham_direction_sha256"])) == 64 for row in bundle.diagnostics))

    def test_real_persisted_schema_fixture_passes_and_file_loss_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, private = make_monolithic_fixture(Path(temporary))
            result = verifier.verify_outputs(run_dir, private)
            self.assertEqual(result["scientific_trajectories"], 480)
            self.assertEqual(result["direction_scalar_hash_pairs"], 640)
            next(iter(private.iterdir())).unlink()
            with self.assertRaises(verifier.MonolithicRun002VerificationError):
                verifier.verify_outputs(run_dir, private)

    def test_hash_loss_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, private = make_monolithic_fixture(Path(temporary))
            with (run_dir / "direction_scalar_diagnostics_v2.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["direction_sha256"] = ""
            write_csv(run_dir / "direction_scalar_diagnostics_v2.csv", rows)
            with self.assertRaises(verifier.MonolithicRun002VerificationError):
                verifier.verify_outputs(run_dir, private)

    def test_no_weight_runner_has_no_active_gpu_authorization(self):
        self.assertFalse(runner.ACTIVE_AUTH.exists())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "dry.json"
            environment = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1"}
            subprocess.run(
                [sys.executable, str(runner.CODE_PATHS["runner"]), "--mode", "dry-run", "--output", str(output)],
                check=True, env=environment, capture_output=True, text=True,
            )
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(result["active_gpu_authorization_present"])
            self.assertFalse(result["torch_imported"])


if __name__ == "__main__":
    unittest.main()
