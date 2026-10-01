# Cognitive transaction boundary

`gateway_semantic_commit_id` proves one validated model result. It does not prove cognitive state was
mutated. `cognitive_transaction_id` is a separate stable SHA-256 identity derived from operation key,
gateway logical call, and semantic commit. The gateway result is reusable after a crash; the cognitive
ledger independently determines whether application is required or already APPLIED.
