# Facial-hair unblinding and mapping verification v1

## Research decision and scope

- **Date (UTC):** 2026-08-07.
- **Authority:** Researcher explicitly authorized opening the private mapping and one-time unblinding/mapping verification.
- **Scope:** Join the already frozen anonymous label table to the private mapping; validate the complete mapping against the frozen frame inventory and manifest; create only lineage/audit artifacts.
- **Out of scope:** condition-level summaries, positive/negative comparisons, hypothesis tests, changes to labels, changes to exclusions, video access, model/GPU use, and manuscript-result revision.

## Input closure

| Input | SHA256 | Validation |
|---|---|---|
| Frozen blinded labels | `4f0f9117b9853c4a590e5f5f85eb26154c7cfb64ecb6f3b88b0d91d2684e2824` | 575 rows; frozen under D013 |
| Private mapping | `25c193ce53bbe9cb57c4629f3775c5b73f20a43c0c71cf30645c9dd00c3c678b` | 575 rows; exact schema `annotation_item_id,sample_id,frame_index` |
| Anonymous template | `246059e6b6a03a275e797e27799b2cb8a44e4060b097a732507b7a91be25dc9a` | 575 ordered anonymous IDs |
| Frame inventory | `805df7257f1d207a1d693a21337b79e65269246a3fffbcdee3555569cd0e06d3` | 1764 rows; 575 nonempty facial-hair annotation IDs |
| Pilot manifest | `dcf66f0222986403493a7c9a09d310629909d4aef590634348b41ce12544f79d` | 12 unique sample IDs |
| Pilot config | `40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47` | canonical frozen config hash |

## Execution facts

- **Fact:** the producer read private mapping contents exactly once, as one 32,792-byte in-memory byte read; its SHA256 matched the expected frozen value.
- **Fact:** the private mapping had 575 unique anonymous IDs and exactly matched the frozen label ID set.
- **Fact:** all 575 reconciled rows matched their source frame inventory `sample_id` and `frame_index`; all referenced samples existed in the frozen manifest.
- **Fact:** independent verification did not read the private mapping and confirmed exact preservation of all frozen label fields, random order, anonymous ID order, frame-inventory closure, and manifest join.
- **Fact:** no condition-level analysis was performed.

## Derived artifacts

- Reconciled table: `derived/pilot_v1_1/facial_hair_unblinding_v1/facial_hair_annotation_unblinded_v1.csv`, SHA256 `e97e3f4f8b2e1b11d9463a5d1bb78fe816989700cc8fa3e8934a5a9efe61050c`.
- Producer audit: `derived/pilot_v1_1/facial_hair_unblinding_v1/facial_hair_unblinding_audit_v1.json`, SHA256 `645fb9db8340606008801250ddc53ae7a13cb4d64cc5acc2e31eac2c54ad6c15`.
- Independent verification: `derived/pilot_v1_1/facial_hair_unblinding_v1/facial_hair_unblinding_independent_verification_v1.json`, SHA256 `ceef889c06f72298adca9f8be82781e68369855280450b20cff2a1cc06638a91`.

## Evidence boundary and next gate

**Fact:** the anonymous annotations are now reconciled to valid frozen sample/frame records.

**Not established:** facial-hair retention by condition, any positive/negative contrast, H1–H4, identity retention, general metric validity, or a causal/mechanistic conclusion.

This stage stops before any descriptive aggregation. A separate researcher authorization is required to create a prospective analysis script and run descriptive video-level facial-hair summaries.
