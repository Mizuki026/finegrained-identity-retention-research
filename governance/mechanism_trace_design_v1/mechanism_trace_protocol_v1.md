# Prospective ConsisID mechanism trace protocol v1

Status: **design complete; implementation and execution not authorized**.

## 1. Objective and claim boundary

The proposed `mechanism_trace_v1` will describe whether reference-derived
signals are available at frozen code locations and how the magnitude of the
local identity residual varies across block and denoising position in the fixed
formal panel.

It will not, by itself, establish attribute causality, locate a definitive
bottleneck, demonstrate post-injection persistence, or show improved generation
quality. It will not support population, model-wide, frame-independent, or
cross-attribute inference.

## 2. Frozen universe and run phases

### 2.1 Engineering phase E

- Universe: the eight units in `engineering_subset_v1.csv`.
- Selection rule: within each attribute, rank the ten `formal_pair_id` values
  lexicographically by
  `SHA256(formal_pair_id + "|mechanism_trace_v1_engineering_pair_subset")`;
  take the first two complete matched pairs.
- Seed: frozen `seed_index=1`, value `2686238281`.
- Per unit: two unchanged baseline repetitions and one zero-local-residual
  engineering control.
- Ceiling: 24 trajectories and 1,200 transformer denoising steps.
- Purpose: shapes, dtype/device, hook placement, deterministic summary repeat,
  and route-isolation checks only. No scientific outcome from phase E may enter
  phase S analysis or motivate a metric change.

### 2.2 Scientific descriptive phase S

- Universe: all 40 frozen formal reference units.
- Seeds: all four frozen seeds: `2686238281`, `280026145`, `2169901996`, and
  `2046930553`.
- Tasks: the existing 160 frozen generation-manifest tasks, ordered by
  `task_id`; no replacement, deletion, or result-dependent rerun.
- Condition: unchanged checkpoint, prompt, guidance, scheduler, reference
  preprocessing, and local identity scale.
- Each trajectory uses all 50 scheduler positions.
- No zero-residual or permutation intervention is part of scientific phase S.
- No video is decoded or saved.

Phase S cannot begin merely because phase E passes. It requires a later
execution freeze containing the implemented code commit and a separate
researcher authorization.

## 3. Instrumentation locations

All reductions cast their inputs to float32. Full tensors remain transient in
device or process memory and must not be serialized.

1. `id_ante_embedding`: 512-D InsightFace component before concatenation.
2. `id_cond_vit`: normalized 768-D EVA head component.
3. `id_vit_hidden[0:5]`: the five `[B,577,1024]` EVA token tensors.
4. `valid_face_emb`: `[B,32,2048]` Local Facial Extractor output.
5. `image_latents`: reference-image VAE latents before concatenation with noisy
   latents.
6. `R[t,j]`: output of `perceiver_cross_attention[j]` before scaling and
   residual addition at scheduler position `t` and injection site `j`.
7. `H[t,j]` and `H[t,j] + local_face_scale * R[t,j]`: the video tokens
   immediately before and after the local residual.

The implementation must not hook text-token activations, VAE-decoded frames,
or unrelated model layers.

## 4. Reference-side attribute readout

The following pooled vectors are computed in memory and then discarded:

- InsightFace: L2-normalized 512-D vector.
- EVA head: L2-normalized 768-D vector.
- Each EVA hidden stage: mean of the 576 patch tokens, excluding CLS, followed
  by L2 normalization; five 1024-D vectors.
- Local Facial Extractor: mean of 32 tokens followed by L2 normalization; one
  2048-D vector.
- Reference-image latent: spatial mean of the nonzero first latent frame,
  followed by L2 normalization; one 16-D vector.

For each attribute and representation stage separately, use leave-one-matched-
pair-out directional ranking:

1. Hold out one of the ten frozen positive/control pairs.
2. On the other nine pairs, compute the mean positive-minus-control feature
   direction.
3. Score both held-out units by dot product with that direction.
4. Record the held-out margin `score_positive - score_control`.
5. Define a tie prospectively as `abs(margin) <= 1e-8`.

The primary representation readout is correct/tie/wrong counts and all ten
margins at the Local Facial Extractor output. The eight earlier-route readouts
are secondary diagnostics. No classifier threshold, p-value, confidence
interval, or population claim is permitted.

## 5. Injection summaries

For each classifier-free-guidance branch separately, at every scheduler
position `t=0..49` and injection index `j=0..20`, compute online:

- `rms_h = sqrt(mean(H^2))`;
- `rms_r = sqrt(mean(R^2))`;
- primary `relative_residual_rms = rms_r / max(rms_h, 1e-12)`;
- secondary mean tokenwise cosine between `H` and `R`, using denominator floor
  `1e-12`;
- secondary tokenwise `rms(R)` quantiles 0.10, 0.50, and 0.90;
- secondary per-latent-frame `rms(R)` for all 13 latent frames.

For `image_latents`, record overall RMS, first-frame RMS, and the maximum
absolute value in the nominal zero-padding frames. These are route-integrity
summaries, not attribute measurements.

## 6. Prespecified aggregation

- Injection indices `0..6`, `7..13`, and `14..20` form early, middle, and late
  block groups. They correspond to Transformer blocks `0..12`, `14..26`, and
  `28..40` at interval two.
- Scheduler positions `0..16`, `17..33`, and `34..49` form early, middle, and
  late denoising groups. Position means order in the frozen 50-step scheduler,
  not normalized noise magnitude.
- Each run yields a prespecified 3x3 block-by-denoising grid for the primary
  relative residual RMS, separately for unconditional and text branches.
- In phase S, first average the four seed summaries within each reference unit.
  Then form positive-minus-control differences within each frozen pair.
- For each attribute and each 3x3 cell, report the ten pair differences, sign
  counts, mean, median, minimum, and maximum.
- Tokens, frames, blocks, timesteps, seeds, and CFG branches are repeated
  measurements, not independent experimental units.

The primary injection description is the complete prespecified 3x3 grid. All
other injection metrics and full trajectories are secondary diagnostics. No
single favorable cell may be promoted after inspection.

## 7. Multiplicity and interpretation

- No null-hypothesis significance tests or inferential confidence intervals are
  planned.
- Attributes are analyzed and reported separately.
- All primary 3x3 cells and all ten Local Facial Extractor margins must be
  reported, including zeros and unfavorable directions.
- Secondary stages and metrics are labeled exploratory diagnostics.
- Activation magnitude is not attribute information. Decodability is not a
  causal mechanism. A local-route residual difference is not generation
  improvement or proof of a model bottleneck.

## 8. Engineering controls and pass rules

Phase E must satisfy all of the following before an execution package may even
propose phase S:

- every tensor matches the frozen stage name, rank, expected last dimension,
  dtype policy, and device policy;
- both baseline repetitions have identical categorical metadata and numerical
  summaries satisfying
  `abs(a-b) <= 1e-6 + 1e-5 * max(abs(a), abs(b))` elementwise;
- the zero-local-residual path computes `R` but adds exactly zero local residual;
- baseline and zero-control runs have identical reference input hash, prompt,
  seed, scheduler positions, `id_cond`, pooled EVA inputs, `valid_face_emb`, and
  `image_latents` summaries within the same tolerance;
- the zero-control is labeled engineering-only and excluded from all phase S
  result tables.

Condition permutation is not implemented in v1.

## 9. Failure handling and stopping rules

- Reference preprocessing failure: record failure; do not substitute another
  reference or alternate detector.
- Shape, hook-order, NaN/Inf, route-isolation, determinism, or zero-padding
  failure: stop the phase immediately and return to researcher review.
- CUDA out-of-memory: stop; do not reduce resolution, frames, steps, tensor
  scope, or precision without a new freeze.
- A clearly external process interruption before a trace artifact is finalized
  permits at most one byte-identical command retry, recorded in an append-only
  event log. No retry may depend on a scientific summary.
- Phase S retains every task status and missing state. No imputation or
  favorable subset analysis is allowed.

## 10. Privacy and storage

- Raw identity embeddings, EVA token tensors, LFE tokens, video-token tensors,
  reference images, and decoded media must never be written by the trace code.
- Detailed bounded summaries and pseudonymous formal IDs may be stored only in
  the formal runtime and frozen by path, byte count, and SHA256.
- Git may contain protocols, code, aggregate summaries, verification records,
  and hashes, but not reference-linked media or raw identity tensors.
- Formal-paper artifacts may contain aggregate finite-panel descriptions only;
  publication of per-reference trace tables requires a separate privacy review.

## 11. Compute ceiling

- Device ceiling: one GPU process at a time; no distributed execution.
- Precision and geometry: frozen bfloat16, 49 frames, 480x720, 50 scheduler
  positions, guidance 6.0; no downscaling or shortened schedule.
- Phase E ceiling: 24 trajectories / 1,200 transformer steps.
- Phase S ceiling: 160 trajectories / 8,000 transformer steps.
- Total ceiling: 184 trajectories / 9,200 transformer steps and 72 GPU-hours.
- Crossing any ceiling requires a new prospective budget decision; unfinished
  tasks remain missing rather than being run under a changed design.

## 12. Remaining gates

Approval of this document may authorize implementation and CPU-only static
tests, but not model loading or GPU execution. Before any runtime work, freeze:

- instrumentation source and test hashes;
- exact research and ConsisID commits;
- Python package inventory and CUDA/GPU inventory;
- all relevant weight and configuration hashes;
- output schema, runtime directory, event log, and independent verifier;
- a dry-run showing task enumeration without loading weights;
- a final execution review record with explicit researcher approval.
