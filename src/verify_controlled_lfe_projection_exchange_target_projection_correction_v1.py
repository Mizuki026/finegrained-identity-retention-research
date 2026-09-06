#!/usr/bin/env python3
"""Independent CPU-only verifier for target projection construction correction."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import controlled_lfe_projection_exchange_instrumentation_v1 as instrumentation
import controlled_lfe_projection_exchange_protocol_v1 as protocol

AUTHORIZATION = (
    REPO
    / "governance/mechanism_controlled_intervention_target_projection_correction_v1"
    / "researcher_target_projection_correction_authorization_v1.json"
)
ABORT_FREEZE = (
    REPO
    / "governance/mechanism_controlled_intervention_engineering_v1"
    / "engineering_run_004_abort_freeze_v1.json"
)
AUTH_STATUS = (
    "CPU_ONLY_TARGET_PROJECTION_CONSTRUCTION_NUMERICAL_DIAGNOSTIC_AND_"
    "FROZEN_DESIGN_PRESERVING_CORRECTION_TESTS_AUTHORIZED_ONLY"
)
ABORT_STATUS = (
    "FROZEN_ABORTED_FAIL_CLOSED_TARGET_PROJECTION_EXCHANGE_"
    "INVARIANT_BEFORE_ANY_TRAJECTORY"
)
ABORT_BYTES = 4585
ABORT_SHA256 = "b3ee540e9303b5e50dc60029a84fdba1625b48ec6636c7c378ebfcd2f35b4cab"


class TargetProjectionCorrectionVerificationError(RuntimeError):
    """Raised when the correction, diagnostic, or frozen binding drifts."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify() -> dict[str, object]:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise TargetProjectionCorrectionVerificationError("verifier must start CUDA-hidden and torch-free")
    auth = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    if auth.get("status") != AUTH_STATUS:
        raise TargetProjectionCorrectionVerificationError("target projection correction authority drift")
    if ABORT_FREEZE.stat().st_size != ABORT_BYTES or sha256(ABORT_FREEZE) != ABORT_SHA256:
        raise TargetProjectionCorrectionVerificationError("run_004 abort freeze binding drift")
    if json.loads(ABORT_FREEZE.read_text(encoding="utf-8")).get("status") != ABORT_STATUS:
        raise TargetProjectionCorrectionVerificationError("run_004 abort status drift")
    if protocol.DIRECTION_ATOL != 1e-6:
        raise TargetProjectionCorrectionVerificationError("frozen absolute tolerance changed")

    source = (REPO / "src/controlled_lfe_projection_exchange_instrumentation_v1.py").read_text()
    required_markers = (
        "delta = torch.dot(counterpart[token_index] - base[token_index], direction)",
        "target_displacement_vector = delta * direction",
        "target = base[token_index] + target_displacement_vector",
        (
            "target_displacement_direction_dot = constructed_displacement_direction_dot(\n"
            "                    target_displacement_vector, direction"
        ),
        "within_frozen_tolerance(target_displacement_direction_dot, delta)",
    )
    if any(marker not in source for marker in required_markers):
        raise TargetProjectionCorrectionVerificationError("construction-grounded target marker missing")
    if "within_frozen_tolerance(target_projection, counterpart_projection)" in source:
        raise TargetProjectionCorrectionVerificationError("realized target projection gate remains active")

    import torch

    generator = torch.Generator(device="cpu").manual_seed(20260907)
    cases = 0
    realized_failures = 0
    constructed_failures = 0
    max_realized_residual = 0.0
    max_constructed_residual = 0.0
    for _index in range(640):
        direction = torch.randn(2048, generator=generator)
        direction = direction / torch.linalg.vector_norm(direction)
        for base_scale in (0.1, 1.0, 10.0):
            base = torch.randn(2048, generator=generator) * base_scale
            for difference_scale in (0.1, 1.0, 10.0):
                counterpart = base + torch.randn(2048, generator=generator) * difference_scale
                delta = torch.dot(counterpart - base, direction)
                target_displacement_vector = delta * direction
                target = base + target_displacement_vector
                realized_projection = torch.dot(target, direction)
                counterpart_projection = torch.dot(counterpart, direction)
                constructed_projection_delta = instrumentation.constructed_displacement_direction_dot(
                    target_displacement_vector, direction
                )
                realized_residual = abs(float((realized_projection - counterpart_projection).item()))
                constructed_residual = abs(float((constructed_projection_delta - delta).item()))
                cases += 1
                max_realized_residual = max(max_realized_residual, realized_residual)
                max_constructed_residual = max(max_constructed_residual, constructed_residual)
                realized_failures += int(not instrumentation.within_frozen_tolerance(
                    realized_projection, counterpart_projection
                ))
                constructed_failures += int(not instrumentation.within_frozen_tolerance(
                    constructed_projection_delta, delta
                ))
                if not torch.equal(target, base + delta * direction):
                    raise TargetProjectionCorrectionVerificationError("target tensor formula changed")
    if cases != 5760 or realized_failures <= 0:
        raise TargetProjectionCorrectionVerificationError("synthetic realization failure not reproduced")
    if constructed_failures != 0:
        raise TargetProjectionCorrectionVerificationError("constructed target projection gate failed")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_CPU_ONLY_TARGET_PROJECTION_CONSTRUCTION_CORRECTION_VERIFICATION",
        "synthetic_seed": 20260907,
        "synthetic_directions": 640,
        "synthetic_scenarios": cases,
        "synthetic_dimension": 2048,
        "base_scales": [0.1, 1.0, 10.0],
        "difference_scales": [0.1, 1.0, 10.0],
        "frozen_absolute_tolerance": 1e-6,
        "frozen_relative_tolerance": 1e-5,
        "realized_target_projection_failures": realized_failures,
        "constructed_target_projection_failures": constructed_failures,
        "max_realized_target_projection_abs_residual": max_realized_residual,
        "max_constructed_target_projection_abs_residual": max_constructed_residual,
        "target_tensor_formula_unchanged": True,
        "delta_direction_and_dose_unchanged": True,
        "threshold_changed": False,
        "formal_manifest_or_reference_opened": False,
        "model_or_weight_loaded": False,
        "gpu_used": False,
        "no_weight_dry_run": False,
        "engineering_execution": False,
        "outcome_opened": False,
        "network_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify()
    partial = args.output.with_suffix(args.output.suffix + ".partial")
    if args.output.exists() or partial.exists():
        raise TargetProjectionCorrectionVerificationError("refusing to overwrite verifier output")
    args.output.parent.mkdir(parents=True, exist_ok=False)
    partial.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    partial.replace(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (TargetProjectionCorrectionVerificationError, OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
