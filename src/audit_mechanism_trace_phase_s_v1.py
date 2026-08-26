#!/usr/bin/env python3
"""Outcome-blind post-run audit for mechanism trace scientific Phase S."""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from mechanism_trace_instrumentation_v1 import (
    INJECTION_COLUMNS,
    MARGIN_COLUMNS,
    ROUTE_COLUMNS,
    TASK_STATUS_COLUMNS,
)
from mechanism_trace_protocol_v1 import (
    ProtocolError,
    atomic_write_json,
    build_plan,
    read_json,
    sha256,
)
from verify_mechanism_trace_v1 import verify_execution


FORBIDDEN_SUFFIXES = {
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".pt", ".pth",
    ".ckpt", ".safetensors", ".npy", ".npz",
}
FALLBACK_MESSAGE = "fail to detect face using insightface, extract embedding on align face"
FATAL_MARKERS = (
    "BLOCKED:",
    "Traceback (most recent call last)",
    "CUDA out of memory",
    "OutOfMemoryError",
)


def read_csv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames or ()), list(reader)


def audit(run_dir: Path, authorization_path: Path, console_log: Path) -> dict:
    independent = verify_execution(run_dir, "scientific")
    _, plan = build_plan("scientific")
    expected_ids = [row["trace_task_id"] for row in plan]

    summary = read_json(run_dir / "execution_summary_v1.json")
    if summary["status"] != "TRACE_PHASE_COMPLETE_PENDING_INDEPENDENT_VERIFICATION":
        raise ProtocolError("execution summary status drift")
    if summary["authorization_sha256"] != sha256(authorization_path):
        raise ProtocolError("execution summary authorization hash mismatch")
    if summary["phase"] != "scientific":
        raise ProtocolError("execution summary phase mismatch")
    if summary["task_count"] != 160 or summary["transformer_steps"] != 8000:
        raise ProtocolError("execution summary budget count mismatch")
    if summary["phase_gpu_hours_ceiling"] != 24.0:
        raise ProtocolError("execution summary phase ceiling drift")
    if not 0.0 < float(summary["phase_elapsed_gpu_hours"]) <= 24.0:
        raise ProtocolError("Phase S elapsed time is outside the approved ceiling")
    if summary["raw_tensor_files_written"] or summary["decoded_media_files_written"]:
        raise ProtocolError("execution summary reports forbidden persistence")

    authorization = read_json(authorization_path)
    if authorization["status"] != "AUTHORIZED_FOR_MECHANISM_TRACE_EXECUTION":
        raise ProtocolError("execution authorization status drift")
    if authorization["phase"] != "scientific":
        raise ProtocolError("execution authorization phase drift")
    if not authorization["gpu_execution_explicitly_approved"]:
        raise ProtocolError("execution authorization did not record explicit GPU approval")
    if authorization["runtime_output_dir"] != str(run_dir):
        raise ProtocolError("execution authorization output directory drift")
    if authorization["trajectory_ceiling"] != 160:
        raise ProtocolError("execution authorization trajectory ceiling drift")
    if authorization["transformer_step_ceiling"] != 8000:
        raise ProtocolError("execution authorization Transformer-step ceiling drift")
    if authorization["cumulative_trajectory_ceiling"] != 219:
        raise ProtocolError("cumulative trajectory ceiling drift")
    if authorization["cumulative_transformer_step_ceiling"] != 10947:
        raise ProtocolError("cumulative Transformer-step ceiling drift")
    if authorization["total_gpu_hours_ceiling"] != 72:
        raise ProtocolError("total GPU-hour ceiling drift")
    if authorization["run_001_partial_reuse_authorized"]:
        raise ProtocolError("run-001 reuse was unexpectedly authorized")
    if authorization["run_002_partial_reuse_authorized"]:
        raise ProtocolError("run-002 reuse was unexpectedly authorized")

    partials = sorted(path.name for path in run_dir.glob("*.partial"))
    if partials:
        raise ProtocolError(f"unfinalized partial artifacts remain: {partials}")
    forbidden = [
        path for path in run_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES
    ]
    if forbidden:
        raise ProtocolError(f"forbidden raw tensor/media artifacts found: {forbidden[:3]}")

    events = [
        json.loads(line)
        for line in (run_dir / "execution_events_v1.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if len(events) != 320:
        raise ProtocolError(f"event count mismatch: {len(events)}")
    for index, expected in enumerate(plan):
        start, complete = events[index * 2 : index * 2 + 2]
        if start.get("event") != "TASK_START" or start.get("task") != expected:
            raise ProtocolError(f"task-start event order or metadata drift at index {index}")
        if complete.get("event") != "TASK_COMPLETE":
            raise ProtocolError(f"task-complete event missing at index {index}")
        if complete.get("trace_task_id") != expected["trace_task_id"]:
            raise ProtocolError(f"task-complete ID drift at index {index}")

    status_header, status_rows = read_csv(run_dir / "task_status_v1.csv")
    if status_header != TASK_STATUS_COLUMNS:
        raise ProtocolError("task-status column order drift")
    if [row["trace_task_id"] for row in status_rows] != expected_ids:
        raise ProtocolError("task-status execution order differs from frozen plan")
    durations = []
    for row in status_rows:
        started = datetime.fromisoformat(row["started_at_utc"])
        finished = datetime.fromisoformat(row["finished_at_utc"])
        duration = (finished - started).total_seconds()
        if not math.isfinite(duration) or duration <= 0:
            raise ProtocolError("non-positive task duration")
        durations.append(duration)

    route_header, route_rows = read_csv(run_dir / "route_summaries_v1.csv")
    if route_header != ROUTE_COLUMNS:
        raise ProtocolError("route-summary column order drift")
    if [row["trace_task_id"] for row in route_rows] != expected_ids:
        raise ProtocolError("route-summary execution order differs from frozen plan")

    margin_header, margin_rows = read_csv(run_dir / "representation_margins_v1.csv")
    if margin_header != MARGIN_COLUMNS:
        raise ProtocolError("representation-margin column order drift")
    if len(margin_rows) != 180:
        raise ProtocolError("representation-margin row count drift")

    scheduler_by_step: dict[int, set[int]] = defaultdict(set)
    task_rows: Counter[str] = Counter()
    task_transition_order: list[str] = []
    injection_path = run_dir / "injection_summaries_v1.csv"
    with injection_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != INJECTION_COLUMNS:
            raise ProtocolError("injection-summary column order drift")
        previous_task = None
        for row in reader:
            task_id = row["trace_task_id"]
            if task_id != previous_task:
                task_transition_order.append(task_id)
                previous_task = task_id
            scheduler_by_step[int(row["step_index"])].add(int(row["scheduler_timestep"]))
            task_rows[task_id] += 1
    if task_transition_order != expected_ids:
        raise ProtocolError("injection-summary task order differs from frozen plan")
    if set(scheduler_by_step) != set(range(50)):
        raise ProtocolError("scheduler position universe drift")
    if any(len(values) != 1 for values in scheduler_by_step.values()):
        raise ProtocolError("scheduler timestep differs across tasks/sites/CFG branches")
    if set(task_rows) != set(expected_ids) or set(task_rows.values()) != {2100}:
        raise ProtocolError("per-task injection rows drift in post-run audit")
    scheduler_sequence = [next(iter(scheduler_by_step[index])) for index in range(50)]

    if not console_log.is_file():
        raise ProtocolError("Phase S console log missing")
    console = console_log.read_text(encoding="utf-8", errors="replace")
    fatal_counts = {marker: console.count(marker) for marker in FATAL_MARKERS}
    if any(fatal_counts.values()):
        raise ProtocolError(f"fatal console marker present: {fatal_counts}")
    fallback_count = console.count(FALLBACK_MESSAGE)

    return {
        "schema_version": 1,
        "status": "PASS_OUTCOME_BLIND_PHASE_S_POST_RUN_AUDIT",
        "independent_runtime_verification": independent["status"],
        "tasks": 160,
        "transformer_steps": 8000,
        "injection_rows": sum(task_rows.values()),
        "route_rows": len(route_rows),
        "task_status_rows": len(status_rows),
        "representation_margin_rows": len(margin_rows),
        "event_rows": len(events),
        "event_sequence_exact": True,
        "task_execution_order_exact": True,
        "runtime_csv_column_orders_exact": True,
        "scheduler_positions": 50,
        "scheduler_timestep_sequence": scheduler_sequence,
        "scheduler_sequence_identical_across_tasks_sites_and_cfg": True,
        "minimum_task_seconds": min(durations),
        "maximum_task_seconds": max(durations),
        "mean_task_seconds": sum(durations) / len(durations),
        "phase_elapsed_gpu_hours": summary["phase_elapsed_gpu_hours"],
        "phase_gpu_hours_ceiling": summary["phase_gpu_hours_ceiling"],
        "cumulative_trajectory_ceiling": authorization["cumulative_trajectory_ceiling"],
        "cumulative_transformer_step_ceiling": authorization[
            "cumulative_transformer_step_ceiling"
        ],
        "unfinalized_partial_files": 0,
        "forbidden_raw_tensor_or_media_files": 0,
        "raw_tensor_files_written": 0,
        "decoded_media_files_written": 0,
        "console_fatal_markers": fatal_counts,
        "insightface_aligned_face_fallback_messages": fallback_count,
        "fallback_task_mapping_available": False,
        "fallback_mapping_limitation": (
            "The frozen console message has no timestamp or trace_task_id; incidence is auditable "
            "only as a run-level count and is not assigned to units post hoc."
        ),
        "outcome_blindness": {
            "scientific_effect_values_summarized": False,
            "scientific_results_interpreted": False,
            "only_structure_integrity_arithmetic_finiteness_and_console_state_checked": True
        },
        "run_001_or_run_002_partial_reuse": False,
        "post_run_gpu_compute_used": False,
        "post_run_model_loaded": False
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--console-log", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.run_dir, args.authorization_file, args.console_log)
    atomic_write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProtocolError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
