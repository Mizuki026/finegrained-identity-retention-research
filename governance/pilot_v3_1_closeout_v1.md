# Pilot v3.1 closeout and claim boundary v1

- Status: `PILOT_V3_1_CURRENT_SCOPE_COMPLETE`
- Analysis unit: video
- Fixed sample: 12 references, one video and one fixed seed per reference
- Frame universe: 49 correlated frames per video; 588 planned frames
- Formal generation: 12/12 completed
- Final evaluation: 524 valid-observable, 64 unobservable, 0 pipeline-failure
- Independent finalization verification: PASS
- Independent descriptive-report verification: PASS

## Researcher decisions

The researcher confirmed that the byte-identical facial-hair submissions were
produced independently. The researcher also authorized the following fixed
reporting treatment:

1. retain `ref_12` as measurement-unavailable/low-coverage;
2. perform no exclusion or imputation for `ref_12`;
3. report hair colour only as an exploratory result and measurement limitation;
4. limit claims to descriptive results for these 12 fixed videos; and
5. make no causal, population, frame-independent, or general-model inference.

## Descriptive evidence

- Eyeglasses: the two present-target videos each matched 48/49 binary-eligible
  frames; both absent-target videos matched 49/49. The four-video pooled value
  194/196 is descriptive only.
- Facial hair: all four videos had 49/49 observable labels and 49/49 expected
  matches; all adjacent binary flip rates were zero.
- Hair colour: valid coverage was 34/49, 49/49, 49/49, and 0/49 for `ref_09`
  through `ref_12`. Their median L* values were 54.910278, 39.080811,
  7.812500, and unavailable, respectively. The frozen visual review records a
  major generation artifact for `ref_09`; it remains included.

## Prohibited retrospective actions

- no sample or frame exclusion;
- no imputation;
- no seed change or selective rerun;
- no post-hoc threshold selection;
- no treatment of frames as independent samples; and
- no promotion of these Pilot observations to a general or causal claim.

## Transition

The completed Pilot may now inform a prospectively frozen formal-experiment
design. It does not itself determine the formal experiment's primary
