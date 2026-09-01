#!/usr/bin/env python3
"""Independent transient, dry-run, and persisted verifier for repeatability v1."""
from __future__ import annotations
import argparse,json,math,sys
from collections import defaultdict
from pathlib import Path
from typing import Any
import preprocessing_repeatability_protocol_v1 as protocol

class RepeatabilityVerificationError(RuntimeError):pass
def _torch():import torch;return torch
def _label(v:float)->str:return "tie" if abs(v)<=protocol.TIE_THRESHOLD else ("correct" if v>0 else "wrong")
def _cmp(left,right):
    torch=_torch();delta=torch.abs(left-right);limit=1e-6+1e-5*torch.maximum(torch.abs(left),torch.abs(right));return bool(torch.equal(left,right)),bool(torch.all(delta<=limit)),float(torch.max(delta).item()),float(torch.sqrt(torch.mean((left-right)**2)).item())
def _independent(tensors,meta,frozen,dim):
    torch=_torch()
    if set(tensors)!=set(meta) or len(tensors)!=40:raise RepeatabilityVerificationError("unit universe drift")
    clean={};result={"within":[],"cross":[],"margins":[],"cross_pooled":[],"run003":[]};control={};pairs={a:defaultdict(dict) for a in protocol.ATTRIBUTES}
    for unit in sorted(tensors):
        m=meta[unit]
        if set(m)!={"formal_pair_id","attribute","role"} or m.get("attribute") not in protocol.ATTRIBUTES or m.get("role") not in protocol.ROLES:raise RepeatabilityVerificationError("metadata drift")
        if set(tensors[unit])!=set(protocol.REPLICATES):raise RepeatabilityVerificationError("replicate universe drift")
        clean[unit]={};control[unit]={};pairs[m["attribute"]][m["formal_pair_id"]][m["role"]]=unit
        for replicate in protocol.REPLICATES:
            if set(tensors[unit][replicate])!=set(protocol.DIRECT_REPEATS):raise RepeatabilityVerificationError("direct universe drift")
            clean[unit][replicate]={}
            for repeat in protocol.DIRECT_REPEATS:
                value=tensors[unit][replicate][repeat].detach().to(device="cpu",dtype=torch.float32)
                if tuple(value.shape)!=(1,protocol.LFE_TOKENS,dim) or not bool(torch.isfinite(value).all()):raise RepeatabilityVerificationError("tensor drift")
                clean[unit][replicate][repeat]=value[0].clone()
            bit,tol,mx,rms=_cmp(clean[unit][replicate][1],clean[unit][replicate][2]);control[unit][replicate]=tol;result["within"].append({"formal_unit_id":unit,**m,"preprocessing_replicate":replicate,"bit_exact":bit,"within_frozen_tolerance":tol,"max_absolute_difference":mx,"rms_difference":rms})
    if any(len(pairs[a])!=10 or any(set(v)!=set(protocol.ROLES) for v in pairs[a].values()) for a in protocol.ATTRIBUTES):raise RepeatabilityVerificationError("pair universe drift")
    for unit in sorted(clean):
        bit,tol,mx,rms=_cmp(clean[unit]["P1"][1],clean[unit]["P2"][1]);result["cross"].append({"formal_unit_id":unit,**meta[unit],"within_input_controls_pass":control[unit]["P1"] and control[unit]["P2"],"bit_exact":bit,"within_frozen_tolerance":tol,"max_absolute_difference":mx,"rms_difference":rms})
    margin_map={r:{} for r in protocol.REPLICATES}
    for replicate in protocol.REPLICATES:
        vectors={}
        for unit in clean:
            vector=clean[unit][replicate][1].mean(0);vectors[unit]=vector/torch.linalg.vector_norm(vector).clamp_min(1e-12)
        for attribute in protocol.ATTRIBUTES:
            for held in sorted(pairs[attribute]):
                others=[p for p in sorted(pairs[attribute]) if p!=held];direction=torch.stack([vectors[pairs[attribute][p]["positive"]]-vectors[pairs[attribute][p]["control"]] for p in others]).mean(0);margin=float(torch.dot(vectors[pairs[attribute][held]["positive"]],direction)-torch.dot(vectors[pairs[attribute][held]["control"]],direction));key=(attribute,held);margin_map[replicate][key]=margin;result["margins"].append({"preprocessing_replicate":replicate,"attribute":attribute,"formal_pair_id":held,"margin":margin,"direction":_label(margin)})
                if not math.isfinite(margin):raise RepeatabilityVerificationError("nonfinite pooled margin")
    for key in sorted(margin_map["P1"]):
        a=margin_map["P1"][key];b=margin_map["P2"][key];difference=abs(a-b);tolerance=1e-6+1e-5*max(abs(a),abs(b));la=_label(a);lb=_label(b);result["cross_pooled"].append({"attribute":key[0],"formal_pair_id":key[1],"p1_margin":a,"p2_margin":b,"absolute_difference":difference,"tolerance":tolerance,"within_tolerance":difference<=tolerance,"p1_direction":la,"p2_direction":lb,"sign_match":la==lb})
    selected=[r for r in frozen if r.get("stage")=="valid_face_emb_mean_token_l2_normalized"];targets={(r["attribute"],r["formal_pair_id"]):float(r["margin"]) for r in selected}
    if len(selected)!=20 or len(targets)!=20 or any(not math.isfinite(v) for v in targets.values()):raise RepeatabilityVerificationError("historical universe drift")
    for replicate in protocol.REPLICATES:
        for key in sorted(margin_map[replicate]):
            value=margin_map[replicate][key];target=targets[key];difference=abs(value-target);tolerance=1e-6+1e-5*max(abs(value),abs(target));label=_label(value);target_label=_label(target);result["run003"].append({"preprocessing_replicate":replicate,"attribute":key[0],"formal_pair_id":key[1],"reconstructed_margin":value,"frozen_run_003_margin":target,"absolute_difference":difference,"tolerance":tolerance,"within_tolerance":difference<=tolerance,"direction":label,"frozen_direction":target_label,"sign_match":label==target_label})
    return result
def _same(observed,recomputed)->None:
    if set(observed)!=set(recomputed):raise RepeatabilityVerificationError("family universe drift")
    numeric={"max_absolute_difference","rms_difference","margin","p1_margin","p2_margin","reconstructed_margin","frozen_run_003_margin","absolute_difference","tolerance"}
    for family in recomputed:
        if len(observed[family])!=len(recomputed[family]):raise RepeatabilityVerificationError("family count drift")
        for left,right in zip(observed[family],recomputed[family]):
            if set(left)!=set(right):raise RepeatabilityVerificationError("field drift")
            for key in right:
                if key in numeric:
                    if not math.isclose(float(left[key]),float(right[key]),rel_tol=1e-7,abs_tol=1e-12):raise RepeatabilityVerificationError("numeric recomputation mismatch")
                elif left[key]!=right[key]:raise RepeatabilityVerificationError("categorical recomputation mismatch")
def verify_transient(tensors:dict[str,dict[str,dict[int,Any]]],meta:dict[str,dict[str,str]],frozen:list[dict[str,str]],observed:dict,*,dim:int=protocol.LFE_DIM)->dict:
    recomputed=_independent(tensors,meta,frozen,dim);_same(observed,recomputed)
    return {"schema_version":1,"status":"PASS_INDEPENDENT_IN_MEMORY_PREPROCESSING_REPEATABILITY_RECOMPUTATION","within_rows":80,"cross_rows":40,"pooled_margin_rows":40,"cross_pooled_rows":20,"run003_rows":40,"raw_tensors_persisted":False,"outcomes_opened":False}
def verify_dry_run(run_dir:Path)->dict:
    plan=protocol.read_csv(run_dir/"preprocessing_repeatability_plan_v1.csv");summary=protocol.read_json(run_dir/"preprocessing_repeatability_no_weight_dry_run_v1.json");_,formal=protocol.formal_rows();expected=protocol.acquisition_plan(formal)
    if plan!=expected or len(plan)!=80:raise RepeatabilityVerificationError("dry-run plan drift")
    if summary.get("status")!="PASS_PREPROCESSING_REPEATABILITY_CPU_ONLY_NO_WEIGHT_DRY_RUN":raise RepeatabilityVerificationError("dry-run status mismatch")
    for key in ("reference_images_opened","preprocessing_run","model_or_weight_loading","gpu_used","raw_tensors_captured","outcomes_opened","token_margins_640_computed","network_used","torch_imported"):
        if summary.get(key) is not False:raise RepeatabilityVerificationError(f"dry-run forbidden action: {key}")
    return {"schema_version":1,"status":"PASS_INDEPENDENT_PREPROCESSING_REPEATABILITY_NO_WEIGHT_DRY_RUN_VERIFICATION","plan_rows":80,"formal_units":40,"preprocessing_calls_planned":80,"direct_lfe_calls_planned":160,"gpu_used":False}
def _bool(raw:str)->bool:
    if raw not in ("True","False"):raise RepeatabilityVerificationError("invalid Boolean")
    return raw=="True"
def verify_persisted(run_dir:Path)->dict:
    names={"within_preprocessing_direct_repeat_v1.csv":80,"cross_preprocessing_lfe_equivalence_v1.csv":40,"preprocessing_replicate_pooled_margins_v1.csv":40,"cross_replicate_pooled_comparison_v1.csv":20,"replicate_run_003_comparison_v1.csv":40,"preprocessing_repeatability_execution_status_v1.csv":80}
    outputs={name:protocol.read_csv(run_dir/name) for name in names}
    if any(len(outputs[name])!=count for name,count in names.items()):raise RepeatabilityVerificationError("persisted family count drift")
    within=outputs["within_preprocessing_direct_repeat_v1.csv"];cross=outputs["cross_preprocessing_lfe_equivalence_v1.csv"];margins=outputs["preprocessing_replicate_pooled_margins_v1.csv"];cross_pooled=outputs["cross_replicate_pooled_comparison_v1.csv"];historical=outputs["replicate_run_003_comparison_v1.csv"];statuses=outputs["preprocessing_repeatability_execution_status_v1.csv"]
    units={r["formal_unit_id"] for r in cross}
    if len(units)!=40 or {(r["formal_unit_id"],r["preprocessing_replicate"]) for r in within}!={(u,p) for u in units for p in protocol.REPLICATES}:raise RepeatabilityVerificationError("within/cross key universe drift")
    panel={(r["attribute"],r["formal_pair_id"]) for r in cross_pooled}
    if len(panel)!=20 or {(r["preprocessing_replicate"],r["attribute"],r["formal_pair_id"]) for r in margins}!={(p,*key) for p in protocol.REPLICATES for key in panel} or {(r["preprocessing_replicate"],r["attribute"],r["formal_pair_id"]) for r in historical}!={(p,*key) for p in protocol.REPLICATES for key in panel}:raise RepeatabilityVerificationError("pooled key universe drift")
    if {(r["formal_unit_id"],r["preprocessing_replicate"]) for r in statuses}!={(u,p) for u in units for p in protocol.REPLICATES} or any(r["status"]!="COMPLETE_TRANSIENT_ONLY" for r in statuses):raise RepeatabilityVerificationError("status universe drift")
    within_pass={}
    for row in within:
        _bool(row["bit_exact"]);within_pass[(row["formal_unit_id"],row["preprocessing_replicate"])]=_bool(row["within_frozen_tolerance"])
        if any(not math.isfinite(float(row[k])) or float(row[k])<0 for k in ("max_absolute_difference","rms_difference")):raise RepeatabilityVerificationError("invalid tensor scalar")
    for row in cross:
        _bool(row["bit_exact"]);_bool(row["within_frozen_tolerance"]);expected_gate=within_pass[(row["formal_unit_id"],"P1")] and within_pass[(row["formal_unit_id"],"P2")]
        if _bool(row["within_input_controls_pass"])!=expected_gate:raise RepeatabilityVerificationError("cross interpretation gate drift")
        if any(not math.isfinite(float(row[k])) or float(row[k])<0 for k in ("max_absolute_difference","rms_difference")):raise RepeatabilityVerificationError("invalid tensor scalar")
    for row in margins:
        value=float(row["margin"])
        if not math.isfinite(value) or row["direction"]!=_label(value):raise RepeatabilityVerificationError("margin direction drift")
    for name,left,right in (("cross_replicate_pooled_comparison_v1.csv","p1_margin","p2_margin"),("replicate_run_003_comparison_v1.csv","reconstructed_margin","frozen_run_003_margin")):
        for row in outputs[name]:
            left_value=float(row[left]);right_value=float(row[right]);difference=abs(left_value-right_value);tolerance=float(row["tolerance"])
            if any(not math.isfinite(v) for v in (left_value,right_value,difference,tolerance)) or tolerance<0:raise RepeatabilityVerificationError("nonfinite pooled scalar")
            if not math.isclose(float(row["absolute_difference"]),difference,rel_tol=0,abs_tol=1e-15) or _bool(row["within_tolerance"])!=(difference<=tolerance):raise RepeatabilityVerificationError("persisted pooled arithmetic drift")
            left_label=_label(left_value);right_label=_label(right_value)
            if name.startswith("cross_"):
                if row["p1_direction"]!=left_label or row["p2_direction"]!=right_label or _bool(row["sign_match"])!=(left_label==right_label):raise RepeatabilityVerificationError("cross pooled label drift")
            elif row["direction"]!=left_label or row["frozen_direction"]!=right_label or _bool(row["sign_match"])!=(left_label==right_label):raise RepeatabilityVerificationError("historical label drift")
    memory=protocol.read_json(run_dir/"preprocessing_repeatability_in_memory_verification_v1.json")
    if memory.get("status")!="PASS_INDEPENDENT_IN_MEMORY_PREPROCESSING_REPEATABILITY_RECOMPUTATION":raise RepeatabilityVerificationError("in-memory verification missing")
    forbidden={".pt",".pth",".npy",".npz",".safetensors",".png",".jpg",".jpeg",".mp4"}
    if any(p.is_file() and p.suffix.lower() in forbidden for p in run_dir.iterdir()):raise RepeatabilityVerificationError("raw tensor or media file found")
    return {"schema_version":1,"status":"PASS_INDEPENDENT_PERSISTED_PREPROCESSING_REPEATABILITY_VERIFICATION","within_rows":80,"cross_rows":40,"pooled_margin_rows":40,"cross_pooled_rows":20,"run003_rows":40,"status_rows":80,"raw_tensor_files":0,"outcome_access":False}
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--mode",required=True,choices=("dry-run","persisted"));p.add_argument("--run-dir",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();result=verify_dry_run(a.run_dir) if a.mode=="dry-run" else verify_persisted(a.run_dir);protocol.atomic_json(a.output,result);print(json.dumps(result,indent=2,sort_keys=True));return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except (RepeatabilityVerificationError,protocol.RepeatabilityProtocolError,ValueError) as error:print(f"FAIL: {error}",file=sys.stderr);raise SystemExit(2)
