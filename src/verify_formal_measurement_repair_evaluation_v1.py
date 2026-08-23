#!/usr/bin/env python3
"""Independent structural and arithmetic verification of repaired eye results."""
from __future__ import annotations
import csv,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path('/root/autodl-tmp/finegrained/formal_experiment_v1_runtime');REPAIR=ROOT/'measurement_repair_v1';RESULT=REPAIR/'repaired_eyeglasses_evaluation_v1';OUT=REPAIR/'repaired_eyeglasses_evaluation_v1_independent_verification.json';CONSENSUS=REPAIR/'eyeglasses_consensus_v1_1/eyeglasses_final_consensus_v1_1.csv';TECH=REPAIR/'selected_detector_technical_audit_final_v1_1/selected_detector_technical_audit_final_v1_1.csv'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def rows(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def require(x,m):
 if not x:raise RuntimeError(m)
def main():
 require(not OUT.exists(),f'refusing to overwrite {OUT}');frame=rows(RESULT/'repaired_eyeglasses_frame_ledger_v1.csv');video=rows(RESULT/'repaired_eyeglasses_video_summary_v1.csv');pair=rows(RESULT/'repaired_eyeglasses_matched_seed_pairs_v1.csv');consensus={r['annotation_item_id']:r for r in rows(CONSENSUS)};technical={r['annotation_item_id']:r for r in rows(TECH)}
 require(len(frame)==560 and len(video)==80 and len(pair)==40,'output universe mismatch');require(len({r['annotation_item_id'] for r in frame})==560,'duplicate item');require(set(consensus)==set(technical)=={r['annotation_item_id'] for r in frame},'join mismatch');by_task=defaultdict(list)
 for r in frame:
  item=r['annotation_item_id'];require(r['human_eyeglasses_label']==consensus[item]['final_eyeglasses_label'],f'label drift {item}');require(r['technical_audit_status']==technical[item]['technical_status_pass_fail'],f'audit drift {item}');require(r['record_status']=='RETAINED',f'not retained {item}')
  if r['technical_audit_status']=='fail':require(r['automated_measurement_status']=='INVALID_TECHNICAL_AUDIT' and not r['p_present'],f'failed item has value {item}')
  else:require(r['automated_measurement_status']=='VALID_OBSERVABLE' and r['p_present'] and abs(float(r['p_present'])+float(r['p_absent'])-1)<2e-7,f'probability error {item}')
  by_task[r['task_id']].append(r)
 require(Counter(r['technical_audit_status'] for r in frame)=={'pass':553,'fail':7},'audit counts mismatch');require(len(by_task)==80 and all(len(g)==7 for g in by_task.values()),'task grouping mismatch')
 for v in video:
  g=by_task[v['task_id']];require(int(v['human_observable_frames'])==sum(r['human_observable']=='true' for r in g),f'human summary {v["task_id"]}');require(int(v['automated_valid_frames'])==sum(r['technical_audit_status']=='pass' for r in g),f'auto summary {v["task_id"]}')
 inventory=rows(RESULT/'output_hashes_v1.csv')
 for r in inventory:
  p=RESULT/r['filename'];require(p.is_file() and sha(p)==r['sha256'] and p.stat().st_size==int(r['bytes']),f'artifact drift {p}')
 freeze=json.loads((RESULT/'repaired_eyeglasses_results_freeze_v1.json').read_text());require(freeze['status']=='FROZEN_PENDING_INDEPENDENT_VERIFICATION','freeze status');require(freeze['output_hash_inventory_sha256']==sha(RESULT/'output_hashes_v1.csv'),'inventory drift')
 out={'schema_version':1,'verification_id':'formal_repaired_eyeglasses_evaluation_v1_independent_verification','result_freeze_sha256':sha(RESULT/'repaired_eyeglasses_results_freeze_v1.json'),'frame_rows_verified':560,'video_rows_verified':80,'matched_seed_pair_rows_verified':40,'all_rows_retained':True,'technical_fail_rows_retained_without_imputation':7,'source_labels_verified':True,'summary_arithmetic_verified':True,'artifact_hashes_verified':True,'status':'PASS_INDEPENDENT_REPAIRED_EYEGLASSES_EVALUATION_VERIFICATION'}
 with OUT.open('x',encoding='utf-8') as f:json.dump(out,f,indent=2,ensure_ascii=False,sort_keys=True);f.write('\n')
 print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
