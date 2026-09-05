#!/usr/bin/env python3
"""Complete-family analyzer for future, separately authorized intervention outcomes."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import controlled_lfe_projection_exchange_protocol_v1 as protocol


class ControlledInterventionAnalysisError(RuntimeError):
    """Raised on invalid labels, keys, or analysis authorization."""


REQUIRED_FIELDS = {
    "attribute", "formal_pair_id", "role", "condition", "seed", "frame_index",
    "final_label", "observability_reason",
}


def _label_value(attribute: str, label: str) -> float | None:
    if attribute == "eyeglasses":
        if label == "present":
            return 1.0
        if label == "absent":
            return 0.0
        if label == "U":
            return None
    elif attribute == "facial_hair":
        if label in {"1", "2"}:
            return 1.0
        if label == "0":
            return 0.0
        if label == "U":
            return None
    raise ControlledInterventionAnalysisError(f"invalid {attribute} final label: {label}")


def _effect(score: dict[tuple[str, str], float | None], role: str, left: str, right: str) -> float | None:
    a, b = score.get((role, left)), score.get((role, right))
    return None if a is None or b is None else a - b


def _role_aligned(score: dict[tuple[str, str], float | None], left: str, right: str) -> float | None:
    positive = _effect(score, "positive", left, right)
    control = _effect(score, "control", left, right)
    return None if positive is None or control is None else 0.5 * (control - positive)


def analyze_rows(rows: list[dict[str, object]]) -> dict:
    expected_keys = {
        (attribute, pair_id, role, condition, seed, frame)
        for attribute in protocol.ATTRIBUTES
        for pair_id in protocol.pair_ids(attribute)
        for role in protocol.ROLES
        for condition in protocol.CONDITIONS
        for seed in protocol.SEEDS
        for frame in protocol.FRAME_INDICES
    }
    observed: dict[tuple[str, str, str, str, int, int], list[tuple[str, str]]] = defaultdict(list)
    for index, row in enumerate(rows):
        if not REQUIRED_FIELDS.issubset(row):
            raise ControlledInterventionAnalysisError(f"missing fields at row {index}")
        try:
            attribute = str(row["attribute"])
            pair_id = str(row["formal_pair_id"])
            role = str(row["role"])
            condition = str(row["condition"])
            seed = int(row["seed"])
            frame = int(row["frame_index"])
        except (TypeError, ValueError) as error:
            raise ControlledInterventionAnalysisError(f"invalid key at row {index}") from error
        key = (attribute, pair_id, role, condition, seed, frame)
        if key not in expected_keys:
            raise ControlledInterventionAnalysisError(f"unexpected outcome key: {key}")
        label, reason = str(row["final_label"]), str(row["observability_reason"])
        _label_value(attribute, label)
        if label == "U" and not reason.strip():
            raise ControlledInterventionAnalysisError(f"U without reason: {key}")
        observed[key].append((label, reason))

    unit_rows: list[dict[str, object]] = []
    missingness: list[dict[str, object]] = []
    unit_scores: dict[tuple[str, str, str, str], float | None] = {}
    coverage: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for attribute in protocol.ATTRIBUTES:
        for pair_id in protocol.pair_ids(attribute):
            for role in protocol.ROLES:
                for condition in protocol.CONDITIONS:
                    keys = [
                        (attribute, pair_id, role, condition, seed, frame)
                        for seed in protocol.SEEDS for frame in protocol.FRAME_INDICES
                    ]
                    missing = sum(key not in observed for key in keys)
                    duplicates = sum(max(0, len(observed.get(key, ())) - 1) for key in keys)
                    values: list[float] = []
                    labels = Counter()
                    reasons = Counter()
                    for key in keys:
                        entries = observed.get(key, ())
                        if len(entries) != 1:
                            continue
                        label, reason = entries[0]
                        labels[label] += 1
                        if label == "U":
                            reasons[reason] += 1
                        value = _label_value(attribute, label)
                        if value is not None:
                            values.append(value)
                    complete_keys = missing == 0 and duplicates == 0
                    score = statistics.fmean(values) if complete_keys and values else None
                    key4 = (attribute, pair_id, role, condition)
                    unit_scores[key4] = score
                    unit_rows.append({
                        "attribute": attribute, "formal_pair_id": pair_id, "role": role,
                        "condition": condition, "planned_frame_states": 28,
                        "unique_frame_states": 28 - missing,
                        "missing_keys": missing, "duplicate_rows": duplicates,
                        "valid_labels": len(values), "unobservable_labels": labels["U"],
                        "present_fraction": score, "complete_keys": complete_keys,
                    })
                    coverage[(attribute, condition)].update(labels)
                    for reason, count in reasons.items():
                        coverage[(attribute, condition)][f"reason:{reason}"] += count
                    if not complete_keys or not values:
                        missingness.append({
                            "attribute": attribute, "formal_pair_id": pair_id, "role": role,
                            "condition": condition, "missing_keys": missing,
                            "duplicate_rows": duplicates, "zero_valid_labels": not values,
                            "action": "RETAIN_MISSING_AND_WITHHOLD_REDUCED_PANEL_AGGREGATE",
                        })

    pair_rows: list[dict[str, object]] = []
    for attribute in protocol.ATTRIBUTES:
        for pair_id in protocol.pair_ids(attribute):
            scores = {
                (role, condition): unit_scores[(attribute, pair_id, role, condition)]
                for role in protocol.ROLES for condition in protocol.CONDITIONS
            }
            complete_pair = all(value is not None for value in scores.values())
            primary = (
                _role_aligned(scores, "target_projection_exchange", "orthogonal_sham")
                if complete_pair else None
            )
            pair_rows.append({
                "attribute": attribute, "formal_pair_id": pair_id,
                "positive_target_minus_sham": _effect(scores, "positive", "target_projection_exchange", "orthogonal_sham"),
                "control_target_minus_sham": _effect(scores, "control", "target_projection_exchange", "orthogonal_sham"),
                "primary_role_aligned_target_minus_sham": primary,
                "secondary_role_aligned_target_minus_baseline": _role_aligned(scores, "target_projection_exchange", "baseline"),
                "secondary_role_aligned_sham_minus_baseline": _role_aligned(scores, "orthogonal_sham", "baseline"),
                "primary_direction": None if primary is None else (
                    "tie" if abs(primary) <= protocol.TIE_THRESHOLD else "correct" if primary > 0 else "wrong"
                ),
                "complete_primary": complete_pair and primary is not None,
            })

    attribute_rows: list[dict[str, object]] = []
    for attribute in protocol.ATTRIBUTES:
        selected = [row for row in pair_rows if row["attribute"] == attribute]
        values = [float(row["primary_role_aligned_target_minus_sham"]) for row in selected if row["complete_primary"]]
        if len(values) == 10:
            labels = Counter(str(row["primary_direction"]) for row in selected)
            attribute_rows.append({
                "attribute": attribute, "pairs_planned": 10, "pairs_complete": 10,
                "aggregate_computed": True, "correct_count": labels["correct"],
                "tie_count": labels["tie"], "wrong_count": labels["wrong"],
                "mean": statistics.fmean(values), "median": statistics.median(values),
                "minimum": min(values), "maximum": max(values),
                "p_values_or_confidence_intervals_computed": False,
            })
        else:
            attribute_rows.append({
                "attribute": attribute, "pairs_planned": 10, "pairs_complete": len(values),
                "aggregate_computed": False, "correct_count": None, "tie_count": None,
                "wrong_count": None, "mean": None, "median": None, "minimum": None,
                "maximum": None, "p_values_or_confidence_intervals_computed": False,
            })

    coverage_rows = []
    for attribute in protocol.ATTRIBUTES:
        for condition in protocol.CONDITIONS:
            counts = coverage[(attribute, condition)]
            row: dict[str, object] = {
                "attribute": attribute, "condition": condition,
                "planned_frame_states": 560,
                "valid_labels": sum(counts[label] for label in (("present", "absent") if attribute == "eyeglasses" else ("0", "1", "2"))),
                "unobservable_labels": counts["U"],
            }
            row["label_counts"] = {key: counts[key] for key in (("present", "absent", "U") if attribute == "eyeglasses" else ("0", "1", "2", "U"))}
            row["unobservable_reasons"] = {key[7:]: value for key, value in sorted(counts.items()) if key.startswith("reason:")}
            coverage_rows.append(row)

    return {
        "schema_version": 1,
        "status": "COMPLETE_FIXED_PANEL_ANALYSIS" if not missingness else "INCOMPLETE_FIXED_PANEL_AGGREGATES_WITHHELD",
        "input_rows": len(rows), "expected_unique_frame_states": 3360,
        "unexpected_keys": 0, "unit_condition_scores": unit_rows,
        "pair_effects": pair_rows, "attribute_summaries": attribute_rows,
        "coverage_by_attribute_condition": coverage_rows, "missingness_ledger": missingness,
        "p_values_computed": False, "confidence_intervals_computed": False,
        "cross_attribute_pooling_or_ranking_computed": False,
    }


def write_outputs(output: Path, result: dict) -> None:
    protocol.atomic_json(output / "controlled_intervention_analysis_v1.json", result)


def _validate_future_analysis_authority(path: Path) -> None:
    auth = protocol.read_json(path)
    if auth.get("status") != "CONTROLLED_INTERVENTION_ANALYSIS_AUTHORIZED":
        raise ControlledInterventionAnalysisError("formal intervention analysis lacks separate authorization")
    if auth.get("outcome_access_explicitly_approved") is not True:
        raise ControlledInterventionAnalysisError("outcome access is not explicitly approved")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    _validate_future_analysis_authority(args.authorization_file)
    rows = protocol.read_csv(args.input)
    result = analyze_rows(rows)
    write_outputs(args.output_dir, result)
    print(json.dumps({"status": result["status"], "input_rows": result["input_rows"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ControlledInterventionAnalysisError, protocol.ControlledInterventionProtocolError, KeyError, ValueError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
