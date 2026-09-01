#!/usr/bin/env python3
"""Fail-closed runner for complete-panel direct-hook diagnostic v1."""
from __future__ import annotations
import argparse,ast,json,os,subprocess,sys
from pathlib import Path
import token_resolved_lfe_direct_hook_diagnostic_protocol_v1 as protocol

REPO=Path(__file__).resolve().parents[1]
GOV=REPO/"governance/mechanism_token_direction_direct_hook_diagnostic_implementation_v1"
IMPLEMENTATION_AUTH=GOV/"researcher_implementation_authorization_v1.json"
DRY_STATUS="COMPLETE_PANEL_DIRECT_HOOK_DIAGNOSTIC_NO_WEIGHT_DRY_RUN_AUTHORIZED"
ACTIVE_STATUS="COMPLETE_PANEL_DIRECT_HOOK_DIAGNOSTIC_GPU_EXECUTION_AUTHORIZED"
CODE_PATHS=tuple(REPO/"src"/name for name in ("token_resolved_lfe_direct_hook_diagnostic_protocol_v1.py","analyze_token_resolved_lfe_direct_hook_diagnostic_v1.py","verify_token_resolved_lfe_direct_hook_diagnostic_v1.py","run_token_resolved_lfe_direct_hook_diagnostic_v1.py","token_resolved_lfe_direct_hook_diagnostic_runtime_v1.py","token_resolved_lfe_direction_instrumentation_v1.py"))
class DiagnosticRunnerError(RuntimeError):pass
def git_value(repo:Path,*args:str)->str:return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
def binding(binding:dict,label:str)->Path:
    path=protocol.resolve(str(binding.get("path","")))
    try:protocol.verify_file(path,int(binding.get("bytes",-1)),str(binding.get("sha256","")))
    except (ValueError,protocol.DiagnosticProtocolError) as error:raise DiagnosticRunnerError(f"{label} binding failed: {error}") from error
    return path
def validate_implementation_authority()->dict:
    auth=protocol.read_json(IMPLEMENTATION_AUTH)
    if auth.get("status")!="DIAGNOSTIC_RUNNER_IMPLEMENTATION_CPU_TESTS_AND_NO_WEIGHT_DRY_RUN_AUTHORIZED_ONLY":raise DiagnosticRunnerError("implementation authority status mismatch")
    protocol.validate_design()
    required=("protocol_and_plan_implementation","fail_closed_runner_implementation","transient_analyzer_implementation","runtime_instrumentation_implementation","independent_verifier_implementation","cpu_only_static_and_synthetic_tests","cpu_only_no_weight_dry_run")
    if any(auth.get("authorized",{}).get(k) is not True for k in required):raise DiagnosticRunnerError("implementation authority incomplete")
    return auth
def validate_code(auth:dict)->None:
    code=auth.get("code",{})
    if set(code)!={p.name for p in CODE_PATHS}:raise DiagnosticRunnerError("code universe mismatch")
    for path in CODE_PATHS:
        if binding(code[path.name],path.name).resolve()!=path.resolve():raise DiagnosticRunnerError("code path mismatch")
def assert_no_top_level_ml_imports()->None:
    for path in CODE_PATHS:
        tree=ast.parse(path.read_text(),filename=str(path))
        for node in tree.body:
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else ([node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            if any(n.split(".")[0] in {"torch","models","diffusers","transformers"} for n in names):raise DiagnosticRunnerError(f"top-level ML import: {path.name}")
def validate_dry(auth_file:Path,output:Path)->dict:
    validate_implementation_authority()
    if os.environ.get("CUDA_VISIBLE_DEVICES")!="":raise DiagnosticRunnerError("dry-run requires hidden CUDA")
    auth=protocol.read_json(auth_file)
    if auth.get("status")!=DRY_STATUS or auth.get("gpu_execution_explicitly_approved") is not False:raise DiagnosticRunnerError("dry authorization mismatch")
    validate_code(auth);binding(auth.get("design_freeze",{}),"design freeze")
    if Path(str(auth.get("output_dir",""))).resolve()!=output.resolve():raise DiagnosticRunnerError("dry output mismatch")
    return auth
def validate_active(auth_file:Path,output:Path)->dict:
    validate_implementation_authority();auth=protocol.read_json(auth_file)
    if auth.get("status")!=ACTIVE_STATUS or auth.get("gpu_execution_explicitly_approved") is not True:raise DiagnosticRunnerError("GPU execution lacks active authorization")
    validate_code(auth);binding(auth.get("design_freeze",{}),"design freeze")
    audit=binding(auth.get("formal_input_audit_freeze",{}),"formal input audit")
    if protocol.read_json(audit).get("status")!="FROZEN_PASS_COMPLETE_PANEL_DIRECT_HOOK_DIAGNOSTIC_INPUT_AUDIT":raise DiagnosticRunnerError("formal input audit did not pass")
    exact={"formal_units":40,"direct_lfe_calls":40,"one_step_hook_controls":40,"hook_pooled_rows":20,"token_margin_rows":0,"transformer_step_ceiling":40,"full_diffusion_trajectory_ceiling":0}
    if any(auth.get(k)!=v for k,v in exact.items()):raise DiagnosticRunnerError("execution count drift")
    if not 0<float(auth.get("phase_gpu_hours_ceiling",0))<=2:raise DiagnosticRunnerError("GPU-hour ceiling drift")
    cuda=str(auth.get("cuda_visible_devices",""))
    if not cuda.isdigit() or "," in cuda or os.environ.get("CUDA_VISIBLE_DEVICES")!=cuda:raise DiagnosticRunnerError("single CUDA binding mismatch")
    if any(os.environ.get(k,"1")!="1" for k in ("WORLD_SIZE","LOCAL_WORLD_SIZE")):raise DiagnosticRunnerError("distributed execution forbidden")
    if git_value(REPO,"branch","--show-current")!="main" or git_value(REPO,"status","--short"):raise DiagnosticRunnerError("execution requires clean main")
    consisid=Path(str(auth.get("consisid_repository","")))
    if git_value(consisid,"rev-parse","HEAD")!=protocol.CONSISID_COMMIT or git_value(consisid,"status","--short"):raise DiagnosticRunnerError("ConsisID state drift")
    if Path(str(auth.get("runtime_output_dir",""))).resolve()!=output.resolve() or output.exists():raise DiagnosticRunnerError("runtime output mismatch or exists")
    return auth
def dry_run(auth_file:Path,output:Path)->int:
    validate_dry(auth_file,output);assert_no_top_level_ml_imports()
    if output.exists():raise DiagnosticRunnerError("dry output exists")
    _,formal=protocol.formal_rows();plan=protocol.diagnostic_plan(formal);output.mkdir(parents=True,exist_ok=False);protocol.atomic_csv(output/"diagnostic_plan_v1.csv",tuple(plan[0]),plan)
    summary={"schema_version":1,"status":"PASS_COMPLETE_PANEL_DIAGNOSTIC_CPU_ONLY_NO_WEIGHT_DRY_RUN","plan_rows":40,"formal_units":40,"direct_calls":40,"one_step_hooks":40,"hook_pooled_rows":20,"token_margin_rows":0,"gpu_used":False,"model_or_weight_loading":False,"reference_images_opened":False,"raw_tensors_captured":False,"outcomes_opened":False,"token_margins_640_computed":False,"network_used":False,"torch_imported":"torch" in sys.modules}
    if summary["torch_imported"]:raise DiagnosticRunnerError("dry-run imported torch")
    protocol.atomic_json(output/"diagnostic_runner_no_weight_dry_run_v1.json",summary);print(json.dumps(summary,indent=2,sort_keys=True));return 0
def execute(auth_file:Path,output:Path)->int:
    validate_active(auth_file,output);os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1",TOKENIZERS_PARALLELISM="false")
    from token_resolved_lfe_direct_hook_diagnostic_runtime_v1 import execute_diagnostic
    return execute_diagnostic(output,auth_file)
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--mode",required=True,choices=("dry-run","execute-diagnostic"));p.add_argument("--authorization-file",required=True,type=Path);p.add_argument("--output-dir",required=True,type=Path);a=p.parse_args();return dry_run(a.authorization_file,a.output_dir) if a.mode=="dry-run" else execute(a.authorization_file,a.output_dir)
if __name__=="__main__":
    try:raise SystemExit(main())
    except (DiagnosticRunnerError,protocol.DiagnosticProtocolError,ValueError) as error:print(f"BLOCKED: {error}",file=sys.stderr);raise SystemExit(2)
