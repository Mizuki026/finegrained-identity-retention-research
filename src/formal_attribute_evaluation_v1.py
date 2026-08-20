#!/usr/bin/env python3
"""Offline formal-experiment machine measurement and blinded annotation pack.

The script evaluates eyeglasses with the frozen local CLIP instrument, records
InsightFace reference-to-frame cosine similarity as a secondary diagnostic, and
prepares the seven frozen frames from each facial-hair video for two independent
blinded annotators. It does not unblind, aggregate matched-pair outcomes, impute,
exclude, or perform scientific inference.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import random
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import cv2
import numpy as np


ROOT = Path("/root/autodl-tmp/finegrained")
REPO = ROOT / "research_pipeline"
RUNTIME = ROOT / "formal_experiment_v1_runtime"
FREEZE = RUNTIME / "experiment_freeze_v1"
MASTER = FREEZE / "pre_generation_master_freeze_v1.json"
MANIFEST = FREEZE / "generation_manifest_v1.csv"
PROTOCOL = FREEZE / "attribute_metric_protocol_v1.json"
SOURCE_PROTOCOL = FREEZE / "source_attribute_metric_protocol_v2_1.json"
MODEL_HASHES = FREEZE / "metric_model_hashes_v1.csv"
INTEGRITY = RUNTIME / "post_generation_integrity_v1/video_integrity_v1.csv"
INTEGRITY_FREEZE = RUNTIME / "post_generation_integrity_v1/integrity_freeze_v1.json"
INTEGRITY_VERIFY = RUNTIME / "post_generation_integrity_independent_verification_v1.json"
CLIP_DIR = ROOT / "metric_models_v2/clip-vit-base-patch32"
FACE_ROOT = Path(
    "/root/autodl-tmp/consisid-smoketest/ckpts/"
    "ConsisID-preview/face_encoder"
)
EXPECTED_MASTER_SHA256 = (
    "149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8"
)
EXPECTED_TASKS = 160
EXPECTED_FRAMES = 49
FACIAL_FRAME_INDICES = (0, 8, 16, 24, 32, 40, 48)
ANNOTATION_NAMESPACE = "formal_facial_hair_blinding_v1_20260820"
ANNOTATOR_A_SEED = 1459215031
ANNOTATOR_B_SEED = 3318467209

EYE_FRAME_COLUMNS = [
    "schema_version", "run_id", "task_id", "formal_unit_id", "formal_pair_id",
    "role", "expected_state", "seed_index", "seed", "frame_index",
    "timestamp_seconds", "face_status", "face_bbox", "crop_box",
    "p_present", "p_absent", "margin_present_minus_absent",
    "predicted_state", "expected_state_match", "measurement_status",
    "primary_reason_code", "record_status",
]
EYE_VIDEO_COLUMNS = [
    "schema_version", "run_id", "task_id", "formal_unit_id", "formal_pair_id",
    "role", "expected_state", "seed_index", "seed", "total_frames",
    "valid_frames", "unobservable_frames", "pipeline_failure_frames",
    "valid_frame_fraction", "low_coverage_flag", "mean_expected_state_probability",
    "median_expected_state_probability", "mean_signed_expected_state_margin",
    "expected_state_match_fraction", "summary_status",
]
IDENTITY_FRAME_COLUMNS = [
    "schema_version", "run_id", "task_id", "formal_unit_id", "formal_pair_id",
    "attribute", "role", "seed_index", "seed", "frame_index",
    "timestamp_seconds", "reference_face_status", "generated_face_status",
    "generated_face_bbox", "cosine_similarity", "diagnostic_status",
    "primary_reason_code", "record_status",
]
IDENTITY_VIDEO_COLUMNS = [
    "schema_version", "run_id", "task_id", "formal_unit_id", "formal_pair_id",
    "attribute", "role", "seed_index", "seed", "total_frames", "valid_frames",
    "valid_frame_fraction", "low_coverage_flag", "mean_cosine_similarity",
    "sd_cosine_similarity", "median_cosine_similarity", "minimum_cosine_similarity",
    "maximum_cosine_similarity", "summary_status",
]
PRIVATE_COLUMNS = [
    "annotation_item_id", "task_id", "formal_unit_id", "formal_pair_id", "role",
    "expected_state", "identity_key", "seed_index", "seed", "frame_index",
    "timestamp_seconds", "source_video_path", "source_video_sha256", "crop_filename",
    "crop_method", "generated_face_status",
]
TEMPLATE_COLUMNS = [
    "annotator_id", "annotation_item_id", "random_order", "ordinal_label",
    "reason_or_note",
]


class EvaluationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise EvaluationError(message)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv_new(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_json_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True
    ).strip()


def largest_face(faces):
    if not faces:
        return None
    return max(
        faces,
        key=lambda face: float(face.bbox[2] - face.bbox[0])
        * float(face.bbox[3] - face.bbox[1]),
    )


def face_square(bbox, width: int, height: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = map(float, bbox)
    side = min(max(1.35 * (x1 - x0), 1.35 * (y1 - y0)), min(width, height))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    size = round(side)
    x = max(0, min(round(cx - side / 2), width - size))
    y = max(0, min(round(cy - side / 2), height - size))
    if size < 2:
        fail("invalid deterministic face crop")
    return x, y, x + size, y + size


def normalized_embedding(face) -> np.ndarray:
    value = getattr(face, "normed_embedding", None)
    if value is None:
        value = np.asarray(face.embedding, dtype=np.float32)
        norm = float(np.linalg.norm(value))
        if norm == 0:
            fail("zero-norm InsightFace embedding")
        value = value / norm
    return np.asarray(value, dtype=np.float32)


def validate_inputs(confirm_sha: str, output_dir: Path) -> tuple[list[dict], dict[str, dict]]:
    if os.environ.get("CUDA_VISIBLE_DEVICES") not in ("", "-1"):
        fail("CUDA_VISIBLE_DEVICES must be disabled for CPU-only evaluation")
    if output_dir.exists() or output_dir.with_name(output_dir.name + ".inprogress").exists():
        fail(f"refusing to overwrite existing output or in-progress directory: {output_dir}")
    if confirm_sha != EXPECTED_MASTER_SHA256 or sha256_path(MASTER) != EXPECTED_MASTER_SHA256:
        fail("master-freeze SHA256 confirmation mismatch")
    required = (
        MANIFEST, PROTOCOL, SOURCE_PROTOCOL, MODEL_HASHES, INTEGRITY,
        INTEGRITY_FREEZE, INTEGRITY_VERIFY, CLIP_DIR / "pytorch_model.bin",
    )
    for path in required:
        if not path.is_file() or path.is_symlink():
            fail(f"missing or invalid input: {path}")
    integrity_freeze = json.loads(INTEGRITY_FREEZE.read_text(encoding="utf-8"))
    integrity_verify = json.loads(INTEGRITY_VERIFY.read_text(encoding="utf-8"))
    if integrity_freeze.get("status") != "FROZEN_ENGINEERING_INTEGRITY_PASS":
        fail("engineering integrity freeze is not PASS")
    if integrity_verify.get("status") != "PASS_INDEPENDENT_ENGINEERING_INTEGRITY_VERIFICATION":
        fail("independent engineering integrity verification is not PASS")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_FORMAL_GENERATION":
        fail("formal metric protocol is not frozen")
    if protocol.get("facial_hair", {}).get("frame_indices") != list(FACIAL_FRAME_INDICES):
        fail("facial-hair frame-index protocol drift")
    for row in read_csv(MODEL_HASHES):
        path = Path(row["absolute_path"])
        if not path.is_file() or path.stat().st_size != int(row["size_bytes"]):
            fail(f"metric model file missing or size drift: {path}")
        if sha256_path(path) != row["sha256"]:
            fail(f"metric model SHA256 drift: {path}")
    manifest = read_csv(MANIFEST)
    integrity = read_csv(INTEGRITY)
    if len(manifest) != EXPECTED_TASKS or len(integrity) != EXPECTED_TASKS:
        fail("formal evaluation universe is not exactly 160 tasks")
    imap = {row["task_id"]: row for row in integrity}
    if len(imap) != EXPECTED_TASKS or any(row["engineering_status"] != "PASS" for row in integrity):
        fail("engineering integrity does not contain exactly 160 PASS tasks")
    attributes = Counter(row["attribute"] for row in manifest)
    if attributes != {"eyeglasses": 80, "facial_hair": 80}:
        fail(f"formal attribute task counts mismatch: {dict(attributes)}")
    for row in manifest:
        observed = imap.get(row["task_id"])
        video = Path(row["expected_video_path"])
        reference = Path(row["reference_image_path"])
        if observed is None or observed["video_path"] != str(video):
            fail(f"integrity mapping mismatch: {row['task_id']}")
        if not video.is_file() or sha256_path(video) != observed["video_sha256"]:
            fail(f"video SHA256 drift: {row['task_id']}")
        if not reference.is_file() or sha256_path(reference) != row["reference_image_sha256"]:
            fail(f"reference SHA256 drift: {row['task_id']}")
    if shutil.disk_usage(ROOT).free < 5 * (1 << 30):
        fail("less than 5 GiB free on data disk")
    return manifest, imap


def load_models():
    import torch
    from insightface.app import FaceAnalysis
    from transformers import CLIPModel, CLIPProcessor

    torch.set_num_threads(1)
    if torch.cuda.is_available():
        fail("torch reports CUDA available during CPU-only evaluation")
    clip = CLIPModel.from_pretrained(str(CLIP_DIR), local_files_only=True).to("cpu").eval()
    processor = CLIPProcessor.from_pretrained(str(CLIP_DIR), local_files_only=True)
    face = FaceAnalysis(
        name="antelopev2", root=str(FACE_ROOT), providers=["CPUExecutionProvider"]
    )
    face.prepare(ctx_id=-1, det_size=(640, 640))
    return torch, clip, processor, face


def clip_prototypes(torch, clip, processor):
    spec = json.loads(SOURCE_PROTOCOL.read_text(encoding="utf-8"))["eyeglasses"]
    positive = spec["prompt_bank"]["positive_prompts"]
    negative = spec["prompt_bank"]["negative_prompts"]
    with torch.no_grad():
        embeddings = clip.get_text_features(
            **processor(text=positive + negative, return_tensors="pt", padding=True)
        )
        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
    pos = embeddings[: len(positive)].mean(0)
    neg = embeddings[len(positive) :].mean(0)
    return pos / pos.norm(), neg / neg.norm()


def score_eye_batch(torch, clip, processor, images, prototypes):
    with torch.no_grad():
        values = clip.get_image_features(
            **processor(images=images, return_tensors="pt")
        )
        values = values / values.norm(dim=-1, keepdim=True)
        logits = torch.stack((values @ prototypes[0], values @ prototypes[1]), dim=1)
        logits = logits * clip.logit_scale.exp()
        probabilities = torch.softmax(logits, dim=1).cpu().numpy()
    return probabilities


def video_summary_eye(rows: list[dict], task: dict, run_id: str) -> dict:
    import statistics

    valid = [row for row in rows if row["measurement_status"] == "VALID_OBSERVABLE"]
    unavailable = sum(row["measurement_status"] == "UNOBSERVABLE" for row in rows)
    failures = sum(row["measurement_status"] == "PIPELINE_FAILURE" for row in rows)
    expected = task["expected_state"]
    probabilities = [
        float(row["p_present"] if expected == "present" else row["p_absent"])
        for row in valid
    ]
    margins = [
        float(row["margin_present_minus_absent"])
        * (1.0 if expected == "present" else -1.0)
        for row in valid
    ]
    matches = [row["expected_state_match"] == "true" for row in valid]
    fraction = len(valid) / EXPECTED_FRAMES
    return {
        "schema_version": "1", "run_id": run_id, "task_id": task["task_id"],
        "formal_unit_id": task["formal_unit_id"], "formal_pair_id": task["formal_pair_id"],
        "role": task["role"], "expected_state": expected,
        "seed_index": task["seed_index"], "seed": task["seed"],
        "total_frames": str(EXPECTED_FRAMES), "valid_frames": str(len(valid)),
        "unobservable_frames": str(unavailable), "pipeline_failure_frames": str(failures),
        "valid_frame_fraction": f"{fraction:.8f}",
        "low_coverage_flag": str(fraction < 0.5).lower(),
        "mean_expected_state_probability": f"{statistics.mean(probabilities):.8f}" if probabilities else "",
        "median_expected_state_probability": f"{statistics.median(probabilities):.8f}" if probabilities else "",
        "mean_signed_expected_state_margin": f"{statistics.mean(margins):.8f}" if margins else "",
        "expected_state_match_fraction": f"{sum(matches) / len(matches):.8f}" if matches else "",
        "summary_status": "COMPLETE" if not failures else "COMPLETE_WITH_PIPELINE_FAILURES",
    }


def video_summary_identity(rows: list[dict], task: dict, run_id: str) -> dict:
    import statistics

    values = [float(row["cosine_similarity"]) for row in rows if row["cosine_similarity"]]
    fraction = len(values) / EXPECTED_FRAMES
    return {
        "schema_version": "1", "run_id": run_id, "task_id": task["task_id"],
        "formal_unit_id": task["formal_unit_id"], "formal_pair_id": task["formal_pair_id"],
        "attribute": task["attribute"], "role": task["role"],
        "seed_index": task["seed_index"], "seed": task["seed"],
        "total_frames": str(EXPECTED_FRAMES), "valid_frames": str(len(values)),
        "valid_frame_fraction": f"{fraction:.8f}",
        "low_coverage_flag": str(fraction < 0.5).lower(),
        "mean_cosine_similarity": f"{statistics.mean(values):.8f}" if values else "",
        "sd_cosine_similarity": f"{statistics.stdev(values):.8f}" if len(values) > 1 else "",
        "median_cosine_similarity": f"{statistics.median(values):.8f}" if values else "",
        "minimum_cosine_similarity": f"{min(values):.8f}" if values else "",
        "maximum_cosine_similarity": f"{max(values):.8f}" if values else "",
        "summary_status": "COMPLETE" if values else "NO_VALID_IDENTITY_FRAMES",
    }


def make_contact_pages(crops: Path, template: list[dict], output: Path, annotator: str) -> int:
    from PIL import Image, ImageDraw, ImageFont

    output.mkdir()
    font = ImageFont.load_default()
    page_size = 70
    columns, cell_w, cell_h = 7, 240, 280
    for page_index, start in enumerate(range(0, len(template), page_size), 1):
        subset = template[start : start + page_size]
        rows = (len(subset) + columns - 1) // columns
        sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
        draw = ImageDraw.Draw(sheet)
        for offset, item in enumerate(subset):
            x = (offset % columns) * cell_w
            y = (offset // columns) * cell_h
            image = Image.open(crops / f"{item['annotation_item_id']}.jpg").convert("RGB")
            image.thumbnail((cell_w - 20, cell_h - 42))
            ix = x + (cell_w - image.width) // 2
            iy = y + 32 + (cell_h - 42 - image.height) // 2
            sheet.paste(image, (ix, iy))
            draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline="#888888")
            draw.text((x + 6, y + 6), item["annotation_item_id"], fill="black", font=font)
        path = output / f"facial_hair_{annotator}_page_{page_index:02d}.png"
        sheet.save(path, optimize=True)
    return (len(template) + page_size - 1) // page_size


def instrument_smoke(confirm_sha: str, output_dir: Path) -> None:
    from PIL import Image

    manifest, _ = validate_inputs(confirm_sha, output_dir)
    torch, clip, processor, face = load_models()
    prototypes = clip_prototypes(torch, clip, processor)
    task = next(row for row in manifest if row["attribute"] == "eyeglasses")
    reference = cv2.imread(task["reference_image_path"])
    selected = largest_face(face.get(reference))
    if selected is None:
        fail("smoke test found no face in reference")
    x0, y0, x1, y1 = face_square(selected.bbox, reference.shape[1], reference.shape[0])
    image = Image.fromarray(reference[y0:y1, x0:x1, ::-1])
    probabilities = score_eye_batch(torch, clip, processor, [image], prototypes)[0]
    if abs(float(probabilities.sum()) - 1.0) > 1e-5:
        fail("smoke-test CLIP probabilities do not sum to one")
    print(json.dumps({
        "status": "FORMAL_INSTRUMENT_SMOKE_PASS", "network_used": False,
        "outputs_written": False, "reference_face_detected": True,
        "p_present_plus_p_absent": float(probabilities.sum()),
    }, indent=2))


def run(output_dir: Path, confirm_sha: str, run_id: str) -> None:
    from PIL import Image

    manifest, imap = validate_inputs(confirm_sha, output_dir)
    work = output_dir.with_name(output_dir.name + ".inprogress")
    work.mkdir(parents=True)
    crops_dir = work / "facial_hair_blinded_crops_v1"
    private_dir = work / "private_mapping_v1"
    materials_dir = work / "facial_hair_annotation_materials_v1"
    crops_dir.mkdir(); private_dir.mkdir(); materials_dir.mkdir()
    log = (work / "formal_attribute_evaluation_v1.log").open("x", encoding="utf-8")
    log.write(f"{now()} RUN_START\n")
    torch, clip, processor, face = load_models()
    prototypes = clip_prototypes(torch, clip, processor)
    eye_frames: list[dict] = []
    eye_videos: list[dict] = []
    identity_frames: list[dict] = []
    identity_videos: list[dict] = []
    private_rows: list[dict] = []
    for task_number, task in enumerate(manifest, 1):
        task_id = task["task_id"]
        reference = cv2.imread(task["reference_image_path"])
        if reference is None:
            fail(f"cannot read reference image: {task_id}")
        reference_face = largest_face(face.get(reference))
        reference_embedding = normalized_embedding(reference_face) if reference_face is not None else None
        cap = cv2.VideoCapture(task["expected_video_path"])
        if not cap.isOpened():
            fail(f"cannot open frozen video: {task_id}")
        local_eye_rows: list[dict] = []
        local_identity_rows: list[dict] = []
        eye_pending = []
        for frame_index in range(EXPECTED_FRAMES):
            ok, frame = cap.read()
            if not ok:
                fail(f"decode failure: {task_id} frame {frame_index}")
            selected = largest_face(face.get(frame))
            bbox = ",".join(f"{float(value):.2f}" for value in selected.bbox) if selected is not None else ""
            identity = {
                "schema_version": "1", "run_id": run_id, "task_id": task_id,
                "formal_unit_id": task["formal_unit_id"], "formal_pair_id": task["formal_pair_id"],
                "attribute": task["attribute"], "role": task["role"],
                "seed_index": task["seed_index"], "seed": task["seed"],
                "frame_index": str(frame_index), "timestamp_seconds": f"{frame_index / 8:.6f}",
                "reference_face_status": "DETECTED" if reference_embedding is not None else "NOT_DETECTED",
                "generated_face_status": "DETECTED" if selected is not None else "NOT_DETECTED",
                "generated_face_bbox": bbox, "cosine_similarity": "",
                "diagnostic_status": "UNOBSERVABLE", "primary_reason_code": "",
                "record_status": "PRODUCED",
            }
            if reference_embedding is None:
                identity["primary_reason_code"] = "REFERENCE_FACE_NOT_DETECTED"
            elif selected is None:
                identity["primary_reason_code"] = "GENERATED_FACE_NOT_DETECTED"
            else:
                cosine = float(np.dot(reference_embedding, normalized_embedding(selected)))
                identity["cosine_similarity"] = f"{cosine:.8f}"
                identity["diagnostic_status"] = "VALID_OBSERVABLE"
            local_identity_rows.append(identity)

            if task["attribute"] == "eyeglasses":
                row = {
                    "schema_version": "1", "run_id": run_id, "task_id": task_id,
                    "formal_unit_id": task["formal_unit_id"], "formal_pair_id": task["formal_pair_id"],
                    "role": task["role"], "expected_state": task["expected_state"],
                    "seed_index": task["seed_index"], "seed": task["seed"],
                    "frame_index": str(frame_index), "timestamp_seconds": f"{frame_index / 8:.6f}",
                    "face_status": "DETECTED" if selected is not None else "NOT_DETECTED",
                    "face_bbox": bbox, "crop_box": "", "p_present": "", "p_absent": "",
                    "margin_present_minus_absent": "", "predicted_state": "",
                    "expected_state_match": "", "measurement_status": "UNOBSERVABLE",
                    "primary_reason_code": "NO_FACE_DETECTED" if selected is None else "",
                    "record_status": "PRODUCED",
                }
                if selected is not None:
                    x0, y0, x1, y1 = face_square(selected.bbox, frame.shape[1], frame.shape[0])
                    row["crop_box"] = f"{x0},{y0},{x1},{y1}"
                    image = Image.fromarray(frame[y0:y1, x0:x1, ::-1])
                    eye_pending.append((row, image))
                local_eye_rows.append(row)
            elif frame_index in FACIAL_FRAME_INDICES:
                item = "FHA_" + hashlib.sha256(
                    f"{ANNOTATION_NAMESPACE}|{task_id}|{frame_index}".encode()
                ).hexdigest()[:16].upper()
                if selected is not None:
                    x0, y0, x1, y1 = face_square(selected.bbox, frame.shape[1], frame.shape[0])
                    crop = frame[y0:y1, x0:x1]
                    method = "largest_face_square_1.35"
                else:
                    crop = frame
                    method = "full_frame_no_face_detected"
                crop_path = crops_dir / f"{item}.jpg"
                if not cv2.imwrite(str(crop_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                    fail(f"cannot write blinded crop: {item}")
                private_rows.append({
                    "annotation_item_id": item, "task_id": task_id,
                    "formal_unit_id": task["formal_unit_id"], "formal_pair_id": task["formal_pair_id"],
                    "role": task["role"], "expected_state": task["expected_state"],
                    "identity_key": task["identity_key"], "seed_index": task["seed_index"],
                    "seed": task["seed"], "frame_index": str(frame_index),
                    "timestamp_seconds": f"{frame_index / 8:.6f}",
                    "source_video_path": task["expected_video_path"],
                    "source_video_sha256": imap[task_id]["video_sha256"],
                    "crop_filename": crop_path.name, "crop_method": method,
                    "generated_face_status": "DETECTED" if selected is not None else "NOT_DETECTED",
                })
        cap.release()
        if len(local_identity_rows) != EXPECTED_FRAMES:
            fail(f"identity frame universe mismatch: {task_id}")
        if task["attribute"] == "eyeglasses":
            if eye_pending:
                probabilities = score_eye_batch(
                    torch, clip, processor, [value[1] for value in eye_pending], prototypes
                )
                for (row, _), probability in zip(eye_pending, probabilities):
                    p_present, p_absent = map(float, probability)
                    margin = p_present - p_absent
                    predicted = "present" if margin > 0 else ("absent" if margin < 0 else "")
                    row.update({
                        "p_present": f"{p_present:.8f}", "p_absent": f"{p_absent:.8f}",
                        "margin_present_minus_absent": f"{margin:.8f}",
                        "predicted_state": predicted,
                        "expected_state_match": str(predicted == task["expected_state"]).lower() if predicted else "",
                        "measurement_status": "VALID_OBSERVABLE" if predicted else "UNOBSERVABLE",
                        "primary_reason_code": "" if predicted else "EXACT_MARGIN_TIE",
                    })
            eye_frames.extend(local_eye_rows)
            eye_videos.append(video_summary_eye(local_eye_rows, task, run_id))
        identity_frames.extend(local_identity_rows)
        identity_videos.append(video_summary_identity(local_identity_rows, task, run_id))
        log.write(f"{now()} TASK_COMPLETE {task_id}\n"); log.flush()
        if task_number % 10 == 0 or task_number == EXPECTED_TASKS:
            print(f"measurement {task_number}/{EXPECTED_TASKS}", flush=True)

    if len(eye_frames) != 80 * EXPECTED_FRAMES or len(eye_videos) != 80:
        fail("eyeglasses output universe mismatch")
    if len(identity_frames) != EXPECTED_TASKS * EXPECTED_FRAMES or len(identity_videos) != EXPECTED_TASKS:
        fail("identity diagnostic universe mismatch")
    if len(private_rows) != 80 * len(FACIAL_FRAME_INDICES):
        fail("facial-hair annotation universe mismatch")
    if len({row["annotation_item_id"] for row in private_rows}) != len(private_rows):
        fail("duplicate annotation item IDs")

    write_csv_new(work / "eyeglasses_frame_measurements_v1.csv", EYE_FRAME_COLUMNS, eye_frames)
    write_csv_new(work / "eyeglasses_video_summary_v1.csv", EYE_VIDEO_COLUMNS, eye_videos)
    write_csv_new(work / "identity_frame_diagnostics_v1.csv", IDENTITY_FRAME_COLUMNS, identity_frames)
    write_csv_new(work / "identity_video_summary_v1.csv", IDENTITY_VIDEO_COLUMNS, identity_videos)
    private_path = private_dir / "facial_hair_private_mapping_v1.csv"
    write_csv_new(private_path, PRIVATE_COLUMNS, private_rows)
    private_path.chmod(0o400)

    item_ids = [row["annotation_item_id"] for row in private_rows]
    templates = {}
    for annotator, seed in (("A", ANNOTATOR_A_SEED), ("B", ANNOTATOR_B_SEED)):
        ordered = list(item_ids); random.Random(seed).shuffle(ordered)
        rows = [
            {"annotator_id": annotator, "annotation_item_id": item,
             "random_order": str(index), "ordinal_label": "", "reason_or_note": ""}
            for index, item in enumerate(ordered, 1)
        ]
        templates[annotator] = rows
        directory = materials_dir / f"annotator_{annotator}"
        directory.mkdir()
        write_csv_new(directory / f"facial_hair_annotator_{annotator}_v1.csv", TEMPLATE_COLUMNS, rows)
        pages = make_contact_pages(crops_dir, rows, directory / "contact_sheets", annotator)
        (directory / "README.txt").write_text(
            "Use only the CSV and contact sheets in this directory. Do not access the private mapping.\n"
            "Enter one ordinal_label per row: 0, 1, 2, or U. Preserve item IDs and random_order.\n"
            f"Contact-sheet pages: {pages}.\n",
            encoding="utf-8",
        )
    codebook = (
        "Formal facial-hair blinded annotation codebook v1\n\n"
        "0 = no visible facial hair\n"
        "1 = faint, sparse, or ambiguous visible facial hair\n"
        "2 = clearly visible moustache, beard, goatee, or stubble\n"
        "U = target attribute cannot be observed reliably in the crop\n\n"
        "Annotate each item independently. Do not infer condition, identity, seed, or pair.\n"
        "Use reason_or_note for uncertainty or technical concerns. Do not alter other columns.\n"
    )
    (materials_dir / "facial_hair_codebook_v1.txt").write_text(codebook, encoding="utf-8")
    log.write(f"{now()} MACHINE_MEASUREMENT_COMPLETE_MANUAL_ANNOTATION_PENDING\n")
    log.close()

    hashes = []
    for path in sorted(work.rglob("*")):
        if path.is_file() and path.name != "output_hashes_v1.csv":
            hashes.append({"relative_path": str(path.relative_to(work)), "sha256": sha256_path(path), "bytes": path.stat().st_size})
    write_csv_new(work / "output_hashes_v1.csv", ["relative_path", "sha256", "bytes"], hashes)
    audit = {
        "schema_version": 1, "run_id": run_id, "completed_at_utc": now(),
        "script_sha256": sha256_path(Path(__file__)), "code_commit": git_commit(),
        "master_freeze_sha256": EXPECTED_MASTER_SHA256,
        "inputs": {
            "generation_manifest": sha256_path(MANIFEST), "metric_protocol": sha256_path(PROTOCOL),
            "source_metric_protocol": sha256_path(SOURCE_PROTOCOL),
            "metric_model_hashes": sha256_path(MODEL_HASHES),
            "integrity_freeze": sha256_path(INTEGRITY_FREEZE),
            "integrity_verification": sha256_path(INTEGRITY_VERIFY),
        },
        "row_counts": {
            "eyeglasses_frames": len(eye_frames), "eyeglasses_videos": len(eye_videos),
            "identity_frames": len(identity_frames), "identity_videos": len(identity_videos),
            "facial_hair_annotation_items": len(private_rows),
        },
        "annotation": {
            "sampled_frame_indices": list(FACIAL_FRAME_INDICES),
            "annotator_A_randomization_seed": ANNOTATOR_A_SEED,
            "annotator_B_randomization_seed": ANNOTATOR_B_SEED,
            "private_mapping_access_required_by_annotators": False,
            "condition_identity_seed_blinded": True,
        },
        "network_used": False, "gpu_used": False, "generation_performed": False,
        "regeneration_performed": False, "imputation_performed": False,
        "exclusion_performed": False, "matched_pair_analysis_performed": False,
        "scientific_outcome_interpretation_performed": False,
        "status": "MACHINE_MEASUREMENT_COMPLETE_MANUAL_ANNOTATION_PENDING",
        "boundary": "Fixed finite panel; no causal, population-model, or frame-independent inference.",
    }
    write_json_new(work / "formal_attribute_execution_audit_v1.json", audit)
    write_json_new(work / "machine_measurement_freeze_v1.json", {
        "schema_version": 1, "freeze_id": "formal_machine_measurement_v1",
        "frozen_at_utc": now(), "master_freeze_sha256": EXPECTED_MASTER_SHA256,
        "output_hash_inventory_sha256": sha256_path(work / "output_hashes_v1.csv"),
        "eyeglasses_video_rows": len(eye_videos), "identity_video_rows": len(identity_videos),
        "facial_hair_annotation_items": len(private_rows),
        "status": "FROZEN_MACHINE_MEASUREMENT_MANUAL_ANNOTATION_PENDING",
    })
    work.rename(output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("dry-run", "instrument-smoke", "run"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confirm-master-sha256", required=True)
    parser.add_argument("--run-id", default="formal_attribute_evaluation_v1")
    args = parser.parse_args()
    if args.mode == "dry-run":
        manifest, _ = validate_inputs(args.confirm_master_sha256, args.output_dir)
        print(json.dumps({
            "status": "PREFLIGHT_PASS", "tasks": len(manifest),
            "eyeglasses_tasks": sum(row["attribute"] == "eyeglasses" for row in manifest),
            "facial_hair_tasks": sum(row["attribute"] == "facial_hair" for row in manifest),
            "models_loaded": False, "videos_opened": False, "outputs_written": False,
        }, indent=2))
    elif args.mode == "instrument-smoke":
        instrument_smoke(args.confirm_master_sha256, args.output_dir)
    else:
        run(args.output_dir, args.confirm_master_sha256, args.run_id)
        print(json.dumps({
            "status": "MACHINE_MEASUREMENT_COMPLETE_MANUAL_ANNOTATION_PENDING",
            "output_dir": str(args.output_dir), "scientific_outcomes_printed": False,
        }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except EvaluationError as exc:
        raise SystemExit(f"FORMAL EVALUATION FAILED: {exc}")
