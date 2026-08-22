#!/usr/bin/env python3
"""Build two independently randomized, identity-blinded eyeglasses annotation packets."""
from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont

REPAIR = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/measurement_repair_v1")
BENCHMARK = REPAIR / "detector_benchmark_v1"
VERIFY = REPAIR / "detector_benchmark_v1_independent_verification.json"
OUT = REPAIR / "eyeglasses_blind_annotation_v1"
NAMESPACE = "formal_measurement_repair_eyeglasses_blind_annotation_v1"
RANDOMIZATION_SEEDS = {"A": 2026082201, "B": 2026082202}


class BuildError(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise BuildError(message)


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


def anonymous_id(evaluation_item_id: str) -> str:
    token = hashlib.sha256(f"{NAMESPACE}|{evaluation_item_id}".encode()).hexdigest()[:16].upper()
    return f"EYA_{token}"


def decode_frame(video_path: str, frame_index: int):
    cap = cv2.VideoCapture(video_path)
    require(cap.isOpened(), f"cannot open video: {video_path}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    require(ok and frame is not None, f"cannot decode frame {frame_index}: {video_path}")
    return frame


def render_pages(packet_dir: Path, ordered_rows, frame_dir: Path):
    pages_dir = packet_dir / "contact_sheets"
    pages_dir.mkdir()
    font = ImageFont.load_default()
    columns, rows_per_page = 4, 5
    cell_w, cell_h = 410, 330
    page_size = columns * cell_w, rows_per_page * cell_h
    per_page = columns * rows_per_page
    page_paths = []
    for page_index, start in enumerate(range(0, len(ordered_rows), per_page), 1):
        page = Image.new("RGB", page_size, "white")
        draw = ImageDraw.Draw(page)
        for offset, row in enumerate(ordered_rows[start:start + per_page]):
            x = (offset % columns) * cell_w
            y = (offset // columns) * cell_h
            draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline="#777777", width=2)
            draw.text((x + 8, y + 7), f"{row['random_order']:03d} | {row['annotation_item_id']}", fill="black", font=font)
            image = Image.open(frame_dir / f"{row['annotation_item_id']}.png").convert("RGB")
            image.thumbnail((cell_w - 16, cell_h - 42), Image.Resampling.LANCZOS)
            px = x + (cell_w - image.width) // 2
            py = y + 34 + (cell_h - 38 - image.height) // 2
            page.paste(image, (px, py))
        path = pages_dir / f"eyeglasses_annotator_{packet_dir.name}_page_{page_index:02d}_v1.png"
        page.save(path, format="PNG", optimize=True)
        page_paths.append(path)
    require(len(page_paths) == 28, "contact sheet page count mismatch")
    return page_paths


def main():
    require(not OUT.exists() and not OUT.with_name(OUT.name + ".inprogress").exists(), "annotation output already exists")
    protocol = json.loads((REPAIR / "measurement_repair_protocol_v1.json").read_text(encoding="utf-8"))
    protocol_freeze = json.loads((REPAIR / "measurement_repair_protocol_freeze_v1.json").read_text(encoding="utf-8"))
    benchmark_freeze = json.loads((BENCHMARK / "detector_benchmark_freeze_v1.json").read_text(encoding="utf-8"))
    verification = json.loads(VERIFY.read_text(encoding="utf-8"))
    require(protocol["code_binding"]["annotation_builder_script_sha256"] == sha256(Path(__file__)), "annotation builder code hash mismatch")
    require(sha256(REPAIR / "measurement_repair_protocol_v1.json") == protocol_freeze["protocol_sha256"], "protocol changed")
    require(sha256(BENCHMARK / "detector_item_results_v1.csv") == benchmark_freeze["item_results_sha256"], "benchmark detail changed")
    require(verification["status"] == "PASS_INDEPENDENT_DETECTOR_BENCHMARK_VERIFICATION", "benchmark not independently verified")
    require(verification["benchmark_freeze_sha256"] == sha256(BENCHMARK / "detector_benchmark_freeze_v1.json"), "verification does not bind benchmark")
    manifest = [r for r in read_csv(REPAIR / "detector_evaluation_manifest_v1.csv") if r["source_kind"] == "eyeglasses_sample_frame"]
    require(len(manifest) == 560 and len({r["evaluation_item_id"] for r in manifest}) == 560, "eyeglasses universe mismatch")
    tmp = OUT.with_name(OUT.name + ".inprogress")
    tmp.mkdir(parents=True)
    frame_dir = tmp / "anonymous_frames"
    private_dir = tmp / "private_mapping_v1"
    frame_dir.mkdir()
    private_dir.mkdir()
    mapping_rows = []
    for row in manifest:
        aid = anonymous_id(row["evaluation_item_id"])
        frame = decode_frame(row["source_path"], int(row["frame_index"]))
        frame_path = frame_dir / f"{aid}.png"
        require(cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_PNG_COMPRESSION, 3]), f"cannot save {frame_path}")
        mapping_rows.append({
            "annotation_item_id": aid,
            "evaluation_item_id": row["evaluation_item_id"],
            "task_id": row["task_id"],
            "formal_unit_id": row["formal_unit_id"],
            "formal_pair_id": row["formal_pair_id"],
            "role": row["role"],
            "seed_index": row["seed_index"],
            "seed": row["seed"],
            "frame_index": row["frame_index"],
            "source_video_path": row["source_path"],
            "source_video_sha256": row["source_sha256"],
            "anonymous_frame_path": str(frame_path).replace(".inprogress", ""),
            "anonymous_frame_sha256": sha256(frame_path),
        })
    require(len({r["annotation_item_id"] for r in mapping_rows}) == 560, "anonymous ID collision")
    mapping_fields = list(mapping_rows[0])
    mapping_path = private_dir / "eyeglasses_private_mapping_v1.csv"
    write_csv(mapping_path, mapping_fields, mapping_rows)
    template_fields = ["annotator_id", "annotation_item_id", "random_order", "face_eye_region_observable_yes_no", "eyeglasses_label", "annotation_confidence_high_low", "reason_or_note"]
    packet_hashes = []
    for annotator in ("A", "B"):
        packet_dir = tmp / f"annotator_{annotator}"
        packet_dir.mkdir()
        ordered = [{"annotation_item_id": r["annotation_item_id"]} for r in mapping_rows]
        random.Random(RANDOMIZATION_SEEDS[annotator]).shuffle(ordered)
        template_rows = []
        for index, row in enumerate(ordered, 1):
            template_rows.append({"annotator_id": annotator, "annotation_item_id": row["annotation_item_id"], "random_order": index, "face_eye_region_observable_yes_no": "", "eyeglasses_label": "", "annotation_confidence_high_low": "", "reason_or_note": ""})
        template_path = packet_dir / f"eyeglasses_annotator_{annotator}_v1.csv"
        write_csv(template_path, template_fields, template_rows)
        render_pages(packet_dir, template_rows, frame_dir)
        packet_hashes.append({"annotator": annotator, "randomization_seed": RANDOMIZATION_SEEDS[annotator], "template_sha256": sha256(template_path), "contact_sheet_pages": 28})
    codebook = """FORMAL MEASUREMENT-REPAIR V1: EYEGLASSES BLIND ANNOTATION CODEBOOK

Scope
- Judge only the displayed full decoded video frame.
- Do not identify the person, infer experimental role, or use any external source.
- Work independently. Do not discuss labels with the other annotator.

Required fields
1. face_eye_region_observable_yes_no: yes or no.
2. eyeglasses_label: present, absent, or U.
3. annotation_confidence_high_low: high or low.
4. reason_or_note: optional concise note; required when label is U.

Decision rules
- present: recognizable eyeglass/spectacle/sunglass frames or lenses are visibly worn on the face.
- absent: the eye region is sufficiently visible and no glasses are worn.
- U: the eye region is too small, blurred, occluded, distorted, outside frame, or artifactually ambiguous.
- If face_eye_region_observable_yes_no=no, eyeglasses_label must be U.
- If eyeglasses_label is present or absent, face_eye_region_observable_yes_no must be yes.
- Generated artifacts that only resemble a frame/lens but are not confidently wearable glasses are U, not present.

Important boundary
- These labels repair measurement coverage only. They do not replace or reclassify the frozen primary formal result.
"""
    (tmp / "eyeglasses_annotation_codebook_v1.txt").write_text(codebook, encoding="utf-8")
    readme = {
        "schema_version": 1,
        "packet_id": "formal_measurement_repair_eyeglasses_blind_annotation_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "annotation_items": 560,
        "annotators": 2,
        "independent": True,
        "full_frame_without_detector_crop": True,
        "private_mapping_location": str(OUT / "private_mapping_v1"),
        "private_mapping_must_not_be_given_to_annotators": True,
        "packet_randomizations": packet_hashes,
        "adjudication_policy": "all eyeglasses-label disagreements and all observability disagreements are adjudicated after independent annotation",
        "status": "READY_FOR_TWO_INDEPENDENT_BLIND_ANNOTATORS",
    }
    write_json(tmp / "eyeglasses_annotation_packet_manifest_v1.json", readme)
    public_files = []
    for p in sorted(x for x in tmp.rglob("*") if x.is_file() and private_dir not in x.parents):
        public_files.append({"relative_path": str(p.relative_to(tmp)), "bytes": p.stat().st_size, "sha256": sha256(p)})
    write_csv(tmp / "eyeglasses_annotation_public_artifact_hashes_v1.csv", ["relative_path", "bytes", "sha256"], public_files)
    private_hash = sha256(mapping_path)
    freeze = {
        "schema_version": 1,
        "freeze_id": "formal_measurement_repair_eyeglasses_annotation_packet_v1_freeze",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_freeze_sha256": sha256(REPAIR / "measurement_repair_protocol_freeze_v1.json"),
        "benchmark_freeze_sha256": sha256(BENCHMARK / "detector_benchmark_freeze_v1.json"),
        "benchmark_verification_sha256": sha256(VERIFY),
        "private_mapping_sha256": private_hash,
        "public_artifact_hashes_sha256": sha256(tmp / "eyeglasses_annotation_public_artifact_hashes_v1.csv"),
        "annotation_items": 560,
        "annotation_started": False,
        "private_mapping_access_required_for_annotation": False,
        "status": "READY_FOR_TWO_INDEPENDENT_BLIND_ANNOTATORS",
    }
    write_json(tmp / "eyeglasses_annotation_packet_freeze_v1.json", freeze)
    tmp.rename(OUT)
    print(json.dumps({"status": freeze["status"], "annotation_items": 560, "annotators": 2, "contact_sheet_pages_per_annotator": 28, "private_mapping_accessed_by_annotators": False}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except BuildError as exc:
        raise SystemExit(f"EYEGLASSES ANNOTATION BUILD FAILED: {exc}")
