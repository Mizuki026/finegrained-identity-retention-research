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
sys.path.insert(0, str(SRC))

import audit_mechanism_outcome_linkage_inputs_v1 as auditor  # noqa: E402
import verify_mechanism_outcome_linkage_input_audit_v1 as verifier  # noqa: E402


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def source_rows(source_name: str) -> tuple[list[str], list[dict]]:
    if source_name == "eyeglasses_outcome":
        header = ["attribute", "formal_pair_id", "seed_index", "human_positive_minus_control"]
        rows = [{
            "attribute": "eyeglasses", "formal_pair_id": f"FEY_{pair:02d}",
            "seed_index": seed, "human_positive_minus_control": pair / 10.0,
        } for pair in range(1, 11) for seed in range(1, 5)]
        return header, rows
    if source_name == "facial_hair_outcome":
        header = ["attribute", "formal_pair_id", "primary_positive_minus_control"]
        rows = [{
            "attribute": attribute,
            "formal_pair_id": f"{'FEY' if attribute == 'eyeglasses' else 'FFH'}_{pair:02d}",
            "primary_positive_minus_control": (
                "" if attribute == "eyeglasses" and pair != 9 else pair / 10.0
            ),
        } for attribute in auditor.ATTRIBUTES for pair in range(1, 11)]
        return header, rows
    if source_name == "representation_margins":
        header = ["attribute", "stage", "formal_pair_id", "margin", "direction"]
        rows = [{
            "attribute": attribute, "stage": stage,
            "formal_pair_id": f"{'FEY' if attribute == 'eyeglasses' else 'FFH'}_{pair:02d}",
            "margin": pair / 100.0, "direction": "correct",
        } for attribute in auditor.ATTRIBUTES
          for stage in (auditor.PRIMARY_STAGE,) + auditor.SECONDARY_STAGES
          for pair in range(1, 11)]
        return header, rows
    header = [
        "attribute", "formal_pair_id", "cfg_branch", "block_group",
        "denoising_group", "positive_minus_control",
    ]
    rows = [{
        "attribute": attribute,
        "formal_pair_id": f"{'FEY' if attribute == 'eyeglasses' else 'FFH'}_{pair:02d}",
        "cfg_branch": branch, "block_group": block, "denoising_group": denoise,
        "positive_minus_control": pair / 1000.0,
    } for attribute in auditor.ATTRIBUTES for pair in range(1, 11)
      for branch in auditor.BRANCHES for block in auditor.GROUPS for denoise in auditor.GROUPS]
    return header, rows


def authorization(root: Path, selected_source: str, source_path: Path) -> Path:
    value = {
        "status": auditor.AUTH_STATUS,
        "not_authorized": {
            "pair_outcome_construction": True,
            "outcome_trace_join": True,
            "spearman_or_other_association": True,
            "cross_source_value_comparison": True,
            "model_loading": True,
            "gpu_execution": True,
            "network_access": True,
        },
        "sources": {
            name: {
                "path": str(source_path),
                "bytes": source_path.stat().st_size,
                "sha256": auditor.sha256(source_path),
            } for name in auditor.SOURCE_NAMES
        },
        "external_runtime": str(root / "runtime"),
    }
    path = root / f"authorization_{selected_source}.json"
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


class FormalInputAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = patch.dict(os.environ, {
            "CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        })
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()

    def test_all_four_sources_pass_independently(self) -> None:
        for source_name in auditor.SOURCE_NAMES:
            with self.subTest(source_name=source_name), tempfile.TemporaryDirectory(dir="/tmp") as temporary:
                root = Path(temporary)
                source_path = root / f"{source_name}.csv"
                header, rows = source_rows(source_name)
                write_csv(source_path, header, rows)
                auth = authorization(root, source_name, source_path)
                output = root / "runtime" / source_name
                summary = auditor.audit(auth, source_name, output)
                self.assertFalse(summary["outcome_trace_joined"])
                self.assertFalse(summary["association_computed"])
                result = verifier.verify(auth, source_name, output)
                self.assertEqual(
                    result["status"],
                    "PASS_INDEPENDENT_FORMAL_SINGLE_SOURCE_INPUT_AUDIT_VERIFICATION",
                )

    def test_duplicate_key_stops_before_output(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            source_path = root / "eyeglasses.csv"
            header, rows = source_rows("eyeglasses_outcome")
            rows[-1] = dict(rows[0])
            write_csv(source_path, header, rows)
            auth = authorization(root, "eyeglasses_outcome", source_path)
            output = root / "runtime" / "eyeglasses_outcome"
            with self.assertRaises(auditor.AuditError):
                auditor.audit(auth, "eyeglasses_outcome", output)
            self.assertFalse(output.exists())

    def test_nonfinite_value_stops_before_output(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            source_path = root / "representations.csv"
            header, rows = source_rows("representation_margins")
            rows[0]["margin"] = "nan"
            write_csv(source_path, header, rows)
            auth = authorization(root, "representation_margins", source_path)
            output = root / "runtime" / "representation_margins"
            with self.assertRaises(auditor.AuditError):
                auditor.audit(auth, "representation_margins", output)
            self.assertFalse(output.exists())

    def test_authorization_must_keep_join_and_association_blocked(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            source_path = root / "injection.csv"
            header, rows = source_rows("injection_pair_grid")
            write_csv(source_path, header, rows)
            auth = authorization(root, "injection_pair_grid", source_path)
            value = json.loads(auth.read_text(encoding="utf-8"))
            value["not_authorized"]["outcome_trace_join"] = False
            auth.write_text(json.dumps(value) + "\n", encoding="utf-8")
            with self.assertRaises(auditor.AuditError):
                auditor.audit(auth, "injection_pair_grid", root / "runtime" / "injection_pair_grid")

    def test_missing_target_facial_hair_value_stops_before_output(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            source_path = root / "hair.csv"
            header, rows = source_rows("facial_hair_outcome")
            next(row for row in rows if row["attribute"] == "facial_hair")[
                "primary_positive_minus_control"
            ] = ""
            write_csv(source_path, header, rows)
            auth = authorization(root, "facial_hair_outcome", source_path)
            output = root / "runtime" / "facial_hair_outcome"
            with self.assertRaises(auditor.AuditError):
                auditor.audit(auth, "facial_hair_outcome", output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
