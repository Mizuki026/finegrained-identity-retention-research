# Work Log

## 2026-08-03 — Stage 1 intake and authorization

- **Research decision:** The researcher explicitly authorized G001 and G002 for one bounded stage: CPU-only Pilot v1.1 output integrity auditing under frozen protocol v1.
- **Fact:** Root `AGENTS.md`, all six governance files, manifest, config, readiness, evaluation protocol, metric specifications, reference audit results, generation summary, generation events, twelve generation metadata files, and the preserved generation log were read before implementation.
- **Fact:** Frozen core hashes match the governance registry, including canonical config SHA256 `40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47`.
- **Fact:** CPU decoder import preflight passed with Python 3.11.15, OpenCV 4.10.0, Decord 0.6.0, NumPy 1.26.4, and Pillow 10.4.0; `CUDA_VISIBLE_DEVICES` was empty and `torch` was not imported.
- **Fact:** No video container or video pixel had been opened at this checkpoint.
- **Fact:** Versioned audit code, output schema, synthetic tests, and an independent no-decode verifier were implemented before real-video access.
- **Diagnostic:** A first unit-test invocation used the unrelated Python 3.10.8 base environment and stopped during import because it lacked `cv2`; no test body or video access occurred.
- **Fact:** The already-installed Pilot environment passed all 6 synthetic tests. No dependency was installed.
- **Fact:** Implementation commit `52a0650aab6065ae20e894f62136517e2205aaa0` froze the producing code before dry-run and decoding.

## 2026-08-03 — Stage 1 execution and Human Gate A

- **Fact:** The no-decode dry-run passed for all 12 samples with clean Git worktrees and matching frozen hashes, mappings, metadata, events, and registry entries.
- **Fact:** The full CPU-only audit opened and completely decoded all 12 MP4 files with OpenCV and Decord. It created only the new versioned derived directory.
- **Fact:** Video integrity status was PASS for 12/12. Each decoder returned 49 frames per video; all media were 8.0 FPS, 6.125 seconds, and 720×480.
- **Diagnostic:** Counts were zero for corrupt frames, black frames, exact duplicate transitions, near-duplicate transitions, frozen runs, and static-video anomalies.
- **Fact:** The independent no-decode verifier passed: 12 video rows, 588 frame rows, exact sample/path/hash/schema closure, status/aggregate agreement, and checksum verification.
- **Diagnostic:** Engineering-only contact-sheet review found no obvious blank, broken, wholly static, or cross-row duplicated sequence. Identity and attribute labels were not evaluated.
- **Fact:** No GPU or model was loaded; no network access or dependency installation occurred; no video was regenerated; no frozen artifact was modified, moved, deleted, or overwritten.
- **Research decision:** G001 and G002 are closed. G003–G010 remain closed. Work stops at Human Gate A pending researcher review.
