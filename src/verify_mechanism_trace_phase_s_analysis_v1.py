#!/usr/bin/env python3
"""Independently verify prespecified Phase-S finite-panel analysis artifacts."""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from analyze_mechanism_trace_v1 import (
    PANEL_COLUMNS,
    PAIR_CELL_COLUMNS,
    PRIMARY_STAGE,
    REPRESENTATION_COLUMNS,
    TASK_CELL_COLUMNS,
)
from mechanism_trace_protocol_v1 import ProtocolError, atomic_write_json, build_plan, read_json
from verify_mechanism_trace_v1 import verify_execution


BRANCHES = ("unconditional", "text")
BLOCKS = ("early", "middle", "late")
DENOISING = ("early", "middle", "late")
POSITIONS = {
    (block, denoise): block_sites * denoise_steps
    for block, block_sites in (("early", 7), ("middle", 7), ("late", 7))
    for denoise, denoise_steps in (("early", 17), ("middle", 17), ("late", 16))
}


def read_csv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames or ()), list(reader)


def finite(value: str, context: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ProtocolError(f"non-finite analysis value: {context}")
    return result


def close(left: float, right: float, context: str) -> None:
    if not math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12):
        raise ProtocolError(f"analysis arithmetic mismatch: {context}/{left}/{right}")


def verify(run_dir: Path, analysis_dir: Path) -> dict:
    runtime = verify_execution(run_dir, "scientific")
    _, plan = build_plan("scientific")
    plan_by_id = {row["trace_task_id"]: row for row in plan}

    task_header, task_rows = read_csv(analysis_dir / "injection_task_3x3_v1.csv")
    if task_header != TASK_CELL_COLUMNS:
        raise ProtocolError("task 3x3 column order drift")
    if len(task_rows) != 2880:
        raise ProtocolError(f"task 3x3 row count mismatch: {len(task_rows)}")
    task_keys = set()
    unit_cells: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    unit_meta: dict[str, dict[str, str]] = {}
    for row in task_rows:
        task_id = row["trace_task_id"]
        if task_id not in plan_by_id:
            raise ProtocolError(f"unknown analysis task: {task_id}")
        expected = plan_by_id[task_id]
        for field in (
            "formal_unit_id", "formal_pair_id", "attribute", "role", "seed_index", "seed"
        ):
            if row[field] != expected[field]:
                raise ProtocolError(f"task analysis metadata drift: {task_id}/{field}")
        branch = row["cfg_branch"]
        block = row["block_group"]
        denoise = row["denoising_group"]
        if branch not in BRANCHES or block not in BLOCKS or denoise not in DENOISING:
            raise ProtocolError("task analysis grid label drift")
        if int(row["positions"]) != POSITIONS[(block, denoise)]:
            raise ProtocolError("task analysis position count drift")
        key = (task_id, branch, block, denoise)
        if key in task_keys:
            raise ProtocolError(f"duplicate task analysis cell: {key}")
        task_keys.add(key)
        value = finite(row["relative_residual_rms_mean"], str(key))
        unit_key = (row["formal_unit_id"], branch, block, denoise)
        unit_cells[unit_key].append(value)
        unit_meta[row["formal_unit_id"]] = row
    if len(task_keys) != 160 * 2 * 9:
        raise ProtocolError("task analysis grid is incomplete")

    unit_means: dict[tuple[str, str, str, str], float] = {}
    for key, values in unit_cells.items():
        if len(values) != 4:
            raise ProtocolError(f"unit cell does not contain four seeds: {key}")
        unit_means[key] = statistics.fmean(values)

    paired: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    for unit, meta in unit_meta.items():
        paired[(meta["attribute"], meta["formal_pair_id"])][meta["role"]] = unit
    if len(paired) != 20 or any(set(roles) != {"positive", "control"} for roles in paired.values()):
        raise ProtocolError("matched-pair universe drift in analysis verification")

    pair_header, pair_rows = read_csv(analysis_dir / "injection_pair_3x3_v1.csv")
    if pair_header != PAIR_CELL_COLUMNS:
        raise ProtocolError("pair 3x3 column order drift")
    if len(pair_rows) != 360:
        raise ProtocolError(f"pair 3x3 row count mismatch: {len(pair_rows)}")
    pair_keys = set()
    panel_values: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in pair_rows:
        pair_key = (row["attribute"], row["formal_pair_id"])
        if pair_key not in paired:
            raise ProtocolError(f"unknown matched pair in analysis: {pair_key}")
        branch, block, denoise = row["cfg_branch"], row["block_group"], row["denoising_group"]
        key = (*pair_key, branch, block, denoise)
        if key in pair_keys:
            raise ProtocolError(f"duplicate pair analysis cell: {key}")
        pair_keys.add(key)
        roles = paired[pair_key]
        expected_positive = unit_means[(roles["positive"], branch, block, denoise)]
        expected_control = unit_means[(roles["control"], branch, block, denoise)]
        expected_difference = expected_positive - expected_control
        observed_positive = finite(row["positive_four_seed_mean"], f"{key}/positive")
        observed_control = finite(row["control_four_seed_mean"], f"{key}/control")
        observed_difference = finite(row["positive_minus_control"], f"{key}/difference")
        close(observed_positive, expected_positive, f"{key}/positive")
        close(observed_control, expected_control, f"{key}/control")
        close(observed_difference, expected_difference, f"{key}/difference")
        panel_values[(row["attribute"], branch, block, denoise)].append(observed_difference)
    if len(pair_keys) != 20 * 2 * 9:
        raise ProtocolError("pair analysis grid is incomplete")

    panel_header, panel_rows = read_csv(analysis_dir / "injection_finite_panel_3x3_v1.csv")
    if panel_header != PANEL_COLUMNS:
        raise ProtocolError("finite-panel 3x3 column order drift")
    if len(panel_rows) != 36:
        raise ProtocolError(f"finite-panel 3x3 row count mismatch: {len(panel_rows)}")
    panel_keys = set()
    for row in panel_rows:
        key = (row["attribute"], row["cfg_branch"], row["block_group"], row["denoising_group"])
        if key in panel_keys or key not in panel_values:
            raise ProtocolError(f"finite-panel key drift: {key}")
        panel_keys.add(key)
        values = panel_values[key]
        if len(values) != 10 or int(row["pairs"]) != 10:
            raise ProtocolError(f"finite-panel pair count drift: {key}")
        expected_counts = (
            sum(value > 0 for value in values),
            sum(value == 0 for value in values),
            sum(value < 0 for value in values),
        )
        observed_counts = (
            int(row["positive_count"]), int(row["zero_count"]), int(row["negative_count"])
        )
        if observed_counts != expected_counts:
            raise ProtocolError(f"finite-panel sign-count mismatch: {key}")
        for field, expected in (
            ("mean", statistics.fmean(values)),
            ("median", statistics.median(values)),
            ("minimum", min(values)),
            ("maximum", max(values)),
        ):
            close(finite(row[field], f"{key}/{field}"), expected, f"{key}/{field}")
    if set(panel_values) != panel_keys:
        raise ProtocolError("finite-panel grid is incomplete")

    raw_margin_header, raw_margins = read_csv(run_dir / "representation_margins_v1.csv")
    if raw_margin_header != ("attribute", "stage", "formal_pair_id", "margin", "direction"):
        raise ProtocolError("raw representation-margin header drift")
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in raw_margins:
        grouped[(row["attribute"], row["stage"])].append(row)

    representation_header, representation_rows = read_csv(
        analysis_dir / "representation_finite_panel_v1.csv"
    )
    if representation_header != REPRESENTATION_COLUMNS:
        raise ProtocolError("representation finite-panel column order drift")
    if len(representation_rows) != 18:
        raise ProtocolError("representation finite-panel row count drift")
    seen_representation = set()
    for row in representation_rows:
        key = (row["attribute"], row["stage"])
        if key in seen_representation or key not in grouped:
            raise ProtocolError(f"representation summary key drift: {key}")
        seen_representation.add(key)
        margins = grouped[key]
        if len(margins) != 10 or int(row["pairs"]) != 10:
            raise ProtocolError(f"representation pair count drift: {key}")
        expected_role = "primary" if row["stage"] == PRIMARY_STAGE else "secondary_diagnostic"
        if row["readout_role"] != expected_role:
            raise ProtocolError(f"representation role drift: {key}")
        values = [finite(item["margin"], f"{key}/margin") for item in margins]
        directions = [item["direction"] for item in margins]
        if (
            int(row["correct_count"]), int(row["tie_count"]), int(row["wrong_count"])
        ) != (directions.count("correct"), directions.count("tie"), directions.count("wrong")):
            raise ProtocolError(f"representation direction-count mismatch: {key}")
        for field, expected in (
            ("mean_margin", statistics.fmean(values)),
            ("median_margin", statistics.median(values)),
            ("minimum_margin", min(values)),
            ("maximum_margin", max(values)),
        ):
            close(finite(row[field], f"{key}/{field}"), expected, f"{key}/{field}")
    if set(grouped) != seen_representation:
        raise ProtocolError("representation finite-panel summaries are incomplete")

    summary = read_json(analysis_dir / "analysis_summary_v1.json")
    expected_summary = {
        "status": "COMPLETE_PRESPECIFIED_FINITE_PANEL_DESCRIPTIONS_ONLY",
        "runtime_verification": "PASS_INDEPENDENT_MECHANISM_TRACE_VERIFICATION",
        "task_3x3_rows": 2880,
        "pair_3x3_rows": 360,
        "finite_panel_3x3_rows": 36,
        "representation_finite_panel_rows": 18,
        "inferential_tests": False,
        "confidence_intervals": False,
        "cross_attribute_ranking": False,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise ProtocolError(f"analysis summary drift: {key}")

    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_PHASE_S_PRESPECIFIED_ANALYSIS_VERIFICATION",
        "runtime_verification": runtime["status"],
        "task_3x3_rows": len(task_rows),
        "pair_3x3_rows": len(pair_rows),
        "finite_panel_3x3_rows": len(panel_rows),
        "representation_finite_panel_rows": len(representation_rows),
        "task_to_unit_four_seed_aggregation_verified": True,
        "unit_to_matched_pair_difference_verified": True,
        "ten_pair_finite_panel_statistics_verified": True,
        "representation_margin_aggregation_verified": True,
        "inferential_tests": False,
        "confidence_intervals": False,
        "cross_attribute_ranking": False,
        "model_loaded": False,
        "gpu_compute_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--analysis-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.run_dir, args.analysis_dir)
    atomic_write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProtocolError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
