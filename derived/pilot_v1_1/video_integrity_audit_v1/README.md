# Pilot v1.1 Video Integrity Audit v1

Status: `PASS`

This directory is a CPU-only engineering integrity audit of exactly 12 frozen MP4 files under protocol SHA256 `5012d924f3ee5b35b45dc8538791b67a6d08a377b18301a9266105bd8f37bbb0`. It does not evaluate identity or attributes and cannot test H1–H4.

Files:

- `video_integrity_audit_v1.csv`: video-level mappings, media properties, diagnostics, and status.
- `frame_inventory_v1.csv`: every decoded/expected frame and frozen diagnostics.
- `pilot_output_audit_v1.json`: aggregate decision and provenance.
- `pilot_video_contact_sheet_v1.png`: deterministic frames [0, 12, 24, 36, 48] for human engineering review only; it does not replace numerical auditing.
- `video_integrity_audit_v1.log`: append-only JSONL execution log.
- `run_environment_v1.json`: CPU runtime provenance.
- `input_output_sha256_v1.csv`: source and derived artifact hashes; its own hash is reported by the independent verifier and Git handoff.

No frozen artifact was modified, moved, or regenerated.
