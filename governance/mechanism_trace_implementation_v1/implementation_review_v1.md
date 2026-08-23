# Mechanism trace implementation review v1

Status: **implementation complete; CPU/no-weight checks pass; GPU execution remains blocked**.

## Implemented scope

The implementation is bound to the prospective `mechanism_trace_design_v1`
freeze. It enumerates exactly 24 engineering trajectories and 160 scientific
baseline trajectories, with all 50 scheduler positions and all 21 local
identity injection sites. Scientific execution cannot pass its authorization
gate unless an independently verified phase-E result is supplied by path and
SHA256.

The runtime instrumentation records float32 bounded summaries only. It keeps
the nine pooled reference representations in memory long enough to compute the
frozen leave-one-matched-pair-out margins, then discards them. It requests
`output_type="latent"` and never decodes or saves video. Reference image paths
and hashes are read from the frozen generation manifest and each image SHA256
is checked immediately before preprocessing.

The zero-local-residual engineering condition sets the checkpoint's existing
`transformer.local_face_scale` to exactly zero. Hooks still observe the
unscaled cross-attention residual `R`, while `rms_post` is computed as
`rms(H + local_face_scale * R)`. This is an engineering route control, not a
scientific intervention and not evidence of generation improvement.

## Fail-closed controls

- Execution authorization is validated before any torch or ConsisID import and
  validated again inside the runtime entry point.
- The research and ConsisID repositories must match approved commits and both
  worktrees must be clean.
- Every runtime source hash, the exact output directory, one numeric CUDA
  device, trajectory count, transformer-step count, and phase GPU-hour ceiling
  must match the later authorization file.
- Distributed execution is rejected. A wall-clock deadline is checked before
  each trajectory and after each denoising step.
- The 72-hour ceiling is global; the proposed phase-E allocation is 12 hours.
  Any later phase-S authorization must account prospectively for phase-E time.
- Existing output artifacts are never overwritten. Failures leave `.partial`
  evidence and stop the phase; no task replacement or result-dependent retry is
  implemented.
- The independent verifier checks the frozen task universe, all
  task×step×site×CFG keys, arithmetic, finite values, route padding, exact
  representation stages/pairs, and forbidden raw tensor/media extensions.

## CPU-only verification completed

Fourteen unit tests passed with offline mode enabled and
`CUDA_VISIBLE_DEVICES=''`. They cover planning counts, engineering-subset
balance, lazy imports, reference pooling, hook formulas, 180 matched-pair
margins, engineering repeat/zero controls, fixed 3×3 aggregation, and
authorization rejection paths.

The final no-weight dry-run independently passed with 184 tasks and 9,200
transformer steps. It reported `torch_imported=false` and
`consisid_modules_imported=false`. Separately, all 72 entries in the frozen
model inventory passed path, byte, and SHA256 validation without importing
torch or ConsisID modules.

## Prespecified CPU analysis

The analysis code first invokes the independent scientific runtime verifier.
It then averages `relative_residual_rms` in each fixed block×denoising 3×3 cell
per task, averages four seeds within each reference unit, forms
positive-minus-control matched-pair differences, and reports all ten pair
values through sign counts, mean, median, minimum, and maximum. CFG branches
and attributes remain separate. The Local Facial Extractor directional
readout is marked primary; eight upstream readouts remain secondary
diagnostics.

## Limits of the completed checks

No real checkpoint tensor has passed through these hooks. Actual tensor
shape/device compatibility, performance overhead, deterministic repeatability,
and zero-route isolation remain unverified until phase E. Passing static and
synthetic tests does not validate a mechanism, generation quality, causal
effect, population result, model-wide result, frame independence, or
cross-attribute ranking.

The implementation package therefore supports only a decision about whether
to run the 24-trajectory engineering phase. It does not support phase-S GPU
execution.
