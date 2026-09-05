#!/usr/bin/env python3
"""Independent verifier for controlled-intervention dry plans and future analysis."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import controlled_lfe_projection_exchange_protocol_v1 as protocol


class ControlledInterventionVerificationError(RuntimeError):
    """Raised when an independent recomputation or safety audit fails."""


CODE_NAMES = (
    "controlled_lfe_projection_exchange_protocol_v1.py",
    "controlled_lfe_projection_exchange_instrumentation_v1.py",
    "controlled_lfe_projection_exchange_runtime_v1.py",
    "run_controlled_lfe_projection_exchange_v1.py",
    "analyze_controlled_lfe_projection_exchange_v1.py",
    "verify_controlled_lfe_projection_exchange_v1.py",
)


def assert_static_safety() -> dict:
    top_level_ml = []
    serializers = []
    for name in CODE_NAMES:
        path = protocol.REPO / "src" / name
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            )
            if any(item.split(".")[0] in {"torch", "models", "diffusers", "transformers"} for item in names):
                top_level_ml.append(name)
        text = path.read_text(encoding="utf-8")
        # Build the spellings so this verifier does not flag its own deny-list literals.
        for forbidden in ("torch" + ".save", "numpy" + ".save", "np" + ".save", "pickle" + ".dump"):
            if forbidden in text:
                serializers.append(f"{name}:{forbidden}")
    if top_level_ml or serializers:
        raise ControlledInterventionVerificationError(
            f"static safety failure: top_level_ml={top_level_ml}, serializers={serializers}"
        )
    runtime_text = (protocol.REPO / "src" / "controlled_lfe_projection_exchange_runtime_v1.py").read_text(encoding="utf-8")
    private_latent_sites = runtime_text.count("save_file({\"final_latents\": latent}, str(path))")
    if private_latent_sites != 1:
        raise ControlledInterventionVerificationError("future private final-latent serializer site drift")
    lifecycle_markers = (
        "with self.torch.inference_mode():\n            values = self.process_face",
        '"id_cond": self._cpu_clone(id_cond)',
        '"id_vit_hidden": [self._cpu_clone(tensor) for tensor in id_vit_hidden]',
        "self.pipe = None",
        "def finish_acquisition",
        "lifecycle = adapter.finish_acquisition()",
    )
    if any(marker not in runtime_text for marker in lifecycle_markers):
        raise ControlledInterventionVerificationError("memory-lifecycle correction marker missing")
    finish_call = runtime_text.index("lifecycle = adapter.finish_acquisition()")
    direction_build = runtime_text.index("bundle = build_transient_interventions")
    release = runtime_text.index('"face_helper_1", "face_helper_2", "face_clip_model"')
    pipeline_load = runtime_text.index("self.pipe = self.pipeline_class.from_pretrained")
    if not finish_call < direction_build or not release < pipeline_load:
        raise ControlledInterventionVerificationError("memory-lifecycle ordering drift")
    return {
        "top_level_ml_imports": 0,
        "forbidden_identity_lfe_or_direction_tensor_serializers": 0,
        "future_private_final_latent_serializer_sites": private_latent_sites,
        "memory_lifecycle_correction_static_gate": True,
    }


def _expected_plan() -> list[dict[str, str]]:
    rows = []
    for attribute, prefix in (("eyeglasses", "FEY"), ("facial_hair", "FFH")):
        for pair_index in range(1, 11):
            pair = f"{prefix}_{pair_index:02d}"
            for role in ("positive", "control"):
                unit = f"CIU__{pair}__{role}"
                for seed_index, seed in enumerate((2686238281, 280026145, 2169901996, 2046930553), 1):
                    task = f"CIT__{unit}__S{seed_index}"
                    order = sorted(protocol.CONDITIONS, key=lambda condition: hashlib.sha256(
                        f"controlled_lfe_projection_exchange_v1|condition_order|{task}|{condition}".encode()
                    ).hexdigest())
                    for position, condition in enumerate(order, 1):
                        rows.append({
                            "planned_task_id": task, "planned_unit_id": unit,
                            "formal_pair_id": pair, "attribute": attribute, "role": role,
                            "seed_index": str(seed_index), "seed": str(seed),
                            "condition_position": str(position), "condition": condition,
                            "scheduler_positions": "50", "trajectory_kind": "complete_scientific_trajectory",
                            "formal_binding_status": "DEFERRED_TO_SEPARATELY_AUTHORIZED_INPUT_AUDIT",
                        })
    return rows


def verify_dry_run(run_dir: Path) -> dict:
    plan_path = run_dir / "controlled_intervention_no_weight_plan_v1.csv"
    summary_path = run_dir / "controlled_intervention_no_weight_dry_run_v1.json"
    observed = protocol.read_csv(plan_path)
    expected = _expected_plan()
    if observed != expected or len(observed) != 480:
        raise ControlledInterventionVerificationError("dry-run plan differs from independent complete-family enumeration")
    summary = protocol.read_json(summary_path)
    expected_counts = {
        "plan_rows": 480, "source_tasks": 160, "formal_units": 40, "formal_pairs": 20,
        "conditions": 3, "scientific_trajectories": 480,
        "scientific_scheduler_steps": 24000, "held_pair_out_directions": 640,
        "fresh_preprocessing_calls": 40, "direct_lfe_acquisitions": 40,
        "planned_frame_states": 3360,
    }
    if summary.get("status") != protocol.DRY_PASS_STATUS:
        raise ControlledInterventionVerificationError("dry-run status mismatch")
    if any(summary.get(key) != value for key, value in expected_counts.items()):
        raise ControlledInterventionVerificationError("dry-run summary count drift")
    forbidden_flags = (
        "formal_manifest_opened", "reference_opened_or_preprocessed", "outcome_opened",
        "model_modules_imported", "weights_loaded", "gpu_used", "trajectory_executed",
        "video_or_latent_generated", "video_decoded", "intervention_executed",
        "formal_analysis_computed", "network_used", "torch_imported",
    )
    if any(summary.get(key) is not False for key in forbidden_flags):
        raise ControlledInterventionVerificationError("dry-run forbidden-action flag is not false")
    correction_flags = (
        "memory_lifecycle_correction_bound", "acquisition_inference_mode_planned",
        "identity_handles_cpu_resident_planned", "pipeline_load_after_40_acquisitions_planned",
        "face_models_release_before_pipeline_load_planned",
    )
    if summary.get("memory_lifecycle_correction_bound") is True and any(
        summary.get(key) is not True for key in correction_flags
    ):
        raise ControlledInterventionVerificationError("correction dry-run lifecycle plan drift")
    suffixes = {".pt", ".pth", ".npy", ".npz", ".safetensors", ".png", ".jpg", ".jpeg", ".mp4"}
    if any(path.is_file() and path.suffix.lower() in suffixes for path in run_dir.iterdir()):
        raise ControlledInterventionVerificationError("dry-run persisted tensor or media")
    safety = assert_static_safety()
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_CONTROLLED_INTERVENTION_NO_WEIGHT_DRY_RUN_VERIFICATION",
        **expected_counts, **safety,
        "formal_manifest_opened": False, "reference_opened_or_preprocessed": False,
        "outcome_opened": False, "model_or_weight_loading": False, "gpu_used": False,
        "trajectory_or_intervention_executed": False, "media_or_latent_generated": False,
        "formal_analysis_computed": False, "network_used": False,
        "memory_lifecycle_correction_bound": summary.get("memory_lifecycle_correction_bound", False),
    }


def _value(attribute: str, label: str) -> float | None:
    valid = {"eyeglasses": {"present": 1.0, "absent": 0.0, "U": None},
             "facial_hair": {"0": 0.0, "1": 1.0, "2": 1.0, "U": None}}
    try:
        return valid[attribute][label]
    except KeyError as error:
        raise ControlledInterventionVerificationError(f"invalid label: {attribute}/{label}") from error


def _independent_primary(rows: list[dict[str, object]]) -> tuple[dict, list[dict], list[dict]]:
    groups: dict[tuple[str, str, str, str], dict[tuple[int, int], list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        key4 = (str(row["attribute"]), str(row["formal_pair_id"]), str(row["role"]), str(row["condition"]))
        key2 = (int(row["seed"]), int(row["frame_index"]))
        groups[key4][key2].append((str(row["final_label"]), str(row["observability_reason"])))
    scores = {}
    missing = []
    expected_subkeys = {(seed, frame) for seed in protocol.SEEDS for frame in protocol.FRAME_INDICES}
    for attribute in protocol.ATTRIBUTES:
        for pair in protocol.pair_ids(attribute):
            for role in protocol.ROLES:
                for condition in protocol.CONDITIONS:
                    key = (attribute, pair, role, condition)
                    group = groups.get(key, {})
                    absent = expected_subkeys - set(group)
                    extras = set(group) - expected_subkeys
                    duplicates = sum(max(0, len(value) - 1) for value in group.values())
                    values = []
                    for subkey in expected_subkeys:
                        entries = group.get(subkey, ())
                        if len(entries) == 1:
                            label, reason = entries[0]
                            if label == "U" and not reason.strip():
                                raise ControlledInterventionVerificationError("U without reason")
                            value = _value(attribute, label)
                            if value is not None:
                                values.append(value)
                    scores[key] = statistics.fmean(values) if not absent and not extras and not duplicates and values else None
                    if scores[key] is None:
                        missing.append({"key": key, "missing": len(absent), "duplicates": duplicates, "zero_valid": not values})
    pair_rows = []
    for attribute in protocol.ATTRIBUTES:
        for pair in protocol.pair_ids(attribute):
            def contrast(
                role: str, left: str, right: str,
                attribute_key: str = attribute, pair_key: str = pair,
            ) -> float | None:
                a, b = scores[(attribute_key, pair_key, role, left)], scores[(attribute_key, pair_key, role, right)]
                return None if a is None or b is None else a - b
            positive = contrast("positive", "target_projection_exchange", "orthogonal_sham")
            control = contrast("control", "target_projection_exchange", "orthogonal_sham")
            complete_pair = all(scores[(attribute, pair, role, condition)] is not None
                                for role in protocol.ROLES for condition in protocol.CONDITIONS)
            effect = None if not complete_pair or positive is None or control is None else 0.5 * (control - positive)
            pair_rows.append({"attribute": attribute, "formal_pair_id": pair, "effect": effect})
    summaries = []
    for attribute in protocol.ATTRIBUTES:
        values = [row["effect"] for row in pair_rows if row["attribute"] == attribute and row["effect"] is not None]
        if len(values) == 10:
            labels = Counter("tie" if abs(value) <= 1e-8 else "correct" if value > 0 else "wrong" for value in values)
            summaries.append({"attribute": attribute, "complete": True, "counts": (labels["correct"], labels["tie"], labels["wrong"]),
                              "stats": (statistics.fmean(values), statistics.median(values), min(values), max(values))})
        else:
            summaries.append({"attribute": attribute, "complete": False, "pairs": len(values)})
    return scores, pair_rows, summaries


def verify_analysis(rows: list[dict[str, object]], observed: dict) -> dict:
    _scores, pairs, summaries = _independent_primary(rows)
    observed_pairs = {(row["attribute"], row["formal_pair_id"]): row for row in observed["pair_effects"]}
    if len(observed_pairs) != 20:
        raise ControlledInterventionVerificationError("observed pair family count drift")
    for expected in pairs:
        actual = observed_pairs[(expected["attribute"], expected["formal_pair_id"])]["primary_role_aligned_target_minus_sham"]
        value = expected["effect"]
        if (actual is None) != (value is None) or (value is not None and not math.isclose(float(actual), float(value), rel_tol=0, abs_tol=1e-15)):
            raise ControlledInterventionVerificationError("primary pair-effect recomputation mismatch")
    observed_summaries = {row["attribute"]: row for row in observed["attribute_summaries"]}
    for expected in summaries:
        actual = observed_summaries[expected["attribute"]]
        if actual["aggregate_computed"] is not expected["complete"]:
            raise ControlledInterventionVerificationError("aggregate missingness policy mismatch")
        if expected["complete"]:
            if (actual["correct_count"], actual["tie_count"], actual["wrong_count"]) != expected["counts"]:
                raise ControlledInterventionVerificationError("aggregate direction counts mismatch")
            values = (actual["mean"], actual["median"], actual["minimum"], actual["maximum"])
            if any(not math.isclose(float(a), float(b), rel_tol=0, abs_tol=1e-15) for a, b in zip(values, expected["stats"])):
                raise ControlledInterventionVerificationError("aggregate summary mismatch")
    if observed.get("p_values_computed") is not False or observed.get("cross_attribute_pooling_or_ranking_computed") is not False:
        raise ControlledInterventionVerificationError("forbidden analysis family present")
    return {
        "schema_version": 1, "status": "PASS_INDEPENDENT_CONTROLLED_INTERVENTION_ANALYSIS_RECOMPUTATION",
        "input_rows": len(rows), "pair_effects_recomputed": 20,
        "complete_attribute_aggregates": sum(item["complete"] for item in summaries),
        "reduced_panel_aggregates_computed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("dry-run",))
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify_dry_run(args.run_dir)
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ControlledInterventionVerificationError, protocol.ControlledInterventionProtocolError, KeyError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
