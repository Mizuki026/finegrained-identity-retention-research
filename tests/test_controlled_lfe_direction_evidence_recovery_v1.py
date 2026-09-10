#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import controlled_lfe_projection_exchange_instrumentation_v1 as instrumentation
from controlled_lfe_direction_evidence_recovery_v1 import (
    DirectionEvidenceRecoveryError,
    recover_scalar_hash_rows,
)
from tests.test_controlled_lfe_projection_exchange_v1 import synthetic_lfe_panel


class DirectionEvidenceRecoveryTests(unittest.TestCase):
    def test_exact_40_hash_gate_and_640_direction_hash_wiring(self):
        tensors, metadata = synthetic_lfe_panel()
        expected = {unit: instrumentation.tensor_scalar_sha256(value) for unit, value in tensors.items()}
        acquisitions, directions = recover_scalar_hash_rows(tensors, metadata, expected, expected_dim=8)
        self.assertEqual(len(acquisitions), 40)
        self.assertTrue(all(row["exact_match"] for row in acquisitions))
        self.assertEqual(len(directions), 640)
        self.assertTrue(all(len(str(row["direction_sha256"])) == 64 for row in directions))
        self.assertTrue(all(len(str(row["sham_direction_sha256"])) == 64 for row in directions))
        expected[next(iter(expected))] = "0" * 64
        with self.assertRaises(DirectionEvidenceRecoveryError):
            recover_scalar_hash_rows(tensors, metadata, expected, expected_dim=8)


if __name__ == "__main__":
    unittest.main()
