#!/usr/bin/env python3
"""Independent engineering-control checks for mechanism trace v1."""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

from mechanism_trace_protocol_v1 import ProtocolError


NUMERIC_SUMMARY_FIELDS = (
    "rms_h",
    "rms_r",
    "rms_post",
    "relative_residual_rms",
    "mean_tokenwise_cosine_h_r",
    "token_rms_r_q10",
    "token_rms_r_q50",
    "token_rms_r_q90",
) + tuple(f"frame_rms_r_{index:02d}" for index in range(13))
ROUTE_FIELDS = (
    "image_latents_overall_rms",
    "image_latents_first_frame_rms",
    "image_latents_padding_max_abs",
)


def _rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def _within(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-6 + 1e-5 * max(abs(a), abs(b))


def verify_engineering_controls(
    injection_path: Path,
    route_path: Path,
    status_rows: list[dict[str, str]],
) -> dict:
    if len(status_rows) != 24:
        raise ProtocolError("engineering status universe is not 24 trajectories")
    if any(row.get("reference_vectors_verified_in_memory") != "True" for row in status_rows):
        raise ProtocolError("reference-vector in-memory invariance was not verified")

    baseline: dict[tuple[str, str, str, str], dict[str, dict[str, str]]] = defaultdict(dict)
    zero_rows = 0
    zero_keys: set[tuple[str, str, str, str]] = set()
    for row in _rows(injection_path):
        condition = row["condition"]
        scale = float(row["local_face_scale"])
        if condition == "baseline":
            if scale != 1.0:
                raise ProtocolError("baseline local_face_scale is not 1.0")
            key = (
                row["formal_unit_id"], row["step_index"], row["site_index"], row["cfg_branch"]
            )
            repetition = row["repetition"]
            if repetition in baseline[key]:
                raise ProtocolError(f"duplicate engineering baseline key: {key}/{repetition}")
            baseline[key][repetition] = row
        elif condition == "zero_local_residual":
            zero_rows += 1
            zero_key = (row["formal_unit_id"], row["step_index"], row["site_index"], row["cfg_branch"])
            if zero_key in zero_keys:
                raise ProtocolError(f"duplicate engineering zero-control key: {zero_key}")
            zero_keys.add(zero_key)
            if scale != 0.0:
                raise ProtocolError("zero-control local_face_scale is not 0.0")
            if not _within(float(row["rms_post"]), float(row["rms_h"])):
                raise ProtocolError("zero-control post hidden differs from pre-residual hidden")
        else:
            raise ProtocolError(f"unexpected engineering condition: {condition}")

    if len(baseline) != 8 * 50 * 21 * 2:
        raise ProtocolError(f"engineering baseline key count mismatch: {len(baseline)}")
    if len(zero_keys) != 8 * 50 * 21 * 2:
        raise ProtocolError(f"engineering zero-control key count mismatch: {len(zero_keys)}")
    if zero_rows != 8 * 50 * 21 * 2:
        raise ProtocolError(f"engineering zero-control row count mismatch: {zero_rows}")
    maximum_repeat_difference = 0.0
    for key, repetitions in baseline.items():
        if set(repetitions) != {"1", "2"}:
            raise ProtocolError(f"baseline repetitions missing for {key}")
        first, second = repetitions["1"], repetitions["2"]
        if first["scheduler_timestep"] != second["scheduler_timestep"]:
            raise ProtocolError(f"scheduler timestep repeat mismatch for {key}")
        for field in NUMERIC_SUMMARY_FIELDS:
            a, b = float(first[field]), float(second[field])
            maximum_repeat_difference = max(maximum_repeat_difference, abs(a - b))
            if not _within(a, b):
                raise ProtocolError(f"baseline numerical repeat mismatch for {key}/{field}")

    routes: dict[str, dict[tuple[str, str], dict[str, str]]] = defaultdict(dict)
    for row in _rows(route_path):
        key = (row["condition"], "2" if "__baseline__r2" in row["trace_task_id"] else "1")
        if key in routes[row["formal_unit_id"]]:
            raise ProtocolError(f"duplicate route summary: {row['formal_unit_id']}/{key}")
        routes[row["formal_unit_id"]][key] = row
    if len(routes) != 8:
        raise ProtocolError(f"engineering route unit count mismatch: {len(routes)}")
    maximum_route_difference = 0.0
    for unit, variants in routes.items():
        expected = {("baseline", "1"), ("baseline", "2"), ("zero_local_residual", "1")}
        if set(variants) != expected:
            raise ProtocolError(f"engineering route variants missing for {unit}")
        reference = variants[("baseline", "1")]
        for variant in (("baseline", "2"), ("zero_local_residual", "1")):
            candidate = variants[variant]
            for field in ROUTE_FIELDS:
                a, b = float(reference[field]), float(candidate[field])
                maximum_route_difference = max(maximum_route_difference, abs(a - b))
                if not _within(a, b):
                    raise ProtocolError(f"reference-image route changed for {unit}/{variant}/{field}")

    if not math.isfinite(maximum_repeat_difference) or not math.isfinite(maximum_route_difference):
        raise ProtocolError("engineering control difference is not finite")
    return {
        "status": "PASS_ENGINEERING_REPEAT_AND_ZERO_ROUTE_CONTROLS",
        "units": 8,
        "baseline_repeat_keys": len(baseline),
        "zero_control_rows": zero_rows,
        "maximum_baseline_repeat_absolute_difference": maximum_repeat_difference,
        "maximum_reference_route_absolute_difference": maximum_route_difference,
    }
