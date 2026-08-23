# Research session handoff v1

- Handoff ID: `finegrained_identity_retention_session_handoff_v1`
- Created: 2026-08-23 UTC
- Status: `READY_FOR_NEW_WINDOW_READ_ONLY_BOOTSTRAP`
- Source-state repository commit: `c8aee35dcd8150a4c34dabb80722073237e56e51`
- Source-state branch: `measurement-repair-v1`
- Source-state working tree: clean

This document is a compact session handoff. Frozen CSV/JSON artifacts, their
hashes, and Git history remain the authoritative evidence. This document does
not replace, modify, or reinterpret a frozen experimental artifact.

## 1. Research objective

The project studies fine-grained identity-attribute retention in
reference-conditioned video generation, using ConsisID as the current model
system. The intended research progression is:

1. establish a reliable output-level measurement;
2. characterize failures in a fixed finite panel;
3. map the abstract information-flow hypothesis to the real ConsisID code;
4. localize generation-side representation or conditioning bottlenecks;
5. design a training-free inference-time intervention;
6. evaluate the intervention with a prospectively frozen ablation.

The present project objective is mechanism analysis plus a method and ablation.
Model fine-tuning and LoRA are outside the current plan unless separately
authorized.

## 2. Evidence vocabulary

- **Verified fact:** directly supported by a frozen artifact, hash, or
  independently reproducible check.
- **Current observation:** descriptive pattern in the fixed experimental panel.
- **Working hypothesis:** prospective explanation not yet established by an
  intervention.
- **Research decision:** a researcher-authorized scope or governance choice.

Output-level differences do not identify an internal information-loss location.
An evaluation-pipeline bottleneck is not a generation-model bottleneck.

## 3. Authoritative locations

- Research repository: `/root/autodl-tmp/finegrained/research_pipeline`
- Formal runtime: `/root/autodl-tmp/finegrained/formal_experiment_v1_runtime`
- ConsisID repository: `/root/autodl-tmp/consisid-smoketest/ConsisID`
- Python environment: `/root/autodl-tmp/consisid-smoketest/env/bin/python`
- ConsisID commit: `60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e`
- Current research branch at handoff source state: `measurement-repair-v1`
- Current research commit at handoff source state:
  `c8aee35dcd8150a4c34dabb80722073237e56e51`

The artifact index in `artifact_index_v1.csv` records the principal absolute
paths, byte sizes, and SHA256 values needed to recover the current state.

## 4. Verified formal-generation state

The pre-generation master freeze records:

- two formal attributes: eyeglasses and obvious facial hair;
- 10 matched pairs per attribute;
- 40 reference units total;
- four fixed seeds per reference unit;
- 160 planned generation tasks;
- one common prompt that does not name either target attribute;
- 49 frames, 8 FPS, 50 inference steps, guidance scale 6.0;
- no seed changes, manual substitutions, or selective favorable reruns.

The generation summary records `FORMAL_GENERATION_ALL_160_PASS`. The engineering
integrity freeze covers all 160 videos and 7,840 decoded frames, and the
independent verifier records
`PASS_INDEPENDENT_ENGINEERING_INTEGRITY_VERIFICATION`.

These are engineering facts. They do not establish identity or attribute
retention.

## 5. Verified facial-hair measurement state

The formal facial-hair panel contains 560 fixed sampled frames: seven frames
from each of 80 videos. Two blinded annotators produced independent submissions;
346 items agreed exactly and 214 were adjudicated by a third researcher. The
final anonymous consensus and its independent verification are frozen.

The verified finite-panel aggregation records:

- 371 valid-observable frames and 189 unobservable frames;
- all 10 planned matched-pair contrasts retained;
- mean matched positive-minus-control difference: `0.2052380952`;
- median difference: `0.0000000000`;
- minimum/maximum: `-1.0000000000` / `1.0000000000`;
- four low-coverage reference units and 21 low-coverage videos;
- status: `COMPLETE_FINITE_PANEL`.

This is a computed and independently verified description of the frozen panel,
not a population estimate, causal effect, frame-independent analysis, or
model-wide performance claim. Scientific interpretation remains subject to the
researcher review gate.

## 6. Verified eyeglasses measurement-repair state

The original formal eyeglasses automatic instrument had inadequate face-
detection coverage. On the later fixed 560-frame human panel, the original
`scrfd_640_t05` path produced only 15 measurable frames and only four of 80
videos had any measurable fixed frame. The corresponding original formal
eyeglasses aggregation is preserved but is not suitable as the main eyeglasses
description.

An independent measurement-repair iteration was frozen and completed:

- fixed universe: 80 videos, 560 frames, 40 matched seed-pair units;
- sampled frame indices: `0, 8, 16, 24, 32, 40, 48`;
- two independent blinded human annotators plus third-researcher adjudication;
- human labels: 230 `present`, 319 `absent`, 11 `U`;
- human-observable frames: 549;
- detector selected prospectively by frozen coverage criteria:
  `yunet_native_t03`;
- detector technical audit: 553 pass, seven fail;
- all seven technical failures retained without imputation, substitution, or
  selective exclusion;
- YuNet technical-pass and human-observable intersection: 542 frames;
- CLIP agreement with human consensus on that intersection: accuracy
  `0.9889298893`, balanced accuracy `0.9866071429`.

The direct human finite-panel description records:

- positive condition: 230 present among 278 observable frames;
- control condition: zero present among 271 observable frames;
- 40 matched seed-pair differences: 33 positive, seven zero, zero negative;
- mean difference: `0.825`;
- median difference: `1.0`.

The supported mechanism statement is limited to the measurement system:
original measurement availability was dominated by face-detector non-detection,
not demonstrated CLIP disagreement. YuNet improves measurement availability; it
does not improve or prove improvement in generated-video quality.

The completion artifact remains
`MEASUREMENT_REPAIR_COMPLETE_PENDING_RESEARCHER_INTERPRETATION_DECISION`.

## 7. Research decisions already in force

- Formal-paper release will not include the generated videos corresponding to
  this reference panel.
- Reference-image and dataset rights must be respected; no redistribution is
  implied by local experimental use.
- Hair color is exploratory and a measurement limitation in the current line;
  it is not part of the two-attribute formal confirmatory panel. A future
  hair-color iteration requires a separately frozen design.
- The current claim boundary is descriptive and limited to the fixed videos and
  matched units.
- No causal, population, model-wide, or independent-frame inference is allowed.
- No result-dependent regeneration, seed replacement, metric alteration,
  threshold tuning, imputation, sample deletion, or favorable subset selection
  is allowed.
- No manuscript draft should be created unless the researcher requests it.
- No large GPU experiment, new metric, changed threshold, changed hypothesis,
  changed sample/reference, or changed exclusion rule may begin without a new
  prospective freeze and researcher authorization.

## 8. Current interpretation boundary

### Verified facts

- The formal panel and generation protocol were frozen before generation.
- All 160 planned videos were generated and passed the frozen engineering
  integrity checks.
- The facial-hair consensus and finite-panel tables were independently verified.
- The repaired eyeglasses consensus, detector audit, scoring outputs, and
  arithmetic were independently verified.
- The original eyeglasses measurement path suffered severe detector coverage
  loss.

### Current observations

- In the fixed eyeglasses panel, most matched seed units favor the positive
  condition, but seven units show zero difference.
- In the fixed facial-hair panel, the mean matched contrast is positive while
  the median is zero, with substantial unobservability and heterogeneous pair
  differences.

### Working hypotheses

- Fine-grained attribute failures may arise from insufficient local reference
  representation, insufficient injection, or later suppression by generative
  priors and spatiotemporal denoising.
- Attribute locality, spatial scale, visibility, and sensitivity to motion or
  pose may modulate retention.

None of these generation-side hypotheses has yet been localized or causally
tested inside ConsisID.

## 9. Required next transition

The next window must begin with a read-only bootstrap:

1. read all five files in this handoff directory completely;
2. verify the repository branch, HEAD, and clean/dirty status;
3. verify the listed critical artifact paths and SHA256 values without changing
   files;
4. report any mismatch before proceeding;
5. restate verified facts, pending interpretation decisions, and prohibited
   claims.

After the bootstrap, the next human gate is to decide whether to accept:

1. frozen human consensus as the main finite-panel eyeglasses description;
2. YuNet plus CLIP only as secondary convergent measurement evidence;
3. generation-side ConsisID mechanism analysis as the next independent
   iteration rather than further detector repair;
4. a conservative interpretation of the facial-hair finite-panel summary.

Only after those decisions should a non-generative, read-only ConsisID code-
structure mapping begin. Any probe, intervention, or new generation remains a
separate prospective design gate.
