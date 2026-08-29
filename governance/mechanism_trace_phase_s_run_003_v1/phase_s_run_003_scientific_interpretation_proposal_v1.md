# Phase-S run-003 scientific mechanism interpretation proposal v1

Status: **scientific interpretation proposed; explicit researcher acceptance or revision required**.

This proposal synthesizes only frozen evidence already produced by the formal
outcome panels, static ConsisID mapping, and Phase-S run-003 mechanism trace. It
does not add a metric, recompute an outcome, select a favorable cell, reopen the
closed execution window, or claim causality.

## 1. Mechanistic question actually answered

The trace separates three questions that are often conflated:

1. Is a positive-versus-control attribute direction linearly readable from a
   bounded pooled representation at a frozen reference-side stage?
2. Is the local identity-token route active, and how large is its residual
   relative to the current video-token state across block and denoising groups?
3. Does either internal description explain attribute retention in generated
   videos?

Run 003 addresses the first two descriptively. It does not answer the third,
because no preregistered pair-level linkage, intervention, mediation statistic,
or outcome-conditioned analysis was part of v1.

## 2. Evidence chain and interpretation boundary

| Evidence location | Frozen observation | Supported interpretation | Not supported |
|---|---|---|---|
| Generated eyeglasses panel | Human consensus: 33/40 matched seed-pair differences positive, 7 zero, 0 negative; mean 0.825, median 1.0 | Eyeglasses are frequently retained in the fixed positive-condition videos | Which ConsisID route caused retention |
| Generated facial-hair panel | Mean matched contrast 0.2052380952, median 0, range -1 to 1, substantial unobservability | Fixed-panel retention is heterogeneous | A population effect or internal mechanism |
| EVA reference stages | Eyeglasses late EVA hidden stages 2–4 are 10/10 directionally correct; facial-hair EVA stages are mostly 7/10 or 8/10 | Under the frozen linear readout, attribute direction is available at several upstream EVA stages | That EVA features cause generated retention or that counts are comparable across attributes |
| Local Facial Extractor output | Primary readout is 5/0/5 for eyeglasses and 6/0/4 for facial hair | The mean-pooled 32-token LFE output is not consistently directionally readable across all ten fixed pairs | That the attribute is absent from the full 32-token representation |
| Reference-image latent pooled readout | Eyeglasses 3/0/7; facial hair 6/0/4 | The 16-D first-frame spatial-mean readout is mixed | That the spatial I2V route lacks attribute information |
| Local injection route | Every one of 36 positive-minus-control cells contains both signs; cell differences are small and heterogeneous | Residual norm ratio is not uniformly larger for positive references in the fixed panel | Residual content, causal mediation, bottleneck location, or generation improvement |

## 3. Primary scientific interpretation

### 3.1 Upstream visual attribute information is not simply absent

For eyeglasses, several EVA representations—especially hidden stages 2–4—show
a positive leave-one-pair-out direction for all ten fixed reference pairs. For
facial hair, EVA readouts are also predominantly positive, though mixed. This
is evidence of stage-specific linear readability in the frozen reference
encoder. It makes a simple explanation of “the reference encoder contains no
attribute distinction at all” inadequate for this panel.

This remains a readout statement. The stages have different dimensions and
representations, and their margin magnitudes are not a common scale. A 10/10
secondary result cannot be promoted above the preregistered primary endpoint.

### 3.2 The LFE result is compatible with transformation or readout mismatch,
not proven information loss

The Local Facial Extractor consumes the 1280-D compact condition plus five EVA
token maps and emits 32 learned-query tokens. The v1 primary statistic reduces
those 32 tokens to one mean-pooled L2-normalized vector. Mixed primary margins
can therefore arise from at least three unresolved possibilities:

- the LFE reorganizes attribute information into a form not aligned with one
  global positive-minus-control direction;
- relevant information remains distributed across the 32 tokens and is lost
  by mean pooling;
- input/preprocessing heterogeneity changes the fused representation across
  pairs.

The data do not distinguish these possibilities and do not establish that the
LFE discards attribute information.

### 3.3 The two conditioning routes prevent a single-route explanation

ConsisID uses both:

- a local identity-token route, injected by 21 Perceiver cross-attention
  residuals; and
- a separate spatial reference-image latent route concatenated with noisy
  video latents before patch embedding.

The mixed primary LFE readout therefore does not conflict with strong
eyeglasses retention in the generated fixed panel. Retention could coexist with
a mixed pooled LFE readout because information is distributed nonlinearly in
the local tokens, supplied through the separate spatial route, or jointly used
by both routes. The current 16-D spatial-mean latent diagnostic collapses
spatial structure and cannot rule the second route in or out.

The most defensible working model is consequently **multi-route and
representation-dependent**, not “upstream attribute absent” and not “LFE is a
proven bottleneck.” This is a working hypothesis, not a verified mechanism.

### 3.4 Residual magnitude is delivery strength, not attribute content

`relative_residual_rms` measures the RMS magnitude of the local residual
relative to the current hidden state. A residual may carry different attribute
content through vector direction, token pattern, or interaction with the video
query while retaining similar norm. Conversely, a larger norm need not carry
the target attribute.

The complete mixed-sign 3×3 result therefore supports only this conclusion:
positive references do not produce a uniformly larger local-residual norm ratio
than their controls across the fixed panel. It does not show that the local
route is irrelevant, and it cannot localize retention or suppression.

### 3.5 Fallback is a plausible heterogeneity source, not an explanation

The 76 untagged InsightFace-to-aligned-face fallback messages concern the
512-D compact identity component. EVA processing uses the aligned parsed face
for all tasks, while the LFE fuses both the compact component and EVA token
maps. The fallback could therefore contribute to pair heterogeneity in the
compact and downstream fused representations.

Because the frozen console message lacks a task identifier, this hypothesis
cannot be tested in run 003. It must remain a run-level limitation and cannot
justify exclusion, regeneration, or a post hoc unit assignment.

## 4. Attribute-specific synthesis without ranking

### Eyeglasses

The coexistence of strong fixed-video retention, strong secondary EVA
directional readability, mixed primary LFE readability, and mixed residual-norm
differences is most consistent with attribute information being available
upstream but not captured by a single global pooled LFE direction or a scalar
residual-magnitude contrast. Separate spatial conditioning and distributed
token structure remain plausible contributors. No route is established as
causal.

### Facial hair

The fixed-video result, primary readout, secondary EVA stages, and injection
cells are all heterogeneous. This is compatible with a combination of partial
stage-specific readability, reference/preprocessing variability, and output
observability variation. The current data cannot rank these explanations or
separate representation limitations from video-side visibility and dynamics.

These two syntheses are reported separately and are not a cross-attribute
performance comparison.

## 5. What the current mechanism window achieved

The window established that:

- bounded instrumentation can trace the actual ConsisID reference and local
  injection paths deterministically;
- attribute-direction readability is stage-specific in the fixed panel;
- the preregistered primary pooled LFE readout is mixed;
- local residual norm differences are small, heterogeneous, and nonlocalizing;
- current evidence does not bridge internal trace values to generated outcome
  retention.

Thus the study narrows the mechanism space but does not identify a retention
mechanism. It argues against a one-number explanation based solely on upstream
absence, pooled LFE readability, or residual magnitude.

## 6. Recommended future transition, if the line is reopened

The next minimal transition should be a separately preregistered **CPU-only
pair-level linkage design using existing frozen outputs**, not another GPU run.
Before computing anything, it would need to freeze:

- ten matched reference pairs per attribute as the analysis units;
- the exact mapping from frozen outcome contrasts to trace pair IDs;
- primary linkage between the preregistered LFE margin and outcome contrast;
- complete, explicitly secondary treatment of all upstream stages rather than
  selecting the favorable EVA stage post hoc;
- a nonselective policy for the complete injection grid;
- descriptive association statistics, missingness, multiplicity, and claim
  boundaries;
- no causal language, no p-value-driven selection, and no new media release.

Such a linkage could test whether pair heterogeneity in internal summaries
co-varies with pair heterogeneity in observed retention. It would still be
associational and would reuse the same fixed panel.

A later causal route test would require a new matched intervention, such as a
scientific local-route ablation while leaving the reference-image latent route
active. That would require new GPU budget and is not recommended before the
CPU-only linkage question is resolved.

## 7. Researcher decisions requested

1. Accept or revise the conclusion that several upstream EVA stages contain a
   linearly readable attribute direction in this fixed panel, while the
   preregistered pooled LFE primary readout remains mixed.
2. Accept or revise the multi-route/distributed-representation working model as
   the most defensible explanation class, explicitly not a verified causal
   mechanism or proven bottleneck.
3. Accept or revise the conclusion that mixed residual-norm differences do not
   establish local-route irrelevance because magnitude is not attribute
   content.
4. Accept or revise the statement that run 003 narrows the mechanism space but
   does not yet connect internal traces to generated retention outcomes.
5. Decide whether a future session may draft—but not execute—a prospective
   CPU-only pair-level linkage protocol using existing frozen artifacts.
6. Reconfirm that no new GPU intervention, fallback rerun, metric computation,
   or outcome linkage begins under the closed Phase-S package.
