# Complete-panel fresh-preprocessing repeatability diagnostic protocol v1

## 1. Scientific role

This is an outcome-blind measurement-path diagnostic following the complete-panel direct-vs-one-step-hook result. That result established bit-exact direct/hook LFE equality when both paths shared the same preprocessing output, but the current hooked pooled readout did not strictly reproduce the historical Phase-S run-003 values.

The present diagnostic tests whether two fresh calls to the frozen reference preprocessing function produce repeatable LFE readouts within one current-runtime process. It does not identify the historical source, prove fallback involvement, measure generated outcomes, or test an attribute mechanism.

## 2. Frozen complete panel and sources

- Retain all 40 formal units: 20 eyeglasses units and 20 facial-hair units, forming ten positive/control pairs per attribute.
- Resolve every unit from the `seed_index=1` row of the frozen 160-row generation manifest. This is a deterministic reference-resolution rule, not selection based on results.
- Verify every reference path and SHA256 before use.
- Preserve the frozen reference alignment setting, bfloat16 dtype, model path, ConsisID commit `60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e`, model-weight inventory, and `local_face_scale=1.0`.
- Do not use `transformer_ema`.
- No unit, pair, role, attribute, preprocessing result, detection result, or fallback case may be removed, substituted, imputed, or selectively rerun.

## 3. Fixed nested acquisition design

Load the frozen face models and transformer once in one process. For every unit in deterministic formal-unit order:

1. call the unchanged frozen preprocessing function to obtain fresh preprocessing replicate `P1`;
2. retain `P1` identity inputs, aligned image, and keypoints transiently;
3. call `transformer.local_facial_extractor` twice with the identical `P1` identity inputs, producing `P1-D1` and `P1-D2`;
4. destroy the transient `P1` aligned image and keypoints after the required readouts are captured in memory;
5. call the unchanged preprocessing function again to obtain an independently constructed replicate `P2` without reusing any `P1` output;
6. call the same LFE twice with the identical `P2` inputs, producing `P2-D1` and `P2-D2`;
7. retain only the four LFE tensors transiently until all complete-panel summaries and independent in-memory verification finish.

The fixed totals are 80 preprocessing calls and 160 direct LFE calls. There are zero hooks, zero transformer denoising steps, zero diffusion trajectories, and zero decoded videos.

Preprocessing order is always `P1` then `P2`; direct-repeat order is always `D1` then `D2`. Neither order may be chosen after inspecting results.

## 4. Frozen tensor gates and equivalence rule

Every LFE output must have shape `[1,32,2048]` and contain only finite values. The frozen elementwise tolerance is:

`abs(a-b) <= 1e-6 + 1e-5 * max(abs(a), abs(b))`.

For every comparison report bit-exact equality, maximum absolute difference, RMS difference, and the frozen-tolerance Boolean. Do not tune the tolerance.

## 5. Complete output families

### 5.1 Within-preprocessing direct-repeat family

Compare `D1` with `D2` separately for `P1` and `P2` for every unit. The family contains exactly 80 rows.

### 5.2 Cross-preprocessing LFE family

Use the deterministically designated first direct result from each preprocessing replicate: compare `P1-D1` with `P2-D1` for every unit. The family contains exactly 40 rows.

Each row also reports whether both corresponding within-preprocessing controls passed the frozen tolerance. If either control fails, the cross-preprocessing numerical row remains in the complete output but is marked `within_input_controls_pass=false` and must not be interpreted as isolated preprocessing variation.

### 5.3 Pooled LOPO margin families

For preprocessing replicate `r` in `{P1,P2}`, form one unit vector from `Pr-D1`:

`V[r,u] = l2_normalize(mean_token(Pr-D1[u]))`.

For each attribute and held-out pair, construct the direction from the other nine pairs:

`D[r,a,-p] = mean_q(V[r,pos(q)] - V[r,ctrl(q)])`,

then calculate:

`M[r,a,p] = dot(V[r,pos(p)], D[r,a,-p]) - dot(V[r,ctrl(p)], D[r,a,-p])`.

Do not normalize, fit, rotate, select, or threshold the LOPO direction. Persist all 40 margins: 20 for `P1` and 20 for `P2`.

### 5.4 Cross-replicate pooled comparison

Compare `M[P1,a,p]` with `M[P2,a,p]` for all 20 attribute/pair keys using the frozen scalar tolerance:

`abs(a-b) <= 1e-6 + 1e-5 * max(abs(a), abs(b))`.

Persist exactly 20 rows.

### 5.5 Replicate-versus-run-003 comparison

Compare all 20 `P1` margins and all 20 `P2` margins separately with frozen run-003 stage `valid_face_emb_mean_token_l2_normalized`, using the same scalar tolerance. Persist exactly 40 rows. Both replicate families are retained; no favorable replicate may be selected.

No token-index margin family is computed.

## 6. Prespecified files and privacy

The future successful transaction may contain only bounded summaries and governance records, including:

- `within_preprocessing_direct_repeat_v1.csv`: 80 rows;
- `cross_preprocessing_lfe_equivalence_v1.csv`: 40 rows;
- `preprocessing_replicate_pooled_margins_v1.csv`: 40 rows;
- `cross_replicate_pooled_comparison_v1.csv`: 20 rows;
- `replicate_run_003_comparison_v1.csv`: 40 rows;
- `preprocessing_repeatability_execution_status_v1.csv`: 80 completed-preprocessing rows;
- bounded execution summary and independent verification.

Raw `id_cond`, `id_vit_hidden`, LFE tensors, aligned images, keypoints, latents, reference copies, and decoded media are never serialized.

## 7. Fallback policy

Fallback remains a run-level limitation unless the unchanged preprocessing API exposes a robust machine-readable status without stdout parsing or behavior modification. Unstructured stdout messages must not be converted into task, unit, pair, role, or attribute labels. Fallback cannot support exclusion, imputation, selective rerun, or pair-level explanation.

## 8. Failure and transaction rules

- Any authorization, bound-source, path, SHA256, commit, shape, finiteness, count, device, or hard-ceiling mismatch aborts without a reduced-panel scientific package.
- A within-input, cross-preprocessing, cross-replicate, or historical-replication tolerance failure is a valid complete-family result and does not justify exclusion or automatic rerun.
- All prespecified rows must be retained. If the complete transaction cannot finish, no partial family may be promoted as the scientific result.
- An external interruption does not authorize resume, retry, or reconstruction from a subset. A new explicit researcher decision is required.

## 9. Prespecified interpretation matrix

1. **One or more within-input direct-repeat controls fail.** Current LFE determinism is unresolved for those inputs. Cross-preprocessing differences cannot be isolated as preprocessing variation, although all complete rows remain reported.
2. **All 80 within-input controls pass and one or more of 40 cross-preprocessing comparisons fail.** Fresh preprocessing plus resulting LFE readout is not fully repeatable in the current process. This narrows the measurement-path explanation but does not identify fallback or the historical source.
3. **All tensor comparisons pass, but one or both complete pooled replicate families fail strict run-003 replication.** Current within-process preprocessing is repeatable at the frozen tensor tolerance, while historical numerical replication remains unresolved and may involve another cross-run state difference.
4. **All tensor comparisons, all 20 cross-replicate pooled comparisons, and both complete replicate-versus-run-003 families pass.** The historical mismatch is not reproduced under this current-runtime diagnostic. This does not retrospectively identify its source or validate failed scientific run-001.

Descriptive sign stability never overrides a frozen numerical tolerance failure.

## 10. Compute and authorization boundary

- One GPU only.
- Expected use: `0.05–0.20 GPU-hours`.
- Hard ceiling: `2 GPU-hours`.
- Exactly 80 preprocessing calls and 160 direct LFE calls.
- Zero transformer steps, zero diffusion trajectories, and zero decoded videos.

This preregistration authorizes no implementation, CPU test, dry-run, formal input audit, reference access, preprocessing, model or weight loading, GPU execution, scientific run-002, outcome linkage, association, intervention, or rerun.

The next gate is separate researcher authorization for runner/analyzer/verifier implementation, CPU-only tests, and no-weight dry-run.
