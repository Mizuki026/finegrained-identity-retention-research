#!/usr/bin/env python3
"""Future single-GPU runtime for preprocessing repeatability v1."""
from __future__ import annotations
import sys,time
from datetime import datetime,timezone
from pathlib import Path
import preprocessing_repeatability_protocol_v1 as protocol

STATUS_FIELDS=("acquisition_task_id","formal_unit_id","formal_pair_id","attribute","role","preprocessing_replicate","status","started_at_utc","finished_at_utc")
def now()->str:return datetime.now(timezone.utc).isoformat()
def verify_weights(master:dict)->int:
    item=master["artifacts"]["model_weight_hashes"];inventory=Path(item["path"]);protocol.verify_file(inventory,int(item["size_bytes"]),item["sha256"]);rows=protocol.read_csv(inventory);root=Path(master["generation"]["model_path"])
    for row in rows:protocol.verify_file(root/row["relative_path"],int(row["size_bytes"]),row["sha256"])
    return len(rows)
def execute_repeatability(output:Path,auth_file:Path)->int:
    from run_preprocessing_repeatability_diagnostic_v1 import validate_active
    auth=validate_active(auth_file,output);start=time.monotonic();deadline=start+float(auth["phase_gpu_hours_ceiling"])*3600
    master,formal=protocol.formal_rows();plan=protocol.unit_plan(formal);weight_rows=verify_weights(master);protocol.verify_file(protocol.RUN003,protocol.RUN003_BYTES,protocol.RUN003_SHA256);frozen=protocol.read_csv(protocol.RUN003)
    consisid=Path(master["consisid"]["repository"]);sys.path.insert(0,str(consisid))
    import torch
    from models.consisid_utils import prepare_face_models,process_face_embeddings_infer
    from models.transformer_consisid import ConsisIDTransformer3DModel
    from analyze_preprocessing_repeatability_v1 import analyze_transient,WITHIN_FIELDS,CROSS_FIELDS,MARGIN_FIELDS,CROSS_POOL_FIELDS,RUN003_FIELDS
    from verify_preprocessing_repeatability_v1 import verify_transient
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise protocol.RepeatabilityProtocolError("exactly one visible GPU required")
    device="cuda";dtype=torch.bfloat16;model_path=master["generation"]["model_path"]
    face=prepare_face_models(model_path,device,dtype);face_helper_1,face_helper_2,face_clip_model,face_main_model,eva_mean,eva_std=face
    transformer=ConsisIDTransformer3DModel.from_pretrained(model_path,subfolder="transformer",torch_dtype=dtype);transformer.to(device,dtype=dtype);transformer.local_face_scale=1.0
    sources={r["task_id"]:r for r in formal};tensors={};meta={};statuses=[]
    for task in plan:
        unit=task["formal_unit_id"];source=sources[task["source_task_id"]];reference=Path(source["reference_image_path"])
        if not reference.is_file() or reference.is_symlink() or protocol.sha256(reference)!=source["reference_image_sha256"]:raise protocol.RepeatabilityProtocolError(f"reference drift: {reference}")
        tensors[unit]={};meta[unit]={k:task[k] for k in ("formal_pair_id","attribute","role")}
        for replicate in protocol.REPLICATES:
            if time.monotonic()>=deadline:raise protocol.RepeatabilityProtocolError("GPU-hour ceiling reached before preprocessing call")
            started=now();id_cond,id_vit_hidden,image,face_kps=process_face_embeddings_infer(face_helper_1,face_clip_model,face_helper_2,eva_mean,eva_std,face_main_model,device,dtype,str(reference),is_align_face=True)
            with torch.inference_mode():
                first=transformer.local_facial_extractor(id_cond,id_vit_hidden);second=transformer.local_facial_extractor(id_cond,id_vit_hidden)
            tensors[unit][replicate]={1:first.detach().float().cpu().clone(),2:second.detach().float().cpu().clone()};finished=now();statuses.append({"acquisition_task_id":f"PPR__{unit}__{replicate}","formal_unit_id":unit,"formal_pair_id":task["formal_pair_id"],"attribute":task["attribute"],"role":task["role"],"preprocessing_replicate":replicate,"status":"COMPLETE_TRANSIENT_ONLY","started_at_utc":started,"finished_at_utc":finished})
            del id_cond,id_vit_hidden,image,face_kps,first,second
            if time.monotonic()>=deadline:raise protocol.RepeatabilityProtocolError("GPU-hour ceiling reached after preprocessing call")
    result=analyze_transient(tensors,meta,frozen);verification=verify_transient(tensors,meta,frozen,result)
    staging=output.with_name(output.name+".partial")
    if output.exists() or staging.exists():raise protocol.RepeatabilityProtocolError("runtime output or staging directory already exists")
    staging.mkdir(parents=True,exist_ok=False);protocol.atomic_csv(staging/"within_preprocessing_direct_repeat_v1.csv",WITHIN_FIELDS,result["within"]);protocol.atomic_csv(staging/"cross_preprocessing_lfe_equivalence_v1.csv",CROSS_FIELDS,result["cross"]);protocol.atomic_csv(staging/"preprocessing_replicate_pooled_margins_v1.csv",MARGIN_FIELDS,result["margins"]);protocol.atomic_csv(staging/"cross_replicate_pooled_comparison_v1.csv",CROSS_POOL_FIELDS,result["cross_pooled"]);protocol.atomic_csv(staging/"replicate_run_003_comparison_v1.csv",RUN003_FIELDS,result["run003"]);protocol.atomic_csv(staging/"preprocessing_repeatability_execution_status_v1.csv",STATUS_FIELDS,statuses);protocol.atomic_json(staging/"preprocessing_repeatability_in_memory_verification_v1.json",verification)
    summary={"schema_version":1,"status":"COMPLETE_PANEL_PREPROCESSING_REPEATABILITY_COMPLETE_PENDING_PERSISTED_VERIFICATION","authorization_path":str(auth_file.resolve()),"authorization_sha256":protocol.sha256(auth_file),"formal_units":40,"preprocessing_calls":80,"direct_lfe_calls":160,"within_rows":80,"cross_rows":40,"pooled_margin_rows":40,"cross_pooled_rows":20,"run003_comparison_rows":40,"token_margin_rows":0,"transformer_steps":0,"full_diffusion_trajectories":0,"raw_tensor_files":0,"outcomes_opened":False,"decoded_media_files":0,"model_weight_rows_rehashed":weight_rows,"elapsed_gpu_hours":(time.monotonic()-start)/3600,"phase_gpu_hours_ceiling":float(auth["phase_gpu_hours_ceiling"])};protocol.atomic_json(staging/"preprocessing_repeatability_execution_summary_v1.json",summary);staging.replace(output);return 0
