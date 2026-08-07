# Decision and human gate log v2 — facial-hair freeze addendum

This is a non-overwriting continuation of `decision_and_human_gate_log_v1.md`.

| Decision ID | Date (UTC) | Status | Decision | Basis / authority | Consequence |
|---|---|---|---|---|---|
| D013 | 2026-08-07 | Active | Freeze the condition-blinded round-1 facial-hair annotation CSV with SHA256 `4f0f9117b9853c4a590e5f5f85eb26154c7cfb64ecb6f3b88b0d91d2684e2824`. | Researcher explicit instruction after transcription and independent pre-unblinding validation passed | The 575 anonymous label assignments are immutable; corrections require a new version and explicit lineage. |

| Transition ID | Date (UTC) | Actor / authority | Gate | New state | Exact scope | Consequence |
|---|---|---|---|---|---|---|
| T013 | 2026-08-07 | Researcher explicit freeze declaration | Facial-hair blinded-label freeze | FROZEN; UNBLINDING CLOSED | Freeze `annotation_round1_filled_v1.csv` only | Private mapping access, reconciliation, condition aggregation, and result interpretation remain unauthorized until a separate explicit transition. |
