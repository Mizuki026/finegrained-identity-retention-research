#!/usr/bin/env python3
"""Create immutable formal-generation inputs; never generates a video."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/root/autodl-tmp/finegrained")
RUNTIME = ROOT / "formal_experiment_v1_runtime"
PANEL = RUNTIME / "formal_reference_panel_v1"
FREEZE = RUNTIME / "experiment_freeze_v1"
OUTPUT = RUNTIME / "formal_generation_v1"
REPO = ROOT / "research_pipeline"
CONSISID = Path("/root/autodl-tmp/consisid-smoketest/ConsisID")
MODEL = Path("/root/autodl-tmp/consisid-smoketest/ckpts/ConsisID-preview")
PYTHON = Path("/root/autodl-tmp/consisid-smoketest/env/bin/python")
PILOT_FREEZE = ROOT / "pilot_v2_runtime/experiment_freeze_v2"
NAMESPACE = "formal_experiment_v1_shared_seed_bank_sha256_20260819"
PROMPT = (
    "A realistic medium close-up video of a person in soft natural daylight, "
    "looking toward the camera, gently blinking and making subtle natural head "
    "movements. The face remains clearly visible and in focus throughout, with "
    "realistic skin texture, stable lighting, natural motion, and a simple softly "
    "blurred background."
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    with path.open("x", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def artifact(path: Path) -> dict:
    return {"path": str(path), "sha256": sha(path), "size_bytes": path.stat().st_size}


def main() -> None:
    if FREEZE.exists() or OUTPUT.exists():
        raise RuntimeError("formal freeze/output path already exists; refusing to overwrite")
    if git(REPO, "status", "--short") or git(CONSISID, "status", "--short"):
        raise RuntimeError("both repositories must have clean working trees")
    panel_manifest = PANEL / "formal_reference_panel_manifest_v1.csv"
    panel_freeze_path = PANEL / "formal_reference_panel_freeze_v1.json"
    panel_freeze = json.loads(panel_freeze_path.read_text(encoding="utf-8"))
    if panel_freeze["status"] != "FORMAL_40_REFERENCE_CONDITION_PANEL_FROZEN":
        raise RuntimeError("formal reference panel is not frozen")
    if sha(panel_manifest) != panel_freeze["artifact_sha256"]["manifest"]:
        raise RuntimeError("formal panel manifest hash drift")
    panel_rows = read_csv(panel_manifest)
    if len(panel_rows) != 40 or len({r["formal_unit_id"] for r in panel_rows}) != 40:
        raise RuntimeError("formal panel must contain exactly 40 unique units")
    if list(RUNTIME.rglob("*.mp4")):
        raise RuntimeError("unexpected MP4 exists in formal runtime")

    FREEZE.mkdir(parents=True)
    seed_bank_path = FREEZE / "shared_seed_bank_v1.csv"
    seeds = []
    for index in range(1, 5):
        token = f"{NAMESPACE}|seed_{index:02d}"
        digest = hashlib.sha256(token.encode()).hexdigest()
        value = int(digest[:8], 16) or 1
        seeds.append({
            "seed_index": index,
            "seed": value,
            "derivation_token": token,
            "sha256": digest,
        })
    write_csv(seed_bank_path, ["seed_index", "seed", "derivation_token", "sha256"], seeds)

    generation_manifest_path = FREEZE / "generation_manifest_v1.csv"
    generation_rows = []
    for reference in panel_rows:
        image = PANEL / "images" / reference["materialized_filename"]
        if not image.is_file() or sha(image) != reference["image_sha256"]:
            raise RuntimeError(f"reference image drift: {reference['formal_unit_id']}")
        for seed in seeds:
            task_id = f"{reference['formal_unit_id']}__s{seed['seed_index']}"
            task_dir = OUTPUT / "videos" / reference["formal_unit_id"] / f"seed_{seed['seed_index']}"
            record = OUTPUT / "execution_records" / f"{task_id}_execution_v1.json"
            log = OUTPUT / "execution_records" / f"{task_id}_generation_v1.log"
            generation_rows.append({
                "task_id": task_id,
                "formal_unit_id": reference["formal_unit_id"],
                "formal_pair_id": reference["formal_pair_id"],
                "attribute": reference["attribute"],
                "role": reference["role"],
                "expected_state": reference["expected_state"],
                "gender": reference["gender"],
                "identity_key": reference["identity_key"],
                "seed_index": seed["seed_index"],
                "seed": seed["seed"],
                "reference_image_path": str(image),
                "reference_image_sha256": reference["image_sha256"],
                "expected_video_path": str(task_dir / f"{seed['seed']}_0000.mp4"),
                "execution_record_path": str(record),
                "log_path": str(log),
            })
    fields = list(generation_rows[0])
    write_csv(generation_manifest_path, fields, generation_rows)

    model_hashes = FREEZE / "model_weight_hashes_v1.csv"
    shutil.copyfile(PILOT_FREEZE / "model_weight_hashes_v2.csv", model_hashes)
    metric_model_hashes = FREEZE / "metric_model_hashes_v1.csv"
    shutil.copyfile(PILOT_FREEZE / "metric_models_v2/metric_model_hashes_v2.csv", metric_model_hashes)
    source_metric_protocol = FREEZE / "source_attribute_metric_protocol_v2_1.json"
    shutil.copyfile(PILOT_FREEZE / "metric_protocol_v2/attribute_metric_protocol_v2_1.json", source_metric_protocol)
    packages = FREEZE / "installed_packages_v1.txt"
    package_text = subprocess.check_output([str(PYTHON), "-m", "pip", "freeze", "--all"], text=True)
    packages.write_text(package_text, encoding="utf-8")

    metric_protocol_path = FREEZE / "attribute_metric_protocol_v1.json"
    metric_protocol = {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_FORMAL_GENERATION",
        "protocol_id": "formal_attribute_metric_protocol_v1",
        "generation_started_before_freeze": False,
        "primary_analysis_unit": "reference_condition_unit_after_aggregation_over_four_seeds",
        "frames_are_correlated": True,
        "no_imputation": True,
        "low_coverage_threshold": 0.5,
        "eyeglasses": {
            "instrument": "local CLIP ViT-B/32 two-prototype classifier",
            "implementation_reference": str(REPO / "src/pilot_v2_attribute_evaluation_v2.py"),
            "model_path": str(ROOT / "metric_models_v2/clip-vit-base-patch32"),
            "frames": list(range(49)),
            "primary_video_measure": "mean probability assigned to the frozen expected state over observable frames",
            "secondary_video_measures": ["expected_state_match_fraction", "mean_signed_margin", "valid_frame_fraction"],
            "prompt_bank_source": str(source_metric_protocol),
        },
        "facial_hair": {
            "instrument": "two independent blinded manual ordinal annotations with third-researcher adjudication",
            "labels": {"0": "none", "1": "faint_or_ambiguous", "2": "clearly_visible", "U": "unobservable"},
            "primary_states": {"positive": "2", "control": "0"},
            "frame_indices": [0, 8, 16, 24, 32, 40, 48],
            "primary_video_measure": "adjudicated expected-state match fraction over observable sampled frames",
            "secondary_video_measures": ["ordinal_mean", "label_2_fraction", "valid_frame_fraction"],
        },
        "identity_diagnostic": {
            "instrument": "InsightFace antelopev2 reference-to-frame cosine similarity",
            "role": "secondary_continuous_diagnostic_only",
            "threshold": None,
            "claim_boundary": "does not establish general identity preservation",
        },
        "failure_states": ["VALID_OBSERVABLE", "UNOBSERVABLE", "PIPELINE_FAILURE"],
        "analysis_boundary": "fixed finite panel; no causal, population-model, or frame-independent inference",
    }
    write_json(metric_protocol_path, metric_protocol)

    analysis_plan_path = FREEZE / "analysis_plan_v1.json"
    write_json(analysis_plan_path, {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_FORMAL_GENERATION",
        "primary_hypothesis": "H1",
        "h2_status": "exploratory",
        "h3_status": "deferred",
        "h4_status": "not_tested",
        "attributes": ["eyeglasses", "facial_hair"],
        "aggregation_order": ["frames_to_video", "four_seeds_to_reference_unit", "units_to_frozen_matched_pairs"],
        "independent_identity_count_not_video_count": True,
        "planned_reference_units": 40,
        "planned_videos": 160,
        "matched_pairs_per_attribute": 10,
        "primary_estimand": "finite-panel mean matched positive-minus-control difference for each attribute",
        "robustness": ["seed-specific paired contrasts", "median and full range", "coverage and all failure counts"],
        "no_cross_attribute_rank_test": True,
        "no_outcome_dependent_exclusion": True,
        "no_imputation": True,
        "claim_boundary": "describes only frozen references and videos; no causal or population claim",
    })

    protocol_path = FREEZE / "generation_protocol_v1.json"
    write_json(protocol_path, {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_FORMAL_GENERATION",
        "protocol_id": "formal_consisid_generation_protocol_v1",
        "model": "ConsisID-preview",
        "model_path": str(MODEL),
        "prompt": PROMPT,
        "negative_prompt": None,
        "target_attributes_mentioned": False,
        "same_prompt_for_all_tasks": True,
        "shared_seed_bank": [s["seed"] for s in seeds],
        "seed_namespace": NAMESPACE,
        "seed_derivation": "first 8 hexadecimal digits of SHA256(namespace|seed_XX), unsigned integer; zero replaced by one",
        "reference_units": 40,
        "seeds_per_reference": 4,
        "planned_videos": 160,
        "inference": {"num_inference_steps": 50, "guidance_scale": 6.0, "dtype": "bfloat16", "num_frames": 49, "fps": 8, "num_videos_per_prompt": 1, "lora": None, "upscale": False, "frame_interpolation": False},
        "recovery_policy": "exact pending-task resume only; completed exact output may be validated after controller interruption; no regeneration or favourable selection",
        "reference_substitution_allowed": False,
        "seed_change_allowed": False,
        "selective_favorable_rerun_allowed": False,
        "generation_started": False,
    })

    runtime_inventory_path = FREEZE / "runtime_inventory_v1.json"
    gpu = subprocess.check_output([
        "nvidia-smi", "--query-gpu=name,driver_version,memory.total,compute_cap", "--format=csv,noheader"
    ], text=True).strip()
    write_json(runtime_inventory_path, {
        "schema_version": 1,
        "captured_at_utc": now(),
        "python": str(PYTHON),
        "python_version": subprocess.check_output([str(PYTHON), "--version"], text=True).strip(),
        "platform": platform.platform(),
        "pytorch": subprocess.check_output([str(PYTHON), "-c", "import torch;print(torch.__version__);print(torch.version.cuda)"], text=True).splitlines(),
        "gpu": gpu,
        "research_branch": git(REPO, "branch", "--show-current"),
        "research_commit": git(REPO, "rev-parse", "HEAD"),
        "research_working_tree_clean": not bool(git(REPO, "status", "--short")),
        "consisid_commit": git(CONSISID, "rev-parse", "HEAD"),
        "consisid_working_tree_clean": not bool(git(CONSISID, "status", "--short")),
        "infer_py_sha256": sha(CONSISID / "infer.py"),
        "generation_performed": False,
    })

    prereg = REPO / "governance/formal_experiment_preregistration_v1.md"
    runner = REPO / "src/formal_generate_consisid_v1.py"
    preparer = REPO / "tools/prepare_formal_generation_v1.py"
    required = {
        "formal_reference_manifest": panel_manifest,
        "formal_reference_panel_freeze": panel_freeze_path,
        "seed_bank": seed_bank_path,
        "generation_manifest": generation_manifest_path,
        "generation_protocol": protocol_path,
        "attribute_metric_protocol": metric_protocol_path,
        "analysis_plan": analysis_plan_path,
        "runtime_inventory": runtime_inventory_path,
        "installed_packages": packages,
        "model_weight_hashes": model_hashes,
        "metric_model_hashes": metric_model_hashes,
        "source_metric_protocol": source_metric_protocol,
        "generation_controller": runner,
        "preparation_script": preparer,
        "preregistration": prereg,
        "consisid_infer_py": CONSISID / "infer.py",
    }
    for path in required.values():
        if not path.is_file():
            raise RuntimeError(f"required freeze input missing: {path}")

    master_path = FREEZE / "pre_generation_master_freeze_v1.json"
    master = {
        "schema_version": 1,
        "freeze_id": "formal_experiment_v1_pre_generation_master_freeze_v1",
        "status": "FROZEN_READY_FOR_FORMAL_GENERATION",
        "frozen_at_utc": now(),
        "generation_started": False,
        "generated_video_count": 0,
        "reference_units": 40,
        "seeds_per_reference": 4,
        "generation_count_planned": 160,
        "artifacts": {name: artifact(path) for name, path in required.items()},
        "code": {"research_repository": str(REPO), "branch": git(REPO, "branch", "--show-current"), "commit": git(REPO, "rev-parse", "HEAD"), "working_tree_clean": True},
        "consisid": {"repository": str(CONSISID), "commit": git(CONSISID, "rev-parse", "HEAD"), "working_tree_clean": True},
        "environment": {"python": str(PYTHON)},
        "generation": {"model_path": str(MODEL), "output_root": str(OUTPUT), "prompt": PROMPT, "negative_prompt": None, "num_inference_steps": 50, "guidance_scale": 6.0, "dtype": "bfloat16", "num_frames": 49, "fps": 8, "upscale": False, "frame_interpolation": False},
        "execution_gate": {"all_required_artifacts_present": True, "all_expected_outputs_absent": True, "generation_may_begin": True},
        "manual_substitution_allowed": False,
        "seed_changes_allowed": False,
        "selective_favorable_reruns_allowed": False,
        "same_prompt_for_all_tasks": True,
        "target_attributes_mentioned_in_prompt": False,
        "claim_boundary": "fixed finite sample; no causal, population-model, or frame-independent inference",
    }
    write_json(master_path, master)
    print(json.dumps({
        "status": "FORMAL_PRE_GENERATION_MASTER_FREEZE_CREATED",
        "master_freeze": str(master_path),
        "master_freeze_sha256": sha(master_path),
        "reference_units": 40,
        "shared_seeds": [s["seed"] for s in seeds],
        "generation_tasks": len(generation_rows),
        "existing_videos": 0,
        "generation_performed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
