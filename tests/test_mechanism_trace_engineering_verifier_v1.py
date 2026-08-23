#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
sys.path.insert(0, str(SRC))

from verify_mechanism_trace_engineering_controls_v1 import (  # noqa: E402
    NUMERIC_SUMMARY_FIELDS,
    ROUTE_FIELDS,
    verify_engineering_controls,
)


class EngineeringControlVerifierTests(unittest.TestCase):
    def test_fixed_engineering_repeat_and_zero_control(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            injection_path = root / "injection.csv"
            route_path = root / "routes.csv"
            injection_fields = (
                "trace_task_id", "formal_unit_id", "condition", "repetition",
                "step_index", "scheduler_timestep", "site_index", "cfg_branch",
                "local_face_scale",
            ) + NUMERIC_SUMMARY_FIELDS
            with injection_path.open("x", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=injection_fields, lineterminator="\n")
                writer.writeheader()
                for unit_index in range(8):
                    unit = f"unit_{unit_index:02d}"
                    for condition, repetition in (
                        ("baseline", "1"), ("baseline", "2"),
                        ("zero_local_residual", "1"),
                    ):
                        task_id = f"E__{unit}__s1__{condition}__r{repetition}"
                        for step in range(50):
                            for site in range(21):
                                for branch in ("unconditional", "text"):
                                    row = {
                                        "trace_task_id": task_id,
                                        "formal_unit_id": unit,
                                        "condition": condition,
                                        "repetition": repetition,
                                        "step_index": step,
                                        "scheduler_timestep": 999 - step,
                                        "site_index": site,
                                        "cfg_branch": branch,
                                        "local_face_scale": 0.0 if condition.startswith("zero") else 1.0,
                                    }
                                    row.update({field: 2.0 for field in NUMERIC_SUMMARY_FIELDS})
                                    row["rms_h"] = 1.0
                                    row["rms_post"] = 1.0 if condition.startswith("zero") else 3.0
                                    writer.writerow(row)

            route_fields = ("trace_task_id", "formal_unit_id", "condition") + ROUTE_FIELDS
            with route_path.open("x", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=route_fields, lineterminator="\n")
                writer.writeheader()
                for unit_index in range(8):
                    unit = f"unit_{unit_index:02d}"
                    for condition, repetition in (
                        ("baseline", "1"), ("baseline", "2"),
                        ("zero_local_residual", "1"),
                    ):
                        row = {
                            "trace_task_id": f"E__{unit}__s1__{condition}__r{repetition}",
                            "formal_unit_id": unit,
                            "condition": condition,
                        }
                        row.update({field: 1.0 for field in ROUTE_FIELDS})
                        writer.writerow(row)

            status_rows = [
                {"reference_vectors_verified_in_memory": "True"}
                for _ in range(24)
            ]
            result = verify_engineering_controls(injection_path, route_path, status_rows)
            self.assertEqual(result["status"], "PASS_ENGINEERING_REPEAT_AND_ZERO_ROUTE_CONTROLS")
            self.assertEqual(result["baseline_repeat_keys"], 8 * 50 * 21 * 2)
            self.assertEqual(result["zero_control_rows"], 8 * 50 * 21 * 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
