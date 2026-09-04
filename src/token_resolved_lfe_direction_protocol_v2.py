#!/usr/bin/env python3
"""Pure-stdlib bindings and execution plan for token-direction v2."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[1]
DESIGN_FREEZE = REPO / "governance/mechanism_token_direction_design_v2/token_resolved_directional_analysis_design_freeze_v2.json"
IMPLEMENTATION_AUTH = REPO / "governance/mechanism_token_direction_implementation_v2/researcher_implementation_authorization_v2.json"
DRY_RUN_AUTH = REPO / "governance/mechanism_token_direction_implementation_v2/no_weight_dry_run_authorization_v2.json"
FORMAL_MASTER = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/experiment_freeze_v1/pre_generation_master_freeze_v1.json")
FORMAL_MASTER_BYTES = 6294
FORMAL_MASTER_SHA256 = "149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8"
RUN003 = Path("/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003/representation_margins_v1.csv")
RUN003_BYTES = 15152
RUN003_SHA256 = "5e1d14990eba4ad20ae9ec790850bc2ae344177bcadd61aff61c92c372e85506"
CONSISID_COMMIT = "60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
ATTRIBUTES = ("eyeglasses", "facial_hair")
ROLES = ("positive", "control")
SEED_MAP = {"1": "2686238281", "2": "280026145", "3": "2169901996", "4": "2046930553"}
LFE_TOKENS = 32
LFE_DIM = 2048
TIE_THRESHOLD = 1e-8
IMPLEMENTATION_STATUS = "TOKEN_DIRECTION_V2_IMPLEMENTATION_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_AUTHORIZED_ONLY"
DRY_AUTH_STATUS = "TOKEN_DIRECTION_V2_NO_WEIGHT_DRY_RUN_AUTHORIZED"
DRY_STATUS = "PASS_TOKEN_DIRECTION_V2_CPU_ONLY_NO_WEIGHT_DRY_RUN"


class DirectionV2ProtocolError(RuntimeError):
    pass


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


def resolve(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO / path


def verify_file(path: Path, size: int, digest: str) -> None:
    if not path.is_file() or path.is_symlink() or path.stat().st_size != size or sha256(path) != digest:
        raise DirectionV2ProtocolError(f"binding mismatch: {path}")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    if path.exists() or partial.exists():
        raise DirectionV2ProtocolError(f"refusing overwrite: {path}")
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    partial.replace(path)


def atomic_csv(path: Path, fields: tuple[str, ...], rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    if path.exists() or partial.exists():
        raise DirectionV2ProtocolError(f"refusing overwrite: {path}")
    with partial.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    partial.replace(path)


def require_cpu_only() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise DirectionV2ProtocolError("CUDA_VISIBLE_DEVICES must be empty")


def _bound(item: dict, label: str) -> Path:
    try:
        path = resolve(str(item.get("path", "")))
        verify_file(path, int(item.get("bytes", -1)), str(item.get("sha256", "")))
    except (TypeError, ValueError, DirectionV2ProtocolError) as error:
        raise DirectionV2ProtocolError(f"{label} binding failed: {error}") from error
    return path


def validate_design() -> dict:
    freeze = read_json(DESIGN_FREEZE)
    if freeze.get("status") != "FROZEN_APPROVED_PROSPECTIVE_SELF_CONTAINED_TOKEN_DIRECTION_V2_PREREGISTRATION_ONLY":
        raise DirectionV2ProtocolError("v2 design freeze status mismatch")
    exact = {
        "formal_units": 40, "matched_pairs": 20, "seed_labelled_source_records": 160,
        "fresh_preprocessing_calls": 160, "direct_lfe_calls": 200,
        "same_input_direct_repeat_controls": 40, "four_label_equivalence_comparisons": 120,
        "current_pooled_lfe_margins": 20, "historical_run_003_comparison_rows": 20,
        "primary_token_margins": 640, "token_finite_panel_rows": 64,
        "pair_token_sign_rows": 20,
    }
    design = freeze.get("approved_design", {})
    if any(design.get(key) != value for key, value in exact.items()):
        raise DirectionV2ProtocolError("v2 frozen design count drift")
    for key in ("run_003_immutable", "run_003_is_descriptive_only_not_validity_gate", "outcome_blind"):
        if design.get(key) is not True:
            raise DirectionV2ProtocolError(f"v2 design boundary drift: {key}")
    for key in ("run_003_replacement_or_threshold_relaxation", "raw_tensor_or_vector_persistence", "best_token_or_top_k_selection"):
        if design.get(key) is not False:
            raise DirectionV2ProtocolError(f"v2 forbidden design drift: {key}")
    return freeze


def validate_implementation_authority() -> dict:
    validate_design()
    auth = read_json(IMPLEMENTATION_AUTH)
    if auth.get("status") != IMPLEMENTATION_STATUS:
        raise DirectionV2ProtocolError("implementation authority status mismatch")
    if _bound(auth.get("approved_design", {}), "approved design").resolve() != DESIGN_FREEZE.resolve():
        raise DirectionV2ProtocolError("approved design path mismatch")
    required = (
        "protocol_and_plan_implementation", "transient_analyzer_implementation",
        "independent_verifier_implementation", "fail_closed_runner_implementation",
        "future_single_gpu_runtime_implementation", "cpu_only_static_and_synthetic_tests",
        "cpu_only_no_weight_dry_run",
    )
    if any(auth.get("authorized", {}).get(key) is not True for key in required):
        raise DirectionV2ProtocolError("implementation authority incomplete")
    forbidden = (
        "formal_input_audit", "reference_image_access_or_decode", "face_preprocessing",
        "model_or_weight_loading", "gpu_execution", "raw_identity_or_token_tensor_capture_in_formal_data",
        "formal_token_margin_computation", "outcome_access_or_join", "association_computation",
        "baseline_replacement", "selective_or_automatic_rerun", "video_generation_or_decode",
        "controlled_intervention_preregistration", "controlled_intervention_execution", "network",
    )
    if any(auth.get("not_authorized", {}).get(key) is not True for key in forbidden):
        raise DirectionV2ProtocolError("implementation forbidden boundary incomplete")
    return auth


def validate_dry_authority(output_dir: Path) -> dict:
    validate_implementation_authority()
    auth = read_json(DRY_RUN_AUTH)
    if auth.get("status") != DRY_AUTH_STATUS or auth.get("gpu_execution_explicitly_approved") is not False:
        raise DirectionV2ProtocolError("dry-run authority status mismatch")
    if _bound(auth.get("implementation_authorization", {}), "implementation authorization").resolve() != IMPLEMENTATION_AUTH.resolve():
        raise DirectionV2ProtocolError("implementation authority path mismatch")
    code = auth.get("code", {})
    expected = {"protocol", "analyzer", "verifier", "runner", "runtime"}
    if set(code) != expected:
        raise DirectionV2ProtocolError("dry-run code universe mismatch")
    for label, item in code.items():
        _bound(item, label)
    authority = auth.get("authority", {})
    if authority.get("cpu_only_no_weight_dry_run") is not True or authority.get("independent_verification") is not True:
        raise DirectionV2ProtocolError("dry-run authority incomplete")
    forbidden = (
        "formal_input_audit", "reference_access", "preprocessing", "model_or_weight_loading",
        "gpu_execution", "raw_token_capture", "formal_token_margin_computation", "outcome_access",
        "association_computation", "generation", "intervention", "network",
    )
    if any(authority.get(key) is not False for key in forbidden):
        raise DirectionV2ProtocolError("dry-run enables forbidden action")
    if output_dir.resolve() != Path(str(auth.get("output_dir", ""))).resolve():
        raise DirectionV2ProtocolError("dry-run output path mismatch")
    return auth


def formal_rows() -> tuple[dict, list[dict[str, str]]]:
    verify_file(FORMAL_MASTER, FORMAL_MASTER_BYTES, FORMAL_MASTER_SHA256)
    master = read_json(FORMAL_MASTER)
    if master.get("consisid", {}).get("commit") != CONSISID_COMMIT:
        raise DirectionV2ProtocolError("ConsisID commit drift")
    item = master.get("artifacts", {}).get("generation_manifest", {})
    path = Path(str(item.get("path", "")))
    verify_file(path, int(item.get("size_bytes", -1)), str(item.get("sha256", "")))
    rows = read_csv(path)
    required = {"task_id", "formal_unit_id", "formal_pair_id", "attribute", "role", "seed_index", "seed", "reference_image_path", "reference_image_sha256"}
    if len(rows) != 160 or len({row["task_id"] for row in rows}) != 160 or any(not required.issubset(row) for row in rows):
        raise DirectionV2ProtocolError("formal task universe or schema drift")
    units: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        units[row["formal_unit_id"]].append(row)
    if len(units) != 40 or Counter(row["attribute"] for row in rows) != Counter({"eyeglasses": 80, "facial_hair": 80}):
        raise DirectionV2ProtocolError("formal unit or attribute universe drift")
    for unit, selected in units.items():
        if len(selected) != 4 or {row["seed_index"]: row["seed"] for row in selected} != SEED_MAP:
            raise DirectionV2ProtocolError(f"four-label crossing drift: {unit}")
        values = {(row["formal_pair_id"], row["attribute"], row["role"], row["reference_image_path"], row["reference_image_sha256"]) for row in selected}
        if len(values) != 1:
            raise DirectionV2ProtocolError(f"unit binding drift: {unit}")
    pairs = defaultdict(lambda: defaultdict(set))
    for row in rows:
        pairs[row["attribute"]][row["formal_pair_id"]].add(row["role"])
    if any(len(pairs[a]) != 10 or any(roles != set(ROLES) for roles in pairs[a].values()) for a in ATTRIBUTES):
        raise DirectionV2ProtocolError("matched-pair crossing drift")
    return master, rows


def execution_plan(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    plan = []
    for row in sorted(rows, key=lambda value: (value["formal_unit_id"], int(value["seed_index"]))):
        repeat = row["seed_index"] == "1"
        plan.append({
            "v2_task_id": f"TDV2__{row['task_id']}", "source_task_id": row["task_id"],
            "formal_unit_id": row["formal_unit_id"], "formal_pair_id": row["formal_pair_id"],
            "attribute": row["attribute"], "role": row["role"], "seed_index": row["seed_index"],
            "seed": row["seed"], "fresh_preprocessing_calls": "1",
            "direct_lfe_calls": "2" if repeat else "1",
            "operation": "fresh_preprocessing_then_D1_and_same_input_D2" if repeat else "fresh_preprocessing_then_D1",
        })
    if len(plan) != 160 or len({row["v2_task_id"] for row in plan}) != 160:
        raise DirectionV2ProtocolError("v2 execution plan drift")
    if Counter(row["direct_lfe_calls"] for row in plan) != Counter({"1": 120, "2": 40}):
        raise DirectionV2ProtocolError("v2 direct-repeat crossing drift")
    return plan
