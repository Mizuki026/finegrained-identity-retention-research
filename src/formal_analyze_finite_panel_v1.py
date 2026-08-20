#!/usr/bin/env python3
"""Produce preregistered finite-panel descriptive results for formal experiment v1.

The producer verifies all frozen inputs, reads the facial-hair private mapping
exactly once after anonymous-consensus verification, and aggregates in the
frozen order: frames -> videos -> four-seed reference units -> matched pairs.
It performs no population/causal inference, cross-attribute ranking, imputation,
outcome-dependent exclusion, or post-hoc thresholding.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,math,statistics,subprocess
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path('/root/autodl-tmp/finegrained/formal_experiment_v1_runtime')
MASTER=ROOT/'experiment_freeze_v1/pre_generation_master_freeze_v1.json'
EXPECTED_MASTER='149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8'
EXPECTED_MAPPING='1376bbfa93ad5d071bf291958ceef7b9e2c852fa713efeb2b475dceaf50de162'
MACHINE=ROOT/'attribute_evaluation_v1/run_001'
CONSENSUS=ROOT/'attribute_evaluation_v1/final_facial_hair_annotation_v1'

class AnalysisError(RuntimeError): pass
def fail(x): raise AnalysisError(x)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''): h.update(b)
 return h.hexdigest()
def rcsv(p):
 with p.open(newline='',encoding='utf-8-sig') as f:
  r=csv.DictReader(f); return list(r.fieldnames or []),list(r)
def wcsv(p,fields,rows):
 with p.open('x',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='raise'); w.writeheader(); w.writerows(rows)
def fnum(x): return '' if x is None or (isinstance(x,float) and math.isnan(x)) else f'{x:.10f}'
def opt(x): return None if x in ('',None) else float(x)
def mean(xs): return statistics.mean(xs) if xs else None
def median(xs): return statistics.median(xs) if xs else None
def span(xs): return (min(xs),max(xs)) if xs else (None,None)
def bools(x): return str(bool(x)).lower()

def verify_inputs():
 if sha(MASTER)!=EXPECTED_MASTER: fail('master freeze hash mismatch')
 master=json.loads(MASTER.read_text()); artifacts=master['artifacts']
 for key in ('analysis_plan','attribute_metric_protocol','generation_manifest'):
  p=Path(artifacts[key]['path'])
  if p.stat().st_size!=artifacts[key]['size_bytes'] or sha(p)!=artifacts[key]['sha256']: fail(f'frozen artifact mismatch: {key}')
 plan=json.loads(Path(artifacts['analysis_plan']['path']).read_text()); protocol=json.loads(Path(artifacts['attribute_metric_protocol']['path']).read_text())
 if plan['aggregation_order']!=['frames_to_video','four_seeds_to_reference_unit','units_to_frozen_matched_pairs'] or plan['primary_estimand']!='finite-panel mean matched positive-minus-control difference for each attribute': fail('analysis plan mismatch')
 if protocol['low_coverage_threshold']!=0.5 or protocol['facial_hair']['primary_states']!={'positive':'2','control':'0'}: fail('metric protocol mismatch')
 freeze=json.loads((MACHINE/'machine_measurement_freeze_v1.json').read_text())
 if sha(MACHINE/'output_hashes_v1.csv')!=freeze['output_hash_inventory_sha256']: fail('machine output inventory mismatch')
 _,inventory=rcsv(MACHINE/'output_hashes_v1.csv'); inv={r['relative_path']:r for r in inventory}
 for rel in ('eyeglasses_video_summary_v1.csv','identity_video_summary_v1.csv'):
  p=MACHINE/rel; r=inv[rel]
  if p.stat().st_size!=int(r['bytes']) or sha(p)!=r['sha256']: fail(f'machine input mismatch: {rel}')
 cv=json.loads((ROOT/'attribute_evaluation_v1/final_facial_hair_annotation_v1_independent_verification.json').read_text())
 if cv['status']!='PASS_INDEPENDENT_ANONYMOUS_CONSENSUS_VERIFICATION': fail('anonymous consensus not independently verified')
 _,ch=rcsv(CONSENSUS/'anonymous_consensus_hashes_v1.csv')
 for r in ch:
  p=CONSENSUS/r['relative_path']
  if p.stat().st_size!=int(r['bytes']) or sha(p)!=r['sha256']: fail(f'consensus input mismatch: {p}')
 return master,plan,protocol

def main():
 ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--output-dir',type=Path,required=True); args=ap.parse_args(); out=args.output_dir.resolve(); temp=out.with_name(out.name+'.inprogress')
 if out.exists() or temp.exists(): fail(f'refusing to overwrite output: {out}')
 temp.mkdir(parents=True,exist_ok=False)
 master,plan,protocol=verify_inputs()
 _,manifest=rcsv(Path(master['artifacts']['generation_manifest']['path'])); tasks={r['task_id']:r for r in manifest}
 if len(manifest)!=160 or len(tasks)!=160: fail('manifest universe mismatch')
 units=defaultdict(list); pairs=defaultdict(list)
 for r in manifest: units[r['formal_unit_id']].append(r); pairs[r['formal_pair_id']].append(r)
 if len(units)!=40 or len(pairs)!=20 or any(len(v)!=4 for v in units.values()) or any(len(v)!=8 for v in pairs.values()): fail('manifest blocking mismatch')
 for pair_id,rows in pairs.items():
  if {r['role'] for r in rows}!={'positive','control'} or len({r['formal_unit_id'] for r in rows})!=2 or {int(r['seed_index']) for r in rows}!={1,2,3,4}: fail(f'pair structure mismatch: {pair_id}')

 # Private mapping: exactly one byte read, then in-memory parse.
 mapping_path=MACHINE/'private_mapping_v1/facial_hair_private_mapping_v1.csv'
 mapping_bytes=mapping_path.read_bytes(); mapping_read_count=1
 if len(mapping_bytes)!=210868 or hashlib.sha256(mapping_bytes).hexdigest()!=EXPECTED_MAPPING: fail('private mapping byte/hash mismatch')
 mapping=list(csv.DictReader(io.StringIO(mapping_bytes.decode('utf-8-sig'))))
 _,final_labels=rcsv(CONSENSUS/'facial_hair_final_labels_v1.csv'); labels={r['annotation_item_id']:r for r in final_labels}
 if len(mapping)!=560 or len(labels)!=560 or {r['annotation_item_id'] for r in mapping}!=set(labels): fail('mapping/consensus universe mismatch')

 frame_fields=['schema_version','annotation_item_id','task_id','formal_unit_id','formal_pair_id','role','expected_state','seed_index','seed','frame_index','final_label','frame_status','expected_state_match','consensus_source','generated_face_status','crop_method']
 facial_frames=[]; facial_by_task=defaultdict(list)
 for m in mapping:
  task=tasks.get(m['task_id']); label=labels[m['annotation_item_id']]
  if task is None or task['attribute']!='facial_hair': fail('mapping task mismatch')
  expected='2' if task['expected_state']=='present' else '0'
  if m['expected_state']!=expected or any(m[k]!=task[k] for k in ('formal_unit_id','formal_pair_id','role','seed_index','seed')): fail('mapping metadata mismatch')
  value=label['final_label']; status='UNOBSERVABLE' if value=='U' else 'VALID_OBSERVABLE'
  row={'schema_version':1,'annotation_item_id':m['annotation_item_id'],'task_id':m['task_id'],'formal_unit_id':m['formal_unit_id'],'formal_pair_id':m['formal_pair_id'],'role':m['role'],'expected_state':expected,'seed_index':m['seed_index'],'seed':m['seed'],'frame_index':m['frame_index'],'final_label':value,'frame_status':status,'expected_state_match':'' if value=='U' else bools(value==expected),'consensus_source':label['consensus_source'],'generated_face_status':m['generated_face_status'],'crop_method':m['crop_method']}
  facial_frames.append(row); facial_by_task[m['task_id']].append(row)
 if set(facial_by_task)!={k for k,v in tasks.items() if v['attribute']=='facial_hair'} or any(sorted(int(x['frame_index']) for x in v)!=[0,8,16,24,32,40,48] for v in facial_by_task.values()): fail('facial frame universe mismatch')
 wcsv(temp/'facial_hair_frame_ledger_v1.csv',frame_fields,sorted(facial_frames,key=lambda x:(x['task_id'],int(x['frame_index']))))

 video_fields=['schema_version','task_id','formal_unit_id','formal_pair_id','attribute','role','expected_state','seed_index','seed','planned_frames','valid_frames','unobservable_frames','pipeline_failure_frames','valid_frame_fraction','low_coverage_flag','primary_expected_state_score','expected_state_match_fraction','mean_signed_expected_state_margin','ordinal_mean','label_2_fraction','summary_status']
 videos=[]
 _,eyes=rcsv(MACHINE/'eyeglasses_video_summary_v1.csv')
 if len(eyes)!=80: fail('eyeglasses video count mismatch')
 for e in eyes:
  t=tasks[e['task_id']]
  if t['attribute']!='eyeglasses' or any(e[k]!=t[k] for k in ('formal_unit_id','formal_pair_id','role','expected_state','seed_index','seed')): fail('eyeglasses metadata mismatch')
  videos.append({'schema_version':1,'task_id':e['task_id'],'formal_unit_id':e['formal_unit_id'],'formal_pair_id':e['formal_pair_id'],'attribute':'eyeglasses','role':e['role'],'expected_state':e['expected_state'],'seed_index':e['seed_index'],'seed':e['seed'],'planned_frames':49,'valid_frames':e['valid_frames'],'unobservable_frames':e['unobservable_frames'],'pipeline_failure_frames':e['pipeline_failure_frames'],'valid_frame_fraction':e['valid_frame_fraction'],'low_coverage_flag':e['low_coverage_flag'],'primary_expected_state_score':e['mean_expected_state_probability'],'expected_state_match_fraction':e['expected_state_match_fraction'],'mean_signed_expected_state_margin':e['mean_signed_expected_state_margin'],'ordinal_mean':'','label_2_fraction':'','summary_status':e['summary_status']})
 for task_id,rows in facial_by_task.items():
  t=tasks[task_id]; valid=[r for r in rows if r['frame_status']=='VALID_OBSERVABLE']; vals=[int(r['final_label']) for r in valid]; expected='2' if t['expected_state']=='present' else '0'; n=len(valid); coverage=n/7
  primary=sum(r['final_label']==expected for r in valid)/n if n else None
  videos.append({'schema_version':1,'task_id':task_id,'formal_unit_id':t['formal_unit_id'],'formal_pair_id':t['formal_pair_id'],'attribute':'facial_hair','role':t['role'],'expected_state':t['expected_state'],'seed_index':t['seed_index'],'seed':t['seed'],'planned_frames':7,'valid_frames':n,'unobservable_frames':7-n,'pipeline_failure_frames':0,'valid_frame_fraction':fnum(coverage),'low_coverage_flag':bools(coverage<0.5),'primary_expected_state_score':fnum(primary),'expected_state_match_fraction':fnum(primary),'mean_signed_expected_state_margin':'','ordinal_mean':fnum(mean(vals)),'label_2_fraction':fnum(sum(x==2 for x in vals)/n if n else None),'summary_status':'COMPLETE' if n else 'NO_VALID_FRAMES'})
 if len(videos)!=160 or len({r['task_id'] for r in videos})!=160: fail('normalized video universe mismatch')
 videos.sort(key=lambda x:x['task_id']); wcsv(temp/'attribute_video_summary_v1.csv',video_fields,videos); video_by={r['task_id']:r for r in videos}

 unit_fields=['schema_version','formal_unit_id','formal_pair_id','attribute','role','expected_state','planned_seeds','valid_video_scores','planned_frames','valid_frames','unobservable_frames','pipeline_failure_frames','valid_frame_fraction','low_coverage_flag','primary_score_mean_across_seeds','primary_score_median_across_seeds','primary_score_min_across_seeds','primary_score_max_across_seeds','expected_match_mean_across_seeds','mean_signed_margin_across_seeds','ordinal_mean_across_seeds','label_2_fraction_across_seeds','unit_status']
 unit_rows=[]
 for unit_id,mrows in sorted(units.items()):
  vv=[video_by[x['task_id']] for x in sorted(mrows,key=lambda x:int(x['seed_index']))]; meta=mrows[0]
  primary=[float(x['primary_expected_state_score']) for x in vv if x['primary_expected_state_score']!='']; lo,hi=span(primary); planned=sum(int(x['planned_frames']) for x in vv); valid=sum(int(x['valid_frames']) for x in vv); unobs=sum(int(x['unobservable_frames']) for x in vv); failures=sum(int(x['pipeline_failure_frames']) for x in vv); cov=valid/planned
  def avgfield(name): return mean([float(x[name]) for x in vv if x[name]!=''])
  unit_rows.append({'schema_version':1,'formal_unit_id':unit_id,'formal_pair_id':meta['formal_pair_id'],'attribute':meta['attribute'],'role':meta['role'],'expected_state':meta['expected_state'],'planned_seeds':4,'valid_video_scores':len(primary),'planned_frames':planned,'valid_frames':valid,'unobservable_frames':unobs,'pipeline_failure_frames':failures,'valid_frame_fraction':fnum(cov),'low_coverage_flag':bools(cov<0.5),'primary_score_mean_across_seeds':fnum(mean(primary)),'primary_score_median_across_seeds':fnum(median(primary)),'primary_score_min_across_seeds':fnum(lo),'primary_score_max_across_seeds':fnum(hi),'expected_match_mean_across_seeds':fnum(avgfield('expected_state_match_fraction')),'mean_signed_margin_across_seeds':fnum(avgfield('mean_signed_expected_state_margin')),'ordinal_mean_across_seeds':fnum(avgfield('ordinal_mean')),'label_2_fraction_across_seeds':fnum(avgfield('label_2_fraction')),'unit_status':'COMPLETE' if len(primary)==4 else ('PARTIAL_VALID_ONLY' if primary else 'NO_VALID_SCORE')})
 if len(unit_rows)!=40: fail('unit count mismatch')
 wcsv(temp/'attribute_reference_unit_summary_v1.csv',unit_fields,unit_rows); unit_by={r['formal_unit_id']:r for r in unit_rows}

 pair_fields=['schema_version','formal_pair_id','attribute','positive_unit_id','control_unit_id','positive_primary_score','control_primary_score','primary_positive_minus_control','positive_valid_frame_fraction','control_valid_frame_fraction','positive_low_coverage_flag','control_low_coverage_flag','pair_status']
 pair_rows=[]
 seed_fields=['schema_version','formal_pair_id','attribute','seed_index','seed','positive_task_id','control_task_id','positive_primary_score','control_primary_score','primary_positive_minus_control','pair_seed_status']
 seed_rows=[]
 for pair_id,mrows in sorted(pairs.items()):
  uid={r['role']:r['formal_unit_id'] for r in mrows}; pos,ctrl=unit_by[uid['positive']],unit_by[uid['control']]
  ps,cs=opt(pos['primary_score_mean_across_seeds']),opt(ctrl['primary_score_mean_across_seeds']); diff=None if ps is None or cs is None else ps-cs
  pair_rows.append({'schema_version':1,'formal_pair_id':pair_id,'attribute':pos['attribute'],'positive_unit_id':pos['formal_unit_id'],'control_unit_id':ctrl['formal_unit_id'],'positive_primary_score':fnum(ps),'control_primary_score':fnum(cs),'primary_positive_minus_control':fnum(diff),'positive_valid_frame_fraction':pos['valid_frame_fraction'],'control_valid_frame_fraction':ctrl['valid_frame_fraction'],'positive_low_coverage_flag':pos['low_coverage_flag'],'control_low_coverage_flag':ctrl['low_coverage_flag'],'pair_status':'COMPLETE' if diff is not None else 'INCOMPLETE_VALID_ONLY_NO_IMPUTATION'})
  for si in range(1,5):
   selected=[r for r in mrows if int(r['seed_index'])==si]; d={r['role']:video_by[r['task_id']] for r in selected}; pscore=opt(d['positive']['primary_expected_state_score']); cscore=opt(d['control']['primary_expected_state_score']); delta=None if pscore is None or cscore is None else pscore-cscore
   if d['positive']['seed']!=d['control']['seed']: fail('shared seed mismatch')
   seed_rows.append({'schema_version':1,'formal_pair_id':pair_id,'attribute':pos['attribute'],'seed_index':si,'seed':d['positive']['seed'],'positive_task_id':d['positive']['task_id'],'control_task_id':d['control']['task_id'],'positive_primary_score':fnum(pscore),'control_primary_score':fnum(cscore),'primary_positive_minus_control':fnum(delta),'pair_seed_status':'COMPLETE' if delta is not None else 'INCOMPLETE_VALID_ONLY_NO_IMPUTATION'})
 wcsv(temp/'attribute_pair_contrasts_v1.csv',pair_fields,pair_rows); wcsv(temp/'attribute_seed_specific_pair_contrasts_v1.csv',seed_fields,seed_rows)

 finite_fields=['schema_version','attribute','planned_pairs','valid_pair_contrasts','planned_units','low_coverage_units','planned_videos','low_coverage_videos','planned_frames','valid_frames','unobservable_frames','pipeline_failure_frames','valid_frame_fraction','mean_matched_positive_minus_control','median_matched_positive_minus_control','minimum_matched_positive_minus_control','maximum_matched_positive_minus_control','exact_randomization_test_performed','population_inference_performed','summary_status']
 finite=[]
 for attribute in ('eyeglasses','facial_hair'):
  pp=[r for r in pair_rows if r['attribute']==attribute]; uu=[r for r in unit_rows if r['attribute']==attribute]; vv=[r for r in videos if r['attribute']==attribute]; diffs=[float(r['primary_positive_minus_control']) for r in pp if r['primary_positive_minus_control']!='']; lo,hi=span(diffs); planned=sum(int(r['planned_frames']) for r in vv); valid=sum(int(r['valid_frames']) for r in vv); unobs=sum(int(r['unobservable_frames']) for r in vv); failures=sum(int(r['pipeline_failure_frames']) for r in vv)
  finite.append({'schema_version':1,'attribute':attribute,'planned_pairs':10,'valid_pair_contrasts':len(diffs),'planned_units':20,'low_coverage_units':sum(r['low_coverage_flag']=='true' for r in uu),'planned_videos':80,'low_coverage_videos':sum(r['low_coverage_flag']=='true' for r in vv),'planned_frames':planned,'valid_frames':valid,'unobservable_frames':unobs,'pipeline_failure_frames':failures,'valid_frame_fraction':fnum(valid/planned),'mean_matched_positive_minus_control':fnum(mean(diffs)),'median_matched_positive_minus_control':fnum(median(diffs)),'minimum_matched_positive_minus_control':fnum(lo),'maximum_matched_positive_minus_control':fnum(hi),'exact_randomization_test_performed':'false','population_inference_performed':'false','summary_status':'COMPLETE_FINITE_PANEL' if len(diffs)==10 else 'PARTIAL_VALID_ONLY_FINITE_PANEL'})
 wcsv(temp/'attribute_finite_panel_summary_v1.csv',finite_fields,finite)

 _,identity=rcsv(MACHINE/'identity_video_summary_v1.csv'); identity_by={r['task_id']:r for r in identity}
 if len(identity_by)!=160: fail('identity video universe mismatch')
 id_unit_fields=['schema_version','formal_unit_id','formal_pair_id','attribute','role','planned_videos','valid_video_scores','planned_frames','valid_frames','valid_frame_fraction','low_coverage_flag','mean_video_cosine_across_seeds','median_video_cosine_across_seeds','minimum_video_cosine_across_seeds','maximum_video_cosine_across_seeds','diagnostic_status']
 id_units=[]
 for unit_id,mrows in sorted(units.items()):
  rr=[identity_by[x['task_id']] for x in mrows]; vals=[float(x['mean_cosine_similarity']) for x in rr if x['mean_cosine_similarity']!='']; lo,hi=span(vals); valid=sum(int(x['valid_frames']) for x in rr); meta=mrows[0]
  id_units.append({'schema_version':1,'formal_unit_id':unit_id,'formal_pair_id':meta['formal_pair_id'],'attribute':meta['attribute'],'role':meta['role'],'planned_videos':4,'valid_video_scores':len(vals),'planned_frames':196,'valid_frames':valid,'valid_frame_fraction':fnum(valid/196),'low_coverage_flag':bools(valid/196<0.5),'mean_video_cosine_across_seeds':fnum(mean(vals)),'median_video_cosine_across_seeds':fnum(median(vals)),'minimum_video_cosine_across_seeds':fnum(lo),'maximum_video_cosine_across_seeds':fnum(hi),'diagnostic_status':'COMPLETE' if len(vals)==4 else ('PARTIAL_VALID_ONLY' if vals else 'NO_VALID_SCORE')})
 wcsv(temp/'identity_reference_unit_summary_v1.csv',id_unit_fields,id_units); id_by={r['formal_unit_id']:r for r in id_units}
 id_pair_fields=['schema_version','formal_pair_id','attribute','positive_unit_id','control_unit_id','positive_mean_cosine','control_mean_cosine','positive_minus_control_cosine','pair_diagnostic_status']
 id_pairs=[]
 for pair_id,mrows in sorted(pairs.items()):
  uid={r['role']:r['formal_unit_id'] for r in mrows}; p=id_by[uid['positive']]; c=id_by[uid['control']]; pv=opt(p['mean_video_cosine_across_seeds']); cv=opt(c['mean_video_cosine_across_seeds']); d=None if pv is None or cv is None else pv-cv
  id_pairs.append({'schema_version':1,'formal_pair_id':pair_id,'attribute':p['attribute'],'positive_unit_id':p['formal_unit_id'],'control_unit_id':c['formal_unit_id'],'positive_mean_cosine':fnum(pv),'control_mean_cosine':fnum(cv),'positive_minus_control_cosine':fnum(d),'pair_diagnostic_status':'COMPLETE' if d is not None else 'INCOMPLETE_VALID_ONLY_NO_IMPUTATION'})
 wcsv(temp/'identity_pair_diagnostics_v1.csv',id_pair_fields,id_pairs)

 commit=subprocess.check_output(['git','-C',str(Path(__file__).resolve().parents[1]),'rev-parse','HEAD'],text=True).strip()
 summary={'schema_version':1,'result_id':'formal_finite_panel_descriptive_results_v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'claim_boundary':plan['claim_boundary'],'primary_estimand':plan['primary_estimand'],'aggregation_order':plan['aggregation_order'],'attribute_summaries':finite,'exact_randomization_test_performed':False,'cross_attribute_rank_test_performed':False,'population_inference_performed':False,'causal_inference_performed':False,'scientific_interpretation_performed':False,'status':'DESCRIPTIVE_RESULTS_COMPUTED_PENDING_INDEPENDENT_VERIFICATION_AND_RESEARCHER_REVIEW'}
 (temp/'formal_descriptive_results_v1.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
 audit={'schema_version':1,'audit_id':'formal_analysis_execution_v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'analysis_code_commit':commit,'analysis_script_sha256':sha(Path(__file__).resolve()),'master_freeze_sha256':EXPECTED_MASTER,'private_mapping_sha256':EXPECTED_MAPPING,'private_mapping_byte_reads':mapping_read_count,'private_mapping_bytes':len(mapping_bytes),'input_counts':{'manifest_tasks':160,'facial_hair_consensus_items':560,'eyeglasses_videos':80,'identity_videos':160},'output_counts':{'facial_hair_frames':len(facial_frames),'attribute_videos':len(videos),'reference_units':len(unit_rows),'matched_pairs':len(pair_rows),'seed_specific_pair_rows':len(seed_rows),'identity_units':len(id_units),'identity_pairs':len(id_pairs)},'imputation_performed':False,'outcome_dependent_exclusion_performed':False,'exact_randomization_test_performed':False,'cross_attribute_rank_test_performed':False,'scientific_interpretation_performed':False,'status':'FORMAL_ANALYSIS_COMPUTED_PENDING_INDEPENDENT_VERIFICATION_AND_RESEARCHER_REVIEW'}
 (temp/'formal_analysis_execution_audit_v1.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
 hashes=[]
 for p in sorted(x for x in temp.rglob('*') if x.is_file()):
  if p.name=='formal_analysis_hashes_v1.csv': continue
  hashes.append({'relative_path':str(p.relative_to(temp)),'bytes':p.stat().st_size,'sha256':sha(p)})
 wcsv(temp/'formal_analysis_hashes_v1.csv',['relative_path','bytes','sha256'],hashes)
 freeze={'schema_version':1,'freeze_id':'formal_descriptive_results_v1','frozen_at_utc':datetime.now(timezone.utc).isoformat(),'analysis_code_commit':commit,'master_freeze_sha256':EXPECTED_MASTER,'output_hash_inventory_sha256':sha(temp/'formal_analysis_hashes_v1.csv'),'planned_videos_retained':160,'planned_units_retained':40,'planned_pairs_retained':20,'no_imputation':True,'no_outcome_dependent_exclusion':True,'claim_boundary':plan['claim_boundary'],'status':'FROZEN_DESCRIPTIVE_RESULTS_PENDING_INDEPENDENT_VERIFICATION_AND_RESEARCHER_REVIEW'}
 (temp/'formal_analysis_freeze_v1.json').write_text(json.dumps(freeze,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
 temp.rename(out)
 print(json.dumps({'status':freeze['status'],'facial_hair_frames':len(facial_frames),'videos':len(videos),'reference_units':len(unit_rows),'matched_pairs':len(pair_rows),'seed_specific_pair_rows':len(seed_rows),'private_mapping_byte_reads':mapping_read_count,'scientific_outcomes_printed':False},indent=2))
if __name__=='__main__':
 try: main()
 except AnalysisError as e: raise SystemExit(f'FORMAL ANALYSIS FAILED: {e}')
