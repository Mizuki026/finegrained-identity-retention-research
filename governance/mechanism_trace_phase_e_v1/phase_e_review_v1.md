# Mechanism trace phase-E review v1

Status: **engineering phase complete and independently verified; phase S remains blocked**.

## Verified facts

- The exact frozen phase-E plan ran: eight units, 24 trajectories, 1,200
  Transformer steps, 50 scheduler positions, 21 local injection sites, and two
  separately recorded CFG branches.
- All 24 task statuses are `COMPLETE_BOUNDED_SUMMARIES_ONLY`; the event log has
  exactly 24 ordered start/complete pairs and no stop event.
- The runtime produced exactly 50,400 injection-summary rows, 24 reference-route
  rows, and no scientific representation-margin file.
- Both baseline repetitions agree elementwise at all 16,800
  unit×step×site×CFG keys. The maximum absolute difference across the frozen
  bounded summaries is exactly `0.0`.
- All 16,800 zero-local-residual rows have `local_face_scale=0` and
  `rms_post=rms_h` within the frozen tolerance. The reference-image route is
  unchanged across the three runs per unit; its maximum absolute difference is
  exactly `0.0`.
- The 50 scheduler timesteps are identical across every task, site, and CFG
  branch. Task order and all runtime CSV column orders match the frozen plan.
- No `.partial` artifact remains. No raw tensor, identity embedding, reference
  image, scientific margin, or decoded media file was written.
- Runtime duration was 1.886 GPU-hours against a 12-hour phase ceiling. Per-task
  duration ranged from 280.752 to 282.574 seconds.

## Current engineering observation

The implemented hooks, online float32 reductions, existing
`local_face_scale=0` control, and bounded-output path operated deterministically
for the fixed eight-unit engineering subset. This is evidence that the
measurement mechanism is operational under the frozen runtime, not a result
about identity retention or attribute retention.

The hashed runner loads the checkpoint in bfloat16 on CUDA and the hook code
casts reductions to float32. Shape and hook-order requirements are enforced at
runtime. Original source-tensor dtype and device values were not separately
persisted as metadata columns; device compatibility is supported by the
successful single-CUDA execution and code-bound loading path rather than a
dedicated per-tensor metadata table. Accepting this evidence mode is an explicit
item in the next review gate.

## Not established

Phase E does not show that an attribute is encoded, retained, lost, or caused
by any route. It does not compare the 40-unit scientific panel, support an
attribute ranking, identify a model bottleneck, or demonstrate generation
quality improvement. The zero-local-residual control is engineering-only and
must not enter phase-S scientific tables.

No scientific mechanism hypothesis has yet been tested. The prospective
hypotheses remain only that frozen reference-side stages may contain
directionally readable attribute information and that local residual magnitude
may vary over the fixed block×denoising grid.

## Engineering decision

The implemented measurement mechanism passes the prespecified repeat,
zero-route, scheduler, shape/order, persistence, and budget checks. Proceeding
to phase S still requires a separate researcher decision on the exact 160-task
execution package. No phase-S authorization file exists.
