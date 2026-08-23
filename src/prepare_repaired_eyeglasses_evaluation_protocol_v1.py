#!/usr/bin/env python3
"""Freeze the repaired eyeglasses measurement protocol before scoring."""
from __future__ import annotations
import csv, hashlib, json, subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path('/root/autodl-tmp/finegrained'); REPO=ROOT/'research_pipeline'
RUNTIME=ROOT/'formal_experiment_v1_runtime'; REPAIR=RUNTIME/'measurement_repair_v1'
OUT=REPAIR/'repaired_eyeglasses_evaluation_protocol_v1'; RESULT=REPAIR/'repaired_eyeglasses_evaluation_v1'
CONSENSUS=REPAIR/'eyeglasses_consensus_v1_1'; TECH=REPAIR/'selected_detector_technical_audit_final_v1_1'
SOURCE_PROTOCOL=RUNTIME/'experiment_freeze_v1/source_attribute_metric_protocol_v2_1.json'
CLIP=ROOT/'metric_models_v2/clip-vit-base-patch32/pytorch_model.bin'
EVALUATOR=REPO/'src/formal_measurement_repair_evaluation_v1.py'; VERIFIER=REPO/'src/verify_formal_measurement_repair_evaluation_v1.py'
EXPECTED={
 'consensus_freeze':'7e913e588a9f3c53ef37da1a0abb03f65a20108f81be72278e882fcd74517e8d',
 'consensus_verification':'2d540a3a8d8902130be19ae61ff5a62281cdccab0d8ed66fd5e4d7385066509a',
 'technical_audit_freeze':'55f33e8c2579b2bbbf910e3f4f57000e7a32f9b9d2bd9638286480f55987afe4',
 'technical_audit_verification':'56c5225a213878ac1aed8f86655ab24aea1b3fcfc9cd83f341cc9bb645bbd0ec',
 'source_metric_protocol':'58e85a206838de08c141f69e333d901a48f35eeefbbe50044f17d5a4d600b4c7',
 'clip_pytorch_model':'a63082132ba4f97a80bea76823f544493bffa8082296d62d71581a4feff1576f'}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''): h.update(b)
 return h.hexdigest()
def rows(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def require(x,m):
 if not x: raise RuntimeError(m)
def write_json_new(p,v):
 with p.open('x',encoding='utf-8') as f: json.dump(v,f,indent=2,ensure_ascii=False,sort_keys=True);f.write('\n')
def main():
 require(not OUT.exists(),'protocol output exists'); require(not RESULT.exists(),'scoring output exists')
 require(subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True)=='','dirty repository')
 commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
 paths={
  'consensus_freeze':CONSENSUS/'eyeglasses_consensus_freeze_v1_1.json',
  'consensus_verification':REPAIR/'eyeglasses_consensus_v1_1_independent_verification.json',
  'technical_audit_freeze':TECH/'selected_detector_technical_audit_freeze_v1_1.json',
  'technical_audit_verification':REPAIR/'selected_detector_technical_audit_final_v1_1_independent_verification.json',
  'source_metric_protocol':SOURCE_PROTOCOL,'clip_pytorch_model':CLIP}
 for k,p in paths.items(): require(p.is_file() and not p.is_symlink(),f'missing {p}');require(sha(p)==EXPECTED[k],f'hash mismatch {k}')
 require(EVALUATOR.is_file() and VERIFIER.is_file(),'evaluator/verifier missing')
 cf=json.loads(paths['consensus_freeze'].read_text());cv=json.loads(paths['consensus_verification'].read_text())
 tf=json.loads(paths['technical_audit_freeze'].read_text());tv=json.loads(paths['technical_audit_verification'].read_text())
 require(cv['status']=='PASS_INDEPENDENT_ANONYMOUS_EYEGLASSES_CONSENSUS_VERIFICATION','consensus not verified')
 require(tf['status']=='FROZEN_TECHNICAL_AUDIT_WITH_7_FAILURES_NO_SUBSTITUTION_NO_EXCLUSION','technical audit not frozen')
 require(tv['status']=='PASS_INDEPENDENT_SELECTED_DETECTOR_TECHNICAL_AUDIT_VERIFICATION','technical audit not verified')
 consensus=rows(CONSENSUS/'eyeglasses_final_consensus_v1_1.csv'); technical=rows(TECH/'selected_detector_technical_audit_final_v1_1.csv')
 require(len(consensus)==len(technical)==560,'universe not 560')
 require({r['annotation_item_id'] for r in consensus}=={r['annotation_item_id'] for r in technical},'join mismatch')
 require(Counter(r['technical_status_pass_fail'] for r in technical)=={'pass':553,'fail':7},'technical counts drift')
 source=json.loads(SOURCE_PROTOCOL.read_text())['eyeglasses']
 protocol={
  'schema_version':1,'protocol_id':'formal_repaired_eyeglasses_evaluation_v1','frozen_at_utc':datetime.now(timezone.utc).isoformat(),
  'classification':'secondary_post_hoc_measurement_validation_and_sensitivity_evidence',
  'fixed_universe':{'videos':80,'frames_per_video':7,'frames':560,'frame_indices':[0,8,16,24,32,40,48]},
  'human_measurement':{'source':'independent blinded two-annotator consensus with third-researcher adjudication','labels':['present','absent','U'],'observable_values':['present','absent'],'primary_finite_panel_outcome':'per-video present-frame fraction among human-observable fixed frames','unobservable_policy':'retain row; exclude only from denominator; no imputation'},
  'automated_measurement':{'detector':'yunet_native_t03','detector_selection_basis':'pre-frozen coverage criteria only; no outcome/effect used','technical_pass_items':553,'technical_fail_items':7,'technical_failure_policy':'retain row as INVALID_TECHNICAL_AUDIT; leave automated values blank; no substitution, exclusion, or imputation','crop':{'source':'audited selected bounding box','shape':'square','scale':1.35,'boundary_policy':'clip to image boundaries'},'clip_instrument':source,'validation_reference':'human consensus on intersection of human-observable and technical-pass frames'},
  'descriptive_outputs':{'frame_ledger_rows':560,'video_summary_rows':80,'matched_seed_pair_rows':40,'detector_coverage_comparison':['scrfd_640_t05','yunet_native_t03','yunet_native_t03_after_technical_audit'],'no_hypothesis_tests':True,'no_confidence_intervals':True},
  'analysis_boundary':{'fixed_videos_only':True,'no_frame_independence_claim':True,'no_population_inference':True,'no_model_wide_inference':True,'no_causal_inference':True,'no_original_result_overwrite':True},
  'input_sha256':{k:sha(p) for k,p in paths.items()},
  'bound_artifact_sha256':{'consensus_csv':cf['consensus_sha256'],'technical_audit_csv':tf['final_audit_sha256'],'evaluator_script':sha(EVALUATOR),'independent_verifier_script':sha(VERIFIER)},
  'repository_commit':commit,'generation_performed':False,'scoring_started_before_freeze':False,'status':'FROZEN_BEFORE_REPAIRED_SCORING'}
 OUT.mkdir(); pp=OUT/'repaired_eyeglasses_evaluation_protocol_v1.json';write_json_new(pp,protocol)
 write_json_new(OUT/'repaired_eyeglasses_evaluation_protocol_freeze_v1.json',{'schema_version':1,'freeze_id':'formal_repaired_eyeglasses_evaluation_protocol_v1_freeze','protocol_sha256':sha(pp),'repository_commit':commit,'evaluator_script_sha256':sha(EVALUATOR),'independent_verifier_script_sha256':sha(VERIFIER),'status':'FROZEN_BEFORE_REPAIRED_SCORING'})
 print(json.dumps({'status':protocol['status'],'protocol':str(pp),'items':560},indent=2))
if __name__=='__main__':main()
