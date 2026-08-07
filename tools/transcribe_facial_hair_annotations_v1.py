#!/usr/bin/env python3
"""Transcribe blinded facial-hair labels from a preserved raw transcript.

Purpose: populate the anonymous annotation template without reading the private
sample mapping. Environment: Python standard library only, CPU-only, offline.
Inputs: frozen manual protocol, preserved raw transcript, anonymous template.
Outputs: new filled CSV, validation JSON, append-only log, checksum manifest.
Runtime: short. Writes are refused if any output already exists.
"""

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EXPECTED = {
    "protocol": "307f2afb4eb92280359960b70eff81cc188d26a60876db896e451f84cc6f25aa",
    "template": "246059e6b6a03a275e797e27799b2cb8a44e4060b097a732507b7a91be25dc9a",
    "transcript": "db9039ae72b8ee6949e3077165d76ab8572c62cc3b83e6110a3e63ef560c7aea",
}
OUTPUT_NAMES = (
    "annotation_round1_filled_v1.csv",
    "annotation_round1_preunblinding_validation_v1.json",
    "annotation_round1_transcription_v1.log",
    "annotation_round1_sha256_v1.csv",
)
ALLOWED_LABELS = {"0", "1", "2", "U"}
ALLOWED_U_REASONS = {"ambiguous_shadow", "character_transformation"}
LABEL_PATTERN = re.compile(
    r"(?<!\d)(?P<order>\d{1,3}):(?P<label>[012U])"
    r"(?:,(?P<reason>ambiguous_shadow|character_transformation))?"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fail(message: str) -> None:
    raise RuntimeError(message)


def read_template(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != [
            "annotation_item_id",
            "random_order",
            "ordinal_label",
            "reason_or_note",
        ]:
            fail("anonymous template schema mismatch")
        rows = list(reader)
    orders = [int(row["random_order"]) for row in rows]
    item_ids = [row["annotation_item_id"] for row in rows]
    if len(rows) != 575 or orders != list(range(1, 576)):
        fail("anonymous template is not exactly ordered 1..575")
    if len(item_ids) != len(set(item_ids)):
        fail("anonymous item IDs are not unique")
    if any(row["ordinal_label"] or row["reason_or_note"] for row in rows):
        fail("anonymous template is not blank")
    return rows


def parse_transcript(path: Path):
    text = path.read_text(encoding="utf-8")
    required_headers = (
        "protocol_id: facial_hair_manual_ordinal_v2",
        "annotation_scope: anonymous_items_1_to_575",
        "private_mapping_opened_before_freeze: no",
        "BEGIN_RAW_ANNOTATIONS",
        "END_RAW_ANNOTATIONS",
    )
    for header in required_headers:
        if header not in text:
            fail(f"raw transcript missing required declaration: {header}")
    records = {}
    duplicates = []
    for match in LABEL_PATTERN.finditer(text):
        order = int(match.group("order"))
        label = match.group("label")
        reason = match.group("reason") or ""
        if order in records:
            duplicates.append(order)
        records[order] = (label, reason)
    if duplicates:
        fail(f"duplicate annotation orders: {duplicates}")
    expected_orders = set(range(1, 576))
    observed_orders = set(records)
    if observed_orders != expected_orders:
        fail(
            "annotation order mismatch; "
            f"missing={sorted(expected_orders-observed_orders)} "
            f"extra={sorted(observed_orders-expected_orders)}"
        )
    for order, (label, reason) in records.items():
        if label not in ALLOWED_LABELS:
            fail(f"invalid label at {order}: {label}")
        if label == "U" and reason not in ALLOWED_U_REASONS:
            fail(f"missing/invalid U reason at {order}: {reason!r}")
        if label != "U" and reason:
            fail(f"non-U label has reason at {order}: {reason}")
    return records


def write_csv(path: Path, fieldnames, rows) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("dry-run", "run"), required=True)
    args = parser.parse_args()

    for name, path in (
        ("protocol", args.protocol),
        ("template", args.template),
        ("transcript", args.transcript),
    ):
        if not path.is_file():
            fail(f"missing {name}: {path}")
        observed = sha256(path)
        if observed != EXPECTED[name]:
            fail(f"{name} SHA256 mismatch: {observed}")
    if not args.output_dir.is_dir():
        fail(f"output directory missing: {args.output_dir}")
    output_paths = [args.output_dir / name for name in OUTPUT_NAMES]
    existing = [str(path) for path in output_paths if path.exists()]
    if existing:
        fail(f"refusing overwrite; outputs exist: {existing}")

    template_rows = read_template(args.template)
    records = parse_transcript(args.transcript)
    counts = Counter(label for label, _ in records.values())
    reason_counts = Counter(
        reason for label, reason in records.values() if label == "U"
    )
    preflight = {
        "status": "PREFLIGHT_PASS",
        "record_count": len(records),
        "label_counts": dict(sorted(counts.items())),
        "u_reason_counts": dict(sorted(reason_counts.items())),
        "private_mapping_read": False,
    }
    if args.mode == "dry-run":
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return

    filled_rows = []
    for row in template_rows:
        order = int(row["random_order"])
        label, reason = records[order]
        filled_rows.append(
            {
                "annotation_item_id": row["annotation_item_id"],
                "random_order": row["random_order"],
                "ordinal_label": label,
                "reason_or_note": reason,
            }
        )
    filled_path, validation_path, log_path, checksum_path = output_paths
    write_csv(
        filled_path,
        ["annotation_item_id", "random_order", "ordinal_label", "reason_or_note"],
        filled_rows,
    )
    validation = {
        **preflight,
        "status": "PASS_BLINDED_LABELS_FROZEN_PENDING_UNBLINDING",
        "validated_at_utc": utc_now(),
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": sha256(Path(__file__)),
        "inputs": {
            "protocol": {"path": str(args.protocol), "sha256": EXPECTED["protocol"]},
            "template": {"path": str(args.template), "sha256": EXPECTED["template"]},
            "transcript": {"path": str(args.transcript), "sha256": EXPECTED["transcript"]},
        },
        "output": {"path": str(filled_path), "sha256": sha256(filled_path)},
        "limitations": [
            "single exploratory annotator; no inter-rater reliability claim",
            "annotation time was not recorded in the raw transcript",
            "visible identity and facial appearance could not be hidden",
        ],
        "private_mapping_read": False,
        "unblinding_authorized": False,
    }
    validation_path.write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    log_path.write_text(
        f"{utc_now()} TRANSCRIPTION_PASS records=575 private_mapping_read=false\n",
        encoding="utf-8",
    )
    checksum_rows = []
    for path in (args.protocol, args.template, args.transcript, filled_path, validation_path, log_path):
        checksum_rows.append(
            {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}
        )
    write_csv(checksum_path, ["path", "sha256", "bytes"], checksum_rows)
    print(json.dumps(validation, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        raise
