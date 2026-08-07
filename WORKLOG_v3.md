# Worklog v3

## 2026-08-07 — Anonymous facial-hair transcription and freeze

- **Fact:** 575 researcher-supplied anonymous facial-hair annotations were transcribed automatically into a new CSV without reading the private mapping.
- **Fact:** transcription preflight and an independently implemented verifier both passed: 575 rows, exact order 1–575, 575 unique anonymous IDs, exact template lineage, valid label/reason schema, and matching SHA256 values.
- **Fact:** label counts before unblinding are `0=291`, `1=146`, `2=84`, and `U=54`; the 54 unobservable reasons comprise 49 `ambiguous_shadow` and 5 `character_transformation` entries.
- **Research decision:** the researcher explicitly declared `annotation_round1_filled_v1.csv`, SHA256 `4f0f9117b9853c4a590e5f5f85eb26154c7cfb64ecb6f3b88b0d91d2684e2824`, frozen and immutable.
- **Fact:** no private mapping was read and no unblinding, condition-level aggregation, video access, model/GPU use, dependency installation, or network access occurred in this stage.
- **Scientific boundary:** the anonymous label distribution is not a condition result and does not test H1–H4.
