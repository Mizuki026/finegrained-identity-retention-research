# Mechanism trace phase-S execution review gate v1

Status: **explicit researcher approval required; phase-S model loading and GPU execution blocked**.

## Proposed scientific execution

- Frozen universe: all 40 formal reference units, with eyeglasses and facial
  hair analyzed separately.
- Frozen seeds: all four existing seeds per unit.
- Condition: unchanged baseline only; no zero-control and no permutation.
- Exact ceiling: 160 trajectories and 8,000 Transformer steps.
- Coverage: all 50 scheduler positions and all 21 local injection sites.
- Device: one process on CUDA device index `0`.
- Proposed phase ceiling: 24 GPU-hours. Together with the observed 1.886
  phase-E hours, this remains below the previously accepted 72-hour total.
- Proposed runtime directory:
  `/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_001`.
- Output remains latent-only with bounded summaries; no video decode, video
  save, raw tensor persistence, or reference-image copying.

## Prespecified reporting after execution

- Primary representation readout: ten leave-one-matched-pair-out margins at
  `valid_face_emb_mean_token_l2_normalized`, with correct/tie/wrong counts.
- Eight upstream representation stages remain secondary diagnostics.
- Primary injection description: the complete fixed 3×3
  block-group×denoising-group grid of `relative_residual_rms`, separately for
  unconditional and text CFG branches.
- Aggregation order remains task cell → four-seed unit mean →
  positive-minus-control matched-pair difference → all ten finite-panel values
  and descriptive summaries.
- No p-values, inferential confidence intervals, selective cells, cross-
  attribute ranking, causal claims, population claims, model-wide claims, or
  frame-independent claims are permitted.

## Decisions requested

1. Accept phase E as an engineering pass based on the independent verifier and
   outcome-blind post-run audit.
2. Accept the code-bound CUDA/bfloat16 execution evidence without adding and
   rerunning a new per-tensor dtype/device metadata trace. A rerun would exceed
   the frozen 184-trajectory total and therefore requires a separate revised
   budget and protocol if preferred.
3. Authorize or reject the exact 160 baseline trajectories, 8,000 steps, CUDA
   index `0`, 24-hour phase ceiling, and runtime directory above.
4. Reconfirm that zero-local-residual engineering rows are excluded from all
   phase-S scientific analysis.
5. Reconfirm the frozen output/privacy policy and the complete, non-selective
   primary reporting plan.
6. Reconfirm that passing phase S would still support fixed-panel descriptive
   evidence only, not causal, population, model-wide, frame-independent, or
   cross-attribute conclusions.

## Authorization construction after approval

A new Git-external authorization JSON must bind the post-phase-E research
commit, clean research and ConsisID repositories, all six runtime code hashes,
the independently verified phase-E artifact path/SHA256, exact phase-S output
directory, CUDA index, 160/8,000 ceilings, 24-hour ceiling, and an explicit GPU
approval boolean.

## Stop rule

Do not create the phase-S authorization or start a scientific model run until
all six decisions are explicitly accepted. No method, sample, seed, threshold,
metric, exclusion rule, or retry policy may change at this gate.
