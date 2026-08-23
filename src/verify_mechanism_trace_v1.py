#!/usr/bin/env python3
"""Independent stdlib verifier for mechanism trace v1 artifacts."""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

from mechanism_trace_protocol_v1 import (
    DRY_RUN_COLUMNS,
    ProtocolError,
    build_plan,
    canonical_json_sha256,
    read_json,
)
from verify_mechanism_trace_engineering_controls_v1 import verify_engineering_controls


FORBIDDEN_SUFFIXES = {
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".pt", ".pth", ".ckpt",
    ".safetensors", ".npy", ".npz",
}


def read_csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def verify_dry_run(run_dir: Path) -> dict:
    summary_path = run_dir / "dry_run_summary_v1.json"
    manifest_path = run_dir / "dry_run_task_manifest_v1.csv"
    if not summary_path.is_file() or not manifest_path.is_file():
        raise ProtocolError("dry-run summary or task manifest missing")
    summary = read_json(summary_path)
    phase = summary["phase"]
    expected_summary, expected_rows = build_plan(phase)
    rows = list(read_csv_rows(manifest_path))
    if not rows or tuple(rows[0]) != DRY_RUN_COLUMNS:
        raise ProtocolError("dry-run manifest columns are missing or drifted")
    expected_public = [{key: row[key] for key in DRY_RUN_COLUMNS} for row in expected_rows]
    if rows != expected_public:
        raise ProtocolError("dry-run task enumeration differs from frozen planner")
    if summary["task_count"] != len(rows):
        raise ProtocolError("dry-run task count mismatch")
    if summary["task_manifest_canonical_sha256"] != canonical_json_sha256(rows):
        raise ProtocolError("dry-run canonical task-manifest hash mismatch")
    for key in (
        "transformer_steps", "scheduler_positions_per_task", "local_injection_sites",
        "counts", "formal_master_sha256", "formal_generation_manifest_sha256",
        "design_freeze_sha256",
    ):
        if summary[key] != expected_summary[key]:
            raise ProtocolError(f"dry-run summary mismatch: {key}")
    if summary.get("torch_imported") or summary.get("consisid_modules_imported"):
        raise ProtocolError("dry-run reports an ML runtime import")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_DRY_RUN_VERIFICATION",
        "phase": phase,
        "task_count": len(rows),
        "transformer_steps": len(rows) * 50,
        "torch_imported": False,
        "consisid_modules_imported": False,
    }


def verify_no_forbidden_files(run_dir: Path) -> None:
    forbidden = [
        path for path in run_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES
    ]
    if forbidden:
        raise ProtocolError(f"forbidden raw tensor/media artifacts found: {forbidden[:3]}")


def _finite(row: dict[str, str], fields: tuple[str, ...]) -> list[float]:
    values = [float(row[field]) for field in fields]
    if any(not math.isfinite(value) for value in values):
        raise ProtocolError(f"non-finite numeric summary in task {row.get('trace_task_id')}")
    return values


def verify_execution(run_dir: Path, phase: str) -> dict:
    verify_no_forbidden_files(run_dir)
    expected_tasks = 24 if phase == "engineering" else 160
    _, expected_plan = build_plan(phase)
    expected_by_id = {row["trace_task_id"]: row for row in expected_plan}
    status_rows = list(read_csv_rows(run_dir / "task_status_v1.csv"))
    if len(status_rows) != expected_tasks:
        raise ProtocolError(f"task-status count mismatch: {len(status_rows)}")
    if any(row["phase"] != phase for row in status_rows):
        raise ProtocolError("task-status phase mismatch")
    if any(row["status"] != "COMPLETE_BOUNDED_SUMMARIES_ONLY" for row in status_rows):
        raise ProtocolError("execution contains a non-complete task")
    if any(row.get("reference_vectors_verified_in_memory") != "True" for row in status_rows):
        raise ProtocolError("reference-vector invariance was not verified in memory")
    task_ids = {row["trace_task_id"] for row in status_rows}
    if task_ids != set(expected_by_id):
        raise ProtocolError("task-status universe differs from frozen planner")
    for row in status_rows:
        expected_row = expected_by_id[row["trace_task_id"]]
        for field in ("phase", "formal_unit_id", "seed", "condition"):
            if row[field] != expected_row[field]:
                raise ProtocolError(f"task-status metadata drift: {row['trace_task_id']}/{field}")
    if len(task_ids) != expected_tasks:
        raise ProtocolError("task-status IDs are not unique")
    if any(int(row["injection_rows"]) != 2100 for row in status_rows):
        raise ProtocolError("per-task injection-row count mismatch")

    summary_fields = (
        "rms_h", "rms_r", "rms_post", "relative_residual_rms",
        "mean_tokenwise_cosine_h_r", "token_rms_r_q10", "token_rms_r_q50",
        "token_rms_r_q90",
    )
    injection_counts = Counter()
    injection_keys = Counter()
    injection_rows = 0
    for row in read_csv_rows(run_dir / "injection_summaries_v1.csv"):
        injection_rows += 1
        task_id = row["trace_task_id"]
        if task_id not in task_ids or row["phase"] != phase:
            raise ProtocolError(f"unknown or wrong-phase injection task ID: {task_id}")
        step = int(row["step_index"])
        site = int(row["site_index"])
        branch = row["cfg_branch"]
        if step not in range(50) or site not in range(21) or branch not in {"unconditional", "text"}:
            raise ProtocolError("injection index or CFG branch drift")
        if int(row["block_index"]) != site * 2:
            raise ProtocolError("injection block mapping drift")
        values = _finite(row, summary_fields)
        rms_h, rms_r, rms_post, relative = values[:4]
        local_face_scale = float(row["local_face_scale"])
        expected_scale = 0.0 if row["condition"] == "zero_local_residual" else 1.0
        if local_face_scale != expected_scale:
            raise ProtocolError("local_face_scale differs from frozen condition")
        expected_relative = rms_r / max(rms_h, 1e-12)
        if not math.isclose(relative, expected_relative, rel_tol=1e-6, abs_tol=1e-8):
            raise ProtocolError("relative_residual_rms arithmetic mismatch")
        if rms_h < 0 or rms_r < 0 or rms_post < 0:
            raise ProtocolError("negative RMS summary")
        frame_fields = tuple(f"frame_rms_r_{index:02d}" for index in range(13))
        frame_values = _finite(row, frame_fields)
        if any(value < 0 for value in frame_values):
            raise ProtocolError("negative per-frame RMS summary")
        injection_counts[task_id] += 1
        injection_keys[(task_id, step, site, branch)] += 1
    if len(injection_keys) != expected_tasks * 2100 or set(injection_keys.values()) != {1}:
        raise ProtocolError("injection position keys are duplicated or missing")
    if injection_rows != expected_tasks * 2100 or set(injection_counts.values()) != {2100}:
        raise ProtocolError("global injection-row structure mismatch")

    route_rows = list(read_csv_rows(run_dir / "route_summaries_v1.csv"))
    if len(route_rows) != expected_tasks:
        raise ProtocolError("route-summary count mismatch")
    if {row["trace_task_id"] for row in route_rows} != task_ids:
        raise ProtocolError("route-summary task universe mismatch")
    for row in route_rows:
        values = _finite(
            row,
            ("image_latents_overall_rms", "image_latents_first_frame_rms",
             "image_latents_padding_max_abs"),
        )
        if any(value < 0 for value in values):
            raise ProtocolError("negative image-latent route summary")
        if values[2] != 0.0:
            raise ProtocolError("reference image latent zero-padding is not exactly zero")

    engineering_control = None
    margin_count = 0
    if phase == "engineering":
        engineering_control = verify_engineering_controls(
            run_dir / "injection_summaries_v1.csv",
            run_dir / "route_summaries_v1.csv",
            status_rows,
        )
        if (run_dir / "representation_margins_v1.csv").exists():
            raise ProtocolError("engineering phase must not emit scientific margins")
    else:
        margin_rows = list(read_csv_rows(run_dir / "representation_margins_v1.csv"))
        margin_count = len(margin_rows)
        if margin_count != 180:
            raise ProtocolError(f"representation-margin count mismatch: {margin_count}")
        expected_stages = {
            "insightface_l2_normalized",
            "eva_head_l2_normalized",
            "eva_hidden_0_patch_mean_l2_normalized",
            "eva_hidden_1_patch_mean_l2_normalized",
            "eva_hidden_2_patch_mean_l2_normalized",
            "eva_hidden_3_patch_mean_l2_normalized",
            "eva_hidden_4_patch_mean_l2_normalized",
            "valid_face_emb_mean_token_l2_normalized",
            "image_latent_first_frame_spatial_mean_l2_normalized",
        }
        if {row["stage"] for row in margin_rows} != expected_stages:
            raise ProtocolError("representation stage universe mismatch")
        margin_keys = {(row["attribute"], row["stage"], row["formal_pair_id"]) for row in margin_rows}
        if len(margin_keys) != 180:
            raise ProtocolError("representation margin keys are duplicated or missing")
        expected_pairs = {(row["attribute"], row["formal_pair_id"]) for row in expected_plan}
        if {(row["attribute"], row["formal_pair_id"]) for row in margin_rows} != expected_pairs:
            raise ProtocolError("representation matched-pair universe mismatch")
        for row in margin_rows:
            margin = float(row["margin"])
            expected_direction = "tie" if abs(margin) <= 1e-8 else ("correct" if margin > 0 else "wrong")
            if row["direction"] != expected_direction:
                raise ProtocolError("representation direction label disagrees with frozen tie rule")
        if Counter(row["direction"] for row in margin_rows).keys() - {"correct", "tie", "wrong"}:
            raise ProtocolError("invalid representation direction label")
        if any(not math.isfinite(float(row["margin"])) for row in margin_rows):
            raise ProtocolError("non-finite representation margin")

    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_MECHANISM_TRACE_VERIFICATION",
        "phase": phase,
        "tasks": expected_tasks,
        "injection_rows": injection_rows,
        "route_rows": len(route_rows),
        "representation_margin_rows": margin_count,
        "forbidden_raw_tensor_or_media_files": 0,
        "engineering_control": engineering_control,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("dry-run", "execution"))
    parser.add_argument("--phase", required=True, choices=("engineering", "scientific", "all"))
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "dry-run":
        result = verify_dry_run(args.run_dir)
    else:
        if args.phase == "all":
            raise ProtocolError("execution verification requires one phase")
        result = verify_execution(args.run_dir, args.phase)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        if args.output.exists():
            raise ProtocolError(f"refusing to overwrite verifier artifact: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProtocolError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
