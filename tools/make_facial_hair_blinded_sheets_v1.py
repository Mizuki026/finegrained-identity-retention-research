#!/usr/bin/env python3
"""Create blinded facial-hair annotation contact sheets from anonymous crops."""
import argparse, csv, hashlib, json
from pathlib import Path
from PIL import Image, ImageDraw

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--materials',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    if a.output.exists(): raise RuntimeError(f'output exists: {a.output}')
    with open(a.materials/'annotation_template_v1.csv',newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
    with open(a.materials/'private_mapping_v1.csv',newline='',encoding='utf-8') as f: mapping=list(csv.DictReader(f))
    ids=[r['annotation_item_id'] for r in rows]
    if len(ids)!=len(set(ids)) or set(ids)!={r['annotation_item_id'] for r in mapping}: raise RuntimeError('template/mapping mismatch')
    crops=a.materials/'crops'
    if any(not (crops/f'{i}.jpg').is_file() for i in ids): raise RuntimeError('missing anonymous crop')
    a.output.mkdir(parents=True); cell=180; cols=5; rows_per=5; per=cols*rows_per
    for page,start in enumerate(range(0,len(rows),per),1):
        subset=rows[start:start+per]; canvas=Image.new('RGB',(cols*cell,rows_per*(cell+24)),'white'); d=ImageDraw.Draw(canvas)
        for n,row in enumerate(subset):
            im=Image.open(crops/f"{row['annotation_item_id']}.jpg").convert('RGB'); im.thumbnail((cell,cell)); x=(n%cols)*cell+(cell-im.width)//2; y=(n//cols)*(cell+24)+(cell-im.height)//2; canvas.paste(im,(x,y)); d.text(((n%cols)*cell+3,(n//cols)*(cell+24)+cell+3),f"{row['random_order']}: {row['annotation_item_id']}",fill='black')
        canvas.save(a.output/f'page_{page:02d}.png')
    with open(a.output/'blinded_sheet_manifest_v1.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['page','sha256']); w.writeheader(); [w.writerow({'page':p.name,'sha256':sha(p)}) for p in sorted(a.output.glob('page_*.png'))]
    with open(a.output/'README.md','x',encoding='utf-8') as f: f.write('Blinded manual facial-hair annotation sheets. Use only anonymous ID and ordinal rubric; do not inspect private_mapping_v1.csv before labels are final.\n')
if __name__=='__main__': main()
