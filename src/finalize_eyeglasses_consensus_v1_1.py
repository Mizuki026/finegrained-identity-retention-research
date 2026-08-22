#!/usr/bin/env python3
"""Freeze anonymous eyeglasses consensus after blind third-researcher adjudication."""
from __future__ import annotations
import csv, hashlib, json, shutil, subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE=Path('/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/measurement_repair_v1')
AGREE=BASE/'eyeglasses_blind_annotation_agreement_v1_1'
OUT=BASE/'eyeglasses_consensus_v1_1'
REPO=Path('/root/autodl-tmp/finegrained/research_pipeline')
EXPECTED_FREEZE='6e792c18202d591fa8ce433444632a5748583825e24de308405adb308c0119f2'
EXPECTED_SUBMISSION='9378ce8803767a39ef933d662b336450ca7fa94339ce38ee929a03f49964e78d'
class E(RuntimeError):pass
def req(x,m):
 if not x:raise E(m)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def rcsv(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def wcsv(p,fields,rows):
 with p.open('x',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='raise');w.writeheader();w.writerows(rows)
def wjson(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 req(not OUT.exists() and not OUT.with_name(OUT.name+'.inprogress').exists(),'output exists')
 freeze=AGREE/'eyeglasses_adjudication_packet_freeze_v1_1.json'; submission=AGREE/'eyeglasses_adjudication_template_v1_1.csv'
 req(sha(freeze)==EXPECTED_FREEZE and sha(submission)==EXPECTED_SUBMISSION,'frozen input mismatch')
 req(subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True)=='','dirty repo')
 committed=REPO/'src/finalize_eyeglasses_consensus_v1_1.py';req(committed.is_file() and sha(committed)==sha(Path(__file__)),'uncommitted script')
 commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
 snaps={a:rcsv(AGREE/f'submitted_snapshots/eyeglasses_annotator_{a}_submitted_v1_1.csv') for a in 'AB'}
 maps={a:{r['annotation_item_id']:r for r in snaps[a]} for a in 'AB'};req(len(maps['A'])==len(maps['B'])==560 and set(maps['A'])==set(maps['B']),'snapshot mismatch')
 submitted=rcsv(submission);req(len(submitted)==78,'submission rows mismatch')
 decisions=defaultdict(dict); normalized=[]; delimiter_changes=0
 for r in submitted:
  item,field=r['annotation_item_id'],r['field'];req(item in maps['A'] and field in {'face_eye_region_observable_yes_no','eyeglasses_label'},'bad key')
  keyA='face_eye_region_observable_yes_no' if field.startswith('face_') else 'eyeglasses_label'
  req(r['option_A']==maps['A'][item][keyA] and r['option_B']==maps['B'][item][keyA],'options changed')
  req(r['note_A']==maps['A'][item]['reason_or_note'] and r['note_B']==maps['B'][item]['reason_or_note'],'notes changed')
  allowed=['yes','no'] if field.startswith('face_') else ['present','absent','U']
  req(r['allowed_values'] in {'|'.join(allowed),','.join(allowed)},'unexpected allowed values')
  delimiter_changes+=r['allowed_values']==','.join(allowed)
  value=r['adjudicated_value'].strip();reason=r['rationale'].strip();req(value in allowed and reason,'invalid adjudication')
  req(field not in decisions[item],'duplicate decision');decisions[item][field]=(value,reason)
  x=dict(r);x['allowed_values']='|'.join(allowed);normalized.append(x)
 req(len(decisions)==39 and all(len(x)==2 for x in decisions.values()),'decision coverage mismatch')
 for item,d in decisions.items():req((d['face_eye_region_observable_yes_no'][0]=='no')==(d['eyeglasses_label'][0]=='U'),f'logic mismatch {item}')
 tmp=OUT.with_name(OUT.name+'.inprogress');tmp.mkdir(parents=True);snap=tmp/'submitted_adjudication';snap.mkdir()
 shutil.copyfile(submission,snap/'adjudication_decisions_submitted_v1_1.csv')
 fields=list(normalized[0]);wcsv(tmp/'adjudication_decisions_normalized_v1_1.csv',fields,normalized)
 final=[]
 for item in sorted(maps['A']):
  a,b=maps['A'][item],maps['B'][item]
  if a['eyeglasses_label']==b['eyeglasses_label'] and a['face_eye_region_observable_yes_no']==b['face_eye_region_observable_yes_no']:
   obs,label,source=a['face_eye_region_observable_yes_no'],a['eyeglasses_label'],'A_B_AGREEMENT';ro=rl=''
  else:
   req(item in decisions,'missing adjudication');obs,ro=decisions[item]['face_eye_region_observable_yes_no'];label,rl=decisions[item]['eyeglasses_label'];source='THIRD_RESEARCHER_ADJUDICATION'
  req((obs=='no')==(label=='U'),'final logic error')
  final.append({'annotation_item_id':item,'final_face_eye_region_observable_yes_no':obs,'final_eyeglasses_label':label,'consensus_source':source,'annotator_A_confidence':a['annotation_confidence_high_low'],'annotator_B_confidence':b['annotation_confidence_high_low'],'note_A':a['reason_or_note'],'note_B':b['reason_or_note'],'adjudication_rationale_observability':ro,'adjudication_rationale_label':rl})
 wcsv(tmp/'eyeglasses_final_consensus_v1_1.csv',list(final[0]),final)
 audit={'schema_version':1,'consensus_id':'formal_measurement_repair_eyeglasses_consensus_v1_1','created_at_utc':datetime.now(timezone.utc).isoformat(),'items':560,'A_B_agreement_items':521,'adjudicated_items':39,'submitted_adjudication_sha256':sha(submission),'mechanical_normalization':{'field':'allowed_values','comma_to_pipe_rows':delimiter_changes,'scientific_values_changed':False},'final_observability_counts':dict(Counter(r['final_face_eye_region_observable_yes_no'] for r in final)),'final_label_counts':dict(Counter(r['final_eyeglasses_label'] for r in final)),'notes_and_rationales_preserved':True,'private_mapping_accessed':False,'status':'FROZEN_ANONYMOUS_CONSENSUS_PENDING_INDEPENDENT_VERIFICATION'}
 wjson(tmp/'eyeglasses_consensus_audit_v1_1.json',audit)
 fr={'schema_version':1,'freeze_id':'formal_measurement_repair_eyeglasses_consensus_v1_1_freeze','frozen_at_utc':datetime.now(timezone.utc).isoformat(),'source_adjudication_freeze_sha256':EXPECTED_FREEZE,'repository_commit':commit,'script_sha256':sha(Path(__file__)),'submitted_adjudication_sha256':sha(submission),'normalized_adjudication_sha256':sha(tmp/'adjudication_decisions_normalized_v1_1.csv'),'consensus_sha256':sha(tmp/'eyeglasses_final_consensus_v1_1.csv'),'audit_sha256':sha(tmp/'eyeglasses_consensus_audit_v1_1.json'),'private_mapping_accessed':False,'status':audit['status']}
 wjson(tmp/'eyeglasses_consensus_freeze_v1_1.json',fr);tmp.rename(OUT)
 print(json.dumps({'status':fr['status'],'items':560,'agreement_items':521,'adjudicated_items':39,'delimiter_normalizations':delimiter_changes,'private_mapping_accessed':False},indent=2))
if __name__=='__main__':
 try:main()
 except E as e:raise SystemExit(f'CONSENSUS FINALIZATION FAILED: {e}')
