#!/usr/bin/env python3
"""Future single-GPU runtime for the frozen token-direction v2 transaction."""
from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import token_resolved_lfe_direction_protocol_v2 as protocol


STATUS_FIELDS = (
    "v2_task_id", "source_task_id", "formal_unit_id", "formal_pair_id",
    "attribute", "role", "seed_index", "seed", "preprocessing_calls",
    "direct_lfe_calls", "status", "started_at_utc", "finished_at_utc",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_weights(master: dict) -> int:
    item = master["artifacts"]["model_weight_hashes"]
    inventory = Path(item["path"])
    protocol.verify_file(inventory, int(item["size_bytes"]), item["sha256"])
    rows = protocol.read_csv(inventory)
    root = Path(master["generation"]["model_path"])
    for row in rows:
        protocol.verify_file(root / row["relative_path"], int(row["size_bytes"]), row["sha256"])
    return len(rows)


def execute_token_direction_v2(output: Path, auth_file: Path) -> int:
    from run_token_resolved_lfe_direction_v2 import validate_active

    auth = validate_active(auth_file, output)
    started_clock = time.monotonic()
    deadline = started_clock + float(auth["phase_gpu_hours_ceiling"]) * 3600
    master, formal = protocol.formal_rows()
    plan = protocol.execution_plan(formal)
    weight_rows = verify_weights(master)
    protocol.verify_file(protocol.RUN003, protocol.RUN003_BYTES, protocol.RUN003_SHA256)
    historical = protocol.read_csv(protocol.RUN003)

    consisid = Path(master["consisid"]["repository"])
    sys.path.insert(0, str(consisid))
    import torch
    from models.consisid_utils import prepare_face_models, process_face_embeddings_infer
    from models.transformer_consisid import ConsisIDTransformer3DModel
    from analyze_token_resolved_lfe_direction_v2 import analyze_transient, write_outputs
    from verify_token_resolved_lfe_direction_v2 import verify_transient

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise protocol.DirectionV2ProtocolError("exactly one visible GPU required")
    device = "cuda"
    dtype = torch.bfloat16
    model_path = master["generation"]["model_path"]
    face = prepare_face_models(model_path, device, dtype)
    face_helper_1, face_helper_2, face_clip_model, face_main_model, eva_mean, eva_std = face
    transformer = ConsisIDTransformer3DModel.from_pretrained(
        model_path, subfolder="transformer", torch_dtype=dtype
    )
    transformer.to(device, dtype=dtype)
    transformer.local_face_scale = 1.0

    sources = {row["task_id"]: row for row in formal}
    tensors: dict = {}
    metadata: dict = {}
    statuses = []
    for task in plan:
        if time.monotonic() >= deadline:
            raise protocol.DirectionV2ProtocolError("GPU-hour ceiling reached before task")
        unit = task["formal_unit_id"]
        seed_index = task["seed_index"]
        source = sources[task["source_task_id"]]
        reference = Path(source["reference_image_path"])
        if not reference.is_file() or reference.is_symlink() or protocol.sha256(reference) != source["reference_image_sha256"]:
            raise protocol.DirectionV2ProtocolError(f"reference drift: {reference}")
        if unit not in tensors:
            tensors[unit] = {}
            metadata[unit] = {key: task[key] for key in ("formal_pair_id", "attribute", "role")}
        elif metadata[unit] != {key: task[key] for key in ("formal_pair_id", "attribute", "role")}:
            raise protocol.DirectionV2ProtocolError(f"unit metadata drift: {unit}")
        task_started = now()
        id_cond, id_vit_hidden, image, face_kps = process_face_embeddings_infer(
            face_helper_1, face_clip_model, face_helper_2, eva_mean, eva_std,
            face_main_model, device, dtype, str(reference), is_align_face=True,
        )
        with torch.inference_mode():
            first = transformer.local_facial_extractor(id_cond, id_vit_hidden)
            second = transformer.local_facial_extractor(id_cond, id_vit_hidden) if seed_index == "1" else None
        record = {"D1": first.detach().float().cpu().clone()}
        if second is not None:
            record["D2"] = second.detach().float().cpu().clone()
        tensors[unit][seed_index] = record
        statuses.append({
            **{key: task[key] for key in ("v2_task_id", "source_task_id", "formal_unit_id", "formal_pair_id", "attribute", "role", "seed_index", "seed")},
            "preprocessing_calls": 1,
            "direct_lfe_calls": 2 if seed_index == "1" else 1,
            "status": "COMPLETE_TRANSIENT_ONLY",
            "started_at_utc": task_started,
            "finished_at_utc": now(),
        })
        del id_cond, id_vit_hidden, image, face_kps, first, second
        if time.monotonic() >= deadline:
            raise protocol.DirectionV2ProtocolError("GPU-hour ceiling reached after task")

    if len(statuses) != 160 or len(tensors) != 40:
        raise protocol.DirectionV2ProtocolError("incomplete acquisition transaction")
    result = analyze_transient(tensors, metadata, historical)
    verification = verify_transient(tensors, metadata, historical, result)

    staging = output.with_name(output.name + ".partial")
    if output.exists() or staging.exists():
        raise protocol.DirectionV2ProtocolError("runtime output or staging directory already exists")
    staging.mkdir(parents=True, exist_ok=False)
    write_outputs(staging, result)
    protocol.atomic_csv(staging / "token_direction_v2_execution_status.csv", STATUS_FIELDS, statuses)
    protocol.atomic_json(staging / "token_direction_v2_in_memory_verification.json", verification)
    summary = {
        "schema_version": 2,
        "status": "COMPLETE_TOKEN_DIRECTION_V2_PENDING_PERSISTED_VERIFICATION",
        "authorization_path": str(auth_file.resolve()),
        "authorization_sha256": protocol.sha256(auth_file),
        "formal_units": 40,
        "source_records": 160,
        "fresh_preprocessing_calls": 160,
        "direct_lfe_calls": 200,
        "direct_control_rows": 40,
        "four_label_rows": 120,
        "current_pooled_rows": 20,
        "historical_rows": 20,
        "token_margin_rows": 640,
        "token_panel_rows": 64,
        "pair_sign_rows": 20,
        "transformer_steps": 0,
        "full_diffusion_trajectories": 0,
        "decoded_media_files": 0,
        "raw_identity_or_token_tensor_files": 0,
        "outcomes_opened_or_joined": False,
        "associations_computed": 0,
        "model_weight_rows_rehashed": weight_rows,
        "elapsed_gpu_hours": (time.monotonic() - started_clock) / 3600,
        "phase_gpu_hours_ceiling": float(auth["phase_gpu_hours_ceiling"]),
    }
    protocol.atomic_json(staging / "token_direction_v2_execution_summary.json", summary)
    staging.replace(output)
    return 0
