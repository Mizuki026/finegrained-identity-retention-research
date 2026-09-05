#!/usr/bin/env python3
"""Independent stdlib verifier for controlled-intervention formal input audit v1."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

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
ATTRIBUTES = ("eyeglasses", "facial_hair")
PAIR_PREFIX = {"eyeglasses": "FEY", "facial_hair": "FFH"}
ROLES = ("positive", "control")
SEEDS = {"1": "2686238281", "2": "280026145", "3": "2169901996", "4": "2046930553"}
RESEARCHER_STATUS = "CPU_ONLY_CONTROLLED_INTERVENTION_FORMAL_INPUT_AUDIT_AUTHORIZED"
EXECUTION_STATUS = "CONTROLLED_INTERVENTION_FORMAL_INPUT_AUDIT_EXECUTION_AUTHORIZED"
SUMMARY_STATUS = "PASS_CONTROLLED_INTERVENTION_FORMAL_INPUT_AUDIT"


class FormalInputAuditVerificationError(RuntimeError):
    """Raised when independent reconstruction or boundary checks fail."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path: Path, size: int, digest: str) -> None:
    if not path.is_file() or path.is_symlink() or path.stat().st_size != size or sha256(path) != digest:
        raise FormalInputAuditVerificationError(f"binding mismatch: {path}")


def read_json(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise FormalInputAuditVerificationError(f"missing regular JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file() or path.is_symlink():
        raise FormalInputAuditVerificationError(f"missing regular CSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def resolve(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO / path


def validate_authority(run_dir: Path) -> dict:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise FormalInputAuditVerificationError("independent verifier must remain CUDA-hidden and torch-free")
    researcher = read_json(RESEARCHER_AUTHORIZATION)
    if researcher.get("status") != RESEARCHER_STATUS:
        raise FormalInputAuditVerificationError("researcher authorization status mismatch")
    for key in ("readiness_freeze", "approved_design"):
        item = researcher.get(key, {})
        verify(resolve(str(item.get("path", ""))), int(item.get("bytes", -1)), str(item.get("sha256", "")))
    authorization = read_json(EXECUTION_AUTHORIZATION)
    if authorization.get("status") != EXECUTION_STATUS:
        raise FormalInputAuditVerificationError("execution authorization status mismatch")
    item = authorization.get("researcher_authorization", {})
    verify(resolve(str(item.get("path", ""))), int(item.get("bytes", -1)), str(item.get("sha256", "")))
    code = authorization.get("code", {})
    if set(code) != {"auditor", "independent_verifier", "protocol_dependency"}:
        raise FormalInputAuditVerificationError("audit code universe mismatch")
    for item in code.values():
        verify(resolve(str(item.get("path", ""))), int(item.get("bytes", -1)), str(item.get("sha256", "")))
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
    if any(authority.get(key) is not True for key in required) or any(authority.get(key) is not False for key in forbidden):
        raise FormalInputAuditVerificationError("authorization boundary mismatch")
    if run_dir.resolve() != Path(str(authorization.get("output_dir", ""))).resolve():
        raise FormalInputAuditVerificationError("audit output path mismatch")
    return authorization


def reconstruct() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    verify(FORMAL_MASTER, FORMAL_MASTER_BYTES, FORMAL_MASTER_SHA256)
    master = read_json(FORMAL_MASTER)
    if master.get("consisid", {}).get("commit") != CONSISID_COMMIT:
        raise FormalInputAuditVerificationError("formal master ConsisID commit drift")
    artifacts_source = master.get("artifacts", {})
    if len(artifacts_source) != 16 or "model_weight_hashes" not in artifacts_source:
        raise FormalInputAuditVerificationError("formal master artifact universe drift")
    artifacts = []
    for name, item in sorted(artifacts_source.items()):
        path = Path(str(item.get("path", "")))
        verify(path, int(item.get("size_bytes", -1)), str(item.get("sha256", "")))
        artifacts.append({"artifact_name": name, "bytes": str(path.stat().st_size), "sha256": sha256(path)})

    freeze = read_json(READINESS_FREEZE)
    if freeze.get("status") != "FROZEN_PASS_CONTROLLED_INTERVENTION_IMPLEMENTATION_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_ONLY":
        raise FormalInputAuditVerificationError("readiness freeze status drift")
    manifest_item = freeze.get("evidence_manifest", {})
    readiness_manifest = resolve(str(manifest_item.get("path", "")))
    verify(readiness_manifest, int(manifest_item.get("bytes", -1)), str(manifest_item.get("sha256", "")))
    readiness_source = read_rows(readiness_manifest)
    if len(readiness_source) != 14:
        raise FormalInputAuditVerificationError("readiness evidence universe drift")
    readiness = []
    for row in readiness_source:
        path = resolve(row["path"]) if row["location"] == "repository" else Path(row["path"])
        verify(path, int(row["bytes"]), row["sha256"])
        readiness.append({
            "artifact_id": row["artifact_id"], "location": row["location"], "path": row["path"],
            "bytes": row["bytes"], "sha256": row["sha256"],
        })

    generation = read_rows(Path(master["artifacts"]["generation_manifest"]["path"]))
    reference_manifest = read_rows(Path(master["artifacts"]["formal_reference_manifest"]["path"]))
    required = {
        "task_id", "formal_unit_id", "formal_pair_id", "attribute", "role",
        "seed_index", "seed", "reference_image_path", "reference_image_sha256",
    }
    if len(generation) != 160 or len({row["task_id"] for row in generation}) != 160:
        raise FormalInputAuditVerificationError("generation task universe drift")
    if any(not required.issubset(row) for row in generation):
        raise FormalInputAuditVerificationError("generation schema drift")
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in generation:
        grouped[row["formal_unit_id"]].append(row)
    reference_by_unit = {row["formal_unit_id"]: row for row in reference_manifest}
    if len(grouped) != 40 or len(reference_manifest) != 40 or len(reference_by_unit) != 40 or set(grouped) != set(reference_by_unit):
        raise FormalInputAuditVerificationError("reference unit crossing drift")

    references = []
    tasks = []
    seen_paths: set[Path] = set()
    for source_unit in sorted(grouped):
        unit_rows = grouped[source_unit]
        if len(unit_rows) != 4 or {row["seed_index"]: row["seed"] for row in unit_rows} != SEEDS:
            raise FormalInputAuditVerificationError("four-seed crossing drift")
        bindings = {
            (row["formal_pair_id"], row["attribute"], row["role"], row["reference_image_path"], row["reference_image_sha256"])
            for row in unit_rows
        }
        if len(bindings) != 1:
            raise FormalInputAuditVerificationError("reference binding drift")
        pair, attribute, role, raw_path, expected_hash = next(iter(bindings))
        expected_pairs = {f"{PAIR_PREFIX[attribute]}_{index:02d}" for index in range(1, 11)} if attribute in ATTRIBUTES else set()
        if pair not in expected_pairs or role not in ROLES or source_unit != f"{pair}_{role}":
            raise FormalInputAuditVerificationError("panel key drift")
        manifest_row = reference_by_unit[source_unit]
        if (pair, attribute, role, expected_hash) != (
            manifest_row["formal_pair_id"], manifest_row["attribute"], manifest_row["role"], manifest_row["image_sha256"]
        ):
            raise FormalInputAuditVerificationError("reference metadata drift")
        path = Path(raw_path)
        if not path.is_file() or path.is_symlink() or path.resolve() in seen_paths:
            raise FormalInputAuditVerificationError("reference missing, symlinked, or reused")
        seen_paths.add(path.resolve())
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise FormalInputAuditVerificationError("reference SHA256 mismatch")
        planned_unit = f"CIU__{pair}__{role}"
        references.append({
            "formal_unit_id": planned_unit, "formal_pair_id": pair, "attribute": attribute,
            "role": role, "task_rows": "4", "reference_bytes": str(path.stat().st_size),
            "reference_sha256": actual_hash,
        })
        for row in sorted(unit_rows, key=lambda value: int(value["seed_index"])):
            seed_index = row["seed_index"]
            if row["task_id"] != f"{pair}_{role}__s{seed_index}" or row["seed"] != SEEDS[seed_index]:
                raise FormalInputAuditVerificationError("source task or seed drift")
            tasks.append({
                "planned_task_id": f"CIT__{planned_unit}__S{seed_index}",
                "planned_unit_id": planned_unit, "source_task_id": row["task_id"],
                "source_formal_unit_id": source_unit, "formal_pair_id": pair,
                "attribute": attribute, "role": role, "seed_index": seed_index,
                "seed": row["seed"], "reference_image_path": raw_path,
                "reference_image_sha256": actual_hash,
            })
    if len(tasks) != 160 or len({row["planned_task_id"] for row in tasks}) != 160:
        raise FormalInputAuditVerificationError("controlled-intervention task universe drift")
    if Counter(row["attribute"] for row in tasks) != Counter({"eyeglasses": 80, "facial_hair": 80}):
        raise FormalInputAuditVerificationError("attribute crossing drift")
    pair_roles: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in tasks:
        pair_roles[(row["attribute"], row["formal_pair_id"])].add(row["role"])
    if len(pair_roles) != 20 or any(roles != set(ROLES) for roles in pair_roles.values()):
        raise FormalInputAuditVerificationError("matched-pair crossing drift")

    commit = subprocess.check_output(["git", "-C", str(CONSISID_REPO), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(["git", "-C", str(CONSISID_REPO), "status", "--porcelain=v1"], text=True)
    if commit != CONSISID_COMMIT or status:
        raise FormalInputAuditVerificationError("ConsisID state drift")
    for path, size, digest in CONSISID_SOURCES:
        verify(path, size, digest)
    return artifacts, readiness, references, tasks


def verify_audit(run_dir: Path) -> dict:
    validate_authority(run_dir)
    artifacts, readiness, references, tasks = reconstruct()
    summary = read_json(run_dir / "audit_summary_v1.json")
    if summary.get("status") != SUMMARY_STATUS:
        raise FormalInputAuditVerificationError("audit summary status mismatch")
    exact = {
        "master_artifact_bindings_verified": 16, "readiness_bindings_verified": 14,
        "generation_tasks": 160, "formal_units": 40, "matched_pairs": 20,
        "controlled_intervention_task_bindings": 160, "planned_trajectories": 480,
        "planned_scheduler_steps": 24000, "planned_fresh_preprocessing_calls": 40,
        "planned_direct_lfe_acquisitions": 40, "unique_reference_files": 40,
        "reference_files_sha256_verified": 40,
    }
    if any(summary.get(key) != value for key, value in exact.items()):
        raise FormalInputAuditVerificationError("audit summary count mismatch")
    required_true = (
        "formal_master_verified", "reference_raw_bytes_read_for_sha256", "consisid_worktree_clean",
        "consisid_utils_source_verified", "transformer_source_verified", "pipeline_source_verified",
        "weight_inventory_binding_verified",
    )
    forbidden_false = (
        "reference_images_decoded", "full_model_weight_rehash_repeated", "face_preprocessing_run",
        "model_module_or_weight_loading", "gpu_used", "direct_lfe_executed", "raw_tensors_captured",
        "trajectory_or_intervention_executed", "generation_latent_video_or_decode_run",
        "outcomes_opened", "annotation_unblinding_or_join", "formal_analysis_or_hypothesis_testing",
        "network_used", "torch_imported",
    )
    if any(summary.get(key) is not True for key in required_true):
        raise FormalInputAuditVerificationError("audit summary required boundary mismatch")
    if any(summary.get(key) is not False for key in forbidden_false):
        raise FormalInputAuditVerificationError("audit summary forbidden boundary mismatch")

    artifact_output = read_rows(run_dir / "master_artifact_bindings_v1.csv")
    readiness_output = read_rows(run_dir / "readiness_bindings_v1.csv")
    reference_output = read_rows(run_dir / "reference_keys_v1.csv")
    task_output = read_rows(run_dir / "formal_task_binding_manifest_v1.csv")
    expected_artifacts = {(row["artifact_name"], row["bytes"], row["sha256"]) for row in artifacts}
    observed_artifacts = {(row["artifact_name"], row["bytes"], row["sha256"]) for row in artifact_output if row.get("verified") == "True"}
    if observed_artifacts != expected_artifacts:
        raise FormalInputAuditVerificationError("master artifact output mismatch")
    readiness_keys = ("artifact_id", "location", "path", "bytes", "sha256")
    expected_readiness = {tuple(row[key] for key in readiness_keys) for row in readiness}
    observed_readiness = {tuple(row[key] for key in readiness_keys) for row in readiness_output if row.get("verified") == "True"}
    if observed_readiness != expected_readiness:
        raise FormalInputAuditVerificationError("readiness output mismatch")
    reference_keys = ("formal_unit_id", "formal_pair_id", "attribute", "role", "task_rows", "reference_bytes", "reference_sha256")
    expected_references = {tuple(row[key] for key in reference_keys) for row in references}
    observed_references = {
        tuple(row[key] for key in reference_keys) for row in reference_output
        if row.get("hash_verified") == "True" and row.get("regular_file") == "True" and row.get("not_symlink") == "True"
    }
    if observed_references != expected_references:
        raise FormalInputAuditVerificationError("reference output mismatch")
    task_keys = (
        "planned_task_id", "planned_unit_id", "source_task_id", "source_formal_unit_id",
        "formal_pair_id", "attribute", "role", "seed_index", "seed",
        "reference_image_path", "reference_image_sha256",
    )
    expected_tasks = {tuple(row[key] for key in task_keys) for row in tasks}
    observed_tasks = {tuple(row[key] for key in task_keys) for row in task_output if row.get("binding_verified") == "True"}
    if len(task_output) != 160 or observed_tasks != expected_tasks:
        raise FormalInputAuditVerificationError("task binding output mismatch")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_CONTROLLED_INTERVENTION_FORMAL_INPUT_AUDIT_VERIFICATION",
        "all_16_master_artifacts_rehashed": True,
        "all_14_readiness_bindings_rehashed": True,
        "all_160_generation_rows_reaudited": True,
        "all_160_task_bindings_reconstructed": True,
        "all_40_reference_files_rehashed": True,
        "consisid_utils_transformer_pipeline_sources_rehashed": True,
        "reference_images_decoded": False,
        "full_model_weights_rehashed": False,
        "face_preprocessing_run": False,
        "model_or_weight_loaded": False,
        "gpu_used": False,
        "direct_lfe_executed": False,
        "raw_tensors_captured": False,
        "trajectory_or_intervention_executed": False,
        "generation_latent_video_or_decode_run": False,
        "outcomes_opened": False,
        "annotation_unblinding_or_join": False,
        "formal_analysis_or_hypothesis_testing": False,
        "network_used": False,
        "torch_imported": "torch" in sys.modules,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify_audit(args.run_dir)
    partial = args.output.with_suffix(args.output.suffix + ".partial")
    if args.output.exists() or partial.exists():
        raise FormalInputAuditVerificationError("refusing to overwrite verifier output")
    partial.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    partial.replace(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FormalInputAuditVerificationError, subprocess.SubprocessError, OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
