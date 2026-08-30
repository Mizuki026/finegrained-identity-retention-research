# Cosine–outcome linkage scientific interpretation proposal v1

## Evidence status

This is a proposal for researcher decision, not an automatically accepted mechanism conclusion. All coefficients are secondary descriptive Spearman correlations over ten fixed matched pairs per attribute. No p-values, confidence intervals, cross-attribute ranking, cell selection, or causal intervention was performed.

The measured variable is the positive-minus-control contrast in mean tokenwise cosine between the current hidden state `H` and local residual `R`. It is direction-sensitive relative to `H`, but remains averaged over all video tokens and is neither an attribute-content direction nor a preserved raw vector.

## Complete 36-cell family

Rows are block groups and columns are denoising groups in early/middle/late order.

### Eyeglasses — text branch

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | -0.502518907629606 | -0.3752141176967725 | -0.3819143697985006 |
| middle | -0.19430731095011433 | -0.1340050420345616 | -0.04020151261036848 |
| late | 0.3283123529846759 | -0.10720403362764928 | -0.29481109247603554 |

### Eyeglasses — unconditional branch

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | -0.502518907629606 | -0.3752141176967725 | -0.3819143697985006 |
| middle | -0.19430731095011433 | -0.1340050420345616 | -0.04020151261036848 |
| late | 0.3283123529846759 | -0.10720403362764928 | -0.29481109247603554 |

### Facial hair — text branch

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.1063019179117228 | 0.06253053994807224 | 0.0 |
| middle | -0.08128970193249391 | -0.08128970193249391 | -0.037518323968843345 |
| late | -0.5190034815689996 | -0.4939912655897707 | -0.30639964574555395 |

### Facial hair — unconditional branch

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.17508551185460228 | 0.0 | 0.04377137796365057 |
| middle | -0.08128970193249391 | -0.08128970193249391 | -0.037518323968843345 |
| late | -0.5190034815689996 | -0.4939912655897707 | -0.30639964574555395 |

All 36 coefficients are defined. Eyeglasses has 16 negative and two positive coefficients, ranging from -0.502518907629606 to 0.3283123529846759. Facial hair has 12 negative, two zero, and four positive coefficients, ranging from -0.5190034815689996 to 0.17508551185460228.

## Current observations

1. **Mean directional alignment is not a uniformly favorable retention signal.** Most cosine/outcome coefficients are negative for both panels. A larger positive-minus-control mean cosine contrast therefore often accompanies a smaller retention outcome in these fixed panels. This is descriptive and does not mean that aligned residuals causally damage retention.
2. **Magnitude and compressed alignment expose different heterogeneity.** In the completed RMS linkage, all 18 eyeglasses coefficients were positive; here 16 of 18 eyeglasses cosine coefficients are negative. For facial hair, both families are predominantly nonpositive, but their cell patterns differ. The local residual cannot be summarized as one universal scalar whose larger value always means better attribute transmission.
3. **The grid pattern is state-dependent but not localizing.** Eyeglasses early-block cosine associations are consistently negative, while the only positive cells occur at late block/early denoising in both branches. Facial-hair early-block cells are near zero or positive, while late-block cells are more negative. No cell can be selected as an attribute location or bottleneck.
4. **CFG-branch rank patterns are highly similar.** All nine eyeglasses cells are identical between branches; six of nine facial-hair cells are identical and the remaining three differ only in the early block. This does not establish branch equivalence, redundancy, or causal interchangeability.

## Proposed mechanism synthesis for researcher decision

1. **Representation–readout mismatch/reorganization remains the leading working explanation and is modestly strengthened.** Weak or mixed pooled-LFE linkage coexists with structured outcome covariation in a different compressed local-route readout. The evidence is inconsistent with treating mean-pooled LFE or scalar RMS as exhaustive representations of attribute information. It still cannot prove representational reorganization.
2. **The local route appears descriptively structured but not monotonically interpretable.** Residual magnitude and mean `H`–`R` cosine can carry different, even opposite, pair rankings. This is compatible with state-dependent corrective updates, orthogonal feature writing, tokenwise cancellation, or interaction with the spatial route; none is individually verified.
3. **Multi-path, distributed representation remains viable and unverified.** The current scalar summaries do not measure path compensation or interaction. Existing positive spatial-latent associations and local-route heterogeneity can coexist without identifying which route is necessary or sufficient.
4. **Mean cosine is still an incomplete readout.** Averaging across video tokens can erase localized positive and negative alignments. Its sign cannot be interpreted as attribute direction, and the result does not validate the stronger residual-vector hypothesis.
5. **The strongest next mechanism question is distributional structure, not another global scalar claim.** Already captured token-RMS quantiles can test whether outcome heterogeneity accompanies diffuse versus concentrated residual magnitude, but they remain magnitude summaries. A direct test of attribute-relevant vector direction or token pattern would require a separately designed new trace capture because raw tensors were not persisted.

## Still unverified hypotheses

- Attribute-relevant residual components may be orthogonal to, rather than aligned with, the global hidden state.
- Positive and negative tokenwise alignments may cancel in the mean while retaining structured token patterns.
- Spatial reference latents may compensate for weak or inverse local-route readouts.
- Late-block facial-hair patterns may reflect state dependence, but not a localized causal bottleneck.
- Similar CFG-branch ranks may arise from shared inputs or aggregation and do not show causal equivalence.

## Recommended next decision

Accept, reject, or revise the five-part mechanism synthesis above before opening a new metric family. If accepted, the next CPU-only design choice is whether to preregister all three existing token-RMS quantiles as a complete 108-coefficient secondary family. Any derived concentration metric, raw-vector capture, GPU trace rerun, intervention, or ablation requires a separate explicit metric/design authorization.
