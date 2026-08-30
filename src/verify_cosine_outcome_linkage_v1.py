#!/usr/bin/env python3
"""Independent verifier for cosine/outcome linkage v1 dry-run and formal results."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path


REPO=Path(__file__).resolve().parents[1]
DRY_STATUS="PASS_NO_WEIGHT_COSINE_LINKAGE_DRY_RUN_NO_REAL_INPUT"
EXECUTION_STATUS="CPU_COSINE_LINKAGE_EXECUTION_APPROVED"
ATTRIBUTES=("eyeglasses","facial_hair")
BRANCHES=("unconditional","text")
GROUPS=("early","middle","late")


class VerificationError(RuntimeError): pass


def sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle: value=json.load(handle)
    if not isinstance(value,dict): raise VerificationError(f"expected JSON object: {path}")
    return value


def atomic_json(path: Path,value: dict) -> None:
    temporary=path.with_suffix(path.suffix+".tmp")
    if path.exists() or temporary.exists(): raise VerificationError("refusing to overwrite verification artifact")
    with temporary.open("x",encoding="utf-8") as handle: json.dump(value,handle,indent=2,sort_keys=True); handle.write("\n")
    temporary.replace(path)


def resolve(value: str|Path) -> Path:
    path=Path(value); return path.resolve() if path.is_absolute() else (REPO/path).resolve()


def ensure_cpu_only() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES")!="": raise VerificationError("CUDA_VISIBLE_DEVICES must be empty")
    forbidden=("torch","transformers","diffusers","consisid")
    if any(any(name==prefix or name.startswith(prefix+".") for prefix in forbidden) for name in sys.modules): raise VerificationError("forbidden ML module imported")


def verify_binding(path: Path,binding: dict,label: str) -> None:
    if path.resolve()!=resolve(binding["path"]) or not path.is_file() or path.is_symlink(): raise VerificationError(f"path mismatch: {label}")
    if path.stat().st_size!=binding["bytes"] or sha256(path)!=binding["sha256"]: raise VerificationError(f"byte or SHA mismatch: {label}")


def verify_dry_run(summary_path: Path) -> dict:
    ensure_cpu_only(); summary=read_json(summary_path)
    if summary.get("status")!=DRY_STATUS: raise VerificationError("dry-run status mismatch")
    exact={"planned_attributes":2,"planned_pairs_per_attribute":10,"planned_task_cell_rows":2880,"planned_pair_cell_rows":360,"planned_joined_rows":360,"planned_associations":36,"joined_rows_created":0}
    if any(summary.get(key)!=value for key,value in exact.items()): raise VerificationError("dry-run planned counts mismatch")
    false_fields=("real_input_paths_received","input_files_opened","cosine_aggregated","outcome_constructed","association_computed","model_modules_imported","model_weights_loaded","gpu_used","network_used","execution_authorized")
    if any(summary.get(field) is not False for field in false_fields): raise VerificationError("dry-run reports forbidden action")
    plan=resolve(summary["analysis_plan_path"])
    if not plan.is_file() or plan.is_symlink() or plan.stat().st_size!=summary["analysis_plan_bytes"] or sha256(plan)!=summary["analysis_plan_sha256"]: raise VerificationError("dry-run plan binding mismatch")
    return {"schema_version":1,"status":"PASS_INDEPENDENT_COSINE_LINKAGE_NO_WEIGHT_DRY_RUN_VERIFICATION","summary_path":str(summary_path.resolve()),"summary_bytes":summary_path.stat().st_size,"summary_sha256":sha256(summary_path),"real_inputs_opened":False,"cosine_aggregated":False,"joined_rows_created":0,"association_computed":False,"model_loaded":False,"gpu_used":False}


def read_bound_csv(binding: dict,label: str) -> list[dict[str,str]]:
    path=resolve(binding["path"]); verify_binding(path,binding,label)
    with path.open(newline="",encoding="utf-8") as handle:
        reader=csv.DictReader(handle)
        if reader.fieldnames!=binding["header"]: raise VerificationError(f"header mismatch: {label}")
        return list(reader)


def read_output(run_dir: Path,name: str,count: int) -> list[dict[str,str]]:
    path=run_dir/name
    if not path.is_file() or path.is_symlink(): raise VerificationError(f"missing output: {name}")
    with path.open(newline="",encoding="utf-8") as handle: rows=list(csv.DictReader(handle))
    if len(rows)!=count: raise VerificationError(f"row count mismatch: {name}")
    return rows


def number(value: str,context: str) -> float:
    try: result=float(value)
    except (TypeError,ValueError) as error: raise VerificationError(f"invalid numeric at {context}") from error
    if not math.isfinite(result): raise VerificationError(f"non-finite numeric at {context}")
    return result


def rank(values: list[float]) -> list[float]:
    order=sorted(range(len(values)),key=lambda index:values[index]); result=[0.0]*len(values); start=0
    while start<len(order):
        end=start+1
        while end<len(order) and values[order[end]]==values[order[start]]: end+=1
        value=((start+1)+end)/2.0
        for position in range(start,end): result[order[position]]=value
        start=end
    return result


def rho(x: list[float],y: list[float]) -> float|None:
    rx,ry=rank(x),rank(y); mx,my=statistics.fmean(rx),statistics.fmean(ry); cx=[v-mx for v in rx]; cy=[v-my for v in ry]
    denominator=math.sqrt(sum(v*v for v in cx)*sum(v*v for v in cy))
    return None if denominator==0 else sum(a*b for a,b in zip(cx,cy))/denominator


def group_site(site: int) -> str: return "early" if site<=6 else "middle" if site<=13 else "late"
def group_step(step: int) -> str: return "early" if step<=16 else "middle" if step<=33 else "late"


def recompute(eye: list[dict[str,str]],hair: list[dict[str,str]],injection: list[dict[str,str]],plan: dict) -> tuple[dict,dict,dict,dict]:
    planned={attribute:set(plan["planned_pair_ids"][attribute]) for attribute in ATTRIBUTES}
    eye_values=defaultdict(dict)
    for row in eye:
        pair=row["formal_pair_id"]; seed=int(row["seed_index"]); eye_values[pair][seed]=number(row["human_positive_minus_control"],f"eye/{pair}/{seed}")
    outcomes={("eyeglasses",pair):statistics.fmean(eye_values[pair].values()) for pair in planned["eyeglasses"] if set(eye_values[pair])=={1,2,3,4}}
    for row in hair:
        if row["attribute"]=="facial_hair" and row["formal_pair_id"] in planned["facial_hair"]: outcomes[("facial_hair",row["formal_pair_id"])]=number(row["primary_positive_minus_control"],"hair")
    if len(outcomes)!=20: raise VerificationError("outcome universe mismatch")
    sums=defaultdict(float); counts=defaultdict(int); meta={}; seen=set()
    for row in injection:
        task=row["trace_task_id"]; step=int(row["step_index"]); site=int(row["site_index"]); branch=row["cfg_branch"]
        position=(task,step,site,branch)
        if position in seen: raise VerificationError("duplicate injection position")
        seen.add(position); current=(row["formal_unit_id"],row["formal_pair_id"],row["attribute"],row["role"],int(row["seed_index"]),row["seed"])
        if task in meta and meta[task]!=current: raise VerificationError("task metadata drift")
        meta[task]=current; key=(task,branch,group_site(site),group_step(step)); sums[key]+=number(row["mean_tokenwise_cosine_h_r"],task); counts[key]+=1
    expected={"early":119,"middle":119,"late":112}; task_values={}
    for key,total in sums.items():
        if counts[key]!=expected[key[3]]: raise VerificationError("task-cell position mismatch")
        task_values[key]=total/counts[key]
    if len(task_values)!=2880: raise VerificationError("task-cell count mismatch")
    unit_values=defaultdict(list)
    for (task,branch,block,denoise),value in task_values.items(): unit_values[(meta[task][0],branch,block,denoise)].append(value)
    if any(len(values)!=4 for values in unit_values.values()): raise VerificationError("seed count mismatch")
    unit_means={key:statistics.fmean(values) for key,values in unit_values.items()}
    roles=defaultdict(dict)
    for unit,pair,attribute,role,_seed_index,_seed in meta.values(): roles[(attribute,pair)][role]=unit
    pair_values={}
    for (attribute,pair),units in roles.items():
        if set(units)!={"positive","control"}: raise VerificationError("pair role mismatch")
        for branch in BRANCHES:
            for block in GROUPS:
                for denoise in GROUPS:
                    key=(attribute,pair,branch,block,denoise); pair_values[key]=unit_means[(units["positive"],branch,block,denoise)]-unit_means[(units["control"],branch,block,denoise)]
    if len(pair_values)!=360: raise VerificationError("pair-cell count mismatch")
    grouped=defaultdict(list)
    for key,value in pair_values.items(): grouped[(key[0],key[2],key[3],key[4])].append((key[1],value,outcomes[(key[0],key[1])]))
    associations={key:rho([v for _p,v,_o in sorted(values)],[o for _p,_v,o in sorted(values)]) for key,values in grouped.items()}
    if len(associations)!=36 or any(len(values)!=10 for values in grouped.values()): raise VerificationError("association family mismatch")
    return outcomes,task_values,pair_values,associations


def verify_formal(auth_path: Path,plan_path: Path,run_dir: Path) -> dict:
    ensure_cpu_only(); auth=read_json(auth_path)
    if auth.get("status")!=EXECUTION_STATUS: raise VerificationError("formal execution not authorized")
    for flag in ("real_cosine_aggregation","outcome_construction","outcome_join","association_computation","independent_verification"):
        if auth.get("authority",{}).get(flag) is not True: raise VerificationError(f"missing authority: {flag}")
    if any(auth.get("authority",{}).get(flag) for flag in ("model_loading","gpu_execution","network")): raise VerificationError("forbidden capability authorized")
    verify_binding(plan_path.resolve(),auth["analysis_plan"],"plan"); verify_binding(Path(__file__).resolve(),auth["code"]["verifier"],"verifier")
    if run_dir.resolve()!=resolve(auth["output_dir"]): raise VerificationError("run directory mismatch")
    sources={name:read_bound_csv(auth["sources"][name],name) for name in ("eyeglasses_outcome","facial_hair_outcome","injection_summaries")}
    outcomes,task_values,pair_values,associations=recompute(sources["eyeglasses_outcome"],sources["facial_hair_outcome"],sources["injection_summaries"],read_json(plan_path))
    task_rows=read_output(run_dir,"cosine_task_3x3_v1.csv",2880); pair_rows=read_output(run_dir,"cosine_pair_3x3_v1.csv",360); joined=read_output(run_dir,"cosine_outcome_joined_pairs_v1.csv",360); assoc_rows=read_output(run_dir,"cosine_outcome_associations_v1.csv",36)
    seen_task=set()
    for row in task_rows:
        key=(row["trace_task_id"],row["cfg_branch"],row["block_group"],row["denoising_group"]); actual=number(row["mean_tokenwise_cosine_h_r_mean"],"task output")
        if key in seen_task or key not in task_values or not math.isclose(actual,task_values[key],rel_tol=0,abs_tol=1e-15): raise VerificationError("task key or value mismatch")
        seen_task.add(key)
    if seen_task!=set(task_values): raise VerificationError("task output key universe mismatch")
    seen_pair=set()
    for row in pair_rows:
        key=(row["attribute"],row["formal_pair_id"],row["cfg_branch"],row["block_group"],row["denoising_group"]); actual=number(row["positive_minus_control"],"pair output")
        if key in seen_pair or key not in pair_values or not math.isclose(actual,pair_values[key],rel_tol=0,abs_tol=1e-15): raise VerificationError("pair key or value mismatch")
        seen_pair.add(key)
    if seen_pair!=set(pair_values): raise VerificationError("pair output key universe mismatch")
    seen_join=set()
    for row in joined:
        key=(row["attribute"],row["formal_pair_id"],row["cfg_branch"],row["block_group"],row["denoising_group"])
        if key in seen_join or key not in pair_values or not math.isclose(number(row["positive_minus_control"],"join mechanism"),pair_values[key],rel_tol=0,abs_tol=1e-15) or not math.isclose(number(row["retention_outcome"],"join outcome"),outcomes[(key[0],key[1])],rel_tol=0,abs_tol=1e-15): raise VerificationError("joined key or value mismatch")
        seen_join.add(key)
    if seen_join!=set(pair_values): raise VerificationError("joined output key universe mismatch")
    seen_assoc=set()
    for row in assoc_rows:
        key=(row["attribute"],row["cfg_branch"],row["block_group"],row["denoising_group"]); expected=associations[key]
        if key in seen_assoc: raise VerificationError("duplicate association key")
        seen_assoc.add(key)
        if expected is None:
            if row["defined"]!="False" or row["spearman_rho"]!="": raise VerificationError("undefined association encoding mismatch")
        elif row["defined"]!="True" or not math.isclose(number(row["spearman_rho"],"association"),expected,rel_tol=0,abs_tol=1e-15): raise VerificationError("association mismatch")
    if seen_assoc!=set(associations): raise VerificationError("association key universe mismatch")
    return {"schema_version":1,"status":"PASS_INDEPENDENT_COSINE_LINKAGE_VERIFICATION","metric_role":"secondary_diagnostic","task_cell_rows":2880,"pair_cell_rows":360,"joined_pair_rows":360,"associations":36,"p_values":False,"confidence_intervals":False,"model_loaded":False,"gpu_used":False}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--mode",choices=("dry-run","formal"),required=True); parser.add_argument("--summary",type=Path); parser.add_argument("--execution-authorization",type=Path); parser.add_argument("--plan",type=Path); parser.add_argument("--run-dir",type=Path); parser.add_argument("--output",required=True,type=Path); args=parser.parse_args()
    if args.mode=="dry-run":
        if not args.summary or args.execution_authorization or args.plan or args.run_dir: raise VerificationError("dry-run verifier argument mismatch")
        result=verify_dry_run(args.summary)
    else:
        if not args.execution_authorization or not args.plan or not args.run_dir or args.summary: raise VerificationError("formal verifier argument mismatch")
        result=verify_formal(args.execution_authorization,args.plan,args.run_dir)
    atomic_json(args.output,result); print(json.dumps(result,indent=2,sort_keys=True)); return 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except VerificationError as error:
        print(f"FAIL: {error}",file=sys.stderr); raise SystemExit(2)
