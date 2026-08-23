#!/usr/bin/env python3
"""Run the frozen, offline eyeglasses measurement-repair evaluation."""
from __future__ import annotations
import csv,hashlib,json,os,statistics,subprocess
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
os.environ.setdefault('CUDA_VISIBLE_DEVICES','');os.environ.setdefault('HF_HUB_OFFLINE','1');os.environ.setdefault('TRANSFORMERS_OFFLINE','1');os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY','1');os.environ.setdefault('TOKENIZERS_PARALLELISM','false');os.environ.setdefault('OMP_NUM_THREADS','1')
from PIL import Image
ROOT=Path('/root/autodl-tmp/finegrained');REPO=ROOT/'research_pipeline';RUNTIME=ROOT/'formal_experiment_v1_runtime';REPAIR=RUNTIME/'measurement_repair_v1'
PDIR=REPAIR/'repaired_eyeglasses_evaluation_protocol_v1';PROTOCOL=PDIR/'repaired_eyeglasses_evaluation_protocol_v1.json';PFREEZE=PDIR/'repaired_eyeglasses_evaluation_protocol_freeze_v1.json';OUT=REPAIR/'repaired_eyeglasses_evaluation_v1'
CONSENSUS=REPAIR/'eyeglasses_consensus_v1_1/eyeglasses_final_consensus_v1_1.csv';MAPPING=REPAIR/'eyeglasses_blind_annotation_v1/private_mapping_v1/eyeglasses_private_mapping_v1.csv';TECH=REPAIR/'selected_detector_technical_audit_final_v1_1/selected_detector_technical_audit_final_v1_1.csv';BENCH=REPAIR/'detector_benchmark_v1/detector_item_results_v1.csv';MANIFEST=RUNTIME/'experiment_freeze_v1/generation_manifest_v1.csv';CLIP_DIR=ROOT/'metric_models_v2/clip-vit-base-patch32'
FRAME_COLUMNS=['schema_version','annotation_item_id','evaluation_item_id','task_id','formal_unit_id','formal_pair_id','role','expected_state','seed_index','seed','frame_index','human_observable','human_eyeglasses_label','human_expected_state_match','consensus_source','selected_detector','detector_detected','technical_audit_status','technical_audit_note','audited_bbox','crop_box','p_present','p_absent','margin_present_minus_absent','automated_predicted_state','automated_human_label_match','automated_expected_state_match','human_measurement_status','automated_measurement_status','primary_reason_code','record_status']
VIDEO_COLUMNS=['schema_version','task_id','formal_unit_id','formal_pair_id','role','expected_state','seed_index','seed','fixed_frames','human_observable_frames','human_unobservable_frames','human_present_frame_fraction','human_expected_state_match_fraction','automated_valid_frames','automated_invalid_technical_frames','automated_valid_fraction','automated_mean_p_present','automated_present_frame_fraction','automated_human_label_match_fraction','summary_status']
PAIR_COLUMNS=['schema_version','formal_pair_id','seed_index','positive_task_id','control_task_id','positive_human_present_fraction','control_human_present_fraction','human_positive_minus_control','positive_automated_mean_p_present','control_automated_mean_p_present','automated_positive_minus_control','record_status']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def read_csv(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write_csv_new(p,cols,data):
 with p.open('x',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=cols,extrasaction='raise');w.writeheader();w.writerows(data)
def write_json_new(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,ensure_ascii=False,sort_keys=True);f.write('\n')
def require(x,m):
 if not x:raise RuntimeError(m)
def square_crop(b,w,h):
 x0,y0,x1,y1=b;side=min(max(1.35*(x1-x0),1.35*(y1-y0)),min(w,h));size=round(side);x=max(0,min(round((x0+x1)/2-side/2),w-size));y=max(0,min(round((y0+y1)/2-side/2),h-size));require(size>=2,'invalid crop');return x,y,x+size,y+size
def mean(values):return f'{statistics.mean(values):.8f}' if values else ''
def fraction(values):return f'{sum(values)/len(values):.8f}' if values else ''
def main():
 require(os.environ.get('CUDA_VISIBLE_DEVICES') in ('','-1'),'CPU-only required');require(not OUT.exists() and not OUT.with_name(OUT.name+'.inprogress').exists(),'output exists');require(subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True)=='','dirty repository')
 protocol=json.loads(PROTOCOL.read_text());pf=json.loads(PFREEZE.read_text());require(protocol['status']==pf['status']=='FROZEN_BEFORE_REPAIRED_SCORING','protocol not frozen');require(sha(PROTOCOL)==pf['protocol_sha256'],'protocol drift');require(sha(Path(__file__))==pf['evaluator_script_sha256'],'evaluator drift');require(sha(CONSENSUS)==protocol['bound_artifact_sha256']['consensus_csv'],'consensus drift');require(sha(TECH)==protocol['bound_artifact_sha256']['technical_audit_csv'],'technical audit drift')
 consensus={r['annotation_item_id']:r for r in read_csv(CONSENSUS)};mapping={r['annotation_item_id']:r for r in read_csv(MAPPING)};technical={r['annotation_item_id']:r for r in read_csv(TECH)};manifest={r['task_id']:r for r in read_csv(MANIFEST) if r['attribute']=='eyeglasses'}
 require(len(consensus)==len(mapping)==len(technical)==560 and len(manifest)==80,'universe drift');require(set(consensus)==set(mapping)==set(technical),'join mismatch')
 import torch
 from transformers import CLIPModel,CLIPProcessor
 torch.set_num_threads(1);require(not torch.cuda.is_available(),'CUDA unexpectedly available');model=CLIPModel.from_pretrained(str(CLIP_DIR),local_files_only=True).to('cpu').eval();processor=CLIPProcessor.from_pretrained(str(CLIP_DIR),local_files_only=True)
 prompts=protocol['automated_measurement']['clip_instrument']['prompt_bank'];pprompts,nprompts=prompts['positive_prompts'],prompts['negative_prompts']
 with torch.no_grad():
  text=model.get_text_features(**processor(text=pprompts+nprompts,return_tensors='pt',padding=True));text=text/text.norm(dim=-1,keepdim=True);pos=text[:len(pprompts)].mean(0);pos=pos/pos.norm();neg=text[len(pprompts):].mean(0);neg=neg/neg.norm()
 work=OUT.with_name(OUT.name+'.inprogress');work.mkdir();frame_rows=[];pending=[]
 for item in sorted(mapping):
  m,c,t=mapping[item],consensus[item],technical[item];task=manifest[m['task_id']];require(m['frame_index'] in {'0','8','16','24','32','40','48'},f'frame drift {item}');require(t['selected_detector']=='yunet_native_t03',f'detector drift {item}')
  observable=c['final_face_eye_region_observable_yes_no']=='yes';label=c['final_eyeglasses_label'];require(label in ({'present','absent'} if observable else {'U'}),f'consensus logic {item}');audit_pass=t['technical_status_pass_fail']=='pass'
  row={'schema_version':'1','annotation_item_id':item,'evaluation_item_id':m['evaluation_item_id'],'task_id':m['task_id'],'formal_unit_id':m['formal_unit_id'],'formal_pair_id':m['formal_pair_id'],'role':m['role'],'expected_state':task['expected_state'],'seed_index':m['seed_index'],'seed':m['seed'],'frame_index':m['frame_index'],'human_observable':str(observable).lower(),'human_eyeglasses_label':label,'human_expected_state_match':str(label==task['expected_state']).lower() if observable else '','consensus_source':c['consensus_source'],'selected_detector':t['selected_detector'],'detector_detected':t['detected'],'technical_audit_status':t['technical_status_pass_fail'],'technical_audit_note':t['review_note'],'audited_bbox':'','crop_box':'','p_present':'','p_absent':'','margin_present_minus_absent':'','automated_predicted_state':'','automated_human_label_match':'','automated_expected_state_match':'','human_measurement_status':'OBSERVABLE' if observable else 'UNOBSERVABLE','automated_measurement_status':'VALID_OBSERVABLE' if audit_pass else 'INVALID_TECHNICAL_AUDIT','primary_reason_code':'' if audit_pass else 'SELECTED_DETECTOR_TECHNICAL_AUDIT_FAIL','record_status':'RETAINED'}
  if audit_pass:
   bbox=[float(t[k]) for k in ('bbox_x1','bbox_y1','bbox_x2','bbox_y2')];row['audited_bbox']=','.join(f'{x:.4f}' for x in bbox);path=Path(m['anonymous_frame_path']);require(sha(path)==m['anonymous_frame_sha256'],f'frame drift {item}');image=Image.open(path).convert('RGB');crop=square_crop(bbox,image.width,image.height);row['crop_box']=','.join(map(str,crop));pending.append((row,image.crop(crop)))
  frame_rows.append(row)
 for start in range(0,len(pending),32):
  batch=pending[start:start+32]
  with torch.no_grad():
   feat=model.get_image_features(**processor(images=[x[1] for x in batch],return_tensors='pt'));feat=feat/feat.norm(dim=-1,keepdim=True);logits=torch.stack((feat@pos,feat@neg),dim=1)*model.logit_scale.exp();probs=torch.softmax(logits,dim=1).cpu().numpy()
  for (row,_),prob in zip(batch,probs):
   ppr,pa=map(float,prob);margin=ppr-pa;pred='present' if margin>0 else ('absent' if margin<0 else '');row.update({'p_present':f'{ppr:.8f}','p_absent':f'{pa:.8f}','margin_present_minus_absent':f'{margin:.8f}','automated_predicted_state':pred,'automated_human_label_match':str(pred==row['human_eyeglasses_label']).lower() if row['human_observable']=='true' else '','automated_expected_state_match':str(pred==row['expected_state']).lower()})
  print(f'CLIP scoring {min(start+32,len(pending))}/{len(pending)}',flush=True)
 by_task=defaultdict(list)
 for r in frame_rows:by_task[r['task_id']].append(r)
 video_rows=[]
 for task_id in sorted(by_task):
  g=by_task[task_id];require(len(g)==7,f'task count {task_id}');human=[r for r in g if r['human_measurement_status']=='OBSERVABLE'];auto=[r for r in g if r['automated_measurement_status']=='VALID_OBSERVABLE'];a=g[0]
  video_rows.append({'schema_version':'1','task_id':task_id,'formal_unit_id':a['formal_unit_id'],'formal_pair_id':a['formal_pair_id'],'role':a['role'],'expected_state':a['expected_state'],'seed_index':a['seed_index'],'seed':a['seed'],'fixed_frames':'7','human_observable_frames':str(len(human)),'human_unobservable_frames':str(7-len(human)),'human_present_frame_fraction':fraction([r['human_eyeglasses_label']=='present' for r in human]),'human_expected_state_match_fraction':fraction([r['human_expected_state_match']=='true' for r in human]),'automated_valid_frames':str(len(auto)),'automated_invalid_technical_frames':str(7-len(auto)),'automated_valid_fraction':f'{len(auto)/7:.8f}','automated_mean_p_present':mean([float(r['p_present']) for r in auto]),'automated_present_frame_fraction':fraction([r['automated_predicted_state']=='present' for r in auto]),'automated_human_label_match_fraction':fraction([r['automated_human_label_match']=='true' for r in auto if r['human_observable']=='true']),'summary_status':'COMPLETE' if len(auto)==7 else 'COMPLETE_WITH_RETAINED_TECHNICAL_INVALIDITY'})
 groups=defaultdict(list)
 for r in video_rows:groups[(r['formal_pair_id'],r['seed_index'])].append(r)
 pair_rows=[]
 for (pair_id,seed_index),g in sorted(groups.items()):
  require(len(g)==2 and {r['role'] for r in g}=={'positive','control'},f'pair {pair_id}/{seed_index}');p=next(r for r in g if r['role']=='positive');c=next(r for r in g if r['role']=='control');hp,hc=p['human_present_frame_fraction'],c['human_present_frame_fraction'];ap,ac=p['automated_mean_p_present'],c['automated_mean_p_present']
  pair_rows.append({'schema_version':'1','formal_pair_id':pair_id,'seed_index':seed_index,'positive_task_id':p['task_id'],'control_task_id':c['task_id'],'positive_human_present_fraction':hp,'control_human_present_fraction':hc,'human_positive_minus_control':f'{float(hp)-float(hc):.8f}' if hp and hc else '','positive_automated_mean_p_present':ap,'control_automated_mean_p_present':ac,'automated_positive_minus_control':f'{float(ap)-float(ac):.8f}' if ap and ac else '','record_status':'DESCRIPTIVE_FIXED_PANEL_ONLY'})
 bench=read_csv(BENCH);e2i={r['evaluation_item_id']:r['annotation_item_id'] for r in mapping.values()};coverage=[]
 for candidate in ('scrfd_640_t05','yunet_native_t03'):
  selected=[r for r in bench if r['candidate_id']==candidate and r['evaluation_item_id'] in e2i];obs=[r for r in selected if consensus[e2i[r['evaluation_item_id']]]['final_face_eye_region_observable_yes_no']=='yes'];det=sum(r['detected']=='true' for r in obs);coverage.append({'method':candidate,'human_observable_frames':len(obs),'usable_frames':det,'coverage':f'{det/len(obs):.8f}','definition':'raw_detector_detection'})
 obs=[r for r in frame_rows if r['human_observable']=='true'];usable=sum(r['technical_audit_status']=='pass' for r in obs);coverage.append({'method':'yunet_native_t03_after_technical_audit','human_observable_frames':len(obs),'usable_frames':usable,'coverage':f'{usable/len(obs):.8f}','definition':'detected_and_human_technical_audit_pass'})
 valid=[r for r in frame_rows if r['human_observable']=='true' and r['automated_measurement_status']=='VALID_OBSERVABLE'];conf=Counter((r['human_eyeglasses_label'],r['automated_predicted_state']) for r in valid);hd=[float(r['human_positive_minus_control']) for r in pair_rows if r['human_positive_minus_control']];ad=[float(r['automated_positive_minus_control']) for r in pair_rows if r['automated_positive_minus_control']];labels=Counter(r['human_eyeglasses_label'] for r in frame_rows);tp=conf[('present','present')]/sum(v for (h,_),v in conf.items() if h=='present');tn=conf[('absent','absent')]/sum(v for (h,_),v in conf.items() if h=='absent')
 summary={'schema_version':1,'analysis_id':'formal_repaired_eyeglasses_evaluation_v1','completed_at_utc':datetime.now(timezone.utc).isoformat(),'fixed_universe':{'frames':560,'videos':80,'matched_seed_pairs':40},'human_consensus':{'label_counts':dict(labels),'observable_frames':labels['present']+labels['absent'],'unobservable_frames':labels['U']},'technical_audit':{'pass':sum(r['technical_audit_status']=='pass' for r in frame_rows),'fail_retained_no_imputation':sum(r['technical_audit_status']=='fail' for r in frame_rows)},'clip_against_human_consensus':{'validated_intersection_frames':len(valid),'confusion_human_then_automated':{f'{a}->{b}':n for (a,b),n in sorted(conf.items())},'accuracy':sum(r['human_eyeglasses_label']==r['automated_predicted_state'] for r in valid)/len(valid),'balanced_accuracy':(tp+tn)/2},'fixed_panel_descriptive_contrasts':{'human_pair_differences_available':len(hd),'human_mean_positive_minus_control':statistics.mean(hd),'human_median_positive_minus_control':statistics.median(hd),'automated_pair_differences_available':len(ad),'automated_mean_positive_minus_control':statistics.mean(ad),'automated_median_positive_minus_control':statistics.median(ad)},'inference_boundary':'Describes only the 80 fixed videos and 40 matched seed pairs; no causal, population, model-wide, or frame-independent inference.','status':'COMPLETE_SECONDARY_MEASUREMENT_REPAIR_DESCRIPTIVE_ONLY'}
 write_csv_new(work/'repaired_eyeglasses_frame_ledger_v1.csv',FRAME_COLUMNS,frame_rows);write_csv_new(work/'repaired_eyeglasses_video_summary_v1.csv',VIDEO_COLUMNS,video_rows);write_csv_new(work/'repaired_eyeglasses_matched_seed_pairs_v1.csv',PAIR_COLUMNS,pair_rows);write_csv_new(work/'detector_coverage_comparison_v1.csv',['method','human_observable_frames','usable_frames','coverage','definition'],coverage);write_json_new(work/'repaired_eyeglasses_descriptive_summary_v1.json',summary)
 hashes=[]
 for p in sorted(work.iterdir()):
  if p.is_file() and p.name!='output_hashes_v1.csv':hashes.append({'filename':p.name,'sha256':sha(p),'bytes':p.stat().st_size})
 write_csv_new(work/'output_hashes_v1.csv',['filename','sha256','bytes'],hashes)
 write_json_new(work/'repaired_eyeglasses_execution_record_v1.json',{'schema_version':1,'repository_commit':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),'script_sha256':sha(Path(__file__)),'protocol_sha256':sha(PROTOCOL),'rows':{'frame_ledger':560,'video_summary':80,'matched_seed_pairs':40},'network_used':False,'gpu_used':False,'generation_performed':False,'detector_substitution_performed':False,'selective_exclusion_performed':False,'imputation_performed':False,'technical_fail_rows_retained':7,'status':summary['status']})
 write_json_new(work/'repaired_eyeglasses_results_freeze_v1.json',{'schema_version':1,'freeze_id':'formal_repaired_eyeglasses_results_v1','protocol_sha256':sha(PROTOCOL),'output_hash_inventory_sha256':sha(work/'output_hashes_v1.csv'),'frame_rows':560,'video_rows':80,'pair_rows':40,'status':'FROZEN_PENDING_INDEPENDENT_VERIFICATION'})
 work.rename(OUT);print(json.dumps(summary,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
