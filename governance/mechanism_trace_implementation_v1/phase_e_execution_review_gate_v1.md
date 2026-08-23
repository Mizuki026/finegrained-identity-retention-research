# Mechanism trace phase-E execution review gate v1

Status: **explicit researcher approval required; model loading and GPU use blocked**.

## Proposed next action

Authorize engineering phase E only:

- eight frozen outcome-blind reference units;
- seed `2686238281` only;
- two baseline repeats and one zero-local-residual control per unit;
- 24 trajectories and 1,200 transformer steps;
- all 50 scheduler positions and 21 injection sites;
- one process on CUDA device index `0`;
- phase ceiling of 12 GPU-hours, within the previously accepted 72-hour total;
- latent output only, with no decoding or video persistence;
- runtime directory
  `/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_e_run_001`.

The 12-hour ceiling is conservative. The prior 160 formal trajectories took a
mean of 4.883 minutes each (13.021 serial GPU-hours total), but tracing adds
online reductions and synchronization. Reaching the phase ceiling stops the
run; it does not authorize fewer steps, altered precision, replacement tasks,
or a changed metric.

## Reviewer checks

1. Confirm the implementation evidence manifest, freeze, 14 passing CPU tests,
   final no-weight dry-run, environment snapshot, and 72-entry model inventory
   verification are acceptable.
2. Confirm that `local_face_scale=0` is accepted only as the eight-unit
   engineering zero-route control and will not enter scientific result tables.
3. Confirm the two baseline repetitions and in-memory route invariance checks
   are adequate to decide hook placement and deterministic behavior.
4. Confirm bounded CSV/JSON summaries and pseudonymous IDs are permitted in the
   external runtime, while raw tensors, embeddings, reference media, and
   decoded videos remain forbidden.
5. Explicitly approve or reject the exact phase-E resource envelope and runtime
   directory above.
6. Confirm that phase S remains blocked even if phase E passes; a new package
   containing the finalized phase-E artifacts and independent verification is
   required before any scientific GPU execution.

## Authorization construction after approval

Approval will permit creation of a separate runtime authorization JSON outside
Git. It must bind the post-implementation research commit, ConsisID commit,
all runtime code SHA256 values, the exact output directory, CUDA index, 24/1200
ceilings, 12-hour phase ceiling, and an explicit boolean GPU approval. The
runner will reject a missing, altered, stale, or in-repository authorization.

## Stop rule

Do not create the runtime authorization, load any model, import the GPU runtime
for execution, or start phase E until the researcher explicitly approves this
gate. Phase-S execution is not requested by this document.
