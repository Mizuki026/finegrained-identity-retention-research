#!/usr/bin/env python3
"""Transient complete-family analyzer for preprocessing repeatability v1."""
from __future__ import annotations
import math
from collections import defaultdict
from typing import Any
import preprocessing_repeatability_protocol_v1 as protocol

WITHIN_FIELDS=("formal_unit_id","formal_pair_id","attribute","role","preprocessing_replicate","bit_exact","within_frozen_tolerance","max_absolute_difference","rms_difference")
CROSS_FIELDS=("formal_unit_id","formal_pair_id","attribute","role","within_input_controls_pass","bit_exact","within_frozen_tolerance","max_absolute_difference","rms_difference")
MARGIN_FIELDS=("preprocessing_replicate","attribute","formal_pair_id","margin","direction")
CROSS_POOL_FIELDS=("attribute","formal_pair_id","p1_margin","p2_margin","absolute_difference","tolerance","within_tolerance","p1_direction","p2_direction","sign_match")
RUN003_FIELDS=("preprocessing_replicate","attribute","formal_pair_id","reconstructed_margin","frozen_run_003_margin","absolute_difference","tolerance","within_tolerance","direction","frozen_direction","sign_match")
class RepeatabilityAnalysisError(RuntimeError):pass
def _torch():import torch;return torch
def _clean(value:Any,dim:int):
    torch=_torch();x=value.detach().to(device="cpu",dtype=torch.float32)
    if tuple(x.shape)!=(1,protocol.LFE_TOKENS,dim) or not bool(torch.isfinite(x).all()):raise RepeatabilityAnalysisError("tensor shape/finiteness drift")
    return x[0].clone()
def _label(value:float)->str:return "tie" if abs(value)<=protocol.TIE_THRESHOLD else ("correct" if value>0 else "wrong")
def _comparison(left:Any,right:Any)->dict:
    torch=_torch();difference=torch.abs(left-right);tolerance=1e-6+1e-5*torch.maximum(torch.abs(left),torch.abs(right))
    return {"bit_exact":bool(torch.equal(left,right)),"within_frozen_tolerance":bool(torch.all(difference<=tolerance)),"max_absolute_difference":float(torch.max(difference).item()),"rms_difference":float(torch.sqrt(torch.mean((left-right)**2)).item())}
def analyze_transient(tensors:dict[str,dict[str,dict[int,Any]]],meta:dict[str,dict[str,str]],frozen:list[dict[str,str]],*,dim:int=protocol.LFE_DIM)->dict:
    torch=_torch()
    if set(tensors)!=set(meta) or len(tensors)!=40:raise RepeatabilityAnalysisError("complete 40-unit tensor universe required")
    clean={};within=[];controls={}
    for unit in sorted(tensors):
        m=meta[unit]
        if set(m)!={"formal_pair_id","attribute","role"} or m.get("attribute") not in protocol.ATTRIBUTES or m.get("role") not in protocol.ROLES:raise RepeatabilityAnalysisError("metadata drift")
        if set(tensors[unit])!=set(protocol.REPLICATES):raise RepeatabilityAnalysisError("preprocessing replicate universe drift")
        clean[unit]={};controls[unit]={}
        for replicate in protocol.REPLICATES:
            values=tensors[unit][replicate]
            if set(values)!=set(protocol.DIRECT_REPEATS):raise RepeatabilityAnalysisError("direct repeat universe drift")
            clean[unit][replicate]={repeat:_clean(values[repeat],dim) for repeat in protocol.DIRECT_REPEATS}
            comparison=_comparison(clean[unit][replicate][1],clean[unit][replicate][2]);controls[unit][replicate]=comparison["within_frozen_tolerance"]
            within.append({"formal_unit_id":unit,**m,"preprocessing_replicate":replicate,**comparison})
    cross=[]
    for unit in sorted(clean):
        cross.append({"formal_unit_id":unit,**meta[unit],"within_input_controls_pass":controls[unit]["P1"] and controls[unit]["P2"],**_comparison(clean[unit]["P1"][1],clean[unit]["P2"][1])})
    pairs={a:defaultdict(dict) for a in protocol.ATTRIBUTES};vectors={r:{} for r in protocol.REPLICATES}
    for unit in clean:
        m=meta[unit];pairs[m["attribute"]][m["formal_pair_id"]][m["role"]]=unit
        for replicate in protocol.REPLICATES:
            vector=clean[unit][replicate][1].mean(dim=0);vectors[replicate][unit]=vector/torch.linalg.vector_norm(vector).clamp_min(1e-12)
    if any(len(pairs[a])!=10 or any(set(v)!=set(protocol.ROLES) for v in pairs[a].values()) for a in protocol.ATTRIBUTES):raise RepeatabilityAnalysisError("pair universe drift")
    margins=[];margin_map={r:{} for r in protocol.REPLICATES}
    for replicate in protocol.REPLICATES:
        for attribute in protocol.ATTRIBUTES:
            for held in sorted(pairs[attribute]):
                train=[p for p in sorted(pairs[attribute]) if p!=held];direction=torch.stack([vectors[replicate][pairs[attribute][p]["positive"]]-vectors[replicate][pairs[attribute][p]["control"]] for p in train]).mean(dim=0)
                margin=float(torch.dot(vectors[replicate][pairs[attribute][held]["positive"]],direction)-torch.dot(vectors[replicate][pairs[attribute][held]["control"]],direction))
                if not math.isfinite(margin):raise RepeatabilityAnalysisError("nonfinite pooled margin")
                key=(attribute,held);margin_map[replicate][key]=margin;margins.append({"preprocessing_replicate":replicate,"attribute":attribute,"formal_pair_id":held,"margin":margin,"direction":_label(margin)})
    cross_pooled=[]
    for key in sorted(margin_map["P1"]):
        p1=margin_map["P1"][key];p2=margin_map["P2"][key];difference=abs(p1-p2);tolerance=1e-6+1e-5*max(abs(p1),abs(p2));l1=_label(p1);l2=_label(p2)
        cross_pooled.append({"attribute":key[0],"formal_pair_id":key[1],"p1_margin":p1,"p2_margin":p2,"absolute_difference":difference,"tolerance":tolerance,"within_tolerance":difference<=tolerance,"p1_direction":l1,"p2_direction":l2,"sign_match":l1==l2})
    selected=[r for r in frozen if r.get("stage")=="valid_face_emb_mean_token_l2_normalized"];expected={(r["attribute"],r["formal_pair_id"]):float(r["margin"]) for r in selected}
    if len(selected)!=20 or len(expected)!=20 or any(not math.isfinite(v) for v in expected.values()):raise RepeatabilityAnalysisError("frozen pooled universe drift")
    historical=[]
    for replicate in protocol.REPLICATES:
        for key in sorted(margin_map[replicate]):
            observed=margin_map[replicate][key];target=expected[key];difference=abs(observed-target);tolerance=1e-6+1e-5*max(abs(observed),abs(target));label=_label(observed);frozen_label=_label(target)
            historical.append({"preprocessing_replicate":replicate,"attribute":key[0],"formal_pair_id":key[1],"reconstructed_margin":observed,"frozen_run_003_margin":target,"absolute_difference":difference,"tolerance":tolerance,"within_tolerance":difference<=tolerance,"direction":label,"frozen_direction":frozen_label,"sign_match":label==frozen_label})
    return {"within":within,"cross":cross,"margins":margins,"cross_pooled":cross_pooled,"run003":historical}
