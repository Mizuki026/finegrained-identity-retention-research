#!/usr/bin/env python3
"""Independently verify frozen anonymous facial-hair consensus v1."""
from __future__ import annotations
import argparse,csv,hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path

EXPECTED_COMMIT="3926cb0ea65e88b52ce1a6e2d9896032f9041b9c"
ALLOWED={"0","1","2","U"}
class VError(RuntimeError): pass
def fail(x): raise VError(x)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(4<<20),b""): h.update(b)
 return h.hexdigest()
def rcsv(p):
 with p.open(newline="",encoding="utf-8-sig") as f:
  r=csv.DictReader(f); return list(r.fieldnames or []),list(r)

def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--package-dir",type=Path,required=True); p.add_argument("--consensus-dir",type=Path,required=True); p.add_argument("--verification-path",type=Path,required=True); a=p.parse_args()
 package=a.package_dir.resolve(); out=a.consensus_dir.resolve()
 if a.verification_path.exists(): fail("refusing to overwrite verification")
 expected={"anonymous_consensus_freeze_v1.json","anonymous_consensus_hashes_v1.csv","facial_hair_annotation_provenance_v1.csv","facial_hair_final_labels_v1.csv","submission_snapshot_v1"}
 if not out.is_dir() or {x.name for x in out.iterdir()}!=expected: fail("consensus file set mismatch")
 freeze=json.loads((out/"anonymous_consensus_freeze_v1.json").read_text())
 if freeze.get("status")!="FROZEN_FINAL_ANONYMOUS_CONSENSUS_READY_FOR_UNBLINDING" or freeze.get("finalization_code_commit")!=EXPECTED_COMMIT: fail("freeze status/commit mismatch")
 if freeze.get("private_mapping_accessed") is not False: fail("freeze reports private mapping access")
 _,hashes=rcsv(out/"anonymous_consensus_hashes_v1.csv")
 for r in hashes:
  q=out/r["relative_path"]
  if not q.is_file() or q.stat().st_size!=int(r["bytes"]) or sha(q)!=r["sha256"]: fail(f"hash mismatch: {q}")
 submitted=package/"adjudication_v1/facial_hair_adjudication_template_v1.csv"; snap=out/"submission_snapshot_v1/facial_hair_adjudication_submitted_v1.csv"
 if sha(submitted)!=sha(snap) or snap.stat().st_mode & 0o222: fail("adjudication snapshot mismatch/writable")
 _,adj=rcsv(snap); adj_by={r["annotation_item_id"]:r for r in adj}
 if len(adj)!=214 or len(adj_by)!=214 or any(r["adjudicated_value"] not in ALLOWED or not r["rationale"].strip() for r in adj): fail("adjudication completion mismatch")
 snapshots=package/"submission_snapshots_v1"; by={}
 for x in "AB":
  _,rows=rcsv(snapshots/f"facial_hair_annotator_{x}_submitted_v1.csv"); by[x]={r["annotation_item_id"]:r for r in rows}
  if len(by[x])!=560: fail(f"annotator {x} universe mismatch")
 _,labels=rcsv(out/"facial_hair_final_labels_v1.csv"); _,prov=rcsv(out/"facial_hair_annotation_provenance_v1.csv")
 if len(labels)!=560 or len(prov)!=560: fail("final table row mismatch")
 label_by={r["annotation_item_id"]:r for r in labels}; prov_by={r["annotation_item_id"]:r for r in prov}
 if len(label_by)!=560 or len(prov_by)!=560 or set(label_by)!=set(by["A"]) or set(prov_by)!=set(by["A"]): fail("final item universe mismatch")
 agree=adjudicated=0
 for item in sorted(by["A"]):
  l,r=by["A"][item],by["B"][item]; final=label_by[item]; q=prov_by[item]
  if l["ordinal_label"]==r["ordinal_label"]:
   expected_label=l["ordinal_label"]; source="A_B_EXACT_AGREEMENT"; expected_adj=""; expected_rat=""; agree+=1
  else:
   d=adj_by.get(item)
   if d is None: fail(f"missing adjudication: {item}")
   expected_label=d["adjudicated_value"]; source="THIRD_RESEARCHER_ADJUDICATION"; expected_adj=expected_label; expected_rat=d["rationale"].strip(); adjudicated+=1
  if final!={"annotation_item_id":item,"final_label":expected_label,"consensus_source":source}: fail(f"final label mismatch: {item}")
  expected_prov={"annotation_item_id":item,"annotator_A_label":l["ordinal_label"],"annotator_A_note":l["reason_or_note"],"annotator_B_label":r["ordinal_label"],"annotator_B_note":r["reason_or_note"],"adjudicated_value":expected_adj,"adjudication_rationale":expected_rat,"final_label":expected_label,"consensus_source":source}
  if q!=expected_prov: fail(f"provenance mismatch: {item}")
 if (agree,adjudicated)!=(346,214) or freeze["A_B_exact_agreement_items"]!=agree or freeze["third_researcher_adjudicated_items"]!=adjudicated: fail("source counts mismatch")
 report={"schema_version":1,"verification_id":"formal_facial_hair_anonymous_consensus_independent_verification_v1","verified_at_utc":datetime.now(timezone.utc).isoformat(),"consensus_dir":str(out),"finalization_code_commit":EXPECTED_COMMIT,"verification_script_sha256":sha(Path(__file__).resolve()),"total_items":560,"agreement_items":agree,"adjudicated_items":adjudicated,"all_hashes_verified":True,"all_final_labels_recomputed":True,"all_provenance_recomputed":True,"private_mapping_accessed":False,"condition_level_analysis_performed":False,"status":"PASS_INDEPENDENT_ANONYMOUS_CONSENSUS_VERIFICATION"}
 a.verification_path.parent.mkdir(parents=True,exist_ok=True)
 with a.verification_path.open("x",encoding="utf-8") as f: json.dump(report,f,indent=2,ensure_ascii=False,sort_keys=True); f.write("\n")
 print(json.dumps({"status":report["status"],"total_items":560,"verification":str(a.verification_path),"scientific_outcomes_printed":False},indent=2))
if __name__=="__main__":
 try: main()
 except VError as e: raise SystemExit(f"ANONYMOUS CONSENSUS VERIFICATION FAILED: {e}")
