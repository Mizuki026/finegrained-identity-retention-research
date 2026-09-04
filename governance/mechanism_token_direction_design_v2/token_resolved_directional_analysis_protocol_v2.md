# Token-resolved LFE directional analysis protocol v2

Status: **formally preregistered after researcher approval; no implementation or execution authority**.

## 1. Scientific role

This is a new prospective, outcome-blind representation diagnostic. It tests whether attribute-related linear direction structure is readable at the 32 learned Local Facial Extractor identity-token indices when every scientific quantity and validity control is constructed self-consistently inside one current-runtime transaction.

It is not a repair, resume, retry, or recovery of token-direction v1 scientific run-001. That transaction remains permanently failed and nonreusable. It also does not replace Phase-S run-003, prove why historical values differ, or test whether token directions cause generated attribute retention.

## 2. Why v2 is separate from v1

V1 required the newly reconstructed pooled-LFE margins to reproduce frozen run-003 numerically before any token family could be finalized. Scientific run-001 completed 160 transient extractions but failed that gate and wrote no scientific family. Later complete-panel diagnostics established:

- direct and one-step-hooked LFE outputs are bit-exact when they share preprocessing;
- repeated direct calls on identical preprocessing inputs are bit-exact;
- two fresh preprocessing calls per unit yield bit-exact LFE tensors within one current process;
- current replicate pooled margins agree exactly with each other but fail strict numerical replication of run-003 while preserving every sign.

The accepted interpretation is an unresolved cross-run measurement-state difference, not attribute-information loss. V2 therefore uses a self-contained current-runtime state and retains run-003 only as an immutable descriptive historical comparator. The old threshold is not relaxed and the old baseline is not replaced.

## 3. Frozen scientific universe

- Attributes: `eyeglasses` and `facial_hair`, always analyzed separately.
- Formal units: all 40 frozen reference units.
- Matched pairs: ten positive/control pairs per attribute, 20 pairs total.
- Source records: all 160 frozen seed-labelled generation-manifest rows, four per unit.
- Reference-resolution order: ascending `formal_unit_id`, then frozen `seed_index` 1, 2, 3, 4.
- Model: ConsisID commit `60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e` with the frozen model-weight inventory, `bfloat16`, aligned-face preprocessing, and `local_face_scale=1.0`.
- LFE shape: exactly `[1,32,2048]` with finite values.

The four seed labels do not alter the reference image or enter LFE numerics. They are retained to preserve the formal 160-row crossing and to provide a within-transaction repeated-extraction gate. No unit, pair, role, seed-labelled row, token index, preprocessing result, fallback case, or unfavorable margin may be removed, replaced, imputed, or selectively rerun.

## 4. Fixed acquisition transaction

Load the frozen face models and transformer once in one process on one GPU. For each of the 160 source records in the fixed order:

1. verify the source row, reference path, reference raw-byte SHA256, unit, pair, attribute, role, seed index, and seed;
2. run the unchanged aligned-face preprocessing function once to construct fresh `id_cond` and `id_vit_hidden` inputs;
3. call `transformer.local_facial_extractor` once to obtain `D1`;
4. for `seed_index=1` only, call the same LFE again with the identical preprocessing outputs to obtain direct-repeat control `D2`;
5. copy only the required LFE tensors transiently to float32 CPU analysis memory;
6. destroy aligned images, keypoints, identity inputs, and GPU outputs after their required controls have been captured.

Fixed acquisition totals:

- 160 fresh preprocessing calls;
- 200 direct LFE calls: 160 `D1` plus 40 seed-index-1 `D2` controls;
- zero hooks;
- zero transformer denoising steps;
- zero diffusion trajectories;
- zero decoded videos.

All 40 units and all 160 source records must complete within one transaction. A process interruption does not authorize resume, subset recovery, or automatic retry.

## 5. Frozen validity gates

The elementwise tolerance remains:

`abs(a-b) <= 1e-6 + 1e-5 * max(abs(a), abs(b))`.

The following gates occur before any 640-margin family is persisted:

1. **Shape and finiteness:** all 200 LFE outputs have shape `[1,32,2048]` and finite values.
2. **Same-input direct-repeat gate:** compare seed-index-1 `D1` and `D2` for all 40 units; all must pass the frozen tolerance. Persist the future complete 40-row control family only if the full scientific transaction succeeds.
3. **Four-label equality gate:** for every unit, compare seed indices 2, 3, and 4 `D1` separately with seed-index-1 `D1`, producing 120 fixed comparisons; all must pass the same tolerance.
4. **Complete crossing gate:** require exactly 40 units, four frozen source rows per unit, ten positive/control pairs per attribute, and all 32 token indices.

Any gate failure aborts before scientific-family promotion. It does not authorize a reduced panel, threshold change, failed-row deletion, imputation, favorable replicate selection, or retry.

Historical run-003 numerical equality is explicitly **not** a v2 validity gate.

## 6. Self-contained current pooled readout

Let `X[u,s,k]` be the float32 LFE token for unit `u`, seed-labelled record `s=1..4`, and token index `k=0..31`.

For each record, construct:

`P[u,s] = l2_normalize(mean_k X[u,s,k])`.

After the four-label equality gate passes, define:

`Pbar[u] = mean_s P[u,s]`.

For attribute `a` and held-out pair `p`, construct a current-runtime pooled LOPO direction using the other nine pairs:

`Dp[a,-p] = mean_q(Pbar[pos(q)] - Pbar[ctrl(q)])`.

Do not normalize, rotate, fit, select, or threshold the direction. The pooled held-out margin is:

`Mp[a,p] = dot(Pbar[pos(p)], Dp[a,-p]) - dot(Pbar[ctrl(p)], Dp[a,-p])`.

This produces exactly 20 current pooled margins. They are current-transaction controls and descriptive context, not retention outcomes.

## 7. Historical run-003 comparison

Join the 20 current pooled margins to the frozen run-003 stage `valid_face_emb_mean_token_l2_normalized` only by `(attribute, formal_pair_id)`. For every key report:

- current margin;
- frozen run-003 margin;
- absolute difference;
- the unchanged scalar tolerance;
- tolerance pass/fail;
- current and historical sign labels;
- sign match.

All 20 rows are retained regardless of direction or numerical agreement. This family is descriptive measurement-history evidence. It cannot invalidate an otherwise valid v2 transaction, replace run-003, redefine the current baseline as historical truth, or support outcome/mechanism claims.

## 8. Token-resolved construction

For each record and token index:

`Z[u,s,k] = X[u,s,k] / max(||X[u,s,k]||_2, 1e-12)`.

After the equality gates pass, average the four normalized copies:

`Zbar[u,k] = mean_s Z[u,s,k]`.

For attribute `a`, token index `k`, and held-out pair `p`, use only the other nine pairs:

`D[a,k,-p] = mean_q(Zbar[pos(q),k] - Zbar[ctrl(q),k])`.

Do not normalize, rotate, fit, select, or threshold this direction. Compute:

`M[a,k,p] = dot(Zbar[pos(p),k], D[a,k,-p]) - dot(Zbar[ctrl(p),k], D[a,k,-p])`.

Label `tie` if `abs(M) <= 1e-8`, `correct` if positive, and `wrong` if negative. The complete primary family contains exactly:

`2 attributes × 32 token indices × 10 held-out pairs = 640 margins`.

Token indices are stable learned-query positions. They are not image regions, semantic parts, independently sampled observations, or automatically valid intervention targets.

## 9. Prespecified persisted outputs

If and only if the complete transaction and all validity gates pass, persist:

- `same_input_direct_repeat_controls_v2.csv`: 40 rows;
- `four_label_lfe_equivalence_v2.csv`: 120 rows;
- `current_pooled_lfe_margins_v2.csv`: 20 rows;
- `historical_run_003_comparison_v2.csv`: 20 rows;
- `lfe_token_margins_v2.csv`: 640 rows;
- `lfe_token_finite_panel_v2.csv`: 64 rows, one per attribute-token index;
- `lfe_pair_token_signs_v2.csv`: 20 rows, one per attribute-pair;
- `token_direction_v2_execution_status.csv`: 160 rows;
- bounded execution summary plus independent in-memory and persisted verifications.

The 64-row token summary reports ten-pair correct/tie/wrong counts and margin mean, median, minimum, and maximum. The 20-row pair summary reports 32-token correct/tie/wrong counts and margin mean, median, minimum, and maximum.

No raw `id_cond`, `id_vit_hidden`, `X`, `Z`, pooled vector, learned direction, aligned image, keypoint, reference copy, latent, frame, or video may be serialized.

## 10. Complete-family and multiplicity rules

- Retain all 640 primary margins, all 64 token summaries, and all 20 pair summaries.
- No best-token, top-k, sparse-token, favorable-pair, favorable-attribute, or favorable-replicate selection.
- No token weighting, classifier fitting, nonlinear probe, metric tuning, threshold tuning, p-value, confidence interval, multiple-testing claim, or cross-attribute ranking.
- The ten pairs within an attribute and the 32 learned token slots are not population samples or independent repeated observations.
- Descriptive counts and margins must not be promoted to population-level inference.

## 11. Fallback and failure policy

Face-detection fallback remains a run-level limitation unless the unchanged API exposes a robust machine-readable status without stdout parsing or behavior modification. Unstructured stdout must not be mapped to a task, unit, pair, role, attribute, seed-labelled row, or token index.

Fallback cannot justify exclusion, imputation, substitution, or rerun. Any execution, authorization, path, hash, commit, device, shape, finiteness, complete-crossing, direct-repeat, four-label equality, privacy, or hard-ceiling failure aborts the transaction without scientific-family promotion.

## 12. Prespecified interpretation

- If token-index sign patterns show heterogeneous coherence while the current pooled readout is mixed, report compatibility with token-index-specific directional organization obscured by mean pooling. Do not claim a causal or distributed mechanism.
- If only a small subset of indices has coherent signs, report the exact complete-family pattern as compatible with sparse readout heterogeneity. Do not call them localized attribute tokens.
- If signs are broadly mixed, conclude only that this fixed linear LOPO readout does not reveal a stable shared token-index direction. Nonlinear, pair-specific, spatial-path, injection-side, and interaction structure remain untested.
- If the current pooled and run-003 signs remain similar despite numerical mismatch, report qualitative measurement stability separately from exact non-replication. Do not merge their numbers.
- Eyeglasses and facial hair remain separate fixed-panel descriptions. No attribute-difficulty ranking is permitted.

Terms such as `coherent`, `mixed`, `small subset`, or `broad` must always be accompanied by exact complete-family counts and are not confirmatory thresholds.

## 13. Compute planning and authorization boundary

Prospective planning only:

- one GPU;
- expected `0.05–0.25 GPU-hours`;
- hard ceiling `2 GPU-hours`;
- 160 preprocessing calls;
- 200 direct LFE calls;
- zero hooks, transformer steps, trajectories, and decoded videos.

This preregistration authorizes no implementation, analyzer, runner, verifier, test, dry-run, formal input audit, reference access, preprocessing, model or weight loading, GPU execution, token-margin computation, outcome access, association, generation, or intervention.

The next gate is separate researcher authorization for v2 runner/analyzer/verifier implementation, CPU-only tests, and no-weight dry-run. A passed implementation stage will not authorize formal input audit or GPU execution.

## 14. Sequential intervention gate

Controlled intervention remains deferred. It may be separately preregistered only after v2 execution is independently verified, frozen, scientifically interpreted, and reviewed by the researcher. Any intervention-target rule must distinguish discovery from confirmatory evidence and cannot select a favorable token from the same v2 family without a prospectively frozen validation or complete-family strategy.
