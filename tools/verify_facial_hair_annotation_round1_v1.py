#!/usr/bin/env python3
"""Independently verify the frozen blinded facial-hair annotation table.

Purpose: validate completeness, uniqueness, allowed values, lineage hashes, and
the transcription report before any private mapping is opened. Environment:
Python standard library only, CPU-only, offline. Inputs are read-only. Outputs
are a new JSON report and append-only log. Runtime class: short. The program
fails closed and refuses to overwrite either output.
"""

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


EXPECTED = {
    "protocol": "307f2afb4eb92280359960b70eff81cc188d26a60876db896e451f84cc6f25aa",
    "template": "246059e6b6a03a275e797e27799b2cb8a44e4060b097a732507b7a91be25dc9a",
    "transcript": "db9039ae72b8ee6949e3077165d76ab8572c62cc3b83e6110a3e63ef560c7aea",
    "filled": "4f0f9117b9853c4a590e5f5f85eb26154c7cfb64ecb6f3b88b0d91d2684e2824",
}
EXPECTED_COUNTS = {"0": 291, "1": 146, "2": 84, "U": 54}
EXPECTED_REASONS = {"ambiguous_shadow": 49, "character_transformation": 5}
FIELDS = ["annotation_item_id", "random_order", "ordinal_label", "reason_or_note"]
ALLOWED_LABELS = {"0", "1", "2", "U"}
ALLOWED_REASONS = {"ambiguous_shadow", "character_transformation"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise RuntimeError(message)


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            fail(f"schema mismatch: {path}")
        return list(reader)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--filled", type=Path, required=True)
    parser.add_argument("--transcription-validation", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-log", type=Path, required=True)
    parser.add_argument("--mode", choices=("dry-run", "run"), required=True)
    args = parser.parse_args()

    paths = {
        "protocol": args.protocol,
        "template": args.template,
        "transcript": args.transcript,
        "filled": args.filled,
    }
    observed_hashes = {}
    for role, path in paths.items():
        if not path.is_file():
            fail(f"missing {role}: {path}")
        observed_hashes[role] = sha256(path)
        if observed_hashes[role] != EXPECTED[role]:
            fail(f"{role} SHA256 mismatch: {observed_hashes[role]}")
    if not args.transcription_validation.is_file():
        fail("missing transcription validation JSON")

    template = read_csv(args.template)
    filled = read_csv(args.filled)
    if len(template) != 575 or len(filled) != 575:
        fail(f"row-count mismatch: template={len(template)} filled={len(filled)}")
    expected_orders = [str(index) for index in range(1, 576)]
    if [row["random_order"] for row in template] != expected_orders:
        fail("template random_order is not exactly 1..575")
    if [row["random_order"] for row in filled] != expected_orders:
        fail("filled random_order is not exactly 1..575")
    template_ids = [row["annotation_item_id"] for row in template]
    filled_ids = [row["annotation_item_id"] for row in filled]
    if len(set(template_ids)) != 575 or len(set(filled_ids)) != 575:
        fail("anonymous item IDs are not unique")
    if template_ids != filled_ids:
        fail("anonymous item ID/order mapping differs from the frozen template")
    if any(row["ordinal_label"] or row["reason_or_note"] for row in template):
        fail("frozen anonymous template is not blank")

    label_counts = Counter()
    reason_counts = Counter()
    for row in filled:
        label = row["ordinal_label"]
        reason = row["reason_or_note"]
        if label not in ALLOWED_LABELS:
            fail(f"invalid label at order {row['random_order']}: {label!r}")
        if label == "U":
            if reason not in ALLOWED_REASONS:
                fail(f"invalid U reason at order {row['random_order']}: {reason!r}")
            reason_counts[reason] += 1
        elif reason:
            fail(f"non-U reason at order {row['random_order']}: {reason!r}")
        label_counts[label] += 1
    if dict(label_counts) != EXPECTED_COUNTS:
        fail(f"label-count mismatch: {dict(label_counts)}")
    if dict(reason_counts) != EXPECTED_REASONS:
        fail(f"U-reason-count mismatch: {dict(reason_counts)}")

    validation = json.loads(args.transcription_validation.read_text(encoding="utf-8"))
    if validation.get("status") != "PASS_BLINDED_LABELS_FROZEN_PENDING_UNBLINDING":
        fail("unexpected transcription validation status")
    if validation.get("private_mapping_read") is not False:
        fail("transcription report does not affirm private_mapping_read=false")
    if validation.get("unblinding_authorized") is not False:
        fail("transcription report does not affirm unblinding_authorized=false")
    if validation.get("record_count") != 575:
        fail("transcription report record_count mismatch")
    if validation.get("label_counts") != EXPECTED_COUNTS:
        fail("transcription report label_counts mismatch")
    if validation.get("u_reason_counts") != EXPECTED_REASONS:
        fail("transcription report U-reason counts mismatch")
    if validation.get("output", {}).get("sha256") != EXPECTED["filled"]:
        fail("transcription report filled-output SHA256 mismatch")

    report = {
        "schema_version": 1,
        "status": "PASS_PREUNBLINDING_INDEPENDENT_VALIDATION",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "validation_scope": "anonymous labels only; private mapping not opened",
        "record_count": 575,
        "random_order_set": "exactly_1_to_575",
        "anonymous_item_ids_unique": True,
        "template_lineage_exact": True,
        "label_counts": EXPECTED_COUNTS,
        "u_reason_counts": EXPECTED_REASONS,
        "input_sha256": {
            **observed_hashes,
            "transcription_validation": sha256(args.transcription_validation),
        },
        "verifier_script": str(Path(__file__).resolve()),
        "verifier_script_sha256": sha256(Path(__file__)),
        "private_mapping_read": False,
        "unblinding_authorized": False,
        "research_boundary": "No condition-level or hypothesis result can be computed before separately authorized unblinding.",
    }
    if args.mode == "dry-run":
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    for output in (args.output_json, args.output_log):
        if output.exists():
            fail(f"refusing overwrite: {output}")
        if not output.parent.is_dir():
            fail(f"output directory missing: {output.parent}")
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.output_log.write_text(
        f"{report['validated_at_utc']} PASS_PREUNBLINDING_INDEPENDENT_VALIDATION "
        "records=575 private_mapping_read=false unblinding_authorized=false\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        raise
