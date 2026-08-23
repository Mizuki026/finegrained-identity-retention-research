#!/usr/bin/env python3
"""Pure-stdlib protocol utilities for prospective ConsisID mechanism trace v1."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[1]
DESIGN = REPO / "governance" / "mechanism_trace_design_v1"
DESIGN_FREEZE = DESIGN / "mechanism_trace_design_freeze_v1.json"
ANALYSIS_PLAN = DESIGN / "mechanism_trace_analysis_plan_v1.json"
ENGINEERING_SUBSET = DESIGN / "engineering_subset_v1.csv"
FORMAL_MASTER = Path(
    "/root/autodl-tmp/finegrained/formal_experiment_v1_runtime/"
    "experiment_freeze_v1/pre_generation_master_freeze_v1.json"
)
EXPECTED_FORMAL_MASTER_SHA256 = (
    "149e5deba4d14b4591186416dbe4e12efb3ed19437c0cca0642eaff8a6d5eed8"
)
EXPECTED_CONSISID_COMMIT = "60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e"
FORMAL_SEEDS = (2686238281, 280026145, 2169901996, 2046930553)
DRY_RUN_COLUMNS = (
    "trace_task_id",
    "phase",
    "source_task_id",
    "formal_unit_id",
    "formal_pair_id",
    "attribute",
    "role",
    "seed_index",
    "seed",
    "condition",
    "repetition",
)


class ProtocolError(RuntimeError):
    """Fail-closed protocol validation error."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_sha256(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def verify_file(path: Path, expected_bytes: int, expected_sha256: str) -> None:
    if not path.is_file():
        raise ProtocolError(f"required file missing: {path}")
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise ProtocolError(
            f"byte-size drift for {path}: expected={expected_bytes} actual={actual_bytes}"
        )
    actual_hash = sha256(path)
    if actual_hash != expected_sha256:
        raise ProtocolError(
            f"SHA256 drift for {path}: expected={expected_sha256} actual={actual_hash}"
        )


def validate_design_freeze() -> dict:
    freeze = read_json(DESIGN_FREEZE)
    if freeze.get("status") != "DESIGN_COMPLETE_IMPLEMENTATION_REVIEW_REQUIRED":
        raise ProtocolError("mechanism trace design freeze is not at the expected review state")
    for name, expected in freeze["artifacts"].items():
        verify_file(DESIGN / name, int(expected["bytes"]), expected["sha256"])
    if freeze.get("consisid_commit") != EXPECTED_CONSISID_COMMIT:
        raise ProtocolError("design freeze ConsisID commit drift")
    return freeze


def validate_formal_master() -> tuple[dict, list[dict[str, str]]]:
    if sha256(FORMAL_MASTER) != EXPECTED_FORMAL_MASTER_SHA256:
        raise ProtocolError("formal master freeze SHA256 drift")
    master = read_json(FORMAL_MASTER)
    if master["consisid"]["commit"] != EXPECTED_CONSISID_COMMIT:
        raise ProtocolError("formal master ConsisID commit drift")
    generation = master["generation"]
    required_generation = {
        "num_frames": 49,
        "num_inference_steps": 50,
        "guidance_scale": 6.0,
        "dtype": "bfloat16",
    }
    for key, expected in required_generation.items():
        if generation.get(key) != expected:
            raise ProtocolError(
                f"formal generation setting drift ({key}): {generation.get(key)!r}"
            )
    manifest_item = master["artifacts"]["generation_manifest"]
    manifest_path = Path(manifest_item["path"])
    verify_file(
        manifest_path,
        int(manifest_item["size_bytes"]),
        manifest_item["sha256"],
    )
    rows = read_csv(manifest_path)
    validate_formal_rows(rows)
    return master, rows


def validate_formal_rows(rows: list[dict[str, str]]) -> None:
    if len(rows) != 160:
        raise ProtocolError(f"expected 160 formal tasks, found {len(rows)}")
    if len({row["task_id"] for row in rows}) != 160:
        raise ProtocolError("formal task IDs are not unique")
    units: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        units[row["formal_unit_id"]].append(row)
    if len(units) != 40:
        raise ProtocolError(f"expected 40 formal units, found {len(units)}")
    for unit_id, unit_rows in units.items():
        seeds = tuple(int(row["seed"]) for row in sorted(unit_rows, key=lambda x: int(x["seed_index"])))
        if seeds != FORMAL_SEEDS:
            raise ProtocolError(f"seed crossing drift for {unit_id}: {seeds}")
    attribute_counts = Counter(row["attribute"] for row in rows)
    if attribute_counts != Counter({"eyeglasses": 80, "facial_hair": 80}):
        raise ProtocolError(f"formal attribute counts drift: {attribute_counts}")
    for row in rows:
        if row["role"] not in {"positive", "control"}:
            raise ProtocolError(f"unexpected role in {row['task_id']}: {row['role']}")


def engineering_plan() -> list[dict[str, str]]:
    rows = read_csv(ENGINEERING_SUBSET)
    if len(rows) != 8:
        raise ProtocolError(f"expected 8 engineering units, found {len(rows)}")
    result: list[dict[str, str]] = []
    for row in rows:
        if (row["seed_index"], row["seed"], row["purpose"]) != (
            "1",
            "2686238281",
            "engineering_only",
        ):
            raise ProtocolError(f"engineering subset row drift: {row['formal_unit_id']}")
        for condition, repetition in (
            ("baseline", "1"),
            ("baseline", "2"),
            ("zero_local_residual", "1"),
        ):
            result.append(
                {
                    "trace_task_id": (
                        f"E__{row['formal_unit_id']}__s1__{condition}__r{repetition}"
                    ),
                    "phase": "engineering",
                    "source_task_id": f"{row['formal_unit_id']}__s1",
                    "formal_unit_id": row["formal_unit_id"],
                    "formal_pair_id": row["formal_pair_id"],
                    "attribute": row["attribute"],
                    "role": row["role"],
                    "seed_index": row["seed_index"],
                    "seed": row["seed"],
                    "condition": condition,
                    "repetition": repetition,
                }
            )
    if len(result) != 24 or len({row["trace_task_id"] for row in result}) != 24:
        raise ProtocolError("engineering plan is not exactly 24 unique trajectories")
    return sorted(result, key=lambda row: row["trace_task_id"])


def scientific_plan(formal_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    result = [
        {
            "trace_task_id": f"S__{row['task_id']}__baseline__r1",
            "phase": "scientific",
            "source_task_id": row["task_id"],
            "formal_unit_id": row["formal_unit_id"],
            "formal_pair_id": row["formal_pair_id"],
            "attribute": row["attribute"],
            "role": row["role"],
            "seed_index": row["seed_index"],
            "seed": row["seed"],
            "condition": "baseline",
            "repetition": "1",
        }
        for row in formal_rows
    ]
    if len(result) != 160 or len({row["trace_task_id"] for row in result}) != 160:
        raise ProtocolError("scientific plan is not exactly 160 unique trajectories")
    return sorted(result, key=lambda row: row["source_task_id"])


def build_plan(phase: str) -> tuple[dict, list[dict[str, str]]]:
    validate_design_freeze()
    master, formal_rows = validate_formal_master()
    if phase == "engineering":
        rows = engineering_plan()
    elif phase == "scientific":
        rows = scientific_plan(formal_rows)
    elif phase == "all":
        rows = engineering_plan() + scientific_plan(formal_rows)
    else:
        raise ProtocolError(f"unsupported phase: {phase}")
    summary = summarize_plan(phase, rows, master)
    return summary, rows


def summarize_plan(phase: str, rows: list[dict[str, str]], master: dict) -> dict:
    counts = Counter((row["phase"], row["attribute"], row["condition"]) for row in rows)
    normalized_counts = {
        "|".join(key): value for key, value in sorted(counts.items())
    }
    public_rows = [{key: row[key] for key in DRY_RUN_COLUMNS} for row in rows]
    return {
        "schema_version": 1,
        "status": "DRY_RUN_NO_MODEL_IMPORT_NO_WEIGHT_LOAD",
        "phase": phase,
        "task_count": len(rows),
        "transformer_steps": len(rows) * 50,
        "scheduler_positions_per_task": 50,
        "local_injection_sites": 21,
        "counts": normalized_counts,
        "task_manifest_canonical_sha256": canonical_json_sha256(public_rows),
        "formal_master_sha256": EXPECTED_FORMAL_MASTER_SHA256,
        "formal_generation_manifest_sha256": master["artifacts"]["generation_manifest"]["sha256"],
        "design_freeze_sha256": sha256(DESIGN_FREEZE),
        "torch_imported": "torch" in __import__("sys").modules,
        "consisid_modules_imported": any(
            name.startswith("models.") or "pipeline_consisid" in name
            for name in __import__("sys").modules
        ),
    }


def atomic_write_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise ProtocolError(f"refusing to overwrite artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def atomic_write_csv(path: Path, rows: Iterable[dict[str, str]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise ProtocolError(f"refusing to overwrite artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DRY_RUN_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in DRY_RUN_COLUMNS})
    temporary.replace(path)


def git_value(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def validate_execution_authorization(path: Path, phase: str, code_paths: list[Path]) -> dict:
    """Validate a future execution authorization before any ML import occurs."""
    if not path.is_file():
        raise ProtocolError(f"execution authorization missing: {path}")
    auth = read_json(path)
    if auth.get("status") != "AUTHORIZED_FOR_MECHANISM_TRACE_EXECUTION":
        raise ProtocolError("execution authorization status is not open")
    if auth.get("phase") != phase:
        raise ProtocolError("execution authorization phase mismatch")
    if auth.get("consisid_commit") != EXPECTED_CONSISID_COMMIT:
        raise ProtocolError("execution authorization ConsisID commit mismatch")
    research_head = git_value(REPO, "rev-parse", "HEAD")
    if auth.get("research_commit") != research_head:
        raise ProtocolError("execution authorization research commit mismatch")
    if git_value(REPO, "status", "--short"):
        raise ProtocolError("research repository must be clean for execution")
    consisid_repository = auth.get("consisid_repository")
    if not isinstance(consisid_repository, str) or not consisid_repository:
        raise ProtocolError("execution authorization ConsisID repository missing")
    consisid_repo = Path(consisid_repository)
    if git_value(consisid_repo, "rev-parse", "HEAD") != EXPECTED_CONSISID_COMMIT:
        raise ProtocolError("ConsisID repository commit drift")
    if git_value(consisid_repo, "status", "--short"):
        raise ProtocolError("ConsisID repository must be clean for execution")
    expected_code = auth.get("code_sha256", {})
    for code_path in code_paths:
        if expected_code.get(code_path.name) != sha256(code_path):
            raise ProtocolError(f"authorized code hash mismatch: {code_path.name}")
    if auth.get("gpu_execution_explicitly_approved") is not True:
        raise ProtocolError("GPU execution is not explicitly approved")
    expected_trajectories = 24 if phase == "engineering" else 160
    if auth.get("trajectory_ceiling") != expected_trajectories:
        raise ProtocolError("execution authorization trajectory ceiling mismatch")
    if auth.get("transformer_step_ceiling") != expected_trajectories * 50:
        raise ProtocolError("execution authorization transformer-step ceiling mismatch")
    try:
        gpu_hours = float(auth.get("phase_gpu_hours_ceiling"))
    except (TypeError, ValueError):
        raise ProtocolError("execution authorization has no numeric GPU-hour ceiling")
    if not 0.0 < gpu_hours <= 72.0:
        raise ProtocolError("phase GPU-hour ceiling must be within (0, 72]")
    if phase == "scientific":
        engineering = auth.get("engineering_verification", {})
        engineering_path = Path(engineering.get("path", ""))
        if not engineering_path.is_file():
            raise ProtocolError("scientific execution requires an engineering verification artifact")
        if engineering.get("sha256") != sha256(engineering_path):
            raise ProtocolError("engineering verification artifact hash mismatch")
        engineering_result = read_json(engineering_path)
        if engineering_result.get("phase") != "engineering" or engineering_result.get("status") != "PASS_INDEPENDENT_MECHANISM_TRACE_VERIFICATION":
            raise ProtocolError("engineering execution did not pass independent verification")
        if (engineering_result.get("engineering_control") or {}).get("status") != "PASS_ENGINEERING_REPEAT_AND_ZERO_ROUTE_CONTROLS":
            raise ProtocolError("engineering repeat/zero-route controls did not pass")
    return auth
