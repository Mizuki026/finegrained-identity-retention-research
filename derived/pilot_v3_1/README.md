# Pilot v3.1 evidence package

This directory is the repository-sized evidence package for the completed
fixed-12-video Pilot. It contains small tabular, protocol, decision, and audit
artifacts copied byte-for-byte from the runtime workspace. Generated media,
reference images, model weights, logs, caches, and private mapping files are
not included.

## Evidence groups

- `freeze/`: pre-generation manifests and frozen generation/metric protocols.
- `generation/`: generation completion, engineering integrity, and the frozen
  visual-review decision; no media are stored here.
- `manual_annotation/`: the two frozen blinded submissions, agreement,
  consensus, and mapping-verification outputs; no private key is stored here.
- `analysis/`: finalized frame/video tables and deterministic verification.
- `report/`: conservative fixed-video descriptive report and verification.
- `governance/`: researcher decision and completion records.

## Claim boundary

The package supports descriptive statements about these 12 fixed videos only.
Frames are correlated observations, not independent experimental units. It
does not authorize causal, population, cross-model, or general ConsisID claims.
No p-values, regression, imputation, post-hoc exclusion, selective rerun, or
seed replacement were used.

The hair-colour arm is an exploratory measurement-limitation result. `ref_12`
is retained as measurement-unavailable/low-coverage without exclusion or
imputation. The two facial-hair submissions are byte-identical; the researcher
confirmed they were independently produced.
