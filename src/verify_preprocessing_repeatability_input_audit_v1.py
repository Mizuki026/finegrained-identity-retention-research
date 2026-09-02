#!/usr/bin/env python3
"""Independent stdlib verifier for preprocessing repeatability input audit v1."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
GOV = REPO / "governance/mechanism_token_direction_preprocessing_repeatability_input_audit_v1"
AUTHORIZATION = GOV / "formal_input_audit_execution_authorization_v1.json"
FORMAL_MASTER = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/experiment_freeze_v1/pre_generation_master_freeze_v1.json")
FORMAL_MASTER_BYTES = 6294
FORMAL_MASTER_SHA256 = "149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8"
RUN003 = Path("/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003/representation_margins_v1.csv")
RUN003_BYTES = 15152
RUN003_SHA256 = "5e1d14990eba4ad20ae9ec790850bc2ae344177bcadd61aff61c92c372e85506"
READINESS_FREEZE = REPO / "governance/mechanism_token_direction_preprocessing_repeatability_implementation_v1/readiness_freeze_v1.json"
READINESS_MANIFEST = REPO / "governance/mechanism_token_direction_preprocessing_repeatability_implementation_v1/readiness_evidence_manifest_v1.csv"
CONSISID_REPO = Path("/root/autodl-tmp/consisid-smoketest/ConsisID")
CONSISID_COMMIT = "60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
SOURCES = (
    (CONSISID_REPO / "models/consisid_utils.py", 22661, "c8baab111813227ffab88fcfc648e5de39307a4cff2dbf4ddf43d10011d35f00"),
    (CONSISID_REPO / "models/transformer_consisid.py", 46480, "b62741974bcde0c3006985a57245cd5c12c23eede7501b6d5146002ce892a7f2"),
    (CONSISID_REPO / "models/pipeline_consisid.py", 48561, "933d93d5fdd85db9238a4dd47f93a423aca342c683cd52b60ad85222487ea9aa"),
)
SEEDS = {"1": "2686238281", "2": "280026145", "3": "2169901996", "4": "2046930553"}


class AuditVerificationError(RuntimeError):
    """Raised when independent reconstruction disagrees with the audit package."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path: Path, size: int, digest: str) -> None:
    if not path.is_file() or path.is_symlink() or path.stat().st_size != size or sha256(path) != digest:
        raise AuditVerificationError(f"binding mismatch: {path}")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def finite(raw: str, label: str) -> float:
    try:
        value = float(raw)
    except ValueError as error:
        raise AuditVerificationError(f"invalid numeric value: {label}") from error
    if not math.isfinite(value):
        raise AuditVerificationError(f"nonfinite value: {label}")
    return value


def resolve(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO / path


def validate_authority(run_dir: Path) -> dict:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise AuditVerificationError("independent verifier must remain CPU-only and torch-free")
    auth = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    expected = "COMPLETE_PANEL_FRESH_PREPROCESSING_REPEATABILITY_FORMAL_INPUT_AUDIT_EXECUTION_AUTHORIZED"
    if auth.get("status") != expected:
        raise AuditVerificationError("execution authorization status mismatch")
    if run_dir.resolve() != Path(str(auth.get("output_dir", ""))).resolve():
        raise AuditVerificationError("audit output path mismatch")
    researcher = auth.get("researcher_authorization", {})
    verify(resolve(str(researcher.get("path", ""))), int(researcher.get("bytes", -1)), str(researcher.get("sha256", "")))
    code = auth.get("code", {})
    if set(code) != {"auditor", "independent_verifier", "diagnostic_protocol"}:
        raise AuditVerificationError("audit code universe mismatch")
    for item in code.values():
        verify(resolve(str(item.get("path", ""))), int(item.get("bytes", -1)), str(item.get("sha256", "")))
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
    authority = auth.get("authority", {})
    if any(authority.get(key) is not True for key in required) or any(authority.get(key) is not False for key in forbidden):
        raise AuditVerificationError("authorization boundary mismatch")
    return auth


def reconstruct_sources() -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    verify(FORMAL_MASTER, FORMAL_MASTER_BYTES, FORMAL_MASTER_SHA256)
    master = json.loads(FORMAL_MASTER.read_text(encoding="utf-8"))
    if master.get("consisid", {}).get("commit") != CONSISID_COMMIT or len(master.get("artifacts", {})) != 16:
        raise AuditVerificationError("formal master universe drift")
    artifacts = []
    for name, item in sorted(master["artifacts"].items()):
        path = Path(item["path"])
        verify(path, int(item["size_bytes"]), item["sha256"])
        artifacts.append({"artifact_name": name, "bytes": str(item["size_bytes"]), "sha256": item["sha256"]})
    freeze = json.loads(READINESS_FREEZE.read_text(encoding="utf-8"))
    expected = "FROZEN_PASS_PREPROCESSING_REPEATABILITY_RUNNER_IMPLEMENTATION_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN"
    if freeze.get("status") != expected:
        raise AuditVerificationError("readiness status drift")
    manifest_item = freeze["evidence_manifest"]
    verify(READINESS_MANIFEST, int(manifest_item["bytes"]), manifest_item["sha256"])
    readiness = read_rows(READINESS_MANIFEST)
    if len(readiness) != 13:
        raise AuditVerificationError("readiness universe drift")
    readiness_values = []
    for row in readiness:
        path = resolve(row["path"])
        verify(path, int(row["bytes"]), row["sha256"])
        readiness_values.append({"artifact_id": row["artifact_id"], "path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"]})
    generation = read_rows(Path(master["artifacts"]["generation_manifest"]["path"]))
    reference_manifest = read_rows(Path(master["artifacts"]["formal_reference_manifest"]["path"]))
    if len(generation) != 160 or len({row["task_id"] for row in generation}) != 160 or len(reference_manifest) != 40:
        raise AuditVerificationError("task/reference universe drift")
    required_columns = {"task_id", "formal_unit_id", "formal_pair_id", "attribute", "role", "seed_index", "seed", "reference_image_path", "reference_image_sha256"}
    if any(not required_columns.issubset(row) for row in generation):
        raise AuditVerificationError("generation schema drift")
    reference_by_unit = {row["formal_unit_id"]: row for row in reference_manifest}
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in generation:
        grouped[row["formal_unit_id"]].append(row)
    if len(grouped) != 40 or set(grouped) != set(reference_by_unit):
        raise AuditVerificationError("formal unit crossing drift")
    references = []
    plans = []
    seen_paths: set[Path] = set()
    for unit in sorted(grouped):
        tasks = grouped[unit]
        if len(tasks) != 4 or {row["seed_index"]: row["seed"] for row in tasks} != SEEDS:
            raise AuditVerificationError("four-seed crossing drift")
        bindings = {(row["formal_pair_id"], row["attribute"], row["role"], row["reference_image_path"], row["reference_image_sha256"]) for row in tasks}
        if len(bindings) != 1:
            raise AuditVerificationError("reference binding drift")
        pair, attribute, role, raw_path, expected_hash = next(iter(bindings))
        manifest_row = reference_by_unit[unit]
        if (pair, attribute, role, expected_hash) != (manifest_row["formal_pair_id"], manifest_row["attribute"], manifest_row["role"], manifest_row["image_sha256"]):
            raise AuditVerificationError("reference metadata mismatch")
        path = Path(raw_path)
        if not path.is_file() or path.is_symlink() or path.resolve() in seen_paths:
            raise AuditVerificationError("reference path missing, symlinked, or reused")
        seen_paths.add(path.resolve())
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise AuditVerificationError("reference hash mismatch")
        references.append({
            "formal_unit_id": unit, "formal_pair_id": pair, "attribute": attribute, "role": role,
            "task_rows": "4", "reference_bytes": str(path.stat().st_size), "reference_sha256": actual_hash,
        })
        selected = [row for row in tasks if row["seed_index"] == "1"]
        if len(selected) != 1:
            raise AuditVerificationError("seed-index-1 selection drift")
        source = selected[0]
        plans.append({
            "unit_task_id": f"PPR__{unit}", "source_task_id": source["task_id"],
            "formal_unit_id": unit, "formal_pair_id": pair, "attribute": attribute,
            "role": role, "seed_index": "1", "seed": "2686238281",
        })
    if Counter(row["attribute"] for row in plans) != Counter({"eyeglasses": 20, "facial_hair": 20}) or len({(row["attribute"], row["formal_pair_id"]) for row in plans}) != 20:
        raise AuditVerificationError("repeatability plan crossing drift")
    verify(RUN003, RUN003_BYTES, RUN003_SHA256)
    source_rows = read_rows(RUN003)
    if len(source_rows) != 180:
        raise AuditVerificationError("run-003 source row count drift")
    pooled = []
    for row in source_rows:
        if row["stage"] != "valid_face_emb_mean_token_l2_normalized":
            continue
        margin = finite(row["margin"], "pooled margin")
        direction = "tie" if abs(margin) <= 1e-8 else ("correct" if margin > 0 else "wrong")
        if row["direction"] != direction:
            raise AuditVerificationError("pooled direction drift")
        pooled.append({"attribute": row["attribute"], "formal_pair_id": row["formal_pair_id"], "margin": margin, "direction": direction})
    if len(pooled) != 20 or Counter(row["attribute"] for row in pooled) != Counter({"eyeglasses": 10, "facial_hair": 10}):
        raise AuditVerificationError("pooled panel drift")
    commit = subprocess.check_output(["git", "-C", str(CONSISID_REPO), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(["git", "-C", str(CONSISID_REPO), "status", "--porcelain=v1"], text=True)
    if commit != CONSISID_COMMIT or status:
        raise AuditVerificationError("ConsisID state drift")
    for path, size, digest in SOURCES:
        verify(path, size, digest)
    return artifacts, readiness_values, references, plans, pooled


def verify_audit(run_dir: Path) -> dict:
    validate_authority(run_dir)
    artifacts, readiness, references, plans, pooled = reconstruct_sources()
    summary = json.loads((run_dir / "audit_summary_v1.json").read_text(encoding="utf-8"))
    if summary.get("status") != "PASS_COMPLETE_PANEL_FRESH_PREPROCESSING_REPEATABILITY_FORMAL_INPUT_AUDIT":
        raise AuditVerificationError("audit summary status mismatch")
    exact = {
        "master_artifact_bindings_verified": 16, "readiness_bindings_verified": 13,
        "generation_tasks": 160, "formal_units": 40, "matched_pairs": 20,
        "repeatability_unit_plan_rows": 40, "seed_index_1_rows": 40,
        "planned_fresh_preprocessing_calls": 80, "planned_direct_lfe_calls": 160,
        "unique_reference_files": 40, "reference_files_sha256_verified": 40, "pooled_lfe_rows": 20,
    }
    if any(summary.get(key) != value for key, value in exact.items()):
        raise AuditVerificationError("audit summary count mismatch")
    required_true = (
        "formal_master_verified", "pooled_lfe_all_finite", "consisid_worktree_clean",
        "consisid_utils_source_verified", "transformer_source_verified", "pipeline_source_verified",
        "weight_inventory_binding_verified",
    )
    forbidden_false = (
        "reference_images_decoded", "full_weight_rehash_repeated", "face_preprocessing_run",
        "model_or_weight_loading", "gpu_used", "direct_lfe_executed", "raw_tensors_captured",
        "scientific_margins_computed", "outcomes_opened", "associations_computed",
        "token_margins_640_computed", "generation_or_video_decode_run", "intervention_run",
        "network_used", "torch_imported",
    )
    if any(summary.get(key) is not True for key in required_true) or any(summary.get(key) is not False for key in forbidden_false):
        raise AuditVerificationError("audit summary boundary mismatch")
    artifact_output = read_rows(run_dir / "master_artifact_bindings_v1.csv")
    readiness_output = read_rows(run_dir / "readiness_bindings_v1.csv")
    reference_output = read_rows(run_dir / "reference_keys_v1.csv")
    plan_output = read_rows(run_dir / "repeatability_unit_plan_keys_v1.csv")
    pooled_output = read_rows(run_dir / "pooled_lfe_keys_v1.csv")
    expected_artifacts = {(row["artifact_name"], row["bytes"], row["sha256"]) for row in artifacts}
    observed_artifacts = {(row["artifact_name"], row["bytes"], row["sha256"]) for row in artifact_output if row["verified"] == "True"}
    if observed_artifacts != expected_artifacts:
        raise AuditVerificationError("master artifact output mismatch")
    expected_readiness = {(row["artifact_id"], row["path"], row["bytes"], row["sha256"]) for row in readiness}
    observed_readiness = {(row["artifact_id"], row["path"], row["bytes"], row["sha256"]) for row in readiness_output if row["verified"] == "True"}
    if observed_readiness != expected_readiness:
        raise AuditVerificationError("readiness output mismatch")
    expected_references = {(row["formal_unit_id"], row["formal_pair_id"], row["attribute"], row["role"], row["task_rows"], row["reference_bytes"], row["reference_sha256"]) for row in references}
    observed_references = {(row["formal_unit_id"], row["formal_pair_id"], row["attribute"], row["role"], row["task_rows"], row["reference_bytes"], row["reference_sha256"]) for row in reference_output if row["hash_verified"] == "True" and row["regular_file"] == "True" and row["not_symlink"] == "True"}
    if observed_references != expected_references:
        raise AuditVerificationError("reference output mismatch")
    expected_plans = {(row["unit_task_id"], row["source_task_id"], row["formal_unit_id"], row["formal_pair_id"], row["attribute"], row["role"], row["seed_index"], row["seed"]) for row in plans}
    observed_plans = {(row["unit_task_id"], row["source_task_id"], row["formal_unit_id"], row["formal_pair_id"], row["attribute"], row["role"], row["seed_index"], row["seed"]) for row in plan_output if row["binding_verified"] == "True"}
    if observed_plans != expected_plans:
        raise AuditVerificationError("repeatability plan output mismatch")
    expected_pooled = {(row["attribute"], row["formal_pair_id"]): (row["margin"], row["direction"]) for row in pooled}
    if len(pooled_output) != 20 or len(expected_pooled) != 20:
        raise AuditVerificationError("pooled output count mismatch")
    for row in pooled_output:
        key = (row["attribute"], row["formal_pair_id"])
        if key not in expected_pooled or row["finite"] != "True":
            raise AuditVerificationError("pooled output key mismatch")
        expected_margin, expected_direction = expected_pooled[key]
        if row["direction"] != expected_direction or not math.isclose(finite(row["margin"], "pooled output"), expected_margin, rel_tol=0, abs_tol=1e-15):
            raise AuditVerificationError("pooled output value mismatch")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_COMPLETE_PANEL_FRESH_PREPROCESSING_REPEATABILITY_FORMAL_INPUT_AUDIT_VERIFICATION",
        "all_16_master_artifacts_rehashed": True, "all_13_readiness_bindings_rehashed": True,
        "all_160_generation_rows_reaudited": True, "all_40_plan_rows_reconstructed": True,
        "all_40_reference_files_rehashed": True, "all_20_pooled_lfe_rows_recomputed": True,
        "consisid_utils_transformer_pipeline_sources_rehashed": True,
        "reference_images_decoded": False, "full_model_weights_rehashed": False,
        "face_preprocessing_run": False, "model_loaded": False, "gpu_used": False,
        "direct_lfe_executed": False, "raw_tensors_captured": False,
        "scientific_margins_computed": False, "outcomes_opened": False,
        "associations_computed": False, "token_margins_640_computed": False,
        "generation_or_video_decode_run": False, "intervention_run": False, "network_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify_audit(args.run_dir)
    partial = args.output.with_suffix(args.output.suffix + ".partial")
    if args.output.exists() or partial.exists():
        raise AuditVerificationError("refusing to overwrite verifier output")
    partial.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    partial.replace(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditVerificationError, subprocess.SubprocessError, OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
