# Research session handoff v3

- Handoff ID: `finegrained_identity_retention_session_handoff_v3`
- Created: 2026-09-04 UTC
- Status: `READY_FOR_NEW_WINDOW_READ_ONLY_BOOTSTRAP_AND_CONTROLLED_INTERVENTION_IMPLEMENTATION_GATE`
- Source-state repository commit: `9238c816543f71436dbd7e3535c9ef663cd32338`
- Source-state branch: `main`
- Source-state working tree: clean
- Source-state relation to `origin/main`: ahead 31, behind 0
- Source-state `origin/main`: `66c990b3e2451b69e3fda02bfd977c9b2f357476`

This handoff supersedes `session_handoff_v2` as the compact current-session
state. It does not supersede or rewrite any frozen CSV/JSON, SHA256, runtime,
protocol, failure history, or Git commit. Frozen artifacts and Git history are
the facts of record. If this summary conflicts with a frozen source, stop and
use the frozen source.

## 1. Research objective and current transition

The project studies fine-grained identity-attribute retention in
reference-conditioned video generation using ConsisID. It asks what attributes
are retained, how attribute-related structure is readable along the real model
path, and whether a prospectively controlled intervention can test contribution
without overstating causality.

The formal output-measurement, bounded mechanism-trace, CPU linkage, scalar
readout, and outcome-blind token-direction observation windows are complete and
closed. The current transition is to a separately preregistered controlled LFE
projection-exchange intervention. Only its design has been frozen. No
intervention implementation or execution is currently authorized.

Fine-tuning and LoRA remain outside the current plan. Public release of
reference-corresponding generated videos remains prohibited.

## 2. Evidence vocabulary

- **Verified fact:** directly supported by a frozen artifact, bound SHA256, or
  independent verification.
- **Current fixed-panel observation:** a descriptive pattern over the exact
  ten pairs per attribute; not a population statement.
- **Accepted working model:** a researcher-accepted explanation framework that
  has not been causally verified.
- **Unverified hypothesis:** a testable mechanism possibility not established
  by the existing evidence.
- **Research decision:** a frozen choice about scope, interpretation,
  sequencing, or authorization.

Linear readability is not attribute content or causality. Association is not
mediation. Residual magnitude and mean H–R cosine are compressed observables,
not complete mechanism descriptions. Learned LFE token indices are not image
regions or independent samples.

## 3. Authoritative locations and source state

- Research repository:
  `/root/autodl-tmp/finegrained/research_pipeline`
- Formal runtime:
  `/root/autodl-tmp/finegrained/formal_experiment_v1_runtime`
- Phase-S runtime:
  `/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003`
- Phase-S analysis:
  `/root/autodl-tmp/finegrained/mechanism_trace_v1_runtime/phase_s_run_003_analysis_v1`
- Formal linkage runtime:
  `/root/autodl-tmp/finegrained/mechanism_outcome_linkage_v1_runtime/run_001`
- Cosine linkage runtime:
  `/root/autodl-tmp/finegrained/mechanism_cosine_outcome_linkage_v1_runtime/run_001`
- Quantile linkage runtime:
  `/root/autodl-tmp/finegrained/mechanism_token_quantile_linkage_v1_runtime/run_001`
- Direct-hook diagnostic runtime:
  `/root/autodl-tmp/finegrained/mechanism_token_direction_direct_hook_diagnostic_v1_runtime/run_001`
- Preprocessing-repeatability runtime:
  `/root/autodl-tmp/finegrained/mechanism_token_direction_preprocessing_repeatability_v1_runtime/run_001`
- Token-direction v2 runtime:
  `/root/autodl-tmp/finegrained/mechanism_token_direction_v2_runtime/run_001`
- ConsisID repository:
  `/root/autodl-tmp/consisid-smoketest/ConsisID`
- Python environment:
  `/root/autodl-tmp/consisid-smoketest/env/bin/python`
- ConsisID commit:
  `60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e`

At source state, both Git worktrees were clean. All eight runtime/analysis
directories listed for bootstrap verification were mode `0555`, with every
contained file mode `0444`.

The commit that adds `session_handoff_v3` will make the next-window HEAD differ
from `9238c816...`. That is expected only if the intervening commit contains
this handoff package. Inspect the diff; do not interpret the expected handoff
commit as data corruption.

## 4. Verified formal output and measurement state

The frozen formal panel contains two attributes, ten matched pairs per
attribute, 40 reference units, four seeds per unit, 160 generation tasks, 49
frames per video, and 160 completed videos. No seed, reference, prompt, task,
or failed sample was changed or selectively replaced.

### Eyeglasses

The primary description is frozen human consensus, not the original
low-coverage SCRFD automatic result:

- 40 seed-pair differences: 33 positive, seven zero, zero negative;
- mean difference `0.825`, median `1.0`;
- fixed finite panel only.

YuNet+CLIP is secondary measurement-convergence evidence. Detector repair
improved measurement availability; it did not improve generation or identify a
mechanism.

### Facial hair

All ten planned pair contrasts were retained:

- mean positive-minus-control difference `0.2052380952`;
- median `0.0`, range `[-1.0,1.0]`;
- substantial unobservability and heterogeneous pair effects.

This does not support population, model-wide, causal, or cross-attribute
claims.

## 5. Verified ConsisID mapping and Phase-S trace

At the frozen ConsisID commit, two reference-conditioning routes were mapped:

1. The local identity route combines InsightFace, EVA head, and five EVA maps
   in the Local Facial Extractor, producing 32 × 2048 learned identity tokens.
   They enter 21 Perceiver cross-attention residual sites after Transformer
   blocks `0,2,...,40`.
2. The spatial route uses a reference-image VAE latent in the first latent
   frame with zero-padded later reference frames, concatenated before patch
   embedding.

There is no frozen target-attribute mask. `local` refers to face-crop feature
origin, not a spatial mask over video tokens.

Phase-S run-001 and run-002 remain immutable aborted histories. Run-003 is the
only complete Phase-S scientific package:

- 160/160 tasks and 8,000/8,000 Transformer steps;
- 336,000 bounded injection rows;
- 180 representation margins;
- 360 pair-level injection-grid rows and all 36 finite-panel cells;
- runtime `12.5001125163` GPU-hours;
- independent runtime, post-run, analysis, and package verification passed;
- no decoded media or raw tensor was persisted.

The 76 unstructured InsightFace fallback messages have no task identifiers.
They remain a run-level limitation only and cannot be assigned, modeled,
excluded, or rerun.

Run-003 observations remain:

- pooled LFE eyeglasses: 5 correct, 0 tie, 5 wrong;
- pooled LFE facial hair: 6 correct, 0 tie, 4 wrong;
- upstream EVA stages show stage-specific secondary readability;
- every one of the 36 residual-RMS cells contains both pair-difference signs.

No grid cell was selected and no bottleneck or location was established.

## 6. Completed CPU mechanism–outcome linkage

The first formal input-audit run failed because its auditor demanded the
facial-hair target field in all 20 source rows. A single prospective correction
was frozen after confirming all nine missing fields were non-target
eyeglasses rows and zero were target facial-hair rows. Run-001 is immutable and
nonreusable. A new run-002 repeated all four source audits and passed.

Formal linkage then completed on CPU with no model or GPU:

- 20 outcome rows;
- 20 primary joined rows;
- 160 representation-secondary joined rows;
- 360 injection-secondary joined rows;
- 2 primary, 16 representation-secondary, and 36 injection-secondary
  Spearman coefficients, all independently recomputed.

Primary pooled-LFE Spearman coefficients over ten pairs were:

- eyeglasses: `0.12060453783110545`;
- facial hair: `0.4939912655897707`.

These are fixed-panel descriptive covariation only. The complete secondary
representation family changes sign and magnitude across stages. The spatial
reference-latent association is positive in both panels, but this does not
isolate the spatial route or establish compensation.

For scalar relative residual RMS, all 18 eyeglasses grid associations are
positive (`0.160806...` to `0.415416...`). Facial hair has 14 negative, two
zero, and two small positive associations (`-0.337665...` to `0.006253...`).
This difference is descriptive and does not rank the attributes.

## 7. Completed cosine and token-RMS quantile linkages

The complete mean tokenwise H–R cosine family contains 36 secondary
coefficients. Eyeglasses has 16 negative and two positive; facial hair has 12
negative, two zero, and four positive. Mean cosine is direction-sensitive
relative to H but is not an attribute direction. Similar CFG-branch ranks do
not establish branch equivalence.

The complete token-RMS quantile family contains 108 independently recomputed
secondary coefficients:

- eyeglasses: 54 positive, zero negative, range
  `[0.0670025210,0.2814105883]`;
- facial hair: 30 positive, 24 negative, range
  `[-0.4564729416,0.1375671879]`.

q10, q50, and q90 have similar coarse sign/grid structure. This is compatible
with a broad token-magnitude ranking shift rather than a q90-only pattern, but
does not prove uniform participation or exclude sparse attribute-relevant
tokens. The global scalar linkage window is formally closed. The unexecuted
13-frame × 36-cell family remains closed.

## 8. Token-direction v1 failure and bounded diagnostics

Token-direction Phase E passed as engineering only: eight units, 24 operations,
eight one-step Transformer controls, no trajectories, and about `0.0264`
GPU-hours.

Scientific token-direction v1 run-001 completed 160 transient reference
extractions but failed its frozen historical pooled-LFE replication gate at
the first reported key `eyeglasses/FEY_01`. It persisted no 640-margin family,
no aggregate scientific output, and no raw tensor. It is permanently failed
and nonreusable.

The complete 40-unit direct-versus-one-step-hook diagnostic then found:

- 40/40 direct-hook comparisons bit-exact;
- 0/20 current hooked pooled values strictly matched historical run-003;
- 20/20 signs matched;
- `0.0736021` GPU-hours, no trajectory and no outcome access.

The complete fresh-preprocessing repeatability diagnostic found:

- 80/80 within-preprocessing direct repeats bit-exact;
- 40/40 cross-preprocessing LFE comparisons bit-exact;
- both current pooled replicate families agree exactly with each other;
- 0/40 replicate-to-run-003 strict matches and 40/40 sign matches;
- `0.0155626` GPU-hours, no trajectory and no outcome access.

Accepted conclusion: same-input hooks and fresh preprocessing are repeatable in
the bounded current process, but the historical run-003 numerical mismatch
remains an unresolved cross-run measurement-state difference. It is not
evidence of attribute-information loss and does not authorize threshold
relaxation or historical replacement.

## 9. Completed token-direction v2 observation

Token-direction v2 was prospectively separated from failed v1. Run-003 remained
an immutable descriptive comparator, not a validity gate. The complete v2
transaction passed:

- 40 units, 160 fresh preprocessing calls, 200 direct LFE calls;
- 40/40 same-input controls bit-exact;
- 120/120 four-label comparisons bit-exact;
- 20 current pooled margins and 20 historical comparisons;
- 640 token margins, 64 token-panel rows, and 20 pair-token summaries;
- independent in-memory and persisted recomputation passed;
- `0.0165919` GPU-hours, zero Transformer steps and zero trajectories.

Historical comparison retained 0/20 strict numerical matches and 20/20 sign
matches. The current v2 transaction neither repairs nor replaces run-003.

Current outcome-blind token observations:

- eyeglasses: 145 positive and 175 negative token margins; six token indices
  have more than five correct pairs, ten have five, and 16 have fewer than
  five; 29/32 indices and all ten pairs contain both signs; the full family
  includes two 10/10-positive and one 0/10-positive indices;
- facial hair: 173 positive and 147 negative token margins; 16 indices have
  more than five correct pairs, four have five, and 12 have fewer than five;
  all 32 indices and all ten pairs contain both signs.

These are structured readout patterns, not semantic attribute-token labels,
spatial localization, sparse/uniform participation evidence, or causal
contribution. The observational token-direction window is closed.

## 10. Accepted working model and unverified hypotheses

The accepted working model is representation–readout mismatch or
representation reorganization within a multi-path, distributed system. It is
more compatible with the complete evidence than the statement that attribute
information simply disappears at LFE. It is not a verified mechanism.

Still-unverified hypotheses include:

- attribute-relevant structure may be distributed or reorganized across the
  32 LFE tokens and missed by mean pooling or a fixed linear direction;
- vector direction, token pattern, or alignment with current video/query state
  may matter beyond RMS and mean cosine;
- `rms(H)` normalization may contribute to facial-hair differences between
  relative RMS and absolute token quantiles;
- the local identity and spatial reference-latent routes may compensate or
  interact;
- unresolved cross-run initialization, backend, input construction, fallback
  realization, or another measurement state may explain historical numerical
  nonreplication.

No current evidence establishes natural mediation, path compensation,
necessity, sufficiency, localization, a bottleneck, population behavior, or
model-wide behavior.

## 11. Current controlled-intervention preregistration

The next stage is formally preregistered as a complete-family LFE
projection-exchange experiment. It has not been implemented or executed.

Frozen design:

- 40 units, 20 pairs, four seeds, 160 source tasks;
- conditions: new within-transaction `baseline`, complete 32-token
  `target_projection_exchange`, and equal-displacement `orthogonal_sham`;
- 480 planned full trajectories and 24,000 scheduler steps;
- direction for each attribute/pair/token is trained only on the other nine
  pairs; no v2 token, pair, margin, sign, or outcome selects a target;
- exactly 40 fresh preprocessing calls and 40 direct LFE acquisitions before
  trajectories, held transiently in one process;
- intervention at `valid_face_emb` before all 21 local Perceiver injection
  sites; spatial reference latents and all weights remain unchanged;
- target swaps the matched units' raw scalar projection along the held-pair-out
  direction; sham uses the same displacement magnitude in a deterministic
  orthogonal direction;
- new condition-blinded outcome collection; historical outcomes are not reused
  as the intervention baseline;
- seven sampled decoded indices per video, giving 3,360 planned frame states;
- primary pair effect is the role-aligned target-minus-sham difference,
  reported separately over all ten pairs per attribute without p-values or
  confidence intervals;
- expected future scientific cost `35–50` single-GPU hours, hard ceiling 72;
  engineering ceiling 24 one-step executions and two GPU-hours.

A positive effect could support contribution of this particular intervened LFE
directional projection under this fixed intervention and panel. It cannot show
natural mediation, localization, a bottleneck, or path necessity/sufficiency.
A null or negative result cannot prove that LFE lacks attribute information or
that the local route is irrelevant.

## 12. Current authorization boundary

The controlled-intervention protocol, machine-readable preregistration,
13-entry design evidence manifest, static audit, and design freeze are complete.
Current authorized GPU-hours are zero.

Not currently authorized:

- runner, instrumentation, analyzer, or verifier implementation;
- CPU synthetic tests or no-weight dry-run;
- formal input audit;
- reference access, decoding, or preprocessing;
- model or weight loading;
- engineering or scientific GPU work;
- video generation or decode;
- annotation packet construction, annotation, unblinding, or outcome
  construction;
- intervention analysis, association, hypothesis testing, or public release.

The immediate next human gate is a separate authorization limited to
implementation, CPU-only synthetic tests, and no-weight dry-run. Passing that
stage will not authorize formal input audit or any GPU execution.

## 13. Frozen histories and prohibited shortcuts

- Phase-S run-001/run-002, linkage input-audit run-001, and token-direction v1
  scientific run-001 are immutable failure histories and cannot be reused.
- Phase-S run-003 is the sole complete and closed Phase-S result package.
- All scalar linkage and observational token-direction results are closed.
- Do not select a favorable stage, cell, token, pair, role, seed, attribute,
  preprocessing result, or condition.
- Do not alter references, prompts, seeds, scheduler, guidance, resolution,
  frames, thresholds, tie rules, outcomes, exclusions, or frozen files.
- Do not impute, delete failed or unobservable samples, assign fallbacks, or
  selectively rerun.
- Do not treat frames, seeds, tokens, stages, branches, blocks, or timesteps as
  independent samples.
- Do not make causal, population, model-wide, frame-independent, localization,
  natural-mediation, bottleneck, path necessity/sufficiency, compensation, or
  cross-attribute-ranking claims beyond the exact preregistered intervention
  interpretation boundary.

## 14. New-window bootstrap

The new window must first:

1. read all five `session_handoff_v3` files completely;
2. verify branch, HEAD, upstream, remote relation, and both Git worktrees;
3. verify all 67 `artifact_index_v3.csv` paths, byte counts, and SHA256 values;
4. recursively verify all 53 entries in the v2 index referenced by `H001`;
5. verify all eight frozen runtime/analysis trees remain directory mode `0555`
   with every file mode `0444`;
6. inspect any commits after source state `9238c816...`; accept a difference
   only if it is exactly the new `session_handoff_v3` commit;
7. stop immediately and report any mismatch.

After successful bootstrap, report verified facts, current fixed-panel
observations, accepted working model, unverified hypotheses, research decisions,
and the exact next authorization gate separately. Do not implement the
intervention merely because its design is preregistered.
