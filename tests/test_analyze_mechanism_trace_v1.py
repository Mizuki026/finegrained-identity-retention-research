#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
sys.path.insert(0, str(SRC))

import analyze_mechanism_trace_v1 as analysis  # noqa: E402


def scientific_plan() -> list[dict[str, str]]:
    rows = []
    for attribute, prefix in (("eyeglasses", "FEY"), ("facial_hair", "FFH")):
        for pair_index in range(1, 11):
            pair = f"{prefix}_{pair_index:02d}"
            for role in ("positive", "control"):
                unit = f"{pair}_{role}"
                for seed_index in range(1, 5):
                    rows.append({
                        "trace_task_id": f"S__{unit}__s{seed_index}__baseline__r1",
                        "formal_unit_id": unit,
                        "formal_pair_id": pair,
                        "attribute": attribute,
                        "role": role,
                        "seed_index": str(seed_index),
                        "seed": str(1000 + seed_index),
                    })
    return rows


class MechanismTraceAnalysisTests(unittest.TestCase):
    def test_fixed_3x3_four_seed_matched_pair_aggregation(self) -> None:
        plan = scientific_plan()

        def injection_rows(_path):
            for task in plan:
                value = 2.0 if task["role"] == "positive" else 1.0
                for step in range(50):
                    for site in range(21):
                        for branch in ("unconditional", "text"):
                            yield {
                                "trace_task_id": task["trace_task_id"],
                                "cfg_branch": branch,
                                "site_index": str(site),
                                "step_index": str(step),
                                "relative_residual_rms": str(value),
                            }

        with patch.object(analysis, "build_plan", return_value=({}, plan)), patch.object(
            analysis, "read_csv_rows", side_effect=injection_rows
        ):
            task_rows, pair_rows, panel_rows = analysis.aggregate_injection(Path("unused"))
        self.assertEqual(len(task_rows), 2880)
        self.assertEqual(len(pair_rows), 360)
        self.assertEqual(len(panel_rows), 36)
        self.assertTrue(all(row["positive_minus_control"] == 1.0 for row in pair_rows))
        self.assertTrue(all(row["mean"] == 1.0 for row in panel_rows))
        self.assertTrue(all(row["positive_count"] == 10 for row in panel_rows))

    def test_representation_primary_and_secondary_labels(self) -> None:
        stages = [analysis.PRIMARY_STAGE] + [f"secondary_{index}" for index in range(8)]

        def margin_rows(_path):
            for attribute, prefix in (("eyeglasses", "FEY"), ("facial_hair", "FFH")):
                for stage in stages:
                    for pair_index in range(1, 11):
                        yield {
                            "attribute": attribute,
                            "stage": stage,
                            "formal_pair_id": f"{prefix}_{pair_index:02d}",
                            "margin": "1.0",
                            "direction": "correct",
                        }

        with patch.object(analysis, "read_csv_rows", side_effect=margin_rows):
            rows = analysis.aggregate_representations(Path("unused"))
        self.assertEqual(len(rows), 18)
        self.assertEqual(sum(row["readout_role"] == "primary" for row in rows), 2)
        self.assertTrue(all(row["correct_count"] == 10 for row in rows))


if __name__ == "__main__":
    unittest.main(verbosity=2)
