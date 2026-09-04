#!/usr/bin/env python3
"""Transient, outcome-blind analyzer for token-resolved LFE direction v2."""
from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import token_resolved_lfe_direction_protocol_v2 as protocol


DIRECT_FIELDS = ("formal_unit_id", "formal_pair_id", "attribute", "role", "bit_exact", "within_frozen_tolerance", "max_absolute_difference", "rms_difference")
FOUR_FIELDS = ("formal_unit_id", "formal_pair_id", "attribute", "role", "comparison_seed_index", "bit_exact", "within_frozen_tolerance", "max_absolute_difference", "rms_difference")
POOLED_FIELDS = ("attribute", "formal_pair_id", "margin", "direction")
HISTORICAL_FIELDS = ("attribute", "formal_pair_id", "current_margin", "frozen_run_003_margin", "absolute_difference", "tolerance", "within_tolerance", "current_direction", "frozen_direction", "sign_match")
TOKEN_FIELDS = ("attribute", "token_index", "formal_pair_id", "margin", "direction")
TOKEN_PANEL_FIELDS = ("attribute", "token_index", "pairs", "correct_count", "tie_count", "wrong_count", "mean_margin", "median_margin", "minimum_margin", "maximum_margin")
PAIR_FIELDS = ("attribute", "formal_pair_id", "tokens", "correct_count", "tie_count", "wrong_count", "mean_margin", "median_margin", "minimum_margin", "maximum_margin")


class DirectionV2AnalysisError(RuntimeError):
    pass


def _torch():
    try:
        import torch
    except ImportError as error:
        raise DirectionV2AnalysisError("torch is required only for transient tensor analysis") from error
    return torch


def _label(value: float) -> str:
    return "tie" if abs(value) <= protocol.TIE_THRESHOLD else ("correct" if value > 0 else "wrong")


def _compare(left: Any, right: Any) -> tuple[bool, bool, float, float]:
    torch = _torch()
    delta = torch.abs(left - right)
    tolerance = 1e-6 + 1e-5 * torch.maximum(torch.abs(left), torch.abs(right))
    return (
        bool(torch.equal(left, right)), bool(torch.all(delta <= tolerance)),
        float(torch.max(delta).item()), float(torch.sqrt(torch.mean((left - right) ** 2)).item()),
    )


def _summary(values: list[float]) -> dict[str, float]:
    if not values or any(not math.isfinite(value) for value in values):
        raise DirectionV2AnalysisError("empty or nonfinite summary")
    return {"mean_margin": statistics.fmean(values), "median_margin": statistics.median(values), "minimum_margin": min(values), "maximum_margin": max(values)}


def _margin(positive: Any, control: Any, direction: Any) -> float:
    torch = _torch()
    value = float(torch.dot(positive, direction).item() - torch.dot(control, direction).item())
    if not math.isfinite(value):
        raise DirectionV2AnalysisError("nonfinite margin")
    return value


def _clean_panel(tensors: dict[str, dict[str, dict[str, Any]]], metadata: dict[str, dict[str, str]], expected_dim: int):
    torch = _torch()
    if len(tensors) != 40 or set(tensors) != set(metadata):
        raise DirectionV2AnalysisError("expected exactly 40 complete units")
    clean = {}
    pairs = {attribute: defaultdict(dict) for attribute in protocol.ATTRIBUTES}
    direct_rows, four_rows = [], []
    for unit in sorted(tensors):
        meta = metadata[unit]
        if set(meta) != {"formal_pair_id", "attribute", "role"} or meta["attribute"] not in protocol.ATTRIBUTES or meta["role"] not in protocol.ROLES:
            raise DirectionV2AnalysisError(f"metadata drift: {unit}")
        pair, attribute, role = meta["formal_pair_id"], meta["attribute"], meta["role"]
        if not pair or role in pairs[attribute][pair]:
            raise DirectionV2AnalysisError(f"duplicate or missing pair role: {unit}")
        pairs[attribute][pair][role] = unit
        if set(tensors[unit]) != set(protocol.SEED_MAP):
            raise DirectionV2AnalysisError(f"four-label tensor universe drift: {unit}")
        clean[unit] = {}
        for seed_index in protocol.SEED_MAP:
            expected_repeats = {"D1", "D2"} if seed_index == "1" else {"D1"}
            if set(tensors[unit][seed_index]) != expected_repeats:
                raise DirectionV2AnalysisError(f"direct-repeat universe drift: {unit}/{seed_index}")
            clean[unit][seed_index] = {}
            for repeat, value in tensors[unit][seed_index].items():
                tensor = value.detach().to(device="cpu", dtype=torch.float32)
                if tuple(tensor.shape) != (1, protocol.LFE_TOKENS, expected_dim) or not bool(torch.isfinite(tensor).all()):
                    raise DirectionV2AnalysisError(f"shape or finiteness drift: {unit}/{seed_index}/{repeat}")
                clean[unit][seed_index][repeat] = tensor[0].clone()
        bit, passed, maximum, rms = _compare(clean[unit]["1"]["D1"], clean[unit]["1"]["D2"])
        direct_rows.append({"formal_unit_id": unit, **meta, "bit_exact": bit, "within_frozen_tolerance": passed, "max_absolute_difference": maximum, "rms_difference": rms})
        for seed_index in ("2", "3", "4"):
            bit, passed, maximum, rms = _compare(clean[unit]["1"]["D1"], clean[unit][seed_index]["D1"])
            four_rows.append({"formal_unit_id": unit, **meta, "comparison_seed_index": seed_index, "bit_exact": bit, "within_frozen_tolerance": passed, "max_absolute_difference": maximum, "rms_difference": rms})
    if any(len(pairs[a]) != 10 or any(set(roles) != set(protocol.ROLES) for roles in pairs[a].values()) for a in protocol.ATTRIBUTES):
        raise DirectionV2AnalysisError("matched-pair universe drift")
    if len(direct_rows) != 40 or len(four_rows) != 120:
        raise DirectionV2AnalysisError("validity-control row count drift")
    if not all(row["within_frozen_tolerance"] for row in direct_rows + four_rows):
        raise DirectionV2AnalysisError("v2 validity equality gate failed")
    return clean, pairs, direct_rows, four_rows


def _historical_map(rows: list[dict[str, str]]) -> dict[tuple[str, str], float]:
    selected = [row for row in rows if row.get("stage") == "valid_face_emb_mean_token_l2_normalized" and row.get("attribute") in protocol.ATTRIBUTES]
    result = {}
    for row in selected:
        key = (row["attribute"], row["formal_pair_id"])
        try:
            value = float(row["margin"])
        except ValueError as error:
            raise DirectionV2AnalysisError("invalid historical margin") from error
        if key in result or not math.isfinite(value):
            raise DirectionV2AnalysisError("historical key or finiteness drift")
        result[key] = value
    if len(result) != 20:
        raise DirectionV2AnalysisError("historical pooled universe drift")
    return result


def analyze_transient(tensors: dict[str, dict[str, dict[str, Any]]], metadata: dict[str, dict[str, str]], historical_rows: list[dict[str, str]], *, expected_dim: int = protocol.LFE_DIM) -> dict[str, list[dict]]:
    torch = _torch()
    clean, pairs, direct_rows, four_rows = _clean_panel(tensors, metadata, expected_dim)
    pooled, normalized = {}, {}
    for unit in clean:
        pooled_copies, token_copies = [], []
        for seed_index in protocol.SEED_MAP:
            raw = clean[unit][seed_index]["D1"]
            vector = raw.mean(dim=0)
            pooled_copies.append(vector / torch.linalg.vector_norm(vector).clamp_min(1e-12))
            token_copies.append(raw / torch.linalg.vector_norm(raw, dim=1, keepdim=True).clamp_min(1e-12))
        pooled[unit] = torch.stack(pooled_copies).mean(dim=0)
        normalized[unit] = torch.stack(token_copies).mean(dim=0)
    pooled_rows, pooled_map = [], {}
    token_rows = []
    for attribute in protocol.ATTRIBUTES:
        pair_ids = sorted(pairs[attribute])
        for held in pair_ids:
            training = [pair for pair in pair_ids if pair != held]
            direction = torch.stack([pooled[pairs[attribute][pair]["positive"]] - pooled[pairs[attribute][pair]["control"]] for pair in training]).mean(dim=0)
            value = _margin(pooled[pairs[attribute][held]["positive"]], pooled[pairs[attribute][held]["control"]], direction)
            pooled_map[(attribute, held)] = value
            pooled_rows.append({"attribute": attribute, "formal_pair_id": held, "margin": value, "direction": _label(value)})
        for token_index in range(protocol.LFE_TOKENS):
            for held in pair_ids:
                training = [pair for pair in pair_ids if pair != held]
                direction = torch.stack([normalized[pairs[attribute][pair]["positive"]][token_index] - normalized[pairs[attribute][pair]["control"]][token_index] for pair in training]).mean(dim=0)
                value = _margin(normalized[pairs[attribute][held]["positive"]][token_index], normalized[pairs[attribute][held]["control"]][token_index], direction)
                token_rows.append({"attribute": attribute, "token_index": token_index, "formal_pair_id": held, "margin": value, "direction": _label(value)})
    if len(pooled_rows) != 20 or len(token_rows) != 640:
        raise DirectionV2AnalysisError("scientific family count drift")
    historical = _historical_map(historical_rows)
    historical_rows_out = []
    for key in sorted(pooled_map):
        current, frozen = pooled_map[key], historical[key]
        difference = abs(current - frozen)
        tolerance = 1e-6 + 1e-5 * max(abs(current), abs(frozen))
        current_label, frozen_label = _label(current), _label(frozen)
        historical_rows_out.append({"attribute": key[0], "formal_pair_id": key[1], "current_margin": current, "frozen_run_003_margin": frozen, "absolute_difference": difference, "tolerance": tolerance, "within_tolerance": difference <= tolerance, "current_direction": current_label, "frozen_direction": frozen_label, "sign_match": current_label == frozen_label})
    by_token, by_pair = defaultdict(list), defaultdict(list)
    for row in token_rows:
        by_token[(row["attribute"], row["token_index"])].append(row)
        by_pair[(row["attribute"], row["formal_pair_id"])].append(row)
    token_panel, pair_signs = [], []
    for (attribute, token_index), rows in sorted(by_token.items()):
        counts = Counter(row["direction"] for row in rows)
        token_panel.append({"attribute": attribute, "token_index": token_index, "pairs": 10, "correct_count": counts["correct"], "tie_count": counts["tie"], "wrong_count": counts["wrong"], **_summary([row["margin"] for row in rows])})
    for (attribute, pair), rows in sorted(by_pair.items()):
        counts = Counter(row["direction"] for row in rows)
        pair_signs.append({"attribute": attribute, "formal_pair_id": pair, "tokens": 32, "correct_count": counts["correct"], "tie_count": counts["tie"], "wrong_count": counts["wrong"], **_summary([row["margin"] for row in rows])})
    if len(token_panel) != 64 or len(pair_signs) != 20:
        raise DirectionV2AnalysisError("summary family count drift")
    return {"direct_controls": direct_rows, "four_label_controls": four_rows, "current_pooled": pooled_rows, "historical": historical_rows_out, "token_margins": token_rows, "token_panel": token_panel, "pair_signs": pair_signs}


def write_outputs(output_dir: Path, result: dict[str, list[dict]]) -> None:
    protocol.atomic_csv(output_dir / "same_input_direct_repeat_controls_v2.csv", DIRECT_FIELDS, result["direct_controls"])
    protocol.atomic_csv(output_dir / "four_label_lfe_equivalence_v2.csv", FOUR_FIELDS, result["four_label_controls"])
    protocol.atomic_csv(output_dir / "current_pooled_lfe_margins_v2.csv", POOLED_FIELDS, result["current_pooled"])
    protocol.atomic_csv(output_dir / "historical_run_003_comparison_v2.csv", HISTORICAL_FIELDS, result["historical"])
    protocol.atomic_csv(output_dir / "lfe_token_margins_v2.csv", TOKEN_FIELDS, result["token_margins"])
    protocol.atomic_csv(output_dir / "lfe_token_finite_panel_v2.csv", TOKEN_PANEL_FIELDS, result["token_panel"])
    protocol.atomic_csv(output_dir / "lfe_pair_token_signs_v2.csv", PAIR_FIELDS, result["pair_signs"])
