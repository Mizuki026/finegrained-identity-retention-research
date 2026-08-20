#!/usr/bin/env python3
"""Freeze blinded facial-hair submissions and prepare disagreement adjudication.

This program never accesses the private task/condition/identity mapping. It
validates and snapshots the two anonymous submissions, computes workflow-level
agreement, and prepares a randomized third-researcher package containing only
item-level disagreements. It performs no condition-level outcome analysis.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

EXPECTED_HEADER = [
    "annotator_id", "annotation_item_id", "random_order",
    "ordinal_label", "reason_or_note",
]
ALLOWED = {"0", "1", "2", "U"}
SEED = "formal_facial_hair_adjudication_v1_seed_20260820"


class PreparationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise PreparationError(message)


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def validate_submission(path: Path, annotator: str, crop_ids: set[str]) -> list[dict[str, str]]:
    header, rows = read_csv(path)
    if header != EXPECTED_HEADER:
        fail(f"annotator {annotator}: header mismatch")
    if len(rows) != 560:
        fail(f"annotator {annotator}: expected 560 rows, found {len(rows)}")
    ids = []
    orders = []
    for line_number, row in enumerate(rows, 2):
        row.update({key: value.strip() for key, value in row.items()})
        if row["annotator_id"] != annotator:
            fail(f"annotator {annotator}: annotator_id mismatch at line {line_number}")
        if row["ordinal_label"] not in ALLOWED:
            fail(f"annotator {annotator}: invalid/blank label at line {line_number}")
        try:
            order = int(row["random_order"])
        except ValueError as exc:
            raise PreparationError(
                f"annotator {annotator}: invalid random_order at line {line_number}"
            ) from exc
        ids.append(row["annotation_item_id"])
        orders.append(order)
    if len(set(ids)) != 560 or set(ids) != crop_ids:
        fail(f"annotator {annotator}: annotation-item universe mismatch")
    if orders != list(range(1, 561)):
        fail(f"annotator {annotator}: random/physical order mismatch")
    return rows


def kappa_unweighted(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    expected = 0.0
    for label in sorted(ALLOWED):
        expected += (a.count(label) / n) * (b.count(label) / n)
    if math.isclose(expected, 1.0):
        return None
    return (observed - expected) / (1.0 - expected)


def font(size: int):
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def make_contact_sheets(rows: list[dict], crops: Path, output: Path) -> list[Path]:
    output.mkdir(parents=True, exist_ok=False)
    columns, rows_per_page = 4, 5
    cell_w, cell_h = 420, 350
    page_size = columns * rows_per_page
    made = []
    for page_index, start in enumerate(range(0, len(rows), page_size), 1):
        batch = rows[start:start + page_size]
        sheet = Image.new("RGB", (columns * cell_w, rows_per_page * cell_h), "white")
        draw = ImageDraw.Draw(sheet)
        title_font, info_font = font(18), font(14)
        for slot, row in enumerate(batch):
            x = (slot % columns) * cell_w
            y = (slot // columns) * cell_h
            draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline="#888", width=2)
            draw.text((x + 8, y + 7), f"{row['adjudication_id']} | {row['annotation_item_id']}", fill="black", font=title_font)
            draw.text((x + 8, y + 32), f"options: {row['option_1']} / {row['option_2']}", fill="#333", font=info_font)
            image_path = crops / f"{row['annotation_item_id']}.jpg"
            with Image.open(image_path) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((cell_w - 20, cell_h - 72), Image.Resampling.LANCZOS)
                px = x + (cell_w - im.width) // 2
                py = y + 64 + (cell_h - 68 - im.height) // 2
                sheet.paste(im, (px, py))
        path = output / f"facial_hair_adjudication_sheet_{page_index:02d}.png"
        sheet.save(path, optimize=True)
        made.append(path)
    return made


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    output = args.output_dir.resolve()
    if output.exists() or output.with_name(output.name + ".inprogress").exists():
        fail(f"refusing to overwrite output: {output}")
    temp = output.with_name(output.name + ".inprogress")
    temp.mkdir(parents=True, exist_ok=False)
    try:
        materials = run / "facial_hair_annotation_materials_v1"
        crops = run / "facial_hair_blinded_crops_v1"
        crop_ids = {path.stem for path in crops.glob("*.jpg")}
        if len(crop_ids) != 560:
            fail("blinded crop universe is not 560 items")
        source_paths = {
            a: materials / f"annotator_{a}" / f"facial_hair_annotator_{a}_v1.csv"
            for a in "AB"
        }
        rows = {a: validate_submission(source_paths[a], a, crop_ids) for a in "AB"}
        if [r["annotation_item_id"] for r in rows["A"]] == [r["annotation_item_id"] for r in rows["B"]]:
            fail("A/B randomization orders unexpectedly identical")

        snapshots = temp / "submission_snapshots_v1"
        snapshots.mkdir()
        source_hashes = {}
        for a in "AB":
            target = snapshots / f"facial_hair_annotator_{a}_submitted_v1.csv"
            shutil.copyfile(source_paths[a], target)
            os.chmod(target, 0o444)
            source_hashes[a] = sha256_path(target)
            if source_hashes[a] != sha256_path(source_paths[a]):
                fail(f"annotator {a}: snapshot byte mismatch")
        if source_hashes["A"] == source_hashes["B"]:
            fail("A/B submissions are byte-identical")

        by_id = {
            a: {row["annotation_item_id"]: row for row in rows[a]}
            for a in "AB"
        }
        item_ids = sorted(crop_ids)
        agreements = []
        disagreements = []
        for item_id in item_ids:
            left, right = by_id["A"][item_id], by_id["B"][item_id]
            if left["ordinal_label"] == right["ordinal_label"]:
                agreements.append({
                    "annotation_item_id": item_id,
                    "consensus_label": left["ordinal_label"],
                    "consensus_source": "A_B_EXACT_AGREEMENT",
                })
            else:
                disagreements.append((item_id, left, right))

        agreement_fields = ["annotation_item_id", "consensus_label", "consensus_source"]
        write_csv(temp / "agreed_items_pre_adjudication_v1.csv", agreement_fields, agreements)

        randomized = sorted(
            disagreements,
            key=lambda x: hashlib.sha256(f"{SEED}|order|{x[0]}".encode()).hexdigest(),
        )
        adjudication_rows = []
        for index, (item_id, left, right) in enumerate(randomized, 1):
            swap = int(hashlib.sha256(f"{SEED}|swap|{item_id}".encode()).hexdigest(), 16) % 2
            first, second = (right, left) if swap else (left, right)
            adjudication_rows.append({
                "adjudication_id": f"FADJ_{index:03d}",
                "annotation_item_id": item_id,
                "option_1": first["ordinal_label"],
                "option_2": second["ordinal_label"],
                "note_1": first["reason_or_note"],
                "note_2": second["reason_or_note"],
                "allowed_values": "0|1|2|U",
                "adjudicated_value": "",
                "rationale": "",
            })
        adjudication = temp / "adjudication_v1"
        adjudication.mkdir()
        adjudication_fields = [
            "adjudication_id", "annotation_item_id", "option_1", "option_2",
            "note_1", "note_2", "allowed_values", "adjudicated_value", "rationale",
        ]
        write_csv(adjudication / "facial_hair_adjudication_template_v1.csv", adjudication_fields, adjudication_rows)
        codebook = (
            "Formal facial-hair disagreement adjudication codebook v1\n\n"
            "0 = no visible facial hair\n"
            "1 = faint, sparse, or ambiguous visible facial hair\n"
            "2 = clearly visible moustache, beard, goatee, or stubble\n"
            "U = target attribute cannot be observed reliably in the crop\n\n"
            "Review each disagreement independently. Fill adjudicated_value and rationale.\n"
            "The final value may be any allowed value; it need not equal either option.\n"
            "Do not alter other columns. Do not access identity, condition, seed, pair, or private mapping.\n"
        )
        (adjudication / "facial_hair_adjudication_codebook_v1.txt").write_text(codebook, encoding="utf-8")
        sheets = make_contact_sheets(adjudication_rows, crops, adjudication / "contact_sheets")

        labels_a = [by_id["A"][item]["ordinal_label"] for item in item_ids]
        labels_b = [by_id["B"][item]["ordinal_label"] for item in item_ids]
        agreement_report = {
            "schema_version": 1,
            "report_id": "formal_facial_hair_interannotator_agreement_v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "item_count": 560,
            "exact_agreement_count": len(agreements),
            "disagreement_count": len(disagreements),
            "raw_exact_agreement": len(agreements) / 560,
            "cohen_kappa_unweighted_workflow_diagnostic": kappa_unweighted(labels_a, labels_b),
            "notes_preserved": {
                "A": sum(bool(row["reason_or_note"]) for row in rows["A"]),
                "B": sum(bool(row["reason_or_note"]) for row in rows["B"]),
            },
            "private_mapping_accessed": False,
            "condition_level_analysis_performed": False,
            "scientific_outcomes_interpreted": False,
            "status": "AGREEMENT_COMPUTED_ADJUDICATION_PENDING",
        }
        (temp / "interannotator_agreement_v1.json").write_text(
            json.dumps(agreement_report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        commit = subprocess.check_output(
            ["git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        audit = {
            "schema_version": 1,
            "audit_id": "formal_facial_hair_annotation_handoff_v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "run_dir": str(run),
            "output_dir": str(output),
            "preparation_code_commit": commit,
            "preparation_script_sha256": sha256_path(Path(__file__).resolve()),
            "submission_sha256": source_hashes,
            "submission_rows": {"A": len(rows["A"]), "B": len(rows["B"])},
            "submission_notes": agreement_report["notes_preserved"],
            "same_item_universe": True,
            "annotator_orders_distinct": True,
            "exact_agreement_count": len(agreements),
            "disagreement_count": len(disagreements),
            "adjudication_rows": len(adjudication_rows),
            "adjudication_contact_sheet_pages": len(sheets),
            "private_mapping_accessed": False,
            "condition_level_analysis_performed": False,
            "status": "SUBMISSIONS_FROZEN_ADJUDICATION_PACKAGE_READY",
        }
        (temp / "annotation_handoff_audit_v1.json").write_text(
            json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        hash_rows = []
        for path in sorted(p for p in temp.rglob("*") if p.is_file()):
            if path.name == "annotation_handoff_hashes_v1.csv":
                continue
            hash_rows.append({
                "relative_path": str(path.relative_to(temp)),
                "bytes": path.stat().st_size,
                "sha256": sha256_path(path),
            })
        write_csv(temp / "annotation_handoff_hashes_v1.csv", ["relative_path", "bytes", "sha256"], hash_rows)
        temp.rename(output)
        print(json.dumps({
            "status": "SUBMISSIONS_FROZEN_ADJUDICATION_PACKAGE_READY",
            "output_dir": str(output),
            "submitted_rows_A": 560,
            "submitted_rows_B": 560,
            "disagreement_items": len(disagreements),
            "adjudication_sheet_pages": len(sheets),
            "private_mapping_accessed": False,
            "scientific_outcomes_printed": False,
        }, indent=2))
    except Exception:
        raise


if __name__ == "__main__":
    try:
        main()
    except PreparationError as exc:
        raise SystemExit(f"FORMAL ANNOTATION PREPARATION FAILED: {exc}")
