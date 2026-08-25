# Mechanism trace phase-S seed-invariance diagnosis v1

Status: **root cause established; no scientific result computed; code change and rerun blocked**.

## Verified facts

Phase S run 001 stopped fail-closed after the first two frozen tasks. The first
task completed and the second task reached all 50 scheduler positions and all
21 injection sites before `ReferenceReadout.add()` raised:

`reference vector changed across seeds:
FEY_01_control/image_latent_first_frame_spatial_mean_l2_normalized`.

The partial files contain 4,200 injection rows, two route rows, two status rows,
and zero representation-margin rows. No execution summary was finalized. No
identity/attribute margin or fixed-panel result was inspected.

The two route-integrity rows have first-frame RMS values
`0.7277534604072571` and `0.7281359434127808`; their absolute difference is
`0.00038248300552368164`. Both padding maxima remain exactly zero.

## Root cause

ConsisID `prepare_latents()` constructs the reference-image latent through
`retrieve_latents(self.vae.encode(...), generator)`. The frozen ConsisID
implementation defaults to `sample_mode="sample"` and calls
`encoder_output.latent_dist.sample(generator)`. Therefore the reference-image
VAE latent is seed-conditioned by construction.

The measurement runner correctly passes each frozen generation seed to that
generator. However, `ReferenceReadout.add()` applies one cross-seed
`torch.allclose` assertion to all nine representation stages. This assertion
is valid for the eight stages derived only from deterministic reference
preprocessing and Local Facial Extractor inputs, but it is not valid for the
sampled image-latent stage.

Phase E used only seed index 1. Its repeat and zero-route controls therefore
verified same-seed determinism but could not exercise this cross-seed mismatch.

## Design conflict

The frozen protocol includes the image-latent vector as a secondary
representation diagnostic and also prespecifies four-seed averaging within
each reference unit. The implementation instead retained only the first vector
per unit and required all later seed vectors to equal it. This is an
implementation/design reconciliation defect, not evidence about ConsisID
identity or attribute retention.

## Recommended minimal correction

- Preserve all 40 units, all four frozen seeds, all nine representation stages,
  the primary Local Facial Extractor stage, directional-ranking formula, and
  tie threshold.
- Collect exactly one vector for every unit×seed×stage key.
- Continue the existing cross-seed `allclose` check for the eight
  deterministic stages.
- For `image_latent_first_frame_spatial_mean_l2_normalized`, accept the four
  prospectively frozen seed-specific vectors and take their arithmetic mean
  within unit. Each per-seed vector remains L2-normalized as frozen; do not
  apply a second normalization after averaging.
- Apply the unchanged leave-one-matched-pair-out directional ranking to the
  resulting unit-level vectors.
- Reject duplicate or missing unit×seed×stage keys and require exactly four
  frozen seeds before margins are computed.

This correction does not alter ConsisID sampling, generation seeds, task
universe, representation stage universe, metric, tie threshold, injection
analysis, or output/privacy policy.

## Rejected alternatives

Changing VAE sampling to posterior mode, using only seed 1, dropping the failed
task, salvaging the two partial trajectories, excluding the image-latent stage,
or changing the tolerance would each alter the frozen generation or analysis
more than the recommended correction.

## Resource accounting

Run 001 attempted two complete 50-step traces. A clean full rerun in a new
directory would make the cumulative ceiling 186 attempted trajectories and
9,300 Transformer steps: 24 phase-E trajectories, two frozen abort attempts,
and 160 new phase-S trajectories. This remains far below the accepted
72 GPU-hour ceiling, but exceeds the frozen 184/9,200 attempt count and
therefore requires explicit approval.

## Boundary

No causal, population, model-wide, frame-independent, cross-attribute, identity
retention, or attribute-retention conclusion follows from this abort or
diagnosis.
