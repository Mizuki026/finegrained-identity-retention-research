# Facial-hair descriptive aggregation plan v1

**Status:** FROZEN; EXECUTION BLOCKED pending completion and acceptance of the fresh condition-blinded facial-hair reference audit v2.

## Purpose and evidence boundary

This plan prospectively fixes descriptive-only aggregation of the already frozen and reconciled Pilot facial-hair labels. It may describe a fixed, confounded Pilot at the video level. It cannot establish general annotation validity, generated-video-domain validation, identity retention, a causal mechanism, a model property, or H1–H4.

## Why execution is blocked

**Fact:** `facial_hair_reference_audit_v2/audit_metadata.json` reports status `generated_pending_condition_blinded_annotation` and requires a fresh blinded reference audit before its acceptance rule can be evaluated.

**Research decision:** no facial-hair condition-level aggregation, expected-label match calculation, figure, manuscript result, or claim will be executed under this plan until the fresh reference audit is annotated, its labels are frozen, the private key is opened under a separate authorization, and all four acceptance requirements pass. The existing generated-frame labels remain preserved as data lineage; this plan does not retroactively change them.

## Frozen inputs

| Input | SHA256 | Role |
|---|---|---|
| Manual ordinal protocol v2 | `307f2afb4eb92280359960b70eff81cc188d26a60876db896e451f84cc6f25aa` | Labels, observability, binary conversion, planned summaries |
| Analysis and claim plan v1 | `eab3259fc490250425b6c98e746521b22f6f66b7c2aeaf6eded5165aaa2f6ed4` | Video-level descriptive unit and claim limits |
| Attribute execution protocol v1 | `432a7f624edc2baacc03b5c7ad6edc6ea0ebf4bf45a9f21366307ca119d77935` | Frame universe and missing-state discipline |
| Reconciled annotation table | `e97e3f4f8b2e1b11d9463a5d1bb78fe816989700cc8fa3e8934a5a9efe61050c` | 575 frozen labels joined to sample/frame records |
| Frame inventory v2 | `805df7257f1d207a1d693a21337b79e65269246a3fffbcdee3555569cd0e06d3` | Full 12 × 49 × 3 evaluation inventory |
| Pilot manifest | `dcf66f0222986403493a7c9a09d310629909d4aef590634348b41ce12544f79d` | Predetermined sample/attribute/condition design |

## Units and fixed universe

- The descriptive unit is one generated video. Frames are correlated within-video measurements and are never independent observations.
- Coverage and ordinal sequences use all twelve predetermined videos and all original indices 0–48 per video (49 planned frames each; 588 planned facial-hair frame positions overall).
- No video, frame, label, `U` entry, pre-existing non-annotated frame, or low-coverage video may be excluded.
- Expected-condition match is applicable only to manifest rows whose predetermined `attribute` is `facial_hair`; all other manifest attributes remain in the all-video coverage ledger but are marked `NOT_APPLICABLE_ATTRIBUTE_NOT_TARGET` for facial-hair expected-match fields.

## State mapping and denominators

| Source state | Aggregated state | Treatment |
|---|---|---|
| Ordinal `0` | `VALID_ABSENT` | Valid; binary absent |
| Ordinal `1` | `VALID_PRESENT_SUBTLE` | Valid; binary present |
| Ordinal `2` | `VALID_PRESENT_CLEAR` | Valid; binary present |
| Ordinal `U` + reason | `UNOBSERVABLE_MANUAL` | Retain reason; exclude only from valid-label denominator |
| No `annotation_item_id` in the existing frame inventory | `UNANNOTATED_PREEXISTING` | Retain the pre-existing frame-inventory status/reason; never convert to absent or `U` |
| Any input/schema/join failure | `PIPELINE_FAILURE` | Fail closed; no summary produced |

For every video, report: planned frame count; valid ordinal counts for 0/1/2; manual-U count by reason; pre-existing unannotated count by existing reason; valid fraction `(0+1+2)/49`; and raw ordinal/state sequence in original frame order. Do not impute, interpolate, carry forward, or reclassify any state.

## Predetermined descriptive calculations

1. Preserve ordinal counts (`0`, `1`, `2`) and binary counts (absent=`0`; present=`1|2`) separately.
2. For predetermined facial-hair target videos only, calculate binary expected-match fraction over valid labels only:
   - manifest `positive`: present is a match;
   - manifest `negative`: absent is a match.
3. For all other videos, leave expected-match fields `NOT_APPLICABLE_ATTRIBUTE_NOT_TARGET`; do not infer a facial-hair target from visible appearance.
4. Calculate adjacent binary flip count only for pairs of consecutive original indices where both labels are valid; never bridge `U`, unannotated, or failed positions.
5. Flag `LOW_COVERAGE` if valid fraction is below 0.50, while retaining the video and reporting its valid-only summaries with that flag.
6. Produce video-level tables only. Do not pool frames as independent observations, run p-values, fit regressions, estimate uncertainty, create a composite score, or use a post-hoc threshold.

## Required outputs and verification

Execution, if and only if the reference-audit gate opens, must create a new versioned directory containing:

- one reconciled frame ledger covering all 588 planned facial-hair positions;
- one 12-row video summary CSV;
- raw ordinal/state sequences by video;
- one execution audit JSON and append-only log;
- input/output SHA256 manifest;
- independent verifier JSON/log checking row counts, sample ID set, 49 frames per video, states, denominators, expected-match applicability, and every computed value;
- README identifying every output as exploratory, single-annotator, and descriptive.

All scripts must dry-run without generating summaries, pass a synthetic calculation test, reject output-directory reuse, and fail closed on any mismatch.

## Claim language frozen before results

Permitted only after all required outputs and independent verification pass: “In this fixed, confounded Pilot, condition-blinded single-annotator ordinal labels produced these video-level descriptive summaries under the frozen rubric.”

Prohibited: “the model preserves/loses facial hair,” “this proves H1,” any general annotation-validity claim, any causal claim, any frame-level inferential claim, or any claim of inter-rater reliability.

## Execution gate

The next required research action is completion of the fresh reference audit v2 under its own blinded-label freeze and unblinding gates. No facial-hair descriptive aggregation is authorized by this plan alone.
