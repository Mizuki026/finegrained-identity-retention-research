#!/usr/bin/env python3
"""Select the detector by frozen gates and build a full anonymous technical audit."""
from __future__ import annotations
import csv,hashlib,json,math,subprocess
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
BASE=Path('/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/measurement_repair_v1');BENCH=BASE/'detector_benchmark_v1';CONS=BASE/'eyeglasses_consensus_v1_1';OUT=BASE/'selected_detector_v1_1';REPO=Path('/root/autodl-tmp/finegrained/research_pipeline')
MAPPING=BASE/'eyeglasses_blind_annotation_v1/private_mapping_v1/eyeglasses_private_mapping_v1.csv';FRAMES=BASE/'eyeglasses_blind_annotation_v1/anonymous_frames'
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
def wjson(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
def square(box,w,h):
 x0,y0,x1,y1=box;side=min(max(1.35*(x1-x0),1.35*(y1-y0)),min(w,h));size=round(side);x=max(0,min(round((x0+x1)/2-side/2),w-size));y=max(0,min(round((y0+y1)/2-side/2),h-size));return x,y,x+size,y+size
def main():
 req(not OUT.exists() and not OUT.with_name(OUT.name+'.inprogress').exists(),'output exists')
 verify=json.loads((BASE/'eyeglasses_consensus_v1_1_independent_verification.json').read_text());req(verify['status']=='PASS_INDEPENDENT_ANONYMOUS_EYEGLASSES_CONSENSUS_VERIFICATION','consensus not verified')
 bverify=json.loads((BASE/'detector_benchmark_v1_independent_verification.json').read_text());req(bverify['status']=='PASS_INDEPENDENT_DETECTOR_BENCHMARK_VERIFICATION','benchmark not verified')
 req(subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True)=='','dirty repo');committed=REPO/'src/select_detector_and_build_technical_audit_v1_1.py';req(committed.is_file() and sha(committed)==sha(Path(__file__)),'uncommitted script');commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
 protocol=json.loads((BASE/'measurement_repair_protocol_v1.json').read_text());defs={x['candidate_id']:x for x in protocol['candidate_detectors']};summary={r['candidate_id']:r for r in rcsv(BENCH/'detector_candidate_summary_v1.csv')};details=rcsv(BENCH/'detector_item_results_v1.csv')
 consensus={r['annotation_item_id']:r for r in rcsv(CONS/'eyeglasses_final_consensus_v1_1.csv')};mapping={r['annotation_item_id']:r for r in rcsv(MAPPING)};req(len(consensus)==len(mapping)==560 and set(consensus)==set(mapping),'private mapping join mismatch')
 observable={mapping[i]['evaluation_item_id'] for i,r in consensus.items() if r['final_face_eye_region_observable_yes_no']=='yes'};unobservable={mapping[i]['evaluation_item_id'] for i,r in consensus.items() if r['final_face_eye_region_observable_yes_no']=='no'};req(observable and len(observable)+len(unobservable)==560,'consensus universe error')
 by={c:{} for c in defs}
 for r in details:
  if r['source_kind']=='eyeglasses_sample_frame':by[r['candidate_id']][r['evaluation_item_id']]=r
 rows=[]
 for cid,d in defs.items():
  s=summary[cid];det=sum(by[cid][i]['detected']=='true' for i in observable);eye=det/len(observable);u=sum(by[cid][i]['detected']=='true' for i in unobservable);ref=float(s['reference_recall']);fac=float(s['facial_hair_human_observable_recall']);score=min(ref,fac,eye);eligible=s['preliminary_eligible']=='true' and eye>=protocol['final_detector_eligibility_after_eye_annotation']['human_observable_eyeglasses_frame_recall_minimum']
  rows.append({'candidate_id':cid,'family':d['family'],'reference_recall':f'{ref:.10f}','facial_hair_human_observable_recall':f'{fac:.10f}','eyeglasses_human_observable_detected':det,'eyeglasses_human_observable_items':len(observable),'eyeglasses_human_observable_recall':f'{eye:.10f}','eyeglasses_U_detected':u,'eyeglasses_U_items':len(unobservable),'selection_score':f'{score:.10f}','preliminary_eligible':s['preliminary_eligible'],'final_eligible':str(eligible).lower()})
 eligible=[r for r in rows if r['final_eligible']=='true'];req(eligible,'no eligible detector')
 def rank(r):
  d=defs[r['candidate_id']];threshold=float(d.get('score_threshold',-1));size=d.get('det_size',[10**9])[0] if isinstance(d.get('det_size'),list) else 10**9;return(-float(r['selection_score']),-threshold,size,r['candidate_id'])
 eligible.sort(key=rank);selected=eligible[0]['candidate_id']
 tmp=OUT.with_name(OUT.name+'.inprogress');tmp.mkdir(parents=True);wcsv(tmp/'detector_final_eligibility_v1_1.csv',list(rows[0]),rows)
 audit=[]
 for item in sorted(consensus):
  eid=mapping[item]['evaluation_item_id'];r=by[selected][eid]
  audit.append({'annotation_item_id':item,'selected_detector':selected,'detected':r['detected'],'bbox_x1':r['bbox_x1'],'bbox_y1':r['bbox_y1'],'bbox_x2':r['bbox_x2'],'bbox_y2':r['bbox_y2'],'bbox_area_fraction':r['bbox_area_fraction'],'correct_face_bbox_yes_no':'','expanded_crop_contains_face_and_eye_region_yes_no':'','technical_status_pass_fail':'','review_note':''})
 wcsv(tmp/'selected_detector_technical_audit_template_v1_1.csv',list(audit[0]),audit)
 sheets=tmp/'technical_audit_contact_sheets';sheets.mkdir();font=ImageFont.load_default();cols,nrows,cw,ch=7,8,330,255
 for page_no,start in enumerate(range(0,560,56),1):
  page=Image.new('RGB',(cols*cw,nrows*ch),'white');draw=ImageDraw.Draw(page)
  for off,r in enumerate(audit[start:start+56]):
   x,y=(off%cols)*cw,(off//cols)*ch;draw.rectangle((x,y,x+cw-1,y+ch-1),outline='#707070',width=2);draw.text((x+5,y+5),f"{r['annotation_item_id']} | detected={r['detected']}",fill='black',font=font)
   with Image.open(FRAMES/f"{r['annotation_item_id']}.png") as z:im=z.convert('RGB')
   if r['detected']=='true':
    box=tuple(float(r[k]) for k in ('bbox_x1','bbox_y1','bbox_x2','bbox_y2'));d=ImageDraw.Draw(im);d.rectangle(box,outline='#00ff00',width=4);d.rectangle(square(box,*im.size),outline='#0080ff',width=4)
   else:ImageDraw.Draw(im).text((10,10),'NO DETECTION',fill='red',font=font)
   im.thumbnail((cw-12,ch-34),Image.Resampling.LANCZOS);page.paste(im,(x+(cw-im.width)//2,y+28+(ch-28-im.height)//2))
  page.save(sheets/f'selected_detector_technical_audit_{page_no:02d}_of_10_v1_1.png',format='PNG',optimize=True)
 codebook='''SELECTED DETECTOR TECHNICAL AUDIT V1.1\n\nReview all 560 anonymous frames independently of attribute label.\nGreen rectangle: raw selected face detection. Blue rectangle: deterministic 1.35x square crop used by the repaired metric.\nFill correct_face_bbox_yes_no and expanded_crop_contains_face_and_eye_region_yes_no with yes/no.\ntechnical_status_pass_fail is pass only when detected=true and both judgments are yes; otherwise fail.\nA note is required for every fail. Do not access private mapping. This audit cannot trigger outcome-dependent detector substitution or selective frame exclusion.\n''';(tmp/'selected_detector_technical_audit_codebook_v1_1.txt').write_text(codebook)
 record={'schema_version':1,'selection_id':'formal_measurement_repair_detector_selection_v1_1','selected_at_utc':datetime.now(timezone.utc).isoformat(),'selected_candidate_id':selected,'eligible_candidates':len(eligible),'human_observable_eyeglasses_frames':len(observable),'unobservable_eyeglasses_frames':len(unobservable),'selection_rule':protocol['final_detector_eligibility_after_eye_annotation'],'private_mapping_accessed_after_consensus_freeze':True,'detector_substitution_after_technical_audit_allowed':False,'selective_frame_exclusion_allowed':False,'automated_repaired_metric_started':False,'technical_audit_items':560,'status':'SELECTED_PENDING_FULL_TECHNICAL_AUDIT'};wjson(tmp/'detector_selection_record_v1_1.json',record)
 fr={'schema_version':1,'freeze_id':'formal_measurement_repair_selected_detector_v1_1_freeze','frozen_at_utc':datetime.now(timezone.utc).isoformat(),'repository_commit':commit,'script_sha256':sha(Path(__file__)),'consensus_verification_sha256':sha(BASE/'eyeglasses_consensus_v1_1_independent_verification.json'),'benchmark_verification_sha256':sha(BASE/'detector_benchmark_v1_independent_verification.json'),'private_mapping_sha256':sha(MAPPING),'eligibility_sha256':sha(tmp/'detector_final_eligibility_v1_1.csv'),'selection_record_sha256':sha(tmp/'detector_selection_record_v1_1.json'),'technical_audit_template_sha256':sha(tmp/'selected_detector_technical_audit_template_v1_1.csv'),'selected_candidate_id':selected,'technical_audit_started':False,'status':record['status']};wjson(tmp/'selected_detector_freeze_v1_1.json',fr);tmp.rename(OUT)
 print(json.dumps({'status':fr['status'],'selected_candidate_id':selected,'eligible_candidates':len(eligible),'human_observable_eyeglasses_frames':len(observable),'technical_audit_items':560,'contact_sheet_pages':10},indent=2))
if __name__=='__main__':
 try:main()
 except E as e:raise SystemExit(f'DETECTOR SELECTION FAILED: {e}')
