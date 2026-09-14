#!/usr/bin/env python3
"""Build the frozen 3,360-item private blinded annotation packet."""
from __future__ import annotations

import csv
import hashlib
import hmac
import json
import os
import secrets
import shutil
import sys
from pathlib import Path

import cv2

import controlled_lfe_private_decode_protocol_v1 as decode

GOVERNANCE = decode.REPO / "governance/mechanism_controlled_intervention_scientific_monolithic_run_002_postdecode_v1"
DECODE_FREEZE = decode.REPO / "governance/mechanism_controlled_intervention_scientific_monolithic_run_002_decode_v1/private_decode_verification_freeze_v1.json"
AUTH = GOVERNANCE / "annotation_packet_execution_authorization_v1.json"
PACKET = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_private_annotation_packets_monolithic/run_002")
MAPPING = Path("/root/autodl-tmp/finegrained/mechanism_controlled_intervention_v1_scientific_private_annotation_mapping_monolithic/run_002")
FRAME_INDICES = (0, 8, 16, 24, 32, 40, 48)
CODEBOOKS = {
    "eyeglasses": (
        Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/measurement_repair_v1/eyeglasses_blind_annotation_v1_1/eyeglasses_annotation_codebook_v1_1.txt"),
        1216, "7e7d2be5bdb39e45134bc222ae73792845ff445392767b6366c2da138046e17e",
    ),
    "facial_hair": (
        Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/attribute_evaluation_v1/run_001/facial_hair_annotation_materials_v1/facial_hair_codebook_v1.txt"),
        418, "75ca640279ac38285c418c7e8bfa21ec8495a94fc9befcd54180cdf26ef3feb1",
    ),
    "facial_hair_adjudication": (
        Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/attribute_evaluation_v1/manual_annotation_v1/adjudication_v1/facial_hair_adjudication_codebook_v1.txt"),
        504, "77d4313c9b2745b7139765ee995742604dcb09f850b2b3a523011a048a8625f9",
    ),
}


class AnnotationPacketError(RuntimeError):
    """Raised when packet construction fails closed."""


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def blind_id(key: bytes, task: str, condition: str, frame: int) -> str:
    message = f"controlled_lfe_annotation_v1|{task}|{condition}|{frame}".encode()
    return "ANN_" + hmac.new(key, message, hashlib.sha256).hexdigest()[:24].upper()


def main() -> int:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise AnnotationPacketError("packet builder must start CUDA-hidden and torch-free")
    authorization = decode.read_json(AUTH)
    if authorization.get("status") != "PRIVATE_BLIND_ANNOTATION_PACKET_CONSTRUCTION_AUTHORIZED":
        raise AnnotationPacketError("annotation packet authorization drift")
    if decode.bound(authorization.get("builder_code", {}), "annotation builder").resolve() != Path(__file__).resolve():
        raise AnnotationPacketError("annotation builder code binding drift")
    if decode.bound(authorization.get("decode_freeze", {}), "decode freeze").resolve() != DECODE_FREEZE.resolve():
        raise AnnotationPacketError("decode freeze binding drift")
    if decode.bound(authorization.get("packet_protocol", {}), "packet protocol").resolve() != (GOVERNANCE / "private_annotation_packet_protocol_v1.json").resolve():
        raise AnnotationPacketError("packet protocol binding drift")
    freeze = decode.read_json(DECODE_FREEZE)
    if freeze.get("status") != "FROZEN_PASS_COMPLETE_INDEPENDENTLY_VERIFIED_PRIVATE_LATENT_DECODE":
        raise AnnotationPacketError("private decode freeze drift")
    for label, (path, size, digest) in CODEBOOKS.items():
        if path.is_symlink() or not path.is_file() or path.stat().st_size != size or decode.sha256(path) != digest:
            raise AnnotationPacketError(f"codebook binding drift: {label}")
    for parent in (PACKET.parent, MAPPING.parent):
        if parent.exists() and (not parent.is_dir() or parent.is_symlink() or parent.stat().st_mode & 0o777 != 0o700):
            raise AnnotationPacketError("private annotation parent mode drift")
        if not parent.exists():
            parent.mkdir(parents=True, mode=0o700)
            os.chmod(parent, 0o700)
    packet_tmp = PACKET.with_name(PACKET.name + ".partial")
    mapping_tmp = MAPPING.with_name(MAPPING.name + ".partial")
    if any(path.exists() for path in (PACKET, packet_tmp, MAPPING, mapping_tmp)):
        raise AnnotationPacketError("annotation packet or mapping output already exists")
    packet_tmp.mkdir(parents=True, mode=0o700)
    mapping_tmp.mkdir(parents=True, mode=0o700)
    frames_dir = packet_tmp / "anonymous_frames"
    frames_dir.mkdir(mode=0o700)
    key = secrets.token_bytes(32)
    key_path = mapping_tmp / "blind_key_v1.bin"
    key_path.write_bytes(key)
    os.chmod(key_path, 0o400)
    mapping_rows: list[dict] = []
    statuses = decode.read_csv(decode.DECODE_RUN / "private_decode_status_v1.csv")
    if len(statuses) != 480:
        raise AnnotationPacketError("private decode status cardinality drift")
    for video_index, row in enumerate(statuses, 1):
        video = Path(str(row["video_path"]))
        capture = cv2.VideoCapture(str(video))
        if not capture.isOpened():
            raise AnnotationPacketError(f"cannot open source video: {video_index}")
        wanted = set(FRAME_INDICES)
        frame_index = 0
        while wanted:
            ok, image = capture.read()
            if not ok:
                break
            if frame_index in wanted:
                aid = blind_id(key, str(row["planned_task_id"]), str(row["condition"]), frame_index)
                image_path = frames_dir / f"{aid}.png"
                if not cv2.imwrite(str(image_path), image, [cv2.IMWRITE_PNG_COMPRESSION, 3]):
                    raise AnnotationPacketError(f"cannot write anonymous frame: {aid}")
                mapping_rows.append({
                    "annotation_item_id": aid,
                    "planned_task_id": row["planned_task_id"],
                    "planned_unit_id": row["planned_unit_id"],
                    "formal_pair_id": row["formal_pair_id"],
                    "attribute": row["attribute"],
                    "role": row["role"],
                    "seed_index": row["seed_index"],
                    "seed": row["seed"],
                    "condition": row["condition"],
                    "frame_index": frame_index,
                    "source_video_path": str(video),
                    "source_video_sha256": row["video_sha256"],
                    "anonymous_frame_path": str(PACKET / "anonymous_frames" / image_path.name),
                    "anonymous_frame_bytes": image_path.stat().st_size,
                    "anonymous_frame_sha256": decode.sha256(image_path),
                })
                wanted.remove(frame_index)
            frame_index += 1
        capture.release()
        if wanted:
            raise AnnotationPacketError(f"sampled frame missing in source video: {video_index}")
    if len(mapping_rows) != 3360 or len({row["annotation_item_id"] for row in mapping_rows}) != 3360:
        raise AnnotationPacketError("annotation item cardinality or blind-ID collision")
    mapping_fields = tuple(mapping_rows[0])
    write_csv(mapping_tmp / "private_annotation_mapping_v1.csv", mapping_fields, mapping_rows)
    template_fields = (
        "annotator_id", "annotation_item_id", "random_order", "rubric",
        "observable_yes_no", "label", "confidence_high_low", "reason_or_note",
    )
    for annotator in ("A", "B"):
        directory = packet_tmp / f"annotator_{annotator}"
        directory.mkdir()
        ordered = sorted(
            mapping_rows,
            key=lambda row: hashlib.sha256(
                f"controlled_lfe_annotation_v1|order|{annotator}|{row['annotation_item_id']}".encode()
            ).hexdigest(),
        )
        template = [{
            "annotator_id": annotator,
            "annotation_item_id": row["annotation_item_id"],
            "random_order": index,
            "rubric": row["attribute"],
            "observable_yes_no": "",
            "label": "",
            "confidence_high_low": "",
            "reason_or_note": "",
        } for index, row in enumerate(ordered, 1)]
        write_csv(directory / f"annotator_{annotator}_template_v1.csv", template_fields, template)
    for label, (source, _size, _digest) in CODEBOOKS.items():
        shutil.copyfile(source, packet_tmp / f"{label}_codebook_v1.txt")
    manifest = {
        "schema_version": 1,
        "status": "READY_FOR_TWO_INDEPENDENT_HUMAN_BLIND_ANNOTATORS",
        "source_videos": 480,
        "sampled_frame_indices": list(FRAME_INDICES),
        "annotation_items": 3360,
        "annotators": 2,
        "private_mapping_accessed_by_annotators": False,
        "condition_pair_role_seed_and_source_path_visible_to_annotators": False,
        "annotation_started": False,
        "unblinding_authorized_but_blocked_until_complete_annotation_and_adjudication": True,
    }
    decode.atomic_json(packet_tmp / "annotation_packet_manifest_v1.json", manifest)
    mapping_tmp.replace(MAPPING)
    packet_tmp.replace(PACKET)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AnnotationPacketError, decode.PrivateDecodeProtocolError, OSError, ValueError, KeyError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
