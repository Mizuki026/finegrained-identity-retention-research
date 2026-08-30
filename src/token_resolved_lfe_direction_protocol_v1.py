#!/usr/bin/env python3
"""Pure-stdlib gates and no-weight planning for LFE token direction v1."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[1]
DESIGN = REPO / "governance/mechanism_token_direction_design_v1"
APPROVAL_FREEZE = DESIGN / "token_resolved_directional_analysis_approval_freeze_v1.json"
IMPLEMENTATION_AUTHORIZATION = (
    REPO
    / "governance/mechanism_token_direction_implementation_v1"
    / "researcher_implementation_authorization_v1.json"
)
DRY_RUN_AUTHORIZATION = (
    REPO
    / "governance/mechanism_token_direction_implementation_v1"
    / "no_weight_dry_run_authorization_v1.json"
)
FORMAL_MASTER = Path(
    "/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/"
    "experiment_freeze_v1/pre_generation_master_freeze_v1.json"
)
FORMAL_MASTER_BYTES = 6294
FORMAL_MASTER_SHA256 = "149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8"
CONSISID_COMMIT = "60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
ATTRIBUTES = ("eyeglasses", "facial_hair")
ROLES = ("positive", "control")
FORMAL_SEEDS = ("2686238281", "280026145", "2169901996", "2046930553")
LFE_TOKENS = 32
LFE_DIM = 2048
TIE_THRESHOLD = 1e-8
DRY_RUN_STATUS = "PASS_TOKEN_DIRECTION_NO_WEIGHT_DRY_RUN"
IMPLEMENTATION_STATUS = "IMPLEMENTATION_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_AUTHORIZED"
DRY_RUN_AUTHORIZATION_STATUS = "TOKEN_DIRECTION_NO_WEIGHT_DRY_RUN_EXECUTION_AUTHORIZED"


class DirectionProtocolError(RuntimeError):
    """Raised when a prospective gate or frozen universe is violated."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def verify_file(path: Path, expected_bytes: int, expected_sha256: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise DirectionProtocolError(f"required regular file missing: {path}")
    if path.stat().st_size != expected_bytes or sha256(path) != expected_sha256:
        raise DirectionProtocolError(f"file binding mismatch: {path}")


def resolve_repository_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO / path


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    if path.exists() or temporary.exists():
        raise DirectionProtocolError(f"refusing to overwrite output: {path}")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def atomic_csv(path: Path, fields: tuple[str, ...], rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    if path.exists() or temporary.exists():
        raise DirectionProtocolError(f"refusing to overwrite output: {path}")
    with temporary.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def ensure_cpu_only() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise DirectionProtocolError("CUDA_VISIBLE_DEVICES must be the empty string")


def validate_approved_design() -> dict:
    freeze = read_json(APPROVAL_FREEZE)
    if freeze.get("status") != "ALL_SEVEN_DESIGN_DECISIONS_APPROVED_PREREGISTRATION_FROZEN":
        raise DirectionProtocolError("approved design status mismatch")
    manifest_item = freeze.get("approval_evidence_manifest", {})
    manifest = resolve_repository_path(str(manifest_item.get("path", "")))
    verify_file(manifest, int(manifest_item.get("bytes", -1)), str(manifest_item.get("sha256", "")))
    rows = read_csv(manifest)
    if len(rows) != int(manifest_item.get("artifact_rows", -1)):
        raise DirectionProtocolError("approval evidence row-count mismatch")
    for row in rows:
        verify_file(REPO / row["path"], int(row["bytes"]), row["sha256"])
    if freeze.get("approved_design", {}).get("primary_margins") != 640:
        raise DirectionProtocolError("approved margin universe drift")
    return freeze


def validate_implementation_authorization() -> dict:
    validate_approved_design()
    authorization = read_json(IMPLEMENTATION_AUTHORIZATION)
    if authorization.get("status") != IMPLEMENTATION_STATUS:
        raise DirectionProtocolError("implementation authorization status mismatch")
    approved = authorization.get("approved_design", {})
    verify_file(
        resolve_repository_path(str(approved.get("path", ""))),
        int(approved.get("bytes", -1)),
        str(approved.get("sha256", "")),
    )
    required = (
        "instrumentation_implementation",
        "analyzer_implementation",
        "independent_verifier_implementation",
        "cpu_only_static_and_synthetic_tests",
        "no_weight_dry_run",
    )
    if any(authorization.get("authorized", {}).get(key) is not True for key in required):
        raise DirectionProtocolError("implementation authority is incomplete")
    forbidden = (
        "formal_input_audit",
        "reference_image_access",
        "model_or_weight_loading",
        "gpu_execution",
        "raw_token_capture",
        "scientific_extraction",
        "formal_analysis",
        "outcome_access_or_join",
        "controlled_intervention_preregistration",
        "controlled_intervention_execution",
        "generation",
        "network",
    )
    if any(authorization.get("not_authorized", {}).get(key) is not True for key in forbidden):
        raise DirectionProtocolError("forbidden-action boundary is incomplete")
    return authorization


def validate_dry_run_authorization(output_dir: Path) -> dict:
    validate_implementation_authorization()
    authorization = read_json(DRY_RUN_AUTHORIZATION)
    if authorization.get("status") != DRY_RUN_AUTHORIZATION_STATUS:
        raise DirectionProtocolError("no-weight dry-run authorization status mismatch")
    implementation = authorization.get("implementation_authorization", {})
    verify_file(
        resolve_repository_path(str(implementation.get("path", ""))),
        int(implementation.get("bytes", -1)),
        str(implementation.get("sha256", "")),
    )
    for label, binding in authorization.get("code", {}).items():
        path = resolve_repository_path(str(binding.get("path", "")))
        verify_file(path, int(binding.get("bytes", -1)), str(binding.get("sha256", "")))
        if label not in {"protocol", "instrumentation", "analyzer", "verifier"}:
            raise DirectionProtocolError("unexpected code binding in dry-run authorization")
    if set(authorization.get("code", {})) != {"protocol", "instrumentation", "analyzer", "verifier"}:
        raise DirectionProtocolError("dry-run code binding universe mismatch")
    authority = authorization.get("authority", {})
    if authority.get("no_weight_dry_run") is not True or authority.get("independent_verification") is not True:
        raise DirectionProtocolError("dry-run authority is incomplete")
    forbidden = (
        "formal_input_audit", "reference_image_access", "model_loading", "gpu_execution",
        "raw_token_capture", "scientific_analysis", "outcome_access", "generation", "network",
    )
    if any(authority.get(key) is not False for key in forbidden):
        raise DirectionProtocolError("dry-run authorization enables a forbidden action")
    if output_dir.resolve() != Path(str(authorization.get("output_dir", ""))).resolve():
        raise DirectionProtocolError("dry-run output directory differs from authorization")
    return authorization


def validate_formal_master() -> tuple[dict, list[dict[str, str]]]:
    verify_file(FORMAL_MASTER, FORMAL_MASTER_BYTES, FORMAL_MASTER_SHA256)
    master = read_json(FORMAL_MASTER)
    if master.get("consisid", {}).get("commit") != CONSISID_COMMIT:
        raise DirectionProtocolError("ConsisID commit drift")
    item = master.get("artifacts", {}).get("generation_manifest", {})
    manifest = Path(str(item.get("path", "")))
    verify_file(manifest, int(item.get("size_bytes", -1)), str(item.get("sha256", "")))
    rows = read_csv(manifest)
    if len(rows) != 160 or len({row["task_id"] for row in rows}) != 160:
        raise DirectionProtocolError("formal task universe drift")
    units: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        units[row["formal_unit_id"]].append(row)
    if len(units) != 40:
        raise DirectionProtocolError("formal unit universe drift")
    for unit_rows in units.values():
        ordered = sorted(unit_rows, key=lambda row: int(row["seed_index"]))
        if tuple(row["seed"] for row in ordered) != FORMAL_SEEDS:
            raise DirectionProtocolError("formal seed crossing drift")
    if Counter(row["attribute"] for row in rows) != Counter({"eyeglasses": 80, "facial_hair": 80}):
        raise DirectionProtocolError("formal attribute counts drift")
    if any(row["role"] not in ROLES for row in rows):
        raise DirectionProtocolError("formal role drift")
    pairs = defaultdict(set)
    for row in rows:
        pairs[row["attribute"]].add(row["formal_pair_id"])
    if any(len(pairs[attribute]) != 10 for attribute in ATTRIBUTES):
        raise DirectionProtocolError("formal matched-pair universe drift")
    return master, rows


def scientific_reference_plan(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    plan = [
        {
            "reference_task_id": f"TD_S__{row['task_id']}",
            "source_task_id": row["task_id"],
            "formal_unit_id": row["formal_unit_id"],
            "formal_pair_id": row["formal_pair_id"],
            "attribute": row["attribute"],
            "role": row["role"],
            "seed_index": row["seed_index"],
            "seed": row["seed"],
            "phase": "scientific_reference_only",
            "operation": "direct_lfe",
        }
        for row in rows
    ]
    if len(plan) != 160 or len({row["reference_task_id"] for row in plan}) != 160:
        raise DirectionProtocolError("scientific reference plan drift")
    return sorted(plan, key=lambda row: row["source_task_id"])


def engineering_plan(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[str, dict[str, str]] = {}
    for row in rows:
        unique.setdefault(row["formal_unit_id"], row)
    ranked = sorted(
        unique.values(),
        key=lambda row: hashlib.sha256(
            (row["formal_pair_id"] + "|mechanism_trace_v1_engineering_pair_subset").encode()
        ).hexdigest(),
    )
    selected_pairs: dict[str, list[str]] = {}
    for attribute in ATTRIBUTES:
        pair_ids = []
        for row in ranked:
            if row["attribute"] == attribute and row["formal_pair_id"] not in pair_ids:
                pair_ids.append(row["formal_pair_id"])
        selected_pairs[attribute] = pair_ids[:2]
    selected = [
        row for row in unique.values()
        if row["formal_pair_id"] in selected_pairs[row["attribute"]]
    ]
    if len(selected) != 8:
        raise DirectionProtocolError("engineering unit selection drift")
    plan: list[dict[str, str]] = []
    for row in sorted(selected, key=lambda item: item["formal_unit_id"]):
        common = {
            "source_task_id": row["task_id"],
            "formal_unit_id": row["formal_unit_id"],
            "formal_pair_id": row["formal_pair_id"],
            "attribute": row["attribute"],
            "role": row["role"],
            "seed_index": row["seed_index"],
            "seed": row["seed"],
            "phase": "engineering",
        }
        for repeat in (1, 2):
            plan.append({**common, "reference_task_id": f"TD_E__{row['formal_unit_id']}__direct_r{repeat}", "operation": f"direct_lfe_repeat_{repeat}"})
        plan.append({**common, "reference_task_id": f"TD_E__{row['formal_unit_id']}__hook", "operation": "one_step_hook_equivalence"})
    if len(plan) != 24:
        raise DirectionProtocolError("engineering plan count drift")
    return plan


def no_weight_dry_run(output_dir: Path) -> dict:
    ensure_cpu_only()
    validate_dry_run_authorization(output_dir)
    if output_dir.exists():
        raise DirectionProtocolError("dry-run output directory already exists")
    master, formal_rows = validate_formal_master()
    engineering = engineering_plan(formal_rows)
    scientific = scientific_reference_plan(formal_rows)
    output_dir.mkdir(parents=True, exist_ok=False)
    fields = tuple(engineering[0])
    atomic_csv(output_dir / "engineering_plan_v1.csv", fields, engineering)
    atomic_csv(output_dir / "scientific_reference_plan_v1.csv", fields, scientific)
    result = {
        "schema_version": 1,
        "status": DRY_RUN_STATUS,
        "approved_design_path": str(APPROVAL_FREEZE.resolve()),
        "approved_design_bytes": APPROVAL_FREEZE.stat().st_size,
        "approved_design_sha256": sha256(APPROVAL_FREEZE),
        "formal_master_path": str(FORMAL_MASTER),
        "formal_master_bytes": FORMAL_MASTER_BYTES,
        "formal_master_sha256": FORMAL_MASTER_SHA256,
        "consisid_commit": master["consisid"]["commit"],
        "engineering_units": 8,
        "engineering_direct_passes": 16,
        "engineering_hook_controls": 8,
        "engineering_plan_rows": len(engineering),
        "scientific_reference_plan_rows": len(scientific),
        "formal_units": 40,
        "matched_pairs": 20,
        "planned_primary_margins": 640,
        "reference_images_opened": False,
        "outcomes_opened": False,
        "model_modules_imported": False,
        "model_weights_loaded": False,
        "raw_tokens_captured": False,
        "scientific_margins_computed": False,
        "gpu_used": False,
        "network_used": False,
        "generation_run": False,
        "formal_input_audit_performed": False,
        "execution_authorized": False,
    }
    atomic_json(output_dir / "no_weight_dry_run_v1.json", result)
    return result
