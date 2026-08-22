#!/usr/bin/env python3
"""Independently recompute and verify the frozen detector benchmark summary."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPAIR = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/measurement_repair_v1")
BENCH = REPAIR / "detector_benchmark_v1"
OUT = REPAIR / "detector_benchmark_v1_independent_verification.json"


class VerificationError(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise VerificationError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def close(a, b, tolerance=5e-10):
    return abs(float(a) - float(b)) <= tolerance


def main():
    require(not OUT.exists(), "independent verification already exists")
    protocol = json.loads((REPAIR / "measurement_repair_protocol_v1.json").read_text(encoding="utf-8"))
    freeze = json.loads((BENCH / "detector_benchmark_freeze_v1.json").read_text(encoding="utf-8"))
    run_record = json.loads((BENCH / "detector_benchmark_run_record_v1.json").read_text(encoding="utf-8"))
    require(sha256(BENCH / "detector_item_results_v1.csv") == freeze["item_results_sha256"], "item results hash mismatch")
    require(sha256(BENCH / "detector_candidate_summary_v1.csv") == freeze["candidate_summary_sha256"], "summary hash mismatch")
    require(sha256(BENCH / "detector_benchmark_run_record_v1.json") == freeze["run_record_sha256"], "run record hash mismatch")
    require(sha256(BENCH / "detector_benchmark_artifact_hashes_v1.csv") == freeze["artifact_hashes_sha256"], "artifact inventory hash mismatch")
    for row in read_csv(BENCH / "detector_benchmark_artifact_hashes_v1.csv"):
        p = BENCH / row["relative_path"]
        require(p.is_file() and p.stat().st_size == int(row["bytes"]) and sha256(p) == row["sha256"], f"artifact mismatch: {p}")
    manifest = read_csv(REPAIR / "detector_evaluation_manifest_v1.csv")
    detail = read_csv(BENCH / "detector_item_results_v1.csv")
    summary = read_csv(BENCH / "detector_candidate_summary_v1.csv")
    item_ids = {r["evaluation_item_id"] for r in manifest}
    candidate_ids = [r["candidate_id"] for r in protocol["candidate_detectors"]]
    require(len(manifest) == 1160 and len(item_ids) == 1160, "manifest universe mismatch")
    require(len(candidate_ids) == 11 and len(set(candidate_ids)) == 11, "candidate universe mismatch")
    require(len(detail) == 12760, "detail count mismatch")
    keys = Counter((r["candidate_id"], r["evaluation_item_id"]) for r in detail)
    require(len(keys) == 12760 and set(keys.values()) == {1}, "candidate-item Cartesian product mismatch")
    require({k[0] for k in keys} == set(candidate_ids) and {k[1] for k in keys} == item_ids, "detail universe mismatch")
    require(len(summary) == 11 and {r["candidate_id"] for r in summary} == set(candidate_ids), "summary universe mismatch")
    manifest_by_id = {r["evaluation_item_id"]: r for r in manifest}
    grouped = defaultdict(list)
    for row in detail:
        require(row["detected"] in {"true", "false"} and row["plausible_bbox"] in {"true", "false"}, "invalid boolean")
        detected = row["detected"] == "true"
        if detected:
            require(int(row["detection_count"]) >= 1 and row["bbox_area_fraction"] != "", "detected row lacks box")
            area = float(row["bbox_area_fraction"])
            require(0 < area <= 1, "invalid bbox area")
            require((row["plausible_bbox"] == "true") == (0.01 <= area <= 0.9), "plausible bbox rule mismatch")
        else:
            require(int(row["detection_count"]) == 0 and row["bbox_area_fraction"] == "" and row["plausible_bbox"] == "false", "undetected row inconsistency")
        source = manifest_by_id[row["evaluation_item_id"]]
        require(row["source_kind"] == source["source_kind"] and row["human_observable_reference"] == source["human_observable_reference"], "manifest join mismatch")
        require(float(row["runtime_ms"]) >= 0, "negative runtime")
        grouped[row["candidate_id"]].append(row)
    summary_map = {r["candidate_id"]: r for r in summary}
    prelim_count = 0
    for candidate in protocol["candidate_detectors"]:
        rows = grouped[candidate["candidate_id"]]
        s = summary_map[candidate["candidate_id"]]
        subsets = {
            "reference": [r for r in rows if r["source_kind"] == "reference_image"],
            "facial": [r for r in rows if r["source_kind"] == "facial_hair_sample_frame" and r["human_observable_reference"] == "true"],
            "facial_u": [r for r in rows if r["source_kind"] == "facial_hair_sample_frame" and r["human_observable_reference"] == "false"],
            "eye": [r for r in rows if r["source_kind"] == "eyeglasses_sample_frame"],
        }
        detected = lambda subset: sum(r["detected"] == "true" for r in subset)
        require([len(subsets[x]) for x in ("reference", "facial", "facial_u", "eye")] == [40, 371, 189, 560], "fixed denominator mismatch")
        selected = [r for r in rows if r["detected"] == "true"]
        ref_recall = detected(subsets["reference"]) / 40
        facial_recall = detected(subsets["facial"]) / 371
        plausible = sum(r["plausible_bbox"] == "true" for r in selected) / len(selected) if selected else 0.0
        require(int(s["total_detected"]) == detected(rows), "total detected mismatch")
        require(int(s["reference_detected"]) == detected(subsets["reference"]) and close(s["reference_recall"], ref_recall), "reference summary mismatch")
        require(int(s["facial_hair_human_observable_detected"]) == detected(subsets["facial"]) and close(s["facial_hair_human_observable_recall"], facial_recall), "facial observable summary mismatch")
        require(int(s["facial_hair_U_detected"]) == detected(subsets["facial_u"]), "facial U summary mismatch")
        require(int(s["eyeglasses_fixed_frames_detected"]) == detected(subsets["eye"]), "eye frame summary mismatch")
        require(close(s["plausible_bbox_fraction_among_detected"], plausible), "bbox summary mismatch")
        gate = protocol["preliminary_detector_eligibility"]
        eligible = ref_recall >= gate["reference_image_detection_recall_minimum"] and facial_recall >= gate["human_observable_facial_hair_frame_recall_minimum"] and plausible >= gate["plausible_bbox_fraction_minimum"]
        require((s["preliminary_eligible"] == "true") == eligible, "eligibility mismatch")
        prelim_count += eligible
    require(run_record["final_detector_selected"] is False and freeze["final_detector_selected"] is False, "detector selected before eye labels")
    result = {
        "schema_version": 1,
        "verification_id": "formal_measurement_repair_detector_benchmark_v1_independent_verification",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark_freeze_sha256": sha256(BENCH / "detector_benchmark_freeze_v1.json"),
        "protocol_freeze_sha256": sha256(REPAIR / "measurement_repair_protocol_freeze_v1.json"),
        "evaluation_items_verified": 1160,
        "candidate_detectors_verified": 11,
        "candidate_item_rows_verified": 12760,
        "fixed_denominators_verified": {"reference_images": 40, "facial_hair_human_observable": 371, "facial_hair_U": 189, "eyeglasses_fixed_frames_unlabeled": 560},
        "preliminary_eligible_candidate_count": prelim_count,
        "final_detector_selected": False,
        "attribute_effect_direction_used": False,
        "status": "PASS_INDEPENDENT_DETECTOR_BENCHMARK_VERIFICATION",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "items": 1160, "candidates": 11, "rows": 12760, "final_detector_selected": False}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except VerificationError as exc:
        raise SystemExit(f"INDEPENDENT BENCHMARK VERIFICATION FAILED: {exc}")
