# Formal experiment preregistration v1

- Status before generation: `FROZEN_DESIGN_PENDING_MASTER_FREEZE`
- Scope: fixed finite-sample output-level experiment with ConsisID-preview
- Primary attributes: eyeglasses and facial hair
- Reference-condition units: 40 (20 matched pairs)
- Seeds per reference: 4 shared fixed seeds crossed with every reference
- Planned videos: 160
- Generation begun at freeze: NO

## Scientific boundary

H1 (identity-related attributes are not uniformly preserved) is the only
candidate primary hypothesis. H2 is exploratory; H3 is deferred to a separately
frozen probe/intervention study; H4 is not tested. Hair colour is excluded from
the primary experiment. Results are bounded to these fixed references, prompts,
seeds, weights, and videos. They do not support a population-level model claim,
a causal mechanism claim, or frame-level independent-sample inference.

## Sampling and blocking

The immutable formal reference panel has 10 units in each attribute-state cell.
Eyeglasses cells each contain five men and five women. Facial-hair cells are
man-only by design. Each positive unit is paired with a prespecified control.
The same four seeds are used for all 40 units. Seed is a crossed blocking factor,
not a source of new identity-level sample size. No reference substitution, seed
change, favourable rerun, outcome-dependent exclusion, or imputation is allowed.
An interrupted job may only resume exact pending tasks or validate a completed
file produced under the same frozen task; all such recovery is recorded.

## Generation

Every task uses the same target-attribute-neutral prompt. ConsisID-preview runs
for 50 inference steps, guidance scale 6.0, bfloat16, 49 frames, 8 fps, one video
per invocation, with no LoRA, upscaling, or frame interpolation. Each task has a
dedicated output directory so ConsisID's filename counter cannot collide.

## Measurement

Eyeglasses use the already frozen local CLIP ViT-B/32 two-prototype instrument,
with largest-face InsightFace crop and continuous expected-state probability as
the primary video measure. Facial hair uses blinded manual ordinal labels
0/1/2/U; labels 0 and 2 are the prespecified primary states. The manual material
uses seven fixed frames per video (indices 0, 8, 16, 24, 32, 40, 48), two
independent annotators, and third-researcher adjudication of disagreements.
Unobservable and pipeline-failure states remain distinct, all failures are
retained, low coverage is flagged below 50%, and no value is imputed.

InsightFace reference-to-frame cosine similarity is a secondary continuous
identity diagnostic without a post-hoc pass threshold. It cannot substitute for
the attribute endpoints or prove general identity preservation.

## Aggregation and analysis

Frames are correlated repeated observations. First aggregate frames to one
video-level result, then aggregate the four seeds within each reference unit.
Matched positive-control contrasts are computed at the 10 frozen pairs per
attribute. Seed-specific contrasts are reported as robustness diagnostics.
Primary summaries include coverage, expected-state score/match, pairwise
difference, median, range, and all failure counts. Any exact paired randomization
calculation is a finite-panel compatibility summary and is not interpreted as a
population p-value. No multiplicity-adjusted cross-attribute ranking is planned.

## Human gates after generation

Generated videos first undergo engineering integrity verification. Facial-hair
annotation is then prepared anonymously and remains blinded to identity,
condition, and seed. Visual quality concerns are reported but do not authorize
replacement generation. Formal outcome interpretation waits for the complete,
frozen annotation and measurement record.
