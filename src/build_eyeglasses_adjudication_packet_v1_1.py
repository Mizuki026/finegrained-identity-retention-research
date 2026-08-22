#!/usr/bin/env python3
"""Validate two blind submissions, quantify agreement, and build blind adjudication."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/measurement_repair_v1")
PACKET = BASE / "eyeglasses_blind_annotation_v1_1"
OUT = BASE / "eyeglasses_blind_annotation_agreement_v1_1"
REPO = Path("/root/autodl-tmp/finegrained/research_pipeline")
EXPECTED_PACKET_FREEZE_SHA = "61768a028d14ef0edc9391ff1fa949617031a120bb5ce58c662bdfd825134adc"
EXPECTED_ROWS = 560


class AdjudicationError(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise AdjudicationError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def write_csv(path: Path, fields, rows):
    with path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_submission(annotator: str, path: Path):
    expected_fields = ["annotator_id", "annotation_item_id", "random_order", "face_eye_region_observable_yes_no", "eyeglasses_label", "annotation_confidence_high_low", "reason_or_note"]
    fields, rows = read_csv(path)
    require(fields == expected_fields, f"annotator {annotator} header mismatch")
    require(len(rows) == EXPECTED_ROWS, f"annotator {annotator} row count mismatch")
    require(len({r["annotation_item_id"] for r in rows}) == EXPECTED_ROWS, f"annotator {annotator} duplicate ID")
    require([int(r["random_order"]) for r in rows] == list(range(1, EXPECTED_ROWS + 1)), f"annotator {annotator} order changed")
    for row in rows:
        require(row["annotator_id"] == annotator, f"annotator {annotator} ID mismatch")
        obs = row["face_eye_region_observable_yes_no"].strip()
        label = row["eyeglasses_label"].strip()
        confidence = row["annotation_confidence_high_low"].strip()
        require(obs in {"yes", "no"}, f"invalid observability: {row['annotation_item_id']}")
        require(label in {"present", "absent", "U"}, f"invalid label: {row['annotation_item_id']}")
        require(confidence in {"high", "low"}, f"invalid confidence: {row['annotation_item_id']}")
        require((obs == "no") == (label == "U"), f"observability-label logic mismatch: {row['annotation_item_id']}")
        require(label != "U" or bool(row["reason_or_note"].strip()), f"U without note: {row['annotation_item_id']}")
    return rows


def kappa(values_a, values_b):
    require(len(values_a) == len(values_b) and values_a, "invalid kappa inputs")
    n = len(values_a)
    observed = sum(a == b for a, b in zip(values_a, values_b)) / n
    categories = sorted(set(values_a) | set(values_b))
    count_a, count_b = Counter(values_a), Counter(values_b)
    expected = sum((count_a[c] / n) * (count_b[c] / n) for c in categories)
    value = (observed - expected) / (1 - expected) if expected < 1 else 1.0
    return observed, expected, value


def render_disputes(disputed_ids, output_dir: Path):
    cols, rows_per_page = 5, 6
    per_page = cols * rows_per_page
    cell_w, cell_h = 360, 280
    font = ImageFont.load_default()
    output_dir.mkdir()
    pages = []
    for page_no, start in enumerate(range(0, len(disputed_ids), per_page), 1):
        batch = disputed_ids[start:start + per_page]
        page = Image.new("RGB", (cols * cell_w, rows_per_page * cell_h), "white")
        draw = ImageDraw.Draw(page)
        for offset, item_id in enumerate(batch):
            x, y = (offset % cols) * cell_w, (offset // cols) * cell_h
            draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline="#707070", width=2)
            draw.text((x + 7, y + 7), item_id, fill="black", font=font)
            path = PACKET.parent / "eyeglasses_blind_annotation_v1" / "anonymous_frames" / f"{item_id}.png"
            require(path.is_file(), f"missing anonymous frame: {item_id}")
            with Image.open(path) as opened:
                frame = opened.convert("RGB")
            frame.thumbnail((cell_w - 14, cell_h - 35), Image.Resampling.LANCZOS)
            page.paste(frame, (x + (cell_w - frame.width) // 2, y + 29 + (cell_h - 29 - frame.height) // 2))
        out = output_dir / f"eyeglasses_adjudication_sheet_{page_no:02d}_v1_1.png"
        page.save(out, format="PNG", optimize=True)
        pages.append(out)
    return pages


def main():
    require(not OUT.exists() and not OUT.with_name(OUT.name + ".inprogress").exists(), "agreement output already exists")
    packet_freeze = PACKET / "eyeglasses_annotation_packet_freeze_v1_1.json"
    require(packet_freeze.is_file(), "packet freeze missing")
    if EXPECTED_PACKET_FREEZE_SHA is not None:
        require(sha256(packet_freeze) == EXPECTED_PACKET_FREEZE_SHA, "packet freeze mismatch")
    require(subprocess.check_output(["git", "-C", str(REPO), "branch", "--show-current"], text=True).strip() == "measurement-repair-v1", "wrong branch")
    require(subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain"], text=True) == "", "working tree not clean")
    committed = REPO / "src/build_eyeglasses_adjudication_packet_v1_1.py"
    require(committed.is_file() and sha256(committed) == sha256(Path(__file__)), "script is not committed copy")
    commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    paths = {a: PACKET / f"annotator_{a}" / f"eyeglasses_annotator_{a}_v1_1.csv" for a in ("A", "B")}
    submissions = {a: validate_submission(a, paths[a]) for a in ("A", "B")}
    maps = {a: {r["annotation_item_id"]: r for r in submissions[a]} for a in ("A", "B")}
    require(set(maps["A"]) == set(maps["B"]), "A/B item sets differ")
    ids = sorted(maps["A"])
    obs_a = [maps["A"][i]["face_eye_region_observable_yes_no"].strip() for i in ids]
    obs_b = [maps["B"][i]["face_eye_region_observable_yes_no"].strip() for i in ids]
    lab_a = [maps["A"][i]["eyeglasses_label"].strip() for i in ids]
    lab_b = [maps["B"][i]["eyeglasses_label"].strip() for i in ids]
    conf_a = [maps["A"][i]["annotation_confidence_high_low"].strip() for i in ids]
    conf_b = [maps["B"][i]["annotation_confidence_high_low"].strip() for i in ids]
    obs_stats, label_stats, confidence_stats = kappa(obs_a, obs_b), kappa(lab_a, lab_b), kappa(conf_a, conf_b)
    disagreement_rows = []
    disputed_ids = []
    for item_id in ids:
        a, b = maps["A"][item_id], maps["B"][item_id]
        fields = []
        if a["face_eye_region_observable_yes_no"].strip() != b["face_eye_region_observable_yes_no"].strip():
            fields.append(("face_eye_region_observable_yes_no", a["face_eye_region_observable_yes_no"].strip(), b["face_eye_region_observable_yes_no"].strip(), "yes|no"))
        if a["eyeglasses_label"].strip() != b["eyeglasses_label"].strip():
            fields.append(("eyeglasses_label", a["eyeglasses_label"].strip(), b["eyeglasses_label"].strip(), "present|absent|U"))
        if fields:
            disputed_ids.append(item_id)
        for field, option_a, option_b, allowed in fields:
            disagreement_rows.append({
                "annotation_item_id": item_id,
                "field": field,
                "option_A": option_a,
                "option_B": option_b,
                "note_A": a["reason_or_note"],
                "note_B": b["reason_or_note"],
                "allowed_values": allowed,
                "adjudicated_value": "",
                "rationale": "",
            })
    require(disputed_ids, "no substantive disagreements; no adjudication packet needed")
    tmp = OUT.with_name(OUT.name + ".inprogress")
    tmp.mkdir(parents=True)
    snapshots = tmp / "submitted_snapshots"
    snapshots.mkdir()
    submitted_hashes = {}
    for a in ("A", "B"):
        dst = snapshots / f"eyeglasses_annotator_{a}_submitted_v1_1.csv"
        shutil.copyfile(paths[a], dst)
        submitted_hashes[a] = sha256(dst)
    disagreement_path = tmp / "eyeglasses_adjudication_template_v1_1.csv"
    fields = ["annotation_item_id", "field", "option_A", "option_B", "note_A", "note_B", "allowed_values", "adjudicated_value", "rationale"]
    write_csv(disagreement_path, fields, disagreement_rows)
    pages = render_disputes(disputed_ids, tmp / "adjudication_contact_sheets")
    codebook = """EYEGLASSES MEASUREMENT-REPAIR V1.1: THIRD-RESEARCHER ADJUDICATION

- Review only the anonymous contact sheets and the adjudication CSV.
- Do not access the private mapping or infer identity, experimental role, expected state, or seed.
- Resolve every row independently using the displayed frame, A/B options, and preserved notes.
- Fill adjudicated_value using exactly one value listed in allowed_values.
- Fill a concise non-empty rationale for every row.
- For face_eye_region_observable_yes_no: choose no when the face/eye region is too small, blurred, occluded, distorted, outside frame, or artifactually ambiguous.
- For eyeglasses_label: present = recognizable worn eyeglasses/spectacles/sunglasses; absent = observable eye region with no glasses; U = not reliably decidable.
- Logical constraint after adjudication: observability=no iff label=U.
"""
    (tmp / "eyeglasses_adjudication_codebook_v1_1.txt").write_text(codebook, encoding="utf-8")
    agreement = {
        "schema_version": 1,
        "analysis_id": "formal_measurement_repair_eyeglasses_blind_agreement_v1_1",
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "annotation_items": EXPECTED_ROWS,
        "submitted_sha256": submitted_hashes,
        "label_counts": {a: dict(Counter(maps[a][i]["eyeglasses_label"].strip() for i in ids)) for a in ("A", "B")},
        "observability_counts": {a: dict(Counter(maps[a][i]["face_eye_region_observable_yes_no"].strip() for i in ids)) for a in ("A", "B")},
        "agreement": {
            "face_eye_region_observable_yes_no": {"matches": sum(x == y for x, y in zip(obs_a, obs_b)), "proportion": obs_stats[0], "cohen_kappa": obs_stats[2]},
            "eyeglasses_label": {"matches": sum(x == y for x, y in zip(lab_a, lab_b)), "proportion": label_stats[0], "cohen_kappa": label_stats[2]},
            "annotation_confidence_high_low": {"matches": sum(x == y for x, y in zip(conf_a, conf_b)), "proportion": confidence_stats[0], "cohen_kappa": confidence_stats[2], "requires_adjudication": False},
        },
        "unique_disputed_items": len(disputed_ids),
        "adjudication_rows": len(disagreement_rows),
        "private_mapping_accessed": False,
        "consensus_created": False,
        "status": "COMPUTED_NOT_ADJUDICATED",
    }
    write_json(tmp / "eyeglasses_blind_agreement_v1_1.json", agreement)
    artifacts = []
    for path in sorted(p for p in tmp.rglob("*") if p.is_file()):
        artifacts.append({"relative_path": str(path.relative_to(tmp)), "bytes": path.stat().st_size, "sha256": sha256(path)})
    write_csv(tmp / "adjudication_packet_artifact_hashes_v1_1.csv", ["relative_path", "bytes", "sha256"], artifacts)
    freeze = {
        "schema_version": 1,
        "freeze_id": "formal_measurement_repair_eyeglasses_adjudication_packet_v1_1_freeze",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_packet_freeze_sha256": sha256(packet_freeze),
        "repository_commit": commit,
        "builder_script_sha256": sha256(Path(__file__)),
        "submitted_sha256": submitted_hashes,
        "agreement_sha256": sha256(tmp / "eyeglasses_blind_agreement_v1_1.json"),
        "adjudication_template_sha256": sha256(disagreement_path),
        "artifact_hashes_sha256": sha256(tmp / "adjudication_packet_artifact_hashes_v1_1.csv"),
        "unique_disputed_items": len(disputed_ids),
        "adjudication_rows": len(disagreement_rows),
        "contact_sheet_pages": len(pages),
        "private_mapping_accessed": False,
        "status": "READY_FOR_BLIND_THIRD_RESEARCHER_ADJUDICATION",
    }
    write_json(tmp / "eyeglasses_adjudication_packet_freeze_v1_1.json", freeze)
    tmp.rename(OUT)
    print(json.dumps({
        "status": freeze["status"],
        "annotation_items": EXPECTED_ROWS,
        "unique_disputed_items": len(disputed_ids),
        "adjudication_rows": len(disagreement_rows),
        "contact_sheet_pages": len(pages),
        "private_mapping_accessed": False,
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except AdjudicationError as exc:
        raise SystemExit(f"ADJUDICATION PACKET BUILD FAILED: {exc}")
