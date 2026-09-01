#!/usr/bin/env python3
"""Future GPU runtime for complete-panel direct-hook diagnostic v1."""
from __future__ import annotations
import sys,time
from datetime import datetime,timezone
from pathlib import Path
import token_resolved_lfe_direct_hook_diagnostic_protocol_v1 as protocol

STATUS_FIELDS=("diagnostic_task_id","formal_unit_id","formal_pair_id","attribute","role","status","started_at_utc","finished_at_utc")
def now():return datetime.now(timezone.utc).isoformat()
def verify_weights(master:dict)->int:
    item=master["artifacts"]["model_weight_hashes"];inventory=Path(item["path"]);protocol.verify_file(inventory,int(item["size_bytes"]),item["sha256"]);rows=protocol.read_csv(inventory);root=Path(master["generation"]["model_path"])
    for row in rows:protocol.verify_file(root/row["relative_path"],int(row["size_bytes"]),row["sha256"])
    return len(rows)
def execute_diagnostic(output:Path,auth_file:Path)->int:
    from run_token_resolved_lfe_direct_hook_diagnostic_v1 import validate_active
    auth=validate_active(auth_file,output);started_clock=time.monotonic();deadline=started_clock+float(auth["phase_gpu_hours_ceiling"])*3600
    master,formal=protocol.formal_rows();plan=protocol.diagnostic_plan(formal);weight_rows=verify_weights(master);protocol.verify_file(protocol.RUN003,protocol.RUN003_BYTES,protocol.RUN003_SHA256);frozen=protocol.read_csv(protocol.RUN003)
    consisid=Path(master["consisid"]["repository"]);sys.path.insert(0,str(consisid))
    import torch
    from models.consisid_utils import prepare_face_models,process_face_embeddings_infer
    from models.pipeline_consisid import ConsisIDPipeline
    from models.transformer_consisid import ConsisIDTransformer3DModel
    from token_resolved_lfe_direction_instrumentation_v1 import OneShotLfeHook,direct_lfe_tokens
    from analyze_token_resolved_lfe_direct_hook_diagnostic_v1 import analyze_transient,EQUIV_FIELDS,POOLED_FIELDS
    from verify_token_resolved_lfe_direct_hook_diagnostic_v1 import verify_transient
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise protocol.DiagnosticProtocolError("exactly one visible GPU required")
    device="cuda";dtype=torch.bfloat16;model_path=master["generation"]["model_path"]
    face=prepare_face_models(model_path,device,dtype);face_helper_1,face_helper_2,face_clip_model,face_main_model,eva_mean,eva_std=face
    transformer=ConsisIDTransformer3DModel.from_pretrained(model_path,subfolder="transformer",torch_dtype=dtype);pipe=ConsisIDPipeline.from_pretrained(model_path,transformer=transformer,torch_dtype=dtype);transformer.to(device,dtype=dtype);pipe.to(device);transformer.local_face_scale=1.0
    sources={r["task_id"]:r for r in formal};direct={};hooked={};meta={};statuses=[]
    def deadline_callback(pipe_instance,step_index,timestep,kwargs):
        del pipe_instance,step_index,timestep
        if time.monotonic()>=deadline:raise protocol.DiagnosticProtocolError("GPU-hour ceiling reached")
        return kwargs
    for task in plan:
        if time.monotonic()>=deadline:raise protocol.DiagnosticProtocolError("GPU-hour ceiling reached before unit")
        started=now();source=sources[task["source_task_id"]];reference=Path(source["reference_image_path"])
        if not reference.is_file() or reference.is_symlink() or protocol.sha256(reference)!=source["reference_image_sha256"]:raise protocol.DiagnosticProtocolError(f"reference drift: {reference}")
        id_cond,id_vit_hidden,image,face_kps=process_face_embeddings_infer(face_helper_1,face_clip_model,face_helper_2,eva_mean,eva_std,face_main_model,device,dtype,str(reference),is_align_face=True)
        with torch.inference_mode():direct_raw=direct_lfe_tokens(transformer,id_cond,id_vit_hidden)
        shot=OneShotLfeHook();handle=transformer.local_facial_extractor.register_forward_hook(shot)
        try:
            generator=torch.Generator(device).manual_seed(int(task["seed"]))
            with torch.inference_mode():latent=pipe(prompt=master["generation"]["prompt"],negative_prompt=master["generation"]["negative_prompt"],image=image,num_videos_per_prompt=1,num_inference_steps=1,num_frames=49,use_dynamic_cfg=False,guidance_scale=6.0,generator=generator,id_vit_hidden=id_vit_hidden,id_cond=id_cond,kps_cond=face_kps,output_type="latent",callback_on_step_end=deadline_callback)
            del latent
        finally:handle.remove()
        unit=task["formal_unit_id"];direct[unit]=direct_raw.detach().float().cpu().clone();hooked[unit]=shot.require_tokens().unsqueeze(0);meta[unit]={k:task[k] for k in ("formal_pair_id","attribute","role")};finished=now();statuses.append({"diagnostic_task_id":task["diagnostic_task_id"],"formal_unit_id":unit,"formal_pair_id":task["formal_pair_id"],"attribute":task["attribute"],"role":task["role"],"status":"COMPLETE_TRANSIENT_ONLY","started_at_utc":started,"finished_at_utc":finished})
        del id_cond,id_vit_hidden,image,face_kps,direct_raw
    result=analyze_transient(direct,hooked,meta,frozen);verification=verify_transient(direct,hooked,meta,frozen,result)
    output.mkdir(parents=True,exist_ok=False);protocol.atomic_csv(output/"direct_hook_equivalence_v1.csv",EQUIV_FIELDS,result["equivalence"]);protocol.atomic_csv(output/"hook_pooled_replication_v1.csv",POOLED_FIELDS,result["hook_pooled"]);protocol.atomic_csv(output/"diagnostic_execution_status_v1.csv",STATUS_FIELDS,statuses);protocol.atomic_json(output/"diagnostic_in_memory_verification_v1.json",verification)
    summary={"schema_version":1,"status":"COMPLETE_PANEL_DIRECT_HOOK_DIAGNOSTIC_COMPLETE_PENDING_PERSISTED_VERIFICATION","authorization_path":str(auth_file.resolve()),"authorization_sha256":protocol.sha256(auth_file),"formal_units":40,"direct_lfe_calls":40,"one_step_hook_controls":40,"transformer_steps":40,"full_diffusion_trajectories":0,"direct_hook_rows":40,"hook_pooled_rows":20,"token_margin_rows":0,"raw_tensor_files":0,"outcomes_opened":False,"decoded_media_files":0,"model_weight_rows_rehashed":weight_rows,"elapsed_gpu_hours":(time.monotonic()-started_clock)/3600,"phase_gpu_hours_ceiling":float(auth["phase_gpu_hours_ceiling"])};protocol.atomic_json(output/"diagnostic_execution_summary_v1.json",summary);return 0
