#!/usr/bin/env python3
"""Fail-closed entry point for ConsisID mechanism trace v1."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from mechanism_trace_protocol_v1 import (
    ProtocolError,
    atomic_write_csv,
    atomic_write_json,
    build_plan,
    validate_execution_authorization,
)


HERE = Path(__file__).resolve().parent
CODE_PATHS = [
    HERE / "mechanism_trace_protocol_v1.py",
    HERE / "mechanism_trace_instrumentation_v1.py",
    HERE / "run_mechanism_trace_v1.py",
    HERE / "verify_mechanism_trace_v1.py",
    HERE / "verify_mechanism_trace_engineering_controls_v1.py",
    HERE / "analyze_mechanism_trace_v1.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        required=True,
        choices=("dry-run", "execute-engineering", "execute-scientific"),
    )
    parser.add_argument("--phase", choices=("engineering", "scientific", "all"))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--authorization-file", type=Path)
    return parser.parse_args()


def dry_run(phase: str, output_dir: Path | None) -> int:
    summary, rows = build_plan(phase)
    if summary["torch_imported"] or summary["consisid_modules_imported"]:
        raise ProtocolError("dry-run unexpectedly imported a model runtime module")
    if output_dir is not None:
        atomic_write_csv(output_dir / "dry_run_task_manifest_v1.csv", rows)
        summary["task_manifest_path"] = str(output_dir / "dry_run_task_manifest_v1.csv")
        atomic_write_json(output_dir / "dry_run_summary_v1.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def execute(mode: str, output_dir: Path | None, authorization_file: Path | None) -> int:
    phase = "engineering" if mode == "execute-engineering" else "scientific"
    if output_dir is None:
        raise ProtocolError("execution requires --output-dir")
    if authorization_file is None:
        raise ProtocolError("execution requires --authorization-file before model imports")
    authorization = validate_execution_authorization(authorization_file, phase, CODE_PATHS)
    authorized_output = Path(authorization.get("runtime_output_dir", "")).resolve()
    if authorized_output != output_dir.resolve():
        raise ProtocolError("runtime output directory differs from execution authorization")
    cuda_visible_devices = str(authorization.get("cuda_visible_devices", ""))
    if not cuda_visible_devices.isdigit():
        raise ProtocolError("authorization must select exactly one numeric CUDA device")
    for variable in ("WORLD_SIZE", "LOCAL_WORLD_SIZE"):
        if os.environ.get(variable, "1") != "1":
            raise ProtocolError(f"distributed execution is forbidden: {variable}")
    os.environ["CUDA_VISIBLE_DEVICES"] = cuda_visible_devices

    # Import only after every prospective execution gate has passed.
    from mechanism_trace_instrumentation_v1 import execute_trace_phase

    return execute_trace_phase(phase, output_dir, authorization_file)


def main() -> int:
    args = parse_args()
    if args.mode == "dry-run":
        return dry_run(args.phase or "all", args.output_dir)
    if args.phase is not None:
        raise ProtocolError("--phase is only valid with --mode dry-run")
    return execute(args.mode, args.output_dir, args.authorization_file)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProtocolError as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
