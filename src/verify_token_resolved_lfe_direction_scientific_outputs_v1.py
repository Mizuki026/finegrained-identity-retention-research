#!/usr/bin/env python3
"""Independent persisted-output verifier for token-direction scientific v1."""
from __future__ import annotations
import argparse,json,math,statistics,sys
from collections import Counter,defaultdict
from pathlib import Path
import token_resolved_lfe_direction_protocol_v1 as protocol

class PersistedVerificationError(RuntimeError): pass
def finite(raw):
    value=float(raw)
    if not math.isfinite(value): raise PersistedVerificationError("nonfinite value")
    return value
def rows(path,count):
    result=protocol.read_csv(path)
    if len(result)!=count: raise PersistedVerificationError(f"row count mismatch: {path.name}")
    return result
def verify(run_dir:Path,output:Path)->dict:
    margins=rows(run_dir/"lfe_token_margins_v1.csv",640); panels=rows(run_dir/"lfe_token_finite_panel_v1.csv",64)
    signs=rows(run_dir/"lfe_pair_token_signs_v1.csv",20); pooled=rows(run_dir/"pooled_lfe_replication_v1.csv",20)
    status=rows(run_dir/"scientific_extraction_status_v1.csv",160)
    if len({r["reference_task_id"] for r in status})!=160 or any(r["status"]!="COMPLETE_TRANSIENT_ONLY" for r in status): raise PersistedVerificationError("extraction status drift")
    keys={(r["attribute"],int(r["token_index"]),r["formal_pair_id"]) for r in margins}
    if len(keys)!=640: raise PersistedVerificationError("margin key duplication")
    by_token=defaultdict(list); by_pair=defaultdict(list)
    for r in margins:
        value=finite(r["margin"]); expected="tie" if abs(value)<=protocol.TIE_THRESHOLD else ("correct" if value>0 else "wrong")
        if r["direction"]!=expected: raise PersistedVerificationError("margin label mismatch")
        by_token[(r["attribute"],int(r["token_index"]))].append((value,expected)); by_pair[(r["attribute"],r["formal_pair_id"])].append((value,expected))
    def check_summary(row,selected,expected_n):
        if len(selected)!=expected_n: raise PersistedVerificationError("summary family incomplete")
        values=[x[0] for x in selected]; counts=Counter(x[1] for x in selected)
        if tuple(int(row[x]) for x in ("correct_count","tie_count","wrong_count"))!=(counts["correct"],counts["tie"],counts["wrong"]): raise PersistedVerificationError("summary counts mismatch")
        expected=(statistics.fmean(values),statistics.median(values),min(values),max(values))
        observed=tuple(finite(row[x]) for x in ("mean_margin","median_margin","minimum_margin","maximum_margin"))
        if any(not math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-7) for a,b in zip(observed,expected)): raise PersistedVerificationError("summary values mismatch")
    for r in panels: check_summary(r,by_token[(r["attribute"],int(r["token_index"]))],10)
    for r in signs: check_summary(r,by_pair[(r["attribute"],r["formal_pair_id"])],32)
    if any(r["within_tolerance"]!="True" for r in pooled): raise PersistedVerificationError("pooled replication failed")
    memory=protocol.read_json(run_dir/"scientific_in_memory_verification_v1.json"); summary=protocol.read_json(run_dir/"scientific_execution_summary_v1.json")
    if memory.get("status")!="PASS_INDEPENDENT_IN_MEMORY_TOKEN_DIRECTION_RECOMPUTATION" or memory.get("all_640_margins_recomputed") is not True: raise PersistedVerificationError("in-memory verification missing")
    if summary.get("raw_identity_or_token_tensor_files")!=0 or summary.get("outcomes_opened_or_joined") is not False: raise PersistedVerificationError("privacy/outcome boundary failed")
    result={"schema_version":1,"status":"PASS_INDEPENDENT_PERSISTED_TOKEN_DIRECTION_SCIENTIFIC_VERIFICATION","extraction_rows":160,"margin_rows":640,"token_panel_rows":64,"pair_sign_rows":20,"pooled_rows":20,"all_640_margins_independently_recomputed_in_memory":True,"raw_tensor_files":0,"outcome_access":False}
    protocol.atomic_json(output,result); print(json.dumps(result,indent=2,sort_keys=True)); return result
def main():
    p=argparse.ArgumentParser(); p.add_argument("--run-dir",required=True,type=Path); p.add_argument("--output",required=True,type=Path); a=p.parse_args(); verify(a.run_dir,a.output); return 0
if __name__=="__main__":
    try: raise SystemExit(main())
    except (PersistedVerificationError,protocol.DirectionProtocolError,ValueError) as error: print(f"FAIL: {error}",file=sys.stderr); raise SystemExit(2)
