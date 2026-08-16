# Pilot v3.1 fixed-video descriptive results

Status: **FROZEN_DESCRIPTIVE_REPORT_PENDING_INDEPENDENT_VERIFICATION**

## Scope

This report describes the 12 fixed videos only. Frames are correlated observations, not independent samples. No causal, population-level, or general-model inference is made.

## Overall evaluability

- Videos: 12
- Planned frames: 588
- Valid-observable frames: 524 (89.12%)
- Unobservable frames: 64 (10.88%)
- Pipeline-failure frames: 0

## Eyeglasses

- Present references (`ref_01`, `ref_02`): expected-label match fractions 0.979592 and 0.979592; video median p(present) 0.755249 and 0.751726.
- Absent references (`ref_03`, `ref_04`): expected-label match fractions 1.000000 and 1.000000; video median p(present) 0.101772 and 0.136202.
- Across these four fixed videos, 194/196 binary-eligible frames matched the planned label (0.989796). This pooled number is descriptive only.

## Facial hair

- All four fixed videos were observable on all 49 frames.
- `ref_05` and `ref_06` had ordinal median 2; `ref_07` and `ref_08` had ordinal median 0.
- All four had expected-label match fraction 1.000000 and adjacent binary flip rate 0.000000.
- The two submissions are byte-identical; the researcher has confirmed they were independently produced. No adjudication was required.

## Hair color

- `ref_09` (light): 34/49 observable; median L*=54.910278. The frozen visual review records a major generation artifact; the video remains included.
- `ref_10` (light): 49/49 observable; median L*=39.080811.
- `ref_11` (dark): 49/49 observable; median L*=7.812500.
- `ref_12` (dark): 0/49 observable; no L* estimate. It is retained as measurement-unavailable/low-coverage, with no exclusion or imputation.
- Because one dark video is wholly unmeasurable and the fixed sample is small and confounded, this arm is reported only as an exploratory result and measurement limitation. No cross-condition inference is performed.

## Governance checks

No p-values, regression, frame-level inference, imputation, post-hoc exclusion, selective rerun, seed change, causal claim, or general-model claim was used.
