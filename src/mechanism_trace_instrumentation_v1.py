#!/usr/bin/env python3
"""Runtime-only instrumentation for the prospectively frozen mechanism trace v1.

This module intentionally has no top-level torch or ConsisID import. The public
entry point imports ML dependencies only after the separate execution gate has
already been validated by ``run_mechanism_trace_v1.py``.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mechanism_trace_protocol_v1 import (
    FORMAL_MASTER,
    ProtocolError,
    build_plan,
    read_csv,
    read_json,
    sha256,
    validate_execution_authorization,
)


FRAME_COUNT_LATENT = 13
INJECTION_BLOCKS = tuple(range(0, 42, 2))
INJECTION_COLUMNS = (
    "trace_task_id",
    "phase",
    "formal_unit_id",
    "formal_pair_id",
    "attribute",
    "role",
    "seed_index",
    "seed",
    "condition",
    "repetition",
    "step_index",
    "scheduler_timestep",
    "site_index",
    "block_index",
    "cfg_branch",
    "local_face_scale",
    "rms_post",
    "rms_h",
    "rms_r",
    "relative_residual_rms",
    "mean_tokenwise_cosine_h_r",
    "token_rms_r_q10",
    "token_rms_r_q50",
    "token_rms_r_q90",
) + tuple(f"frame_rms_r_{index:02d}" for index in range(FRAME_COUNT_LATENT))
ROUTE_COLUMNS = (
    "trace_task_id",
    "phase",
    "formal_unit_id",
    "condition",
    "image_latents_overall_rms",
    "image_latents_first_frame_rms",
    "image_latents_padding_max_abs",
)
TASK_STATUS_COLUMNS = (
    "trace_task_id",
    "phase",
    "formal_unit_id",
    "seed",
    "condition",
    "status",
    "injection_rows",
    "started_at_utc",
    "finished_at_utc",
    "error_type",
    "error_message",
    "reference_vectors_verified_in_memory",
)
MARGIN_COLUMNS = (
    "attribute",
    "stage",
    "formal_pair_id",
    "margin",
    "direction",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_model_inventory(master: dict) -> None:
    """Hash every frozen model file before importing a model class."""
    item = master["artifacts"]["model_weight_hashes"]
    inventory_path = Path(item["path"])
    if inventory_path.stat().st_size != int(item["size_bytes"]) or sha256(inventory_path) != item["sha256"]:
        raise ProtocolError("model-weight inventory drift")
    model_root = Path(master["generation"]["model_path"])
    for row in read_csv(inventory_path):
        path = model_root / row["relative_path"]
        if not path.is_file():
            raise ProtocolError(f"model file missing: {path}")
        if path.stat().st_size != int(row["size_bytes"]) or sha256(path) != row["sha256"]:
            raise ProtocolError(f"model file drift: {path}")


class PartialCsvWriter:
    """Exclusive, flush-on-row CSV writer finalized by atomic rename."""

    def __init__(self, final_path: Path, columns: tuple[str, ...]):
        self.final_path = final_path
        self.partial_path = final_path.with_suffix(final_path.suffix + ".partial")
        if final_path.exists() or self.partial_path.exists():
            raise ProtocolError(f"refusing to overwrite runtime artifact: {final_path}")
        final_path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.partial_path.open("x", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.handle, fieldnames=columns, lineterminator="\n")
        self.writer.writeheader()
        self.handle.flush()

    def write(self, row: dict[str, Any]) -> None:
        self.writer.writerow(row)

    def flush(self) -> None:
        self.handle.flush()
        os.fsync(self.handle.fileno())

    def finalize(self) -> None:
        self.flush()
        self.handle.close()
        self.partial_path.replace(self.final_path)


def _float(value: Any) -> float:
    return float(value.detach().float().cpu().item())


def _rms(tensor: Any) -> Any:
    torch = __import__("torch")
    value = tensor.detach().float()
    return torch.sqrt(torch.mean(value * value))


def _l2_normalize(vector: Any) -> Any:
    torch = __import__("torch")
    vector = vector.detach().float()
    denominator = torch.linalg.vector_norm(vector).clamp_min(1e-12)
    return vector / denominator


def pooled_reference_vectors(id_cond: Any, id_vit_hidden: list[Any]) -> dict[str, Any]:
    if tuple(id_cond.shape) != (1, 1280):
        raise ProtocolError(f"unexpected id_cond shape: {tuple(id_cond.shape)}")
    if len(id_vit_hidden) != 5:
        raise ProtocolError(f"expected five EVA hidden tensors, found {len(id_vit_hidden)}")
    vectors = {
        "insightface_l2_normalized": _l2_normalize(id_cond[0, :512]),
        "eva_head_l2_normalized": _l2_normalize(id_cond[0, 512:]),
    }
    for index, tensor in enumerate(id_vit_hidden):
        if tuple(tensor.shape) != (1, 577, 1024):
            raise ProtocolError(f"unexpected EVA hidden {index} shape: {tuple(tensor.shape)}")
        vectors[f"eva_hidden_{index}_patch_mean_l2_normalized"] = _l2_normalize(tensor[0, 1:, :].float().mean(dim=0))
    return vectors


class TraceRecorder:
    def __init__(self, task: dict[str, str], injection_writer: PartialCsvWriter):
        self.task = task
        self.injection_writer = injection_writer
        self.step_index = -1
        self.site_index = 0
        self.scheduler_timestep: int | None = None
        self.row_count = 0
        self.image_route_summary: dict[str, float] | None = None
        self.reference_vectors: dict[str, Any] = {}
        self._first_lfe_vector: Any | None = None
        self.handles: list[Any] = []
        self._original_prepare_latents: Any | None = None

    def set_reference_inputs(self, id_cond: Any, id_vit_hidden: list[Any]) -> None:
        self.reference_vectors = pooled_reference_vectors(id_cond, id_vit_hidden)

    def _transformer_pre_hook(self, module: Any, args: tuple, kwargs: dict) -> None:
        if self.step_index >= 0 and self.site_index != 21:
            raise ProtocolError(
                f"step {self.step_index} ended after {self.site_index} injection sites"
            )
        self.step_index += 1
        self.site_index = 0
        timestep = kwargs.get("timestep")
        if timestep is None:
            raise ProtocolError("transformer hook did not receive timestep keyword")
        self.scheduler_timestep = int(timestep.detach().flatten()[0].cpu().item())

    def _lfe_hook(self, module: Any, inputs: tuple, output: Any) -> None:
        if tuple(output.shape) != (1, 32, 2048):
            raise ProtocolError(f"unexpected Local Facial Extractor output: {tuple(output.shape)}")
        pooled = _l2_normalize(output[0].detach().float().mean(dim=0))
        if self._first_lfe_vector is None:
            self._first_lfe_vector = pooled.cpu()
            self.reference_vectors["valid_face_emb_mean_token_l2_normalized"] = self._first_lfe_vector
        else:
            torch = __import__("torch")
            if not torch.allclose(
                pooled.cpu(), self._first_lfe_vector, rtol=1e-5, atol=1e-6
            ):
                raise ProtocolError("Local Facial Extractor output changed across scheduler steps")

    def _cross_attention_hook(self, expected_site: int):
        def hook(module: Any, inputs: tuple, output: Any) -> None:
            torch = __import__("torch")
            if self.site_index != expected_site:
                raise ProtocolError(
                    f"cross-attention order mismatch: expected={self.site_index} got={expected_site}"
                )
            if self.step_index not in range(50):
                raise ProtocolError(f"invalid scheduler position: {self.step_index}")
            if len(inputs) != 2:
                raise ProtocolError("cross-attention hook input arity drift")
            hidden = inputs[1].detach().float()
            residual = output.detach().float()
            if hidden.shape != residual.shape:
                raise ProtocolError("cross-attention residual shape differs from hidden states")
            if hidden.ndim != 3 or hidden.shape[0] != 2 or hidden.shape[-1] != 3072:
                raise ProtocolError(f"unexpected cross-attention hidden shape: {tuple(hidden.shape)}")
            if hidden.shape[1] % FRAME_COUNT_LATENT:
                raise ProtocolError("video token count is not divisible by 13 latent frames")
            branches = ("unconditional", "text")
            for branch_index, branch in enumerate(branches):
                h = hidden[branch_index]
                r = residual[branch_index]
                rms_h = _rms(h)
                rms_r = _rms(r)
                relative = rms_r / rms_h.clamp_min(1e-12)
                local_scale = float(self.task["condition"] != "zero_local_residual")
                post = h + local_scale * r
                rms_post = _rms(post)
                h_norm = torch.linalg.vector_norm(h, dim=-1).clamp_min(1e-12)
                r_norm = torch.linalg.vector_norm(r, dim=-1).clamp_min(1e-12)
                cosine = torch.mean(torch.sum(h * r, dim=-1) / (h_norm * r_norm))
                token_rms = torch.sqrt(torch.mean(r * r, dim=-1))
                quantiles = torch.quantile(
                    token_rms,
                    torch.tensor((0.10, 0.50, 0.90), device=token_rms.device),
                )
                per_frame = torch.sqrt(
                    torch.mean(
                        r.reshape(FRAME_COUNT_LATENT, -1, r.shape[-1]) ** 2,
                        dim=(1, 2),
                    )
                )
                row = {
                    **{key: self.task[key] for key in (
                        "trace_task_id", "phase", "formal_unit_id", "formal_pair_id",
                        "attribute", "role", "seed_index", "seed", "condition", "repetition"
                    )},
                    "step_index": self.step_index,
                    "scheduler_timestep": self.scheduler_timestep,
                    "site_index": expected_site,
                    "block_index": INJECTION_BLOCKS[expected_site],
                    "cfg_branch": branch,
                    "local_face_scale": local_scale,
                    "rms_post": _float(rms_post),
                    "rms_h": _float(rms_h),
                    "rms_r": _float(rms_r),
                    "relative_residual_rms": _float(relative),
                    "mean_tokenwise_cosine_h_r": _float(cosine),
                    "token_rms_r_q10": _float(quantiles[0]),
                    "token_rms_r_q50": _float(quantiles[1]),
                    "token_rms_r_q90": _float(quantiles[2]),
                }
                row.update(
                    {f"frame_rms_r_{index:02d}": _float(value) for index, value in enumerate(per_frame)}
                )
                self.injection_writer.write(row)
                self.row_count += 1
            self.site_index += 1

        return hook

    def _record_image_latents(self, image_latents: Any) -> None:
        torch = __import__("torch")
        tensor = image_latents.detach().float()
        if tensor.ndim != 5 or tensor.shape[0] != 1 or tensor.shape[1] != 13 or tensor.shape[2] != 16:
            raise ProtocolError(f"unexpected image_latents shape: {tuple(tensor.shape)}")
        first = tensor[:, :1]
        padding = tensor[:, 1:]
        vector = _l2_normalize(first.mean(dim=(0, 1, 3, 4))).cpu()
        self.reference_vectors["image_latent_first_frame_spatial_mean_l2_normalized"] = vector
        summary = {
            "image_latents_overall_rms": _float(_rms(tensor)),
            "image_latents_first_frame_rms": _float(_rms(first)),
            "image_latents_padding_max_abs": _float(torch.max(torch.abs(padding))),
        }
        if self.image_route_summary is not None:
            raise ProtocolError("prepare_latents was called more than once in one trajectory")
        self.image_route_summary = summary

    def install(self, transformer: Any, pipe: Any) -> None:
        if len(transformer.perceiver_cross_attention) != 21:
            raise ProtocolError("checkpoint does not expose 21 local cross-attention modules")
        self.handles.append(
            transformer.register_forward_pre_hook(self._transformer_pre_hook, with_kwargs=True)
        )
        self.handles.append(transformer.local_facial_extractor.register_forward_hook(self._lfe_hook))
        for index, module in enumerate(transformer.perceiver_cross_attention):
            self.handles.append(module.register_forward_hook(self._cross_attention_hook(index)))
        self._original_prepare_latents = pipe.prepare_latents

        def wrapped_prepare_latents(*args: Any, **kwargs: Any):
            result = self._original_prepare_latents(*args, **kwargs)
            self._record_image_latents(result[1])
            return result

        pipe.prepare_latents = wrapped_prepare_latents

    def uninstall(self, pipe: Any) -> None:
        for handle in self.handles:
            handle.remove()
        self.handles.clear()
        if self._original_prepare_latents is not None:
            pipe.prepare_latents = self._original_prepare_latents
            self._original_prepare_latents = None

    def finish(self) -> dict[str, float]:
        if self.step_index != 49 or self.site_index != 21:
            raise ProtocolError(
                f"incomplete trace: last_step={self.step_index} sites={self.site_index}"
            )
        if self.row_count != 50 * 21 * 2:
            raise ProtocolError(f"unexpected injection row count: {self.row_count}")
        if self.image_route_summary is None:
            raise ProtocolError("image_latents summary was not recorded")
        if set(self.reference_vectors) != {
            "insightface_l2_normalized", "eva_head_l2_normalized", "eva_hidden_0_patch_mean_l2_normalized", "eva_hidden_1_patch_mean_l2_normalized",
            "eva_hidden_2_patch_mean_l2_normalized", "eva_hidden_3_patch_mean_l2_normalized", "eva_hidden_4_patch_mean_l2_normalized",
            "valid_face_emb_mean_token_l2_normalized", "image_latent_first_frame_spatial_mean_l2_normalized"
        }:
            raise ProtocolError(f"reference vector stage mismatch: {sorted(self.reference_vectors)}")
        return self.image_route_summary


class ReferenceReadout:
    """Keep pooled vectors in memory, emit only matched-pair margins."""

    def __init__(self):
        self.vectors: dict[str, dict[str, Any]] = {}
        self.meta: dict[str, dict[str, str]] = {}

    def add(self, task: dict[str, str], vectors: dict[str, Any]) -> None:
        torch = __import__("torch")
        unit = task["formal_unit_id"]
        cpu_vectors = {name: value.detach().float().cpu() for name, value in vectors.items()}
        if unit in self.vectors:
            for name, value in cpu_vectors.items():
                if not torch.allclose(value, self.vectors[unit][name], rtol=1e-5, atol=1e-6):
                    raise ProtocolError(f"reference vector changed across seeds: {unit}/{name}")
            return
        self.vectors[unit] = cpu_vectors
        self.meta[unit] = {
            "attribute": task["attribute"],
            "role": task["role"],
            "formal_pair_id": task["formal_pair_id"],
        }

    def margins(self) -> list[dict[str, Any]]:
        torch = __import__("torch")
        if len(self.vectors) != 40:
            raise ProtocolError(f"scientific readout expected 40 units, found {len(self.vectors)}")
        rows: list[dict[str, Any]] = []
        stages = sorted(next(iter(self.vectors.values())))
        for attribute in ("eyeglasses", "facial_hair"):
            pairs: dict[str, dict[str, str]] = defaultdict(dict)
            for unit, meta in self.meta.items():
                if meta["attribute"] == attribute:
                    pairs[meta["formal_pair_id"]][meta["role"]] = unit
            if len(pairs) != 10 or any(set(roles) != {"positive", "control"} for roles in pairs.values()):
                raise ProtocolError(f"matched-pair structure drift for {attribute}")
            for stage in stages:
                for held_pair in sorted(pairs):
                    training_pairs = [pair for pair in sorted(pairs) if pair != held_pair]
                    directions = [
                        self.vectors[pairs[pair]["positive"]][stage]
                        - self.vectors[pairs[pair]["control"]][stage]
                        for pair in training_pairs
                    ]
                    direction = torch.stack(directions).mean(dim=0)
                    positive = self.vectors[pairs[held_pair]["positive"]][stage]
                    control = self.vectors[pairs[held_pair]["control"]][stage]
                    margin = float(torch.dot(positive, direction) - torch.dot(control, direction))
                    label = "tie" if abs(margin) <= 1e-8 else ("correct" if margin > 0 else "wrong")
                    rows.append(
                        {
                            "attribute": attribute,
                            "stage": stage,
                            "formal_pair_id": held_pair,
                            "margin": margin,
                            "direction": label,
                        }
                    )
        if len(rows) != 2 * 9 * 10:
            raise ProtocolError(f"unexpected representation-margin count: {len(rows)}")
        return rows


def _task_reference_rows(master: dict) -> dict[str, dict[str, str]]:
    manifest = Path(master["artifacts"]["generation_manifest"]["path"])
    return {row["task_id"]: row for row in read_csv(manifest)}


def _route_row(task: dict[str, str], summary: dict[str, float]) -> dict[str, Any]:
    return {
        "trace_task_id": task["trace_task_id"],
        "phase": task["phase"],
        "formal_unit_id": task["formal_unit_id"],
        "condition": task["condition"],
        **summary,
    }


def execute_trace_phase(phase: str, output_dir: Path, authorization_file: Path) -> int:
    """Execute only after the caller has validated a final authorization file."""
    runtime_code_paths = [
        Path(__file__).resolve().parent / name
        for name in (
            "mechanism_trace_protocol_v1.py",
            "mechanism_trace_instrumentation_v1.py",
            "run_mechanism_trace_v1.py",
            "verify_mechanism_trace_v1.py",
            "verify_mechanism_trace_engineering_controls_v1.py",
            "analyze_mechanism_trace_v1.py",
        )
    ]
    authorization = validate_execution_authorization(authorization_file, phase, runtime_code_paths)
    if Path(authorization.get("runtime_output_dir", "")).resolve() != output_dir.resolve():
        raise ProtocolError("runtime output directory differs from execution authorization")
    authorized_cuda = str(authorization.get("cuda_visible_devices", ""))
    if os.environ.get("CUDA_VISIBLE_DEVICES") != authorized_cuda:
        raise ProtocolError("CUDA_VISIBLE_DEVICES differs from execution authorization")
    phase_gpu_hours_ceiling = float(authorization["phase_gpu_hours_ceiling"])
    phase_started_monotonic = time.monotonic()
    phase_deadline = phase_started_monotonic + phase_gpu_hours_ceiling * 3600.0
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ProtocolError(f"runtime output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary, plan = build_plan(phase)
    expected = 24 if phase == "engineering" else 160
    if len(plan) != expected:
        raise ProtocolError(f"execution plan count drift: {len(plan)}")
    master = read_json(FORMAL_MASTER)
    verify_model_inventory(master)

    os.environ.update(
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        TOKENIZERS_PARALLELISM="false",
    )
    consisid_repo = Path(master["consisid"]["repository"])
    sys.path.insert(0, str(consisid_repo))

    import torch
    from models.consisid_utils import prepare_face_models, process_face_embeddings_infer
    from models.pipeline_consisid import ConsisIDPipeline
    from models.transformer_consisid import ConsisIDTransformer3DModel

    if not torch.cuda.is_available():
        raise ProtocolError("authorized execution requires CUDA but CUDA is unavailable")
    device = "cuda"
    dtype = torch.bfloat16
    model_path = master["generation"]["model_path"]
    if (Path(model_path) / "transformer_ema").exists():
        raise ProtocolError("unexpected transformer_ema appeared after design freeze")

    face_models = prepare_face_models(model_path, device, dtype)
    face_helper_1, face_helper_2, face_clip_model, face_main_model, eva_mean, eva_std = face_models
    transformer = ConsisIDTransformer3DModel.from_pretrained(
        model_path, subfolder="transformer", torch_dtype=dtype
    )
    pipe = ConsisIDPipeline.from_pretrained(model_path, transformer=transformer, torch_dtype=dtype)
    transformer.to(device, dtype=dtype)
    pipe.to(device)

    source_rows = _task_reference_rows(master)
    injection_writer = PartialCsvWriter(output_dir / "injection_summaries_v1.csv", INJECTION_COLUMNS)
    route_writer = PartialCsvWriter(output_dir / "route_summaries_v1.csv", ROUTE_COLUMNS)
    status_writer = PartialCsvWriter(output_dir / "task_status_v1.csv", TASK_STATUS_COLUMNS)
    margin_writer = (
        PartialCsvWriter(output_dir / "representation_margins_v1.csv", MARGIN_COLUMNS)
        if phase == "scientific" else None
    )
    readout = ReferenceReadout()
    event_path = output_dir / "execution_events_v1.jsonl"
    if event_path.exists():
        raise ProtocolError(f"refusing to overwrite event log: {event_path}")
    def enforce_deadline(pipe_instance: Any, step_index: int, timestep: Any, callback_kwargs: dict) -> dict:
        del pipe_instance, step_index, timestep
        if time.monotonic() >= phase_deadline:
            raise ProtocolError("phase GPU-hour ceiling reached during trajectory")
        return callback_kwargs

    with event_path.open("x", encoding="utf-8") as events:
        for task in plan:
            if time.monotonic() >= phase_deadline:
                raise ProtocolError("phase GPU-hour ceiling reached before next trajectory")
            started = utc_now()
            events.write(json.dumps({"event": "TASK_START", "at": started, "task": task}, sort_keys=True) + "\n")
            events.flush()
            source = source_rows[task["source_task_id"]]
            reference_path = Path(source["reference_image_path"])
            if not reference_path.is_file():
                raise ProtocolError(f"frozen reference image missing: {reference_path}")
            if sha256(reference_path) != source["reference_image_sha256"]:
                raise ProtocolError(f"frozen reference image SHA256 drift: {reference_path}")
            recorder = TraceRecorder(task, injection_writer)
            try:
                id_cond, id_vit_hidden, image, face_kps = process_face_embeddings_infer(
                    face_helper_1,
                    face_clip_model,
                    face_helper_2,
                    eva_mean,
                    eva_std,
                    face_main_model,
                    device,
                    dtype,
                    source["reference_image_path"],
                    is_align_face=True,
                )
                recorder.set_reference_inputs(id_cond, id_vit_hidden)
                recorder.install(transformer, pipe)
                transformer.local_face_scale = (
                    0.0 if task["condition"] == "zero_local_residual" else 1.0
                )
                generator = torch.Generator(device).manual_seed(int(task["seed"]))
                with torch.inference_mode():
                    output = pipe(
                        prompt=master["generation"]["prompt"],
                        negative_prompt=master["generation"]["negative_prompt"],
                        image=image,
                        num_videos_per_prompt=1,
                        num_inference_steps=50,
                        num_frames=49,
                        use_dynamic_cfg=False,
                        guidance_scale=6.0,
                        generator=generator,
                        id_vit_hidden=id_vit_hidden,
                        id_cond=id_cond,
                        kps_cond=face_kps,
                        output_type="latent",
                        callback_on_step_end=enforce_deadline,
                    )
                del output
                route_summary = recorder.finish()
                route_writer.write(_route_row(task, route_summary))
                readout.add(task, recorder.reference_vectors)
                finished = utc_now()
                status_writer.write(
                    {
                        "trace_task_id": task["trace_task_id"],
                        "phase": phase,
                        "formal_unit_id": task["formal_unit_id"],
                        "seed": task["seed"],
                        "condition": task["condition"],
                        "status": "COMPLETE_BOUNDED_SUMMARIES_ONLY",
                        "injection_rows": recorder.row_count,
                        "started_at_utc": started,
                        "finished_at_utc": finished,
                        "error_type": "",
                        "error_message": "",
                        "reference_vectors_verified_in_memory": True,
                    }
                )
                events.write(json.dumps({"event": "TASK_COMPLETE", "at": finished, "trace_task_id": task["trace_task_id"]}, sort_keys=True) + "\n")
            except Exception as error:
                finished = utc_now()
                status_writer.write(
                    {
                        "trace_task_id": task["trace_task_id"],
                        "phase": phase,
                        "formal_unit_id": task["formal_unit_id"],
                        "seed": task["seed"],
                        "condition": task["condition"],
                        "status": "FAILED_STOPPED",
                        "injection_rows": recorder.row_count,
                        "started_at_utc": started,
                        "finished_at_utc": finished,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                        "reference_vectors_verified_in_memory": False,
                    }
                )
                events.write(json.dumps({"event": "PHASE_STOP", "at": finished, "trace_task_id": task["trace_task_id"], "error_type": type(error).__name__, "error_message": str(error)}, sort_keys=True) + "\n")
                injection_writer.flush()
                route_writer.flush()
                status_writer.flush()
                raise
            finally:
                recorder.uninstall(pipe)
                transformer.local_face_scale = 1.0
            injection_writer.flush()
            route_writer.flush()
            status_writer.flush()
        if margin_writer is not None:
            for row in readout.margins():
                margin_writer.write(row)
            margin_writer.finalize()

    injection_writer.finalize()
    route_writer.finalize()
    status_writer.finalize()
    execution_summary = {
        **summary,
        "status": "TRACE_PHASE_COMPLETE_PENDING_INDEPENDENT_VERIFICATION",
        "phase": phase,
        "authorization_file": str(authorization_file),
        "authorization_sha256": sha256(authorization_file),
        "raw_tensor_files_written": 0,
        "decoded_media_files_written": 0,
        "torch_imported_during_execution": True,
        "phase_gpu_hours_ceiling": phase_gpu_hours_ceiling,
        "phase_elapsed_gpu_hours": (time.monotonic() - phase_started_monotonic) / 3600.0,
    }
    execution_summary.pop("torch_imported", None)
    execution_summary.pop("consisid_modules_imported", None)
    from mechanism_trace_protocol_v1 import atomic_write_json

    atomic_write_json(output_dir / "execution_summary_v1.json", execution_summary)
    return 0
