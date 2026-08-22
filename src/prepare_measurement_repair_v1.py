#!/usr/bin/env python3
"""Freeze the independent formal measurement-repair v1 protocol before benchmarking."""
from __future__ import annotations
import csv,hashlib,json,shutil,subprocess
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path('/root/autodl-tmp/finegrained')
REPO=ROOT/'research_pipeline'
RUNTIME=ROOT/'formal_experiment_v1_runtime'
MASTER=RUNTIME/'experiment_freeze_v1/pre_generation_master_freeze_v1.json'
REPAIR=RUNTIME/'measurement_repair_v1'
MACHINE=RUNTIME/'attribute_evaluation_v1/run_001'
CONSENSUS=RUNTIME/'attribute_evaluation_v1/final_facial_hair_annotation_v1'
MASTER_SHA='149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8'
MAPPING_SHA='1376bbfa93ad5d071bf291958ceef7b9e2c852fa713efeb2b475dceaf50de162'
FRAME_INDICES=(0,8,16,24,32,40,48)
SCRFD=Path('/root/autodl-tmp/consisid-smoketest/ckpts/ConsisID-preview/face_encoder/models/antelopev2/scrfd_10g_bnkps.onnx')
YUNET=ROOT/'metric_models_v2/yunet/face_detection_yunet_2023mar.onnx'
HAAR=Path('/root/autodl-tmp/consisid-smoketest/env/lib/python3.11/site-packages/cv2/data/haarcascade_frontalface_default.xml')
EXPECTED_MODELS={SCRFD:'5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91',YUNET:'8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4',HAAR:'0f7d4527844eb514d4a4948e822da90fbb16a34a0bbbbc6adc6498747a5aafb0'}
class FreezeError(RuntimeError):pass
def check(x,msg):
 if not x:raise FreezeError(msg)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def rcsv(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def wcsv(p,fields,rows):
 with p.open('x',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='raise');w.writeheader();w.writerows(rows)
def wjson(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
def item(prefix,text):return prefix+'_'+hashlib.sha256(text.encode()).hexdigest()[:16].upper()
def main():
 check(sha(MASTER)==MASTER_SHA,'master freeze mismatch')
 check(not REPAIR.exists() and not REPAIR.with_name(REPAIR.name+'.inprogress').exists(),'repair directory already exists')
 check(subprocess.check_output(['git','-C',str(REPO),'branch','--show-current'],text=True).strip()=='measurement-repair-v1','wrong branch')
 check(subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True)=='','working tree not clean')
 for p,h in EXPECTED_MODELS.items():check(p.is_file() and sha(p)==h,f'detector model mismatch: {p}')
 for name in ('prepare_measurement_repair_v1.py','measurement_repair_detector_benchmark_v1.py','build_eyeglasses_blind_annotation_v1.py'):
  check((REPO/'src'/name).is_file(),f'missing committed code: {name}')
 master=json.loads(MASTER.read_text()); manifest=rcsv(Path(master['artifacts']['generation_manifest']['path']))
 check(len(manifest)==160 and len({r['task_id'] for r in manifest})==160,'manifest mismatch')
 integrity=rcsv(RUNTIME/'post_generation_integrity_v1/video_integrity_v1.csv'); imap={r['task_id']:r for r in integrity}
 check(len(imap)==160 and all(r['engineering_status']=='PASS' for r in integrity),'integrity mismatch')
 cv=json.loads((RUNTIME/'attribute_evaluation_v1/final_facial_hair_annotation_v1_independent_verification.json').read_text())
 check(cv['status']=='PASS_INDEPENDENT_ANONYMOUS_CONSENSUS_VERIFICATION','consensus not verified')
 mapping_path=MACHINE/'private_mapping_v1/facial_hair_private_mapping_v1.csv';check(sha(mapping_path)==MAPPING_SHA,'mapping hash mismatch')
 mapping=rcsv(mapping_path);labels={r['annotation_item_id']:r for r in rcsv(CONSENSUS/'facial_hair_final_labels_v1.csv')}
 check(len(mapping)==560 and len(labels)==560 and {r['annotation_item_id'] for r in mapping}==set(labels),'mapping/labels mismatch')
 tasks={r['task_id']:r for r in manifest}; rows=[]
 by_unit=defaultdict(list)
 for r in manifest:by_unit[r['formal_unit_id']].append(r)
 for uid,mrows in sorted(by_unit.items()):
  r=mrows[0]; eid=item('MRD',f'measurement_repair_v1|reference|{uid}')
  rows.append({'evaluation_item_id':eid,'source_kind':'reference_image','task_id':'','formal_unit_id':uid,'formal_pair_id':r['formal_pair_id'],'attribute':r['attribute'],'role':r['role'],'seed_index':'','seed':'','frame_index':'','source_path':r['reference_image_path'],'source_sha256':r['reference_image_sha256'],'human_observable_reference':'true'})
 for m in mapping:
  t=tasks[m['task_id']];eid=item('MRD',f"measurement_repair_v1|facial|{m['annotation_item_id']}")
  rows.append({'evaluation_item_id':eid,'source_kind':'facial_hair_sample_frame','task_id':m['task_id'],'formal_unit_id':m['formal_unit_id'],'formal_pair_id':m['formal_pair_id'],'attribute':'facial_hair','role':m['role'],'seed_index':m['seed_index'],'seed':m['seed'],'frame_index':m['frame_index'],'source_path':m['source_video_path'],'source_sha256':m['source_video_sha256'],'human_observable_reference':str(labels[m['annotation_item_id']]['final_label']!='U').lower()})
 for t in manifest:
  if t['attribute']!='eyeglasses':continue
  for fi in FRAME_INDICES:
   eid=item('MRD',f"measurement_repair_v1|eyeglasses|{t['task_id']}|{fi}")
   rows.append({'evaluation_item_id':eid,'source_kind':'eyeglasses_sample_frame','task_id':t['task_id'],'formal_unit_id':t['formal_unit_id'],'formal_pair_id':t['formal_pair_id'],'attribute':'eyeglasses','role':t['role'],'seed_index':t['seed_index'],'seed':t['seed'],'frame_index':fi,'source_path':t['expected_video_path'],'source_sha256':imap[t['task_id']]['video_sha256'],'human_observable_reference':''})
 check(len(rows)==1160 and len({r['evaluation_item_id'] for r in rows})==1160,'evaluation universe mismatch')
 tmp=REPAIR.with_name(REPAIR.name+'.inprogress');tmp.mkdir(parents=True)
 fields=['evaluation_item_id','source_kind','task_id','formal_unit_id','formal_pair_id','attribute','role','seed_index','seed','frame_index','source_path','source_sha256','human_observable_reference']
 wcsv(tmp/'detector_evaluation_manifest_v1.csv',fields,rows)
 model_rows=[]
 for name,p in [('scrfd_10g',SCRFD),('yunet_2023mar',YUNET),('opencv_haar_frontal_default',HAAR)]:model_rows.append({'model_id':name,'absolute_path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
 wcsv(tmp/'detector_model_hashes_v1.csv',['model_id','absolute_path','bytes','sha256'],model_rows)
 candidates=[
  {'candidate_id':f'scrfd_{size}_t{str(thr).replace(".","")}', 'family':'SCRFD-10G','det_size':[size,size],'score_threshold':thr,'postfilter_from_threshold':0.1} for size in (640,1024) for thr in (0.5,0.3,0.1)
 ]+[
  {'candidate_id':f'yunet_native_t{str(thr).replace(".","")}', 'family':'YuNet-2023mar','input_size':'native_frame','score_threshold':thr,'nms_threshold':0.3,'top_k':5000,'postfilter_from_threshold':0.3} for thr in (0.9,0.6,0.3)
 ]+[
  {'candidate_id':f'haar_sf105_n{n}','family':'OpenCV-Haar','grayscale_equalization':True,'scale_factor':1.05,'min_neighbors':n,'min_size':[24,24]} for n in (3,5)
 ]
 commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
 protocol={'schema_version':1,'protocol_id':'formal_measurement_repair_v1','frozen_at_utc':datetime.now(timezone.utc).isoformat(),'repair_classification':'post_hoc_measurement_validation_and_sensitivity_iteration','parent_master_freeze_sha256':MASTER_SHA,'parent_formal_results_are_immutable':True,'benchmark_universe':{'reference_images':40,'facial_hair_human_labeled_frames':560,'eyeglasses_fixed_frames':560,'total_items':1160,'fixed_frame_indices':list(FRAME_INDICES)},'candidate_detectors':candidates,'preliminary_detector_eligibility':{'reference_image_detection_recall_minimum':1.0,'human_observable_facial_hair_frame_recall_minimum':0.9,'plausible_bbox_fraction_minimum':0.98,'plausible_bbox_area_fraction_interval':[0.01,0.9],'eyeglasses_effect_direction_used_for_selection':False},'final_detector_eligibility_after_eye_annotation':{'human_observable_eyeglasses_frame_recall_minimum':0.9,'selection_score':'minimum(reference_recall, facial_hair_human_observable_recall, eyeglasses_human_observable_recall)','tie_break_order':['higher_selection_score','higher_score_threshold','smaller_inference_input','candidate_id_lexical'],'human_attribute_labels_never_inferred_from_detector_output':True},'manual_eyeglasses_annotation':{'frames_per_video':7,'total_frames':560,'frame_indices':list(FRAME_INDICES),'presentation':'full_decoded_frame_without_detector_crop','annotators':2,'independent':True,'blinded_fields':['task_id','formal_unit_id','formal_pair_id','role','expected_state','identity','seed','source_path'],'labels':['present','absent','U'],'face_eye_region_observable':['yes','no'],'confidence':['high','low'],'adjudicate_all_label_disagreements':True},'analysis_boundary':{'original_formal_results_replaced':False,'original_primary_metrics_reclassified':False,'repair_outputs_status':'secondary measurement-validation/sensitivity evidence','no_population_inference':True,'no_causal_inference':True,'no_detector_selection_by_attribute_effect':True,'no_imputation':True,'no_outcome_dependent_frame_exclusion':True},'code_binding':{'repository_commit':commit,'protocol_builder_script_sha256':sha(REPO/'src/prepare_measurement_repair_v1.py'),'benchmark_script_sha256':sha(REPO/'src/measurement_repair_detector_benchmark_v1.py'),'annotation_builder_script_sha256':sha(REPO/'src/build_eyeglasses_blind_annotation_v1.py')},'generation_or_annotation_started':False,'status':'FROZEN_BEFORE_DETECTOR_BENCHMARK_OR_EYE_ANNOTATION'}
 wjson(tmp/'measurement_repair_protocol_v1.json',protocol)
 inventory=[]
 for p in sorted(x for x in tmp.iterdir() if x.is_file()):inventory.append({'relative_path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
 wcsv(tmp/'protocol_artifact_hashes_v1.csv',['relative_path','bytes','sha256'],inventory)
 freeze={'schema_version':1,'freeze_id':'formal_measurement_repair_v1_protocol_freeze','frozen_at_utc':datetime.now(timezone.utc).isoformat(),'repository_commit':commit,'parent_master_freeze_sha256':MASTER_SHA,'protocol_sha256':sha(tmp/'measurement_repair_protocol_v1.json'),'evaluation_manifest_sha256':sha(tmp/'detector_evaluation_manifest_v1.csv'),'detector_model_hashes_sha256':sha(tmp/'detector_model_hashes_v1.csv'),'protocol_artifact_hashes_sha256':sha(tmp/'protocol_artifact_hashes_v1.csv'),'benchmark_started':False,'annotation_started':False,'status':'FROZEN_BEFORE_MEASUREMENT_REPAIR_EXECUTION'}
 wjson(tmp/'measurement_repair_protocol_freeze_v1.json',freeze);tmp.rename(REPAIR)
 print(json.dumps({'status':freeze['status'],'evaluation_items':len(rows),'detector_candidates':len(candidates),'scientific_outcomes_observed':False},indent=2))
if __name__=='__main__':
 try:main()
 except FreezeError as e:raise SystemExit(f'MEASUREMENT REPAIR FREEZE FAILED: {e}')
