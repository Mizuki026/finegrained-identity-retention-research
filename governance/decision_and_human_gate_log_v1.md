# Decision and Human Gate Log v1

- Log ID: `finegrained_decision_human_gate_v1`
- Created: 2026-08-03 UTC
- Policy: append-only decisions; corrections are new superseding entries, never silent edits

## Recorded decisions

| Decision ID | Date (UTC) | Status | Decision | Basis / authority | Consequence |
|---|---|---|---|---|---|
| D001 | 2026-08-03 | Active | Treat H1–H4 as untested hypotheses. | Researcher directive and evidence boundary | No Pilot or mechanism claim may be written as a finding. |
| D002 | 2026-08-03 | Active | Treat reference audits as usability evidence only on their frozen reference sets. | Frozen metric protocols | No claim of general or video-domain metric validity. |
| D003 | 2026-08-03 | Active | Treat 12/12 generation success as generation-chain success only. | Generation summary/log plus researcher directive | Integrity, identity, and attribute retention remain unevaluated. |
| D004 | 2026-08-03 | Active | The canonical `config.json` SHA256 is `40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47`. | Disk and experiment-chain agreement; researcher designated it authoritative | The 65-character handoff transcription is ignored; no frozen artifact is rewritten. |
| D005 | 2026-08-03 | Active | Keep upstream ConsisID read-only and create a separate `research_pipeline` Git repository. | Researcher directive | Research code and governance must not enter `code/ConsisID`. |
| D006 | 2026-08-03 | Active | Freeze the integrity-audit protocol before any video container or pixel access. | Researcher directive | Thresholds and PASS/FAIL rules are prospective and immutable for v1. |
| D007 | 2026-08-03 | Active | Byte-size and whole-file SHA256 collection is allowed for governance; video opening/decoding is not. | Researcher directive | Registry hashes may be recorded now without starting the audit. |
| D008 | 2026-08-03 | Active | The next scientific task is a CPU-only integrity audit, but this governance round stops before executing it. | Researcher directive | A new approval is required before container open or pixel read. |
| D009 | 2026-08-03 | Active | Use strict gross-failure thresholds in `video_integrity_audit_protocol_v1.md`; isolated duplicate-like transitions are diagnostic, while black frames, frozen runs, or static-video anomalies fail visual integrity. | Prospective protocol decision before pixel access | Thresholds cannot be adjusted after results are visible. |
| D010 | 2026-08-03 | Active | Planned derived audit artifacts live under a new versioned `research_pipeline/derived/pilot_v1_1/video_integrity_audit_v1` path. | Non-overwrite and lineage requirements | No existing Pilot artifact is overwritten or colocated ambiguously. |

## Current gates

| Gate ID | Operation | State | Required approval/evidence |
|---|---|---|---|
| G001 | Execute CPU-only Pilot v1.1 integrity audit | CLOSED | Researcher must explicitly authorize execution after reviewing the frozen governance commit and protocol hash. |
| G002 | Read video pixels or create contact sheets | CLOSED | Opens only with G001 and only under protocol v1. |
| G003 | Run identity or attribute evaluation | CLOSED | Integrity audit reviewed and passed plus separate researcher approval. |
| G004 | Perform facial-hair human annotation | CLOSED | Frozen blinding/randomization materials and separate approval. |
| G005 | Regenerate any video | CLOSED | Explicit researcher decision; failed integrity never opens this gate automatically. |
| G006 | Load a model or access GPU | CLOSED | Explicit scope and compute-budget approval. |
| G007 | Install dependencies or access network | CLOSED | Explicit dependency/network approval. |
| G008 | Begin formal experiment | CLOSED | Pilot go/no-go plus frozen preregistration, statistics, sampling, exclusions, budget, and stopping rules. |
| G009 | Begin probe/intervention/method development | CLOSED | Validated output-level effect plus separately frozen mechanism protocol and approval. |
| G010 | Change frozen thresholds, samples, metrics, exclusions, or primary claims | CLOSED | New prospective version and explicit researcher decision; never retroactive. |

## Append-only procedure

Future entries must include UTC time, actor/authority, exact requested scope, affected artifact IDs, decision, rationale, and whether they supersede an earlier entry. A superseded entry remains visible. Verbal or inferred permission is insufficient for a closed gate.
