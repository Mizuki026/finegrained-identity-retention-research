# Mechanism iteration review gate v1

Status: **researcher review required before runtime instrumentation or GPU work**.

## 1. Completed and accepted inputs

- The four interpretation decisions are recorded in
  `researcher_decisions_v1.json`.
- The static ConsisID mapping is complete at the frozen code commit and actual
  checkpoint configuration.
- No model was loaded, no forward pass was run, no video was generated, and no
  formal result was recomputed during mapping.

## 2. Proposed next independent iteration

Provisional name: `mechanism_trace_v1`.

Proposed objective: determine, descriptively and without claiming causality,
whether reference-derived information is present at defined reference-side
tensors, delivered through the local identity cross-attention route, and
retained in bounded post-injection summaries across block and denoising
position.

This is an instrumentation iteration, not a generation-quality intervention.
It must not be described as improving ConsisID.

## 3. Recommended minimal design

The following is a proposal for review, not yet authorized:

1. Use all 40 frozen formal reference units; analyze eyeglasses and facial hair
   separately and prohibit cross-attribute ranking.
2. Preserve the frozen prompt and existing seed policy. Do not replace failed,
   zero-difference, or low-observability units.
3. Do not decode or save videos in the first trace pass.
4. Instrument only these tensor stages:
   - the 512-D InsightFace component;
   - the normalized 768-D EVA head component;
   - five EVA hidden-state inputs;
   - the 32x2048 local facial extractor output;
   - pre-scale injection residual summaries at the 21 fixed injection sites;
   - paired pre/post-injection video-token summaries.
5. Use the actual 50-step scheduler, but retain only prospectively selected
   bounded summaries by step and block; do not persist full video-token tensors.
6. Separate the two conditioning routes. The first trace pass observes the
   active checkpoint unchanged. Any later local-route ablation must retain the
   reference-image latent route and be labeled as a local-route ablation only.
7. Store no raw identity embeddings, reconstructed reference faces, or
   reference-linked generated media in the research repository.
8. Treat reference unit or matched unit as the analysis unit; never treat token,
   frame, block, or timestep observations as independent replicates.

## 4. Required negative and engineering controls

Before implementation, freeze:

- a shape/dtype/device check for every instrumented tensor;
- deterministic repeat checks on a small prospectively chosen engineering-only
  subset, with no scientific outcome inspection;
- a zero-local-residual engineering control that confirms instrumentation can
  remove only the `PerceiverCrossAttention` residual while leaving the
  reference-image latent route unchanged;
- a condition-permutation control, if approved, that keeps prompt, noise, and
  reference-image latent fixed while permuting only local identity tokens;
- explicit missingness and face-processing failure handling with no fallback
  sample substitution;
- resource ceilings and stopping rules.

The zero and permutation controls are proposed controls, not authorized
interventions or evidence.

## 5. Measurements that still require prospective definition

No metric below may be selected after seeing trace outcomes:

- attribute-information readout at reference-side tensors;
- identity-information control readout;
- injection magnitude and normalization convention;
- spatial/temporal aggregation of video-token summaries;
- post-injection persistence statistic;
- multiplicity handling across five EVA stages, 21 injection sites, and 50
  denoising positions;
- thresholds, missingness states, exclusion rules, and visualization choices.

Simple activation norms alone cannot establish attribute information or a
mechanistic bottleneck.

## 6. Researcher decisions required to open implementation

Please approve, reject, or revise each item:

1. Scope: all 40 frozen reference units, with attributes analyzed separately.
2. Runtime boundary: instrumentation-only first pass with no decoded or saved
   videos.
3. Tensor scope: the six stage groups listed in section 3.
4. Denoising scope: all 50 scheduler steps with bounded summaries, versus a
   smaller prospectively fixed step subset.
5. Controls: zero-local-residual engineering control and condition-permutation
   control.
6. Privacy/storage: summaries only; no raw identity tensors or reference-linked
   media in Git or paper artifacts.
7. Next design task: authorize drafting and freezing exact metrics, analysis
   units, multiplicity policy, failure handling, code commit, environment,
   weight hashes, and GPU ceiling before any implementation.

## 7. Stop condition

Until all seven items are decided, do not implement hooks, load model weights,
run a forward pass, allocate GPU budget, generate video, change a metric or
threshold, or select samples based on observed outcomes.
