# Pilot attribute evaluation status update v1

## Facts

- `attribute_evaluation_v1` is preserved but invalid for eyeglasses expected-label-match summaries because of a label-vocabulary mapping defect.
- Corrected `attribute_evaluation_v2` completed CPU-only/offline over the fixed 12-video universe. It contains 1,764 frame-attribute rows and 12 intended-attribute summary rows.
- The independent count/schema check passed. Eyeglasses had 575 valid-observable and 13 unobservable rows; hair colour had 330 valid-observable and 258 unobservable rows; neither has pipeline-failure rows.
- Facial-hair manual results remain absent: 575 anonymous crops and 23 randomized sheets exist, but the available operator was unblinded by necessary implementation work and cannot produce a valid condition-blinded annotation.

## Claim boundary

The manuscript draft may report integrity, eyeglasses, and hair-colour descriptive facts with their stated coverage. It must not report a facial-hair result or promote any Pilot pattern to H1-H4, a cross-attribute ranking, general metric validity, or mechanism.

## Next valid action

Give the anonymous sheets to an independent condition-blinded human annotator using the frozen ordinal rubric; preserve raw labels before opening the private mapping. Then create a new derived reconciliation artifact and revise the manuscript in a new version.
