#!/usr/bin/env python3
"""Audit a frozen reference pool without selecting formal-study samples.

This audit reads labels and identity metadata only. It does not open images,
choose references, define random seeds, inspect generated outcomes, or use a
model/GPU. Outputs are deterministic for a fixed input CSV.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


ATTRIBUTE_SPECS = (
    ("eyeglasses", "eyeglasses_label", "present", "absent"),
    ("facial_hair", "facial_hair_ordinal", "2", "0"),
    ("hair_color", "hair_color_label", "light", "dark"),
)

REQUIRED_COLUMNS = {
    "item_id",
    "identity",
    "gender",
    "eyeglasses_label",
    "facial_hair_ordinal",
    "hair_color_label",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_pool(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"missing required columns: {sorted(missing)}")
        rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    item_ids = [row["item_id"] for row in rows]
    if not rows:
        raise ValueError("candidate pool is empty")
    if any(not item_id for item_id in item_ids):
        raise ValueError("blank item_id")
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("duplicate item_id")
    identity_gender: dict[str, str] = {}
    for row in rows:
        if not row["identity"] or not row["gender"]:
            raise ValueError(f"blank identity/gender for {row['item_id']}")
        prior = identity_gender.setdefault(row["identity"], row["gender"])
        if prior != row["gender"]:
            raise ValueError(f"inconsistent gender for identity {row['identity']}")
    return rows


def gender_counts(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    return dict(sorted(Counter(row["gender"] for row in rows).items()))


def gender_identity_counts(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    identity_gender = {row["identity"]: row["gender"] for row in rows}
    return dict(sorted(Counter(identity_gender.values()).items()))


def audit_pool(rows: list[dict[str, str]]) -> tuple[dict, list[dict[str, str]]]:
    by_identity: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_identity[row["identity"]].append(row)

    cells: list[dict] = []
    matched_rows: list[dict[str, str]] = []
    attributes: dict[str, dict] = {}
    for attribute, column, positive, negative in ATTRIBUTE_SPECS:
        states: dict[str, dict] = {}
        for state in (positive, negative):
            subset = [row for row in rows if row[column] == state]
            states[state] = {
                "images": len(subset),
                "identities": len({row["identity"] for row in subset}),
                "gender_images": gender_counts(subset),
                "gender_identities": gender_identity_counts(subset),
            }
            cells.append(
                {
                    "attribute": attribute,
                    "state": state,
                    **states[state],
                }
            )

        for identity in sorted(by_identity):
            identity_rows = by_identity[identity]
            state_counts = Counter(row[column] for row in identity_rows)
            if state_counts[positive] and state_counts[negative]:
                matched_rows.append(
                    {
                        "attribute": attribute,
                        "identity": identity,
                        "gender": identity_rows[0]["gender"],
                        "state_a": positive,
                        "state_a_images": str(state_counts[positive]),
                        "state_b": negative,
                        "state_b_images": str(state_counts[negative]),
                    }
                )

        matched = [row for row in matched_rows if row["attribute"] == attribute]
        attributes[attribute] = {
            "label_column": column,
            "contrasted_states": [positive, negative],
            "states": states,
            "within_identity_both_states": len(matched),
            "within_identity_gender_counts": dict(
                sorted(Counter(row["gender"] for row in matched).items())
            ),
        }

    combinations: dict[tuple[str, str, str, str], dict[str, object]] = {}
    for row in rows:
        if row["facial_hair_ordinal"] not in {"0", "2"}:
            continue
        key = (
            row["eyeglasses_label"],
            row["facial_hair_ordinal"],
            row["hair_color_label"],
            row["gender"],
        )
        entry = combinations.setdefault(key, {"images": 0, "identities": set()})
        entry["images"] = int(entry["images"]) + 1
        entry["identities"].add(row["identity"])

    factorial = [
        {
            "eyeglasses": key[0],
            "facial_hair_ordinal": key[1],
            "hair_color": key[2],
            "gender": key[3],
            "images": int(value["images"]),
            "identities": len(value["identities"]),
        }
        for key, value in sorted(combinations.items())
    ]

    missing_gender_cells = [
        f"{cell['attribute']}:{cell['state']}"
        for cell in cells
        if set(cell["gender_identities"]) != {"man", "woman"}
    ]
    unpaired_attributes = [
        attribute
        for attribute, value in attributes.items()
        if value["within_identity_both_states"] == 0
    ]
    reasons = []
    if missing_gender_cells:
        reasons.append(
            "cells without both represented gender labels: " + ", ".join(missing_gender_cells)
        )
    if unpaired_attributes:
        reasons.append(
            "attributes without any within-identity opposite-state pair: "
            + ", ".join(unpaired_attributes)
        )

    audit = {
        "schema_version": 1,
        "audit_id": "formal_candidate_pool_feasibility_v1",
        "status": "FEASIBILITY_AUDITED_NO_SELECTION",
        "candidate_images": len(rows),
        "candidate_identities": len(by_identity),
        "gender_images": gender_counts(rows),
        "gender_identities": gender_identity_counts(rows),
        "attributes": attributes,
        "cells": cells,
        "factorial_combinations_excluding_facial_hair_ordinal_1": factorial,
        "design_diagnostics": {
            "six_cell_gender_balanced": not missing_gender_cells,
            "all_attributes_have_within_identity_pair": not unpaired_attributes,
            "reasons": reasons,
        },
        "boundary": (
            "Aggregate feasibility audit only; no sample selection, randomization, "
            "generation, outcome inspection, hypothesis test, or population claim."
        ),
    }
    return audit, matched_rows


def write_outputs(
    audit: dict,
    matched_rows: list[dict[str, str]],
    pool_path: Path,
    output_json: Path,
    output_csv: Path,
) -> None:
    audit = dict(audit)
    audit["input"] = {
        "filename": pool_path.name,
        "sha256": sha256_file(pool_path),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    columns = [
        "attribute",
        "identity",
        "gender",
        "state_a",
        "state_a_images",
        "state_b",
        "state_b_images",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(matched_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-csv", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--matched-csv", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_pool(args.pool_csv)
    audit, matched_rows = audit_pool(rows)
    write_outputs(audit, matched_rows, args.pool_csv, args.output_json, args.matched_csv)
    print(f"Candidates: {audit['candidate_images']}")
    print(f"Identities: {audit['candidate_identities']}")
    for attribute in (spec[0] for spec in ATTRIBUTE_SPECS):
        value = audit["attributes"][attribute]
        print(f"{attribute} within-identity pairs: {value['within_identity_both_states']}")
    print("Final references selected: NO")
    print(f"Audit: {args.output_json}")
    print(f"Matched candidates: {args.matched_csv}")
    print(f"Status: {audit['status']}")


if __name__ == "__main__":
    main()
