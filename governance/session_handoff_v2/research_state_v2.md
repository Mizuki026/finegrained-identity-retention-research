# Research session handoff v2

- Handoff ID: `finegrained_identity_retention_session_handoff_v2`
- Created: 2026-08-29 UTC
- Status: `READY_FOR_NEW_WINDOW_READ_ONLY_BOOTSTRAP_AND_LINKAGE_DESIGN_REVIEW`
- Source-state repository commit: `ff465f9d3e1707d3b70f9810a8405dff96297e5d`
- Source-state branch: `measurement-repair-v1`
- Source-state working tree: clean
- Source-state relation to `origin/measurement-repair-v1`: ahead by two commits

This handoff supersedes `session_handoff_v1` as the current compact session
state. It does not supersede any frozen experiment, CSV/JSON artifact, hash, or
Git history. If this summary conflicts with a frozen source, the frozen source
wins and work must stop for review.

## 1. Research objective and present boundary

The project studies fine-grained identity-attribute retention in
reference-conditioned video generation using ConsisID. Output-level baseline
and measurement repair are complete. Static code mapping and the first bounded
mechanism-trace window are also complete. The current transition is to review a
prospective CPU-only design that could descriptively link existing pair-level
mechanism summaries to existing pair-level generated outcomes.

The intended longer progression remains mechanism analysis, followed—only if
supported by prospectively reviewed evidence—by a separately designed
training-free intervention and ablation. Fine-tuning and LoRA are not currently
planned. Reference-linked generated videos will not be publicly released.

## 2. Evidence vocabulary

- **Verified fact:** directly supported by a frozen artifact, its SHA256, or an
  independent verification record.
- **Current observation:** a descriptive pattern in the fixed finite panel.
- **Working hypothesis:** an accepted explanation class that has not been
  established by intervention or outcome linkage.
- **Research decision:** an explicit researcher-approved scope,
  interpretation, or authorization boundary.

Linear readability is not causality. Residual magnitude is not attribute
content. A detector-coverage repair is not generation-quality improvement. A
fixed-panel association, if later authorized, will not identify a model
bottleneck or route necessity/sufficiency.

## 3. Authoritative locations and Git state

- Research repository:
  `/root/autodl-tmp/finegrained/research_pipeline`
- Formal runtime:
  `/root/autodl-tmp/finegrained/formal_experiment_v1_runtime`
- Mechanism runtime:
  `/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime`
- Phase-S run-003 runtime:
  `/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003`
- Phase-S run-003 analysis:
  `/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003_analysis_v1`
- ConsisID repository:
  `/root/autodl-tmp/consisid-smoketest/ConsisID`
- Python environment:
  `/root/autodl-tmp/consisid-smoketest/env/bin/python`
- ConsisID commit:
  `60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e`
- Research source-state commit:
  `ff465f9d3e1707d3b70f9810a8405dff96297e5d`

At source state, both Git worktrees were clean. The Phase-S run-003 runtime and
analysis directories were mode `0555`; checked key files were mode `0444`.

The commit that adds this v2 handoff will necessarily make the new-window HEAD
different from the source-state commit. That difference is expected only if
the intervening commit contains this handoff package. It must be inspected, not
misreported as artifact corruption.

## 4. Verified formal output and measurement state

The frozen formal design contains two attributes, ten matched reference pairs
per attribute, 40 reference units, four seeds per unit, and 160 generation
tasks. All 160 formal videos completed without seed replacement, manual
substitution, or result-dependent favorable rerun. Frozen engineering integrity
covered all 160 videos and 7,840 frames and passed independent verification.

### Eyeglasses

The original SCRFD-based automatic instrument had inadequate face-detection
coverage and is not the primary eyeglasses description. The accepted primary
finite-panel description is frozen human consensus:

- 40 matched seed-pair differences: 33 positive, seven zero, zero negative;
- mean difference `0.825` and median `1.0`;
- fixed panel only.

The audited YuNet+CLIP route remains secondary convergent measurement evidence
only. Detector repair improved measurement availability; it did not improve
generation and did not locate an internal ConsisID mechanism.

### Facial hair

The accepted conservative fixed-panel description is:

- ten planned pair contrasts retained;
- mean matched positive-minus-control difference `0.2052380952`;
- median `0.0`, range `[-1.0, 1.0]`;
- substantial unobservability and heterogeneous pair differences.

It does not support a population, model-wide, causal, or cross-attribute
conclusion.

## 5. Verified ConsisID structure mapping

The read-only static mapping at ConsisID commit `60429e4...` established two
reference-conditioning routes:

1. The local identity-token route combines a 512-D InsightFace component, a
   768-D EVA head component, and five EVA token maps in the Local Facial
   Extractor. It produces 32 x 2048 identity tokens and injects Perceiver
   cross-attention residuals at 21 sites after Transformer blocks
   `0,2,...,40`.
2. A separate spatial reference-image VAE latent contributes the nonzero first
   latent frame and zero-padded later frames, concatenated with the noisy video
   latent before patch embedding.

`local` describes the origin of face-crop features, not a spatial mask over
video tokens. There is no target-attribute mask in the mapped route. The static
mapping alone did not establish information availability, suppression,
causality, or a bottleneck.

## 6. Mechanism-trace design and engineering history

The prospectively accepted trace used all 40 reference units, four seeds, 160
scientific trajectories, all 50 scheduler positions, nine reference-side
readouts, and 21 local injection sites. The primary representation endpoint was
matched-pair directional ranking at the mean-pooled LFE output. The primary
injection metric was `relative_residual_rms`, reported as a complete 3 x 3
block-by-denoising grid separately for both CFG branches.

Phase E completed 24 engineering trajectories and 1,200 Transformer steps in
approximately 1.886 GPU-hours. Repeat and zero-local-residual engineering
controls passed exactly. Phase E produced no scientific retention result.

Two incomplete Phase-S histories remain frozen and excluded:

- run-001 stopped after two attempted trajectories and 100 steps because a
  sampled image latent had incorrectly been required to remain invariant
  across seeds. The correction retained all stages, metrics, thresholds, and
  four seeds; it changed only the invalid invariance treatment.
- run-002 was interrupted by external power loss after 33 attempted
  trajectories, 32 completed trajectories, and 1,647 attempted steps. Its
  partial products are immutable, never reused, and not analyzed.

Neither aborted run may be revived, pooled, repaired, or selectively reused.

## 7. Verified Phase-S run-003 execution

Run-003 restarted the complete scientific panel from the beginning and passed
independent runtime, outcome-blind post-run, analysis, and package verification:

- 160/160 tasks and 8,000/8,000 Transformer steps;
- 336,000 bounded injection rows;
- 160 route rows and 160 complete task-status rows;
- 180 representation margins;
- 2,880 task-level and 360 pair-level injection-grid rows;
- complete 36-cell finite-panel injection table;
- 18 attribute-by-stage representation summaries;
- phase runtime `12.5001125163` GPU-hours, below the 24-hour phase ceiling;
- accepted cumulative ceiling: 219 trajectories and 10,947 steps;
- accepted total GPU ceiling remained 72 hours.

No decoded media, raw tensor, retry, replacement, partial old-run reuse,
inferential test, confidence interval, or cross-attribute ranking entered the
result package.

The run emitted 76 built-in InsightFace-to-aligned-face fallback messages.
They lack task identifiers and therefore remain an unassigned run-level
preprocessing limitation. All 160 tasks were retained; no exclusion,
regeneration, imputation, or post-hoc assignment is permitted.

## 8. Accepted Phase-S observations

### Primary representation readout

- Eyeglasses LFE: 5 correct, 0 tie, 5 wrong; mean margin
  `0.0008087739`, median `0.0001810329`, range approximately
  `[-0.00737778, 0.00973450]`.
- Facial-hair LFE: 6 correct, 0 tie, 4 wrong; mean margin
  `0.0012283967`, median `0.0007300735`, range approximately
  `[-0.00406565, 0.01049384]`.

The accepted primary description is mixed direction with no established
consistent readability at the pooled LFE stage.

### Secondary and injection diagnostics

Several upstream EVA stages have fixed-panel linear directional readability;
for eyeglasses, EVA hidden stages 2–4 are 10/10 under the frozen secondary
readout. EVA results remain secondary stage-specific diagnostics and are not
promoted to primary.

Every one of the 36 fixed injection cells contains both positive and negative
pair differences. The accepted description is small heterogeneous differences
in relative local-residual magnitude. No cell is selected and no localization,
causal mediation, or generation-quality conclusion is supported.

## 9. Accepted scientific interpretation and unverified hypotheses

The researcher accepted the following interpretation:

- upstream EVA linear readability coexists with a mixed primary pooled LFE
  readout in this fixed panel;
- a multi-route, distributed-representation account is the most defensible
  working model, not a verified mechanism or proven bottleneck;
- residual magnitude is not attribute content, so mixed residual magnitudes do
  not establish local-route irrelevance;
- run-003 narrows the mechanism space but does not connect internal traces to
  generated retention outcomes.

The unresolved mechanism hypotheses are therefore:

- attribute information may be reorganized across the 32 LFE tokens and lost
  to the frozen mean-pooled linear readout rather than absent from the full
  representation;
- the separate spatial reference-latent path, the local identity-token path,
  or their interaction may contribute to retention;
- preprocessing heterogeneity may contribute to pair differences;
- residual vector direction, token pattern, or interaction with current video
  tokens may matter even when scalar RMS magnitude does not differ uniformly.

None is verified causally. The Phase-S mechanism-trace window is closed.

## 10. Current draft-only transition

A prospective mechanism–outcome pair-level linkage protocol has been drafted
but not approved for implementation or execution. No outcome has been joined
to a trace and no association coefficient has been computed.

The draft proposes:

- ten `formal_pair_id` units per attribute, with attributes separate;
- eyeglasses outcome: four-seed mean of frozen human
  `human_positive_minus_control`, excluding automatic eyeglasses scores;
- facial-hair outcome: existing frozen `primary_positive_minus_control`;
- primary mechanism variable: frozen
  `valid_face_emb_mean_token_l2_normalized` margin;
- primary descriptive estimand: one Spearman correlation per attribute, using
  average ranks, with no p-value or confidence interval;
- complete secondary families: all eight upstream stages and all 18
  CFG-by-3x3 injection cells per attribute, with no selection;
- stop on any hash, key, duplicate, missingness, or non-finite-value mismatch;
- joined pseudonymous pair tables external-only;
- CPU-only, no weights, no network, and no GPU if later authorized.

This is a proposed design, not a result. Seven researcher decisions in
`open_questions_v2.md` remain unresolved. Until they are answered, analyzer or
verifier implementation, dry-run, input joining, and association computation
are not authorized.

## 11. Frozen and superseded items

- Formal references, prompts, seeds, videos, frame samples, annotations,
  thresholds, metrics, and exclusion rules remain frozen.
- The original low-coverage automatic eyeglasses outcome is preserved but
  superseded as the main eyeglasses description by frozen human consensus.
- YuNet+CLIP is secondary measurement convergence only.
- Phase-S run-001 and run-002 are immutable aborted histories and are excluded
  from scientific analysis.
- Phase-S run-003 is the only completed Phase-S result package and is closed.
- The current linkage materials are explicitly drafts; they are not a new
  frozen analysis and grant no execution authority.

## 12. Prohibited claims and operations

- No causal, population, model-wide, frame-independent, localization, route
  necessity/sufficiency, or cross-attribute conclusion.
- No selective regeneration, seed change, metric or threshold tuning,
  imputation, failed-sample deletion, favorable-stage selection, or favorable
  injection-cell selection.
- No fallback attribution, fallback-based exclusion, or fallback rerun from
  run-003.
- No modification of frozen runtime or analysis products.
- No input joining, association computation, analyzer implementation, model
  loading, or GPU work under the present draft-only authority.
- No public release of reference-linked generated videos.
- No manuscript drafting unless separately requested.

## 13. New-window bootstrap and next gate

The new window must first perform a read-only bootstrap:

1. read all five files in `session_handoff_v2` completely;
2. verify repository branch, HEAD, and working-tree state;
3. verify all 53 `artifact_index_v2.csv` entries by path, bytes, and SHA256;
4. if HEAD differs from `ff465f9...`, inspect intervening commits and accept the
   difference only if it is solely the v2 handoff commit;
5. verify the Phase-S runtime and analysis directories remain read-only;
6. stop immediately on any mismatch.

After a successful bootstrap, the only current research gate is resolution of
the seven linkage-design decisions. If all seven are accepted, the next
permitted stage may be limited to analyzer/verifier writing, CPU-only tests,
and a no-weight dry-run. It still must not join outcome and mechanism data or
compute an association without another explicit authorization.
