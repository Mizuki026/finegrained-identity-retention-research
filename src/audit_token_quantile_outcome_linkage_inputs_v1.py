#!/usr/bin/env python3
"""One-source CPU-only formal input audit for token-quantile linkage v1."""
from __future__ import annotations

import argparse
import csv
import json
import math
import stat
import sys
from collections import Counter
from pathlib import Path

import audit_cosine_outcome_linkage_inputs_v1 as base


AUTH_STATUS="CPU_ONLY_TOKEN_QUANTILE_FORMAL_INPUT_AUDIT_APPROVED"
SOURCE_NAMES=base.SOURCE_NAMES
METRICS=("token_rms_r_q10","token_rms_r_q50","token_rms_r_q90")


class AuditError(RuntimeError): pass


def audit_injection(path: Path) -> tuple[list[str],list[str],dict]:
    tasks_expected=base.expected_tasks(); task_counts=Counter(); branch_counts=Counter(); keys=[]; seen=set(); checked=0
    with path.open(newline="",encoding="utf-8") as handle:
        reader=csv.DictReader(handle)
        if reader.fieldnames!=base.INJECTION_HEADER: raise AuditError("injection header mismatch")
        for index,row in enumerate(reader,1):
            task=row["trace_task_id"]
            if task not in tasks_expected: raise AuditError(f"unexpected trace task at row {index}")
            attribute,pair,role,seed_index,seed,unit=tasks_expected[task]
            if (row["attribute"],row["formal_pair_id"],row["role"],row["seed_index"],row["seed"],row["formal_unit_id"])!=(attribute,pair,role,str(seed_index),seed,unit): raise AuditError(f"task metadata mismatch at row {index}")
            if row["phase"]!="scientific" or row["condition"]!="baseline" or row["repetition"]!="1" or row["local_face_scale"]!="1.0": raise AuditError(f"condition metadata mismatch at row {index}")
            step,site=int(row["step_index"]),int(row["site_index"]); branch=row["cfg_branch"]
            if step not in range(50) or site not in range(21) or branch not in base.BRANCHES: raise AuditError(f"position domain mismatch at row {index}")
            key=f"{task}|{step}|{site}|{branch}"
            if key in seen: raise AuditError(f"duplicate position key at row {index}")
            seen.add(key); keys.append(key); task_counts[task]+=1; branch_counts[branch]+=1
            try: values=tuple(float(row[metric]) for metric in METRICS)
            except (KeyError,TypeError,ValueError) as error: raise AuditError(f"invalid quantile triple at row {index}") from error
            if any(not math.isfinite(value) for value in values): raise AuditError(f"nonfinite quantile at row {index}")
            if not values[0]<=values[1]<=values[2]: raise AuditError(f"nonmonotone quantile triple at row {index}")
            checked+=3
    if len(keys)!=336000 or set(task_counts)!=set(tasks_expected) or set(task_counts.values())!={2100}: raise AuditError("injection row/task count mismatch")
    if branch_counts!=Counter({"unconditional":168000,"text":168000}): raise AuditError("branch balance mismatch")
    return base.INJECTION_HEADER,sorted(keys),{"rows":336000,"unique_keys":336000,"finite_values_checked":checked,"quantile_triples_checked":336000,"nonmonotone_triples":0,"trace_tasks":160,"rows_per_task":2100,"key_columns":["trace_task_id","step_index","site_index","cfg_branch"]}


def audit(authorization_path: Path,source_name: str,output_dir: Path) -> dict:
    try: base.ensure_cpu_offline()
    except base.AuditError as error: raise AuditError(str(error)) from error
    authorization=base.read_json(authorization_path)
    if authorization.get("status")!=AUTH_STATUS: raise AuditError("formal input audit is not authorized")
    if source_name not in SOURCE_NAMES: raise AuditError("source outside authorized universe")
    forbidden=("quantile_aggregation","pair_outcome_construction","outcome_trace_join","spearman_or_other_association","cross_source_value_comparison","derived_quantile_metric","model_loading","gpu_execution","network_access")
    if any(authorization.get("not_authorized",{}).get(name) is not True for name in forbidden): raise AuditError("authorization does not forbid every disallowed operation")
    expected_output=Path(authorization["external_runtime"]).resolve()/source_name
    if output_dir.resolve()!=expected_output or output_dir.exists(): raise AuditError("output mismatch or overwrite attempt")
    binding=authorization["sources"][source_name]; source_path=Path(binding["path"]).resolve()
    if not source_path.is_file() or source_path.is_symlink(): raise AuditError("invalid source path")
    if source_path.stat().st_size!=binding["bytes"] or base.sha256(source_path)!=binding["sha256"]: raise AuditError("source byte or SHA mismatch")
    try:
        if source_name=="eyeglasses_outcome": header,keys,counts=base.audit_eye(source_path)
        elif source_name=="facial_hair_outcome": header,keys,counts=base.audit_hair(source_path)
        else: header,keys,counts=audit_injection(source_path)
    except base.AuditError as error: raise AuditError(str(error)) from error
    output_dir.mkdir(parents=True,exist_ok=False); key_path=output_dir/"keys_v1.csv"; base.atomic_keys(key_path,keys)
    record={"schema_version":1,"status":"PASS_TOKEN_QUANTILE_FORMAL_SINGLE_SOURCE_INPUT_AUDIT","source_name":source_name,"path":str(source_path),"bytes":source_path.stat().st_size,"sha256":base.sha256(source_path),"mode":format(stat.S_IMODE(source_path.stat().st_mode),"03o"),"header":header,"key_columns":counts["key_columns"],"expected_rows":counts["rows"],"expected_unique_keys":counts["unique_keys"],"key_manifest":{"path":str(key_path),"bytes":key_path.stat().st_size,"sha256":base.sha256(key_path)},"numeric_values_exported":False,"source_modified":False}
    binding_path=output_dir/"binding_v1.json"; base.atomic_json(binding_path,record)
    summary={"schema_version":1,"status":"PASS_TOKEN_QUANTILE_FORMAL_SINGLE_SOURCE_INPUT_AUDIT","source_name":source_name,"source_path":str(source_path),"source_bytes":source_path.stat().st_size,"source_sha256":base.sha256(source_path),**{key:value for key,value in counts.items() if key!="key_columns"},"duplicate_keys":0,"missing_required_fields":0,"nonfinite_values":0,"exact_planned_key_universe":True,"keys_manifest_bytes":key_path.stat().st_size,"keys_manifest_sha256":base.sha256(key_path),"binding_bytes":binding_path.stat().st_size,"binding_sha256":base.sha256(binding_path),"other_sources_opened":0,"quantiles_aggregated":False,"pair_outcome_constructed":False,"outcome_trace_joined":False,"association_computed":False,"derived_quantile_metric_computed":False,"numeric_values_exported":False,"model_loaded":False,"gpu_used":False,"network_used":False}
    base.atomic_json(output_dir/"audit_summary_v1.json",summary); return summary


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--authorization",required=True,type=Path); parser.add_argument("--source-name",required=True,choices=SOURCE_NAMES); parser.add_argument("--output-dir",required=True,type=Path); args=parser.parse_args()
    print(json.dumps(audit(args.authorization,args.source_name,args.output_dir),indent=2,sort_keys=True)); return 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except (AuditError,base.AuditError) as error:
        print(f"FAIL: {error}",file=sys.stderr); raise SystemExit(2)
