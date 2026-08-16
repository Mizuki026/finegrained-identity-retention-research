# Worklog v6

## 2026-08-16 — Fixed-video Pilot completion and evidence packaging

- **Fact:** unified generation completed for all 12 frozen references without
  seed changes, selective reruns, or post-hoc exclusions.
- **Fact:** finalization produced 588 frame rows and 12 video rows: 524 frames
  were valid-observable, 64 were unobservable, and none had pipeline failure.
- **Fact:** two independently produced facial-hair submissions were frozen;
  their bytes and all 196 ordinal labels were identical, so no adjudication was
  required. The researcher explicitly confirmed independent provenance.
- **Fact:** deterministic finalization and the conservative descriptive report
  each passed a separate exact-recalculation and hash verification.
- **Research decision:** retain `ref_12` as low-coverage and measurement
  unavailable, with no exclusion or imputation.
- **Research decision:** treat the hair-colour arm as an exploratory
  measurement-limitation result only.
- **Research decision:** claims remain descriptive for the 12 fixed videos;
  no causal, population, frame-level inferential, or general-model claim is
  permitted.
- **Archive action:** 38 small evidence artifacts were copied byte-for-byte
  into `derived/pilot_v3_1`; media, images, weights, logs, and private mapping
  files were excluded.
