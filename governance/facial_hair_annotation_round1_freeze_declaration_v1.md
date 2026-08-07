# Facial-hair annotation round 1 freeze declaration v1

## Research decision

- **Date (UTC):** 2026-08-07
- **Authority:** Researcher explicit instruction: “将上述填充 CSV 宣告为冻结标注”.
- **Decision:** The anonymous, condition-blinded round-1 facial-hair annotation table identified below is frozen and immutable.
- **Scope:** This decision freezes the annotation bytes and anonymous item/order-to-label assignments only. It does not authorize opening the private mapping, unblinding, condition-level aggregation, hypothesis testing, or manuscript-claim revision.

## Frozen artifact

- **Path:** `derived/pilot_v1_1/facial_hair_annotation_round1_v1/annotation_round1_filled_v1.csv`
- **SHA256:** `4f0f9117b9853c4a590e5f5f85eb26154c7cfb64ecb6f3b88b0d91d2684e2824`
- **Rows:** 575 data rows, plus one header row.
- **Anonymous order:** exactly integers 1 through 575, once each.
- **Anonymous item IDs:** 575 unique values; exact ID/order lineage matches the blank template.
- **Label counts:** `0=291`, `1=146`, `2=84`, `U=54`.
- **Unobservable reasons:** `ambiguous_shadow=49`, `character_transformation=5`.

## Validation evidence

- Frozen manual protocol SHA256: `307f2afb4eb92280359960b70eff81cc188d26a60876db896e451f84cc6f25aa`.
- Blank anonymous template SHA256: `246059e6b6a03a275e797e27799b2cb8a44e4060b097a732507b7a91be25dc9a`.
- Preserved raw transcript SHA256: `db9039ae72b8ee6949e3077165d76ab8572c62cc3b83e6110a3e63ef560c7aea`.
- Transcription validation SHA256: `37ce4795af606d87170e86b625ff110605a5175f5d339d98ff496694faa0ec99`.
- Independent pre-unblinding validation SHA256: `667febe13716d2eb216d46a0bbf4a97dd2f074f5d1e16e95a356a18cfb42a4c2`.
- Both validation paths passed. Both recorded `private_mapping_read=false` and `unblinding_authorized=false`.

## Immutability and correction rule

The frozen CSV must not be edited, overwritten, renamed, moved, deleted, or selectively filtered. Any later correction requires a new versioned CSV, an explicit reason, complete parent lineage, a new SHA256, and a separately recorded researcher decision. This v1 artifact remains preserved even if superseded.

## Evidence boundary

**Fact:** the artifact contains a complete and independently schema-validated set of 575 anonymous labels.

**Research decision:** these exact anonymous assignments are now frozen.

**Not established:** condition-specific facial-hair retention, association with positive/negative prompting, identity preservation, H1–H4, general metric validity, or a causal/mechanistic result.

## Gate state

The private mapping remains unopened. Unblinding and reconciliation require a separate explicit authorization and must first verify the frozen CSV and mapping hashes without modifying either input.
