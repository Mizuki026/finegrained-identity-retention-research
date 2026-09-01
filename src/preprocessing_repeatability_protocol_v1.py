#!/usr/bin/env python3
"""Pure-stdlib bindings and plan for preprocessing repeatability diagnostic v1."""
from __future__ import annotations
import csv,hashlib,json
from pathlib import Path
from typing import Iterable

REPO=Path(__file__).resolve().parents[1]
DESIGN_FREEZE=REPO/"governance/mechanism_token_direction_preprocessing_repeatability_design_v1/complete_panel_fresh_preprocessing_repeatability_design_freeze_v1.json"
FORMAL_MASTER=Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/experiment_freeze_v1/pre_generation_master_freeze_v1.json")
FORMAL_MASTER_BYTES=6294
FORMAL_MASTER_SHA256="149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8"
RUN003=Path("/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003/representation_margins_v1.csv")
RUN003_BYTES=15152
RUN003_SHA256="5e1d14990eba4ad20ae9ec790850bc2ae344177bcadd61aff61c92c372e85506"
CONSISID_COMMIT="60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
ATTRIBUTES=("eyeglasses","facial_hair");ROLES=("positive","control");REPLICATES=("P1","P2");DIRECT_REPEATS=(1,2)
LFE_TOKENS=32;LFE_DIM=2048;TIE_THRESHOLD=1e-8

class RepeatabilityProtocolError(RuntimeError):pass
def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):h.update(block)
    return h.hexdigest()
def read_json(path:Path)->dict:return json.loads(path.read_text(encoding="utf-8"))
def read_csv(path:Path)->list[dict[str,str]]:
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def resolve(raw:str)->Path:
    p=Path(raw);return p if p.is_absolute() else REPO/p
def verify_file(path:Path,size:int,digest:str)->None:
    if not path.is_file() or path.is_symlink() or path.stat().st_size!=size or sha256(path)!=digest:raise RepeatabilityProtocolError(f"binding mismatch: {path}")
def atomic_json(path:Path,payload:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True);partial=path.with_suffix(path.suffix+".partial")
    if path.exists() or partial.exists():raise RepeatabilityProtocolError(f"refusing overwrite: {path}")
    partial.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8");partial.replace(path)
def atomic_csv(path:Path,fields:tuple[str,...],rows:Iterable[dict])->None:
    path.parent.mkdir(parents=True,exist_ok=True);partial=path.with_suffix(path.suffix+".partial")
    if path.exists() or partial.exists():raise RepeatabilityProtocolError(f"refusing overwrite: {path}")
    with partial.open("x",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");writer.writeheader();writer.writerows(rows)
    partial.replace(path)
def validate_design()->dict:
    freeze=read_json(DESIGN_FREEZE)
    if freeze.get("status")!="FROZEN_APPROVED_COMPLETE_PANEL_FRESH_PREPROCESSING_REPEATABILITY_PREREGISTRATION_ONLY":raise RepeatabilityProtocolError("design freeze status mismatch")
    design=freeze.get("frozen_design",{})
    exact={"formal_units":40,"fresh_preprocessing_calls_per_unit":2,"total_preprocessing_calls":80,"direct_lfe_repeats_per_preprocessing_result":2,"total_direct_lfe_calls":160,"hooks":0,"transformer_steps":0,"full_diffusion_trajectories":0,"within_preprocessing_direct_repeat_rows":80,"cross_preprocessing_lfe_equivalence_rows":40,"preprocessing_replicate_pooled_margin_rows":40,"cross_replicate_pooled_comparison_rows":20,"replicate_vs_frozen_run_003_comparison_rows":40,"token_index_margin_rows":0,"gpu_devices":1,"hard_gpu_hours_ceiling":2}
    if any(design.get(k)!=v for k,v in exact.items()):raise RepeatabilityProtocolError("frozen design count drift")
    for key in ("raw_tensor_or_media_persistence","outcome_access","selective_or_automatic_rerun"):
        if design.get(key) is not False:raise RepeatabilityProtocolError(f"frozen boundary drift: {key}")
    return freeze
def formal_rows()->tuple[dict,list[dict[str,str]]]:
    verify_file(FORMAL_MASTER,FORMAL_MASTER_BYTES,FORMAL_MASTER_SHA256);master=read_json(FORMAL_MASTER)
    if master.get("consisid",{}).get("commit")!=CONSISID_COMMIT:raise RepeatabilityProtocolError("ConsisID commit drift")
    item=master["artifacts"]["generation_manifest"];manifest=Path(item["path"]);verify_file(manifest,int(item["size_bytes"]),item["sha256"]);rows=read_csv(manifest)
    if len(rows)!=160 or len({r["task_id"] for r in rows})!=160:raise RepeatabilityProtocolError("formal task universe drift")
    return master,rows
def unit_plan(rows:list[dict[str,str]])->list[dict[str,str]]:
    selected=[r for r in rows if r["seed_index"]=="1"]
    if len(selected)!=40 or len({r["formal_unit_id"] for r in selected})!=40:raise RepeatabilityProtocolError("seed-index-1 unit universe drift")
    plan=[]
    for r in sorted(selected,key=lambda x:x["formal_unit_id"]):
        if r["attribute"] not in ATTRIBUTES or r["role"] not in ROLES:raise RepeatabilityProtocolError("attribute or role drift")
        plan.append({"unit_task_id":f"PPR__{r['formal_unit_id']}","source_task_id":r["task_id"],"formal_unit_id":r["formal_unit_id"],"formal_pair_id":r["formal_pair_id"],"attribute":r["attribute"],"role":r["role"],"seed_index":r["seed_index"],"seed":r["seed"]})
    pairs={a:{} for a in ATTRIBUTES}
    for r in plan:pairs[r["attribute"]].setdefault(r["formal_pair_id"],set()).add(r["role"])
    if any(len(pairs[a])!=10 or any(v!=set(ROLES) for v in pairs[a].values()) for a in ATTRIBUTES):raise RepeatabilityProtocolError("matched-pair plan drift")
    return plan
def acquisition_plan(rows:list[dict[str,str]])->list[dict[str,str]]:
    output=[]
    for unit in unit_plan(rows):
        for replicate in REPLICATES:
            output.append({**unit,"preprocessing_replicate":replicate,"fresh_preprocessing_call":str(len(output)+1),"direct_lfe_repeats":"2","operation":"fresh_preprocessing_then_two_identical_input_direct_lfe_calls"})
    if len(output)!=80:raise RepeatabilityProtocolError("acquisition plan count drift")
    return output
