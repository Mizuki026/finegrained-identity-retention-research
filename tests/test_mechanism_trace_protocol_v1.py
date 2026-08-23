#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
sys.path.insert(0, str(SRC))

import mechanism_trace_protocol_v1 as protocol  # noqa: E402


class MechanismTraceProtocolTests(unittest.TestCase):
    def test_frozen_plan_counts_and_crossing(self) -> None:
        engineering_summary, engineering = protocol.build_plan("engineering")
        scientific_summary, scientific = protocol.build_plan("scientific")
        all_summary, all_rows = protocol.build_plan("all")
        self.assertEqual(len(engineering), 24)
        self.assertEqual(len(scientific), 160)
        self.assertEqual(len(all_rows), 184)
        self.assertEqual(engineering_summary["transformer_steps"], 1200)
        self.assertEqual(scientific_summary["transformer_steps"], 8000)
        self.assertEqual(all_summary["transformer_steps"], 9200)
        self.assertEqual(len({row["formal_unit_id"] for row in scientific}), 40)
        seeds = Counter(int(row["seed"]) for row in scientific)
        self.assertEqual(seeds, Counter({seed: 40 for seed in protocol.FORMAL_SEEDS}))

    def test_engineering_plan_is_balanced_and_outcome_blind(self) -> None:
        rows = protocol.engineering_plan()
        self.assertEqual(len({row["formal_unit_id"] for row in rows}), 8)
        per_unit = Counter(row["formal_unit_id"] for row in rows)
        self.assertEqual(set(per_unit.values()), {3})
        conditions = Counter(row["condition"] for row in rows)
        self.assertEqual(conditions, Counter({"baseline": 16, "zero_local_residual": 8}))
        attribute_role_units = {
            (row["attribute"], row["role"], row["formal_unit_id"])
            for row in rows
        }
        self.assertEqual(
            Counter((attribute, role) for attribute, role, _ in attribute_role_units),
            Counter({
                ("eyeglasses", "positive"): 2,
                ("eyeglasses", "control"): 2,
                ("facial_hair", "positive"): 2,
                ("facial_hair", "control"): 2,
            }),
        )

    def test_dry_run_and_independent_verifier_without_ml_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "dry"
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(SRC)
            run = subprocess.run(
                [
                    sys.executable,
                    str(SRC / "run_mechanism_trace_v1.py"),
                    "--mode", "dry-run",
                    "--phase", "all",
                    "--output-dir", str(output),
                ],
                cwd=REPO,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('"task_count": 184', run.stdout)
            verify = subprocess.run(
                [
                    sys.executable,
                    str(SRC / "verify_mechanism_trace_v1.py"),
                    "--mode", "dry-run",
                    "--phase", "all",
                    "--run-dir", str(output),
                ],
                cwd=REPO,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)
            self.assertIn("PASS_INDEPENDENT_DRY_RUN_VERIFICATION", verify.stdout)

    def test_execution_blocks_before_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(SRC)
            run = subprocess.run(
                [
                    sys.executable,
                    str(SRC / "run_mechanism_trace_v1.py"),
                    "--mode", "execute-engineering",
                    "--output-dir", str(Path(directory) / "blocked"),
                ],
                cwd=REPO,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(run.returncode, 2)
            self.assertIn("requires --authorization-file", run.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
