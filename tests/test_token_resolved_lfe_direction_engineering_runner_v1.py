#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib.util
import os
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
sys.path.insert(0, str(SRC))

import run_token_resolved_lfe_direction_engineering_v1 as runner  # noqa: E402
import token_resolved_lfe_direction_protocol_v1 as protocol  # noqa: E402


class TokenDirectionEngineeringRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": ""})
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()

    def test_engineering_plan_is_complete_fixed_family(self) -> None:
        _, rows = protocol.validate_formal_master()
        plan = protocol.engineering_plan(rows)
        self.assertEqual(len(plan), 24)
        self.assertEqual(len({row["formal_unit_id"] for row in plan}), 8)
        self.assertEqual(Counter(row["operation"] for row in plan), Counter({
            "direct_lfe_repeat_1": 8,
            "direct_lfe_repeat_2": 8,
            "one_step_hook_equivalence": 8,
        }))

    def test_runner_runtime_files_have_no_top_level_ml_imports(self) -> None:
        runner._assert_no_top_level_ml_imports()

    def test_runtime_has_no_tensor_serialization_api(self) -> None:
        runtime_path = SRC / "token_resolved_lfe_direction_engineering_runtime_v1.py"
        tree = ast.parse(runtime_path.read_text(encoding="utf-8"))
        called = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertFalse({"save", "torch_save", "numpy", "tolist"} & called)

    def test_runner_rejects_non_active_phase_e_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = root / "draft.json"
            draft.write_text(
                '{"status":"PHASE_E_EXECUTION_PACKAGE_READY_RESEARCHER_FINAL_APPROVAL_REQUIRED"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                runner.RunnerGateError, "lacks final active researcher authorization"
            ):
                runner.validate_active_execution_authorization(draft, root / "output")

    def test_runtime_module_import_does_not_import_torch_or_models(self) -> None:
        before = set(sys.modules)
        path = SRC / "token_resolved_lfe_direction_engineering_runtime_v1.py"
        spec = importlib.util.spec_from_file_location("phase_e_runtime_import_test", path)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        newly_imported = set(sys.modules) - before
        self.assertNotIn("torch", newly_imported)
        self.assertFalse(any(name == "models" or name.startswith("models.") for name in newly_imported))

    def test_dry_run_verifier_reconstructs_exact_plan(self) -> None:
        _, rows = protocol.validate_formal_master()
        plan = protocol.engineering_plan(rows)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "dry"
            output.mkdir()
            protocol.atomic_csv(output / "phase_e_engineering_plan_v1.csv", tuple(plan[0]), plan)
            summary = {
                "status": "PASS_PHASE_E_RUNNER_CPU_ONLY_NO_WEIGHT_DRY_RUN",
                "engineering_units": 8,
                "direct_passes": 16,
                "hook_controls": 8,
                "transformer_step_ceiling": 8,
            }
            for field in (
                "torch_imported", "consisid_modules_imported", "reference_images_opened",
                "reference_images_decoded", "face_preprocessing_run", "model_weights_loaded",
                "raw_tokens_captured_or_persisted", "pipeline_forward_run",
                "scientific_extraction_run", "outcomes_opened_or_joined", "gpu_used",
                "network_used", "gpu_execution_authorized_by_this_artifact",
            ):
                summary[field] = False
            protocol.atomic_json(output / "phase_e_runner_no_weight_dry_run_v1.json", summary)
            from verify_token_resolved_lfe_direction_engineering_v1 import verify_dry_run

            result = verify_dry_run(output, root / "verification.json")
            self.assertEqual(
                result["status"],
                "PASS_INDEPENDENT_PHASE_E_RUNNER_NO_WEIGHT_DRY_RUN_VERIFICATION",
            )

