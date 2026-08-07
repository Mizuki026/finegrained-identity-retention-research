# Worklog v4

## 2026-08-07 — One-time facial-hair unblinding and mapping verification

- **Research decision:** The researcher explicitly authorized a one-time private-mapping read for reconciliation only.
- **Diagnostic:** An unexecuted v1 implementation draft was found during code review to rehash the mapping while writing its checksum manifest. It was never run and was superseded prospectively by v2, which uses one in-memory mapping byte read and reuses its digest.
- **Fact:** v2 dry-run passed without reading mapping contents; it validated all public input hashes, frozen label/template closure, 12 manifest samples, and 1764 frame-inventory rows.
- **Fact:** v2 then read the private mapping exactly once (32,792 bytes), matched its registered SHA256 and exact three-column schema, and produced a 575-row reconciled table.
- **Fact:** all 575 rows matched the frozen label IDs, source sample/frame records, and manifest membership. The independent verifier did not read mapping contents and passed exact frozen-label preservation, ID/order closure, frame-inventory closure, and manifest join checks.
- **Fact:** no condition-level aggregation, model/GPU use, video access, dependency installation, network access, or frozen-input modification occurred.
- **Scientific boundary:** these results establish mapping integrity only; they do not establish an attribute effect or test H1–H4.
