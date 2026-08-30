#!/usr/bin/env python3
"""Outcome-blind token-index LFE directional analyzer v1.

Raw LFE tokens are accepted only as transient in-memory tensors. This module
writes pair-level margins and aggregate summaries, never token vectors.
"""
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


TOKEN_MARGIN_FIELDS = ("attribute", "token_index", "formal_pair_id", "margin", "direction")
TOKEN_PANEL_FIELDS = (
    "attribute", "token_index", "pairs", "correct_count", "tie_count", "wrong_count",
    "mean_margin", "median_margin", "minimum_margin", "maximum_margin",
)
PAIR_SIGN_FIELDS = (
    "attribute", "formal_pair_id", "tokens", "correct_count", "tie_count", "wrong_count",
    "mean_margin", "median_margin", "minimum_margin", "maximum_margin",
)
POOLED_FIELDS = (
    "attribute", "formal_pair_id", "reconstructed_margin", "frozen_run_003_margin",
    "absolute_difference", "within_tolerance", "direction",
)


class DirectionAnalysisError(RuntimeError):
    """Raised when a transient panel or fixed analysis rule is violated."""


def _torch():
    try:
        import torch
    except ImportError as error:
        raise DirectionAnalysisError("torch is required only for in-memory tensor analysis") from error
    return torch


def _label(value: float) -> str:
    if abs(value) <= protocol.TIE_THRESHOLD:
        return "tie"
    return "correct" if value > 0 else "wrong"


def _summary(values: list[float]) -> dict[str, float]:
    if not values or any(not math.isfinite(value) for value in values):
        raise DirectionAnalysisError("summary received empty or nonfinite values")
    return {
        "mean_margin": statistics.fmean(values),
        "median_margin": statistics.median(values),
        "minimum_margin": min(values),
        "maximum_margin": max(values),
    }


def _validate_panel(
    unit_tokens: dict[str, Any],
    metadata: dict[str, dict[str, str]],
    expected_dim: int,
) -> tuple[dict[str, Any], dict[str, dict[str, dict[str, str]]]]:
    torch = _torch()
    if set(unit_tokens) != set(metadata) or len(unit_tokens) != 40:
        raise DirectionAnalysisError("expected exactly 40 token-bearing formal units")
    cleaned: dict[str, Any] = {}
    pairs: dict[str, dict[str, dict[str, str]]] = {
        attribute: defaultdict(dict) for attribute in protocol.ATTRIBUTES
    }
    for unit, value in unit_tokens.items():
        tensor = value.detach().float().cpu()
        if tuple(tensor.shape) != (protocol.LFE_TOKENS, expected_dim):
            raise DirectionAnalysisError(f"unexpected LFE token shape for {unit}: {tuple(tensor.shape)}")
        if not bool(torch.isfinite(tensor).all()):
            raise DirectionAnalysisError(f"nonfinite LFE token for {unit}")
        meta = metadata[unit]
        attribute, pair, role = meta.get("attribute"), meta.get("formal_pair_id"), meta.get("role")
        if attribute not in protocol.ATTRIBUTES or role not in protocol.ROLES or not pair:
            raise DirectionAnalysisError(f"metadata drift for {unit}")
        if role in pairs[attribute][pair]:
            raise DirectionAnalysisError(f"duplicate pair role: {attribute}/{pair}/{role}")
        pairs[attribute][pair][role] = unit
        norms = torch.linalg.vector_norm(tensor, dim=-1, keepdim=True).clamp_min(1e-12)
        cleaned[unit] = tensor / norms
    for attribute in protocol.ATTRIBUTES:
        if len(pairs[attribute]) != 10:
            raise DirectionAnalysisError(f"expected ten pairs for {attribute}")
        if any(set(roles) != set(protocol.ROLES) for roles in pairs[attribute].values()):
            raise DirectionAnalysisError(f"incomplete matched pair for {attribute}")
    return cleaned, pairs


def _directional_margin(positive: Any, control: Any, direction: Any) -> float:
    torch = _torch()
    value = torch.dot(positive, direction) - torch.dot(control, direction)
    margin = float(value.item())
    if not math.isfinite(margin):
        raise DirectionAnalysisError("nonfinite directional margin")
    return margin


def _pooled_replication(
    raw_tokens: dict[str, Any],
    pairs: dict[str, dict[str, dict[str, str]]],
    frozen_rows: list[dict[str, str]] | None,
) -> list[dict]:
    torch = _torch()
    pooled = {}
    for unit, value in raw_tokens.items():
        vector = value.detach().float().cpu().mean(dim=0)
        pooled[unit] = vector / torch.linalg.vector_norm(vector).clamp_min(1e-12)
    expected = None
    if frozen_rows is not None:
        selected = [row for row in frozen_rows if row.get("stage") == "valid_face_emb_mean_token_l2_normalized"]
        expected = {(row["attribute"], row["formal_pair_id"]): float(row["margin"]) for row in selected}
        if len(selected) != 20 or len(expected) != 20:
            raise DirectionAnalysisError("frozen pooled-LFE margin universe drift")
    output = []
    for attribute in protocol.ATTRIBUTES:
        for held_pair in sorted(pairs[attribute]):
            training = [pair for pair in sorted(pairs[attribute]) if pair != held_pair]
            direction = torch.stack([
                pooled[pairs[attribute][pair]["positive"]]
                - pooled[pairs[attribute][pair]["control"]]
                for pair in training
            ]).mean(dim=0)
            margin = _directional_margin(
                pooled[pairs[attribute][held_pair]["positive"]],
                pooled[pairs[attribute][held_pair]["control"]],
                direction,
            )
            frozen = margin if expected is None else expected[(attribute, held_pair)]
            difference = abs(margin - frozen)
            tolerance = 1e-6 + 1e-5 * max(abs(margin), abs(frozen))
            within = difference <= tolerance
            if expected is not None and not within:
                raise DirectionAnalysisError(f"pooled run-003 replication mismatch: {attribute}/{held_pair}")
            output.append({
                "attribute": attribute,
                "formal_pair_id": held_pair,
                "reconstructed_margin": margin,
                "frozen_run_003_margin": frozen,
                "absolute_difference": difference,
                "within_tolerance": within,
                "direction": _label(margin),
            })
    return output


def analyze_transient_tokens(
    unit_tokens: dict[str, Any],
    metadata: dict[str, dict[str, str]],
    frozen_pooled_rows: list[dict[str, str]] | None = None,
    *,
    expected_dim: int = protocol.LFE_DIM,
) -> dict[str, list[dict]]:
    """Compute the fixed 640-margin family from transient CPU tensors."""
    torch = _torch()
    normalized, pairs = _validate_panel(unit_tokens, metadata, expected_dim)
    margins: list[dict] = []
    for attribute in protocol.ATTRIBUTES:
        for token_index in range(protocol.LFE_TOKENS):
            for held_pair in sorted(pairs[attribute]):
                training = [pair for pair in sorted(pairs[attribute]) if pair != held_pair]
                direction = torch.stack([
                    normalized[pairs[attribute][pair]["positive"]][token_index]
                    - normalized[pairs[attribute][pair]["control"]][token_index]
                    for pair in training
                ]).mean(dim=0)
                margin = _directional_margin(
                    normalized[pairs[attribute][held_pair]["positive"]][token_index],
                    normalized[pairs[attribute][held_pair]["control"]][token_index],
                    direction,
                )
                margins.append({
                    "attribute": attribute,
                    "token_index": token_index,
                    "formal_pair_id": held_pair,
                    "margin": margin,
                    "direction": _label(margin),
                })
    if len(margins) != 640:
        raise DirectionAnalysisError("primary margin family is not 640 rows")
    by_token: dict[tuple[str, int], list[dict]] = defaultdict(list)
    by_pair: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in margins:
        by_token[(row["attribute"], row["token_index"])].append(row)
        by_pair[(row["attribute"], row["formal_pair_id"])].append(row)
    token_panel = []
    for (attribute, token_index), rows in sorted(by_token.items()):
        if len(rows) != 10:
            raise DirectionAnalysisError("token panel is not ten pairs")
        counts = Counter(row["direction"] for row in rows)
        token_panel.append({
            "attribute": attribute,
            "token_index": token_index,
            "pairs": 10,
            "correct_count": counts["correct"],
            "tie_count": counts["tie"],
            "wrong_count": counts["wrong"],
            **_summary([row["margin"] for row in rows]),
        })
    pair_signs = []
    for (attribute, pair), rows in sorted(by_pair.items()):
        if len(rows) != protocol.LFE_TOKENS:
            raise DirectionAnalysisError("pair summary is not 32 tokens")
        counts = Counter(row["direction"] for row in rows)
        pair_signs.append({
            "attribute": attribute,
            "formal_pair_id": pair,
            "tokens": protocol.LFE_TOKENS,
            "correct_count": counts["correct"],
            "tie_count": counts["tie"],
            "wrong_count": counts["wrong"],
            **_summary([row["margin"] for row in rows]),
        })
    if len(token_panel) != 64 or len(pair_signs) != 20:
        raise DirectionAnalysisError("fixed summary family count mismatch")
    pooled = _pooled_replication(unit_tokens, pairs, frozen_pooled_rows)
    return {
        "token_margins": margins,
        "token_finite_panel": token_panel,
        "pair_token_signs": pair_signs,
        "pooled_replication": pooled,
    }


def write_outputs(output_dir: Path, result: dict[str, list[dict]]) -> dict:
    if output_dir.exists():
        raise DirectionAnalysisError("analysis output directory already exists")
    output_dir.mkdir(parents=True, exist_ok=False)
    protocol.atomic_csv(output_dir / "lfe_token_margins_v1.csv", TOKEN_MARGIN_FIELDS, result["token_margins"])
    protocol.atomic_csv(output_dir / "lfe_token_finite_panel_v1.csv", TOKEN_PANEL_FIELDS, result["token_finite_panel"])
    protocol.atomic_csv(output_dir / "lfe_pair_token_signs_v1.csv", PAIR_SIGN_FIELDS, result["pair_token_signs"])
    protocol.atomic_csv(output_dir / "pooled_lfe_replication_v1.csv", POOLED_FIELDS, result["pooled_replication"])
    summary = {
        "schema_version": 1,
        "status": "COMPLETE_TOKEN_DIRECTION_ANALYSIS_PENDING_INDEPENDENT_IN_MEMORY_VERIFICATION",
        "token_margin_rows": 640,
        "token_panel_rows": 64,
        "pair_token_sign_rows": 20,
        "pooled_replication_rows": 20,
        "raw_vectors_persisted": False,
        "outcomes_opened": False,
        "association_computed": False,
        "p_values": False,
        "confidence_intervals": False,
    }
    protocol.atomic_json(output_dir / "analysis_summary_v1.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run",), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = protocol.no_weight_dry_run(args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DirectionAnalysisError, protocol.DirectionProtocolError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
