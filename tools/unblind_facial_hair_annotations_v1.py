#!/usr/bin/env python3
"""One-time, fail-closed reconciliation of frozen blinded facial-hair labels.

Purpose: join a frozen anonymous label table to the private mapping and verify
each mapped sample/frame against frozen Pilot inputs. Environment: Python
standard library only, CPU-only, offline. The mapping is read exactly once in
run mode (as one byte read); dry-run does not read mapping contents. Outputs
are new versioned files and are refused if the output directory already exists.
No condition-level analysis is performed.
"""

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_SHA256 = {
    "protocol": "307f2afb4eb92280359960b70eff81cc188d26a60876db896e451f84cc6f25aa",
    "frozen_labels": "4f0f9117b9853c4a590e5f5f85eb26154c7cfb64ecb6f3b88b0d91d2684e2824",
    "template": "246059e6b6a03a275e797e27799b2cb8a44e4060b097a732507b7a91be25dc9a",
    "mapping": "25c193ce53bbe9cb57c4629f3775c5b73f20a43c0c71cf30645c9dd00c3c678b",
    "frame_inventory": "805df7257f1d207a1d693a21337b79e65269246a3fffbcdee3555569cd0e06d3",
    "manifest": "dcf66f0222986403493a7c9a09d310629909d4aef590634348b41ce12544f79d",
    "config": "40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47",
}
LABEL_FIELDS = ["annotation_item_id", "random_order", "ordinal_label", "reason_or_note"]
MAPPING_FIELDS = ["annotation_item_id", "sample_id", "frame_index"]
MANIFEST_FIELDS = ["sample_id", "attribute", "granularity", "label", "identity", "reference_sample", "reference_path", "reference_sha256", "output_dir"]
FRAME_REQUIRED = {"sample_id", "attribute", "frame_index", "timestamp_seconds", "attribute_frame_status", "annotation_item_id", "record_status"}
OUTPUT_FIELDS = ["annotation_item_id", "random_order", "ordinal_label", "reason_or_note", "sample_id", "frame_index", "manifest_attribute", "manifest_label", "source_frame_timestamp_seconds", "source_attribute_frame_status", "record_status"]


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path, expected_fields):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_fields:
            fail(f"schema mismatch for {path}: {reader.fieldnames}")
        return list(reader)


def write_csv(path: Path, fields, rows) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def check_hash(role: str, path: Path) -> str:
    if not path.is_file():
        fail(f"missing {role}: {path}")
    observed = sha256_path(path)
    if observed != EXPECTED_SHA256[role]:
        fail(f"{role} SHA256 mismatch: {observed}")
    return observed


def load_public_inputs(args):
    hashes = {}
    for role, path in (("protocol", args.protocol), ("frozen_labels", args.frozen_labels), ("template", args.template), ("frame_inventory", args.frame_inventory), ("manifest", args.manifest), ("config", args.config)):
        hashes[role] = check_hash(role, path)
    if not args.mapping.is_file():
        fail(f"missing private mapping: {args.mapping}")
    labels = read_csv(args.frozen_labels, LABEL_FIELDS)
    template = read_csv(args.template, LABEL_FIELDS)
    manifest = read_csv(args.manifest, MANIFEST_FIELDS)
    with args.frame_inventory.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not FRAME_REQUIRED.issubset(reader.fieldnames):
            fail("frame inventory schema missing required fields")
        frames = list(reader)
    if len(labels) != 575 or len(template) != 575:
        fail(f"annotation row-count mismatch labels={len(labels)} template={len(template)}")
    if [row["random_order"] for row in labels] != [str(i) for i in range(1, 576)]:
        fail("frozen label random order is not exactly 1..575")
    if [row["random_order"] for row in template] != [str(i) for i in range(1, 576)]:
        fail("template random order is not exactly 1..575")
    label_ids = [row["annotation_item_id"] for row in labels]
    template_ids = [row["annotation_item_id"] for row in template]
    if len(set(label_ids)) != 575 or label_ids != template_ids:
        fail("frozen labels do not exactly match anonymous template lineage")
    if any(row["ordinal_label"] or row["reason_or_note"] for row in template):
        fail("anonymous template is not blank")
    if len(manifest) != 12 or len({row["sample_id"] for row in manifest}) != 12:
        fail("manifest does not contain exactly 12 unique samples")
    if len(frames) != 1764:
        fail(f"unexpected frame inventory count: {len(frames)}")
    return hashes, labels, manifest, frames


def parse_mapping_once(path: Path):
    # This is intentionally the sole mapping-content read in the program.
    raw = path.read_bytes()
    observed = sha256_bytes(raw)
    if observed != EXPECTED_SHA256["mapping"]:
        fail(f"private mapping SHA256 mismatch: {observed}")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    if reader.fieldnames != MAPPING_FIELDS:
        fail(f"private mapping schema mismatch: {reader.fieldnames}")
    return observed, list(reader)


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("protocol", "frozen_labels", "template", "mapping", "frame_inventory", "manifest", "config"):
        parser.add_argument(f"--{name.replace('_', '-')}", dest=name, type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("dry-run", "run"), required=True)
    args = parser.parse_args()

    if args.output_dir.exists():
        fail(f"refusing overwrite; output directory exists: {args.output_dir}")
    if not args.output_dir.parent.is_dir():
        fail(f"output parent missing: {args.output_dir.parent}")
    hashes, labels, manifest, frames = load_public_inputs(args)
    preflight = {
        "status": "PREFLIGHT_PASS_MAPPING_NOT_READ",
        "frozen_label_rows": len(labels),
        "manifest_rows": len(manifest),
        "frame_inventory_rows": len(frames),
        "private_mapping_read_count": 0,
        "expected_private_mapping_sha256": EXPECTED_SHA256["mapping"],
        "public_input_sha256": hashes,
        "unblinding_authorized": True,
        "scope": "mapping reconciliation only; no condition-level analysis",
    }
    if args.mode == "dry-run":
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return

    mapping_hash, mapping = parse_mapping_once(args.mapping)
    mapping_ids = [row["annotation_item_id"] for row in mapping]
    if len(mapping) != 575 or len(set(mapping_ids)) != 575:
        fail(f"mapping cardinality/uniqueness failure: rows={len(mapping)} unique_ids={len(set(mapping_ids))}")
    label_ids = [row["annotation_item_id"] for row in labels]
    if set(mapping_ids) != set(label_ids):
        fail("private mapping anonymous-ID set does not exactly match frozen labels")
    mapping_by_id = {row["annotation_item_id"]: row for row in mapping}
    manifest_by_sample = {row["sample_id"]: row for row in manifest}
    frame_by_id = {}
    for row in frames:
        item = row["annotation_item_id"]
        if item:
            if item in frame_by_id:
                fail(f"duplicate annotation_item_id in frame inventory: {item}")
            frame_by_id[item] = row
    if set(frame_by_id) != set(label_ids):
        fail("frame inventory anonymous-ID set does not exactly match frozen labels")
    reconciled = []
    for label in labels:
        item = label["annotation_item_id"]
        mapping_row = mapping_by_id[item]
        sample_id = mapping_row["sample_id"]
        frame_index = mapping_row["frame_index"]
        if sample_id not in manifest_by_sample:
            fail(f"mapping sample missing from manifest: {sample_id}")
        try:
            parsed_index = int(frame_index)
        except ValueError as exc:
            raise RuntimeError(f"non-integer mapping frame_index for {item}: {frame_index!r}") from exc
        if not 0 <= parsed_index <= 48:
            fail(f"mapping frame_index out of range for {item}: {frame_index}")
        source = frame_by_id[item]
        if source["sample_id"] != sample_id or source["frame_index"] != frame_index:
            fail(f"mapping/frame-inventory mismatch for {item}")
        manifest_row = manifest_by_sample[sample_id]
        reconciled.append({
            **label,
            "sample_id": sample_id,
            "frame_index": frame_index,
            "manifest_attribute": manifest_row["attribute"],
            "manifest_label": manifest_row["label"],
            "source_frame_timestamp_seconds": source["timestamp_seconds"],
            "source_attribute_frame_status": source["attribute_frame_status"],
            "record_status": "MAPPED",
        })
    if len(reconciled) != 575:
        fail("reconciled table row count mismatch")
    output_csv = args.output_dir / "facial_hair_annotation_unblinded_v1.csv"
    audit_json = args.output_dir / "facial_hair_unblinding_audit_v1.json"
    log_path = args.output_dir / "facial_hair_unblinding_v1.log"
    checksums_csv = args.output_dir / "input_output_sha256_v1.csv"
    args.output_dir.mkdir()
    write_csv(output_csv, OUTPUT_FIELDS, reconciled)
    timestamp = datetime.now(timezone.utc).isoformat()
    audit = {
        "schema_version": 1,
        "status": "PASS_MAPPING_RECONCILIATION_ONLY_NO_CONDITION_ANALYSIS",
        "executed_at_utc": timestamp,
        "frozen_label_rows": 575,
        "mapping_rows": 575,
        "reconciled_rows": 575,
        "anonymous_id_set_exact_match": True,
        "sample_frame_inventory_exact_match": True,
        "manifest_sample_membership_exact_match": True,
        "private_mapping_read_count": 1,
        "unblinding_authorized": True,
        "condition_level_analysis_performed": False,
        "input_sha256": {**hashes, "mapping": mapping_hash},
        "output": {"path": str(output_csv), "sha256": sha256_path(output_csv)},
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": sha256_path(Path(__file__)),
    }
    audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log_path.write_text(f"{timestamp} PASS_MAPPING_RECONCILIATION rows=575 mapping_read_count=1 condition_analysis=false\n", encoding="utf-8")
    checksum_rows = []
    for path in (args.protocol, args.frozen_labels, args.template, args.mapping, args.frame_inventory, args.manifest, args.config, output_csv, audit_json, log_path):
        checksum_rows.append({"path": str(path), "sha256": sha256_path(path), "bytes": path.stat().st_size})
    write_csv(checksums_csv, ["path", "sha256", "bytes"], checksum_rows)
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        raise
