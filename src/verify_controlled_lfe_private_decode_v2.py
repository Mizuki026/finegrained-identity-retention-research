#!/usr/bin/env python3
"""Corrected CPU-only verifier with independent source-latent rehashing."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import controlled_lfe_private_decode_protocol_v1 as protocol
import verify_controlled_lfe_private_decode_v1 as v1

AUTH = protocol.GOVERNANCE / "researcher_private_decode_verification_authorization_v1.json"
STATUS = "RESEARCHER_AUTHORIZATION_FOR_CPU_ONLY_INDEPENDENT_PRIVATE_LATENT_DECODE_VERIFIER"
PASS = "PASS_INDEPENDENT_PRIVATE_LATENT_DECODE_VERIFICATION_V2"


class PrivateDecodeVerificationV2Error(RuntimeError):
    """Raised when corrected independent verification fails closed."""


def validate_authority(path: Path) -> dict:
    protocol.require_cpu_only()
    if "torch" in sys.modules:
        raise PrivateDecodeVerificationV2Error("v2 verifier must start torch-free")
    if path.resolve() != AUTH.resolve():
        raise PrivateDecodeVerificationV2Error("verification authorization path drift")
    auth = protocol.read_json(path)
    if auth.get("status") != STATUS or auth.get("cpu_only_independent_verifier_authorized") is not True:
        raise PrivateDecodeVerificationV2Error("verification authorization drift")
    code = protocol.bound(auth.get("verifier_code", {}), "v2 verifier code")
    if code.resolve() != Path(__file__).resolve():
        raise PrivateDecodeVerificationV2Error("v2 verifier code binding drift")
    execution = protocol.bound(auth.get("execution_authorization", {}), "decode execution authorization")
    v1.validate_authority(execution)
    if subprocess.check_output(
        ["git", "--no-optional-locks", "-C", str(protocol.REPO), "status", "--short"], text=True
    ):
        raise PrivateDecodeVerificationV2Error("v2 verifier requires clean research worktree")
    return auth


def verify(run_dir: Path, video_root: Path) -> dict[str, object]:
    prior = v1.verify_outputs(run_dir, video_root)
    plan = protocol.build_plan()
    latents: set[Path] = set()
    latent_bytes = 0
    for index, row in enumerate(plan, 1):
        path = Path(str(row["latent_path"]))
        if path.parent.resolve() != protocol.LATENT_ROOT.resolve() or path in latents:
            raise PrivateDecodeVerificationV2Error(f"source latent universe drift: {index}")
        if path.is_symlink() or not path.is_file():
            raise PrivateDecodeVerificationV2Error(f"missing regular source latent: {index}")
        if path.stat().st_size != int(row["latent_bytes"]) or protocol.sha256(path) != row["latent_sha256"]:
            raise PrivateDecodeVerificationV2Error(f"source latent byte/SHA256 drift: {index}")
        latents.add(path)
        latent_bytes += path.stat().st_size
    actual = set(protocol.LATENT_ROOT.iterdir())
    if actual != latents or len(latents) != protocol.TRAJECTORIES or any(
        path.is_symlink() or not path.is_file() or path.suffix != ".safetensors" for path in actual
    ):
        raise PrivateDecodeVerificationV2Error("source latent file universe drift")
    return {
        **prior,
        "schema_version": 2,
        "status": PASS,
        "source_latent_bindings_verified": 480,
        "source_latent_files": 480,
        "source_latent_bytes": latent_bytes,
        "source_latent_byte_and_sha256_rehashed_by_v2": 480,
        "private_decoded_video_byte_and_sha256_rehashed": 480,
        "prior_v1_record_disposition": "SUPERSEDED_NONAUTHORITATIVE_DUE_TO_SOURCE_LATENT_REHASH_OMISSION",
        "reference_or_outcome_opened": False,
        "annotation_unblinding_or_analysis_performed": False,
        "model_loaded_by_verifier": False,
        "gpu_used_by_verifier": False,
        "network_used_by_verifier": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--private-video-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    validate_authority(args.authorization_file)
    result = verify(args.run_dir, args.private_video_dir)
    protocol.atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        PrivateDecodeVerificationV2Error, v1.PrivateDecodeVerificationError,
        protocol.PrivateDecodeProtocolError, OSError, ValueError, KeyError,
        subprocess.SubprocessError,
    ) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
