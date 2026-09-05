#!/usr/bin/env python3
"""Independent CPU-only verifier for sham displacement construction correction."""
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
    / "governance/mechanism_controlled_intervention_sham_construction_correction_v1"
    / "researcher_sham_construction_correction_authorization_v1.json"
)
ABORT_FREEZE = (
    REPO
    / "governance/mechanism_controlled_intervention_engineering_v1"
    / "engineering_run_003_abort_freeze_v1.json"
)
AUTH_STATUS = (
    "CPU_ONLY_SHAM_DISPLACEMENT_CONSTRUCTION_NUMERICAL_DIAGNOSTIC_AND_"
    "FROZEN_DESIGN_PRESERVING_CORRECTION_TESTS_AUTHORIZED_ONLY"
)
ABORT_STATUS = (
    "FROZEN_ABORTED_FAIL_CLOSED_STABLE_SHAM_DISPLACEMENT_"
    "ORTHOGONALITY_INVARIANT_BEFORE_ANY_TRAJECTORY"
)
ABORT_BYTES = 4120
ABORT_SHA256 = "fda4e9da2a6d0201c586ea2926a4db76a9e0b2bc441f8823b78d59e313882c80"


class ShamConstructionCorrectionVerificationError(RuntimeError):
    """Raised when the correction, diagnostic, or frozen binding drifts."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify() -> dict[str, object]:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise ShamConstructionCorrectionVerificationError("verifier must start CUDA-hidden and torch-free")
    auth = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    if auth.get("status") != AUTH_STATUS:
        raise ShamConstructionCorrectionVerificationError("construction correction authority drift")
    if ABORT_FREEZE.stat().st_size != ABORT_BYTES or sha256(ABORT_FREEZE) != ABORT_SHA256:
        raise ShamConstructionCorrectionVerificationError("run_003 abort freeze binding drift")
    if json.loads(ABORT_FREEZE.read_text(encoding="utf-8")).get("status") != ABORT_STATUS:
        raise ShamConstructionCorrectionVerificationError("run_003 abort status drift")
    if protocol.DIRECTION_ATOL != 1e-6:
        raise ShamConstructionCorrectionVerificationError("frozen absolute tolerance changed")

    source = (REPO / "src/controlled_lfe_projection_exchange_instrumentation_v1.py").read_text()
    required_markers = (
        "target_displacement_vector = delta * direction",
        "sham_displacement_vector = delta * sham_direction",
        "target = base[token_index] + target_displacement_vector",
        "sham = base[token_index] + sham_displacement_vector",
        "constructed_displacement_direction_dot(\n                    sham_displacement_vector, direction",
    )
    if any(marker not in source for marker in required_markers):
        raise ShamConstructionCorrectionVerificationError("construction-grounded invariant marker missing")

    import torch

    generator = torch.Generator(device="cpu").manual_seed(20260906)
    cases = 0
    realized_failures = 0
    constructed_failures = 0
    ideal_amplification_failures = 0
    reconstruction_dominant_failures = 0
    max_q_dot = 0.0
    max_realized_residual = 0.0
    max_constructed_residual = 0.0
    for index in range(640):
        direction = torch.randn(2048, generator=generator)
        direction = direction / torch.linalg.vector_norm(direction)
        attribute = "eyeglasses" if index < 320 else "facial_hair"
        prefix = "FEY" if index < 320 else "FFH"
        pair = f"{prefix}_{(index // 32) % 10 + 1:02d}"
        sham_direction, _ = instrumentation.deterministic_sham_direction(
            attribute, pair, index % 32, direction
        )
        q_dot = abs(float(torch.dot(sham_direction, direction).item()))
        max_q_dot = max(max_q_dot, q_dot)
        for scale in (0.1, 1.0, 10.0):
            base = torch.randn(2048, generator=generator) * scale
            for delta in (0.1, 1.0, 10.0):
                cases += 1
                constructed = delta * sham_direction
                sham = base + constructed
                realized = abs(float(torch.dot(sham - base, direction).item()))
                stable = abs(float(
                    instrumentation.constructed_displacement_direction_dot(
                        constructed, direction
                    ).item()
                ))
                ideal = abs(delta * float(torch.dot(sham_direction, direction).item()))
                max_realized_residual = max(max_realized_residual, realized)
                max_constructed_residual = max(max_constructed_residual, stable)
                if realized > protocol.DIRECTION_ATOL:
                    realized_failures += 1
                    if ideal > protocol.DIRECTION_ATOL:
                        ideal_amplification_failures += 1
                    else:
                        reconstruction_dominant_failures += 1
                constructed_failures += int(stable > protocol.DIRECTION_ATOL)
                if not torch.equal(sham, base + delta * sham_direction):
                    raise ShamConstructionCorrectionVerificationError("sham tensor formula changed")
    if cases != 5760 or realized_failures <= 0 or reconstruction_dominant_failures <= 0:
        raise ShamConstructionCorrectionVerificationError("synthetic reconstruction failure not reproduced")
    if constructed_failures != 0 or ideal_amplification_failures != 0:
        raise ShamConstructionCorrectionVerificationError("constructed displacement stress gate failed")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_CPU_ONLY_SHAM_CONSTRUCTION_CORRECTION_VERIFICATION",
        "synthetic_seed": 20260906,
        "synthetic_directions": 640,
        "synthetic_scenarios": cases,
        "synthetic_dimension": 2048,
        "base_scales": [0.1, 1.0, 10.0],
        "deltas": [0.1, 1.0, 10.0],
        "frozen_absolute_tolerance": protocol.DIRECTION_ATOL,
        "realized_add_subtract_failures": realized_failures,
        "constructed_displacement_failures": constructed_failures,
        "ideal_amplification_failures": ideal_amplification_failures,
        "reconstruction_dominant_failures": reconstruction_dominant_failures,
        "max_sham_direction_abs_dot": max_q_dot,
        "max_realized_add_subtract_abs_residual": max_realized_residual,
        "max_constructed_displacement_abs_residual": max_constructed_residual,
        "sham_tensor_formula_unchanged": True,
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
        raise ShamConstructionCorrectionVerificationError("refusing to overwrite verifier output")
    args.output.parent.mkdir(parents=True, exist_ok=False)
    partial.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    partial.replace(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ShamConstructionCorrectionVerificationError, OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
