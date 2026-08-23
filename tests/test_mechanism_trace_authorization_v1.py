#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
sys.path.insert(0, str(SRC))

import mechanism_trace_protocol_v1 as protocol  # noqa: E402


class ExecutionAuthorizationTests(unittest.TestCase):
    def authorization(self, code_path: Path) -> dict:
        return {
            "status": "AUTHORIZED_FOR_MECHANISM_TRACE_EXECUTION",
            "phase": "engineering",
            "consisid_commit": protocol.EXPECTED_CONSISID_COMMIT,
            "research_commit": "research-head",
            "consisid_repository": "/frozen/consisid",
            "code_sha256": {code_path.name: protocol.sha256(code_path)},
            "gpu_execution_explicitly_approved": True,
            "trajectory_ceiling": 24,
            "transformer_step_ceiling": 1200,
            "phase_gpu_hours_ceiling": 12.0,
        }

    @staticmethod
    def git_value(repo: Path, *args: str) -> str:
        if args == ("status", "--short"):
            return ""
        if Path(repo) == protocol.REPO:
            return "research-head"
        return protocol.EXPECTED_CONSISID_COMMIT

    def test_complete_engineering_authorization_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code_path = root / "code.py"
            code_path.write_text("bounded = True\n", encoding="utf-8")
            auth_path = root / "authorization.json"
            auth_path.write_text(json.dumps(self.authorization(code_path)), encoding="utf-8")
            with patch.object(protocol, "git_value", side_effect=self.git_value):
                result = protocol.validate_execution_authorization(
                    auth_path, "engineering", [code_path]
                )
            self.assertTrue(result["gpu_execution_explicitly_approved"])

    def test_gpu_hour_ceiling_above_total_budget_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code_path = root / "code.py"
            code_path.write_text("bounded = True\n", encoding="utf-8")
            auth = self.authorization(code_path)
            auth["phase_gpu_hours_ceiling"] = 72.01
            auth_path = root / "authorization.json"
            auth_path.write_text(json.dumps(auth), encoding="utf-8")
            with patch.object(protocol, "git_value", side_effect=self.git_value):
                with self.assertRaisesRegex(protocol.ProtocolError, "GPU-hour ceiling"):
                    protocol.validate_execution_authorization(auth_path, "engineering", [code_path])

    def test_scientific_phase_requires_passed_engineering_controls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code_path = root / "code.py"
            code_path.write_text("bounded = True\n", encoding="utf-8")
            auth = self.authorization(code_path)
            auth.update(
                phase="scientific",
                trajectory_ceiling=160,
                transformer_step_ceiling=8000,
            )
            auth_path = root / "authorization.json"
            auth_path.write_text(json.dumps(auth), encoding="utf-8")
            with patch.object(protocol, "git_value", side_effect=self.git_value):
                with self.assertRaisesRegex(protocol.ProtocolError, "engineering verification"):
                    protocol.validate_execution_authorization(auth_path, "scientific", [code_path])


if __name__ == "__main__":
    unittest.main(verbosity=2)
