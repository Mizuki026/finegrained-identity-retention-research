#!/usr/bin/env python3
"""Independent CPU-only verifier for formal LFE-direction input audit v1."""
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
AUTHORIZATION = REPO / "governance/mechanism_token_direction_input_audit_v1/formal_input_audit_execution_authorization_v1.json"
FORMAL_MASTER = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/experiment_freeze_v1/pre_generation_master_freeze_v1.json")
FORMAL_MASTER_BYTES = 6294
FORMAL_MASTER_SHA256 = "149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8"
POOLED = Path("/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003/representation_margins_v1.csv")
POOLED_BYTES = 15152
POOLED_SHA256 = "5e1d14990eba4ad20ae9ec790850bc2ae344177bcadd61aff61c92c372e85506"
CONSISID_REPO = Path("/root/autodl-tmp/consisid-smoketest/ConsisID")
CONSISID_COMMIT = "60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
TRANSFORMER = CONSISID_REPO / "models/transformer_consisid.py"
TRANSFORMER_BYTES = 46480
TRANSFORMER_SHA256 = "b62741974bcde0c3006985a57245cd5c12c23eede7501b6d5146002ce892a7f2"
ATTRIBUTES = ("eyeglasses", "facial_hair")
ROLES = ("positive", "control")
SEEDS = {"2686238281", "280026145", "2169901996", "2046930553"}


class AuditVerificationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path: Path, size: int, digest: str) -> None:
    if not path.is_file() or path.is_symlink() or path.stat().st_size != size or sha256(path) != digest:
        raise AuditVerificationError(f"binding mismatch: {path}")


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def number(raw: str, label: str) -> float:
    try:
        value = float(raw)
    except ValueError as error:
        raise AuditVerificationError(f"invalid number: {label}") from error
    if not math.isfinite(value):
        raise AuditVerificationError(f"nonfinite number: {label}")
    return value


def validate_authorization(run_dir: Path) -> dict:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise AuditVerificationError("CUDA_VISIBLE_DEVICES must be empty")
    auth = json.loads(AUTHORIZATION.read_text())
    if auth.get("status") != "TOKEN_DIRECTION_FORMAL_INPUT_AUDIT_EXECUTION_AUTHORIZED":
        raise AuditVerificationError("audit authorization status mismatch")
    if run_dir.resolve() != Path(auth.get("output_dir", "")).resolve():
        raise AuditVerificationError("audit output path mismatch")
    authority = auth.get("authority", {})
    required = (
        "metadata_and_source_binding_audit", "manifest_schema_and_task_audit",
        "reference_raw_byte_sha256_audit", "pooled_lfe_baseline_audit",
        "consisid_commit_and_source_audit", "independent_verification",
    )
    if any(authority.get(key) is not True for key in required):
        raise AuditVerificationError("audit authority incomplete")
    forbidden = (
        "reference_decode", "face_preprocessing", "model_loading", "gpu_execution",
        "raw_token_capture", "scientific_analysis", "outcome_access", "generation", "network",
    )
    if any(authority.get(key) is not False for key in forbidden):
        raise AuditVerificationError("audit authorization enables forbidden action")
    code = auth.get("code", {})
    if set(code) != {"auditor", "independent_verifier", "protocol_dependency"}:
        raise AuditVerificationError("audit code universe mismatch")
    for item in code.values():
        path = Path(item["path"])
        if not path.is_absolute():
            path = REPO / path
        verify(path, int(item["bytes"]), item["sha256"])
    return auth


def independent_sources() -> tuple[list[dict], list[dict], list[dict]]:
    verify(FORMAL_MASTER, FORMAL_MASTER_BYTES, FORMAL_MASTER_SHA256)
    master = json.loads(FORMAL_MASTER.read_text())
    if master["consisid"]["commit"] != CONSISID_COMMIT or len(master["artifacts"]) != 16:
        raise AuditVerificationError("formal master universe drift")
    artifact_values = []
    for name, item in sorted(master["artifacts"].items()):
        path = Path(item["path"])
        verify(path, int(item["size_bytes"]), item["sha256"])
        artifact_values.append({"artifact_name": name, "bytes": str(item["size_bytes"]), "sha256": item["sha256"]})
    generation_item = master["artifacts"]["generation_manifest"]
    generation = rows(Path(generation_item["path"]))
    reference_item = master["artifacts"]["formal_reference_manifest"]
    reference_manifest = rows(Path(reference_item["path"]))
    if len(generation) != 160 or len(reference_manifest) != 40:
        raise AuditVerificationError("task or reference universe drift")
    reference_by_unit = {row["formal_unit_id"]: row for row in reference_manifest}
    grouped = defaultdict(list)
    for row in generation:
        grouped[row["formal_unit_id"]].append(row)
    if len(grouped) != 40 or set(grouped) != set(reference_by_unit):
        raise AuditVerificationError("reference unit crossing drift")
    reference_values = []
    seen_paths = set()
    for unit in sorted(grouped):
        unit_rows = grouped[unit]
        if len(unit_rows) != 4 or {row["seed"] for row in unit_rows} != SEEDS:
            raise AuditVerificationError("reference seed crossing drift")
        bindings = {(row["formal_pair_id"], row["attribute"], row["role"], row["reference_image_path"], row["reference_image_sha256"]) for row in unit_rows}
        if len(bindings) != 1:
            raise AuditVerificationError("reference binding drift across tasks")
        pair, attribute, role, raw_path, expected_hash = next(iter(bindings))
        manifest_row = reference_by_unit[unit]
        if (pair, attribute, role, expected_hash) != (manifest_row["formal_pair_id"], manifest_row["attribute"], manifest_row["role"], manifest_row["image_sha256"]):
            raise AuditVerificationError("reference manifest mismatch")
        path = Path(raw_path)
        if not path.is_file() or path.is_symlink() or path.resolve() in seen_paths:
            raise AuditVerificationError("reference path missing, symlinked, or reused")
        seen_paths.add(path.resolve())
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise AuditVerificationError("reference hash mismatch")
        reference_values.append({
            "formal_unit_id": unit, "formal_pair_id": pair, "attribute": attribute, "role": role,
            "task_rows": "4", "reference_bytes": str(path.stat().st_size), "reference_sha256": actual_hash,
        })
    verify(POOLED, POOLED_BYTES, POOLED_SHA256)
    pooled_source = rows(POOLED)
    if len(pooled_source) != 180:
        raise AuditVerificationError("representation source row drift")
    pooled_values = []
    for row in pooled_source:
        if row["stage"] != "valid_face_emb_mean_token_l2_normalized":
            continue
        margin = number(row["margin"], "pooled margin")
        direction = "tie" if abs(margin) <= 1e-8 else ("correct" if margin > 0 else "wrong")
        if row["direction"] != direction:
            raise AuditVerificationError("pooled direction mismatch")
        pooled_values.append({"attribute": row["attribute"], "formal_pair_id": row["formal_pair_id"], "margin": margin, "direction": direction})
    if len(pooled_values) != 20 or Counter(row["attribute"] for row in pooled_values) != Counter({"eyeglasses": 10, "facial_hair": 10}):
        raise AuditVerificationError("pooled panel universe drift")
    commit = subprocess.run(["git", "-C", str(CONSISID_REPO), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "-C", str(CONSISID_REPO), "status", "--porcelain=v1"], check=True, capture_output=True, text=True).stdout
    if commit != CONSISID_COMMIT or status:
        raise AuditVerificationError("ConsisID state drift")
    verify(TRANSFORMER, TRANSFORMER_BYTES, TRANSFORMER_SHA256)
    return artifact_values, reference_values, pooled_values


def verify_audit(run_dir: Path) -> dict:
    validate_authorization(run_dir)
    artifacts, references, pooled = independent_sources()
    summary_path = run_dir / "audit_summary_v1.json"
    summary = json.loads(summary_path.read_text())
    if summary.get("status") != "PASS_TOKEN_DIRECTION_FORMAL_INPUT_AUDIT":
        raise AuditVerificationError("audit summary status mismatch")
    exact = {
        "master_artifact_bindings_verified": 16, "generation_tasks": 160, "formal_units": 40,
        "matched_pairs": 20, "unique_reference_files": 40, "reference_files_sha256_verified": 40,
        "pooled_lfe_rows": 20,
    }
    if any(summary.get(key) != value for key, value in exact.items()):
        raise AuditVerificationError("audit summary count mismatch")
    forbidden_false = (
        "reference_images_decoded", "full_weight_rehash_repeated", "model_loaded", "gpu_used",
        "raw_tokens_captured", "scientific_margins_computed", "outcomes_opened", "network_used", "generation_run",
    )
    if any(summary.get(key) is not False for key in forbidden_false):
        raise AuditVerificationError("audit summary reports forbidden action")
    artifact_output = rows(run_dir / "artifact_bindings_v1.csv")
    reference_output = rows(run_dir / "reference_keys_v1.csv")
    pooled_output = rows(run_dir / "pooled_lfe_keys_v1.csv")
    if len(artifact_output) != 16 or len(reference_output) != 40 or len(pooled_output) != 20:
        raise AuditVerificationError("audit output row count mismatch")
    expected_artifacts = {(row["artifact_name"], row["bytes"], row["sha256"]) for row in artifacts}
    observed_artifacts = {(row["artifact_name"], row["bytes"], row["sha256"]) for row in artifact_output if row["verified"] == "True"}
    if observed_artifacts != expected_artifacts:
        raise AuditVerificationError("artifact audit output mismatch")
    expected_references = {(row["formal_unit_id"], row["formal_pair_id"], row["attribute"], row["role"], row["task_rows"], row["reference_bytes"], row["reference_sha256"]) for row in references}
    observed_references = {(row["formal_unit_id"], row["formal_pair_id"], row["attribute"], row["role"], row["task_rows"], row["reference_bytes"], row["reference_sha256"]) for row in reference_output if row["hash_verified"] == "True" and row["regular_file"] == "True" and row["not_symlink"] == "True"}
    if observed_references != expected_references:
        raise AuditVerificationError("reference audit output mismatch")
    expected_pooled = {(row["attribute"], row["formal_pair_id"]): (row["margin"], row["direction"]) for row in pooled}
    if len(expected_pooled) != 20:
        raise AuditVerificationError("duplicate pooled keys")
    for row in pooled_output:
        key = (row["attribute"], row["formal_pair_id"])
        if key not in expected_pooled or row["finite"] != "True":
            raise AuditVerificationError("pooled audit key mismatch")
        expected_margin, expected_direction = expected_pooled[key]
        if row["direction"] != expected_direction or not math.isclose(number(row["margin"], "pooled output"), expected_margin, rel_tol=0, abs_tol=1e-15):
            raise AuditVerificationError("pooled audit value mismatch")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_TOKEN_DIRECTION_FORMAL_INPUT_AUDIT_VERIFICATION",
        "all_16_master_artifacts_rehashed": True,
        "all_40_reference_files_rehashed": True,
        "all_20_pooled_lfe_rows_recomputed": True,
        "reference_images_decoded": False,
        "full_model_weights_rehashed": False,
        "model_loaded": False,
        "gpu_used": False,
        "raw_tokens_captured": False,
        "scientific_margins_computed": False,
        "outcomes_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify_audit(args.run_dir)
    temporary = args.output.with_suffix(args.output.suffix + ".partial")
    if args.output.exists() or temporary.exists():
        raise AuditVerificationError("refusing to overwrite verifier output")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditVerificationError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
