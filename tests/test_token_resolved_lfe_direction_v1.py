#!/usr/bin/env python3
from __future__ import annotations

import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
sys.path.insert(0, str(SRC))

import token_resolved_lfe_direction_protocol_v1 as protocol  # noqa: E402
import token_resolved_lfe_direction_instrumentation_v1 as instrumentation  # noqa: E402
import analyze_token_resolved_lfe_direction_v1 as analyzer  # noqa: E402
import verify_token_resolved_lfe_direction_v1 as verifier  # noqa: E402


def synthetic_panel(dim: int = 8):
    import torch

    generator = torch.Generator(device="cpu").manual_seed(731)
    tokens = {}
    metadata = {}
    for attribute, prefix, attribute_shift in (
        ("eyeglasses", "FEY", 0.18),
        ("facial_hair", "FFH", -0.11),
    ):
        for pair_index in range(1, 11):
            pair = f"{prefix}_{pair_index:02d}"
            base = torch.randn(protocol.LFE_TOKENS, dim, generator=generator)
            direction = torch.zeros(protocol.LFE_TOKENS, dim)
            direction[:, pair_index % dim] = attribute_shift
            for role in protocol.ROLES:
                unit = f"{pair}_{role}"
                tokens[unit] = base + (direction if role == "positive" else 0.0)
                metadata[unit] = {"attribute": attribute, "formal_pair_id": pair, "role": role}
    return tokens, metadata


def frozen_from_result(result: dict) -> list[dict[str, str]]:
    return [
        {
            "attribute": row["attribute"],
            "stage": "valid_face_emb_mean_token_l2_normalized",
            "formal_pair_id": row["formal_pair_id"],
            "margin": str(row["reconstructed_margin"]),
            "direction": row["direction"],
        }
        for row in result["pooled_replication"]
    ]


class TokenResolvedLfeDirectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = patch.dict(
            os.environ,
            {
                "CUDA_VISIBLE_DEVICES": "",
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1",
            },
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()

    def test_approved_design_and_implementation_authorization(self) -> None:
        self.assertEqual(
            protocol.validate_approved_design()["status"],
            "ALL_SEVEN_DESIGN_DECISIONS_APPROVED_PREREGISTRATION_FROZEN",
        )
        self.assertEqual(
            protocol.validate_implementation_authorization()["status"],
            protocol.IMPLEMENTATION_STATUS,
        )

    def test_no_weight_dry_run_and_independent_verification(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            run_dir = Path(temporary) / "run"
            with patch.object(protocol, "validate_dry_run_authorization", return_value={}):
                summary = protocol.no_weight_dry_run(run_dir)
            self.assertEqual(summary["scientific_reference_plan_rows"], 160)
            self.assertFalse(summary["reference_images_opened"])
            verified = verifier.verify_dry_run(run_dir)
            self.assertEqual(
                verified["status"],
                "PASS_INDEPENDENT_TOKEN_DIRECTION_NO_WEIGHT_DRY_RUN_VERIFICATION",
            )

    def test_dry_run_rejects_visible_cuda(self) -> None:
        with patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0"}):
            with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
                with self.assertRaises(protocol.DirectionProtocolError):
                    protocol.no_weight_dry_run(Path(temporary) / "run")

    def test_instrumentation_rejects_wrong_shape_and_nonfinite(self) -> None:
        import torch

        collector = instrumentation.TransientLfeTokenCollector(expected_dim=8)
        with self.assertRaises(instrumentation.TokenInstrumentationError):
            collector.add_engineering_direct("u", 1, torch.zeros(1, 31, 8))
        invalid = torch.zeros(1, 32, 8)
        invalid[0, 0, 0] = float("nan")
        with self.assertRaises(instrumentation.TokenInstrumentationError):
            collector.add_engineering_direct("u", 1, invalid)

    def test_engineering_repeat_and_hook_equivalence(self) -> None:
        import torch

        collector = instrumentation.TransientLfeTokenCollector(expected_dim=8)
        for index in range(8):
            value = torch.full((1, 32, 8), float(index + 1))
            collector.add_engineering_direct(f"u{index}", 1, value)
            collector.add_engineering_direct(f"u{index}", 2, value.clone())
            collector.add_engineering_hook(f"u{index}", value.clone())
        self.assertEqual(collector.validate_engineering()["engineering_units"], 8)

    def test_engineering_equivalence_fails_closed(self) -> None:
        import torch

        collector = instrumentation.TransientLfeTokenCollector(expected_dim=8)
        for index in range(8):
            value = torch.ones(1, 32, 8)
            collector.add_engineering_direct(f"u{index}", 1, value)
            collector.add_engineering_direct(f"u{index}", 2, value)
            hook = value.clone()
            if index == 0:
                hook[0, 0, 0] += 0.1
            collector.add_engineering_hook(f"u{index}", hook)
        with self.assertRaises(instrumentation.TokenInstrumentationError):
            collector.validate_engineering()

    def test_scientific_collector_requires_all_40_units_and_four_seed_labels(self) -> None:
        tokens, metadata = synthetic_panel()
        collector = instrumentation.TransientLfeTokenCollector(expected_dim=8)
        for unit, value in tokens.items():
            meta = metadata[unit]
            for seed_index, seed in enumerate(protocol.FORMAL_SEEDS, 1):
                collector.add_scientific(
                    {"formal_unit_id": unit, **meta, "seed_index": str(seed_index), "seed": seed},
                    value.unsqueeze(0),
                )
        finalized, final_meta = collector.finalize_scientific()
        self.assertEqual(len(finalized), 40)
        self.assertEqual(final_meta, metadata)
        self.assertFalse(collector.raw_tensor_serialization_supported)

    def test_complete_640_family_and_pooled_replication(self) -> None:
        tokens, metadata = synthetic_panel()
        discovery = analyzer.analyze_transient_tokens(tokens, metadata, expected_dim=8)
        result = analyzer.analyze_transient_tokens(
            tokens, metadata, frozen_from_result(discovery), expected_dim=8
        )
        self.assertEqual(len(result["token_margins"]), 640)
        self.assertEqual(len(result["token_finite_panel"]), 64)
        self.assertEqual(len(result["pair_token_signs"]), 20)
        self.assertEqual(len(result["pooled_replication"]), 20)
        self.assertTrue(all(row["within_tolerance"] for row in result["pooled_replication"]))

    def test_independent_recomputation_and_tamper_detection(self) -> None:
        tokens, metadata = synthetic_panel()
        initial = analyzer.analyze_transient_tokens(tokens, metadata, expected_dim=8)
        result = analyzer.analyze_transient_tokens(
            tokens, metadata, frozen_from_result(initial), expected_dim=8
        )
        verified = verifier.verify_transient_results(tokens, metadata, result, expected_dim=8)
        self.assertTrue(verified["all_640_margins_recomputed"])
        tampered = copy.deepcopy(result)
        tampered["token_margins"][0]["margin"] += 0.1
        with self.assertRaises(verifier.DirectionVerificationError):
            verifier.verify_transient_results(tokens, metadata, tampered, expected_dim=8)

    def test_preregistration_forbids_outcome_and_raw_vector_outputs(self) -> None:
        plan = protocol.read_json(
            REPO
            / "governance/mechanism_token_direction_design_v1"
            / "token_resolved_directional_analysis_preregistration_v1.json"
        )
        self.assertEqual(plan["planned_outputs"]["outcome_join_rows"], 0)
        self.assertEqual(plan["planned_outputs"]["association_coefficients"], 0)
        self.assertEqual(plan["planned_outputs"]["raw_vector_rows"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
