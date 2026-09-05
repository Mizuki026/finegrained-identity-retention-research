#!/usr/bin/env python3
"""Pure-stdlib bindings and frozen plan for controlled LFE projection exchange v1."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DESIGN_DIR = REPO / "governance/mechanism_controlled_intervention_design_v1"
DESIGN_FREEZE = DESIGN_DIR / "controlled_intervention_design_freeze_v1.json"
PREREGISTRATION = DESIGN_DIR / "controlled_lfe_projection_exchange_preregistration_v1.json"
IMPLEMENTATION_DIR = REPO / "governance/mechanism_controlled_intervention_implementation_v1"
IMPLEMENTATION_AUTH = IMPLEMENTATION_DIR / "researcher_implementation_authorization_v1.json"
DRY_RUN_AUTH = IMPLEMENTATION_DIR / "no_weight_dry_run_authorization_v1.json"
CORRECTION_DIR = REPO / "governance/mechanism_controlled_intervention_memory_correction_v1"
CORRECTION_AUTH = CORRECTION_DIR / "researcher_memory_lifecycle_correction_authorization_v1.json"
CORRECTION_DRY_RUN_AUTH = CORRECTION_DIR / "no_weight_dry_run_authorization_v1.json"

DESIGN_FREEZE_BYTES = 3918
DESIGN_FREEZE_SHA256 = "12697bf6f44f85ed1dddacfd339a176f65d8b32d1c22c30d5e4e803cd31eb89f"
PREREGISTRATION_BYTES = 10955
PREREGISTRATION_SHA256 = "02ef043b3391ac931c5a6bb92f8716954abfcf97b4ed9511eaead1a42ade38eb"
IMPLEMENTATION_STATUS = "CONTROLLED_INTERVENTION_IMPLEMENTATION_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_AUTHORIZED_ONLY"
DRY_RUN_STATUS = "CONTROLLED_INTERVENTION_NO_WEIGHT_DRY_RUN_AUTHORIZED"
CORRECTION_STATUS = "CONTROLLED_INTERVENTION_MEMORY_LIFECYCLE_CORRECTION_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_AUTHORIZED_ONLY"
CORRECTION_DRY_RUN_STATUS = "CONTROLLED_INTERVENTION_MEMORY_LIFECYCLE_CORRECTION_NO_WEIGHT_DRY_RUN_AUTHORIZED"
DRY_PASS_STATUS = "PASS_CONTROLLED_INTERVENTION_CPU_ONLY_NO_WEIGHT_DRY_RUN"
NAMESPACE = "controlled_lfe_projection_exchange_v1"
ENGINEERING_NAMESPACE = "controlled_lfe_projection_exchange_v1_engineering_pair_subset"

ATTRIBUTES = ("eyeglasses", "facial_hair")
PAIR_PREFIX = {"eyeglasses": "FEY", "facial_hair": "FFH"}
ROLES = ("positive", "control")
CONDITIONS = ("baseline", "target_projection_exchange", "orthogonal_sham")
SEEDS = (2686238281, 280026145, 2169901996, 2046930553)
FRAME_INDICES = (0, 8, 16, 24, 32, 40, 48)
LFE_TOKENS = 32
LFE_DIM = 2048
NORM_FLOOR = 1e-12
DIRECTION_ATOL = 1e-6
TIE_THRESHOLD = 1e-8
SCHEDULER_POSITIONS = 50


class ControlledInterventionProtocolError(RuntimeError):
    """Raised when any frozen binding, authority, or plan invariant drifts."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def resolve(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO / path


def verify_file(path: Path, size: int, digest: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ControlledInterventionProtocolError(f"missing or non-regular binding: {path}")
    if path.stat().st_size != size or sha256(path) != digest:
        raise ControlledInterventionProtocolError(f"size or SHA256 binding mismatch: {path}")


def bound(item: dict, label: str) -> Path:
    try:
        path = resolve(str(item.get("path", "")))
        verify_file(path, int(item.get("bytes", -1)), str(item.get("sha256", "")))
    except (TypeError, ValueError, ControlledInterventionProtocolError) as error:
        raise ControlledInterventionProtocolError(f"{label} binding failed: {error}") from error
    return path


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    if path.exists() or partial.exists():
        raise ControlledInterventionProtocolError(f"refusing overwrite: {path}")
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    partial.replace(path)


def atomic_csv(path: Path, fields: tuple[str, ...], rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    if path.exists() or partial.exists():
        raise ControlledInterventionProtocolError(f"refusing overwrite: {path}")
    with partial.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    partial.replace(path)


def require_cpu_only() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ControlledInterventionProtocolError("CUDA_VISIBLE_DEVICES must be empty")


def validate_design() -> tuple[dict, dict]:
    verify_file(DESIGN_FREEZE, DESIGN_FREEZE_BYTES, DESIGN_FREEZE_SHA256)
    verify_file(PREREGISTRATION, PREREGISTRATION_BYTES, PREREGISTRATION_SHA256)
    freeze = read_json(DESIGN_FREEZE)
    prereg = read_json(PREREGISTRATION)
    if freeze.get("status") != "FROZEN_FORMALLY_PREREGISTERED_DESIGN_ONLY_NO_IMPLEMENTATION_OR_EXECUTION_AUTHORITY":
        raise ControlledInterventionProtocolError("design freeze status drift")
    machine = freeze.get("machine_readable_preregistration", {})
    if bound(machine, "machine preregistration").resolve() != PREREGISTRATION.resolve():
        raise ControlledInterventionProtocolError("preregistration path drift")
    panel = prereg.get("frozen_panel", {})
    expected = {
        "pairs_per_attribute": 10, "pairs_total": 20, "formal_units": 40,
        "source_tasks": 160, "scientific_trajectories": 480,
    }
    if any(panel.get(key) != value for key, value in expected.items()):
        raise ControlledInterventionProtocolError("frozen panel count drift")
    if tuple(panel.get("attributes", ())) != ATTRIBUTES or tuple(panel.get("roles", ())) != ROLES:
        raise ControlledInterventionProtocolError("attribute or role drift")
    if tuple(panel.get("conditions", ())) != CONDITIONS or tuple(panel.get("seeds", ())) != SEEDS:
        raise ControlledInterventionProtocolError("condition or seed drift")
    if prereg.get("direction", {}).get("token_indices") != LFE_TOKENS:
        raise ControlledInterventionProtocolError("token family drift")
    if prereg.get("outcome_plan", {}).get("sampled_decoded_frame_indices") != list(FRAME_INDICES):
        raise ControlledInterventionProtocolError("frame-index drift")
    if prereg.get("compute_planning", {}).get("transformer_scheduler_steps") != 24000:
        raise ControlledInterventionProtocolError("scheduler-step count drift")
    return freeze, prereg


def validate_implementation_authority() -> dict:
    validate_design()
    auth = read_json(IMPLEMENTATION_AUTH)
    if auth.get("status") != IMPLEMENTATION_STATUS:
        raise ControlledInterventionProtocolError("implementation authority status drift")
    if bound(auth.get("approved_design", {}), "approved design").resolve() != DESIGN_FREEZE.resolve():
        raise ControlledInterventionProtocolError("approved-design path drift")
    required = (
        "protocol_and_plan_implementation", "runner_implementation",
        "lfe_hook_instrumentation_implementation", "outcome_analyzer_implementation",
        "independent_verifier_implementation", "future_runtime_entrypoint_implementation",
        "cpu_only_synthetic_tests", "cpu_only_no_weight_dry_run", "readiness_record_and_freeze",
    )
    if any(auth.get("authorized", {}).get(key) is not True for key in required):
        raise ControlledInterventionProtocolError("implementation authority incomplete")
    forbidden = (
        "formal_input_audit", "formal_manifest_access", "reference_access_decode_or_preprocessing",
        "outcome_access_annotation_unblinding_construction_or_join", "model_module_or_weight_loading",
        "gpu_engineering_execution", "scientific_generation", "video_or_latent_generation_or_decode",
        "controlled_intervention_execution", "formal_intervention_analysis", "network_access_or_remote_push",
    )
    if any(auth.get("not_authorized", {}).get(key) is not True for key in forbidden):
        raise ControlledInterventionProtocolError("implementation forbidden boundary incomplete")
    return auth


def validate_correction_authority() -> dict:
    validate_design()
    auth = read_json(CORRECTION_AUTH)
    if auth.get("status") != CORRECTION_STATUS:
        raise ControlledInterventionProtocolError("memory-lifecycle correction authority status drift")
    abort = bound(auth.get("abort_freeze", {}), "engineering abort freeze")
    expected_abort = REPO / "governance/mechanism_controlled_intervention_engineering_v1/engineering_run_001_abort_freeze_v1.json"
    if abort.resolve() != expected_abort.resolve():
        raise ControlledInterventionProtocolError("engineering abort freeze path drift")
    if read_json(abort).get("status") != auth.get("abort_freeze", {}).get("required_status"):
        raise ControlledInterventionProtocolError("engineering abort freeze status drift")
    required = (
        "runtime_memory_lifecycle_correction", "acquisition_under_inference_mode",
        "identity_handle_immediate_cpu_transfer", "pipeline_load_deferred_until_all_40_acquisitions",
        "face_models_release_before_pipeline_load", "lifecycle_fail_closed_gates_and_scalar_diagnostics",
        "runner_no_weight_authorization_extension", "cpu_only_synthetic_tests",
        "cpu_only_no_weight_dry_run", "independent_no_weight_verification",
        "correction_readiness_record_evidence_and_freeze",
    )
    if any(auth.get("authorized", {}).get(key) is not True for key in required):
        raise ControlledInterventionProtocolError("memory-lifecycle correction authority incomplete")
    forbidden = (
        "formal_manifest_or_reference_access", "reference_preprocessing_execution",
        "model_module_or_weight_loading", "gpu_execution",
        "engineering_run_001_reuse_retry_or_resume", "new_engineering_execution",
        "scientific_generation", "latent_image_frame_or_video_generation_or_decode",
        "outcome_access_annotation_unblinding_construction_or_join",
        "formal_intervention_analysis_or_hypothesis_testing", "network_access_or_remote_push",
    )
    if any(auth.get("not_authorized", {}).get(key) is not True for key in forbidden):
        raise ControlledInterventionProtocolError("memory-lifecycle forbidden boundary incomplete")
    return auth


def pair_ids(attribute: str) -> tuple[str, ...]:
    if attribute not in ATTRIBUTES:
        raise ControlledInterventionProtocolError(f"unknown attribute: {attribute}")
    return tuple(f"{PAIR_PREFIX[attribute]}_{index:02d}" for index in range(1, 11))


def unit_id(attribute: str, pair_id: str, role: str) -> str:
    if pair_id not in pair_ids(attribute) or role not in ROLES:
        raise ControlledInterventionProtocolError("invalid planned unit key")
    return f"CIU__{pair_id}__{role}"


def task_id(attribute: str, pair_id: str, role: str, seed_index: int) -> str:
    return f"CIT__{unit_id(attribute, pair_id, role)}__S{seed_index}"


def condition_order(source_task_id: str) -> tuple[str, ...]:
    return tuple(sorted(CONDITIONS, key=lambda condition: hashlib.sha256(
        f"{NAMESPACE}|condition_order|{source_task_id}|{condition}".encode()
    ).hexdigest()))


PLAN_FIELDS = (
    "planned_task_id", "planned_unit_id", "formal_pair_id", "attribute", "role",
    "seed_index", "seed", "condition_position", "condition", "scheduler_positions",
    "trajectory_kind", "formal_binding_status",
)


def execution_plan() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for attribute in ATTRIBUTES:
        for pair_id in pair_ids(attribute):
            for role in ROLES:
                planned_unit = unit_id(attribute, pair_id, role)
                for seed_index, seed in enumerate(SEEDS, 1):
                    planned_task = task_id(attribute, pair_id, role, seed_index)
                    for position, condition in enumerate(condition_order(planned_task), 1):
                        rows.append({
                            "planned_task_id": planned_task,
                            "planned_unit_id": planned_unit,
                            "formal_pair_id": pair_id,
                            "attribute": attribute,
                            "role": role,
                            "seed_index": seed_index,
                            "seed": seed,
                            "condition_position": position,
                            "condition": condition,
                            "scheduler_positions": SCHEDULER_POSITIONS,
                            "trajectory_kind": "complete_scientific_trajectory",
                            "formal_binding_status": "DEFERRED_TO_SEPARATELY_AUTHORIZED_INPUT_AUDIT",
                        })
    keys = {(row["planned_task_id"], row["condition"]) for row in rows}
    if len(rows) != 480 or len(keys) != 480:
        raise ControlledInterventionProtocolError("complete trajectory plan drift")
    counts = Counter(str(row["condition"]) for row in rows)
    if counts != Counter({condition: 160 for condition in CONDITIONS}):
        raise ControlledInterventionProtocolError("condition crossing drift")
    return rows


def engineering_pairs() -> dict[str, tuple[str, str]]:
    selected = {}
    for attribute in ATTRIBUTES:
        ranked = sorted(pair_ids(attribute), key=lambda pair: hashlib.sha256(
            f"{pair}|{ENGINEERING_NAMESPACE}".encode()
        ).hexdigest())
        selected[attribute] = (ranked[0], ranked[1])
    return selected


def plan_summary(rows: list[dict[str, object]]) -> dict:
    tasks = {str(row["planned_task_id"]) for row in rows}
    units = {str(row["planned_unit_id"]) for row in rows}
    pairs = {(str(row["attribute"]), str(row["formal_pair_id"])) for row in rows}
    return {
        "plan_rows": len(rows), "source_tasks": len(tasks), "formal_units": len(units),
        "formal_pairs": len(pairs), "conditions": len(CONDITIONS),
        "scientific_trajectories": len(rows),
        "scientific_scheduler_steps": sum(int(row["scheduler_positions"]) for row in rows),
        "held_pair_out_directions": len(pairs) * LFE_TOKENS,
        "fresh_preprocessing_calls": len(units), "direct_lfe_acquisitions": len(units),
        "planned_frame_states": len(rows) * len(FRAME_INDICES),
    }
