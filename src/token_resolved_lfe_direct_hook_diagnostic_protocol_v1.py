#!/usr/bin/env python3
"""Pure-stdlib gates and planning for complete-panel direct-hook diagnostic v1."""
from __future__ import annotations
import csv,hashlib,json
from pathlib import Path
from typing import Iterable

REPO=Path(__file__).resolve().parents[1]
DESIGN_FREEZE=REPO/"governance/mechanism_token_direction_direct_hook_diagnostic_v1/complete_panel_direct_hook_diagnostic_design_freeze_v1.json"
FORMAL_MASTER=Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/experiment_freeze_v1/pre_generation_master_freeze_v1.json")
FORMAL_MASTER_BYTES=6294
FORMAL_MASTER_SHA256="149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8"
RUN003=Path("/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003/representation_margins_v1.csv")
RUN003_BYTES=15152
RUN003_SHA256="5e1d14990eba4ad20ae9ec790850bc2ae344177bcadd61aff61c92c372e85506"
CONSISID_COMMIT="60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
ATTRIBUTES=("eyeglasses","facial_hair"); ROLES=("positive","control")
LFE_TOKENS=32; LFE_DIM=2048; TIE_THRESHOLD=1e-8

class DiagnosticProtocolError(RuntimeError): pass
def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def read_json(path:Path)->dict: return json.loads(path.read_text(encoding="utf-8"))
def read_csv(path:Path)->list[dict[str,str]]:
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def resolve(raw:str)->Path:
    p=Path(raw); return p if p.is_absolute() else REPO/p
def verify_file(path:Path,size:int,digest:str)->None:
    if not path.is_file() or path.is_symlink() or path.stat().st_size!=size or sha256(path)!=digest: raise DiagnosticProtocolError(f"binding mismatch: {path}")
def atomic_json(path:Path,payload:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".partial")
    if path.exists() or tmp.exists(): raise DiagnosticProtocolError(f"refusing overwrite: {path}")
    tmp.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8"); tmp.replace(path)
def atomic_csv(path:Path,fields:tuple[str,...],rows:Iterable[dict])->None:
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".partial")
    if path.exists() or tmp.exists(): raise DiagnosticProtocolError(f"refusing overwrite: {path}")
    with tmp.open("x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)
    tmp.replace(path)
def validate_design()->dict:
    freeze=read_json(DESIGN_FREEZE)
    if freeze.get("status")!="FROZEN_APPROVED_COMPLETE_40_UNIT_DIRECT_HOOK_DIAGNOSTIC_PREREGISTRATION_ONLY": raise DiagnosticProtocolError("design freeze status mismatch")
    design=freeze.get("frozen_design",{})
    exact={"formal_units":40,"direct_lfe_calls":40,"one_step_hook_controls":40,"direct_hook_rows":40,"hook_pooled_replication_rows":20,"token_margin_rows":0,"gpu_devices":1,"hard_gpu_hours_ceiling":2}
    if any(design.get(k)!=v for k,v in exact.items()): raise DiagnosticProtocolError("frozen design count drift")
    if design.get("outcome_access") is not False or design.get("raw_tensor_persistence") is not False: raise DiagnosticProtocolError("design boundary drift")
    return freeze
def formal_rows()->tuple[dict,list[dict[str,str]]]:
    verify_file(FORMAL_MASTER,FORMAL_MASTER_BYTES,FORMAL_MASTER_SHA256); master=read_json(FORMAL_MASTER)
    if master.get("consisid",{}).get("commit")!=CONSISID_COMMIT: raise DiagnosticProtocolError("ConsisID commit drift")
    item=master["artifacts"]["generation_manifest"]; manifest=Path(item["path"]); verify_file(manifest,int(item["size_bytes"]),item["sha256"])
    rows=read_csv(manifest)
    if len(rows)!=160 or len({r["task_id"] for r in rows})!=160: raise DiagnosticProtocolError("formal task universe drift")
    return master,rows
def diagnostic_plan(rows:list[dict[str,str]])->list[dict[str,str]]:
    selected=[r for r in rows if r["seed_index"]=="1"]
    if len(selected)!=40 or len({r["formal_unit_id"] for r in selected})!=40: raise DiagnosticProtocolError("seed-index-1 unit universe drift")
    plan=[]
    for r in sorted(selected,key=lambda x:x["formal_unit_id"]):
        plan.append({"diagnostic_task_id":f"DHD__{r['formal_unit_id']}","source_task_id":r["task_id"],"formal_unit_id":r["formal_unit_id"],"formal_pair_id":r["formal_pair_id"],"attribute":r["attribute"],"role":r["role"],"seed_index":r["seed_index"],"seed":r["seed"],"operation":"same_preprocessing_direct_and_one_step_hook"})
    pairs={a:{} for a in ATTRIBUTES}
    for r in plan:pairs[r["attribute"]].setdefault(r["formal_pair_id"],set()).add(r["role"])
    if any(len(pairs[a])!=10 or any(v!=set(ROLES) for v in pairs[a].values()) for a in ATTRIBUTES): raise DiagnosticProtocolError("matched-pair plan drift")
    return plan
