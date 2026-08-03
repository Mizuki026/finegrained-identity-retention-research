# Execution Safety Policy v1

- Policy ID: `finegrained_execution_safety_v1`
- Status: active governance baseline
- Effective date: 2026-08-03 UTC
- Default posture: read-only and fail-closed

## Authorized boundary at policy creation

The current authorization covers governance files and reproducibility infrastructure only. It does not authorize video decoding, pixel reads, an integrity-audit run, attribute metrics, model loading, GPU access, video generation, formal experiments, probes, interventions, dependency installation, or network access.

The next scientific execution, if separately authorized, is limited to the CPU-only Pilot v1.1 video integrity audit governed by `video_integrity_audit_protocol_v1.md`.

## Protected locations

The following are immutable inputs:

- `/root/autodl-tmp/finegrained/experiments/pilot_v1_1`
- frozen metric/protocol artifacts under `/root/autodl-tmp/finegrained/experiments/pilot_v1`
- `/root/autodl-tmp/finegrained/datasets`
- `/root/autodl-tmp/finegrained/ckpts`
- `/root/autodl-tmp/finegrained/code/ConsisID`
- `/root/autodl-tmp/envs/consisid-pilot`

No process may edit, rename, move, delete, truncate, normalize, transcode, repair, or overwrite anything in these locations. The upstream baseline repository must remain clean.

## Research repository boundary

- Research governance and future scripts belong only in `/root/autodl-tmp/finegrained/research_pipeline`.
- Never copy or commit weights, datasets, references, MP4 files, or large generated artifacts.
- External inputs are referenced by absolute path and SHA256, not vendored.
- New derived artifacts use a new versioned directory and are registered with parent lineage.
- Existing targets cause immediate failure. No `--force`, overwrite mode, in-place edit, or implicit resume is permitted.

## Compute and dependency controls

- Governance work is CPU-only and must not initialize CUDA or query/load a GPU runtime.
- Future integrity-audit execution must explicitly disable GPU visibility and must not import model code or load weights.
- Network access and dependency installation are prohibited without researcher approval.
- Missing or conflicting decoder dependencies cause a stopped preflight; they are not repaired automatically.
- Large or formal compute requires a separately frozen compute budget and stopping rule.

## Mandatory preflight for every script

Before processing data, a script must validate and log:

1. authorized task and protocol ID/version/hash;
2. current research-pipeline Git commit and clean/dirty status;
3. exact input paths, canonical resolved paths, byte sizes, SHA256 values, and schemas;
4. sample count, unique IDs, one-to-one mappings, and absence of unexpected inputs;
5. environment and dependency versions;
6. CPU/GPU/network policy compliance;
7. output root containment and non-existence of every final output;
8. available disk space and a bounded estimate of writes;
9. append-only log initialization;
10. a validation plan for every declared output.

Any mismatch or uncertainty stops execution before data processing.

## Safe path and write rules

- Resolve canonical paths and reject symlink inputs/outputs where identity matters.
- Never use unresolved globs, broad recursive deletion, workspace-root deletion, or destructive Git commands.
- Use a new run-specific temporary directory inside the authorized derived-output root.
- Finalize outputs atomically only after schema validation; retain failed-run logs and do not publish partial files as PASS.
- Do not delete a failed run. A retry requires a new run/version identifier and explicit lineage.
- Never mutate source timestamps or metadata intentionally.

## Scientific controls

- Do not inspect results before mappings, thresholds, reason codes, schemas, and decision rules are frozen.
- Do not change thresholds, labels, metrics, samples, exclusions, primary analyses, or statistical plans after results are visible.
- Do not transform missing, unobservable, or pipeline failure into attribute absence or zero.
- Do not selectively regenerate or exclude undesirable results.
- Do not treat correlated frames as independent samples.
- Preserve raw machine-readable outputs alongside summaries.
- Distinguish fact, diagnostic, inference, hypothesis, and research decision in every report.

## Human-gated operations

Stop and request approval before:

- GPU access or any model loading;
- regeneration or selective reruns;
- formal output experiments or increased compute budget;
- probing, intervention, ablation, or method modification;
- modifying any frozen input, reference, metric, protocol, or annotation definition;
- installing/upgrading dependencies or using the network;
- deleting, overwriting, moving, renaming, or repairing an existing artifact;
- changing thresholds, exclusion rules, sample design, statistical plan, primary endpoint, or main conclusions;
- advancing after a failed integrity gate.

Approval for one operation does not imply approval for later phases.

## Completion report requirements

Every authorized run must report:

- created files and their SHA256 values;
- unchanged protected inputs verified by hashes where relevant;
- producing Git commit and script/protocol hashes;
- environment and timestamps;
- PASS/FAIL counts with reason codes;
- whether GPU, network, models, video generation, or frozen artifacts were touched;
- the next human gate.
