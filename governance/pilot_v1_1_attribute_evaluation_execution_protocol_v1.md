# Pilot v1.1 Attribute Evaluation Execution Protocol v1

Status: prospective and frozen before attribute-result inspection.

## Purpose and scope

This protocol defines a descriptive, output-level evaluation of the twelve intact Pilot v1.1 videos. It may measure frame observability and the three already-frozen attribute instruments. It cannot establish a general model property, a causal mechanism, a cross-attribute ranking, or H1-H4 as findings.

The protocol does not authorize execution. Execution additionally requires a recorded pixel-read scope, model-loading scope, and, for facial hair, an annotation gate with blinded materials.

## Authoritative inputs

| Input | SHA256 | Required use |
|---|---|---|
| manifest_v1_1 | dcf66f0222986403493a7c9a09d310629909d4aef590634348b41ce12544f79d | Exact 12-sample universe and expected labels |
| config_v1_1 | 40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47 | Generation provenance only |
| video_evaluation_protocol_v1 | 0a096f8e74af5fad769955ce331658bd9ef8373ba526279e96aba778c07a3964 | Status hierarchy, reason codes, temporal summaries |
| eyeglasses_metric_spec_v2 | e0b3a6b480f51b49d503afee7eecc47a334f4d196592540426499deae06eeace | Frozen CLIP prompts, crop, and margin rule |
| facial_hair_manual_protocol_v2 | 307f2afb4eb92280359960b70eff81cc188d26a60876db896e451f84cc6f25aa | Blinded ordinal annotation rubric |
| hair_color_metric_spec_v1 | f470674cc4c4e9092619001567db0f874e6a58488c4697d543642fe8366cbe11 | Frozen parsing, ROI, continuous L-star |
| video_integrity_audit_v1 | a762dcf9d3b85334d557fbdb223594689d926b7f4e8e703f3432f17911c118d5 | Eligibility gate: exactly 12 PASS videos |

Any hash, schema, set, status, or one-to-one path mismatch is a hard preflight failure. The run must not continue by excluding or repairing a sample.

## Fixed sample and frame universe

- Evaluate every one of the 12 manifest sample IDs; no replacement, exclusion, or regeneration is allowed.
- For every integrity-PASS video, attempt all original frame indices 0 through 48 in increasing order. There is no temporal subsampling.
- A frame remains one correlated within-video observation. The video, not the frame, is the Pilot descriptive unit.
- Attribute-specific observability is separate: one frame may be valid for hair color and unobservable for eyeglasses or facial hair.

## Status and missing-value rules

Use exactly VALID_OBSERVABLE, UNOBSERVABLE, and PIPELINE_FAILURE with the reason-code vocabulary from the frozen video evaluation protocol.

- Scores and labels exist only for VALID_OBSERVABLE frames.
- UNOBSERVABLE and PIPELINE_FAILURE receive empty CSV fields / JSON null; never zero, absent, negative, or an imputed value.
- Each non-valid row has one primary reason code and optional semicolon-separated secondary reason codes.
- A newly observed video technical problem preserves evidence and marks the video as execution failure rather than silently continuing.

## Attribute-specific execution rules

### Eyeglasses

Use only the local frozen CLIP ViT-B/32 model, frozen four-prompt class banks, InsightFace largest-face crop, two-class softmax, and margin rule in metric spec v2. Do not tune prompts, crop geometry, prototypes, or the zero-margin decision rule on generated frames. A frame without a sufficiently judgeable intended eye/bridge region is unobservable, not no-eyeglasses.

### Facial hair

Use the frozen manual ordinal protocol. Create anonymous item IDs and reproducible random order before annotation; hide expected label, prompt, seed, output-directory name, and reference-to-video pairing. Preserve raw labels from every annotator. Labels 0, 1, 2, and U must remain available in the raw table; only the frozen binary mapping may be used for descriptive expected-label-match summaries. A single annotator is exploratory and cannot support inter-rater reliability claims.

### Hair color

Use only BiSeNet class 17, frozen crop/ROI, 7x7 erosion, and required 1000 core-mask pixels at 512x512. Report continuous reference-relative CIELAB L-star summaries; do not create a light/dark video classification threshold. Insufficient masks or scientifically uninterpretable illumination are missing with a protocol reason code.

## Fixed outputs

Every execution must create a new run root, never overwrite an earlier run, and include:

1. attribute_frame_inventory_v1.csv: one row per sample x frame x attribute (12 x 49 x 3 = 1764 planned rows).
2. attribute_video_summary_v1.csv: one row per sample x applicable attribute (12 planned rows).
3. attribute_execution_audit_v1.json: preflight, counts, status, reasons, versions, environment, and boundaries.
4. Raw facial-hair annotations, blinded-item mapping, randomization seed/algorithm, and agreement records in separate immutable files.
5. Append-only run log, environment snapshot, checksum manifest, README, and independent verifier result.

The CSV schemas are fixed in schemas/pilot_attribute_evaluation_output_schema_v1.json. Scripts must reject additional/missing columns.

## Preflight and stop conditions

Before reading a video frame or loading a model, validate: authorization transitions; all authoritative hashes; 12 unique PASS videos; expected MP4 paths/hashes; schema; clean code repository; upstream cleanliness; local model directories/checksums if authorized; output non-existence; disk space; CPU/GPU/network settings; and a new append-only log.

Stop without output PASS for missing input, drift, model or decoder exception, unexpected face-selection ambiguity, invalid annotation record, output schema mismatch, or an unapproved resource request. Preserve the failed run directory and request a new decision; do not retry in place.

## Descriptive summaries and boundary

For each sample and applicable attribute, report valid/unobservable/pipeline-failure counts and fractions. Compute metric summaries only over valid frames. Adjacent flips use only consecutive original indices with two valid observations; do not bridge missing frames. Low coverage is flagged at valid fraction below 0.50 and remains reported rather than excluded.

The Pilot may be described as a fixed, confounded, exploratory output-level case study. It cannot provide confirmatory p-values, independent-frame inference, general metric validation, causal localization, or an unconditional cross-attribute robustness claim.
