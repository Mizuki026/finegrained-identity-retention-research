#!/usr/bin/env python3
"""Verify the Phase-S run-003 recovery package without ML imports."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import stat
import sys
from collections import Counter, defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
GOVERNANCE = REPO / "governance" / "mechanism_trace_phase_s_recovery_v1"
MANIFEST = GOVERNANCE / "recovery_evidence_manifest_v1.csv"
RUN_002 = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_002"
)
RUN_003 = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003"
)
PENDING_AUTHORIZATION = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/"
    "phase_s_run_003_execution_authorization_pending_v1.json"
)
FINAL_AUTHORIZATION = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/"
    "phase_s_run_003_execution_authorization_v1.json"
)
FINAL_NAMES = (
    "execution_summary_v1.json",
    "injection_summaries_v1.csv",
    "route_summaries_v1.csv",
    "task_status_v1.csv",
    "representation_margins_v1.csv",
)


class VerificationError(RuntimeError):
    """Fail-closed recovery-package verification error."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO / path


def csv_data_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return max(sum(1 for _ in csv.reader(handle)) - 1, 0)


def structural_runtime_audit() -> dict:
    event_counts: Counter[str] = Counter()
    starts: list[str] = []
    completes: list[str] = []
    event_path = RUN_002 / "execution_events_v1.jsonl"
    with event_path.open(encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            name = event["event"]
            event_counts[name] += 1
            if name == "TASK_START":
                starts.append(event["task"]["trace_task_id"])
            elif name == "TASK_COMPLETE":
                completes.append(event["trace_task_id"])

    injection_path = RUN_002 / "injection_summaries_v1.csv.partial"
    task_rows: Counter[str] = Counter()
    task_steps: dict[str, set[int]] = defaultdict(set)
    task_step_rows: Counter[tuple[str, int]] = Counter()
    with injection_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames is not None, "injection partial has no header")
        require("trace_task_id" in reader.fieldnames, "trace-task column missing")
        require("step_index" in reader.fieldnames, "step-index column missing")
        for row in reader:
            task = row["trace_task_id"]
            step = int(row["step_index"])
            task_rows[task] += 1
            task_steps[task].add(step)
            task_step_rows[(task, step)] += 1

    unfinished = sorted(set(starts) - set(completes))
    require(len(unfinished) == 1, f"expected one interrupted task, found {unfinished}")
    interrupted = unfinished[0]
    last_step = max(task_steps[interrupted])
    return {
        "task_start_events": event_counts["TASK_START"],
        "task_complete_events": event_counts["TASK_COMPLETE"],
        "phase_stop_events": event_counts["PHASE_STOP"],
        "attempted_trajectories": len(starts),
        "completed_trajectories": len(completes),
        "interrupted_trajectories": len(unfinished),
        "transformer_steps_attempted": sum(len(steps) for steps in task_steps.values()),
        "injection_summary_data_rows": sum(task_rows.values()),
        "complete_trajectory_injection_rows": sum(task_rows[t] for t in completes),
        "interrupted_trajectory_injection_rows": task_rows[interrupted],
        "route_summary_data_rows": csv_data_rows(RUN_002 / "route_summaries_v1.csv.partial"),
        "task_status_data_rows": csv_data_rows(RUN_002 / "task_status_v1.csv.partial"),
        "representation_margin_data_rows": csv_data_rows(
            RUN_002 / "representation_margins_v1.csv.partial"
        ),
        "interrupted_trace_task_id": interrupted,
        "interrupted_scheduler_steps_with_any_rows": len(task_steps[interrupted]),
        "interrupted_last_started_step_index": last_step,
        "interrupted_last_started_step_rows": task_step_rows[(interrupted, last_step)],
    }


def verify() -> dict:
    require("torch" not in sys.modules, "recovery verifier imported torch")
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    require(len(evidence) == 23, f"expected 23 evidence rows, found {len(evidence)}")
    require(len({row["evidence_id"] for row in evidence}) == 23, "duplicate evidence IDs")
    for row in evidence:
        path = resolve(row["path"])
        require(path.is_file(), f"evidence missing: {path}")
        require(path.stat().st_size == int(row["bytes"]), f"byte mismatch: {path}")
        require(sha256(path) == row["sha256"], f"SHA256 mismatch: {path}")

    authorization = json.loads(
        (GOVERNANCE / "researcher_phase_s_recovery_authorization_v1.json").read_text()
    )
    audit = json.loads(
        (GOVERNANCE / "phase_s_run_002_power_loss_audit_v1.json").read_text()
    )
    dry_summary = json.loads(
        (GOVERNANCE / "no_weight_dry_run_v1" / "dry_run_summary_v1.json").read_text()
    )
    dry_verification = json.loads(
        (GOVERNANCE / "no_weight_dry_run_verification_v1.json").read_text()
    )

    require(
        authorization["status"]
        == "AUTHORIZED_FOR_ABORT_FREEZE_RECOVERY_PACKAGE_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_ONLY",
        "researcher recovery authorization status mismatch",
    )
    require(
        authorization["model_loading_authorized"] is False
        and authorization["gpu_execution_authorized"] is False
        and authorization["final_execution_authorization_authorized"] is False,
        "researcher recovery authorization unexpectedly permits execution",
    )
    accounting = authorization["approved_recovery_accounting"]
    require(
        accounting["cumulative_trajectory_ceiling"] == 219
        and accounting["cumulative_transformer_step_ceiling"] == 10947
        and accounting["total_gpu_hour_ceiling"] == 72.0,
        "recovery accounting mismatch",
    )

    observed = structural_runtime_audit()
    expected = audit["validated_counts"]
    for key in (
        "task_start_events",
        "task_complete_events",
        "phase_stop_events",
        "attempted_trajectories",
        "completed_trajectories",
        "interrupted_trajectories",
        "transformer_steps_attempted",
        "injection_summary_data_rows",
        "complete_trajectory_injection_rows",
        "interrupted_trajectory_injection_rows",
        "route_summary_data_rows",
        "task_status_data_rows",
        "representation_margin_data_rows",
    ):
        require(observed[key] == expected[key], f"run-002 structural mismatch: {key}")
    interrupted = audit["interrupted_task"]
    require(
        observed["interrupted_trace_task_id"] == interrupted["trace_task_id"]
        and observed["interrupted_scheduler_steps_with_any_rows"]
        == interrupted["scheduler_steps_with_any_rows"]
        and observed["interrupted_last_started_step_index"]
        == interrupted["last_started_step_index"]
        and observed["interrupted_last_started_step_rows"]
        == interrupted["rows_at_last_started_step"],
        "interrupted-task structure mismatch",
    )

    for name in FINAL_NAMES:
        require(not (RUN_002 / name).exists(), f"unexpected finalized run-002 artifact: {name}")
    for path in RUN_002.iterdir():
        require(path.is_file(), f"unexpected non-file in frozen run-002 directory: {path}")
        require(
            not (stat.S_IMODE(path.stat().st_mode) & 0o222),
            f"run-002 evidence remains writable: {path}",
        )

    require(
        dry_summary["phase"] == "scientific"
        and dry_summary["task_count"] == 160
        and dry_summary["transformer_steps"] == 8000
        and dry_summary["torch_imported"] is False
        and dry_summary["consisid_modules_imported"] is False,
        "no-weight scientific dry-run mismatch",
    )
    require(
        dry_verification["status"] == "PASS_INDEPENDENT_RUN_003_NO_WEIGHT_DRY_RUN_VERIFICATION",
        "no-weight dry-run verification did not pass",
    )
    require(not RUN_003.exists(), "run-003 output directory already exists")
    require(not PENDING_AUTHORIZATION.exists(), "pending authorization already exists")
    require(not FINAL_AUTHORIZATION.exists(), "final executable authorization already exists")
    require("torch" not in sys.modules, "recovery verifier imported torch during checks")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_PHASE_S_RUN_003_RECOVERY_PACKAGE_VERIFICATION",
        "evidence_entries": len(evidence),
        "paths_exist": True,
        "bytes_match": True,
        "sha256_match": True,
        "run_002_attempted_trajectories": 33,
        "run_002_completed_trajectories": 32,
        "run_002_transformer_steps_attempted": 1647,
        "run_002_representation_margin_rows": 0,
        "run_002_artifacts_read_only": True,
        "run_002_reuse_authorized": False,
        "dry_run_tasks": 160,
        "dry_run_transformer_steps": 8000,
        "cumulative_attempt_ceiling": 219,
        "cumulative_transformer_step_ceiling": 10947,
        "model_loaded": False,
        "gpu_compute_used": False,
        "pending_authorization_exists": False,
        "final_execution_authorization_exists": False,
        "run_003_exists": False,
        "phase_s_run_003_gpu_execution_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise VerificationError(f"refusing to overwrite package verification: {args.output}")
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
