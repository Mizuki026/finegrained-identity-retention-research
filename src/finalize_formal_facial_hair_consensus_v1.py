#!/usr/bin/env python3
"""Validate, snapshot, and freeze formal anonymous facial-hair consensus.

The finalizer reconstructs the frozen adjudication template from the two
read-only anonymous snapshots and the frozen randomization seed. It verifies
that only decision columns were filled, then emits complete anonymous consensus
and provenance tables. It never accesses the private mapping or conditions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ALLOWED={"0","1","2","U"}
SEED="formal_facial_hair_adjudication_v1_seed_20260820"
ADJ_HEADER=["adjudication_id","annotation_item_id","option_1","option_2","note_1","note_2","allowed_values","adjudicated_value","rationale"]


class FinalizationError(RuntimeError): pass

def fail(message:str)->None: raise FinalizationError(message)

def sha256_path(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(4<<20),b""): h.update(block)
    return h.hexdigest()

def read_csv(path:Path)->tuple[list[str],list[dict[str,str]]]:
    with path.open(newline="",encoding="utf-8-sig") as f:
        r=csv.DictReader(f); return list(r.fieldnames or []),list(r)

def write_csv(path:Path,fields:list[str],rows:list[dict])->None:
    with path.open("x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="raise"); w.writeheader(); w.writerows(rows)

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package-dir",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args(); package=args.package_dir.resolve(); output=args.output_dir.resolve()
    temp=output.with_name(output.name+".inprogress")
    if output.exists() or temp.exists(): fail(f"refusing to overwrite output: {output}")
    temp.mkdir(parents=True,exist_ok=False)
    snapshots=package/"submission_snapshots_v1"
    handoff=json.loads((package/"annotation_handoff_audit_v1.json").read_text())
    rows={}; by_id={}
    for a in "AB":
        path=snapshots/f"facial_hair_annotator_{a}_submitted_v1.csv"
        if sha256_path(path)!=handoff["submission_sha256"][a]: fail(f"annotator {a} snapshot hash mismatch")
        if path.stat().st_mode & 0o222: fail(f"annotator {a} snapshot writable")
        _,data=read_csv(path); rows[a]=data; by_id[a]={x["annotation_item_id"]:x for x in data}
        if len(data)!=560 or len(by_id[a])!=560: fail(f"annotator {a} universe mismatch")
    if set(by_id["A"])!=set(by_id["B"]): fail("A/B item universes differ")
    agreements=[]; disagreements=[]
    for item in sorted(by_id["A"]):
        left,right=by_id["A"][item],by_id["B"][item]
        if left["ordinal_label"]==right["ordinal_label"]: agreements.append((item,left,right))
        else: disagreements.append((item,left,right))
    expected_random=sorted(disagreements,key=lambda x:hashlib.sha256(f"{SEED}|order|{x[0]}".encode()).hexdigest())
    submitted_path=package/"adjudication_v1/facial_hair_adjudication_template_v1.csv"
    header,submitted=read_csv(submitted_path)
    if header!=ADJ_HEADER or len(submitted)!=len(expected_random): fail("submitted adjudication schema/count mismatch")
    submitted_by_item={x["annotation_item_id"]:x for x in submitted}
    if len(submitted_by_item)!=len(submitted): fail("duplicate adjudication item IDs")
    for index,(observed,(item,left,right)) in enumerate(zip(submitted,expected_random),1):
        swap=int(hashlib.sha256(f"{SEED}|swap|{item}".encode()).hexdigest(),16)%2
        first,second=(right,left) if swap else (left,right)
        expected={
            "adjudication_id":f"FADJ_{index:03d}","annotation_item_id":item,
            "option_1":first["ordinal_label"],"option_2":second["ordinal_label"],
            "note_1":first["reason_or_note"],"note_2":second["reason_or_note"],
            "allowed_values":"0|1|2|U",
        }
        for key,value in expected.items():
            if observed[key]!=value: fail(f"frozen adjudication field changed: {item} {key}")
        observed["adjudicated_value"]=observed["adjudicated_value"].strip()
        observed["rationale"]=observed["rationale"].strip()
        if observed["adjudicated_value"] not in ALLOWED: fail(f"invalid/blank adjudication value: {item}")
        if not observed["rationale"]: fail(f"blank adjudication rationale: {item}")
    if set(submitted_by_item)!={x[0] for x in disagreements}: fail("adjudication item universe mismatch")

    snapdir=temp/"submission_snapshot_v1"; snapdir.mkdir()
    target=snapdir/"facial_hair_adjudication_submitted_v1.csv"
    shutil.copyfile(submitted_path,target); os.chmod(target,0o444)
    if sha256_path(target)!=sha256_path(submitted_path): fail("adjudication snapshot byte mismatch")

    labels=[]; provenance=[]
    for item in sorted(by_id["A"]):
        left,right=by_id["A"][item],by_id["B"][item]
        if left["ordinal_label"]==right["ordinal_label"]:
            final=left["ordinal_label"]; source="A_B_EXACT_AGREEMENT"; adj=""; rationale=""
        else:
            decision=submitted_by_item[item]
            final=decision["adjudicated_value"]; source="THIRD_RESEARCHER_ADJUDICATION"
            adj=final; rationale=decision["rationale"]
        labels.append({"annotation_item_id":item,"final_label":final,"consensus_source":source})
        provenance.append({
            "annotation_item_id":item,
            "annotator_A_label":left["ordinal_label"],"annotator_A_note":left["reason_or_note"],
            "annotator_B_label":right["ordinal_label"],"annotator_B_note":right["reason_or_note"],
            "adjudicated_value":adj,"adjudication_rationale":rationale,
            "final_label":final,"consensus_source":source,
        })
    write_csv(temp/"facial_hair_final_labels_v1.csv",["annotation_item_id","final_label","consensus_source"],labels)
    write_csv(temp/"facial_hair_annotation_provenance_v1.csv",["annotation_item_id","annotator_A_label","annotator_A_note","annotator_B_label","annotator_B_note","adjudicated_value","adjudication_rationale","final_label","consensus_source"],provenance)
    commit=subprocess.check_output(["git","-C",str(Path(__file__).resolve().parents[1]),"rev-parse","HEAD"],text=True).strip()
    audit={
        "schema_version":1,"audit_id":"formal_facial_hair_anonymous_consensus_freeze_v1",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "package_dir":str(package),"output_dir":str(output),
        "finalization_code_commit":commit,"finalization_script_sha256":sha256_path(Path(__file__).resolve()),
        "annotator_submission_sha256":handoff["submission_sha256"],
        "adjudication_submission_sha256":sha256_path(target),
        "total_items":len(labels),"A_B_exact_agreement_items":len(agreements),
        "third_researcher_adjudicated_items":len(disagreements),
        "all_adjudication_values_complete":True,"all_adjudication_rationales_complete":True,
        "all_notes_and_rationales_preserved":True,"private_mapping_accessed":False,
        "condition_level_analysis_performed":False,
        "status":"FROZEN_FINAL_ANONYMOUS_CONSENSUS_READY_FOR_UNBLINDING",
    }
    (temp/"anonymous_consensus_freeze_v1.json").write_text(json.dumps(audit,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    hashes=[]
    for path in sorted(x for x in temp.rglob("*") if x.is_file()):
        if path.name=="anonymous_consensus_hashes_v1.csv": continue
        hashes.append({"relative_path":str(path.relative_to(temp)),"bytes":path.stat().st_size,"sha256":sha256_path(path)})
    write_csv(temp/"anonymous_consensus_hashes_v1.csv",["relative_path","bytes","sha256"],hashes)
    temp.rename(output)
    print(json.dumps({"status":audit["status"],"total_items":len(labels),"agreement_items":len(agreements),"adjudicated_items":len(disagreements),"private_mapping_accessed":False,"scientific_outcomes_printed":False},indent=2))

if __name__=="__main__":
    try: main()
    except FinalizationError as exc: raise SystemExit(f"CONSENSUS FINALIZATION FAILED: {exc}")
