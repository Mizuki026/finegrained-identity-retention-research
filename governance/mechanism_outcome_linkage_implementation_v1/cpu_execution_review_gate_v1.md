# Mechanism–outcome linkage CPU execution review gate v1

Status: **implementation review required; real input audit, join, and association computation remain unauthorized**.

The researcher accepted all seven design decisions and authorized only analyzer
and independent-verifier implementation, CPU-only synthetic tests, and a
no-weight dry-run that does not open the frozen linkage inputs.

Before any real linkage execution, separately freeze and independently verify:

1. the final analyzer and verifier source bytes and SHA256 values;
2. the exact approved-plan path, bytes, and SHA256;
3. all four input paths, bytes, SHA256 values, exact CSV headers, and exact key
   universes without changing any source;
4. one new external runtime directory, its output schema, no-overwrite policy,
   and external-only handling of joined pseudonymous pair tables;
5. the exact CPU-only command and environment with `CUDA_VISIBLE_DEVICES=''`,
   offline flags, no ML imports, no model weights, and no network access;
6. the analyzer/verifier test and no-weight dry-run evidence;
7. a Git commit containing the reviewed implementation package; and
8. an explicit researcher decision whose authorization flags separately allow
   formal input audit, real input reads, outcome–trace join, association
   computation, and independent result verification.

Approval must cover the complete prespecified families. It may not authorize a
reduced panel, favorable EVA-stage or injection-cell selection, fallback
assignment, imputation, exclusion, p-values, confidence intervals, or
cross-attribute ranking.

Even after execution, permitted interpretation is fixed-panel descriptive
co-variation only. No causal, population, model-wide, frame-independent,
localization, route necessity/sufficiency, or cross-attribute conclusion is
licensed.
