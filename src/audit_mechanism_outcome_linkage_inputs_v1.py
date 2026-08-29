#!/usr/bin/env python3
"""CPU-only, one-source-at-a-time formal input audit for linkage v1.

This program never accepts more than one source name per invocation. It audits
schema, keys, duplicates, missing fields, and finite target numeric values, but
does not construct outcomes, compare sources, join rows, or compute any
association.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import stat
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
AUTH_STATUS = "CPU_ONLY_FORMAL_INPUT_AUDIT_APPROVED"
ATTRIBUTES = ("eyeglasses", "facial_hair")
PRIMARY_STAGE = "valid_face_emb_mean_token_l2_normalized"
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


class AuditError(RuntimeError):
    pass


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
        raise AuditError(f"expected JSON object: {path}")
    return value


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise AuditError(f"refusing to overwrite audit artifact: {path}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def atomic_keys(path: Path, keys: list[str]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise AuditError(f"refusing to overwrite key manifest: {path}")
    with temporary.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("key_index", "key"), lineterminator="\n")
        writer.writeheader()
        for index, key in enumerate(keys, start=1):
            writer.writerow({"key_index": index, "key": key})
    temporary.replace(path)


def ensure_cpu_offline() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise AuditError("CUDA_VISIBLE_DEVICES must be explicitly empty")
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        if os.environ.get(name) != "1":
            raise AuditError(f"{name} must be 1")
    forbidden = ("torch", "transformers", "diffusers", "consisid")
    loaded = [
        name for name in sys.modules
        if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)
    ]
    if loaded:
        raise AuditError(f"forbidden ML module imported: {sorted(loaded)[:5]}")


def pair_ids(attribute: str) -> tuple[str, ...]:
    prefix = "FEY" if attribute == "eyeglasses" else "FFH"
    return tuple(f"{prefix}_{index:02d}" for index in range(1, 11))


def source_rules(source_name: str) -> dict:
    stages = (PRIMARY_STAGE,) + SECONDARY_STAGES
    if source_name == "eyeglasses_outcome":
        return {
            "required_columns": ("formal_pair_id", "seed_index", "human_positive_minus_control"),
            "key_columns": ("formal_pair_id", "seed_index"),
            "expected_keys": tuple(
                f"{pair}|{seed}" for pair in pair_ids("eyeglasses") for seed in range(1, 5)
            ),
            "finite_columns": ("human_positive_minus_control",),
            "expected_rows": 40,
        }
    if source_name == "facial_hair_outcome":
        return {
            "required_columns": ("attribute", "formal_pair_id", "primary_positive_minus_control"),
            "key_columns": ("attribute", "formal_pair_id"),
            "expected_keys": tuple(
                f"{attribute}|{pair}"
                for attribute in ATTRIBUTES for pair in pair_ids(attribute)
            ),
            "finite_columns": ("primary_positive_minus_control",),
            "finite_attribute": "facial_hair",
            "expected_rows": 20,
        }
    if source_name == "representation_margins":
        return {
            "required_columns": ("attribute", "stage", "formal_pair_id", "margin", "direction"),
            "key_columns": ("attribute", "stage", "formal_pair_id"),
            "expected_keys": tuple(
                f"{attribute}|{stage}|{pair}"
                for attribute in ATTRIBUTES for stage in stages for pair in pair_ids(attribute)
            ),
            "finite_columns": ("margin",),
            "expected_rows": 180,
        }
    if source_name == "injection_pair_grid":
        return {
            "required_columns": (
                "attribute", "formal_pair_id", "cfg_branch", "block_group",
                "denoising_group", "positive_minus_control",
            ),
            "key_columns": (
                "attribute", "formal_pair_id", "cfg_branch", "block_group", "denoising_group",
            ),
            "expected_keys": tuple(
                f"{attribute}|{pair}|{branch}|{block}|{denoise}"
                for attribute in ATTRIBUTES for pair in pair_ids(attribute)
                for branch in BRANCHES for block in GROUPS for denoise in GROUPS
            ),
            "finite_columns": ("positive_minus_control",),
            "expected_rows": 360,
        }
    raise AuditError(f"unsupported source name: {source_name}")


def validate_rows(source_name: str, header: list[str], rows: list[dict[str, str]]) -> tuple[dict, list[str]]:
    rules = source_rules(source_name)
    if not header or any(not column for column in header) or len(header) != len(set(header)):
        raise AuditError("blank or duplicate CSV header")
    missing_columns = sorted(set(rules["required_columns"]) - set(header))
    if missing_columns:
        raise AuditError(f"required columns missing: {missing_columns}")
    if len(rows) != rules["expected_rows"]:
        raise AuditError(f"row count mismatch: {len(rows)} != {rules['expected_rows']}")
    if any(None in row for row in rows):
        raise AuditError("CSV row contains fields beyond the header")

    missing_field_count = 0
    finite_values_checked = 0
    keys = []
    for row_index, row in enumerate(rows, start=1):
        for column in rules["required_columns"]:
            if row.get(column, "") != "":
                continue
            if (
                rules.get("finite_attribute")
                and column in rules["finite_columns"]
                and row.get("attribute") != rules["finite_attribute"]
            ):
                continue
            missing_field_count += 1
        key = "|".join(row[column] for column in rules["key_columns"])
        keys.append(key)
        if source_name == "eyeglasses_outcome" and "attribute" in row and row["attribute"] != "eyeglasses":
            raise AuditError(f"unexpected eyeglasses attribute at row {row_index}")
        if source_name in ("facial_hair_outcome", "representation_margins", "injection_pair_grid"):
            if row["attribute"] not in ATTRIBUTES:
                raise AuditError(f"unexpected attribute at row {row_index}")
        if source_name == "representation_margins" and row["direction"] not in ("correct", "tie", "wrong"):
            raise AuditError(f"unexpected direction at row {row_index}")
        if source_name == "injection_pair_grid":
            if row["cfg_branch"] not in BRANCHES or row["block_group"] not in GROUPS or row["denoising_group"] not in GROUPS:
                raise AuditError(f"unexpected injection label at row {row_index}")
        if rules.get("finite_attribute") and row.get("attribute") != rules["finite_attribute"]:
            continue
        for column in rules["finite_columns"]:
            try:
                value = float(row[column])
            except (KeyError, TypeError, ValueError) as error:
                raise AuditError(f"invalid numeric field {column} at row {row_index}") from error
            if not math.isfinite(value):
                raise AuditError(f"non-finite numeric field {column} at row {row_index}")
            finite_values_checked += 1
    if missing_field_count:
        raise AuditError(f"missing required field count: {missing_field_count}")
    if len(keys) != len(set(keys)):
        raise AuditError("duplicate source key")
    if sorted(keys) != sorted(rules["expected_keys"]):
        raise AuditError("exact planned key universe mismatch")
    return {
        "rows": len(rows),
        "columns": len(header),
        "unique_keys": len(keys),
        "duplicate_keys": 0,
        "missing_required_fields": 0,
        "finite_values_checked": finite_values_checked,
        "nonfinite_values": 0,
        "exact_planned_key_universe": True,
    }, sorted(keys)


def audit(authorization_path: Path, source_name: str, output_dir: Path) -> dict:
    ensure_cpu_offline()
    authorization = read_json(authorization_path)
    if authorization.get("status") != AUTH_STATUS:
        raise AuditError("formal input audit is not authorized")
    if source_name not in SOURCE_NAMES:
        raise AuditError("source name is outside the authorized universe")
    if any(authorization.get("not_authorized", {}).get(name) is not True for name in (
        "pair_outcome_construction", "outcome_trace_join", "spearman_or_other_association",
        "cross_source_value_comparison", "model_loading", "gpu_execution", "network_access",
    )):
        raise AuditError("authorization no longer explicitly blocks a forbidden operation")
    runtime_root = Path(authorization["external_runtime"]).resolve()
    expected_output = runtime_root / source_name
    if output_dir.resolve() != expected_output or output_dir.exists():
        raise AuditError("output directory mismatch or overwrite attempt")
    binding = authorization["sources"][source_name]
    source_path = Path(binding["path"]).resolve()
    if not source_path.is_file() or source_path.is_symlink():
        raise AuditError("source is missing, not a regular file, or a symlink")
    if source_path.stat().st_size != int(binding["bytes"]) or sha256(source_path) != binding["sha256"]:
        raise AuditError("source byte or SHA256 mismatch")

    with source_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        rows = list(reader)
    counts, keys = validate_rows(source_name, header, rows)
    rules = source_rules(source_name)

    output_dir.mkdir(parents=True, exist_ok=False)
    key_path = output_dir / "keys_v1.csv"
    atomic_keys(key_path, keys)
    binding_record = {
        "schema_version": 1,
        "status": "PASS_FORMAL_SINGLE_SOURCE_INPUT_AUDIT",
        "source_name": source_name,
        "path": str(source_path),
        "bytes": source_path.stat().st_size,
        "sha256": sha256(source_path),
        "mode": format(stat.S_IMODE(source_path.stat().st_mode), "03o"),
        "header": header,
        "key_columns": list(rules["key_columns"]),
        "expected_keys": keys,
        "key_manifest": {
            "path": str(key_path),
            "bytes": key_path.stat().st_size,
            "sha256": sha256(key_path),
        },
        "numeric_values_exported": False,
        "source_modified": False,
    }
    binding_path = output_dir / "binding_v1.json"
    atomic_json(binding_path, binding_record)
    summary = {
        "schema_version": 1,
        "status": "PASS_FORMAL_SINGLE_SOURCE_INPUT_AUDIT",
        "source_name": source_name,
        "source_path": str(source_path),
        "source_bytes": source_path.stat().st_size,
        "source_sha256": sha256(source_path),
        "source_mode": binding_record["mode"],
        "header": header,
        **counts,
        "keys_manifest_bytes": key_path.stat().st_size,
        "keys_manifest_sha256": sha256(key_path),
        "binding_bytes": binding_path.stat().st_size,
        "binding_sha256": sha256(binding_path),
        "other_sources_opened": 0,
        "pair_outcome_constructed": False,
        "outcome_trace_joined": False,
        "association_computed": False,
        "numeric_values_exported": False,
        "model_loaded": False,
        "gpu_used": False,
        "network_used": False,
    }
    atomic_json(output_dir / "audit_summary_v1.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--source-name", required=True, choices=SOURCE_NAMES)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.authorization, args.source_name, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
