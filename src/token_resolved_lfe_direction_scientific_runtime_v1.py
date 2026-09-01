#!/usr/bin/env python3
"""Transient-only single-GPU scientific runtime for token direction v1."""
from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import token_resolved_lfe_direction_protocol_v1 as protocol


FROZEN_POOLED = Path("/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003/representation_margins_v1.csv")
FROZEN_POOLED_BYTES = 15152
FROZEN_POOLED_SHA256 = "5e1d14990eba4ad20ae9ec790850bc2ae344177bcadd61aff61c92c372e85506"
STATUS_FIELDS = ("reference_task_id", "source_task_id", "formal_unit_id", "formal_pair_id", "attribute", "role", "seed_index", "seed", "status", "started_at_utc", "finished_at_utc")


def utc_now() -> str: return datetime.now(timezone.utc).isoformat()


def verify_weights(master: dict) -> int:
    item = master["artifacts"]["model_weight_hashes"]
    inventory = Path(item["path"])
    protocol.verify_file(inventory, int(item["size_bytes"]), item["sha256"])
    rows = protocol.read_csv(inventory); root = Path(master["generation"]["model_path"])
    for row in rows: protocol.verify_file(root / row["relative_path"], int(row["size_bytes"]), row["sha256"])
    return len(rows)


def execute_scientific(output_dir: Path, auth_file: Path) -> int:
    from run_token_resolved_lfe_direction_scientific_v1 import validate_active
    auth = validate_active(auth_file, output_dir)
    started_clock = time.monotonic(); deadline = started_clock + float(auth["phase_gpu_hours_ceiling"]) * 3600
    master, formal = protocol.validate_formal_master(); plan = protocol.scientific_reference_plan(formal)
    if len(plan) != 160: raise protocol.DirectionProtocolError("scientific plan drift")
    weight_rows = verify_weights(master)
    protocol.verify_file(FROZEN_POOLED, FROZEN_POOLED_BYTES, FROZEN_POOLED_SHA256)
    frozen_pooled = protocol.read_csv(FROZEN_POOLED)
    consisid = Path(master["consisid"]["repository"]); sys.path.insert(0, str(consisid))

    import torch
    from models.consisid_utils import prepare_face_models, process_face_embeddings_infer
    from models.transformer_consisid import ConsisIDTransformer3DModel
    from token_resolved_lfe_direction_instrumentation_v1 import TransientLfeTokenCollector, direct_lfe_tokens
    import analyze_token_resolved_lfe_direction_v1 as analyzer
    import verify_token_resolved_lfe_direction_v1 as verifier

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise protocol.DirectionProtocolError("scientific run requires exactly one visible CUDA GPU")
    device="cuda"; dtype=torch.bfloat16; model_path=master["generation"]["model_path"]
    if (Path(model_path)/"transformer_ema").exists(): raise protocol.DirectionProtocolError("unexpected transformer_ema")
    face_models=prepare_face_models(model_path,device,dtype)
    face_helper_1,face_helper_2,face_clip_model,face_main_model,eva_mean,eva_std=face_models
    transformer=ConsisIDTransformer3DModel.from_pretrained(model_path,subfolder="transformer",torch_dtype=dtype)
    transformer.to(device,dtype=dtype); transformer.local_face_scale=1.0
    sources={row["task_id"]:row for row in formal}; collector=TransientLfeTokenCollector()
    exact: dict[str,Any]={}; statuses=[]
    for task in plan:
        if time.monotonic() >= deadline: raise protocol.DirectionProtocolError("scientific GPU-hour ceiling reached")
        started=utc_now(); source=sources[task["source_task_id"]]; reference=Path(source["reference_image_path"])
        if not reference.is_file() or reference.is_symlink() or protocol.sha256(reference)!=source["reference_image_sha256"]:
            raise protocol.DirectionProtocolError(f"scientific reference drift: {reference}")
        id_cond,id_vit_hidden,image,face_kps=process_face_embeddings_infer(face_helper_1,face_clip_model,face_helper_2,eva_mean,eva_std,face_main_model,device,dtype,str(reference),is_align_face=True)
        with torch.inference_mode(): raw=direct_lfe_tokens(transformer,id_cond,id_vit_hidden)
        collector.add_scientific(task,raw)
        current=raw.detach().float().cpu()[0].clone(); unit=task["formal_unit_id"]
        if unit in exact and not torch.equal(exact[unit],current):
            raise protocol.DirectionProtocolError(f"seed-labelled LFE copies are not bit-exact: {unit}")
        exact.setdefault(unit,current)
        finished=utc_now(); statuses.append({**{key:task[key] for key in STATUS_FIELDS[:8]},"status":"COMPLETE_TRANSIENT_ONLY","started_at_utc":started,"finished_at_utc":finished})
        del id_cond,id_vit_hidden,image,face_kps,raw,current
    unit_tokens,metadata=collector.finalize_scientific()
    if set(unit_tokens)!=set(exact) or len(exact)!=40: raise protocol.DirectionProtocolError("exact-copy unit universe drift")
    result=analyzer.analyze_transient_tokens(unit_tokens,metadata,frozen_pooled)
    in_memory=verifier.verify_transient_results(unit_tokens,metadata,result)
    if in_memory.get("status")!="PASS_INDEPENDENT_IN_MEMORY_TOKEN_DIRECTION_RECOMPUTATION":
        raise protocol.DirectionProtocolError("independent in-memory recomputation failed")
    analyzer.write_outputs(output_dir,result)
    protocol.atomic_csv(output_dir/"scientific_extraction_status_v1.csv",STATUS_FIELDS,statuses)
    protocol.atomic_json(output_dir/"scientific_in_memory_verification_v1.json",in_memory)
    summary={
        "schema_version":1,"status":"SCIENTIFIC_TOKEN_DIRECTION_COMPLETE_PENDING_PERSISTED_OUTPUT_VERIFICATION",
        "authorization_path":str(auth_file.resolve()),"authorization_sha256":protocol.sha256(auth_file),
        "scientific_reference_records":160,"formal_units":40,"seed_labelled_copies_per_unit":4,
        "seed_labelled_copies_bit_exact":True,"token_margin_rows":640,"token_panel_rows":64,
        "pair_token_sign_rows":20,"pooled_replication_rows":20,"weight_inventory_rows_rehashed":weight_rows,
        "transformer_steps":0,"full_diffusion_trajectories":0,"decoded_media_files":0,
        "raw_identity_or_token_tensor_files":0,"outcomes_opened_or_joined":False,"associations_computed":0,
        "elapsed_gpu_hours":(time.monotonic()-started_clock)/3600,"phase_gpu_hours_ceiling":float(auth["phase_gpu_hours_ceiling"]),
    }
    protocol.atomic_json(output_dir/"scientific_execution_summary_v1.json",summary)
    return 0
