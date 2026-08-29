#!/usr/bin/env python3
"""Fail-closed CPU-only mechanism–outcome linkage implementation v1.

The default permitted mode is a no-weight dry-run that opens only the approved
plan. Real inputs cannot be opened unless a later execution authorization
explicitly enables input audit, real input reads, joining, and association
computation and binds every relevant path, byte count, SHA256, and CSV header.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence


REPO = Path(__file__).resolve().parents[1]
APPROVED_PLAN_STATUS = "APPROVED_DESIGN_IMPLEMENTATION_ONLY_EXECUTION_NOT_AUTHORIZED"
EXECUTION_STATUS = "CPU_LINKAGE_EXECUTION_APPROVED"
PRIMARY_STAGE = "valid_face_emb_mean_token_l2_normalized"
ATTRIBUTES = ("eyeglasses", "facial_hair")
SECONDARY_STAGES = (
    "insightface_l2_normalized",
    "eva_head_l2_normalized",
    "eva_hidden_0_patch_mean_l2_normalized",
    "eva_hidden_1_patch_mean_l2_normalized",
    "eva_hidden_2_patch_mean_l2_normalized",
    "eva_hidden_3_patch_mean_l2_normalized",
    "eva_hidden_4_patch_mean_l2_normalized",
    "image_latent_first_frame_spatial_mean_l2_normalized",
)
BRANCHES = ("unconditional", "text")
GROUPS = ("early", "middle", "late")
SOURCE_NAMES = (
    "eyeglasses_outcome",
    "facial_hair_outcome",
    "representation_margins",
    "injection_pair_grid",
)
PAIR_COLUMNS = (
    "attribute", "formal_pair_id", "outcome", "mechanism_stage", "mechanism_margin",
)
INJECTION_PAIR_COLUMNS = (
    "attribute", "formal_pair_id", "outcome", "cfg_branch", "block_group",
    "denoising_group", "positive_minus_control",
)
ASSOCIATION_COLUMNS = (
    "attribute", "mechanism_stage", "pairs", "spearman_rho", "defined", "role",
)
INJECTION_ASSOCIATION_COLUMNS = (
    "attribute", "cfg_branch", "block_group", "denoising_group", "pairs",
    "spearman_rho", "defined", "role",
)
FORBIDDEN_MODULE_PREFIXES = ("torch", "transformers", "diffusers", "consisid")
FROZEN_RUNTIME_ROOTS = (
    Path("/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003"),
    Path("/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003_analysis_v1"),
)


class LinkageError(RuntimeError):
    """Raised when a prospective or execution-time invariant fails."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise LinkageError(f"expected JSON object: {path}")
    return value


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise LinkageError(f"refusing to overwrite artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def atomic_csv(path: Path, columns: Sequence[str], rows: Iterable[dict]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise LinkageError(f"refusing to overwrite artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in columns})
    temporary.replace(path)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPO / path).resolve()


def ensure_cpu_only() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise LinkageError("CUDA_VISIBLE_DEVICES must be explicitly empty")
    loaded = sorted(
        name for name in sys.modules
        if any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_MODULE_PREFIXES)
    )
    if loaded:
        raise LinkageError(f"forbidden ML modules already imported: {loaded[:5]}")


def planned_pairs(plan: dict) -> dict[str, tuple[str, ...]]:
    if plan.get("status") != APPROVED_PLAN_STATUS:
        raise LinkageError("approved analysis-plan status mismatch")
    if tuple(plan.get("attributes", [])) != ATTRIBUTES:
        raise LinkageError("attribute order or universe drift")
    result = {
        attribute: tuple(plan["planned_pair_ids"][attribute]) for attribute in ATTRIBUTES
    }
    if any(len(values) != 10 or len(set(values)) != 10 for values in result.values()):
        raise LinkageError("each attribute must contain ten unique planned pair IDs")
    if plan["primary_mechanism_variable"]["stage"] != PRIMARY_STAGE:
        raise LinkageError("primary pooled-LFE stage drift")
    if tuple(plan["secondary_representation_stages"]) != SECONDARY_STAGES:
        raise LinkageError("secondary representation family drift")
    injection = plan["secondary_injection_family"]
    if tuple(injection["cfg_branches"]) != BRANCHES:
        raise LinkageError("CFG branch universe drift")
    if tuple(injection["block_groups"]) != GROUPS or tuple(injection["denoising_groups"]) != GROUPS:
        raise LinkageError("injection grid universe drift")
    association = plan["association"]
    if association["method"] != "spearman_rank_correlation" or association["ties"] != "average_ranks":
        raise LinkageError("primary association definition drift")
    if association["p_values"] or association["confidence_intervals"] or association["reduced_panel_if_missing"]:
        raise LinkageError("forbidden inferential or reduced-panel setting")
    return result


def no_weight_dry_run(plan_path: Path, output_path: Path) -> dict:
    ensure_cpu_only()
    plan = read_json(plan_path)
    pairs = planned_pairs(plan)
    result = {
        "schema_version": 1,
        "status": "PASS_NO_WEIGHT_DRY_RUN_NO_REAL_INPUT_ACCESS",
        "analysis_plan_path": str(plan_path.resolve()),
        "analysis_plan_bytes": plan_path.stat().st_size,
        "analysis_plan_sha256": sha256(plan_path),
        "planned_attributes": len(pairs),
        "planned_pairs_per_attribute": 10,
        "planned_primary_coefficients": 2,
        "planned_secondary_representation_coefficients": 16,
        "planned_secondary_injection_coefficients": 36,
        "real_input_paths_received": False,
        "input_files_opened": False,
        "joined_rows_created": 0,
        "association_computed": False,
        "model_modules_imported": False,
        "model_weights_loaded": False,
        "gpu_used": False,
        "network_used": False,
        "execution_authorized": False,
    }
    atomic_json(output_path, result)
    return result


def average_ranks(values: Sequence[float]) -> list[float]:
    if not values or any(not math.isfinite(value) for value in values):
        raise LinkageError("ranking requires a nonempty finite vector")
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = ((start + 1) + end) / 2.0
        for position in range(start, end):
            ranks[order[position]] = rank
        start = end
    return ranks


def spearman(values_x: Sequence[float], values_y: Sequence[float]) -> float | None:
    if len(values_x) != len(values_y) or not values_x:
        raise LinkageError("Spearman vectors must have equal nonzero length")
    ranks_x = average_ranks(values_x)
    ranks_y = average_ranks(values_y)
    mean_x = statistics.fmean(ranks_x)
    mean_y = statistics.fmean(ranks_y)
    centered_x = [value - mean_x for value in ranks_x]
    centered_y = [value - mean_y for value in ranks_y]
    denominator = math.sqrt(
        sum(value * value for value in centered_x) * sum(value * value for value in centered_y)
    )
    if denominator == 0.0:
        return None
    return sum(x * y for x, y in zip(centered_x, centered_y)) / denominator


def finite_number(row: dict[str, str], column: str, context: str) -> float:
    try:
        value = float(row[column])
    except (KeyError, TypeError, ValueError) as error:
        raise LinkageError(f"invalid numeric {column} at {context}") from error
    if not math.isfinite(value):
        raise LinkageError(f"non-finite numeric {column} at {context}")
    return value


def verify_bound_file(path: Path, binding: dict, label: str) -> None:
    if path != resolve(binding["path"]):
        raise LinkageError(f"authorized path mismatch for {label}")
    if not path.is_file() or path.is_symlink():
        raise LinkageError(f"missing, non-file, or symlink input for {label}: {path}")
    if path.stat().st_size != int(binding["bytes"]):
        raise LinkageError(f"byte mismatch for {label}")
    if sha256(path) != binding["sha256"]:
        raise LinkageError(f"SHA256 mismatch for {label}")


def read_bound_csv(binding: dict, label: str) -> list[dict[str, str]]:
    path = resolve(binding["path"])
    verify_bound_file(path, binding, label)
    expected_header = binding.get("header")
    if not isinstance(expected_header, list) or not expected_header:
        raise LinkageError(f"authorization lacks exact CSV header for {label}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_header:
            raise LinkageError(f"CSV header mismatch for {label}")
        rows = list(reader)
    key_columns = binding.get("key_columns")
    expected_keys = binding.get("expected_keys")
    if not isinstance(key_columns, list) or not key_columns or not isinstance(expected_keys, list):
        raise LinkageError(f"authorization lacks exact key binding for {label}")
    actual_keys = ["|".join(row[column] for column in key_columns) for row in rows]
    if len(actual_keys) != len(set(actual_keys)):
        raise LinkageError(f"duplicate source key for {label}")
    if sorted(actual_keys) != sorted(expected_keys):
        raise LinkageError(f"exact source key universe mismatch for {label}")
    return rows


def extract_outcomes(
    eye_rows: list[dict[str, str]], hair_rows: list[dict[str, str]],
    pairs: dict[str, tuple[str, ...]],
) -> dict[tuple[str, str], float]:
    eye_values: dict[str, dict[int, float]] = defaultdict(dict)
    for row in eye_rows:
        attribute = row.get("attribute", "eyeglasses")
        if attribute != "eyeglasses":
            raise LinkageError("unexpected attribute in eyeglasses outcome source")
        pair = row["formal_pair_id"]
        if pair not in pairs["eyeglasses"]:
            raise LinkageError(f"unexpected eyeglasses pair: {pair}")
        try:
            seed_index = int(row["seed_index"])
        except (KeyError, ValueError) as error:
            raise LinkageError(f"invalid eyeglasses seed index for {pair}") from error
        if seed_index not in (1, 2, 3, 4) or seed_index in eye_values[pair]:
            raise LinkageError(f"duplicate or unexpected eyeglasses seed for {pair}")
        eye_values[pair][seed_index] = finite_number(
            row, "human_positive_minus_control", f"eyeglasses/{pair}/seed-{seed_index}"
        )
    if set(eye_values) != set(pairs["eyeglasses"]):
        raise LinkageError("eyeglasses pair universe mismatch")
    outcomes = {}
    for pair in pairs["eyeglasses"]:
        if set(eye_values[pair]) != {1, 2, 3, 4}:
            raise LinkageError(f"eyeglasses requires four frozen seeds: {pair}")
        outcomes[("eyeglasses", pair)] = statistics.fmean(eye_values[pair].values())

    hair_values: dict[str, float] = {}
    for row in hair_rows:
        attribute = row.get("attribute")
        if attribute not in ATTRIBUTES:
            raise LinkageError(f"unexpected attribute in facial-hair source: {attribute}")
        if attribute != "facial_hair":
            continue
        pair = row["formal_pair_id"]
        if pair not in pairs["facial_hair"] or pair in hair_values:
            raise LinkageError(f"duplicate or unexpected facial-hair pair: {pair}")
        hair_values[pair] = finite_number(
            row, "primary_positive_minus_control", f"facial_hair/{pair}"
        )
    if set(hair_values) != set(pairs["facial_hair"]):
        raise LinkageError("facial-hair pair universe mismatch")
    outcomes.update({("facial_hair", pair): value for pair, value in hair_values.items()})
    return outcomes


def extract_representation_rows(
    rows: list[dict[str, str]], outcomes: dict[tuple[str, str], float],
    pairs: dict[str, tuple[str, ...]],
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    expected_stages = (PRIMARY_STAGE,) + SECONDARY_STAGES
    margins: dict[tuple[str, str, str], float] = {}
    for row in rows:
        key = (row["attribute"], row["stage"], row["formal_pair_id"])
        attribute, stage, pair = key
        if attribute not in ATTRIBUTES or stage not in expected_stages or pair not in pairs[attribute]:
            raise LinkageError(f"unexpected representation key: {key}")
        if key in margins:
            raise LinkageError(f"duplicate representation key: {key}")
        margins[key] = finite_number(row, "margin", "/".join(key))
    expected = {
        (attribute, stage, pair)
        for attribute in ATTRIBUTES for stage in expected_stages for pair in pairs[attribute]
    }
    if set(margins) != expected:
        raise LinkageError("representation key universe mismatch")

    primary_pairs: list[dict] = []
    secondary_pairs: list[dict] = []
    primary_associations: list[dict] = []
    secondary_associations: list[dict] = []
    for attribute in ATTRIBUTES:
        ordered_pairs = pairs[attribute]
        outcome_values = [outcomes[(attribute, pair)] for pair in ordered_pairs]
        for stage in expected_stages:
            mechanism_values = [margins[(attribute, stage, pair)] for pair in ordered_pairs]
            joined = [{
                "attribute": attribute,
                "formal_pair_id": pair,
                "outcome": outcomes[(attribute, pair)],
                "mechanism_stage": stage,
                "mechanism_margin": margins[(attribute, stage, pair)],
            } for pair in ordered_pairs]
            rho = spearman(outcome_values, mechanism_values)
            association = {
                "attribute": attribute,
                "mechanism_stage": stage,
                "pairs": 10,
                "spearman_rho": "" if rho is None else rho,
                "defined": rho is not None,
                "role": "primary" if stage == PRIMARY_STAGE else "secondary_complete_family",
            }
            if stage == PRIMARY_STAGE:
                primary_pairs.extend(joined)
                primary_associations.append(association)
            else:
                secondary_pairs.extend(joined)
                secondary_associations.append(association)
    return primary_pairs, secondary_pairs, primary_associations, secondary_associations


def extract_injection_rows(
    rows: list[dict[str, str]], outcomes: dict[tuple[str, str], float],
    pairs: dict[str, tuple[str, ...]],
) -> tuple[list[dict], list[dict]]:
    values: dict[tuple[str, str, str, str, str], float] = {}
    for row in rows:
        key = (
            row["attribute"], row["formal_pair_id"], row["cfg_branch"],
            row["block_group"], row["denoising_group"],
        )
        attribute, pair, branch, block, denoise = key
        if (
            attribute not in ATTRIBUTES or pair not in pairs[attribute]
            or branch not in BRANCHES or block not in GROUPS or denoise not in GROUPS
        ):
            raise LinkageError(f"unexpected injection key: {key}")
        if key in values:
            raise LinkageError(f"duplicate injection key: {key}")
        values[key] = finite_number(row, "positive_minus_control", "/".join(key))
    expected = {
        (attribute, pair, branch, block, denoise)
        for attribute in ATTRIBUTES for pair in pairs[attribute]
        for branch in BRANCHES for block in GROUPS for denoise in GROUPS
    }
    if set(values) != expected:
        raise LinkageError("injection key universe mismatch")

    joined_rows: list[dict] = []
    associations: list[dict] = []
    for attribute in ATTRIBUTES:
        ordered_pairs = pairs[attribute]
        outcome_values = [outcomes[(attribute, pair)] for pair in ordered_pairs]
        for branch in BRANCHES:
            for block in GROUPS:
                for denoise in GROUPS:
                    mechanism_values = [
                        values[(attribute, pair, branch, block, denoise)] for pair in ordered_pairs
                    ]
                    joined_rows.extend({
                        "attribute": attribute,
                        "formal_pair_id": pair,
                        "outcome": outcomes[(attribute, pair)],
                        "cfg_branch": branch,
                        "block_group": block,
                        "denoising_group": denoise,
                        "positive_minus_control": values[(attribute, pair, branch, block, denoise)],
                    } for pair in ordered_pairs)
                    rho = spearman(outcome_values, mechanism_values)
                    associations.append({
                        "attribute": attribute,
                        "cfg_branch": branch,
                        "block_group": block,
                        "denoising_group": denoise,
                        "pairs": 10,
                        "spearman_rho": "" if rho is None else rho,
                        "defined": rho is not None,
                        "role": "secondary_complete_family",
                    })
    return joined_rows, associations


def validate_execution_authorization(
    authorization_path: Path, plan_path: Path, output_dir: Path,
) -> tuple[dict, dict[str, dict]]:
    ensure_cpu_only()
    authorization = read_json(authorization_path)
    if authorization.get("status") != EXECUTION_STATUS:
        raise LinkageError("formal CPU linkage execution is not authorized")
    authority = authorization.get("authority", {})
    required = (
        "formal_input_audit", "real_input_read", "input_join",
        "association_computation", "independent_verification",
    )
    if any(authority.get(name) is not True for name in required):
        raise LinkageError("execution authorization lacks a required explicit authority flag")
    if authority.get("model_loading") or authority.get("gpu_execution") or authority.get("network"):
        raise LinkageError("execution authorization permits a forbidden capability")

    plan_binding = authorization.get("analysis_plan", {})
    verify_bound_file(plan_path.resolve(), plan_binding, "analysis_plan")
    code_binding = authorization.get("code", {}).get("analyzer", {})
    verify_bound_file(Path(__file__).resolve(), code_binding, "analyzer")
    authorized_output = resolve(authorization.get("output_dir", ""))
    if output_dir.resolve() != authorized_output:
        raise LinkageError("output directory does not match execution authorization")
    if REPO == authorized_output or REPO in authorized_output.parents:
        raise LinkageError("linkage output directory must remain external to Git")
    if any(root == authorized_output or root in authorized_output.parents for root in FROZEN_RUNTIME_ROOTS):
        raise LinkageError("refusing output inside a frozen Phase-S directory")
    if output_dir.exists():
        raise LinkageError("authorized output directory already exists")
    sources = authorization.get("sources", {})
    if set(sources) != set(SOURCE_NAMES):
        raise LinkageError("execution authorization source universe mismatch")
    return authorization, sources


def run_authorized(authorization_path: Path, plan_path: Path, output_dir: Path) -> dict:
    _, sources = validate_execution_authorization(authorization_path, plan_path, output_dir)
    plan = read_json(plan_path)
    pairs = planned_pairs(plan)
    source_rows = {name: read_bound_csv(sources[name], name) for name in SOURCE_NAMES}
    outcomes = extract_outcomes(
        source_rows["eyeglasses_outcome"], source_rows["facial_hair_outcome"], pairs,
    )
    primary_pairs, secondary_pairs, primary_assoc, secondary_assoc = extract_representation_rows(
        source_rows["representation_margins"], outcomes, pairs,
    )
    injection_pairs, injection_assoc = extract_injection_rows(
        source_rows["injection_pair_grid"], outcomes, pairs,
    )
    if tuple(map(len, (primary_pairs, secondary_pairs, injection_pairs))) != (20, 160, 360):
        raise LinkageError("joined output row-count invariant failed")
    if tuple(map(len, (primary_assoc, secondary_assoc, injection_assoc))) != (2, 16, 36):
        raise LinkageError("association output row-count invariant failed")

    output_dir.mkdir(parents=True, exist_ok=False)
    outputs = {
        "primary_joined_pairs_v1.csv": (PAIR_COLUMNS, primary_pairs),
        "secondary_representation_joined_pairs_v1.csv": (PAIR_COLUMNS, secondary_pairs),
        "secondary_injection_joined_pairs_v1.csv": (INJECTION_PAIR_COLUMNS, injection_pairs),
        "primary_associations_v1.csv": (ASSOCIATION_COLUMNS, primary_assoc),
        "secondary_representation_associations_v1.csv": (ASSOCIATION_COLUMNS, secondary_assoc),
        "secondary_injection_associations_v1.csv": (INJECTION_ASSOCIATION_COLUMNS, injection_assoc),
    }
    for name, (columns, rows) in outputs.items():
        atomic_csv(output_dir / name, columns, rows)
    summary = {
        "schema_version": 1,
        "status": "COMPLETE_FIXED_PANEL_DESCRIPTIVE_ASSOCIATIONS_PENDING_INDEPENDENT_VERIFICATION",
        "attributes_separate": True,
        "pairs_per_attribute": 10,
        "primary_coefficients": 2,
        "secondary_representation_coefficients": 16,
        "secondary_injection_coefficients": 36,
        "p_values_computed": False,
        "confidence_intervals_computed": False,
        "cross_attribute_ranking": False,
        "fallback_policy": "UNMAPPED_RUN_LEVEL_LIMITATION_NO_ASSIGNMENT_EXCLUSION_OR_RERUN",
        "joined_pair_tables": "EXTERNAL_ONLY",
        "claim_boundary": (
            "Fixed-panel descriptive co-variation only; no causal, population, model-wide, "
            "frame-independent, localization, route necessity/sufficiency, or cross-attribute conclusion."
        ),
    }
    atomic_json(output_dir / "analysis_summary_v1.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dry-run-output", type=Path)
    parser.add_argument("--execution-authorization", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.dry_run:
        if args.execution_authorization or args.output_dir or not args.dry_run_output:
            raise LinkageError("dry-run accepts only --plan and --dry-run-output")
        result = no_weight_dry_run(args.plan, args.dry_run_output)
    else:
        if args.dry_run_output or not args.execution_authorization or not args.output_dir:
            raise LinkageError("formal mode requires authorization and output directory")
        result = run_authorized(args.execution_authorization, args.plan, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LinkageError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
