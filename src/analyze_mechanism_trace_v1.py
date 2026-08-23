#!/usr/bin/env python3
"""Prespecified CPU-only aggregation for scientific mechanism trace v1."""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from mechanism_trace_protocol_v1 import ProtocolError, atomic_write_json, build_plan
from verify_mechanism_trace_v1 import read_csv_rows, verify_execution


TASK_CELL_COLUMNS = (
    "trace_task_id", "formal_unit_id", "formal_pair_id", "attribute", "role",
    "seed_index", "seed", "cfg_branch", "block_group", "denoising_group",
    "relative_residual_rms_mean", "positions",
)
PAIR_CELL_COLUMNS = (
    "attribute", "formal_pair_id", "cfg_branch", "block_group", "denoising_group",
    "positive_four_seed_mean", "control_four_seed_mean", "positive_minus_control",
)
PANEL_COLUMNS = (
    "attribute", "cfg_branch", "block_group", "denoising_group", "pairs",
    "positive_count", "zero_count", "negative_count", "mean", "median", "minimum", "maximum",
)
REPRESENTATION_COLUMNS = (
    "attribute", "stage", "readout_role", "pairs", "correct_count", "tie_count",
    "wrong_count", "mean_margin", "median_margin", "minimum_margin", "maximum_margin",
)
PRIMARY_STAGE = "valid_face_emb_mean_token_l2_normalized"


def block_group(site: int) -> str:
    if site <= 6:
        return "early"
    if site <= 13:
        return "middle"
    return "late"


def denoising_group(step: int) -> str:
    if step <= 16:
        return "early"
    if step <= 33:
        return "middle"
    return "late"


def atomic_csv(path: Path, columns: tuple[str, ...], rows: Iterable[dict]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise ProtocolError(f"refusing to overwrite analysis artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in columns})
    temporary.replace(path)


def finite_panel(values: list[float]) -> dict[str, float | int]:
    if len(values) != 10 or any(not math.isfinite(value) for value in values):
        raise ProtocolError("finite-panel summary requires ten finite matched-pair values")
    return {
        "pairs": 10,
        "positive_count": sum(value > 0 for value in values),
        "zero_count": sum(value == 0 for value in values),
        "negative_count": sum(value < 0 for value in values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def aggregate_injection(run_dir: Path) -> tuple[list[dict], list[dict], list[dict]]:
    _, plan = build_plan("scientific")
    plan_by_id = {row["trace_task_id"]: row for row in plan}
    sums: dict[tuple[str, str, str, str], float] = defaultdict(float)
    counts: dict[tuple[str, str, str, str], int] = defaultdict(int)
    for row in read_csv_rows(run_dir / "injection_summaries_v1.csv"):
        task_id = row["trace_task_id"]
        key = (
            task_id,
            row["cfg_branch"],
            block_group(int(row["site_index"])),
            denoising_group(int(row["step_index"])),
        )
        value = float(row["relative_residual_rms"])
        if not math.isfinite(value):
            raise ProtocolError(f"non-finite relative residual in {task_id}")
        sums[key] += value
        counts[key] += 1

    task_rows: list[dict] = []
    expected_per_cell = {
        (block, denoise): block_sites * denoise_steps
        for block, block_sites in (("early", 7), ("middle", 7), ("late", 7))
        for denoise, denoise_steps in (("early", 17), ("middle", 17), ("late", 16))
    }
    for key in sorted(sums):
        task_id, branch, block, denoise = key
        expected = expected_per_cell[(block, denoise)]
        if counts[key] != expected:
            raise ProtocolError(f"3x3 task-cell count mismatch: {key}/{counts[key]}")
        meta = plan_by_id[task_id]
        task_rows.append({
            **{name: meta[name] for name in (
                "trace_task_id", "formal_unit_id", "formal_pair_id", "attribute",
                "role", "seed_index", "seed",
            )},
            "cfg_branch": branch,
            "block_group": block,
            "denoising_group": denoise,
            "relative_residual_rms_mean": sums[key] / counts[key],
            "positions": counts[key],
        })
    if len(task_rows) != 160 * 2 * 9:
        raise ProtocolError(f"task 3x3 grid row count mismatch: {len(task_rows)}")

    unit_cells: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    unit_meta: dict[str, dict] = {}
    for row in task_rows:
        key = (
            row["formal_unit_id"], row["cfg_branch"],
            row["block_group"], row["denoising_group"],
        )
        unit_cells[key].append(float(row["relative_residual_rms_mean"]))
        unit_meta[row["formal_unit_id"]] = row
    unit_means = {}
    for key, values in unit_cells.items():
        if len(values) != 4:
            raise ProtocolError(f"four-seed unit cell count mismatch: {key}/{len(values)}")
        unit_means[key] = statistics.fmean(values)

    paired: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    for unit, meta in unit_meta.items():
        paired[(meta["attribute"], meta["formal_pair_id"])][meta["role"]] = unit
    if len(paired) != 20 or any(set(roles) != {"positive", "control"} for roles in paired.values()):
        raise ProtocolError("scientific matched-pair universe drift during aggregation")

    pair_rows: list[dict] = []
    panel_values: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for (attribute, pair_id), roles in sorted(paired.items()):
        for branch in ("unconditional", "text"):
            for block in ("early", "middle", "late"):
                for denoise in ("early", "middle", "late"):
                    positive = unit_means[(roles["positive"], branch, block, denoise)]
                    control = unit_means[(roles["control"], branch, block, denoise)]
                    difference = positive - control
                    pair_rows.append({
                        "attribute": attribute,
                        "formal_pair_id": pair_id,
                        "cfg_branch": branch,
                        "block_group": block,
                        "denoising_group": denoise,
                        "positive_four_seed_mean": positive,
                        "control_four_seed_mean": control,
                        "positive_minus_control": difference,
                    })
                    panel_values[(attribute, branch, block, denoise)].append(difference)
    if len(pair_rows) != 360:
        raise ProtocolError(f"paired 3x3 row count mismatch: {len(pair_rows)}")

    panel_rows = []
    for (attribute, branch, block, denoise), values in sorted(panel_values.items()):
        panel_rows.append({
            "attribute": attribute,
            "cfg_branch": branch,
            "block_group": block,
            "denoising_group": denoise,
            **finite_panel(values),
        })
    if len(panel_rows) != 36:
        raise ProtocolError(f"finite-panel 3x3 row count mismatch: {len(panel_rows)}")
    return task_rows, pair_rows, panel_rows


def aggregate_representations(run_dir: Path) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in read_csv_rows(run_dir / "representation_margins_v1.csv"):
        grouped[(row["attribute"], row["stage"])].append(row)
    rows = []
    for (attribute, stage), margins in sorted(grouped.items()):
        if len(margins) != 10 or len({row["formal_pair_id"] for row in margins}) != 10:
            raise ProtocolError(f"representation pair count mismatch: {attribute}/{stage}")
        values = [float(row["margin"]) for row in margins]
        directions = [row["direction"] for row in margins]
        rows.append({
            "attribute": attribute,
            "stage": stage,
            "readout_role": "primary" if stage == PRIMARY_STAGE else "secondary_diagnostic",
            "pairs": 10,
            "correct_count": directions.count("correct"),
            "tie_count": directions.count("tie"),
            "wrong_count": directions.count("wrong"),
            "mean_margin": statistics.fmean(values),
            "median_margin": statistics.median(values),
            "minimum_margin": min(values),
            "maximum_margin": max(values),
        })
    if len(rows) != 18:
        raise ProtocolError(f"representation finite-panel row count mismatch: {len(rows)}")
    return rows


def analyze(run_dir: Path, output_dir: Path) -> dict:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ProtocolError(f"analysis output directory is not empty: {output_dir}")
    verification = verify_execution(run_dir, "scientific")
    task_rows, pair_rows, panel_rows = aggregate_injection(run_dir)
    representation_rows = aggregate_representations(run_dir)
    atomic_csv(output_dir / "injection_task_3x3_v1.csv", TASK_CELL_COLUMNS, task_rows)
    atomic_csv(output_dir / "injection_pair_3x3_v1.csv", PAIR_CELL_COLUMNS, pair_rows)
    atomic_csv(output_dir / "injection_finite_panel_3x3_v1.csv", PANEL_COLUMNS, panel_rows)
    atomic_csv(
        output_dir / "representation_finite_panel_v1.csv",
        REPRESENTATION_COLUMNS,
        representation_rows,
    )
    summary = {
        "schema_version": 1,
        "status": "COMPLETE_PRESPECIFIED_FINITE_PANEL_DESCRIPTIONS_ONLY",
        "runtime_verification": verification["status"],
        "task_3x3_rows": len(task_rows),
        "pair_3x3_rows": len(pair_rows),
        "finite_panel_3x3_rows": len(panel_rows),
        "representation_finite_panel_rows": len(representation_rows),
        "inferential_tests": False,
        "confidence_intervals": False,
        "cross_attribute_ranking": False,
        "claim_boundary": (
            "Fixed-panel descriptive evidence only; no causal, population, model-wide, "
            "frame-independent, or cross-attribute conclusion."
        ),
    }
    atomic_write_json(output_dir / "analysis_summary_v1.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = analyze(args.run_dir, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProtocolError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
