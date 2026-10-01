# Failure taxonomy

Transport failures are distinct from content failures. Authentication, authorization, rate limit,
timeout, connection/remote ambiguity, provider 5xx/unavailable, missing model/capability,
concurrency exhaustion, empty, truncated, refusal, invalid JSON, schema-invalid, semantic-invalid,
unknown usage, budget, circuit, idempotency conflict, and unknown provider failure are explicit.

Provider finish state is inspected before JSON parsing. Normal failures terminate without waiting
for a person. Unknown usage retains the conservative reservation.
