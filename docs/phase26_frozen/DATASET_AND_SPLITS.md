# Dataset and Splits

Planned corpus: `P26-SYNTH-V1`, eight families, 24 experience records and 40 evaluation records. IDs follow `P26-{family}-{EXP|ID|PARA|NEAR|OOD}-{nn}`. Every canonical JSON record is UTF-8, key-sorted, newline-normalized, and SHA-256 hashed. The split registry must be sealed before calls.

Variation dimensions include entities, quantities, ordering, irrelevant facts, and surface form. OOD cases are superficially similar but require rejecting the learned procedure. Experience and evaluation hashes must be disjoint; normalized 8-gram overlap above 0.80 triggers manual leakage review and blocks execution until resolved under a new protocol version.

Because no repository or domain schema was supplied, task instances were not fabricated in isolation. Their generation must use existing SYUNE action/tool schemas so deterministic scoring maps to real system behavior.

