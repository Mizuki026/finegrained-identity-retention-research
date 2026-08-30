#!/usr/bin/env python3
"""Independent verifier for fixed-family token-RMS quantile linkage v1."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import verify_cosine_outcome_linkage_v1 as base


DRY_STATUS="PASS_NO_WEIGHT_TOKEN_QUANTILE_LINKAGE_DRY_RUN_NO_REAL_INPUT"
EXECUTION_STATUS="CPU_TOKEN_QUANTILE_LINKAGE_EXECUTION_APPROVED"
METRICS=("token_rms_r_q10","token_rms_r_q50","token_rms_r_q90")
ATTRIBUTES=base.ATTRIBUTES; BRANCHES=base.BRANCHES; GROUPS=base.GROUPS


class VerificationError(RuntimeError): pass


def verify_dry_run(summary_path: Path) -> dict:
    try: base.ensure_cpu_only()
    except base.VerificationError as error: raise VerificationError(str(error)) from error
    summary=base.read_json(summary_path)
    if summary.get("status")!=DRY_STATUS or tuple(summary.get("metrics",[]))!=METRICS: raise VerificationError("dry-run status or metric mismatch")
    exact={"planned_attributes":2,"planned_pairs_per_attribute":10,"planned_task_cell_rows":8640,"planned_pair_cell_rows":1080,"planned_joined_rows":1080,"planned_associations":108,"joined_rows_created":0}
    if any(summary.get(key)!=value for key,value in exact.items()): raise VerificationError("dry-run count mismatch")
    false_fields=("real_input_paths_received","input_files_opened","quantiles_aggregated","outcome_constructed","association_computed","model_modules_imported","model_weights_loaded","gpu_used","network_used","execution_authorized")
    if any(summary.get(field) is not False for field in false_fields): raise VerificationError("dry-run reports forbidden action")
    plan=base.resolve(summary["analysis_plan_path"])
    if not plan.is_file() or plan.is_symlink() or plan.stat().st_size!=summary["analysis_plan_bytes"] or base.sha256(plan)!=summary["analysis_plan_sha256"]: raise VerificationError("dry-run plan binding mismatch")
    return {"schema_version":1,"status":"PASS_INDEPENDENT_TOKEN_QUANTILE_NO_WEIGHT_DRY_RUN_VERIFICATION","summary_path":str(summary_path.resolve()),"summary_bytes":summary_path.stat().st_size,"summary_sha256":base.sha256(summary_path),"real_inputs_opened":False,"quantiles_aggregated":False,"joined_rows_created":0,"association_computed":False,"model_loaded":False,"gpu_used":False}


def recompute(eye,hair,injection,plan) -> tuple[dict,dict,dict,dict]:
    planned={attribute:set(plan["planned_pair_ids"][attribute]) for attribute in ATTRIBUTES}
    eye_values=defaultdict(dict)
    for row in eye: eye_values[row["formal_pair_id"]][int(row["seed_index"])]=base.number(row["human_positive_minus_control"],"eye")
    outcomes={("eyeglasses",pair):statistics.fmean(eye_values[pair].values()) for pair in planned["eyeglasses"] if set(eye_values[pair])=={1,2,3,4}}
    for row in hair:
        if row["attribute"]=="facial_hair" and row["formal_pair_id"] in planned["facial_hair"]: outcomes[("facial_hair",row["formal_pair_id"])]=base.number(row["primary_positive_minus_control"],"hair")
    if len(outcomes)!=20: raise VerificationError("outcome universe mismatch")
    sums=defaultdict(float); counts=defaultdict(int); meta={}; seen=set()
    for row in injection:
        task=row["trace_task_id"]; step=int(row["step_index"]); site=int(row["site_index"]); branch=row["cfg_branch"]; position=(task,step,site,branch)
        if position in seen: raise VerificationError("duplicate injection position")
        seen.add(position); current=(row["formal_unit_id"],row["formal_pair_id"],row["attribute"],row["role"],int(row["seed_index"]),row["seed"])
        if task in meta and meta[task]!=current: raise VerificationError("task metadata drift")
        meta[task]=current; cell=(task,branch,base.group_site(site),base.group_step(step)); counts[cell]+=1
        values=tuple(base.number(row[metric],metric) for metric in METRICS)
        if not values[0]<=values[1]<=values[2]: raise VerificationError("nonmonotone quantile triple")
        for metric,value in zip(METRICS,values): sums[(metric,*cell)]+=value
    expected={"early":119,"middle":119,"late":112}; task_values={}
    for key,total in sums.items():
        metric,task,branch,block,denoise=key; cell=(task,branch,block,denoise)
        if counts[cell]!=expected[denoise]: raise VerificationError("task-cell position mismatch")
        task_values[key]=total/counts[cell]
    if len(meta)!=160 or len(task_values)!=8640: raise VerificationError("task-cell universe mismatch")
    unit_values=defaultdict(list)
    for (metric,task,branch,block,denoise),value in task_values.items(): unit_values[(metric,meta[task][0],branch,block,denoise)].append(value)
    if any(len(values)!=4 for values in unit_values.values()): raise VerificationError("four-seed count mismatch")
    unit_means={key:statistics.fmean(values) for key,values in unit_values.items()}
    roles=defaultdict(dict)
    for unit,pair,attribute,role,_seed_index,_seed in meta.values(): roles[(attribute,pair)][role]=unit
    pair_values={}
    for metric in METRICS:
        for (attribute,pair),units in roles.items():
            if set(units)!={"positive","control"}: raise VerificationError("pair role mismatch")
            for branch in BRANCHES:
                for block in GROUPS:
                    for denoise in GROUPS:
                        key=(metric,attribute,pair,branch,block,denoise); pair_values[key]=unit_means[(metric,units["positive"],branch,block,denoise)]-unit_means[(metric,units["control"],branch,block,denoise)]
    if len(pair_values)!=1080: raise VerificationError("pair-cell universe mismatch")
    grouped=defaultdict(list)
    for key,value in pair_values.items(): grouped[(key[0],key[1],key[3],key[4],key[5])].append((key[2],value,outcomes[(key[1],key[2])]))
    associations={key:base.rho([value for _pair,value,_outcome in sorted(values)],[outcome for _pair,_value,outcome in sorted(values)]) for key,values in grouped.items()}
    if len(associations)!=108 or any(len(values)!=10 for values in grouped.values()): raise VerificationError("association universe mismatch")
    return outcomes,task_values,pair_values,associations


def verify_formal(auth_path: Path,plan_path: Path,run_dir: Path) -> dict:
    try: base.ensure_cpu_only()
    except base.VerificationError as error: raise VerificationError(str(error)) from error
    auth=base.read_json(auth_path)
    if auth.get("status")!=EXECUTION_STATUS: raise VerificationError("formal execution not authorized")
    for flag in ("real_quantile_aggregation","outcome_construction","outcome_join","association_computation","independent_verification"):
        if auth.get("authority",{}).get(flag) is not True: raise VerificationError(f"missing authority: {flag}")
    if any(auth.get("authority",{}).get(flag) for flag in ("model_loading","gpu_execution","network")): raise VerificationError("forbidden capability authorized")
    try:
        base.verify_binding(plan_path.resolve(),auth["analysis_plan"],"plan"); base.verify_binding(Path(__file__).resolve(),auth["code"]["verifier"],"verifier"); base.verify_binding(Path(base.__file__).resolve(),auth["code"]["base_verifier_dependency"],"base verifier dependency")
    except base.VerificationError as error: raise VerificationError(str(error)) from error
    if run_dir.resolve()!=base.resolve(auth["output_dir"]): raise VerificationError("run directory mismatch")
    try: sources={name:base.read_bound_csv(auth["sources"][name],name) for name in ("eyeglasses_outcome","facial_hair_outcome","injection_summaries")}
    except base.VerificationError as error: raise VerificationError(str(error)) from error
    outcomes,task_values,pair_values,associations=recompute(sources["eyeglasses_outcome"],sources["facial_hair_outcome"],sources["injection_summaries"],base.read_json(plan_path))
    task_rows=base.read_output(run_dir,"quantile_task_3x3_v1.csv",8640); pair_rows=base.read_output(run_dir,"quantile_pair_3x3_v1.csv",1080); joined=base.read_output(run_dir,"quantile_outcome_joined_pairs_v1.csv",1080); assoc_rows=base.read_output(run_dir,"quantile_outcome_associations_v1.csv",108)
    seen=set()
    for row in task_rows:
        key=(row["metric"],row["trace_task_id"],row["cfg_branch"],row["block_group"],row["denoising_group"])
        if key in seen or key not in task_values or not math.isclose(base.number(row["quantile_value_mean"],"task output"),task_values[key],rel_tol=0,abs_tol=1e-15): raise VerificationError("task output mismatch")
        seen.add(key)
    if seen!=set(task_values): raise VerificationError("task output key universe mismatch")
    seen=set()
    for row in pair_rows:
        key=(row["metric"],row["attribute"],row["formal_pair_id"],row["cfg_branch"],row["block_group"],row["denoising_group"])
        if key in seen or key not in pair_values or not math.isclose(base.number(row["positive_minus_control"],"pair output"),pair_values[key],rel_tol=0,abs_tol=1e-15): raise VerificationError("pair output mismatch")
        seen.add(key)
    if seen!=set(pair_values): raise VerificationError("pair output key universe mismatch")
    seen=set()
    for row in joined:
        key=(row["metric"],row["attribute"],row["formal_pair_id"],row["cfg_branch"],row["block_group"],row["denoising_group"])
        if key in seen or key not in pair_values or not math.isclose(base.number(row["positive_minus_control"],"join mechanism"),pair_values[key],rel_tol=0,abs_tol=1e-15) or not math.isclose(base.number(row["retention_outcome"],"join outcome"),outcomes[(key[1],key[2])],rel_tol=0,abs_tol=1e-15): raise VerificationError("joined output mismatch")
        seen.add(key)
    if seen!=set(pair_values): raise VerificationError("joined output key universe mismatch")
    seen=set()
    for row in assoc_rows:
        key=(row["metric"],row["attribute"],row["cfg_branch"],row["block_group"],row["denoising_group"]); expected=associations[key]
        if key in seen: raise VerificationError("duplicate association key")
        seen.add(key)
        if expected is None:
            if row["defined"]!="False" or row["spearman_rho"]!="": raise VerificationError("undefined association encoding mismatch")
        elif row["defined"]!="True" or not math.isclose(base.number(row["spearman_rho"],"association"),expected,rel_tol=0,abs_tol=1e-15): raise VerificationError("association mismatch")
    if seen!=set(associations): raise VerificationError("association key universe mismatch")
    return {"schema_version":1,"status":"PASS_INDEPENDENT_TOKEN_QUANTILE_LINKAGE_VERIFICATION","metrics":list(METRICS),"metric_role":"secondary_complete_family","task_cell_rows":8640,"pair_cell_rows":1080,"joined_rows":1080,"associations":108,"derived_metrics":False,"p_values":False,"confidence_intervals":False,"model_loaded":False,"gpu_used":False}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--mode",choices=("dry-run","formal"),required=True); parser.add_argument("--summary",type=Path); parser.add_argument("--execution-authorization",type=Path); parser.add_argument("--plan",type=Path); parser.add_argument("--run-dir",type=Path); parser.add_argument("--output",required=True,type=Path); args=parser.parse_args()
    if args.mode=="dry-run":
        if not args.summary or args.execution_authorization or args.plan or args.run_dir: raise VerificationError("dry-run argument mismatch")
        result=verify_dry_run(args.summary)
    else:
        if not args.execution_authorization or not args.plan or not args.run_dir or args.summary: raise VerificationError("formal argument mismatch")
        result=verify_formal(args.execution_authorization,args.plan,args.run_dir)
    base.atomic_json(args.output,result); print(json.dumps(result,indent=2,sort_keys=True)); return 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except (VerificationError,base.VerificationError) as error:
        print(f"FAIL: {error}",file=sys.stderr); raise SystemExit(2)
