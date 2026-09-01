#!/usr/bin/env python3
"""Independent transient, dry-run, and persisted verifier for diagnostic v1."""
from __future__ import annotations
import argparse,json,math,sys
from collections import defaultdict
from pathlib import Path
from typing import Any
import token_resolved_lfe_direct_hook_diagnostic_protocol_v1 as protocol

class DiagnosticVerificationError(RuntimeError):pass
def _torch(): import torch; return torch
def _independent_recompute(direct,hook,meta,frozen,dim):
    torch=_torch()
    if set(direct)!=set(hook) or set(direct)!=set(meta) or len(direct)!=40:raise DiagnosticVerificationError("transient unit universe drift")
    result={"equivalence":[],"hook_pooled":[]};pooled={};pairs={a:defaultdict(dict) for a in protocol.ATTRIBUTES}
    for unit in sorted(direct):
        d=direct[unit].detach().to(device="cpu",dtype=torch.float32);h=hook[unit].detach().to(device="cpu",dtype=torch.float32)
        if tuple(d.shape)!=(1,protocol.LFE_TOKENS,dim) or tuple(h.shape)!=tuple(d.shape) or not bool(torch.isfinite(d).all() and torch.isfinite(h).all()):raise DiagnosticVerificationError("transient tensor drift")
        d=d[0];h=h[0];difference=torch.abs(d-h);tolerance=1e-6+1e-5*torch.maximum(torch.abs(d),torch.abs(h));m=meta[unit]
        result["equivalence"].append({"formal_unit_id":unit,"formal_pair_id":m["formal_pair_id"],"attribute":m["attribute"],"role":m["role"],"bit_exact":bool(torch.equal(d,h)),"within_frozen_tolerance":bool(torch.all(difference<=tolerance)),"max_absolute_difference":float(torch.max(difference).item()),"rms_difference":float(torch.sqrt(torch.mean((d-h)**2)).item())})
        vector=h.mean(dim=0);pooled[unit]=vector/torch.linalg.vector_norm(vector).clamp_min(1e-12);pairs[m["attribute"]][m["formal_pair_id"]][m["role"]]=unit
    selected=[r for r in frozen if r.get("stage")=="valid_face_emb_mean_token_l2_normalized"];expected={(r["attribute"],r["formal_pair_id"]):float(r["margin"]) for r in selected}
    if len(selected)!=20 or len(expected)!=20:raise DiagnosticVerificationError("frozen pooled universe drift")
    for attribute in protocol.ATTRIBUTES:
        if len(pairs[attribute])!=10 or any(set(v)!=set(protocol.ROLES) for v in pairs[attribute].values()):raise DiagnosticVerificationError("pair universe drift")
        for held in sorted(pairs[attribute]):
            train=[p for p in sorted(pairs[attribute]) if p!=held];direction=torch.stack([pooled[pairs[attribute][p]["positive"]]-pooled[pairs[attribute][p]["control"]] for p in train]).mean(dim=0)
            margin=float(torch.dot(pooled[pairs[attribute][held]["positive"]],direction)-torch.dot(pooled[pairs[attribute][held]["control"]],direction));frozen_value=expected[(attribute,held)];difference=abs(margin-frozen_value);tolerance=1e-6+1e-5*max(abs(margin),abs(frozen_value));label="tie" if abs(margin)<=protocol.TIE_THRESHOLD else ("correct" if margin>0 else "wrong")
            result["hook_pooled"].append({"attribute":attribute,"formal_pair_id":held,"reconstructed_margin":margin,"frozen_run_003_margin":frozen_value,"absolute_difference":difference,"tolerance":tolerance,"within_tolerance":difference<=tolerance,"direction":label})
    return result
def verify_transient(direct:dict[str,Any],hook:dict[str,Any],meta:dict[str,dict[str,str]],frozen:list[dict[str,str]],observed:dict,*,dim:int=protocol.LFE_DIM)->dict:
    recomputed=_independent_recompute(direct,hook,meta,frozen,dim)
    if len(observed.get("equivalence",[]))!=40 or len(observed.get("hook_pooled",[]))!=20: raise DiagnosticVerificationError("observed family count drift")
    for left,right in zip(observed["equivalence"],recomputed["equivalence"]):
        if {k:left[k] for k in ("formal_unit_id","formal_pair_id","attribute","role","bit_exact","within_frozen_tolerance")}!={k:right[k] for k in ("formal_unit_id","formal_pair_id","attribute","role","bit_exact","within_frozen_tolerance")}: raise DiagnosticVerificationError("equivalence recomputation mismatch")
        for key in ("max_absolute_difference","rms_difference"):
            if not math.isclose(float(left[key]),float(right[key]),rel_tol=1e-7,abs_tol=1e-12): raise DiagnosticVerificationError("equivalence scalar mismatch")
    for left,right in zip(observed["hook_pooled"],recomputed["hook_pooled"]):
        if (left["attribute"],left["formal_pair_id"],left["within_tolerance"],left["direction"])!=(right["attribute"],right["formal_pair_id"],right["within_tolerance"],right["direction"]): raise DiagnosticVerificationError("pooled recomputation mismatch")
        for key in ("reconstructed_margin","frozen_run_003_margin","absolute_difference","tolerance"):
            if not math.isclose(float(left[key]),float(right[key]),rel_tol=1e-7,abs_tol=1e-12): raise DiagnosticVerificationError("pooled scalar mismatch")
    return {"schema_version":1,"status":"PASS_INDEPENDENT_IN_MEMORY_COMPLETE_PANEL_DIRECT_HOOK_DIAGNOSTIC_RECOMPUTATION","direct_hook_rows":40,"hook_pooled_rows":20,"raw_tensors_persisted":False,"outcomes_opened":False,"gpu_used_by_verifier":False}
def verify_dry_run(run_dir:Path)->dict:
    plan=protocol.read_csv(run_dir/"diagnostic_plan_v1.csv"); summary=protocol.read_json(run_dir/"diagnostic_runner_no_weight_dry_run_v1.json")
    _,formal=protocol.formal_rows(); expected=protocol.diagnostic_plan(formal)
    if plan!=expected or len(plan)!=40: raise DiagnosticVerificationError("dry-run plan differs from independent reconstruction")
    if summary.get("status")!="PASS_COMPLETE_PANEL_DIAGNOSTIC_CPU_ONLY_NO_WEIGHT_DRY_RUN": raise DiagnosticVerificationError("dry-run status mismatch")
    for key in ("gpu_used","model_or_weight_loading","reference_images_opened","raw_tensors_captured","outcomes_opened","token_margins_640_computed"):
        if summary.get(key) is not False: raise DiagnosticVerificationError("dry-run forbidden action")
    return {"schema_version":1,"status":"PASS_INDEPENDENT_COMPLETE_PANEL_DIAGNOSTIC_NO_WEIGHT_DRY_RUN_VERIFICATION","plan_rows":40,"formal_units":40,"direct_calls":40,"one_step_hooks":40,"pooled_rows":20,"gpu_used":False}
def _bool(raw:str)->bool:
    if raw not in ("True","False"): raise DiagnosticVerificationError("invalid Boolean")
    return raw=="True"
def verify_persisted(run_dir:Path)->dict:
    eq=protocol.read_csv(run_dir/"direct_hook_equivalence_v1.csv"); pooled=protocol.read_csv(run_dir/"hook_pooled_replication_v1.csv"); status=protocol.read_csv(run_dir/"diagnostic_execution_status_v1.csv")
    if len(eq)!=40 or len({r["formal_unit_id"] for r in eq})!=40 or len(pooled)!=20 or len(status)!=40: raise DiagnosticVerificationError("persisted family count drift")
    for r in eq:
        _bool(r["bit_exact"]); _bool(r["within_frozen_tolerance"])
        if any(not math.isfinite(float(r[k])) or float(r[k])<0 for k in ("max_absolute_difference","rms_difference")): raise DiagnosticVerificationError("invalid equivalence scalar")
    for r in pooled:
        observed=float(r["reconstructed_margin"]); frozen=float(r["frozen_run_003_margin"]); difference=float(r["absolute_difference"]); tolerance=float(r["tolerance"])
        if not math.isclose(difference,abs(observed-frozen),rel_tol=0,abs_tol=1e-15) or _bool(r["within_tolerance"])!=(difference<=tolerance): raise DiagnosticVerificationError("pooled arithmetic mismatch")
    memory=protocol.read_json(run_dir/"diagnostic_in_memory_verification_v1.json")
    if memory.get("status")!="PASS_INDEPENDENT_IN_MEMORY_COMPLETE_PANEL_DIRECT_HOOK_DIAGNOSTIC_RECOMPUTATION": raise DiagnosticVerificationError("in-memory verification missing")
    return {"schema_version":1,"status":"PASS_INDEPENDENT_PERSISTED_COMPLETE_PANEL_DIRECT_HOOK_DIAGNOSTIC_VERIFICATION","direct_hook_rows":40,"hook_pooled_rows":20,"status_rows":40,"raw_tensor_files":0,"outcome_access":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("--mode",required=True,choices=("dry-run","persisted"));p.add_argument("--run-dir",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args(); result=verify_dry_run(a.run_dir) if a.mode=="dry-run" else verify_persisted(a.run_dir);protocol.atomic_json(a.output,result);print(json.dumps(result,indent=2,sort_keys=True));return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except (DiagnosticVerificationError,protocol.DiagnosticProtocolError,ValueError) as error:print(f"FAIL: {error}",file=sys.stderr);raise SystemExit(2)
