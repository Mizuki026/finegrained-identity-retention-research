#!/usr/bin/env python3
"""CPU-only formal input auditor for token-resolved LFE direction v1."""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import token_resolved_lfe_direction_protocol_v1 as protocol


REPO = Path(__file__).resolve().parents[1]
AUTHORIZATION = (
    REPO
    / "governance/mechanism_token_direction_input_audit_v1"
    / "formal_input_audit_execution_authorization_v1.json"
)
RESEARCHER_AUTHORIZATION = (
    REPO
    / "governance/mechanism_token_direction_input_audit_v1"
    / "researcher_formal_input_audit_authorization_v1.json"
)
IMPLEMENTATION_FREEZE = (
    REPO
    / "governance/mechanism_token_direction_implementation_v1"
    / "implementation_and_dry_run_freeze_v1.json"
)
IMPLEMENTATION_MANIFEST = (
    REPO
    / "governance/mechanism_token_direction_implementation_v1"
    / "implementation_evidence_manifest_v1.csv"
)
POOLED_MARGINS = Path(
    "/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/"
    "phase_s_run_003/representation_margins_v1.csv"
)
POOLED_MARGINS_BYTES = 15152
POOLED_MARGINS_SHA256 = "5e1d14990eba4ad20ae9ec790850bc2ae344177bcadd61aff61c92c372e85506"
TRANSFORMER_SOURCE = Path(
    "/root/autodl-tmp/consisid-smoketest/ConsisID/models/transformer_consisid.py"
)
TRANSFORMER_BYTES = 46480
TRANSFORMER_SHA256 = "b62741974bcde0c3006985a57245cd5c12c23eede7501b6d5146002ce892a7f2"
CONSISID_REPO = Path("/root/autodl-tmp/consisid-smoketest/ConsisID")
AUDIT_STATUS = "TOKEN_DIRECTION_FORMAL_INPUT_AUDIT_EXECUTION_AUTHORIZED"
SUMMARY_STATUS = "PASS_TOKEN_DIRECTION_FORMAL_INPUT_AUDIT"

ARTIFACT_FIELDS = ("artifact_name", "bytes", "sha256", "verified")
REFERENCE_FIELDS = (
    "formal_unit_id", "formal_pair_id", "attribute", "role", "task_rows",
    "reference_bytes", "reference_sha256", "hash_verified", "regular_file", "not_symlink",
)
POOLED_FIELDS = ("attribute", "formal_pair_id", "margin", "direction", "finite")


class InputAuditError(RuntimeError):
    """Raised when a formal source or authorization binding fails."""


def _verify(path: Path, expected_bytes: int, expected_hash: str) -> None:
    try:
        protocol.verify_file(path, expected_bytes, expected_hash)
    except protocol.DirectionProtocolError as error:
        raise InputAuditError(str(error)) from error


def _binding(item: dict, label: str) -> Path:
    path = protocol.resolve_repository_path(str(item.get("path", "")))
    try:
        _verify(path, int(item.get("bytes", item.get("size_bytes", -1))), str(item.get("sha256", "")))
    except (TypeError, ValueError) as error:
        raise InputAuditError(f"invalid binding: {label}") from error
    return path


def validate_execution_authorization(output_dir: Path) -> dict:
    protocol.ensure_cpu_only()
    researcher = protocol.read_json(RESEARCHER_AUTHORIZATION)
    if researcher.get("status") != "CPU_ONLY_FORMAL_INPUT_AUDIT_AUTHORIZED":
        raise InputAuditError("researcher audit authorization status mismatch")
    _binding(researcher.get("implementation_freeze", {}), "implementation freeze")
    authorization = protocol.read_json(AUTHORIZATION)
    if authorization.get("status") != AUDIT_STATUS:
        raise InputAuditError("formal input audit execution authorization mismatch")
    _binding(authorization.get("researcher_authorization", {}), "researcher authorization")
    code = authorization.get("code", {})
    if set(code) != {"auditor", "independent_verifier", "protocol_dependency"}:
        raise InputAuditError("audit code binding universe mismatch")
    for label, item in code.items():
        _binding(item, label)
    authority = authorization.get("authority", {})
    required = (
        "metadata_and_source_binding_audit", "manifest_schema_and_task_audit",
        "reference_raw_byte_sha256_audit", "pooled_lfe_baseline_audit",
        "consisid_commit_and_source_audit", "independent_verification",
    )
    if any(authority.get(key) is not True for key in required):
        raise InputAuditError("formal input audit authority is incomplete")
    forbidden = (
        "reference_decode", "face_preprocessing", "model_loading", "gpu_execution",
        "raw_token_capture", "scientific_analysis", "outcome_access", "generation", "network",
    )
    if any(authority.get(key) is not False for key in forbidden):
        raise InputAuditError("formal input audit authorization enables forbidden action")
    if output_dir.resolve() != Path(str(authorization.get("output_dir", ""))).resolve():
        raise InputAuditError("audit output path differs from authorization")
    if output_dir.exists():
        raise InputAuditError("audit output directory already exists")
    return authorization


def _audit_master_artifacts(master: dict) -> list[dict]:
    rows = []
    artifacts = master.get("artifacts", {})
    if len(artifacts) != 16:
        raise InputAuditError("formal master artifact universe drift")
    for name, item in sorted(artifacts.items()):
        path = Path(str(item.get("path", "")))
        expected_bytes = int(item.get("size_bytes", -1))
        expected_hash = str(item.get("sha256", ""))
        _verify(path, expected_bytes, expected_hash)
        rows.append({"artifact_name": name, "bytes": expected_bytes, "sha256": expected_hash, "verified": True})
    return rows


def _audit_references(master: dict, generation_rows: list[dict[str, str]]) -> list[dict]:
    reference_item = master["artifacts"]["formal_reference_manifest"]
    reference_manifest = Path(reference_item["path"])
    reference_rows = protocol.read_csv(reference_manifest)
    if len(reference_rows) != 40 or len({row["formal_unit_id"] for row in reference_rows}) != 40:
        raise InputAuditError("formal reference manifest universe drift")
    expected = {row["formal_unit_id"]: row for row in reference_rows}
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in generation_rows:
        grouped[row["formal_unit_id"]].append(row)
    if set(grouped) != set(expected):
        raise InputAuditError("generation/reference unit universe mismatch")
    seen_paths = set()
    output = []
    for unit in sorted(grouped):
        tasks = grouped[unit]
        if len(tasks) != 4:
            raise InputAuditError(f"reference task crossing incomplete: {unit}")
        values = {
            (row["formal_pair_id"], row["attribute"], row["role"], row["reference_image_path"], row["reference_image_sha256"])
            for row in tasks
        }
        if len(values) != 1:
            raise InputAuditError(f"reference binding changes across seed labels: {unit}")
        pair, attribute, role, raw_path, expected_hash = next(iter(values))
        manifest_row = expected[unit]
        if (pair, attribute, role, expected_hash) != (
            manifest_row["formal_pair_id"], manifest_row["attribute"], manifest_row["role"], manifest_row["image_sha256"]
        ):
            raise InputAuditError(f"reference manifest metadata mismatch: {unit}")
        path = Path(raw_path)
        if not path.is_file() or path.is_symlink():
            raise InputAuditError(f"reference is missing, nonregular, or symlinked: {unit}")
        actual_hash = protocol.sha256(path)
        if actual_hash != expected_hash:
            raise InputAuditError(f"reference SHA256 mismatch: {unit}")
        resolved = path.resolve()
        if resolved in seen_paths:
            raise InputAuditError(f"reference path reused across formal units: {unit}")
        seen_paths.add(resolved)
        output.append({
            "formal_unit_id": unit,
            "formal_pair_id": pair,
            "attribute": attribute,
            "role": role,
            "task_rows": 4,
            "reference_bytes": path.stat().st_size,
            "reference_sha256": actual_hash,
            "hash_verified": True,
            "regular_file": True,
            "not_symlink": True,
        })
    if len(output) != 40:
        raise InputAuditError("reference audit output count mismatch")
    return output


def _audit_pooled_lfe() -> list[dict]:
    _verify(POOLED_MARGINS, POOLED_MARGINS_BYTES, POOLED_MARGINS_SHA256)
    rows = protocol.read_csv(POOLED_MARGINS)
    if len(rows) != 180:
        raise InputAuditError("run-003 representation margin row count drift")
    selected = [row for row in rows if row["stage"] == "valid_face_emb_mean_token_l2_normalized"]
    if len(selected) != 20:
        raise InputAuditError("pooled-LFE baseline row count drift")
    seen = set()
    output = []
    for row in selected:
        key = (row["attribute"], row["formal_pair_id"])
        if key in seen or row["attribute"] not in protocol.ATTRIBUTES:
            raise InputAuditError("pooled-LFE key universe drift")
        seen.add(key)
        try:
            margin = float(row["margin"])
        except ValueError as error:
            raise InputAuditError("invalid pooled-LFE margin") from error
        if not math.isfinite(margin):
            raise InputAuditError("nonfinite pooled-LFE margin")
        expected_direction = "tie" if abs(margin) <= protocol.TIE_THRESHOLD else ("correct" if margin > 0 else "wrong")
        if row["direction"] != expected_direction:
            raise InputAuditError("pooled-LFE direction label mismatch")
        output.append({"attribute": key[0], "formal_pair_id": key[1], "margin": margin, "direction": expected_direction, "finite": True})
    if Counter(row["attribute"] for row in output) != Counter({"eyeglasses": 10, "facial_hair": 10}):
        raise InputAuditError("pooled-LFE attribute panel drift")
    return sorted(output, key=lambda row: (row["attribute"], row["formal_pair_id"]))


def _audit_consisid() -> dict:
    commit = subprocess.run(
        ["git", "-C", str(CONSISID_REPO), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if commit != protocol.CONSISID_COMMIT:
        raise InputAuditError("ConsisID HEAD drift")
    status = subprocess.run(
        ["git", "-C", str(CONSISID_REPO), "status", "--porcelain=v1"],
        check=True, capture_output=True, text=True,
    ).stdout
    if status:
        raise InputAuditError("ConsisID worktree is not clean")
    _verify(TRANSFORMER_SOURCE, TRANSFORMER_BYTES, TRANSFORMER_SHA256)
    return {"commit": commit, "worktree_clean": True, "transformer_source_verified": True}


def audit(output_dir: Path) -> dict:
    validate_execution_authorization(output_dir)
    protocol.validate_approved_design()
    master, generation_rows = protocol.validate_formal_master()
    artifact_rows = _audit_master_artifacts(master)
    reference_rows = _audit_references(master, generation_rows)
    pooled_rows = _audit_pooled_lfe()
    consisid = _audit_consisid()
    # Reverify the frozen implementation evidence without importing model code.
    freeze = protocol.read_json(IMPLEMENTATION_FREEZE)
    item = freeze.get("evidence_manifest", {})
    _verify(IMPLEMENTATION_MANIFEST, int(item.get("bytes", -1)), str(item.get("sha256", "")))
    if int(item.get("artifact_rows", -1)) != 14:
        raise InputAuditError("implementation evidence universe drift")
    output_dir.mkdir(parents=True, exist_ok=False)
    protocol.atomic_csv(output_dir / "artifact_bindings_v1.csv", ARTIFACT_FIELDS, artifact_rows)
    protocol.atomic_csv(output_dir / "reference_keys_v1.csv", REFERENCE_FIELDS, reference_rows)
    protocol.atomic_csv(output_dir / "pooled_lfe_keys_v1.csv", POOLED_FIELDS, pooled_rows)
    summary = {
        "schema_version": 1,
        "status": SUMMARY_STATUS,
        "formal_master_verified": True,
        "master_artifact_bindings_verified": 16,
        "generation_tasks": 160,
        "formal_units": 40,
        "matched_pairs": 20,
        "unique_reference_files": 40,
        "reference_files_sha256_verified": 40,
        "reference_images_decoded": False,
        "pooled_lfe_rows": 20,
        "pooled_lfe_all_finite": True,
        "consisid_commit": consisid["commit"],
        "consisid_worktree_clean": consisid["worktree_clean"],
        "transformer_source_verified": consisid["transformer_source_verified"],
        "weight_inventory_binding_verified": True,
        "full_weight_rehash_repeated": False,
        "model_loaded": False,
        "gpu_used": False,
        "raw_tokens_captured": False,
        "scientific_margins_computed": False,
        "outcomes_opened": False,
        "network_used": False,
        "generation_run": False,
    }
    protocol.atomic_json(output_dir / "audit_summary_v1.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (InputAuditError, protocol.DirectionProtocolError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
