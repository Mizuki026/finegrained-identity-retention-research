#!/usr/bin/env python3
"""Independent structural verifier for formal attribute evaluation v1.

The verifier performs no model inference and no condition-level scientific
analysis. It checks the frozen task universe, row-level arithmetic, blinded
annotation material, and the output checksum inventory, then writes one new
verification JSON outside the frozen run directory.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime")
MASTER_FREEZE = ROOT / "experiment_freeze_v1/pre_generation_master_freeze_v1.json"
MANIFEST = ROOT / "experiment_freeze_v1/generation_manifest_v1.csv"
EXPECTED_MASTER_SHA256 = (
    "149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8"
)
EXPECTED_EVALUATOR_COMMIT = "89e30cd5d16dd9ffb0d37438144661206e7218f4"
FACIAL_INDICES = {0, 8, 16, 24, 32, 40, 48}


class VerifyError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerifyError(message)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def close(left: float, right: float, tolerance: float = 2e-7) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=tolerance)


def recompute_eye_summary(rows: list[dict], task: dict) -> dict[str, float | int | str]:
    valid = [row for row in rows if row["measurement_status"] == "VALID_OBSERVABLE"]
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
    return {
        "valid": len(valid),
        "unobservable": sum(row["measurement_status"] == "UNOBSERVABLE" for row in rows),
        "failures": sum(row["measurement_status"] == "PIPELINE_FAILURE" for row in rows),
        "mean_probability": statistics.mean(probabilities) if probabilities else math.nan,
        "median_probability": statistics.median(probabilities) if probabilities else math.nan,
        "mean_margin": statistics.mean(margins) if margins else math.nan,
        "match_fraction": sum(matches) / len(matches) if matches else math.nan,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--verification-path", type=Path, required=True)
    args = parser.parse_args()
    run = args.run_dir
    if args.verification_path.exists():
        fail(f"refusing to overwrite verification: {args.verification_path}")
    if sha256_path(MASTER_FREEZE) != EXPECTED_MASTER_SHA256:
        fail("pre-generation master-freeze SHA256 mismatch")
    required = {
        "eyeglasses_frame_measurements_v1.csv",
        "eyeglasses_video_summary_v1.csv",
        "identity_frame_diagnostics_v1.csv",
        "identity_video_summary_v1.csv",
        "formal_attribute_evaluation_v1.log",
        "formal_attribute_execution_audit_v1.json",
        "machine_measurement_freeze_v1.json",
        "output_hashes_v1.csv",
        "facial_hair_blinded_crops_v1",
        "facial_hair_annotation_materials_v1",
        "private_mapping_v1",
    }
    if not run.is_dir() or {path.name for path in run.iterdir()} != required:
        fail("formal evaluation output file set mismatch")
    manifest = read_csv(MANIFEST)
    if len(manifest) != 160:
        fail("manifest task universe mismatch")
    tasks = {row["task_id"]: row for row in manifest}
    if len(tasks) != 160:
        fail("duplicate manifest task IDs")
    eye_tasks = {key: row for key, row in tasks.items() if row["attribute"] == "eyeglasses"}
    facial_tasks = {key: row for key, row in tasks.items() if row["attribute"] == "facial_hair"}
    if len(eye_tasks) != 80 or len(facial_tasks) != 80:
        fail("attribute task split mismatch")

    eye_frames = read_csv(run / "eyeglasses_frame_measurements_v1.csv")
    eye_summaries = read_csv(run / "eyeglasses_video_summary_v1.csv")
    identity_frames = read_csv(run / "identity_frame_diagnostics_v1.csv")
    identity_summaries = read_csv(run / "identity_video_summary_v1.csv")
    if (len(eye_frames), len(eye_summaries), len(identity_frames), len(identity_summaries)) != (3920, 80, 7840, 160):
        fail("machine measurement row-count mismatch")

    eye_by_task = defaultdict(list)
    for row in eye_frames:
        eye_by_task[row["task_id"]].append(row)
        if row["task_id"] not in eye_tasks:
            fail(f"unknown eyeglasses task: {row['task_id']}")
        if row["measurement_status"] == "VALID_OBSERVABLE":
            p_present = float(row["p_present"])
            p_absent = float(row["p_absent"])
            margin = float(row["margin_present_minus_absent"])
            if not close(p_present + p_absent, 1.0, 3e-7):
                fail(f"CLIP probability sum mismatch: {row['task_id']} frame {row['frame_index']}")
            if not close(p_present - p_absent, margin, 3e-7):
                fail(f"CLIP margin mismatch: {row['task_id']} frame {row['frame_index']}")
            predicted = "present" if margin > 0 else ("absent" if margin < 0 else "")
            if row["predicted_state"] != predicted:
                fail("eyeglasses decision-rule mismatch")
            expected_match = str(predicted == eye_tasks[row["task_id"]]["expected_state"]).lower()
            if row["expected_state_match"] != expected_match:
                fail("eyeglasses expected-state match mismatch")
    if set(eye_by_task) != set(eye_tasks):
        fail("eyeglasses task set mismatch")
    eye_summary_by_task = {row["task_id"]: row for row in eye_summaries}
    if len(eye_summary_by_task) != 80 or set(eye_summary_by_task) != set(eye_tasks):
        fail("eyeglasses summary task set mismatch")
    for task_id, rows in eye_by_task.items():
        rows.sort(key=lambda row: int(row["frame_index"]))
        if [int(row["frame_index"]) for row in rows] != list(range(49)):
            fail(f"eyeglasses frame universe mismatch: {task_id}")
        expected = recompute_eye_summary(rows, eye_tasks[task_id])
        observed = eye_summary_by_task[task_id]
        if int(observed["valid_frames"]) != expected["valid"]:
            fail(f"eyeglasses valid-frame aggregate mismatch: {task_id}")
        if int(observed["unobservable_frames"]) != expected["unobservable"]:
            fail(f"eyeglasses unobservable aggregate mismatch: {task_id}")
        if int(observed["pipeline_failure_frames"]) != expected["failures"]:
            fail(f"eyeglasses failure aggregate mismatch: {task_id}")
        pairs = (
            ("mean_expected_state_probability", "mean_probability"),
            ("median_expected_state_probability", "median_probability"),
            ("mean_signed_expected_state_margin", "mean_margin"),
            ("expected_state_match_fraction", "match_fraction"),
        )
        for observed_key, expected_key in pairs:
            if observed[observed_key] and not close(float(observed[observed_key]), float(expected[expected_key])):
                fail(f"eyeglasses summary arithmetic mismatch: {task_id} {observed_key}")

    identity_by_task = defaultdict(list)
    for row in identity_frames:
        identity_by_task[row["task_id"]].append(row)
        if row["task_id"] not in tasks:
            fail(f"unknown identity task: {row['task_id']}")
        if row["cosine_similarity"]:
            value = float(row["cosine_similarity"])
            if not -1.000001 <= value <= 1.000001:
                fail("identity cosine outside mathematical range")
            if row["diagnostic_status"] != "VALID_OBSERVABLE":
                fail("identity cosine present on non-valid row")
    if set(identity_by_task) != set(tasks):
        fail("identity task set mismatch")
    identity_summary_by_task = {row["task_id"]: row for row in identity_summaries}
    if len(identity_summary_by_task) != 160 or set(identity_summary_by_task) != set(tasks):
        fail("identity summary task set mismatch")
    for task_id, rows in identity_by_task.items():
        rows.sort(key=lambda row: int(row["frame_index"]))
        if [int(row["frame_index"]) for row in rows] != list(range(49)):
            fail(f"identity frame universe mismatch: {task_id}")
        values = [float(row["cosine_similarity"]) for row in rows if row["cosine_similarity"]]
        observed = identity_summary_by_task[task_id]
        if int(observed["valid_frames"]) != len(values):
            fail(f"identity valid-frame aggregate mismatch: {task_id}")
        if values:
            checks = (
                ("mean_cosine_similarity", statistics.mean(values)),
                ("median_cosine_similarity", statistics.median(values)),
                ("minimum_cosine_similarity", min(values)),
                ("maximum_cosine_similarity", max(values)),
            )
            for key, value in checks:
                if not close(float(observed[key]), value):
                    fail(f"identity summary arithmetic mismatch: {task_id} {key}")

    private = read_csv(run / "private_mapping_v1/facial_hair_private_mapping_v1.csv")
    if len(private) != 560 or len({row["annotation_item_id"] for row in private}) != 560:
        fail("facial-hair private mapping universe mismatch")
    for row in private:
        if row["task_id"] not in facial_tasks or int(row["frame_index"]) not in FACIAL_INDICES:
            fail("facial-hair private mapping task/frame mismatch")
        crop = run / "facial_hair_blinded_crops_v1" / row["crop_filename"]
        if not crop.is_file() or crop.stat().st_size <= 0:
            fail(f"missing annotation crop: {crop}")
    expected_items = {row["annotation_item_id"] for row in private}
    observed_crop_names = {path.stem for path in (run / "facial_hair_blinded_crops_v1").glob("*.jpg")}
    if observed_crop_names != expected_items:
        fail("blinded crop item set mismatch")
    orders = {}
    for annotator in ("A", "B"):
        directory = run / "facial_hair_annotation_materials_v1" / f"annotator_{annotator}"
        template = read_csv(directory / f"facial_hair_annotator_{annotator}_v1.csv")
        if len(template) != 560 or {row["annotation_item_id"] for row in template} != expected_items:
            fail(f"annotator {annotator} template item set mismatch")
        if any(row["annotator_id"] != annotator or row["ordinal_label"] or row["reason_or_note"] for row in template):
            fail(f"annotator {annotator} template is not blank and correctly identified")
        if sorted(int(row["random_order"]) for row in template) != list(range(1, 561)):
            fail(f"annotator {annotator} random-order permutation mismatch")
        pages = sorted((directory / "contact_sheets").glob("*.png"))
        if len(pages) != 8 or any(path.stat().st_size <= 0 for path in pages):
            fail(f"annotator {annotator} contact-sheet page set mismatch")
        orders[annotator] = [row["annotation_item_id"] for row in template]
    if orders["A"] == orders["B"]:
        fail("annotator randomization orders unexpectedly identical")

    hashes = read_csv(run / "output_hashes_v1.csv")
    if len({row["relative_path"] for row in hashes}) != len(hashes):
        fail("duplicate output hash inventory paths")
    for row in hashes:
        path = run / row["relative_path"]
        if not path.is_file() or path.stat().st_size != int(row["bytes"]):
            fail(f"hash inventory target missing or size mismatch: {path}")
        if sha256_path(path) != row["sha256"]:
            fail(f"hash inventory SHA256 mismatch: {path}")
    audit = json.loads((run / "formal_attribute_execution_audit_v1.json").read_text(encoding="utf-8"))
    freeze = json.loads((run / "machine_measurement_freeze_v1.json").read_text(encoding="utf-8"))
    if audit.get("status") != "MACHINE_MEASUREMENT_COMPLETE_MANUAL_ANNOTATION_PENDING":
        fail("machine execution audit status mismatch")
    if freeze.get("status") != "FROZEN_MACHINE_MEASUREMENT_MANUAL_ANNOTATION_PENDING":
        fail("machine measurement freeze status mismatch")
    if audit.get("master_freeze_sha256") != EXPECTED_MASTER_SHA256:
        fail("machine execution master-freeze mismatch")
    if audit.get("code_commit") != EXPECTED_EVALUATOR_COMMIT:
        fail("machine evaluator code-commit mismatch")

    report = {
        "schema_version": 1,
        "verification_id": "formal_attribute_evaluation_independent_verification_v1",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run), "master_freeze_sha256": EXPECTED_MASTER_SHA256,
        "machine_evaluator_code_commit": EXPECTED_EVALUATOR_COMMIT,
        "verification_script_sha256": sha256_path(Path(__file__).resolve()),
        "row_counts": {
            "eyeglasses_frames": len(eye_frames), "eyeglasses_videos": len(eye_summaries),
            "identity_frames": len(identity_frames), "identity_videos": len(identity_summaries),
            "facial_hair_annotation_items": len(private),
        },
        "annotator_orders_distinct": True, "all_listed_hashes_verified": True,
        "all_summary_arithmetic_recomputed": True,
        "models_loaded": False, "video_pixels_read": False, "network_used": False,
        "private_mapping_accessed_by_verifier": True,
        "condition_level_scientific_analysis_performed": False,
        "status": "PASS_INDEPENDENT_MACHINE_MEASUREMENT_AND_BLINDING_VERIFICATION",
    }
    args.verification_path.parent.mkdir(parents=True, exist_ok=True)
    with args.verification_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    print(json.dumps({
        "status": report["status"], "verification": str(args.verification_path),
        "scientific_outcomes_printed": False,
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except VerifyError as exc:
        raise SystemExit(f"FORMAL EVALUATION VERIFICATION FAILED: {exc}")
