#!/usr/bin/env python3
"""Independent no-private-mapping verification of facial-hair unblinding v1.

CPU-only, offline, and read-only except for new versioned verification outputs.
It deliberately never accepts a private-mapping path. It checks the reconciled
table against frozen labels, the frame inventory, manifest, and producer audit.
"""

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


EXPECTED = {
    "frozen_labels": "4f0f9117b9853c4a590e5f5f85eb26154c7cfb64ecb6f3b88b0d91d2684e2824",
    "frame_inventory": "805df7257f1d207a1d693a21337b79e65269246a3fffbcdee3555569cd0e06d3",
    "manifest": "dcf66f0222986403493a7c9a09d310629909d4aef590634348b41ce12544f79d",
    "reconciled": "e97e3f4f8b2e1b11d9463a5d1bb78fe816989700cc8fa3e8934a5a9efe61050c",
}
LABEL_FIELDS = ["annotation_item_id", "random_order", "ordinal_label", "reason_or_note"]
OUT_FIELDS = LABEL_FIELDS + ["sample_id", "frame_index", "manifest_attribute", "manifest_label", "source_frame_timestamp_seconds", "source_attribute_frame_status", "record_status"]
MANIFEST_FIELDS = ["sample_id", "attribute", "granularity", "label", "identity", "reference_sample", "reference_path", "reference_sha256", "output_dir"]


def fail(message):
    raise RuntimeError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(role, path):
    if not path.is_file():
        fail(f"missing {role}: {path}")
    observed = sha(path)
    if observed != EXPECTED[role]:
        fail(f"{role} SHA256 mismatch: {observed}")
    return observed


def read_csv(path, fields=None):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if fields is not None and reader.fieldnames != fields:
            fail(f"schema mismatch for {path}: {reader.fieldnames}")
        return list(reader)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-labels", type=Path, required=True)
    parser.add_argument("--frame-inventory", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reconciled", type=Path, required=True)
    parser.add_argument("--producer-audit", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-log", type=Path, required=True)
    parser.add_argument("--mode", choices=("dry-run", "run"), required=True)
    args = parser.parse_args()
    for output in (args.output_json, args.output_log):
        if output.exists():
            fail(f"refusing overwrite: {output}")
        if not output.parent.is_dir():
            fail(f"output parent missing: {output.parent}")
    hashes = {"frozen_labels": check("frozen_labels", args.frozen_labels), "frame_inventory": check("frame_inventory", args.frame_inventory), "manifest": check("manifest", args.manifest), "reconciled": check("reconciled", args.reconciled)}
    labels = read_csv(args.frozen_labels, LABEL_FIELDS)
    reconciled = read_csv(args.reconciled, OUT_FIELDS)
    manifest = read_csv(args.manifest, MANIFEST_FIELDS)
    frames = read_csv(args.frame_inventory)
    if len(labels) != 575 or len(reconciled) != 575:
        fail(f"row-count mismatch labels={len(labels)} reconciled={len(reconciled)}")
    label_by_id = {row["annotation_item_id"]: row for row in labels}
    if len(label_by_id) != 575:
        fail("frozen annotation IDs not unique")
    if [r["random_order"] for r in reconciled] != [str(i) for i in range(1, 576)]:
        fail("reconciled random_order is not exactly 1..575")
    if [r["annotation_item_id"] for r in reconciled] != [r["annotation_item_id"] for r in labels]:
        fail("reconciled anonymous IDs/order differ from frozen labels")
    by_manifest = {row["sample_id"]: row for row in manifest}
    if len(by_manifest) != 12:
        fail("manifest sample uniqueness failure")
    by_frame = {}
    for row in frames:
        item = row.get("annotation_item_id", "")
        if item:
            if item in by_frame:
                fail(f"duplicate frame inventory annotation ID: {item}")
            by_frame[item] = row
    if set(by_frame) != set(label_by_id):
        fail("frame inventory anonymous-ID closure failure")
    for row in reconciled:
        item = row["annotation_item_id"]
        frozen = label_by_id[item]
        if any(row[key] != frozen[key] for key in LABEL_FIELDS):
            fail(f"frozen label changed during reconciliation: {item}")
        if row["record_status"] != "MAPPED":
            fail(f"unexpected record status: {item}")
        source = by_frame[item]
        if row["sample_id"] != source["sample_id"] or row["frame_index"] != source["frame_index"]:
            fail(f"source sample/frame mismatch: {item}")
        if row["source_frame_timestamp_seconds"] != source["timestamp_seconds"] or row["source_attribute_frame_status"] != source["attribute_frame_status"]:
            fail(f"source frame metadata mismatch: {item}")
        mrow = by_manifest.get(row["sample_id"])
        if mrow is None or row["manifest_attribute"] != mrow["attribute"] or row["manifest_label"] != mrow["label"]:
            fail(f"manifest mapping mismatch: {item}")
    audit = json.loads(args.producer_audit.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS_MAPPING_RECONCILIATION_ONLY_NO_CONDITION_ANALYSIS":
        fail("producer audit status mismatch")
    if audit.get("private_mapping_read_count") != 1 or audit.get("condition_level_analysis_performed") is not False:
        fail("producer audit violates declared one-read/no-analysis boundary")
    if audit.get("output", {}).get("sha256") != EXPECTED["reconciled"]:
        fail("producer audit output SHA mismatch")
    report = {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_UNBLINDING_VERIFICATION_NO_CONDITION_ANALYSIS",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_label_rows": 575,
        "reconciled_rows": 575,
        "frozen_labels_preserved_exactly": True,
        "anonymous_id_order_exact": True,
        "frame_inventory_closure_exact": True,
        "manifest_join_exact": True,
        "private_mapping_read_by_verifier": False,
        "condition_level_analysis_performed": False,
        "input_sha256": {**hashes, "producer_audit": sha(args.producer_audit)},
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": sha(Path(__file__)),
    }
    if args.mode == "dry-run":
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_log.write_text(f"{report['verified_at_utc']} PASS_INDEPENDENT_UNBLINDING_VERIFICATION rows=575 mapping_read_by_verifier=false condition_analysis=false\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        raise
