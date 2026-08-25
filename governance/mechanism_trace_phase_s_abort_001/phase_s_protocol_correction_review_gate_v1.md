# Mechanism trace phase-S protocol-correction review gate v1

Status: **explicit researcher approval required; source changes and all GPU execution blocked**.

## Decisions requested

1. Accept the outcome-blind diagnosis that run 001 stopped because the
   implementation incorrectly required a seed-sampled reference-image VAE
   latent to be invariant across the four frozen seeds.
2. Accept the minimal reconciliation: keep the existing cross-seed
   `allclose` assertion for the eight deterministic reference stages; for the
   image-latent stage, collect exactly four frozen seed-specific L2-normalized
   vectors per unit and use their arithmetic mean without a second
   normalization.
3. Reconfirm that all nine stages, the primary
   `valid_face_emb_mean_token_l2_normalized` readout, matched-pair directional
   ranking, `1e-8` tie rule, 3×3 injection analysis, task universe, seeds, and
   privacy/output rules remain unchanged.
4. Authorize instrumentation/test changes, CPU-only tests, and a no-weight
   dry-run only. Required tests must cover deterministic-stage drift,
   seed-specific image-latent acceptance, duplicate/missing seeds, exact
   four-seed unit aggregation, and unchanged 180-margin output structure.
5. Accept that run 001 remains immutable and excluded from scientific analysis;
   a future clean run must use
   `/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_002`.
   Approve revised cumulative attempt ceilings of 186 trajectories and 9,300
   Transformer steps while retaining one GPU and the accepted 72 GPU-hour
   total ceiling.
6. Reconfirm that after implementation and independent CPU/no-weight
   verification, a new code-bound execution package and another explicit
   researcher approval are required before creating a replacement Phase S
   authorization or loading the model.

## Stop rule

Do not modify the runtime code, create a replacement execution authorization,
reuse or analyze run-001 partial trajectories, load the model, or start a GPU
run until all six decisions are explicitly accepted.
