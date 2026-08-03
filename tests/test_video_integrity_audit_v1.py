#!/usr/bin/env python3
"""Small synthetic tests for frozen Stage 1 diagnostics; no real MP4 is opened."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import pilot_v1_1_video_integrity_audit_v1 as audit  # noqa: E402


class FrozenDiagnosticTests(unittest.TestCase):
    def test_black_frame_threshold(self) -> None:
        black = np.zeros((32, 48, 3), dtype=np.uint8)
        luma, _ = audit.luma_and_small(black)
        self.assertGreaterEqual(float((luma <= 16).mean()), 0.98)
        self.assertLessEqual(float(luma.mean()), 8.0)

        dark_but_not_black = np.full((32, 48, 3), 17, dtype=np.uint8)
        luma, _ = audit.luma_and_small(dark_but_not_black)
        self.assertFalse(float((luma <= 16).mean()) >= 0.98 and float(luma.mean()) <= 8.0)

    def test_duplicate_pair_thresholds(self) -> None:
        base = np.full((64, 64), 100.0, dtype=np.float32)
        nmae, close = audit.pair_metrics(base, base.copy())
        self.assertEqual(nmae, 0.0)
        self.assertEqual(close, 1.0)

        near = base.copy()
        near[0, 0] = 101.0
        nmae, close = audit.pair_metrics(base, near)
        self.assertLessEqual(nmae, 0.002)
        self.assertGreaterEqual(close, 0.995)

        changed = np.full((64, 64), 120.0, dtype=np.float32)
        nmae, close = audit.pair_metrics(base, changed)
        self.assertGreater(nmae, 0.002)
        self.assertLess(close, 0.995)

    def test_frozen_and_static_boundaries(self) -> None:
        self.assertEqual(audit.max_true_run([True] * 7 + [False]), 7)
        self.assertEqual(audit.max_true_run([False] + [True] * 8), 8)
        self.assertFalse(audit.max_true_run([True] * 7) >= 8)
        self.assertTrue(audit.max_true_run([True] * 8) >= 8)
        self.assertFalse(sum([True] * 43 + [False] * 5) >= 44)
        self.assertTrue(sum([True] * 44 + [False] * 4) >= 44)

    def test_status_precedence(self) -> None:
        self.assertEqual(audit.classify_status([]), "PASS")
        self.assertEqual(audit.classify_status(["BLACK_FRAME"]), "FAIL_VISUAL_INTEGRITY")
        self.assertEqual(audit.classify_status(["FPS_MISMATCH", "BLACK_FRAME"]), "FAIL_MEDIA_SPEC")
        self.assertEqual(audit.classify_status(["CORRUPT_FRAME", "FPS_MISMATCH"]), "FAIL_CONTAINER_OR_DECODE")
        self.assertEqual(audit.classify_status(["VIDEO_SHA256_MISMATCH"]), "FAIL_FILE_INTEGRITY")
        self.assertEqual(audit.classify_status(["PATH_MAPPING_MISMATCH"]), "FAIL_MAPPING")

    def test_synthetic_contact_sheet(self) -> None:
        selected: dict[str, dict[int, np.ndarray]] = {}
        for sample_number in range(1, 13):
            sample_id = f"synthetic_{sample_number:02d}"
            selected[sample_id] = {
                index: np.full((48, 72, 3), (sample_number * 17 + index) % 255, dtype=np.uint8)
                for index in audit.CONTACT_INDICES
            }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "contact.png"
            audit.create_contact_sheet(output, selected)
            self.assertTrue(output.is_file())
            with Image.open(output) as image:
                self.assertEqual(image.size, (240 * 5, (160 + 30) * 12))

    def test_schema_loads(self) -> None:
        schema = audit.read_json(audit.SCHEMA_PATH)
        self.assertEqual(schema["schema_version"], 1)
        self.assertEqual(schema["audit_id"], audit.AUDIT_ID)
        self.assertEqual(len(schema["video_csv_columns"]), 48)
        self.assertEqual(len(schema["frame_csv_columns"]), 22)


if __name__ == "__main__":
    unittest.main(verbosity=2)
