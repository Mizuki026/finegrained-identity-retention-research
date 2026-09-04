#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import analyze_token_resolved_lfe_direction_v2 as analyzer
import run_token_resolved_lfe_direction_v2 as runner
import token_resolved_lfe_direction_protocol_v2 as protocol
import verify_token_resolved_lfe_direction_v2 as verifier


def synthetic_panel(dim: int = 8):
    import torch

    generator = torch.Generator().manual_seed(20260904)
    tensors, metadata = {}, {}
    for attribute, prefix in (("eyeglasses", "FEY"), ("facial_hair", "FFH")):
        for index in range(1, 11):
            pair = f"{prefix}_{index:02d}"
            for role in protocol.ROLES:
                unit = f"{pair}_{role}"
                base = torch.randn(1, protocol.LFE_TOKENS, dim, generator=generator)
                tensors[unit] = {
                    "1": {"D1": base.clone(), "D2": base.clone()},
                    "2": {"D1": base.clone()},
                    "3": {"D1": base.clone()},
                    "4": {"D1": base.clone()},
                }
                metadata[unit] = {"formal_pair_id": pair, "attribute": attribute, "role": role}
    historical = protocol.read_csv(protocol.RUN003)
    return tensors, metadata, historical


def synthetic_source_rows():
    rows = []
    for attribute, prefix in (("eyeglasses", "FEY"), ("facial_hair", "FFH")):
        for index in range(1, 11):
            pair = f"{prefix}_{index:02d}"
            for role in protocol.ROLES:
                unit = f"{pair}_{role}"
                for seed_index, seed in protocol.SEED_MAP.items():
                    rows.append({
                        "task_id": f"TASK__{unit}__S{seed_index}",
                        "formal_unit_id": unit,
                        "formal_pair_id": pair,
                        "attribute": attribute,
                        "role": role,
                        "seed_index": seed_index,
                        "seed": seed,
                    })
    return rows


class TokenDirectionV2Tests(unittest.TestCase):
    def test_design_binding_and_complete_plan(self):
        self.assertIn("FROZEN", protocol.validate_design()["status"])
        plan = protocol.execution_plan(synthetic_source_rows())
        self.assertEqual(len(plan), 160)
        self.assertEqual(sum(int(row["fresh_preprocessing_calls"]) for row in plan), 160)
        self.assertEqual(sum(int(row["direct_lfe_calls"]) for row in plan), 200)

    def test_no_top_level_ml_imports(self):
        runner.assert_no_top_level_ml_imports()

    def test_runtime_has_no_tensor_serializer_or_outcome_reference(self):
        text = (REPO / "src/token_resolved_lfe_direction_runtime_v2.py").read_text(encoding="utf-8")
        for forbidden in ("torch.save", "numpy.save", "pickle.dump", "outcome.csv", "spearman"):
            self.assertNotIn(forbidden, text)

    def test_runtime_imports_models_only_inside_execute(self):
        path = REPO / "src/token_resolved_lfe_direction_runtime_v2.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        top = tree.body
        for node in top:
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            self.assertFalse(any(name.split(".")[0] in {"torch", "models"} for name in names))

    def test_complete_analyzer_and_independent_recomputation(self):
        tensors, metadata, historical = synthetic_panel()
        result = analyzer.analyze_transient(tensors, metadata, historical, expected_dim=8)
        self.assertEqual(
            [len(result[key]) for key in ("direct_controls", "four_label_controls", "current_pooled", "historical", "token_margins", "token_panel", "pair_signs")],
            [40, 120, 20, 20, 640, 64, 20],
        )
        self.assertTrue(all(row["bit_exact"] for row in result["direct_controls"] + result["four_label_controls"]))
        proof = verifier.verify_transient(tensors, metadata, historical, result, expected_dim=8)
        self.assertEqual(proof["status"], "PASS_INDEPENDENT_IN_MEMORY_TOKEN_DIRECTION_V2_RECOMPUTATION")

    def test_historical_difference_is_descriptive_not_a_gate(self):
        tensors, metadata, historical = synthetic_panel()
        result = analyzer.analyze_transient(tensors, metadata, historical, expected_dim=8)
        self.assertEqual(len(result["historical"]), 20)
        self.assertTrue(any(not row["within_tolerance"] for row in result["historical"]))

    def test_validity_control_failure_aborts_before_scientific_family(self):
        tensors, metadata, historical = synthetic_panel()
        unit = sorted(tensors)[0]
        tensors[unit]["2"]["D1"] = tensors[unit]["2"]["D1"].clone()
        tensors[unit]["2"]["D1"][0, 0, 0] += 1.0
        with self.assertRaises(analyzer.DirectionV2AnalysisError):
            analyzer.analyze_transient(tensors, metadata, historical, expected_dim=8)

    def test_independent_verifier_detects_analyzer_tamper(self):
        tensors, metadata, historical = synthetic_panel()
        result = analyzer.analyze_transient(tensors, metadata, historical, expected_dim=8)
        result["token_margins"][0]["margin"] += 0.5
        with self.assertRaises(verifier.DirectionV2VerificationError):
            verifier.verify_transient(tensors, metadata, historical, result, expected_dim=8)

    def test_persisted_verifier_checks_complete_family(self):
        tensors, metadata, historical = synthetic_panel()
        result = analyzer.analyze_transient(tensors, metadata, historical, expected_dim=8)
        memory = verifier.verify_transient(tensors, metadata, historical, result, expected_dim=8)
        with tempfile.TemporaryDirectory() as raw:
            run = Path(raw)
            analyzer.write_outputs(run, result)
            statuses = []
            for unit in sorted(metadata):
                for seed_index, seed in protocol.SEED_MAP.items():
                    statuses.append({
                        "v2_task_id": f"TDV2__{unit}__S{seed_index}",
                        "formal_unit_id": unit,
                        **metadata[unit],
                        "seed_index": seed_index,
                        "seed": seed,
                        "preprocessing_calls": 1,
                        "direct_lfe_calls": 2 if seed_index == "1" else 1,
                        "status": "COMPLETE_TRANSIENT_ONLY",
                    })
            protocol.atomic_csv(run / "token_direction_v2_execution_status.csv", tuple(statuses[0]), statuses)
            protocol.atomic_json(run / "token_direction_v2_in_memory_verification.json", memory)
            protocol.atomic_json(run / "token_direction_v2_execution_summary.json", {
                "raw_identity_or_token_tensor_files": 0,
                "outcomes_opened_or_joined": False,
            })
            proof = verifier.verify_persisted(run)
            self.assertEqual(proof["margin_rows"], 640)


if __name__ == "__main__":
    unittest.main()
