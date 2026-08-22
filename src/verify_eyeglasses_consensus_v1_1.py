#!/usr/bin/env python3
"""Independently reconstruct and verify anonymous eyeglasses consensus."""
import csv,hashlib,json
from pathlib import Path
BASE=Path('/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/measurement_repair_v1')
AGREE=BASE/'eyeglasses_blind_annotation_agreement_v1_1';CONS=BASE/'eyeglasses_consensus_v1_1';OUT=BASE/'eyeglasses_consensus_v1_1_independent_verification.json'
class E(RuntimeError):pass
def req(x,m):
 if not x:raise E(m)
def sha(p):
 h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()
def rcsv(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def main():
 req(not OUT.exists(),'verification exists')
 freeze=json.loads((CONS/'eyeglasses_consensus_freeze_v1_1.json').read_text()); final=rcsv(CONS/'eyeglasses_final_consensus_v1_1.csv')
 req(sha(CONS/'eyeglasses_final_consensus_v1_1.csv')==freeze['consensus_sha256'] and len(final)==560,'consensus freeze mismatch')
 snaps={a:{r['annotation_item_id']:r for r in rcsv(AGREE/f'submitted_snapshots/eyeglasses_annotator_{a}_submitted_v1_1.csv')} for a in 'AB'}
 dec={}
 for r in rcsv(CONS/'adjudication_decisions_normalized_v1_1.csv'):
  req(r['adjudicated_value'] in r['allowed_values'].split('|') and r['rationale'].strip(),'invalid normalized decision');dec[(r['annotation_item_id'],r['field'])]=r
 req(len(dec)==78,'decision count mismatch'); rebuilt=[]
 for item in sorted(snaps['A']):
  a,b=snaps['A'][item],snaps['B'][item]
  if a['eyeglasses_label']==b['eyeglasses_label'] and a['face_eye_region_observable_yes_no']==b['face_eye_region_observable_yes_no']:
   obs,label,source=a['face_eye_region_observable_yes_no'],a['eyeglasses_label'],'A_B_AGREEMENT';ro=rl=''
  else:
   o=dec[(item,'face_eye_region_observable_yes_no')];l=dec[(item,'eyeglasses_label')]
   obs,label,source=o['adjudicated_value'],l['adjudicated_value'],'THIRD_RESEARCHER_ADJUDICATION';ro,rl=o['rationale'],l['rationale']
  rebuilt.append({'annotation_item_id':item,'final_face_eye_region_observable_yes_no':obs,'final_eyeglasses_label':label,'consensus_source':source,'annotator_A_confidence':a['annotation_confidence_high_low'],'annotator_B_confidence':b['annotation_confidence_high_low'],'note_A':a['reason_or_note'],'note_B':b['reason_or_note'],'adjudication_rationale_observability':ro,'adjudication_rationale_label':rl})
 req(rebuilt==final,'independent reconstruction differs');req(all((r['final_face_eye_region_observable_yes_no']=='no')==(r['final_eyeglasses_label']=='U') for r in final),'logic error')
 result={'schema_version':1,'verification_id':'formal_measurement_repair_eyeglasses_consensus_v1_1_independent_verification','consensus_freeze_sha256':sha(CONS/'eyeglasses_consensus_freeze_v1_1.json'),'items_verified':560,'agreement_items_verified':sum(r['consensus_source']=='A_B_AGREEMENT' for r in final),'adjudicated_items_verified':sum(r['consensus_source']=='THIRD_RESEARCHER_ADJUDICATION' for r in final),'notes_and_rationales_verified':True,'private_mapping_accessed':False,'status':'PASS_INDEPENDENT_ANONYMOUS_EYEGLASSES_CONSENSUS_VERIFICATION'}
 OUT.write_text(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 try:main()
 except E as e:raise SystemExit(f'CONSENSUS VERIFICATION FAILED: {e}')
