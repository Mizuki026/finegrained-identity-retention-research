# Open questions and human gates v3

Status: `CONTROLLED_INTERVENTION_PREREGISTERED_IMPLEMENTATION_NOT_AUTHORIZED`

## Immediate authorization gate

The next window must not infer implementation authority from the completed
preregistration. The immediate researcher decision is whether to authorize only:

- runner and LFE-hook instrumentation implementation;
- analyzer and independent verifier implementation;
- CPU-only synthetic tests;
- a no-weight dry-run that enumerates the complete frozen plan without loading
  references, outcomes, model modules, or weights.

If authorized, this stage must remain offline and may create only source code,
tests, schemas, dry-run summaries, hashes, and a new readiness freeze. It must
stop again before formal input audit.

## Later sequential gates

Each gate requires a separate explicit decision; no earlier pass authorizes a
later stage.

1. **CPU-only formal input audit.** Verify the complete panel, task order,
   references by raw-byte hash without decoding, weights/configuration by
   frozen inventory, source commits, output schemas, paths, condition-order
   manifest, privacy, and failure rules. No preprocessing, model load, or
   intervention.
2. **Single-GPU engineering execution.** Use the fixed hash-selected two pairs
   per attribute, eight units, seed index 1, three conditions, and at most 24
   one-step executions. Verify exact target projection exchange, sham
   orthogonality, matched displacement, hook equivalence, unchanged spatial
   route, and absence of persisted raw tensors/media. Hard ceiling two
   GPU-hours; no scientific result.
3. **Single-GPU scientific generation.** Execute all 160 frozen tasks under all
   three conditions: 480 complete trajectories and 24,000 scheduler steps.
   Expected 35–50 GPU-hours, hard ceiling 72. No reduced panel, condition-only
   recovery, or automatic rerun.
4. **Blinded outcome material construction.** Decode only after separate
   approval; sample exactly frames `[0,8,16,24,32,40,48]`; create 3,360
   pseudonymous frame states and a private blind key.
5. **Two-annotator labeling and adjudication.** Use the bound eyeglasses and
   facial-hair codebooks. Preserve every U, reason, and low-coverage state.
6. **Unblinding, outcome construction, and analysis.** Each requires its own
   freeze. Only then may the role-aligned target-minus-sham primary estimand be
   computed over all ten pairs per attribute.

## Scientific questions still open

These are not established findings:

- Does complete 32-token held-pair-out LFE projection exchange change generated
  attribute-role contrast relative to an equal-displacement orthogonal sham?
- Are any intervention effects consistent across all ten fixed pairs, or are
  they pair/state dependent?
- Does sham perturbation have a comparable effect, weakening a
  direction-specific interpretation?
- Can the local-route intervention affect retention while the separate spatial
  route remains unchanged, without implying natural mediation or necessity?
- Would a null/negative intervention result reflect readout mismatch,
  off-manifold perturbation, path compensation, or true lack of contribution?
- Does `rms(H)` normalization explain the facial-hair difference between
  relative RMS and absolute token quantiles?
- What unresolved cross-run state explains the stable-sign but numerically
  non-reproducing pooled-LFE margins?
- Do any results replicate beyond the fixed two-attribute, ten-pair panels and
  this ConsisID checkpoint?

The current design directly addresses only the first three and part of the
fourth. It cannot by itself resolve natural mediation, spatial-path
compensation, route necessity/sufficiency, or generalization.

## Frozen design choices that cannot be silently revised

- all 40 units, 20 pairs, four seeds, and 160 tasks;
- baseline, target projection exchange, and orthogonal sham;
- all 32 LFE tokens with leave-one-pair-out directions;
- no v2 best-token or favorable-pair selection;
- one current-transaction baseline rather than historical baseline reuse;
- intervention at `valid_face_emb` before all 21 Perceiver sites;
- unchanged spatial reference-latent route and weights;
- exactly seven sampled decoded indices per video;
- two independent blinded annotators and adjudication;
- role-aligned target-minus-sham primary pair effect;
- all ten pair effects per attribute or no reduced-panel aggregate;
- no p-values, confidence intervals, or cross-attribute ranking;
- expected and hard compute ceilings, privacy rules, and fail-closed policy.

Any scientifically meaningful change requires a new versioned preregistration
before implementation or result access.

## Prohibited shortcuts

- Do not treat the preregistration as execution authority.
- Do not load outcomes to tune the intervention or choose token indices.
- Do not restore token-direction v1 run-001 or any other failed/partial run.
- Do not replace historical run-003 values with current-process values or
  relax the frozen numerical tolerance.
- Do not reopen the scalar 13-frame × 36-cell family automatically.
- Do not assign run-level fallback messages to units, pairs, roles, attributes,
  seeds, or conditions.
- Do not alter seed, reference, prompt, scheduler, guidance, resolution,
  precision, frame indices, labels, thresholds, exclusions, or intervention
  dose because of observed results.
- Do not impute, delete failures, select a favorable subset, or selectively
  regenerate.
- Do not persist raw identity, EVA, LFE, direction, latent, keypoint, aligned
  image, or private-reference material in Git.
- Do not publicly release reference-corresponding generated videos.

## First safe action after bootstrap

If the researcher separately authorizes the immediate gate, implement the
runner/instrumentation/analyzer/verifier, run CPU-only synthetic tests, and run
a no-weight dry-run only. Freeze and independently verify that package, then
stop for formal input-audit authorization.
