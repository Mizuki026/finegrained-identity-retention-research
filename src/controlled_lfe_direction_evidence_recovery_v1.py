#!/usr/bin/env python3
"""Scalar-only reconstruction helpers for direction-evidence recovery."""
from __future__ import annotations

from typing import Any

import controlled_lfe_projection_exchange_protocol_v1 as protocol
from controlled_lfe_projection_exchange_instrumentation_v1 import (
    build_transient_interventions,
    tensor_scalar_sha256,
)


class DirectionEvidenceRecoveryError(RuntimeError):
    """Raised before direction evidence can be treated as recovered."""


def recover_scalar_hash_rows(
    tensors: dict[str, Any], metadata: dict[str, dict[str, str]], expected_lfe_hashes: dict[str, str],
    *, expected_dim: int = protocol.LFE_DIM,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if set(tensors) != set(expected_lfe_hashes) or len(tensors) != 40:
        raise DirectionEvidenceRecoveryError("recovery requires exactly 40 expected-hash-bound LFE tensors")
    acquisition_rows = []
    for unit in sorted(tensors):
        observed = tensor_scalar_sha256(tensors[unit])
        expected = expected_lfe_hashes[unit]
        acquisition_rows.append({
            "planned_unit_id": unit, "expected_lfe_sha256": expected,
            "recovered_lfe_sha256": observed, "exact_match": observed == expected,
        })
    if not all(bool(row["exact_match"]) for row in acquisition_rows):
        raise DirectionEvidenceRecoveryError("recovered acquisition LFE hashes are not exactly 40/40 identical")
    bundle = build_transient_interventions(tensors, metadata, expected_dim=expected_dim)
    direction_rows = []
    for diagnostic in bundle.diagnostics:
        key = (
            str(diagnostic["attribute"]), str(diagnostic["formal_pair_id"]),
            int(diagnostic["token_index"]),
        )
        direction_rows.append({
            "attribute": key[0], "formal_pair_id": key[1], "token_index": key[2],
            "direction_sha256": tensor_scalar_sha256(bundle.directions[key]),
            "sham_direction_sha256": tensor_scalar_sha256(bundle.sham_directions[key]),
        })
    if len(direction_rows) != 640:
        raise DirectionEvidenceRecoveryError("recovered direction hash family is not exactly 640")
    return acquisition_rows, direction_rows
