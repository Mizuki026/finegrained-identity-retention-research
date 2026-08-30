#!/usr/bin/env python3
"""Prespecified CPU-only cosine/outcome linkage analyzer v1.

Dry-run mode reads only the approved plan. Formal mode is implemented but
fail-closed behind a separate execution authorization that is not granted by
the implementation/input-audit authorization.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence


REPO = Path(__file__).resolve().parents[1]
PLAN_STATUS = "APPROVED_FIXED_DESIGN_IMPLEMENTATION_AND_INPUT_AUDIT_ONLY"
EXECUTION_STATUS = "CPU_COSINE_LINKAGE_EXECUTION_APPROVED"
DRY_STATUS = "PASS_NO_WEIGHT_COSINE_LINKAGE_DRY_RUN_NO_REAL_INPUT"
ATTRIBUTES = ("eyeglasses", "facial_hair")
BRANCHES = ("unconditional", "text")
GROUPS = ("early", "middle", "late")
SOURCE_NAMES = ("eyeglasses_outcome", "facial_hair_outcome", "injection_summaries")
FORBIDDEN_MODULE_PREFIXES = ("torch", "transformers", "diffusers", "consisid")
FROZEN_RUNTIME_ROOTS = (
    Path("/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003"),
    Path("/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003_analysis_v1"),
)


class CosineLinkageError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise CosineLinkageError(f"expected JSON object: {path}")
    return value


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise CosineLinkageError(f"refusing to overwrite artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def atomic_csv(path: Path, columns: Sequence[str], rows: Iterable[dict]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise CosineLinkageError(f"refusing to overwrite artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in columns})
    temporary.replace(path)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPO / path).resolve()


def ensure_cpu_only() -> None:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise CosineLinkageError("CUDA_VISIBLE_DEVICES must be explicitly empty")
    loaded = sorted(
        name for name in sys.modules
        if any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_MODULE_PREFIXES)
    )
    if loaded:
        raise CosineLinkageError(f"forbidden ML modules imported: {loaded[:5]}")


def validate_plan(plan: dict) -> dict[str, tuple[str, ...]]:
    if plan.get("status") != PLAN_STATUS:
        raise CosineLinkageError("approved plan status mismatch")
    if tuple(plan.get("attributes", [])) != ATTRIBUTES:
        raise CosineLinkageError("attribute universe drift")
    pairs = {attribute: tuple(plan["planned_pair_ids"][attribute]) for attribute in ATTRIBUTES}
    if any(len(value) != 10 or len(set(value)) != 10 for value in pairs.values()):
        raise CosineLinkageError("pair universe drift")
    if tuple(plan.get("cfg_branches", [])) != BRANCHES:
        raise CosineLinkageError("CFG branch universe drift")
    if tuple(plan.get("block_groups", {})) != GROUPS or tuple(plan.get("denoising_groups", {})) != GROUPS:
        raise CosineLinkageError("3x3 group universe drift")
    metric = plan.get("metric", {})
    if metric.get("source_column") != "mean_tokenwise_cosine_h_r" or metric.get("role") != "secondary_diagnostic" or metric.get("promoted_to_primary") is not False:
        raise CosineLinkageError("cosine metric role drift")
    association = plan.get("association", {})
    if association.get("method") != "spearman_rank_correlation" or association.get("ties") != "average_ranks":
        raise CosineLinkageError("association definition drift")
    if association.get("p_values") or association.get("confidence_intervals") or association.get("reduced_panel_if_missing"):
        raise CosineLinkageError("forbidden inference or reduced panel")
    if plan.get("expected_counts", {}).get("associations") != 36:
        raise CosineLinkageError("planned association count drift")
    return pairs


def no_weight_dry_run(plan_path: Path, output_path: Path) -> dict:
    ensure_cpu_only()
    plan = read_json(plan_path)
    validate_plan(plan)
    result = {
        "schema_version": 1,
        "status": DRY_STATUS,
        "analysis_plan_path": str(plan_path.resolve()),
        "analysis_plan_bytes": plan_path.stat().st_size,
        "analysis_plan_sha256": sha256(plan_path),
        "metric": "mean_tokenwise_cosine_h_r",
        "metric_role": "secondary_diagnostic",
        "planned_attributes": 2,
        "planned_pairs_per_attribute": 10,
        "planned_task_cell_rows": 2880,
        "planned_pair_cell_rows": 360,
        "planned_joined_rows": 360,
        "planned_associations": 36,
        "real_input_paths_received": False,
        "input_files_opened": False,
        "cosine_aggregated": False,
        "outcome_constructed": False,
        "joined_rows_created": 0,
        "association_computed": False,
        "model_modules_imported": False,
        "model_weights_loaded": False,
        "gpu_used": False,
        "network_used": False,
        "execution_authorized": False,
    }
    atomic_json(output_path, result)
    return result


def average_ranks(values: Sequence[float]) -> list[float]:
    if not values or any(not math.isfinite(value) for value in values):
        raise CosineLinkageError("ranking requires finite values")
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = ((start + 1) + end) / 2.0
        for position in range(start, end):
            ranks[order[position]] = rank
        start = end
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) != len(y) or not x:
        raise CosineLinkageError("Spearman vectors must have equal nonzero length")
    rx, ry = average_ranks(x), average_ranks(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    cx, cy = [value - mx for value in rx], [value - my for value in ry]
    denominator = math.sqrt(sum(value * value for value in cx) * sum(value * value for value in cy))
    return None if denominator == 0.0 else sum(a * b for a, b in zip(cx, cy)) / denominator


def finite(row: dict[str, str], column: str, context: str) -> float:
    try:
        value = float(row[column])
    except (KeyError, TypeError, ValueError) as error:
        raise CosineLinkageError(f"invalid {column} at {context}") from error
    if not math.isfinite(value):
        raise CosineLinkageError(f"non-finite {column} at {context}")
    return value


def block_group(site: int) -> str:
    if site <= 6:
        return "early"
    if site <= 13:
        return "middle"
    return "late"


def denoising_group(step: int) -> str:
    if step <= 16:
        return "early"
    if step <= 33:
        return "middle"
    return "late"


def verify_bound_file(path: Path, binding: dict, label: str) -> None:
    if path != resolve(binding["path"]):
        raise CosineLinkageError(f"path mismatch for {label}")
    if not path.is_file() or path.is_symlink():
        raise CosineLinkageError(f"invalid source file for {label}")
    if path.stat().st_size != int(binding["bytes"]) or sha256(path) != binding["sha256"]:
        raise CosineLinkageError(f"byte or SHA256 mismatch for {label}")


def read_bound_csv(binding: dict, label: str) -> list[dict[str, str]]:
    path = resolve(binding["path"])
    verify_bound_file(path, binding, label)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != binding.get("header"):
            raise CosineLinkageError(f"header mismatch for {label}")
        return list(reader)


def construct_outcomes(eye_rows: list[dict[str, str]], hair_rows: list[dict[str, str]], pairs: dict[str, tuple[str, ...]]) -> dict[tuple[str, str], float]:
    eye: dict[str, dict[int, float]] = defaultdict(dict)
    for row in eye_rows:
        pair = row["formal_pair_id"]
        seed = int(row["seed_index"])
        if pair not in pairs["eyeglasses"] or seed not in (1, 2, 3, 4) or seed in eye[pair]:
            raise CosineLinkageError("eyeglasses outcome key drift")
        eye[pair][seed] = finite(row, "human_positive_minus_control", f"eye/{pair}/{seed}")
    outcomes = {}
    for pair in pairs["eyeglasses"]:
        if set(eye[pair]) != {1, 2, 3, 4}:
            raise CosineLinkageError("incomplete eyeglasses seed set")
        outcomes[("eyeglasses", pair)] = statistics.fmean(eye[pair].values())
    hair = {}
    for row in hair_rows:
        if row.get("attribute") != "facial_hair":
            continue
        pair = row["formal_pair_id"]
        if pair not in pairs["facial_hair"] or pair in hair:
            raise CosineLinkageError("facial-hair outcome key drift")
        hair[pair] = finite(row, "primary_positive_minus_control", f"hair/{pair}")
    if set(hair) != set(pairs["facial_hair"]):
        raise CosineLinkageError("incomplete facial-hair outcome panel")
    outcomes.update({("facial_hair", pair): value for pair, value in hair.items()})
    return outcomes


def aggregate_cosine(rows: list[dict[str, str]], pairs: dict[str, tuple[str, ...]]) -> tuple[list[dict], list[dict]]:
    sums, counts, metadata = defaultdict(float), defaultdict(int), {}
    seen = set()
    for row in rows:
        task = row["trace_task_id"]
        position = (task, row["step_index"], row["site_index"], row["cfg_branch"])
        if position in seen:
            raise CosineLinkageError("duplicate injection position")
        seen.add(position)
        step, site = int(row["step_index"]), int(row["site_index"])
        branch = row["cfg_branch"]
        if step not in range(50) or site not in range(21) or branch not in BRANCHES:
            raise CosineLinkageError("injection position domain drift")
        attribute, pair, role, seed_index = row["attribute"], row["formal_pair_id"], row["role"], int(row["seed_index"])
        if attribute not in ATTRIBUTES or pair not in pairs[attribute] or role not in ("positive", "control") or seed_index not in (1, 2, 3, 4):
            raise CosineLinkageError("task metadata drift")
        meta = (attribute, pair, role, seed_index, row["formal_unit_id"], row["seed"])
        if task in metadata and metadata[task] != meta:
            raise CosineLinkageError("metadata changes within task")
        metadata[task] = meta
        key = (task, branch, block_group(site), denoising_group(step))
        sums[key] += finite(row, "mean_tokenwise_cosine_h_r", task)
        counts[key] += 1
    expected_positions = {("early", "early"):119, ("early", "middle"):119, ("early", "late"):112,
                          ("middle", "early"):119, ("middle", "middle"):119, ("middle", "late"):112,
                          ("late", "early"):119, ("late", "middle"):119, ("late", "late"):112}
    if len(metadata) != 160 or len(sums) != 2880:
        raise CosineLinkageError("task or task-cell count mismatch")
    task_rows = []
    for key in sorted(sums):
        task, branch, block, denoise = key
        if counts[key] != expected_positions[(block, denoise)]:
            raise CosineLinkageError("task-cell position count mismatch")
        attribute, pair, role, seed_index, unit, seed = metadata[task]
        task_rows.append({"trace_task_id":task,"formal_unit_id":unit,"formal_pair_id":pair,"attribute":attribute,"role":role,"seed_index":seed_index,"seed":seed,"cfg_branch":branch,"block_group":block,"denoising_group":denoise,"mean_tokenwise_cosine_h_r_mean":sums[key]/counts[key],"positions":counts[key]})
    unit_values = defaultdict(list)
    for row in task_rows:
        key = (row["formal_unit_id"], row["cfg_branch"], row["block_group"], row["denoising_group"])
        unit_values[key].append(float(row["mean_tokenwise_cosine_h_r_mean"]))
    if any(len(values) != 4 for values in unit_values.values()):
        raise CosineLinkageError("four-seed unit-cell count mismatch")
    unit_means = {key: statistics.fmean(values) for key, values in unit_values.items()}
    unit_by_role = defaultdict(dict)
    for task, (attribute, pair, role, _seed_index, unit, _seed) in metadata.items():
        unit_by_role[(attribute, pair)][role] = unit
    if len(unit_by_role) != 20 or any(set(roles) != {"positive", "control"} for roles in unit_by_role.values()):
        raise CosineLinkageError("matched-pair role universe drift")
    pair_rows = []
    for (attribute, pair), roles in sorted(unit_by_role.items()):
        for branch in BRANCHES:
            for block in GROUPS:
                for denoise in GROUPS:
                    positive = unit_means[(roles["positive"],branch,block,denoise)]
                    control = unit_means[(roles["control"],branch,block,denoise)]
                    pair_rows.append({"attribute":attribute,"formal_pair_id":pair,"cfg_branch":branch,"block_group":block,"denoising_group":denoise,"positive_four_seed_mean":positive,"control_four_seed_mean":control,"positive_minus_control":positive-control})
    if len(pair_rows) != 360:
        raise CosineLinkageError("pair-cell row count mismatch")
    return task_rows, pair_rows


def join_and_associate(pair_rows: list[dict], outcomes: dict[tuple[str, str], float]) -> tuple[list[dict], list[dict]]:
    joined, grouped = [], defaultdict(list)
    for row in pair_rows:
        key = (row["attribute"], row["formal_pair_id"])
        if key not in outcomes:
            raise CosineLinkageError("missing outcome during join")
        item = {**row, "retention_outcome": outcomes[key]}
        joined.append(item)
        grouped[(row["attribute"],row["cfg_branch"],row["block_group"],row["denoising_group"])].append(item)
    if len(joined) != 360 or len(grouped) != 36:
        raise CosineLinkageError("joined family count mismatch")
    associations = []
    for (attribute, branch, block, denoise), values in sorted(grouped.items()):
        if len(values) != 10:
            raise CosineLinkageError("association panel is not ten pairs")
        rho = spearman([float(row["positive_minus_control"]) for row in values], [float(row["retention_outcome"]) for row in values])
        associations.append({"attribute":attribute,"cfg_branch":branch,"block_group":block,"denoising_group":denoise,"pairs":10,"spearman_rho":"" if rho is None else rho,"defined":rho is not None,"role":"secondary_complete_family"})
    return joined, associations


def validate_execution_authorization(path: Path, plan_path: Path, output_dir: Path) -> dict:
    ensure_cpu_only()
    authorization = read_json(path)
    if authorization.get("status") != EXECUTION_STATUS:
        raise CosineLinkageError("formal cosine linkage execution is not authorized")
    authority = authorization.get("authority", {})
    for flag in ("real_cosine_aggregation", "outcome_construction", "outcome_join", "association_computation", "independent_verification"):
        if authority.get(flag) is not True:
            raise CosineLinkageError(f"missing execution authority: {flag}")
    if any(authority.get(flag) for flag in ("model_loading", "gpu_execution", "network")):
        raise CosineLinkageError("authorization permits forbidden capability")
    verify_bound_file(plan_path.resolve(), authorization["analysis_plan"], "analysis plan")
    verify_bound_file(Path(__file__).resolve(), authorization["code"]["analyzer"], "analyzer")
    authorized_output = resolve(authorization["output_dir"])
    if output_dir.resolve() != authorized_output or output_dir.exists():
        raise CosineLinkageError("output mismatch or overwrite attempt")
    if REPO == authorized_output or REPO in authorized_output.parents:
        raise CosineLinkageError("formal joined outputs must remain external to Git")
    if any(root == authorized_output or root in authorized_output.parents for root in FROZEN_RUNTIME_ROOTS):
        raise CosineLinkageError("output cannot be inside frozen Phase-S trees")
    if set(authorization.get("sources", {})) != set(SOURCE_NAMES):
        raise CosineLinkageError("source universe mismatch")
    return authorization


def run_formal(authorization_path: Path, plan_path: Path, output_dir: Path) -> dict:
    authorization = validate_execution_authorization(authorization_path, plan_path, output_dir)
    plan = read_json(plan_path)
    pairs = validate_plan(plan)
    sources = {name: read_bound_csv(authorization["sources"][name], name) for name in SOURCE_NAMES}
    outcomes = construct_outcomes(sources["eyeglasses_outcome"], sources["facial_hair_outcome"], pairs)
    task_rows, pair_rows = aggregate_cosine(sources["injection_summaries"], pairs)
    joined, associations = join_and_associate(pair_rows, outcomes)
    output_dir.mkdir(parents=True, exist_ok=False)
    atomic_csv(output_dir/"cosine_task_3x3_v1.csv", tuple(task_rows[0]), task_rows)
    atomic_csv(output_dir/"cosine_pair_3x3_v1.csv", tuple(pair_rows[0]), pair_rows)
    atomic_csv(output_dir/"cosine_outcome_joined_pairs_v1.csv", tuple(joined[0]), joined)
    atomic_csv(output_dir/"cosine_outcome_associations_v1.csv", tuple(associations[0]), associations)
    summary = {"schema_version":1,"status":"COMPLETE_COSINE_LINKAGE_PENDING_INDEPENDENT_VERIFICATION","metric_role":"secondary_diagnostic","task_cell_rows":len(task_rows),"pair_cell_rows":len(pair_rows),"joined_pair_rows":len(joined),"associations":len(associations),"p_values":False,"confidence_intervals":False,"gpu_used":False,"model_loaded":False}
    atomic_json(output_dir/"analysis_summary_v1.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "formal"), required=True)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--dry-run-output", type=Path)
    parser.add_argument("--execution-authorization", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.mode == "dry-run":
        if not args.dry_run_output or args.execution_authorization or args.output_dir:
            raise CosineLinkageError("dry-run accepts only plan and dry-run output")
        result = no_weight_dry_run(args.plan, args.dry_run_output)
    else:
        if not args.execution_authorization or not args.output_dir or args.dry_run_output:
            raise CosineLinkageError("formal mode requires authorization and output directory")
        result = run_formal(args.execution_authorization, args.plan, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CosineLinkageError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
