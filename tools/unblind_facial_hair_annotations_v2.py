#!/usr/bin/env python3
"""One-read, fail-closed reconciliation of frozen blinded facial-hair labels.

CPU-only and offline. Dry-run reads no private-mapping contents. Run mode uses
exactly one `Path.read_bytes()` call for the private mapping, then parses and
hashes that in-memory byte string. It creates a new output directory only.
No condition-level result is calculated.
"""

import argparse
import csv
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


HASHES = {
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
OUT_FIELDS = LABEL_FIELDS + ["sample_id", "frame_index", "manifest_attribute", "manifest_label", "source_frame_timestamp_seconds", "source_attribute_frame_status", "record_status"]


def fail(message):
    raise RuntimeError(message)


def sha_path(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_hash(role, path):
    if not path.is_file():
        fail(f"missing {role}: {path}")
    observed = sha_path(path)
    if observed != HASHES[role]:
        fail(f"{role} SHA256 mismatch: {observed}")
    return observed


def read_csv(path, fields):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            fail(f"schema mismatch for {path}: {reader.fieldnames}")
        return list(reader)


def read_frame_inventory(path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not FRAME_REQUIRED.issubset(reader.fieldnames):
            fail("frame inventory schema missing required fields")
        return list(reader)


def write_csv(path, fields, rows):
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def public_preflight(args):
    observed = {}
    for role in ("protocol", "frozen_labels", "template", "frame_inventory", "manifest", "config"):
        observed[role] = check_hash(role, getattr(args, role))
    if not args.mapping.is_file():
        fail(f"missing private mapping: {args.mapping}")
    labels = read_csv(args.frozen_labels, LABEL_FIELDS)
    template = read_csv(args.template, LABEL_FIELDS)
    manifest = read_csv(args.manifest, MANIFEST_FIELDS)
    frames = read_frame_inventory(args.frame_inventory)
    expected_order = [str(i) for i in range(1, 576)]
    label_ids = [row["annotation_item_id"] for row in labels]
    if len(labels) != 575 or len(template) != 575 or len(set(label_ids)) != 575:
        fail("frozen label cardinality/uniqueness failure")
    if [r["random_order"] for r in labels] != expected_order or [r["random_order"] for r in template] != expected_order:
        fail("label/template random_order is not exactly 1..575")
    if label_ids != [r["annotation_item_id"] for r in template]:
        fail("frozen labels do not exactly match template anonymous IDs/order")
    if any(row["ordinal_label"] or row["reason_or_note"] for row in template):
        fail("template is not blank")
    if len(manifest) != 12 or len({r["sample_id"] for r in manifest}) != 12:
        fail("manifest cardinality/uniqueness failure")
    if len(frames) != 1764:
        fail(f"frame inventory row count mismatch: {len(frames)}")
    return observed, labels, manifest, frames


def read_mapping_once(path):
    # The only operation in this script that reads mapping contents.
    raw = path.read_bytes()
    observed = hashlib.sha256(raw).hexdigest()
    if observed != HASHES["mapping"]:
        fail(f"private mapping SHA256 mismatch: {observed}")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    if reader.fieldnames != MAPPING_FIELDS:
        fail(f"private mapping schema mismatch: {reader.fieldnames}")
    return observed, list(reader), len(raw)


def main():
    parser = argparse.ArgumentParser()
    for name in ("protocol", "frozen_labels", "template", "mapping", "frame_inventory", "manifest", "config"):
        parser.add_argument("--" + name.replace("_", "-"), dest=name, type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("dry-run", "run"), required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        fail(f"refusing overwrite; output directory exists: {args.output_dir}")
    if not args.output_dir.parent.is_dir():
        fail(f"output parent missing: {args.output_dir.parent}")

    observed, labels, manifest, frames = public_preflight(args)
    preflight = {
        "status": "PREFLIGHT_PASS_MAPPING_NOT_READ",
        "frozen_label_rows": 575,
        "manifest_rows": 12,
        "frame_inventory_rows": 1764,
        "private_mapping_read_count": 0,
        "expected_private_mapping_sha256": HASHES["mapping"],
        "public_input_sha256": observed,
        "unblinding_authorized": True,
        "condition_level_analysis_performed": False,
    }
    if args.mode == "dry-run":
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return

    mapping_hash, mapping, mapping_bytes = read_mapping_once(args.mapping)
    mapping_ids = [row["annotation_item_id"] for row in mapping]
    label_ids = [row["annotation_item_id"] for row in labels]
    if len(mapping) != 575 or len(set(mapping_ids)) != 575 or set(mapping_ids) != set(label_ids):
        fail("mapping/label cardinality or anonymous-ID set mismatch")
    by_mapping = {row["annotation_item_id"]: row for row in mapping}
    by_manifest = {row["sample_id"]: row for row in manifest}
    by_frame = {}
    for row in frames:
        item = row["annotation_item_id"]
        if item:
            if item in by_frame:
                fail(f"duplicate annotation ID in frame inventory: {item}")
            by_frame[item] = row
    if set(by_frame) != set(label_ids):
        fail("frame-inventory/label anonymous-ID set mismatch")
    reconciled = []
    for label in labels:
        item = label["annotation_item_id"]
        mapped = by_mapping[item]
        source = by_frame[item]
        sample_id, frame_index = mapped["sample_id"], mapped["frame_index"]
        if sample_id not in by_manifest:
            fail(f"mapping sample absent from manifest: {sample_id}")
        try:
            index_int = int(frame_index)
        except ValueError as exc:
            raise RuntimeError(f"non-integer frame index: {item}={frame_index!r}") from exc
        if index_int < 0 or index_int > 48:
            fail(f"frame index out of range: {item}={frame_index}")
        if source["sample_id"] != sample_id or source["frame_index"] != frame_index:
            fail(f"mapping/frame inventory mismatch: {item}")
        mrow = by_manifest[sample_id]
        reconciled.append({**label, "sample_id": sample_id, "frame_index": frame_index, "manifest_attribute": mrow["attribute"], "manifest_label": mrow["label"], "source_frame_timestamp_seconds": source["timestamp_seconds"], "source_attribute_frame_status": source["attribute_frame_status"], "record_status": "MAPPED"})
    if len(reconciled) != 575:
        fail("reconciled row count mismatch")

    args.output_dir.mkdir()
    output_csv = args.output_dir / "facial_hair_annotation_unblinded_v1.csv"
    audit_json = args.output_dir / "facial_hair_unblinding_audit_v1.json"
    log_path = args.output_dir / "facial_hair_unblinding_v1.log"
    checksum_csv = args.output_dir / "input_output_sha256_v1.csv"
    write_csv(output_csv, OUT_FIELDS, reconciled)
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
        "private_mapping_bytes_read": mapping_bytes,
        "unblinding_authorized": True,
        "condition_level_analysis_performed": False,
        "input_sha256": {**observed, "mapping": mapping_hash},
        "output": {"path": str(output_csv), "sha256": sha_path(output_csv)},
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": sha_path(Path(__file__)),
    }
    audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log_path.write_text(f"{timestamp} PASS_MAPPING_RECONCILIATION rows=575 mapping_read_count=1 condition_analysis=false\n", encoding="utf-8")
    items = [(args.protocol, None), (args.frozen_labels, None), (args.template, None), (args.frame_inventory, None), (args.manifest, None), (args.config, None), (output_csv, None), (audit_json, None), (log_path, None), (args.mapping, mapping_hash)]
    rows = []
    for path, preserved_hash in items:
        rows.append({"path": str(path), "sha256": preserved_hash or sha_path(path), "bytes": path.stat().st_size})
    write_csv(checksum_csv, ["path", "sha256", "bytes"], rows)
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        raise
