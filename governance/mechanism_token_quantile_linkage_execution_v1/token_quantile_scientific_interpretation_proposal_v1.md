# Token-RMS quantile linkage scientific interpretation proposal v1

## Evidence status

This proposal is for researcher decision. The canonical full-precision result is the frozen external `quantile_outcome_associations_v1.csv` (11,200 bytes; SHA256 `b7f6279745056d13f13e0adb84bdcd49d7a08d45059359bd4239ee1e62d7f4bb`). All 108 coefficients are secondary descriptive Spearman correlations over ten fixed matched pairs. Tables below contain the complete family rounded to six decimals for readability.

No p-values, confidence intervals, derived interquantile metrics, cross-attribute ranking, cell selection, or causal intervention was performed. q10, q50, and q90 are quantiles of tokenwise `rms(R)`; they do not identify tokens, attribute directions, concentration, or sparsity.

## Complete q10 family

### Eyeglasses — text

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.127305 | 0.187607 | 0.067003 |
| middle | 0.167506 | 0.167506 | 0.227809 |
| late | 0.201008 | 0.201008 | 0.201008 |

### Eyeglasses — unconditional

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.127305 | 0.187607 | 0.067003 |
| middle | 0.167506 | 0.167506 | 0.227809 |
| late | 0.201008 | 0.201008 | 0.201008 |

### Facial hair — text

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.050024 | -0.018759 | 0.081290 |
| middle | 0.118808 | 0.118808 | 0.118808 |
| late | -0.431461 | -0.431461 | -0.456473 |

### Facial hair — unconditional

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.050024 | -0.018759 | 0.081290 |
| middle | 0.118808 | 0.118808 | 0.118808 |
| late | -0.431461 | -0.431461 | -0.456473 |

## Complete q50 family

### Eyeglasses — text

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.067003 | 0.160806 | 0.221108 |
| middle | 0.167506 | 0.107204 | 0.227809 |
| late | 0.107204 | 0.201008 | 0.201008 |

### Eyeglasses — unconditional

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.067003 | 0.160806 | 0.281411 |
| middle | 0.167506 | 0.107204 | 0.227809 |
| late | 0.107204 | 0.201008 | 0.201008 |

### Facial hair — text

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.112555 | -0.062531 | 0.081290 |
| middle | 0.075037 | 0.075037 | 0.075037 |
| late | -0.431461 | -0.400195 | -0.400195 |

### Facial hair — unconditional

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.050024 | -0.062531 | 0.081290 |
| middle | 0.075037 | 0.075037 | 0.075037 |
| late | -0.431461 | -0.400195 | -0.400195 |

## Complete q90 family

### Eyeglasses — text

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.100504 | 0.100504 | 0.254610 |
| middle | 0.227809 | 0.107204 | 0.227809 |
| late | 0.167506 | 0.167506 | 0.201008 |

### Eyeglasses — unconditional

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.100504 | 0.100504 | 0.254610 |
| middle | 0.227809 | 0.107204 | 0.227809 |
| late | 0.167506 | 0.167506 | 0.201008 |

### Facial hair — text

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.025012 | -0.043771 | 0.137567 |
| middle | 0.075037 | 0.075037 | 0.075037 |
| late | -0.400195 | -0.400195 | -0.400195 |

### Facial hair — unconditional

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.025012 | -0.043771 | 0.137567 |
| middle | 0.075037 | 0.075037 | 0.075037 |
| late | -0.400195 | -0.400195 | -0.400195 |

## Verified complete-family observations

1. Every eyeglasses coefficient is positive: 18/18 at each quantile, hence 54/54 overall. The per-quantile ranges are q10 `0.067003–0.227809`, q50 `0.067003–0.281411`, and q90 `0.100504–0.254610`.
2. Every facial-hair quantile has the same sign count: ten positive and eight negative coefficients. Across the full facial-hair family there are 30 positive and 24 negative coefficients, with no zero coefficient. The total range is `-0.456473–0.137567`.
3. Facial-hair early and middle blocks are mostly weakly positive, except early-block/middle-denoising, whereas every late-block coefficient is negative at all quantiles and both branches.
4. Branch rankings are highly similar. q10 and q90 have exact branch equality in all 18 attribute-specific grid cells. q50 differs between branches in only one eyeglasses cell and one facial-hair cell.
5. q10, q50, and q90 show qualitatively similar sign and grid structures. The upper quantile does not uniquely produce the observed pattern in this fixed panel.

## Proposed mechanism synthesis for researcher decision

1. **The quantile families are compatible with a broad token-magnitude ranking shift rather than an exclusively upper-tail phenomenon.** Similar q10/q50/q90 patterns mean outcome heterogeneity is not confined descriptively to q90. This does not prove uniform token participation, diffusion, or absence of sparse attribute-specific tokens.
2. **Magnitude and alignment remain separable readouts.** Eyeglasses has positive associations across relative RMS and all three absolute token-RMS quantiles, while mean H–R cosine is mostly negative. Better retention can therefore co-vary with larger residual magnitude without co-varying with greater global H–R alignment. This remains descriptive, not a causal update rule.
3. **Facial-hair linkage is strongly state/statistic dependent.** Absolute token-magnitude quantiles are mostly positive in early/middle blocks and consistently negative in late blocks, whereas relative RMS was predominantly nonpositive. Hidden-state normalization in `rms(R)/rms(H)` is a plausible contributor to the difference, but denominator effects were not isolated and are unverified.
4. **The multi-path/distributed working model remains necessary for interpretation but unverified.** Neither magnitude quantiles nor mean cosine measure spatial-path compensation, local–spatial interaction, token identity, or route necessity/sufficiency.
5. **Further expansion of global scalar correlations has diminishing mechanism value.** The q10/q50/q90 family largely reproduces a shared coarse pattern. The next major advance should target token-resolved direction or a prospectively controlled intervention rather than automatically opening the 13-frame × 36-cell family. Such work requires a new trace/intervention design and explicit GPU authorization.

## Still unverified

- Whether many tokens share the magnitude shift or a small attribute-relevant subset is hidden by quantiles.
- Whether `rms(H)` normalization explains facial-hair differences between absolute quantiles and relative RMS.
- Whether negative late-block facial-hair associations reflect corrective state dependence, compensation, or measurement geometry.
- Whether spatial reference latents compensate for local-route magnitude or alignment patterns.
- Whether any route, block group, denoising group, or CFG branch is causally necessary or sufficient.

## Recommended decision

Accept, reject, or revise the five-part mechanism synthesis above. Acceptance should close the current scalar linkage window. It should not automatically authorize per-frame linkage, derived concentration metrics, new raw-vector capture, GPU tracing, intervention, or ablation.
