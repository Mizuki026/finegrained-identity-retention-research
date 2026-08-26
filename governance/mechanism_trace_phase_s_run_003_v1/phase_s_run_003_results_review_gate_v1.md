# Mechanism trace Phase-S run-003 results review gate v1

Status: **independent runtime and prespecified-analysis verification pass; explicit researcher interpretation and disposition decisions required**.

## Evidence state

- Run 003 completed the exact frozen scientific plan: 40 formal units, four
  seeds, 160 trajectories, 8,000 Transformer steps, all 50 scheduler positions,
  all 21 local-injection sites, and both CFG branches.
- Independent runtime verification passed for 336,000 injection rows, 160 route
  rows, 160 complete task-status rows, and 180 representation margins.
- The outcome-blind post-run audit passed the exact 320-event sequence, task and
  CSV order, scheduler sequence, authorization, persistence, and budget checks.
- Runtime was 12.5001 GPU-hours against the 24-hour phase ceiling. No partial,
  decoded media, raw tensor, identity embedding, traceback, OOM, or stop event
  exists.
- The frozen prespecified analysis emitted 2,880 task cells, 360 matched-pair
  cells, 36 finite-panel injection cells, and 18 representation summaries.
  Independent arithmetic verification passed every aggregation layer.
- No inferential test, confidence interval, cross-attribute ranking, retry,
  replacement, threshold change, or run-001/run-002 reuse was performed.

## Measurement limitation requiring judgment

The ConsisID console emitted the built-in message
`fail to detect face using insightface, extract embedding on align face` 76
times. The fallback completed and no task failed. The frozen message contains
neither timestamp nor `trace_task_id`, so incidence is auditable only as a
run-level count and is not assigned to units post hoc. This concerns
reference-conditioning preprocessing, not generated-frame measurement and not
generation-quality improvement. No post hoc exclusion or regeneration is
permitted.

## Primary representation readout

The primary readout is the preregistered
`valid_face_emb_mean_token_l2_normalized` leave-one-matched-pair-out directional
margin. These are fixed-panel descriptions, not accuracy estimates for a
population.

| attribute | correct/tie/wrong | mean margin | median margin | minimum | maximum |
|---|---:|---:|---:|---:|---:|
| eyeglasses | 5/0/5 | 0.000808774 | 0.000181033 | -0.00737778 | 0.00973450 |
| facial hair | 6/0/4 | 0.00122840 | 0.000730074 | -0.00406565 | 0.0104938 |

Current observation: both primary panels contain margins of both signs. The
eyeglasses panel is evenly split and the facial-hair panel is 6/4; both have
small positive means and medians with heterogeneous pair values. This does not
establish a consistently directionally readable primary representation across
all ten fixed pairs.

## Secondary representation diagnostics

Secondary stages must not replace or be pooled with the primary readout.

### Eyeglasses

| stage | role | correct/tie/wrong | mean | median | minimum | maximum |
|---|---|---:|---:|---:|---:|---:|
| `valid_face_emb_mean_token_l2_normalized` | primary | 5/0/5 | 0.000808774 | 0.000181033 | -0.00737778 | 0.00973450 |
| `insightface_l2_normalized` | secondary | 6/0/4 | 0.00874346 | 0.0192769 | -0.0702901 | 0.0762356 |
| `eva_head_l2_normalized` | secondary | 9/0/1 | 0.0594534 | 0.0711084 | -0.0136934 | 0.108578 |
| `eva_hidden_0_patch_mean_l2_normalized` | secondary | 4/0/6 | -0.00155992 | -0.000761554 | -0.0165952 | 0.00413841 |
| `eva_hidden_1_patch_mean_l2_normalized` | secondary | 9/0/1 | 0.00622293 | 0.00574229 | -0.00236119 | 0.0164028 |
| `eva_hidden_2_patch_mean_l2_normalized` | secondary | 10/0/0 | 0.00887071 | 0.00780336 | 0.00166651 | 0.0174642 |
| `eva_hidden_3_patch_mean_l2_normalized` | secondary | 10/0/0 | 0.0156016 | 0.0141510 | 0.00700112 | 0.0263055 |
| `eva_hidden_4_patch_mean_l2_normalized` | secondary | 10/0/0 | 0.0191398 | 0.0174484 | 0.00269840 | 0.0411785 |
| `image_latent_first_frame_spatial_mean_l2_normalized` | secondary | 3/0/7 | -0.00288806 | -0.00124960 | -0.0162024 | 0.00103036 |

### Facial hair

| stage | role | correct/tie/wrong | mean | median | minimum | maximum |
|---|---|---:|---:|---:|---:|---:|
| `valid_face_emb_mean_token_l2_normalized` | primary | 6/0/4 | 0.00122840 | 0.000730074 | -0.00406565 | 0.0104938 |
| `insightface_l2_normalized` | secondary | 4/0/6 | -0.00530527 | -0.0117411 | -0.0655883 | 0.0418805 |
| `eva_head_l2_normalized` | secondary | 8/0/2 | 0.0240443 | 0.0297934 | -0.0422078 | 0.0858087 |
| `eva_hidden_0_patch_mean_l2_normalized` | secondary | 7/0/3 | 0.000660863 | 0.00532215 | -0.0257302 | 0.0106566 |
| `eva_hidden_1_patch_mean_l2_normalized` | secondary | 7/0/3 | 0.00177025 | 0.00559473 | -0.0161440 | 0.0108690 |
| `eva_hidden_2_patch_mean_l2_normalized` | secondary | 8/0/2 | 0.00287066 | 0.00294446 | -0.00657632 | 0.0112152 |
| `eva_hidden_3_patch_mean_l2_normalized` | secondary | 8/0/2 | 0.00905517 | 0.00746159 | -0.00306328 | 0.0284509 |
| `eva_hidden_4_patch_mean_l2_normalized` | secondary | 8/0/2 | 0.00942647 | 0.00906436 | -0.00722246 | 0.0286744 |
| `image_latent_first_frame_spatial_mean_l2_normalized` | secondary | 6/0/4 | 0.00435271 | 0.00885728 | -0.0230373 | 0.0199150 |

Current observation: directional readout varies materially by representation
stage within each fixed panel. Several EVA stages have predominantly positive
margins, while the primary and other secondary stages remain mixed. A candidate
hypothesis is that attribute-direction linear readability is stage-specific.
The data do not establish information loss, causal transfer, a bottleneck, or
which representation drives generated outcomes.

## Complete primary-injection 3×3 descriptions

Each cell is `mean / median / positive-zero-negative pair count` for the frozen
positive-minus-control difference in `relative_residual_rms`. Exact values are
in `injection_finite_panel_3x3_v1.csv`.

### Eyeglasses — unconditional CFG branch

| block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | -5.75551e-05 / -0.000197548 / 3-0-7 | -0.000156943 / -0.000198292 / 3-0-7 | -7.90215e-05 / -0.000113414 / 4-0-6 |
| middle | 5.07115e-05 / -1.98417e-05 / 5-0-5 | -0.000102196 / -0.000133523 / 3-0-7 | -5.41769e-05 / -6.59050e-05 / 4-0-6 |
| late | -2.45765e-06 / -5.52973e-06 / 4-0-6 | 2.36443e-06 / -5.78859e-06 / 5-0-5 | -9.78459e-06 / -5.72878e-06 / 5-0-5 |

### Eyeglasses — text CFG branch

| block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | -4.56631e-05 / -0.000159194 / 3-0-7 | -0.000147477 / -0.000175614 / 3-0-7 | -7.40603e-05 / -0.000102444 / 4-0-6 |
| middle | 3.92111e-05 / -2.81591e-05 / 5-0-5 | -9.88181e-05 / -0.000121778 / 3-0-7 | -5.36367e-05 / -6.56031e-05 / 4-0-6 |
| late | -4.07087e-06 / -1.06806e-05 / 4-0-6 | 2.12591e-06 / -5.56572e-06 / 5-0-5 | -9.70969e-06 / -6.11733e-06 / 5-0-5 |

### Facial hair — unconditional CFG branch

| block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | -3.57902e-05 / 3.68622e-05 / 6-0-4 | -8.67798e-06 / 1.77838e-05 / 5-0-5 | -4.33384e-05 / -3.32846e-05 / 5-0-5 |
| middle | 2.31370e-05 / 1.32410e-05 / 5-0-5 | 1.51018e-05 / 9.46285e-05 / 6-0-4 | -3.94620e-06 / 6.23488e-05 / 6-0-4 |
| late | -5.09568e-06 / 3.96250e-06 / 7-0-3 | 1.87518e-06 / 1.58928e-05 / 6-0-4 | 1.67592e-06 / 3.50529e-05 / 6-0-4 |

### Facial hair — text CFG branch

| block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | -2.61364e-05 / 3.74555e-05 / 6-0-4 | -3.22439e-06 / 1.71024e-05 / 6-0-4 | -3.99591e-05 / -3.24662e-05 / 5-0-5 |
| middle | 2.41538e-05 / 2.10738e-05 / 5-0-5 | 1.94772e-05 / 0.000105601 / 6-0-4 | -2.32096e-06 / 6.43356e-05 / 6-0-4 |
| late | -3.00426e-06 / 7.59654e-06 / 7-0-3 | 1.24540e-06 / 1.39738e-05 / 5-0-5 | 1.52208e-06 / 3.44514e-05 / 6-0-4 |

Current observation: every one of the 36 cells contains both positive and
negative matched-pair differences. The cell means and medians are small and
the sign patterns are heterogeneous. These tables describe the relative
magnitude of the local residual route; they do not identify causal attribute
flow, a bottleneck, frame-independent behavior, or generation quality.

## Mechanism hypotheses not verified

1. Attribute-direction linear readability may be reorganized between EVA
   reference stages and `valid_face_emb`.
2. Local residual magnitude may vary with block and denoising position, but the
   observed positive-minus-control differences do not establish that the route
   carries or causes attribute retention.
3. InsightFace-to-aligned-face fallback may contribute to stage heterogeneity,
   but the current untagged console record cannot test that hypothesis.

## Six researcher decisions required

1. Accept or reject the independent runtime verification, outcome-blind audit,
   independent analysis verification, and exact frozen evidence package.
2. Accept or reject retaining all 160 tasks while reporting the 76 unassigned
   built-in fallback messages as a run-level measurement limitation; no post
   hoc exclusion, replacement, or regeneration is proposed.
3. Accept or reject the conservative primary-readout description: eyeglasses
   is 5/0/5 and facial hair is 6/0/4 with mixed margins; neither fixed panel
   establishes consistently readable attribute direction at the primary stage.
4. Accept or reject retaining the EVA-stage patterns strictly as secondary
   stage-specific directional-readout diagnostics, not as replacements for the
   primary endpoint or evidence of causal information flow or a bottleneck.
5. Accept or reject describing all 36 injection cells as small, heterogeneous
   fixed-panel residual-magnitude differences with both signs, without choosing
   a cell or claiming localization, causal mediation, or generation improvement.
6. Choose the stage disposition: close this mechanism-trace window with the
   fixed-panel descriptive conclusions above, or pause for a separately
   preregistered follow-up design. Any new instrumentation, fallback tagging,
   metric, exclusion rule, sample, model load, or GPU budget requires a new
   explicit authorization.

## Stop rule

Do not elevate a secondary endpoint, map fallback messages to units post hoc,
select a favorable 3×3 cell, run a new analysis, change any rule, or start
another model/GPU execution before all six decisions are explicitly resolved.
