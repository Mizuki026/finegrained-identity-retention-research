#!/usr/bin/env python3
"""Transient analyzer for complete-panel direct-hook diagnostic v1."""
from __future__ import annotations
import math
from collections import defaultdict
from typing import Any
import token_resolved_lfe_direct_hook_diagnostic_protocol_v1 as protocol

EQUIV_FIELDS=("formal_unit_id","formal_pair_id","attribute","role","bit_exact","within_frozen_tolerance","max_absolute_difference","rms_difference")
POOLED_FIELDS=("attribute","formal_pair_id","reconstructed_margin","frozen_run_003_margin","absolute_difference","tolerance","within_tolerance","direction")
class DiagnosticAnalysisError(RuntimeError):pass
def _torch(): import torch; return torch
def _tensor(value:Any,dim:int):
    torch=_torch(); x=value.detach().float().cpu()
    if tuple(x.shape)!=(1,protocol.LFE_TOKENS,dim) or not bool(torch.isfinite(x).all()): raise DiagnosticAnalysisError("tensor shape/finiteness drift")
    return x[0].clone()
def _label(value:float)->str:return "tie" if abs(value)<=protocol.TIE_THRESHOLD else ("correct" if value>0 else "wrong")
def analyze_transient(direct:dict[str,Any],hook:dict[str,Any],meta:dict[str,dict[str,str]],frozen:list[dict[str,str]],*,dim:int=protocol.LFE_DIM)->dict:
    torch=_torch()
    if set(direct)!=set(hook) or set(direct)!=set(meta) or len(direct)!=40: raise DiagnosticAnalysisError("complete 40-unit tensor universe required")
    clean_d={};clean_h={};equiv=[]
    for unit in sorted(direct):
        d=_tensor(direct[unit],dim); h=_tensor(hook[unit],dim); difference=torch.abs(d-h); tolerance=1e-6+1e-5*torch.maximum(torch.abs(d),torch.abs(h))
        m=meta[unit]
        if m["attribute"] not in protocol.ATTRIBUTES or m["role"] not in protocol.ROLES: raise DiagnosticAnalysisError("metadata drift")
        equiv.append({"formal_unit_id":unit,"formal_pair_id":m["formal_pair_id"],"attribute":m["attribute"],"role":m["role"],"bit_exact":bool(torch.equal(d,h)),"within_frozen_tolerance":bool(torch.all(difference<=tolerance)),"max_absolute_difference":float(torch.max(difference).item()),"rms_difference":float(torch.sqrt(torch.mean((d-h)**2)).item())})
        clean_d[unit]=d;clean_h[unit]=h
    pairs={a:defaultdict(dict) for a in protocol.ATTRIBUTES}
    pooled={}
    for unit,h in clean_h.items():
        m=meta[unit]; pairs[m["attribute"]][m["formal_pair_id"]][m["role"]]=unit
        vector=h.mean(dim=0); pooled[unit]=vector/torch.linalg.vector_norm(vector).clamp_min(1e-12)
    if any(len(pairs[a])!=10 or any(set(v)!=set(protocol.ROLES) for v in pairs[a].values()) for a in protocol.ATTRIBUTES): raise DiagnosticAnalysisError("pair universe drift")
    selected=[r for r in frozen if r.get("stage")=="valid_face_emb_mean_token_l2_normalized"]
    expected={(r["attribute"],r["formal_pair_id"]):float(r["margin"]) for r in selected}
    if len(selected)!=20 or len(expected)!=20: raise DiagnosticAnalysisError("frozen pooled universe drift")
    pooled_rows=[]
    for attribute in protocol.ATTRIBUTES:
        for held in sorted(pairs[attribute]):
            train=[p for p in sorted(pairs[attribute]) if p!=held]
            direction=torch.stack([pooled[pairs[attribute][p]["positive"]]-pooled[pairs[attribute][p]["control"]] for p in train]).mean(dim=0)
            margin=float(torch.dot(pooled[pairs[attribute][held]["positive"]],direction)-torch.dot(pooled[pairs[attribute][held]["control"]],direction))
            if not math.isfinite(margin): raise DiagnosticAnalysisError("nonfinite pooled margin")
            frozen_value=expected[(attribute,held)]; difference=abs(margin-frozen_value); tolerance=1e-6+1e-5*max(abs(margin),abs(frozen_value))
            pooled_rows.append({"attribute":attribute,"formal_pair_id":held,"reconstructed_margin":margin,"frozen_run_003_margin":frozen_value,"absolute_difference":difference,"tolerance":tolerance,"within_tolerance":difference<=tolerance,"direction":_label(margin)})
    return {"equivalence":equiv,"hook_pooled":pooled_rows}
