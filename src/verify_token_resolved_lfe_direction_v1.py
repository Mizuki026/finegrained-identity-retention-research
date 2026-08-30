#!/usr/bin/env python3
"""Independent verifier for token-resolved LFE direction analysis v1."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import token_resolved_lfe_direction_protocol_v1 as protocol


class DirectionVerificationError(RuntimeError):
    """Raised when dry-run or transient scientific results do not reproduce."""


def _torch():
    try:
        import torch
    except ImportError as error:
        raise DirectionVerificationError("torch is required only for transient recomputation") from error
    return torch


def _finite_number(raw: Any, label: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as error:
        raise DirectionVerificationError(f"invalid numeric value: {label}") from error
    if not math.isfinite(value):
        raise DirectionVerificationError(f"nonfinite numeric value: {label}")
    return value


def _label(value: float) -> str:
    if abs(value) <= protocol.TIE_THRESHOLD:
        return "tie"
    return "correct" if value > 0 else "wrong"


def _read_rows(path: Path, expected: int) -> list[dict[str, str]]:
    if not path.is_file() or path.is_symlink():
        raise DirectionVerificationError(f"missing regular dry-run file: {path}")
    rows = protocol.read_csv(path)
    if len(rows) != expected:
        raise DirectionVerificationError(f"row-count mismatch: {path}")
    return rows


def verify_dry_run(run_dir: Path) -> dict:
    protocol.ensure_cpu_only()
    summary_path = run_dir / "no_weight_dry_run_v1.json"
    summary = protocol.read_json(summary_path)
    if summary.get("status") != protocol.DRY_RUN_STATUS:
        raise DirectionVerificationError("dry-run status mismatch")
    exact = {
        "engineering_units": 8,
        "engineering_direct_passes": 16,
        "engineering_hook_controls": 8,
        "engineering_plan_rows": 24,
        "scientific_reference_plan_rows": 160,
        "formal_units": 40,
        "matched_pairs": 20,
        "planned_primary_margins": 640,
    }
    if any(summary.get(key) != value for key, value in exact.items()):
        raise DirectionVerificationError("dry-run planned-count mismatch")
    forbidden_false = (
        "reference_images_opened", "outcomes_opened", "model_modules_imported",
        "model_weights_loaded", "raw_tokens_captured", "scientific_margins_computed",
        "gpu_used", "network_used", "generation_run", "formal_input_audit_performed",
        "execution_authorized",
    )
    if any(summary.get(key) is not False for key in forbidden_false):
        raise DirectionVerificationError("dry-run reports a forbidden action")
    approval = Path(summary["approved_design_path"])
    protocol.verify_file(approval, int(summary["approved_design_bytes"]), summary["approved_design_sha256"])
    protocol.verify_file(
        Path(summary["formal_master_path"]),
        int(summary["formal_master_bytes"]),
        summary["formal_master_sha256"],
    )
    engineering = _read_rows(run_dir / "engineering_plan_v1.csv", 24)
    scientific = _read_rows(run_dir / "scientific_reference_plan_v1.csv", 160)
    if Counter(row["operation"] for row in engineering) != Counter({
        "direct_lfe_repeat_1": 8, "direct_lfe_repeat_2": 8, "one_step_hook_equivalence": 8
    }):
        raise DirectionVerificationError("engineering operation universe mismatch")
    if set(row["operation"] for row in scientific) != {"direct_lfe"}:
        raise DirectionVerificationError("scientific operation universe mismatch")
    if len({row["formal_unit_id"] for row in scientific}) != 40:
        raise DirectionVerificationError("scientific unit universe mismatch")
    seeds = defaultdict(set)
    pair_roles = defaultdict(set)
    for row in scientific:
        seeds[row["formal_unit_id"]].add(row["seed"])
        pair_roles[(row["attribute"], row["formal_pair_id"])].add(row["role"])
    if any(value != set(protocol.FORMAL_SEEDS) for value in seeds.values()):
        raise DirectionVerificationError("scientific seed crossing mismatch")
    if len(pair_roles) != 20 or any(value != set(protocol.ROLES) for value in pair_roles.values()):
        raise DirectionVerificationError("scientific pair-role crossing mismatch")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_TOKEN_DIRECTION_NO_WEIGHT_DRY_RUN_VERIFICATION",
        "summary_path": str(summary_path.resolve()),
        "summary_bytes": summary_path.stat().st_size,
        "summary_sha256": protocol.sha256(summary_path),
        "engineering_plan_rows": 24,
        "scientific_reference_plan_rows": 160,
        "planned_primary_margins": 640,
        "reference_images_opened": False,
        "outcomes_opened": False,
        "model_loaded": False,
        "raw_tokens_captured": False,
        "gpu_used": False,
    }


def _panel(
    unit_tokens: dict[str, Any], metadata: dict[str, dict[str, str]], expected_dim: int
) -> tuple[dict[str, Any], dict[str, dict[str, dict[str, str]]]]:
    torch = _torch()
    if len(unit_tokens) != 40 or set(unit_tokens) != set(metadata):
        raise DirectionVerificationError("transient unit universe mismatch")
    normalized = {}
    pairs = {attribute: defaultdict(dict) for attribute in protocol.ATTRIBUTES}
    for unit, raw in unit_tokens.items():
        tensor = raw.detach().to(device="cpu", dtype=torch.float32)
        if tuple(tensor.shape) != (protocol.LFE_TOKENS, expected_dim) or not bool(torch.isfinite(tensor).all()):
            raise DirectionVerificationError("transient tensor shape or finiteness mismatch")
        normalized[unit] = torch.nn.functional.normalize(tensor, p=2.0, dim=1, eps=1e-12)
        meta = metadata[unit]
        attribute, pair, role = meta["attribute"], meta["formal_pair_id"], meta["role"]
        if attribute not in protocol.ATTRIBUTES or role not in protocol.ROLES or role in pairs[attribute][pair]:
            raise DirectionVerificationError("transient metadata drift")
        pairs[attribute][pair][role] = unit
    for attribute in protocol.ATTRIBUTES:
        if len(pairs[attribute]) != 10 or any(set(value) != set(protocol.ROLES) for value in pairs[attribute].values()):
            raise DirectionVerificationError("transient matched-pair drift")
    return normalized, pairs


def _recompute_margins(
    unit_tokens: dict[str, Any], metadata: dict[str, dict[str, str]], expected_dim: int
) -> dict[tuple[str, int, str], tuple[float, str]]:
    torch = _torch()
    normalized, pairs = _panel(unit_tokens, metadata, expected_dim)
    result = {}
    for attribute in protocol.ATTRIBUTES:
        pair_ids = sorted(pairs[attribute])
        for token_index in range(protocol.LFE_TOKENS):
            for held in pair_ids:
                train = [pair for pair in pair_ids if pair != held]
                positive_train = torch.stack([
                    normalized[pairs[attribute][pair]["positive"]][token_index] for pair in train
                ])
                control_train = torch.stack([
                    normalized[pairs[attribute][pair]["control"]][token_index] for pair in train
                ])
                direction = positive_train.mean(dim=0) - control_train.mean(dim=0)
                held_difference = (
                    normalized[pairs[attribute][held]["positive"]][token_index]
                    - normalized[pairs[attribute][held]["control"]][token_index]
                )
                margin = float(torch.sum(held_difference * direction).item())
                if not math.isfinite(margin):
                    raise DirectionVerificationError("nonfinite recomputed margin")
                result[(attribute, token_index, held)] = (margin, _label(margin))
    if len(result) != 640:
        raise DirectionVerificationError("recomputed margin family mismatch")
    return result


def _recompute_pooled(
    unit_tokens: dict[str, Any], metadata: dict[str, dict[str, str]], expected_dim: int
) -> dict[tuple[str, str], float]:
    torch = _torch()
    _normalized, pairs = _panel(unit_tokens, metadata, expected_dim)
    pooled = {}
    for unit, raw in unit_tokens.items():
        tensor = raw.detach().to(device="cpu", dtype=torch.float32)
        vector = tensor.mean(dim=0)
        pooled[unit] = vector / torch.linalg.vector_norm(vector).clamp_min(1e-12)
    result = {}
    for attribute in protocol.ATTRIBUTES:
        pair_ids = sorted(pairs[attribute])
        for held in pair_ids:
            train = [pair for pair in pair_ids if pair != held]
            positive_train = torch.stack([pooled[pairs[attribute][pair]["positive"]] for pair in train])
            control_train = torch.stack([pooled[pairs[attribute][pair]["control"]] for pair in train])
            direction = positive_train.mean(dim=0) - control_train.mean(dim=0)
            held_difference = (
                pooled[pairs[attribute][held]["positive"]]
                - pooled[pairs[attribute][held]["control"]]
            )
            margin = float(torch.sum(held_difference * direction).item())
            if not math.isfinite(margin):
                raise DirectionVerificationError("nonfinite recomputed pooled margin")
            result[(attribute, held)] = margin
    if len(result) != 20:
        raise DirectionVerificationError("recomputed pooled margin family mismatch")
    return result


def _verify_summary_values(row: dict, values: list[float], label: str) -> None:
    expected = {
        "mean_margin": statistics.fmean(values),
        "median_margin": statistics.median(values),
        "minimum_margin": min(values),
        "maximum_margin": max(values),
    }
    for field, value in expected.items():
        observed = _finite_number(row[field], f"{label}/{field}")
        if not math.isclose(observed, value, rel_tol=1e-6, abs_tol=1e-7):
            raise DirectionVerificationError(f"{label} summary mismatch: {field}")


def verify_transient_results(
    unit_tokens: dict[str, Any],
    metadata: dict[str, dict[str, str]],
    analyzer_result: dict[str, list[dict]],
    *,
    expected_dim: int = protocol.LFE_DIM,
) -> dict:
    expected = _recompute_margins(unit_tokens, metadata, expected_dim)
    expected_pooled = _recompute_pooled(unit_tokens, metadata, expected_dim)
    rows = analyzer_result.get("token_margins", [])
    if len(rows) != 640:
        raise DirectionVerificationError("analyzer margin output count mismatch")
    seen = set()
    for row in rows:
        key = (row["attribute"], int(row["token_index"]), row["formal_pair_id"])
        if key in seen or key not in expected:
            raise DirectionVerificationError("analyzer margin key mismatch")
        seen.add(key)
        expected_margin, expected_label = expected[key]
        observed = _finite_number(row["margin"], "analyzer margin")
        if not math.isclose(observed, expected_margin, rel_tol=1e-6, abs_tol=1e-7):
            raise DirectionVerificationError(f"analyzer margin mismatch: {key}")
        if row["direction"] != expected_label:
            raise DirectionVerificationError(f"analyzer direction mismatch: {key}")
    if seen != set(expected):
        raise DirectionVerificationError("analyzer margin key universe incomplete")
    token_panel = analyzer_result.get("token_finite_panel", [])
    pair_signs = analyzer_result.get("pair_token_signs", [])
    pooled = analyzer_result.get("pooled_replication", [])
    if (len(token_panel), len(pair_signs), len(pooled)) != (64, 20, 20):
        raise DirectionVerificationError("analyzer summary count mismatch")
    for row in token_panel:
        key_prefix = (row["attribute"], int(row["token_index"]))
        selected = [value for (attribute, token, _pair), value in expected.items() if (attribute, token) == key_prefix]
        labels = [label for _margin, label in selected]
        counts = Counter(labels)
        if (int(row["correct_count"]), int(row["tie_count"]), int(row["wrong_count"])) != (
            counts["correct"], counts["tie"], counts["wrong"]
        ):
            raise DirectionVerificationError("token-panel sign counts mismatch")
        _verify_summary_values(row, [margin for margin, _label_value in selected], "token-panel")
    for row in pair_signs:
        selected = [value for (attribute, _token, pair), value in expected.items() if (attribute, pair) == (row["attribute"], row["formal_pair_id"])]
        labels = [label for _margin, label in selected]
        counts = Counter(labels)
        if len(labels) != 32 or (int(row["correct_count"]), int(row["tie_count"]), int(row["wrong_count"])) != (
            counts["correct"], counts["tie"], counts["wrong"]
        ):
            raise DirectionVerificationError("pair-token sign counts mismatch")
        _verify_summary_values(row, [margin for margin, _label_value in selected], "pair-token")
    seen_pooled = set()
    for row in pooled:
        key = (row["attribute"], row["formal_pair_id"])
        if key in seen_pooled or key not in expected_pooled:
            raise DirectionVerificationError("pooled replication key mismatch")
        seen_pooled.add(key)
        reconstructed = _finite_number(row["reconstructed_margin"], "pooled reconstructed")
        frozen = _finite_number(row["frozen_run_003_margin"], "pooled frozen")
        difference = _finite_number(row["absolute_difference"], "pooled difference")
        if not math.isclose(reconstructed, expected_pooled[key], rel_tol=1e-6, abs_tol=1e-7):
            raise DirectionVerificationError("pooled reconstruction mismatch")
        if not math.isclose(difference, abs(reconstructed - frozen), rel_tol=0, abs_tol=1e-15):
            raise DirectionVerificationError("pooled difference mismatch")
        tolerance = 1e-6 + 1e-5 * max(abs(reconstructed), abs(frozen))
        expected_within = difference <= tolerance
        if row.get("within_tolerance") is not expected_within or not expected_within:
            raise DirectionVerificationError("pooled replication did not pass")
        if row.get("direction") != _label(reconstructed):
            raise DirectionVerificationError("pooled direction mismatch")
    if seen_pooled != set(expected_pooled):
        raise DirectionVerificationError("pooled replication universe incomplete")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_IN_MEMORY_TOKEN_DIRECTION_RECOMPUTATION",
        "all_640_margins_recomputed": True,
        "token_panel_rows": 64,
        "pair_token_sign_rows": 20,
        "pooled_replication_rows": 20,
        "raw_vectors_persisted": False,
        "outcomes_opened": False,
        "gpu_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run",), required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify_dry_run(args.run_dir)
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DirectionVerificationError, protocol.DirectionProtocolError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
