#!/usr/bin/env python3
"""CPU-only, offline, one-run attribute evaluation for Pilot v3.

The twelve references, target attributes, metric protocol, prompt bank, model
weights and generation settings are frozen before generation. Each video is
evaluated only for its preassigned primary attribute. Outputs are always new;
the script fails closed and never overwrites an existing run.
"""
import argparse, csv, hashlib, json, os, platform, random, shutil, subprocess, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

ROOT = Path("/root/autodl-tmp/finegrained")
REPO = ROOT / "research_pipeline"
RUNTIME = ROOT / "pilot_v3_runtime"
FREEZE = RUNTIME / "experiment_freeze_v1"
INTEGRITY = RUNTIME / "generation_outputs_v1/video_integrity_audit_v3_1.csv"
PROTOCOL = FREEZE / "metric_protocol_v1/attribute_metric_protocol_v2_1.json"
ROI_ADDENDUM = REPO / "governance/hair_color_roi_coordinate_addendum_v1.md"
SCHEMA = REPO / "schemas/pilot_attribute_evaluation_output_schema_v1.json"
MANIFEST = FREEZE / "evaluation_manifest_v3.csv"
GLASSES_SPEC = PROTOCOL
VIDEO_PROTOCOL = FREEZE / "generation_protocol_v3.json"
CLIP_DIR = ROOT / "metric_models_v2/clip-vit-base-patch32"
FACE_ROOT = Path(
    "/root/autodl-tmp/consisid-smoketest/ckpts/"
    "ConsisID-preview/face_encoder"
)
PARSING_WEIGHTS = FACE_ROOT / "parsing_bisenet.pth"

FRAME_COLUMNS = [
 "schema_version","run_id","sample_id","attribute","frame_index","timestamp_seconds","video_integrity_status","attribute_frame_status","primary_reason_code","secondary_reason_codes","observability_evidence","eyeglasses_p_present","eyeglasses_p_absent","eyeglasses_margin","eyeglasses_predicted_label","eyeglasses_expected_label_match","facial_hair_ordinal_label","facial_hair_binary_label","facial_hair_expected_label_match","hair_valid_core_pixels","hair_Lstar_median","hair_Lstar_q25","hair_Lstar_q75","hair_astar_median","hair_bstar_median","hair_reference_Lstar_median","hair_delta_Lstar","hair_abs_delta_Lstar","annotation_item_id","record_status"
]
SUMMARY_COLUMNS = [
 "schema_version","run_id","sample_id","attribute","expected_label","total_frames","valid_observable_frames","unobservable_frames","pipeline_failure_frames","valid_frame_fraction","unobservable_fraction","pipeline_failure_fraction","low_coverage_flag","metric_mean","metric_sd","metric_median","expected_label_match_fraction","adjacent_valid_pair_count","adjacent_flip_count","adjacent_flip_rate","primary_reason_code","secondary_reason_codes","summary_status"
]

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def empty_row(run,sample,attr,index,t):
    d={k:"" for k in FRAME_COLUMNS}; d.update(schema_version="1",run_id=run,sample_id=sample,attribute=attr,frame_index=str(index),timestamp_seconds=f"{t:.6f}",video_integrity_status="PASS",record_status="PRODUCED"); return d
def fail(msg): raise RuntimeError(msg)
def git_commit(path):
    return subprocess.check_output(["git","-C",str(path),"rev-parse","HEAD"],text=True).strip()
def read_csv(path):
    with open(path,newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def write_csv(path, columns, rows):
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction="raise"); w.writeheader(); w.writerows(rows)
def set_status(row,status,reason="",secondary="",evidence=""):
    row["attribute_frame_status"]=status; row["primary_reason_code"]=reason; row["secondary_reason_codes"]=secondary; row["observability_evidence"]=evidence

def face_square(bbox, width, height):
    x0,y0,x1,y1=map(float,bbox); side=min(max(1.35*(x1-x0),1.35*(y1-y0)),min(width,height))
    cx,cy=(x0+x1)/2,(y0+y1)/2; x=round(cx-side/2); y=round(cy-side/2)
    x=max(0,min(x,width-round(side))); y=max(0,min(y,height-round(side))); s=round(side)
    if s<2: fail("invalid deterministic face crop")
    return x,y,x+s,y+s

def hair_geometry(bbox, width, height):
    import math
    x0,y0,x1,y1=map(float,bbox); w,h=x1-x0,y1-y0
    ex0=max(0,math.floor(x0-.85*w)); ey0=max(0,math.floor(y0-.90*h)); ex1=min(width,math.ceil(x1+.85*w)); ey1=min(height,math.ceil(y1+1.40*h))
    rx0=max(ex0,math.ceil(x0+.30*w)); ry0=max(ey0,math.ceil(y0-.85*h)); rx1=min(ex1,math.floor(x1-.30*w)); ry1=min(ey1,math.floor(y0+.35*h))
    if ex1<=ex0 or ey1<=ey0 or rx1<=rx0 or ry1<=ry0: return None
    sx,sy=512/(ex1-ex0),512/(ey1-ey0)
    mx0=max(0,min(512,math.ceil((rx0-ex0)*sx))); my0=max(0,min(512,math.ceil((ry0-ey0)*sy)))
    mx1=max(0,min(512,math.floor((rx1-ex0)*sx))); my1=max(0,min(512,math.floor((ry1-ey0)*sy)))
    return (ex0,ey0,ex1,ey1,mx0,my0,mx1,my1)

def synthetic_tests():
    assert face_square((10,20,110,120),200,180)==(0,2,135,137)
    g=hair_geometry((100,100,200,200),640,480); assert g and g[0:4]==(15,10,285,340) and 0<=g[4]<g[6]<=512 and 0<=g[5]<g[7]<=512
    assert hair_geometry((0,0,0,1),10,10) is None
    assert expected_match("eyeglasses", "present", "present") == "True"
    assert expected_match("eyeglasses", "absent", "absent") == "True"

def preflight(run_dir):
    if os.environ.get("CUDA_VISIBLE_DEVICES") not in ("", "-1"): fail("GPU visibility is not disabled")
    if run_dir.exists(): fail(f"output already exists: {run_dir}")
    for p in (
        MANIFEST,
        INTEGRITY,
        PROTOCOL,
        ROI_ADDENDUM,
        SCHEMA,
        VIDEO_PROTOCOL,
        PARSING_WEIGHTS,
        CLIP_DIR / "pytorch_model.bin",
    ):
        if not p.exists(): fail(f"required input missing: {p}")
    with open(SCHEMA) as f: schema=json.load(f)
    if schema["frame_inventory_columns"]!=FRAME_COLUMNS or schema["video_summary_columns"]!=SUMMARY_COLUMNS: fail("schema drift")
    manifest=read_csv(MANIFEST); integrity=read_csv(INTEGRITY)
    if len(manifest)!=12 or len({r['sample_id'] for r in manifest})!=12: fail("manifest is not exactly 12 unique samples")
    if len(integrity)!=12 or any(r["status"]!="PASS" for r in integrity): fail("integrity eligibility is not exactly 12 PASS")
    imap={r["sample_id"]:r for r in integrity}
    for r in manifest:
        sid=r["sample_id"]
        if sid not in imap or not Path(imap[sid]["observed_video_path"]).is_file(): fail(f"unmapped video: {sid}")
        if sha(imap[sid]["observed_video_path"])!=imap[sid]["observed_video_sha256"]: fail(f"video SHA drift: {sid}")
    if shutil.disk_usage(REPO).free < 10*(1<<30): fail("less than 10 GiB free disk")
    return manifest, imap

def load_models():
    import torch
    from transformers import CLIPModel, CLIPProcessor
    from insightface.app import FaceAnalysis
    from facexlib.parsing import BiSeNet
    torch.set_num_threads(1)
    if torch.cuda.is_available(): fail("torch reports CUDA available; CPU-only run refused")
    clip=CLIPModel.from_pretrained(str(CLIP_DIR),local_files_only=True).to("cpu").eval(); processor=CLIPProcessor.from_pretrained(str(CLIP_DIR),local_files_only=True)
    app=FaceAnalysis(name="antelopev2",root=str(FACE_ROOT),providers=["CPUExecutionProvider"]); app.prepare(ctx_id=-1,det_size=(640,640))
    parser=BiSeNet(num_class=19); state=torch.load(PARSING_WEIGHTS,map_location="cpu")
    parser.load_state_dict(state,strict=True); parser.eval()
    return torch,clip,processor,app,parser

def clip_prototypes(torch,clip,processor,spec):
    pos=spec["prompt_bank"]["positive_prompts"]; neg=spec["prompt_bank"]["negative_prompts"]
    with torch.no_grad():
        e=clip.get_text_features(**processor(text=pos+neg,return_tensors="pt",padding=True)); e=e/e.norm(dim=-1,keepdim=True)
    p=e[:len(pos)].mean(0); p=p/p.norm(); n=e[len(pos):].mean(0); n=n/n.norm(); return p,n

def score_glasses(torch,clip,processor,frame,bbox,protos):
    from PIL import Image
    x0,y0,x1,y1=face_square(bbox,frame.shape[1],frame.shape[0]); crop=frame[y0:y1,x0:x1,:,]
    image=Image.fromarray(crop[:,:,::-1])
    with torch.no_grad():
        v=clip.get_image_features(**processor(images=image,return_tensors="pt")); v=v/v.norm(dim=-1,keepdim=True)
        scale=clip.logit_scale.exp(); logits=torch.stack([(v@protos[0]).squeeze(),(v@protos[1]).squeeze()])*scale; probs=torch.softmax(logits,dim=0)
    pp,pn=float(probs[0]),float(probs[1]); return pp,pn,pp-pn,(x0,y0,x1,y1),crop

def score_hair(torch,parser,frame,bbox):
    import cv2, numpy as np
    g=hair_geometry(bbox,frame.shape[1],frame.shape[0])
    if not g:return None,"INVALID_HAIR_ROI"
    ex0,ey0,ex1,ey1,mx0,my0,mx1,my1=g; crop=cv2.resize(frame[ey0:ey1,ex0:ex1],(512,512),interpolation=cv2.INTER_LINEAR)
    rgb=crop[:,:,::-1].astype("float32")/255.; a=np.array([.485,.456,.406],dtype="float32"); b=np.array([.229,.224,.225],dtype="float32")
    ten=torch.from_numpy(((rgb-a)/b).transpose(2,0,1)).unsqueeze(0)
    with torch.no_grad(): out=parser(ten)[0].argmax(1).squeeze(0).numpy().astype("uint8")
    core=np.zeros((512,512),dtype="uint8"); core[my0:my1,mx0:mx1]=1; mask=((out==17).astype("uint8")*core)
    num,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
    if num>1:
        keep=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]); mask=(labels==keep).astype("uint8") if stats[keep,cv2.CC_STAT_AREA]>=256 else np.zeros_like(mask)
    else: mask=np.zeros_like(mask)
    mask=cv2.erode(mask,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7)),iterations=1); count=int(mask.sum())
    if count<1000:return {"pixels":count},"INSUFFICIENT_CORE_HAIR_MASK"
    lab=cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB); vals=lab[mask.astype(bool)]
    q=np.quantile(vals[:,0],[.25,.5,.75]); med=np.median(vals,axis=0)
    return {"pixels":count,"L":float(q[1]),"q25":float(q[0]),"q75":float(q[2]),"a":float(med[1]),"b":float(med[2])},None

def expected_ref_lstar(sample):
    # Pilot v3 freezes continuous output-video L-star as the primary outcome.
    # No post-generation threshold or unavailable reference-L-star lookup is used.
    return None

def expected_match(attribute, prediction, manifest_label):
    """Map the frozen manifest condition vocabulary to each instrument vocabulary."""
    if not prediction:
        return ""
    if attribute == "eyeglasses":
        target = {"positive": "present", "negative": "absent", "present": "present", "absent": "absent"}.get(manifest_label)
        if target is None: fail(f"unexpected eyeglasses manifest label: {manifest_label}")
        return str(prediction == target)
    return str(prediction == manifest_label)

def summarize(rows, manifest, run):
    import math, statistics
    out=[]
    for s in manifest:
      attr=s["attribute"]; rr=[r for r in rows if r["sample_id"]==s["sample_id"] and r["attribute"]==attr]; statuses=Counter(r["attribute_frame_status"] for r in rr); valid=[r for r in rr if r["attribute_frame_status"]=="VALID_OBSERVABLE"]
      values=[]; matches=[]; labels=[]
      for r in valid:
        x=r["eyeglasses_p_present"] if attr=="eyeglasses" else (r["hair_Lstar_median"] if attr=="hair_color" else "")
        if x!="": values.append(float(x))
        if r["eyeglasses_expected_label_match"] or r["facial_hair_expected_label_match"]: matches.append((r["eyeglasses_expected_label_match"] or r["facial_hair_expected_label_match"])=="True")
        labels.append(r["eyeglasses_predicted_label"] or r["facial_hair_binary_label"])
      pairs=flips=0
      for a,b in zip(valid,valid[1:]):
        if int(b["frame_index"])-int(a["frame_index"])==1 and (a["eyeglasses_predicted_label"] or a["facial_hair_binary_label"]) and (b["eyeglasses_predicted_label"] or b["facial_hair_binary_label"]):
          pairs+=1; flips+=int((a["eyeglasses_predicted_label"] or a["facial_hair_binary_label"]) != (b["eyeglasses_predicted_label"] or b["facial_hair_binary_label"]))
      n=len(rr); d={"schema_version":"1","run_id":run,"sample_id":s["sample_id"],"attribute":attr,"expected_label":s["label"],"total_frames":n,"valid_observable_frames":len(valid),"unobservable_frames":statuses["UNOBSERVABLE"],"pipeline_failure_frames":statuses["PIPELINE_FAILURE"],"valid_frame_fraction":f"{len(valid)/n:.6f}","unobservable_fraction":f"{statuses['UNOBSERVABLE']/n:.6f}","pipeline_failure_fraction":f"{statuses['PIPELINE_FAILURE']/n:.6f}","low_coverage_flag":str(len(valid)/n<.5).lower(),"metric_mean":f"{statistics.mean(values):.6f}" if values else "","metric_sd":f"{statistics.stdev(values):.6f}" if len(values)>1 else "","metric_median":f"{statistics.median(values):.6f}" if values else "","expected_label_match_fraction":f"{sum(matches)/len(matches):.6f}" if matches else "","adjacent_valid_pair_count":pairs,"adjacent_flip_count":flips,"adjacent_flip_rate":f"{flips/pairs:.6f}" if pairs else "","primary_reason_code":"","secondary_reason_codes":"","summary_status":"COMPLETE"}
      out.append(d)
    return out


def instrument_smoke():
    """Load all frozen instruments offline and test them on frozen references."""
    import cv2

    freeze_path = (
        FREEZE
        / "metric_protocol_v1"
        / "attribute_metric_protocol_freeze_v1.json"
    )
    reference_manifest = (
        RUNTIME
        / "frozen_references_v1"
        / "frozen_reference_files_v1.csv"
    )

    for path in (
        PROTOCOL,
        freeze_path,
        MANIFEST,
        reference_manifest,
        PARSING_WEIGHTS,
        CLIP_DIR / "pytorch_model.bin",
    ):
        if not path.exists():
            fail(f"instrument-smoke input missing: {path}")

    protocol = json.load(open(PROTOCOL, encoding="utf-8"))
    freeze = json.load(open(freeze_path, encoding="utf-8"))

    if freeze["status"] != "FROZEN":
        fail("metric protocol freeze is not FROZEN")
    if sha(PROTOCOL) != freeze["protocol_sha256"]:
        fail("active metric protocol SHA256 mismatch")
    if protocol["generation_started_before_freeze"] is not False:
        fail("metric protocol was not frozen before generation")

    manifest = read_csv(MANIFEST)
    references = read_csv(reference_manifest)

    if len(manifest) != 12 or len(references) != 12:
        fail("instrument-smoke requires exactly 12 frozen references")

    reference_by_id = {
        row["reference_id"]: row
        for row in references
    }

    for row in manifest:
        reference = reference_by_id.get(row["reference_id"])
        if reference is None:
            fail(f"reference mapping missing: {row['reference_id']}")
        image_path = Path(row["reference_image_path"])
        if not image_path.is_file():
            fail(f"reference image missing: {image_path}")
        if sha(image_path) != row["reference_image_sha256"]:
            fail(f"reference image SHA drift: {row['reference_id']}")

    torch, clip, processor, face, parser = load_models()

    eyeglasses_sample = next(
        row for row in manifest
        if row["attribute"] == "eyeglasses"
    )
    eyeglasses_frame = cv2.imread(
        eyeglasses_sample["reference_image_path"]
    )
    if eyeglasses_frame is None:
        fail("OpenCV could not read eyeglasses smoke-test image")

    eyeglasses_faces = face.get(eyeglasses_frame)
    if not eyeglasses_faces:
        fail("InsightFace detected no face in eyeglasses smoke-test image")

    eyeglasses_face = max(
        eyeglasses_faces,
        key=lambda item: (
            float(item.bbox[2] - item.bbox[0])
            * float(item.bbox[3] - item.bbox[1])
        ),
    )

    glasses_spec = protocol["eyeglasses"]
    prototypes = clip_prototypes(
        torch,
        clip,
        processor,
        glasses_spec,
    )
    p_present, p_absent, margin, crop_box, _ = score_glasses(
        torch,
        clip,
        processor,
        eyeglasses_frame,
        eyeglasses_face.bbox,
        prototypes,
    )

    if abs((p_present + p_absent) - 1.0) > 1e-5:
        fail("CLIP two-class probabilities do not sum to one")

    hair_sample = next(
        row for row in manifest
        if row["attribute"] == "hair_color"
    )
    hair_frame = cv2.imread(hair_sample["reference_image_path"])
    if hair_frame is None:
        fail("OpenCV could not read hair smoke-test image")

    hair_faces = face.get(hair_frame)
    if not hair_faces:
        fail("InsightFace detected no face in hair smoke-test image")

    hair_face = max(
        hair_faces,
        key=lambda item: (
            float(item.bbox[2] - item.bbox[0])
            * float(item.bbox[3] - item.bbox[1])
        ),
    )

    hair_result, hair_reason = score_hair(
        torch,
        parser,
        hair_frame,
        hair_face.bbox,
    )

    if hair_result is None:
        fail("BiSeNet smoke test returned no structured result")
    if hair_reason not in (None, "INSUFFICIENT_CORE_HAIR_MASK"):
        fail(f"unexpected BiSeNet smoke-test result: {hair_reason}")

    facial_hair_samples = [
        row for row in manifest
        if row["attribute"] == "facial_hair"
    ]
    if len(facial_hair_samples) != 4:
        fail("expected exactly four facial-hair primary samples")
    if any(row["label"] not in ("0", "2") for row in facial_hair_samples):
        fail("facial-hair primary labels are not frozen 0/2 labels")

    result = {
        "status": "INSTRUMENT_SMOKE_PASS",
        "network_used": False,
        "generation_performed": False,
        "outputs_written": False,
        "references_verified": len(manifest),
        "insightface_face_detected": True,
        "clip": {
            "reference_id": eyeglasses_sample["reference_id"],
            "p_present": p_present,
            "p_absent": p_absent,
            "margin": margin,
            "crop_box": list(crop_box),
        },
        "bisenet": {
            "reference_id": hair_sample["reference_id"],
            "valid_core_pixels": hair_result.get("pixels", 0),
            "measurement_status": (
                "VALID_OBSERVABLE"
                if hair_reason is None
                else hair_reason
            ),
            "frame_median_Lstar": (
                hair_result.get("L")
                if hair_reason is None
                else None
            ),
        },
        "facial_hair_manual_protocol": {
            "primary_sample_count": len(facial_hair_samples),
            "allowed_primary_labels": ["0", "2"],
            "annotation_performed": False,
        },
    }

    print(json.dumps(result, indent=2, sort_keys=True))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["instrument-smoke","dry-run","run"],required=True); ap.add_argument("--run-dir",type=Path); ap.add_argument("--run-id",default="pilot_v3_attribute_evaluation_v3"); args=ap.parse_args(); synthetic_tests()
    if args.mode == "instrument-smoke":
        instrument_smoke()
        return
    if args.run_dir is None:
        fail("--run-dir is required for dry-run and run modes")
    manifest,imap=preflight(args.run_dir)
    if args.mode=="dry-run": print(json.dumps({"status":"PREFLIGHT_PASS","samples":12,"frames":588,"attributes":3,"no_models_loaded":True},indent=2)); return
    import cv2, numpy as np
    args.run_dir.mkdir(parents=True); log=open(args.run_dir/"attribute_evaluation_v3.log","x",encoding="utf-8"); log.write(f"{now()} RUN_START\n")
    run=args.run_id; torch,clip,processor,face,parser=load_models(); spec=json.load(open(GLASSES_SPEC))["eyeglasses"]; protos=clip_prototypes(torch,clip,processor,spec)
    rows=[]; ann=[]; random.seed(20260803)
    for sample in manifest:
      sid=sample["sample_id"]; cap=cv2.VideoCapture(imap[sid]["observed_video_path"])
      if not cap.isOpened(): fail(f"decoder cannot open {sid}")
      for idx in range(49):
        ok,frame=cap.read()
        if not ok: fail(f"decoder failure {sid} frame {idx}")
        t=idx/8.0; faces=face.get(frame); selected=max(faces,key=lambda x:float(x.bbox[2]-x.bbox[0])*float(x.bbox[3]-x.bbox[1])) if faces else None
        for attr in (sample["attribute"],):
          r=empty_row(run,sid,attr,idx,t)
          if selected is None: set_status(r,"UNOBSERVABLE","NO_FACE_DETECTED","","InsightFace returned zero faces"); rows.append(r); continue
          if attr=="eyeglasses":
            try:
              pp,pn,margin,box,_=score_glasses(torch,clip,processor,frame,selected.bbox,protos); pred="present" if margin>0 else ("absent" if margin<0 else "")
              set_status(r,"VALID_OBSERVABLE","","",f"largest_face_bbox={','.join(f'{x:.1f}' for x in selected.bbox)};crop={box}")
              r.update(eyeglasses_p_present=f"{pp:.8f}",eyeglasses_p_absent=f"{pn:.8f}",eyeglasses_margin=f"{margin:.8f}",eyeglasses_predicted_label=pred,eyeglasses_expected_label_match=expected_match(attr,pred,sample['label']) if sample['attribute']==attr else "")
            except Exception as e: set_status(r,"PIPELINE_FAILURE","EYEGLASSES_SCORING_ERROR","",type(e).__name__)
          elif attr=="hair_color":
            try:
              h,reason=score_hair(torch,parser,frame,selected.bbox)
              if reason: set_status(r,"UNOBSERVABLE",reason,"",f"largest_face_bbox={','.join(f'{x:.1f}' for x in selected.bbox)}"); r["hair_valid_core_pixels"]=str(h.get("pixels",0)) if h else ""
              else:
                ref=expected_ref_lstar(sample); set_status(r,"VALID_OBSERVABLE","","",f"largest_face_bbox={','.join(f'{x:.1f}' for x in selected.bbox)}"); r.update(hair_valid_core_pixels=h['pixels'],hair_Lstar_median=f"{h['L']:.8f}",hair_Lstar_q25=f"{h['q25']:.8f}",hair_Lstar_q75=f"{h['q75']:.8f}",hair_astar_median=f"{h['a']:.8f}",hair_bstar_median=f"{h['b']:.8f}",hair_reference_Lstar_median=f"{ref:.8f}" if ref is not None else "",hair_delta_Lstar=f"{h['L']-ref:.8f}" if ref is not None else "",hair_abs_delta_Lstar=f"{abs(h['L']-ref):.8f}" if ref is not None else "")
            except Exception as e: set_status(r,"PIPELINE_FAILURE","HAIR_COLOR_SCORING_ERROR","",type(e).__name__)
          else:
            item=f"FH_{hashlib.sha256(f'{sid}:{idx}:20260803'.encode()).hexdigest()[:12].upper()}"; set_status(r,"UNOBSERVABLE","ANNOTATION_PENDING","","blinded manual annotation pending"); r["annotation_item_id"]=item; ann.append((item,sid,idx,frame,selected.bbox))
          rows.append(r)
      cap.release(); log.write(f"{now()} VIDEO_DONE {sid}\n"); log.flush()
    write_csv(args.run_dir/"attribute_frame_inventory_v3.csv",FRAME_COLUMNS,rows); write_csv(args.run_dir/"attribute_video_summary_v3.csv",SUMMARY_COLUMNS,summarize(rows,manifest,run))
    ann_dir=args.run_dir/"facial_hair_blinded_materials"; ann_dir.mkdir(); crops=ann_dir/"crops"; crops.mkdir(); random.shuffle(ann)
    key=[]; template=[]
    for order,(item,sid,idx,frame,bbox) in enumerate(ann,1):
      x0,y0,x1,y1=face_square(bbox,frame.shape[1],frame.shape[0]); cp=frame[y0:y1,x0:x1]; cv2.imwrite(str(crops/f"{item}.jpg"),cp,[cv2.IMWRITE_JPEG_QUALITY,95]); key.append({"annotation_item_id":item,"sample_id":sid,"frame_index":idx}); template.append({"annotation_item_id":item,"random_order":order,"ordinal_label":"","reason_or_note":""})
    write_csv(ann_dir/"private_mapping_v3.csv",["annotation_item_id","sample_id","frame_index"],key); write_csv(ann_dir/"annotation_template_v3.csv",["annotation_item_id","random_order","ordinal_label","reason_or_note"],template)
    checks=[]
    for p in sorted(args.run_dir.rglob("*")):
      if p.is_file(): checks.append({"path":str(p),"sha256":sha(p),"bytes":p.stat().st_size})
    write_csv(args.run_dir/"input_output_sha256_v3.csv",["path","sha256","bytes"],checks)
    audit={"run_id":run,"completed_at":now(),"script_sha256":sha(Path(__file__)),"code_commit":git_commit(REPO),"inputs":{"manifest":sha(MANIFEST),"integrity":sha(INTEGRITY),"protocol":sha(PROTOCOL),"roi_addendum":sha(ROI_ADDENDUM),"schema":sha(SCHEMA)},"environment":{"python":sys.version,"platform":platform.platform(),"cuda_visible_devices":os.environ.get('CUDA_VISIBLE_DEVICES'),"hf_hub_offline":os.environ.get('HF_HUB_OFFLINE')},"row_counts":{"frame_inventory":len(rows),"summary":12,"annotation_items":len(ann)},"status":"MACHINE_EVALUATION_COMPLETE_MANUAL_ANNOTATION_PENDING","boundary":"Pilot v3 primary-attribute measurement only; no confirmatory causal claim."}
    with open(args.run_dir/"attribute_execution_audit_v3.json","x",encoding="utf-8") as f:json.dump(audit,f,indent=2);f.write("\n")
    with open(args.run_dir/"README.md","x",encoding="utf-8") as f:f.write("# Pilot v3 attribute evaluation v3\n\nMachine observations are complete; facial-hair labels remain blinded and pending. Do not overwrite or reuse this run.\n")
    log.write(f"{now()} MACHINE_EVALUATION_COMPLETE rows={len(rows)} annotation_items={len(ann)}\n"); log.close()

if __name__=="__main__": main()
