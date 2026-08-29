# Mechanism–outcome linkage: scientific interpretation proposal v1

## Status and scope

This proposal interprets the independently verified, fixed-panel descriptive associations from `mechanism_outcome_linkage_v1_run_001`. It is submitted for researcher acceptance and is not itself a frozen scientific conclusion.

Each coefficient is a Spearman rank correlation across exactly ten prespecified pairs within one attribute. No p-values or confidence intervals were computed. The two attributes remain separate panels. No coefficient supports causal, population, model-wide, frame-independent, localization, route necessity/sufficiency, cross-attribute-ranking, or proven-bottleneck claims.

## Verified facts

- The eyeglasses outcome is the prespecified four-seed arithmetic mean of frozen human positive-minus-control values for each of ten FEY pairs.
- The facial-hair outcome uses the ten existing frozen `primary_positive_minus_control` values without reconstruction.
- All planned joins are complete: 20 primary rows, 160 representation-secondary rows, and 360 injection-secondary rows.
- All 2 primary, 16 representation-secondary, and 36 injection-secondary coefficients are defined and were independently recomputed exactly.
- Run-001 used CPU only, zero GPUs, no model modules or weights, no network, and no generation.

## Primary result

| Attribute | Pooled-LFE Spearman rho | Fixed-panel description |
|---|---:|---|
| eyeglasses | 0.12060453783110545 | weak positive, close to zero |
| facial_hair | 0.4939912655897707 | moderate positive |

The primary family therefore does not show a uniform attribute-general pooled-LFE/outcome relationship. Within the eyeglasses panel, mean-pooled LFE margin barely co-varies with retention heterogeneity. Within the facial-hair panel, larger pooled-LFE margins tend to accompany larger retention outcomes. This difference is descriptive; it is not a statistical cross-attribute comparison.

## Complete representation-secondary family

| Stage | eyeglasses rho | facial_hair rho |
|---|---:|---:|
| insightface_l2_normalized | -0.5427204202399745 | 0.05002443195845779 |
| eva_head_l2_normalized | 0.44221663871405326 | 0.1563263498701806 |
| eva_hidden_0_patch_mean_l2_normalized | 0.0670025210172808 | 0.6440645614651441 |
| eva_hidden_1_patch_mean_l2_normalized | -0.12060453783110545 | 0.32515880772997563 |
| eva_hidden_2_patch_mean_l2_normalized | -0.18090680674665816 | 0.21885688981825285 |
| eva_hidden_3_patch_mean_l2_normalized | 0.06030226891555272 | -0.03126526997403612 |
| eva_hidden_4_patch_mean_l2_normalized | 0.4020151261036848 | 0.06878359394287946 |
| image_latent_first_frame_spatial_mean_l2_normalized | 0.4355163866123252 | 0.4252076716468912 |

The complete family is stage-heterogeneous. Eyeglasses changes sign across stages: InsightFace is negative, several intermediate EVA summaries are near zero or negative, while EVA head, EVA hidden 4, and the spatial reference latent are positive. Facial hair is positive at pooled LFE and several upstream/spatial stages, strongest descriptively at EVA hidden 0, but near zero at InsightFace, EVA hidden 3, and EVA hidden 4. This pattern is compatible with stage-specific readout and representational reorganization; it does not establish where information is lost or retained.

## Complete injection-secondary family

Rows are block groups and columns are denoising groups in early/middle/late order.

### Eyeglasses, unconditional branch

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.22110831935702663 | 0.25460957986566707 | 0.28811084037430745 |
| middle | 0.29481109247603554 | 0.3551133613915882 | 0.41541563030714096 |
| late | 0.2613098319673951 | 0.2613098319673951 | 0.17420655464493007 |

### Eyeglasses, text branch

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | 0.22110831935702663 | 0.16080605044147392 | 0.25460957986566707 |
| middle | 0.32161210088294784 | 0.3551133613915882 | 0.41541563030714096 |
| late | 0.3551133613915882 | 0.2613098319673951 | 0.17420655464493007 |

### Facial hair, unconditional branch

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | -0.13756718788575892 | -0.22510994381306007 | -0.06253053994807224 |
| middle | 0.006253053994807224 | 0.0 | -0.05627748595326502 |
| late | -0.16257940386498781 | -0.30639964574555395 | -0.2063507818286384 |

### Facial hair, text branch

| Block \ denoising | early | middle | late |
|---|---:|---:|---:|
| early | -0.06253053994807224 | -0.22510994381306007 | -0.06253053994807224 |
| middle | 0.006253053994807224 | 0.0 | -0.05627748595326502 |
| late | -0.17508551185460228 | -0.3376649157195901 | -0.2063507818286384 |

All 18 eyeglasses grid coefficients are positive (0.16080605044147392 to 0.41541563030714096). In this fixed panel, larger positive-minus-control scalar residual RMS tends to accompany better eyeglasses retention broadly across the measured grid. The similar patterns across CFG branches are descriptive and do not show branch equivalence or causal redundancy.

For facial hair, 14 of 18 coefficients are negative, two are exactly zero, and two are small positive values of 0.006253053994807224 (range -0.3376649157195901 to 0.006253053994807224). Thus the same scalar RMS contrast does not have a uniformly positive relationship with facial-hair retention. This is consistent with scalar residual RMS being an attribute-dependent and mechanistically incomplete observation; it does not show that RMS is useless or that the local route is irrelevant.

## Proposed scientific synthesis for researcher decision

1. **Representation–readout mismatch remains the most defensible explanation.** The weak eyeglasses pooled-LFE primary association coexists with positive EVA-head, EVA-hidden-4, and spatial-latent associations and a negative InsightFace association. The facial-hair panel also changes substantially by stage. These results fit reorganization or readout dependence better than a claim that attribute information simply disappears in LFE, but they do not prove reorganization.
2. **The multi-path, distributed-representation working model remains viable.** Positive spatial-latent associations for both panels coexist with attribute-dependent local scalar-RMS patterns and stage-dependent representation patterns. Linkage does not isolate either path and cannot establish compensation or interaction.
3. **Scalar residual RMS is not a universal directional mechanism measure.** Its association is broadly positive for eyeglasses and mostly nonpositive for facial hair. A vector direction, token pattern, query-state alignment, or path interaction could matter, but each remains an unverified mechanism hypothesis.
4. **The linkage identifies heterogeneity worth testing, not a location or bottleneck.** No grid cell may be selected as the place where an attribute is stored, lost, or causally used. The complete 36-cell family must remain intact.
5. **The unmapped 76 fallbacks remain only a run-level limitation.** They cannot be assigned to pairs and do not explain any individual coefficient.

## Still unverified

- Whether attribute information is reorganized across the 32 identity tokens rather than lost.
- Whether vector direction, tokenwise structure, or query-state alignment predicts retention better than scalar RMS.
- Whether the spatial reference-latent path compensates for weak pooled-LFE readout.
- Whether local and spatial paths interact causally, or whether either is necessary or sufficient.
- Whether any observed association replicates beyond these two fixed ten-pair panels, this model, or this experimental setup.

## Recommended next gate

The next scientific step should be a separately prespecified, CPU-first reanalysis design that evaluates richer already-captured trace summaries only if those summaries can be derived without changing frozen samples or rerunning generation. Any new model execution, activation capture, intervention, GPU use, route ablation, or generation requires a new explicit authorization and must not be inferred from these descriptive associations.
