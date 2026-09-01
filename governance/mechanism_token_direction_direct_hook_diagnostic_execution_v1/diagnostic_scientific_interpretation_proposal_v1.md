# Direct-vs-one-step-hook diagnostic scientific interpretation proposal v1

Status: **proposal for researcher review; not yet an accepted scientific interpretation**.

## Verified facts

1. The authorized complete fixed panel finished: 40 formal units, 40 direct LFE calls, 40 one-step hooked controls, and 40 transformer steps. Both in-memory independent recomputation and persisted-output verification passed. No raw tensors, outcomes, 640 token margins, decoded media, or full trajectories were produced.
2. All 40 current-runtime direct-versus-hook comparisons were bit-exact. Their maximum absolute and RMS differences were both zero.
3. None of the 20 current hooked pooled margins reproduced the frozen run-003 margin within the preregistered tolerance. Absolute differences ranged from `1.466367393732071e-06` to `4.715844988822937e-05`.
4. All 20 reconstructed margins retained the sign of their frozen run-003 counterpart: 11 were positive/correct and 9 negative/wrong. This descriptive sign stability does not override the frozen numerical replication failure.
5. Face-detection fallback messages were observed in runtime stdout, but no raw stdout log or task identifier was persisted. They remain an unassigned run-level limitation and cannot explain any unit, pair, role, or attribute.

## Current fixed-panel observation

The result instantiates preregistered interpretation branch 3: direct and hooked LFE outputs agree exactly when they share the same preprocessing result in the current runtime, while the current hooked complete-panel pooled readout does not strictly reproduce historical run-003.

## Proposed scientific interpretation decisions

1. **Accept current-runtime direct/hook equivalence, narrowly scoped.** Under this exact model state, same-preprocessing pairing, one-step call context, and complete 40-unit panel, the direct call is not measurably different from the hooked LFE output. This does not establish equivalence across software environments, preprocessing runs, model versions, devices, or arbitrary transformer states.
2. **Reject the direct-versus-hook call context as the observed source of the historical pooled mismatch.** Because every paired tensor is bit-exact, the current evidence does not support the hypothesis that entering LFE through the transformer hook changes its output. It does not prove that all implementation-path effects are absent elsewhere.
3. **Treat the run-003 mismatch as cross-run state or input-construction non-replication, not attribute-information loss.** The remaining candidate class includes preprocessing/fallback realization, backend/runtime state, or another historical-versus-current input-construction difference upstream of the shared LFE call. The experiment does not distinguish these candidates and does not localize a mechanism.
4. **Preserve both strict numerical failure and descriptive sign stability.** The 20/20 tolerance failures mean the frozen run-003 values were not reproduced and the threshold must not be relaxed. The 20/20 sign matches indicate qualitative direction stability on this panel, but cannot validate exact replication, population generalization, cross-attribute ranking, or a token mechanism.
5. **Keep token-direction scientific run-001 nonreusable and do not start scientific run-002 yet.** The next smallest mechanism-safe step should be separately preregistered complete-panel preprocessing-repeatability diagnostics using fresh repeated preprocessing with transient LFE readout, without outcome access or token-margin analysis. Its purpose would be to test whether input construction itself varies across repeated current-runtime calls; even a pass would not retrospectively identify the historical run-003 source.

## Claim boundary

These results do not establish attribute loss, a bottleneck, localization, route necessity or sufficiency, causal mediation, population or model-wide behavior, frame independence, or cross-attribute ordering. The accepted working model of distributed, multi-path representation is neither confirmed nor rejected by this measurement-path diagnostic.
