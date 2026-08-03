# Pilot v1.1 Video Integrity Audit Protocol v1

- Protocol ID: `pilot_v1_1_video_integrity_audit_v1`
- Status: **FROZEN BEFORE VIDEO PIXEL ACCESS**
- Frozen date: 2026-08-03 UTC
- Scope: integrity of exactly 12 existing Pilot v1.1 MP4 files
- Execution class: CPU-only, read-only inputs, versioned new outputs
- Scientific scope: engineering/output integrity only; no identity or attribute measurement

## 1. Freeze declaration

This protocol was written before opening a video container, decoding a frame, or reading video pixels in the current research pipeline. Only filesystem metadata, byte size, paths, and whole-file SHA256 values were read while creating it.

The rules and thresholds below must not be changed after pixel access. A later concern may produce a prospectively frozen `v2`, but `v1` inputs, outputs, logs, and conclusions must remain unchanged and must not be retrospectively reclassified.

## 2. Authorized inputs and immutable sources

- Manifest: `/root/autodl-tmp/finegrained/experiments/pilot_v1_1/manifest.csv`
- Config: `/root/autodl-tmp/finegrained/experiments/pilot_v1_1/config.json`
- Generation summary: `/root/autodl-tmp/finegrained/experiments/pilot_v1_1/generation_summary_v1.csv`
- Generation events: `/root/autodl-tmp/finegrained/experiments/pilot_v1_1/generation_events_v1.jsonl`
- Video root: `/root/autodl-tmp/finegrained/experiments/pilot_v1_1/outputs`
- Registry: `governance/artifact_registry_v1.csv`

All inputs are read-only. The canonical config SHA256 is `40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47`.

## 3. Mandatory preflight and stop conditions

Before any video is opened, the future audit script must:

1. confirm that GPU visibility is disabled for the process and that no model framework or model weights are loaded;
2. confirm the exact manifest, config, summary, events, registry, and protocol SHA256 values;
3. confirm 12 unique manifest `sample_id` values and four rows per attribute;
4. confirm 12 unique successful summary rows and one-to-one manifest/summary correspondence;
5. confirm every planned output path is absent; any collision stops the run;
6. record the actual Python, OpenCV (`cv2`), and Decord versions without installing or upgrading anything;
7. require CPU decoding from both OpenCV and Decord; an unavailable/import-failing decoder stops the run and requires researcher approval;
8. confirm there are exactly 12 expected MP4 mappings and no extra MP4 under the frozen output root;
9. open an append-only execution log before decoding, containing protocol hash, script hash, Git commit, input hashes, UTC start time, and preflight results.

Any mismatch, ambiguity, missing input, unexpected extra MP4, dependency problem, or output collision is fail-closed: do not decode any video and do not repair state automatically.

## 4. File mapping and uniqueness

For every manifest row:

- expected directory is exactly `<output_root>/<sample_id>/`;
- expected basename is exactly `<sample_id>_seed42.mp4`;
- the path must equal the corresponding `video_path` in `generation_summary_v1.csv`;
- `sample_id`, attribute, label, identity, and path must agree across manifest and summary;
- exactly one MP4 must exist for the sample;
- every MP4 under the output root must map to exactly one manifest row;
- symlinks are not accepted as video inputs;
- duplicate canonical paths or duplicate SHA256 values across different sample IDs are recorded and cause video-level failure. A shared hash is not silently treated as deduplication.

Missing, extra, ambiguous, or multiply mapped files receive explicit reason codes and are never substituted.

## 5. Byte size and whole-file SHA256

- Record byte size as a non-negative integer.
- A missing file is `OUTPUT_FILE_MISSING`.
- A zero-byte file is `OUTPUT_FILE_EMPTY` and fails.
- No nonzero minimum-size heuristic is used; byte size is descriptive because codec efficiency varies.
- Compute SHA256 over the original file bytes in streaming chunks without decoding.
- The digest must be 64 lowercase hexadecimal characters and match both the frozen registry and generation summary.
- A digest mismatch is `VIDEO_SHA256_MISMATCH` and stops decoding that video. The file is not replaced, renamed, or regenerated.

## 6. Container readability and full-decode rules

Two CPU decoders are required:

- primary: OpenCV `VideoCapture`, sequential reads from frame zero through end-of-stream;
- cross-check: Decord `VideoReader` with explicit CPU context, reading every indexed frame.

A container passes only when both decoders open it without exception, traverse the complete stream, and agree on decoded frame count and frame dimensions. Decoder warnings and exceptions are retained verbatim in the log.

A decoded frame is valid only if it:

- is returned successfully by both required traversal procedures;
- has a finite, non-empty image array;
- has three color channels;
- converts deterministically to canonical `uint8` RGB;
- has exactly the expected width and height;
- has no truncated row, channel, or buffer.

Early EOF, an exception, an invalid array, a malformed frame, inconsistent dimensions, or decoder disagreement is `FRAME_DECODE_FAILED` or `DECODER_DISAGREEMENT`. No frame is interpolated, duplicated, or skipped to repair the stream.

## 7. Frozen media expectations and tolerances

| Property | Frozen expectation | Allowed tolerance | Failure code |
|---|---:|---:|---|
| Decoded frame count | 49 | none | `FRAME_COUNT_MISMATCH` |
| Frame width | 720 px | none | `RESOLUTION_MISMATCH` |
| Frame height | 480 px | none | `RESOLUTION_MISMATCH` |
| Average/declared FPS | 8.000 | absolute difference ≤ 0.01 FPS | `FPS_MISMATCH` |
| Nominal duration | 49 / 8 = 6.125 s | absolute difference ≤ one frame interval = 0.125 s | `DURATION_MISMATCH` |

Duration is recorded from each available decoder/container report and also as `decoded_frame_count / measured_fps`. Missing duration metadata is recorded; it is a failure if no reliable duration can be obtained from either required decoder. OpenCV and Decord FPS values must each satisfy the tolerance and differ from each other by no more than 0.01 FPS.

## 8. Canonical pixel representation for diagnostics

The following diagnostics run only after all byte-level and container preconditions for a video pass. They use the full decoded frame in canonical 8-bit RGB, without face crops, attribute regions, model inference, or learned metrics.

Luma is frozen as:

`Y = 0.2126 * R + 0.7152 * G + 0.0722 * B`, on the 0–255 scale.

For pairwise diagnostics, luma is resized to 64×64 using deterministic area interpolation and then retained as floating point on the 0–255 scale.

## 9. Black-frame definition

For each frame record mean luma and the fraction of pixels with `Y <= 16`.

A frame is `BLACK_FRAME` only when both conditions hold:

- at least 98% of pixels have `Y <= 16`; and
- mean luma is at most 8.

This deliberately strict engineering threshold detects near-empty black output rather than judging dark cinematography. Any black frame causes visual-integrity failure for that video; its index and raw diagnostic values are retained.

## 10. Exact and near-duplicate definitions

For each adjacent pair `(t-1, t)` among the 49 original frame indices:

- `EXACT_DUPLICATE` means SHA256 of the canonical full-resolution RGB byte arrays is identical.
- Compute `NMAE = mean(abs(Y64_t - Y64_(t-1))) / 255`.
- Compute `close_fraction` as the fraction of 64×64 luma pixels whose absolute difference is at most 2 intensity levels.
- A non-exact pair is `NEAR_DUPLICATE` when `NMAE <= 0.002` and `close_fraction >= 0.995`.
- `DUPLICATE_LIKE` means exact or near duplicate.

Record every pairwise value and flag. An isolated duplicate-like transition is diagnostic and does not alone fail the video.

## 11. Frozen-run and static-video definitions

- A `FROZEN_RUN` is at least 8 consecutive duplicate-like transitions, corresponding to at least 9 frames and 1.0 second between the first and last frame at 8 FPS.
- A `STATIC_VIDEO_ANOMALY` occurs when at least 44 of the 48 adjacent transitions (at least 90%, rounded up) are duplicate-like.

Any frozen run or static-video anomaly causes visual-integrity failure. These are gross-failure diagnostics only; they are not motion-quality scores and must not be used to compare attributes.

## 12. Damage, missingness, and reason codes

Statuses are never encoded as attribute absence or numeric zero.

Video-level status is one of:

- `PASS`
- `FAIL_MAPPING`
- `FAIL_FILE_INTEGRITY`
- `FAIL_CONTAINER_OR_DECODE`
- `FAIL_MEDIA_SPEC`
- `FAIL_VISUAL_INTEGRITY`

Required reason codes include:

- `OUTPUT_FILE_MISSING`, `OUTPUT_FILE_EMPTY`, `UNEXPECTED_EXTRA_VIDEO`
- `PATH_MAPPING_MISMATCH`, `DUPLICATE_PATH`, `DUPLICATE_VIDEO_HASH`
- `VIDEO_SHA256_MISMATCH`, `CONTAINER_OPEN_FAILED`
- `FRAME_DECODE_FAILED`, `DECODER_DISAGREEMENT`, `CORRUPT_FRAME`
- `FRAME_COUNT_MISMATCH`, `FPS_MISMATCH`, `DURATION_MISMATCH`, `RESOLUTION_MISMATCH`
- `BLACK_FRAME`, `FROZEN_RUN`, `STATIC_VIDEO_ANOMALY`

Every failure has one primary reason code and may have ordered secondary codes. Missing numeric fields remain empty in CSV and `null` in JSON. Exceptions and warnings are copied to the log; no failed row is dropped.

## 13. Video-level and Pilot-level decisions

A video is `PASS` only if all of the following hold:

- unique and exact manifest/summary/path mapping;
- non-empty file and matching registered SHA256;
- successful complete traversal by both CPU decoders;
- exactly 49 valid decoded frames at 720×480;
- FPS and duration within frozen tolerances;
- zero corrupt or black frames;
- no frozen run and no static-video anomaly.

The Pilot integrity audit is `PASS` only if:

- the expected set contains exactly 12 videos with no extra or missing MP4;
- all 12 videos individually pass;
- summary paths, statuses, stored SHA256 values, and media specifications agree with observed values;
- all declared outputs validate against their schemas.

Otherwise the overall result is `FAIL`. A failure does not authorize exclusion, deletion, repair, regeneration, threshold modification, or continued attribute evaluation. It triggers a human gate.

## 14. Required versioned outputs

The planned output root is:

`/root/autodl-tmp/finegrained/research_pipeline/derived/pilot_v1_1/video_integrity_audit_v1`

The future audit must create new, non-existing files:

- `video_integrity_audit_v1.csv`: one row per expected or unexpected video;
- `frame_inventory_v1.csv`: one row per expected frame index, with decode and diagnostic fields;
- `pilot_output_audit_v1.json`: protocol, provenance, aggregate decision, counts, and reason codes;
- `pilot_video_contact_sheet_v1.png`: deterministic fixed-index contact sheet for engineering inspection only;
- `video_integrity_audit_v1.log`: append-only preflight, execution, warnings, exceptions, and validation log.

Each output must record or be accompanied by its SHA256, byte size, schema version, producing script SHA256, research-pipeline Git commit, protocol SHA256, source artifact hashes, UTC timestamps, and parent/derived lineage. Temporary files must be created only inside a new run-specific temporary directory and atomically finalized; output collisions stop execution.

## 15. Prohibited interpretation and post-hoc changes

This audit cannot establish identity preservation, eyeglasses retention, facial-hair retention, hair-color retention, temporal attribute stability, H1–H4, or a ConsisID mechanism.

After video pixel access begins, do not change mappings, tolerances, diagnostic thresholds, failure rules, output schemas, sample inclusion, or the overall decision rule. Unexpected behavior is reported under the frozen rules and escalated to the researcher.
