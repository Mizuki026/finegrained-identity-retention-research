# Token-resolved directional analysis researcher decision gate v1

The research order is recorded: token-resolved directional analysis first; controlled intervention receives a separate preregistration only after the directional analysis is completed and reviewed.

Before implementation, accept, reject, or revise these seven fixed design decisions:

1. **Primary tensor scope:** analyze the 32 LFE identity-token slots; exclude the 17,550 injection residual video tokens from v1.
2. **Outcome-blind design:** compute no retention outcome, join, correlation, p-value, confidence interval, or best-token selection.
3. **Direction construction:** per attribute and token index, use leave-one-matched-pair-out positive-minus-control directions from the other nine pairs, with per-token L2 normalization and the frozen `1e-8` tie threshold.
4. **Complete family:** retain all 640 token × pair margins, all 64 attribute × token summaries, and all 20 pair-level token-sign summaries.
5. **Equivalence gate:** require direct LFE extraction to match the hooked LFE tensor in the eight-unit engineering subset and require reconstructed pooled margins to match the frozen run-003 margins before scientific outputs finalize.
6. **Privacy and execution:** raw 32×2048 token vectors remain transient; no raw identity tensor, reference image, or media is serialized. Model/GPU execution remains unauthorized until a later gate.
7. **Compute ceiling and sequence:** propose at most one GPU and 12 GPU-hours total, with engineering capped at four and scientific extraction at eight; intervention preregistration remains blocked until this analysis is completed, frozen, interpreted, and reviewed.

Approval of all seven items may authorize only a later explicitly scoped implementation stage if the researcher says so. It does not itself authorize implementation, tests, model loading, GPU use, capture, or analysis.
