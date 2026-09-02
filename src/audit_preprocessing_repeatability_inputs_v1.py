#!/usr/bin/env python3
"""CPU-only formal input audit for preprocessing repeatability v1."""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import preprocessing_repeatability_protocol_v1 as protocol


REPO = Path(__file__).resolve().parents[1]
GOV = REPO / "governance/mechanism_token_direction_preprocessing_repeatability_input_audit_v1"
RESEARCHER_AUTHORIZATION = GOV / "researcher_formal_input_audit_authorization_v1.json"
EXECUTION_AUTHORIZATION = GOV / "formal_input_audit_execution_authorization_v1.json"
READINESS_FREEZE = REPO / "governance/mechanism_token_direction_preprocessing_repeatability_implementation_v1/readiness_freeze_v1.json"
READINESS_MANIFEST = REPO / "governance/mechanism_token_direction_preprocessing_repeatability_implementation_v1/readiness_evidence_manifest_v1.csv"
CONSISID_REPO = Path("/root/autodl-tmp/consisid-smoketest/ConsisID")
CONSISID_SOURCES = (
    (CONSISID_REPO / "models/consisid_utils.py", 22661, "c8baab111813227ffab88fcfc648e5de39307a4cff2dbf4ddf43d10011d35f00"),
    (CONSISID_REPO / "models/transformer_consisid.py", 46480, "b62741974bcde0c3006985a57245cd5c12c23eede7501b6d5146002ce892a7f2"),
    (CONSISID_REPO / "models/pipeline_consisid.py", 48561, "933d93d5fdd85db9238a4dd47f93a423aca342c683cd52b60ad85222487ea9aa"),
)
EXPECTED_SEEDS = {"1": "2686238281", "2": "280026145", "3": "2169901996", "4": "2046930553"}
AUTHORIZATION_STATUS = "COMPLETE_PANEL_FRESH_PREPROCESSING_REPEATABILITY_FORMAL_INPUT_AUDIT_EXECUTION_AUTHORIZED"
SUMMARY_STATUS = "PASS_COMPLETE_PANEL_FRESH_PREPROCESSING_REPEATABILITY_FORMAL_INPUT_AUDIT"

ARTIFACT_FIELDS = ("artifact_name", "bytes", "sha256", "verified")
READINESS_FIELDS = ("artifact_id", "path", "bytes", "sha256", "verified")
REFERENCE_FIELDS = (
    "formal_unit_id", "formal_pair_id", "attribute", "role", "task_rows",
    "reference_bytes", "reference_sha256", "hash_verified", "regular_file", "not_symlink",
)
PLAN_FIELDS = (
    "unit_task_id", "source_task_id", "formal_unit_id", "formal_pair_id",
    "attribute", "role", "seed_index", "seed", "binding_verified",
)
POOLED_FIELDS = ("attribute", "formal_pair_id", "margin", "direction", "finite")


class InputAuditError(RuntimeError):
    """Raised when a frozen binding or authorization boundary fails."""


def binding(item: dict, label: str) -> Path:
    path = protocol.resolve(str(item.get("path", "")))
    try:
        protocol.verify_file(path, int(item.get("bytes", -1)), str(item.get("sha256", "")))
    except (TypeError, ValueError, protocol.RepeatabilityProtocolError) as error:
        raise InputAuditError(f"{label} binding failed: {error}") from error
    return path


def require_cpu_only() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise InputAuditError("CUDA_VISIBLE_DEVICES must be empty")
    if "torch" in sys.modules:
        raise InputAuditError("torch must not be imported during input audit")


def validate_authority(output_dir: Path) -> dict:
    require_cpu_only()
    researcher = protocol.read_json(RESEARCHER_AUTHORIZATION)
    expected_researcher = "CPU_ONLY_COMPLETE_PANEL_FRESH_PREPROCESSING_REPEATABILITY_FORMAL_INPUT_AUDIT_AUTHORIZED"
    if researcher.get("status") != expected_researcher:
        raise InputAuditError("researcher authorization status mismatch")
    if binding(researcher.get("readiness_freeze", {}), "readiness freeze").resolve() != READINESS_FREEZE.resolve():
        raise InputAuditError("readiness freeze path mismatch")
    authorization = protocol.read_json(EXECUTION_AUTHORIZATION)
    if authorization.get("status") != AUTHORIZATION_STATUS:
        raise InputAuditError("execution authorization status mismatch")
    if binding(authorization.get("researcher_authorization", {}), "researcher authorization").resolve() != RESEARCHER_AUTHORIZATION.resolve():
        raise InputAuditError("researcher authorization path mismatch")
    code = authorization.get("code", {})
    if set(code) != {"auditor", "independent_verifier", "diagnostic_protocol"}:
        raise InputAuditError("audit code universe mismatch")
    for label, item in code.items():
        binding(item, label)
    required = (
        "design_and_readiness_binding_audit", "master_and_artifact_binding_audit",
        "manifest_schema_and_160_task_audit", "complete_40_unit_plan_audit",
        "reference_raw_byte_sha256_audit", "run_003_pooled_lfe_baseline_audit",
        "consisid_commit_and_preprocessing_lfe_source_audit", "independent_verification",
    )
    forbidden = (
        "reference_decode", "face_preprocessing", "model_or_weight_loading",
        "full_model_weight_rehash", "gpu_execution", "direct_lfe_execution",
        "raw_tensor_capture", "scientific_margin_computation", "outcome_access",
        "association_computation", "token_margin_analysis_640", "generation_or_video_decode",
        "intervention", "network",
    )
    authority = authorization.get("authority", {})
    if any(authority.get(key) is not True for key in required):
        raise InputAuditError("formal input audit authority is incomplete")
    if any(authority.get(key) is not False for key in forbidden):
        raise InputAuditError("formal input audit authorization enables a forbidden action")
    if output_dir.resolve() != Path(str(authorization.get("output_dir", ""))).resolve():
        raise InputAuditError("audit output path mismatch")
    if output_dir.exists():
        raise InputAuditError("audit output directory already exists")
    return authorization


def audit_master(master: dict) -> list[dict]:
    artifacts = master.get("artifacts", {})
    if len(artifacts) != 16 or "model_weight_hashes" not in artifacts:
        raise InputAuditError("formal master artifact universe drift")
    output = []
    for name, item in sorted(artifacts.items()):
        path = Path(str(item.get("path", "")))
        try:
            protocol.verify_file(path, int(item.get("size_bytes", -1)), str(item.get("sha256", "")))
        except (TypeError, ValueError, protocol.RepeatabilityProtocolError) as error:
            raise InputAuditError(f"formal master artifact mismatch: {name}") from error
        output.append({"artifact_name": name, "bytes": path.stat().st_size, "sha256": protocol.sha256(path), "verified": True})
    return output


def audit_readiness() -> list[dict]:
    freeze = protocol.read_json(READINESS_FREEZE)
    expected = "FROZEN_PASS_PREPROCESSING_REPEATABILITY_RUNNER_IMPLEMENTATION_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN"
    if freeze.get("status") != expected:
        raise InputAuditError("readiness freeze status mismatch")
    item = freeze.get("evidence_manifest", {})
    protocol.verify_file(READINESS_MANIFEST, int(item.get("bytes", -1)), str(item.get("sha256", "")))
    rows = protocol.read_csv(READINESS_MANIFEST)
    if len(rows) != 13 or int(item.get("artifact_rows", -1)) != 13:
        raise InputAuditError("readiness evidence universe drift")
    output = []
    for row in rows:
        path = protocol.resolve(row["path"])
        protocol.verify_file(path, int(row["bytes"]), row["sha256"])
        output.append({
            "artifact_id": row["artifact_id"], "path": row["path"], "bytes": path.stat().st_size,
            "sha256": protocol.sha256(path), "verified": True,
        })
    return output


def audit_panel(master: dict, generation: list[dict[str, str]], plan: list[dict[str, str]]) -> tuple[list[dict], list[dict]]:
    required_columns = {
        "task_id", "formal_unit_id", "formal_pair_id", "attribute", "role", "seed_index",
        "seed", "reference_image_path", "reference_image_sha256",
    }
    if len(generation) != 160 or len({row["task_id"] for row in generation}) != 160:
        raise InputAuditError("generation task universe drift")
    if any(not required_columns.issubset(row) for row in generation):
        raise InputAuditError("generation manifest schema drift")
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in generation:
        grouped[row["formal_unit_id"]].append(row)
    if len(grouped) != 40:
        raise InputAuditError("formal unit universe drift")
    reference_rows = protocol.read_csv(Path(master["artifacts"]["formal_reference_manifest"]["path"]))
    reference_by_unit = {row["formal_unit_id"]: row for row in reference_rows}
    if len(reference_rows) != 40 or len(reference_by_unit) != 40 or set(reference_by_unit) != set(grouped):
        raise InputAuditError("reference manifest universe drift")
    references = []
    seen_paths: set[Path] = set()
    for unit in sorted(grouped):
        tasks = grouped[unit]
        if len(tasks) != 4 or {row["seed_index"]: row["seed"] for row in tasks} != EXPECTED_SEEDS:
            raise InputAuditError(f"four-seed crossing drift: {unit}")
        values = {
            (row["formal_pair_id"], row["attribute"], row["role"], row["reference_image_path"], row["reference_image_sha256"])
            for row in tasks
        }
        if len(values) != 1:
            raise InputAuditError(f"reference binding changes across seed rows: {unit}")
        pair, attribute, role, raw_path, expected_hash = next(iter(values))
        manifest_row = reference_by_unit[unit]
        if (pair, attribute, role, expected_hash) != (
            manifest_row["formal_pair_id"], manifest_row["attribute"], manifest_row["role"], manifest_row["image_sha256"],
        ):
            raise InputAuditError(f"reference metadata mismatch: {unit}")
        path = Path(raw_path)
        if not path.is_file() or path.is_symlink() or path.resolve() in seen_paths:
            raise InputAuditError(f"reference missing, symlinked, or reused: {unit}")
        seen_paths.add(path.resolve())
        actual_hash = protocol.sha256(path)
        if actual_hash != expected_hash:
            raise InputAuditError(f"reference SHA256 mismatch: {unit}")
        references.append({
            "formal_unit_id": unit, "formal_pair_id": pair, "attribute": attribute, "role": role,
            "task_rows": 4, "reference_bytes": path.stat().st_size, "reference_sha256": actual_hash,
            "hash_verified": True, "regular_file": True, "not_symlink": True,
        })
    plan_by_unit = {row["formal_unit_id"]: row for row in plan}
    if len(plan) != 40 or len(plan_by_unit) != 40:
        raise InputAuditError("repeatability unit plan universe drift")
    plan_output = []
    for unit in sorted(plan_by_unit):
        source_rows = [item for item in grouped[unit] if item["seed_index"] == "1"]
        if len(source_rows) != 1:
            raise InputAuditError(f"seed-index-1 source drift: {unit}")
        source = source_rows[0]
        expected = {
            "unit_task_id": f"PPR__{unit}", "source_task_id": source["task_id"],
            "formal_unit_id": unit, "formal_pair_id": source["formal_pair_id"],
            "attribute": source["attribute"], "role": source["role"],
            "seed_index": "1", "seed": "2686238281",
        }
        if any(plan_by_unit[unit].get(key) != value for key, value in expected.items()):
            raise InputAuditError(f"seed-index-1 repeatability plan mismatch: {unit}")
        plan_output.append({**expected, "binding_verified": True})
    if Counter(row["attribute"] for row in plan_output) != Counter({"eyeglasses": 20, "facial_hair": 20}):
        raise InputAuditError("repeatability plan attribute crossing drift")
    pairs = {(row["attribute"], row["formal_pair_id"]) for row in plan_output}
    if len(pairs) != 20:
        raise InputAuditError("matched-pair universe drift")
    return references, plan_output


def audit_pooled() -> list[dict]:
    protocol.verify_file(protocol.RUN003, protocol.RUN003_BYTES, protocol.RUN003_SHA256)
    source = protocol.read_csv(protocol.RUN003)
    if len(source) != 180:
        raise InputAuditError("run-003 representation source row count drift")
    output = []
    seen = set()
    for row in source:
        if row["stage"] != "valid_face_emb_mean_token_l2_normalized":
            continue
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
        direction = "tie" if abs(margin) <= protocol.TIE_THRESHOLD else ("correct" if margin > 0 else "wrong")
        if row["direction"] != direction:
            raise InputAuditError("pooled-LFE direction mismatch")
        output.append({"attribute": key[0], "formal_pair_id": key[1], "margin": margin, "direction": direction, "finite": True})
    if len(output) != 20 or Counter(row["attribute"] for row in output) != Counter({"eyeglasses": 10, "facial_hair": 10}):
        raise InputAuditError("pooled-LFE panel drift")
    return sorted(output, key=lambda row: (row["attribute"], row["formal_pair_id"]))


def audit_consisid() -> dict:
    commit = subprocess.check_output(["git", "-C", str(CONSISID_REPO), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(["git", "-C", str(CONSISID_REPO), "status", "--porcelain=v1"], text=True)
    if commit != protocol.CONSISID_COMMIT or status:
        raise InputAuditError("ConsisID commit or worktree drift")
    for path, size, digest in CONSISID_SOURCES:
        protocol.verify_file(path, size, digest)
    return {"commit": commit, "worktree_clean": True}


def audit(output_dir: Path) -> dict:
    validate_authority(output_dir)
    protocol.validate_design()
    master, generation = protocol.formal_rows()
    plan = protocol.unit_plan(generation)
    artifacts = audit_master(master)
    readiness = audit_readiness()
    references, plan_rows = audit_panel(master, generation, plan)
    pooled = audit_pooled()
    consisid = audit_consisid()
    require_cpu_only()
    output_dir.mkdir(parents=True, exist_ok=False)
    protocol.atomic_csv(output_dir / "master_artifact_bindings_v1.csv", ARTIFACT_FIELDS, artifacts)
    protocol.atomic_csv(output_dir / "readiness_bindings_v1.csv", READINESS_FIELDS, readiness)
    protocol.atomic_csv(output_dir / "reference_keys_v1.csv", REFERENCE_FIELDS, references)
    protocol.atomic_csv(output_dir / "repeatability_unit_plan_keys_v1.csv", PLAN_FIELDS, plan_rows)
    protocol.atomic_csv(output_dir / "pooled_lfe_keys_v1.csv", POOLED_FIELDS, pooled)
    summary = {
        "schema_version": 1, "status": SUMMARY_STATUS, "formal_master_verified": True,
        "master_artifact_bindings_verified": 16, "readiness_bindings_verified": 13,
        "generation_tasks": 160, "formal_units": 40, "matched_pairs": 20,
        "repeatability_unit_plan_rows": 40, "seed_index_1_rows": 40,
        "planned_fresh_preprocessing_calls": 80, "planned_direct_lfe_calls": 160,
        "unique_reference_files": 40, "reference_files_sha256_verified": 40,
        "reference_images_decoded": False, "pooled_lfe_rows": 20, "pooled_lfe_all_finite": True,
        "consisid_commit": consisid["commit"], "consisid_worktree_clean": consisid["worktree_clean"],
        "consisid_utils_source_verified": True, "transformer_source_verified": True,
        "pipeline_source_verified": True, "weight_inventory_binding_verified": True,
        "full_weight_rehash_repeated": False, "face_preprocessing_run": False,
        "model_or_weight_loading": False, "gpu_used": False, "direct_lfe_executed": False,
        "raw_tensors_captured": False, "scientific_margins_computed": False,
        "outcomes_opened": False, "associations_computed": False,
        "token_margins_640_computed": False, "generation_or_video_decode_run": False,
        "intervention_run": False, "network_used": False, "torch_imported": "torch" in sys.modules,
    }
    if summary["torch_imported"]:
        raise InputAuditError("torch imported during audit")
    protocol.atomic_json(output_dir / "audit_summary_v1.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.output_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (InputAuditError, protocol.RepeatabilityProtocolError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
