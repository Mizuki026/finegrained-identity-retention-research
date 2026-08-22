#!/usr/bin/env python3
"""Repack the frozen eyeglasses blind packet as 10 sheets of 56 images each."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/measurement_repair_v1")
REPO = Path("/root/autodl-tmp/finegrained/research_pipeline")
SOURCE = BASE / "eyeglasses_blind_annotation_v1"
OUT = BASE / "eyeglasses_blind_annotation_v1_1"
SOURCE_FREEZE_SHA256 = "df616a68b047097d303743d6f7d8ea450320cac8412aaa4b90df3e3fc4e88b88"
COLS = 7
ROWS = 8
PER_SHEET = COLS * ROWS
EXPECTED_ITEMS = 560


class RepackError(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise RepackError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields, rows):
    with path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def render(annotator: str, ordered_rows, target_dir: Path):
    cell_w, cell_h = 330, 255
    page_w, page_h = COLS * cell_w, ROWS * cell_h
    font = ImageFont.load_default()
    pages = []
    rendered_ids = []
    for page_number in range(1, 11):
        start = (page_number - 1) * PER_SHEET
        batch = ordered_rows[start:start + PER_SHEET]
        require(len(batch) == PER_SHEET, f"annotator {annotator} page {page_number} is incomplete")
        page = Image.new("RGB", (page_w, page_h), "white")
        draw = ImageDraw.Draw(page)
        for offset, row in enumerate(batch):
            x = (offset % COLS) * cell_w
            y = (offset // COLS) * cell_h
            draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline="#707070", width=2)
            title = f"{int(row['random_order']):03d} | {row['annotation_item_id']}"
            draw.text((x + 6, y + 6), title, fill="black", font=font)
            frame_path = SOURCE / "anonymous_frames" / f"{row['annotation_item_id']}.png"
            require(frame_path.is_file(), f"missing anonymous frame: {frame_path}")
            with Image.open(frame_path) as opened:
                frame = opened.convert("RGB")
            frame.thumbnail((cell_w - 12, cell_h - 34), Image.Resampling.LANCZOS)
            px = x + (cell_w - frame.width) // 2
            py = y + 28 + (cell_h - 28 - frame.height) // 2
            page.paste(frame, (px, py))
            rendered_ids.append(row["annotation_item_id"])
        page_path = target_dir / f"eyeglasses_annotator_{annotator}_sheet_{page_number:02d}_of_10_v1_1.png"
        page.save(page_path, format="PNG", optimize=True)
        pages.append({
            "annotator": annotator,
            "sheet_number": page_number,
            "items": PER_SHEET,
            "first_random_order": start + 1,
            "last_random_order": start + PER_SHEET,
            "relative_path": str(page_path.relative_to(OUT.with_name(OUT.name + ".inprogress"))),
            "bytes": page_path.stat().st_size,
            "sha256": sha256(page_path),
        })
    require(rendered_ids == [r["annotation_item_id"] for r in ordered_rows], f"annotator {annotator} order changed")
    return pages


def main():
    source_freeze = SOURCE / "eyeglasses_annotation_packet_freeze_v1.json"
    require(source_freeze.is_file() and sha256(source_freeze) == SOURCE_FREEZE_SHA256, "source annotation freeze mismatch")
    require(not OUT.exists() and not OUT.with_name(OUT.name + ".inprogress").exists(), "v1_1 output already exists")
    require(subprocess.check_output(["git", "-C", str(REPO), "branch", "--show-current"], text=True).strip() == "measurement-repair-v1", "wrong branch")
    require(subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain"], text=True) == "", "working tree not clean")
    committed_script = REPO / "src/repack_eyeglasses_contact_sheets_56_v1_1.py"
    require(committed_script.is_file() and sha256(committed_script) == sha256(Path(__file__)), "repack script is not the committed copy")
    commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    tmp = OUT.with_name(OUT.name + ".inprogress")
    tmp.mkdir(parents=True)
    all_pages = []
    source_template_hashes = {}
    for annotator in ("A", "B"):
        src_csv = SOURCE / f"annotator_{annotator}" / f"eyeglasses_annotator_{annotator}_v1.csv"
        rows = read_csv(src_csv)
        require(len(rows) == EXPECTED_ITEMS, f"annotator {annotator} row count mismatch")
        require([int(r["random_order"]) for r in rows] == list(range(1, EXPECTED_ITEMS + 1)), f"annotator {annotator} random order mismatch")
        require(len({r["annotation_item_id"] for r in rows}) == EXPECTED_ITEMS, f"annotator {annotator} duplicate ID")
        packet_dir = tmp / f"annotator_{annotator}"
        sheets_dir = packet_dir / "contact_sheets"
        sheets_dir.mkdir(parents=True)
        dst_csv = packet_dir / f"eyeglasses_annotator_{annotator}_v1_1.csv"
        shutil.copyfile(src_csv, dst_csv)
        require(sha256(src_csv) == sha256(dst_csv), "template byte copy mismatch")
        source_template_hashes[annotator] = sha256(src_csv)
        all_pages.extend(render(annotator, rows, sheets_dir))
    src_codebook = SOURCE / "eyeglasses_annotation_codebook_v1.txt"
    dst_codebook = tmp / "eyeglasses_annotation_codebook_v1_1.txt"
    shutil.copyfile(src_codebook, dst_codebook)
    require(sha256(src_codebook) == sha256(dst_codebook), "codebook byte copy mismatch")
    write_csv(tmp / "contact_sheet_manifest_v1_1.csv", list(all_pages[0]), all_pages)
    packet = {
        "schema_version": 1,
        "packet_id": "formal_measurement_repair_eyeglasses_blind_annotation_v1_1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "change_from_v1": "layout_only: 10 contact sheets per annotator, 56 images per sheet",
        "source_annotation_freeze_sha256": SOURCE_FREEZE_SHA256,
        "source_templates_copied_byte_for_byte": True,
        "source_template_sha256": source_template_hashes,
        "source_codebook_copied_byte_for_byte": True,
        "annotators": 2,
        "items_per_annotator": EXPECTED_ITEMS,
        "sheets_per_annotator": 10,
        "items_per_sheet": PER_SHEET,
        "layout": {"columns": COLS, "rows": ROWS},
        "randomized_order_changed": False,
        "private_mapping_accessed": False,
        "scientific_content_changed": False,
        "code_binding": {"repository_commit": commit, "repack_script_sha256": sha256(Path(__file__))},
        "status": "READY_FOR_TWO_INDEPENDENT_BLIND_ANNOTATORS",
    }
    write_json(tmp / "eyeglasses_annotation_packet_manifest_v1_1.json", packet)
    artifacts = []
    for path in sorted(p for p in tmp.rglob("*") if p.is_file()):
        artifacts.append({"relative_path": str(path.relative_to(tmp)), "bytes": path.stat().st_size, "sha256": sha256(path)})
    write_csv(tmp / "artifact_hashes_v1_1.csv", ["relative_path", "bytes", "sha256"], artifacts)
    freeze = {
        "schema_version": 1,
        "freeze_id": "formal_measurement_repair_eyeglasses_annotation_packet_v1_1_freeze",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_annotation_freeze_sha256": SOURCE_FREEZE_SHA256,
        "repository_commit": commit,
        "repack_script_sha256": sha256(Path(__file__)),
        "packet_manifest_sha256": sha256(tmp / "eyeglasses_annotation_packet_manifest_v1_1.json"),
        "contact_sheet_manifest_sha256": sha256(tmp / "contact_sheet_manifest_v1_1.csv"),
        "artifact_hashes_sha256": sha256(tmp / "artifact_hashes_v1_1.csv"),
        "sheets_per_annotator": 10,
        "items_per_sheet": 56,
        "annotation_started": False,
        "status": "READY_FOR_TWO_INDEPENDENT_BLIND_ANNOTATORS",
    }
    write_json(tmp / "eyeglasses_annotation_packet_freeze_v1_1.json", freeze)
    tmp.rename(OUT)
    print(json.dumps({
        "status": freeze["status"],
        "annotator_A_sheets": 10,
        "annotator_B_sheets": 10,
        "images_per_sheet": 56,
        "source_templates_byte_identical": True,
        "scientific_content_changed": False,
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except RepackError as exc:
        raise SystemExit(f"CONTACT-SHEET REPACK FAILED: {exc}")
