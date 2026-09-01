# Complete-panel direct-vs-one-step-hook diagnostic protocol v1

## 1. Scientific role

This is a bounded engineering/measurement diagnostic triggered by the failed token-direction scientific run-001. It asks whether a direct call to the Local Facial Extractor and the LFE output observed inside one real transformer step are equivalent across the complete fixed 40-unit panel, and whether the current hooked outputs reproduce the 20 frozen run-003 pooled-LFE margins.

It is not a token-direction scientific rerun, a mechanism intervention, an outcome analysis, or a localization experiment.

## 2. Frozen inputs and complete panel

- Use the frozen 40 formal units: 20 eyeglasses units and 20 facial-hair units, comprising ten positive/control pairs per attribute.
- No unit, pair, role, attribute, failed face, or fallback case may be removed, substituted, imputed, or selectively rerun.
- Resolve each unit from the `seed_index=1` row of the frozen 160-row generation manifest. All four seed-labelled rows for a unit bind the same reference path and SHA256; `seed_index=1` is a deterministic operational representative, not a favorable selection.
- Use frozen seed `2686238281` for the one-step pipeline control.
- Preserve the frozen prompt, negative prompt, 49 frames, guidance scale 6.0, disabled dynamic CFG, bfloat16 dtype, reference alignment setting, model path, ConsisID commit, and model-weight inventory.
- Set `local_face_scale=1.0`. Do not use `transformer_ema`.

## 3. Same-preprocessing paired measurement

For each of the 40 units exactly once:

1. verify the frozen reference path and SHA256;
2. call the frozen face/reference preprocessing once;
3. retain its `id_cond`, `id_vit_hidden`, aligned image, and keypoints transiently in memory;
4. call `transformer.local_facial_extractor(id_cond, id_vit_hidden)` directly and retain the `[1,32,2048]` output transiently;
5. install a one-shot forward hook on the same `local_facial_extractor` module;
6. execute exactly one pipeline denoising step with the same preprocessing outputs;
7. require the hook to fire exactly once and compare the hooked `[1,32,2048]` output with the direct output;
8. destroy transient identity and token tensors after all complete-panel summaries pass.

The pipeline control uses `output_type=latent`; latent output is discarded immediately. No video is decoded or persisted. There are exactly 40 direct LFE calls and 40 transformer steps.

## 4. Direct-hook equivalence family

For every unit, compute without persisting either tensor:

- tensor shape and finiteness gates;
- bit-exact equality as a descriptive Boolean;
- maximum absolute element difference;
- RMS element difference;
- frozen tolerance result using `abs(a-b) <= 1e-6 + 1e-5*max(abs(a),abs(b))` elementwise.

The complete family contains exactly 40 rows. All rows are retained. No threshold tuning, top-k selection, unit exclusion, or attribute-level cherry-picking is permitted.

## 5. Hook-pooled run-003 replication

For each hooked output `H[u]`, construct:

`P[u] = l2_normalize(mean_token H[u])`.

For each attribute and held-out pair, use the other nine pairs only:

`D[a,-p] = mean_q(P[pos(q)] - P[ctrl(q)])`

and compute:

`M[a,p] = dot(P[pos(p)],D[a,-p]) - dot(P[ctrl(p)],D[a,-p])`.

Do not normalize, fit, rotate, select, or threshold the LOPO direction. Compare all 20 reconstructed margins with the frozen run-003 `valid_face_emb_mean_token_l2_normalized` margins using `abs(a-b) <= 1e-6 + 1e-5*max(abs(a),abs(b))`. Report reconstructed value, frozen value, absolute difference, tolerance, within-tolerance Boolean, and sign label for all 20 rows.

No 640 token-index margins are computed in this diagnostic.

## 6. Prespecified outputs

- `direct_hook_equivalence_v1.csv`: exactly 40 complete-panel rows.
- `hook_pooled_replication_v1.csv`: exactly 20 rows.
- `diagnostic_execution_status_v1.csv`: exactly 40 completed-unit rows if the transaction succeeds.
- bounded execution summary, independent-verification record, hashes, and audit/freeze records.

Raw LFE tokens, identity embeddings, aligned images, keypoints, latent tensors, reference images, and decoded media are never serialized.

## 7. Prespecified interpretation matrix

1. **All 40 direct-hook comparisons pass and all 20 hooked pooled margins reproduce run-003.** The failed scientific run-001 is then compatible with an implementation-path discrepancy outside the intended paired diagnostic transaction. This does not validate token-direction results.
2. **One or more direct-hook comparisons fail while all 20 hooked pooled margins reproduce run-003.** The direct extraction route is not a valid complete-panel substitute for the in-pipeline hooked route under the current runtime. This is a measurement-path finding, not an attribute mechanism.
3. **All 40 direct-hook comparisons pass but one or more hooked pooled margins fail to reproduce run-003.** The current paired runtime does not reproduce the historical run-003 pooled readout; historical preprocessing/fallback/runtime heterogeneity remains a plausible but unlocalized source. This does not identify a causal source.
4. **Both families contain failures.** Direct-vs-hook context and historical replication are jointly unresolved. Report the complete two families without selecting an explanatory subset.

Bit-exact failure with frozen-tolerance success is reported descriptively and is not treated as scientific non-equivalence. No branch authorizes mechanism, bottleneck, path necessity/sufficiency, localization, population, model-wide, frame-independent, or cross-attribute conclusions.

## 8. Fallback and failure rules

- Face-detection fallback messages remain run-level limitations only. They are not assigned to a unit, pair, role, attribute, or task in persisted outputs.
- Any missing/bound-source/hash/commit/shape/finiteness/task-count mismatch, preprocessing exception, hook count other than one, or incomplete 40-unit panel aborts without reduced-panel results.
- Diagnostic disagreement is a valid complete-family result and does not itself abort, provided all 40 paired measurements and all 20 pooled computations are complete and finite.
- No automatic or selective rerun is authorized. An external interruption requires a new explicit decision before any byte-identical full-command retry.

## 9. Compute and authorization

- One GPU only.
- Expected use: 0.1–0.3 GPU-hours.
- Hard ceiling: 2 GPU-hours.
- Exactly 40 one-step transformer controls; zero full diffusion trajectories and zero decoded videos.
- This preregistration authorizes no implementation, test, dry-run, reference access, model loading, GPU execution, scientific run-002, outcome linkage, or intervention.

## 10. Claim boundary and next gate

The maximum claim is complete-fixed-panel measurement-path agreement or disagreement under the frozen diagnostic. A separate researcher authorization is required to implement and audit the diagnostic runner. GPU execution requires another code-bound authorization after CPU-only tests, no-weight dry-run, and formal input audit pass.
