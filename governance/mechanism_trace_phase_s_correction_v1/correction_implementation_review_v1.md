# Mechanism trace phase-S protocol-correction implementation review v1

Status: **correction implemented and independently verified; model loading and GPU execution remain blocked**.

## Verified facts

- The correction authorization is bound to abort freeze
  `0858e7516193fed99ce45e46f8b25b87051b9670db90cd30f5b2899abaf99548`
  and explicitly prohibits model loading, GPU execution, replacement
  authorization construction, and reuse of run-001 partial artifacts.
- The nine frozen representation stages remain unchanged. The eight
  deterministic reference stages retain cross-seed `allclose` checks.
- The sampled image-latent stage now requires exactly the four frozen seeds,
  takes their arithmetic mean after per-seed L2 normalization, and does not
  apply a second normalization.
- Duplicate scientific unit×seed observations, missing frozen seeds, unexpected
  seeds, metadata drift, deterministic-stage drift, and stage-universe drift
  all fail closed.
- Engineering same-seed repeat and zero-route behavior remains supported.
- The matched-pair directional-ranking formula, `1e-8` tie rule, 180-row
  representation structure, injection metrics, 3×3 aggregation, CFG branch
  separation, task universe, and output/privacy rules are unchanged.
- All 17 mechanism-trace CPU tests passed. The independent correction verifier
  passed and did not import Torch in its own process.
- The no-weight dry-run contains the unchanged 184-task fresh plan and 9,200
  planned Transformer steps. It reports no Torch or ConsisID import and passed
  the existing independent dry-run verifier.
- The 15-entry correction evidence manifest passed independent path, byte, and
  SHA256 verification.
- Of the six runtime files bound by an execution authorization, only
  `mechanism_trace_instrumentation_v1.py` changed. No ConsisID source or weight
  changed.

## Resource accounting

The fresh run plan remains 24 phase-E plus 160 phase-S trajectories. Historical
attempt accounting additionally retains the two immutable run-001 abort
attempts, producing a revised cumulative ceiling of 186 trajectories and 9,300
Transformer steps. No attempted trajectory is reused or credited toward the
future 160-task scientific run.

The existing 72 GPU-hour total ceiling remains unchanged. The proposed run-002
phase ceiling remains 24 GPU-hours on one CUDA device.

## What this establishes

The correction reconciles the frozen four-seed aggregation with ConsisID's
seed-sampled reference-image VAE latent while preserving fail-closed checks for
the deterministic stages. This is an engineering measurement-mechanism result
only.

It does not establish identity retention, attribute retention, an attribute
ranking, a causal route, a bottleneck, a generation-quality improvement, or a
population/model-wide/frame-independent conclusion.

## Safety state

No run-002 execution authorization exists. The run-002 output directory does
not exist. No model was loaded and no GPU compute was used during correction,
testing, dry-run, or independent verification.
