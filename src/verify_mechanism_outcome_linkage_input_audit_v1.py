#!/usr/bin/env python3
"""Independent one-source verifier for formal linkage input audit v1."""
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


AUTH_STATUS = "CPU_ONLY_FORMAL_INPUT_AUDIT_APPROVED"
ATTRIBUTES = ("eyeglasses", "facial_hair")
PRIMARY_STAGE = "valid_face_emb_mean_token_l2_normalized"
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


class VerificationError(RuntimeError):
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
        raise VerificationError(f"expected JSON object: {path}")
    return value


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise VerificationError(f"refusing to overwrite verification: {path}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def ensure_cpu_offline() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise VerificationError("CUDA_VISIBLE_DEVICES must be explicitly empty")
    if os.environ.get("HF_HUB_OFFLINE") != "1" or os.environ.get("TRANSFORMERS_OFFLINE") != "1":
        raise VerificationError("offline flags must be set")
    forbidden = ("torch", "transformers", "diffusers", "consisid")
    if any(
        any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)
        for name in sys.modules
    ):
        raise VerificationError("forbidden ML module imported")


def pair_ids(attribute: str) -> tuple[str, ...]:
    prefix = "FEY" if attribute == "eyeglasses" else "FFH"
    return tuple(f"{prefix}_{index:02d}" for index in range(1, 11))


def rules(source_name: str) -> dict:
    stages = (PRIMARY_STAGE,) + SECONDARY_STAGES
    definitions = {
        "eyeglasses_outcome": {
            "required": ("formal_pair_id", "seed_index", "human_positive_minus_control"),
            "keys": ("formal_pair_id", "seed_index"),
            "expected": tuple(f"{pair}|{seed}" for pair in pair_ids("eyeglasses") for seed in range(1, 5)),
            "finite": ("human_positive_minus_control",), "rows": 40,
        },
        "facial_hair_outcome": {
            "required": ("attribute", "formal_pair_id", "primary_positive_minus_control"),
            "keys": ("attribute", "formal_pair_id"),
            "expected": tuple(
                f"{attribute}|{pair}" for attribute in ATTRIBUTES for pair in pair_ids(attribute)
            ),
            "finite": ("primary_positive_minus_control",), "finite_attribute": "facial_hair", "rows": 20,
        },
        "representation_margins": {
            "required": ("attribute", "stage", "formal_pair_id", "margin", "direction"),
            "keys": ("attribute", "stage", "formal_pair_id"),
            "expected": tuple(
                f"{attribute}|{stage}|{pair}"
                for attribute in ATTRIBUTES for stage in stages for pair in pair_ids(attribute)
            ),
            "finite": ("margin",), "rows": 180,
        },
        "injection_pair_grid": {
            "required": (
                "attribute", "formal_pair_id", "cfg_branch", "block_group",
                "denoising_group", "positive_minus_control",
            ),
            "keys": ("attribute", "formal_pair_id", "cfg_branch", "block_group", "denoising_group"),
            "expected": tuple(
                f"{attribute}|{pair}|{branch}|{block}|{denoise}"
                for attribute in ATTRIBUTES for pair in pair_ids(attribute)
                for branch in BRANCHES for block in GROUPS for denoise in GROUPS
            ),
            "finite": ("positive_minus_control",), "rows": 360,
        },
    }
    try:
        return definitions[source_name]
    except KeyError as error:
        raise VerificationError(f"unsupported source: {source_name}") from error


def read_key_manifest(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["key_index", "key"]:
            raise VerificationError("key manifest header mismatch")
        rows = list(reader)
    if [row["key_index"] for row in rows] != [str(index) for index in range(1, len(rows) + 1)]:
        raise VerificationError("key manifest index mismatch")
    return [row["key"] for row in rows]


def verify(authorization_path: Path, source_name: str, audit_dir: Path) -> dict:
    ensure_cpu_offline()
    authorization = read_json(authorization_path)
    if authorization.get("status") != AUTH_STATUS:
        raise VerificationError("input audit authorization status mismatch")
    if source_name not in SOURCE_NAMES:
        raise VerificationError("source outside authorized universe")
    expected_dir = Path(authorization["external_runtime"]).resolve() / source_name
    if audit_dir.resolve() != expected_dir or not audit_dir.is_dir():
        raise VerificationError("audit directory mismatch")
    source_binding = authorization["sources"][source_name]
    source_path = Path(source_binding["path"]).resolve()
    if not source_path.is_file() or source_path.is_symlink():
        raise VerificationError("invalid source path")
    if source_path.stat().st_size != int(source_binding["bytes"]) or sha256(source_path) != source_binding["sha256"]:
        raise VerificationError("source bytes or SHA256 mismatch")

    summary_path = audit_dir / "audit_summary_v1.json"
    binding_path = audit_dir / "binding_v1.json"
    key_path = audit_dir / "keys_v1.csv"
    summary = read_json(summary_path)
    binding = read_json(binding_path)
    definition = rules(source_name)

    with source_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        rows = list(reader)
    if header != binding.get("header") or header != summary.get("header"):
        raise VerificationError("recorded exact header mismatch")
    if not set(definition["required"]) <= set(header) or len(header) != len(set(header)):
        raise VerificationError("required or unique header check failed")
    if len(rows) != definition["rows"]:
        raise VerificationError("source row count mismatch")
    keys = []
    finite_count = 0
    for row_index, row in enumerate(rows, start=1):
        if None in row:
            raise VerificationError(f"excess field at row {row_index}")
        missing_required = []
        for column in definition["required"]:
            if row.get(column, "") != "":
                continue
            if (
                definition.get("finite_attribute")
                and column in definition["finite"]
                and row.get("attribute") != definition["finite_attribute"]
            ):
                continue
            missing_required.append(column)
        if missing_required:
            raise VerificationError(f"missing required field at row {row_index}")
        key = "|".join(row[column] for column in definition["keys"])
        keys.append(key)
        if source_name == "eyeglasses_outcome" and "attribute" in row and row["attribute"] != "eyeglasses":
            raise VerificationError("eyeglasses attribute mismatch")
        if source_name in ("facial_hair_outcome", "representation_margins", "injection_pair_grid") and row["attribute"] not in ATTRIBUTES:
            raise VerificationError("attribute universe mismatch")
        if source_name == "representation_margins" and row["direction"] not in ("correct", "tie", "wrong"):
            raise VerificationError("direction universe mismatch")
        if source_name == "injection_pair_grid" and (
            row["cfg_branch"] not in BRANCHES or row["block_group"] not in GROUPS
            or row["denoising_group"] not in GROUPS
        ):
            raise VerificationError("injection label universe mismatch")
        if definition.get("finite_attribute") and row.get("attribute") != definition["finite_attribute"]:
            continue
        for column in definition["finite"]:
            try:
                value = float(row[column])
            except ValueError as error:
                raise VerificationError(f"invalid numeric at row {row_index}") from error
            if not math.isfinite(value):
                raise VerificationError(f"non-finite numeric at row {row_index}")
            finite_count += 1
    keys = sorted(keys)
    if len(keys) != len(set(keys)) or keys != sorted(definition["expected"]):
        raise VerificationError("exact source key universe mismatch")
    manifest_keys = read_key_manifest(key_path)
    if manifest_keys != keys or binding.get("expected_keys") != keys:
        raise VerificationError("external key binding mismatch")

    expected_mode = format(stat.S_IMODE(source_path.stat().st_mode), "03o")
    if binding.get("mode") != expected_mode or summary.get("source_mode") != expected_mode:
        raise VerificationError("source mode record mismatch")
    if binding.get("key_columns") != list(definition["keys"]):
        raise VerificationError("key column record mismatch")
    if key_path.stat().st_size != summary.get("keys_manifest_bytes") or sha256(key_path) != summary.get("keys_manifest_sha256"):
        raise VerificationError("key manifest byte or SHA256 mismatch")
    if binding_path.stat().st_size != summary.get("binding_bytes") or sha256(binding_path) != summary.get("binding_sha256"):
        raise VerificationError("binding byte or SHA256 mismatch")
    if summary.get("finite_values_checked") != finite_count:
        raise VerificationError("finite-value audit count mismatch")
    forbidden_true = (
        "pair_outcome_constructed", "outcome_trace_joined", "association_computed",
        "numeric_values_exported", "model_loaded", "gpu_used", "network_used",
    )
    if any(summary.get(field) is not False for field in forbidden_true):
        raise VerificationError("audit summary reports a forbidden action")
    if summary.get("other_sources_opened") != 0:
        raise VerificationError("audit summary reports cross-source access")

    result = {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_FORMAL_SINGLE_SOURCE_INPUT_AUDIT_VERIFICATION",
        "source_name": source_name,
        "source_bytes": source_path.stat().st_size,
        "source_sha256": sha256(source_path),
        "source_mode": expected_mode,
        "rows": len(rows),
        "columns": len(header),
        "unique_keys": len(keys),
        "finite_values_checked": finite_count,
        "path_bytes_sha256_header_keys_finiteness_match": True,
        "other_sources_opened": 0,
        "pair_outcome_constructed": False,
        "outcome_trace_joined": False,
        "association_computed": False,
        "model_loaded": False,
        "gpu_used": False,
        "network_used": False,
    }
    atomic_json(audit_dir / "independent_verification_v1.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--source-name", required=True, choices=SOURCE_NAMES)
    parser.add_argument("--audit-dir", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.authorization, args.source_name, args.audit_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
