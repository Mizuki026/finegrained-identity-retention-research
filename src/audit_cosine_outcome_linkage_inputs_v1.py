#!/usr/bin/env python3
"""CPU-only one-source-at-a-time formal input audit for cosine linkage v1."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import stat
import sys
from collections import Counter
from pathlib import Path


AUTH_STATUS = "CPU_ONLY_COSINE_LINKAGE_FORMAL_INPUT_AUDIT_APPROVED"
SOURCE_NAMES = ("eyeglasses_outcome", "facial_hair_outcome", "injection_summaries")
ATTRIBUTES = ("eyeglasses", "facial_hair")
BRANCHES = ("unconditional", "text")
SEEDS = {1: "2686238281", 2: "280026145", 3: "2169901996", 4: "2046930553"}
EYE_HEADER = ["schema_version","formal_pair_id","seed_index","positive_task_id","control_task_id","positive_human_present_fraction","control_human_present_fraction","human_positive_minus_control","positive_automated_mean_p_present","control_automated_mean_p_present","automated_positive_minus_control","record_status"]
HAIR_HEADER = ["schema_version","formal_pair_id","attribute","positive_unit_id","control_unit_id","positive_primary_score","control_primary_score","primary_positive_minus_control","positive_valid_frame_fraction","control_valid_frame_fraction","positive_low_coverage_flag","control_low_coverage_flag","pair_status"]
INJECTION_HEADER = ["trace_task_id","phase","formal_unit_id","formal_pair_id","attribute","role","seed_index","seed","condition","repetition","step_index","scheduler_timestep","site_index","block_index","cfg_branch","local_face_scale","rms_post","rms_h","rms_r","relative_residual_rms","mean_tokenwise_cosine_h_r","token_rms_r_q10","token_rms_r_q50","token_rms_r_q90"] + [f"frame_rms_r_{index:02d}" for index in range(13)]


class AuditError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise AuditError("authorization must be a JSON object")
    return value


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise AuditError(f"refusing to overwrite: {path}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def atomic_keys(path: Path, keys: list[str]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise AuditError(f"refusing to overwrite: {path}")
    with temporary.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("key_index", "key"))
        for index, key in enumerate(keys, 1):
            writer.writerow((index, key))
    temporary.replace(path)


def ensure_cpu_offline() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise AuditError("CUDA_VISIBLE_DEVICES must be explicitly empty")
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        if os.environ.get(name) != "1":
            raise AuditError(f"{name} must be 1")
    forbidden = ("torch", "transformers", "diffusers", "consisid")
    if any(any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden) for name in sys.modules):
        raise AuditError("forbidden ML module imported")


def pair_ids(attribute: str) -> tuple[str, ...]:
    prefix = "FEY" if attribute == "eyeglasses" else "FFH"
    return tuple(f"{prefix}_{index:02d}" for index in range(1, 11))


def finite(value: str, context: str) -> None:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise AuditError(f"invalid numeric value at {context}") from error
    if not math.isfinite(number):
        raise AuditError(f"non-finite numeric value at {context}")


def audit_eye(path: Path) -> tuple[list[str], list[str], dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EYE_HEADER:
            raise AuditError("eyeglasses header mismatch")
        rows = list(reader)
    expected = {f"{pair}|{seed}" for pair in pair_ids("eyeglasses") for seed in range(1, 5)}
    keys=[]
    for index,row in enumerate(rows,1):
        key=f"{row['formal_pair_id']}|{row['seed_index']}"; keys.append(key)
        finite(row["human_positive_minus_control"],f"eye row {index}")
    if len(rows)!=40 or len(keys)!=len(set(keys)) or set(keys)!=expected:
        raise AuditError("eyeglasses exact key universe mismatch")
    return EYE_HEADER,sorted(keys),{"rows":40,"unique_keys":40,"finite_values_checked":40,"key_columns":["formal_pair_id","seed_index"]}


def audit_hair(path: Path) -> tuple[list[str], list[str], dict]:
    with path.open(newline="",encoding="utf-8") as handle:
        reader=csv.DictReader(handle)
        if reader.fieldnames!=HAIR_HEADER: raise AuditError("facial-hair header mismatch")
        rows=list(reader)
    expected={f"{attribute}|{pair}" for attribute in ATTRIBUTES for pair in pair_ids(attribute)}
    keys=[]; checked=0
    for index,row in enumerate(rows,1):
        key=f"{row['attribute']}|{row['formal_pair_id']}"; keys.append(key)
        if row["attribute"]=="facial_hair": finite(row["primary_positive_minus_control"],f"hair row {index}"); checked+=1
    if len(rows)!=20 or len(keys)!=len(set(keys)) or set(keys)!=expected or checked!=10:
        raise AuditError("facial-hair exact key universe mismatch")
    return HAIR_HEADER,sorted(keys),{"rows":20,"unique_keys":20,"finite_values_checked":10,"target_scope":"facial_hair_rows_only","key_columns":["attribute","formal_pair_id"]}


def expected_tasks() -> dict[str, tuple[str,str,str,int,str,str]]:
    result={}
    for attribute in ATTRIBUTES:
        for pair in pair_ids(attribute):
            for role in ("positive","control"):
                unit=f"{pair}_{role}"
                for seed_index,seed in SEEDS.items():
                    task=f"S__{unit}__s{seed_index}__baseline__r1"
                    result[task]=(attribute,pair,role,seed_index,seed,unit)
    return result


def audit_injection(path: Path) -> tuple[list[str], list[str], dict]:
    tasks_expected=expected_tasks(); task_counts=Counter(); branch_counts=Counter(); keys=[]; seen=set(); checked=0
    with path.open(newline="",encoding="utf-8") as handle:
        reader=csv.DictReader(handle)
        if reader.fieldnames!=INJECTION_HEADER: raise AuditError("injection header mismatch")
        for index,row in enumerate(reader,1):
            task=row["trace_task_id"]
            if task not in tasks_expected: raise AuditError(f"unexpected trace task at row {index}")
            attribute,pair,role,seed_index,seed,unit=tasks_expected[task]
            if (row["attribute"],row["formal_pair_id"],row["role"],row["seed_index"],row["seed"],row["formal_unit_id"])!=(attribute,pair,role,str(seed_index),seed,unit):
                raise AuditError(f"task metadata mismatch at row {index}")
            if row["phase"]!="scientific" or row["condition"]!="baseline" or row["repetition"]!="1" or row["local_face_scale"]!="1.0":
                raise AuditError(f"condition metadata mismatch at row {index}")
            step,site=int(row["step_index"]),int(row["site_index"]); branch=row["cfg_branch"]
            if step not in range(50) or site not in range(21) or branch not in BRANCHES:
                raise AuditError(f"position domain mismatch at row {index}")
            key=f"{task}|{step}|{site}|{branch}"
            if key in seen: raise AuditError(f"duplicate position key at row {index}")
            seen.add(key); keys.append(key); task_counts[task]+=1; branch_counts[branch]+=1
            finite(row["mean_tokenwise_cosine_h_r"],f"injection row {index}"); checked+=1
    if len(keys)!=336000 or set(task_counts)!=set(tasks_expected) or set(task_counts.values())!={2100}:
        raise AuditError("injection row/task count mismatch")
    if branch_counts!=Counter({"unconditional":168000,"text":168000}):
        raise AuditError("injection branch balance mismatch")
    return INJECTION_HEADER,sorted(keys),{"rows":336000,"unique_keys":336000,"finite_values_checked":checked,"trace_tasks":160,"rows_per_task":2100,"key_columns":["trace_task_id","step_index","site_index","cfg_branch"]}


def audit(authorization_path: Path, source_name: str, output_dir: Path) -> dict:
    ensure_cpu_offline()
    authorization=read_json(authorization_path)
    if authorization.get("status")!=AUTH_STATUS: raise AuditError("formal input audit is not authorized")
    if source_name not in SOURCE_NAMES: raise AuditError("source outside authorized universe")
    forbidden=("cosine_aggregation","pair_outcome_construction","outcome_trace_join","spearman_or_other_association","cross_source_value_comparison","model_loading","gpu_execution","network_access")
    if any(authorization.get("not_authorized",{}).get(name) is not True for name in forbidden):
        raise AuditError("authorization does not explicitly forbid every disallowed operation")
    expected_output=Path(authorization["external_runtime"]).resolve()/source_name
    if output_dir.resolve()!=expected_output or output_dir.exists(): raise AuditError("output mismatch or overwrite attempt")
    binding=authorization["sources"][source_name]; source_path=Path(binding["path"]).resolve()
    if not source_path.is_file() or source_path.is_symlink(): raise AuditError("invalid source path")
    if source_path.stat().st_size!=binding["bytes"] or sha256(source_path)!=binding["sha256"]: raise AuditError("source byte or SHA256 mismatch")
    if source_name=="eyeglasses_outcome": header,keys,counts=audit_eye(source_path)
    elif source_name=="facial_hair_outcome": header,keys,counts=audit_hair(source_path)
    else: header,keys,counts=audit_injection(source_path)
    output_dir.mkdir(parents=True,exist_ok=False)
    key_path=output_dir/"keys_v1.csv"; atomic_keys(key_path,keys)
    record={"schema_version":1,"status":"PASS_COSINE_LINKAGE_FORMAL_SINGLE_SOURCE_INPUT_AUDIT","source_name":source_name,"path":str(source_path),"bytes":source_path.stat().st_size,"sha256":sha256(source_path),"mode":format(stat.S_IMODE(source_path.stat().st_mode),"03o"),"header":header,"key_columns":counts["key_columns"],"expected_rows":counts["rows"],"expected_unique_keys":counts["unique_keys"],"key_manifest":{"path":str(key_path),"bytes":key_path.stat().st_size,"sha256":sha256(key_path)},"numeric_values_exported":False,"source_modified":False}
    binding_path=output_dir/"binding_v1.json"; atomic_json(binding_path,record)
    summary={"schema_version":1,"status":"PASS_COSINE_LINKAGE_FORMAL_SINGLE_SOURCE_INPUT_AUDIT","source_name":source_name,"source_path":str(source_path),"source_bytes":source_path.stat().st_size,"source_sha256":sha256(source_path),**{k:v for k,v in counts.items() if k!="key_columns"},"duplicate_keys":0,"missing_required_fields":0,"nonfinite_values":0,"exact_planned_key_universe":True,"keys_manifest_bytes":key_path.stat().st_size,"keys_manifest_sha256":sha256(key_path),"binding_bytes":binding_path.stat().st_size,"binding_sha256":sha256(binding_path),"other_sources_opened":0,"cosine_aggregated":False,"pair_outcome_constructed":False,"outcome_trace_joined":False,"association_computed":False,"numeric_values_exported":False,"model_loaded":False,"gpu_used":False,"network_used":False}
    atomic_json(output_dir/"audit_summary_v1.json",summary)
    return summary


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--authorization",required=True,type=Path); parser.add_argument("--source-name",required=True,choices=SOURCE_NAMES); parser.add_argument("--output-dir",required=True,type=Path); args=parser.parse_args()
    print(json.dumps(audit(args.authorization,args.source_name,args.output_dir),indent=2,sort_keys=True)); return 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except AuditError as error:
        print(f"FAIL: {error}",file=sys.stderr); raise SystemExit(2)
