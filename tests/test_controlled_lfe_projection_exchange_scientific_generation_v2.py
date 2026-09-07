#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import verify_controlled_lfe_projection_exchange_scientific_generation_v1 as verifier_v1
import verify_controlled_lfe_projection_exchange_scientific_generation_v2 as verifier_v2
from tests.test_controlled_lfe_projection_exchange_scientific_generation_v1 import (
    make_shard,
    write_csv,
)


class ScientificGenerationVerifierV2RegressionTests(unittest.TestCase):
    def test_runtime_persisted_schema_fails_v1_and_passes_v2(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, private = make_shard(Path(temporary), 1)
            status_path = run_dir / "trajectory_status_v1.csv"
            with status_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            for row in rows:
                row.pop("trajectory_kind")
                row.pop("formal_binding_status")
            write_csv(status_path, rows)
            with self.assertRaises(KeyError):
                verifier_v1.verify_outputs(run_dir, private, 1)
            result = verifier_v2.verify_outputs(run_dir, private, 1)
            self.assertEqual(result["verification_schema_version"], 2)
            self.assertEqual(result["persisted_plan_fields_verified"], list(verifier_v2.PERSISTED_PLAN_FIELDS))
            self.assertEqual(result["private_final_latent_files"], 120)
            self.assertEqual(result["cross_condition_input_invariants_verified"], 40)
            self.assertEqual(result["acquisition_scalar_hashes"], 40)
            self.assertEqual(result["direction_scalar_hash_pairs"], 640)


if __name__ == "__main__":
    unittest.main()
