#!/usr/bin/env python3
"""Independent verifier for token-quantile linkage input-audit v1."""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

import verify_cosine_outcome_linkage_input_audit_v1 as base


AUTH_STATUS="CPU_ONLY_TOKEN_QUANTILE_FORMAL_INPUT_AUDIT_APPROVED"
SOURCE_NAMES=base.SOURCE_NAMES
METRICS=("token_rms_r_q10","token_rms_r_q50","token_rms_r_q90")


class VerificationError(RuntimeError): pass


def recompute_injection(path: Path) -> tuple[list[str],list[str],int,int,int]:
    keys=[]; checked=0; triples=0; task_counts=Counter(); branch_counts=Counter(); task_meta={}
    expected_tasks=set()
    for attribute in ("eyeglasses","facial_hair"):
        for pair in base.pairs(attribute):
            for role in ("positive","control"):
                unit=f"{pair}_{role}"
                for seed_index in base.SEEDS: expected_tasks.add(f"S__{unit}__s{seed_index}__baseline__r1")
    with path.open(newline="",encoding="utf-8") as handle:
        reader=csv.DictReader(handle); header=list(reader.fieldnames or [])
        for index,row in enumerate(reader,1):
            task=row["trace_task_id"]
            if task not in expected_tasks: raise VerificationError(f"unexpected task at row {index}")
            step,site=int(row["step_index"]),int(row["site_index"]); branch=row["cfg_branch"]
            if step not in range(50) or site not in range(21) or branch not in ("unconditional","text"): raise VerificationError(f"position drift at row {index}")
            if row["phase"]!="scientific" or row["condition"]!="baseline" or row["repetition"]!="1": raise VerificationError(f"condition drift at row {index}")
            current=(row["formal_unit_id"],row["formal_pair_id"],row["attribute"],row["role"],row["seed_index"],row["seed"])
            if task in task_meta and task_meta[task]!=current: raise VerificationError(f"metadata drift at row {index}")
            task_meta[task]=current; key=f"{task}|{step}|{site}|{branch}"; keys.append(key); task_counts[task]+=1; branch_counts[branch]+=1
            try: values=tuple(float(row[metric]) for metric in METRICS)
            except (KeyError,TypeError,ValueError) as error: raise VerificationError(f"invalid quantile at row {index}") from error
            if any(not math.isfinite(value) for value in values) or not values[0]<=values[1]<=values[2]: raise VerificationError(f"nonfinite or nonmonotone triple at row {index}")
            checked+=3; triples+=1
    if len(keys)!=336000 or len(set(keys))!=336000 or set(task_counts)!=expected_tasks or set(task_counts.values())!={2100}: raise VerificationError("injection key universe mismatch")
    if branch_counts!=Counter({"unconditional":168000,"text":168000}): raise VerificationError("branch balance mismatch")
    return header,sorted(keys),len(keys),checked,triples


def verify(authorization_path: Path,run_dir: Path) -> dict:
    try: base.ensure_cpu_offline()
    except base.VerificationError as error: raise VerificationError(str(error)) from error
    authorization=base.read_json(authorization_path)
    if authorization.get("status")!=AUTH_STATUS: raise VerificationError("audit authorization mismatch")
    if run_dir.resolve()!=Path(authorization["external_runtime"]).resolve(): raise VerificationError("audit run path mismatch")
    evidence={}
    for source_name in SOURCE_NAMES:
        source_binding=authorization["sources"][source_name]; source=Path(source_binding["path"]).resolve()
        if not source.is_file() or source.is_symlink() or source.stat().st_size!=source_binding["bytes"] or base.sha256(source)!=source_binding["sha256"]: raise VerificationError(f"source binding mismatch: {source_name}")
        root=run_dir/source_name; binding_path=root/"binding_v1.json"; summary_path=root/"audit_summary_v1.json"; keys_path=root/"keys_v1.csv"; binding=base.read_json(binding_path); summary=base.read_json(summary_path)
        if binding.get("status")!="PASS_TOKEN_QUANTILE_FORMAL_SINGLE_SOURCE_INPUT_AUDIT" or summary.get("status")!="PASS_TOKEN_QUANTILE_FORMAL_SINGLE_SOURCE_INPUT_AUDIT": raise VerificationError(f"audit status mismatch: {source_name}")
        if source_name=="injection_summaries": header,expected_keys,row_count,finite_count,triples=recompute_injection(source)
        else:
            try: header,expected_keys,row_count,finite_count=base.recompute_source(source_name,source)
            except base.VerificationError as error: raise VerificationError(str(error)) from error
            triples=0
        with keys_path.open(newline="",encoding="utf-8") as handle:
            reader=csv.DictReader(handle)
            if reader.fieldnames!=["key_index","key"]: raise VerificationError("key manifest header mismatch")
            manifest=list(reader)
        if [row["key"] for row in manifest]!=expected_keys or [int(row["key_index"]) for row in manifest]!=list(range(1,len(expected_keys)+1)): raise VerificationError(f"key manifest mismatch: {source_name}")
        if binding["path"]!=str(source) or binding["bytes"]!=source.stat().st_size or binding["sha256"]!=base.sha256(source) or binding["header"]!=header: raise VerificationError(f"binding mismatch: {source_name}")
        if binding["key_manifest"]!={"path":str(keys_path),"bytes":keys_path.stat().st_size,"sha256":base.sha256(keys_path)}: raise VerificationError(f"key binding mismatch: {source_name}")
        if summary["rows"]!=row_count or summary["unique_keys"]!=row_count or summary["finite_values_checked"]!=finite_count: raise VerificationError(f"count mismatch: {source_name}")
        if source_name=="injection_summaries" and (summary.get("quantile_triples_checked")!=triples or summary.get("nonmonotone_triples")!=0): raise VerificationError("quantile triple count mismatch")
        false_fields=("quantiles_aggregated","pair_outcome_constructed","outcome_trace_joined","association_computed","derived_quantile_metric_computed","numeric_values_exported","model_loaded","gpu_used","network_used")
        if any(summary.get(field) is not False for field in false_fields): raise VerificationError(f"forbidden action reported: {source_name}")
        evidence[source_name]={"source_rows":row_count,"finite_values_checked":finite_count,"quantile_triples_checked":triples,"binding_bytes":binding_path.stat().st_size,"binding_sha256":base.sha256(binding_path),"summary_bytes":summary_path.stat().st_size,"summary_sha256":base.sha256(summary_path),"keys_bytes":keys_path.stat().st_size,"keys_sha256":base.sha256(keys_path)}
    return {"schema_version":1,"status":"PASS_INDEPENDENT_TOKEN_QUANTILE_INPUT_AUDIT_VERIFICATION","sources_verified":3,"cross_source_numeric_comparison":False,"quantiles_aggregated":False,"outcome_constructed":False,"join_computed":False,"association_computed":False,"derived_quantile_metric_computed":False,"model_loaded":False,"gpu_used":False,"network_used":False,"evidence":evidence}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--authorization",required=True,type=Path); parser.add_argument("--run-dir",required=True,type=Path); parser.add_argument("--output",required=True,type=Path); args=parser.parse_args(); result=verify(args.authorization,args.run_dir); base.atomic_json(args.output,result); print(json.dumps(result,indent=2,sort_keys=True)); return 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except (VerificationError,base.VerificationError) as error:
        print(f"FAIL: {error}",file=sys.stderr); raise SystemExit(2)
