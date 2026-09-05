#!/usr/bin/env python3
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import analyze_controlled_lfe_projection_exchange_v1 as analyzer
import controlled_lfe_projection_exchange_instrumentation_v1 as instrumentation
import controlled_lfe_projection_exchange_protocol_v1 as protocol
import controlled_lfe_projection_exchange_runtime_v1 as runtime
import run_controlled_lfe_projection_exchange_v1 as runner
import verify_controlled_lfe_projection_exchange_v1 as verifier


def synthetic_lfe_panel(dim: int = 8):
    import torch

    generator = torch.Generator(device="cpu").manual_seed(20260904)
    tensors, metadata = {}, {}
    attribute_axes = {
        "eyeglasses": torch.tensor([1.0] + [0.0] * (dim - 1)),
        "facial_hair": torch.tensor([0.0, 1.0] + [0.0] * (dim - 2)),
    }
    for attribute in protocol.ATTRIBUTES:
        for pair in protocol.pair_ids(attribute):
            pair_index = int(pair[-2:])
            for role in protocol.ROLES:
                unit = protocol.unit_id(attribute, pair, role)
                base = torch.randn(1, protocol.LFE_TOKENS, dim, generator=generator) * 0.1
                role_sign = 1.0 if role == "positive" else -1.0
                base += role_sign * (1.0 + pair_index * 0.01) * attribute_axes[attribute]
                tensors[unit] = base
                metadata[unit] = {"attribute": attribute, "formal_pair_id": pair, "role": role}
    return tensors, metadata


def synthetic_outcomes():
    rows = []
    for attribute in protocol.ATTRIBUTES:
        for pair in protocol.pair_ids(attribute):
            for role in protocol.ROLES:
                for condition in protocol.CONDITIONS:
                    for seed in protocol.SEEDS:
                        for frame in protocol.FRAME_INDICES:
                            present = (
                                (condition == "target_projection_exchange" and role == "control")
                                or (condition in {"baseline", "orthogonal_sham"} and role == "positive")
                            )
                            label = ("present" if present else "absent") if attribute == "eyeglasses" else ("1" if present else "0")
                            rows.append({
                                "attribute": attribute, "formal_pair_id": pair, "role": role,
                                "condition": condition, "seed": seed, "frame_index": frame,
                                "final_label": label, "observability_reason": "",
                            })
    return rows


class ControlledInterventionTests(unittest.TestCase):
    def test_01_frozen_design_and_current_implementation_authority(self):
        freeze, prereg = protocol.validate_design()
        self.assertIn("FROZEN", freeze["status"])
        self.assertEqual(prereg["frozen_panel"]["scientific_trajectories"], 480)
        self.assertEqual(protocol.validate_implementation_authority()["status"], protocol.IMPLEMENTATION_STATUS)

    def test_02_complete_deterministic_no_weight_plan(self):
        first = protocol.execution_plan()
        second = protocol.execution_plan()
        self.assertEqual(first, second)
        self.assertEqual(protocol.plan_summary(first), {
            "plan_rows": 480, "source_tasks": 160, "formal_units": 40,
            "formal_pairs": 20, "conditions": 3, "scientific_trajectories": 480,
            "scientific_scheduler_steps": 24000, "held_pair_out_directions": 640,
            "fresh_preprocessing_calls": 40, "direct_lfe_acquisitions": 40,
            "planned_frame_states": 3360,
        })
        by_task = {}
        for row in first:
            by_task.setdefault(row["planned_task_id"], []).append(row["condition"])
        self.assertTrue(all(tuple(value) == protocol.condition_order(key) for key, value in by_task.items()))

    def test_03_frozen_engineering_subset_is_24_one_step_conditions(self):
        rows = runtime._phase_rows("engineering")
        self.assertEqual(len(rows), 24)
        self.assertEqual(sum(int(row["scheduler_positions"]) for row in rows), 24)
        self.assertEqual({int(row["seed_index"]) for row in rows}, {1})

    def test_04_sham_is_deterministic_unit_and_orthogonal(self):
        import torch

        direction = torch.arange(1, 9, dtype=torch.float32)
        direction = direction / torch.linalg.vector_norm(direction)
        first, attempt1 = instrumentation.deterministic_sham_direction("eyeglasses", "FEY_01", 0, direction)
        second, attempt2 = instrumentation.deterministic_sham_direction("eyeglasses", "FEY_01", 0, direction)
        self.assertTrue(torch.equal(first, second))
        self.assertEqual(attempt1, attempt2)
        self.assertAlmostEqual(float(torch.linalg.vector_norm(first)), 1.0, places=6)
        self.assertLessEqual(abs(float(torch.dot(first, direction))), 1e-6)

    def test_05_complete_transient_intervention_math(self):
        import torch

        tensors, metadata = synthetic_lfe_panel()
        bundle = instrumentation.build_transient_interventions(tensors, metadata, expected_dim=8)
        self.assertEqual(len(bundle.directions), 640)
        self.assertEqual(len(bundle.sham_directions), 640)
        self.assertEqual(len(bundle.selected), 120)
        self.assertEqual(len(bundle.diagnostics), 640)
        pair = "FEY_01"
        positive = protocol.unit_id("eyeglasses", pair, "positive")
        control = protocol.unit_id("eyeglasses", pair, "control")
        for token in range(protocol.LFE_TOKENS):
            direction = bundle.directions[("eyeglasses", pair, token)]
            target_projection = torch.dot(bundle.selected[(positive, "target_projection_exchange")][0, token], direction)
            counterpart_projection = torch.dot(bundle.unmodified[control][0, token], direction)
            self.assertTrue(instrumentation.within_frozen_tolerance(target_projection, counterpart_projection))

    def test_06_output_hook_expands_identically_across_cfg_rows(self):
        import torch

        module = torch.nn.Identity()
        direct = torch.randn(1, protocol.LFE_TOKENS, 8)
        selected = direct + 0.25
        with instrumentation.LFEOutputOverride(module, direct, selected, expected_dim=8) as hook:
            output = module(direct.expand(2, -1, -1).clone())
        hook.verify_calls(1)
        self.assertTrue(torch.equal(output[0], output[1]))
        self.assertTrue(torch.equal(output[0], selected[0]))

    def test_07_degenerate_direction_fails_complete_transaction(self):
        import torch

        tensors, metadata = synthetic_lfe_panel()
        shared = torch.ones(1, protocol.LFE_TOKENS, 8)
        for unit in tensors:
            tensors[unit] = shared.clone()
        with self.assertRaises(instrumentation.ControlledInterventionInstrumentationError):
            instrumentation.build_transient_interventions(tensors, metadata, expected_dim=8)

    def test_08_complete_outcome_analyzer_and_independent_recomputation(self):
        rows = synthetic_outcomes()
        result = analyzer.analyze_rows(rows)
        self.assertEqual(result["status"], "COMPLETE_FIXED_PANEL_ANALYSIS")
        self.assertEqual(len(result["unit_condition_scores"]), 120)
        self.assertEqual(len(result["pair_effects"]), 20)
        self.assertEqual(len(result["coverage_by_attribute_condition"]), 6)
        self.assertTrue(all(row["aggregate_computed"] for row in result["attribute_summaries"]))
        self.assertTrue(all(row["primary_role_aligned_target_minus_sham"] == 1.0 for row in result["pair_effects"]))
        proof = verifier.verify_analysis(rows, result)
        self.assertEqual(proof["pair_effects_recomputed"], 20)

    def test_09_missingness_withholds_reduced_panel_aggregate(self):
        rows = synthetic_outcomes()
        rows = [row for row in rows if not (
            row["attribute"] == "eyeglasses" and row["formal_pair_id"] == "FEY_01"
            and row["role"] == "control" and row["condition"] == "target_projection_exchange"
        )]
        result = analyzer.analyze_rows(rows)
        summary = next(row for row in result["attribute_summaries"] if row["attribute"] == "eyeglasses")
        self.assertFalse(summary["aggregate_computed"])
        self.assertEqual(summary["pairs_complete"], 9)
        verifier.verify_analysis(rows, result)

    def test_10_duplicate_key_withholds_aggregate(self):
        rows = synthetic_outcomes()
        rows.append(copy.deepcopy(rows[0]))
        result = analyzer.analyze_rows(rows)
        attribute = rows[0]["attribute"]
        summary = next(row for row in result["attribute_summaries"] if row["attribute"] == attribute)
        self.assertFalse(summary["aggregate_computed"])

    def test_11_independent_verifier_detects_effect_tamper(self):
        rows = synthetic_outcomes()
        result = analyzer.analyze_rows(rows)
        result["pair_effects"][0]["primary_role_aligned_target_minus_sham"] = 0.5
        with self.assertRaises(verifier.ControlledInterventionVerificationError):
            verifier.verify_analysis(rows, result)

    def test_12_transformer_input_invariants_are_scalar_hashes(self):
        import torch

        class FakeTransformer(torch.nn.Module):
            def forward(self, hidden_states=None):
                return hidden_states

        transformer = FakeTransformer()
        hidden = torch.arange(64, dtype=torch.float32).reshape(2, 1, 8, 2, 2)
        with instrumentation.TransformerInputInvariantRecorder(transformer) as recorder:
            transformer(hidden_states=hidden)
            transformer(hidden_states=hidden)
        result = recorder.finish(2)
        self.assertEqual(len(result["initial_denoising_input_sha256"]), 64)
        self.assertEqual(len(result["spatial_reference_route_sha256"]), 64)
        self.assertEqual(result["hidden_shape"], "2x1x8x2x2")
        self.assertEqual(result["hidden_device_type"], "cpu")

    def test_13_static_safety_and_current_gpu_entry_block(self):
        self.assertEqual(
            verifier.assert_static_safety(),
            {
                "top_level_ml_imports": 0,
                "forbidden_identity_lfe_or_direction_tensor_serializers": 0,
                "future_private_final_latent_serializer_sites": 1,
            },
        )
        with self.assertRaises(runner.ControlledInterventionRunnerError):
            runner.validate_active(protocol.IMPLEMENTATION_AUTH, Path("/tmp/not-authorized"), "engineering")


if __name__ == "__main__":
    unittest.main()
