#!/usr/bin/env python3
"""CPU-only formal input auditor for controlled LFE projection exchange v1."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import controlled_lfe_projection_exchange_protocol_v1 as protocol

REPO = Path(__file__).resolve().parents[1]
GOV = REPO / "governance/mechanism_controlled_intervention_input_audit_v1"
RESEARCHER_AUTHORIZATION = GOV / "researcher_formal_input_audit_authorization_v1.json"
EXECUTION_AUTHORIZATION = GOV / "formal_input_audit_execution_authorization_v1.json"
READINESS_FREEZE = REPO / "governance/mechanism_controlled_intervention_implementation_v1/runner_readiness_freeze_v1.json"
FORMAL_MASTER = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/experiment_freeze_v1/pre_generation_master_freeze_v1.json")
FORMAL_MASTER_BYTES = 6294
FORMAL_MASTER_SHA256 = "149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8"
CONSISID_REPO = Path("/root/autodl-tmp/consisid-smoketest/ConsisID")
CONSISID_COMMIT = "60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
CONSISID_SOURCES = (
    (CONSISID_REPO / "models/consisid_utils.py", 22661, "c8baab111813227ffab88fcfc648e5de39307a4cff2dbf4ddf43d10011d35f00"),
    (CONSISID_REPO / "models/transformer_consisid.py", 46480, "b62741974bcde0c3006985a57245cd5c12c23eede7501b6d5146002ce892a7f2"),
    (CONSISID_REPO / "models/pipeline_consisid.py", 48561, "933d93d5fdd85db9238a4dd47f93a423aca342c683cd52b60ad85222487ea9aa"),
)
RESEARCHER_STATUS = "CPU_ONLY_CONTROLLED_INTERVENTION_FORMAL_INPUT_AUDIT_AUTHORIZED"
EXECUTION_STATUS = "CONTROLLED_INTERVENTION_FORMAL_INPUT_AUDIT_EXECUTION_AUTHORIZED"
SUMMARY_STATUS = "PASS_CONTROLLED_INTERVENTION_FORMAL_INPUT_AUDIT"
SEED_MAP = {str(index): str(seed) for index, seed in enumerate(protocol.SEEDS, 1)}

ARTIFACT_FIELDS = ("artifact_name", "bytes", "sha256", "verified")
READINESS_FIELDS = ("artifact_id", "location", "path", "bytes", "sha256", "verified")
REFERENCE_FIELDS = (
    "formal_unit_id", "formal_pair_id", "attribute", "role", "task_rows",
    "reference_bytes", "reference_sha256", "hash_verified", "regular_file", "not_symlink",
)
TASK_FIELDS = (
    "planned_task_id", "planned_unit_id", "source_task_id", "source_formal_unit_id",
    "formal_pair_id", "attribute", "role", "seed_index", "seed",
    "reference_image_path", "reference_image_sha256", "binding_verified",
)


class FormalInputAuditError(RuntimeError):
    """Raised when an authorized formal input or boundary check fails."""


def require_cpu_only() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise FormalInputAuditError("formal input audit must remain CUDA-hidden and torch-free")


def binding(item: dict, label: str) -> Path:
    try:
        return protocol.bound(item, label)
    except protocol.ControlledInterventionProtocolError as error:
        raise FormalInputAuditError(str(error)) from error


def validate_authority(output_dir: Path) -> dict:
    require_cpu_only()
    researcher = protocol.read_json(RESEARCHER_AUTHORIZATION)
    if researcher.get("status") != RESEARCHER_STATUS:
        raise FormalInputAuditError("researcher authorization status mismatch")
    readiness = binding(researcher.get("readiness_freeze", {}), "readiness freeze")
    if readiness.resolve() != READINESS_FREEZE.resolve():
        raise FormalInputAuditError("readiness freeze path mismatch")
    if protocol.read_json(readiness).get("status") != researcher["readiness_freeze"].get("required_status"):
        raise FormalInputAuditError("readiness freeze status mismatch")
    design = binding(researcher.get("approved_design", {}), "approved design")
    if design.resolve() != protocol.DESIGN_FREEZE.resolve():
        raise FormalInputAuditError("approved design path mismatch")

    authorization = protocol.read_json(EXECUTION_AUTHORIZATION)
    if authorization.get("status") != EXECUTION_STATUS:
        raise FormalInputAuditError("execution authorization status mismatch")
    if binding(authorization.get("researcher_authorization", {}), "researcher authorization").resolve() != RESEARCHER_AUTHORIZATION.resolve():
        raise FormalInputAuditError("researcher authorization path mismatch")
    code = authorization.get("code", {})
    if set(code) != {"auditor", "independent_verifier", "protocol_dependency"}:
        raise FormalInputAuditError("audit code universe mismatch")
    for label, item in code.items():
        binding(item, label)
    required = (
        "design_and_readiness_binding_audit", "formal_master_and_artifact_binding_audit",
        "manifest_schema_and_complete_160_task_audit", "controlled_intervention_task_binding_construction",
        "reference_raw_byte_sha256_audit", "consisid_commit_and_source_binding_audit",
        "frozen_weight_inventory_artifact_binding_audit", "independent_verification",
    )
    forbidden = (
        "reference_decode_visualization_or_preprocessing", "face_detection_alignment_or_embedding",
        "model_module_or_weight_loading", "full_model_weight_rehash", "gpu_execution",
        "direct_lfe_execution_or_tensor_capture", "trajectory_or_intervention_execution",
        "generation_latent_video_or_decode", "outcome_access_annotation_unblinding_construction_or_join",
        "formal_analysis_or_hypothesis_testing", "network",
    )
    authority = authorization.get("authority", {})
    if any(authority.get(key) is not True for key in required):
        raise FormalInputAuditError("formal input audit authority is incomplete")
    if any(authority.get(key) is not False for key in forbidden):
        raise FormalInputAuditError("formal input audit authorization enables forbidden action")
    if output_dir.resolve() != Path(str(authorization.get("output_dir", ""))).resolve():
        raise FormalInputAuditError("audit output path mismatch")
    staging = output_dir.with_name(output_dir.name + ".partial")
    if output_dir.exists() or staging.exists():
        raise FormalInputAuditError("audit output or staging directory already exists")
    return authorization


def audit_master() -> tuple[dict, list[dict]]:
    protocol.verify_file(FORMAL_MASTER, FORMAL_MASTER_BYTES, FORMAL_MASTER_SHA256)
    master = protocol.read_json(FORMAL_MASTER)
    if master.get("consisid", {}).get("commit") != CONSISID_COMMIT:
        raise FormalInputAuditError("formal master ConsisID commit drift")
    artifacts = master.get("artifacts", {})
    if len(artifacts) != 16 or "model_weight_hashes" not in artifacts:
        raise FormalInputAuditError("formal master artifact universe drift")
    output = []
    for name, item in sorted(artifacts.items()):
        path = Path(str(item.get("path", "")))
        try:
            protocol.verify_file(path, int(item.get("size_bytes", -1)), str(item.get("sha256", "")))
        except (TypeError, ValueError, protocol.ControlledInterventionProtocolError) as error:
            raise FormalInputAuditError(f"formal master artifact mismatch: {name}") from error
        output.append({
            "artifact_name": name, "bytes": path.stat().st_size,
            "sha256": protocol.sha256(path), "verified": True,
        })
    return master, output


def audit_readiness() -> list[dict]:
    freeze = protocol.read_json(READINESS_FREEZE)
    expected = "FROZEN_PASS_CONTROLLED_INTERVENTION_IMPLEMENTATION_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_ONLY"
    if freeze.get("status") != expected:
        raise FormalInputAuditError("readiness freeze status drift")
    item = freeze.get("evidence_manifest", {})
    manifest = protocol.resolve(str(item.get("path", "")))
    protocol.verify_file(manifest, int(item.get("bytes", -1)), str(item.get("sha256", "")))
    rows = protocol.read_csv(manifest)
    if len(rows) != 14:
        raise FormalInputAuditError("readiness evidence universe drift")
    output = []
    for row in rows:
        path = protocol.resolve(row["path"]) if row["location"] == "repository" else Path(row["path"])
        protocol.verify_file(path, int(row["bytes"]), row["sha256"])
        output.append({
            "artifact_id": row["artifact_id"], "location": row["location"], "path": row["path"],
            "bytes": path.stat().st_size, "sha256": protocol.sha256(path), "verified": True,
        })
    return output


def audit_panel(master: dict) -> tuple[list[dict], list[dict]]:
    generation_path = Path(master["artifacts"]["generation_manifest"]["path"])
    generation = protocol.read_csv(generation_path)
    required = {
        "task_id", "formal_unit_id", "formal_pair_id", "attribute", "role",
        "seed_index", "seed", "reference_image_path", "reference_image_sha256",
    }
    if len(generation) != 160 or len({row["task_id"] for row in generation}) != 160:
        raise FormalInputAuditError("generation manifest task universe drift")
    if any(not required.issubset(row) for row in generation):
        raise FormalInputAuditError("generation manifest schema drift")

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in generation:
        grouped[row["formal_unit_id"]].append(row)
    reference_path = Path(master["artifacts"]["formal_reference_manifest"]["path"])
    reference_manifest = protocol.read_csv(reference_path)
    reference_by_unit = {row["formal_unit_id"]: row for row in reference_manifest}
    if len(grouped) != 40 or len(reference_manifest) != 40 or len(reference_by_unit) != 40:
        raise FormalInputAuditError("formal unit or reference universe drift")
    if set(grouped) != set(reference_by_unit):
        raise FormalInputAuditError("generation/reference unit universe mismatch")

    references = []
    tasks = []
    seen_reference_paths: set[Path] = set()
    for source_unit in sorted(grouped):
        unit_rows = grouped[source_unit]
        if len(unit_rows) != 4 or {row["seed_index"]: row["seed"] for row in unit_rows} != SEED_MAP:
            raise FormalInputAuditError(f"four-seed crossing drift: {source_unit}")
        values = {
            (row["formal_pair_id"], row["attribute"], row["role"], row["reference_image_path"], row["reference_image_sha256"])
            for row in unit_rows
        }
        if len(values) != 1:
            raise FormalInputAuditError(f"reference binding changes across seeds: {source_unit}")
        pair, attribute, role, raw_path, expected_hash = next(iter(values))
        if attribute not in protocol.ATTRIBUTES or pair not in protocol.pair_ids(attribute) or role not in protocol.ROLES:
            raise FormalInputAuditError(f"panel key drift: {source_unit}")
        if source_unit != f"{pair}_{role}":
            raise FormalInputAuditError(f"source formal-unit naming drift: {source_unit}")
        manifest_row = reference_by_unit[source_unit]
        if (pair, attribute, role, expected_hash) != (
            manifest_row["formal_pair_id"], manifest_row["attribute"], manifest_row["role"], manifest_row["image_sha256"]
        ):
            raise FormalInputAuditError(f"reference manifest metadata drift: {source_unit}")
        path = Path(raw_path)
        if not path.is_file() or path.is_symlink() or path.resolve() in seen_reference_paths:
            raise FormalInputAuditError(f"reference missing, symlinked, or reused: {source_unit}")
        seen_reference_paths.add(path.resolve())
        actual_hash = protocol.sha256(path)
        if actual_hash != expected_hash:
            raise FormalInputAuditError(f"reference SHA256 mismatch: {source_unit}")
        references.append({
            "formal_unit_id": protocol.unit_id(attribute, pair, role), "formal_pair_id": pair,
            "attribute": attribute, "role": role, "task_rows": 4,
            "reference_bytes": path.stat().st_size, "reference_sha256": actual_hash,
            "hash_verified": True, "regular_file": True, "not_symlink": True,
        })
        for row in sorted(unit_rows, key=lambda value: int(value["seed_index"])):
            seed_index = int(row["seed_index"])
            expected_source_task = f"{pair}_{role}__s{seed_index}"
            if row["task_id"] != expected_source_task or row["seed"] != SEED_MAP[str(seed_index)]:
                raise FormalInputAuditError(f"source task or seed drift: {row['task_id']}")
            tasks.append({
                "planned_task_id": protocol.task_id(attribute, pair, role, seed_index),
                "planned_unit_id": protocol.unit_id(attribute, pair, role),
                "source_task_id": row["task_id"], "source_formal_unit_id": source_unit,
                "formal_pair_id": pair, "attribute": attribute, "role": role,
                "seed_index": seed_index, "seed": row["seed"],
                "reference_image_path": raw_path, "reference_image_sha256": actual_hash,
                "binding_verified": True,
            })

    expected_tasks = {str(row["planned_task_id"]) for row in protocol.execution_plan()}
    observed_tasks = {str(row["planned_task_id"]) for row in tasks}
    pair_roles: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in tasks:
        pair_roles[(str(row["attribute"]), str(row["formal_pair_id"]))].add(str(row["role"]))
    if len(tasks) != 160 or len(observed_tasks) != 160 or observed_tasks != expected_tasks:
        raise FormalInputAuditError("controlled-intervention task binding universe drift")
    if len(pair_roles) != 20 or any(roles != set(protocol.ROLES) for roles in pair_roles.values()):
        raise FormalInputAuditError("complete matched-pair role crossing drift")
    if Counter(str(row["attribute"]) for row in tasks) != Counter({"eyeglasses": 80, "facial_hair": 80}):
        raise FormalInputAuditError("attribute task crossing drift")
    return references, tasks


def audit_consisid() -> dict:
    commit = subprocess.check_output(["git", "-C", str(CONSISID_REPO), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(["git", "-C", str(CONSISID_REPO), "status", "--porcelain=v1"], text=True)
    if commit != CONSISID_COMMIT or status:
        raise FormalInputAuditError("ConsisID commit or worktree drift")
    for path, size, digest in CONSISID_SOURCES:
        protocol.verify_file(path, size, digest)
    return {"commit": commit, "worktree_clean": True}


def audit(output_dir: Path) -> dict:
    validate_authority(output_dir)
    protocol.validate_design()
    master, artifacts = audit_master()
    readiness = audit_readiness()
    references, tasks = audit_panel(master)
    consisid = audit_consisid()
    require_cpu_only()

    staging = output_dir.with_name(output_dir.name + ".partial")
    staging.mkdir(parents=True, exist_ok=False)
    protocol.atomic_csv(staging / "master_artifact_bindings_v1.csv", ARTIFACT_FIELDS, artifacts)
    protocol.atomic_csv(staging / "readiness_bindings_v1.csv", READINESS_FIELDS, readiness)
    protocol.atomic_csv(staging / "reference_keys_v1.csv", REFERENCE_FIELDS, references)
    protocol.atomic_csv(staging / "formal_task_binding_manifest_v1.csv", TASK_FIELDS, tasks)
    summary = {
        "schema_version": 1, "status": SUMMARY_STATUS, "formal_master_verified": True,
        "master_artifact_bindings_verified": 16, "readiness_bindings_verified": 14,
        "generation_tasks": 160, "formal_units": 40, "matched_pairs": 20,
        "controlled_intervention_task_bindings": 160, "planned_trajectories": 480,
        "planned_scheduler_steps": 24000, "planned_fresh_preprocessing_calls": 40,
        "planned_direct_lfe_acquisitions": 40, "unique_reference_files": 40,
        "reference_files_sha256_verified": 40, "reference_raw_bytes_read_for_sha256": True,
        "reference_images_decoded": False, "consisid_commit": consisid["commit"],
        "consisid_worktree_clean": consisid["worktree_clean"],
        "consisid_utils_source_verified": True, "transformer_source_verified": True,
        "pipeline_source_verified": True, "weight_inventory_binding_verified": True,
        "full_model_weight_rehash_repeated": False, "face_preprocessing_run": False,
        "model_module_or_weight_loading": False, "gpu_used": False,
        "direct_lfe_executed": False, "raw_tensors_captured": False,
        "trajectory_or_intervention_executed": False, "generation_latent_video_or_decode_run": False,
        "outcomes_opened": False, "annotation_unblinding_or_join": False,
        "formal_analysis_or_hypothesis_testing": False, "network_used": False,
        "torch_imported": "torch" in sys.modules,
    }
    if summary["torch_imported"]:
        raise FormalInputAuditError("torch imported during audit")
    protocol.atomic_json(staging / "audit_summary_v1.json", summary)
    staging.replace(output_dir)
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
    except (FormalInputAuditError, protocol.ControlledInterventionProtocolError, subprocess.SubprocessError, OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
