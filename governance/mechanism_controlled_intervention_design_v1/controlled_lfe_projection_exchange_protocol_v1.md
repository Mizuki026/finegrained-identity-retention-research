# Controlled LFE projection-exchange intervention protocol v1

Status: **formally preregistered after researcher authorization; design only; no implementation or execution authority**.

## 1. Scientific question and causal target

This prospective experiment asks whether a complete-family, leave-one-pair-out
attribute direction at the Local Facial Extractor (LFE) token interface
contributes to the generated positive-versus-control attribute contrast in the
fixed formal panel.

The intervention is deliberately narrower than a mediation analysis. It tests
the effect of replacing one scalar projection at every one of the 32 LFE token
indices, compared with a deterministic direction-matched sham displacement,
while all other frozen generation inputs remain paired. A result in the
predicted direction would support causal contribution of this particular
intervened LFE directional component under this fixed intervention. It would
not establish natural mediation, semantic token content, a bottleneck, spatial
localization, or route necessity or sufficiency.

## 2. Prior evidence and discovery/confirmation separation

The independently verified token-direction v2 transaction is accepted as an
internally coherent outcome-blind measurement. It found token-index- and
pair-dependent directional heterogeneity and retained historical numerical
non-replication with Phase-S run-003. Its extreme eyeglasses indices are not
promoted to targets.

This intervention uses a **complete-family rule** fixed prospectively:

- every learned LFE token index `k=0..31` is intervened;
- each held pair obtains its direction only from the other nine frozen pairs
  of the same attribute;
- no v2 margin, sign, correct count, outcome value, or token ranking selects or
  weights a token;
- token-direction v2 outputs are provenance and design motivation only; its
  persisted direction summaries are not loaded as intervention parameters.

The intervention directions will be reconstructed transiently from fresh LFE
outputs inside the future authorized execution transaction. Thus the target
rule is prospective, complete, and held-pair-out.

## 3. Frozen scientific universe

- Attributes: `eyeglasses` and `facial_hair`, always reported separately.
- Formal pairs: `FEY_01..FEY_10` and `FFH_01..FFH_10`.
- Formal units: 40 total, one positive and one control unit per pair.
- Frozen seeds: `2686238281`, `280026145`, `2169901996`, and `2046930553`.
- Scientific tasks: all `40 units × 4 seeds = 160` frozen tasks.
- Conditions per task: `baseline`, `target_projection_exchange`, and
  `orthogonal_sham`.
- Planned complete scientific trajectories: `160 × 3 = 480`.

No attribute, pair, role, unit, seed, token index, condition, frame, failed
sample, or unfavorable result may be deleted, replaced, imputed, selectively
rerun, or used to alter the design.

## 4. Frozen model and generation configuration

Use ConsisID commit `60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e`
and the same frozen weight inventory, prompts, references, negative prompt,
scheduler, guidance `6.0`, `bfloat16`, 49 decoded frames, resolution `480×720`,
50 scheduler positions, aligned-face preprocessing, and
`local_face_scale=1.0` used by the formal panel.

For every frozen task, all three conditions start from the same initial latent
noise by resetting a fresh generator to the frozen task seed. Scheduler state
is reconstructed identically for each condition. The spatial reference-latent
route, text conditioning, global identity inputs, keypoints, and all model
weights remain unchanged.

A newly generated baseline is required inside this transaction. Historical
videos or outcomes are not substituted because current work established an
unresolved cross-run measurement-state difference.

## 5. Intervention interface

The only intervention site is the output of
`transformer.local_facial_extractor(id_cond, id_vit_hidden)`, before it enters
the 21 `perceiver_cross_attention` modules following Transformer blocks
`0,2,...,40`. Its expected shape is `[B,32,2048]`.

The selected condition tensor replaces `valid_face_emb` consistently for all
21 sites, all 50 scheduler positions, and every classifier-free-guidance batch
row. It must not modify the LFE inputs, the Perceiver modules, their internal
LayerNorm, the video/query hidden state, or the spatial route.

Before any trajectory, the future runner must perform exactly 40 fresh face
preprocessing calls and 40 direct LFE acquisitions in ascending
`formal_unit_id` order, once per formal unit in one loaded process. It caches
the resulting unmodified LFE tensors only in process memory. The same
preprocessing result and unmodified tensor are the source for all four seeds
and all three conditions of that unit; no condition triggers a new face
preprocessing call. Before intervention, a one-step baseline hook control must
be bit-exact to the cached direct LFE tensor. No raw LFE tensor may be
persisted.

## 6. Held-pair-out direction and target intervention

Let `X[u,k]` be the transient float32 2048-D LFE token for formal unit `u` and
token index `k`. Define

`Z[u,k] = X[u,k] / max(||X[u,k]||_2, 1e-12)`.

For attribute `a`, held pair `p`, and token `k`, use the other nine pairs:

`d[a,p,k] = mean_{q != p}(Z[pos(q),k] - Z[ctrl(q),k])`

and

`u[a,p,k] = d[a,p,k] / ||d[a,p,k]||_2`.

Direction normalization is required only to define a scalar projection and
matched displacement. If any direction norm is non-finite or `<=1e-12`, the
whole future scientific transaction fails before video generation; no token,
pair, or attribute is omitted.

For held-pair roles `r ∈ {pos,ctrl}`, let `other(r)` be the other unit and set

`delta[r,k] = dot(X[other(r),k] - X[r,k], u[a,p,k])`.

The target token is

`X_target[r,k] = X[r,k] + delta[r,k] * u[a,p,k]`.

This exactly exchanges the two held units' raw scalar projections along the
held-pair-out direction while leaving each token's component orthogonal to
that direction unchanged. Both pair roles are intervened symmetrically. There
is no fitted strength, alpha sweep, top-k rule, outcome-informed sign flip, or
post-result dose change.

## 7. Deterministic orthogonal sham

For every `(attribute, formal_pair_id, token_index)`, generate a dense
Rademacher vector from SHAKE256 using the namespace

`controlled_lfe_projection_exchange_v1|attribute|formal_pair_id|token_index|attempt`.

Convert its deterministic bytes to `{-1,+1}`, cast to float32, subtract its
projection onto `u[a,p,k]`, and L2-normalize the remainder. Call the resulting
unit vector `q[a,p,k]`. Start with `attempt=0` and increment deterministically
only if the orthogonalized norm is non-finite or `<=1e-12`; more than 16
attempts fails the entire transaction.

The sham token is

`X_sham[r,k] = X[r,k] + delta[r,k] * q[a,p,k]`.

Thus target and sham have exactly equal per-token displacement L2 magnitude,
while the sham displacement is orthogonal to the target direction and leaves
the original target-direction projection unchanged. This controls additive
perturbation magnitude, not every possible off-manifold or downstream effect.

The baseline token is `X_baseline[r,k] = X[r,k]`.

## 8. Condition order and paired execution

For each frozen task, derive one of the six condition permutations by sorting
the three condition labels by

`SHA256("controlled_lfe_projection_exchange_v1|condition_order|" + task_id + "|" + condition)`.

The manifest must freeze the resulting condition order before any model or
weight load. Each condition is a fresh full trajectory with its own freshly
initialized scheduler and generator. An interruption cannot resume a partial
trajectory or reuse a later condition as a replacement.

Condition labels are hidden from annotators. Filenames and annotation packet
IDs must use a separately generated pseudonymous blind key stored outside Git.

## 9. Engineering phase and validity gates

No engineering or scientific runtime is authorized by this preregistration.
If later authorized, implementation proceeds sequentially:

1. CPU-only synthetic tests and a no-weight dry-run covering enumeration,
   schemas, direction math, sham orthogonality, deterministic ordering,
   missingness, and fail-closed behavior.
2. A separately authorized CPU-only formal input audit.
3. A separately authorized single-GPU engineering phase using two complete
   pairs per attribute selected only by the fixed hash rule
   `SHA256(formal_pair_id + "|controlled_lfe_projection_exchange_v1_engineering_pair_subset")`,
   first two lexicographically smallest hashes, seed index 1, and all three
   conditions. It may run at most one transformer scheduler position per unit,
   must decode or persist no media, and produces no scientific outcome.
4. Only after an independent engineering freeze and another explicit
   researcher decision may the 480-trajectory scientific phase be authorized.

The engineering phase must verify all of the following:

- exact 40-unit/20-pair/160-task scientific enumeration without executing it;
- direct-versus-baseline-hook tensor equality at the frozen tolerance
  `abs(a-b) <= 1e-6 + 1e-5*max(abs(a),abs(b))`;
- all 640 direction vectors are finite and have unit norm within `1e-6`;
- every target projection equals the counterpart projection within the frozen
  tolerance;
- every sham displacement is orthogonal to its target direction within
  absolute tolerance `1e-6`;
- target and sham per-token displacement norms match within the frozen
  tolerance;
- baseline, target, and sham retain shape, dtype, device, task inputs, initial
  latent hash, scheduler positions, and unchanged spatial-route summaries;
- no raw identity tensor, LFE tensor, direction, image, latent, frame, or video
  is written.

Any failure returns to researcher review. Passing engineering does not
authorize scientific generation.

## 10. Frozen outcome collection

Outcome construction is new and condition-blinded. Existing frozen outcomes
remain historical context and are not reused as the intervention baseline. The
label semantics are bound to the frozen eyeglasses codebook (1,216 bytes,
SHA256 `7e7d2be5bdb39e45134bc222ae73792845ff445392767b6366c2da138046e17e`)
and facial-hair codebook (418 bytes, SHA256
`75ca640279ac38285c418c7e8bfa21ec8495a94fc9befcd54180cdf26ef3feb1`);
facial-hair disagreement adjudication is bound to its 504-byte codebook,
SHA256 `77d4313c9b2745b7139765ee995742604dcb09f850b2b3a523011a048a8625f9`.

For every one of the 480 generated videos, sample only decoded frame indices
`[0,8,16,24,32,40,48]`, producing 3,360 planned frame observations. No other
frame may be substituted because a sampled frame is difficult or
unobservable.

- Eyeglasses: apply the frozen human rubric `present`, `absent`, or `U` with
  eye-region observability/reason, using two independent blinded annotations
  and adjudication of disagreements. The unit-condition score is the present
  fraction among valid labels.
- Facial hair: apply the frozen ordinal rubric `0`, `1`, `2`, or `U` with
  reason, using two independent blinded annotations and adjudication. Preserve
  ordinal counts; for the primary binary score use absent=`0`, present=`1|2`,
  and compute present fraction among valid labels.

Each formal unit-condition score pools the four frozen seeds and seven sampled
frames, so its planned denominator is 28 valid-or-unobservable frame states.
Every `U`, unobservable reason, and low-coverage state is retained. No label is
imputed. Annotation packets must mix attributes, pairs, roles, conditions, and
seeds under the blind key; annotators may not see condition or pair-role
metadata.

Annotation, unblinding, outcome construction, and scientific analysis each
require later, separate freezes and authority. Generation approval alone will
not authorize any of them.

## 11. Primary causal estimand

For attribute `a`, pair `p`, and role `r`, let `S[r,c]` be the unit-condition
valid-frame present fraction for condition `c`. Define the role-specific
target-versus-sham contrast

`C[r] = S[r,target] - S[r,sham]`.

Because projection exchange is predicted to raise the target attribute in the
control role and lower it in the positive role, define

`E[a,p] = 0.5 * (C[ctrl] - C[pos])`.

The primary result is the complete set of ten `E[a,p]` values for each
attribute plus, separately by attribute, correct/tie/wrong counts and mean,
median, minimum, and maximum. A tie is `abs(E)<=1e-8`; positive is the
preregistered predicted direction. No p-value, confidence interval,
multiplicity-adjusted claim, pooled cross-attribute coefficient, or
cross-attribute ranking is computed.

All ten pairs must have defined positive-role and control-role scores in both
target and sham conditions. If any required unit-condition has zero valid
sampled frames or any key is missing/duplicated, the affected value remains
missing and the attribute-level primary aggregate is not computed on a reduced
panel. The complete missingness ledger is reported and work stops for
researcher review without imputation, deletion, or regeneration.

## 12. Complete secondary diagnostics

The following are secondary and must be reported as complete families rather
than searched for favorable results:

1. the same role-aligned pair estimand with `target - baseline`;
2. the same role-aligned pair estimand with `sham - baseline`, as a generic
   perturbation diagnostic rather than a null guarantee;
3. target-versus-sham contrasts reported separately for positive and control
   roles;
4. eyeglasses observability and valid-frame coverage by complete condition;
5. facial-hair ordinal `0/1/2/U` counts, observability reasons, and valid-frame
   coverage by complete condition.

No token-resolved generated outcome, 13-frame family, stage/grid search,
identity-metric threshold, aesthetic metric, automatic eyeglasses replacement,
or association with historical outcomes is part of this v1 design.

## 13. Failure, fallback, and retry policy

- Preprocessing exception, direction degeneracy, shape/finiteness failure,
  condition mismatch, hook mismatch, sham-control failure, OOM, privacy
  violation, task duplication, or ceiling breach stops the phase immediately.
- Unstructured face-detection fallback messages remain a run-level limitation.
  They are not parsed from stdout or assigned to task, unit, pair, role,
  attribute, seed, or condition and cannot cause exclusion or selective rerun.
- A clearly external interruption before any finalized scientific output may
  permit at most one byte-identical full-transaction restart only after a new
  explicit researcher decision and append-only incident record. There is no
  checkpoint resume, condition-only recovery, or result-dependent retry.
- Failed and unobservable states remain visible. Metrics, thresholds, prompts,
  seeds, samples, references, conditions, intervention dose, exclusions, and
  outcome rules are never changed because of observed results.

## 14. Privacy and artifact policy

- References, identity names, raw face embeddings, EVA tensors, LFE tokens,
  direction vectors, aligned images, keypoints, latents, and sampled annotation
  frames remain external/private and never enter Git.
- Scientific videos and blinded annotation packets remain external/private and
  become read-only after their own verification. Public reference-corresponding
  generation remains prohibited.
- Git may contain protocols, source code after separate authorization, hashes,
  pseudonymous aggregate tables, verification records, and finite-panel
  interpretations only.
- The future runtime uses a new versioned directory and never modifies Phase-S
  run-003, token-direction v2, or any frozen outcome directory.

## 15. Compute plan and hard ceiling

Prospective scientific planning only:

- one GPU process; no distributed execution;
- 480 complete trajectories and 24,000 transformer scheduler steps;
- expected `35–50 GPU-hours`, extrapolating conservatively from the frozen
  Phase-S run-003 160-trajectory runtime;
- hard ceiling `72 GPU-hours` for the scientific phase;
- engineering ceiling: 24 one-step condition executions and `2 GPU-hours`;
- no resolution, frame, step, precision, model, condition, or panel reduction
  is allowed to meet a ceiling.

Manual annotation and adjudication are human time, not GPU-hours, and must be
planned separately.

## 16. Interpretation rules

- Predominantly positive target-versus-sham pair effects would support causal
  contribution of the complete LFE directional projection under this fixed
  intervention and panel.
- Mixed effects would support pair/state dependence of the intervention effect;
  they would not identify a universal token rule.
- Near-zero or negative effects would not establish absence of attribute
  information or irrelevance of the local route because the intervention may
  be off-manifold, the linear readout may be mismatched, and spatial/local
  paths may compensate or interact.
- A target effect accompanied by a comparable sham effect weakens
  direction-specific interpretation and requires reporting the generic
  perturbation diagnostic; it does not authorize redesign after results.
- Attribute results remain separate. Neither effect count nor magnitude ranks
  inherent attribute difficulty.

Under no result may this design claim natural mediation, attribute information
loss, semantic/spatial token localization, a bottleneck, local-route necessity
or sufficiency, spatial-route compensation, population or model-wide behavior,
frame independence, or cross-attribute ordering.

## 17. Current authority and next gate

This protocol freezes design only. It authorizes no runner, instrumentation,
analyzer, verifier, CPU test, dry-run, input audit, reference access,
preprocessing, model/weight load, GPU use, generation, decode, annotation,
outcome construction, unblinding, join, association, intervention, or public
release.

The next gate is a separate researcher authorization limited to runner,
instrumentation, analyzer, and verifier implementation, CPU-only synthetic
tests, and a no-weight dry-run. A passed implementation stage will still not
authorize formal input audit, engineering GPU work, scientific generation,
annotation, or analysis.
