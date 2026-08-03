#!/usr/bin/env python3
"""Derive descriptive tables and figures from immutable Pilot v1.1 evaluation v2."""
import argparse, csv, hashlib, json, os, statistics
from collections import Counter
from pathlib import Path

ROOT=Path('/root/autodl-tmp/finegrained/research_pipeline')
FRAME=ROOT/'derived/pilot_v1_1/attribute_evaluation_v2/attribute_frame_inventory_v1.csv'
SUMMARY=ROOT/'derived/pilot_v1_1/attribute_evaluation_v2/attribute_video_summary_v1.csv'
AUDIT=ROOT/'derived/pilot_v1_1/attribute_evaluation_v2/attribute_execution_audit_v1.json'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read(p):
 with open(p,newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def write(p,cols,rows):
 with open(p,'w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 if a.output.exists():raise RuntimeError(f'output exists: {a.output}')
 for p in (FRAME,SUMMARY,AUDIT):
  if not p.is_file():raise RuntimeError(f'missing {p}')
 fr,su=read(FRAME),read(SUMMARY)
 if len(fr)!=1764 or len(su)!=12 or len({r['sample_id'] for r in fr})!=12:raise RuntimeError('input schema/count mismatch')
 a.output.mkdir(parents=True)
 out=[]
 for s in su:
  if s['attribute'] not in ('eyeglasses','hair_color'):continue
  sid=s['sample_id']; rows=[r for r in fr if r['sample_id']==sid and r['attribute']==s['attribute'] and r['attribute_frame_status']=='VALID_OBSERVABLE']
  if s['attribute']=='eyeglasses':
   out.append({'sample_id':sid,'attribute':'eyeglasses','expected_condition':s['expected_label'],'valid_frames':len(rows),'coverage':s['valid_frame_fraction'],'mean_probability_present':s['metric_mean'],'sd_probability_present':s['metric_sd'],'median_probability_present':s['metric_median'],'expected_match_fraction':s['expected_label_match_fraction'],'mean_abs_delta_Lstar':'','median_abs_delta_Lstar':'','reference_Lstar':''})
  else:
   delta=[float(r['hair_abs_delta_Lstar']) for r in rows]
   ref=next((r['hair_reference_Lstar_median'] for r in rows if r['hair_reference_Lstar_median']), '')
   out.append({'sample_id':sid,'attribute':'hair_color','expected_condition':s['expected_label'],'valid_frames':len(rows),'coverage':s['valid_frame_fraction'],'mean_probability_present':'','sd_probability_present':'','median_probability_present':'','expected_match_fraction':'','mean_abs_delta_Lstar':f'{statistics.mean(delta):.6f}' if delta else '', 'median_abs_delta_Lstar':f'{statistics.median(delta):.6f}' if delta else '', 'reference_Lstar':ref})
 cols=list(out[0]);write(a.output/'pilot_descriptive_results_v1.csv',cols,out)
 status=[]
 for attr in ('eyeglasses','facial_hair','hair_color'):
  c=Counter(r['attribute_frame_status'] for r in fr if r['attribute']==attr)
  status.append({'attribute':attr,'planned_frames':588,'valid_observable':c['VALID_OBSERVABLE'],'unobservable':c['UNOBSERVABLE'],'pipeline_failure':c['PIPELINE_FAILURE'],'interpretation':'facial-hair labels pending independent blinded annotator' if attr=='facial_hair' else 'descriptive only'})
 write(a.output/'attribute_status_summary_v1.csv',list(status[0]),status)
 import matplotlib.pyplot as plt
 g=[x for x in out if x['attribute']=='eyeglasses'];fig,ax=plt.subplots(figsize=(7,3.5));ax.bar([x['sample_id'][:2] for x in g],[float(x['mean_probability_present']) for x in g],color=['#b2182b','#b2182b','#2166ac','#2166ac']);ax.axhline(.5,color='black',lw=1,ls='--');ax.set(ylabel='Mean P(eyeglasses)',ylim=(0,1),title='Pilot eyeglasses observation (descriptive)');fig.tight_layout();fig.savefig(a.output/'figure_eyeglasses_probability_v1.png',dpi=200);plt.close(fig)
 h=[x for x in out if x['attribute']=='hair_color'];fig,ax=plt.subplots(figsize=(7,3.5));ax.bar([x['sample_id'][:2] for x in h],[float(x['median_abs_delta_Lstar']) for x in h],color='#4d9221');ax.set(ylabel='Median |frame L* - reference L*|',title='Pilot hair-colour reference-relative deviation (descriptive)');fig.tight_layout();fig.savefig(a.output/'figure_hair_abs_delta_Lstar_v1.png',dpi=200);plt.close(fig)
 audit={'status':'PASS','input_sha256':{str(p):sha(p) for p in (FRAME,SUMMARY,AUDIT)},'output_sha256':{},'row_counts':{'frame_input':len(fr),'summary_input':len(su),'descriptive_rows':len(out),'status_rows':len(status)},'boundary':'No facial-hair outcome is reported; no cross-sample inferential statistic or H1-H4 conclusion.'}
 for p in a.output.glob('*'):
  if p.is_file():audit['output_sha256'][p.name]=sha(p)
 with open(a.output/'analysis_audit_v1.json','x',encoding='utf-8') as f:json.dump(audit,f,indent=2);f.write('\n')
if __name__=='__main__':main()
