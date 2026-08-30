#!/usr/bin/env python3
"""CPU-only fixed-family token-RMS quantile/outcome linkage analyzer v1."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import analyze_cosine_outcome_linkage_v1 as base


REPO=Path(__file__).resolve().parents[1]
PLAN_STATUS="APPROVED_FIXED_108_FAMILY_TWO_STAGE_EXECUTION"
EXECUTION_STATUS="CPU_TOKEN_QUANTILE_LINKAGE_EXECUTION_APPROVED"
DRY_STATUS="PASS_NO_WEIGHT_TOKEN_QUANTILE_LINKAGE_DRY_RUN_NO_REAL_INPUT"
METRICS=("token_rms_r_q10","token_rms_r_q50","token_rms_r_q90")
ATTRIBUTES=base.ATTRIBUTES; BRANCHES=base.BRANCHES; GROUPS=base.GROUPS
SOURCE_NAMES=base.SOURCE_NAMES


class QuantileLinkageError(RuntimeError): pass


def validate_plan(plan: dict) -> dict[str,tuple[str,...]]:
    if plan.get("status")!=PLAN_STATUS: raise QuantileLinkageError("approved plan status mismatch")
    if tuple(plan.get("attributes",[]))!=ATTRIBUTES or tuple(plan.get("metrics",[]))!=METRICS: raise QuantileLinkageError("attribute or metric universe drift")
    pairs={attribute:tuple(plan["planned_pair_ids"][attribute]) for attribute in ATTRIBUTES}
    if any(len(values)!=10 or len(set(values))!=10 for values in pairs.values()): raise QuantileLinkageError("pair universe drift")
    if tuple(plan.get("cfg_branches",[]))!=BRANCHES or tuple(plan.get("block_groups",{}))!=GROUPS or tuple(plan.get("denoising_groups",{}))!=GROUPS: raise QuantileLinkageError("grid universe drift")
    if plan.get("metric_role")!="secondary_complete_family": raise QuantileLinkageError("metric role drift")
    counts=plan.get("expected_counts",{})
    exact={"source_rows":336000,"trace_tasks":160,"rows_per_task":2100,"task_cell_rows":8640,"pair_cell_rows":1080,"joined_rows":1080,"associations":108,"pairs_per_association":10}
    if any(counts.get(key)!=value for key,value in exact.items()): raise QuantileLinkageError("planned count drift")
    association=plan.get("association",{})
    if association.get("method")!="spearman_rank_correlation" or association.get("ties")!="average_ranks" or association.get("p_values") or association.get("confidence_intervals") or association.get("reduced_panel_if_missing"): raise QuantileLinkageError("association definition drift")
    return pairs


def no_weight_dry_run(plan_path: Path,output_path: Path) -> dict:
    try: base.ensure_cpu_only()
    except base.CosineLinkageError as error: raise QuantileLinkageError(str(error)) from error
    validate_plan(base.read_json(plan_path))
    result={"schema_version":1,"status":DRY_STATUS,"analysis_plan_path":str(plan_path.resolve()),"analysis_plan_bytes":plan_path.stat().st_size,"analysis_plan_sha256":base.sha256(plan_path),"metrics":list(METRICS),"metric_role":"secondary_complete_family","planned_attributes":2,"planned_pairs_per_attribute":10,"planned_task_cell_rows":8640,"planned_pair_cell_rows":1080,"planned_joined_rows":1080,"planned_associations":108,"real_input_paths_received":False,"input_files_opened":False,"quantiles_aggregated":False,"outcome_constructed":False,"joined_rows_created":0,"association_computed":False,"model_modules_imported":False,"model_weights_loaded":False,"gpu_used":False,"network_used":False,"execution_authorized":False}
    base.atomic_json(output_path,result); return result


def aggregate_quantiles(rows,pairs: dict[str,tuple[str,...]]) -> tuple[list[dict],list[dict]]:
    sums=defaultdict(float); counts=defaultdict(int); metadata={}; seen=set()
    for row in rows:
        task=row["trace_task_id"]; step=int(row["step_index"]); site=int(row["site_index"]); branch=row["cfg_branch"]
        position=(task,step,site,branch)
        if position in seen: raise QuantileLinkageError("duplicate injection position")
        seen.add(position)
        if step not in range(50) or site not in range(21) or branch not in BRANCHES: raise QuantileLinkageError("position domain drift")
        attribute,pair,role,seed_index=row["attribute"],row["formal_pair_id"],row["role"],int(row["seed_index"])
        if attribute not in ATTRIBUTES or pair not in pairs[attribute] or role not in ("positive","control") or seed_index not in (1,2,3,4): raise QuantileLinkageError("task metadata drift")
        meta=(attribute,pair,role,seed_index,row["formal_unit_id"],row["seed"])
        if task in metadata and metadata[task]!=meta: raise QuantileLinkageError("metadata changes within task")
        metadata[task]=meta
        try: values=tuple(float(row[metric]) for metric in METRICS)
        except (KeyError,TypeError,ValueError) as error: raise QuantileLinkageError("invalid quantile value") from error
        if any(not math.isfinite(value) for value in values) or not values[0]<=values[1]<=values[2]: raise QuantileLinkageError("nonfinite or nonmonotone quantile triple")
        cell=(task,branch,base.block_group(site),base.denoising_group(step)); counts[cell]+=1
        for metric,value in zip(METRICS,values): sums[(metric,*cell)]+=value
    expected={"early":119,"middle":119,"late":112}
    if len(metadata)!=160 or len(counts)!=2880 or len(sums)!=8640: raise QuantileLinkageError("task or task-cell count mismatch")
    task_rows=[]
    for key in sorted(sums):
        metric,task,branch,block,denoise=key; cell=(task,branch,block,denoise)
        if counts[cell]!=expected[denoise]: raise QuantileLinkageError("task-cell position count mismatch")
        attribute,pair,role,seed_index,unit,seed=metadata[task]
        task_rows.append({"metric":metric,"trace_task_id":task,"formal_unit_id":unit,"formal_pair_id":pair,"attribute":attribute,"role":role,"seed_index":seed_index,"seed":seed,"cfg_branch":branch,"block_group":block,"denoising_group":denoise,"quantile_value_mean":sums[key]/counts[cell],"positions":counts[cell]})
    unit_values=defaultdict(list)
    for row in task_rows: unit_values[(row["metric"],row["formal_unit_id"],row["cfg_branch"],row["block_group"],row["denoising_group"])].append(float(row["quantile_value_mean"]))
    if len(unit_values)!=2160 or any(len(values)!=4 for values in unit_values.values()): raise QuantileLinkageError("four-seed unit-cell mismatch")
    unit_means={key:statistics.fmean(values) for key,values in unit_values.items()}
    roles=defaultdict(dict)
    for attribute,pair,role,_seed_index,unit,_seed in metadata.values(): roles[(attribute,pair)][role]=unit
    if len(roles)!=20 or any(set(value)!={"positive","control"} for value in roles.values()): raise QuantileLinkageError("matched-pair role universe drift")
    pair_rows=[]
    for metric in METRICS:
        for (attribute,pair),units in sorted(roles.items()):
            for branch in BRANCHES:
                for block in GROUPS:
                    for denoise in GROUPS:
                        positive=unit_means[(metric,units["positive"],branch,block,denoise)]; control=unit_means[(metric,units["control"],branch,block,denoise)]
                        pair_rows.append({"metric":metric,"attribute":attribute,"formal_pair_id":pair,"cfg_branch":branch,"block_group":block,"denoising_group":denoise,"positive_four_seed_mean":positive,"control_four_seed_mean":control,"positive_minus_control":positive-control})
    if len(pair_rows)!=1080: raise QuantileLinkageError("pair-cell row count mismatch")
    return task_rows,pair_rows


def join_and_associate(pair_rows,outcomes) -> tuple[list[dict],list[dict]]:
    joined=[]; grouped=defaultdict(list)
    for row in pair_rows:
        outcome_key=(row["attribute"],row["formal_pair_id"])
        if outcome_key not in outcomes: raise QuantileLinkageError("missing outcome")
        item={**row,"retention_outcome":outcomes[outcome_key]}; joined.append(item)
        grouped[(row["metric"],row["attribute"],row["cfg_branch"],row["block_group"],row["denoising_group"])].append(item)
    if len(joined)!=1080 or len(grouped)!=108: raise QuantileLinkageError("joined family count mismatch")
    associations=[]
    for (metric,attribute,branch,block,denoise),values in sorted(grouped.items()):
        if len(values)!=10: raise QuantileLinkageError("association panel is not ten pairs")
        rho=base.spearman([float(row["positive_minus_control"]) for row in values],[float(row["retention_outcome"]) for row in values])
        associations.append({"metric":metric,"attribute":attribute,"cfg_branch":branch,"block_group":block,"denoising_group":denoise,"pairs":10,"spearman_rho":"" if rho is None else rho,"defined":rho is not None,"role":"secondary_complete_family"})
    return joined,associations


def validate_execution_authorization(path: Path,plan_path: Path,output_dir: Path) -> dict:
    try: base.ensure_cpu_only()
    except base.CosineLinkageError as error: raise QuantileLinkageError(str(error)) from error
    authorization=base.read_json(path)
    if authorization.get("status")!=EXECUTION_STATUS: raise QuantileLinkageError("formal quantile linkage execution is not authorized")
    authority=authorization.get("authority",{})
    for flag in ("real_quantile_aggregation","outcome_construction","outcome_join","association_computation","independent_verification"):
        if authority.get(flag) is not True: raise QuantileLinkageError(f"missing execution authority: {flag}")
    if any(authority.get(flag) for flag in ("model_loading","gpu_execution","network")): raise QuantileLinkageError("forbidden capability authorized")
    try:
        base.verify_bound_file(plan_path.resolve(),authorization["analysis_plan"],"analysis plan")
        base.verify_bound_file(Path(__file__).resolve(),authorization["code"]["analyzer"],"analyzer")
        base.verify_bound_file(Path(base.__file__).resolve(),authorization["code"]["base_analyzer_dependency"],"base analyzer dependency")
    except base.CosineLinkageError as error: raise QuantileLinkageError(str(error)) from error
    authorized_output=base.resolve(authorization["output_dir"])
    if output_dir.resolve()!=authorized_output or output_dir.exists(): raise QuantileLinkageError("output mismatch or overwrite attempt")
    if REPO==authorized_output or REPO in authorized_output.parents: raise QuantileLinkageError("pair outputs must remain external to Git")
    if set(authorization.get("sources",{}))!=set(SOURCE_NAMES): raise QuantileLinkageError("source universe mismatch")
    return authorization


def run_formal(authorization_path: Path,plan_path: Path,output_dir: Path) -> dict:
    authorization=validate_execution_authorization(authorization_path,plan_path,output_dir); pairs=validate_plan(base.read_json(plan_path))
    try: sources={name:base.read_bound_csv(authorization["sources"][name],name) for name in SOURCE_NAMES}
    except base.CosineLinkageError as error: raise QuantileLinkageError(str(error)) from error
    try: outcomes=base.construct_outcomes(sources["eyeglasses_outcome"],sources["facial_hair_outcome"],pairs)
    except base.CosineLinkageError as error: raise QuantileLinkageError(str(error)) from error
    task_rows,pair_rows=aggregate_quantiles(sources["injection_summaries"],pairs); joined,associations=join_and_associate(pair_rows,outcomes)
    output_dir.mkdir(parents=True,exist_ok=False)
    base.atomic_csv(output_dir/"quantile_task_3x3_v1.csv",tuple(task_rows[0]),task_rows); base.atomic_csv(output_dir/"quantile_pair_3x3_v1.csv",tuple(pair_rows[0]),pair_rows); base.atomic_csv(output_dir/"quantile_outcome_joined_pairs_v1.csv",tuple(joined[0]),joined); base.atomic_csv(output_dir/"quantile_outcome_associations_v1.csv",tuple(associations[0]),associations)
    summary={"schema_version":1,"status":"COMPLETE_TOKEN_QUANTILE_LINKAGE_PENDING_INDEPENDENT_VERIFICATION","metrics":list(METRICS),"metric_role":"secondary_complete_family","task_cell_rows":len(task_rows),"pair_cell_rows":len(pair_rows),"joined_rows":len(joined),"associations":len(associations),"p_values":False,"confidence_intervals":False,"derived_metrics_computed":False,"gpu_used":False,"model_loaded":False}
    base.atomic_json(output_dir/"analysis_summary_v1.json",summary); return summary


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--mode",choices=("dry-run","formal"),required=True); parser.add_argument("--plan",required=True,type=Path); parser.add_argument("--dry-run-output",type=Path); parser.add_argument("--execution-authorization",type=Path); parser.add_argument("--output-dir",type=Path); args=parser.parse_args()
    if args.mode=="dry-run":
        if not args.dry_run_output or args.execution_authorization or args.output_dir: raise QuantileLinkageError("dry-run argument mismatch")
        result=no_weight_dry_run(args.plan,args.dry_run_output)
    else:
        if not args.execution_authorization or not args.output_dir or args.dry_run_output: raise QuantileLinkageError("formal argument mismatch")
        result=run_formal(args.execution_authorization,args.plan,args.output_dir)
    print(json.dumps(result,indent=2,sort_keys=True)); return 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except (QuantileLinkageError,base.CosineLinkageError) as error:
        print(f"FAIL: {error}",file=sys.stderr); raise SystemExit(2)
