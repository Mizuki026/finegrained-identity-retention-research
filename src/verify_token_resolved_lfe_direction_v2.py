#!/usr/bin/env python3
"""Independent dry-run, transient, and persisted verifier for token-direction v2."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import token_resolved_lfe_direction_protocol_v2 as protocol


class DirectionV2VerificationError(RuntimeError):
    pass


def _torch():
    try:
        import torch
    except ImportError as error:
        raise DirectionV2VerificationError("torch is required only for transient recomputation") from error
    return torch


def _label(value: float) -> str:
    return "tie" if abs(value) <= protocol.TIE_THRESHOLD else ("correct" if value > 0 else "wrong")


def _finite(raw: Any, label: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as error:
        raise DirectionV2VerificationError(f"invalid numeric value: {label}") from error
    if not math.isfinite(value):
        raise DirectionV2VerificationError(f"nonfinite numeric value: {label}")
    return value


def _boolean(raw: Any) -> bool:
    if raw in (True, "True"):
        return True
    if raw in (False, "False"):
        return False
    raise DirectionV2VerificationError("invalid Boolean")


def _rows(path: Path, count: int) -> list[dict[str, str]]:
    if not path.is_file() or path.is_symlink():
        raise DirectionV2VerificationError(f"missing regular file: {path}")
    rows = protocol.read_csv(path)
    if len(rows) != count:
        raise DirectionV2VerificationError(f"row count mismatch: {path.name}")
    return rows


def verify_dry_run(run_dir: Path) -> dict:
    protocol.require_cpu_only()
    summary_path = run_dir / "token_direction_v2_no_weight_dry_run.json"
    summary = protocol.read_json(summary_path)
    if summary.get("status") != protocol.DRY_STATUS:
        raise DirectionV2VerificationError("dry-run status mismatch")
    exact = {
        "plan_rows": 160, "formal_units": 40, "matched_pairs": 20,
        "fresh_preprocessing_calls_planned": 160, "direct_lfe_calls_planned": 200,
        "same_input_direct_repeat_controls_planned": 40, "four_label_comparisons_planned": 120,
        "current_pooled_rows_planned": 20, "historical_rows_planned": 20,
        "token_margin_rows_planned": 640, "token_panel_rows_planned": 64,
        "pair_sign_rows_planned": 20,
    }
    if any(summary.get(key) != value for key, value in exact.items()):
        raise DirectionV2VerificationError("dry-run planned count mismatch")
    forbidden = (
        "reference_images_opened", "preprocessing_run", "model_or_weight_loading", "gpu_used",
        "raw_tokens_captured", "formal_token_margins_computed", "outcomes_opened",
        "associations_computed", "generation_run", "intervention_run", "network_used", "torch_imported",
    )
    if any(summary.get(key) is not False for key in forbidden):
        raise DirectionV2VerificationError("dry-run reports forbidden action")
    plan = _rows(run_dir / "token_direction_v2_execution_plan.csv", 160)
    if len({row["v2_task_id"] for row in plan}) != 160 or len({row["formal_unit_id"] for row in plan}) != 40:
        raise DirectionV2VerificationError("dry-run plan key universe drift")
    if Counter(row["direct_lfe_calls"] for row in plan) != Counter({"1": 120, "2": 40}):
        raise DirectionV2VerificationError("dry-run direct-repeat crossing drift")
    seeds, roles = defaultdict(dict), defaultdict(set)
    for row in plan:
        seeds[row["formal_unit_id"]][row["seed_index"]] = row["seed"]
        roles[(row["attribute"], row["formal_pair_id"])].add(row["role"])
    if any(value != protocol.SEED_MAP for value in seeds.values()) or len(roles) != 20 or any(value != set(protocol.ROLES) for value in roles.values()):
        raise DirectionV2VerificationError("dry-run crossing drift")
    return {"schema_version": 2, "status": "PASS_INDEPENDENT_TOKEN_DIRECTION_V2_NO_WEIGHT_DRY_RUN_VERIFICATION", "plan_rows": 160, "formal_units": 40, "fresh_preprocessing_calls_planned": 160, "direct_lfe_calls_planned": 200, "token_margin_rows_planned": 640, "reference_images_opened": False, "model_loaded": False, "gpu_used": False, "outcome_access": False}


def _compare(left: Any, right: Any) -> tuple[bool, bool, float, float]:
    torch = _torch()
    delta = torch.abs(left - right)
    limit = 1e-6 + 1e-5 * torch.maximum(torch.abs(left), torch.abs(right))
    return bool(torch.equal(left, right)), bool(torch.all(delta <= limit)), float(torch.max(delta).item()), float(torch.sqrt(torch.mean((left - right) ** 2)).item())


def _recompute(tensors: dict[str, dict[str, dict[str, Any]]], metadata: dict[str, dict[str, str]], historical_rows: list[dict[str, str]], expected_dim: int) -> dict[str, list[dict]]:
    torch = _torch()
    if len(tensors) != 40 or set(tensors) != set(metadata):
        raise DirectionV2VerificationError("transient unit universe drift")
    clean, pairs, direct, four = {}, {a: defaultdict(dict) for a in protocol.ATTRIBUTES}, [], []
    for unit in sorted(tensors):
        meta = metadata[unit]
        if set(meta) != {"formal_pair_id", "attribute", "role"} or meta["attribute"] not in protocol.ATTRIBUTES or meta["role"] not in protocol.ROLES:
            raise DirectionV2VerificationError("transient metadata drift")
        pair, attribute, role = meta["formal_pair_id"], meta["attribute"], meta["role"]
        if role in pairs[attribute][pair]:
            raise DirectionV2VerificationError("duplicate pair role")
        pairs[attribute][pair][role] = unit
        if set(tensors[unit]) != set(protocol.SEED_MAP):
            raise DirectionV2VerificationError("transient seed universe drift")
        clean[unit] = {}
        for seed_index in protocol.SEED_MAP:
            expected = {"D1", "D2"} if seed_index == "1" else {"D1"}
            if set(tensors[unit][seed_index]) != expected:
                raise DirectionV2VerificationError("transient repeat universe drift")
            clean[unit][seed_index] = {}
            for repeat, value in tensors[unit][seed_index].items():
                tensor = value.detach().to(device="cpu", dtype=torch.float32)
                if tuple(tensor.shape) != (1, protocol.LFE_TOKENS, expected_dim) or not bool(torch.isfinite(tensor).all()):
                    raise DirectionV2VerificationError("transient tensor drift")
                clean[unit][seed_index][repeat] = tensor[0].clone()
        values = _compare(clean[unit]["1"]["D1"], clean[unit]["1"]["D2"])
        direct.append({"formal_unit_id": unit, **meta, "bit_exact": values[0], "within_frozen_tolerance": values[1], "max_absolute_difference": values[2], "rms_difference": values[3]})
        for seed_index in ("2", "3", "4"):
            values = _compare(clean[unit]["1"]["D1"], clean[unit][seed_index]["D1"])
            four.append({"formal_unit_id": unit, **meta, "comparison_seed_index": seed_index, "bit_exact": values[0], "within_frozen_tolerance": values[1], "max_absolute_difference": values[2], "rms_difference": values[3]})
    if any(len(pairs[a]) != 10 or any(set(v) != set(protocol.ROLES) for v in pairs[a].values()) for a in protocol.ATTRIBUTES):
        raise DirectionV2VerificationError("transient pair universe drift")
    if not all(row["within_frozen_tolerance"] for row in direct + four):
        raise DirectionV2VerificationError("transient equality gate failed")
    pooled, normalized = {}, {}
    for unit in clean:
        pooled_parts, token_parts = [], []
        for seed_index in protocol.SEED_MAP:
            raw = clean[unit][seed_index]["D1"]
            vector = raw.mean(0)
            pooled_parts.append(vector / torch.linalg.vector_norm(vector).clamp_min(1e-12))
            token_parts.append(raw / torch.linalg.vector_norm(raw, dim=1, keepdim=True).clamp_min(1e-12))
        pooled[unit] = torch.stack(pooled_parts).mean(0)
        normalized[unit] = torch.stack(token_parts).mean(0)
    pooled_rows, pooled_map, margins = [], {}, []
    for attribute in protocol.ATTRIBUTES:
        pair_ids = sorted(pairs[attribute])
        for held in pair_ids:
            train = [pair for pair in pair_ids if pair != held]
            direction = torch.stack([pooled[pairs[attribute][pair]["positive"]] - pooled[pairs[attribute][pair]["control"]] for pair in train]).mean(0)
            value = float(torch.dot(pooled[pairs[attribute][held]["positive"]] - pooled[pairs[attribute][held]["control"]], direction).item())
            if not math.isfinite(value):
                raise DirectionV2VerificationError("nonfinite pooled margin")
            pooled_map[(attribute, held)] = value
            pooled_rows.append({"attribute": attribute, "formal_pair_id": held, "margin": value, "direction": _label(value)})
        for token_index in range(protocol.LFE_TOKENS):
            for held in pair_ids:
                train = [pair for pair in pair_ids if pair != held]
                direction = torch.stack([normalized[pairs[attribute][pair]["positive"]][token_index] - normalized[pairs[attribute][pair]["control"]][token_index] for pair in train]).mean(0)
                value = float(torch.dot(normalized[pairs[attribute][held]["positive"]][token_index] - normalized[pairs[attribute][held]["control"]][token_index], direction).item())
                if not math.isfinite(value):
                    raise DirectionV2VerificationError("nonfinite token margin")
                margins.append({"attribute": attribute, "token_index": token_index, "formal_pair_id": held, "margin": value, "direction": _label(value)})
    historical = {}
    for row in historical_rows:
        if row.get("stage") != "valid_face_emb_mean_token_l2_normalized" or row.get("attribute") not in protocol.ATTRIBUTES:
            continue
        key = (row["attribute"], row["formal_pair_id"])
        value = _finite(row["margin"], "historical source")
        if key in historical:
            raise DirectionV2VerificationError("duplicate historical key")
        historical[key] = value
    if len(historical) != 20:
        raise DirectionV2VerificationError("historical universe drift")
    history_rows = []
    for key in sorted(pooled_map):
        current, frozen = pooled_map[key], historical[key]
        difference = abs(current - frozen); tolerance = 1e-6 + 1e-5 * max(abs(current), abs(frozen))
        current_label, frozen_label = _label(current), _label(frozen)
        history_rows.append({"attribute": key[0], "formal_pair_id": key[1], "current_margin": current, "frozen_run_003_margin": frozen, "absolute_difference": difference, "tolerance": tolerance, "within_tolerance": difference <= tolerance, "current_direction": current_label, "frozen_direction": frozen_label, "sign_match": current_label == frozen_label})
    by_token, by_pair = defaultdict(list), defaultdict(list)
    for row in margins:
        by_token[(row["attribute"], row["token_index"])].append(row)
        by_pair[(row["attribute"], row["formal_pair_id"])].append(row)
    def summary(rows: list[dict], key: dict) -> dict:
        values = [row["margin"] for row in rows]; counts = Counter(row["direction"] for row in rows)
        return {**key, "correct_count": counts["correct"], "tie_count": counts["tie"], "wrong_count": counts["wrong"], "mean_margin": statistics.fmean(values), "median_margin": statistics.median(values), "minimum_margin": min(values), "maximum_margin": max(values)}
    panels = [summary(rows, {"attribute": key[0], "token_index": key[1], "pairs": 10}) for key, rows in sorted(by_token.items())]
    signs = [summary(rows, {"attribute": key[0], "formal_pair_id": key[1], "tokens": 32}) for key, rows in sorted(by_pair.items())]
    return {"direct_controls": direct, "four_label_controls": four, "current_pooled": pooled_rows, "historical": history_rows, "token_margins": margins, "token_panel": panels, "pair_signs": signs}


def _same(observed: dict[str, list[dict]], expected: dict[str, list[dict]]) -> None:
    if set(observed) != set(expected):
        raise DirectionV2VerificationError("analyzer family universe drift")
    numeric = {"max_absolute_difference", "rms_difference", "margin", "current_margin", "frozen_run_003_margin", "absolute_difference", "tolerance", "mean_margin", "median_margin", "minimum_margin", "maximum_margin"}
    for family in expected:
        if len(observed[family]) != len(expected[family]):
            raise DirectionV2VerificationError(f"family count drift: {family}")
        for left, right in zip(observed[family], expected[family]):
            if set(left) != set(right):
                raise DirectionV2VerificationError(f"field drift: {family}")
            for key in right:
                if key in numeric:
                    if not math.isclose(_finite(left[key], key), float(right[key]), rel_tol=1e-6, abs_tol=1e-7):
                        raise DirectionV2VerificationError(f"numeric mismatch: {family}/{key}")
                elif left[key] != right[key]:
                    raise DirectionV2VerificationError(f"categorical mismatch: {family}/{key}")


def verify_transient(tensors: dict[str, dict[str, dict[str, Any]]], metadata: dict[str, dict[str, str]], historical_rows: list[dict[str, str]], observed: dict[str, list[dict]], *, expected_dim: int = protocol.LFE_DIM) -> dict:
    expected = _recompute(tensors, metadata, historical_rows, expected_dim)
    _same(observed, expected)
    return {"schema_version": 2, "status": "PASS_INDEPENDENT_IN_MEMORY_TOKEN_DIRECTION_V2_RECOMPUTATION", "direct_control_rows": 40, "four_label_control_rows": 120, "current_pooled_rows": 20, "historical_rows": 20, "all_640_margins_recomputed": True, "token_panel_rows": 64, "pair_sign_rows": 20, "raw_vectors_persisted": False, "outcomes_opened": False}


def _check_summary(row: dict[str, str], selected: list[tuple[float, str]], expected_n: int) -> None:
    if len(selected) != expected_n:
        raise DirectionV2VerificationError("persisted summary universe drift")
    values = [item[0] for item in selected]; counts = Counter(item[1] for item in selected)
    if tuple(int(row[key]) for key in ("correct_count", "tie_count", "wrong_count")) != (counts["correct"], counts["tie"], counts["wrong"]):
        raise DirectionV2VerificationError("persisted summary count drift")
    expected = (statistics.fmean(values), statistics.median(values), min(values), max(values))
    observed = tuple(_finite(row[key], key) for key in ("mean_margin", "median_margin", "minimum_margin", "maximum_margin"))
    if any(not math.isclose(left, right, rel_tol=1e-6, abs_tol=1e-7) for left, right in zip(observed, expected)):
        raise DirectionV2VerificationError("persisted summary value drift")


def verify_persisted(run_dir: Path) -> dict:
    direct = _rows(run_dir / "same_input_direct_repeat_controls_v2.csv", 40)
    four = _rows(run_dir / "four_label_lfe_equivalence_v2.csv", 120)
    pooled = _rows(run_dir / "current_pooled_lfe_margins_v2.csv", 20)
    history = _rows(run_dir / "historical_run_003_comparison_v2.csv", 20)
    margins = _rows(run_dir / "lfe_token_margins_v2.csv", 640)
    panels = _rows(run_dir / "lfe_token_finite_panel_v2.csv", 64)
    signs = _rows(run_dir / "lfe_pair_token_signs_v2.csv", 20)
    status = _rows(run_dir / "token_direction_v2_execution_status.csv", 160)
    if any(not _boolean(row["within_frozen_tolerance"]) for row in direct + four):
        raise DirectionV2VerificationError("persisted validity control failed")
    direct_units = {}
    for row in direct:
        key = row["formal_unit_id"]
        meta = (row["attribute"], row["formal_pair_id"], row["role"])
        if key in direct_units or meta[0] not in protocol.ATTRIBUTES or meta[2] not in protocol.ROLES:
            raise DirectionV2VerificationError("direct-control crossing drift")
        direct_units[key] = meta
    four_keys = set()
    for row in four:
        unit = row["formal_unit_id"]
        key = (unit, row["comparison_seed_index"])
        meta = (row["attribute"], row["formal_pair_id"], row["role"])
        if unit not in direct_units or direct_units[unit] != meta or row["comparison_seed_index"] not in {"2", "3", "4"} or key in four_keys:
            raise DirectionV2VerificationError("four-label crossing drift")
        four_keys.add(key)
    if len(direct_units) != 40 or len(four_keys) != 120:
        raise DirectionV2VerificationError("control universe drift")
    status_task_ids, status_keys = set(), set()
    status_units = defaultdict(dict)
    for row in status:
        unit, seed_index = row["formal_unit_id"], row["seed_index"]
        key = (unit, seed_index)
        if row["v2_task_id"] in status_task_ids or unit not in direct_units or key in status_keys:
            raise DirectionV2VerificationError("persisted status duplicate drift")
        status_task_ids.add(row["v2_task_id"]); status_keys.add(key)
        if seed_index not in protocol.SEED_MAP or row["seed"] != protocol.SEED_MAP[seed_index]:
            raise DirectionV2VerificationError("persisted status seed drift")
        if (row["attribute"], row["formal_pair_id"], row["role"]) != direct_units[unit]:
            raise DirectionV2VerificationError("persisted status metadata drift")
        if int(row["preprocessing_calls"]) != 1 or int(row["direct_lfe_calls"]) != (2 if seed_index == "1" else 1):
            raise DirectionV2VerificationError("persisted status call-count drift")
        status_units[unit][seed_index] = row["seed"]
    if len(status_task_ids) != 160 or any(value != protocol.SEED_MAP for value in status_units.values()) or any(row["status"] != "COMPLETE_TRANSIENT_ONLY" for row in status):
        raise DirectionV2VerificationError("persisted status universe drift")
    pooled_map = {}
    for row in pooled:
        value = _finite(row["margin"], "pooled margin")
        key = (row["attribute"], row["formal_pair_id"])
        if row["attribute"] not in protocol.ATTRIBUTES or key in pooled_map or row["direction"] != _label(value):
            raise DirectionV2VerificationError("pooled key or label drift")
        pooled_map[key] = value
    if len(pooled_map) != 20:
        raise DirectionV2VerificationError("pooled key drift")
    history_keys = set()
    for row in history:
        key = (row["attribute"], row["formal_pair_id"])
        current = _finite(row["current_margin"], "history current"); frozen = _finite(row["frozen_run_003_margin"], "history frozen")
        difference = abs(current - frozen); tolerance = 1e-6 + 1e-5 * max(abs(current), abs(frozen))
        if key not in pooled_map or key in history_keys or not math.isclose(current, pooled_map[key], rel_tol=0, abs_tol=1e-15):
            raise DirectionV2VerificationError("historical-to-current join drift")
        history_keys.add(key)
        if not math.isclose(_finite(row["absolute_difference"], "difference"), difference, rel_tol=0, abs_tol=1e-15) or not math.isclose(_finite(row["tolerance"], "tolerance"), tolerance, rel_tol=0, abs_tol=1e-15):
            raise DirectionV2VerificationError("historical arithmetic drift")
        if _boolean(row["within_tolerance"]) != (difference <= tolerance) or row["current_direction"] != _label(current) or row["frozen_direction"] != _label(frozen) or _boolean(row["sign_match"]) != (_label(current) == _label(frozen)):
            raise DirectionV2VerificationError("historical label drift")
    if history_keys != set(pooled_map):
        raise DirectionV2VerificationError("historical key universe drift")
    by_token, by_pair, keys = defaultdict(list), defaultdict(list), set()
    for row in margins:
        value = _finite(row["margin"], "token margin"); label = _label(value)
        key = (row["attribute"], int(row["token_index"]), row["formal_pair_id"])
        if key[0] not in protocol.ATTRIBUTES or not 0 <= key[1] < protocol.LFE_TOKENS or (key[0], key[2]) not in pooled_map or key in keys or row["direction"] != label:
            raise DirectionV2VerificationError("token key or label drift")
        keys.add(key); by_token[key[:2]].append((value, label)); by_pair[(key[0], key[2])].append((value, label))
    if len(keys) != 640:
        raise DirectionV2VerificationError("token family key drift")
    panel_keys = set()
    for row in panels:
        key = (row["attribute"], int(row["token_index"]))
        if key in panel_keys or int(row["pairs"]) != 10:
            raise DirectionV2VerificationError("token-panel key drift")
        panel_keys.add(key); _check_summary(row, by_token[key], 10)
    sign_keys = set()
    for row in signs:
        key = (row["attribute"], row["formal_pair_id"])
        if key in sign_keys or int(row["tokens"]) != 32:
            raise DirectionV2VerificationError("pair-sign key drift")
        sign_keys.add(key); _check_summary(row, by_pair[key], 32)
    if panel_keys != set(by_token) or sign_keys != set(by_pair):
        raise DirectionV2VerificationError("persisted summary key universe drift")
    memory = protocol.read_json(run_dir / "token_direction_v2_in_memory_verification.json")
    summary = protocol.read_json(run_dir / "token_direction_v2_execution_summary.json")
    if memory.get("status") != "PASS_INDEPENDENT_IN_MEMORY_TOKEN_DIRECTION_V2_RECOMPUTATION" or memory.get("all_640_margins_recomputed") is not True:
        raise DirectionV2VerificationError("in-memory verification missing")
    if summary.get("raw_identity_or_token_tensor_files") != 0 or summary.get("outcomes_opened_or_joined") is not False:
        raise DirectionV2VerificationError("privacy or outcome boundary drift")
    forbidden = {".pt", ".pth", ".npy", ".npz", ".safetensors", ".png", ".jpg", ".jpeg", ".mp4"}
    if any(path.is_file() and path.suffix.lower() in forbidden for path in run_dir.iterdir()):
        raise DirectionV2VerificationError("raw tensor or media file found")
    return {"schema_version": 2, "status": "PASS_INDEPENDENT_PERSISTED_TOKEN_DIRECTION_V2_VERIFICATION", "execution_rows": 160, "direct_control_rows": 40, "four_label_control_rows": 120, "current_pooled_rows": 20, "historical_rows": 20, "margin_rows": 640, "token_panel_rows": 64, "pair_sign_rows": 20, "all_640_margins_recomputed_in_memory": True, "raw_tensor_files": 0, "outcome_access": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("dry-run", "persisted"))
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify_dry_run(args.run_dir) if args.mode == "dry-run" else verify_persisted(args.run_dir)
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DirectionV2VerificationError, protocol.DirectionV2ProtocolError, ValueError, KeyError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(2)
