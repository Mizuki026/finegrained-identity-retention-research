# An auditable exploratory pilot of fine-grained attribute observations in reference-conditioned video generation

## Abstract

Fine-grained visible attributes may not be captured by generic identity-retention claims. We conducted a fixed, descriptive Pilot v1.1 of twelve reference-conditioned videos generated with the frozen ConsisID pipeline. All 12 MP4 files passed a pre-specified engineering integrity audit (49 decoded frames/video; 8 fps; 720 x 480). We then applied frozen output-level instruments to every frame: an InsightFace-cropped, local CLIP ViT-B/32 eyeglasses score and a BiSeNet class-17 core-hair CIELAB L* measure. Four eyeglasses videos had 49/49 observable frames each and their expected-condition match fractions were 1.000 under the frozen zero-margin rule. Hair-colour coverage ranged from 0.776 to 1.000, with median reference-relative absolute L* deviations from 1.074 to 17.606. Facial-hair manual annotation was intentionally withheld because the available operator had already seen condition metadata and could not truthfully serve as condition-blinded; no facial-hair result is claimed. These measurements are an auditable, confounded case study, not a test of H1-H4, a general evaluation of ConsisID, or a causal account of attribute loss.

## 1. Introduction

Reference-conditioned video generation aims to retain identity while producing motion. ConsisID is a frequency-decomposition-based identity-preserving text-to-video system [@yuan2025consisid]. Its reported objective does not itself establish retention of individual visible properties. We therefore ask a narrower measurement question: *what do pre-specified output-level instruments observe for a fixed, small set of generated videos, after basic media integrity is verified?*

The study preserves four prospective hypotheses without treating the Pilot as their test. H1 states that identity-related attributes are not uniformly preserved; H2 concerns associations with attribute properties; H3 concerns location/timestep information and requires probe/intervention evidence; H4 predicts coarse hair-colour retention/stability exceeding local fine-grained attributes. The present fixed, identity-confounded sample cannot establish any of these hypotheses.

## 2. Methods

### 2.1 Design and frozen inputs

The Pilot sample universe was a frozen 12-row manifest: four eyeglasses, four facial-hair, and four hair-colour conditions. Each video used the frozen prompt/configuration and contains 49 correlated frames. Frames are repeated observations for temporal description and observability accounting, not independent observations. The canonical configuration SHA256 was `40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47`.

### 2.2 Engineering integrity

Before attribute evaluation, a CPU-only audit checked mappings, byte hashes, container readability, full decode by OpenCV and Decord, frame count, frame rate, duration, resolution, corrupted frames, black frames, duplicate-like transitions, frozen runs, and static-video anomalies. The audit protocol and thresholds were frozen before video-pixel access. It returned PASS for all 12 videos; each decoder reported 49 frames, 8 fps, 6.125 s, and 720 x 480.

### 2.3 Frozen output-level instruments

For eyeglasses, the protocol selected the largest locally detected InsightFace face, applied the frozen deterministic square crop, and scored it with local CLIP ViT-B/32 against four positive and four negative prompts. CLIP is a language-supervised image-text model [@radford2021clip], not a dedicated eyeglasses detector; the four-reference audit demonstrates only frozen-reference-set usability. The label boundary was the frozen probability margin of zero.

For hair colour, local BiSeNet [@yu2018bisenet] class-17 pixels were intersected with a prospectively specified upper-head core ROI, largest-component and 7 x 7 erosion rules. A frame required at least 1,000 core-mask pixels; the reported measure is continuous median CIELAB L*, reference-relative and without a light/dark classification cutoff. The coordinate convention missing from the legacy metric specification was written and versioned before any generated-frame evaluation.

The frozen facial-hair procedure is manual ordinal annotation with condition blinding. We created 575 anonymous face crops and 23 randomized contact sheets. The present operator had previously accessed sample/condition metadata while implementing and validating the pipeline, so this operator is not a valid blinded annotator. We therefore report no facial-hair label or match summary.

### 2.4 Analysis boundary

We report per-video coverage and descriptive valid-frame summaries only. There are no p-values, cross-attribute composite scores, frame-independent tests, causal claims, or post-hoc thresholds. Missing and unobservable frames are not counted as attribute absence.

## 3. Results

### 3.1 Integrity and observability

All 12/12 videos passed engineering integrity. Across the full 588-frame universe, eyeglasses had 575 valid-observable and 13 unobservable frames; hair colour had 330 valid-observable and 258 unobservable frames; facial-hair rows remain unobservable/pending annotation by design. No attribute pipeline-failure frame was recorded.

### 3.2 Eyeglasses

Each of the four eyeglasses-target videos had 49 valid frames (coverage 1.000). Mean P(eyeglasses) was 0.672 and 0.785 for the two positive conditions, and 0.127 and 0.178 for the two negative conditions. The descriptive expected-condition match fraction was 1.000 for each of the four videos. Figure 1 visualizes these frozen-instrument summaries. These observations are confined to four fixed identities/conditions and do not validate CLIP on generated video generally or establish a model-level retention rate.

### 3.3 Hair colour

The four hair-colour videos had valid-frame coverage of 1.000, 0.959, 0.776, and 1.000. Median absolute deviation from the associated reference L* was 6.012, 17.606, 1.074, and 1.532, respectively. Figure 2 shows these reference-relative quantities. They are continuous measurement summaries, not light/dark decisions. Coverage and illumination/segmentation limitations prevent interpreting between-video differences as an attribute-granularity effect.

### 3.4 Facial hair

No facial-hair outcome is reported. This is a missing planned measurement, not evidence of absence, failure, or retention.

## 4. Discussion

The Pilot establishes a reproducible evidence path: frozen input hashes, full media integrity verification, local CPU-only evaluation, raw frame tables, explicit unobservable states, and versioned derived figures. It illustrates why an identity-retention workflow needs attribute-specific observability accounting.

The results do not test H1-H4. The sample is small and identity is confounded with attribute condition; prompt, identity, lighting, photographic domain, and attribute label are not separable. The Turing reference also has a historical monochrome-domain confound. Reference audits are not video-domain validation. A larger preregistered study must use matched identities/seeds, fixed sampling and exclusions, prespecified endpoints/statistics, independent blinded facial-hair annotation, uncertainty reporting, and replication before any comparative or causal claim.

## Data and code availability

Frozen inputs remain outside the research-code repository. Derived CSVs, SHA256 manifests, analysis scripts, governance documents, and manuscript traceability tables are versioned under `research_pipeline`. No frozen MP4, reference image, weight, or upstream ConsisID source file was modified.

## References

[@radford2021clip; @yuan2025consisid; @yu2018bisenet]
