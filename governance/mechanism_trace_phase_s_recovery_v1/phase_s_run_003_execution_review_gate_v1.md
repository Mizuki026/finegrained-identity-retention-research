# Mechanism trace Phase-S run-003 execution review gate v1

Status: **explicit researcher GPU approval required; final execution authorization, model loading, and GPU execution blocked**.

## Verified recovery basis

- Run 002 ended after an unexpected instance power loss, not a protocol stop.
- Thirty-two trajectories completed; the thirty-third was interrupted inside
  scheduler step index 46. The conservative attempted-step count is 1,647.
- Run 002 has no execution summary, finalized CSVs, or representation margins.
- Same-directory continuation is unsupported because runtime artifacts are
  exclusive, the output directory must be empty, and the representation
  readout existed only in process memory.
- All run-002 artifacts remain excluded from scientific analysis and may not be
  reused, deleted, overwritten, or mixed with run 003.

## Proposed clean execution

- Frozen scientific universe: all 40 formal units, analyzed separately for
  eyeglasses and facial hair.
- Frozen seeds: all four existing seeds per unit.
- Condition: unchanged baseline only.
- Exact fresh execution: 160 trajectories and 8,000 Transformer steps.
- Conservative cumulative ceiling including Phase E and both aborted runs:
  219 trajectory attempts and 10,947 Transformer steps.
- Coverage: all 50 scheduler positions and all 21 local injection sites.
- Device: one process on CUDA device index `0`.
- Phase ceiling: 24 GPU-hours; total accepted ceiling remains 72 GPU-hours.
- New output directory:
  `/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003`.
- Output remains bounded latent summaries only: no decoded/saved videos, raw
  tensors, identity embeddings, or copied reference images.

## Frozen reporting retained

- Primary representation readout remains
  `valid_face_emb_mean_token_l2_normalized` with ten
  leave-one-matched-pair-out margins and correct/tie/wrong counts.
- Eight other representation stages remain secondary diagnostics.
- Image-latent unit vectors retain the exact four-seed arithmetic mean without
  a second normalization.
- Primary injection description remains the complete fixed 3×3
  block-group×denoising-group grid of `relative_residual_rms`, separately for
  unconditional and text CFG branches.
- No selective cells, retries, replacements, p-values, inferential confidence
  intervals, threshold changes, cross-attribute ranking, or partial-run salvage
  are permitted.

## Six decisions requested after package verification

1. Accept the outcome-blind run-002 power-loss audit and immutable exclusion of
   all run-002 partial artifacts.
2. Accept that run 003 must be a complete fresh execution and that no run-001
   or run-002 trajectories may be reused.
3. Accept cumulative ceilings of 219 trajectory attempts and 10,947
   Transformer steps, with the unchanged 72 GPU-hour total ceiling.
4. Explicitly approve or reject one-process CUDA-0 execution of 160 fresh
   trajectories and 8,000 steps at the exact run-003 directory with a
   24 GPU-hour phase ceiling.
5. Reconfirm the frozen task universe, seeds, metrics, thresholds, exclusions,
   output/privacy rules, non-selective reporting, and no-retry policy.
6. Reconfirm that a passing run supports fixed-panel descriptive evidence only,
   not causal, population, model-wide, frame-independent, or cross-attribute
   conclusions.

## Authorization construction after approval

The Git-external pending authorization is intentionally non-executable. Only
after all six decisions are explicitly accepted may the final
`phase_s_run_003_execution_authorization_v1.json` be created. It must bind the
reviewed research commit, clean research and ConsisID repositories, all six
runtime code hashes, Phase-E verification, the correction and recovery package
verifications, the exact run-003 directory and ceilings, CUDA index `0`, and an
explicit GPU approval boolean.

## Stop rule

Do not create the final executable authorization, create the run-003 output
directory, load the model, or use GPU until all six decisions are explicitly
approved.
