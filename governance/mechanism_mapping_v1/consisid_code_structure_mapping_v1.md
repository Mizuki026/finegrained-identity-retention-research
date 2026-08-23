# ConsisID code-structure mapping v1

Status: **static mapping complete; no runtime mechanism finding**.

## 1. Scope and provenance

This is a read-only mapping of the ConsisID implementation used by the frozen
formal panel. It does not load model weights, execute a forward pass, inspect
new outcomes, generate video, or establish a causal mechanism.

- ConsisID repository: `/root/autodl-tmp/consisid-smoketest/ConsisID`
- Repository state: detached HEAD at
  `60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e`, clean working tree
- Formal checkpoint root:
  `/root/autodl-tmp/consisid-smoketest/ckpts/ConsisID-preview`
- Source and configuration hashes: `static_evidence_manifest_v1.csv`
- Formal runtime points to the same repository commit and checkpoint root in
  the frozen pre-generation master record.

Code structure establishes where information can flow. It does not establish
which attribute is represented, which module caused an observed failure, or
whether changing a module will improve generation.

## 2. End-to-end static map

| Stage | Actual object or call site | Input | Output or action | Code-supported role |
|---|---|---|---|---|
| Entry | `infer.generate` (`infer.py:67-118`) | reference image, prompt, seed | face conditions and pipeline call | Formal inference entry and argument handoff |
| Reference load | `process_face_embeddings_infer` (`models/consisid_utils.py:204-273`) | path or array | long-edge-1024 RGB image | Normalizes orientation and size before face processing |
| Detection and alignment | `process_face_embeddings` (`models/consisid_utils.py:130-157`) | RGB reference | largest detected face, 5-point landmarks, aligned 512x512 crop | Selects one face; falls back to `glintr100` embedding when the main InsightFace path does not detect a face |
| Face parsing | same function (`models/consisid_utils.py:163-179`) | aligned face | grayscale parsed face for EVA; color parsed face for I2V conditioning | Removes configured background/parts and creates two downstream image views |
| Global identity vector | `FaceAnalysis`/`glintr100` plus EVA head (`models/consisid_utils.py:133-194`) | largest-face embedding from the original image, or aligned-face fallback; grayscale parsed face for EVA | `id_cond`: 512-D InsightFace embedding concatenated with normalized 768-D EVA vector, shape `[B,1280]` | Compact identity condition supplied to the local facial extractor |
| Multi-scale local source | EVA visual encoder (`eva_vit_model.py:587-644`) | 336x336 normalized grayscale parsed face | five hidden states at loop indices 4, 8, 12, 16, 20; expected shape `[B,577,1024]` each | Patch-token features supplied to the local facial extractor |
| Local feature projection | `LocalFacialExtractor` (`models/transformer_consisid.py:85-184`) | `[B,1280]` plus five EVA hidden states | 32 learned-query tokens of width 2048 | Maps five identity tokens and multi-scale ViT features through ten Perceiver/FF layers, then projects to `[B,32,2048]` |
| Reference-image I2V branch | `prepare_latents` (`models/pipeline_consisid.py:424-523`) | color parsed aligned face | one VAE reference latent frame followed by zero latent frames | Separate channel-concatenated image-conditioning path; not the local cross-attention branch |
| Transformer input | denoising loop (`models/pipeline_consisid.py:934-959`) | noisy latents plus reference-image latents | 32-channel model input and identity arguments | Calls the transformer once per scheduler timestep |
| Base video/text blocks | `ConsisIDBlock` (`models/transformer_consisid.py:236-356`) | video tokens, text tokens, timestep embedding | updated video and text tokens | CogVideoX joint attention and feed-forward path |
| Local identity injection | `PerceiverCrossAttention` after selected blocks (`models/transformer_consisid.py:796-822`) | 32 identity tokens as K/V; all video tokens as Q | residual added to every video token | Direct local-identity injection site |
| Output | final norm/projection/unpatchify (`models/transformer_consisid.py:824-849`) | final video tokens | predicted latent-space model output | Feeds scheduler update; no identity-specific operation after the last injection |

## 3. Actual checkpoint topology

The frozen checkpoint configuration, rather than class defaults, determines
the active topology:

- No `transformer_ema` directory is present, so `infer.py` selects the
  `transformer` checkpoint subdirectory.

- `is_train_face=true`: the local identity branch is active.
- `is_kps=false`: keypoint conditioning is inactive. `infer.py` passes
  `face_kps`, but the pipeline sets `kps_cond=None` before latent preparation.
- `in_channels=32`: 16 noisy latent channels and 16 reference-image latent
  channels are concatenated before patch embedding.
- `num_layers=42`, `num_attention_heads=48`, `attention_head_dim=64`: video
  token width is 3072.
- `cross_attn_interval=2`: 21 distinct `PerceiverCrossAttention` modules are
  used after blocks `0,2,4,...,40`.
- `local_face_scale=1.0`: the local identity residual uses a constant scalar;
  no timestep-dependent schedule exists in this code path.
- The checkpoint index contains weights for the local facial extractor and all
  cross-attention modules `0` through `20`.
- The formal pipeline uses 50 inference steps. The transformer is called once
  inside each scheduler iteration, so the same reference-derived branch is
  available at all 50 steps and all 21 injection sites. The injected residual
  can still vary because its video-token queries vary by block and timestep.

## 4. Two distinct reference-conditioning routes

### 4.1 Reference-image latent route

The color parsed aligned crop is resized to the pipeline resolution and VAE
encoded. Its latent occupies the first latent frame; remaining reference-latent
frames are zero. At every denoising step this tensor is concatenated with the
noisy video latent along the channel dimension before patch embedding.

This path is spatially structured and is part of the base I2V model input. An
ablation of only `local_face_scale` would leave this route active.

### 4.2 Local identity-token route

The 1280-D compact identity condition and five EVA token maps are fused into 32
tokens. Each selected post-block cross-attention module lets every video token
query those 32 tokens, and adds the result as a residual.

The code contains no target-attribute mask, video-space face-region mask, or
attribute-specific selector in this route. “Local” refers to face-crop-derived
reference features; the injection itself addresses all video tokens.

## 5. Timestep and classifier-free-guidance behavior

- `id_cond` and `id_vit_hidden` are passed unchanged at every scheduler step.
- `LocalFacialExtractor` is called inside `transformer.forward`, so its 32-token
  output is recomputed for every transformer call and has no explicit timestep
  input.
- Cross-attention has no explicit timestep gate. Timestep can influence its
  output indirectly through the block-updated query tokens.
- With formal guidance scale 6.0, video/text inputs are doubled for classifier-
  free guidance. The identity inputs are not explicitly duplicated in the
  pipeline. Static tensor semantics indicate that the singleton identity batch
  is broadcast in cross-attention; this specific runtime behavior remains to be
  confirmed by instrumentation.

## 6. Candidate instrumentation points

These are code locations, not approved measurements:

1. Reference representation: `id_ante_embedding`, `id_cond_vit`, the five
   `id_vit_hidden` tensors, and the 32-token `valid_face_emb` output.
2. Injection delivery: the output of each
   `perceiver_cross_attention[ca_idx]` before multiplication by
   `local_face_scale` and residual addition.
3. Post-injection persistence: paired pre/post-injection video-token summaries
   at blocks `0,2,...,40`, indexed by scheduler step.
4. Route separation: local identity route versus the independently active
   reference-image latent route.
5. Output connection: scheduler input/output latents without decoding or
   treating frames as independent units.

Instrumentation must use bounded online summaries or pre-authorized tensor
storage. Raw identity embeddings and reference-linked outputs must not be
committed or published.

## 7. What this audit does not verify

- It does not show that eyeglasses or facial-hair information is decodable at
  any listed tensor.
- It does not locate a representation, injection, or suppression bottleneck.
- It does not show that local-feature scaling, layer ablation, or timestep
  scheduling improves attribute retention.
- It does not distinguish identity preservation from generic image-conditioning
  effects.
- It does not support causal, population, model-wide, frame-independent, or
  cross-attribute conclusions.

The next transition is governed by `mechanism_iteration_review_gate_v1.md`.
