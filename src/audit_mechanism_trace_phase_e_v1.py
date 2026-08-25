#!/usr/bin/env python3
"""Outcome-blind post-run audit for mechanism trace engineering phase E."""
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


def read_csv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames or ()), list(reader)


def audit(run_dir: Path, authorization_path: Path) -> dict:
    independent = verify_execution(run_dir, "engineering")
    _, plan = build_plan("engineering")
    expected_ids = [row["trace_task_id"] for row in plan]

    summary = read_json(run_dir / "execution_summary_v1.json")
    if summary["status"] != "TRACE_PHASE_COMPLETE_PENDING_INDEPENDENT_VERIFICATION":
        raise ProtocolError("execution summary status drift")
    if summary["authorization_sha256"] != sha256(authorization_path):
        raise ProtocolError("execution summary authorization hash mismatch")
    if summary["task_count"] != 24 or summary["transformer_steps"] != 1200:
        raise ProtocolError("execution summary budget count mismatch")
    if summary["raw_tensor_files_written"] or summary["decoded_media_files_written"]:
        raise ProtocolError("execution summary reports forbidden persistence")

    partials = sorted(path.name for path in run_dir.glob("*.partial"))
    if partials:
        raise ProtocolError(f"unfinalized partial artifacts remain: {partials}")
    if (run_dir / "representation_margins_v1.csv").exists():
        raise ProtocolError("engineering run emitted scientific representation margins")

    events = [json.loads(line) for line in (run_dir / "execution_events_v1.jsonl").read_text().splitlines()]
    if len(events) != 48:
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

    scheduler_by_step: dict[int, set[int]] = defaultdict(set)
    task_rows = Counter()
    injection_path = run_dir / "injection_summaries_v1.csv"
    with injection_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != INJECTION_COLUMNS:
            raise ProtocolError("injection-summary column order drift")
        for row in reader:
            scheduler_by_step[int(row["step_index"])].add(int(row["scheduler_timestep"]))
            task_rows[row["trace_task_id"]] += 1
    if set(scheduler_by_step) != set(range(50)):
        raise ProtocolError("scheduler position universe drift")
    if any(len(values) != 1 for values in scheduler_by_step.values()):
        raise ProtocolError("scheduler timestep differs across tasks/sites/CFG branches")
    if set(task_rows) != set(expected_ids) or set(task_rows.values()) != {2100}:
        raise ProtocolError("per-task injection rows drift in post-run audit")
    scheduler_sequence = [next(iter(scheduler_by_step[index])) for index in range(50)]

    return {
        "schema_version": 1,
        "status": "PASS_OUTCOME_BLIND_PHASE_E_POST_RUN_AUDIT",
        "independent_runtime_verification": independent["status"],
        "engineering_control_verification": independent["engineering_control"]["status"],
        "tasks": 24,
        "transformer_steps": 1200,
        "injection_rows": sum(task_rows.values()),
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
        "unfinalized_partial_files": 0,
        "scientific_representation_margin_files": 0,
        "raw_tensor_files_written": 0,
        "decoded_media_files_written": 0,
        "phase_s_execution_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.run_dir, args.authorization_file)
    atomic_write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProtocolError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
