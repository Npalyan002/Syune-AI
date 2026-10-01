# Model gateway contract

Requests carry a logical call ID, purpose, role, trusted messages, capabilities, optional schema
and deterministic validator, model/provider constraints, output/timeout/retry/repair/fallback
policy references, hierarchical budgets, principal/access context, metadata, and data policy.

Results preserve execution and semantic-commit IDs, state, normalized failure, provider,
requested/resolved model and version, request ID, attempts, quality, usage, cost, latency, policy,
and audit facts. The request fingerprint covers every execution-relevant field and the validator
identity. Reusing a logical ID with a different fingerprint fails `IDEMPOTENCY_CONFLICT`.
