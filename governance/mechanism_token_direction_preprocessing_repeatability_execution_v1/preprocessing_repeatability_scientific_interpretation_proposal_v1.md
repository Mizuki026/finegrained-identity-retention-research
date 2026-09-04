# Preprocessing repeatability diagnostic scientific interpretation proposal v1

Status: **proposal for researcher review; not yet an accepted scientific interpretation**.

## Verified facts

1. The authorized complete fixed panel finished: 40 formal units, 80 fresh preprocessing calls, and 160 direct LFE calls. Both in-memory independent recomputation and persisted-output verification passed. No raw tensors, outcomes, token-index margins, transformer steps, trajectories, or decoded media were produced.
2. All 80 within-preprocessing `D1` versus `D2` comparisons were bit-exact. Their maximum absolute and RMS differences were both zero.
3. All 40 cross-preprocessing `P1-D1` versus `P2-D1` comparisons were bit-exact, with all 40 corresponding within-input control gates passing. Their maximum absolute and RMS differences were both zero.
4. All 20 `P1` versus `P2` pooled LOPO margins were exactly equal. All passed the frozen scalar tolerance and all retained the same sign.
5. Neither current replicate reproduced any frozen run-003 pooled margin within the preregistered tolerance: 0/20 passed for P1 and 0/20 passed for P2. Across the 40 retained comparisons, absolute differences ranged from `2.7478672564029694e-06` to `4.0709623135626316e-05`; all 40 retained the frozen sign.
6. Unstructured face-detection fallback messages were observed in runtime stdout. No raw stdout log or machine-readable task label was persisted. They remain an unassigned run-level limitation and cannot support a unit-, pair-, role-, or attribute-level explanation.

## Current fixed-panel observation

The result instantiates preregistered interpretation branch 3: every within-input and cross-preprocessing tensor comparison passed, and both current pooled replicate families agreed exactly with each other, while both complete replicate families failed strict numerical replication of historical run-003.

## Proposed scientific interpretation decisions

1. **Accept current-runtime direct-repeat determinism, narrowly scoped.** With identical current preprocessing inputs, every paired direct LFE call was bit-exact on this fixed 40-unit panel. This does not establish determinism across hardware, software environments, processes, model versions, or arbitrary inputs.
2. **Accept current-process fresh-preprocessing repeatability at the measured LFE readout.** Two independently constructed preprocessing calls per unit produced bit-exact `P1-D1` and `P2-D1` tensors, and identical complete-panel pooled margins. Under this run's fixed order and loaded state, no fresh-call variation was detected by the frozen LFE tensor and pooled readouts.
3. **Do not attribute the historical run-003 mismatch to within-process fresh-preprocessing stochasticity.** The current result rejects that narrow observed-source hypothesis for this run. It does not rule out process initialization, backend/runtime state, historical input construction, or other cross-run differences, and it does not identify fallback as the source.
4. **Preserve both strict historical non-replication and descriptive sign stability.** The 40/40 frozen-tolerance failures remain numerical replication failures and the threshold must not be relaxed. The 40/40 sign matches show qualitative direction stability on this panel, but do not make the current values interchangeable with run-003 or justify population, model-wide, or cross-attribute conclusions.
5. **Treat the remaining discrepancy as an unresolved cross-run measurement-state issue, not attribute-information loss.** This diagnostic further narrows the mismatch upstream of the planned token-direction inference but does not localize a mechanism. Token-direction scientific run-001 remains nonreusable; no run-002, baseline replacement, intervention, outcome linkage, or additional diagnostic should begin without a separate preregistered researcher decision.

## Mechanism-model implication

The result does not update the accepted distributed, multi-path representation model in a causal sense. It only strengthens the measurement caution: current LFE tensors can be perfectly repeatable within a process while differing slightly from a historical run. It neither shows that attribute information disappears from LFE nor establishes route necessity, sufficiency, compensation, bottleneck location, or an update rule.

## Claim boundary

These results do not establish attribute loss, fallback causation, a bottleneck, localization, route necessity or sufficiency, causal mediation, population or model-wide behavior, frame independence, or cross-attribute ordering. No outcome was accessed, so no retention association or mechanism-to-outcome claim is available.
