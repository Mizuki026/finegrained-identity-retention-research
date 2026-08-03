# Pilot attribute evaluation v1 invalidity notice

Status: **invalid for expected-label-match summaries**; preserved, not overwritten.

## Fact

The independent output check found that the v1 implementation compares the eyeglasses prediction vocabulary `present` / `absent` directly to manifest labels `positive` / `negative`.  Consequently, the derived `eyeglasses_expected_label_match` field and its video-level fraction are zero even when the direction of the raw probability margin is consistent with the expected condition.

The v1 raw CLIP probabilities, margins, face-observability statuses, hair-colour values, and blinded facial-hair materials are preserved as execution artifacts.  This notice does not infer their scientific validity.

## Research decision

Do not use v1 expected-label-match outputs in any table, figure, claim, or manuscript.  Correct the fixed label mapping prospectively in the implementation, add a unit test, and run a new complete v2 output directory over the unmodified 12-video universe.  No v1 file will be edited, deleted, or reused as a substitute for the corrected run.
