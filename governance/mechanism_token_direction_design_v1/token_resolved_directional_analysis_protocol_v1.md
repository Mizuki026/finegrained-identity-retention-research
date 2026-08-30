# Token-resolved LFE directional analysis protocol v1

Status: **proposed fixed design; researcher approval required; no implementation or execution authority**.

## 1. Objective

Test whether attribute-related linear direction structure that is mixed after mean pooling is readable at the 32 learned Local Facial Extractor identity-token slots. This is an outcome-blind representation analysis. It does not reopen scalar outcome linkage and does not analyze the 17,550 video residual-token vectors.

The primary scientific contrast is between:

- the already frozen mean-pooled LFE leave-one-pair-out margins; and
- leave-one-pair-out directions constructed separately at every one of the 32 LFE token indices.

The study asks whether mean pooling can obscure token-index-specific directional structure. It does not ask whether a token direction causes generated attribute retention.

## 2. Why the scope is restricted to LFE tokens

The LFE output has fixed shape `[1,32,2048]`. Its 32 entries are learned query slots with stable computational indices under the frozen model commit. They are not image regions, semantic parts, or independently sampled observations.

At each local injection site, the residual `R` instead has shape `[2,17550,3072]` in the frozen 49-frame geometry. Persisting or fitting full directions over every video residual token, site, step, and task would create a qualitatively different storage, privacy, multiplicity, and compute problem. Injection-side raw-vector direction analysis is therefore excluded from v1 rather than silently pooled or projected.

## 3. Frozen scientific universe

- Attributes: eyeglasses and facial hair, analyzed separately.
- Units: all 40 frozen formal reference units.
- Matched pairs: ten positive/control pairs per attribute; no replacement or reduced panel.
- Reference task crossing: all four frozen seed-labelled task records per unit, for 160 records total.
- The seed does not enter the deterministic reference/LFE computation; the four labels are retained solely to preserve the frozen crossing and verify equality across repeated reference extraction.
- Frozen references, pair roles, prompts, preprocessing configuration, checkpoints, dtype, and model commit remain unchanged.
- Existing 76 unmapped fallback messages remain only a run-003 limitation and are not assigned to any unit or pair.

No generated outcome is opened or joined in this analysis.

## 4. Prospective engineering phase

Use the already frozen eight-unit mechanism-trace engineering subset. For every engineering unit:

1. run the unchanged reference preprocessing and direct LFE call twice;
2. require token tensors of exact shape `[1,32,2048]` and finite float32 analysis copies;
3. require repeat equality under `abs(a-b) <= 1e-6 + 1e-5 * max(abs(a),abs(b))` elementwise;
4. compare the direct LFE result with the LFE forward-hook result from one bounded transformer step under the same tolerance;
5. verify that token index order and pooled-vector reconstruction are unchanged.

Engineering outputs may establish route equivalence and determinism only. They cannot be used to select token indices, metrics, thresholds, or attributes. Any shape, equivalence, determinism, nonfinite-value, or ordering failure stops the study before the scientific phase.

## 5. In-memory token construction

For unit `u` and token index `k=0..31`, let `X[u,k]` be the 2048-dimensional LFE token. Cast to float32 and compute:

`Z[u,k] = X[u,k] / max(||X[u,k]||_2, 1e-12)`.

The four seed-labelled copies for a unit must first satisfy the frozen equality tolerance. Then average the four normalized copies to obtain the unit token vector. No raw `X` or `Z`, per-reference embedding, reference image, or decoded media may be serialized.

For pooled replication only, reconstruct the original stage exactly as:

`P[u] = l2_normalize(mean_k X[u,k])`.

The resulting 20 pooled LOPO margins must match the frozen run-003 LFE margins under the same tolerance before token-specific scientific summaries are finalized.

## 6. Fixed token-specific LOPO direction

For attribute `a`, token index `k`, and held-out pair `p`:

1. use the other nine matched pairs only;
2. compute `D[a,k,-p] = mean_q(Z[pos(q),k] - Z[ctrl(q),k])`;
3. do not normalize, fit, rotate, threshold, or select `D` after inspecting the held-out pair;
4. compute held-out margin
   `M[a,k,p] = dot(Z[pos(p),k],D[a,k,-p]) - dot(Z[ctrl(p),k],D[a,k,-p])`;
5. label tie if `abs(M) <= 1e-8`, correct if positive, and wrong if negative.

This produces exactly `2 attributes × 32 tokens × 10 pairs = 640` primary margins. Pair roles or retention outcomes never enter direction selection beyond the frozen positive/control attribute labels required by LOPO.

## 7. Prespecified outputs and summaries

Primary complete family:

- `lfe_token_margins_v1.csv`: 640 rows containing attribute, token index, formal pair ID, margin, and correct/tie/wrong label.
- `lfe_token_finite_panel_v1.csv`: 64 rows containing the ten-pair correct/tie/wrong counts and margin mean, median, minimum, and maximum for each attribute-token index.

Secondary descriptive summaries:

- `lfe_pair_token_signs_v1.csv`: 20 rows containing, for every attribute-pair, the correct/tie/wrong counts across all 32 token indices plus the mean, median, minimum, and maximum token margin.
- `pooled_lfe_replication_v1.csv`: the 20 reconstructed pooled margins and their frozen run-003 counterparts, used as a validity check rather than a new outcome.
- execution, audit, and independent-verification JSON records.

All 32 token indices and all ten pairs must be reported. There is no best-token selection, top-k family, token exclusion, token weighting, outcome correlation, classifier fitting, p-value, confidence interval, or cross-attribute ranking.

## 8. Prospective interpretation rules

- If several token indices have more coherent LOPO signs than the pooled LFE baseline, the result is compatible with token-index-specific directional organization obscured by mean pooling. It does not prove a distributed mechanism.
- If only a small number of token indices show coherent signs, report the exact complete-family pattern as compatible with sparse readout heterogeneity. Do not call those slots localized attribute tokens.
- If token-index signs are broadly mixed, conclude that this fixed linear LOPO readout does not reveal a stable shared token-index direction. This does not establish absence of nonlinear, pair-specific, spatial-path, or injection-side attribute structure.
- If pair-level token-specific mean margins are more directionally consistent than frozen pooled margins, describe this as compatibility with representation–readout mismatch, not improved retention or functional contribution.
- Eyeglasses and facial hair remain separate finite-panel descriptions; their counts or margins must not be ranked as attribute difficulty.

Terms such as `several`, `small number`, `coherent`, and `broadly mixed` may be used only in a qualitative description accompanied by all exact counts. They are not thresholded confirmatory categories.

## 9. Failure and privacy rules

- Any bound source path, byte count, SHA256, model commit, tensor shape, token count, pair structure, or four-record crossing mismatch: abort.
- Any nonfinite vector or margin, incomplete pair, failed reference, or pooled replication mismatch: abort without reduced-panel analysis, imputation, substitution, or rerun selected by result.
- A predeclared external interruption policy may permit one byte-identical command retry only if later frozen before execution.
- Raw identity embeddings and token vectors remain transient in memory. Runtime storage is limited to pseudonymous pair-level margins, bounded aggregate summaries, logs, and hashes.
- No output may map old run-003 fallback messages to tasks or pairs.

## 10. Compute and authorization boundary

The proposed implementation must enumerate tasks and validate all joins without weights in a CPU-only dry-run. Actual reference encoding and LFE extraction require a separately authorized single-GPU run. No video decoding or full diffusion trajectory is planned. Engineering may execute at most 16 direct reference/LFE passes plus eight one-step hook-equivalence controls; scientific extraction contains exactly 160 seed-labelled reference/LFE passes.

Prospective planning ceilings, subject to separate researcher approval, are one GPU, at most 4 GPU-hours for engineering, at most 8 GPU-hours for scientific extraction, and 12 GPU-hours total. A passed engineering phase does not authorize the scientific phase.

Approval of this preregistration still does not authorize analyzer implementation, CPU tests, dry-run, input audit, model loading, GPU execution, token capture, outcome linkage, intervention, ablation, or generation.

## 11. Sequential gate to intervention

Controlled intervention will not be preregistered from this document. A separate intervention preregistration may be drafted only after token-direction execution is independently verified, frozen, scientifically interpreted, and reviewed by the researcher. Any intervention target-selection rule must distinguish discovery from confirmatory evidence and may not select a favorable token from the same data without a prospectively frozen validation strategy.
