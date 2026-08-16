#!/usr/bin/env python3
"""Finalize Pilot v3 machine observations with frozen blinded consensus labels."""
import argparse
import csv
import hashlib
import json
import statistics
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/root/autodl-tmp/finegrained")
REPO = ROOT / "research_pipeline"
RUN = ROOT / "pilot_v3_runtime/attribute_evaluation_v3/run_002"
FREEZE = ROOT / "pilot_v3_runtime/experiment_freeze_v1"
FRAME_INPUT = RUN / "attribute_frame_inventory_v3.csv"
SUMMARY_INPUT = RUN / "attribute_video_summary_v3.csv"
MANIFEST = FREEZE / "evaluation_manifest_v3.csv"
UNBLINDED = RUN / "facial_hair_unblinding_v3_1/facial_hair_annotation_unblinded_v3_1.csv"
UNBLIND_VERIFY = RUN / "facial_hair_unblinding_v3_1/facial_hair_unblinding_independent_verification_v3_1.json"
PLAN_DIR = RUN / "facial_hair_aggregation_plan_v3_1"
PLAN = PLAN_DIR / "facial_hair_descriptive_aggregation_plan_v3_1.json"
PLAN_FREEZE = PLAN_DIR / "facial_hair_aggregation_plan_freeze_v3_1.json"

FACIAL_COLUMNS = [
    "schema_version", "run_id", "annotation_item_id", "sample_id",
    "frame_index", "timestamp_seconds", "expected_label",
    "ordinal_label", "binary_label", "expected_label_match",
    "attribute_frame_status", "primary_reason_code", "consensus_source",
    "record_status",
]
FACIAL_SUMMARY_COLUMNS = [
    "schema_version", "run_id", "sample_id", "expected_label",
    "planned_frames", "count_label_0", "count_label_1", "count_label_2",
    "count_label_U", "valid_ordinal_frames", "valid_ordinal_fraction",
    "binary_eligible_frames", "binary_match_frames",
    "binary_expected_match_fraction", "ordinal_mean_over_observable",
    "ordinal_median_over_observable", "adjacent_binary_valid_pair_count",
    "adjacent_binary_flip_count", "adjacent_binary_flip_rate",
    "low_coverage_flag", "raw_ordinal_sequence", "summary_status",
]


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, columns, rows):
    with open(path, "x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    with open(path, "x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def git_commit():
    return subprocess.check_output(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True
    ).strip()


def preflight(output_dir, require_output=False):
    required = [
        FRAME_INPUT, SUMMARY_INPUT, MANIFEST, UNBLINDED, UNBLIND_VERIFY,
        PLAN, PLAN_FREEZE,
    ]
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"missing input: {path}")
    if require_output and not output_dir.is_dir():
        raise RuntimeError(f"finalized output missing: {output_dir}")
    if not require_output and output_dir.exists():
        raise RuntimeError(f"refusing to overwrite output: {output_dir}")
    plan = json.load(open(PLAN, encoding="utf-8"))
    freeze = json.load(open(PLAN_FREEZE, encoding="utf-8"))
    verify = json.load(open(UNBLIND_VERIFY, encoding="utf-8"))
    if freeze["status"] != "FROZEN" or freeze["plan_json_sha256"] != sha(PLAN):
        raise RuntimeError("aggregation plan freeze mismatch")
    if plan["status"] != "FROZEN_READY_FOR_EXECUTION":
        raise RuntimeError("aggregation plan is not executable")
    if not plan["frozen_before_condition_summary_inspection"]:
        raise RuntimeError("aggregation plan was not prospectively frozen")
    if verify["status"] != "PASS_INDEPENDENT_UNBLINDING_VERIFICATION_NO_CONDITION_ANALYSIS":
        raise RuntimeError("unblinding verification did not pass")


def facial_video_summary(sample_id, expected, rows, run_id):
    rows = sorted(rows, key=lambda row: int(row["frame_index"]))
    if len(rows) != 49 or [int(row["frame_index"]) for row in rows] != list(range(49)):
        raise RuntimeError(f"facial-hair frame universe mismatch: {sample_id}")
    labels = [row["facial_hair_ordinal_label"] for row in rows]
    counts = Counter(labels)
    if set(counts) - {"0", "1", "2", "U"}:
        raise RuntimeError(f"unexpected ordinal label: {sample_id}")
    valid = [int(label) for label in labels if label in {"0", "1", "2"}]
    binary = [label if label in {"0", "2"} else None for label in labels]
    eligible = sum(label is not None for label in binary)
    matches = sum(label == expected for label in binary if label is not None)
    pairs = flips = 0
    for left, right in zip(binary, binary[1:]):
        if left is not None and right is not None:
            pairs += 1
            flips += int(left != right)
    valid_fraction = len(valid) / 49
    return {
        "schema_version": "3.1", "run_id": run_id, "sample_id": sample_id,
        "expected_label": expected, "planned_frames": "49",
        "count_label_0": str(counts["0"]), "count_label_1": str(counts["1"]),
        "count_label_2": str(counts["2"]), "count_label_U": str(counts["U"]),
        "valid_ordinal_frames": str(len(valid)),
        "valid_ordinal_fraction": f"{valid_fraction:.6f}",
        "binary_eligible_frames": str(eligible), "binary_match_frames": str(matches),
        "binary_expected_match_fraction": f"{matches / eligible:.6f}" if eligible else "",
        "ordinal_mean_over_observable": f"{statistics.mean(valid):.6f}" if valid else "",
        "ordinal_median_over_observable": f"{statistics.median(valid):.6f}" if valid else "",
        "adjacent_binary_valid_pair_count": str(pairs),
        "adjacent_binary_flip_count": str(flips),
        "adjacent_binary_flip_rate": f"{flips / pairs:.6f}" if pairs else "",
        "low_coverage_flag": str(valid_fraction < 0.5).lower(),
        "raw_ordinal_sequence": "|".join(labels), "summary_status": "COMPLETE",
    }


def unified_facial_summary(detail, source_columns):
    row = {column: "" for column in source_columns}
    row.update({
        "schema_version": "1", "run_id": detail["run_id"],
        "sample_id": detail["sample_id"], "attribute": "facial_hair",
        "expected_label": detail["expected_label"], "total_frames": "49",
        "valid_observable_frames": detail["valid_ordinal_frames"],
        "unobservable_frames": detail["count_label_U"],
        "pipeline_failure_frames": "0",
        "valid_frame_fraction": detail["valid_ordinal_fraction"],
        "unobservable_fraction": f"{int(detail['count_label_U']) / 49:.6f}",
        "pipeline_failure_fraction": "0.000000",
        "low_coverage_flag": detail["low_coverage_flag"],
        "metric_mean": detail["ordinal_mean_over_observable"],
        "metric_median": detail["ordinal_median_over_observable"],
        "expected_label_match_fraction": detail["binary_expected_match_fraction"],
        "adjacent_valid_pair_count": detail["adjacent_binary_valid_pair_count"],
        "adjacent_flip_count": detail["adjacent_binary_flip_count"],
        "adjacent_flip_rate": detail["adjacent_binary_flip_rate"],
        "summary_status": "COMPLETE",
    })
    valid = []
    for label, count_key in ((0, "count_label_0"), (1, "count_label_1"), (2, "count_label_2")):
        valid.extend([label] * int(detail[count_key]))
    row["metric_sd"] = f"{statistics.stdev(valid):.6f}" if len(valid) > 1 else ""
    return row


def build_outputs():
    frames = read_csv(FRAME_INPUT)
    machine_summaries = read_csv(SUMMARY_INPUT)
    manifest = read_csv(MANIFEST)
    unblinded = read_csv(UNBLINDED)
    if len(frames) != 588 or len(machine_summaries) != 12 or len(manifest) != 12:
        raise RuntimeError("input universe mismatch")
    if len(unblinded) != 196:
        raise RuntimeError("unblinded row count mismatch")
    manifest_by_sample = {row["sample_id"]: row for row in manifest}
    label_by_item = {row["annotation_item_id"]: row for row in unblinded}
    if len(label_by_item) != 196:
        raise RuntimeError("duplicate unblinded annotation item")
    final_frames = []
    facial_ledger = []
    used = set()
    for source in frames:
        row = dict(source)
        if row["attribute"] == "facial_hair":
            item = row["annotation_item_id"]
            if item not in label_by_item:
                raise RuntimeError(f"unmapped facial-hair item: {item}")
            label = label_by_item[item]["consensus_ordinal_label"]
            expected = manifest_by_sample[row["sample_id"]]["label"]
            if label not in {"0", "1", "2", "U"}:
                raise RuntimeError(f"invalid frozen label: {label}")
            row["facial_hair_ordinal_label"] = label
            row["facial_hair_binary_label"] = label if label in {"0", "2"} else ""
            row["facial_hair_expected_label_match"] = (
                str(label == expected) if label in {"0", "2"} else ""
            )
            row["record_status"] = "FINALIZED_CONSENSUS"
            if label == "U":
                row["attribute_frame_status"] = "UNOBSERVABLE"
                row["primary_reason_code"] = "MANUAL_UNOBSERVABLE"
                row["secondary_reason_codes"] = ""
            else:
                row["attribute_frame_status"] = "VALID_OBSERVABLE"
                row["primary_reason_code"] = ""
                row["secondary_reason_codes"] = ""
            row["observability_evidence"] = "two_frozen_submissions_exact_agreement"
            used.add(item)
            facial_ledger.append({
                "schema_version": "3.1", "run_id": row["run_id"],
                "annotation_item_id": item, "sample_id": row["sample_id"],
                "frame_index": row["frame_index"],
                "timestamp_seconds": row["timestamp_seconds"],
                "expected_label": expected, "ordinal_label": label,
                "binary_label": row["facial_hair_binary_label"],
                "expected_label_match": row["facial_hair_expected_label_match"],
                "attribute_frame_status": row["attribute_frame_status"],
                "primary_reason_code": row["primary_reason_code"],
                "consensus_source": label_by_item[item]["consensus_source"],
                "record_status": "MAPPED_AND_FINALIZED",
            })
        final_frames.append(row)
    if used != set(label_by_item):
        raise RuntimeError("unblinded labels do not close over frame inventory")
    run_id = final_frames[0]["run_id"]
    facial_details = []
    for sample in manifest:
        if sample["attribute"] != "facial_hair":
            continue
        subset = [row for row in final_frames if row["sample_id"] == sample["sample_id"]]
        facial_details.append(facial_video_summary(sample["sample_id"], sample["label"], subset, run_id))
    if len(facial_details) != 4:
        raise RuntimeError("expected four facial-hair summaries")
    original_by_sample = {row["sample_id"]: row for row in machine_summaries}
    detail_by_sample = {row["sample_id"]: row for row in facial_details}
    summary_columns = list(machine_summaries[0])
    unified = []
    for sample in manifest:
        sid = sample["sample_id"]
        unified.append(
            unified_facial_summary(detail_by_sample[sid], summary_columns)
            if sid in detail_by_sample else original_by_sample[sid]
        )
    return list(frames[0]), summary_columns, final_frames, facial_ledger, facial_details, unified


def execute(output_dir):
    frame_columns, summary_columns, frames, ledger, details, unified = build_outputs()
    output_dir.mkdir(parents=True)
    write_csv(output_dir / "attribute_frame_inventory_final_v3_1.csv", frame_columns, frames)
    write_csv(output_dir / "attribute_video_summary_final_v3_1.csv", summary_columns, unified)
    write_csv(output_dir / "facial_hair_finalized_frame_ledger_v3_1.csv", FACIAL_COLUMNS, ledger)
    write_csv(output_dir / "facial_hair_video_summary_v3_1.csv", FACIAL_SUMMARY_COLUMNS, details)
    with open(output_dir / "README.md", "x", encoding="utf-8") as handle:
        handle.write(
            "# Pilot v3 finalized attribute evaluation v3.1\n\n"
            "Exploratory video-level descriptive outputs under the frozen protocol. "
            "Frames are correlated and are not independent samples. No causal or "
            "general model claim is supported.\n"
        )
    audit = {
        "schema_version": 3, "run_id": "pilot_v3_attribute_evaluation_final_v3_1",
        "completed_at_utc": now(), "script_sha256": sha(Path(__file__)),
        "code_commit": git_commit(),
        "inputs": {
            "machine_frames": sha(FRAME_INPUT), "machine_summary": sha(SUMMARY_INPUT),
            "manifest": sha(MANIFEST), "unblinded_consensus": sha(UNBLINDED),
            "unblinding_verification": sha(UNBLIND_VERIFY), "aggregation_plan": sha(PLAN),
            "aggregation_plan_freeze": sha(PLAN_FREEZE),
        },
        "row_counts": {
            "final_frame_inventory": len(frames), "unified_video_summary": len(unified),
            "facial_hair_frame_ledger": len(ledger), "facial_hair_video_summary": len(details),
        },
        "frame_status_counts": dict(Counter(row["attribute_frame_status"] for row in frames)),
        "pipeline_failure_frames": sum(row["attribute_frame_status"] == "PIPELINE_FAILURE" for row in frames),
        "selective_rerun_performed": False, "imputation_performed": False,
        "condition_level_inferential_analysis_performed": False,
        "status": "FINALIZATION_EXECUTION_PASS_PENDING_INDEPENDENT_VERIFICATION",
    }
    write_json(output_dir / "finalization_execution_audit_v3_1.json", audit)
    hash_rows = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file():
            hash_rows.append({"file": path.name, "sha256": sha(path), "bytes": path.stat().st_size})
    write_csv(output_dir / "finalization_output_hashes_v3_1.csv", ["file", "sha256", "bytes"], hash_rows)
    freeze = {
        "schema_version": 3, "freeze_id": "pilot_v3_finalized_attribute_outputs_v3_1",
        "frozen_at_utc": now(), "output_hash_inventory_sha256": sha(output_dir / "finalization_output_hashes_v3_1.csv"),
        "frame_rows": len(frames), "video_rows": len(unified),
        "facial_hair_frame_rows": len(ledger), "facial_hair_video_rows": len(details),
        "status": "FROZEN_PENDING_INDEPENDENT_VERIFICATION",
    }
    write_json(output_dir / "finalization_freeze_v3_1.json", freeze)


def verify(output_dir, verification_path):
    frame_columns, summary_columns, frames, ledger, details, unified = build_outputs()
    expected = {
        "attribute_frame_inventory_final_v3_1.csv": (frame_columns, frames),
        "attribute_video_summary_final_v3_1.csv": (summary_columns, unified),
        "facial_hair_finalized_frame_ledger_v3_1.csv": (FACIAL_COLUMNS, ledger),
        "facial_hair_video_summary_v3_1.csv": (FACIAL_SUMMARY_COLUMNS, details),
    }
    for name, (_, rows) in expected.items():
        if read_csv(output_dir / name) != rows:
            raise RuntimeError(f"independent recomputation mismatch: {name}")
    inventory = read_csv(output_dir / "finalization_output_hashes_v3_1.csv")
    for row in inventory:
        path = output_dir / row["file"]
        if not path.is_file() or sha(path) != row["sha256"] or path.stat().st_size != int(row["bytes"]):
            raise RuntimeError(f"output hash mismatch: {path}")
    if verification_path.exists():
        raise RuntimeError(f"refusing to overwrite verification: {verification_path}")
    value = {
        "schema_version": 3, "verification_id": "pilot_v3_finalized_attribute_independent_verification_v3_1",
        "verified_at_utc": now(), "finalization_script_sha256": sha(Path(__file__)),
        "output_freeze_sha256": sha(output_dir / "finalization_freeze_v3_1.json"),
        "frame_rows": len(frames), "video_rows": len(unified),
        "facial_hair_frame_rows": len(ledger), "facial_hair_video_rows": len(details),
        "sample_ids_exact": len({row["sample_id"] for row in frames}) == 12,
        "forty_nine_frames_each": all(Counter(row["sample_id"] for row in frames)[sid] == 49 for sid in {row["sample_id"] for row in frames}),
        "all_computed_rows_reproduced_exactly": True,
        "all_listed_output_hashes_verified": True,
        "private_mapping_read_by_verifier": False,
        "frame_level_inference_performed": False,
        "status": "PASS_INDEPENDENT_FINALIZATION_VERIFICATION",
    }
    write_json(verification_path, value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["dry-run", "run", "verify"], required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--verification-path", type=Path)
    args = parser.parse_args()
    preflight(args.output_dir, require_output=args.mode == "verify")
    if args.mode == "dry-run":
        _, _, frames, ledger, details, unified = build_outputs()
        print(json.dumps({
            "status": "PREFLIGHT_PASS", "frame_rows": len(frames),
            "facial_hair_rows": len(ledger), "facial_hair_videos": len(details),
            "unified_videos": len(unified), "outputs_written": False,
        }, indent=2))
    elif args.mode == "run":
        execute(args.output_dir)
        print(json.dumps({
            "status": "FINALIZATION_EXECUTION_PASS",
            "output_dir": str(args.output_dir),
        }, indent=2))
    else:
        verification = args.verification_path or args.output_dir.parent / "finalized_v3_1_independent_verification.json"
        verify(args.output_dir, verification)
        print(json.dumps({"status": "PASS_INDEPENDENT_FINALIZATION_VERIFICATION", "verification": str(verification)}, indent=2))


if __name__ == "__main__":
    main()
