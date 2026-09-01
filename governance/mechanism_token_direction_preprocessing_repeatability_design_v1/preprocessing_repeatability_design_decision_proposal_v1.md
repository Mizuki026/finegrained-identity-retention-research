# Complete-panel fresh-preprocessing repeatability diagnostic: design-decision proposal v1

Status: **design proposal only**. It is not a preregistration and grants no implementation, reference access, preprocessing, model loading, GPU, scientific run, outcome, or intervention authority.

## Scientific purpose

The direct-hook diagnostic established bit-exact agreement when both paths shared one preprocessing result, while the current hooked pooled family failed strict numerical replication against historical run-003. The smallest remaining measurement-path question is whether two fresh preprocessing calls on the same frozen reference produce repeatable LFE inputs/readouts in the current runtime.

This diagnostic can test current-runtime repeatability. It cannot retrospectively identify which historical run-003 calls used fallback, prove that fallback caused the mismatch, or localize an attribute mechanism.

## Seven proposed fixed decisions

1. **Target and claim boundary.** Test only within-process, current-runtime repeatability of fresh reference preprocessing and its LFE readout. Do not label the result as historical-source localization, attribute-information loss, a bottleneck, or a causal mechanism.
2. **Complete panel.** Retain all 40 frozen formal units, using the deterministic `seed_index=1` manifest row only to resolve each unit's frozen reference path and SHA256. No unit, pair, role, attribute, detection result, or fallback case may be selected, replaced, excluded, imputed, or selectively rerun.
3. **Two fresh preprocessing calls.** For every unit, call the frozen preprocessing function twice from the same loaded process and model state. Neither call may reuse the other's `id_cond`, `id_vit_hidden`, aligned image, or keypoints.
4. **Nested direct-LFE determinism control.** For each fresh preprocessing result, call the same LFE twice without changing inputs. This gives 160 direct LFE calls: 40 units × 2 preprocessing replicates × 2 direct repeats. Compare the two within-preprocessing calls first; compare the two fresh-preprocessing readouts only after both within-input controls pass. No transformer step or hook is needed because the complete prior diagnostic already established current same-input direct/hook bit-exactness.
5. **Complete prespecified output families.** Persist no tensors. Report 80 within-preprocessing direct-repeat rows, 40 cross-preprocessing LFE-equivalence rows, 40 pooled LOPO margins (20 for each preprocessing replicate), 20 cross-replicate pooled comparisons, and both complete 20-row replicate-versus-frozen-run-003 comparisons. Use the already frozen elementwise and pooled tolerances; do not compute 640 token-index margins, choose a favorable replicate, or change thresholds.
6. **Fallback handling.** Preserve fallback only as a run-level limitation unless the unchanged preprocessing API exposes a robust machine-readable status without parsing stdout or changing preprocessing behavior. Do not infer a task-level fallback label from unstructured messages and do not use fallback for exclusion or explanation of a specific pair.
7. **Compute, privacy, and authorization.** One GPU, expected `0.05–0.20 GPU-hours`, proposed hard ceiling `2 GPU-hours`; zero transformer steps and zero diffusion trajectories. Identity inputs, LFE tensors, aligned images, keypoints, and media remain transient and are never serialized. Approval of these decisions would authorize preregistration drafting/freezing only; implementation, formal input audit, and GPU execution would remain separate gates.

## Prespecified interpretation matrix

- **Within-input direct repeats fail:** current LFE determinism is unresolved; cross-preprocessing comparison cannot be interpreted as preprocessing variation.
- **All within-input controls pass and one or more cross-preprocessing tensors fail:** current fresh preprocessing and resulting LFE readout are not fully repeatable on the complete panel. This narrows the measurement-path explanation but does not assign fallback or identify the historical source.
- **All tensor comparisons pass but pooled replicate values fail frozen run-003:** current preprocessing is internally repeatable, while historical numerical replication remains unresolved and likely involves another cross-run state difference.
- **All tensor and pooled comparisons pass, including both replicate families versus run-003:** the historical mismatch is not reproduced under the new current-runtime diagnostic; this still does not retrospectively identify its source or validate scientific run-001.

## Prohibited automatic continuation

No analyzer/runner implementation, image decode, preprocessing call, model loading, GPU use, rerun, outcome access, association, token-direction scientific run-002, or intervention may occur from this proposal alone.
