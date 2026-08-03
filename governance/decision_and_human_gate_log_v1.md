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

## Gate transition entries

| Transition ID | Date (UTC) | Actor / authority | Gate | New state | Exact scope | Consequence |
|---|---|---|---|---|---|---|
| T001 | 2026-08-03 | Researcher explicit authorization in project handoff turn | G001 | OPEN FOR ONE STAGE | Implement, dry-run, synthetic-test, and execute the frozen CPU-only Pilot v1.1 integrity audit over all 12 existing MP4 files | May create only the versioned Stage 1 code, logs, and derived integrity artifacts governed by protocol v1. |
| T002 | 2026-08-03 | Researcher explicit authorization in project handoff turn | G002 | OPEN ONLY WITH G001 | Read all 12 video containers and pixels solely for frozen integrity diagnostics and deterministic contact sheet generation | Does not authorize identity or attribute measurement. |
| T003 | 2026-08-03 | Researcher explicit stop condition | G003–G010 | REMAIN CLOSED | Attribute scoring, annotations, regeneration, GPU/model use, dependency/network changes, formal experiments, probing/intervention, threshold/sample/statistical/claim changes | Stage 1 must stop at Human Gate A after its commit and report. |
| T004 | 2026-08-03 | Stage completion under T001–T002 | G001–G002 | CLOSED | The authorized 12/12 CPU-only integrity audit and contact-sheet creation are complete | No further video decoding or pixel reading is authorized in this stage. |
| T005 | 2026-08-03 | Researcher explicit stop condition plus completed Stage 1 evidence | Human Gate A | AWAITING RESEARCHER DECISION | Review PASS 12/12 audit outputs, zero frozen-threshold anomalies, independent verification, and engineering-only contact sheet | G003 remains closed; no identity or attribute evaluation may start without a new explicit authorization. |

## Human review gates

| Human gate | State | Evidence package | Allowed next action |
|---|---|---|---|
| Human Gate A — Pilot output integrity | AWAITING RESEARCHER DECISION | `derived/pilot_v1_1/video_integrity_audit_v1/`; producer commit `52a0650aab6065ae20e894f62136517e2205aaa0`; independent verification SHA256 `12075e958cf16c6345be5f3d46a024fcedc91e8a4cbe9f8c1f62faf128ae2b83` | Researcher may accept, reject, or request a prospective follow-up. Attribute evaluation remains unauthorized until acceptance plus separate scope approval. |

## Post-Stage-1 authorization entries

| Decision ID | Date (UTC) | Status | Decision | Basis / authority | Consequence |
|---|---|---|---|---|---|
| D011 | 2026-08-03 | Active | The researcher accepted Human Gate A and authorized autonomous progression through a paper draft under all existing evidence, immutability, and fail-closed rules. | Explicit researcher directive in the active conversation | Governance, prospective protocol/code preparation, evidence organization, and manuscript infrastructure may proceed without per-microstep approval. |
| D012 | 2026-08-03 | Active | The autonomy directive does not silently waive operation-specific protections. | Existing AGENTS and safety policy remain in force | Model/GPU, network/install, regeneration, formal compute, probe/intervention, frozen-design change, and unblinded human annotation need their own recorded scope decision before execution. |

| Transition ID | Date (UTC) | Actor / authority | Gate | New state | Exact scope | Consequence |
|---|---|---|---|---|---|---|
| T006 | 2026-08-03 | Researcher autonomous-work directive | Human Gate A | ACCEPTED | Stage 1 integrity evidence package | The project may leave the Human Gate A stop point. |
| T007 | 2026-08-03 | Researcher autonomous-work directive | G003 | OPEN FOR PROTOCOL AND CODE PREPARATION ONLY | Freeze prospective evaluation/analysis plans and develop/test non-model infrastructure without reading new video pixels | Attribute-result execution remains contingent on the applicable pixel/model/annotation gate. |
| T008 | 2026-08-03 | Prospective package completion | G003 planning scope | COMPLETED | Attribute execution protocol v1, analysis/claim plan v1, schema, and paper traceability tables | Execution cannot begin until its operational gates are explicitly opened. |
| T009 | 2026-08-03 | Existing safety policy retained | G002; G004; G006; G007; G008; G009; G010 | REMAIN CLOSED | Video pixel reads for evaluation; annotation; model/GPU; network/install; formal study; probe/intervention; frozen-design changes | A future transition must name the exact operation, resources, budget, and inputs. |

## Current human-gate status (superseding the earlier awaiting row)

| Human gate | State | Consequence |
|---|---|---|
| Human Gate A — Pilot output integrity | ACCEPTED | Prospective protocol and traceability work is complete; execution remains blocked by T009. |

| Transition ID | Date (UTC) | Actor / authority | Gate | New state | Exact scope | Consequence |
|---|---|---|---|---|---|---|
| T010 | 2026-08-03 | Researcher explicit execution authorization | G002; G004; G006 | OPEN FOR ONE RUN | CPU-only offline evaluation of all 12 frozen MP4 files and all 49 frames; local InsightFace, CLIP ViT-B/32, and BiSeNet; frozen blinded single-annotator facial-hair protocol | May create only new versioned evaluation artifacts; no GPU, network, install, regeneration, or protocol change. |
| T011 | 2026-08-03 | Researcher scope boundary | G005; G007; G008; G009; G010 | REMAIN CLOSED | Regeneration; network/install; formal study; probe/intervention; frozen-design or main-claim change | This authorization cannot be reused for later runs or broader operations. |

| Human Gate | State | Consequence |
|---|---|---|
| Pilot attribute evaluation execution | OPEN FOR ONE RUN | Execute the frozen protocol once, then stop for verification and a new human gate. |

| Transition ID | Date (UTC) | Actor / authority | Gate | New state | Exact scope | Consequence |
|---|---|---|---|---|---|---|
| T012 | 2026-08-03 | Researcher explicit all-permissions / paper-draft directive | G005–G010 | OPEN AS NEEDED, PROSPECTIVELY RECORDED | Autonomous work required to complete a rigorous paper draft, including local model evaluation and, if scientifically justified, network, installation, regeneration, or formal follow-up | Existing frozen artifacts remain immutable; each material new design or execution decision must be versioned before its results are inspected. |
