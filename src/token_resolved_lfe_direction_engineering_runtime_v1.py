#!/usr/bin/env python3
"""GPU runtime for the separately authorized token-direction Phase-E gate.

The module itself has no top-level ML import. Raw identity/token tensors live
only in process memory and no serializer for them is provided.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import token_resolved_lfe_direction_protocol_v1 as protocol


STATUS_FIELDS = (
    "reference_task_id", "formal_unit_id", "formal_pair_id", "attribute", "role",
    "operation", "status", "started_at_utc", "finished_at_utc",
)
EQUIVALENCE_FIELDS = (
    "formal_unit_id", "formal_pair_id", "attribute", "role",
    "direct_repeat_equal", "direct_hook_equal",
    "direct_repeat_max_abs_difference", "direct_hook_max_abs_difference",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_model_inventory(master: dict) -> dict:
    item = master["artifacts"]["model_weight_hashes"]
    inventory = Path(item["path"])
    protocol.verify_file(inventory, int(item["size_bytes"]), str(item["sha256"]))
    rows = protocol.read_csv(inventory)
    model_root = Path(master["generation"]["model_path"])
    for row in rows:
        protocol.verify_file(
            model_root / row["relative_path"], int(row["size_bytes"]), row["sha256"]
        )
    return {"inventory_rows": len(rows), "all_model_files_rehashed": True}


def _source_rows(master: dict) -> dict[str, dict[str, str]]:
    manifest = Path(master["artifacts"]["generation_manifest"]["path"])
    return {row["task_id"]: row for row in protocol.read_csv(manifest)}


def _max_abs(torch: Any, left: Any, right: Any) -> float:
    return float(torch.max(torch.abs(left - right)).item())


def execute_phase_e(output_dir: Path, authorization_file: Path) -> int:
    # Revalidate through the fail-closed entry point before touching weights.
    from run_token_resolved_lfe_direction_engineering_v1 import validate_active_execution_authorization

    authorization = validate_active_execution_authorization(authorization_file, output_dir)
    phase_started = time.monotonic()
    deadline = phase_started + float(authorization["phase_gpu_hours_ceiling"]) * 3600.0
    master, formal_rows = protocol.validate_formal_master()
    plan = protocol.engineering_plan(formal_rows)
    if len(plan) != 24:
        raise protocol.DirectionProtocolError("Phase-E operation universe drift")

    # Full frozen-weight rehash occurs before ML imports or CUDA initialization.
    model_inventory = verify_model_inventory(master)
    consisid_repo = Path(master["consisid"]["repository"])
    sys.path.insert(0, str(consisid_repo))

    import torch
    from models.consisid_utils import prepare_face_models, process_face_embeddings_infer
    from models.pipeline_consisid import ConsisIDPipeline
    from models.transformer_consisid import ConsisIDTransformer3DModel
    from token_resolved_lfe_direction_instrumentation_v1 import (
        OneShotLfeHook,
        TransientLfeTokenCollector,
        direct_lfe_tokens,
        within_frozen_tolerance,
    )

    if not torch.cuda.is_available():
        raise protocol.DirectionProtocolError("authorized Phase-E requires CUDA")
    if torch.cuda.device_count() != 1:
        raise protocol.DirectionProtocolError("CUDA visibility must resolve to exactly one GPU")
    device = "cuda"
    dtype = torch.bfloat16
    model_path = master["generation"]["model_path"]
    if (Path(model_path) / "transformer_ema").exists():
        raise protocol.DirectionProtocolError("unexpected transformer_ema appeared")

    face_models = prepare_face_models(model_path, device, dtype)
    face_helper_1, face_helper_2, face_clip_model, face_main_model, eva_mean, eva_std = face_models
    transformer = ConsisIDTransformer3DModel.from_pretrained(
        model_path, subfolder="transformer", torch_dtype=dtype
    )
    pipe = ConsisIDPipeline.from_pretrained(model_path, transformer=transformer, torch_dtype=dtype)
    transformer.to(device, dtype=dtype)
    pipe.to(device)
    transformer.local_face_scale = 1.0

    collector = TransientLfeTokenCollector()
    direct: dict[str, dict[int, Any]] = {}
    equivalence_meta: dict[str, dict[str, str]] = {}
    hook_tokens: dict[str, Any] = {}
    statuses: list[dict[str, str]] = []
    sources = _source_rows(master)
    output_dir.mkdir(parents=True, exist_ok=False)
    event_path = output_dir / "phase_e_execution_events_v1.jsonl"

    def enforce_deadline(pipe_instance: Any, step_index: int, timestep: Any, callback_kwargs: dict) -> dict:
        del pipe_instance, step_index, timestep
        if time.monotonic() >= deadline:
            raise protocol.DirectionProtocolError("Phase-E GPU-hour ceiling reached")
        return callback_kwargs

    with event_path.open("x", encoding="utf-8") as events:
        for operation in plan:
            if time.monotonic() >= deadline:
                raise protocol.DirectionProtocolError("Phase-E GPU-hour ceiling reached before operation")
            started = utc_now()
            events.write(json.dumps({"event": "OPERATION_START", "at": started, "reference_task_id": operation["reference_task_id"]}, sort_keys=True) + "\n")
            events.flush()
            source = sources[operation["source_task_id"]]
            reference = Path(source["reference_image_path"])
            if not reference.is_file() or reference.is_symlink():
                raise protocol.DirectionProtocolError(f"frozen reference missing: {reference}")
            if protocol.sha256(reference) != source["reference_image_sha256"]:
                raise protocol.DirectionProtocolError(f"frozen reference hash drift: {reference}")
            id_cond, id_vit_hidden, image, face_kps = process_face_embeddings_infer(
                face_helper_1, face_clip_model, face_helper_2, eva_mean, eva_std,
                face_main_model, device, dtype, str(reference), is_align_face=True,
            )
            unit = operation["formal_unit_id"]
            if operation["operation"].startswith("direct_lfe_repeat_"):
                with torch.inference_mode():
                    current_direct_raw = direct_lfe_tokens(transformer, id_cond, id_vit_hidden)
                current_direct = current_direct_raw.detach().float().cpu()[0].clone()
                repeat = int(operation["operation"].rsplit("_", 1)[1])
                collector.add_engineering_direct(unit, repeat, current_direct_raw)
                direct.setdefault(unit, {})[repeat] = current_direct
            else:
                hook = OneShotLfeHook()
                handle = transformer.local_facial_extractor.register_forward_hook(hook)
                try:
                    generator = torch.Generator(device).manual_seed(int(operation["seed"]))
                    with torch.inference_mode():
                        pipeline_output = pipe(
                            prompt=master["generation"]["prompt"],
                            negative_prompt=master["generation"]["negative_prompt"],
                            image=image,
                            num_videos_per_prompt=1,
                            num_inference_steps=1,
                            num_frames=master["generation"]["num_frames"],
                            use_dynamic_cfg=False,
                            guidance_scale=master["generation"]["guidance_scale"],
                            generator=generator,
                            id_vit_hidden=id_vit_hidden,
                            id_cond=id_cond,
                            kps_cond=face_kps,
                            output_type="latent",
                            callback_on_step_end=enforce_deadline,
                        )
                    del pipeline_output
                finally:
                    handle.remove()
                captured = hook.require_tokens()
                collector.add_engineering_hook(unit, captured.unsqueeze(0))
                hook_tokens[unit] = captured
                equivalence_meta[unit] = {
                    key: operation[key]
                    for key in ("formal_unit_id", "formal_pair_id", "attribute", "role")
                }
                if unit not in direct or 1 not in direct[unit]:
                    raise protocol.DirectionProtocolError(f"hook preceded direct baseline: {unit}")
                if not within_frozen_tolerance(direct[unit][1], captured):
                    raise protocol.DirectionProtocolError(f"direct/hook mismatch: {unit}")
            finished = utc_now()
            statuses.append({
                "reference_task_id": operation["reference_task_id"],
                "formal_unit_id": unit,
                "formal_pair_id": operation["formal_pair_id"],
                "attribute": operation["attribute"],
                "role": operation["role"],
                "operation": operation["operation"],
                "status": "COMPLETE_TRANSIENT_TENSORS_ONLY",
                "started_at_utc": started,
                "finished_at_utc": finished,
            })
            events.write(json.dumps({"event": "OPERATION_COMPLETE", "at": finished, "reference_task_id": operation["reference_task_id"]}, sort_keys=True) + "\n")
            events.flush()

    control = collector.validate_engineering()
    equivalence_rows = []
    for unit in sorted(direct):
        first, second, hooked = direct[unit][1], direct[unit][2], hook_tokens[unit]
        equivalence_rows.append({
            **equivalence_meta[unit],
            "direct_repeat_equal": within_frozen_tolerance(first, second),
            "direct_hook_equal": within_frozen_tolerance(first, hooked),
            "direct_repeat_max_abs_difference": format(_max_abs(torch, first, second), ".17g"),
            "direct_hook_max_abs_difference": format(_max_abs(torch, first, hooked), ".17g"),
        })
    protocol.atomic_csv(output_dir / "phase_e_task_status_v1.csv", STATUS_FIELDS, statuses)
    protocol.atomic_csv(output_dir / "phase_e_equivalence_controls_v1.csv", EQUIVALENCE_FIELDS, equivalence_rows)
    summary = {
        "schema_version": 1,
        "status": "PHASE_E_COMPLETE_PENDING_INDEPENDENT_VERIFICATION",
        "authorization_path": str(authorization_file.resolve()),
        "authorization_sha256": protocol.sha256(authorization_file),
        "engineering_control": control,
        "model_inventory": model_inventory,
        "operations_complete": len(statuses),
        "transformer_steps_executed": 8,
        "full_diffusion_trajectories": 0,
        "decoded_media_files_written": 0,
        "raw_identity_or_token_tensor_files_written": 0,
        "scientific_extraction_run": False,
        "outcomes_opened_or_joined": False,
        "elapsed_gpu_hours": (time.monotonic() - phase_started) / 3600.0,
        "phase_gpu_hours_ceiling": float(authorization["phase_gpu_hours_ceiling"]),
    }
    protocol.atomic_json(output_dir / "phase_e_execution_summary_v1.json", summary)
    return 0
