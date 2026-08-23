#!/usr/bin/env python3
"""Create a non-overwriting completion and review packet for measurement repair."""
from __future__ import annotations
import csv,hashlib,json,statistics,subprocess
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path('/root/autodl-tmp/finegrained');REPO=ROOT/'research_pipeline';RUNTIME=ROOT/'formal_experiment_v1_runtime';REPAIR=RUNTIME/'measurement_repair_v1';RESULT=REPAIR/'repaired_eyeglasses_evaluation_v1';VERIFY=REPAIR/'repaired_eyeglasses_evaluation_v1_independent_verification.json';OUT=REPAIR/'measurement_repair_completion_v1';OLD=RUNTIME/'attribute_evaluation_v1/run_001/eyeglasses_frame_measurements_v1.csv';MANIFEST=RUNTIME/'experiment_freeze_v1/generation_manifest_v1.csv'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def rows(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def require(x,m):
 if not x:raise RuntimeError(m)
def write_json_new(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,ensure_ascii=False,sort_keys=True);f.write('\n')
def write_csv_new(p,cols,data):
 with p.open('x',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(data)
def main():
 require(not OUT.exists(),f'refusing to overwrite {OUT}');require(subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True)=='','dirty repository')
 verification=json.loads(VERIFY.read_text());require(verification['status']=='PASS_INDEPENDENT_REPAIRED_EYEGLASSES_EVALUATION_VERIFICATION','repair results not independently verified')
 new=rows(RESULT/'repaired_eyeglasses_frame_ledger_v1.csv');pairs=rows(RESULT/'repaired_eyeglasses_matched_seed_pairs_v1.csv');old_all=rows(OLD);fixed={'0','8','16','24','32','40','48'};old={(r['task_id'],r['frame_index']):r for r in old_all if r['frame_index'] in fixed};require(len(new)==len(old)==560 and len(pairs)==40,'universe mismatch')
 original_inter=[]
 for r in new:
  o=old[(r['task_id'],r['frame_index'])]
  if o['measurement_status']=='VALID_OBSERVABLE' and r['human_observable']=='true':original_inter.append((r,o))
 repaired=[r for r in new if r['automated_measurement_status']=='VALID_OBSERVABLE' and r['human_observable']=='true']
 old_tasks={o['task_id'] for _,o in original_inter};new_tasks={r['task_id'] for r in repaired}
 human_deltas=[float(r['human_positive_minus_control']) for r in pairs];auto_deltas=[float(r['automated_positive_minus_control']) for r in pairs]
 zero=[{'formal_pair_id':r['formal_pair_id'],'seed_index':r['seed_index'],'positive_task_id':r['positive_task_id'],'control_task_id':r['control_task_id'],'human_positive_minus_control':r['human_positive_minus_control']} for r in pairs if float(r['human_positive_minus_control'])==0]
 mechanism={
  'schema_version':1,'summary_id':'formal_measurement_repair_completion_v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
  'fixed_universe':{'frames':560,'videos':80,'matched_seed_pairs':40},
  'original_formal_instrument_same_frame_subset':{'detector':'scrfd_640_t05','valid_frames':sum(o['measurement_status']=='VALID_OBSERVABLE' for o in old.values()),'valid_fraction':sum(o['measurement_status']=='VALID_OBSERVABLE' for o in old.values())/560,'human_observable_intersection':len(original_inter),'human_consensus_accuracy_on_tiny_intersection':sum(r['human_eyeglasses_label']==o['predicted_state'] for r,o in original_inter)/len(original_inter),'videos_with_any_valid_frame':len(old_tasks)},
  'repaired_instrument':{'detector':'yunet_native_t03 plus frozen technical audit','technical_pass_frames':sum(r['technical_audit_status']=='pass' for r in new),'technical_pass_fraction':sum(r['technical_audit_status']=='pass' for r in new)/560,'human_observable_intersection':len(repaired),'human_consensus_accuracy':sum(r['human_eyeglasses_label']==r['automated_predicted_state'] for r in repaired)/len(repaired),'videos_with_any_valid_frame':len(new_tasks)},
  'human_consensus_fixed_panel':{'positive_condition_observable_frames':sum(r['role']=='positive' and r['human_observable']=='true' for r in new),'positive_condition_present_frames':sum(r['role']=='positive' and r['human_eyeglasses_label']=='present' for r in new),'control_observable_frames':sum(r['role']=='control' and r['human_observable']=='true' for r in new),'control_present_frames':sum(r['role']=='control' and r['human_eyeglasses_label']=='present' for r in new),'mean_matched_seed_pair_difference':statistics.mean(human_deltas),'median_matched_seed_pair_difference':statistics.median(human_deltas),'positive_difference_units':sum(x>0 for x in human_deltas),'zero_difference_units':sum(x==0 for x in human_deltas),'negative_difference_units':sum(x<0 for x in human_deltas)},
  'mechanism_interpretation_for_review':'The dominant original measurement loss is face-detector non-detection, not demonstrated CLIP disagreement. This is a measurement-availability mechanism; it is not evidence that generation quality improved.',
  'decision_boundary':['Whether to accept human consensus as the main finite-panel eyeglasses description','Whether to retain YuNet+CLIP only as secondary convergent measurement evidence','Whether the next independent iteration should target generation-side identity/attribute retention mechanisms rather than further detector repair'],
  'prohibited_claims':['causal effect','population inference','model-wide performance','independent-frame inference','generalization from the 15-frame original-instrument intersection'],
  'status':'MEASUREMENT_REPAIR_COMPLETE_PENDING_RESEARCHER_INTERPRETATION_DECISION'}
 OUT.mkdir();write_json_new(OUT/'measurement_repair_mechanism_summary_v1.json',mechanism);write_csv_new(OUT/'zero_difference_pair_seed_units_v1.csv',['formal_pair_id','seed_index','positive_task_id','control_task_id','human_positive_minus_control'],zero)
 memo=f'''# Formal measurement-repair review memo v1\n\nStatus: **pending researcher interpretation decision**.\n\n- Fixed universe: 560 frames, 80 videos, 40 matched seed-pair units.\n- Original formal detector: 15/560 measurable frames; only {len(old_tasks)}/80 videos had any measurable fixed frame.\n- Repaired audited detector: 553/560 technical-pass frames; {len(repaired)} human-observable/technical-pass frames.\n- CLIP versus frozen human consensus on that repaired intersection: {mechanism['repaired_instrument']['human_consensus_accuracy']:.2%} accuracy.\n- Human consensus: 230/278 observable positive-condition frames contain eyeglasses; 0/271 observable control frames contain eyeglasses.\n- Matched seed-pair descriptions: 33 positive differences, 7 zero differences, 0 negative differences; mean difference {statistics.mean(human_deltas):.3f}.\n\nInterpretation proposed for review: the original instrument's main failure was detector coverage. The repaired automatic path is secondary convergent evidence; the frozen human consensus is the direct finite-panel description. No causal, population, model-wide, or independent-frame inference is permitted. No selective rerun or imputation was performed.\n'''
 (OUT/'measurement_repair_review_memo_v1.md').write_text(memo,encoding='utf-8')
 artifacts=[]
 for p in sorted(OUT.iterdir()):artifacts.append({'filename':p.name,'sha256':sha(p),'bytes':p.stat().st_size})
 write_csv_new(OUT/'artifact_hashes_v1.csv',['filename','sha256','bytes'],artifacts)
 write_json_new(OUT/'measurement_repair_completion_freeze_v1.json',{'schema_version':1,'freeze_id':'formal_measurement_repair_completion_v1','repository_commit':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),'script_sha256':sha(Path(__file__)),'repaired_result_freeze_sha256':verification['result_freeze_sha256'],'independent_verification_sha256':sha(VERIFY),'artifact_hash_inventory_sha256':sha(OUT/'artifact_hashes_v1.csv'),'status':mechanism['status']})
 print(json.dumps(mechanism,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
