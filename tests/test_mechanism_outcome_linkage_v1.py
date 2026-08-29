#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
PLAN = REPO / "governance/mechanism_outcome_linkage_implementation_v1/approved_analysis_plan_v1.json"
sys.path.insert(0, str(SRC))

import analyze_mechanism_outcome_linkage_v1 as analyzer  # noqa: E402
import verify_mechanism_outcome_linkage_v1 as verifier  # noqa: E402


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def binding(path: Path, header: list[str], key_columns: list[str]) -> dict:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": analyzer.sha256(path),
        "header": header,
        "key_columns": key_columns,
        "expected_keys": ["|".join(row[column] for column in key_columns) for row in rows],
    }


def file_binding(path: Path) -> dict:
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": analyzer.sha256(path),
    }


def synthetic_package(root: Path) -> tuple[Path, Path]:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan_path = root / "plan.json"
    write_json(plan_path, plan)
    eye_path = root / "eye.csv"
    hair_path = root / "hair.csv"
    rep_path = root / "representations.csv"
    injection_path = root / "injections.csv"

    eye_header = ["attribute", "formal_pair_id", "seed_index", "human_positive_minus_control"]
    eye_rows = []
    for pair_index in range(1, 11):
        for seed_index in range(1, 5):
            eye_rows.append({
                "attribute": "eyeglasses",
                "formal_pair_id": f"FEY_{pair_index:02d}",
                "seed_index": seed_index,
                "human_positive_minus_control": pair_index + (seed_index - 2.5) / 10.0,
            })
    write_csv(eye_path, eye_header, eye_rows)

    hair_header = ["attribute", "formal_pair_id", "primary_positive_minus_control"]
    hair_rows = [{
        "attribute": "facial_hair",
        "formal_pair_id": f"FFH_{pair_index:02d}",
        "primary_positive_minus_control": 11 - pair_index,
    } for pair_index in range(1, 11)]
    write_csv(hair_path, hair_header, hair_rows)

    rep_header = ["attribute", "stage", "formal_pair_id", "margin"]
    rep_rows = []
    stages = (analyzer.PRIMARY_STAGE,) + analyzer.SECONDARY_STAGES
    for attribute, prefix in (("eyeglasses", "FEY"), ("facial_hair", "FFH")):
        for stage_index, stage in enumerate(stages):
            for pair_index in range(1, 11):
                rep_rows.append({
                    "attribute": attribute,
                    "stage": stage,
                    "formal_pair_id": f"{prefix}_{pair_index:02d}",
                    "margin": pair_index + stage_index / 100.0,
                })
    write_csv(rep_path, rep_header, rep_rows)

    injection_header = [
        "attribute", "formal_pair_id", "cfg_branch", "block_group",
        "denoising_group", "positive_minus_control",
    ]
    injection_rows = []
    for attribute, prefix in (("eyeglasses", "FEY"), ("facial_hair", "FFH")):
        for pair_index in range(1, 11):
            for branch_index, branch in enumerate(analyzer.BRANCHES):
                for block_index, block in enumerate(analyzer.GROUPS):
                    for denoise_index, denoise in enumerate(analyzer.GROUPS):
                        injection_rows.append({
                            "attribute": attribute,
                            "formal_pair_id": f"{prefix}_{pair_index:02d}",
                            "cfg_branch": branch,
                            "block_group": block,
                            "denoising_group": denoise,
                            "positive_minus_control": pair_index + branch_index / 10.0 + block_index / 100.0 + denoise_index / 1000.0,
                        })
    write_csv(injection_path, injection_header, injection_rows)

    output_dir = root / "external_output"
    authorization = {
        "schema_version": 1,
        "status": analyzer.EXECUTION_STATUS,
        "authority": {
            "formal_input_audit": True,
            "real_input_read": True,
            "input_join": True,
            "association_computation": True,
            "independent_verification": True,
            "model_loading": False,
            "gpu_execution": False,
            "network": False,
        },
        "analysis_plan": file_binding(plan_path),
        "code": {
            "analyzer": file_binding(Path(analyzer.__file__)),
            "verifier": file_binding(Path(verifier.__file__)),
        },
        "sources": {
            "eyeglasses_outcome": binding(eye_path, eye_header, ["formal_pair_id", "seed_index"]),
            "facial_hair_outcome": binding(hair_path, hair_header, ["attribute", "formal_pair_id"]),
            "representation_margins": binding(rep_path, rep_header, ["attribute", "stage", "formal_pair_id"]),
            "injection_pair_grid": binding(
                injection_path, injection_header,
                ["attribute", "formal_pair_id", "cfg_branch", "block_group", "denoising_group"],
            ),
        },
        "output_dir": str(output_dir.resolve()),
    }
    authorization_path = root / "authorization.json"
    write_json(authorization_path, authorization)
    return authorization_path, output_dir


class MechanismOutcomeLinkageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cpu_environment = patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": ""})
        self.cpu_environment.start()

    def tearDown(self) -> None:
        self.cpu_environment.stop()

    def test_average_ranks_use_average_for_ties(self) -> None:
        self.assertEqual(analyzer.average_ranks([10.0, 20.0, 20.0, 40.0]), [1.0, 2.5, 2.5, 4.0])

    def test_spearman_perfect_and_reverse(self) -> None:
        self.assertAlmostEqual(analyzer.spearman([1, 2, 3], [4, 5, 6]), 1.0)
        self.assertAlmostEqual(analyzer.spearman([1, 2, 3], [6, 5, 4]), -1.0)

    def test_spearman_zero_variance_is_undefined(self) -> None:
        self.assertIsNone(analyzer.spearman([1, 1, 1], [1, 2, 3]))

    def test_approved_plan_has_complete_fixed_families(self) -> None:
        pairs = analyzer.planned_pairs(json.loads(PLAN.read_text(encoding="utf-8")))
        self.assertEqual({attribute: len(value) for attribute, value in pairs.items()}, {"eyeglasses": 10, "facial_hair": 10})

    def test_no_weight_dry_run_creates_no_join_or_association(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            summary_path = Path(temporary) / "dry_run.json"
            summary = analyzer.no_weight_dry_run(PLAN, summary_path)
            self.assertFalse(summary["input_files_opened"])
            self.assertEqual(summary["joined_rows_created"], 0)
            self.assertFalse(summary["association_computed"])
            verified = verifier.verify_dry_run(summary_path)
            self.assertEqual(verified["status"], "PASS_INDEPENDENT_NO_WEIGHT_DRY_RUN_VERIFICATION")

    def test_dry_run_requires_explicitly_hidden_cuda(self) -> None:
        with patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0"}):
            with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
                with self.assertRaises(analyzer.LinkageError):
                    analyzer.no_weight_dry_run(PLAN, Path(temporary) / "dry_run.json")

    def test_formal_mode_rejects_unapproved_authorization_before_input_access(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            authorization = root / "authorization.json"
            write_json(authorization, {"status": "IMPLEMENTATION_ONLY"})
            with self.assertRaises(analyzer.LinkageError):
                analyzer.run_authorized(authorization, PLAN, root / "output")
            self.assertFalse((root / "output").exists())

    def test_synthetic_complete_family_execution_and_independent_verification(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            authorization, output_dir = synthetic_package(root)
            summary = analyzer.run_authorized(authorization, root / "plan.json", output_dir)
            self.assertEqual(summary["primary_coefficients"], 2)
            self.assertEqual(summary["secondary_representation_coefficients"], 16)
            self.assertEqual(summary["secondary_injection_coefficients"], 36)
            verified = verifier.verify_result(authorization, root / "plan.json", output_dir)
            self.assertEqual(verified["status"], "PASS_INDEPENDENT_FIXED_PANEL_LINKAGE_VERIFICATION")

    def test_independent_verifier_detects_joined_value_tamper(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            authorization, output_dir = synthetic_package(root)
            analyzer.run_authorized(authorization, root / "plan.json", output_dir)
            path = output_dir / "primary_joined_pairs_v1.csv"
            lines = path.read_text(encoding="utf-8").splitlines()
            fields = lines[1].split(",")
            fields[-1] = "999.0"
            lines[1] = ",".join(fields)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(verifier.VerificationError):
                verifier.verify_result(authorization, root / "plan.json", output_dir)


if __name__ == "__main__":
    unittest.main(verbosity=2)
