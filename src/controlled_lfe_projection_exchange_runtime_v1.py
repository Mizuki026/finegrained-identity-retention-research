#!/usr/bin/env python3
"""Fail-closed runtime orchestration behind future phase-specific adapters.

This module does not import ConsisID or torch at module load. A future, separately
authorized GPU adapter must supply acquisition and trajectory execution methods.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import controlled_lfe_projection_exchange_protocol_v1 as protocol


class ControlledInterventionRuntimeError(RuntimeError):
    """Raised when a future runtime adapter violates the frozen transaction."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _phase_rows(mode: str) -> list[dict[str, object]]:
    rows = protocol.execution_plan()
    if mode == "engineering":
        chosen = protocol.engineering_pairs()
        rows = [
            {**row, "scheduler_positions": 1, "trajectory_kind": "engineering_one_step"}
            for row in rows
            if row["formal_pair_id"] in chosen[str(row["attribute"])] and int(row["seed_index"]) == 1
        ]
        if len(rows) != 24:
            raise ControlledInterventionRuntimeError("engineering plan is not exactly 24 one-step conditions")
    elif mode != "scientific":
        raise ControlledInterventionRuntimeError(f"unknown runtime mode: {mode}")
    return rows


def execute_with_adapter(
    mode: str,
    source_bindings: dict[str, dict[str, object]],
    adapter: Any,
    output_dir: Path,
    authorization: dict,
) -> dict:
    """Execute only after the runner has validated a later active authorization.

    Adapter contract:
      acquire(unit_id, binding) -> {"lfe": tensor, "handle": opaque}
      run_trajectory(plan_row, handle, direct_lfe, selected_lfe) -> scalar dict
      close() -> None
    Tensor-bearing values are retained only in local memory and never passed to
    artifact writers.
    """
    if authorization.get("execution_explicitly_approved") is not True:
        raise ControlledInterventionRuntimeError("active execution authorization required")
    if authorization.get("phase") != mode:
        raise ControlledInterventionRuntimeError("runtime phase differs from authorization")
    ceiling = float(authorization.get("phase_gpu_hours_ceiling", 0))
    maximum = 2.0 if mode == "engineering" else 72.0
    if not 0 < ceiling <= maximum:
        raise ControlledInterventionRuntimeError("GPU-hour ceiling outside frozen phase boundary")
    if output_dir.exists() or output_dir.with_name(output_dir.name + ".partial").exists():
        raise ControlledInterventionRuntimeError("runtime output or staging path already exists")
    expected_units = [
        protocol.unit_id(attribute, pair, role)
        for attribute in protocol.ATTRIBUTES
        for pair in protocol.pair_ids(attribute)
        for role in protocol.ROLES
    ]
    if set(source_bindings) != set(expected_units):
        raise ControlledInterventionRuntimeError("formal input audit did not bind exactly 40 planned units")

    started = time.monotonic()
    deadline = started + ceiling * 3600
    tensors, metadata, handles = {}, {}, {}
    try:
        for unit in sorted(expected_units):
            if time.monotonic() >= deadline:
                raise ControlledInterventionRuntimeError("GPU-hour ceiling reached during acquisition")
            binding = source_bindings[unit]
            acquired = adapter.acquire(unit, binding)
            if set(acquired) != {"lfe", "handle"}:
                raise ControlledInterventionRuntimeError("adapter acquisition contract drift")
            tensors[unit] = acquired["lfe"]
            handles[unit] = acquired["handle"]
            metadata[unit] = {
                "attribute": str(binding["attribute"]),
                "formal_pair_id": str(binding["formal_pair_id"]),
                "role": str(binding["role"]),
            }
        if len(tensors) != 40:
            raise ControlledInterventionRuntimeError("acquisition transaction did not complete all 40 units")
        from controlled_lfe_projection_exchange_instrumentation_v1 import (
            build_transient_interventions,
        )

        bundle = build_transient_interventions(tensors, metadata)
        rows = _phase_rows(mode)
        statuses = []
        for row in rows:
            if time.monotonic() >= deadline:
                raise ControlledInterventionRuntimeError("GPU-hour ceiling reached before trajectory")
            unit = str(row["planned_unit_id"])
            condition = str(row["condition"])
            result = adapter.run_trajectory(
                row, handles[unit], bundle.unmodified[unit], bundle.selected[(unit, condition)]
            )
            if not isinstance(result, dict) or any(not isinstance(key, str) for key in result):
                raise ControlledInterventionRuntimeError("adapter trajectory result must be scalar metadata")
            if any(hasattr(value, "shape") for value in result.values()):
                raise ControlledInterventionRuntimeError("adapter attempted to return a tensor for persistence")
            statuses.append({
                "planned_task_id": row["planned_task_id"], "planned_unit_id": unit,
                "formal_pair_id": row["formal_pair_id"], "attribute": row["attribute"],
                "role": row["role"], "seed_index": row["seed_index"], "seed": row["seed"],
                "condition_position": row["condition_position"], "condition": condition,
                "scheduler_positions": row["scheduler_positions"], "status": "COMPLETE",
                "finished_at_utc": _now(), **result,
            })
        expected = 24 if mode == "engineering" else 480
        if len(statuses) != expected:
            raise ControlledInterventionRuntimeError("trajectory completion count drift")
        staging = output_dir.with_name(output_dir.name + ".partial")
        staging.mkdir(parents=True, exist_ok=False)
        protocol.atomic_csv(staging / "trajectory_status_v1.csv", tuple(statuses[0]), statuses)
        if mode == "engineering":
            protocol.atomic_csv(staging / "direction_scalar_diagnostics_v1.csv", tuple(bundle.diagnostics[0]), bundle.diagnostics)
        summary = {
            "schema_version": 1, "status": "COMPLETE_PENDING_INDEPENDENT_PHASE_VERIFICATION",
            "phase": mode, "fresh_preprocessing_calls": 40, "direct_lfe_acquisitions": 40,
            "directions_constructed": 640, "trajectory_rows": len(statuses),
            "scheduler_steps": sum(int(row["scheduler_positions"]) for row in rows),
            "raw_identity_lfe_or_direction_tensor_files": 0,
            "elapsed_gpu_hours": (time.monotonic() - started) / 3600,
            "phase_gpu_hours_ceiling": ceiling,
        }
        protocol.atomic_json(staging / "execution_summary_v1.json", summary)
        staging.replace(output_dir)
        return summary
    finally:
        tensors.clear()
        handles.clear()
        if hasattr(adapter, "close"):
            adapter.close()



class ConsisIDRuntimeAdapter:
    """Delayed-import adapter used only after all later execution gates pass."""

    def __init__(self, master: dict, authorization: dict, phase: str):
        import torch
        from models.consisid_utils import (
            prepare_face_models,
            process_face_embeddings_infer,
        )
        from models.pipeline_consisid import ConsisIDPipeline
        from models.transformer_consisid import ConsisIDTransformer3DModel

        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise ControlledInterventionRuntimeError("exactly one visible GPU is required")
        self.torch = torch
        self.process_face = process_face_embeddings_infer
        self.phase = phase
        self.master = master
        self.authorization = authorization
        self.device = "cuda"
        self.dtype = torch.bfloat16
        model_path = master["generation"]["model_path"]
        face = prepare_face_models(model_path, self.device, self.dtype)
        (self.face_helper_1, self.face_helper_2, self.face_clip_model,
         self.face_main_model, self.eva_mean, self.eva_std) = face
        self.transformer = ConsisIDTransformer3DModel.from_pretrained(
            model_path, subfolder="transformer", torch_dtype=self.dtype
        )
        self.pipe = ConsisIDPipeline.from_pretrained(
            model_path, transformer=self.transformer, torch_dtype=self.dtype
        )
        self.transformer.to(self.device, dtype=self.dtype)
        self.pipe.to(self.device)
        self.transformer.local_face_scale = 1.0
        self.invariants: dict[str, dict[str, object]] = {}
        self.private_root = Path(str(authorization.get("private_latent_output_dir", "")))
        if phase == "scientific":
            if not self.private_root.is_absolute() or protocol.REPO.resolve() in self.private_root.resolve().parents:
                raise ControlledInterventionRuntimeError("scientific latent output must be absolute and outside Git")
            if self.private_root.exists():
                raise ControlledInterventionRuntimeError("private scientific latent output path already exists")
            self.private_root.mkdir(parents=True, exist_ok=False)

    def acquire(self, unit_id: str, binding: dict[str, object]) -> dict[str, object]:
        reference = Path(str(binding["reference_image_path"]))
        if reference.is_symlink() or not reference.is_file() or protocol.sha256(reference) != binding["reference_image_sha256"]:
            raise ControlledInterventionRuntimeError(f"reference binding drift: {unit_id}")
        values = self.process_face(
            self.face_helper_1, self.face_clip_model, self.face_helper_2,
            self.eva_mean, self.eva_std, self.face_main_model,
            self.device, self.dtype, str(reference), is_align_face=True,
        )
        id_cond, id_vit_hidden, image, face_kps = values
        with self.torch.inference_mode():
            lfe = self.transformer.local_facial_extractor(id_cond, id_vit_hidden)
        return {"lfe": lfe.detach().float().cpu().clone(),
                "handle": {"id_cond": id_cond, "id_vit_hidden": id_vit_hidden,
                           "image": image, "face_kps": face_kps}}

    def run_trajectory(self, row: dict[str, object], handle: dict[str, object], direct_lfe: Any, selected_lfe: Any) -> dict[str, object]:
        from controlled_lfe_projection_exchange_instrumentation_v1 import (
            LFEOutputOverride,
            TransformerInputInvariantRecorder,
        )

        steps = int(row["scheduler_positions"])
        generator = self.torch.Generator(self.device).manual_seed(int(row["seed"]))
        override = LFEOutputOverride(self.transformer.local_facial_extractor, direct_lfe, selected_lfe)
        recorder = TransformerInputInvariantRecorder(self.transformer)
        with self.torch.inference_mode(), override, recorder:
            output = self.pipe(
                prompt=self.master["generation"]["prompt"],
                negative_prompt=self.master["generation"]["negative_prompt"],
                image=handle["image"], num_videos_per_prompt=1,
                num_inference_steps=steps, num_frames=49, use_dynamic_cfg=False,
                guidance_scale=6.0, generator=generator,
                id_vit_hidden=handle["id_vit_hidden"], id_cond=handle["id_cond"],
                kps_cond=handle["face_kps"], output_type="latent",
            )
        override.verify_calls(steps)
        invariant = recorder.finish(steps)
        task = str(row["planned_task_id"])
        if task in self.invariants and invariant != self.invariants[task]:
            raise ControlledInterventionRuntimeError("initial latent or spatial-route invariant differs across conditions")
        self.invariants.setdefault(task, invariant)
        result: dict[str, object] = {**invariant, "lfe_hook_calls": override.calls}
        if self.phase == "engineering":
            del output
            result.update(private_latent_persisted=False, decoded_media_persisted=False)
        else:
            from safetensors.torch import save_file

            latent = output.frames.detach().cpu().contiguous()
            pseudonym = protocol.sha256_text(
                f"{protocol.NAMESPACE}|private_latent|{task}|{row['condition']}"
            )[:32]
            path = self.private_root / f"{pseudonym}.safetensors"
            if path.exists():
                raise ControlledInterventionRuntimeError("private latent collision")
            save_file({"final_latents": latent}, str(path))
            result.update(private_latent_path=str(path), private_latent_bytes=path.stat().st_size,
                          private_latent_sha256=protocol.sha256(path), decoded_media_persisted=False)
            del latent, output
        return result

    def close(self) -> None:
        for name in ("pipe", "transformer", "face_main_model", "face_clip_model"):
            if hasattr(self, name):
                delattr(self, name)
        if hasattr(self, "torch") and self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()


def prepare_active_runtime(authorization: dict, phase: str) -> tuple[dict[str, dict[str, object]], ConsisIDRuntimeAdapter]:
    import os
    import sys

    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                      TOKENIZERS_PARALLELISM="false")
    master_path = protocol.bound(authorization.get("formal_generation_master", {}), "formal generation master")
    binding_path = protocol.bound(authorization.get("formal_task_binding_manifest", {}), "formal task binding manifest")
    master = protocol.read_json(master_path)
    consisid = Path(str(authorization.get("consisid_repository", "")))
    if not consisid.is_dir():
        raise ControlledInterventionRuntimeError("ConsisID repository missing")
    sys.path.insert(0, str(consisid))
    rows = protocol.read_csv(binding_path)
    required = {"planned_task_id", "planned_unit_id", "formal_pair_id", "attribute", "role",
                "seed_index", "seed", "reference_image_path", "reference_image_sha256"}
    if len(rows) != 160 or any(not required.issubset(row) for row in rows):
        raise ControlledInterventionRuntimeError("formal task binding manifest schema or row-count drift")
    expected_tasks = {str(row["planned_task_id"]): row for row in protocol.execution_plan()}
    bindings: dict[str, dict[str, object]] = {}
    seen = set()
    for row in rows:
        task = row["planned_task_id"]
        if task not in expected_tasks or task in seen:
            raise ControlledInterventionRuntimeError("formal task binding key drift")
        seen.add(task)
        expected = expected_tasks[task]
        for key in ("planned_unit_id", "formal_pair_id", "attribute", "role", "seed_index", "seed"):
            if str(row[key]) != str(expected[key]):
                raise ControlledInterventionRuntimeError(f"formal task binding metadata drift: {task}/{key}")
        unit = row["planned_unit_id"]
        candidate = {key: row[key] for key in ("attribute", "formal_pair_id", "role", "reference_image_path", "reference_image_sha256")}
        if unit in bindings and bindings[unit] != candidate:
            raise ControlledInterventionRuntimeError(f"unit reference binding drift: {unit}")
        bindings[unit] = candidate
    if seen != set(expected_tasks) or len(bindings) != 40:
        raise ControlledInterventionRuntimeError("formal task binding universe incomplete")
    return bindings, ConsisIDRuntimeAdapter(master, authorization, phase)
