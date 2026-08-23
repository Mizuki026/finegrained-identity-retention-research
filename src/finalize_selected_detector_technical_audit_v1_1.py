#!/usr/bin/env python3
"""Freeze the completed full technical audit for the selected detector."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/measurement_repair_v1")
SELECTED = BASE / "selected_detector_v1_1"
BENCH = BASE / "detector_benchmark_v1"
CONSENSUS = BASE / "eyeglasses_consensus_v1_1"
MAPPING = BASE / "eyeglasses_blind_annotation_v1/private_mapping_v1/eyeglasses_private_mapping_v1.csv"
OUT = BASE / "selected_detector_technical_audit_final_v1_1"
REPO = Path("/root/autodl-tmp/finegrained/research_pipeline")
EXPECTED_SELECTED_FREEZE_SHA256 = "82a3ff9361f49a15382fc8e68da2e092797ce1b71d348b45f1f7d445f9bef84a"
EXPECTED_SUBMISSION_SHA256 = "8e2a533f0f651fd91c4d8f8b28e97187ed6ad221ac80a967bdf2a4b567fc348b"
FIELDS = [
    "annotation_item_id", "selected_detector", "detected", "bbox_x1", "bbox_y1",
    "bbox_x2", "bbox_y2", "bbox_area_fraction", "correct_face_bbox_yes_no",
    "expanded_crop_contains_face_and_eye_region_yes_no", "technical_status_pass_fail",
    "review_note",
]
PROTECTED = FIELDS[:8]


class AuditError(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise AuditError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def write_csv(path: Path, fields, rows):
    with path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def reconstruct_expected(selected_id: str):
    _, consensus = read_csv(CONSENSUS / "eyeglasses_final_consensus_v1_1.csv")
    _, mapping_rows = read_csv(MAPPING)
    _, details = read_csv(BENCH / "detector_item_results_v1.csv")
    mapping = {r["annotation_item_id"]: r for r in mapping_rows}
    detected = {
        r["evaluation_item_id"]: r
        for r in details
        if r["candidate_id"] == selected_id and r["source_kind"] == "eyeglasses_sample_frame"
    }
    require(len(consensus) == len(mapping) == len(detected) == 560, "reconstruction universe mismatch")
    expected = []
    for row in sorted(consensus, key=lambda x: x["annotation_item_id"]):
        item = row["annotation_item_id"]
        source = detected[mapping[item]["evaluation_item_id"]]
        expected.append({
            "annotation_item_id": item,
            "selected_detector": selected_id,
            "detected": source["detected"],
            "bbox_x1": source["bbox_x1"],
            "bbox_y1": source["bbox_y1"],
            "bbox_x2": source["bbox_x2"],
            "bbox_y2": source["bbox_y2"],
            "bbox_area_fraction": source["bbox_area_fraction"],
            "correct_face_bbox_yes_no": "",
            "expanded_crop_contains_face_and_eye_region_yes_no": "",
            "technical_status_pass_fail": "",
            "review_note": "",
        })
    return expected


def main():
    require(not OUT.exists() and not OUT.with_name(OUT.name + ".inprogress").exists(), "output exists")
    selected_freeze_path = SELECTED / "selected_detector_freeze_v1_1.json"
    submission = SELECTED / "selected_detector_technical_audit_template_v1_1.csv"
    require(sha256(selected_freeze_path) == EXPECTED_SELECTED_FREEZE_SHA256, "selected-detector freeze mismatch")
    require(sha256(submission) == EXPECTED_SUBMISSION_SHA256, "technical-audit submission mismatch")
    require(subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain"], text=True) == "", "dirty repo")
    committed = REPO / "src/finalize_selected_detector_technical_audit_v1_1.py"
    require(committed.is_file() and sha256(committed) == sha256(Path(__file__)), "script is not committed copy")
    commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    selected_freeze = json.loads(selected_freeze_path.read_text(encoding="utf-8"))
    selected_id = selected_freeze["selected_candidate_id"]
    expected = reconstruct_expected(selected_id)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, extrasaction="raise")
    writer.writeheader(); writer.writerows(expected)
    require(hashlib.sha256(buffer.getvalue().encode()).hexdigest() == selected_freeze["technical_audit_template_sha256"], "cannot reconstruct frozen template")
    fields, submitted = read_csv(submission)
    require(fields == FIELDS and len(submitted) == 560, "submission shape mismatch")
    require(len({r["annotation_item_id"] for r in submitted}) == 560, "duplicate anonymous ID")
    expected_map = {r["annotation_item_id"]: r for r in expected}
    failures = []
    for row in submitted:
        item = row["annotation_item_id"]
        require(item in expected_map, f"unknown anonymous ID: {item}")
        require(all(row[k] == expected_map[item][k] for k in PROTECTED), f"protected field changed: {item}")
        bbox = row["correct_face_bbox_yes_no"].strip()
        crop = row["expanded_crop_contains_face_and_eye_region_yes_no"].strip()
        status = row["technical_status_pass_fail"].strip()
        note = row["review_note"].strip()
        require(bbox in {"yes", "no"} and crop in {"yes", "no"}, f"invalid judgment: {item}")
        expected_status = "pass" if row["detected"] == "true" and bbox == "yes" and crop == "yes" else "fail"
        require(status == expected_status, f"status logic mismatch: {item}")
        require(status != "fail" or note, f"failure without note: {item}")
        if status == "fail":
            failures.append({"annotation_item_id": item, "correct_face_bbox_yes_no": bbox, "expanded_crop_contains_face_and_eye_region_yes_no": crop, "review_note": note})
    tmp = OUT.with_name(OUT.name + ".inprogress")
    tmp.mkdir(parents=True)
    shutil.copyfile(submission, tmp / "selected_detector_technical_audit_submitted_v1_1.csv")
    write_csv(tmp / "selected_detector_technical_audit_final_v1_1.csv", FIELDS, submitted)
    audit = {
        "schema_version": 1,
        "audit_id": "formal_measurement_repair_selected_detector_technical_audit_v1_1",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_candidate_id": selected_id,
        "items": 560,
        "pass_items": 553,
        "fail_items": 7,
        "pass_fraction": 553 / 560,
        "failure_records": failures,
        "detector_substitution_performed": False,
        "selective_frame_exclusion_performed": False,
        "imputation_performed": False,
        "downstream_policy": "retain all 560 ledger rows; technical failures remain explicit invalid measurements without imputation",
        "status": "FROZEN_TECHNICAL_AUDIT_WITH_7_FAILURES_NO_SUBSTITUTION_NO_EXCLUSION",
    }
    require(Counter(r["technical_status_pass_fail"] for r in submitted) == {"pass": 553, "fail": 7}, "unexpected final counts")
    write_json(tmp / "selected_detector_technical_audit_record_v1_1.json", audit)
    freeze = {
        "schema_version": 1,
        "freeze_id": "formal_measurement_repair_selected_detector_technical_audit_v1_1_freeze",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_commit": commit,
        "script_sha256": sha256(Path(__file__)),
        "selected_detector_freeze_sha256": sha256(selected_freeze_path),
        "submitted_sha256": sha256(tmp / "selected_detector_technical_audit_submitted_v1_1.csv"),
        "final_audit_sha256": sha256(tmp / "selected_detector_technical_audit_final_v1_1.csv"),
        "audit_record_sha256": sha256(tmp / "selected_detector_technical_audit_record_v1_1.json"),
        "status": audit["status"],
    }
    write_json(tmp / "selected_detector_technical_audit_freeze_v1_1.json", freeze)
    tmp.rename(OUT)
    print(json.dumps({"status": freeze["status"], "items": 560, "pass": 553, "fail": 7}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except AuditError as exc:
        raise SystemExit(f"TECHNICAL AUDIT FINALIZATION FAILED: {exc}")
