# Fine-grained identity-attribute retention — research state v4

Date: 2026-09-16  
Authoritative source-state commit: `290dd40a5a97cfeb211f3df00379fed0220420da`  
Status: controlled-intervention run-002 complete, independently verified, scientifically interpreted, accepted, and closed.

Frozen CSV/JSON artifacts, their bound SHA256 values, and Git history are the factual sources. This narrative is a compact handoff, not an experimental database.

## Repository state

- Research branch: `main`; upstream `origin/main`; source state is 72 commits ahead and 0 behind.
- Research worktree is intentionally not clean only because four user-owned annotation helper scripts remain untracked. They are not part of any governed commit and must not be modified or staged automatically.
- ConsisID HEAD is `60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e`; its worktree is clean.
- `artifact_index_v4.csv` contains 31 direct entries. H001 nests the verified v3 index of 67 entries, which in turn nests v2's 53 entries.

## Verified facts

- The implementation, CPU-only synthetic tests, no-weight dry-run, formal input audit, and final single-GPU engineering run-006 all passed their frozen gates.
- Engineering runs 001–005 are immutable aborted history and must not be reused. Run-006 is engineering feasibility only, not a scientific outcome.
- The seed-1 shard path, its verifier correction attempt, and the direction-recovery audit remain nonreusable history. The sole authoritative scientific transaction is monolithic run-002.
- Run-002 completed 480 trajectories over 40 units, 20 pairs, four seeds, and three conditions, totaling 24,000 scheduler steps in one four-seed process. Generation used 35.5592085 GPU-hours.
- All 480 private final latents were persisted and verified. No decoded media were created during generation, and no raw identity-LFE or direction tensors were persisted.
- Private decode produced and independently verified 480 videos and 23,520 frames in 0.7415468 GPU-hours. Verification v1 is preserved but superseded; corrected verification v2 is authoritative.
- The blind packet contained 3,360 sampled-frame items. Annotators A and B agreed on 1,521; all 1,839 disagreements were adjudicated before unblinding. Human independence is researcher-attested, not file-verifiable.
- Corrected unblinding v2 is authoritative and retains all 625 `U` reasons. Outcome construction contains 120 unit-condition scores with zero invalid scores, no imputation, and no reduced panel.
- The preregistered analysis contains all 20 pair effects. No p-values, confidence intervals, cross-attribute pooling, or cross-attribute ranking were computed.

## Current fixed-panel observation

- Eyeglasses target-versus-sham: 0 correct, 7 ties, 3 wrong; mean `-0.0232142857`, median `0`, range `[-0.125, 0]`.
- Facial hair target-versus-sham: 2 correct, 7 ties, 1 wrong; mean `0.00509370016`, median `0`, range `[-0.0292397661, 0.0555555556]`.
- The complete-family result is sparse, mixed, and centered near zero, not a predominant predicted-direction effect.
- FFH_08 and FFH_09 provide modest pair-specific direction-consistent evidence; FFH_10 is a facial-hair counterexample. Eyeglasses contains no predicted-direction pair effect.
- Many role scores lie at the preregistered floor or ceiling. This is retained as a measurement-state limitation, not used to change the metric after observing results.

## Accepted scientific interpretation

Under this fixed dose, LFE interface, complete 32-token family, human readout, and finite panel, the experiment does not support a broad robust causal contribution of the exchanged held-pair-out directional projection to the generated positive-versus-control attribute contrast.

This does not establish that attribute information is absent from LFE, that the local route is irrelevant, or that any route is necessary, sufficient, bottlenecked, or localized. It supports no population-wide, model-wide, frame-independent, or cross-attribute ordering claim.

## Accepted working models, not verified mechanisms

- Representation–readout mismatch or representation reorganization.
- Multi-path distributed representation.

Both remain compatible with the result; neither is mechanistically verified by it.

## Unverified mechanism hypotheses

- Attribute-relevant structure may be distributed or reorganized across LFE tokens.
- Nonlinear downstream use may make this fixed linear exchange incomplete.
- The fixed displacement may be partly off-manifold.
- Local and spatial routes may compensate or interact.
- Readout saturation may conceal some intervention-induced movement.
- The source of the historical cross-run numerical mismatch remains unlocalized.

## Research decision and boundary

The controlled-intervention v1 analysis window is closed. Retain the complete mixed/near-zero result, including every tie and wrong-direction pair. Do not rerun, selectively regenerate, alter dose or metric, select favorable pairs or tokens, replace the human result, or open a post-hoc frame family.

Current authorization covers governance closure, this handoff, and bounded result synthesis only. It does not authorize a new diagnostic or experiment, reference/outcome reprocessing, model or weight loading, GPU use, generation, decode, annotation, unblinding, outcome reconstruction, or a new analysis family.

## Next minimal work

Prepare a bounded manuscript-style synthesis of the completed research arc and decide whether the mechanism line should end with this result. Any distinct empirical follow-up must begin with a separate, prospective research question, design, claim boundary, and researcher authorization; it must not be framed as rescuing the closed result.
