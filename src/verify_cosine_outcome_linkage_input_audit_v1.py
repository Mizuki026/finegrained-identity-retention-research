#!/usr/bin/env python3
"""Independent CPU-only verifier for cosine-linkage input-audit run v1."""
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


AUTH_STATUS="CPU_ONLY_COSINE_LINKAGE_FORMAL_INPUT_AUDIT_APPROVED"
SOURCE_NAMES=("eyeglasses_outcome","facial_hair_outcome","injection_summaries")
SEEDS={1:"2686238281",2:"280026145",3:"2169901996",4:"2046930553"}


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
    if path.exists() or temporary.exists(): raise VerificationError("refusing to overwrite verification")
    with temporary.open("x",encoding="utf-8") as handle: json.dump(value,handle,indent=2,sort_keys=True); handle.write("\n")
    temporary.replace(path)


def ensure_cpu_offline() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES")!="": raise VerificationError("CUDA_VISIBLE_DEVICES must be empty")
    if os.environ.get("HF_HUB_OFFLINE")!="1" or os.environ.get("TRANSFORMERS_OFFLINE")!="1": raise VerificationError("offline flags must be 1")
    forbidden=("torch","transformers","diffusers","consisid")
    if any(any(name==prefix or name.startswith(prefix+".") for prefix in forbidden) for name in sys.modules): raise VerificationError("forbidden ML module imported")


def pairs(attribute: str) -> tuple[str,...]:
    prefix="FEY" if attribute=="eyeglasses" else "FFH"
    return tuple(f"{prefix}_{index:02d}" for index in range(1,11))


def finite(value: str,context: str) -> None:
    try: number=float(value)
    except (TypeError,ValueError) as error: raise VerificationError(f"invalid numeric at {context}") from error
    if not math.isfinite(number): raise VerificationError(f"non-finite numeric at {context}")


def recompute_source(source_name: str,path: Path) -> tuple[list[str],list[str],int,int]:
    keys=[]; checked=0
    with path.open(newline="",encoding="utf-8") as handle:
        reader=csv.DictReader(handle); header=list(reader.fieldnames or [])
        if source_name=="eyeglasses_outcome":
            for index,row in enumerate(reader,1):
                keys.append(f"{row['formal_pair_id']}|{row['seed_index']}"); finite(row["human_positive_minus_control"],f"eye/{index}"); checked+=1
            expected={f"{pair}|{seed}" for pair in pairs("eyeglasses") for seed in range(1,5)}
            if len(keys)!=40 or len(set(keys))!=40 or set(keys)!=expected: raise VerificationError("eye key universe mismatch")
        elif source_name=="facial_hair_outcome":
            for index,row in enumerate(reader,1):
                keys.append(f"{row['attribute']}|{row['formal_pair_id']}")
                if row["attribute"]=="facial_hair": finite(row["primary_positive_minus_control"],f"hair/{index}"); checked+=1
            expected={f"{attribute}|{pair}" for attribute in ("eyeglasses","facial_hair") for pair in pairs(attribute)}
            if len(keys)!=20 or len(set(keys))!=20 or set(keys)!=expected or checked!=10: raise VerificationError("hair key universe mismatch")
        else:
            task_counts=Counter(); branch_counts=Counter(); task_meta={}
            expected_tasks=set()
            for attribute in ("eyeglasses","facial_hair"):
                for pair in pairs(attribute):
                    for role in ("positive","control"):
                        unit=f"{pair}_{role}"
                        for seed_index,seed in SEEDS.items(): expected_tasks.add(f"S__{unit}__s{seed_index}__baseline__r1")
            for index,row in enumerate(reader,1):
                task=row["trace_task_id"]
                if task not in expected_tasks: raise VerificationError(f"unexpected task at {index}")
                step,site=int(row["step_index"]),int(row["site_index"]); branch=row["cfg_branch"]
                if step not in range(50) or site not in range(21) or branch not in ("unconditional","text"): raise VerificationError(f"position drift at {index}")
                if row["phase"]!="scientific" or row["condition"]!="baseline" or row["repetition"]!="1": raise VerificationError(f"condition drift at {index}")
                current=(row["formal_unit_id"],row["formal_pair_id"],row["attribute"],row["role"],row["seed_index"],row["seed"])
                if task in task_meta and task_meta[task]!=current: raise VerificationError(f"metadata drift at {index}")
                task_meta[task]=current
                keys.append(f"{task}|{step}|{site}|{branch}"); task_counts[task]+=1; branch_counts[branch]+=1
                finite(row["mean_tokenwise_cosine_h_r"],f"injection/{index}"); checked+=1
            if len(keys)!=336000 or len(set(keys))!=336000 or set(task_counts)!=expected_tasks or set(task_counts.values())!={2100}: raise VerificationError("injection key universe mismatch")
            if branch_counts!=Counter({"unconditional":168000,"text":168000}): raise VerificationError("branch balance mismatch")
    return header,sorted(keys),len(keys),checked


def verify(authorization_path: Path,run_dir: Path) -> dict:
    ensure_cpu_offline(); authorization=read_json(authorization_path)
    if authorization.get("status")!=AUTH_STATUS: raise VerificationError("audit authorization status mismatch")
    if run_dir.resolve()!=Path(authorization["external_runtime"]).resolve(): raise VerificationError("audit run path mismatch")
    evidence={}
    for source_name in SOURCE_NAMES:
        source_binding=authorization["sources"][source_name]; source=Path(source_binding["path"]).resolve()
        if not source.is_file() or source.is_symlink() or source.stat().st_size!=source_binding["bytes"] or sha256(source)!=source_binding["sha256"]: raise VerificationError(f"source binding mismatch: {source_name}")
        root=run_dir/source_name; binding_path=root/"binding_v1.json"; summary_path=root/"audit_summary_v1.json"; keys_path=root/"keys_v1.csv"
        binding=read_json(binding_path); summary=read_json(summary_path)
        if binding.get("status")!="PASS_COSINE_LINKAGE_FORMAL_SINGLE_SOURCE_INPUT_AUDIT" or summary.get("status")!="PASS_COSINE_LINKAGE_FORMAL_SINGLE_SOURCE_INPUT_AUDIT": raise VerificationError(f"audit status mismatch: {source_name}")
        header,expected_keys,row_count,finite_count=recompute_source(source_name,source)
        with keys_path.open(newline="",encoding="utf-8") as handle:
            reader=csv.DictReader(handle)
            if reader.fieldnames!=["key_index","key"]: raise VerificationError("key-manifest header mismatch")
            manifest_rows=list(reader)
        actual_keys=[row["key"] for row in manifest_rows]
        if actual_keys!=expected_keys or [int(row["key_index"]) for row in manifest_rows]!=list(range(1,len(expected_keys)+1)): raise VerificationError(f"key manifest mismatch: {source_name}")
        if binding["path"]!=str(source) or binding["bytes"]!=source.stat().st_size or binding["sha256"]!=sha256(source) or binding["header"]!=header: raise VerificationError(f"binding content mismatch: {source_name}")
        if binding["key_manifest"]!={"path":str(keys_path),"bytes":keys_path.stat().st_size,"sha256":sha256(keys_path)}: raise VerificationError(f"key binding mismatch: {source_name}")
        if summary["rows"]!=row_count or summary["unique_keys"]!=row_count or summary["finite_values_checked"]!=finite_count: raise VerificationError(f"audit counts mismatch: {source_name}")
        false_fields=("cosine_aggregated","pair_outcome_constructed","outcome_trace_joined","association_computed","numeric_values_exported","model_loaded","gpu_used","network_used")
        if any(summary.get(field) is not False for field in false_fields): raise VerificationError(f"forbidden action reported: {source_name}")
        evidence[source_name]={"source_rows":row_count,"finite_values_checked":finite_count,"binding_bytes":binding_path.stat().st_size,"binding_sha256":sha256(binding_path),"summary_bytes":summary_path.stat().st_size,"summary_sha256":sha256(summary_path),"keys_bytes":keys_path.stat().st_size,"keys_sha256":sha256(keys_path)}
    return {"schema_version":1,"status":"PASS_INDEPENDENT_COSINE_LINKAGE_INPUT_AUDIT_VERIFICATION","sources_verified":3,"cross_source_numeric_comparison":False,"cosine_aggregated":False,"outcome_constructed":False,"join_computed":False,"association_computed":False,"model_loaded":False,"gpu_used":False,"network_used":False,"evidence":evidence}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--authorization",required=True,type=Path); parser.add_argument("--run-dir",required=True,type=Path); parser.add_argument("--output",required=True,type=Path); args=parser.parse_args()
    result=verify(args.authorization,args.run_dir); atomic_json(args.output,result); print(json.dumps(result,indent=2,sort_keys=True)); return 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except VerificationError as error:
        print(f"FAIL: {error}",file=sys.stderr); raise SystemExit(2)
