#!/usr/bin/env python3
"""CPU-only independent verification for the Phase-S seed correction."""
from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
GOVERNANCE = REPO / "governance" / "mechanism_trace_phase_s_correction_v1"
ABORT = REPO / "governance" / "mechanism_trace_phase_s_abort_001"
AUTHORIZATION = GOVERNANCE / "researcher_protocol_correction_authorization_v1.json"
ABORT_FREEZE = ABORT / "phase_s_abort_freeze_v1.json"
DRY_RUN = GOVERNANCE / "no_weight_dry_run_v1"
DRY_SUMMARY = DRY_RUN / "dry_run_summary_v1.json"
DRY_VERIFICATION = GOVERNANCE / "no_weight_dry_run_verification_v1.json"
FUTURE_AUTHORIZATION = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/"
    "phase_s_run_002_execution_authorization_v1.json"
)
FUTURE_RUN = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_002"
)


class VerificationError(RuntimeError):
    """Fail-closed correction verifier error."""


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def run_cpu_tests() -> int:
    environment = dict(os.environ)
    environment.update(
        CUDA_VISIBLE_DEVICES="",
        PYTHONPATH=str(SRC),
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        TOKENIZERS_PARALLELISM="false",
    )
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-p",
        "test_mechanism_trace*.py",
        "-v",
    ]
    result = subprocess.run(
        command,
        cwd=REPO,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    require(result.returncode == 0, result.stdout + result.stderr)
    match = re.search(r"Ran (\d+) tests", result.stdout + result.stderr)
    require(match is not None, "could not parse CPU test count")
    return int(match.group(1))


def verify() -> dict:
    require("torch" not in sys.modules, "verifier imported torch before checks")
    sys.path.insert(0, str(SRC))
    import mechanism_trace_instrumentation_v1 as instrumentation

    require("torch" not in sys.modules, "instrumentation import was not lazy")
    authorization = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    abort_freeze = json.loads(ABORT_FREEZE.read_text(encoding="utf-8"))
    dry_summary = json.loads(DRY_SUMMARY.read_text(encoding="utf-8"))
    dry_verification = json.loads(DRY_VERIFICATION.read_text(encoding="utf-8"))

    require(
        authorization["status"]
        == "AUTHORIZED_FOR_CODE_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_ONLY",
        "researcher correction authorization status mismatch",
    )
    require(
        authorization["abort_freeze_sha256"] == sha256(ABORT_FREEZE),
        "abort freeze hash mismatch",
    )
    require(
        abort_freeze["safety_state"]["partial_artifacts_reused"] is False,
        "abort partial artifacts were marked reusable",
    )
    require(
        authorization["gpu_execution_authorized"] is False
        and authorization["model_loading_authorized"] is False,
        "correction authorization unexpectedly permits GPU/model loading",
    )
    require(not FUTURE_AUTHORIZATION.exists(), "replacement execution authorization exists")
    require(not FUTURE_RUN.exists(), "future Phase-S run directory already exists")

    require(
        len(instrumentation.REFERENCE_VECTOR_STAGES) == 9
        and len(instrumentation.DETERMINISTIC_REFERENCE_VECTOR_STAGES) == 8,
        "representation stage counts changed",
    )
    require(
        instrumentation.REFERENCE_VECTOR_STAGES[-1]
        == instrumentation.IMAGE_LATENT_VECTOR_STAGE,
        "sampled image-latent stage is not isolated",
    )
    mean_source = inspect.getsource(instrumentation.ReferenceReadout._unit_mean_vectors)
    require(".mean(dim=0)" in mean_source, "four-seed arithmetic mean is missing")
    require("_l2_normalize" not in mean_source, "unit mean applies a second normalization")

    require(
        dry_summary["status"] == "DRY_RUN_NO_MODEL_IMPORT_NO_WEIGHT_LOAD"
        and dry_summary["task_count"] == 184
        and dry_summary["transformer_steps"] == 9200,
        "no-weight dry-run summary mismatch",
    )
    require(
        dry_summary["torch_imported"] is False
        and dry_summary["consisid_modules_imported"] is False,
        "no-weight dry-run imported ML modules",
    )
    require(
        dry_verification["status"] == "PASS_INDEPENDENT_DRY_RUN_VERIFICATION"
        and dry_verification["task_count"] == 184
        and dry_verification["transformer_steps"] == 9200,
        "independent dry-run verification mismatch",
    )

    test_count = run_cpu_tests()
    require(test_count == 17, f"unexpected CPU test count: {test_count}")
    require("torch" not in sys.modules, "verifier process imported torch after subprocess tests")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_PHASE_S_PROTOCOL_CORRECTION_VERIFICATION",
        "cpu_tests_passed": test_count,
        "representation_stages": 9,
        "deterministic_cross_seed_stages": 8,
        "sampled_image_latent_stages": 1,
        "four_seed_mean_without_second_normalization": True,
        "dry_run_tasks": 184,
        "dry_run_transformer_steps": 9200,
        "cumulative_attempt_ceiling": 186,
        "cumulative_transformer_step_ceiling": 9300,
        "torch_imported_by_verifier": False,
        "model_loaded": False,
        "gpu_compute_used": False,
        "run_001_partial_reused": False,
        "replacement_phase_s_authorization_exists": False,
        "phase_s_run_002_exists": False,
        "phase_s_gpu_execution_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise VerificationError(f"refusing to overwrite verifier artifact: {args.output}")
    result = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
