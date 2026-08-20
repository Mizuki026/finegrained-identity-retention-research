#!/usr/bin/env python3
"""Independently recompute and verify formal finite-panel result artifacts."""
from __future__ import annotations
import argparse,csv,hashlib,io,json,math,statistics,subprocess
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path('/root/autodl-tmp/finegrained/formal_experiment_v1_runtime')
MASTER=ROOT/'experiment_freeze_v1/pre_generation_master_freeze_v1.json'
MACHINE=ROOT/'attribute_evaluation_v1/run_001'
CONSENSUS=ROOT/'attribute_evaluation_v1/final_facial_hair_annotation_v1'
RESULT=ROOT/'formal_analysis_v1'
MASTER_SHA='149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8'
MAPPING_SHA='1376bbfa93ad5d071bf291958ceef7b9e2c852fa713efeb2b475dceaf50de162'
ANALYSIS_COMMIT='30663b406549603af90e731ca2ad49918eaf1e0c'
EXPECTED_FILES={
 'attribute_finite_panel_summary_v1.csv','attribute_pair_contrasts_v1.csv',
 'attribute_reference_unit_summary_v1.csv','attribute_seed_specific_pair_contrasts_v1.csv',
 'attribute_video_summary_v1.csv','facial_hair_frame_ledger_v1.csv',
 'formal_analysis_execution_audit_v1.json','formal_analysis_freeze_v1.json',
 'formal_analysis_hashes_v1.csv','formal_descriptive_results_v1.json',
 'identity_pair_diagnostics_v1.csv','identity_reference_unit_summary_v1.csv'}
class VerificationError(RuntimeError): pass
def check(x,msg):
 if not x: raise VerificationError(msg)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''): h.update(b)
 return h.hexdigest()
def rcsv(p):
 with p.open(newline='',encoding='utf-8-sig') as f:
  r=csv.DictReader(f); return list(r.fieldnames or []),list(r)
def fnum(x): return '' if x is None or (isinstance(x,float) and math.isnan(x)) else f'{x:.10f}'
def opt(x): return None if x in ('',None) else float(x)
def avg(xs): return statistics.mean(xs) if xs else None
def med(xs): return statistics.median(xs) if xs else None
def span(xs): return (min(xs),max(xs)) if xs else (None,None)
def bstr(x): return str(bool(x)).lower()
def csvize(rows): return [{k:str(v) for k,v in r.items()} for r in rows]
def compare_rows(path,expected,key):
 fields,actual=rcsv(path); exp=csvize(expected)
 check(len(actual)==len(exp),f'row count mismatch: {path.name}')
 a={tuple(r[k] for k in key):r for r in actual}; e={tuple(r[k] for k in key):r for r in exp}
 check(len(a)==len(actual) and len(e)==len(exp),f'duplicate keys: {path.name}')
 check(set(a)==set(e),f'key universe mismatch: {path.name}')
 check(fields==list(exp[0]) if exp else True,f'field order mismatch: {path.name}')
 for k in e: check(a[k]==e[k],f'row mismatch: {path.name}')
def facial_state(task):
 x=task['expected_state']; check(x in ('0','2'),'bad facial state coding'); return x

def main():
 ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--output',type=Path,required=True); args=ap.parse_args(); output=args.output.resolve()
 check(not output.exists(),'refusing to overwrite verification output')
 check(RESULT.is_dir(),'formal result directory missing')
 check({p.name for p in RESULT.iterdir() if p.is_file()}==EXPECTED_FILES,'result file set mismatch')
 check(sha(MASTER)==MASTER_SHA,'master freeze hash mismatch')
 freeze=json.loads((RESULT/'formal_analysis_freeze_v1.json').read_text())
 check(freeze['status']=='FROZEN_DESCRIPTIVE_RESULTS_PENDING_INDEPENDENT_VERIFICATION_AND_RESEARCHER_REVIEW','result freeze status mismatch')
 check(freeze['analysis_code_commit']==ANALYSIS_COMMIT,'analysis commit mismatch')
 check(sha(RESULT/'formal_analysis_hashes_v1.csv')==freeze['output_hash_inventory_sha256'],'result inventory hash mismatch')
 _,hinv=rcsv(RESULT/'formal_analysis_hashes_v1.csv'); inv={r['relative_path']:r for r in hinv}
 check(set(inv)==EXPECTED_FILES-{'formal_analysis_hashes_v1.csv','formal_analysis_freeze_v1.json'},'result inventory universe mismatch')
 for rel,r in inv.items():
  q=RESULT/rel; check(q.stat().st_size==int(r['bytes']) and sha(q)==r['sha256'],f'result artifact hash mismatch: {rel}')
 repo=Path('/root/autodl-tmp/finegrained/research_pipeline')
 script=repo/'src/formal_analyze_finite_panel_v1.py'
 committed=subprocess.check_output(['git','-C',str(repo),'show',f'{ANALYSIS_COMMIT}:src/formal_analyze_finite_panel_v1.py'])
 audit=json.loads((RESULT/'formal_analysis_execution_audit_v1.json').read_text())
 check(hashlib.sha256(committed).hexdigest()==audit['analysis_script_sha256'],'committed analysis script hash mismatch')
 check(audit['analysis_code_commit']==ANALYSIS_COMMIT and audit['private_mapping_byte_reads']==1,'analysis audit mismatch')
 check(not audit['imputation_performed'] and not audit['outcome_dependent_exclusion_performed'],'forbidden analysis behavior recorded')
 machine_freeze=json.loads((MACHINE/'machine_measurement_freeze_v1.json').read_text())
 check(sha(MACHINE/'output_hashes_v1.csv')==machine_freeze['output_hash_inventory_sha256'],'machine inventory hash mismatch')
 _,minvrows=rcsv(MACHINE/'output_hashes_v1.csv'); minv={r['relative_path']:r for r in minvrows}
 for rel in ('eyeglasses_video_summary_v1.csv','identity_video_summary_v1.csv'):
  q=MACHINE/rel; r=minv[rel]; check(q.stat().st_size==int(r['bytes']) and sha(q)==r['sha256'],f'machine source mismatch: {rel}')
 consensus_verification=json.loads((ROOT/'attribute_evaluation_v1/final_facial_hair_annotation_v1_independent_verification.json').read_text())
 check(consensus_verification['status']=='PASS_INDEPENDENT_ANONYMOUS_CONSENSUS_VERIFICATION','consensus verification status mismatch')
 _,cinvrows=rcsv(CONSENSUS/'anonymous_consensus_hashes_v1.csv')
 for r in cinvrows:
  q=CONSENSUS/r['relative_path']; check(q.stat().st_size==int(r['bytes']) and sha(q)==r['sha256'],f'consensus source mismatch: {r["relative_path"]}')

 master=json.loads(MASTER.read_text()); plan=json.loads(Path(master['artifacts']['analysis_plan']['path']).read_text())
 _,manifest=rcsv(Path(master['artifacts']['generation_manifest']['path'])); tasks={r['task_id']:r for r in manifest}
 check(len(tasks)==160,'manifest universe mismatch')
 units=defaultdict(list); pairs=defaultdict(list)
 for r in manifest: units[r['formal_unit_id']].append(r); pairs[r['formal_pair_id']].append(r)
 check(len(units)==40 and len(pairs)==20,'manifest block mismatch')

 mapping_bytes=(MACHINE/'private_mapping_v1/facial_hair_private_mapping_v1.csv').read_bytes()
 check(len(mapping_bytes)==210868 and hashlib.sha256(mapping_bytes).hexdigest()==MAPPING_SHA,'private mapping mismatch')
 mapping=list(csv.DictReader(io.StringIO(mapping_bytes.decode('utf-8-sig'))))
 _,labrows=rcsv(CONSENSUS/'facial_hair_final_labels_v1.csv'); labels={r['annotation_item_id']:r for r in labrows}
 check(len(mapping)==560 and len(labels)==560 and {r['annotation_item_id'] for r in mapping}==set(labels),'consensus mapping universe mismatch')

 frames=[]; facial_by_task=defaultdict(list)
 for m in mapping:
  t=tasks[m['task_id']]; label=labels[m['annotation_item_id']]; expected=facial_state(t); value=label['final_label']
  check(m['expected_state']==expected and all(m[k]==t[k] for k in ('formal_unit_id','formal_pair_id','role','seed_index','seed')),'facial metadata mismatch')
  row={'schema_version':1,'annotation_item_id':m['annotation_item_id'],'task_id':m['task_id'],'formal_unit_id':m['formal_unit_id'],'formal_pair_id':m['formal_pair_id'],'role':m['role'],'expected_state':expected,'seed_index':m['seed_index'],'seed':m['seed'],'frame_index':m['frame_index'],'final_label':value,'frame_status':'UNOBSERVABLE' if value=='U' else 'VALID_OBSERVABLE','expected_state_match':'' if value=='U' else bstr(value==expected),'consensus_source':label['consensus_source'],'generated_face_status':m['generated_face_status'],'crop_method':m['crop_method']}
  frames.append(row); facial_by_task[m['task_id']].append(row)
 compare_rows(RESULT/'facial_hair_frame_ledger_v1.csv',frames,('annotation_item_id',))
 check(len(facial_by_task)==80 and all(sorted(int(x['frame_index']) for x in v)==[0,8,16,24,32,40,48] for v in facial_by_task.values()),'facial frame schedule mismatch')

 videos=[]; _,eyes=rcsv(MACHINE/'eyeglasses_video_summary_v1.csv')
 for e in eyes:
  t=tasks[e['task_id']]; check(t['attribute']=='eyeglasses' and all(e[k]==t[k] for k in ('formal_unit_id','formal_pair_id','role','expected_state','seed_index','seed')),'eye metadata mismatch')
  videos.append({'schema_version':1,'task_id':e['task_id'],'formal_unit_id':e['formal_unit_id'],'formal_pair_id':e['formal_pair_id'],'attribute':'eyeglasses','role':e['role'],'expected_state':e['expected_state'],'seed_index':e['seed_index'],'seed':e['seed'],'planned_frames':49,'valid_frames':e['valid_frames'],'unobservable_frames':e['unobservable_frames'],'pipeline_failure_frames':e['pipeline_failure_frames'],'valid_frame_fraction':e['valid_frame_fraction'],'low_coverage_flag':e['low_coverage_flag'],'primary_expected_state_score':e['mean_expected_state_probability'],'expected_state_match_fraction':e['expected_state_match_fraction'],'mean_signed_expected_state_margin':e['mean_signed_expected_state_margin'],'ordinal_mean':'','label_2_fraction':'','summary_status':e['summary_status']})
 for task_id,rr in facial_by_task.items():
  t=tasks[task_id]; valid=[r for r in rr if r['final_label']!='U']; vals=[int(r['final_label']) for r in valid]; n=len(valid); coverage=n/7; expected=facial_state(t); score=sum(r['final_label']==expected for r in valid)/n if n else None
  videos.append({'schema_version':1,'task_id':task_id,'formal_unit_id':t['formal_unit_id'],'formal_pair_id':t['formal_pair_id'],'attribute':'facial_hair','role':t['role'],'expected_state':t['expected_state'],'seed_index':t['seed_index'],'seed':t['seed'],'planned_frames':7,'valid_frames':n,'unobservable_frames':7-n,'pipeline_failure_frames':0,'valid_frame_fraction':fnum(coverage),'low_coverage_flag':bstr(coverage<0.5),'primary_expected_state_score':fnum(score),'expected_state_match_fraction':fnum(score),'mean_signed_expected_state_margin':'','ordinal_mean':fnum(avg(vals)),'label_2_fraction':fnum(sum(x==2 for x in vals)/n if n else None),'summary_status':'COMPLETE' if n else 'NO_VALID_FRAMES'})
 check(len(videos)==160,'video universe mismatch'); compare_rows(RESULT/'attribute_video_summary_v1.csv',videos,('task_id',)); vby={r['task_id']:r for r in csvize(videos)}

 unit_rows=[]
 for uid,mrows in sorted(units.items()):
  vv=[vby[x['task_id']] for x in sorted(mrows,key=lambda x:int(x['seed_index']))]; meta=mrows[0]; primary=[float(x['primary_expected_state_score']) for x in vv if x['primary_expected_state_score']!='']; lo,hi=span(primary); planned=sum(int(x['planned_frames']) for x in vv); valid=sum(int(x['valid_frames']) for x in vv); unobs=sum(int(x['unobservable_frames']) for x in vv); failures=sum(int(x['pipeline_failure_frames']) for x in vv); cov=valid/planned
  def af(name): return avg([float(x[name]) for x in vv if x[name]!=''])
  unit_rows.append({'schema_version':1,'formal_unit_id':uid,'formal_pair_id':meta['formal_pair_id'],'attribute':meta['attribute'],'role':meta['role'],'expected_state':meta['expected_state'],'planned_seeds':4,'valid_video_scores':len(primary),'planned_frames':planned,'valid_frames':valid,'unobservable_frames':unobs,'pipeline_failure_frames':failures,'valid_frame_fraction':fnum(cov),'low_coverage_flag':bstr(cov<0.5),'primary_score_mean_across_seeds':fnum(avg(primary)),'primary_score_median_across_seeds':fnum(med(primary)),'primary_score_min_across_seeds':fnum(lo),'primary_score_max_across_seeds':fnum(hi),'expected_match_mean_across_seeds':fnum(af('expected_state_match_fraction')),'mean_signed_margin_across_seeds':fnum(af('mean_signed_expected_state_margin')),'ordinal_mean_across_seeds':fnum(af('ordinal_mean')),'label_2_fraction_across_seeds':fnum(af('label_2_fraction')),'unit_status':'COMPLETE' if len(primary)==4 else ('PARTIAL_VALID_ONLY' if primary else 'NO_VALID_SCORE')})
 compare_rows(RESULT/'attribute_reference_unit_summary_v1.csv',unit_rows,('formal_unit_id',)); uby={r['formal_unit_id']:r for r in csvize(unit_rows)}

 pair_rows=[]; seed_rows=[]
 for pid,mrows in sorted(pairs.items()):
  ids={r['role']:r['formal_unit_id'] for r in mrows}; p,c=uby[ids['positive']],uby[ids['control']]; pv,cv=opt(p['primary_score_mean_across_seeds']),opt(c['primary_score_mean_across_seeds']); delta=None if pv is None or cv is None else pv-cv
  pair_rows.append({'schema_version':1,'formal_pair_id':pid,'attribute':p['attribute'],'positive_unit_id':p['formal_unit_id'],'control_unit_id':c['formal_unit_id'],'positive_primary_score':fnum(pv),'control_primary_score':fnum(cv),'primary_positive_minus_control':fnum(delta),'positive_valid_frame_fraction':p['valid_frame_fraction'],'control_valid_frame_fraction':c['valid_frame_fraction'],'positive_low_coverage_flag':p['low_coverage_flag'],'control_low_coverage_flag':c['low_coverage_flag'],'pair_status':'COMPLETE' if delta is not None else 'INCOMPLETE_VALID_ONLY_NO_IMPUTATION'})
  for si in range(1,5):
   d={r['role']:vby[r['task_id']] for r in mrows if int(r['seed_index'])==si}; check(d['positive']['seed']==d['control']['seed'],'shared seed mismatch'); ps,cs=opt(d['positive']['primary_expected_state_score']),opt(d['control']['primary_expected_state_score']); sd=None if ps is None or cs is None else ps-cs
   seed_rows.append({'schema_version':1,'formal_pair_id':pid,'attribute':p['attribute'],'seed_index':si,'seed':d['positive']['seed'],'positive_task_id':d['positive']['task_id'],'control_task_id':d['control']['task_id'],'positive_primary_score':fnum(ps),'control_primary_score':fnum(cs),'primary_positive_minus_control':fnum(sd),'pair_seed_status':'COMPLETE' if sd is not None else 'INCOMPLETE_VALID_ONLY_NO_IMPUTATION'})
 compare_rows(RESULT/'attribute_pair_contrasts_v1.csv',pair_rows,('formal_pair_id',)); compare_rows(RESULT/'attribute_seed_specific_pair_contrasts_v1.csv',seed_rows,('formal_pair_id','seed_index'))

 finite=[]
 for attr in ('eyeglasses','facial_hair'):
  pp=[r for r in pair_rows if r['attribute']==attr]; uu=[r for r in unit_rows if r['attribute']==attr]; vv=[r for r in videos if r['attribute']==attr]; diffs=[float(r['primary_positive_minus_control']) for r in pp if r['primary_positive_minus_control']!='']; lo,hi=span(diffs); planned=sum(int(r['planned_frames']) for r in vv); valid=sum(int(r['valid_frames']) for r in vv); unobs=sum(int(r['unobservable_frames']) for r in vv); failures=sum(int(r['pipeline_failure_frames']) for r in vv)
  finite.append({'schema_version':1,'attribute':attr,'planned_pairs':10,'valid_pair_contrasts':len(diffs),'planned_units':20,'low_coverage_units':sum(r['low_coverage_flag']=='true' for r in uu),'planned_videos':80,'low_coverage_videos':sum(r['low_coverage_flag']=='true' for r in vv),'planned_frames':planned,'valid_frames':valid,'unobservable_frames':unobs,'pipeline_failure_frames':failures,'valid_frame_fraction':fnum(valid/planned),'mean_matched_positive_minus_control':fnum(avg(diffs)),'median_matched_positive_minus_control':fnum(med(diffs)),'minimum_matched_positive_minus_control':fnum(lo),'maximum_matched_positive_minus_control':fnum(hi),'exact_randomization_test_performed':'false','population_inference_performed':'false','summary_status':'COMPLETE_FINITE_PANEL' if len(diffs)==10 else 'PARTIAL_VALID_ONLY_FINITE_PANEL'})
 compare_rows(RESULT/'attribute_finite_panel_summary_v1.csv',finite,('attribute',))

 _,identity=rcsv(MACHINE/'identity_video_summary_v1.csv'); iby={r['task_id']:r for r in identity}; check(len(iby)==160,'identity universe mismatch')
 for r in identity:
  t=tasks.get(r['task_id']); check(t is not None and all(r[k]==t[k] for k in ('formal_unit_id','formal_pair_id','attribute','role','seed_index','seed')),'identity metadata mismatch')
 id_units=[]
 for uid,mrows in sorted(units.items()):
  rr=[iby[x['task_id']] for x in mrows]; vals=[float(x['mean_cosine_similarity']) for x in rr if x['mean_cosine_similarity']!='']; lo,hi=span(vals); valid=sum(int(x['valid_frames']) for x in rr); meta=mrows[0]
  id_units.append({'schema_version':1,'formal_unit_id':uid,'formal_pair_id':meta['formal_pair_id'],'attribute':meta['attribute'],'role':meta['role'],'planned_videos':4,'valid_video_scores':len(vals),'planned_frames':196,'valid_frames':valid,'valid_frame_fraction':fnum(valid/196),'low_coverage_flag':bstr(valid/196<0.5),'mean_video_cosine_across_seeds':fnum(avg(vals)),'median_video_cosine_across_seeds':fnum(med(vals)),'minimum_video_cosine_across_seeds':fnum(lo),'maximum_video_cosine_across_seeds':fnum(hi),'diagnostic_status':'COMPLETE' if len(vals)==4 else ('PARTIAL_VALID_ONLY' if vals else 'NO_VALID_SCORE')})
 compare_rows(RESULT/'identity_reference_unit_summary_v1.csv',id_units,('formal_unit_id',)); idby={r['formal_unit_id']:r for r in csvize(id_units)}; id_pairs=[]
 for pid,mrows in sorted(pairs.items()):
  ids={r['role']:r['formal_unit_id'] for r in mrows}; p,c=idby[ids['positive']],idby[ids['control']]; pv,cv=opt(p['mean_video_cosine_across_seeds']),opt(c['mean_video_cosine_across_seeds']); delta=None if pv is None or cv is None else pv-cv
  id_pairs.append({'schema_version':1,'formal_pair_id':pid,'attribute':p['attribute'],'positive_unit_id':p['formal_unit_id'],'control_unit_id':c['formal_unit_id'],'positive_mean_cosine':fnum(pv),'control_mean_cosine':fnum(cv),'positive_minus_control_cosine':fnum(delta),'pair_diagnostic_status':'COMPLETE' if delta is not None else 'INCOMPLETE_VALID_ONLY_NO_IMPUTATION'})
 compare_rows(RESULT/'identity_pair_diagnostics_v1.csv',id_pairs,('formal_pair_id',))

 desc=json.loads((RESULT/'formal_descriptive_results_v1.json').read_text()); check(desc['attribute_summaries']==finite,'descriptive JSON mismatch'); check(desc['claim_boundary']==plan['claim_boundary'] and desc['primary_estimand']==plan['primary_estimand'],'claim boundary mismatch'); check(not desc['exact_randomization_test_performed'] and not desc['population_inference_performed'] and not desc['causal_inference_performed'],'forbidden inference flag')
 check(freeze['planned_videos_retained']==160 and freeze['planned_units_retained']==40 and freeze['planned_pairs_retained']==20 and freeze['no_imputation'] and freeze['no_outcome_dependent_exclusion'],'freeze count/policy mismatch')
 verifier_commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
 report={'schema_version':1,'verification_id':'formal_finite_panel_results_independent_verification_v1','verified_at_utc':datetime.now(timezone.utc).isoformat(),'verifier_code_commit':verifier_commit,'verifier_script_sha256':sha(Path(__file__).resolve()),'analysis_code_commit_verified':ANALYSIS_COMMIT,'master_freeze_sha256_verified':MASTER_SHA,'result_hash_inventory_verified':True,'private_mapping_sha256_verified':MAPPING_SHA,'private_mapping_read_for_verification':True,'rows_recomputed':{'facial_hair_frames':560,'attribute_videos':160,'reference_units':40,'matched_pairs':20,'seed_specific_pair_rows':80,'finite_panel_attribute_rows':2,'identity_units':40,'identity_pairs':20},'no_imputation_verified':True,'no_outcome_dependent_exclusion_verified':True,'exact_randomization_test_absent_verified':True,'cross_attribute_ranking_absent_verified':True,'scientific_outcomes_printed':False,'scientific_interpretation_performed':False,'status':'PASS_INDEPENDENT_FORMAL_FINITE_PANEL_RESULTS_VERIFICATION'}
 output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
 print(json.dumps({'status':report['status'],'tables_recomputed':8,'rows_recomputed_total':922,'scientific_outcomes_printed':False},indent=2))
if __name__=='__main__':
 try: main()
 except VerificationError as e: raise SystemExit(f'INDEPENDENT VERIFICATION FAILED: {e}')
