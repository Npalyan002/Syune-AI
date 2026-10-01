# Retry, repair, and fallback policy

Default retry is finite (two attempts) for rate limit, timeout, connection/provider failures and
provider-declared truncation. `Retry-After` is honored within the overall timeout. Remote completion
ambiguity is terminal by default. Repair is explicit, separately metered, receives only schema,
sanitized malformed data and deterministic errors, and is never used for a valid-but-wrong answer.
Fallback is opt-in capability equivalence; exact-model calls never fallback.
