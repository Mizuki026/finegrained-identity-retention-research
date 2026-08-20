#!/usr/bin/env python3
"""Independent verifier for the formal facial-hair adjudication package.

No private mapping, model, video, condition, identity, seed, or pair metadata is
read. The verifier recomputes submission validation and disagreement routing,
checks all package hashes, and writes one report outside the package.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_PREPARATION_COMMIT = "7d0035a24feaf296424f068361550f842e52d148"
SEED = "formal_facial_hair_adjudication_v1_seed_20260820"
ALLOWED = {"0", "1", "2", "U"}


class VerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerificationError(message)


def sha256_path(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(4<<20),b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str,str]]]:
    with path.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        return list(reader.fieldnames or []),list(reader)


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir",type=Path,required=True)
    p.add_argument("--package-dir",type=Path,required=True)
    p.add_argument("--verification-path",type=Path,required=True)
    args=p.parse_args()
    run=args.run_dir.resolve(); package=args.package_dir.resolve()
    if args.verification_path.exists(): fail("refusing to overwrite verification")
    expected_top={
        "adjudication_v1","agreed_items_pre_adjudication_v1.csv",
        "annotation_handoff_audit_v1.json","annotation_handoff_hashes_v1.csv",
        "interannotator_agreement_v1.json","submission_snapshots_v1",
    }
    if not package.is_dir() or {x.name for x in package.iterdir()}!=expected_top:
        fail("package top-level file set mismatch")
    audit=json.loads((package/"annotation_handoff_audit_v1.json").read_text())
    agreement=json.loads((package/"interannotator_agreement_v1.json").read_text())
    if audit.get("status")!="SUBMISSIONS_FROZEN_ADJUDICATION_PACKAGE_READY":
        fail("handoff audit status mismatch")
    if audit.get("preparation_code_commit")!=EXPECTED_PREPARATION_COMMIT:
        fail("preparation code commit mismatch")
    if audit.get("private_mapping_accessed") is not False:
        fail("handoff reports private mapping access")
    if agreement.get("condition_level_analysis_performed") is not False:
        fail("agreement report indicates condition analysis")

    source={a:run/f"facial_hair_annotation_materials_v1/annotator_{a}/facial_hair_annotator_{a}_v1.csv" for a in "AB"}
    snap={a:package/f"submission_snapshots_v1/facial_hair_annotator_{a}_submitted_v1.csv" for a in "AB"}
    rows={}; by_id={}
    expected_header=["annotator_id","annotation_item_id","random_order","ordinal_label","reason_or_note"]
    crop_ids={x.stem for x in (run/"facial_hair_blinded_crops_v1").glob("*.jpg")}
    if len(crop_ids)!=560: fail("crop universe mismatch")
    for a in "AB":
        if sha256_path(source[a])!=sha256_path(snap[a]) or sha256_path(snap[a])!=audit["submission_sha256"][a]:
            fail(f"annotator {a} source/snapshot/hash mismatch")
        if snap[a].stat().st_mode & 0o222:
            fail(f"annotator {a} snapshot is writable")
        header,data=read_csv(snap[a]); rows[a]=data
        if header!=expected_header or len(data)!=560:
            fail(f"annotator {a} schema/row mismatch")
        if [int(x["random_order"]) for x in data]!=list(range(1,561)):
            fail(f"annotator {a} order mismatch")
        if any(x["annotator_id"]!=a or x["ordinal_label"] not in ALLOWED for x in data):
            fail(f"annotator {a} identifier/label mismatch")
        by_id[a]={x["annotation_item_id"]:x for x in data}
        if len(by_id[a])!=560 or set(by_id[a])!=crop_ids:
            fail(f"annotator {a} item universe mismatch")
    if [x["annotation_item_id"] for x in rows["A"]]==[x["annotation_item_id"] for x in rows["B"]]:
        fail("A/B orders unexpectedly identical")

    agreements=[]; disagreements=[]
    for item in sorted(crop_ids):
        left,right=by_id["A"][item],by_id["B"][item]
        if left["ordinal_label"]==right["ordinal_label"]:
            agreements.append((item,left["ordinal_label"]))
        else:
            disagreements.append((item,left,right))
    _,agreed_rows=read_csv(package/"agreed_items_pre_adjudication_v1.csv")
    observed_agreed=[(x["annotation_item_id"],x["consensus_label"]) for x in agreed_rows]
    if observed_agreed!=agreements or any(x["consensus_source"]!="A_B_EXACT_AGREEMENT" for x in agreed_rows):
        fail("agreed-item routing mismatch")
    expected_random=sorted(disagreements,key=lambda x:hashlib.sha256(f"{SEED}|order|{x[0]}".encode()).hexdigest())
    adj_path=package/"adjudication_v1/facial_hair_adjudication_template_v1.csv"
    header,adj=read_csv(adj_path)
    expected_adj_header=["adjudication_id","annotation_item_id","option_1","option_2","note_1","note_2","allowed_values","adjudicated_value","rationale"]
    if header!=expected_adj_header or len(adj)!=len(disagreements):
        fail("adjudication schema/row mismatch")
    if [x["annotation_item_id"] for x in adj]!=[x[0] for x in expected_random]:
        fail("adjudication deterministic random order mismatch")
    for index,(observed,(item,left,right)) in enumerate(zip(adj,expected_random),1):
        if observed["adjudication_id"]!=f"FADJ_{index:03d}" or observed["allowed_values"]!="0|1|2|U":
            fail("adjudication identifier/allowed-values mismatch")
        if observed["adjudicated_value"] or observed["rationale"]:
            fail("adjudication decision columns are not blank")
        pairs={(left["ordinal_label"],left["reason_or_note"]),(right["ordinal_label"],right["reason_or_note"])}
        if {(observed["option_1"],observed["note_1"]),(observed["option_2"],observed["note_2"])}!=pairs:
            fail(f"option/note association mismatch: {item}")
    pages=list((package/"adjudication_v1/contact_sheets").glob("*.png"))
    if len(pages)!=math.ceil(len(disagreements)/20) or any(x.stat().st_size<=0 for x in pages):
        fail("adjudication contact-sheet page mismatch")

    _,hashes=read_csv(package/"annotation_handoff_hashes_v1.csv")
    if len({x["relative_path"] for x in hashes})!=len(hashes): fail("duplicate hash paths")
    for row in hashes:
        path=package/row["relative_path"]
        if not path.is_file() or path.stat().st_size!=int(row["bytes"]) or sha256_path(path)!=row["sha256"]:
            fail(f"hash verification failed: {path}")
    if audit["exact_agreement_count"]!=len(agreements) or audit["disagreement_count"]!=len(disagreements):
        fail("handoff count mismatch")
    if agreement["exact_agreement_count"]!=len(agreements) or agreement["disagreement_count"]!=len(disagreements):
        fail("agreement report count mismatch")

    report={
        "schema_version":1,
        "verification_id":"formal_facial_hair_adjudication_package_independent_verification_v1",
        "verified_at_utc":datetime.now(timezone.utc).isoformat(),
        "package_dir":str(package),
        "preparation_code_commit":EXPECTED_PREPARATION_COMMIT,
        "verification_script_sha256":sha256_path(Path(__file__).resolve()),
        "submission_rows":{"A":560,"B":560},
        "agreement_items":len(agreements),
        "adjudication_items":len(disagreements),
        "contact_sheet_pages":len(pages),
        "all_listed_hashes_verified":True,
        "all_disagreements_routed_once":True,
        "all_agreements_excluded_from_adjudication":True,
        "all_option_note_associations_verified":True,
        "adjudication_columns_blank":True,
        "private_mapping_accessed":False,
        "condition_level_analysis_performed":False,
        "status":"PASS_INDEPENDENT_ADJUDICATION_PACKAGE_VERIFICATION",
    }
    args.verification_path.parent.mkdir(parents=True,exist_ok=True)
    with args.verification_path.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False,sort_keys=True); f.write("\n")
    print(json.dumps({"status":report["status"],"adjudication_items":len(disagreements),"verification":str(args.verification_path),"scientific_outcomes_printed":False},indent=2))


if __name__=="__main__":
    try: main()
    except VerificationError as exc: raise SystemExit(f"ADJUDICATION PACKAGE VERIFICATION FAILED: {exc}")
