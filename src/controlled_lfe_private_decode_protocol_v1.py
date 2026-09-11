#!/usr/bin/env python3
"""Pure-stdlib protocol and bindings for private run-002 latent decoding."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

import controlled_lfe_projection_exchange_protocol_v1 as intervention

REPO = Path(__file__).resolve().parents[1]
GOVERNANCE = REPO / "governance/mechanism_controlled_intervention_scientific_monolithic_run_002_decode_v1"
GENERATION_GOVERNANCE = REPO / "governance/mechanism_controlled_intervention_scientific_monolithic_run_002_v1"
GENERATION_FREEZE = GENERATION_GOVERNANCE / "scientific_monolithic_run_002_generation_freeze_v1.json"
GENERATION_RUN = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_monolithic/run_002")
LATENT_ROOT = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_private_monolithic/run_002")
DECODE_RUN = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_decode_monolithic/run_002")
VIDEO_ROOT = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_private_decoded_monolithic/run_002")
MODEL_ROOT = Path("/root/autodl-tmp/consisid-smoketest/ckpts/ConsisID-preview")
MODEL_INVENTORY = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/experiment_freeze_v1/model_weight_hashes_v1.csv")
CONSISID = Path("/root/autodl-tmp/consisid-smoketest/ConsisID")
CONSISID_COMMIT = "60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
NAMESPACE = "controlled_lfe_projection_exchange_v1|monolithic_run_002|private_decode_v1"
FPS = 8
FRAMES = 49
WIDTH = 720
HEIGHT = 480
LATENT_SHAPE = (1, 13, 16, 60, 90)
LATENT_DTYPE = "torch.bfloat16"
VAE_SCALING_FACTOR = 0.7
TRAJECTORIES = 480
GPU_HOURS_CEILING = 12.0

PLAN_FIELDS = (
    "planned_task_id", "planned_unit_id", "formal_pair_id", "attribute", "role",
    "seed_index", "seed", "condition_position", "condition", "scheduler_positions",
    "latent_path", "latent_bytes", "latent_sha256", "video_path",
)


class PrivateDecodeProtocolError(RuntimeError):
    """Raised when a private decode binding or invariant drifts."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def resolve(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO / path


def bound(item: dict, label: str) -> Path:
    path = resolve(str(item.get("path", "")))
    if path.is_symlink() or not path.is_file():
        raise PrivateDecodeProtocolError(f"missing regular binding: {label}")
    if path.stat().st_size != int(item.get("bytes", -1)) or sha256(path) != item.get("sha256"):
        raise PrivateDecodeProtocolError(f"size or SHA256 drift: {label}")
    return path


def atomic_json(path: Path, payload: dict) -> None:
    partial = path.with_suffix(path.suffix + ".partial")
    if path.exists() or partial.exists():
        raise PrivateDecodeProtocolError(f"refusing overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    partial.replace(path)


def atomic_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    partial = path.with_suffix(path.suffix + ".partial")
    if path.exists() or partial.exists():
        raise PrivateDecodeProtocolError(f"refusing overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with partial.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    partial.replace(path)


def require_cpu_only() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise PrivateDecodeProtocolError("CUDA_VISIBLE_DEVICES must be empty")


def video_name(task: str, condition: str) -> str:
    return sha256_text(f"{NAMESPACE}|{task}|{condition}")[:32] + ".mp4"


def build_plan() -> list[dict[str, object]]:
    statuses = read_csv(GENERATION_RUN / "trajectory_status_v2.csv")
    expected = intervention.execution_plan()
    keys = (
        "planned_task_id", "planned_unit_id", "formal_pair_id", "attribute", "role",
        "seed_index", "seed", "condition_position", "condition", "scheduler_positions",
    )
    if len(statuses) != TRAJECTORIES or [tuple(row[key] for key in keys) for row in statuses] != [
        tuple(str(row[key]) for key in keys) for row in expected
    ]:
        raise PrivateDecodeProtocolError("frozen trajectory status plan drift")
    rows: list[dict[str, object]] = []
    seen_latents: set[Path] = set()
    seen_videos: set[Path] = set()
    for status in statuses:
        if status.get("status") != "COMPLETE":
            raise PrivateDecodeProtocolError("non-complete source trajectory")
        latent = Path(status["private_latent_path"])
        if latent.parent.resolve() != LATENT_ROOT.resolve() or latent in seen_latents:
            raise PrivateDecodeProtocolError("latent path universe drift")
        video = VIDEO_ROOT / video_name(status["planned_task_id"], status["condition"])
        if video in seen_videos:
            raise PrivateDecodeProtocolError("video pseudonym collision")
        seen_latents.add(latent)
        seen_videos.add(video)
        rows.append({
            **{key: status[key] for key in keys},
            "latent_path": str(latent),
            "latent_bytes": int(status["private_latent_bytes"]),
            "latent_sha256": status["private_latent_sha256"],
            "video_path": str(video),
        })
    if len(rows) != TRAJECTORIES or len(seen_latents) != TRAJECTORIES or len(seen_videos) != TRAJECTORIES:
        raise PrivateDecodeProtocolError("decode plan cardinality drift")
    return rows


def inspect_video(path: Path) -> dict[str, object]:
    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise PrivateDecodeProtocolError(f"cannot open decoded video: {path}")
    decoded = 0
    while True:
        ok, _frame = capture.read()
        if not ok:
            break
        decoded += 1
    metadata = {
        "frame_count": decoded,
        "fps": float(capture.get(cv2.CAP_PROP_FPS)),
        "width": round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    capture.release()
    if metadata != {"frame_count": FRAMES, "fps": float(FPS), "width": WIDTH, "height": HEIGHT}:
        raise PrivateDecodeProtocolError(f"decoded-video integrity mismatch: {metadata}")
    return metadata
