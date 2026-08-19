#!/usr/bin/env python3
"""Fail-closed controller for the frozen formal ConsisID generation manifest."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise RuntimeError(f"refusing to overwrite execution artifact: {path}")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def git_value(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def inspect_video(path: Path) -> dict:
    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV cannot open generated video: {path}")
    decoded = 0
    while True:
        ok, _frame = capture.read()
        if not ok:
            break
        decoded += 1
    metadata = {
        "frame_count": decoded,
        "fps": float(capture.get(cv2.CAP_PROP_FPS)),
        "width": int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH))),
        "height": int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))),
    }
    capture.release()
    if metadata != {"frame_count": 49, "fps": 8.0, "width": 720, "height": 480}:
        raise RuntimeError(f"generated-video integrity mismatch: {metadata}")
    return metadata


def validate_freeze(master_path: Path, expected_hash: str) -> tuple[dict, list[dict[str, str]]]:
    if sha256(master_path) != expected_hash:
        raise RuntimeError("master-freeze SHA256 does not match --confirm-freeze-sha256")
    master = json.loads(master_path.read_text(encoding="utf-8"))
    if master.get("status") != "FROZEN_READY_FOR_FORMAL_GENERATION":
        raise RuntimeError("master freeze is not ready for formal generation")
    if master["execution_gate"].get("generation_may_begin") is not True:
        raise RuntimeError("generation gate is closed")

    artifacts = master["artifacts"]
    for name, item in artifacts.items():
        path = Path(item["path"])
        if not path.is_file():
            raise RuntimeError(f"required artifact missing ({name}): {path}")
        if sha256(path) != item["sha256"]:
            raise RuntimeError(f"artifact hash drift ({name}): {path}")

    research_repo = Path(master["code"]["research_repository"])
    consisid_repo = Path(master["consisid"]["repository"])
    if git_value(research_repo, "rev-parse", "HEAD") != master["code"]["commit"]:
        raise RuntimeError("research repository commit drift")
    if git_value(research_repo, "status", "--short"):
        raise RuntimeError("research repository working tree is not clean")
    if git_value(consisid_repo, "rev-parse", "HEAD") != master["consisid"]["commit"]:
        raise RuntimeError("ConsisID commit drift")
    if git_value(consisid_repo, "status", "--short"):
        raise RuntimeError("ConsisID working tree is not clean")

    manifest_path = Path(artifacts["generation_manifest"]["path"])
    rows = read_csv(manifest_path)
    if len(rows) != 160:
        raise RuntimeError(f"expected 160 generation rows, found {len(rows)}")
    units = {row["formal_unit_id"] for row in rows}
    if len(units) != 40:
        raise RuntimeError("generation manifest is not exactly 40 units")
    seed_sets = {
        unit: tuple(int(row["seed"]) for row in rows if row["formal_unit_id"] == unit)
        for unit in units
    }
    if len(set(seed_sets.values())) != 1 or len(next(iter(seed_sets.values()))) != 4:
        raise RuntimeError("the same four-seed bank is not crossed with every reference")
    if len({row["task_id"] for row in rows}) != 160:
        raise RuntimeError("task IDs are not unique")
    for row in rows:
        image = Path(row["reference_image_path"])
        if not image.is_file() or sha256(image) != row["reference_image_sha256"]:
            raise RuntimeError(f"reference image drift: {row['task_id']}")
    return master, rows


def verify_weights(master: dict) -> None:
    model_root = Path(master["generation"]["model_path"])
    inventory = Path(master["artifacts"]["model_weight_hashes"]["path"])
    for row in read_csv(inventory):
        path = model_root / row["relative_path"]
        if not path.is_file():
            raise RuntimeError(f"model file missing: {path}")
        if path.stat().st_size != int(row["size_bytes"]) or sha256(path) != row["sha256"]:
            raise RuntimeError(f"model file drift: {path}")


def existing_state(rows: list[dict[str, str]]) -> tuple[int, int]:
    videos = sum(Path(row["expected_video_path"]).is_file() for row in rows)
    records = sum(Path(row["execution_record_path"]).is_file() for row in rows)
    return videos, records


def recover_or_verify(row: dict[str, str], master_hash: str) -> bool:
    video = Path(row["expected_video_path"])
    record = Path(row["execution_record_path"])
    if record.is_file():
        data = json.loads(record.read_text(encoding="utf-8"))
        if data.get("status") not in {"SUCCESS_FROZEN_OUTPUT", "RECOVERED_FROZEN_OUTPUT"}:
            raise RuntimeError(f"non-success execution record exists: {record}")
        if data.get("master_freeze_sha256") != master_hash:
            raise RuntimeError(f"execution record belongs to another freeze: {record}")
        if not video.is_file() or sha256(video) != data.get("video_sha256"):
            raise RuntimeError(f"recorded video missing or changed: {video}")
        inspect_video(video)
        return True
    if video.is_file():
        metadata = inspect_video(video)
        atomic_json(
            record,
            {
                "schema_version": 1,
                "status": "RECOVERED_FROZEN_OUTPUT",
                "recovered_at_utc": utc_now(),
                "task_id": row["task_id"],
                "formal_unit_id": row["formal_unit_id"],
                "seed_index": int(row["seed_index"]),
                "seed": int(row["seed"]),
                "video_path": str(video),
                "video_sha256": sha256(video),
                "video_size_bytes": video.stat().st_size,
                "master_freeze_sha256": master_hash,
                **metadata,
                "note": "Video completed before controller record finalization; no regeneration occurred.",
            },
        )
        return True
    if video.parent.exists() and any(video.parent.iterdir()):
        raise RuntimeError(f"unexpected partial task directory: {video.parent}")
    return False


def run_task(row: dict[str, str], master: dict, master_hash: str) -> None:
    video = Path(row["expected_video_path"])
    record = Path(row["execution_record_path"])
    log = Path(row["log_path"])
    video.parent.mkdir(parents=True, exist_ok=True)
    if any(video.parent.iterdir()):
        raise RuntimeError(f"task directory is not empty: {video.parent}")
    log.parent.mkdir(parents=True, exist_ok=True)
    if record.exists() or log.exists():
        raise RuntimeError(f"execution artifact collision for {row['task_id']}")

    generation = master["generation"]
    command = [
        master["environment"]["python"],
        str(Path(master["consisid"]["repository"]) / "infer.py"),
        "--model_path", generation["model_path"],
        "--img_file_path", row["reference_image_path"],
        "--prompt", generation["prompt"],
        "--output_path", str(video.parent),
        "--guidance_scale", str(generation["guidance_scale"]),
        "--num_inference_steps", str(generation["num_inference_steps"]),
        "--num_videos_per_prompt", "1",
        "--dtype", generation["dtype"],
        "--seed", row["seed"],
    ]
    environment = os.environ.copy()
    environment.update(
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        TOKENIZERS_PARALLELISM="false",
        CUDA_VISIBLE_DEVICES="0",
    )
    started = utc_now()
    with log.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps({"started_at_utc": started, "task_id": row["task_id"], "command": command}) + "\n")
        handle.flush()
        result = subprocess.run(
            command,
            cwd=master["consisid"]["repository"],
            env=environment,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
    if result.returncode != 0:
        raise RuntimeError(f"ConsisID failed for {row['task_id']}; see {log}")
    if not video.is_file():
        raise RuntimeError(f"expected video was not created: {video}")
    if len(list(video.parent.glob("*.mp4"))) != 1:
        raise RuntimeError(f"task directory does not contain exactly one MP4: {video.parent}")
    metadata = inspect_video(video)
    atomic_json(
        record,
        {
            "schema_version": 1,
            "status": "SUCCESS_FROZEN_OUTPUT",
            "started_at_utc": started,
            "completed_at_utc": utc_now(),
            "return_code": result.returncode,
            "task_id": row["task_id"],
            "formal_unit_id": row["formal_unit_id"],
            "formal_pair_id": row["formal_pair_id"],
            "attribute": row["attribute"],
            "role": row["role"],
            "seed_index": int(row["seed_index"]),
            "seed": int(row["seed"]),
            "reference_image_path": row["reference_image_path"],
            "reference_image_sha256": row["reference_image_sha256"],
            "video_path": str(video),
            "video_sha256": sha256(video),
            "video_size_bytes": video.stat().st_size,
            "log_path": str(log),
            "master_freeze_sha256": master_hash,
            "manual_substitution": False,
            "seed_change": False,
            **metadata,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "run"), required=True)
    parser.add_argument("--master-freeze", type=Path, required=True)
    parser.add_argument("--confirm-freeze-sha256", required=True)
    parser.add_argument("--verify-all-weights", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    master, rows = validate_freeze(args.master_freeze, args.confirm_freeze_sha256)
    if args.verify_all_weights:
        verify_weights(master)
    videos, records = existing_state(rows)
    if args.mode == "preflight":
        if videos or records:
            raise RuntimeError(f"formal output is not empty: videos={videos}, records={records}")
        print(json.dumps({
            "status": "FORMAL_GENERATION_PREFLIGHT_PASS",
            "tasks": len(rows),
            "reference_units": 40,
            "shared_seeds": sorted({int(row["seed"]) for row in rows}),
            "existing_videos": videos,
            "existing_records": records,
            "all_weights_verified": args.verify_all_weights,
            "generation_performed": False,
        }, indent=2))
        return

    if (videos or records) and not args.resume:
        raise RuntimeError("formal outputs already exist; exact recovery requires --resume")
    output_root = Path(master["generation"]["output_root"])
    output_root.mkdir(parents=True, exist_ok=True)
    session_dir = output_root / "execution_records"
    session_dir.mkdir(parents=True, exist_ok=True)
    for index, row in enumerate(rows, 1):
        if args.resume and recover_or_verify(row, args.confirm_freeze_sha256):
            print(f"[{index:03d}/160] verified existing {row['task_id']}", flush=True)
            continue
        print(f"[{index:03d}/160] generating {row['task_id']}", flush=True)
        run_task(row, master, args.confirm_freeze_sha256)

    videos, records = existing_state(rows)
    if videos != 160 or records != 160:
        raise RuntimeError(f"incomplete formal generation: videos={videos}, records={records}")
    summary_path = session_dir / "formal_generation_summary_v1.json"
    atomic_json(summary_path, {
        "schema_version": 1,
        "status": "FORMAL_GENERATION_ALL_160_PASS",
        "completed_at_utc": utc_now(),
        "master_freeze_sha256": args.confirm_freeze_sha256,
        "tasks": 160,
        "reference_units": 40,
        "seeds_per_reference": 4,
        "seed_changes": False,
        "reference_substitutions": False,
        "selective_favorable_reruns": False,
    })
    print(f"Status: FORMAL_GENERATION_ALL_160_PASS\nSummary: {summary_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FORMAL_GENERATION_ABORTED: {error}", file=sys.stderr)
        raise
