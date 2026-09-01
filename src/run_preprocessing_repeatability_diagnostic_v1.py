#!/usr/bin/env python3
"""Fail-closed runner for complete-panel preprocessing repeatability v1."""
from __future__ import annotations
import argparse,ast,json,os,subprocess,sys
from pathlib import Path
import preprocessing_repeatability_protocol_v1 as protocol

REPO=Path(__file__).resolve().parents[1]
GOV=REPO/"governance/mechanism_token_direction_preprocessing_repeatability_implementation_v1"
IMPLEMENTATION_AUTH=GOV/"researcher_implementation_authorization_v1.json"
DRY_STATUS="PREPROCESSING_REPEATABILITY_NO_WEIGHT_DRY_RUN_AUTHORIZED"
ACTIVE_STATUS="PREPROCESSING_REPEATABILITY_GPU_EXECUTION_AUTHORIZED"
CODE_PATHS=tuple(REPO/"src"/name for name in ("preprocessing_repeatability_protocol_v1.py","analyze_preprocessing_repeatability_v1.py","verify_preprocessing_repeatability_v1.py","run_preprocessing_repeatability_diagnostic_v1.py","preprocessing_repeatability_runtime_v1.py"))
class RepeatabilityRunnerError(RuntimeError):pass
def git_value(repo:Path,*args:str)->str:return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
def binding(item:dict,label:str)->Path:
    path=protocol.resolve(str(item.get("path","")))
    try:protocol.verify_file(path,int(item.get("bytes",-1)),str(item.get("sha256","")))
    except (ValueError,protocol.RepeatabilityProtocolError) as error:raise RepeatabilityRunnerError(f"{label} binding failed: {error}") from error
    return path
def validate_implementation_authority()->dict:
    auth=protocol.read_json(IMPLEMENTATION_AUTH)
    if auth.get("status")!="PREPROCESSING_REPEATABILITY_IMPLEMENTATION_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_AUTHORIZED_ONLY":raise RepeatabilityRunnerError("implementation authority status mismatch")
    protocol.validate_design();required=("protocol_and_plan_implementation","transient_analyzer_implementation","independent_verifier_implementation","fail_closed_runner_implementation","future_runtime_implementation","cpu_only_static_and_synthetic_tests","cpu_only_no_weight_dry_run")
    if any(auth.get("authorized",{}).get(k) is not True for k in required):raise RepeatabilityRunnerError("implementation authority incomplete")
    return auth
def validate_code(auth:dict)->None:
    code=auth.get("code",{})
    if set(code)!={p.name for p in CODE_PATHS}:raise RepeatabilityRunnerError("code universe mismatch")
    for path in CODE_PATHS:
        if binding(code[path.name],path.name).resolve()!=path.resolve():raise RepeatabilityRunnerError("code path mismatch")
def assert_no_top_level_ml_imports()->None:
    for path in CODE_PATHS:
        tree=ast.parse(path.read_text(),filename=str(path))
        for node in tree.body:
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else ([node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            if any(n.split(".")[0] in {"torch","models","diffusers","transformers"} for n in names):raise RepeatabilityRunnerError(f"top-level ML import: {path.name}")
def validate_dry(auth_file:Path,output:Path)->dict:
    validate_implementation_authority()
    if os.environ.get("CUDA_VISIBLE_DEVICES")!="":raise RepeatabilityRunnerError("dry-run requires hidden CUDA")
    auth=protocol.read_json(auth_file)
    if auth.get("status")!=DRY_STATUS or auth.get("gpu_execution_explicitly_approved") is not False:raise RepeatabilityRunnerError("dry authorization mismatch")
    validate_code(auth);binding(auth.get("design_freeze",{}),"design freeze")
    if Path(str(auth.get("output_dir",""))).resolve()!=output.resolve():raise RepeatabilityRunnerError("dry output mismatch")
    return auth
def validate_active(auth_file:Path,output:Path)->dict:
    validate_implementation_authority();auth=protocol.read_json(auth_file)
    if auth.get("status")!=ACTIVE_STATUS or auth.get("gpu_execution_explicitly_approved") is not True:raise RepeatabilityRunnerError("GPU execution lacks active authorization")
    validate_code(auth);binding(auth.get("design_freeze",{}),"design freeze");audit=binding(auth.get("formal_input_audit_freeze",{}),"formal input audit")
    if protocol.read_json(audit).get("status")!="FROZEN_PASS_COMPLETE_PANEL_FRESH_PREPROCESSING_REPEATABILITY_INPUT_AUDIT":raise RepeatabilityRunnerError("formal input audit did not pass")
    exact={"formal_units":40,"preprocessing_calls":80,"direct_lfe_calls":160,"within_rows":80,"cross_rows":40,"pooled_margin_rows":40,"cross_pooled_rows":20,"run003_comparison_rows":40,"token_margin_rows":0,"transformer_step_ceiling":0,"full_diffusion_trajectory_ceiling":0}
    if any(auth.get(k)!=v for k,v in exact.items()):raise RepeatabilityRunnerError("execution count drift")
    if not 0<float(auth.get("phase_gpu_hours_ceiling",0))<=2:raise RepeatabilityRunnerError("GPU-hour ceiling drift")
    cuda=str(auth.get("cuda_visible_devices",""))
    if not cuda.isdigit() or "," in cuda or os.environ.get("CUDA_VISIBLE_DEVICES")!=cuda:raise RepeatabilityRunnerError("single CUDA binding mismatch")
    if any(os.environ.get(k,"1")!="1" for k in ("WORLD_SIZE","LOCAL_WORLD_SIZE")):raise RepeatabilityRunnerError("distributed execution forbidden")
    if git_value(REPO,"branch","--show-current")!="main" or git_value(REPO,"status","--short"):raise RepeatabilityRunnerError("execution requires clean main")
    consisid=Path(str(auth.get("consisid_repository","")))
    if git_value(consisid,"rev-parse","HEAD")!=protocol.CONSISID_COMMIT or git_value(consisid,"status","--short"):raise RepeatabilityRunnerError("ConsisID state drift")
    staging=output.with_name(output.name+".partial")
    if Path(str(auth.get("runtime_output_dir",""))).resolve()!=output.resolve() or output.exists() or staging.exists():raise RepeatabilityRunnerError("runtime output mismatch or output/staging exists")
    return auth
def dry_run(auth_file:Path,output:Path)->int:
    validate_dry(auth_file,output);assert_no_top_level_ml_imports()
    if output.exists():raise RepeatabilityRunnerError("dry output exists")
    _,formal=protocol.formal_rows();plan=protocol.acquisition_plan(formal)
    if len(plan)!=80:raise RepeatabilityRunnerError("dry plan count drift")
    output.mkdir(parents=True,exist_ok=False);protocol.atomic_csv(output/"preprocessing_repeatability_plan_v1.csv",tuple(plan[0]),plan)
    summary={"schema_version":1,"status":"PASS_PREPROCESSING_REPEATABILITY_CPU_ONLY_NO_WEIGHT_DRY_RUN","plan_rows":80,"formal_units":40,"preprocessing_calls_planned":80,"direct_lfe_calls_planned":160,"within_rows_planned":80,"cross_rows_planned":40,"pooled_margin_rows_planned":40,"cross_pooled_rows_planned":20,"run003_rows_planned":40,"token_margin_rows":0,"transformer_steps":0,"reference_images_opened":False,"preprocessing_run":False,"model_or_weight_loading":False,"gpu_used":False,"raw_tensors_captured":False,"outcomes_opened":False,"token_margins_640_computed":False,"network_used":False,"torch_imported":"torch" in sys.modules}
    if summary["torch_imported"]:raise RepeatabilityRunnerError("dry-run imported torch")
    protocol.atomic_json(output/"preprocessing_repeatability_no_weight_dry_run_v1.json",summary);print(json.dumps(summary,indent=2,sort_keys=True));return 0
def execute(auth_file:Path,output:Path)->int:
    validate_active(auth_file,output);os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1",TOKENIZERS_PARALLELISM="false")
    from preprocessing_repeatability_runtime_v1 import execute_repeatability
    return execute_repeatability(output,auth_file)
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--mode",required=True,choices=("dry-run","execute-repeatability"));p.add_argument("--authorization-file",required=True,type=Path);p.add_argument("--output-dir",required=True,type=Path);a=p.parse_args();return dry_run(a.authorization_file,a.output_dir) if a.mode=="dry-run" else execute(a.authorization_file,a.output_dir)
if __name__=="__main__":
    try:raise SystemExit(main())
    except (RepeatabilityRunnerError,protocol.RepeatabilityProtocolError,ValueError) as error:print(f"BLOCKED: {error}",file=sys.stderr);raise SystemExit(2)
