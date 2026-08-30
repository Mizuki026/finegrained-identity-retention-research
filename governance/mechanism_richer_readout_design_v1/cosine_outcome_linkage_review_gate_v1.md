# Mean-tokenwise-cosine linkage review gate v1

## Proposed next minimum

Use the already captured and originally prespecified secondary diagnostic `mean_tokenwise_cosine_h_r` to test whether a direction-sensitive local-residual summary co-varies with outcome heterogeneity. This is a CPU-only reanalysis of frozen summaries, not new model inference.

The complete family contains 36 Spearman coefficients: two attributes × two CFG branches × three block groups × three denoising groups. Each coefficient uses the same ten fixed matched pairs as the completed linkage. No cell selection, reduced panel, p-value, confidence interval, fallback assignment, or cross-attribute ranking is permitted.

## Why this comes before token quantiles or frame summaries

Cosine is the smallest existing summary directly motivated by the accepted concern that scalar RMS discards direction. The three token-RMS quantiles still measure magnitude distribution, while the 13 frame-RMS columns would create a much larger repeated-measure family. Deferring them is a prospective scope decision made before any cosine/outcome association was computed.

## Required researcher decision

Formal work may start only if the researcher explicitly approves all of the following as one fixed package:

1. `mean_tokenwise_cosine_h_r` remains a secondary diagnostic and is not promoted to a primary mechanism measure.
2. The existing 2-branch × 3-block × 3-denoising aggregation and four-seed positive-minus-control construction are reused unchanged.
3. The already frozen eyeglasses and facial-hair outcomes are joined separately by attribute and pair ID.
4. Exactly 36 Spearman coefficients with average ranks are computed and reported as a complete family, without p-values or confidence intervals.
5. Token-quantile and per-frame linkage are deferred; no raw vector or token-pattern claim is made.
6. Initial authorization, if granted, covers analyzer/verifier implementation, synthetic CPU tests, no-weight dry-run, and a new formal input audit only. Real aggregation, outcome join, and association computation require a second explicit approval after that audit passes.

Until this package is approved, no analyzer/verifier will be implemented and no cosine aggregation, outcome join, or association will be computed.
