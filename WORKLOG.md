# Work Log

## 2026-08-03 — Stage 1 intake and authorization

- **Research decision:** The researcher explicitly authorized G001 and G002 for one bounded stage: CPU-only Pilot v1.1 output integrity auditing under frozen protocol v1.
- **Fact:** Root `AGENTS.md`, all six governance files, manifest, config, readiness, evaluation protocol, metric specifications, reference audit results, generation summary, generation events, twelve generation metadata files, and the preserved generation log were read before implementation.
- **Fact:** Frozen core hashes match the governance registry, including canonical config SHA256 `40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47`.
- **Fact:** CPU decoder import preflight passed with Python 3.11.15, OpenCV 4.10.0, Decord 0.6.0, NumPy 1.26.4, and Pillow 10.4.0; `CUDA_VISIBLE_DEVICES` was empty and `torch` was not imported.
- **Fact:** No video container or video pixel had been opened at this checkpoint.
- **Next:** Implement versioned audit code and schemas, run dry-run and synthetic tests, then execute all twelve videos only if every preflight passes.
