# Token-RMS quantile linkage implementation review gate v1

## Frozen design

The proposed secondary family contains exactly 108 Spearman coefficients:

- three existing metrics: `token_rms_r_q10`, `token_rms_r_q50`, and `token_rms_r_q90`;
- two attributes, analyzed separately;
- two CFG branches;
- three block groups;
- three denoising groups.

Each coefficient retains the same ten fixed matched pairs. Aggregation remains row → task cell → four-seed reference-unit mean → positive-minus-control pair value → frozen outcome join → Spearman with average ranks.

No interquantile range, ratio, slope, concentration, or sparsity metric is part of this design. The three quantile families must all be retained and reported, regardless of sign or apparent strength.

## Current boundary

The researcher authorized this preregistration only. No analyzer/verifier implementation, test, dry-run, input audit, real aggregation, outcome join, or association is currently authorized.

## Next approval package

Before implementation, the researcher must explicitly approve:

1. implementation of a fail-closed analyzer and independent verifier for the fixed 108 family;
2. CPU-only synthetic tests and a no-weight dry-run that cannot receive real input paths;
3. a new three-source formal input audit checking all 336,000 q10/q50/q90 triples for finite values and row-level monotonicity;
4. reuse of the two frozen outcome sources without construction during the audit;
5. external-only pair-level outputs and complete nonselective reporting;
6. continued prohibition of real aggregation, outcome construction, join, and association until a second post-audit execution approval.

GPU use, model loading, generation, intervention, and raw-vector capture remain outside this gate.
