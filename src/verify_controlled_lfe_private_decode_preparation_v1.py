#!/usr/bin/env python3
"""CPU-only, torch-free verifier for private latent decode preparation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import controlled_lfe_private_decode_protocol_v1 as protocol
import run_controlled_lfe_private_decode_v1 as runner


class PrivateDecodePreparationVerificationError(RuntimeError):
    """Raised when private decode preparation evidence drifts."""


def verify(dry_run_dir: Path) -> dict[str, object]:
    protocol.require_cpu_only()
    if "torch" in sys.modules:
        raise PrivateDecodePreparationVerificationError("preparation verifier imported torch")
    researcher = protocol.read_json(runner.RESEARCHER_AUTH)
    if researcher.get("status") != runner.RESEARCHER_STATUS:
        raise PrivateDecodePreparationVerificationError("researcher authorization drift")
    dry = protocol.read_json(dry_run_dir / "private_decode_no_weight_dry_run_v1.json")
    exact = {
        "status": "PASS_PRIVATE_LATENT_DECODE_CPU_ONLY_NO_WEIGHT_DRY_RUN",
        "source_latents": 480,
        "planned_private_videos": 480,
        "frames_per_video": 49,
        "fps": 8,
        "width": 720,
        "height": 480,
        "latent_shape": list(protocol.LATENT_SHAPE),
        "latent_dtype": protocol.LATENT_DTYPE,
        "vae_scaling_factor": protocol.VAE_SCALING_FACTOR,
        "vae_only_model_loading_planned": True,
        "upscale": False,
        "frame_interpolation": False,
        "active_execution_authorization_present": False,
        "latent_tensor_opened": False,
        "model_or_weights_loaded": False,
        "gpu_used": False,
        "reference_or_outcome_opened": False,
        "decoded_video_generated": False,
        "annotation_unblinding_or_analysis": False,
        "torch_imported": False,
        "network_used": False,
    }
    if any(dry.get(key) != value for key, value in exact.items()):
        raise PrivateDecodePreparationVerificationError("no-weight dry-run evidence drift")
    observed = protocol.read_csv(dry_run_dir / "private_decode_plan_v1.csv")
    expected = [{key: str(row[key]) for key in protocol.PLAN_FIELDS} for row in protocol.build_plan()]
    if observed != expected or len(observed) != protocol.TRAJECTORIES:
        raise PrivateDecodePreparationVerificationError("persisted private decode plan drift")
    if runner.ACTIVE_AUTH.exists():
        raise PrivateDecodePreparationVerificationError("active GPU authorization exists during preparation")
    if protocol.DECODE_RUN.exists() or protocol.DECODE_RUN.with_name(protocol.DECODE_RUN.name + ".partial").exists():
        raise PrivateDecodePreparationVerificationError("decode scalar output exists during preparation")
    if protocol.VIDEO_ROOT.exists():
        raise PrivateDecodePreparationVerificationError("private decoded-video output exists during preparation")
    parent = protocol.VIDEO_ROOT.parent
    if not parent.is_dir() or parent.stat().st_mode & 0o777 != 0o700:
        raise PrivateDecodePreparationVerificationError("private decoded-video parent mode drift")
    runtime = runner.CODE_PATHS["runtime"].read_text(encoding="utf-8")
    required_fragments = (
        "AutoencoderKLCogVideoX.from_pretrained", 'subfolder="vae"',
        "latent.permute(0, 2, 1, 3, 4) / protocol.VAE_SCALING_FACTOR",
        "VideoProcessor(vae_scale_factor=8)", "export_to_video(frames[0]",
        "protocol.inspect_video(partial_video)",
    )
    if any(fragment not in runtime for fragment in required_fragments):
        raise PrivateDecodePreparationVerificationError("native VAE decode wiring drift")
    if "ConsisIDPipeline.from_pretrained" in runtime:
        raise PrivateDecodePreparationVerificationError("full pipeline loading present")
    return {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_PRIVATE_LATENT_DECODE_CPU_PREPARATION_VERIFICATION",
        "source_latent_bindings_planned": 480,
        "private_videos_planned": 480,
        "decoded_frames_planned": 23520,
        "native_vae_decode_wiring_verified": True,
        "private_parent_mode": "0700",
        "active_gpu_authorization_present": False,
        "runtime_output_present": False,
        "private_video_output_present": False,
        "cuda_visible_devices": "",
        "torch_imported": False,
        "model_or_weights_loaded": False,
        "reference_or_outcome_opened": False,
        "annotation_unblinding_or_analysis": False,
        "gpu_used": False,
        "network_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.dry_run_dir)
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        PrivateDecodePreparationVerificationError, protocol.PrivateDecodeProtocolError,
        OSError, ValueError, KeyError,
    ) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
