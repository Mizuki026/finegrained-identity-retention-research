#!/usr/bin/env python3
"""Single-GPU, VAE-only private decoder for frozen monolithic run-002 latents."""
from __future__ import annotations

import gc
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import controlled_lfe_private_decode_protocol_v1 as protocol


class PrivateDecodeRuntimeError(RuntimeError):
    """Raised when decoding violates a frozen input, output, or runtime gate."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def execute(authorization: dict) -> dict[str, object]:
    if authorization.get("execution_explicitly_approved") is not True:
        raise PrivateDecodeRuntimeError("active private decode authorization required")
    ceiling = float(authorization.get("gpu_hours_ceiling", 0))
    if ceiling != protocol.GPU_HOURS_CEILING:
        raise PrivateDecodeRuntimeError("private decode GPU-hour ceiling drift")
    scalar = protocol.DECODE_RUN
    staging = scalar.with_name(scalar.name + ".partial")
    videos = protocol.VIDEO_ROOT
    if scalar.exists() or staging.exists() or videos.exists():
        raise PrivateDecodeRuntimeError("decode output, staging, or private video path already exists")
    plan = protocol.build_plan()
    if len(plan) != protocol.TRAJECTORIES:
        raise PrivateDecodeRuntimeError("decode plan is not exactly 480 trajectories")

    import torch
    from diffusers import AutoencoderKLCogVideoX
    from diffusers.utils import export_to_video
    from diffusers.video_processor import VideoProcessor
    from safetensors.torch import load_file

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise PrivateDecodeRuntimeError("exactly one visible GPU is required")
    started = time.monotonic()
    deadline = started + ceiling * 3600
    videos.mkdir(parents=True, exist_ok=False, mode=0o700)
    os.chmod(videos, 0o700)
    vae = None
    statuses: list[dict[str, object]] = []
    torch.cuda.reset_peak_memory_stats()
    try:
        vae = AutoencoderKLCogVideoX.from_pretrained(
            protocol.MODEL_ROOT, subfolder="vae", torch_dtype=torch.bfloat16
        )
        vae.to("cuda")
        vae.eval()
        processor = VideoProcessor(vae_scale_factor=8)
        for index, row in enumerate(plan, 1):
            if time.monotonic() >= deadline:
                raise PrivateDecodeRuntimeError("GPU-hour ceiling reached before private decode completion")
            latent_path = Path(str(row["latent_path"]))
            if (
                latent_path.is_symlink()
                or not latent_path.is_file()
                or latent_path.stat().st_size != int(row["latent_bytes"])
                or protocol.sha256(latent_path) != row["latent_sha256"]
            ):
                raise PrivateDecodeRuntimeError(f"frozen latent binding drift: {index}")
            tensors = load_file(str(latent_path), device="cpu")
            if set(tensors) != {"final_latents"}:
                raise PrivateDecodeRuntimeError(f"latent tensor key drift: {index}")
            latent = tensors["final_latents"]
            if (
                tuple(latent.shape) != protocol.LATENT_SHAPE
                or str(latent.dtype) != protocol.LATENT_DTYPE
                or not bool(torch.isfinite(latent).all())
            ):
                raise PrivateDecodeRuntimeError(f"latent tensor schema drift: {index}")
            latent = latent.to(device="cuda", dtype=torch.bfloat16)
            with torch.inference_mode():
                decoded = vae.decode(
                    latent.permute(0, 2, 1, 3, 4) / protocol.VAE_SCALING_FACTOR
                ).sample
                frames = processor.postprocess_video(video=decoded, output_type="pil")
            video = Path(str(row["video_path"]))
            partial_video = video.with_suffix(".partial.mp4")
            if video.exists() or partial_video.exists():
                raise PrivateDecodeRuntimeError(f"private video collision: {index}")
            export_to_video(frames[0], str(partial_video), fps=protocol.FPS)
            metadata = protocol.inspect_video(partial_video)
            partial_video.replace(video)
            os.chmod(video, 0o600)
            statuses.append({
                **row,
                "status": "COMPLETE",
                "finished_at_utc": utc_now(),
                "latent_shape": str(list(protocol.LATENT_SHAPE)),
                "latent_dtype": protocol.LATENT_DTYPE,
                "vae_scaling_factor": protocol.VAE_SCALING_FACTOR,
                "video_bytes": video.stat().st_size,
                "video_sha256": protocol.sha256(video),
                **metadata,
                "private_video_persisted": True,
                "public_video_persisted": False,
            })
            del tensors, latent, decoded, frames
            torch.cuda.empty_cache()
            print(f"PRIVATE_DECODE_COMPLETE {index}/{protocol.TRAJECTORIES}", flush=True)
        if len(statuses) != protocol.TRAJECTORIES:
            raise PrivateDecodeRuntimeError("private decode completion count drift")
        staging.mkdir(parents=True, exist_ok=False, mode=0o700)
        os.chmod(staging, 0o700)
        protocol.atomic_csv(staging / "private_decode_status_v1.csv", tuple(statuses[0]), statuses)
        summary = {
            "schema_version": 1,
            "status": "COMPLETE_PENDING_INDEPENDENT_PRIVATE_DECODE_VERIFICATION",
            "run_id": "monolithic_run_002_private_decode_v1",
            "source_latents": protocol.TRAJECTORIES,
            "decoded_private_videos": protocol.TRAJECTORIES,
            "frames_per_video": protocol.FRAMES,
            "fps": protocol.FPS,
            "width": protocol.WIDTH,
            "height": protocol.HEIGHT,
            "vae_only_model_loading": True,
            "vae_scaling_factor": protocol.VAE_SCALING_FACTOR,
            "upscale": False,
            "frame_interpolation": False,
            "public_video_files": 0,
            "reference_opened": False,
            "outcome_opened": False,
            "annotation_or_unblinding_performed": False,
            "elapsed_gpu_hours": (time.monotonic() - started) / 3600,
            "gpu_hours_ceiling": ceiling,
            "max_gpu_memory_allocated_bytes": torch.cuda.max_memory_allocated(),
        }
        protocol.atomic_json(staging / "private_decode_summary_v1.json", summary)
        staging.replace(scalar)
        return summary
    finally:
        if vae is not None:
            del vae
        gc.collect()
        if "torch" in locals() and torch.cuda.is_available():
            torch.cuda.empty_cache()
