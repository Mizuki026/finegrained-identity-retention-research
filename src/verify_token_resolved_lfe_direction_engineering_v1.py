#!/usr/bin/env python3
"""Independent stdlib verifier for Phase-E runner dry-run and execution outputs."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import token_resolved_lfe_direction_protocol_v1 as protocol


class VerificationError(RuntimeError):
    pass


def verify_plan(output_dir: Path) -> list[dict[str, str]]:
    plan = protocol.read_csv(output_dir / "phase_e_engineering_plan_v1.csv")
    _, formal = protocol.validate_formal_master()
    expected = protocol.engineering_plan(formal)
    if plan != expected:
        raise VerificationError("serialized Phase-E plan differs from independent reconstruction")
    if len(plan) != 24 or len({row["formal_unit_id"] for row in plan}) != 8:
        raise VerificationError("Phase-E plan universe drift")
    operations = Counter(row["operation"] for row in plan)
    if operations != Counter({
        "direct_lfe_repeat_1": 8,
        "direct_lfe_repeat_2": 8,
        "one_step_hook_equivalence": 8,
    }):
        raise VerificationError("Phase-E operation counts drift")
    return plan


def verify_dry_run(output_dir: Path, verification_output: Path) -> dict:
    plan = verify_plan(output_dir)
    summary_path = output_dir / "phase_e_runner_no_weight_dry_run_v1.json"
    summary = protocol.read_json(summary_path)
    if summary.get("status") != "PASS_PHASE_E_RUNNER_CPU_ONLY_NO_WEIGHT_DRY_RUN":
        raise VerificationError("runner dry-run did not pass")
    false_fields = (
        "torch_imported", "consisid_modules_imported", "reference_images_opened",
        "reference_images_decoded", "face_preprocessing_run", "model_weights_loaded",
        "raw_tokens_captured_or_persisted", "pipeline_forward_run",
        "scientific_extraction_run", "outcomes_opened_or_joined", "gpu_used",
        "network_used", "gpu_execution_authorized_by_this_artifact",
    )
    if any(summary.get(field) is not False for field in false_fields):
        raise VerificationError("dry-run reports a forbidden action")
    if summary.get("engineering_units") != 8 or summary.get("direct_passes") != 16:
        raise VerificationError("dry-run engineering count mismatch")
    if summary.get("hook_controls") != 8 or summary.get("transformer_step_ceiling") != 8:
        raise VerificationError("dry-run hook/step count mismatch")
    result = {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_PHASE_E_RUNNER_NO_WEIGHT_DRY_RUN_VERIFICATION",
        "dry_run_summary": {
            "path": str(summary_path.resolve()),
            "bytes": summary_path.stat().st_size,
            "sha256": protocol.sha256(summary_path),
        },
        "plan_rows": len(plan),
        "engineering_units": 8,
        "direct_passes": 16,
        "hook_controls": 8,
        "gpu_used": False,
        "model_or_weight_loading": False,
        "reference_decode": False,
        "scientific_extraction": False,
        "outcome_access": False,
    }
    protocol.atomic_json(verification_output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def verify_execution(output_dir: Path, verification_output: Path) -> dict:
    status = protocol.read_csv(output_dir / "phase_e_task_status_v1.csv")
    controls = protocol.read_csv(output_dir / "phase_e_equivalence_controls_v1.csv")
    summary_path = output_dir / "phase_e_execution_summary_v1.json"
    summary = protocol.read_json(summary_path)
    if len(status) != 24 or len({row["reference_task_id"] for row in status}) != 24:
        raise VerificationError("Phase-E status universe drift")
    if any(row["status"] != "COMPLETE_TRANSIENT_TENSORS_ONLY" for row in status):
        raise VerificationError("Phase-E operation incomplete")
    if len(controls) != 8 or len({row["formal_unit_id"] for row in controls}) != 8:
        raise VerificationError("Phase-E equivalence universe drift")
    if any(row["direct_repeat_equal"] != "True" or row["direct_hook_equal"] != "True" for row in controls):
        raise VerificationError("Phase-E equivalence control failed")
    if summary.get("status") != "PHASE_E_COMPLETE_PENDING_INDEPENDENT_VERIFICATION":
        raise VerificationError("Phase-E execution summary status mismatch")
    if summary.get("operations_complete") != 24 or summary.get("transformer_steps_executed") != 8:
        raise VerificationError("Phase-E execution counts mismatch")
    if summary.get("raw_identity_or_token_tensor_files_written") != 0:
        raise VerificationError("raw identity/token tensor persistence detected")
    if summary.get("scientific_extraction_run") is not False or summary.get("outcomes_opened_or_joined") is not False:
        raise VerificationError("Phase-E crossed scientific/outcome boundary")
    result = {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_TOKEN_DIRECTION_PHASE_E_VERIFICATION",
        "engineering_units": 8,
        "direct_passes": 16,
        "hook_controls": 8,
        "transformer_steps": 8,
        "raw_tensor_files": 0,
        "scientific_extraction": False,
        "outcome_access": False,
        "execution_summary": {
            "path": str(summary_path.resolve()),
            "bytes": summary_path.stat().st_size,
            "sha256": protocol.sha256(summary_path),
        },
    }
    protocol.atomic_json(verification_output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("dry-run", "execution"))
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verification-output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "dry-run":
        verify_dry_run(args.output_dir, args.verification_output)
    else:
        verify_execution(args.output_dir, args.verification_output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (VerificationError, protocol.DirectionProtocolError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
