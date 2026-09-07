# Prospective four-seed-shard amendment v1

This amendment changes only execution packaging. The frozen 40 units, 20 pairs, four seeds, three conditions, intervention construction, prompt, scheduler, guidance, precision, thresholds, and analysis boundaries remain unchanged.

Four seed-complete shards are accepted; three condition shards are rejected. Each shard runs one exact frozen seed over all 40 units and all three co-resident conditions: 120 trajectories and 6,000 scheduler steps. The four shards reconstruct the exact 480-trajectory, 24,000-step family.

Because acquisition is transaction-local, every shard performs 40 fresh preprocessing/LFE acquisitions and constructs 640 held-pair-out token directions. Across the family this is 160 acquisitions and 2,560 transient directions. Only canonical CPU-float32 SHA256 values are retained (40 LFE hashes and 640 direction/sham hash pairs per shard); no raw identity, LFE, or direction tensor is persisted. Exact cross-shard equality is required before any decode gate. Seed and transaction therefore remain confounded until that gate passes.

A shard is atomic. There is no automatic resume, selective condition/trajectory rerun, repair, sample deletion, or reduced family. A failed or interrupted shard may be restarted only from the beginning after a new explicit researcher authorization. A completed and independently verified shard is frozen and is not rerun.

No active GPU execution authorization is created by this preparation. Each shard requires separate single-GPU researcher authorization. No decode, annotation, outcome access/construction, unblinding, or analysis is authorized.
