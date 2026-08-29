#!/usr/bin/env python3
"""Independent stdlib verifier for mechanism–outcome linkage v1."""
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
from typing import Sequence


REPO = Path(__file__).resolve().parents[1]
DRY_STATUS = "PASS_NO_WEIGHT_DRY_RUN_NO_REAL_INPUT_ACCESS"
EXECUTION_STATUS = "CPU_LINKAGE_EXECUTION_APPROVED"
PRIMARY_STAGE = "valid_face_emb_mean_token_l2_normalized"
ATTRIBUTES = ("eyeglasses", "facial_hair")
SECONDARY_STAGES = (
    "insightface_l2_normalized", "eva_head_l2_normalized",
    "eva_hidden_0_patch_mean_l2_normalized", "eva_hidden_1_patch_mean_l2_normalized",
    "eva_hidden_2_patch_mean_l2_normalized", "eva_hidden_3_patch_mean_l2_normalized",
    "eva_hidden_4_patch_mean_l2_normalized",
    "image_latent_first_frame_spatial_mean_l2_normalized",
)
BRANCHES = ("unconditional", "text")
GROUPS = ("early", "middle", "late")
SOURCE_NAMES = (
    "eyeglasses_outcome", "facial_hair_outcome",
    "representation_margins", "injection_pair_grid",
)
OUTPUT_HEADERS = {
    "primary_joined_pairs_v1.csv": [
        "attribute", "formal_pair_id", "outcome", "mechanism_stage", "mechanism_margin",
    ],
    "secondary_representation_joined_pairs_v1.csv": [
        "attribute", "formal_pair_id", "outcome", "mechanism_stage", "mechanism_margin",
    ],
    "secondary_injection_joined_pairs_v1.csv": [
        "attribute", "formal_pair_id", "outcome", "cfg_branch", "block_group",
        "denoising_group", "positive_minus_control",
    ],
    "primary_associations_v1.csv": [
        "attribute", "mechanism_stage", "pairs", "spearman_rho", "defined", "role",
    ],
    "secondary_representation_associations_v1.csv": [
        "attribute", "mechanism_stage", "pairs", "spearman_rho", "defined", "role",
    ],
    "secondary_injection_associations_v1.csv": [
        "attribute", "cfg_branch", "block_group", "denoising_group", "pairs",
        "spearman_rho", "defined", "role",
    ],
}


class VerificationError(RuntimeError):
    """Raised on independent verification failure."""


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
        raise VerificationError(f"expected JSON object: {path}")
    return value


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise VerificationError(f"refusing to overwrite verification artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPO / path).resolve()


def ensure_cpu_only() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise VerificationError("CUDA_VISIBLE_DEVICES must be explicitly empty")
    forbidden = ("torch", "transformers", "diffusers", "consisid")
    loaded = [
        name for name in sys.modules
        if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)
    ]
    if loaded:
        raise VerificationError(f"forbidden ML modules imported: {sorted(loaded)[:5]}")


def verify_dry_run(summary_path: Path) -> dict:
    ensure_cpu_only()
    summary = read_json(summary_path)
    if summary.get("status") != DRY_STATUS:
        raise VerificationError("dry-run status mismatch")
    exact = {
        "planned_attributes": 2,
        "planned_pairs_per_attribute": 10,
        "planned_primary_coefficients": 2,
        "planned_secondary_representation_coefficients": 16,
        "planned_secondary_injection_coefficients": 36,
        "joined_rows_created": 0,
    }
    if any(summary.get(key) != value for key, value in exact.items()):
        raise VerificationError("dry-run planned-count mismatch")
    false_fields = (
        "real_input_paths_received", "input_files_opened", "association_computed",
        "model_modules_imported", "model_weights_loaded", "gpu_used", "network_used",
        "execution_authorized",
    )
    if any(summary.get(field) is not False for field in false_fields):
        raise VerificationError("dry-run reports a forbidden action")
    plan_path = resolve(summary["analysis_plan_path"])
    if not plan_path.is_file() or plan_path.is_symlink():
        raise VerificationError("dry-run plan path is missing or a symlink")
    if plan_path.stat().st_size != summary["analysis_plan_bytes"]:
        raise VerificationError("dry-run plan byte count mismatch")
    if sha256(plan_path) != summary["analysis_plan_sha256"]:
        raise VerificationError("dry-run plan SHA256 mismatch")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_NO_WEIGHT_DRY_RUN_VERIFICATION",
        "summary_path": str(summary_path.resolve()),
        "summary_bytes": summary_path.stat().st_size,
        "summary_sha256": sha256(summary_path),
        "real_inputs_opened": False,
        "joined_rows_created": 0,
        "association_computed": False,
        "model_loaded": False,
        "gpu_used": False,
    }


def average_ranks(values: Sequence[float]) -> list[float]:
    if not values or any(not math.isfinite(value) for value in values):
        raise VerificationError("ranking requires finite values")
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and values[order[end]] == values[order[index]]:
            end += 1
        rank = ((index + 1) + end) / 2.0
        for position in range(index, end):
            ranks[order[position]] = rank
        index = end
    return ranks


def spearman(values_x: Sequence[float], values_y: Sequence[float]) -> float | None:
    if len(values_x) != len(values_y) or not values_x:
        raise VerificationError("invalid Spearman vector lengths")
    ranks_x, ranks_y = average_ranks(values_x), average_ranks(values_y)
    mean_x, mean_y = statistics.fmean(ranks_x), statistics.fmean(ranks_y)
    centered_x = [value - mean_x for value in ranks_x]
    centered_y = [value - mean_y for value in ranks_y]
    denominator = math.sqrt(
        sum(value * value for value in centered_x) * sum(value * value for value in centered_y)
    )
    if denominator == 0.0:
        return None
    return sum(x * y for x, y in zip(centered_x, centered_y)) / denominator


def finite(row: dict[str, str], column: str, context: str) -> float:
    try:
        value = float(row[column])
    except (KeyError, TypeError, ValueError) as error:
        raise VerificationError(f"invalid {column} at {context}") from error
    if not math.isfinite(value):
        raise VerificationError(f"non-finite {column} at {context}")
    return value


def verify_binding(path: Path, binding: dict, label: str) -> None:
    if path != resolve(binding.get("path", "")):
        raise VerificationError(f"path mismatch for {label}")
    if not path.is_file() or path.is_symlink():
        raise VerificationError(f"invalid file for {label}")
    if path.stat().st_size != int(binding["bytes"]) or sha256(path) != binding["sha256"]:
        raise VerificationError(f"byte or SHA256 mismatch for {label}")


def read_bound_csv(binding: dict, label: str) -> list[dict[str, str]]:
    path = resolve(binding["path"])
    verify_binding(path, binding, label)
    header = binding.get("header")
    keys = binding.get("key_columns")
    expected = binding.get("expected_keys")
    if not isinstance(header, list) or not isinstance(keys, list) or not isinstance(expected, list):
        raise VerificationError(f"incomplete header/key binding for {label}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != header:
            raise VerificationError(f"header mismatch for {label}")
        rows = list(reader)
    actual = ["|".join(row[column] for column in keys) for row in rows]
    if len(actual) != len(set(actual)) or sorted(actual) != sorted(expected):
        raise VerificationError(f"key universe mismatch for {label}")
    return rows


def read_output_csv(run_dir: Path, name: str, expected_rows: int) -> list[dict[str, str]]:
    path = run_dir / name
    if not path.is_file() or path.is_symlink():
        raise VerificationError(f"missing or symlink output: {name}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != OUTPUT_HEADERS[name]:
            raise VerificationError(f"output header mismatch: {name}")
        rows = list(reader)
    if len(rows) != expected_rows:
        raise VerificationError(f"output row-count mismatch: {name}/{len(rows)}")
    return rows


def expected_source_values(
    source_rows: dict[str, list[dict[str, str]]], pairs: dict[str, tuple[str, ...]],
) -> tuple[dict[tuple[str, str], float], dict[tuple[str, str, str], float], dict[tuple[str, str, str, str, str], float]]:
    eye: dict[str, dict[int, float]] = defaultdict(dict)
    for row in source_rows["eyeglasses_outcome"]:
        if row.get("attribute", "eyeglasses") != "eyeglasses":
            raise VerificationError("unexpected eyeglasses-source attribute")
        pair, seed = row["formal_pair_id"], int(row["seed_index"])
        if pair not in pairs["eyeglasses"] or seed not in (1, 2, 3, 4) or seed in eye[pair]:
            raise VerificationError("eyeglasses source key mismatch")
        eye[pair][seed] = finite(row, "human_positive_minus_control", pair)
    outcomes: dict[tuple[str, str], float] = {}
    for pair in pairs["eyeglasses"]:
        if set(eye[pair]) != {1, 2, 3, 4}:
            raise VerificationError("eyeglasses four-seed requirement failed")
        outcomes[("eyeglasses", pair)] = statistics.fmean(eye[pair].values())
    hair = {}
    for row in source_rows["facial_hair_outcome"]:
        if row.get("attribute") == "facial_hair":
            pair = row["formal_pair_id"]
            if pair in hair:
                raise VerificationError("duplicate facial-hair pair")
            hair[pair] = finite(row, "primary_positive_minus_control", pair)
    if set(hair) != set(pairs["facial_hair"]):
        raise VerificationError("facial-hair pair universe mismatch")
    outcomes.update({("facial_hair", pair): value for pair, value in hair.items()})

    margins = {}
    for row in source_rows["representation_margins"]:
        key = (row["attribute"], row["stage"], row["formal_pair_id"])
        if key in margins:
            raise VerificationError("duplicate representation key")
        margins[key] = finite(row, "margin", "/".join(key))
    expected_margin_keys = {
        (attribute, stage, pair)
        for attribute in ATTRIBUTES for stage in (PRIMARY_STAGE,) + SECONDARY_STAGES
        for pair in pairs[attribute]
    }
    if set(margins) != expected_margin_keys:
        raise VerificationError("representation key universe mismatch")

    injections = {}
    for row in source_rows["injection_pair_grid"]:
        key = (
            row["attribute"], row["formal_pair_id"], row["cfg_branch"],
            row["block_group"], row["denoising_group"],
        )
        if key in injections:
            raise VerificationError("duplicate injection key")
        injections[key] = finite(row, "positive_minus_control", "/".join(key))
    expected_injection_keys = {
        (attribute, pair, branch, block, denoise)
        for attribute in ATTRIBUTES for pair in pairs[attribute]
        for branch in BRANCHES for block in GROUPS for denoise in GROUPS
    }
    if set(injections) != expected_injection_keys:
        raise VerificationError("injection key universe mismatch")
    return outcomes, margins, injections


def check_float(actual: str, expected: float, context: str) -> None:
    value = finite({"value": actual}, "value", context)
    if value != expected:
        raise VerificationError(f"numeric source/output mismatch at {context}")


def check_association_row(row: dict[str, str], expected: float | None, context: str) -> None:
    if row["pairs"] != "10":
        raise VerificationError(f"pair count mismatch at {context}")
    if expected is None:
        if row["defined"] != "False" or row["spearman_rho"] != "":
            raise VerificationError(f"undefined coefficient encoding mismatch at {context}")
    else:
        if row["defined"] != "True":
            raise VerificationError(f"defined coefficient flag mismatch at {context}")
        actual = finite(row, "spearman_rho", context)
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-15):
            raise VerificationError(f"Spearman mismatch at {context}")


def verify_result(authorization_path: Path, plan_path: Path, run_dir: Path) -> dict:
    ensure_cpu_only()
    authorization = read_json(authorization_path)
    if authorization.get("status") != EXECUTION_STATUS:
        raise VerificationError("formal CPU linkage execution is not authorized")
    authority = authorization.get("authority", {})
    for flag in ("formal_input_audit", "real_input_read", "input_join", "association_computation", "independent_verification"):
        if authority.get(flag) is not True:
            raise VerificationError(f"authorization flag not true: {flag}")
    if authority.get("model_loading") or authority.get("gpu_execution") or authority.get("network"):
        raise VerificationError("authorization permits forbidden capability")
    verify_binding(plan_path.resolve(), authorization["analysis_plan"], "analysis_plan")
    verify_binding(Path(__file__).resolve(), authorization["code"]["verifier"], "verifier")
    if run_dir.resolve() != resolve(authorization["output_dir"]):
        raise VerificationError("run directory authorization mismatch")
    plan = read_json(plan_path)
    pairs = {attribute: tuple(plan["planned_pair_ids"][attribute]) for attribute in ATTRIBUTES}
    if any(len(value) != 10 for value in pairs.values()):
        raise VerificationError("planned pair count mismatch")
    sources = authorization.get("sources", {})
    if set(sources) != set(SOURCE_NAMES):
        raise VerificationError("source binding universe mismatch")
    source_rows = {name: read_bound_csv(sources[name], name) for name in SOURCE_NAMES}
    outcomes, margins, injections = expected_source_values(source_rows, pairs)

    primary_pairs = read_output_csv(run_dir, "primary_joined_pairs_v1.csv", 20)
    secondary_pairs = read_output_csv(run_dir, "secondary_representation_joined_pairs_v1.csv", 160)
    injection_pairs = read_output_csv(run_dir, "secondary_injection_joined_pairs_v1.csv", 360)
    primary_assoc = read_output_csv(run_dir, "primary_associations_v1.csv", 2)
    secondary_assoc = read_output_csv(run_dir, "secondary_representation_associations_v1.csv", 16)
    injection_assoc = read_output_csv(run_dir, "secondary_injection_associations_v1.csv", 36)

    seen_representation = set()
    for row in primary_pairs + secondary_pairs:
        key = (row["attribute"], row["mechanism_stage"], row["formal_pair_id"])
        if key in seen_representation or key not in margins:
            raise VerificationError(f"joined representation key mismatch: {key}")
        seen_representation.add(key)
        check_float(row["outcome"], outcomes[(key[0], key[2])], f"outcome/{key}")
        check_float(row["mechanism_margin"], margins[key], f"margin/{key}")
    if set(margins) != seen_representation:
        raise VerificationError("joined representation universe incomplete")

    seen_injection = set()
    for row in injection_pairs:
        key = (
            row["attribute"], row["formal_pair_id"], row["cfg_branch"],
            row["block_group"], row["denoising_group"],
        )
        if key in seen_injection or key not in injections:
            raise VerificationError(f"joined injection key mismatch: {key}")
        seen_injection.add(key)
        check_float(row["outcome"], outcomes[(key[0], key[1])], f"outcome/{key}")
        check_float(row["positive_minus_control"], injections[key], f"injection/{key}")
    if set(injections) != seen_injection:
        raise VerificationError("joined injection universe incomplete")

    rep_assoc_by_key = {
        (row["attribute"], row["mechanism_stage"]): row
        for row in primary_assoc + secondary_assoc
    }
    if len(rep_assoc_by_key) != 18:
        raise VerificationError("representation association key mismatch")
    for attribute in ATTRIBUTES:
        outcome_values = [outcomes[(attribute, pair)] for pair in pairs[attribute]]
        for stage in (PRIMARY_STAGE,) + SECONDARY_STAGES:
            expected = spearman(
                outcome_values, [margins[(attribute, stage, pair)] for pair in pairs[attribute]],
            )
            row = rep_assoc_by_key[(attribute, stage)]
            expected_role = "primary" if stage == PRIMARY_STAGE else "secondary_complete_family"
            if row["role"] != expected_role:
                raise VerificationError("representation role mismatch")
            check_association_row(row, expected, f"representation/{attribute}/{stage}")

    injection_assoc_by_key = {
        (row["attribute"], row["cfg_branch"], row["block_group"], row["denoising_group"]): row
        for row in injection_assoc
    }
    if len(injection_assoc_by_key) != 36:
        raise VerificationError("injection association key mismatch")
    for attribute in ATTRIBUTES:
        outcome_values = [outcomes[(attribute, pair)] for pair in pairs[attribute]]
        for branch in BRANCHES:
            for block in GROUPS:
                for denoise in GROUPS:
                    expected = spearman(outcome_values, [
                        injections[(attribute, pair, branch, block, denoise)]
                        for pair in pairs[attribute]
                    ])
                    row = injection_assoc_by_key[(attribute, branch, block, denoise)]
                    if row["role"] != "secondary_complete_family":
                        raise VerificationError("injection role mismatch")
                    check_association_row(row, expected, f"injection/{attribute}/{branch}/{block}/{denoise}")

    summary = read_json(run_dir / "analysis_summary_v1.json")
    if summary.get("primary_coefficients") != 2 or summary.get("secondary_representation_coefficients") != 16 or summary.get("secondary_injection_coefficients") != 36:
        raise VerificationError("analysis summary count mismatch")
    if summary.get("p_values_computed") or summary.get("confidence_intervals_computed") or summary.get("cross_attribute_ranking"):
        raise VerificationError("analysis summary reports forbidden inference")
    files = sorted(path for path in run_dir.iterdir() if path.is_file())
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_FIXED_PANEL_LINKAGE_VERIFICATION",
        "verified_output_files": {path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in files},
        "primary_coefficients": 2,
        "secondary_representation_coefficients": 16,
        "secondary_injection_coefficients": 36,
        "p_values": False,
        "confidence_intervals": False,
        "cross_attribute_ranking": False,
        "model_loaded": False,
        "gpu_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run-summary", type=Path)
    parser.add_argument("--execution-authorization", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.dry_run_summary:
        if args.execution_authorization or args.plan or args.run_dir:
            raise VerificationError("dry-run verification cannot receive real execution paths")
        result = verify_dry_run(args.dry_run_summary)
    else:
        if not args.execution_authorization or not args.plan or not args.run_dir:
            raise VerificationError("result verification requires authorization, plan, and run directory")
        result = verify_result(args.execution_authorization, args.plan, args.run_dir)
    if args.output:
        atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
