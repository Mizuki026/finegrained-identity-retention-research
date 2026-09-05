#!/usr/bin/env python3
"""Independent CPU-only verifier for the sham-projection numerical correction."""
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
    / "governance/mechanism_controlled_intervention_sham_projection_correction_v1"
    / "researcher_sham_projection_correction_authorization_v1.json"
)
ABORT_FREEZE = (
    REPO
    / "governance/mechanism_controlled_intervention_engineering_v1"
    / "engineering_run_002_abort_freeze_v1.json"
)
AUTH_STATUS = (
    "CPU_ONLY_SHAM_PROJECTION_NUMERICAL_INVARIANT_DIAGNOSTIC_AND_"
    "THRESHOLD_PRESERVING_CORRECTION_TESTS_AUTHORIZED_ONLY"
)
ABORT_STATUS = "FROZEN_ABORTED_FAIL_CLOSED_SHAM_PROJECTION_INVARIANT_BEFORE_ANY_TRAJECTORY"
ABORT_BYTES = 3557
ABORT_SHA256 = "413a29c5de1b67e6d529352231ee29778994f70acf991c04c3d91d981e675f84"


class ShamProjectionCorrectionVerificationError(RuntimeError):
    """Raised when the correction or a frozen binding drifts."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify() -> dict[str, object]:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise ShamProjectionCorrectionVerificationError("verifier must start CUDA-hidden and torch-free")
    auth = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    if auth.get("status") != AUTH_STATUS:
        raise ShamProjectionCorrectionVerificationError("correction authorization status drift")
    if ABORT_FREEZE.stat().st_size != ABORT_BYTES or sha256(ABORT_FREEZE) != ABORT_SHA256:
        raise ShamProjectionCorrectionVerificationError("run_002 abort freeze binding drift")
    abort = json.loads(ABORT_FREEZE.read_text(encoding="utf-8"))
    if abort.get("status") != ABORT_STATUS:
        raise ShamProjectionCorrectionVerificationError("run_002 abort freeze status drift")
    if protocol.DIRECTION_ATOL != 1e-6:
        raise ShamProjectionCorrectionVerificationError("frozen absolute tolerance changed")
    source = (REPO / "src/controlled_lfe_projection_exchange_instrumentation_v1.py").read_text()
    required_markers = (
        "sham = base[token_index] + delta * sham_direction",
        "displacement = sham - base",
        "return torch.dot(displacement, direction)",
    )
    if any(marker not in source for marker in required_markers):
        raise ShamProjectionCorrectionVerificationError("frozen formula or stable evaluator marker missing")
    if "sham_projection - base_projection" in source:
        raise ShamProjectionCorrectionVerificationError("cancellation-prone evaluator remains active")

    import torch

    generator = torch.Generator(device="cpu").manual_seed(20260905)
    direction = torch.randn(2048, generator=generator)
    direction = direction / torch.linalg.vector_norm(direction)
    sham_direction, attempt = instrumentation.deterministic_sham_direction(
        "eyeglasses", "FEY_01", 0, direction
    )
    torch.randn(2048, generator=generator)
    torch.randn(2048, generator=generator)
    base = torch.randn(2048, generator=generator) * 10.0
    delta = 0.1
    sham = base + delta * sham_direction
    old_residual = abs(float((torch.dot(sham, direction) - torch.dot(base, direction)).item()))
    stable_residual = abs(float(
        instrumentation.sham_displacement_direction_dot(sham, base, direction).item()
    ))
    direction_residual = abs(float(torch.dot(sham_direction, direction).item()))
    if not old_residual > protocol.DIRECTION_ATOL:
        raise ShamProjectionCorrectionVerificationError("synthetic cancellation counterexample disappeared")
    if stable_residual > protocol.DIRECTION_ATOL or direction_residual > protocol.DIRECTION_ATOL:
        raise ShamProjectionCorrectionVerificationError("stable frozen invariant did not pass")
    if not torch.equal(sham, base + delta * sham_direction):
        raise ShamProjectionCorrectionVerificationError("sham intervention formula changed")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_CPU_ONLY_SHAM_PROJECTION_CORRECTION_VERIFICATION",
        "synthetic_seed": 20260905,
        "synthetic_dimension": 2048,
        "synthetic_base_scale": 10.0,
        "synthetic_delta": delta,
        "sham_attempt": attempt,
        "frozen_absolute_tolerance": protocol.DIRECTION_ATOL,
        "old_projection_subtraction_abs_residual": old_residual,
        "stable_displacement_dot_abs_residual": stable_residual,
        "sham_direction_abs_dot": direction_residual,
        "old_evaluator_exceeds_frozen_tolerance": True,
        "stable_evaluator_passes_frozen_tolerance": True,
        "sham_formula_unchanged": True,
        "threshold_changed": False,
        "formal_manifest_or_reference_opened": False,
        "model_or_weight_loaded": False,
        "gpu_used": False,
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
        raise ShamProjectionCorrectionVerificationError("refusing to overwrite verifier output")
    args.output.parent.mkdir(parents=True, exist_ok=False)
    partial.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    partial.replace(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ShamProjectionCorrectionVerificationError, OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
