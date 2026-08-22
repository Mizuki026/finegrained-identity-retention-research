#!/usr/bin/env python3
"""Run the frozen, outcome-independent face-detector coverage benchmark."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis

REPAIR = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/measurement_repair_v1")
OUT = REPAIR / "detector_benchmark_v1"


class BenchmarkError(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise BenchmarkError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields, rows):
    with path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def verify_protocol():
    freeze_path = REPAIR / "measurement_repair_protocol_freeze_v1.json"
    protocol_path = REPAIR / "measurement_repair_protocol_v1.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    require(freeze["status"] == "FROZEN_BEFORE_MEASUREMENT_REPAIR_EXECUTION", "protocol freeze status mismatch")
    require(sha256(protocol_path) == freeze["protocol_sha256"], "protocol hash mismatch")
    require(sha256(REPAIR / "detector_evaluation_manifest_v1.csv") == freeze["evaluation_manifest_sha256"], "manifest hash mismatch")
    require(sha256(REPAIR / "detector_model_hashes_v1.csv") == freeze["detector_model_hashes_sha256"], "model inventory hash mismatch")
    require(protocol["code_binding"]["benchmark_script_sha256"] == sha256(Path(__file__)), "benchmark code hash mismatch")
    for row in read_csv(REPAIR / "detector_model_hashes_v1.csv"):
        p = Path(row["absolute_path"])
        require(p.is_file() and sha256(p) == row["sha256"], f"model changed: {p}")
    return freeze, protocol


def load_frames(rows):
    frames = {}
    by_video = defaultdict(list)
    for row in rows:
        if row["source_kind"] == "reference_image":
            p = Path(row["source_path"])
            require(p.is_file() and sha256(p) == row["source_sha256"], f"reference mismatch: {p}")
            image = cv2.imread(str(p), cv2.IMREAD_COLOR)
            require(image is not None, f"cannot decode reference: {p}")
            frames[row["evaluation_item_id"]] = image
        else:
            by_video[row["source_path"]].append(row)
    for source_path, group in sorted(by_video.items()):
        p = Path(source_path)
        require(p.is_file() and sha256(p) == group[0]["source_sha256"], f"video mismatch: {p}")
        needed = {int(row["frame_index"]): row["evaluation_item_id"] for row in group}
        cap = cv2.VideoCapture(str(p))
        require(cap.isOpened(), f"cannot open video: {p}")
        index = 0
        while needed:
            ok, frame = cap.read()
            if not ok:
                break
            if index in needed:
                frames[needed.pop(index)] = frame
            index += 1
        cap.release()
        require(not needed, f"missing frozen frame(s): {p} {sorted(needed)}")
    require(len(frames) == len(rows), "decoded frame count mismatch")
    return frames


def normalize_boxes(boxes, width, height, threshold=None):
    result = []
    for box in boxes:
        x1, y1, x2, y2, score = map(float, box)
        if threshold is not None and score < threshold:
            continue
        x1, x2 = sorted((max(0.0, min(x1, width)), max(0.0, min(x2, width))))
        y1, y2 = sorted((max(0.0, min(y1, height)), max(0.0, min(y2, height))))
        if x2 <= x1 or y2 <= y1:
            continue
        result.append((x1, y1, x2, y2, score))
    return result


def run_scrfd(frames, size):
    root = "/root/autodl-tmp/consisid-smoketest/ckpts/ConsisID-preview/face_encoder"
    app = FaceAnalysis(name="antelopev2", root=root, allowed_modules=["detection"], providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=-1, det_thresh=0.1, det_size=(size, size))
    output = {}
    for item_id, image in frames.items():
        started = time.perf_counter()
        faces = app.get(image)
        elapsed = (time.perf_counter() - started) * 1000.0
        boxes = [(*face.bbox.tolist(), float(face.det_score)) for face in faces]
        output[item_id] = (boxes, elapsed)
    return output


def run_yunet(frames, model_path):
    detector = cv2.FaceDetectorYN.create(str(model_path), "", (320, 320), 0.3, 0.3, 5000)
    output = {}
    for item_id, image in frames.items():
        height, width = image.shape[:2]
        detector.setInputSize((width, height))
        started = time.perf_counter()
        _, detections = detector.detect(image)
        elapsed = (time.perf_counter() - started) * 1000.0
        boxes = []
        if detections is not None:
            for d in detections:
                x, y, w, h = map(float, d[:4])
                boxes.append((x, y, x + w, y + h, float(d[14])))
        output[item_id] = (boxes, elapsed)
    return output


def run_haar(frames, cascade_path, neighbors):
    detector = cv2.CascadeClassifier(str(cascade_path))
    require(not detector.empty(), "cannot load Haar cascade")
    output = {}
    for item_id, image in frames.items():
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        started = time.perf_counter()
        detections = detector.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=neighbors, minSize=(24, 24))
        elapsed = (time.perf_counter() - started) * 1000.0
        boxes = [(float(x), float(y), float(x + w), float(y + h), math.nan) for x, y, w, h in detections]
        output[item_id] = (boxes, elapsed)
    return output


def result_row(candidate, item, image, boxes, elapsed):
    height, width = image.shape[:2]
    threshold = candidate.get("score_threshold") if candidate["family"] != "OpenCV-Haar" else None
    boxes = normalize_boxes(boxes, width, height, threshold)
    selected = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])) if boxes else None
    area_fraction = ((selected[2] - selected[0]) * (selected[3] - selected[1]) / (width * height)) if selected else math.nan
    plausible = bool(selected and 0.01 <= area_fraction <= 0.9)
    return {
        "candidate_id": candidate["candidate_id"],
        "evaluation_item_id": item["evaluation_item_id"],
        "source_kind": item["source_kind"],
        "human_observable_reference": item["human_observable_reference"],
        "image_width": width,
        "image_height": height,
        "detected": str(bool(boxes)).lower(),
        "detection_count": len(boxes),
        "selected_score": "" if selected is None or math.isnan(selected[4]) else f"{selected[4]:.8f}",
        "bbox_x1": "" if selected is None else f"{selected[0]:.4f}",
        "bbox_y1": "" if selected is None else f"{selected[1]:.4f}",
        "bbox_x2": "" if selected is None else f"{selected[2]:.4f}",
        "bbox_y2": "" if selected is None else f"{selected[3]:.4f}",
        "bbox_area_fraction": "" if selected is None else f"{area_fraction:.10f}",
        "plausible_bbox": str(plausible).lower(),
        "runtime_ms": f"{elapsed:.6f}",
    }


def summarize(candidate, rows, protocol):
    def detected(subset):
        return sum(r["detected"] == "true" for r in subset)
    reference = [r for r in rows if r["source_kind"] == "reference_image"]
    facial_observable = [r for r in rows if r["source_kind"] == "facial_hair_sample_frame" and r["human_observable_reference"] == "true"]
    facial_u = [r for r in rows if r["source_kind"] == "facial_hair_sample_frame" and r["human_observable_reference"] == "false"]
    eye = [r for r in rows if r["source_kind"] == "eyeglasses_sample_frame"]
    selected = [r for r in rows if r["detected"] == "true"]
    ref_recall = detected(reference) / len(reference)
    facial_recall = detected(facial_observable) / len(facial_observable)
    plausible = sum(r["plausible_bbox"] == "true" for r in selected) / len(selected) if selected else 0.0
    gate = protocol["preliminary_detector_eligibility"]
    eligible = ref_recall >= gate["reference_image_detection_recall_minimum"] and facial_recall >= gate["human_observable_facial_hair_frame_recall_minimum"] and plausible >= gate["plausible_bbox_fraction_minimum"]
    return {
        "candidate_id": candidate["candidate_id"],
        "family": candidate["family"],
        "total_detected": detected(rows),
        "total_items": len(rows),
        "total_coverage": f"{detected(rows)/len(rows):.10f}",
        "reference_detected": detected(reference),
        "reference_items": len(reference),
        "reference_recall": f"{ref_recall:.10f}",
        "facial_hair_human_observable_detected": detected(facial_observable),
        "facial_hair_human_observable_items": len(facial_observable),
        "facial_hair_human_observable_recall": f"{facial_recall:.10f}",
        "facial_hair_U_detected": detected(facial_u),
        "facial_hair_U_items": len(facial_u),
        "eyeglasses_fixed_frames_detected": detected(eye),
        "eyeglasses_fixed_frames": len(eye),
        "eyeglasses_fixed_frame_coverage": f"{detected(eye)/len(eye):.10f}",
        "plausible_bbox_fraction_among_detected": f"{plausible:.10f}",
        "median_runtime_ms": f"{statistics.median(float(r['runtime_ms']) for r in rows):.6f}",
        "preliminary_eligible": str(eligible).lower(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["run"], default="run")
    parser.parse_args()
    require(not OUT.exists() and not OUT.with_name(OUT.name + ".inprogress").exists(), "benchmark output already exists")
    freeze, protocol = verify_protocol()
    manifest = read_csv(REPAIR / "detector_evaluation_manifest_v1.csv")
    require(len(manifest) == 1160 and len({r["evaluation_item_id"] for r in manifest}) == 1160, "benchmark universe mismatch")
    frames = load_frames(manifest)
    model_paths = {r["model_id"]: Path(r["absolute_path"]) for r in read_csv(REPAIR / "detector_model_hashes_v1.csv")}
    raw = {}
    raw[("SCRFD-10G", 640)] = run_scrfd(frames, 640)
    raw[("SCRFD-10G", 1024)] = run_scrfd(frames, 1024)
    raw[("YuNet-2023mar", "native_frame")] = run_yunet(frames, model_paths["yunet_2023mar"])
    for neighbors in (3, 5):
        raw[("OpenCV-Haar", neighbors)] = run_haar(frames, model_paths["opencv_haar_frontal_default"], neighbors)
    tmp = OUT.with_name(OUT.name + ".inprogress")
    tmp.mkdir(parents=True)
    detail = []
    summary = []
    for candidate in protocol["candidate_detectors"]:
        if candidate["family"] == "SCRFD-10G":
            source = raw[(candidate["family"], candidate["det_size"][0])]
        elif candidate["family"] == "YuNet-2023mar":
            source = raw[(candidate["family"], "native_frame")]
        else:
            source = raw[(candidate["family"], candidate["min_neighbors"])]
        candidate_rows = []
        for item in manifest:
            boxes, elapsed = source[item["evaluation_item_id"]]
            row = result_row(candidate, item, frames[item["evaluation_item_id"]], boxes, elapsed)
            candidate_rows.append(row)
            detail.append(row)
        summary.append(summarize(candidate, candidate_rows, protocol))
    require(len(detail) == 1160 * len(protocol["candidate_detectors"]), "detail row count mismatch")
    detail_fields = list(detail[0])
    summary_fields = list(summary[0])
    write_csv(tmp / "detector_item_results_v1.csv", detail_fields, detail)
    write_csv(tmp / "detector_candidate_summary_v1.csv", summary_fields, summary)
    run_record = {
        "schema_version": 1,
        "benchmark_id": "formal_measurement_repair_detector_benchmark_v1",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_freeze_sha256": sha256(REPAIR / "measurement_repair_protocol_freeze_v1.json"),
        "evaluation_items": len(manifest),
        "candidate_detectors": len(summary),
        "detail_rows": len(detail),
        "cpu_only": os.environ.get("CUDA_VISIBLE_DEVICES", "") == "",
        "attribute_effect_direction_used_for_selection": False,
        "final_detector_selected": False,
        "status": "DETECTOR_BENCHMARK_COMPLETE_PENDING_INDEPENDENT_VERIFICATION_AND_EYE_LABELS",
    }
    write_json(tmp / "detector_benchmark_run_record_v1.json", run_record)
    artifact_rows = []
    for p in sorted(tmp.iterdir()):
        if p.is_file():
            artifact_rows.append({"relative_path": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)})
    write_csv(tmp / "detector_benchmark_artifact_hashes_v1.csv", ["relative_path", "bytes", "sha256"], artifact_rows)
    freeze_out = {
        "schema_version": 1,
        "freeze_id": "formal_measurement_repair_detector_benchmark_v1_freeze",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_freeze_sha256": run_record["protocol_freeze_sha256"],
        "item_results_sha256": sha256(tmp / "detector_item_results_v1.csv"),
        "candidate_summary_sha256": sha256(tmp / "detector_candidate_summary_v1.csv"),
        "run_record_sha256": sha256(tmp / "detector_benchmark_run_record_v1.json"),
        "artifact_hashes_sha256": sha256(tmp / "detector_benchmark_artifact_hashes_v1.csv"),
        "final_detector_selected": False,
        "status": run_record["status"],
    }
    write_json(tmp / "detector_benchmark_freeze_v1.json", freeze_out)
    tmp.rename(OUT)
    print(json.dumps({"status": freeze_out["status"], "evaluation_items": len(manifest), "candidates": len(summary), "detail_rows": len(detail), "final_detector_selected": False}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except BenchmarkError as exc:
        raise SystemExit(f"DETECTOR BENCHMARK FAILED: {exc}")
