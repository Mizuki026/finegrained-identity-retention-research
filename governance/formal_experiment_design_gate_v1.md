# Formal experiment design gate v1

- Status: `AWAITING_RESEARCHER_DESIGN_DECISION`
- Scope: prospective design only
- Generation started: NO
- Formal references selected: NO
- Formal seeds defined: NO
- Manuscript drafting: OUT OF SCOPE

## Fixed scientific boundary

The completed fixed-video study is descriptive evidence and a measurement
diagnostic. It is not used to tune thresholds, remove difficult cases, select
favourable seeds, estimate frame-level sample size, or claim H1-H4. The video,
not an individual frame, remains the experimental unit. H3 remains outside the
first formal output-level experiment because it requires separately frozen
probe and intervention evidence.

## Candidate-pool feasibility result

The frozen eligible pool contains 107 images from 23 identities (75 images and
16 identities labelled man; 32 images and 7 identities labelled woman).

| Candidate cell | Images | Identities | Man identities | Woman identities |
|---|---:|---:|---:|---:|
| eyeglasses present | 14 | 5 | 5 | 0 |
| eyeglasses absent | 93 | 22 | 15 | 7 |
| facial hair ordinal 2 | 13 | 3 | 3 | 0 |
| facial hair ordinal 0 | 89 | 20 | 13 | 7 |
| hair colour light | 35 | 11 | 8 | 3 |
| hair colour dark | 72 | 17 | 12 | 5 |

Within-identity opposite-state availability is four identities for eyeglasses,
zero for facial hair, and five for hair colour. Consequently, the pool cannot
support either a gender-balanced six-cell design or a three-attribute,
within-identity paired design. This is a design constraint, not an outcome.

## Decisions required before preregistration can be frozen

### D1 — first formal objective

Recommended: make the first formal experiment an output-level, attribute-
specific replication study. Estimate prespecified video-level retention and
observability separately for eyeglasses and facial hair. Treat H1 as the only
candidate primary hypothesis. Keep H2 exploratory, defer H3, and do not test H4
until hair colour has a validated commensurate endpoint.

Alternative: make cross-attribute H4 the primary objective. This requires a new
matched reference set and a comparable hair-colour endpoint before generation;
the current pool and metric are insufficient.

### D2 — reference design

Recommended: expand and independently audit the reference pool before formal
selection. At minimum, add eyeglasses-present women and additional independent
identities with facial-hair ordinal 2. For facial hair, prespecify a man-only
analysis if that is the intended sampling frame rather than presenting an
infeasible gender-balanced contrast.

Alternative: construct same-identity edited counterfactual references. This
controls identity but changes the estimand to responses to audited image edits
and requires a separate edit-quality, realism, and leakage audit.

Using the current pool without expansion is permitted only for a bounded
finite-sample replication; it cannot remove identity/state imbalance or support
population, causal, or gender-comparative claims.

### D3 — hair-colour role

Recommended: exclude hair colour from the primary confirmatory family while a
new measurement iteration is developed. It may be collected as prespecified
exploratory/measurement-development data with missingness and low coverage
reported without imputation.

Alternative: delay all formal generation until the new hair-colour instrument
has frozen validity, coverage, failure, and reference-relative decision rules.

### D4 — resource tier

The observed generation runtime is approximately 262 seconds per 49-frame
video. Storage for MP4 outputs is small relative to model weights, but decoded
frames, audit artifacts, and backups should be budgeted separately.

| Planning tier | Reference-condition units | Seeds per unit | Videos | Estimated generation GPU-hours |
|---|---:|---:|---:|---:|
| feasibility-limited | 38 | 3 | 114 | 8.3 |
| expanded | 60 | 4 | 240 | 17.5 |
| stronger replication | 90 | 4 | 360 | 26.2 |

These are engineering budgets, not power calculations. A formal sample size
must be justified at the video/identity level after D1-D3 fix the endpoint and
sampling frame. Frame count must not be used as independent sample size.

## Actions held closed

Until D1-D4 are decided, do not select identities/images, freeze formal seeds,
run ConsisID, inspect formal outcomes, tune metric thresholds, or begin a
manuscript. After the decision, the next artifacts are a preregistration,
sampling/randomization plan, metric-validation plan, analysis plan, compute
budget, and a non-formal smoke-test manifest.
