# Mechanism trace implementation review gate v1

Status: **researcher design review required; implementation and GPU execution blocked**.

## Decisions requested

1. Accept or revise the full-panel scientific scope: 40 reference units, four
   frozen seeds, 160 unchanged baseline trajectories, and all 50 scheduler
   positions.
2. Accept or revise the representation readout: leave-one-matched-pair-out
   directional ranking, with the Local Facial Extractor output primary and
   eight upstream routes secondary.
3. Accept or revise the injection description: float32 online summaries,
   `relative_residual_rms` primary, fixed 3x3 block-by-denoising aggregation,
   and CFG branches reported separately.
4. Accept the outcome-blind engineering subset and phase-E controls: eight
   units, seed 1, two baseline repeats plus one zero-local-residual run per unit;
   condition permutation remains deferred.
5. Accept or reduce the ceiling of 184 trajectories, 9,200 transformer steps,
   one GPU process, and 72 GPU-hours. Increasing it requires an explicit revised
   decision.
6. Authorize implementation plus CPU-only schema/unit tests and a no-weight
   dry-run. This does **not** authorize model loading, a forward pass, GPU use,
   or scientific execution.
7. Require a separate execution package and final researcher approval after
   implementation hashes, environment, weights, task enumeration, output
   schema, failure policy, and independent verifier are frozen.

## Audit guidance

- Review `mechanism_trace_protocol_v1.md` sections 2 through 11 for scientific
  and operational choices.
- Review `mechanism_trace_analysis_plan_v1.json` for the machine-readable exact
  indices, formulas, aggregation order, and ceilings.
- Confirm that no metric can be changed after phase-E or phase-S outcome
  inspection.
- Confirm that full tensors and media cannot be persisted.
- Confirm that phase E is engineering-only and excluded from scientific tables.

## Stop rule

Until all seven decisions above are explicitly answered, do not create
instrumentation code, load any weight, run any forward pass, use a GPU, or
generate/decode media.
