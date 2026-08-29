# Mechanism–outcome linkage implementation review v1

Status: **implementation and no-weight checks pass; real linkage execution remains blocked**.

## Implemented scope

The implementation follows the seven researcher-approved design decisions. It
keeps eyeglasses and facial hair separate, requires all ten planned
`formal_pair_id` values per attribute, and implements the frozen pooled-LFE
margin as the sole primary mechanism variable. The complete secondary families
contain all eight upstream representation stages and all 18 CFG-by-3x3
injection cells per attribute.

Spearman correlation is implemented with average ranks for ties. Zero-variance
vectors yield an undefined coefficient. The code produces no p-value,
confidence interval, reduced-panel result, stage/cell selection, multiplicity
claim, or cross-attribute ranking.

## Fail-closed execution boundary

No execution authorization is stored in this package. The included template
has status `TEMPLATE_NOT_AUTHORIZATION` and all execution authority flags set
to false.

Formal mode refuses to open any candidate input unless a later authorization:

- has status `CPU_LINKAGE_EXECUTION_APPROVED`;
- separately enables formal input audit, real input reads, joining,
  association computation, and independent verification;
- keeps model loading, GPU execution, and network access false;
- binds the plan, analyzer, verifier, and four source files by exact path,
  bytes, and SHA256;
- binds every source by exact CSV header and complete unique key universe; and
- binds one new external output directory that does not already exist and is
  outside Git and the frozen Phase-S directories.

Any missing, duplicate, unexpected, or non-finite value stops the computation.
The analyzer refuses output overwrite. Joined pseudonymous pair tables are
external-only.

## CPU-only verification

Nine synthetic unit tests passed. They cover average ranks, perfect/reverse and
zero-variance Spearman behavior, the approved fixed families, explicit CUDA
hiding, rejection of an unapproved execution record before output creation,
complete synthetic 2/16/36 association production, independent recomputation,
and detection of a tampered joined value.

Synthetic test correlations are engineering checks only; they contain no
frozen experimental outcome or trace value and are not scientific results.

The no-weight dry-run and its independent verifier both passed. The dry-run
accepted only the approved plan, did not receive any real input path, opened no
outcome or trace input, created zero joined rows, computed no association, and
used no model module, model weight, GPU, or network.

## Scientific interpretation boundary

This implementation adds no mechanism result. Existing evidence still shows
that upstream EVA linear readability can coexist with a mixed mean-pooled LFE
readout, while all scalar injection-magnitude cells are heterogeneous in sign.
That pattern is compatible with a multi-route, distributed-representation
working model, but does not validate it or establish a bottleneck.

A later association, regardless of sign or magnitude, would describe only
fixed-panel pair-level co-variation. It could not establish causality,
localization, attribute content in a residual, population or model-wide
behavior, frame independence, route necessity/sufficiency, or cross-attribute
ordering.

## Next gate

Stop before formal input audit, real input reads, outcome–trace joining, or any
association computation. The researcher must separately review the complete
implementation package and approve a filled, independently verified CPU
execution authorization as specified in `cpu_execution_review_gate_v1.md`.
