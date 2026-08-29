# Prospective mechanism–outcome pair-level linkage protocol draft v1

Status: **draft only; researcher review required; no computation or implementation authorized**.

## 1. Purpose

This proposed follow-up asks whether fixed-pair heterogeneity in already frozen
ConsisID mechanism summaries co-varies descriptively with fixed-pair
heterogeneity in already frozen generated-video attribute retention.

It is not an intervention, mediation analysis, causal test, population study,
model-wide evaluation, frame-independent analysis, or cross-attribute ranking.
It will not identify which conditioning route caused retention. A positive,
zero, or negative association cannot establish route necessity, sufficiency,
absence, or a model bottleneck.

This document does not authorize analysis. It freezes no result and performs no
metric computation. Implementation, dry-run, and CPU execution each require a
later explicit researcher decision.

## 2. Fixed analysis units and separation by attribute

- Analyze eyeglasses and facial hair separately.
- The independent descriptive unit is the frozen `formal_pair_id`.
- Each attribute contains exactly ten planned pairs: `FEY_01..FEY_10` and
  `FFH_01..FFH_10`.
- Seeds, sampled frames, Transformer blocks, scheduler positions, CFG branches,
  and representation stages are repeated measurements, not independent units.
- No pair, seed, frame, stage, or injection cell may be removed because of its
  outcome or mechanism value.
- No value may be imputed. An unexpected missing or duplicate key stops the
  future analysis before an output is finalized.

## 3. Proposed frozen outcome variables

### 3.1 Eyeglasses

Use only the frozen human-consensus column `human_positive_minus_control` from
`repaired_eyeglasses_matched_seed_pairs_v1.csv`. For each `formal_pair_id`, the
proposed pair-level outcome is the arithmetic mean of its four frozen seed-pair
values, with all four seeds required.

The automatic YuNet+CLIP columns are not used in the linkage outcome. They
remain secondary measurement-convergence evidence outside this proposed
analysis. The original low-coverage automatic eyeglasses result is excluded
from the definition because it was already judged unsuitable as the main
eyeglasses description, not because of any linkage result.

### 3.2 Facial hair

Use the existing `primary_positive_minus_control` value for each `FFH_*`
`formal_pair_id` in the frozen `attribute_pair_contrasts_v1.csv`. Do not
reconstruct or replace the already frozen reference-unit aggregation.

The known fixed-panel heterogeneity and unobservability remain part of the
outcome definition and interpretation. No low-coverage pair is deleted and no
missing frame is filled.

## 4. Proposed mechanism variables

### 4.1 Primary mechanism variable

For each attribute and `formal_pair_id`, use the already frozen `margin` at
stage `valid_face_emb_mean_token_l2_normalized` from
`representation_margins_v1.csv`.

This is the preregistered primary Phase-S representation readout. It is one
leave-one-pair-out directional margin per fixed pair. No direction is refit and
no representation vector or raw identity tensor is reopened.

### 4.2 Secondary representation diagnostics

Use all eight already frozen secondary stages as a complete family:

1. `insightface_l2_normalized`
2. `eva_head_l2_normalized`
3. `eva_hidden_0_patch_mean_l2_normalized`
4. `eva_hidden_1_patch_mean_l2_normalized`
5. `eva_hidden_2_patch_mean_l2_normalized`
6. `eva_hidden_3_patch_mean_l2_normalized`
7. `eva_hidden_4_patch_mean_l2_normalized`
8. `image_latent_first_frame_spatial_mean_l2_normalized`

All eight must be reported or all must remain uncomputed. No favorable EVA
stage may be selected or promoted to primary after inspection.

### 4.3 Secondary injection diagnostics

Use all 18 already frozen pair-level `positive_minus_control` values per
attribute from `injection_pair_3x3_v1.csv`: both CFG branches crossed with all
nine prespecified block-by-denoising cells.

The complete grid must be reported without selecting a cell, smoothing over
cells, or treating cells as independent replicates. These values describe
`relative_residual_rms`; they do not measure residual attribute content.

## 5. Proposed association estimand

For each attribute separately, the primary descriptive estimand is Spearman's
rank correlation between the ten primary LFE margins and the ten pair-level
outcome values.

- Ranks use average ranks for ties.
- No p-value or confidence interval is computed.
- If either vector has zero variance, the correlation is recorded as undefined.
- If fewer than ten complete planned pairs remain after key validation, stop
  for researcher review; do not compute a reduced-panel primary result.
- Report `n`, the coefficient, and all ten pseudonymous pair values in an
  external-only audit table.
- Git may contain only the aggregate coefficient, counts, hashes, verification
  records, and fixed-panel interpretation; per-pair joined values require a
  separate privacy decision before publication or Git inclusion.

The exact same Spearman definition may be applied separately to every complete
secondary representation stage and every one of the 18 injection cells. These
are explicitly secondary descriptive diagnostics. They are not a search space
for the largest coefficient.

## 6. Multiplicity and interpretation

- The primary result is one coefficient per attribute at the frozen LFE stage.
- The eight representation-stage and 18 injection-cell coefficients per
  attribute form complete secondary families.
- No null-hypothesis test, p-value, confidence interval, multiplicity-adjusted
  significance claim, threshold, model selection, or cell ranking is allowed.
- Attributes are reported separately; coefficient magnitudes are not compared
  across attributes.
- A positive primary coefficient would support only fixed-panel co-variation
  under this readout. It would not show that LFE information caused retention.
- A near-zero or negative coefficient would not show that the LFE or local
  route lacks usable information.
- Secondary coefficients cannot localize a mechanism because the design is
  observational, representations differ, and injection magnitude is not
  attribute content.

## 7. Fallback handling

The 76 InsightFace-to-aligned-face fallback messages remain unmapped at task
level. They are not assigned to pairs, modeled, excluded, or rerun. The future
linkage report must repeat this as a run-level preprocessing limitation. No
fallback-stratified result is permitted from run-003.

## 8. Input binding and key validation

Before any future computation, an independent input audit must verify every
path, byte count, SHA256, schema header, file mode, and exact key set. The join
key is only `(attribute, formal_pair_id)`; seed values are aggregated only for
the eyeglasses human-consensus outcome as defined above.

The future audit must establish:

- ten unique planned pair IDs per attribute in each required primary source;
- exactly four unique eyeglasses seed indices per pair;
- exactly one primary LFE margin per pair;
- exactly one row per pair, CFG branch, block group, and denoising group in the
  injection pair table;
- no unexpected attribute, role, seed, stage, branch, or grid label;
- no non-finite numeric input.

Any mismatch stops the work and returns to researcher review. Files are never
corrected in place.

## 9. Privacy and output policy

- No reference image, generated video, decoded frame, raw embedding, raw
  activation, or identity name enters the linkage package.
- Inputs remain read-only and are never copied into Git.
- A future implementation must write to a new external runtime directory and
  must never modify the Phase-S run-003 runtime or analysis directories.
- Joined pseudonymous pair tables stay external-only and become read-only after
  verification.
- Publication of per-pair traces remains separately gated.

## 10. Compute and execution boundary

The proposed analysis is CPU-only and uses only small frozen CSV files. A future
implementation must set `CUDA_VISIBLE_DEVICES=''`, import no ML framework, load
no weights, and make no network call. It creates no trajectory and consumes no
GPU budget.

The present authorization covers protocol drafting only. It does not authorize:

- analyzer or verifier implementation;
- dry-run or input audit execution;
- association computation or joined output creation;
- model loading, GPU use, regeneration, fallback rerun, or new measurement.

## 11. Required future gates

Before implementation, the researcher must approve the exact outcome
definitions, primary estimand, complete secondary families, missingness and
privacy rules, and claim boundary in this draft.

After implementation, a separate package must bind source code hashes, input
hashes, output schemas, a no-weight dry-run, independent verifier, external
output directory, and Git commit. CPU execution then requires another explicit
authorization. Any future GPU intervention remains a separate preregistration.
