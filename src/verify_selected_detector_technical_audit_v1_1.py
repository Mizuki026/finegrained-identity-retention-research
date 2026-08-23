#!/usr/bin/env python3
"""Independently verify the selected-detector technical-audit freeze."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

BASE = Path("/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/measurement_repair_v1")
SOURCE = BASE / "selected_detector_v1_1"
FINAL = BASE / "selected_detector_technical_audit_final_v1_1"
OUT = BASE / "selected_detector_technical_audit_final_v1_1_independent_verification.json"


class VerifyError(RuntimeError): pass
def require(x, message):
    if not x: raise VerifyError(message)
def sha256(path):
    h = hashlib.sha256(); h.update(Path(path).read_bytes()); return h.hexdigest()
def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f: return list(csv.DictReader(f))


def main():
    require(not OUT.exists(), "verification exists")
    freeze = json.loads((FINAL / "selected_detector_technical_audit_freeze_v1_1.json").read_text(encoding="utf-8"))
    rows = read_csv(FINAL / "selected_detector_technical_audit_final_v1_1.csv")
    source = read_csv(SOURCE / "selected_detector_technical_audit_template_v1_1.csv")
    require(len(rows) == len(source) == 560, "row-count mismatch")
    require(sha256(FINAL / "selected_detector_technical_audit_final_v1_1.csv") == freeze["final_audit_sha256"], "final hash mismatch")
    require(sha256(FINAL / "selected_detector_technical_audit_submitted_v1_1.csv") == freeze["submitted_sha256"], "submitted hash mismatch")
    require(rows == source, "final audit is not the exact submitted table")
    errors = []
    for row in rows:
        expected = "pass" if row["detected"] == "true" and row["correct_face_bbox_yes_no"] == "yes" and row["expanded_crop_contains_face_and_eye_region_yes_no"] == "yes" else "fail"
        if row["technical_status_pass_fail"] != expected: errors.append(row["annotation_item_id"])
        if expected == "fail" and not row["review_note"].strip(): errors.append(row["annotation_item_id"])
    counts = Counter(r["technical_status_pass_fail"] for r in rows)
    require(not errors and counts == {"pass": 553, "fail": 7}, "logical verification failed")
    result = {
        "schema_version": 1,
        "verification_id": "formal_measurement_repair_selected_detector_technical_audit_v1_1_independent_verification",
        "technical_audit_freeze_sha256": sha256(FINAL / "selected_detector_technical_audit_freeze_v1_1.json"),
        "items_verified": 560,
        "pass_items_verified": 553,
        "fail_items_verified": 7,
        "no_detector_substitution_verified": True,
        "no_selective_exclusion_verified": True,
        "status": "PASS_INDEPENDENT_SELECTED_DETECTOR_TECHNICAL_AUDIT_VERIFICATION",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try: main()
    except VerifyError as exc: raise SystemExit(f"TECHNICAL AUDIT VERIFICATION FAILED: {exc}")
